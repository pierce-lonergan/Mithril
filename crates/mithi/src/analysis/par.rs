//! T-Par (note section 5.9): E-PAR-BREAK, E-PAR-EFFECT (on the exercised row, F-36),
//! E-PAR-DISJOINT (writes injective in the iteration variable, through a declared footprint, or
//! by Proj-Split [prov, F-45]) and E-PAR-RACE (reads of written places only at the own index).
//! E-PAR-SEND is not checked by mithi v0 (Send/Sync are structural and every X1 type is both).
//!
//! Index functions are affine forms `k*i + c` read off the syntax: `i` itself, lossless integer
//! casts of it, `+`/`-` of par-invariant terms, and `*` by a non-zero constant (a literal or a
//! `const` item). Several writes to one place in an iteration must use the same index function,
//! or the same factor k with constant offsets less than |k| apart (a stride); otherwise iteration
//! i's second write can be iteration j's first (review 2026-10-16: each write was judged alone).
//! Any other use of a written place in the body (a whole-place borrow, a method receiver, a
//! call argument, a `for` iterable) is a read of every element, so E-PAR-RACE; `len()` is exempt.

use super::*;
use crate::ast::{BinOp, UnOp};
use crate::diag::Diag;
use crate::program::Label;
use std::collections::{BTreeMap, BTreeSet};

/// Is a cast from `from` to `to` lossless (every value of `from` survives)?
fn lossless_cast(from: &Ty, to: &Ty) -> bool {
    match (from, to) {
        (Ty::Int(a), Ty::Int(b)) => {
            if a == b {
                return true;
            }
            match (a.signed(), b.signed()) {
                (false, false) | (true, true) => b.bits() >= a.bits(),
                (false, true) => b.bits() > a.bits(),
                (true, false) => false,
            }
        }
        _ => false,
    }
}

/// The context of one `par for`: its variable, the locals it binds and the locals it assigns.
struct ParCx<'a> {
    c: &'a Checked,
    v: LocalId,
    /// the binder is an immutable, unshadowed identifier (F-103: `par for mut i` that assigns i
    /// indexes through an ordinary local; review 2026-10-23, N-95)
    var_ok: bool,
    inner: BTreeSet<LocalId>,
    assigned: BTreeSet<LocalId>,
    /// roots of every place the body writes (a field of one is not invariant)
    written_roots: BTreeSet<LocalId>,
    /// inner locals bound exactly once by an immutable `let x = e0;` (no pattern): x is e0
    /// (review 2026-10-23, pa11: `let j = i; y[j] = 1` was E-PAR-DISJOINT)
    defs: BTreeMap<LocalId, &'a TExpr>,
}

impl<'a> ParCx<'a> {
    fn is_var(&self, e: &TExpr) -> bool {
        match &e.kind {
            TK::Local(l) => *l == self.v && self.var_ok,
            // only a cast that keeps every value: `(i as u8) as usize` is not injective
            TK::Cast(x) => lossless_cast(&x.ty, &e.ty) && self.is_var(x),
            _ => false,
        }
    }

    fn const_val(&self, e: &TExpr) -> Option<i128> {
        match &e.kind {
            TK::Lit(LitVal::Int(v)) => Some(*v),
            TK::Const(cid) => self.c.program.const_int_value(*cid),
            TK::Cast(x) if lossless_cast(&x.ty, &e.ty) => self.const_val(x),
            TK::Unary(UnOp::Neg, x) => self.const_val(x).and_then(|v| v.checked_neg()),
            TK::Binary(BinOp::Add, a, b) => self.const_val(a)?.checked_add(self.const_val(b)?),
            TK::Binary(BinOp::Sub, a, b) => self.const_val(a)?.checked_sub(self.const_val(b)?),
            TK::Binary(BinOp::Mul, a, b) => self.const_val(a)?.checked_mul(self.const_val(b)?),
            _ => None,
        }
    }

    /// The same value in every iteration: constants, locals bound outside the body and not
    /// assigned in it, arithmetic of those, and the length of such a local's place.
    fn invariant(&self, e: &TExpr) -> bool {
        match &e.kind {
            TK::Lit(_) | TK::Const(_) => true,
            TK::Local(l) if self.inner.contains(l) => !self.assigned.contains(l) && self.defs.get(l).map(|d| self.invariant(d)).unwrap_or(false),
            TK::Local(l) => *l != self.v && !self.assigned.contains(l),
            TK::Cast(x) | TK::Unary(_, x) => self.invariant(x),
            TK::Binary(_, a, b) => self.invariant(a) && self.invariant(b),
            // a field of a place the body does not write
            TK::Field(b, _) | TK::Deref(b) => self.invariant(b) && place_root(e).map(|r| !self.written_roots.contains(&r)).unwrap_or(false),
            _ => false,
        }
    }

