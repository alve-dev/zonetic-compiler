<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/icons/svg/icon_zonetic_dark.svg">
  <img src="./assets/icons/svg/icon_zonetic.svg" width="300">
</picture>

# Zonetic Programming Language — Tree-Walker

A statically typed, expression-oriented language designed for robotics.

> **This repository contains the tree-walker interpreter version of Zonetic.** > The bytecode VM version will live in a separate repository once development begins.

## Status

> `v0.1.3` — The CLI Update 2.0 release.  
> **Coming Soon:** The Closure Update

## Features

- **Multi-platform CLI** — Native support for Linux, Windows, and Android (Termux).
- **Explicit mutability** with `mut` / `inmut`.
- **Form-based control flow** — `if form`, `while form`, `infinity form`.
- **Block expressions** with `give`.
- **Functions** with typed parameters, keyparams, and default values.
- **Structs** with field access, construct expressions, and nested objects.
- **Initialization Shadowing** — Reuse variable names during initialization.
- **Numeric Underscores** — Strict support for readable numbers (`1_000_000`).
- **Rust-inspired error reporting** with spans and Zonny.
- **Hybrid statement terminators** — `;` or newline.
- **Type inference** from first assignment.

## Quick Look

```
-| while form |-
mut i: int = 0
while i < 3 {
    i += 1
}

-| if form |-
if i == 1 {
    print("one")
} elif i == 2 {
    print("two")
} else {
    print("three")
}

-| func form |-
func greet(inmut name: string) -> void {
    print("Hello, ", name)
}

greet("Zonetic")

-| struct form |-
struct Point {
    mut x: int = 0
    mut y: int = 0
}

mut p = Point[3, 7]
print("x: ", p.x, " y: ", p.y)
```

**Terminal execution:**
```bash
ZoneticDev ~/ zon r quick_look.zon
--- Executing ---
three
Hello, Zonetic
x: 3 y: 7
```

## Documentation

> Full language documentation → [zonetic-official-docs](https://github.com/alve-dev/zonetic-official-docs)

## Pipeline
```
source → lexer → normalizer → parser → semantic → interpreter
```

Each phase has its own indexed error codes — `E0xxx` lexer, `E1xxx` normalizer, `E2xxx` parser, `E3xxx` semantic, `E4xxx` runtime.

## Logo

The Zonetic logo is available in both SVG and PNG formats.

- **SVG** — vector format, scales to any size. Available in [assets/icons/svg](assets/icons/svg).  
  > On mobile, SVG files may require a dedicated app to open. If your device does not support SVG natively, any vector graphics viewer will work.
- **PNG** — raster format, works everywhere. Available in [assets/icons/png/](assets/icons/png/) in multiple sizes.

## Installation

Choose your operating system:

* **Linux:** [Installation Guide for Linux](./install_guides/INSTALL_LINUX.md)
* **Windows:** [Installation Guide for Windows](./install_guides/INSTALL_WINDOWS.md)
* **macOS:** *Coming soon (Testing in progress)*
* **Android:** [Installation Guide for Android](./install_guides/INSTALL_ANDROID.md)

![Language](https://img.shields.io/badge/written%20in-Python-yellow)
[![Version](https://img.shields.io/badge/version-0--1--3-orange)](changelog.md)
