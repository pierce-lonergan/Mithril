//! Grades (note sections 2.3, 5.3, 5.5, 5.7, 5.9, 5.11, 5.12): a dependency analysis over symbolic
//! parameter grades. A grade here is (sd, plat, raw, deps, nu, obs):
//! - sd / plat: the constant schedule and platform components of the scope (⟨d_s, d_p⟩);
//! - raw: the constant NaN bit (ν = raw);
//! - deps: parameters the value depends on by data or control flow (D);
//! - nu: parameters whose NaN bit passes through (n = pass(D_ν));
//! - obs: parameters whose raw float content reaches a NaN observer (O).
//! Fidelity is `exact` throughout v0 (real and approx are reserved). B (evidence) is not tracked:
//! typing never rejects on it (section 5.12).
//!
//! Sinks: kernel outputs and `#[grade(exact, cross_device)]` outputs (results and `&mut`
//! referents at every normal exit) need a cross_device constant scope and, for float content,
//! ν = canon whatever the inputs' bits (a caller's buffer is raw in general, derivation D-C2);
//! E-GRADE or E-NAN-RAW-SINK. Trait impls are checked against the row-derived bound Θ̂_m
//! (E-IMPL-GRADE, F-50).

use super::*;
use crate::ast::BinOp;
use crate::diag::Diag;
use crate::program::Label;
use std::collections::{BTreeSet, HashMap};

#[derive(Clone, Copy, Debug, PartialEq, Eq, Default)]
pub struct G {
    sd: bool,
    plat: bool,
    raw: bool,
    deps: u64,
    nu: u64,
    obs: u64,
}

impl G {
    fn j(self, o: G) -> G {
        G { sd: self.sd | o.sd, plat: self.plat | o.plat, raw: self.raw | o.raw, deps: self.deps | o.deps, nu: self.nu | o.nu, obs: self.obs | o.obs }
    }
    /// The control part of a grade (scope and dependencies; no NaN bit).
    fn ctl(self) -> G {
        G { sd: self.sd, plat: self.plat, raw: false, deps: self.deps, nu: 0, obs: self.obs }
    }
    fn param(i: u32, float: bool) -> G {
        let b = 1u64 << (i.min(63));
        G { deps: b, nu: if float { b } else { 0 }, ..Default::default() }
    }
    fn sh() -> G {
        // γ_sh = (exact, ⟨sd, cd⟩, ∅, raw)
        G { sd: true, raw: true, ..Default::default() }
    }
    fn canon(self) -> G {
        G { raw: false, nu: 0, ..self }
    }
    fn rawed(self) -> G {
        G { raw: true, nu: 0, ..self }
    }
}

/// Substitute a transfer over symbolic parameters with actual argument grades.
fn apply(t: G, args: &[G], base: u32) -> G {
    let mut out = G { sd: t.sd, plat: t.plat, raw: t.raw, ..Default::default() };
    for (i, a) in args.iter().enumerate() {
        let bit = 1u64 << ((base + i as u32).min(63));
        if t.deps & bit != 0 {
            out = out.j(a.ctl());
        }
        if t.nu & bit != 0 {
            out.raw |= a.raw;
            out.nu |= a.nu;
        }
        if t.obs & bit != 0 {
            if a.raw {
                out.plat = true;
            }
            out.obs |= a.nu;
        }
    }
    // symbols not substituted (the enclosing definition's own parameters) stay
    let mask: u64 = (0..args.len() as u32).map(|i| 1u64 << ((base + i).min(63))).fold(0, |a, b| a | b);
    out.deps |= t.deps & !mask;
    out.nu |= t.nu & !mask;
    out.obs |= t.obs & !mask;
    out
}

#[derive(Clone, Default, Debug)]
pub struct Summary {
    ret: G,
    /// final referent grade of each `&mut` parameter (by parameter index)
    muts: Vec<(usize, G)>,
    exit: G,
    may_trap: bool,
}

#[derive(Clone, Default, Debug)]
struct CloSum {
    ret: G,
    /// by-mut captures and captured `&mut` referents written: (target, grade over closure params)
    writes: Vec<(Target, G)>,
    /// final referent grade of each `&mut` parameter of the closure (θ_mut, F-69)
    param_muts: Vec<(usize, G)>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)]
enum Target {
    Local(LocalId),
    MutRef(LocalId),
}

#[derive(Clone)]
struct St {
    env: HashMap<LocalId, G>,
    /// referents of `&mut` parameters
    mutref: HashMap<LocalId, G>,
    /// closures a local's value carries (lazy adapters)
    clos: HashMap<LocalId, BTreeSet<ClosureId>>,
    /// local references: the targets their loans point to (write targets, F-39)
    refs: HashMap<LocalId, (Target, G)>,
    dead: bool,
}

#[allow(dead_code)]
struct Ga<'a> {
    c: &'a Checked,
    fid: FnId,
    body: &'a Body,
    st: St,
    pc: Vec<G>,
    jumps: HashMap<LoopId, G>,
    jf: G,
    omega: G,
    rho: G,
    x: HashMap<LocalId, G>,
    sums: &'a HashMap<FnId, Summary>,
    closums: HashMap<ClosureId, CloSum>,
    /// symbols of closure parameters start here
    clo_base: u32,
    cover_rhs: HashMap<LoopId, G>,
    open_loops: Vec<LoopId>,
    /// grades of the values `break` gives each `loop` (F-85)
    brk_vals: HashMap<LoopId, G>,
    /// while a closure body is summarised: the grades its locals have at its `return`s (F-68)
    clo_x: Option<HashMap<LocalId, G>>,
}

fn lit_is_nan(bits: u64, t: &Ty) -> bool {
    match t {
        Ty::F32 => f32::from_bits(bits as u32).is_nan(),
        Ty::F64 => f64::from_bits(bits).is_nan(),
        _ => false,
    }
}

/// A float constant initialised by a literal (possibly negated), so never a NaN.
fn const_is_plain_float(c: &Checked, cid: u32) -> bool {
    use crate::ast::{ExprKind, Lit};
    fn plain(e: &crate::ast::Expr) -> bool {
        match &e.kind {
            ExprKind::Lit(Lit::Float(..)) | ExprKind::Lit(Lit::Int(..)) => true,
            ExprKind::Unary(crate::ast::UnOp::Neg, x) => plain(x),
            ExprKind::Paren(x) => plain(x),
            _ => false,
        }
    }
    c.program.consts.get(cid as usize).and_then(|cd| cd.value.as_ref()).map(plain).unwrap_or(false)
}

fn holds_mut_ref(t: &Ty) -> bool {
    let mut h = false;
    t.walk(&mut |x| {
        if matches!(x, Ty::Ref(true, _)) {
            h = true;
        }
    });
    h
}