    /// `k*i + c`: Some((k, Some(c))) with a constant offset, Some((k, None)) with an invariant
    /// offset that is not a constant; None when the expression is not affine in i.
    fn affine(&self, e: &TExpr) -> Option<(i128, Option<i128>)> {
        if self.is_var(e) {
            return Some((1, Some(0)));
        }
        if let TK::Local(l) = &e.kind {
            if let Some(d) = self.defs.get(l) {
                if !self.assigned.contains(l) {
                    return self.affine(d);
                }
            }
        }
        if let Some(v) = self.const_val(e) {
            return Some((0, Some(v)));
        }
        if self.invariant(e) {
            return Some((0, None));
        }
        match &e.kind {
            TK::Cast(x) if lossless_cast(&x.ty, &e.ty) => self.affine(x),
            TK::Binary(op @ (BinOp::Add | BinOp::Sub), a, b) => {
                let (ka, ca) = self.affine(a)?;
                let (kb, cb) = self.affine(b)?;
                let s = if *op == BinOp::Add { 1 } else { -1 };
                let k = ka.checked_add(kb.checked_mul(s)?)?;
                let c = match (ca, cb) {
                    (Some(x), Some(y)) => x.checked_add(y.checked_mul(s)?),
                    _ => None,
                };
                Some((k, c))
            }
            TK::Binary(BinOp::Mul, a, b) => {
                // a non-zero constant factor (a literal or the value of a `const` item)
                if let Some(m) = self.const_val(b) {
                    let (k, c) = self.affine(a)?;
                    return Some((k.checked_mul(m)?, c.and_then(|x| x.checked_mul(m))));
                }
                if let Some(m) = self.const_val(a) {
                    let (k, c) = self.affine(b)?;
                    return Some((k.checked_mul(m)?, c.and_then(|x| x.checked_mul(m))));
                }
                None
            }
            TK::Unary(UnOp::Neg, x) => {
                let (k, c) = self.affine(x)?;
                Some((k.checked_neg()?, c.and_then(|v| v.checked_neg())))
            }
            _ => None,
        }
    }

    /// The same place in every iteration: no index, slice bound or projection argument along it
    /// depends on the iteration (`y.window(3 - i)[i]` is not `y[i]`: item N-47).
    fn base_invariant(&self, p: &TExpr) -> bool {
        match &p.kind {
            TK::Local(_) => true,
            TK::Field(b, _) | TK::Unsize(b) | TK::Borrow(_, b) => self.base_invariant(b),
            TK::Index(b, ix) => self.invariant(ix) && self.base_invariant(b),
            TK::SliceRange { base, lo, hi, .. } => lo.as_ref().map(|x| self.invariant(x)).unwrap_or(true) && hi.as_ref().map(|x| self.invariant(x)).unwrap_or(true) && self.base_invariant(base),
            TK::Deref(b) => match &b.kind {
                TK::Call { args, .. } => args.first().map(|r| self.base_invariant(r)).unwrap_or(true) && args.iter().skip(1).all(|a| self.invariant(a)),
                _ => self.base_invariant(b),
            },
            _ => false,
        }
    }

    /// Injective on the iteration range: affine with a non-zero factor.
    fn injective(&self, e: &TExpr) -> bool {
        matches!(self.affine(e), Some((k, _)) if k != 0)
    }

    /// A sub-slice `p[lo(i)..hi(i)]` whose ranges are disjoint across iterations:
    /// lo = k*i + c, hi = lo + d with 0 <= d <= |k| (`2*i .. 2*i + 2`, `k*i .. k*(i+1)`).
    fn disjoint_range(&self, lo: &TExpr, hi: &TExpr) -> bool {
        // k*i .. k*(i+1) with an invariant k (any k: k = 0 gives empty ranges)
        if let (TK::Binary(BinOp::Mul, a, b), TK::Binary(BinOp::Mul, c, d)) = (&hi.kind, &lo.kind) {
            let plus1 = |x: &TExpr| matches!(&x.kind, TK::Binary(BinOp::Add, p, q) if self.is_var(p) && matches!(q.kind, TK::Lit(LitVal::Int(1))));
            if (plus1(a) && self.is_var(c) && same_index(b, d) && self.invariant(b)) || (plus1(b) && self.is_var(d) && same_index(a, c) && self.invariant(a)) {
                return true;
            }
        }
        match (self.affine(lo), self.affine(hi)) {
            (Some((k1, Some(c1))), Some((k2, Some(c2)))) => k1 == k2 && k1 > 0 && c2 >= c1 && c2 - c1 <= k1,
            _ => false,
        }
    }
}

