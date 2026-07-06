"""Expression code generation for the Zonetic bytecode emitter.

Two public entry points:
    generate_expr(emitter, node, target_type) — emit code that leaves
        the expression value in a ZonVar (register or stack slot).
    generate_cond(emitter, label, node) — emit a conditional branch
        that jumps to label when node evaluates to false.

Register conventions
---------------------
  Scratch x31 (REG_SCRATCH_X) and f31 (REG_SCRATCH_F) are never
  allocated — they are used as temporaries within single emit calls.
  Register 30 (t5) is used as a second scratch when x31 is already
  occupied by one operand.
"""

from .instruction import (
    emit_i_type, emit_r_type, emit_f_type, emit_b_type,
    emit_jump, emit_s, emit_ecall, AddressLoad, emit_ecall_alloc_load,
)
from .rodata import generate_literal_num, generate_literal_f, add_string_to_pool
from .bytecodescope import RegT, ZonVar
from zonc.zonast import *
from .opcode import *


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _scratch(emitter, regt: RegT) -> int:
    return emitter.REG_SCRATCH_X if regt == RegT.X else emitter.REG_SCRATCH_F


def _alt_scratch(primary: int, emitter) -> int:
    """Return a second scratch register when the primary one is in use."""
    return 30 if primary == emitter.REG_SCRATCH_X else emitter.REG_SCRATCH_X


def _read_pair(emitter, left: ZonVar, right: ZonVar):
    """Read both operands, avoiding scratch register conflicts."""
    src_l = emitter._read_operand(left,  _scratch(emitter, left.regt))
    src_r = emitter._read_operand(right, _alt_scratch(src_l, emitter))
    return src_l, src_r


def _alloc_and_resolve(emitter, regt: RegT):
    """Allocate a temp and resolve its physical register."""
    if regt == RegT.F:
        reg = emitter.reg_manager.alloc_ftemp()
        rd  = emitter._resolve_dest(reg, emitter.REG_SCRATCH_F)
    else:
        reg = emitter.reg_manager.alloc_temp()
        rd  = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
    return reg, rd


def _emit_int_r(emitter, funct3, funct7, left: ZonVar, right: ZonVar, is_w: bool = False) -> ZonVar:
    """Emit an integer R-type instruction and return the result ZonVar."""
    src_l, src_r = _read_pair(emitter, left, right)
    reg, rd = _alloc_and_resolve(emitter, RegT.X)
    opcode = OpCode.OP_32 if is_w else OpCode.OP
    emit_r_type(emitter, opcode, funct3, funct7, rd, src_l, src_r)
    emitter._write_result(reg, rd)
    emitter.reg_manager.free_temp(left)
    emitter.reg_manager.free_temp(right)
    return reg


def _emit_float_r(emitter, f7, rm, left: ZonVar, right: ZonVar) -> ZonVar:
    """Emit a float R-type instruction and return the result ZonVar."""
    src_l, src_r = _read_pair(emitter, left, right)
    reg, rd = _alloc_and_resolve(emitter, RegT.F)
    emit_f_type(emitter, OpCode.OP_F, rd, src_l, src_r, rm, f7)
    emitter._write_result(reg, rd)
    emitter.reg_manager.free_temp(left)
    emitter.reg_manager.free_temp(right)
    reg.zontype = ZonType(2, "double")
    return reg


def _emit_caller_save(emitter):
    x_regs, f_regs = emitter.reg_manager.get_active_regs()
    offset = emitter.offset_stack[-1][0]
    for r in x_regs:
        emit_s(emitter, OpCode.OP_S,  F3_S.SD,  2, r, offset); offset -= 8
    for r in f_regs:
        emit_s(emitter, OpCode.OP_FS, F3_FS.FSD, 2, r, offset); offset -= 8
    return x_regs, f_regs


def _emit_caller_restore(emitter, x_regs, f_regs):
    offset = emitter.offset_stack[-1][0]
    for r in x_regs:
        emit_i_type(emitter, OpCode.L,  F3_L.LD,  r, 2, offset); offset -= 8
    for r in f_regs:
        emit_i_type(emitter, OpCode.FL, F3_FL.FLD, r, 2, offset); offset -= 8


