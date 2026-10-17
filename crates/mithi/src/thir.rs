//! Typed IR (the THIR): what the checker's analyses and the interpreter run on.
//! Method calls are resolved, auto-references and auto-dereferences are explicit, and every
//! expression carries its type.

use crate::ast::{BinOp, UnOp};
use crate::diag::Span;
use crate::types::*;

pub type LocalId = u32;
pub type LoopId = u32;

#[derive(Clone, Debug)]
pub struct LocalDecl {
    pub name: String,
    pub ty: Ty,
    pub mutable: bool,
    pub span: Span,
    /// parameter index, if a parameter
    pub param: Option<usize>,
    /// the closure whose parameter this is, if any
    pub closure: Option<ClosureId>,
}

#[derive(Clone, Debug, PartialEq)]
pub enum LitVal {
    Int(i128),
    /// f32 bits or f64 bits, by the expression's type
    Float(u64),
    Bool(bool),
    Str(String),
    Char(char),
    Unit,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CaptureMode {
    Ref,
    Mut,
    Move,
}

#[derive(Clone, Debug)]
pub struct Capture {
    pub local: LocalId,
    pub mode: CaptureMode,
    pub ty: Ty,
}

#[derive(Clone, Debug)]
pub struct ClosureDef {
    pub owner: FnId,
    pub params: Vec<TPat>,
    pub param_tys: Vec<Ty>,
    pub ret: Ty,
    pub body: TExpr,
    pub captures: Vec<Capture>,
    pub is_move: bool,
    pub span: Span,
    /// Fn (0), FnMut (1) or FnOnce (2), as inferred from the body
    pub fn_kind: u8,
}

#[derive(Clone, Debug)]
pub enum TrapKind {
    Panic,
    Unreachable,
    Unwrap,
    Expect,
    Assert,
    Hole(String),
    Elided,
}

#[derive(Clone, Debug)]
pub struct TExpr {
    pub kind: TK,
    pub ty: Ty,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub enum TK {
    Lit(LitVal),
    Local(LocalId),
    /// a constant item, by index
    Const(u32),
    Field(Box<TExpr>, u32),
    Index(Box<TExpr>, Box<TExpr>),
    /// `place[lo..hi]` (an unsized place of slice type)
    SliceRange { base: Box<TExpr>, lo: Option<Box<TExpr>>, hi: Option<Box<TExpr>>, inclusive: bool },
    Deref(Box<TExpr>),
    Borrow(bool, Box<TExpr>),
    /// `&[T; N]` / `&Vec<T>` / `&Buf<T>` / `&String` coerced to `&[T]` / `&str`
    Unsize(Box<TExpr>),
    Unary(UnOp, Box<TExpr>),
    Binary(BinOp, Box<TExpr>, Box<TExpr>),
    Cast(Box<TExpr>),
    Assign(Box<TExpr>, Box<TExpr>),
    AssignOp(BinOp, Box<TExpr>, Box<TExpr>),
    /// direct call of a function (user, prelude, std builtin); substs cover all generics
    Call { f: FnId, substs: Vec<Ty>, args: Vec<TExpr> },
    /// a trait method on a type parameter: dispatched on the runtime type
    TraitCall { tr: TraitId, method: String, decl: FnId, self_ty: Ty, substs: Vec<Ty>, args: Vec<TExpr> },
    /// call of a closure or function value
    CallValue(Box<TExpr>, Vec<TExpr>),
    Closure(ClosureId),
    FnRef(FnId, Vec<Ty>),
    Ctor { adt: AdtId, variant: u32, fields: Vec<TExpr> },
    CtorUpdate { adt: AdtId, variant: u32, fields: Vec<(u32, TExpr)>, base: Box<TExpr> },
    Tuple(Vec<TExpr>),
    Array(Vec<TExpr>),
    Repeat(Box<TExpr>, u64),
    Block(Vec<TStmt>, Option<Box<TExpr>>),
    If(Box<TExpr>, Box<TExpr>, Option<Box<TExpr>>),
    Match(Box<TExpr>, Vec<TArm>),
    Loop(LoopId, Box<TExpr>),
    While(LoopId, Box<TExpr>, Box<TExpr>),
    /// `for pat in iter { body }`; `range` is set when iter is a literal range `lo..hi`
    For { id: LoopId, par: bool, pat: TPat, iter: Box<TExpr>, body: Box<TExpr>, range: Option<(Box<TExpr>, Box<TExpr>, bool)> },
    Break(LoopId, Option<Box<TExpr>>),
    Continue(LoopId),
    Return(Option<Box<TExpr>>),
    /// `e?`; `from` is the From conversion applied to the error (None = identity)
    Try { e: Box<TExpr>, is_option: bool, from: Option<(FnId, Vec<Ty>)> },
    /// `deterministic(by: E) { e }`
    Det { evidence: String, body: Box<TExpr> },
    Trap(TrapKind, Option<String>),
    Assert { cond: Box<TExpr>, msg: Option<String> },
    /// `assert_eq!(a, b)` / `assert_ne!`
    AssertCmp { eq: bool, a: Box<TExpr>, b: Box<TExpr> },
    /// `format!` and friends: a String built from literal pieces and arguments
    Format { pieces: Vec<String>, args: Vec<TExpr> },
    /// `matches!(e, pat)`
    Matches(Box<TExpr>, Box<TPat>),
    /// `let pat = e` inside an `if`/`while` condition
    LetCond(Box<TPat>, Box<TExpr>),
    Error,
}

#[derive(Clone, Debug)]
pub enum TStmt {
    Let { pat: TPat, init: Option<TExpr>, els: Option<TExpr>, span: Span },
    Expr(TExpr),
}

#[derive(Clone, Debug)]
pub struct TArm {
    pub pat: TPat,
    pub guard: Option<TExpr>,
    pub body: TExpr,
}

#[derive(Clone, Debug)]
pub struct TPat {
    pub kind: PK,
    pub ty: Ty,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub enum PK {
    Wild,
    /// binding; `by_ref` = Some(mutable) when it binds a reference (default binding mode or `ref`)
    Bind { local: LocalId, by_ref: Option<bool>, sub: Option<Box<TPat>> },
    Lit(LitVal),
    Range(i128, i128),
    Tuple(Vec<TPat>),
    Variant { adt: AdtId, variant: u32, fields: Vec<(u32, TPat)> },
    /// match through a reference: the scrutinee is a reference, the pattern matches its referent
    Deref(Box<TPat>),
    Or(Vec<TPat>),
    Slice(Vec<TPat>, Option<usize>),
}

/// A checked function body.
#[derive(Clone, Debug)]
pub struct Body {
    pub fid: FnId,
    pub locals: Vec<LocalDecl>,
    pub params: Vec<LocalId>,
    pub expr: TExpr,
    /// `requires` clauses, typed over the parameters
    pub requires: Vec<TExpr>,
    /// `ensures` clauses; `result` is the local `result_local`
    pub ensures: Vec<TExpr>,
    /// footprint ensures: `footprint(result) == place`
    pub footprints: Vec<TExpr>,
    pub result_local: Option<LocalId>,
    pub n_loops: u32,
    /// loop labels by id (for diagnostics)
    pub loop_spans: Vec<Span>,
}

impl TExpr {
    pub fn new(kind: TK, ty: Ty, span: Span) -> TExpr {
        TExpr { kind, ty, span }
    }
    pub fn err(span: Span) -> TExpr {
        TExpr { kind: TK::Error, ty: Ty::Error, span }
    }
    pub fn is_place(&self) -> bool {
        matches!(self.kind, TK::Local(_) | TK::Field(..) | TK::Index(..) | TK::Deref(_) | TK::SliceRange { .. } | TK::Const(_))
    }
    /// Visit every direct child expression.
    pub fn children(&self) -> Vec<&TExpr> {
        let mut v: Vec<&TExpr> = Vec::new();
        match &self.kind {
            TK::Lit(_) | TK::Local(_) | TK::Const(_) | TK::Closure(_) | TK::FnRef(..) | TK::Continue(_) | TK::Trap(..) | TK::Error => {}
            TK::Field(e, _) | TK::Deref(e) | TK::Borrow(_, e) | TK::Unsize(e) | TK::Unary(_, e) | TK::Cast(e) | TK::Repeat(e, _) | TK::Loop(_, e) => v.push(e),
            TK::Index(a, b) | TK::Binary(_, a, b) | TK::Assign(a, b) | TK::AssignOp(_, a, b) | TK::While(_, a, b) => {
                v.push(a);
                v.push(b);
            }
            TK::SliceRange { base, lo, hi, .. } => {
                v.push(base);
                if let Some(l) = lo {
                    v.push(l);
                }
                if let Some(h) = hi {
                    v.push(h);
                }
            }
            TK::Call { args, .. } | TK::TraitCall { args, .. } => v.extend(args.iter()),
            TK::CallValue(f, args) => {
                v.push(f);
                v.extend(args.iter());
            }
            TK::Ctor { fields, .. } | TK::Tuple(fields) | TK::Array(fields) => v.extend(fields.iter()),
            TK::CtorUpdate { fields, base, .. } => {
                v.extend(fields.iter().map(|(_, e)| e));
                v.push(base);
            }
            TK::Block(stmts, tail) => {
                for s in stmts {
                    match s {
                        TStmt::Let { init, els, .. } => {
                            if let Some(i) = init {
                                v.push(i);
                            }
                            if let Some(e) = els {
                                v.push(e);
                            }
                        }
                        TStmt::Expr(e) => v.push(e),
                    }
                }
                if let Some(t) = tail {
                    v.push(t);
                }
            }
            TK::If(c, t, e) => {
                v.push(c);
                v.push(t);
                if let Some(e) = e {
                    v.push(e);
                }
            }
            TK::Match(s, arms) => {
                v.push(s);
                for a in arms {
                    if let Some(g) = &a.guard {
                        v.push(g);
                    }
                    v.push(&a.body);
                }
            }
            TK::For { iter, body, .. } => {
                v.push(iter);
                v.push(body);
            }
            TK::Break(_, e) | TK::Return(e) => {
                if let Some(e) = e {
                    v.push(e);
                }
            }
            TK::Try { e, .. } => v.push(e),
            TK::Det { body, .. } => v.push(body),
            TK::Assert { cond, .. } => v.push(cond),
            TK::AssertCmp { a, b, .. } => {
                v.push(a);
                v.push(b);
            }
            TK::Format { args, .. } => v.extend(args.iter()),
            TK::Matches(e, _) | TK::LetCond(_, e) => v.push(e),
        }
        v
    }
    /// Pre-order walk over this expression and every sub-expression (closures not entered).
    pub fn walk(&self, f: &mut dyn FnMut(&TExpr)) {
        f(self);
        for c in self.children() {
            c.walk(f);
        }
    }
}

impl TPat {
    pub fn bindings(&self, out: &mut Vec<LocalId>) {
        match &self.kind {
            PK::Bind { local, sub, .. } => {
                out.push(*local);
                if let Some(s) = sub {
                    s.bindings(out);
                }
            }
            PK::Tuple(ps) | PK::Or(ps) | PK::Slice(ps, _) => {
                for p in ps {
                    p.bindings(out);
                }
            }
            PK::Variant { fields, .. } => {
                for (_, p) in fields {
                    p.bindings(out);
                }
            }
            PK::Deref(p) => p.bindings(out),
            _ => {}
        }
    }
    pub fn is_irrefutable_bind(&self) -> Option<LocalId> {
        match &self.kind {
            PK::Bind { local, sub: None, .. } => Some(*local),
            _ => None,
        }
    }
}
