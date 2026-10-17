//! The MCore analyses of docs/m0/core-calculus.md section 5, run on checked THIR.
//!
//! Order: J2 well-formedness and kinds (wf), rows (rows), grade contexts and class codes (ctx),
//! obligations and T2 (t2), kernels (kernel), ownership and loans (own), par (par), the deterministic
//! boundary (det), policies (policy), grades and sinks (grade), schedules (sched), specs (spec).

pub mod ctx;
pub mod det;
pub mod grade;
pub mod kernel;
pub mod own;
pub mod par;
pub mod policy;
pub mod rows;
pub mod sched;
pub mod spec;
pub mod stdfacts;
pub mod t2;
pub mod wf;

use crate::ast::FnKind;
use crate::check::{Checked, Config};
use crate::diag::{json_escape, FileRole, Span};
use crate::program::{Owner, Row};
use crate::thir::*;
use crate::types::*;
use std::collections::{BTreeMap, BTreeSet};

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum Ctx {
    Default,
    TimingOnly,
    Exact,
}

#[derive(Default, Debug, Clone)]
pub struct FnFacts {
    pub row: Row,
    pub exercised: Row,
    pub may_trap: bool,
    pub trap_sites: Vec<String>,
    pub kcall: bool,
    pub output: String,
}

#[derive(Default, Debug, Clone)]
pub struct Facts {
    pub ctx: BTreeMap<FnId, Ctx>,
    pub fns: BTreeMap<FnId, FnFacts>,
    /// per (function, loop id): places covered by T-Cover (by root local)
    pub covers: BTreeMap<(FnId, LoopId), Vec<LocalId>>,
    /// per (function, loop id): a loop that covers a footprinted row of a `&mut` parameter
    pub row_covers: BTreeMap<(FnId, LoopId), LocalId>,
    pub format_sizes: Vec<(String, Option<u64>)>,
    pub schedules: Vec<(String, Vec<(String, String)>)>,
    /// declared or inferred rows of every function (rows pass)
    pub rows: std::collections::HashMap<FnId, Row>,
    /// exercised rows (F-36, F-71: det blocks do not remove nondet; callees' exercised rows count)
    pub ex_rows: std::collections::HashMap<FnId, Row>,
    /// undischarged trap sites (t2), for the exit grade ω
    pub undischarged: std::collections::HashSet<(FnId, Span)>,
}

impl Facts {
    pub fn to_json(&self, c: &Checked) -> String {
        let mut s = String::from("{\"functions\":[");
        let mut first = true;
        for (fid, ff) in &self.fns {
            let f = &c.program.fns[*fid as usize];
            if f.role != FileRole::User {
                continue;
            }
            if !first {
                s.push(',');
            }
            first = false;
            let ctx = match self.ctx.get(fid) {
                Some(Ctx::Exact) => "exact",
                Some(Ctx::TimingOnly) => "timing_only",
                _ => "default",
            };
            let kind = match f.kind {
                FnKind::Kernel => "kernel",
                FnKind::Policy => "policy",
                FnKind::Plain => "fn",
            };
            s.push_str(&format!(
                "{{\"path\":\"{}\",\"kind\":\"{}\",\"ctx\":\"{}\",\"row\":[{}],\"may_trap\":{},\"trap_sites\":[{}],\"kcall\":{},\"output\":\"{}\"}}",
                json_escape(&f.path),
                kind,
                ctx,
                ff.row.iter().map(|l| format!("\"{}\"", l.text())).collect::<Vec<_>>().join(","),
                ff.may_trap,
                ff.trap_sites.iter().map(|t| format!("\"{}\"", json_escape(t))).collect::<Vec<_>>().join(","),
                ff.kcall,
                json_escape(&ff.output)
            ));
        }
        s.push_str("],\"formats\":[");
        for (i, (n, sz)) in self.format_sizes.iter().enumerate() {
            if i > 0 {
                s.push(',');
            }
            s.push_str(&format!("{{\"name\":\"{}\",\"size\":{}}}", json_escape(n), sz.map(|x| x.to_string()).unwrap_or("null".into())));
        }
        s.push_str("],\"schedules\":[");
        for (i, (n, lic)) in self.schedules.iter().enumerate() {
            if i > 0 {
                s.push(',');
            }
            s.push_str(&format!(
                "{{\"name\":\"{}\",\"licences\":{{{}}}}}",
                json_escape(n),
                lic.iter().map(|(a, b)| format!("\"{}\":\"{}\"", json_escape(a), json_escape(b))).collect::<Vec<_>>().join(",")
            ));
        }
        s.push_str("]}");
        s
    }
}

