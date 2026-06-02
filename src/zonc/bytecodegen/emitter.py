from zonc.zonast import *
from .opcode import *
from .register_manager import RegisterManager
from .bytecodescope import SymbolTable, RegT, ZonVar
from collections import namedtuple
import struct

#TODO -> despues de meter metodos recordar meter .in_heap() y .in_rodata() en str

class LabelManger:
    def __init__(self):
        self.labels: dict[int, int] = {}
        self.counter = 0
        
    def create(self):
        self.labels.update({self.counter:0})
        self.counter += 1
        return self.counter-1
        
    def place_label(self, id, pc):
        self.labels[id] = pc * 4
        
IntsB = namedtuple("IntsB", ["rs1", "rs2", "opc", "f3", "label"])
IntsJ = namedtuple("IntsJ", ["opc", "label", "rd"])
InstJR = namedtuple("IntsJR", ["rd", "rs1"])
ConstantLoad = namedtuple("ConstantLoad", ["rd", "rd_int", "pool_offset", "is_float"])
AddressLoad = namedtuple("AddressLoad", ["rd", "pool_offset"])

class Emitter:
    def __init__(self):
        self.REG_SCRATCH_X = 31
        self.REG_SCRATCH_F = 31 
        self.code = []
        self.offset_stack = []
        self.reg_manager = RegisterManager(self.offset_stack)
        self.symbol_table = SymbolTable()
        self.label_manager = LabelManger()
        self.loop_stack = []
        self.constant_pool = {}
        self.pool_data = bytearray()
        self.functions = {}
        self.actual_func = ""
        self.block_exits = []
        self.value_block_exits = []
        self.data_section_size = 0
        self.entry_point = 0
        self.string_pool = {}
          
    def add_to_pool(self, value_bits):
        if value_bits not in self.constant_pool:
            offset = len(self.pool_data)
            self.constant_pool[value_bits] = offset
            self.pool_data.extend(struct.pack('<q', value_bits))
        return self.constant_pool[value_bits]
    
    def get_pc(self): return len(self.code)
    
    def _unwrap(self, reg):
        if isinstance(reg, int): return reg
        return reg.reg 
 
    def _resolve_dest(self, reg: ZonVar, scratch: int) -> int:
        """Devuelve el registro físico a usar como destino (rd) de una instrucción.
        Si reg está desbordado al stack (reg=None), devuelve el scratch comodín;
        el caller debe llamar a _write_result(reg, scratch) después para guardarlo."""
        if isinstance(reg, int): return reg
        return reg.reg if reg.reg is not None else scratch

    def _read_operand(self, zonvar: ZonVar, scratch_reg: int):
        """
        Si zonvar está en el stack (reg es None), emite la instrucción para cargarlo
        en el registro scratch_reg (comodín) y retorna dicho registro.
        Si ya es un registro físico, lo retorna directamente sin emitir nada.
        """
        if zonvar.reg is not None:
            return zonvar.reg
            
        offset_val = zonvar.offset_stack[0] if isinstance(zonvar.offset_stack, list) else zonvar.offset_stack
        
        if zonvar.regt == RegT.X:
            self.emit_i_type(OpCode.L, F3_L.LD, scratch_reg, 8, offset_val)
            return scratch_reg
        elif zonvar.regt == RegT.F:
            self.emit_i_type(OpCode.FL, F3_FL.FLD, scratch_reg, 8, offset_val)
            return scratch_reg
        return self._unwrap(zonvar)

    def _write_result(self, dest_zonvar: ZonVar, source_reg: int):
        """
        Si el destino de una operación es un desborde (reg es None), guarda el resultado
        que quedó en source_reg de vuelta en el slot del stack correspondiente.
        """
        if dest_zonvar.reg is not None:
            return
        
        offset_val = dest_zonvar.offset_stack[0] if isinstance(dest_zonvar.offset_stack, list) else dest_zonvar.offset_stack
        
        if dest_zonvar.regt == RegT.X:
            self.emit_s(OpCode.OP_S, F3_S.SD, 8, source_reg, offset_val)
        elif dest_zonvar.regt == RegT.F:
            self.emit_s(OpCode.OP_FS, F3_FS.FSD, 8, source_reg, offset_val)
        
    def emit_r_type(self, opcode, funct3, funct7, rd, rs1, rs2):
        rd = self._unwrap(rd) & 0x1F
        rs1 = self._unwrap(rs1) & 0x1F
        rs2 = self._unwrap(rs2) & 0x1F
        funct3 &= 0x7
        funct7 &= 0x7F
        opcode &= 0x7F
        inst: int = (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode
        self.code.append(inst.to_bytes(4, "little"))
        
    def emit_s(self, opcode, funct3, rs1, rs2, imm):
        opcode &= 0x7F
        funct3 &= 0x7
        rs1 = self._unwrap(rs1) & 0x1F
        rs2 = self._unwrap(rs2) & 0x1F
        imm &= 0xFFF
        
        imm_11_5 = (imm >> 5) & 0x7F
        imm_4_0 = imm & 0x1F
        
        inst = (imm_11_5 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (imm_4_0 << 7) | opcode
        self.code.append(inst.to_bytes(4, "little"))
        
    def emit_i_type(self, opcode, funct3, rd, rs1, imm):
        rd = self._unwrap(rd) & 0x1F
        rs1 = self._unwrap(rs1) & 0x1F
        funct3 &= 0x7
        imm &= 0xFFF
        opcode &= 0x7F
        inst: int = (imm << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode
        self.code.append(inst.to_bytes(4, "little"))
      
    def emit_b_type(self, opcode, f3, rs1, rs2, label):
        rs1 = self._unwrap(rs1)
        rs2 = self._unwrap(rs2)
        self.code.append(IntsB(rs1=rs1, rs2=rs2, f3=f3, opc=opcode, label=label))

    def emit_j_type(self, opcode, rd, label):
        rd = self._unwrap(rd)
        self.code.append(IntsJ(rd=rd, opc=opcode, label=label))
        
    def emit_jalr(self, rd, rs1):
        rd = self._unwrap(rd)
        rs1 = self._unwrap(rs1)
        self.code.append(InstJR(rd=rd, rs1=rs1))
        
    def emit_u_type(self, opcode, rd, imm):
        rd = self._unwrap(rd) & 0x1F
        opcode &= 0x7F
        inst = (imm << 12) | (rd << 7) | opcode
        self.code.append(inst.to_bytes(4, "little"))
        
    def emit_f_type(self, opcode, rd, rs1, rs2, rm, f7):
        rd = self._unwrap(rd) & 0x1F
        rs1 = self._unwrap(rs1) & 0x1F
        rs2 = self._unwrap(rs2) & 0x1F
        rm &= 0x7
        f7 &= 0x7F
        opcode &= 0x7F
        inst = (f7 << 25) | (rs2 << 20) | (rs1 << 15) | (rm << 12) | (rd << 7) | opcode
        self.code.append(inst.to_bytes(4, "little"))
    
    def generate_b_type(self, instruction, offset):
        val = offset
        b12   = (val >> 12) & 0x1
        b11   = (val >> 11) & 0x1
        b10_5 = (val >> 5)  & 0x3F
        b4_1  = (val >> 1)  & 0xF
        
        inst = (b12 << 31) | (b10_5 << 25) | (instruction.rs2 << 20) | (instruction.rs1 << 15) | \
                (instruction.f3 << 12) | (b4_1 << 8) | (b11 << 7) | (instruction.opc & 0x7F)
        
        return inst.to_bytes(4, "little")
    
    def generate_j_type(self, instruction, offset):
        val = offset
        imm_20    = (val >> 20) & 0x1
        imm_10_1  = (val >> 1)  & 0x3FF
        imm_11    = (val >> 11) & 0x1
        imm_19_12 = (val >> 12) & 0xFF

        inst = (imm_20 << 31) | (imm_10_1 << 21) | (imm_11 << 20) | \
            (imm_19_12 << 12) | (instruction.rd << 7) | (instruction.opc)
        
        return inst.to_bytes(4, "little")
    
    def generate_i_type_jalr(self, instruction, offset=0):
        val = offset & 0xFFF
        
        rd = instruction.rd & 0x1F
        rs1 = instruction.rs1 & 0x1F
        funct3 = 0x0 
        opcode = 0x67 & 0x7F
        
        inst = (val << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode
        
        return inst.to_bytes(4, "little")
        
    def emit_ecall(self):
        self.code.append(0x73.to_bytes(4, "little"))
        
    def save(self, filename):
        with open(f"{filename}", "wb") as f:
            # Cabecera Fija (64 bytes en total)
            f.write(b"!NOZo\x00") # 6 bytes
            f.write(0b00000001.to_bytes(1, "little")) # 1 byte (version)
            f.write(0b00000000.to_bytes(1, "little")) # 1 byte (flags)
            f.write(self.label_manager.labels[self.entry_point].to_bytes(4, "little")) # 4 bytes(entry_point segun .text)
            
            text_size = len(self.code) * 4
            data_size = self.data_section_size
            pool_size = len(self.pool_data)
            f.write(text_size.to_bytes(4, "little")) # 4 bytes(.text size)
            f.write(data_size.to_bytes(4, "little")) # 4 bytes(.data size)
            f.write(pool_size.to_bytes(4, "little")) #4 bytes(.rodata size)
            
            #40 bytes vacios padding para futura expansion
            i = 0
            while i < 10:
                f.write(0b0.to_bytes(4, "little"))
                i += 1
            
            for i, inst in enumerate(self.code):
                if inst == "DUMMY":
                    continue
                
                current_pc = i * 4
                
                if isinstance(inst, bytes):
                    f.write(inst)
                
                elif isinstance(inst, IntsB):
                    target_pc = self.label_manager.labels[inst.label]
                    offset = target_pc - current_pc
                    f.write(self.generate_b_type(inst, offset))

                elif isinstance(inst, IntsJ):
                    target_pc = self.label_manager.labels[inst.label]
                    offset = target_pc - current_pc
                    f.write(self.generate_j_type(inst, offset))
                
                elif isinstance(inst, ConstantLoad):
                    dist_to_pool = (text_size - current_pc) + inst.pool_offset
                    
                    low = dist_to_pool & 0xFFF
                    high = dist_to_pool >> 12
                    if low & 0x800: high += 1
                    high &= 0xFFFFF
                    
                    rd = inst.rd_int & 0x1F
                    opcode = OpCode.AUIPC & 0x7F
                    auipc_inst = (high << 12) | (rd << 7) | opcode
                    f.write(auipc_inst.to_bytes(4, "little"))
                    
                    rd = inst.rd & 0x1F
                    rs1 = inst.rd_int & 0x1F
                    funct3 = 0x3 & 0x7
                    
                    if inst.is_float:
                        opcode = OpCode.FL
                    else:
                        opcode = OpCode.L
                    
                    fld_inst = (low << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode
                    f.write(fld_inst.to_bytes(4, "little"))
                
                elif isinstance(inst, InstJR):
                    f.write(self.generate_i_type_jalr(inst))
                    
                elif isinstance(inst, AddressLoad):
                    dist_to_pool = (text_size - current_pc) + inst.pool_offset
                    low = dist_to_pool & 0xFFF
                    high = dist_to_pool >> 12
                    if low & 0x800:
                        high += 1
                    high &= 0xFFFFF
                    rd = inst.rd & 0x1F
                    
                    auipc_inst = (high << 12) | (rd << 7) | OpCode.AUIPC
                    f.write(auipc_inst.to_bytes(4, "little"))
                    
                    addi_inst = (low << 20) | (rd << 15) | (F3_ALU.ADD_SUB << 12) | (rd << 7) | OpCode.OP_IMM
                    f.write(addi_inst.to_bytes(4, "little"))
            
            f.write(self.pool_data)

            data_size_in_4_bytes = self.data_section_size / 4
            i = 0
            while i < data_size_in_4_bytes:
                f.write(0b0.to_bytes(4, "little"))
                i += 1
                         
    def float_to_bits(self, f):
        return struct.unpack('<q', struct.pack('<d', f))[0]
    
    def generate_literal_f(self, imm, reg):
        bits = self.float_to_bits(imm)
        pool_offset = self.add_to_pool(bits)
        reg_addr = self.reg_manager.alloc_temp()
        
        target_reg = self._unwrap(reg)
        self.code.append(ConstantLoad(rd=target_reg, rd_int=reg_addr.reg, pool_offset=pool_offset, is_float=True))
        self.code.append("DUMMY") 
        
        self.reg_manager.free_temp(reg_addr)
        
        if isinstance(reg, ZonVar) and reg.reg is None:
            self._write_result(reg, target_reg)
    
    def generate_literal_num(self, imm, reg):
        target_reg = self._unwrap(reg)
        if imm >= -2048 and imm <= 2047:
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, target_reg, 0x0, imm)
        elif imm >= -2_147_000_000 and imm <= 2_147_000_000:
            self.emit_li(imm, target_reg)
        else:
            pool_offset = self.add_to_pool(imm)
            reg_addr = self.reg_manager.alloc_temp()
            
            self.code.append(ConstantLoad(rd=target_reg, rd_int=reg_addr.reg, pool_offset=pool_offset, is_float=False))
            self.code.append("DUMMY") 
            
            self.reg_manager.free_temp(reg_addr)
            
        if isinstance(reg, ZonVar) and reg.reg is None:
            self._write_result(reg, target_reg)
            
    def add_string_to_pool(self, s: str) -> int:
        if s in self.string_pool:
            return self.string_pool[s]

        length = len(s)
        len_bytes = bytearray()
        for i in range(8):
            len_bytes.append((length >> (8 * i)) & 0xFF)

        data_bytes = s.encode('ascii')
        full_bytes = len_bytes + data_bytes + b'\00'

        offset = len(self.pool_data)
        self.pool_data.extend(full_bytes)
        self.string_pool[s] = offset
        return offset
    
    def emit_li(self, n, reg):
        low = n & 0xFFF
        high = n >> 12
        
        if low & 0x800:
            high += 1
            
        high &= 0xFFFFF
        
        self.emit_u_type(OpCode.LUI, reg, high)
        self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, reg, reg, low)
        
    def prologue(self, stmts, params: list = None):
        from .linear_scan_register_allocation import LinearScanRegisterAllocation
        allocator = LinearScanRegisterAllocation(num_available_regs=7, num_available_fregs=12)
        
        
        bytes_needed, has_call, used_s = allocator.analyze_function(stmts, params)

        self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 2, 2, -bytes_needed)
        self.emit_s(OpCode.OP_S, F3_S.SD, 2, 8, bytes_needed - 8)
        
        if has_call:
            self.emit_s(OpCode.OP_S, F3_S.SD, 2, 1, bytes_needed - 16)
        
        current_offset = bytes_needed - 24
        for reg_num in used_s[0]:
            self.emit_s(OpCode.OP_S, F3_S.SD, 2, reg_num, current_offset)
            current_offset -= 8
            
        for reg_num in used_s[1]:
            self.emit_s(OpCode.OP_FS, F3_FS.FSD, 2, reg_num, current_offset)
            current_offset -= 8
        
        
        self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 8, 2, bytes_needed)
        self.offset_stack.append([current_offset, bytes_needed, has_call, used_s])
    
        self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -100)
        self.emit_ecall()
             
    def epilogue(self):
        _, bytes_reserved, has_call, used_s = self.offset_stack[-1]
        
        
        current_offset = bytes_reserved - 24
        for reg_num in used_s[0]:
            self.emit_i_type(OpCode.L, F3_L.LD, reg_num, 2, current_offset)
            current_offset -= 8
            
        for reg_num in used_s[1]:
            self.emit_i_type(OpCode.FL, F3_FL.FLD, reg_num, 2, current_offset)
            current_offset -= 8
        
        if has_call:
            self.emit_i_type(OpCode.L, F3_L.LD, 1, 2, bytes_reserved - 16)
        
        self.emit_i_type(OpCode.L, F3_L.LD, 8, 2, bytes_reserved - 8)
        self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 2, 2, bytes_reserved)
        
        self.offset_stack.pop()
        
        self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -101)
        self.emit_ecall()
    
    def generate_program_entry(self, program_stmts: list):
        has_main = any(isinstance(s, FuncForm) and s.name == "main" for s in program_stmts)
        _start_program = self.label_manager.create()
        
        if has_main:
            funciones_encontradas = [s for s in program_stmts if isinstance(s, FuncForm)]
            variables_globals = [s for s in program_stmts if isinstance(s, InitializationStmt)]
            
            _init_globals = self.label_manager.create()
            self.label_manager.place_label(_init_globals, self.get_pc())
            self.entry_point = _init_globals
            
            for node in variables_globals:
                var_name = node.name if isinstance(node, DeclarationStmt) else node.decl_stmt.name
                var_type = node.type if isinstance(node, DeclarationStmt) else node.decl_stmt.type
                
                if self.symbol_table.exists_here(var_name):
                    real_reg = self.symbol_table.resolve(var_name)
                else:
                    self.symbol_table.define_global(var_name, offset_global=self.data_section_size, zontype=var_type)
                    self.data_section_size += 8
                    real_reg = self.symbol_table.resolve(var_name)
                
                val_node = node.assign_stmt.value
                if isinstance(val_node, (IntLiteral, BoolLiteral)):
                    temp_reg = self.reg_manager.alloc_temp()
                    temp_reg_s = self._read_operand(temp_reg, self.REG_SCRATCH_X)
                    self.generate_literal_num(val_node.value, temp_reg)
                    self._write_result(temp_reg, temp_reg_s)
                    is_literal = True
                    
                elif isinstance(val_node, FloatLiteral):
                    temp_reg = self.reg_manager.alloc_temp()
                    temp_reg_s = self._read_operand(temp_reg, self.REG_SCRATCH_F)
                    self.generate_literal_f(val_node.value, temp_reg)
                    self._write_result(temp_reg, temp_reg_s)
                    is_literal = True
                    
                elif isinstance(val_node, StringLiteral):
                    str_zv = self.generate_expr(val_node)
                    temp_reg = self._read_operand(str_zv, self.REG_SCRATCH_X)
                    is_literal = True
                    self.reg_manager.free_temp(str_zv)
                    
                else:
                    reg_value = self.generate_expr(val_node, var_type.num)
                    temp_reg = self._read_operand(reg_value, self.REG_SCRATCH_X if reg_value.regt == RegT.X else self.REG_SCRATCH_F)
                    is_literal = False

                if var_type.num in [1, 3, 4, 6]:
                    self.emit_s(OpCode.OP_S, F3_S.SD, 3, temp_reg, real_reg.offset_global)
                elif var_type.num in [2, 7]:
                    self.emit_s(OpCode.OP_FS, F3_FS.FSD, 3, temp_reg, real_reg.offset_global)

                if not is_literal:
                    self.reg_manager.free_temp(reg_value)
            
            self.emit_jump(_start_program)
            
            for func in funciones_encontradas:
                _func_start = self.label_manager.create()
                self.functions.update({func.name : (_func_start, func.return_type)})
            
            for func in funciones_encontradas:
                self.symbol_table.enter_scope()
                self.actual_func = func.name
                _func_start = self.functions[func.name][0]
                self.label_manager.place_label(_func_start, self.get_pc())
                current_pc_epilogue = self.label_manager.create()
                start_body = self.label_manager.create()
                self.functions.update({func.name : (_func_start, func.return_type, current_pc_epilogue, start_body)})
                
                self.prologue(func.block_expr.stmts, func.params)
                
                self.label_manager.place_label(start_body, self.get_pc())
                
                param_counter = 10
                fparam_counter = 10
                if func.params is not None:
                    for param in func.params:
                        if param.zontype.num in [1, 3, 6]:
                            reg = self.symbol_table.define(param.name, param.zontype)
                            if reg is not None:
                                self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, reg, param_counter, 0)
                                param_counter += 1
                            
                            else:
                                pass
                            
                        else:
                            reg = self.symbol_table.define_f(param.name, param.zontype)
                            if reg is not None:
                                self.emit_f_type(OpCode.OP_F, reg, fparam_counter, fparam_counter, 0x00, F7.FSGNJ_D)
                                fparam_counter += 1
                            
                            else:
                                pass
                
                for stmt in func.block_expr.stmts:
                    self.generate_stmt(stmt)
                
                self.label_manager.place_label(current_pc_epilogue, self.get_pc())
                self.epilogue()
                self.emit_jalr(0, 1)
                self.symbol_table.exit_scope()
            
            self.label_manager.place_label(_start_program, self.get_pc())
            self.emit_jump(self.functions["main"][0], 1)
            
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0x0, 93)
            self.emit_ecall()
            
        else:
            funciones_encontradas = [s for s in program_stmts if isinstance(s, FuncForm)]
            cuerpo_script = [s for s in program_stmts if not isinstance(s, FuncForm)]
            
            self.entry_point = _start_program
            self.label_manager.place_label(_start_program, self.get_pc())
            
            for func in funciones_encontradas:
                _func_start = self.label_manager.create()
                self.functions.update({func.name : (_func_start, )})
                
            self.prologue(cuerpo_script)
            
            for stmt in cuerpo_script:
                self.generate_stmt(stmt)
                
            self.epilogue()
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 10, 0x0, 0)
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0x0, 93)
            self.emit_ecall()
            
            for func in funciones_encontradas:
                self.symbol_table.enter_scope()
                self.actual_func = func.name
                _func_start = self.functions[func.name][0]
                self.label_manager.place_label(_func_start, self.get_pc())
                current_pc_epilogue = self.label_manager.create()
                start_body = self.label_manager.create()
                self.functions.update({func.name : (_func_start, func.return_type, current_pc_epilogue, start_body)})
                
                self.prologue(func.block_expr.stmts, func.params)
                
                self.label_manager.place_label(start_body, self.get_pc())
                param_counter = 10
                fparam_counter = 10
                if func.params is not None:
                    for param in func.params:
                        if param.zontype.num in [1, 3, 6]:
                            reg = self.symbol_table.define(param.name, param.zontype)
                            if reg is not None:
                                self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, reg, param_counter, 0)
                                param_counter += 1
                            
                            else:
                                pass
                            
                        else:
                            reg = self.symbol_table.define_f(param.name, param.zontype)
                            if reg is not None:
                                self.emit_f_type(OpCode.OP_F, reg, fparam_counter, fparam_counter, 0x00, F7.FSGNJ_D)
                                fparam_counter += 1
                            
                            else:
                                pass
                
                for stmt in func.block_expr.stmts:
                    self.generate_stmt(stmt)
                
                self.label_manager.place_label(current_pc_epilogue, self.get_pc())
                self.epilogue()
                self.emit_jalr(0, 1)
                self.symbol_table.exit_scope()

    #Function temporal
    def emit_ecall_store(self, node):
        for i, param in enumerate(node.params):
            if isinstance(param, IntLiteral):
                self.generate_literal_num(param.value, 10+i)
            
            else:
                
                reg_param = self.generate_expr(param)
                src_reg = self._read_operand(reg_param, self.REG_SCRATCH_X)
                
                self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 10+i, src_reg, 0)
                self.reg_manager.free_temp(reg_param)
                        
        self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0x0, -103)
        self.emit_ecall()
        
    def emit_ecall_alloc_load(self, node, flag):
        if isinstance(node.params[0], IntLiteral):
            self.generate_literal_num(node.params[0].value, 10)
            
        else:
            reg_param = self.generate_expr(node.params[0])
            src_reg = self._read_operand(reg_param, self.REG_SCRATCH_X)
            
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 10, src_reg, 0)
            self.reg_manager.free_temp(reg_param)
        
        code = 0
        if flag == 0: code = -102
        elif flag == 1: code = -104
        
        self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0x0, code)
        self.emit_ecall()
        
        return ZonVar(10, RegT.X, ZonType(1, "int64"))
            
    def generate_stmt(self, node):
        match node:
            case DeclarationStmt():
                if not self.symbol_table.exists_here(node.name):
                    is_float = node.type.num in [2, 7]
                    saved_list = self.symbol_table.fsaved if is_float else self.symbol_table.saved
                    regt = RegT.F if is_float else RegT.X
                    used_regs = {v.reg for s in self.symbol_table.scopes for v in s.values() if v.reg is not None and v.regt == regt}
                    free_reg = next((r for r in saved_list if r not in used_regs), None)
                    if free_reg is not None:
                        zonvar = ZonVar(free_reg, regt, node.type)
                    else:
                        bytes_needed = self.offset_stack[-1][1]
                        current_offset = self.offset_stack[-1][0]
                        fp_offset = current_offset - bytes_needed 
                        zonvar = ZonVar(None, regt, node.type, offset_stack=fp_offset)
                    self.symbol_table.scopes[-1][node.name] = zonvar

            case AssignmentStmt():
                real_reg = self.symbol_table.resolve(node.name)
                
                if real_reg.is_global:
                    reg_value = self.generate_expr(node.value, real_reg.zontype.num)
                    src_reg = self._read_operand(reg_value, self.REG_SCRATCH_X if reg_value.regt == RegT.X else self.REG_SCRATCH_F)
                    
                    if real_reg.zontype.num in [1, 3, 4, 6]:
                        self.emit_s(OpCode.OP_S, F3_S.SD, 3, src_reg, real_reg.offset_global)
                        self.reg_manager.free_temp(reg_value)
                    elif real_reg.zontype.num in [2, 7]:
                        self.emit_s(OpCode.OP_FS, F3_FS.FSD, 3, src_reg, real_reg.offset_global)
                        self.reg_manager.free_temp(reg_value)
                        
                    return

                if real_reg.reg is not None:
                    if isinstance(node.value, (IntLiteral, BoolLiteral)):
                        self.generate_literal_num(node.value.value, real_reg.reg)
                        return
                    elif isinstance(node.value, FloatLiteral):
                        self.generate_literal_f(node.value.value, real_reg.reg)
                        return
                    
                    reg_value = self.generate_expr(node.value, real_reg.zontype.num)
                    src_reg = self._read_operand(reg_value, self.REG_SCRATCH_X if reg_value.regt == RegT.X else self.REG_SCRATCH_F)
                    
                    if reg_value.regt == RegT.X:
                        self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, real_reg.reg, src_reg, 0)
                    elif reg_value.regt == RegT.F:
                        self.emit_f_type(OpCode.OP_F, real_reg.reg, src_reg, src_reg, 0x00, F7.FSGNJ_D)
                        
                    self.reg_manager.free_temp(reg_value)
                else:
                    if isinstance(node.value, (IntLiteral, BoolLiteral)):
                        scratch = self.REG_SCRATCH_X
                        self.generate_literal_num(node.value.value, scratch)
                        self._write_result(real_reg, scratch)
                        return
                    elif isinstance(node.value, FloatLiteral):
                        scratch = self.REG_SCRATCH_F
                        self.generate_literal_f(node.value.value, scratch)
                        self._write_result(real_reg, scratch)
                        return

                    reg_value = self.generate_expr(node.value, real_reg.zontype.num)
                    src_reg = self._read_operand(reg_value, self.REG_SCRATCH_X if reg_value.regt == RegT.X else self.REG_SCRATCH_F)
                    self._write_result(real_reg, src_reg)
                    self.reg_manager.free_temp(reg_value)
                
            case InitializationStmt():
                var_name = node.decl_stmt.name
                var_type = node.decl_stmt.type
                var_num_type = var_type.num
                is_float = var_num_type in [2, 7]
                regt = RegT.F if is_float else RegT.X
                val_node = node.assign_stmt.value

                if isinstance(val_node, (IntLiteral, BoolLiteral)):
                    temp_reg = self.REG_SCRATCH_X
                    self.generate_literal_num(val_node.value, temp_reg)
                    is_literal = True
                    
                elif isinstance(val_node, FloatLiteral):
                    temp_reg = self.REG_SCRATCH_F
                    self.generate_literal_f(val_node.value, temp_reg)
                    is_literal = True
                    
                elif isinstance(val_node, StringLiteral):
                    str_zv = self.generate_expr(val_node)
                    temp_reg = self._read_operand(str_zv, self.REG_SCRATCH_X)
                    is_literal = True
                    self.reg_manager.free_temp(str_zv)    
                
                else:
                    reg_value = self.generate_expr(val_node, var_num_type)
                    temp_reg = self._read_operand(reg_value, self.REG_SCRATCH_X if reg_value.regt == RegT.X else self.REG_SCRATCH_F)
                    is_literal = False

                if self.symbol_table.exists_here(var_name):
                    real_reg = self.symbol_table.resolve(var_name)
                else:
                    used_regs = {v.reg for s in self.symbol_table.scopes for v in s.values() if v.reg is not None and v.regt == regt}
                    saved_list = self.symbol_table.fsaved if is_float else self.symbol_table.saved
                    
                    free_reg = next((r for r in saved_list if r not in used_regs), None)
                    
                    if free_reg is not None:
                        real_reg = ZonVar(free_reg, regt, var_type)
                    else:
                        current_offset = self.offset_stack[-1][0]
                        self.offset_stack[-1][0] -= 8 
                        bytes_needed = self.offset_stack[-1][1]
                        fp_offset = current_offset - bytes_needed
                        real_reg = ZonVar(None, regt, var_type, offset_stack=fp_offset)
                    
                    self.symbol_table.scopes[-1][var_name] = real_reg

                if real_reg.reg is not None:
                    if regt == RegT.X:
                        self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, real_reg.reg, temp_reg, 0)
                    elif regt == RegT.F:
                        self.emit_f_type(OpCode.OP_F, real_reg.reg, temp_reg, temp_reg, 0x00, F7.FSGNJ_D)
                else:
                    self._write_result(real_reg, temp_reg)

                if not is_literal:
                    self.reg_manager.free_temp(reg_value)

            case CallFunc():
                if node.name in ["print", "println"]:
                    if node.params is not None:
                        for param in node.params:
                            if isinstance(param, BoolLiteral):
                                self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 10, 0x0, param.value)
                                self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0x0, -3)
                                self.emit_ecall()
                            
                            elif isinstance(param, IntLiteral):
                                self.generate_literal_num(param.value, 10)
                                self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0x0, -1)
                                self.emit_ecall()
                                
                            elif isinstance(param, FloatLiteral):
                                self.generate_literal_f(param.value, 10)
                                self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0x0, -2)
                                self.emit_ecall()
                            
                            elif isinstance(param, StringLiteral):
                                str_var = self.generate_expr(param)
                                src_reg = self._read_operand(str_var, self.REG_SCRATCH_X)
                                self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 10, src_reg, 0)
                                self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -4)
                                self.emit_ecall()
                                self.reg_manager.free_temp(str_var)
                            
                            else:
                                reg_param = self.generate_expr(param)
                                src_reg = self._read_operand(reg_param, self.REG_SCRATCH_X if reg_param.regt == RegT.X else self.REG_SCRATCH_F)
                                
                                if reg_param.regt == RegT.X:
                                    self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 10, src_reg, 0)
                                    if reg_param.zontype.num == 3:
                                        self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -3)
                                    elif reg_param.zontype.num == 4:
                                        self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -4)
                                    else:
                                        self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -1)
                                        
                                elif reg_param.regt == RegT.F:
                                    self.emit_f_type(OpCode.OP_F, 10, src_reg, src_reg, 0x0, F7.FSGNJ_D)
                                    self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -2)
                                
                                self.emit_ecall()
                                self.reg_manager.free_temp(reg_param)
                    
                    if node.name == "println":
                        self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -5)
                        self.emit_ecall()
                    
                elif node.name == "store":
                    self.emit_ecall_store(node)
                
                else:
                    param_counter = 10
                    fparam_counter = 10
                    if node.params is not None:
                        for param in node.params:
                            reg = self.generate_expr(param)
                            src_reg = self._read_operand(reg, self.REG_SCRATCH_X if reg.regt == RegT.X else self.REG_SCRATCH_F)
                            if reg.regt == RegT.X:
                                self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, param_counter, src_reg, 0)
                                param_counter += 1
                            else:
                                self.emit_f_type(OpCode.OP_F, fparam_counter, src_reg, src_reg, 0x0, F7.FSGNJ_D)
                                fparam_counter += 1
                            self.reg_manager.free_temp(reg)
                            
                    current_used_temps, current_used_ftemps = self.reg_manager.get_active_regs()
                    current_offset = self.offset_stack[-1][0]
                    for reg_num in current_used_temps:
                        self.emit_s(OpCode.OP_S, F3_S.SD, 2, reg_num, current_offset)
                        current_offset -= 8
                        
                    for reg_num in current_used_ftemps:
                        self.emit_s(OpCode.OP_FS, F3_FS.FSD, 2, reg_num, current_offset)
                        current_offset -= 8
                        
                    self.emit_jump(self.functions[node.name][0], rd=1)
                    
                    current_offset = self.offset_stack[-1][0]
                    for reg_num in current_used_temps:
                        self.emit_i_type(OpCode.L, F3_L.LD, reg_num, 2, current_offset)
                        current_offset -= 8
                        
                    for reg_num in current_used_ftemps:
                        self.emit_i_type(OpCode.FL, F3_FL.FLD, reg_num, 2, current_offset)
                        current_offset -= 8
                
            case BlockExpr():
                exit = self.label_manager.create()
                self.value_block_exits.append(exit)
                self.symbol_table.enter_scope()
                self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -100)
                self.emit_ecall()
                for stmt in node.stmts:
                    self.generate_stmt(stmt)
                self.symbol_table.exit_scope()
                self.label_manager.place_label(exit, self.get_pc())
                self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -101)
                self.emit_ecall()
                            
            case IfForm():
                exit = self.label_manager.create()
                end_if = self.label_manager.create()
                if not node.if_branch is None:
                    self.generate_cond(end_if, node.if_branch.cond)
                    self.generate_stmt(node.if_branch.block)
                    
                    if node.elif_branches is None and node.else_branch is None:
                        self.label_manager.place_label(end_if, self.get_pc())
                        return
                    
                    elif node.elif_branches is None and not node.else_branch is None:
                        self.emit_jump(exit)
                        self.label_manager.place_label(end_if, self.get_pc())
                        
                if not node.elif_branches is None:
                    if not node.if_branch is None:
                        self.emit_jump(exit)
                        self.label_manager.place_label(end_if, self.get_pc())
                    for i, branch in enumerate(node.elif_branches):
                        if branch is None:
                            continue
                        
                        end_elif = self.label_manager.create()
                        self.generate_cond(end_elif, branch.cond)
                        self.generate_stmt(branch.block)
                        
                        if (len(node.elif_branches) - 1) == i and node.else_branch is None:
                            self.label_manager.place_label(end_elif, self.get_pc())
                            self.label_manager.place_label(exit, self.get_pc())
                            return
                        
                        self.emit_jump(exit)
                        self.label_manager.place_label(end_elif, self.get_pc())
                        
                if not node.else_branch is None:
                    self.generate_stmt(node.else_branch.block)
                    
                self.label_manager.place_label(exit, self.get_pc())
                
            case WhileForm():
                exit = self.label_manager.create()
                cond = self.label_manager.create()
                self.loop_stack.append((exit, cond))
                self.label_manager.place_label(cond, self.get_pc())
                self.generate_cond(exit, node.condition_field)
                self.generate_stmt(node.block_expr)
                self.emit_jump(cond)
                self.label_manager.place_label(exit, self.get_pc())
                
            case ContinueStmt():
                self.emit_jump(self.loop_stack[-1][1])
                
            case BreakStmt():
                self.emit_jump(self.loop_stack[-1][0])
            
            case GiveStmt():
                reg_res = self.generate_expr(node.value)
                src_reg = self._read_operand(reg_res, self.REG_SCRATCH_X if reg_res.regt == RegT.X else self.REG_SCRATCH_F)
                if reg_res.regt == RegT.X:
                    self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 10, src_reg, 0)
                else:
                    self.emit_f_type(OpCode.OP_F, 10, src_reg, src_reg, 0x00, F7.FSGNJ_D)
                    
                self.reg_manager.free_temp(reg_res)
                self.emit_jump(self.value_block_exits[-1])
                return reg_res.regt, reg_res.zontype
                
            case ReturnStmt():
                if node.value is None:
                    self.emit_jump(self.functions[self.actual_func][2])
                    return
                
                if isinstance(node.value, CallFunc) and node.value.name == self.actual_func:
                    param_counter = 10
                    fparam_counter = 10
                    if node.value.params is not None:
                        for param in node.value.params:
                            reg = self.generate_expr(param)
                            src_reg = self._read_operand(reg, self.REG_SCRATCH_X if reg.regt == RegT.X else self.REG_SCRATCH_F)
                            if reg.regt == RegT.X:
                                self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, param_counter, src_reg, 0)
                                param_counter += 1
                            else:
                                self.emit_f_type(OpCode.OP_F, fparam_counter, src_reg, src_reg, 0x0, F7.FSGNJ_D)
                                fparam_counter += 1
                            self.reg_manager.free_temp(reg)
                            
                    current_used_temps, current_used_ftemps = self.reg_manager.get_active_regs()
                    current_offset = self.offset_stack[-1][0]
                    for reg_num in current_used_temps:
                        self.emit_s(OpCode.OP_S, F3_S.SD, 2, reg_num, current_offset)
                        current_offset -= 8
                        
                    for reg_num in current_used_ftemps:
                        self.emit_s(OpCode.OP_FS, F3_FS.FSD, 2, reg_num, current_offset)
                        current_offset -= 8
                        
                    self.emit_jump(self.functions[node.value.name][3], rd=1)
                    
                    current_offset = self.offset_stack[-1][0]
                    for reg_num in current_used_temps:
                        self.emit_i_type(OpCode.L, F3_L.LD, reg_num, 2, current_offset)
                        current_offset -= 8
                        
                    for reg_num in current_used_ftemps:
                        self.emit_i_type(OpCode.FL, F3_FL.FLD, reg_num, 2, current_offset)
                        current_offset -= 8
                            
                    self.emit_jump(self.functions[self.actual_func][2])
                    return
                    
                reg_res = self.generate_expr(node.value)
                src_reg = self._read_operand(reg_res, self.REG_SCRATCH_X if reg_res.regt == RegT.X else self.REG_SCRATCH_F)
                if reg_res.regt == RegT.X:
                    self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 10, src_reg, 0)
                else:
                    self.emit_f_type(OpCode.OP_F, 10, src_reg, src_reg, 0x00, F7.FSGNJ_D)
                    
                self.reg_manager.free_temp(reg_res)
                self.emit_jump(self.functions[self.actual_func][2])
                        
    def emit_jump(self, label, rd=0):
        self.emit_j_type(OpCode.JAL, rd, label)
    
    def generate_expr(self, node, target_type = None):
        if isinstance(node, (IntLiteral, BoolLiteral)):
            reg = self.reg_manager.alloc_temp()
            self.generate_literal_num(node.value, reg)
            return reg
        
        if isinstance(node, FloatLiteral):
            reg = self.reg_manager.alloc_ftemp()
            self.generate_literal_f(node.value, reg)
            return reg
        
        if isinstance(node, StringLiteral):
            pool_offset = self.add_string_to_pool(node.value)
            reg = self.reg_manager.alloc_temp()
            self.code.append(AddressLoad(rd=reg.reg, pool_offset=pool_offset))
            self.code.append("DUMMY")
            return ZonVar(reg.reg, RegT.X, ZonType(4, "string"))
        
        match node:
            case CastExpr():
                if node.zontype.num == 1:
                    reg_value = self.generate_expr(node.value)
                    src_v = self._read_operand(reg_value, self.REG_SCRATCH_X if reg_value.regt == RegT.X else self.REG_SCRATCH_F)
                    reg = self.reg_manager.alloc_temp()
                    rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
                    self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, reg, src_v, 0)
                    self._write_result(reg, rd)
                    return reg
                
                elif node.zontype.num == 3:
                    reg_value = self.generate_expr(node.value)
                    src_v = self._read_operand(reg_value, self.REG_SCRATCH_X if reg_value.regt == RegT.X else self.REG_SCRATCH_F)
                    reg = self.reg_manager.alloc_temp()
                    rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
                    self.emit_r_type(OpCode.OP, F3_ALU.SLTU_SLTIU, F7.STANDARD, reg, 0, src_v)
                    self._write_result(reg, rd)
                    reg.zontype = node.zontype
                    return reg
                    
            case BinaryExpr():
                is_w = (target_type == 6)
                is_s = (target_type == 2)
                
                match node.operator:
                    case Operator.EQ_STR:
                        reg = self.emit_eq_str(node)
                        reg.zontype = ZonType(3, "bool")
                        return reg
                    
                    case Operator.NE_STR:
                        reg = self.emit_eq_str(node)
                        reg_not = self.generate_not_expr(reg_val=reg)
                        reg_not.zontype = ZonType(3, "bool")
                        return reg_not
                    
                    case Operator.CONCAT:
                        reg_left = self.generate_expr(node.left)
                        reg_right = self.generate_expr(node.right)
                        
                        src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
                        src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_X else self.REG_SCRATCH_X)
                        
                        reg = self.reg_manager.alloc_temp()
                        rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
                        
                        # Emitir STR_CONCAT rd, rs1, rs2
                        self.emit_r_type(OpCode.OP_STR, F3_STR.CONCAT, F7_STR.STANDARD, rd, src_l, src_r)
                        self._write_result(reg, rd)
                        
                        self.reg_manager.free_temp(reg_left)
                        self.reg_manager.free_temp(reg_right)
                        
                        reg.zontype = ZonType(4, "string")
                        return reg
                  
                    case Operator.ADD:
                        if isinstance(node.right, IntLiteral) and (node.right.value >= -2048 and node.right.value <= 2047):
                            reg_left = self.generate_expr(node.left)
                            src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
                            reg = self.reg_manager.alloc_temp()
                            rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
                            opcode = OpCode.OP_IMM_32 if is_w else OpCode.OP_IMM
                            self.emit_i_type(opcode, F3_ALU.ADD_SUB, rd, src_l, node.right.value)
                            self._write_result(reg, rd)
                            self.reg_manager.free_temp(reg_left)
                            reg.zontype = ZonType(1, "int64")
                            return reg

                        if isinstance(node.left, IntLiteral) and (node.left.value >= -2048 and node.left.value <= 2047):
                            reg_right = self.generate_expr(node.right)
                            src_r = self._read_operand(reg_right, self.REG_SCRATCH_X)
                            reg = self.reg_manager.alloc_temp()
                            rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
                            opcode = OpCode.OP_IMM_32 if is_w else OpCode.OP_IMM
                            self.emit_i_type(opcode, F3_ALU.ADD_SUB, rd, src_r, node.left.value)
                            self._write_result(reg, rd)
                            self.reg_manager.free_temp(reg_right)
                            reg.zontype = ZonType(1, "int64")
                            return reg

                        reg_left = self.generate_expr(node.left)
                        reg_right = self.generate_expr(node.right)
                        
                        if reg_left.regt == RegT.X:
                            src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
                            src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_X else self.REG_SCRATCH_X)
                            reg = self.reg_manager.alloc_temp()
                            rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
                            opcode = OpCode.OP_32 if is_w else OpCode.OP
                            self.emit_r_type(opcode, F3_ALU.ADD_SUB, F7.STANDARD, rd, src_l, src_r)
                            self._write_result(reg, rd)
                            reg.zontype = ZonType(1, "int64")
                            
                        elif reg_left.regt == RegT.F:
                            src_l = self._read_operand(reg_left, self.REG_SCRATCH_F)
                            src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_F else self.REG_SCRATCH_F)
                            reg = self.reg_manager.alloc_ftemp()
                            rd = self._resolve_dest(reg, self.REG_SCRATCH_F)
                            f7 = F7.STANDARD if is_s else F7.M_EXT_OR_FADD_D
                            self.emit_f_type(OpCode.OP_F, rd, src_l, src_r, 0x7, f7)
                            self._write_result(reg, rd)
                            reg.zontype = ZonType(2, "double")
                        
                        self.reg_manager.free_temp(reg_left)
                        self.reg_manager.free_temp(reg_right)
                        
                        return reg

                    case Operator.SUB:
                        if isinstance(node.right, IntLiteral) and (node.right.value >= -2048 and node.right.value <= 2047):
                            reg_left = self.generate_expr(node.left)
                            src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
                            reg = self.reg_manager.alloc_temp()
                            rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
                            opcode = OpCode.OP_IMM_32 if is_w else OpCode.OP_IMM
                            self.emit_i_type(opcode, F3_ALU.ADD_SUB, rd, src_l, -(node.right.value))
                            self.reg_manager.free_temp(reg_left)
                            self._write_result(reg, rd)
                            reg.zontype = ZonType(1, "int64")
                            return reg

                        reg_left = self.generate_expr(node.left)
                        reg_right = self.generate_expr(node.right)
                        if reg_left.regt == RegT.X:
                            src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
                            src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_X else self.REG_SCRATCH_X)
                            reg = self.reg_manager.alloc_temp()
                            rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
                            opcode = OpCode.OP_32 if is_w else OpCode.OP
                            self.emit_r_type(opcode, F3_ALU.ADD_SUB, F7.ALT, rd, src_l, src_r)
                            self._write_result(reg, rd)
                            reg.zontype = ZonType(1, "int64")
                        
                        elif reg_left.regt == RegT.F:
                            src_l = self._read_operand(reg_left, self.REG_SCRATCH_F)
                            src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_F else self.REG_SCRATCH_F)
                            reg = self.reg_manager.alloc_ftemp()
                            rd = self._resolve_dest(reg, self.REG_SCRATCH_F)
                            f7 = F7.FSUB_S if is_s else F7.FSUB_D
                            self.emit_f_type(OpCode.OP_F, rd, src_l, src_r, 0x7, f7)
                            self._write_result(reg, rd)
                            reg.zontype = ZonType(2, "double")
                            
                            
                        self.reg_manager.free_temp(reg_left)
                        self.reg_manager.free_temp(reg_right)
                        
                        return reg
                    
                    case Operator.MUL:
                        reg_left = self.generate_expr(node.left)
                        reg_right = self.generate_expr(node.right)
                        if reg_left.regt == RegT.X:
                            src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
                            src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_X else self.REG_SCRATCH_X)
                            reg = self.reg_manager.alloc_temp()
                            rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
                            opcode = OpCode.OP_32 if is_w else OpCode.OP
                            self.emit_r_type(opcode, F3_M_EXT.MUL, F7.M_EXT_OR_FADD_D, rd, src_l, src_r)
                            self._write_result(reg, rd)
                            reg.zontype = ZonType(1, "int64")
                            
                        elif reg_left.regt == RegT.F:
                            src_l = self._read_operand(reg_left, self.REG_SCRATCH_F)
                            src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_F else self.REG_SCRATCH_F)
                            reg = self.reg_manager.alloc_ftemp()
                            rd = self._resolve_dest(reg, self.REG_SCRATCH_F)
                            f7 = F7.FMUL_S if is_s else F7.FMUL_D
                            self.emit_f_type(OpCode.OP_F, rd, src_l, src_r, 0x7, f7)
                            self._write_result(reg, rd)
                            reg.zontype = ZonType(2, "double")
                            

                        
                        self.reg_manager.free_temp(reg_left)
                        self.reg_manager.free_temp(reg_right)
                       
                        return reg
                    
                    case Operator.DIV:
                        reg_left = self.generate_expr(node.left)
                        reg_right = self.generate_expr(node.right)
                        if reg_left.regt == RegT.X:
                            src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
                            src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_X else self.REG_SCRATCH_X)
                            reg = self.reg_manager.alloc_temp()
                            rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
                            opcode = OpCode.OP_32 if is_w else OpCode.OP
                            self.emit_r_type(opcode, F3_M_EXT.DIV, F7.M_EXT_OR_FADD_D, rd, src_l, src_r)
                            self._write_result(reg, rd)
                            reg.zontype = ZonType(1, "int64")
                        
                        elif reg_left.regt == RegT.F:
                            src_l = self._read_operand(reg_left, self.REG_SCRATCH_F)
                            src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_F else self.REG_SCRATCH_F)
                            reg = self.reg_manager.alloc_ftemp()
                            rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
                            f7 = F7.FDIV_S if is_s else F7.FDIV_D
                            self.emit_f_type(OpCode.OP_F, rd, src_l, src_r, 0x7, f7)
                            self._write_result(reg, rd)
                            reg.zontype = ZonType(2, "double")
                            
                            
                        self.reg_manager.free_temp(reg_left)
                        self.reg_manager.free_temp(reg_right)     
                        return reg
                    
                    case Operator.MOD:
                        reg_left = self.generate_expr(node.left)
                        reg_right = self.generate_expr(node.right)
                        src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
                        src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_X else self.REG_SCRATCH_X)
                        reg = self.reg_manager.alloc_temp()
                        rd = self._resolve_dest(reg, self.REG_SCRATCH_X)                        
                        opcode = OpCode.OP_32 if is_w else OpCode.OP
                        self.emit_r_type(opcode, F3_M_EXT.REM, F7.M_EXT_OR_FADD_D, rd, src_l, src_r)
                        self._write_result(reg, rd)
                        reg.zontype = ZonType(1, "int64")

                        self.reg_manager.free_temp(reg_left)
                        self.reg_manager.free_temp(reg_right)
                        return reg
                    
                    case Operator.LT: return self.generate_lt_expr(node)
                    
                    case Operator.GT:
                        right = node.right
                        node.right = node.left
                        node.left = right
                        return self.generate_lt_expr(node)
                    
                    case Operator.LE:
                        right = node.right
                        node.right = node.left
                        node.left = right
                        reg_lt = self.generate_lt_expr(node)
                        return self.generate_not_expr(reg_val=reg_lt)
                    
                    case Operator.GE:
                        reg_lt = self.generate_lt_expr(node)
                        return self.generate_not_expr(reg_val=reg_lt)
                    
                    case Operator.EQ: return self.generate_eq_expr(node)
                    
                    case Operator.NE:
                        reg_eq = self.generate_eq_expr(node)
                        return self.generate_not_expr(reg_val=reg_eq)
                    
                    case Operator.AND: 
                        reg = self.reg_manager.alloc_temp()
                        rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
                        self.generate_cond_and(node, None, rd)
                        self._write_result(reg, rd)
                        reg.zontype = ZonType(3, "bool")
                        return reg
                    
                    case Operator.OR:
                        reg = self.reg_manager.alloc_temp()
                        rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
                        self.generate_cond_or(node, None, rd)
                        self._write_result(reg, rd)
                        reg.zontype = ZonType(3, "bool")
                        return reg
                    
                    case Operator.BAND:
                        return self.generate_and_expr(node)
                    
                    case Operator.BXOR:
                        reg = self.generate_xor_expr(node)
                        return reg
                    
                    case Operator.BOR:
                        return self.generate_or_expr(node)
                    
                    case Operator.SL:
                        if isinstance(node.right, IntLiteral) and node.right.value >= -2048 and node.right.value <= 2047:
                            reg_left = self.generate_expr(node.left)
                            src_l = self._read_operand(reg_right, self.REG_SCRATCH_X)
                            reg = self.reg_manager.alloc_temp()
                            rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
                            self.emit_i_type(OpCode.OP_IMM, F3_ALU.SLL_SLLI, rd, src_l, node.right.value)
                            self._write_result(reg, rd)
                            self.reg_manager.free_temp(reg_left)
                            return reg
                        
                        reg_left = self.generate_expr(node.left)
                        reg_right = self.generate_expr(node.right)
                        src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
                        src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_X else self.REG_SCRATCH_X)
                        reg = self.reg_manager.alloc_temp()
                        rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
                        self.emit_r_type(OpCode.OP, F3_ALU.SLL_SLLI, F7.STANDARD, rd, src_l, src_r)
                        self._write_result(reg, rd)
                        self.reg_manager.free_temp(reg_left)
                        self.reg_manager.free_temp(reg_right)
                        return reg
                    
                    case Operator.SR:
                        if isinstance(node.right, IntLiteral):
                            reg_left = self.generate_expr(node.left)
                            src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
                            reg = self.reg_manager.alloc_temp()
                            rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
                            shamt = node.right.value & 0x3F 
    
                            imm_preparado = 0x400 | shamt  
                            
                            self.emit_i_type(OpCode.OP_IMM, F3_ALU.SRL_SRLI_SRA_SRAI, rd, src_l, imm_preparado)
                            self._write_result(reg, rd)
                            self.reg_manager.free_temp(reg_left)
                            return reg
                        
                        reg_left = self.generate_expr(node.left)
                        reg_right = self.generate_expr(node.right)
                        src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
                        src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_X else self.REG_SCRATCH_X)
                        reg = self.reg_manager.alloc_temp()
                        rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
                        self.emit_r_type(OpCode.OP, F3_ALU.SRL_SRLI_SRA_SRAI, F7.ALT, rd, src_l, src_r)
                        self._write_result(reg, rd)
                        self.reg_manager.free_temp(reg_left)
                        self.reg_manager.free_temp(reg_right)
                        return reg
                    
                    case Operator.BNAND:
                        reg = self.generate_and_expr(node)
                        reg_not = self.generate_not_expr(reg_val=reg, bit=True)
                        return reg_not
                    
                    case Operator.BNOR:
                        reg = self.generate_or_expr(node)
                        reg_not = self.generate_not_expr(reg_val=reg, bit=True)
                        return reg_not
                    
                    case Operator.BXNOR:
                        reg = self.generate_xor_expr(node)
                        reg_not = self.generate_not_expr(reg_val=reg, bit=True)
                        return reg_not
                    
            case UnaryExpr():
                match node.operator:
                    case Operator.NEG:
                        reg_value = self.generate_expr(node.value)
                        src_v = self._read_operand(reg_value, self.REG_SCRATCH_X if reg_value.regt == RegT.X else self.REG_SCRATCH_F)
                        if reg_value.regt == RegT.X:
                            reg = self.reg_manager.alloc_temp()
                            rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
                            opcode = OpCode.OP_32 if is_w else OpCode.OP
                            self.emit_r_type(opcode, F3_ALU.ADD_SUB, F7.ALT, reg, 0x0, src_v)
                            self._write_result(reg, rd)
                            
                        elif reg_value.regt == RegT.F:
                            reg = self.reg_manager.alloc_ftemp()
                            rd = self._resolve_dest(reg, self.REG_SCRATCH_F)
                            self.emit_f_type(OpCode.OP_F, reg, src_v, src_v, 0x01, F7.FSGNJ_D)
                            self._write_result(reg, rd)
                            
                        self.reg_manager.free_temp(reg_value)
                        return reg

                    case Operator.NOT:
                        return self.generate_not_expr(node)
                    
                    case Operator.BNOT:
                        reg_value = self.generate_expr(node.value)
                        src_v = self._read_operand(reg_value, self.REG_SCRATCH_X)
                        
                        reg = self.reg_manager.alloc_temp()
                        rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
                        
                        self.emit_i_type(OpCode.OP_IMM, F3_ALU.XOR_XORI, rd, src_v, -1)
                        self._write_result(reg, rd)
                        
                        self.reg_manager.free_temp(reg_value)
                        return reg
                        
            case VariableExpr():
                var = self.symbol_table.resolve(node.name)
                if var.is_global:
                    if var.zontype.num in [1, 3, 4, 6]:
                        reg_temp = self.reg_manager.alloc_temp()
                        reg_temp_s = self._read_operand(reg_temp, self.REG_SCRATCH_X)
                        self.emit_i_type(OpCode.L, F3_L.LD, reg_temp_s, 3, var.offset_global)
                        return ZonVar(reg_temp_s, RegT.X, var.zontype)
                    
                    elif var.zontype.num in [2, 7]:
                        reg_temp = self.reg_manager.alloc_ftemp()
                        reg_temp_s = self._read_operand(reg_temp, self.REG_SCRATCH_F)
                        self.emit_i_type(OpCode.FL, F3_FL.FLD, reg_temp_s, 3, var.offset_global)
                        return ZonVar(reg_temp_s, RegT.F, var.zontype)
                    
                return var
            
            case BlockExpr():
                exit_label = self.label_manager.create()
                self.value_block_exits.append(exit_label)
                self.symbol_table.enter_scope()
                self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -100)
                self.emit_ecall()
                
                regt = None
                for stmt in node.stmts:
                    if isinstance(stmt, GiveStmt):
                        regt, zontype = self.generate_stmt(stmt)
                    else:
                        self.generate_stmt(stmt)
                        
                self.symbol_table.exit_scope()
                self.label_manager.place_label(exit_label, self.get_pc())
                self.value_block_exits.pop()
                self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -101)
                self.emit_ecall()
                return ZonVar(10, regt, zontype)
        
            case IfForm():
                exit_label = self.label_manager.create()
                
                result_reg = self.reg_manager.alloc_temp()
                rd = self._resolve_dest(result_reg, self.REG_SCRATCH_X)
                
                if node.if_branch:
                    false_label = self.label_manager.create()
                    self.generate_cond(false_label, node.if_branch.cond)
                    value = self.generate_expr(node.if_branch.block)
                    src = self._read_operand(value, self.REG_SCRATCH_X if value.regt == RegT.X else self.REG_SCRATCH_F)
                    if value.regt == RegT.X:
                        self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, rd, src, 0)
                    else:
                        self.emit_f_type(OpCode.OP_F, rd, src, src, 0x00, F7.FSGNJ_D)
                        
                    result_reg.zontype = value.zontype
                    self.emit_jump(exit_label)
                    self.label_manager.place_label(false_label, self.get_pc())
                    
                if node.elif_branches:
                    for i, branch in enumerate(node.elif_branches):
                        if branch is None:
                            continue
                        
                        elif_label = self.label_manager.create()
                        self.generate_cond(elif_label, branch.cond)
                        value = self.generate_expr(branch.block)
                        src = self._read_operand(value, self.REG_SCRATCH_X if value.regt == RegT.X else self.REG_SCRATCH_F)
                        if value.regt == RegT.X:
                            self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, rd, src, 0)
                        else:
                            self.emit_f_type(OpCode.OP_F, rd, src, src, 0x00, F7.FSGNJ_D)
                        self.emit_jump(exit_label)
                        self.label_manager.place_label(elif_label, self.get_pc())
                
                value = self.generate_expr(node.else_branch.block)
                src = self._read_operand(value, self.REG_SCRATCH_X if value.regt == RegT.X else self.REG_SCRATCH_F)
                if value.regt == RegT.X:
                    self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, rd, src, 0)
                else:
                    self.emit_f_type(OpCode.OP_F, rd, src, src, 0x00, F7.FSGNJ_D)
                
                self.label_manager.place_label(exit_label, self.get_pc())
                
                self._write_result(result_reg, rd)
                return result_reg
            
            case CallFunc():
                if node.name == "alloc":
                    return self.emit_ecall_alloc_load(node, 0)
                elif node.name == "load":
                    return self.emit_ecall_alloc_load(node, 1)
                
                if node.params is not None:
                    param_counter = 10
                    fparam_counter = 10
                    for param in node.params:
                        reg = self.generate_expr(param)
                        src_reg = self._read_operand(reg, self.REG_SCRATCH_X if reg.regt == RegT.X else self.REG_SCRATCH_F)
                        if reg.regt == RegT.X:
                            self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, param_counter, src_reg, 0)
                            param_counter += 1
                        else:
                            self.emit_f_type(OpCode.OP_F, fparam_counter, src_reg, src_reg, 0x0, F7.FSGNJ_D)
                            fparam_counter += 1
                        self.reg_manager.free_temp(reg)
                    
                current_used_temps, current_used_ftemps = self.reg_manager.get_active_regs()
                current_offset = self.offset_stack[-1][0]
                for reg_num in current_used_temps:
                    self.emit_s(OpCode.OP_S, F3_S.SD, 2, reg_num, current_offset)
                    current_offset -= 8
                    
                for reg_num in current_used_ftemps:
                    self.emit_s(OpCode.OP_FS, F3_FS.FSD, 2, reg_num, current_offset)
                    current_offset -= 8
                    
                self.emit_jump(self.functions[node.name][0], rd=1)
                
                current_offset = self.offset_stack[-1][0]
                for reg_num in current_used_temps:
                    self.emit_i_type(OpCode.L, F3_L.LD, reg_num, 2, current_offset)
                    current_offset -= 8
                    
                for reg_num in current_used_ftemps:
                    self.emit_i_type(OpCode.FL, F3_FL.FLD, reg_num, 2, current_offset)
                    current_offset -= 8
                
                return_type = self.functions[node.name][1]
                
                if return_type.num in [1, 3, 4, 6]:
                    result = self.reg_manager.alloc_temp()
                    rd = self._resolve_dest(result, self.REG_SCRATCH_X)
                    self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, rd, 10, 0)
                    self._write_result(result, rd)
                    result.zontype = return_type
                    return result
                
                elif return_type.num in [2, 7]:
                    result = self.reg_manager.alloc_ftemp()
                    rd = self._resolve_dest(result, self.REG_SCRATCH_F)
                    self.emit_f_type(OpCode.OP_F, rd, 10, 10, 0x0, F7.FSGNJ_D)
                    self._write_result(result, rd)
                    return result
                
                else:
                    return ZonVar(10, None, return_type)
    
    def generate_xor_expr(self, node):
        if isinstance(node.left, IntLiteral) and node.left.value >= -2048 and node.left.value <= 2047:
            reg_right = self.generate_expr(node.right)
            src_r = self._read_operand(reg_right,self.REG_SCRATCH_X)
            reg = self.reg_manager.alloc_temp()
            rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.XOR_XORI, rd, src_r, node.left.value)
            self._write_result(reg, rd)
            self.reg_manager.free_temp(reg_right)
            return reg
        
        elif isinstance(node.right, IntLiteral) and node.right.value >= -2048 and node.right.value <= 2047:
            reg_left = self.generate_expr(node.left)
            src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
            reg = self.reg_manager.alloc_temp()
            rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.XOR_XORI, rd, src_l, node.right.value)
            self._write_result(reg, rd)
            self.reg_manager.free_temp(reg_left)
            return reg
            
        reg_left = self.generate_expr(node.left)
        reg_right = self.generate_expr(node.right)
        src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
        src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_X else self.REG_SCRATCH_X)
        reg = self.reg_manager.alloc_temp()
        rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
        self.emit_r_type(OpCode.OP, F3_ALU.XOR_XORI, F7.STANDARD, rd, src_l, src_r)
        self._write_result(reg, rd)
        self.reg_manager.free_temp(reg_left)
        self.reg_manager.free_temp(reg_right)
        return reg
    
    def generate_not_expr(self, node=None, reg_val=None, bit: bool = False):
        if not reg_val is None:
            src_v = self._read_operand(reg_val, self.REG_SCRATCH_X)
            reg = self.reg_manager.alloc_temp()
            rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.XOR_XORI, rd, src_v, -1 if bit else 1)
            self.reg_manager.free_temp(reg_val)
            self._write_result(reg, rd)
            
            return reg
            
        reg_value = self.generate_expr(node.value)
        src_v = self._read_operand(reg_value, self.REG_SCRATCH_X)
        reg = self.reg_manager.alloc_temp()
        rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
        self.emit_i_type(OpCode.OP_IMM, F3_ALU.XOR_XORI, rd, src_v, -1 if bit else 1)
        self.reg_manager.free_temp(reg_value)
        self._write_result(reg, rd)
        
        return reg
    
    def emit_eq_str(self, node):
        reg_left = self.generate_expr(node.left)
        reg_right = self.generate_expr(node.right)
        src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
        src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_X else self.REG_SCRATCH_X)
        reg = self.reg_manager.alloc_temp()
        rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
        self.emit_r_type(OpCode.OP_STR, F3_STR.CMP, F7_STR.STANDARD, rd, src_l, src_r)
        self._write_result(reg, rd)
        return reg
    
    def generate_eq_expr(self, node):
        if isinstance(node.left, (IntLiteral, BoolLiteral)):
            reg_right = self.generate_expr(node.right)
            src_r = self._read_operand(reg_right, self.REG_SCRATCH_X)
            reg_xor = self.reg_manager.alloc_temp()
            rd_xor = self._resolve_dest(reg_xor, self.REG_SCRATCH_X)
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.XOR_XORI, rd_xor, src_r, node.left.value)
            self._write_result(reg_xor, rd_xor)
            self.reg_manager.free_temp(reg_right)
            reg = self.reg_manager.alloc_temp()
            rd = self._resolve_dest(reg_xor, self.REG_SCRATCH_X)
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.SLTU_SLTIU, rd, reg_xor, 1)
            self.reg_manager.free_temp(reg_xor)
            self._write_result(reg, rd)
            
            return reg
        
        if isinstance(node.right, (IntLiteral, BoolLiteral)):
            reg_left = self.generate_expr(node.left)
            src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
            reg_xor = self.reg_manager.alloc_temp()
            rd_xor = self._resolve_dest(reg_xor, self.REG_SCRATCH_X)
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.XOR_XORI, rd_xor, src_l, node.right.value)
            self._write_result(reg_xor, rd_xor)
            self.reg_manager.free_temp(reg_left)
            reg = self.reg_manager.alloc_temp()
            rd = self._resolve_dest(reg_xor, self.REG_SCRATCH_X)
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.SLTU_SLTIU, rd, reg_xor, 1)
            self.reg_manager.free_temp(reg_xor)
            self._write_result(reg, rd)
            
            return reg
        
        reg_left = self.generate_expr(node.left)
        reg_right = self.generate_expr(node.right)
        if reg_left.regt == RegT.X:
            src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
            src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_X else self.REG_SCRATCH_X)
            reg_xor = self.reg_manager.alloc_temp()
            rd_xor = self._resolve_dest(reg_xor, self.REG_SCRATCH_X)
            self.emit_r_type(OpCode.OP, F3_ALU.XOR_XORI, F7.STANDARD, rd_xor, src_l, src_r)
            self._write_result(reg_xor, rd_xor)
            self.reg_manager.free_temp(reg_left)
            self.reg_manager.free_temp(reg_right)
            reg = self.reg_manager.alloc_temp()
            rd = self._resolve_dest(reg_xor, self.REG_SCRATCH_X)
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.SLTU_SLTIU, rd, reg_xor, 1)
            self.reg_manager.free_temp(reg_xor)
            self._write_result(reg, rd)
            return reg
        
        elif reg_left.regt == RegT.F:
            src_l = self._read_operand(reg_left, self.REG_SCRATCH_F)
            src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_F else self.REG_SCRATCH_F)
            reg = self.reg_manager.alloc_temp()
            rd = self._resolve_dest(reg_xor, self.REG_SCRATCH_F)
            self.emit_f_type(OpCode.OP_F, rd, src_l, src_r, 0x02, F7.FCOMP_S)
            self.reg_manager.free_temp(reg_left)
            self.reg_manager.free_temp(reg_right)
            self._write_result(reg, rd)
            return reg
     
    def generate_lt_expr(self, node):
        if isinstance(node.right, IntLiteral):
            reg_left = self.generate_expr(node.left)
            src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
            reg = self.reg_manager.alloc_temp()
            rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.SLT_SLTI, rd, src_l, node.right.value)
            self.reg_manager.free_temp(reg_left)
            self._write_result(reg, rd)
            
            return reg
        
        reg_left = self.generate_expr(node.left)
        reg_right = self.generate_expr(node.right)
        reg = self.reg_manager.alloc_temp()

        if reg_left.regt == RegT.X:
            src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
            src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_X else self.REG_SCRATCH_X)
            rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
            self.emit_r_type(OpCode.OP, F3_ALU.SLT_SLTI, F7.STANDARD, rd, src_l, src_r)
            self._write_result(reg, rd)

        elif reg_left.regt == RegT.F:
            src_l = self._read_operand(reg_left, self.REG_SCRATCH_F)
            src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_F else self.REG_SCRATCH_F)
            rd = self._resolve_dest(reg, self.REG_SCRATCH_F)
            self.emit_f_type(OpCode.OP_F, rd, src_l, src_r, 0x01, F7.FCOMP_S)
            self._write_result(reg, rd)
            
        self.reg_manager.free_temp(reg_left)
        self.reg_manager.free_temp(reg_right)
        return reg

    def generate_cond(self, label, node):
        match node:
            case BoolLiteral():
                reg_b = self.reg_manager.alloc_temp()
                self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, reg_b, 0x0, node.value)
                self.emit_b_type(OpCode.OP_B, F3_B.BEQ, reg_b, 0x0, label)
                self.reg_manager.free_temp(reg_b)
                
            case BinaryExpr():
                match node.operator:
                    case Operator.NE:
                        reg_left = self.generate_expr(node.left)
                        reg_right = self.generate_expr(node.right)
                        if reg_left.regt == RegT.X:
                            src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
                            src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_X else self.REG_SCRATCH_X)
                            self.emit_b_type(OpCode.OP_B, F3_B.BEQ, src_l, src_r, label)
                        elif reg_left.regt == RegT.F:
                            src_l = self._read_operand(reg_left, self.REG_SCRATCH_F)
                            src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_F else self.REG_SCRATCH_F)
                            reg_x = self.reg_manager.alloc_temp()
                            self.emit_f_type(OpCode.OP_F, reg_x, src_l, src_r, 0x02, F7.FCOMP_S)
                            self.emit_b_type(OpCode.OP_B, F3_B.BEQ, 0x0, reg_x, label)
                            self.reg_manager.free_temp(reg_x)
                        
                        self.reg_manager.free_temp(reg_left)
                        self.reg_manager.free_temp(reg_right)
                        
                    case Operator.EQ:
                        reg_left = self.generate_expr(node.left)
                        reg_right = self.generate_expr(node.right)
                        if reg_left.regt == RegT.X:
                            src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
                            src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_X else self.REG_SCRATCH_X)
                            self.emit_b_type(OpCode.OP_B, F3_B.BNE, src_l, src_r, label)
                            
                        elif reg_left.regt == RegT.F:
                            src_l = self._read_operand(reg_left, self.REG_SCRATCH_F)
                            src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_F else self.REG_SCRATCH_F)
                            reg_x = self.reg_manager.alloc_temp()
                            self.emit_f_type(OpCode.OP_F, reg_x, src_l, src_r, 0x02, F7.FCOMP_S)
                            self.emit_b_type(OpCode.OP_B, F3_B.BEQ, 0x0, reg_x, label)
                            self.reg_manager.free_temp(reg_x)
                            
                        self.reg_manager.free_temp(reg_left)
                        self.reg_manager.free_temp(reg_right)
                        
                    case Operator.LT: self.generate_cond_lt(label, node)
                    case Operator.GT:
                        right = node.right
                        node.right = node.left
                        node.left = right
                        self.generate_cond_lt(label, node)
                    case Operator.LE:
                        right = node.right
                        node.right = node.left
                        node.left = right
                        self.generate_cond_ge(label, node)
                    case Operator.GE: self.generate_cond_ge(label, node)
                    case Operator.AND: self.generate_cond_and(node, label)
                    case Operator.OR: self.generate_cond_or(node, label)
                        
            case VariableExpr():
                var = self.symbol_table.resolve(node.name)
                src_v = self._read_operand(var, self.REG_SCRATCH_X)
                self.emit_b_type(OpCode.OP_B, F3_B.BEQ, src_v, 0x0, label)
                
    def generate_cond_and(self, node, label=None, reg_x=None):
        reg_left = self.generate_expr(node.left)
        src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
        false_l = self.label_manager.create()
        exit = self.label_manager.create()
        
        if label is None:
            self.emit_b_type(OpCode.OP_B, F3_B.BEQ, src_l, 0x0, false_l)
        else:
            self.emit_b_type(OpCode.OP_B, F3_B.BEQ, src_l, 0x0, label)
        
        self.reg_manager.free_temp(reg_left)
        reg_right = self.generate_expr(node.right)
        src_r = self._read_operand(reg_right, self.REG_SCRATCH_X)
        
        if label is None:
            self.emit_b_type(OpCode.OP_B, F3_B.BEQ, src_r, 0x0, false_l)
        else:
            self.emit_b_type(OpCode.OP_B, F3_B.BEQ, src_r, 0x0, label)
        
        self.reg_manager.free_temp(reg_right)
        
        if label is None:
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, reg_x, 0x0, 1)
            self.emit_jump(exit)
            self.label_manager.place_label(false_l, self.get_pc())
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, reg_x, 0x0, 0)
            self.label_manager.place_label(exit, self.get_pc())
             
    def generate_cond_lt(self, label, node):
        reg_left = self.generate_expr(node.left)
        reg_right = self.generate_expr(node.right)
        if reg_left.regt == RegT.X:
            src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
            src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_X else self.REG_SCRATCH_X)
            self.emit_b_type(OpCode.OP_B, F3_B.BGE, src_l, src_r, label)
        elif reg_left.regt == RegT.F:
            src_l = self._read_operand(reg_left, self.REG_SCRATCH_F)
            src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_F else self.REG_SCRATCH_F)
            reg_x = self.reg_manager.alloc_temp()
            self.emit_f_type(OpCode.OP_F, reg_x, src_l, src_r, 0x01, F7.FCOMP_S)
            self.emit_b_type(OpCode.OP_B, F3_B.BEQ, 0x0, reg_x, label)
            self.reg_manager.free_temp(reg_x)
        
        self.reg_manager.free_temp(reg_left)
        self.reg_manager.free_temp(reg_right)
        
    def generate_cond_ge(self, label, node):
        reg_left = self.generate_expr(node.left)
        reg_right = self.generate_expr(node.right)
        if reg_left.regt == RegT.X:
            src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
            src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_X else self.REG_SCRATCH_X)
            self.emit_b_type(OpCode.OP_B, F3_B.BLT, src_l, src_r, label)
        elif reg_left.regt == RegT.F:
            src_l = self._read_operand(reg_left, self.REG_SCRATCH_F)
            src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_F else self.REG_SCRATCH_F)
            reg_x = self.reg_manager.alloc_temp()
            self.emit_f_type(OpCode.OP_F, reg_x, src_r, src_l, 0x00, F7.FCOMP_S)
            self.emit_b_type(OpCode.OP_B, F3_B.BEQ, 0x0, reg_x, label)
            self.reg_manager.free_temp(reg_x)
            
        self.reg_manager.free_temp(reg_left)
        self.reg_manager.free_temp(reg_right)
    
    def generate_and_expr(self, node):
        if isinstance(node.left, (VariableExpr, IntLiteral)) or isinstance(node.right, (VariableExpr, IntLiteral)):
            if isinstance(node.left, IntLiteral) and node.left.value >= -2048 and node.left.value <= 2047:
                reg_right = self.generate_expr(node.right)
                src_r = self._read_operand(reg_right, self.REG_SCRATCH_X)
                reg = self.reg_manager.alloc_temp()
                rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
                self.emit_i_type(OpCode.OP_IMM, F3_ALU.AND_ANDI, reg, src_r, node.left.value)
                self.reg_manager.free_temp(reg_right)
                self._write_result(reg, rd)

                return reg
            
            if isinstance(node.right, IntLiteral) and node.right.value >= -2048 and node.right.value <= 2047:
                reg_left = self.generate_expr(node.left)
                src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
                reg = self.reg_manager.alloc_temp()
                rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
                self.emit_i_type(OpCode.OP_IMM, F3_ALU.AND_ANDI, reg, src_l, node.right.value)
                self.reg_manager.free_temp(reg_left)
                self._write_result(reg, rd)

                return reg
                
            reg_left = self.generate_expr(node.left)
            reg_right = self.generate_expr(node.right)
            src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
            src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_X else self.REG_SCRATCH_X)
            reg = self.reg_manager.alloc_temp()
            rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
            self.emit_r_type(OpCode.OP, F3_ALU.AND_ANDI, F7.STANDARD, rd, src_l, src_r)
            self._write_result(reg, rd)
            self.reg_manager.free_temp(reg_left)
            self.reg_manager.free_temp(reg_right)
            
            return reg
        
        reg = self.reg_manager.alloc_temp()
        self.generate_cond_and(node, reg_x=reg)
        return reg
    
    def generate_or_expr(self, node):
        if isinstance(node.left, (VariableExpr, IntLiteral)) or isinstance(node.right, (VariableExpr, IntLiteral)):
            if isinstance(node.left, IntLiteral) and node.left.value >= -2048 and node.left.value <= 2047:
                reg_right = self.generate_expr(node.right)
                src_r = self._read_operand(reg_right, self.REG_SCRATCH_X)
                reg = self.reg_manager.alloc_temp()
                rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
                self.emit_i_type(OpCode.OP_IMM, F3_ALU.OR_ORI, rd, src_r, node.left.value)
                self.reg_manager.free_temp(reg_right)
                self._write_result(reg, rd)

                return reg
            
            if isinstance(node.right, IntLiteral) and node.right.value >= -2048 and node.right.value <= 2047:
                reg_left = self.generate_expr(node.left)
                src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
                reg = self.reg_manager.alloc_temp()
                rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
                self.emit_i_type(OpCode.OP_IMM, F3_ALU.OR_ORI, rd, src_l, node.right.value)
                self.reg_manager.free_temp(reg_left)
                self._write_result(reg, rd)

                return reg
                
            reg_left = self.generate_expr(node.left)
            reg_right = self.generate_expr(node.right)
            src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
            src_r = self._read_operand(reg_right, 30 if src_l == self.REG_SCRATCH_X else self.REG_SCRATCH_X)
            reg = self.reg_manager.alloc_temp()
            rd = self._resolve_dest(reg, self.REG_SCRATCH_X)
            self.emit_r_type(OpCode.OP, F3_ALU.OR_ORI, F7.STANDARD, rd, src_l, src_r)
            self._write_result(reg, rd)

            self.reg_manager.free_temp(reg_left)
            self.reg_manager.free_temp(reg_right)
            return reg
        
        reg = self.reg_manager.alloc_temp()
        self.generate_cond_or(node, reg_x=reg)
        return reg
    
    def generate_cond_or(self, node, label=None, reg_x=None):
        reg_left = self.generate_expr(node.left)
        src_l = self._read_operand(reg_left, self.REG_SCRATCH_X)
        true_l = self.label_manager.create()
        exit = self.label_manager.create()
        if label is None:
            self.emit_b_type(OpCode.OP_B, F3_B.BNE, src_l, 0x0, true_l)
        else:
            self.emit_b_type(OpCode.OP_B, F3_B.BNE, src_l, 0x0, label)
        
        self.reg_manager.free_temp(reg_left)
        reg_right = self.generate_expr(node.right)
        src_r = self._read_operand(reg_right, self.REG_SCRATCH_X)
        
        if label is None:
            self.emit_b_type(OpCode.OP_B, F3_B.BNE, src_r, 0x0, true_l)
        else:
            self.emit_b_type(OpCode.OP_B, F3_B.BNE, src_r, 0x0, label)
        
        self.reg_manager.free_temp(reg_right)
        
        if label is None:
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, reg_x, 0x0, 0)
            self.emit_jump(exit)
            self.label_manager.place_label(true_l, self.get_pc())
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, reg_x, 0x0, 1)
            self.label_manager.place_label(exit, self.get_pc())