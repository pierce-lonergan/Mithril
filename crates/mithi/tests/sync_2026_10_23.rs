//! Regression tests of the core-calculus note's round-3 sync with mithi (2026-10-23; note section
//! 0.8, F-114 to F-122). The supplementary items N-110 to N-127 themselves are checked by
//! `tests/verdicts.rs` against verdicts.json; these are the twins and values the items' text names
//! and the boundary cases of the rules that changed: (t5) and (t6) (F-118) and the order of codes
//! at one anchor (F-117). Expected verdicts are the note's rules; where a case is Rust-shaped, its
//! Rust form was compiled with the pinned rustc 1.99.1 [M, laptop, 2026-10-23; scratch probes
//! ccsync/rs s01 to s08]. The last section holds the cases of the review of the sync (note
//! section 0.9, F-123 to F-134) and the reviser's controls.

mod common;

/// (t5) and (t6) as pinned by F-118.
const POLICY: &[(&str, &str, &str, &str)] = &[
    // a range bounded by the length of a core-provided slice parameter (N-118's rule)
    ("t5-len", "accept", "--canonical-prelude", r####"policy fn p(slots: &[SlotView], now: Tick) -> Hint<usize> { let mut b = 0usize; for i in 0..slots.len() { if slots[i].refs == 0 { b = i; } } Hint::some(b) }"####),
    // a `const` item is a constant (rejected before the sync: only literals were read as constants)
    ("t5-const", "accept", "--canonical-prelude", r####"const N: usize = 4;
policy fn p(slots: &[SlotView], now: Tick) -> Hint<usize> { let mut b = 0usize; for i in 0..N { b = b + i; } Hint::some(b) }"####),
    ("t5-inclusive-len", "accept", "--canonical-prelude", r####"policy fn p(slots: &[SlotView], now: Tick) -> Hint<usize> { let mut b = 0usize; for i in 1..=slots.len() { b = i; } Hint::some(b) }"####),
    // a bound that is not a view length: the trip count is a view field's value, not a length
    ("t5-field", "E-TO-LOOP", "--canonical-prelude", r####"policy fn p(slots: &[SlotView], now: Tick) -> Hint<SlotId> { for _k in 0..now.0 { } Hint::none() }"####),
    // the bound held in a local is not read through (N-120)
    ("t5-local", "E-TO-LOOP", "--canonical-prelude", r####"policy fn p(slots: &[SlotView], now: Tick) -> Hint<usize> { let n = slots.len(); let mut b = 0usize; for i in 0..n { b = i; } Hint::some(b) }"####),
    // the length of a slice that is not a parameter (a sub-slice) is not a view length as written
    ("t5-subslice", "E-TO-LOOP", "--canonical-prelude", r####"policy fn p(slots: &[SlotView], now: Tick) -> Hint<usize> { let mut b = 0usize; for i in 0..slots[1..].len() { b = i; } Hint::some(b) }"####),
    ("t5-while", "E-TO-LOOP", "--canonical-prelude", r####"policy fn p(slots: &[SlotView], now: Tick) -> Hint<usize> { let mut i = 0usize; while i < slots.len() { i += 1; } Hint::some(i) }"####),
    // closures of either kind that stay inside the call (N-119)
    ("t6-move-local", "accept", "--canonical-prelude", r####"policy fn p(slots: &[SlotView], now: Tick) -> Hint<u64> { let f = move || now.0; Hint::some(f()) }"####),
    ("t6-capture-free", "accept", "--canonical-prelude", r####"policy fn p(slots: &[SlotView], now: Tick) -> Hint<usize> { Hint::some(slots.iter().filter(|s| s.refs == 0).count()) }"####),
    ("t6-move-filter", "accept", "--canonical-prelude", r####"policy fn p(slots: &[SlotView], now: Tick) -> Hint<usize> { Hint::some(slots.iter().filter(move |s| s.last_use.0 < now.0).count()) }"####),
    // a function value in the result leaves the call (N-121)
    ("t6-fn-result", "E-TO-AUTHORITY", "--canonical-prelude", r####"fn one() -> u32 { 1 }
policy fn p(slots: &[SlotView], now: Tick) -> Hint<fn() -> u32> { Hint::some(one) }"####),
    // a helper may return a closure inside the policy's extent; the helper's own body is still
    // checked by (t5) and (t7)
    ("t6-helper-loop", "E-TO-CALL", "--canonical-prelude", r####"fn h(n: usize) -> usize { let mut i = 0usize; while i < n { i += 1; } i }
policy fn p(slots: &[SlotView], now: Tick) -> Hint<usize> { let c = move || h(slots.len()); Hint::some(c()) }"####),
];

#[test]
fn policy_loops_and_closures() {
    let bad = common::run_cases(POLICY);
    assert!(bad.is_empty(), "{} of {} cases differ:\n{}", bad.len(), POLICY.len(), bad.join("\n"));
}

/// F-117: at one anchor, codes are ordered by spelling, so N-117's two codes at the parameter come
/// out E-TO-AUTHORITY, then E-TO-PARAM, whatever order the passes emit them in.
#[test]
fn ties_at_one_anchor_follow_the_code_spelling() {
    let c = common::checked("policy fn p(slots: &[SlotView], m: &Mutex<u32>) -> Hint<u32> { Hint::some(m.with_lock(|v| *v)) }", "--canonical-prelude");
    let codes: Vec<String> = c.errors().iter().map(|d| d.code.clone()).collect();
    assert_eq!(codes, vec!["E-TO-ROW", "E-TO-AUTHORITY", "E-TO-PARAM", "E-TO-CALL"], "{codes:?}");
}

/// F-114 for `T-CallClo`'s state line (N-128): a call through a reference chosen under h writes
/// the state of the closure the reference borrows, with the address grade. Before the sync mithi
/// wrote it into the reference and found no closure behind an `if`, so all three were accepted.
const CLOSURE_STATE: &[(&str, &str, &str, &str)] = &[
    ("state-overwrite", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn g(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut s = 0u32; let mut c1 = move |x: u32| -> u32 { let o = s; s = x; o }; let mut c2 = c1; { let r = if h > 1 { &mut c1 } else { &mut c2 }; r(9); } c1(0) }"####),
    ("state-increment", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn g(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut n = 0u32; let mut c1 = move || { n += 1; n }; let mut c2 = c1; { let r = if h > 1 { &mut c1 } else { &mut c2 }; r(); } c1() }"####),
    ("state-match", "E-GRADE", "", r####"#[grade(exact, cross_device)] fn g(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut n = 0u32; let mut c1 = move || { n += 1; n }; let mut c2 = c1; { let r = match h { 0 => &mut c1, _ => &mut c2 }; r(); } c1() }"####),
    // one target, no choice: the state update is the closure's own, at the call's pc
    ("state-one-target", "accept", "", r####"#[grade(exact, cross_device)] fn g(m: &Mutex<u32>) -> u32 uses { nondet } { let _h = m.with_lock(|v| *v); let mut n = 0u32; let mut c1 = move || { n += 1; n }; { let r = &mut c1; r(); } c1() }"####),
];

#[test]
fn closure_state_through_a_chosen_reference() {
    let bad = common::run_cases(CLOSURE_STATE);
    assert!(bad.is_empty(), "{} of {} cases differ:\n{}", bad.len(), CLOSURE_STATE.len(), bad.join("\n"));
    // Rust's values [M: rustc 1.99.1, probes s10 and s11 print `2 1` and `9 0`]
    let src = "fn g(h: u32) -> u32 { let mut s = 0u32; let mut c1 = move |x: u32| -> u32 { let o = s; s = x; o }; let mut c2 = c1; { let r = if h > 1 { &mut c1 } else { &mut c2 }; r(9); } c1(0) }
fn g3() -> u32 { g(3) }
fn g0() -> u32 { g(0) }
fn k(h: u32) -> u32 { let mut n = 0u32; let mut c1 = move || { n += 1; n }; let mut c2 = c1; { let r = if h > 1 { &mut c1 } else { &mut c2 }; r(); } c1() }
fn k3() -> u32 { k(3) }
fn k0() -> u32 { k(0) }";
    for (entry, want) in [("g3", "9"), ("g0", "0"), ("k3", "2"), ("k0", "1")] {
        assert_eq!(common::run_entry(src, "", entry).unwrap(), want, "{entry}");
    }
}

/// The twins and values N-76 and N-109 name in their text (verdicts.json).
#[test]
fn twins_and_values_of_the_third_round_items() {
    // N-109's accepted twin: the variant the `if let` does not match carries no Linear value
    let twin = "fn f(store: &Store, o: Option<Lease>) uses { io, spawn } { if let Some(l) = o { store.release(l) } }";
    let c = common::checked(twin, "--canonical-prelude --module store");
    assert_eq!(common::verdict(&c), "accept");
    // N-76: rustc accepts it and the write reaches v[0] [M: rustc 1.99.1 compiles the Rust form]
    let src = "fn g() -> u32 { let mut v = [0u32; 4]; let x = v.iter_mut().next().unwrap(); *x = 1; v[0] }";
    assert_eq!(common::run_entry(src, "", "g").unwrap(), "1");
}

// ---------------------------------------------------------------- review of the round-3 sync
// The review of 2026-10-23 (reviewer 7, Claude, same family, independent context; note section
// 0.9, F-123 to F-134) and the reviser's controls. Each expectation is the note's verdict as revised;
// where a case is Rust-shaped, rustc 1.99.1 gives the same accept or reject [M, laptop, 2026-10-23;
// scratch probes ccsync-diff/rs (the reviewer's) and ccsync/r2/rs t01 to t37, z01 to z08 (the
// reviser's), named per case].

/// F-123: closure-call loan transfers through `move`-captured `&mut` (rustc: t01 to t05, t23, t26 to t28).
const REVIEW_TRANSFER: &[(&str, &str, &str, &str)] = &[
    // t01
    ("B2-move-state", "E-LOCAL-MUT-STORE", "", r####"fn put(o: &mut Option<&u32>, d: &u32) { let mut c = move |x| { *o = Some(x); }; c(d); }"####),
    // t23
    ("B2c-move-dangle", "E-LOCAL-MUT-STORE", "", r####"fn put(o: &mut Option<&u32>, d: &u32) { let mut c = move |x| { *o = Some(x); }; c(d); }
fn g() -> u32 { let mut o: Option<&u32> = None; { let z = 5u32; put(&mut o, &z); } *o.unwrap() }"####),
    // t02
    ("B2d-move-push", "E-LOCAL-MUT-STORE", "", r####"fn put(o: &mut Vec<&u32>, d: &u32) uses { alloc(Global) } { let mut c = move |x| o.push(x); c(d); }"####),
    // t03, the non-move form
    ("B2b-uniq-capture", "E-LOCAL-MUT-STORE", "", r####"fn put(o: &mut Option<&u32>, d: &u32) { let mut c = |x| { *o = Some(x); }; c(d); }"####),
    // annotated, higher-ranked
    ("B2e-move-annot", "E-LOCAL-MUT-STORE", "", r####"fn put(o: &mut Option<&u32>, d: &u32) { let mut c = move |x: &u32| { *o = Some(x); }; c(d); }"####),
    // t05, returns 5
    ("X05-move-local-ref", "accept", "", r####"fn g() -> u32 { let z = 5u32; let mut o: Option<&u32> = None; { let r = &mut o; let mut c = move |x| { *r = Some(x); }; c(&z); } *o.unwrap() }"####),
    // t26, E0597
    ("X06-move-local-ref-dangle", "E-BORROW-OUTLIVE", "", r####"fn g() -> u32 { let mut o: Option<&u32> = None; { let z = 5u32; let r = &mut o; let mut c = move |x| { *r = Some(x); }; c(&z); } *o.unwrap() }"####),
    // t04: only o's own contents are stored
    ("X07-move-own-contents", "accept", "", r####"fn put(o: &mut Option<&u32>) { let mut c = move || { let t = *o; *o = t; }; c(); }"####),
];

/// F-125: anchors of E-LINEAR-DROP and E-REF-ESCAPE (rustc: t07 for D1).
const REVIEW_ANCHORS: &[(&str, &str, &str, &str)] = &[
    // t07: E0506 before E0515
    ("D1-escape-anchor", "E-BORROW-CONFLICT", "", r####"fn f(v: &[u32]) -> &u32 { let mut a = 1u32; let r = &a; a = 2; let l = [*r, 2]; &l[0] }"####),
    // one anchor, spelling order
    ("D2-tie-brace", "E-BORROW-OUTLIVE", "--canonical-prelude --module store", r####"fn f(store: &Store, id: ExpertId) -> Result<u32, IoError> uses { io, spawn } { let a = 0u32; let mut r = &a; { let l = store.lease(id)?; let z = 1u32; r = &z; } Ok(*r) }"####),
    // the lease is dropped at the closing brace
    ("D9-lineardrop-anchor", "E-BORROW-CONFLICT", "--canonical-prelude --module store", r####"fn f(store: &Store, id: ExpertId) -> Result<(), IoError> uses { io, spawn } { let l = store.lease(id)?; let mut a = 1u32; let r = &a; a = 2; let _u = *r; Ok(()) }"####),
    // the `return` form
    ("D10-escape-anchor-tail", "E-BORROW-CONFLICT", "", r####"fn f(v: &[u32]) -> &u32 { let mut a = 1u32; let r = &a; a = 2; let _u = *r; let l = [1u32, 2]; return &l[0]; }"####),
    ("G1-capture-unconsumed", "E-LINEAR-DROP", "--canonical-prelude --module store", r####"fn f(store: &Store, id: ExpertId) -> Result<(), IoError> uses { io, spawn } { let l = store.lease(id)?; let c = move || { let _r = &l; }; c(); Ok(()) }"####),
    // F-124; t06: E0382
    ("G4-called-twice", "E-MOVE-USED", "--canonical-prelude --module store", r####"fn f(store: &Store, id: ExpertId) -> Result<(), IoError> uses { io, spawn } { let l = store.lease(id)?; let c = move || store.release(l); c(); c(); Ok(()) }"####),
];

/// F-126: place captures (rustc: t10, z01 to z08).
const REVIEW_CAPTURES: &[(&str, &str, &str, &str)] = &[
    // t10
    ("R6-clo-disjoint", "accept", "", r####"struct S { x: u32, y: u32 }
fn g() -> u32 { let mut s = S { x: 1, y: 2 }; let mut c = || s.x += 1; let r = &s.y; c(); *r + s.x }"####),
    ("R6b-clo-whole-conflict", "E-BORROW-CONFLICT", "", r####"struct S { x: u32, y: u32 }
fn g() -> u32 { let mut s = S { x: 1, y: 2 }; let mut c = || s.x += 1; let r = &s.x; c(); *r }"####),
    // z01
    ("Z01-two-disjoint-mut", "accept", "", r####"struct S { x: u32, y: u32 }
fn g() -> u32 { let mut s = S { x: 1, y: 2 }; let mut a = || s.x += 1; let mut b = || s.y += 1; a(); b(); s.x + s.y }"####),
    // z02: E0502
    ("Z02-same-field-conflict", "E-BORROW-CONFLICT", "", r####"struct S { x: u32, y: u32 }
fn g() -> u32 { let mut s = S { x: 1, y: 2 }; let mut c = || s.x += 1; let r = &s.x; c(); *r }"####),
    // z03: E0502
    ("Z03-whole-and-field", "E-BORROW-CONFLICT", "", r####"struct S { x: u32, y: u32 }
fn g() -> u32 { let mut s = S { x: 1, y: 2 }; let mut c = || s.x += 1; let r = &s; c(); r.y }"####),
    // z04
    ("Z04-read-field-write-other", "accept", "", r####"struct S { x: u32, y: u32 }
fn g() -> u32 { let mut s = S { x: 1, y: 2 }; let c = || s.x + 1; s.y = 5; c() + s.y }"####),
    // z05: E0506
    ("Z05-read-field-write-same", "E-BORROW-CONFLICT", "", r####"struct S { x: u32, y: u32 }
fn g() -> u32 { let mut s = S { x: 1, y: 2 }; let c = || s.x + 1; s.x = 5; c() + s.y }"####),
    // z06
    ("Z06-nested-field", "accept", "", r####"struct T { a: S, b: u32 }
struct S { x: u32, y: u32 }
fn g() -> u32 { let mut t = T { a: S { x: 1, y: 2 }, b: 3 }; let mut c = || t.a.x += 1; let r = &t.a.y; c(); *r + t.b }"####),
    // z07: E0502
    ("Z07-index-truncates", "E-BORROW-CONFLICT", "", r####"struct V { v: [u32; 2], w: u32 }
fn g() -> u32 { let mut s = V { v: [1, 2], w: 3 }; let mut c = || s.v[0] += 1; let r = &s.v[1]; c(); *r }"####),
    // z08
    ("Z08-index-other-field", "accept", "", r####"struct V { v: [u32; 2], w: u32 }
fn g() -> u32 { let mut s = V { v: [1, 2], w: 3 }; let mut c = || s.v[0] += 1; let r = &s.w; c(); *r }"####),
];

/// F-124, F-127 to F-130: codes, classes and (t6) (rustc: t20, t21).
const REVIEW_CODES: &[(&str, &str, &str, &str)] = &[
    ("C1-kernel-clock", "E-FF-CLOCK", "", r####"kernel fn k(c: &Clock) -> u64 { c.now_ns() }"####),
    // F-127
    ("C2-helper-clock", "E-FF-CLOCK", "", r####"fn hc(c: &Clock) -> u64 uses { time } { c.now_ns() }
kernel fn k(c: &Clock) -> u64 uses { time } { hc(c) }"####),
    // F-127
    ("C3-generic-helper-clock", "E-FF-CLOCK", "", r####"fn hc(c: &Clock) -> u64 uses { time } { c.now_ns() }
#[grade(exact, cross_device)] fn ex(c: &Clock) -> u64 uses { time, nondet } { hc(c) }
kernel fn k(c: &Clock) -> u64 uses { time } { hc(c) }"####),
    // not reached from a kernel
    ("C4-helper-from-exact", "E-GRADE", "", r####"fn hc(c: &Clock) -> u64 uses { time } { c.now_ns() }
#[grade(exact, cross_device)] fn ex(c: &Clock) -> u64 uses { time, nondet } { hc(c) }"####),
    // F-128; t20: E0505
    ("R18-move-while-borrowed", "E-BORROW-CONFLICT", "", r####"fn g() -> usize uses { alloc(Global) } { let v: Vec<u32> = Vec::new(); let r = &v; let w = v; r.len() + w.len() }"####),
    // F-128; t21: E0507
    ("R19-move-behind-ref", "E-MOVE-BORROWED", "", r####"fn g(v: &Vec<u32>) -> Vec<u32> { *v }"####),
    // F-129: class 1
    ("D7-linear-copy-class", "E-LINEAR-COPY", "", r####"#[derive(Copy, Clone)] linear struct L { a: u32 }
fn g() { println!("x"); }"####),
    // F-130
    ("E5-fnptr-in-struct", "E-TO-AUTHORITY", "--canonical-prelude", r####"#[derive(Copy, Clone)] struct W { f: fn() -> u32 }
fn one() -> u32 { 1 }
policy fn p(slots: &[SlotView], now: Tick) -> Hint<W> { Hint::some(W { f: one }) }"####),
    ("E5b-option-fn", "E-TO-AUTHORITY", "--canonical-prelude", r####"fn one() -> u32 { 1 }
policy fn p(slots: &[SlotView], now: Tick) -> Hint<Option<fn() -> u32>> { Hint::some(Some(one)) }"####),
    ("E5c-tuple-fn", "E-TO-AUTHORITY", "--canonical-prelude", r####"fn one() -> u32 { 1 }
policy fn p(slots: &[SlotView], now: Tick) -> Hint<(u32, fn() -> u32)> { Hint::some((0, one)) }"####),
    // F-130: type arguments substituted
    ("P01-generic-struct-fn", "E-TO-AUTHORITY", "--canonical-prelude", r####"#[derive(Copy, Clone)] struct W2<T> { f: T }
fn one() -> u32 { 1 }
policy fn p(slots: &[SlotView], now: Tick) -> Hint<W2<fn() -> u32>> { Hint::some(W2 { f: one }) }"####),
    ("P02-struct-no-fn", "accept", "--canonical-prelude", r####"#[derive(Copy, Clone)] struct W3 { a: u32, b: usize }
policy fn p(slots: &[SlotView], now: Tick) -> Hint<W3> { Hint::some(W3 { a: 1, b: slots.len() }) }"####),
    // F-130: nested structs
    ("P03-nested-struct-fn", "E-TO-AUTHORITY", "--canonical-prelude", r####"#[derive(Copy, Clone)] struct In { f: fn() -> u32 }
#[derive(Copy, Clone)] struct Out { i: In, k: u32 }
fn one() -> u32 { 1 }
policy fn p(slots: &[SlotView], now: Tick) -> Hint<Out> { Hint::some(Out { i: In { f: one }, k: 0 }) }"####),
];

/// F-131: match-arm facts and shifted join bounds in T2 (kernels; no rustc analogue).
const REVIEW_PATHFACTS: &[(&str, &str, &str, &str)] = &[
    ("F2-match-pred", "accept", "", r####"kernel fn k(i: usize, y: &mut [u32]) requires i < y.len() { let j = match i { 0 => 0, _ => i - 1 }; y[j] = 1; }"####),
    ("F2b-if-form", "accept", "", r####"kernel fn k(i: usize, y: &mut [u32]) requires i < y.len() { let j = if i == 0 { 0 } else { i - 1 }; y[j] = 1; }"####),
    ("F2c-match-arm-cond", "accept", "", r####"kernel fn k(i: usize, y: &mut [u32]) requires i < y.len() { match i { 0 => {}, _ => { y[i - 1] = 1; } } }"####),
    ("F2d-match-bind-guard", "accept", "", r####"kernel fn k(i: usize, y: &mut [u32]) requires i < y.len() { match i { 0 => {}, n => { y[n - 1] = 1; } } }"####),
    ("Y01-match-norequires", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(i: usize, y: &mut [u32]) { match i { 0 => {}, _ => { y[i] = 1; } } }"####),
    // i may be 0
    ("Y02-match-other-lit", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(i: usize, y: &mut [u32]) requires i < y.len() { match i { 1 => {}, _ => { y[i - 1] = 1; } } }"####),
    // a guarded arm contributes no negation
    ("Y03-match-guarded", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(i: usize, b: bool, y: &mut [u32]) requires i < y.len() { match i { 0 if b => {}, _ => { y[i - 1] = 1; } } }"####),
    ("Y04-if-plus-one", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(i: usize, y: &mut [u32]) requires i < y.len() { let j = if i == 0 { 0 } else { i + 1 }; y[j] = 1; }"####),
    ("Y05-if-const-5", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(i: usize, y: &mut [u32]) requires i < y.len() { let j = if i == 0 { 5 } else { i - 1 }; y[j] = 1; }"####),
    ("Y06-range-neg", "accept", "", r####"kernel fn k(i: usize, y: &mut [u32]) requires i < y.len() { match i { 0..=3 => {}, _ => { y[i - 4] = 1; } } }"####),
    ("Y07-range-pos-underflow", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(i: usize, y: &mut [u32]) requires i < y.len() { match i { 0..=3 => { y[i - 1] = 1; }, _ => {} } }"####),
    ("Y08-range-pos-ok", "accept", "", r####"kernel fn k(i: usize, y: &mut [u32]) requires i < y.len() { match i { 1..=3 => { y[i - 1] = 1; }, _ => {} } }"####),
    ("Y09-or-lits", "accept", "", r####"kernel fn k(i: usize, y: &mut [u32]) requires i < y.len() { match i { 0 | 1 => {}, _ => { y[i - 2] = 1; } } }"####),
    ("Y10-if-lower-bound", "E-KERNEL-OBLIGATION", "", r####"kernel fn k(i: usize, y: &mut [u32]) requires i < y.len() { let j = if i == 0 { 0 } else { i - 1 }; y[j - 1] = 1; }"####),
    ("Y11-if-swap", "accept", "", r####"kernel fn k(i: usize, y: &mut [u32]) requires i < y.len() { let j = if i != 0 { i - 1 } else { 0 }; y[j] = 1; }"####),
    ("Y12-match-value", "accept", "", r####"kernel fn k(i: usize, y: &mut [u32]) requires i < y.len() { let j = match i { 0 => 0, n => n - 1 }; y[j] = 1; }"####),
];

/// F-132: closures written as arguments, parenthesised or as a block's tail (rustc: t08, t09, t35, t36).
const REVIEW_CLOSURE_ARGS: &[(&str, &str, &str, &str)] = &[
    // t08
    ("H1-paren-closure", "accept", "", r####"fn f() -> u32 { let a = 1u32; let v = [2u32, 3]; let mut out = &a; v.iter().for_each((|x: &u32| out = x)); *out }"####),
    // t09
    ("H2-block-closure", "accept", "", r####"fn f() -> u32 { let a = 1u32; let v = [2u32, 3]; let mut out = &a; v.iter().for_each({ |x: &u32| out = x }); *out }"####),
    // t35
    ("H6-block-stmt-closure", "accept", "", r####"fn f() -> u32 { let a = 1u32; let v = [2u32, 3]; let mut out = &a; v.iter().for_each({ let _k = 1u32; |x: &u32| out = x }); *out }"####),
    // t36
    ("H7-paren-block-paren", "accept", "", r####"fn f() -> u32 { let a = 1u32; let v = [2u32, 3]; let mut out = &a; v.iter().for_each(({ (|x: &u32| out = x) })); *out }"####),
    // an Fn* bound that writes the parameter as a reference
    ("H4-hr-bound", "E-LOCAL-MUT-STORE", "", r####"fn app<F: FnMut(&u32)>(mut f: F) { let k = 7u32; f(&k) }
fn g() -> u32 { let a = 1u32; let mut out = &a; app(|x: &u32| out = x); *out }"####),
];

/// F-133: overloaded indexing borrows the base first (rustc: t11 to t19, t24, t25, t30, t32 to t34).
const REVIEW_INDEXING: &[(&str, &str, &str, &str)] = &[
    // t11: E0502
    ("R12b-vec-index-len", "E-BORROW-CONFLICT", "", r####"fn g() -> u32 uses { alloc(Global) } { let mut v: Vec<u32> = Vec::new(); v.push(3); v[v.len() - 1] = 5; v[0] }"####),
    // t12: E0502
    ("R12d-vec-compound", "E-BORROW-CONFLICT", "", r####"fn g() -> u32 uses { alloc(Global) } { let mut v: Vec<u32> = Vec::new(); v.push(3); v[v.len() - 1] += 5; v[0] }"####),
    // t13
    ("R12c-array-index-len", "accept", "", r####"fn g() -> u32 { let mut a = [1u32, 2]; a[a.len() - 1] = 5; a[1] }"####),
    // t30: E0502
    ("R12-index-len", "E-BORROW-CONFLICT", "", r####"fn g() -> u32 uses { alloc(Global) } { let mut v: Vec<u32> = Vec::new(); v.push(3); let n = v.len(); v[n - 1] = 0; v[v.len() - 1] = 5; v[0] }"####),
    // t14
    ("X08-vec-idx-assign-val", "accept", "", r####"fn g() -> u32 uses { alloc(Global) } { let mut v: Vec<u32> = Vec::new(); v.push(3); v.push(4); v[0] = v[1]; v[1] += v[0]; v[0] + v[1] }"####),
    // t15
    ("X09-slice-idx", "accept", "", r####"fn g(s: &mut [u32]) -> u32 { s[s.len() - 1] = 5; s[0] }"####),
    // t16
    ("X10-vec-idx-read", "accept", "", r####"fn g() -> u32 uses { alloc(Global) } { let mut v: Vec<u32> = Vec::new(); v.push(0); v.push(7); let x = v[v.len() - 1]; x }"####),
    // t17: E0502
    ("X11-vec-idx-idx", "E-BORROW-CONFLICT", "", r####"fn g() -> u32 uses { alloc(Global) } { let mut v: Vec<u32> = Vec::new(); v.push(0); v[v[0] as usize] = 1; v[0] }"####),
    // t18: E0502
    ("X12-vec-mut-idx", "E-BORROW-CONFLICT", "", r####"fn g() -> u32 uses { alloc(Global) } { let mut v: Vec<u32> = Vec::new(); v.push(0); let r = &mut v[v.len() - 1]; *r = 2; v[0] }"####),
    // t19: E0502
    ("X13-vecvec-push", "E-BORROW-CONFLICT", "", r####"fn g() -> usize uses { alloc(Global) } { let mut v: Vec<Vec<u32>> = Vec::new(); v.push(Vec::new()); v[v.len() - 1].push(1); v[0].len() }"####),
    // t24: E0502
    ("X14-vecvec-inner", "E-BORROW-CONFLICT", "", r####"fn g() -> u32 uses { alloc(Global) } { let mut v: Vec<Vec<u32>> = Vec::new(); v.push(Vec::new()); v[0].push(0); v[0][v.len() - 1] = 1; v[0][0] }"####),
    // t25
    ("X15-arr-vec-push", "accept", "", r####"fn g() -> usize uses { alloc(Global) } { let mut a: [Vec<u32>; 2] = [Vec::new(), Vec::new()]; a[a.len() - 1].push(1); a[1].len() }"####),
    // t32: E0502
    ("X32-self-items-last", "E-BORROW-CONFLICT", "", r####"struct S { items: Vec<u32> }
impl S { fn set_last(&mut self, x: u32) { self.items[self.items.len() - 1] = x; } }"####),
    // t33: E0502
    ("X33-mut-slice-range", "E-BORROW-CONFLICT", "", r####"fn g() -> u32 uses { alloc(Global) } { let mut v: Vec<u32> = Vec::new(); v.push(1); v.push(2); v.push(3); let s = &mut v[1..v.len()]; s[0] = 9; v[1] }"####),
    // t34
    ("X34-push-read-idx", "accept", "", r####"fn g() -> u32 uses { alloc(Global) } { let mut v: Vec<u32> = Vec::new(); v.push(1); v.push(2); v.push(v[v.len() - 1]); v[2] }"####),
    ("I1-two-phase", "accept", "", r####"fn g() -> usize uses { alloc(Global) } { let mut v: Vec<usize> = Vec::new(); v.push(v.len()); v[0] }"####),
];

/// F-134: T-Call's strong case through a local reference (rustc values: t22, t29, t31).
const REVIEW_STRONG: &[(&str, &str, &str, &str)] = &[
    // alpha_o takes r's grade
    ("A1-samecell", "E-GRADE", "", r####"fn w(o: &mut u32, k: u32) { *o = k; }
#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut y = 0u32; let r = if h > 1 { &mut y } else { &mut y }; w(r, 4); y }"####),
    ("X17-strong-idx-arg", "E-GRADE", "", r####"fn w(o: &mut u32, k: u32) { *o = k; }
#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut a = [0u32; 2]; w(&mut a[(h % 2) as usize], 4); a[0] }"####),
    // OP-25: w's theta_mut mentions alpha_o
    ("X20-strong-localref-old-high", "E-GRADE", "", r####"fn w(o: &mut u32, k: u32) { *o = k; }
#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut y = h; let r = &mut y; w(r, 4); y }"####),
    ("X21-strong-direct-old-high", "E-GRADE", "", r####"fn w(o: &mut u32, k: u32) { *o = k; }
#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut y = h; w(&mut y, 4); y }"####),
    ("X27-cover-direct-old-high", "accept", "", r####"fn z(o: &mut [u32; 2]) { for i in 0..2 { o[i] = 4; } }
#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut y = [h, h]; z(&mut y); y[0] }"####),
    ("X28-cover-A1", "accept", "", r####"fn z(o: &mut [u32; 2]) { for i in 0..2 { o[i] = 4; } }
#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut y = [0u32; 2]; let r = if h > 1 { &mut y } else { &mut y }; z(r); y[0] }"####),
    ("X29-cover-A1-old-high", "accept", "", r####"fn z(o: &mut [u32; 2]) { for i in 0..2 { o[i] = 4; } }
#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut y = [h, h]; let r = if h > 1 { &mut y } else { &mut y }; z(r); y[0] }"####),
    // t31
    ("X30-cover-localref-old-high", "accept", "", r####"fn z(o: &mut [u32; 2]) { for i in 0..2 { o[i] = 4; } }
#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut y = [h, h]; let r = &mut y; z(r); y[0] }"####),
    // t29: F-114's case
    ("X31-cover-two-targets", "E-GRADE", "", r####"fn z(o: &mut [u32; 2]) { for i in 0..2 { o[i] = 4; } }
#[grade(exact, cross_device)] fn f(m: &Mutex<u32>) -> u32 uses { nondet } { let h = m.with_lock(|v| *v); let mut y = [0u32; 2]; let mut w2 = [0u32; 2]; let r = if h > 1 { &mut y } else { &mut w2 }; z(r); y[0] }"####),
];

#[test]
fn review_of_the_sync_cases() {
    let mut bad = vec![];
    let mut n = 0;
    for set in [REVIEW_TRANSFER, REVIEW_ANCHORS, REVIEW_CAPTURES, REVIEW_CODES, REVIEW_PATHFACTS, REVIEW_CLOSURE_ARGS, REVIEW_INDEXING, REVIEW_STRONG] {
        n += set.len();
        bad.extend(common::run_cases(set));
    }
    assert!(bad.is_empty(), "{} of {n} cases differ:\n{}", bad.len(), bad.join("\n"));
}

/// Run-time values of the accepted cases, equal to rustc 1.99.1's [M: probes t05, t10, t14, t16,
/// t25, t34, z01, z04, z06, z08, t08, t35, t36].
#[test]
fn review_of_the_sync_values() {
    let cases: &[(&str, &str, &str)] = &[
        (r####"fn g() -> u32 { let z = 5u32; let mut o: Option<&u32> = None; { let r = &mut o; let mut c = move |x| { *r = Some(x); }; c(&z); } *o.unwrap() }"####, "g", "5"),
        (r####"struct S { x: u32, y: u32 }
fn g() -> u32 { let mut s = S { x: 1, y: 2 }; let mut c = || s.x += 1; let r = &s.y; c(); *r + s.x }"####, "g", "4"),
        (r####"fn g() -> u32 uses { alloc(Global) } { let mut v: Vec<u32> = Vec::new(); v.push(3); v.push(4); v[0] = v[1]; v[1] += v[0]; v[0] + v[1] }"####, "g", "12"),
        (r####"fn g() -> u32 uses { alloc(Global) } { let mut v: Vec<u32> = Vec::new(); v.push(0); v.push(7); let x = v[v.len() - 1]; x }"####, "g", "7"),
        (r####"fn g() -> usize uses { alloc(Global) } { let mut a: [Vec<u32>; 2] = [Vec::new(), Vec::new()]; a[a.len() - 1].push(1); a[1].len() }"####, "g", "1"),
        (r####"fn g() -> u32 uses { alloc(Global) } { let mut v: Vec<u32> = Vec::new(); v.push(1); v.push(2); v.push(v[v.len() - 1]); v[2] }"####, "g", "2"),
        (r####"struct S { x: u32, y: u32 }
fn g() -> u32 { let mut s = S { x: 1, y: 2 }; let mut a = || s.x += 1; let mut b = || s.y += 1; a(); b(); s.x + s.y }"####, "g", "5"),
        (r####"struct S { x: u32, y: u32 }
fn g() -> u32 { let mut s = S { x: 1, y: 2 }; let c = || s.x + 1; s.y = 5; c() + s.y }"####, "g", "7"),
        (r####"struct T { a: S, b: u32 }
struct S { x: u32, y: u32 }
fn g() -> u32 { let mut t = T { a: S { x: 1, y: 2 }, b: 3 }; let mut c = || t.a.x += 1; let r = &t.a.y; c(); *r + t.b }"####, "g", "5"),
        (r####"struct V { v: [u32; 2], w: u32 }
fn g() -> u32 { let mut s = V { v: [1, 2], w: 3 }; let mut c = || s.v[0] += 1; let r = &s.w; c(); *r }"####, "g", "3"),
        (r####"fn f() -> u32 { let a = 1u32; let v = [2u32, 3]; let mut out = &a; v.iter().for_each((|x: &u32| out = x)); *out }"####, "f", "3"),
        (r####"fn f() -> u32 { let a = 1u32; let v = [2u32, 3]; let mut out = &a; v.iter().for_each({ let _k = 1u32; |x: &u32| out = x }); *out }"####, "f", "3"),
        (r####"fn f() -> u32 { let a = 1u32; let v = [2u32, 3]; let mut out = &a; v.iter().for_each(({ (|x: &u32| out = x) })); *out }"####, "f", "3"),
    ];
    for (src, entry, want) in cases {
        assert_eq!(common::run_entry(src, "", entry).unwrap(), *want, "{src}");
    }
}

/// F-125: the codes of one program in anchor order. D1: the conflict at `a = 2`, then the escape at
/// the returned expression, then the outliving at the closing brace. D2: two codes at the inner
/// block's closing brace, in spelling order. Two Linear values dropped at one brace are two reports
/// (the anchor is shared, the message names the value).
#[test]
fn review_of_the_sync_anchor_order() {
    let codes = |src: &str, flags: &str| -> Vec<String> { common::checked(src, flags).errors().iter().map(|d| d.code.clone()).collect() };
    assert_eq!(codes(r####"fn f(v: &[u32]) -> &u32 { let mut a = 1u32; let r = &a; a = 2; let l = [*r, 2]; &l[0] }"####, ""), vec!["E-BORROW-CONFLICT", "E-REF-ESCAPE", "E-BORROW-OUTLIVE"]);
    assert_eq!(codes(r####"fn f(store: &Store, id: ExpertId) -> Result<u32, IoError> uses { io, spawn } { let a = 0u32; let mut r = &a; { let l = store.lease(id)?; let z = 1u32; r = &z; } Ok(*r) }"####, "--canonical-prelude --module store"), vec!["E-BORROW-OUTLIVE", "E-LINEAR-DROP"]);
    let two = "linear struct T { id: u32 }\nfn mk(i: u32) -> T { T { id: i } }\nfn f() -> u32 { let t = mk(1); let o = if true { Some(t) } else { None }; 0 }";
    let c = common::checked(two, "");
    let drops: Vec<String> = c.errors().iter().filter(|d| d.code == "E-LINEAR-DROP").map(|d| d.msg.clone()).collect();
    assert_eq!(drops.len(), 2, "{drops:?}");
    assert!(drops.iter().any(|m| m.contains("`t`")) && drops.iter().any(|m| m.contains("`o`")), "{drops:?}");
}
