//! Unification, associated-type normalisation and trait solving.

use crate::program::*;
use crate::types::*;
use std::collections::HashMap;

#[derive(Clone, Default)]
pub struct Infer {
    pub vars: Vec<Option<Ty>>,
    pub ints: Vec<Option<Ty>>,
    pub floats: Vec<Option<Ty>>,
    /// Fn-family bounds of inference variables created by instantiating generics
    pub fn_bounds: HashMap<u32, (u8, Vec<Ty>, Ty)>,
}

impl Infer {
    pub fn fresh(&mut self) -> Ty {
        self.vars.push(None);
        Ty::Infer(self.vars.len() as u32 - 1)
    }
    pub fn fresh_int(&mut self) -> Ty {
        self.ints.push(None);
        Ty::IntVar(self.ints.len() as u32 - 1)
    }
    pub fn fresh_float(&mut self) -> Ty {
        self.floats.push(None);
        Ty::FloatVar(self.floats.len() as u32 - 1)
    }
    pub fn snapshot(&self) -> Infer {
        self.clone()
    }
    pub fn rollback(&mut self, s: Infer) {
        *self = s;
    }
    pub fn shallow(&self, t: &Ty) -> Ty {
        let mut t = t.clone();
        loop {
            match &t {
                Ty::Infer(i) => match &self.vars[*i as usize] {
                    Some(x) => t = x.clone(),
                    None => return t,
                },
                Ty::IntVar(i) => match &self.ints[*i as usize] {
                    Some(x) => t = x.clone(),
                    None => return t,
                },
                Ty::FloatVar(i) => match &self.floats[*i as usize] {
                    Some(x) => t = x.clone(),
                    None => return t,
                },
                _ => return t,
            }
        }
    }
    pub fn zonk(&self, t: &Ty) -> Ty {
        let t = self.shallow(t);
        match t {
            Ty::Tuple(v) => Ty::Tuple(v.iter().map(|x| self.zonk(x)).collect()),
            Ty::Array(a, n) => Ty::Array(Box::new(self.zonk(&a)), Box::new(self.zonk(&n))),
            Ty::Slice(a) => Ty::Slice(Box::new(self.zonk(&a))),
            Ty::Ref(m, a) => Ty::Ref(m, Box::new(self.zonk(&a))),
            Ty::Adt(a, v) => Ty::Adt(a, v.iter().map(|x| self.zonk(x)).collect()),
            Ty::Assoc(b, tr, n) => Ty::Assoc(Box::new(self.zonk(&b)), tr, n),
            Ty::FnPtr(p, r) => Ty::FnPtr(p.iter().map(|x| self.zonk(x)).collect(), Box::new(self.zonk(&r))),
            Ty::Opaque(b) => Ty::Opaque(b.iter().map(|(t, bs)| (*t, bs.iter().map(|(n, x)| (n.clone(), self.zonk(x))).collect())).collect()),
            other => other,
        }
    }
    fn occurs(&self, v: u32, t: &Ty) -> bool {
        let t = self.shallow(t);
        let mut found = false;
        t.walk(&mut |x| {
            if let Ty::Infer(i) = x {
                if *i == v {
                    found = true;
                } else if let Some(Some(inner)) = self.vars.get(*i as usize) {
                    if self.occurs(v, inner) {
                        found = true;
                    }
                }
            }
        });
        found
    }
    pub fn default_vars(&mut self) {
        for i in 0..self.ints.len() {
            if self.ints[i].is_none() {
                self.ints[i] = Some(Ty::Int(IntTy::I32));
            }
        }
        for i in 0..self.floats.len() {
            if self.floats[i].is_none() {
                self.floats[i] = Some(Ty::F64);
            }
        }
    }
}

pub struct Solver<'a> {
    pub p: &'a Program,
    pub inf: &'a mut Infer,
    /// bounds of the generic parameters in scope (by Param index)
    pub param_bounds: &'a [GParam],
    /// capture lists of closures for Copy/Fn queries: closure id -> (param tys, ret ty, fn kind)
    pub closures: &'a HashMap<ClosureId, (Vec<Ty>, Ty, u8)>,
}