def _load_string(emitter, node: StringLiteral) -> ZonVar:
    pool_offset = add_string_to_pool(emitter, node.value)
    reg = emitter.reg_manager.alloc_temp()
    emitter.code.append(AddressLoad(rd=reg.reg, pool_offset=pool_offset))
    emitter.code.append("DUMMY")
    return ZonVar(reg.reg, RegT.X, ZonType(4, "string"))


# ------------------------------------------------------------------
# generate_expr — main expression evaluator
# ------------------------------------------------------------------

def generate_expr(emitter, node, target_type=None) -> ZonVar:
    """Emit code for node and return the ZonVar holding the result."""

    # -- literals (handled before the match for speed) --
    if isinstance(node, (IntLiteral, BoolLiteral)):
        reg = emitter.reg_manager.alloc_temp()
        generate_literal_num(emitter, node.value, reg)
        return reg

    if isinstance(node, FloatLiteral):
        reg = emitter.reg_manager.alloc_ftemp()
        generate_literal_f(emitter, node.value, reg)
        return reg

    if isinstance(node, StringLiteral):
        return _load_string(emitter, node)

    is_w = (target_type == 6)   # int32 target → use *W opcodes
    is_s = (target_type == 2)   # float32 target → use *S f7 variants

    match node:

        # ----------------------------------------------------------
        case CastExpr():
            val = generate_expr(emitter, node.value)
            src = emitter._read_operand(val, _scratch(emitter, val.regt))
            reg, rd = _alloc_and_resolve(emitter, RegT.X)

            if node.zontype.num == 1:   # cast to int64
                emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, rd, src, 0)
            else:                        # cast to bool (sltu rd, x0, src)
                emit_r_type(emitter, OpCode.OP, F3_ALU.SLTU_SLTIU, F7.STANDARD, rd, 0, src)
                reg.zontype = node.zontype

            emitter._write_result(reg, rd)
            emitter.reg_manager.free_temp(val)
            return reg

        # ----------------------------------------------------------
        case BinaryExpr():
            return _gen_binary(emitter, node, is_w, is_s)

        # ----------------------------------------------------------
        case UnaryExpr():
            return _gen_unary(emitter, node, is_w)

        # ----------------------------------------------------------
        case VariableExpr():
            var = emitter.symbol_table.resolve(node.name)
            if not var.is_global:
                return var
            # global: load from .data via gp (register 3)
            if var.zontype.num in (1, 3, 4, 6):
                reg = emitter.reg_manager.alloc_temp()
                src = emitter._read_operand(reg, emitter.REG_SCRATCH_X)
                emit_i_type(emitter, OpCode.L, F3_L.LD, src, 3, var.offset_global)
                return ZonVar(src, RegT.X, var.zontype)
            else:
                reg = emitter.reg_manager.alloc_ftemp()
                src = emitter._read_operand(reg, emitter.REG_SCRATCH_F)
                emit_i_type(emitter, OpCode.FL, F3_FL.FLD, src, 3, var.offset_global)
                return ZonVar(src, RegT.F, var.zontype)

        # ----------------------------------------------------------
        #case IndexExpr():
        #    return _gen_index(emitter, node)

        # ----------------------------------------------------------
        case BlockExpr():
            from .stmt_gen import generate_stmt
            exit_label = emitter.label_manager.create()
            emitter.value_block_exits.append(exit_label)
            emitter.symbol_table.enter_scope()

            regt = zontype = None
            for stmt in node.stmts:
                if isinstance(stmt, GiveStmt):
                    regt, zontype = generate_stmt(emitter, stmt)
                else:
                    generate_stmt(emitter, stmt)

            emitter.symbol_table.exit_scope()
            emitter.label_manager.place_label(exit_label, emitter.get_pc())
            emitter.value_block_exits.pop()
            return ZonVar(10, regt, zontype)

        # ----------------------------------------------------------
        case IfForm():
            return _gen_if_expr(emitter, node)

        # ----------------------------------------------------------
        case CallFunc():
            return _gen_call(emitter, node)

    return None


# ------------------------------------------------------------------
# Binary expression generation
# ------------------------------------------------------------------