fn same_index(a: &TExpr, b: &TExpr) -> bool {
    match (&a.kind, &b.kind) {
        (TK::Local(x), TK::Local(y)) => x == y,
        (TK::Lit(x), TK::Lit(y)) => x == y,
        (TK::Const(x), TK::Const(y)) => x == y,
        (TK::Cast(x), TK::Cast(y)) => a.ty == b.ty && same_index(x, y),
        // a lossless cast on one side only keeps the value
        (TK::Cast(x), _) if lossless_cast(&x.ty, &a.ty) => same_index(x, b),
        (_, TK::Cast(y)) if lossless_cast(&y.ty, &b.ty) => same_index(a, y),
        (TK::Binary(o1, a1, b1), TK::Binary(o2, a2, b2)) => o1 == o2 && same_index(a1, a2) && same_index(b1, b2),
        (TK::Field(x, i), TK::Field(y, j)) => i == j && same_index(x, y),
        (TK::Deref(x), TK::Deref(y)) => same_index(x, y),
        _ => false,
    }
}

/// A footprinted projection call `proj(&mut *y, i)`: (receiver root, index argument).
fn footprint_call<'a>(c: &Checked, e: &'a TExpr) -> Option<(LocalId, &'a TExpr, FnId)> {
    let TK::Call { f, args, .. } = &e.kind else { return None };
    let has_fp = c.bodies.get(f).map(|b| !b.footprints.is_empty()).unwrap_or(false);
    if !has_fp || args.len() < 2 {
        return None;
    }
    Some((place_root(&args[0])?, &args[1], *f))
}

/// Do the declared footprints of `proj` for distinct values of its index parameter never
/// overlap? `self.blocks[t]`, `self.blocks[t*k .. (t+1)*k]`, `self.blocks[k*t .. k*t + k]`.
/// (`self.blocks[t .. t+4]` overlaps: item N-47, F-63.)
fn footprint_tiles(c: &Checked, proj: FnId) -> bool {
    let Some(b) = c.bodies.get(&proj) else { return false };
    let Some(fp) = b.footprints.first() else { return false };
    let Some(&t) = b.params.get(1) else { return false };
    let pc = ParCx { c, v: t, var_ok: !b.locals[t as usize].mutable, inner: BTreeSet::new(), assigned: BTreeSet::new(), written_roots: BTreeSet::new(), defs: BTreeMap::new() };
    match &fp.kind {
        TK::Index(_, ix) => pc.injective(ix),
        TK::SliceRange { lo: Some(lo), hi: Some(hi), inclusive: false, .. } => pc.disjoint_range(lo, hi),
        _ => false,
    }
}

/// The local a written place belongs to: through fields, indices and references, and through a
/// projection's result to the projection's receiver (`y.window(t)[i]` writes y).
fn write_root(p: &TExpr) -> Option<LocalId> {
    match &p.kind {
        TK::Local(l) => Some(*l),
        TK::Field(b, _) | TK::Index(b, _) | TK::Unsize(b) | TK::Borrow(_, b) => write_root(b),
        TK::SliceRange { base, .. } => write_root(base),
        TK::Deref(b) => match &b.kind {
            TK::Call { args, .. } => args.first().and_then(write_root),
            _ => write_root(b),
        },
        _ => None,
    }
}

/// The index argument of the footprinted projection a place is reached through, if any.
fn footprint_arg_of<'a>(c: &Checked, p: &'a TExpr) -> Option<&'a TExpr> {
    match &p.kind {
        TK::Deref(inner) => match footprint_call(c, inner) {
            Some((_, ix, _)) => Some(ix),
            None => footprint_arg_of(c, inner),
        },
        TK::Field(b, _) | TK::Index(b, _) | TK::Unsize(b) => footprint_arg_of(c, b),
        TK::SliceRange { base, .. } => footprint_arg_of(c, base),
        _ => None,
    }
}

struct Write<'a> {
    root: LocalId,
    index: Option<&'a TExpr>,
    span: Span,
    ok: bool,
    /// through a footprinted projection called with an invariant argument: that argument (two
    /// such writes must use the same one, F-95)
    proj_arg: Option<&'a TExpr>,
}

