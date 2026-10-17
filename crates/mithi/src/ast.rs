//! Surface AST, produced by `parser` and mirrored by grammar/mithril_v0.lark.

use crate::diag::Span;

#[derive(Clone, Debug)]
pub struct Ident {
    pub name: String,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub struct Attr {
    pub name: String,
    /// Raw argument tokens rendered as text, split at top-level commas.
    pub args: Vec<String>,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub struct Path {
    pub segs: Vec<PathSeg>,
    pub span: Span,
    pub global: bool,
}

#[derive(Clone, Debug)]
pub struct PathSeg {
    pub ident: Ident,
    pub generics: Option<Vec<GenericArg>>,
}

impl Path {
    pub fn last(&self) -> &str {
        &self.segs.last().unwrap().ident.name
    }
    pub fn text(&self) -> String {
        self.segs.iter().map(|s| s.ident.name.as_str()).collect::<Vec<_>>().join("::")
    }
    pub fn single(&self) -> Option<&str> {
        if self.segs.len() == 1 && self.segs[0].generics.is_none() {
            Some(&self.segs[0].ident.name)
        } else {
            None
        }
    }
}

#[derive(Clone, Debug)]
pub enum GenericArg {
    Type(TypeAst),
    /// `Item = T` associated-type binding.
    Binding(Ident, TypeAst),
    /// A const argument such as `4096` or `{ N }`.
    Const(Expr),
}

#[derive(Clone, Debug)]
pub struct TypeAst {
    pub kind: TypeKind,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub enum TypeKind {
    Path(Path),
    Ref { mutable: bool, lifetime: Option<String>, inner: Box<TypeAst> },
    Slice(Box<TypeAst>),
    Array(Box<TypeAst>, Box<Expr>),
    Tuple(Vec<TypeAst>),
    Never,
    Infer,
    ImplTrait(Vec<Bound>),
    DynTrait(Vec<Bound>),
    FnPtr(Vec<TypeAst>, Option<Box<TypeAst>>),
    /// `<T as Trait>::Name`
    QPath(Box<TypeAst>, Path, Ident),
    RawPtr(bool, Box<TypeAst>),
}

#[derive(Clone, Debug)]
pub enum Bound {
    Trait(Path),
    /// `Fn(A, B) -> R` (also FnMut, FnOnce)
    FnTrait { kind: String, params: Vec<TypeAst>, ret: Option<TypeAst>, span: Span },
    Lifetime(String, Span),
    /// `?Sized`, `?Local`, `?Linear`
    Maybe(Path),
}

#[derive(Clone, Debug)]
pub struct GenericParam {
    pub name: Ident,
    pub bounds: Vec<Bound>,
    pub is_const: Option<TypeAst>,
    pub is_lifetime: bool,
}

#[derive(Clone, Debug, Default)]
pub struct Generics {
    pub params: Vec<GenericParam>,
    /// where-clauses: (type, bounds)
    pub wheres: Vec<(TypeAst, Vec<Bound>)>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum FnKind {
    Plain,
    Kernel,
    Policy,
}

#[derive(Clone, Debug)]
pub enum SelfParam {
    Value { mutable: bool },
    Ref { mutable: bool },
}

#[derive(Clone, Debug)]
pub struct Param {
    pub pat: Pat,
    pub ty: TypeAst,
    pub attrs: Vec<Attr>,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub struct Effect {
    pub name: Ident,
    pub arg: Option<Ident>,
}

#[derive(Clone, Debug)]
pub struct FnDecl {
    pub attrs: Vec<Attr>,
    pub is_pub: bool,
    pub kind: FnKind,
    pub name: Ident,
    pub generics: Generics,
    pub self_param: Option<(SelfParam, Span)>,
    pub params: Vec<Param>,
    pub ret: Option<TypeAst>,
    pub uses: Option<Vec<Effect>>,
    pub requires: Vec<Expr>,
    pub ensures: Vec<Expr>,
    pub body: Option<Block>,
    pub span: Span,
    /// span of the signature (from the first keyword to the end of the contract)
    pub sig_span: Span,
    pub is_unsafe: bool,
    pub is_async: bool,
    pub is_const: bool,
    pub is_extern: bool,
}

#[derive(Clone, Debug)]
pub struct FieldDecl {
    pub attrs: Vec<Attr>,
    pub is_pub: bool,
    pub name: Ident,
    pub ty: TypeAst,
}

#[derive(Clone, Debug)]
pub enum VariantData {
    Unit,
    Tuple(Vec<FieldDecl>),
    Struct(Vec<FieldDecl>),
}

#[derive(Clone, Debug)]
pub struct StructDecl {
    pub attrs: Vec<Attr>,
    pub is_pub: bool,
    pub linear: bool,
    pub name: Ident,
    pub generics: Generics,
    pub data: VariantData,
    /// `struct S;` with an elided body (`…`) in a prelude: opaque.
    pub opaque: bool,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub struct VariantDecl {
    pub name: Ident,
    pub data: VariantData,
    pub discr: Option<Expr>,
}

#[derive(Clone, Debug)]
pub struct EnumDecl {
    pub attrs: Vec<Attr>,
    pub is_pub: bool,
    pub name: Ident,
    pub generics: Generics,
    pub variants: Vec<VariantDecl>,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub struct InvariantDecl {
    pub ty: Path,
    pub cond: Expr,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub enum ImplMember {
    Fn(FnDecl),
    Type(Ident, TypeAst),
    Const(ConstDecl),
}

#[derive(Clone, Debug)]
pub struct ImplDecl {
    pub attrs: Vec<Attr>,
    pub generics: Generics,
    pub trait_: Option<Path>,
    pub negative: bool,
    pub self_ty: TypeAst,
    pub members: Vec<ImplMember>,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub enum TraitMember {
    Fn(FnDecl),
    Type(Ident, Vec<Bound>),
    Const(Ident, TypeAst, Option<Expr>),
}

#[derive(Clone, Debug)]
pub struct TraitDecl {
    pub attrs: Vec<Attr>,
    pub is_pub: bool,
    pub name: Ident,
    pub generics: Generics,
    pub supers: Vec<Bound>,
    pub members: Vec<TraitMember>,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub struct FormatField {
    pub name: Ident,
    pub code: FormatCode,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub enum FormatCode {
    /// A storage or scalar type name, possibly with generic-like arguments: `f16`, `e8m0`,
    /// `nibbles<64, offset = 8>`, `e2m1x2<32>`.
    Named { name: Ident, args: Vec<(Option<Ident>, Expr)> },
    Array(Box<FormatCode>, Expr),
}

#[derive(Clone, Debug)]
pub struct FormatDecl {
    pub attrs: Vec<Attr>,
    pub is_pub: bool,
    pub name: Ident,
    pub fields: Vec<FormatField>,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub struct Directive {
    pub verb: Ident,
    /// Remaining words of the directive, in order (identifiers, numbers, dotted names).
    pub words: Vec<Ident>,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub struct ScheduleDecl {
    pub name: Ident,
    pub for_fn: Path,
    pub arch: Ident,
    pub features: Vec<Ident>,
    pub directives: Vec<Directive>,
    /// prelude stub `{ … }`
    pub elided: bool,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub struct ClaimQual {
    pub name: Ident,
    pub args: Vec<(Ident, ClaimArg)>,
}

#[derive(Clone, Debug)]
pub enum ClaimArg {
    Path(Path),
    Percent(String, Span),
    Num(String, Span),
}

#[derive(Clone, Debug)]
pub struct Claim {
    pub kind: Ident,
    pub args: Vec<Path>,
    pub grade: Ident,
    pub qualifier: Option<ClaimQual>,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub struct SpecDecl {
    pub name: Ident,
    pub for_fn: Path,
    pub claims: Vec<Claim>,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub struct UseDecl {
    pub tree: Vec<Path>,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub struct ModDecl {
    pub name: Ident,
    pub items: Vec<Item>,
    pub span: Span,
    /// a `#[path = ..]` attribute (E-X1-NOTYET-PATH in the agent subset)
    pub path_attr: Option<Span>,
}

#[derive(Clone, Debug)]
pub struct ConstDecl {
    pub attrs: Vec<Attr>,
    pub is_pub: bool,
    pub is_static: bool,
    pub is_mut: bool,
    pub name: Ident,
    pub ty: TypeAst,
    pub value: Option<Expr>,
    pub span: Span,
}

/// Prelude-only declaration standing in for a ledger fact (note section 12).
#[derive(Clone, Debug)]
pub struct EvidenceDecl {
    pub name: Path,
    pub fields: Vec<(Ident, Path)>,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub struct SeamDecl {
    pub name: Ident,
    pub fns: Vec<Ident>,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub struct TargetDecl {
    pub arch: Ident,
    pub features: Vec<Ident>,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub struct OutOfScope {
    /// Keyword (upper case) for E-OUT-OF-SCOPE-<KW>.
    pub kw: String,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub enum Item {
    Fn(FnDecl),
    Struct(StructDecl),
    Enum(EnumDecl),
    Invariant(InvariantDecl),
    Impl(ImplDecl),
    Trait(TraitDecl),
    Format(FormatDecl),
    Schedule(ScheduleDecl),
    Spec(SpecDecl),
    Use(UseDecl),
    Mod(ModDecl),
    Const(ConstDecl),
    Evidence(EvidenceDecl),
    Seam(SeamDecl),
    Target(TargetDecl),
    OutOfScope(OutOfScope),
    /// Statements at item level (documentation snippets such as D-C7); the checker places them in
    /// the body of a host function named by the configuration.
    LooseStmts(Vec<Stmt>, Span),
    TypeAlias(Ident, Generics, TypeAst, Span),
    MacroRules(Span),
}

#[derive(Clone, Debug)]
pub struct Block {
    pub stmts: Vec<Stmt>,
    /// Tail expression (no trailing semicolon).
    pub tail: Option<Box<Expr>>,
    pub span: Span,
    pub is_unsafe: bool,
}

#[derive(Clone, Debug)]
pub enum Stmt {
    Let { pat: Pat, ty: Option<TypeAst>, init: Option<Expr>, els: Option<Block>, span: Span },
    Expr(Expr, bool /* has semicolon */),
    Item(Box<Item>),
    Empty,
}

#[derive(Clone, Debug)]
pub struct Pat {
    pub kind: PatKind,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub enum PatKind {
    Wild,
    Rest,
    Ident { name: Ident, mutable: bool, by_ref: bool, sub: Option<Box<Pat>> },
    Lit(Box<Expr>),
    Range(Box<Expr>, Box<Expr>, bool),
    Tuple(Vec<Pat>),
    TupleStruct(Path, Vec<Pat>),
    Struct(Path, Vec<(Ident, Pat)>, bool),
    Path(Path),
    Ref(Box<Pat>, bool),
    Or(Vec<Pat>),
    Slice(Vec<Pat>),
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum BinOp {
    Add,
    Sub,
    Mul,
    Div,
    Rem,
    And,
    Or,
    BitAnd,
    BitOr,
    BitXor,
    Shl,
    Shr,
    Eq,
    Ne,
    Lt,
    Le,
    Gt,
    Ge,
}

impl BinOp {
    pub fn sym(self) -> &'static str {
        use BinOp::*;
        match self {
            Add => "+",
            Sub => "-",
            Mul => "*",
            Div => "/",
            Rem => "%",
            And => "&&",
            Or => "||",
            BitAnd => "&",
            BitOr => "|",
            BitXor => "^",
            Shl => "<<",
            Shr => ">>",
            Eq => "==",
            Ne => "!=",
            Lt => "<",
            Le => "<=",
            Gt => ">",
            Ge => ">=",
        }
    }
    pub fn name(self) -> &'static str {
        use BinOp::*;
        match self {
            Add => "add",
            Sub => "sub",
            Mul => "mul",
            Div => "div",
            Rem => "rem",
            And => "and",
            Or => "or",
            BitAnd => "bitand",
            BitOr => "bitor",
            BitXor => "bitxor",
            Shl => "shl",
            Shr => "shr",
            Eq => "eq",
            Ne => "ne",
            Lt => "lt",
            Le => "le",
            Gt => "gt",
            Ge => "ge",
        }
    }
    pub fn is_cmp(self) -> bool {
        matches!(self, BinOp::Eq | BinOp::Ne | BinOp::Lt | BinOp::Le | BinOp::Gt | BinOp::Ge)
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum UnOp {
    Neg,
    Not,
    Deref,
}

#[derive(Clone, Debug)]
pub enum Lit {
    Int(u128, Option<String>),
    Float(String, Option<String>),
    Bool(bool),
    Str(String),
    Char(char),
}

#[derive(Clone, Debug)]
pub struct Expr {
    pub kind: ExprKind,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub struct MatchArm {
    pub pat: Pat,
    pub guard: Option<Expr>,
    pub body: Expr,
    pub span: Span,
}

#[derive(Clone, Debug)]
pub struct ClosureParam {
    pub pat: Pat,
    pub ty: Option<TypeAst>,
}

#[derive(Clone, Debug)]
pub enum MacroArgs {
    Exprs(Vec<Expr>),
    /// `vec![x; n]`
    Repeat(Box<Expr>, Box<Expr>),
    /// `matches!(e, pat)`
    Matches(Box<Expr>, Pat),
    /// Unparsed (user macros, which are Dc anyway)
    Raw,
}

#[derive(Clone, Debug)]
pub enum ExprKind {
    Lit(Lit),
    Path(Path),
    Unary(UnOp, Box<Expr>),
    Ref { mutable: bool, expr: Box<Expr> },
    Binary(BinOp, Box<Expr>, Box<Expr>),
    Assign(Box<Expr>, Box<Expr>),
    AssignOp(BinOp, Box<Expr>, Box<Expr>),
    Cast(Box<Expr>, TypeAst),
    Call(Box<Expr>, Vec<Expr>),
    MethodCall { recv: Box<Expr>, method: Ident, generics: Option<Vec<GenericArg>>, args: Vec<Expr> },
    Field(Box<Expr>, Ident),
    TupleField(Box<Expr>, u32, Span),
    Index(Box<Expr>, Box<Expr>),
    Range(Option<Box<Expr>>, Option<Box<Expr>>, bool),
    Try(Box<Expr>),
    Tuple(Vec<Expr>),
    Array(Vec<Expr>),
    ArrayRepeat(Box<Expr>, Box<Expr>),
    Struct { path: Path, fields: Vec<(Ident, Expr)>, base: Option<Box<Expr>> },
    Block(Block),
    If(Box<Expr>, Block, Option<Box<Expr>>),
    /// `if let PAT = e { } else { }`
    IfLet(Pat, Box<Expr>, Block, Option<Box<Expr>>),
    Match(Box<Expr>, Vec<MatchArm>),
    While(Option<String>, Box<Expr>, Block),
    WhileLet(Option<String>, Pat, Box<Expr>, Block),
    Loop(Option<String>, Block),
    For { label: Option<String>, par: bool, pat: Pat, iter: Box<Expr>, body: Block },
    Break(Option<String>, Option<Box<Expr>>),
    Continue(Option<String>),
    Return(Option<Box<Expr>>),
    Closure { is_move: bool, params: Vec<ClosureParam>, ret: Option<TypeAst>, body: Box<Expr> },
    Macro { name: Ident, args: MacroArgs },
    Det { by: Path, body: Block },
    Ellipsis,
    /// `async` blocks, `.await`, `unsafe` blocks are parsed so they can be rejected by name.
    Async(Box<Expr>),
    Await(Box<Expr>),
    /// out-of-scope expression keyword (`comptime { }`)
    OutOfScope(String, Box<Expr>),
    Paren(Box<Expr>),
    Let(Pat, Box<Expr>),
}
