//! Building a `Program` from source files: parse, apply the prelude override rule, declare names,
//! generate `format` code (⊢_fmt), lower signatures and fields.

use crate::ast::{self, Bound, FnKind, Item, TypeKind, VariantData};
use crate::diag::{Diag, FileRole, SourceMap, Span};
use crate::program::*;
use crate::types::*;
use std::collections::{BTreeMap, BTreeSet, HashSet};

#[derive(Clone)]
pub struct SourceInput {
    pub name: String,
    pub text: String,
    pub role: FileRole,
    /// module the file's items are placed in ("" = root)
    pub module: String,
}

pub const STD_SOURCE: &str = include_str!("../std/std.mith");
pub const CANONICAL_PRELUDE: &str = include_str!("../prelude/canonical.mith");

/// Paths defined by a list of items (used for the prelude override rule).
fn defined_paths(items: &[Item], module: &str, out: &mut HashSet<String>) {
    for it in items {
        match it {
            Item::Fn(f) => {
                out.insert(join_path(module, &f.name.name));
            }
            Item::Struct(s) => {
                out.insert(join_path(module, &s.name.name));
            }
            Item::Enum(e) => {
                out.insert(join_path(module, &e.name.name));
            }
            Item::Trait(t) => {
                out.insert(join_path(module, &t.name.name));
            }
            Item::Format(f) => {
                out.insert(join_path(module, &f.name.name));
            }
            Item::Const(c) => {
                out.insert(join_path(module, &c.name.name));
            }
            Item::Schedule(s) => {
                out.insert(join_path(module, &s.name.name));
            }
            Item::Spec(s) => {
                out.insert(join_path(module, &format!("spec {}", s.name.name)));
            }
            Item::Invariant(i) => {
                out.insert(join_path(module, &format!("invariant {}", i.ty.last())));
            }
            Item::Impl(im) => {
                if let Some(tn) = impl_self_name(&im.self_ty) {
                    for m in &im.members {
                        if let ast::ImplMember::Fn(f) = m {
                            let key = match &im.trait_ {
                                None => join_path(module, &format!("{tn}::{}", f.name.name)),
                                Some(t) => join_path(module, &format!("{tn} as {}::{}", t.last(), f.name.name)),
                            };
                            out.insert(key);
                        }
                    }
                }
            }
            Item::Mod(m) => defined_paths(&m.items, &join_path(module, &m.name.name), out),
            _ => {}
        }
    }
}

fn impl_self_name(t: &ast::TypeAst) -> Option<String> {
    match &t.kind {
        TypeKind::Path(p) => Some(p.last().to_string()),
        _ => None,
    }
}

/// Remove prelude items whose path a user file defines.
fn apply_override(items: Vec<Item>, module: &str, user: &HashSet<String>) -> Vec<Item> {
    let mut out = Vec::new();
    for it in items {
        let keep = match &it {
            Item::Fn(f) => !user.contains(&join_path(module, &f.name.name)),
            Item::Struct(s) => !user.contains(&join_path(module, &s.name.name)),
            Item::Enum(e) => !user.contains(&join_path(module, &e.name.name)),
            Item::Trait(t) => !user.contains(&join_path(module, &t.name.name)),
            Item::Format(f) => !user.contains(&join_path(module, &f.name.name)),
            Item::Const(c) => !user.contains(&join_path(module, &c.name.name)),
            Item::Schedule(s) => !user.contains(&join_path(module, &s.name.name)),
            Item::Spec(s) => !user.contains(&join_path(module, &format!("spec {}", s.name.name))),
            Item::Invariant(i) => !user.contains(&join_path(module, &format!("invariant {}", i.ty.last()))),
            _ => true,
        };
        if !keep {
            continue;
        }
        match it {
            Item::Impl(mut im) => {
                if let Some(tn) = impl_self_name(&im.self_ty) {
                    let tr = im.trait_.as_ref().map(|t| t.last().to_string());
                    im.members.retain(|m| match m {
                        ast::ImplMember::Fn(f) => {
                            let key = match &tr {
                                None => join_path(module, &format!("{tn}::{}", f.name.name)),
                                Some(t) => join_path(module, &format!("{tn} as {t}::{}", f.name.name)),
                            };
                            !user.contains(&key)
                        }
                        _ => true,
                    });
                    // a trait impl that lost a method entirely is dropped (the user re-implements it)
                    if tr.is_some() && im.members.iter().all(|m| !matches!(m, ast::ImplMember::Fn(_))) {
                        continue;
                    }
                }
                out.push(Item::Impl(im));
            }
            Item::Mod(mut m) => {
                let sub = join_path(module, &m.name.name);
                m.items = apply_override(m.items, &sub, user);
                out.push(Item::Mod(m));
            }
            other => out.push(other),
        }
    }
    out
}

pub struct Built {
    pub program: Program,
    /// (items, module, role) per file, after override, in load order
    pub files: Vec<(Vec<Item>, String, FileRole, u16)>,
}

