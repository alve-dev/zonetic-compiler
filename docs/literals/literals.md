# Literals in Zonetic

This document defines **literals** in Zonetic.

Literals represent **raw values** directly written in source code.  
They are **not expressions**: literals do not compute or transform values, they simply denote a value.

> **Note:**  
> Literals are intentionally separated from expressions and from types.  
> For example, the type `int` is **not** an integer literal.

---

## Numeric Literals

Numeric literals represent numeric values written directly in source code.

### Definition

A numeric literal is any sequence of numeric characters that forms a valid number.

Numeric literals belong to one of the following categories:

- **Integer literals**
- **Floating-point literals**

---

### Integer Literals

- Composed exclusively of digits (`0–9`)
- May include underscore (`_`) as a digit separator
- Do **not** contain a decimal point (`.`)

#### Examples

```zonetic
0
42
1000000
1_000_000
```

#### Digit Separator (`_`)
- The underscore is used for **readability only**
- It has **no semantic meaning**
- The following behavior is **currently under consideration:**
```zonetic
1_000_00
```

>**Status:** ***In progress***
>It is undecided whether malformed grouping should:
>  - "raise a semantic error, or"
>  - "be normalized into a valid integer value"
This rule will be finalized in a future revision.

---

### Floating-point Literals
- Contain exactly **one** decimal point (`.`)
- Must form a valid numeric representation
- Cannot contain multiple decimal points

#### Examples

```zonetic
0.0
3.14
100.5
1_000.25
```

#### Invalid Examples

```zonetic
100.0.0   // ❌ invalid
```

---

### Integer vs Float Resolution
- If a numeric literal contains a decimal point (`.`), it is a **float**
- Otherwise, it is a **integer**

---

## String Literals

String literals represent sequences of characters.

### Definition

A string literal is any sequence of characters enclosed by matching quotes:

- Double quotes: " ... "

- Single quotes: ' ... '

The opening and closing quote **must be the same type.**

#### Examples
```zonetic
"hello"
'world'
```

---

#### Escape Sequences

The backslash (`\`) introduces an escape sequence.

A standalone backslash is **invalid** and results in a lexical error.

##### Supported Escape Sequences
**Escape**  **Meaning**
---
`\n`  newline
`\t`  tab
`\\`  literal backslash (`\`)
`\()` ***In progress*** (future interpolation support)