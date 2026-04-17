# Changelog

All notable changes to Zonetic are documented here.
Versions are listed from newest to oldest.
 
---
## v0.1.6 — *The Fashionable Update*

> High-performance UX overhaul, intelligent REPL mechanics, and advanced CLI diagnostics for Linux and Android.

**REPL & Developer Experience (Linux/Termux)**

* **Advanced Line Editing** — Implementation of `GNU Readline` support, enabling horizontal cursor movement (← / →) and standard terminal shortcuts (**Ctrl+L**, **Ctrl+W**, **Ctrl+A/E**).
* **Persistent Unified History** — Added a 500-line history buffer shared between `REPL mode` and `setfile`. Commands are now stored in `~/.zonhistoryrepl`.
* **Intelligent Autocomplete** — Integrated a keyword-driven completion engine. The REPL now dynamically pulls keywords directly from the Lexer’s "Single Source of Truth" to provide **TAB** completion (includes `EOF` and `exit()`).
* **History Maintenance** — Added the `clrhis` command to the launcher. It performs a 0-byte truncation of the history file for a clean privacy reset.
* **Resilient Initialization** — Automatic creation of history files with built-in `OSError` handling to ensure stability in read-only or restricted environments.

**CLI & Visualization**

* **Pretty Print Diagnostics** — Complete redesign of `zon ast` and `zon tokens`. Outputs now feature enhanced visual hierarchy and formatting for easier debugging of the syntax tree.
* **Refined Auto-Update** — Fixed critical permission bugs in the Linux/Termux `zon update` flow. The updater now ensures the execution bit (`+x`) is restored post-synchronization.
* **Unified Core Logic** — Synchronized the execution engine for both interactive and file-based modes, ensuring that UX improvements in the REPL are inherited by `setfile`.

**Technical Fixes**

* **Keyboard Mapping** — Fixed a conflict in `parse_and_bind` that intercepted the 'b' key, restoring standard character input while maintaining Emacs-style control shortcuts.
* **Environment Parity** — Optimized terminal escape sequences to ensure Linux/Termux performance doesn't conflict with Windows PowerShell's native handling.

> **Coming next** — **v2.0.0**: The dawn of **Zonetic 2**. Transitioning from Tree-walking to a high-performance C++ Virtual Machine based on Registers and > RISC-V architecture.

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