/// Closures passed to each (function, parameter): bodies generic over a closure type are
/// re-checked per closure site for the exercised row (C-CLOMONO, F-35, F-36).
fn passed_closures(c: &Checked) -> BTreeMap<(FnId, usize), Vec<ClosureId>> {
    let mut out: BTreeMap<(FnId, usize), Vec<ClosureId>> = BTreeMap::new();
    let mut fids: Vec<&FnId> = c.bodies.keys().collect();
    fids.sort();
    for fid in fids {
        let b = &c.bodies[fid];
        walk_deep(c, &b.expr, &mut |e| {
            if let TK::Call { f, args, .. } = &e.kind {
                for (i, a) in args.iter().enumerate() {
                    let cid = match &a.kind {
                        TK::Closure(x) => Some(*x),
                        TK::Borrow(_, inner) => match &inner.kind {
                            TK::Closure(x) => Some(*x),
                            _ => None,
                        },
                        _ => None,
                    };
                    if let Some(x) = cid {
                        out.entry((*f, i)).or_default().push(x);
                    }
                }
            }
        });
    }
    out
}

pub fn run(c: &mut Checked) {
    let passed = passed_closures(c);
    let mut diags = vec![];
    let mut fids: Vec<FnId> = c.bodies.keys().copied().collect();
    fids.sort();
    for fid in fids {
        let b = &c.bodies[&fid];
        let f = &c.program.fns[fid as usize];
        if f.role == FileRole::Std || f.body.is_none() {
            continue;
        }
        let path = f.path.clone();
        let mut pars: Vec<&TExpr> = vec![];
        walk_deep(c, &b.expr, &mut |e| {
            if let TK::For { par: true, .. } = e.kind {
                pars.push(e);
            }
        });
        for p in pars {
            let TK::For { id, pat, body, .. } = &p.kind else { continue };
            let var = pat.is_irrefutable_bind();
            // locals declared inside the body, loops declared inside it, locals it assigns
            let mut inner_locals: BTreeSet<LocalId> = BTreeSet::new();
            let mut inner_loops: BTreeSet<LoopId> = BTreeSet::new();
            let mut assigned: BTreeSet<LocalId> = BTreeSet::new();
            let mut defs: BTreeMap<LocalId, &TExpr> = BTreeMap::new();
            if let Some(v) = var {
                inner_locals.insert(v);
            }
            walk_deep(c, body, &mut |e| match &e.kind {
                TK::Block(stmts, _) => {
                    for s in stmts {
                        if let TStmt::Let { pat, init, els, .. } = s {
                            let mut bs = vec![];
                            pat.bindings(&mut bs);
                            inner_locals.extend(bs);
                            if let (PK::Bind { local, by_ref: None, sub: None }, Some(e0), None) = (&pat.kind, init, els) {
                                if !b.locals[*local as usize].mutable {
                                    defs.insert(*local, e0);
                                }
                            }
                        }
                    }
                }
                TK::For { pat, id: l, .. } => {
                    let mut bs = vec![];
                    pat.bindings(&mut bs);
                    inner_locals.extend(bs);
                    inner_loops.insert(*l);
                }
                TK::Loop(l, _) | TK::While(l, _, _) => {
                    inner_loops.insert(*l);
                }
                TK::LetCond(pat, _) => {
                    let mut bs = vec![];
                    pat.bindings(&mut bs);
                    inner_locals.extend(bs);
                }
                TK::Match(_, arms) => {
                    for a in arms {
                        let mut bs = vec![];
                        a.pat.bindings(&mut bs);
                        inner_locals.extend(bs);
                    }
                }
                TK::Assign(p, _) | TK::AssignOp(_, p, _) => {
                    if let TK::Local(l) = p.kind {
                        assigned.insert(l);
                    }
                }
                TK::Borrow(true, p) => {
                    if let TK::Local(l) = p.kind {
                        assigned.insert(l);
                    }
                }
                _ => {}
            });
            for (l, ld) in b.locals.iter().enumerate() {
                if ld.closure.is_some() {
                    inner_locals.insert(l as LocalId);
                }
            }
            // E-PAR-BREAK (F-75): no break targets the par or a loop enclosing it (labelled
            // breaks included), and no continue targets an enclosing loop
            walk_deep(c, body, &mut |e| match &e.kind {
                TK::Break(l, _) if !inner_loops.contains(l) => {
                    let what = if l == id { "out of a `par for`" } else { "out of a loop enclosing a `par for`" };
                    diags.push(Diag::new("E-PAR-BREAK", e.span, format!("`break` {what}: the iteration order would be observable (01 section 12.3, F-75)")).in_def(&path));
                }
                TK::Continue(l) if l != id && !inner_loops.contains(l) => {
                    diags.push(Diag::new("E-PAR-BREAK", e.span, "`continue` of a loop enclosing a `par for`: the iteration order would be observable (F-75)").in_def(&path));
                }
                _ => {}
            });
            // E-PAR-EFFECT on the exercised row
            let mut labels = vec![];
            super::rows::expr_labels(c, &c.facts.ex_rows, body, false, &mut labels);
            // calls of a closure parameter: the rows of the closures passed for it
            walk_deep(c, body, &mut |e| {
                if let TK::CallValue(fv, _) = &e.kind {
                    let local = match &fv.kind {
                        TK::Local(l) => Some(*l),
                        TK::Deref(x) => match x.kind {
                            TK::Local(l) => Some(l),
                            _ => None,
                        },
                        _ => None,
                    };
                    if let Some(l) = local {
                        if let Some(pi) = b.locals[l as usize].param {
                            for cid in passed.get(&(fid, pi)).cloned().unwrap_or_default() {
                                super::rows::expr_labels(c, &c.facts.ex_rows, &c.closures[cid as usize].body, false, &mut labels);
                            }
                        }
                    }
                }
            });
            // calls of a function value: the rows of every function the enclosing body uses as
            // a value (it may be any of them; their rows were charged where they were named)
            let mut calls_fn_value = false;
            walk_deep(c, body, &mut |e| {
                if let TK::CallValue(fv, _) = &e.kind {
                    if matches!(fv.ty.strip_refs(), Ty::FnPtr(..)) {
                        calls_fn_value = true;
                    }
                }
            });
            if calls_fn_value {
                walk_deep(c, &b.expr, &mut |e| {
                    if let TK::FnRef(g, _) = &e.kind {
                        if let Some(r) = c.facts.ex_rows.get(g) {
                            for l in r {
                                labels.push((l.clone(), e.span));
                            }
                        }
                    }
                });
            }
            let mut bad: Vec<String> = vec![];
            for (l, _) in &labels {
                let ok = matches!(l, Label::Blob) || matches!(l, Label::Alloc(a) if a == "Global");
                if !ok && !bad.contains(&l.text()) {
                    bad.push(l.text());
                }
            }
            if !bad.is_empty() {
                diags.push(Diag::new("E-PAR-EFFECT", p.span, format!("a `par for` body exercises {{{}}}; only `blob` and `alloc` on Sync arenas are allowed (01 section 12.3, F-36: rows of called closures and nondet under `deterministic` count)", bad.join(", "))).in_def(&path));
            }
            // writes
            let Some(v) = var else { continue };
            let mut written_roots: BTreeSet<LocalId> = BTreeSet::new();
            walk_deep(c, body, &mut |e| {
                if let TK::Assign(p, _) | TK::AssignOp(_, p, _) | TK::Borrow(true, p) = &e.kind {
                    if let Some(r) = write_root(p) {
                        written_roots.insert(r);
                    }
                }
            });
            let var_ok = !b.locals[v as usize].mutable && !assigned.contains(&v);
            let pc = ParCx { c, v, var_ok, inner: inner_locals.clone(), assigned: assigned.clone(), written_roots, defs };
            let mut writes: Vec<Write> = vec![];
            let mut stack: Vec<&TExpr> = vec![body];
            let mut all: Vec<&TExpr> = vec![];
            while let Some(e) = stack.pop() {
                all.push(e);
                if let TK::Closure(cid) = &e.kind {
                    stack.push(&c.closures[*cid as usize].body);
                }
                for ch in e.children() {
                    stack.push(ch);
                }
            }
            // receiver borrows of footprinted projections are judged at the projection
            let mut proj_recv: BTreeSet<*const TExpr> = BTreeSet::new();
            for x in &all {
                if footprint_call(c, x).is_some() {
                    if let TK::Call { args, .. } = &x.kind {
                        proj_recv.insert(&args[0] as *const TExpr);
                    }
                }
            }
            for e in &all {
                let (place, is_assign) = match &e.kind {
                    TK::Assign(p, _) | TK::AssignOp(_, p, _) => (p.as_ref(), true),
                    TK::Borrow(true, p) => (p.as_ref(), false),
                    _ => continue,
                };
                if !is_assign && proj_recv.contains(&(*e as *const TExpr)) {
                    continue;
                }
                let Some(root) = write_root(place) else { continue };
                if inner_locals.contains(&root) {
                    continue;
                }
                // through a footprinted projection whose index is this iteration's own
                let mut ok = false;
                let mut index = None;
                let mut proj_arg: Option<&TExpr> = None;
                let mut cur = place;
                loop {
                    match &cur.kind {
                        TK::Index(base, idx) => {
                            if pc.injective(idx) && pc.base_invariant(base) {
                                ok = true;
                                index = Some(idx.as_ref());
                                // an invariant base reached through a footprinted projection names
                                // one footprint (F-95)
                                proj_arg = footprint_arg_of(c, base);
                                break;
                            }
                            cur = base;
                        }
                        TK::Field(base, _) => cur = base,
                        TK::Deref(inner) => {
                            if let Some((_r, ix, proj)) = footprint_call(c, inner) {
                                // F-102: the receiver and every other argument are invariant
                                // (`y[i..4].whole(0)[1 - i]` writes one element twice; review
                                // 2026-10-23, N-93)
                                let TK::Call { args: pargs, .. } = &inner.kind else { break };
                                let rest_inv = pc.base_invariant(&pargs[0]) && pargs.iter().skip(2).all(|a| pc.invariant(a));
                                if !rest_inv {
                                    break;
                                }
                                // Proj-Split (F-63): distinct indices must give disjoint footprints
                                if pc.injective(ix) && footprint_tiles(c, proj) {
                                    ok = true;
                                    index = Some(ix);
                                    break;
                                }
                                // an invariant projection argument: an inner par writes
                                // footprint[π(j)] (judged there); two such writes must name the
                                // same footprint (F-95, below)
                                if let TK::Index(_, ix2) = &place.kind {
                                    if pc.invariant(ix) && pc.injective(ix2) {
                                        ok = true;
                                        index = Some(ix2.as_ref());
                                        proj_arg = Some(ix);
                                    }
                                }
                                break;
                            }
                            cur = inner;
                        }
                        TK::SliceRange { base, lo, hi, .. } => {
                            // &mut p[lo(i)..hi(i)] with disjoint ranges
                            if let (Some(l), Some(h)) = (lo, hi) {
                                if pc.disjoint_range(l, h) {
                                    ok = true;
                                    index = Some(l.as_ref());
                                    break;
                                }
                            }
                            cur = base;
                        }
                        _ => break,
                    }
                }
                writes.push(Write { root, index, span: e.span, ok, proj_arg });
            }
            // writes without an assignment or an explicit `&mut p` (T-Par's W includes the `&mut`
            // accesses of §5.4 and of calls; review 2026-10-23, c1, pa14, c6, c8, c10, pa15):
            // (1) a `&mut`-carrying local passed by implicit reborrow, moved or copied
            let mut implicit: Vec<(LocalId, Span)> = vec![];
            implicit_mut_uses(c, body, &mut implicit);
            for (root, sp) in implicit {
                if !inner_locals.contains(&root) {
                    writes.push(Write { root, index: None, span: sp, ok: false, proj_arg: None });
                }
            }
            // (2) a call of a closure created outside the body: its by-mut captures (and the
            // places its by-move `&mut` captures point to) are written in every iteration, and a
            // FnMut or FnOnce closure's own state too; (3) a call of an FnMut/FnOnce type
            // parameter (or `&mut F`) writes the closure it stands for
            let created_inside: BTreeSet<ClosureId> = {
                let mut s = BTreeSet::new();
                walk_deep(c, body, &mut |x| {
                    if let TK::Closure(cid) = x.kind {
                        s.insert(cid);
                    }
                });
                s
            };
            let gen_kinds: Vec<Option<u8>> = f.generics.iter().map(|g| g.bounds.iter().find_map(|bd| if let crate::program::BoundDef::Fn { kind, .. } = bd { Some(*kind) } else { None })).collect();
            for x in &all {
                let TK::CallValue(fv, _) = &x.kind else { continue };
                let holder = place_root(fv).filter(|r| !inner_locals.contains(r));
                match fv.ty.strip_refs() {
                    Ty::Closure(cid) if !created_inside.contains(cid) => {
                        let cd = &c.closures[*cid as usize];
                        for cap in &cd.captures {
                            let writes_cap = cap.mode == CaptureMode::Mut || (cap.mode == CaptureMode::Move && holds_mut_ref(&cap.ty));
                            if writes_cap && !inner_locals.contains(&cap.local) {
                                writes.push(Write { root: cap.local, index: None, span: x.span, ok: false, proj_arg: None });
                            }
                        }
                        if cd.fn_kind >= 1 {
                            if let Some(h) = holder {
                                writes.push(Write { root: h, index: None, span: x.span, ok: false, proj_arg: None });
                            }
                        }
                    }
                    Ty::Param(g) => {
                        if gen_kinds.get(*g as usize).copied().flatten().unwrap_or(0) >= 1 {
                            if let Some(h) = holder {
                                writes.push(Write { root: h, index: None, span: x.span, ok: false, proj_arg: None });
                            }
                        }
                    }
                    _ => {}
                }
            }
            for w in &writes {
                if !w.ok {
                    let nm = b.locals[w.root as usize].name.clone();
                    diags.push(Diag::new("E-PAR-DISJOINT", w.span, format!("a `par for` iteration writes `{nm}` at a place not indexed injectively by its own iteration variable (a cross-iteration write or accumulator; 02 section 3)")).in_def(&path));
                }
            }
            // several writes to one place: one index function, or a stride (same factor k,
            // constant offsets less than |k| apart)
            let mut by_root: BTreeMap<LocalId, Vec<&Write>> = BTreeMap::new();
            for w in writes.iter().filter(|w| w.ok) {
                by_root.entry(w.root).or_default().push(w);
            }
            for (root, ws) in &by_root {
                // F-95: writes through a projection with an invariant argument name one footprint
                // each; two different footprints (`y.window(0)[i]`, `y.window(1)[i]`) can overlap
                // across iterations, and so can a footprint and the place itself (review
                // 2026-10-23, N-87)
                if ws.iter().any(|w| w.proj_arg.is_some()) {
                    let first = ws[0].proj_arg;
                    let same = ws.iter().all(|w| match (w.proj_arg, first) {
                        (Some(a), Some(b)) => same_index(a, b) || matches!((pc.const_val(a), pc.const_val(b)), (Some(x), Some(y)) if x == y),
                        _ => false,
                    });
                    if !same {
                        let nm = b.locals[*root as usize].name.clone();
                        let sp = ws.last().map(|w| w.span).unwrap_or(p.span);
                        diags.push(Diag::new("E-PAR-DISJOINT", sp, format!("a `par for` iteration writes `{nm}` through two different footprints (or a footprint and the place itself), which can meet across iterations (F-95)")).in_def(&path));
                        continue;
                    }
                }
                let idxs: Vec<&TExpr> = ws.iter().filter_map(|w| w.index).collect();
                if idxs.len() < 2 {
                    continue;
                }
                let first = idxs[0];
                let fa = pc.affine(first);
                let mut offs: Vec<i128> = vec![];
                let mut compatible = true;
                for ix in &idxs {
                    if same_index(first, ix) {
                        if let Some((_, Some(cc))) = pc.affine(ix) {
                            offs.push(cc);
                        }
                        continue;
                    }
                    match (fa, pc.affine(ix)) {
                        (Some((k1, Some(_))), Some((k2, Some(c2)))) if k1 == k2 && k1 != 0 => offs.push(c2),
                        _ => compatible = false,
                    }
                }
                if let Some((k, Some(c0))) = fa {
                    offs.push(c0);
                    let (mn, mx) = (offs.iter().min().copied().unwrap_or(0), offs.iter().max().copied().unwrap_or(0));
                    if mx - mn >= k.abs() {
                        compatible = false;
                    }
                }
                if !compatible {
                    let nm = b.locals[*root as usize].name.clone();
                    let sp = ws.last().map(|w| w.span).unwrap_or(p.span);
                    diags.push(Diag::new("E-PAR-DISJOINT", sp, format!("a `par for` iteration writes `{nm}` at two index functions that can meet across iterations (iteration i's write is iteration j's other write)")).in_def(&path));
                }
            }
            // reads of written places: only at an index the iteration itself writes
            let written: BTreeMap<LocalId, Vec<&TExpr>> = {
                let mut m: BTreeMap<LocalId, Vec<&TExpr>> = BTreeMap::new();
                for w in &writes {
                    m.entry(w.root).or_default().extend(w.index);
                }
                m
            };
            let mut rd = Reads { pc: &pc, written: &written, proj_recv: &proj_recv, hits: vec![] };
            rd.visit(body);
            let mut seen: BTreeSet<Span> = BTreeSet::new();
            for (sp, root) in rd.hits {
                if !seen.insert(sp) {
                    continue;
                }
                let nm = b.locals[root as usize].name.clone();
                diags.push(Diag::new("E-PAR-RACE", sp, format!("`{nm}` is written by this `par for` and read here outside the iteration's own index (another iteration's element, or the whole place; 01 section 12.3)")).in_def(&path));
            }
        }
    }
    c.diags.extend(diags);
}