impl<'a> Solver<'a> {
    pub fn unify(&mut self, a: &Ty, b: &Ty) -> bool {
        let a = self.normalize(&self.inf.shallow(a));
        let b = self.normalize(&self.inf.shallow(b));
        match (&a, &b) {
            (Ty::Error, _) | (_, Ty::Error) => true,
            (Ty::Infer(i), Ty::Infer(j)) if i == j => true,
            (Ty::Infer(i), t) | (t, Ty::Infer(i)) => {
                if self.inf.occurs(*i, t) {
                    return false;
                }
                // propagate Fn bounds to the other variable
                if let (Ty::Infer(j), Some(fb)) = (t, self.inf.fn_bounds.get(i).cloned()) {
                    self.inf.fn_bounds.entry(*j).or_insert(fb);
                }
                self.inf.vars[*i as usize] = Some(t.clone());
                true
            }
            (Ty::Never, _) | (_, Ty::Never) => true,
            (Ty::IntVar(i), Ty::IntVar(j)) => {
                if i != j {
                    self.inf.ints[*i as usize] = Some(Ty::IntVar(*j));
                }
                true
            }
            (Ty::IntVar(i), Ty::Int(_)) | (Ty::Int(_), Ty::IntVar(i)) => {
                let t = if let Ty::IntVar(_) = a { b.clone() } else { a.clone() };
                self.inf.ints[*i as usize] = Some(t);
                true
            }
            (Ty::FloatVar(i), Ty::FloatVar(j)) => {
                if i != j {
                    self.inf.floats[*i as usize] = Some(Ty::FloatVar(*j));
                }
                true
            }
            (Ty::FloatVar(i), Ty::F32 | Ty::F64) | (Ty::F32 | Ty::F64, Ty::FloatVar(i)) => {
                let t = if let Ty::FloatVar(_) = a { b.clone() } else { a.clone() };
                self.inf.floats[*i as usize] = Some(t);
                true
            }
            (Ty::Int(x), Ty::Int(y)) => x == y,
            (Ty::Tuple(x), Ty::Tuple(y)) => x.len() == y.len() && x.iter().zip(y.iter()).all(|(p, q)| self.unify(p, q)),
            (Ty::Array(t, n), Ty::Array(u, m)) => self.unify(t, u) && self.unify(n, m),
            (Ty::Slice(t), Ty::Slice(u)) => self.unify(t, u),
            (Ty::Ref(m1, t), Ty::Ref(m2, u)) => m1 == m2 && self.unify(t, u),
            (Ty::Adt(x, xs), Ty::Adt(y, ys)) => x == y && xs.len() == ys.len() && xs.iter().zip(ys.iter()).all(|(p, q)| self.unify(p, q)),
            (Ty::FnPtr(p1, r1), Ty::FnPtr(p2, r2)) => p1.len() == p2.len() && p1.iter().zip(p2.iter()).all(|(p, q)| self.unify(p, q)) && self.unify(r1, r2),
            (Ty::Assoc(b1, t1, n1), Ty::Assoc(b2, t2, n2)) => t1 == t2 && n1 == n2 && self.unify(b1, b2),
            (Ty::Opaque(x), Ty::Opaque(y)) => x.len() == y.len(),
            _ => a == b,
        }
    }

    /// Normalise a projection whose base is known.
    pub fn normalize(&mut self, t: &Ty) -> Ty {
        if let Ty::Assoc(base, tr, name) = t {
            let b = self.normalize(&self.inf.shallow(base));
            if let Some(x) = self.assoc_of(&b, *tr, name) {
                return self.normalize(&self.inf.shallow(&x));
            }
            return Ty::Assoc(Box::new(b), *tr, name.clone());
        }
        t.clone()
    }

