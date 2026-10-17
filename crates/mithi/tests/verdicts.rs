//! mithi against the core-calculus note's hand verdicts (docs/m0/core-calculus/verdicts.json),
//! by the agreement rule of note section 0.3 and derivations section V:
//!
//! - every canonical and derived item, whatever its scope: the snippet is extracted from the named
//!   file and lines, its SHA-256 is checked against the recorded hash (a mismatch is a stale item,
//!   not a disagreement), the prelude is concatenated, and mithi's verdict must equal the expected
//!   one (`verdict` for X1-scope items, `x1_expected` for the others); for a reject, the primary
//!   code must match;
//! - every negative item with gate_item true (N-01 to N-06): the commented-out example inside its
//!   parent snippet, uncommented (N-05: the parent with `store.release(lease);` deleted).
//!
//! The supplementary negative items (every negative item with gate_item false: N-07 to N-69 at
//! this commit) are prose in verdicts.json, not snippets; they are checked in
//! `supplementary_items` from constructions written here, each annotated with what was completed
//! (a wrapper function, a `use`, a fixture), against the verdict verdicts.json records. They are
//! not gate inputs (note Q11). Secondary facts (row, may_trap) are compared in `secondary_facts`;
//! a difference fails the test.
//!
//! Harness conventions (mithi's, documented in crates/mithi/README.md):
//! - "prelude" = mithi's std + crates/mithi/prelude/canonical.mith (derivations section P) + the
//!   canonical snippets other snippets name (D-C1 BlockQ4, D-C2 q4_row_dot/q4_matvec, D-C3
//!   q4_matvec_avx512), taken from the documents at their recorded lines; a snippet that defines an
//!   item with the same path replaces the prelude's;
//! - snippets that section P says live in `mod store` are checked in module `store`;
//! - the manifest grants declare_deterministic = ["store"] (01 section 11);
//! - documentation shorthand `…` is accepted as an elided body; D-C7's loose statements are the
//!   body of the prelude's `snippet_c7`.

use mithi::check::{check, Config};
use mithi::diag::FileRole;
use mithi::json::{self, Json};
use mithi::lower::{SourceInput, CANONICAL_PRELUDE};
use mithi::sha256::sha256_hex;
use std::path::PathBuf;

fn repo() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join("..")
}

fn verdicts() -> Json {
    let t = std::fs::read_to_string(repo().join("docs/m0/core-calculus/verdicts.json")).expect("verdicts.json");
    json::parse(&t).expect("valid JSON")
}

/// The body of a fenced block: lines start..=end (1-based), joined with LF, plus a final LF.
fn extract(file: &str, start: u64, end: u64) -> String {
    let t = std::fs::read_to_string(repo().join(file)).unwrap_or_else(|_| panic!("read {file}"));
    let lines: Vec<&str> = t.split('\n').map(|l| l.strip_suffix('\r').unwrap_or(l)).collect();
    let mut s = lines[(start - 1) as usize..end as usize].join("\n");
    s.push('\n');
    s
}

fn item<'a>(v: &'a Json, id: &str) -> &'a Json {
    v.get("items").unwrap().as_arr().iter().find(|i| i.str_of("id") == Some(id)).unwrap()
}

fn snippet_of(v: &Json, id: &str) -> String {
    let it = item(v, id);
    let o = &it.get("snippet").unwrap().get("occurrences").unwrap().as_arr()[0];
    extract(o.str_of("file").unwrap(), o.get("start_line").unwrap().as_u64().unwrap(), o.get("end_line").unwrap().as_u64().unwrap())
}

const STORE_ITEMS: &[&str] = &["D-C5", "D-D05", "D-D06", "D-D14", "D-D15", "D-D22"];

fn config(v: &Json, user: &str, module: &str) -> Config {
    let mut cfg = Config::default();
    cfg.inputs.push(SourceInput { name: "<canonical prelude>".into(), text: CANONICAL_PRELUDE.into(), role: FileRole::Prelude, module: String::new() });
    for ctx in ["D-C1", "D-C2", "D-C3"] {
        cfg.inputs.push(SourceInput { name: format!("<context {ctx}>"), text: snippet_of(v, ctx), role: FileRole::Prelude, module: String::new() });
    }
    cfg.inputs.push(SourceInput { name: "<snippet>".into(), text: user.into(), role: FileRole::User, module: module.into() });
    cfg.doc_snippets = true;
    cfg.loose_host = Some("snippet_c7".into());
    cfg.declare_deterministic = vec!["store".into()];
    cfg
}

