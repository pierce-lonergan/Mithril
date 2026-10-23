//! Rows (note section 5.2): declared and inferred rows, E-ROW-UNDECLARED, grants, the charged row
//! and the exercised row (F-36).

use super::*;
use crate::diag::Diag;
use crate::program::Label;
use std::collections::HashMap;

/// The declared row of a function, if it has one (a `uses` clause, or a `pub fn` or trait method
/// without one, which declares ∅: F-22).
pub fn declared_row(c: &Checked, fid: FnId) -> Option<Row> {
    let f = &c.program.fns[fid as usize];
    if let Some(u) = &f.uses {
        return Some(u.clone());
    }
    if f.builtin.is_some() || f.role == FileRole::Std || f.body.is_none() || f.is_pub || matches!(f.owner, Owner::Trait(_)) {
        return Some(Row::new());
    }
    None
}

/// Labels an expression uses. `charged`: nondet removed inside det blocks (the charged row);
/// otherwise the exercised row. Sites: the first span per label.
pub fn expr_labels(c: &Checked, rows: &HashMap<FnId, Row>, e: &TExpr, charged: bool, out: &mut Vec<(Label, Span)>) {
    match &e.kind {
        TK::Det { body, .. } => {
            let mut inner = vec![];
            expr_labels(c, rows, body, charged, &mut inner);
            for (l, sp) in inner {
                if charged && l == Label::Nondet {
                    continue;
                }
                out.push((l, sp));
            }
            return;
        }
        TK::Closure(cid) => {
            // the row of a closure body is charged where the closure is created (Effekt-style)
            if let Some(cd) = c.closures.get(*cid as usize) {
                expr_labels(c, rows, &cd.body, charged, out);
            }
        }
        _ => {}
    }
    if let Some(t) = call_target(c, e) {
        if let Some(r) = rows.get(&t) {
            for l in r {
                out.push((l.clone(), e.span));
            }
        }
        // C-ALLOC: cloning a Vec, String or Buf allocates (the `clone` builtin serves every
        // Clone type, so its row is decided by the type cloned)
        if c.program.fns[t as usize].builtin.as_deref() == Some("clone") && mentions_heap(c, &e.ty) {
            out.push((Label::Alloc("Global".into()), e.span));
        }
    }
    match &e.kind {
        // `format!` builds a String (C-ALLOC)
        TK::Format { .. } => out.push((Label::Alloc("Global".into()), e.span)),
        // a function used as a value: its row is charged where it is referenced, since calling
        // the value later charges nothing (review 2026-10-16: `let g = h; g(c)` laundered h's row)
        TK::FnRef(fid, _) => {
            if let Some(r) = rows.get(fid) {
                for l in r {
                    out.push((l.clone(), e.span));
                }
            }
        }
        _ => {}
    }
    for ch in e.children() {
        expr_labels(c, rows, ch, charged, out);
    }
}

/// A type whose values own heap storage from `Global` (Vec, String, Buf), at any depth.
fn mentions_heap(c: &Checked, t: &Ty) -> bool {
    let mut h = false;
    t.walk(&mut |x| {
        if let Ty::Adt(a, _) = x {
            if matches!(c.program.adts[*a as usize].lang.as_deref(), Some("Vec") | Some("String") | Some("Buf")) {
                h = true;
            }
        }
    });
    h
}

pub fn row_of(out: &[(Label, Span)]) -> Row {
    out.iter().map(|(l, _)| l.clone()).collect()
}

