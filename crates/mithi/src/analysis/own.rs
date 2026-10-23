//! Ownership, linearity and loans (note sections 5.4, 5.6, 5.8): E-MOVE-USED, E-MOVE-LOOP,
//! E-MOVE-BORROWED (a move out of a place behind a reference or an index), E-LINEAR-DROP, E-LINEAR-PARTIAL, E-BORROW-CONFLICT, E-BORROW-OUTLIVE, E-LOCAL-MUT-STORE, and the
//! body part of T-Ret (a projection's result carries only loans on the elided parameter).
//!
//! Loans travel with values (F-39): `&p` creates a loan; `let`, assignment, std storing calls and
//! closure creation move loan sets; a loan is live while a live local carries it. Liveness is
//! approximated by source order within one body, with a use inside a loop keeping a local live for
//! the whole loop (Rust's NLL restricted to one body; no signature mentions a lifetime).
//! A move out of a field of an owned local moves that field path only (Rust's partial moves).
//!
//! Places reached through a reference are rooted at the reference local with a path that starts
//! with `*` (`(*r).f` is `r` + `*.0`), as NLL roots them; a loan on such a place targets the
//! reference local, and accesses through the reference are checked against it (review
//! 2026-10-16: through `&mut` parameters nothing was checked). A loan is named by its creation
//! site (F-80), so the loop fixpoint terminates.

use super::wf::{is_linear, is_local};
use super::*;
use crate::diag::Diag;
use crate::program::BoundDef;
use std::collections::{BTreeMap, BTreeSet, HashMap};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum MS {
    Init,
    Moved,
    Maybe,
    Uninit,
}

fn join_ms(a: MS, b: MS) -> MS {
    match (a, b) {
        (x, y) if x == y => x,
        (MS::Uninit, _) | (_, MS::Uninit) => MS::Maybe,
        _ => MS::Maybe,
    }
}

#[derive(Clone, Debug)]
#[allow(dead_code)]
struct Loan {
    /// target local (None = the caller's place behind reference parameter `param`)
    target: Option<LocalId>,
    param: Option<LocalId>,
    path: String,
    mutable: bool,
    span: Span,
    /// for a symbolic loan ℓ_j,k* (target None): the reference position k within the type of
    /// parameter j (F-62: one symbol per reference position, not per parameter; review
    /// 2026-10-23, e2): `.i` a tuple component, `[]` an element of an array, slice or Vec, `<k>`
    /// the k-th type argument of a std type (Option and Result payloads), `*` through a
    /// reference, `~` a reference hidden inside a std adapter; "" the parameter itself
    pos: String,
}

/// The holder reported for a loan passed as an earlier argument of the call being evaluated.
const PENDING: LocalId = LocalId::MAX;
/// The holder reported for a loan carried by the iterator of an enclosing `for` loop.
const ITER: LocalId = LocalId::MAX - 1;

/// Ordered maps throughout, so that diagnostics (which holder a message names) do not depend on
/// hash seeds (review 2026-10-16: `check --json` differed between runs).
#[derive(Clone, PartialEq)]
struct St {
    ms: BTreeMap<LocalId, MS>,
    loans_of: BTreeMap<LocalId, BTreeSet<u32>>,
    /// field paths moved out of an owned local (".a", ".a.b")
    /// (path -> the moved place as written, for messages)
    pmoved: BTreeMap<LocalId, BTreeMap<String, String>>,
    dead: bool,
}

/// Where a moved place lives (note section 5.4, access mode Move).
enum Origin {
    /// a local or a field path of an owned local
    Owned(LocalId, String),
    /// behind a reference or an index: E-MOVE-BORROWED
    Behind,
    /// a temporary (a call result, a literal)
    Temp,
}

#[derive(Clone, Copy, PartialEq)]
enum Use {
    Value,
    Read,
    Write,
}

#[allow(dead_code)]
struct Own<'a> {
    c: &'a Checked,
    body: &'a Body,
    fid: FnId,
    st: St,
    loans: Vec<Loan>,
    scopes: Vec<Vec<LocalId>>,
    loop_stack: Vec<(LoopId, usize, Span)>,
    /// (loop id, scope depth at loop entry)
    diags: Vec<Diag>,
    uses: HashMap<LocalId, Vec<u32>>,
    loop_spans: Vec<Span>,
    reported: BTreeSet<(String, Span)>,
    second_pass: bool,
    param_loan: HashMap<LocalId, u32>,
    is_copy_cache: HashMap<String, bool>,
    returned_loans: Vec<(BTreeSet<u32>, Span)>,
    closure_results: HashMap<ClosureId, BTreeSet<u32>>,
    /// > 0 while the base of a place is evaluated (partial-move checks belong to the whole place)
    base_depth: u32,
    /// loans passed by the arguments already evaluated of the calls in progress; `true` marks a
    /// method's `&mut self` reservation, which admits reads until the call (two-phase borrows)
    pending: Vec<(BTreeSet<u32>, bool)>,
    /// loans carried by the iterators of the enclosing `for` loops (live for the whole loop)
    loop_iters: Vec<BTreeSet<u32>>,
    /// per loop being evaluated: the states at its `break`s and at its `continue`s, and the
    /// loans its `break` values carry
    jumps: Vec<(LoopId, Vec<St>, Vec<St>, BTreeSet<u32>)>,
    /// loan ids by creation site (F-80)
    loan_ids: HashMap<(Option<LocalId>, Option<LocalId>, String, bool, Span), u32>,
    /// generic parameters of the definition whose bounds make them Copy
    copy_params: Vec<bool>,
    /// locals some loan of this body targets (a local never borrowed has no conflicts)
    targeted: std::collections::HashSet<LocalId>,
    /// the Fn kind of each generic parameter with an Fn* bound
    gen_fn_kinds: Vec<Option<u8>>,
    /// locals that hold a by-value part of a parameter's value, by destructuring: per parameter,
    /// the position of the part (F-62). Absent: unknown (the per-parameter rule applies)
    sym_base: HashMap<LocalId, BTreeMap<LocalId, String>>,
    /// per closure created in this body: the indices of its parameters that are higher-ranked
    /// references (the closure is passed where an `Fn*` bound writes that parameter as an elided
    /// reference, `F: FnMut(&u32)`; note section 5.7 "Stores into captures")
    hr_params: HashMap<ClosureId, Vec<usize>>,
    /// the symbolic loans of those parameters, while the closure body is checked
    hr_loans: BTreeSet<u32>,
    /// the closures whose bodies are being checked (innermost last)
    clo_stack: Vec<ClosureId>,
}

impl<'a> Own<'a> {
    fn err(&mut self, code: &str, sp: Span, msg: String) {
        if self.reported.insert((code.to_string(), sp)) {
            let path = fn_path(self.c, self.fid);
            self.diags.push(Diag::new(code, sp, msg).in_def(&path));
        }
    }
    fn name(&self, l: LocalId) -> String {
        self.body.locals[l as usize].name.clone()
    }
    fn holder(&self, h: LocalId) -> String {
        if h == PENDING {
            "an earlier argument or component of the same call or value".into()
        } else if h == ITER {
            "the iterator of the enclosing `for` loop".into()
        } else {
            self.name(h)
        }
    }
    fn is_copy(&mut self, t: &Ty) -> bool {
        let key = format!("{t:?}");
        if let Some(v) = self.is_copy_cache.get(&key) {
            return *v;
        }
        let v = copy_ty_with(self.c, t, &self.copy_params);
        self.is_copy_cache.insert(key, v);
        v
    }
    fn lin(&self, t: &Ty) -> bool {
        is_linear(self.c, t)
    }

    /// Is local `l` used at a source position after `pos` (or inside a loop around `pos`)?
    fn live_after(&self, l: LocalId, pos: u32) -> bool {
        if let Some(us) = self.uses.get(&l) {
            if us.iter().any(|u| *u > pos) {
                return true;
            }
            // a use inside an enclosing loop keeps it live across iterations
            for (_, _, lsp) in &self.loop_stack {
                if us.iter().any(|u| *u >= lsp.lo && *u < lsp.hi) && pos >= lsp.lo && pos < lsp.hi {
                    return true;
                }
            }
        }
        false
    }

    fn new_loan(&mut self, target: Option<LocalId>, param: Option<LocalId>, path: String, mutable: bool, span: Span) -> u32 {
        self.new_loan_at(target, param, path, mutable, span, String::new())
    }

    fn new_loan_at(&mut self, target: Option<LocalId>, param: Option<LocalId>, path: String, mutable: bool, span: Span, pos: String) -> u32 {
        let key = (target, param, format!("{path}\u{0}{pos}"), mutable, span);
        if let Some(id) = self.loan_ids.get(&key) {
            return *id;
        }
        if let Some(t) = target {
            self.targeted.insert(t);
        }
        self.loans.push(Loan { target, param, path, mutable, span, pos });
        let id = (self.loans.len() - 1) as u32;
        self.loan_ids.insert(key, id);
        id
    }

    /// The parameter and reference position of a place reached from a local whose position is
    /// known (`sym_base`): `(*v)[]` for an element of `*v` (F-62).
    fn place_pos(&self, p: &TExpr) -> Option<(LocalId, String)> {
        match &p.kind {
            TK::Local(l) => {
                let m = self.sym_base.get(l)?;
                if m.len() != 1 {
                    return None;
                }
                m.iter().next().map(|(j, b)| (*j, b.clone()))
            }
            TK::Deref(b) => match &b.kind {
                TK::Unsize(u) => match &u.kind {
                    TK::Borrow(_, q) => self.place_pos(q),
                    _ => None,
                },
                TK::Borrow(_, q) => self.place_pos(q),
                _ if b.ty.is_ref() => self.place_pos(b).map(|(j, s)| (j, format!("{s}*"))),
                _ => self.place_pos(b),
            },
            TK::Field(b, i) => self.place_pos(b).map(|(j, s)| (j, format!("{s}.{i}"))),
            TK::Index(b, _) => self.place_pos(b).map(|(j, s)| (j, format!("{s}[]"))),
            TK::SliceRange { base, .. } => self.place_pos(base),
            TK::Unsize(b) => self.place_pos(b),
            TK::Borrow(_, q) => self.place_pos(q),
            _ => None,
        }
    }

    /// The bindings of a pattern with the position of the part each binds by value (None: a
    /// binding by reference, or under a dereference).
    fn pat_paths(&self, p: &TPat, path: &str, under_ref: bool, out: &mut Vec<(LocalId, Option<String>)>) {
        match &p.kind {
            PK::Bind { local, by_ref, sub } => {
                let r = under_ref || by_ref.is_some();
                out.push((*local, if r { None } else { Some(path.to_string()) }));
                if let Some(sp) = sub {
                    self.pat_paths(sp, path, r, out);
                }
            }
            PK::Tuple(ps) => {
                for (i, x) in ps.iter().enumerate() {
                    self.pat_paths(x, &format!("{path}.{i}"), under_ref, out);
                }
            }
            PK::Variant { adt, variant, fields } => {
                let ad = &self.c.program.adts[*adt as usize];
                for (fi, x) in fields {
                    let suffix = match ad.variants.get(*variant as usize).and_then(|v| v.fields.get(*fi as usize)).map(|f| &f.ty) {
                        Some(Ty::Param(k)) if ad.role == FileRole::Std => format!("<{k}>"),
                        _ => format!(".{fi}"),
                    };
                    self.pat_paths(x, &format!("{path}{suffix}"), under_ref, out);
                }
            }
            PK::Deref(x) => self.pat_paths(x, &format!("{path}*"), true, out),
            PK::Slice(ps, _) => {
                for x in ps {
                    self.pat_paths(x, &format!("{path}[]"), under_ref, out);
                }
            }
            PK::Or(ps) => {
                for x in ps {
                    self.pat_paths(x, path, under_ref, out);
                }
            }
            _ => {}
        }
    }

    fn move_origin(&self, e: &TExpr) -> Origin {
        match &e.kind {
            TK::Local(l) => {
                if self.body.locals[*l as usize].ty.is_ref() {
                    Origin::Behind
                } else {
                    Origin::Owned(*l, String::new())
                }
            }
            TK::Field(b, i) => match self.move_origin(b) {
                Origin::Owned(l, p) => Origin::Owned(l, format!("{p}.{i}")),
                o => o,
            },
            TK::Deref(_) | TK::Index(..) | TK::SliceRange { .. } => Origin::Behind,
            _ => Origin::Temp,
        }
    }

    /// E-MOVE-USED when the place overlaps a field path already moved out of its root local.
    fn check_partial(&mut self, p: &TExpr, sp: Span) {
        let Some(l) = place_root_direct(p) else { return };
        let path = path_text(p);
        let hit = self.st.pmoved.get(&l).and_then(|set| set.iter().find(|(m, _)| overlaps(m, &path)).map(|(_, t)| t.clone()));
        if let Some(t) = hit {
            let code = if self.second_pass { "E-MOVE-LOOP" } else { "E-MOVE-USED" };
            let nm = self.name(l);
            self.err(code, sp, format!("`{t}` was moved out of `{nm}` and is used here"));
        }
    }

    fn move_behind(&mut self, e: &TExpr) {
        self.err(
            "E-MOVE-BORROWED",
            e.span,
            "a move out of a place behind a reference or an index: copy, clone or swap the value instead (`std::mem::take`, `.clone()`)".into(),
        );
    }

