"""Statement code generation for the Zonetic bytecode emitter.

`generate_stmt(emitter, node)` dispatches on the AST node type and
emits the corresponding RISC-V instruction sequence.

Print/println ecall codes
--------------------------
  -1  print int64
  -2  print double/float
  -3  print bool
  -4  print string
  -5  println newline
"""

from .instruction import (
    emit_i_type, emit_s, emit_f_type,
    emit_jump, emit_ecall, emit_ecall_store,
)
from .expr_gen import generate_expr, generate_cond
from .rodata import generate_literal_num, generate_literal_f
from .bytecodescope import RegT, ZonVar
from zonc.zonast import *
from .opcode import *


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _scratch(emitter, regt: RegT) -> int:
    return emitter.REG_SCRATCH_X if regt == RegT.X else emitter.REG_SCRATCH_F


def _move_to_return_reg(emitter, reg: ZonVar) -> None:
    """Copy reg into a0 (integer) or fa0 (float) for return or give."""
    src = emitter._read_operand(reg, _scratch(emitter, reg.regt))
    if reg.regt == RegT.X:
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 10, src, 0)
    else:
        emit_f_type(emitter, OpCode.OP_F, 10, src, src, 0x00, F7.FSGNJ_D)


def _alloc_var(emitter, regt: RegT, var_type: ZonType) -> ZonVar:
    """Allocate a ZonVar: prefer an s-register, spill to stack if none free."""
    from .bytecodescope import _SAVED_X, _SAVED_F
    saved = _SAVED_F if regt == RegT.F else _SAVED_X
    used  = {v.reg for s in emitter.symbol_table._scopes for v in s.values()
             if v.reg is not None and v.regt == regt}
    free  = next((r for r in saved if r not in used), None)

    if free is not None:
        return ZonVar(free, regt, var_type)

    frame        = emitter.offset_stack[-1]
    fp_offset    = frame[0] - frame[1]
    frame[0]    -= 8
    return ZonVar(None, regt, var_type, offset_stack=fp_offset)


def _emit_caller_save(emitter) -> tuple[list, list, int]:
    """Save all live temps to the stack before a call. Returns (x_regs, f_regs, offset)."""
    x_regs, f_regs = emitter.reg_manager.get_active_regs()
    offset = emitter.offset_stack[-1][0]

    for r in x_regs:
        emit_s(emitter, OpCode.OP_S,  F3_S.SD,  2, r, offset); offset -= 8
    for r in f_regs:
        emit_s(emitter, OpCode.OP_FS, F3_FS.FSD, 2, r, offset); offset -= 8

    return x_regs, f_regs, emitter.offset_stack[-1][0]


def _emit_caller_restore(emitter, x_regs: list, f_regs: list) -> None:
    """Restore temps saved by _emit_caller_save."""
    offset = emitter.offset_stack[-1][0]
    for r in x_regs:
        emit_i_type(emitter, OpCode.L,  F3_L.LD,  r, 2, offset); offset -= 8
    for r in f_regs:
        emit_i_type(emitter, OpCode.FL, F3_FL.FLD, r, 2, offset); offset -= 8


def _emit_print_param(emitter, param) -> None:
    """Emit a single argument for print/println."""
    if isinstance(param, BoolLiteral):
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 10, 0, param.value)
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -3)
        emit_ecall(emitter)

    elif isinstance(param, IntLiteral):
        generate_literal_num(emitter, param.value, 10)
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -1)
        emit_ecall(emitter)

    elif isinstance(param, FloatLiteral):
        generate_literal_f(emitter, param.value, 10)
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -2)
        emit_ecall(emitter)

    elif isinstance(param, StringLiteral):
        str_var = generate_expr(emitter, param)
        src     = emitter._read_operand(str_var, emitter.REG_SCRATCH_X)
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 10, src, 0)
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -4)
        emit_ecall(emitter)
        emitter.reg_manager.free_temp(str_var)

    else:
        reg = generate_expr(emitter, param)
        src = emitter._read_operand(reg, _scratch(emitter, reg.regt))

        if reg.regt == RegT.X:
            emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 10, src, 0)
            code = {3: -3, 4: -4}.get(reg.zontype.num, -1)
            emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, code)
        else:
            emit_f_type(emitter, OpCode.OP_F, 10, src, src, 0x0, F7.FSGNJ_D)
            emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -2)

        emit_ecall(emitter)
        emitter.reg_manager.free_temp(reg)


