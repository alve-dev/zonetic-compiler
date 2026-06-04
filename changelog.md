# Changelog

All notable changes to Zonetic are documented here.
Versions are listed from newest to oldest.

## v2.6.0 — *The ByteCode Refactor Update*

> This version introduces a major architectural overhaul of the compiler's backend bytecode generation subsystem, transitioning from a monolithic emitter into a highly modular, scalable file-based infrastructure. Additionally, memory management undergoes high-performance optimizations by transitioning the Scope-Based Arena Heap into a Function-Based lifecycle with lazy initialization. Finally, the custom ISA has been expanded with three non-standard, single-cycle R-Type hardware instructions (`nand`, `nor`, `xnor`) to achieve maximum execution density in bitwise operations.

**Backend Architecture & Emitter Modularization**

* **De-monolithization of `TheEmitter`** — Refactored the core bytecode generation system, expanding the emitter codebase to nearly 2,000 lines of highly optimized C++. The monolithic structure was entirely dismantled and distributed across dedicated, domain-specific translation files, ensuring clean separation of concerns and enabling trivial expansion for future hardware extensions.
* **Streamlined Pipeline Scalability** — The structural splitting of the backend isolates expression parsing, statement emission, and register mapping, reducing compiler technical debt and improving compilation throughput in the pre-linking phases.

**Optimized Function-Based Arena Heap**

* **Lazy Allocation Subsystem** — Upgraded the dynamic memory boundary triggers within the Virtual Machine. The compiler now statically analyzes scope blocks and emits `heap_push` and `heap_pop` environment calls **only** if dynamic memory allocation (such as dynamic strings) is actively requested, eliminating structural overhead in pure compute blocks.
* **Function-Based Arena Lifecycles** — Re-engineered the topology of the Arena Heap. The architecture departs from the extreme block-scope model (where every localized `if` or `while` block spawned an isolated arena) and unifies the allocation boundary at the function level. Each execution frame now controls its own persistent Arena Heap, drastically lowering the frequency of runtime context switching and memory re-mapping.

**Custom ISA Bitwise R-Type Extensions**

* **Single-Cycle Native Universal Gates** — Expanded the custom non-standard RISC-V ISA with three native hardware-level primitives to offload universal gate logic from double-instruction software emulation patterns. The universal logic operations `bnand` (`~&`), `bnor` (`~|`), and `bxnor` (`~^`) now execute in **exactly 1 hardware instruction cycle**:
  * `nand` (*R-Type, Opcode: 0x33, F3: 0x07, F7: 0x20*) — Native bitwise AND inversion.
  * `nor` (*R-Type, Opcode: 0x33, F3: 0x06, F7: 0x20*) — Native bitwise OR inversion.
  * `xnor` (*R-Type, Opcode: 0x33, F3: 0x04, F7: 0x20*) — Native bitwise XOR inversion.
* **Hardware-Level Bit Recycling (`f7` Alt-Masking)** — Implemented the new gates by mirroring the exact base Opcode and Function-3 (`f3`) configurations of standard RISC-V `and`, `or`, and `xor` primitives. To differentiate the inversion layer directly in hardware decoding, the compiler flags the alternate-operation mask inside the Function-7 (`f7`) field, shifting it from `0x00` to `0x20` (`alt` bit active), allowing the VM decoder to execute them via instant computed branch paths.

---

## v2.5.0 — *The Heap Update*

> This version introduces the initial dynamic memory management subsystem through a deterministic Scope-Based Arena Heap, full support for extended ASCII immutable and dynamic strings, and advanced expression parsing. Zonetic now features native expression-level `if` evaluations, strict hardware-level explicit casting, unique bitwise-logical naming semantics, a unified 16MB monolithic runtime memory map, and high-performance custom ISA string extensions.

**Dynamic Memory & The Scope-Based Arena Heap**

* **Deterministic Arena Architecture** — Implemented a streamlined, high-performance Heap based on stacked Arenas mapped directly to local block scopes. Allocation occurs linearly via instantaneous pointer bumps, using scoped `push` and `pop` lifecycles to completely eliminate fragmentation and the necessity of slow, manual `free()` subroutines.
* **Unified 16MB Runtime RAM** — Refactored the entire C++ Virtual Machine memory topology, consolidating instructions, global data, stack, and the new heap segments into a single, cohesive 16MB monolithic RAM array to maximize cache locality and simplify hardware emulated addressing.
* **Optimized Dynamic Memory ECALLs** — Integrated dedicated low-level runtime environment calls to handle high-frequency `heap_push` and `heap_pop` boundary updates directly via the VM execution core.

**Native Extended ASCII String Subsystem**