pub fn run(c: &mut Checked, cfg: &Config) {
    let n = c.program.fns.len();
    let mut rows: HashMap<FnId, Row> = HashMap::new();
    for fid in 0..n as FnId {
        rows.insert(fid, declared_row(c, fid).unwrap_or_default());
    }
    // least fixpoint for inferred rows
    loop {
        let mut changed = false;
        for fid in 0..n as FnId {
            if declared_row(c, fid).is_some() {
                continue;
            }
            let Some(b) = c.bodies.get(&fid) else { continue };
            let mut out = vec![];
            expr_labels(c, &rows, &b.expr, true, &mut out);
            let r = row_of(&out);
            if &r != rows.get(&fid).unwrap() {
                rows.insert(fid, r);
                changed = true;
            }
        }
        if !changed {
            break;
        }
    }
    // exercised rows (F-36, F-71): nondet under a det block stays, and a callee contributes its
    // own exercised row, transitively (a least fixpoint)
    let mut ex: HashMap<FnId, Row> = rows.clone();
    loop {
        let mut changed = false;
        for fid in 0..n as FnId {
            let Some(b) = c.bodies.get(&fid) else { continue };
            let mut out = vec![];
            expr_labels(c, &ex, &b.expr, false, &mut out);
            let mut r = row_of(&out);
            r.extend(rows[&fid].iter().cloned());
            if &r != ex.get(&fid).unwrap() {
                ex.insert(fid, r);
                changed = true;
            }
        }
        if !changed {
            break;
        }
    }
    // checks
    let mut diags = vec![];
    for fid in 0..n as FnId {
        let f = &c.program.fns[fid as usize];
        if f.role == FileRole::Std {
            continue;
        }
        let Some(b) = c.bodies.get(&fid) else {
            let ff = c.facts.fns.entry(fid).or_default();
            ff.row = rows[&fid].clone();
            ff.exercised = rows[&fid].clone();
            continue;
        };
        let mut charged = vec![];
        expr_labels(c, &rows, &b.expr, true, &mut charged);
        let mut exercised = vec![];
        expr_labels(c, &rows, &b.expr, false, &mut exercised);
        // contracts are evaluated too (calls in requires/ensures)
        for e in b.requires.iter().chain(b.ensures.iter()) {
            expr_labels(c, &rows, e, true, &mut charged);
        }
        if let Some(decl) = declared_row(c, fid) {
            let mut reported = std::collections::BTreeSet::new();
            for (l, sp) in &charged {
                if !decl.contains(l) && reported.insert(l.clone()) {
                    let why = if f.uses.is_none() { " (a `pub fn` without `uses` declares the empty row, F-22)" } else { "" };
                    diags.push(Diag::new("E-ROW-UNDECLARED", *sp, format!("`{}` uses `{}` but its row {} does not declare it{why}", f.name, l.text(), crate::program::row_text(&decl))).in_def(&f.path));
                }
            }
        }
        // grants (J3)
        let module = f.module.clone();
        for (l, sp) in &charged {
            match l {
                Label::Unsafe if !cfg.grant_unsafe.contains(&module) => diags.push(Diag::new("E-GRANT-UNSAFE", *sp, "`unsafe` needs the package grant (FF-UNSAFE)").in_def(&f.path)),
                Label::Foreign if !cfg.grant_foreign.contains(&module) => diags.push(Diag::new("E-GRANT-FOREIGN", *sp, "`foreign` needs the package grant").in_def(&f.path)),
                Label::FpEnv => diags.push(Diag::new("E-FP-ENV", *sp, "`fp_env` is reserved to std_platform's audited runtime").in_def(&f.path)),
                _ => {}
            }
        }
        if let Some(u) = &f.uses {
            for l in u {
                match l {
                    // J3 applies to the declared row ε_g too (review 2026-10-23: a declared
                    // `uses { foreign }` without a grant was accepted); a charged label of the same
                    // kind is reported above, so the declared one is reported only when nothing
                    // in the body charges it
                    Label::Unsafe if !cfg.grant_unsafe.contains(&module) && !charged.iter().any(|(x, _)| x == l) => diags.push(Diag::new("E-GRANT-UNSAFE", f.sig_span, "`uses { unsafe }` needs the package grant (FF-UNSAFE; J3 on the declared row)").in_def(&f.path)),
                    Label::Foreign if !cfg.grant_foreign.contains(&module) && !charged.iter().any(|(x, _)| x == l) => diags.push(Diag::new("E-GRANT-FOREIGN", f.sig_span, "`uses { foreign }` needs the package grant (J3 on the declared row)").in_def(&f.path)),
                    Label::FpEnv =>diags.push(Diag::new("E-FP-ENV", f.sig_span, "`fp_env` is reserved to std_platform's audited runtime (01 section 6.1)").in_def(&f.path)),
                    Label::Lossy => diags.push(Diag::new("E-GRANT-LOSSY", f.sig_span, "`lossy` has no producer in v0 (reserved; note section 5.2)").in_def(&f.path)),
                    _ => {}
                }
            }
        }
        // impl rows within the trait's declared row (E-IMPL-ROW)
        if let Some((tr, _iid)) = owner_trait_impl(c, fid) {
            if let Some(decl) = c.program.traits[tr as usize].methods.get(&f.name) {
                let trow = declared_row(c, *decl).unwrap_or_default();
                let mine = rows[&fid].clone();
                for l in &mine {
                    if !trow.contains(l) {
                        diags.push(Diag::new("E-IMPL-ROW", f.sig_span, format!("impl method `{}` uses `{}`, outside the trait method's row {}", f.name, l.text(), crate::program::row_text(&trow))).in_def(&f.path));
                    }
                }
            }
        }
        let _ = &exercised;
        let ff = c.facts.fns.entry(fid).or_default();
        ff.row = rows[&fid].clone();
        ff.exercised = ex[&fid].clone();
    }
    c.diags.extend(diags);
    c.facts.rows = rows;
    c.facts.ex_rows = ex;
}
