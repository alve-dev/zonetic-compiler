# Assignment Statement

## What is an Assignment Statement?

An assignment statement updates the value of an existing variable.
It does not create a new variable — the variable must already exist in the current scope
or in an outer scope. If it does not, a semantic error is raised.

---

## Structure
```
name operator expr
```

All three parts are **required**. Nothing here is optional.

- **name** — the identifier of the variable to update
- **operator** — a valid assignment operator
- **expr** — an expression whose return type must match the variable's type

---

## Type Rules

The expression on the right must return the same type as the variable.
If it does not, a semantic error is raised.
```zonetic
mut score: int = 0

score = 10          -- ✓ valid, int matches int
score = 3.14        -- ❌ error, float does not match int
```

If the variable's type is still `UNKNOWN` — meaning it was declared without a type
and has never been assigned before — the first assignment defines its type permanently.
```zonetic
mut score
score = 10          -- score is now int, permanently
score = "hello"     -- ❌ error, score is already int
```

---

## Assignment Operators

Zonetic currently supports the following assignment operators:

| Operator | Meaning |
|----------|---------|
| `=`      | Standard assignment |
| `+=`     | Add and assign |
| `-=`     | Subtract and assign |
| `*=`     | Multiply and assign |
| `**=`    | Exponentiate and assign |
| `/=`     | Float divide and assign |
| `//=`    | Integer divide and assign |
| `%=`     | Modulo and assign |

Every compound operator is **syntactic sugar**. They all desugar to a standard assignment:
```zonetic
score += 1
-- is equivalent to:
score = score + 1

score **= 2
-- is equivalent to:
score = score ** 2
```

The compiler treats them as the same thing — a read, an operation, and a write back.

---

## Mutability

Only `mut` variables can be reassigned.
Attempting to assign to an `inmut` variable after its first assignment is a semantic error.
```zonetic
inmut name: string = "Zonetic"
name = "Other"      -- ❌ error, name is inmutable
```

> For more on mutability and the difference between `mut` and `inmut`,
> see [`declaration_stmt_doc.md`](declaration_stmt_doc.md).