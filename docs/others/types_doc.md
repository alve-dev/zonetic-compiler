# Types

## What is a Type?

A type tells Zonetic what kind of value a variable holds.
Zonetic uses types to make sure values are used correctly — for example,
you cannot add a number to a string, or compare a boolean with a float.

---

## Current Types

### `int`
Whole numbers, positive or negative.
```zonetic
mut age: int = 25
mut temperature: int = -10
```

### `float`
Numbers with a decimal point.
```zonetic
mut price: float = 3.14
mut ratio: float = 0.5
```

### `string`
Text — any sequence of characters enclosed in quotes.
```zonetic
mut name: string = "Zonetic"
mut message: string = "Hello, world!"
```

### `bool`
A logical value — either `true` or `false`.
```zonetic
mut active: bool = true
mut finished: bool = false
```

---

## Special Types

### `UNKNOWN`
`UNKNOWN` is an internal compiler type. It is not a type you write yourself —
it appears when a variable is declared without an explicit type annotation,
signaling to Zonetic that the type will be inferred from the first assigned value.
```zonetic
mut score       -- type is UNKNOWN until first assignment
score = 10      -- type is now inferred as int
```

> `UNKNOWN` is not valid as an explicit type annotation.
> Writing `mut x: UNKNOWN` is a semantic error.

---

> This document covers the current types available in Zonetic.
> More types — such as `int32`, `int64`, and others — will be added in future revisions.