//! ⊢_sch (note section 5.14), the completeness side only: (s1) a kernel and a catalogue target,
//! (s2) names resolve over the inlined KIR (own scope first, then unique in inlined kernel
//! callees, F-2), (s3/s3') licence classes decided from loop-carried dependences (F-52), (s4)
//! anything else is E-SCHED-REASSOC. Soundness is T1 on the emitted object (M2), not mithi's.

use super::*;
use crate::diag::Diag;
use std::collections::{BTreeSet, HashMap};

#[derive(Clone, Debug)]
#[allow(dead_code)]
struct Name {
    local: LocalId,
    fid: FnId,
    is_loop: Option<LoopId>,
    par: bool,
    float: bool,
}

/// Names of a kernel body: parameters, let-bound locals and loop variables.
fn names_of(c: &Checked, fid: FnId) -> HashMap<String, Vec<Name>> {
    let mut out: HashMap<String, Vec<Name>> = HashMap::new();
    let Some(b) = c.bodies.get(&fid) else { return out };
    let mut loop_of: HashMap<LocalId, (LoopId, bool)> = HashMap::new();
    walk_deep(c, &b.expr, &mut |e| {
        if let TK::For { id, pat, par, .. } = &e.kind {
            if let Some(v) = pat.is_irrefutable_bind() {
                loop_of.insert(v, (*id, *par));
            }
        }
    });
    for (i, l) in b.locals.iter().enumerate() {
        if l.closure.is_some() || l.name == "result" {
            continue;
        }
        let lp = loop_of.get(&(i as LocalId)).copied();
        out.entry(l.name.clone()).or_default().push(Name { local: i as LocalId, fid, is_loop: lp.map(|x| x.0), par: lp.map(|x| x.1).unwrap_or(false), float: l.ty.is_float() });
    }
    out
}

/// Kernel callees, transitively (the inlined KIR's functions).
fn inlined(c: &Checked, fid: FnId) -> Vec<FnId> {
    let mut seen = BTreeSet::new();
    let mut stack = vec![fid];
    let mut out = vec![];
    while let Some(f) = stack.pop() {
        for (t, _) in callees(c, f) {
            if c.program.fns[t as usize].kind == FnKind::Kernel && t != fid && seen.insert(t) {
                out.push(t);
                stack.push(t);
            }
        }
    }
    out
}

/// Locals assigned in a loop's body and declared outside it: the loop-carried dependences.
fn carried(c: &Checked, fid: FnId, lid: LoopId) -> Vec<(LocalId, bool)> {
    let Some(b) = c.bodies.get(&fid) else { return vec![] };
    let mut lp: Option<&TExpr> = None;
    walk_deep(c, &b.expr, &mut |e| match &e.kind {
        TK::For { id, body, .. } | TK::While(id, _, body) | TK::Loop(id, body) if *id == lid => lp = Some(body),
        _ => {}
    });
    let Some(body) = lp else { return vec![] };
    let mut declared = BTreeSet::new();
    walk_deep(c, body, &mut |e| {
        if let TK::Block(stmts, _) = &e.kind {
            for s in stmts {
                if let TStmt::Let { pat, .. } = s {
                    let mut bs = vec![];
                    pat.bindings(&mut bs);
                    declared.extend(bs);
                }
            }
        }
        if let TK::For { pat, .. } = &e.kind {
            let mut bs = vec![];
            pat.bindings(&mut bs);
            declared.extend(bs);
        }
    });
    let mut out = BTreeSet::new();
    walk_deep(c, body, &mut |e| {
        if let TK::Assign(p, _) | TK::AssignOp(_, p, _) = &e.kind {
            if let TK::Local(l) = p.kind {
                if !declared.contains(&l) {
                    out.insert(l);
                }
            }
        }
    });
    out.into_iter().map(|l| (l, b.locals[l as usize].ty.is_float())).collect()
}