/// (verdict, primary code)
fn run(cfg: &Config) -> (String, Option<String>, Vec<String>) {
    let c = check(cfg);
    let errs = c.errors();
    let all: Vec<String> = errs.iter().map(|d| format!("{} {}", d.code, d.msg)).collect();
    match errs.first() {
        None => ("accept".into(), None, all),
        Some(d) => ("reject".into(), Some(d.code.clone()), all),
    }
}

#[test]
fn prelude_alone_is_accepted() {
    let v = verdicts();
    let (verdict, _, all) = run(&config(&v, "", ""));
    assert_eq!(verdict, "accept", "the prelude must check on its own: {all:#?}");
}

#[test]
fn snippet_hashes_match_the_documents() {
    let v = verdicts();
    let mut stale = vec![];
    for it in v.get("items").unwrap().as_arr() {
        let sn = it.get("snippet").unwrap();
        let want = sn.str_of("sha256").unwrap();
        for o in sn.get("occurrences").unwrap().as_arr() {
            let body = extract(o.str_of("file").unwrap(), o.get("start_line").unwrap().as_u64().unwrap(), o.get("end_line").unwrap().as_u64().unwrap());
            if sha256_hex(body.as_bytes()) != want {
                stale.push(format!("{} {}:{}", it.str_of("id").unwrap(), o.str_of("file").unwrap(), o.get("start_line").unwrap().as_u64().unwrap()));
            }
        }
    }
    assert!(stale.is_empty(), "stale snippets (hash mismatch): {stale:?}");
}

#[test]
fn canonical_and_derived_items_agree() {
    let v = verdicts();
    let mut rows = vec![];
    let mut disagreements = vec![];
    for it in v.get("items").unwrap().as_arr() {
        let id = it.str_of("id").unwrap();
        let scope = it.str_of("scope").unwrap_or("");
        let (exp_verdict, exp_code) = if scope == "x1" || scope == "x1-front-end" {
            (it.str_of("verdict").unwrap().to_string(), it.str_of("code").map(|s| s.to_string()))
        } else {
            let x = it.get("x1_expected").unwrap();
            (x.str_of("verdict").unwrap().to_string(), x.str_of("code").map(|s| s.to_string()))
        };
        let module = if STORE_ITEMS.contains(&id) { "store" } else { "" };
        let (got, code, all) = run(&config(&v, &snippet_of(&v, id), module));
        let agree = got == exp_verdict && (got == "accept" || code == exp_code);
        rows.push(format!("{id:6} {scope:13} expected {exp_verdict:6} {:28} got {got:6} {:28} {}", exp_code.clone().unwrap_or_default(), code.clone().unwrap_or_default(), if agree { "agree" } else { "DISAGREE" }));
        if !agree {
            disagreements.push(format!("{id}: expected {exp_verdict} {exp_code:?}, got {got} {code:?}: {all:#?}"));
        }
    }
    println!("{}", rows.join("\n"));
    println!("agreement: {}/{} items", rows.len() - disagreements.len(), rows.len());
    assert!(disagreements.is_empty(), "{}", disagreements.join("\n"));
}

fn uncomment(text: &str, pred: impl Fn(&str) -> bool) -> String {
    text.split('\n')
        .map(|l| {
            if pred(l) {
                let t = l.trim_start();
                let ind = &l[..l.len() - t.len()];
                let rest = t.strip_prefix("// ").or_else(|| t.strip_prefix("//")).unwrap_or(t);
                format!("{ind}{rest}")
            } else {
                l.to_string()
            }
        })
        .collect::<Vec<_>>()
        .join("\n")
}