def _gen_binary(emitter, node: BinaryExpr, is_w: bool, is_s: bool) -> ZonVar:
    op = node.operator

    # -- string ops --
    if op == Operator.EQ_STR:
        reg = _emit_eq_str(emitter, node)
        reg.zontype = ZonType(3, "bool")
        return reg

    if op == Operator.NE_STR:
        reg = _emit_eq_str(emitter, node)
        result = _gen_not(emitter, reg)
        result.zontype = ZonType(3, "bool")
        return result

    if op == Operator.CONCAT:
        left  = generate_expr(emitter, node.left)
        right = generate_expr(emitter, node.right)
        src_l, src_r = _read_pair(emitter, left, right)
        reg, rd = _alloc_and_resolve(emitter, RegT.X)
        emit_r_type(emitter, OpCode.OP_STR, F3_STR.CONCAT, F7_STR.STANDARD, rd, src_l, src_r)
        emitter._write_result(reg, rd)
        emitter.reg_manager.free_temp(left)
        emitter.reg_manager.free_temp(right)
        reg.zontype = ZonType(4, "string")
        return reg

    # -- add/sub with small immediate (single-instruction fast path) --
    if op in (Operator.ADD, Operator.SUB):
        imm_node = node.right if op == Operator.ADD else node.right
        other    = node.left
        if isinstance(imm_node, IntLiteral) and -2048 <= imm_node.value <= 2047:
            val = -imm_node.value if op == Operator.SUB else imm_node.value
            src_reg = generate_expr(emitter, other)
            src     = emitter._read_operand(src_reg, emitter.REG_SCRATCH_X)
            reg, rd = _alloc_and_resolve(emitter, RegT.X)
            opcode  = OpCode.OP_IMM_32 if is_w else OpCode.OP_IMM
            emit_i_type(emitter, opcode, F3_ALU.ADD_SUB, rd, src, val)
            emitter._write_result(reg, rd)
            emitter.reg_manager.free_temp(src_reg)
            reg.zontype = ZonType(1, "int64")
            return reg
        if op == Operator.ADD and isinstance(node.left, IntLiteral) and -2048 <= node.left.value <= 2047:
            src_reg = generate_expr(emitter, node.right)
            src     = emitter._read_operand(src_reg, emitter.REG_SCRATCH_X)
            reg, rd = _alloc_and_resolve(emitter, RegT.X)
            opcode  = OpCode.OP_IMM_32 if is_w else OpCode.OP_IMM
            emit_i_type(emitter, opcode, F3_ALU.ADD_SUB, rd, src, node.left.value)
            emitter._write_result(reg, rd)
            emitter.reg_manager.free_temp(src_reg)
            reg.zontype = ZonType(1, "int64")
            return reg

    # -- general arithmetic --
    left  = generate_expr(emitter, node.left)
    right = generate_expr(emitter, node.right)

    if op == Operator.ADD:
        if left.regt == RegT.X:
            reg = _emit_int_r(emitter, F3_ALU.ADD_SUB, F7.STANDARD, left, right, is_w)
            reg.zontype = ZonType(1, "int64")
            return reg
        f7 = F7.STANDARD if is_s else F7.M_EXT_OR_FADD_D
        return _emit_float_r(emitter, f7, 0x7, left, right)

    if op == Operator.SUB:
        if left.regt == RegT.X:
            reg = _emit_int_r(emitter, F3_ALU.ADD_SUB, F7.ALT, left, right, is_w)
            reg.zontype = ZonType(1, "int64")
            return reg
        f7 = F7.FSUB_S if is_s else F7.FSUB_D
        return _emit_float_r(emitter, f7, 0x7, left, right)

    if op == Operator.MUL:
        if left.regt == RegT.X:
            reg = _emit_int_r(emitter, F3_M_EXT.MUL, F7.M_EXT_OR_FADD_D, left, right, is_w)
            reg.zontype = ZonType(1, "int64")
            return reg
        f7 = F7.FMUL_S if is_s else F7.FMUL_D
        return _emit_float_r(emitter, f7, 0x7, left, right)

    if op == Operator.DIV:
        if left.regt == RegT.X:
            reg = _emit_int_r(emitter, F3_M_EXT.DIV, F7.M_EXT_OR_FADD_D, left, right, is_w)
            reg.zontype = ZonType(1, "int64")
            return reg
        f7 = F7.FDIV_S if is_s else F7.FDIV_D
        return _emit_float_r(emitter, f7, 0x7, left, right)

    if op == Operator.MOD:
        reg = _emit_int_r(emitter, F3_M_EXT.REM, F7.M_EXT_OR_FADD_D, left, right, is_w)
        reg.zontype = ZonType(1, "int64")
        return reg

    # -- comparisons --
    if op == Operator.LT:
        return _gen_lt(emitter, left, right)
    if op == Operator.GT:
        return _gen_lt(emitter, right, left)       # swap operands
    if op == Operator.GE:
        return _gen_not(emitter, _gen_lt(emitter, left, right))
    if op == Operator.LE:
        return _gen_not(emitter, _gen_lt(emitter, right, left))
    if op == Operator.EQ:
        return _gen_eq(emitter, left, right, node.left, node.right)
    if op == Operator.NE:
        return _gen_not(emitter, _gen_eq(emitter, left, right, node.left, node.right))

    # -- logical (short-circuit) --
    if op == Operator.AND:
        reg, rd = _alloc_and_resolve(emitter, RegT.X)
        _gen_cond_and(emitter, node, label=None, result_reg=rd)
        emitter._write_result(reg, rd)
        reg.zontype = ZonType(3, "bool")
        return reg

    if op == Operator.OR:
        reg, rd = _alloc_and_resolve(emitter, RegT.X)
        _gen_cond_or(emitter, node, label=None, result_reg=rd)
        emitter._write_result(reg, rd)
        reg.zontype = ZonType(3, "bool")
        return reg

    # -- bitwise --
    if op == Operator.BAND:  return _gen_bitwise(emitter, node, F3_ALU.AND_ANDI, F7.STANDARD)
    if op == Operator.BNAND: return _gen_not(emitter, _gen_bitwise(emitter, node, F3_ALU.AND_ANDI, F7.STANDARD), bit=True)
    if op == Operator.BOR:   return _gen_bitwise(emitter, node, F3_ALU.OR_ORI,  F7.STANDARD)
    if op == Operator.BNOR:  return _gen_not(emitter, _gen_bitwise(emitter, node, F3_ALU.OR_ORI,  F7.STANDARD), bit=True)
    if op == Operator.BXOR:  return _gen_bitwise(emitter, node, F3_ALU.XOR_XORI, F7.STANDARD)
    if op == Operator.BXNOR: return _gen_not(emitter, _gen_bitwise(emitter, node, F3_ALU.XOR_XORI, F7.STANDARD), bit=True)

    # -- shifts --
    if op == Operator.SL:
        if isinstance(node.right, IntLiteral) and -2048 <= node.right.value <= 2047:
            src_reg = generate_expr(emitter, node.left)
            src     = emitter._read_operand(src_reg, emitter.REG_SCRATCH_X)
            reg, rd = _alloc_and_resolve(emitter, RegT.X)
            emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.SLL_SLLI, rd, src, node.right.value)
            emitter._write_result(reg, rd)
            emitter.reg_manager.free_temp(src_reg)
            return reg
        return _emit_int_r(emitter, F3_ALU.SLL_SLLI, F7.STANDARD, left, right)

    if op == Operator.SR:
        if isinstance(node.right, IntLiteral):
            src_reg = generate_expr(emitter, node.left)
            src     = emitter._read_operand(src_reg, emitter.REG_SCRATCH_X)
            reg, rd = _alloc_and_resolve(emitter, RegT.X)
            shamt   = node.right.value & 0x3F
            emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.SRL_SRLI_SRA_SRAI, rd, src, 0x400 | shamt)
            emitter._write_result(reg, rd)
            emitter.reg_manager.free_temp(src_reg)
            return reg
        return _emit_int_r(emitter, F3_ALU.SRL_SRLI_SRA_SRAI, F7.ALT, left, right)

    return None


