<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/icons/svg/icon_zonetic_dark.svg">
  <img src="./assets/icons/svg/icon_zonetic.svg" width="300">
</picture> 

# Zonetic Programming Language

## What this project demonstrates

Zonetic is a systems-oriented programming language that showcases expertise in:

- **Compiler Design:** Implementing a full pipeline from lexing to bytecode generation.
- **Virtual Machine Architecture:** Designing a custom RISC-inspired execution engine (ZonVM).
- **Tooling & Infrastructure:** Building cross-platform CLI tools and automated installers.
- **Low-level logic:** Handling register allocation, memory layout, and binary formats.

A statically typed, expression-oriented language designed for robotics and performance-critical applications.

## Status

> **Current Version:** `v2.4.0` — *The Function Update 2.0* > **Next Milestone:** `v2.5.0` — *The Heap Update*

## Features

- **Bytecode Compilation:** Compiles high-level code into optimized binary instructions for ZonVM.
- **Hybrid Execution:** Integrated REPL with support for both Bytecode VM and Legacy Interpreter (`--in` mode).
- **Explicit mutability** with `mut` / `inmut`.
- **Form-based control flow** — `if form`, `while form`, `infinity form`, `func form`.
- **Rust-inspired error reporting** with source spans and Zonny.
- **Register-based ABI:** Sophisticated register management (Saved vs. Temporals).
- **Type inference** and strict numeric formatting (`1_000_000`).

## Pipeline

The compilation flow follows a modern structured pipeline:

```
launcher → cli → lexer → normalizer → parser → semantic → bytecodegen → ZonVM
```

Each phase generates indexed error codes for precise debugging:
- `E0xxx`: Lexer
- `E1xxx`: Normalizer
- `E2xxx`: Parser
- `E3xxx`: Semantic / Type Checker
- `E4xxx`: Tree-Walker
- `E5xxx`: Optimizations

## Quick Look (Legacy Interpreter Mode)

Current development focuses on the VM backend. To test high-level features like Structs and Strings, use the legacy interpreter:

```bash
alve-dev@dev-zonetic:~/.zonetic$ zon repl --in
[zon info]: Repl Mode. Type 'EOF' or Ctrl+D to end.
>> print("Hello from Legacy Mode")
>> EOF
Hello from Legacy Mode
--------------------------------------------------------------------------------
[ MASSIVE SUCCESS ] Compiler: 0.26ms | Runtime: 0.03ms | Total: 0.29ms
[ ⌐■_■]b <("Epic execution, bro. Your logic is as sharp as a Katana!")
```

In vm:

```bash
alve-dev@dev-zonetic:~/.zonetic$ zon repl
[zon info]: Repl Mode. Type 'EOF' or Ctrl+D to end.
>> print(10)
>> EOF
10
```

## Documentation

> Full language documentation → [zonetic-official-docs](https://github.com/alve-dev/zonetic-official-docs)

## Installation

Zonetic 2.0.0 uses a modular installation. The compiler and VM are synchronized automatically by the installer.

* **Linux:** [Installation Guide for Linux](./install_guides/INSTALL_LINUX.md)
* **Windows (MinGW):** [Installation Guide for Windows](./install_guides/INSTALL_WINDOWS.md)
* **Android:** [Installation Guide for Android](./install_guides/INSTALL_ANDROID.md)
* **macOS:** *Coming soon (Testing in progress)*

![Language](https://img.shields.io/badge/written%20in-Python-yellow)
[![Version](https://img.shields.io/badge/version-2--4--0-orange)](changelog.md)
