//! Regression tests from the review of 2026-10-16 (two reviewers, Claude, same family,
//! independent context). Each case is a reviewer's probe or a reviser's companion case; its
//! expected verdict is Rust's (rustc was not run [inference]) or the note's, and mithi's verdict was
//! checked against it when the table was generated. Where a probe's stated expectation was judged
//! wrong, the case records the verdict the reviser defends and the README review log says why.
//! Surface: labelled blocks, impl conformance and coherence, duplicates, derive and std bounds,
//! format placeholders, false-friend codes (also per generic instantiation), the agent subset.

mod common;

/// reviewer probes (core, ff, ff2, c1, c2, c3, c12, c13, N-63)
const SURFACE_CASES: &[(&str, &str, &str, &str)] = &[
    ("core/s01", "accept", "", r####"fn f(o: Option<u32>) -> u32 { let Some(x) = o else { return 0; }; x }
fn f2() -> u32 { f(Some(7)) }"####),
    ("core/s02", "accept", "", r####"fn f() -> u32 { let r = 'a: { if true { break 'a 5u32; } 6u32 }; r }"####),
    ("core/s03", "accept", "", r####"fn f() -> u32 { let mut v = vec![1u32, 2, 3]; let mut s = 0; while let Some(x) = v.pop() { s += x; } s }"####),
    ("core/s04", "accept", "", r####"fn f() -> u32 { let mut i = 0u32; let r = loop { i += 1; if i == 4 { break i * 2; } }; r }"####),
    ("core/s05", "accept", "", r####"fn f() -> u32 { let mut s = 0u32; 'o: for i in 0..5u32 { for j in 0..5u32 { if j > i { continue 'o; } if i == 3 { break 'o; } s += 1; } } s }"####),
    ("core/s06", "accept", "", r####"fn f(x: u32) -> u32 { match x { 0 => 1, 1 | 2 => 2, n if n > 10 => 3, _ => 4 } }
fn g() -> u32 { f(0) * 1000 + f(2) * 100 + f(11) * 10 + f(5) }"####),
    ("core/s07", "accept", "", r####"fn f() -> Result<u32, u32> { let a: Result<u32, u32> = Err(3); let b = a?; Ok(b + 1) }
fn g() -> u32 { match f() { Ok(x) => x, Err(e) => e * 10 } }"####),
    ("core/s08", "accept", "", r####"fn f() -> i32 { let x = -5i32; let y = x as u8 as i32; y }"####),
    ("core/s09", "accept", "", r####"fn f() -> String { format!("{:>5}|{:<4}|{:05}|{:x}|{:#b}|{:.2}", 42u32, 7u32, -12i32, 255u32, 5u32, 1.005f32) }"####),
    ("ff/f01", "E-FF-SUM", "", r####"#[grade(exact, cross_device)] fn f(x: &[f32]) -> f32 { canon::nan(x.iter().sum::<f32>()) }"####),
    ("ff/f02", "accept", "", r####"fn f(x: &[f32]) -> f32 { x.iter().sum::<f32>() }"####),
    ("ff/f03", "E-FF-SUM", "", r####"fn helper(x: &[f32]) -> f32 { x.iter().sum::<f32>() }
#[grade(exact, cross_device)] fn f(x: &[f32]) -> f32 { canon::nan(helper(x)) }"####),
    ("ff/f05", "E-FF-SUM", "", r####"fn gfold<T: Copy, F: Fn(T, T) -> T>(xs: &[T], z: T, op: F) -> T { xs.iter().fold(z, |a, b| op(a, *b)) }
#[grade(exact, cross_device)] fn f(x: &[f32]) -> f32 { canon::nan(gfold(x, 0.0f32, |a, b| a + b)) }"####),
    ("ff/f06", "E-FF-SUM", "", r####"#[grade(exact, cross_device)] fn f(x: &[f32]) -> f32 { canon::nan(x.iter().product::<f32>()) }"####),
    ("ff/f07", "E-FF-SUM", "", r####"#[grade(exact, cross_device)] fn f(x: &[f32]) -> f32 { canon::nan(x.iter().fold(0.0f32, |a, b| a + *b)) }"####),
    ("ff/f08", "E-FF-SUM", "", r####"#[grade(exact, cross_device)] fn f(x: &[f32]) -> f32 { let t: (f32, u32) = x.iter().fold((0.0f32, 0u32), |a, b| (a.0 + *b, a.1 + 1)); canon::nan(t.0) }"####),
    ("ff/f09", "E-FF-SUM", "", r####"#[grade(exact, cross_device)] fn f(x: &[f32]) -> f32 { canon::nan(x.iter().map(|v| *v * 2.0).sum::<f32>()) }"####),
    ("ff/f10", "E-FF-SUM", "", r####"#[grade(exact, cross_device)] fn f(x: &[f64]) -> f64 { let s: f64 = x.iter().sum(); if s.is_nan() { 0.0 } else { s } }"####),
    ("ff/f11", "E-FF-TIES", "", r####"#[grade(exact, cross_device)] fn f(x: &[f32]) -> usize { x.iter().enumerate().max_by(|a, b| a.1.partial_cmp(b.1).unwrap()).map(|p| p.0).unwrap_or(0) }"####),
    ("ff/f12", "accept", "--canonical-prelude", r####"policy fn p(slots: &[SlotView], now: Tick) -> Hint<SlotId> { let s: f32 = slots.iter().map(|v| v.refs as f32).sum(); if s > 1.0 { Hint::none() } else { Hint::none() } }"####),
    ("ff/f13", "E-FF-EXP", "", r####"#[grade(exact, cross_device)] fn f(x: f32) -> f32 { canon::nan(x.exp()) }"####),
    ("ff/f14", "E-FF-POWI", "", r####"#[grade(exact, cross_device)] fn f(x: f32) -> f32 { canon::nan(x.powi(2)) }"####),
    ("ff/f15", "E-FF-F16", "", r####"fn f(a: f16, b: f16) -> f16 { a + b }"####),
    ("ff/f16", "E-FF-CLOCK", "", r####"fn now(c: &Clock) -> u64 uses { time } { c.now_ns() }
kernel fn k(c: &Clock, y: &mut [u64]) requires y.len() == 1 { y[0] = now(c); }"####),
    ("ff/f17", "E-FF-ADDR", "", r####"fn f(x: &u32) -> String { format!("{:p}", x) }"####),
    ("ff/f18", "E-AMBIENT-IO", "", r####"fn f(x: u32) { println!("{}", x); }"####),
    ("ff/f19", "E-AMBIENT-IO", "", r####"fn f(x: u32) -> u32 { dbg!(x) }"####),
    ("ff/f20", "E-MACRO", "", r####"macro_rules! twice { ($e:expr) => { $e * 2 } }
fn f(x: u32) -> u32 { twice!(x) }"####),
    ("ff/f21", "E-DYN", "", r####"trait T { fn m(&self) -> u32; }
fn f(x: &dyn T) -> u32 { x.m() }"####),
    ("ff/f22", "E-FF-CELL", "", r####"use std::cell::Cell;
fn f() -> u32 { let c = Cell::new(1u32); c.set(2); c.get() }"####),
    ("ff/f23", "E-FF-CELL", "", r####"static mut N: u32 = 0;
fn f() -> u32 { 1 }"####),
    ("ff/f24", "E-GLOBAL-STATE", "", r####"static M: Mutex<u32> = Mutex::new(0);
fn f() -> u32 { 1 }"####),
    ("ff/f25", "E-DROP-IMPL", "", r####"struct G { x: u32 }
impl Drop for G { fn drop(&mut self) { } }"####),
    ("ff/f26", "E-LIFETIME", "", r####"fn f<'a>(x: &'a u32, y: &u32) -> &'a u32 { x }"####),
    ("ff/f28", "E-FF-ADDR", "", r####"fn f(x: &u32) -> String { let mut s = String::new(); write!(s, "{:p}", x).unwrap(); s }"####),
    ("ff/f30", "E-ASYNC", "", r####"async fn f() -> u32 { 1 }"####),
    ("ff2/g04", "E-FF-SUM", "", r####"fn gfold<T: Copy, F: Fn(T, T) -> T>(xs: &[T], z: T, op: &F) -> T { let mut a = z; for i in 0..xs.len() { a = op(a, xs[i]); } a }
fn fsum<T: Copy>(xs: &[T], z: T) -> T { xs.iter().fold(z, |a, b| a) }
#[grade(exact, cross_device)] fn f(x: &[f32]) -> f32 { canon::nan(fsum(x, 0.0f32)) }"####),
    ("nx/N63", "E-MONO-DEPTH", "", r####"fn f<F: Fn()>(g: F, n: u32) { if n > 0 { f(|| g(), n - 1) } }
fn h() { f(|| (), 3) }"####),
    ("c1:t01", "E-MOVE-USED", "", r####"fn f(o: Option<Vec<u32>>) -> usize { let a = o; let b = o; 0 }"####),
    ("c1:t02", "E-MOVE-USED", "", r####"fn f(o: Result<Vec<u32>, u32>) -> usize { let a = o; let b = o; 0 }"####),
    ("c1:t03", "E-TYPE", "", r####"fn f(x: u32) -> u64 { x }"####),
    ("c1:t04", "E-TYPE", "", r####"fn f(x: u32, y: u64) -> u64 { x as u64 + y + x }"####),
    ("c1:t05", "E-TYPE", "", r####"enum E { A, B, C } fn f(e: E) -> u32 { match e { E::A => 1, E::B => 2 } }"####),
    ("c1:t06", "E-TYPE", "", r####"fn f(x: u32) -> u32 { match x { 0 => 1, 1 => 2 } }"####),
    ("c1:t07", "E-TYPE", "", r####"fn f(o: Option<u32>) -> u32 { match o { Some(x) => x } }"####),
    ("c1:t08", "E-TYPE", "", r####"fn f() -> u8 { let x: u8 = 300; x }"####),
    ("c1:t09", "E-TYPE", "", r####"fn f(v: &[u32]) { v[0] = 1; }"####),
    ("c1:t10", "E-TYPE", "", r####"fn f<T>(a: T, b: T) -> bool { a == b }"####),
    ("c1:t11", "E-TYPE", "", r####"fn f<T>(a: &T) -> T { a.clone() }"####),
    ("c1:t12", "E-TYPE", "", r####"fn f(x: u32) -> u32 { if x > 0 { 1 } }"####),
    ("c1:t13", "E-TYPE", "", r####"fn f(x: u32) -> u32 { }"####),
    ("c1:t14", "E-TYPE", "", r####"fn g(a: u32, b: u32) -> u32 { a } fn f() -> u32 { g(1) }"####),
    ("c1:t15", "E-TYPE", "", r####"struct S { a: u32 } fn f() -> S { S { } }"####),
    ("c1:t16", "E-TYPE", "", r####"struct S { a: u32 } fn f() -> S { S { a: 1, b: 2 } }"####),
    ("c1:t17", "E-TYPE", "", r####"fn f(x: i32) -> u32 { x }"####),
    ("c1:t18", "E-TYPE", "", r####"fn f() -> u32 { let v: Vec<u32> = Vec::new(); v }"####),
    ("c1:t19", "E-TYPE", "", r####"fn f(x: Option<u32>) -> u32 { x + 1 }"####),
    ("c1:t20", "E-TYPE", "", r####"fn f(x: f32) -> f32 { x + 1 }"####),
    ("c1:t21", "E-TYPE", "", r####"fn f(x: u32) -> bool { x }"####),
    ("c1:t22", "E-TYPE", "", r####"fn f(x: u32) -> u32 { -x }"####),
    ("c1:t23", "E-TYPE", "", r####"fn f(x: &mut u32) { let y: &u32 = x; *y = 3; }"####),
    ("c1:t24", "E-TYPE", "", r####"fn f() { let x = 5; x.foo(); }"####),
    ("c1:t25", "E-TYPE", "", r####"fn f(x: u32) -> u32 { x << 1u64 >> "a" }"####),
    ("c1:t26", "E-TYPE", "", r####"fn f(x: (u32, u32)) -> u32 { x.2 }"####),
    ("c1:t27", "E-TYPE", "", r####"fn f() -> u32 { let a = [1u32, 2, 3]; a[0usize..1] }"####),
    ("c1:t28", "E-TYPE", "", r####"fn f(c: bool) -> u32 { let x = if c { 1u32 } else { 2u64 }; 0 }"####),
    ("c1:t29", "E-TYPE", "", r####"fn f() { let mut v = Vec::new(); v.push(1u32); v.push(1u64); }"####),
    ("c1:t30", "E-TYPE", "", r####"fn f() -> u32 { let x = loop { break 5u64; }; x }"####),
    ("c1:t31", "E-TYPE", "", r####"fn f() { let c = |x: u32| x + 1; let y: u64 = c(1); }"####),
    ("c1:t32", "E-TYPE", "", r####"trait T { fn m(&self) -> u32; } struct S; impl T for S { } fn f() {}"####),
    ("c1:t33", "E-TYPE", "", r####"trait T { fn m(&self) -> u32; } struct S; impl T for S { fn m(&self) -> u64 { 0 } }"####),
    ("c1:t34", "E-TYPE", "", r####"fn f(x: u32) -> u32 { let y = x; y = 3; y }"####),
    ("c1:t35", "E-TYPE", "", r####"struct S { a: u32 } impl S { fn set(&self) { self.a = 1; } }"####),
    ("c1:t36", "E-TYPE", "", r####"fn f(x: &u32) -> u32 { x }"####),
    ("c1:t37", "E-TYPE", "", r####"fn f() -> u32 { 5u32 / 0 + "x".len() }"####),
    ("c1:t38", "E-TYPE", "", r####"fn f(x: u32) -> u32 { return; }"####),
    ("c1:t39", "E-TYPE", "", r####"fn f() -> i32 { let x: u8 = 1; let y: i8 = 2; (x + y) as i32 }"####),
    ("c1:t40", "E-TYPE", "", r####"fn f() -> usize { let s = "abc"; s[0] as usize }"####),
    ("c2:i01", "E-TYPE", "", r####"trait T { fn m(&self, a: u32) -> u32; } struct S; impl T for S { fn m(&self) -> u32 { 0 } }"####),
    ("c2:i02", "E-TYPE", "", r####"trait T { fn m(&self) -> u32; } struct S; impl T for S { fn m(&mut self) -> u32 { 0 } }"####),
    ("c2:i03", "E-TYPE", "", r####"trait T { fn m(&self) -> u32; } struct S; impl T for S { fn m(&self) -> u32 { 0 } fn z(&self) {} }"####),
    ("c2:i04", "E-TYPE", "", r####"trait T { fn m(&self, a: u32) -> u32; } struct S; impl T for S { fn m(&self, a: u64) -> u32 { 0 } }"####),
    ("c2:i05", "E-TYPE", "", r####"trait T { fn m(&self) -> u32; } struct S; impl T for S { fn m(self) -> u32 { 0 } }"####),
    ("c2:i07", "E-TYPE", "", r####"struct S; impl S { fn m(&self) -> u32 { 0 } fn m(&self) -> u32 { 1 } }"####),
    ("c2:i08", "E-TYPE", "", r####"fn f() -> u32 { 0 } fn f() -> u32 { 1 }"####),
    ("c2:i09", "E-TYPE", "", r####"struct S { a: u32, a: u32 }"####),
    ("c2:i10", "E-TYPE", "", r####"fn f(a: u32, a: u32) -> u32 { a }"####),
    ("c2:i11", "E-TYPE", "", r####"enum E { A, A }"####),
    ("c2:i12", "E-TYPE", "", r####"struct S { a: u32 } fn f() -> S { S { a: 1, a: 2 } }"####),
    ("c3:s01", "E-SPECIALIZE", "", r####"trait T { fn m(&self) -> u32; } impl<X> T for X { default fn m(&self) -> u32 { 0 } }"####),
    ("c3:s02", "E-COHERENCE", "", r####"trait T { fn m(&self) -> u32; } impl<X> T for X { fn m(&self) -> u32 { 0 } } impl T for u32 { fn m(&self) -> u32 { 1 } }"####),
    ("c3:s03", "E-COHERENCE", "", r####"impl Clone for u32 { fn clone(&self) -> u32 { 0 } }"####),
    ("c3:s04", "E-COHERENCE", "", r####"struct S; impl Clone for S { fn clone(&self) -> S { S } } impl Clone for S { fn clone(&self) -> S { S } }"####),
    ("c3:s05", "E-COHERENCE", "", r####"#[derive(Clone)] struct S; impl Clone for S { fn clone(&self) -> S { S } }"####),
    ("c12:y01", "E-TYPE", "", r####"#[derive(Copy, Clone)] struct S { v: Vec<u32> } fn f(s: S) -> usize { let t = s; s.v.len() + t.v.len() }"####),
    ("c12:y02", "E-TYPE", "", r####"struct S { v: Vec<u32> } impl Clone for S { fn clone(&self) -> S { S { v: self.v.clone() } } } impl Copy for S {} fn f(s: S) -> usize { let t = s; s.v.len() }"####),
    ("c12:y03", "E-TYPE", "", r####"#[derive(Copy)] struct S { a: u32 } fn f() {}"####),
    ("c12:y05", "E-TYPE", "", r####"struct T; #[derive(Clone)] struct S { t: T } fn f() {}"####),
    ("c12:y06", "E-TYPE", "", r####"struct T; #[derive(Debug)] struct S { t: T } fn f(s: &S) -> String { format!("{:?}", s) }"####),
    ("c12:y07", "E-TYPE", "", r####"struct T; fn f(t: &T) -> String { format!("{}", t) }"####),
    ("c12:y08", "E-TYPE", "", r####"struct T; fn f(a: &T, b: &T) -> bool { a == b }"####),
    ("c12:y09", "E-TYPE", "", r####"struct T; fn f(v: &mut Vec<T>) { v.sort(); }"####),
    ("c12:y10", "E-TYPE", "", r####"#[derive(PartialEq)] struct T(f32); fn f(v: &mut Vec<T>) -> bool { v[0] < v[1] }"####),
    ("c12:y11", "E-TYPE", "", r####"fn f(v: &mut Vec<f32>) { v.sort(); }"####),
    ("c12:y12", "E-TYPE", "", r####"struct T; fn f(v: Vec<T>) -> Vec<T> { v.clone() }"####),
    ("c13:z01", "E-TYPE", "", r####"fn f(v: &[f32]) -> Option<f32> { v.iter().copied().max() }"####),
    ("c13:z02", "E-TYPE", "", r####"fn f(v: &[u32]) -> u64 { v.iter().sum() }"####),
    ("c13:z03", "E-TYPE", "", r####"fn f(v: &[u32]) -> String { v.iter().sum() }"####),
    ("c13:z04", "E-TYPE", "", r####"struct T; fn f(v: &[T], t: &T) -> bool { v.contains(t) }"####),
    ("c13:z05", "E-TYPE", "", r####"struct T; fn f(v: &[T]) -> Vec<T> { v.to_vec() }"####),
    ("c13:z06", "E-TYPE", "", r####"fn f(a: f32, b: f32) -> f32 { std::cmp::max(a, b) }"####),
    ("c13:z07", "E-TYPE", "", r####"fn f(a: f32, b: f32) -> std::cmp::Ordering { a.cmp(&b) }"####),
];

#[test]
fn surface_cases() {
    let bad = common::run_cases(SURFACE_CASES);
    assert!(bad.is_empty(), "{} of {} cases differ:\n{}", bad.len(), SURFACE_CASES.len(), bad.join("\n"));
}

/// the X1 agent subset (X1 DESIGN 9.1)
const AGENT_SUBSET: &[(&str, &str, &str, &str)] = &[
    ("c10:x01", "E-X1-NOTYET-INCLUDE", "--subset agent", r####"fn f() -> usize { let s = include_str!("a.txt"); s.len() }"####),
    ("c10:x02", "E-X1-NOTYET-ENV", "--subset agent", r####"fn f() -> usize { let s = env!("HOME"); s.len() }"####),
    ("c10:x03", "E-X1-NOTYET-INCLUDE", "--subset agent", r####"fn f() -> usize { let s = include_bytes!("a.bin"); s.len() }"####),
    ("c10:x04", "E-X1-NOTYET-PATH", "--subset agent", r####"#[path = "x.rs"] mod m;"####),
    ("c10:x05", "E-X1-NOTYET-CANON", "--subset agent", r####"fn f(x: &mut [f32]) { canon::softmax(x); }"####),
    ("c10:x07", "E-KERNEL-OBLIGATION", "--subset agent", r####"kernel fn f(a: &[u32], i: usize) -> u32 { a[i] }"####),
];

#[test]
fn agent_subset() {
    let bad = common::run_cases(AGENT_SUBSET);
    assert!(bad.is_empty(), "{} of {} cases differ:\n{}", bad.len(), AGENT_SUBSET.len(), bad.join("\n"));
}

/// companion cases
const REVISER_SURFACE: &[(&str, &str, &str, &str)] = &[
    ("reviser:i06-two-impls", "E-COHERENCE", "", r####"trait T { fn m(&self) -> u32; } struct S; impl T for S { fn m(&self) -> u32 { 0 } } impl T for S { fn m(&self) -> u32 { 1 } }"####),
    ("reviser:y04-fn-pointer-eq", "accept", "", r####"#[derive(PartialEq)] struct T; #[derive(PartialEq)] struct S { t: T, f: fn(u32) } fn f() {}"####),
    ("reviser:escape-110000", "E-PARSE", "", r####"fn f() -> char { '\u{110000}' }"####),
    ("reviser:escape-surrogate", "E-PARSE", "", r####"fn f() -> char { '\u{D800}' }"####),
    ("reviser:continue-label-block", "E-TYPE", "", r####"fn e() { loop { 'x: { continue 'x; } } }"####),
    ("reviser:break-unlabelled-in-block", "E-TYPE", "", r####"fn d() { 'x: { if true { break; } } }"####),
    ("reviser:format-unknown-type", "E-TYPE", "", r####"fn f() -> String { format!("{:Q}", 10) }"####),
    ("reviser:format-unused-arg", "E-TYPE", "", r####"fn f() -> String { format!("{0}", 1, 2) }"####),
    ("reviser:format-display-missing", "E-TYPE", "", r####"struct T;
fn h(t: &T) -> String { format!("{}", t) }"####),
    ("reviser:default-fn", "E-SPECIALIZE", "", r####"trait T { fn m(&self) -> u32; } struct S; impl T for S { default fn m(&self) -> u32 { 0 } }"####),
];

#[test]
fn reviser_surface() {
    let bad = common::run_cases(REVISER_SURFACE);
    assert!(bad.is_empty(), "{} of {} cases differ:\n{}", bad.len(), REVISER_SURFACE.len(), bad.join("\n"));
}
