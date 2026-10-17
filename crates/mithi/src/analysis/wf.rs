//! J1/J2: kinds (Local, Linear, Copy) and well-formedness (note section 5.1), the signature part
//! of T-Ret (section 5.6), instantiation rules (E-LOCAL-INSTANTIATE, E-LINEAR-INSTANTIATE, the
//! std ¬Local bound of with_lock's R), E-TRAIT-OFF and the agent subset (E-X1-NOTYET).

use super::*;
use crate::diag::Diag;
use crate::program::{AdtKind, BoundDef, FnDef, Program, SelfMode};

/// Type-level K-Local.
pub fn is_local(c: &Checked, t: &Ty) -> bool {
    is_local_p(&c.program, &c.closures, t, 0)
}

pub fn is_local_p(p: &Program, closures: &[ClosureDef], t: &Ty, depth: u32) -> bool {
    if depth > 16 {
        return false;
    }
    match t {
        Ty::Ref(..) => true,
        Ty::Tuple(v) => v.iter().any(|x| is_local_p(p, closures, x, depth + 1)),
        Ty::Array(e, _) | Ty::Slice(e) => is_local_p(p, closures, e, depth + 1),
        Ty::Adt(_, xs) => xs.iter().any(|x| is_local_p(p, closures, x, depth + 1)),
        Ty::Closure(cid) => match closures.get(*cid as usize) {
            Some(cd) => cd.captures.iter().any(|c| c.mode != CaptureMode::Move || is_local_p(p, closures, &c.ty, depth + 1)),
            None => false,
        },
        Ty::Opaque(bs) => bs.iter().any(|(_, assoc)| assoc.iter().any(|(_, x)| is_local_p(p, closures, x, depth + 1))),
        _ => false,
    }
}

/// K-Lin, K-LinClo.
pub fn is_linear(c: &Checked, t: &Ty) -> bool {
    is_linear_p(&c.program, &c.closures, t, 0)
}

pub fn is_linear_p(p: &Program, closures: &[ClosureDef], t: &Ty, depth: u32) -> bool {
    if depth > 16 {
        return false;
    }
    match t {
        Ty::Adt(a, xs) => {
            let ad = &p.adts[*a as usize];
            if ad.linear {
                return true;
            }
            for v in &ad.variants {
                for f in &v.fields {
                    if is_linear_p(p, closures, &f.ty.subst(xs), depth + 1) {
                        return true;
                    }
                }
            }
            // std generics with a Linear argument (Option, Result, Vec, Frozen, Iter)
            if ad.role == FileRole::Std {
                return xs.iter().any(|x| is_linear_p(p, closures, x, depth + 1));
            }
            false
        }
        Ty::Tuple(v) => v.iter().any(|x| is_linear_p(p, closures, x, depth + 1)),
        Ty::Array(e, _) => is_linear_p(p, closures, e, depth + 1),
        Ty::Closure(cid) => match closures.get(*cid as usize) {
            // K-LinClo: a closure that captures a Linear value by move
            Some(cd) => cd.captures.iter().any(|cap| cap.mode == CaptureMode::Move && is_linear_p(p, closures, &cap.ty, depth + 1)),
            None => false,
        },
        _ => false,
    }
}

fn err(c: &mut Checked, code: &str, sp: Span, def: &str, msg: impl Into<String>) {
    c.diags.push(Diag::new(code, sp, msg).in_def(def));
}