/// Parse and declare every file. Returns the program with names declared and signatures lowered.
pub fn build(inputs: &[SourceInput]) -> Built {
    let mut sm = SourceMap::default();
    let mut parsed: Vec<(Vec<Item>, String, FileRole, u16)> = Vec::new();
    let mut parse_diags = Vec::new();
    let std_id = sm.add("<std>", STD_SOURCE, FileRole::Std);
    match crate::parser::parse_source(std_id, STD_SOURCE, true) {
        Ok(items) => parsed.push((items, String::new(), FileRole::Std, std_id)),
        Err(d) => parse_diags.push(d),
    }
    for inp in inputs {
        let id = sm.add(&inp.name, &inp.text, inp.role);
        match crate::parser::parse_source(id, &inp.text, inp.role != FileRole::User) {
            Ok(items) => parsed.push((items, inp.module.clone(), inp.role, id)),
            Err(d) => parse_diags.push(d),
        }
    }
    // override rule
    let mut user_paths = HashSet::new();
    for (items, module, role, _) in &parsed {
        if *role == FileRole::User {
            defined_paths(items, module, &mut user_paths);
        }
    }
    let parsed: Vec<_> = parsed
        .into_iter()
        .map(|(items, module, role, id)| {
            if role == FileRole::Prelude {
                (apply_override(items, &module, &user_paths), module, role, id)
            } else {
                (items, module, role, id)
            }
        })
        .collect();
    let mut prog = Program::new(sm);
    prog.diags.extend(parse_diags);
    // format code generation happens before declaration so that generated structs are declared
    let mut all = Vec::new();
    for (items, module, role, id) in parsed {
        let mut gen_files = Vec::new();
        gen_formats(&mut prog, &items, &module, role, &mut gen_files);
        all.push((items, module, role, id));
        all.extend(gen_files);
    }
    for (items, module, role, _) in &all {
        prog.collect_file(items, module, *role);
    }
    let mut lw = Lowerer { p: &mut prog };
    for (items, module, role, _) in &all {
        lw.lower_items_pass1(items, module, *role);
    }
    for (items, module, role, _) in &all {
        lw.lower_items_pass2(items, module, *role);
    }
    lw.lower_invariants();
    lw.finish_formats();
    lw.check_coherence();
    Built { program: prog, files: all }
}

// ---------------------------------------------------------------- formats (⊢_fmt, note §5.14)

fn code_size(code: &ast::FormatCode) -> Option<u64> {
    match code {
        ast::FormatCode::Named { name, args } => match name.name.as_str() {
            "f16" | "bf16" | "i16" | "u16" => Some(2),
            "f32" | "i32" | "u32" => Some(4),
            "i8" | "u8" => Some(1),
            "nibbles" => {
                let n = args.iter().find(|(k, _)| k.is_none()).and_then(|(_, e)| lit_u64(e))?;
                Some(n / 2)
            }
            _ => None,
        },
        ast::FormatCode::Array(inner, n) => Some(code_size(inner)? * lit_u64(n)?),
    }
}

fn lit_u64(e: &ast::Expr) -> Option<u64> {
    match &e.kind {
        ast::ExprKind::Lit(ast::Lit::Int(v, _)) => Some(*v as u64),
        _ => None,
    }
}

fn code_ty_text(code: &ast::FormatCode, prog: &mut Program, gen: &mut String, done: &mut BTreeSet<String>) -> Result<String, (String, Span)> {
    match code {
        ast::FormatCode::Named { name, args } => {
            let n = name.name.as_str();
            if !X1_FORMAT_CODES.contains(&n) {
                return Err((n.to_uppercase(), name.span));
            }
            if n == "nibbles" {
                let count = args.iter().find(|(k, _)| k.is_none()).and_then(|(_, e)| lit_u64(e));
                let off = args.iter().find(|(k, _)| k.as_ref().map(|k| k.name == "offset").unwrap_or(false)).and_then(|(_, e)| lit_u64(e)).unwrap_or(0);
                let count = match count {
                    Some(c) if c % 2 == 0 && c > 0 => c,
                    _ => {
                        prog.diags.push(Diag::new("E-TYPE", name.span, "nibbles<N, offset = K> needs an even element count N"));
                        return Ok("u8".into());
                    }
                };
                if off > 15 {
                    prog.diags.push(Diag::new("E-TYPE", name.span, "nibble offset must be in 0..=15"));
                }
                let tn = format!("Nib{count}o{off}");
                if done.insert(tn.clone()) {
                    let half = count / 2;
                    let hi = 15i64 - off as i64;
                    // Hearth's layout (hx_quant.h, hx_block_q4 at b5d3f14, as read by the CC track):
                    // byte j holds element j in its low nibble and element j+N/2 in its high
                    // nibble, stored as q+K. Body as in derivation D-C1.
                    gen.push_str(&format!(
                        "#[derive(Copy, Clone)] #[format_derived] pub struct {tn} {{ pub b: [u8; {half}] }}\n\
                         impl {tn} {{\n\
                         \x20   #[format_accessor] pub fn elem(&self, i: usize) -> i32\n\
                         \x20       requires i < {count}\n\
                         \x20       ensures -{off} <= result && result <= {hi}\n\
                         \x20   {{\n\
                         \x20       let raw: u8 = if i < {half} {{ self.b[i] & 0x0F }} else {{ self.b[i - {half}] >> 4 }};\n\
                         \x20       (raw as i32) - {off}\n\
                         \x20   }}\n\
                         }}\n"
                    ));
                }
                return Ok(tn);
            }
            Ok(n.to_string())
        }
        ast::FormatCode::Array(inner, n) => {
            let it = code_ty_text(inner, prog, gen, done)?;
            let nn = lit_u64(n).unwrap_or(0);
            Ok(format!("[{it}; {nn}]"))
        }
    }
}

