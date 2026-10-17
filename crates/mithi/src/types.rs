//! Semantic types.

use std::fmt;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum IntTy {
    I8,
    I16,
    I32,
    I64,
    I128,
    Isize,
    U8,
    U16,
    U32,
    U64,
    U128,
    Usize,
}

impl IntTy {
    pub fn from_name(s: &str) -> Option<IntTy> {
        Some(match s {
            "i8" => IntTy::I8,
            "i16" => IntTy::I16,
            "i32" => IntTy::I32,
            "i64" => IntTy::I64,
            "i128" => IntTy::I128,
            "isize" => IntTy::Isize,
            "u8" => IntTy::U8,
            "u16" => IntTy::U16,
            "u32" => IntTy::U32,
            "u64" => IntTy::U64,
            "u128" => IntTy::U128,
            "usize" => IntTy::Usize,
            _ => return None,
        })
    }
    pub fn name(self) -> &'static str {
        match self {
            IntTy::I8 => "i8",
            IntTy::I16 => "i16",
            IntTy::I32 => "i32",
            IntTy::I64 => "i64",
            IntTy::I128 => "i128",
            IntTy::Isize => "isize",
            IntTy::U8 => "u8",
            IntTy::U16 => "u16",
            IntTy::U32 => "u32",
            IntTy::U64 => "u64",
            IntTy::U128 => "u128",
            IntTy::Usize => "usize",
        }
    }
    pub fn signed(self) -> bool {
        matches!(self, IntTy::I8 | IntTy::I16 | IntTy::I32 | IntTy::I64 | IntTy::I128 | IntTy::Isize)
    }
    /// Bit width; isize/usize are 64 (x86_64 is the only X1 target).
    pub fn bits(self) -> u32 {
        match self {
            IntTy::I8 | IntTy::U8 => 8,
            IntTy::I16 | IntTy::U16 => 16,
            IntTy::I32 | IntTy::U32 => 32,
            IntTy::I64 | IntTy::U64 | IntTy::Isize | IntTy::Usize => 64,
            IntTy::I128 | IntTy::U128 => 128,
        }
    }
    pub fn min_val(self) -> i128 {
        if self.signed() {
            if self.bits() == 128 {
                i128::MIN
            } else {
                -(1i128 << (self.bits() - 1))
            }
        } else {
            0
        }
    }
    /// Maximum value; u128::MAX does not fit i128 and is clamped (mithi uses i128 arithmetic).
    pub fn max_val(self) -> i128 {
        if self.signed() {
            if self.bits() == 128 {
                i128::MAX
            } else {
                (1i128 << (self.bits() - 1)) - 1
            }
        } else if self.bits() == 128 {
            i128::MAX
        } else {
            (1i128 << self.bits()) - 1
        }
    }
    pub fn all() -> [IntTy; 12] {
        use IntTy::*;
        [I8, I16, I32, I64, I128, Isize, U8, U16, U32, U64, U128, Usize]
    }
}

pub type AdtId = u32;
pub type TraitId = u32;
pub type FnId = u32;
pub type ImplId = u32;
pub type ClosureId = u32;

#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum Ty {
    Int(IntTy),
    F32,
    F64,
    F16,
    Bf16,
    Bool,
    Char,
    Str,
    Unit,
    Never,
    Tuple(Vec<Ty>),
    /// element type and length (a `Const` or a `Param`)
    Array(Box<Ty>, Box<Ty>),
    Slice(Box<Ty>),
    Ref(bool, Box<Ty>),
    Adt(AdtId, Vec<Ty>),
    /// generic parameter, by index into the definition's generic list
    Param(u32),
    Infer(u32),
    IntVar(u32),
    FloatVar(u32),
    Closure(ClosureId),
    Const(i128),
    /// projection `<T as Trait>::Name`
    Assoc(Box<Ty>, TraitId, String),
    /// `impl Bounds` in return position (opaque)
    Opaque(Vec<(TraitId, Vec<(String, Ty)>)>),
    FnPtr(Vec<Ty>, Box<Ty>),
    Error,
}

