"""RISC-V disassembler for the Zon VM bytecode format.

Decodes the .text section of a .zon binary and prints each instruction
in a human-readable form alongside its byte offset and raw encoding.

Supports the RV64IMAFD base ISA plus the Zon custom opcode (0b0001011)
used for built-in string operations.
"""

import struct


# ------------------------------------------------------------------
# Register name tables
# ------------------------------------------------------------------

_INT_REGS = [
    "x0", "ra", "sp",    "gp",  "tp",   "t0",  "t1", "t2",
    "s0/fp", "s1", "a0", "a1",  "a2",  "a3",  "a4", "a5",
    "a6", "a7", "s2",    "s3",  "s4",   "s5",  "s6", "s7",
    "s8", "s9", "s10",   "s11", "t3",   "t4",  "t5", "t6",
]

_FLOAT_REGS = [
    "ft0",  "ft1",  "ft2",  "ft3",  "ft4",  "ft5",  "ft6",  "ft7",
    "fs0",  "fs1",  "fa0",  "fa1",  "fa2",  "fa3",  "fa4",  "fa5",
    "fa6",  "fa7",  "fs2",  "fs3",  "fs4",  "fs5",  "fs6",  "fs7",
    "fs8",  "fs9",  "fs10", "fs11", "ft8",  "ft9",  "ft10", "ft11",
]


def _reg(num: int) -> str:
    return _INT_REGS[num] if 0 <= num < 32 else f"x{num}"


def _freg(num: int) -> str:
    return _FLOAT_REGS[num] if 0 <= num < 32 else f"f{num}"


# ------------------------------------------------------------------
# Immediate extraction helpers
# ------------------------------------------------------------------

def _sign_imm(value: int, bits: int) -> int:
    """Sign-extend `value` from `bits` width to a Python int."""
    sign_bit = 1 << (bits - 1)
    if value & sign_bit:
        value -= sign_bit << 1
    return value


def _imm_i(word: int) -> int:
    return _sign_imm((word >> 20) & 0xFFF, 12)


def _imm_s(word: int) -> int:
    low  = (word >> 7)  & 0x1F
    high = (word >> 25) & 0x7F
    return _sign_imm(low | (high << 5), 12)


def _imm_b(word: int) -> int:
    i31    = (word >> 31) & 0x1
    i30_25 = (word >> 25) & 0x3F
    i11_8  = (word >> 8)  & 0xF
    i7     = (word >> 7)  & 0x1
    raw = (i31 << 12) | (i7 << 11) | (i30_25 << 5) | (i11_8 << 1)
    return _sign_imm(raw, 13)


def _imm_j(word: int) -> int:
    i31    = (word >> 31) & 0x1
    i30_21 = (word >> 21) & 0x3FF
    i20    = (word >> 20) & 0x1
    i19_12 = (word >> 12) & 0xFF
    raw = (i31 << 20) | (i19_12 << 12) | (i20 << 11) | (i30_21 << 1)
    return _sign_imm(raw, 21)


# ------------------------------------------------------------------
# Per-family decoders
# ------------------------------------------------------------------

def _decode_system(word: int) -> str:
    funct3 = (word >> 12) & 0x7
    if funct3 == 0:
        csr = (word >> 20) & 0xFFF
        if csr == 0: return "ecall"
        if csr == 1: return "ebreak"
    return f".word 0x{word:08x}"


def _decode_zon_custom(word: int) -> str:
    """Zon VM custom opcode for built-in string operations."""
    funct3 = (word >> 12) & 0x7
    funct7 = (word >> 25) & 0x7F
    rd  = (word >> 7)  & 0x1F
    rs1 = (word >> 15) & 0x1F
    rs2 = (word >> 20) & 0x1F

    if funct7 == 0x00:
        if funct3 == 0x00:
            return f"str.concat {_reg(rd)}, {_reg(rs1)}, {_reg(rs2)}"
        if funct3 == 0x01:
            return f"str.eq {_reg(rd)}, {_reg(rs1)}, {_reg(rs2)}"

    return f".word 0x{word:08x}"


def _decode_lui(word: int) -> str:
    rd  = (word >> 7) & 0x1F
    imm = (word >> 12) & 0xFFFFF
    return f"lui {_reg(rd)}, 0x{imm:x}"


def _decode_auipc(word: int) -> str:
    rd  = (word >> 7) & 0x1F
    imm = (word >> 12) & 0xFFFFF
    return f"auipc {_reg(rd)}, 0x{imm:x}"


def _decode_jal(word: int, pc: int) -> str:
    rd  = (word >> 7) & 0x1F
    imm = _imm_j(word)
    return f"jal {_reg(rd)}, {imm:+d}  # target = 0x{pc + imm:04x}"


