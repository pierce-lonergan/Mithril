//! ⊢_spec (note section 5.14): (p1) names resolve (definitions, schedules, seam symbols), (p2)
//! claim kinds, (p3) grade scales (DR-007: correctness and performance never mix), (p4)
//! admissibility (03 section 2.2), (p5) typed qualifiers. Sealing and Author ownership are ledger
//! rules (M3), outside mithi.

use super::*;
use crate::ast::ClaimArg;
use crate::diag::Diag;
use crate::program::Def;

const CORRECTNESS: &[&str] = &["refines", "confined", "safe", "deterministic"];
const PERFORMANCE: &[&str] = &["perf", "quality"];
const CORRECT_GRADES: &[&str] = &["proof", "validated", "tested", "assumed"];
const PERF_GRADES: &[&str] = &["measured", "bound"];

enum Subject {
    Fn(FnId),
    Schedule(String),
    Seam,
}

pub fn run(c: &mut Checked) {
    let mut diags = vec![];
    for (s, module) in c.program.specs.clone() {
        let path = crate::program::join_path(&module, &s.name.name);
        let resolve = |p: &crate::ast::Path| -> Option<Subject> {
            let segs: Vec<String> = p.segs.iter().map(|x| x.ident.name.clone()).collect();
            match c.program.resolve(&module, &segs) {
                Some(Def::Fn(f)) => Some(Subject::Fn(f)),
                Some(Def::Schedule(i)) => Some(Subject::Schedule(c.program.schedules[i as usize].0.for_fn.text())),
                Some(Def::SeamFn(_)) => Some(Subject::Seam),
                _ => None,
            }
        };
        if resolve(&s.for_fn).is_none() {
            diags.push(Diag::new("E-UNRESOLVED", s.for_fn.span, format!("spec `{}` is for `{}`, which does not resolve (p1)", s.name.name, s.for_fn.text())).in_def(&path));
        }
        for cl in &s.claims {
            let kind = cl.kind.name.as_str();
            if !CORRECTNESS.contains(&kind) && !PERFORMANCE.contains(&kind) {
                diags.push(Diag::new("E-CLAIM-KIND", cl.kind.span, format!("`{kind}` is not a claim kind (refines, confined, safe, deterministic, perf, quality) (p2)")).in_def(&path));
                continue;
            }
            let mut subjects = vec![];
            for a in &cl.args {
                match resolve(a) {
                    Some(x) => subjects.push(x),
                    None => diags.push(Diag::new("E-UNRESOLVED", a.span, format!("claim subject `{}` does not resolve to a definition, a schedule or a seam symbol (p1)", a.text())).in_def(&path)),
                }
            }
            let g = cl.grade.name.as_str();
            let scale_ok = if CORRECTNESS.contains(&kind) { CORRECT_GRADES.contains(&g) } else { PERF_GRADES.contains(&g) };
            if !scale_ok {
                diags.push(Diag::new("E-CLAIM-KIND", cl.grade.span, format!("grade `{g}` is not on the {} scale of a `{kind}` claim (p3, DR-007)", if CORRECTNESS.contains(&kind) { "correctness" } else { "performance" })).in_def(&path));
                continue;
            }
            // (p4) admissibility
            let kernel_slot = subjects.iter().any(|x| match x {
                Subject::Fn(f) => c.program.fns[*f as usize].kind == FnKind::Kernel,
                Subject::Schedule(target) => {
                    let segs: Vec<String> = target.split("::").map(|x| x.to_string()).collect();
                    matches!(c.program.resolve(&module, &segs), Some(Def::Fn(f)) if c.program.fns[f as usize].kind == FnKind::Kernel)
                }
                Subject::Seam => false,
            });
            let admissible = match kind {
                "refines" if kernel_slot => matches!(g, "proof" | "validated"),
                "refines" => true,
                "confined" => g == "proof",
                "safe" if kernel_slot => g == "proof",
                "perf" | "quality" => g == "measured" || (kind == "perf" && g == "bound"),
                _ => true,
            };
            if !admissible {
                diags.push(Diag::new("E-CLAIM-INADMISSIBLE", cl.grade.span, format!("`{g}` is not admissible for `{kind}`{} (03 section 2.2)", if kernel_slot { " on a kernel slot" } else { "" })).in_def(&path));
            }
            // (p5) qualifiers
            if let Some(q) = &cl.qualifier {
                for (k, v) in &q.args {
                    match (k.name.as_str(), v) {
                        ("margin", ClaimArg::Percent(..)) => {}
                        ("margin", _) => diags.push(Diag::new("E-TYPE", k.span, "`margin` is a Ratio: write a percentage such as `3%` (p5)").in_def(&path)),
                        ("to", ClaimArg::Path(p)) => {
                            if resolve(p).is_none() {
                                diags.push(Diag::new("E-UNRESOLVED", p.span, format!("`{}` does not resolve (p1)", p.text())).in_def(&path));
                            }
                        }
                        _ => {}
                    }
                }
            }
        }
    }
    c.diags.extend(diags);
}