fn gen_formats(prog: &mut Program, items: &[Item], module: &str, role: FileRole, out: &mut Vec<(Vec<Item>, String, FileRole, u16)>) {
    let mut done = BTreeSet::new();
    for it in items {
        match it {
            Item::Format(f) => {
                let mut gen = String::new();
                let mut fields = Vec::new();
                let mut oos = None;
                for fld in &f.fields {
                    match code_ty_text(&fld.code, prog, &mut gen, &mut done) {
                        Ok(t) => fields.push(format!("pub {}: {}", fld.name.name, t)),
                        Err((kw, sp)) => {
                            if oos.is_none() {
                                oos = Some((kw, sp));
                            }
                            fields.push(format!("pub {}: u8", fld.name.name));
                        }
                    }
                }
                if let Some((kw, sp)) = oos {
                    prog.oos.push((kw, sp));
                }
                let text = format!("{gen}#[derive(Copy, Clone)] #[format_struct] pub struct {} {{ {} }}\n", f.name.name, fields.join(", "));
                let name = format!("<format {}>", f.name.name);
                let id = prog.sm.add(&name, &text, role);
                match crate::parser::parse_source(id, &text, true) {
                    Ok(items) => out.push((items, module.to_string(), role, id)),
                    Err(d) => prog.diags.push(d),
                }
            }
            Item::Mod(m) => gen_formats(prog, &m.items, &join_path(module, &m.name.name), role, out),
            _ => {}
        }
    }
}

// ---------------------------------------------------------------- lowering

pub struct Lowerer<'a> {
    pub p: &'a mut Program,
}

impl<'a> Lowerer<'a> {
    fn adt_by_path(&self, path: &str) -> Option<AdtId> {
        match self.p.names.get(path) {
            Some(Def::Adt(a)) => Some(*a),
            _ => None,
        }
    }
    fn trait_by_path(&self, path: &str) -> Option<TraitId> {
        match self.p.names.get(path) {
            Some(Def::Trait(t)) => Some(*t),
            _ => None,
        }
    }

    fn generics(&mut self, g: &ast::Generics, parent: &[GParam], cx_base: &TyCx, module: &str) -> (Vec<GParam>, TyCx) {
        let mut out: Vec<GParam> = parent.to_vec();
        let mut cx = cx_base.clone();
        for gp in &g.params {
            if gp.is_lifetime {
                self.p.diags.push(Diag::new("E-LIFETIME", gp.name.span, format!("lifetime parameter `{}`: lifetimes do not exist (FF-REF)", gp.name.name)));
                continue;
            }
            cx.params.push(gp.name.name.clone());
            cx.bounds.push(vec![]);
            out.push(GParam { name: gp.name.name.clone(), is_const: None, bounds: vec![], relax_local: false, relax_linear: false, span: gp.name.span });
        }
        // bounds (after all names are known)
        let base = parent.len();
        let mut k = 0;
        for gp in g.params.iter() {
            if gp.is_lifetime {
                continue;
            }
            let idx = base + k;
            k += 1;
            if let Some(ct) = &gp.is_const {
                let t = self.p.lower_ty(ct, &cx, module);
                out[idx].is_const = Some(t);
            }
            let mut tmp = out[idx].clone();
            tmp.bounds.clear();
            self.p.lower_bounds(&gp.bounds, &cx, module, &mut tmp);
            out[idx].bounds.extend(tmp.bounds);
            out[idx].relax_local |= tmp.relax_local;
            out[idx].relax_linear |= tmp.relax_linear;
            cx.bounds[idx] = out[idx].bounds.clone();
        }
        for (t, bs) in &g.wheres {
            if let TypeKind::Path(p) = &t.kind {
                if let Some(n) = p.single() {
                    if let Some(i) = cx.params.iter().position(|x| x == n) {
                        let mut tmp = out[i].clone();
                        tmp.bounds.clear();
                        self.p.lower_bounds(bs, &cx, module, &mut tmp);
                        out[i].bounds.extend(tmp.bounds);
                        cx.bounds[i] = out[i].bounds.clone();
                        continue;
                    }
                }
            }
            // bounds on other types are not checked by mithi v0
        }
        (out, cx)
    }

    fn field_defs(&mut self, fs: &[ast::FieldDecl], cx: &TyCx, module: &str) -> Vec<FieldDef> {
        // a field name may appear once (rustc E0124)
        let mut seen = BTreeSet::new();
        for f in fs {
            if !seen.insert(f.name.name.clone()) {
                self.p.diags.push(Diag::new("E-TYPE", f.name.span, format!("duplicate definition: field `{}` is declared more than once", f.name.name)));
            }
        }
        fs.iter()
            .map(|f| {
                let ty = self.p.lower_ty(&f.ty, cx, module);
                let range = f.attrs.iter().find(|a| a.name == "range").and_then(parse_range_attr);
                FieldDef { name: f.name.name.clone(), ty, is_pub: f.is_pub, range, span: f.name.span }
            })
            .collect()
    }