/// Does a value of this type hold float content (directly, or in the fields of a struct or
/// enum)? Review 2026-10-16: a struct's float fields were not seen, so a `&mut S` output with an
/// `[f32; 4]` field skipped the NaN sink check (item N-58).
fn has_float(c: &Checked, t: &Ty) -> bool {
    has_float_d(c, t, 0)
}

fn has_float_d(c: &Checked, t: &Ty, depth: u32) -> bool {
    if depth > 8 {
        return false;
    }
    let mut h = false;
    t.walk(&mut |x| match x {
        Ty::F32 | Ty::F64 => h = true,
        Ty::Adt(a, xs) => {
            let ad = &c.program.adts[*a as usize];
            if ad.role != FileRole::Std && ad.variants.iter().any(|v| v.fields.iter().any(|f| has_float_d(c, &f.ty.subst(xs), depth + 1))) {
                h = true;
            }
        }
        _ => {}
    });
    h
}

impl<'a> Ga<'a> {
    fn pc(&self) -> G {
        let mut g = self.pc.last().copied().unwrap_or_default();
        for l in &self.open_loops {
            if let Some(j) = self.jumps.get(l) {
                g = g.j(*j);
            }
        }
        g.j(self.jf).ctl()
    }

    fn read_local(&self, l: LocalId) -> G {
        self.st.env.get(&l).copied().unwrap_or_default()
    }

    /// The grade of a place read, and the target a write to it updates.
    fn place(&mut self, e: &TExpr) -> (G, Option<Target>, G) {
        // returns (grade read, write target, selection/address grade)
        match &e.kind {
            TK::Local(l) => (self.read_local(*l), Some(Target::Local(*l)), G::default()),
            TK::Deref(b) => {
                if let TK::Local(l) = &b.kind {
                    if let Some(g) = self.st.mutref.get(l) {
                        return (*g, Some(Target::MutRef(*l)), G::default());
                    }
                    if let Some((t, addr)) = self.st.refs.get(l).copied() {
                        let g = self.target_grade(t);
                        return (g.j(addr), Some(t), addr);
                    }
                    return (self.read_local(*l), None, G::default());
                }
                // the unsized view of a place built by method probing
                if let TK::Unsize(u) = &b.kind {
                    if let TK::Borrow(_, p) = &u.kind {
                        let p = p.clone();
                        return self.place(&p);
                    }
                }
                if let TK::Borrow(_, p) = &b.kind {
                    let p = p.clone();
                    return self.place(&p);
                }
                // a projection result: writes go to the receiver's place (target*, F-39)
                if let TK::Call { args, .. } = &b.kind {
                    let g = self.eval(b);
                    let t = match args.first().map(|a| &a.kind) {
                        Some(TK::Borrow(_, p)) => {
                            let p = p.clone();
                            self.place(&p).1
                        }
                        Some(TK::Local(l)) => {
                            if self.st.mutref.contains_key(l) {
                                Some(Target::MutRef(*l))
                            } else {
                                self.st.refs.get(l).map(|x| x.0)
                            }
                        }
                        _ => None,
                    };
                    return (g, t, G::default());
                }
                let g = self.eval(b);
                (g, None, G::default())
            }
            TK::Field(b, _) => {
                let (g, t, a) = self.place(b);
                (g, t, a)
            }
            TK::Index(b, i) => {
                let gi = self.eval(i);
                let (g, t, a) = self.place(b);
                (g.j(gi.ctl()), t, a.j(gi.ctl()))
            }
            TK::SliceRange { base, lo, hi, .. } => {
                let mut sel = G::default();
                if let Some(x) = lo {
                    sel = sel.j(self.eval(x).ctl());
                }
                if let Some(x) = hi {
                    sel = sel.j(self.eval(x).ctl());
                }
                let (g, t, a) = self.place(base);
                (g.j(sel), t, a.j(sel))
            }
            TK::Unsize(b) => self.place(b),
            _ => {
                let g = self.eval(e);
                (g, None, G::default())
            }
        }
    }

    fn target_grade(&self, t: Target) -> G {
        match t {
            Target::Local(l) => self.read_local(l),
            Target::MutRef(l) => self.st.mutref.get(&l).copied().unwrap_or_default(),
        }
    }

    fn write(&mut self, t: Target, g: G, strong: bool) {
        match t {
            Target::Local(l) => {
                let cur = self.read_local(l);
                self.st.env.insert(l, if strong { g } else { cur.j(g) });
            }
            Target::MutRef(l) => {
                let cur = self.st.mutref.get(&l).copied().unwrap_or_default();
                self.st.mutref.insert(l, if strong { g } else { cur.j(g) });
            }
        }
    }

    fn row_taint(&self, fid: FnId) -> G {
        let r = self.c.facts.rows.get(&fid).cloned().unwrap_or_default();
        let mut g = G::default();
        if r.contains(&Label::Nondet) || r.contains(&Label::Time) {
            g.sd = true;
        }
        if r.contains(&Label::NondetPlatform) {
            g.plat = true;
        }
        g
    }

    fn closures_in(&self, e: &TExpr) -> BTreeSet<ClosureId> {
        let mut out = BTreeSet::new();
        match &e.kind {
            TK::Closure(c) => {
                out.insert(*c);
            }
            TK::Local(l) => {
                if let Some(s) = self.st.clos.get(l) {
                    out.extend(s.iter().copied());
                }
            }
            TK::Borrow(_, b) | TK::Deref(b) | TK::Unsize(b) => out.extend(self.closures_in(b)),
            TK::Call { args, .. } => {
                for a in args {
                    out.extend(self.closures_in(a));
                }
            }
            _ => {}
        }
        out
    }

    /// Apply a closure's writes (by-mut captures, captured `&mut` referents) at the given grade
    /// for its parameters and the current pc.
    fn apply_closure_writes(&mut self, cid: ClosureId, params: &[G], extra: G) {
        // the summary just computed for this call, if any (it depends on the current state)
        let cs = match self.closums.remove(&cid) {
            Some(s) => s,
            None => self.closure_summary(cid),
        };
        let pc = self.pc();
        for (t, g) in cs.writes {
            let v = apply(g, params, self.clo_base).j(pc).j(extra.ctl());
            self.write(t, v, false);
        }
    }

    /// The summary of a closure body at the current grades of what it captures. It is computed
    /// at every call, not once (F-60: a later call reads the captures' current grades, so state a
    /// first call left under a schedule-dependent pc is seen). `holder` is the local holding the
    /// closure value when it is called through one: by-move captures are part of that value, so
    /// they read and write its grade.
    fn closure_summary(&mut self, cid: ClosureId) -> CloSum {
        self.closure_summary_at(cid, None)
    }