fn gate_negative(v: &Json, id: &str) -> (String, &'static str) {
    match id {
        "N-01" => (uncomment(&snippet_of(v, "D-D01"), |l| l.starts_with("// fn first_dyn")), ""),
        "N-02" => (uncomment(&snippet_of(v, "D-D02"), |l| l.starts_with("// struct RowCache")), ""),
        "N-03" => (uncomment(&snippet_of(v, "D-D02"), |l| l.starts_with("// fn pick")), ""),
        "N-04" => {
            let s = snippet_of(v, "D-D04");
            let lines: Vec<String> = s.split('\n').map(|x| x.to_string()).collect();
            let at = lines.iter().position(|l| l.starts_with("// fn live")).unwrap();
            let set: Vec<String> = lines[at..at + 3].to_vec();
            (uncomment(&s, move |l| set.iter().any(|x| x == l)), "")
        }
        "N-05" => (snippet_of(v, "D-D05").split('\n').filter(|l| !l.contains("store.release(lease);")).collect::<Vec<_>>().join("\n"), "store"),
        "N-06" => (uncomment(&snippet_of(v, "D-D06"), |l| l.starts_with("// fn heat_view")), "store"),
        _ => unreachable!(),
    }
}

#[test]
fn gate_negative_items_agree() {
    let v = verdicts();
    let mut disagreements = vec![];
    for n in v.get("negative_items").unwrap().as_arr() {
        if n.get("gate_item").and_then(|g| g.as_bool()) != Some(true) {
            continue;
        }
        let id = n.str_of("id").unwrap();
        let (text, module) = gate_negative(&v, id);
        let (got, code, all) = run(&config(&v, &text, module));
        let exp = n.str_of("code").unwrap();
        let agree = got == "reject" && code.as_deref() == Some(exp);
        println!("{id} expected reject {exp:22} got {got} {:22} {}", code.clone().unwrap_or_default(), if agree { "agree" } else { "DISAGREE" });
        if !agree {
            disagreements.push(format!("{id}: expected {exp}, got {got} {code:?}: {all:#?}"));
        }
    }
    assert!(disagreements.is_empty(), "{}", disagreements.join("\n"));
}

/// Constructions of the supplementary items (verdicts.json gives them as prose). Each completes
/// the prose minimally: a host function where the text is statements, `use std::time::Instant;`
/// for N-09, `struct E;` for N-15 and N-54, `struct W` / `struct S` where N-47 and N-58 use them
/// undeclared, full names where the prose abbreviates (`bpr` in N-23), callers where the text says
/// "called as" (N-46, N-63), and a fixture where the text says "with a fixture whose subject is
/// the block". N-40..N-69 were first constructed by a reviewer (same family, independent context)
/// and checked against the text by mithi's reviser. The expected verdict is read from
/// verdicts.json, not copied here; an item with no construction fails the test unless
/// `NOT_CONSTRUCTED` says why (review 2026-10-16: a hand list stopped at N-39 while verdicts.json
/// went on to N-69).
struct Supp {
    id: &'static str,
    text: &'static str,
    module: &'static str,
    fixture: Option<(&'static str, &'static str)>,
}