    /// Pass 1: ADT generics and fields, trait headers.
    pub fn lower_items_pass1(&mut self, items: &[Item], module: &str, role: FileRole) {
        for it in items {
            match it {
                Item::Struct(s) => {
                    let Some(id) = self.adt_by_path(&join_path(module, &s.name.name)) else { continue };
                    if self.p.adts[id as usize].role != role {
                        continue;
                    }
                    let (gs, cx) = self.generics(&s.generics, &[], &TyCx::default(), module);
                    self.p.adts[id as usize].generics = gs;
                    let cx = TyCx { self_ty: Some(Ty::Adt(id, (0..cx.params.len() as u32).map(Ty::Param).collect())), ..cx };
                    let (fields, tuple, unit) = match &s.data {
                        VariantData::Unit => (vec![], false, true),
                        VariantData::Tuple(f) => (self.field_defs(f, &cx, module), true, false),
                        VariantData::Struct(f) => (self.field_defs(f, &cx, module), false, false),
                    };
                    let a = &mut self.p.adts[id as usize];
                    if s.opaque && fields.is_empty() && matches!(a.kind, AdtKind::Struct) {
                        a.kind = AdtKind::Opaque;
                    }
                    a.partial = s.opaque;
                    a.variants = vec![VariantDef { name: s.name.name.clone(), fields, tuple, unit }];
                }
                Item::Enum(e) => {
                    let Some(id) = self.adt_by_path(&join_path(module, &e.name.name)) else { continue };
                    if self.p.adts[id as usize].role != role {
                        continue;
                    }
                    let (gs, cx) = self.generics(&e.generics, &[], &TyCx::default(), module);
                    self.p.adts[id as usize].generics = gs;
                    let mut vs = vec![];
                    for v in &e.variants {
                        let (fields, tuple, unit) = match &v.data {
                            VariantData::Unit => (vec![], false, true),
                            VariantData::Tuple(f) => (self.field_defs(f, &cx, module), true, false),
                            VariantData::Struct(f) => (self.field_defs(f, &cx, module), false, false),
                        };
                        vs.push(VariantDef { name: v.name.name.clone(), fields, tuple, unit });
                    }
                    self.p.adts[id as usize].variants = vs;
                }
                Item::Trait(t) => {
                    let Some(id) = self.trait_by_path(&join_path(module, &t.name.name)) else { continue };
                    let self_param = GParam { name: "Self".into(), is_const: None, bounds: vec![], relax_local: false, relax_linear: false, span: t.name.span };
                    let base_cx = TyCx { params: vec!["Self".into()], bounds: vec![vec![]], self_ty: Some(Ty::Param(0)), in_trait: Some(id), ..Default::default() };
                    let assoc: Vec<String> = t.members.iter().filter_map(|m| if let ast::TraitMember::Type(n, _) = m { Some(n.name.clone()) } else { None }).collect();
                    self.p.traits[id as usize].assoc_types = assoc;
                    let (gs, _cx) = self.generics(&t.generics, &[self_param], &base_cx, module);
                    self.p.traits[id as usize].generics = gs;
                }
                Item::Mod(m) => self.lower_items_pass1(&m.items, &join_path(module, &m.name.name), role),
                _ => {}
            }
        }
    }

    /// Pass 2: trait methods, impls, functions, consts.
    pub fn lower_items_pass2(&mut self, items: &[Item], module: &str, role: FileRole) {
        for it in items {
            match it {
                Item::Trait(t) => {
                    let Some(id) = self.trait_by_path(&join_path(module, &t.name.name)) else { continue };
                    if self.p.traits[id as usize].role != role {
                        continue;
                    }
                    let tg = self.p.traits[id as usize].generics.clone();
                    let cx = TyCx {
                        params: tg.iter().map(|g| g.name.clone()).collect(),
                        bounds: tg.iter().map(|g| g.bounds.clone()).collect(),
                        self_ty: Some(Ty::Param(0)),
                        in_trait: Some(id),
                        ..Default::default()
                    };
                    let mut sups = vec![];
                    let mut tmp = GParam { name: "Self".into(), is_const: None, bounds: vec![], relax_local: false, relax_linear: false, span: t.name.span };
                    self.p.lower_bounds(&t.supers, &cx, module, &mut tmp);
                    sups.extend(tmp.bounds);
                    self.p.traits[id as usize].supers = sups;
                    for m in &t.members {
                        match m {
                            ast::TraitMember::Fn(f) => {
                                let path = format!("{}::{}", join_path(module, &t.name.name), f.name.name);
                                let fid = self.lower_fn(f, &path, module, role, Owner::Trait(id), &tg, &cx);
                                self.p.traits[id as usize].methods.insert(f.name.name.clone(), fid);
                            }
                            ast::TraitMember::Const(n, ty, v) => {
                                let t2 = self.p.lower_ty(ty, &cx, module);
                                self.p.traits[id as usize].consts.insert(n.name.clone(), (t2, v.clone()));
                            }
                            ast::TraitMember::Type(..) => {}
                        }
                    }
                }
                Item::Impl(im) => self.lower_impl(im, module, role),
                Item::Fn(f) => {
                    let path = join_path(module, &f.name.name);
                    let fid = self.lower_fn(f, &path, module, role, Owner::Free, &[], &TyCx::default());
                    let key = path.clone();
                    match self.p.names.get(&key) {
                        Some(Def::Alias(_)) | None => {
                            self.p.names.insert(key, Def::Fn(fid));
                        }
                        Some(_) => self.p.diags.push(Diag::new("E-TYPE", f.name.span, format!("`{key}` is defined more than once"))),
                    }
                }
                Item::Const(c) => {
                    let path = join_path(module, &c.name.name);
                    if let Some(Def::Const(cid)) = self.p.names.get(&path).cloned() {
                        let t = self.p.lower_ty(&c.ty, &TyCx::default(), module);
                        self.p.consts[cid as usize].ty = t;
                    }
                }
                Item::Mod(m) => self.lower_items_pass2(&m.items, &join_path(module, &m.name.name), role),
                _ => {}
            }
        }
    }