# ------------------------------------------------------------------
# Comparison helpers
# ------------------------------------------------------------------

def _gen_lt(emitter, left: ZonVar, right: ZonVar) -> ZonVar:
    """Emit set-less-than for integer or float operands."""
    reg, rd = _alloc_and_resolve(emitter, RegT.X)
    if left.regt == RegT.X:
        src_l, src_r = _read_pair(emitter, left, right)
        emit_r_type(emitter, OpCode.OP, F3_ALU.SLT_SLTI, F7.STANDARD, rd, src_l, src_r)
    else:
        src_l, src_r = _read_pair(emitter, left, right)
        emit_f_type(emitter, OpCode.OP_F, rd, src_l, src_r, 0x01, F7.FCOMP_S)
    emitter._write_result(reg, rd)
    emitter.reg_manager.free_temp(left)
    emitter.reg_manager.free_temp(right)
    return reg


def _gen_eq(emitter, left: ZonVar, right: ZonVar, orig_left, orig_right) -> ZonVar:
    """Emit equality check (XOR + SLTIU 1) for integer or float."""
    reg, rd = _alloc_and_resolve(emitter, RegT.X)

    if left.regt == RegT.X:
        # xor then sltu rd, xor_result, 1
        if isinstance(orig_left, (IntLiteral, BoolLiteral)):
            src = emitter._read_operand(right, emitter.REG_SCRATCH_X)
            xor_rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
            emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.XOR_XORI, xor_rd, src, orig_left.value)
        elif isinstance(orig_right, (IntLiteral, BoolLiteral)):
            src = emitter._read_operand(left, emitter.REG_SCRATCH_X)
            xor_rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
            emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.XOR_XORI, xor_rd, src, orig_right.value)
        else:
            src_l, src_r = _read_pair(emitter, left, right)
            xor_rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
            emit_r_type(emitter, OpCode.OP, F3_ALU.XOR_XORI, F7.STANDARD, xor_rd, src_l, src_r)
            emitter.reg_manager.free_temp(right)

        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.SLTU_SLTIU, rd, xor_rd, 1)
        emitter._write_result(reg, rd)
        emitter.reg_manager.free_temp(left)
        return reg

    # float equality: FEQ
    src_l, src_r = _read_pair(emitter, left, right)
    emit_f_type(emitter, OpCode.OP_F, rd, src_l, src_r, 0x02, F7.FCOMP_S)
    emitter._write_result(reg, rd)
    emitter.reg_manager.free_temp(left)
    emitter.reg_manager.free_temp(right)
    return reg


