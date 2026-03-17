# Give Statement

## What is a Give Statement?

A give statement produces a value from a block expression and exits it immediately.
When Zonetic encounters `give`, it evaluates the expression to its right,
returns that value to whoever is waiting for it, and leaves the block.
Any statements below `give` inside the block are not executed.

---

## Where it can be used

`give` can only be used inside a block expression.
Using `give` outside of a block expression is a semantic error.

---

## Structure
```
give expr
```

- **expr** — any expression. Its return type becomes the return type of the block.

---

## Behavior

When `give` executes, two things happen at the same time:
- The expression to its right is evaluated and its value is produced.
- The block exits immediately — nothing below `give` runs.
```zonetic
mut result: int = {
    mut x: int = 10
    mut y: int = 20
    give x + y
    mut z: int = 99    -- never executes
}
```

`give x + y` produces `30` and exits the block.
`mut z: int = 99` is never reached.

---

## Give in a Value Context

When a block expression is used where a value is expected — such as an assignment —
`give` is required. Without it, the block produces nothing and a semantic error is raised.
```zonetic
mut result: int = {
    mut x: int = 5
    give x * 2        -- ✓ required here
}
```

---

## Give in a Statement Context

When a block expression is used as a standalone statement with no value expected,
`give` is optional. Using it produces a warning — the value will be computed but discarded.
```zonetic
{
    mut x: int = 5
    give x * 2        -- ⚠ warning, value is discarded
}
```

---

> `give` will be extended in a future revision to work inside loop forms,
> where it will act as a combined break and value return.