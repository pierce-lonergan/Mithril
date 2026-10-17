//! Regression tests from the review of 2026-10-16 (two reviewers, Claude, same family,
//! independent context). Each case is a reviewer's probe or a reviser's companion case; its
//! expected verdict is Rust's (rustc was not run [inference]) or the note's, and mithi's verdict was
//! checked against it when the table was generated. Where a probe's stated expectation was judged
//! wrong, the case records the verdict the reviser defends and the README review log says why.
//! T2 (note section 5.10): path-sensitive intervals, writes through references, calls and closures,
//! signed shift amounts, `!=` facts, and the evaluation budget.

mod common;

/// reviewer probes (t2, budget)
const KERNEL_CASES: &[(&str, &str, &str, &str)] = &[
    ("t2/demo", "E-KERNEL-OBLIGATION", "", r####"kernel fn k14(x: u32, s: i32, y: &mut [u32]) requires y.len() == 1 && s < 32 { y[0] = x << s; }
kernel fn bump(n: &mut usize) { *n = 100; }
kernel fn k21(y: &mut [u32], i: usize) requires i < y.len() { let mut j = i; bump(&mut j); y[j] = 1; }
kernel fn k22(y: &mut [u32], i: usize) requires i < y.len() { let mut j = i; let r = &mut j; *r = 1000; y[j] = 1; }
kernel fn k24(y: &mut [u32], i: usize) requires i < y.len() { let mut j = i; let mut f = || j = 1000; f(); y[j] = 1; }
kernel fn k36(y: &mut [u32], i: usize) requires i < y.len() { let mut j = i; if i > 0 { j = i - 1; } else { j = y.len(); } y[j] = 1; }
fn t14() -> u32 { let mut y = [0u32; 1]; k14(1, -1, &mut y); y[0] }
fn t21() -> u32 { let mut y = [0u32; 4]; k21(&mut y, 0); y[0] }
fn t22() -> u32 { let mut y = [0u32; 4]; k22(&mut y, 0); y[0] }
fn t24() -> u32 { let mut y = [0u32; 4]; k24(&mut y, 0); y[0] }
fn t36() -> u32 { let mut y = [0u32; 4]; k36(&mut y, 0); y[0] }"####),
    ("t2/k01", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(a: u32, b: u32, y: &mut [u32]) requires y.len() == 1 { y[0] = a + b; }"####),
    ("t2/k02", "accept", "", r####"kernel fn k(a: u32, b: u32, y: &mut [u32]) requires y.len() == 1 { y[0] = a.wrapping_add(b); }"####),
    ("t2/k03", "accept", "", r####"kernel fn k(a: u8, y: &mut [u8]) requires y.len() == 1 && a < 16 { y[0] = a * a; }"####),
    ("t2/k04", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(a: u8, y: &mut [u8]) requires y.len() == 1 && a <= 16 { y[0] = a * a; }"####),
    ("t2/k05", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(a: u8, b: u8, y: &mut [u8]) requires y.len() == 1 && a < 17 && b < 17 { y[0] = a * b; }"####),
    ("t2/k06", "accept", "", r####"kernel fn k(a: i8, y: &mut [i8]) requires y.len() == 1 && a > -12 && a < 12 { y[0] = a * a; }"####),
    ("t2/k07", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(a: i8, y: &mut [i8]) requires y.len() == 1 && a > -13 && a < 12 { y[0] = a * a; }"####),
    ("t2/k08", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(a: u32, b: u32, y: &mut [u32]) requires y.len() == 1 && a + 1 >= b { y[0] = a - b; }"####),
    ("t2/k09", "accept", "", r####"kernel fn k(a: u32, b: u32, y: &mut [u32]) requires y.len() == 1 && a >= b { y[0] = a - b; }"####),
    ("t2/k10", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(a: i32, b: i32, y: &mut [i32]) requires y.len() == 1 && b != 0 { y[0] = a / b; }"####),
    ("t2/k11", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(a: i32, b: i32, y: &mut [i32]) requires y.len() == 1 && b != 0 { y[0] = a % b; }"####),
    ("t2/k12", "accept", "", r####"kernel fn k(a: i32, b: i32, y: &mut [i32]) requires y.len() == 1 && b > 0 { y[0] = a / b; }"####),
    ("t2/k13", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(x: u32, s: u32, y: &mut [u32]) requires y.len() == 1 && s <= 32 { y[0] = x << s; }"####),
    ("t2/k14", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(x: u32, s: i32, y: &mut [u32]) requires y.len() == 1 && s < 32 { y[0] = x << s; }"####),
    ("t2/k15", "accept", "", r####"kernel fn k(x: u32, s: u32, y: &mut [u32]) requires y.len() == 1 && s < 32 { y[0] = x << s; }"####),
    ("t2/k16", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(y: &mut [u8]) requires y.len() == 1 { let mut s: u8 = 0; for _i in 0..64 { s += 4; } y[0] = s; }"####),
    ("t2/k17", "accept", "", r####"kernel fn k(y: &mut [u8]) requires y.len() == 1 { let mut s: u8 = 0; for _i in 0..63 { s += 4; } y[0] = s; }"####),
    ("t2/k18", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(y: &mut [u32], n: usize) requires n <= y.len() { let mut j = 0usize; for _i in 0..n { y[j] = 1; j += 2; } }"####),
    ("t2/k19", "accept", "", r####"kernel fn k(y: &mut [u32]) { let mut i = 0usize; while i < y.len() { y[i] = 0; i += 1; } }"####),
    ("t2/k20", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(y: &mut [u32]) { let mut i = 0usize; while i <= y.len() { y[i] = 0; i += 1; } }"####),
    ("t2/k21", "E-KERNEL-OBLIGATION", "", r####"kernel fn bump(n: &mut usize) { *n = 100; }
kernel fn k(y: &mut [u32], i: usize) requires i < y.len() { let mut j = i; bump(&mut j); y[j] = 1; }"####),
    ("t2/k22", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(y: &mut [u32], i: usize) requires i < y.len() { let mut j = i; let r = &mut j; *r = 1000; y[j] = 1; }"####),
    ("t2/k23", "E-KERNEL-OBLIGATION", "", r####"struct P { a: usize }
kernel fn k(y: &mut [u32], i: usize) requires i < y.len() { let mut p = P { a: i }; p.a = 100; y[p.a] = 1; }"####),
    ("t2/k24", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(y: &mut [u32], i: usize) requires i < y.len() { let mut j = i; let mut f = || j = 1000; f(); y[j] = 1; }"####),
    ("t2/k25", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(y: &mut [u32], i: usize) requires i < y.len() { let mut a = [i, i]; a[0] = 1000; y[a[0]] = 1; }"####),
    ("t2/k26", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(y: &mut [u32], i: usize) requires i < y.len() { let mut a = [i, i]; let k2 = i % 2; a[k2] = 1000; y[a[0]] = 1; }"####),
    ("t2/k27", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(y: &mut [u32], x: &[u32]) requires y.len() == 4 && x.len() == 4 { for i in 0..4 { y[x[i] as usize] = 1; } }"####),
    ("t2/k28", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(y: &mut [i32], a: i32) requires y.len() == 1 && a != -2147483648 { y[0] = -(a - 1); }"####),
    ("t2/k29", "accept", "", r####"kernel fn k(y: &mut [i32], a: i32) requires y.len() == 1 && a != -2147483648 { y[0] = -a; }"####),
    ("t2/k30", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(y: &mut [u32], i: usize) requires i < y.len() { let mut j = i; for _t in 0..3 { j = j * 2; } y[j] = 1; }"####),
    ("t2/k31", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(y: &mut [u32], i: usize) requires i < y.len() { let j = (i as u8) as usize; y[j + 300] = 1; }"####),
    ("t2/k32", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(y: &mut [u32], i: u64) requires i < y.len() as u64 { y[i as usize] = 1; y[(i as u32) as usize + 1] = 2; }"####),
    ("t2/k33", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(y: &mut [i32], a: i32, b: i32) requires y.len() == 1 && a >= 0 && b >= 0 { y[0] = a + b; }"####),
    ("t2/k34", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(y: &mut [u64], a: u64, b: u64) requires y.len() == 1 && a < 4294967296 && b <= 4294967296 { y[0] = a * b * 2; }"####),
    ("t2/k35", "accept", "", r####"kernel fn k(y: &mut [u64], a: u64, b: u64) requires y.len() == 1 && a < 4294967296 && b < 2147483648 { y[0] = a * b * 2; }"####),
    ("t2/k36", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(y: &mut [u32], i: usize) requires i < y.len() { let mut j = i; if i > 0 { j = i - 1; } else { j = y.len(); } y[j] = 1; }"####),
    ("t2/k36b", "E-KERNEL-OBLIGATION", "", r####"kernel fn k36(y: &mut [u32], i: usize) requires i < y.len() { let mut j = i; if i > 0 { j = i - 1; } else { j = y.len(); } y[j] = 1; }"####),
    ("t2/k36c", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(y: &mut [u32], i: usize) requires i < y.len() { let j = if i > 0 { i - 1 } else { y.len() }; y[j] = 1; }
kernel fn k2(y: &mut [u32], i: usize) requires i < y.len() { let mut j = i; if i == 0 { j = y.len(); } y[j] = 1; }
kernel fn k3(y: &mut [u32], i: usize) requires i < y.len() { let mut j = i; j = y.len(); y[j] = 1; }"####),
    ("t2/k36d", "E-KERNEL-OBLIGATION", "", r####"kernel fn a(y: &mut [u32], c: bool) requires y.len() > 0 { let j = if c { 0 } else { y.len() }; y[j] = 1; }
kernel fn b(y: &mut [u32], c: bool) requires y.len() > 0 { let j = if c { y.len() } else { 0 }; y[j] = 1; }
kernel fn d(y: &mut [u32], i: usize) requires i < y.len() { let j = if i > 0 { 0 } else { y.len() }; y[j] = 1; }
kernel fn e(y: &mut [u32], i: usize) requires i < y.len() { let j = if i > 0 { i - 1 } else { 99 }; y[j] = 1; }
kernel fn g(y: &mut [u32], i: usize) requires i < y.len() { let j = if i == 0 { y.len() } else { i }; y[j] = 1; }"####),
    ("t2/k37", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(y: &mut [u32], x: &mut [usize], i: usize) requires i < y.len() && x.len() == 1 { x[0] = i; x[0] = x[0] + 1; y[x[0]] = 1; }"####),
    ("t2/k38", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(y: &mut [u32]) requires y.len() == 4 { for i in 0..5 { y[i] = 1; } }"####),
    ("t2/k39", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(y: &mut [u32], n: usize) requires y.len() == 4 && n <= 5 { for i in 0..n { y[i] = 1; } }"####),
    ("t2/k40", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(y: &mut [u32], i: usize) requires i <= y.len() { y[i] = 1; }"####),
    ("t2/leak", "E-KERNEL-OBLIGATION", "", r####"kernel fn m1(y: &mut [u32], i: usize) requires i < y.len() { if i > 0 { y[i] = 1; } else { y[1000] = 1; } }
fn t() -> u32 { let mut y = [0u32; 4]; m1(&mut y, 0); y[0] }"####),
    ("t2/neg", "E-KERNEL-OBLIGATION", "", r####"kernel fn n1(y: &mut [u32], i: usize) requires y.len() == 4 { if i > 0 { } else { y[1000] = 1; } }
kernel fn n2(y: &mut [u32], i: usize) requires y.len() == 4 { if i > 3 { } else { y[1000] = 1; } }
kernel fn n3(y: &mut [u32], i: u32) requires y.len() == 4 { if i > 3 { } else { y[1000] = 1; } }
kernel fn n4(y: &mut [u32], i: i32) requires y.len() == 4 { if i > 3 { } else { y[1000] = 1; } }
kernel fn n5(y: &mut [u32], i: usize) requires y.len() == 4 { if i >= 1 { } else { y[1000] = 1; } }
kernel fn n6(y: &mut [u32], i: usize) requires y.len() == 4 { if !(i > 0) { y[1000] = 1; } }
kernel fn n7(y: &mut [u32], i: usize) requires y.len() == 4 { if i < 5 { } else { y[1000] = 1; } }
kernel fn n8(y: &mut [u32], i: usize) requires y.len() == 4 { if 0 < i { } else { y[1000] = 1; } }
fn t1() -> u32 { let mut y = [0u32; 4]; n1(&mut y, 0); 0 }"####),
    ("t2/neg2", "E-KERNEL-OBLIGATION", "", r####"kernel fn m1(y: &mut [u32], i: usize) requires i < y.len() { if i > 0 { } else { y[1000] = 1; } }
kernel fn m2(y: &mut [u32], i: usize) requires i < y.len() { let j = if i > 0 { 0 } else { 1000 }; y[j] = 1; }
kernel fn m3(y: &mut [u32], i: usize) requires y.len() == 4 { let j = if i > 0 { 0 } else { 1000 }; y[j] = 1; }
kernel fn m4(y: &mut [u32], c: bool) requires y.len() == 4 { let j = if c { 0 } else { 1000 }; y[j] = 1; }
kernel fn m5(y: &mut [u32], i: usize) requires y.len() == 4 { let j = if i > 0 { 0usize } else { 1000usize }; y[j] = 1; }
kernel fn m6(y: &mut [u32], i: usize) requires y.len() == 4 { let mut j = 0usize; if i > 0 { j = 0; } else { j = 1000; } y[j] = 1; }"####),
    ("p/bud0", "E-KERNEL-OBLIGATION", "", r####"kernel fn f(a: &[u32], i: usize) -> u32 {
    let mut s = 0u32;
    for x in 0..4 {
        for y in 0..4 {
            s = s ^ ((x + y) as u32);
        }
    }
    s ^ a[i]
}"####),
    ("p/bud1", "E-KERNEL-OBLIGATION", "", r####"kernel fn f(a: &[u32], i: usize) -> u32 {
    let mut s = 0u32;
    for x in 0..64 {
        for y in 0..64 {
            s = s ^ ((x + y) as u32);
        }
    }
    s ^ a[i]
}
fn main1() -> u32 { let v = vec![1u32]; f(&v, 5) }"####),
];

#[test]
fn kernel_cases() {
    let bad = common::run_cases(KERNEL_CASES);
    assert!(bad.is_empty(), "{} of {} cases differ:\n{}", bad.len(), KERNEL_CASES.len(), bad.join("\n"));
}
