"""RISC-V instruction emitters and binary encoders.

Two kinds of functions live here:

  emit_*   — append an instruction (or a placeholder) to emitter.code.
             Branch and jump targets use placeholder namedtuples that the
             linker pass in Emitter.save() resolves to real offsets later.

  generate_* — encode an already-resolved instruction to 4 raw bytes.
               Called by the linker pass, never during code generation.

Instruction formats
--------------------
  R-type  funct7 | rs2 | rs1 | funct3 | rd | opcode
  I-type  imm[11:0]   | rs1 | funct3 | rd | opcode
  S-type  imm[11:5] | rs2 | rs1 | funct3 | imm[4:0] | opcode
  B-type  imm[12|10:5] | rs2 | rs1 | funct3 | imm[4:1|11] | opcode
  U-type  imm[31:12] | rd | opcode
  J-type  imm[20|10:1|11|19:12] | rd | opcode
  F-type  funct7 | rs2 | rs1 | rm | rd | opcode   (floating-point)
"""

from collections import namedtuple
from .opcode import *
from zonc.zonast import ZonType, IntLiteral
from .bytecodescope import RegT, ZonVar
from .rodata import generate_literal_num


# ------------------------------------------------------------------
# Instruction placeholders (resolved by the linker pass in Emitter.save)
# ------------------------------------------------------------------

# Branch instruction — offset filled in at link time
IntsB = namedtuple("IntsB", ["rs1", "rs2", "opc", "f3", "label"])

# JAL instruction — offset filled in at link time
IntsJ = namedtuple("IntsJ", ["opc", "label", "rd"])

# JALR instruction — always offset 0 (return / indirect call)
InstJR = namedtuple("InstJR", ["rd", "rs1"])

# AUIPC + FLD/LD pair for loading a float or int constant from .rodata
ConstantLoad = namedtuple("ConstantLoad", ["rd", "rd_int", "pool_offset", "is_float"])

# AUIPC + ADDI pair for loading the address of a string from .rodata
AddressLoad = namedtuple("AddressLoad", ["rd", "pool_offset"])


# ------------------------------------------------------------------
# Emit helpers — append to emitter.code
# ------------------------------------------------------------------

