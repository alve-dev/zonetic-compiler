# bytecodegen/expr_gen.py
from .instruction import (
    emit_i_type, emit_r_type, emit_f_type, emit_b_type, emit_jump,
    emit_s, emit_ecall, AddressLoad, emit_ecall_alloc_load
)
from .rodata import generate_literal_num, generate_literal_f, add_string_to_pool
from .bytecodescope import RegT, ZonVar
from zonc.zonast import *
from .opcode import *
import struct

def _load_string_literal(emitter, node):
    pool_offset = add_string_to_pool(emitter, node.value)
    reg = emitter.reg_manager.alloc_temp()
    emitter.code.append(AddressLoad(rd=reg.reg, pool_offset=pool_offset))
    emitter.code.append("DUMMY")
    return ZonVar(reg.reg, RegT.X, ZonType(4, "string"))

def generate_expr(emitter, node, target_type=None):
    if isinstance(node, (IntLiteral, BoolLiteral)):
        reg = emitter.reg_manager.alloc_temp()
        generate_literal_num(emitter, node.value, reg)
        return reg
    
    if isinstance(node, FloatLiteral):
        reg = emitter.reg_manager.alloc_ftemp()
        generate_literal_f(emitter, node.value, reg)
        return reg
    
    if isinstance(node, StringLiteral):
        return _load_string_literal(emitter, node)

    match node:
        case CastExpr():
            if node.zontype.num == 1:
                reg_value = generate_expr(emitter, node.value)
                src_v = emitter._read_operand(reg_value, emitter.REG_SCRATCH_X if reg_value.regt == RegT.X else emitter.REG_SCRATCH_F)
                reg = emitter.reg_manager.alloc_temp()
                rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
                emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, rd, src_v, 0)
                emitter._write_result(reg, rd)
                return reg
            
            elif node.zontype.num == 3:
                reg_value = generate_expr(emitter, node.value)
                src_v = emitter._read_operand(reg_value, emitter.REG_SCRATCH_X if reg_value.regt == RegT.X else emitter.REG_SCRATCH_F)
                reg = emitter.reg_manager.alloc_temp()
                rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
                emit_r_type(emitter, OpCode.OP, F3_ALU.SLTU_SLTIU, F7.STANDARD, rd, 0, src_v)
                emitter._write_result(reg, rd)
                reg.zontype = node.zontype
                return reg

        case BinaryExpr():
            is_w = (target_type == 6)
            is_s = (target_type == 2)
            match node.operator:
                case Operator.EQ_STR:
                    reg = emit_eq_str(emitter, node)
                    reg.zontype = ZonType(3, "bool")
                    return reg
                
                case Operator.NE_STR:
                    reg = emit_eq_str(emitter, node)
                    reg_not = generate_not_expr(emitter, reg_val=reg, bit=False)
                    reg_not.zontype = ZonType(3, "bool")
                    return reg_not
                
                case Operator.CONCAT:
                    reg_left = generate_expr(emitter, node.left)
                    reg_right = generate_expr(emitter, node.right)
                    src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
                    src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_X else emitter.REG_SCRATCH_X)
                    reg = emitter.reg_manager.alloc_temp()
                    rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
                    emit_r_type(emitter, OpCode.OP_STR, F3_STR.CONCAT, F7_STR.STANDARD, rd, src_l, src_r)
                    emitter._write_result(reg, rd)
                    emitter.reg_manager.free_temp(reg_left)
                    emitter.reg_manager.free_temp(reg_right)
                    reg.zontype = ZonType(4, "string")
                    return reg

                case Operator.ADD:
                    if isinstance(node.right, IntLiteral) and (-2048 <= node.right.value <= 2047):
                        reg_left = generate_expr(emitter, node.left)
                        src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
                        reg = emitter.reg_manager.alloc_temp()
                        rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
                        opcode = OpCode.OP_IMM_32 if is_w else OpCode.OP_IMM
                        emit_i_type(emitter, opcode, F3_ALU.ADD_SUB, rd, src_l, node.right.value)
                        emitter._write_result(reg, rd)
                        emitter.reg_manager.free_temp(reg_left)
                        reg.zontype = ZonType(1, "int64")
                        return reg
                    if isinstance(node.left, IntLiteral) and (-2048 <= node.left.value <= 2047):
                        reg_right = generate_expr(emitter, node.right)
                        src_r = emitter._read_operand(reg_right, emitter.REG_SCRATCH_X)
                        reg = emitter.reg_manager.alloc_temp()
                        rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
                        opcode = OpCode.OP_IMM_32 if is_w else OpCode.OP_IMM
                        emit_i_type(emitter, opcode, F3_ALU.ADD_SUB, rd, src_r, node.left.value)
                        emitter._write_result(reg, rd)
                        emitter.reg_manager.free_temp(reg_right)
                        reg.zontype = ZonType(1, "int64")
                        return reg
                    reg_left = generate_expr(emitter, node.left)
                    reg_right = generate_expr(emitter, node.right)
                    if reg_left.regt == RegT.X:
                        src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
                        src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_X else emitter.REG_SCRATCH_X)
                        reg = emitter.reg_manager.alloc_temp()
                        rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
                        opcode = OpCode.OP_32 if is_w else OpCode.OP
                        emit_r_type(emitter, opcode, F3_ALU.ADD_SUB, F7.STANDARD, rd, src_l, src_r)
                        emitter._write_result(reg, rd)
                        reg.zontype = ZonType(1, "int64")
                    elif reg_left.regt == RegT.F:
                        src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_F)
                        src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_F else emitter.REG_SCRATCH_F)
                        reg = emitter.reg_manager.alloc_ftemp()
                        rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_F)
                        f7 = F7.STANDARD if is_s else F7.M_EXT_OR_FADD_D
                        emit_f_type(emitter, OpCode.OP_F, rd, src_l, src_r, 0x7, f7)
                        emitter._write_result(reg, rd)
                        reg.zontype = ZonType(2, "double")
                    emitter.reg_manager.free_temp(reg_left)
                    emitter.reg_manager.free_temp(reg_right)
                    return reg

                case Operator.SUB:
                    if isinstance(node.right, IntLiteral) and (node.right.value >= -2048 and node.right.value <= 2047):
                        reg_left = generate_expr(emitter, node.left)
                        src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
                        reg = emitter.reg_manager.alloc_temp()
                        rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
                        opcode = OpCode.OP_IMM_32 if is_w else OpCode.OP_IMM
                        emit_i_type(emitter, opcode, F3_ALU.ADD_SUB, rd, src_l, -(node.right.value))
                        emitter.reg_manager.free_temp(reg_left)
                        emitter._write_result(reg, rd)
                        reg.zontype = ZonType(1, "int64")
                        return reg

                    reg_left = generate_expr(emitter, node.left)
                    reg_right = generate_expr(emitter, node.right)
                    if reg_left.regt == RegT.X:
                        src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
                        src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_X else emitter.REG_SCRATCH_X)
                        reg = emitter.reg_manager.alloc_temp()
                        rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
                        opcode = OpCode.OP_32 if is_w else OpCode.OP
                        emitter.emit_r_type(emitter, opcode, F3_ALU.ADD_SUB, F7.ALT, rd, src_l, src_r)
                        emitter._write_result(reg, rd)
                        reg.zontype = ZonType(1, "int64")
                    
                    elif reg_left.regt == RegT.F:
                        src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_F)
                        src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_F else emitter.REG_SCRATCH_F)
                        reg = emitter.reg_manager.alloc_ftemp()
                        rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_F)
                        f7 = F7.FSUB_S if is_s else F7.FSUB_D
                        emit_f_type(emitter, OpCode.OP_F, rd, src_l, src_r, 0x7, f7)
                        emitter._write_result(reg, rd)
                        reg.zontype = ZonType(2, "double")
                        
                        
                    emitter.reg_manager.free_temp(reg_left)
                    emitter.reg_manager.free_temp(reg_right)
                    
                    return reg

                case Operator.MUL:
                    reg_left = generate_expr(emitter, node.left)
                    reg_right = generate_expr(emitter, node.right)
                    if reg_left.regt == RegT.X:
                        src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
                        src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_X else emitter.REG_SCRATCH_X)
                        reg = emitter.reg_manager.alloc_temp()
                        rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
                        opcode = OpCode.OP_32 if is_w else OpCode.OP
                        emit_r_type(emitter, opcode, F3_M_EXT.MUL, F7.M_EXT_OR_FADD_D, rd, src_l, src_r)
                        emitter._write_result(reg, rd)
                        reg.zontype = ZonType(1, "int64")
                        
                    elif reg_left.regt == RegT.F:
                        src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_F)
                        src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_F else emitter.REG_SCRATCH_F)
                        reg = emitter.reg_manager.alloc_ftemp()
                        rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_F)
                        f7 = F7.FMUL_S if is_s else F7.FMUL_D
                        emit_f_type(emitter, OpCode.OP_F, rd, src_l, src_r, 0x7, f7)
                        emitter._write_result(reg, rd)
                        reg.zontype = ZonType(2, "double")
                    
                    emitter.reg_manager.free_temp(reg_left)
                    emitter.reg_manager.free_temp(reg_right)
                    
                    return reg
                
                case Operator.DIV:
                    reg_left = generate_expr(emitter, node.left)
                    reg_right = generate_expr(emitter, node.right)
                    if reg_left.regt == RegT.X:
                        src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
                        src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_X else emitter.REG_SCRATCH_X)
                        reg = emitter.reg_manager.alloc_temp()
                        rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
                        opcode = OpCode.OP_32 if is_w else OpCode.OP
                        emit_r_type(emitter, opcode, F3_M_EXT.DIV, F7.M_EXT_OR_FADD_D, rd, src_l, src_r)
                        emitter._write_result(reg, rd)
                        reg.zontype = ZonType(1, "int64")
                    
                    elif reg_left.regt == RegT.F:
                        src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_F)
                        src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_F else emitter.REG_SCRATCH_F)
                        reg = emitter.reg_manager.alloc_ftemp()
                        rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
                        f7 = F7.FDIV_S if is_s else F7.FDIV_D
                        emit_f_type(emitter, OpCode.OP_F, rd, src_l, src_r, 0x7, f7)
                        emitter._write_result(reg, rd)
                        reg.zontype = ZonType(2, "double")
                        
                        
                    emitter.reg_manager.free_temp(reg_left)
                    emitter.reg_manager.free_temp(reg_right)     
                    return reg
                
                case Operator.MOD:
                    reg_left = generate_expr(emitter, node.left)
                    reg_right = generate_expr(emitter, node.right)
                    src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
                    src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_X else emitter.REG_SCRATCH_X)
                    reg = emitter.reg_manager.alloc_temp()
                    rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)                        
                    opcode = OpCode.OP_32 if is_w else OpCode.OP
                    emit_r_type(emitter, opcode, F3_M_EXT.REM, F7.M_EXT_OR_FADD_D, rd, src_l, src_r)
                    emitter._write_result(reg, rd)
                    reg.zontype = ZonType(1, "int64")

                    emitter.reg_manager.free_temp(reg_left)
                    emitter.reg_manager.free_temp(reg_right)
                    return reg
                
                case Operator.LT: return generate_lt_expr(emitter, node)
                    
                case Operator.GT:
                    right = node.right
                    node.right = node.left
                    node.left = right
                    return generate_lt_expr(emitter, node)
                
                case Operator.LE:
                    right = node.right
                    node.right = node.left
                    node.left = right
                    reg_lt = generate_lt_expr(emitter, node)
                    return generate_not_expr(emitter, reg_val=reg_lt)
                
                case Operator.GE:
                    reg_lt = generate_lt_expr(emitter, node)
                    return generate_not_expr(emitter, reg_val=reg_lt)
                
                case Operator.EQ: return generate_eq_expr(emitter, node)
                
                case Operator.NE:
                    reg_eq = generate_eq_expr(emitter, node)
                    return generate_not_expr(emitter, reg_val=reg_eq)
                
                case Operator.AND: 
                    reg = emitter.reg_manager.alloc_temp()
                    rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
                    generate_cond_and(emitter, node, None, rd)
                    emitter._write_result(reg, rd)
                    reg.zontype = ZonType(3, "bool")
                    return reg
                
                case Operator.OR:
                    reg = emitter.reg_manager.alloc_temp()
                    rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
                    generate_cond_or(emitter, node, None, rd)
                    emitter._write_result(reg, rd)
                    reg.zontype = ZonType(3, "bool")
                    return reg
                
                case Operator.BAND:
                    return generate_and_expr(emitter, node)
                
                case Operator.BXOR:
                    reg = generate_xor_expr(emitter, node)
                    return reg
                
                case Operator.BOR:
                    return generate_or_expr(emitter, node)
                
                case Operator.SL:
                    if isinstance(node.right, IntLiteral) and node.right.value >= -2048 and node.right.value <= 2047:
                        reg_left = generate_expr(emitter, node.left)
                        src_l = emitter._read_operand(reg_right, emitter.REG_SCRATCH_X)
                        reg = emitter.reg_manager.alloc_temp()
                        rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
                        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.SLL_SLLI, rd, src_l, node.right.value)
                        emitter._write_result(reg, rd)
                        emitter.reg_manager.free_temp(reg_left)
                        return reg
                    
                    reg_left = generate_expr(emitter, node.left)
                    reg_right = generate_expr(emitter, node.right)
                    src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
                    src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_X else emitter.REG_SCRATCH_X)
                    reg = emitter.reg_manager.alloc_temp()
                    rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
                    emit_r_type(emitter, OpCode.OP, F3_ALU.SLL_SLLI, F7.STANDARD, rd, src_l, src_r)
                    emitter._write_result(reg, rd)
                    emitter.reg_manager.free_temp(reg_left)
                    emitter.reg_manager.free_temp(reg_right)
                    return reg
                
                case Operator.SR:
                    if isinstance(node.right, IntLiteral):
                        reg_left = generate_expr(emitter, node.left)
                        src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
                        reg = emitter.reg_manager.alloc_temp()
                        rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
                        shamt = node.right.value & 0x3F 

                        imm_preparado = 0x400 | shamt  
                        
                        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.SRL_SRLI_SRA_SRAI, rd, src_l, imm_preparado)
                        emitter._write_result(reg, rd)
                        emitter.reg_manager.free_temp(reg_left)
                        return reg
                    
                    reg_left = generate_expr(emitter, node.left)
                    reg_right = generate_expr(emitter, node.right)
                    src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
                    src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_X else emitter.REG_SCRATCH_X)
                    reg = emitter.reg_manager.alloc_temp()
                    rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
                    emit_r_type(emitter, OpCode.OP, F3_ALU.SRL_SRLI_SRA_SRAI, F7.ALT, rd, src_l, src_r)
                    emitter._write_result(reg, rd)
                    emitter.reg_manager.free_temp(reg_left)
                    emitter.reg_manager.free_temp(reg_right)
                    return reg
                
                case Operator.BNAND:
                    reg = generate_and_expr(emitter, node, negate=True)
                    return reg
                
                case Operator.BNOR:
                    reg = generate_or_expr(emitter, node, negate=True)
                    return reg_not
                
                case Operator.BXNOR:
                    reg = generate_xor_expr(emitter, node, negate=True)
                    return reg_not

        case UnaryExpr():
            match node.operator:
                case Operator.NEG:
                    reg_value = generate_expr(emitter, node.value)
                    src_v = emitter._read_operand(reg_value, emitter.REG_SCRATCH_X if reg_value.regt == RegT.X else emitter.REG_SCRATCH_F)
                    if reg_value.regt == RegT.X:
                        reg = emitter.reg_manager.alloc_temp()
                        rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
                        opcode = OpCode.OP_32 if is_w else OpCode.OP
                        emit_r_type(emitter, opcode, F3_ALU.ADD_SUB, F7.ALT, reg, 0x0, src_v)
                        emitter._write_result(reg, rd)
                        
                    elif reg_value.regt == RegT.F:
                        reg = emitter.reg_manager.alloc_ftemp()
                        rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_F)
                        emit_f_type(emitter, OpCode.OP_F, reg, src_v, src_v, 0x01, F7.FSGNJ_D)
                        emitter._write_result(reg, rd)
                        
                    emitter.reg_manager.free_temp(reg_value)
                    return reg

                case Operator.NOT:
                    return generate_not_expr(emitter, node)
                
                case Operator.BNOT:
                    return generate_not_expr(emitter, node, bit=True)

        case VariableExpr():
            var = emitter.symbol_table.resolve(node.name)
            if var.is_global:
                if var.zontype.num in [1, 3, 4, 6]:
                    reg_temp = emitter.reg_manager.alloc_temp()
                    reg_temp_s = emitter._read_operand(reg_temp, emitter.REG_SCRATCH_X)
                    emit_i_type(emitter, OpCode.L, F3_L.LD, reg_temp_s, 3, var.offset_global)
                    return ZonVar(reg_temp_s, RegT.X, var.zontype)
                elif var.zontype.num in [2, 7]:
                    reg_temp = emitter.reg_manager.alloc_ftemp()
                    reg_temp_s = emitter._read_operand(reg_temp, emitter.REG_SCRATCH_F)
                    emit_i_type(emitter, OpCode.FL, F3_FL.FLD, reg_temp_s, 3, var.offset_global)
                    return ZonVar(reg_temp_s, RegT.F, var.zontype)
            return var

        case BlockExpr():
            from .stmt_gen import generate_stmt
            exit_label = emitter.label_manager.create()
            emitter.value_block_exits.append(exit_label)
            emitter.symbol_table.enter_scope()

            regt = None
            zontype = None
            for stmt in node.stmts:
                if isinstance(stmt, GiveStmt):
                    regt, zontype = generate_stmt(emitter, stmt)
                else:
                    generate_stmt(emitter, stmt)

            emitter.symbol_table.exit_scope()
            emitter.label_manager.place_label(exit_label, emitter.get_pc())
            emitter.value_block_exits.pop()
            return ZonVar(10, regt, zontype)

        case IfForm():
            exit_label = emitter.label_manager.create()
            result_reg = emitter.reg_manager.alloc_temp()
            rd = emitter._resolve_dest(result_reg, emitter.REG_SCRATCH_X)

            if node.if_branch:
                false_label = emitter.label_manager.create()
                generate_cond(emitter, false_label, node.if_branch.cond)
                value = generate_expr(emitter, node.if_branch.block)
                src = emitter._read_operand(value, emitter.REG_SCRATCH_X if value.regt == RegT.X else emitter.REG_SCRATCH_F)
                if value.regt == RegT.X:
                    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, rd, src, 0)
                else:
                    emit_f_type(emitter, OpCode.OP_F, rd, src, src, 0x00, F7.FSGNJ_D)
                    
                result_reg.zontype = value.zontype
                emit_jump(emitter, exit_label)
                emitter.label_manager.place_label(false_label, emitter.get_pc())

            if node.elif_branches:
                for branch in node.elif_branches:
                    if branch is None:
                        continue
                    
                    elif_label = emitter.label_manager.create()
                    generate_cond(emitter, elif_label, branch.cond)
                    value = generate_expr(emitter, branch.block)
                    src = emitter._read_operand(value, emitter.REG_SCRATCH_X if value.regt == RegT.X else emitter.REG_SCRATCH_F)
                    if value.regt == RegT.X:
                        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, rd, src, 0)
                    else:
                        emit_f_type(emitter, OpCode.OP_F, rd, src, src, 0x00, F7.FSGNJ_D)
                    emit_jump(emitter, exit_label)
                    emitter.label_manager.place_label(elif_label, emitter.get_pc())

            if node.else_branch:
                value = generate_expr(emitter, node.else_branch.block)
                src = emitter._read_operand(value, emitter.REG_SCRATCH_X if value.regt == RegT.X else emitter.REG_SCRATCH_F)
                if value.regt == RegT.X:
                    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, rd, src, 0)
                else:
                    emit_f_type(emitter, OpCode.OP_F, rd, src, src, 0x00, F7.FSGNJ_D)

            emitter.label_manager.place_label(exit_label, emitter.get_pc())
            emitter._write_result(result_reg, rd)
            return result_reg

        case CallFunc():
            if node.name == "alloc":
                return emit_ecall_alloc_load(emitter, node, 0)
            elif node.name == "load":
                return emit_ecall_alloc_load(emitter, node, 1)

            if node.params is not None:
                param_counter = 10
                fparam_counter = 10
                for param in node.params:
                    reg = generate_expr(emitter, param)
                    src_reg = emitter._read_operand(reg, emitter.REG_SCRATCH_X if reg.regt == RegT.X else emitter.REG_SCRATCH_F)
                    if reg.regt == RegT.X:
                        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, param_counter, src_reg, 0)
                        param_counter += 1
                    else:
                        emit_f_type(emitter, OpCode.OP_F, fparam_counter, src_reg, src_reg, 0x0, F7.FSGNJ_D)
                        fparam_counter += 1
                        
                    emitter.reg_manager.free_temp(reg)
                
            current_used_temps, current_used_ftemps = emitter.reg_manager.get_active_regs()
            current_offset = emitter.offset_stack[-1][0]
            for reg_num in current_used_temps:
                emit_s(emitter, OpCode.OP_S, F3_S.SD, 2, reg_num, current_offset)
                current_offset -= 8
                
            for reg_num in current_used_ftemps:
                emit_s(emitter, OpCode.OP_FS, F3_FS.FSD, 2, reg_num, current_offset)
                current_offset -= 8
                
            emit_jump(emitter.functions[node.name][0], rd=1)
            
            current_offset = emitter.offset_stack[-1][0]
            for reg_num in current_used_temps:
                emit_i_type(emitter, OpCode.L, F3_L.LD, reg_num, 2, current_offset)
                current_offset -= 8
                
            for reg_num in current_used_ftemps:
                emit_i_type(emitter, OpCode.FL, F3_FL.FLD, reg_num, 2, current_offset)
                current_offset -= 8
            
            return_type = emitter.functions[node.name][1]
            
            if return_type.num in [1, 3, 4, 6]:
                result = emitter.reg_manager.alloc_temp()
                rd = emitter._resolve_dest(result, emitter.REG_SCRATCH_X)
                emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, rd, 10, 0)
                emitter._write_result(result, rd)
                result.zontype = return_type
                return result
            
            elif return_type.num in [2, 7]:
                result = emitter.reg_manager.alloc_ftemp()
                rd = emitter._resolve_dest(result, emitter.REG_SCRATCH_F)
                emit_f_type(emitter, OpCode.OP_F, rd, 10, 10, 0x0, F7.FSGNJ_D)
                emitter._write_result(result, rd)
                return result
            
            else:
                return ZonVar(10, None, return_type)

    return None