    fn loans_carried(&self, l: LocalId) -> BTreeSet<u32> {
        self.st.loans_of.get(&l).cloned().unwrap_or_default()
    }

    /// Live loans on local `target` held by live locals other than `except`.
    fn conflicting(&self, target: LocalId, path: &str, pos: u32, want_mut_only: bool, except: Option<LocalId>) -> Option<(LocalId, u32)> {
        if !self.targeted.contains(&target) {
            return None;
        }
        for (holder, ls) in &self.st.loans_of {
            if Some(*holder) == except {
                continue;
            }
            if !self.live_after(*holder, pos) {
                continue;
            }
            for lid in ls {
                let ln = &self.loans[*lid as usize];
                if ln.target == Some(target) && (!want_mut_only || ln.mutable) && overlaps(&ln.path, path) {
                    return Some((*holder, *lid));
                }
            }
        }
        for (ls, reserved) in &self.pending {
            for lid in ls {
                let ln = &self.loans[*lid as usize];
                if ln.target == Some(target) && (!want_mut_only || ln.mutable) && overlaps(&ln.path, path) {
                    if *reserved && want_mut_only {
                        continue;
                    }
                    return Some((PENDING, *lid));
                }
            }
        }
        // a `for` loop's iterator is live for the whole loop (a hidden local in Rust's desugaring)
        for ls in &self.loop_iters {
            for lid in ls {
                let ln = &self.loans[*lid as usize];
                if ln.target == Some(target) && (!want_mut_only || ln.mutable) && overlaps(&ln.path, path) {
                    return Some((ITER, *lid));
                }
            }
        }
        None
    }

    // ------------------------------------------------------------ expressions
    /// Returns the set of loans the expression's value carries (only Local values carry any).
    fn eval(&mut self, e: &TExpr, u: Use) -> BTreeSet<u32> {
        let r = self.eval_inner(e, u);
        if r.is_empty() || is_local(self.c, &e.ty) || matches!(e.ty, Ty::Never | Ty::Error) {
            r
        } else {
            BTreeSet::new()
        }
    }

    fn eval_inner(&mut self, e: &TExpr, u: Use) -> BTreeSet<u32> {
        let place = matches!(e.kind, TK::Field(..) | TK::Index(..) | TK::SliceRange { .. } | TK::Deref(_) | TK::Local(_));
        let saved = self.base_depth;
        if !place {
            self.base_depth = 0;
        }
        let r = self.eval_kind(e, u);
        self.base_depth = saved;
        r
    }

    fn eval_kind(&mut self, e: &TExpr, u: Use) -> BTreeSet<u32> {
        if self.st.dead {
            return BTreeSet::new();
        }
        match &e.kind {
            TK::Local(l) => {
                let l = *l;
                let ms = *self.st.ms.get(&l).unwrap_or(&MS::Init);
                let ty = self.body.locals[l as usize].ty.clone();
                let copy = self.is_copy(&ty);
                if ms != MS::Init && (u != Use::Write) {
                    let code = if self.second_pass { "E-MOVE-LOOP" } else { "E-MOVE-USED" };
                    let why = match ms {
                        MS::Uninit => "is not initialised",
                        _ => "was moved",
                    };
                    let nm = self.name(l);
                    self.err(code, e.span, format!("`{nm}` {why} here{}", if self.second_pass { " (moved in a previous iteration of the loop)" } else { "" }));
                }
                if u != Use::Write && ms == MS::Init {
                    self.check_partial(e, e.span);
                }
                let moving = u == Use::Value && !copy;
                if moving {
                    self.st.ms.insert(l, MS::Moved);
                }
                if u == Use::Write {
                    if let Some((h, _)) = self.conflicting(l, "", e.span.lo, false, Some(l)) {
                        let (a, b) = (self.name(l), self.holder(h));
                        self.err("E-BORROW-CONFLICT", e.span, format!("`{a}` is written while `{b}` holds a loan on it"));
                    }
                }
                // reading a local with live mutable loans on it conflicts; a move conflicts with
                // every live loan (access mode Move is as for a write)
                if u != Use::Write {
                    if let Some((h, _)) = self.conflicting(l, "", e.span.lo, !moving, None) {
                        let (a, b) = (self.name(l), self.holder(h));
                        let what = if moving { "moved" } else { "used" };
                        let kind = if moving { "a" } else { "a mutable" };
                        self.err("E-BORROW-CONFLICT", e.span, format!("`{a}` is {what} while `{b}` holds {kind} loan on it"));
                    }
                }
                self.loans_carried(l)
            }
            TK::Field(b, _) => {
                if u == Use::Value && !self.is_copy(&e.ty) {
                    // a move out of a field
                    match self.move_origin(e) {
                        Origin::Owned(l, path) => {
                            let bt = self.body.locals[l as usize].ty.clone();
                            if self.lin(&bt) {
                                let nm = self.name(l);
                                self.err("E-LINEAR-PARTIAL", e.span, format!("a partial move out of the Linear value `{nm}`: destructure the whole value"));
                                let _ = self.eval(b, Use::Read);
                                self.st.ms.insert(l, MS::Moved);
                                return self.loans_carried(l);
                            }
                            let ms = *self.st.ms.get(&l).unwrap_or(&MS::Init);
                            if ms != MS::Init {
                                let code = if self.second_pass { "E-MOVE-LOOP" } else { "E-MOVE-USED" };
                                let nm = self.name(l);
                                self.err(code, e.span, format!("`{nm}` was moved and is used here"));
                            } else {
                                self.check_partial(e, e.span);
                            }
                            if let Some((h, _)) = self.conflicting(l, &path, e.span.lo, false, None) {
                                let (a, bb) = (self.c.sm().snippet(e.span), self.holder(h));
                                self.err("E-BORROW-CONFLICT", e.span, format!("`{a}` is moved while `{bb}` holds a loan on it"));
                            }
                            let text = self.c.sm().snippet(e.span);
                            self.st.pmoved.entry(l).or_default().insert(path, text);
                            return self.loans_carried(l);
                        }
                        Origin::Behind => self.move_behind(e),
                        Origin::Temp => {}
                    }
                }
                if self.base_depth == 0 {
                    self.check_partial(e, e.span);
                    self.check_access(e, u);
                }
                let inner_u = if u == Use::Write { Use::Write } else { Use::Read };
                self.eval_base(b, inner_u, e.span)
            }
            TK::Index(b, i) => {
                let saved = std::mem::replace(&mut self.base_depth, 0);
                self.eval(i, Use::Value);
                self.base_depth = saved;
                if u == Use::Value && !self.is_copy(&e.ty) {
                    self.move_behind(e);
                }
                if self.base_depth == 0 {
                    self.check_partial(e, e.span);
                    self.check_access(e, u);
                }
                let inner_u = if u == Use::Write { Use::Write } else { Use::Read };
                self.eval_base(b, inner_u, e.span)
            }
            TK::SliceRange { base, lo, hi, .. } => {
                let saved = std::mem::replace(&mut self.base_depth, 0);
                if let Some(x) = lo {
                    self.eval(x, Use::Value);
                }
                if let Some(x) = hi {
                    self.eval(x, Use::Value);
                }
                self.base_depth = saved;
                if self.base_depth == 0 {
                    self.check_partial(e, e.span);
                    self.check_access(e, u);
                }
                let inner_u = if u == Use::Write { Use::Write } else { Use::Read };
                self.eval_base(base, inner_u, e.span)
            }
            TK::Deref(b) => {
                if u == Use::Value && !self.is_copy(&e.ty) {
                    self.move_behind(e);
                }
                // an access to the referent (`*r` rooted at r): checked against loans on it
                if self.base_depth == 0 {
                    self.check_access(e, u);
                }
                match &b.kind {
                    // the reference itself is used shallowly: a loan on `(*r).f` does not
                    // conflict with dereferencing r
                    TK::Local(_) => self.eval_base(b, Use::Read, e.span),
                    // the unsized view of a place (`Deref(Unsize(&p))`): an access to p
                    TK::Unsize(x) if matches!(x.kind, TK::Borrow(..)) => {
                        let TK::Borrow(_, q) = &x.kind else { unreachable!() };
                        self.base_depth += 1;
                        let r = self.eval_place(q, if u == Use::Write { Use::Write } else { Use::Read }, e.span);
                        self.base_depth -= 1;
                        r
                    }
                    _ if b.is_place() => {
                        self.base_depth += 1;
                        let r = self.eval(b, Use::Read);
                        self.base_depth -= 1;
                        r
                    }
                    _ => self.eval(b, Use::Read),
                }
            }
            TK::Borrow(m, p) => {
                self.check_partial(p, e.span);
                let carried = self.eval_place(p, if *m { Use::Write } else { Use::Read }, e.span);
                // the new loan targets the place's root local; a place reached through a
                // reference r is rooted at r with a `*` path, and the reborrow also keeps the
                // loans of r (whatever r borrows stays borrowed while the reborrow lives)
                let mut out = BTreeSet::new();
                match place_root_any(p) {
                    Some(root) => {
                        let path = path_text(p);
                        if *m {
                            if let Some((h, _)) = self.conflicting(root, &path, e.span.lo, false, None) {
                                let (a, b) = (self.c.sm().snippet(p.span), self.holder(h));
                                self.err("E-BORROW-CONFLICT", e.span, format!("`&mut {a}` while `{b}` holds a loan on it"));
                            }
                        } else if let Some((h, _)) = self.conflicting(root, &path, e.span.lo, true, None) {
                            let (a, b) = (self.c.sm().snippet(p.span), self.holder(h));
                            self.err("E-BORROW-CONFLICT", e.span, format!("`&{a}` while `{b}` holds a mutable loan on it"));
                        }
                        let through = path.contains('*');
                        let id = self.new_loan(Some(root), None, path, *m, e.span);
                        out.insert(id);
                        if through {
                            out.extend(carried);
                        }
                    }
                    None => {
                        // a reborrow through a temporary reference (a call result): keeps the
                        // loans of the reference it is reached through
                        out.extend(carried);
                    }
                }
                out
            }
            TK::Unsize(b) | TK::Cast(b) => self.eval(b, if matches!(b.kind, TK::Borrow(..)) { Use::Value } else { u }),
            TK::Unary(_, a) => {
                self.eval(a, Use::Value);
                BTreeSet::new()
            }
            TK::Binary(_, a, b) => {
                self.eval(a, Use::Read);
                self.eval(b, Use::Read);
                BTreeSet::new()
            }
            TK::Assign(p, r) => {
                let ls = self.eval(r, Use::Value);
                self.assign(p, ls, e.span);
                BTreeSet::new()
            }
            TK::AssignOp(_, p, r) => {
                self.eval(r, Use::Value);
                self.eval(p, Use::Write);
                BTreeSet::new()
            }
            TK::Call { f, args, substs } => self.eval_call(*f, substs, args, e),
            TK::TraitCall { args, decl, .. } => {
                let mut all = BTreeSet::new();
                for a in args {
                    all.extend(self.eval(a, Use::Value));
                }
                let _ = decl;
                if is_local(self.c, &e.ty) {
                    all
                } else {
                    BTreeSet::new()
                }
            }
            TK::CallValue(f, args) => {
                // calling a closure: an FnOnce closure (or an FnOnce-bounded parameter) is
                // consumed; an FnMut one is used mutably
                let fk = match &f.ty {
                    Ty::Closure(cid) => self.c.closures.get(*cid as usize).map(|c| c.fn_kind).unwrap_or(0),
                    Ty::Param(i) => self.gen_fn_kinds.get(*i as usize).copied().flatten().unwrap_or(0),
                    _ => 0,
                };
                if fk == 1 {
                    if let TK::Local(l) = f.kind {
                        if let Some((h, _)) = self.conflicting(l, "", f.span.lo, false, Some(l)) {
                            let (a, b) = (self.name(l), self.holder(h));
                            self.err("E-BORROW-CONFLICT", f.span, format!("the FnMut `{a}` is called while `{b}` holds a loan on it"));
                        }
                    }
                }
                let carried = self.eval(f, if fk == 2 { Use::Value } else { Use::Read });
                let mut arg_loans = BTreeSet::new();
                let mut per_arg: Vec<BTreeSet<u32>> = vec![];
                for a in args {
                    let ls = self.eval(a, Use::Value);
                    arg_loans.extend(ls.iter().copied());
                    per_arg.push(ls);
                }
                // T-CallClo (F-61): a by-mut captured place of Local type may receive what the
                // body can store into it: the arguments' loans and the closure's own loans
                // (its by-ref captures and what its by-move captures carry). The loans of
                // arguments at higher-ranked parameters are not transferred: the body may not
                // store them (F-107; such a store is E-LOCAL-MUT-STORE in the body)
                if let Ty::Closure(cid) = f.ty.strip_refs() {
                    let hr = self.hr_params.get(cid).cloned().unwrap_or_default();
                    let mut other: BTreeSet<u32> = BTreeSet::new();
                    for (i, ls) in per_arg.iter().enumerate() {
                        if !hr.contains(&i) {
                            other.extend(ls.iter().copied());
                        }
                    }
                    let mut value: BTreeSet<u32> = carried.clone();
                    let holder = place_root(f);
                    if let Some(fl) = holder {
                        value.extend(self.loans_carried(fl));
                    }
                    self.closure_transfer(*cid, &other, &value, holder, e.span);
                }
                // a Local result carries the closure's capture loans and the arguments' (F-40)
                if is_local(self.c, &e.ty) {
                    carried.union(&arg_loans).copied().collect()
                } else {
                    BTreeSet::new()
                }
            }
            TK::Closure(cid) => {
                let cd = &self.c.closures[*cid as usize];
                let mut out = BTreeSet::new();
                let caps = cd.captures.clone();
                for cap in caps {
                    match cap.mode {
                        CaptureMode::Move => {
                            let le = TExpr::new(TK::Local(cap.local), cap.ty.clone(), e.span);
                            out.extend(self.eval(&le, Use::Value));
                        }
                        CaptureMode::Ref | CaptureMode::Mut => {
                            let m = cap.mode == CaptureMode::Mut;
                            if let Some((h, _)) = self.conflicting(cap.local, "", e.span.lo, !m, None) {
                                let (a, b) = (self.name(cap.local), self.holder(h));
                                self.err("E-BORROW-CONFLICT", e.span, format!("a closure borrows `{a}` while `{b}` holds a conflicting loan"));
                            }
                            let id = self.new_loan(Some(cap.local), None, String::new(), m, e.span);
                            out.insert(id);
                            // loans the captured value itself carries
                            out.extend(self.loans_carried(cap.local));
                        }
                    }
                }
                // the closure body: moves and linear checks inside it
                let _ = self.check_closure_body(*cid);
                out
            }
            TK::FnRef(..) | TK::Lit(_) | TK::Const(_) | TK::Error => BTreeSet::new(),
            TK::Ctor { fields, .. } | TK::Tuple(fields) | TK::Array(fields) => {
                // the components' loans are live until the aggregate is built, like a call's
                // arguments: `(&mut x, &x)` conflicts (F-84)
                let mut out = BTreeSet::new();
                let base = self.pending.len();
                for f in fields {
                    let ls = self.eval(f, Use::Value);
                    self.pending.push((ls.clone(), false));
                    out.extend(ls);
                }
                self.pending.truncate(base);
                out
            }
            TK::CtorUpdate { fields, base, .. } => {
                let mut out = BTreeSet::new();
                for (_, f) in fields {
                    out.extend(self.eval(f, Use::Value));
                }
                out.extend(self.eval(base, Use::Value));
                out
            }
            TK::Repeat(x, _) => self.eval(x, Use::Value),
            TK::Block(stmts, tail) => self.eval_block(stmts, tail.as_deref(), e),
            TK::If(c, t, el) => {
                // `if let p = s`: the scrutinee is moved and p bound only on the then-path, and
                // p's bindings are scoped to it (review 2026-10-16: a Linear payload bound in
                // the then-branch was checked on the else-path too)
                if let TK::LetCond(p, s) = &c.kind {
                    let sl = self.eval(s, Use::Read);
                    let moves = pat_moves(self.c, p, &self.copy_params) && !self.is_copy(&s.ty);
                    // a Linear scrutinee whose other variants carry no Linear value is consumed
                    // on both paths (`if let Some(t) = o`: in the else-branch o is None)
                    let lin = self.lin(&s.ty);
                    let others_linear = match &p.kind {
                        PK::Variant { variant, .. } => self.linear_variants(&s.ty).iter().any(|v| v != variant),
                        _ => true,
                    };
                    if lin && (moves || !is_place_expr(s)) && self.pat_drops_linear(p) {
                        self.err("E-LINEAR-DROP", p.span, "this pattern discards a Linear value: bind it by value and consume it (§5.8)".into());
                    }
                    if lin && moves && !others_linear {
                        self.move_by_pattern(s);
                    }
                    if lin && !is_place_expr(s) && others_linear {
                        self.err("E-LINEAR-DROP", c.span, "the value of this `if let` is dropped when the pattern does not match, and it may hold a Linear value".into());
                    }
                    let s0 = self.st.clone();
                    self.scopes.push(vec![]);
                    if moves && !(lin && !others_linear) {
                        self.move_by_pattern(s);
                    }
                    self.bind_pat_from(p, sl, Some(s));
                    let l1 = self.eval(t, u);
                    let scope = self.scopes.pop().unwrap_or_default();
                    if !self.st.dead {
                        self.end_scope(&scope, t.span, &l1);
                    }
                    for b in &scope {
                        self.st.ms.remove(b);
                        self.st.loans_of.remove(b);
                    }
                    let s1 = std::mem::replace(&mut self.st, s0);
                    let l2 = match el {
                        Some(x) => self.eval(x, u),
                        None => BTreeSet::new(),
                    };
                    let s2 = std::mem::replace(&mut self.st, s1.clone());
                    self.join(s1, s2, e.span);
                    return l1.union(&l2).cloned().collect();
                }
                self.eval(c, Use::Read);
                let s0 = self.st.clone();
                let l1 = self.eval(t, u);
                let s1 = std::mem::replace(&mut self.st, s0);
                let l2 = match el {
                    Some(x) => self.eval(x, u),
                    None => BTreeSet::new(),
                };
                let s2 = std::mem::replace(&mut self.st, s1.clone());
                self.join(s1, s2, e.span);
                l1.union(&l2).cloned().collect()
            }
            TK::Match(s, arms) => {
                let sl = self.eval(s, Use::Read);
                // a by-value binding of a non-Copy part moves the scrutinee
                let moves = arms.iter().any(|a| pat_moves(self.c, &a.pat, &self.copy_params));
                if moves && !self.is_copy(&s.ty) {
                    self.move_by_pattern(s);
                }
                if self.lin(&s.ty) && (moves || !is_place_expr(s)) {
                    self.check_linear_arms(&s.ty, arms);
                }
                let s0 = self.st.clone();
                let mut outs: Vec<St> = vec![];
                let mut ls = BTreeSet::new();
                for a in arms {
                    self.st = s0.clone();
                    // an arm's bindings exist in that arm only: scoped to it, and gone at the join
                    self.scopes.push(vec![]);
                    self.bind_pat_from(&a.pat, sl.clone(), Some(s));
                    if let Some(g) = &a.guard {
                        self.eval(g, Use::Read);
                    }
                    let al = self.eval(&a.body, u);
                    let scope = self.scopes.pop().unwrap_or_default();
                    if !self.st.dead {
                        self.end_scope(&scope, a.body.span, &al);
                    }
                    for b in &scope {
                        self.st.ms.remove(b);
                        self.st.loans_of.remove(b);
                    }
                    ls.extend(al);
                    outs.push(self.st.clone());
                }
                if outs.is_empty() {
                    self.st = s0;
                    self.st.dead = true;
                    return ls;
                }
                let mut acc = outs.remove(0);
                for o in outs {
                    self.join(acc.clone(), o, e.span);
                    acc = self.st.clone();
                }
                self.st = acc;
                ls
            }
            TK::Loop(id, b) => self.eval_loop(*id, b, None, None, true, e.span),
            TK::While(id, c, b) => self.eval_loop(*id, b, Some(c), None, false, e.span),
            TK::For { id, pat, iter, body, .. } => {
                let il = self.eval(iter, Use::Value);
                self.eval_loop(*id, body, None, Some((pat, il)), false, e.span);
                BTreeSet::new()
            }
            TK::Break(id, v) => {
                let vl = match v {
                    Some(v) => self.eval(v, Use::Value),
                    None => BTreeSet::new(),
                };
                if self.st.dead {
                    return BTreeSet::new();
                }
                self.check_exit_linear(Some(*id), e.span);
                self.check_jump_outlive(*id, true, &vl, e.span);
                let st = self.st.clone();
                if let Some(fr) = self.jumps.iter_mut().rev().find(|f| f.0 == *id) {
                    fr.1.push(st);
                    fr.3.extend(vl);
                }
                self.st.dead = true;
                BTreeSet::new()
            }
            TK::Continue(id) => {
                if self.st.dead {
                    return BTreeSet::new();
                }
                self.check_exit_linear(Some(*id), e.span);
                self.check_jump_outlive(*id, false, &BTreeSet::new(), e.span);
                let st = self.st.clone();
                if let Some(fr) = self.jumps.iter_mut().rev().find(|f| f.0 == *id) {
                    fr.2.push(st);
                }
                self.st.dead = true;
                BTreeSet::new()
            }
            TK::Return(v) => {
                let ls = match v {
                    Some(v) => self.eval(v, Use::Value),
                    None => BTreeSet::new(),
                };
                self.returned_loans.push((ls, e.span));
                self.check_exit_linear(None, e.span);
                self.st.dead = true;
                BTreeSet::new()
            }
            TK::Try { e: inner, .. } => {
                let ls = self.eval(inner, Use::Value);
                // the error path returns: linear values live here must be consumed (trap-free path)
                let saved = self.st.clone();
                self.check_exit_linear(None, e.span);
                self.st = saved;
                ls
            }
            TK::Det { body, .. } => self.eval(body, u),
            TK::Trap(..) => {
                // trap paths are exempt (section 6.3 abandons live Linear values)
                self.st.dead = true;
                BTreeSet::new()
            }
            TK::Assert { cond, .. } => {
                self.eval(cond, Use::Read);
                BTreeSet::new()
            }
            TK::AssertCmp { a, b, .. } => {
                self.eval(a, Use::Read);
                self.eval(b, Use::Read);
                BTreeSet::new()
            }
            TK::Format { args, .. } => {
                for a in args {
                    self.eval(a, Use::Read);
                }
                BTreeSet::new()
            }
            TK::Matches(s, _) => {
                self.eval(s, Use::Read);
                BTreeSet::new()
            }
            TK::LetCond(p, s) => {
                let ls = self.eval(s, Use::Read);
                if pat_moves(self.c, p, &self.copy_params) && !self.is_copy(&s.ty) {
                    self.move_by_pattern(s);
                }
                self.bind_pat_from(p, ls, Some(s));
                BTreeSet::new()
            }
        }
    }