def _emit_call_args(emitter, params: list) -> None:
    """Move each argument into the appropriate a-register before a call."""
    int_arg   = 10
    float_arg = 10
    for param in params:
        reg = generate_expr(emitter, param)
        src = emitter._read_operand(reg, _scratch(emitter, reg.regt))
        if reg.regt == RegT.X:
            emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, int_arg, src, 0)
            int_arg += 1
        else:
            emit_f_type(emitter, OpCode.OP_F, float_arg, src, src, 0x0, F7.FSGNJ_D)
            float_arg += 1
        emitter.reg_manager.free_temp(reg)


# ------------------------------------------------------------------
# Main dispatcher
# ------------------------------------------------------------------

def generate_stmt(emitter, node) -> None:
    match node:

        # --------------------------------------------------------------
        case DeclarationStmt():
            if emitter.symbol_table.exists_here(node.name):
                return
            is_float = node.type.num in (2, 7)
            regt     = RegT.F if is_float else RegT.X
            var      = _alloc_var(emitter, regt, node.type)
            emitter.symbol_table._scopes[-1][node.name] = var

        # --------------------------------------------------------------
        case AssignmentStmt():
            slot = emitter.symbol_table.resolve(node.name)

            if slot.is_global:
                reg = generate_expr(emitter, node.value, slot.zontype.num)
                src = emitter._read_operand(reg, _scratch(emitter, reg.regt))
                if slot.zontype.num in (1, 3, 4, 6):
                    emit_s(emitter, OpCode.OP_S,  F3_S.SD,   3, src, slot.offset_global)
                elif slot.zontype.num in (2, 7):
                    emit_s(emitter, OpCode.OP_FS, F3_FS.FSD, 3, src, slot.offset_global)
                emitter.reg_manager.free_temp(reg)
                return

            if slot.reg is not None:
                if isinstance(node.value, (IntLiteral, BoolLiteral)):
                    generate_literal_num(emitter, node.value.value, slot.reg)
                    return
                if isinstance(node.value, FloatLiteral):
                    generate_literal_f(emitter, node.value.value, slot.reg)
                    return

                reg = generate_expr(emitter, node.value, slot.zontype.num)
                src = emitter._read_operand(reg, _scratch(emitter, reg.regt))
                if reg.regt == RegT.X:
                    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, slot.reg, src, 0)
                else:
                    emit_f_type(emitter, OpCode.OP_F, slot.reg, src, src, 0x00, F7.FSGNJ_D)
                emitter.reg_manager.free_temp(reg)

            else:
                if isinstance(node.value, (IntLiteral, BoolLiteral)):
                    generate_literal_num(emitter, node.value.value, emitter.REG_SCRATCH_X)
                    emitter._write_result(slot, emitter.REG_SCRATCH_X)
                    return
                if isinstance(node.value, FloatLiteral):
                    generate_literal_f(emitter, node.value.value, emitter.REG_SCRATCH_F)
                    emitter._write_result(slot, emitter.REG_SCRATCH_F)
                    return

                reg = generate_expr(emitter, node.value, slot.zontype.num)
                src = emitter._read_operand(reg, _scratch(emitter, reg.regt))
                emitter._write_result(slot, src)
                emitter.reg_manager.free_temp(reg)

        # --------------------------------------------------------------
        case InitializationStmt():
            var_name = node.decl_stmt.name
            var_type = node.decl_stmt.type
            is_float = var_type.num in (2, 7)
            regt     = RegT.F if is_float else RegT.X
            val      = node.assign_stmt.value

            # evaluate the right-hand side into a scratch/temp register
            if isinstance(val, (IntLiteral, BoolLiteral)):
                src      = emitter.REG_SCRATCH_X
                generate_literal_num(emitter, val.value, src)
                is_expr  = False
            elif isinstance(val, FloatLiteral):
                src      = emitter.REG_SCRATCH_F
                generate_literal_f(emitter, val.value, src)
                is_expr  = False
            elif isinstance(val, StringLiteral):
                str_var  = generate_expr(emitter, val)
                src      = emitter._read_operand(str_var, emitter.REG_SCRATCH_X)
                emitter.reg_manager.free_temp(str_var)
                is_expr  = False
            else:
                reg_val  = generate_expr(emitter, val, var_type.num)
                src      = emitter._read_operand(reg_val, _scratch(emitter, reg_val.regt))
                is_expr  = True

            # find or allocate the destination slot
            if emitter.symbol_table.exists_here(var_name):
                slot = emitter.symbol_table.resolve(var_name)
            else:
                slot = _alloc_var(emitter, regt, var_type)
                emitter.symbol_table._scopes[-1][var_name] = slot

            # move value into the slot
            if slot.reg is not None:
                if regt == RegT.X:
                    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, slot.reg, src, 0)
                else:
                    emit_f_type(emitter, OpCode.OP_F, slot.reg, src, src, 0x00, F7.FSGNJ_D)
            else:
                emitter._write_result(slot, src)

            if is_expr:
                emitter.reg_manager.free_temp(reg_val)

        # --------------------------------------------------------------
        case CallFunc():
            if node.name in ("print", "println"):
                if node.params is not None:
                    for param in node.params:
                        _emit_print_param(emitter, param)
                if node.name == "println":
                    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -5)
                    emit_ecall(emitter)

            elif node.name == "store":
                emit_ecall_store(emitter, node)

            else:
                if node.params is not None:
                    _emit_call_args(emitter, node.params)

                x_regs, f_regs, _ = _emit_caller_save(emitter)
                emit_jump(emitter, emitter.functions[node.name][0], rd=1)
                _emit_caller_restore(emitter, x_regs, f_regs)

        # --------------------------------------------------------------
        case BlockExpr():
            exit_label = emitter.label_manager.create()
            emitter.value_block_exits.append(exit_label)
            emitter.symbol_table.enter_scope()

            for stmt in node.stmts:
                generate_stmt(emitter, stmt)

            emitter.symbol_table.exit_scope()
            emitter.label_manager.place_label(exit_label, emitter.get_pc())

        # --------------------------------------------------------------
        case IfForm():
            exit_label   = emitter.label_manager.create()
            end_if_label = emitter.label_manager.create()

            if node.if_branch is not None:
                generate_cond(emitter, end_if_label, node.if_branch.cond)
                generate_stmt(emitter, node.if_branch.block)

                if node.elif_branches is None and node.else_branch is None:
                    emitter.label_manager.place_label(end_if_label, emitter.get_pc())
                    return

                emit_jump(emitter, exit_label)
                emitter.label_manager.place_label(end_if_label, emitter.get_pc())

            if node.elif_branches is not None:
                if node.if_branch is not None:
                    pass  # already jumped past the if block above

                for i, branch in enumerate(node.elif_branches):
                    if branch is None:
                        continue
                    end_elif = emitter.label_manager.create()
                    generate_cond(emitter, end_elif, branch.cond)
                    generate_stmt(emitter, branch.block)

                    is_last = (i == len(node.elif_branches) - 1)
                    if is_last and node.else_branch is None:
                        emitter.label_manager.place_label(end_elif, emitter.get_pc())
                        emitter.label_manager.place_label(exit_label, emitter.get_pc())
                        return

                    emit_jump(emitter, exit_label)
                    emitter.label_manager.place_label(end_elif, emitter.get_pc())

            if node.else_branch is not None:
                generate_stmt(emitter, node.else_branch.block)

            emitter.label_manager.place_label(exit_label, emitter.get_pc())

        # --------------------------------------------------------------
        case WhileForm():
            exit_label = emitter.label_manager.create()
            cond_label = emitter.label_manager.create()
            emitter.loop_stack.append((exit_label, cond_label))

            emitter.label_manager.place_label(cond_label, emitter.get_pc())
            generate_cond(emitter, exit_label, node.condition_field)
            generate_stmt(emitter, node.block_expr)
            emit_jump(emitter, cond_label)

            emitter.label_manager.place_label(exit_label, emitter.get_pc())
            emitter.loop_stack.pop()

        # --------------------------------------------------------------
        case ContinueStmt():
            emit_jump(emitter, emitter.loop_stack[-1][1])

        case BreakStmt():
            emit_jump(emitter, emitter.loop_stack[-1][0])

        # --------------------------------------------------------------
        case GiveStmt():
            reg = generate_expr(emitter, node.value)
            _move_to_return_reg(emitter, reg)
            emitter.reg_manager.free_temp(reg)
            emit_jump(emitter, emitter.value_block_exits[-1])
            return reg.regt, reg.zontype

        # --------------------------------------------------------------
        case ReturnStmt():
            func_epilogue = emitter.functions[emitter.current_func][2]

            if node.value is None:
                emit_jump(emitter, func_epilogue)
                return

            # tail-call optimisation: return f(args) where f is the current function
            is_self_call = (
                isinstance(node.value, CallFunc)
                and node.value.name == emitter.current_func
            )
            if is_self_call:
                if node.value.params is not None:
                    _emit_call_args(emitter, node.value.params)

                x_regs, f_regs, _ = _emit_caller_save(emitter)
                emit_jump(emitter, emitter.functions[node.value.name][3], rd=1)
                _emit_caller_restore(emitter, x_regs, f_regs)
                emit_jump(emitter, func_epilogue)
                return

            reg = generate_expr(emitter, node.value)
            _move_to_return_reg(emitter, reg)
            emitter.reg_manager.free_temp(reg)
            emit_jump(emitter, func_epilogue)