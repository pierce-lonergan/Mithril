# 02 — The compute layer: exact meanings, checked realisations, measured bytes

**Summary.** Mithril writes every performance-critical computation once, as an *exact meaning*: an
executable `kernel fn` or `flow` whose floating-point order is fixed by the canonical numeric
contract `canon.v1` (Hearth's NUMERICS.md made normative). Everything that makes the computation
fast is a separate, separately checked *realisation*: a **schedule** (which may move work but never
change the op-DAG), a **layout** (which may move bytes but never change values), a **policy** (which
may only emit hints the store core validates) or a **placement** (which may move work between tiers
and devices only where the result is cross-device bit-identical). Each kind of realisation is a
certified space: correctness is established once for the space, so agents and the Forge search it
with performance evidence alone. The compiler derives a **cost signature** for each realisation —
bytes per memory tier, operations per class, synchronisations — as unit- and origin-typed
quantities, evaluates it against a measured machine profile, and reports every result as a fraction
of a physics floor. The honest picture for Hearth is that decode is bound by bytes, not
instructions: the lossless Qwen3-30B-A3B ceiling is about 34 tok/s at 77 GB/s measured DRAM, Hearth
measures 19–22 tok/s, and the CPU headroom is about 1.5x. The largest lossless lever is the
owner-gated GPU expert tier, which this layer makes output-invariant through validated PTX kernels
plus a `tested` SASS level (DR-022).
Speed comes from bytes, placement and scheduling, not from syntax.

**Contents**
1. Position in the stack and the central rule
2. Meanings (`kernel fn`)
3. `par for`
4. Projections and iteration in hot loops
5. The canon library
6. Transcendentals
7. Formats, layouts and integer views (MXFP4 native)
8. Schedules
9. Batched prefill under canon
10. Block sparsity
11. Chunkwise recurrent scans (KDA) under canon
12. Flows and policies (timing_only, hint ports, the store-core certificate, one policy code)
13. Cost signatures and the roofline, with honest Hearth ceilings
14. Tiers and placement
15. The GPU expert tier and cross-device determinism (DR-022)
16. The reserved approx/cache effect
17. The visual-generation boundary (DR-024)
18. Meanings and Hearth's numpy reference: the independent intent oracle
19. Status summary
20. Open questions and reviewer notes

**Conventions.** All syntax is provisional pending the Surface Lab ([05-agent-protocol.md](05-agent-protocol.md));
snippets obey the subset rule of DR-002 ([01-language.md](01-language.md)). Status labels map to
milestones exactly as in [../ROADMAP.md](../ROADMAP.md) §1 rule 7:
- **v0**: in the mithc that ports Hearth (M1–M5);
- **v1**: present by Edition 1 (M6–M7);
- **later**: planned after M7;
- **reserved**: in the types and schema but not producible;
- **by-trigger**: added only when its register trigger fires (deferral register, ROADMAP §9).

Where known, the delivering milestone is given, as in "v0 (M2)". Numbers are labelled measured,
SIMULATED, [inference] or [target]. Citations: dossiers [R08], [G03]; revisit-archive nodes [RV: D2-A]; proposals [P3 §3.2];
[judges] = the design panel's evaluations of the proposals.

---

## 1. Position in the stack and the central rule

The compute layer spans L3–L6 of the stack ([../ARCHITECTURE.md](../ARCHITECTURE.md)). Its IRs are
**KIR** (per-output FP op-DAG, `Order` nodes, exact-integer subterms with ranges, layouts, schedule
application) and the flow fragment of MIR (tiers, residency, async I/O, hint ports, placements; P3's
"FIR"). C11 lowering and the object audit are in [04-toolchain.md](04-toolchain.md); T0–T3 and the
semantics table in [03-trust.md](03-trust.md).

**The central rule.** *A realisation may change where, when and in which layout an operation runs.
It may never change which IEEE operation runs on which operands in which order* [P3 §1, R05, R07].
Integer subterms are the exception that buys speed: an integer sum with a proved overflow bound is
associative, so any order of evaluation (VNNI, dp4a; INT8 tensor cores once their exact accumulation
is confirmed [G03]) yields the same bits.

```text
                       exact meaning: kernel fn / flow  (canon.v1 orders, formats, ranges)
                                       |  KIR: per-output FP-DAG + Order + exact_i32(range)
      +-------------------+------------+--------+--------------------+--------------------+
      | schedule          | relayout            | policy             | placement          |
      | DAG-preserving    | value-preserving    | timing_only hints  | cross_device only  |
      +---------+---------+----------+----------+---------+----------+---------+----------+
                |                    |                    |                    |
     T1 on the emitted code   round-trip proof     T0 binary confinement   placement checker
     + T2 side conditions     per instance (T2)    + store-core cert O1-O5 + cross-device corpus
                |                    |                    |                    |
                +-------- member of a certified space: promote on performance evidence -------+
                                                   |
                cost signature -> floor (phys / emp) -> measured fraction of roof -> ledger
```

For every space, **soundness** (anything the check accepts preserves outputs) is trusted and is
established per build on the binary, while **completeness-for-members** (every legitimate member
passes, so agents do not see spurious rejections) is untrusted and only tested [P2 §5.3]. A
checker "unknown" is a rejection. Promotion of a space member follows the Gödel–Darwin rule in
[03-trust.md](03-trust.md) and [06-forge.md](06-forge.md).

---

## 2. Meanings (`kernel fn`)

A **meaning** is the specification and an executable program at the same time. `mithi`, the
independent Rust interpreter, runs it as written (DR-010); it is the differential oracle for every
realisation and the comptime evaluator. A `kernel fn` is graded `exact` by default, with
determinism scope `cross_device`, under the project's pinned canonical contract (`canon.v1`).

```mith
/// NUMERICS §3, one Q4 row times one Q8 activation. Exact grade is the default.
kernel fn q4_row_dot(w: &[BlockQ4], a: &[ActQ8]) -> f32
    requires w.len() == a.len()
{
    let mut acc: f32 = 0.0;
    for g in 0..w.len() {
        let mut isum: i32 = 0;      // exact integer sum: may be reordered (T2 range proof)
        for j in 0..32 {
            isum += w[g].q.elem(j) * (a[g].q[j] as i32);
            isum += w[g].q.elem(j + 32) * (a[g].q[j + 32] as i32);
        }
        // |isum| <= 64 * 8 * 127 = 65_024 < 2^24, so the cast is exact (T2 obligation)
        acc = acc + (isum as f32) * (w[g].d.to_f32() * a[g].d);   // fixed order, no contraction
    }
    canon::nan(acc)                 // canonical quiet NaN 0x7fc00000
}

kernel fn q4_matvec(w: &Matrix<BlockQ4>, a: &[ActQ8], y: &mut [f32])
    requires y.len() == w.rows() && a.len() == w.blocks_per_row()
{
    par for r in 0..w.rows() {      // disjoint writes: each y[r] written by exactly one iteration
        y[r] = q4_row_dot(w.row(r), a);   // w.row(r) is a projection, not a stored borrow
    }
}
```

This is the canonical form of [../ARCHITECTURE.md](../ARCHITECTURE.md) §5.3. The second conjunct of
`q4_matvec`'s `requires`, together with `Matrix::row` ensuring `result.len() == self.blocks_per_row()`
([01-language.md](01-language.md) §5.3), discharges `q4_row_dot`'s `requires w.len() == a.len()`
statically. Without it the call would be an unprovable refinement in kernel code, which is a
compile error (DR-011).

**Rules inside `kernel` code** (status **v0**, M1 checker and M2 KIR; each is a type or T0 rule, not
a lint):

- *Strict IEEE binary32.* `+ - * /` and `sqrt` round to nearest even; `a * b + c` is two roundings
  (the Rust meaning); the only fused form is an explicit `a.mul_add(b, c)`, which `canon.v1` never
  uses [P1 §3, FF-FMA]. No reassociation, no FTZ/DAZ. The `fp_env` effect is not available in
  kernels. Kernel code can run on the caller's thread [R11 §3], so every `export abi` and `hx_*`
  entry **sets** the default MXCSR on entry and restores the caller's value on exit, and pool
  workers set and assert it at start. Every T1 certificate records "default MXCSR" as a
  precondition checked at entry: a runtime-checked trust-base entry, not an axiom and not a
  discharged obligation ([../ARCHITECTURE.md](../ARCHITECTURE.md) §6.3,
  [04-toolchain.md](04-toolchain.md) §9.2, [03-trust.md](03-trust.md) §3.4). This closes a live
  Hearth gap (MXCSR is never asserted today) [P2 §3.6, G02].
- *Reductions are named.* Bare float `.sum()`, `fold`, `max_by`, `min_by_key` on floats are
  rejected in exact-graded code and on the logits path (DR-013). The Safe fix is
  `canon::sum_seq`, Rust's sequential left fold including the pinned Rust reference's start value
  (§5), so the bits are the same; the MeaningChanging fix is `canon::sum16`. NUMERICS-style
  sequential accumulation from `+0.0f` is written as an explicit loop, as in `q4_row_dot` above
  ([01-language.md](01-language.md) R4). Integer `.sum()` over values with proved ranges is allowed,
  because it is exact in any order.
- *Transcendentals are named* (`cr::` or `canon_v1::`, DR-014; §6).
- *Refinements must be proved.* An unprovable `#[range]`, `requires` or index bound inside a
  `kernel` is a compile error, never a silent runtime trap (DR-011). Kernels are therefore
  trap-free by construction, which matters for vectorisation: a trap in a memory-bound inner loop
  can defeat MSVC's vectoriser [P2 §3.3; judges].
- *NaN is canonical at sinks.* Every kernel output passes through `canon::nan`: IEEE does not fix
  which NaN operand propagates and compilers commute SIMD operands (NUMERICS §3).
- *No ambient authority.* Kernels hold no capabilities beyond caller-provided buffers.

KIR holds, per output element, the FP expression DAG, the `Order` objects that fix association (§5)
and every exact-integer subterm with its interval bound. It is the object T1 compares emitted code
against ([03-trust.md](03-trust.md)); schedules are KIR→KIR rewrites that emit a correspondence map.
In v0, elaborating meanings into KIR (comptime included) is a trusted code component with code floor
`tested`, mitigated by the second comptime evaluation path in `mithi`. An independent kernel-subset
extractor inside `mithcheck`, which would take elaboration out of the TCB, is a by-trigger upgrade
([03-trust.md](03-trust.md) §3.4 and §14).

---

## 3. `par for`

`par for i in range { body }` has **sequential meaning and parallel realisation** (status **v0**).
Its value is defined as executing the iterations in increasing index order; the compiler may run
them in any order on any number of threads because T0 proves that no two iterations conflict:

1. *Disjoint writes.* Every location written in the body is written by exactly one iteration
   (`y[r]` is indexed by the loop variable through an injective index expression, or by a
   projection of a disjoint chunk).
2. *No read of another iteration's writes.* Reads of shared inputs are allowed; reads of a
   location another iteration writes are rejected.
3. *No cross-iteration float accumulation.* A reduction across iterations must be a named canon
   reduction (`canon::sum16` over a materialised array) or an exact integer accumulator with a
   proved bound. There is no `reduction(+: acc)` clause, because a parallel float sum would make
   the result depend on the thread count.

Dynamic chunk claiming stays value-deterministic because disjointness makes the assignment of
iterations to threads unobservable. The persistent pool ported from `pool.c` costs about 0.75 µs per
16-thread round trip and 7.5 µs at 32 threads (measured under load), so small regions stay on the
caller [R11]. Decode threads must span both CCDs to exceed the 64 GB/s per-CCD cap [R08]; barriers
enter the cost signature as `syncs` (§13).

**Deterministic failure.** Kernels cannot fail (§2), so this matters for non-kernel `par for`
(parsing slabs, verifying content hashes). If several iterations fail, the result is the error of
the **lowest failing index**, independent of thread count. The realisation: workers claim chunks
in increasing order and publish `min_fail = min(min_fail, i)`; chunks starting above `min_fail` are
skipped; at the join every chunk below `min_fail` has completed, so the reported error is fixed.
The contents of output regions after a failed `par for` are unspecified and must be re-initialised
before use. The general trap semantics are in [01-language.md](01-language.md) §12: a trap ends its
fail domain; it never unwinds and never aborts the host.

---

## 4. Projections and iteration in hot loops

References are second-class (DR-004), yet hot loops need zero-copy rows, blocks and slices, and
agents constantly write `w.row(r)`, `&x[64 * b..64 * b + 64]` and reference-capturing closures. Two
mechanisms close the gap; their typing is in [01-language.md](01-language.md), and this section
states what they must compile to.

- **Projections** (Hylo-style subscripts) are the one way a borrow leaves a call: `w.row(r)`,
  `w[g]`, slicing. The borrow is scoped to the caller's enclosing expression or statement and
  cannot be stored [P3 §3.1].
- **The non-escaping kind** covers closures and iterator adapters that capture references
  (`|w| expert_ffn(cfg, w, x)` in §12, `q.iter().map(|v| *v as i32)`), so ordinary Rust idioms type
  without lifetimes.

**Lowering contract for hot loops** (status **v0 (M2)**, with the port-wide hidden-copy gate at M5;
enforced by the C11 lowering rules in [04-toolchain.md](04-toolchain.md)):

| Construct | Must lower to | Checked by |
|---|---|---|
| `w.row(r)` on `Matrix<BlockQ4>` | base pointer + `r * row_bytes`; no copy, no allocation | no-hidden-memcpy check |
| `w[g]`, `&x[a..b]` with proved bounds | pointer arithmetic, no bounds check | refinement facts (T2); unprovable in kernels → error |
| two projections from disjoint `&mut` chunks | C `restrict` pointers | alias facts (DR-027) |
| non-escaping iterator chain over an exact integer domain | a counted loop | MIR inspection |
| MVS value results (`[f32; R]`, structs) | out-parameters, in place | no memcpy above N bytes on hot paths (DR-027) |

The `restrict` row is needed for parity with hand-written C, not for the attention speed-up:
Hearth's portable value pass is already `restrict`-annotated and runs at 18.0 GMAC/s. The
bit-identical 94 GMAC/s prototype (measured) differs by register blocking, which is a
DAG-preserving, T1-validated schedule (§8), not an aliasing fact [R11 §3;
[04-toolchain.md](04-toolchain.md) §6.4; DEC reviewer note 1].

---

## 5. The canon library

`canon.v1` is the normative, machine-readable form of Hearth's NUMERICS.md, plus the transcendental
choices of Hearth's ADR-0010 once it lands (DR-014). Its members are ordinary Mithril meanings in a
sealed, Author-owned module, versioned as one contract (status **v0 (M2)**).

| Member | Definition (canon.v1) | Source |
|---|---|---|
| `canon::sum16(a)` | 16 lane accumulators from +0.0; `L[i & 15] = L[i & 15] + a[i]`; then tree s = 8, 4, 2, 1 | NUMERICS §1 |
| `canon::dot16(w, x)` | `sum16` of `w[i] * x[i]`, each product rounded to f32 then added, never fused | NUMERICS §1 |
| `canon::sum_seq(a)` | left fold with the pinned Rust reference's start value (−0.0 for an empty float sum per [RV: D3-i], inference), i.e. Rust's `Iterator::sum` meaning; NUMERICS-style accumulation from `+0.0f` is written as an explicit loop | DR-013; [01](01-language.md) R4 |
| `canon::nan(v)` | NaN → 0x7fc00000, otherwise identity | NUMERICS §3 |
| `canon::act_q8(x)` | per 64-block: exact amax; `d = amax / 127`; `id = 1 / d` (0 when d is 0); `q = rne(x * id)`; exact int32 `sum` | NUMERICS §2; quant.c |
| `canon::matvec_q` | per row: exact int32 block sums, then `acc = acc + (isum as f32) * (dw * dx)` in block order | NUMERICS §3 |
| batched `Y = W X` | every (token, row) equals the single-token value | NUMERICS §3, INV-DET-2 |
| `canon::rmsnorm`, `softmax`, `silu`, `sigmoid`, `rope` | NUMERICS §4 formulas, with named transcendentals (§6) | NUMERICS §4 |
| `canon::combine_rank(ids, outs, scale)` | MoE combine in routing rank order, whatever finished first | NUMERICS §5.3 |
| `canon::topk(sel, k)` | descending, ties → lower index, NaN rule explicit | NUMERICS §5.3; FF-TIES/FF-NAN in [01](01-language.md) |
| attention value pass | `o[d] = Σ_t p_t * v_t[d]`, sequential in t from +0.0 | NUMERICS §5.1–5.2 |

Note on `canon::act_q8`: NUMERICS §2 states the rule for finite inputs. The C quantiser also
defines the degenerate cases in code (NaN products become 0; values are clamped to ±127 before
rounding; `quant.c`, `act_q8_scalar`). The meaning must transcribe the code's behaviour, branches
included, and the cross-binary hash corpus must contain NaN/Inf activations [P3 §9 Stage 0]. This
is a small instance of the intent gap discussed in §18.

**Order objects.** Association is a value, versioned with the contract [G03 Implications 3]:

```text
lanes(16).tree([8, 4, 2, 1])     sum16 / dot16 (one zmm, two ymm, or a half-warp)
blocks(64, exact_i32).then(seq)  Q8/Q4 rows: exact block sums, then a sequential float chain
seq                              canon.v1 attention value pass over t
chunks(c, seq).then(seq)         reserved: fixed-chunk forms for attention and KDA (sections 11, 15)
```

**Versioning.** `canon::` names resolve through the contract pinned in `mith.lock`; any change of
bits is a new version, classified by the canon migration protocol ([03-trust.md](03-trust.md) §12).
*Additive* changes add an order or function without touching an existing op-DAG and are a minor
version, `canon.v1.1` (**later**): expected are the MXFP4 sub-block order of §7.3 and, if adopted, a
KDA order (§11), both for meanings that do not exist yet. *Redefining* changes alter an existing
op-DAG and are a major version, `canon.v2` (**by-trigger**), with meaning hashes changed and
bit-exact goldens reset: the fixed-chunk attention order (§15.4), which redefines the CPU's existing
attention order too, or explicit FMA (on a measured speed-up worth a full golden reset [G03 F8]).
Whichever redefinition comes first takes `canon.v2`, and that is the first use of the
major-version migration protocol. Hearth's own goldens are relational, so a consistent
change needs an ADR and updated C references but no Hearth golden re-lock [G04 F8]; the expensive
items are Mithril's bit-exact goldens and the cross-binary hash corpus, which a major version
regenerates, and that is why ADR-0010 lands before that corpus exists [G04 F8].

---

## 6. Transcendentals

The platform C runtime is not a fixed function even on one OS: UCRT selects FMA3 or non-FMA3
transcendental paths at startup, and over all 2^32 inputs the two paths disagree on 1 `expf`,
44,232 `sinf` and 18,018 `cosf` inputs (measured on the 9950X); for a Qwen3-30B-A3B-shaped RoPE
table that changes cos values at 17 of the first 40,960 positions [G04 F3]. Letting MSVC vectorise
libm calls under `/fp:fast` changes 51% of `expf` results on [−10, 10] (measured) [G04 F5.1]. Rust
itself documents `f32::exp` as having platform-dependent precision [G04 F6]. Hence (DR-014, status
**v0 (M2)**):

- **No implicit default in exact code.** Every call names `cr::expf` (correctly rounded, round to
  nearest even) or `canon_v1::expf` (a fixed op-DAG of IEEE basic operations without FMA).
  `x.exp()` in exact code is rejected with a named diagnostic whose fixes are the two names.
  Outside exact code, `x.exp()` means `cr::expf`, which is one of the implementations Rust's
  meaning already permits, so it is not a false friend.
- **Platform libm only through `foreign` with `nondet(platform)`**, which the exact grade rejects.
  A `parity::` shim calling the same CRT symbols exists only for migration comparisons against
  legacy C [G04 Implications 3].

**Why both kinds exist.** `cr` has a meaning independent of any implementation, so any correct
implementation on any ISA, OS or GPU gives the same bits. Scalar correct rounding is cheap (LLVM
libc's `expf` costs 9 cycles reciprocal throughput against glibc's 7 on a Ryzen 1700 [G04 F4]), but
vectorised correct rounding is immature [G04 F5.2]. `canon_v1::expf` vectorises exactly by
construction: a no-FMA prototype gave **0 mismatches across scalar, AVX2 and AVX-512 over all 2^32
inputs**, was 99.19% correctly rounded (maximum error 1 ulp), and ran at **0.204 ns/element on
AVX-512 against 1.12 ns for scalar UCRT `expf`** (measured) [G04 F5.3].

**Evidence.** A `canon_v1::` function is a DAG of basic operations, so T1 checks its vectorised
realisations structurally, as for `dot16`. A `cr::` binary32 univariate function is validated
exhaustively per target against an independent correctly rounded implementation (G04's probe of
three functions, two CRT paths and a binary64 reference took about 22 s on 32 threads). A vector
`cr` uses a fast path, a rounding test and a scalar fallback for undecided lanes, expressed as
masked lanes with a scalar escape; timing is data-dependent, the result is not [G04].

**Expected choice for Hearth** (ADR-0010, in C Hearth first): `cr::sinf`/`cr::cosf` for RoPE (128
calls per token) and `canon_v1::expf` for softmax, SiLU and sigmoid, which need vector speed
[judges, G04]. Transcendentals are about 0.2% of decode CPU time at 512 context, 1% at 4,096, about
8% at 32,768 and about 3% of a 2,048-token prefill; after a 5x attention speed-up, scalar `expf` could
reach 15–20% of long-context attention time [G04 F7, inference]. GPU transcendentals: §15.

---

## 7. Formats, layouts and integer views

### 7.1 `format` types

A block-scaled quantisation format is declared once; pack/unpack, size checks, the dequantised
value, the round-trip property and the integer view are derived (status **v0 (M2)** for Hearth's Q4,
Q8, F16, BF16, F32; the container parser derived from `format` descriptions is port Stage S2,
**v0 (M3)**).

```mith
/// Hearth Q4 weight block (FORMAT.md, hx_quant.h): 64 elements in 34 bytes.
format BlockQ4 {
    d: f16,                          // block scale
    q: nibbles<64, offset = 8>,      // byte j: low nibble = elem j, high nibble = elem j+32
}
// Derived by the compiler: size == 34 (checked), elem(i) -> i32 with #[range(-8..=7)],
// pack/unpack, and the integer view used by exact dot products.
```

Sub-byte and microscaling codes (nibbles, `e2m1`, `e8m0`) are **storage codes valid only inside
`format`**. They are not arithmetic types. Real kernels lower them through int8 dot products or
in-register lookup tables, not "int4 primitives lowered via popcount" (a seed claim the research
rejected) [R05, P5 §3.3]. `f16` and `bf16` are storage types; arithmetic requires an exact
widening to f32. The Q4 format is a false friend for anyone who knows llama.cpp: Q4_0 has 32
elements with the high nibble at j+16, Hearth Q4 has 64 with the high nibble at j+32, and the
difference is reachable only through the `format` type [P1 §3, FF-Q4].

### 7.2 Integer views and overflow licences

An **integer view** maps each element code to a small integer with a declared range. From it the
compiler derives an exact-integer dot meaning against `ActQ8` blocks and the T2 obligations that
license reordering. The bounds Hearth's kernels rely on, each a sub-second bit-vector query [R07]:

| Obligation | Bound | Licenses |
|---|---|---|
| Q4 block sum | \|isum\| ≤ 64·8·127 = 65,024 < 2^24 | any summation order; exact `isum as f32` |
| Q8 block sum | \|isum\| ≤ 64·127·127 = 1,032,256 < 2^24 | same |
| AVX2 `vpmaddubsw` int16 pair | 2·15·127 = 3,810 (7,620 for low plus high) [R07] | int16 intermediates without saturation |
| Q8 sign trick | 32,512 < 32,767 [R07] | the unsigned-times-signed rewrite |
| VNNI bias correction | Σ(u−8)·x = Σu·x − 8·Σx over Z, using `ActQ8.sum` | `vpdpbusd` on unsigned stored nibbles |
| MXFP4 sub-block (§7.3) | \|isum\| ≤ 32·12·127 = 48,768 < 2^24 | exact integer path for E2M1 × int8 |

### 7.3 MXFP4, native (status **later**)

The `format` mechanism this section uses is v0 (M2); MXFP4 itself is later because its dot order
needs `canon.v1.1` (later, §5). MXFP4 is the native, quantisation-aware-trained expert format of gpt-oss and Kimi K3: E2M1
elements in blocks of 32 with one E8M0 power-of-two scale, 4.25 bits per weight — the same as
Hearth Q4 — so running it natively is lossless and fits INV-LOSSLESS-DEFAULT [R06 F1]. One Kimi K3
expert is exactly 17,547,264 bytes in MXFP4 [R06].

```mith
/// OCP MX v1.0 MXFP4: 32 E2M1 elements sharing one E8M0 power-of-two scale (17 bytes).
format BlockMxfp4 {
    e: e8m0,                          // shared scale 2^(e - 127); special encodings per the spec
    q: e2m1x2<32>,                    // two E2M1 codes per byte; nibble order per source checkpoint
}
// Derived: size == 17 (checked); integer_view(i) = 2 * value(i) -> i32 with #[range(-12..=12)],
// taking only {0, ±1, ±2, ±3, ±4, ±6, ±8, ±12}; exact dot meaning against ActQ8 sub-blocks.
```

With a power-of-two scale, an MXFP4 × Q8 block dot is an exact int32 sum times a power-of-two
factor, as long as no overflow or underflow occurs [G03 F8, R06]. Two decisions remain: (a) **the
order** — scale blocks are 32 elements and activation blocks 64, so `canon.v1.1` must fix the
epilogue, e.g. two sub-block terms added in order, `acc = acc + isum_a * (sa * dx); acc = acc +
isum_b * (sb * dx)` [P3 §9 item 5], before the first MXFP4 golden; (b) **range side conditions** —
folding a power-of-two scale by exponent arithmetic is exact only in the normal range, a T2
condition on the rewrite. Native block-scaled FP4 MMA cannot be canonical: OCP MX leaves the
dot-product order implementation-defined [G03 F5]. Gate [P3 M2]: round trip exact against
checkpoint bytes, integer path derived with no hand-written kernel. NVFP4 is **later** [R06].

### 7.4 Layout/tile algebra and lossless relayouts

A **layout** is a map from logical indices to storage order with provable bounds and contiguity
(status **v0** where the port needs it: the relayout space at M2, prefill tiles at M5; **v1**
otherwise, including the Forge's relayout search at M6). It serves GEMM register blocking, row-interleaved repacks (ik_llama's R4/R8),
expert-major prefill tiles, KV paging and — outside v1 — spatio-temporal video tiles [R13, R06]. A
**relayout** is a certified space [P2 §5.3]: weights repacked into a kernel-native layout with
identical values; derived pack/unpack are inverses (proved once) and each instance passes a
round-trip check (T2, or exhaustive per block). Two expected uses: row-interleaved CPU repacks for
prefill, and **scales separated from the 34-byte Q4 blocks** for the GPU tier, because unaligned
34-byte blocks hurt coalescing [judges]. The meaning is untouched.

**Relayouts and the lossless-tier obligation.** A relayouted copy's bytes differ from the slab, so
O4's content-hash check (§12.4) is defined on the **canonical, on-disk layout**: a slab is verified
against its per-slab hash *before* relayout, and the relayouted copy (in VRAM, or a CPU repack) is
keyed by (slab hash, relayout id). Its integrity rests on the relayout space's certificate (pack and
unpack proved inverse) plus a per-instance check recorded at first fill — either a round trip back to
the canonical bytes or a hash of the relayout output — and later fills of the same key are checked
against that recorded hash.