def _gen_not(emitter, reg: ZonVar, bit: bool = False) -> ZonVar:
    """Emit logical NOT (xori rd, src, 1) or bitwise NOT (xori rd, src, -1)."""
    src     = emitter._read_operand(reg, emitter.REG_SCRATCH_X)
    out, rd = _alloc_and_resolve(emitter, RegT.X)
    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.XOR_XORI, rd, src, -1 if bit else 1)
    emitter.reg_manager.free_temp(reg)
    emitter._write_result(out, rd)
    return out


def _gen_bitwise(emitter, node: BinaryExpr, funct3, funct7) -> ZonVar:
    """Emit a bitwise AND/OR/XOR, using immediate form when one operand fits."""
    imm_node = None
    other    = None
    if isinstance(node.left,  IntLiteral) and -2048 <= node.left.value  <= 2047:
        imm_node, other = node.left, node.right
    elif isinstance(node.right, IntLiteral) and -2048 <= node.right.value <= 2047:
        imm_node, other = node.right, node.left

    if imm_node is not None:
        src_reg = generate_expr(emitter, other)
        src     = emitter._read_operand(src_reg, emitter.REG_SCRATCH_X)
        reg, rd = _alloc_and_resolve(emitter, RegT.X)
        emit_i_type(emitter, OpCode.OP_IMM, funct3, rd, src, imm_node.value)
        emitter._write_result(reg, rd)
        emitter.reg_manager.free_temp(src_reg)
        return reg

    left  = generate_expr(emitter, node.left)
    right = generate_expr(emitter, node.right)
    return _emit_int_r(emitter, funct3, funct7, left, right)


# ------------------------------------------------------------------
# Unary expression generation
# ------------------------------------------------------------------

def _gen_unary(emitter, node: UnaryExpr, is_w: bool) -> ZonVar:
    if node.operator == Operator.NEG:
        val = generate_expr(emitter, node.value)
        src = emitter._read_operand(val, _scratch(emitter, val.regt))
        if val.regt == RegT.X:
            reg, rd = _alloc_and_resolve(emitter, RegT.X)
            opcode  = OpCode.OP_32 if is_w else OpCode.OP
            emit_r_type(emitter, opcode, F3_ALU.ADD_SUB, F7.ALT, rd, 0, src)
            emitter._write_result(reg, rd)
        else:
            reg, rd = _alloc_and_resolve(emitter, RegT.F)
            emit_f_type(emitter, OpCode.OP_F, rd, src, src, 0x01, F7.FSGNJ_D)
            emitter._write_result(reg, rd)
        emitter.reg_manager.free_temp(val)
        return reg

    if node.operator == Operator.NOT:
        val = generate_expr(emitter, node.value)
        return _gen_not(emitter, val)

    if node.operator == Operator.BNOT:
        val = generate_expr(emitter, node.value)
        return _gen_not(emitter, val, bit=True)

    return None