const SUPP: &[Supp] = &[
    Supp { id: "N-07", module: "", fixture: None, text: "kernel fn q4_matvec(w: &Matrix<BlockQ4>, a: &[ActQ8], y: &mut [f32])\n    requires y.len() == w.rows()\n{\n    par for r in 0..w.rows() {\n        y[r] = q4_row_dot(w.row(r), a);\n    }\n}\n" },
    Supp { id: "N-08", module: "", fixture: None, text: "let bw: Quantity<GBps, Simulated> = profile.dram_read_all_core;\n" },
    Supp { id: "N-09", module: "", fixture: None, text: "use std::time::Instant;\npolicy fn pick_victim(slots: &[SlotView], now: Tick) -> Hint<SlotId> {\n    let mut best = Hint::none();\n    let mut best_age: u64 = 0;\n    let t = Instant::now();\n    for s in slots {\n        if s.pinned || s.refs > 0 { continue; }\n        let age = now.0 - s.last_use.0;\n        if age > best_age { best_age = age; best = Hint::some(s.id); }\n    }\n    best\n}\n" },
    Supp { id: "N-10", module: "", fixture: None, text: "kernel fn q4_row_sum(xs: &[f32]) -> f32 {\n    canon::nan(xs.iter().sum::<f32>())\n}\n" },
    Supp { id: "N-11", module: "", fixture: None, text: "#[grade(exact, cross_device)] fn count(st: &Mutex<u32>) -> u32 uses { nondet } { let n = st.with_lock(|s| *s); let mut c = 0u32; for _i in 0..n { c = c + 1; } c }\n" },
    Supp { id: "N-12", module: "store", fixture: Some(("E", "store::leak@det0")), text: "#[grade(exact, cross_device)] fn leak(st: &Mutex<u32>) -> u32 uses { nondet } { let v = st.with_lock(|s| *s); deterministic(by: E) { v } }\n" },
    Supp { id: "N-13", module: "", fixture: None, text: "fn apply<F: Fn() -> u64>(f: F) -> u64 { f() }\n#[grade(exact, cross_device)] fn stamp(c: &Clock) -> u64 uses { time, nondet } { apply(|| c.now_ns()) }\n" },
    Supp { id: "N-14", module: "", fixture: None, text: "kernel fn k(x: &[f32], y: &mut [f32]) requires x.len() == y.len() { for i in 0..y.len() { y[i] = canon::nan(x[i]); if x[i] > 0.0 { break; } } }\n" },
    Supp { id: "N-15", module: "", fixture: None, text: "struct E;\nfn fill(y: &mut [u32], x: &[u32]) -> Result<(), E> { par for i in 0..y.len() { if x[i] == 0 { return Err(E) } y[i] = x[i]; } Ok(()) }\n#[grade(exact, cross_device)] fn g(x: &[u32; 8]) -> u32 { let mut y = [0u32; 8]; let _ = fill(&mut y, x); y[7] }\n" },
    Supp { id: "N-16", module: "", fixture: None, text: "#[grade(exact, cross_device)] fn f(v: &mut [u32], m: &Mutex<u32>) uses { nondet } { let i = m.with_lock(|s| *s) as usize % v.len(); let r = &mut v[i]; *r = 1; }\n" },
    Supp { id: "N-17", module: "store", fixture: None, text: "fn helper<F: Fn(usize)>(n: usize, f: &F) { par for i in 0..n { f(i); } }\nfn k(i: usize) -> ExpertKey { ExpertKey(i as u32) }\nfn caller(st: &Mutex<StoreState>) uses { nondet } { helper(4, &|i| st.with_lock(|s| s.touch(k(i)))); }\n" },
    Supp { id: "N-18", module: "", fixture: None, text: "fn apply<F: Fn(&[f32]) -> &[f32]>(f: F, t: &[f32]) -> &[f32] { f(t) }\nfn caller() -> f32 { let big = [1.0f32; 4]; let t = [2.0f32; 2]; let r = apply(|_x| &big[..], &t); r[0] }\n" },
    Supp { id: "N-19 (with the call)", module: "store", fixture: None, text: "fn n19(store: &Store, id: ExpertId) -> Result<(), IoError> uses { io, spawn } { let l = store.lease(id)?; let c = move || l.bytes().len(); let _n = c(); Ok(()) }\n" },
    Supp { id: "N-19 (without)", module: "store", fixture: None, text: "fn n19(store: &Store, id: ExpertId) -> Result<(), IoError> uses { io, spawn } { let l = store.lease(id)?; let c = move || l.bytes().len(); Ok(()) }\n" },
    Supp { id: "N-21", module: "", fixture: None, text: "impl<B> Matrix<B> { fn f(m: &mut Matrix<BlockQ4>, a: &[ActQ8], y: &mut [f32]) { m.rows = m.rows + 1; q4_matvec(&*m, a, y); } }\n" },
    Supp { id: "N-22", module: "", fixture: None, text: "kernel fn k(y: &mut [u32], j0: usize) requires j0 < y.len() { let mut j = j0; if j < y.len() { j = j + 1; y[j] = 0; } }\n" },
    Supp { id: "N-23", module: "", fixture: None, text: "impl std::ops::IndexMut<usize> for Matrix<f32> { type Output = [f32]; fn index_mut(&mut self, t: usize) -> &mut [f32] ensures footprint(result) == self.blocks[t * self.blocks_per_row..(t + 1) * self.blocks_per_row] { &mut self.blocks[0..self.blocks_per_row] } }\n" },
    Supp { id: "N-24", module: "", fixture: None, text: "fn set(o: &mut Option<&u32>, d: &u32) { *o = Some(d); }\n" },
    Supp { id: "N-25", module: "", fixture: None, text: "fn n25() -> i32 { let a = 1; let mut outer = &a; { let y = 5; let mut inner = &y; std::mem::swap(&mut outer, &mut inner); } *outer }\n" },
    Supp { id: "N-26", module: "", fixture: None, text: "fn n26() -> u32 { let mut v: Vec<&u32> = Vec::new(); { let d = 1; v.push(&d); } *v[0] }\n" },
    Supp { id: "N-27", module: "", fixture: None, text: "fn n27() -> i32 { let mut x = vec![1]; let r = { let c = || &x[0]; c() }; x.push(2); *r }\n" },
    Supp { id: "N-28", module: "", fixture: None, text: "impl<B> Matrix<B> { fn shrink(m: &mut Matrix<BlockQ4>) { m.blocks.truncate(0); } }\n" },
    Supp { id: "N-29", module: "", fixture: None, text: "#[grade(exact, cross_device)] fn n(st: &Mutex<u32>) -> u32 uses { nondet } { st.with_lock(|s| *s) }\n" },
    Supp { id: "N-30", module: "", fixture: None, text: "#[grade(exact, cross_device)] fn first_is_nan(x: f32) -> bool { let mut xs = [x - x, 1.0f32]; xs.sort_by(|p, q| p.total_cmp(q)); xs[0].is_nan() }\n" },
    Supp { id: "N-31", module: "", fixture: None, text: "#[grade(exact, cross_device)] fn g(m: &Mutex<bool>, out: &mut [u32]) uses { nondet } requires out.len() >= 1 { let mut c = 0u32; let mut it = (0..1).map(|_| { c += 1; 0 }); if m.with_lock(|s| *s) { it.next(); } drop(it); out[0] = c; }\n" },
    Supp { id: "N-32", module: "store", fixture: Some(("E", "store::n32@det0")), text: "fn n32(x: &[u32], clock: &Clock) uses { time } { let f = deterministic(by: E) { || (x.len(), clock.now_ns()) }; }\n" },
    Supp { id: "N-33", module: "store", fixture: None, text: "impl Store { fn racy(&self) -> u32 uses { nondet } { deterministic(by: golden::scheduling_independence) { self.state.with_lock(|s| s.counter) } } }\n" },
    Supp { id: "N-34", module: "store", fixture: Some(("E", "store::p@det0")), text: "fn p(m: &Mutex<u32>, n: usize) -> Option<usize> uses { nondet } { par for i in 0..n { let k = deterministic(by: E) { m.with_lock(|c| { *c += 1; *c }) }; if k == 3 { return Some(i); } } None }\n" },
    Supp { id: "N-35", module: "", fixture: None, text: "schedule bad for q4_row_dot on x86_64(avx512f) { vectorize g; }\n" },
    Supp { id: "N-36", module: "", fixture: None, text: "kernel fn s(x: &[f32]) -> f32 { canon::nan(x.iter().fold(0.0, |a, b| a + b)) }\n" },
    Supp { id: "N-37", module: "", fixture: None, text: "fn addr_len(v: &[u32]) -> usize { let s = format!(\"{:p}\", &v[0]); s.len() }\n" },
    Supp { id: "N-39", module: "", fixture: None, text: "trait Key { fn key(&self) -> u32; } impl Key for f32 { fn key(&self) -> u32 { (*self + 0.0).to_bits() } }\n" },
    Supp { id: "N-40", module: "", fixture: None, text: "#[grade(exact, cross_device)] fn leak(m: &Mutex<bool>) -> bool uses { nondet } { let h = m.with_lock(|s| *s); let mut c = false; let mut f = || { let o = c; c = true; o }; if h { f(); } f() }\n" },
    Supp { id: "N-41", module: "", fixture: None, text: "#[grade(exact, cross_device)] fn leak(m: &Mutex<bool>) -> bool uses { nondet } { let h = m.with_lock(|s| *s); let mut n = false; let mut f = move || { let o = n; n = true; o }; if h { f(); } f() }\n" },
    Supp { id: "N-42", module: "", fixture: None, text: "fn twice<F: FnMut(u32) -> u32>(mut f: F, h: u32) -> u32 { f(h); f(0) }\n#[grade(exact, cross_device)] fn g(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|s| *s); let mut c = 0u32; twice(|x: u32| -> u32 { let old = c; c = x; old }, h) }\n" },
    Supp { id: "N-43", module: "", fixture: None, text: "fn f() -> u32 { let mut slot: Option<&u32> = None; { let mut put = |d: &u32| { slot = Some(d); }; let x = 5u32; put(&x); } *slot.unwrap() }\n" },
    Supp { id: "N-44", module: "", fixture: None, text: "fn bad2() -> u32 { let a = 1u32; let mut out: &u32 = &a; { let y = 5u32; let mut c = || { out = &y; }; c(); } *out }\n" },
    Supp { id: "N-45", module: "", fixture: None, text: "fn set(o: Option<&mut u32>, h: bool) { if let Some(r) = o { if h { *r = 1; } } }\n#[grade(exact, cross_device)] fn g(m: &Mutex<bool>) -> u32 uses { nondet } { let h = m.with_lock(|s| *s); let mut y = 0u32; set(Some(&mut y), h); y }\n" },
    Supp { id: "N-46", module: "", fixture: None, text: "fn put(o: Option<&mut Option<&u32>>, d: &u32) { if let Some(r) = o { *r = Some(d); } }\nfn g() -> u32 { let mut slot = None; { let d = 5u32; put(Some(&mut slot), &d); } *slot.unwrap() }\n" },
    Supp { id: "N-47", module: "", fixture: None, text: "struct W { blocks: Vec<f32> }\nimpl W { fn window(&mut self, t: usize) -> &mut [f32] requires t + 4 <= self.blocks.len() ensures footprint(result) == self.blocks[t..t+4] { &mut self.blocks[t..t+4] } }\nfn race(y: &mut W) { par for i in 0..4 { y.window(3 - i)[i] = i as f32; } }\n" },
    Supp { id: "N-48", module: "", fixture: None, text: "#[grade(exact, cross_device)] fn k(a: &mut [f32], b: &mut [f32], x: &[f32], h: bool) { b[0] = x[0] - x[0]; let y = if h { &mut *a } else { &mut *b }; for i in 0..y.len() { y[i] = canon::nan(x[i]); } }\n" },
    Supp { id: "N-49", module: "", fixture: None, text: "fn set(m: &Mutex<u32>, y: &mut u32) uses { nondet } { loop { *y = m.with_lock(|s| *s); return; } }\n#[grade(exact, cross_device)] fn g(m: &Mutex<u32>) -> u32 uses { nondet } { let mut y = 0u32; set(m, &mut y); y }\n" },
    Supp { id: "N-50", module: "", fixture: None, text: "fn f() -> u32 { loop { return 1; } }\n" },
    Supp { id: "N-51", module: "store", fixture: None, text: "fn f(store: &Store, id: ExpertId, h: bool) -> Result<(), IoError> uses { io, spawn } { loop { let l = store.lease(id)?; if h { break; } store.release(l); } Ok(()) }\n" },
    Supp { id: "N-52", module: "", fixture: None, text: "#[grade(exact, cross_device)] fn f(m: &Mutex<bool>) -> u32 uses { nondet } { let h = m.with_lock(|s| *s); let mut y = 0u32; { let r = &mut y; let mut g = || { *r = 1; }; if h { g(); } } y }\n" },
    Supp { id: "N-53", module: "", fixture: None, text: "#[grade(exact, cross_device)] fn f(m: &Mutex<bool>) -> u32 uses { nondet } { let h = m.with_lock(|s| *s); let mut y = 0u32; { let mut g = |b: bool| { if b { y = 1; return; } }; g(h); } y }\n" },
    Supp { id: "N-54", module: "", fixture: None, text: "struct E;\n#[grade(exact, cross_device)] fn g(x: &[u32; 8]) -> u32 { let mut y = [0u32; 8]; let mut run = || -> Result<(), E> { par for i in 0..8 { if x[i] == 0 { return Err(E) } y[i] = x[i]; } Ok(()) }; let _ = run(); y[7] }\n" },
    Supp { id: "N-55", module: "", fixture: None, text: "#[grade(exact, cross_device)] fn leak(m: &Mutex<bool>) -> u32 uses { nondet } { let h = m.with_lock(|s| *s); let o: Option<u32> = if h { Some(1) } else { None }; let mut c = 0u32; let _ = o.map(|v| { c = 1; v }); c }\n" },
    Supp { id: "N-56", module: "store", fixture: Some(("E", "store::bump@det0")), text: "fn bump(m: &Mutex<u32>, i: u32) -> u32 { deterministic(by: E) { m.with_lock(|c| { *c = c.wrapping_mul(2).wrapping_add(i); 0 }) } }\nfn p(m: &Mutex<u32>, n: usize) { par for i in 0..n { let _ = bump(m, i as u32); } }\n" },
    Supp { id: "N-57", module: "store", fixture: Some(("E", "store::leak@det0")), text: "#[grade(exact, cross_device)] fn leak(clock: &Clock) -> u64 uses { time, nondet } { let m = Mutex::new(0u64); m.with_lock(|v| *v = clock.now_ns()); deterministic(by: E) { m.with_lock(|v| *v) } }\n" },
    Supp { id: "N-58", module: "", fixture: None, text: "struct S { buf: [f32; 4] }\nfn poke(s: &mut S) { s.buf[0] = s.buf[0] - s.buf[0]; }\n#[grade(exact, cross_device)] fn k(x: &[f32; 4], s: &mut S) { for i in 0..4 { s.buf[i] = canon::nan(x[i]); poke(&mut *s); } }\n" },
    Supp { id: "N-59", module: "", fixture: None, text: "kernel fn k(x: &[f32], y: &mut [f32], m: usize) requires x.len() == y.len() { for i in 0..y.len() { for _k in 0..m { y[i] = canon::nan(x[i]); } } }\n" },
    Supp { id: "N-60", module: "", fixture: None, text: "#[grade(exact, cross_device)] fn k(x: &[f32], y: &mut [f32], c: bool) { for i in 0..y.len() { let mut w = || y[i] = canon::nan(x[i]); if c { w() } } }\n" },
    Supp { id: "N-61", module: "", fixture: None, text: "fn f(x: &[u32], n: usize) { 'outer: loop { par for i in 0..n { if x[i] == 0 { break 'outer; } } } }\n" },
    Supp { id: "N-62", module: "", fixture: None, text: "kernel fn outer(w: &Matrix<BlockQ4>, a: &[ActQ8], y: &mut [f32]) requires y.len() == w.rows() && a.len() == w.blocks_per_row() && y.len() >= 1 { y[0] = y[0] - y[0]; q4_matvec(w, a, &mut *y); }\n" },
    Supp { id: "N-63", module: "", fixture: None, text: "fn f<F: Fn()>(g: F, n: u32) { if n > 0 { f(|| g(), n - 1) } }\nfn h() { f(|| (), 3) }\n" },
    Supp { id: "N-64", module: "", fixture: None, text: "#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let mut y = 0u32; let r = &mut y; *r = m.with_lock(|s| *s); *r }\n" },
    Supp { id: "N-65", module: "", fixture: None, text: "#[grade(exact, cross_device)] fn g(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|s| *s); let mut y = 0u32; let f = |v: &mut u32| { *v = h; }; f(&mut y); y }\n" },
    Supp { id: "N-66", module: "", fixture: None, text: "fn bad() -> u32 { let a = 1u32; let mut out: &u32 = &a; { let y = 5u32; let r: &u32 = &y; let c = move || r; out = c(); } *out }\n" },
    Supp { id: "N-67", module: "store", fixture: None, text: "fn take_first(slots: &mut [Option<Lease>], want: &[bool]) -> Option<Lease> { par for i in 0..slots.len() { if want[i] { return slots[i].take(); } } None }\n" },
    Supp { id: "N-68", module: "", fixture: None, text: "fn t() -> u32 { let a = 1u32; let mut out = &a; { let y = 5u32; let t = (&y,); out = t.0; } *out }\n" },
    Supp { id: "N-69", module: "", fixture: None, text: "#[grade(exact, cross_device)] fn f(m: &Mutex<bool>) -> u32 uses { nondet } { let h = m.with_lock(|s| *s); loop { if h { break 1 } else { break 0 } } }\n" },
];

