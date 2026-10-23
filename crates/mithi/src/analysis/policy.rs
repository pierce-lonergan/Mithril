//! ⊢_to (note section 5.13): (t1) E-TO-ROW, (t2) E-TO-RESULT, (t3) E-TO-PARAM, (t5) E-TO-LOOP and
//! E-TO-RECURSION, (t6) E-TO-AUTHORITY, (t7) E-TO-CALL. (t8) allows may_trap; (t9) needs a port's
//! stack budget and is outside X1 (E-TO-STACK belongs to ⊢_store, M4).

use super::*;
use crate::diag::Diag;
use std::collections::{HashMap, HashSet};

fn is_view(c: &Checked, t: &Ty) -> bool {
    match t {
        Ty::Adt(a, _) => {
            let ad = &c.program.adts[*a as usize];
            ad.has_attr("view") && super::own::copy_ty(c, t)
        }
        _ => false,
    }
}

fn view_param(c: &Checked, t: &Ty) -> bool {
    match t {
        Ty::Ref(false, inner) => match &**inner {
            Ty::Slice(e) => is_view(c, e),
            x => is_view(c, x),
        },
        x => is_view(c, x),
    }
}

/// (t1), (t5), (t6), (t7) for a policy or a helper it calls; (t2), (t3) only for the policy.
/// Returns the failures of `fid` itself. For a helper (not the entry), the caller reports them as
/// one E-TO-CALL at its call site, with the helper's own failures as notes: (t7) says a callee
/// that fails ⊢_to apart from (t2) is E-TO-CALL (review 2026-10-23, po10: a helper's loop was
/// reported as E-TO-LOOP at the helper). Recursion is the exception: (t5)'s "no recursion" is a
/// property of the policy's whole call graph ((t9): "(t5) makes the call graph acyclic"), so a
/// cycle anywhere in it is E-TO-RECURSION, reported directly [prov, mithi].
fn check_to(c: &Checked, fid: FnId, is_entry: bool, memo: &mut HashMap<FnId, Vec<Diag>>, stack: &mut Vec<FnId>, direct: &mut Vec<Diag>) -> Vec<Diag> {
    let f = &c.program.fns[fid as usize];
    let path = f.path.clone();
    if stack.contains(&fid) {
        direct.push(Diag::new("E-TO-RECURSION", f.sig_span, "recursion in a timing_only policy (t5): fuel and stack must be statically bounded").in_def(&path));
        return vec![];
    }
    if !is_entry {
        if let Some(d) = memo.get(&fid) {
            return d.clone();
        }
    }
    let mut out: Vec<Diag> = vec![];
    let diags = &mut out;
    stack.push(fid);
    let row = c.facts.rows.get(&fid).cloned().unwrap_or_default();
    let ex = c.facts.fns.get(&fid).map(|x| x.exercised.clone()).unwrap_or_default();
    if !row.is_empty() || !ex.is_empty() {
        let mut all = row.clone();
        all.extend(ex);
        diags.push(Diag::new("E-TO-ROW", f.sig_span, format!("a timing_only policy has the empty row; `{}` uses {} (t1)", f.name, crate::program::row_text(&all))).in_def(&path));
    }
    if is_entry {
        let is_hint = matches!(&f.ret, Ty::Adt(a, _) if c.program.adts[*a as usize].lang.as_deref() == Some("Hint"));
        if !is_hint {
            diags.push(Diag::new("E-TO-RESULT", f.ret_ast.as_ref().map(|t| t.span).unwrap_or(f.sig_span), "a policy returns Hint<T> (t2): it can only suggest, and the core validates every hint").in_def(&path));
        }
        for p in &f.params {
            if !view_param(c, &p.ty) {
                diags.push(Diag::new("E-TO-PARAM", p.span, format!("policy parameter of type `{}`: parameters are core-provided #[view] types (Copy, payload-free) or slices of them (t3)", c.program.ty_name(&p.ty))).in_def(&path));
            }
        }
    }
    let Some(b) = c.bodies.get(&fid) else {
        stack.pop();
        if !is_entry {
            memo.insert(fid, out.clone());
        }
        return out;
    };
    let params: HashSet<LocalId> = b.params.iter().copied().collect();
    walk_deep(c, &b.expr, &mut |e| match &e.kind {
        TK::For { iter, range, .. } => {
            let const_range = match range {
                Some((lo, hi, _)) => matches!(lo.kind, TK::Lit(_)) && matches!(hi.kind, TK::Lit(_)),
                None => false,
            };
            let over_param = iterates_param(iter, &params);
            if !const_range && !over_param {
                diags.push(Diag::new("E-TO-LOOP", e.span, "a policy loops only over core-provided slices or constant ranges (t5)").in_def(&path));
            }
        }
        TK::While(..) | TK::Loop(..) => diags.push(Diag::new("E-TO-LOOP", e.span, "`while`/`loop` in a policy: loops only over core-provided slices or constant ranges (t5)").in_def(&path)),
        TK::Det { .. } => diags.push(Diag::new("E-TO-AUTHORITY", e.span, "a `deterministic` block in a policy (t6)").in_def(&path)),
        TK::Closure(cid) => {
            if c.closures[*cid as usize].is_move {
                diags.push(Diag::new("E-TO-AUTHORITY", e.span, "an escaping (move) closure in a policy (t6)").in_def(&path));
            }
        }
        _ => {}
    });
    for l in &b.locals {
        let mut bad = false;
        l.ty.walk(&mut |t| {
            if let Ty::Adt(a, _) = t {
                if matches!(c.program.adts[*a as usize].lang.as_deref(), Some("Mutex") | Some("BlobFile") | Some("Clock")) {
                    bad = true;
                }
            }
        });
        if bad {
            diags.push(Diag::new("E-TO-AUTHORITY", l.span, "a Mutex or a capability in a policy (t6)").in_def(&path));
        }
    }
    for (t, sp) in callees(c, fid) {
        let tf = &c.program.fns[t as usize];
        if tf.role == FileRole::Std {
            let r = c.facts.rows.get(&t).cloned().unwrap_or_default();
            if !r.is_empty() {
                diags.push(Diag::new("E-TO-CALL", sp, format!("`{}` has row {}: a policy calls only stateless std functions with row ∅ (t7)", tf.path, crate::program::row_text(&r))).in_def(&path));
            }
        } else {
            let sub = check_to(c, t, false, memo, stack, direct);
            if !sub.is_empty() {
                let mut d = Diag::new("E-TO-CALL", sp, format!("`{}` does not satisfy ⊢_to apart from (t2): a policy calls only helpers that do, or stateless std functions with row ∅ (t7)", tf.path)).in_def(&path);
                for x in &sub {
                    d = d.note(format!("{} in `{}`: {}", x.code, x.def.clone().unwrap_or_default(), x.msg));
                }
                diags.push(d);
            }
        }
    }
    stack.pop();
    if !is_entry {
        memo.insert(fid, out.clone());
    }
    out
}

fn iterates_param(e: &TExpr, params: &HashSet<LocalId>) -> bool {
    match &e.kind {
        TK::Local(l) => params.contains(l),
        TK::Call { args, .. } => args.first().map(|a| iterates_param(a, params)).unwrap_or(false),
        TK::Unsize(b) | TK::Borrow(_, b) | TK::Deref(b) => iterates_param(b, params),
        _ => false,
    }
}

pub fn run(c: &mut Checked) {
    let mut diags = vec![];
    let n = c.program.fns.len() as FnId;
    for fid in 0..n {
        let f = &c.program.fns[fid as usize];
        if f.kind != FnKind::Policy || f.role == FileRole::Std {
            continue;
        }
        let mut memo = HashMap::new();
        let mut stack = vec![];
        let mut direct = vec![];
        let own = check_to(c, fid, true, &mut memo, &mut stack, &mut direct);
        diags.extend(own);
        for d in direct {
            if !diags.iter().any(|x: &Diag| x.code == d.code && x.span == d.span) {
                diags.push(d);
            }
        }
    }
    c.diags.extend(diags);
}