---

## 8. Schedules

### 8.1 The primitive set

A `schedule` binds a meaning to a target and applies only **DAG-preserving** primitives (status
**v0 (M2)**: first as the X2/X3 spike over transliterated intrinsics at M0, then as KIR rewrites at
M2). The rewrite library borrows Exo's model (MIT) with the value domain changed from reals
to IEEE operations over a fixed DAG; Exo itself treats floats as reals and would accept a
reassociated reduction [R05 F2].

| Primitive | Licence | Why the result is bit-identical |
|---|---|---|
| `tile r by n`, loop split, interchange keeping each output's order | `exact` | per-output DAG unchanged |
| `vectorize` with lanes = independent outputs (rows, tokens) | `exact` | lanes never interact |
| `vectorize` with lanes = the 16 canonical lanes of `dot16` | `exact` | lane count is part of the meaning |
| integer-sum lowering (`vpdpbusd`, `vpmaddubsw`, dp4a) | `int_assoc` | exact integer sum; T2 proves no wrap or saturation |
| hoist exact conversions (f16/bf16→f32, small int→f32) | `exact` | conversion is exact (table fact or T2 range) |
| commute one IEEE add or mul | `exact` with side condition | exact only if no order-sensitive consumer (e.g. MAXPS/MINPS) sits before NaN canonicalisation |
| `prefetch w ahead n` | timing only | no value effect |
| `parallel` over disjoint output tiles | `exact` | disjointness inherited from `par for` |
| `keep_order acc` | `exact` | asserts the float chain is untouched |
| relayout of operands | relayout space (§7.4) | values identical by round-trip proof |