    /// The variants of an enum type that carry a Linear field.
    fn linear_variants(&self, t: &Ty) -> BTreeSet<u32> {
        let mut out = BTreeSet::new();
        if let Ty::Adt(a, xs) = t {
            let ad = &self.c.program.adts[*a as usize];
            for (vi, v) in ad.variants.iter().enumerate() {
                if v.fields.iter().any(|f| self.lin(&f.ty.subst(xs))) {
                    out.insert(vi as u32);
                }
            }
        }
        out
    }

    /// Does a by-value pattern on a Linear value discard a Linear component: a `_`, a `ref`
    /// binding (the value stays in the consumed scrutinee), or a variant field left out?
    fn pat_drops_linear(&self, p: &TPat) -> bool {
        match &p.kind {
            PK::Wild => self.lin(&p.ty),
            PK::Bind { by_ref: None, .. } => false,
            PK::Bind { by_ref: Some(_), .. } => self.lin(&p.ty),
            PK::Tuple(ps) | PK::Or(ps) | PK::Slice(ps, _) => ps.iter().any(|x| self.pat_drops_linear(x)),
            PK::Variant { adt, variant, fields } => {
                if fields.iter().any(|(_, x)| self.pat_drops_linear(x)) {
                    return true;
                }
                let xs = match &p.ty {
                    Ty::Adt(_, xs) => xs.clone(),
                    _ => vec![],
                };
                let ad = &self.c.program.adts[*adt as usize];
                match ad.variants.get(*variant as usize) {
                    Some(v) => v.fields.iter().enumerate().any(|(i, f)| !fields.iter().any(|(fi, _)| *fi as usize == i) && self.lin(&f.ty.subst(&xs))),
                    None => false,
                }
            }
            _ => false,
        }
    }

    /// The arms of a match that consumes a Linear scrutinee must each consume its Linear payload
    /// (§5.8): an arm binding nothing of it (`Some(_)`, or `_` over variants that carry one)
    /// drops it (review 2026-10-16).
    fn check_linear_arms(&mut self, scrut_ty: &Ty, arms: &[TArm]) {
        let lv = self.linear_variants(scrut_ty);
        // a Linear struct itself (not only its fields), or a non-ADT Linear value (a tuple)
        let whole = match scrut_ty {
            Ty::Adt(a, _) => self.c.program.adts[*a as usize].linear,
            t => self.lin(t),
        };
        let mut covered: BTreeSet<u32> = BTreeSet::new();
        for a in arms {
            let drops = match &a.pat.kind {
                PK::Wild => whole || lv.iter().any(|v| !covered.contains(v)),
                PK::Bind { by_ref: None, .. } => false,
                _ => self.pat_drops_linear(&a.pat),
            };
            if drops {
                self.err("E-LINEAR-DROP", a.pat.span, "this arm discards a Linear value: bind it by value and consume it (§5.8)".into());
            }
            if a.guard.is_none() {
                if let PK::Variant { variant, .. } = &a.pat.kind {
                    covered.insert(*variant);
                }
            }
        }
    }

    /// A by-value binding of a non-Copy part of the scrutinee moves (part of) it.
    fn move_by_pattern(&mut self, s: &TExpr) {
        match self.move_origin(s) {
            Origin::Owned(l, path) => {
                if path.is_empty() || self.lin(&self.body.locals[l as usize].ty.clone()) {
                    self.st.ms.insert(l, MS::Moved);
                } else {
                    let text = self.c.sm().snippet(s.span);
                    self.st.pmoved.entry(l).or_default().insert(path, text);
                }
            }
            Origin::Behind => self.move_behind(s),
            Origin::Temp => {}
        }
    }