* **Immutable String Deduplication (`.rodata`)** — Literal and immutable strings are formally allocated within the newly formalized `.rodata` segment. The compiler emitter utilizes an internal string-pooling dictionary to cross-reference identical literals, reusing memory addresses to prevent static binary bloat.
* **Extended ASCII Standard & C-Compatibility** — Established Extended ASCII as the immutable, high-efficiency encoding standard for Zonetic text processing. Strings are strictly null-terminated (`\0`) for seamless C-interoperability, while the Lexer actively bans raw `\0` literal injections to guarantee memory safety.
* **Dynamic Heap Strings & Constraints** — Dynamic string manipulations are routed directly onto the Arena Heap. In this baseline phase, strict safety invariants are maintained: heap-allocated strings cannot be returned out of scope, length attributes (`len`) remain encapsulated, and dynamic reallocation is strictly controlled.
* **Custom ISA String Extensions** — Extended the base instruction set with non-standard RISC-V hardware instructions to offload text operations from heavy software loops:
  * `str.concat` (*R-Type, Opcode: 0x0B, F3: 0x00, F7: 0x00*) — Hardware-level reference combining.
  * `str.eq` (*R-Type, Opcode: 0x0B, F3: 0x01, F7: 0x00*) — Hardware-accelerated string byte comparison.

**Bitwise & Logical Hardware Primitives**

* **Strict Bitwise-Logical Semantic Separation** — Introduced an explicit naming convention to separate control-flow logic from raw bit manipulation, preventing silent structural bugs. Boolean operations use `and`, `or`, and `not`, while bitwise operations are explicitly bound to keyword-token twins: `band` (`&`), `bor` (`|`), `bxor` (`^`), and `bnot` (`~`).
* **Bitwise Shift Primitives** — Full native emitter integration for logical left shift (`<<`) and right shift (`>>`) operators.
* **Universal Gate Syntactic Sugar** — Integrated native bitwise shorthand representation for universal logic gates. The compiler transparently maps `bnand` (`~&`), `bnor` (`~|`), and `bxnor` (`~^`) into inverted bitwise operations (e.g., `~(a & b)`) without adding AST complexity.
* **Compound Assignment Operators** — Added syntactic shorthand for register-modifying expressions. Supports bitwise compound assignments (`&=`, `|=`, `^=`) and boolean control-flow short-circuit compounds (`&&=`, `||=`).

**Conditional Expressions & Explicit Type Casting**

* **Conditional Block Expressions (`if expr`)** — Upgraded `if-else` blocks into evaluation-level expressions capable of returning values. Leverages the `give` keyword to yield data out of a localized block directly into a destination register.
* **Zero Implicit Coercion & Explicit Casting** — Enforced rigid type isolation to prevent silent truncation. All cross-type operations must be explicitly cast by the programmer:
  * `int64()` — Sign-extended 64-bit integer conversion. Booleans evaluate to `1` or `0` via an optimized `ADDI` (Move) pass.
  * `bool()` — Boolean evaluation mapping. Implemented a zero-overhead runtime pass via `SLTU` against `x0`, correctly converting signed negative numbers (e.g., `bool(-5)`) to `true` in exactly 1 hardware instruction cycle.

**Compiler Diagnostics & CLI Architecture**

* **Post-Optimization AST Inspection (`--ast-o`)** — Expanded the Command Line Interface with the `--ast-o` flag. While `--ast` dumps the raw post-parser tree, `--ast-o` outputs the highly optimized AST after undergoing Semantic Analysis, Constant Folding, and Dead Code Elimination (DCE).
* **Multi-Argument System Printing** — Upgraded `print` and the newly introduced `println` into variadic multi-argument operations. The compiler breaks down multi-argument sequences into a continuous chain of individual, high-performance print evaluations.
* **High-Range ECALL Vectoring** — Redesigned the virtual machine's ECALL mapping layout. To prevent overlapping with standard RISC-V environment vectors, custom runtime calls are directed to negative registers and ranges above `1900`, preserving the 12-bit `ADDI` immediate boundary. Includes `SPRINT` for string structures and `EPRINT` for executing standard newline insertions (`\n`).

**Refinements & Infrastructure Fixes**

* **Windows Provisioning Script (`zon.ps1`)** — Fixed an infrastructure bug inside the PowerShell update automation utility. Replaced an incompatible networking cmdlet with a robust alternative, stabilizing the `zon update` workflow on Windows host environments.

---

## v2.4.0 — *The Function Update 2.0*

> This version introduces formal procedural execution, stack frame isolation, cross-platform hardware-level memory protection, and binary format formalization. Zonetic now officially supports robust recursion, structured data segments, and optimized runtime printing.

**Procedural Execution & Stack Management**

* **Structured Control Flow (`JALR`)** — Integration of the `JALR` instruction to handle indirect jumps, enabling dynamic function routing and proper return paths.
* **Function Life Cycle Archetype** — Implementation of complete function prologues and epilogues to automatically manage context execution.
* **Dedicated Frame Pointer (`x8 / fp`)** — Redefined the `x8` register exclusively as a Frame Pointer (`fp`) to track local stack boundaries, while `x1` (`ra`) manages the return address.
* **Stack Memory Opcodes** — Added native support for doubleword memory storage and retrieval via `SD` (Store Doubleword) and `LD` (Load Doubleword).
* **Floating-Point Memory Opcodes** — Added native support for `FSD` (Float Store Double) and `FLD` (Float Load Double) to manage floating-point variables within stack frames.