def generate_lt_expr(emitter, node):
    if isinstance(node.right, IntLiteral):
        reg_left = generate_expr(emitter, node.left)
        src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
        reg = emitter.reg_manager.alloc_temp()
        rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.SLT_SLTI, rd, src_l, node.right.value)
        emitter.reg_manager.free_temp(reg_left)
        emitter._write_result(reg, rd)
        return reg
    
    reg_left = generate_expr(emitter, node.left)
    reg_right = generate_expr(emitter, node.right)
    reg = emitter.reg_manager.alloc_temp()
    if reg_left.regt == RegT.X:
        src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
        src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_X else emitter.REG_SCRATCH_X)
        rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
        emit_r_type(emitter, OpCode.OP, F3_ALU.SLT_SLTI, F7.STANDARD, rd, src_l, src_r)
        emitter._write_result(reg, rd)
        
    elif reg_left.regt == RegT.F:
        src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_F)
        src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_F else emitter.REG_SCRATCH_F)
        rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_F)
        emit_f_type(emitter, OpCode.OP_F, rd, src_l, src_r, 0x01, F7.FCOMP_S)
        emitter._write_result(reg, rd)
        
    emitter.reg_manager.free_temp(reg_left)
    emitter.reg_manager.free_temp(reg_right)
    return reg