    /// Conflicts of an access to a whole place rooted in a local, directly or through a reference
    /// (its field, index and `*` path).
    fn check_access(&mut self, p: &TExpr, u: Use) {
        let Some(root) = place_root_any(p) else { return };
        let path = path_text(p);
        let sp = p.span;
        if u == Use::Write {
            if let Some((h, _)) = self.conflicting(root, &path, sp.lo, false, None) {
                let (a, b) = (self.c.sm().snippet(sp), self.holder(h));
                self.err("E-BORROW-CONFLICT", sp, format!("`{a}` is written while `{b}` holds a loan on it"));
            }
        } else if let Some((h, _)) = self.conflicting(root, &path, sp.lo, true, None) {
            let (a, b) = (self.c.sm().snippet(sp), self.holder(h));
            self.err("E-BORROW-CONFLICT", sp, format!("`{a}` is read while `{b}` holds a mutable loan on it"));
        }
    }

    /// The base of a field, index or slice place: a local base is checked for initialisation
    /// only; conflicts are decided on the whole place by `check_access`.
    fn eval_base(&mut self, b: &TExpr, u: Use, sp: Span) -> BTreeSet<u32> {
        match &b.kind {
            TK::Local(l) => {
                let l = *l;
                let ms = *self.st.ms.get(&l).unwrap_or(&MS::Init);
                if ms != MS::Init && u != Use::Write {
                    let code = if self.second_pass { "E-MOVE-LOOP" } else { "E-MOVE-USED" };
                    let nm = self.name(l);
                    self.err(code, sp, format!("`{nm}` was moved and is used here"));
                }
                self.loans_carried(l)
            }
            _ => self.eval_place(b, u, sp),
        }
    }

    fn eval_place(&mut self, b: &TExpr, u: Use, sp: Span) -> BTreeSet<u32> {
        // a place base: Local roots are accessed (not moved)
        match &b.kind {
            TK::Local(l) => {
                let l = *l;
                let ms = *self.st.ms.get(&l).unwrap_or(&MS::Init);
                if ms != MS::Init && u != Use::Write {
                    let code = if self.second_pass { "E-MOVE-LOOP" } else { "E-MOVE-USED" };
                    let nm = self.name(l);
                    self.err(code, sp, format!("`{nm}` was moved and is used here"));
                }
                if u == Use::Write {
                    if let Some((h, _)) = self.conflicting(l, "", sp.lo, false, None) {
                        let (a, bb) = (self.name(l), self.holder(h));
                        self.err("E-BORROW-CONFLICT", sp, format!("`{a}` is written while `{bb}` holds a loan on it"));
                    }
                } else if let Some((h, _)) = self.conflicting(l, "", sp.lo, true, None) {
                    let (a, bb) = (self.name(l), self.holder(h));
                    self.err("E-BORROW-CONFLICT", sp, format!("`{a}` is read while `{bb}` holds a mutable loan on it"));
                }
                self.loans_carried(l)
            }
            _ => {
                // unfiltered: the loans of the reference a place is reached through, whatever the
                // place's own type
                self.base_depth += 1;
                let r = self.eval_inner(b, if u == Use::Write { Use::Write } else { Use::Read });
                self.base_depth -= 1;
                r
            }
        }
    }

    /// Inside a closure body: a value stored into a by-mut captured place or into the closure's
    /// by-move state may not carry a loan on a body local, on a by-mut captured place or on the
    /// state, nor a higher-ranked parameter's loan (§5.7 "Stores into captures", "By-move state
    /// stores", F-61, F-93; review 2026-10-23, N-79). Checked at the store, the first failure.
    fn check_capture_store(&mut self, q: LocalId, stored: &BTreeSet<u32>, sp: Span) {
        let Some(&cid) = self.clo_stack.last() else { return };
        let cd = &self.c.closures[cid as usize];
        let Some(cap) = cd.captures.iter().find(|c| c.local == q) else { return };
        if cap.mode == CaptureMode::Ref {
            return;
        }
        let mut bad: Option<String> = None;
        for x in stored {
            if self.hr_loans.contains(x) {
                bad = Some("a borrow received through a higher-ranked parameter".into());
                break;
            }
            let ln = &self.loans[*x as usize];
            let Some(t) = ln.target else { continue };
            if ln.path.starts_with('*') && self.body.locals[t as usize].ty.is_ref() {
                continue;
            }
            let internal = self.body.locals[t as usize].closure == Some(cid);
            let own_place = cd.captures.iter().any(|c| c.local == t && c.mode != CaptureMode::Ref);
            if internal || own_place {
                bad = Some(format!("a borrow of `{}`, {}", self.name(t), if internal { "a local of the closure body" } else { "a place the closure captures by mut or owns" }));
                break;
            }
        }
        if let Some(why) = bad {
            let (nm, what) = (self.name(q), if cap.mode == CaptureMode::Move { "the closure's own (by-move) state" } else { "a place the closure captures by mut" });
            self.err("E-LOCAL-MUT-STORE", sp, format!("storing {why} into `{nm}`, {what}: it would outlive the call (§5.7, F-61, F-93; rustc rejects it too)"));
        }
    }

    fn assign(&mut self, p: &TExpr, ls: BTreeSet<u32>, sp: Span) {
        if let Some(r) = place_root_direct(p) {
            self.check_capture_store(r, &ls, sp);
        }
        match &p.kind {
            TK::Local(l) => {
                let l = *l;
                let ms = *self.st.ms.get(&l).unwrap_or(&MS::Init);
                let ty = self.body.locals[l as usize].ty.clone();
                if self.lin(&ty) && ms == MS::Init {
                    let nm = self.name(l);
                    self.err("E-LINEAR-DROP", sp, format!("assigning over the initialised Linear value `{nm}` drops it"));
                }
                if let Some((h, _)) = self.conflicting(l, "", sp.lo, false, Some(l)) {
                    let (a, b) = (self.name(l), self.holder(h));
                    self.err("E-BORROW-CONFLICT", sp, format!("`{a}` is assigned while `{b}` holds a loan on it"));
                }
                self.st.ms.insert(l, MS::Init);
                self.st.pmoved.remove(&l);
                self.st.loans_of.insert(l, ls);
                self.sym_base.remove(&l);
            }
            _ => {
                // assigning a moved field path (or a parent of it) initialises it again
                if let Some(l) = place_root_direct(p) {
                    let path = path_text(p);
                    if let Some(set) = self.st.pmoved.get_mut(&l) {
                        set.retain(|m, _| !is_prefix_path(&path, m));
                    }
                }
                let carried = self.eval(p, Use::Write);
                if self.lin(&p.ty) {
                    self.err("E-LINEAR-DROP", sp, "assigning over an initialised Linear place drops the old value".into());
                }
                // E-LOCAL-MUT-STORE through a reference into the caller's memory, else the
                // stored loans join the written referents
                let through = deref_chain(p);
                let what = self.c.sm().snippet(p.span);
                let dpos = self.place_pos(p);
                self.store_into_at(place_root(p), through, &carried, &ls, sp, &what, dpos);
            }
        }
    }

    /// A value carrying the loans `stored` is stored into a place reached through a reference
    /// carrying `dst_loans` (T-Assign, storing std calls; §5.4). If that reference points into
    /// the caller's memory (it carries the symbolic loan of a parameter j: a reference parameter,
    /// a reborrow of one, or a reference bound out of a by-value parameter such as
    /// `Option<&mut T>`, F-62), the stored value may carry only j's own symbolic loans
    /// (E-LOCAL-MUT-STORE), at the destination's reference position when that is known
    /// (`store_into_at`), otherwise at any of j's positions. Otherwise the loans join every
    /// referent the reference borrows mutably, and the root.
    fn store_into(&mut self, dst_root: Option<LocalId>, through: bool, dst_loans: &BTreeSet<u32>, stored: &BTreeSet<u32>, sp: Span, what: &str) {
        self.store_into_at(dst_root, through, dst_loans, stored, sp, what, None)
    }

    /// As `store_into`, with the destination's parameter and reference position when known
    /// (`place_pos`): a stored symbolic loan of that parameter must then be at a position on the
    /// destination's own path (the destination's position or one inside it, or a reference it
    /// is reached through), not a sibling position (F-62, item e2 of the 2026-10-23 review).
    #[allow(clippy::too_many_arguments)]
    fn store_into_at(&mut self, dst_root: Option<LocalId>, through: bool, dst_loans: &BTreeSet<u32>, stored: &BTreeSet<u32>, sp: Span, what: &str, dpos: Option<(LocalId, String)>) {
        if stored.is_empty() {
            return;
        }
        if let Some(r) = dst_root {
            if !self.body.locals[r as usize].ty.is_ref() {
                self.check_capture_store(r, stored, sp);
            }
        }
        let mut params: BTreeSet<LocalId> = BTreeSet::new();
        if through {
            for x in dst_loans {
                if let Some(j) = self.loans[*x as usize].param {
                    params.insert(j);
                }
            }
            if let Some(r) = dst_root {
                if self.body.locals[r as usize].param.is_some() && self.body.locals[r as usize].ty.is_ref() {
                    params.insert(r);
                }
            }
        }
        if !params.is_empty() {
            let foreign: Vec<u32> = stored
                .iter()
                .copied()
                .filter(|x| {
                    let ln = &self.loans[*x as usize];
                    let own = match (&dpos, ln.param, ln.target) {
                        // the destination's own position: the same parameter, on its path
                        (Some((j, dp)), Some(lj), None) if params.contains(j) => lj == *j && (ln.pos.starts_with(dp.as_str()) || dp.starts_with(ln.pos.as_str())),
                        _ => ln.param.map(|j| params.contains(&j)).unwrap_or(false),
                    };
                    // a reborrow through a reference is judged by the loans carried with it
                    let transparent = ln.target.is_some() && ln.path.starts_with('*');
                    !own && !transparent
                })
                .collect();
            if !foreign.is_empty() {
                let names: Vec<String> = params.iter().map(|j| format!("`{}`", self.name(*j))).collect();
                self.err("E-LOCAL-MUT-STORE", sp, format!("storing a borrow into `{what}`, a Local place in the caller's memory (reached through {}): the stored value borrows something other than what the caller lent through it (rustc rejects it too)", names.join(", ")));
            }
            return;
        }
        let targets: Vec<LocalId> = dst_loans.iter().filter(|x| self.loans[**x as usize].mutable).filter_map(|x| self.loans[*x as usize].target).collect();
        for t in targets {
            self.st.loans_of.entry(t).or_default().extend(stored.iter().copied());
        }
        if let Some(r) = dst_root {
            self.st.loans_of.entry(r).or_default().extend(stored.iter().copied());
        }
    }

    /// An argument passed where the parameter is declared `&mut _`: a `&mut` local is implicitly
    /// reborrowed (`&mut *r`), as Rust does at this coercion site, not moved. The coercion may
    /// also unsize it (`&mut [u32; 4]` passed for `&mut [u32]`: review 2026-10-23, d3).
    fn arg_value(&mut self, a: &TExpr) -> BTreeSet<u32> {
        let inner = match &a.kind {
            TK::Unsize(x) => x.as_ref(),
            _ => a,
        };
        let TK::Local(r) = inner.kind else { return self.eval(a, Use::Value) };
        if !matches!(self.body.locals[r as usize].ty, Ty::Ref(true, _)) {
            return self.eval(a, Use::Value);
        }
        let ms = *self.st.ms.get(&r).unwrap_or(&MS::Init);
        if ms != MS::Init {
            let code = if self.second_pass { "E-MOVE-LOOP" } else { "E-MOVE-USED" };
            let nm = self.name(r);
            self.err(code, a.span, format!("`{nm}` was moved and is used here"));
        }
        if let Some((h, _)) = self.conflicting(r, "*", a.span.lo, false, None) {
            let (x, b) = (self.name(r), self.holder(h));
            self.err("E-BORROW-CONFLICT", a.span, format!("`{x}` is reborrowed mutably while `{b}` holds a loan on its referent"));
        }
        let mut out = self.loans_carried(r);
        out.insert(self.new_loan(Some(r), None, "*".into(), true, a.span));
        out
    }

    fn eval_call(&mut self, f: FnId, substs: &[Ty], args: &[TExpr], e: &TExpr) -> BTreeSet<u32> {
        let r = self.eval_call_inner(f, substs, args, e);
        if std::env::var_os("MITHI_OWN_DEBUG").is_some() {
            let cf = &self.c.program.fns[f as usize];
            eprintln!("own: call {} ({:?}, local result {}) -> {} loans; args {:?}", cf.path, cf.role, is_local(self.c, &e.ty), r.len(), args.iter().map(|a| format!("{:?}", std::mem::discriminant(&a.kind))).collect::<Vec<_>>());
        }
        r
    }