    /// The associated type `name` of trait `tr` for type `t`, if it can be determined.
    pub fn assoc_of(&mut self, t: &Ty, tr: TraitId, name: &str) -> Option<Ty> {
        match t {
            Ty::Infer(_) | Ty::Error => None,
            Ty::Param(i) => {
                let gp = self.param_bounds.get(*i as usize)?;
                for b in &gp.bounds {
                    if let BoundDef::Trait { tr: bt, assoc, .. } = b {
                        if *bt == tr {
                            if let Some((_, x)) = assoc.iter().find(|(n, _)| n == name) {
                                return Some(x.clone());
                            }
                        }
                    }
                }
                None
            }
            Ty::Opaque(bs) => {
                for (bt, assoc) in bs {
                    if *bt == tr {
                        if let Some((_, x)) = assoc.iter().find(|(n, _)| n == name) {
                            return Some(x.clone());
                        }
                    }
                }
                None
            }
            _ => {
                let impls = self.p.impls_of_trait.get(&tr).cloned().unwrap_or_default();
                for iid in impls {
                    let im = &self.p.impls[iid as usize];
                    let snap = self.inf.snapshot();
                    let fresh: Vec<Ty> = im.generics.iter().map(|_| self.inf.fresh()).collect();
                    let st = im.self_ty.subst(&fresh);
                    if self.unify(&st, t) && self.impl_bounds_hold(iid, &fresh, 0) {
                        if let Some(x) = im.assoc.get(name) {
                            let r = self.inf.zonk(&x.subst(&fresh));
                            // keep bindings made while matching (they are implied by t)
                            let _ = snap;
                            return Some(r);
                        }
                    }
                    self.inf.rollback(snap);
                }
                None
            }
        }
    }

    pub fn impl_bounds_hold(&mut self, iid: ImplId, substs: &[Ty], depth: u32) -> bool {
        let gs = self.p.impls[iid as usize].generics.clone();
        for (i, g) in gs.iter().enumerate() {
            for b in &g.bounds {
                if let BoundDef::Trait { tr, args, .. } = b {
                    let a: Vec<Ty> = args.iter().map(|x| x.subst(substs)).collect();
                    if !self.implements_d(&substs[i], *tr, &a, depth + 1) {
                        return false;
                    }
                }
            }
        }
        true
    }

    pub fn implements(&mut self, t: &Ty, tr: TraitId, args: &[Ty]) -> bool {
        self.implements_d(t, tr, args, 0)
    }