**Register Spilling Optimization**

* **Context Spilling Architecture** — The compiler now spills temporary and saved registers (both integer and floating-point) directly into the stack when register pressure is high.
* **Dedicated Auxiliary Registers** — Registers `x31` and `f31` have been decoupled from standard temporary allocation and are now reserved as dedicated hardware helpers for stack loading operations.
* **Reusable Stack Slots** — Implemented an optimization pass for stack offset reusability. Spilled temporaries share memory slots based on their lifetime, preventing linear stack bloat and maximizing allocation efficiency.

**The Extended `.zbc` Binary Format & Headers**

* **Fixed 64-Byte Header** — Replaced the primitive magic number check with a formal 64-byte binary header to support structural validation.
* **Header Architecture Map**:
  * **Bytes 0–5**: Magic Number (`ZON!o\0` / `\0o!NOZ` in Little Endian).
  * **Byte 6**: Execution flags.
  * **Byte 7**: Version identifier (initialized at `0`).
  * **Bytes 8–11**: `.text` section size (4 bytes).
  * **Bytes 12–15**: `.data` section size (4 bytes).
  * **Bytes 16–19**: Constant pool size (4 bytes).
  * **Bytes 20–63**: 40-byte zero-filled padding reserved for future backward-compatible expansions.
* **Binary Segmentation** — The runtime now splits and maps the executable into clear, back-to-back sections: `.text` (code), followed by `.data` (global memory), and ending with the Constant Pool.

**Global Data Segment & Execution Modes**

* **Global Pointer Integration (`x3 / gp`)** — Fully activated the `x3` (`gp`) register to manage absolute addressing for the newly added `.data` segment.
* **Execution Mode Bifurcation**:
  * **Main Function Mode** — Triggered when a formal `main` function is defined. Global variables are strictly initialized via explicit statement constraints, mapped to `.data`, and modifiable by internal scopes if marked as `mut`.
  * **Top-to-Bottom Scripting Mode** — Retained for flexible, lightweight procedural execution paths without a structural `main` anchor.

**Hardware-Level Stack Protection & Runtimes**

* **Hardware-Enforced Stack Limits** — Configured a rigid 128KB stack limit mapped directly against physical CPU pages via low-level OS allocation, replacing slow software boundaries.
* **Asynchronous Signal Guard** — Integrated native platform hooks (`mprotect` and `sigaction` via POSIX on UNIX; `VirtualProtect` and Vectored Exception Handling on Windows) to trap memory access violations on a zero-overhead guard page, isolating infinite recursion.
* **Tail Call Optimization (TCO)** — Maintained recursive loop compression for tail calls, drastically lowering stack allocation requirements for continuous execution loops.

**Compiler Diagnostics & Refinements**

* **Levenshtein Distance Fix** — Patched a semantic analysis subroutine within the spelling suggestion algorithm to properly display compiler diagnostic hints.
* **Optimized Input/Output ECALLs** — Streamlined `IPRINT`, `FPRINT`, and `BPRINT` services inside the VM by bypassing dynamic formatting allocation in favor of raw buffer insertion and fixed precision layout.

---

## v2.3.0 — *The 64-bit Precision Update*

> This version marks the architectural shift to full 64-bit dominance. By expanding the word size, implementing a unified Constant Pool, and integrating the RISC-V "D" extension, Zonetic now handles massive integers and high-precision physics data with "industrial-grade" stability.

**The 64-bit Foundation (The Wide Path)**

* **Native 64-bit Integers (`int64`)** — Support for the full range of signed 64-bit integers, allowing literals up to $9,223,372,036,854,775,807$ via Constant Pool loading.
* **Double Precision Floating-Point (`double`)** — Implementation of 64-bit floats as the standard for scientific computation, ensuring high-fidelity modeling for future robotics and physics simulations.
* **Scientific Notation Support** — The Lexer and Parser now recognize exponential literals (e.g., `2e3`, `5.5E-10`), automatically promoting them to `double` precision.
* **Type Bifurcation** — Strict internal separation between `int32` vs `int64` and `float` vs `double`, providing granular control over how data is stored and operated upon.

**Unified Constant Pool & Memory Mapping**

* **The Constant Pool Architecture** — Introduction of a dedicated data section at the end of the binary. This allows loading 64-bit constants that exceed the immediate limits of standard RISC-V instructions.
* **Relative Addressing (`AUIPC`)** — The Emitter now uses PC-relative addressing to calculate offsets to the Constant Pool, ensuring code remains position-independent.
* **Universal Constant Loading** — Implementation of `LD` (Load Doubleword) and `FLD` (Float Load Double) to pull 8-byte values directly into registers.

**Expanded Instruction Set (ISA Extension)**