    fn closure_summary_at(&mut self, cid: ClosureId, holder: Option<LocalId>) -> CloSum {
        let cd = &self.c.closures[cid as usize];
        // analyse the body with symbolic parameters, captures at their current grades
        let saved_st = self.st.clone();
        let saved_pc = std::mem::take(&mut self.pc);
        let saved_j = std::mem::take(&mut self.jumps);
        let saved_open = std::mem::take(&mut self.open_loops);
        let saved_jf = self.jf;
        let saved_omega = self.omega;
        let saved_rho = self.rho;
        let saved_x = self.clo_x.replace(HashMap::new());
        self.jf = G::default();
        self.rho = G::default();
        self.pc = vec![G::default()];
        let moved: Vec<LocalId> = cd.captures.iter().filter(|c| c.mode == CaptureMode::Move).map(|c| c.local).collect();
        if let Some(h) = holder {
            let gh = self.read_local(h);
            for m in &moved {
                let cur = self.read_local(*m);
                self.st.env.insert(*m, cur.j(gh));
            }
        }
        let mut mut_params: Vec<(usize, LocalId)> = vec![];
        for (i, p) in cd.params.iter().enumerate() {
            let g = G::param(self.clo_base + i as u32, has_float(self.c, &p.ty));
            self.bind(p, g);
            // a `&mut` parameter's referent: written through, reported as θ_mut (F-69)
            if let (Some(l), Ty::Ref(true, _)) = (p.is_irrefutable_bind(), &p.ty) {
                self.st.mutref.insert(l, g);
                mut_params.push((i, l));
            }
        }
        let before = self.st.clone();
        let r = self.eval(&cd.body);
        let ret = r.j(self.rho);
        let at_returns = self.clo_x.take().unwrap_or_default();
        // every place the body writes, by syntax: a write applies at the caller's pc even when
        // it does not change the grade the closure saw
        let mut written: BTreeSet<LocalId> = BTreeSet::new();
        walk_deep(self.c, &cd.body, &mut |x| match &x.kind {
            TK::Assign(p, _) | TK::AssignOp(_, p, _) | TK::Borrow(true, p) => {
                if let Some(r) = place_root(p) {
                    written.insert(r);
                }
            }
            _ => {}
        });
        let _ = &before;
        let dead = self.st.dead;
        // a write's grade: at the body's normal end, joined with the grades at its returns (F-68)
        let fin = |_me: &Self, l: LocalId, g: G| -> G {
            let base = if dead { G::default() } else { g };
            match at_returns.get(&l) {
                Some(x) => base.j(*x),
                None => base,
            }
        };
        let mut writes = vec![];
        for l in written {
            let param_mut = mut_params.iter().any(|(_, pl)| *pl == l);
            if param_mut {
                continue;
            }
            if self.st.mutref.contains_key(&l) {
                let g = fin(self, l, self.st.mutref[&l]);
                writes.push((Target::MutRef(l), g));
            } else if let Some((t, _)) = self.st.refs.get(&l).copied() {
                // a captured local reference: the place it borrows is written (F-67)
                let g = fin(self, l, self.target_grade(t));
                writes.push((t, g));
            } else if cd.captures.iter().any(|c| c.local == l) {
                let g = fin(self, l, self.read_local(l));
                match holder {
                    // a by-move capture is state of the closure value (F-60)
                    Some(h) if moved.contains(&l) => writes.push((Target::Local(h), g)),
                    _ => writes.push((Target::Local(l), g)),
                }
            }
        }
        let mut param_muts = vec![];
        for (i, l) in &mut_params {
            let g = fin(self, *l, self.st.mutref.get(l).copied().unwrap_or_default());
            param_muts.push((*i, g));
        }
        self.st = saved_st;
        self.pc = saved_pc;
        self.jumps = saved_j;
        self.open_loops = saved_open;
        self.jf = saved_jf;
        self.omega = saved_omega;
        self.rho = saved_rho;
        self.clo_x = saved_x;
        let s = CloSum { ret, writes, param_muts };
        self.closums.insert(cid, s.clone());
        s
    }

    /// At a `return` inside a closure body being summarised: the grades of the locals it may
    /// have written, and of the referents of local references, join the closure's exit context.
    fn record_clo_exit(&mut self) {
        if self.clo_x.is_none() {
            return;
        }
        let pc = self.pc();
        let env: Vec<(LocalId, G)> = self.st.env.iter().map(|(k, v)| (*k, *v)).collect();
        let muts: Vec<(LocalId, G)> = self.st.mutref.iter().map(|(k, v)| (*k, *v)).collect();
        let refs: Vec<(LocalId, Target)> = self.st.refs.iter().map(|(k, v)| (*k, v.0)).collect();
        let mut add: Vec<(LocalId, G)> = vec![];
        for (k, v) in env.into_iter().chain(muts) {
            add.push((k, v.j(pc)));
        }
        for (k, t) in refs {
            add.push((k, self.target_grade(t).j(pc)));
        }
        if let Some(cx) = &mut self.clo_x {
            for (k, v) in add {
                let e = cx.entry(k).or_default();
                *e = e.j(v);
            }
        }
    }

    /// The place an argument lends mutably: `&mut p`, a `&mut` local or parameter, or a `&mut`
    /// inside an aggregate (`Some(&mut y)`, F-62).
    fn arg_target(&mut self, a: &TExpr) -> Option<Target> {
        match &a.kind {
            TK::Borrow(true, p) => self.place(p).1,
            TK::Local(l) => {
                if self.st.mutref.contains_key(l) {
                    Some(Target::MutRef(*l))
                } else {
                    self.st.refs.get(l).map(|x| x.0)
                }
            }
            TK::Unsize(inner) => self.arg_target(inner),
            TK::Ctor { fields, .. } | TK::Tuple(fields) => fields.iter().find_map(|f| self.arg_target(f)),
            _ => None,
        }
    }

    /// `&mut` references bound out of a by-value parameter that holds them (`Some(r) = o` with
    /// `o: Option<&mut T>`): writes through them go to the parameter's pseudo-place `*o` (F-62).
    fn bind_mut_refs(&mut self, p: &TPat, scrut: &TExpr) {
        let TK::Local(o) = scrut.kind else { return };
        if !self.st.mutref.contains_key(&o) {
            return;
        }
        let mut bs = vec![];
        p.bindings(&mut bs);
        for b in bs {
            if matches!(self.body.locals.get(b as usize).map(|d| &d.ty), Some(Ty::Ref(true, _))) {
                self.st.refs.insert(b, (Target::MutRef(o), G::default()));
            }
        }
    }

    /// Does the argument lend a whole place, the one its write target names?
    fn lends_whole(&self, a: &TExpr) -> bool {
        match &a.kind {
            TK::Borrow(true, p) => match &p.kind {
                TK::Local(_) => true,
                TK::Deref(b) => matches!(&b.kind, TK::Local(r) if self.st.mutref.contains_key(r)),
                _ => false,
            },
            TK::Unsize(x) => self.lends_whole(x),
            TK::Local(r) => self.st.mutref.contains_key(r),
            _ => false,
        }
    }

    fn bind(&mut self, p: &TPat, g: G) {
        let mut bs = vec![];
        p.bindings(&mut bs);
        for b in bs {
            self.st.env.insert(b, g);
        }
    }

