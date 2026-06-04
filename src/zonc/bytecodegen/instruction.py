from collections import namedtuple
from .opcode import *
from zonc.zonast import ZonType, IntLiteral
from .bytecodescope import RegT, ZonVar
from .rodata import generate_literal_num


IntsB = namedtuple("IntsB", ["rs1", "rs2", "opc", "f3", "label"])
IntsJ = namedtuple("IntsJ", ["opc", "label", "rd"])
InstJR = namedtuple("InstJR", ["rd", "rs1"])
ConstantLoad = namedtuple("ConstantLoad", ["rd", "rd_int", "pool_offset", "is_float"])
AddressLoad = namedtuple("AddressLoad", ["rd", "pool_offset"])

def emit_r_type(emitter, opcode, funct3, funct7, rd, rs1, rs2):
    rd = emitter._unwrap(rd) & 0x1F
    rs1 = emitter._unwrap(rs1) & 0x1F
    rs2 = emitter._unwrap(rs2) & 0x1F
    funct3 &= 0x7
    funct7 &= 0x7F
    opcode &= 0x7F
    inst = (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode
    emitter.code.append(inst.to_bytes(4, "little"))

def emit_s(emitter, opcode, funct3, rs1, rs2, imm):
    opcode &= 0x7F
    funct3 &= 0x7
    rs1 = emitter._unwrap(rs1) & 0x1F
    rs2 = emitter._unwrap(rs2) & 0x1F
    imm &= 0xFFF
    imm_11_5 = (imm >> 5) & 0x7F
    imm_4_0 = imm & 0x1F
    inst = (imm_11_5 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (imm_4_0 << 7) | opcode
    emitter.code.append(inst.to_bytes(4, "little"))

def emit_i_type(emitter, opcode, funct3, rd, rs1, imm):
    rd = emitter._unwrap(rd) & 0x1F
    rs1 = emitter._unwrap(rs1) & 0x1F
    funct3 &= 0x7
    imm &= 0xFFF
    opcode &= 0x7F
    inst = (imm << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode
    emitter.code.append(inst.to_bytes(4, "little"))

def emit_b_type(emitter, opcode, f3, rs1, rs2, label):
    rs1 = emitter._unwrap(rs1)
    rs2 = emitter._unwrap(rs2)
    emitter.code.append(IntsB(rs1=rs1, rs2=rs2, f3=f3, opc=opcode, label=label))

def emit_j_type(emitter, opcode, rd, label):
    rd = emitter._unwrap(rd)
    emitter.code.append(IntsJ(rd=rd, opc=opcode, label=label))

def emit_jalr(emitter, rd, rs1):
    rd = emitter._unwrap(rd)
    rs1 = emitter._unwrap(rs1)
    emitter.code.append(InstJR(rd=rd, rs1=rs1))

def emit_u_type(emitter, opcode, rd, imm):
    rd = emitter._unwrap(rd) & 0x1F
    opcode &= 0x7F
    inst = (imm << 12) | (rd << 7) | opcode
    emitter.code.append(inst.to_bytes(4, "little"))

def emit_f_type(emitter, opcode, rd, rs1, rs2, rm, f7):
    rd = emitter._unwrap(rd) & 0x1F
    rs1 = emitter._unwrap(rs1) & 0x1F
    rs2 = emitter._unwrap(rs2) & 0x1F
    rm &= 0x7
    f7 &= 0x7F
    opcode &= 0x7F
    inst = (f7 << 25) | (rs2 << 20) | (rs1 << 15) | (rm << 12) | (rd << 7) | opcode
    emitter.code.append(inst.to_bytes(4, "little"))

def emit_ecall(emitter):
    emitter.code.append(0x73.to_bytes(4, "little"))

def emit_jump(emitter, label, rd=0):
    emit_j_type(emitter, OpCode.JAL, rd, label)

def generate_b_type(instruction, offset):
    val = offset
    b12   = (val >> 12) & 0x1
    b11   = (val >> 11) & 0x1
    b10_5 = (val >> 5)  & 0x3F
    b4_1  = (val >> 1)  & 0xF
    inst = (b12 << 31) | (b10_5 << 25) | (instruction.rs2 << 20) | (instruction.rs1 << 15) | \
            (instruction.f3 << 12) | (b4_1 << 8) | (b11 << 7) | (instruction.opc & 0x7F)
            
    return inst.to_bytes(4, "little")

def generate_j_type(instruction, offset):
    val = offset
    imm_20    = (val >> 20) & 0x1
    imm_10_1  = (val >> 1)  & 0x3FF
    imm_11    = (val >> 11) & 0x1
    imm_19_12 = (val >> 12) & 0xFF
    inst = (imm_20 << 31) | (imm_10_1 << 21) | (imm_11 << 20) | \
            (imm_19_12 << 12) | (instruction.rd << 7) | (instruction.opc)
            
    return inst.to_bytes(4, "little")

def generate_i_type_jalr(instruction, offset=0):
    val = offset & 0xFFF
    rd = instruction.rd & 0x1F
    rs1 = instruction.rs1 & 0x1F
    funct3 = 0x0
    opcode = 0x67 & 0x7F
    inst = (val << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode
    return inst.to_bytes(4, "little")

def emit_ecall_store(emitter, node):
    from .expr_gen import generate_expr
    
    for i, param in enumerate(node.params):
        if isinstance(param, IntLiteral):
            generate_literal_num(emitter, param.value, 10+i)
            
        else:
            reg_param = generate_expr(emitter, param)
            src_reg = emitter._read_operand(reg_param, emitter.REG_SCRATCH_X)
            emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 10+i, src_reg, 0)
            emitter.reg_manager.free_temp(reg_param)
            
    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0x0, -103)
    emit_ecall(emitter)

def emit_ecall_alloc_load(emitter, node, flag):
    from .expr_gen import generate_expr
    if isinstance(node.params[0], IntLiteral):
        generate_literal_num(emitter, node.params[0].value, 10)
        
    else:
        reg_param = generate_expr(emitter, node.params[0])
        src_reg = emitter._read_operand(reg_param, emitter.REG_SCRATCH_X)
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 10, src_reg, 0)
        emitter.reg_manager.free_temp(reg_param)
        
    code = -102 if flag == 0 else -104
    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0x0, code)
    emit_ecall(emitter)
    return ZonVar(10, RegT.X, ZonType(1, "int64"))