"""Function and program entry-point code generation.

Exports:
    prologue(emitter, stmts, params) — emit function prologue
    epilogue(emitter)                — emit function epilogue
    generate_program_entry(emitter, stmts) — top-level dispatcher

Two program modes
-----------------
  Structured (has `main`):
      global-var init → jal to _start → emit each FuncForm → _start: call main → exit

  Script (no `main`):
      _start: prologue → emit body stmts → epilogue → exit → emit each FuncForm

Frame layout (offset_stack entry)
----------------------------------
  [0] spill_ptr    — next available spill slot (sp-relative, moves down)
  [1] bytes_needed — total frame size in bytes
  [2] has_call     — True if the function calls other functions
  [3] used_s       — (saved_x_regs, saved_f_regs) lists
  [4] used_heap    — True if alloc/store/load are used
  [5] bool_slot    — reserved for packed bool spill slots
  [6] array_ptr    — base of stack-array area (sp-relative, moves up per array)
"""

from .instruction import (
    emit_i_type, emit_s, emit_f_type, emit_jalr, emit_ecall,
    emit_jump,
)
from .expr_gen import generate_expr
from .stmt_gen import generate_stmt
from .rodata import generate_literal_num, generate_literal_f
from .linear_scan_register_allocation import LinearScanRegisterAllocation
from .opcode import *
from .bytecodescope import RegT
from zonc.zonast import (
    FuncForm, InitializationStmt,
    IntLiteral, BoolLiteral, FloatLiteral, StringLiteral,
)
from dataclasses import dataclass

# ------------------------------------------------------------------
# Frame Info
# ------------------------------------------------------------------

@dataclass
class FrameInfo(list):
    bytes_needed: int
    has_call: bool
    saved_regs: tuple
    used_heap: bool
    bool_slot: object = None
    array_ptr: int = 0
    array_top: int = 0
    spill_ptr: int = 0

    def __post_init__(self):
        super().__init__([
            self.spill_ptr, self.bytes_needed, self.has_call, 
            self.saved_regs, self.used_heap, self.bool_slot, self.array_ptr
        ])


# ------------------------------------------------------------------
# Prologue and epilogue
# ------------------------------------------------------------------

def prologue(emitter, stmts: list, params: list = None) -> None:
    """Emit the function prologue: allocate frame, save callee-saved registers."""
    allocator   = LinearScanRegisterAllocation(num_available_regs=7, num_available_fregs=12)
    bytes_needed, has_call, used_s, used_heap = allocator.analyze_function(stmts, params)
    array_bytes = allocator.array_bytes

    # allocate frame and save s0 (frame pointer) at the top
    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 2, 2, -bytes_needed)
    emit_s(emitter, OpCode.OP_S, F3_S.SD, 2, 8, bytes_needed - 8)

    offset = bytes_needed - 16

    if has_call:
        emit_s(emitter, OpCode.OP_S, F3_S.SD, 2, 1, offset)
        offset -= 8

    for reg in used_s[0]:
        emit_s(emitter, OpCode.OP_S, F3_S.SD, 2, reg, offset)
        offset -= 8

    for reg in used_s[1]:
        emit_s(emitter, OpCode.OP_FS, F3_FS.FSD, 2, reg, offset)
        offset -= 8

    # reserve space for stack arrays — spill slots go below this area
    array_top = offset
    offset -= array_bytes
    array_ptr = offset
    spill_ptr = offset 

    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 8, 2, bytes_needed)
    frame = FrameInfo(
        bytes_needed=bytes_needed,
        has_call=has_call,
        saved_regs=used_s,
        used_heap=used_heap,
        bool_slot=None,
        array_ptr=array_ptr,
        array_top=array_top,
        spill_ptr=spill_ptr
    )
    emitter.offset_stack.append(frame)

    if used_heap:
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -100)
        emit_ecall(emitter)


def epilogue(emitter) -> None:
    """Emit the function epilogue: restore callee-saved registers, deallocate frame."""
    frame = emitter.offset_stack[-1]
    bytes_reserved = frame.bytes_needed
    has_call = frame.has_call
    used_s = frame.saved_regs
    used_heap = frame.used_heap

    offset = bytes_reserved - 16

    if has_call:
        emit_i_type(emitter, OpCode.L, F3_L.LD, 1, 2, offset)
        offset -= 8

    for reg in used_s[0]:
        emit_i_type(emitter, OpCode.L, F3_L.LD, reg, 2, offset)
        offset -= 8

    for reg in used_s[1]:
        emit_i_type(emitter, OpCode.FL, F3_FL.FLD, reg, 2, offset)
        offset -= 8

    emit_i_type(emitter, OpCode.L,      F3_L.LD,       8, 2, bytes_reserved - 8)
    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 2, 2, bytes_reserved)
    emitter.offset_stack.pop()

    if used_heap:
        emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, -101)
        emit_ecall(emitter)


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _emit_global_var(emitter, node: InitializationStmt) -> None:
    """Register and emit code to initialise one global variable."""
    var_name = node.decl_stmt.name
    var_type = node.decl_stmt.type

    if not emitter.symbol_table.exists_here(var_name):
        emitter.symbol_table.define_global(var_name, emitter.data_section_size, var_type)
        emitter.data_section_size += 8

    slot     = emitter.symbol_table.resolve(var_name)
    val_node = node.assign_stmt.value

    if isinstance(val_node, (IntLiteral, BoolLiteral)):
        tmp = emitter.reg_manager.alloc_temp()
        src = emitter._read_operand(tmp, emitter.REG_SCRATCH_X)
        generate_literal_num(emitter, val_node.value, tmp)
        is_expr = False

    elif isinstance(val_node, FloatLiteral):
        tmp = emitter.reg_manager.alloc_temp()
        src = emitter._read_operand(tmp, emitter.REG_SCRATCH_F)
        generate_literal_f(emitter, val_node.value, tmp)
        is_expr = False

    elif isinstance(val_node, StringLiteral):
        tmp = generate_expr(emitter, val_node)
        src = emitter._read_operand(tmp, emitter.REG_SCRATCH_X)
        emitter.reg_manager.free_temp(tmp)
        is_expr = False

    else:
        tmp = generate_expr(emitter, val_node, var_type.num)
        src = emitter._read_operand(
            tmp, emitter.REG_SCRATCH_X if tmp.regt == RegT.X else emitter.REG_SCRATCH_F
        )
        is_expr = True

    if var_type.num in (1, 3, 4, 6):
        emit_s(emitter, OpCode.OP_S,  F3_S.SD,  3, src, slot.offset_global)
    elif var_type.num in (2, 7):
        emit_s(emitter, OpCode.OP_FS, F3_FS.FSD, 3, src, slot.offset_global)

    if is_expr:
        emitter.reg_manager.free_temp(tmp)