# ------------------------------------------------------------------
# Index expression
# ------------------------------------------------------------------

"""def _gen_index(emitter, node: IndexExpr) -> ZonVar:
    symbol = emitter.symbol_table.resolve(node.name)

    if isinstance(node.index, IntLiteral):
        offset = symbol.offset_stack + node.index.value * 8
        reg, rd = _alloc_and_resolve(emitter, RegT.X)
        emit_i_type(emitter, OpCode.L, F3_L.LD, rd, 8, offset)
        emitter._write_result(reg, rd)
        reg.zontype = symbol.zontype
        return reg

    # dynamic index — bounds check via ecall 1947, then load
    idx_reg = generate_expr(emitter, node.index)
    src_i   = emitter._read_operand(idx_reg, emitter.REG_SCRATCH_X)

    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 10, src_i, 0)
    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 11, 0, symbol.zontype.size.value)

    valid_label = emitter.label_manager.create()
    emit_b_type(emitter, OpCode.OP_B, F3_B.BLTU, 10, 11, valid_label)
    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, 1947)
    emit_ecall(emitter)
    emitter.label_manager.place_label(valid_label, emitter.get_pc())

    offset_reg, rd_off = _alloc_and_resolve(emitter, RegT.X)
    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.SLL_SLLI, rd_off, 10, 3)
    emitter._write_result(offset_reg, rd_off)

    dir_reg, rd_dir = _alloc_and_resolve(emitter, RegT.X)
    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, rd_dir, 8, symbol.offset_stack)
    emitter._write_result(dir_reg, rd_dir)

    src_off = emitter._read_operand(offset_reg, 30 if rd_dir == emitter.REG_SCRATCH_X else emitter.REG_SCRATCH_X)
    emit_r_type(emitter, OpCode.OP, F3_ALU.ADD_SUB, F7.STANDARD, rd_dir, rd_dir, src_off)
    emitter._write_result(dir_reg, rd_dir)

    result, rd_res = _alloc_and_resolve(emitter, RegT.X)
    emit_i_type(emitter, OpCode.L, F3_L.LD, rd_res, rd_dir, 0)
    emitter._write_result(result, rd_res)

    emitter.reg_manager.free_temp(idx_reg)
    emitter.reg_manager.free_temp(offset_reg)
    emitter.reg_manager.free_temp(dir_reg)
    result.zontype = symbol.zontype
    return result"""


# ------------------------------------------------------------------
# If-as-expression
# ------------------------------------------------------------------

def _gen_if_expr(emitter, node: IfForm) -> ZonVar:
    exit_label  = emitter.label_manager.create()
    result, rd  = _alloc_and_resolve(emitter, RegT.X)

    def _emit_branch_value(block):
        value = generate_expr(emitter, block)
        src   = emitter._read_operand(value, _scratch(emitter, value.regt))
        if value.regt == RegT.X:
            emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, rd, src, 0)
        else:
            emit_f_type(emitter, OpCode.OP_F, rd, src, src, 0x00, F7.FSGNJ_D)
        result.zontype = value.zontype

    if node.if_branch:
        false_label = emitter.label_manager.create()
        generate_cond(emitter, false_label, node.if_branch.cond)
        _emit_branch_value(node.if_branch.block)
        emit_jump(emitter, exit_label)
        emitter.label_manager.place_label(false_label, emitter.get_pc())

    for branch in (node.elif_branches or []):
        if branch is None:
            continue
        elif_label = emitter.label_manager.create()
        generate_cond(emitter, elif_label, branch.cond)
        _emit_branch_value(branch.block)
        emit_jump(emitter, exit_label)
        emitter.label_manager.place_label(elif_label, emitter.get_pc())

    if node.else_branch:
        _emit_branch_value(node.else_branch.block)

    emitter.label_manager.place_label(exit_label, emitter.get_pc())
    emitter._write_result(result, rd)
    return result


# ------------------------------------------------------------------
# Call as expression
# ------------------------------------------------------------------