def generate_eq_expr(emitter, node):
    if isinstance(node.left, (IntLiteral, BoolLiteral)):
        reg_right = generate_expr(emitter, node.right)
        src_r = emitter._read_operand(reg_right, emitter.REG_SCRATCH_X)
        reg_xor = emitter.reg_manager.alloc_temp()
        rd_xor = emitter._resolve_dest(reg_xor, emitter.REG_SCRATCH_X)
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.XOR_XORI, rd_xor, src_r, node.left.value)
        emitter._write_result(reg_xor, rd_xor)
        emitter.reg_manager.free_temp(reg_right)
        reg = emitter.reg_manager.alloc_temp()
        rd = emitter._resolve_dest(reg_xor, emitter.REG_SCRATCH_X)
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.SLTU_SLTIU, rd, reg_xor, 1)
        emitter.reg_manager.free_temp(reg_xor)
        emitter._write_result(reg, rd)
        
        return reg
    
    if isinstance(node.right, (IntLiteral, BoolLiteral)):
        reg_left = generate_expr(emitter, node.left)
        src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
        reg_xor = emitter.reg_manager.alloc_temp()
        rd_xor = emitter._resolve_dest(reg_xor, emitter.REG_SCRATCH_X)
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.XOR_XORI, rd_xor, src_l, node.right.value)
        emitter._write_result(reg_xor, rd_xor)
        emitter.reg_manager.free_temp(reg_left)
        reg = emitter.reg_manager.alloc_temp()
        rd = emitter._resolve_dest(reg_xor, emitter.REG_SCRATCH_X)
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.SLTU_SLTIU, rd, reg_xor, 1)
        emitter.reg_manager.free_temp(reg_xor)
        emitter._write_result(reg, rd)
        
        return reg
    
    reg_left = generate_expr(emitter, node.left)
    reg_right = generate_expr(emitter, node.right)
    if reg_left.regt == RegT.X:
        src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
        src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_X else emitter.REG_SCRATCH_X)
        reg_xor = emitter.reg_manager.alloc_temp()
        rd_xor = emitter._resolve_dest(reg_xor, emitter.REG_SCRATCH_X)
        emit_r_type(emitter, OpCode.OP, F3_ALU.XOR_XORI, F7.STANDARD, rd_xor, src_l, src_r)
        emitter._write_result(reg_xor, rd_xor)
        emitter.reg_manager.free_temp(reg_left)
        emitter.reg_manager.free_temp(reg_right)
        reg = emitter.reg_manager.alloc_temp()
        rd = emitter._resolve_dest(reg_xor, emitter.REG_SCRATCH_X)
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.SLTU_SLTIU, rd, reg_xor, 1)
        emitter.reg_manager.free_temp(reg_xor)
        emitter._write_result(reg, rd)
        return reg
    
    elif reg_left.regt == RegT.F:
        src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_F)
        src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_F else emitter.REG_SCRATCH_F)
        reg = emitter.reg_manager.alloc_temp()
        rd = emitter._resolve_dest(reg_xor, emitter.REG_SCRATCH_F)
        emit_f_type(emitter, OpCode.OP_F, rd, src_l, src_r, 0x02, F7.FCOMP_S)
        emitter.reg_manager.free_temp(reg_left)
        emitter.reg_manager.free_temp(reg_right)
        emitter._write_result(reg, rd)
        return reg
    pass