/// Supplementary items that are not constructed, and why.
const NOT_CONSTRUCTED: &[(&str, &str)] = &[("N-38", "a hint port's stack budget (E-TO-STACK): M4, outside X1")];

/// Constructions that disagree with the note, with the diagnosis of which side is wrong ("mithi
/// wrong" or "note wrong"); reported, not failing. Empty at this commit.
const DIAGNOSED: &[(&str, &str)] = &[];

#[test]
fn supplementary_items() {
    let v = verdicts();
    let mut disagreements = vec![];
    let mut unconstructed = vec![];
    let mut n = 0;
    for item in v.get("negative_items").unwrap().as_arr() {
        if item.get("gate_item").and_then(|g| g.as_bool()) == Some(true) {
            continue;
        }
        let id = item.str_of("id").unwrap();
        let expect = if item.str_of("verdict") == Some("accept") { "accept".to_string() } else { item.str_of("code").unwrap_or("?").to_string() };
        let mut runs: Vec<(String, String, Option<String>, Vec<String>)> = vec![];
        for s in SUPP.iter().filter(|s| s.id.split_whitespace().next() == Some(id)) {
            let mut cfg = config(&v, s.text, s.module);
            if let Some((name, subject)) = s.fixture {
                cfg.fixtures.push((name.into(), "deterministic".into(), subject.into(), "tested".into()));
            }
            let (got, code, all) = run(&cfg);
            runs.push((s.id.to_string(), got, code, all));
        }
        if id == "N-20" {
            // expert_step with drop(lease) in place of store.release(lease)
            let n20 = snippet_of(&v, "D-D05").replace("store.release(lease);", "drop(lease);");
            let (got, code, all) = run(&config(&v, &n20, "store"));
            runs.push(("N-20".into(), got, code, all));
        }
        if runs.is_empty() {
            if !NOT_CONSTRUCTED.iter().any(|(x, _)| *x == id) {
                unconstructed.push(id.to_string());
            }
            continue;
        }
        for (sid, got, code, all) in runs {
            n += 1;
            let agree = if expect == "accept" { got == "accept" } else { code.as_deref() == Some(expect.as_str()) };
            let diag = DIAGNOSED.iter().find(|(x, _)| *x == sid).map(|(_, d)| *d);
            println!("{sid:22} expected {expect:22} got {got} {:22} {}", code.clone().unwrap_or_default(), if agree { "agree" } else if diag.is_some() { "DISAGREE (diagnosed)" } else { "DISAGREE" });
            if !agree && diag.is_none() {
                disagreements.push(format!("{sid}: expected {expect}, got {got} {code:?}: {all:#?}"));
            }
        }
    }
    println!("supplementary agreement: {}/{n}; not constructed: {NOT_CONSTRUCTED:?}", n - disagreements.len());
    assert!(unconstructed.is_empty(), "supplementary items without a construction: {unconstructed:?}");
    assert!(disagreements.is_empty(), "{}", disagreements.join("\n"));
}