pub fn run(c: &mut Checked, cfg: &Config) {
    // ---- struct and enum fields (J2: E-REF-FIELD), Linear + Copy
    let adts = c.program.adts.clone();
    for ad in &adts {
        if ad.role == FileRole::Std {
            continue;
        }
        for v in &ad.variants {
            for f in &v.fields {
                if is_local(c, &f.ty) {
                    err(c, "E-REF-FIELD", f.span, &ad.path, format!("field `{}` of `{}` has a Local type `{}`: references are second-class (FF-REF); store an index instead", f.name, ad.name, c.program.ty_name(&f.ty)));
                }
                if let Ty::Adt(m, xs) = &f.ty {
                    if c.program.adts[*m as usize].lang.as_deref() == Some("Mutex") && xs.first().map(|x| is_local(c, x)).unwrap_or(false) {
                        err(c, "E-LOCAL-INSTANTIATE", f.span, &ad.path, "Mutex<T> requires T: ¬Local (note section 5.1)");
                    }
                }
                check_adt_instantiation(c, &f.ty, f.span, &ad.path);
            }
        }
        if ad.linear && ad.derives("Copy") {
            err(c, "E-LINEAR-COPY", ad.span, &ad.path, format!("`{}` is linear and Copy: Linear and Copy are exclusive", ad.name));
        }
        if !ad.linear && ad.derives("Copy") {
            // a struct with a Linear field is Linear, so it cannot be Copy either
            let lin_field = ad.variants.iter().flat_map(|v| v.fields.iter()).any(|f| is_linear(c, &f.ty));
            if lin_field {
                err(c, "E-LINEAR-COPY", ad.span, &ad.path, format!("`{}` has a Linear field and derives Copy", ad.name));
            }
        }
    }
    // ---- traits off (the "Mithril without traits" arm)
    if cfg.no_user_traits {
        for t in c.program.traits.clone() {
            if t.role == FileRole::User {
                err(c, "E-TRAIT-OFF", t.span, &t.path, "user traits are not available in this arm (DR-005 ablation)");
            }
        }
        for im in c.program.impls.clone() {
            if im.role == FileRole::User && im.trait_.is_some() {
                err(c, "E-TRAIT-OFF", im.span, "", "`impl Trait for` is not available in this arm (DR-005 ablation)");
            }
        }
        for f in c.program.fns.clone() {
            if f.role != FileRole::User {
                continue;
            }
            for g in &f.generics[f.n_parent..] {
                if g.bounds.iter().any(|b| matches!(b, BoundDef::Trait { .. })) {
                    err(c, "E-TRAIT-OFF", g.span, &f.path, format!("trait bound on `{}`: trait bounds on your own generics are not available in this arm", g.name));
                }
            }
        }
    }
    // ---- signatures: T-Ret's signature part, parameter types
    let fns = c.program.fns.clone();
    for (fid, f) in fns.iter().enumerate() {
        if f.role == FileRole::Std {
            continue;
        }
        check_signature(c, fid as FnId, f);
        for p in &f.params {
            check_adt_instantiation(c, &p.ty, p.span, &f.path);
        }
    }
    // ---- instantiations inside bodies
    let fids: Vec<FnId> = c.bodies.keys().copied().collect();
    for fid in fids {
        if c.program.fns[fid as usize].role == FileRole::Std {
            continue;
        }
        check_body_instantiations(c, fid);
        check_mono_depth(c, fid);
    }
}

/// E-MONO-DEPTH (§5.7 rule 4, F-80): polymorphic recursion. A generic function that calls itself
/// at a type argument that strictly contains one of its own type parameters, or a closure type it
/// creates (a closure type is parameterised by the enclosing generics), has no finite set of
/// instantiations, so monomorphisation (and per-closure re-typing) would not end; rustc reports it
/// at its recursion limit [inference]. Only direct self-recursion is detected (mithi v0).
fn check_mono_depth(c: &mut Checked, fid: FnId) {
    let f = &c.program.fns[fid as usize];
    if f.generics.is_empty() {
        return;
    }
    let Some(body) = c.bodies.get(&fid) else { return };
    let mut hits: Vec<Span> = vec![];
    walk_deep(c, &body.expr, &mut |e| {
        if let TK::Call { f: callee, substs, .. } = &e.kind {
            if *callee != fid {
                return;
            }
            for (i, t) in substs.iter().enumerate() {
                if *t == Ty::Param(i as u32) {
                    continue;
                }
                let mut grows = false;
                t.walk(&mut |x| match x {
                    Ty::Closure(cid) => {
                        if c.closures.get(*cid as usize).map(|cd| cd.owner == fid).unwrap_or(false) {
                            grows = true;
                        }
                    }
                    Ty::Param(_) => {
                        if !matches!(t, Ty::Param(_)) {
                            grows = true;
                        }
                    }
                    _ => {}
                });
                if grows {
                    hits.push(e.span);
                    return;
                }
            }
        }
    });
    let path = f.path.clone();
    for sp in hits {
        err(c, "E-MONO-DEPTH", sp, &path, "a generic function calls itself at a type that grows (its own closure type or a type containing its type parameter): monomorphisation would not terminate (F-80; rustc stops at its recursion limit)");
    }
}

