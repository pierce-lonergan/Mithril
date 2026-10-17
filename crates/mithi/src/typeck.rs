//! Type checking: local inference, method resolution, traits, closures. Produces THIR bodies.
//! Errors are E-TYPE / E-UNRESOLVED (class 1) plus the Dc diagnostics that are visible at this
//! level (E-AMBIENT-IO, E-MACRO, E-FF-ADDR, E-FF-F16, E-DYN, E-GRANT-UNSAFE, ...).

use crate::ast::{self, BinOp, ExprKind, Lit, PatKind, UnOp};
use crate::diag::{Diag, FileRole, Span};
use crate::infer::{Infer, Solver};
use crate::program::*;
use crate::thir::*;
use crate::types::*;
use std::collections::{BTreeSet, HashMap};

#[derive(Clone, Default)]
pub struct Options {
    /// accept `…` as an elided body (documentation snippets; the negative items N-01 ff.)
    pub doc_snippets: bool,
    /// host function whose body the user file's loose statements become (D-C7)
    pub loose_host: Option<String>,
}

pub struct Typeck<'p> {
    pub p: &'p Program,
    pub opts: Options,
    pub diags: Vec<Diag>,
    pub closures: Vec<ClosureDef>,
    pub closure_parent: Vec<Option<ClosureId>>,
    pub bodies: HashMap<FnId, Body>,
    pub const_vals: HashMap<u32, TExpr>,
}

#[derive(Clone)]
struct LoopFrame {
    id: LoopId,
    label: Option<String>,
    break_ty: Option<Ty>,
    is_loop: bool,
    closure_depth: usize,
}

struct FnCx {
    fid: FnId,
    module: String,
    generics: Vec<GParam>,
    self_ty: Option<Ty>,
    inf: Infer,
    locals: Vec<LocalDecl>,
    scopes: Vec<Vec<(String, LocalId)>>,
    loops: Vec<LoopFrame>,
    n_loops: u32,
    loop_spans: Vec<Span>,
    ret_stack: Vec<Ty>,
    closure_stack: Vec<ClosureId>,
    closure_sigs: HashMap<ClosureId, (Vec<Ty>, Ty, u8)>,
    field_scope: Option<AdtId>,
    obligations: Vec<(Ty, TraitId, Vec<Ty>, Span)>,
    lit_checks: Vec<(Ty, i128, Span)>,
    /// locals declared without an initialiser (assignable once)
    deferred: BTreeSet<LocalId>,
    new_closures: Vec<(ClosureId, ClosureDef)>,
    in_contract: bool,
    /// builtin-specific fixups to apply after inference: (call result ty, builtin name, item ty)
    fixups: Vec<(Ty, String, Ty, Span)>,
    role: FileRole,
}


fn lit_float_text(text: &str, ty: &Ty) -> u64 {
    match ty {
        Ty::F32 => text.parse::<f32>().map(|v| v.to_bits() as u64).unwrap_or(0),
        _ => text.parse::<f64>().map(|v| v.to_bits()).unwrap_or(0),
    }
}