    fn eval_call_inner(&mut self, f: FnId, _substs: &[Ty], args: &[TExpr], e: &TExpr) -> BTreeSet<u32> {
        let cf = &self.c.program.fns[f as usize];
        let builtin = cf.builtin.clone();
        let two_phase = cf.self_mode.is_some();
        let mut arg_loans = vec![];
        let base = self.pending.len();
        for (i, a) in args.iter().enumerate() {
            let declared_mut_ref = matches!(cf.params.get(i).map(|p| &p.ty), Some(Ty::Ref(true, _)));
            let ls = if declared_mut_ref { self.arg_value(a) } else { self.eval(a, Use::Value) };
            // the loans an argument passes stay live until the call (Rust: two-phase borrows
            // for a method's receiver)
            self.pending.push((ls.clone(), i == 0 && two_phase));
            arg_loans.push(ls);
        }
        self.pending.truncate(base);
        // T-Call (F-35, F-61): a call whose argument type mentions clo⟨κ⟩ (directly, through
        // &F or &mut F, or a std adapter that stores it) may run κ, so κ's loan transfer λ_q into
        // its by-mut captures applies here too, with the call's arguments for κ's parameters
        // (review 2026-10-23: only a direct call `c()` transferred, so a closure passed to
        // `for_each`, `Option::map` or a user `run<F: FnMut()>` stored a dangling loan)
        let mut clos: BTreeSet<ClosureId> = BTreeSet::new();
        for a in args {
            a.ty.walk(&mut |t| {
                if let Ty::Closure(cid) = t {
                    clos.insert(*cid);
                }
            });
        }
        if !clos.is_empty() {
            // the closure arguments' own loans are the closure value's, not values the call
            // hands to the closure (F-99: `v.iter().for_each(|x| out = x)` would otherwise give
            // out a loan on itself)
            let mut other: BTreeSet<u32> = BTreeSet::new();
            let mut values: Vec<(BTreeSet<u32>, Option<LocalId>, BTreeSet<ClosureId>)> = vec![];
            for (i, a) in args.iter().enumerate() {
                let mut ls: BTreeSet<u32> = arg_loans[i].clone();
                ls.extend(self.content_loans(a));
                let holder = place_root(a).filter(|_| !matches!(a.kind, TK::Closure(_)));
                if let Some(l) = holder {
                    if !self.body.locals[l as usize].ty.is_ref() {
                        ls.extend(self.loans_carried(l));
                    }
                }
                let mut mine: BTreeSet<ClosureId> = BTreeSet::new();
                a.ty.walk(&mut |t| {
                    if let Ty::Closure(cid) = t {
                        mine.insert(*cid);
                    }
                });
                if mine.is_empty() {
                    other.extend(ls);
                } else {
                    values.push((ls, holder, mine));
                }
            }
            for (value, holder, mine) in values {
                for cid in mine {
                    self.closure_transfer(cid, &other, &value, holder, e.span);
                }
            }
        }
        let cf = &self.c.program.fns[f as usize];
        // K-CloCopy (F-104): a closure is Clone iff no capture is by mut and every by-move
        // capture is Clone (the type checker admits `.clone()` on any closure; captures are
        // known here)
        if builtin.as_deref() == Some("clone") {
            if let Some(Ty::Closure(cid)) = args.first().map(|a| a.ty.strip_refs().clone()) {
                let cd = &self.c.closures[cid as usize];
                let bad = cd.captures.iter().find(|cp| cp.mode == CaptureMode::Mut || (cp.mode == CaptureMode::Move && !clone_ty(self.c, &cp.ty, &self.copy_params)));
                if let Some(cp) = bad {
                    let nm = self.name(cp.local);
                    let why = if cp.mode == CaptureMode::Mut { "captures it by mut" } else { "owns a value that is not Clone" };
                    self.err("E-TYPE", e.span, format!("this closure is not Clone: it {why} (`{nm}`; K-CloCopy, F-104)"));
                }
            }
        }
        // std storing calls: the stored value's loans join the receiving referent (F-39), or are
        // E-LOCAL-MUT-STORE when the receiver is the caller's memory
        match builtin.as_deref() {
            Some("vec_push") | Some("vec_insert") | Some("opt_insert") | Some("slice_fill") | Some("vec_resize") | Some("vec_extend_from_slice") => {
                if let (Some(dst), Some(v)) = (args.first(), arg_loans.last()) {
                    let mut stored = v.clone();
                    if builtin.as_deref() == Some("vec_extend_from_slice") {
                        // the elements stored are copies of the slice's elements: the loans its
                        // referent carries, not the slice's own borrow of it
                        stored = match args.last().and_then(place_root) {
                            Some(r) if !self.body.locals[r as usize].ty.is_ref() => self.loans_carried(r),
                            _ => v.clone(),
                        };
                    }
                    let what = self.c.sm().snippet(dst.span);
                    let dl = arg_loans[0].clone();
                    // the stored value lands in an element of the receiver (or the payload)
                    let sfx = if builtin.as_deref() == Some("opt_insert") { "<0>" } else { "[]" };
                    let dpos = self.place_pos(dst).map(|(j, s)| (j, format!("{s}{sfx}")));
                    self.store_into_at(place_root(dst), true, &dl, &stored, e.span, &what, dpos);
                }
            }
            Some("mem_swap") => {
                if args.len() == 2 {
                    // each side's content: the loans its place carries, or, for a reference that
                    // is not a borrow of a local's place (`o.as_mut().unwrap()`), every loan the
                    // argument carries (review 2026-10-23: such a swap moved no loan, once typeck
                    // stopped dereferencing `&mut r` to `&mut *r`; probe br/b12)
                    let roots = [place_root(&args[0]), place_root(&args[1])];
                    let content: Vec<BTreeSet<u32>> = (0..2)
                        .map(|i| match (roots[i], &args[i].kind) {
                            (Some(r), TK::Borrow(..)) if !self.body.locals[r as usize].ty.is_ref() => self.loans_carried(r),
                            _ => arg_loans[i].clone(),
                        })
                        .collect();
                    for i in 0..2 {
                        let other = content[1 - i].clone();
                        let d = arg_loans[i].clone();
                        let w = self.c.sm().snippet(args[i].span);
                        match (roots[i], &args[i].kind) {
                            (Some(r), TK::Borrow(..)) if !self.body.locals[r as usize].ty.is_ref() => {
                                if d.iter().any(|x| self.loans[*x as usize].param.is_some()) {
                                    self.store_into(Some(r), true, &d, &other, e.span, &w);
                                } else {
                                    self.st.loans_of.insert(r, other);
                                }
                            }
                            // through a reference: into whatever it borrows mutably
                            _ => self.store_into(roots[i], true, &d, &other, e.span, &w),
                        }
                    }
                }
            }
            Some("mem_replace") => {
                if let (Some(dst), Some(v)) = (args.first(), arg_loans.get(1)) {
                    if let Some(root) = place_root(dst) {
                        let old = self.loans_carried(root);
                        let v = v.clone();
                        let d0 = arg_loans[0].clone();
                        if d0.iter().any(|x| self.loans[*x as usize].param.is_some()) {
                            let w = self.c.sm().snippet(dst.span);
                            self.store_into(Some(root), true, &d0, &v, e.span, &w);
                        } else {
                            self.st.loans_of.insert(root, v);
                        }
                        if is_local(self.c, &e.ty) {
                            return old;
                        }
                    }
                }
            }
            _ => {}
        }
        // closure result discipline (F-40): a closure instantiated at a Fn-bounded parameter whose
        // bound declares a Local result may return only loans on its own parameters
        if cf.role != FileRole::Std {
            for (i, a) in args.iter().enumerate() {
                let cid = match &a.kind {
                    TK::Closure(c) => Some(*c),
                    TK::Borrow(_, inner) => match &inner.kind {
                        TK::Closure(c) => Some(*c),
                        _ => None,
                    },
                    _ => None,
                };
                let Some(cid) = cid else { continue };
                let gi = match cf.params.get(i).map(|p| &p.ty) {
                    Some(Ty::Param(g)) => Some(*g),
                    Some(Ty::Ref(_, inner)) => {
                        if let Ty::Param(g) = **inner {
                            Some(g)
                        } else {
                            None
                        }
                    }
                    _ => None,
                };
                let local_ret = gi.and_then(|g| crate::lower::fn_bound(&cf.generics[g as usize])).map(|(_, _, r)| r.mentions_ref()).unwrap_or(false);
                if local_ret {
                    let res = self.closure_results.get(&cid).cloned().unwrap_or_default();
                    if res.iter().any(|x| self.loans[*x as usize].target.is_some()) {
                        let sp = self.c.closures[cid as usize].span;
                        self.err("E-REF-ESCAPE", sp, "the closure returns a borrow of a captured value, but the parameter's bound ties its result to the closure's own argument (F-40; rustc rejects the higher-ranked signature too)".into());
                    }
                }
            }
        }
        if !is_local(self.c, &e.ty) {
            return BTreeSet::new();
        }
        // a projection: the result carries the loan of the elided parameter (receiver or the single
        // reference parameter); a std adapter: the union of its Local arguments' loans
        // (a borrowed owned place also passes the loans its value carries: `it.next()` returns a
        // reference into what `it` borrows, review 2026-10-16)
        if cf.role == FileRole::Std {
            let mut out = BTreeSet::new();
            for (i, a) in args.iter().enumerate() {
                if is_local(self.c, &a.ty) {
                    out.extend(arg_loans[i].iter().copied());
                    out.extend(self.content_loans(a));
                }
            }
            return out;
        }
        let idx = if cf.self_mode.is_some() { Some(0) } else { cf.params.iter().position(|p| p.ty.is_ref()) };
        match idx {
            Some(i) => {
                let mut out = arg_loans.get(i).cloned().unwrap_or_default();
                if let Some(a) = args.get(i) {
                    out.extend(self.content_loans(a));
                }
                out
            }
            None => BTreeSet::new(),
        }
    }

    /// T-CallClo's (and T-Call's, for a call that may run the closure) loan transfer λ_q into
    /// each by-mut captured place q of closure `cid` (F-61): what the body may store there is
    /// over-approximated by `add` (the call's arguments' loans and the closure's own loans),
    /// less loans on q itself. A capture that is a reference goes through `store_into`, so a
    /// store into a parameter's referent is E-LOCAL-MUT-STORE (§5.4; review 2026-10-23, g1);
    /// a capture that cannot hold a loan (`&mut Vec<u32>`) receives nothing.
    ///
    /// `other`: the call's argument loans that may reach the closure's parameters (not those of
    /// higher-ranked parameters). `value`: the loans the closure value carries. What the body may
    /// store (λ_q, §5.7 "Stores into captures", F-94): by-ref capture loans and what by-move
    /// captures carry; each capture's current loans in place of its capture symbol ℓ_q*; and
    /// the parameters' loans. Not the loans **on** by-mut captured places (storing one is
    /// E-LOCAL-MUT-STORE in the body): review 2026-10-23, N-84, where out1 received a loan on
    /// out2 and a later read of out2 was a false E-BORROW-CONFLICT. A closure whose body writes
    /// its by-move state gets the same loans into the value itself (λ_σ, F-93), held by
    /// `holder`.
    fn closure_transfer(&mut self, cid: ClosureId, other: &BTreeSet<u32>, value: &BTreeSet<u32>, holder: Option<LocalId>, sp: Span) {
        let Some(cd) = self.c.closures.get(cid as usize) else { return };
        let mut add: BTreeSet<u32> = other.clone();
        for x in value {
            let ln = &self.loans[*x as usize];
            let on_mut_capture = cd.captures.iter().any(|c| c.mode == CaptureMode::Mut && ln.target == Some(c.local) && !ln.path.starts_with('*'));
            if !on_mut_capture {
                add.insert(*x);
            }
        }
        for cap in &cd.captures {
            if cap.mode != CaptureMode::Move {
                add.extend(self.loans_carried(cap.local));
            }
        }
        let add = &add;
        // λ_σ: a body that stores into its by-move state keeps those loans in the closure value
        if let Some(h) = holder {
            let body = &cd.body;
            let writes_state = cd.captures.iter().any(|c| {
                c.mode == CaptureMode::Move && is_local(self.c, &c.ty) && {
                    let mut w = false;
                    walk_deep(self.c, body, &mut |x| {
                        if let TK::Assign(p, _) | TK::AssignOp(_, p, _) | TK::Borrow(true, p) = &x.kind {
                            if place_root(p) == Some(c.local) {
                                w = true;
                            }
                        }
                    });
                    w
                }
            });
            if writes_state && !self.body.locals[h as usize].ty.is_ref() {
                let add_s: Vec<u32> = add.iter().copied().filter(|x| self.loans[*x as usize].target != Some(h) && !self.hr_loans.contains(x)).collect();
                self.st.loans_of.entry(h).or_default().extend(add_s);
            }
        }
        let caps: Vec<(LocalId, Ty)> = cd.captures.iter().filter(|cp| cp.mode == CaptureMode::Mut).map(|cp| (cp.local, cp.ty.clone())).collect();
        for (q, qt) in caps {
            if !self.capture_can_store(cid, q, &qt) {
                continue;
            }
            let add_q: BTreeSet<u32> = add.iter().copied().filter(|x| self.loans[*x as usize].target != Some(q) && !self.hr_loans.contains(x)).collect();
            if add_q.is_empty() {
                continue;
            }
            if qt.is_ref() {
                let dl = self.loans_carried(q);
                let what = self.name(q);
                self.store_into(Some(q), true, &dl, &add_q, sp, &what);
            } else {
                self.st.loans_of.entry(q).or_default().extend(add_q);
            }
        }
    }