def generate_not_expr(emitter, node=None, reg_val=None, bit: bool = False):
    if reg_val is not None:
        src_v = emitter._read_operand(reg_val, emitter.REG_SCRATCH_X)
        reg = emitter.reg_manager.alloc_temp()
        rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.XOR_XORI, rd, src_v, -1 if bit else 1)
        emitter.reg_manager.free_temp(reg_val)
        emitter._write_result(reg, rd)
        return reg
    
    reg_value = generate_expr(emitter, node.value)
    src_v = emitter._read_operand(reg_value, emitter.REG_SCRATCH_X)
    reg = emitter.reg_manager.alloc_temp()
    rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.XOR_XORI, rd, src_v, -1 if bit else 1)
    emitter.reg_manager.free_temp(reg_value)
    emitter._write_result(reg, rd)
    return reg

def emit_eq_str(emitter, node):
    reg_left = generate_expr(emitter, node.left)
    reg_right = generate_expr(emitter, node.right)
    src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
    src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_X else emitter.REG_SCRATCH_X)
    reg = emitter.reg_manager.alloc_temp()
    rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
    emit_r_type(emitter, OpCode.OP_STR, F3_STR.CMP, F7_STR.STANDARD, rd, src_l, src_r)
    emitter.reg_manager.free_temp(reg_right)
    emitter.reg_manager.free_temp(reg_left)
    
    return reg

