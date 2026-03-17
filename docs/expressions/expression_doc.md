# Expressions

## What is an Expression?

An expression is any piece of code that produces a value.

When Zonetic sees an expression, it evaluates it — it does the work — and the result is a value you can use.

### Simple examples
```zonetic
5
```
This is an expression. It produces the value `5`.
```zonetic
3 + 2
```
This is also an expression. Zonetic adds `3` and `2` and the result is `5`.
```zonetic
10 > 3
```
This is an expression too. Zonetic compares `10` and `3` and the result is `true`.

### Expressions can be combined

Because every expression produces a value, you can use expressions inside other expressions.
```zonetic
(3 + 2) * 4
```

Zonetic first evaluates `3 + 2` and gets `5`. Then it evaluates `5 * 4` and gets `20`.
The final result is `20`.

### Expressions always produce something

No matter how simple or complex, an expression always ends with a value.
That value has a type — it could be a number, a boolean, a string, or something else.
Zonetic uses that type to make sure you are using the value correctly.

---