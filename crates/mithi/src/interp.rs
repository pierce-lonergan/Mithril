//! The tree-walking interpreter: the meaning of a checked program (note section 6), run as its
//! serial projection. Traps are deterministic: a trap names its site (kind, definition, anchor),
//! ends the run's fail domain (here: the entry point or test case), runs no user code on the way,
//! and reports the Linear values it abandons, newest first (section 6.3). `par for` runs its
//! serial projection, so the lowest failing index wins by construction (section 6.4).
//! `deterministic` blocks are administrative frames with no dynamic effect (section 6.6).

use crate::ast::{BinOp, UnOp};
use crate::check::Checked;
use crate::diag::Span;
use crate::program::{AdtKind, FnDef};
use crate::thir::*;
use crate::types::*;
use std::cell::RefCell;
use std::collections::HashMap;
use std::rc::Rc;

pub type Cell = Rc<RefCell<V>>;

#[derive(Clone, Debug)]
pub struct Ptr {
    pub cell: Cell,
    pub path: Vec<usize>,
}

#[derive(Clone, Debug)]
pub enum V {
    Unit,
    Bool(bool),
    Int(i128),
    F32(u32),
    F64(u64),
    F16(u16),
    Bf16(u16),
    Char(char),
    Str(Rc<str>),
    Tuple(Vec<V>),
    Arr(Vec<V>),
    Adt(AdtId, u32, Vec<V>),
    Vec(Vec<V>),
    String(String),
    Ref(Ptr),
    Slice(Ptr, usize, usize),
    Closure(Rc<CloV>),
    Iter(Rc<RefCell<It>>),
    Mutex(Cell, Rc<RefCell<bool>>),
    Hint(Option<Box<V>>),
    FnRef(FnId, Vec<Ty>),
    Ctor(AdtId, u32),
    Moved,
    Opaque(&'static str),
}

#[derive(Debug)]
pub struct CloV {
    pub id: ClosureId,
    /// cells of the enclosing frame's locals the closure sees (by-ref captures share the cell)
    pub env: Vec<(LocalId, Cell)>,
    pub nlocals: usize,
    pub targs: Vec<Ty>,
    pub owner: FnId,
}

#[derive(Debug)]
pub enum It {
    Range { cur: i128, end: i128 },
    Items(std::collections::VecDeque<V>),
    Map(Box<It>, V),
    Filter(Box<It>, V),
    FilterMap(Box<It>, V),
    Enumerate(Box<It>, usize),
    Zip(Box<It>, Box<It>),
    Take(Box<It>, usize),
    Skip(Box<It>, usize),
    StepBy(Box<It>, usize, bool),
    Chain(Box<It>, Box<It>),
    Copied(Box<It>),
    /// a user iterator: the receiver value and its `next`
    User(Cell, FnId, Vec<Ty>),
    Shared(Rc<RefCell<It>>),
}

#[derive(Clone, Debug)]
pub struct Trap {
    pub kind: String,
    pub def: String,
    pub anchor: String,
    pub msg: Option<String>,
    pub abandoned: Vec<String>,
    /// the `par for` iteration indices the trap happened in, innermost first (m·ī, §6.4)
    pub par_index: Vec<String>,
}

#[derive(Debug)]
pub enum Ctrl {
    Trap(Trap),
    Return(V),
    Break(LoopId, V),
    Continue(LoopId),
    Host(String),
}

type R<T> = Result<T, Ctrl>;

struct Frame {
    fid: FnId,
    locals: Vec<Option<Cell>>,
    targs: Vec<Ty>,
    /// creation order of Linear locals (for abandonment on trap paths)
    linear: Vec<LocalId>,
}

pub struct Interp<'a> {
    c: &'a Checked,
    frames: Vec<Frame>,
    depth: u32,
    pub steps: u64,
    pub max_steps: u64,
    const_cache: HashMap<u32, V>,
    /// set while the callee of a closure call is read: it is called in place, not copied
    in_place_call: bool,
}

#[derive(Clone)]
enum Place {
    P(Ptr),
    S(Ptr, usize, usize),
}

fn new_cell(v: V) -> Cell {
    Rc::new(RefCell::new(v))
}

fn ty_mentions_closure(t: &Ty) -> bool {
    let mut h = false;
    t.walk(&mut |x| {
        if matches!(x, Ty::Closure(_)) {
            h = true;
        }
    });
    h
}

/// A copy of a value whose closures own fresh copies of their by-move captured state; by-ref
/// and by-mut captures stay shared (they are borrows of the creating frame's places).
fn fresh_closures(closures: &[ClosureDef], v: V) -> V {
    match v {
        V::Closure(cl) => {
            let cd = &closures[cl.id as usize];
            let env = cl
                .env
                .iter()
                .map(|(l, cell)| {
                    let by_move = cd.captures.iter().any(|c| c.local == *l && c.mode == CaptureMode::Move);
                    if by_move {
                        let inner = cell.borrow().clone();
                        (*l, new_cell(fresh_closures(closures, inner)))
                    } else {
                        (*l, cell.clone())
                    }
                })
                .collect();
            V::Closure(Rc::new(CloV { id: cl.id, env, nlocals: cl.nlocals, targs: cl.targs.clone(), owner: cl.owner }))
        }
        V::Tuple(xs) => V::Tuple(xs.into_iter().map(|x| fresh_closures(closures, x)).collect()),
        V::Arr(xs) => V::Arr(xs.into_iter().map(|x| fresh_closures(closures, x)).collect()),
        V::Adt(a, k, xs) => V::Adt(a, k, xs.into_iter().map(|x| fresh_closures(closures, x)).collect()),
        other => other,
    }
}

fn int_ty(t: &Ty) -> Option<IntTy> {
    match t {
        Ty::Int(i) => Some(*i),
        _ => None,
    }
}

pub fn f16_to_f32(h: u16) -> f32 {
    let sign = ((h >> 15) as u32) << 31;
    let exp = ((h >> 10) & 0x1f) as u32;
    let man = (h & 0x3ff) as u32;
    let bits = if exp == 0 {
        if man == 0 {
            sign
        } else {
            // subnormal: man × 2^-24; normalise with k shifts to 1.f × 2^(-14-k)
            let mut e: i32 = 0;
            let mut m = man;
            while m & 0x400 == 0 {
                m <<= 1;
                e -= 1;
            }
            let m = m & 0x3ff;
            let exp32 = (127 - 14 + e) as u32;
            sign | (exp32 << 23) | (m << 13)
        }
    } else if exp == 0x1f {
        sign | 0x7f80_0000 | (man << 13)
    } else {
        sign | ((exp + 127 - 15) << 23) | (man << 13)
    };
    f32::from_bits(bits)
}

/// canon::sum16 (02 section 5; NUMERICS section 1): 16 lane accumulators from +0.0, element i
/// into lane i & 15, then the tree s = 8, 4, 2, 1.
pub fn canon_sum16(a: &[f32]) -> f32 {
    let mut l = [0.0f32; 16];
    for (i, x) in a.iter().enumerate() {
        l[i & 15] += *x;
    }
    for s in [8usize, 4, 2, 1] {
        for j in 0..s {
            l[j] += l[j + s];
        }
    }
    l[0]
}

