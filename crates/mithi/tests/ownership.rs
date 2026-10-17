//! Ownership and borrowing against Rust's verdicts (note sections 5.4, 5.6, 5.8): programs Rust
//! rejects must be rejected with the note's code, and ordinary programs Rust accepts must be
//! accepted. Written by mithi's author from Rust's rules (rustc was not run on them [inference]);
//! a regression suite for the bugs found on 2026-10-16 (moves out of references, partial moves,
//! loans through std calls and reborrows, two-phase borrows, method probing for `clone`).

use mithi::check::{check, Config};
use mithi::diag::FileRole;
use mithi::lower::SourceInput;

const CASES: &[(&str, &str, &str)] = &[
    ("a16", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32> } fn g(mut s: S) { let r = &mut s.a; let q = &mut s.b; r.push(1); q.push(1); }"#),
    ("a17", "accept", r#"fn g() { let mut v = vec![1u32]; let r = &mut v; r.push(1); v.push(2); }"#),
    ("a18", "accept", r#"fn g() { let mut v = vec![1u32]; v.push(v.len() as u32); }"#),
    ("a31", "accept", r#"fn g() -> u32 { let mut x = 1u32; { let r = &mut x; *r += 1; } x }"#),
    ("a32", "accept", r#"fn g(v: &mut Vec<u32>) { let n = v.len(); v.push(n as u32); }"#),
    ("a34", "accept", r#"fn g(o: &mut Option<Vec<u32>>) -> Vec<u32> { o.take().unwrap_or(Vec::new()) }"#),
    ("d1", "E-BORROW-CONFLICT", r#"fn g() { let mut v = vec![1u32]; let it = v.iter(); v.push(2); let n = it.count(); }"#),
    ("d2", "E-BORROW-CONFLICT", r#"fn g() { let mut v = vec![1u32]; let s: &[u32] = &v; let it = s.iter(); v.push(2); let n = it.count(); }"#),
    ("d3", "E-BORROW-CONFLICT", r#"fn g() { let mut v = vec![1u32]; let s: &[u32] = &v; v.push(2); let n = s.len(); }"#),
    ("d5", "E-BORROW-CONFLICT", r#"fn g() { let mut v = [1u32, 2]; let it = v.iter(); v[0] = 2; let n = it.count(); }"#),
    ("d6", "E-BORROW-CONFLICT", r#"fn g() { let mut v = vec![1u32]; let x = v.first(); v.push(2); let n = x.is_some(); }"#),
    ("r01", "E-MOVE-USED", r#"fn f(v: Vec<u32>) {} fn g() -> usize { let v = vec![1u32]; f(v); v.len() }"#),
    ("r02", "E-BORROW-CONFLICT", r#"fn g() -> usize { let mut v = vec![1u32]; let r = &v; v.push(1); r.len() }"#),
    ("r03", "E-BORROW-CONFLICT", r#"fn g() { let mut v = vec![1u32]; let a = &mut v; let b = &mut v; a.push(1); b.push(2); }"#),
    ("r04", "E-REF-ESCAPE", r#"fn g() -> &u32 { let x = 1u32; &x }"#),
    ("r05", "E-BORROW-CONFLICT", r#"fn g() { let mut v = vec![1u32]; for x in v.iter() { v.push(*x); } }"#),
    ("r06", "E-BORROW-CONFLICT", r#"fn g() -> usize { let mut v = vec![1u32]; let mut c = || v.push(1); let r = &v; c(); r.len() }"#),
    ("r07", "E-MOVE-LOOP", r#"fn f(v: Vec<u32>) {} fn g() { let v = vec![1u32]; for _i in 0..2 { f(v); } }"#),
    ("r08", "E-TYPE", r#"fn g() -> u32 { let x = 1u32; x = 2; x }"#),
    ("r09", "E-TYPE", r#"fn f(v: &Vec<u32>) { v.push(1); }"#),
    ("r10", "E-TYPE", r#"fn g() { let v: Vec<u32> = Vec::new(); v.push(1); }"#),
    ("r11", "E-MOVE-USED", r#"fn g() -> u32 { let x: u32; x + 1 }"#),
    ("r12", "E-MOVE-USED", r#"fn f(v: Vec<u32>) {} fn g(c: bool) -> usize { let v = vec![1u32]; if c { f(v); } v.len() }"#),
    ("r14", "E-BORROW-CONFLICT", r#"fn g() -> usize { let mut v = vec![1u32]; let r = &v; v = vec![2u32]; r.len() }"#),
    ("r15", "E-BORROW-CONFLICT", r#"struct S { a: Vec<u32>, b: Vec<u32> } fn g(mut s: S) -> usize { let r = &s.a; s.a.push(1); r.len() }"#),
    ("r19", "E-MOVE-USED", r#"fn g() { let v = vec![1u32]; let c = move || { let w = v; w.len() }; c(); c(); }"#),
    ("r23", "E-TYPE", r#"struct S { a: u32 } fn g() { let s = S { a: 1 }; s.a = 2; }"#),
    ("r24", "E-TYPE", r#"fn f(x: u32) -> u32 { x += 1; x }"#),
    ("r25", "E-BORROW-CONFLICT", r#"fn g() -> usize { let mut v = vec![1u32]; let first = &v[0]; v.clear(); *first as usize }"#),
    ("r26", "E-BORROW-OUTLIVE", r#"fn g(v: &mut Vec<u32>) -> &u32 { let x = 5u32; v.push(x); &x }"#),
    ("r27", "E-BORROW-CONFLICT", r#"fn g() { let mut s = String::new(); let r = &s; s.push_str("a"); let n = r.len(); }"#),
    ("r28", "E-BORROW-CONFLICT", r#"fn f(a: &mut u32, b: &mut u32) {} fn g() { let mut x = 1u32; f(&mut x, &mut x); }"#),
    ("r29", "E-BORROW-CONFLICT", r#"fn g() { let mut x = 1u32; let r = &x; x += 1; let y = *r; }"#),
    ("r30", "E-BORROW-CONFLICT", r#"fn g() -> Vec<u32> { let v = vec![1u32]; let r = &v; drop(v); r.clone() }"#),
    ("r33", "E-MOVE-BORROWED", r#"fn g(o: &mut Option<Vec<u32>>) -> Vec<u32> { match *o { Some(v) => v, None => Vec::new() } }"#),
    ("r35", "E-BORROW-CONFLICT", r#"fn g() { let mut v = vec![1u32]; let it = v.iter(); v.push(2); let n = it.count(); }"#),
    ("a40", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g() { let mut v = vec![1u32, 2]; for x in v.iter_mut() { *x += 1; } }"#),
    ("a41", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g() -> u32 { let mut v = vec![3u32, 1]; v.sort(); v[0] }"#),
    ("a42", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn f(s: &mut S) { s.a.push(1); s.b.push(2); }"#),
    ("a43", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g() { let mut m = [0u32; 4]; let (a, b) = m.split_at_mut(2); a[0] = b[0]; }"#),
    ("a44", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g() { let mut v = vec![1u32]; let n = v.len(); v[n - 1] = 5; }"#),
    ("a45", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g(mut s: S) { let r = &mut s; r.a.push(1); s.b.push(2); }"#),
    ("a46", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g() -> usize { let v = vec![String::new()]; let mut n = 0; for s in &v { n += s.len(); } n }"#),
    ("a47", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g() -> Option<usize> { let mut best: Option<usize> = None; for i in 0..3 { if best.is_none() { best = Some(i); } } best }"#),
    ("a48", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g() { let mut v: Vec<u32> = vec![3]; while let Some(x) = v.pop() { if x == 0 { break; } v.push(x - 1); } }"#),
    ("a49", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn longest(xs: &[String]) -> usize { let mut best = 0; for s in xs { if s.len() > best { best = s.len(); } } best }"#),
    ("a50", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } impl S { fn add(&mut self, x: u32) { self.a.push(x); self.total += x; } }"#),
    ("a51", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g() -> usize { let mut s = String::new(); s.push_str("a"); let t = s.clone(); s.push_str(&t); s.len() }"#),
    ("a52", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g() { let mut v = vec![1u32, 2, 3]; let last = *v.last().unwrap(); v.push(last); }"#),
    ("a53", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn get(v: &Vec<u32>, i: usize) -> Option<&u32> { v.get(i) }"#),
    ("a54", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g() -> usize { let mut a = vec![1u32]; let b = &mut a; b.push(2); let c = &a; c.len() }"#),
    ("a55", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g() -> u32 { let mut count = 0u32; let mut inc = || count += 1; inc(); inc(); count }"#),
    ("a56", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g() { let mut v = vec![1u32]; { let first = &v[0]; let _y = *first; } v.push(2); }"#),
    ("a57", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn f(v: &mut Vec<u32>) { for i in 0..v.len() { v[i] *= 2; } }"#),
    ("a58", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn f(v: &mut [u32]) { let n = v.len(); if n > 0 { v.swap(0, n - 1); } }"#),
    ("a59", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } struct N { next: Option<Vec<u32>> } fn f(n: &mut N) -> Option<Vec<u32>> { n.next.take() }"#),
    ("a60", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn f(o: &Option<String>) -> usize { match o { Some(s) => s.len(), None => 0 } }"#),
    ("a61", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn f(o: &Option<String>) -> usize { if let Some(s) = o { s.len() } else { 0 } }"#),
    ("a62", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn f(v: &[String]) -> Vec<String> { v.iter().map(|s| s.clone()).collect() }"#),
    ("a63", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g() { let mut v = vec![1u32]; let x = v[0]; v[0] = x + 1; }"#),
    ("a64", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn f(s: &mut S) -> &mut Vec<u32> { &mut s.a }"#),
    ("a65", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g(s: S) -> usize { let S { a, b, total } = s; a.len() + b.len() + total as usize }"#),
    ("a66", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g(mut s: S) -> usize { let a = s.a; s = S { a: a, b: Vec::new(), total: 0 }; s.a.len() }"#),
    ("a68", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn f(v: &mut Vec<u32>) { v.retain(|x| *x > 1); }"#),
    ("a69", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g() -> u32 { let v = vec![1u32]; v.iter().map(|x| x * 2).sum() }"#),
    ("a70", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g() -> u32 { let mut grid = vec![vec![0u32; 3]; 3]; grid[1][2] = 5; grid[1][2] }"#),
    ("a71", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g(s: &S) -> u32 { let mut t = 0; for x in &s.a { t += *x; } t + s.total }"#),
    ("a72", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g(v: &mut Vec<String>) { let s = v[0].clone(); v.push(s); }"#),
    ("a73", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g(v: &mut Vec<u32>) -> u32 { let x = v[0]; v[1] = x; v[1] }"#),
    ("a74", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g(s: &mut S) { let n = s.a.len() as u32; s.total = n; }"#),
    ("a75", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g(s: &mut S) { s.total = s.a.len() as u32; }"#),
    ("a76", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g(mut s: S) -> S { s.total += 1; s }"#),
    ("a77", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g() -> String { let mut s = String::new(); for i in 0..3u32 { s.push_str(&format!("{}", i)); } s }"#),
    ("a78", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g(xs: &[u32]) -> Vec<u32> { let mut out = Vec::new(); for &x in xs { out.push(x); } out }"#),
    ("a79", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g(xs: &mut [u32]) { for x in xs.iter_mut() { *x = 0; } }"#),
    ("a80", "accept", r#"struct S { a: Vec<u32>, b: Vec<u32>, total: u32 } fn g(m: &mut Vec<Vec<u32>>) { let row = &mut m[0]; row.push(1); }"#),
    ("c1", "accept", r#"fn f(s: &String) -> String { s.clone() }"#),
    ("c2", "accept", r#"fn f(v: &[String]) -> Vec<String> { let r: Vec<String> = v.iter().map(|s| s.clone()).collect(); r }"#),
    ("c3", "accept", r#"fn f(v: &[u32]) -> Vec<u32> { v.iter().map(|s| *s + 1).collect() }"#),
    ("c4", "accept", r#"fn f(v: &[String]) -> Vec<String> { v.iter().cloned().collect() }"#),
    ("c5", "accept", r#"fn f(v: &[String]) -> Vec<usize> { v.iter().map(|s| s.len()).collect() }"#),
    ("c6", "accept", r#"fn f(v: &[String]) -> Vec<String> { let mut o = Vec::new(); for s in v.iter().map(|s| s.clone()) { o.push(s); } o }"#),
    ("m01", "E-BORROW-CONFLICT", r#"fn m1() -> u32 { let v = vec![1u32]; let r = &v; let w = v; r[0] }"#),
    ("m02", "E-MOVE-BORROWED", r#"struct Q { a: Vec<u32>, b: Vec<u32>, ab: Vec<u32> } fn m2(q: &Q) -> Vec<u32> { q.a }"#),
    ("m03", "accept", r#"struct Q { a: Vec<u32>, b: Vec<u32>, ab: Vec<u32> } fn ok_partial(q: Q) -> usize { let x = q.a; let y = q.b; x.len() + y.len() }"#),
    ("m04", "E-MOVE-USED", r#"struct Q { a: Vec<u32>, b: Vec<u32>, ab: Vec<u32> } fn bad_partial(q: Q) -> usize { let x = q.a; let z = q; x.len() + z.b.len() }"#),
    ("m05", "E-MOVE-USED", r#"struct Q { a: Vec<u32>, b: Vec<u32>, ab: Vec<u32> } fn bad_field_again(q: Q) -> usize { let x = q.a; let y = q.a; x.len() + y.len() }"#),
    ("m06", "accept", r#"struct Q { a: Vec<u32>, b: Vec<u32>, ab: Vec<u32> } fn ok_prefix_names(q: Q) -> usize { let x = q.a; let y = q.ab; x.len() + y.len() }"#),
    ("m07", "accept", r#"struct Q { a: Vec<u32>, b: Vec<u32>, ab: Vec<u32> } fn reinit(mut q: Q) -> usize { let x = q.a; q.a = vec![]; let y = q.a; x.len() + y.len() }"#),
    ("m08", "E-MOVE-BORROWED", r#"fn idx(v: Vec<Vec<u32>>) -> Vec<u32> { v[0] }"#),
    ("m09", "E-MOVE-BORROWED", r#"fn deref(r: &Vec<u32>) -> Vec<u32> { *r }"#),
    ("m10", "accept", r#"struct Q { a: Vec<u32>, b: Vec<u32>, ab: Vec<u32> } fn ok_wild(q: &Q) { let _ = q.a; }"#),
    ("m11", "accept", r#"fn iflet(o: Option<Vec<u32>>) -> usize { if let Some(x) = o { x.len() } else { 0 } }"#),
    // m12 as first written (`{ return x.len(); }`) is accepted by Rust: the move happens in the
    // matching arm only, which returns (review 2026-10-16; MIR moves per arm [inference])
    ("m12", "E-MOVE-USED", r#"fn iflet_bad(o: Option<Vec<u32>>) -> usize { if let Some(x) = o { x.len(); } let p = o; 0 }"#),
    ("m12b", "accept", r#"fn iflet_ret(o: Option<Vec<u32>>) -> usize { if let Some(x) = o { return x.len(); } let p = o; 0 }"#),
    ("m13", "E-MOVE-BORROWED", r#"struct Q2 { o: Option<Vec<u32>> } fn iflet_ref(q: &Q2) -> usize { if let Some(x) = q.o { x.len() } else { 0 } }"#),
    ("m14", "E-MOVE-LOOP", r#"struct Q { a: Vec<u32>, b: Vec<u32>, ab: Vec<u32> } fn loop_move(q: Q) -> usize { let mut n = 0; for _i in 0..2 { let x = q.a; n += x.len(); } n }"#),
];

#[test]
fn ownership_cases_match_rust() {
    let mut bad = vec![];
    for (id, want, src) in CASES {
        let mut cfg = Config::default();
        cfg.inputs.push(SourceInput { name: format!("{id}.mith"), text: format!("{src}
"), role: FileRole::User, module: String::new() });
        let c = check(&cfg);
        let got = match c.primary() {
            Some(d) if !c.errors().is_empty() => d.code.clone(),
            _ => "accept".to_string(),
        };
        if got != *want {
            let all: Vec<String> = c.errors().iter().map(|d| mithi::diag::render_text(c.sm(), d)).collect();
            bad.push(format!("{id}: want {want}, got {got}
{}", all.join("
")));
        }
    }
    assert!(bad.is_empty(), "{} of {} cases differ:
{}", bad.len(), CASES.len(), bad.join("
"));
}

#[test]
fn bodiless_functions_need_doc_mode() {
    // a free function needs a body (Rust); a signature alone is documentation shorthand (N-03)
    let src = "fn f(a: u32) -> u32;\nfn g() -> u32 { f(1) }\n";
    for (doc, want) in [(false, Some("E-TYPE")), (true, None)] {
        let mut cfg = Config::default();
        cfg.doc_snippets = doc;
        cfg.inputs.push(SourceInput { name: "bodiless.mith".into(), text: src.into(), role: FileRole::User, module: String::new() });
        let c = check(&cfg);
        assert_eq!(c.primary().map(|d| d.code.as_str()), want, "doc_snippets = {doc}");
    }
}