The canonical AVX-512 schedule for the Q4 matvec:

```mith
/// A schedule may only apply DAG-preserving primitives. T1 validates the emitted object code.
schedule q4_matvec_avx512 for q4_matvec on x86_64(avx512f, avx512bw, avx512vnni) {
    tile r by 16;                   // 16 rows per pass
    vectorize j using vpdpbusd;     // integer block sums via VNNI: licensed by the exact-i32 range proof
    keep_order acc;                 // the float epilogue order comes from the meaning
    prefetch w ahead 2 blocks;
}
```

`vectorize j using vpdpbusd` multiplies *unsigned* stored nibbles (q + 8) by signed activations, so
the lowering includes the bias identity of §7.2 and reads the precomputed `ActQ8.sum`; T2 proves the
identity and the ranges. This mirrors Hearth's hand-written `quant_avx512.c` ("VNNI vpdpbusd on
unsigned weights, corrected by bias*sum(x)", "SIMD lanes = independent rows", "never FMA"). An AVX2
sibling uses `vpmaddubsw` under the 3,810 bound, and a portable schedule is the scalar and arm64
CI path. One meaning plus three schedules replaces Hearth's scalar/AVX2/AVX-512 triplets, whose two
SIMD files total 726 lines [P5 §3.2, R05].

### 8.2 What is rejected

Splitting a float accumulator into several partial sums ("split-accumulator"), FMA contraction,
changing the lane count or tree of a canonical reduction, and splitting K across threads for a
float chain are all reassociations. They are not in the `exact` licence set and are rejected with a
diagnostic that names the rule and the false friend ("C compilers do this under `-ffast-math`;
Mithril never does in exact code") [P3 §7]. They become admissible only under `real(bound)` with a
T3 certificate, which is **reserved**.

### 8.3 Correspondence maps and where T1 checks

T1 validates the output, not each rewrite [P5 §4]: the schedule supplies a **correspondence map**
(lane, register-to-value and loop correspondence) and T1 matches the emitted FP-DAG against KIR
modulo an audited list of IEEE-exact rewrites; T2 discharges integer side conditions. Hand-written
intrinsics with a `#[lanes(...)]` annotation are checked the same way, so value arrives before the
schedule language exists. DR-008 fixes the order: instruction census of what MSVC, Clang and GCC
emit (including `_mm512_reduce_add_ps`, shuffles, unrolling, rotation, spills), then the X2 spike,
then the object audit of the ~20 hot kernels. **A variant that fails to lift or match drops to
`tested` and is not dispatched in release profiles** (DR-008, DR-021). Matcher, loop rule and
semantics table: [03-trust.md](03-trust.md), [04-toolchain.md](04-toolchain.md).

### 8.4 Targets, lanes and vector width

ISA tiers are data, not syntax: portable, `x86_64(avx2)` (+F16C), `x86_64(avx2, avxvnni)`
(VEX-encoded 256-bit `vpdpbusd`; the tier every Intel client chip through Panther Lake needs, since
none has AVX-512 [R08 §3]), `x86_64(avx512f, avx512bw, avx512vl, avx512vnni)` (+BF16 on Zen 4/5; no
AMX or FP16 on Zen 5), arm64 portable. On the AVX-VNNI tier the `vpdpbusd` schedule applies at 256
bits with the same bias identity (§7.2), so it does not fall back to `vpmaddubsw` and its 3,810
bound. The AVX-VNNI and NEON/SVE schedules are **by-trigger** (trigger for AVX-VNNI: an Intel client
target profile) [R08 §3, P5 D-13]. Dispatch uses cpuid
plus XCR0 at load, with no P/E-core paths [R08]. Vector width is a cost-model choice where lanes are
free, but **under `exact` the lane count of a float reduction is semantics**: 16 lanes map to one
zmm, two ymm, a half-warp or four NEON registers [G03 F8, P5 §6]. Winning schedules are pinned per
(kernel, target profile), as Helion pins configs [R05]. `instr` definitions are generated from the
owned semantics table, so an intrinsic without validated semantics cannot be written [G02].

---

## 9. Batched prefill under canon

**Meaning.** NUMERICS §3 defines the batched product so that every (token, row) equals the
single-token value; that is what makes prefill, speculative verification and decode agree (INV-DET-2).
The batched meaning is therefore literally the per-token one:

```mith
/// NUMERICS §3 "Batched": each (token, row) equals the single-token matvec (INV-DET-2).
kernel fn q4_matmul(w: &Matrix<BlockQ4>, a: &Matrix<ActQ8>, y: &mut Matrix<f32>)
    requires y.rows() == a.rows() && y.cols() == w.rows() && a.cols() == w.blocks_per_row()
{
    par for t in 0..a.rows() {
        par for r in 0..w.rows() {            // disjoint writes: y[t][r] has one writer
            y[t][r] = q4_row_dot(w.row(r), a.row(t));   // Matrix::row ensures both lengths
        }
    }
}

schedule q4_matmul_avx512 for q4_matmul on x86_64(avx512f, avx512bw, avx512vnni) {
    tile r by 16;                   // rows -> zmm lanes, as in decode
    tile t by 8;                    // 8 tokens per pass over a row tile: each weight load reused 8x
    vectorize j using vpdpbusd;     // exact integer block sums
    keep_order acc;                 // per (t, r): blocks in ascending order, never split
    parallel r.tiles;               // threads own disjoint output tiles
}
```

As in §2, the last conjunct of the `requires` discharges `q4_row_dot`'s `requires w.len() == a.len()`
statically (DR-011): `Matrix::row` ensures `result.len() == self.blocks_per_row()`, which for
`w.row(r)` is `w.blocks_per_row()` and for the `Matrix<ActQ8>` projection `a.row(t)` is `a.cols()`,
one `ActQ8` block per column ([01-language.md](01-language.md) §5.3).

Hearth's T>1 path already processes 8 tokens per pass over a row tile [R11], so this schedule is a
transcription, not a new algorithm. Register-blocked GEMM is compatible with canonical order:
a microkernel that updates a (16 rows × 8 tokens) accumulator tile once per K block keeps every
output's chain sequential in K. What canon forbids is splitting K *across threads* (or across
accumulators) for the float chain.