impl<'a> Interp<'a> {
    pub fn new(c: &'a Checked) -> Interp<'a> {
        Interp { c, frames: vec![], depth: 0, steps: 0, max_steps: 200_000_000, const_cache: HashMap::new(), in_place_call: false }
    }

    fn trap<T>(&self, kind: &str, sp: Span, msg: Option<String>) -> R<T> {
        let def = self.frames.last().map(|f| self.c.program.fns[f.fid as usize].path.clone()).unwrap_or_default();
        Err(Ctrl::Trap(Trap { kind: kind.to_string(), def, anchor: self.c.program.sm.snippet(sp), msg, abandoned: vec![], par_index: vec![] }))
    }
    fn host<T>(&self, m: impl Into<String>) -> R<T> {
        Err(Ctrl::Host(m.into()))
    }

    fn subst(&self, t: &Ty) -> Ty {
        match self.frames.last() {
            Some(f) if !f.targs.is_empty() => t.subst(&f.targs),
            _ => t.clone(),
        }
    }

    // ------------------------------------------------------------ calls
    /// Operands evaluated left to right (arguments, fields, elements). A Linear value already
    /// evaluated is a temporary in Φ.lin until the call or the aggregate takes it (F-42): if a
    /// later operand traps, it is abandoned, newer than the frame's named Linear locals.
    fn eval_operands(&mut self, es: &[TExpr], name: &dyn Fn(usize) -> String) -> R<Vec<V>> {
        let mut vs = Vec::with_capacity(es.len());
        let mut temps: Vec<usize> = vec![];
        for (k, a) in es.iter().enumerate() {
            match self.eval(a) {
                Ok(v) => {
                    let ty = self.subst(&a.ty);
                    if crate::analysis::wf::is_linear(self.c, &ty) {
                        temps.push(k);
                    }
                    vs.push(v);
                }
                Err(Ctrl::Trap(mut t)) => {
                    let here = self.frames.last().map(|f| self.c.program.fns[f.fid as usize].path.clone()).unwrap_or_default();
                    for k in temps.iter().rev() {
                        t.abandoned.push(format!("{} in {here}", name(*k)));
                    }
                    return Err(Ctrl::Trap(t));
                }
                Err(e) => return Err(e),
            }
        }
        Ok(vs)
    }

    pub fn call(&mut self, fid: FnId, targs: Vec<Ty>, args: Vec<V>, sp: Span) -> R<V> {
        self.depth += 1;
        if self.depth > 2000 {
            self.depth -= 1;
            return self.host("stack depth limit (2000 frames): mithi does not model stack exhaustion (F-8)");
        }
        let r = self.call_inner(fid, targs, args, sp);
        self.depth -= 1;
        r
    }

    fn call_inner(&mut self, fid: FnId, targs: Vec<Ty>, args: Vec<V>, sp: Span) -> R<V> {
        let f: &FnDef = &self.c.program.fns[fid as usize];
        if let Some(b) = &f.builtin {
            let b = b.clone();
            return self.builtin(&b, fid, &targs, args, sp);
        }
        // trait method declarations reached directly: dispatch on the receiver
        if let crate::program::Owner::Trait(tr) = f.owner {
            if f.body.is_none() || targs.first().map(|t| !matches!(t, Ty::Param(_))).unwrap_or(false) {
                let st = targs.first().cloned().unwrap_or(Ty::Error);
                if let Some(t) = crate::analysis::resolve_impl_method(self.c, tr, &st, &f.name) {
                    if t != fid {
                        let im_targs = impl_targs(self.c, t, &st);
                        return self.call(t, im_targs, args, sp);
                    }
                }
                if f.body.is_none() {
                    return self.derived(&f.name.clone(), &st, args, sp);
                }
            }
        }
        let Some(body) = self.c.bodies.get(&fid) else {
            return self.host(format!("`{}` has no body", f.path));
        };
        if f.body.is_none() {
            return self.host(format!("`{}` is a prelude signature without a body; mithi cannot run it", f.path));
        }
        let mut frame = Frame { fid, locals: vec![None; body.locals.len()], targs, linear: vec![] };
        for (i, pl) in body.params.iter().enumerate() {
            let v = args.get(i).cloned().unwrap_or(V::Unit);
            frame.locals[*pl as usize] = Some(new_cell(v));
            if crate::analysis::wf::is_linear(self.c, &body.locals[*pl as usize].ty) {
                frame.linear.push(*pl);
            }
        }
        self.frames.push(frame);
        // requires (callers assert them; mithi checks at entry, which is observably the same)
        for r in &body.requires {
            match self.eval(r) {
                Ok(V::Bool(true)) => {}
                Ok(V::Bool(false)) => {
                    let name = f.name.clone();
                    let r = self.trap(&format!("req({name})"), r.span, None);
                    self.frames.pop();
                    return r;
                }
                Ok(_) => {}
                Err(Ctrl::Trap(mut t)) => {
                    t.kind = "contract_ovf".into();
                    self.frames.pop();
                    return Err(Ctrl::Trap(t));
                }
                Err(e) => {
                    self.frames.pop();
                    return Err(e);
                }
            }
        }
        let res = match self.eval(&body.expr) {
            Ok(v) => Ok(v),
            Err(Ctrl::Return(v)) => Ok(v),
            Err(Ctrl::Trap(mut t)) => {
                // abandon live Linear values, newest first (section 6.3)
                let fr = self.frames.last().unwrap();
                for l in fr.linear.iter().rev() {
                    if let Some(cell) = &fr.locals[*l as usize] {
                        if !matches!(*cell.borrow(), V::Moved) {
                            t.abandoned.push(format!("{} in {}", body.locals[*l as usize].name, f.path));
                        }
                    }
                }
                Err(Ctrl::Trap(t))
            }
            Err(e) => Err(e),
        };
        let res = match res {
            Ok(v) => {
                // ensures
                if !body.ensures.is_empty() {
                    if let Some(rl) = body.result_local {
                        self.frames.last_mut().unwrap().locals[rl as usize] = Some(new_cell(v.clone()));
                        for en in &body.ensures {
                            match self.eval(en) {
                                Ok(V::Bool(false)) => {
                                    let name = f.name.clone();
                                    let r = self.trap(&format!("ens({name})"), en.span, None);
                                    self.frames.pop();
                                    return r;
                                }
                                Err(Ctrl::Trap(mut t)) => {
                                    t.kind = "contract_ovf".into();
                                    self.frames.pop();
                                    return Err(Ctrl::Trap(t));
                                }
                                _ => {}
                            }
                        }
                    }
                }
                Ok(v)
            }
            e => e,
        };
        self.frames.pop();
        res
    }

    /// Derived and builtin trait methods (clone, eq, cmp, default, partial_cmp ...).
    fn derived(&mut self, name: &str, st: &Ty, args: Vec<V>, sp: Span) -> R<V> {
        match name {
            // a cloned closure owns a copy of its by-move state (K-CloCopy, F-104)
            "clone" => Ok(fresh_closures(&self.c.closures, self.deref_val(&args[0]))),
            "eq" => Ok(V::Bool(self.val_eq(&self.deref_val(&args[0]), &self.deref_val(&args[1])))),
            "ne" => Ok(V::Bool(!self.val_eq(&self.deref_val(&args[0]), &self.deref_val(&args[1])))),
            "cmp" | "partial_cmp" => {
                let o = self.val_cmp(&self.deref_val(&args[0]), &self.deref_val(&args[1]));
                let ord = self.ordering(o);
                if name == "cmp" {
                    Ok(ord)
                } else {
                    match o {
                        Some(_) => Ok(self.some(ord)),
                        None => Ok(self.none()),
                    }
                }
            }
            "default" => self.default_of(st, sp),
            "max" | "min" => {
                let o = self.val_cmp(&args[0], &args[1]).unwrap_or(std::cmp::Ordering::Equal);
                let first_wins = if name == "max" { o == std::cmp::Ordering::Greater } else { o != std::cmp::Ordering::Greater };
                Ok(if name == "max" { if o == std::cmp::Ordering::Greater { args[0].clone() } else { args[1].clone() } } else if first_wins { args[0].clone() } else { args[1].clone() })
            }
            "into" => Ok(args[0].clone()),
            "from" => Ok(args[0].clone()),
            _ => self.host(format!("no implementation of `{name}` for `{}`", self.c.program.ty_name(st))),
        }
    }

    fn default_of(&mut self, t: &Ty, sp: Span) -> R<V> {
        Ok(match t {
            Ty::Int(_) => V::Int(0),
            Ty::F32 => V::F32(0),
            Ty::F64 => V::F64(0),
            Ty::Bool => V::Bool(false),
            Ty::Unit => V::Unit,
            Ty::Tuple(v) => {
                let mut out = vec![];
                for x in v {
                    out.push(self.default_of(x, sp)?);
                }
                V::Tuple(out)
            }
            Ty::Array(e, n) => {
                let n = match **n {
                    Ty::Const(k) => k as usize,
                    _ => 0,
                };
                let d = self.default_of(e, sp)?;
                V::Arr(vec![d; n])
            }
            Ty::Adt(a, xs) => {
                let ad = &self.c.program.adts[*a as usize];
                match ad.lang.as_deref() {
                    Some("Vec") | Some("Buf") => V::Vec(vec![]),
                    Some("String") => V::String(String::new()),
                    Some("Option") => self.none(),
                    _ => {
                        if ad.kind == AdtKind::Struct {
                            let fields = ad.variants[0].fields.clone();
                            let mut out = vec![];
                            for f in fields {
                                out.push(self.default_of(&f.ty.subst(xs), sp)?);
                            }
                            V::Adt(*a, 0, out)
                        } else {
                            return self.host(format!("no Default for `{}`", ad.name));
                        }
                    }
                }
            }
            _ => return self.host("no Default for this type"),
        })
    }

    fn some(&self, v: V) -> V {
        V::Adt(self.c.program.lang_adt("Option"), 1, vec![v])
    }
    fn none(&self) -> V {
        V::Adt(self.c.program.lang_adt("Option"), 0, vec![])
    }
    fn ok(&self, v: V) -> V {
        V::Adt(self.c.program.lang_adt("Result"), 0, vec![v])
    }
    fn err_v(&self, v: V) -> V {
        V::Adt(self.c.program.lang_adt("Result"), 1, vec![v])
    }
    fn ordering(&self, o: Option<std::cmp::Ordering>) -> V {
        let a = self.c.program.lang_adt("Ordering");
        match o {
            Some(std::cmp::Ordering::Less) => V::Adt(a, 0, vec![]),
            Some(std::cmp::Ordering::Equal) | None => V::Adt(a, 1, vec![]),
            Some(std::cmp::Ordering::Greater) => V::Adt(a, 2, vec![]),
        }
    }
    fn ord_of(&self, v: &V) -> std::cmp::Ordering {
        match v {
            V::Adt(_, 0, _) => std::cmp::Ordering::Less,
            V::Adt(_, 1, _) => std::cmp::Ordering::Equal,
            _ => std::cmp::Ordering::Greater,
        }
    }

    // ------------------------------------------------------------ places
    fn read_ptr(&self, p: &Ptr) -> V {
        let b = p.cell.borrow();
        let mut cur: &V = &b;
        for &i in &p.path {
            cur = match cur {
                V::Tuple(v) | V::Arr(v) | V::Vec(v) | V::Adt(_, _, v) => match v.get(i) {
                    Some(x) => x,
                    None => return V::Moved,
                },
                _ => return V::Moved,
            };
        }
        cur.clone()
    }

    fn write_ptr(&self, p: &Ptr, val: V) {
        let mut b = p.cell.borrow_mut();
        let mut cur: &mut V = &mut b;
        for &i in &p.path {
            cur = match cur {
                V::Tuple(v) | V::Arr(v) | V::Vec(v) | V::Adt(_, _, v) => match v.get_mut(i) {
                    Some(x) => x,
                    None => return,
                },
                _ => return,
            };
        }
        *cur = val;
    }

    fn with_mut<T>(&self, p: &Ptr, f: impl FnOnce(&mut V) -> T) -> Option<T> {
        let mut b = p.cell.borrow_mut();
        let mut cur: &mut V = &mut b;
        for &i in &p.path {
            cur = match cur {
                V::Tuple(v) | V::Arr(v) | V::Vec(v) | V::Adt(_, _, v) => v.get_mut(i)?,
                _ => return None,
            };
        }
        Some(f(cur))
    }

    fn container_len(&self, p: &Ptr) -> usize {
        match self.read_ptr(p) {
            V::Arr(v) | V::Vec(v) => v.len(),
            V::String(s) => s.len(),
            _ => 0,
        }
    }

    fn local_cell(&mut self, l: LocalId) -> Cell {
        let fr = self.frames.last_mut().unwrap();
        if fr.locals[l as usize].is_none() {
            fr.locals[l as usize] = Some(new_cell(V::Moved));
        }
        fr.locals[l as usize].clone().unwrap()
    }

    fn place(&mut self, e: &TExpr) -> R<Place> {
        match &e.kind {
            TK::Local(l) => Ok(Place::P(Ptr { cell: self.local_cell(*l), path: vec![] })),
            TK::Deref(b) => {
                let v = self.eval(b)?;
                match v {
                    V::Ref(p) => Ok(Place::P(p)),
                    V::Slice(p, s, n) => Ok(Place::S(p, s, n)),
                    V::Str(s) => Ok(Place::P(Ptr { cell: new_cell(V::Str(s)), path: vec![] })),
                    other => Ok(Place::P(Ptr { cell: new_cell(other), path: vec![] })),
                }
            }
            TK::Field(b, i) => {
                let pb = self.place(b)?;
                match pb {
                    Place::P(mut p) => {
                        // a reference stored in a struct field is followed by Deref nodes
                        p.path.push(*i as usize);
                        Ok(Place::P(p))
                    }
                    Place::S(..) => self.host("field of a slice"),
                }
            }
            TK::Index(b, i) => {
                let idx = self.eval(i)?;
                let idx = match idx {
                    V::Int(k) => k,
                    _ => return self.host("non-integer index"),
                };
                let pb = self.place(b)?;
                match pb {
                    Place::P(mut p) => {
                        let len = self.container_len(&p);
                        if idx < 0 || idx as usize >= len {
                            return self.trap("idx", e.span, Some(format!("index {idx} out of bounds for length {len}")));
                        }
                        p.path.push(idx as usize);
                        Ok(Place::P(p))
                    }
                    Place::S(mut p, s, n) => {
                        if idx < 0 || idx as usize >= n {
                            return self.trap("idx", e.span, Some(format!("index {idx} out of bounds for length {n}")));
                        }
                        p.path.push(s + idx as usize);
                        Ok(Place::P(p))
                    }
                }
            }
            TK::SliceRange { base, lo, hi, inclusive } => {
                let lo_v = match lo {
                    Some(x) => self.eval_int(x)?,
                    None => 0,
                };
                let hi_v = match hi {
                    Some(x) => Some(self.eval_int(x)? + if *inclusive { 1 } else { 0 }),
                    None => None,
                };
                let pb = self.place(base)?;
                let (p, s0, n0) = match pb {
                    Place::P(p) => {
                        let n = self.container_len(&p);
                        (p, 0usize, n)
                    }
                    Place::S(p, s, n) => (p, s, n),
                };
                let hi_v = hi_v.unwrap_or(n0 as i128);
                if lo_v < 0 || lo_v > hi_v || hi_v as usize > n0 {
                    return self.trap("slice", e.span, Some(format!("range {lo_v}..{hi_v} out of bounds for length {n0}")));
                }
                Ok(Place::S(p, s0 + lo_v as usize, (hi_v - lo_v) as usize))
            }
            TK::Unsize(b) => self.place(b),
            _ => {
                // a temporary
                let v = self.eval(e)?;
                match v {
                    V::Slice(p, s, n) => Ok(Place::S(p, s, n)),
                    v => Ok(Place::P(Ptr { cell: new_cell(v), path: vec![] })),
                }
            }
        }
    }

    fn read_place(&self, p: &Place) -> V {
        match p {
            Place::P(p) => self.read_ptr(p),
            Place::S(p, s, n) => match self.read_ptr(p) {
                V::Arr(v) | V::Vec(v) => V::Arr(v[*s..*s + *n].to_vec()),
                other => other,
            },
        }
    }

    fn deref_val(&self, v: &V) -> V {
        match v {
            V::Ref(p) => self.read_ptr(p),
            V::Slice(p, s, n) => match self.read_ptr(p) {
                V::Arr(v) | V::Vec(v) => V::Arr(v[*s..(*s + *n).min(v.len())].to_vec()),
                other => other,
            },
            other => other.clone(),
        }
    }

    /// Elements of a slice-like value (a reference to an array, Vec or slice).
    fn slice_items(&self, v: &V) -> Vec<V> {
        match v {
            V::Ref(p) => match self.read_ptr(p) {
                V::Arr(v) | V::Vec(v) => v,
                V::Ref(_) | V::Slice(..) => self.slice_items(&self.read_ptr(p)),
                _ => vec![],
            },
            V::Slice(p, s, n) => match self.read_ptr(p) {
                V::Arr(v) | V::Vec(v) => v[*s..(*s + *n).min(v.len())].to_vec(),
                _ => vec![],
            },
            V::Arr(v) | V::Vec(v) => v.clone(),
            _ => vec![],
        }
    }

    fn slice_ptr(&self, v: &V) -> Option<(Ptr, usize, usize)> {
        match v {
            V::Slice(p, s, n) => Some((p.clone(), *s, *n)),
            V::Ref(p) => {
                let n = self.container_len(p);
                Some((p.clone(), 0, n))
            }
            _ => None,
        }
    }

    // ------------------------------------------------------------ expressions
    fn eval_int(&mut self, e: &TExpr) -> R<i128> {
        match self.eval(e)? {
            V::Int(k) => Ok(k),
            V::Bool(b) => Ok(b as i128),
            V::Char(c) => Ok(c as i128),
            _ => self.host("expected an integer"),
        }
    }

    fn eval_bool(&mut self, e: &TExpr) -> R<bool> {
        match self.eval(e)? {
            V::Bool(b) => Ok(b),
            _ => self.host("expected a bool"),
        }
    }

    pub fn eval(&mut self, e: &TExpr) -> R<V> {
        self.steps += 1;
        if self.steps > self.max_steps {
            return self.host("step limit reached (a divergent loop, or raise --max-steps)");
        }
        match &e.kind {
            TK::Lit(l) => Ok(match l {
                LitVal::Int(v) => match self.subst(&e.ty) {
                    Ty::F32 => V::F32((*v as f32).to_bits()),
                    Ty::F64 => V::F64((*v as f64).to_bits()),
                    _ => V::Int(*v),
                },
                LitVal::Float(bits) => match self.subst(&e.ty) {
                    Ty::F32 => V::F32(*bits as u32),
                    _ => V::F64(*bits),
                },
                LitVal::Bool(b) => V::Bool(*b),
                LitVal::Str(s) => V::Str(Rc::from(s.as_str())),
                LitVal::Char(c) => V::Char(*c),
                LitVal::Unit => V::Unit,
            }),
            TK::Const(cid) => {
                if let Some(v) = self.const_cache.get(cid) {
                    return Ok(v.clone());
                }
                let ce = self.c.const_vals.get(cid).cloned();
                match ce {
                    Some(ce) => {
                        let v = self.eval(&ce)?;
                        self.const_cache.insert(*cid, v.clone());
                        Ok(v)
                    }
                    None => self.host("constant without a value"),
                }
            }
            TK::Local(_) | TK::Field(..) | TK::Index(..) | TK::Deref(_) | TK::SliceRange { .. } => {
                let in_place = std::mem::replace(&mut self.in_place_call, false);
                let p = self.place(e)?;
                let v = self.read_place(&p);
                if let V::Moved = v {
                    return self.host("read of a moved or uninitialised value (the checker should have rejected this)");
                }
                // a closure read by value is a copy (or a move): its by-move state is its own
                // (K-CloCopy, F-104; review 2026-10-23: `let mut d = c; d(); c()` shared the
                // state, so c() returned 2 where rustc gives 1). A call of the closure in place
                // keeps its state (`c(); c()`)
                let v = if !in_place && ty_mentions_closure(&e.ty) { fresh_closures(&self.c.closures, v) } else { v };
                // a moved Linear local leaves Φ.lin (section 6.2, E-Move): mark it ⊠
                if let (TK::Local(l), Place::P(ptr)) = (&e.kind, &p) {
                    if ptr.path.is_empty() && self.frames.last().map(|f| f.linear.contains(l)).unwrap_or(false) {
                        *ptr.cell.borrow_mut() = V::Moved;
                    }
                }
                Ok(v)
            }
            TK::Borrow(_, p) => {
                let pl = self.place(p)?;
                Ok(match pl {
                    Place::P(ptr) => V::Ref(ptr),
                    Place::S(ptr, s, n) => V::Slice(ptr, s, n),
                })
            }
            TK::Unsize(b) => {
                let v = self.eval(b)?;
                Ok(match v {
                    V::Ref(p) => match self.read_ptr(&p) {
                        V::Arr(a) | V::Vec(a) => {
                            let n = a.len();
                            V::Slice(p, 0, n)
                        }
                        V::String(_) => V::Ref(p),
                        _ => V::Ref(p),
                    },
                    other => other,
                })
            }
            TK::Unary(op, a) => {
                let v = self.eval(a)?;
                self.unary(*op, v, &self.subst(&e.ty), e.span)
            }
            TK::Binary(op, a, b) => {
                if matches!(op, BinOp::And) {
                    if !self.eval_bool(a)? {
                        return Ok(V::Bool(false));
                    }
                    return Ok(V::Bool(self.eval_bool(b)?));
                }
                if matches!(op, BinOp::Or) {
                    if self.eval_bool(a)? {
                        return Ok(V::Bool(true));
                    }
                    return Ok(V::Bool(self.eval_bool(b)?));
                }
                let x = self.eval(a)?;
                let y = self.eval(b)?;
                let ty = self.subst(&a.ty);
                self.binary(*op, x, y, &ty, e.span)
            }
            TK::Cast(a) => {
                let v = self.eval(a)?;
                let to = self.subst(&e.ty);
                Ok(self.cast(v, &to))
            }
            TK::Assign(p, r) => {
                // the assigned value first, then the place (F-54)
                let v = self.eval(r)?;
                let pl = self.place(p)?;
                self.store(&pl, v, p, e.span)?;
                Ok(V::Unit)
            }
            TK::AssignOp(op, p, r) => {
                let rv = self.eval(r)?;
                let pl = self.place(p)?;
                let cur = self.read_place(&pl);
                let ty = self.subst(&p.ty);
                let nv = self.binary(*op, cur, rv, &ty, e.span)?;
                self.store(&pl, nv, p, e.span)?;
                Ok(V::Unit)
            }
            TK::Call { f, substs, args } => {
                let callee = self.c.program.fns[*f as usize].name.clone();
                let vs = self.eval_operands(args, &|k| format!("<arg {k} of {callee}>"))?;
                let targs: Vec<Ty> = substs.iter().map(|t| self.subst(t)).collect();
                self.check_param_ranges(*f, &vs, e.span)?;
                self.call(*f, targs, vs, e.span)
            }
            TK::TraitCall { tr, method, decl, self_ty, substs, args } => {
                let vs = self.eval_operands(args, &|k| format!("<arg {k} of {method}>"))?;
                let st = self.subst(self_ty);
                let targs: Vec<Ty> = substs.iter().map(|t| self.subst(t)).collect();
                // dispatch on the concrete Self (static dispatch after monomorphisation)
                let st = if matches!(st, Ty::Param(_) | Ty::Infer(_)) { self.runtime_ty(&vs) } else { st };
                if let Some(t) = crate::analysis::resolve_impl_method(self.c, *tr, &st, method) {
                    let mut ita = impl_targs(self.c, t, &st);
                    let own = targs.len().saturating_sub(self.c.program.fns[*decl as usize].n_parent);
                    ita.extend_from_slice(&targs[targs.len() - own..]);
                    return self.call(t, ita, vs, e.span);
                }
                let dfn = &self.c.program.fns[*decl as usize];
                if dfn.body.is_some() || dfn.builtin.is_some() {
                    let mut t2 = targs.clone();
                    if !t2.is_empty() {
                        t2[0] = st.clone();
                    }
                    return self.call(*decl, t2, vs, e.span);
                }
                self.derived(method, &st, vs, e.span)
            }
            TK::CallValue(f, args) => {
                // the callee is called in place (FnMut state persists across calls)
                self.in_place_call = f.is_place();
                let fv = self.eval(f);
                self.in_place_call = false;
                let fv = fv?;
                let vs = self.eval_operands(args, &|k| format!("<arg {k} of a closure call>"))?;
                self.call_value(fv, vs, e.span)
            }
            TK::Closure(cid) => {
                let cd = &self.c.closures[*cid as usize];
                let mut env = vec![];
                for cap in &cd.captures {
                    let cell = self.local_cell(cap.local);
                    match cap.mode {
                        CaptureMode::Ref | CaptureMode::Mut => env.push((cap.local, cell)),
                        CaptureMode::Move => {
                            let v = cell.borrow().clone();
                            env.push((cap.local, new_cell(v)));
                        }
                    }
                }
                let fr = self.frames.last().unwrap();
                Ok(V::Closure(Rc::new(CloV { id: *cid, env, nlocals: fr.locals.len(), targs: fr.targs.clone(), owner: fr.fid })))
            }
            TK::FnRef(f, s) => {
                let s2: Vec<Ty> = s.iter().map(|t| self.subst(t)).collect();
                Ok(V::FnRef(*f, s2))
            }
            TK::Ctor { adt, variant, fields } => {
                let an = self.c.program.adts[*adt as usize].name.clone();
                let vs = self.eval_operands(fields, &|k| format!("<field {k} of {an}>"))?;
                let v = V::Adt(*adt, *variant, vs);
                self.check_construction(*adt, &v, e)?;
                Ok(v)
            }
            TK::CtorUpdate { adt, variant, fields, base } => {
                let mut ups = vec![];
                for (i, f) in fields {
                    ups.push((*i as usize, self.eval(f)?));
                }
                let b = self.eval(base)?;
                let mut vs = match b {
                    V::Adt(_, _, vs) => vs,
                    _ => vec![],
                };
                for (i, v) in ups {
                    if i < vs.len() {
                        vs[i] = v;
                    }
                }
                let v = V::Adt(*adt, *variant, vs);
                self.check_construction(*adt, &v, e)?;
                Ok(v)
            }
            TK::Tuple(fs) => {
                let vs = self.eval_operands(fs, &|k| format!("<tuple element {k}>"))?;
                Ok(if vs.is_empty() { V::Unit } else { V::Tuple(vs) })
            }
            TK::Array(fs) => {
                let vs = self.eval_operands(fs, &|k| format!("<array element {k}>"))?;
                Ok(V::Arr(vs))
            }
            TK::Repeat(x, n) => {
                let v = self.eval(x)?;
                Ok(V::Arr(vec![v; *n as usize]))
            }
            TK::Block(stmts, tail) => {
                for s in stmts {
                    match s {
                        TStmt::Let { pat, init, els, .. } => match init {
                            Some(i) => {
                                let v = self.eval(i)?;
                                if !self.bind(pat, v.clone())? {
                                    match els {
                                        Some(el) => {
                                            self.eval(el)?;
                                            return self.host("let-else fell through");
                                        }
                                        None => return self.host("refutable pattern in let"),
                                    }
                                }
                            }
                            None => {
                                let mut bs = vec![];
                                pat.bindings(&mut bs);
                                for b in bs {
                                    let c = new_cell(V::Moved);
                                    self.frames.last_mut().unwrap().locals[b as usize] = Some(c);
                                }
                            }
                        },
                        TStmt::Expr(x) => {
                            self.eval(x)?;
                        }
                    }
                }
                match tail {
                    Some(t) => self.eval(t),
                    None => Ok(V::Unit),
                }
            }
            TK::If(c, t, el) => {
                if self.eval_bool(c)? {
                    self.eval(t)
                } else {
                    match el {
                        Some(x) => self.eval(x),
                        None => Ok(V::Unit),
                    }
                }
            }
            TK::Match(s, arms) => {
                let sv = self.eval(s)?;
                for a in arms {
                    if self.bind(&a.pat, sv.clone())? {
                        if let Some(g) = &a.guard {
                            if !self.eval_bool(g)? {
                                continue;
                            }
                        }
                        return self.eval(&a.body);
                    }
                }
                self.trap("unreachable", e.span, Some("no match arm matched".into()))
            }
            TK::Loop(id, b) => loop {
                match self.eval(b) {
                    Ok(_) => {}
                    Err(Ctrl::Break(l, v)) if l == *id => return Ok(v),
                    Err(Ctrl::Continue(l)) if l == *id => {}
                    Err(x) => return Err(x),
                }
            },
            TK::While(id, c, b) => {
                loop {
                    if !self.eval_bool(c)? {
                        break;
                    }
                    match self.eval(b) {
                        Ok(_) => {}
                        Err(Ctrl::Break(l, _)) if l == *id => break,
                        Err(Ctrl::Continue(l)) if l == *id => {}
                        Err(x) => return Err(x),
                    }
                }
                Ok(V::Unit)
            }
            TK::For { id, pat, iter, body, range, par } => {
                // `par for` runs its serial projection (section 6.4)
                if let Some((lo, hi, incl)) = range {
                    let a = self.eval_int(lo)?;
                    let b = self.eval_int(hi)? + if *incl { 1 } else { 0 };
                    let mut i = a;
                    while i < b {
                        self.bind(pat, V::Int(i))?;
                        match self.eval(body) {
                            Ok(_) => {}
                            Err(Ctrl::Break(l, _)) if l == *id => break,
                            Err(Ctrl::Continue(l)) if l == *id => {}
                            Err(Ctrl::Trap(mut t)) if *par => {
                                // the lowest failing index wins; the report names it
                                let var = pat.is_irrefutable_bind().and_then(|l| self.frames.last().and_then(|f| self.c.bodies.get(&f.fid)).and_then(|b| b.locals.get(l as usize)).map(|d| d.name.clone())).unwrap_or_else(|| "_".into());
                                t.par_index.push(format!("{var}={i}"));
                                return Err(Ctrl::Trap(t));
                            }
                            Err(x) => return Err(x),
                        }
                        i += 1;
                    }
                    return Ok(V::Unit);
                }
                let iv = self.eval(iter)?;
                let it = self.to_iter(iv, &self.subst(&iter.ty))?;
                loop {
                    let next = self.iter_next(&it)?;
                    let Some(x) = next else { break };
                    self.bind(pat, x)?;
                    match self.eval(body) {
                        Ok(_) => {}
                        Err(Ctrl::Break(l, _)) if l == *id => break,
                        Err(Ctrl::Continue(l)) if l == *id => {}
                        Err(x) => return Err(x),
                    }
                }
                Ok(V::Unit)
            }
            TK::Break(id, v) => {
                let val = match v {
                    Some(x) => self.eval(x)?,
                    None => V::Unit,
                };
                Err(Ctrl::Break(*id, val))
            }
            TK::Continue(id) => Err(Ctrl::Continue(*id)),
            TK::Return(v) => {
                let val = match v {
                    Some(x) => self.eval(x)?,
                    None => V::Unit,
                };
                Err(Ctrl::Return(val))
            }
            TK::Try { e: inner, is_option, from } => {
                let v = self.eval(inner)?;
                match v {
                    V::Adt(_, var, mut fs) => {
                        if *is_option {
                            if var == 1 {
                                Ok(fs.remove(0))
                            } else {
                                Err(Ctrl::Return(self.none()))
                            }
                        } else if var == 0 {
                            Ok(fs.remove(0))
                        } else {
                            let ev = fs.remove(0);
                            let ev = match from {
                                Some((f, s)) => {
                                    let s2: Vec<Ty> = s.iter().map(|t| self.subst(t)).collect();
                                    self.call(*f, s2, vec![ev], e.span)?
                                }
                                None => ev,
                            };
                            Err(Ctrl::Return(self.err_v(ev)))
                        }
                    }
                    _ => self.host("`?` on a non-enum value"),
                }
            }
            TK::Det { body, .. } => self.eval(body),
            TK::Trap(kind, msg) => {
                let k = match kind {
                    TrapKind::Hole(n) => format!("hole({n})"),
                    TrapKind::Panic => "panic".into(),
                    TrapKind::Unreachable => "unreachable".into(),
                    TrapKind::Unwrap => "unwrap".into(),
                    TrapKind::Expect => "expect".into(),
                    TrapKind::Assert => "assert".into(),
                    TrapKind::Elided => "hole(…)".into(),
                };
                self.trap(&k, e.span, msg.clone())
            }
            TK::Assert { cond, msg } => {
                if self.eval_bool(cond)? {
                    Ok(V::Unit)
                } else {
                    self.trap("assert", e.span, msg.clone())
                }
            }
            TK::AssertCmp { eq, a, b } => {
                let x = self.eval(a)?;
                let y = self.eval(b)?;
                let same = self.val_eq(&self.deref_val(&x), &self.deref_val(&y));
                if same == *eq {
                    Ok(V::Unit)
                } else {
                    let m = format!("left: {}, right: {}", self.debug(&x), self.debug(&y));
                    self.trap("assert", e.span, Some(m))
                }
            }
            TK::Format { pieces, args } => {
                let mut vs = vec![];
                let mut bits = vec![];
                for a in args {
                    vs.push(self.eval(a)?);
                    // integer width, for `{:x}` / `{:b}` / `{:o}` of negative values
                    let t = self.subst(&a.ty);
                    bits.push(match t.strip_refs() {
                        Ty::Int(it) => it.bits(),
                        _ => 128,
                    });
                }
                Ok(V::String(self.format_typed(pieces, &vs, &bits)))
            }
            TK::Matches(s, p) => {
                let v = self.eval(s)?;
                Ok(V::Bool(self.bind(p, v)?))
            }
            TK::LetCond(p, s) => {
                let v = self.eval(s)?;
                Ok(V::Bool(self.bind(p, v)?))
            }
            TK::Error => self.host("an ill-typed expression (the checker rejected this program)"),
        }
    }

    fn runtime_ty(&self, vs: &[V]) -> Ty {
        match vs.first().map(|v| self.deref_val(v)) {
            Some(V::Adt(a, _, _)) => Ty::Adt(a, vec![]),
            Some(V::F32(_)) => Ty::F32,
            Some(V::F64(_)) => Ty::F64,
            Some(V::Bool(_)) => Ty::Bool,
            _ => Ty::Error,
        }
    }

    fn store(&mut self, pl: &Place, v: V, target: &TExpr, sp: Span) -> R<()> {
        // #[range] fields are checked on every direct write (note section 5.10)
        if let TK::Field(b, i) = &target.kind {
            if let Ty::Adt(a, _) = self.subst(&b.ty).strip_refs() {
                let ad = &self.c.program.adts[*a as usize];
                if let Some(f) = ad.variants.first().and_then(|vv| vv.fields.get(*i as usize)) {
                    if let (Some((lo, hi)), V::Int(k)) = (f.range, &v) {
                        if *k < lo || *k > hi {
                            return self.trap("range", sp, Some(format!("{k} is outside #[range({lo}..={hi})]")));
                        }
                    }
                }
            }
        }
        match pl {
            Place::P(p) => {
                if p.path.is_empty() {
                    *p.cell.borrow_mut() = v;
                } else {
                    self.write_ptr(p, v);
                }
            }
            Place::S(p, s, n) => {
                if let V::Arr(items) = v {
                    for (k, it) in items.into_iter().enumerate().take(*n) {
                        let mut q = p.clone();
                        q.path.push(s + k);
                        self.write_ptr(&q, it);
                    }
                }
            }
        }
        Ok(())
    }

    fn check_construction(&mut self, adt: AdtId, v: &V, e: &TExpr) -> R<()> {
        let ad = &self.c.program.adts[adt as usize];
        // ranges at construction
        if let V::Adt(_, var, fs) = v {
            if let Some(vd) = ad.variants.get(*var as usize) {
                for (i, f) in vd.fields.iter().enumerate() {
                    if let Some((lo, hi)) = f.range {
                        let bad = match fs.get(i) {
                            Some(V::Int(k)) => *k < lo || *k > hi,
                            Some(V::Arr(items)) => items.iter().any(|x| matches!(x, V::Int(k) if *k < lo || *k > hi)),
                            _ => false,
                        };
                        if bad {
                            return self.trap("range", e.span, Some(format!("field `{}` outside #[range({lo}..={hi})]", f.name)));
                        }
                    }
                }
            }
        }
        // the invariant at construction
        if let Some(inv) = ad.invariant {
            let name = ad.name.clone();
            let targs = match self.subst(&e.ty) {
                Ty::Adt(_, xs) => xs,
                _ => vec![],
            };
            let r = self.call(inv, targs, vec![V::Ref(Ptr { cell: new_cell(v.clone()), path: vec![] })], e.span)?;
            if let V::Bool(false) = r {
                return self.trap(&format!("inv({name})"), e.span, None);
            }
        }
        Ok(())
    }

    fn check_param_ranges(&mut self, f: FnId, vs: &[V], sp: Span) -> R<()> {
        let fd = &self.c.program.fns[f as usize];
        for (i, p) in fd.params.iter().enumerate() {
            if let (Some((lo, hi)), Some(V::Int(k))) = (p.range, vs.get(i)) {
                if *k < lo || *k > hi {
                    return self.trap("range", sp, Some(format!("argument `{}` = {k} outside #[range({lo}..={hi})]", p.name)));
                }
            }
            // invariants of structs passed by reference (publication points, F-43): checked when the
            // referent's invariant fails at the call boundary
            if let (Ty::Ref(_, inner), Some(V::Ref(ptr))) = (&p.ty, vs.get(i)) {
                if let Ty::Adt(a, _) = &**inner {
                    if let Some(inv) = self.c.program.adts[*a as usize].invariant {
                        if fd.role != crate::diag::FileRole::Std {
                            let v = self.read_ptr(ptr);
                            if let V::Adt(..) = v {
                                let name = self.c.program.adts[*a as usize].name.clone();
                                let r = self.call(inv, vec![], vec![V::Ref(ptr.clone())], sp)?;
                                if let V::Bool(false) = r {
                                    return self.trap(&format!("inv({name})"), sp, Some("invariant broken at a publication point (F-43)".into()));
                                }
                            }
                        }
                    }
                }
            }
        }
        Ok(())
    }

    fn call_value(&mut self, fv: V, args: Vec<V>, sp: Span) -> R<V> {
        match fv {
            V::Closure(cl) => {
                let cd = &self.c.closures[cl.id as usize];
                let mut fr = Frame { fid: cl.owner, locals: vec![None; cl.nlocals], targs: cl.targs.clone(), linear: vec![] };
                for (l, c) in &cl.env {
                    fr.locals[*l as usize] = Some(c.clone());
                }
                self.frames.push(fr);
                for (i, p) in cd.params.iter().enumerate() {
                    let v = args.get(i).cloned().unwrap_or(V::Unit);
                    if let Err(e) = self.bind(p, v) {
                        self.frames.pop();
                        return Err(e);
                    }
                }
                self.depth += 1;
                let r = match self.eval(&cd.body) {
                    Ok(v) => Ok(v),
                    Err(Ctrl::Return(v)) => Ok(v),
                    Err(e) => Err(e),
                };
                self.depth -= 1;
                self.frames.pop();
                r
            }
            V::Ref(p) => {
                let inner = self.read_ptr(&p);
                self.call_value(inner, args, sp)
            }
            V::FnRef(f, s) => self.call(f, s, args, sp),
            V::Ctor(a, v) => Ok(V::Adt(a, v, args)),
            _ => self.host("call of a non-callable value"),
        }
    }

    // ------------------------------------------------------------ patterns
    fn bind(&mut self, p: &TPat, v: V) -> R<bool> {
        match &p.kind {
            PK::Wild => Ok(true),
            PK::Bind { local, by_ref, sub } => {
                if let Some(s) = sub {
                    if !self.bind(s, v.clone())? {
                        return Ok(false);
                    }
                }
                let val = match by_ref {
                    Some(_) => match v {
                        // default binding mode: a reference to the matched part
                        V::Ref(_) | V::Slice(..) => v,
                        other => V::Ref(Ptr { cell: new_cell(other), path: vec![] }),
                    },
                    None => v,
                };
                let cell = new_cell(val);
                let fid = self.frames.last().unwrap().fid;
                let lin = self.c.bodies.get(&fid).and_then(|b| b.locals.get(*local as usize)).map(|d| crate::analysis::wf::is_linear(self.c, &d.ty)).unwrap_or(false);
                let fr = self.frames.last_mut().unwrap();
                fr.locals[*local as usize] = Some(cell);
                if lin && !fr.linear.contains(local) {
                    fr.linear.push(*local);
                }
                Ok(true)
            }
            PK::Lit(l) => {
                let lv = match l {
                    LitVal::Int(k) => V::Int(*k),
                    LitVal::Bool(b) => V::Bool(*b),
                    LitVal::Char(c) => V::Char(*c),
                    LitVal::Str(s) => V::Str(Rc::from(s.as_str())),
                    LitVal::Float(b) => V::F64(*b),
                    LitVal::Unit => V::Unit,
                };
                Ok(self.val_eq(&self.deref_val(&v), &lv))
            }
            PK::Range(lo, hi) => {
                let k = match self.deref_val(&v) {
                    V::Int(k) => k,
                    V::Char(c) => c as i128,
                    _ => return Ok(false),
                };
                Ok(k >= *lo && k <= *hi)
            }
            PK::Tuple(ps) => {
                let items = match self.deref_val(&v) {
                    V::Tuple(items) => items,
                    V::Unit => vec![],
                    _ => return Ok(false),
                };
                for (i, sp) in ps.iter().enumerate() {
                    let item = match &v {
                        V::Ref(ptr) => {
                            let mut q = ptr.clone();
                            q.path.push(i);
                            V::Ref(q)
                        }
                        _ => items.get(i).cloned().unwrap_or(V::Unit),
                    };
                    let item = if matches!(v, V::Ref(_)) && !matches!(sp.kind, PK::Bind { by_ref: Some(_), .. } | PK::Deref(_)) && !matches!(sp.ty, Ty::Ref(..)) { self.deref_val(&item) } else { item };
                    if !self.bind(sp, item)? {
                        return Ok(false);
                    }
                }
                Ok(true)
            }
            PK::Variant { adt, variant, fields } => {
                let dv = self.deref_val(&v);
                let (a, var, items) = match dv {
                    V::Adt(a, var, items) => (a, var, items),
                    V::Hint(h) => (self.c.program.lang_adt("Option"), if h.is_some() { 1 } else { 0 }, h.map(|x| vec![*x]).unwrap_or_default()),
                    _ => return Ok(false),
                };
                if a != *adt || var != *variant {
                    return Ok(false);
                }
                for (fi, sp) in fields {
                    let item = match &v {
                        V::Ref(ptr) => {
                            let mut q = ptr.clone();
                            q.path.push(*fi as usize);
                            let r = V::Ref(q);
                            if matches!(sp.kind, PK::Bind { by_ref: Some(_), .. }) {
                                r
                            } else {
                                self.deref_val(&r)
                            }
                        }
                        _ => items.get(*fi as usize).cloned().unwrap_or(V::Unit),
                    };
                    if !self.bind(sp, item)? {
                        return Ok(false);
                    }
                }
                Ok(true)
            }
            PK::Deref(inner) => {
                // matching through a reference: bindings inside get references to the parts
                match &v {
                    V::Ref(_) | V::Slice(..) => self.bind_through_ref(inner, v.clone()),
                    _ => self.bind(inner, v),
                }
            }
            PK::Or(ps) => {
                for x in ps {
                    if self.bind(x, v.clone())? {
                        return Ok(true);
                    }
                }
                Ok(false)
            }
            PK::Slice(ps, rest) => {
                let items = self.slice_items(&v);
                let items = if items.is_empty() {
                    match self.deref_val(&v) {
                        V::Arr(x) | V::Vec(x) => x,
                        _ => vec![],
                    }
                } else {
                    items
                };
                match rest {
                    None if items.len() != ps.len() => return Ok(false),
                    Some(_) if items.len() < ps.len() => return Ok(false),
                    _ => {}
                }
                let r = rest.unwrap_or(ps.len());
                for (i, sp) in ps.iter().enumerate() {
                    let idx = if i < r { i } else { items.len() - (ps.len() - i) };
                    if !self.bind(sp, items[idx].clone())? {
                        return Ok(false);
                    }
                }
                Ok(true)
            }
        }
    }

    fn bind_through_ref(&mut self, p: &TPat, r: V) -> R<bool> {
        match &p.kind {
            PK::Bind { local, by_ref: Some(_), sub: None } => {
                let cell = new_cell(r);
                self.frames.last_mut().unwrap().locals[*local as usize] = Some(cell);
                Ok(true)
            }
            PK::Bind { by_ref: None, .. } => {
                let v = self.deref_val(&r);
                self.bind(p, v)
            }
            _ => self.bind(p, r),
        }
    }

    // ------------------------------------------------------------ arithmetic
    fn wrap_int(v: i128, t: IntTy) -> i128 {
        let bits = t.bits();
        if bits >= 128 {
            return v;
        }
        let m = 1i128 << bits;
        let mut x = v.rem_euclid(m);
        if t.signed() && x >= m / 2 {
            x -= m;
        }
        x
    }

    fn unary(&self, op: UnOp, v: V, ty: &Ty, sp: Span) -> R<V> {
        match (op, v) {
            (UnOp::Neg, V::Int(k)) => {
                let it = int_ty(ty).unwrap_or(IntTy::I64);
                let r = -k;
                if r < it.min_val() || r > it.max_val() {
                    return self.trap("ovf(neg)", sp, None);
                }
                Ok(V::Int(r))
            }
            (UnOp::Neg, V::F32(b)) => Ok(V::F32((-f32::from_bits(b)).to_bits())),
            (UnOp::Neg, V::F64(b)) => Ok(V::F64((-f64::from_bits(b)).to_bits())),
            (UnOp::Not, V::Bool(b)) => Ok(V::Bool(!b)),
            (UnOp::Not, V::Int(k)) => {
                let it = int_ty(ty).unwrap_or(IntTy::I64);
                Ok(V::Int(Self::wrap_int(!k, it)))
            }
            (UnOp::Deref, v) => Ok(self.deref_val(&v)),
            _ => self.host("bad unary operand"),
        }
    }

    fn binary(&self, op: BinOp, x: V, y: V, ty: &Ty, sp: Span) -> R<V> {
        use BinOp::*;
        let x = match x {
            V::Ref(_) | V::Slice(..) if op.is_cmp() => self.deref_val(&x),
            other => other,
        };
        let y = match y {
            V::Ref(_) | V::Slice(..) if op.is_cmp() => self.deref_val(&y),
            other => other,
        };
        if op.is_cmp() {
            let r = match op {
                Eq => self.val_eq(&x, &y),
                Ne => !self.val_eq(&x, &y),
                _ => {
                    let o = self.val_cmp(&x, &y);
                    match (op, o) {
                        (_, None) => false,
                        (Lt, Some(o)) => o == std::cmp::Ordering::Less,
                        (Le, Some(o)) => o != std::cmp::Ordering::Greater,
                        (Gt, Some(o)) => o == std::cmp::Ordering::Greater,
                        (Ge, Some(o)) => o != std::cmp::Ordering::Less,
                        _ => false,
                    }
                }
            };
            return Ok(V::Bool(r));
        }
        match (x, y) {
            (V::Int(a), V::Int(b)) => {
                let it = int_ty(ty).unwrap_or(IntTy::I64);
                let checked = |r: Option<i128>, kind: &str| -> R<V> {
                    match r {
                        Some(v) if v >= it.min_val() && v <= it.max_val() => Ok(V::Int(v)),
                        _ => self.trap(kind, sp, None),
                    }
                };
                match op {
                    Add => checked(a.checked_add(b), "ovf(add)"),
                    Sub => checked(a.checked_sub(b), "ovf(sub)"),
                    Mul => checked(a.checked_mul(b), "ovf(mul)"),
                    Div | Rem => {
                        if b == 0 {
                            return self.trap("div0", sp, None);
                        }
                        if it.signed() && a == it.min_val() && b == -1 {
                            return self.trap("divovf", sp, None);
                        }
                        Ok(V::Int(if op == Div { a / b } else { a % b }))
                    }
                    BitAnd => Ok(V::Int(a & b)),
                    BitOr => Ok(V::Int(a | b)),
                    BitXor => Ok(V::Int(Self::wrap_int(a ^ b, it))),
                    Shl | Shr => {
                        if b < 0 || b >= it.bits() as i128 {
                            return self.trap("shift", sp, None);
                        }
                        let r = if op == Shl { Self::wrap_int(a.wrapping_shl(b as u32), it) } else { a >> b };
                        Ok(V::Int(r))
                    }
                    _ => self.host("bad integer operator"),
                }
            }
            (V::F32(a), V::F32(b)) => {
                let (a, b) = (f32::from_bits(a), f32::from_bits(b));
                // IEEE binary32, round to nearest even, never contracted (FF-FMA)
                let r = match op {
                    Add => a + b,
                    Sub => a - b,
                    Mul => a * b,
                    Div => a / b,
                    Rem => a % b,
                    _ => return self.host("bad float operator"),
                };
                Ok(V::F32(r.to_bits()))
            }
            (V::F64(a), V::F64(b)) => {
                let (a, b) = (f64::from_bits(a), f64::from_bits(b));
                let r = match op {
                    Add => a + b,
                    Sub => a - b,
                    Mul => a * b,
                    Div => a / b,
                    Rem => a % b,
                    _ => return self.host("bad float operator"),
                };
                Ok(V::F64(r.to_bits()))
            }
            (V::Bool(a), V::Bool(b)) => Ok(V::Bool(match op {
                BitAnd => a & b,
                BitOr => a | b,
                BitXor => a ^ b,
                _ => return self.host("bad bool operator"),
            })),
            _ => self.host("bad operands"),
        }
    }

    fn cast(&self, v: V, to: &Ty) -> V {
        match (v, to) {
            (V::Int(k), Ty::Int(it)) => V::Int(Self::wrap_int(k, *it)),
            (V::Int(k), Ty::F32) => V::F32((k as f32).to_bits()),
            (V::Int(k), Ty::F64) => V::F64((k as f64).to_bits()),
            (V::Int(k), Ty::Char) => V::Char(char::from_u32(k as u32).unwrap_or('\u{FFFD}')),
            (V::Bool(b), Ty::Int(_)) => V::Int(b as i128),
            (V::Char(c), Ty::Int(it)) => V::Int(Self::wrap_int(c as i128, *it)),
            (V::F32(b), Ty::Int(it)) => V::Int(float_to_int(f32::from_bits(b) as f64, *it)),
            (V::F64(b), Ty::Int(it)) => V::Int(float_to_int(f64::from_bits(b), *it)),
            (V::F32(b), Ty::F64) => V::F64((f32::from_bits(b) as f64).to_bits()),
            (V::F64(b), Ty::F32) => V::F32((f64::from_bits(b) as f32).to_bits()),
            (V::Adt(_, var, _), Ty::Int(_)) => V::Int(var as i128),
            (v, _) => v,
        }
    }

    pub fn val_eq(&self, a: &V, b: &V) -> bool {
        match (a, b) {
            (V::Int(x), V::Int(y)) => x == y,
            (V::F32(x), V::F32(y)) => f32::from_bits(*x) == f32::from_bits(*y),
            (V::F64(x), V::F64(y)) => f64::from_bits(*x) == f64::from_bits(*y),
            (V::Bool(x), V::Bool(y)) => x == y,
            (V::Char(x), V::Char(y)) => x == y,
            (V::Unit, V::Unit) => true,
            (V::Str(x), V::Str(y)) => x == y,
            (V::String(x), V::String(y)) => x == y,
            (V::String(x), V::Str(y)) | (V::Str(y), V::String(x)) => x.as_str() == &**y,
            (V::Tuple(x), V::Tuple(y)) | (V::Arr(x), V::Arr(y)) | (V::Vec(x), V::Vec(y)) | (V::Arr(x), V::Vec(y)) | (V::Vec(x), V::Arr(y)) => x.len() == y.len() && x.iter().zip(y).all(|(p, q)| self.val_eq(p, q)),
            (V::Adt(a1, v1, x), V::Adt(a2, v2, y)) => a1 == a2 && v1 == v2 && x.iter().zip(y).all(|(p, q)| self.val_eq(p, q)),
            (V::Ref(_), _) | (V::Slice(..), _) => self.val_eq(&self.deref_val(a), b),
            (_, V::Ref(_)) | (_, V::Slice(..)) => self.val_eq(a, &self.deref_val(b)),
            (V::Hint(x), V::Hint(y)) => match (x, y) {
                (None, None) => true,
                (Some(p), Some(q)) => self.val_eq(p, q),
                _ => false,
            },
            _ => false,
        }
    }

    pub fn val_cmp(&self, a: &V, b: &V) -> Option<std::cmp::Ordering> {
        use std::cmp::Ordering;
        match (a, b) {
            (V::Int(x), V::Int(y)) => Some(x.cmp(y)),
            (V::F32(x), V::F32(y)) => f32::from_bits(*x).partial_cmp(&f32::from_bits(*y)),
            (V::F64(x), V::F64(y)) => f64::from_bits(*x).partial_cmp(&f64::from_bits(*y)),
            (V::Bool(x), V::Bool(y)) => Some(x.cmp(y)),
            (V::Char(x), V::Char(y)) => Some(x.cmp(y)),
            (V::Str(x), V::Str(y)) => Some(x.cmp(y)),
            (V::String(x), V::String(y)) => Some(x.cmp(y)),
            (V::Unit, V::Unit) => Some(Ordering::Equal),
            (V::Tuple(x), V::Tuple(y)) | (V::Arr(x), V::Arr(y)) | (V::Vec(x), V::Vec(y)) => {
                for (p, q) in x.iter().zip(y) {
                    match self.val_cmp(p, q)? {
                        Ordering::Equal => continue,
                        o => return Some(o),
                    }
                }
                Some(x.len().cmp(&y.len()))
            }
            (V::Adt(a1, v1, x), V::Adt(a2, v2, y)) if a1 == a2 => {
                if v1 != v2 {
                    return Some(v1.cmp(v2));
                }
                // std::cmp::Reverse reverses Ord
                let rev = self.c.program.adts[*a1 as usize].lang.as_deref() == Some("Reverse");
                for (p, q) in x.iter().zip(y) {
                    match self.val_cmp(p, q)? {
                        Ordering::Equal => continue,
                        o => return Some(if rev { o.reverse() } else { o }),
                    }
                }
                Some(Ordering::Equal)
            }
            (V::Ref(_), _) | (V::Slice(..), _) => self.val_cmp(&self.deref_val(a), b),
            (_, V::Ref(_)) | (_, V::Slice(..)) => self.val_cmp(a, &self.deref_val(b)),
            _ => None,
        }
    }

    // ------------------------------------------------------------ formatting
    pub fn display(&self, v: &V) -> String {
        match v {
            V::Int(k) => k.to_string(),
            V::F32(b) => format!("{}", f32::from_bits(*b)),
            V::F64(b) => format!("{}", f64::from_bits(*b)),
            V::Bool(b) => b.to_string(),
            V::Char(c) => c.to_string(),
            V::Str(s) => s.to_string(),
            V::String(s) => s.clone(),
            V::Ref(_) | V::Slice(..) => self.display(&self.deref_val(v)),
            other => self.debug(other),
        }
    }

    pub fn debug(&self, v: &V) -> String {
        match v {
            V::Unit => "()".into(),
            V::Int(k) => k.to_string(),
            V::F32(b) => format!("{:?}", f32::from_bits(*b)),
            V::F64(b) => format!("{:?}", f64::from_bits(*b)),
            V::F16(b) => format!("f16({:#06x})", b),
            V::Bf16(b) => format!("bf16({:#06x})", b),
            V::Bool(b) => b.to_string(),
            V::Char(c) => format!("{c:?}"),
            V::Str(s) => format!("{:?}", &**s),
            V::String(s) => format!("{s:?}"),
            V::Tuple(v) => format!("({})", v.iter().map(|x| self.debug(x)).collect::<Vec<_>>().join(", ")),
            V::Arr(v) | V::Vec(v) => format!("[{}]", v.iter().map(|x| self.debug(x)).collect::<Vec<_>>().join(", ")),
            V::Adt(a, var, fs) => {
                let ad = &self.c.program.adts[*a as usize];
                let vd = &ad.variants[*var as usize];
                let name = &vd.name;
                if fs.is_empty() {
                    name.clone()
                } else if vd.tuple || vd.fields.iter().all(|f| f.name.parse::<u32>().is_ok()) {
                    format!("{name}({})", fs.iter().map(|x| self.debug(x)).collect::<Vec<_>>().join(", "))
                } else {
                    format!("{name} {{ {} }}", vd.fields.iter().zip(fs).map(|(f, x)| format!("{}: {}", f.name, self.debug(x))).collect::<Vec<_>>().join(", "))
                }
            }
            V::Ref(_) | V::Slice(..) => self.debug(&self.deref_val(v)),
            V::Hint(h) => match h {
                Some(x) => format!("Hint::some({})", self.debug(x)),
                None => "Hint::none()".into(),
            },
            V::Closure(_) => "<closure>".into(),
            V::Iter(_) => "<iterator>".into(),
            V::Mutex(c, _) => format!("Mutex({})", self.debug(&c.borrow())),
            V::FnRef(..) | V::Ctor(..) => "<fn>".into(),
            V::Moved => "<moved>".into(),
            V::Opaque(n) => format!("<{n}>"),
        }
    }

    /// `format!` with Rust's placeholder grammar (src/fmtspec.rs): positional arguments, fill and
    /// alignment, sign, `#`, zero padding, width and precision (literal, `N$` or `.*`), and the
    /// Display, Debug (`#?` pretty), radix and exponent formats.
    fn format_typed(&self, pieces: &[String], vs: &[V], bits: &[u32]) -> String {
        let mut out = String::new();
        let mut implicit = 0usize;
        for p in pieces {
            let Some(inner) = p.strip_prefix('\u{0}') else {
                out.push_str(p);
                continue;
            };
            let spec = match crate::fmtspec::parse_placeholder(inner, &mut implicit) {
                Ok(x) => x,
                Err(_) => continue, // the checker rejected it
            };
            let count = |c: Option<crate::fmtspec::Count>| -> Option<usize> {
                match c {
                    Some(crate::fmtspec::Count::Lit(n)) => Some(n),
                    Some(crate::fmtspec::Count::Arg(k)) => match vs.get(k).map(|v| self.deref_val(v)) {
                        Some(V::Int(n)) => Some(n.max(0) as usize),
                        _ => None,
                    },
                    None => None,
                }
            };
            let width = count(spec.width);
            let prec = count(spec.precision);
            let v = self.deref_val(&vs.get(spec.arg).cloned().unwrap_or(V::Unit));
            let numeric = matches!(v, V::Int(_) | V::F32(_) | V::F64(_));
            let mut core = match spec.ty.as_str() {
                "x" | "X" | "o" | "b" => match v {
                    V::Int(i) => {
                        // two's complement in the type's width for negatives (Rust)
                        let w = bits.get(spec.arg).copied().unwrap_or(128);
                        let u = (i as u128) & if w >= 128 { u128::MAX } else { (1u128 << w) - 1 };
                        let (body, pre) = match spec.ty.as_str() {
                            "x" => (format!("{u:x}"), "0x"),
                            "X" => (format!("{u:X}"), "0x"),
                            "b" => (format!("{u:b}"), "0b"),
                            _ => (format!("{u:o}"), "0o"),
                        };
                        if spec.alt {
                            format!("{pre}{body}")
                        } else {
                            body
                        }
                    }
                    _ => self.display(&v),
                },
                "e" | "E" => {
                    let t = match (&v, prec) {
                        (V::F32(b), Some(pr)) => format!("{:.*e}", pr, f32::from_bits(*b)),
                        (V::F32(b), None) => format!("{:e}", f32::from_bits(*b)),
                        (V::F64(b), Some(pr)) => format!("{:.*e}", pr, f64::from_bits(*b)),
                        (V::F64(b), None) => format!("{:e}", f64::from_bits(*b)),
                        (V::Int(i), Some(pr)) => format!("{:.*e}", pr, *i),
                        (V::Int(i), None) => format!("{:e}", *i),
                        _ => self.display(&v),
                    };
                    if spec.ty == "E" {
                        t.replace('e', "E")
                    } else {
                        t
                    }
                }
                "?" | "x?" | "X?" => match (&v, prec) {
                    (V::F32(b), Some(pr)) => format!("{:.*?}", pr, f32::from_bits(*b)),
                    (V::F64(b), Some(pr)) => format!("{:.*?}", pr, f64::from_bits(*b)),
                    (V::Int(i), _) if spec.ty == "x?" => format!("{:x}", *i),
                    (V::Int(i), _) if spec.ty == "X?" => format!("{:X}", *i),
                    _ => {
                        if spec.alt {
                            self.debug_pretty(&v, 0)
                        } else {
                            self.debug(&v)
                        }
                    }
                },
                _ => match (&v, prec) {
                    (V::F32(b), Some(pr)) => format!("{:.*}", pr, f32::from_bits(*b)),
                    (V::F64(b), Some(pr)) => format!("{:.*}", pr, f64::from_bits(*b)),
                    // a precision truncates strings (Rust); integers ignore it
                    (V::Str(_) | V::String(_), Some(pr)) => self.display(&v).chars().take(pr).collect(),
                    _ => self.display(&v),
                },
            };
            // `+`: a sign on non-negative numbers (NaN has none)
            if spec.plus && numeric && !core.starts_with('-') && !core.contains("NaN") {
                core = format!("+{core}");
            }
            out.push_str(&crate::fmtspec::pad(core, &spec, width, numeric));
        }
        out
    }

    /// `{:#?}`: Rust's pretty Debug (one field or element per line, four spaces per level).
    fn debug_pretty(&self, v: &V, ind: usize) -> String {
        let pad = " ".repeat(ind + 4);
        let close = " ".repeat(ind);
        let list = |open: &str, items: Vec<String>, end: &str| -> String {
            if items.is_empty() {
                return format!("{open}{end}");
            }
            let mut s = format!("{open}\n");
            for it in items {
                s.push_str(&format!("{pad}{it},\n"));
            }
            s.push_str(&format!("{close}{end}"));
            s
        };
        match v {
            V::Tuple(xs) => list("(", xs.iter().map(|x| self.debug_pretty(x, ind + 4)).collect(), ")"),
            V::Arr(xs) | V::Vec(xs) => list("[", xs.iter().map(|x| self.debug_pretty(x, ind + 4)).collect(), "]"),
            V::Adt(a, var, fs) if !fs.is_empty() => {
                let ad = &self.c.program.adts[*a as usize];
                let vd = &ad.variants[*var as usize];
                let name = &vd.name;
                if vd.tuple || vd.fields.iter().all(|f| f.name.parse::<u32>().is_ok()) {
                    list(&format!("{name}("), fs.iter().map(|x| self.debug_pretty(x, ind + 4)).collect(), ")")
                } else {
                    list(&format!("{name} {{"), vd.fields.iter().zip(fs).map(|(f, x)| format!("{}: {}", f.name, self.debug_pretty(x, ind + 4))).collect(), "}")
                }
            }
            V::Ref(_) | V::Slice(..) => self.debug_pretty(&self.deref_val(v), ind),
            _ => self.debug(v),
        }
    }

    // ------------------------------------------------------------ iterators
    fn to_iter(&mut self, v: V, ty: &Ty) -> R<Rc<RefCell<It>>> {
        Ok(Rc::new(RefCell::new(self.make_it(v, ty)?)))
    }

    fn make_it(&mut self, v: V, ty: &Ty) -> R<It> {
        match v {
            V::Iter(it) => Ok(It::Shared(it)),
            V::Adt(a, _, fs) if matches!(self.c.program.adts[a as usize].lang.as_deref(), Some("Range") | Some("RangeInclusive")) => {
                let incl = self.c.program.adts[a as usize].lang.as_deref() == Some("RangeInclusive");
                let (s, e) = match (&fs[0], &fs[1]) {
                    (V::Int(s), V::Int(e)) => (*s, *e),
                    _ => (0, 0),
                };
                Ok(It::Range { cur: s, end: if incl { e + 1 } else { e } })
            }
            V::Ref(p) => {
                // &mut I where I: Iterator
                let inner = self.read_ptr(&p);
                match inner {
                    V::Iter(it) => Ok(It::Shared(it)),
                    _ => {
                        let inner_ty = ty.deref_ty().cloned().unwrap_or(Ty::Error);
                        self.user_iter(p.cell.clone(), &inner_ty)
                    }
                }
            }
            V::Adt(..) => {
                let cell = new_cell(v);
                self.user_iter(cell, ty)
            }
            V::Vec(items) | V::Arr(items) => Ok(It::Items(items.into())),
            _ => self.host("not an iterator"),
        }
    }

    fn user_iter(&mut self, cell: Cell, ty: &Ty) -> R<It> {
        let tr = self.c.program.lang_trait("Iterator");
        let st = match ty {
            Ty::Adt(..) => ty.clone(),
            _ => match &*cell.borrow() {
                V::Adt(a, _, _) => Ty::Adt(*a, vec![]),
                _ => Ty::Error,
            },
        };
        match crate::analysis::resolve_impl_method(self.c, tr, &st, "next") {
            Some(f) => {
                let targs = impl_targs(self.c, f, &st);
                Ok(It::User(cell, f, targs))
            }
            None => self.host("no Iterator impl for this value"),
        }
    }

    fn iter_next(&mut self, it: &Rc<RefCell<It>>) -> R<Option<V>> {
        // take the state out to avoid holding the borrow across closure calls
        let mut st = std::mem::replace(&mut *it.borrow_mut(), It::Items(Default::default()));
        let r = self.it_next(&mut st);
        *it.borrow_mut() = st;
        r
    }

    fn it_next(&mut self, st: &mut It) -> R<Option<V>> {
        match st {
            It::Range { cur, end } => {
                if *cur < *end {
                    let v = *cur;
                    *cur += 1;
                    Ok(Some(V::Int(v)))
                } else {
                    Ok(None)
                }
            }
            It::Items(q) => Ok(q.pop_front()),
            It::Map(inner, f) => match self.it_next(inner)? {
                Some(x) => {
                    let f = f.clone();
                    Ok(Some(self.call_value(f, vec![x], Span::DUMMY)?))
                }
                None => Ok(None),
            },
            It::Filter(inner, f) => loop {
                match self.it_next(inner)? {
                    Some(x) => {
                        let f = f.clone();
                        let r = self.call_value(f, vec![V::Ref(Ptr { cell: new_cell(x.clone()), path: vec![] })], Span::DUMMY)?;
                        if let V::Bool(true) = r {
                            return Ok(Some(x));
                        }
                    }
                    None => return Ok(None),
                }
            },
            It::FilterMap(inner, f) => loop {
                match self.it_next(inner)? {
                    Some(x) => {
                        let f = f.clone();
                        if let V::Adt(_, 1, mut fs) = self.call_value(f, vec![x], Span::DUMMY)? {
                            return Ok(Some(fs.remove(0)));
                        }
                    }
                    None => return Ok(None),
                }
            },
            It::Enumerate(inner, k) => match self.it_next(inner)? {
                Some(x) => {
                    let i = *k;
                    *k += 1;
                    Ok(Some(V::Tuple(vec![V::Int(i as i128), x])))
                }
                None => Ok(None),
            },
            It::Zip(a, b) => {
                let x = self.it_next(a)?;
                let Some(x) = x else { return Ok(None) };
                let y = self.it_next(b)?;
                let Some(y) = y else { return Ok(None) };
                Ok(Some(V::Tuple(vec![x, y])))
            }
            It::Take(inner, n) => {
                if *n == 0 {
                    return Ok(None);
                }
                *n -= 1;
                self.it_next(inner)
            }
            It::Skip(inner, n) => {
                while *n > 0 {
                    *n -= 1;
                    if self.it_next(inner)?.is_none() {
                        return Ok(None);
                    }
                }
                self.it_next(inner)
            }
            It::StepBy(inner, n, first) => {
                if *first {
                    *first = false;
                    return self.it_next(inner);
                }
                for _ in 0..(*n - 1) {
                    if self.it_next(inner)?.is_none() {
                        return Ok(None);
                    }
                }
                self.it_next(inner)
            }
            It::Chain(a, b) => match self.it_next(a)? {
                Some(x) => Ok(Some(x)),
                None => self.it_next(b),
            },
            It::Copied(inner) => Ok(self.it_next(inner)?.map(|x| self.deref_val(&x))),
            It::User(cell, f, targs) => {
                let r = self.call(*f, targs.clone(), vec![V::Ref(Ptr { cell: cell.clone(), path: vec![] })], Span::DUMMY)?;
                match r {
                    V::Adt(_, 1, mut fs) => Ok(Some(fs.remove(0))),
                    _ => Ok(None),
                }
            }
            It::Shared(rc) => {
                let rc = rc.clone();
                self.iter_next(&rc)
            }
        }
    }

    fn collect_all(&mut self, it: It) -> R<Vec<V>> {
        let mut st = it;
        let mut out = vec![];
        while let Some(x) = self.it_next(&mut st)? {
            out.push(x);
            if out.len() > 50_000_000 {
                return self.host("iterator too long");
            }
        }
        Ok(out)
    }

    // ------------------------------------------------------------ builtins
    #[allow(clippy::too_many_lines)]
    fn builtin(&mut self, name: &str, fid: FnId, targs: &[Ty], args: Vec<V>, sp: Span) -> R<V> {
        let arg = |i: usize| -> V { args.get(i).cloned().unwrap_or(V::Unit) };
        let int = |v: &V| -> i128 {
            match v {
                V::Int(k) => *k,
                _ => 0,
            }
        };
        let f32v = |v: &V| -> f32 {
            match v {
                V::F32(b) => f32::from_bits(*b),
                V::Ref(_) => 0.0,
                _ => 0.0,
            }
        };
        let self_int_ty = || -> IntTy {
            match targs.first() {
                Some(Ty::Int(i)) => *i,
                _ => IntTy::I64,
            }
        };
        match name {
            // ---- slices
            "slice_len" => {
                let (_, _, n) = self.slice_ptr(&arg(0)).unwrap_or((Ptr { cell: new_cell(V::Unit), path: vec![] }, 0, 0));
                Ok(V::Int(n as i128))
            }
            "slice_is_empty" => Ok(V::Bool(self.slice_ptr(&arg(0)).map(|x| x.2 == 0).unwrap_or(true))),
            "slice_iter" | "slice_iter_mut" => {
                let (p, s, n) = self.slice_ptr(&arg(0)).ok_or_else(|| Ctrl::Host("iter on a non-slice".into()))?;
                let items: std::collections::VecDeque<V> = (0..n)
                    .map(|k| {
                        let mut q = p.clone();
                        q.path.push(s + k);
                        V::Ref(q)
                    })
                    .collect();
                Ok(V::Iter(Rc::new(RefCell::new(It::Items(items)))))
            }
            "slice_first" | "slice_last" | "slice_get" | "slice_get_mut" => {
                let (p, s, n) = self.slice_ptr(&arg(0)).ok_or_else(|| Ctrl::Host("not a slice".into()))?;
                let k = match name {
                    "slice_first" => 0i128,
                    "slice_last" => n as i128 - 1,
                    _ => int(&arg(1)),
                };
                if k < 0 || k as usize >= n {
                    return Ok(self.none());
                }
                let mut q = p;
                q.path.push(s + k as usize);
                Ok(self.some(V::Ref(q)))
            }
            "slice_contains" => {
                let items = self.slice_items(&arg(0));
                let x = self.deref_val(&arg(1));
                Ok(V::Bool(items.iter().any(|y| self.val_eq(y, &x))))
            }
            "slice_swap" | "slice_reverse" | "slice_fill" | "slice_copy_from_slice" | "slice_sort" | "slice_sort_by" | "slice_sort_by_key" => {
                let (p, s, n) = self.slice_ptr(&arg(0)).ok_or_else(|| Ctrl::Host("not a slice".into()))?;
                let mut items = self.slice_items(&arg(0));
                match name {
                    "slice_swap" => {
                        let (a, b) = (int(&arg(1)), int(&arg(2)));
                        if a < 0 || b < 0 || a as usize >= n || b as usize >= n {
                            return self.trap("idx", sp, Some("swap index out of bounds".into()));
                        }
                        items.swap(a as usize, b as usize);
                    }
                    "slice_reverse" => items.reverse(),
                    "slice_fill" => {
                        for x in items.iter_mut() {
                            *x = arg(1);
                        }
                    }
                    "slice_copy_from_slice" => {
                        let src = self.slice_items(&arg(1));
                        if src.len() != n {
                            return self.trap("panic", sp, Some("copy_from_slice: lengths differ".into()));
                        }
                        items = src;
                    }
                    "slice_sort" => {
                        let mut err = false;
                        // stable merge sort through val_cmp
                        items = self.stable_sort(items, &mut |me, a, b| Ok(me.val_cmp(a, b).unwrap_or_else(|| {
                            err = true;
                            std::cmp::Ordering::Equal
                        })))?;
                    }
                    "slice_sort_by" => {
                        let f = arg(1);
                        items = self.stable_sort(items, &mut |me, a, b| {
                            let r = me.call_value(f.clone(), vec![V::Ref(Ptr { cell: new_cell(a.clone()), path: vec![] }), V::Ref(Ptr { cell: new_cell(b.clone()), path: vec![] })], sp)?;
                            Ok(me.ord_of(&r))
                        })?;
                    }
                    _ => {
                        let f = arg(1);
                        items = self.stable_sort(items, &mut |me, a, b| {
                            let ka = me.call_value(f.clone(), vec![V::Ref(Ptr { cell: new_cell(a.clone()), path: vec![] })], sp)?;
                            let kb = me.call_value(f.clone(), vec![V::Ref(Ptr { cell: new_cell(b.clone()), path: vec![] })], sp)?;
                            Ok(me.val_cmp(&ka, &kb).unwrap_or(std::cmp::Ordering::Equal))
                        })?;
                    }
                }
                for (k, it) in items.into_iter().enumerate() {
                    let mut q = p.clone();
                    q.path.push(s + k);
                    self.write_ptr(&q, it);
                }
                Ok(V::Unit)
            }
            "slice_to_vec" => Ok(V::Vec(self.slice_items(&arg(0)).iter().map(|x| self.deref_val(x)).collect())),
            "slice_split_at" | "slice_split_at_mut" => {
                let (p, s, n) = self.slice_ptr(&arg(0)).ok_or_else(|| Ctrl::Host("not a slice".into()))?;
                let m = int(&arg(1));
                if m < 0 || m as usize > n {
                    return self.trap("panic", sp, Some("split_at out of bounds".into()));
                }
                Ok(V::Tuple(vec![V::Slice(p.clone(), s, m as usize), V::Slice(p, s + m as usize, n - m as usize)]))
            }
            "slice_windows" => {
                let (p, s, n) = self.slice_ptr(&arg(0)).ok_or_else(|| Ctrl::Host("not a slice".into()))?;
                let k = int(&arg(1)) as usize;
                if k == 0 {
                    return self.trap("panic", sp, Some("window size must be non-zero".into()));
                }
                let mut q = std::collections::VecDeque::new();
                let mut i = 0;
                while i + k <= n {
                    q.push_back(V::Slice(p.clone(), s + i, k));
                    i += 1;
                }
                Ok(V::Iter(Rc::new(RefCell::new(It::Items(q)))))
            }
            "vec_retain" => {
                let V::Ref(p) = arg(0) else { return self.host("retain without a receiver") };
                let V::Vec(items) = self.read_ptr(&p) else { return self.host("retain on a non-Vec") };
                let mut kept = vec![];
                for x in items {
                    let r = self.call_value(arg(1), vec![V::Ref(Ptr { cell: new_cell(x.clone()), path: vec![] })], sp)?;
                    if let V::Bool(true) = r {
                        kept.push(x);
                    }
                }
                self.with_mut(&p, |v| *v = V::Vec(kept));
                Ok(V::Unit)
            }
            "vec_swap_remove" => {
                let V::Ref(p) = arg(0) else { return self.host("swap_remove without a receiver") };
                let i = int(&arg(1));
                let r = self.with_mut(&p, |v| match v {
                    V::Vec(items) if i >= 0 && (i as usize) < items.len() => Some(items.swap_remove(i as usize)),
                    _ => None,
                });
                match r.flatten() {
                    Some(x) => Ok(x),
                    None => self.trap("idx", sp, Some("swap_remove index out of bounds".into())),
                }
            }
            "slice_chunks" => {
                let (p, s, n) = self.slice_ptr(&arg(0)).ok_or_else(|| Ctrl::Host("not a slice".into()))?;
                let k = int(&arg(1)) as usize;
                if k == 0 {
                    return self.trap("panic", sp, Some("chunk size must be non-zero".into()));
                }
                let mut q = std::collections::VecDeque::new();
                let mut i = 0;
                while i < n {
                    let len = k.min(n - i);
                    q.push_back(V::Slice(p.clone(), s + i, len));
                    i += k;
                }
                Ok(V::Iter(Rc::new(RefCell::new(It::Items(q)))))
            }
            // ---- Vec / Buf / String
            "vec_new" => Ok(V::Vec(vec![])),
            "vec_with_capacity" => Ok(V::Vec(vec![])),
            "vec_from_array" => Ok(V::Vec(match arg(0) {
                V::Arr(v) => v,
                _ => vec![],
            })),
            "vec_repeat" => {
                let n = int(&arg(1));
                if n < 0 {
                    return self.trap("panic", sp, None);
                }
                Ok(V::Vec(vec![arg(0); n as usize]))
            }
            "buf_from_vec" => Ok(arg(0)),
            "vec_push" | "vec_pop" | "vec_clear" | "vec_truncate" | "vec_insert" | "vec_remove" | "vec_extend_from_slice" | "vec_resize" => {
                let V::Ref(p) = arg(0) else { return self.host("vec method without a receiver") };
                let extra = if name == "vec_extend_from_slice" { self.slice_items(&arg(1)).iter().map(|x| self.deref_val(x)).collect() } else { vec![] };
                let a1 = arg(1);
                let a2 = arg(2);
                let none = self.none();
                let opt = self.c.program.lang_adt("Option");
                let res: Option<Result<V, String>> = self.with_mut(&p, |v| {
                    let V::Vec(items) = v else { return Err("not a Vec".to_string()) };
                    Ok(match name {
                        "vec_push" => {
                            items.push(a1);
                            V::Unit
                        }
                        "vec_pop" => match items.pop() {
                            Some(x) => V::Adt(opt, 1, vec![x]),
                            None => none,
                        },
                        "vec_clear" => {
                            items.clear();
                            V::Unit
                        }
                        "vec_truncate" => {
                            items.truncate(int(&a1).max(0) as usize);
                            V::Unit
                        }
                        "vec_insert" => {
                            let i = int(&a1);
                            if i < 0 || i as usize > items.len() {
                                return Err("trap:idx".into());
                            }
                            items.insert(i as usize, a2);
                            V::Unit
                        }
                        "vec_remove" => {
                            let i = int(&a1);
                            if i < 0 || i as usize >= items.len() {
                                return Err("trap:idx".into());
                            }
                            items.remove(i as usize)
                        }
                        "vec_extend_from_slice" => {
                            items.extend(extra);
                            V::Unit
                        }
                        _ => {
                            let n = int(&a1).max(0) as usize;
                            items.resize(n, a2);
                            V::Unit
                        }
                    })
                });
                match res {
                    Some(Ok(v)) => Ok(v),
                    Some(Err(e)) if e.starts_with("trap:") => self.trap(&e[5..], sp, None),
                    Some(Err(e)) => self.host(e),
                    None => self.host("bad Vec receiver"),
                }
            }
            "vec_as_slice" | "vec_as_mut_slice" => match arg(0) {
                V::Ref(p) => {
                    let n = self.container_len(&p);
                    Ok(V::Slice(p, 0, n))
                }
                v => Ok(v),
            },
            "vec_into_iter" => match arg(0) {
                V::Vec(v) => Ok(V::Iter(Rc::new(RefCell::new(It::Items(v.into()))))),
                _ => self.host("into_iter on a non-Vec"),
            },
            "string_new" => Ok(V::String(String::new())),
            "string_len" | "str_len" => Ok(V::Int(match self.deref_val(&arg(0)) {
                V::String(s) => s.len() as i128,
                V::Str(s) => s.len() as i128,
                _ => 0,
            })),
            "string_push_str" => {
                let add = self.display(&arg(1));
                if let V::Ref(p) = arg(0) {
                    self.with_mut(&p, |v| {
                        if let V::String(s) = v {
                            s.push_str(&add);
                        }
                    });
                }
                Ok(V::Unit)
            }
            "string_as_str" => Ok(V::Str(Rc::from(self.display(&arg(0)).as_str()))),
            "str_to_string" => Ok(V::String(self.display(&arg(0)))),
            "str_bytes" => Ok(V::Iter(Rc::new(RefCell::new(It::Items(self.display(&arg(0)).bytes().map(|b| V::Int(b as i128)).collect()))))),
            "string_write_fmt" => {
                let add = self.display(&arg(1));
                if let V::Ref(p) = arg(0) {
                    self.with_mut(&p, |v| {
                        if let V::String(s) = v {
                            s.push_str(&add);
                        }
                    });
                }
                Ok(self.ok(V::Unit))
            }
            // ---- Option / Result
            "opt_is_some" | "opt_is_none" => {
                let v = self.deref_val(&arg(0));
                let some = matches!(v, V::Adt(_, 1, _));
                Ok(V::Bool(if name == "opt_is_some" { some } else { !some }))
            }
            "opt_unwrap" | "opt_expect" => match arg(0) {
                V::Adt(_, 1, mut fs) => Ok(fs.remove(0)),
                _ => self.trap(if name == "opt_unwrap" { "unwrap" } else { "expect" }, sp, Some("called on None".into())),
            },
            "opt_unwrap_or" => match arg(0) {
                V::Adt(_, 1, mut fs) => Ok(fs.remove(0)),
                _ => Ok(arg(1)),
            },
            "opt_map" => match arg(0) {
                V::Adt(_, 1, mut fs) => {
                    let x = fs.remove(0);
                    let r = self.call_value(arg(1), vec![x], sp)?;
                    Ok(self.some(r))
                }
                _ => Ok(self.none()),
            },
            "opt_and_then" => match arg(0) {
                V::Adt(_, 1, mut fs) => {
                    let x = fs.remove(0);
                    self.call_value(arg(1), vec![x], sp)
                }
                _ => Ok(self.none()),
            },
            "opt_unwrap_or_else" => match arg(0) {
                V::Adt(_, 1, mut fs) => Ok(fs.remove(0)),
                _ => self.call_value(arg(1), vec![], sp),
            },
            "opt_map_or" => match arg(0) {
                V::Adt(_, 1, mut fs) => {
                    let x = fs.remove(0);
                    self.call_value(arg(2), vec![x], sp)
                }
                _ => Ok(arg(1)),
            },
            "opt_ok_or_else" => match arg(0) {
                V::Adt(_, 1, mut fs) => Ok(self.ok(fs.remove(0))),
                _ => {
                    let e = self.call_value(arg(1), vec![], sp)?;
                    Ok(self.err_v(e))
                }
            },
            "opt_ok_or" => match arg(0) {
                V::Adt(_, 1, mut fs) => Ok(self.ok(fs.remove(0))),
                _ => Ok(self.err_v(arg(1))),
            },
            "opt_take" => {
                let V::Ref(p) = arg(0) else { return self.host("take without a place") };
                let old = self.read_ptr(&p);
                let n = self.none();
                self.write_ptr_or_cell(&p, n);
                Ok(old)
            }
            "opt_as_ref" | "opt_as_mut" => match arg(0) {
                V::Ref(p) => match self.read_ptr(&p) {
                    V::Adt(_, 1, _) => {
                        let mut q = p;
                        q.path.push(0);
                        Ok(self.some(V::Ref(q)))
                    }
                    _ => Ok(self.none()),
                },
                _ => Ok(self.none()),
            },
            "res_is_ok" | "res_is_err" => {
                let v = self.deref_val(&arg(0));
                let ok = matches!(v, V::Adt(_, 0, _));
                Ok(V::Bool(if name == "res_is_ok" { ok } else { !ok }))
            }
            "res_unwrap" | "res_expect" => match arg(0) {
                V::Adt(_, 0, mut fs) => Ok(fs.remove(0)),
                V::Adt(_, _, fs) => {
                    let m = fs.first().map(|x| self.debug(x));
                    self.trap(if name == "res_unwrap" { "unwrap" } else { "expect" }, sp, m)
                }
                _ => self.host("unwrap on a non-Result"),
            },
            "res_ok" => match arg(0) {
                V::Adt(_, 0, mut fs) => Ok(self.some(fs.remove(0))),
                _ => Ok(self.none()),
            },
            "res_unwrap_or_else" => match arg(0) {
                V::Adt(_, 0, mut fs) => Ok(fs.remove(0)),
                V::Adt(_, _, mut fs) => {
                    let e = fs.remove(0);
                    self.call_value(arg(1), vec![e], sp)
                }
                _ => self.host("unwrap_or_else on a non-Result"),
            },
            "res_unwrap_or" => match arg(0) {
                V::Adt(_, 0, mut fs) => Ok(fs.remove(0)),
                _ => Ok(arg(1)),
            },
            "res_map_err" => match arg(0) {
                V::Adt(_, 1, mut fs) => {
                    let x = fs.remove(0);
                    let r = self.call_value(arg(1), vec![x], sp)?;
                    Ok(self.err_v(r))
                }
                v => Ok(v),
            },
            // ---- integers
            "int_checked_add" | "int_checked_sub" | "int_checked_mul" | "int_checked_div" => {
                let it = self_int_ty();
                let (a, b) = (int(&arg(0)), int(&arg(1)));
                let r = match name {
                    "int_checked_add" => a.checked_add(b),
                    "int_checked_sub" => a.checked_sub(b),
                    "int_checked_mul" => a.checked_mul(b),
                    _ => {
                        if b == 0 || (it.signed() && a == it.min_val() && b == -1) {
                            None
                        } else {
                            Some(a / b)
                        }
                    }
                };
                Ok(match r {
                    Some(v) if v >= it.min_val() && v <= it.max_val() => self.some(V::Int(v)),
                    _ => self.none(),
                })
            }
            "int_wrapping_add" | "int_wrapping_sub" | "int_wrapping_mul" => {
                let it = self_int_ty();
                let (a, b) = (int(&arg(0)), int(&arg(1)));
                let r = match name {
                    "int_wrapping_add" => a.wrapping_add(b),
                    "int_wrapping_sub" => a.wrapping_sub(b),
                    _ => a.wrapping_mul(b),
                };
                Ok(V::Int(Self::wrap_int(r, it)))
            }
            "int_saturating_add" | "int_saturating_sub" | "int_saturating_mul" => {
                let it = self_int_ty();
                let (a, b) = (int(&arg(0)), int(&arg(1)));
                let r = match name {
                    "int_saturating_add" => a.saturating_add(b),
                    "int_saturating_sub" => a.saturating_sub(b),
                    _ => a.saturating_mul(b),
                };
                Ok(V::Int(r.clamp(it.min_val(), it.max_val())))
            }
            "int_min" => Ok(V::Int(int(&arg(0)).min(int(&arg(1))))),
            "int_max" => Ok(V::Int(int(&arg(0)).max(int(&arg(1))))),
            "int_abs" => {
                let it = self_int_ty();
                let a = int(&arg(0));
                if it.signed() && a == it.min_val() {
                    return self.trap("ovf(abs)", sp, None);
                }
                Ok(V::Int(a.abs()))
            }
            "int_pow" => {
                let it = self_int_ty();
                let (a, e) = (int(&arg(0)), int(&arg(1)));
                let mut r: i128 = 1;
                for _ in 0..e {
                    r = match r.checked_mul(a) {
                        Some(x) if x >= it.min_val() && x <= it.max_val() => x,
                        _ => return self.trap("ovf(mul)", sp, None),
                    };
                }
                Ok(V::Int(r))
            }
            "int_is_power_of_two" => {
                let a = int(&arg(0));
                Ok(V::Bool(a > 0 && (a & (a - 1)) == 0))
            }
            "int_count_ones" | "int_leading_zeros" | "int_trailing_zeros" => {
                let it = self_int_ty();
                let bits = it.bits();
                let a = int(&arg(0));
                let u = (a as u128) & if bits == 128 { u128::MAX } else { (1u128 << bits) - 1 };
                Ok(V::Int(match name {
                    "int_count_ones" => u.count_ones() as i128,
                    "int_leading_zeros" => (u.leading_zeros() - (128 - bits)) as i128,
                    _ => {
                        if u == 0 {
                            bits as i128
                        } else {
                            u.trailing_zeros() as i128
                        }
                    }
                }))
            }
            "u16_from_le_bytes" | "u32_from_le_bytes" | "u64_from_le_bytes" => {
                let items = match arg(0) {
                    V::Arr(v) => v,
                    _ => vec![],
                };
                let mut r: i128 = 0;
                for (i, b) in items.iter().enumerate() {
                    r |= int(b) << (8 * i);
                }
                Ok(V::Int(r))
            }
            "u16_to_le_bytes" | "u32_to_le_bytes" | "u64_to_le_bytes" => {
                let n = match name {
                    "u16_to_le_bytes" => 2,
                    "u32_to_le_bytes" => 4,
                    _ => 8,
                };
                let a = int(&arg(0));
                Ok(V::Arr((0..n).map(|i| V::Int((a >> (8 * i)) & 0xff)).collect()))
            }
            // ---- floats
            "f32_to_bits" => Ok(V::Int(match arg(0) {
                V::F32(b) => b as i128,
                _ => 0,
            })),
            "f32_from_bits" => Ok(V::F32(int(&arg(0)) as u32)),
            "f64_to_bits" => Ok(V::Int(match arg(0) {
                V::F64(b) => b as i128,
                _ => 0,
            })),
            "f64_from_bits" => Ok(V::F64(int(&arg(0)) as u64)),
            "f32_is_nan" => Ok(V::Bool(f32v(&arg(0)).is_nan())),
            "f32_is_finite" => Ok(V::Bool(f32v(&arg(0)).is_finite())),
            "f32_is_infinite" => Ok(V::Bool(f32v(&arg(0)).is_infinite())),
            "f32_is_sign_negative" => Ok(V::Bool(f32v(&arg(0)).is_sign_negative())),
            "f32_is_sign_positive" => Ok(V::Bool(f32v(&arg(0)).is_sign_positive())),
            "f32_abs" => Ok(V::F32(f32v(&arg(0)).abs().to_bits())),
            "f32_sqrt" => Ok(V::F32(f32v(&arg(0)).sqrt().to_bits())),
            "f32_max" | "f32_min" => {
                // FF-NANMAX pinned: max(±0, ∓0) = +0.0, min(±0, ∓0) = −0.0; a NaN operand gives the
                // other operand; two NaNs give the canonical NaN 0x7fc00000 (01 section 2.5)
                let (a, b) = (f32v(&arg(0)), f32v(&arg(1)));
                let r = if a.is_nan() && b.is_nan() {
                    f32::from_bits(0x7fc0_0000)
                } else if a.is_nan() {
                    b
                } else if b.is_nan() {
                    a
                } else if a == 0.0 && b == 0.0 {
                    if name == "f32_max" {
                        if a.is_sign_positive() || b.is_sign_positive() { 0.0 } else { -0.0 }
                    } else if a.is_sign_negative() || b.is_sign_negative() {
                        -0.0
                    } else {
                        0.0
                    }
                } else if name == "f32_max" {
                    if a > b { a } else { b }
                } else if a < b {
                    a
                } else {
                    b
                };
                Ok(V::F32(r.to_bits()))
            }
            "f32_mul_add" => Ok(V::F32(f32v(&arg(0)).mul_add(f32v(&arg(1)), f32v(&arg(2))).to_bits())),
            "f32_round" => Ok(V::F32(f32v(&arg(0)).round().to_bits())),
            "f32_round_ties_even" => Ok(V::F32(f32v(&arg(0)).round_ties_even().to_bits())),
            "f32_floor" => Ok(V::F32(f32v(&arg(0)).floor().to_bits())),
            "f32_ceil" => Ok(V::F32(f32v(&arg(0)).ceil().to_bits())),
            "f32_trunc" => Ok(V::F32(f32v(&arg(0)).trunc().to_bits())),
            "f32_recip" => Ok(V::F32((1.0f32 / f32v(&arg(0))).to_bits())),
            "f32_copysign" => Ok(V::F32(f32v(&arg(0)).copysign(f32v(&arg(1))).to_bits())),
            "f32_clamp" => {
                let (x, lo, hi) = (f32v(&arg(0)), f32v(&arg(1)), f32v(&arg(2)));
                if !(lo <= hi) {
                    return self.trap("panic", sp, Some("clamp: min > max or NaN".into()));
                }
                Ok(V::F32(x.clamp(lo, hi).to_bits()))
            }
            "f32_total_cmp" => {
                let (a, b) = (f32v(&self.deref_val(&arg(0))), f32v(&self.deref_val(&arg(1))));
                Ok(self.ordering(Some(a.total_cmp(&b))))
            }
            "f32_partial_cmp" => {
                let (a, b) = (f32v(&self.deref_val(&arg(0))), f32v(&self.deref_val(&arg(1))));
                Ok(match a.partial_cmp(&b) {
                    Some(o) => {
                        let ov = self.ordering(Some(o));
                        self.some(ov)
                    }
                    None => self.none(),
                })
            }
            "f64_is_nan" | "f64_is_finite" | "f64_abs" | "f64_sqrt" | "f64_max" | "f64_min" | "f64_round" | "f64_floor" | "f64_total_cmp" | "f64_partial_cmp" => {
                let g = |v: &V| -> f64 {
                    match v {
                        V::F64(b) => f64::from_bits(*b),
                        _ => 0.0,
                    }
                };
                let a = g(&self.deref_val(&arg(0)));
                let b = g(&self.deref_val(&arg(1)));
                Ok(match name {
                    "f64_is_nan" => V::Bool(a.is_nan()),
                    "f64_is_finite" => V::Bool(a.is_finite()),
                    "f64_abs" => V::F64(a.abs().to_bits()),
                    "f64_sqrt" => V::F64(a.sqrt().to_bits()),
                    "f64_max" => V::F64(a.max(b).to_bits()),
                    "f64_min" => V::F64(a.min(b).to_bits()),
                    "f64_round" => V::F64(a.round().to_bits()),
                    "f64_floor" => V::F64(a.floor().to_bits()),
                    "f64_total_cmp" => self.ordering(Some(a.total_cmp(&b))),
                    _ => match a.partial_cmp(&b) {
                        Some(o) => {
                            let ov = self.ordering(Some(o));
                            self.some(ov)
                        }
                        None => self.none(),
                    },
                })
            }
            "f32_exp" | "f32_ln" | "f32_sin" | "f32_cos" | "f32_tanh" | "f32_powf" | "f32_powi" | "f64_exp" | "canon_v1_expf" | "cr_expf" | "cr_sinf" | "cr_cosf" => self.host(format!(
                "`{}` is typed but not executed by mithi v0: its bits are fixed by cr:: (correct rounding) or canon_v1:: (an op-DAG pending Hearth ADR-0010 and D0-2), which mithi does not implement yet",
                self.c.program.fns[fid as usize].path
            )),
            "f16_to_f32" => Ok(V::F32(match arg(0) {
                V::F16(h) => f16_to_f32(h),
                _ => 0.0,
            }
            .to_bits())),
            "f16_from_bits" => Ok(V::F16(int(&arg(0)) as u16)),
            "f16_to_bits" => Ok(V::Int(match arg(0) {
                V::F16(h) => h as i128,
                _ => 0,
            })),
            "bf16_to_f32" => Ok(V::F32(match arg(0) {
                V::Bf16(h) => (h as u32) << 16,
                _ => 0,
            })),
            "bf16_from_bits" => Ok(V::Bf16(int(&arg(0)) as u16)),
            "bf16_to_bits" => Ok(V::Int(match arg(0) {
                V::Bf16(h) => h as i128,
                _ => 0,
            })),
            // ---- canon.v1
            "canon_nan" => {
                let x = f32v(&arg(0));
                Ok(V::F32(if x.is_nan() { 0x7fc0_0000 } else { x.to_bits() }))
            }
            "canon_sum16" => {
                let xs: Vec<f32> = self.slice_items(&arg(0)).iter().map(|v| f32v(&self.deref_val(v))).collect();
                Ok(V::F32(canon_sum16(&xs).to_bits()))
            }
            "canon_dot16" => {
                let w: Vec<f32> = self.slice_items(&arg(0)).iter().map(|v| f32v(&self.deref_val(v))).collect();
                let x: Vec<f32> = self.slice_items(&arg(1)).iter().map(|v| f32v(&self.deref_val(v))).collect();
                let prods: Vec<f32> = w.iter().zip(x.iter()).map(|(a, b)| a * b).collect();
                Ok(V::F32(canon_sum16(&prods).to_bits()))
            }
            "canon_sum_seq" => {
                // Rust's float Iterator::sum: a left fold from −0.0 (02 section 5; RV D3-i,
                // inference: the start value follows the pinned Rust reference)
                let xs: Vec<f32> = self.slice_items(&arg(0)).iter().map(|v| f32v(&self.deref_val(v))).collect();
                let mut acc = -0.0f32;
                for x in xs {
                    acc += x;
                }
                Ok(V::F32(acc.to_bits()))
            }
            // ---- std_platform
            "hint_none" => Ok(V::Hint(None)),
            "hint_some" => Ok(V::Hint(Some(Box::new(arg(0))))),
            "hint_get" => match self.deref_val(&arg(0)) {
                V::Hint(Some(x)) => Ok(self.some(V::Ref(Ptr { cell: new_cell(*x), path: vec![] }))),
                _ => Ok(self.none()),
            },
            "mutex_new" => Ok(V::Mutex(new_cell(arg(0)), Rc::new(RefCell::new(false)))),
            "mutex_with_lock" => {
                let m = self.deref_val(&arg(0));
                let V::Mutex(cell, locked) = m else { return self.host("with_lock on a non-Mutex") };
                if *locked.borrow() {
                    return self.host("with_lock re-entered on the same thread: a deadlock in the realisation");
                }
                *locked.borrow_mut() = true;
                let r = self.call_value(arg(1), vec![V::Ref(Ptr { cell: cell.clone(), path: vec![] })], sp);
                *locked.borrow_mut() = false;
                r
            }
            "instant_now" | "clock_now_ns" => self.host("mithi has no clock (a time read is outside the deterministic subset it runs)"),
            "blobfile_read_at" | "slabbuf_bytes_mut" | "slabbuf_bytes" | "frozen_bytes" => self.host(format!("`{name}` needs std_platform I/O, which mithi v0 does not provide")),
            // ---- mem, cmp
            "mem_swap" => {
                let (V::Ref(a), V::Ref(b)) = (arg(0), arg(1)) else { return self.host("swap needs two places") };
                let va = self.read_ptr(&a);
                let vb = self.read_ptr(&b);
                self.write_ptr_or_cell(&a, vb);
                self.write_ptr_or_cell(&b, va);
                Ok(V::Unit)
            }
            "mem_replace" => {
                let V::Ref(a) = arg(0) else { return self.host("replace needs a place") };
                let old = self.read_ptr(&a);
                self.write_ptr_or_cell(&a, arg(1));
                Ok(old)
            }
            "mem_take" => {
                let V::Ref(a) = arg(0) else { return self.host("take needs a place") };
                let old = self.read_ptr(&a);
                let t = targs.first().cloned().unwrap_or(Ty::Error);
                let d = self.default_of(&t, sp)?;
                self.write_ptr_or_cell(&a, d);
                Ok(old)
            }
            "drop" | "mem_forget" => Ok(V::Unit),
            "cmp_min" | "ord_min" => {
                let o = self.val_cmp(&arg(0), &arg(1)).unwrap_or(std::cmp::Ordering::Equal);
                Ok(if o == std::cmp::Ordering::Greater { arg(1) } else { arg(0) })
            }
            "cmp_max" | "ord_max" => {
                let o = self.val_cmp(&arg(0), &arg(1)).unwrap_or(std::cmp::Ordering::Equal);
                Ok(if o == std::cmp::Ordering::Greater { arg(0) } else { arg(1) })
            }
            "ordering_reverse" => {
                let o = self.ord_of(&arg(0));
                Ok(self.ordering(Some(o.reverse())))
            }
            "ordering_then" => {
                let o = self.ord_of(&arg(0));
                Ok(if o == std::cmp::Ordering::Equal { arg(1) } else { arg(0) })
            }
            "ordering_is_eq" => Ok(V::Bool(self.ord_of(&arg(0)) == std::cmp::Ordering::Equal)),
            "ordering_is_lt" => Ok(V::Bool(self.ord_of(&arg(0)) == std::cmp::Ordering::Less)),
            "ordering_is_gt" => Ok(V::Bool(self.ord_of(&arg(0)) == std::cmp::Ordering::Greater)),
            "range_len" => match self.deref_val(&arg(0)) {
                V::Adt(_, _, fs) => Ok(V::Int((int(&fs[1]) - int(&fs[0])).max(0))),
                _ => Ok(V::Int(0)),
            },
            "range_contains" => match self.deref_val(&arg(0)) {
                V::Adt(_, _, fs) => {
                    let x = int(&self.deref_val(&arg(1)));
                    Ok(V::Bool(x >= int(&fs[0]) && x < int(&fs[1])))
                }
                _ => Ok(V::Bool(false)),
            },
            "range_next" | "range_incl_next" => {
                let V::Ref(p) = arg(0) else { return self.host("next without a place") };
                let v = self.read_ptr(&p);
                let V::Adt(a, var, mut fs) = v else { return self.host("bad range") };
                let (s, e) = (int(&fs[0]), int(&fs[1]));
                let end = if name == "range_incl_next" { e + 1 } else { e };
                if s < end {
                    fs[0] = V::Int(s + 1);
                    self.write_ptr_or_cell(&p, V::Adt(a, var, fs));
                    Ok(self.some(V::Int(s)))
                } else {
                    Ok(self.none())
                }
            }
            "clone" => Ok(fresh_closures(&self.c.closures, self.deref_val(&arg(0)))),
            "eq" | "ne" | "partial_cmp" | "cmp" | "default" | "into" => {
                let st = targs.first().cloned().unwrap_or(Ty::Error);
                self.derived(name, &st, args, sp)
            }
            // ---- iterators
            "iter_next" => {
                let V::Ref(p) = arg(0) else { return self.host("next without a place") };
                let it = self.read_ptr(&p);
                match it {
                    V::Iter(rc) => {
                        let r = self.iter_next(&rc)?;
                        Ok(match r {
                            Some(x) => self.some(x),
                            None => self.none(),
                        })
                    }
                    _ => self.host("next on a non-iterator"),
                }
            }
            n if n.starts_with("iter_") => self.iter_builtin(n, targs, args, sp),
            other => self.host(format!("builtin `{other}` is not implemented")),
        }
    }

    fn write_ptr_or_cell(&self, p: &Ptr, v: V) {
        if p.path.is_empty() {
            *p.cell.borrow_mut() = v;
        } else {
            self.write_ptr(p, v);
        }
    }

    fn stable_sort(&mut self, items: Vec<V>, cmp: &mut dyn FnMut(&mut Self, &V, &V) -> R<std::cmp::Ordering>) -> R<Vec<V>> {
        // insertion-merge sort that keeps equal elements in order (Rust's sort is stable)
        if items.len() <= 1 {
            return Ok(items);
        }
        let mid = items.len() / 2;
        let right = items[mid..].to_vec();
        let left = items[..mid].to_vec();
        let l = self.stable_sort(left, cmp)?;
        let r = self.stable_sort(right, cmp)?;
        let mut out = Vec::with_capacity(l.len() + r.len());
        let (mut i, mut j) = (0, 0);
        while i < l.len() && j < r.len() {
            if cmp(self, &r[j], &l[i])? == std::cmp::Ordering::Less {
                out.push(r[j].clone());
                j += 1;
            } else {
                out.push(l[i].clone());
                i += 1;
            }
        }
        out.extend_from_slice(&l[i..]);
        out.extend_from_slice(&r[j..]);
        Ok(out)
    }

    fn iter_builtin(&mut self, name: &str, targs: &[Ty], args: Vec<V>, sp: Span) -> R<V> {
        let self_ty = targs.first().cloned().unwrap_or(Ty::Error);
        let recv = args.first().cloned().unwrap_or(V::Unit);
        let it = self.make_it(recv, &self_ty)?;
        let arg = |i: usize| -> V { args.get(i).cloned().unwrap_or(V::Unit) };
        let int = |v: &V| -> i128 {
            match v {
                V::Int(k) => *k,
                _ => 0,
            }
        };
        let wrap = |it: It| V::Iter(Rc::new(RefCell::new(it)));
        match name {
            "iter_filter" => Ok(wrap(It::Filter(Box::new(it), arg(1)))),
            "iter_map" => Ok(wrap(It::Map(Box::new(it), arg(1)))),
            "iter_filter_map" => Ok(wrap(It::FilterMap(Box::new(it), arg(1)))),
            "iter_enumerate" => Ok(wrap(It::Enumerate(Box::new(it), 0))),
            "iter_zip" => {
                let other_ty = targs.get(1).cloned().unwrap_or(Ty::Error);
                let o = self.make_it(arg(1), &other_ty)?;
                Ok(wrap(It::Zip(Box::new(it), Box::new(o))))
            }
            "iter_rev" => {
                let mut all = self.collect_all(it)?;
                all.reverse();
                Ok(wrap(It::Items(all.into())))
            }
            "iter_take" => Ok(wrap(It::Take(Box::new(it), int(&arg(1)).max(0) as usize))),
            "iter_skip" => Ok(wrap(It::Skip(Box::new(it), int(&arg(1)).max(0) as usize))),
            "iter_step_by" => {
                let n = int(&arg(1));
                if n <= 0 {
                    return self.trap("panic", sp, Some("step_by(0)".into()));
                }
                Ok(wrap(It::StepBy(Box::new(it), n as usize, true)))
            }
            "iter_chain" => {
                let other_ty = targs.get(1).cloned().unwrap_or(Ty::Error);
                let o = self.make_it(arg(1), &other_ty)?;
                Ok(wrap(It::Chain(Box::new(it), Box::new(o))))
            }
            "iter_copied" | "iter_cloned" => Ok(wrap(It::Copied(Box::new(it)))),
            "iter_count" => Ok(V::Int(self.collect_all(it)?.len() as i128)),
            "iter_last" => {
                let all = self.collect_all(it)?;
                Ok(match all.last() {
                    Some(x) => self.some(x.clone()),
                    None => self.none(),
                })
            }
            "iter_nth" => {
                let mut st = it;
                let n = int(&arg(1));
                let mut r = None;
                for _ in 0..=n {
                    r = self.it_next(&mut st)?;
                    if r.is_none() {
                        break;
                    }
                }
                Ok(match r {
                    Some(x) => self.some(x),
                    None => self.none(),
                })
            }
            "iter_sum" | "iter_product" => {
                let all = self.collect_all(it)?;
                let res_ty = targs.last().cloned().unwrap_or(Ty::Error);
                let res_ty = if matches!(res_ty, Ty::Param(_) | Ty::Error) { Ty::Int(IntTy::I64) } else { res_ty };
                match res_ty {
                    Ty::F32 => {
                        // Rust's float sum: a left fold from −0.0; product from 1.0
                        let mut acc: f32 = if name == "iter_sum" { -0.0 } else { 1.0 };
                        for x in all {
                            let v = match self.deref_val(&x) {
                                V::F32(b) => f32::from_bits(b),
                                _ => 0.0,
                            };
                            if name == "iter_sum" {
                                acc += v;
                            } else {
                                acc *= v;
                            }
                        }
                        Ok(V::F32(acc.to_bits()))
                    }
                    Ty::F64 => {
                        let mut acc: f64 = if name == "iter_sum" { -0.0 } else { 1.0 };
                        for x in all {
                            let v = match self.deref_val(&x) {
                                V::F64(b) => f64::from_bits(b),
                                _ => 0.0,
                            };
                            if name == "iter_sum" {
                                acc += v;
                            } else {
                                acc *= v;
                            }
                        }
                        Ok(V::F64(acc.to_bits()))
                    }
                    Ty::Int(itt) => {
                        let mut acc: i128 = if name == "iter_sum" { 0 } else { 1 };
                        for x in all {
                            let v = int(&self.deref_val(&x));
                            let r = if name == "iter_sum" { acc.checked_add(v) } else { acc.checked_mul(v) };
                            acc = match r {
                                Some(r) if r >= itt.min_val() && r <= itt.max_val() => r,
                                _ => return self.trap(if name == "iter_sum" { "ovf(add)" } else { "ovf(mul)" }, sp, None),
                            };
                        }
                        Ok(V::Int(acc))
                    }
                    _ => self.host("sum of a non-numeric type"),
                }
            }
            "iter_fold" => {
                let mut st = it;
                let mut acc = arg(1);
                let f = arg(2);
                while let Some(x) = self.it_next(&mut st)? {
                    acc = self.call_value(f.clone(), vec![acc, x], sp)?;
                }
                Ok(acc)
            }
            "iter_for_each" => {
                let mut st = it;
                let f = arg(1);
                while let Some(x) = self.it_next(&mut st)? {
                    self.call_value(f.clone(), vec![x], sp)?;
                }
                Ok(V::Unit)
            }
            "iter_any" | "iter_all" | "iter_position" | "iter_find" => {
                let mut st = it;
                let f = arg(1);
                let mut k: i128 = 0;
                while let Some(x) = self.it_next(&mut st)? {
                    let a = if name == "iter_find" { V::Ref(Ptr { cell: new_cell(x.clone()), path: vec![] }) } else { x.clone() };
                    let r = self.call_value(f.clone(), vec![a], sp)?;
                    let b = matches!(r, V::Bool(true));
                    match name {
                        "iter_any" if b => return Ok(V::Bool(true)),
                        "iter_all" if !b => return Ok(V::Bool(false)),
                        "iter_position" if b => return Ok(self.some(V::Int(k))),
                        "iter_find" if b => return Ok(self.some(x)),
                        _ => {}
                    }
                    k += 1;
                }
                Ok(match name {
                    "iter_any" => V::Bool(false),
                    "iter_all" => V::Bool(true),
                    _ => self.none(),
                })
            }
            "iter_max" | "iter_min" | "iter_max_by_key" | "iter_min_by_key" | "iter_max_by" | "iter_min_by" => {
                let all = self.collect_all(it)?;
                let f = arg(1);
                let mut best: Option<(V, V)> = None;
                for x in all {
                    let key = match name {
                        "iter_max_by_key" | "iter_min_by_key" => self.call_value(f.clone(), vec![V::Ref(Ptr { cell: new_cell(x.clone()), path: vec![] })], sp)?,
                        _ => x.clone(),
                    };
                    best = Some(match best {
                        None => (x, key),
                        Some((bx, bk)) => {
                            let o = match name {
                                "iter_max_by" | "iter_min_by" => {
                                    let r = self.call_value(f.clone(), vec![V::Ref(Ptr { cell: new_cell(bx.clone()), path: vec![] }), V::Ref(Ptr { cell: new_cell(x.clone()), path: vec![] })], sp)?;
                                    self.ord_of(&r)
                                }
                                _ => self.val_cmp(&bk, &key).unwrap_or(std::cmp::Ordering::Equal),
                            };
                            // Rust: max returns the last maximum, min the first minimum
                            let take_new = if name.contains("max") { o != std::cmp::Ordering::Greater } else { o == std::cmp::Ordering::Greater };
                            if take_new {
                                (x, key)
                            } else {
                                (bx, bk)
                            }
                        }
                    });
                }
                Ok(match best {
                    Some((x, _)) => self.some(x),
                    None => self.none(),
                })
            }
            "iter_collect" => Ok(V::Vec(self.collect_all(it)?)),
            other => self.host(format!("iterator method `{other}` is not implemented")),
        }
    }
}

fn float_to_int(x: f64, it: IntTy) -> i128 {
    // Rust `as`: saturating, NaN to 0 (FF-CAST)
    if x.is_nan() {
        return 0;
    }
    let t = x.trunc();
    if t <= it.min_val() as f64 {
        it.min_val()
    } else if t >= it.max_val() as f64 {
        it.max_val()
    } else {
        t as i128
    }
}

/// Type arguments of an impl method for a concrete Self type (impl generics by matching).
pub fn impl_targs(c: &Checked, fid: FnId, st: &Ty) -> Vec<Ty> {
    let f = &c.program.fns[fid as usize];
    let crate::program::Owner::Impl(iid) = f.owner else { return vec![] };
    let im = &c.program.impls[iid as usize];
    let mut out = vec![Ty::Error; im.generics.len()];
    fn m(p: &Ty, t: &Ty, out: &mut Vec<Ty>) {
        match (p, t) {
            (Ty::Param(i), _) => {
                if (*i as usize) < out.len() {
                    out[*i as usize] = t.clone();
                }
            }
            (Ty::Adt(_, xs), Ty::Adt(_, ys)) | (Ty::Tuple(xs), Ty::Tuple(ys)) => {
                for (x, y) in xs.iter().zip(ys) {
                    m(x, y, out);
                }
            }
            (Ty::Ref(_, x), Ty::Ref(_, y)) | (Ty::Slice(x), Ty::Slice(y)) => m(x, y, out),
            (Ty::Array(x, n), Ty::Array(y, k)) => {
                m(x, y, out);
                m(n, k, out);
            }
            _ => {}
        }
    }
    m(&im.self_ty, st, &mut out);
    out
}

// ---------------------------------------------------------------- entry points

pub fn outcome_text(i: &Interp, r: Result<V, Ctrl>) -> Result<String, String> {
    match r {
        Ok(v) => Ok(i.debug(&v)),
        Err(Ctrl::Trap(t)) => {
            let mut s = format!("trap {} in {} at `{}`", t.kind, t.def, t.anchor);
            if let Some(m) = t.msg {
                s.push_str(&format!(": {m}"));
            }
            if !t.par_index.is_empty() {
                let v: Vec<String> = t.par_index.iter().rev().cloned().collect();
                s.push_str(&format!(" [par {}]", v.join(", ")));
            }
            if !t.abandoned.is_empty() {
                s.push_str(&format!("; abandoned (newest first): {}", t.abandoned.join(", ")));
            }
            Err(s)
        }
        Err(Ctrl::Host(m)) => Err(format!("host limit: {m}")),
        Err(Ctrl::Return(v)) => Ok(i.debug(&v)),
        Err(Ctrl::Break(..)) | Err(Ctrl::Continue(_)) => Err("break or continue outside a loop".into()),
    }
}

pub fn find_fn(c: &Checked, name: &str) -> Option<FnId> {
    c.program.fns.iter().position(|f| (f.path == name || f.name == name) && f.role == crate::diag::FileRole::User).map(|i| i as FnId)
}

pub fn run_entry(c: &Checked, name: &str) -> Result<String, String> {
    let Some(fid) = find_fn(c, name) else { return Err(format!("no function `{name}`")) };
    if !c.program.fns[fid as usize].params.is_empty() {
        return Err(format!("`{name}` takes parameters; `run` calls functions without parameters"));
    }
    let mut i = Interp::new(c);
    let r = i.call(fid, vec![], vec![], Span::DUMMY);
    outcome_text(&i, r)
}

/// Run every `#[test]` function of the user files.
pub fn run_tests(c: &Checked) -> Vec<(String, Result<(), String>)> {
    let mut out = vec![];
    for (fid, f) in c.program.fns.iter().enumerate() {
        if f.role != crate::diag::FileRole::User || !f.has_attr("test") {
            continue;
        }
        let mut i = Interp::new(c);
        let r = i.call(fid as FnId, vec![], vec![], Span::DUMMY);
        let res = outcome_text(&i, r).map(|_| ());
        out.push((f.path.clone(), res));
    }
    out
}

/// Call a function with argument values (for embedding and tests).
pub fn call_fn(c: &Checked, name: &str, args: Vec<V>) -> Result<V, String> {
    let Some(fid) = find_fn(c, name) else { return Err(format!("no function `{name}`")) };
    let mut i = Interp::new(c);
    match i.call(fid, vec![], args, Span::DUMMY) {
        Ok(v) => Ok(v),
        e => outcome_text(&i, e).and_then(|s| Err(s)),
    }
}
