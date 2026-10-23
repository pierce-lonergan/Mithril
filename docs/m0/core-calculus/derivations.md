# Core-calculus note, appendix: hand derivations

Status: DRAFT, with [the note](../core-calculus.md). Rules cited by name are the note's §5 and §6.
Expected verdicts are repeated, keyed by snippet hash, in [verdicts.json](verdicts.json).
Revised 2026-10-16 after the first same-family review (note §17): the prelude, D-C2, D-C4, D-C5,
D-D01, D-D04, D-D06, D-D09, D-D11 to D-D13, D-D18, D-D19, D-D21 to D-D23, §N and §V changed. No
canonical verdict changed. Revised again 2026-10-16 after the second same-family review (note §0.6,
§17): the prelude (`BlockQ4`, `Lease`, `Clock`, `Buf<T>` declared; std higher-order transfers),
D-C2, D-C3, D-C5 (a fact corrected), D-D02, D-D04, D-D10, D-D11 (now `Cover-Proj`), D-D19, D-D21,
D-D22, D-D23, §N (N-40 to N-69) and §V changed. No canonical verdict changed. Revised a third time
2026-10-23 after the third same-family review (note §0.7, §17). These changed: the prelude
(`Iterator::next`'s per-position result loan, F-90); D-C2 (the hidden loop counter, F-103, and the
whole-cell strong update, F-89); D-D04 (the result loan of `max_by_key`, F-90, F-99); D-D11 (the
receiver premise of `Proj-Split`, F-102, pairwise disjointness, F-95, and the partial update of
`Cover-Proj`, F-89, F-97); D-D21 (whole cells); §N (N-43's code, F-107, and the new items N-70 to
N-109); and §V. No canonical or derived verdict changed. Revised again 2026-10-23 in the round-3
sync with `mithi` (note §0.8, F-114 to F-122): §N (N-110 to N-128) and §V. No canonical or derived
verdict changed. Revised again 2026-10-23 after the same-family review of that sync (note §0.9,
F-123 to F-134): §N (the new items N-129 to N-153, and N-110's and N-111's rationale, corrected by
F-134) and §V. No canonical or derived verdict changed.

Every snippet below was hashed by the CC track's scratch script on 2026-10-16, at Mithril commit
`ec46300` [M]. The hash is the SHA-256 of the fenced block's body (the lines between the opening
`mith` fence and the closing fence, joined with LF, with a final LF). Where a snippet occurs more than
once, the copies were compared after stripping `//` comments and normalising whitespace; all copies
listed as "comment-equal" matched [M, same script].

**Format of each derivation.** Source and hash; scope (`x1`, or out of X1 with the milestone);
elaborated MCore, abbreviated where a step repeats; the context; the judgement steps; every
obligation with how it is discharged; the computed facts; the verdict; and what fails without the
note's additions, where something does.

**Contents**