    fn exit_site(&mut self, e: &TExpr, operands: G) {
        if self.c.facts.undischarged.contains(&(self.fid, e.span)) {
            let pc = self.pc();
            self.omega = self.omega.j(pc).j(operands.ctl());
        }
    }

    fn eval(&mut self, e: &TExpr) -> G {
        if self.st.dead {
            return G::default();
        }
        let pc = self.pc();
        match &e.kind {
            // `f32::NAN` / `f64::NAN` (folded to a literal; no float literal is a NaN): ν = raw
            // until the Surface Map pins its bits (note §5.3; review 2026-10-16). Switch to
            // canon here, in one place, when 0x7fc00000 is pinned.
            TK::Lit(LitVal::Float(bits)) if lit_is_nan(*bits, &e.ty) => G::default().rawed().j(pc),
            // a float constant whose initialiser is not a plain literal may hold a NaN
            TK::Const(cid) if has_float(self.c, &e.ty) && !const_is_plain_float(self.c, *cid) => G::default().rawed().j(pc),
            TK::Lit(_) | TK::Const(_) => pc,
            TK::Local(_) | TK::Field(..) | TK::Index(..) | TK::Deref(_) | TK::SliceRange { .. } => {
                let (g, _, _) = self.place(e);
                self.exit_site(e, g);
                // integers carry no NaN bit
                let g = if has_float(self.c, &e.ty) { g } else { g.canon() };
                g.j(pc)
            }
            TK::Borrow(_, p) => {
                let (g, _, _) = self.place(p);
                g.j(pc)
            }
            TK::Unsize(b) => self.eval(b),
            TK::Unary(_, a) => {
                let g = self.eval(a);
                if e.ty.is_float() {
                    g.rawed().j(pc)
                } else {
                    g.canon().j(pc)
                }
            }
            TK::Binary(op, a, b) => {
                let ga = self.eval(a);
                let gb = self.eval(b);
                let g = ga.j(gb);
                self.exit_site(e, g);
                if matches!(op, BinOp::And | BinOp::Or) || op.is_cmp() {
                    // payload-blind comparisons: no NaN observation
                    return G { raw: false, nu: 0, ..g }.j(pc);
                }
                if e.ty.is_float() {
                    g.rawed().j(pc)
                } else {
                    g.canon().j(pc)
                }
            }
            TK::Cast(a) => {
                let g = self.eval(a);
                match (&a.ty, &e.ty) {
                    (f, t) if f.is_float() && t.is_float() => {
                        if f == t {
                            g.j(pc)
                        } else {
                            g.rawed().j(pc)
                        }
                    }
                    _ => g.canon().j(pc),
                }
            }
            TK::Assign(p, r) => {
                let gv = self.eval(r);
                let (_, t, addr) = self.place(p);
                let pc = self.pc();
                let val = gv.j(addr).j(pc);
                if let Some(t) = t {
                    let strong = matches!(p.kind, TK::Local(_));
                    self.write(t, val, strong);
                }
                // a local reference: remember where it points
                if let TK::Local(l) = p.kind {
                    if let TK::Borrow(true, inner) = &r.kind {
                        let (_, tt, a2) = self.place(inner);
                        if let Some(tt) = tt {
                            self.st.refs.insert(l, (tt, a2));
                        }
                    }
                }
                // cover bookkeeping: the RHS of the covering write p[i] = e
                if let Some(lid) = self.open_loops.last().copied() {
                    let covered = self.c.facts.covers.get(&(self.fid, lid)).cloned().unwrap_or_default();
                    let row = self.c.facts.row_covers.get(&(self.fid, lid)).copied();
                    if let Some(root) = write_root(self.c, p) {
                        if covered.contains(&root) || row == Some(root) {
                            self.cover_rhs.insert(lid, gv.j(addr));
                        }
                    }
                }
                pc
            }
            TK::AssignOp(_, p, r) => {
                let gv = self.eval(r);
                let (gp, t, addr) = self.place(p);
                self.exit_site(e, gv.j(gp));
                let pc = self.pc();
                let mut val = gv.j(gp).j(addr).j(pc);
                if has_float(self.c, &p.ty) {
                    val = val.rawed();
                } else {
                    val = val.canon();
                }
                if let Some(t) = t {
                    self.write(t, val, false);
                }
                pc
            }
            TK::Call { f, args, .. } => self.eval_call(*f, args, e),
            TK::TraitCall { decl, args, tr, self_ty, method, .. } => {
                // a call on a type parameter uses the row-derived bound Θ̂_m (section 5.12)
                let mut gs = vec![];
                for a in args {
                    gs.push(self.eval(a));
                }
                let concrete = !matches!(self_ty, Ty::Param(_) | Ty::Infer(_) | Ty::Opaque(_));
                if concrete {
                    if let Some(t) = resolve_impl_method(self.c, *tr, self_ty, method) {
                        if let Some(s) = self.sums.get(&t) {
                            let r = apply(s.ret, &gs, 0);
                            return r.j(pc);
                        }
                    }
                }
                let mut g = self.row_taint(*decl);
                for x in &gs {
                    g = g.j(x.ctl());
                    g.obs |= x.nu;
                    if x.raw {
                        g.plat = true;
                    }
                }
                if has_float(self.c, &e.ty) {
                    g.raw = true;
                }
                g.j(pc)
            }
            TK::CallValue(f, args) => {
                let gf = self.eval(f);
                let mut gs = vec![];
                for a in args {
                    gs.push(self.eval(a));
                }
                let cs: Vec<ClosureId> = self.closures_in(f).into_iter().collect();
                let mut r = gf.j(pc);
                if cs.is_empty() {
                    // a closure parameter of a generic body: conservative
                    for g in &gs {
                        r = r.j(*g);
                    }
                    if has_float(self.c, &e.ty) {
                        r.raw = true;
                    }
                }
                let holder = match &f.kind {
                    TK::Local(l) => Some(*l),
                    _ => None,
                };
                for c in cs {
                    let s = self.closure_summary_at(c, holder);
                    r = r.j(apply(s.ret, &gs, self.clo_base));
                    // T-CallClo (F-69): the closure's θ_mut on its `&mut` parameters, applied to
                    // the places the arguments borrow
                    for (i, mg) in &s.param_muts {
                        if let Some(a) = args.get(*i) {
                            if let Some(t) = self.arg_target(a) {
                                let v = apply(*mg, &gs, self.clo_base).j(self.pc());
                                self.write(t, v, false);
                            }
                        }
                    }
                    self.apply_closure_writes(c, &gs, G::default());
                }
                r
            }
            // a function used as a value carries the constant part of what calling it yields
            // (its row's schedule and platform taint, its summary's), so a later call through
            // the value is not cleaner than the direct call (review 2026-10-16)
            TK::FnRef(fid, _) => {
                let mut g = pc.j(self.row_taint(*fid));
                if let Some(s) = self.sums.get(fid) {
                    g.sd |= s.ret.sd | s.exit.sd;
                    g.plat |= s.ret.plat | s.exit.plat;
                } else if self.c.bodies.contains_key(fid) {
                    // no summary yet: as the pessimistic call path
                    g.sd = true;
                }
                g
            }
            TK::Closure(_) => pc,
            TK::Ctor { fields, .. } | TK::Tuple(fields) | TK::Array(fields) => {
                let mut g = pc;
                for f in fields {
                    g = g.j(self.eval(f));
                }
                g
            }
            TK::CtorUpdate { fields, base, .. } => {
                let mut g = pc.j(self.eval(base));
                for (_, f) in fields {
                    g = g.j(self.eval(f));
                }
                g
            }
            TK::Repeat(x, _) => self.eval(x),
            TK::Block(stmts, tail) => {
                for s in stmts {
                    if self.st.dead {
                        return G::default();
                    }
                    match s {
                        TStmt::Let { pat, init, .. } => {
                            let g = match init {
                                Some(i) => self.eval(i),
                                None => G::default(),
                            };
                            if let Some(i) = init {
                                // closures and adapters carried by the new local
                                let cl = self.closures_in(i);
                                if let Some(l) = pat.is_irrefutable_bind() {
                                    if !cl.is_empty() {
                                        self.st.clos.insert(l, cl);
                                    }
                                    if let TK::Borrow(true, inner) = &i.kind {
                                        let (_, tt, a2) = self.place(inner);
                                        if let Some(tt) = tt {
                                            self.st.refs.insert(l, (tt, a2));
                                        }
                                    }
                                }
                            }
                            self.bind(pat, g);
                        }
                        TStmt::Expr(x) => {
                            self.eval(x);
                            if matches!(x.ty, Ty::Never) {
                                self.st.dead = true;
                            }
                        }
                    }
                }
                match tail {
                    Some(t) => self.eval(t),
                    None => pc,
                }
            }
            TK::If(c, t, el) => {
                let gc = self.eval(c);
                let base = self.pc();
                self.pc.push(base.j(gc.ctl()));
                let s0 = self.st.clone();
                let g1 = self.eval(t);
                let s1 = std::mem::replace(&mut self.st, s0);
                let g2 = match el {
                    Some(x) => self.eval(x),
                    None => G::default(),
                };
                let s2 = std::mem::replace(&mut self.st, s1.clone());
                self.pc.pop();
                self.join_states(s1, s2);
                g1.j(g2).j(gc.ctl())
            }
            TK::Match(s, arms) => {
                let gs = self.eval(s);
                let base = self.pc();
                self.pc.push(base.j(gs.ctl()));
                let s0 = self.st.clone();
                let mut acc: Option<St> = None;
                let mut g = gs.ctl();
                for a in arms {
                    self.st = s0.clone();
                    self.bind(&a.pat, gs);
                    self.bind_mut_refs(&a.pat, s);
                    if let Some(gd) = &a.guard {
                        let gg = self.eval(gd);
                        let p2 = self.pc().j(gg.ctl());
                        self.pc.push(p2);
                        g = g.j(self.eval(&a.body));
                        self.pc.pop();
                    } else {
                        g = g.j(self.eval(&a.body));
                    }
                    acc = Some(match acc {
                        None => self.st.clone(),
                        Some(prev) => {
                            let cur = self.st.clone();
                            self.join_states(prev, cur);
                            self.st.clone()
                        }
                    });
                }
                self.pc.pop();
                self.st = acc.unwrap_or(s0);
                g
            }
            TK::Loop(id, b) => {
                self.brk_vals.remove(id);
                self.eval_loop(*id, b, None, G::default());
                // the loop's value: what its breaks give, each under its own pc (F-85)
                pc.j(self.brk_vals.remove(id).unwrap_or_default())
            }
            TK::While(id, c, b) => {
                let id = *id;
                self.open_loops.push(id);
                // to the fixpoint: the grade lattice is finite and the state only grows, so this
                // ends; the bound is a safety net that widens (review 2026-10-16: a cap of 6
                // passes left long loop-carried chains too clean)
                let bound = loop_bound(&self.st);
                let mut stable = false;
                for _ in 0..bound {
                    let before = self.st.clone();
                    let gc = self.eval(c);
                    // leaving the loop is decided by the condition: J(L)
                    let j = self.jumps.get(&id).copied().unwrap_or_default().j(gc.ctl()).j(self.pc());
                    self.jumps.insert(id, j);
                    self.eval(b);
                    self.st.dead = false;
                    self.join_states(before.clone(), self.st.clone());
                    if same_state(&before, &self.st) {
                        stable = true;
                        break;
                    }
                }
                if !stable {
                    widen(&mut self.st);
                }
                self.open_loops.pop();
                self.jumps.remove(&id);
                pc
            }
            TK::For { id, iter, body, range, pat, par } => {
                let early = *par && {
                    let mut ex = false;
                    walk_deep(self.c, body, &mut |x| {
                        if matches!(x.kind, TK::Return(_) | TK::Try { .. }) {
                            ex = true;
                        }
                    });
                    ex
                };
                let gi = match range {
                    Some((lo, hi, _)) => {
                        let a = self.eval(lo);
                        let b = self.eval(hi);
                        a.j(b)
                    }
                    None => self.eval(iter),
                };
                // the iteration variable: index grades (bounds) or item grades (iterators)
                let item = if range.is_some() { gi.ctl().j(self.pc()) } else { gi.j(self.pc()) };
                self.bind(pat, item);
                if range.is_none() {
                    // a lazy adapter that stores a closure runs it here
                    for cid in self.closures_in(iter) {
                        self.apply_closure_writes(cid, &[gi, gi], gi);
                    }
                }
                self.eval_loop(*id, body, Some(gi.ctl()), gi);
                if early {
                    // T-Par (F-38): after an early return the written places hold schedule-
                    // dependent contents: γ_unspec joins them in the exit context X
                    let unspec = G { sd: true, raw: true, ..Default::default() };
                    let mut written: BTreeSet<LocalId> = BTreeSet::new();
                    walk_deep(self.c, body, &mut |x| {
                        if let TK::Assign(p, _) | TK::AssignOp(_, p, _) = &x.kind {
                            if let Some(r) = place_root(p) {
                                written.insert(r);
                            }
                        }
                    });
                    for w in written {
                        if self.st.mutref.contains_key(&w) {
                            let e = self.x.entry(w).or_default();
                            *e = e.j(unspec);
                        }
                        // inside a closure body: the closure's exit context (F-68, item N-54)
                        if let Some(cx) = &mut self.clo_x {
                            let e = cx.entry(w).or_default();
                            *e = e.j(unspec);
                        }
                    }
                }
                pc
            }
            TK::Break(id, v) => {
                if let Some(v) = v {
                    let g = self.eval(v).j(self.pc());
                    let e = self.brk_vals.entry(*id).or_default();
                    *e = e.j(g);
                }
                let j = self.jumps.get(id).copied().unwrap_or_default().j(self.pc());
                self.jumps.insert(*id, j);
                self.st.dead = true;
                G::default()
            }
            TK::Continue(id) => {
                let j = self.jumps.get(id).copied().unwrap_or_default().j(self.pc());
                self.jumps.insert(*id, j);
                self.st.dead = true;
                G::default()
            }
            TK::Return(v) => {
                let g = match v {
                    Some(v) => self.eval(v),
                    None => G::default(),
                };
                let pc = self.pc();
                self.rho = self.rho.j(g).j(pc);
                self.omega = self.omega.j(pc);
                self.jf = self.jf.j(pc);
                let muts: Vec<(LocalId, G)> = self.st.mutref.iter().map(|(k, v)| (*k, *v)).collect();
                for (k, v) in muts {
                    let e = self.x.entry(k).or_default();
                    *e = e.j(v);
                }
                self.record_clo_exit();
                self.st.dead = true;
                G::default()
            }
            TK::Try { e: inner, .. } => {
                let g = self.eval(inner);
                // the error path returns: an early exit decided by the value's discriminant
                let pc = self.pc();
                self.rho = self.rho.j(g.ctl()).j(pc);
                self.jf = self.jf.j(g.ctl()).j(pc);
                let muts: Vec<(LocalId, G)> = self.st.mutref.iter().map(|(k, v)| (*k, *v)).collect();
                for (k, v) in muts {
                    let e = self.x.entry(k).or_default();
                    *e = e.j(v);
                }
                self.record_clo_exit();
                g
            }
            TK::Det { body, .. } => {
                // T-Det: the result's schedule component is recomputed from the block's free inputs
                let g = self.eval(body);
                let mut sd_in = false;
                let mut free = BTreeSet::new();
                walk_deep(self.c, body, &mut |x| {
                    if let TK::Local(l) = x.kind {
                        free.insert(l);
                    }
                });
                for l in free {
                    if self.read_local(l).sd || self.st.mutref.get(&l).map(|m| m.sd).unwrap_or(false) {
                        sd_in = true;
                    }
                }
                let pc = self.pc();
                G { sd: sd_in, ..g }.j(pc.ctl())
            }
            TK::Trap(..) => {
                let pc = self.pc();
                self.omega = self.omega.j(pc);
                self.st.dead = true;
                G::default()
            }
            TK::Assert { cond, .. } => {
                let g = self.eval(cond);
                self.exit_site(e, g);
                pc
            }
            TK::AssertCmp { a, b, .. } => {
                let g = self.eval(a).j(self.eval(b));
                let pc = self.pc();
                self.omega = self.omega.j(pc).j(g.ctl());
                pc
            }
            TK::Format { args, .. } => {
                let mut g = pc;
                for a in args {
                    g = g.j(self.eval(a));
                }
                g.canon()
            }
            TK::Matches(s, _) | TK::LetCond(_, s) => {
                let g = self.eval(s);
                if let TK::LetCond(p, _) = &e.kind {
                    self.bind(p, g);
                    self.bind_mut_refs(p, s);
                }
                g.ctl().j(pc)
            }
            TK::Error => pc,
        }
    }

