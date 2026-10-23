# D-Q4-2 (development item): dequantise Q4 blocks to f32

Write the body of `q4_dequant(w, y)`. The stub fixes the signature; keep it.

**Inputs.** `w` is a row of nb Q4 weight blocks (nb >= 0); `y` is an output slice of exactly 64 * nb
f32 values (its initial contents are garbage).
- A Q4 weight block holds 64 elements in 34 bytes: a scale `d` (IEEE binary16) and 32 bytes. Byte j
  (0 <= j < 32) holds element j in its low nibble and element j+32 in its high nibble. Each nibble
  stores the element plus 8, so elements lie in -8..=7. The prelude gives an accessor for element i
  and an exact binary16-to-f32 conversion.

**Meaning (exact: the result must be bit-identical).**

```text
for each block g in 0..nb, for each element i in 0..64:
    y[64*g + i] = canon( (element_i(w[g]) as f32) * widen(w[g].d) )
```

- `widen` converts binary16 to f32 exactly; the product is one IEEE f32 multiplication (round to
  nearest-even). `canon` returns the canonical NaN (bits 0x7fc00000) for any NaN and leaves every
  other value unchanged.
- Signs of zero follow IEEE: element 0 times a negative scale is -0.0.

**What is compared.** Every value of `y`, as the 32-bit pattern in 8 lowercase hex digits, comma
separated (the word `empty` when nb = 0).
