import struct
from .opcode import *
from .bytecodescope import ZonVar

def add_to_pool(emitter, value_bits):
    if value_bits not in emitter.constant_pool:
        offset = len(emitter.pool_data)
        emitter.constant_pool[value_bits] = offset
        emitter.pool_data.extend(struct.pack('<q', value_bits))
        
    return emitter.constant_pool[value_bits]

def add_string_to_pool(emitter, s: str) -> int:
    if s in emitter.string_pool:
        return emitter.string_pool[s]
    
    length = len(s)
    len_bytes = bytearray()
    
    for i in range(8):
        len_bytes.append((length >> (8 * i)) & 0xFF)
        
    data_bytes = s.encode('ascii')
    full_bytes = len_bytes + data_bytes
    offset = len(emitter.pool_data)
    emitter.pool_data.extend(full_bytes)
    emitter.string_pool[s] = offset
    return offset

def generate_literal_num(emitter, imm, reg):
    from .instruction import emit_i_type, ConstantLoad
    target_reg = emitter._unwrap(reg)
    
    if imm >= -2048 and imm <= 2047:
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, target_reg, 0x0, imm)
        
    elif imm >= -2_147_000_000 and imm <= 2_147_000_000:
        emit_li(emitter, imm, target_reg)
        
    else:
        pool_offset = add_to_pool(emitter, imm)
        reg_addr = emitter.reg_manager.alloc_temp()
        emitter.code.append(ConstantLoad(rd=target_reg, rd_int=reg_addr.reg, pool_offset=pool_offset, is_float=False))
        emitter.code.append("DUMMY")
        emitter.reg_manager.free_temp(reg_addr)
        
    if isinstance(reg, ZonVar) and reg.reg is None:
        emitter._write_result(reg, target_reg)

def float_to_bits(f):
    return struct.unpack('<q', struct.pack('<d', f))[0]

def generate_literal_f(emitter, imm, reg):
    from .instruction import ConstantLoad
    bits = float_to_bits(imm)
    pool_offset = add_to_pool(emitter, bits)
    reg_addr = emitter.reg_manager.alloc_temp()
    target_reg = emitter._unwrap(reg)
    emitter.code.append(ConstantLoad(rd=target_reg, rd_int=reg_addr.reg, pool_offset=pool_offset, is_float=True))
    emitter.code.append("DUMMY")
    emitter.reg_manager.free_temp(reg_addr)
    
    if isinstance(reg, ZonVar) and reg.reg is None:
        emitter._write_result(reg, target_reg)

def emit_li(emitter, n, reg):
    low = n & 0xFFF
    high = n >> 12
    if low & 0x800:
        high += 1
    high &= 0xFFFFF
    
    from .instruction import emit_u_type, emit_i_type
    emit_u_type(emitter, OpCode.LUI, reg, high)
    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, reg, reg, low)