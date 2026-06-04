# bytecodegen/stmt_gen.py
from .instruction import (
    emit_i_type, emit_s, emit_f_type, emit_jump, emit_ecall
)
from .expr_gen import generate_expr, generate_cond
from .func_gen import emit_ecall_store
from .rodata import generate_literal_num, generate_literal_f
from .bytecodescope import RegT, ZonVar
from zonc.zonast import *
from .opcode import *

def generate_stmt(emitter, node):
    match node:
        case DeclarationStmt():
            if not emitter.symbol_table.exists_here(node.name):
                is_float = node.type.num in [2, 7]
                saved_list = emitter.symbol_table.fsaved if is_float else emitter.symbol_table.saved
                regt = RegT.F if is_float else RegT.X
                used_regs = {v.reg for s in emitter.symbol_table.scopes for v in s.values() if v.reg is not None and v.regt == regt}
                free_reg = next((r for r in saved_list if r not in used_regs), None)
                
                if free_reg is not None:
                    zonvar = ZonVar(free_reg, regt, node.type)
                else:
                    bytes_needed = emitter.offset_stack[-1][1]
                    current_offset = emitter.offset_stack[-1][0]
                    fp_offset = current_offset - bytes_needed
                    zonvar = ZonVar(None, regt, node.type, offset_stack=fp_offset)
                    
                emitter.symbol_table.scopes[-1][node.name] = zonvar

        case AssignmentStmt():
            real_reg = emitter.symbol_table.resolve(node.name)
            
            if real_reg.is_global:
                reg_value = generate_expr(emitter, node.value, real_reg.zontype.num)
                src_reg = emitter._read_operand(reg_value, emitter.REG_SCRATCH_X if reg_value.regt == RegT.X else emitter.REG_SCRATCH_F)
                
                if real_reg.zontype.num in [1, 3, 4, 6]:
                    emit_s(emitter, OpCode.OP_S, F3_S.SD, 3, src_reg, real_reg.offset_global)
                elif real_reg.zontype.num in [2, 7]:
                    emit_s(emitter, OpCode.OP_FS, F3_FS.FSD, 3, src_reg, real_reg.offset_global)
                    
                emitter.reg_manager.free_temp(reg_value)
                return

            if real_reg.reg is not None:
                if isinstance(node.value, (IntLiteral, BoolLiteral)):
                    generate_literal_num(emitter, node.value.value, real_reg.reg)
                    return
                
                elif isinstance(node.value, FloatLiteral):
                    generate_literal_f(emitter, node.value.value, real_reg.reg)
                    return
                
                reg_value = generate_expr(emitter, node.value, real_reg.zontype.num)
                src_reg = emitter._read_operand(reg_value, emitter.REG_SCRATCH_X if reg_value.regt == RegT.X else emitter.REG_SCRATCH_F)
                
                if reg_value.regt == RegT.X:
                    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, real_reg.reg, src_reg, 0)
                elif reg_value.regt == RegT.F:
                    emit_f_type(emitter, OpCode.OP_F, real_reg.reg, src_reg, src_reg, 0x00, F7.FSGNJ_D)
                    
                emitter.reg_manager.free_temp(reg_value)
            else:
                if isinstance(node.value, (IntLiteral, BoolLiteral)):
                    scratch = emitter.REG_SCRATCH_X
                    generate_literal_num(emitter, node.value.value, scratch)
                    emitter._write_result(real_reg, scratch)
                    return
                
                elif isinstance(node.value, FloatLiteral):
                    scratch = emitter.REG_SCRATCH_F
                    generate_literal_f(emitter, node.value.value, scratch)
                    emitter._write_result(real_reg, scratch)
                    return
                
                reg_value = generate_expr(emitter, node.value, real_reg.zontype.num)
                src_reg = emitter._read_operand(reg_value, emitter.REG_SCRATCH_X if reg_value.regt == RegT.X else emitter.REG_SCRATCH_F)
                emitter._write_result(real_reg, src_reg)
                emitter.reg_manager.free_temp(reg_value)

        case InitializationStmt():
            var_name = node.decl_stmt.name
            var_type = node.decl_stmt.type
            var_num_type = var_type.num
            is_float = var_num_type in [2, 7]
            regt = RegT.F if is_float else RegT.X
            val_node = node.assign_stmt.value

            if isinstance(val_node, (IntLiteral, BoolLiteral)):
                temp_reg = emitter.REG_SCRATCH_X
                generate_literal_num(emitter, val_node.value, temp_reg)
                is_literal = True
                
            elif isinstance(val_node, FloatLiteral):
                temp_reg = emitter.REG_SCRATCH_F
                generate_literal_f(emitter, val_node.value, temp_reg)
                is_literal = True
                
            elif isinstance(val_node, StringLiteral):
                str_zv = generate_expr(emitter, val_node)
                temp_reg = emitter._read_operand(str_zv, emitter.REG_SCRATCH_X)
                is_literal = True
                emitter.reg_manager.free_temp(str_zv)
                
            else:
                reg_value = generate_expr(emitter, val_node, var_num_type)
                temp_reg = emitter._read_operand(reg_value, emitter.REG_SCRATCH_X if reg_value.regt == RegT.X else emitter.REG_SCRATCH_F)
                is_literal = False

            if emitter.symbol_table.exists_here(var_name):
                real_reg = emitter.symbol_table.resolve(var_name)
            else:
                used_regs = {v.reg for s in emitter.symbol_table.scopes for v in s.values() if v.reg is not None and v.regt == regt}
                saved_list = emitter.symbol_table.fsaved if is_float else emitter.symbol_table.saved
                free_reg = next((r for r in saved_list if r not in used_regs), None)
                
                if free_reg is not None:
                    real_reg = ZonVar(free_reg, regt, var_type)
                else:
                    current_offset = emitter.offset_stack[-1][0]
                    emitter.offset_stack[-1][0] -= 8
                    bytes_needed = emitter.offset_stack[-1][1]
                    fp_offset = current_offset - bytes_needed
                    real_reg = ZonVar(None, regt, var_type, offset_stack=fp_offset)
                    
                emitter.symbol_table.scopes[-1][var_name] = real_reg

            if real_reg.reg is not None:
                if regt == RegT.X:
                    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, real_reg.reg, temp_reg, 0)
                elif regt == RegT.F:
                    emit_f_type(emitter, OpCode.OP_F, real_reg.reg, temp_reg, temp_reg, 0x00, F7.FSGNJ_D)
            else:
                emitter._write_result(real_reg, temp_reg)

            if not is_literal:
                emitter.reg_manager.free_temp(reg_value)

        case CallFunc():
            if node.name in ["print", "println"]:
                if node.params is not None:
                    for param in node.params:
                        if isinstance(param, BoolLiteral):
                            emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 10, 0x0, param.value)
                            emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0x0, -3)
                            emit_ecall(emitter)
                            
                        elif isinstance(param, IntLiteral):
                            generate_literal_num(emitter, param.value, 10)
                            emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0x0, -1)
                            emit_ecall(emitter)
                        elif isinstance(param, FloatLiteral):
                            generate_literal_f(emitter, param.value, 10)
                            emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0x0, -2)
                            emit_ecall(emitter)
                            
                        elif isinstance(param, StringLiteral):
                            str_var = generate_expr(emitter, param)
                            src_reg = emitter._read_operand(str_var, emitter.REG_SCRATCH_X)
                            emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 10, src_reg, 0)
                            emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -4)
                            emit_ecall(emitter)
                            emitter.reg_manager.free_temp(str_var)
                            
                        else:
                            reg_param = generate_expr(emitter, param)
                            src_reg = emitter._read_operand(reg_param, emitter.REG_SCRATCH_X if reg_param.regt == RegT.X else emitter.REG_SCRATCH_F)
                            
                            if reg_param.regt == RegT.X:
                                emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 10, src_reg, 0)
                                if reg_param.zontype.num == 3:
                                    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -3)
                                elif reg_param.zontype.num == 4:
                                    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -4)
                                else:
                                    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -1)
                                    
                            elif reg_param.regt == RegT.F:
                                emit_f_type(emitter, OpCode.OP_F, 10, src_reg, src_reg, 0x0, F7.FSGNJ_D)
                                emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -2)
                            emit_ecall(emitter)
                            emitter.reg_manager.free_temp(reg_param)
                            
                if node.name == "println":
                    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -5)
                    emit_ecall(emitter)
                    
            elif node.name == "store":
                emit_ecall_store(emitter, node)
                
            else:
                param_counter = 10
                fparam_counter = 10
                if node.params is not None:
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
                    
                emit_jump(emitter, emitter.functions[node.name][0], rd=1)
                current_offset = emitter.offset_stack[-1][0]
                
                for reg_num in current_used_temps:
                    emit_i_type(emitter, OpCode.L, F3_L.LD, reg_num, 2, current_offset)
                    current_offset -= 8
                    
                for reg_num in current_used_ftemps:
                    emit_i_type(emitter, OpCode.FL, F3_FL.FLD, reg_num, 2, current_offset)
                    current_offset -= 8

        case BlockExpr():
            exit_label = emitter.label_manager.create()
            emitter.value_block_exits.append(exit_label)
            emitter.symbol_table.enter_scope()
            
            for stmt in node.stmts:
                generate_stmt(emitter, stmt)
                
            emitter.symbol_table.exit_scope()
            emitter.label_manager.place_label(exit_label, emitter.get_pc())

        case IfForm():
            exit_label = emitter.label_manager.create()
            end_if_label = emitter.label_manager.create()
            
            if node.if_branch is not None:
                generate_cond(emitter, end_if_label, node.if_branch.cond)
                generate_stmt(emitter, node.if_branch.block)
                
                if node.elif_branches is None and node.else_branch is None:
                    emitter.label_manager.place_label(end_if_label, emitter.get_pc())
                    return
                
                elif node.elif_branches is None and node.else_branch is not None:
                    emit_jump(emitter, exit_label)
                    emitter.label_manager.place_label(end_if_label, emitter.get_pc())
                    
            if node.elif_branches is not None:
                if node.if_branch is not None:
                    emit_jump(emitter, exit_label)
                    emitter.label_manager.place_label(end_if_label, emitter.get_pc())
                    
                for i, branch in enumerate(node.elif_branches):
                    if branch is None:
                        continue
                    
                    end_elif_label = emitter.label_manager.create()
                    generate_cond(emitter, end_elif_label, branch.cond)
                    generate_stmt(emitter, branch.block)
                    
                    if (len(node.elif_branches) - 1) == i and node.else_branch is None:
                        emitter.label_manager.place_label(end_elif_label, emitter.get_pc())
                        emitter.label_manager.place_label(exit_label, emitter.get_pc())
                        return
                    
                    emit_jump(emitter, exit_label)
                    emitter.label_manager.place_label(end_elif_label, emitter.get_pc())
                    
            if node.else_branch is not None:
                generate_stmt(emitter, node.else_branch.block)
                
            emitter.label_manager.place_label(exit_label, emitter.get_pc())

        case WhileForm():
            exit_label = emitter.label_manager.create()
            cond_label = emitter.label_manager.create()
            emitter.loop_stack.append((exit_label, cond_label))
            emitter.label_manager.place_label(cond_label, emitter.get_pc())
            generate_cond(emitter, exit_label, node.condition_field)
            generate_stmt(emitter, node.block_expr)
            emit_jump(emitter, cond_label)
            emitter.label_manager.place_label(exit_label, emitter.get_pc())

        case ContinueStmt():
            emit_jump(emitter, emitter.loop_stack[-1][1])

        case BreakStmt():
            emit_jump(emitter, emitter.loop_stack[-1][0])

        case GiveStmt():
            reg_res = generate_expr(emitter, node.value)
            src_reg = emitter._read_operand(reg_res, emitter.REG_SCRATCH_X if reg_res.regt == RegT.X else emitter.REG_SCRATCH_F)
            
            if reg_res.regt == RegT.X:
                emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 10, src_reg, 0)
            else:
                emit_f_type(emitter, OpCode.OP_F, 10, src_reg, src_reg, 0x00, F7.FSGNJ_D)
                
            emitter.reg_manager.free_temp(reg_res)
            emit_jump(emitter, emitter.value_block_exits[-1])
            return reg_res.regt, reg_res.zontype

        case ReturnStmt():
            if node.value is None:
                emit_jump(emitter, emitter.functions[emitter.actual_func][2])
                return
            
            if isinstance(node.value, CallFunc) and node.value.name == emitter.actual_func:
                param_counter = 10
                fparam_counter = 10
                if node.value.params is not None:
                    for param in node.value.params:
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
                    
                emit_jump(emitter, emitter.functions[node.value.name][3], rd=1)
                current_offset = emitter.offset_stack[-1][0]
                
                for reg_num in current_used_temps:
                    emit_i_type(emitter, OpCode.L, F3_L.LD, reg_num, 2, current_offset)
                    current_offset -= 8
                    
                for reg_num in current_used_ftemps:
                    emit_i_type(emitter, OpCode.FL, F3_FL.FLD, reg_num, 2, current_offset)
                    current_offset -= 8
                    
                emit_jump(emitter, emitter.functions[emitter.actual_func][2])
                return
            
            reg_res = generate_expr(emitter, node.value)
            src_reg = emitter._read_operand(reg_res, emitter.REG_SCRATCH_X if reg_res.regt == RegT.X else emitter.REG_SCRATCH_F)
            if reg_res.regt == RegT.X:
                emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 10, src_reg, 0)
            else:
                emit_f_type(emitter, OpCode.OP_F, 10, src_reg, src_reg, 0x00, F7.FSGNJ_D)
                
            emitter.reg_manager.free_temp(reg_res)
            emit_jump(emitter, emitter.functions[emitter.actual_func][2])