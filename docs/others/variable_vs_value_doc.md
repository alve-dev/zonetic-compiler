# Variable vs Value

## The Difference

In Zonetic, not everything you declare behaves the same way.
When you declare something with `mut`, you get a **variable**.
When you declare something with `inmut`, you get a **value**.

They look similar on the surface, but they have different rules about what you can do with them.

---

## Variable — `mut`

A variable can change. After its first assignment, you can reassign it as many times as you need.
```zonetic
mut score: int = 0
score = 10
score = 25
```

This is valid. `score` is a variable — it is allowed to change.

### Methods

A variable has access to both **read methods** and **write methods**.
- Read methods observe the value without changing it.
- Write methods modify the value in place.

> Method examples will be added in a future revision when the method system is complete.

---

## Value — `inmut`

A value cannot change. Once assigned, it stays that way for its entire lifetime in the scope.
Any attempt to reassign it is a semantic error.
```zonetic
inmut name: string = "Zonetic"
name = "Other"      -- ❌ error, name is a value and cannot be reassigned
```

### Methods

A value only has access to **read methods**.
Write methods are blocked entirely — this is what makes `inmut` deeply immutable.

Immutability in Zonetic is **deep** — not just the variable itself, but everything it holds
is protected from modification through that binding.

> Method examples will be added in a future revision when the method system is complete.

---

## Why Does This Distinction Matter?

Knowing whether something can change makes your code easier to reason about.

When you see `inmut`, you know that value will never be different from what it was assigned.
You do not need to track where it might have changed — it simply cannot.

When you see `mut`, you know that value might change — and you know it is intentional,
because the programmer explicitly asked for a variable.

This explicitness is a core part of Zonetic's design.
Mutability is never implicit — you always declare it up front.