* **The "D" Extension (Double Precision)** — Full integration of RISC-V double-precision floating-point instructions, including `FADD.D`, `FSUB.D`, `FMUL.D`, and `FDIV.D`.
* **Word-Mode Operations (`-W` Instructions)** — Support for `ADDW`, `SUBW`, and other word-specific instructions in the VM to handle 32-bit arithmetic within 64-bit registers via sign-extension.
* **Precision Conversion** — Added specialized instructions for moving data between integer and floating-point registers, as well as converting between single and double precision.

**Optimizer & Compiler Intelligence**

* **Constant Folding** — The compiler now evaluates constant expressions at compile-time (e.g., `2 + 2` becomes `4`), reducing the number of instructions sent to the VM.
* **Dead Code Elimination (DCE)** — Implementation of a basic optimization pass that identifies and removes unreachable code segments, streamlining the final binary.
* **Refined Comment Nesting** — Upgraded the comment system to support nested block comments (`-| -| |- |-`), allowing for better code documentation and temporary code disabling.
* **Short-hand Single Comments** — Added `-/` as a lightweight syntax for single-line comments.

**VM Core Refinement**

* **8-Byte Alignment** — The VM and Emitter now coordinate to ensure 64-bit constants are properly aligned in memory, preventing desynchronization during data loads.
* **Extended Register Width** — Internal `regs` and `fregs` arrays have been upgraded to `int64_t` and `double` respectively to reflect the new 64-bit hardware reality.

---

## v2.1.0 — *The Ascension Logic Update*

> This version marks the transition from linear execution to complex decision-making. By implementing conditional branching, short-circuit logic, and a refined scope architecture, Zonetic attains a new level of computational "cultivation."

**Logic & Control Flow (The Decision Path)**

* **Conditional Branching (B-Type)** — Full support for `if`, `elif`, and `else` structures using native RISC-V branches: `BEQ`, `BNE`, `BLT`, `BGE`, `BLTU`, and `BGEU`.
* **Iterative Cultivation (Loops)** — Implementation of `while` loops with backward-jumping offsets for repetitive execution.
* **J-Type Instructions** — Added `JAL` (Jump and Link) and `JALR` for unconditional jumps and future function call support, providing a wider jumping range than standard branches.
* **Short-Circuit Evaluation** — The Emitter now generates optimized jump-based logic for `and` and `or` operators, avoiding unnecessary computations.

**Refactored Register & Scope Management**

* **Symbol Manager Integration** — A new specialized component that handles `Saved Registers` (s0-s11), ensuring precise variable persistence across scopes.
* **Temporal Isolation** — The `Register Manager` has been optimized to focus exclusively on `Temporary Registers` (t0-t6), improving allocation speed during expression evaluation.
* **Block Expression Support** — Introduction of `BlockExpr` logic, allowing scoped execution where local variables are automatically managed and registers are freed upon block exit.

**Expanded Instruction Set (ISA)**

* **Boolean & Bitwise Mastery** — Added logical instructions for both register and immediate forms: `AND`, `ANDI`, `OR`, `ORI`, `XOR`, and `XORI`.
* **Comparison Operations** — Implementation of `SLT` (Set Less Than) and its variants (`SLTI`, `SLTU`, `SLTUI`) to transform comparisons into boolean values (0 or 1) when needed.

**CLI & Developer Experience**

* **The `zon rebuild` Command** — Added a dedicated automation command to recompile the C++ Virtual Machine source code instantly. This streamlines the development cycle when modifying the VM's core.
* **Enhanced Debugging** — Improved VM output to track jump offsets and label resolutions during execution.

**Internal Refactoring**

* **Dual-Pass Label Resolution** — The Bytecodegen now performs a more robust label resolution to calculate precise relative offsets for B-Type and J-Type instructions.
* **Register-Symbol Decoupling** — Complete separation between variable storage and intermediate calculation logic for a more "real-world" compiler architecture.
---

## v2.0.0 — *The First Step To VM*

> Transition from Tree-walking to a high-performance C++ Virtual Machine based on Registers and RISC-V architecture. This version introduces the modular ecosystem (Compiler + VM).

**Core Infrastructure (ZonVM)**

* **High-Performance C++ Backend** — Implementation of a new execution engine written in C++20 for maximum efficiency.
* **RISC-V Inspired Architecture** — Adhesion to the RV32I standard with 32 general-purpose registers (`x0-x31`) and 64-bit double precision.
* **Instruction Set Architecture (ISA)** — Support for `I-Type` (immediates) and `R-Type` (register-to-register) instructions, including the `M-Extension` (MUL, DIV, REM).
* **Binary Bytecode Format** — Introduction of the `.zbc` (Zonetic Bytecode) format with custom magic number validation (`0x5A4F4E21`).

**Compiler & Bytecode Generation**