def generate_cond(emitter, label, node):
    match node:
        case CastExpr():
            reg_value = generate_expr(emitter, node.value)
            src_v = emitter._read_operand(reg_value, emitter.REG_SCRATCH_X if reg_value.regt == RegT.X else emitter.REG_SCRATCH_F)
            reg = emitter.reg_manager.alloc_temp()
            rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
            emit_r_type(emitter, OpCode.OP, F3_ALU.SLTU_SLTIU, F7.STANDARD, rd, 0, src_v)
            emitter._write_result(reg, rd)
            emit_b_type(emitter, OpCode.OP_B, F3_B.BEQ, reg, 0x0, label)
            emitter.reg_manager.free_temp(reg_value)
            emitter.reg_manager.free_temp(reg)
            
        
        case BoolLiteral():
            reg_b = emitter.reg_manager.alloc_temp()
            emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, reg_b, 0x0, node.value)
            emit_b_type(emitter, OpCode.OP_B, F3_B.BEQ, reg_b, 0x0, label)
            emitter.reg_manager.free_temp(reg_b)
            
        case BinaryExpr():
            match node.operator:
                case Operator.NE:
                    reg_left = generate_expr(emitter, node.left)
                    reg_right = generate_expr(emitter, node.right)
                    if reg_left.regt == RegT.X:
                        src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
                        src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_X else emitter.REG_SCRATCH_X)
                        emit_b_type(emitter, OpCode.OP_B, F3_B.BEQ, src_l, src_r, label)
                        
                    elif reg_left.regt == RegT.F:
                        src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_F)
                        src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_F else emitter.REG_SCRATCH_F)
                        reg_x = emitter.reg_manager.alloc_temp()
                        emit_f_type(emitter, OpCode.OP_F, reg_x, src_l, src_r, 0x02, F7.FCOMP_S)
                        emit_b_type(emitter, OpCode.OP_B, F3_B.BEQ, 0x0, reg_x, label)
                        emitter.reg_manager.free_temp(reg_x)
                        
                    emitter.reg_manager.free_temp(reg_left)
                    emitter.reg_manager.free_temp(reg_right)
                    
                case Operator.EQ:
                    reg_left = generate_expr(emitter, node.left)
                    reg_right = generate_expr(emitter, node.right)
                    if reg_left.regt == RegT.X:
                        src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
                        src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_X else emitter.REG_SCRATCH_X)
                        emit_b_type(emitter, OpCode.OP_B, F3_B.BNE, src_l, src_r, label)
                        
                    elif reg_left.regt == RegT.F:
                        src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_F)
                        src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_F else emitter.REG_SCRATCH_F)
                        reg_x = emitter.reg_manager.alloc_temp()
                        emit_f_type(emitter, OpCode.OP_F, reg_x, src_l, src_r, 0x02, F7.FCOMP_S)
                        emit_b_type(emitter, OpCode.OP_B, F3_B.BEQ, 0x0, reg_x, label)
                        emitter.reg_manager.free_temp(reg_x)
                        
                    emitter.reg_manager.free_temp(reg_left)
                    emitter.reg_manager.free_temp(reg_right)
                    pass
                
                case Operator.LT:
                    generate_cond_lt(emitter, label, node)
                    
                case Operator.GT:
                    right = node.right
                    node.right = node.left
                    node.left = right
                    generate_cond_lt(emitter, label, node)
                    
                case Operator.LE:
                    right = node.right
                    node.right = node.left
                    node.left = right
                    generate_cond_ge(emitter, label, node)
                    
                case Operator.GE:
                    generate_cond_ge(emitter, label, node)
                    
                case Operator.AND:
                    generate_cond_and(emitter, node, label)
                    
                case Operator.OR:
                    generate_cond_or(emitter, node, label)
                    
        case VariableExpr():
            var = emitter.symbol_table.resolve(node.name)
            src_v = emitter._read_operand(var, emitter.REG_SCRATCH_X)
            emit_b_type(emitter, OpCode.OP_B, F3_B.BEQ, src_v, 0x0, label)

