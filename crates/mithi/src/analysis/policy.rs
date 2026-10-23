//! ⊢_to (note section 5.13): (t1) E-TO-ROW, (t2) E-TO-RESULT, (t3) E-TO-PARAM, (t5) E-TO-LOOP and
//! E-TO-RECURSION, (t6) E-TO-AUTHORITY, (t7) E-TO-CALL. (t8) allows may_trap; (t9) needs a port's
//! stack budget and is outside X1 (E-TO-STACK belongs to ⊢_store, M4). (t5) and (t6) follow the
//! note's F-118 (round-3 sync, 2026-10-23): ranges bounded by constants or by the length of a
//! core-provided slice parameter, and "escaping" as outliving the port call.

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
        // (t6), the extent reading (note F-118): a closure or function value in the policy's
        // result would outlive the port call; at X1 there is no port state, so the result is the
        // only way out of the call
        // The scan goes through the fields of user structs and enums too, with their type
        // arguments substituted: review of the round-3 sync (2026-10-23, finding 8, probe E5),
        // `struct W { f: fn() -> u32 }` returned as `Hint<W>` was accepted while the Option and
        // tuple forms were rejected
        if holds_fn_value(c, &f.ret, 0) {
            diags.push(Diag::new("E-TO-AUTHORITY", f.ret_ast.as_ref().map(|t| t.span).unwrap_or(f.sig_span), "a closure or function value in a policy's result escapes the port call (t6)").in_def(&path));
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
    // parameters of core-provided slice type (`&[V]`, V a #[view]): `s.len()` bounds a range (t5)
    let view_slices: HashSet<LocalId> = b
        .params
        .iter()
        .copied()
        .filter(|l| matches!(&b.locals[*l as usize].ty, Ty::Ref(false, inner) if matches!(&**inner, Ty::Slice(e) if is_view(c, e))))
        .collect();
    walk_deep(c, &b.expr, &mut |e| match &e.kind {
        TK::For { iter, range, .. } => {
            // (t5) as pinned by note F-118: each bound of a range is an integer literal, a `const`
            // item, or `s.len()` for a parameter s of core-provided slice type
            let bounded_range = match range {
                Some((lo, hi, _)) => range_bound(c, lo, &view_slices) && range_bound(c, hi, &view_slices),
                None => false,
            };
            let over_param = iterates_param(iter, &params);
            if !bounded_range && !over_param {
                diags.push(Diag::new("E-TO-LOOP", e.span, "a policy loops only over core-provided slices, or over ranges whose bounds are constants or the length of a core-provided slice parameter (t5)").in_def(&path));
            }
        }
        TK::While(..) | TK::Loop(..) => diags.push(Diag::new("E-TO-LOOP", e.span, "`while`/`loop` in a policy: loops only over core-provided slices, or over ranges whose bounds are constants or the length of a core-provided slice parameter (t5)").in_def(&path)),
        TK::Det { .. } => diags.push(Diag::new("E-TO-AUTHORITY", e.span, "a `deterministic` block in a policy (t6)").in_def(&path)),
        // (t6) "no escaping closure" means no closure value outlives the port call (note F-118):
        // closures of either kind may be created and called inside the policy; the entry's
        // result type is checked above. Before 2026-10-23 (round-3 sync) every `move` closure
        // was E-TO-AUTHORITY here (review 2026-10-23, finding 17, probe po11)
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

/// A range bound (t5) allows: an integer literal, a `const` item (possibly cast), or `s.len()` for
/// a parameter s of core-provided slice type. Static fuel is then a polynomial in view lengths
/// (note section 5.13).
fn range_bound(c: &Checked, e: &TExpr, view_slices: &HashSet<LocalId>) -> bool {
    match &e.kind {
        TK::Lit(_) | TK::Const(_) => true,
        TK::Cast(b) => range_bound(c, b, view_slices),
        TK::Call { f, args, .. } => {
            let fd = &c.program.fns[*f as usize];
            fd.role == FileRole::Std && fd.name == "len" && args.len() == 1 && roots_in(&args[0], view_slices)
        }
        _ => false,
    }
}

fn roots_in(e: &TExpr, set: &HashSet<LocalId>) -> bool {
    match &e.kind {
        TK::Local(l) => set.contains(l),
        TK::Unsize(b) | TK::Borrow(_, b) | TK::Deref(b) => roots_in(b, set),
        _ => false,
    }
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

/// Does a value of type t contain a closure or a function value, through tuples, arrays,
/// references, std generics and the fields of user ADTs (with substitution)? (t6)
fn holds_fn_value(c: &Checked, t: &Ty, depth: u32) -> bool {
    let mut seen: Vec<(crate::types::AdtId, Vec<Ty>)> = vec![];
    holds_fn_value_in(c, t, depth, &mut seen)
}

fn holds_fn_value_in(c: &Checked, t: &Ty, depth: u32, seen: &mut Vec<(crate::types::AdtId, Vec<Ty>)>) -> bool {
    if depth > 16 {
        return false;
    }
    let mut found = false;
    let mut adts: Vec<(crate::types::AdtId, Vec<Ty>)> = vec![];
    t.walk(&mut |x| match x {
        Ty::Closure(_) | Ty::Opaque(_) | Ty::FnPtr(..) => found = true,
        Ty::Adt(a, xs) => adts.push((*a, xs.clone())),
        _ => {}
    });
    if found {
        return true;
    }
    for key in adts {
        if seen.contains(&key) {
            continue;
        }
        seen.push(key.clone());
        let ad = &c.program.adts[key.0 as usize];
        for v in &ad.variants {
            for fl in &v.fields {
                if holds_fn_value_in(c, &fl.ty.subst(&key.1), depth + 1, seen) {
                    return true;
                }
            }
        }
    }
    false
}