/// User generic ADTs instantiated at Local or Linear types.
fn check_adt_instantiation(c: &mut Checked, t: &Ty, sp: Span, def: &str) {
    let mut found: Vec<(String, String)> = vec![];
    t.walk(&mut |x| {
        if let Ty::Adt(a, xs) = x {
            let ad = &c.program.adts[*a as usize];
            if ad.role != FileRole::Std {
                for (i, arg) in xs.iter().enumerate() {
                    if is_local(c, arg) {
                        found.push(("E-LOCAL-INSTANTIATE".into(), format!("`{}` instantiated at the Local type `{}` (its parameter {} has the implicit ¬Local bound, 01 section 5.4)", ad.name, c.program.ty_name(arg), i)));
                    } else if is_linear(c, arg) {
                        found.push(("E-LINEAR-INSTANTIATE".into(), format!("`{}` instantiated at the Linear type `{}` (implicit ¬Linear bound, F-41)", ad.name, c.program.ty_name(arg))));
                    }
                }
            }
        }
    });
    for (code, m) in found {
        err(c, &code, sp, def, m);
    }
}

/// Does the generic parameter qualify for the closure-parameter exception (note section 5.7)?
fn closure_param_exception(f: &FnDef, gi: usize) -> bool {
    let g = &f.generics[gi];
    if !g.bounds.iter().any(|b| matches!(b, BoundDef::Fn { .. })) {
        return false;
    }
    let p = Ty::Param(gi as u32);
    let mut occurrences = 0;
    for prm in &f.params {
        let mut hit = false;
        let shape_ok = match &prm.ty {
            t if *t == p => true,
            Ty::Ref(_, inner) if **inner == p => true,
            _ => false,
        };
        prm.ty.walk(&mut |x| {
            if *x == p {
                hit = true;
            }
        });
        if hit {
            if !shape_ok {
                return false;
            }
            occurrences += 1;
        }
    }
    let mut in_ret = false;
    f.ret.walk(&mut |x| {
        if *x == p {
            in_ret = true;
        }
        if let Ty::Assoc(b, _, _) = x {
            if **b == p {
                in_ret = true;
            }
        }
    });
    occurrences == 1 && !in_ret
}