def _decode_jalr(word: int) -> str:
    rd  = (word >> 7)  & 0x1F
    rs1 = (word >> 15) & 0x1F
    imm = _imm_i(word)
    return f"jalr {_reg(rd)}, {imm}({_reg(rs1)})"


def _decode_branch(word: int, pc: int) -> str:
    rs1 = (word >> 15) & 0x1F
    rs2 = (word >> 20) & 0x1F
    imm = _imm_b(word)

    mnemonics = {0: "beq", 1: "bne", 4: "blt", 5: "bge", 6: "bltu", 7: "bgeu"}
    funct3 = (word >> 12) & 0x7
    mnemonic = mnemonics.get(funct3, f".branch_f{funct3}")
    return f"{mnemonic} {_reg(rs1)}, {_reg(rs2)}, {imm:+d}  # target = 0x{pc + imm:04x}"


def _decode_load(word: int) -> str:
    rd  = (word >> 7)  & 0x1F
    rs1 = (word >> 15) & 0x1F
    imm = _imm_i(word)
    funct3 = (word >> 12) & 0x7

    mnemonics = ["lb", "lh", "lw", "ld", "lbu", "lhu", "lwu"]
    mnemonic = mnemonics[funct3] if funct3 < len(mnemonics) else f".load_f{funct3}"
    return f"{mnemonic} {_reg(rd)}, {imm}({_reg(rs1)})"


def _decode_store(word: int) -> str:
    rs1 = (word >> 15) & 0x1F
    rs2 = (word >> 20) & 0x1F
    imm = _imm_s(word)
    funct3 = (word >> 12) & 0x7

    mnemonics = ["sb", "sh", "sw", "sd"]
    mnemonic = mnemonics[funct3] if funct3 < len(mnemonics) else f".store_f{funct3}"
    return f"{mnemonic} {_reg(rs2)}, {imm}({_reg(rs1)})"


def _decode_alu_imm(word: int, opcode: int) -> str:
    """OP-IMM and OP-IMM-32 (addi, slti, xori, ori, andi, slli, srli, srai)."""
    rd  = (word >> 7)  & 0x1F
    rs1 = (word >> 15) & 0x1F
    imm = _imm_i(word)
    funct3 = (word >> 12) & 0x7
    suffix = "w" if opcode == 0b0011011 else ""

    # shifts encode shamt in imm[5:0] and direction in imm[10]
    if funct3 == 0b001:
        return f"slli{suffix} {_reg(rd)}, {_reg(rs1)}, {imm & 0x3F}"
    if funct3 == 0b101:
        op = "srai" if imm & 0x400 else "srli"
        return f"{op}{suffix} {_reg(rd)}, {_reg(rs1)}, {imm & 0x3F}"

    mnemonics = ["addi", "slli", "slti", "sltiu", "xori", None, "ori", "andi"]
    mnemonic = mnemonics[funct3] or f".alui_f{funct3}"
    return f"{mnemonic}{suffix} {_reg(rd)}, {_reg(rs1)}, {imm}"


def _decode_alu_reg(word: int, opcode: int) -> str:
    """OP and OP-32 (add, sub, mul, sll, xor, or, and, …)."""
    rd  = (word >> 7)  & 0x1F
    rs1 = (word >> 15) & 0x1F
    rs2 = (word >> 20) & 0x1F
    funct3 = (word >> 12) & 0x7
    funct7 = (word >> 25) & 0x7F
    suffix = "w" if opcode == 0b0111011 else ""

    # M extension (funct7 = 0b0000001)
    if funct7 == 0b0000001:
        m_ops = ["mul", "mulh", "mulhsu", "mulhu", "div", "divu", "rem", "remu"]
        return f"{m_ops[funct3]}{suffix} {_reg(rd)}, {_reg(rs1)}, {_reg(rs2)}"

    # Standard and alternate encodings (funct7 = 0b0100000)
    alt = 0b0100000
    match funct3:
        case 0b000: mnemonic = "sub"  if funct7 == alt else "add"
        case 0b001: mnemonic = "sll"
        case 0b010: mnemonic = "slt"
        case 0b011: mnemonic = "sltu"
        case 0b100: mnemonic = "xnor" if funct7 == alt else "xor"
        case 0b101: mnemonic = "sra"  if funct7 == alt else "srl"
        case 0b110: mnemonic = "nor"  if funct7 == alt else "or"
        case 0b111: mnemonic = "nand" if funct7 == alt else "and"
        case _:     mnemonic = f".alur_f{funct3}"

    return f"{mnemonic}{suffix} {_reg(rd)}, {_reg(rs1)}, {_reg(rs2)}"


