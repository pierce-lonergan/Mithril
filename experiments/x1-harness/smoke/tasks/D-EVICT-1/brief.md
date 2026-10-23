# D-EVICT-1 (development item): LRU victim choice

Write the body of `pick_victim(slots, now)`. The stub fixes the signature; keep it. This is a
cache-eviction policy: it only advises, so it must be deterministic and must not read any clock.

**Inputs.** `slots` describes the cache slots (0 to 12 of them here); each has an `id` (u32), `pinned`
(bool), `refs` (u32), `loading` (bool) and `last_use` (a tick, u64). `now` is the current tick.
Every `last_use <= now`.

**Meaning (exact).**

```text
candidates = the slots with !pinned && refs == 0 && !loading
victim     = the candidate with the largest age = now - last_use, INCLUDING age 0;
             among equal ages, the one with the smaller id (the id field, not the position)
no candidate -> no victim
```

The result is a slot id (the Mithril arm returns a hint holding the SlotId; the Rust arm returns
`Some(id)`), or no victim (an empty hint; `None`).

**What is compared.** The victim's id in decimal, or the word `none`.