    fn lower_impl(&mut self, im: &ast::ImplDecl, module: &str, role: FileRole) {
        // E-DROP-IMPL (note F-17, C-DROP)
        if let Some(tp) = &im.trait_ {
            if tp.last() == "Drop" {
                self.p.diags.push(Diag::new("E-DROP-IMPL", im.span, "a user `impl Drop`: traps never run user code, so Drop would run on normal paths only (false friend, C-DROP); use a `linear struct` consumed explicitly"));
                return;
            }
        }
        let (gs, cx0) = self.generics(&im.generics, &[], &TyCx { allow_missing_args: false, ..Default::default() }, module);
        let self_ty = self.p.lower_ty(&im.self_ty, &cx0, module);
        let mut cx = cx0.clone();
        cx.self_ty = Some(self_ty.clone());
        let mut trait_ = None;
        if let Some(tp) = &im.trait_ {
            if let Some((tid, mut args, _assoc)) = self.p.lower_trait_ref(tp, &cx, module) {
                // missing trait arguments default to Self (Rhs = Self, PartialEq<Rhs = Self>)
                let want = self.p.traits[tid as usize].generics.len() - 1;
                while args.len() < want {
                    args.push(self_ty.clone());
                }
                trait_ = Some((tid, args));
                cx.impl_trait = Some(tid);
            } else {
                return;
            }
        }
        let iid = self.p.impls.len() as ImplId;
        self.p.impls.push(ImplDef {
            generics: gs.clone(),
            trait_: trait_.clone(),
            self_ty: self_ty.clone(),
            methods: BTreeMap::new(),
            assoc: BTreeMap::new(),
            consts: BTreeMap::new(),
            span: im.span,
            role,
            module: module.to_string(),
            negative: im.negative,
        });
        if let Some((tid, _)) = &trait_ {
            self.p.impls_of_trait.entry(*tid).or_default().push(iid);
        }
        let tyname = match &self_ty {
            Ty::Adt(a, _) => self.p.adts[*a as usize].path.clone(),
            other => join_path(module, &self.p.ty_name(other)),
        };
        for m in &im.members {
            match m {
                ast::ImplMember::Type(n, t) => {
                    let ty = self.p.lower_ty(t, &cx, module);
                    self.p.impls[iid as usize].assoc.insert(n.name.clone(), ty);
                }
                ast::ImplMember::Const(c) => {
                    let ty = self.p.lower_ty(&c.ty, &cx, module);
                    if let Some(v) = &c.value {
                        self.p.impls[iid as usize].consts.insert(c.name.name.clone(), (ty, v.clone()));
                    }
                }
                ast::ImplMember::Fn(f) => {
                    let path = match &trait_ {
                        None => format!("{tyname}::{}", f.name.name),
                        Some((tid, _)) => format!("<{tyname} as {}>::{}", self.p.traits[*tid as usize].name, f.name.name),
                    };
                    if let Some(a) = f.attrs.iter().find(|a| a.name == "default") {
                        self.p.diags.push(Diag::new("E-SPECIALIZE", a.span, "`default fn`: specialization is not in Mithril (DR-005)"));
                    }
                    let fid = self.lower_fn(f, &path, module, role, Owner::Impl(iid), &gs, &cx);
                    if self.p.impls[iid as usize].methods.contains_key(&f.name.name) {
                        // rustc E0201 / E0592
                        self.p.diags.push(Diag::new("E-TYPE", f.name.span, format!("duplicate definition: method `{}` is defined more than once for `{tyname}`", f.name.name)));
                        continue;
                    }
                    self.p.impls[iid as usize].methods.insert(f.name.name.clone(), fid);
                }
            }
        }
        // trait impl conformance: every required method present
        if let Some((tid, _)) = &trait_ {
            let tr = self.p.traits[*tid as usize].clone();
            for (mname, mfid) in &tr.methods {
                let has_default = self.p.fns[*mfid as usize].body.is_some() || self.p.fns[*mfid as usize].builtin.is_some();
                if !self.p.impls[iid as usize].methods.contains_key(mname) && !has_default {
                    self.p.diags.push(Diag::new("E-TYPE", im.span, format!("missing method `{mname}` in impl of `{}`", tr.name)));
                }
            }
            for (mname, fid) in self.p.impls[iid as usize].methods.clone() {
                if !tr.methods.contains_key(&mname) {
                    self.p.diags.push(Diag::new("E-TYPE", self.p.fns[fid as usize].span, format!("method `{mname}` is not a member of trait `{}`", tr.name)));
                }
            }
            for a in &tr.assoc_types {
                if !self.p.impls[iid as usize].assoc.contains_key(a) {
                    self.p.diags.push(Diag::new("E-TYPE", im.span, format!("missing associated type `{a}` in impl of `{}`", tr.name)));
                }
            }
            // each method's signature is the trait's, with Self and the trait's arguments
            // substituted (note section 5.12; Rust E0050, E0053, E0185, E0186)
            let (_, targs) = trait_.clone().unwrap_or((*tid, vec![]));
            for (mname, ifid) in self.p.impls[iid as usize].methods.clone() {
                let Some(&dfid) = tr.methods.get(&mname) else { continue };
                if let Some(msg) = self.signature_mismatch(dfid, ifid, &self_ty, &targs, iid, *tid) {
                    let sp = self.p.fns[ifid as usize].sig_span;
                    self.p.diags.push(Diag::new("E-TYPE", sp, format!("method `{mname}` does not match the declaration in trait `{}`: {msg}", tr.name)));
                }
            }
        }
    }

