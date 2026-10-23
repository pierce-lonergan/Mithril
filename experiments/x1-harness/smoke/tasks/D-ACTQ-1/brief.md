# D-ACTQ-1 (development item): Q8 activation quantisation

Write the body of `act_quantize_q8(x, out)`. The stub fixes the signature; keep it.

**Inputs.** `x` holds 64 * nb finite f32 values (nb >= 0); `out` holds exactly nb Q8 activation blocks
whose initial contents are garbage. Block b quantises `x[64*b .. 64*b + 64]`.
A Q8 activation block holds a scale `d` (f32), `sum` (i32) and 64 values `q` (i8).

**Meaning (exact: the result must be bit-identical).** For each block b:

```text
amax = +0.0; for each of the 64 values v: if |v| > amax { amax = |v| }
d    = amax / 127.0                         (one f32 division)
id   = if d != 0.0 { 1.0 / d } else { 0.0 } (one f32 division)
q_i  = round_half_to_even(x_i * id), converted to i8 as Rust's `as i8` does
       (saturating to -128..=127; NaN converts to 0)
sum  = q_0 + q_1 + ... + q_63               (exact, i32)
out[b] = { d, sum, q }
```

- Every operation is one IEEE f32 operation rounded to nearest-even; nothing is fused.
- `x_i * id` exactly halfway between two integers rounds to the even one (2.5 -> 2, -3.5 -> -4).
- A block of zeros gives d = 0.0, id = 0.0, q all 0, sum 0.

**What is compared.** For each block: the bits of `d` (8 lowercase hex digits), `sum`, and the 64
values of `q`, as `d:sum:q0,q1,...,q63`; blocks are separated by `;` (the word `empty` when nb = 0).