* **The Emitter Pipeline** — New backend phase that transforms the Semantic Tree into binary instructions.
* **Intelligent Register Allocation** — Implementation of a `Register Manager` to handle temporary and saved registers (`t` and `s` registers) following standard ABI rules.
* **Smart Execution Flow** — The `zon r` (run) command is now intelligent:
    - If input is `.zon`: Compiles to bytecode and executes immediately.
    - If input is `.zbc`: Skips compilation and runs directly in the VM.
* **Zonetic Compiler (Zonc)** — Refactored the internal pipeline to: `Lexer → Normalizer → Parser → Semantic → Bytecodegen`.

**CLI Evolution & Commands**

* **Command Hierarchy Refactor** — Transitioned from flat commands to a "Area + Flag" hierarchy for better scalability:
    - `zon st --zbc` / `zon st --path`: Area for state and configuration.
    - `zon clr --his`: Area for cleanup operations.
    - `zon vw --file` / `zon vw --ast` / `zon vw --vers`: Area for visualization and diagnostics.
* **Lazy Compilation in Launcher** — The global launcher now detects the absence of the VM binary and compiles the C++ source on-the-fly using `g++`.
* **Hybrid REPL Mode** — Maintained the legacy interpreter via `zon repl --in` while the default `zon repl` now targets the Bytecode VM.

**Distribution & Organization**

* **Modular Directory Structure** — New organized setup under `~/.zonetic/` with hidden sub-directories:
    - `.zonc/`: Python compiler and scripts.
    - `.zonvm/`: C++ source and VM headers.
* **Unified Versioning** — Synchronized versioning between the Compiler and VM to ensure bytecode compatibility.

---

## v0.1.6 — *The Fashionable Update*

> High-performance UX overhaul, intelligent REPL mechanics, and advanced CLI diagnostics for Linux and Android.

**REPL & Developer Experience (Linux/Termux)**

* **Advanced Line Editing** — Implementation of `GNU Readline` support, enabling horizontal cursor movement (← / →) and standard terminal shortcuts (**Ctrl+L**, **Ctrl+W**, **Ctrl+A/E**).
* **Persistent Unified History** — Added a 500-line history buffer shared between `REPL mode` and `setfile`. Commands are now stored in `~/.zonhistoryrepl`.
* **Intelligent Autocomplete** — Integrated a keyword-driven completion engine. The REPL now dynamically pulls keywords directly from the Lexer’s "Single Source of Truth" to provide **TAB** completion.
* **History Maintenance** — Added the `clrhis` command to the launcher for a clean privacy reset.
* **Resilient Initialization** — Automatic creation of history files with built-in `OSError` handling.

**CLI & Visualization**

* **Pretty Print Diagnostics** — Complete redesign of `zon ast` and `zon tokens` with enhanced visual hierarchy.
* **Refined Auto-Update** — Fixed critical permission bugs in the Linux/Termux `zon update` flow.
* **Unified Core Logic** — Synchronized the execution engine for both interactive and file-based modes.

**Technical Fixes**

* **Keyboard Mapping** — Fixed a conflict in `parse_and_bind` that intercepted the 'b' key.
* **Environment Parity** — Optimized terminal escape sequences for Linux/Termux vs Windows.

> **Note:** This was the last version using the Tree-walker as the primary execution engine.

---

## v0.1.5 — *The Install Windows & Auto-Update*
> Full Windows ecosystem support with automated deployment and cross-platform update parity

**CLI & Distribution**

- **Windows Native Installer** — Added `install.ps1`, a dedicated PowerShell installer that automates the entire setup on Windows environments.
- **Automated Path Configuration** — The Windows installer now automatically injects the Zonetic binary path into the `User Environment Variables`, enabling global `zon` command access without manual PATH editing.
- **Zonetic Windows Launcher** — Implementation of `zon.ps1`, a PowerShell-native wrapper that replicates the behavior of the Linux/Termux launchers.
- **Universal Auto-Update** — The `zon update` command is now fully functional on Windows. It synchronizes with the GitHub repository, handles version tracking, and performs hot-swaps of the compiler files.
- **Parity Architecture** — Refactored the update logic to ensure consistent behavior across Android (Termux), Linux, and Windows using environment-specific scripts.

**Technical Fixes**

- **PowerShell Execution Policies** — The installer now handles common execution policy restrictions to ensure a smooth one-command installation experience.
- **Cross-Platform IO** — Optimized internal file handling to prevent line-ending conflicts (CRLF vs LF) when updating scripts across different operating systems.

---

## v0.1.4 — *The Install & Auto-Update*
> Automated deployment system and self-syncing compiler for Linux and Android

**CLI & Distribution**
    
- **Automated Installers** — Added `install.sh` (Lightweight) and `install_complete.sh` (Full) for one-command setup via curl.
- **Zonetic Launcher** — Implementation of `zon_launcher.sh`, a smart wrapper that handles the global `zon` command and system updates.
- **Auto-Update System** — Added `zon update` command. It fetches updates from GitHub and performs a safe synchronization.
- **Stability Control** — The update system now parses commit messages to verify stability. It only allows updates if the commit is marked with the `[STABLE|version]` flag and blocks `[NOSTABLE]` builds.
- **Cross-Platform Synchronization** — Simplified workflow for developers moving between Windows, Linux, and Termux without re-cloning.
- **Sparse Checkout Integration** — The lightweight installer now only pulls essential source code and scripts, reducing disk footprint.