    /// The first difference between an impl method's signature and its trait declaration's.
    fn signature_mismatch(&self, dfid: FnId, ifid: FnId, self_ty: &Ty, targs: &[Ty], iid: ImplId, tid: TraitId) -> Option<String> {
        let d = &self.p.fns[dfid as usize];
        let m = &self.p.fns[ifid as usize];
        if d.self_mode != m.self_mode {
            let show = |x: Option<SelfMode>| match x {
                None => "no `self`",
                Some(SelfMode::Value) => "`self`",
                Some(SelfMode::Ref) => "`&self`",
                Some(SelfMode::RefMut) => "`&mut self`",
            };
            return Some(format!("the trait has {}, the impl has {}", show(d.self_mode), show(m.self_mode)));
        }
        if d.params.len() != m.params.len() {
            return Some(format!("the trait has {} parameter(s), the impl has {}", d.params.len(), m.params.len()));
        }
        let d_own = d.generics.len().saturating_sub(d.n_parent);
        let m_own = m.generics.len().saturating_sub(m.n_parent);
        if d_own != m_own {
            return Some(format!("the trait has {d_own} generic parameter(s), the impl has {m_own}"));
        }
        let mut substs = vec![self_ty.clone()];
        substs.extend(targs.iter().cloned());
        while substs.len() < d.n_parent {
            substs.push(self_ty.clone());
        }
        for k in 0..d_own {
            substs.push(Ty::Param((m.n_parent + k) as u32));
        }
        let assoc = self.p.impls[iid as usize].assoc.clone();
        let norm = |t: &Ty| -> Ty { normalize_assoc(t, self_ty, tid, &assoc) };
        for (i, (dp, mp)) in d.params.iter().zip(m.params.iter()).enumerate() {
            let dt = norm(&dp.ty.subst(&substs));
            let mt = norm(&mp.ty);
            if comparable(&dt) && comparable(&mt) && dt != mt {
                return Some(format!("parameter {} has type `{}` in the trait and `{}` in the impl", i + 1, self.p.ty_name(&dt), self.p.ty_name(&mt)));
            }
        }
        let dr = norm(&d.ret.subst(&substs));
        let mr = norm(&m.ret);
        if comparable(&dr) && comparable(&mr) && dr != mr {
            return Some(format!("the result type is `{}` in the trait and `{}` in the impl", self.p.ty_name(&dr), self.p.ty_name(&mr)));
        }
        None
    }

    /// E-COHERENCE (note section 5.12): two impls of one trait that can apply to the same type
    /// (overlap, including a derive and a manual impl), and impls of a std trait for a type with
    /// no local component (the orphan rule). Inherent methods defined twice for one type are
    /// duplicate definitions (rustc E0592).
    pub fn check_coherence(&mut self) {
        let impls = self.p.impls.clone();
        let local = |t: &Ty, p: &Program| -> bool {
            let mut l = false;
            t.walk(&mut |x| {
                if let Ty::Adt(a, _) = x {
                    if p.adts[*a as usize].role != FileRole::Std {
                        l = true;
                    }
                }
            });
            l
        };
        for (i, a) in impls.iter().enumerate() {
            if a.negative {
                continue;
            }
            if let Some((tid, aargs)) = &a.trait_ {
                let tr = &self.p.traits[*tid as usize];
                if a.role == FileRole::User && tr.role == FileRole::Std {
                    let fundamental = match &a.self_ty {
                        Ty::Ref(_, x) => (**x).clone(),
                        t => t.clone(),
                    };
                    if !local(&fundamental, self.p) && !aargs.iter().any(|x| local(x, self.p)) {
                        self.p.diags.push(Diag::new("E-COHERENCE", a.span, format!("impl of the std trait `{}` for a type that is not defined in this program (the orphan rule)", tr.name)));
                    }
                }
                // a derive of the same trait on the same type
                if a.role != FileRole::Std {
                    if let (Ty::Adt(ad, _), Some(lang)) = (&a.self_ty, tr.lang.as_deref()) {
                        if self.p.adts[*ad as usize].derives(lang) {
                            self.p.diags.push(Diag::new("E-COHERENCE", a.span, format!("`{}` both derives `{lang}` and implements it", self.p.adts[*ad as usize].name)));
                        }
                    }
                }
                for b in impls.iter().skip(i + 1) {
                    if b.negative || a.role == FileRole::Std && b.role == FileRole::Std {
                        continue;
                    }
                    let Some((tid2, bargs)) = &b.trait_ else { continue };
                    if tid2 != tid {
                        continue;
                    }
                    let overlap = (super::analysis::ty_matches(&a.self_ty, &b.self_ty) || super::analysis::ty_matches(&b.self_ty, &a.self_ty))
                        && aargs.len() == bargs.len()
                        && aargs.iter().zip(bargs).all(|(x, y)| super::analysis::ty_matches(x, y) || super::analysis::ty_matches(y, x));
                    if overlap {
                        self.p.diags.push(Diag::new("E-COHERENCE", b.span, format!("conflicting impls of `{}`: this impl and an earlier one can apply to the same type", self.p.traits[*tid as usize].name)));
                    }
                }
            } else if a.role != FileRole::Std {
                // inherent methods: one definition per name and self type
                for b in impls.iter().skip(i + 1) {
                    if b.trait_.is_some() || b.role == FileRole::Std {
                        continue;
                    }
                    if !(super::analysis::ty_matches(&a.self_ty, &b.self_ty) || super::analysis::ty_matches(&b.self_ty, &a.self_ty)) {
                        continue;
                    }
                    for (n, fid) in &b.methods {
                        if a.methods.contains_key(n) {
                            let sp = self.p.fns[*fid as usize].span;
                            self.p.diags.push(Diag::new("E-TYPE", sp, format!("duplicate definition: method `{n}` is defined more than once for one type")));
                        }
                    }
                }
            }
        }
    }

