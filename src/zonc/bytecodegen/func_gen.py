# bytecodegen/func_gen.py
from .instruction import (
    emit_i_type, emit_s, emit_f_type, emit_jalr, emit_ecall, emit_jump,
    emit_b_type, emit_j_type, emit_r_type, emit_u_type, emit_ecall_store,
    emit_ecall_alloc_load
)
from .expr_gen import generate_expr
from .stmt_gen import generate_stmt
from .rodata import generate_literal_num, generate_literal_f
from .linear_scan_register_allocation import LinearScanRegisterAllocation
from .opcode import *
from .bytecodescope import RegT, ZonVar
from zonc.zonast import ZonType, FuncForm, InitializationStmt, DeclarationStmt, IntLiteral, BoolLiteral, FloatLiteral, StringLiteral, CallFunc

def prologue(emitter, stmts, params=None):
    allocator = LinearScanRegisterAllocation(num_available_regs=7, num_available_fregs=12)
    bytes_needed, has_call, used_s, used_heap = allocator.analyze_function(stmts, params)
    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 2, 2, -bytes_needed)
    emit_s(emitter, OpCode.OP_S, F3_S.SD, 2, 8, bytes_needed - 8)
    
    if has_call:
        emit_s(emitter, OpCode.OP_S, F3_S.SD, 2, 1, bytes_needed - 16)
        
    current_offset = bytes_needed - 24
    
    for reg_num in used_s[0]:
        emit_s(emitter, OpCode.OP_S, F3_S.SD, 2, reg_num, current_offset)
        current_offset -= 8
        
    for reg_num in used_s[1]:
        emit_s(emitter, OpCode.OP_FS, F3_FS.FSD, 2, reg_num, current_offset)
        current_offset -= 8
        
    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 8, 2, bytes_needed)
    emitter.offset_stack.append([current_offset, bytes_needed, has_call, used_s, used_heap])
    
    if used_heap:
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -100)
        emit_ecall(emitter)

def epilogue(emitter):
    _, bytes_reserved, has_call, used_s, used_heap = emitter.offset_stack[-1]
    current_offset = bytes_reserved - 24
    
    for reg_num in used_s[0]:
        emit_i_type(emitter, OpCode.L, F3_L.LD, reg_num, 2, current_offset)
        current_offset -= 8
        
    for reg_num in used_s[1]:
        emit_i_type(emitter, OpCode.FL, F3_FL.FLD, reg_num, 2, current_offset)
        current_offset -= 8
        
    if has_call:
        emit_i_type(emitter, OpCode.L, F3_L.LD, 1, 2, bytes_reserved - 16)
        
    emit_i_type(emitter, OpCode.L, F3_L.LD, 8, 2, bytes_reserved - 8)
    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 2, 2, bytes_reserved)
    emitter.offset_stack.pop()
    
    if used_heap:
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -101)
        emit_ecall(emitter)

