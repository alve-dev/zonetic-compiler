from zonc.zonast import *
from .opcode import *
from .register_manager import RegisterManager
from .bytecodescope import SymbolTable, RegT, ZonVar
from collections import namedtuple
import struct

# Importar funciones necesarias para save
from .instruction import IntsB, IntsJ, InstJR, ConstantLoad, AddressLoad, generate_b_type, generate_j_type, generate_i_type_jalr
from .func_gen import generate_program_entry

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

    def get_pc(self):
        return len(self.code)
    
    def _unwrap(self, reg):
        if isinstance(reg, int):
            return reg
        
        return reg.reg
    
    def _resolve_dest(self, reg: ZonVar, scratch: int) -> int:
        if isinstance(reg, int):
            return reg
        
        return reg.reg if reg.reg is not None else scratch

    def _read_operand(self, zonvar: ZonVar, scratch_reg: int):
        from .instruction import emit_i_type
        if zonvar.reg is not None:
            return zonvar.reg
        
        offset_val = zonvar.offset_stack[0] if isinstance(zonvar.offset_stack, list) else zonvar.offset_stack
        if zonvar.regt == RegT.X:
            emit_i_type(self, OpCode.L, F3_L.LD, scratch_reg, 8, offset_val)
            return scratch_reg
        
        elif zonvar.regt == RegT.F:
            emit_i_type(self, OpCode.FL, F3_FL.FLD, scratch_reg, 8, offset_val)
            return scratch_reg
        
        return self._unwrap(zonvar)

    def _write_result(self, dest_zonvar: ZonVar, source_reg: int):
        from .instruction import emit_s
        if dest_zonvar.reg is not None:
            return
        
        offset_val = dest_zonvar.offset_stack[0] if isinstance(dest_zonvar.offset_stack, list) else dest_zonvar.offset_stack

        if dest_zonvar.regt == RegT.X:
            emit_s(self, OpCode.OP_S, F3_S.SD, 8, source_reg, offset_val)
            
        elif dest_zonvar.regt == RegT.F:
            emit_s(self, OpCode.OP_FS, F3_FS.FSD, 8, source_reg, offset_val)

    def save(self, stmts, filename):
        generate_program_entry(self, stmts)
        
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
                    f.write(generate_b_type(inst, offset))

                elif isinstance(inst, IntsJ):
                    target_pc = self.label_manager.labels[inst.label]
                    offset = target_pc - current_pc
                    f.write(generate_j_type(inst, offset))
                
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
                    f.write(generate_i_type_jalr(inst))
                    
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