**Does the K-split ban cost parallelism?** At a 512-token chunk each of Qwen3-30B-A3B's 128
experts gets about 32 tokens on average [R08 §7.2]. A 768-row gate projection is 48 row tiles × 4
token tiles ≈ 190 independent output tiles per expert, about 24,600 across the 128 experts
[inference]. Sixteen cores are not short of work, so on the CPU the ban does not limit MoE prefill
parallelism [inference]. What canon does cost is small and inherent to NUMERICS: per 16-row tile and
block, 16 `vpdpbusd` carry the integer work and about four float instructions carry the epilogue;
forbidding FMA costs one of them [inference]. Float paths (F32/BF16 weights) pay more, since R08's
4.1–5.1 TFLOPS FP32 figure counts an FMA as two operations [R08 §7.2]. BF16 dot-product instructions
fuse products and pairwise sums; they are admissible only if the semantics table shows they equal
the canonical DAG, which we do not expect [inference].

**Exact int32 cross-thread partials** (status **v0 (M5)**, a schedule primitive). Where independent
outputs are genuinely too few — tiny experts (Qwen3-Next's expert dimension is 512 [R06]), very
uneven routing, or the GPU, where split-K is the usual small-M remedy — the integer work can be
split across threads exactly: threads compute the int32 block sums `isum[t][r][g]` for disjoint
ranges of blocks g and store them; one owner per (t, r) then runs the float epilogue over g in
canonical order. Each `isum` is the same integer whichever thread computed it, so the schedule is a
member of the `int_assoc` space and needs no new correctness argument beyond T1/T2. Its price is
materialising 4 bytes per (t, r, g) and a second pass. Against the bytes it competes with, the
partials cost 4·T B per (r, g) against 34 B of Q4 weights, which is more than the weights
themselves for T ≥ 9 (3.8x at T = 32) [inference]. The schedule is therefore admissible only with
an L2- or shared-memory-resident partial tile, which the cost signature checks (§13), and
measurement decides when it pays.

**Honest prefill ceilings.** The Zen 5 ridge is about 213 ops/byte (16.4 int8 TOPS at 4.0 GHz over
77 GB/s) [R08 §7.2]. The two chunk sizes have different ceilings [inference]:

- *512-token chunk:* about 120 ops/byte, below the ridge, so the expert share is **bandwidth-bound**
  at about 120 × 77 GB/s ≈ 9.2 TOPS. At about 6.06 G ops per token that is roughly 1,500 tok/s if all
  work ran at the expert intensity, well below the compute peak.
- *2,048-token chunk:* about 480 ops/byte, **compute-bound**; the ceiling is the compute peak, about
  2,700 tok/s at 16.4 TOPS.

Hearth measures 345–433 tok/s at 512 tokens (roughly 2–3 of the ~16.4 TOPS) and 226 at 2,048
[R11]. The gap is the missing expert-major tiled VNNI prefill (Hearth task R05) and the attention core, not canonical order: a bit-identical AVX-512
value-pass prototype runs at 94 GMAC/s against 18.0 for the portable loop (measured) [R11]. The
gate is non-inferiority (δ = 3%) against interleaved `hearth-c-ref` (DR-018); any improvement claim
needs e ≥ 20.

---

## 10. Block sparsity

Block sparsity is a general feature in two flavours (status **v0** where the port needs it — causal
masks and MoE routing ids, M5 — and **v1** otherwise) [R13 §Implications 3]:

- **Static/structured masks** computable from geometry: causal masks, sliding windows (gpt-oss
  alternates dense layers with a 128-token banded window [R06 F1]), chunk boundaries.
- **Dynamic, data-dependent block lists**: MoE routing (the `ids` of §12), paged KV (a page
  table), and in later workloads top-K block selection.

Both lower to **dense inner blocks plus a block list**. Gathers go to contiguous slabs and
in-register lookup tables, not `VPGATHERDD`, which on Zen 5 issues 64 µops at about 12.6 cycles
per 16 lanes [R08]. Data-dependent indices are a typed indirection primitive whose range facts
(`#[range(0..n_experts)]`, page-table bounds) are proved or checked at construction, because affine
dependence analysis cannot see through them [R05 F7].

**The exactness subtlety.** Under canon the iteration domain of a sparse reduction is part of the
meaning: "skip the masked block" and "multiply it by zero and add" are different IEEE programs
(`0 * Inf` is NaN; `x + 0.0` turns −0.0 into +0.0). A meaning iterates over the *active* set (the
window `[pos − 127, pos]`, the routed `ids`), so skipping is the meaning, not an optimisation. A
schedule never introduces or drops a block; it may only reorder independent work (which expert is
computed first), never the combine.

---

## 11. Chunkwise recurrent scans (KDA) under canon

Kimi K3 has 93 layers, 69 of them KDA linear attention and 24 Gated MLA; KDA extends Gated DeltaNet
with finer gating and a diagonal-plus-low-rank (DPLR) transition, and each KDA layer carries a fixed
recurrent state (kimi-k3-in-c sizes it at 96 heads × 128×128 per layer, about 626 MB in total)
[R06 F1]. The state update has the form `S_t = T_t(S_{t−1}) + U_t` with a gated DPLR transition
`T_t`; outputs read `S_t` with the query. Two algebraically equal evaluation strategies exist: the
**recurrent form** (token by token, natural for decode) and the **chunkwise-parallel form** (within
a chunk, intra-chunk contributions as matrix products plus a triangular solve; across chunks, the
state passed sequentially), which is what made the delta rule practical [R02]. In floats they are
not bit-equal: the chunkwise form reassociates.

**Consequences under canon** (status **later**; decided when Hearth adds Kimi K3, DR-025):

1. **One form is the meaning; the other is at best `real(bound)`.** Converting between them is
   reassociation, so no `exact` schedule does it; a tolerance relation is a T3 certificate (reserved).
2. **Chunk boundaries must be absolute positions** (multiples of a contract constant c), never a
   function of batch size or thread count — the analogue of the "fixed split size, not a fixed
   number of splits" rule behind batch-invariant GPU attention [G03 F3]. Decode then reproduces the
   chunkwise arithmetic exactly: the state is committed at chunk boundaries, and token t's output is
   computed from the chunk-start state plus intra-chunk terms up to t. Decode work grows within a
   chunk; that is the price of batch == sequential (INV-DET-2).
3. **The choice is a canon decision** (reserved `chunks(c, …)` order; an additive `canon.v1.1`
   change while no KDA meaning exists yet, a major version once one does; migration protocol). The recurrent form makes decode cheapest and prefill sequential over t (still parallel
   over heads and state rows); the chunkwise form parallelises prefill within chunks and makes decode
   costlier. Both forms' cost signatures on the measured profile decide; the loser becomes a scoped
   tombstone [R02: recurrent vs chunkwise is niche-dependent].
4. **Gates use transcendentals**, named `cr::` or `canon_v1::` as in any exact code.
5. **The state is an exact value with a content hash at token boundaries.** Its snapshot API
   (checkpoint and resume, as kimi-k3-in-c does with checksummed state files [R06]) is designed with
   the weight-overlay API (DR-025, [06-forge.md](06-forge.md)). A placement may move a KDA layer only
   if the state hash is identical across placements (§15).

The intent oracle for KDA is weaker than for GQA: reference implementations commonly use the
chunkwise form for prefill and the recurrent form for decode [inference], so agreement with them is a
tolerance claim (§18). Physics context [R06]: Kimi K3's ~109 GB BF16 trunk does not fit in 64 GB;
routed experts touch ~25.8 GB per token; kimi-k3-in-c reports 19.8 s/token at 64 GB, measured by
the project on 2× EPYC 7763 (AVX2) with 3.2 GB/s O_DIRECT cold reads, not on this machine. On the
990 PRO, R06's lower bound for the routed experts alone, at about 5.2 GB/s effective with no cache
hits, is about 5 s/token before any trunk streaming [R06, inference]. With the lossless trunk
streamed as well, [07-hearth-port.md](07-hearth-port.md) §11 derives ≈ 59 GB/token from the trunk,
≈ 8.2 s, ≤ ~0.12 tok/s, and about 12 s/token with experts [inference].

---

## 12. Flows and policies

### 12.1 Flows

A **flow** is the meaning of a data-movement computation: which bytes come from which tier, which
work starts as each item's bytes arrive, and how results combine (status **v0 (M4–M5)**, port Stage S4–S5).
Completion order varies; outputs must not.

```mith
/// One MoE FFN step (NUMERICS §5.3). Slabs may arrive in any order; the sum may not.
flow moe_ffn(cfg: &LayerCfg, x: &Act, store: &Store) -> Result<Act, IoError> uses { io, spawn } {
    let ids = route(cfg, x);                                     // exact; ties -> lower expert index
    let outs = deterministic(by: golden::scheduling_independence) {
        store.map_on_arrival(&ids, |w| expert_ffn(cfg, w, x))   // completion order varies
    }?;
    Ok(canon::combine_rank(&ids, &outs, cfg.routed_scale))     // rank order: fixed
}
```

The `deterministic` block removes **only** `nondet` (its result becomes `blob`-grade); `io` and
`spawn` stay in the signature (DR-006). It needs a DeclareDeterministic grant, cites its evidence and
passes that evidence's grade downstream. **As written**, the citation is a named golden test, so
every value-level claim on data that flows from it (`deterministic` of an output, end-to-end
logits) is capped at `tested`. Input-universal claims (`refines`, `confined`, `safe`), such as an
`expert_ffn` kernel's refinement, are not capped by this upstream boundary: the cap is
⨅ grade(b) for b ∈ B(o), the data-flow set ([01-language.md](01-language.md) §6.4 and §7.2,
[03-trust.md](03-trust.md) §3.2–3.3). Once the store-core certificate O1–O5 (§12.4) is admitted at
`validated`, the Author changes the citation to
`deterministic(by: store_core::output_noninterference)` and the grade rises to `validated` with no
other edit; INV-DET-1 on the store path is then honestly `validated`, not `proof` [P2 §3.5]. Each
expert writes its own buffer and the sum is in rank order, which is why experts arriving from NVMe
in any order give identical output today (NUMERICS §5.3).

### 12.2 One flow, many handlers — one policy code for engine and simulator

A flow is interpreted by several **handlers** [RV: D2-C, P3 §4]:

| Handler | Computes | Tier of its numbers |
|---|---|---|
| engine | the real thing, via C11 | measured, by the sealed evaluator |
| simulator | trace replay of routing traces, running the **same compiled policy code** | SIMULATED until calibrated |
| bytes | unit-typed bytes per tier from load events | exact for timing_blind policies (§12.5) |
| timing | max-plus critical-path estimate from profile service laws | `est` only; ranks, never prunes |

The decisive property is the shared policy code. Each policy compiles once to C11 behind an
`hx_policy`-style vtable; the engine links it, and Hearth's Python simulator calls the same object
through its existing ctypes path [RV: D2-A E0, inference]. Only the simulator's hardware model stays
hand-written (`est`-tier). Hearth's drift history motivates this: mis-counted prefetch bytes (H04),
LFU heat seeded differently from the engine, online policies "beating" a warm-started Belady bound
[RV: D2-C], and a simulated lookahead win rejected on hardware (depth 4 raised hits from 73% to 86%
but cut decode from 13.0 to 10.0 tok/s, measured). Shared code removes the first class of error;
SIMULATED labels contain the second.

### 12.3 `timing_only` policies and hint ports

A `timing_only` policy (status **v0 (M4)**) may influence *when* and *where* things happen — eviction,
prefetch issue, I/O order, mirror choice, pinning, thread mapping — and nothing else.

```mith
/// A policy can only emit hints. The store core validates every hint, so no policy can change
/// logits (certified space, store-core certificate O1–O5). Integer scores avoid the f32-Ord trap.
policy fn pick_victim(slots: &[SlotView], now: Tick) -> Hint<SlotId> {
    let mut best = Hint::none();
    let mut best_age: u64 = 0;
    for s in slots {
        if s.pinned || s.refs > 0 { continue; }
        let age = now.0 - s.last_use.0;
        if age > best_age { best_age = age; best = Hint::some(s.id); }   // ties: lowest index wins
    }
    best
}
```

The per-policy check (milliseconds) is T0 confinement [RV: D2-A]:

- **Payload parametricity.** A policy sees `SlotView`s and opaque handles; slab bytes do not
  exist in its world.
- **No ambient authority.** No `io`, `time`, `alloc`, `fp_env`; a fixed-size state block; loops
  only over core-provided slices with static fuel; no recursion.
- **Outputs only in a hint lattice** (`Hint<T>`), validated by the core at commit.
- **Binary-level confinement**, re-checked on the compiled object so that neither mithc nor the C
  compiler is trusted: an instruction allowlist banning RDTSC/RDTSCP/RDPMC/CPUID/LDMXCSR/FLDCW,
  syscalls and indirect calls; stores only to the state block or stack; fuel instrumentation
  [P2 §5.2]. The front-end effect check becomes advisory. Details in [03-trust.md](03-trust.md).

Hint ports live in the trusted store core:

```mith
/// The store core is trusted, hash-keyed and certified once. Policies plug into its ports.
store ExpertStore {
    hint port evict: pick_victim fallback lru validate evictable budget fuel(4 * n_slots) off_lock;
    hint port prefetch: next_layer fallback none reserve demand_readers >= 1 budget prefetch_bytes;
    certificate output_noninterference(O1, O2, O3, O4, O5)
        evidence validated(model_check(bound = 6), chaos_suite, core_mutants(kill = 1.0));
}
```

**Keywords these items introduce** (DR-002: every new concept is keyword-led). `store`,
`hint port` and `certificate` (status **v0 (M4)**) and `flow` (status **v0 (M4–M5)**) are contextual item keywords, alongside
`policy` and `schedule`. They are listed, with status labels, in the Tier 0 keyword lists of
[../ARCHITECTURE.md](../ARCHITECTURE.md) §5.1, [01-language.md](01-language.md) §2.4 and
[05-agent-protocol.md](05-agent-protocol.md) (Tier 0 block and Lark `item` production). The clause
words inside a `store` item (`fallback`, `validate`, `budget`, `fuel`, `reserve`, `off_lock`,
`evidence`) are reserved only inside that item, as the primitives inside a `schedule` are; outside
it they are ordinary identifiers.

Port semantics:

- **Off-lock on snapshots.** Today `pick_victim` runs under the single store mutex, so policy time
  becomes compute stall; ports run policies on a snapshot and validate at commit [RV: D2-A].
- **Fallback, never Err.** A policy that traps (fuel exhausted, an underflow in `now.0 - …`, an
  out-of-range or invalid hint) yields "no hint" and the port uses its fallback; after k strikes the
  policy is ejected for the session. A policy fault **never** returns `Err`, or a policy could deny
  service through the `Err` branch of the noninterference theorem (a gap found in all proposals).
- **Robust wrapper.** `robust(p, lru, eps)` switches to LRU when `p` falls behind by more than ε
  [RV: D2-A].
- **Timing contracts** (fuel, reserved demand readers, a prefetch byte budget, a miss-ratio floor,
  a watchdog) are monitored, not proved. Hearth gap: with `n_io = 1` a demand read can wait behind a
  prefetch [RV: D2-A].

D2-B's shadow-priced prefetch rule is a typical policy body: issue only when
`p · stall_saved > λ · (1 − p) · bytes / BW + evict_damage`, λ being NVMe utilisation [RV: D2-B].
Float comparisons are allowed in policies; sorting by an f32 key is not (f32 is not `Ord`).

### 12.4 The store-core certificate O1–O5

The one-time theorem, keyed by the core's hash: **for every hint stream h and every I/O completion
order σ, the output is either the output with the fallback policy and a reference order, or an
error** [RV: D2-A]. It splits into five obligations:

| | Obligation | Meaning for Hearth |
|---|---|---|
| O1 | Hint validation | a victim must be evictable (not pinned, `refs == 0`); prefetch targets must be valid; anything else is ignored |
| O2 | Slab race freedom | slab bytes follow LOADING → READY(refs > 0) → evictable; no reader sees a slab being refilled |
| O3 | Arrival-order confluence | results do not depend on completion order: completion-order compute plus rank-order combine |
| O4 | Lossless tiers by content hash | every tier copy, mirror included, is verified against a per-slab content hash of the canonical (on-disk) layout; verification happens before any relayout, and a relayouted copy (VRAM, CPU repack) is keyed by (slab hash, relayout id) and checked by the relayout certificate plus a per-instance round trip or output hash recorded at first fill (§7.4). Live gap: `check_mirror` compares only the first page of up to 16 slabs and FORMAT.md has no slab hash, so a drifted mirror chosen by timing would break INV-DET-1 nondeterministically |
| O5 | Liveness | `n_slots ≥ 2·top_k + n_io + 2` (checked at open, not at runtime); an I/O failure yields `HX_E_IO`, never wrong logits |

`Err` is reachable only through genuine I/O failure, never through a policy. The certificate is
graded **`validated`** — bounded model check, chaos-policy suite (random, anti-LRU, out-of-range,
over-budget, FTZ hook, drifted mirror) with read-order fuzzing, 100% kill of seeded core mutants —
until mechanised (DR-010). Falsifiable predictions: every type-checked policy is bit-identical (a
hard stop if violated); a C hook that sets FTZ breaks golden output while the Mithril equivalent
fails to compile [RV: D2-A]. The honest prize: eviction gains a few points at most, prefetch timing
is the bigger lever, and the durable win is assurance (closing the mirror and FP-environment holes);
large wins such as lower-bit cold experts change outputs and belong to the reserved `approx` lane
(§16) [RV: D2-A].

### 12.5 `timing_blind` and what it licenses

A `timing_blind` policy is a `timing_only` policy whose decisions read only the logical event
stream, never clocks or completion events (status **v0 (M4)**). For such policies the trusted core can
replay a routing trace and obtain **exact** bytes per tier, because INV-DET-1 makes the trace
independent of the policy; this is what makes replay-conditioned pruning sound. In the simulated
D3-ii pilot it pruned 16–41% of candidates per cache size (66% jointly), while physics-only
rooflines pruned none of 144 [RV: D3-ii]. Those fractions overstate what `timing_blind` replay
licenses: some pruned candidates were prefetching configurations that are deterministic in the
simulator but timing-dependent in the engine, so the real-engine fraction is likely lower and is
gated at M4 on the eligible part of the 144-candidate grid ([06-forge.md](06-forge.md) §5.4)
[inference]. Timing-dependent policies — prefetch, which D2-A calls the
bigger lever — get only MIN-type bounds, which pruned nothing. How the Forge uses this, and the
audit protocol for prune certificates, are in [06-forge.md](06-forge.md).

---

## 13. Cost signatures and the roofline

### 13.1 The signature

For every kernel, schedule, flow and placement the compiler derives a cost signature (status
**v0 (M2)**, with `mithc explain` v0; P3's design, adopted by all three judges):

```text
bytes { nvme, dram_rd, dram_wr, pcie_h2d, pcie_d2h, vram }   per tier, incl. the DRAM write of each DMA'd miss
ops   { int8_mac, f32_add, f32_mul, f32_div, cvt, ... }       per class (mul and add counted apart: no FMA)
syncs { barrier, cross_ccd, h2d_event }                       per call
```

It is **symbolic at build time** (in shape parameters, k, dtypes, and runtime observables such as
per-tier hit rates), **numeric at load time** (evaluated with the model header's dimensions; this
needs no code specialisation, so it does not wait for `@bind(load)`, which is by-trigger), and
**measured at run time** by the sealed evaluator. All values are `Quantity<Unit, Origin>`:

```mith
let bw: Quantity<GBps, Measured> = profile.dram_read_all_core;
// Formatting prints value + origin ("77 GB/s, measured, <hw fingerprint>"); an unlabelled
// number does not format. Simulated and measured quantities do not mix without conversion.
```

Unit errors such as Hearth's `/tok` versus `*tok` bug become type errors [RV: D2-C].

### 13.2 Floors, bound tiers and plausibility

Evaluating a signature against a machine profile gives two numbers [P3 §4]:

- the **floor** `T_floor = max over tiers ρ of bytes_ρ / BW_ρ` (perfect overlap), extended with a
  compute term (canonical op counts over peak) and the work/span laws [RV: D3-ii];
- a **serial estimate** `T_serial = Σ_ρ bytes_ρ / BW_ρ + compute + syncs · latency`.

Bound terms carry a **soundness tier**: `phys` (link, DIMM and datapath limits: 96 GB/s DDR5-6000,
7.877 GB/s PCIe 4.0 x4), `emp` (audited measured peaks: ~77 GB/s DRAM, 7.16 GB/s demand reads) and
`est` (calibrated efficiencies, the simulator's time model). **Only `phys` and audited `emp` terms
may prune or quarantine; `est` may only rank** [RV: D3-ii]. A measured peak is a lower bound on the
attainable roof (a better kernel or I/O pattern can beat 77 GB/s or 7.16 GB/s), so an audited `emp`
term acts as an upper bound only with a pre-registered headroom: `emp_bound = min(phys, max observed
peak × (1 + h))`, with h at least the measurement CI plus a declared margin (e.g. 5%). Results between
`emp_bound` and `phys` are flagged for audit, not quarantined; pruning uses `emp_bound` with the same
margin (reviewer note in §20). A measurement beating a `phys` floor is quarantined as an evaluator bug
or a hack. A policy bound such as Belady may quarantine only once it
is itself validated: two generations of Hearth's "Belady bound" were beaten through bugs (LRU 0.697
vs 0.692; lru-layer 68.2% vs 63.4%) [RV: D3-ii]. Profiles come from `mithc profile measure` inside the
evaluator (STREAM per CCD and all-core, NVMe request-size × queue-depth grid, PCIe H2D/D2H, later a
VRAM GEMV), keyed by a profile hash (memory, DIMMs, PCIe, drives, I/O mode, PBO); a mismatch voids
dependent claims.

### 13.3 `mithc explain`: a worked example

One Qwen3-30B-A3B expert projection (768 rows × 2048 columns, Q4) [P3 §7]:

```text
$ mithc explain q4_matvec --profile this-pc --shape rows=768,cols=2048 --json
{"kernel": "q4_matvec#<hash>", "schedule": "q4_matvec_avx512",
 "bytes": {"dram_rd": "835584 B (derived: 768 x 32 blocks x 34 B)"},
 "ops":   {"int8_mac": 1572864, "f32_mul": 49152, "f32_add": 24576, "cvt": 24576},
 "syncs": {"barrier": 1, "est": "0.75 us (measured pool round trip, 16 threads) = 7% of floor"},
 "intensity": "3.8 int ops/B; ridge 213 ops/B [inference, R08]",
 "binding": "dram_rd",
 "floor": {"emp": "10.9 us at 77 GB/s (measured profile)", "phys": "8.7 us at 96 GB/s"},
 "achieved": null, "fraction_of_roof": null,
 "next": ["mithc bench q4_matvec --shape rows=768,cols=2048"]}
```

Arithmetic: 768 × 32 × 34 B = 835,584 B; / 77 GB/s = 10.85 µs; 2 × 1,572,864 int ops / 835,584 B ≈
3.8 ops/B, R08's 56x-below-ridge figure. At 16.4 TOPS the integer work takes about 0.19 µs
[inference]: the cores mostly wait, by design. The floor is not pure bytes: the one barrier of the
`par for` costs about 0.75 µs per 16-thread pool round trip (measured [R11]), about 7% of this
kernel's 10.9 µs floor, and a token runs hundreds of such regions. That sync cost is why small regions
stay on the caller (§3). Once measured, `explain` adds achieved time, fraction
of roof and gap attribution (for cache policy: eviction vs wrong prefetch vs lateness [RV: D2-B]).
The fraction of roof is the Forge's physics-normalised fitness: a stopping rule ("within 5% of
floor"), a hack detector ("above floor") and a diagnosis.

### 13.4 Honest Hearth ceilings

| Workload | Bytes per token | Ceiling (arithmetic) | Today | Labels |
|---|---|---|---|---|
| Qwen3-30B-A3B, Q4 experts + Q8 dense ("cfg B"), in RAM, short context | DRAM 2.27 GB [R08] (R11 counts ~2.38 GB incl. ~0.11 GB KV) | 2.27 GB / 77 GB/s = 29.5 ms → **33.9 tok/s**; 42.3 at 96 GB/s | **19–22 tok/s** (noisy) = 43–50 GB/s effective, 56–65% of the measured roof; llama.cpp ~25 tok/s (noisy, not a clean head-to-head) | ceilings [inference]; today measured |
| same, 4K context | 2.67 GB (+0.40 GB KV) | **28.8 tok/s** at 77 GB/s | — | [inference] |
| uniform Q4 ("cfg A") | 1.66 GB | 46.4 tok/s at 77 GB/s | — | lossy for this model: opt-in only (INV-LOSSLESS-DEFAULT) |
| NVMe-bound, 2 GiB cache | NVMe 401–402 MB/token measured; MIN floor ~193 MB/token | serial 9.9 tok/s, overlapped 16.2 [R11]; clairvoyant ~20 [RV: D2-B] | **13.02 tok/s** (depth-1 prefetch); depth 4: 10.0 tok/s at 545 MB/token | MIN floor [inference, low-medium]; today measured |
| Kimi-K2-class, 40 GB cache, one 990 PRO | NVMe 2.25–5.62 GB at hit rate 0.8–0.5; DRAM 11.37 GB backbone | all-in-DRAM ceiling **3.41 tok/s**; band **0.8–2.9 tok/s** | synthetic 1T container: 1.2–1.8 s/token worst case | [inference]; measured synthetic |
| Prefill, 512 / 2,048 tokens | ~120 / ~480 ops/B against a 213 ops/B ridge | 512: expert share bandwidth-bound (~9.2 TOPS roof, ~1,500 tok/s); 2,048: compute-bound, ~2,700 tok/s at 16.4 TOPS | 345–433 / 226 tok/s | [inference]; measured |
| GPU tier (a), owner-gated: experts only in VRAM, all dense work on the CPU | DRAM ≈ 1.31 GB dense per token (2.27 − 0.963 GB of experts), plus (1 − h_vram)·0.963 GB of misses. VRAM fit: all 6,144 Q4 experts × 2.51 MB ≈ 15.4 GB against ~10.5 GiB usable, so h_vram < 1 | ≤ 77 GB/s / 1.31 GB ≈ **59 tok/s**; ≈ 33–38 tok/s at Hearth's 56–65% efficiency, about 1.6–1.8x over ~21 tok/s | — | [inference]; cannot meet the 2x gate alone (§15.6) |
| GPU tier (b), the gate configuration: experts + Q8 dense projections + LM head in VRAM, attention core on the CPU | DRAM (1 − h_vram)·0.963 GB + KV; VRAM ≈ 1.25 GB dense + resident experts (~10 GB left, about 4,000 of 6,144); ~96 H2D/D2H syncs per token | byte terms small (e.g. VRAM ≈ 2.1 GB at 672 GB/s ≈ 3.2 ms at the SIMULATED h_vram = 0.89); bound by syncs and hand-offs: ≲ 20 µs per round trip at the 2x gate | — | [inference]; gate: measured ≥ 2x CPU-only (DR-022) |
| GPU tier (c), later: full backbone incl. attention core in VRAM (needs a major canon version, §15.4) | VRAM serves 89% of expert loads (simulated) | GPU-bound in the simulator | SIMULATED 23.2 → 112.4 tok/s (Qwen3), 15.2 → 54.7 (gpt-oss-120b) [G03 F9] | SIMULATED; GPU paths uncalibrated |

Sources for unmarked rows: [R08 §7], [R11], [P3 §6], [G03 F1, F9]. As a fraction of physics against
this table's own 29.5 ms floor, Hearth's 45–53 ms per token is 1.5–1.8x the floor and llama.cpp's
~40 ms about 1.35x [inference]. The D3-ii node quotes 1.8–2.1x and 1.6x against a DRAM bound of
about 25 ms, which used a different byte count [RV: D3-ii].

### 13.5 What follows for Mithril

About **1.5x of honest CPU headroom** exists for in-RAM decode, all of it in effective bandwidth
(~45 → ~65 GB/s would give about 28–29 tok/s [R08]); none comes from instruction selection, since a
Q4 GEMV uses about 3% of the core's instruction capacity at full bandwidth [R08 §2]. Hence no direct
x86 emitter for decode GEMV (DR-009), and the GPU tier before any emitter when the object audit
covers ≥ 95% of kernels ([04-toolchain.md](04-toolchain.md)). Wins come, in order of size, from
placement (GPU tier), bytes (lossless formats, policies approaching MIN bytes, I/O–compute
overlap), schedules for prefill and attention, and alias facts in emitted C. Gates are relative
(DR-018); the 69.6 GB/s single-thread L2-resident figure, measured on a busy machine, is context only.

---

## 14. Tiers and placement

**Tiers** are types, present from **v0** (types at M1; NVMe and DRAM implemented in v0 at M4–M5,
`std_platform` and S4; VRAM **reserved**):
`Tier::{Nvme, Dram, Vram}`, where `Vram` takes a device index (`Vram(d)`, reserved with it). The
residency types on flow values are `resident<T, Tier>`, `streamed<T, Tier>` and
`cached<T, Tier, budget>` [P3 §3.5, P5 §6], the same spelling and arity as
[../ARCHITECTURE.md](../ARCHITECTURE.md) §7.4 and [01-language.md](01-language.md) §4.
`Dram` and `Vram` buffers are addressable within their device; `Nvme` is
never dereferenceable and is reached only through `read_at` into an aligned buffer:

```mith
/// Unbuffered positional read of one expert slab. Authority is explicit in the signature.
fn read_slab(file: &BlobFile, off: Aligned<u64, 4096>, buf: &mut SlabBuf) -> Result<(), IoError>
    uses { io }
{
    file.read_at(off, buf.bytes_mut())   // std_platform: OVERLAPPED+NO_BUFFERING / pread+O_DIRECT
}
```

Alignment is in the types, so direct-I/O preconditions are type facts [P3 §3.2]. Demand and
prefetch have separate priorities, at least one reader is reserved for demand, and reads are
chunked and cancellable [RV: D2-B]. `std_platform` and large pages for a 30 GB arena are in
[04-toolchain.md](04-toolchain.md).

**Placement** is a realisation like a schedule: it moves work between tiers and devices and must
not change bits. Its physical rules come from the profile:

- **PCIe 5.0 x16 (63 GB/s theoretical, ~50 GB/s planning) is slower than the CPU reading DRAM
  (~77 GB/s)**, so at batch 1 cold experts are computed where they live, never shipped per token
  [R08 §6, G03 F2]; upload-on-miss halved decode at a 43.5% hit rate in a llama.cpp follow-up
  (33 → 16 tok/s) [G03 F9].
- **Topology is a cost term**: 64 GB/s per CCD; cross-CCD latency "nearly 200 ns" on launch firmware
  [R08 §2]; barriers per layer are counted.
- **Every DMA'd NVMe miss also costs a DRAM write** [R08 §7].
- **Every VRAM cache fill also costs a DRAM read.** Uploading an expert reads the same DRAM bytes as
  computing it on the CPU, plus PCIe, so fills compete with CPU cold-expert compute for the DRAM
  roof. The cost signature counts each fill as both `dram_rd` and `pcie_h2d`. Fills are issued
  through a `vram_fill` hint port (`timing_only`, owner-gated with the GPU tier) with a per-token byte
  budget, and stay off the critical path: a miss is computed on the CPU, never waited for, which
  avoids the upload-on-miss regression above. Full-rate asynchronous H2D on Windows needs pinned host
  memory; how pinned staging (registering `SlabBuf` chunks with the driver, e.g.
  `cuMemHostRegister`) interacts with the large-page locked arena is a `std_platform` item of the
  owner-gated tier ([04-toolchain.md](04-toolchain.md) §9).

**The placement checker rule** (cross rule C2 [P2 §3.4], status **v0 (M4)**; it has nothing to
reject until `device(t)` becomes producible, D-06): a value of determinism
scope `device(t)` must not flow into a computation whose placement is decided at runtime. A
cache-driven placement — whether expert e runs on the CPU or the GPU depends on what is resident —
therefore requires `cross_device` kernels. Statically placed, opt-in fast paths with device orders
(a tensor-core BF16 prefill, say) are allowed only as opt-in profiles with their own goldens, never
as defaults [G03 Implications 2, DR-015]. Placements become a Forge search space only **by-trigger** (F1-place, after the DR-022 gate, ROADMAP §8 M7)
([06-forge.md](06-forge.md), level F1).

---

## 15. The GPU expert tier and cross-device determinism (DR-022)

**Status: owner-gated, by-trigger** (trigger: the owner puts the RTX 5070 in scope, an INV-DEP
ruling on `nvcuda.dll` or Vulkan, and the decisive GEMV experiment below passes [P5 D-8]). The
machine has an RTX 5070: 12,227 MiB, compute capability 12.0, PCIe Gen5 x16 capable, about 1.5 GB in
use by the display at idle (measured, read-only query) [G03 F1]. Moving the display to the iGPU is an
owner decision.

### 15.1 Why cross-device bit-identity is required, not nice

With an LRU GPU expert cache, whether expert e runs on the CPU or the GPU depends on cache state;
if the devices compute different bits, logits depend on cache state, breaking INV-DET-1 and, if
default-on, INV-LOSSLESS-DEFAULT [G03 Implications 2]. Batch-invariance work (Thinking Machines,
vLLM, SGLang, cuBLASLt's experimental mode, which excludes compute capability 12.0) gives
same-device determinism only [G03 F3]. No engine found offers output independent of VRAM contents
[G03] — N8 in [../ARCHITECTURE.md](../ARCHITECTURE.md).

### 15.2 What is cross-device exact under canon.v1

The heavy work in Hearth's numerics is exact integer arithmetic plus a short float epilogue in
fixed order, which makes them unusually GPU-friendly [G03 F8]:

| Op (NUMERICS) | Device mapping that reproduces it bit for bit | First GPU tier? |
|---|---|---|
| Q4/Q8/MXFP4 expert GEMV (§3) | dp4a for int32 block sums (INT8 `mma` only after its exactness on sm_120 is confirmed, G03 open question 3); per-block products rounded, then a serial `add.rn` chain of n/64 adds: 32 for d = 2048, 45 for 2,880, 112 for 7,168 | yes |
| Q8 dense projection GEMVs and LM head | same kernel family | **yes, statically placed in the gate configuration** (§15.6): without them the CPU still reads ~1.31 GB per token and 2x is out of reach; costs ~2 CPU↔GPU transfers per layer around the CPU-resident attention core |
| activation quantisation (§2) | warp max (exact, order-free), IEEE `/` with `prec-div=true`, `cvt.rni` | yes |
| `sum16`/`dot16`, RMSNorm, router | one half-warp per row: lane j accumulates in order, then shuffles 8, 4, 2, 1 with `add.rn` | yes |
| SiLU/SwiGLU, sigmoid, softmax `exp` | only with `canon_v1::expf` (or a validated `cr::expf`) compiled to PTX | yes, after ADR-0010 |
| RoPE `sin`/`cos` | computed with `cr::` on the host and uploaded (a few KB per token) | host-side |
| MoE combine (§5.3) | rank order, identical on either device | yes |
| attention core (§5.1–5.2): `dot16` scores, softmax, sequential-in-t value pass | expressible exactly (one thread per (head, d), serial over t) but latency-bound at long context: a 32k chain is on the order of 10^5 cycles per layer | **no** — stays on the CPU (§15.4) |
| float prefill GEMM (F32/BF16) | CUDA cores only, no FMA: about 15.4 T non-FMA multiply-add pairs/s vs 61.7 TFLOPS dense BF16 tensor, about 4x lower ceiling | not in the first tier |

PTX `add`/`mul` with explicit `.rn` are never contracted; `nvcc --fmad` defaults to true and is
avoided; fast-math is banned [G03 F4]. Decode stays bandwidth-bound (about 0.67 TFLOP/s needed at
672 GB/s with BF16 weights, under even the non-FMA rate) [G03 F4]. Canonical GEMV's overhead against
llama.cpp-class GEMV is *guessed* at 0–30%, low confidence, unmeasured [G03 F8].

### 15.3 Transcendentals on the device

CUDA's `expf`/`sinf`/`cosf` are 2 ulp with independent host and device implementations; LLVM libc's
GPU build is 1 ulp off correct rounding for `sinf`/`cosf` [G03 F5]. So Mithril owns the
implementations: `canon_v1::expf` in PTX is checked structurally; `cr::` on the GPU should use
float-only algorithms, since FP64 runs at 1/64 rate on GeForce [G03 F5], and each target is validated
exhaustively over 2^32 inputs before joining the cross-device set. Until then RoPE is host-computed.

### 15.4 Attention order on the device

DR-022 keeps the attention core on the CPU in the first GPU tier. Moving it first needs validated
canon/cr PTX transcendentals (§15.3) and a **fixed-chunk attention order** (sequential inside each
chunk; chunks of contract-fixed size at absolute positions, combined in order), the analogue of
SGLang's and Thinking Machines' fixed split size [G03 F8]. That changes canon for the CPU too: it
redefines an existing op-DAG, so it is a major version (`canon.v2`) under the canon migration
protocol, with bit-exact goldens reset, not an additive `canon.v1.1` change
([03-trust.md](03-trust.md) §12; §5). The chunk size, and the effect on MLA's absorbed form and KDA
(§11), are open [G03 open question 4]. Attention on the GPU with a device-specific order is a
`device(t)` lane: opt-in, own goldens, never default.

### 15.5 Evidence and trust base

The PTX backend (B2) emits PTX text with explicit `.rn` and loads it with `cuModuleLoadData` from the
driver DLL already on the machine; no CUDA toolkit is needed [G03 F4]. T1 checks PTX against KIR
using a small PTX table (`add/mul.rn.f32`, `cvt`, `dp4a`, shuffles) [P3 §5]. **ptxas and the driver
JIT that turn PTX into SASS are in the trust base**, and the SASS level is graded `tested`, backed by
the cross-device hash corpus (DR-022). `mithc ledger why --trust-base` prints exactly this chain.
WDDM display-driver timeouts and VRAM sharing with the compositor are unverified risks [G03 open
question 7].

### 15.6 The gate and the decisive experiment

DR-022: canonical expert GEMV ≥ 0.6x llama.cpp MMVQ on the same card, **and** measured end-to-end ≥ 2x
CPU-only, **and** logits hash-identical across placements.

**The gate configuration is a design constraint.** Moving the expert GEMVs alone cannot pass the 2x
clause: the CPU would still read about 1.31 GB of dense weights per token from DRAM, a ceiling of
about 59 tok/s and about 33–38 tok/s at Hearth's present 56–65% efficiency, i.e. about 1.6–1.8x over
~21 tok/s [inference] (§13.4, row a). The configuration judged against the gate therefore
**statically places the Q8 dense projection GEMVs and the LM head on the GPU** as well (same
`cross_device` kernel family, §15.2), with the attention core, host-computed RoPE tables and expert
misses on the CPU (§13.4, row b). The price is about two CPU↔GPU transfers per layer around the
CPU-resident attention core, about 96 per token over 48 layers.

**The sync budget follows from the gate.** 2x over the measured 19–22 tok/s is 38–44 tok/s, a token
budget of about 23–26 ms. If the ~96 round trips may take at most about 2 ms of it (≈ 8%), each must
cost ≲ 20 µs, including WDDM submission and kernel-launch latency [inference]. The judges' warning
that syncs can eat a 12–15 ms token budget [judges] corresponds to roughly 70–80 tok/s, the budget of
a placement near the simulated full-backbone case (§13.4, row c), not of the gate. The placement's
cost signature counts `h2d_event` syncs and `pcie_*` bytes, so `explain` shows the risk before
measurement.

**The decisive experiment.** Before any backend work, the G03 experiment runs and records two
numbers on the RTX 5070: (1) a Q4/Q8 expert GEMV prototype with exact integer blocks and an `add.rn`
epilogue against MMVQ — "the single number that decides useful speed" [G03 open question 2]; and
(2) the **measured CPU↔GPU round-trip latency under WDDM** for an activation-sized transfer plus a
kernel launch, against the ≲ 20 µs budget.

**Outcomes** (the bands of [../ROADMAP.md](../ROADMAP.md) §5 M7, stated the same way in DR-022 and
[../ARCHITECTURE.md](../ARCHITECTURE.md) §13): *pass* at ≥ 0.6x MMVQ with the end-to-end and identity
clauses met; *amber* at 0.5–0.6x: one relayout campaign (scales split from the 34-byte blocks,
§7.4), then re-judge; *kill* below 0.5x, or when identity cannot be repaired [P3 M6]. The kill
outcomes are split, because rule C2 (§14) forbids `device(t)` values in placements decided at run
time, and a Qwen3 expert tier is necessarily cache-driven (about 15.4 GB of Q4 experts exceed about
10.5 GiB of usable VRAM, §13.4 row a):

- *speed miss with identity intact* (GEMV < 0.5x, or end-to-end < 2x): the tier stays an opt-in
  `cross_device` profile, never a default, recorded as a class H tombstone with a hardware trigger,
  so the `cross_device` kernels are kept;
- *identity failure*: only a statically placed, load-time-fixed GPU plan may run, as a `device(t)`
  opt-in lane with per-plan goldens; no cache-driven expert placement.

A round-trip latency far above budget fails the end-to-end clause by arithmetic before any backend
is built.

---

## 16. The reserved approx/cache effect

Step caching, low-bit attention, INT8 KV, lower-bit cold experts, reduced or dynamic top-k and
layer skipping all trade exactness for speed [R13 §Implications 4, R06]. They get one typed route
(status **reserved**: in types and schema from v0, producible later):

- the **`lossy` effect** (authority, in the signature) plus the **`approx(profile)` grade** on
  results; fidelity composes by **join**, so one `approx` input makes a logits value `approx`;
- a declared policy (reuse interval, threshold on a declared distance, bit width) and an error
  contract;
- a `quality(profile)` claim measured on a held-out corpus (KL divergence, flip rate, route
  agreement where values reach top-k or argmax) [P2 §3.6, §5.3];
- **never a default**: a default profile reaching `lossy` is a link error (INV-LOSSLESS-DEFAULT;
  DR-015).

**Exact memoisation is not approximate caching.** INV-DET-2 makes KV-prefix reuse an exact memo —
a prefix evaluated in any batch shape has the same bits — so a content-hash-keyed prefix cache needs
no `lossy` effect [inference]. Reusing values whose inputs are merely similar is `approx`.

---

## 17. The visual-generation boundary (DR-024)

**No visual-generation primitives in v1** — no `Gaussian4D`, `solve_ode`, rasteriser or framebuffer
built-ins [R13 §Implications 1]. Generative video on this CPU is ≈30–40× short of Self-Forcing-class
16 fps at 480p on raw peak, and ≥ 250× short of the seed's 720p/1080p 30 fps target [R13, inference]:
Self-Forcing's 1.3B model needs roughly 160–220 TFLOP/s for 16–17 fps at 832×480, and the 9950X peaks
near 5 TFLOPS FP32. Video diffusion transformers are compute-bound, so Hearth's bandwidth physics
does not transfer [R13, inference]. Realistic local video needs tensor cores, so it is a
**`device(t)` workload** that must not stretch the cross-device contract [G03 Implications 7].
Through v1, Mithril provides the shared general features instead: the layout/tile algebra (§7.4),
block sparsity (§10), low-bit formats (§7), bounded streaming flows (§12) and the reserved
approx/cache effect (§16). Generative video is **later (v2+), gated on a GPU backend**; a CPU Gaussian-splatting
rasteriser and a Wan-1.3B DiT block serve as **benchmarks** of those features [R13], not features.

---

## 18. Meanings and Hearth's numpy reference: the independent intent oracle

A meaning is complete by construction for exact refinement: every realisation is checked against
it. Its risk is the **intent gap** — the meaning itself may be wrong [P2 §5.5]. Bit-exact checks
cannot see this, because they compare implementations of the same text. Mithril therefore checks
meanings against oracles of decreasing dependence on NUMERICS (status **v0**, from S1 at M2, for the oracle chain;
the port mechanics are in [07-hearth-port.md](07-hearth-port.md)):

| Oracle | Independent of | Comparison | Catches |
|---|---|---|---|
| `hearth-c-ref` (frozen C binary) | Mithril's compiler and meaning text | bit-exact cross-binary hash corpus | transcription and lowering errors; not errors NUMERICS itself contains |
| `hearth.reference` (numpy) | the C and Mithril code; shares NUMERICS's reduction orders, processes tokens one at a time, evaluates `exp`/`sin`/`cos` in float64 rounded to float32, emulates activation quantisation by default | INV-NUM-1: max abs logit error ≤ 1e-3·max(1, max\|logit\|) on F32 containers; INV-NUM-2: routing ids equal | moderate intent errors (a wrong scale, a wrong rope style), tie-rule errors through exact route equality |
| Hugging Face `transformers` | NUMERICS entirely (different orders, different kernels) | 2e-3 relative against `hearth.reference` | architecture misreadings (norm placement, attention variant, routing normalisation) |

**Using the chain.** (1) Until the normative flip at the end of the port, NUMERICS.md and the scalar
C code are normative and the meaning is checked against them; afterwards the meaning is normative
[P5 Summary]. (2) The numerics fault model runs **against the meaning**: mutate it (FMA contraction,
lane or tree change, RNE → truncate, a 127 → 128 clamp, a dropped scale, a tie flip) and record which
oracle kills each mutant [P2 §5.5–5.6]. Small mutants are invisible to tolerance oracles and are
caught only by the bit-exact corpus against the independently written C; large ones must be caught
by numpy and transformers. The kill table is the meaning's spec-strength record
([03-trust.md](03-trust.md)). (3) With `cr::` transcendentals, numpy's float64-then-round values
should match the meaning bit for bit except where double rounding misrounds, so "bit-exact
agreement rate plus explained mismatches" is sharper than the 1e-3 tolerance [inference]; with
`canon_v1::expf` (0.81% of inputs 1 ulp off [G04]) it stays tolerance based. (4) Independence is a
role property: the Author must not derive a meaning mechanically from the numpy reference (spec
escrow). (5) Where NUMERICS is weaker than code — activation quantisation's degenerate branches (§5),
MLA's absorbed form (tolerance only, NUMERICS §5.2), the future KDA form (§11) — the claim is a
tolerance claim. The honest claim is always "strong against fault model F, as judged by principals
P", never "correct" [P2 §5.5].

---

## 19. Status summary

Labels follow [../ROADMAP.md](../ROADMAP.md) §1 rule 7 (v0 = M1–M5, v1 = M6–M7).

| Capability | Status |
|---|---|
| `kernel fn` meanings, exact grade default, canon.v1 library, named reductions, canonical NaN | v0 (M2) |
| `par for` with proved disjoint writes; lowest-index failure rule | v0 |
| Projections; non-escaping closures/iterators in kernels; hot-loop lowering contract | v0 (M1; lowering contract M2) |
| Transcendental namespace rule (`cr::`, `canon_v1::`); `canon_v1::expf` | v0 (M2) |
| `format` types (Q4, Q8, F16, BF16, F32) with integer views and T2 overflow licences | v0 (M2) |
| Derived container parser and writer | v0 (M3, S2) |
| Schedules: DAG-preserving primitives, correspondence maps; T1 on transliterated intrinsics | v0 (M2; X2 spike at M0) |
| Object audit of the ~20 hot kernels; non-matching variants not dispatched | v0 (M2, DR-008) |
| MXFP4 native (format, integer path, `canon.v1.1` order) | later |
| Layout/tile algebra; certified relayouts | v0 where the port needs them (relayout space M2, prefill tiles M5); v1 otherwise (Forge relayout search M6) |
| Batched prefill schedules; exact int32 cross-thread partials | v0 (M5) |
| Block sparsity (static masks, dynamic block lists, typed gather) | v0 where the port needs it (M5); v1 otherwise |
| Flows; engine, simulator, bytes and timing handlers; shared policy code | v0 (M4–M5) |
| `timing_only` policies, hint ports, binary-level confinement, store-core certificate O1–O5 (`validated`) | v0 (M4) |
| `timing_blind` policies and exact replay bytes | v0 (M4) |
| Cost signatures, `mithc explain` | v0 (M2) |
| `mithc profile measure`, phys/emp/est tiers | v0 (M0 evaluator kit, X4) |
| Tiers NVMe/DRAM, residency types, placement checker (C2) | v0 (types M1; NVMe/DRAM tiers M4–M5; C2 from M4) |
| VRAM tier, `device(t)`, GPU placements | reserved |
| PTX expert tier (B2), cross-device corpus | owner-gated, by-trigger (D-06) |
| Fixed-chunk attention order; GPU attention | later (D-19; needs the by-trigger major version `canon.v2`) |
| `canon.v2` (major: fixed-chunk attention or explicit FMA; first use of the major-version migration protocol) | by-trigger |
| KDA meaning and chunk order; recurrent-state snapshot API | later (DR-025) |
| `real(bound)`, T3 tolerance certificates | reserved |
| `lossy` + `approx(profile)` approx/cache lane | reserved |
| NVFP4; NEON/SVE schedules | later / by-trigger (D-17) |
| `@bind(load)` code specialisation; direct x86 emitter (never for decode GEMV) | by-trigger (D-04, D-05; DR-009) |
| Visual-generation primitives | later (v2+), gated on a GPU backend (D-20) |

---

## 20. Open questions and reviewer notes

**Open questions** (each owned by an experiment, not by argument):
1. How many audited IEEE-exact rewrites does T1 need for zero false positives on compiler-emitted
   horizontal reductions and shuffles? (DR-008 census and X2.)
2. INT8 `mma` exactness on sm_120, and canonical GEMV speed against MMVQ on the RTX 5070 [G03].
3. The MXFP4 sub-block order for `canon.v1.1` (additive), and the fixed attention chunk size for
   the major version `canon.v2` (redefining, bit-exact goldens reset).
4. Recurrent vs chunkwise KDA as the canonical form, decided by both forms' cost signatures.
5. Accuracy and cost of a tighter `canon_v1::expf` (minimax plus a float-float step) [G04 open
   question 4].
6. Whether a CPU↔GPU round trip on WDDM costs ≲ 20 µs, which the gate configuration (experts plus Q8
   dense GEMVs and LM head on the GPU, attention core on the CPU, ~96 round trips per token) needs to
   reach the end-to-end 2x gate (§15.6). Measured in the G03 experiment alongside GEMV vs MMVQ.

**Reviewer notes** (on the canonical outline shared by all documents; decisions kept, problems
flagged):
- *DR-022 wording.* "GPU attention needs a fixed-chunk order first" is a performance and policy
  prerequisite, not a correctness one: canon.v1's sequential-in-t order is expressible exactly in
  PTX (one thread per (head, d)) but latency-bound at long context [G03 F8]. This document keeps
  the decision and says so (§15.4).
- *Canonical `acquire` snippet (resolved).* The outline's `acquire` returned `Frozen<SlabBuf>` with
  no `Result`, yet O5 requires an I/O failure to surface as `HX_E_IO`. The canonical snippet in
  [../ARCHITECTURE.md](../ARCHITECTURE.md) §5.3 now returns `Result<Frozen<SlabBuf>, IoError>`, as
  §12.1 does, and its corrected `q4_matvec` is the form printed in §2 (with §9's `q4_matmul`
  following it).
- *`nibbles<64, offset = 8>` in the `BlockQ4` snippet* parses like a Rust generic argument list with
  an associated-item constraint (`Trait<Item = T>`), which risks a false friend under DR-002. The
  Surface Lab should test it against an attribute or field-clause spelling.
- *The canonical `q4_matvec_avx512` schedule* hides the VNNI bias identity (Σ(u−8)x = Σux − 8Σx) and
  its use of `ActQ8.sum` inside `vectorize j using vpdpbusd`. Naming the rewrite explicitly (as P5's
  `rewrite isum = vpdpbusd_sum(..) - 8 * a.sum` did) would make the T2 obligation visible to agents.
- *The judges' small-M concern* (no K-split limits prefill parallelism at ~32 tokens per expert) does
  not hold on the CPU by the arithmetic in §9; exact int32 partials matter mainly for the GPU,
  tiny experts and skewed routing. The gap is nonetheless addressed as asked.
- *Two byte counts for the same token*: R08 gives 2.27 GB (cfg B, short context), R11 about 2.38 GB
  (container layout incl. ~0.11 GB KV). The headline ~34 tok/s ceiling uses R08; both are quoted.
- *The "approx/cache effect" of DR-024* is not a separate entry in the canonical effect list
  ([01-language.md](01-language.md)); this document maps it to the `lossy` authority effect plus the
  reserved `approx(profile)` grade (§16). Sibling documents should use the same mapping.
- *Keywords missing from Tier 0 (resolved).* DR-002 requires every new concept to be keyword-led
  and Tier 0 to list the keywords. `flow`, `store`, `hint port` and `certificate` (this document,
  §12.3; store, hint port and certificate v0 (M4), flow v0 (M4–M5)), `evolve slot` ([06-forge.md](06-forge.md)), `comptime` and `export abi`
  are now listed as contextual keywords with status labels in [../ARCHITECTURE.md](../ARCHITECTURE.md)
  §5.1, [01-language.md](01-language.md) §2.4 and the Tier 0 block and Lark `item` production of
  [05-agent-protocol.md](05-agent-protocol.md); `cached<T, Tier, budget>` joins the residency types
  of [../ARCHITECTURE.md](../ARCHITECTURE.md) §7.4 and [01-language.md](01-language.md) §4 (§14). The
  Surface Lab may still respell any of them as attributes or std items.
- *`emp` bounds are lower bounds on the roof.* The outline lets audited `emp` terms prune and
  quarantine (also [../ARCHITECTURE.md](../ARCHITECTURE.md) §7.5, [03-trust.md](03-trust.md) §7.4,
  [06-forge.md](06-forge.md) §5.3). A measured peak (AIDA64's 76.9 GB/s, Hearth's ~78 GB/s, a
  7.16 GB/s demand read against a 7.45 GB/s spec and a 7.877 GB/s link) can be beaten by a better
  kernel or I/O pattern, so quarantining against the raw peak would quarantine real wins — the
  failure [06-forge.md](06-forge.md) §5.3 warns about. The decision is kept, with `emp_bound =
  min(phys, max observed peak × (1 + h))`, h ≥ measurement CI + a declared margin (e.g. 5%); results
  between `emp_bound` and `phys` are flagged for audit, not quarantined; pruning uses `emp_bound`
  (§13.2). The D3-ii pilot shows why it matters: empirical peaks pruned 72% jointly against 66% for
  physical ones [RV: D3-ii]. *Resolved:* [../ARCHITECTURE.md](../ARCHITECTURE.md) §7.5,
  [03-trust.md](03-trust.md) §7.4 and [06-forge.md](06-forge.md) §5.3 adopt this definition and the
  "flag, not quarantine, between `emp_bound` and `phys`" rule, citing §13.2.
- *Cross-document consistency points (resolved except the last two).* The siblings now match this
  document on: the
  `restrict` attribution (§4; [../ARCHITECTURE.md](../ARCHITECTURE.md) §9.3 calls the 18 → 94 GMAC/s
  gap a schedule gap); fixed-chunk attention as the by-trigger major version `canon.v2`, not
  `canon.v1.1` (§5, §15.4; [../ARCHITECTURE.md](../ARCHITECTURE.md) §6.4 and §17); the
  residency-type spelling (§14); the status labels of [../ROADMAP.md](../ROADMAP.md) §1 rule 7
  (Conventions, §19); the MXCSR rule (§2); and the GPU bands with the split kill outcomes (§15.6;
  ROADMAP §5 M7, DR-022, [../ARCHITECTURE.md](../ARCHITECTURE.md) §13). Still to be carried into the
  siblings on their side: O4 hashing the canonical layout before relayout (§7.4, §12.4;
  [../ARCHITECTURE.md](../ARCHITECTURE.md) §7.3–7.4), and pinned staging for VRAM fills as a
  `std_platform` item ([04-toolchain.md](04-toolchain.md) §9).
