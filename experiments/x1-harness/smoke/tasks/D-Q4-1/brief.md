# D-Q4-1 (development item): Q4 weight row times Q8 activation

Write the body of `q4_row_dot(w, a) -> f32`. The stub fixes the signature; keep it.

**Inputs.** `w` is a row of nb Q4 weight blocks and `a` a row of nb Q8 activation blocks, with the same
nb (nb >= 0).
- A Q4 weight block holds 64 elements in 34 bytes: a scale `d` (IEEE binary16) and 32 bytes. Byte j
  (0 <= j < 32) holds element j in its low nibble and element j+32 in its high nibble. Each nibble
  stores the element plus 8, so elements lie in -8..=7. The prelude gives an accessor for element i
  and an exact binary16-to-f32 conversion.
- A Q8 activation block holds a scale `d` (f32), `sum` (i32; not needed here) and 64 values `q` (i8).

**Meaning (exact: the result must be bit-identical).**

```text
acc = +0.0                                   (f32)
for each block g, in order 0, 1, ..., nb-1:
    isum = sum over j in 0..64 of element_j(w[g]) * a[g].q[j]      (exact integer arithmetic)
    acc  = acc + (isum as f32) * (widen(w[g].d) * a[g].d)
return acc, except that a NaN result is returned as the canonical NaN (bits 0x7fc00000)
```

- `widen` converts binary16 to f32 exactly. The product in parentheses is computed first. Every
  operation is one IEEE f32 operation rounded to nearest-even; nothing is fused (no FMA) and nothing
  is reordered.
- nb = 0 returns +0.0. `acc` starts at +0.0, so a first term of -0.0 leaves +0.0.

**What is compared.** The 32-bit pattern of the result, printed as 8 lowercase hex digits.
