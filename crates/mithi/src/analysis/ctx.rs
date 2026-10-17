//! Grade contexts (note section 5.3) and the context-dependent class codes of section 5.0:
//! FF-SUM, FF-TIES, FF-EXP, FF-POWI (Dc in exact context) and FF-CLOCK (Dc in exact and
//! timing_only contexts).

use super::stdfacts::{ff_class, FfClass};
use super::*;
use crate::diag::Diag;
use std::collections::{HashMap, HashSet};

fn has_grade_exact(c: &Checked, fid: FnId) -> bool {
    c.program.fns[fid as usize].attrs.iter().any(|a| a.name == "grade" && a.args.first().map(|x| x.trim() == "exact").unwrap_or(false))
}

pub fn has_grade_attr(c: &Checked, fid: FnId) -> Option<(String, String)> {
    let a = c.program.fns[fid as usize].attrs.iter().find(|a| a.name == "grade")?;
    Some((a.args.first().cloned().unwrap_or_default().trim().to_string(), a.args.get(1).cloned().unwrap_or_default().trim().to_string()))
}

pub fn run(c: &mut Checked) {
    let n = c.program.fns.len() as FnId;
    let mut calls: HashMap<FnId, Vec<FnId>> = HashMap::new();
    let mut callers: HashMap<FnId, HashSet<FnId>> = HashMap::new();
    for fid in 0..n {
        if c.program.fns[fid as usize].role == FileRole::Std {
            continue;
        }
        let cs: Vec<FnId> = callees(c, fid).into_iter().map(|x| x.0).collect();
        for &t in &cs {
            callers.entry(t).or_default().insert(fid);
        }
        calls.insert(fid, cs);
    }
    let mut exact: HashSet<FnId> = HashSet::new();
    let mut stack: Vec<FnId> = (0..n).filter(|f| c.program.fns[*f as usize].kind == FnKind::Kernel || has_grade_exact(c, *f)).collect();
    while let Some(f) = stack.pop() {
        if !exact.insert(f) {
            continue;
        }
        for &t in calls.get(&f).map(|v| v.as_slice()).unwrap_or(&[]) {
            if !exact.contains(&t) {
                stack.push(t);
            }
        }
    }
    // FF-CLOCK is Dc in kernels, policies and Forge candidates (01 section 2.5), not in every
    // exact-graded definition: the code reached from kernels, and timing_only code
    let mut kreach: HashSet<FnId> = HashSet::new();
    let mut stack2: Vec<FnId> = (0..n).filter(|f| c.program.fns[*f as usize].kind == FnKind::Kernel).collect();
    while let Some(f) = stack2.pop() {
        if !kreach.insert(f) {
            continue;
        }
        for &t in calls.get(&f).map(|v| v.as_slice()).unwrap_or(&[]) {
            stack2.push(t);
        }
    }
    let mut timing: HashSet<FnId> = (0..n).filter(|f| c.program.fns[*f as usize].kind == FnKind::Policy && !exact.contains(f)).collect();
    loop {
        let mut changed = false;
        for fid in 0..n {
            if timing.contains(&fid) || exact.contains(&fid) {
                continue;
            }
            if let Some(cs) = callers.get(&fid) {
                if !cs.is_empty() && cs.iter().all(|x| timing.contains(x)) {
                    timing.insert(fid);
                    changed = true;
                }
            }
        }
        if !changed {
            break;
        }
    }
    for fid in 0..n {
        let x = if exact.contains(&fid) {
            Ctx::Exact
        } else if timing.contains(&fid) {
            Ctx::TimingOnly
        } else {
            Ctx::Default
        };
        c.facts.ctx.insert(fid, x);
    }
    // the instantiations of generic user functions reached from exact code (F-53, (k5)): the
    // class check runs on each, with the type arguments substituted (review 2026-10-16: a float
    // fold inside a generic body was never seen)
    let mut insts: HashMap<FnId, Vec<Vec<Ty>>> = HashMap::new();
    let mut work: Vec<(FnId, Vec<Ty>)> = vec![];
    for &fid in &exact {
        if c.program.fns[fid as usize].generics.is_empty() {
            work.push((fid, vec![]));
        }
    }
    let mut seen: HashSet<(FnId, String)> = HashSet::new();
    while let Some((fid, s)) = work.pop() {
        if !seen.insert((fid, format!("{s:?}"))) || seen.len() > 4096 {
            continue;
        }
        if !s.is_empty() {
            insts.entry(fid).or_default().push(s.clone());
        }
        let Some(b) = c.bodies.get(&fid) else { continue };
        walk_deep(c, &b.expr, &mut |e| {
            if let TK::Call { f: g, substs, .. } = &e.kind {
                let gd = &c.program.fns[*g as usize];
                if gd.role != FileRole::Std && !gd.generics.is_empty() && c.bodies.contains_key(g) {
                    let t: Vec<Ty> = substs.iter().map(|x| x.subst(&s)).collect();
                    if t.iter().any(|x| !matches!(x, Ty::Param(_))) {
                        work.push((*g, t));
                    }
                }
            }
        });
    }
    // class codes
    let mut diags = vec![];
    let mut reported: HashSet<(String, Span)> = HashSet::new();
    let mut fids: Vec<FnId> = c.bodies.keys().copied().collect();
    fids.sort();
    for fid in &fids {
        let b = &c.bodies[fid];
        let f = &c.program.fns[*fid as usize];
        if f.role == FileRole::Std {
            continue;
        }
        let ctx = c.facts.ctx[fid];
        let path = f.path.clone();
        let mut views: Vec<Vec<Ty>> = vec![vec![]];
        views.extend(insts.get(fid).cloned().unwrap_or_default());
        for inst in &views {
        walk_deep(c, &b.expr, &mut |e| {
            let (callee, substs) = match &e.kind {
                TK::Call { f, substs, .. } => (*f, substs),
                _ => return,
            };
            let substs: &Vec<Ty> = &substs.iter().map(|t| if inst.is_empty() { t.clone() } else { t.subst(inst) }).collect();
            let ety = if inst.is_empty() { e.ty.clone() } else { e.ty.subst(inst) };
            let Some(bn) = builtin_name(c, callee) else { return };
            let Some(cls) = ff_class(bn) else { return };
            let cf = &c.program.fns[callee as usize];
            let float_in = |t: &Ty| {
                let mut h = false;
                t.walk(&mut |x| {
                    if matches!(x, Ty::F32 | Ty::F64) {
                        h = true
                    }
                });
                h
            };
            match cls {
                FfClass::Sum if ctx == Ctx::Exact => {
                    let float = match bn {
                        "iter_fold" => substs.get(cf.n_parent).map(|t| float_in(t)).unwrap_or(false),
                        _ => float_in(&ety),
                    };
                    if float && reported.insert(("E-FF-SUM".into(), e.span)) {
                        diags.push(Diag::new("E-FF-SUM", e.span, format!("float `{}` in exact context: a sequential left fold, but exact code names its reduction order (FF-SUM, DR-013); use canon::sum_seq (same bits) or canon::sum16", cf.name)).in_def(&path).note("context: exact (kernel fn or #[grade(exact, ..)] or called from one)"));
                    }
                }
                FfClass::Ties if ctx == Ctx::Exact => {
                    let item = substs.first().map(|s| super::wf::iter_item_of(c, s)).unwrap_or(Ty::Error);
                    if float_in(&item) && bn != "slice_sort_by" && reported.insert(("E-FF-TIES".into(), e.span)) {
                        diags.push(Diag::new("E-FF-TIES", e.span, format!("`{}` over floats in exact context: `max_by` returns the last maximum and f32 is not Ord (FF-TIES); use topk with an explicit tie and NaN rule", cf.name)).in_def(&path));
                    }
                }
                FfClass::Exp if ctx == Ctx::Exact && reported.insert(("E-FF-EXP".into(), e.span)) => {
                    diags.push(Diag::new("E-FF-EXP", e.span, format!("`{}` in exact code: platform precision is unspecified (FF-EXP, DR-014); name cr::expf or canon_v1::expf", cf.name)).in_def(&path));
                }
                FfClass::Powi if ctx == Ctx::Exact && reported.insert(("E-FF-POWI".into(), e.span)) => {
                    diags.push(Diag::new("E-FF-POWI", e.span, "`powi` in exact code: no particular rounding sequence is guaranteed (FF-POWI); write the multiplications in a fixed order").in_def(&path));
                }
                FfClass::Clock if (kreach.contains(fid) || ctx == Ctx::TimingOnly) && reported.insert(("E-FF-CLOCK".into(), e.span)) => {
                    let where_ = if kreach.contains(fid) { "a kernel" } else { "a timing_only policy" };
                    diags.push(Diag::new("E-FF-CLOCK", e.span, format!("a clock read in {where_}: forbidden in kernels, policies and Forge candidates (FF-CLOCK)")).in_def(&path));
                }
                _ => {}
            }
        });
        }
    }
    c.diags.extend(diags);
}
