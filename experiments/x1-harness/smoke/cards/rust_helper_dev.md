RUST HELPER CARD - X1 smoke run, DEVELOPMENT card (v0-dev). Not the frozen X1 helper card.

YOUR FILE. You write Rust 2021 for rustc 1.99.1, std only, no crates. Your file is the module
`solution` of a crate whose other modules are `prelude` (the task's types and helpers, read-only)
and a harness driver. Keep `use crate::prelude::*;` at the top and keep the stub's `pub fn`
signature. Private helper fns in your file are fine.

BUILD (the checker, the visible tests and the hidden tests use the same flags):
rustc --edition 2021 -C opt-level=0 -C overflow-checks=on -C debug-assertions=on -F unsafe_code
- Integer overflow panics; wrapping_*/checked_* are explicit. A panic fails a test case.
- Rejected in your file (static gate, code E-X1-GATE): unsafe, include!/include_bytes!/
  include_str!, #[path], env!/option_env!, extern crate, asm!, std::fs, std::env, std::process,
  std::net, std::os. Printing to stdout corrupts the result record; do not print.
- todo!()/unimplemented!() left in the file count as holes; submit with none.

HELPER PACK (present in the prelude when a task needs them; bit-identical to the Mithril std):
- f16_to_f32(h: u16) -> f32       exact binary16 -> f32 widening (subnormals, inf, NaN)
- canon_nan(x: f32) -> f32        any NaN -> bits 0x7fc00000; other values unchanged
- sum16(a: &[f32]) -> f32         canonical 16-lane sum: lane i & 15 in index order, lanes start
                                  at +0.0, then lane j += lane j+s for s = 8, 4, 2, 1; result lane 0
- dot16(w: &[f32], x: &[f32]) -> f32   sum16 of the rounded products w[i] * x[i]
- BlockQ4 { d: u16, qs: [u8; 32] } with .elem(i) -> i32: Hearth Q4, 64 elements, byte j holds
  element j (low nibble) and element j+32 (HIGH nibble), stored element + 8 (not llama.cpp's j+16)

NUMERICS IN RUST (Rust's own meaning, for reference)
- a * b + c is two roundings (rustc never contracts); a.mul_add(b, c) is one rounding.
- Iterator::sum / product / fold over floats is a sequential left fold (not the 16-lane order).
- max_by / min_by / max_by_key over floats keep the LAST maximum; f32 is not Ord.
- f32::total_cmp orders -0.0 before +0.0 and places NaN by sign; == treats -0.0 == +0.0 and
  NaN != NaN. f32::max/min return the non-NaN operand.
- x.round() ties away from zero; x.round_ties_even() ties to even.
- float `as` integer saturates; NaN -> 0.
- exp, ln, powf, powi: platform libm precision; avoid where a brief fixes the bits.

SNIPPETS (equivalents of the Mithril card's snippets; each compiles under the flags above)
pub fn scale_into(y: &mut [f32], x: &[f32], s: f32) {
    for i in 0..y.len() { y[i] = canon_nan(x[i] * s); }
}
pub fn spread(y: &mut [f32], x: &[f32]) {        // y.len() == 2 * x.len()
    for v in y.iter_mut() { *v = 0.0; }
    for i in 0..x.len() { y[2 * i] = canon_nan(x[i]); }
}
fn pair_max(v: &[i32]) -> i32 { if v[0] > v[1] { v[0] } else { v[1] } }
pub fn pair_maxes(x: &[i32], out: &mut [i32]) { // x.len() == 2 * out.len()
    for (b, o) in out.iter_mut().enumerate() { *o = pair_max(&x[b * 2..b * 2 + 2]); }
}
pub fn argmin(x: &[u32]) -> usize {             // first minimum (strict <)
    let mut best = 0;
    for i in 0..x.len() { if x[i] < x[best] { best = i; } }
    best
}
pub fn prefix_sum(x: &[i32], y: &mut [i64]) {
    let mut acc: i64 = 0;
    for i in 0..y.len() { acc = acc.wrapping_add(x[i] as i64); y[i] = acc; }
}
#[derive(Clone, Copy)] pub struct QueueView { pub len: u32, pub busy: bool }
pub fn prefetch_depth(q: QueueView) -> Option<u32> {   // advice: pure, no clock
    if q.busy { return None; }
    if q.len > 8 { Some(1) } else { Some(4) }
}
pub fn evens(v: &[u32]) -> Vec<u32> {
    v.iter().copied().filter(|x| x % 2 == 0).collect()
}

READING rustc OUTPUT. check returns the compiler's messages (error[E....], file:line:col and the
source line), the static gate's hits, the hole count and, with --tests, each visible case's
expected and actual result. A panic in a test case is reported with its message.