    fn lower_fn(&mut self, f: &ast::FnDecl, path: &str, module: &str, role: FileRole, owner: Owner, parent: &[GParam], parent_cx: &TyCx) -> FnId {
        if f.is_async {
            self.p.diags.push(Diag::new("E-ASYNC", f.span, "`async fn`: no async in v1 (FF-ASYNC, DR-005)"));
        }
        if f.is_unsafe && role == FileRole::User {
            self.p.diags.push(Diag::new("E-GRANT-UNSAFE", f.span, "`unsafe fn` needs the package grant `unsafe` (FF-UNSAFE)"));
        }
        if f.is_extern && role == FileRole::User {
            self.p.diags.push(Diag::new("E-GRANT-FOREIGN", f.span, "`extern` functions need the package grant `foreign` (01 section 6.1)"));
        }
        let (mut gs, mut cx) = self.generics(&f.generics, parent, parent_cx, module);
        let n_parent = parent.len();
        let mut params = Vec::new();
        let mut self_mode = None;
        if let Some((sp, span)) = &f.self_param {
            let st = cx.self_ty.clone().unwrap_or(Ty::Error);
            let (mode, ty) = match sp {
                ast::SelfParam::Value { .. } => (SelfMode::Value, st),
                ast::SelfParam::Ref { mutable: false } => (SelfMode::Ref, Ty::Ref(false, Box::new(st))),
                ast::SelfParam::Ref { mutable: true } => (SelfMode::RefMut, Ty::Ref(true, Box::new(st))),
            };
            self_mode = Some(mode);
            params.push(ParamDef { name: "self".into(), pat: None, ty, range: None, span: *span, ty_ast: None });
        }
        for p in &f.params {
            // `impl Trait` in argument position: an anonymous generic parameter
            let ty = if let TypeKind::ImplTrait(bs) = &p.ty.kind {
                let idx = gs.len() as u32;
                let mut gp = GParam { name: format!("impl#{idx}"), is_const: None, bounds: vec![], relax_local: false, relax_linear: false, span: p.ty.span };
                self.p.lower_bounds(bs, &cx, module, &mut gp);
                cx.params.push(gp.name.clone());
                cx.bounds.push(gp.bounds.clone());
                gs.push(gp);
                Ty::Param(idx)
            } else {
                self.p.lower_ty(&p.ty, &cx, module)
            };
            let name = match &p.pat.kind {
                ast::PatKind::Ident { name, .. } => name.name.clone(),
                _ => "_".into(),
            };
            let range = p.attrs.iter().find(|a| a.name == "range").and_then(parse_range_attr);
            if name != "_" && params.iter().any(|q: &ParamDef| q.name == name) {
                // rustc E0415
                self.p.diags.push(Diag::new("E-TYPE", p.span, format!("duplicate definition: parameter `{name}` is bound more than once")));
            }
            params.push(ParamDef { name, pat: Some(p.pat.clone()), ty, range, span: p.span, ty_ast: Some(p.ty.clone()) });
        }
        let ret = match &f.ret {
            Some(t) => self.p.lower_ty(t, &cx, module),
            None => Ty::Unit,
        };
        let uses = f.uses.as_ref().map(|effs| {
            let mut r = Row::new();
            for e in effs {
                match Label::parse(&e.name.name, e.arg.as_ref().map(|a| a.name.as_str())) {
                    Some(l) => {
                        r.insert(l);
                    }
                    None => self.p.diags.push(Diag::new("E-TYPE", e.name.span, format!("unknown effect label `{}` (the v0 label set is fixed, 01 section 6.1)", e.name.name))),
                }
            }
            r
        });
        let builtin = attr_value(&f.attrs, "builtin");
        let fid = self.p.fns.len() as FnId;
        self.p.fns.push(FnDef {
            name: f.name.name.clone(),
            path: path.to_string(),
            module: module.to_string(),
            kind: f.kind,
            owner,
            generics: gs,
            n_parent,
            self_mode,
            params,
            ret,
            ret_ast: f.ret.clone(),
            uses,
            requires: f.requires.clone(),
            ensures: f.ensures.clone(),
            body: f.body.clone(),
            builtin,
            attrs: f.attrs.clone(),
            is_pub: f.is_pub || matches!(owner, Owner::Trait(_)),
            span: f.span,
            sig_span: f.sig_span,
            role,
            synthetic: if f.attrs.iter().any(|a| a.name == "format_accessor") { Some("format_accessor".into()) } else { None },
            is_unsafe: f.is_unsafe,
            is_async: f.is_async,
            is_extern: f.is_extern,
        });
        fid
    }