**Technical Fixes**

- **Path Resolution** — Fixed symlink recursion issues in the launcher to correctly locate `main.py` regardless of the execution directory.
- **Environment Detection** — The installer now automatically detects Termux vs Standard Linux to adjust paths and sudo requirements.

---

## v0.1.3 — *The CLI Update 2.0*
> Complete environment overhaul with cross-platform distribution and language refinements

**CLI & Distribution**
- **Unified Entry Point** — The compiler is now globally accessible via the `zon` command.
- **Linux & Android Integration** — Implementation of `shebang` in `main.py` combined with symbolic links in `$PREFIX/bin` or `/usr/local/bin` and execution permissions.
- **Windows Portability** — Added `zon.bat` wrapper and environment variable manipulation to enable global PATH access in CMD/PowerShell.
- **Formal Documentation** — Created comprehensive installation guides in `install_guides/`:
    - `INSTALL_LINUX.md`
    - `INSTALL_WINDOWS.md`
    - `INSTALL_ANDROID.md` (optimized for Termux).
- **Command Suite Expansion** — New standardized command flags:
    - `r` / `run`: Execute source files.
    - `vers`: Display compiler version.
    - `help`: Command usage guide.
    - `setpath` / `showpath` / `clrpath`: Internal workspace path management.
    - `repl`: Interactive mode with `EOF` trigger for multi-line execution.
    - `setfile`: Streamlined file creation (including directory tree) with an optional immediate run prompt.
- **CLI Security Layer** — Added dedicated error handling and safety messages specifically for CLI operations, independent from the core language diagnostics.

**Language Refinements**
- **Numeric Underscore Support** — Added numeric separators for readability (e.g., `1_000_000`).
    - Implementation is strict: only permitted for thousands separation in integers or the integer part of a float.
    - Disallowed in decimal parts or as leading/trailing characters.
- **Initialization Shadowing** — Refined `Initialization Statement` logic.
    - Shadowing (e.g., `mut x = 10; inmut x = x`) is now valid.
    - The shadowed variable remains accessible during the initialization of the new variable before being replaced in the scope.
    - Strict validation remains: standard assignment to an uninitialized variable (shadowing or not) will still trigger a diagnostic.

**New Lexer Errors**
- `E0007` — Invalid underscore usage (e.g., `100_` or `1_0.0`).
- `E0008` — Forbidden underscore usage in the decimal part of a float (e.g., `3.12_14`).

**Technical Fixes**
- **F-String Compatibility** — Refactored internal rendering to support Python 3.11 by removing nested quotes and backslashes in template expressions.
- **IO Normalization** — Fixed newline stripping issues in Windows environments during file generation.

---

## v0.1.2 — *The Struct Update*
> Zonetic gets structs — data blueprints, objects, and field access

**Language**
- `struct` keyword and `struct form` added — defines a named blueprint of fields
- `object` — a clone of a struct, created with a construct expression and stored in a variable
- `field` — a named slot inside a struct or object, declared with the same syntax as variables
- `impl` form planned for a future revision — methods not included in this version
- Struct names follow PascalCase convention and share the namespace with functions
- Structs registered through pre-scan — reachable from anywhere in the program
- Structs can only be declared in global scope

**Construct Expression**
- Syntax: `StructName[]`
- Fields can be passed by index, by name, or mixed — same rules as function call parameters
- Fields with default values are optional in the construct
- Uninitialized fields cannot be read until assigned

**Field Expression**
- Syntax: `object.field`
- Supports unlimited nesting — `object.field.field.field`
- Returns the value and type of the accessed field

**Field Assignment Statement**
- Syntax: `object.field = expr` or `object.field.field op= expr`
- Supports standard and compound assignment operators
- Respects field mutability declared in the struct

**Nee Parser Errors**
- `E2027` — Expected and identifier after `struct`
- `E2028` — Invalid field access syntax
- `E2029` — A field is assigned in the construct expr, but that same field had already been assigned before in the same construct.
- `E2030` — Positional assignment was found after starting to assign by key in construct expr
- `E2031` — It was expected, to continue or to terminate the construct expr, something else was found
- `E2032` — A field expression was used in the statement area, meaning no one expects a returned value

