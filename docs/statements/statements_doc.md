# Statements

## What is a Statement?

A statement is any piece of code that **does something**.

Unlike expressions, statements do not produce a value — they perform an action that changes the program in some way.

### Simple examples
```zonetic
mut score: int = 0
```
This is a statement. It creates a new variable called `score` and gives it the value `0`.
Nothing is produced — a variable now exists in the program that did not exist before.
```zonetic
score = score + 1
```
This is also a statement. It takes the current value of `score`, adds `1`, and stores the result back into `score`.
The program has changed — `score` is now different.

### Statements are instructions

Think of a statement as an instruction you give to Zonetic:
- *"Create this variable."*
- *"Change this value."*
- *"Run this block if the condition is true."*
- *"Keep repeating this block until I say stop."*

Each instruction changes something about the program — its variables, its flow, its state.

### Statements do not produce values

A statement cannot be used where a value is expected.
You cannot do this:
```zonetic
mut x: int = mut y: int = 0
```

`mut y: int = 0` is a statement — it does not produce a value, so it cannot be used as one.

### Expressions inside statements

Even though statements do not produce values themselves, they often contain expressions.
```zonetic
mut result: int = 3 + 2
```

Here `3 + 2` is an expression — it produces `5`.
The statement uses that value to initialize `result`.
The expression does the math. The statement stores the result.