//! Regression tests from the review of 2026-10-16 (two reviewers, Claude, same family,
//! independent context). Each case is a reviewer's probe or a reviser's companion case; its
//! expected verdict is Rust's (rustc was not run [inference]) or the note's, and mithi's verdict was
//! checked against it when the table was generated. Where a probe's stated expectation was judged
//! wrong, the case records the verdict the reviser defends and the README review log says why.
//! Ownership and loans: places through references, loops, jumps, stores, closures, Linear arms.

mod common;

/// reviewer probes (br2, br3, c4, c5, c9, ln, ff2)
const REJECTS_AND_ACCEPTS: &[(&str, &str, &str, &str)] = &[
    ("br3/h01", "E-BORROW-CONFLICT", "", r####"fn f() -> u32 { let mut w = vec![1u32]; let v = &mut w; let r = &v[0]; v.push(1); *r }"####),
    ("br3/h02", "E-BORROW-CONFLICT", "", r####"fn f(v: &mut Vec<u32>) -> u32 { let r = &*v; v.push(1); r[0] }"####),
    ("br3/h03", "E-BORROW-CONFLICT", "", r####"fn f(v: &mut Vec<u32>) -> u32 { let r = &mut *v; v.push(1); r.push(2); 0 }"####),
    ("br3/h04", "E-BORROW-CONFLICT", "", r####"struct S { a: Vec<u32> }
fn f(s: &mut S) -> u32 { let r = &s.a[0]; s.a.push(1); *r }"####),
    ("br3/h05", "E-BORROW-CONFLICT", "", r####"fn f(v: &mut Vec<u32>) -> u32 { let r = v.first().unwrap(); v.push(1); *r }"####),
    ("br3/h06", "E-BORROW-CONFLICT", "", r####"fn f(v: &mut [u32]) { let a = &mut v[0]; let b = &mut v[0]; *a = 1; *b = 2; }"####),
    ("br3/h07", "E-BORROW-CONFLICT", "", r####"fn f(v: &mut Vec<u32>) -> u32 { let r = &v[0]; *v = Vec::new(); *r }"####),
    ("br3/h08", "E-BORROW-CONFLICT", "", r####"fn f(mut v: Vec<u32>) -> u32 { let r = &v[0]; v.push(1); *r }"####),
    ("br3/h09", "E-BORROW-CONFLICT", "", r####"fn f(x: &mut u32) -> u32 { let r = &*x; *x = 5; *r }"####),
    ("br2/e01", "E-LOCAL-MUT-STORE", "", r####"fn put(v: &mut Vec<&u32>, x: &u32) { v.push(x); }
fn g() -> u32 { let mut v: Vec<&u32> = Vec::new(); { let x = 5u32; put(&mut v, &x); } *v[0] }"####),
    ("br2/e02", "E-BORROW-OUTLIVE", "", r####"fn g() -> u32 { let a = 0u32; let mut r = &a; loop { let x = 9u32; r = &x; break; } *r }"####),
    ("br2/e03", "E-BORROW-OUTLIVE", "", r####"fn g() -> u32 { let a = 0u32; let mut r = &a; while true { let x = 9u32; r = &x; break; } *r }"####),
    ("br2/e04", "E-BORROW-OUTLIVE", "", r####"fn g(n: u32) -> u32 { let a = 0u32; let mut r = &a; for i in 0..n { let x = i; r = &x; if i == 2 { break; } } *r }"####),
    ("br2/e05", "E-BORROW-CONFLICT", "", r####"fn f(v: &mut Vec<u32>) -> u32 { let r = &v[0]; v.push(1); *r }"####),
    ("br2/e06", "E-BORROW-CONFLICT", "", r####"fn f(v: &mut Vec<u32>) -> u32 { let r = &mut v[0]; v.clear(); *r }"####),
    ("br2/e07", "E-BORROW-CONFLICT", "", r####"fn f(v: &mut [u32]) -> u32 { let r = &mut v[0]; let s = &mut v[0]; *s = 1; *r }"####),
    ("br2/e08", "E-BORROW-CONFLICT", "", r####"fn f() -> u32 { let mut v = vec![1u32]; let (a, b) = (&mut v, &v); a.push(1); b[0] }"####),
    ("br2/e09", "E-BORROW-CONFLICT", "", r####"fn f() -> u32 { let mut x = 1u32; let t = (&mut x, &x); *t.0 = 2; *t.1 }"####),
    ("br2/e10", "E-BORROW-CONFLICT", "", r####"fn f() -> u32 { let mut x = 1u32; let a = [&mut x, &mut x]; 0 }"####),
    ("br2/e12", "E-BORROW-CONFLICT", "", r####"fn f(s: &mut Vec<u32>) -> u32 { let r = s.last().unwrap(); s.push(*r); 0 }"####),
    ("br2/e13", "E-BORROW-CONFLICT", "", r####"fn f(v: &mut Vec<u32>) -> u32 { let it = v.iter(); v.push(2); it.count() as u32 }"####),
    ("br2/e14", "E-BORROW-CONFLICT", "", r####"fn f(v: &mut Vec<u32>) -> u32 { for x in v.iter() { v.push(*x); } 0 }"####),
    ("br2/e15", "E-BORROW-OUTLIVE", "", r####"fn g() -> u32 { let a = 0u32; let mut r = &a; let mut i = 0u32; loop { let x = 9u32; if i == 0 { r = &x; } i += 1; if i > 1 { break; } } *r }"####),
    ("br2/e16", "E-BORROW-OUTLIVE", "", r####"fn g() -> u32 { let a = 0u32; let mut r = &a; 'l: { let x = 9u32; r = &x; break 'l; } *r }"####),
    ("br2/e17", "E-BORROW-OUTLIVE", "", r####"fn g() -> u32 { let a = 0u32; let mut r = &a; loop { let x = 9u32; r = &x; if true { break; } } *r }"####),
    ("c4:o01", "E-BORROW-OUTLIVE", "", r####"fn f() -> u32 { let r; { let x = 1u32; r = &x; } *r }"####),
    ("c4:o02", "E-BORROW-CONFLICT", "", r####"fn first(v: &Vec<u32>) -> &u32 { &v[0] } fn f() -> u32 { let mut v = vec![1u32]; let r = first(&v); v.push(2); *r }"####),
    ("c4:o03", "E-BORROW-CONFLICT", "", r####"fn f() { let mut v = vec![1u32]; let r = &mut v; let s = &v; r.push(1); let n = s.len(); }"####),
    ("c4:o04", "E-MOVE-USED", "", r####"fn f() -> usize { let v = vec![1u32]; let c = move || v.len(); v.len() }"####),
    ("c4:o05", "E-MOVE-USED", "", r####"fn f() -> usize { let v = vec![1u32]; for x in v { } v.len() }"####),
    ("c4:o06", "E-MOVE-USED", "", r####"fn f(c: bool) -> usize { let v = vec![1u32]; let w = match c { true => v, false => vec![] }; v.len() }"####),
    ("c4:o08", "E-MOVE-USED", "", r####"fn f() -> usize { let v = vec![1u32]; let w = (v, 1u32); v.len() }"####),
    ("c4:o09", "E-MOVE-USED", "", r####"struct S { a: Vec<u32> } fn f() -> usize { let v = vec![1u32]; let s = S { a: v }; v.len() }"####),
    ("c4:o10", "E-MOVE-USED", "", r####"fn f() -> usize { let v = vec![1u32]; let w = [v]; v.len() }"####),
    ("c4:o12", "E-BORROW-CONFLICT", "", r####"fn f() { let mut v = vec![1u32, 2]; let a = &mut v[0]; let b = &mut v[1]; *a += *b; }"####),
    ("c4:o13", "E-BORROW-CONFLICT", "", r####"fn f() { let mut x = 1u32; let a = &mut x; let b = &mut *a; *a += 1; *b += 1; }"####),
    ("c4:o14", "E-BORROW-CONFLICT", "", r####"fn f() { let mut v = vec![1u32]; let r = &v; let c = || v.push(2); let n = r.len(); }"####),
    ("c4:o15", "E-BORROW-CONFLICT", "", r####"fn f() { let mut v = vec![vec![1u32]]; let r = &v[0]; v[0].push(1); let n = r.len(); }"####),
    ("c4:o16", "E-BORROW-CONFLICT", "", r####"fn f() { let mut s = (vec![1u32], 2u32); let r = &s; s.1 = 3; let n = r.0.len(); }"####),
    ("c4:o17", "E-BORROW-CONFLICT", "", r####"fn f(v: &mut Vec<u32>) { let r = &v[0]; v.push(*r); }"####),
    ("c4:o18", "E-BORROW-CONFLICT", "", r####"fn f(v: &mut Vec<u32>) { for x in v.iter() { if *x > 0 { v.clear(); } } }"####),
    ("c4:o19", "E-BORROW-CONFLICT", "", r####"fn f() { let mut v = vec![1u32]; let it = v.iter_mut(); let n = v.len(); for x in it { *x = 0; } }"####),
    ("c4:o20", "E-BORROW-CONFLICT", "", r####"fn f() { let mut o = Some(vec![1u32]); if let Some(x) = &o { o = None; let n = x.len(); } }"####),
    ("c4:o21", "E-BORROW-CONFLICT", "", r####"fn f() { let mut o = Some(vec![1u32]); match &mut o { Some(x) => { o = None; x.push(1); } None => {} } }"####),
    ("c4:o22", "E-BORROW-CONFLICT", "", r####"fn get(v: &mut Vec<u32>) -> &mut u32 { &mut v[0] } fn f() { let mut v = vec![1u32]; let a = get(&mut v); let b = get(&mut v); *a += *b; }"####),
    ("c4:o23", "E-BORROW-CONFLICT", "", r####"struct S { a: Vec<u32> } impl S { fn get(&self) -> &u32 { &self.a[0] } fn put(&mut self) { self.a.push(1); } } fn f(s: &mut S) { let r = s.get(); s.put(); let y = *r; }"####),
    ("c4:o24", "E-MOVE-BORROWED", "", r####"fn f(v: &Vec<String>) -> String { let s = v[0]; s }"####),
    ("c4:o25", "E-MOVE-BORROWED", "", r####"fn f(v: &[String]) -> String { for s in v.iter() { return *s; } String::new() }"####),
    ("c4:o26", "E-MOVE-USED", "", r####"fn f() { let a = vec![1u32]; let b = a; let c = a.clone(); }"####),
    ("c4:o27", "E-BORROW-CONFLICT", "", r####"fn f() { let mut v = vec![1u32]; let r = &mut v; let w = &mut *r; r.push(0); w.push(1); }"####),
    ("c4:o28", "E-MOVE-USED", "", r####"fn take(v: Vec<u32>) {} fn f() { let v = vec![1u32]; let c = || take(v); c(); c(); }"####),
    ("c4:o29", "E-BORROW-CONFLICT", "", r####"fn f() { let mut a = [1u32, 2]; let r = &a[0]; a = [3, 4]; let y = *r; }"####),
    ("c4:o30", "E-BORROW-CONFLICT", "", r####"fn f() { let mut v = vec![1u32]; let s = &v[..]; v.push(1); let n = s.len(); }"####),
    ("c4:o31", "E-BORROW-CONFLICT", "", r####"fn f() { let mut v = vec![1u32]; let s = v.as_slice(); v.push(1); let n = s.len(); }"####),
    ("c4:o32", "E-MOVE-USED", "", r####"fn f(v: Vec<u32>) -> Vec<u32> { let w = if true { v } else { Vec::new() }; v }"####),
    ("c4:o33", "E-BORROW-CONFLICT", "", r####"fn f() { let mut x = 0u32; let mut c = || x += 1; let y = x; c(); }"####),
    ("c4:o34", "E-BORROW-CONFLICT", "", r####"fn f() { let mut x = 0u32; let r = &mut x; let y = x; *r = 1; }"####),
    ("c4:o35", "E-MOVE-USED", "", r####"#[derive(Clone)] struct S { v: Vec<u32> } fn f(s: S) -> S { let t = s; s }"####),
    ("c4:o37", "E-BORROW-CONFLICT", "", r####"fn f() { let mut v = vec![1u32]; let mut it = v.iter(); let a = it.next(); v.push(2); let b = a; }"####),
    ("c5:v01", "E-BORROW-CONFLICT", "", r####"struct S { a: Vec<u32> } impl S { fn get(&self) -> &u32 { &self.a[0] } fn put(&mut self) { self.a.push(1); } } fn f() { let mut s = S { a: vec![1] }; let r = s.get(); s.put(); let y = *r; }"####),
    ("c5:v02", "E-BORROW-CONFLICT", "", r####"struct S { a: Vec<u32> } fn get(s: &S) -> &u32 { &s.a[0] } fn put(s: &mut S) { s.a.push(1); } fn f(s: &mut S) { let r = get(s); put(s); let y = *r; }"####),
    ("c5:v03", "E-BORROW-CONFLICT", "", r####"fn f(v: &mut Vec<u32>) { let r = &v[0]; v.clear(); let y = *r; }"####),
    ("c5:v04", "E-BORROW-CONFLICT", "", r####"fn f(v: &mut Vec<u32>) { let it = v.iter(); v.clear(); let n = it.count(); }"####),
    ("c5:v05", "E-BORROW-CONFLICT", "", r####"fn f(v: &mut Vec<u32>) { for x in v.iter() { v.push(*x); } }"####),
    ("c5:v06", "E-BORROW-CONFLICT", "", r####"fn f() { let mut v = vec![1u32]; for x in v.iter() { if *x > 0 { v.clear(); } } }"####),
    ("c5:v07", "E-BORROW-CONFLICT", "", r####"fn f() { let mut v = vec![1u32]; let r = &mut v; let w = &mut *r; r.push(0); w.push(1); }"####),
    ("c5:v08", "E-BORROW-CONFLICT", "", r####"fn f() { let mut x = 1u32; let a = &mut x; let b = &mut *a; *a += 1; *b += 1; }"####),
    ("c5:v09", "E-BORROW-CONFLICT", "", r####"fn f(a: &mut u32) { let b = &mut *a; *a += 1; *b += 1; }"####),
    ("c5:v10", "E-BORROW-CONFLICT", "", r####"fn f() { let mut v = vec![1u32]; let a = v.iter().next(); v.push(2); let b = a; }"####),
    ("c5:v11", "E-BORROW-CONFLICT", "", r####"fn f() { let mut v = vec![1u32]; let mut it = v.iter(); let a = it.next(); v.push(2); let b = a; }"####),
    ("c5:v12", "E-BORROW-CONFLICT", "", r####"fn f(v: &mut Vec<u32>) { let r = v.first(); v.clear(); let y = r; }"####),
    ("c5:v13", "E-BORROW-CONFLICT", "", r####"fn f(v: &mut Vec<u32>) { let r = &mut v[0]; v.clear(); *r = 1; }"####),
    ("c5:v14", "E-BORROW-CONFLICT", "", r####"fn f(v: &mut Vec<u32>) { let w = &mut *v; v.clear(); w.push(1); }"####),
    ("c5:v15", "E-BORROW-CONFLICT", "", r####"fn f(v: &mut Vec<u32>) { let w: &Vec<u32> = v; v.clear(); let n = w.len(); }"####),
    ("c5:v16", "E-BORROW-CONFLICT", "", r####"fn f(v: &mut Vec<u32>) { let w = &*v; v.clear(); let n = w.len(); }"####),
    ("c5:v17", "E-BORROW-CONFLICT", "", r####"fn f(v: &mut Vec<u32>) { let w = &v; v.clear(); let n = w.len(); }"####),
    ("c5:v18", "E-BORROW-CONFLICT", "", r####"fn f() { let mut v = vec![1u32]; let p = &mut v; let w = &p[0]; p.clear(); let n = *w; }"####),
    ("c9:l01", "E-BORROW-CONFLICT", "", r####"fn f() -> u32 { let mut v = vec![1u32]; let z = 0u32; let mut r = &z; for _i in 0..2 { v.push(1); r = &v[0]; } *r }"####),
    ("c9:l02", "E-BORROW-CONFLICT", "", r####"fn f() -> usize { let mut v = vec![1u32]; let e: Vec<u32> = Vec::new(); let mut r = &e; for _i in 0..2 { v.push(1); r = &v; } r.len() }"####),
    ("c9:l03", "E-BORROW-CONFLICT", "", r####"fn f() -> usize { let mut v = vec![1u32]; let mut keep: Vec<&u32> = Vec::new(); for _i in 0..2 { v.push(1); keep.push(&v[0]); } keep.len() }"####),
    ("c9:l04", "E-BORROW-CONFLICT", "", r####"fn f() -> usize { let mut v = vec![1u32]; let e: Vec<u32> = Vec::new(); let mut a = &e; let mut b = &e; for _i in 0..3 { v.push(1); b = a; a = &v; } b.len() }"####),
    ("ln/m01", "accept", "", r####"linear struct T { id: u32 }
fn eat(t: T) -> u32 { let T { id } = t; id }
fn mk(i: u32) -> T { T { id: i } }
fn f(o: Option<T>) -> u32 { match o { Some(t) => eat(t), None => 0 } }"####),
    ("ln/m02", "accept", "", r####"linear struct T { id: u32 }
fn eat(t: T) -> u32 { let T { id } = t; id }
fn mk(i: u32) -> T { T { id: i } }
fn f(o: Option<T>) -> u32 { if let Some(t) = o { eat(t) } else { 0 } }"####),
    ("ln/m04", "accept", "", r####"linear struct T { id: u32 }
fn eat(t: T) -> u32 { let T { id } = t; id }
fn mk(i: u32) -> T { T { id: i } }
fn f(o: Option<T>) -> u32 { match o { Some(t) => eat(t), None => 0 } }
fn g() -> u32 { f(Some(mk(1))) }"####),
    ("ln/m05", "accept", "--canonical-prelude --module store", r####"linear struct T { id: u32 }
fn eat(t: T) -> u32 { let T { id } = t; id }
fn mk(i: u32) -> T { T { id: i } }
fn f(store: &Store, o: Option<Lease>) uses { io, spawn } { match o { Some(l) => store.release(l), None => {} } }"####),
    ("ln/l14", "accept", "", r####"linear struct T { id: u32 }
fn eat(t: T) -> u32 { let T { id } = t; id }
fn mk(i: u32) -> T { T { id: i } }
fn f() -> u32 { let o = Some(mk(1)); match o { Some(t) => eat(t), None => 0 } }"####),
    ("ff2/g01", "accept", "", r####"fn g<F: Fn(u32) -> u32>(op: F) -> u32 { let c = |x: u32| op(x); c(1) + op(2) }"####),
    ("ff2/g02", "accept", "", r####"fn h<T: Copy>(b: &T) -> T { *b }"####),
    ("ff2/g03", "accept", "", r####"fn h<T: Copy>(xs: &[T]) -> T { xs[0] }"####),
    ("ff2/g06", "accept", "", r####"fn g<F: FnMut(u32)>(mut op: F) { let mut c = |x: u32| op(x); c(1); c(2); op(3); }"####),
];

#[test]
fn rejects_and_accepts() {
    let bad = common::run_cases(REJECTS_AND_ACCEPTS);
    assert!(bad.is_empty(), "{} of {} cases differ:\n{}", bad.len(), REJECTS_AND_ACCEPTS.len(), bad.join("\n"));
}

/// ordinary Rust through `&mut` parameters, written by the reviser (false-rejection guard)
const ORDINARY_RUST_ACCEPTED: &[(&str, &str, &str, &str)] = &[
    ("reviser:q01", "accept", "", r####"struct S { a: Vec<u32>, b: usize } fn f(s: &mut S) { s.a.push(1); let n = s.a.len(); s.b = n; }"####),
    ("reviser:q02", "accept", "", r####"fn f(v: &mut Vec<u32>) { let n = v.len(); for i in 0..n { v[i] += 1; } }"####),
    ("reviser:q03", "accept", "", r####"fn f(v: &mut [u32]) { let (a, b) = v.split_at_mut(1); a[0] = b[0]; }"####),
    ("reviser:q04", "accept", "", r####"fn f(v: &mut Vec<u32>) -> u32 { let x = v[0]; v.push(x); x }"####),
    ("reviser:q05", "accept", "", r####"struct S { a: Vec<u32>, b: usize } fn f(s: &mut S) -> &mut Vec<u32> { &mut s.a }"####),
    ("reviser:q06", "accept", "", r####"fn f(v: &mut Vec<u32>) { let r = &mut v[0]; *r = 1; v.push(2); }"####),
    ("reviser:q07", "accept", "", r####"fn f(a: &mut u32) { let b = &mut *a; *b += 1; *a += 1; }"####),
    ("reviser:q08", "accept", "", r####"struct S { a: Vec<u32>, b: Vec<u32> } fn f(s: &mut S) { let r = &mut s.a; let q = &mut s.b; r.push(1); q.push(2); }"####),
    ("reviser:q09", "accept", "", r####"fn f(v: &mut Vec<u32>) { for x in v.iter_mut() { *x += 1; } v.push(0); }"####),
    ("reviser:q10", "accept", "", r####"fn f(m: &mut Vec<Vec<u32>>) { let n = m.len(); for i in 0..n { m[i].push(1); } }"####),
    ("reviser:q11", "accept", "", r####"fn f(v: &mut Vec<u32>) -> Option<&u32> { v.first() }"####),
    ("reviser:q12", "accept", "", r####"fn helper(v: &mut Vec<u32>) { v.push(1) } fn g(v: &mut Vec<u32>) { helper(v); helper(v); v.push(2); }"####),
    ("reviser:q13", "accept", "", r####"struct S { a: Vec<u32>, b: usize } fn g(s: &mut S) { let a = &s.a; let b = &s.a; let n = a.len() + b.len(); s.b = n; }"####),
    ("reviser:q14", "accept", "", r####"struct S { n: u32 } impl S { fn inc(&mut self) { self.n += 1; self.inc2(); } fn inc2(&mut self) { self.n += 2; } }"####),
    ("reviser:q15", "accept", "", r####"struct S { a: Vec<u32> } impl S { fn total(&self) -> u32 { let mut t = 0; for x in self.a.iter() { t += *x; } t } }"####),
    ("reviser:q16", "accept", "", r####"struct S { a: Vec<u32> } impl S { fn push_all(&mut self, xs: &[u32]) { for x in xs { self.a.push(*x); } } }"####),
    ("reviser:q17", "accept", "", r####"fn f(v: &mut Vec<u32>) { while let Some(x) = v.pop() { if x == 0 { break; } } }"####),
    ("reviser:q18", "accept", "", r####"fn f(xs: &[u32]) -> u32 { let mut best = &xs[0]; for x in xs { if x > best { best = x; } } *best }"####),
    ("reviser:q19", "accept", "", r####"fn f(v: &mut Vec<u32>) { let first = v[0]; let n = v.len(); let last = v[n - 1]; v[0] = last; v[n - 1] = first; }"####),
    ("reviser:q20", "accept", "", r####"struct S { a: Vec<u32>, b: usize } fn f(s: &mut S) { s.a.push(s.a.len() as u32); }"####),
    ("reviser:q21", "accept", "", r####"struct S { a: Vec<u32>, b: Vec<u32> } fn f(s: &mut S) { s.b.push(s.a[0]); }"####),
    ("reviser:q22", "accept", "", r####"fn f(v: &mut [f32], w: &[f32]) { for i in 0..v.len() { v[i] += w[i]; } }"####),
    ("reviser:q23", "accept", "", r####"struct St { cache: Vec<u32>, count: usize } impl St { fn update(&mut self, x: usize) { self.count = x; } } fn f(st: &mut St) { let x = st.cache.len(); st.update(x); }"####),
    ("reviser:q24", "accept", "", r####"struct St { cache: Vec<u32>, count: usize } fn f(st: &mut St) { let c = &mut st.cache; c.clear(); st.count += 1; }"####),
    ("reviser:q25", "accept", "", r####"fn f(o: Option<&mut u32>) { if let Some(r) = o { *r = 1; } }"####),
    ("reviser:q26", "accept", "", r####"fn f(o: &mut Option<Vec<u32>>) { if let Some(v) = o { v.push(1); } }"####),
    ("reviser:q27", "accept", "", r####"fn f(o: &mut Option<Vec<u32>>) { match o { Some(v) => v.push(1), None => {} } }"####),
    ("reviser:q28", "accept", "", r####"fn f(xs: &mut Vec<String>) { for s in xs.iter_mut() { s.push_str("a"); } }"####),
    ("reviser:q29", "accept", "", r####"fn f(v: &[u32]) -> usize { let mut i = 0; loop { if v[i] == 0 { break i; } i += 1; } }"####),
    ("reviser:q30", "accept", "", r####"fn f(v: &mut Vec<u32>) -> u32 { let r = &v[0]; let x = *r; v.push(x); x }"####),
    ("reviser:q31", "accept", "", r####"struct St { a: Vec<u32>, n: usize } impl St { fn get(&self, i: usize) -> u32 { self.a[i] } fn step(&mut self) { let x = self.get(0); self.a.push(x); self.n += 1; } }"####),
    ("reviser:q32", "accept", "", r####"fn f(v: &mut Vec<Vec<u32>>) { let row = &mut v[0]; row.push(1); let row2 = &mut v[1]; row2.push(2); }"####),
    ("reviser:q33", "accept", "", r####"fn f(v: &mut Vec<u32>) { let mut k = 0; for i in 0..v.len() { if v[i] > 0 { v[k] = v[i]; k += 1; } } v.truncate(k); }"####),
    ("reviser:q34", "accept", "", r####"fn f(s: &mut String, t: &str) { s.push_str(t); s.push_str(t); }"####),
    ("reviser:q35", "accept", "", r####"fn f(v: &mut Vec<u32>) -> u32 { let mut s = 0; for x in v.iter() { s += *x; } v.push(s); s }"####),
    ("reviser:q36", "accept", "", r####"fn f(a: &mut [u32], b: &mut [u32]) { for i in 0..a.len() { let t = a[i]; a[i] = b[i]; b[i] = t; } }"####),
    ("reviser:q37", "accept", "", r####"fn f(v: &mut Vec<u32>) { let w = &mut *v; w.push(1); v.push(2); }"####),
    ("reviser:q38", "accept", "", r####"fn g(x: &mut u32) -> &mut u32 { x } fn f(v: &mut u32) { let r = g(v); *r = 1; *v = 2; }"####),
    ("reviser:q39", "accept", "", r####"fn f(v: &mut Vec<&u32>, x: &u32) -> usize { v.len() + (*x as usize) }"####),
];

#[test]
fn ordinary_rust_accepted() {
    let bad = common::run_cases(ORDINARY_RUST_ACCEPTED);
    assert!(bad.is_empty(), "{} of {} cases differ:\n{}", bad.len(), ORDINARY_RUST_ACCEPTED.len(), bad.join("\n"));
}

/// companion cases for the fixes
const REVISER_EXTRAS: &[(&str, &str, &str, &str)] = &[
    ("reviser:break-move", "E-MOVE-USED", "", r####"fn k(v: Vec<u32>) -> usize { loop { let _x = v; break; } v.len() }"####),
    ("reviser:implicit-reborrow", "accept", "", r####"fn inc(x: &mut u32) { *x += 1; }
fn g(r: &mut u32) { inc(r); inc(r); *r += 1; }"####),
    ("reviser:for-iter-unbound", "E-BORROW-CONFLICT", "", r####"fn f(v: &mut Vec<u32>) { for _x in v.iter() { v.push(1); } }"####),
    ("reviser:linear-arm-drops", "E-LINEAR-DROP", "", r####"linear struct T { id: u32 }
fn eat(t: T) -> u32 { let T { id } = t; id }
enum E { A(T), B(T) }
fn f(e: E) -> u32 { match e { E::A(t) => eat(t), E::B(_) => 0 } }"####),
    ("reviser:linear-iflet-other-variant", "E-LINEAR-DROP", "", r####"linear struct T { id: u32 }
fn eat(t: T) -> u32 { let T { id } = t; id }
enum E { A(T), B(T) }
fn f(e: E) -> u32 { if let E::A(t) = e { eat(t) } else { 0 } }"####),
    ("reviser:continue-outlive", "E-BORROW-OUTLIVE", "", r####"fn g() -> u32 { let a = 0u32; let mut r = &a; for i in 0..2u32 { let x = i; r = &x; continue; } *r }"####),
    // review 2026-10-23: the annotated parameter `x: &u32` is higher-ranked, so the store is
    // E-LOCAL-MUT-STORE (F-107); rustc 1.99.1 rejects it with E0521 [M: scratch probe t1]. The
    // unannotated twin compiles [M: t2] and is accepted
    ("reviser:closure-transfer-ok", "E-LOCAL-MUT-STORE", "", r####"fn f(v: &[u32]) -> u32 { let mut best: Option<&u32> = None; let mut up = |x: &u32| { best = Some(x); }; for x in v.iter() { up(x); } match best { Some(b) => *b, None => 0 } }"####),
    ("reviser:closure-transfer-ok2", "accept", "", r####"fn f(v: &[u32]) -> u32 { let mut best: Option<&u32> = None; let mut up = |x| { best = Some(x); }; for x in v.iter() { up(x); } match best { Some(b) => *b, None => 0 } }"####),
    ("cl/c12", "E-REF-ESCAPE", "", r####"fn g(v: &Vec<u32>) -> u32 { let mut keep: Vec<u32> = Vec::new(); let mut f = |x: u32| -> &u32 { keep.push(x); &keep[0] }; *f(1) }"####),
    ("reviser:closure-by-ref-result-ok", "accept", "", r####"fn h(v: &[u32]) -> Option<&u32> { let c = |i: usize| v.get(i); c(0) }"####),
];

#[test]
fn reviser_extras() {
    let bad = common::run_cases(REVISER_EXTRAS);
    assert!(bad.is_empty(), "{} of {} cases differ:\n{}", bad.len(), REVISER_EXTRAS.len(), bad.join("\n"));
}