    pub fn implements_d(&mut self, t: &Ty, tr: TraitId, args: &[Ty], depth: u32) -> bool {
        if depth > 12 {
            return false;
        }
        let t = self.normalize(&self.inf.shallow(t));
        let lang = self.p.traits[tr as usize].lang.clone().unwrap_or_default();
        // type parameters: bounds (and supertraits)
        if let Ty::Param(i) = &t {
            if lang == "Sized" || lang == "Send" || lang == "Sync" {
                return true;
            }
            let gp = match self.param_bounds.get(*i as usize) {
                Some(g) => g.clone(),
                None => return false,
            };
            for b in &gp.bounds {
                match b {
                    BoundDef::Trait { tr: bt, .. } => {
                        if *bt == tr || self.trait_implies(*bt, tr) {
                            return true;
                        }
                    }
                    BoundDef::Fn { kind, .. } => {
                        if lang == "Fn" && *kind == 0 || lang == "FnMut" && *kind <= 1 || lang == "FnOnce" {
                            return true;
                        }
                    }
                }
            }
            return false;
        }
        if let Ty::Opaque(bs) = &t {
            return bs.iter().any(|(bt, _)| *bt == tr || self.trait_implies(*bt, tr));
        }
        if matches!(t, Ty::Infer(_) | Ty::Error | Ty::Never) {
            return true;
        }
        match lang.as_str() {
            "Sized" => return !matches!(t, Ty::Slice(_) | Ty::Str),
            "Send" | "Sync" => return true,
            "Copy" => return self.is_copy(&t, depth),
            "Clone" => {
                if self.is_copy(&t, depth) {
                    return true;
                }
                return match &t {
                    Ty::Adt(a, xs) => {
                        let ad = &self.p.adts[*a as usize];
                        if ad.derives("Clone") || matches!(ad.lang.as_deref(), Some("Vec") | Some("String") | Some("Buf")) {
                            xs.clone().iter().all(|x| self.implements_d(x, tr, &[], depth + 1)) || ad.derives("Clone")
                        } else {
                            self.via_impls(&t, tr, args, depth)
                        }
                    }
                    Ty::Tuple(v) => v.clone().iter().all(|x| self.implements_d(x, tr, &[], depth + 1)),
                    Ty::Array(e, _) => self.implements_d(&e.clone(), tr, &[], depth + 1),
                    _ => false,
                };
            }
            "Int" => return matches!(t, Ty::Int(_) | Ty::IntVar(_)),
            "Fn" | "FnMut" | "FnOnce" => {
                return match &t {
                    Ty::Closure(c) => {
                        let k = self.closures.get(c).map(|x| x.2).unwrap_or(0);
                        match lang.as_str() {
                            "Fn" => k == 0,
                            "FnMut" => k <= 1,
                            _ => true,
                        }
                    }
                    Ty::FnPtr(..) => true,
                    _ => false,
                };
            }
            "PartialEq" | "Eq" | "PartialOrd" | "Ord" | "Hash" | "Debug" | "Default" => {
                if self.builtin_cmp_trait(&t, &lang, depth) {
                    return true;
                }
                return self.via_impls(&t, tr, args, depth);
            }
            "From" => {
                // From<T> for T
                if let Some(a0) = args.first() {
                    let snap = self.inf.snapshot();
                    if self.unify(&t, a0) {
                        return true;
                    }
                    self.inf.rollback(snap);
                }
                return self.via_impls(&t, tr, args, depth);
            }
            _ => {}
        }
        self.via_impls(&t, tr, args, depth)
    }

    fn via_impls(&mut self, t: &Ty, tr: TraitId, args: &[Ty], depth: u32) -> bool {
        let impls = self.p.impls_of_trait.get(&tr).cloned().unwrap_or_default();
        for iid in impls {
            let im = self.p.impls[iid as usize].clone();
            if im.negative {
                continue;
            }
            let snap = self.inf.snapshot();
            let fresh: Vec<Ty> = im.generics.iter().map(|_| self.inf.fresh()).collect();
            let st = im.self_ty.subst(&fresh);
            let mut ok = self.unify(&st, t);
            if ok {
                if let Some((_, targs)) = &im.trait_ {
                    for (x, y) in targs.iter().zip(args.iter()) {
                        let xs = x.subst(&fresh);
                        if !self.unify(&xs, y) {
                            ok = false;
                            break;
                        }
                    }
                }
            }
            if ok && self.impl_bounds_hold(iid, &fresh, depth) {
                return true;
            }
            self.inf.rollback(snap);
        }
        false
    }

    /// Does a bound on `have` imply trait `want` (through supertraits)?
    pub fn trait_implies(&self, have: TraitId, want: TraitId) -> bool {
        if have == want {
            return true;
        }
        let mut stack = vec![have];
        let mut seen = vec![];
        while let Some(t) = stack.pop() {
            if seen.contains(&t) {
                continue;
            }
            seen.push(t);
            for s in &self.p.traits[t as usize].supers {
                if let BoundDef::Trait { tr, .. } = s {
                    if *tr == want {
                        return true;
                    }
                    stack.push(*tr);
                }
            }
        }
        false
    }

