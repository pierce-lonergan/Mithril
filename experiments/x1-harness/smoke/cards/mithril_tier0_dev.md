MITHRIL TIER 0 CARD - X1 smoke run, DEVELOPMENT card (v0-dev). Not the frozen X1 card.

IDENTITY. Mithril source (.mith) has a Rust-shaped surface. Each construct is one of:
C  coincident: parses as Rust and means what Rust means;
Dc rejected: a Rust form Mithril does not support; the checker names it with an E- code and a fix;
D  new: a new meaning, always introduced by a new keyword, type or std name.
Nothing is reinterpreted: code Mithril accepts means what Rust says it means.

RULES
- Integer overflow traps in every build; wrapping_*/checked_* are explicit. Out-of-bounds index,
  division by zero, unwrap of None and todo!() trap at run time.
- kernel fn = exact-graded code. A kernel may call kernels, format accessors, canon:: items, f32
  methods such as abs, sqrt, to_bits, from_bits, is_nan, round_ties_even, mul_add, and plain fns
  with an empty effect row. No Vec/String/allocation, no I/O, no clock (E-KERNEL-ROW, E-KERNEL-CALL).
- In a kernel every possible trap (index, overflow, div0, a callee's requires, todo!) must be
  proved absent by the checker's prover T2 (E-KERNEL-OBLIGATION). T2 knows `for i in 0..n` bounds,
  the fn's `requires`, and facts from enclosing `if` tests. It has no loop invariants: an index
  kept across iterations has no known bound, and it does not see through / or % by a variable.
  Fixes: guard (`if k < y.len() { y[k] = ..; }`), keep a best VALUE in a local next to its index,
  or move work into a helper kernel whose `requires` states what it needs. Very long kernel bodies
  can exhaust T2's budget; split them.
- Kernel float outputs (result, &mut [f32], float fields) must have canonical NaN bits: pass each
  stored float through canon::nan(x) (E-NAN-RAW-SINK). An output slice counts as overwritten only by
  one loop `for i in 0..y.len()` (or a length `requires` equates) that writes y[i] unconditionally.
  If later writes are conditional, first fill the whole slice that way.
- policy fn = timing_only advice: empty row (no clock, no I/O), parameters are #[view] types or
  slices of them, result is a Hint<T> (Hint::some(x), Hint::none(); callers use .get()).
- Effects: a fn that allocates (Vec::push, format!, to_vec, collect, to_string) declares
  `uses { alloc(Global) }`; a pub fn without `uses` has the empty row (E-ROW-UNDECLARED).
- References are second-class: no & in struct fields, no lifetimes, no stored borrowing closures.
- todo!("name") is a typed hole: allowed in fn and policy fn (traps if reached), rejected in a
  kernel. Submit with no holes.

KEYWORDS (X1): fn, kernel fn, policy fn, struct, enum, impl, trait (static dispatch), format,
uses, requires. Not in X1 (E-X1-NOTYET-*): schedule, spec, claim, store, flow, evolve, comptime,
linear, deterministic, par for, export abi, include!/env!/#[path]. No println! (no I/O).

FALSE FRIENDS (Mithril rule; "exact" = kernel code)
FF-FMA a*b+c: two roundings, never contracted.  FF-MULADD a.mul_add(b,c): one rounding.
FF-SUM float .sum()/.product()/fold: rejected in exact code; use canon::sum16 / canon::dot16
  (16 lanes, lane i%16, then 8-4-2-1 tree) or canon::sum_seq (left fold from -0.0).
FF-TIES max_by/min_by/min_by_key over floats (keeps the LAST max): rejected in exact code; write
  explicit comparisons with the tie rule you need.
FF-NANMAX f32::max/min: Rust meaning; max(+-0,-+0)=+0.0, min=-0.0; a NaN operand gives the other.
FF-ROUND x.round(): ties away from zero; ties to even is x.round_ties_even().
FF-CAST float `as` int: saturating, NaN -> 0.   FF-OVF: integer overflow traps.
FF-EXP exp/ln/sin/powf: rejected in exact code; use canon_v1::expf or cr::expf.
FF-POWI powi: rejected in exact code; multiply explicitly.
FF-F16 f16 arithmetic/compare: rejected; f16 is storage, widen with .to_f32() (exact).
FF-REF FF-LOCAL FF-DYN FF-ASYNC FF-CELL FF-UNSAFE: & fields, lifetimes, escaping borrow closures,
  dyn, async/macros, Cell/RefCell/Rc/static mut, unsafe: rejected.
FF-CLOCK Instant::now: forbidden in kernels and policies.  FF-HOLE todo!: traps when reached.
FF-Q4 a Hearth Q4 block: 64 elements, element j+32 in byte j's HIGH nibble (not llama.cpp's j+16).