def generate_program_entry(emitter, program_stmts: list):
    has_main = any(isinstance(s, FuncForm) and s.name == "main" for s in program_stmts)
    _start_program = emitter.label_manager.create()
    
    if has_main:
        funciones_encontradas = [s for s in program_stmts if isinstance(s, FuncForm)]
        variables_globals = [s for s in program_stmts if isinstance(s, InitializationStmt)]
        
        _init_globals = emitter.label_manager.create()
        emitter.label_manager.place_label(_init_globals, emitter.get_pc())
        emitter.entry_point = _init_globals
        
        for node in variables_globals:
            var_name = node.name if isinstance(node, DeclarationStmt) else node.decl_stmt.name
            var_type = node.type if isinstance(node, DeclarationStmt) else node.decl_stmt.type
            
            if emitter.symbol_table.exists_here(var_name):
                real_reg = emitter.symbol_table.resolve(var_name)
            else:
                emitter.symbol_table.define_global(var_name, offset_global=emitter.data_section_size, zontype=var_type)
                emitter.data_section_size += 8
                real_reg = emitter.symbol_table.resolve(var_name)
            
            val_node = node.assign_stmt.value
            if isinstance(val_node, (IntLiteral, BoolLiteral)):
                temp_reg = emitter.reg_manager.alloc_temp()
                temp_reg_s = emitter._read_operand(temp_reg, emitter.REG_SCRATCH_X)
                generate_literal_num(emitter, val_node.value, temp_reg)
                emitter._write_result(temp_reg, temp_reg_s)
                is_literal = True
            elif isinstance(val_node, FloatLiteral):
                temp_reg = emitter.reg_manager.alloc_temp()
                temp_reg_s = emitter._read_operand(temp_reg, emitter.REG_SCRATCH_F)
                generate_literal_f(emitter, val_node.value, temp_reg)
                emitter._write_result(temp_reg, temp_reg_s)
                is_literal = True
            elif isinstance(val_node, StringLiteral):
                str_zv = generate_expr(emitter, val_node)
                temp_reg = emitter._read_operand(str_zv, emitter.REG_SCRATCH_X)
                is_literal = True
                emitter.reg_manager.free_temp(str_zv)
            else:
                reg_value = generate_expr(emitter, val_node, var_type.num)
                temp_reg = emitter._read_operand(reg_value, emitter.REG_SCRATCH_X if reg_value.regt == RegT.X else emitter.REG_SCRATCH_F)
                is_literal = False

            if var_type.num in [1, 3, 4, 6]:
                emit_s(emitter, OpCode.OP_S, F3_S.SD, 3, temp_reg, real_reg.offset_global)
            elif var_type.num in [2, 7]:
                emit_s(emitter, OpCode.OP_FS, F3_FS.FSD, 3, temp_reg, real_reg.offset_global)

            if not is_literal:
                emitter.reg_manager.free_temp(reg_value)
        
        emit_jump(emitter, _start_program)
        
        for func in funciones_encontradas:
            _func_start = emitter.label_manager.create()
            emitter.functions.update({func.name : (_func_start, func.return_type)})
        
        for func in funciones_encontradas:
            emitter.symbol_table.enter_scope()
            emitter.actual_func = func.name
            _func_start = emitter.functions[func.name][0]
            emitter.label_manager.place_label(_func_start, emitter.get_pc())
            current_pc_epilogue = emitter.label_manager.create()
            start_body = emitter.label_manager.create()
            emitter.functions.update({func.name : (_func_start, func.return_type, current_pc_epilogue, start_body)})
            
            prologue(emitter, func.block_expr.stmts, func.params)
            emitter.label_manager.place_label(start_body, emitter.get_pc())
            
            param_counter = 10
            fparam_counter = 10
            if func.params is not None:
                for param in func.params:
                    if param.zontype.num in [1, 3, 6]:
                        reg = emitter.symbol_table.define(param.name, param.zontype)
                        if reg is not None:
                            emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, reg, param_counter, 0)
                            param_counter += 1
                    else:
                        reg = emitter.symbol_table.define_f(param.name, param.zontype)
                        if reg is not None:
                            emit_f_type(emitter, OpCode.OP_F, reg, fparam_counter, fparam_counter, 0x00, F7.FSGNJ_D)
                            fparam_counter += 1
            
            for stmt in func.block_expr.stmts:
                generate_stmt(emitter, stmt)
            
            emitter.label_manager.place_label(current_pc_epilogue, emitter.get_pc())
            epilogue(emitter)
            emit_jalr(emitter, 0, 1)
            emitter.symbol_table.exit_scope()
        
        emitter.label_manager.place_label(_start_program, emitter.get_pc())
        emit_jump(emitter, emitter.functions["main"][0], 1)
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0x0, 93)
        emit_ecall(emitter)
    
    else:
        funciones_encontradas = [s for s in program_stmts if isinstance(s, FuncForm)]
        cuerpo_script = [s for s in program_stmts if not isinstance(s, FuncForm)]
        
        emitter.entry_point = _start_program
        emitter.label_manager.place_label(_start_program, emitter.get_pc())
        
        for func in funciones_encontradas:
            _func_start = emitter.label_manager.create()
            emitter.functions.update({func.name : (_func_start, )})
        
        prologue(emitter, cuerpo_script)
        for stmt in cuerpo_script:
            generate_stmt(emitter, stmt)
        epilogue(emitter)
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 10, 0x0, 0)
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0x0, 93)
        emit_ecall(emitter)
        
        for func in funciones_encontradas:
            emitter.symbol_table.enter_scope()
            emitter.actual_func = func.name
            _func_start = emitter.functions[func.name][0]
            emitter.label_manager.place_label(_func_start, emitter.get_pc())
            current_pc_epilogue = emitter.label_manager.create()
            start_body = emitter.label_manager.create()
            emitter.functions.update({func.name : (_func_start, func.return_type, current_pc_epilogue, start_body)})
            
            prologue(emitter, func.block_expr.stmts, func.params)
            emitter.label_manager.place_label(start_body, emitter.get_pc())
            
            param_counter = 10
            fparam_counter = 10
            if func.params is not None:
                for param in func.params:
                    if param.zontype.num in [1, 3, 6]:
                        reg = emitter.symbol_table.define(param.name, param.zontype)
                        if reg is not None:
                            emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, reg, param_counter, 0)
                            param_counter += 1
                    else:
                        reg = emitter.symbol_table.define_f(param.name, param.zontype)
                        if reg is not None:
                            emit_f_type(emitter, OpCode.OP_F, reg, fparam_counter, fparam_counter, 0x00, F7.FSGNJ_D)
                            fparam_counter += 1
            
            for stmt in func.block_expr.stmts:
                generate_stmt(emitter, stmt)
            
            emitter.label_manager.place_label(current_pc_epilogue, emitter.get_pc())
            epilogue(emitter)
            emit_jalr(emitter, 0, 1)
            emitter.symbol_table.exit_scope()