pub fn run(c: &mut Checked, cfg: &Config) {
    if cfg.subset == crate::check::Subset::Agent {
        wf::agent_subset(c);
    }
    // MITHI_TIME=1 prints the time each pass takes (to stderr)
    let timed = std::env::var_os("MITHI_TIME").is_some();
    let mut t = std::time::Instant::now();
    let mut lap = |name: &str| {
        if timed {
            eprintln!("mithi: {name} {:.3} s", t.elapsed().as_secs_f64());
            t = std::time::Instant::now();
        }
    };
    wf::run(c, cfg);
    lap("wf");
    rows::run(c, cfg);
    lap("rows");
    ctx::run(c);
    lap("ctx");
    t2::run(c);
    lap("t2");
    kernel::run(c);
    lap("kernel");
    own::run(c);
    lap("own");
    par::run(c);
    lap("par");
    det::run(c, cfg);
    lap("det");
    policy::run(c);
    lap("policy");
    grade::run(c);
    lap("grade");
    sched::run(c);
    spec::run(c);
    lap("sched+spec");
    for f in &c.program.formats {
        c.facts.format_sizes.push((f.decl.name.name.clone(), f.size));
    }
}

// ---------------------------------------------------------------- shared helpers

/// Walk an expression, entering the bodies of closures created in it.
pub fn walk_deep<'a>(c: &'a Checked, e: &'a TExpr, f: &mut dyn FnMut(&'a TExpr)) {
    f(e);
    if let TK::Closure(cid) = &e.kind {
        if let Some(cd) = c.closures.get(*cid as usize) {
            walk_deep(c, &cd.body, f);
        }
    }
    for ch in e.children() {
        walk_deep(c, ch, f);
    }
}

/// The concrete function a call node invokes, if known statically.
pub fn call_target(c: &Checked, e: &TExpr) -> Option<FnId> {
    match &e.kind {
        TK::Call { f, .. } => Some(*f),
        TK::TraitCall { tr, method, self_ty, decl, .. } => {
            if matches!(self_ty, Ty::Param(_) | Ty::Infer(_) | Ty::Opaque(_)) {
                return Some(*decl);
            }
            resolve_impl_method(c, *tr, self_ty, method).or(Some(*decl))
        }
        _ => None,
    }
}

pub fn resolve_impl_method(c: &Checked, tr: TraitId, self_ty: &Ty, method: &str) -> Option<FnId> {
    let impls = c.program.impls_of_trait.get(&tr)?;
    for iid in impls {
        let im = &c.program.impls[*iid as usize];
        if let Some(fid) = im.methods.get(method) {
            if ty_matches(&im.self_ty, self_ty) {
                return Some(*fid);
            }
        }
    }
    None
}

/// Structural match of an impl self type (with parameters) against a concrete type.
pub fn ty_matches(pat: &Ty, t: &Ty) -> bool {
    match (pat, t) {
        (Ty::Param(_), _) => true,
        (Ty::Adt(a, xs), Ty::Adt(b, ys)) => a == b && xs.len() == ys.len() && xs.iter().zip(ys).all(|(x, y)| ty_matches(x, y)),
        (Ty::Ref(m1, x), Ty::Ref(m2, y)) => m1 == m2 && ty_matches(x, y),
        (Ty::Slice(x), Ty::Slice(y)) => ty_matches(x, y),
        (Ty::Array(x, n), Ty::Array(y, m)) => ty_matches(x, y) && ty_matches(n, m),
        (Ty::Tuple(x), Ty::Tuple(y)) => x.len() == y.len() && x.iter().zip(y).all(|(a, b)| ty_matches(a, b)),
        (a, b) => a == b,
    }
}

/// Direct callees of a function (calls in its body and in closures created there).
pub fn callees(c: &Checked, fid: FnId) -> Vec<(FnId, Span)> {
    let mut out = vec![];
    if let Some(b) = c.bodies.get(&fid) {
        walk_deep(c, &b.expr, &mut |e| {
            if let Some(t) = call_target(c, e) {
                out.push((t, e.span));
            }
        });
    }
    out
}

pub fn fn_path(c: &Checked, fid: FnId) -> String {
    c.program.fns.get(fid as usize).map(|f| f.path.clone()).unwrap_or_default()
}

pub fn is_user_or_prelude(c: &Checked, fid: FnId) -> bool {
    c.program.fns[fid as usize].role != FileRole::Std
}

pub fn builtin_name(c: &Checked, fid: FnId) -> Option<&str> {
    c.program.fns.get(fid as usize).and_then(|f| f.builtin.as_deref())
}

/// The local a place expression is rooted in (through fields, indexing and derefs of locals).
pub fn place_root(e: &TExpr) -> Option<LocalId> {
    match &e.kind {
        TK::Local(l) => Some(*l),
        TK::Field(b, _) | TK::Index(b, _) | TK::Deref(b) | TK::Unsize(b) | TK::Borrow(_, b) => place_root(b),
        TK::SliceRange { base, .. } => place_root(base),
        _ => None,
    }
}

pub fn label_set(ls: &[crate::program::Label]) -> Row {
    ls.iter().cloned().collect()
}

pub fn owner_trait_impl(c: &Checked, fid: FnId) -> Option<(TraitId, ImplId)> {
    match c.program.fns[fid as usize].owner {
        Owner::Impl(i) => c.program.impls[i as usize].trait_.as_ref().map(|(t, _)| (*t, i)),
        _ => None,
    }
}

pub fn set_of<T: Ord + Clone>(v: &[T]) -> BTreeSet<T> {
    v.iter().cloned().collect()
}