FORMAT. `format F { s: f16, q: nibbles<N, offset = k> }`: q holds N elements in N/2 bytes; byte j
has element j (low nibble) and element j+N/2 (high nibble); p.q.elem(i) -> i32 is nibble - k;
p.s.to_f32() widens exactly. Storage type is NibNok, e.g. Nib8o8 { b: [u8; 4] }.

SNIPPETS (illustrations, each accepted by mithi)
kernel fn scale_into(y: &mut [f32], x: &[f32], s: f32)
    requires x.len() == y.len()
{
    for i in 0..y.len() { y[i] = canon::nan(x[i] * s); }
}
kernel fn spread(y: &mut [f32], x: &[f32])
    requires y.len() == x.len() * 2
{
    for i in 0..y.len() { y[i] = 0.0; }          // full overwrite first
    for i in 0..x.len() {
        let k = 2 * i;
        if k < y.len() { y[k] = canon::nan(x[i]); }   // guarded write
    }
}
kernel fn pair_max(v: &[i32]) -> i32 requires v.len() == 2 { if v[0] > v[1] { v[0] } else { v[1] } }
kernel fn pair_maxes(x: &[i32], out: &mut [i32])
    requires x.len() == out.len() * 2
{
    for b in 0..out.len() { out[b] = pair_max(&x[b * 2..b * 2 + 2]); }
}
kernel fn argmin(x: &[u32]) -> usize requires x.len() > 0 {
    let mut best: usize = 0;
    let mut best_v: u32 = x[0];                   // keep the value, not just the index
    for i in 0..x.len() { if x[i] < best_v { best = i; best_v = x[i]; } }
    best
}
kernel fn prefix_sum(x: &[i32], y: &mut [i64]) requires x.len() == y.len() {
    let mut acc: i64 = 0;
    for i in 0..y.len() { acc = acc.wrapping_add(x[i] as i64); y[i] = acc; }
}
#[view] #[derive(Copy, Clone)] struct QueueView { pub len: u32, pub busy: bool }
policy fn prefetch_depth(q: QueueView) -> Hint<u32> {
    if q.busy { return Hint::none(); }
    if q.len > 8 { Hint::some(1) } else { Hint::some(4) }
}
fn evens(v: &[u32]) -> Vec<u32> uses { alloc(Global) } {
    let mut out: Vec<u32> = Vec::new();
    for x in v { if *x % 2 == 0 { out.push(*x); } }
    out
}

READING mithi OUTPUT. check returns verdict (accept|reject), primary (root-cause code) and
diagnostics [{code, message, loc file:line:col, anchor = the source text}]. Run-time traps name
the kind (idx, ovf(add), div0, hole(name), req(f)), the function and the source anchor. Codes:
E-KERNEL-OBLIGATION unproved trap site (guard it or add a requires); E-NAN-RAW-SINK float output
not canonical or not fully overwritten; E-KERNEL-ROW/E-KERNEL-CALL effect or call not allowed in a
kernel; E-ROW-UNDECLARED missing uses; E-FF-* false friend (apply the named fix); E-TYPE, E-PARSE;
E-MOVE-USED, E-BORROW-CONFLICT ownership as in Rust; E-X1-NOTYET-* outside the X1 subset.