def _emit_func(emitter, func: FuncForm) -> None:
    """Emit prologue, body, and epilogue for a single FuncForm."""
    emitter.symbol_table.enter_scope()
    emitter.current_func = func.name

    func_label, return_type = emitter.functions[func.name][:2]
    emitter.label_manager.place_label(func_label, emitter.get_pc())

    epilogue_label = emitter.label_manager.create()
    body_label     = emitter.label_manager.create()
    emitter.functions[func.name] = (func_label, return_type, epilogue_label, body_label)

    prologue(emitter, func.block_expr.stmts, func.params)
    emitter.label_manager.place_label(body_label, emitter.get_pc())

    # move incoming arguments from a-registers into s-registers
    int_arg   = 10
    float_arg = 10
    if func.params is not None:
        for param in func.params:
            if param.zontype.num in (1, 3, 6):
                reg = emitter.symbol_table.define(param.name, param.zontype)
                if reg is not None:
                    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, reg, int_arg, 0)
                    int_arg += 1
            else:
                reg = emitter.symbol_table.define_f(param.name, param.zontype)
                if reg is not None:
                    emit_f_type(emitter, OpCode.OP_F, reg, float_arg, float_arg, 0x00, F7.FSGNJ_D)
                    float_arg += 1

    for stmt in func.block_expr.stmts:
        generate_stmt(emitter, stmt)

    emitter.label_manager.place_label(epilogue_label, emitter.get_pc())
    epilogue(emitter)
    emit_jalr(emitter, 0, 1)
    emitter.symbol_table.exit_scope()


def _register_funcs(emitter, funcs: list[FuncForm]) -> None:
    """Pre-register all functions so they can be called before their definition."""
    for func in funcs:
        label = emitter.label_manager.create()
        emitter.functions[func.name] = (label, func.return_type)


# ------------------------------------------------------------------
# Top-level entry point
# ------------------------------------------------------------------

def generate_program_entry(emitter, program_stmts: list) -> None:
    """Generate code for the entire program.

    Dispatches to structured mode (has main) or script mode (no main).
    """
    funcs      = [s for s in program_stmts if isinstance(s, FuncForm)]
    has_main   = any(f.name == "main" for f in funcs)
    start_label = emitter.label_manager.create()

    if has_main:
        _emit_structured(emitter, program_stmts, funcs, start_label)
    else:
        _emit_script(emitter, program_stmts, funcs, start_label)


def _emit_structured(emitter, stmts: list, funcs: list, start_label: int) -> None:
    """Structured mode: init globals → jump to main → exit."""
    global_vars = [s for s in stmts if isinstance(s, InitializationStmt)]

    # entry point: initialise globals then jump to the function body area
    init_label = emitter.label_manager.create()
    emitter.label_manager.place_label(init_label, emitter.get_pc())
    emitter.entry_point = init_label

    for node in global_vars:
        _emit_global_var(emitter, node)

    emit_jump(emitter, start_label)

    _register_funcs(emitter, funcs)
    for func in funcs:
        _emit_func(emitter, func)

    # _start: call main, then exit via ecall 93
    emitter.label_manager.place_label(start_label, emitter.get_pc())
    emit_jump(emitter, emitter.functions["main"][0], rd=1)
    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, 93)
    emit_ecall(emitter)


def _emit_script(emitter, stmts: list, funcs: list, start_label: int) -> None:
    """Script mode: execute top-level statements directly, then exit."""
    script_body = [s for s in stmts if not isinstance(s, FuncForm)]

    emitter.entry_point = start_label
    emitter.label_manager.place_label(start_label, emitter.get_pc())

    _register_funcs(emitter, funcs)

    prologue(emitter, script_body)
    for stmt in script_body:
        generate_stmt(emitter, stmt)
    epilogue(emitter)

    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 10, 0, 0)
    emit_i_type(emitter, OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0, 93)
    emit_ecall(emitter)

    for func in funcs:
        _emit_func(emitter, func)