    fn eval_loop(&mut self, id: LoopId, body: &TExpr, guard: Option<G>, item: G) {
        self.open_loops.push(id);
        if let Some(g) = guard {
            // the guard's break: the bound's grade enters J(L) (F-30)
            let j = self.jumps.get(&id).copied().unwrap_or_default().j(g).j(self.pc());
            self.jumps.insert(id, j);
        }
        let covered = self.c.facts.covers.get(&(self.fid, id)).cloned().unwrap_or_default();
        let entry = self.st.clone();
        // to the fixpoint (finite lattice, growing state); the bound only guards it and widens
        let bound = loop_bound(&self.st);
        let mut stable = false;
        for _ in 0..bound {
            let before = self.st.clone();
            self.eval(body);
            self.st.dead = false;
            self.join_states(before.clone(), self.st.clone());
            if same_state(&before, &self.st) {
                stable = true;
                break;
            }
        }
        if !stable {
            widen(&mut self.st);
        }
        let _ = item;
        // T-Cover: a covering loop is a strong update of the covered place
        if !covered.is_empty() {
            let rhs = self.cover_rhs.get(&id).copied().or_else(|| {
                // a nested row cover: the inner loop's write
                self.c.facts.row_covers.iter().filter(|((f, _), _)| *f == self.fid).filter_map(|((_, l), _)| self.cover_rhs.get(l).copied()).next()
            });
            if let Some(rhs) = rhs {
                let pcl = self.pc();
                for root in covered {
                    let t = if self.st.mutref.contains_key(&root) { Target::MutRef(root) } else { Target::Local(root) };
                    let _ = &entry;
                    self.write(t, rhs.j(pcl), true);
                }
            }
        }
        self.open_loops.pop();
        // J(L) persists only inside the loop; what the loop wrote already carries it
        self.jumps.remove(&id);
    }