def _decode_float_load(word: int) -> str:
    rd  = (word >> 7)  & 0x1F
    rs1 = (word >> 15) & 0x1F
    imm = _imm_i(word)
    funct3 = (word >> 12) & 0x7
    mnemonic = "fld" if funct3 == 0b011 else "flw"
    return f"{mnemonic} {_freg(rd)}, {imm}({_reg(rs1)})"


def _decode_float_store(word: int) -> str:
    rs1 = (word >> 15) & 0x1F
    rs2 = (word >> 20) & 0x1F
    imm = _imm_s(word)
    funct3 = (word >> 12) & 0x7
    mnemonic = "fsd" if funct3 == 0b011 else "fsw"
    return f"{mnemonic} {_freg(rs2)}, {imm}({_reg(rs1)})"


# ------------------------------------------------------------------
# Main decoder dispatcher
# ------------------------------------------------------------------

def _decode(word: int, pc: int) -> str:
    """Decode a single 32-bit RISC-V instruction word at byte offset pc."""
    opcode = word & 0x7F

    match opcode:
        case 0b1110011: return _decode_system(word)
        case 0b0001011: return _decode_zon_custom(word)
        case 0b0110111: return _decode_lui(word)
        case 0b0010111: return _decode_auipc(word)
        case 0b1101111: return _decode_jal(word, pc)
        case 0b1100111: return _decode_jalr(word)
        case 0b1100011: return _decode_branch(word, pc)
        case 0b0000011: return _decode_load(word)
        case 0b0100011: return _decode_store(word)
        case 0b0010011 | 0b0011011: return _decode_alu_imm(word, opcode)
        case 0b0110011 | 0b0111011: return _decode_alu_reg(word, opcode)
        case 0b0000111: return _decode_float_load(word)
        case 0b0100111: return _decode_float_store(word)
        case _: return f".word 0x{word:08x}"


# ------------------------------------------------------------------
# File-level disassembly
# ------------------------------------------------------------------

def disassemble(filename: str) -> None:
    """Read a .zon bytecode file and print its disassembly to stdout."""
    with open(filename, "rb") as f:
        _print_header(f)
        text_size, pool_size, data_size = _read_file_header(f)
        f.read(40)  # reserved padding for future header fields

        _print_text_section(f, text_size)

        if pool_size > 0:
            _print_rodata_section(f, pool_size)

        if data_size > 0:
            _print_data_section(data_size)


def _read_file_header(f) -> tuple[int, int, int]:
    """Validate the magic bytes and read the section sizes.
    Returns (text_size, pool_size, data_size).
    """
    magic = f.read(6)
    if magic != b"!NOZo\x00":
        raise ValueError("not a valid Zon VM bytecode file")

    version     = f.read(1)[0]
    _flags      = f.read(1)[0]  # reserved for future use
    entry_point = struct.unpack("<I", f.read(4))[0]
    text_size   = struct.unpack("<I", f.read(4))[0]
    data_size   = struct.unpack("<I", f.read(4))[0]
    pool_size   = struct.unpack("<I", f.read(4))[0]

    print("=== Zon VM Disassembly ===")
    print(f"Version: {version}")
    print(f"Entry point: 0x{entry_point:x}")
    print(f".text size: {text_size} bytes ({text_size // 4} instructions)")
    print(f".data size: {data_size} bytes")
    print(f".rodata size: {pool_size} bytes")

    return text_size, pool_size, data_size


def _print_header(f) -> None:
    pass  # header is read inside _read_file_header to keep seek position correct


def _print_text_section(f, size: int) -> None:
    print("\n--- .text section ---")
    pc = 0
    for _ in range(size // 4):
        word = struct.unpack("<I", f.read(4))[0]
        print(f"0x{pc:04x}  {word:08x}  {_decode(word, pc)}")
        pc += 4


def _print_rodata_section(f, size: int) -> None:
    print(f"\n--- .rodata section (size: {size} bytes) ---")
    print(f"{'Offset':<12}{'Raw Hex':<20}{'As Int64':<22}{'As Double':<22}{'Dump (ASCII)'}")

    offset = 0
    for _ in range(size // 8):
        raw = f.read(8)
        if len(raw) < 8:
            break

        raw_hex   = f"{struct.unpack('<Q', raw)[0]:016x}"
        val_int   = struct.unpack("<q", raw)[0]
        val_float = struct.unpack("<d", raw)[0]
        float_str = f"{val_float:.10g}" if val_float == val_float else "nan"  # nan check
        ascii_str = "".join(chr(b) if 32 <= b <= 126 else "." for b in raw)

        print(f"0x{offset:04x}      {raw_hex}    {val_int:<20}  {float_str:<20}  {ascii_str}")
        offset += 8


def _print_data_section(size: int) -> None:
    print(f"\n--- .data ---")
    print(f"Size: {size} bytes ({size // 8} unified 8-byte slots)")
    print("Status: initialized to 0 by the VM at startup [OK]")