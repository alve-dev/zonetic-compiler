# Forms

## What is a Form?

A form is a language construct that works alongside a block expression to extend or control its behavior.
A form may add new capabilities to a block, impose restrictions on it, or define how and when it executes.

A form cannot exist without a block expression — the block is always the body of the form.
Some forms work with a single block, others coordinate multiple blocks to express branching or repetition.

---

## If Form

The if form is a decision-making construct. It does not modify the internal behavior of its block expressions — it controls **which block executes** based on conditions.

The if form works with **branches**. Each branch owns a block expression and a condition field.
For more information on condition fields, see [`docs/form/condition_field_doc.md`](condition_field_doc.md).

### Branch Types

The if form has three types of branches:

**Opening branch — `if`**
The entry point of the if form. Always required and always evaluated first.
Opens the decision structure.

**Continuation branch — `elif`**
Extends the decision structure. Zero or more `elif` branches may follow the `if` branch.
Each one is evaluated in order if the previous branch was not taken.

**Exception branch — `else`**
Closes the decision structure. Optional and always appears last.
Has no explicit condition — internally its condition field is always `true`.
If an `elif` appears after an `else`, it is a semantic error.

> All three branch types share the same internal structure: a condition field and a block expression.
> The difference between them is structural and semantic, not mechanical.

---

### Early Entry

The if form uses **early entry**: once a branch condition evaluates to `true`, its block executes and all remaining branches are skipped immediately. Evaluation always flows top to bottom and stops at the first match.

---

### Flow — Single If Form
```
if condition_1 {      ──► condition_1 true?  ──► YES ──► execute block, exit form
    ...                                           │
}                                                NO
elif condition_2 {    ──► condition_2 true?  ──► YES ──► execute block, exit form
    ...                                           │
}                                                NO
else {                ──► always true        ──► YES ──► execute block, exit form
    ...
}
```

All branches belong to the same if form. Only one block will ever execute. This is early entry.

---

### Flow — Two Separate If Forms
```
if condition_1 {      ──► condition_1 true?  ──► YES ──► execute block
    ...               
}                     ──► continues regardless

if condition_2 {      ──► condition_2 true?  ──► YES ──► execute block
    ...
}                     ──► continues regardless
```

These are two independent if forms. Each one is evaluated on its own.
Both blocks may execute if both conditions are true.
There is no early entry between separate if forms — they do not share a decision structure.

---

### Why Three Branch Types?

The three branch types exist to make the **structure of the decision explicit**:

- `if` opens the form — there is always exactly one.
- `elif` continues it — the decision is still being made.
- `else` closes it — no condition was met, this is the fallback.

Without this distinction, two consecutive `if` blocks would be ambiguous:
are they the same decision or two independent ones?
In Zonetic, the answer is always clear from the keyword used.

---

### Example
```zonetic
inmut score: int = 75

if score >= 90 {
    mut grade = "A"
} elif score >= 75 {
    mut grade = "B"
} elif score >= 60 {
    mut grade = "C"
} else {
    mut grade = "F"
}
```

---

## While Form

The while form is a repetition construct. It works on top of a block expression and extends it with two capabilities: the ability to use `break` and `continue` statements inside the block.

The while form has a condition field and a block expression.
For more information on condition fields, see [`docs/form/condition_field_doc.md`](condition_field_doc.md).

### How It Works

The while form evaluates its condition field before every execution of the block.
If the condition is `true`, the block executes. Then the condition is evaluated again.
This repeats until the condition becomes `false` or a statement interrupts the flow.

A while form may execute its block zero times — if the condition is `false` from the start, the block never runs.
A while form may also execute indefinitely if the condition never becomes `false` and no statement interrupts it. This is generally undesirable.

---

### Flow — While Form That Stops Naturally
```
evaluate condition ──► true  ──► execute block ──► back to condition
                   │
                   └──► false ──► exit form, continue program
```
```zonetic
mut num: int = 0

while num < 5 {
    num += 1
}
```

The condition `num < 5` becomes `false` after 5 iterations. The form exits naturally.

---

### Flow — Infinite While Form (Undesirable)
```
evaluate condition ──► true  ──► execute block ──► back to condition
       ▲                                                    │
       └────────────────────────────────────────────────────┘
                         never exits
```
```zonetic
mut num: int = 0

while true {
    num += 1
}
```

The condition is always `true`. The block executes forever.
The program never advances past this form. This is an infinite loop with no exit.

---

### Flow — While Form That Stops With Break
```
evaluate condition ──► true  ──► execute block ──► break? ──► YES ──► exit form
                   │                                      │
                   └──► false ──► exit form               └──► NO ──► back to condition
```
```zonetic
mut num: int = 0

while true {
    num += 1

    if num == 5 {
        break
    }
}
```

The condition is always `true`, but `break` exits the form when `num` reaches 5.
For more on `break`, see [`docs/statements/break_stmt_doc.md`](../statements/break_stmt_doc.md).

---

## Infinity Form

The infinity form is **syntactic sugar** for a while form with its condition field permanently set to `true`.
```zonetic
infinity {
    stmts
}
```

Is exactly equivalent to:
```zonetic
while true {
    stmts
}
```

Because the condition is always `true`, the infinity form has no natural exit point.
Flow control inside the block must be managed explicitly — the compiler will not stop it.
A `break` statement or an equivalent flow interrupt is the only way to exit an infinity form.

> The infinity form makes the intent explicit: this loop is meant to run indefinitely,
> and the programmer is responsible for controlling when it stops.