/// The read premise of T-Par: every use of a written place that is not a write target and not
/// an element read at an index the iteration itself writes is E-PAR-RACE.
struct Reads<'a, 'b> {
    pc: &'a ParCx<'b>,
    written: &'a BTreeMap<LocalId, Vec<&'a TExpr>>,
    proj_recv: &'a BTreeSet<*const TExpr>,
    hits: Vec<(Span, LocalId)>,
}

impl<'a, 'b> Reads<'a, 'b> {
    fn own_index(&self, root: LocalId, idx: &TExpr) -> bool {
        let Some(ws) = self.written.get(&root) else { return false };
        ws.iter().any(|w| same_index(w, idx) || matches!((self.pc.affine(w), self.pc.affine(idx)), (Some((k1, Some(c1))), Some((k2, Some(c2)))) if k1 == k2 && k1 != 0 && c1 == c2))
    }

    fn root_of(&self, e: &TExpr) -> Option<LocalId> {
        let r = place_root(e)?;
        if self.written.contains_key(&r) && !self.pc.inner.contains(&r) {
            Some(r)
        } else {
            None
        }
    }

    /// The index subexpressions along a place (they are reads of their own).
    fn visit_place_indices(&mut self, p: &TExpr) {
        match &p.kind {
            TK::Index(b, i) => {
                self.visit(i);
                self.visit_place_indices(b);
            }
            TK::SliceRange { base, lo, hi, .. } => {
                if let Some(x) = lo {
                    self.visit(x);
                }
                if let Some(x) = hi {
                    self.visit(x);
                }
                self.visit_place_indices(base);
            }
            TK::Field(b, _) | TK::Deref(b) | TK::Unsize(b) | TK::Borrow(_, b) => self.visit_place_indices(b),
            TK::Local(_) => {}
            _ => self.visit(p),
        }
    }

