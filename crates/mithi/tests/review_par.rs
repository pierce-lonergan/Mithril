//! Regression tests from the review of 2026-10-16 (two reviewers, Claude, same family,
//! independent context). Each case is a reviewer's probe or a reviser's companion case; its
//! expected verdict is Rust's (rustc was not run [inference]) or the note's, and mithi's verdict was
//! checked against it when the table was generated. Where a probe's stated expectation was judged
//! wrong, the case records the verdict the reviser defends and the README review log says why.
//! T-Par: lossless casts only, non-zero constant factors, one index function or a stride per
//! place, whole-place reads of written places, labelled jumps, projection footprints.

mod common;

/// reviewer probes (par, c6, c7)
const PAR_CASES: &[(&str, &str, &str, &str)] = &[
    ("par/d01", "E-PAR-DISJOINT", "", r####"fn f(x: &[u32]) -> u32 { let mut s = 0u32; par for i in 0..x.len() { s += x[i]; } s }"####),
    ("par/d02", "accept", "", r####"fn f(y: &mut [u32]) { par for i in 0..y.len() / 2 { y[2 * i] = 1; } }"####),
    ("par/d03", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [u32]) { par for i in 0..y.len() { y[i / 2] = 1; } }"####),
    ("par/d04", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [u32]) { par for i in 0..y.len() { y[i % 2] = 1; } }"####),
    ("par/d05", "accept", "", r####"fn f(y: &mut [u32]) { let n = y.len(); par for i in 0..n { y[n - 1 - i] = 1; } }"####),
    ("par/d06", "E-PAR-RACE", "", r####"fn f(y: &mut [u32]) requires y.len() > 0 { par for i in 0..y.len() - 1 { y[i] = y[i + 1]; } }"####),
    ("par/d07", "E-PAR-BREAK", "", r####"fn f(y: &mut [u32]) { par for i in 0..y.len() { if y[i] == 0 { break; } y[i] = 1; } }"####),
    ("par/d08", "E-PAR-DISJOINT", "", r####"fn f(v: &mut Vec<u32>, n: usize) { par for i in 0..n { v.push(i as u32); } }"####),
    ("par/d09", "E-PAR-EFFECT", "", r####"fn f(m: &Mutex<u32>, n: usize) uses { nondet } { par for i in 0..n { m.with_lock(|s| *s += 1); } }"####),
    ("par/d10", "E-PAR-DISJOINT", "", r####"fn g(y: &mut [u32]) { y[0] = 1; }
fn f(y: &mut [u32]) { par for i in 0..y.len() { g(&mut *y); } }"####),
    ("par/d11", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [u32], idx: &[usize]) { par for i in 0..idx.len() { y[idx[i]] = 1; } }"####),
    ("par/d12", "accept", "", r####"fn f(y: &mut [u32], x: &[u32]) requires x.len() == y.len() { par for i in 0..y.len() { y[i] = x[i] + 1; } }"####),
    ("par/d13", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [u32]) { let mut k = 0usize; par for i in 0..y.len() { k = i; y[i] = 1; } }"####),
    ("par/d14", "E-PAR-RACE", "", r####"fn f(y: &mut [u32]) requires y.len() > 0 { par for i in 0..y.len() { y[i] = y[0] + 1; } }"####),
    ("par/d15", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [u32]) { par for i in 0..y.len() { let r = &mut y[0]; *r = i as u32; } }"####),
    ("par/d16", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [[u32; 2]]) { par for i in 0..y.len() { y[0][i % 2] = 1; } }"####),
    ("par/d17", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [u32]) { par for i in 0..y.len() { let mut w = || y[0] = 1; w(); } }"####),
    ("par/d18", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [u32], j: usize) { par for i in 0..y.len() { y[j] = i as u32; } }"####),
    ("par/d19", "E-PAR-RACE", "", r####"fn f(y: &mut [u32], z: &mut [u32]) requires z.len() == y.len() { par for i in 0..y.len() { y[i] = 1; z[i] = y[(i + 1) % y.len()]; } }"####),
    ("par/d20", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [u32]) { par for i in 0..y.len() { y.swap(i, 0); } }"####),
    ("par/d21", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [u32]) { par for i in 0..y.len() { y[i] = 1; par for j in 0..y.len() { y[j] = 2; } } }"####),
    ("par/d22", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [u32]) { par for i in 0..y.len() { for j in 0..y.len() { y[j] = i as u32; } } }"####),
    ("par/d23", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [u32]) requires y.len() >= 4 { par for i in 0..4 { let s = &mut y[i..i + 2]; s[0] = 1; } }"####),
    ("par/d24", "accept", "", r####"fn f(y: &mut [u32]) requires y.len() >= 8 { par for i in 0..4 { let s = &mut y[2 * i..2 * i + 2]; s[0] = 1; s[1] = 2; } }"####),
    ("par/d25", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [u32], h: bool) { par for i in 0..y.len() { if h { y[i] = 1; } else { y[0] = 2; } } }"####),
    ("par/d26", "E-PAR-RACE", "", r####"fn f(y: &mut [u32]) { par for i in 0..y.len() { y[i] = 1; let t = y.len(); let s = y.iter().count(); } }"####),
    ("par/d27", "E-PAR-DISJOINT", "", r####"struct S { a: [u32; 4], n: u32 }
fn f(s: &mut S) { par for i in 0..4 { s.a[i] = 1; s.n = 2; } }"####),
    ("par/d28", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [u32]) { par for i in 0..y.len() { y[(i * 3) % y.len()] = 1; } }"####),
    ("par/d29", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [u32]) { par for i in 0..y.len() { y[i & 1] = 1; } }"####),
    ("par/d30", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [u32]) { par for i in 0..y.len() { y[(i as u8) as usize] = 1; } }"####),
    ("par/d31", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [u32]) { par for i in 0..y.len() { y[i * 0] = 1; } }"####),
    ("par/d32", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [u32]) { par for i in 0..y.len() { y[i.wrapping_mul(2)] = 1; } }"####),
    ("par/e01", "E-PAR-RACE", "", r####"fn f(y: &mut [u32]) -> u32 { let mut out = [0u32; 8]; par for i in 0..y.len() { y[i] = 1; let r = &*y; out[i % 8] = r[0]; } out[0] }"####),
    ("par/e02", "E-PAR-RACE", "", r####"fn f(y: &mut [u32], z: &mut [u32]) requires z.len() == y.len() { par for i in 0..y.len() { y[i] = 1; z[i] = y.iter().count() as u32; } }"####),
    ("par/e03", "E-PAR-RACE", "", r####"fn f(y: &mut [u32], z: &mut [u32]) requires z.len() == y.len() { par for i in 0..y.len() { y[i] = 1; z[i] = y.to_vec()[0]; } }"####),
    ("par/e04", "E-PAR-RACE", "", r####"fn s(v: &[u32]) -> u32 { v[0] }
fn f(y: &mut [u32], z: &mut [u32]) requires z.len() == y.len() { par for i in 0..y.len() { y[i] = 1; z[i] = s(&*y); } }"####),
    ("par/e05", "E-PAR-RACE", "", r####"fn f(y: &mut [u32], z: &mut [u32]) requires z.len() == y.len() && y.len() > 2 { par for i in 0..y.len() { y[i] = 1; z[i] = y[1..2][0]; } }"####),
    ("par/e06", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [u32]) requires y.len() >= 512 { par for i in 0..512 { y[(i as u8) as usize] = 1; } }"####),
    ("par/e07", "accept", "", r####"fn f(y: &mut [u32]) requires y.len() >= 8 { par for i in 0..4 { y[2 * i] = 1; y[2 * i + 1] = 2; } }"####),
    ("par/e08", "accept", "", r####"fn f(y: &mut [u32]) { let n = y.len(); par for i in 0..n { y[(n - 1) - i] = 1; } }"####),
    ("par/e09", "E-PAR-RACE", "", r####"fn f(y: &mut [u32], z: &mut [u32]) requires z.len() == y.len() { par for i in 0..y.len() { y[i] = 1; for v in y.iter() { z[i] = *v; } } }"####),
    ("par/e10", "E-PAR-RACE", "", r####"fn f(y: &mut [u32], z: &mut [u32]) requires z.len() == y.len() { par for i in 0..y.len() { y[i] = 1; let c = || y[0]; z[i] = c(); } }"####),
    ("par/f01", "E-PAR-DISJOINT", "", r####"const Z: usize = 0;
fn f(y: &mut [u32]) { par for i in 0..y.len() { y[i * Z] = i as u32; } }
fn t() -> u32 { let mut y = [9u32; 4]; f(&mut y); y[0] }"####),
    ("par/f02", "E-PAR-RACE", "", r####"fn f(y: &mut [u32], z: &mut [u32]) requires z.len() == y.len() && y.len() <= 1000 { par for i in 0..y.len() { y[i] = 1; z[i] = y[((i + 1) as u8) as usize % y.len()]; } }"####),
    ("par/f03", "E-PAR-RACE", "", r####"fn f(y: &mut [u32], z: &mut [u32]) requires z.len() == y.len() { par for i in 0..y.len() { y[i] = 1; z[i] = y[(i as u8) as usize]; } }"####),
    ("par/q01", "accept", "", r####"fn ret_before_trap(xs: &[u32]) -> Result<u32, usize> {
    let mut out = [0u32; 6];
    par for i in 0..xs.len() {
        if xs[i] == 0 { return Err(i); }
        out[i] = 100 / (xs[i] - 1);
    }
    Ok(out[0])
}
fn a() -> usize { match ret_before_trap(&[5u32, 3, 0, 1, 0, 2]) { Err(i) => i, Ok(_) => 99 } }
fn b() -> usize { match ret_before_trap(&[5u32, 1, 0, 2]) { Err(i) => i, Ok(_) => 99 } }
fn nested() -> u32 {
    let xs = [[1u32, 1, 1], [1u32, 4294967295, 1], [4294967295u32, 1, 1]];
    let mut out = [[0u32; 3]; 3];
    par for i in 0..3 {
        par for j in 0..3 {
            out[i][j] = xs[i][j] + 1;
        }
    }
    out[0][0]
}
fn partial() -> u32 {
    let mut out = [0u32; 5];
    let xs = [1u32, 2, 0, 4, 0];
    let r = fill(&mut out, &xs);
    out[0] + out[1] + out[3] + out[4]
}
fn fill(out: &mut [u32], xs: &[u32]) -> Result<(), usize> {
    par for i in 0..out.len() {
        if xs[i] == 0 { return Err(i); }
        out[i] = xs[i];
    }
    Ok(())
}
fn cont() -> u32 {
    let mut out = [0u32; 4];
    par for i in 0..4 {
        if i == 1 { continue; }
        out[i] = 1;
    }
    out[0] + out[1] + out[2] + out[3]
}"####),
    ("c6:p01", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [f32]) { let n = y.len(); par for i in 0..n { y[0] = 1.0; } }"####),
    ("c6:p02", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [f32]) { let n = y.len(); par for i in 0..n { y[i / 2] = 1.0; } }"####),
    ("c6:p03", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [f32]) { let n = y.len(); par for i in 0..n { y[i % 4] = 1.0; } }"####),
    ("c6:p04", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [f32]) { let n = y.len() - 1; par for i in 0..n { y[i] = 1.0; y[i + 1] = 2.0; } }"####),
    ("c6:p05", "E-PAR-RACE", "", r####"fn f(y: &mut [f32]) { let n = y.len() - 1; par for i in 0..n { y[i] = y[i + 1]; } }"####),
    ("c6:p06", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [f32]) -> u32 { let n = y.len(); let mut s = 0u32; par for i in 0..n { s += 1; } s }"####),
    ("c6:p07", "E-PAR-DISJOINT", "", r####"fn f(y: &mut Vec<f32>) { par for i in 0..4 { y.push(1.0); } }"####),
    ("c6:p08", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [f32], idx: &[usize]) { let n = idx.len(); par for i in 0..n { y[idx[i]] = 1.0; } }"####),
    ("c6:p09", "E-PAR-DISJOINT", "", r####"struct S { c: u32 } fn f(st: &mut S) { par for i in 0..4 { st.c += 1; } }"####),
    ("c6:p10", "E-PAR-DISJOINT", "", r####"fn bump(x: &mut f32) { *x += 1.0; } fn f(y: &mut [f32]) { par for i in 0..4 { bump(&mut y[0]); } }"####),
    ("c6:p11", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [f32], j: usize) { let n = y.len(); par for i in 0..n { y[j] = 1.0; } }"####),
    ("c6:p12", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [f32]) { let n = y.len(); let z = &mut *y; par for i in 0..n { z[0] = 1.0; } }"####),
    ("c6:p13", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [f32]) { let n = y.len(); par for i in 0..n { let k = 0usize; y[k] = 1.0; } }"####),
    ("c6:p14", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [f32]) { let n = y.len(); par for i in 0..n { let k = i - i; y[k] = 1.0; } }"####),
    ("c6:p15", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [f32]) { let n = y.len(); par for i in 0..n { let k = i * 0; y[k] = 1.0; } }"####),
    ("c6:p16", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [f32]) { let n = y.len(); par for i in 0..n { let mut k = i; k = 0; y[k] = 1.0; } }"####),
    ("c6:p17", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [f32]) { let n = y.len(); par for i in 0..n { for j in 0..n { y[j] = 1.0; } } }"####),
    ("c6:p18", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [f32]) { let n = y.len(); par for i in 0..n { if i > 0 { y[i - 1] = 1.0; } y[i] = 2.0; } }"####),
    ("c6:p19", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [[f32; 4]]) { let n = y.len(); par for i in 0..n { y[0][i % 4] = 1.0; } }"####),
    ("c6:p20", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [f32]) { let n = y.len(); par for i in 0..n { let r = &mut y[0]; *r = 1.0; } }"####),
    ("c6:p21", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [f32]) { let n = y.len(); par for i in 0..n { let s = &mut y[..]; s[0] = 1.0; } }"####),
    ("c6:p22", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [f32]) { let n = y.len(); par for i in 0..n { y.swap(0, i); } }"####),
    ("c6:p23", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [f32]) { let n = y.len(); par for i in 0..n { y[n - 1 - i] = 1.0; y[0] = 2.0; } }"####),
    ("c6:p24", "accept", "", r####"fn f(y: &mut [f32]) { let n = y.len(); par for i in 0..n { y[i] = 1.0; } }"####),
    ("c6:p25", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [f32]) { let n = y.len(); par for i in 0..n { y[(i + 1) % n] = y[i]; } }"####),
    ("c6:p26", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [f32]) { let n = y.len(); par for i in 0..n { y.reverse(); } }"####),
    ("c6:p27", "E-PAR-RACE", "", r####"fn f(y: &mut [f32]) { let n = y.len(); par for i in 0..n { let t = y[0]; y[i] = t; } }"####),
    ("c7:p28", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [f32]) { let n = y.len(); par for i in 0..n { y[(i as u8) as usize] = 1.0; } }"####),
    ("c7:p29", "E-PAR-DISJOINT", "", r####"const Z: usize = 0; fn f(y: &mut [f32]) { let n = y.len(); par for i in 0..n { y[i * Z] = 1.0; } }"####),
    ("c7:p30", "E-PAR-RACE", "", r####"fn f(y: &mut [f32]) { let n = y.len(); par for i in 0..n { let s: f32 = y.iter().sum(); y[i] = s; } }"####),
    ("c7:p31", "E-PAR-RACE", "", r####"fn tot(x: &[f32]) -> f32 { x[0] } fn f(y: &mut [f32]) { let n = y.len(); par for i in 0..n { let s = tot(y); y[i] = s; } }"####),
    ("c7:p32", "E-PAR-RACE", "", r####"fn f(y: &mut [f32]) { let n = y.len(); par for i in 0..n { let s = *y.first().unwrap(); y[i] = s; } }"####),
    ("c7:p33", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [f32]) { let n = y.len() / 2; par for i in 0..n { y[2 * i] = 1.0; y[i] = 2.0; } }"####),
    ("c7:p34", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [f32]) { let n = y.len(); par for i in 0..n { let k = i; y[k] = 1.0; y[i] = y[0]; } }"####),
    ("c7:p35", "E-PAR-RACE", "", r####"fn f(y: &mut [u32]) { let n = y.len(); par for i in 0..n { y[i] = 1; } par for i in 0..n { y[i] += y[n - 1 - i]; } }"####),
    ("c7:p36", "E-PAR-RACE", "", r####"struct S { a: Vec<f32>, b: Vec<f32> } fn f(s: &mut S) { let n = s.a.len(); par for i in 0..n { s.a[i] = s.a[0]; } }"####),
    ("c7:p37", "E-BORROW-CONFLICT", "", r####"fn f(y: &mut [f32]) { let n = y.len(); par for i in 0..n { let r = &y[0]; y[i] = *r; } }"####),
    ("c7:p38", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [f32], z: &mut [f32]) { let n = y.len(); par for i in 0..n { z[0] = y[i]; } }"####),
    ("c7:p40", "E-PAR-DISJOINT", "", r####"fn f(y: &mut [f32]) { let n = y.len(); par for i in 0..n { y[i] = 1.0; let w = &mut y[0..1]; w[0] = 2.0; } }"####),
];

#[test]
fn par_cases() {
    let bad = common::run_cases(PAR_CASES);
    assert!(bad.is_empty(), "{} of {} cases differ:\n{}", bad.len(), PAR_CASES.len(), bad.join("\n"));
}

/// race-free loops that must stay accepted
const PAR_ACCEPTED: &[(&str, &str, &str, &str)] = &[
    ("reviser:r01", "accept", "", r####"fn f(y: &mut [u32]) { let n = y.len(); par for i in 0..n { let v = y[i]; y[i] = v + 1; } }"####),
    ("reviser:r02", "accept", "", r####"fn f(y: &mut [u32]) { par for i in 0..y.len() { y[i] += 1; } }"####),
    ("reviser:r03", "accept", "", r####"fn dot(a: &[f32], b: &[f32]) -> f32 { a[0] * b[0] } fn f(y: &mut [f32], w: &[f32], x: &[f32], k: usize) requires w.len() == y.len() * k { par for r in 0..y.len() { y[r] = dot(&w[r * k..(r + 1) * k], x); } }"####),
    ("reviser:r04", "accept", "", r####"fn f(y: &mut [u32]) { par for i in 0..y.len() { if y[i] > 0 { y[i] = 0; } } }"####),
    ("reviser:r05", "accept", "", r####"fn f(y: &mut [usize], out: &mut [usize]) requires out.len() == y.len() { par for i in 0..y.len() { out[i] = y.len(); y[i] = 1; } }"####),
    ("reviser:r06", "accept", "", r####"fn f(y: &mut [u32], x: &[u32], m: usize) requires x.len() == y.len() * m { par for i in 0..y.len() { for j in 0..m { y[i] += x[i * m + j]; } } }"####),
    ("reviser:r07", "accept", "", r####"fn f(y: &mut [u32]) requires y.len() >= 8 { par for i in 0..4 { y[2 * i] = 1; y[2 * i + 1] = y[2 * i]; } }"####),
    ("reviser:r08", "accept", "", r####"struct P { a: [u32; 4], b: [u32; 4] } fn f(p: &mut P) { par for i in 0..4 { p.a[i] = p.b[i]; } }"####),
    ("reviser:r09", "accept", "", r####"fn f(y: &mut [u32], n: usize) requires y.len() >= n { par for i in 0..n { y[n - 1 - i] = 1; } }"####),
    ("reviser:r10", "accept", "", r####"fn f(y: &mut [[u32; 4]]) { par for i in 0..y.len() { y[i][0] = 1; y[i][1] = 2; } }"####),
    ("reviser:p39-same-element", "accept", "", r####"fn f(y: &mut [f32]) { let n = y.len(); par for i in 0..n { y[i + 0] = 1.0; y[0 + i] = 2.0; } }"####),
];

#[test]
fn par_accepted() {
    let bad = common::run_cases(PAR_ACCEPTED);
    assert!(bad.is_empty(), "{} of {} cases differ:\n{}", bad.len(), PAR_ACCEPTED.len(), bad.join("\n"));
}