def _gen_call(emitter, node: CallFunc) -> ZonVar:
    if node.name == "alloc":
        return emit_ecall_alloc_load(emitter, node, 0)
    if node.name == "load":
        return emit_ecall_alloc_load(emitter, node, 1)

    int_arg = float_arg = 10
    if node.params is not None:
        for param in node.params:
            reg = generate_expr(emitter, param)
            src = emitter._read_operand(reg, _scratch(emitter, reg.regt))
            if reg.regt == RegT.X:
                emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, int_arg, src, 0)
                int_arg += 1
            else:
                emit_f_type(emitter, OpCode.OP_F, float_arg, src, src, 0x0, F7.FSGNJ_D)
                float_arg += 1
            emitter.reg_manager.free_temp(reg)

    x_regs, f_regs = _emit_caller_save(emitter)
    emit_jump(emitter, emitter.functions[node.name][0], rd=1)
    _emit_caller_restore(emitter, x_regs, f_regs)

    return_type = emitter.functions[node.name][1]
    if return_type.num in (1, 3, 4, 6):
        result, rd = _alloc_and_resolve(emitter, RegT.X)
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, rd, 10, 0)
        emitter._write_result(result, rd)
        result.zontype = return_type
        return result
    if return_type.num in (2, 7):
        result, rd = _alloc_and_resolve(emitter, RegT.F)
        emit_f_type(emitter, OpCode.OP_F, rd, 10, 10, 0x0, F7.FSGNJ_D)
        emitter._write_result(result, rd)
        return result
    return ZonVar(10, None, return_type)


# ------------------------------------------------------------------
# String equality
# ------------------------------------------------------------------

def _emit_eq_str(emitter, node: BinaryExpr) -> ZonVar:
    left  = generate_expr(emitter, node.left)
    right = generate_expr(emitter, node.right)
    src_l, src_r = _read_pair(emitter, left, right)
    reg, rd = _alloc_and_resolve(emitter, RegT.X)
    emit_r_type(emitter, OpCode.OP_STR, F3_STR.CMP, F7_STR.STANDARD, rd, src_l, src_r)
    emitter._write_result(reg, rd)
    emitter.reg_manager.free_temp(left)
    emitter.reg_manager.free_temp(right)
    return reg


# ------------------------------------------------------------------
# generate_cond — condition branch emitter
# ------------------------------------------------------------------

def generate_cond(emitter, label: int, node) -> None:
    """Emit a conditional branch to label when node is false."""
    match node:

        case BoolLiteral():
            reg = emitter.reg_manager.alloc_temp()
            emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, reg, 0, node.value)
            emit_b_type(emitter, OpCode.OP_B, F3_B.BEQ, reg, 0, label)
            emitter.reg_manager.free_temp(reg)

        case VariableExpr():
            var = emitter.symbol_table.resolve(node.name)
            src = emitter._read_operand(var, emitter.REG_SCRATCH_X)
            emit_b_type(emitter, OpCode.OP_B, F3_B.BEQ, src, 0, label)

        case CastExpr():
            val = generate_expr(emitter, node.value)
            src = emitter._read_operand(val, _scratch(emitter, val.regt))
            reg, rd = _alloc_and_resolve(emitter, RegT.X)
            emit_r_type(emitter, OpCode.OP, F3_ALU.SLTU_SLTIU, F7.STANDARD, rd, 0, src)
            emitter._write_result(reg, rd)
            emit_b_type(emitter, OpCode.OP_B, F3_B.BEQ, reg, 0, label)
            emitter.reg_manager.free_temp(val)
            emitter.reg_manager.free_temp(reg)

        case BinaryExpr():
            _gen_cond_binary(emitter, label, node)


def _gen_cond_binary(emitter, label: int, node: BinaryExpr) -> None:
    op = node.operator

    if op == Operator.AND:
        _gen_cond_and(emitter, node, label=label)
        return
    if op == Operator.OR:
        _gen_cond_or(emitter, node, label=label)
        return

    left  = generate_expr(emitter, node.left)
    right = generate_expr(emitter, node.right)

    if op in (Operator.EQ, Operator.NE):
        branch = F3_B.BNE if op == Operator.EQ else F3_B.BEQ
        if left.regt == RegT.X:
            src_l, src_r = _read_pair(emitter, left, right)
            emit_b_type(emitter, OpCode.OP_B, branch, src_l, src_r, label)
        else:
            src_l, src_r = _read_pair(emitter, left, right)
            reg = emitter.reg_manager.alloc_temp()
            emit_f_type(emitter, OpCode.OP_F, reg, src_l, src_r, 0x02, F7.FCOMP_S)
            emit_b_type(emitter, OpCode.OP_B, F3_B.BEQ, 0, reg, label)
            emitter.reg_manager.free_temp(reg)
        emitter.reg_manager.free_temp(left)
        emitter.reg_manager.free_temp(right)
        return

    if op == Operator.LT:
        _gen_cond_lt(emitter, label, left, right)
        return
    if op == Operator.GT:
        _gen_cond_lt(emitter, label, right, left)
        return
    if op == Operator.LE:
        _gen_cond_ge(emitter, label, right, left)
        return
    if op == Operator.GE:
        _gen_cond_ge(emitter, label, left, right)
        return