**New Semantic Errors**
- `E3027` — duplicate parameter name in function declaration
- `E3028` — complex expressions are used in the declaration of fields
- `E3029` — An attempt is being made to assign an expr to a field that is not the type of the field.
- `E3030` — object does not exist in scope
- `E3031` — variable exists but is not a struct object
- `E3032` — A field is assigned in a construct by key, but the key does not match any existing field in the struct
- `E3033` — field assignment target does not exist
- `E3034` — attempt to assign to an inmut field that already has a value
- `E3036` — It involves using a field that does not exist in the struct
- `E3037` — too many values passed to construct
- `E3038` — struct does not exist
- `E3040` — field does not exist in struct
- `E3041` — function name conflicts with existing struct name
- `E3042` — struct name conflicts with existing function name
- `E3043` — empty block expression
- `E3044` — field name shadowing inside struct block
- `E3045` — assigning a field that does not exist (this in a struct declaration)
- `E3046` — invalid statement inside struct block

---

## v0.1.1 — *The Function Update*
> Zonetic gets functions — the most significant feature addition since v0.1.0

**Language**
- `func` keyword and `func form` added — functions are now a first-class construct
- `return` statement added — exits a function and produces its value
- `-> type` explicit return type required on every function — including `-> void` for no return
- `void` type added — exclusively for function return types
- Parameters require explicit mutability — `mut` or `inmut` always declared
- Parameters always passed by copy — changes inside never affect the original outside
- Default parameter values supported — optional at call site
- `func main` as optional program entry point — if present, execution starts there regardless of declaration order
- Pre-scan phase added — all functions registered before execution begins, enabling forward references
- Recursion supported — each call creates an independent `CallFrame` with its own scope
- Functions see the global scope — variables declared outside any function are visible inside all functions

**Call Expression**
- Positional parameters — values matched left to right
- Keyparams — parameters passed by name using `name=value`
- Mixed calls supported — positional first, keyparams after; once a keyparam is used all following must be keyparams
- Keyparam terminology adopted — `param` for positional, `keyparam` for named

**Terminology**
- `parameter` adopted as the single term for both declaration and call contexts
- `keyparam` introduced for parameters passed by name in a call expression
- `argument` retired from Zonetic terminology to avoid confusion

**New Parser Errors**
- `E2013` — missing function name after `func`
- `E2014` — missing `(` after function name
- `E2015` — missing `=` after keyparam name in call
- `E2016` — missing `mut` or `inmut` to start a parameter
- `E2017` — missing parameter name after mutability keyword
- `E2018` — `void` used in invalid context
- `E2019` — invalid type in parameter declaration
- `E2020` — missing `:` after parameter name
- `E2021` — missing `->` after parameter list
- `E2022` — invalid return type after `->`
- `E2023` — keyparam passed more than once in the same call
- `E2024` — positional parameter found after a keyparam
- `E2025` — missing `,` or `)` after parameter (replaces E2015 for unclosed parameter lists)
- `E2026` — `return` found outside any block expr

**New Lexer Errors**
- `E0008` — malformed identifier starting with a digit

**New Semantic Errors**
- `E3013` — Existing function name being used for a new function
- `E3014` — `return` found in some block expr but not in function context
- `E3015` — The return type of the expression that has a `return` found in a function does not match the return type of that function.
- `E3016` — A value(`inmut`) is initialized in a loop when the value is not in the scope of the loop but at least one above it.
- `E3017` — An attempt is being made to declare a function within a function.
- `E3018` — `give` is used in a block that is not valid for expressions, for example: `func`
- `E3019` — semantic detects that there is no `return` in all possible paths (this only applies to functions that do not `return` `void`)
- `E3020` — It's called a non-existent function
- `E3021` — Parameters are added to a function call that the function does not need (if it has zero declared parameters).
- `E3022` — Parameters are being passed that do not match the declared parameters of the function.
- `E3023` — A keyparam is passed with the name of a parameter not declared in the function.
- `E3024` — Passing a value twice to a function parameter causes a collision; only one value can be passed per parameter.
- `E3025` — It was necessary to pass parameters in the call that the function expects
- `E3026` — A function call that returns `void` is used as an expression

**New Semantic Warnings**
- `W3005` — unreachable code below `return`
- `W3006` — unreachable code below `continue` or `break`

**New Runtime Errors**
- `E4002` — Stack Overflow

**Zon Std Lib Mininum**
- `print` print string on screen
- `readInt` — takes a string as an argument and returns a int
- `readFloat` — takes a string as an argument and returns a float
- `readString` — takes a string as an argument and returns a string

---

## v0.1.0 — *The First Release*
> Tree-walker interpreter complete — first fully functional version of Zonetic

**Interpreter**
- Full rewrite of the interpreter with visitor pattern
- `RuntimeScope` and `RuntimeValue` — clean separation from semantic scope
- All native expressions evaluated — arithmetic, boolean, comparison, unary
- Short-circuit evaluation for `and` and `or`
- `if form` as statement and as expression
- `while form` and `infinity form` with full loop execution
- `break` and `continue` via signal system (`BreakSignal`, `ContinueSignal`)
- `give` statement via `GiveSignal` — exits block and returns value
- Block expressions evaluated in both statement and value context
- `print` statement — concatenates multiple values without separator
- `input` statement — reads user input and converts to target type
- Runtime error system — `ZoneticRuntimeError` bubbles to pipeline entry point