    /// Can closure `cid`'s body store a loan into its by-mut capture q? q's value is Local, or q
    /// is a reference whose referent is Local (or which the body reassigns as a whole).
    fn capture_can_store(&self, cid: ClosureId, q: LocalId, qt: &Ty) -> bool {
        match qt {
            Ty::Ref(m, inner) => {
                if *m && is_local(self.c, inner) {
                    return true;
                }
                // `out = &y` reassigns the captured reference itself
                let body = &self.c.closures[cid as usize].body;
                let mut whole = false;
                walk_deep(self.c, body, &mut |x| {
                    if let TK::Assign(p, _) = &x.kind {
                        if matches!(p.kind, TK::Local(l) if l == q) {
                            whole = true;
                        }
                    }
                });
                whole
            }
            t => is_local(self.c, t),
        }
    }

    /// For an argument `&p` or `&mut p` of an owned place p: the loans p's value carries.
    fn content_loans(&self, a: &TExpr) -> BTreeSet<u32> {
        let inner = match &a.kind {
            TK::Unsize(x) => x,
            _ => a,
        };
        match &inner.kind {
            TK::Borrow(_, p) => match place_root_direct(p) {
                Some(r) => self.loans_carried(r),
                None => BTreeSet::new(),
            },
            _ => BTreeSet::new(),
        }
    }

    fn eval_block(&mut self, stmts: &[TStmt], tail: Option<&TExpr>, e: &TExpr) -> BTreeSet<u32> {
        self.scopes.push(vec![]);
        for s in stmts {
            if self.st.dead {
                break;
            }
            match s {
                TStmt::Let { pat, init, els, span } => {
                    let ls = match init {
                        // `let _ = place;` binds nothing and moves nothing (Rust)
                        Some(i) if matches!(pat.kind, PK::Wild) && is_place_expr(i) => self.eval(i, Use::Read),
                        Some(i) => self.eval(i, Use::Value),
                        None => BTreeSet::new(),
                    };
                    if let Some(el) = els {
                        let saved = self.st.clone();
                        self.eval(el, Use::Value);
                        self.st = saved;
                    }
                    if let PK::Wild = pat.kind {
                        if let Some(i) = init {
                            if self.lin(&i.ty) && !matches!(i.kind, TK::Local(_)) {
                                self.err("E-LINEAR-DROP", *span, "`let _ = ..` drops a Linear value".into());
                            }
                        }
                    }
                    if init.is_none() {
                        let mut bs = vec![];
                        pat.bindings(&mut bs);
                        for b in bs {
                            self.st.ms.insert(b, MS::Uninit);
                            self.st.pmoved.remove(&b);
                            self.scopes.last_mut().unwrap().push(b);
                        }
                    } else {
                        self.bind_pat_from(pat, ls, init.as_ref());
                    }
                }
                TStmt::Expr(x) => {
                    let _ = self.eval(x, Use::Value);
                    // a discarded Linear value is dropped
                    if self.lin(&x.ty) && !matches!(x.ty, Ty::Never) && !self.st.dead && !is_place_expr(x) {
                        self.err("E-LINEAR-DROP", x.span, format!("a Linear value of type `{}` is discarded", self.c.program.ty_name(&x.ty)));
                    }
                }
            }
        }
        let ls = match tail {
            Some(t) if !self.st.dead => self.eval(t, Use::Value),
            _ => BTreeSet::new(),
        };
        let scope = self.scopes.pop().unwrap();
        if !self.st.dead {
            self.end_scope(&scope, e.span, &ls);
        }
        ls
    }

    fn end_scope(&mut self, scope: &[LocalId], sp: Span, result_loans: &BTreeSet<u32>) {
        let in_scope: BTreeSet<LocalId> = scope.iter().copied().collect();
        for &l in scope {
            let ty = self.body.locals[l as usize].ty.clone();
            let ms = *self.st.ms.get(&l).unwrap_or(&MS::Init);
            if self.lin(&ty) && (ms == MS::Init || ms == MS::Maybe) {
                let nm = self.name(l);
                let lsp = self.body.locals[l as usize].span;
                self.err("E-LINEAR-DROP", lsp, format!("the Linear value `{nm}` is not consumed on every normal path (moved into a call, returned or destructured)"));
            }
        }
        // E-BORROW-OUTLIVE: a live value outside the scope still carries a loan on one of its
        // locals (one pass over the holders; a reborrow through a reference, a `*` path, borrows
        // the referent, not the reference, and may outlive the reference local)
        let mut hits: Vec<(LocalId, LocalId)> = vec![];
        for (holder, ls) in &self.st.loans_of {
            if ls.is_empty() || in_scope.contains(holder) {
                continue;
            }
            let targets: BTreeSet<LocalId> = ls.iter().filter_map(|x| {
                let ln = &self.loans[*x as usize];
                match ln.target {
                    Some(t) if in_scope.contains(&t) && !ln.path.starts_with('*') => Some(t),
                    _ => None,
                }
            }).collect();
            if targets.is_empty() || !self.live_after(*holder, sp.hi) {
                continue;
            }
            for t in targets {
                hits.push((t, *holder));
            }
        }
        hits.sort();
        // anchored where the scope ends (its closing brace), the point at which the loan
        // outlives its target; the review of 2026-10-23 found that anchoring at the block's start
        // put this consequence before its cause in the §5.16 order (N-79, ow05)
        let end = Span { file: sp.file, lo: sp.hi.saturating_sub(1).max(sp.lo), hi: sp.hi };
        for (l, holder) in hits {
            let (a, b) = (self.name(l), self.name(holder));
            self.err("E-BORROW-OUTLIVE", end, format!("`{a}` goes out of scope while `{b}` still borrows it"));
        }
        for &l in scope {
            if result_loans.iter().any(|x| self.loans[*x as usize].target == Some(l) && !self.loans[*x as usize].path.starts_with('*')) {
                let a = self.name(l);
                self.err("E-BORROW-OUTLIVE", end, format!("the block's value borrows `{a}`, which goes out of scope"));
            }
            self.st.loans_of.remove(&l);
            self.st.pmoved.remove(&l);
        }
    }

    fn check_exit_linear(&mut self, loop_id: Option<LoopId>, sp: Span) {
        // locals declared in scopes being left
        let depth = match loop_id {
            Some(id) => self.loop_stack.iter().find(|x| x.0 == id).map(|x| x.1).unwrap_or(0),
            None => 0,
        };
        let mut leaving = vec![];
        for s in &self.scopes[depth.min(self.scopes.len())..] {
            leaving.extend(s.iter().copied());
        }
        for l in leaving {
            let ty = self.body.locals[l as usize].ty.clone();
            let ms = *self.st.ms.get(&l).unwrap_or(&MS::Init);
            if self.lin(&ty) && (ms == MS::Init || ms == MS::Maybe) {
                let nm = self.name(l);
                self.err("E-LINEAR-DROP", sp, format!("leaving here drops the Linear value `{nm}`"));
            }
        }
    }

    fn bind_pat(&mut self, p: &TPat, ls: BTreeSet<u32>) {
        self.bind_pat_from(p, ls, None);
    }

    /// Bind a pattern whose scrutinee value carries `ls`. When the scrutinee is a local holding
    /// a known part of a parameter (`sym_base`), a by-value binding of a component receives only
    /// the symbolic loans at that component's positions, and its own position is recorded
    /// (F-62: `let (v, d) = t;` with `t: (&mut Vec<&u32>, &u32)` gives v the positions `.0`
    /// and `.0*[]`, d the position `.1`; review 2026-10-23, e2).
    fn bind_pat_from(&mut self, p: &TPat, ls: BTreeSet<u32>, scrut: Option<&TExpr>) {
        let base: Option<BTreeMap<LocalId, String>> = match scrut.map(|x| &x.kind) {
            Some(TK::Local(y)) => self.sym_base.get(y).cloned(),
            _ => None,
        };
        let mut paths = vec![];
        self.pat_paths(p, "", false, &mut paths);
        let mut per: BTreeMap<LocalId, BTreeSet<u32>> = BTreeMap::new();
        for (b, path) in paths {
            match (&base, &path) {
                (Some(bm), Some(sfx)) => {
                    let keep: BTreeSet<u32> = ls
                        .iter()
                        .copied()
                        .filter(|x| {
                            let ln = &self.loans[*x as usize];
                            match (ln.target, ln.param) {
                                (None, Some(j)) => match bm.get(&j) {
                                    Some(b0) => {
                                        let full = format!("{b0}{sfx}");
                                        ln.pos.starts_with(&full) || full.starts_with(&ln.pos)
                                    }
                                    None => true,
                                },
                                _ => true,
                            }
                        })
                        .collect();
                    self.sym_base.insert(b, bm.iter().map(|(j, b0)| (*j, format!("{b0}{sfx}"))).collect());
                    per.insert(b, keep);
                }
                _ => {
                    self.sym_base.remove(&b);
                }
            }
        }
        let mut bs = vec![];
        p.bindings(&mut bs);
        if std::env::var_os("MITHI_OWN_DEBUG").is_some() {
            let names: Vec<String> = bs.iter().map(|b| self.name(*b)).collect();
            let targets: Vec<String> = ls.iter().map(|x| format!("{:?}{}", self.loans[*x as usize].target.map(|t| self.name(t)), self.loans[*x as usize].path)).collect();
            eprintln!("own: bind {names:?} carries {targets:?}");
        }
        for b in bs {
            self.st.ms.insert(b, MS::Init);
            self.st.pmoved.remove(&b);
            let own = per.get(&b).cloned().unwrap_or_else(|| ls.clone());
            self.st.loans_of.insert(b, own);
            if let Some(s) = self.scopes.last_mut() {
                s.push(b);
            }
        }
    }

    fn join(&mut self, s1: St, s2: St, sp: Span) {
        if s1.dead {
            self.st = s2;
            return;
        }
        if s2.dead {
            self.st = s1;
            return;
        }
        let mut st = s1.clone();
        let keys: BTreeSet<LocalId> = s1.ms.keys().chain(s2.ms.keys()).copied().collect();
        for k in keys {
            let a = *s1.ms.get(&k).unwrap_or(&MS::Init);
            let b = *s2.ms.get(&k).unwrap_or(&MS::Init);
            let j = join_ms(a, b);
            if a != b && j == MS::Maybe {
                let ty = self.body.locals[k as usize].ty.clone();
                if self.lin(&ty) && (a == MS::Moved || b == MS::Moved) {
                    let nm = self.name(k);
                    self.err("E-LINEAR-DROP", sp, format!("the Linear value `{nm}` is consumed on one path and not on the other"));
                }
            }
            st.ms.insert(k, j);
        }
        for (k, v) in s2.loans_of {
            st.loans_of.entry(k).or_default().extend(v);
        }
        for (k, v) in s2.pmoved {
            st.pmoved.entry(k).or_default().extend(v);
        }
        self.st = st;
    }

    /// A loop (T-Loop, F-65): the body is re-evaluated from the join of the entry state and the
    /// states that reach the head again (the body's end, every `continue`) until that head state
    /// stops changing, so moves, partial moves and loans carried across any number of iterations
    /// are seen (review 2026-10-16: two fixed passes, and loans not carried at all). Loans are
    /// named by site, so the state space is finite. After the loop: for `while` and `for`, the
    /// head state (the condition or iterator ends) joined with every `break`; for `loop`, the
    /// `break`s only (none: the loop does not end normally).
    fn eval_loop(&mut self, id: LoopId, body: &TExpr, cond: Option<&TExpr>, pat: Option<(&TPat, BTreeSet<u32>)>, is_loop: bool, sp: Span) -> BTreeSet<u32> {
        self.loop_stack.push((id, self.scopes.len(), sp));
        let iter_pushed = if let Some((_, il)) = &pat {
            self.loop_iters.push(il.clone());
            true
        } else {
            false
        };
        // locals bound anywhere in the loop (they are not part of the state at the head)
        let mut inner: BTreeSet<LocalId> = bound_in(self.c, body);
        if let Some((p, _)) = &pat {
            let mut bs = vec![];
            p.bindings(&mut bs);
            inner.extend(bs);
        }
        if let Some(c) = cond {
            inner.extend(bound_in(self.c, c));
        }
        let entry = self.st.clone();
        let mut head = entry.clone();
        head.dead = false;
        let was = self.second_pass;
        let mut after: Vec<St> = vec![];
        let mut break_loans = BTreeSet::new();
        let bound = 2 + 2 * self.body.locals.len() + self.loans.len().min(4096);
        for pass in 0..bound.max(4) {
            self.second_pass = was || pass > 0;
            self.st = head.clone();
            self.jumps.push((id, vec![], vec![], BTreeSet::new()));
            self.scopes.push(vec![]);
            let mut exit_state: Option<St> = None;
            if let Some(c) = cond {
                match &c.kind {
                    TK::LetCond(p, s) => {
                        let sl = self.eval(s, Use::Read);
                        exit_state = Some(self.st.clone());
                        if pat_moves(self.c, p, &self.copy_params) && !self.is_copy(&s.ty) {
                            self.move_by_pattern(s);
                        }
                        self.bind_pat_from(p, sl, Some(s));
                    }
                    _ => {
                        self.eval(c, Use::Read);
                        exit_state = Some(self.st.clone());
                    }
                }
            } else if !is_loop {
                exit_state = Some(self.st.clone());
            }
            if let Some((p, ls)) = &pat {
                self.bind_pat(p, ls.clone());
            }
            self.eval(body, Use::Value);
            let scope = self.scopes.pop().unwrap_or_default();
            if !self.st.dead {
                self.end_scope(&scope, sp, &BTreeSet::new());
            }
            let (_, brk, cont, bl) = self.jumps.pop().unwrap_or((id, vec![], vec![], BTreeSet::new()));
            break_loans = bl;
            let mut back: Vec<St> = vec![self.st.clone()];
            back.extend(cont);
            let mut new_head = head.clone();
            for s in &back {
                if !s.dead {
                    new_head = merge(&new_head, &strip(s, &inner));
                }
            }
            after = brk.iter().map(|s| strip(s, &inner)).collect();
            if let Some(x) = exit_state {
                if !x.dead {
                    after.push(strip(&x, &inner));
                }
            }
            if new_head == head {
                break;
            }
            head = new_head;
        }
        self.second_pass = was;
        if iter_pushed {
            self.loop_iters.pop();
        }
        self.loop_stack.pop();
        let mut out: Option<St> = None;
        for s in &after {
            if s.dead {
                continue;
            }
            out = Some(match out {
                None => s.clone(),
                Some(o) => merge(&o, s),
            });
        }
        match out {
            Some(o) => self.st = o,
            None => {
                self.st = entry;
                self.st.dead = true;
            }
        }
        break_loans
    }