fn check_body_instantiations(c: &mut Checked, fid: FnId) {
    let Some(body) = c.bodies.get(&fid) else { return };
    let def = fn_path(c, fid);
    let mut found: Vec<(String, Span, String)> = vec![];
    walk_deep(c, &body.expr, &mut |e| {
        let (callee, substs) = match &e.kind {
            TK::Call { f, substs, .. } => (*f, substs.clone()),
            TK::TraitCall { decl, substs, .. } => (*decl, substs.clone()),
            _ => return,
        };
        let cf = &c.program.fns[callee as usize];
        if cf.role == FileRole::Std {
            // with_lock: R carries the implicit ¬Local bound (F-28)
            if cf.builtin.as_deref() == Some("mutex_with_lock") {
                if let Some(r) = substs.get(cf.n_parent) {
                    if is_local(c, r) {
                        found.push(("E-REF-ESCAPE".into(), e.span, format!("`with_lock`'s result type R is instantiated at the Local type `{}`: a borrow of locked state cannot leave `with_lock` (F-28); return a copy", c.program.ty_name(r))));
                    }
                }
            }
            if let Some(b) = cf.builtin.as_deref() {
                if super::stdfacts::discards_elements(b) && b != "iter_next" {
                    // the element type: T for drop/forget/take; Item for iterator methods
                    let elem = if b.starts_with("iter_") {
                        substs.first().map(|s| iter_item_of(c, s))
                    } else if b == "vec_clear" || b == "vec_truncate" {
                        substs.first().cloned()
                    } else {
                        substs.get(cf.n_parent).cloned().or_else(|| substs.first().cloned())
                    };
                    if let Some(t) = elem {
                        if is_linear(c, &t) {
                            found.push(("E-LINEAR-INSTANTIATE".into(), e.span, format!("`{}` would discard the Linear value `{}`: its parameter keeps the ¬Linear bound (F-41); consume it explicitly", cf.name, c.program.ty_name(&t))));
                        }
                    }
                }
            }
            return;
        }
        for (gi, t) in substs.iter().enumerate() {
            if gi >= cf.generics.len() {
                break;
            }
            if cf.generics[gi].is_const.is_some() {
                continue;
            }
            if is_local(c, t) && !closure_param_exception(cf, gi) && !cf.generics[gi].relax_local {
                found.push(("E-LOCAL-INSTANTIATE".into(), e.span, format!("`{}`'s parameter `{}` instantiated at the Local type `{}` (implicit ¬Local bound, 01 section 5.4)", cf.name, cf.generics[gi].name, c.program.ty_name(t))));
            }
            if is_linear(c, t) && !cf.generics[gi].relax_linear {
                found.push(("E-LINEAR-INSTANTIATE".into(), e.span, format!("`{}`'s parameter `{}` instantiated at the Linear type `{}` (implicit ¬Linear bound, F-41)", cf.name, cf.generics[gi].name, c.program.ty_name(t))));
            }
        }
    });
    // local variable types mentioning user generics at Local types
    let locals = c.bodies[&fid].locals.clone();
    for (code, sp, m) in found {
        err(c, &code, sp, &def, m);
    }
    for l in &locals {
        check_adt_instantiation(c, &l.ty, l.span, &def);
    }
}

pub fn iter_item_of(c: &Checked, t: &Ty) -> Ty {
    match t {
        Ty::Adt(a, xs) if c.program.adts[*a as usize].lang.as_deref() == Some("Iter") => xs[0].clone(),
        Ty::Adt(a, xs) if matches!(c.program.adts[*a as usize].lang.as_deref(), Some("Range") | Some("RangeInclusive")) => xs[0].clone(),
        Ty::Ref(_, inner) => iter_item_of(c, inner),
        _ => Ty::Error,
    }
}

/// Count reference positions in a type (Rust's input lifetime positions).
fn ref_positions(t: &Ty) -> usize {
    let mut n = 0;
    t.walk(&mut |x| {
        if matches!(x, Ty::Ref(..)) {
            n += 1;
        }
    });
    n
}

#[derive(PartialEq)]
enum RetShape {
    NotLocal,
    Projection,
    Adapter,
}

fn ret_shape(c: &Checked, t: &Ty) -> RetShape {
    if !is_local(c, t) && !matches!(t, Ty::Opaque(_)) {
        return RetShape::NotLocal;
    }
    match t {
        Ty::Ref(..) => RetShape::Projection,
        Ty::Opaque(_) => {
            if is_local(c, t) {
                RetShape::Adapter
            } else {
                RetShape::NotLocal
            }
        }
        Ty::Adt(a, xs) => {
            let lang = c.program.adts[*a as usize].lang.clone().unwrap_or_default();
            if (lang == "Option" || lang == "Result") && xs.iter().all(|x| !is_local(c, x) || matches!(ret_shape(c, x), RetShape::Projection | RetShape::NotLocal)) {
                RetShape::Projection
            } else {
                RetShape::Adapter
            }
        }
        Ty::Tuple(v) => {
            if v.iter().all(|x| matches!(ret_shape(c, x), RetShape::Projection | RetShape::NotLocal)) {
                RetShape::Projection
            } else {
                RetShape::Adapter
            }
        }
        _ => RetShape::Adapter,
    }
}