    fn join_states(&mut self, a: St, b: St) {
        if a.dead {
            self.st = b;
            return;
        }
        if b.dead {
            self.st = a;
            return;
        }
        let mut st = a.clone();
        for (k, v) in b.env {
            let e = st.env.entry(k).or_default();
            *e = e.j(v);
        }
        for (k, v) in b.mutref {
            let e = st.mutref.entry(k).or_default();
            *e = e.j(v);
        }
        for (k, v) in b.clos {
            st.clos.entry(k).or_default().extend(v);
        }
        for (k, v) in b.refs {
            st.refs.entry(k).or_insert(v);
        }
        st.dead = false;
        self.st = st;
    }

    fn eval_call(&mut self, fid: FnId, args: &[TExpr], e: &TExpr) -> G {
        let g = self.eval_call_inner(fid, args, e);
        // F-57: a hint value is graded γ_sh. At X1 a policy is called directly (no hint port,
        // §12), so the result of every call of a policy fn is a hint value [prov, mithi]
        if self.c.program.fns[fid as usize].kind == FnKind::Policy {
            return g.j(G::sh());
        }
        g
    }

    fn eval_call_inner(&mut self, fid: FnId, args: &[TExpr], e: &TExpr) -> G {
        let mut gs = vec![];
        for a in args {
            gs.push(self.eval(a));
        }
        let pc = self.pc();
        let f = &self.c.program.fns[fid as usize];
        let taint = self.row_taint(fid);
        if let Some(b) = f.builtin.clone() {
            let float = has_float(self.c, &e.ty);
            let mut base = taint;
            for g in &gs {
                base = base.j(g.ctl());
            }
            // closures run by the builtin
            let mut clo_ret = G::default();
            let item = gs.first().copied().unwrap_or_default();
            for (i, a) in args.iter().enumerate() {
                for cid in self.closures_in(a) {
                    let s = self.closure_summary(cid);
                    let params: Vec<G> = match b.as_str() {
                        "mutex_with_lock" => vec![G::sh()],
                        "slice_sort_by" | "iter_max_by" | "iter_min_by" => vec![item, item],
                        "iter_fold" => vec![gs.get(1).copied().unwrap_or_default(), item],
                        _ => vec![item, item],
                    };
                    if super::stdfacts::runs_closure(&b).is_some() || b == "mutex_with_lock" {
                        clo_ret = clo_ret.j(apply(s.ret, &params, self.clo_base));
                        self.apply_closure_writes(cid, &params, if b == "mutex_with_lock" { G::default() } else { item });
                    } else {
                        // stored or passed along: applied conservatively at this call
                        self.apply_closure_writes(cid, &params, item);
                    }
                    let _ = i;
                }
            }
            // a lazy adapter's next runs its stored closures
            if b == "iter_next" {
                if let Some(a0) = args.first() {
                    for cid in self.closures_in(a0) {
                        let s = self.closure_summary(cid);
                        clo_ret = clo_ret.j(apply(s.ret, &[item, item], self.clo_base));
                        self.apply_closure_writes(cid, &[item, item], item);
                    }
                }
            }
            let mut g = match b.as_str() {
                "mutex_with_lock" => clo_ret.j(taint).j(gs.first().copied().unwrap_or_default().ctl()),
                "slice_sort_by" | "slice_sort_by_key" => {
                    // θ_mut,self = α_self ⊔ Θ_f.θ_ret(α_item, α_item)
                    if let Some(a0) = args.first() {
                        if let TK::Borrow(true, p) = &a0.kind {
                            let (_, t, _) = self.place(p);
                            if let Some(t) = t {
                                let v = clo_ret.ctl().j(pc);
                                self.write(t, v, false);
                            }
                        }
                    }
                    base
                }
                _ => base.j(clo_ret),
            };
            // the NaN bit
            if float {
                match super::stdfacts::nanrule(&b) {
                    Some(true) => g = g.canon(),
                    Some(false) => g = g.rawed(),
                    None => {
                        for x in &gs {
                            g.raw |= x.raw;
                            g.nu |= x.nu;
                        }
                    }
                }
            } else {
                g = g.canon();
            }
            // observers
            if super::stdfacts::is_observer(&b) {
                for x in &gs {
                    if x.raw {
                        g.plat = true;
                    }
                    g.obs |= x.nu;
                }
            }
            // &mut arguments of builtins: read_at writes the buffer from file and offset
            for (i, a) in args.iter().enumerate() {
                if let TK::Borrow(true, p) = &a.kind {
                    if matches!(b.as_str(), "slice_sort_by" | "slice_sort_by_key") {
                        continue;
                    }
                    let (_, t, _) = self.place(p);
                    if let Some(t) = t {
                        let mut v = pc.j(taint);
                        for (k, x) in gs.iter().enumerate() {
                            if k != i {
                                v = v.j(x.ctl());
                            }
                        }
                        self.write(t, v, false);
                    }
                }
            }
            self.exit_site(e, base);
            return g.j(pc);
        }
        // user and prelude functions: summaries
        let r = match self.sums.get(&fid) {
            Some(s) => {
                let r = apply(s.ret, &gs, 0);
                let muts = s.muts.clone();
                for (pi, mg) in &muts {
                    if let Some(a) = args.get(*pi) {
                        let target = self.arg_target(a);
                        if let Some(t) = target {
                            let v = apply(*mg, &gs, 0).j(pc);
                            // F-78: an argument that lends a whole place (`&mut x`, `&mut *y` of a
                            // `&mut` parameter) is one place, so the callee's final referent grade
                            // (stated over its initial grade) replaces it: a strong update
                            let strong = self.lends_whole(a);
                            self.write(t, v, strong);
                        }
                    }
                }
                if s.may_trap {
                    let ex = apply(s.exit, &gs, 0);
                    self.omega = self.omega.j(pc).j(ex.ctl());
                }
                r
            }
            None => {
                // no summary (bodiless prelude signature or recursion): conservative
                let mut g = taint;
                for x in &gs {
                    g = g.j(*x);
                }
                if has_float(self.c, &e.ty) {
                    if f.kind == FnKind::Kernel {
                        g = g.canon();
                    } else {
                        g = g.rawed();
                    }
                } else {
                    g = g.canon();
                }
                g
            }
        };
        // closures passed to user functions: their returns and writes count here
        let mut r = r;
        for a in args {
            for cid in self.closures_in(a) {
                let s = self.closure_summary(cid);
                let all = gs.iter().fold(G::default(), |x, y| x.j(*y));
                r = r.j(apply(s.ret, &[all, all, all], self.clo_base).ctl());
                self.apply_closure_writes(cid, &[all, all, all], all);
            }
        }
        r.j(taint).j(pc)
    }
}