    /// T-Jump (F-66): leaving a loop's scopes by `break` or `continue` ends the locals declared
    /// in them, so no loan live after the jump may target one (E-BORROW-OUTLIVE), and a `break`
    /// value may not borrow one (review 2026-10-16: only the block end checked this).
    fn check_jump_outlive(&mut self, id: LoopId, is_break: bool, value_loans: &BTreeSet<u32>, sp: Span) {
        let Some(&(_, depth, lsp)) = self.loop_stack.iter().find(|x| x.0 == id) else { return };
        let mut leaving: Vec<LocalId> = vec![];
        for s in &self.scopes[depth.min(self.scopes.len())..] {
            leaving.extend(s.iter().copied());
        }
        if leaving.is_empty() {
            return;
        }
        let pos = if is_break { lsp.hi } else { lsp.lo };
        for &l in &leaving {
            for (holder, ls) in self.st.loans_of.clone() {
                if holder == l || leaving.contains(&holder) {
                    continue;
                }
                let live = if is_break { self.live_after(holder, pos) } else { self.live_after(holder, pos) || self.live_after(holder, sp.hi) };
                if !live {
                    continue;
                }
                if ls.iter().any(|x| self.loans[*x as usize].target == Some(l) && !self.loans[*x as usize].path.starts_with('*')) {
                    let (a, b) = (self.name(l), self.name(holder));
                    let how = if is_break { "`break`" } else { "`continue`" };
                    self.err("E-BORROW-OUTLIVE", sp, format!("{how} ends the scope of `{a}` while `{b}` still borrows it"));
                }
            }
            if value_loans.iter().any(|x| self.loans[*x as usize].target == Some(l) && !self.loans[*x as usize].path.starts_with('*')) {
                let a = self.name(l);
                self.err("E-BORROW-OUTLIVE", sp, format!("the `break` value borrows `{a}`, which goes out of scope"));
            }
        }
    }

    fn check_closure_body(&mut self, cid: ClosureId) -> BTreeSet<u32> {
        // moves of the closure's own parameters and linear values created inside it
        let cd = &self.c.closures[cid as usize];
        let saved = self.st.clone();
        let saved_scopes = std::mem::take(&mut self.scopes);
        let saved_hr = std::mem::take(&mut self.hr_loans);
        self.scopes.push(vec![]);
        // by-move captures belong to the closure value: the body owns them, initialised, whatever
        // the creating state says after the move into the closure (review 2026-10-23: they were
        // checked in the creating state, where they are moved, so every use was E-MOVE-USED)
        let mut lin_caps: Vec<LocalId> = vec![];
        for cap in &cd.captures {
            if cap.mode == CaptureMode::Move {
                self.st.ms.insert(cap.local, MS::Init);
                self.st.pmoved.remove(&cap.local);
                // K-LinClo, T-Lin in the body: a Linear by-move capture must be consumed on every
                // normal path of the body (a Linear closure implements only FnOnce)
                if self.lin(&cap.ty) {
                    lin_caps.push(cap.local);
                }
            }
        }
        if let Some(s0) = self.scopes.last_mut() {
            s0.extend(lin_caps.iter().copied());
        }
        let hr = self.hr_params.get(&cid).cloned().unwrap_or_default();
        for (i, p) in cd.params.iter().enumerate() {
            if hr.contains(&i) {
                let mut ls = BTreeSet::new();
                let mut bs = vec![];
                p.bindings(&mut bs);
                for b in bs {
                    let id = self.new_loan_at(None, Some(b), String::new(), false, p.span, "hr".into());
                    self.hr_loans.insert(id);
                    ls.insert(id);
                }
                self.bind_pat(p, ls);
            } else {
                self.bind_pat(p, BTreeSet::new());
            }
        }
        // captured-by-move linear values are consumed by the closure body or dropped with it
        let body = cd.body.clone();
        // a `return` inside the closure returns from the closure, not from the enclosing body
        let saved_returns = std::mem::take(&mut self.returned_loans);
        self.clo_stack.push(cid);
        let mut ls = self.eval(&body, Use::Value);
        self.clo_stack.pop();
        for (r, _) in std::mem::replace(&mut self.returned_loans, saved_returns) {
            ls.extend(r);
        }
        let sc = self.scopes.pop().unwrap_or_default();
        if !self.st.dead {
            self.end_scope(&sc, body.span, &BTreeSet::new());
        }
        // a higher-ranked parameter's loan stored into a capture (or anything outside the body)
        // is E-LOCAL-MUT-STORE (§5.7 "Stores into captures"; review 2026-10-23, f15)
        if !self.hr_loans.is_empty() {
            let mut escaped: Vec<LocalId> = vec![];
            for (h, ls) in &self.st.loans_of {
                if self.body.locals[*h as usize].closure == Some(cid) {
                    continue;
                }
                if ls.iter().any(|x| self.hr_loans.contains(x)) {
                    escaped.push(*h);
                }
            }
            for h in escaped {
                let nm = self.name(h);
                let sp = self.c.closures[cid as usize].span;
                self.err("E-LOCAL-MUT-STORE", sp, format!("the closure stores a borrow received through a higher-ranked parameter (one whose written reference type has an elided lifetime and no expected signature, or one an `Fn*` bound writes as a reference) into `{nm}`, outside its body: the borrow may end when the call returns (§5.7, F-107; rustc rejects it too, E0521)"));
            }
        }
        let my_hr = std::mem::replace(&mut self.hr_loans, saved_hr);
        self.scopes = saved_scopes;
        self.st = saved;
        // a result carrying an annotated higher-ranked parameter's loan: `|d: &u32| d` (F-107;
        // rustc 1.99.1: "lifetime may not live long enough" [M]). A closure that has an expected
        // signature is judged by its bound's elision instead (F-40, at the call)
        let annotated_hr = self.c.closures[cid as usize].hr_annot.iter().any(|h| *h);
        if annotated_hr && ls.iter().any(|x| my_hr.contains(x)) {
            let sp = self.c.closures[cid as usize].span;
            self.err("E-REF-ESCAPE", sp, "the closure returns a borrow received through a parameter whose annotated reference type makes it higher-ranked: the result may outlive it (§5.7, F-107; rustc rejects it too)".into());
        }
        // result discipline (§5.7, F-40): a result borrowing a by-mut captured place or the
        // closure's own by-move state escapes the closure body (rustc rejects it too [inference])
        let cd = &self.c.closures[cid as usize];
        let owned: Vec<LocalId> = cd.captures.iter().filter(|c| c.mode != CaptureMode::Ref).map(|c| c.local).collect();
        if let Some(l) = owned.iter().find(|l| ls.iter().any(|x| self.loans[*x as usize].target == Some(**l) && !self.loans[*x as usize].path.starts_with('*'))) {
            let (nm, sp) = (self.name(*l), cd.span);
            self.err("E-REF-ESCAPE", sp, format!("the closure's result borrows `{nm}`, which it captures by mut or by move: the reference would escape the closure body (§5.7, F-40)"));
        }
        self.closure_results.insert(cid, ls.clone());
        ls
    }
}

/// The join of two states without diagnostics (loop heads and exits).
fn merge(a: &St, b: &St) -> St {
    if a.dead {
        return b.clone();
    }
    if b.dead {
        return a.clone();
    }
    let mut st = a.clone();
    let keys: BTreeSet<LocalId> = a.ms.keys().chain(b.ms.keys()).copied().collect();
    for k in keys {
        let x = *a.ms.get(&k).unwrap_or(&MS::Init);
        let y = *b.ms.get(&k).unwrap_or(&MS::Init);
        st.ms.insert(k, join_ms(x, y));
    }
    for (k, v) in &b.loans_of {
        st.loans_of.entry(*k).or_default().extend(v.iter().copied());
    }
    for (k, v) in &b.pmoved {
        st.pmoved.entry(*k).or_default().extend(v.iter().map(|(p, t)| (p.clone(), t.clone())));
    }
    st
}

/// A state without the given locals (they are out of scope where the state is used).
fn strip(s: &St, locals: &BTreeSet<LocalId>) -> St {
    let mut o = s.clone();
    o.ms.retain(|k, _| !locals.contains(k));
    o.loans_of.retain(|k, _| !locals.contains(k));
    o.pmoved.retain(|k, _| !locals.contains(k));
    o
}

/// The locals a pattern anywhere in `e` binds (closures not entered).
fn bound_in(_c: &Checked, e: &TExpr) -> BTreeSet<LocalId> {
    let mut out = BTreeSet::new();
    e.walk(&mut |x| {
        let mut bs = vec![];
        match &x.kind {
            TK::Block(stmts, _) => {
                for s in stmts {
                    if let TStmt::Let { pat, .. } = s {
                        pat.bindings(&mut bs);
                    }
                }
            }
            TK::Match(_, arms) => {
                for a in arms {
                    a.pat.bindings(&mut bs);
                }
            }
            TK::LetCond(p, _) => p.bindings(&mut bs),
            TK::For { pat, .. } => pat.bindings(&mut bs),
            _ => {}
        }
        out.extend(bs);
    });
    out
}

/// Two place paths overlap when one is a prefix of the other at a path boundary (`.a` and `.a.b`
/// overlap; `.a` and `.ab` do not; `*` steps through a reference).
fn overlaps(a: &str, b: &str) -> bool {
    is_prefix_path(a, b) || is_prefix_path(b, a)
}

fn is_prefix_path(pre: &str, p: &str) -> bool {
    p.starts_with(pre) && (p.len() == pre.len() || matches!(p.as_bytes()[pre.len()], b'.' | b'[' | b'*'))
}

/// The path of a place below its root (`place_root_any`): fields `.i`, indices `[]`, and `*` for
/// each reference dereferenced; the unsized view of a place is the place.
fn path_text(p: &TExpr) -> String {
    match &p.kind {
        TK::Local(_) => String::new(),
        TK::Field(b, i) => format!("{}.{i}", path_text(b)),
        TK::Index(b, _) | TK::SliceRange { base: b, .. } => format!("{}[]", path_text(b)),
        TK::Deref(b) => match &b.kind {
            TK::Unsize(u) => match &u.kind {
                TK::Borrow(_, q) => path_text(q),
                _ => String::new(),
            },
            _ if !b.ty.is_ref() => path_text(b),
            _ => format!("{}*", path_text(b)),
        },
        _ => String::new(),
    }
}

/// The local a place is rooted in, directly or through references: `r` for `*r`, `(*r).f`,
/// `r[i]` (NLL's roots). None for places reached through a temporary (a call result).
fn place_root_any(p: &TExpr) -> Option<LocalId> {
    match &p.kind {
        TK::Local(l) => Some(*l),
        TK::Field(b, _) | TK::Index(b, _) => place_root_any(b),
        TK::SliceRange { base, .. } => place_root_any(base),
        TK::Deref(b) => match &b.kind {
            TK::Unsize(u) => match &u.kind {
                TK::Borrow(_, q) => place_root_any(q),
                _ => None,
            },
            TK::Local(_) | TK::Field(..) | TK::Index(..) | TK::Deref(_) | TK::SliceRange { .. } => place_root_any(b),
            _ => None,
        },
        _ => None,
    }
}

/// The local a place is rooted in, not through a reference. A dereference of an owned container
/// (`Vec`, `String`, `Buf` viewed as a slice) stays inside the container's local.
fn place_root_direct(p: &TExpr) -> Option<LocalId> {
    match &p.kind {
        TK::Local(l) => Some(*l),
        TK::Field(b, _) | TK::Index(b, _) => place_root_direct(b),
        TK::SliceRange { base, .. } => place_root_direct(base),
        TK::Deref(b) if !b.ty.is_ref() => place_root_direct(b),
        _ => None,
    }
}

fn deref_chain(p: &TExpr) -> bool {
    match &p.kind {
        TK::Deref(_) => true,
        TK::Field(b, _) | TK::Index(b, _) => deref_chain(b),
        _ => false,
    }
}

fn is_place_expr(e: &TExpr) -> bool {
    matches!(e.kind, TK::Local(_) | TK::Field(..) | TK::Index(..) | TK::Deref(_))
}

