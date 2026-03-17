# Continue Statement

## What is a Continue Statement?

A continue statement skips the rest of the current iteration and jumps back to the top of the loop.
When Zonetic encounters `continue`, it ignores everything below it in the current iteration
and starts the next one immediately.

---

## Where it can be used

`continue` can only be used inside a `while` form or an `infinity` form.
Using `continue` outside of a loop is a semantic error.

---

## Behavior

When `continue` executes, the current iteration stops at that point.
Everything below `continue` inside the block is skipped.
The loop goes back to the top — the condition is evaluated again for `while`,
or the block restarts immediately for `infinity`.
```zonetic
mut num: int = 0

while num < 10 {
    num += 1

    if num == 5 {
        continue
    }

    mut result = num * 2
}
```

When `num` equals `5`, `continue` skips `mut result = num * 2` for that iteration
and jumps back to evaluate `num < 10` again.
All other iterations execute normally.

---

> `continue` will be extended in a future revision to support loop identifiers,
> allowing it to skip to the next iteration of a specific outer loop from inside a nested one.