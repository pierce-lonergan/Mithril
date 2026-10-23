# D-ROUTE-2 (development item): group-limited top-k selection

Write the body of `group_topk(sel, n_group, topk_group, k, ids)`. The stub fixes the signature;
keep it.

**Inputs.** `sel` holds E f32 selection values (any values, including NaN, +-inf and -0.0), split
into `n_group` groups of `gs = E / n_group` consecutive experts (1 <= n_group <= 16,
n_group <= E <= 256, E a multiple of n_group). `1 <= topk_group <= n_group`; `k <= E`; `ids` is an
output slice of exactly k u32 values whose initial contents are garbage.

**Order ("a ranks before b"), used for every selection below:**

```text
if a or b is NaN:  a ranks before b  iff  (both NaN and index(a) < index(b))  or  (only b is NaN)
else if value(a) != value(b):  a ranks before b  iff  value(a) > value(b)     (IEEE comparison)
else:  a ranks before b  iff  index(a) < index(b)
```

(-0.0 and +0.0 compare equal; NaN ranks after every number; the index is the position inside the
sequence being ranked: an expert's position within its group, a group's number, or an expert's
number.)

**Meaning (exact).**

```text
eff = sel                                   (conceptually; `sel` itself is read-only)
if n_group > 1:
    for each group g: score_g = v1 + v2, where v1 and v2 are the values of the group's best and
        second-best experts in rank order (one f32 addition, v1 + v2); score_g = v1 if gs == 1
    keep the topk_group best groups, ranking groups by score_g (ties and NaN as in the order above)
    for every expert e in a group that is not kept: eff[e] = +0.0   (it stays eligible)
ids = the indices of the k best experts by eff, best first, in the order above
```

This is the selection step of Hearth's `route_select` (NUMERICS 5.3).

**What is compared.** The k indices, comma separated (the word `empty` when k = 0).