/// T-Ret, signature part: a Local result is accepted only as a projection on the parameter Rust's
/// lifetime elision selects (01 section 5.3), or by a std adapter.
fn check_signature(c: &mut Checked, fid: FnId, f: &FnDef) {
    let shape = ret_shape(c, &f.ret);
    if shape == RetShape::NotLocal {
        return;
    }
    let sp = f.ret_ast.as_ref().map(|t| t.span).unwrap_or(f.sig_span);
    if shape == RetShape::Adapter {
        err(c, "E-LOCAL-RETURN", sp, &f.path, format!("`{}` returns the Local type `{}` (an adapter or closure that borrows): only projections may return borrows (FF-LOCAL); take a closure parameter or return owned values", f.name, c.program.ty_name(&f.ret)));
        return;
    }
    let by_receiver = matches!(f.self_mode, Some(SelfMode::Ref) | Some(SelfMode::RefMut));
    let positions: usize = f.params.iter().map(|p| ref_positions(&p.ty)).sum();
    if !by_receiver && positions != 1 {
        let why = if positions == 0 { "no reference parameter" } else { "no receiver and several borrowed parameters" };
        err(c, "E-REF-ESCAPE", sp, &f.path, format!("`{}` returns a reference but elision has nothing to tie it to ({why}); return an index or a copy (FF-REF)", f.name));
    }
    let _ = fid;
}

/// The X1 agent subset (X1 design section 9.1): constructs not built for agents yet.
pub fn agent_subset(c: &mut Checked) {
    let mut found: Vec<(String, Span, String)> = vec![];
    for ad in &c.program.adts {
        if ad.role == FileRole::User && ad.linear {
            found.push(("E-X1-NOTYET-LINEAR".into(), ad.span, ad.path.clone()));
        }
    }
    for (s, _) in &c.program.schedules {
        if c.program.sm.role(s.span) == FileRole::User {
            found.push(("E-X1-NOTYET-SCHEDULE".into(), s.span, s.name.name.clone()));
        }
    }
    for (s, _) in &c.program.specs {
        if c.program.sm.role(s.span) == FileRole::User {
            found.push(("E-X1-NOTYET-SPEC".into(), s.span, s.name.name.clone()));
        }
    }
    for (fid, b) in &c.bodies {
        if c.program.fns[*fid as usize].role != FileRole::User {
            continue;
        }
        let path = c.program.fns[*fid as usize].path.clone();
        walk_deep(c, &b.expr, &mut |e| match &e.kind {
            TK::For { par: true, .. } => found.push(("E-X1-NOTYET-PAR".into(), e.span, path.clone())),
            TK::Det { .. } => found.push(("E-X1-NOTYET-DETERMINISTIC".into(), e.span, path.clone())),
            _ => {}
        });
        for l in &b.locals {
            let mut hit = None;
            l.ty.walk(&mut |t| {
                if let Ty::Adt(a, _) = t {
                    match c.program.adts[*a as usize].lang.as_deref() {
                        Some("Frozen") => hit = Some("FROZEN"),
                        Some("BlobFile") => hit = Some("BLOBFILE"),
                        _ => {}
                    }
                }
            });
            if let Some(h) = hit {
                found.push((format!("E-X1-NOTYET-{h}"), l.span, path.clone()));
            }
        }
    }
    // `#[path]` (X1 design 9.1: the static gate's Mithril side)
    for sp in c.program.path_attrs.clone() {
        if c.program.sm.role(sp) == FileRole::User {
            found.push(("E-X1-NOTYET-PATH".into(), sp, String::new()));
        }
    }
    // out-of-scope keywords become E-X1-NOTYET in the agent subset
    let oos = std::mem::take(&mut c.program.oos);
    for (kw, sp) in oos {
        let is_kw = matches!(kw.as_str(), "FLOW" | "STORE" | "EVOLVE" | "EXPORT" | "COMPTIME");
        if is_kw {
            found.push((format!("E-X1-NOTYET-{kw}"), sp, String::new()));
        } else {
            c.program.oos.push((kw, sp));
        }
    }
    for (code, sp, def) in found {
        c.diags.push(Diag::new(&code, sp, "not in the X1 agent subset (X1 design section 9.1)").in_def(&def));
    }
}

pub fn adt_kind(c: &Checked, a: AdtId) -> &AdtKind {
    &c.program.adts[a as usize].kind
}