def generate_cond_lt(emitter, label, node):
    reg_left = generate_expr(emitter, node.left)
    reg_right = generate_expr(emitter, node.right)
    if reg_left.regt == RegT.X:
        src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
        src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_X else emitter.REG_SCRATCH_X)
        emit_b_type(emitter, OpCode.OP_B, F3_B.BGE, src_l, src_r, label)
    elif reg_left.regt == RegT.F:
        src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_F)
        src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_F else emitter.REG_SCRATCH_F)
        reg_x = emitter.reg_manager.alloc_temp()
        emit_f_type(emitter, OpCode.OP_F, reg_x, src_l, src_r, 0x01, F7.FCOMP_S)
        emit_b_type(emitter, OpCode.OP_B, F3_B.BEQ, 0x0, reg_x, label)
        emitter.reg_manager.free_temp(reg_x)
    emitter.reg_manager.free_temp(reg_left)
    emitter.reg_manager.free_temp(reg_right)

def generate_cond_ge(emitter, label, node):
    reg_left = generate_expr(emitter, node.left)
    reg_right = generate_expr(emitter, node.right)
    if reg_left.regt == RegT.X:
        src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
        src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_X else emitter.REG_SCRATCH_X)
        emit_b_type(emitter, OpCode.OP_B, F3_B.BLT, src_l, src_r, label)
    elif reg_left.regt == RegT.F:
        src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_F)
        src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_F else emitter.REG_SCRATCH_F)
        reg_x = emitter.reg_manager.alloc_temp()
        emit_f_type(emitter, OpCode.OP_F, reg_x, src_r, src_l, 0x00, F7.FCOMP_S)
        emit_b_type(emitter, OpCode.OP_B, F3_B.BEQ, 0x0, reg_x, label)
        emitter.reg_manager.free_temp(reg_x)
    emitter.reg_manager.free_temp(reg_left)
    emitter.reg_manager.free_temp(reg_right)