impl Ty {
    pub fn usize() -> Ty {
        Ty::Int(IntTy::Usize)
    }
    pub fn is_float(&self) -> bool {
        matches!(self, Ty::F32 | Ty::F64 | Ty::FloatVar(_))
    }
    pub fn is_int(&self) -> bool {
        matches!(self, Ty::Int(_) | Ty::IntVar(_))
    }
    pub fn is_numeric(&self) -> bool {
        self.is_int() || self.is_float()
    }
    pub fn is_ref(&self) -> bool {
        matches!(self, Ty::Ref(..))
    }
    pub fn deref_ty(&self) -> Option<&Ty> {
        match self {
            Ty::Ref(_, t) => Some(t),
            _ => None,
        }
    }
    pub fn strip_refs(&self) -> &Ty {
        let mut t = self;
        while let Ty::Ref(_, i) = t {
            t = i;
        }
        t
    }
    pub fn subst(&self, s: &[Ty]) -> Ty {
        match self {
            Ty::Param(i) => s.get(*i as usize).cloned().unwrap_or(Ty::Param(*i)),
            Ty::Tuple(v) => Ty::Tuple(v.iter().map(|t| t.subst(s)).collect()),
            Ty::Array(t, n) => Ty::Array(Box::new(t.subst(s)), Box::new(n.subst(s))),
            Ty::Slice(t) => Ty::Slice(Box::new(t.subst(s))),
            Ty::Ref(m, t) => Ty::Ref(*m, Box::new(t.subst(s))),
            Ty::Adt(a, v) => Ty::Adt(*a, v.iter().map(|t| t.subst(s)).collect()),
            Ty::Assoc(t, tr, n) => Ty::Assoc(Box::new(t.subst(s)), *tr, n.clone()),
            Ty::FnPtr(p, r) => Ty::FnPtr(p.iter().map(|t| t.subst(s)).collect(), Box::new(r.subst(s))),
            Ty::Opaque(b) => Ty::Opaque(b.iter().map(|(t, bs)| (*t, bs.iter().map(|(n, x)| (n.clone(), x.subst(s))).collect())).collect()),
            _ => self.clone(),
        }
    }
    pub fn walk(&self, f: &mut dyn FnMut(&Ty)) {
        f(self);
        match self {
            Ty::Tuple(v) | Ty::Adt(_, v) => v.iter().for_each(|t| t.walk(f)),
            Ty::Array(t, n) => {
                t.walk(f);
                n.walk(f);
            }
            Ty::Slice(t) | Ty::Ref(_, t) => t.walk(f),
            Ty::Assoc(t, _, _) => t.walk(f),
            Ty::FnPtr(p, r) => {
                p.iter().for_each(|t| t.walk(f));
                r.walk(f);
            }
            Ty::Opaque(b) => b.iter().for_each(|(_, bs)| bs.iter().for_each(|(_, t)| t.walk(f))),
            _ => {}
        }
    }
    pub fn has_infer(&self) -> bool {
        let mut h = false;
        self.walk(&mut |t| {
            if matches!(t, Ty::Infer(_) | Ty::IntVar(_) | Ty::FloatVar(_)) {
                h = true
            }
        });
        h
    }
    pub fn has_param(&self) -> bool {
        let mut h = false;
        self.walk(&mut |t| {
            if matches!(t, Ty::Param(_)) {
                h = true
            }
        });
        h
    }
    pub fn mentions_ref(&self) -> bool {
        let mut h = false;
        self.walk(&mut |t| {
            if matches!(t, Ty::Ref(..)) {
                h = true
            }
        });
        h
    }
}

/// Display needs names, which live in the program; this is a fallback.
impl fmt::Display for Ty {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Ty::Int(i) => write!(f, "{}", i.name()),
            Ty::F32 => write!(f, "f32"),
            Ty::F64 => write!(f, "f64"),
            Ty::F16 => write!(f, "f16"),
            Ty::Bf16 => write!(f, "bf16"),
            Ty::Bool => write!(f, "bool"),
            Ty::Char => write!(f, "char"),
            Ty::Str => write!(f, "str"),
            Ty::Unit => write!(f, "()"),
            Ty::Never => write!(f, "!"),
            Ty::Tuple(v) => {
                write!(f, "(")?;
                for (i, t) in v.iter().enumerate() {
                    if i > 0 {
                        write!(f, ", ")?;
                    }
                    write!(f, "{t}")?;
                }
                if v.len() == 1 {
                    write!(f, ",")?;
                }
                write!(f, ")")
            }
            Ty::Array(t, n) => write!(f, "[{t}; {n}]"),
            Ty::Slice(t) => write!(f, "[{t}]"),
            Ty::Ref(m, t) => write!(f, "&{}{t}", if *m { "mut " } else { "" }),
            Ty::Adt(a, v) => {
                write!(f, "adt#{a}")?;
                if !v.is_empty() {
                    write!(f, "<")?;
                    for (i, t) in v.iter().enumerate() {
                        if i > 0 {
                            write!(f, ", ")?;
                        }
                        write!(f, "{t}")?;
                    }
                    write!(f, ">")?;
                }
                Ok(())
            }
            Ty::Param(i) => write!(f, "T{i}"),
            Ty::Infer(i) => write!(f, "?{i}"),
            Ty::IntVar(_) => write!(f, "{{integer}}"),
            Ty::FloatVar(_) => write!(f, "{{float}}"),
            Ty::Closure(c) => write!(f, "closure#{c}"),
            Ty::Const(n) => write!(f, "{n}"),
            Ty::Assoc(t, _, n) => write!(f, "<{t}>::{n}"),
            Ty::Opaque(_) => write!(f, "impl Trait"),
            Ty::FnPtr(..) => write!(f, "fn(..)"),
            Ty::Error => write!(f, "{{error}}"),
        }
    }
}
