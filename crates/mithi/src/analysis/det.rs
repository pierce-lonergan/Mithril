//! T-Det's side conditions (note section 5.11): E-DET-GRANT, E-DET-POLICY, E-DET-EVIDENCE,
//! E-DET-RESULT. E-DET-STALE needs ledger hashes, which X1 fixtures do not carry yet: not checked.
//! At X1, evidence is a fixture (mith.toml `[evidence] fixtures`, or a prelude `evidence` item).
//! A fixture's subject names a definition whose entire body is the block, or the block's anchor
//! `<definition path>@det<k>` (the k-th `deterministic` block in the definition, from 0) [prov,
//! mithi: the anchor spelling is mithi's until 05 fixes anchors].

use super::wf::is_local;
use super::*;
use crate::check::Config;
use crate::diag::Diag;
use std::collections::{HashMap, HashSet};

pub fn run(c: &mut Checked, cfg: &Config) {
    // functions a policy reaches (E-DET-POLICY)
    let n = c.program.fns.len() as FnId;
    let mut reached: HashSet<FnId> = HashSet::new();
    let mut stack: Vec<FnId> = (0..n).filter(|f| c.program.fns[*f as usize].kind == FnKind::Policy).collect();
    let mut calls: HashMap<FnId, Vec<FnId>> = HashMap::new();
    while let Some(f) = stack.pop() {
        if !reached.insert(f) {
            continue;
        }
        let cs = calls.entry(f).or_insert_with(|| callees(c, f).into_iter().map(|x| x.0).collect()).clone();
        for t in cs {
            stack.push(t);
        }
    }
    let mut diags = vec![];
    for (fid, b) in &c.bodies {
        let f = &c.program.fns[*fid as usize];
        if f.role == FileRole::Std || f.body.is_none() {
            continue;
        }
        let path = f.path.clone();
        let mut dets: Vec<&TExpr> = vec![];
        walk_deep(c, &b.expr, &mut |e| {
            if let TK::Det { .. } = e.kind {
                dets.push(e);
            }
        });
        let whole_body = is_whole_body(&b.expr);
        for (k, e) in dets.iter().enumerate() {
            let TK::Det { evidence, body } = &e.kind else { continue };
            if !cfg.declare_deterministic.iter().any(|m| m == &f.module) {
                diags.push(Diag::new("E-DET-GRANT", e.span, format!("a `deterministic` block needs the DeclareDeterministic grant for module `{}` (mith.toml declare_deterministic names exact modules, 01 section 6.4)", if f.module.is_empty() { "<root>" } else { &f.module })).in_def(&path));
            }
            if f.kind == FnKind::Policy || reached.contains(fid) {
                diags.push(Diag::new("E-DET-POLICY", e.span, "a policy, or code a policy reaches, may not hold a `deterministic` block (01 section 6.4 rule 3)").in_def(&path));
            }
            let anchor = format!("{path}@det{k}");
            let evs: Vec<&crate::program::Evidence> = c.program.evidences.iter().filter(|x| &x.name == evidence).collect();
            let ev = evs.iter().find(|x| x.subject == anchor || (whole_body && dets.len() == 1 && x.subject == path)).or(evs.first()).copied();
            match ev {
                None => diags.push(Diag::new("E-DET-EVIDENCE", e.span, format!("evidence `{evidence}` is not admitted (no fixture or ledger fact)")).in_def(&path)),
                Some(ev) => {
                    let about_block = ev.subject == anchor || (whole_body && dets.len() == 1 && ev.subject == path);
                    if ev.kind != "deterministic" {
                        diags.push(Diag::new("E-DET-EVIDENCE", e.span, format!("evidence `{evidence}` is of kind `{}`, not `deterministic`", ev.kind)).in_def(&path));
                    } else if !about_block {
                        diags.push(Diag::new("E-DET-EVIDENCE", e.span, format!("evidence `{evidence}` is about `{}`, not about this block (`{anchor}`; F-33: evidence about another definition does not cover it)", ev.subject)).in_def(&path));
                    }
                }
            }
            let mut has_closure = false;
            body.ty.walk(&mut |t| {
                if matches!(t, Ty::Closure(_) | Ty::FnPtr(..)) {
                    has_closure = true;
                }
            });
            if has_closure || is_local(c, &body.ty) {
                diags.push(Diag::new("E-DET-RESULT", e.span, "a `deterministic` block's result may contain no closure and may not be Local: it would run or borrow nondeterministic state after the block (F-34)").in_def(&path));
            }
        }
    }
    c.diags.extend(diags);
}

/// Is the definition's entire body one `deterministic` block?
fn is_whole_body(e: &TExpr) -> bool {
    match &e.kind {
        TK::Det { .. } => true,
        TK::Block(stmts, Some(t)) if stmts.is_empty() => is_whole_body(t),
        _ => false,
    }
}