def generate_cond_and(emitter, node, label=None, reg_x=None):
    reg_left = generate_expr(emitter, node.left)
    src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
    false_l = emitter.label_manager.create()
    exit_l = emitter.label_manager.create()
    if label is None:
        emit_b_type(emitter, OpCode.OP_B, F3_B.BEQ, src_l, 0x0, false_l)
    else:
        emit_b_type(emitter, OpCode.OP_B, F3_B.BEQ, src_l, 0x0, label)
    emitter.reg_manager.free_temp(reg_left)
    reg_right = generate_expr(emitter, node.right)
    src_r = emitter._read_operand(reg_right, emitter.REG_SCRATCH_X)
    if label is None:
        emit_b_type(emitter, OpCode.OP_B, F3_B.BEQ, src_r, 0x0, false_l)
    else:
        emit_b_type(emitter, OpCode.OP_B, F3_B.BEQ, src_r, 0x0, label)
    emitter.reg_manager.free_temp(reg_right)
    if label is None:
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, reg_x, 0x0, 1)
        emit_jump(emitter, exit_l)
        emitter.label_manager.place_label(false_l, emitter.get_pc())
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, reg_x, 0x0, 0)
        emitter.label_manager.place_label(exit_l, emitter.get_pc())

def generate_cond_or(emitter, node, label=None, reg_x=None):
    reg_left = generate_expr(emitter, node.left)
    src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
    true_l = emitter.label_manager.create()
    exit_l = emitter.label_manager.create()
    if label is None:
        emit_b_type(emitter, OpCode.OP_B, F3_B.BNE, src_l, 0x0, true_l)
    else:
        emit_b_type(emitter, OpCode.OP_B, F3_B.BNE, src_l, 0x0, label)
    emitter.reg_manager.free_temp(reg_left)
    reg_right = generate_expr(emitter, node.right)
    src_r = emitter._read_operand(reg_right, emitter.REG_SCRATCH_X)
    if label is None:
        emit_b_type(emitter, OpCode.OP_B, F3_B.BNE, src_r, 0x0, true_l)
    else:
        emit_b_type(emitter, OpCode.OP_B, F3_B.BNE, src_r, 0x0, label)
    emitter.reg_manager.free_temp(reg_right)
    if label is None:
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, reg_x, 0x0, 0)
        emit_jump(emitter, exit_l)
        emitter.label_manager.place_label(true_l, emitter.get_pc())
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, reg_x, 0x0, 1)
        emitter.label_manager.place_label(exit_l, emitter.get_pc())

