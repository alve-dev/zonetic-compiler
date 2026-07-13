"""Emitter — the central state object for RISC-V bytecode generation.

Every code-generation function receives the emitter and mutates it.
Once all statements are processed, `save()` runs the linker pass that
resolves labels and branch offsets, then writes the final .zbc binary.

.zbc binary layout
-------------------
Offset  Size  Field
0       6     magic  b"!NOZo\x00"
6       1     version  (currently 1)
7       1     flags    (reserved, 0)
8       4     entry_point  byte offset into .text
12      4     text_size    bytes
16      4     data_size    bytes
20      4     pool_size    bytes
24      40    padding      (reserved for future header fields)
64+     N     .text section  (RISC-V instructions)
64+N    M     .rodata section  (constant pool: floats, strings)
64+N+M  K     .data section  (global variables, zero-initialised by VM)
"""
from zonc.zonast import *
from .opcode import *
from .register_manager import RegisterManager
from .bytecodescope import SymbolTable, RegT, ZonVar
from .instruction import (
    IntsB, IntsJ, InstJR, ConstantLoad, AddressLoad,
    generate_b_type, generate_j_type, generate_i_type_jalr,
    emit_i_type, emit_s,
)
from .func_gen import generate_program_entry


# ------------------------------------------------------------------
# Label manager
# ------------------------------------------------------------------

class LabelManager:
    """Assigns numeric IDs to labels and resolves them to byte offsets.

    Labels are created before the instructions that reference them,
    then placed once the target instruction is emitted.
    """

    def __init__(self) -> None:
        self.labels: dict[int, int] = {}
        self._counter = 0

    def create(self) -> int:
        """Reserve a new label ID (unplaced). Returns the ID."""
        label_id = self._counter
        self.labels[label_id] = 0
        self._counter += 1
        return label_id

    def place_label(self, label_id: int, pc: int) -> None:
        """Bind label_id to pc (instruction index, not byte offset)."""
        self.labels[label_id] = pc * 4


# ------------------------------------------------------------------
# Emitter
# ------------------------------------------------------------------

