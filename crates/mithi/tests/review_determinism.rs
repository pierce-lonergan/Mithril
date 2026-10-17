//! Diagnostics must not depend on hash seeds (review 2026-10-16: with eight live shared borrows,
//! which holder an E-BORROW-CONFLICT message named varied between runs, 8 distinct outputs in 12).
//! Every map instance gets its own random seed, so repeating the check in one process exposes
//! iteration-order dependence.

mod common;

const SRC: &str = "fn g() -> usize {
    let mut v = vec![1u32];
    let a = &v; let b = &v; let c = &v; let d = &v; let e = &v; let f = &v; let h = &v; let k = &v;
    v.push(2);
    a.len() + b.len() + c.len() + d.len() + e.len() + f.len() + h.len() + k.len()
}
struct S { a: u32 }
fn m(x: &mut [u32], s: &mut S) {
    let p = &mut s.a;
    let q = &x[0];
    x[1] = *q;
    *p = 1;
    par for i in 0..x.len() { x[i] = x[0]; }
}
";

fn render() -> String {
    let c = common::checked(SRC, "");
    c.diags.iter().map(|d| mithi::diag::render_json(c.sm(), d)).collect::<Vec<_>>().join("\n")
}

#[test]
fn diagnostics_are_identical_across_runs() {
    let first = render();
    assert!(first.contains("E-BORROW-CONFLICT"), "{first}");
    for _ in 0..20 {
        assert_eq!(render(), first);
    }
}