def generate_and_expr(emitter, node, negate = False):
    if not negate:
        if isinstance(node.left, (VariableExpr, IntLiteral)) or isinstance(node.right, (VariableExpr, IntLiteral)):
            if isinstance(node.left, IntLiteral) and node.left.value >= -2048 and node.left.value <= 2047:
                reg_right = generate_expr(emitter, node.right)
                src_r = emitter._read_operand(reg_right, emitter.REG_SCRATCH_X)
                reg = emitter.reg_manager.alloc_temp()
                rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
                emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.AND_ANDI, reg, src_r, node.left.value)
                emitter.reg_manager.free_temp(reg_right)
                emitter._write_result(reg, rd)

                return reg
            
            if isinstance(node.right, IntLiteral) and node.right.value >= -2048 and node.right.value <= 2047:
                reg_left = generate_expr(emitter, node.left)
                src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
                reg = emitter.reg_manager.alloc_temp()
                rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
                emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.AND_ANDI, reg, src_l, node.right.value)
                emitter.reg_manager.free_temp(reg_left)
                emitter._write_result(reg, rd)

                return reg
            
    f7 = F7.ALT if negate else F7.STANDARD
        
    reg_left = generate_expr(emitter, node.left)
    reg_right = generate_expr(emitter, node.right)
    src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
    src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_X else emitter.REG_SCRATCH_X)
    reg = emitter.reg_manager.alloc_temp()
    rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
    emit_r_type(emitter, OpCode.OP, F3_ALU.AND_ANDI, f7, rd, src_l, src_r)
    emitter._write_result(reg, rd)
    emitter.reg_manager.free_temp(reg_left)
    emitter.reg_manager.free_temp(reg_right)
    
    return reg
    
def generate_or_expr(emitter, node, negate = False):
    if not negate:
        if isinstance(node.left, (VariableExpr, IntLiteral)) or isinstance(node.right, (VariableExpr, IntLiteral)):
            if isinstance(node.left, IntLiteral) and node.left.value >= -2048 and node.left.value <= 2047:
                reg_right = generate_expr(emitter, node.right)
                src_r = emitter._read_operand(reg_right, emitter.REG_SCRATCH_X)
                reg = emitter.reg_manager.alloc_temp()
                rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
                emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.OR_ORI, rd, src_r, node.left.value)
                emitter.reg_manager.free_temp(reg_right)
                emitter._write_result(reg, rd)

                return reg
            
            if isinstance(node.right, IntLiteral) and node.right.value >= -2048 and node.right.value <= 2047:
                reg_left = generate_expr(emitter, node.left)
                src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
                reg = emitter.reg_manager.alloc_temp()
                rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
                emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.OR_ORI, rd, src_l, node.right.value)
                emitter.reg_manager.free_temp(reg_left)
                emitter._write_result(reg, rd)

                return reg
            
    f7 = F7.ALT if negate else F7.STANDARD
        
    reg_left = generate_expr(emitter, node.left)
    reg_right = generate_expr(emitter, node.right)
    src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
    src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_X else emitter.REG_SCRATCH_X)
    reg = emitter.reg_manager.alloc_temp()
    rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
    emit_r_type(emitter, OpCode.OP, F3_ALU.OR_ORI, f7, rd, src_l, src_r)
    emitter._write_result(reg, rd)

    emitter.reg_manager.free_temp(reg_left)
    emitter.reg_manager.free_temp(reg_right)
    return reg

def generate_xor_expr(emitter, node, negate = False):
    if not negate: 
        if isinstance(node.left, IntLiteral) and node.left.value >= -2048 and node.left.value <= 2047:
            reg_right = generate_expr(emitter, node.right)
            src_r = emitter._read_operand(reg_right,emitter.REG_SCRATCH_X)
            reg = emitter.reg_manager.alloc_temp()
            rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
            emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.XOR_XORI, rd, src_r, node.left.value)
            emitter._write_result(reg, rd)
            emitter.reg_manager.free_temp(reg_right)
            return reg
        
        elif isinstance(node.right, IntLiteral) and node.right.value >= -2048 and node.right.value <= 2047:
            reg_left = generate_expr(emitter, node.left)
            src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
            reg = emitter.reg_manager.alloc_temp()
            rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
            emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.XOR_XORI, rd, src_l, node.right.value)
            emitter._write_result(reg, rd)
            emitter.reg_manager.free_temp(reg_left)
            return reg
        
    f7 = F7.ALT if negate else F7.STANDARD
    
    reg_left = generate_expr(emitter, node.left)
    reg_right = generate_expr(emitter, node.right)
    src_l = emitter._read_operand(reg_left, emitter.REG_SCRATCH_X)
    src_r = emitter._read_operand(reg_right, 30 if src_l == emitter.REG_SCRATCH_X else emitter.REG_SCRATCH_X)
    reg = emitter.reg_manager.alloc_temp()
    rd = emitter._resolve_dest(reg, emitter.REG_SCRATCH_X)
    emit_r_type(emitter, OpCode.OP, F3_ALU.XOR_XORI, f7, rd, src_l, src_r)
    emitter._write_result(reg, rd)
    emitter.reg_manager.free_temp(reg_left)
    emitter.reg_manager.free_temp(reg_right)
    return reg