    /// A read of place `p` (rooted in a written place): at an own index, or of the whole place.
    fn read_place(&mut self, p: &TExpr, root: LocalId) {
        let mut cur = p;
        loop {
            match &cur.kind {
                TK::Index(b, i) => {
                    if self.own_index(root, i) {
                        self.visit_place_indices(p);
                        return;
                    }
                    cur = b;
                }
                TK::Field(b, _) | TK::Deref(b) | TK::Unsize(b) | TK::Borrow(_, b) => cur = b,
                TK::SliceRange { base, .. } => cur = base,
                _ => break,
            }
        }
        self.hits.push((p.span, root));
        self.visit_place_indices(p);
    }

    fn visit(&mut self, e: &TExpr) {
        match &e.kind {
            TK::Assign(p, r) => {
                self.visit(r);
                self.visit_place_indices(p);
            }
            TK::AssignOp(_, p, r) => {
                // `p op= r` reads p too: at the write's own index
                self.visit(r);
                match self.root_of(p) {
                    Some(root) => self.read_place(p, root),
                    None => self.visit_place_indices(p),
                }
            }
            TK::Borrow(true, p) => {
                // a write (judged above); a projection receiver is judged at the projection
                self.visit_place_indices(p);
            }
            TK::Call { f, args, .. } => {
                let len = matches!(self.pc.c.program.fns[*f as usize].builtin.as_deref(), Some("slice_len") | Some("str_len"));
                for a in args {
                    if len || self.proj_recv.contains(&(a as *const TExpr)) {
                        self.visit_place_indices(a);
                    } else {
                        self.visit(a);
                    }
                }
            }
            TK::Closure(cid) => {
                let body = &self.pc.c.closures[*cid as usize].body;
                self.visit(body);
            }
            TK::Local(_) | TK::Index(..) | TK::Field(..) | TK::Deref(_) | TK::SliceRange { .. } | TK::Unsize(_) | TK::Borrow(false, _) => {
                match self.root_of(e) {
                    Some(root) => self.read_place(e, root),
                    None => {
                        for ch in e.children() {
                            self.visit(ch);
                        }
                    }
                }
            }
            _ => {
                for ch in e.children() {
                    self.visit(ch);
                }
            }
        }
    }
}