class Emitter:
    """Holds all mutable state produced during code generation.

    Scratch registers (31) are reserved for temporary loads/stores
    and are never allocated to user variables.
    """

    REG_SCRATCH_X = 31  # x31 / t6 — integer scratch
    REG_SCRATCH_F = 31  # f31 / ft11 — float scratch

    def __init__(self) -> None:
        self.code: list              = []
        self.offset_stack: list      = []
        self.reg_manager             = RegisterManager(self.offset_stack)
        self.symbol_table            = SymbolTable()
        self.label_manager           = LabelManager()
        self.loop_stack: list        = []
        self.pool_data: bytearray    = bytearray()
        self.functions: dict         = {}
        self.current_func: str       = ""
        self.block_exits: list       = []
        self.value_block_exits: list = []
        self.data_section_size: int  = 0
        self.entry_point: int        = 0
        self.string_pool: dict       = {}
        self.constant_pool           = {}

    # ------------------------------------------------------------------
    # Code position
    # ------------------------------------------------------------------

    def get_pc(self) -> int:
        """Current instruction index (not byte offset)."""
        return len(self.code)

    # ------------------------------------------------------------------
    # Register helpers
    # ------------------------------------------------------------------

    def _unwrap(self, reg) -> int:
        """Return the physical register number from a ZonVar or bare int."""
        return reg if isinstance(reg, int) else reg.reg

    def _resolve_dest(self, reg: ZonVar, scratch: int) -> int:
        """Return the physical register for a destination ZonVar.
        Falls back to scratch if the var has been spilled to the stack.
        """
        if isinstance(reg, int):
            return reg
        return reg.reg if reg.reg is not None else scratch

    def _read_operand(self, var: ZonVar, scratch: int) -> int:
        """Emit a load if var is spilled, then return the physical register.
        If var already lives in a register, returns it directly.
        """
        if var.reg is not None:
            return var.reg

        offset = var.offset_stack[0] if isinstance(var.offset_stack, list) else var.offset_stack

        if var.regt == RegT.X:
            emit_i_type(self, OpCode.L, F3_L.LD, scratch, 8, offset)
        elif var.regt == RegT.F:
            emit_i_type(self, OpCode.FL, F3_FL.FLD, scratch, 8, offset)

        return scratch

    def _write_result(self, dest: ZonVar, source_reg: int) -> None:
        """Emit a store if dest is spilled. No-op if dest lives in a register."""
        if dest.reg is not None:
            return

        offset = dest.offset_stack[0] if isinstance(dest.offset_stack, list) else dest.offset_stack

        if dest.regt == RegT.X:
            emit_s(self, OpCode.OP_S, F3_S.SD, 8, source_reg, offset)
        elif dest.regt == RegT.F:
            emit_s(self, OpCode.OP_FS, F3_FS.FSD, 8, source_reg, offset)

    # ------------------------------------------------------------------
    # Save — linker pass + binary output
    # ------------------------------------------------------------------

    def save(self, ast, filename: str) -> None:
        """Generate code from ast, resolve all labels, and write filename."""
        generate_program_entry(self, ast)

        text_size = len(self.code) * 4
        pool_size = len(self.pool_data)

        with open(filename, "wb") as f:
            self._write_header(f, text_size, pool_size)
            self._write_text(f, text_size)
            f.write(self.pool_data)
            self._write_data(f)

    def _write_header(self, f, text_size: int, pool_size: int) -> None:
        f.write(b"!NOZo\x00")                                              # magic  (6 bytes)
        f.write((1).to_bytes(1, "little"))                                  # version
        f.write((0).to_bytes(1, "little"))                                  # flags
        f.write(self.label_manager.labels[self.entry_point].to_bytes(4, "little"))  # entry point
        f.write(text_size.to_bytes(4, "little"))                            # .text size
        f.write(self.data_section_size.to_bytes(4, "little"))              # .data size
        f.write(pool_size.to_bytes(4, "little"))                            # .rodata size
        f.write(b"\x00" * 40)                                              # reserved padding

    def _write_text(self, f, text_size: int) -> None:
        """Resolve and write every instruction in the .text section."""
        for i, inst in enumerate(self.code):
            if inst == "DUMMY":
                continue

            pc = i * 4

            if isinstance(inst, bytes):
                f.write(inst)

            elif isinstance(inst, IntsB):
                offset = self.label_manager.labels[inst.label] - pc
                f.write(generate_b_type(inst, offset))

            elif isinstance(inst, IntsJ):
                offset = self.label_manager.labels[inst.label] - pc
                f.write(generate_j_type(inst, offset))

            elif isinstance(inst, ConstantLoad):
                f.write(self._encode_constant_load(inst, pc, text_size))

            elif isinstance(inst, InstJR):
                f.write(generate_i_type_jalr(inst))

            elif isinstance(inst, AddressLoad):
                f.write(self._encode_address_load(inst, pc, text_size))

    def _encode_constant_load(self, inst: ConstantLoad, pc: int, text_size: int) -> bytes:
        """Encode an AUIPC + FLD/LD pair for loading a constant from .rodata."""
        dist  = (text_size - pc) + inst.pool_offset
        low   = dist & 0xFFF
        high  = dist >> 12
        if low & 0x800:
            high += 1
        high &= 0xFFFFF

        rd_int = inst.rd_int & 0x1F
        auipc  = (high << 12) | (rd_int << 7) | (OpCode.AUIPC & 0x7F)

        rd      = inst.rd & 0x1F
        funct3  = 0x3
        opcode  = OpCode.FL if inst.is_float else OpCode.L
        load    = (low << 20) | (rd_int << 15) | (funct3 << 12) | (rd << 7) | opcode

        return auipc.to_bytes(4, "little") + load.to_bytes(4, "little")

    def _encode_address_load(self, inst: AddressLoad, pc: int, text_size: int) -> bytes:
        """Encode an AUIPC + ADDI pair for loading a .rodata address."""
        dist  = (text_size - pc) + inst.pool_offset
        low   = dist & 0xFFF
        high  = dist >> 12
        if low & 0x800:
            high += 1
        high &= 0xFFFFF

        rd     = inst.rd & 0x1F
        auipc  = (high << 12) | (rd << 7) | OpCode.AUIPC
        addi   = (low << 20) | (rd << 15) | (F3_ALU.ADD_SUB << 12) | (rd << 7) | OpCode.OP_IMM

        return auipc.to_bytes(4, "little") + addi.to_bytes(4, "little")

    def _write_data(self, f) -> None:
        """Write the .data section as zero bytes (VM initialises it at load time)."""
        f.write(b"\x00" * self.data_section_size)