/// The local a write lands in: through fields, indexing, derefs and projection receivers.
fn write_root(c: &Checked, p: &TExpr) -> Option<LocalId> {
    match &p.kind {
        TK::Local(l) => Some(*l),
        TK::Field(b, _) | TK::Index(b, _) | TK::Unsize(b) | TK::Borrow(_, b) => write_root(c, b),
        TK::SliceRange { base, .. } => write_root(c, base),
        TK::Deref(b) => match &b.kind {
            TK::Call { args, .. } => args.first().and_then(|a| write_root(c, a)),
            _ => write_root(c, b),
        },
        _ => None,
    }
}

fn same_state(a: &St, b: &St) -> bool {
    a.env == b.env && a.mutref == b.mutref
}

/// More passes than the lattice has height over the state's entries (3 flags and 3 sets of at
/// most 64 symbols per entry), plus slack for entries created inside the loop.
fn loop_bound(st: &St) -> usize {
    (st.env.len() + st.mutref.len() + 8) * 200
}

/// The widening of last resort: every value top (schedule- and platform-dependent, raw).
fn widen(st: &mut St) {
    let top = G { sd: true, plat: true, raw: true, deps: u64::MAX, nu: u64::MAX, obs: 0 };
    for v in st.env.values_mut() {
        *v = v.j(top);
    }
    for v in st.mutref.values_mut() {
        *v = v.j(top);
    }
}

