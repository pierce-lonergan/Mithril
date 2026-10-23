# D-NORM-1 (development item): RMSNorm with the canonical 16-lane sum

Write the body of `rmsnorm(y, x, w, eps)`. The stub fixes the signature; keep it.

**Inputs.** `x` and `w` hold n >= 1 finite f32 values; `y` is an output slice of n f32 values whose
initial contents are garbage; `eps` is a finite f32 >= 0.

**Meaning (exact: the result must be bit-identical).**

```text
ms  = sum16(x_0*x_0, x_1*x_1, ..., x_{n-1}*x_{n-1}) / (n as f32)
r   = 1.0 / sqrt(ms + eps)
y_i = canon( (x_i * r) * w_i )            for i in 0..n
```

- `sum16` is the canonical 16-lane sum: 16 lanes start at +0.0; value i is added to lane i mod 16 in
  index order; then lane j += lane j+8 (j < 8), lane j += lane j+4 (j < 4), lane j += lane j+2
  (j < 2), lane 0 += lane 1; the result is lane 0. Each square is rounded before it is added. The
  helper `dot16(a, b)` computes exactly sum16(a_0*b_0, ..., a_{n-1}*b_{n-1}); `sum16(v)` sums a slice.
- `sqrt` is the IEEE square root; every operation is one IEEE f32 operation rounded to
  nearest-even; nothing is fused; the parenthesisation above is the evaluation order.
- `canon` returns the canonical NaN (bits 0x7fc00000) for any NaN and leaves other values unchanged.
- A square may overflow to +inf; then r = 0.0 and the outputs are signed zeros (or NaN, canonical).

**What is compared.** Every value of `y`, as 8 lowercase hex digits of its bits, comma separated.
