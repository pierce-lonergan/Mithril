//! ⊢_k and kcall (note section 5.10): (k1) row, (k3) callees, (k6) no det block, no Mutex, no
//! capability. (k2) is decided in t2, (k4) in grade, (k5) in ctx.

use super::*;
use crate::diag::Diag;
use std::collections::HashSet;

fn is_capability(c: &Checked, t: &Ty) -> bool {
    let mut hit = false;
    t.walk(&mut |x| {
        if let Ty::Adt(a, _) = x {
            if matches!(c.program.adts[*a as usize].lang.as_deref(), Some("BlobFile") | Some("Clock") | Some("Mutex")) {
                hit = true;
            }
        }
    });
    hit
}

/// Local conditions of kcall: not a kernel, row ∅, may_trap false, (k6).
fn kcall_local(c: &Checked, fid: FnId) -> bool {
    let f = &c.program.fns[fid as usize];
    if f.kind == FnKind::Kernel || f.body.is_none() || f.builtin.is_some() {
        return false;
    }
    if !c.facts.rows.get(&fid).map(|r| r.is_empty()).unwrap_or(false) {
        return false;
    }
    if c.facts.fns.get(&fid).map(|x| x.may_trap).unwrap_or(true) {
        return false;
    }
    if f.params.iter().any(|p| is_capability(c, &p.ty)) {
        return false;
    }
    let Some(b) = c.bodies.get(&fid) else { return false };
    let mut ok = true;
    walk_deep(c, &b.expr, &mut |e| {
        if let TK::Det { .. } = e.kind {
            ok = false;
        }
    });
    ok
}

fn admissible_std(c: &Checked, fid: FnId) -> bool {
    let f = &c.program.fns[fid as usize];
    f.has_attr("exact_std") || f.synthetic.as_deref() == Some("format_accessor") || f.has_attr("format_accessor") || f.has_attr("kcall")
}

pub fn run(c: &mut Checked) {
    let n = c.program.fns.len() as FnId;
    // kcall: greatest fixpoint over the call graph
    let mut kc: HashSet<FnId> = (0..n).filter(|f| kcall_local(c, *f)).collect();
    loop {
        let mut drop = vec![];
        for &f in &kc {
            for (t, _) in callees(c, f) {
                let tf = &c.program.fns[t as usize];
                let ok = tf.kind == FnKind::Kernel || admissible_std(c, t) || kc.contains(&t);
                if !ok {
                    drop.push(f);
                    break;
                }
            }
        }
        if drop.is_empty() {
            break;
        }
        for f in drop {
            kc.remove(&f);
        }
    }
    for f in &kc {
        c.facts.fns.entry(*f).or_default().kcall = true;
    }
    let mut diags = vec![];
    for fid in 0..n {
        let f = &c.program.fns[fid as usize];
        if f.kind != FnKind::Kernel || f.role == FileRole::Std || f.body.is_none() {
            continue;
        }
        let path = f.path.clone();
        // (k1)
        let row = c.facts.fns.get(&fid).map(|x| x.row.clone()).unwrap_or_default();
        let ex = c.facts.fns.get(&fid).map(|x| x.exercised.clone()).unwrap_or_default();
        if !row.is_empty() || !ex.is_empty() {
            let mut all = row.clone();
            all.extend(ex);
            diags.push(Diag::new("E-KERNEL-ROW", f.sig_span, format!("a kernel's row and exercised row must be empty; `{}` uses {} (k1)", f.name, crate::program::row_text(&all))).in_def(&path));
        }
        // (k6) capability parameters
        for p in &f.params {
            if is_capability(c, &p.ty) {
                diags.push(Diag::new("E-KERNEL-ROW", p.span, "a kernel holds no capability beyond caller-provided buffers (k6; 02 section 2)").in_def(&path).note("the note names no code for (k6); mithi reports it as E-KERNEL-ROW [prov]"));
            }
        }
        let Some(b) = c.bodies.get(&fid) else { continue };
        walk_deep(c, &b.expr, &mut |e| {
            if let TK::Det { .. } = e.kind {
                diags.push(Diag::new("E-KERNEL-ROW", e.span, "a `deterministic` block in a kernel (k6)").in_def(&path));
            }
            if let Some(t) = call_target(c, e) {
                let tf = &c.program.fns[t as usize];
                let ok = tf.kind == FnKind::Kernel || admissible_std(c, t) || kc.contains(&t);
                if !ok {
                    let why = if tf.role == FileRole::Std {
                        format!("`{}` is not on the closed list C-EXACT-STD", tf.path)
                    } else {
                        format!("`{}` is not kcall (it must be trap-free given its requires, row ∅, and call only admissible functions)", tf.path)
                    };
                    diags.push(Diag::new("E-KERNEL-CALL", e.span, format!("a kernel may call only kernels, C-EXACT-STD functions, format accessors and kcall helpers (k3): {why}")).in_def(&path));
                }
            }
        });
    }
    c.diags.extend(diags);
}