def emit_r_type(emitter, opcode, funct3, funct7, rd, rs1, rs2) -> None:
    rd     = emitter._unwrap(rd)  & 0x1F
    rs1    = emitter._unwrap(rs1) & 0x1F
    rs2    = emitter._unwrap(rs2) & 0x1F
    funct3 &= 0x7
    funct7 &= 0x7F
    opcode &= 0x7F
    inst = (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode
    emitter.code.append(inst.to_bytes(4, "little"))


def emit_i_type(emitter, opcode, funct3, rd, rs1, imm) -> None:
    rd     = emitter._unwrap(rd)  & 0x1F
    rs1    = emitter._unwrap(rs1) & 0x1F
    funct3 &= 0x7
    imm    &= 0xFFF
    opcode &= 0x7F
    inst = (imm << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode
    emitter.code.append(inst.to_bytes(4, "little"))


def emit_s(emitter, opcode, funct3, rs1, rs2, imm) -> None:
    rs1    = emitter._unwrap(rs1) & 0x1F
    rs2    = emitter._unwrap(rs2) & 0x1F
    funct3 &= 0x7
    opcode &= 0x7F
    imm    &= 0xFFF
    imm_11_5 = (imm >> 5) & 0x7F
    imm_4_0  =  imm       & 0x1F
    inst = (imm_11_5 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (imm_4_0 << 7) | opcode
    emitter.code.append(inst.to_bytes(4, "little"))


def emit_u_type(emitter, opcode, rd, imm) -> None:
    rd     = emitter._unwrap(rd) & 0x1F
    opcode &= 0x7F
    inst = (imm << 12) | (rd << 7) | opcode
    emitter.code.append(inst.to_bytes(4, "little"))


def emit_f_type(emitter, opcode, rd, rs1, rs2, rm, f7) -> None:
    """Floating-point R-type: uses rm (rounding mode) instead of funct3."""
    rd     = emitter._unwrap(rd)  & 0x1F
    rs1    = emitter._unwrap(rs1) & 0x1F
    rs2    = emitter._unwrap(rs2) & 0x1F
    rm    &= 0x7
    f7    &= 0x7F
    opcode &= 0x7F
    inst = (f7 << 25) | (rs2 << 20) | (rs1 << 15) | (rm << 12) | (rd << 7) | opcode
    emitter.code.append(inst.to_bytes(4, "little"))


def emit_b_type(emitter, opcode, f3, rs1, rs2, label) -> None:
    """Append a branch placeholder — offset resolved at link time."""
    emitter.code.append(IntsB(
        rs1=emitter._unwrap(rs1),
        rs2=emitter._unwrap(rs2),
        f3=f3, opc=opcode, label=label,
    ))


def emit_j_type(emitter, opcode, rd, label) -> None:
    """Append a JAL placeholder — offset resolved at link time."""
    emitter.code.append(IntsJ(rd=emitter._unwrap(rd), opc=opcode, label=label))


def emit_jalr(emitter, rd, rs1) -> None:
    """Append a JALR instruction (always offset 0 — return or indirect call)."""
    emitter.code.append(InstJR(rd=emitter._unwrap(rd), rs1=emitter._unwrap(rs1)))


def emit_jump(emitter, label, rd: int = 0) -> None:
    """Unconditional jump to label. rd=1 saves the return address (call)."""
    emit_j_type(emitter, OpCode.JAL, rd, label)


def emit_ecall(emitter) -> None:
    emitter.code.append((0x73).to_bytes(4, "little"))


# ------------------------------------------------------------------
# Binary encoders — called by the linker pass, not during codegen
# ------------------------------------------------------------------

def generate_b_type(inst: IntsB, offset: int) -> bytes:
    """Encode a branch instruction with the resolved byte offset."""
    b12   = (offset >> 12) & 0x1
    b11   = (offset >> 11) & 0x1
    b10_5 = (offset >>  5) & 0x3F
    b4_1  = (offset >>  1) & 0xF
    word = (
        (b12   << 31) | (b10_5 << 25) | (inst.rs2 << 20) | (inst.rs1 << 15) |
        (inst.f3 << 12) | (b4_1  <<  8) | (b11  <<  7) | (inst.opc & 0x7F)
    )
    return word.to_bytes(4, "little")


def generate_j_type(inst: IntsJ, offset: int) -> bytes:
    """Encode a JAL instruction with the resolved byte offset."""
    imm_20    = (offset >> 20) & 0x1
    imm_10_1  = (offset >>  1) & 0x3FF
    imm_11    = (offset >> 11) & 0x1
    imm_19_12 = (offset >> 12) & 0xFF
    word = (
        (imm_20 << 31) | (imm_10_1 << 21) | (imm_11 << 20) |
        (imm_19_12 << 12) | (inst.rd << 7) | inst.opc
    )
    return word.to_bytes(4, "little")


def generate_i_type_jalr(inst: InstJR, offset: int = 0) -> bytes:
    """Encode a JALR instruction (opcode 0x67, funct3 0)."""
    imm    = offset & 0xFFF
    rd     = inst.rd  & 0x1F
    rs1    = inst.rs1 & 0x1F
    word = (imm << 20) | (rs1 << 15) | (rd << 7) | 0x67
    return word.to_bytes(4, "little")


# ------------------------------------------------------------------
# Ecall helpers for heap built-ins
# ------------------------------------------------------------------

def emit_ecall_store(emitter, node) -> None:
    """Emit the argument setup and ecall for the built-in `store` function."""
    from .expr_gen import generate_expr

    for i, param in enumerate(node.params):
        if isinstance(param, IntLiteral):
            generate_literal_num(emitter, param.value, 10 + i)
        else:
            reg = generate_expr(emitter, param)
            src = emitter._read_operand(reg, emitter.REG_SCRATCH_X)
            emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 10 + i, src, 0)
            emitter.reg_manager.free_temp(reg)

    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -103)
    emit_ecall(emitter)


def emit_ecall_alloc_load(emitter, node, flag: int) -> ZonVar:
    """Emit the argument setup and ecall for `alloc` (flag=0) or `load` (flag=1).
    Returns a ZonVar pointing to a0 which holds the result.
    """
    from .expr_gen import generate_expr

    param = node.params[0]
    if isinstance(param, IntLiteral):
        generate_literal_num(emitter, param.value, 10)
    else:
        reg = generate_expr(emitter, param)
        src = emitter._read_operand(reg, emitter.REG_SCRATCH_X)
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 10, src, 0)
        emitter.reg_manager.free_temp(reg)

    # ecall codes: -102 = alloc, -104 = load
    ecall_code = -102 if flag == 0 else -104
    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, ecall_code)
    emit_ecall(emitter)
    return ZonVar(10, RegT.X, ZonType(1, "int64"))