//! Closure capture inference with Rust's rules (note §3.2: "captures follow Rust's inference of
//! capture modes"): a non-`move` closure captures each outer variable by the weakest mode its body
//! needs — shared reference, unique (mutable) reference, or by value when the body moves a non-Copy
//! value out of it. A `move` closure captures every outer variable by value. The closure's Fn kind
//! follows from what the body does with its captures.

use crate::program::Program;
use crate::thir::*;
use crate::types::*;
use std::collections::BTreeMap;

#[derive(Clone, Copy, PartialEq, Eq)]
enum Ctx {
    Value,
    Read,
    Write,
}

struct Cap<'a> {
    locals: &'a [LocalDecl],
    cid: ClosureId,
    parents: &'a [Option<ClosureId>],
    modes: BTreeMap<LocalId, CaptureMode>,
    moved_out: bool,
    mutated: bool,
    is_copy: &'a mut dyn FnMut(&Ty) -> bool,
    /// the Fn kind of a callable type (0 Fn, 1 FnMut, 2 FnOnce or unknown)
    callee_kind: &'a dyn Fn(&Ty) -> u8,
    nested: &'a BTreeMap<ClosureId, Vec<Capture>>,
}

impl<'a> Cap<'a> {
    fn internal(&self, l: LocalId) -> bool {
        let mut c = self.locals[l as usize].closure;
        while let Some(x) = c {
            if x == self.cid {
                return true;
            }
            c = self.parents.get(x as usize).copied().flatten();
        }
        false
    }
    fn note(&mut self, l: LocalId, m: CaptureMode) {
        if self.internal(l) {
            return;
        }
        let e = self.modes.entry(l).or_insert(m);
        let rank = |x: CaptureMode| match x {
            CaptureMode::Ref => 0,
            CaptureMode::Mut => 1,
            CaptureMode::Move => 2,
        };
        if rank(m) > rank(*e) {
            *e = m;
        }
    }
    fn visit(&mut self, e: &TExpr, ctx: Ctx) {
        match &e.kind {
            TK::Local(l) => {
                let l = *l;
                if self.internal(l) {
                    return;
                }
                match ctx {
                    Ctx::Write => {
                        self.note(l, CaptureMode::Mut);
                        self.mutated = true;
                    }
                    Ctx::Read => self.note(l, CaptureMode::Ref),
                    Ctx::Value => {
                        let ty = self.locals[l as usize].ty.clone();
                        if (self.is_copy)(&ty) {
                            self.note(l, CaptureMode::Ref);
                        } else {
                            self.note(l, CaptureMode::Move);
                            self.moved_out = true;
                        }
                    }
                }
            }
            TK::Field(b, _) => {
                let c = match ctx {
                    Ctx::Value => {
                        if (self.is_copy)(&e.ty) {
                            Ctx::Read
                        } else {
                            Ctx::Value
                        }
                    }
                    x => x,
                };
                self.visit(b, c);
            }
            TK::Index(b, i) => {
                let c = match ctx {
                    Ctx::Value => Ctx::Read,
                    x => x,
                };
                self.visit(b, c);
                self.visit(i, Ctx::Value);
            }
            TK::SliceRange { base, lo, hi, .. } => {
                let c = match ctx {
                    Ctx::Value => Ctx::Read,
                    x => x,
                };
                self.visit(base, c);
                if let Some(l) = lo {
                    self.visit(l, Ctx::Value);
                }
                if let Some(h) = hi {
                    self.visit(h, Ctx::Value);
                }
            }
            TK::Deref(b) => {
                // a write through a reference needs a unique borrow of the reference variable
                let c = if ctx == Ctx::Write { Ctx::Write } else { Ctx::Read };
                if ctx == Ctx::Write {
                    // `*r = v` mutates the referent; the capture of r is a unique borrow
                    self.visit_ref_holder(b);
                } else {
                    self.visit(b, c);
                }
            }
            TK::Borrow(m, p) => self.visit(p, if *m { Ctx::Write } else { Ctx::Read }),
            TK::Assign(l, r) | TK::AssignOp(_, l, r) => {
                self.visit(r, Ctx::Value);
                self.visit(l, Ctx::Write);
            }
            TK::Closure(c) => {
                if let Some(caps) = self.nested.get(c) {
                    for cap in caps.clone() {
                        if !self.internal(cap.local) {
                            self.note(cap.local, cap.mode);
                            if cap.mode == CaptureMode::Mut {
                                self.mutated = true;
                            }
                            if cap.mode == CaptureMode::Move {
                                let ty = self.locals[cap.local as usize].ty.clone();
                                if !(self.is_copy)(&ty) {
                                    self.moved_out = true;
                                }
                            }
                        }
                    }
                }
            }
            TK::Match(s, arms) => {
                // a by-value binding of a non-Copy part moves the scrutinee: Rust captures it by
                // value then (review 2026-10-23: `move || match o { Some(x) => eat(x), .. }`
                // was inferred Fn, so a second call was accepted)
                let moves = arms.iter().any(|a| self.pat_moves(&a.pat));
                self.visit(s, if moves { Ctx::Value } else { Ctx::Read });
                for a in arms {
                    if let Some(g) = &a.guard {
                        self.visit(g, Ctx::Value);
                    }
                    self.visit(&a.body, Ctx::Value);
                }
            }
            TK::LetCond(p, s) => {
                let moves = self.pat_moves(p);
                self.visit(s, if moves { Ctx::Value } else { Ctx::Read })
            }
            TK::Matches(s, _) => self.visit(s, Ctx::Read),
            // calling a captured callable needs it by shared reference (Fn), by unique reference
            // (FnMut) or by value (FnOnce), as Rust captures it (review 2026-10-16: the callee
            // was visited as a value use, so a captured `op: F` was moved)
            TK::CallValue(f, args) => {
                match (self.callee_kind)(&f.ty) {
                    0 => self.visit(f, Ctx::Read),
                    1 => self.visit(f, Ctx::Write),
                    _ => self.visit(f, Ctx::Value),
                }
                for a in args {
                    self.visit(a, Ctx::Value);
                }
            }
            _ => {
                for c in e.children() {
                    self.visit(c, Ctx::Value);
                }
            }
        }
    }
    /// Does the pattern bind a non-Copy part by value?
    fn pat_moves(&mut self, p: &TPat) -> bool {
        match &p.kind {
            PK::Bind { by_ref: None, sub, .. } => {
                let t = p.ty.clone();
                !(self.is_copy)(&t) || sub.as_ref().map(|x| self.pat_moves(x)).unwrap_or(false)
            }
            PK::Bind { sub: Some(x), .. } => self.pat_moves(x),
            PK::Tuple(ps) | PK::Or(ps) | PK::Slice(ps, _) => {
                let mut m = false;
                for x in ps {
                    m |= self.pat_moves(x);
                }
                m
            }
            PK::Variant { fields, .. } => {
                let mut m = false;
                for (_, x) in fields {
                    m |= self.pat_moves(x);
                }
                m
            }
            _ => false,
        }
    }
    fn visit_ref_holder(&mut self, b: &TExpr) {
        match &b.kind {
            TK::Local(l) => {
                if !self.internal(*l) {
                    self.note(*l, CaptureMode::Mut);
                    self.mutated = true;
                }
            }
            _ => self.visit(b, Ctx::Write),
        }
    }
}