**Runtime Errors**
- `E4001` — division by zero for `/` and `%`

**Semantic** *(completed this version)*
- `if form` as expression — type concordance across all branches
- `else` required when `if form` is used as expression (`E3010`)
- Return type mismatch across branches (`E3011`)
- `give` outside block expression (`E2012`)
- `break` and `continue` outside loop (`E3012`)
- Condition field type warnings — `W3002`, `W3003`
- Infinite loop detection without `break` — `W3004`

---

## v0.0.9
> The Great Refactor Update — language renamed from **Akon** to **Zonetic**

This is the biggest and most important update to date. Nearly everything was rewritten from scratch.

**Language & Identity**
- Language renamed from **Akon** to **Zonetic**
- `zon-cli` replaces `akon-cli`
- Zonny mascot added to the error system

**Lexer**
- Full rewrite with span system
- Binary search index for exact line and column reporting
- `FileMap` for source location tracking

**Normalizer**
- Full rewrite with hybrid statement terminator
- Supports both `;` and newline as statement terminators (one per script)

**Parser**
- Full rewrite with new AST hierarchy — `NodeStmt` and `NodeExpr`
- Real mutability system with `mut` and `inmut`
- Explicit type annotation with `: type` or `UNKNOWN` for future inference
- Form concept introduced — `if form`, `while form`, `infinity form`
- `give` statement for block expressions
- Operator enums — `ADD`, `SUB`, `MUL`, `FDIV`, `IDIV`, `MOD`, `POW`, etc.
- Type enums — `INT`, `FLOAT`, `BOOL`, `STRING`, `UNKNOWN`
- Basic scope system with parent chain

**Diagnostic System** *(new)*
- Indexed error codes — `E####` for errors, `W####` for warnings
- Span-aware error reporting with source line, column pointer, and context
- Severity system — `ERROR` and `WARNING`
- Error registry — all errors defined as data, not hardcoded strings
- Error limit system with summary of remaining errors
- Repeated error condensing — full detail on first occurrence, compact on repeats
- Chronological error sorting by source position
- Zonny — the compiler mascot with personality-driven help messages

**Semantic** *(in progress)*
- Type checker for all native expressions
- Real mutability enforcement
- Type inference from first assignment
- Block expression validation with `give`
- Unreachable code detection after `give`
- Scope chain with `Symbol` entries

**Documentation** *(all created in this version)*
- [`NERT`](docs/expressions/NERT.md), [`precedence_doc`](docs/expressions/precedence.md), [`forms_doc`](docs/forms/forms_doc.md), [`condition_field_doc`](docs/forms/condition_field_doc.md)
- [`types_doc`](docs/others/types_doc.md), [`expression_doc`](docs/expressions/expression_doc.md), [`statements_doc`](docs/statements/statements_doc.md), [`variable_vs_value_doc`](docs/others/variable_vs_value_doc.md)
- [`declaration_stmt_doc`](docs/statements/declaration_stmt_doc.md), [`assignment_stmt_doc`](docs/statements/assignment_stmt_doc.md), [`give_stmt_doc`](docs/statements/give_stmt_doc.md)
- [`break_stmt_doc`](docs/statements//break_stmt_doc.md), [`continue_stmt_doc`](docs/statements//continue_stmt_doc.md)

> Interpreter rewrite pending — will complete this version.

---

## v0.0.8
> The Semantic Prototype

- Semantic analysis added — type checker for all existing expressions and statements

---

## v0.0.7
> The Normalizer Update

- `TheNormalizer` added — hybrid statement terminator, supports both `;` and newline
- `NEWLINE` token added to the lexer
- Parser fix — precedence of `and`, `or`, and `not` corrected

---

## v0.0.6
> The Loop Update

- `while` loop added
- `loop` sugar syntax added (now called `infinity`)
- `break` and `continue` statements added
- `True` and `False` keywords changed to `true` and `false`
- Lexer refactor

---

## v0.0.5
> The CLI Update

- `akon-cli` added (now `zon-cli`) with REPL support
- Parentheses no longer required for conditions

---

## v0.0.4
> The Assignment Update

- Compound and standard assignment operators added: `=`, `+=`, `-=`, `*=`, `**=`, `/=`, `%=`
- General structure improvements

---

## v0.0.3
> The Control Flow Update

- `if`, `elif`, `else` added

---

## v0.0.2
> The Operators Update

- Arithmetic operators: `+`, `-`, `*`, `**`, `/`, `%`
- Comparison operators: `<`, `>`, `<=`, `>=`, `==`, `!=`
- Boolean operators: `and`, `or`, `not`

---

## v0.0.1
> The Beginning — language was called **Akon** at this point

- Lexer, tokens, and `TokenType`
- Basic AST nodes
- Basic parser
- Basic environment
- Basic interpreter
- `AkonErrors` — first error system (now replaced)