def _gen_cond_lt(emitter, label: int, left: ZonVar, right: ZonVar) -> None:
    if left.regt == RegT.X:
        src_l, src_r = _read_pair(emitter, left, right)
        emit_b_type(emitter, OpCode.OP_B, F3_B.BGE, src_l, src_r, label)
    else:
        src_l, src_r = _read_pair(emitter, left, right)
        reg = emitter.reg_manager.alloc_temp()
        emit_f_type(emitter, OpCode.OP_F, reg, src_l, src_r, 0x01, F7.FCOMP_S)
        emit_b_type(emitter, OpCode.OP_B, F3_B.BEQ, 0, reg, label)
        emitter.reg_manager.free_temp(reg)
    emitter.reg_manager.free_temp(left)
    emitter.reg_manager.free_temp(right)


def _gen_cond_ge(emitter, label: int, left: ZonVar, right: ZonVar) -> None:
    if left.regt == RegT.X:
        src_l, src_r = _read_pair(emitter, left, right)
        emit_b_type(emitter, OpCode.OP_B, F3_B.BLT, src_l, src_r, label)
    else:
        src_l, src_r = _read_pair(emitter, left, right)
        reg = emitter.reg_manager.alloc_temp()
        emit_f_type(emitter, OpCode.OP_F, reg, src_r, src_l, 0x00, F7.FCOMP_S)
        emit_b_type(emitter, OpCode.OP_B, F3_B.BEQ, 0, reg, label)
        emitter.reg_manager.free_temp(reg)
    emitter.reg_manager.free_temp(left)
    emitter.reg_manager.free_temp(right)


def _gen_cond_and(emitter, node: BinaryExpr, label=None, result_reg=None) -> None:
    """Short-circuit AND: jump to label (or set result_reg=0) if left is false."""
    false_l = emitter.label_manager.create()
    exit_l  = emitter.label_manager.create()

    left = generate_expr(emitter, node.left)
    src  = emitter._read_operand(left, emitter.REG_SCRATCH_X)
    emit_b_type(emitter, OpCode.OP_B, F3_B.BEQ, src, 0, label if label else false_l)
    emitter.reg_manager.free_temp(left)

    right = generate_expr(emitter, node.right)
    src   = emitter._read_operand(right, emitter.REG_SCRATCH_X)
    emit_b_type(emitter, OpCode.OP_B, F3_B.BEQ, src, 0, label if label else false_l)
    emitter.reg_manager.free_temp(right)

    if result_reg is not None:
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, result_reg, 0, 1)
        emit_jump(emitter, exit_l)
        emitter.label_manager.place_label(false_l, emitter.get_pc())
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, result_reg, 0, 0)
        emitter.label_manager.place_label(exit_l, emitter.get_pc())


def _gen_cond_or(emitter, node: BinaryExpr, label=None, result_reg=None) -> None:
    """Short-circuit OR: jump to label (or set result_reg=1) if left is true."""
    true_l = emitter.label_manager.create()
    exit_l = emitter.label_manager.create()

    left = generate_expr(emitter, node.left)
    src  = emitter._read_operand(left, emitter.REG_SCRATCH_X)
    emit_b_type(emitter, OpCode.OP_B, F3_B.BNE, src, 0, label if label else true_l)
    emitter.reg_manager.free_temp(left)

    right = generate_expr(emitter, node.right)
    src   = emitter._read_operand(right, emitter.REG_SCRATCH_X)
    emit_b_type(emitter, OpCode.OP_B, F3_B.BNE, src, 0, label if label else true_l)
    emitter.reg_manager.free_temp(right)

    if result_reg is not None:
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, result_reg, 0, 0)
        emit_jump(emitter, exit_l)
        emitter.label_manager.place_label(true_l, emitter.get_pc())
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, result_reg, 0, 1)
        emitter.label_manager.place_label(exit_l, emitter.get_pc())