/// Analyse one function with symbolic parameter grades.
fn summarize(c: &Checked, fid: FnId, sums: &HashMap<FnId, Summary>) -> Option<(Summary, Vec<(LocalId, G)>, G, G)> {
    let body = c.bodies.get(&fid)?;
    let f = &c.program.fns[fid as usize];
    let mut st = St { env: HashMap::new(), mutref: HashMap::new(), clos: HashMap::new(), refs: HashMap::new(), dead: false };
    let policy = c.facts.ctx.get(&fid) == Some(&Ctx::TimingOnly) && f.kind == FnKind::Policy;
    for (i, pl) in body.params.iter().enumerate() {
        let ty = &body.locals[*pl as usize].ty;
        let float = has_float(c, ty);
        let mut g = G::param(i as u32, float);
        if policy {
            // views are snapshots of shared core state: γ_sh (section 5.13)
            g = g.j(G::sh());
        }
        st.env.insert(*pl, g);
        // `&mut` parameters, and by-value parameters that hold a `&mut` (F-62: their pseudo-place
        // `*j` is a write target the caller sees)
        if let Ty::Ref(true, _) = ty {
            st.mutref.insert(*pl, g);
        } else if holds_mut_ref(ty) {
            st.mutref.insert(*pl, g);
        }
    }
    let mut ga = Ga {
        c,
        fid,
        body,
        st,
        pc: vec![G::default()],
        jumps: HashMap::new(),
        jf: G::default(),
        omega: G::default(),
        rho: G::default(),
        x: HashMap::new(),
        sums,
        closums: HashMap::new(),
        clo_base: 40,
        cover_rhs: HashMap::new(),
        open_loops: vec![],
        brk_vals: HashMap::new(),
        clo_x: None,
    };
    let r = ga.eval(&body.expr);
    let dead = ga.st.dead;
    let ret = if dead { ga.rho } else { r.j(ga.rho).j(ga.jf) };
    let mut muts = vec![];
    let mut mut_finals = vec![];
    for (i, pl) in body.params.iter().enumerate() {
        if ga.st.mutref.contains_key(pl) || ga.x.contains_key(pl) {
            let mut g = if dead { G::default() } else { ga.st.mutref.get(pl).copied().unwrap_or_default() };
            if let Some(x) = ga.x.get(pl) {
                g = g.j(*x);
            }
            muts.push((i, g));
            mut_finals.push((*pl, g));
        }
    }
    let may_trap = c.facts.fns.get(&fid).map(|x| x.may_trap).unwrap_or(false);
    Some((Summary { ret, muts, exit: ga.omega, may_trap }, mut_finals, ret, ga.omega))
}

fn describe(g: &G) -> String {
    let scope = if g.sd {
        "schedule_dependent"
    } else if g.plat {
        "device(platform)"
    } else {
        "cross_device"
    };
    let nan = if g.raw { "raw" } else if g.nu != 0 { "pass(inputs)" } else { "canon" };
    format!("(exact, {scope}{}, ν={nan})", if g.deps != 0 { " if inputs are" } else { "" })
}

pub fn run(c: &mut Checked) {
    let fids: Vec<FnId> = {
        let mut v: Vec<FnId> = c.bodies.keys().copied().filter(|f| {
            let fd = &c.program.fns[*f as usize];
            fd.role != FileRole::Std && fd.body.is_some()
        }).collect();
        v.sort();
        v
    };
    // summaries to a fixpoint (callees first is not required: iterate)
    // until no summary changes (review 2026-10-16: four rounds made helper chains of depth five
    // or more, written callers first, depend on definition order); the cap is a safety net
    let mut sums: HashMap<FnId, Summary> = HashMap::new();
    for _round in 0..(4 * fids.len() + 8) {
        let mut changed = false;
        for &fid in &fids {
            if let Some((s, _, _, _)) = summarize(c, fid, &sums) {
                let old = sums.get(&fid).map(|o| (o.ret, o.exit, o.muts.clone()));
                if old != Some((s.ret, s.exit, s.muts.clone())) {
                    changed = true;
                }
                sums.insert(fid, s);
            }
        }
        if !changed {
            break;
        }
    }
    let mut diags = vec![];
    for &fid in &fids {
        let f = &c.program.fns[fid as usize];
        let Some((s, mut_finals, ret, omega)) = summarize(c, fid, &sums) else { continue };
        let grade_attr = super::ctx::has_grade_attr(c, fid);
        let is_sink = f.kind == FnKind::Kernel || matches!(&grade_attr, Some((_, d)) if d == "cross_device");
        let ff = c.facts.fns.entry(fid).or_default();
        ff.output = describe(&ret);
        if is_sink && f.role != FileRole::Std {
            let path = f.path.clone();
            let what = if f.kind == FnKind::Kernel { "a kernel output" } else { "a #[grade(exact, cross_device)] output" };
            let check = |g: G, float: bool, name: String, sp: Span, diags: &mut Vec<Diag>| {
                if g.sd || g.plat || g.obs != 0 {
                    let why = if g.sd { "schedule_dependent" } else { "device(platform): a raw NaN reaches an observer" };
                    diags.push(Diag::new("E-GRADE", sp, format!("{what} ({name}) must be cross_device, but it is {why} (01 section 13.6)")).in_def(&path));
                } else if float && (g.raw || g.nu != 0) {
                    diags.push(Diag::new("E-NAN-RAW-SINK", sp, format!("{what} ({name}) holds float content whose NaN bit is raw on some path: pass it through canon::nan (01 section 13.6; NUMERICS section 3)")).in_def(&path));
                }
            };
            let body = &c.bodies[&fid];
            if f.ret != Ty::Unit && f.ret != Ty::Never {
                check(ret, has_float(c, &f.ret), "the result".into(), f.sig_span, &mut diags);
            }
            for (pl, g) in mut_finals {
                let ty = body.locals[pl as usize].ty.clone();
                let nm = body.locals[pl as usize].name.clone();
                check(g, has_float(c, &ty), format!("`*{nm}`"), body.locals[pl as usize].span, &mut diags);
            }
            if omega.sd || omega.plat {
                diags.push(Diag::new("E-GRADE", f.sig_span, format!("{what}: the exit grade ω is not cross_device (an early exit or trap is decided by schedule-dependent state; Theorem 4)")).in_def(&path));
            }
            let _ = s;
        }
        // E-IMPL-GRADE: Θ_impl ⊑ Θ̂_m (the trait method's row-derived bound)
        if let Some((tr, _)) = owner_trait_impl(c, fid) {
            if c.program.traits[tr as usize].role != FileRole::Std {
                if let Some(decl) = c.program.traits[tr as usize].methods.get(&f.name) {
                    let trow = c.facts.rows.get(decl).cloned().unwrap_or_default();
                    let allow_sd = trow.contains(&Label::Nondet) || trow.contains(&Label::Time);
                    let allow_plat = trow.contains(&Label::NondetPlatform);
                    if (ret.sd && !allow_sd) || (ret.plat && !allow_plat) {
                        diags.push(Diag::new("E-IMPL-GRADE", f.sig_span, format!("impl method `{}` has a constant grade component {} that the trait method's row-derived bound does not allow (F-50); canonicalise before observing", f.name, describe(&ret))).in_def(&f.path));
                    }
                }
            }
        }
    }
    c.diags.extend(diags);
}

#[allow(dead_code)]
fn debug_g(g: &G) -> String {
    format!("{g:?}")
}
