# D-FMT-1 (development item): routing-trace parser

Write the body of `parse_trace(buf, m, ids)`. The stub fixes the signature; keep it.

**Format** (Hearth FORMAT.md 9, little-endian): a 24-byte header of six u32 fields, `magic`
(0x52545248, the bytes "HRTR"), `version` (1), `n_layers`, `n_experts`, `top_k`, `n_moe_layers`; then,
per token, `n_moe_layers * top_k` expert ids, each a u16.

**Inputs.** `buf` is the file's bytes (any length, any content); `m` holds the model's `n_experts`,
`top_k` and `n_moe_layers`; `ids` is empty on entry.

**Meaning (exact).** Run these checks in this order; the first that fails decides the error:

1. `buf.len() >= 24`, else `Truncated`.
2. magic == 0x52545248, else `BadMagic`.
3. version == 1, else `BadVersion`.
4. the header's `n_experts`, `top_k` and `n_moe_layers` equal the model's, else `Mismatch`.
5. `n_layers >= n_moe_layers`, else `Mismatch`.
6. the record size `n_moe_layers * top_k * 2` (bytes per token) is non-zero and divides
   `buf.len() - 24` exactly, else `Truncated`.
7. every id is `< n_experts`, else `BadId`.

On success return the header (`n_layers`, `n_experts`, `top_k`, `n_moe_layers`, and
`n_tokens = (buf.len() - 24) / record size`), with `ids` holding every id in file order. On an error,
the contents of `ids` do not matter. Never read outside `buf`, never panic or trap, on any input.

**What is compared.** `E:<error name>`, or `H:n_layers,n_experts,top_k,n_moe_layers,n_tokens;`
followed by the ids, comma separated.
