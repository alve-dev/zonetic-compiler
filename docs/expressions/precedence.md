## Operator Precedence

Operators are listed from **highest** to **lowest** precedence.
Operators on the same level share the same precedence and are evaluated left-to-right,
unless stated otherwise.
```
Level 7  │  Literals & Grouping(Primitive)   │  42  3.14  true  "hi"  (expr) {block_expr}
Level 6  │  Exponentiation                   │  a ** b              (right-to-left)
Level 5  │  Unary                            │  -a
Level 4  │  Multiplicative                   │  a * b   a / b   a // b   a % b
Level 3  │  Additive                         │  a + b   a - b
Level 2  │  Comparison & Equality            │  a > b   a < b   a >= b   a <= b   a == b   a != b
Level 1  │  Boolean NOT                      │  not a
Level 0  │  Boolean AND / OR                 │  a and b   a or b
```