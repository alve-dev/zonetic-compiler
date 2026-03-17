# Break Statement

## What is a Break Statement?

A break statement stops a loop immediately and exits it.
When Zonetic encounters `break`, it leaves the current loop and continues the program
from the point right after the loop.

---

## Where it can be used

`break` can only be used inside a `while` form or an `infinity` form.
Using `break` outside of a loop is a semantic error.

---

## Behavior

When `break` executes, the loop stops immediately.
Any statements below `break` inside the current iteration are skipped.
The program continues from the next statement after the loop.
```zonetic
mut num: int = 0

infinity {
    num += 1

    if num == 5 {
        break
    }
}
```

When `num` reaches `5`, `break` exits the infinity form.
The program continues after the closing `}` of the loop.

---

> `break` will be extended in a future revision to support loop identifiers,
> allowing it to exit a specific outer loop from inside a nested one.