    pub fn is_copy(&mut self, t: &Ty, depth: u32) -> bool {
        if depth > 12 {
            return false;
        }
        let t = self.inf.shallow(t);
        match &t {
            Ty::Int(_) | Ty::IntVar(_) | Ty::F32 | Ty::F64 | Ty::FloatVar(_) | Ty::F16 | Ty::Bf16 | Ty::Bool | Ty::Char | Ty::Unit | Ty::Never | Ty::Error | Ty::FnPtr(..) => true,
            Ty::Ref(false, _) => true,
            Ty::Ref(true, _) => false,
            Ty::Tuple(v) => v.clone().iter().all(|x| self.is_copy(x, depth + 1)),
            Ty::Array(e, _) => self.is_copy(&e.clone(), depth + 1),
            Ty::Adt(a, xs) => {
                let ad = self.p.adts[*a as usize].clone();
                if ad.linear || !ad.derives("Copy") {
                    return false;
                }
                // derive(Copy) holds when every field is Copy after substitution
                for v in &ad.variants {
                    for f in &v.fields {
                        let ft = f.ty.subst(xs);
                        if !self.is_copy(&ft, depth + 1) {
                            return false;
                        }
                    }
                }
                true
            }
            Ty::Param(i) => {
                let copy = self.p.try_lang_trait("Copy");
                match (self.param_bounds.get(*i as usize), copy) {
                    (Some(g), Some(c)) => g.bounds.iter().any(|b| matches!(b, BoundDef::Trait { tr, .. } if *tr == c || self.trait_implies(*tr, c))),
                    _ => false,
                }
            }
            Ty::Closure(_) => false,
            Ty::Infer(_) => true,
            _ => false,
        }
    }

    fn builtin_cmp_trait(&mut self, t: &Ty, lang: &str, depth: u32) -> bool {
        let t = self.inf.shallow(t);
        let float_ok = !matches!(lang, "Eq" | "Ord" | "Hash");
        match &t {
            Ty::Int(_) | Ty::IntVar(_) | Ty::Bool | Ty::Char | Ty::Unit | Ty::Str => lang != "Default" || !matches!(t, Ty::Str),
            Ty::F32 | Ty::F64 | Ty::FloatVar(_) => float_ok,
            Ty::F16 | Ty::Bf16 => lang == "Debug" || lang == "Default",
            Ty::Ref(_, x) => lang != "Default" && self.builtin_cmp_trait(&x.clone(), lang, depth + 1),
            Ty::Tuple(v) => v.clone().iter().all(|x| self.builtin_cmp_trait(x, lang, depth + 1)),
            Ty::Array(e, _) | Ty::Slice(e) => self.builtin_cmp_trait(&e.clone(), lang, depth + 1),
            Ty::Adt(a, xs) => {
                let ad = self.p.adts[*a as usize].clone();
                let derived = ad.derives(lang) || (lang == "PartialEq" && ad.derives("Eq")) || (lang == "PartialOrd" && ad.derives("Ord"));
                let builtin_ok = match ad.lang.as_deref() {
                    Some("Vec") | Some("Buf") => lang != "Default" || true,
                    Some("String") => true,
                    Some("Hint") | Some("Mutex") | Some("Iter") => lang == "Debug",
                    _ => false,
                };
                if derived {
                    // derive adds `T: Trait` for every parameter used by a field
                    for v in &ad.variants {
                        for f in &v.fields {
                            let ft = f.ty.subst(xs);
                            if ft.has_param() {
                                continue;
                            }
                            if !self.builtin_cmp_trait(&ft, lang, depth + 1) {
                                let tr = self.p.try_lang_trait(lang);
                                if let Some(tr) = tr {
                                    if !self.via_impls(&ft, tr, &[ft.clone()], depth + 1) {
                                        return false;
                                    }
                                }
                            }
                        }
                    }
                    true
                } else if builtin_ok {
                    xs.clone().iter().all(|x| self.builtin_cmp_trait(x, lang, depth + 1))
                } else {
                    false
                }
            }
            Ty::Infer(_) | Ty::Error | Ty::Never => true,
            _ => false,
        }
    }
}
