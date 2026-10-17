//! Regression tests from the review of 2026-10-16 (two reviewers, Claude, same family,
//! independent context). Each case is a reviewer's probe or a reviser's companion case; its
//! expected verdict is Rust's (rustc was not run [inference]) or the note's, and mithi's verdict was
//! checked against it when the table was generated. Where a probe's stated expectation was judged
//! wrong, the case records the verdict the reviser defends and the README review log says why.
//! Rows (C-ALLOC, function values), grades (loop and summary fixpoints, NaN constants, policy
//! hints).

mod common;

/// reviewer probes (gr, rw, pol, c14, c15, loop chains, summary chains)
const GRADE_ROW_CASES: &[(&str, &str, &str, &str)] = &[
    ("gr/g01", "E-NAN-RAW-SINK", "", r####"#[grade(exact, cross_device)] fn f(a: f32, b: f32) -> f32 { a + b }"####),
    ("gr/g02", "accept", "", r####"#[grade(exact, cross_device)] fn f(a: f32, b: f32) -> f32 { canon::nan(a + b) }"####),
    ("gr/g03", "accept", "", r####"#[grade(exact, cross_device)] fn f(a: f32, b: f32) -> f32 { (a + b).max(0.0) }"####),
    ("gr/g04", "E-NAN-RAW-SINK", "", r####"#[grade(exact, cross_device)] fn f(a: f64, b: f64) -> f64 { (a + b).max(0.0) }"####),
    ("gr/g05", "E-NAN-RAW-SINK", "", r####"#[grade(exact, cross_device)] fn f() -> f32 { f32::NAN }"####),
    ("gr/g06", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(a: f32, b: f32) -> u32 { (a - b).to_bits() }"####),
    ("gr/g07", "accept", "", r####"#[grade(exact, cross_device)] fn f(a: f32, b: f32) -> u32 { canon::nan(a - b).to_bits() }"####),
    ("gr/g08", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(a: f32) -> bool { (a * 0.0).is_sign_negative() }"####),
    ("gr/g09", "accept", "", r####"#[grade(exact, cross_device)] fn f(a: f32) -> bool { (a * 0.0).is_nan() }"####),
    ("gr/g10", "accept", "", r####"#[grade(exact, cross_device)] fn f(n: u32) -> f32 { n as f32 }"####),
    ("gr/g11", "E-NAN-RAW-SINK", "", r####"#[grade(exact, cross_device)] fn f(a: f32) -> f32 { a.clamp(0.0, 1.0) }"####),
    ("gr/g12", "E-NAN-RAW-SINK", "", r####"#[grade(exact, cross_device)] fn f(a: f32) -> f32 { (a as f64) as f32 }"####),
    ("gr/g13", "E-NAN-RAW-SINK", "", r####"#[grade(exact, cross_device)] fn f(a: f32) -> f32 { a.abs() }"####),
    ("gr/g14", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(a: f32) -> u8 { (a + 1.0).to_bits() as u8 }"####),
    ("gr/g15", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(a: f32, b: f32) -> bool { (a - a).total_cmp(&b) == std::cmp::Ordering::Less }"####),
    ("gr/g16", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let v = m.with_lock(|s| *s); if v > 3 { 1 } else { 0 } }"####),
    ("gr/g17", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(m: &Mutex<u32>, out: &mut u32) uses { nondet } { let v = m.with_lock(|s| *s); if v > 3 { *out = 1; } }"####),
    ("gr/g18", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let v = m.with_lock(|s| *s); let mut r = 0u32; let mut i = 0u32; while i < v { r += 1; i += 1; } r }"####),
    ("gr/g19", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let v = m.with_lock(|s| *s); if v > 3 { return 1; } 0 }"####),
    ("gr/g20", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(m: &Mutex<u32>, xs: &[u32]) -> u32 uses { nondet } { let v = m.with_lock(|s| *s) as usize; xs[v % 1] }"####),
    ("gr/g21", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let v = m.with_lock(|s| *s); let o = if v > 3 { Some(1u32) } else { None }; match o { Some(x) => x, None => 0 } }"####),
    ("gr/g22", "E-GRADE", "", r####"fn h(m: &Mutex<u32>) -> u32 uses { nondet } { m.with_lock(|s| *s) }
fn id(x: u32) -> u32 { x }
#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { id(h(m)) }"####),
    ("gr/g23", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(c: &Clock) -> u64 uses { time } { c.now_ns() }"####),
    ("gr/g24", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let v = m.with_lock(|s| *s); let mut a = [0u32; 2]; a[(v & 1) as usize] = 1; a[0] }"####),
    ("gr/g25", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let v = m.with_lock(|s| *s); let t = (v, 1u32); t.1 + 0 * t.0 }"####),
    ("gr/g27", "accept", "", r####"#[grade(exact, cross_device)] fn f(x: &[f32], y: &mut [f32]) requires x.len() == y.len() { for i in 0..y.len() { y[i] = canon::nan(x[i]); } }"####),
    ("gr/g28", "E-NAN-RAW-SINK", "", r####"#[grade(exact, cross_device)] fn f(x: &[f32], y: &mut [f32]) requires x.len() == y.len() { for i in 0..y.len() { if i > 0 { continue; } y[i] = canon::nan(x[i]); } }"####),
    ("gr/g29", "E-NAN-RAW-SINK", "", r####"#[grade(exact, cross_device)] fn f(x: &[f32], y: &mut [f32]) requires x.len() == y.len() { for i in 0..y.len() { y[i] = canon::nan(x[i]); y[0] = x[0] - x[0]; } }"####),
    ("gr/g30", "E-NAN-RAW-SINK", "", r####"#[grade(exact, cross_device)] fn f(x: &[f32], y: &mut [f32]) requires x.len() == y.len() && y.len() > 0 { for i in 0..y.len() - 1 { y[i] = canon::nan(x[i]); } }"####),
    ("gr/g31", "E-NAN-RAW-SINK", "", r####"#[grade(exact, cross_device)] fn f(x: &[f32], y: &mut [f32]) requires x.len() == y.len() { for i in 0..y.len() { y[i] = canon::nan(x[i]); } y[0] = y[0] * 2.0; }"####),
    ("gr/g32", "E-NAN-RAW-SINK", "", r####"#[grade(exact, cross_device)] fn f(x: &[f32], y: &mut [f32]) requires x.len() == y.len() { for i in 0..y.len() { let r = &mut y[i]; *r = canon::nan(x[i]); } }"####),
    ("gr/g33", "E-NAN-RAW-SINK", "", r####"#[grade(exact, cross_device)] fn f(x: &[f32], y: &mut [f32]) requires x.len() == y.len() { for i in 0..y.len() { y[i] = canon::nan(x[i]); y[i] = x[i] + 1.0; } }"####),
    ("gr/g34", "E-NAN-RAW-SINK", "", r####"#[grade(exact, cross_device)] fn f(x: &[f32], y: &mut [f32]) requires x.len() == y.len() && x.len() > 1 { for i in 0..y.len() { y[i] = canon::nan(x[i]); } y.swap(0, 1); y[0] = x[0] - x[0]; }"####),
    ("gr/g35", "E-NAN-RAW-SINK", "", r####"#[grade(exact, cross_device)] fn f(x: &[f32], y: &mut [f32]) requires x.len() == y.len() { for i in 0..y.len() { y[i] = canon::nan(x[i]); } let z = &mut *y; z[0] = x[0] - x[0]; }"####),
    ("gr/g36", "E-NAN-RAW-SINK", "", r####"#[grade(exact, cross_device)] fn f(x: &[f32], y: &mut [f32], j: usize) requires x.len() == y.len() { for i in 0..y.len() { y[i] = canon::nan(x[i]); y[j % y.len()] = x[0]; } }"####),
    ("gr/g37", "E-NAN-RAW-SINK", "", r####"#[grade(exact, cross_device)] fn f(a: f32) -> f32 { if a > 0.0 { a } else { f32::NAN } }"####),
    ("gr/g38", "E-NAN-RAW-SINK", "", r####"const N: f32 = f32::NAN;
#[grade(exact, cross_device)] fn f() -> f32 { let x = N; x }"####),
    ("gr/g39", "E-NAN-RAW-SINK", "", r####"#[grade(exact, cross_device)] fn f(y: &mut [f32]) { for i in 0..y.len() { y[i] = f32::NAN; } }"####),
    ("rw/r01", "E-ROW-UNDECLARED", "", r####"pub fn f() -> Vec<u32> { vec![1u32] }"####),
    ("rw/r02", "E-ROW-UNDECLARED", "", r####"pub fn f(c: &Clock) -> u64 { c.now_ns() }"####),
    ("rw/r03", "E-ROW-UNDECLARED", "", r####"fn inner(c: &Clock) -> u64 { c.now_ns() }
pub fn f(c: &Clock) -> u64 uses { nondet } { inner(c) }"####),
    ("rw/r04", "E-ROW-UNDECLARED", "", r####"fn apply<F: Fn() -> u64>(f: F) -> u64 { f() }
pub fn g(c: &Clock) -> u64 { apply(|| c.now_ns()) }"####),
    ("rw/r05", "E-ROW-UNDECLARED", "", r####"pub fn g(c: &Clock, v: &[u32]) -> u64 { let mut t = 0u64; for _x in v { t = t.wrapping_add(c.now_ns()); } t }"####),
    ("rw/r06", "E-IMPL-ROW", "", r####"trait K { fn key(&self) -> u32; }
struct A;
impl K for A { fn key(&self) -> u32 { let v = vec![1u32]; v[0] } }"####),
    ("rw/r09", "accept", "", r####"fn f(x: &mut [u32]) { par for i in 0..x.len() { let v = vec![i as u32]; x[i] = v[0]; } }"####),
    ("rw/r10", "E-PAR-EFFECT", "", r####"fn f(c: &Clock, x: &mut [u64]) uses { time, nondet } { par for i in 0..x.len() { x[i] = c.now_ns(); } }"####),
    ("rw/r11", "E-ROW-UNDECLARED", "", r####"trait Tm { fn t(&self) -> u64; }
struct A;
pub fn f(c: &Clock) -> u64 { let g = || c.now_ns(); 0 }"####),
    ("rw/r12", "E-ROW-UNDECLARED", "", r####"pub fn f(m: &Mutex<u32>) -> u32 { m.with_lock(|s| *s) }"####),
    ("rw/r13", "accept", "", r####"fn f(m: &Mutex<u32>) -> u32 { m.with_lock(|s| *s) }
pub fn g(m: &Mutex<u32>) -> u32 uses { nondet } { f(m) }"####),
    ("rw/r14", "E-ROW-UNDECLARED", "", r####"pub fn f() -> String { format!("{}", 1u32) }"####),
    ("rw/r15", "E-ROW-UNDECLARED", "", r####"struct S;
impl S { pub fn mk(&self) -> Vec<u32> { Vec::with_capacity(4) } }"####),
    ("rw/r16", "E-ROW-UNDECLARED", "", r####"fn a(n: u32, c: &Clock) -> u64 { if n == 0 { c.now_ns() } else { b(n - 1, c) } }
fn b(n: u32, c: &Clock) -> u64 { a(n, c) }
pub fn f(c: &Clock) -> u64 { b(3, c) }"####),
    ("rw/r17", "E-ROW-UNDECLARED", "", r####"pub fn f(v: &mut Vec<u32>) { v.push(1); }"####),
    ("rw/r18", "E-ROW-UNDECLARED", "", r####"pub fn f(v: &[u32]) -> Vec<u32> { v.to_vec() }"####),
    ("rw/r19", "E-ROW-UNDECLARED", "", r####"pub fn f(v: &[u32]) -> Vec<u32> { v.iter().map(|x| *x + 1).collect() }"####),
    ("rw/r20", "E-ROW-UNDECLARED", "", r####"pub fn f(s: &String) -> String { s.clone() }"####),
    ("pol/p01", "E-TO-ROW", "--canonical-prelude", r####"policy fn p(slots: &[SlotView], now: Tick) -> Hint<SlotId> { let v: Vec<u32> = slots.iter().map(|s| s.refs).collect(); if v.len() > 0 { Hint::some(slots[0].id) } else { Hint::none() } }"####),
    ("pol/p02", "E-TO-ROW", "--canonical-prelude", r####"policy fn p(slots: &[SlotView], now: Tick) -> Hint<SlotId> { let s = format!("{}", now.0); if s.len() > 3 { Hint::none() } else { Hint::none() } }"####),
    ("pol/p03", "E-TO-RESULT", "--canonical-prelude", r####"policy fn p(slots: &[SlotView], now: Tick) -> u32 { 0 }"####),
    ("pol/p04", "E-TO-PARAM", "--canonical-prelude", r####"policy fn p(slots: &Vec<SlotView>, now: Tick) -> Hint<SlotId> { Hint::none() }"####),
    ("pol/p05", "E-TO-PARAM", "--canonical-prelude", r####"struct NotView { a: u32 }
policy fn p(x: NotView) -> Hint<u32> { Hint::none() }"####),
    ("pol/p06", "E-TO-LOOP", "--canonical-prelude", r####"policy fn p(slots: &[SlotView], now: Tick) -> Hint<SlotId> { let mut i = 0usize; while i < slots.len() { i += 1; } Hint::none() }"####),
    ("pol/p07", "E-TO-LOOP", "--canonical-prelude", r####"policy fn p(slots: &[SlotView], now: Tick) -> Hint<SlotId> { for _k in 0..now.0 { } Hint::none() }"####),
    ("pol/p08", "E-TO-RECURSION", "--canonical-prelude", r####"fn depth(n: u32) -> u32 { if n == 0 { 0 } else { depth(n - 1) } }
policy fn p(slots: &[SlotView], now: Tick) -> Hint<SlotId> { let _d = depth(3); Hint::none() }"####),
    ("pol/p11", "accept", "--canonical-prelude", r####"policy fn p(slots: &[SlotView], now: Tick) -> Hint<SlotId> { let mut best: f32 = 0.0; let mut id: Option<SlotId> = None; for s in slots { let sc = s.refs as f32 * 0.5; if sc > best { best = sc; id = Some(s.id); } } match id { Some(i) => Hint::some(i), None => Hint::none() } }"####),
    ("pol/p12", "E-GRADE", "--canonical-prelude", r####"policy fn p(slots: &[SlotView], now: Tick) -> Hint<SlotId> { if slots.len() > 0 { Hint::some(slots[0].id) } else { Hint::none() } }
#[grade(exact, cross_device)] fn use_hint(slots: &[SlotView], now: Tick) -> u32 { match p(slots, now).get() { Some(i) => i.0, None => 0 } }"####),
    ("pol/p13", "accept", "--canonical-prelude", r####"policy fn p(slots: &[SlotView], now: Tick) -> Hint<SlotId> { let age = now.0 - slots[0].last_use.0; if age > 3 { Hint::some(slots[0].id) } else { Hint::none() } }
fn call() -> u32 { let s = [SlotView { id: SlotId(1), idx: 0, pinned: false, refs: 0, last_use: Tick(9) }]; match p(&s, Tick(2)).get() { Some(i) => i.0, None => 7 } }"####),
    ("pol/p14", "E-TO-AUTHORITY", "--canonical-prelude", r####"policy fn p(slots: &[SlotView], now: Tick) -> Hint<SlotId> { let f = move || now.0; Hint::none() }"####),
    ("pol/p15", "E-TO-LOOP", "--canonical-prelude", r####"policy fn p(slots: &[SlotView], now: Tick) -> Hint<SlotId> { let n = slots.len(); for i in 0..n { } Hint::none() }"####),
    ("pol/p16", "E-TO-LOOP", "--canonical-prelude", r####"policy fn p(slots: &[SlotView], now: Tick) -> Hint<SlotId> { loop { if slots.len() > 0 { break; } } Hint::none() }"####),
    ("c14:w01", "E-ROW-UNDECLARED", "", r####"pub fn f(c: &Clock) -> u64 uses { } { c.now_ns() }"####),
    ("c14:w02", "E-ROW-UNDECLARED", "", r####"pub fn f(c: &Clock) -> u64 { c.now_ns() }"####),
    ("c14:w03", "E-ROW-UNDECLARED", "", r####"fn g(c: &Clock) -> u64 uses { time } { c.now_ns() } pub fn f(c: &Clock) -> u64 { g(c) }"####),
    ("c14:w04", "E-ROW-UNDECLARED", "", r####"pub fn f(c: &Clock) -> u64 { let h = || c.now_ns(); h() }"####),
    ("c14:w05", "E-ROW-UNDECLARED", "", r####"pub fn f(c: &Clock, v: &[u32]) -> u64 { v.iter().map(|x| c.now_ns() + *x as u64).sum() }"####),
    ("c14:w06", "E-ROW-UNDECLARED", "", r####"fn ap<F: Fn() -> u64>(f: F) -> u64 { f() } pub fn f(c: &Clock) -> u64 { ap(|| c.now_ns()) }"####),
    ("c14:w08", "E-ROW-UNDECLARED", "", r####"pub fn f(c: &Clock) -> u64 { let g: fn(&Clock) -> u64 = Clock::now_ns; g(c) }"####),
    ("c14:w09", "E-ROW-UNDECLARED", "", r####"fn h(c: &Clock) -> u64 { c.now_ns() } pub fn f(c: &Clock) -> u64 uses { } { h(c) }"####),
    ("c14:w10", "E-ROW-UNDECLARED", "", r####"pub fn f(m: &Mutex<u32>) -> u32 { m.with_lock(|v| *v) }"####),
    ("c15:w12", "E-ROW-UNDECLARED", "", r####"fn h(c: &Clock) -> u64 uses { time } { c.now_ns() } pub fn f(c: &Clock) -> u64 { let g: fn(&Clock) -> u64 = h; g(c) }"####),
    ("c15:w13", "E-ROW-UNDECLARED", "", r####"fn h(c: &Clock) -> u64 uses { time } { c.now_ns() } pub fn f(c: &Clock) -> u64 { let g = h; g(c) }"####),
    ("c15:w14", "E-GRADE", "", r####"fn h(c: &Clock) -> u64 uses { time } { c.now_ns() } fn ap(g: fn(&Clock) -> u64, c: &Clock) -> u64 { g(c) } kernel fn k(c: &Clock) -> u64 { ap(h, c) }"####),
    ("c15:w15", "E-GRADE", "", r####"fn h(m: &Mutex<u32>) -> u32 uses { nondet } { m.with_lock(|v| *v) } #[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 { let g = h; g(m) }"####),
    ("c15:w16", "E-PAR-EFFECT", "", r####"fn h(m: &Mutex<u32>) -> u32 uses { nondet } { m.with_lock(|v| *v) } fn f(y: &mut [u32], m: &Mutex<u32>) { let n = y.len(); let g = h; par for i in 0..n { y[i] = g(m); } }"####),
    ("p/c12bu", "accept", "", r####"fn h12(x: f32) -> f32 { canon::nan(x * 2.0) }
fn h11(x: f32) -> f32 { h12(x) }
fn h10(x: f32) -> f32 { h11(x) }
fn h9(x: f32) -> f32 { h10(x) }
fn h8(x: f32) -> f32 { h9(x) }
fn h7(x: f32) -> f32 { h8(x) }
fn h6(x: f32) -> f32 { h7(x) }
fn h5(x: f32) -> f32 { h6(x) }
fn h4(x: f32) -> f32 { h5(x) }
fn h3(x: f32) -> f32 { h4(x) }
fn h2(x: f32) -> f32 { h3(x) }
fn h1(x: f32) -> f32 { h2(x) }

kernel fn top(x: f32) -> f32 { h1(x) }"####),
    ("p/c12td", "accept", "", r####"kernel fn top(x: f32) -> f32 { h1(x) }

fn h1(x: f32) -> f32 { h2(x) }
fn h2(x: f32) -> f32 { h3(x) }
fn h3(x: f32) -> f32 { h4(x) }
fn h4(x: f32) -> f32 { h5(x) }
fn h5(x: f32) -> f32 { h6(x) }
fn h6(x: f32) -> f32 { h7(x) }
fn h7(x: f32) -> f32 { h8(x) }
fn h8(x: f32) -> f32 { h9(x) }
fn h9(x: f32) -> f32 { h10(x) }
fn h10(x: f32) -> f32 { h11(x) }
fn h11(x: f32) -> f32 { h12(x) }
fn h12(x: f32) -> f32 { canon::nan(x * 2.0) }"####),
    ("p/c1bu", "accept", "", r####"fn h1(x: f32) -> f32 { canon::nan(x * 2.0) }

kernel fn top(x: f32) -> f32 { h1(x) }"####),
    ("p/c1td", "accept", "", r####"kernel fn top(x: f32) -> f32 { h1(x) }

fn h1(x: f32) -> f32 { canon::nan(x * 2.0) }"####),
    ("p/c3bu", "accept", "", r####"fn h3(x: f32) -> f32 { canon::nan(x * 2.0) }
fn h2(x: f32) -> f32 { h3(x) }
fn h1(x: f32) -> f32 { h2(x) }

kernel fn top(x: f32) -> f32 { h1(x) }"####),
    ("p/c3td", "accept", "", r####"kernel fn top(x: f32) -> f32 { h1(x) }

fn h1(x: f32) -> f32 { h2(x) }
fn h2(x: f32) -> f32 { h3(x) }
fn h3(x: f32) -> f32 { canon::nan(x * 2.0) }"####),
    ("p/c4bu", "accept", "", r####"fn h4(x: f32) -> f32 { canon::nan(x * 2.0) }
fn h3(x: f32) -> f32 { h4(x) }
fn h2(x: f32) -> f32 { h3(x) }
fn h1(x: f32) -> f32 { h2(x) }

kernel fn top(x: f32) -> f32 { h1(x) }"####),
    ("p/c4td", "accept", "", r####"kernel fn top(x: f32) -> f32 { h1(x) }

fn h1(x: f32) -> f32 { h2(x) }
fn h2(x: f32) -> f32 { h3(x) }
fn h3(x: f32) -> f32 { h4(x) }
fn h4(x: f32) -> f32 { canon::nan(x * 2.0) }"####),
    ("p/c5bu", "accept", "", r####"fn h5(x: f32) -> f32 { canon::nan(x * 2.0) }
fn h4(x: f32) -> f32 { h5(x) }
fn h3(x: f32) -> f32 { h4(x) }
fn h2(x: f32) -> f32 { h3(x) }
fn h1(x: f32) -> f32 { h2(x) }

kernel fn top(x: f32) -> f32 { h1(x) }"####),
    ("p/c5td", "accept", "", r####"kernel fn top(x: f32) -> f32 { h1(x) }

fn h1(x: f32) -> f32 { h2(x) }
fn h2(x: f32) -> f32 { h3(x) }
fn h3(x: f32) -> f32 { h4(x) }
fn h4(x: f32) -> f32 { h5(x) }
fn h5(x: f32) -> f32 { canon::nan(x * 2.0) }"####),
    ("p/c6bu", "accept", "", r####"fn h6(x: f32) -> f32 { canon::nan(x * 2.0) }
fn h5(x: f32) -> f32 { h6(x) }
fn h4(x: f32) -> f32 { h5(x) }
fn h3(x: f32) -> f32 { h4(x) }
fn h2(x: f32) -> f32 { h3(x) }
fn h1(x: f32) -> f32 { h2(x) }

kernel fn top(x: f32) -> f32 { h1(x) }"####),
    ("p/c6td", "accept", "", r####"kernel fn top(x: f32) -> f32 { h1(x) }

fn h1(x: f32) -> f32 { h2(x) }
fn h2(x: f32) -> f32 { h3(x) }
fn h3(x: f32) -> f32 { h4(x) }
fn h4(x: f32) -> f32 { h5(x) }
fn h5(x: f32) -> f32 { h6(x) }
fn h6(x: f32) -> f32 { canon::nan(x * 2.0) }"####),
    ("p/c8bu", "accept", "", r####"fn h8(x: f32) -> f32 { canon::nan(x * 2.0) }
fn h7(x: f32) -> f32 { h8(x) }
fn h6(x: f32) -> f32 { h7(x) }
fn h5(x: f32) -> f32 { h6(x) }
fn h4(x: f32) -> f32 { h5(x) }
fn h3(x: f32) -> f32 { h4(x) }
fn h2(x: f32) -> f32 { h3(x) }
fn h1(x: f32) -> f32 { h2(x) }

kernel fn top(x: f32) -> f32 { h1(x) }"####),
    ("p/c8td", "accept", "", r####"kernel fn top(x: f32) -> f32 { h1(x) }

fn h1(x: f32) -> f32 { h2(x) }
fn h2(x: f32) -> f32 { h3(x) }
fn h3(x: f32) -> f32 { h4(x) }
fn h4(x: f32) -> f32 { h5(x) }
fn h5(x: f32) -> f32 { h6(x) }
fn h6(x: f32) -> f32 { h7(x) }
fn h7(x: f32) -> f32 { h8(x) }
fn h8(x: f32) -> f32 { canon::nan(x * 2.0) }"####),
    ("p/lc12", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(st: &Mutex<u32>, k: u32) -> u32 uses { nondet } {
    let x = st.with_lock(|s| *s);
    let mut b1 = 0u32;
    let mut b2 = 0u32;
    let mut b3 = 0u32;
    let mut b4 = 0u32;
    let mut b5 = 0u32;
    let mut b6 = 0u32;
    let mut b7 = 0u32;
    let mut b8 = 0u32;
    let mut b9 = 0u32;
    let mut b10 = 0u32;
    let mut b11 = 0u32;
    let mut b12 = 0u32;
    for _i in 0..k {
        b12 = b11;
        b11 = b10;
        b10 = b9;
        b9 = b8;
        b8 = b7;
        b7 = b6;
        b6 = b5;
        b5 = b4;
        b4 = b3;
        b3 = b2;
        b2 = b1;
        b1 = x;
    }
    b12
}"####),
    ("p/lc4", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(st: &Mutex<u32>, k: u32) -> u32 uses { nondet } {
    let x = st.with_lock(|s| *s);
    let mut b1 = 0u32;
    let mut b2 = 0u32;
    let mut b3 = 0u32;
    let mut b4 = 0u32;
    for _i in 0..k {
        b4 = b3;
        b3 = b2;
        b2 = b1;
        b1 = x;
    }
    b4
}"####),
    ("p/lc7", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(st: &Mutex<u32>, k: u32) -> u32 uses { nondet } {
    let x = st.with_lock(|s| *s);
    let mut b1 = 0u32;
    let mut b2 = 0u32;
    let mut b3 = 0u32;
    let mut b4 = 0u32;
    let mut b5 = 0u32;
    let mut b6 = 0u32;
    let mut b7 = 0u32;
    for _i in 0..k {
        b7 = b6;
        b6 = b5;
        b5 = b4;
        b4 = b3;
        b3 = b2;
        b2 = b1;
        b1 = x;
    }
    b7
}"####),
    ("p/lc8", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(st: &Mutex<u32>, k: u32) -> u32 uses { nondet } {
    let x = st.with_lock(|s| *s);
    let mut b1 = 0u32;
    let mut b2 = 0u32;
    let mut b3 = 0u32;
    let mut b4 = 0u32;
    let mut b5 = 0u32;
    let mut b6 = 0u32;
    let mut b7 = 0u32;
    let mut b8 = 0u32;
    for _i in 0..k {
        b8 = b7;
        b7 = b6;
        b6 = b5;
        b5 = b4;
        b4 = b3;
        b3 = b2;
        b2 = b1;
        b1 = x;
    }
    b8
}"####),
    ("p/lc9", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(st: &Mutex<u32>, k: u32) -> u32 uses { nondet } {
    let x = st.with_lock(|s| *s);
    let mut b1 = 0u32;
    let mut b2 = 0u32;
    let mut b3 = 0u32;
    let mut b4 = 0u32;
    let mut b5 = 0u32;
    let mut b6 = 0u32;
    let mut b7 = 0u32;
    let mut b8 = 0u32;
    let mut b9 = 0u32;
    for _i in 0..k {
        b9 = b8;
        b8 = b7;
        b7 = b6;
        b6 = b5;
        b5 = b4;
        b4 = b3;
        b3 = b2;
        b2 = b1;
        b1 = x;
    }
    b9
}"####),
    ("p/lw12", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(st: &Mutex<u32>, k: u32) -> u32 uses { nondet } {
    let x = st.with_lock(|s| *s);
    let mut b1 = 0u32;
    let mut b2 = 0u32;
    let mut b3 = 0u32;
    let mut b4 = 0u32;
    let mut b5 = 0u32;
    let mut b6 = 0u32;
    let mut b7 = 0u32;
    let mut b8 = 0u32;
    let mut b9 = 0u32;
    let mut b10 = 0u32;
    let mut b11 = 0u32;
    let mut b12 = 0u32;
    let mut j = 0u32; while j < k { j = j + 1;
        b12 = b11;
        b11 = b10;
        b10 = b9;
        b9 = b8;
        b8 = b7;
        b7 = b6;
        b6 = b5;
        b5 = b4;
        b4 = b3;
        b3 = b2;
        b2 = b1;
        b1 = x;
    }
    b12
}"####),
    ("p/lw4", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(st: &Mutex<u32>, k: u32) -> u32 uses { nondet } {
    let x = st.with_lock(|s| *s);
    let mut b1 = 0u32;
    let mut b2 = 0u32;
    let mut b3 = 0u32;
    let mut b4 = 0u32;
    let mut j = 0u32; while j < k { j = j + 1;
        b4 = b3;
        b3 = b2;
        b2 = b1;
        b1 = x;
    }
    b4
}"####),
    ("p/lw7", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(st: &Mutex<u32>, k: u32) -> u32 uses { nondet } {
    let x = st.with_lock(|s| *s);
    let mut b1 = 0u32;
    let mut b2 = 0u32;
    let mut b3 = 0u32;
    let mut b4 = 0u32;
    let mut b5 = 0u32;
    let mut b6 = 0u32;
    let mut b7 = 0u32;
    let mut j = 0u32; while j < k { j = j + 1;
        b7 = b6;
        b6 = b5;
        b5 = b4;
        b4 = b3;
        b3 = b2;
        b2 = b1;
        b1 = x;
    }
    b7
}"####),
    ("p/lw8", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(st: &Mutex<u32>, k: u32) -> u32 uses { nondet } {
    let x = st.with_lock(|s| *s);
    let mut b1 = 0u32;
    let mut b2 = 0u32;
    let mut b3 = 0u32;
    let mut b4 = 0u32;
    let mut b5 = 0u32;
    let mut b6 = 0u32;
    let mut b7 = 0u32;
    let mut b8 = 0u32;
    let mut j = 0u32; while j < k { j = j + 1;
        b8 = b7;
        b7 = b6;
        b6 = b5;
        b5 = b4;
        b4 = b3;
        b3 = b2;
        b2 = b1;
        b1 = x;
    }
    b8
}"####),
    ("p/lw9", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(st: &Mutex<u32>, k: u32) -> u32 uses { nondet } {
    let x = st.with_lock(|s| *s);
    let mut b1 = 0u32;
    let mut b2 = 0u32;
    let mut b3 = 0u32;
    let mut b4 = 0u32;
    let mut b5 = 0u32;
    let mut b6 = 0u32;
    let mut b7 = 0u32;
    let mut b8 = 0u32;
    let mut b9 = 0u32;
    let mut j = 0u32; while j < k { j = j + 1;
        b9 = b8;
        b8 = b7;
        b7 = b6;
        b6 = b5;
        b5 = b4;
        b4 = b3;
        b3 = b2;
        b2 = b1;
        b1 = x;
    }
    b9
}"####),
];

#[test]
fn grade_row_cases() {
    let bad = common::run_cases(GRADE_ROW_CASES);
    assert!(bad.is_empty(), "{} of {} cases differ:\n{}", bad.len(), GRADE_ROW_CASES.len(), bad.join("\n"));
}
