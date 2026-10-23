//! Regression tests from the blind adversarial review of 2026-10-23 (one reviewer, Claude, same
//! family, independent context; verdicts.json read only after its predictions) and from the
//! reviser's companion cases. Ids are the reviewer's probe ids; `reviser:` marks a companion.
//!
//! Expected verdicts: for ownership, Rust's, measured with the pinned rustc 1.99.1 (58cf8f9c3,
//! x86_64-pc-windows-gnu, `--edition 2021`) on a Rust transcription of each case [M, laptop,
//! 2026-10-23; the transcriptions are in the session scratch area, mrv/rs/own]; for grades, `par`,
//! T2, rows and policies, the note's rules (docs/m0/core-calculus.md), whose Rust skeletons compile.
//! Run-time values are rustc's [M, same toolchain].

mod common;

/// Finding 1 (write targets) and finding 7 (the address grade of a call argument): writes through
/// references chosen by `if`/`match`, bound by patterns, returned by projections, moved, stored in
/// aggregates, and the `&mut` items std hands to closures.
const GRADE_WRITES: &[(&str, &str, &str, &str)] = &[
    ("h9", "E-GRADE", "", r####"fn w(o: &mut u32, k: u32) { *o = k; }
#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut y = 0u32; let mut z = 0u32; let r = if h > 1 { &mut y } else { &mut z }; w(r, 4); y }"####),
    ("h10", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut y = 0u32; let mut z = 0u32; let r = if h > 1 { &mut y } else { &mut z }; *r = 4; y }"####),
    ("h11", "E-GRADE", "", r####"fn w(o: &mut u32, k: u32) { *o = k; }
#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut a = [0u32; 2]; w(&mut a[(h % 2) as usize], 4); a[0] }"####),
    ("h12", "E-GRADE", "", r####"fn w(o: &mut u32, k: u32) { *o = k; }
#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut y = 0u32; let mut z = 0u32; let r = if h > 1 { &mut y } else { &mut z }; w(&mut *r, 4); y }"####),
    ("h13", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut y = 0u32; let mut z = 0u32; let r = if h > 1 { &mut y } else { &mut z }; let mut g = |k: u32| *r = k; g(4); y }"####),
    ("h16", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut y = 0u32; let mut z = 0u32; let mut r = &mut z; if h > 1 { r = &mut y; } *r = 4; y }"####),
    ("h17", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut y = 0u32; let mut z = 0u32; { let r = if h > 1 { &mut y } else { &mut z }; *r = 4; } y + z }"####),
    ("h18", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(m: &Mutex<u32>, c: bool) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut y = 0u32; let mut z = 0u32; let r = if c { &mut y } else { &mut z }; *r = h; y }"####),
    ("h19", "E-NAN-RAW-SINK", "", r####"#[grade(exact, cross_device)] fn f(x: f32, c: bool) -> f32 { let mut y = 0.0f32; let mut z = 0.0f32; let r = if c { &mut y } else { &mut z }; *r = x + 1.0; y }"####),
    ("h20", "E-NAN-RAW-SINK", "", r####"#[grade(exact, cross_device)] fn f(x: f32, c: bool) -> f32 { let mut y = 0.0f32; let mut z = 0.0f32; let r = match c { true => &mut y, false => &mut z }; *r = x + 1.0; y }"####),
    ("h22", "E-NAN-RAW-SINK", "", r####"#[grade(exact, cross_device)] fn f(x: f32) -> f32 { let mut y = 0.0f32; let o = Some(&mut y); if let Some(r) = o { *r = x + 1.0; } y }"####),
    ("h23", "E-NAN-RAW-SINK", "", r####"#[grade(exact, cross_device)] fn f(x: f32) -> f32 { let mut v = [0.0f32; 2]; if let Some(r) = v.get_mut(0) { *r = x + 1.0; } v[0] }"####),
    ("h24", "E-NAN-RAW-SINK", "", r####"#[grade(exact, cross_device)] fn f(x: f32) -> f32 { let mut v = [0.0f32; 2]; for r in v.iter_mut() { *r = x + 1.0; } v[0] }"####),
    ("h25", "E-NAN-RAW-SINK", "", r####"#[grade(exact, cross_device)] fn f(x: f32) -> f32 { let mut v = [0.0f32; 2]; { let (a, b) = v.split_at_mut(1); a[0] = x + 1.0; } v[0] }"####),
    ("h26", "E-GRADE", "", r####"fn fill(y: &mut [u32], m: &Mutex<u32>) uses { nondet } { let h = m.with_lock(|v| *v); for r in y.iter_mut() { *r = h; } }
#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let mut a = [0u32; 4]; fill(&mut a, m); a[0] }"####),
    ("h27", "E-GRADE", "", r####"fn fill(y: &mut [u32], m: &Mutex<u32>) uses { nondet } { let h = m.with_lock(|v| *v); if let Some(r) = y.get_mut(0) { *r = h; } }
#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let mut a = [0u32; 4]; fill(&mut a, m); a[0] }"####),
    ("reviser:as-mut", "E-NAN-RAW-SINK", "", r####"#[grade(exact, cross_device)] fn f(x: f32) -> f32 { let mut o = Some(0.0f32); if let Some(r) = o.as_mut() { *r = x + 1.0; } o.unwrap_or(0.0) }"####),
    ("reviser:for-each-iter-mut", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut a = [0u32; 4]; a.iter_mut().for_each(|r| *r = h); a[0] }"####),
    ("reviser:user-hof-mut-param", "E-GRADE", "", r####"fn each<F: FnMut(&mut u32)>(v: &mut [u32], mut f: F) { for x in v.iter_mut() { f(x); } }
#[grade(exact, cross_device)] fn g(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut a = [0u32; 4]; each(&mut a, |r| *r = h); a[0] }"####),
    ("reviser:tuple-ref", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut y = [0u32; 2]; let t = (&mut y, 1u32); t.0[0] = h; y[0] }"####),
    ("reviser:match-ref", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut y = 0u32; let mut z = 0u32; let r = match h { 0 => &mut y, _ => &mut z }; *r = 1; y }"####),
    ("reviser:projection", "E-GRADE", "", r####"fn first(v: &mut [u32]) -> &mut u32 { &mut v[0] }
#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut a = [0u32; 2]; *first(&mut a) = h; a[0] }"####),
    ("reviser:moved-ref", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut y = 0u32; let r = &mut y; let s = r; *s = h; y }"####),
    ("reviser:vec-of-refs", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet, alloc(Global) } { let h = m.with_lock(|v| *v); let mut y = 0u32; let mut v: Vec<&mut u32> = Vec::new(); v.push(&mut y); *v[0] = h; y }"####),
    ("reviser:swap-refs", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut y = 0u32; let mut z = 0u32; let mut r1 = &mut y; let mut r2 = &mut z; std::mem::swap(&mut r1, &mut r2); *r2 = h; y }"####),
    ("reviser:option-assigned", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut y = 0u32; let mut o: Option<&mut u32> = None; o = Some(&mut y); if let Some(r) = o { *r = h; } y }"####),
];

/// The accepted twins: the same shapes writing cross_device, canonical values.
const GRADE_WRITES_ACCEPTED: &[(&str, &str, &str, &str)] = &[
    ("reviser:h9-ok", "accept", "", r####"fn w(o: &mut u32, k: u32) { *o = k; }
#[grade(exact, cross_device)] fn f(c: bool) -> u32 { let mut y = 0u32; let mut z = 0u32; let r = if c { &mut y } else { &mut z }; w(r, 4); y }"####),
    ("reviser:h19-ok", "accept", "", r####"#[grade(exact, cross_device)] fn f(x: f32, c: bool) -> f32 { let mut y = 0.0f32; let mut z = 0.0f32; let r = if c { &mut y } else { &mut z }; *r = canon::nan(x + 1.0); y }"####),
    ("reviser:h22-ok", "accept", "", r####"#[grade(exact, cross_device)] fn f(x: f32) -> f32 { let mut y = 0.0f32; let o = Some(&mut y); if let Some(r) = o { *r = canon::nan(x + 1.0); } y }"####),
    ("reviser:h23-ok", "accept", "", r####"#[grade(exact, cross_device)] fn f(x: f32) -> f32 { let mut v = [0.0f32; 2]; if let Some(r) = v.get_mut(0) { *r = canon::nan(x + 1.0); } v[0] }"####),
    ("reviser:h24-ok", "accept", "", r####"#[grade(exact, cross_device)] fn f(x: f32) -> f32 { let mut v = [0.0f32; 2]; for r in v.iter_mut() { *r = canon::nan(x + 1.0); } v[0] }"####),
    ("reviser:h25-ok", "accept", "", r####"#[grade(exact, cross_device)] fn f(x: f32) -> f32 { let mut v = [0.0f32; 2]; { let (a, b) = v.split_at_mut(1); a[0] = canon::nan(x + 1.0); b[0] = 2.0; } v[0] }"####),
    ("reviser:h26-ok", "accept", "", r####"fn fill(y: &mut [u32], k: u32) { for r in y.iter_mut() { *r = k; } }
#[grade(exact, cross_device)] fn f(k: u32) -> u32 { let mut a = [0u32; 4]; fill(&mut a, k); a[0] }"####),
    ("reviser:as-mut-ok", "accept", "", r####"#[grade(exact, cross_device)] fn f(x: f32) -> f32 { let mut o = Some(0.0f32); if let Some(r) = o.as_mut() { *r = canon::nan(x + 1.0); } o.unwrap_or(0.0) }"####),
    ("reviser:for-each-ok", "accept", "", r####"#[grade(exact, cross_device)] fn f(k: u32) -> u32 { let mut a = [0u32; 4]; a.iter_mut().for_each(|r| *r = k); a[0] }"####),
    ("reviser:user-hof-ok", "accept", "", r####"fn each<F: FnMut(&mut u32)>(v: &mut [u32], mut f: F) { for x in v.iter_mut() { f(x); } }
#[grade(exact, cross_device)] fn g(k: u32) -> u32 { let mut a = [0u32; 4]; each(&mut a, |r| *r = k); a[0] }"####),
    ("reviser:moved-ref-ok", "accept", "", r####"#[grade(exact, cross_device)] fn f(k: u32) -> u32 { let mut y = 0u32; let r = &mut y; let s = r; *s = k; y }"####),
    ("reviser:vec-of-refs-ok", "accept", "", r####"#[grade(exact, cross_device)] fn f(k: u32) -> u32 uses { alloc(Global) } { let mut y = 0u32; let mut v: Vec<&mut u32> = Vec::new(); v.push(&mut y); *v[0] = k; y }"####),
    ("reviser:cover-still-ok", "accept", "", r####"#[grade(exact, cross_device)] fn f(x: &[f32], y: &mut [f32]) requires x.len() == y.len() { for i in 0..y.len() { y[i] = canon::nan(x[i]); } }"####),
    ("reviser:shared-iter-ok", "accept", "", r####"#[grade(exact, cross_device)] fn f(x: &[f32]) -> f32 { let mut s = 0.0f32; for v in x.iter() { s = canon::nan(s + *v); } s }"####),
];

/// Finding 5: T-Cover premise 3 with an implicit reborrow of the `&mut` parameter.
const COVER: &[(&str, &str, &str, &str)] = &[
    ("e1b", "E-NAN-RAW-SINK", "", r####"fn poke(z: &mut [f32]) { z[0] = z[0] + 1.0; }
#[grade(exact, cross_device)] fn k(x: &[f32], y: &mut [f32]) requires x.len() == y.len() { for i in 0..y.len() { y[i] = canon::nan(x[i]); poke(y); } }"####),
    ("e1c", "E-NAN-RAW-SINK", "", r####"fn poke(z: &mut [f32]) { z[0] = z[0] + 1.0; }
#[grade(exact, cross_device)] fn k(x: &[f32], y: &mut [f32]) requires x.len() == y.len() { for i in 0..y.len() { y[i] = canon::nan(x[i]); poke(&mut *y); } }"####),
    ("kc38", "E-NAN-RAW-SINK", "", r####"fn poke(z: &mut [f32]) { }
kernel fn k(x: &[f32], y: &mut [f32]) requires x.len() == y.len() { for i in 0..y.len() { y[i] = canon::nan(x[i]); poke(y); } }"####),
];

/// Finding 2: writes in a `par for` without an assignment or an explicit `&mut p`; finding 11.
const PAR: &[(&str, &str, &str, &str)] = &[
    ("c1", "E-PAR-DISJOINT", "", r####"fn set0(r: &mut [u32], i: usize) { r[0] = r[0] + i as u32; }
fn f(y: &mut [u32]) { par for i in 0..y.len() { set0(y, i); } }"####),
    ("pa14", "E-PAR-DISJOINT", "", r####"fn set(r: &mut [u32], i: usize) { r[i] = 1; }
fn f(y: &mut [u32]) { par for i in 0..y.len() { set(y, i); } }"####),
    ("c6", "E-PAR-DISJOINT", "", r####"fn f(n: usize) -> u32 { let mut s = 0u32; let mut g = |k: usize| s = s + k as u32; par for i in 0..n { g(i); } s }"####),
    ("c8", "E-PAR-DISJOINT", "", r####"fn f(n: usize) -> u32 { let mut s = [0u32; 1]; let mut g = || s[0] += 1; par for i in 0..n { g(); } s[0] }"####),
    ("pa15", "E-PAR-DISJOINT", "", r####"fn f(n: usize) -> u32 { let mut s = 0u32; let mut g = || s += 1; par for i in 0..n { g(); } s }"####),
    ("c10", "E-PAR-DISJOINT", "", r####"fn each<F: FnMut(usize)>(n: usize, mut f: F) { par for i in 0..n { f(i); } }
fn g(n: usize) -> u32 { let mut s = 0u32; each(n, |k| s = s + k as u32); s }"####),
    ("r1-unsize", "E-PAR-DISJOINT", "", r####"fn set0(r: &mut [u32], i: usize) { r[0] = r[0] * 10 + i as u32; }
fn g() -> u32 { let mut y = [0u32; 4]; let yy = &mut y; par for i in 0..4 { set0(yy, i); } y[0] }"####),
    ("pa11", "accept", "", r####"fn f(y: &mut [u32]) { par for i in 0..y.len() { let j = i; y[j] = 1; } }"####),
    ("reviser:fn-closure-outside-ok", "accept", "", r####"fn f(y: &mut [u32], x: &[u32]) requires x.len() == y.len() { let h = |k: usize| x[k] * 2; par for i in 0..y.len() { y[i] = h(i); } }"####),
    ("reviser:fn-param-ok", "accept", "", r####"fn each<F: Fn(usize)>(n: usize, f: F) { par for i in 0..n { f(i); } }"####),
    ("reviser:let-copy-shadowed", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [u32]) { par for i in 0..y.len() { let mut j = i; j = 0; y[j] = 1; } }"####),
];

/// Findings 3, 4, 6, 8, 9 and the note's F-107: closures, loans and symbolic loans. Each expected
/// verdict is rustc 1.99.1's on the Rust transcription [M]; Linear cases (no Rust analogue) follow
/// K-LinClo and T-Lin.
const OWNERSHIP: &[(&str, &str, &str, &str)] = &[
    ("a1", "accept", "", r####"struct S { a: u32 } fn eat(s: S) -> u32 { s.a } fn f() -> u32 { let s = S { a: 1 }; let c = move || eat(s); c() }"####),
    ("a2", "accept", "", r####"struct S { a: u32 } fn eat(s: S) -> u32 { s.a } fn f() -> u32 { let s = S { a: 1 }; let c = || eat(s); c() }"####),
    ("a3", "accept", "", r####"struct S { a: u32 } fn eat(s: S) -> u32 { s.a } fn f() { let o = Some(S { a: 1 }); let c = move || { match o { Some(x) => { eat(x); } None => {} } }; c(); }"####),
    ("a4", "E-MOVE-USED", "", r####"struct S { a: u32 } fn eat(s: S) -> u32 { s.a } fn f() -> u32 { let s = S { a: 1 }; let c = move || eat(s); c() + c() }"####),
    ("a5", "accept", "", r####"fn run<F: FnOnce() -> u32>(f: F) -> u32 { f() } struct S { a: u32 } fn eat(s: S) -> u32 { s.a } fn f() -> u32 { let s = S { a: 1 }; run(move || eat(s)) }"####),
    ("b1", "accept", "", r####"struct S { a: u32 } fn f() -> u32 { let s = S { a: 1 }; let c = move || s.a; c() }"####),
    ("b2", "accept", "", r####"struct S { a: u32 } fn f(o: Option<S>) -> S { let d = S { a: 0 }; o.unwrap_or_else(move || d) }"####),
    ("b3", "accept", "", r####"struct S { a: u32 } fn f(o: Option<S>) -> S { let d = S { a: 0 }; o.unwrap_or_else(|| d) }"####),
    ("b4", "accept", "", r####"fn f(v: Vec<u32>) -> usize { let c = move || { let w = v; w.len() }; c() }"####),
    ("ln06", "accept", "", r####"linear struct L { a: u32 }
fn mk() -> L { L { a: 1 } }
fn eat(l: L) { let L { a } = l; }
fn f() { let l = mk(); let c = move || eat(l); c(); }"####),
    ("reviser:linear-capture-not-consumed", "E-LINEAR-DROP", "", r####"linear struct L { a: u32 }
fn mk() -> L { L { a: 1 } }
fn eat(l: L) { let L { a } = l; }
fn f() -> u32 { let l = mk(); let c = move || l.a; let n = c(); n }"####),
    ("reviser:linear-closure-twice", "E-MOVE-USED", "", r####"linear struct L { a: u32 }
fn mk() -> L { L { a: 1 } }
fn eat(l: L) { let L { a } = l; }
fn f() { let l = mk(); let c = move || eat(l); c(); c(); }"####),
    ("d1", "accept", "", r####"fn set0(r: &mut [u32; 4], i: usize) { r[0] = i as u32; }
fn g() -> u32 { let mut y = [0u32; 4]; let yy = &mut y; for i in 0..4 { set0(yy, i); } y[0] }"####),
    ("d3", "accept", "", r####"fn set0(r: &mut [u32], i: usize) { r[0] = i as u32; }
fn g() -> u32 { let mut y = [0u32; 4]; let yy = &mut y; set0(yy, 1); set0(yy, 2); y[0] }"####),
    ("g1", "E-LOCAL-MUT-STORE", "", r####"fn put(o: &mut Vec<&u32>, d: &u32) uses { alloc(Global) } { let mut c = |x: &u32| o.push(x); c(d); }"####),
    ("reviser:g1-unannotated", "E-LOCAL-MUT-STORE", "", r####"fn put(o: &mut Vec<&u32>, d: &u32) uses { alloc(Global) } { let mut c = |x| o.push(x); c(d); }"####),
    ("g2", "E-BORROW-OUTLIVE", "", r####"fn g() -> u32 uses { alloc(Global) } { let mut v: Vec<&u32> = Vec::new(); { let z = 3u32; let mut c = || v.push(&z); c(); } *v[0] }"####),
    ("g3", "E-BORROW-OUTLIVE", "", r####"fn g() -> u32 uses { alloc(Global) } { let mut v: Vec<&u32> = Vec::new(); { let z = 3u32; [1u32].iter().for_each(|_| v.push(&z)); } *v[0] }"####),
    ("g4", "E-BORROW-OUTLIVE", "", r####"fn g() -> u32 uses { alloc(Global) } { let mut v: Vec<&u32> = Vec::new(); { let z = 3u32; let _ = Some(1u32).map(|_| v.push(&z)); } *v[0] }"####),
    ("g5", "E-BORROW-OUTLIVE", "", r####"fn g() -> u32 { let mut s: Option<&u32> = None; { let z = 3u32; let _ = Some(1u32).map(|_| { s = Some(&z); }); } *s.unwrap() }"####),
    ("g6", "E-BORROW-OUTLIVE", "", r####"fn g() -> u32 { let mut s: Option<&u32> = None; { let z = 3u32; let mut c = || { s = Some(&z); }; c(); } *s.unwrap() }"####),
    ("g7", "E-BORROW-OUTLIVE", "", r####"fn run<F: FnMut()>(mut f: F) { f(); }
fn g() -> u32 { let mut s: Option<&u32> = None; { let z = 3u32; run(|| { s = Some(&z); }); } *s.unwrap() }"####),
    ("e2", "E-LOCAL-MUT-STORE", "", r####"fn put(t: (&mut Vec<&u32>, &u32)) uses { alloc(Global) } { let (v, d) = t; v.push(d); }
fn main2() -> u32 uses { alloc(Global) } { let mut v: Vec<&u32> = Vec::new(); { let x = 7u32; put((&mut v, &x)); } *v[0] }"####),
    ("reviser:same-position-ok", "accept", "", r####"fn f(v: &mut Vec<&u32>) uses { alloc(Global) } { let x = v[0]; v.push(x); }"####),
    ("f14", "E-LOCAL-MUT-STORE", "", r####"fn put<F: FnMut(&u32)>(mut f: F) { let z = 1u32; f(&z); }
fn g() -> bool { let mut slot: Option<&u32> = None; put(|d| { slot = Some(d); }); slot.is_some() }"####),
    ("f15", "E-LOCAL-MUT-STORE", "", r####"fn put<F: FnMut(&u32)>(mut f: F) { let z = 41u32; f(&z); }
fn g() -> u32 { let mut slot: Option<&u32> = None; put(|d| { slot = Some(d); }); *slot.unwrap() + 1 }"####),
    ("reviser:annotated-for-each-ok", "accept", "", r####"fn g() -> u32 { let a = 1u32; let v = [2u32, 3]; let mut out = &a; v.iter().for_each(|x: &u32| out = x); *out }"####),
    ("reviser:annotated-map-ok", "accept", "", r####"fn g(v: &[u32]) -> u32 uses { alloc(Global) } { let w: Vec<&u32> = v.iter().map(|x: &u32| x).collect(); *w[0] }"####),
    ("ow05", "E-REF-ESCAPE", "", r####"fn f(v: &[u32]) -> &u32 { let l = [1u32, 2]; &l[0] }"####),
    ("ow31", "accept", "", r####"fn f(o: &mut Option<u32>) { if let Some(r) = o.as_mut() { *r = 3; } }"####),
    ("br/b12", "E-BORROW-OUTLIVE", "", r####"fn f() -> u32 { let a = 0u32; let mut r = &a; { let b = 7u32; let mut o = Some(&b); std::mem::swap(&mut r, o.as_mut().unwrap()); } *r }"####),
    ("reviser:clone-closure-ok", "accept", "", r####"fn h() -> usize uses { alloc(Global) } { let v = vec![1u32]; let c = move || v.len(); let d = c.clone(); c() + d() }"####),
    ("reviser:clone-closure-mut", "E-TYPE", "", r####"fn h() -> u32 { let mut n = 0u32; let mut c = || { n += 1; n }; let d = c.clone(); c() }"####),
];

/// Finding 10 (T2): remainders, right shifts and values merged from two branches.
const T2: &[(&str, &str, &str, &str)] = &[
    ("kc27", "accept", "", r####"kernel fn k(y: &mut [u32], j: usize) requires y.len() > 0 { y[j % y.len()] = 1; }"####),
    ("e4", "accept", "", r####"kernel fn k(y: &mut [u32], j: usize) requires y.len() > 0 { let n = y.len(); let m = j % n; y[m] = 1; }"####),
    ("f5", "accept", "", r####"kernel fn k(i: usize, y: &mut [u32]) requires i < y.len() { y[i >> 1] = 1; }"####),
    ("kc10", "accept", "", r####"kernel fn k(i: usize, y: &mut [u32]) requires y.len() >= 1 { let j = if i < y.len() { i } else { 0 }; y[j] = 1; }"####),
    ("reviser:phi-assign-ok", "accept", "", r####"kernel fn k(i: usize, y: &mut [u32]) requires y.len() >= 1 { let mut j = 0usize; if i < y.len() { j = i; } y[j] = 1; }"####),
    ("reviser:rem-wrong-modulus", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(y: &mut [u32], j: usize) requires y.len() > 0 { y[j % (y.len() + 1)] = 1; }"####),
    ("reviser:shr-plus-one", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(i: usize, y: &mut [u32]) requires i < y.len() { y[(i >> 1) + 1] = 1; }"####),
    ("reviser:phi-wrong-branch", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(i: usize, y: &mut [u32]) requires y.len() >= 1 { let j = if i < y.len() { i } else { y.len() }; y[j] = 1; }"####),
];

/// Findings 12, 13: row labels and policy helpers.
const SURFACE: &[(&str, &str, &str, &str)] = &[
    ("rw08", "E-GRANT-UNSAFE", "", r####"fn f() uses { unsafe } { }"####),
    ("u1", "E-GRANT-FOREIGN", "", r####"fn f() uses { foreign } { }"####),
    ("po10", "E-TO-CALL", "--canonical-prelude", r####"fn h(n: usize) -> usize { let mut i = 0usize; while i < n { i += 1; } i }
policy fn p(slots: &[SlotView], now: Tick) -> Hint<usize> { Hint::some(h(slots.len())) }"####),
];

#[test]
fn grade_write_targets() {
    let bad = common::run_cases(GRADE_WRITES);
    assert!(bad.is_empty(), "{} of {} cases differ:\n{}", bad.len(), GRADE_WRITES.len(), bad.join("\n"));
    let bad = common::run_cases(GRADE_WRITES_ACCEPTED);
    assert!(bad.is_empty(), "{} of {} cases differ:\n{}", bad.len(), GRADE_WRITES_ACCEPTED.len(), bad.join("\n"));
}

#[test]
fn cover_premise_three() {
    let bad = common::run_cases(COVER);
    assert!(bad.is_empty(), "{} of {} cases differ:\n{}", bad.len(), COVER.len(), bad.join("\n"));
}

#[test]
fn par_writes_through_calls_and_closures() {
    let bad = common::run_cases(PAR);
    assert!(bad.is_empty(), "{} of {} cases differ:\n{}", bad.len(), PAR.len(), bad.join("\n"));
}

#[test]
fn closures_and_loans() {
    let bad = common::run_cases(OWNERSHIP);
    assert!(bad.is_empty(), "{} of {} cases differ:\n{}", bad.len(), OWNERSHIP.len(), bad.join("\n"));
}

#[test]
fn t2_relations() {
    let bad = common::run_cases(T2);
    assert!(bad.is_empty(), "{} of {} cases differ:\n{}", bad.len(), T2.len(), bad.join("\n"));
}

#[test]
fn rows_and_policies() {
    let bad = common::run_cases(SURFACE);
    assert!(bad.is_empty(), "{} of {} cases differ:\n{}", bad.len(), SURFACE.len(), bad.join("\n"));
}

/// Rust's meaning [M: rustc 1.99.1 prints `1 2 3 2 0`, `110`, `1`]: a copied or cloned closure
/// owns a copy of its by-move state, a closure called in place keeps its state, and
/// `mem::swap(&mut r1, &mut r2)` swaps the references (T = &mut u32), not the referents.
#[test]
fn closure_state_and_swap_have_rusts_meaning() {
    let src = r#"
fn h() -> u32 { let mut n = 0u32; let mut c = move || { n += 1; n }; let mut d = c; d(); c() }
fn h2() -> u32 { let mut n = 0u32; let mut c = move || { n += 1; n }; c(); c() }
fn h3() -> u32 { let mut n = 0u32; let mut c = move || { n += 1; n }; let r = &mut c; r(); r(); c() }
fn run<F: FnMut() -> u32>(mut f: F) -> u32 { f(); f() }
fn h4() -> u32 { let mut n = 0u32; let c = move || { n += 1; n }; run(c) }
fn leak(h: u32) -> u32 { let mut s = 0u32; let mut c = move |x: u32| { let o = s; s = x; o }; let mut d = c; d(h); c(0) }
fn l7() -> u32 { leak(7) }
fn cl() -> u32 { let mut n = 0u32; let mut c = move || { n += 1; n }; let mut d = c.clone(); d(); d(); c() }
fn sw() -> u32 { let mut y = 1u32; let mut z = 2u32; let mut r1 = &mut y; let mut r2 = &mut z; std::mem::swap(&mut r1, &mut r2); *r1 = 10; y * 100 + z }
fn am() -> u32 { let mut o = Some(1u32); if let Some(r) = o.as_mut() { *r = 5; } o.unwrap() }
"#;
    for (entry, want) in [("h", "1"), ("h2", "2"), ("h3", "3"), ("h4", "2"), ("l7", "0"), ("cl", "1"), ("sw", "110"), ("am", "5")] {
        let got = common::run_entry(src, "", entry).unwrap_or_else(|e| panic!("{entry} trapped: {e}"));
        assert_eq!(got, want, "{entry}");
    }
}