/// Returns the captures and the Fn kind (0 Fn, 1 FnMut, 2 FnOnce).
pub fn infer_captures(_p: &Program, locals: &[LocalDecl], cid: ClosureId, parents: &[Option<ClosureId>], cd: &ClosureDef, is_copy: &mut dyn FnMut(&Ty) -> bool, callee_kind: &dyn Fn(&Ty) -> u8) -> (Vec<Capture>, u8) {
    thread_local! {
        static NESTED: std::cell::RefCell<BTreeMap<ClosureId, Vec<Capture>>> = std::cell::RefCell::new(BTreeMap::new());
    }
    let nested = NESTED.with(|n| n.borrow().clone());
    let mut c = Cap { locals, cid, parents, modes: BTreeMap::new(), moved_out: false, mutated: false, is_copy, callee_kind, nested: &nested };
    c.visit(&cd.body, Ctx::Value);
    let mut caps: Vec<Capture> = c.modes.iter().map(|(l, m)| Capture { local: *l, mode: if cd.is_move { CaptureMode::Move } else { *m }, ty: locals[*l as usize].ty.clone() }).collect();
    caps.sort_by_key(|x| x.local);
    // K-LinClo: a closure that captures a Linear value by move implements only FnOnce
    let linear_capture = caps.iter().any(|cap| cap.mode == CaptureMode::Move && crate::analysis::wf::is_linear_p(_p, &[], &cap.ty, 0));
    let kind = if c.moved_out || linear_capture {
        2
    } else if c.mutated {
        1
    } else {
        0
    };
    NESTED.with(|n| {
        n.borrow_mut().insert(cid, caps.clone());
    });
    (caps, kind)
}
