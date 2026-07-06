"""Read-only data section (.rodata) helpers.

Constants that cannot be encoded as 12-bit immediates (large integers,
all floats, strings) are stored in the .rodata pool and loaded at
runtime via an AUIPC + LD/FLD pair.

Pool layout
-----------
  - Numbers (int/float): 8 bytes, little-endian packed as int64/double.
  - Strings: 8-byte length prefix (little-endian) followed by ASCII bytes.

Deduplication: both number and string pools are keyed by value so the
same constant is only stored once regardless of how many times it appears
in the source.
"""

import struct
from .opcode import *
from .bytecodescope import ZonVar


# ------------------------------------------------------------------
# Pool management
# ------------------------------------------------------------------

def _pool_add_number(emitter, bits: int) -> int:
    """Store a 64-bit value in the pool (if not already there).
    Returns the byte offset of the value inside pool_data.
    """
    if bits not in emitter.constant_pool:
        emitter.constant_pool[bits] = len(emitter.pool_data)
        emitter.pool_data.extend(struct.pack('<q', bits))
    return emitter.constant_pool[bits]


def add_string_to_pool(emitter, s: str) -> int:
    """Store a string in the pool (if not already there).
    Format: 8-byte little-endian length prefix + ASCII bytes.
    Returns the byte offset of the entry inside pool_data.
    """
    if s in emitter.string_pool:
        return emitter.string_pool[s]

    length_bytes = bytearray(
        (len(s) >> (8 * i)) & 0xFF for i in range(8)
    )
    offset = len(emitter.pool_data)
    emitter.pool_data.extend(length_bytes + s.encode('ascii'))
    emitter.string_pool[s] = offset
    return offset


# ------------------------------------------------------------------
# Literal emitters
# ------------------------------------------------------------------

def generate_literal_num(emitter, imm: int, reg) -> None:
    """Emit the shortest instruction sequence to load imm into reg.

    Strategy:
      imm fits in 12 bits  → single ADDI from x0
      imm fits in 32 bits  → LUI + ADDI (emit_li)
      larger               → store in .rodata, load via AUIPC + LD
    """
    from .instruction import emit_i_type, ConstantLoad

    target = emitter._unwrap(reg)

    if -2048 <= imm <= 2047:
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, target, 0, imm)

    elif -2_147_000_000 <= imm <= 2_147_000_000:
        _emit_li(emitter, imm, target)

    else:
        pool_offset = _pool_add_number(emitter, imm)
        addr_reg    = emitter.reg_manager.alloc_temp()
        emitter.code.append(ConstantLoad(
            rd=target, rd_int=addr_reg.reg,
            pool_offset=pool_offset, is_float=False,
        ))
        emitter.code.append("DUMMY")  # placeholder for the paired LD
        emitter.reg_manager.free_temp(addr_reg)

    # if reg was spilled, write the result back to the stack slot
    if isinstance(reg, ZonVar) and reg.reg is None:
        emitter._write_result(reg, target)


def generate_literal_f(emitter, imm: float, reg) -> None:
    """Store a double literal in .rodata and emit AUIPC + FLD to load it."""
    from .instruction import ConstantLoad

    bits        = struct.unpack('<q', struct.pack('<d', imm))[0]
    pool_offset = _pool_add_number(emitter, bits)
    addr_reg    = emitter.reg_manager.alloc_temp()
    target      = emitter._unwrap(reg)

    emitter.code.append(ConstantLoad(
        rd=target, rd_int=addr_reg.reg,
        pool_offset=pool_offset, is_float=True,
    ))
    emitter.code.append("DUMMY")  # placeholder for the paired FLD
    emitter.reg_manager.free_temp(addr_reg)

    if isinstance(reg, ZonVar) and reg.reg is None:
        emitter._write_result(reg, target)


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _emit_li(emitter, n: int, reg: int) -> None:
    """Emit LUI + ADDI to load a 32-bit immediate into reg."""
    from .instruction import emit_u_type, emit_i_type

    low  =  n & 0xFFF
    high = (n >> 12) + (1 if low & 0x800 else 0)
    high &= 0xFFFFF

    emit_u_type(emitter, OpCode.LUI, reg, high)
    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, reg, reg, low)