# D-ROUTE-1 (development item): exact top-k selection

Write the body of `topk(sel, k, ids)`. The stub fixes the signature; keep it.

**Inputs.** `sel` holds n f32 values (1 <= n <= 256; any values, including NaN, +-inf and -0.0);
`k` <= n; `ids` is an output slice of exactly k u32 values whose initial contents are garbage.

**Meaning (exact).** `ids[0..k]` are the indices of the k best entries of `sel`, best first, under
this order ("a ranks before b"):

```text
if a or b is NaN:  a ranks before b  iff  (both NaN and index(a) < index(b))  or  (only b is NaN)
else if value(a) != value(b):  a ranks before b  iff  value(a) > value(b)     (IEEE comparison)
else:  a ranks before b  iff  index(a) < index(b)
```

- So: larger values first; equal values (including -0.0 and +0.0, which compare equal) go to the
  lower index; every NaN ranks after every number, and NaNs among themselves go by index.
- The result is a pure function of `sel` and `k`; there is no randomness and no stable-sort
  ambiguity.

**What is compared.** The k indices, comma separated (the word `empty` when k = 0).