impl<'p> Typeck<'p> {
    pub fn new(p: &'p Program, opts: Options) -> Typeck<'p> {
        Typeck { p, opts, diags: vec![], closures: vec![], closure_parent: vec![], bodies: HashMap::new(), const_vals: HashMap::new() }
    }

    pub fn check_all(&mut self) {
        // loose statements: placed in the configured host function
        let mut loose_body: Option<(ast::Block, String)> = None;
        for (stmts, sp, module) in &self.p.loose {
            if self.p.sm.role(*sp) != FileRole::User {
                continue;
            }
            if self.opts.loose_host.is_none() {
                self.diags.push(Diag::new("E-PARSE", *sp, "statements outside a function (a documentation snippet needs a host function, --loose-host)"));
                continue;
            }
            let b = ast::Block { stmts: stmts.clone(), tail: None, span: *sp, is_unsafe: false };
            loose_body = Some((b, module.clone()));
        }
        for fid in 0..self.p.fns.len() as FnId {
            let f = &self.p.fns[fid as usize];
            let mut body = f.body.clone();
            if let (Some((lb, _m)), Some(host)) = (&loose_body, &self.opts.loose_host) {
                if &f.path == host || &f.name == host {
                    body = Some(lb.clone());
                }
            }
            if f.builtin.is_some() {
                // builtin bodies are native; contracts are still typed for the checker
                self.check_fn(fid, None);
                continue;
            }
            self.check_fn(fid, body.as_ref());
        }
        for cid in 0..self.p.consts.len() as u32 {
            self.check_const(cid);
        }
        self.check_derives();
    }

    /// A derive needs every field to implement the derived trait (Rust adds the bound to the
    /// generated impl, E0277), and `Copy` needs `Clone` and Copy fields (E0204), whether derived
    /// or implemented by hand (review 2026-10-16: all of these were accepted).
    fn check_derives(&mut self) {
        let closures: HashMap<ClosureId, (Vec<Ty>, Ty, u8)> = HashMap::new();
        let mut inf = Infer::default();
        let mut out = vec![];
        for ad in &self.p.adts {
            if ad.role != FileRole::User {
                continue;
            }
            let mut solver = Solver { p: self.p, inf: &mut inf, param_bounds: &ad.generics, closures: &closures };
            let manual_copy = self.p.impls.iter().any(|im| im.role == FileRole::User && matches!(&im.self_ty, Ty::Adt(a, _) if self.p.adts[*a as usize].path == ad.path) && im.trait_.as_ref().map(|(t, _)| self.p.traits[*t as usize].lang.as_deref() == Some("Copy")).unwrap_or(false));
            if ad.derives("Copy") && !ad.derives("Clone") {
                let has_clone_impl = self.p.impls.iter().any(|im| matches!(&im.self_ty, Ty::Adt(a, _) if self.p.adts[*a as usize].path == ad.path) && im.trait_.as_ref().map(|(t, _)| self.p.traits[*t as usize].lang.as_deref() == Some("Clone")).unwrap_or(false));
                if !has_clone_impl {
                    out.push(Diag::new("E-TYPE", ad.span, format!("`{}` derives `Copy` without `Clone` (Copy: Clone)", ad.name)));
                }
            }
            for lang in ["Clone", "Copy", "PartialEq", "Eq", "PartialOrd", "Ord", "Debug", "Hash", "Default"] {
                let wanted = ad.derives(lang) || (lang == "Copy" && manual_copy);
                if !wanted {
                    continue;
                }
                let Some(tr) = self.p.try_lang_trait(lang) else { continue };
                for v in &ad.variants {
                    for f in &v.fields {
                        // a field over the type's parameters: the derive bounds the parameter
                        if f.ty.has_param() || matches!(f.ty, Ty::Error) {
                            continue;
                        }
                        let ok = match (&f.ty, lang) {
                            // fn pointers implement the comparison, hash and formatting traits
                            (Ty::FnPtr(..), _) => true,
                            (_, "Debug") => debug_ok(self.p, &f.ty, 0),
                            (_, "PartialEq") | (_, "PartialOrd") => solver.implements(&f.ty, tr, std::slice::from_ref(&f.ty)),
                            (_, "Copy") => solver.is_copy(&f.ty, 0),
                            _ => solver.implements(&f.ty, tr, &[]),
                        };
                        if !ok {
                            let what = if lang == "Copy" && manual_copy && !ad.derives("Copy") { "implements" } else { "derives" };
                            out.push(Diag::new("E-TYPE", f.span, format!("`{}` {what} `{lang}`, but its field `{}` of type `{}` does not implement it", ad.name, f.name, self.p.ty_name(&f.ty))));
                        }
                    }
                }
            }
        }
        self.diags.extend(out);
    }

    fn new_cx(&self, fid: FnId) -> FnCx {
        let f = &self.p.fns[fid as usize];
        let self_ty = match f.owner {
            Owner::Impl(i) => Some(self.p.impls[i as usize].self_ty.clone()),
            Owner::Trait(_) => Some(Ty::Param(0)),
            Owner::Free => match &f.synthetic {
                Some(s) if s.starts_with("invariant:") => f.params.first().and_then(|p| p.ty.deref_ty().cloned()),
                _ => None,
            },
        };
        let field_scope = match &f.synthetic {
            Some(s) if s.starts_with("invariant:") => s[10..].parse::<u32>().ok(),
            _ => None,
        };
        FnCx {
            fid,
            module: f.module.clone(),
            generics: f.generics.clone(),
            self_ty,
            inf: Infer::default(),
            locals: vec![],
            scopes: vec![vec![]],
            loops: vec![],
            n_loops: 0,
            loop_spans: vec![],
            ret_stack: vec![f.ret.clone()],
            closure_stack: vec![],
            closure_sigs: HashMap::new(),
            field_scope,
            obligations: vec![],
            lit_checks: vec![],
            deferred: BTreeSet::new(),
            new_closures: vec![],
            in_contract: false,
            fixups: vec![],
            role: f.role,
        }
    }

    fn check_fn(&mut self, fid: FnId, body: Option<&ast::Block>) {
        let f = self.p.fns[fid as usize].clone();
        let mut cx = self.new_cx(fid);
        // a return-position `impl Trait` is an inference variable inside the body
        let mut ret_ty = f.ret.clone();
        if let Ty::Opaque(bs) = &f.ret {
            let v = cx.inf.fresh();
            for (tr, _assoc) in bs {
                cx.obligations.push((v.clone(), *tr, vec![], f.sig_span));
            }
            ret_ty = v;
        }
        cx.ret_stack = vec![ret_ty.clone()];
        let mut params = vec![];
        for (i, p) in f.params.iter().enumerate() {
            let mutable = matches!(&p.pat, Some(ast::Pat { kind: PatKind::Ident { mutable: true, .. }, .. }));
            let lid = self.add_local(&mut cx, &p.name, p.ty.clone(), mutable, p.span);
            cx.locals[lid as usize].param = Some(i);
            params.push(lid);
            // destructuring parameter patterns
            if let Some(pat) = &p.pat {
                if !matches!(pat.kind, PatKind::Ident { .. } | PatKind::Wild) {
                    self.diags.push(Diag::new("E-TYPE", pat.span, "destructuring parameter patterns are not supported by mithi v0; bind a name and destructure with `let`").in_def(&f.path));
                }
            }
        }
        // contracts
        cx.in_contract = true;
        let mut requires = vec![];
        for r in &f.requires {
            let e = self.check_expr(&mut cx, r, Some(&Ty::Bool));
            requires.push(e);
        }
        let mut result_local = None;
        let mut ensures = vec![];
        let mut footprints = vec![];
        if !f.ensures.is_empty() {
            cx.scopes.push(vec![]);
            let rl = self.add_local(&mut cx, "result", ret_ty.clone(), false, f.sig_span);
            result_local = Some(rl);
            for e in &f.ensures {
                // `footprint(result) == place`
                if let ExprKind::Binary(BinOp::Eq, l, r) = &e.kind {
                    if let ExprKind::Call(callee, args) = &l.kind {
                        if let ExprKind::Path(p) = &callee.kind {
                            if p.single() == Some("footprint") && args.len() == 1 {
                                let place = self.check_expr(&mut cx, r, None);
                                if !place.is_place() {
                                    self.diags.push(Diag::new("E-FOOTPRINT", r.span, "a footprint must be a place of the receiver").in_def(&f.path));
                                }
                                footprints.push(place);
                                continue;
                            }
                        }
                    }
                }
                let te = self.check_expr(&mut cx, e, Some(&Ty::Bool));
                ensures.push(te);
            }
            cx.scopes.pop();
        }
        cx.in_contract = false;
        let expr = match body {
            Some(b) => {
                let te = self.check_block(&mut cx, b, Some(&ret_ty));
                self.coerce(&mut cx, te, &ret_ty)
            }
            None => TExpr::new(TK::Trap(TrapKind::Elided, Some("no body".into())), Ty::Never, f.span),
        };
        let body = self.finish(cx, params, expr, requires, ensures, footprints, result_local);
        self.bodies.insert(fid, body);
    }

    fn check_const(&mut self, cid: u32) {
        let c = self.p.consts[cid as usize].clone();
        if c.is_static {
            if c.is_mut {
                self.diags.push(Diag::new("E-FF-CELL", c.span, "`static mut`: ambient mutable state is rejected (FF-CELL)"));
            } else {
                self.diags.push(Diag::new("E-GLOBAL-STATE", c.span, "a `static`: no globals in v0 (01 section 6.2); pass the state as a parameter"));
            }
        }
        let Some(v) = &c.value else { return };
        // check in a throwaway context owned by no function
        let mut cx = FnCx {
            fid: u32::MAX,
            module: c.module.clone(),
            generics: vec![],
            self_ty: None,
            inf: Infer::default(),
            locals: vec![],
            scopes: vec![vec![]],
            loops: vec![],
            n_loops: 0,
            loop_spans: vec![],
            ret_stack: vec![c.ty.clone()],
            closure_stack: vec![],
            closure_sigs: HashMap::new(),
            field_scope: None,
            obligations: vec![],
            lit_checks: vec![],
            deferred: BTreeSet::new(),
            new_closures: vec![],
            in_contract: false,
            fixups: vec![],
            role: c.role,
        };
        let te = self.check_expr(&mut cx, v, Some(&c.ty));
        let te = self.coerce(&mut cx, te, &c.ty);
        cx.inf.default_vars();
        let te = self.zonk_expr(&mut cx, te);
        self.const_vals.insert(cid, te);
    }

    // ------------------------------------------------------------------ helpers
    fn solver<'a>(&'a self, cx: &'a mut FnCx) -> Solver<'a> {
        let FnCx { inf, generics, closure_sigs, .. } = cx;
        Solver { p: self.p, inf, param_bounds: generics, closures: closure_sigs }
    }
    fn unify(&self, cx: &mut FnCx, a: &Ty, b: &Ty) -> bool {
        let mut s = self.solver(cx);
        s.unify(a, b)
    }
    fn shallow(&self, cx: &mut FnCx, t: &Ty) -> Ty {
        let t = cx.inf.shallow(t);
        let mut s = self.solver(cx);
        s.normalize(&t)
    }
    fn tn(&self, cx: &FnCx, t: &Ty) -> String {
        self.p.ty_name(&cx.inf.zonk(t))
    }
    fn err(&mut self, cx: &FnCx, code: &str, sp: Span, msg: impl Into<String>) {
        let path = if cx.fid == u32::MAX { String::new() } else { self.p.fns[cx.fid as usize].path.clone() };
        self.diags.push(Diag::new(code, sp, msg).in_def(&path));
    }
    fn mismatch(&mut self, cx: &FnCx, sp: Span, want: &Ty, got: &Ty) {
        let w = self.tn(cx, want);
        let g = self.tn(cx, got);
        self.err(cx, "E-TYPE", sp, format!("mismatched types: expected `{w}`, found `{g}`"));
    }
    fn add_local(&mut self, cx: &mut FnCx, name: &str, ty: Ty, mutable: bool, span: Span) -> LocalId {
        let id = cx.locals.len() as LocalId;
        cx.locals.push(LocalDecl { name: name.to_string(), ty, mutable, span, param: None, closure: cx.closure_stack.last().copied() });
        cx.scopes.last_mut().unwrap().push((name.to_string(), id));
        id
    }
    fn lookup_local(&self, cx: &FnCx, name: &str) -> Option<LocalId> {
        for s in cx.scopes.iter().rev() {
            for (n, id) in s.iter().rev() {
                if n == name {
                    return Some(*id);
                }
            }
        }
        None
    }
    fn tycx(&self, cx: &FnCx) -> TyCx {
        TyCx {
            params: cx.generics.iter().map(|g| g.name.clone()).collect(),
            bounds: cx.generics.iter().map(|g| g.bounds.clone()).collect(),
            self_ty: cx.self_ty.clone(),
            in_trait: match self.p.fns.get(cx.fid as usize).map(|f| f.owner) {
                Some(Owner::Trait(t)) => Some(t),
                _ => None,
            },
            impl_trait: match self.p.fns.get(cx.fid as usize).map(|f| f.owner) {
                Some(Owner::Impl(i)) => self.p.impls[i as usize].trait_.as_ref().map(|x| x.0),
                _ => None,
            },
            impl_trait_arg: false,
            allow_missing_args: true,
        }
    }
    /// Lower a type written inside a body; `_` and missing generic arguments become variables.
    fn lower_body_ty(&mut self, cx: &mut FnCx, t: &ast::TypeAst) -> Ty {
        let tycx = self.tycx(cx);
        // lowering may push diagnostics into a scratch program clone; use a local copy of names
        let mut scratch = ScratchLower { p: self.p, diags: vec![] };
        let ty = scratch.lower(t, &tycx, &cx.module);
        for d in scratch.diags {
            self.diags.push(d);
        }
        self.fill_holes(cx, ty)
    }
    fn fill_holes(&mut self, cx: &mut FnCx, t: Ty) -> Ty {
        match t {
            Ty::Error => cx.inf.fresh(),
            Ty::Tuple(v) => Ty::Tuple(v.into_iter().map(|x| self.fill_holes(cx, x)).collect()),
            Ty::Array(a, n) => Ty::Array(Box::new(self.fill_holes(cx, *a)), n),
            Ty::Slice(a) => Ty::Slice(Box::new(self.fill_holes(cx, *a))),
            Ty::Ref(m, a) => Ty::Ref(m, Box::new(self.fill_holes(cx, *a))),
            Ty::Adt(a, v) => Ty::Adt(a, v.into_iter().map(|x| self.fill_holes(cx, x)).collect()),
            other => other,
        }
    }

    fn is_copy(&self, cx: &mut FnCx, t: &Ty) -> bool {
        let mut s = self.solver(cx);
        s.is_copy(t, 0)
    }

    #[allow(dead_code)]
    fn opt(&self, t: Ty) -> Ty {
        self.p.opt_ty(t)
    }
    fn lang_adt(&self, n: &str) -> AdtId {
        self.p.lang_adt(n)
    }

    // ------------------------------------------------------------------ finishing
    fn finish(&mut self, mut cx: FnCx, params: Vec<LocalId>, expr: TExpr, requires: Vec<TExpr>, ensures: Vec<TExpr>, footprints: Vec<TExpr>, result_local: Option<LocalId>) -> Body {
        // builtin-specific fixups (sum/collect/copied) before defaulting
        let fix = std::mem::take(&mut cx.fixups);
        for (res, name, item, sp) in fix {
            let item_r = self.shallow(&mut cx, &item);
            match name.as_str() {
                "iter_sum" | "iter_product" => {
                    let r = self.shallow(&mut cx, &res);
                    if let Ty::Infer(_) = r {
                        let base = match &item_r {
                            Ty::Ref(_, x) => (**x).clone(),
                            x => x.clone(),
                        };
                        self.unify(&mut cx, &res, &base);
                    }
                    let r = self.shallow(&mut cx, &res);
                    if !r.is_numeric() && !matches!(r, Ty::Infer(_) | Ty::Error) {
                        let rn = self.tn(&cx, &r);
                        self.err(&cx, "E-TYPE", sp, format!("`sum`/`product` into `{rn}`: only numeric results are supported"));
                    } else if r.is_numeric() {
                        // Sum<A> is implemented for S = A and S from &A only (review 2026-10-16:
                        // `v.iter().sum::<u64>()` over u32 items was accepted)
                        let base = match &item_r {
                            Ty::Ref(_, x) => self.shallow(&mut cx, x),
                            x => x.clone(),
                        };
                        let rr = self.shallow(&mut cx, &r);
                        if !matches!(base, Ty::Infer(_) | Ty::Error | Ty::IntVar(_) | Ty::FloatVar(_)) && !matches!(rr, Ty::IntVar(_) | Ty::FloatVar(_)) && base != rr {
                            let (rn, bn) = (self.tn(&cx, &rr), self.tn(&cx, &base));
                            self.err(&cx, "E-TYPE", sp, format!("`{rn}: Sum<{bn}>` is not satisfied: `sum`/`product` must produce the item type"));
                        }
                    }
                }
                "iter_collect" => {
                    let r = self.shallow(&mut cx, &res);
                    let vec = Ty::Adt(self.lang_adt("Vec"), vec![item.clone()]);
                    match r {
                        Ty::Infer(_) => {
                            self.unify(&mut cx, &res, &vec);
                        }
                        _ => {
                            if !self.unify(&mut cx, &res, &vec) {
                                let rn = self.tn(&cx, &res);
                                self.err(&cx, "E-TYPE", sp, format!("`collect` into `{rn}`: mithi v0 collects into Vec only"));
                            }
                        }
                    }
                }
                _ => {}
            }
        }
        cx.inf.default_vars();
        let expr = self.zonk_expr(&mut cx, expr);
        let requires: Vec<TExpr> = requires.into_iter().map(|e| self.zonk_expr(&mut cx, e)).collect();
        let ensures: Vec<TExpr> = ensures.into_iter().map(|e| self.zonk_expr(&mut cx, e)).collect();
        let footprints: Vec<TExpr> = footprints.into_iter().map(|e| self.zonk_expr(&mut cx, e)).collect();
        for l in cx.locals.iter_mut() {
            l.ty = cx.inf.zonk(&l.ty);
        }
        // closures: zonk bodies, compute captures, register globally
        let new = std::mem::take(&mut cx.new_closures);
        let mut defs = vec![];
        for (cid, mut cd) in new {
            cd.body = self.zonk_expr(&mut cx, cd.body);
            cd.ret = cx.inf.zonk(&cd.ret);
            cd.param_tys = cd.param_tys.iter().map(|t| cx.inf.zonk(t)).collect();
            cd.params = cd.params.into_iter().map(|p| zonk_pat(&cx.inf, p)).collect();
            defs.push((cid, cd));
        }
        for (cid, cd) in defs.iter_mut() {
            // the Fn kind of a callable type a closure body calls: a closure's inferred kind, a
            // type parameter's Fn* bound, a reference (Fn through `&`, FnMut through `&mut`)
            let kinds: std::collections::HashMap<ClosureId, u8> = cx.closure_sigs.iter().map(|(k, v)| (*k, v.2)).collect();
            let gkinds: Vec<Option<u8>> = cx.generics.iter().map(|g| g.bounds.iter().find_map(|b| if let BoundDef::Fn { kind, .. } = b { Some(*kind) } else { None })).collect();
            let callee_kind = |t: &Ty| -> u8 {
                match t {
                    Ty::Closure(c) => kinds.get(c).copied().unwrap_or(0),
                    Ty::Param(i) => gkinds.get(*i as usize).copied().flatten().unwrap_or(2),
                    Ty::Ref(m, _) => {
                        if *m {
                            1
                        } else {
                            0
                        }
                    }
                    Ty::FnPtr(..) => 0,
                    _ => 2,
                }
            };
            let (caps, kind) = crate::captures::infer_captures(
                self.p,
                &cx.locals,
                *cid,
                &self.closure_parent,
                cd,
                &mut |t| {
                    let mut s = Solver { p: self.p, inf: &mut cx.inf, param_bounds: &cx.generics, closures: &cx.closure_sigs };
                    s.is_copy(t, 0)
                },
                &callee_kind,
            );
            cd.captures = caps;
            cd.fn_kind = kind;
            if let Some(s) = cx.closure_sigs.get_mut(cid) {
                s.2 = kind;
            }
        }
        for (cid, cd) in defs {
            let idx = cid as usize;
            if self.closures.len() <= idx {
                // should not happen: closures are pre-allocated
                continue;
            }
            self.closures[idx] = cd;
        }
        // literal range checks
        for (t, v, sp) in std::mem::take(&mut cx.lit_checks) {
            if let Ty::Int(it) = cx.inf.zonk(&t) {
                if v > it.max_val() || v < it.min_val() {
                    self.err(&cx, "E-TYPE", sp, format!("literal out of range for `{}`", it.name()));
                }
            }
        }
        // trait obligations
        for (t, tr, args, sp) in std::mem::take(&mut cx.obligations) {
            let tz = cx.inf.zonk(&t);
            if tz.has_infer() && matches!(tz, Ty::Infer(_)) {
                continue;
            }
            let argsz: Vec<Ty> = args.iter().map(|a| cx.inf.zonk(a)).collect();
            let ok = {
                let mut s = Solver { p: self.p, inf: &mut cx.inf, param_bounds: &cx.generics, closures: &cx.closure_sigs };
                s.implements(&tz, tr, &argsz)
            };
            if !ok {
                let tn = self.p.ty_name(&tz);
                let trn = self.p.traits[tr as usize].name.clone();
                self.err(&cx, "E-TYPE", sp, format!("the trait bound `{tn}: {trn}` is not satisfied"));
            }
        }
        Body {
            fid: cx.fid,
            locals: cx.locals,
            params,
            expr,
            requires,
            ensures,
            footprints,
            result_local,
            n_loops: cx.n_loops,
            loop_spans: cx.loop_spans,
        }
    }

    fn zonk_expr(&self, cx: &mut FnCx, mut e: TExpr) -> TExpr {
        e.ty = cx.inf.zonk(&e.ty);
        {
            let mut s = Solver { p: self.p, inf: &mut cx.inf, param_bounds: &cx.generics, closures: &cx.closure_sigs };
            e.ty = deep_normalize(&mut s, &e.ty);
        }
        e.kind = match e.kind {
            TK::Lit(LitVal::Float(_)) => e.kind,
            TK::Field(b, i) => TK::Field(Box::new(self.zonk_expr(cx, *b)), i),
            TK::Index(a, b) => TK::Index(Box::new(self.zonk_expr(cx, *a)), Box::new(self.zonk_expr(cx, *b))),
            TK::SliceRange { base, lo, hi, inclusive } => TK::SliceRange {
                base: Box::new(self.zonk_expr(cx, *base)),
                lo: lo.map(|x| Box::new(self.zonk_expr(cx, *x))),
                hi: hi.map(|x| Box::new(self.zonk_expr(cx, *x))),
                inclusive,
            },
            TK::Deref(b) => TK::Deref(Box::new(self.zonk_expr(cx, *b))),
            TK::Borrow(m, b) => TK::Borrow(m, Box::new(self.zonk_expr(cx, *b))),
            TK::Unsize(b) => TK::Unsize(Box::new(self.zonk_expr(cx, *b))),
            TK::Unary(o, b) => TK::Unary(o, Box::new(self.zonk_expr(cx, *b))),
            TK::Binary(o, a, b) => TK::Binary(o, Box::new(self.zonk_expr(cx, *a)), Box::new(self.zonk_expr(cx, *b))),
            TK::Cast(b) => TK::Cast(Box::new(self.zonk_expr(cx, *b))),
            TK::Assign(a, b) => TK::Assign(Box::new(self.zonk_expr(cx, *a)), Box::new(self.zonk_expr(cx, *b))),
            TK::AssignOp(o, a, b) => TK::AssignOp(o, Box::new(self.zonk_expr(cx, *a)), Box::new(self.zonk_expr(cx, *b))),
            TK::Call { f, substs, args } => TK::Call { f, substs: substs.iter().map(|t| cx.inf.zonk(t)).collect(), args: args.into_iter().map(|a| self.zonk_expr(cx, a)).collect() },
            TK::TraitCall { tr, method, decl, self_ty, substs, args } => TK::TraitCall {
                tr,
                method,
                decl,
                self_ty: cx.inf.zonk(&self_ty),
                substs: substs.iter().map(|t| cx.inf.zonk(t)).collect(),
                args: args.into_iter().map(|a| self.zonk_expr(cx, a)).collect(),
            },
            TK::CallValue(f, args) => TK::CallValue(Box::new(self.zonk_expr(cx, *f)), args.into_iter().map(|a| self.zonk_expr(cx, a)).collect()),
            TK::FnRef(f, s) => TK::FnRef(f, s.iter().map(|t| cx.inf.zonk(t)).collect()),
            TK::Ctor { adt, variant, fields } => TK::Ctor { adt, variant, fields: fields.into_iter().map(|a| self.zonk_expr(cx, a)).collect() },
            TK::CtorUpdate { adt, variant, fields, base } => TK::CtorUpdate { adt, variant, fields: fields.into_iter().map(|(i, a)| (i, self.zonk_expr(cx, a))).collect(), base: Box::new(self.zonk_expr(cx, *base)) },
            TK::Tuple(v) => TK::Tuple(v.into_iter().map(|a| self.zonk_expr(cx, a)).collect()),
            TK::Array(v) => TK::Array(v.into_iter().map(|a| self.zonk_expr(cx, a)).collect()),
            TK::Repeat(a, n) => TK::Repeat(Box::new(self.zonk_expr(cx, *a)), n),
            TK::Block(stmts, tail) => TK::Block(
                stmts
                    .into_iter()
                    .map(|s| match s {
                        TStmt::Let { pat, init, els, span } => TStmt::Let { pat: zonk_pat(&cx.inf, pat), init: init.map(|x| self.zonk_expr(cx, x)), els: els.map(|x| self.zonk_expr(cx, x)), span },
                        TStmt::Expr(x) => TStmt::Expr(self.zonk_expr(cx, x)),
                    })
                    .collect(),
                tail.map(|t| Box::new(self.zonk_expr(cx, *t))),
            ),
            TK::If(c, t, e2) => TK::If(Box::new(self.zonk_expr(cx, *c)), Box::new(self.zonk_expr(cx, *t)), e2.map(|x| Box::new(self.zonk_expr(cx, *x)))),
            TK::Match(s, arms) => TK::Match(
                Box::new(self.zonk_expr(cx, *s)),
                arms.into_iter().map(|a| TArm { pat: zonk_pat(&cx.inf, a.pat), guard: a.guard.map(|g| self.zonk_expr(cx, g)), body: self.zonk_expr(cx, a.body) }).collect(),
            ),
            TK::Loop(id, b) => TK::Loop(id, Box::new(self.zonk_expr(cx, *b))),
            TK::While(id, c, b) => TK::While(id, Box::new(self.zonk_expr(cx, *c)), Box::new(self.zonk_expr(cx, *b))),
            TK::For { id, par, pat, iter, body, range } => TK::For {
                id,
                par,
                pat: zonk_pat(&cx.inf, pat),
                iter: Box::new(self.zonk_expr(cx, *iter)),
                body: Box::new(self.zonk_expr(cx, *body)),
                range: range.map(|(a, b, i)| (Box::new(self.zonk_expr(cx, *a)), Box::new(self.zonk_expr(cx, *b)), i)),
            },
            TK::Break(id, v) => TK::Break(id, v.map(|x| Box::new(self.zonk_expr(cx, *x)))),
            TK::Return(v) => TK::Return(v.map(|x| Box::new(self.zonk_expr(cx, *x)))),
            TK::Try { e: inner, is_option, from } => TK::Try { e: Box::new(self.zonk_expr(cx, *inner)), is_option, from: from.map(|(f, s)| (f, s.iter().map(|t| cx.inf.zonk(t)).collect())) },
            TK::Det { evidence, body } => TK::Det { evidence, body: Box::new(self.zonk_expr(cx, *body)) },
            TK::Assert { cond, msg } => TK::Assert { cond: Box::new(self.zonk_expr(cx, *cond)), msg },
            TK::AssertCmp { eq, a, b } => TK::AssertCmp { eq, a: Box::new(self.zonk_expr(cx, *a)), b: Box::new(self.zonk_expr(cx, *b)) },
            TK::Format { pieces, args } => TK::Format { pieces, args: args.into_iter().map(|a| self.zonk_expr(cx, a)).collect() },
            TK::Matches(a, p) => TK::Matches(Box::new(self.zonk_expr(cx, *a)), Box::new(zonk_pat(&cx.inf, *p))),
            TK::LetCond(p, a) => TK::LetCond(Box::new(zonk_pat(&cx.inf, *p)), Box::new(self.zonk_expr(cx, *a))),
            other => other,
        };
        // float literals: parse at the final type
        if let TK::Lit(LitVal::Str(s)) = &e.kind {
            if let Some(text) = s.strip_prefix("\u{0}float:") {
                let bits = lit_float_text(text, &e.ty);
                e.kind = TK::Lit(LitVal::Float(bits));
            }
        }
        e
    }

    // ------------------------------------------------------------------ coercion
    fn coerce(&mut self, cx: &mut FnCx, te: TExpr, target: &Ty) -> TExpr {
        let got = self.shallow(cx, &te.ty);
        let want = self.shallow(cx, target);
        if matches!(got, Ty::Never) {
            return TExpr { ty: target.clone(), ..te };
        }
        if let (Ty::Ref(m_got, inner_got), Ty::Ref(m_want, inner_want)) = (&got, &want) {
            let ig = self.shallow(cx, inner_got);
            let iw = self.shallow(cx, inner_want);
            // &mut T -> &T, and unsizing (&[T; N], &Vec<T>, &Buf<T> -> &[T]; &String -> &str)
            let unsize_elem = match (&ig, &iw) {
                (Ty::Array(e, _), Ty::Slice(_)) => Some((**e).clone()),
                (Ty::Adt(a, xs), Ty::Slice(_)) if self.p.adts[*a as usize].lang.as_deref() == Some("Vec") || self.p.adts[*a as usize].lang.as_deref() == Some("Buf") => Some(xs[0].clone()),
                _ => None,
            };
            if !*m_want || *m_got {
                if let Some(el) = unsize_elem {
                    let st = Ty::Ref(*m_want, Box::new(Ty::Slice(Box::new(el))));
                    let base = if *m_got && !*m_want { self.reborrow_shared(te) } else { te };
                    let u = TExpr::new(TK::Unsize(Box::new(base)), st.clone(), Span::DUMMY);
                    let span = u.children()[0].span;
                    let u = TExpr { span, ..u };
                    if !self.unify(cx, &st, &want) {
                        self.mismatch(cx, span, target, &st);
                    }
                    return u;
                }
                if let (Ty::Adt(a, _), Ty::Str) = (&ig, &iw) {
                    if self.p.adts[*a as usize].lang.as_deref() == Some("String") {
                        let span = te.span;
                        return TExpr::new(TK::Unsize(Box::new(te)), want.clone(), span);
                    }
                }
                // auto-deref coercion: &&T -> &T
                if let Ty::Ref(_, inner2) = &ig {
                    let snap = cx.inf.snapshot();
                    if self.unify(cx, inner2, &iw) {
                        let span = te.span;
                        let d1 = TExpr::new(TK::Deref(Box::new(te)), ig.clone(), span);
                        let d2 = TExpr::new(TK::Deref(Box::new(d1)), (**inner2).clone(), span);
                        return TExpr::new(TK::Borrow(*m_want, Box::new(d2)), want.clone(), span);
                    }
                    cx.inf.rollback(snap);
                }
                if *m_got && !*m_want {
                    let snap = cx.inf.snapshot();
                    if self.unify(cx, &ig, &iw) {
                        return self.reborrow_shared(te);
                    }
                    cx.inf.rollback(snap);
                }
            }
        }
        if !self.unify(cx, &te.ty, target) {
            let sp = te.span;
            self.mismatch(cx, sp, target, &te.ty);
        }
        te
    }

    fn reborrow_shared(&self, te: TExpr) -> TExpr {
        let span = te.span;
        let inner = match &te.ty {
            Ty::Ref(_, i) => (**i).clone(),
            _ => Ty::Error,
        };
        let d = TExpr::new(TK::Deref(Box::new(te)), inner.clone(), span);
        TExpr::new(TK::Borrow(false, Box::new(d)), Ty::Ref(false, Box::new(inner)), span)
    }

    // ------------------------------------------------------------------ blocks and statements
    fn check_block(&mut self, cx: &mut FnCx, b: &ast::Block, expected: Option<&Ty>) -> TExpr {
        if b.is_unsafe {
            self.err(cx, "E-GRANT-UNSAFE", b.span, "`unsafe` block: only packages granted `unsafe` may use it (FF-UNSAFE)");
        }
        cx.scopes.push(vec![]);
        let mut stmts = vec![];
        let mut diverges = false;
        for s in &b.stmts {
            match s {
                ast::Stmt::Let { pat, ty, init, els, span } => {
                    let declared = ty.as_ref().map(|t| self.lower_body_ty(cx, t));
                    let init_te = init.as_ref().map(|e| {
                        let te = self.check_expr(cx, e, declared.as_ref());
                        match &declared {
                            Some(d) => self.coerce(cx, te, d),
                            None => te,
                        }
                    });
                    let vty = match (&declared, &init_te) {
                        (Some(d), _) => d.clone(),
                        (None, Some(te)) => te.ty.clone(),
                        (None, None) => cx.inf.fresh(),
                    };
                    if let Some(te) = &init_te {
                        if matches!(self.shallow(cx, &te.ty), Ty::Never) && els.is_none() {
                            diverges = true;
                        }
                    }
                    let els_te = els.as_ref().map(|eb| self.check_block(cx, eb, Some(&Ty::Never)));
                    let tp = self.check_pat(cx, pat, &vty, None);
                    if init.is_none() {
                        let mut ls = vec![];
                        tp.bindings(&mut ls);
                        for l in ls {
                            cx.deferred.insert(l);
                        }
                    }
                    stmts.push(TStmt::Let { pat: tp, init: init_te, els: els_te, span: *span });
                }
                ast::Stmt::Expr(e, semi) => {
                    let exp = if *semi { None } else { Some(Ty::Unit) };
                    let te = self.check_expr(cx, e, exp.as_ref());
                    let ty = self.shallow(cx, &te.ty);
                    if matches!(ty, Ty::Never) {
                        diverges = true;
                    } else if !*semi && !matches!(ty, Ty::Unit | Ty::Error | Ty::Infer(_)) {
                        let tn = self.tn(cx, &ty);
                        self.err(cx, "E-TYPE", e.span, format!("expected `()`, found `{tn}` (add `;`?)"));
                    }
                    stmts.push(TStmt::Expr(te));
                }
                ast::Stmt::Item(it) => {
                    self.err(cx, "E-TYPE", item_span(it), "items inside function bodies are not supported by mithi v0; move the item to module level");
                }
                ast::Stmt::Empty => {}
            }
        }
        let tail = b.tail.as_ref().map(|t| Box::new(self.check_expr(cx, t, expected)));
        cx.scopes.pop();
        let ty = match &tail {
            Some(t) => t.ty.clone(),
            None => {
                if diverges {
                    Ty::Never
                } else {
                    Ty::Unit
                }
            }
        };
        TExpr::new(TK::Block(stmts, tail), ty, b.span)
    }

    // ------------------------------------------------------------------ patterns
    /// `by_ref`: the default binding mode (None = move, Some(m) = by reference).
    fn check_pat(&mut self, cx: &mut FnCx, pat: &ast::Pat, expected: &Ty, by_ref: Option<bool>) -> TPat {
        let sp = pat.span;
        let exp = self.shallow(cx, expected);
        // default binding modes: a non-reference pattern against a reference
        let is_ref_pat = matches!(pat.kind, PatKind::Ref(..) | PatKind::Ident { .. } | PatKind::Wild | PatKind::Rest);
        if !is_ref_pat {
            if let Ty::Ref(m, inner) = &exp {
                let mode = Some(by_ref.map(|x| x && *m).unwrap_or(*m));
                let innerp = self.check_pat(cx, pat, inner, mode);
                return TPat { kind: PK::Deref(Box::new(innerp)), ty: exp.clone(), span: sp };
            }
        }
        match &pat.kind {
            PatKind::Wild | PatKind::Rest => TPat { kind: PK::Wild, ty: exp, span: sp },
            PatKind::Ident { name, mutable, by_ref: explicit_ref, sub } => {
                // a bare uppercase-less ident that names a unit variant or const is not a binding
                let (bty, br) = match (explicit_ref, by_ref) {
                    (true, _) => (Ty::Ref(*mutable, Box::new(exp.clone())), Some(*mutable)),
                    (false, Some(m)) => (Ty::Ref(m, Box::new(exp.clone())), Some(m)),
                    (false, None) => (exp.clone(), None),
                };
                let mutable_local = *mutable && !*explicit_ref;
                let lid = self.add_local(cx, &name.name, bty.clone(), mutable_local, name.span);
                let subp = sub.as_ref().map(|s| Box::new(self.check_pat(cx, s, &exp, by_ref)));
                TPat { kind: PK::Bind { local: lid, by_ref: br, sub: subp }, ty: exp, span: sp }
            }
            PatKind::Lit(e) => {
                let te = self.check_expr(cx, e, Some(&exp));
                let te = self.coerce(cx, te, &exp);
                let v = match &te.kind {
                    TK::Lit(l) => l.clone(),
                    TK::Unary(UnOp::Neg, inner) => match &inner.kind {
                        TK::Lit(LitVal::Int(v)) => LitVal::Int(-*v),
                        TK::Lit(l) => l.clone(),
                        _ => LitVal::Unit,
                    },
                    _ => {
                        self.err(cx, "E-TYPE", sp, "unsupported literal pattern");
                        LitVal::Unit
                    }
                };
                TPat { kind: PK::Lit(v), ty: exp, span: sp }
            }
            PatKind::Range(lo, hi, incl) => {
                let a = self.pat_const(cx, lo, &exp);
                let b = self.pat_const(cx, hi, &exp);
                let b = if *incl { b } else { b - 1 };
                TPat { kind: PK::Range(a, b), ty: exp, span: sp }
            }
            PatKind::Tuple(ps) => {
                let tys: Vec<Ty> = match &exp {
                    Ty::Tuple(v) if v.len() == ps.len() || ps.iter().any(|p| matches!(p.kind, PatKind::Rest)) => v.clone(),
                    Ty::Unit if ps.is_empty() => vec![],
                    _ => {
                        let v: Vec<Ty> = ps.iter().map(|_| cx.inf.fresh()).collect();
                        let t = Ty::Tuple(v.clone());
                        if !self.unify(cx, &t, &exp) {
                            self.mismatch(cx, sp, &exp, &t);
                        }
                        v
                    }
                };
                let mut out = vec![];
                let mut ti = 0;
                for p in ps {
                    if matches!(p.kind, PatKind::Rest) {
                        let skip = tys.len().saturating_sub(ps.len() - 1);
                        for _ in 0..skip {
                            out.push(TPat { kind: PK::Wild, ty: tys.get(ti).cloned().unwrap_or(Ty::Error), span: p.span });
                            ti += 1;
                        }
                        continue;
                    }
                    let t = tys.get(ti).cloned().unwrap_or(Ty::Error);
                    out.push(self.check_pat(cx, p, &t, by_ref));
                    ti += 1;
                }
                TPat { kind: PK::Tuple(out), ty: exp, span: sp }
            }
            PatKind::Slice(ps) => {
                let et = match &exp {
                    Ty::Array(e, _) | Ty::Slice(e) => (**e).clone(),
                    _ => {
                        self.err(cx, "E-TYPE", sp, "slice pattern on a non-array type");
                        Ty::Error
                    }
                };
                let rest = ps.iter().position(|p| matches!(p.kind, PatKind::Rest));
                let out = ps.iter().filter(|p| !matches!(p.kind, PatKind::Rest)).map(|p| self.check_pat(cx, p, &et, by_ref)).collect();
                TPat { kind: PK::Slice(out, rest), ty: exp, span: sp }
            }
            PatKind::Ref(inner, m) => match &exp {
                Ty::Ref(em, it) => {
                    if *m && !*em {
                        self.err(cx, "E-TYPE", sp, "`&mut` pattern against a shared reference");
                    }
                    let ip = self.check_pat(cx, inner, it, None);
                    TPat { kind: PK::Deref(Box::new(ip)), ty: exp.clone(), span: sp }
                }
                _ => {
                    self.err(cx, "E-TYPE", sp, "reference pattern against a non-reference");
                    TPat { kind: PK::Wild, ty: exp, span: sp }
                }
            },
            PatKind::Or(alts) => {
                let ps = alts.iter().map(|a| self.check_pat(cx, a, &exp, by_ref)).collect();
                TPat { kind: PK::Or(ps), ty: exp, span: sp }
            }
            PatKind::Path(p) => {
                let segs: Vec<String> = p.segs.iter().map(|s| s.ident.name.clone()).collect();
                match self.resolve_variant_path(cx, &segs) {
                    Some((adt, v)) => {
                        let t = self.adt_fresh(cx, adt);
                        if !self.unify(cx, &t, &exp) {
                            self.mismatch(cx, sp, &exp, &t);
                        }
                        TPat { kind: PK::Variant { adt, variant: v, fields: vec![] }, ty: exp, span: sp }
                    }
                    None => {
                        // a const pattern
                        if let Some(Def::Const(c)) = self.p.resolve(&cx.module, &segs) {
                            if let Some(v) = self.p.const_int_value(c) {
                                return TPat { kind: PK::Lit(LitVal::Int(v)), ty: exp, span: sp };
                            }
                        }
                        if segs.len() == 1 {
                            // lowercase-free single name: bind it
                            let lid = self.add_local(cx, &segs[0], exp.clone(), false, sp);
                            return TPat { kind: PK::Bind { local: lid, by_ref: None, sub: None }, ty: exp, span: sp };
                        }
                        self.err(cx, "E-UNRESOLVED", sp, format!("cannot find `{}` in this scope", p.text()));
                        TPat { kind: PK::Wild, ty: exp, span: sp }
                    }
                }
            }
            PatKind::TupleStruct(p, ps) => {
                let segs: Vec<String> = p.segs.iter().map(|s| s.ident.name.clone()).collect();
                let Some((adt, v)) = self.resolve_variant_path(cx, &segs).or_else(|| match self.p.resolve(&cx.module, &segs) {
                    Some(Def::Adt(a)) => Some((a, 0)),
                    _ => None,
                }) else {
                    self.err(cx, "E-UNRESOLVED", sp, format!("cannot find tuple struct or variant `{}`", p.text()));
                    return TPat { kind: PK::Wild, ty: exp, span: sp };
                };
                let (t, substs) = self.adt_fresh_substs(cx, adt);
                if !self.unify(cx, &t, &exp) {
                    self.mismatch(cx, sp, &exp, &t);
                }
                let vd = self.p.adts[adt as usize].variants[v as usize].clone();
                let mut fields = vec![];
                let mut fi = 0usize;
                for sp2 in ps {
                    if matches!(sp2.kind, PatKind::Rest) {
                        fi = vd.fields.len().saturating_sub(ps.len() - 1 - fields.len());
                        continue;
                    }
                    let ft = vd.fields.get(fi).map(|f| f.ty.subst(&substs)).unwrap_or(Ty::Error);
                    if fi >= vd.fields.len() {
                        self.err(cx, "E-TYPE", sp2.span, "too many fields in pattern");
                    }
                    fields.push((fi as u32, self.check_pat(cx, sp2, &ft, by_ref)));
                    fi += 1;
                }
                TPat { kind: PK::Variant { adt, variant: v, fields }, ty: exp, span: sp }
            }
            PatKind::Struct(p, fs, _rest) => {
                let segs: Vec<String> = p.segs.iter().map(|s| s.ident.name.clone()).collect();
                let Some((adt, v)) = self.resolve_variant_path(cx, &segs).or_else(|| match self.p.resolve(&cx.module, &segs) {
                    Some(Def::Adt(a)) => Some((a, 0)),
                    _ => None,
                }) else {
                    self.err(cx, "E-UNRESOLVED", sp, format!("cannot find struct or variant `{}`", p.text()));
                    return TPat { kind: PK::Wild, ty: exp, span: sp };
                };
                let (t, substs) = self.adt_fresh_substs(cx, adt);
                if !self.unify(cx, &t, &exp) {
                    self.mismatch(cx, sp, &exp, &t);
                }
                let vd = self.p.adts[adt as usize].variants[v as usize].clone();
                let mut fields = vec![];
                for (fname, fp) in fs {
                    match vd.fields.iter().position(|f| f.name == fname.name) {
                        Some(fi) => {
                            let ft = vd.fields[fi].ty.subst(&substs);
                            fields.push((fi as u32, self.check_pat(cx, fp, &ft, by_ref)));
                        }
                        None => self.err(cx, "E-TYPE", fname.span, format!("no field `{}`", fname.name)),
                    }
                }
                TPat { kind: PK::Variant { adt, variant: v, fields }, ty: exp, span: sp }
            }
        }
    }

    fn pat_const(&mut self, cx: &mut FnCx, e: &ast::Expr, ty: &Ty) -> i128 {
        let te = self.check_expr(cx, e, Some(ty));
        match &te.kind {
            TK::Lit(LitVal::Int(v)) => *v,
            TK::Lit(LitVal::Char(c)) => *c as i128,
            TK::Unary(UnOp::Neg, i) => match &i.kind {
                TK::Lit(LitVal::Int(v)) => -*v,
                _ => 0,
            },
            _ => {
                self.err(cx, "E-TYPE", e.span, "range patterns need literal bounds");
                0
            }
        }
    }

    fn adt_fresh_substs(&mut self, cx: &mut FnCx, adt: AdtId) -> (Ty, Vec<Ty>) {
        let n = self.p.adts[adt as usize].generics.len();
        let substs: Vec<Ty> = (0..n).map(|_| cx.inf.fresh()).collect();
        (Ty::Adt(adt, substs.clone()), substs)
    }
    fn adt_fresh(&mut self, cx: &mut FnCx, adt: AdtId) -> Ty {
        self.adt_fresh_substs(cx, adt).0
    }

    fn resolve_variant_path(&self, cx: &FnCx, segs: &[String]) -> Option<(AdtId, u32)> {
        match self.p.resolve(&cx.module, segs) {
            Some(Def::Variant(a, v)) => return Some((a, v)),
            _ => {}
        }
        // `Self::Variant` and `Type::Variant` through an alias
        if segs.len() == 2 {
            let base = if segs[0] == "Self" {
                cx.self_ty.clone()
            } else {
                match self.p.resolve(&cx.module, &segs[..1]) {
                    Some(Def::Adt(a)) => Some(Ty::Adt(a, vec![])),
                    _ => None,
                }
            };
            if let Some(Ty::Adt(a, _)) = base {
                if let Some(i) = self.p.adts[a as usize].variants.iter().position(|v| v.name == segs[1]) {
                    if self.p.adts[a as usize].kind == AdtKind::Enum {
                        return Some((a, i as u32));
                    }
                }
            }
        }
        None
    }

    // ------------------------------------------------------------------ expressions
    fn check_expr(&mut self, cx: &mut FnCx, e: &ast::Expr, expected: Option<&Ty>) -> TExpr {
        self.check_expr_m(cx, e, expected, false)
    }

    /// `want_mut`: the expression is a place that will be written (IndexMut selection).
    fn check_expr_m(&mut self, cx: &mut FnCx, e: &ast::Expr, expected: Option<&Ty>, want_mut: bool) -> TExpr {
        let sp = e.span;
        match &e.kind {
            ExprKind::Lit(l) => self.check_lit(cx, l, expected, sp),
            ExprKind::Paren(inner) => self.check_expr_m(cx, inner, expected, want_mut),
            ExprKind::Path(p) => self.check_path_expr(cx, p, expected, sp),
            ExprKind::Unary(op, inner) => self.check_unary(cx, *op, inner, expected, sp, want_mut),
            ExprKind::Ref { mutable, expr } => {
                let exp_inner = expected.and_then(|t| match self.shallow(cx, t) {
                    Ty::Ref(_, i) => Some((*i).clone()),
                    _ => None,
                });
                let inner = self.check_expr_m(cx, expr, exp_inner.as_ref(), *mutable);
                if *mutable {
                    self.check_mutable_place(cx, &inner, sp, "borrow as mutable");
                }
                let inner = self.ensure_place(cx, inner);
                let t = Ty::Ref(*mutable, Box::new(inner.ty.clone()));
                TExpr::new(TK::Borrow(*mutable, Box::new(inner)), t, sp)
            }
            ExprKind::Binary(op, a, b) => self.check_binary(cx, *op, a, b, expected, sp),
            ExprKind::Assign(lhs, rhs) => {
                // the assigned value is evaluated first (F-54)
                let l = self.check_expr_m(cx, lhs, None, true);
                let r = self.check_expr(cx, rhs, Some(&l.ty));
                let r = self.coerce(cx, r, &l.ty.clone());
                self.check_mutable_place(cx, &l, lhs.span, "assign to");
                if !l.is_place() {
                    self.err(cx, "E-TYPE", lhs.span, "invalid left-hand side of an assignment");
                }
                TExpr::new(TK::Assign(Box::new(l), Box::new(r)), Ty::Unit, sp)
            }
            ExprKind::AssignOp(op, lhs, rhs) => {
                let l = self.check_expr_m(cx, lhs, None, true);
                let lt = self.shallow(cx, &l.ty);
                let r = if matches!(op, BinOp::Shl | BinOp::Shr) {
                    let r = self.check_expr(cx, rhs, None);
                    let rt = self.shallow(cx, &r.ty);
                    if !rt.is_int() && !matches!(rt, Ty::Error) {
                        self.err(cx, "E-TYPE", rhs.span, "shift amount must be an integer");
                    }
                    r
                } else {
                    let r = self.check_expr(cx, rhs, Some(&lt));
                    self.coerce(cx, r, &lt)
                };
                self.check_mutable_place(cx, &l, lhs.span, "assign to");
                let lt = self.shallow(cx, &l.ty);
                if !lt.is_numeric() && !(matches!(lt, Ty::Bool) && matches!(op, BinOp::BitAnd | BinOp::BitOr | BinOp::BitXor)) && !matches!(lt, Ty::Error | Ty::Infer(_) | Ty::F16 | Ty::Bf16) {
                    let tn = self.tn(cx, &lt);
                    self.err(cx, "E-TYPE", sp, format!("`{}=` on `{tn}`: compound assignment is defined on primitive numbers only in mithi v0", op.sym()));
                }
                if matches!(lt, Ty::F16 | Ty::Bf16) {
                    self.err(cx, "E-FF-F16", sp, "arithmetic on `f16`/`bf16`: storage only; widen with `.to_f32()` (FF-F16)");
                }
                TExpr::new(TK::AssignOp(*op, Box::new(l), Box::new(r)), Ty::Unit, sp)
            }
            ExprKind::Cast(inner, t) => {
                let target = self.lower_body_ty(cx, t);
                let it = self.check_expr(cx, inner, None);
                let from = self.shallow(cx, &it.ty);
                let to = self.shallow(cx, &target);
                // an unsuffixed literal cast: give it its natural default
                let ok = match (&from, &to) {
                    (Ty::F16 | Ty::Bf16, _) | (_, Ty::F16 | Ty::Bf16) => {
                        self.err(cx, "E-FF-F16", sp, "`as` to or from `f16`/`bf16`: storage only; use `.to_f32()` (FF-F16)");
                        true
                    }
                    (a, b) if (a.is_numeric() || matches!(a, Ty::Bool | Ty::Char)) && b.is_numeric() => true,
                    (Ty::Int(IntTy::U8) | Ty::IntVar(_), Ty::Char) => true,
                    (Ty::Adt(a, _), b) if b.is_int() && self.p.adts[*a as usize].kind == AdtKind::Enum && self.p.adts[*a as usize].variants.iter().all(|v| v.unit) => true,
                    (Ty::Error, _) | (_, Ty::Error) | (Ty::Infer(_), _) => true,
                    (a, b) if a == b => true,
                    _ => false,
                };
                if !ok {
                    let a = self.tn(cx, &from);
                    let b = self.tn(cx, &to);
                    self.err(cx, "E-TYPE", sp, format!("non-primitive cast: `{a}` as `{b}`"));
                }
                TExpr::new(TK::Cast(Box::new(it)), target, sp)
            }
            ExprKind::Call(callee, args) => self.check_call(cx, callee, args, expected, sp),
            ExprKind::MethodCall { recv, method, generics, args } => self.check_method_call(cx, recv, method, generics.as_deref(), args, expected, sp, want_mut),
            ExprKind::Field(base, name) => self.check_field(cx, base, &name.name, name.span, sp, want_mut),
            ExprKind::TupleField(base, idx, fsp) => self.check_field(cx, base, &idx.to_string(), *fsp, sp, want_mut),
            ExprKind::Index(base, idx) => self.check_index(cx, base, idx, sp, want_mut),
            ExprKind::Range(lo, hi, incl) => {
                let elem = cx.inf.fresh_int();
                let elem = match expected.map(|t| self.shallow(cx, t)) {
                    Some(Ty::Adt(_, xs)) if xs.len() == 1 => {
                        self.unify(cx, &elem, &xs[0]);
                        elem
                    }
                    _ => elem,
                };
                let mut fields = vec![];
                for x in [lo, hi] {
                    match x {
                        Some(x) => {
                            let te = self.check_expr(cx, x, Some(&elem));
                            let te = self.coerce(cx, te, &elem);
                            fields.push(te);
                        }
                        None => {
                            self.err(cx, "E-TYPE", sp, "open ranges are only supported in slicing (`&x[a..]`)");
                            fields.push(TExpr::err(sp));
                        }
                    }
                }
                let adt = self.lang_adt(if *incl { "RangeInclusive" } else { "Range" });
                TExpr::new(TK::Ctor { adt, variant: 0, fields }, Ty::Adt(adt, vec![elem]), sp)
            }
            ExprKind::Try(inner) => self.check_try(cx, inner, sp),
            ExprKind::Tuple(es) => {
                let exps: Option<Vec<Ty>> = expected.and_then(|t| match self.shallow(cx, t) {
                    Ty::Tuple(v) if v.len() == es.len() => Some(v),
                    _ => None,
                });
                let mut out = vec![];
                for (i, x) in es.iter().enumerate() {
                    let et = exps.as_ref().map(|v| v[i].clone());
                    let te = self.check_expr(cx, x, et.as_ref());
                    let te = match &et {
                        Some(t) => self.coerce(cx, te, t),
                        None => te,
                    };
                    out.push(te);
                }
                let t = if out.is_empty() { Ty::Unit } else { Ty::Tuple(out.iter().map(|x| x.ty.clone()).collect()) };
                TExpr::new(TK::Tuple(out), t, sp)
            }
            ExprKind::Array(es) => {
                let et = match expected.map(|t| self.shallow(cx, t)) {
                    Some(Ty::Array(e, _)) | Some(Ty::Slice(e)) => (*e).clone(),
                    _ => cx.inf.fresh(),
                };
                let mut out = vec![];
                for x in es {
                    let te = self.check_expr(cx, x, Some(&et));
                    out.push(self.coerce(cx, te, &et));
                }
                let n = out.len() as i128;
                TExpr::new(TK::Array(out), Ty::Array(Box::new(et), Box::new(Ty::Const(n))), sp)
            }
            ExprKind::ArrayRepeat(x, n) => {
                let et = match expected.map(|t| self.shallow(cx, t)) {
                    Some(Ty::Array(e, _)) => (*e).clone(),
                    _ => cx.inf.fresh(),
                };
                let te = self.check_expr(cx, x, Some(&et));
                let te = self.coerce(cx, te, &et);
                let cnt = self.const_usize(cx, n);
                if cnt > 1 && !self.is_copy(cx, &te.ty) {
                    let tn = self.tn(cx, &te.ty);
                    self.err(cx, "E-TYPE", sp, format!("`[x; n]` needs a Copy element, `{tn}` is not"));
                }
                TExpr::new(TK::Repeat(Box::new(te), cnt), Ty::Array(Box::new(et), Box::new(Ty::Const(cnt as i128))), sp)
            }
            ExprKind::Struct { path, fields, base } => self.check_struct_lit(cx, path, fields, base.as_deref(), sp),
            ExprKind::Block(b) => self.check_block(cx, b, expected),
            ExprKind::If(c, t, e2) => {
                let ct = self.check_cond(cx, c);
                cx.scopes.push(vec![]);
                let tt = self.check_block(cx, t, if e2.is_some() { expected } else { Some(&Ty::Unit) });
                cx.scopes.pop();
                self.finish_if(cx, ct, tt, e2.as_deref(), expected, sp)
            }
            ExprKind::IfLet(p, scrut, t, e2) => {
                let s = self.check_expr(cx, scrut, None);
                cx.scopes.push(vec![]);
                let st = s.ty.clone();
                let tp = self.check_pat(cx, p, &st, None);
                let cond = TExpr::new(TK::LetCond(Box::new(tp), Box::new(s)), Ty::Bool, sp);
                let tt = self.check_block(cx, t, if e2.is_some() { expected } else { Some(&Ty::Unit) });
                cx.scopes.pop();
                self.finish_if(cx, cond, tt, e2.as_deref(), expected, sp)
            }
            ExprKind::Match(scrut, arms) => self.check_match(cx, scrut, arms, expected, sp),
            ExprKind::While(label, c, b) => {
                let id = self.new_loop(cx, label.clone(), false, sp);
                let ct = self.check_cond(cx, c);
                let bt = self.check_block(cx, b, Some(&Ty::Unit));
                cx.loops.pop();
                TExpr::new(TK::While(id, Box::new(ct), Box::new(bt)), Ty::Unit, sp)
            }
            ExprKind::WhileLet(label, p, scrut, b) => {
                let id = self.new_loop(cx, label.clone(), false, sp);
                let s = self.check_expr(cx, scrut, None);
                cx.scopes.push(vec![]);
                let st = s.ty.clone();
                let tp = self.check_pat(cx, p, &st, None);
                let cond = TExpr::new(TK::LetCond(Box::new(tp), Box::new(s)), Ty::Bool, sp);
                let bt = self.check_block(cx, b, Some(&Ty::Unit));
                cx.scopes.pop();
                cx.loops.pop();
                TExpr::new(TK::While(id, Box::new(cond), Box::new(bt)), Ty::Unit, sp)
            }
            ExprKind::Loop(label, b) => {
                let id = self.new_loop(cx, label.clone(), true, sp);
                let bt = self.check_block(cx, b, Some(&Ty::Unit));
                let fr = cx.loops.pop().unwrap();
                let ty = fr.break_ty.unwrap_or(Ty::Never);
                TExpr::new(TK::Loop(id, Box::new(bt)), ty, sp)
            }
            ExprKind::For { label, par, pat, iter, body } => self.check_for(cx, label.clone(), *par, pat, iter, body, sp),
            ExprKind::Break(label, v) => {
                let Some(fi) = self.find_loop(cx, label.as_deref(), sp) else { return TExpr::new(TK::Error, Ty::Never, sp) };
                let fr = cx.loops[fi].clone();
                let val = v.as_ref().map(|x| {
                    let bt = fr.break_ty.clone();
                    let te = self.check_expr(cx, x, bt.as_ref());
                    Box::new(te)
                });
                if let Some(vv) = &val {
                    if !fr.is_loop {
                        self.err(cx, "E-TYPE", sp, "`break` with a value is only allowed in `loop`");
                    }
                    match &cx.loops[fi].break_ty {
                        Some(t) => {
                            let t = t.clone();
                            if !self.unify(cx, &t, &vv.ty) {
                                self.mismatch(cx, sp, &t, &vv.ty);
                            }
                        }
                        None => cx.loops[fi].break_ty = Some(vv.ty.clone()),
                    }
                } else if fr.is_loop {
                    match &cx.loops[fi].break_ty {
                        Some(t) => {
                            let t = t.clone();
                            self.unify(cx, &t, &Ty::Unit);
                        }
                        None => cx.loops[fi].break_ty = Some(Ty::Unit),
                    }
                }
                TExpr::new(TK::Break(fr.id, val), Ty::Never, sp)
            }
            ExprKind::Continue(label) => {
                let Some(fi) = self.find_loop(cx, label.as_deref(), sp) else { return TExpr::new(TK::Error, Ty::Never, sp) };
                TExpr::new(TK::Continue(cx.loops[fi].id), Ty::Never, sp)
            }
            ExprKind::Return(v) => {
                let rt = cx.ret_stack.last().cloned().unwrap_or(Ty::Unit);
                let val = match v {
                    Some(x) => {
                        let te = self.check_expr(cx, x, Some(&rt));
                        Some(Box::new(self.coerce(cx, te, &rt)))
                    }
                    None => {
                        if !self.unify(cx, &rt, &Ty::Unit) {
                            self.mismatch(cx, sp, &rt, &Ty::Unit);
                        }
                        None
                    }
                };
                TExpr::new(TK::Return(val), Ty::Never, sp)
            }
            ExprKind::Closure { is_move, params, ret, body } => self.check_closure(cx, *is_move, params, ret.as_ref(), body, expected, sp),
            ExprKind::Macro { name, args } => self.check_macro(cx, &name.name, args, expected, sp),
            ExprKind::Det { by, body } => {
                let b = self.check_block(cx, body, expected);
                let ty = b.ty.clone();
                TExpr::new(TK::Det { evidence: by.text(), body: Box::new(b) }, ty, sp)
            }
            ExprKind::Ellipsis => {
                if !self.opts.doc_snippets && cx.role == FileRole::User {
                    self.err(cx, "E-PARSE", sp, "`…` is documentation shorthand, not Mithril syntax (use `todo!()`)");
                }
                TExpr::new(TK::Trap(TrapKind::Elided, None), Ty::Never, sp)
            }
            ExprKind::Async(_) | ExprKind::Await(_) => {
                self.err(cx, "E-ASYNC", sp, "`async`/`.await`: no async in v1 (FF-ASYNC, DR-005)");
                TExpr::err(sp)
            }
            ExprKind::OutOfScope(kw, _) => {
                self.err(cx, &format!("E-OUT-OF-SCOPE-{kw}"), sp, format!("`{}` is outside the X1 subset (note section 12)", kw.to_lowercase()));
                TExpr::err(sp)
            }
            ExprKind::Let(p, scrut) => {
                let s = self.check_expr(cx, scrut, None);
                let st = s.ty.clone();
                let tp = self.check_pat(cx, p, &st, None);
                TExpr::new(TK::LetCond(Box::new(tp), Box::new(s)), Ty::Bool, sp)
            }
        }
    }

    fn check_cond(&mut self, cx: &mut FnCx, c: &ast::Expr) -> TExpr {
        let ct = self.check_expr(cx, c, Some(&Ty::Bool));
        self.coerce(cx, ct, &Ty::Bool)
    }

    fn finish_if(&mut self, cx: &mut FnCx, ct: TExpr, tt: TExpr, e2: Option<&ast::Expr>, expected: Option<&Ty>, sp: Span) -> TExpr {
        match e2 {
            None => {
                let t = self.shallow(cx, &tt.ty);
                if !matches!(t, Ty::Unit | Ty::Never | Ty::Error) {
                    let _ = self.unify(cx, &tt.ty, &Ty::Unit);
                }
                TExpr::new(TK::If(Box::new(ct), Box::new(tt), None), Ty::Unit, sp)
            }
            Some(eb) => {
                let exp = expected.cloned().or_else(|| {
                    let t = cx.inf.shallow(&tt.ty);
                    if matches!(t, Ty::Never) {
                        None
                    } else {
                        Some(tt.ty.clone())
                    }
                });
                let et = self.check_expr(cx, eb, exp.as_ref());
                let t1 = self.shallow(cx, &tt.ty);
                let t2 = self.shallow(cx, &et.ty);
                let ty = if matches!(t1, Ty::Never) {
                    et.ty.clone()
                } else if matches!(t2, Ty::Never) {
                    tt.ty.clone()
                } else {
                    let tt2 = tt.ty.clone();
                    let et2 = et.ty.clone();
                    if !self.unify(cx, &tt2, &et2) {
                        self.mismatch(cx, eb.span, &tt2, &et2);
                    }
                    tt2
                };
                TExpr::new(TK::If(Box::new(ct), Box::new(tt), Some(Box::new(et))), ty, sp)
            }
        }
    }

    fn new_loop(&mut self, cx: &mut FnCx, label: Option<String>, is_loop: bool, sp: Span) -> LoopId {
        let id = cx.n_loops;
        cx.n_loops += 1;
        cx.loop_spans.push(sp);
        cx.loops.push(LoopFrame { id, label, break_ty: None, is_loop, closure_depth: cx.closure_stack.len() });
        id
    }

    fn find_loop(&mut self, cx: &mut FnCx, label: Option<&str>, sp: Span) -> Option<usize> {
        let depth = cx.closure_stack.len();
        for i in (0..cx.loops.len()).rev() {
            if cx.loops[i].closure_depth != depth {
                break;
            }
            match label {
                None => return Some(i),
                Some(l) => {
                    if cx.loops[i].label.as_deref() == Some(l) {
                        return Some(i);
                    }
                }
            }
        }
        self.err(cx, "E-TYPE", sp, "`break`/`continue` outside of a loop");
        None
    }

    fn const_usize(&mut self, cx: &mut FnCx, e: &ast::Expr) -> u64 {
        match &e.kind {
            ExprKind::Lit(Lit::Int(v, _)) => *v as u64,
            ExprKind::Binary(op, a, b) => {
                let x = self.const_usize(cx, a);
                let y = self.const_usize(cx, b);
                match op {
                    BinOp::Add => x.wrapping_add(y),
                    BinOp::Sub => x.wrapping_sub(y),
                    BinOp::Mul => x.wrapping_mul(y),
                    BinOp::Shl => x.checked_shl(y as u32).unwrap_or(0),
                    BinOp::Div if y != 0 => x / y,
                    _ => {
                        self.err(cx, "E-TYPE", e.span, "unsupported constant expression");
                        0
                    }
                }
            }
            ExprKind::Paren(x) => self.const_usize(cx, x),
            ExprKind::Path(p) => {
                let segs: Vec<String> = p.segs.iter().map(|s| s.ident.name.clone()).collect();
                if let Some(Def::Const(c)) = self.p.resolve(&cx.module, &segs) {
                    if let Some(v) = self.p.const_int_value(c) {
                        return v as u64;
                    }
                }
                self.err(cx, "E-TYPE", e.span, "array lengths must be constants");
                0
            }
            _ => {
                self.err(cx, "E-TYPE", e.span, "array lengths must be constants");
                0
            }
        }
    }

    fn check_lit(&mut self, cx: &mut FnCx, l: &Lit, expected: Option<&Ty>, sp: Span) -> TExpr {
        match l {
            Lit::Int(v, suf) => {
                let ty = match suf {
                    Some(s) => crate::program::prim_ty(s).unwrap_or(Ty::Error),
                    None => {
                        let iv = cx.inf.fresh_int();
                        if let Some(t) = expected {
                            let t = self.shallow(cx, t);
                            if t.is_int() {
                                self.unify(cx, &iv, &t);
                            }
                        }
                        iv
                    }
                };
                if ty.is_float() {
                    let text = format!("{v}");
                    return TExpr::new(TK::Lit(LitVal::Str(format!("\u{0}float:{text}"))), ty, sp);
                }
                cx.lit_checks.push((ty.clone(), *v as i128, sp));
                TExpr::new(TK::Lit(LitVal::Int(*v as i128)), ty, sp)
            }
            Lit::Float(text, suf) => {
                let ty = match suf.as_deref() {
                    Some("f32") => Ty::F32,
                    Some("f64") => Ty::F64,
                    Some("f16") => {
                        self.err(cx, "E-FF-F16", sp, "an `f16` literal: f16 is storage only (FF-F16)");
                        Ty::F16
                    }
                    _ => {
                        let fv = cx.inf.fresh_float();
                        if let Some(t) = expected {
                            let t = self.shallow(cx, t);
                            if t.is_float() {
                                self.unify(cx, &fv, &t);
                            }
                        }
                        fv
                    }
                };
                TExpr::new(TK::Lit(LitVal::Str(format!("\u{0}float:{text}"))), ty, sp)
            }
            Lit::Bool(b) => TExpr::new(TK::Lit(LitVal::Bool(*b)), Ty::Bool, sp),
            Lit::Str(s) => TExpr::new(TK::Lit(LitVal::Str(s.clone())), Ty::Ref(false, Box::new(Ty::Str)), sp),
            Lit::Char(c) => TExpr::new(TK::Lit(LitVal::Char(*c)), Ty::Char, sp),
        }
    }

    fn check_unary(&mut self, cx: &mut FnCx, op: UnOp, inner: &ast::Expr, expected: Option<&Ty>, sp: Span, want_mut: bool) -> TExpr {
        match op {
            UnOp::Deref => {
                let te = self.check_expr_m(cx, inner, None, want_mut);
                let t = self.shallow(cx, &te.ty);
                match t {
                    Ty::Ref(_, i) => TExpr::new(TK::Deref(Box::new(te)), *i, sp),
                    Ty::Error => TExpr::err(sp),
                    other => {
                        let tn = self.tn(cx, &other);
                        self.err(cx, "E-TYPE", sp, format!("type `{tn}` cannot be dereferenced"));
                        TExpr::err(sp)
                    }
                }
            }
            UnOp::Neg | UnOp::Not => {
                let te = self.check_expr(cx, inner, expected);
                // `-2147483648` is a negative literal for the range check, as in Rust
                if op == UnOp::Neg {
                    if let ExprKind::Lit(Lit::Int(..)) = &inner.kind {
                        if let Some(last) = cx.lit_checks.last_mut() {
                            if last.2 == inner.span {
                                last.1 = -last.1;
                            }
                        }
                    }
                }
                let t = self.shallow(cx, &te.ty);
                match (&t, op) {
                    (Ty::Int(i), UnOp::Neg) if !i.signed() => {
                        self.err(cx, "E-TYPE", sp, format!("cannot negate unsigned `{}`", i.name()));
                    }
                    (Ty::F16 | Ty::Bf16, _) => {
                        self.err(cx, "E-FF-F16", sp, "arithmetic on `f16`/`bf16` (FF-F16)");
                    }
                    (Ty::Adt(..), UnOp::Neg) => {
                        if let Some(r) = self.user_op(cx, "Neg", "neg", te.clone(), None, sp) {
                            return r;
                        }
                    }
                    (Ty::Bool, UnOp::Not) | (Ty::Int(_), _) | (Ty::IntVar(_), _) | (Ty::Error, _) | (Ty::Infer(_), _) => {}
                    (Ty::F32 | Ty::F64 | Ty::FloatVar(_), UnOp::Neg) => {}
                    _ => {
                        let tn = self.tn(cx, &t);
                        self.err(cx, "E-TYPE", sp, format!("cannot apply unary `{}` to `{tn}`", if op == UnOp::Neg { "-" } else { "!" }));
                    }
                }
                let ty = te.ty.clone();
                TExpr::new(TK::Unary(op, Box::new(te)), ty, sp)
            }
        }
    }

    fn check_binary(&mut self, cx: &mut FnCx, op: BinOp, a: &ast::Expr, b: &ast::Expr, expected: Option<&Ty>, sp: Span) -> TExpr {
        if matches!(op, BinOp::And | BinOp::Or) {
            let x = self.check_expr(cx, a, Some(&Ty::Bool));
            let x = self.coerce(cx, x, &Ty::Bool);
            let y = self.check_expr(cx, b, Some(&Ty::Bool));
            let y = self.coerce(cx, y, &Ty::Bool);
            return TExpr::new(TK::Binary(op, Box::new(x), Box::new(y)), Ty::Bool, sp);
        }
        let hint = if op.is_cmp() { None } else { expected };
        let x = self.check_expr(cx, a, hint);
        let xt = self.shallow(cx, &x.ty);
        if matches!(op, BinOp::Shl | BinOp::Shr) {
            let y = self.check_expr(cx, b, None);
            let yt = self.shallow(cx, &y.ty);
            if !xt.is_int() && !matches!(xt, Ty::Error | Ty::Infer(_)) || !yt.is_int() && !matches!(yt, Ty::Error | Ty::Infer(_)) {
                self.err(cx, "E-TYPE", sp, "shifts are defined on integers");
            }
            let ty = x.ty.clone();
            return TExpr::new(TK::Binary(op, Box::new(x), Box::new(y)), ty, sp);
        }
        // user operator impls
        if let Ty::Adt(aid, _) = &xt {
            let lang = self.p.adts[*aid as usize].lang.clone();
            let builtin_cmp = op.is_cmp();
            if !builtin_cmp || lang.is_none() {
                let tr = match op {
                    BinOp::Add => Some(("Add", "add")),
                    BinOp::Sub => Some(("Sub", "sub")),
                    BinOp::Mul => Some(("Mul", "mul")),
                    BinOp::Div => Some(("Div", "div")),
                    BinOp::Rem => Some(("Rem", "rem")),
                    _ => None,
                };
                if let Some((tn, mn)) = tr {
                    let y = self.check_expr(cx, b, Some(&x.ty));
                    if let Some(r) = self.user_op(cx, tn, mn, x.clone(), Some(y.clone()), sp) {
                        return r;
                    }
                    let xn = self.tn(cx, &x.ty);
                    let yn = self.tn(cx, &y.ty);
                    self.err(cx, "E-TYPE", sp, format!("no implementation for `{xn} {} {yn}`", op.sym()));
                    return TExpr::err(sp);
                }
            }
        }
        // `a + &b`, `&a + b`, `&a == &b`: Rust's operator impls for references to primitives
        // (comparisons only when both operands are references)
        let (x, y) = if op.is_cmp() {
            let x_is_ref = matches!(self.shallow(cx, &x.ty), Ty::Ref(..));
            let y = self.check_expr(cx, b, if x_is_ref { None } else { Some(&x.ty) });
            let y_is_ref = matches!(self.shallow(cx, &y.ty), Ty::Ref(..));
            // `String == &str`, `&String == &str`, `&str == String`: Rust's PartialEq impls
            // between the string types; compared as `&str`
            if matches!(op, BinOp::Eq | BinOp::Ne) {
                let xs = self.str_view(cx, x.clone());
                let ys = self.str_view(cx, y.clone());
                if let (Some(xs), Some(ys)) = (xs, ys) {
                    return TExpr::new(TK::Binary(op, Box::new(xs), Box::new(ys)), Ty::Bool, sp);
                }
            }
            if x_is_ref && y_is_ref {
                (self.deref_prim_operand(cx, x), self.deref_prim_operand(cx, y))
            } else {
                (x, y)
            }
        } else {
            let x = self.deref_prim_operand(cx, x);
            let y = self.check_expr(cx, b, Some(&x.ty));
            let y = self.deref_prim_operand(cx, y);
            (x, y)
        };
        let y = self.coerce_operand(cx, y, &x.ty);
        let xt = self.shallow(cx, &x.ty);
        if matches!(xt, Ty::F16 | Ty::Bf16) {
            self.err(cx, "E-FF-F16", sp, "arithmetic or comparison on `f16`/`bf16`: storage only; widen with `.to_f32()` (FF-F16)");
        }
        if op.is_cmp() {
            // PartialEq / PartialOrd
            let base = xt.strip_refs().clone();
            let needs = if matches!(op, BinOp::Eq | BinOp::Ne) { "PartialEq" } else { "PartialOrd" };
            if !base.is_numeric() && !matches!(base, Ty::Bool | Ty::Char | Ty::Error | Ty::Infer(_) | Ty::Unit) {
                if let Some(tr) = self.p.try_lang_trait(needs) {
                    cx.obligations.push((base.clone(), tr, vec![base.clone()], sp));
                }
            }
            return TExpr::new(TK::Binary(op, Box::new(x), Box::new(y)), Ty::Bool, sp);
        }
        let ok = xt.is_numeric() || matches!(xt, Ty::Error | Ty::Infer(_) | Ty::F16 | Ty::Bf16) || (matches!(xt, Ty::Bool) && matches!(op, BinOp::BitAnd | BinOp::BitOr | BinOp::BitXor));
        if !ok {
            let tn = self.tn(cx, &xt);
            self.err(cx, "E-TYPE", sp, format!("cannot apply `{}` to `{tn}`", op.sym()));
        }
        if xt.is_float() && matches!(op, BinOp::BitAnd | BinOp::BitOr | BinOp::BitXor) {
            self.err(cx, "E-TYPE", sp, "bitwise operators are not defined on floats");
        }
        let ty = x.ty.clone();
        TExpr::new(TK::Binary(op, Box::new(x), Box::new(y)), ty, sp)
    }

    /// A `&str` view of a string operand (`String`, `&String`, `str`, `&str`, `&&str`), or None.
    fn str_view(&mut self, cx: &mut FnCx, e: TExpr) -> Option<TExpr> {
        let t = self.shallow(cx, &e.ty);
        let sp = e.span;
        let string_adt = |p: &Program, t: &Ty| matches!(t, Ty::Adt(a, _) if p.adts[*a as usize].lang.as_deref() == Some("String"));
        let str_ref = Ty::Ref(false, Box::new(Ty::Str));
        match &t {
            Ty::Ref(_, inner) => {
                let it = self.shallow(cx, inner);
                if matches!(it, Ty::Str) {
                    Some(e)
                } else if string_adt(self.p, &it) {
                    Some(TExpr::new(TK::Unsize(Box::new(e)), str_ref, sp))
                } else if let Ty::Ref(..) = it {
                    let d = TExpr::new(TK::Deref(Box::new(e)), it.clone(), sp);
                    self.str_view(cx, d)
                } else {
                    None
                }
            }
            Ty::Str => Some(TExpr::new(TK::Borrow(false, Box::new(e)), str_ref, sp)),
            _ if string_adt(self.p, &t) => {
                let b = TExpr::new(TK::Borrow(false, Box::new(e)), Ty::Ref(false, Box::new(t.clone())), sp);
                Some(TExpr::new(TK::Unsize(Box::new(b)), str_ref, sp))
            }
            _ => None,
        }
    }

    fn deref_prim_operand(&mut self, cx: &mut FnCx, e: TExpr) -> TExpr {
        let t = self.shallow(cx, &e.ty);
        if let Ty::Ref(_, inner) = &t {
            let it = self.shallow(cx, inner);
            if it.is_numeric() || matches!(it, Ty::Bool | Ty::Char) {
                let sp = e.span;
                return TExpr::new(TK::Deref(Box::new(e)), it, sp);
            }
        }
        e
    }

    fn coerce_operand(&mut self, cx: &mut FnCx, y: TExpr, want: &Ty) -> TExpr {
        if !self.unify(cx, &y.ty, want) {
            let sp = y.span;
            self.mismatch(cx, sp, want, &y.ty);
        }
        y
    }

    /// An operator trait implemented by a user (or prelude) type: `Add::add(x, y)`.
    fn user_op(&mut self, cx: &mut FnCx, trait_name: &str, method: &str, x: TExpr, y: Option<TExpr>, sp: Span) -> Option<TExpr> {
        let tr = self.p.try_lang_trait(trait_name)?;
        let xt = self.shallow(cx, &x.ty);
        let rhs_ty = y.as_ref().map(|t| t.ty.clone());
        let impls = self.p.impls_of_trait.get(&tr).cloned().unwrap_or_default();
        for iid in impls {
            let im = self.p.impls[iid as usize].clone();
            let snap = cx.inf.snapshot();
            let fresh: Vec<Ty> = im.generics.iter().map(|_| cx.inf.fresh()).collect();
            let st = im.self_ty.subst(&fresh);
            let mut ok = self.unify(cx, &st, &xt);
            if ok {
                if let (Some(rt), Some((_, targs))) = (&rhs_ty, &im.trait_) {
                    if let Some(a0) = targs.first() {
                        ok = self.unify(cx, &a0.subst(&fresh), rt);
                    }
                }
            }
            if ok {
                if let Some(fid) = im.methods.get(method) {
                    let f = &self.p.fns[*fid as usize];
                    let mut substs = fresh.clone();
                    for _ in f.n_parent..f.generics.len() {
                        substs.push(cx.inf.fresh());
                    }
                    let ret = f.ret.subst(&substs);
                    let mut args = vec![x];
                    if let Some(y) = y {
                        args.push(y);
                    }
                    let ret = self.shallow(cx, &ret);
                    return Some(TExpr::new(TK::Call { f: *fid, substs, args }, ret, sp));
                }
            }
            cx.inf.rollback(snap);
        }
        None
    }

    // ------------------------------------------------------------------ paths
    fn check_path_expr(&mut self, cx: &mut FnCx, p: &ast::Path, expected: Option<&Ty>, sp: Span) -> TExpr {
        let segs: Vec<String> = p.segs.iter().map(|s| s.ident.name.clone()).collect();
        if segs.len() == 1 && p.segs[0].generics.is_none() {
            let n = &segs[0];
            if let Some(l) = self.lookup_local(cx, n) {
                let t = cx.locals[l as usize].ty.clone();
                return TExpr::new(TK::Local(l), t, sp);
            }
            // fields in scope (invariant bodies)
            if let Some(adt) = cx.field_scope {
                if let Some(fi) = self.p.adts[adt as usize].variants.first().and_then(|v| v.fields.iter().position(|f| &f.name == n)) {
                    let selfl = self.lookup_local(cx, "self").unwrap();
                    let st = cx.locals[selfl as usize].ty.clone();
                    let inner = st.deref_ty().cloned().unwrap_or(Ty::Error);
                    let substs = match &inner {
                        Ty::Adt(_, xs) => xs.clone(),
                        _ => vec![],
                    };
                    let ft = self.p.adts[adt as usize].variants[0].fields[fi].ty.subst(&substs);
                    let base = TExpr::new(TK::Deref(Box::new(TExpr::new(TK::Local(selfl), st, sp))), inner, sp);
                    return TExpr::new(TK::Field(Box::new(base), fi as u32), ft, sp);
                }
            }
        }
        // associated consts of primitive types (u32::MAX, f32::NAN, isize::MAX)
        if segs.len() == 2 {
            if let Some(t) = crate::program::prim_ty(&segs[0]) {
                if let Some(c) = self.prim_const(&t, &segs[1], sp) {
                    return c;
                }
            }
        }
        let turbofish: Option<Vec<ast::GenericArg>> = p.segs.last().and_then(|s| s.generics.clone());
        match self.resolve_value(cx, p, &segs) {
            Some(Value::Local(l)) => {
                let t = cx.locals[l as usize].ty.clone();
                TExpr::new(TK::Local(l), t, sp)
            }
            Some(Value::Fn(fid, parent_substs)) => {
                let (substs, _) = self.instantiate_fn(cx, fid, parent_substs, turbofish.as_deref(), sp);
                let f = &self.p.fns[fid as usize];
                let ps: Vec<Ty> = f.params.iter().map(|x| x.ty.subst(&substs)).collect();
                let r = f.ret.subst(&substs);
                TExpr::new(TK::FnRef(fid, substs), Ty::FnPtr(ps, Box::new(r)), sp)
            }
            Some(Value::Const(c)) => {
                let t = self.p.consts[c as usize].ty.clone();
                TExpr::new(TK::Const(c), t, sp)
            }
            Some(Value::Variant(adt, v)) => {
                let (t, substs) = self.adt_fresh_substs(cx, adt);
                if let Some(ga) = &turbofish {
                    self.apply_turbofish(cx, &substs, ga);
                }
                let vd = &self.p.adts[adt as usize].variants[v as usize];
                if vd.unit || (vd.fields.is_empty() && !vd.tuple) {
                    TExpr::new(TK::Ctor { adt, variant: v, fields: vec![] }, t, sp)
                } else if vd.tuple {
                    // a tuple constructor used as a function value
                    let ps: Vec<Ty> = vd.fields.iter().map(|f| f.ty.subst(&substs)).collect();
                    let _ = expected;
                    TExpr::new(TK::Error, Ty::FnPtr(ps, Box::new(t)), sp)
                } else {
                    self.err(cx, "E-TYPE", sp, format!("`{}` is a struct variant: use `{} {{ .. }}`", p.text(), p.text()));
                    TExpr::err(sp)
                }
            }
            Some(Value::UnitStruct(adt)) => {
                let (t, _) = self.adt_fresh_substs(cx, adt);
                TExpr::new(TK::Ctor { adt, variant: 0, fields: vec![] }, t, sp)
            }
            Some(Value::TraitMethod(tr, fid, self_ty)) => {
                // a trait method used as a value; callers handle the call form
                let _ = (tr, self_ty);
                let (substs, _) = self.instantiate_fn(cx, fid, None, turbofish.as_deref(), sp);
                let f = &self.p.fns[fid as usize];
                let ps: Vec<Ty> = f.params.iter().map(|x| x.ty.subst(&substs)).collect();
                let r = f.ret.subst(&substs);
                TExpr::new(TK::FnRef(fid, substs), Ty::FnPtr(ps, Box::new(r)), sp)
            }
            Some(Value::AssocConst(t, v)) => TExpr::new(TK::Lit(v), t, sp),
            None => {
                let n = p.text();
                if n == "Instant::now" || n.ends_with("Instant::now") {
                    self.err(cx, "E-UNRESOLVED", sp, "cannot find `Instant`: add `use std::time::Instant;`");
                } else if is_dc_value_path(&n) {
                    self.err(cx, "E-FF-CELL", sp, format!("`{n}`: interior mutability, shared ownership and unscoped threads are rejected (FF-CELL)"));
                } else {
                    self.err(cx, "E-UNRESOLVED", sp, format!("cannot find value `{n}` in this scope"));
                }
                TExpr::err(sp)
            }
        }
    }

    fn prim_const(&mut self, t: &Ty, name: &str, sp: Span) -> Option<TExpr> {
        match t {
            Ty::Int(i) => {
                let v = match name {
                    "MAX" => i.max_val(),
                    "MIN" => i.min_val(),
                    "BITS" => return Some(TExpr::new(TK::Lit(LitVal::Int(i.bits() as i128)), Ty::Int(IntTy::U32), sp)),
                    _ => return None,
                };
                Some(TExpr::new(TK::Lit(LitVal::Int(v)), t.clone(), sp))
            }
            Ty::F32 => {
                let v: f32 = match name {
                    // f32::NAN: Rust does not promise a bit pattern; mithi uses the canonical
                    // 0x7fc00000 and the checker treats f32::NAN as raw (note section 5.3)
                    "NAN" => f32::from_bits(0x7fc0_0000),
                    "INFINITY" => f32::INFINITY,
                    "NEG_INFINITY" => f32::NEG_INFINITY,
                    "MAX" => f32::MAX,
                    "MIN" => f32::MIN,
                    "EPSILON" => f32::EPSILON,
                    "MIN_POSITIVE" => f32::MIN_POSITIVE,
                    _ => return None,
                };
                Some(TExpr::new(TK::Lit(LitVal::Float(v.to_bits() as u64)), Ty::F32, sp))
            }
            Ty::F64 => {
                let v: f64 = match name {
                    "NAN" => f64::from_bits(0x7ff8_0000_0000_0000),
                    "INFINITY" => f64::INFINITY,
                    "NEG_INFINITY" => f64::NEG_INFINITY,
                    "MAX" => f64::MAX,
                    "MIN" => f64::MIN,
                    "EPSILON" => f64::EPSILON,
                    _ => return None,
                };
                Some(TExpr::new(TK::Lit(LitVal::Float(v.to_bits())), Ty::F64, sp))
            }
            _ => None,
        }
    }

    /// The formatting trait a placeholder needs (Display for `{}`, Debug for `{:?}`, LowerHex and
    /// friends for `{:x}`, LowerExp for `{:e}`), when the argument's type lacks it.
    fn fmt_trait_missing(&mut self, cx: &mut FnCx, t: &Ty, ty: &str) -> Option<String> {
        let base = self.shallow(cx, t.strip_refs());
        let tn = self.tn(cx, &base);
        let unknown = matches!(base, Ty::Error | Ty::Infer(_) | Ty::Param(_) | Ty::Opaque(_));
        if unknown {
            return None;
        }
        match ty {
            "" => {
                let ok = base.is_numeric() || matches!(base, Ty::Bool | Ty::Char | Ty::Str | Ty::IntVar(_) | Ty::FloatVar(_)) || matches!(&base, Ty::Adt(a, _) if self.p.adts[*a as usize].lang.as_deref() == Some("String"));
                if ok {
                    None
                } else {
                    Some(format!("`{tn}` does not implement Display (`{{}}`); mithi v0's Display covers numbers, bool, char, str and String"))
                }
            }
            "?" | "x?" | "X?" => {
                if self.fmt_debug(cx, &base, 0) {
                    None
                } else {
                    Some(format!("`{tn}` does not implement Debug (`{{:?}}`): derive it"))
                }
            }
            "x" | "X" | "o" | "b" => {
                if base.is_int() {
                    None
                } else {
                    Some(format!("`{tn}` does not implement the integer radix formats (`{{:{ty}}}`)"))
                }
            }
            "e" | "E" => {
                if base.is_numeric() || matches!(base, Ty::IntVar(_) | Ty::FloatVar(_)) {
                    None
                } else {
                    Some(format!("`{tn}` does not implement LowerExp / UpperExp (`{{:{ty}}}`)"))
                }
            }
            _ => None,
        }
    }

    fn fmt_debug(&mut self, cx: &mut FnCx, t: &Ty, depth: u32) -> bool {
        if depth > 8 {
            return true;
        }
        let t = self.shallow(cx, t);
        match &t {
            Ty::Ref(_, x) | Ty::Slice(x) | Ty::Array(x, _) => self.fmt_debug(cx, x, depth + 1),
            Ty::Tuple(v) => v.clone().iter().all(|x| self.fmt_debug(cx, x, depth + 1)),
            Ty::Adt(a, xs) => {
                let ad = &self.p.adts[*a as usize];
                if !ad.derives("Debug") && ad.role != FileRole::Std {
                    return false;
                }
                if ad.role == FileRole::Std && !matches!(ad.lang.as_deref(), Some("Option") | Some("Result") | Some("Vec") | Some("String") | Some("Ordering") | Some("Reverse") | Some("Range") | Some("RangeInclusive") | Some("IoError") | Some("Aligned")) {
                    return false;
                }
                xs.clone().iter().all(|x| self.fmt_debug(cx, x, depth + 1))
            }
            Ty::Closure(_) | Ty::FnPtr(..) => matches!(t, Ty::FnPtr(..)),
            _ => true,
        }
    }

    fn apply_turbofish(&mut self, cx: &mut FnCx, substs: &[Ty], ga: &[ast::GenericArg]) {
        for (i, g) in ga.iter().enumerate() {
            if let (ast::GenericArg::Type(t), Some(s)) = (g, substs.get(i)) {
                let lt = self.lower_body_ty(cx, t);
                let s = s.clone();
                self.unify(cx, &s, &lt);
            }
        }
    }

    /// Resolve a value path: locals, functions, consts, variants, associated items.
    fn resolve_value(&mut self, cx: &mut FnCx, p: &ast::Path, segs: &[String]) -> Option<Value> {
        if segs.len() == 1 {
            if let Some(l) = self.lookup_local(cx, &segs[0]) {
                return Some(Value::Local(l));
            }
        }
        match self.p.resolve(&cx.module, segs) {
            Some(Def::Fn(f)) => return Some(Value::Fn(f, None)),
            Some(Def::Const(c)) => return Some(Value::Const(c)),
            Some(Def::Variant(a, v)) => return Some(Value::Variant(a, v)),
            Some(Def::Adt(a)) => {
                let ad = &self.p.adts[a as usize];
                if ad.kind == AdtKind::Struct && ad.variants.first().map(|v| v.unit || v.tuple).unwrap_or(false) {
                    if ad.variants[0].unit {
                        return Some(Value::UnitStruct(a));
                    }
                    return Some(Value::Variant(a, 0));
                }
                return None;
            }
            _ => {}
        }
        if segs.len() >= 2 {
            // Type::item
            let (base_segs, item) = (&segs[..segs.len() - 1], &segs[segs.len() - 1]);
            let base_generics = p.segs[segs.len() - 2].generics.clone();
            let base_ty: Option<Ty> = if base_segs.len() == 1 && base_segs[0] == "Self" {
                cx.self_ty.clone()
            } else if base_segs.len() == 1 && cx.generics.iter().any(|g| g.name == base_segs[0]) {
                let i = cx.generics.iter().position(|g| g.name == base_segs[0]).unwrap();
                Some(Ty::Param(i as u32))
            } else {
                match self.p.resolve(&cx.module, base_segs) {
                    Some(Def::Adt(a)) => {
                        let n = self.p.adts[a as usize].generics.len();
                        let mut args: Vec<Ty> = (0..n).map(|_| cx.inf.fresh()).collect();
                        if let Some(ga) = &base_generics {
                            let mut k = 0;
                            for g in ga {
                                if let ast::GenericArg::Type(t) = g {
                                    if k < n {
                                        let lt = self.lower_body_ty(cx, t);
                                        args[k] = lt;
                                    }
                                    k += 1;
                                }
                            }
                        }
                        Some(Ty::Adt(a, args))
                    }
                    Some(Def::Prim(n)) => crate::program::prim_ty(&n),
                    Some(Def::Trait(tr)) => {
                        // Trait::method (UFCS): Self is inferred from the arguments
                        let fid = *self.p.traits[tr as usize].methods.get(item)?;
                        let st = cx.inf.fresh();
                        return Some(Value::TraitMethod(tr, fid, st));
                    }
                    _ => None,
                }
            };
            let bt = base_ty?;
            let bt = self.shallow(cx, &bt);
            // enum variant through Self / alias
            if let Ty::Adt(a, _) = &bt {
                if self.p.adts[*a as usize].kind == AdtKind::Enum {
                    if let Some(i) = self.p.adts[*a as usize].variants.iter().position(|v| &v.name == item) {
                        return Some(Value::Variant(*a, i as u32));
                    }
                }
            }
            if let Some(t) = crate::program::prim_ty(&self.p.ty_name(&bt)) {
                let _ = t;
            }
            // associated function: inherent impls first, then traits
            if let Some((fid, substs)) = self.find_assoc_fn(cx, &bt, item) {
                return Some(Value::Fn(fid, Some(substs)));
            }
            // a provided or derived trait method on a concrete type: `Rect::default()`
            if !matches!(bt, Ty::Param(_)) {
                let ntr = self.p.traits.len() as TraitId;
                for tid in 0..ntr {
                    let Some(&fid) = self.p.traits[tid as usize].methods.get(item) else { continue };
                    let ntg = self.p.traits[tid as usize].generics.len();
                    let targs: Vec<Ty> = (1..ntg).map(|_| cx.inf.fresh()).collect();
                    let snap = cx.inf.snapshot();
                    let ok = {
                        let mut s = self.solver(cx);
                        s.implements(&bt, tid, &targs)
                    };
                    cx.inf.rollback(snap);
                    if ok {
                        return Some(Value::TraitMethod(tid, fid, bt.clone()));
                    }
                }
            }
            // a trait method through a type parameter's bound: `T::default()`
            if let Ty::Param(_) = bt {
                for tid in self.bound_traits(cx, &bt) {
                    if let Some(fid) = self.p.traits[tid as usize].methods.get(item) {
                        return Some(Value::TraitMethod(tid, *fid, bt.clone()));
                    }
                }
            }
            // impl consts
            for im in &self.p.impls {
                if let Some((t, v)) = im.consts.get(item) {
                    let snap = cx.inf.snapshot();
                    let fresh: Vec<Ty> = im.generics.iter().map(|_| cx.inf.fresh()).collect();
                    if self.unify(cx, &im.self_ty.subst(&fresh), &bt) {
                        if let ExprKind::Lit(Lit::Int(n, _)) = &v.kind {
                            return Some(Value::AssocConst(t.subst(&fresh), LitVal::Int(*n as i128)));
                        }
                    }
                    cx.inf.rollback(snap);
                }
            }
        }
        None
    }

    fn bound_traits(&self, cx: &FnCx, t: &Ty) -> Vec<TraitId> {
        let mut out = vec![];
        if let Ty::Param(i) = t {
            if let Some(g) = cx.generics.get(*i as usize) {
                for b in &g.bounds {
                    if let BoundDef::Trait { tr, .. } = b {
                        let mut stack = vec![*tr];
                        while let Some(x) = stack.pop() {
                            if out.contains(&x) {
                                continue;
                            }
                            out.push(x);
                            for s in &self.p.traits[x as usize].supers {
                                if let BoundDef::Trait { tr, .. } = s {
                                    stack.push(*tr);
                                }
                            }
                        }
                    }
                }
            }
        }
        if let Ty::Opaque(bs) = t {
            for (tr, _) in bs {
                out.push(*tr);
            }
        }
        out
    }

    /// Find `Type::name` among inherent impls (and trait impls) of a type.
    fn find_assoc_fn(&mut self, cx: &mut FnCx, bt: &Ty, name: &str) -> Option<(FnId, Vec<Ty>)> {
        let n_impls = self.p.impls.len();
        for pass in 0..2 {
            for iid in 0..n_impls {
                let im = self.p.impls[iid].clone();
                if (pass == 0) != im.trait_.is_none() {
                    continue;
                }
                let Some(fid) = im.methods.get(name) else { continue };
                let snap = cx.inf.snapshot();
                let fresh: Vec<Ty> = im.generics.iter().map(|_| cx.inf.fresh()).collect();
                if self.unify(cx, &im.self_ty.subst(&fresh), bt) && self.impl_bounds_ok(cx, iid as u32, &fresh) {
                    return Some((*fid, fresh));
                }
                cx.inf.rollback(snap);
            }
        }
        // provided (default) trait methods: Default::default via a derive, Iterator adapters
        None
    }

    fn impl_bounds_ok(&mut self, cx: &mut FnCx, iid: ImplId, substs: &[Ty]) -> bool {
        let mut s = self.solver(cx);
        s.impl_bounds_hold(iid, substs, 0)
    }

    /// Fresh substitutions for a function's generics (parent substs given or fresh), with Fn bounds
    /// recorded for closure checking and trait bounds as obligations.
    fn instantiate_fn(&mut self, cx: &mut FnCx, fid: FnId, parent: Option<Vec<Ty>>, turbofish: Option<&[ast::GenericArg]>, sp: Span) -> (Vec<Ty>, Vec<Ty>) {
        let f = self.p.fns[fid as usize].clone();
        let mut substs: Vec<Ty> = match parent {
            Some(p) => p,
            None => (0..f.n_parent).map(|_| cx.inf.fresh()).collect(),
        };
        while substs.len() < f.n_parent {
            substs.push(cx.inf.fresh());
        }
        let own_start = substs.len();
        for _ in f.n_parent..f.generics.len() {
            substs.push(cx.inf.fresh());
        }
        if let Some(ga) = turbofish {
            let mut k = own_start;
            for g in ga {
                match g {
                    ast::GenericArg::Type(t) => {
                        if k < substs.len() {
                            let lt = self.lower_body_ty(cx, t);
                            let s = substs[k].clone();
                            self.unify(cx, &s, &lt);
                        }
                        k += 1;
                    }
                    ast::GenericArg::Const(_) => k += 1,
                    _ => {}
                }
            }
        }
        for (i, g) in f.generics.iter().enumerate() {
            for b in &g.bounds {
                match b {
                    BoundDef::Fn { kind, params, ret } => {
                        if let Ty::Infer(v) = cx.inf.shallow(&substs[i]) {
                            let ps: Vec<Ty> = params.iter().map(|t| t.subst(&substs)).collect();
                            let r = ret.subst(&substs);
                            cx.inf.fn_bounds.insert(v, (*kind, ps, r));
                        }
                    }
                    BoundDef::Trait { tr, args, .. } => {
                        let a: Vec<Ty> = args.iter().map(|t| t.subst(&substs)).collect();
                        cx.obligations.push((substs[i].clone(), *tr, a, sp));
                    }
                }
            }
        }
        (substs, vec![])
    }

    // ------------------------------------------------------------------ calls
    fn check_call(&mut self, cx: &mut FnCx, callee: &ast::Expr, args: &[ast::Expr], expected: Option<&Ty>, sp: Span) -> TExpr {
        if let ExprKind::Path(p) = &callee.kind {
            let segs: Vec<String> = p.segs.iter().map(|s| s.ident.name.clone()).collect();
            let is_local = segs.len() == 1 && self.lookup_local(cx, &segs[0]).is_some();
            if !is_local {
                // Dc constructors
                let text = p.text();
                if is_dc_value_path(&text) {
                    self.err(cx, "E-FF-CELL", sp, format!("`{text}`: interior mutability, shared ownership and unscoped threads are rejected; use Mutex<T>::with_lock, Frozen<T> or scoped threads (FF-CELL)"));
                    for a in args {
                        self.check_expr(cx, a, None);
                    }
                    return TExpr::err(sp);
                }
                if segs.len() == 2 && segs[0] == "Box" && segs[1] == "new" {
                    self.err(cx, "E-UNRESOLVED", sp, "`Box` is not in mithi's X1 std");
                    return TExpr::err(sp);
                }
                let turbofish: Option<Vec<ast::GenericArg>> = p.segs.last().and_then(|s| s.generics.clone());
                match self.resolve_value(cx, p, &segs) {
                    Some(Value::Fn(fid, parent)) => {
                        let (substs, _) = self.instantiate_fn(cx, fid, parent, turbofish.as_deref(), sp);
                        return self.finish_call(cx, fid, substs, args, expected, sp, None);
                    }
                    Some(Value::TraitMethod(tr, fid, self_ty)) => {
                        // UFCS: Trait::method(args) or T::method(args)
                        let (mut substs, _) = self.instantiate_fn(cx, fid, Some(vec![self_ty.clone()]), turbofish.as_deref(), sp);
                        let n_tr = self.p.traits[tr as usize].generics.len();
                        while substs.len() < n_tr {
                            substs.insert(1, cx.inf.fresh());
                        }
                        let te = self.finish_call(cx, fid, substs.clone(), args, expected, sp, None);
                        // if Self became concrete, resolve to the impl
                        let st = self.shallow(cx, &substs[0]);
                        if let TK::Call { args: targs, .. } = te.kind.clone() {
                            if let Some(c) = self.resolve_trait_call(cx, tr, fid, &st, &substs, targs, te.ty.clone(), sp) {
                                return c;
                            }
                        }
                        return te;
                    }
                    Some(Value::Variant(adt, v)) => {
                        let vd = self.p.adts[adt as usize].variants[v as usize].clone();
                        if !vd.tuple {
                            self.err(cx, "E-TYPE", sp, format!("`{}` is not a tuple constructor", p.text()));
                            return TExpr::err(sp);
                        }
                        let (t, substs) = self.adt_fresh_substs(cx, adt);
                        if let Some(ga) = &turbofish {
                            self.apply_turbofish(cx, &substs, ga);
                        }
                        if let Some(et) = expected {
                            let snap = cx.inf.snapshot();
                            if !self.unify(cx, &t, et) {
                                cx.inf.rollback(snap);
                            }
                        }
                        if args.len() != vd.fields.len() {
                            self.err(cx, "E-TYPE", sp, format!("`{}` takes {} field(s), {} given", p.text(), vd.fields.len(), args.len()));
                        }
                        let mut fields = vec![];
                        for (i, a) in args.iter().enumerate() {
                            let ft = vd.fields.get(i).map(|f| f.ty.subst(&substs)).unwrap_or(Ty::Error);
                            let te = self.check_expr(cx, a, Some(&ft));
                            fields.push(self.coerce(cx, te, &ft));
                        }
                        return TExpr::new(TK::Ctor { adt, variant: v, fields }, t, sp);
                    }
                    Some(Value::Local(_)) => {}
                    Some(Value::Const(_)) | Some(Value::UnitStruct(_)) | Some(Value::AssocConst(..)) => {
                        self.err(cx, "E-TYPE", sp, format!("`{}` is not callable", p.text()));
                        return TExpr::err(sp);
                    }
                    None => {
                        let n = p.text();
                        if n == "footprint" {
                            self.err(cx, "E-TYPE", sp, "`footprint(..)` is a ghost form allowed only as `ensures footprint(result) == place`");
                        } else if n.ends_with("thread::spawn") || n == "spawn" {
                            self.err(cx, "E-FF-CELL", sp, "unscoped `thread::spawn`: use scoped threads (FF-CELL)");
                        } else if is_whole_task_canon(&n) {
                            self.err(cx, "E-X1-NOTYET-CANON", sp, format!("`{n}` is a whole-task canon helper, not in the X1 std (X1 design 5.1a)"));
                        } else {
                            self.err(cx, "E-UNRESOLVED", sp, format!("cannot find function `{n}` in this scope"));
                        }
                        for a in args {
                            self.check_expr(cx, a, None);
                        }
                        return TExpr::err(sp);
                    }
                }
            }
        }
        // a value call: closure, fn pointer, Fn-bounded parameter
        let f = self.check_expr(cx, callee, None);
        let ft = self.shallow(cx, &f.ty);
        let (ps, ret): (Vec<Ty>, Ty) = match &ft {
            Ty::Closure(c) => match cx.closure_sigs.get(c) {
                Some((ps, r, _)) => (ps.clone(), r.clone()),
                None => (vec![], Ty::Error),
            },
            Ty::FnPtr(ps, r) => (ps.clone(), (**r).clone()),
            Ty::Param(i) => match cx.generics.get(*i as usize).and_then(crate::lower::fn_bound) {
                Some((_, ps, r)) => (ps, r),
                None => {
                    self.err(cx, "E-TYPE", sp, "this value is not callable (no Fn bound)");
                    (vec![], Ty::Error)
                }
            },
            Ty::Ref(_, inner) => match self.shallow(cx, inner) {
                Ty::Closure(c) => match cx.closure_sigs.get(&c) {
                    Some((ps, r, _)) => (ps.clone(), r.clone()),
                    None => (vec![], Ty::Error),
                },
                Ty::Param(i) => match cx.generics.get(i as usize).and_then(crate::lower::fn_bound) {
                    Some((_, ps, r)) => (ps, r),
                    None => (vec![], Ty::Error),
                },
                _ => (vec![], Ty::Error),
            },
            Ty::Infer(v) => match cx.inf.fn_bounds.get(v) {
                Some((_, ps, r)) => (ps.clone(), r.clone()),
                None => (vec![], Ty::Error),
            },
            Ty::Error => (vec![], Ty::Error),
            _ => {
                let tn = self.tn(cx, &ft);
                self.err(cx, "E-TYPE", sp, format!("type `{tn}` is not callable"));
                (vec![], Ty::Error)
            }
        };
        if !ps.is_empty() && ps.len() != args.len() {
            self.err(cx, "E-TYPE", sp, format!("this closure takes {} argument(s), {} given", ps.len(), args.len()));
        }
        let mut targs = vec![];
        for (i, a) in args.iter().enumerate() {
            let pt = ps.get(i).cloned();
            let te = self.check_expr(cx, a, pt.as_ref());
            let te = match &pt {
                Some(t) => self.coerce(cx, te, t),
                None => te,
            };
            targs.push(te);
        }
        TExpr::new(TK::CallValue(Box::new(f), targs), ret, sp)
    }

    /// Check arguments against a resolved function's parameters.
    fn finish_call(&mut self, cx: &mut FnCx, fid: FnId, substs: Vec<Ty>, args: &[ast::Expr], expected: Option<&Ty>, sp: Span, recv: Option<TExpr>) -> TExpr {
        let f = self.p.fns[fid as usize].clone();
        let n_expected = f.params.len();
        let given = args.len() + recv.is_some() as usize;
        if n_expected != given {
            self.err(cx, "E-TYPE", sp, format!("`{}` takes {} argument(s), {} given", f.name, n_expected - recv.is_some() as usize, args.len()));
        }
        let ret = {
            let r = f.ret.subst(&substs);
            self.shallow(cx, &r)
        };
        // let the expected type flow into generic results before checking closure arguments
        if let Some(et) = expected {
            let snap = cx.inf.snapshot();
            if !self.unify(cx, &ret, et) {
                cx.inf.rollback(snap);
            }
        }
        let mut targs = vec![];
        let mut pi = 0;
        if let Some(r) = recv {
            targs.push(r);
            pi = 1;
        }
        for a in args {
            let pt = f.params.get(pi).map(|p| p.ty.subst(&substs));
            let pt = pt.map(|t| {
                let z = cx.inf.zonk(&t);
                let mut s = self.solver(cx);
                deep_normalize(&mut s, &z)
            });
            let te = self.check_expr(cx, a, pt.as_ref());
            let te = match &pt {
                Some(t) => self.coerce(cx, te, t),
                None => te,
            };
            targs.push(te);
            pi += 1;
        }
        let ret = self.shallow(cx, &f.ret.subst(&substs));
        let ret = {
            let z = cx.inf.zonk(&ret);
            let mut s = self.solver(cx);
            deep_normalize(&mut s, &z)
        };
        // builtin result fixups
        if let Some(b) = &f.builtin {
            match b.as_str() {
                "iter_copied" | "iter_cloned" => {
                    let item = self.iter_item(cx, &substs[0]);
                    let base = match self.shallow(cx, &item) {
                        Ty::Ref(_, x) => (*x).clone(),
                        x => x,
                    };
                    let it = Ty::Adt(self.lang_adt("Iter"), vec![base]);
                    return TExpr::new(TK::Call { f: fid, substs, args: targs }, it, sp);
                }
                "iter_sum" | "iter_product" | "iter_collect" => {
                    let item = self.iter_item(cx, &substs[0]);
                    cx.fixups.push((ret.clone(), b.clone(), item, sp));
                }
                "iter_max" | "iter_min" => {
                    let item = self.iter_item(cx, &substs[0]);
                    if let Some(ord) = self.p.try_lang_trait("Ord") {
                        cx.obligations.push((item, ord, vec![], sp));
                    }
                }
                _ => {}
            }
        }
        TExpr::new(TK::Call { f: fid, substs, args: targs }, ret, sp)
    }

    fn iter_item(&mut self, cx: &mut FnCx, self_ty: &Ty) -> Ty {
        let it = self.p.lang_trait("Iterator");
        let t = Ty::Assoc(Box::new(self_ty.clone()), it, "Item".into());
        let z = cx.inf.zonk(&t);
        let mut s = self.solver(cx);
        s.normalize(&z)
    }

    /// A trait method called on a now-known Self type: resolve to the impl's method.
    #[allow(clippy::too_many_arguments)]
    fn resolve_trait_call(&mut self, cx: &mut FnCx, tr: TraitId, decl: FnId, st: &Ty, substs: &[Ty], args: Vec<TExpr>, ret: Ty, sp: Span) -> Option<TExpr> {
        let mname = self.p.fns[decl as usize].name.clone();
        match st {
            Ty::Param(_) | Ty::Infer(_) | Ty::Opaque(_) => Some(TExpr::new(
                TK::TraitCall { tr, method: mname, decl, self_ty: st.clone(), substs: substs.to_vec(), args },
                ret,
                sp,
            )),
            _ => {
                if let Some((fid, isubsts)) = self.impl_method(cx, tr, st, &mname) {
                    let mut s2 = isubsts;
                    let own = &substs[self.p.fns[decl as usize].n_parent..];
                    s2.extend_from_slice(own);
                    return Some(TExpr::new(TK::Call { f: fid, substs: s2, args }, ret, sp));
                }
                // derived / builtin implementation: keep the trait call (dispatched at run time)
                Some(TExpr::new(TK::TraitCall { tr, method: mname, decl, self_ty: st.clone(), substs: substs.to_vec(), args }, ret, sp))
            }
        }
    }

    fn impl_method(&mut self, cx: &mut FnCx, tr: TraitId, st: &Ty, name: &str) -> Option<(FnId, Vec<Ty>)> {
        let impls = self.p.impls_of_trait.get(&tr).cloned().unwrap_or_default();
        for iid in impls {
            let im = self.p.impls[iid as usize].clone();
            let Some(fid) = im.methods.get(name) else { continue };
            let snap = cx.inf.snapshot();
            let fresh: Vec<Ty> = im.generics.iter().map(|_| cx.inf.fresh()).collect();
            if self.unify(cx, &im.self_ty.subst(&fresh), st) {
                return Some((*fid, fresh));
            }
            cx.inf.rollback(snap);
        }
        None
    }

    // ------------------------------------------------------------------ method calls
    #[allow(clippy::too_many_arguments)]
    fn check_method_call(&mut self, cx: &mut FnCx, recv: &ast::Expr, method: &ast::Ident, generics: Option<&[ast::GenericArg]>, args: &[ast::Expr], expected: Option<&Ty>, sp: Span, want_mut: bool) -> TExpr {
        let _ = want_mut;
        let r = self.check_expr_m(cx, recv, None, false);
        let name = method.name.as_str();
        // Dc method names
        if name == "borrow_mut" || name == "get_mut" && false {
            // (RefCell is rejected at its type)
        }
        let rt = self.shallow(cx, &r.ty);
        if matches!(rt, Ty::Error) {
            for a in args {
                self.check_expr(cx, a, None);
            }
            return TExpr::err(sp);
        }
        if let Ty::Infer(_) = rt {
            self.err(cx, "E-TYPE", recv.span, format!("type annotations needed before calling `.{name}()`"));
            for a in args {
                self.check_expr(cx, a, None);
            }
            return TExpr::err(sp);
        }
        // closure-typed field call `(self.f)(x)` is a CallValue; `x.f(...)` with f a field is not a method
        match self.probe_method(cx, r.clone(), name, sp) {
            Some(Probe { recv: adj, fid, parent, trait_dispatch }) => {
                let (substs, _) = self.instantiate_fn(cx, fid, Some(parent.clone()), generics, sp);
                let te = self.finish_call(cx, fid, substs.clone(), args, expected, sp, Some(adj));
                if let Some((tr, st)) = trait_dispatch {
                    if let TK::Call { args: targs, .. } = te.kind.clone() {
                        let mname = self.p.fns[fid as usize].name.clone();
                        return TExpr::new(TK::TraitCall { tr, method: mname, decl: fid, self_ty: st, substs, args: targs }, te.ty, sp);
                    }
                }
                te
            }
            None => {
                let tn = self.tn(cx, &rt);
                let hint = match name {
                    "borrow" | "borrow_mut" => " (RefCell is Dc: FF-CELL)",
                    "lock" => " (use Mutex<T>::with_lock)",
                    _ => "",
                };
                self.err(cx, "E-TYPE", method.span, format!("no method named `{name}` found for `{tn}`{hint}"));
                for a in args {
                    self.check_expr(cx, a, None);
                }
                TExpr::err(sp)
            }
        }
    }

    /// Method probe with auto-deref, unsizing and auto-ref (Rust's probe order).
    fn probe_method(&mut self, cx: &mut FnCx, recv: TExpr, name: &str, sp: Span) -> Option<Probe> {
        let mut cur = recv;
        for _step in 0..8 {
            let t = self.shallow(cx, &cur.ty);
            // Rust's by-value step: at a reference type `&U`, a method of `U` taking `&self` (or
            // `&mut self` through `&mut U`) takes the reference as it is. It wins over methods of
            // `&U` itself, so `s.clone()` with `s: &String` is `String::clone`, not `<&String>::clone`.
            if let Ty::Ref(m, inner) = &t {
                let inner_t = self.shallow(cx, inner);
                if !matches!(inner_t, Ty::Infer(_)) {
                    let snap = cx.inf.snapshot();
                    let nd = self.diags.len();
                    let dcur = TExpr::new(TK::Deref(Box::new(cur.clone())), inner_t.clone(), cur.span);
                    if let Some(pr) = self.probe_at(cx, &dcur, &inner_t, name, sp) {
                        let sm = self.p.fns[pr.fid as usize].self_mode;
                        if matches!(sm, Some(SelfMode::Ref)) || (matches!(sm, Some(SelfMode::RefMut)) && *m) {
                            return Some(pr);
                        }
                    }
                    self.diags.truncate(nd);
                    cx.inf.rollback(snap);
                }
            }
            if let Some(pr) = self.probe_at(cx, &cur, &t, name, sp) {
                return Some(pr);
            }
            // unsizing step: [T; N] / Vec<T> / Buf<T> -> [T]; String -> str
            let uns = match &t {
                Ty::Array(e, _) => Some(Ty::Slice(e.clone())),
                Ty::Adt(a, xs) if matches!(self.p.adts[*a as usize].lang.as_deref(), Some("Vec") | Some("Buf")) => Some(Ty::Slice(Box::new(xs[0].clone()))),
                Ty::Adt(a, _) if self.p.adts[*a as usize].lang.as_deref() == Some("String") => Some(Ty::Str),
                _ => None,
            };
            if let Some(ut) = uns {
                // the unsized place: a deref of an unsize of a borrow of the place
                let sp2 = cur.span;
                let place = self.ensure_place(cx, cur.clone());
                let b = TExpr::new(TK::Borrow(false, Box::new(place)), Ty::Ref(false, Box::new(t.clone())), sp2);
                let u = TExpr::new(TK::Unsize(Box::new(b)), Ty::Ref(false, Box::new(ut.clone())), sp2);
                let uplace = TExpr::new(TK::Deref(Box::new(u)), ut.clone(), sp2);
                if let Some(pr) = self.probe_at(cx, &uplace, &ut, name, sp) {
                    // a &mut self method through the unsize needs a mutable borrow
                    return Some(self.fix_unsize_mut(pr));
                }
            }
            match t {
                Ty::Ref(_, inner) => {
                    let sp2 = cur.span;
                    cur = TExpr::new(TK::Deref(Box::new(cur)), *inner, sp2);
                }
                _ => return None,
            }
        }
        None
    }

    fn fix_unsize_mut(&self, mut pr: Probe) -> Probe {
        // Borrow(true, Deref(Unsize(Borrow(false, p)))) -> make the inner borrow mutable
        if let TK::Borrow(true, inner) = &mut pr.recv.kind {
            if let TK::Deref(u) = &mut inner.kind {
                if let TK::Unsize(b) = &mut u.kind {
                    if let TK::Borrow(m, _) = &mut b.kind {
                        *m = true;
                        if let Ty::Ref(mm, _) = &mut b.ty {
                            *mm = true;
                        }
                    }
                    if let Ty::Ref(mm, _) = &mut u.ty {
                        *mm = true;
                    }
                }
            }
        }
        pr
    }

    fn probe_at(&mut self, cx: &mut FnCx, cur: &TExpr, t: &Ty, name: &str, sp: Span) -> Option<Probe> {
        // inherent impls
        let n_impls = self.p.impls.len();
        for iid in 0..n_impls {
            let im = &self.p.impls[iid];
            if im.trait_.is_some() {
                continue;
            }
            let Some(&fid) = im.methods.get(name) else { continue };
            if self.p.fns[fid as usize].self_mode.is_none() {
                continue;
            }
            let im = im.clone();
            let snap = cx.inf.snapshot();
            let fresh: Vec<Ty> = im.generics.iter().map(|_| cx.inf.fresh()).collect();
            if self.unify(cx, &im.self_ty.subst(&fresh), t) && self.impl_bounds_ok(cx, iid as u32, &fresh) {
                let adj = self.adjust_recv(cx, cur.clone(), fid, t, sp)?;
                return Some(Probe { recv: adj, fid, parent: fresh, trait_dispatch: None });
            }
            cx.inf.rollback(snap);
        }
        // type parameters / opaque types: methods of bound traits
        if matches!(t, Ty::Param(_) | Ty::Opaque(_)) {
            for tid in self.bound_traits(cx, t) {
                if let Some(&fid) = self.p.traits[tid as usize].methods.get(name) {
                    if self.p.fns[fid as usize].self_mode.is_none() {
                        continue;
                    }
                    let mut parent = vec![t.clone()];
                    let ntg = self.p.traits[tid as usize].generics.len();
                    for _ in 1..ntg {
                        parent.push(cx.inf.fresh());
                    }
                    // bound args
                    if let Ty::Param(pi) = t {
                        if let Some(g) = cx.generics.get(*pi as usize).cloned() {
                            for b in &g.bounds {
                                if let BoundDef::Trait { tr, args, .. } = b {
                                    if *tr == tid {
                                        for (k, a) in args.iter().enumerate() {
                                            if k + 1 < parent.len() {
                                                parent[k + 1] = a.clone();
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    let adj = self.adjust_recv(cx, cur.clone(), fid, t, sp)?;
                    return Some(Probe { recv: adj, fid, parent, trait_dispatch: Some((tid, t.clone())) });
                }
            }
            return None;
        }
        // trait impls (and provided methods of implemented traits)
        let ntraits = self.p.traits.len();
        for tid in 0..ntraits as TraitId {
            let Some(&decl) = self.p.traits[tid as usize].methods.get(name) else { continue };
            if self.p.fns[decl as usize].self_mode.is_none() {
                continue;
            }
            // closures: Fn traits have no methods
            let ntg = self.p.traits[tid as usize].generics.len();
            let targs: Vec<Ty> = (1..ntg).map(|_| cx.inf.fresh()).collect();
            let snap = cx.inf.snapshot();
            let implemented = {
                let mut s = self.solver(cx);
                s.implements(t, tid, &targs)
            };
            if !implemented {
                cx.inf.rollback(snap);
                continue;
            }
            // impl's own method, or the trait's provided method
            if let Some((fid, isubsts)) = self.impl_method(cx, tid, t, name) {
                let adj = self.adjust_recv(cx, cur.clone(), fid, t, sp)?;
                return Some(Probe { recv: adj, fid, parent: isubsts, trait_dispatch: None });
            }
            let decl_f = &self.p.fns[decl as usize];
            if decl_f.body.is_some() || decl_f.builtin.is_some() {
                let mut parent = vec![t.clone()];
                parent.extend(targs);
                let adj = self.adjust_recv(cx, cur.clone(), decl, t, sp)?;
                // derived/builtin trait methods (clone, eq, cmp, default) dispatch at run time
                return Some(Probe { recv: adj, fid: decl, parent, trait_dispatch: None });
            }
            cx.inf.rollback(snap);
        }
        None
    }

    /// Adjust the receiver for the method's self mode (by value, &, &mut).
    fn adjust_recv(&mut self, cx: &mut FnCx, cur: TExpr, fid: FnId, t: &Ty, sp: Span) -> Option<TExpr> {
        let mode = self.p.fns[fid as usize].self_mode?;
        let csp = cur.span;
        Some(match mode {
            SelfMode::Value => cur,
            SelfMode::Ref => {
                let place = self.ensure_place(cx, cur);
                TExpr::new(TK::Borrow(false, Box::new(place)), Ty::Ref(false, Box::new(t.clone())), csp)
            }
            SelfMode::RefMut => {
                self.check_mutable_place(cx, &cur, sp, "borrow as mutable");
                let place = self.ensure_place(cx, cur);
                TExpr::new(TK::Borrow(true, Box::new(place)), Ty::Ref(true, Box::new(t.clone())), csp)
            }
        })
    }

    /// A value used where a place is needed is first stored in a temporary place; mithi
    /// represents that as the value itself (the interpreter materialises it).
    fn ensure_place(&mut self, _cx: &mut FnCx, e: TExpr) -> TExpr {
        e
    }

    fn check_mutable_place(&mut self, cx: &mut FnCx, e: &TExpr, sp: Span, what: &str) {
        if !self.place_is_mutable(cx, e) {
            self.err(cx, "E-TYPE", sp, format!("cannot {what} an immutable place (declare it `mut` or reach it through `&mut`)"));
        }
    }

    fn place_is_mutable(&self, cx: &FnCx, e: &TExpr) -> bool {
        match &e.kind {
            TK::Local(l) => cx.locals[*l as usize].mutable || cx.deferred.contains(l) || cx.locals[*l as usize].ty == Ty::Error,
            TK::Field(b, _) | TK::Index(b, _) => self.place_is_mutable(cx, b),
            TK::SliceRange { base, .. } => self.place_is_mutable(cx, base),
            TK::Deref(b) => {
                // the unsized view built by method probing: as mutable as the place it views
                if let TK::Unsize(u) = &b.kind {
                    if let TK::Borrow(_, p) = &u.kind {
                        return self.place_is_mutable(cx, p);
                    }
                }
                match cx.inf.shallow(&b.ty) {
                    Ty::Ref(m, _) => m,
                    _ => true,
                }
            }
            TK::Unsize(b) => self.place_is_mutable(cx, b),
            TK::Borrow(m, _) => *m,
            TK::Error => true,
            // temporaries (call results, literals) are mutable rvalues
            _ => true,
        }
    }

    // ------------------------------------------------------------------ fields and indexing
    fn check_field(&mut self, cx: &mut FnCx, base: &ast::Expr, name: &str, fsp: Span, sp: Span, want_mut: bool) -> TExpr {
        let b = self.check_expr_m(cx, base, None, want_mut);
        let mut cur = b;
        for _ in 0..8 {
            let t = self.shallow(cx, &cur.ty);
            match &t {
                Ty::Adt(a, xs) => {
                    let ad = &self.p.adts[*a as usize];
                    if ad.kind != AdtKind::Enum {
                        if let Some(v) = ad.variants.first() {
                            if let Some(fi) = v.fields.iter().position(|f| f.name == name) {
                                let ft = v.fields[fi].ty.subst(xs);
                                return TExpr::new(TK::Field(Box::new(cur), fi as u32), ft, sp);
                            }
                        }
                        if ad.partial {
                            let an = ad.name.clone();
                            self.err(cx, "E-TYPE", fsp, format!("no field `{name}` on `{an}` (the prelude declares `{an}` partially)"));
                            return TExpr::err(sp);
                        }
                    }
                    let tn = self.tn(cx, &t);
                    self.err(cx, "E-TYPE", fsp, format!("no field `{name}` on type `{tn}`"));
                    return TExpr::err(sp);
                }
                Ty::Tuple(v) => {
                    if let Ok(i) = name.parse::<usize>() {
                        if i < v.len() {
                            let ft = v[i].clone();
                            return TExpr::new(TK::Field(Box::new(cur), i as u32), ft, sp);
                        }
                    }
                    let tn = self.tn(cx, &t);
                    self.err(cx, "E-TYPE", fsp, format!("no field `{name}` on tuple `{tn}`"));
                    return TExpr::err(sp);
                }
                Ty::Ref(_, inner) => {
                    let csp = cur.span;
                    cur = TExpr::new(TK::Deref(Box::new(cur)), (**inner).clone(), csp);
                }
                Ty::Error => return TExpr::err(sp),
                _ => {
                    let tn = self.tn(cx, &t);
                    self.err(cx, "E-TYPE", fsp, format!("no field `{name}` on type `{tn}`"));
                    return TExpr::err(sp);
                }
            }
        }
        TExpr::err(sp)
    }

    fn check_index(&mut self, cx: &mut FnCx, base: &ast::Expr, idx: &ast::Expr, sp: Span, want_mut: bool) -> TExpr {
        let b = self.check_expr_m(cx, base, None, want_mut);
        // range index -> sub-slice place
        if let ExprKind::Range(lo, hi, incl) = &idx.kind {
            let mut cur = b;
            for _ in 0..8 {
                let t = self.shallow(cx, &cur.ty);
                match &t {
                    Ty::Ref(_, inner) => {
                        let csp = cur.span;
                        cur = TExpr::new(TK::Deref(Box::new(cur)), (**inner).clone(), csp);
                        continue;
                    }
                    Ty::Array(e, _) | Ty::Slice(e) => {
                        let e = (**e).clone();
                        return self.slice_range(cx, cur, e, lo.as_deref(), hi.as_deref(), *incl, sp);
                    }
                    Ty::Adt(a, xs) if matches!(self.p.adts[*a as usize].lang.as_deref(), Some("Vec") | Some("Buf")) => {
                        let e = xs[0].clone();
                        return self.slice_range(cx, cur, e, lo.as_deref(), hi.as_deref(), *incl, sp);
                    }
                    Ty::Error => return TExpr::err(sp),
                    _ => {
                        let tn = self.tn(cx, &t);
                        self.err(cx, "E-TYPE", sp, format!("cannot slice `{tn}`"));
                        return TExpr::err(sp);
                    }
                }
            }
            return TExpr::err(sp);
        }
        let mut cur = b;
        for _ in 0..8 {
            let t = self.shallow(cx, &cur.ty);
            match &t {
                Ty::Ref(_, inner) => {
                    let csp = cur.span;
                    cur = TExpr::new(TK::Deref(Box::new(cur)), (**inner).clone(), csp);
                }
                Ty::Array(e, _) | Ty::Slice(e) => {
                    let et = (**e).clone();
                    let i = self.check_expr(cx, idx, Some(&Ty::usize()));
                    let i = self.coerce(cx, i, &Ty::usize());
                    return TExpr::new(TK::Index(Box::new(cur), Box::new(i)), et, sp);
                }
                Ty::Adt(a, xs) if matches!(self.p.adts[*a as usize].lang.as_deref(), Some("Vec") | Some("Buf")) => {
                    let et = xs[0].clone();
                    let i = self.check_expr(cx, idx, Some(&Ty::usize()));
                    let i = self.coerce(cx, i, &Ty::usize());
                    return TExpr::new(TK::Index(Box::new(cur), Box::new(i)), et, sp);
                }
                Ty::Adt(..) => {
                    // user Index / IndexMut
                    let (tn, mn, m) = if want_mut { ("IndexMut", "index_mut", true) } else { ("Index", "index", false) };
                    let i = self.check_expr(cx, idx, None);
                    if let Some(tr) = self.p.try_lang_trait(tn) {
                        let ity = i.ty.clone();
                        if let Some((fid, isub)) = self.impl_method_with_arg(cx, tr, &t, mn, &ity) {
                            let f = self.p.fns[fid as usize].clone();
                            let ret = self.shallow(cx, &f.ret.subst(&isub));
                            let csp = cur.span;
                            self.check_mutable_place_if(cx, &cur, m, sp);
                            let recv = TExpr::new(TK::Borrow(m, Box::new(cur)), Ty::Ref(m, Box::new(t.clone())), csp);
                            let i = match f.params.get(1) {
                                Some(p) => {
                                    let pt = p.ty.subst(&isub);
                                    self.coerce(cx, i, &pt)
                                }
                                None => i,
                            };
                            let call = TExpr::new(TK::Call { f: fid, substs: isub, args: vec![recv, i] }, ret.clone(), sp);
                            let inner = match ret {
                                Ty::Ref(_, x) => *x,
                                other => other,
                            };
                            return TExpr::new(TK::Deref(Box::new(call)), inner, sp);
                        }
                    }
                    let tyn = self.tn(cx, &t);
                    self.err(cx, "E-TYPE", sp, format!("cannot index `{tyn}`{}", if want_mut { " mutably (no IndexMut impl)" } else { " (no Index impl)" }));
                    return TExpr::err(sp);
                }
                Ty::Error => {
                    self.check_expr(cx, idx, None);
                    return TExpr::err(sp);
                }
                _ => {
                    let tyn = self.tn(cx, &t);
                    self.err(cx, "E-TYPE", sp, format!("cannot index into a value of type `{tyn}`"));
                    return TExpr::err(sp);
                }
            }
        }
        TExpr::err(sp)
    }

    fn check_mutable_place_if(&mut self, cx: &mut FnCx, e: &TExpr, m: bool, sp: Span) {
        if m {
            self.check_mutable_place(cx, e, sp, "borrow as mutable");
        }
    }

    fn impl_method_with_arg(&mut self, cx: &mut FnCx, tr: TraitId, st: &Ty, name: &str, arg: &Ty) -> Option<(FnId, Vec<Ty>)> {
        let impls = self.p.impls_of_trait.get(&tr).cloned().unwrap_or_default();
        for iid in impls {
            let im = self.p.impls[iid as usize].clone();
            let Some(fid) = im.methods.get(name) else { continue };
            let snap = cx.inf.snapshot();
            let fresh: Vec<Ty> = im.generics.iter().map(|_| cx.inf.fresh()).collect();
            let mut ok = self.unify(cx, &im.self_ty.subst(&fresh), st);
            if ok {
                if let Some((_, targs)) = &im.trait_ {
                    if let Some(a0) = targs.first() {
                        ok = self.unify(cx, &a0.subst(&fresh), arg);
                    }
                }
            }
            if ok {
                return Some((*fid, fresh));
            }
            cx.inf.rollback(snap);
        }
        None
    }

    #[allow(clippy::too_many_arguments)]
    fn slice_range(&mut self, cx: &mut FnCx, base: TExpr, elem: Ty, lo: Option<&ast::Expr>, hi: Option<&ast::Expr>, incl: bool, sp: Span) -> TExpr {
        let lo = lo.map(|x| {
            let t = self.check_expr(cx, x, Some(&Ty::usize()));
            Box::new(self.coerce(cx, t, &Ty::usize()))
        });
        let hi = hi.map(|x| {
            let t = self.check_expr(cx, x, Some(&Ty::usize()));
            Box::new(self.coerce(cx, t, &Ty::usize()))
        });
        TExpr::new(TK::SliceRange { base: Box::new(base), lo, hi, inclusive: incl }, Ty::Slice(Box::new(elem)), sp)
    }

    // ------------------------------------------------------------------ structs, match, for, try
    fn check_struct_lit(&mut self, cx: &mut FnCx, path: &ast::Path, fields: &[(ast::Ident, ast::Expr)], base: Option<&ast::Expr>, sp: Span) -> TExpr {
        let segs: Vec<String> = path.segs.iter().map(|s| s.ident.name.clone()).collect();
        let target = if segs.len() == 1 && segs[0] == "Self" {
            match &cx.self_ty {
                Some(Ty::Adt(a, xs)) => Some((*a, 0u32, Some(xs.clone()))),
                _ => None,
            }
        } else {
            match self.p.resolve(&cx.module, &segs) {
                Some(Def::Adt(a)) => Some((a, 0, None)),
                Some(Def::Variant(a, v)) => Some((a, v, None)),
                _ => self.resolve_variant_path(cx, &segs).map(|(a, v)| (a, v, None)),
            }
        };
        let Some((adt, v, fixed)) = target else {
            self.err(cx, "E-UNRESOLVED", path.span, format!("cannot find struct `{}`", path.text()));
            for (_, e) in fields {
                self.check_expr(cx, e, None);
            }
            return TExpr::err(sp);
        };
        let ad = self.p.adts[adt as usize].clone();
        if ad.partial || ad.kind == AdtKind::Opaque || matches!(ad.kind, AdtKind::Builtin(_)) {
            self.err(cx, "E-TYPE", sp, format!("`{}` cannot be constructed here (opaque or partially declared)", ad.name));
            return TExpr::err(sp);
        }
        let (t, substs) = match fixed {
            Some(xs) => (Ty::Adt(adt, xs.clone()), xs),
            None => self.adt_fresh_substs(cx, adt),
        };
        let vd = ad.variants[v as usize].clone();
        let mut vals: Vec<Option<TExpr>> = vec![None; vd.fields.len()];
        for (fname, fe) in fields {
            match vd.fields.iter().position(|f| f.name == fname.name) {
                Some(fi) => {
                    let ft = vd.fields[fi].ty.subst(&substs);
                    let te = self.check_expr(cx, fe, Some(&ft));
                    let te = self.coerce(cx, te, &ft);
                    if vals[fi].is_some() {
                        self.err(cx, "E-TYPE", fname.span, format!("field `{}` specified twice", fname.name));
                    }
                    vals[fi] = Some(te);
                }
                None => {
                    self.err(cx, "E-TYPE", fname.span, format!("no field `{}` in `{}`", fname.name, ad.name));
                    self.check_expr(cx, fe, None);
                }
            }
        }
        if let Some(b) = base {
            let bt = self.check_expr(cx, b, Some(&t));
            let bt = self.coerce(cx, bt, &t);
            let fs: Vec<(u32, TExpr)> = vals.into_iter().enumerate().filter_map(|(i, x)| x.map(|e| (i as u32, e))).collect();
            return TExpr::new(TK::CtorUpdate { adt, variant: v, fields: fs, base: Box::new(bt) }, t, sp);
        }
        let mut out = vec![];
        for (i, x) in vals.into_iter().enumerate() {
            match x {
                Some(e) => out.push(e),
                None => {
                    self.err(cx, "E-TYPE", sp, format!("missing field `{}` in initializer of `{}`", vd.fields[i].name, ad.name));
                    out.push(TExpr::err(sp));
                }
            }
        }
        TExpr::new(TK::Ctor { adt, variant: v, fields: out }, t, sp)
    }

    fn check_match(&mut self, cx: &mut FnCx, scrut: &ast::Expr, arms: &[ast::MatchArm], expected: Option<&Ty>, sp: Span) -> TExpr {
        let s = self.check_expr(cx, scrut, None);
        let st = s.ty.clone();
        let mut tarms = vec![];
        let mut result: Option<Ty> = expected.cloned();
        for a in arms {
            cx.scopes.push(vec![]);
            let p = self.check_pat(cx, &a.pat, &st, None);
            let g = a.guard.as_ref().map(|g| {
                let t = self.check_expr(cx, g, Some(&Ty::Bool));
                self.coerce(cx, t, &Ty::Bool)
            });
            let b = self.check_expr(cx, &a.body, result.as_ref());
            let bt = self.shallow(cx, &b.ty);
            let b = if matches!(bt, Ty::Never) {
                b
            } else {
                match &result {
                    Some(r) => {
                        let r = r.clone();
                        self.coerce(cx, b, &r)
                    }
                    None => {
                        result = Some(b.ty.clone());
                        b
                    }
                }
            };
            cx.scopes.pop();
            tarms.push(TArm { pat: p, guard: g, body: b });
        }
        // exhaustiveness (enums and bools; wildcard or binding covers all)
        self.check_exhaustive(cx, &st, &tarms, sp);
        let ty = result.unwrap_or(Ty::Never);
        TExpr::new(TK::Match(Box::new(s), tarms), ty, sp)
    }

    fn check_exhaustive(&mut self, cx: &mut FnCx, st: &Ty, arms: &[TArm], sp: Span) {
        fn covers_all(p: &TPat) -> bool {
            match &p.kind {
                PK::Wild => true,
                PK::Bind { sub: None, .. } => true,
                PK::Bind { sub: Some(s), .. } => covers_all(s),
                PK::Deref(i) => covers_all(i),
                PK::Or(ps) => ps.iter().any(covers_all),
                PK::Tuple(ps) => ps.iter().all(covers_all),
                _ => false,
            }
        }
        fn variants_covered(p: &TPat, out: &mut Vec<u32>) {
            match &p.kind {
                PK::Variant { variant, fields, .. } => {
                    if fields.iter().all(|(_, f)| covers_all(f) || matches!(f.kind, PK::Variant { .. } | PK::Lit(_)) && false) {
                        out.push(*variant);
                    }
                }
                PK::Deref(i) => variants_covered(i, out),
                PK::Or(ps) => ps.iter().for_each(|x| variants_covered(x, out)),
                PK::Bind { sub: Some(s), .. } => variants_covered(s, out),
                _ => {}
            }
        }
        let unguarded: Vec<&TArm> = arms.iter().filter(|a| a.guard.is_none()).collect();
        if unguarded.iter().any(|a| covers_all(&a.pat)) {
            return;
        }
        let t = cx.inf.zonk(st);
        let t = t.strip_refs().clone();
        match &t {
            Ty::Adt(a, _) if self.p.adts[*a as usize].kind == AdtKind::Enum => {
                let mut cov = vec![];
                for a2 in &unguarded {
                    variants_covered(&a2.pat, &mut cov);
                }
                let n = self.p.adts[*a as usize].variants.len() as u32;
                if (0..n).all(|v| cov.contains(&v)) {
                    return;
                }
                // nested enum patterns (Some(Ok(x)) ...) are accepted without a full check
                if unguarded.iter().any(|a| has_nested_variant(&a.pat)) {
                    return;
                }
                let missing: Vec<String> = (0..n).filter(|v| !cov.contains(v)).map(|v| self.p.adts[*a as usize].variants[v as usize].name.clone()).collect();
                self.err(cx, "E-TYPE", sp, format!("non-exhaustive patterns: {} not covered", missing.join(", ")));
            }
            Ty::Bool => {
                let mut t_ = false;
                let mut f_ = false;
                for a in &unguarded {
                    lit_bools(&a.pat, &mut t_, &mut f_);
                }
                if !(t_ && f_) {
                    self.err(cx, "E-TYPE", sp, "non-exhaustive patterns over `bool`");
                }
            }
            Ty::Error => {}
            Ty::Tuple(_) => {}
            _ => {
                self.err(cx, "E-TYPE", sp, "non-exhaustive patterns: add a `_` arm");
            }
        }
    }

    #[allow(clippy::too_many_arguments)]
    fn check_for(&mut self, cx: &mut FnCx, label: Option<String>, par: bool, pat: &ast::Pat, iter: &ast::Expr, body: &ast::Block, sp: Span) -> TExpr {
        let it = self.check_expr(cx, iter, None);
        let range = match (&iter.kind, &it.kind) {
            (ExprKind::Range(Some(_), Some(_), incl), TK::Ctor { fields, .. }) if fields.len() == 2 => Some((Box::new(fields[0].clone()), Box::new(fields[1].clone()), *incl)),
            (ExprKind::Paren(inner), TK::Ctor { fields, .. }) if matches!(inner.kind, ExprKind::Range(Some(_), Some(_), _)) && fields.len() == 2 => {
                let incl = matches!(inner.kind, ExprKind::Range(_, _, true));
                Some((Box::new(fields[0].clone()), Box::new(fields[1].clone()), incl))
            }
            _ => None,
        };
        // IntoIterator: &[T] / &Vec<T> / &[T; N] -> slice iter; Vec<T> -> into_iter
        let (iter_te, item) = self.into_iter(cx, it, sp);
        let id = self.new_loop(cx, label, false, sp);
        cx.scopes.push(vec![]);
        let tp = self.check_pat(cx, pat, &item, None);
        let bt = self.check_block(cx, body, Some(&Ty::Unit));
        cx.scopes.pop();
        cx.loops.pop();
        TExpr::new(TK::For { id, par, pat: tp, iter: Box::new(iter_te), body: Box::new(bt), range }, Ty::Unit, sp)
    }

    fn into_iter(&mut self, cx: &mut FnCx, it: TExpr, sp: Span) -> (TExpr, Ty) {
        let t = self.shallow(cx, &it.ty);
        let iter_tr = self.p.lang_trait("Iterator");
        let slice_like = |s: &Self, cx: &mut FnCx, t: &Ty| -> Option<Ty> {
            match t {
                Ty::Array(e, _) | Ty::Slice(e) => Some((**e).clone()),
                Ty::Adt(a, xs) if matches!(s.p.adts[*a as usize].lang.as_deref(), Some("Vec") | Some("Buf")) => Some(xs[0].clone()),
                _ => {
                    let _ = cx;
                    None
                }
            }
        };
        if let Ty::Ref(m, inner) = &t {
            let inner_t = self.shallow(cx, inner);
            if let Some(e) = slice_like(self, cx, &inner_t) {
                let name = if *m { "iter_mut" } else { "iter" };
                let slice_ty = Ty::Ref(*m, Box::new(Ty::Slice(Box::new(e.clone()))));
                if let Some((fid, _)) = self.find_slice_method(name) {
                    let recv = self.coerce(cx, it, &slice_ty);
                    let item = Ty::Ref(*m, Box::new(e.clone()));
                    let ity = Ty::Adt(self.lang_adt("Iter"), vec![item.clone()]);
                    return (TExpr::new(TK::Call { f: fid, substs: vec![e], args: vec![recv] }, ity, sp), item);
                }
            }
            // &mut I where I: Iterator
            if let Ty::Adt(..) = inner_t {
                let mut s = self.solver(cx);
                if s.implements(&inner_t, iter_tr, &[]) {
                    let item = self.iter_item(cx, &inner_t);
                    return (it, item);
                }
            }
        }
        if let Ty::Adt(a, xs) = &t {
            if self.p.adts[*a as usize].lang.as_deref() == Some("Vec") {
                let e = xs[0].clone();
                if let Some(fid) = self.find_method_by_builtin("vec_into_iter") {
                    let ity = Ty::Adt(self.lang_adt("Iter"), vec![e.clone()]);
                    return (TExpr::new(TK::Call { f: fid, substs: vec![e.clone()], args: vec![it] }, ity, sp), e);
                }
            }
        }
        if let Ty::Array(..) = &t {
            self.err(cx, "E-TYPE", sp, "iterate an array by reference (`for x in &arr`) in mithi v0");
            return (TExpr::err(sp), Ty::Error);
        }
        if matches!(t, Ty::Error) {
            return (it, Ty::Error);
        }
        let implemented = {
            let mut s = self.solver(cx);
            s.implements(&t, iter_tr, &[])
        };
        if implemented {
            let item = self.iter_item(cx, &t);
            return (it, item);
        }
        let tn = self.tn(cx, &t);
        self.err(cx, "E-TYPE", sp, format!("`{tn}` is not an iterator"));
        (TExpr::err(sp), Ty::Error)
    }

    fn find_slice_method(&self, name: &str) -> Option<(FnId, ())> {
        for im in &self.p.impls {
            if im.trait_.is_none() && matches!(im.self_ty, Ty::Slice(_)) {
                if let Some(f) = im.methods.get(name) {
                    return Some((*f, ()));
                }
            }
        }
        None
    }
    fn find_method_by_builtin(&self, b: &str) -> Option<FnId> {
        self.p.fns.iter().position(|f| f.builtin.as_deref() == Some(b)).map(|i| i as FnId)
    }

    fn check_try(&mut self, cx: &mut FnCx, inner: &ast::Expr, sp: Span) -> TExpr {
        let e = self.check_expr(cx, inner, None);
        let t = self.shallow(cx, &e.ty);
        let ret = cx.ret_stack.last().cloned().unwrap_or(Ty::Unit);
        let ret = self.shallow(cx, &ret);
        let res = self.lang_adt("Result");
        let opt = self.lang_adt("Option");
        match &t {
            Ty::Adt(a, xs) if *a == res => {
                let ok_t = xs[0].clone();
                let err_t = xs[1].clone();
                let (fn_err, fresh_ret) = match &ret {
                    Ty::Adt(b, ys) if *b == res => (ys[1].clone(), None),
                    Ty::Infer(_) => {
                        let fe = cx.inf.fresh();
                        let rt = Ty::Adt(res, vec![cx.inf.fresh(), fe.clone()]);
                        (fe, Some(rt))
                    }
                    _ => {
                        let tn = self.tn(cx, &ret);
                        self.err(cx, "E-TYPE", sp, format!("`?` on a Result in a function returning `{tn}`"));
                        return TExpr::err(sp);
                    }
                };
                if let Some(rt) = fresh_ret {
                    self.unify(cx, &ret, &rt);
                }
                // From conversion: identity or a From impl
                let snap = cx.inf.snapshot();
                let from = if self.unify(cx, &err_t, &fn_err) {
                    None
                } else {
                    cx.inf.rollback(snap);
                    let from_tr = self.p.lang_trait("From");
                    let fe = self.shallow(cx, &fn_err);
                    match self.impl_method_with_arg(cx, from_tr, &fe, "from", &err_t) {
                        Some((fid, s)) => Some((fid, s)),
                        None => {
                            let a = self.tn(cx, &err_t);
                            let b = self.tn(cx, &fn_err);
                            self.err(cx, "E-TYPE", sp, format!("`?` cannot convert the error `{a}` into `{b}` (no From impl)"));
                            None
                        }
                    }
                };
                TExpr::new(TK::Try { e: Box::new(e), is_option: false, from }, ok_t, sp)
            }
            Ty::Adt(a, xs) if *a == opt => {
                let ok_t = xs[0].clone();
                match &ret {
                    Ty::Adt(b, _) if *b == opt => {}
                    Ty::Infer(_) => {
                        let v = cx.inf.fresh();
                        let rt = Ty::Adt(opt, vec![v]);
                        self.unify(cx, &ret, &rt);
                    }
                    _ => {
                        let tn = self.tn(cx, &ret);
                        self.err(cx, "E-TYPE", sp, format!("`?` on an Option in a function returning `{tn}`"));
                    }
                }
                TExpr::new(TK::Try { e: Box::new(e), is_option: true, from: None }, ok_t, sp)
            }
            Ty::Error => TExpr::err(sp),
            _ => {
                let tn = self.tn(cx, &t);
                self.err(cx, "E-TYPE", sp, format!("`?` cannot be applied to `{tn}`"));
                TExpr::err(sp)
            }
        }
    }

    // ------------------------------------------------------------------ closures
    #[allow(clippy::too_many_arguments)]
    fn check_closure(&mut self, cx: &mut FnCx, is_move: bool, params: &[ast::ClosureParam], ret: Option<&ast::TypeAst>, body: &ast::Expr, expected: Option<&Ty>, sp: Span) -> TExpr {
        // expected signature from an Fn bound (instantiated generics) or a fn pointer
        let exp_sig: Option<(Vec<Ty>, Ty)> = expected.and_then(|t| match cx.inf.shallow(t) {
            Ty::Infer(v) => cx.inf.fn_bounds.get(&v).map(|(_, ps, r)| (ps.clone(), r.clone())),
            Ty::FnPtr(ps, r) => Some((ps, *r)),
            Ty::Param(i) => cx.generics.get(i as usize).and_then(crate::lower::fn_bound).map(|(_, ps, r)| (ps, r)),
            _ => None,
        });
        let cid = self.closures.len() as ClosureId;
        // reserve the global slot
        self.closures.push(ClosureDef { owner: cx.fid, params: vec![], param_tys: vec![], ret: Ty::Error, body: TExpr::err(sp), captures: vec![], is_move, span: sp, fn_kind: 0 });
        self.closure_parent.push(cx.closure_stack.last().copied());
        cx.closure_stack.push(cid);
        cx.scopes.push(vec![]);
        let mut ptys = vec![];
        let mut tpats = vec![];
        for (i, p) in params.iter().enumerate() {
            let t = match &p.ty {
                Some(t) => self.lower_body_ty(cx, t),
                None => match &exp_sig {
                    Some((ps, _)) if i < ps.len() => {
                        let z = cx.inf.zonk(&ps[i]);
                        let mut s = self.solver(cx);
                        deep_normalize(&mut s, &z)
                    }
                    _ => cx.inf.fresh(),
                },
            };
            if let (Some(_), Some((ps, _))) = (&p.ty, &exp_sig) {
                if let Some(et) = ps.get(i) {
                    let et = et.clone();
                    self.unify(cx, &t, &et);
                }
            }
            let tp = self.check_pat(cx, &p.pat, &t, None);
            ptys.push(t);
            tpats.push(tp);
        }
        if let Some((ps, _)) = &exp_sig {
            if ps.len() != params.len() {
                self.err(cx, "E-TYPE", sp, format!("this closure takes {} argument(s) but {} are expected", params.len(), ps.len()));
            }
        }
        let rty = match ret {
            Some(t) => self.lower_body_ty(cx, t),
            None => match &exp_sig {
                Some((_, r)) => r.clone(),
                None => cx.inf.fresh(),
            },
        };
        cx.closure_sigs.insert(cid, (ptys.clone(), rty.clone(), 0));
        cx.ret_stack.push(rty.clone());
        let bt = self.check_expr(cx, body, Some(&rty));
        let bt = self.coerce(cx, bt, &rty);
        cx.ret_stack.pop();
        cx.scopes.pop();
        cx.closure_stack.pop();
        let def = ClosureDef { owner: cx.fid, params: tpats, param_tys: ptys, ret: rty, body: bt, captures: vec![], is_move, span: sp, fn_kind: 0 };
        cx.new_closures.push((cid, def));
        let ct = Ty::Closure(cid);
        if let Some(t) = expected {
            let t = t.clone();
            let snap = cx.inf.snapshot();
            if !self.unify(cx, &ct, &t) {
                cx.inf.rollback(snap);
            }
        }
        TExpr::new(TK::Closure(cid), ct, sp)
    }

    // ------------------------------------------------------------------ macros
    fn check_macro(&mut self, cx: &mut FnCx, name: &str, args: &ast::MacroArgs, expected: Option<&Ty>, sp: Span) -> TExpr {
        let exprs: Vec<ast::Expr> = match args {
            ast::MacroArgs::Exprs(v) => v.clone(),
            _ => vec![],
        };
        let first_str = |v: &[ast::Expr]| -> Option<String> {
            match v.first().map(|e| &e.kind) {
                Some(ExprKind::Lit(Lit::Str(s))) => Some(s.clone()),
                _ => None,
            }
        };
        match name {
            "todo" | "unimplemented" => {
                let n = first_str(&exprs).unwrap_or_default();
                for a in exprs.iter().skip(1) {
                    self.check_expr(cx, a, None);
                }
                let kind = if name == "todo" { TrapKind::Hole(n.clone()) } else { TrapKind::Panic };
                TExpr::new(TK::Trap(kind, Some(n)), Ty::Never, sp)
            }
            "unreachable" | "panic" => {
                let msg = first_str(&exprs);
                for a in exprs.iter().skip(1) {
                    self.check_expr(cx, a, None);
                }
                let kind = if name == "panic" { TrapKind::Panic } else { TrapKind::Unreachable };
                TExpr::new(TK::Trap(kind, msg), Ty::Never, sp)
            }
            "assert" | "debug_assert" => {
                if exprs.is_empty() {
                    self.err(cx, "E-TYPE", sp, "assert! needs a condition");
                    return TExpr::err(sp);
                }
                let c = self.check_expr(cx, &exprs[0], Some(&Ty::Bool));
                let c = self.coerce(cx, c, &Ty::Bool);
                let msg = exprs.get(1).and_then(|e| if let ExprKind::Lit(Lit::Str(s)) = &e.kind { Some(s.clone()) } else { None });
                for a in exprs.iter().skip(2) {
                    self.check_expr(cx, a, None);
                }
                TExpr::new(TK::Assert { cond: Box::new(c), msg }, Ty::Unit, sp)
            }
            "assert_eq" | "assert_ne" | "debug_assert_eq" | "debug_assert_ne" => {
                if exprs.len() < 2 {
                    self.err(cx, "E-TYPE", sp, format!("{name}! needs two operands"));
                    return TExpr::err(sp);
                }
                let a = self.check_expr(cx, &exprs[0], None);
                let at = a.ty.clone();
                let b = self.check_expr(cx, &exprs[1], Some(&at));
                // string operands of different string types compare as `&str` (as `==` does)
                let views = match (self.str_view(cx, a.clone()), self.str_view(cx, b.clone())) {
                    (Some(x), Some(y)) if !self.unify(cx, &a.ty, &b.ty) => Some((x, y)),
                    _ => None,
                };
                let (a, b) = match views {
                    Some(v) => v,
                    None => {
                        let b = self.coerce(cx, b, &at);
                        (a, b)
                    }
                };
                for x in exprs.iter().skip(2) {
                    self.check_expr(cx, x, None);
                }
                TExpr::new(TK::AssertCmp { eq: name.ends_with("eq"), a: Box::new(a), b: Box::new(b) }, Ty::Unit, sp)
            }
            "vec" => {
                let vec = self.lang_adt("Vec");
                let et = match expected.map(|t| self.shallow(cx, t)) {
                    Some(Ty::Adt(a, xs)) if a == vec => xs[0].clone(),
                    _ => cx.inf.fresh(),
                };
                match args {
                    ast::MacroArgs::Repeat(x, n) => {
                        let te = self.check_expr(cx, x, Some(&et));
                        let te = self.coerce(cx, te, &et);
                        let nt = self.check_expr(cx, n, Some(&Ty::usize()));
                        let nt = self.coerce(cx, nt, &Ty::usize());
                        let fid = self.find_method_by_builtin("vec_repeat").expect("std vec_repeat");
                        TExpr::new(TK::Call { f: fid, substs: vec![et.clone()], args: vec![te, nt] }, Ty::Adt(vec, vec![et]), sp)
                    }
                    _ => {
                        let mut out = vec![];
                        for x in &exprs {
                            let te = self.check_expr(cx, x, Some(&et));
                            out.push(self.coerce(cx, te, &et));
                        }
                        let n = out.len() as i128;
                        let arr = TExpr::new(TK::Array(out), Ty::Array(Box::new(et.clone()), Box::new(Ty::Const(n))), sp);
                        let fid = self.find_method_by_builtin("vec_from_array").expect("std vec_from_array");
                        TExpr::new(TK::Call { f: fid, substs: vec![et.clone(), Ty::Const(n)], args: vec![arr] }, Ty::Adt(vec, vec![et]), sp)
                    }
                }
            }
            "format" | "println" | "print" | "eprintln" | "eprint" | "dbg" | "write" | "writeln" => {
                let mut rest = exprs.clone();
                let mut dest = None;
                if name == "write" || name == "writeln" {
                    if rest.is_empty() {
                        self.err(cx, "E-TYPE", sp, "write! needs a destination");
                        return TExpr::err(sp);
                    }
                    dest = Some(rest.remove(0));
                }
                let mut specs: Vec<crate::fmtspec::Spec> = vec![];
                let (pieces, nargs) = match rest.first().map(|e| &e.kind) {
                    Some(ExprKind::Lit(Lit::Str(s))) => match parse_format_specs(s) {
                        Ok((p, sp_list)) => {
                            if sp_list.iter().any(|x| x.ty == "p") {
                                self.err(cx, "E-FF-ADDR", sp, "`{:p}` prints an address, which safe code cannot observe (01 section 6.1, C-FMT-ADDR)");
                            }
                            let n = crate::fmtspec::args_used(&sp_list).last().map(|m| m + 1).unwrap_or(0);
                            specs = sp_list;
                            (p, n)
                        }
                        Err(m) => {
                            self.err(cx, "E-TYPE", sp, m);
                            (vec![], usize::MAX)
                        }
                    },
                    _ if name == "dbg" => (vec![], rest.len()),
                    _ => (vec!["".into()], 0),
                };
                let mut targs = vec![];
                let skip = if name == "dbg" { 0 } else { 1 };
                for a in rest.iter().skip(skip) {
                    targs.push(self.check_expr(cx, a, None));
                }
                if nargs == usize::MAX {
                    // the format string itself was rejected above
                } else if name != "dbg" && targs.len() != nargs {
                    self.err(cx, "E-TYPE", sp, format!("format string expects {nargs} argument(s), {} given", targs.len()));
                } else if name != "dbg" {
                    let used = crate::fmtspec::args_used(&specs);
                    if let Some(k) = (0..targs.len()).find(|k| !used.contains(k)) {
                        self.err(cx, "E-TYPE", sp, format!("format argument {k} is never used"));
                    }
                    for spc in &specs {
                        for c in [spc.width, spc.precision].into_iter().flatten() {
                            if let crate::fmtspec::Count::Arg(k) = c {
                                if let Some(a) = targs.get(k) {
                                    let t = self.shallow(cx, &a.ty);
                                    if !matches!(t, Ty::Int(IntTy::Usize) | Ty::IntVar(_) | Ty::Error | Ty::Infer(_)) {
                                        self.err(cx, "E-TYPE", sp, format!("a width or precision argument must be `usize`, found `{}`", self.tn(cx, &t)));
                                    }
                                }
                            }
                        }
                        if let Some(a) = targs.get(spc.arg) {
                            let t = self.shallow(cx, &a.ty);
                            if let Some(why) = self.fmt_trait_missing(cx, &t, &spc.ty) {
                                self.err(cx, "E-TYPE", sp, why);
                            }
                        }
                    }
                }
                if matches!(name, "println" | "print" | "eprintln" | "eprint" | "dbg") {
                    self.err(cx, "E-AMBIENT-IO", sp, format!("`{name}!` performs ambient I/O (C-IO); pass a log capability or remove it"));
                }
                if name == "dbg" {
                    // `dbg!(e)` returns e (Rust); it never runs, being E-AMBIENT-IO
                    return match targs.len() {
                        0 => TExpr::new(TK::Block(vec![], None), Ty::Unit, sp),
                        1 => {
                            let a = targs.remove(0);
                            let t = a.ty.clone();
                            TExpr::new(TK::Block(vec![], Some(Box::new(a))), t, sp)
                        }
                        _ => {
                            let t = Ty::Tuple(targs.iter().map(|a| a.ty.clone()).collect());
                            TExpr::new(TK::Tuple(targs), t, sp)
                        }
                    };
                }
                let string = Ty::Adt(self.lang_adt("String"), vec![]);
                let fmt = TExpr::new(TK::Format { pieces, args: targs }, string.clone(), sp);
                match name {
                    "format" => fmt,
                    "write" | "writeln" => {
                        let d = self.check_expr(cx, dest.as_ref().unwrap(), None);
                        let res = Ty::Adt(self.lang_adt("Result"), vec![Ty::Unit, Ty::Unit]);
                        let fid = self.find_method_by_builtin("string_write_fmt").expect("std string_write_fmt");
                        TExpr::new(TK::Call { f: fid, substs: vec![], args: vec![d, fmt] }, res, sp)
                    }
                    _ => TExpr::new(TK::Block(vec![TStmt::Expr(fmt)], None), Ty::Unit, sp),
                }
            }
            "matches" => {
                if let ast::MacroArgs::Matches(e, p) = args {
                    let s = self.check_expr(cx, e, None);
                    cx.scopes.push(vec![]);
                    let st = s.ty.clone();
                    let tp = self.check_pat(cx, p, &st, None);
                    cx.scopes.pop();
                    return TExpr::new(TK::Matches(Box::new(s), Box::new(tp)), Ty::Bool, sp);
                }
                TExpr::err(sp)
            }
            "include" | "include_bytes" | "include_str" | "env" | "option_env" => {
                let kw = if name.ends_with("env") { "ENV" } else { "INCLUDE" };
                self.err(cx, &format!("E-X1-NOTYET-{kw}"), sp, format!("`{name}!` is not in the X1 subset (X1 design 9.1)"));
                TExpr::err(sp)
            }
            _ => {
                self.err(cx, "E-MACRO", sp, format!("`{name}!`: user macros are rejected (DR-005); the built-in forms are a closed list (C-MACROS)"));
                let _ = expected;
                TExpr::err(sp)
            }
        }
    }
}

#[derive(Clone)]
struct Probe {
    recv: TExpr,
    fid: FnId,
    parent: Vec<Ty>,
    trait_dispatch: Option<(TraitId, Ty)>,
}

enum Value {
    Local(LocalId),
    Fn(FnId, Option<Vec<Ty>>),
    Const(u32),
    Variant(AdtId, u32),
    UnitStruct(AdtId),
    TraitMethod(TraitId, FnId, Ty),
    AssocConst(Ty, LitVal),
}

fn has_nested_variant(p: &TPat) -> bool {
    match &p.kind {
        PK::Variant { fields, .. } => fields.iter().any(|(_, f)| matches!(f.kind, PK::Variant { .. } | PK::Lit(_) | PK::Range(..)) || has_nested_variant(f)),
        PK::Deref(i) => has_nested_variant(i),
        PK::Or(ps) => ps.iter().any(has_nested_variant),
        _ => false,
    }
}

fn lit_bools(p: &TPat, t: &mut bool, f: &mut bool) {
    match &p.kind {
        PK::Lit(LitVal::Bool(true)) => *t = true,
        PK::Lit(LitVal::Bool(false)) => *f = true,
        PK::Or(ps) => ps.iter().for_each(|x| lit_bools(x, t, f)),
        PK::Deref(i) => lit_bools(i, t, f),
        _ => {}
    }
}

fn item_span(it: &ast::Item) -> Span {
    match it {
        ast::Item::Fn(f) => f.span,
        ast::Item::Struct(s) => s.span,
        ast::Item::Enum(e) => e.span,
        ast::Item::Impl(i) => i.span,
        ast::Item::Trait(t) => t.span,
        _ => Span::DUMMY,
    }
}

pub fn zonk_pat(inf: &Infer, mut p: TPat) -> TPat {
    p.ty = inf.zonk(&p.ty);
    p.kind = match p.kind {
        PK::Bind { local, by_ref, sub } => PK::Bind { local, by_ref, sub: sub.map(|s| Box::new(zonk_pat(inf, *s))) },
        PK::Tuple(ps) => PK::Tuple(ps.into_iter().map(|x| zonk_pat(inf, x)).collect()),
        PK::Variant { adt, variant, fields } => PK::Variant { adt, variant, fields: fields.into_iter().map(|(i, x)| (i, zonk_pat(inf, x))).collect() },
        PK::Deref(i) => PK::Deref(Box::new(zonk_pat(inf, *i))),
        PK::Or(ps) => PK::Or(ps.into_iter().map(|x| zonk_pat(inf, x)).collect()),
        PK::Slice(ps, r) => PK::Slice(ps.into_iter().map(|x| zonk_pat(inf, x)).collect(), r),
        other => other,
    };
    p
}

pub fn deep_normalize(s: &mut Solver, t: &Ty) -> Ty {
    let t = s.normalize(&s.inf.shallow(t));
    match t {
        Ty::Tuple(v) => Ty::Tuple(v.iter().map(|x| deep_normalize(s, x)).collect()),
        Ty::Array(a, n) => Ty::Array(Box::new(deep_normalize(s, &a)), n),
        Ty::Slice(a) => Ty::Slice(Box::new(deep_normalize(s, &a))),
        Ty::Ref(m, a) => Ty::Ref(m, Box::new(deep_normalize(s, &a))),
        Ty::Adt(a, v) => Ty::Adt(a, v.iter().map(|x| deep_normalize(s, x)).collect()),
        other => other,
    }
}

fn is_dc_value_path(n: &str) -> bool {
    let segs: Vec<&str> = n.split("::").collect();
    segs.iter().any(|s| matches!(*s, "Cell" | "RefCell" | "Rc" | "Weak" | "UnsafeCell" | "OnceCell"))
}

pub fn is_whole_task_canon(n: &str) -> bool {
    matches!(n, "canon::act_q8" | "canon::matvec_q" | "canon::rmsnorm" | "canon::softmax" | "canon::silu" | "canon::sigmoid" | "canon::rope" | "canon::combine_rank")
}

/// Parse a Rust format string into literal pieces and count the `{}` arguments; reports `{:p}`.
pub fn parse_format_string(s: &str) -> Result<(Vec<String>, usize, bool), String> {
    let (pieces, specs) = parse_format_specs(s)?;
    let addr = specs.iter().any(|x| x.ty == "p");
    Ok((pieces, crate::fmtspec::args_used(&specs).last().map(|m| m + 1).unwrap_or(0), addr))
}

/// Pieces (literal text, and `\0` + the placeholder's text) and the parsed placeholders.
pub fn parse_format_specs(s: &str) -> Result<(Vec<String>, Vec<crate::fmtspec::Spec>), String> {
    let mut pieces = vec![String::new()];
    let mut specs = vec![];
    let mut implicit = 0usize;
    let cs: Vec<char> = s.chars().collect();
    let mut i = 0;
    while i < cs.len() {
        let c = cs[i];
        if c == '{' {
            if i + 1 < cs.len() && cs[i + 1] == '{' {
                pieces.last_mut().unwrap().push('{');
                i += 2;
                continue;
            }
            let mut j = i + 1;
            let mut spec = String::new();
            while j < cs.len() && cs[j] != '}' {
                spec.push(cs[j]);
                j += 1;
            }
            if j >= cs.len() {
                return Err("unterminated `{` in format string".into());
            }
            specs.push(crate::fmtspec::parse_placeholder(&spec, &mut implicit)?);
            pieces.push(format!("\u{0}{spec}"));
            pieces.push(String::new());
            i = j + 1;
            continue;
        }
        if c == '}' {
            if i + 1 < cs.len() && cs[i + 1] == '}' {
                pieces.last_mut().unwrap().push('}');
                i += 2;
                continue;
            }
            return Err("unmatched `}` in format string".into());
        }
        pieces.last_mut().unwrap().push(c);
        i += 1;
    }
    Ok((pieces, specs))
}

/// Lowering of body types without mutating the program (diagnostics are collected).
struct ScratchLower<'a> {
    p: &'a Program,
    diags: Vec<Diag>,
}

impl<'a> ScratchLower<'a> {
    fn lower(&mut self, t: &ast::TypeAst, cx: &TyCx, module: &str) -> Ty {
        use ast::TypeKind as K;
        match &t.kind {
            K::Ref { mutable, lifetime, inner } => {
                if let Some(l) = lifetime {
                    self.diags.push(Diag::new("E-LIFETIME", t.span, format!("lifetime `'{l}` (FF-REF)")));
                }
                Ty::Ref(*mutable, Box::new(self.lower(inner, cx, module)))
            }
            K::Slice(i) => Ty::Slice(Box::new(self.lower(i, cx, module))),
            K::Array(i, n) => {
                let et = self.lower(i, cx, module);
                let nt = match &n.kind {
                    ExprKind::Lit(Lit::Int(v, _)) => Ty::Const(*v as i128),
                    ExprKind::Path(p) => {
                        let segs: Vec<String> = p.segs.iter().map(|s| s.ident.name.clone()).collect();
                        match self.p.resolve(module, &segs) {
                            Some(Def::Const(c)) => self.p.const_int_value(c).map(Ty::Const).unwrap_or(Ty::Error),
                            _ => match cx.params.iter().position(|g| Some(g.as_str()) == p.single()) {
                                Some(i) => Ty::Param(i as u32),
                                None => Ty::Error,
                            },
                        }
                    }
                    _ => Ty::Error,
                };
                Ty::Array(Box::new(et), Box::new(nt))
            }
            K::Tuple(v) => {
                if v.is_empty() {
                    Ty::Unit
                } else {
                    Ty::Tuple(v.iter().map(|x| self.lower(x, cx, module)).collect())
                }
            }
            K::Never => Ty::Never,
            K::Infer => Ty::Error,
            K::DynTrait(_) => {
                self.diags.push(Diag::new("E-DYN", t.span, "`dyn Trait`: no dynamic dispatch (FF-DYN)"));
                Ty::Error
            }
            K::Path(p) => {
                let segs: Vec<String> = p.segs.iter().map(|s| s.ident.name.clone()).collect();
                if segs.len() == 1 {
                    if segs[0] == "Self" {
                        if let Some(s) = &cx.self_ty {
                            return s.clone();
                        }
                    }
                    if let Some(i) = cx.params.iter().position(|g| g == &segs[0]) {
                        return Ty::Param(i as u32);
                    }
                }
                let args: Vec<Ty> = match &p.segs.last().unwrap().generics {
                    Some(ga) => ga
                        .iter()
                        .filter_map(|g| match g {
                            ast::GenericArg::Type(x) => Some(self.lower(x, cx, module)),
                            ast::GenericArg::Const(e) => match &e.kind {
                                ExprKind::Lit(Lit::Int(v, _)) => Some(Ty::Const(*v as i128)),
                                _ => Some(Ty::Error),
                            },
                            _ => None,
                        })
                        .collect(),
                    None => vec![],
                };
                match self.p.resolve(module, &segs) {
                    Some(Def::Prim(n)) => crate::program::prim_ty(&n).unwrap_or(Ty::Error),
                    Some(Def::Adt(a)) => {
                        let want = self.p.adts[a as usize].generics.len();
                        let mut args = args;
                        while args.len() < want {
                            args.push(Ty::Error);
                        }
                        args.truncate(want);
                        Ty::Adt(a, args)
                    }
                    _ => {
                        let n = p.text();
                        if crate::program::is_dc_type(&n) {
                            self.diags.push(Diag::new("E-FF-CELL", t.span, format!("`{n}`: interior mutability and shared ownership are rejected (FF-CELL)")));
                        } else if OOS_PLATFORM_NAMES.contains(&segs.last().unwrap().as_str()) {
                            self.diags.push(Diag::new(&format!("E-OUT-OF-SCOPE-{}", segs.last().unwrap().to_uppercase()), t.span, format!("`{n}` is a std_platform name outside the X1 prelude")));
                        } else {
                            self.diags.push(Diag::new("E-UNRESOLVED", t.span, format!("cannot find type `{n}`")));
                        }
                        Ty::Error
                    }
                }
            }
            K::ImplTrait(_) => {
                self.diags.push(Diag::new("E-TYPE", t.span, "`impl Trait` is only allowed in function signatures"));
                Ty::Error
            }
            K::FnPtr(ps, r) => Ty::FnPtr(ps.iter().map(|x| self.lower(x, cx, module)).collect(), Box::new(r.as_ref().map(|x| self.lower(x, cx, module)).unwrap_or(Ty::Unit))),
            K::QPath(..) | K::RawPtr(..) => {
                self.diags.push(Diag::new("E-TYPE", t.span, "unsupported type form in a body"));
                Ty::Error
            }
        }
    }
}

/// Debug for a field type: primitives, references, slices, arrays, tuples, std types with Debug
/// arguments, and user types that derive it.
fn debug_ok(p: &Program, t: &Ty, depth: u32) -> bool {
    if depth > 8 {
        return true;
    }
    match t {
        Ty::Ref(_, x) | Ty::Slice(x) | Ty::Array(x, _) => debug_ok(p, x, depth + 1),
        Ty::Tuple(v) => v.iter().all(|x| debug_ok(p, x, depth + 1)),
        Ty::Adt(a, xs) => {
            let ad = &p.adts[*a as usize];
            let own = if ad.role == FileRole::Std { !matches!(ad.lang.as_deref(), Some("Mutex") | Some("Iter") | Some("BlobFile") | Some("Clock") | Some("SlabBuf") | Some("Frozen") | Some("Hint")) } else { ad.derives("Debug") };
            own && xs.iter().all(|x| debug_ok(p, x, depth + 1))
        }
        Ty::Closure(_) => false,
        _ => true,
    }
}
