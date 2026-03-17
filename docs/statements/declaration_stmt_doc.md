# Declaration Statement

## What is a Declaration Statement?

A declaration statement creates a new variable in the current scope.
Once declared, the variable exists and can be used by other statements and expressions.

---

## Structure

A declaration always starts with a **mutability keyword** — either `mut` or `inmut`.
This defines whether the variable can change after its first assignment or not.
```
mut | inmut name [: type] [= expr]
```

The mutability keyword and the name are **required**.
The type annotation and the initial value are **optional**.

---

## The Name

The name of a variable — also called an **identifier** — follows these rules:

- Can contain letters `a-z`, `A-Z`, digits `0-9`, and underscores `_`
- **Must start** with a letter `a-z`, `A-Z`, or an underscore `_`
- Cannot start with a digit
```zonetic
mut score     -- ✓ valid
mut _temp     -- ✓ valid
mut x1        -- ✓ valid
mut 1x        -- ❌ invalid, starts with a digit
```

---

## Type Annotation

The type annotation is optional. It is written with `:` followed by a valid type.
```zonetic
mut x: int
```

If no type is given, the variable gets the type `UNKNOWN` — Zonetic will infer its type
from the first value assigned to it.
```zonetic
mut x
```

Here `x` is declared with no type. Its type will be determined later.

---

## A Declaration on Its Own

A declaration with no value simply introduces the variable into the scope.
```zonetic
mut score: int
inmut name: string
mut flag
```

These variables exist but have no value yet.
Attempting to use them before a value is assigned is a semantic error.

---

## Initialization — Declaration + Assignment in One Line

A declaration can include an initial value using `=` followed by an expression.
This is called an **initialization**.
```zonetic
mut score: int = 0
```

Initialization is **syntactic sugar**. This single line is exactly equivalent to:
```zonetic
mut score: int
score = 0
```

The compiler treats them as the same thing — a declaration followed by an assignment.

---

## Type Rules

**If the type is explicit:**
The expression must return the declared type. If it does not, a semantic error is raised.
```zonetic
mut score: int = 3.14   -- ❌ error, float is not int
mut score: int = 10     -- ✓ valid
```

**If the type is `UNKNOWN`:**
The type is inferred from the first value assigned — either in the initialization
or in the first assignment statement after the declaration.
```zonetic
mut score = 10          -- score is inferred as int
mut name = "Zonetic"    -- name is inferred as string
```

---

## Mutability

- `mut` — the variable can be reassigned after its first value.
- `inmut` — the variable can only be assigned **once**. Any further assignment is a semantic error.
```zonetic
mut score: int = 0
score = 10              -- ✓ valid, score is mutable

inmut name: string = "Zonetic"
name = "Other"          -- ❌ error, name is inmutable
```

> To understand the difference between mutable variables and inmutable values in depth,
> see [`variable vs value`](../others/variable_vs_value_doc.md).