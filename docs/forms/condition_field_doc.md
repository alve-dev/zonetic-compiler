# Condition Field

## What is a Condition Field?

A condition field is a slot used by certain forms to make decisions based on logic.

It expects a single expression that must return a `bool` — either `true` or `false`.
That result is what the form uses to decide what to do next.

## How it works

When a form has a condition field, Zonetic evaluates the expression inside it.
If the result is `true`, the form acts on it — for example, executing a block or repeating it.
If the result is `false`, the form skips or stops.

The expression inside a condition field can be as simple or as complex as needed,
as long as it produces a `bool` at the end.
```zonetic
if num > 10 {
    ...
}
```

Here `num > 10` is the condition field. Zonetic evaluates it and gets either `true` or `false`.
```zonetic
while num < 5 and active == true {
    ...
}
```

Here `num < 5 and active == true` is the condition field.
It combines two expressions with `and` — the result is still a single `bool`.

## Restriction

A condition field only accepts expressions that return `bool`.
Passing any other type — such as `int`, `float`, or `string` — is a semantic error.

> To see which expressions return `bool` and which return other types,
> see the [NERT](../expressions/NERT.md).