    /// Each `invariant S { φ }` becomes a synthetic predicate `fn S::__invariant(&self) -> bool`.
    pub fn lower_invariants(&mut self) {
        let decls = std::mem::take(&mut self.p.invariant_decls);
        for (inv, module, role) in &decls {
            let names: Vec<String> = inv.ty.segs.iter().map(|s| s.ident.name.clone()).collect();
            let Some(Def::Adt(aid)) = self.p.resolve(module, &names) else {
                self.p.diags.push(Diag::new("E-UNRESOLVED", inv.ty.span, format!("invariant for unknown type `{}`", inv.ty.text())));
                continue;
            };
            if self.p.adts[aid as usize].invariant.is_some() {
                self.p.diags.push(Diag::new("E-TYPE", inv.span, "a type has at most one invariant block"));
                continue;
            }
            let gs = self.p.adts[aid as usize].generics.clone();
            let self_ty = Ty::Adt(aid, (0..gs.len() as u32).map(Ty::Param).collect());
            let path = format!("{}::__invariant", self.p.adts[aid as usize].path);
            let fid = self.p.fns.len() as FnId;
            let body = ast::Block { stmts: vec![], tail: Some(Box::new(inv.cond.clone())), span: inv.span, is_unsafe: false };
            self.p.fns.push(FnDef {
                name: "__invariant".into(),
                path,
                module: module.clone(),
                kind: FnKind::Plain,
                owner: Owner::Free,
                generics: gs.clone(),
                n_parent: gs.len(),
                self_mode: Some(SelfMode::Ref),
                params: vec![ParamDef { name: "self".into(), pat: None, ty: Ty::Ref(false, Box::new(self_ty)), range: None, span: inv.span, ty_ast: None }],
                ret: Ty::Bool,
                ret_ast: None,
                uses: Some(Row::new()),
                requires: vec![],
                ensures: vec![],
                body: Some(body),
                builtin: None,
                attrs: vec![],
                is_pub: false,
                span: inv.span,
                sig_span: inv.span,
                role: *role,
                synthetic: Some(format!("invariant:{aid}")),
                is_unsafe: false,
                is_async: false,
                is_extern: false,
            });
            self.p.adts[aid as usize].invariant = Some(fid);
        }
        self.p.invariant_decls = decls;
    }

    fn finish_formats(&mut self) {
        for i in 0..self.p.formats.len() {
            let mut size = Some(0u64);
            for f in &self.p.formats[i].decl.fields {
                size = match (size, code_size(&f.code)) {
                    (Some(a), Some(b)) => Some(a + b),
                    _ => None,
                };
            }
            self.p.formats[i].size = size;
            // the format's struct is the generated one; point the format at it
            let path = join_path(&self.p.formats[i].module, &self.p.formats[i].decl.name.name);
            if let Some(Def::Adt(a)) = self.p.names.get(&path) {
                self.p.formats[i].adt = *a;
            }
        }
    }
}

/// Bounds helper used by typeck: Fn-family bound of a generic parameter, if any.
pub fn fn_bound(gp: &GParam) -> Option<(u8, Vec<Ty>, Ty)> {
    gp.bounds.iter().find_map(|b| match b {
        BoundDef::Fn { kind, params, ret } => Some((*kind, params.clone(), ret.clone())),
        _ => None,
    })
}

pub fn has_bound_kind(bs: &[Bound]) -> bool {
    !bs.is_empty()
}

/// `<Self as Trait>::Name` resolved through an impl's associated types.
fn normalize_assoc(t: &Ty, self_ty: &Ty, tid: TraitId, assoc: &BTreeMap<String, Ty>) -> Ty {
    match t {
        Ty::Assoc(x, tr, n) if *tr == tid && **x == *self_ty => assoc.get(n).cloned().unwrap_or_else(|| t.clone()),
        Ty::Ref(m, x) => Ty::Ref(*m, Box::new(normalize_assoc(x, self_ty, tid, assoc))),
        Ty::Tuple(v) => Ty::Tuple(v.iter().map(|x| normalize_assoc(x, self_ty, tid, assoc)).collect()),
        Ty::Slice(x) => Ty::Slice(Box::new(normalize_assoc(x, self_ty, tid, assoc))),
        Ty::Array(x, n) => Ty::Array(Box::new(normalize_assoc(x, self_ty, tid, assoc)), n.clone()),
        Ty::Adt(a, v) => Ty::Adt(*a, v.iter().map(|x| normalize_assoc(x, self_ty, tid, assoc)).collect()),
        _ => t.clone(),
    }
}

/// A type whose comparison means something (no error, inference or opaque part).
fn comparable(t: &Ty) -> bool {
    let mut ok = true;
    t.walk(&mut |x| {
        if matches!(x, Ty::Error | Ty::Infer(_) | Ty::IntVar(_) | Ty::FloatVar(_) | Ty::Opaque(_) | Ty::Assoc(..)) {
            ok = false;
        }
    });
    ok
}