fn pat_moves(c: &Checked, p: &TPat, copy_params: &[bool]) -> bool {
    match &p.kind {
        PK::Bind { by_ref: None, .. } => !copy_ty_with(c, &p.ty, copy_params),
        PK::Tuple(ps) | PK::Or(ps) | PK::Slice(ps, _) => ps.iter().any(|x| pat_moves(c, x, copy_params)),
        PK::Variant { fields, .. } => fields.iter().any(|(_, x)| pat_moves(c, x, copy_params)),
        _ => false,
    }
}

/// Copy, for zonked concrete types (no inference variables); a type parameter is not Copy.
pub fn copy_ty(c: &Checked, t: &Ty) -> bool {
    copy_ty_with(c, t, &[])
}

/// Copy, with the definition's generic parameters whose bounds imply `Copy` (as infer.rs's
/// `is_copy` honours them; review 2026-10-16: `fn h<T: Copy>(b: &T) -> T { *b }` was rejected).
pub fn copy_ty_with(c: &Checked, t: &Ty, copy_params: &[bool]) -> bool {
    match t {
        Ty::Int(_) | Ty::F32 | Ty::F64 | Ty::F16 | Ty::Bf16 | Ty::Bool | Ty::Char | Ty::Unit | Ty::Never | Ty::Error | Ty::FnPtr(..) => true,
        Ty::Ref(false, _) => true,
        Ty::Ref(true, _) => false,
        Ty::Tuple(v) => v.iter().all(|x| copy_ty_with(c, x, copy_params)),
        Ty::Array(e, _) => copy_ty_with(c, e, copy_params),
        Ty::Adt(a, xs) => {
            let ad = &c.program.adts[*a as usize];
            if ad.linear || !ad.derives("Copy") {
                return false;
            }
            ad.variants.iter().all(|v| v.fields.iter().all(|f| copy_ty_with(c, &f.ty.subst(xs), copy_params)))
        }
        Ty::Param(i) => copy_params.get(*i as usize).copied().unwrap_or(false),
        Ty::Closure(cid) => c.closures.get(*cid as usize).map(|cd| cd.captures.iter().all(|cap| cap.mode == CaptureMode::Ref || (cap.mode == CaptureMode::Move && copy_ty_with(c, &cap.ty, copy_params)))).unwrap_or(false),
        _ => false,
    }
}

/// Clone, structurally (K-CloCopy's by-move captures): Copy types, std containers of Clone
/// types, derived Clone, tuples and arrays of Clone types, and closures that are Clone.
fn clone_ty(c: &Checked, t: &Ty, copy_params: &[bool]) -> bool {
    if copy_ty_with(c, t, copy_params) {
        return true;
    }
    match t {
        Ty::Adt(a, xs) => {
            let ad = &c.program.adts[*a as usize];
            if ad.linear {
                return false;
            }
            if matches!(ad.lang.as_deref(), Some("Vec") | Some("Buf") | Some("Option") | Some("Result")) {
                return xs.iter().all(|x| clone_ty(c, x, copy_params));
            }
            ad.derives("Clone") || ad.lang.as_deref() == Some("String")
        }
        Ty::Tuple(v) => v.iter().all(|x| clone_ty(c, x, copy_params)),
        Ty::Array(e, _) => clone_ty(c, e, copy_params),
        Ty::Ref(false, _) => true,
        Ty::Closure(cid) => c.closures.get(*cid as usize).map(|cd| cd.captures.iter().all(|cp| cp.mode == CaptureMode::Ref || (cp.mode == CaptureMode::Move && clone_ty(c, &cp.ty, copy_params)))).unwrap_or(false),
        _ => false,
    }
}

/// Which generic parameters of a definition are Copy by their bounds (a bound on `Copy` or on a
/// trait whose supertraits include it).
fn copy_params_of(c: &Checked, generics: &[crate::program::GParam]) -> Vec<bool> {
    let Some(copy) = c.program.try_lang_trait("Copy") else { return vec![false; generics.len()] };
    let implies = |have: TraitId| -> bool {
        let mut stack = vec![have];
        let mut seen = vec![];
        while let Some(t) = stack.pop() {
            if t == copy {
                return true;
            }
            if seen.contains(&t) {
                continue;
            }
            seen.push(t);
            for s in &c.program.traits[t as usize].supers {
                if let BoundDef::Trait { tr, .. } = s {
                    stack.push(*tr);
                }
            }
        }
        false
    };
    generics.iter().map(|g| g.bounds.iter().any(|b| matches!(b, BoundDef::Trait { tr, .. } if implies(*tr)))).collect()
}

pub fn run(c: &mut Checked) {
    let fids: Vec<FnId> = c.bodies.keys().copied().collect();
    let mut diags = vec![];
    for fid in fids {
        let f = &c.program.fns[fid as usize];
        if f.role == FileRole::Std || f.body.is_none() {
            continue;
        }
        let body = &c.bodies[&fid];
        // source positions of every use of each local
        let mut uses: HashMap<LocalId, Vec<u32>> = HashMap::new();
        walk_deep(c, &body.expr, &mut |e| {
            if let TK::Local(l) = e.kind {
                uses.entry(l).or_default().push(e.span.lo);
            }
            if let TK::Closure(cid) = e.kind {
                for cap in &c.closures[cid as usize].captures {
                    uses.entry(cap.local).or_default().push(e.span.lo);
                }
            }
        });
        let mut o = Own {
            c,
            body,
            fid,
            st: St { ms: BTreeMap::new(), loans_of: BTreeMap::new(), pmoved: BTreeMap::new(), dead: false },
            loans: vec![],
            scopes: vec![vec![]],
            loop_stack: vec![],
            diags: vec![],
            uses,
            loop_spans: body.loop_spans.clone(),
            reported: BTreeSet::new(),
            second_pass: false,
            param_loan: HashMap::new(),
            is_copy_cache: HashMap::new(),
            returned_loans: vec![],
            closure_results: HashMap::new(),
            base_depth: 0,
            pending: vec![],
            loop_iters: vec![],
            jumps: vec![],
            loan_ids: HashMap::new(),
            copy_params: copy_params_of(c, &f.generics),
            targeted: std::collections::HashSet::new(),
            gen_fn_kinds: f.generics.iter().map(|g| g.bounds.iter().find_map(|b| if let BoundDef::Fn { kind, .. } = b { Some(*kind) } else { None })).collect(),
            sym_base: HashMap::new(),
            hr_params: hr_closure_params(c, &body.expr),
            hr_loans: BTreeSet::new(),
            clo_stack: vec![],
        };
        // parameters: owned locals; reference parameters carry the symbolic loan ℓ_j*
        for &p in &body.params {
            o.st.ms.insert(p, MS::Init);
            o.scopes[0].push(p);
            let pty = body.locals[p as usize].ty.clone();
            if pty.is_ref() || is_local(c, &pty) {
                // one symbolic loan per reference position (F-62)
                let mut positions = vec![];
                ref_positions(c, &pty, "", 0, &mut positions);
                if positions.is_empty() {
                    positions.push(String::new());
                }
                let mut ids = BTreeSet::new();
                for pos in positions {
                    let id = o.new_loan_at(None, Some(p), String::new(), false, body.locals[p as usize].span, pos);
                    o.param_loan.entry(p).or_insert(id);
                    ids.insert(id);
                }
                o.st.loans_of.insert(p, ids);
                o.sym_base.insert(p, [(p, String::new())].into_iter().collect());
            }
        }
        let ls = o.eval(&body.expr, Use::Value);
        if !o.st.dead {
            o.returned_loans.push((ls, body.expr.span));
            let scope = o.scopes.pop().unwrap_or_default();
            // by-value Linear parameters must be consumed
            for &l in &scope {
                let ty = body.locals[l as usize].ty.clone();
                let ms = *o.st.ms.get(&l).unwrap_or(&MS::Init);
                if is_linear(c, &ty) && (ms == MS::Init || ms == MS::Maybe) {
                    let nm = o.name(l);
                    let sp = body.locals[l as usize].span;
                    o.err("E-LINEAR-DROP", sp, format!("the Linear parameter `{nm}` is not consumed"));
                }
            }
        }
        // T-Ret (a), body part: a Local result carries only loans on the elided parameter
        if is_local(c, &f.ret) {
            let elided: Option<LocalId> = if f.self_mode.is_some() {
                body.params.first().copied()
            } else {
                let refs: Vec<LocalId> = body.params.iter().copied().filter(|p| body.locals[*p as usize].ty.mentions_ref()).collect();
                if refs.len() == 1 {
                    Some(refs[0])
                } else {
                    None
                }
            };
            for (ls, sp) in o.returned_loans.clone() {
                for lid in &ls {
                    let ln = o.loans[*lid as usize].clone();
                    // a reborrow through a reference is judged by the loans carried with it
                    if ln.path.starts_with('*') && ln.target.map(|t| body.locals[t as usize].ty.is_ref()).unwrap_or(false) {
                        continue;
                    }
                    let ok = match (ln.param, ln.target, elided) {
                        (Some(p), _, Some(e)) => p == e,
                        (None, Some(t), Some(e)) => t == e && deref_target_is_param(body, t),
                        _ => false,
                    };
                    if !ok {
                        let what = match (ln.param, ln.target) {
                            (Some(p), _) => format!("the parameter `{}`", o.name(p)),
                            (_, Some(t)) => format!("the local `{}`", o.name(t)),
                            _ => "a temporary".into(),
                        };
                        o.err("E-REF-ESCAPE", sp, format!("the result borrows {what}, not the place Rust's elision ties it to; a reference may leave a body only as a projection of the elided parameter (T-Ret (a))"));
                    }
                }
            }
        }
        diags.extend(o.diags);
    }
    c.diags.extend(diags);
}

/// The reference positions of a type (F-62): see `Loan::pos`.
fn ref_positions(c: &Checked, t: &Ty, path: &str, depth: u32, out: &mut Vec<String>) {
    if depth > 12 {
        return;
    }
    match t {
        Ty::Ref(_, inner) => {
            out.push(path.to_string());
            ref_positions(c, inner, &format!("{path}*"), depth + 1, out);
        }
        Ty::Tuple(ts) => {
            for (i, x) in ts.iter().enumerate() {
                ref_positions(c, x, &format!("{path}.{i}"), depth + 1, out);
            }
        }
        Ty::Array(e, _) | Ty::Slice(e) => ref_positions(c, e, &format!("{path}[]"), depth + 1, out),
        Ty::Adt(a, xs) => {
            let ad = &c.program.adts[*a as usize];
            let n0 = out.len();
            if matches!(ad.lang.as_deref(), Some("Vec") | Some("Buf")) {
                if let Some(x) = xs.first() {
                    ref_positions(c, x, &format!("{path}[]"), depth + 1, out);
                }
            } else {
                for (k, x) in xs.iter().enumerate() {
                    ref_positions(c, x, &format!("{path}<{k}>"), depth + 1, out);
                }
            }
            if out.len() == n0 && is_local(c, t) {
                out.push(format!("{path}~"));
            }
        }
        _ => {
            if is_local(c, t) {
                out.push(format!("{path}~"));
            }
        }
    }
}

/// Closures passed where a parameter's type is a type parameter (or a reference to one) whose
/// `Fn*` bound writes an argument type that mentions a reference: those closure parameters are
/// higher-ranked in Rust (no X1 signature names a lifetime, so every such reference is elided).
fn hr_closure_params(c: &Checked, body: &TExpr) -> HashMap<ClosureId, Vec<usize>> {
    let mut out: HashMap<ClosureId, Vec<usize>> = HashMap::new();
    // parameters higher-ranked by their annotation (F-107), for closures with no expected
    // signature (typeck records which)
    walk_deep(c, body, &mut |e| {
        if let TK::Closure(cid) = e.kind {
            let idx: Vec<usize> = c.closures[cid as usize].hr_annot.iter().enumerate().filter(|(_, h)| **h).map(|(k, _)| k).collect();
            if !idx.is_empty() {
                out.insert(cid, idx);
            }
        }
    });
    walk_deep(c, body, &mut |e| {
        let (callee, args) = match &e.kind {
            TK::Call { f, args, .. } => (*f, args),
            TK::TraitCall { decl, args, .. } => (*decl, args),
            _ => return,
        };
        let cf = &c.program.fns[callee as usize];
        for (i, a) in args.iter().enumerate() {
            let cid = match &a.kind {
                TK::Closure(x) => *x,
                TK::Borrow(_, inner) => match &inner.kind {
                    TK::Closure(x) => *x,
                    _ => continue,
                },
                _ => continue,
            };
            let gi = match cf.params.get(i).map(|p| &p.ty) {
                Some(Ty::Param(g)) => Some(*g),
                Some(Ty::Ref(_, inner)) => match **inner {
                    Ty::Param(g) => Some(g),
                    _ => None,
                },
                _ => None,
            };
            let Some(gi) = gi else { continue };
            let Some(gp) = cf.generics.get(gi as usize) else { continue };
            if let Some((_, ps, _)) = crate::lower::fn_bound(gp) {
                let idx: Vec<usize> = ps.iter().enumerate().filter(|(_, t)| t.mentions_ref()).map(|(k, _)| k).collect();
                if !idx.is_empty() {
                    out.insert(cid, idx);
                }
            }
        }
    });
    out
}

fn deref_target_is_param(body: &Body, t: LocalId) -> bool {
    body.locals[t as usize].param.is_some()
}

#[allow(dead_code)]
fn unused(_: BTreeMap<u32, u32>) {}