#[test]
fn secondary_facts() {
    // row and may_trap per function, where verdicts.json states them (reported; see README)
    let v = verdicts();
    let mut report = vec![];
    let mut mismatches = 0;
    for it in v.get("items").unwrap().as_arr() {
        let id = it.str_of("id").unwrap();
        let Some(Json::Obj(facts)) = it.get("facts") else { continue };
        let scope = it.str_of("scope").unwrap_or("");
        if !(scope == "x1" || scope == "x1-front-end") {
            continue;
        }
        let module = if STORE_ITEMS.contains(&id) { "store" } else { "" };
        let c = check(&config(&v, &snippet_of(&v, id), module));
        for (name, f) in facts {
            let Some(mt) = f.get("may_trap").and_then(|x| x.as_bool()) else { continue };
            let named = |d: &&mithi::program::FnDef| d.path == *name || d.path.ends_with(&format!("::{name}")) || d.name == *name;
            // the snippet's own definition first; a loose snippet (D-C7) is the body of a host
            // function the prelude declares (the loose-host convention), so fall back to that
            let fid = c.program.fns.iter().position(|d| named(&d) && d.role == FileRole::User).or_else(|| c.program.fns.iter().position(|d| named(&d) && d.body.is_some()));
            let Some(fid) = fid else {
                report.push(format!("{id} {name}: not found"));
                continue;
            };
            let ff = c.facts.fns.get(&(fid as u32)).cloned().unwrap_or_default();
            let want_row: Vec<String> = f.get("row").map(|r| r.as_arr().iter().filter_map(|x| x.as_str().map(|s| s.to_string())).collect()).unwrap_or_default();
            let got_row: Vec<String> = ff.row.iter().map(|l| l.text()).collect();
            let ok = ff.may_trap == mt && want_row == got_row;
            if !ok {
                mismatches += 1;
            }
            report.push(format!("{id:6} {name:22} may_trap {mt:5} / {:5}  row {want_row:?} / {got_row:?}  {}", ff.may_trap, if ok { "same" } else { "DIFFERS" }));
        }
    }
    println!("{}", report.join("\n"));
    println!("secondary facts differing: {mismatches}");
    assert_eq!(mismatches, 0, "secondary facts differ from verdicts.json:\n{}", report.join("\n"));
}
