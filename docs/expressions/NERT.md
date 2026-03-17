# Native Expression Return Table a.k.a NERT

This table defines the static semantic rules for native expressions in Zonetic.
Each operator specifies its accepted operand types, semantic constraints, and return type.

---

## Arithmetic Expressions

### Common Arithmetic Rules

Unless stated otherwise, arithmetic operators follow these rules:

- **Operands:** `int | float`
- **Restriction:**  
  Both operands must be of the **same type**, otherwise a semantic error is raised.
- **Return behavior:**  
  - returns `int` if both operands are `int`
  - returns `float` if both operands are `float`

### Addition

- **Call operator:** `+`
- **Return type:** `int | float`
- **Rules:** Common Arithmetic Rules

### Subtraction

- **Call operator:** `-`
- **Return type:** `int | float`
- **Rules:** Common Arithmetic Rules

### Multiplication

- **Call operator:** `*`
- **Return type:** `int | float`
- **Rules:** Common Arithmetic Rules

### Float Division

- **Call operator:** `/`
- **Return type:** `float`
- **Special rule:**  
  Always returns `float`, regardless of operand type.

### Integer Division

- **Call operator:** `//`
- **Return type:** `int`
- **Special rule:**  
  Always returns `int`.

### Exponentiation

- **Call operator:** `**`
- **Return type:** `int | float`
- **Rules:** Common Arithmetic Rules 

### Negation

- **Call operator:** `-`
- **Operand:** `right`: `int | float`
- **Return type:** `int | float`
- **Special rules:**
  - `-` operates on a **single right-hand operand**
  - `-42` is interpreted as `neg(42)`
  - Even pairs of negatives cancel each other out, odd pairs reverse the Boolean: `-5 == -5`, `--5 == 5`, `---5 == -5`, etc
  - To apply negation after exponentiation, parentheses are required:
    `-2 ** 2` evaluates as `neg(2 ** 2)` = `-4`, not `(-2) ** 2` = `4`

---

## Boolean Expressions

### Common Boolean Rules

Unless stated otherwise, boolean expressions follow these rules:

- **Operands:** `bool`
- **Restriction:**  
  Both operands must be of type `bool`, otherwise a semantic error is raised.
- **Return behavior:**  
  Always returns `bool`.

### Bool-wise AND

- **Call operator:** `and | &&`
- **Return type:** `bool`
- **Rules:** Common Boolean Rules
- **Special rule:**  
  If the left operand evaluates to `false`, the result is immediately `false`  
  *(short-circuit evaluation)*.

### Bool-wise OR

- **Call operator:** `or | ||`
- **Return type:** `bool`
- **Rules:** Common Boolean Rules
- **Special rule:**  
  If the left operand evaluates to `true`, the result is immediately `true`  
  *(short-circuit evaluation)*.

### Bool-wise NOT

- **Call operator:** `not | !`
- **Return type:** `bool`
- **Operand:** `right`: `bool`
- **Special rules:**
  - `not` operates on a **single right-hand operand**
  - `not true` is interpreted as `not(true)`
  - `not true and false` is interpreted as `(not true) and false`
  - To express `not (true and false)`, parentheses must be used explicitly
  - Even pairs of Not cancel each other out, odd pairs reverse the Boolean: `not true == false`, `not not true == true`, `not not not true == false`, etc

---

## Comparison Expressions

Comparison expressions compare two values and return a boolean result.

> **Note:**  
> Equality operators (`==`, `!=`) accept a wider set of types than relational
> operators. See their individual entries below.

### Common Comparison Rules

Unless stated otherwise, comparison expressions follow these rules:

- **Operands:** `int` or `float`
- **Restriction:**
  - `left` and `right` must be of the **same numeric type**
  - Mixed comparisons (`int` vs `float`) are not allowed
- **Return behavior:**  
  Always returns `bool`

### Less Than

- **Call operator:** `<`
- **Operands:** `left`, `right`
- **Return type:** `bool`
- **Rules:** Common Comparison Rules

### Greater Than

- **Call operator:** `>`
- **Operands:** `left`, `right`
- **Return type:** `bool`
- **Rules:** Common Comparison Rules

### Less Than Or Equal To

- **Call operator:** `<=`
- **Operands:** `left`, `right`
- **Return type:** `bool`
- **Rules:** Common Comparison Rules
- **Definition:** `<=` is **syntactic sugar** for `a < b or a == b`

#### Desugaring Rule
```zonetic
a <= b
-- is equivalent to:
a < b or a == b
```

### Greater Than Or Equal To

- **Call operator:** `>=`
- **Operands:** `left`, `right`
- **Return type:** `bool`
- **Rules:** Common Comparison Rules
- **Definition:** `>=` is **syntactic sugar** for `a > b or a == b`

#### Desugaring Rule
```zonetic
a >= b
-- is equivalent to:
a > b or a == b
```

### Equal To

- **Call operator:** `==`
- **Operands:** `left`, `right`
- **Return type:** `bool`
- **Accepted types:** `int`, `float`, `bool`, `string`
- **Restriction:** `left` and `right` must be of the **same type**

#### Special Notes

- **String equality** is implemented internally as a function call, lowered to:
```zonetic
  string.equal_to(other_string) -> bool
```
  This function is also exposed publicly in `string_lib`.

### Not Equal To

- **Call operator:** `!=`
- **Operands:** `left`, `right`
- **Return type:** `bool`
- **Rules:** Same as **Equal To**
- **Definition:** `!=` is **syntactic sugar** for the negation of equality

#### Desugaring Rule
```zonetic
a != b
-- is equivalent to:
not a == b
```

### Spaceship Operator

- **Call operator:** `<=>`
- **Operands:** `left`, `right`
- **Planned return type:** `int8`
- **Status:** *In progress*

### Semantic Notes

- Chained comparisons are **not allowed**:
```zonetic
  5 > 6 > 7  -- ❌ invalid
```
  The expression `6 > 7` returns `bool`, and comparison operators do not accept `bool` operands.

- Equality for arrays is **not currently supported**. This behavior will be defined in a future revision.

---

## Special Expressions

### Block Expression

- **Call operator:** `{ }`
- **Return type:** Depends on the `give` statement inside the block, or `void` if no `give` is present.
- **Operands:** None — a block expression contains statements, not operands.

#### Behavior

A block expression introduces its own scope and executes a sequence of statements.
Its return type is determined at the point where `give` is used.

- If `give` is present, the block produces a value of the type of the expression passed to `give`.
- If `give` is absent, the block produces no value (`void`).

#### Restrictions

- If a block expression is used in a **value context** — such as an assignment or inside another expression — it **must** contain a `give` statement. Omitting `give` in this context is a semantic error.
- If a block expression is used as a **statement** — standing alone with no surrounding context expecting a value — `give` is **optional**. Using `give` in this context produces a warning, as the value will be discarded.

#### Example — Block as statement (no value expected)
```zonetic
{
    mut counter: int = 0
    counter = counter + 1
}
```

This block executes, modifies `counter` locally, and produces no value.
`counter` is not visible outside the block.

#### Special rules

- All variables declared inside a block are **scoped to that block** and are not accessible outside of it.
- A block expression can be **nested** inside another block expression. Each block maintains its own scope, and inner blocks can access variables from outer blocks through the scope chain.