- [P. The canonical prelude](#p-the-canonical-prelude)
- [C. Canonical snippets](#c-canonical-snippets): D-C1 to D-C8
- [D. Derived snippets](#d-derived-snippets): D-D01 to D-D27
- [N. Negative items](#n-negative-items)
- [V. How `mithi` is compared with these derivations](#v-how-mithi-is-compared-with-these-derivations)

---

## P. The canonical prelude

The canonical snippets refer to declarations they do not contain. This prelude supplies them as
signatures. Its contents are assumptions of this note, not specifications taken from elsewhere, except
where a source is given. `mithi` is judged on "prelude plus snippet" (note §9, Owner question Q5). The
block uses a `text` fence on purpose, so that it is never mistaken for a canonical `mith` snippet.

Two declarations in the prelude are copies of declarations that snippets themselves make:
`format BlockQ4` (D-C1 and its copies) and `linear struct Lease` (D-D05). When an item's
snippet declares a name that the prelude also declares, the item is run with the prelude's copy of
that declaration omitted, so that it is not declared twice (§V). The second review found that the
first revision's prelude lacked `BlockQ4` and `Clock`, so that every item naming them was `E-TYPE`
when run on "prelude plus snippet", and its own `Store::lease` named the undeclared `Lease` (note
F-87).

```text
// ---------- std (signatures; bodies are std's) ----------
impl<T> [T] {
    fn len(&self) -> usize            ensures result <= isize::MAX as usize          // kcall
    fn iter(&self) -> slice::Iter<T>  // std adapter: result loan = the loan on *self (T-Ret (b))
    fn iter_mut(&mut self) -> slice::IterMut<T>   // result loan = the &mut loan on *self
}
// Iterator::next on slice::Iter<'a, T> and IterMut<'a, T>, and on adapters over them: the Some
// payload's position is tied to 'a inside the referent of &mut self, so it carries the loans the
// iterator carries, not the loan on the iterator (note §5.4's per-position rule, F-90). Option::take
// on Option<&'a mut T> likewise.
impl f16 { fn to_f32(self) -> f32 }   // exact widening; nanrule raw (01 §2.5 FF-F16)
mod canon {
    fn nan(x: f32) -> f32             // nanrule canon (02 §5)
    fn sum16(a: &[f32]) -> f32        // canon.v1 order (02 §5); nanrule raw
}
mod canon_v1 { fn expf(x: f32) -> f32 }    // fixed op-DAG (DR-014); its use for softmax is
                                           // provisional, pending D0-2
impl<T: ?Local + ?Linear> Option<T> {
    fn map<U, F: FnOnce(T) -> U>(self, f: F) -> Option<U>
        // θ_ret = α_self ⊔ Θ_f.θ_ret(α_self); θ_inv,f = α_self (f runs iff self is Some); at most once
        // (note §5.7 rule 2, F-70)
    fn ok_or<E>(self, e: E) -> Result<T, E>
    fn take(&mut self) -> Option<T>
}
impl u64 { fn checked_add(self, rhs: u64) -> Option<u64> }
trait Iterator {                      // ?Local on Self and Item (01 §5.4)
    type Item;
    fn next(&mut self) -> Option<Self::Item>
        // on an adapter that stores closure κ: θ_ret = α_self ⊔ Θ_κ.θ_ret(α_item), θ_inv = α_self
    fn filter<P: FnMut(&Self::Item) -> bool>(self, p: P) -> Filter<Self, P>      // lazy: stores κ_p
    fn max_by_key<B: Ord, F: FnMut(&Self::Item) -> B>(self, f: F) -> Option<Self::Item>
        // θ_ret = α_self ⊔ Θ_f.θ_ret(α_item); θ_inv,f = α_self; may_trap includes mt_f (F-69, F-70)
    fn map<U, F: FnMut(Self::Item) -> U>(self, f: F) -> Map<Self, F>            // lazy: stores κ_f
    fn sum<S>(self) -> S              // integer S only in exact context (FF-SUM: float sum, product, fold)
    // every other std higher-order method states θ_inv as note §5.7 rule 2 lists, or gets its default
}
struct Buf<T>;                        // an owned std buffer (note OP-1); Deref<Target = [T]> and
                                      // DerefMut: len, indexing and range slicing are <[T]>'s built-in
                                      // forms, so they are on C-EXACT-STD (note F-88)
struct Reverse<T>(pub T);             // std::cmp: reverses Ord
impl<T> From<T> for T { fn from(t: T) -> T }

// ---------- std_platform ----------
struct Hint<T>;
impl<T> Hint<T> { fn none() -> Hint<T>; fn some(x: T) -> Hint<T> }      // row ∅, total, ⊢_to-callable
struct Aligned<T, const N: u64>(T);   // Copy if T is; the value is a multiple of N
struct BlobFile;                      // capability type, affine (note C-CAP)
impl BlobFile {
    fn read_at(&self, off: Aligned<u64, 4096>, buf: &mut [u8]) -> Result<(), IoError>
        uses { io }
        requires buf.len() % 4096 == 0
        // θ_mut(buf) = (⊥, {self, off}, canon); may_trap false; Err only when e says fault
}
linear struct SlabBuf;                // 4096-aligned; length a multiple of 4096 (04 §9.2)
impl SlabBuf {
    fn bytes_mut(&mut self) -> &mut [u8]  ensures result.len() % 4096 == 0     // projection (mut)
    fn bytes(&self) -> &[u8]                                                     // projection (ref)
}
struct Frozen<T>;                     // Linear iff T is (note C-FROZEN); Send + Sync iff T is
impl Frozen<SlabBuf> { fn bytes(&self) -> &[u8] }                            // projection (ref)
struct Mutex<T: ¬Local>;
impl<T> Mutex<T> {
    fn with_lock<R, F: FnOnce(&mut T) -> R>(&self, f: F) -> R  uses { nondet }
        // R carries the implicit ¬Local bound; f's parameter is declared at the shared grade γ_sh;
        // θ_ret = Θ_f.θ_ret(γ_sh) ⊔ γ(f); θ_inv,f = ⊥ (f runs once, unconditionally) (note §5.7);
        // no θ_mut,self: f's writes through its &mut T go to the locked state, always read at γ_sh
}
enum IoError { … }                    // Copy
struct Clock;                         // capability type, affine (note C-CAP); used by N-13 and N-57
impl Clock { fn now_ns(&self) -> u64 uses { time, nondet } }                 // a time primitive

// ---------- Hearth-shaped declarations the snippets assume ----------
format BlockQ4 { d: f16, q: nibbles<64, offset = 8> }   // verbatim from D-C1; omitted when the item's
                                                         // own snippet declares BlockQ4 (note F-87)
struct ActQ8 { d: f32, sum: i32, #[range(-127..=127)] q: [i8; 64] }          // 01 §9.1; hx_act_q8
invariant ActQ8 { sum == q.iter().map(|v| *v as i32).sum::<i32>() }          // 01 §9.1
struct Matrix<B> { rows: usize, blocks_per_row: usize, blocks: Buf<B> }      // Buf<B>: the owned
                                                                             // std buffer above
invariant Matrix { blocks.len() == rows * blocks_per_row }                   // note F-3
impl<B> Matrix<B> {
    pub fn rows(&self) -> usize            ensures result == self.rows
    pub fn blocks_per_row(&self) -> usize  ensures result == self.blocks_per_row
    pub fn cols(&self) -> usize            ensures result == self.blocks_per_row   // D-D11
    pub fn row(&self, r: usize) -> &[B]    // as 01 §5.3: derivation D-D02
}
impl IndexMut<usize> for Matrix<f32> {
    fn index_mut(&mut self, t: usize) -> &mut [f32]
        requires t < self.rows
        ensures footprint(result) == self.blocks[t * self.blocks_per_row .. (t + 1) * self.blocks_per_row]
        // a declared footprint (note §5.6, F-25). Assumed body: &mut self.blocks[t*bpr .. (t+1)*bpr],
        // which writes nothing and reads only rows, blocks_per_row and the footprint, so E-FOOTPRINT is discharged
        // by T2 at the definition (F-45); never checked at run time
}
#[derive(Copy, Clone)] struct SlotId(u32);
#[view] #[derive(Copy, Clone)] struct Tick(pub u64);  // #[view]: (t3) needs it for pick_victim's `now`
                                                      // (the first prelude omitted it; review R2-21)
#[view] #[derive(Copy, Clone)]
struct SlotView { pub id: SlotId, pub idx: usize, pub pinned: bool, pub refs: u32, pub last_use: Tick }
#[derive(Copy, Clone)] struct ExpertId(u32);
#[derive(Copy, Clone)] struct ExpertKey(u32);

mod store {                           // mith.toml: declare_deterministic = ["store"] (01 §11)
    pub struct Store { state: Mutex<StoreState>, … }
    struct StoreState { count_f: Buf<f32>, … }
    impl StoreState { fn touch(&mut self, k: ExpertKey) }                     // row ∅
    linear struct Lease { slot: SlotId, slab: Frozen<SlabBuf> }  // verbatim from D-D05; it and the
    impl Lease { pub fn bytes(&self) -> &[u8] }                  // impl are omitted for D-D05, whose
                                                                 // snippet declares both (note F-87)
    impl Store {
        fn acquire_inner(&self, id: ExpertId) -> Result<Frozen<SlabBuf>, IoError>
            uses { io, spawn, nondet }                                        // may_trap false
        pub fn lease(&self, id: ExpertId) -> Result<Lease, IoError>  uses { io, spawn }
        pub fn release(&self, l: Lease)                                uses { io, spawn }
        pub fn n_heat(&self) -> usize
    }
    // read_slab, acquire (D-C5), heat_into (D-D22), note_use (D-D06) and expert_step (D-D05) live
    // here; the prelude's Lease above is D-D05's declaration
}
kernel fn ffn_q4(w: &[u8], x: &[f32], y: &mut [f32])         // D-D05; no requires assumed
struct ExpertEntry { offset: u64, nbytes: u64 }
enum FormatError { Overflow { entry: usize }, OutOfBounds { entry: usize } }
struct GBps; struct Measured; struct Simulated;
struct Quantity<U, O>(f64);           // phantom U and O; Copy; Add only for equal U and equal O
struct MachineProfile { pub dram_read_all_core: Quantity<GBps, Measured>, … }
fn snippet_c7(profile: &MachineProfile) { /* D-C7's two lines are this body */ }

// ---------- declarations outside MCore ----------
evidence golden::scheduling_independence { kind: deterministic, subject: store::acquire, grade: tested }
                                      // an X1 fixture standing in for the ledger fact (note §12). The
                                      // subject is one definition whose whole body is the det block,
                                      // resolved to acquire's content hash at admission; the first
                                      // prelude's glob `store::*` is withdrawn (F-33)
schedule q4_matvec_avx2 for q4_matvec on x86_64(avx2) { … }          // D-C6 refers to it
seam hearth_c_ref { fn mm_q4_avx512; fn forward_token; }              // external C reference symbols
target x86_64 features { avx2, avxvnni, avx512f, avx512bw, avx512vl, avx512vnni, avx512bf16 }
```

The `hx_quant.h` layouts at Hearth `b5d3f14` agree with the prelude's `ActQ8` and the derived
`BlockQ4`: `hx_act_q8 { float d; int32_t sum; int8_t q[64]; }` (72 bytes) and
`hx_block_q4 { uint16_t d; uint8_t qs[32]; }` (34 bytes; byte j holds element j in its low nibble
and element j+32 in its high nibble, stored as q+8) [M, CC track: read 2026-10-16].

---

## C. Canonical snippets

### D-C1: `format BlockQ4`

- **Source.** docs/ARCHITECTURE.md:456–462, `5db323b4af93942911bb28d9aa77d77c1665b8d6bee334f5a5251e4d46daf3ec`.
  The same hash at 01-language.md:291–297 and 02-compute.md:344–350 [M].
- **Scope.** x1.

**Elaboration** (`⊢_fmt`, note §5.14):

```text
struct BlockQ4 { d: f16, q: Nib64o8 }                  // size_of == 34: 2 bytes + 64·4/8 = 32 bytes [D]
struct Nib64o8 { b: [u8; 32] }
impl Nib64o8 {
    fn elem(&self, i: usize) -> i32  requires i < 64  ensures -8 <= result && result <= 7 {
        let raw: u8 = if i < 32 { self.b[i] & 0x0F } else { self.b[i - 32] >> 4 };
        (raw as i32) - 8
    }
}
```

**Obligations of `elem`.**

| # | Site | Obligation | Facts used | Discharged |
|---|---|---|---|---|
| 1 | `self.b[i]` | `i < 32` | branch condition `i < 32` | T2 |
| 2 | `i - 32` | no `usize` underflow | `¬(i < 32)` | T2 |
| 3 | `self.b[i - 32]` | `i - 32 < 32` | `i < 64` (requires) | T2 |
| 4 | `(raw as i32) - 8` | no `i32` overflow | `raw ≤ 15` (mask or shift of a `u8`) | T2 |
| 5 | ensures | `-8 ≤ result ≤ 7` | `0 ≤ raw ≤ 15` | T2 |

**Facts.** `elem`: row ∅; `may_trap` false under its requires; ν canon (integer); `kcall` holds.
Context: exact when called from a kernel.

**Verdict: accept.** FF-Q4 holds by construction: the high nibble is element j+32, not llama.cpp's
j+16. The spelling `nibbles<64, offset = 8>` is parsed as a format field code, not as a Rust generic
argument list; 02 §20 asks the Surface Lab to test it.

### D-C2: `q4_row_dot` and `q4_matvec`

- **Source.** docs/ARCHITECTURE.md:469–492, `d091a2e613220315d25f277750dc63a12305bb91acfcbbaea0ca75e9535abdea`.
  Same hash at 02-compute.md:104–127. Comment-equal: 01-language.md:787–802 (`q4_row_dot`,
  `9f5d0d3a…`), 01-language.md:387–393 (`q4_matvec`, `bfad207b…`), and README.md's `q4_row_dot` [M].
- **Scope.** x1.

**Elaboration of `q4_row_dot`** (note §3.2):

```text
kernel fn q4_row_dot(w: &[BlockQ4], a: &[ActQ8]) -> f32  requires w.len() == a.len() {
  let mut acc: f32 = 0.0;
  let mut c_g: usize = 0;  let n_g: usize = <[BlockQ4]>::len(&*w);     // c_g: hidden counter (F-103)
  loop {
    if c_g >= n_g { break }
    let g: usize = c_g;                              // the binder: immutable, one per iteration
    let mut isum: i32 = 0;
    let mut c_j: usize = 0;
    loop {
      if c_j >= 32 { break }
      let j: usize = c_j;
      // isum += w[g].q.elem(j) * (a[g].q[j] as i32);
      assert⟨idx⟩(g < len(*w));  assert⟨req(elem)⟩(j < 64);
      let t1: i32 = Nib64o8::elem(&(*w)[g].q, j);
      assert⟨idx⟩(g < len(*a));  assert⟨idx⟩(j < 64);
      let t2: i32 = prim_cast_i8_i32(copy (*a)[g].q[j]);
      assert⟨ovf(mul)⟩(no_ovf_mul_i32(t1, t2));     let p1 = prim_mul_i32(t1, t2);
      assert⟨ovf(add)⟩(no_ovf_add_i32(isum, p1));   isum = prim_add_i32(isum, p1);
      // isum += w[g].q.elem(j + 32) * (a[g].q[j + 32] as i32);
      assert⟨ovf(add)⟩(no_ovf_add_usize(j, 32));    let j2: usize = j + 32;
      … the same five steps with j2 …
      c_j = c_j + 1;                                 // its overflow assert is discharged: c_j < 32
    }
    let c: f32  = prim_cvt_i32_f32(isum);           // round to nearest even
    let dw: f32 = prim_cvt_f16_f32(copy (*w)[g].d);  // exact
    let da: f32 = copy (*a)[g].d;
    let s: f32  = prim_fmul32(dw, da);              // w[g].d.to_f32() * a[g].d
    let t: f32  = prim_fmul32(c, s);                // (isum as f32) * (…)
    acc = prim_fadd32(acc, t);                      // two roundings, never contracted (FF-FMA)
    c_g = c_g + 1;
  }
  return prim_canon_nan(acc)
}
```

**Context.** Δ = prelude. `Γ0 = { w : (&[BlockQ4], α_w, own), a : (&[ActQ8], α_a, own) }`. `Σ = ∅`.
`Φ0 = { len(*w) == len(*a) }` ∪ `{ (*a)[k].q[m] ∈ [−127, 127] }` (field range) ∪ `{ (*a)[k].sum == Σ (*a)[k].q }`
(invariant) ∪ `{ len(*w), len(*a) ≤ isize::MAX }`. `pc = ⊥`. `ctx = exact`.

**Judgement steps.**

1. `T-Let`: `acc : (f32, ⊥ with ν canon)`, from the literal `0.0`.
2. `T-Loop` (outer) with `T-Jump`. The guard's `break_L` is decided under the grade of `c_g >= n_g`,
   which is `α_w` (the length of `*w`), so `J(L) = α_w`, and by `T-Loop`'s fixpoint every iteration's
   body runs under the effective pc `α_w` (note §5.5, F-30). The first draft asserted this step
   without a rule that produced it.
3. `T-Loop` (inner). The guard `c_j >= 32` is constant, so `J(L_inner) = ⊥`; the inner body's effective
   pc stays `α_w`, because `J(L)` of the outer loop is still open.
4. `T-Call` of `Nib64o8::elem`: a format accessor; `ε = ∅ ⊆ Σ`; its requires `j < 64` is discharged;
   its ensures `t1 ∈ [−8, 7]` joins Φ.
5. `T-Prim` for the cast, the multiplication and the addition: no labels; every assert is discharged
   (table below).
6. `T-Prim` for the float operations: `fid = exact`, `taint = ⊥`, `nanrule = raw`. `acc`'s grade becomes
   `α_w ⊔ α_a` with ν raw.
7. `T-Return`: `prim_canon_nan(acc)` has ν canon and grade `α_w ⊔ α_a`. `ρ` and `ω` are joined under
   `pc = ⊥`, so `ω = ⊥`.
8. `T-Fn` with `⊢_k`, checked below.

**Obligations of `q4_row_dot`.**

| # | Site | Obligation | Facts used | Discharged |
|---|---|---|---|---|
| 1 | `w[g]` | `g < len(*w)` | `g = c_g < n_g = len(*w)` (outer loop) | T2 |
| 2 | `a[g]` | `g < len(*a)` | 1 and `len(*w) == len(*a)` (requires) | T2 |
| 3 | `elem(j)` | `j < 64` | `j < 32` | T2 |
| 4 | `a[g].q[j]` | `j < 64` (array of 64) | `j < 32` | T2 |
| 5 | `j + 32` | no `usize` overflow | `j < 32` | T2 |
| 6 | `elem(j + 32)`, `q[j + 32]` | `j + 32 < 64` | `j < 32` | T2 |
| 7 | both multiplications | the product fits `i32` | `t1 ∈ [−8, 7]` (ensures), `t2 ∈ [−127, 127]` (range), so `\|p\| ≤ 1,016` [D: 8 · 127] | T2 |
| 8 | the 64 additions to `isum` | no `i32` overflow | over SSA versions (note §5.10, F-44): `isum_0 = 0` and `\|isum_k\| ≤ 1,016 · k ≤ 65,024` [D: 64 · 8 · 127] for the k-th version | T2, by unrolling the constant 32-trip inner loop (two additions per trip); no loop invariant is needed or inferred (DR-012) |
| 9 | `c_j = c_j + 1` | no overflow | `c_j < 32` | T2 |
| 10 | `c_g = c_g + 1` | no overflow | `c_g < len(*w) ≤ isize::MAX` | T2 |

Not an obligation: `|isum| < 2^24`, which makes `isum as f32` exact. The cast is defined (round to
nearest even) for every `i32`, so typing does not need the bound. It holds anyway, since 65,024 <
16,777,216 [D], and the schedule's licence argument uses it (D-C3).

**Facts of `q4_row_dot`.** Row ∅. `may_trap` false. `θ_ret = (⊥, D = {w, a}, canon)`. `ω = ⊥`.
Context exact.

**`⊢_k q4_row_dot`.**

- (k1) row ∅.
- (k2) every assert is discharged (obligations 1–10).
- (k3) callees: `<[T]>::len` (`kcall`), `Nib64o8::elem` (a format accessor), and integer, cast,
  float and `canon::nan` primitives, all admissible in exact context.
- (k4) the result is `(exact, cross_device)` whenever its inputs are, with ν canon, and `ω = ⊥`.
- (k5) the sequential float accumulation is an explicit loop, not `.sum()`. There is no `max_by`, no
  transcendental, and no `f16` arithmetic, only widening. `a * b + c` patterns keep their two
  roundings (FF-FMA is C).
- (k6) no `det`, no `Mutex`, no capability.

**Elaboration of `q4_matvec`.**

```text
kernel fn q4_matvec(w: &Matrix<BlockQ4>, a: &[ActQ8], y: &mut [f32])
    requires y.len() == w.rows() && a.len() == w.blocks_per_row() {
  par r in 0..Matrix::rows(&*w) {
    assert⟨req(row)⟩(r < rows(*w));
    let wr: &[BlockQ4] = Matrix::row(&*w, r);        // T-Proj: a shared loan on *w, ends after the call
    assert⟨req(q4_row_dot)⟩(len(*wr) == len(*a));
    let v: f32 = q4_row_dot(wr, &*a);
    assert⟨idx⟩(r < len(*y));
    (*y)[r] = v;
  }
}
```

**Obligations of `q4_matvec`.**

| # | Site | Obligation | Facts used | Discharged |
|---|---|---|---|---|
| 1 | `w.row(r)` | `r < rows(*w)` | `r ∈ [0, rows(*w))` (par range) | T2 |
| 2 | `q4_row_dot(…)` | `len(*wr) == len(*a)` | `row`'s ensures `len(result) == bpr(*w)`, and the requires `len(*a) == bpr(*w)` | T2 |
| 3 | `y[r]` | `r < len(*y)` | `len(*y) == rows(*w)` (requires) | T2 |
| 4 | `Matrix::row` itself | `kcall(Matrix::row)` | the `Matrix` invariant (D-D02), and `Buf<T>`'s slicing being the built-in one on C-EXACT-STD (F-88) | — |

**`T-Par`.**

- W = `{ (*y)[r] }` with `π = id`, which is injective.
- No place in W is read.
- The shared captures `w` (a `&Matrix<BlockQ4>`, where `Matrix<BlockQ4>` is plain data and `Sync`) and
  `a` (a `&[ActQ8]`, `Sync`) are read-only.
- The written element type `f32` is `Send`.
- There is no `break`, and the exercised row is ∅ (`q4_row_dot` and `Matrix::row` have row ∅ and call
  no closure; F-36).
- No iteration can return early, so the early-return grading of W (F-38) does not apply.
- `pc' = α_w`, the grade of `rows(*w)`.

**`T-Cover`** (note §5.9, with premise 0 of F-37).

0. The surface body (`y[r] = q4_row_dot(w.row(r), a);`) contains no `break`,
   `continue`, `return` or `?`. Its only possible exits are traps, and it has none: every assert is
   discharged.
1. The body is the one write `(*y)[r] = …`, a statement at the top level of the surface body, with
   no `if` or `match` before it (the call to the kernel `q4_row_dot` cannot exit early).
2. `Φ ⊢ rows(*w) == len(*y)`.
3. No other write to `*y`: no other element, no whole-`y` write, no `&mut` of `*y` or of any place
   overlapping it passed to a call, and no closure.
4. `target*((*y)[r])` is one place: `*y` is the referent of the reference parameter y (must-alias,
   F-64), whose type `[f32]` holds no reference.

The index r is the `par for`'s binder, a plain identifier without `mut`, never shadowed (premise 1,
F-103). `*y` is a whole grade cell, so the strong update replaces the cell (note §5.4, F-89). The
referent of `y` becomes `(exact, cross_device-if-inputs-are, {}, canon) ⊔ α_w`, and
`θ_mut,y = (⊥, {w, a}, canon)`: the output does not depend on y's old contents. `T-Par`'s
pairwise premise has one write, `(*y)[r]` with index function `r`, so it holds affinely (F-95).

**`⊢_k q4_matvec`.** (k1)–(k6) hold. The sink `y` is canonical by `T-Cover`.

**Verdict: accept.** Both kernels; row ∅; `may_trap` false.

**Without the note's additions.**

- Without `T-Cover`, y's element grade is the weak join `α_y ⊔ (… canon)`. A caller's `y` is raw in
  general, so ν = raw ⊔ canon = raw. If the sink check reads y's final contents, it fails here with
  `E-NAN-RAW-SINK`. If it checks only the values written, `q4_matvec` passes, but its transfer
  `θ_mut,y` keeps a dependency on the old `y`, and the error appears at the next exact sink that
  receives `y` (F-1).
- Without the `Matrix` invariant, `Matrix::row`'s slice bound is a runtime assert, `kcall` fails, and
  `⊢_k q4_matvec` fails (k3) with `E-KERNEL-CALL` (F-3).

### D-C3: `schedule q4_matvec_avx512`

- **Source.** docs/ARCHITECTURE.md:499–505, `96901256fa8cf920e54e1d0eac489aaae67c8f56214cdb55e866b4f134539f99`.
  Comment-equal: 02-compute.md:452–458 (`b9c51b0c…`) [M].
- **Scope.** x1, front end only. Soundness is T1 at M2.

**`⊢_sch`** (note §5.14):

- (s1) `q4_matvec` is a kernel fn (D-C2), and the target `x86_64(avx512f, avx512bw, avx512vnni)` names
  catalogue features (prelude).
- (s2) Name resolution, own scope first (note §5.14, F-2, F-86). `r` and `w` resolve in
  `q4_matvec`'s own scope (the `par` variable and the parameter), so they are not looked up further.
  `j` and `acc` are not bound there; after inlining `q4_row_dot` each is bound exactly once in the
  inlined nest, so each is accepted. `q4_row_dot`'s own parameter `w` is never consulted, because
  `w` resolved in the first step, so `prefetch w` is unambiguous. Under a rule that searched only
  `q4_matvec`'s scope, `j` and `acc` would be unresolved; under "unique anywhere in the nest", which
  is how the first revision's (s2) read, `w` would be ambiguous.
- (s3) Primitives and their licences:
  - `tile r by 16`: exact.
  - `vectorize j using vpdpbusd`: int_assoc. It emits T2 obligations for M2. With unsigned stored
    nibbles `u = elem + 8 ∈ [0, 15]` and activations `x ∈ [−127, 127]`, every partial sum in any order
    is bounded by `Σ|u·x| ≤ 64 · 15 · 127 = 121,920 < 2^31` [D]. The bias identity
    `Σ(u − 8)·x = Σu·x − 8·Σx` holds over ℤ, with `Σx = a[g].sum` by the `ActQ8` invariant (02 §7.2).
  - `keep_order acc`: exact; it asserts that the float epilogue chain is untouched.
  - `prefetch w ahead 2 blocks`: timing only. Two `BlockQ4`s are 68 bytes [D: 2 · 34], which
    ARCHITECTURE §5.3's reviewer note already calls too short to matter; it is kept only if measured.
- (s4) No rejected primitive.

**Verdict: accept** (front end). `mithi` checks `⊢_sch` and cannot run T1.

### D-C4: `policy fn pick_victim`

- **Source.** docs/ARCHITECTURE.md:512–523, `36cc4697c6eba3789903caa8049d40093890e31a1c7ab987c222316034c74147`.
  Same hash at 01-language.md:1080–1091, 02-compute.md:715–726 and 03-trust.md:513–524.
  Comment-equal: README.md's `pick_victim` [M].
- **Scope.** x1.

**Elaboration.**

```text
policy fn pick_victim(slots: &[SlotView], now: Tick) -> Hint<SlotId> {
  let mut best: Hint<SlotId> = Hint::none();
  let mut best_age: u64 = 0;
  let mut i: usize = 0;  let n: usize = <[SlotView]>::len(&*slots);
  loop {
    if i >= n { break }
    let s: &SlotView = &(*slots)[i];                   // built-in projection; i < n discharges the bound
    if (if copy (*s).pinned { true } else { copy (*s).refs > 0 }) { i = i + 1; continue }
    assert⟨ovf(sub)⟩(copy now.0 >= copy (*s).last_use.0);   // NOT dischargeable (no fact relates them)
    let age: u64 = prim_sub_u64(copy now.0, copy (*s).last_use.0);
    if age > best_age { best_age = age; best = Hint::some(copy (*s).id); }
    i = i + 1;
  }
  return move best
}
```

**Context.** `Γ0 = { slots : (&[SlotView], γ_sh, own), now : (Tick, γ_sh, own) }`: views have the
fixed shared grade (note §5.13). `Σ = ∅`. `ctx = timing_only`.

**Judgement steps.**

1. `T-Call` `Hint::none()`: std, row ∅.
2. `T-Loop` over a core-provided slice: (t5). The `continue` is decided under the grade of
   `s.pinned || s.refs > 0`, which is `γ_sh`, so `J(L) = γ_sh` (`T-Jump`); `best` and `best_age`
   were `γ_sh` already.
3. `T-Proj` for `&(*slots)[i]`: a shared loan on `(*slots)[i]`, ending at the last use of `s` in the
   iteration.
4. `T-Copy` for the `Copy` fields read through `s`.
5. `T-Assert` for the subtraction: not discharged. The site `ovf(sub)` stays, so `ω ⊔= γ_sh`.
6. `T-If` with the strict `>`: the first maximum, which is the lowest index, is kept. That is the
   comment "ties: lowest index wins", read off the serial loop order.
7. `T-Return`.

**`⊢_to`.**

- (t1) row ∅.
- (t2) the result is `Hint<SlotId>`.
- (t3) `SlotView` and `Tick` are `#[view]`, `Copy` and payload-free. This is a prelude condition: the
  first prelude declared `Tick` without `#[view]`, so (t3) failed for `now` (review item R2-21); the
  code for a (t3) failure is now `E-TO-PARAM`.
- (t4) no state block.
- (t5) one loop, over `slots`; no recursion. `fuel(P) = n_slots + c` [D: one back edge per
  iteration, plus a constant c], within 02 §12.3's illustrative port budget `fuel(4 * n_slots)`
  whenever `n_slots ≥ c/3`, so `W-FUEL` is not raised for any realistic slot count.
- (t6) no `det`, no `Mutex`, no capability, no closure.
- (t7) the callees are `Hint::none`, `Hint::some`, `<[T]>::len` and integer primitives.
- (t8) `may_trap` true: the subtraction.
- (t9) `S(P)`: one frame with three scalars, one `Hint<SlotId>` and the loop variables, no callees
  with frames of their own other than `Hint::some`, `Hint::none` and `len`. The number of bytes is a
  property of the lowering and is not computed here.

**Facts.** Row ∅. `may_trap` true, at the trap site `ovf(sub)`. Result grade `γ_sh`. No sink
requirement applies.

**Dynamic behaviour.** If `last_use` is ever ahead of `now`, the assert fails, the trap ends the port
call's domain (`E-Domain`), and the port takes its fallback's decision plus a strike (`E-Port-Fail`).
This is exactly 01 §12.5's example.

**Verdict: accept.**

### D-C5: `read_slab` and `acquire`

- **Source.** docs/ARCHITECTURE.md:529–542, `38b13b20c0fa73dbc084000dede930770e06d2219141b152a9131f1ab2cff5b9`.
  Same hash at 01-language.md:612–625. Comment-equal: 02-compute.md:942–947 (`read_slab`,
  `646242d0…`) and 03-trust.md:277–283 (`acquire`, `c47e32d8…`) [M].
- **Scope.** x1.

**`read_slab`.**

```text
fn read_slab(file: &BlobFile, off: Aligned<u64, 4096>, buf: &mut SlabBuf) -> Result<(), IoError>
    uses { io } {
  let b: &mut [u8] = SlabBuf::bytes_mut(&mut *buf);     // T-Proj: a mutable loan on *buf
  assert⟨req(read_at)⟩(len(*b) % 4096 == 0);           // discharged by bytes_mut's ensures
  return BlobFile::read_at(&*file, copy off, b)          // ε = {io} ⊆ Σ = {io}; κ_io passed
}
```

- **Steps.** `T-Proj` (mode mut), `T-Call` with the capability check `{io} ⊆ {io}`, `T-Return`. The
  loan on `*buf` ends when `read_at` returns; nothing else touches `*buf` meanwhile. `b` is a local
  reference carrying the projection loan on `*buf`, so `read_at`'s `θ_mut` lands on `*buf` through
  `target*` (note §5.4, F-39), not on `b`; the first draft's `root(·)` would have updated `b`.
- **Facts.**
  - Row `{io}`, declared, and equal to the inferred row.
  - `may_trap` false.
  - `θ_ret = (⊥, {file, off}, canon)`. `io` on a `BlobFile` adds no taint (01 §6.1). The Ok/Err
    discriminant depends on the environment, which Theorem 4's non-failing condition (c) covers (F-5).
  - `θ_mut,buf = (⊥, {buf, file, off}, canon)`. The bytes `read_at` writes are a function of the file
    and the offset, but the call reaches `*buf` through the projection result `b`, which `T-Call`'s
    strong case does not cover (it needs an argument that borrows one whole place, and nothing
    declares that `bytes_mut`'s result covers all of `*buf`), so the update is a weak join and buf's
    old grade stays in D (note F-78). The previous revisions stated `(⊥, {file, off}, canon)`, which
    needed a strong update that no rule gave; the second review's R3-18 led to the correction. It is a
    secondary fact: `read_slab` has no sink, and no verdict depends on it. A footprint
    `ensures footprint(result) == *self` on `bytes_mut` would make the update strong.
- **Verdict: accept.**

**`acquire`.**

```text
fn acquire(store: &Store, id: ExpertId) -> Result<Frozen<SlabBuf>, IoError> uses { io, spawn } {
  return det[golden::scheduling_independence] { Store::acquire_inner(&*store, copy id) }
}
```

**`T-Det` premises.**

1. `module(acquire) = store ∈ grants.declare_deterministic = ["store"]`. This is a condition: the
   snippet does not say which module it is in; the prelude places it in `store`.
2. `acquire` is not a policy, and no policy reaches it.
3. `golden::scheduling_independence` is admitted and current, of kind `deterministic`, and its subject
   is `store::acquire`, whose entire body is this block, resolved to `acquire`'s content hash at
   admission (note §5.11, F-33). This is a condition: at X1 it is a hash-pinned fixture (note §12).
   The first prelude's subject was the glob `store::*`, which the revised rule rejects.
4. The result type `Result<Frozen<SlabBuf>, IoError>` contains no closure type and is not `Local`
   (`E-DET-RESULT`, F-34).

**Body**, under `Σ ∪ {nondet} = {io, spawn, nondet}`. `acquire_inner`'s row `{io, spawn, nondet}` is
a subset (prelude). Its result grade is `α_store ⊔ α_id ⊔ taint(nondet)`, that is
`(exact, ⟨sd, cd⟩, ∅, canon) ⊔ α_store ⊔ α_id`.

**Conclusion.**

- The result's schedule component is recomputed from the block's free inputs, `store` and `id`:
  `d_s^in = α_store.d_s ⊔ α_id.d_s` (note §5.11, F-32). The scope is therefore
  `⟨α_store.d_s ⊔ α_id.d_s, cd⟩ ⊔ pc.d`, which is `cross_device` exactly when the inputs are. The
  first draft wrote the same words, "cross_device if the inputs are", but its mask gave `cd` whatever
  the inputs were; the revised rule is what makes the sentence true.
- `B = {golden::scheduling_independence}`.
- `ε = {io, spawn, nondet} \ {nondet} = {io, spawn}`, which is a subset of the declared row and equal
  to it.
- The result type `Result<Frozen<SlabBuf>, IoError>` is not `Local`. `Frozen<SlabBuf>` is Linear
  (C-FROZEN), and returning it consumes it.

**Facts.** Row `{io, spawn}`. `may_trap` false (prelude: `acquire_inner` reports I/O faults as `Err`,
O5). Every value-level claim downstream meets `grade(golden::scheduling_independence) = tested`
(03 §3.3).

**Verdict: accept**, under conditions 1 and 3 and the prelude signature of `acquire_inner`.

### D-C6: `spec q4_matvec_claims`

- **Source.** docs/ARCHITECTURE.md:549–555, `e0aea59febaf2aa4947977e8d8582a4cc4c70838acab8cc7fd5330b7845ba057`.
  Same hash at 01-language.md:877–883 and 03-trust.md:76–82. Comment-equal: ROADMAP.md:65–71
  (`c57e441b…`; indented inside a list) [M].
- **Scope.** x1, front end only.

**`⊢_spec`.**

- (p1) `q4_matvec` resolves (D-C2) and `q4_matvec_avx512` resolves (D-C3). `q4_matvec_avx2` resolves
  only through the prelude stub: a condition. `hearth_c_ref::mm_q4_avx512` resolves in the declared
  seam namespace.
- (p2) The kinds `refines`, `refines` and `perf` are valid.
- (p3) `validated` is on the correctness scale, for `refines`; `measured` is on the performance scale,
  for `perf`.
- (p4) `refines` on a kernel slot admits `validated`. `perf ... noninferior(to: …, margin: …)` admits
  `measured`.
- (p5) `margin: 3%` is a `Ratio`, a [target] (DR-018).

**Verdict: accept** (front end), under the conditions on `q4_matvec_avx2` and the seam namespace.
Sealing and Author ownership are M3 ledger rules (03 §8). Whether `validated` is an INV-VERIFY
evidence class is provisional, pending D0-11.

### D-C7: `Quantity` and a typed hole

- **Source.** docs/ARCHITECTURE.md:561–565, `15ff8fa9afbfddc2d3902d9b6d4e6d357dbc930f72dfc71087adb792d3d3d12b`.
  Comment-equal parts: 01-language.md:306–308 and 02-compute.md:840–842 (`371b1cd0…`, the `Quantity`
  line), and 01-language.md:220 (`33ecc757…`, the hole) [M].
- **Scope.** x1. Checked as the body of the prelude's `snippet_c7(profile: &MachineProfile)`.

**Elaboration.**

```text
let bw: Quantity<GBps, Measured> = copy (*profile).dram_read_all_core;  // Quantity is Copy; the types match
let score: α = trap(hole("eviction_score"));                             // T-Hole at a fresh α
```

**Steps.** `T-Let` with `T-Copy`, then `T-Let` with `T-Hole`. α is never constrained in the fragment.
It defaults to the pinned edition's never-type fallback type, and the item is accepted either way
(F-23; which type that is has not been verified here).

**Facts.** Row ∅. `may_trap` true, at the trap site `hole("eviction_score")`.

**Verdict: accept.**

### D-C8: README "A taste"

- **Source.** README.md:54–80, `4f4bc27e56fa507162b630696fea46a4333d5b580683ed4eaa8cadf1b75a3fa5`.
- **Scope.** x1.

After stripping comments, the block's two functions are identical to ARCHITECTURE's `q4_row_dot`
(D-C2) and `pick_victim` (D-C4) [M]. The derivations are those.

**Verdict: accept** (`q4_row_dot`: kernel, row ∅, `may_trap` false; `pick_victim`: policy, row ∅,
`may_trap` true).

---

## D. Derived snippets

### D-D01: `trait Dequant`, `first_value`

- **Source.** 01-language.md:276–284, `69dab4ebdb91c1d47f71c2b1d2fb3212f78b8e6be54756bb2077013337968e72`.
- **Scope.** x1, the traits arm.

```text
trait Dequant { fn scale(&self) -> f32;  fn elem(&self, i: usize) -> i32; }      // rows absent = ∅
fn first_value<B: Dequant>(b: &B) -> f32 {
  return prim_fmul32(Dequant::scale::<B>(&*b), prim_cast_i32_f32(Dequant::elem::<B>(&*b, 0)))
}
```

- **Steps.**
  - J12: B is bounded by `Dequant` and carries the implicit `¬Local` bound.
  - `T-Call` on a type parameter uses `ε_m = ∅` and `Θ̂_m(γ̄) = ⨆γ̄`, with ν raw for `scale` and the
    observer set O = all parameters (note §5.12, F-50): if a caller passes a `B` whose float content
    is raw, `elem`'s integer result may carry the observer taint, because an impl may observe it.
  - `T-Prim` for the cast and the multiplication.
- **Facts.** Row ∅. `may_trap` is conservatively true: it is not part of trait signatures, so the
  generic definition's summary cannot know; each monomorphic instance has its own. Result
  `(⊥, {b}, raw, O = {b})`.
- **Verdict: accept.** The commented `first_dyn` is item N-01.

### D-D02: `Matrix::row`

- **Source.** 01-language.md:363–376, `ec3ce489251878ad0200ed973bf6ab4b9212ea0e322155ee6ff4b5ceb79e0666`.
- **Scope.** x1.

```text
pub fn row(&self, r: usize) -> &[B]  requires r < self.rows()  ensures result.len() == self.blocks_per_row() {
  let bpr = copy (*self).blocks_per_row;
  assert⟨ovf(mul)⟩(no_ovf(r * bpr));  assert⟨ovf(add)⟩(no_ovf(r + 1));  assert⟨ovf(mul)⟩(no_ovf((r + 1) * bpr));
  assert⟨slice⟩(r * bpr <= (r + 1) * bpr && (r + 1) * bpr <= len((*self).blocks));
  return &(*self).blocks[r * bpr .. (r + 1) * bpr]       // a built-in projection of *self
}
```

- **Steps.** By `T-Ret` (a), `row` is a projection on the receiver: the receiver is `x★` by elision,
  and the result's loan is on a sub-place of `*self`. Then `T-Proj` for the slice. `pub` without
  `uses` declares ∅ (F-22).
- **Obligations.** From `r < rows`, the invariant `len(blocks) == rows · bpr` and
  `len(blocks) ≤ isize::MAX`:
  - `(r + 1) · bpr ≤ rows · bpr = len(blocks)`, so no multiplication or addition overflows;
  - the slice bounds hold;
  - the ensures holds: `(r + 1) · bpr − r · bpr = bpr`.

  All are T2, but the first needs nonlinear bit-vector reasoning (OP-10). `len((*self).blocks)` and
  the range slice of `blocks: Buf<B>` are `<[B]>`'s built-in length and slicing through `Buf`'s
  deref (prelude), which C-EXACT-STD admits (note F-88); read strictly, the first revision's list
  did not cover them, and `kcall(Matrix::row)` failed (k3).
- **Facts.** Row ∅. `may_trap` false given its requires and the invariant. `kcall` holds. Result
  referent grade `α_self ⊔ α_r`.
- **Verdict: accept**, under the condition that `Matrix` declares the fields and the invariant (F-3).
  The snippet accesses `self.blocks` and `self.blocks_per_row` but shows no struct declaration.
  Negative items N-02 (`RowCache`) and N-03 (`pick`).

### D-D04: `hottest`

- **Source.** 01-language.md:443–456, `5a6b6593f660791c41cf67af83ff4e3a8841f4674ade7ed643c64427d639d9ad`.
- **Scope.** x1.

```text
fn hottest(slots: &[SlotView], heat: &[u32]) -> Option<SlotId> {
  return Option::map(
    Iterator::max_by_key(
      Iterator::filter(<[SlotView]>::iter(&*slots), clo_E[] |s| !(*(*s)).pinned),
      clo_L⟨κ⟩[heat by ref] |s| (copy (*heat)[(*(*s)).idx], Reverse(copy (*(*s)).idx))),
    clo_E[] |s| copy (*s).id)
}
```

**Steps.**

1. `slots.iter()` is a std adapter. Its result is `Local`, with a loan on `*slots` (`T-Ret` (b)).
2. The `filter` closure captures nothing, so it is `clo_E` with ε = ∅.
3. The `max_by_key` closure captures `heat` by reference, so it is `clo_L` (`T-CloL`, ε = ∅). The
   closure-parameter exception admits it, because F occurs in one parameter and not in the return
   type. The key `(u32, Reverse<usize>)` is `Ord`. FF-TIES concerns float keys only, so this is C.
4. `max_by_key` returns `Option<&SlotView>`, which is `Local`. Its loan is the loan of its by-value
   `Local` self, the `filter` adapter, which carries the shared loan on `*slots`. The key closure is
   a closure argument, so its capture loan on `heat` is not among the result's loans (`T-Ret` (b),
   note §5.4's per-position rule, F-90, F-99). The previous text took the union of every `Local`
   argument's loans, closure included, which only over-approximated. Its result grade is `α_slots ⊔ Θ_κ.θ_ret(α_slots)` (prelude), where
   the key closure's summary `Θ_κ` reads `heat`, so the grade is `α_slots ⊔ α_heat`; its `mt_κ` is
   true (the `heat[s.idx]` check), and `max_by_key`'s `may_trap` includes the `mt_κ` of the closure
   it runs, so `T-Call` puts it into `may_trap` (note §5.5, §5.7 rule 2, F-35, F-69). `θ_inv,f =
   α_self`, but the key closure has no by-mut capture, so nothing is raised by it (F-70).
5. `Option::map` with a capture-free closure yields `Option<SlotId>`, which is not `Local`, so it is
   returned freely. The closures' results are not references, so the closure result discipline
   (F-40) has nothing to check.

- **Ties.** Rust's `max_by_key` returns the last maximum. With the key `(heat, Reverse(idx))` and
  distinct `idx` values the maximum is unique: the highest heat, then the lowest index. That is the
  comment "ties -> lowest idx" [D: from the key's total order; it assumes `idx` is distinct across
  slots].
- **Facts.** Row ∅ (inferred). `may_trap` true: `heat[s.idx]` is a runtime bound check. Context
  default.
- **Verdict: accept.** The commented `live` is item N-04.

### D-D05: `Lease` and `expert_step`

- **Source.** 01-language.md:488–502, `f732e79cba68e08faa6bf3d5a17325be253c618b0e283c77d4d68a26e56b0a0e`.
- **Scope.** x1.

```text
linear struct Lease { slot: SlotId, slab: Frozen<SlabBuf> }
pub fn bytes(&self) -> &[u8] { return Frozen::bytes(&(*self).slab) }      // a projection of a projection
fn expert_step(store: &Store, id: ExpertId, x: &[f32], y: &mut [f32]) -> Result<(), IoError> uses { io, spawn } {
  let lease: Lease = match Store::lease(&*store, copy id) { Ok(v) => v, Err(r) => return Err(From::from(r)) };
  ffn_q4(Lease::bytes(&lease), &*x, &mut *y);      // a shared loan on lease, ended after the call
  Store::release(&*store, move lease);             // consumes lease
  return Ok(())
}
```

- **Steps.** K-Lin (declared linear). `T-Match` for `?`: on the `Err` path no lease exists. `T-Proj`
  twice. `T-Call` `ffn_q4`, a kernel with row ∅. `T-Call` `release` consumes `lease`. `T-Lin`: `lease`
  is consumed exactly once on the only normal path that creates it.
- **Facts.** Row `{io, spawn}`, declared, and the union of `lease`'s and `release`'s rows. `may_trap`
  false given the prelude's signatures.
- **Verdict: accept**, under the prelude's `Store::lease`, `Store::release`, `Frozen::bytes` and
  `ffn_q4`. Deleting the `release` line is item N-05.

### D-D06: `note_use`

- **Source.** 01-language.md:536–543, `2339f24db5f062a04ec4ad40a1d75fbd9f292a6f510abbf386409d32cff65b37`.
- **Scope.** x1.

```text
fn note_use(st: &Mutex<StoreState>, k: ExpertKey) uses { nondet } {
  Mutex::with_lock(&*st, clo_L⟨κ⟩[k by ref] |s: &mut StoreState| StoreState::touch(&mut *s, copy k));
}
```

- **Steps.** Rust infers a by-reference capture of `k` for a non-`move` closure that uses a `Copy`
  value by value, so the closure is `clo_L`. The closure-parameter exception applies. `R = ()` is not
  `Local`. `with_lock`'s `{nondet}` is a subset of the declared row. The closure has no by-mut capture,
  so `T-Call` applies no capture writes; its writes go to the locked state, whose reads always have the
  fixed grade `γ_sh`.
- **Facts.** Row `{nondet}`. `may_trap` false. The closure's parameter has grade `γ_sh`; the result `()`
  has grade `Θ_κ.θ_ret(γ_sh)`, irrelevant here.
- **Conditions.** The prelude's `with_lock` and `StoreState::touch` (marked `conditional` in
  verdicts.json after review item R2-21).
- **Verdict: accept.** The commented `heat_view` is item N-06.

### D-D08: `ActQ8` and `block_index`

- **Source.** 01-language.md:835–842, `e0863a0f49005d277afe73e47304f7b42a438ec6053e068307fd90cc8237b4d2`.
- **Scope.** x1.

**`ActQ8`.** The fields are not `Local`. `#[range]` applies elementwise to the array. The invariant is
a contract expression (note §5.10, F-14). `q.iter().map(...)` is a `Local` adapter consumed by an
integer `sum`, so FF-SUM does not apply. Checked arithmetic is required: the sum of 64 terms of
magnitude at most 127 is at most 8,128 [D: 64 · 127], proved by T2 by unrolling, so it cannot overflow.

**`block_index`.**

```text
pub fn block_index(row: u32, col: u32) -> u32  [row ∈ 0..=511, col ∈ 0..=63]  ensures result < 32_768 {
  assert⟨ovf(mul)⟩(no_ovf(row * 64));  assert⟨ovf(add)⟩(no_ovf(row * 64 + col));
  return row * 64 + col
}
```

- **Obligations.** `row · 64 ≤ 32,704` and `+ 63 ≤ 32,767 < 32,768` [D: 511 · 64 + 63]. Both overflow
  asserts and the ensures are discharged by T2.
- **Facts.** Row ∅ (`pub`, no `uses`). `may_trap` false.
- **Verdict: accept.**

### D-D09: `check_entries`

- **Source.** 01-language.md:1032–1039, `15bc3324a0e2b1aab0190f9fb11b90732933146534b4e3e2355aa4fb0620ba2c`.
- **Scope.** x1.

```text
fn check_entries(entries: &[ExpertEntry], file_len: u64) -> Result<(), FormatError> {
  par i in 0..len(*entries) {
    let end: u64 = match Option::ok_or(u64::checked_add(copy (*entries)[i].offset, copy (*entries)[i].nbytes),
                                      FormatError::Overflow { entry: i }) {
                     Ok(v) => v, Err(r) => return Err(From::from(r)) };
    if end > file_len { return Err(FormatError::OutOfBounds { entry: i }) }
  }
  return Ok(())
}
```

- **`T-Par`.** W = ∅, so disjointness and the read rule hold vacuously, and the early-return grading
  of F-38 has nothing to raise. `entries` is a shared `Sync` capture. The exercised row is ∅. The
  early exits (`return` from `?` and from the `if`) are allowed and join `ω` and `ρ` under `pc'`; they
  also raise `J(F)`, so the final `return Ok(())` carries the entries' grade in `ρ` (F-30).
- **Obligations.** `(*entries)[i]`: `i < len` from the range, discharged.
- **Dynamic behaviour** (`E-Par-Join`, Lemma B). With entries 3 and 9 both bad, the join waits for
  indices 0–2, and the outcome is index 3's `Err` at any thread count, as the snippet's comment says.
- **Facts.** Row ∅. `may_trap` false.
- **Verdict: accept.**

### D-D11: `q4_matmul` and `schedule q4_matmul_avx512`

- **Source.** 02-compute.md:514–531, `aeb299b84bdc4dff7b41a99aea6fb3a2efc0f311e15505d2d14e1193308180d2`.
- **Scope.** x1 (conditional).

```text
kernel fn q4_matmul(w: &Matrix<BlockQ4>, a: &Matrix<ActQ8>, y: &mut Matrix<f32>)
    requires y.rows() == a.rows() && y.cols() == w.rows() && a.cols() == w.blocks_per_row() {
  par t in 0..rows(*a) {
    par r in 0..rows(*w) {
      (*IndexMut::index_mut(&mut *y, t))[r] = q4_row_dot(Matrix::row(&*w, r), Matrix::row(&*a, t));
    }
  }
}
```

- **Obligations.**
  - `q4_row_dot`'s requires: `len(row(*w, r)) = bpr(*w)` and `len(row(*a, t)) = bpr(*a) = cols(*a) =
    bpr(*w)`, by the prelude's `cols` ensures.
  - `index_mut`'s requires: `t < rows(*y) = rows(*a)`.
  - `[r]`: `r < len(row t) = cols(*y) = rows(*w)`.
- **Footprint.** `index_mut`'s footprint is discharged statically at its definition (`E-FOOTPRINT`,
  F-45), from the prelude's assumed body; it is never a runtime check.
- **Outer `T-Par`.** W is `y`'s row t, reached through `index_mut`. Its declared footprint
  `blocks[t·bpr .. (t+1)·bpr]` has the form `lo(t) ≤ hi(t) ≤ lo(t+1)` [D], so it is disjoint across t
  (F-25). The call borrows only the footprint (note §5.6).
- **Inner `T-Par`, by `Proj-Split`** (note §5.9, F-45). The elaborated body
  `(*IndexMut::index_mut(&mut *y, t))[r] = …` calls `index_mut` in every inner iteration r, taking a
  `&mut` on row t each time. As the review found (items R1-14, R2-27), the first draft's T-Par did
  not admit that: the place is not of the form `p[π(r)]`, and every iteration borrows the same row.
  `Proj-Split` lets a footprinted projection whose result is used, within the iteration, only as the
  base of a write at index `π(r) = r` contribute only `footprint[r]` to W, with its loan split per
  iteration. Its premise holds in the form the third review gave it: every argument, the receiver
  included, is invariant in the inner `par`. The receiver is `&mut *y`, and the only other argument
  is t, the outer `par`'s index. Neither mentions the inner index r or a place the inner body
  writes (note §5.9, F-63, F-102). The inner W is then `{ blocks[t·bpr + r] }`, from one write with
  index function r, so the pairwise premise holds affinely (F-95). At the outer level the same
  call varies with t, so `Proj-Split` does not apply there. The outer W is checked through the
  footprint's form, as above, and the outer body has that one write only.
- **Invariant.** The `&mut` loans on rows of `*y` end inside the `par` bodies; under F-43 the `Matrix`
  invariant re-check they trigger is deferred to each join, so it never reads a row another
  iteration is writing.
- **Cover, by `Cover-Proj`** (note §5.9, F-73). The previous revisions wrote "nested `T-Cover`", but
  no stated rule derived it: the outer body writes no `p[t] = e_w`, and every inner iteration passes
  `&mut *y` to `index_mut` (second review, R3-13, R4-11). `Cover-Proj`'s premises:
  0. neither body contains `break`, `continue`, `return` or `?`;
  1. the outer body is exactly the inner `par r`, and the inner body is the one top-level write
     `(*IndexMut::index_mut(&mut *y, t))[r] = q4_row_dot(…)`;
  2. the footprints tile `S = (*y).blocks`: `lo(t) = t · bpr(*y)`, so `lo(0) = 0` and `hi(t) =
     lo(t+1)`; `hi(rows(*a) − 1) = rows(*y) · bpr(*y) = len(S)` by `rows(*a) == rows(*y)` (requires)
     and the `Matrix` invariant; and `k = rows(*w) = cols(*y) = bpr(*y)` by the requires and `cols`'s
     ensures [D: T2 obligations, linear given the invariant];
  3. the only other access to `*y` is the receiver reborrow, which `Proj-Split` resolves to
     `footprint[r]`, with the receiver `&mut *y` and t invariant in the inner loop (F-102);
  4. `*y` is the referent of the reference parameter y, one place, and `Matrix<f32>` holds no
     reference.

  S is the field `(*y).blocks` of the grade cell `*y`, so the update is the partial update of note
  §5.4 (F-89), with `γ_new = γ(q4_row_dot(…)) ⊔ pc'_t ⊔ pc'_r`. γ(q4_row_dot(…)) is
  `(exact, cross_device-if-inputs-are, ∅, canon)`.

  `Matrix<f32>`'s other fields, `rows` and `blocks_per_row`, are `usize`, so S holds all of the
  cell's float content. The NaN bit is therefore reset to canon. The cell keeps α_y's fidelity,
  scope and B, so `θ_mut,y` depends on y in scope only, with ν canon, and the kernel's sink holds.
  The previous revisions wrote `S[*] := …`, which replaced the whole cell. With a raw `f32` field
  beside `blocks` that was unsound (item N-74), but D-D11 has no such field, so its verdict does
  not change.

  At run time the partly run nest is typed by `RT-CoverProj` (note §7.1, F-97).
- **Schedule.**
  - `t`, `r`: own scope.
  - `j`, `acc`: unique in the inlined `q4_row_dot`.
  - `tile r by 16`, `tile t by 8`: exact.
  - `vectorize j using vpdpbusd`: int_assoc, as in D-C3.
  - `keep_order acc`: exact.
  - `parallel r.tiles`: exact, inheriting disjointness.
- **Verdict: accept**, under the `IndexMut` footprint, `cols() == blocks_per_row()` in the prelude, and
  the provisional rules `Proj-Split` and `Cover-Proj`. Without a footprint, the outer `par` is checked
  as if it wrote all of `*y`, and `E-PAR-DISJOINT` rejects it. Without `Proj-Split`, the inner `par`
  is `E-PAR-DISJOINT`, and the fix is the hoist that note §14 P-19 proposes to 02's owner, together
  with P-25's flat cover. Since F-89, a cover of the hoisted row is a partial update that cannot
  reset the cell's NaN bit. Without `Cover-Proj`, `*y`'s float content is the weak join
  `raw ⊔ canon = raw`, and the kernel's sink is `E-NAN-RAW-SINK` (P-25). Note §12.1 lists
  `Proj-Split` and `Cover-Proj` in freeze tier C. Under its option (ii), D-D11's X1 expected
  verdict would become `E-PAR-DISJOINT`. This reviser recommends option (i), which keeps accept.

### D-D12: `flow moe_ffn`

- **Source.** 02-compute.md:665–672, `d65baa996b4828a77c01be1e68fcbd692fbeb9f35091d66b2309a3386d7a2f4c`.
- **Scope.** Out of X1: `flow` is M4–M5. Typed here as a `fn` (note OP-12).

**Steps.**

- `route(cfg, x)`: exact.
- `det[golden::scheduling_independence] { store.map_on_arrival(&ids, |w| expert_ffn(cfg, w, x)) }?`:
  - the closure captures `cfg` and `x` by reference, so it is `clo_L`, charged at creation, with row ∅
    (`expert_ffn` is a kernel);
  - `map_on_arrival` must be a scoped `std` API that joins before it returns, because `Local` values
    cross only into scoped threads (01 §5.7). Its row is `{io, spawn, nondet}`;
  - `T-Det` recomputes the result's schedule component from the block's free inputs (`store`, `ids`,
    `cfg`, `x`; note §5.11, F-32), and the `?` applies outside the block. The block lies outside any
    `par`, so the exercised `nondet` raises no `E-PAR-EFFECT`.
- `canon::combine_rank` is exact.

**Conditions.**

1. `DeclareDeterministic` for `moe_ffn`'s module. 01 §11's manifest grants only `store`, so as written
   the block is `E-DET-GRANT` (F-18).
2. An allocation rule. `ids`, `outs` and the returned `Act` look like owned collections. Under
   C-ALLOC the row would need `alloc(Global)`, which the declared `{ io, spawn }` lacks (F-15).
3. `map_on_arrival`'s signature, as above.
4. `golden::scheduling_independence`'s subject is `store::acquire` (prelude), which does not cover
   this block. A fixture whose subject is this block's anchor is needed, or the block is
   `E-DET-EVIDENCE` (F-33). The block's result `outs` is not a closure and not `Local`, so
   `E-DET-RESULT` holds if `map_on_arrival` returns an owned collection.

**Verdict: accept, conditional; out of X1.** At the X1 checker precondition the expected verdict is
reject with `E-OUT-OF-SCOPE-FLOW` (note §0.3, §12, Q10).

### D-D13: `store ExpertStore`

- **Source.** 02-compute.md:744–750, `7d54bbbe49164e0b17a2d17f24f86a685ea11076bd3100e787859cccd1a2d137`.
- **Scope.** Out of X1 (M4). `⊢_store` sketch only.

- **`hint port evict`.**
  - `⊢_to pick_victim` holds (D-C4).
  - `fallback lru` must satisfy F-tot: core code, row ∅, trap-free.
  - `validate evictable` must be trap-free (part of P-ind); the core must satisfy P-ind and A-ind.
  - the port must reserve a stack region of at least `S(pick_victim)` (S-tot, (t9)).
  - `fuel(4 * n_slots)` is at least `fuel(pick_victim) = n_slots + c`, so `W-FUEL` is not raised.
- **`hint port prefetch`.** `next_layer` is not shown: a condition.
- **`certificate output_noninterference(O1, O2, O3, O4, O5)`.** Under note §8 it should also name O6,
  F-tot, P-ind, S-tot and A-ind (P-2).

**Verdict: accept, conditional; out of X1.** At the X1 checker precondition the expected verdict is
reject with `E-OUT-OF-SCOPE-STORE`.

### D-D14 and D-D15: copies

- D-D14 is 02-compute.md:942–947 (`646242d0806f9e7c4da0cc7dd9bfcb9e23d483c83e411bafcb6d64c96f9f09e6`):
  `read_slab` alone, comment-equal to D-C5. **Accept.**
- D-D15 is 03-trust.md:277–283 (`c47e32d89effcca6c1edb5848d72637bbb6ad5a0fefe760e998f94e437f5b379`):
  `acquire` alone, comment-equal to D-C5. **Accept**, under D-C5's conditions.

### D-D16: `value_sum` with a hole

- **Source.** 04-toolchain.md:397–402, `6daa0e6dff14f010595744fc95a675b77dd30078fdedab1fc61a96ec9e61578c`.
- **Scope.** x1.

**Elaboration.** The body is `trap(hole("value_sum")) : ()`. The `requires` uses multiplications
(`heads * dn`, …). Under F-14 they are evaluated with checked arithmetic, so at run time a call whose
products overflow traps at `contract_ovf`, and in T2 they are read over ℤ with a no-overflow conjunct.

- **Facts.** Row ∅. `may_trap` true. Context default: it is a `fn`, not a kernel.
- **Verdict: accept.**

### D-D17: `KvRow`, `decayed`, `tick`

- **Source.** 04-toolchain.md:449–458, `e487eb7a827bba64d599aabe0403b324e3baf106a9259efb572290f19cfb9362`.
- **Scope.** x1.

**`tick`.**

```text
assert⟨idx⟩(i < len(*rows)); let tmp = decayed(&(*rows)[i], 0.5);
assert⟨idx⟩(i < len(*rows)); (*rows)[i] = tmp;
```

- **Steps.**
  - The right-hand side is evaluated first. Its shared loan through `rows` ends at the call.
  - Then `T-Assign` writes `(*rows)[i]`; the old `KvRow` is not Linear.
  - `decayed`'s body is a hole returning `KvRow`, which is not `Local`.
- **Facts.** `tick`: row ∅, `may_trap` true (the index asserts). `decayed`: `may_trap` true.
- **Verdict: accept by the calculus.** On a hot path, 04 §6.5's lowering rule rejects the overlapping
  out-parameter, which would need a hidden 4,096-byte temporary [D: 1,024 · 4]. That is a lowering
  rule, outside MCore, and the snippet's comment says so.

### D-D18: `open_slots`

- **Source.** 04-toolchain.md:818–826, `dea88ccac3b2a46a313a32b55d5b698338b4f38624e8a5e67994c01c9e94bbd0`.
- **Scope.** Out of X1 (M5, S6b).

**Assumed signatures** (not in the prelude, since the item is outside X1):

- `Arena::reserve(&MemCap, u32, Aligned<u64, 4096>, Pages) -> Result<Arena<LargePages>, AllocError>
  uses { alloc(LargePages) }`;
- `Arena<A>` is Linear;
- `page_report(&self) -> PageReport`, which is `Copy`;
- `split(self, u32)` consumes the arena;
- `Slots::new` consumes the chunks.

**Steps.** `T-Match` for `?`, `T-Lin` (the arena is consumed by `split`), and the row
`{alloc(LargePages)}`. Under C-OOM (note §3.4, F-49), exhausting the `LargePages` reservation is the
environment fault `⇑F(oom(LargePages))`, not a trap: its capacity comes from `cap_nv`.

**Verdict: accept, conditional; out of X1.** At the X1 checker precondition the expected verdict is
reject with `E-OUT-OF-SCOPE-MEMCAP`: `MemCap` is the first name in source order outside the X1
prelude.

### D-D19: `evolve slot store_evict`

- **Source.** 06-forge.md:179–188, `b6e66be4931f847c5ec811f70efff9b83a67ce8bd7ae9b500ff78897ae46963f`.
- **Scope.** Out of X1 (M4; campaigns at M6).

**Sketch.** `seed pick_victim` satisfies `⊢_to` (D-C4). `space timing_only` selects `⊢_to` for every
candidate. The remaining clauses (`objective`, `niches`, `plausible`, `prune`, `holdout`, `promote`)
are data for the Forge and the gate, not MCore.

**Verdict: not derived.** This is a sketch, not a derivation, so no calculus verdict is recorded;
verdicts.json's `verdict` is `not-derived`, and the item gets a derivation before `evolve slot`
enters scope (note §0.3, review item R4-15). The expected verdict for `mithi` at the X1 checker
precondition is reject with `E-OUT-OF-SCOPE-EVOLVE` (note §0.3, Q10).

### D-D20: `spec s5_forward_claims`

- **Source.** 07-hearth-port.md:220–227, `c4e7aa7dd5e376c9bf0f399018401671021777c8b29c145d3274676fdcd276fa`.
- **Scope.** x1, front end only.

**`⊢_spec`.**

- (p1) `forward_token` is a prelude-level stub. `hearth_c_ref::forward_token` is a seam symbol.
- (p3) Every claim's grade is on its kind's scale.
- (p4) The second claim, `refines(forward_token, …) requires tested`, is admissible because
  `forward_token` is non-kernel logits-path code (03 §2.2, DR-021). The same grade on a kernel slot
  would be `E-CLAIM-INADMISSIBLE`.

The spec targets `forward_token` but claims something about `q4_matvec_avx512`. Under the proposed
scope rule (note OP-16) that is allowed because `q4_matvec` lies in `forward_token`'s closure.

**Verdict: accept, conditional** on the stubs and OP-16.

### D-D21: `kernel fn softmax`

- **Source.** 07-hearth-port.md:287–303, `f891be467105e3527eb27b93b940165d7739c9c9bd050544ddbc19e6da674e03`.
- **Scope.** x1.

**Elaboration**, abbreviated:

```text
assert⟨idx⟩(0 < len(*x)) discharged by requires;  let mut m: f32 = copy (*x)[0];
for i in 1..len(*x) { if (*x)[i] > m { m = copy (*x)[i] } }               // payload-blind compare
for i in 0..len(*x) { (*x)[i] = canon_v1::expf(prim_fsub32(copy (*x)[i], m)) }   // covering loop 1
let s: f32 = canon::sum16(&*x);                                                   // shared reborrow of *x
for i in 0..len(*x) { (*x)[i] = canon::nan(prim_fdiv32(copy (*x)[i], s)) }        // covering loop 2
```

**Steps.**

- The two write loops each satisfy `T-Cover`: each body is the one top-level write `(*x)[i] = …`
  over `0..len(*x)` (premise 1), neither body contains a `break`, `continue`, `return` or `?`
  (premise 0, F-37), neither passes `&mut` of `*x` or of an overlapping place to a call (premise 3),
  and `*x` is the referent of the reference parameter x, one place and a whole grade cell, so each
  update replaces the cell (premise 4, F-64, F-89). Each binder i is a plain identifier without
  `mut` (premise 1, F-103). Each reads
  `(*x)[i]` before writing it; the strong update's grade `γ(e_w)` includes that read.
- After the second loop the referent of `x` has ν canon and grade `α_x`.
- `canon::sum16(x)` takes `&[f32]`; the `&mut` is reborrowed as shared for the call (Rust's coercion),
  and no loan conflicts.
- `⊢_k`:
  - (k1) row ∅;
  - (k2) all bounds are discharged;
  - (k3) `canon_v1::expf`, `canon::sum16` and `canon::nan` are admissible in exact context;
  - (k4) the sink `x` is canonical;
  - (k5) the transcendental is named (DR-014), the reduction is named (DR-013), and the maximum is an
    explicit comparison loop, not `max_by`;
  - (k6) holds.
- Which transcendental Hearth uses for softmax is provisional, pending D0-2. The calculus requires only
  that it be named.

**Facts.** Row ∅. `may_trap` false.

**Verdict: accept.**

**Without `T-Cover`.** The referent of `x` ends `raw ⊔ canon = raw`, and the note's sink check, which
reads final contents, fails with `E-NAN-RAW-SINK` (F-1).

### D-D22: `heat_into`

- **Source.** 07-hearth-port.md:457–465, `fe26ec2da4c6fc532a1d973509c853f2e57a2567477b2c0dd40b60e868b6b604`.
- **Scope.** x1.

```text
fn heat_into(store: &Store, out: &mut [f32]) uses { nondet }  requires out.len() == store.n_heat() {
  Mutex::with_lock(&(*store).state, clo_L⟨κ⟩[*out by mut] |s: &mut StoreState| {
    for k in 0..len(*out) { assert⟨idx⟩(k < len((*s).count_f)); (*out)[k] = copy (*s).count_f[k]; }
  });
}
```

**Steps.**

- The closure captures the place `*out` by mutable (unique) borrow, as Rust 2021 captures disjoint
  places (note §2.4, F-67), so it is `clo_L`, admitted by the exception. `target*(*out)` is the
  referent of the reference parameter out.
- In the body, `*out` has the capture symbol `β_out` (note §5.7, F-60), and `s` has grade `γ_sh`.
- `(*out)[k]`'s bound is discharged (`k < len(*out)`).
- `(*s).count_f[k]`'s bound is not: no fact relates `count_f`'s length to `n_heat()`. It stays a
  runtime check.
- `Θ_κ.θ_mut,*out = β_out ⊔ α_s`: the weak element writes join the copied value's grade with the old
  contents, and the loop guard's `J(L)` carries `len(*out)`, which is `β_out`.
- `T-Call` applies `wr_out ⊔ pc ⊔ θ_inv` to `target*(*out)`. `with_lock` runs the closure once, so
  `wr_out` is one application: `Θ_κ.θ_mut,*out(α_s := γ_sh, β_out := α_out) = γ_sh ⊔ α_out`, and
  `θ_inv = ⊥`. So the copied values are `schedule_dependent`, as 01 §7.2 requires: "a value read out
  of a `Mutex` through `with_lock` is never `cross_device`". The result is the same as the first
  revision's; the symbols make it follow from the rule rather than from the creation-time grade.

**Facts.** Row `{nondet}`. `may_trap` true.

**Verdict: accept**, under the prelude's `Store.state` (visible in module `store`) and
`StoreState.count_f`.

### D-D10 and D-D23: MXFP4 formats

- **Source.** 02-compute.md:385–391 (`1c59bb1c367400b340acb19fe4f89e26b0da68b17ef12fb734f8bc3ee04f5046`)
  and 07-hearth-port.md:885–891 (`2ca91205066fa92c7ca3e0facfd880b1f08556b63e615c03e0c93f097c53b74f`).
- **Scope.** Out of scope: status later. The dot order needs `canon.v1.1`.

`⊢_fmt` structure only: 1 + 32 · 4/8 = 17 bytes [D], as the snippets say.

**Verdict: not derived.** Only the structure is checked, and the dot order needs `canon.v1.1`, so
no calculus verdict is recorded; verdicts.json's `verdict` is `not-derived` (review item R4-15). At
the X1 checker precondition the expected verdict is reject with `E-OUT-OF-SCOPE-E8M0`: `e8m0` is the
first format code outside the X1 list in both snippets.

### D-D24 to D-D27: copies

| Item | Source and hash | Same derivation as | Verdict |
|---|---|---|---|
| D-D24 | ROADMAP.md:65–71, `c57e441bae825fc29aa0adfbcb5b5afecd63f820a7fca75afbdc7f50a3bc9eba` | D-C6 | accept (front end), conditional |
| D-D25 | 01-language.md:220, `33ecc757128adf51f17436e4e62a5fe58a3a5307a4690e6937088b503e99ebd9` | D-C7 (hole) | accept |
| D-D26 | 01-language.md:306–308 and 02-compute.md:840–842, `371b1cd074fcc4a119339c935e9efd4c961a3340e42f8cffbb264cecf9ffaa56` | D-C7 (`Quantity`) | accept |
| D-D27 | 02-compute.md:452–458, `b9c51b0c61557f820ec776fbea335a3ea9fa8ed984a9e2c24f4ba5eddbd2f7c0` | D-C3 | accept (front end) |

D-D03 (01-language.md:387–393, `bfad207b…`) and D-D07 (01-language.md:787–802, `9f5d0d3a…`) are the
two halves of D-C2, verdict accept.

---

## N. Negative items

Items N-01 to N-06 are the commented-out examples inside snippet blocks, uncommented; they are gate
items. N-07 comes from ARCHITECTURE §5.3's reviewer note, which quotes the outline's earlier
`q4_matvec`. N-08 to N-10 are constructed here from the documents' rules. N-11 to N-39 are the
counterexamples of the first 2026-10-16 review, N-40 to N-69 those of the second, and N-70 to N-109
those of the third (2026-10-23) (note §17). N-110 to N-128 come from the round-3 sync with `mithi`
(2026-10-23, note §0.8). N-110 to N-127 are the probes of `mithi`'s items 7 to 15 and their twins;
N-128 was found during the sync. N-129 to N-153 come from the review of that sync (2026-10-23,
note §0.9): the reviewer's probes, and N-132, N-152 and N-153, which this reviser added. Each has
the verdict the revised rules give. N-07 to N-153 are supplementary: reported, and offered to the
planted corpus, but not gate inputs, because they are not in any fenced snippet (note Q11). In
N-40 to N-153, `h` is a value read under `with_lock`, so its grade is `γ_sh`.

The second round's "rustc rejects" statements were [inference] when written. The third revision
compiled them with the pinned rustc 1.99.1 [M: laptop, 2026-10-23]:

- N-24 (probe r07), N-25 to N-27, N-43, N-44, N-46 (r06), N-63 (r10), N-66 and N-68 are all
  rejected:
  - N-43 with E0521;
  - N-63 at the recursion limit;
  - the others with E0597, E0502 (N-27) or "lifetime may not live long enough" (N-24, N-46);
- every third-round item's rustc result is in its row;
- the probe files are in the session scratch area, `cc3/` (note §0.7).

Primary codes follow the precedence of note §5.16; secondary codes are in verdicts.json's `also`.
For N-70 to N-109, verdicts.json's `mithi_dcd4c87` field records what `mithi` at `dcd4c87` gives
(note §12.2). `mithi` at `4b4dd05`, with the sync's changes, agreed with every item N-07 to N-128
except N-38, which is not constructed [M: `tests/verdicts.rs`, 2026-10-23; note §12.2]. N-110 to
N-128 cite the sync's rustc probes `s01` to `s11` [M: rustc 1.99.1, laptop, 2026-10-23]. N-129 to
N-153 cite the review's probes (`ccsync-diff/`) and this reviser's rustc probes `t01` to `t37`
[M: rustc 1.99.1, laptop, 2026-10-23]. Their verdicts.json field `mithi_pre_review` records what
the sync's final `mithi` gave. `mithi` with this revision's changes agrees with every item N-07 to
N-153 except N-38 [M: `tests/verdicts.rs`, 2026-10-23].

| Item | Text (uncommented) | Expected | Code | Rule |
|---|---|---|---|---|
| N-01 | `fn first_dyn(b: &dyn Dequant) -> f32 { … }` (01 §4) | reject | `E-DYN` | J2 |
| N-02 | `struct RowCache { last: &[BlockQ4] }` (01 §5.3) | reject | `E-REF-FIELD` | J2 |
| N-03 | `fn pick(a: &[f32], b: &[f32]) -> &[f32]` (01 §5.3) | reject | `E-REF-ESCAPE` | T-Ret: no receiver, two reference parameters, elision fails (rustc rejects it too) |
| N-04 | `fn live(slots: &[SlotView]) -> impl Iterator<Item = &SlotView> { slots.iter().filter(\|s\| s.refs > 0) }` (01 §5.4) | reject | `E-LOCAL-RETURN` | T-Ret: an adapter, not a reference |
| N-05 | `expert_step` with `store.release(lease);` deleted (01 §5.6) | reject | `E-LINEAR-DROP` | T-Lin |
| N-06 | `fn heat_view(st: &Mutex<StoreState>) -> &[u32] { st.with_lock(\|s\| &s.heat) }` (01 §5.8) | reject | `E-REF-ESCAPE` | `with_lock`'s R at a reference type (F-28); the signature itself is a valid projection |
| N-07 | the outline's `q4_matvec`, requiring only `y.len() == w.rows()` (ARCHITECTURE §5.3 reviewer note 1) | reject | `E-KERNEL-OBLIGATION` | ⊢_k (k2): `q4_row_dot`'s requires cannot be proved at the call |
| N-08 | `let bw: Quantity<GBps, Simulated> = profile.dram_read_all_core;` | reject | `E-TYPE` | origins are distinct types (01 §4) |
| N-09 | in `pick_victim`, `let t = Instant::now();` | reject | `E-FF-CLOCK` (and `E-TO-ROW`) | ⊢_to (t1) |
| N-10 | in `q4_row_dot`, the float accumulation written `xs.iter().sum::<f32>()` | reject | `E-FF-SUM` | ⊢_k (k5) |
| N-11 | `#[grade(exact, cross_device)] fn count(st: &Mutex<u32>) -> u32 uses { nondet } { let n = st.with_lock(\|s\| *s); let mut c = 0u32; for _i in 0..n { c = c + 1; } c }` (R1-1) | reject | `E-GRADE` | `T-Jump`: the guard's `break_L` puts `γ_sh` into `J(L)`, so c is `schedule_dependent` (F-30) |
| N-12 | in module `store`, with a fixture whose subject is the block: `#[grade(exact, cross_device)] fn leak(st: &Mutex<u32>) -> u32 uses { nondet } { let v = st.with_lock(\|s\| *s); deterministic(by: E) { v } }` (R1-2) | reject | `E-GRADE` | `T-Det`: `d_s^in` is v's `sd` (F-32) |
| N-13 | `fn apply<F: Fn() -> u64>(f: F) -> u64 { f() }` and `#[grade(exact, cross_device)] fn stamp(c: &Clock) -> u64 uses { time, nondet } { apply(\|\| c.now_ns()) }`, with `Clock::now_ns` a `time` primitive (R1-3) | reject | `E-GRADE` | `T-CallClo` with `Θ_κ`, `apply` re-typed per κ (F-35) |
| N-14 | `kernel fn k(x: &[f32], y: &mut [f32]) requires x.len() == y.len() { for i in 0..y.len() { y[i] = canon::nan(x[i]); if x[i] > 0.0 { break; } } }` (R1-4, R2-3) | reject | `E-NAN-RAW-SINK` | `T-Cover` premise 0 fails, so the update is weak (F-37) |
| N-15 | `fn fill(y: &mut [u32], x: &[u32]) -> Result<(), E> { par for i in 0..y.len() { if x[i] == 0 { return Err(E) } y[i] = x[i]; } Ok(()) }` and `#[grade(exact, cross_device)] fn g(x: &[u32; 8]) -> u32 { let mut y = [0u32; 8]; let _ = fill(&mut y, x); y[7] }` (R1-5) | reject | `E-GRADE` | `T-Par`'s exit context grades W `γ_unspec` on the early return, and `θ_mut,y` carries it (F-38, F-31) |
| N-16 | `#[grade(exact, cross_device)] fn f(v: &mut [u32], m: &Mutex<u32>) uses { nondet } { let i = m.with_lock(\|s\| *s) as usize % v.len(); let r = &mut v[i]; *r = 1; }`; and R1-6's `let mut y = 0u32; { let r = &mut y; if h { *r = 1; } } y` with h read under `with_lock` (R1-6, R2-2) | reject | `E-GRADE` | `T-Assign` writes `target*(*r)`, the borrowed place, with the address grade (F-39) |
| N-17 | `fn helper<F: Fn(usize)>(n: usize, f: &F) { par for i in 0..n { f(i); } }` called from a `uses { nondet }` function as `helper(4, &\|i\| st.with_lock(\|s\| s.touch(k(i))))` (R1-7) | reject | `E-PAR-EFFECT` | the exercised row of the per-κ `helper` body contains `nondet` (F-36) |
| N-18 | `fn apply<F: Fn(&[f32]) -> &[f32]>(f: F, t: &[f32]) -> &[f32] { f(t) }` called as `apply(\|_x\| &big[..], &t)` (R1-8) | reject | `E-REF-ESCAPE` | closure result discipline: the bound's elision selects `_x`, and the body returns a loan on the capture `big` (F-40) |
| N-19 | `let l = store.lease(id)?; let c = move \|\| l.bytes().len(); let _n = c(); Ok(())`, and the same without the call (R1-9) | reject | `E-LINEAR-DROP` | K-LinClo: with the call, the closure body drops the captured lease; without it, the Linear closure is dropped (F-41) |
| N-20 | `expert_step` with `drop(lease);` in place of `store.release(lease);` (R2-5) | reject | `E-LINEAR-INSTANTIATE` | `drop`'s parameter keeps `¬Linear` (F-41) |
| N-21 | inside `impl<B> Matrix<B>`: `fn f(m: &mut Matrix<BlockQ4>, a: &[ActQ8], y: &mut [f32]) { m.rows = m.rows + 1; q4_matvec(&*m, a, y); }` (R1-11) | accept; `may_trap` true | — | the shared reborrow passed to a call is a publication point: a runtime check at site `inv(Matrix)` traps before the kernel runs (F-43) |
| N-22 | `kernel fn k(y: &mut [u32], j0: usize) requires j0 < y.len() { let mut j = j0; if j < y.len() { j = j + 1; y[j] = 0; } }` (R1-12) | reject | `E-KERNEL-OBLIGATION` | facts over SSA versions: `j₁ = j₀ + 1` has no bound (F-44). An integer slice keeps a NaN sink failure out of the way |
| N-23 | `impl IndexMut<usize> for Matrix<f32> { fn index_mut(&mut self, t: usize) -> &mut [f32] ensures footprint(result) == self.blocks[t*bpr..(t+1)*bpr] { &mut self.blocks[0..self.blocks_per_row] } }` (R1-13) | reject | `E-FOOTPRINT` | the result's loan targets row 0, not the declared footprint (F-45) |
| N-24 | `fn set(o: &mut Option<&u32>, d: &u32) { *o = Some(d); }` (R2-1) | reject | `E-LOCAL-MUT-STORE` | the stored value carries `ℓ_d*`, not `ℓ_o*` (F-39); rustc rejects it too |
| N-25 | `let a = 1; let mut outer = &a; { let y = 5; let mut inner = &y; std::mem::swap(&mut outer, &mut inner); } *outer` (R2-1) | reject | `E-BORROW-OUTLIVE` | `swap` moves the loan on y into outer, which is live when y's scope ends (F-39) |
| N-26 | `let mut v: Vec<&u32> = Vec::new(); { let d = 1; v.push(&d); } v[0]` (R2-1) | reject | `E-BORROW-OUTLIVE` | `push` adds the loan on d to v's loan set (F-39) |
| N-27 | `let mut x = vec![1]; let r = { let c = \|\| &x[0]; c() }; x.push(2); *r` (R2-1) | reject | `E-BORROW-CONFLICT` | `T-CallClo` gives r the closure's capture loan on x (F-40) |
| N-28 | inside `impl<B> Matrix<B>`: `fn shrink(m: &mut Matrix<BlockQ4>) { m.blocks.truncate(0); }`, assuming `Buf` has `truncate` (R2-4) | accept; `may_trap` true | — | the loan on the field `m.blocks` ends inside an S value: runtime check at `inv(Matrix)`, and again at exit (F-43) |
| N-29 | `#[grade(exact, cross_device)] fn n(st: &Mutex<u32>) -> u32 uses { nondet } { st.with_lock(\|s\| *s) }` (R2-6) | reject | `E-GRADE` | `with_lock`'s `θ_ret = Θ_f.θ_ret(γ_sh)` (F-35) |
| N-30 | `#[grade(exact, cross_device)] fn first_is_nan(x: f32) -> bool { let mut xs = [x - x, 1.0f32]; xs.sort_by(\|p, q\| p.total_cmp(q)); xs[0].is_nan() }` (R2-6) | reject | `E-GRADE` | the comparator's summary carries the observer taint of `total_cmp` on raw values; `sort_by`'s `θ_mut,self` joins it (F-35, F-50). For x = ∞, `x - x` is the target's default NaN, whose sign differs between x86 and arm64 [inference, as note §5.3] |
| N-31 | `#[grade(exact, cross_device)] fn g(m: &Mutex<bool>, out: &mut [u32]) uses { nondet } requires out.len() >= 1 { let mut c = 0u32; let mut it = (0..1).map(\|_\| { c += 1; 0 }); if m.with_lock(\|s\| *s) { it.next(); } drop(it); out[0] = c; }` (R2-7) | reject | `E-GRADE` | `it`'s type mentions κ, so the `next` call under the `γ_sh` pc applies κ's write to c (F-35) |
| N-32 | with a fixture whose subject is the block: `let f = deterministic(by: E) { \|\| (x.len(), clock.now_ns()) };` (R2-8) | reject | `E-DET-RESULT` | the block's result is a closure (F-34) |
| N-33 | in module `store`, with a `u32` field `counter` added to `StoreState`: `fn racy(&self) -> u32 uses { nondet } { deterministic(by: golden::scheduling_independence) { self.state.with_lock(\|s\| s.counter) } }` (R2-9) | reject | `E-DET-EVIDENCE` | the fixture's subject is `store::acquire`, which does not cover this block (F-33) |
| N-34 | with E covering the block: `fn p(m: &Mutex<u32>, n: usize) -> Option<usize> uses { nondet } { par for i in 0..n { let k = deterministic(by: E) { m.with_lock(\|c\| { *c += 1; *c }) }; if k == 3 { return Some(i); } } None }` (R2-10) | reject | `E-PAR-EFFECT` | the exercised row keeps `nondet` under `det` (F-36) |
| N-35 | `schedule bad for q4_row_dot on x86_64(avx512f) { vectorize g; }` (R2-18) | reject | `E-SCHED-REASSOC` | (s3'): g's loop carries the float chain `acc` (F-52) |
| N-36 | `kernel fn s(x: &[f32]) -> f32 { canon::nan(x.iter().fold(0.0, \|a, b\| a + b)) }` (R2-30) | reject | `E-FF-SUM` (also `E-KERNEL-CALL`) | FF-SUM covers float `fold` (F-59); `<[T]>::iter` is not on C-EXACT-STD |
| N-37 | `fn addr_len(v: &[u32]) -> usize { let s = format!("{:p}", &v[0]); s.len() }` (R2-25) | reject | `E-FF-ADDR` | C-FMT-ADDR (F-56) |
| N-38 | at a port (M4, out of X1): `policy fn p(slots: &[SlotView], now: Tick) -> Hint<SlotId> { let scratch = [0u64; 1 << 21]; … }` with a port stack budget below 16 MiB [D: 2^21 · 8 bytes] (R1-18, R2-16) | reject | `E-TO-STACK` | (t9) and `⊢_store` (F-48) |
| N-39 | `trait Key { fn key(&self) -> u32; } impl Key for f32 { fn key(&self) -> u32 { (*self + 0.0).to_bits() } }` (R1-20) | reject | `E-IMPL-GRADE` | the impl's constant part carries `obs⁰`, which `Θ̂_key` does not allow (F-50) |
| N-40 | `#[grade(exact, cross_device)] fn leak(m: &Mutex<bool>) -> bool uses { nondet } { let h = m.with_lock(\|s\| *s); let mut c = false; let mut f = \|\| { let o = c; c = true; o }; if h { f(); } f() }` (R3-1, R4-2) | reject | `E-GRADE` | the first call raises c to `γ_sh`; the second call's `θ_ret` reads `β_c := Γ(c) = γ_sh` (F-60). Before: `θ_ret` was the creation constant ⊥ and the result, which equals h, was `cross_device` |
| N-41 | N-40 with `let mut n = false; let mut f = move \|\| { let o = n; n = true; o };` (R3-1, R4-2) | reject | `E-GRADE` | the first call raises `γ(f)` by `θ_state ⊔ pc = γ_sh`; the second returns `θ_ret[σ := γ(f)] ⊔ γ(f)` (F-60) |
| N-42 | `fn twice<F: FnMut(u32) -> u32>(mut f: F, h: u32) -> u32 { f(h); f(0) }` and `#[grade(exact, cross_device)] fn g(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(\|s\| *s); let mut c = 0u32; twice(\|x: u32\| -> u32 { let old = c; c = x; old }, h) }` (R4-2) | reject | `E-GRADE` | per-κ re-typing of `twice` treats c as an implicit `&mut` referent: after `f(h)` it holds `α_h`, so `f(0)` returns `α_h` and `twice`'s per-κ `θ_ret` carries it (F-60, rule 1) |
| N-43 | `fn f() -> u32 { let mut slot: Option<&u32> = None; { let mut put = \|d: &u32\| { slot = Some(d); }; let x = 5u32; put(&x); } *slot.unwrap() }` (R3-2, R4-6) | reject | `E-LOCAL-MUT-STORE` (changed 2026-10-23, F-107; was `E-BORROW-OUTLIVE`) | d is annotated `&u32`, so it is higher-ranked, and storing its loan into the capture slot is `E-LOCAL-MUT-STORE`, as rustc's E0521 [M: rustc 1.99.1, this program]. With an unannotated `\|d\|`, `T-CallClo` transfers `λ_slot = {ℓ_d*}` with `ℓ_d* := {(x, ref)}`, and x's scope end is `E-BORROW-OUTLIVE` (F-61), as rustc's E0597 [M: probe n43u] |
| N-44 | `fn bad2() -> u32 { let a = 1u32; let mut out: &u32 = &a; { let y = 5u32; let mut c = \|\| { out = &y; }; c(); } *out }` (R4-6) | reject | `E-BORROW-OUTLIVE` | `λ_out` holds the by-ref capture loan on y, which `T-CallClo` adds to `L(out)` (F-61); rustc rejects it with E0597 |
| N-45 | `fn set(o: Option<&mut u32>, h: bool) { if let Some(r) = o { if h { *r = 1; } } }` and `#[grade(exact, cross_device)] fn g(m: &Mutex<bool>) -> u32 uses { nondet } { let h = m.with_lock(\|s\| *s); let mut y = 0u32; set(Some(&mut y), h); y }` (R3-3) | reject | `E-GRADE` | `set` has `θ_mut,o = α_o ⊔ α_h` for its `&mut`-carrying by-value parameter, and `T-Call` applies it to y through the loan `(y, mut)` that `Some(&mut y)` carries (F-62) |
| N-46 | `fn put(o: Option<&mut Option<&u32>>, d: &u32) { if let Some(r) = o { *r = Some(d); } }`, called as `let mut slot = None; { let d = 5u32; put(Some(&mut slot), &d); } *slot.unwrap()` (R3-3) | reject | `E-LOCAL-MUT-STORE` | the stored value carries `ℓ_d*` into a place at reference position `o.2` (F-62); rustc rejects it too, the elided lifetimes differ |
| N-47 | `impl W { fn window(&mut self, t: usize) -> &mut [f32] requires t + 4 <= self.blocks.len() ensures footprint(result) == self.blocks[t..t+4] { &mut self.blocks[t..t+4] } }` and `fn race(y: &mut W) { par for i in 0..4 { y.window(3 - i)[i] = i as f32; } }` (R3-4) | reject | `E-PAR-DISJOINT` | `window`'s argument `3 - i` varies with i, so `Proj-Split` does not apply, and the footprints `blocks[3-i..7-i]` overlap (F-63). Before: every iteration wrote `blocks[3]` |
| N-48 | `#[grade(exact, cross_device)] fn k(a: &mut [f32], b: &mut [f32], x: &[f32], h: bool) { b[0] = x[0] - x[0]; let y = if h { &mut *a } else { &mut *b }; for i in 0..y.len() { y[i] = canon::nan(x[i]); } }` (R3-5) | reject | `E-NAN-RAW-SINK` | `T-Cover` premise 4 fails (`L(y)` has two loans), so the writes are weak and `*b` stays raw (F-64). For `x[0] = +∞` and h true, b[0] is the target's default NaN [inference, as note §5.3] |
| N-49 | `fn set(m: &Mutex<u32>, y: &mut u32) uses { nondet } { loop { *y = m.with_lock(\|s\| *s); return; } }` and `#[grade(exact, cross_device)] fn g(m: &Mutex<u32>) -> u32 uses { nondet } { let mut y = 0u32; set(m, &mut y); y }` (R3-6) | reject | `E-GRADE` | `T-Loop`'s `Γ_out` keeps the X the return recorded, so `θ_mut,y` of `set` is `γ_sh` (F-65) |
| N-50 | `fn f() -> u32 { loop { return 1; } }` (R3-6) | accept | — | a loop with no break has type `!` (F-65); before, it was `()` and the tail elaboration `return (loop {…})` was `E-TYPE` |
| N-51 | `fn f(store: &Store, id: ExpertId, h: bool) -> Result<(), IoError> uses { io, spawn } { loop { let l = store.lease(id)?; if h { break; } store.release(l); } Ok(()) }` (R3-7) | reject | `E-LINEAR-DROP` | `T-Jump`: the break leaves l's scope with l unconsumed (F-66) |
| N-52 | `#[grade(exact, cross_device)] fn f(m: &Mutex<bool>) -> u32 uses { nondet } { let h = m.with_lock(\|s\| *s); let mut y = 0u32; { let r = &mut y; let mut g = \|\| { *r = 1; }; if h { g(); } } y }` (R3-8) | reject | `E-GRADE` | the closure captures the place `*r`, and `T-CallClo` updates `target*(*r) = y` under pc `γ_sh` (F-67) |
| N-53 | `#[grade(exact, cross_device)] fn f(m: &Mutex<bool>) -> u32 uses { nondet } { let h = m.with_lock(\|s\| *s); let mut y = 0u32; { let mut g = \|b: bool\| { if b { y = 1; return; } }; g(h); } y }` (R3-9, R4-4) | reject | `E-GRADE` | the closure's return records y in X, so `θ_mut,y = α_b`, instantiated at `γ_sh` (F-68) |
| N-54 | `#[grade(exact, cross_device)] fn g(x: &[u32; 8]) -> u32 { let mut y = [0u32; 8]; let mut run = \|\| -> Result<(), E> { par for i in 0..8 { if x[i] == 0 { return Err(E) } y[i] = x[i]; } Ok(()) }; let _ = run(); y[7] }` (R4-4) | reject | `E-GRADE` | `T-Par`'s X' raises the by-mut captured place y by `γ_unspec` in the closure's exit context, and `θ_mut,y` reads it (F-68, F-38) |
| N-55 | `#[grade(exact, cross_device)] fn leak(m: &Mutex<bool>) -> u32 uses { nondet } { let h = m.with_lock(\|s\| *s); let o: Option<u32> = if h { Some(1) } else { None }; let mut c = 0u32; let _ = o.map(\|v\| { c = 1; v }); c }` (R3-10) | reject | `E-GRADE` | `Option::map`'s `θ_inv,f = α_self = γ_sh` raises c (F-70) |
| N-56 | in module `store`, with a fixture whose subject is the block: `fn bump(m: &Mutex<u32>, i: u32) -> u32 { deterministic(by: E) { m.with_lock(\|c\| { *c = c.wrapping_mul(2).wrapping_add(i); 0 }) } }` and `fn p(m: &Mutex<u32>, n: usize) { par for i in 0..n { let _ = bump(m, i as u32); } }` (R3-11; the review's `n: u32` would make the `par` range `E-TYPE` first, since `par` indices are `usize`) | reject | `E-PAR-EFFECT` | `bump`'s exercised row `ε^x_bump` keeps `nondet`, and `T-Call` adds it to the body's (F-71) |
| N-57 | in module `store`, with a fixture E whose subject is the block: `#[grade(exact, cross_device)] fn leak(clock: &Clock) -> u64 uses { time, nondet } { let m = Mutex::new(0u64); m.with_lock(\|v\| *v = clock.now_ns()); deterministic(by: E) { m.with_lock(\|v\| *v) } }` (R3-12, R4-17) | accept; output graded `cross_device` | — | typing accepts: m's grade is ⊥, so `d_s^in = cd`. The restated claim form (note §5.11, F-72) makes E's claim false, because the result depends on m's contents; Theorem 4's condition (i) then fails and nothing is claimed. A fixture checker cannot detect a false claim; this item shows what evidence must establish |
| N-58 | `struct S { buf: [f32; 4] }`, `fn poke(s: &mut S) { s.buf[0] = s.buf[0] - s.buf[0]; }` and `#[grade(exact, cross_device)] fn k(x: &[f32; 4], s: &mut S) { for i in 0..4 { s.buf[i] = canon::nan(x[i]); poke(&mut *s); } }` (R3-13) | reject | `E-NAN-RAW-SINK` | `&mut *s` overlaps `s.buf` as an ancestor, so `T-Cover` premise 3 fails, and `poke`'s raw write stays (F-64) |
| N-59 | `kernel fn k(x: &[f32], y: &mut [f32], m: usize) requires x.len() == y.len() { for i in 0..y.len() { for _k in 0..m { y[i] = canon::nan(x[i]); } } }` (R4-16) | reject | `E-NAN-RAW-SINK` | the write is inside a nested loop, not at the top level, so `T-Cover` premise 1 fails; with m = 0 no element is written (F-64) |
| N-60 | `#[grade(exact, cross_device)] fn k(x: &[f32], y: &mut [f32], c: bool) { for i in 0..y.len() { let mut w = \|\| y[i] = canon::nan(x[i]); if c { w() } } }` (R4-16) | reject | `E-NAN-RAW-SINK` | the only write is inside a closure, which premises 1 and 3 exclude (F-64) |
| N-61 | `fn f(x: &[u32], n: usize) { 'outer: loop { par for i in 0..n { if x[i] == 0 { break 'outer; } } } }` (R3-15, R4-8) | reject | `E-PAR-BREAK` | a break in a `par` body targets an enclosing loop (F-75) |
| N-62 | `kernel fn outer(w: &Matrix<BlockQ4>, a: &[ActQ8], y: &mut [f32]) requires y.len() == w.rows() && a.len() == w.blocks_per_row() && y.len() >= 1 { y[0] = y[0] - y[0]; q4_matvec(w, a, &mut *y); }` (R3-18) | accept | — | `&mut *y` borrows the whole referent of y, one place, so `T-Call` updates it strongly with `q4_matvec`'s `θ_mut,y = (⊥, {w, a}, canon)` (F-78); before, `raw ⊔ canon = raw` failed the sink |
| N-63 | `fn f<F: Fn()>(g: F, n: u32) { if n > 0 { f(\|\| g(), n - 1) } }` called as `f(\|\| (), 3)` (R3-20) | reject | `E-MONO-DEPTH` | every level instantiates f at a new closure type, so per-κ re-typing exceeds the fixed depth (F-80); rustc reports its recursion limit |
| N-64 | `#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let mut y = 0u32; let r = &mut y; *r = m.with_lock(\|s\| *s); *r }` (R4-1) | reject | `E-GRADE` | `P-Deref-Local` reads y's current grade `γ_sh` through r (F-82). Before: r's creation grade ⊥ |
| N-65 | `#[grade(exact, cross_device)] fn g(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(\|s\| *s); let mut y = 0u32; let f = \|v: &mut u32\| { *v = h; }; f(&mut y); y }`; also with `fn app<F: Fn(&mut u32)>(f: F, y: &mut u32) { f(y) }`, and `y.iter_mut().for_each(\|v\| *v = h)` on an array (R4-3) | reject | `E-GRADE` | `Θ_κ.θ_mut,v = γ(h)`, applied by `T-CallClo` to `target*` of the argument's loan; the std form through `for_each`'s `θ_mut,self` (F-69) |
| N-66 | `fn bad() -> u32 { let a = 1u32; let mut out: &u32 = &a; { let y = 5u32; let r: &u32 = &y; let c = move \|\| r; out = c(); } *out }` (R4-5) | reject | `E-BORROW-OUTLIVE` | the closure value and its `Local` result carry the loan r carries (F-61); rustc rejects it with E0597 |
| N-67 | `fn take_first(slots: &mut [Option<Lease>], want: &[bool]) -> Option<Lease> { par for i in 0..slots.len() { if want[i] { return slots[i].take(); } } None }` (R4-7) | accept, if `SlabBuf : Send` | — | typing accepts; dynamically, with `want[3]` and `want[9]` true, iteration 9's lease is abandoned at the join instead of lost (F-83) |
| N-68 | `fn t() -> u32 { let a = 1u32; let mut out = &a; { let y = 5u32; let t = (&y,); out = t.0; } *out }` (R4-9) | reject | `E-BORROW-OUTLIVE` | the tuple literal carries the loan on y, and `t.0` carries `L(t)` (F-84) |
| N-69 | `#[grade(exact, cross_device)] fn f(m: &Mutex<bool>) -> u32 uses { nondet } { let h = m.with_lock(\|s\| *s); loop { if h { break 1 } else { break 0 } } }` (R4-10) | reject | `E-GRADE` | the elaboration assigns `t_L` under the effective pc `γ_sh` before each break (F-85) |
| N-70 | `struct S { buf: [u32; 4], tag: u32 } #[grade(exact, cross_device)] fn k(m: &Mutex<u32>, s: &mut S) uses { nondet } { s.tag = m.with_lock(\|v\| *v); for i in 0..4 { s.buf[i] = 0; } }`; the call form: `fn zero(s: &mut S) { for i in 0..4 { s.buf[i] = 0; } } #[grade(exact, cross_device)] fn k2(m: &Mutex<u32>) -> u32 uses { nondet } { let mut s = S { buf: [1u32; 4], tag: 0 }; s.tag = m.with_lock(\|v\| *v); zero(&mut s); s.tag }` (R5-1) | reject | `E-GRADE` | `s.buf` is a proper sub-place of the cell `*s`, so the cover's update is partial and keeps `s.tag`'s `γ_sh` (F-89). In the call form, `zero`'s own cover is partial too, so its `θ_mut,s` keeps `α_s`, and the caller's strong update of the whole cell s keeps the tag's grade. Before: `*s := ⊥ ⊔ pc'`, and both returned `s.tag` at `cross_device`. rustc 1.99.1: the Rust skeleton compiles (probe p01, k_field). `mithi` at `dcd4c87`: reject E-GRADE (m01, m03): agrees |
| N-71 | `#[grade(exact, cross_device)] fn k(a: &mut [f32; 4], x: &[f32; 4]) { a[3] = x[0] - x[0]; let r = &mut a[0..2]; for i in 0..r.len() { r[i] = canon::nan(x[i]); } }` (R5-1) | reject | `E-NAN-RAW-SINK` | `res(*r)` is the range `(*a)[0..2]` of the cell `*a`. An index or range suffix never holds all of the cell's float content, so the update is partial, and `a[3]`'s raw NaN keeps the cell raw (F-89). For `x[0] = +∞`, `a[3]` is the target's default NaN [inference, as note §5.3]. rustc 1.99.1: the Rust skeleton compiles (probe p01, k_sub). `mithi` at `dcd4c87`: reject E-NAN-RAW-SINK (m02): agrees |
| N-72 | `struct Pair { buf: [f32; 4], tag: f32 } #[grade(exact, cross_device)] fn f(s: &mut Pair, x: &[f32; 4]) { s.tag = s.tag + 1.0; for i in 0..4 { s.buf[i] = canon::nan(x[i]); } }` (R6-3) | reject | `E-NAN-RAW-SINK` | the field `tag` is float content outside `s.buf`, so the partial update keeps the cell's NaN bit raw (F-89). `mithi` at `dcd4c87`: reject E-NAN-RAW-SINK (a03): agrees |
| N-73 | `#[grade(exact, cross_device)] fn f(vv: &mut [[f32; 4]; 2], x: &[f32; 4]) { vv[1][0] = vv[1][0] + 1.0; for i in 0..4 { vv[0][i] = canon::nan(x[i]); } }`; the same through a local reference: `let r = &mut vv[0]; for i in 0..4 { r[i] = canon::nan(x[i]); }` (R6-3) | reject | `E-NAN-RAW-SINK` | a row is an index suffix of the cell `*vv`, so the update is partial, and the raw `vv[1][0]` keeps the NaN bit raw; through `r`, `res(*r) = {(*vv)[0]}` gives the same (F-89). `mithi` at `dcd4c87`: reject E-NAN-RAW-SINK (a04, a05): agrees |
| N-74 | `struct M2 { rows: usize, blocks_per_row: usize, blocks: Vec<f32>, scale: f32 } invariant M2 { self.blocks.len() == self.rows * self.blocks_per_row } impl std::ops::IndexMut<usize> for M2 { type Output = [f32]; fn index_mut(&mut self, t: usize) -> &mut [f32] requires t < self.rows ensures footprint(result) == self.blocks[t * self.blocks_per_row .. (t + 1) * self.blocks_per_row] { &mut self.blocks[t * self.blocks_per_row .. (t + 1) * self.blocks_per_row] } } #[grade(exact, cross_device)] fn mm(x: &[f32], y: &mut M2) requires x.len() == y.blocks_per_row { y.scale = y.scale + 1.0; for t in 0..y.rows { for r in 0..y.blocks_per_row { y[t][r] = canon::nan(x[r]); } } }` (R6-3) | reject | `E-NAN-RAW-SINK` | `Cover-Proj`'s S is the field `(*y).blocks` of the cell `*y`, beside the raw `f32` field `scale`, so its update is partial and keeps ν raw (F-89). Without the loops (probe a21) and with the raw write after them (a22) the program is rejected too. D-D11 differs: `Matrix<f32>` has no float field outside `blocks`. `mithi` at `dcd4c87`: accept (a19): disagrees |
| N-75 | `#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> [u32; 4] uses { nondet } { let h = m.with_lock(\|s\| *s); let mut v = [0u32; 4]; for x in v.iter_mut() { *x = h; } v }` (R5-2) | reject | `E-GRADE` | `next`'s `Some` payload on `IterMut<'a, u32>` carries the loans the iterator carries, `{(v, mut)}`, so `*x = h` writes v under h's grade (F-90). Before: the item carried `(it, mut)`, the write went to the iterator, and v was returned at `cross_device`. rustc 1.99.1: the Rust skeleton compiles (probe p02, f). `mithi` at `dcd4c87`: accept (m04): disagrees |
| N-76 | `fn g() -> [u32; 4] { let mut v = [0u32; 4]; let x = v.iter_mut().next().unwrap(); *x = 1; v }` (R5-2) | accept | — | x carries the loan on v, not on the temporary iterator, which dies at the end of its statement (F-90). Before: x carried a loan on the dead temporary, `E-BORROW-OUTLIVE`. rustc 1.99.1: compiles (probe p02, g). `mithi` at `dcd4c87`: accept (m05); its test gives v[0] = 1: agrees |
| N-77 | `fn g(x: &mut &mut u32, h: u32) { **x = h; } #[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(\|s\| *s); let mut y = 0u32; let mut r = &mut y; g(&mut r, h); y }`; by-value form: `fn g2(o: &mut Option<&mut u32>, h: u32) { if let Some(r) = o { **r = h } }`, called on `&mut Some(&mut y)` (R5-3) | reject | `E-GRADE` | `R(&mut r) = {r, y}`. τ = `&mut u32` holds a reference, so the strong case does not apply, and y is raised weakly by `θ_mut,x = α_x ⊔ α_h` (F-91). Before: the strong case replaced r's grade and y stayed ⊥. rustc 1.99.1: the Rust skeleton compiles (probe p03). `mithi` at `dcd4c87`: accept (m06): disagrees |
| N-78 | `#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(\|s\| *s); let mut y = 0u32; { let r = &mut y; let mut g = move \|\| { *r = h; }; g(); } y }` (R5-4) | reject | `E-GRADE` | the by-move capture r carries `(y, mut)`, so y is an output place of the closure, and `T-CallClo` raises it by `θ_mut,y`, which carries h's grade (F-92). Before: the write went to a place outside Γ_c and was lost. rustc 1.99.1: the Rust skeleton compiles (probe p04). `mithi` at `dcd4c87`: reject E-MOVE-USED (m07), a false rejection, with E-GRADE secondary: disagrees in code |
| N-79 | `fn h() -> u32 { let a = 1u32; let mut r: &u32 = &a; let mut c = move \|set: bool\| -> u32 { if set { let z = 5u32; r = &z; 0 } else { *r } }; c(true); c(false) }` (R5-5) | reject | `E-LOCAL-MUT-STORE` (and `E-BORROW-OUTLIVE`) | storing a loan on the body local z into the by-move state r (F-93). r is live at the body's end, so z's scope end is `E-BORROW-OUTLIVE` too, later by source position. Before: accepted, and `c(false)` read a dangling reference. rustc 1.99.1: E0521 (probe p05a). `mithi` at `dcd4c87`: reject E-BORROW-OUTLIVE (m08): verdict agrees, primary code differs |
| N-80 | `fn h() -> u32 { let a = 1u32; let mut slot: Option<&u32> = Some(&a); let mut c = move \|d: Option<&u32>\| -> u32 { if let Some(d) = d { slot = Some(d); 0 } else { *slot.unwrap() } }; { let x = 5u32; c(Some(&x)); } c(None) }` (R5-5) | reject | `E-LOCAL-MUT-STORE` | d's written type has an elided reference lifetime, so d is higher-ranked, and storing its loan into the by-move state slot is rejected (F-93, F-107). rustc 1.99.1: E0521 (probe p05b). `mithi` at `dcd4c87`: accept (m09): disagrees |
| N-81 | N-80 with `move \|d\|` (unannotated) (R5-5) | reject | `E-BORROW-OUTLIVE` | `λ_σ = {ℓ_d*}`, so the call `c(Some(&x))` adds `(x, ref)` to `L(c)`, and c is live when x's scope ends (F-93). rustc 1.99.1: E0597 (probe p05c). `mithi` at `dcd4c87`: accept (m21): disagrees |
| N-82 | `fn g() -> u32 { let a = 1u32; let mut slot: Option<&u32> = Some(&a); let x = 5u32; let mut c = move \|d\| -> u32 { if let Some(d) = d { slot = Some(d); 0 } else { *slot.unwrap() } }; c(Some(&x)); c(None) }` (R5-5) | accept | — | the transfer adds `(x, ref)` to `L(c)`, and x outlives c (F-93). The reviewer's proposed rule would have rejected it. rustc 1.99.1: compiles (probe q09). `mithi` at `dcd4c87`: accept (m20): agrees |
| N-83 | `fn f() -> u32 { let a = 1u32; let mut out1: &u32 = &a; let mut out2: &u32 = &a; { let z0 = 7u32; out2 = &z0; let mut c = \|\| { out1 = out2; out2 = &a; }; c(); } *out1 }` (R5-6) | reject | `E-BORROW-OUTLIVE` | `λ_out1 = {ℓ_out2*}`, substituted with `L(out2) = {(z0, ref)}` before the call, so out1 carries the loan on z0 when z0's scope ends (F-94). Before: `ℓ_out2*` stayed symbolic and the program read a dangling reference. rustc 1.99.1: E0597 (probe p06a). `mithi` at `dcd4c87`: reject E-BORROW-OUTLIVE (m10): agrees |
| N-84 | `fn f() -> u32 { let a = 1u32; let b = 2u32; let mut out1: &u32 = &a; let mut out2: &u32 = &b; { let mut c = \|\| { out1 = out2; out2 = &a; }; c(); } *out1 + *out2 }` (R5-6) | accept | — | after substitution out1 carries `(b, ref)` and out2 `(a, ref)`; both outlive the reads (F-94). rustc 1.99.1: compiles (probe p06b). `mithi` at `dcd4c87`: reject E-BORROW-CONFLICT (m23), a false rejection from its Interpretation 12: disagrees |
| N-85 | `fn g() -> u32 { let a = 1u32; let mut out2: &u32 = &a; let r; { let z0 = 7u32; out2 = &z0; let mut c = \|\| { let t = out2; out2 = &a; t }; r = c(); } *r }` (R5-6) | reject | `E-BORROW-OUTLIVE` | `λ_ret = {ℓ_out2*}`, substituted with `{(z0, ref)}`, so r carries the loan on z0 when z0's scope ends (F-94). rustc 1.99.1: E0597 (probe p06c). `mithi` at `dcd4c87`: reject E-BORROW-OUTLIVE (m11): agrees |
| N-86 | `fn g() -> u32 { let a = 1u32; let b = 2u32; let mut out2: &u32 = &b; let r; { let mut c = \|\| { let t = out2; out2 = &a; t }; r = c(); } *r + *out2 }` (R5-6) | accept | — | r carries `(b, ref)` and out2 `(a, ref)` (F-94). rustc 1.99.1: compiles (probe p06d). `mithi` at `dcd4c87`: accept (m24): agrees |
| N-87 | `fn f(y: &mut [f32; 8]) { par for i in 0..7 { y[i] = 1.0; y[i + 1] = 2.0; } }`; through a projection, with N-47's W: `fn race(y: &mut W) { par for i in 0..4 { y.window(0)[i] = 1.0; y.window(1)[i] = 2.0; } }` (R5-7, R6-2) | reject | `E-PAR-DISJOINT` | the two writes' footprints meet across iterations: iteration i writes `y[i + 1]` and iteration i + 1 writes `y[i + 1]`; through the projection, `blocks[1 + i]` and `blocks[0 + (i + 1)]` (F-95). Before: each write was injective on its own, and both were accepted. `mithi` at `dcd4c87`: reject E-PAR-DISJOINT for the first form (d03), accept for the window form (m19): disagrees on the second |
| N-88 | `fn f() -> u32 { let a = 1u32; let mut slot: &u32 = &a; { let y = 5u32; let r = &y; slot = &*r; } *slot }` (R5-8) | reject | `E-BORROW-OUTLIVE` | the reborrow `&*r` carries a loan on y, resolved when it is created (F-96). rustc 1.99.1: E0597 (probe p08b). `mithi` at `dcd4c87`: reject E-BORROW-OUTLIVE (m16): agrees |
| N-89 | `fn f() -> u32 { let y = 5u32; let slot; { let r = &y; slot = &*r; } *slot }` (R5-8) | accept | — | slot's loan is on y, not on r, so r's scope end does not matter (F-96). rustc 1.99.1: compiles (probe p08a). `mithi` at `dcd4c87`: accept (m17): agrees |
| N-90 | `#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(\|s\| *s); let mut y = 0u32; { let t = (&mut y,); *t.0 = h; } y }` (R5-8) | reject | `E-GRADE` | `res(*t.0) = {y}` through `L̂(t.0) = L(t)` (F-96). Before: no rule typed the write. rustc 1.99.1: the Rust skeleton compiles (probe p08c). `mithi` at `dcd4c87`: accept (m18): disagrees |
| N-91 | `fn f() -> u32 { let a = 1u32; let v = [2u32, 3]; let mut out = &a; v.iter().for_each(\|x\| out = x); *out }` (R5-11) | accept | — | `for_each`'s item carries the iterator's loan `(v, ref)`. The closure argument's own capture loan on out is excluded, so out does not borrow itself (F-99). Before: `E-BORROW-CONFLICT`. rustc 1.99.1: compiles (probe p10). `mithi` at `dcd4c87`: accept (m12): agrees |
| N-92 | `#[grade(exact, cross_device)] fn f(m: &Mutex<bool>, y: &mut [u32; 4]) uses { nondet } { let h = m.with_lock(\|s\| *s); par for i in 0..4 { if h { continue; } y[i] = 1; } }` (R5-12) | reject | `E-GRADE` | `J(par)` holds h's grade at the write, and `γ_w` includes the effective pc (F-100). `mithi` at `dcd4c87`: reject E-GRADE (m13): agrees |
| N-93 | `trait Whole { fn whole(&mut self, t: usize) -> &mut [f32]; } impl Whole for [f32] { fn whole(&mut self, t: usize) -> &mut [f32] ensures footprint(result) == self[0..self.len()] { &mut self[0..self.len()] } } fn race(y: &mut [f32; 4]) { par for i in 0..2 { y[i..4].whole(0)[1 - i] = i as f32; } }` (R6-1) | reject | `E-PAR-DISJOINT` | the receiver `y[i..4]` varies with i, so `Proj-Split` does not apply. The composed map `i ↦ y[i + 1 − i] = y[1]` is not injective, so each call contributes its whole footprint `y[i..4]`, and those overlap (F-102). rustc 1.99.1: the serial for form compiles (probe r20). `mithi` at `dcd4c87`: accept (a10); its serial run writes y[1] in both iterations and y[0] never (a13): disagrees |
| N-94 | `#[grade(exact, cross_device)] fn f(y: &mut [f32; 4], x: &[f32; 4]) { for mut i in 0..4 { i = 0; y[i] = canon::nan(x[i]); } }` (R6-4) | reject | `E-NAN-RAW-SINK` | the index is a `mut` binder, so the loop is not a cover (premise 1). Only `y[0]` is written, and the weak join keeps the caller's raw NaN bit (F-103). rustc 1.99.1: the Rust form compiles (probe r19), and r02 shows that for mut i runs every iteration. `mithi` at `dcd4c87`: accept (a06); its run leaves y[1] = 0x7fc00001 (a06r): disagrees |
| N-95 | `fn f(y: &mut [f32; 4]) { par for mut i in 0..4 { i = 0; y[i] = 1.0; } }` (R6-4) | reject | `E-PAR-DISJOINT` | through SSA the index is the constant 0 in every iteration (F-103). `mithi` at `dcd4c87`: accept (a16): disagrees |
| N-96 | `fn h() -> u32 { let mut n = 0u32; let mut c = move \|\| { n += 1; n }; let mut d = c; d(); c() }` (R6-5) | accept | — | c is Copy (K-CloCopy): no by-mut capture, and n is Copy. d has its own state, so `h()` returns 1 (F-104). Before: `let mut d = c` moved c, and `c()` was a use after move. rustc 1.99.1: compiles and returns 1 (probe r09). `mithi` at `dcd4c87`: accept (b09), but h() evaluates to 2: verdict agrees, value differs |
| N-97 | `#[grade(exact, cross_device)] fn leak(st: &Mutex<u32>) -> u32 uses { nondet } { let h = st.with_lock(\|v\| *v); let mut s = 0u32; let mut c = move \|x: u32\| { let o = s; s = x; o }; let mut d = c; d(h); c(0) }` (R6-5) | accept | — | d is a copy of c with its own state, so `d(h)` raises only `γ(d)`, and `c(0)` returns c's state, 0, graded ⊥ (F-104). The result is the same for every h, so `cross_device` is right. The reviewer expected `E-GRADE`, which holds only if the copies share state, as `mithi`'s interpreter wrongly does. rustc 1.99.1: compiles; leak(7) returns 0 (probe r13). `mithi` at `dcd4c87`: accept (c01), but its run returns 7: verdict agrees, value differs |
| N-98 | `fn f() -> usize { let mut v: Vec<usize> = Vec::new(); v.push(v.len()); v.push(v.len()); v[1] }` (R6-6) | accept | — | the receiver's autoref is a two-phase reservation while `v.len()` is evaluated (F-105). Before: `E-BORROW-CONFLICT`. rustc 1.99.1: compiles (probe r14). `mithi` at `dcd4c87`: accept (d01): agrees |
| N-99 | `fn f(a: &mut Vec<usize>, n: usize) { a.push(n); } fn g() -> usize { let mut v: Vec<usize> = Vec::new(); f(&mut v, v.len()); v.len() }` (R6-6) | reject | `E-BORROW-CONFLICT` | an explicit `&mut v` written as an argument is an ordinary loan, not a reservation (F-105). rustc 1.99.1: E0502 (probe q01). `mithi` at `dcd4c87`: reject E-BORROW-CONFLICT (m14): agrees |
| N-100 | `fn f(v: &mut [u32; 4]) { let a = &mut v[0]; let b = &mut v[1]; *a = 1; *b = 2; }` (R6-7) | reject | `E-BORROW-CONFLICT` | places that differ only at an index overlap outside `par` (F-106). Before: T2 proved `0 ≠ 1`, and the program was accepted. rustc 1.99.1: E0499 (probe r01). `mithi` at `dcd4c87`: reject E-BORROW-CONFLICT (a08): agrees |
| N-101 | `fn g() -> u32 { let x = 5u32; let mut slot: Option<&u32> = None; { let mut put = \|d: &u32\| { slot = Some(d); }; put(&x); } *slot.unwrap() }` (R6-8) | reject | `E-LOCAL-MUT-STORE` | d is higher-ranked, so storing its loan into the by-mut capture slot is rejected, though x outlives slot (F-107). rustc 1.99.1: E0521 (probe r03). `mithi` at `dcd4c87`: accept (b03): disagrees |
| N-102 | `fn g() -> u32 { let x = 5u32; let id = \|d: &u32\| d; let r = id(&x); *r }` (R6-8) | reject | `E-REF-ESCAPE` | returning a higher-ranked parameter's loan (F-107). rustc 1.99.1: "lifetime may not live long enough" (probe r05). `mithi` at `dcd4c87`: accept (b05): disagrees |
| N-103 | `fn g(p: (&mut Vec<&u32>, &u32)) { p.0.push(p.1) }` (R6-8, R6-11) | reject | `E-LOCAL-MUT-STORE` | the pushed value carries `ℓ_p,2*` into a place at reference position `p.1`'s inner position (F-62, per position). rustc 1.99.1: "lifetime may not live long enough" (probe r08). `mithi` at `dcd4c87`: accept (d02): disagrees |
| N-104 | `fn g() -> u32 { let x = 5u32; let mut slot: Option<&u32> = None; { let mut put = \|d\| { slot = Some(d); }; put(&x); } *slot.unwrap() }` (R6-8) | accept | — | an unannotated parameter's loan is transferred into slot, and x outlives slot (F-61, F-107). rustc 1.99.1: compiles (probe r04). `mithi` at `dcd4c87`: accept (m25): agrees |
| N-105 | `fn n() -> &'static str { "x" }` (R6-9) | reject | `E-LIFETIME` | a named lifetime (J2); a Dc cost X1 counts (note §11 A-12, F-108, OP-23). rustc 1.99.1: compiles (probe q11). `mithi` at `dcd4c87`: reject E-LIFETIME (e01): agrees |
| N-106 | `struct Op { name: &'static str }` (R6-9) | reject | `E-REF-FIELD` (and `E-LIFETIME`) | a reference in a field (J2), first by source position; the lifetime is also `E-LIFETIME` (F-108). rustc 1.99.1: compiles (probe q11). `mithi` at `dcd4c87`: reject E-REF-FIELD (e02): agrees |
| N-107 | `fn g(v: &[u32]) -> Option<u32> { let x = v.first()?; Some(*x + 1) }` (R6-13) | accept | — | `?` on `Option` in a function returning `Option` (F-112); `may_trap` true (the addition). rustc 1.99.1: compiles (probe q10). `mithi` at `dcd4c87`: accept (m15): agrees |
| N-108 | `#[grade(exact, cross_device)] fn s(a: f64, b: f64) -> bool { 1.0 / a.max(b) < 0.0 }` (R6-15) | reject | `E-GRADE` | `f64::max`'s result carries the platform taint until P-20 pins its signed zero; for `a = -0.0, b = 0.0` the bool can differ between conforming targets (F-113). `mithi` at `dcd4c87`: accept (m26): disagrees |
| N-109 | in module `store`: `enum E { A(Lease), B(Lease) } fn f(store: &Store, e: E) uses { io, spawn } { match e { E::A(l) => store.release(l), _ => {} } }`; accepted twin: `fn f(store: &Store, o: Option<Lease>) uses { io, spawn } { if let Some(l) = o { store.release(l) } }` (R6-11) | reject | `E-LINEAR-DROP` | the `_` arm matches `B`, which carries a Linear value, and would drop it (F-111). The twin is accepted: the variant `if let` does not match, `None`, carries no Linear value. `mithi` at `dcd4c87`: reject E-LINEAR-DROP (m27); the twin is accepted (m28): agrees |
| N-110 | `fn w(o: &mut u32, k: u32) { *o = k; }` and `#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(\|v\| *v); let mut y = 0u32; let mut z = 0u32; let r = if h > 1 { &mut y } else { &mut z }; w(r, 4); y }` (`mithi` item 7, h9) | reject | `E-GRADE` | r's targets {y, z} were chosen under h, and `T-Call`'s weak update of `R(r) = {y, z}` joins `γ_addr(r) ⊇ γ_h` (F-114). Corrected by F-134: w's `*o = k` is a weak update (OP-25), so `θ_mut,o` does mention `α_o`, and `α_o := γ(&mut *r) ⊇ γ_h` rejects the item without the address grade too [M: a `mithi` build without it]. F-114's own case is N-153 |
| N-111 | the same w, and `… let mut a = [0u32; 2]; w(&mut a[(h % 2) as usize], 4); a[0] }` (`mithi` item 7, h11) | reject | `E-GRADE` | the index grade `γ_h` is part of `γ_addr` of the argument (F-114), and also of the argument's grade `γ(&mut a[i])`, which `α_o` takes; so, as for N-110, the item is rejected without the address grade too (F-134) [M] |
| N-112 | `fn put(o: &mut Vec<&u32>, d: &u32) uses { alloc(Global) } { let mut c = \|x: &u32\| o.push(x); c(d); }` and `fn g() -> u32 uses { alloc(Global) } { let mut v: Vec<&u32> = Vec::new(); { let z = 5u32; put(&mut v, &z); } *v[0] }` (`mithi` item 8, g1) | reject | `E-LOCAL-MUT-STORE` | x is annotated and the closure has no expected signature, so x is higher-ranked; its store into the output place `*o` is rejected in the body (F-107, F-121). rustc 1.99.1: E0521 on put (probe s06) |
| N-113 | N-112 with `\|x\|` (unannotated) (`mithi` item 8, g1's twin) | reject | `E-LOCAL-MUT-STORE` | the body may store `ℓ_x*` into `*o`; the call `c(d)` transfers `ℓ_d*` into o's referent at o's inner position, which is a store (F-115). Before F-115 put passed and g dangled. rustc 1.99.1: "lifetime may not live long enough" on put (probe s05) |
| N-114 | `fn put(o: &mut Vec<&u32>, v: &[u32]) { v.iter().for_each(\|x\| o.push(x)); }` (`mithi` item 8) | reject | `E-LOCAL-MUT-STORE` | `for_each`'s λ_q substitutes the loans of v's items, `ℓ_v*`, for x, and stores them into o's referent (F-115). rustc 1.99.1: "lifetime may not live long enough" (probe s07) |
| N-115 | `#[grade(exact, cross_device)] fn stamp(c: &Clock) -> u64 uses { time, nondet } { c.now_ns() }` (`mithi` item 9) | reject | `E-GRADE` | stamp is neither a kernel nor `timing_only`, so `cls(FF-CLOCK) = C` there (F-116); the `time` label's `nondet` taint fails the `cross_device` result, as in N-13 |
| N-116 | `fn f(v: &[u32]) -> &u32 { let l = [1u32, 2]; &l[0] }` (`mithi` item 10, ow05) | reject | `E-REF-ESCAPE` (and `E-BORROW-OUTLIVE`) | both class 4; `E-REF-ESCAPE` is anchored at the returned expression, before the closing brace where `E-BORROW-OUTLIVE` is anchored (F-117). rustc 1.99.1: E0515 (probe s08) |
| N-117 | `policy fn p(slots: &[SlotView], m: &Mutex<u32>) -> Hint<u32> { Hint::some(m.with_lock(\|v\| *v)) }` (`mithi` item 10, po09) | reject | `E-TO-ROW` (and `E-TO-AUTHORITY`, `E-TO-PARAM`, `E-TO-CALL`) | all class 7; (t1) at the item header comes first; `E-TO-AUTHORITY` and `E-TO-PARAM` share the parameter's anchor and are ordered by spelling (F-117) |
| N-118 | `policy fn p(slots: &[SlotView], now: Tick) -> Hint<usize> { let mut b = 0usize; for i in 0..slots.len() { if slots[i].refs == 0 { b = i; } } Hint::some(b) }` (`mithi` item 11, po04) | accept | — | (t5): the range's upper bound is `s.len()` of a core-provided slice parameter (F-118); `slots[i]` may trap, which (t8) allows |
| N-119 | `fn ap<F: Fn() -> u32>(f: F) -> u32 { f() }` and `policy fn p(slots: &[SlotView], now: Tick) -> Hint<u32> { let k = slots.len() as u32; Hint::some(ap(move \|\| k)) }` (`mithi` item 11, po11) | accept | — | (t6): the closure is called inside p and is not in p's result (F-118); ap satisfies ⊢_to apart from (t2) |
| N-120 | `policy fn p(slots: &[SlotView], now: Tick) -> Hint<usize> { let n = slots.len(); let mut b = 0usize; for i in 0..n { b = i; } Hint::some(b) }` (`mithi` item 11, pol/p15) | reject | `E-TO-LOOP` | (t5): a bound held in a local is not read through (F-118) |
| N-121 | `fn one() -> u32 { 1 }` and `policy fn p(slots: &[SlotView], now: Tick) -> Hint<fn() -> u32> { Hint::some(one) }` (`mithi` item 11) | reject | `E-TO-AUTHORITY` | (t6): a function value in p's result outlives the port call (F-118) |
| N-122 | `kernel fn k(i: usize, y: &mut [u32]) requires y.len() >= 1 { let j = if i < y.len() { i } else { 0 }; y[j] = 1; }` (`mithi` item 12, kc10) | accept | — | Φ holds `i < len(y) ⇒ j = i` and `¬(i < len(y)) ⇒ j = 0`, with `len(y) ≥ 1`, so T2 proves `j < len(y)` (F-119) |
| N-123 | in module `store`: `fn f(store: &Store, id: ExpertId) -> Result<(), IoError> uses { io, spawn } { let l = store.lease(id)?; let c = move \|\| store.release(l); c(); Ok(()) }` (`mithi` item 13) | accept | — | the body consumes its by-move Linear capture l (the new premise of `T-CloL`, F-120), and `c()` consumes the Linear closure c (K-LinClo). The accepted twin of N-19 |
| N-124 | `fn f() -> u32 { let a = 1u32; let v = [2u32, 3]; let mut out = &a; v.iter().for_each(\|x: &u32\| out = x); *out }` (`mithi` item 14, r2) | accept | — | the closure is written at `for_each`'s bound, so it has an expected signature and x is not higher-ranked (F-121); x carries the iterator's loan on v (F-90, F-99). rustc 1.99.1: compiles, returns 3 (probe s01) |
| N-125 | `fn f() -> u32 { let a = 1u32; let v = [2u32, 3]; let mut out = &a; let c = \|x: &u32\| out = x; v.iter().for_each(c); *out }` (`mithi` item 14) | reject | `E-LOCAL-MUT-STORE` | created by `let`, the closure has no expected signature, so the annotated x is higher-ranked and its store into the capture out is rejected (F-107, F-121). rustc 1.99.1: E0521 (probe s03) |
| N-126 | N-74's `M2` and `index_mut`, with `#[grade(exact, cross_device)] fn mm(x: &[f32], y: &mut M2) requires x.len() == y.blocks_per_row { for t in 0..y.rows { for r in 0..y.blocks_per_row { y[t][r] = canon::nan(x[r]); } } }` (`mithi` item 15, cc3's a20_coverproj_ctrl) | reject | `E-NAN-RAW-SINK` | `Cover-Proj`'s update of `(*y).blocks` is partial; `scale` is the caller's value, raw in general, and reaches the exact sink untouched (F-122). Field-sensitive cells would reject it too |
| N-127 | N-126 with `y.scale = canon::nan(y.scale);` before the loops (`mithi` item 15) | reject | `E-NAN-RAW-SINK` | both writes are partial updates of `*y`'s one cell, and neither sub-place holds all of its float content, so the NaN bit cannot be reset (C-CELL, F-89, F-122). Field-sensitive cells (OP-24) would accept it; note §11 A-13 |
| N-128 | `#[grade(exact, cross_device)] fn g(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(\|v\| *v); let mut s = 0u32; let mut c1 = move \|x: u32\| -> u32 { let o = s; s = x; o }; let mut c2 = c1; { let r = if h > 1 { &mut c1 } else { &mut c2 }; r(9); } c1(0) }` (found in the sync) | reject | `E-GRADE` | c2 is a copy of c1 (K-CloCopy). `T-CallClo`'s state update of `target*(r) = {c1, c2}` joins `γ_addr(r) ⊇ γ_h` (F-114). The body stores x into its state without reading the old state into it, so `θ_state` does not mention σ, and only the address grade carries h. rustc 1.99.1: the Rust form returns 9 for h = 3 and 0 for h = 0 (probe s11). `mithi` at `4b4dd05` accepted it |
| N-129 | `fn put(o: &mut Option<&u32>, d: &u32) { let mut c = move \|x\| { *o = Some(x); }; c(d); }` (RS-1, probe B2) | reject | `E-LOCAL-MUT-STORE` | o is captured by move, so *o, which its mutable loan reaches, is an output place (F-92). The body may store `ℓ_x*` there, and `c(d)` transfers `ℓ_d*` into o's referent at its inner position: a store, `E-LOCAL-MUT-STORE` at the call (F-115, F-123). rustc 1.99.1: "lifetime may not live long enough" (t01) |
| N-130 | `fn put(o: &mut Option<&u32>, d: &u32) { let mut c = move \|x\| { *o = Some(x); }; c(d); }` and `fn g() -> u32 { let mut o: Option<&u32> = None; { let z = 5u32; put(&mut o, &z); } *o.unwrap() }` (RS-1, probe B2c) | reject | `E-LOCAL-MUT-STORE` | put is rejected at `c(d)` as in N-129, so the program never reads the dead z. Before this revision `mithi` accepted both functions, and `mithi run --entry g` returned 5, read from the dead z [M]. rustc 1.99.1: "lifetime may not live long enough" (t23) |
| N-131 | `fn put(o: &mut Vec<&u32>, d: &u32) uses { alloc(Global) } { let mut c = move \|x\| o.push(x); c(d); }` (RS-1, probe B2d) | reject | `E-LOCAL-MUT-STORE` | the push form of N-129: `Vec::push` stores x into *o, an output place of the `move` closure, and `c(d)` transfers `ℓ_d*` there (F-115, F-123). rustc 1.99.1: "lifetime may not live long enough" (t02) |
| N-132 | `fn g() -> u32 { let mut o: Option<&u32> = None; { let z = 5u32; let r = &mut o; let mut c = move \|x\| { *r = Some(x); }; c(&z); } *o.unwrap() }` (RS-1, probe X06) | reject | `E-BORROW-OUTLIVE` | r is captured by move, so o, which r's loan targets, is an output place (F-92). `c(&z)` adds the loan on z to L(o), and z's scope ends at the inner block's closing brace while o, read after it, carries that loan: `E-BORROW-OUTLIVE` (F-123). rustc 1.99.1: E0597 (t26). `mithi` accepted it before this revision |
| N-133 | in module `store`: `fn f(store: &Store, id: ExpertId) -> Result<(), IoError> uses { io, spawn } { let l = store.lease(id)?; let c = move \|\| store.release(l); c(); c(); Ok(()) }` (RS-2, probe G4) | reject | `E-MOVE-USED` | in module `store`. c owns the Linear lease l, so c is Linear and runs once (K-LinClo). The first `c()` consumes c, and the second is a use after a move: `E-MOVE-USED` at the second call (§5.4, F-124). rustc 1.99.1 on the same shape with a non-Copy struct: E0382 (t06) |
| N-134 | `fn f(v: &[u32]) -> &u32 { let mut a = 1u32; let r = &a; a = 2; let l = [*r, 2]; &l[0] }` (RS-3, probe D1) | reject | `E-BORROW-CONFLICT` | all class 4. `E-BORROW-CONFLICT` at `a = 2` (r's loan on a is live) comes before `E-REF-ESCAPE` at the returned expression `&l[0]` and `E-BORROW-OUTLIVE` at the closing brace (§5.16, F-125). rustc 1.99.1 lists E0506 before E0515 (t07). `mithi` anchored `E-REF-ESCAPE` at the body's opening brace before this revision |
| N-135 | in module `store`: `fn f(store: &Store, id: ExpertId) -> Result<u32, IoError> uses { io, spawn } { let a = 0u32; let mut r = &a; { let l = store.lease(id)?; let z = 1u32; r = &z; } Ok(*r) }` (RS-3, probe D2) | reject | `E-BORROW-OUTLIVE` | in module `store`. At the inner block's closing brace, l is dropped (`E-LINEAR-DROP`) and z's scope ends while r carries its loan (`E-BORROW-OUTLIVE`). They share the anchor, so their spelling orders them (F-117, F-125). `mithi` anchored `E-LINEAR-DROP` at l's binding before this revision |
| N-136 | in module `store`: `fn f(store: &Store, id: ExpertId) -> Result<(), IoError> uses { io, spawn } { let l = store.lease(id)?; let mut a = 1u32; let r = &a; a = 2; let _u = *r; Ok(()) }` (RS-3, probe D9) | reject | `E-BORROW-CONFLICT` | in module `store`. `E-BORROW-CONFLICT` at `a = 2` comes before `E-LINEAR-DROP` at the body's closing brace, where the lease that is never released is dropped (§5.16, F-125). `mithi` reported `E-LINEAR-DROP` first, at l's binding, before this revision |
| N-137 | `struct S { x: u32, y: u32 }` and `fn g() -> u32 { let mut s = S { x: 1, y: 2 }; let mut c = \|\| s.x += 1; let r = &s.y; c(); *r + s.x }` (RS-4, probe R6) | accept | — | captures are places (§2.4, F-67): c captures `s.x` by unique borrow, which does not overlap `s.y` (F-126). rustc 1.99.1: compiles, returns 4 (t10). `mithi` captured the whole local and answered `E-BORROW-CONFLICT` before this revision |
| N-138 | `fn hc(c: &Clock) -> u64 uses { time } { c.now_ns() }` and `kernel fn k(c: &Clock) -> u64 uses { time } { hc(c) }` (RS-5, probe C2) | reject | `E-FF-CLOCK` | hc is not a kernel, and the kernel k calls it, so `cls(FF-CLOCK) = Dc` there (§5.0 as reworded, F-127): `E-FF-CLOCK` (class 2), with `E-GRADE`, `E-KERNEL-ROW` and `E-KERNEL-CALL` behind it. Under the sync's wording, "a `kcall` helper", the read had no Dc class: hc's row {time} makes `kcall(hc)` false |
| N-139 | `fn g() -> usize uses { alloc(Global) } { let v: Vec<u32> = Vec::new(); let r = &v; let w = v; r.len() + w.len() }` (RS-6, probe R18) | reject | `E-BORROW-CONFLICT` | the move `let w = v` while r's loan on v is live: `E-BORROW-CONFLICT`, as for a write (§5.4 as reworded, F-128). rustc 1.99.1: E0505 (t20) |
| N-140 | `fn g(v: &Vec<u32>) -> Vec<u32> { *v }` (RS-6, probe R19) | reject | `E-MOVE-BORROWED` | `*v` moves out of a place behind a shared reference: `E-MOVE-BORROWED` (F-128). rustc 1.99.1: E0507 (t21) |
| N-141 | `#[derive(Copy, Clone)] linear struct L { a: u32 }` and `fn g() { println!("x"); }` (RS-7, probe D7) | reject | `E-LINEAR-COPY` | L is linear and derives Copy (J1): `E-LINEAR-COPY`, now named in class 1, comes before the `println!`'s `E-AMBIENT-IO` (class 2) (F-129). Under the sync's class lines it fell under class 4's `E-LINEAR-*` |
| N-142 | `#[derive(Copy, Clone)] struct W { f: fn() -> u32 }` and `fn one() -> u32 { 1 }` and `policy fn p(slots: &[SlotView], now: Tick) -> Hint<W> { Hint::some(W { f: one }) }` (RS-8, probe E5) | reject | `E-TO-AUTHORITY` | (t6): the function value `one` is a field of W in p's result, so it outlives the port call: `E-TO-AUTHORITY` at the result type (F-118, F-130). `mithi` accepted it before this revision: its scan did not enter W |
| N-143 | `kernel fn k(i: usize, y: &mut [u32]) requires i < y.len() { let j = if i == 0 { 0 } else { i - 1 }; y[j] = 1; }` (RS-9, probe F2b) | accept | — | Φ holds `i == 0 ⇒ j = 0` and `i ≠ 0 ⇒ j = i - 1` (F-119). With `i < len(y)`, `j < len(y)` holds on both arms, and `i - 1` is evaluated under `i ≠ 0`. `mithi` answered `E-KERNEL-OBLIGATION` at `y[j]` before this revision; it now keeps the shifted bound `j ≤ i` (F-131) |
| N-144 | `kernel fn k(i: usize, y: &mut [u32]) requires i < y.len() { match i { 0 => {}, _ => { y[i - 1] = 1; } } }` (RS-9, probe F2c) | accept | — | the second arm's path facts include the negation of the first arm's test, `i ≠ 0` (§5.10 as revised, F-131), so `i - 1` does not underflow, and `i - 1 < len(y)`. `mithi` answered `E-KERNEL-OBLIGATION` at `i - 1` before this revision |
| N-145 | `kernel fn k(i: usize, y: &mut [u32]) requires i < y.len() { match i { 0 => {}, n => { y[n - 1] = 1; } } }` (RS-9, probe F2d) | accept | — | as N-144; the binding arm's n equals the scrutinee i (F-131). `mithi` answered `E-KERNEL-OBLIGATION` before this revision |
| N-146 | `fn f() -> u32 { let a = 1u32; let v = [2u32, 3]; let mut out = &a; v.iter().for_each((\|x: &u32\| out = x)); *out }` (RS-10, probe H1) | accept | — | the parenthesised closure is written as an argument at `for_each`'s `Fn*` bound, so it has an expected signature, and x is not higher-ranked (F-121, F-132); x carries the iterator's loan on v. rustc 1.99.1: compiles, returns 3 (t08) |
| N-147 | `fn f() -> u32 { let a = 1u32; let v = [2u32, 3]; let mut out = &a; v.iter().for_each({ \|x: &u32\| out = x }); *out }` (RS-10, probe H2) | accept | — | as N-146, with the closure as the tail expression of a block that is the argument (F-132). rustc 1.99.1: compiles, returns 3 (t09; also with a statement before the closure, t35) |
| N-148 | `fn g() -> u32 uses { alloc(Global) } { let mut v: Vec<u32> = Vec::new(); v.push(3); v[v.len() - 1] = 5; v[0] }` (RS-11, probe R12b) | reject | `E-BORROW-CONFLICT` | on a `Vec`, `v[e] = …` is `*IndexMut::index_mut(&mut v, e)`. The `&mut` of v is created before `v.len() - 1` is evaluated and is not a reservation, so the read of v conflicts: `E-BORROW-CONFLICT` (§3.2, F-133). rustc 1.99.1: E0502 (t11). `mithi` accepted it before this revision |
| N-149 | `fn g() -> u32 uses { alloc(Global) } { let mut v: Vec<u32> = Vec::new(); v.push(3); v[v.len() - 1] += 5; v[0] }` (RS-11, probe R12d) | reject | `E-BORROW-CONFLICT` | the compound form: the right operand first, then the place, with the same base-first `&mut` (F-133). rustc 1.99.1: E0502 (t12). `mithi` accepted it before this revision |
| N-150 | `fn g() -> u32 { let mut a = [1u32, 2]; a[a.len() - 1] = 5; a[1] }` (RS-11, probe R12c) | accept | — | an array uses built-in indexing, which evaluates the index first (F-133). rustc 1.99.1: compiles, returns 5 (t13) |
| N-151 | `fn w(o: &mut u32, k: u32) { *o = k; }` and `#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(\|v\| *v); let mut y = 0u32; let r = if h > 1 { &mut y } else { &mut y }; w(r, 4); y }` (RS-12, probe A1) | reject | `E-GRADE` | the review expected accept. `target*(*r) = {y}` is one whole cell, so `T-Call`'s strong case applies, without `γ_addr`. But w's `*o = k` is a weak update (OP-25), so `θ_mut,o` mentions `α_o`, and `α_o := γ(&mut *r) ⊇ γ(r) ⊇ γ_h` (T-If, P-Deref-Local): y gets h, `E-GRADE` (F-134). rustc 1.99.1: y is 4 for both h (t22), so the rejection is a cost, one that OP-25 would remove |
| N-152 | `fn z(o: &mut [u32; 2]) { for i in 0..2 { o[i] = 4; } }` and `#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(\|v\| *v); let mut y = [h, h]; let r = &mut y; z(r); y[0] }` (RS-12, probe X30) | accept | — | z covers *o (`T-Cover`), so `θ_mut,o` carries no `α_o`. `target*(*r) = {y}` is one whole cell, so `T-Call`'s strong case replaces y's grade, h's included (F-78, F-134). rustc 1.99.1: `y[0]` is 4 for both h (t31). `mithi` made no strong update through a local reference before this revision and answered `E-GRADE` |
| N-153 | `fn z(o: &mut [u32; 2]) { for i in 0..2 { o[i] = 4; } }` and `#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(\|v\| *v); let mut y = [0u32; 2]; let mut w2 = [0u32; 2]; let r = if h > 1 { &mut y } else { &mut w2 }; z(r); y[0] }` (RS-12, probe X31) | reject | `E-GRADE` | F-114's own case. `target*(*r) = {y, w2}`: a weak update. z's `θ_mut,o = ⊥` does not mention `α_o`, so only `γ_addr(r) ⊇ γ_h` carries the choice (F-114, F-134). rustc 1.99.1: `y[0]` is 4 for h = 3 and 0 for h = 0 (t29). A `mithi` build without the address grade accepts it [M] |

---

## V. How `mithi` is compared with these derivations

1. For **every** canonical and derived item of verdicts.json, whatever its scope, the comparison
   script extracts the snippet from the named file and lines, checks its SHA-256 against the recorded
   hash (a mismatch is a stale item, not a disagreement), concatenates the prelude, and runs
   `mithi --check --json`. A prelude declaration whose name the snippet itself declares (`BlockQ4`
   for D-C1 and its copies; `Lease` and its `impl` for D-D05) is omitted from the concatenation, so
   nothing is declared twice (§P, note F-87).
2. **Agreement** (note §0.3): the verdict matches; for a reject, the primary code matches, where the
   primary code is the first emitted code in the precedence order of note §5.16. A conditional item
   counts as an accept when the prelude supplies its conditions. For an item outside X1 scope the
   expected verdict is its `x1_expected` field, a reject with `E-OUT-OF-SCOPE-<KW>` (note §12, Q10);
   the first draft excluded these items from agreement, which loosened ROADMAP §3.2 (review item
   R2-19).
3. **Secondary facts** are compared and reported, but are not gate inputs: row, `may_trap`, trap
   sites, and the output grade's scope and NaN bit.
4. Negative items N-01 to N-06 are gate items. N-07 to N-153 are reported only (note Q11). For
   N-70 to N-109, verdicts.json's `mithi_dcd4c87` field records the result of `mithi` at `dcd4c87`
   (note §12.2), so that a later build's agreement can be compared with it.
5. An item whose `verdict` is `not-derived` (D-D10, D-D19, D-D23) is compared only on its
   `x1_expected`; `not-derived` is never an expected verdict (note §0.3).
6. The X1 design draft would reject several canonical constructs with `E-X1-NOTYET` (note §12, Q9).
   Such a rejection is a disagreement, not an agreement, under this rule.
7. The comparison script belongs to the X1 track (`experiments/x1-harness/`). This note supplies
   its inputs, not the script.