pub fn run(c: &mut Checked) {
    let mut diags = vec![];
    let mut facts = vec![];
    for (s, module) in c.program.schedules.clone() {
        if s.elided {
            continue;
        }
        let path = join(&module, &s.name.name);
        let segs: Vec<String> = s.for_fn.segs.iter().map(|x| x.ident.name.clone()).collect();
        let kfid = match c.program.resolve(&module, &segs) {
            Some(crate::program::Def::Fn(f)) => f,
            _ => {
                diags.push(Diag::new("E-UNRESOLVED", s.for_fn.span, format!("schedule `{}` is for `{}`, which does not resolve", s.name.name, s.for_fn.text())).in_def(&path));
                continue;
            }
        };
        if c.program.fns[kfid as usize].kind != FnKind::Kernel {
            diags.push(Diag::new("E-SCHED-TARGET", s.for_fn.span, format!("a schedule applies to a kernel fn (s1); `{}` is not one", s.for_fn.text())).in_def(&path).note("the note names no code for (s1); E-SCHED-TARGET is mithi's [prov]"));
            continue;
        }
        // (s1) target catalogue
        match c.program.targets.iter().find(|t| t.arch.name == s.arch.name) {
            None => diags.push(Diag::new("E-SCHED-TARGET", s.arch.span, format!("target `{}` is not in the catalogue (s1)", s.arch.name)).in_def(&path)),
            Some(t) => {
                for ft in &s.features {
                    if !t.features.iter().any(|x| x.name == ft.name) {
                        diags.push(Diag::new("E-SCHED-TARGET", ft.span, format!("feature `{}` is not a catalogue feature of `{}` (s1)", ft.name, s.arch.name)).in_def(&path));
                    }
                }
            }
        }
        // (s2) names over the inlined KIR
        let own = names_of(c, kfid);
        let callees: Vec<FnId> = inlined(c, kfid);
        let inl: Vec<HashMap<String, Vec<Name>>> = callees.iter().map(|f| names_of(c, *f)).collect();
        let resolve = |n: &str| -> Result<Name, String> {
            let base = n.split('.').next().unwrap_or(n);
            if let Some(v) = own.get(base) {
                if v.len() == 1 {
                    return Ok(v[0].clone());
                }
                return Err(format!("`{base}` is bound more than once in `{}`", s.for_fn.text()));
            }
            let mut found: Vec<Name> = vec![];
            for m in &inl {
                if let Some(v) = m.get(base) {
                    found.extend(v.iter().cloned());
                }
            }
            match found.len() {
                1 => Ok(found.remove(0)),
                0 => Err(format!("`{base}` is bound neither in `{}` nor in its inlined kernel callees", s.for_fn.text())),
                _ => Err(format!("`{base}` is bound more than once in the inlined loop nest (F-2)")),
            }
        };
        let mut lic = vec![];
        for d in &s.directives {
            let verb = d.verb.name.as_str();
            let first = d.words.first().map(|w| w.name.clone()).unwrap_or_default();
            let text = std::iter::once(verb.to_string()).chain(d.words.iter().map(|w| w.name.clone())).collect::<Vec<_>>().join(" ");
            let name = match resolve(&first) {
                Ok(n) => n,
                Err(m) => {
                    diags.push(Diag::new("E-SCHED-AMBIGUOUS", d.span, format!("schedule name: {m} (s2)")).in_def(&path));
                    continue;
                }
            };
            let class: Result<&str, String> = match verb {
                "tile" | "unroll" => {
                    if name.is_loop.is_some() {
                        Ok("exact")
                    } else {
                        Err(format!("`{first}` is not a loop"))
                    }
                }
                "vectorize" => match name.is_loop {
                    None => Err(format!("`{first}` is not a loop")),
                    Some(lid) => {
                        let cr = carried(c, name.fid, lid);
                        let floats: Vec<&(LocalId, bool)> = cr.iter().filter(|x| x.1).collect();
                        let using = d.words.iter().position(|w| w.name == "using").and_then(|i| d.words.get(i + 1)).map(|w| w.name.clone());
                        if !floats.is_empty() {
                            let nm = c.bodies[&name.fid].locals[floats[0].0 as usize].name.clone();
                            Err(format!("vectorising `{first}` splits the float chain `{nm}` across lanes (a split accumulator, 02 section 8.2; F-52)"))
                        } else if let Some(u) = using {
                            if (u == "vpdpbusd" || u == "vpmaddubsw") && cr.len() == 1 {
                                Ok("int_assoc")
                            } else if u == "vpdpbusd" || u == "vpmaddubsw" {
                                Err(format!("`using {u}` needs exactly one integer accumulator carried by `{first}`"))
                            } else {
                                Err(format!("`{u}` is not in the licence table"))
                            }
                        } else {
                            Ok("exact")
                        }
                    }
                },
                "keep_order" => {
                    if name.float {
                        Ok("exact")
                    } else {
                        Err(format!("`keep_order {first}`: `{first}` is not a float chain"))
                    }
                }
                "prefetch" => Ok("timing-only"),
                "parallel" => {
                    if name.par {
                        Ok("exact")
                    } else {
                        Err(format!("`parallel {first}`: only a `par for` loop may run in parallel"))
                    }
                }
                other => Err(format!("`{other}` is not a DAG-preserving primitive of the licence table (s4)")),
            };
            match class {
                Ok(k) => lic.push((text, k.to_string())),
                Err(m) => diags.push(Diag::new("E-SCHED-REASSOC", d.span, m).in_def(&path)),
            }
        }
        facts.push((s.name.name.clone(), lic));
    }
    c.facts.schedules = facts;
    c.diags.extend(diags);
}

fn join(m: &str, n: &str) -> String {
    crate::program::join_path(m, n)
}
