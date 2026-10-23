//! Trap sites, obligations and T2 (note section 5.10).
//!
//! T2 here is mithi's own decision procedure for the integer side conditions the note lists:
//! overflow, bounds, ranges, contracts over integers, indices and lengths. It works over SSA
//! versions (F-44): every value is a polynomial over atoms (parameters, fields, lengths, call
//! results); facts are polynomial inequalities. A goal is proved by interval reasoning, then by
//! Fourier–Motzkin elimination over the relevant facts, with degree-2 products of facts and
//! non-negative atoms added for nonlinear goals (`(r + 1) * bpr <= rows * bpr`, OP-10). Loops are
//! not given invariants (DR-012): a loop with a constant trip count up to 64 is unrolled; any other
//! loop havocs what it writes. Undischarged sites stay runtime asserts (may_trap) outside kernels
//! and are E-KERNEL-OBLIGATION in kernels.

use super::*;
use crate::ast::{BinOp, UnOp};
use crate::diag::Diag;
use crate::program::FnDef;
use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};

type AtomId = u32;

#[derive(Clone, PartialEq, Eq, PartialOrd, Ord, Hash, Debug)]
struct Mono(Vec<AtomId>);

#[derive(Clone, PartialEq, Eq, Hash, Debug, Default)]
pub struct Poly {
    t: BTreeMap<Mono, i128>,
}

impl Poly {
    fn c(v: i128) -> Poly {
        let mut t = BTreeMap::new();
        if v != 0 {
            t.insert(Mono(vec![]), v);
        }
        Poly { t }
    }
    fn atom(a: AtomId) -> Poly {
        let mut t = BTreeMap::new();
        t.insert(Mono(vec![a]), 1);
        Poly { t }
    }
    fn konst(&self) -> Option<i128> {
        if self.t.is_empty() {
            return Some(0);
        }
        if self.t.len() == 1 {
            if let Some(v) = self.t.get(&Mono(vec![])) {
                return Some(*v);
            }
        }
        None
    }
    fn add(&self, o: &Poly) -> Option<Poly> {
        let mut t = self.t.clone();
        for (m, v) in &o.t {
            let e = t.entry(m.clone()).or_insert(0);
            *e = e.checked_add(*v)?;
            if *e == 0 {
                t.remove(m);
            }
        }
        Some(Poly { t })
    }
    fn scale(&self, k: i128) -> Option<Poly> {
        if k == 0 {
            return Some(Poly::default());
        }
        let mut t = BTreeMap::new();
        for (m, v) in &self.t {
            t.insert(m.clone(), v.checked_mul(k)?);
        }
        Some(Poly { t })
    }
    fn neg(&self) -> Option<Poly> {
        self.scale(-1)
    }
    fn sub(&self, o: &Poly) -> Option<Poly> {
        self.add(&o.neg()?)
    }
    fn mul(&self, o: &Poly) -> Option<Poly> {
        let mut out = Poly::default();
        for (m1, v1) in &self.t {
            for (m2, v2) in &o.t {
                let mut m = m1.0.clone();
                m.extend_from_slice(&m2.0);
                m.sort();
                if m.len() > 2 {
                    return None;
                }
                let v = v1.checked_mul(*v2)?;
                out = out.add(&Poly { t: [(Mono(m), v)].into_iter().collect() })?;
            }
        }
        Some(out)
    }
    fn degree(&self) -> usize {
        self.t.keys().map(|m| m.0.len()).max().unwrap_or(0)
    }
    fn atoms(&self) -> HashSet<AtomId> {
        self.t.keys().flat_map(|m| m.0.iter().copied()).collect()
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Hash)]
enum Fact {
    Ge(Poly),
    Eq(Poly),
    /// poly != 0 (used by interval edges and by `!=` goals; not by Fourier–Motzkin)
    Ne(Poly),
}

#[derive(Clone, Debug, Default)]
struct Cond {
    /// facts the condition states when true (goals, when the condition is asserted)
    pos: Option<Vec<Fact>>,
    neg: Option<Vec<Fact>>,
    /// facts that hold whenever the condition is true, but are not part of what it states: the
    /// `ensures` of calls in a short-circuit operand evaluated only on that outcome
    pos_side: Vec<Fact>,
    neg_side: Vec<Fact>,
}

#[derive(Clone, Debug)]
enum Sym {
    Int(Poly),
    Bool(Cond),
    Ref(PSym),
    Opaque,
}

#[derive(Clone, Debug, PartialEq)]
struct PSym {
    root: String,
    path: String,
    len: Option<Poly>,
    /// footprint key when this reference came from a footprinted projection
    proj: Option<String>,
}

/// The per-path state. Atom intervals and atom equalities are path facts like any other, so they
/// live here and are restored with the rest of the state at branches and loops (review
/// 2026-10-16: kept in `Ev`, a then-branch condition leaked into the else-branch).
#[derive(Clone)]
struct State {
    env: HashMap<LocalId, Sym>,
    facts: Vec<Fact>,
    /// the same facts, for de-duplication
    fset: HashSet<Fact>,
    /// fact indices by the atoms they mention (as canonical when added): `prove_ge` collects the
    /// facts relevant to a goal without scanning all of them (review 2026-10-16: time grew faster
    /// than quadratically in a body's length)
    fidx: HashMap<AtomId, Vec<u32>>,
    ver: HashMap<String, u32>,
    /// tightened intervals of class roots (absent: the atom's base interval)
    iv: BTreeMap<AtomId, (i128, i128)>,
    /// union-find parent links of atom equalities (absent: a root)
    uf: BTreeMap<AtomId, AtomId>,
    dead: bool,
}

impl State {
    fn new() -> State {
        State { env: HashMap::new(), facts: vec![], fset: HashSet::new(), fidx: HashMap::new(), ver: HashMap::new(), iv: BTreeMap::new(), uf: BTreeMap::new(), dead: false }
    }
}

pub struct T2Result {
    /// a footprinted projection: does its result target exactly the declared footprint?
    pub footprint_ok: Option<bool>,
    pub sites: Vec<(Span, String, bool)>,
    pub covers: Vec<(LoopId, LocalId)>,
    pub row_covers: Vec<(LoopId, LocalId)>,
}

#[allow(dead_code)]
struct Ev<'a> {
    c: &'a Checked,
    fid: FnId,
    body: &'a Body,
    /// (key, base interval): the base interval depends only on the key (a type range or a field
    /// range), never on the path; path-dependent tightening lives in `State::iv`
    atoms: Vec<(String, i128, i128)>,
    atom_keys: HashMap<String, AtomId>,
    st: State,
    sites: BTreeMap<(Span, String), bool>,
    callk: u32,
    budget: u32,
    /// the evaluation budget ran out: sites after that point were not visited
    exhausted: bool,
    is_kernel: bool,
    covers: Vec<(LoopId, LocalId)>,
    row_covers: Vec<(LoopId, LocalId)>,
    /// set while evaluating a contract of another function: no sites are recorded
    quiet: u32,
    /// locals that a reference, a `ref mut` binding or a by-mut closure capture may write (F-44)
    addr_taken: BTreeSet<LocalId>,
    /// locals captured by mut by a closure created in this body
    mut_captured: BTreeSet<LocalId>,
}

const ISIZE_MAX: i128 = i64::MAX as i128;

fn ty_range(t: &Ty) -> (i128, i128) {
    match t {
        Ty::Int(i) => (i.min_val(), i.max_val()),
        Ty::Bool => (0, 1),
        Ty::Char => (0, 0x10FFFF),
        _ => (i128::MIN / 4, i128::MAX / 4),
    }
}

impl<'a> Ev<'a> {
    fn new(c: &'a Checked, fid: FnId, body: &'a Body) -> Ev<'a> {
        let (addr_taken, mut_captured) = addr_taken_of(c, body);
        Ev {
            c,
            fid,
            body,
            atoms: vec![],
            atom_keys: HashMap::new(),
            st: State::new(),
            sites: BTreeMap::new(),
            callk: 0,
            budget: 20000,
            exhausted: false,
            is_kernel: c.program.fns[fid as usize].kind == FnKind::Kernel,
            covers: vec![],
            row_covers: vec![],
            quiet: 0,
            addr_taken,
            mut_captured,
        }
    }

    // ------------------------------------------------------------ atoms
    fn find(&self, a: AtomId) -> AtomId {
        let mut x = a;
        while let Some(p) = self.st.uf.get(&x) {
            x = *p;
        }
        x
    }
    fn atom_keyed(&mut self, key: &str, lo: i128, hi: i128) -> AtomId {
        if let Some(a) = self.atom_keys.get(key) {
            return *a;
        }
        let id = self.atoms.len() as AtomId;
        self.atoms.push((key.to_string(), lo, hi));
        self.atom_keys.insert(key.to_string(), id);
        id
    }
    fn base_iv(&self, a: AtomId) -> (i128, i128) {
        (self.atoms[a as usize].1, self.atoms[a as usize].2)
    }
    fn fresh(&mut self, hint: &str, lo: i128, hi: i128) -> AtomId {
        self.callk += 1;
        let k = format!("{hint}#{}", self.callk);
        self.atom_keyed(&k, lo, hi)
    }
    fn fresh_ty(&mut self, hint: &str, t: &Ty) -> Poly {
        let (lo, hi) = ty_range(t);
        Poly::atom(self.fresh(hint, lo, hi))
    }
    fn iv(&self, a: AtomId) -> (i128, i128) {
        let r = self.find(a);
        match self.st.iv.get(&r) {
            Some(x) => *x,
            None => self.base_iv(r),
        }
    }
    fn set_iv(&mut self, a: AtomId, lo: i128, hi: i128) {
        let r = self.find(a);
        let (l0, h0) = self.iv(r);
        self.st.iv.insert(r, (l0.max(lo), h0.min(hi)));
    }
    fn union(&mut self, a: AtomId, b: AtomId) {
        let (ra, rb) = (self.find(a), self.find(b));
        if ra == rb {
            return;
        }
        let (la, ha) = self.iv(ra);
        let (lb, hb) = self.iv(rb);
        self.st.uf.insert(rb, ra);
        self.st.iv.insert(ra, (la.max(lb), ha.min(hb)));
    }
    /// The interval of `a` in state `s` (for joins).
    fn iv_in(&self, s: &State, a: AtomId) -> (i128, i128) {
        let mut x = a;
        while let Some(p) = s.uf.get(&x) {
            x = *p;
        }
        match s.iv.get(&x) {
            Some(v) => *v,
            None => self.base_iv(x),
        }
    }
    fn canon(&self, p: &Poly) -> Poly {
        self.canon_in(&self.st, p)
    }
    fn canon_in(&self, s: &State, p: &Poly) -> Poly {
        if s.uf.is_empty() {
            return p.clone();
        }
        let mut out = Poly::default();
        for (m, v) in &p.t {
            let mut mm: Vec<AtomId> = m
                .0
                .iter()
                .map(|a| {
                    let mut x = *a;
                    while let Some(p) = s.uf.get(&x) {
                        x = *p;
                    }
                    x
                })
                .collect();
            mm.sort();
            out = out.add(&Poly { t: [(Mono(mm), *v)].into_iter().collect() }).unwrap_or_default();
        }
        out
    }
    fn mono_iv_in(&self, s: &State, m: &Mono) -> (i128, i128) {
        let mut lo = 1i128;
        let mut hi = 1i128;
        for a in &m.0 {
            let (l, h) = self.iv_in(s, *a);
            let c = [lo.saturating_mul(l), lo.saturating_mul(h), hi.saturating_mul(l), hi.saturating_mul(h)];
            lo = *c.iter().min().unwrap();
            hi = *c.iter().max().unwrap();
        }
        (lo, hi)
    }
    fn poly_iv(&self, p: &Poly) -> (i128, i128) {
        self.poly_iv_in(&self.st, p)
    }
    /// The interval of a polynomial in state `s` (a join computes each side's in its own state).
    fn poly_iv_in(&self, s: &State, p: &Poly) -> (i128, i128) {
        let p = self.canon_in(s, p);
        let mut lo = 0i128;
        let mut hi = 0i128;
        for (m, v) in &p.t {
            let (l, h) = self.mono_iv_in(s, m);
            let (a, b) = (l.saturating_mul(*v), h.saturating_mul(*v));
            lo = lo.saturating_add(a.min(b));
            hi = hi.saturating_add(a.max(b));
        }
        (lo, hi)
    }

    // ------------------------------------------------------------ facts and proving
    /// Append a fact to the path state (its index by atom too).
    fn push_fact(&mut self, f: Fact) {
        if !self.st.fset.insert(f.clone()) {
            return;
        }
        let idx = self.st.facts.len() as u32;
        let p = match &f {
            Fact::Ge(p) | Fact::Eq(p) | Fact::Ne(p) => p,
        };
        for m in p.t.keys() {
            for a in &m.0 {
                let v = self.st.fidx.entry(*a).or_default();
                if v.last() != Some(&idx) {
                    v.push(idx);
                }
            }
        }
        self.st.facts.push(f);
    }

    fn canon_fact(&self, f: &Fact) -> Fact {
        match f {
            Fact::Ge(p) => Fact::Ge(self.canon(p)),
            Fact::Eq(p) => Fact::Eq(self.canon(p)),
            Fact::Ne(p) => Fact::Ne(self.canon(p)),
        }
    }

    fn add_fact(&mut self, f: Fact) {
        let f = self.canon_fact(&f);
        match &f {
            Fact::Ne(p) => {
                // atom != const at an end of the atom's interval moves that end
                let lin: Vec<(&Mono, &i128)> = p.t.iter().filter(|(m, _)| !m.0.is_empty()).collect();
                let k = p.t.get(&Mono(vec![])).copied().unwrap_or(0);
                if lin.len() == 1 && lin[0].0 .0.len() == 1 && lin[0].1.abs() == 1 {
                    let a = lin[0].0 .0[0];
                    let v = -k * lin[0].1;
                    let (lo, hi) = self.iv(a);
                    if lo == v {
                        self.set_iv(a, v.saturating_add(1), hi);
                    } else if hi == v {
                        self.set_iv(a, lo, v.saturating_sub(1));
                    }
                }
            }
            Fact::Eq(p) => {
                // atom == atom: union; atom == const: interval
                let lin: Vec<(&Mono, &i128)> = p.t.iter().filter(|(m, _)| !m.0.is_empty()).collect();
                let k = p.t.get(&Mono(vec![])).copied().unwrap_or(0);
                if lin.len() == 2 && lin[0].0 .0.len() == 1 && lin[1].0 .0.len() == 1 && k == 0 && *lin[0].1 == -*lin[1].1 && lin[0].1.abs() == 1 {
                    let (a, b) = (lin[0].0 .0[0], lin[1].0 .0[0]);
                    self.union(a, b);
                    // kept in the list too, so that a short-circuit operand's facts can be
                    // replayed in the state that continues (eval_binary And/Or)
                    self.push_fact(f);
                    return;
                }
                if lin.len() == 1 && lin[0].0 .0.len() == 1 && lin[0].1.abs() == 1 {
                    let a = lin[0].0 .0[0];
                    let v = -k * lin[0].1;
                    self.set_iv(a, v, v);
                }
            }
            Fact::Ge(p) => {
                let lin: Vec<(&Mono, &i128)> = p.t.iter().filter(|(m, _)| !m.0.is_empty()).collect();
                let k = p.t.get(&Mono(vec![])).copied().unwrap_or(0);
                if lin.len() == 1 && lin[0].0 .0.len() == 1 {
                    let a = lin[0].0 .0[0];
                    let c = *lin[0].1;
                    // c*a + k >= 0
                    if c > 0 {
                        let lo = div_ceil(-k, c);
                        self.set_iv(a, lo, i128::MAX);
                    } else if c < 0 {
                        let hi = div_floor(k, -c);
                        self.set_iv(a, i128::MIN, hi);
                    }
                }
            }
        }
        self.push_fact(f);
    }

    fn add_cond(&mut self, c: &Cond, positive: bool) {
        let side = if positive { c.pos_side.clone() } else { c.neg_side.clone() };
        for f in side {
            self.add_fact(f);
        }
        let fs = if positive { c.pos.clone() } else { c.neg.clone() };
        if let Some(fs) = fs {
            for f in fs {
                self.add_fact(f);
            }
        }
    }

    fn prove(&mut self, goal: &Fact) -> bool {
        match goal {
            Fact::Eq(p) => {
                let p = self.canon(p);
                if p.t.is_empty() {
                    return true;
                }
                self.prove_ge(&p) && self.prove_ge(&p.neg().unwrap_or_default())
            }
            Fact::Ge(p) => {
                let p = self.canon(p);
                self.prove_ge(&p)
            }
            Fact::Ne(p) => {
                let p = self.canon(p);
                if let Some(k) = p.konst() {
                    return k != 0;
                }
                let (lo, hi) = self.poly_iv(&p);
                if lo > 0 || hi < 0 {
                    return true;
                }
                let np = p.neg().unwrap_or_default();
                if self.st.facts.iter().any(|f| matches!(f, Fact::Ne(q) if { let q = self.canon(q); q == p || q == np })) {
                    return true;
                }
                let up = p.add(&Poly::c(-1)).unwrap_or_default();
                let dn = np.add(&Poly::c(-1)).unwrap_or_default();
                self.prove_ge(&up) || self.prove_ge(&dn)
            }
        }
    }

    fn prove_ge(&mut self, p: &Poly) -> bool {
        if let Some(k) = p.konst() {
            return k >= 0;
        }
        let (lo, _) = self.poly_iv(p);
        if lo >= 0 {
            return true;
        }
        // Fourier–Motzkin over the relevant facts: those reachable from the goal's atoms through
        // shared atoms, newest first, found through the atom index (facts are stored canonical;
        // they need re-canonicalising only after later unions)
        let mut rel: Vec<(Poly, bool)> = vec![];
        let mut want: BTreeSet<AtomId> = p.atoms().into_iter().collect();
        let mut queue: Vec<AtomId> = want.iter().copied().collect();
        let mut used: HashSet<u32> = HashSet::new();
        let uf_members: Vec<(AtomId, AtomId)> = self.st.uf.keys().map(|a| (self.find(*a), *a)).collect();
        'gather: while let Some(a) = queue.pop() {
            let mut keys = vec![a];
            keys.extend(uf_members.iter().filter(|(r, _)| *r == a).map(|(_, m)| *m));
            for k in keys {
                let Some(idxs) = self.st.fidx.get(&k) else { continue };
                for &i in idxs.iter().rev() {
                    if !used.insert(i) {
                        continue;
                    }
                    let f = match self.st.facts.get(i as usize) {
                        Some(f) => f,
                        None => continue,
                    };
                    let f = if self.st.uf.is_empty() { f.clone() } else { self.canon_fact(f) };
                    let (q, eq) = match f {
                        Fact::Ge(q) => (q, false),
                        Fact::Eq(q) => (q, true),
                        Fact::Ne(_) => continue,
                    };
                    for b in q.atoms() {
                        if want.insert(b) {
                            queue.push(b);
                        }
                    }
                    rel.push((q, eq));
                    if rel.len() > 64 {
                        break 'gather;
                    }
                }
            }
        }
        // interval bounds of the atoms involved
        let atoms: Vec<AtomId> = want.iter().copied().collect();
        for a in &atoms {
            let (l, h) = self.iv(*a);
            if l > i128::MIN / 8 {
                rel.push((Poly::atom(*a).add(&Poly::c(-l)).unwrap_or_default(), false));
            }
            if h < i128::MAX / 8 {
                rel.push((Poly::c(h).sub(&Poly::atom(*a)).unwrap_or_default(), false));
            }
        }
        // degree-2 augmentation: products of linear facts with non-negative atoms of the goal's
        // monomials
        let mut extra = vec![];
        let nonlinear: Vec<Mono> = p.t.keys().filter(|m| m.0.len() == 2).cloned().collect();
        let mut nl_atoms: BTreeSet<AtomId> = BTreeSet::new();
        for m in &nonlinear {
            for a in &m.0 {
                nl_atoms.insert(*a);
            }
        }
        // also products appearing in equality facts (len == rows * bpr)
        for (q, _) in &rel {
            for m in q.t.keys() {
                if m.0.len() == 2 {
                    for a in &m.0 {
                        nl_atoms.insert(*a);
                    }
                }
            }
        }
        if !nl_atoms.is_empty() {
            for z in nl_atoms.iter() {
                let (lz, _) = self.iv(*z);
                if lz < 0 {
                    continue;
                }
                let zp = Poly::atom(*z).add(&Poly::c(-lz)).unwrap_or_default();
                for (q, eq) in &rel {
                    if q.degree() != 1 {
                        continue;
                    }
                    if !q.atoms().iter().any(|a| nl_atoms.contains(a)) {
                        continue;
                    }
                    if let Some(prod) = q.mul(&zp) {
                        extra.push((prod, *eq));
                    }
                }
            }
        }
        rel.extend(extra);
        // negated goal: -p - 1 >= 0
        let neg = match p.neg().and_then(|x| x.add(&Poly::c(-1))) {
            Some(x) => x,
            None => return false,
        };
        rel.push((neg, false));
        fm_infeasible(rel)
    }

    fn check(&mut self, sp: Span, kind: &str, goal: Option<Fact>) -> bool {
        if self.st.dead {
            return true;
        }
        let ok = match &goal {
            Some(g) => self.prove(g),
            None => false,
        };
        if !ok && self.quiet == 0 && std::env::var("MITHI_T2_DEBUG").is_ok() {
            eprintln!("T2 unproved {kind} at {}: goal {}", self.c.program.sm.snippet(sp), goal.as_ref().map(|g| self.fact_text(g)).unwrap_or("<none>".into()));
            for f in &self.st.facts {
                eprintln!("    fact {}", self.fact_text(f));
            }
        }
        if self.quiet == 0 {
            let e = self.sites.entry((sp, kind.to_string())).or_insert(true);
            *e = *e && ok;
        }
        ok
    }

    fn poly_str(&self, p: &Poly) -> String {
        let p = self.canon(p);
        let mut parts = vec![];
        for (m, v) in &p.t {
            let names: Vec<String> = m.0.iter().map(|a| {
                let (l, h) = self.iv(*a);
                format!("{}[{}..{}]", self.atoms[*a as usize].0, if l < -(1i128 << 70) { "-inf".to_string() } else { l.to_string() }, if h > (1i128 << 70) { "inf".to_string() } else { h.to_string() })
            }).collect();
            parts.push(if names.is_empty() { v.to_string() } else { format!("{v}*{}", names.join("*")) });
        }
        if parts.is_empty() { "0".into() } else { parts.join(" + ") }
    }
    fn fact_text(&self, f: &Fact) -> String {
        match f {
            Fact::Ge(p) => format!("{} >= 0", self.poly_str(p)),
            Fact::Eq(p) => format!("{} == 0", self.poly_str(p)),
            Fact::Ne(p) => format!("{} != 0", self.poly_str(p)),
        }
    }

    fn site_always(&mut self, sp: Span, kind: &str) {
        if self.st.dead || self.quiet > 0 {
            return;
        }
        self.sites.insert((sp, kind.to_string()), false);
    }

    // ------------------------------------------------------------ places
    fn root_ver(&self, root: &str) -> u32 {
        *self.st.ver.get(root).unwrap_or(&0)
    }
    fn bump(&mut self, root: &str) {
        *self.st.ver.entry(root.to_string()).or_insert(0) += 1;
    }
    /// Versions of every prefix of a place: a write to a prefix invalidates reads below it.
    /// Element writes (`p[i] = v`) bump only the element version `E:p`, which lengths ignore.
    fn path_ver(&self, root: &str, path: &str, for_len: bool) -> u32 {
        let mut v: u32 = 0;
        let mut cuts: Vec<usize> = path.char_indices().filter(|(i, ch)| *i > 0 && (*ch == '.' || *ch == '[')).map(|(i, _)| i).collect();
        cuts.insert(0, 0);
        cuts.push(path.len());
        for i in cuts {
            let pre = format!("{root}{}", &path[..i]);
            v = v.wrapping_mul(31).wrapping_add(self.root_ver(&pre));
            if !for_len || i < path.len() {
                v = v.wrapping_mul(37).wrapping_add(self.root_ver(&format!("E:{pre}")));
            }
        }
        v
    }
    fn pkey(&self, ps: &PSym) -> String {
        format!("{}{}#{}", ps.root, ps.path, self.path_ver(&ps.root, &ps.path, false))
    }
    /// Is a place with this root known to be the place it names? A local (`L`), a temporary (`T`)
    /// and the referent of a reference parameter (`*L` of a parameter: caller memory, which no
    /// local of this body aliases) are. Anything reached through another reference (a local
    /// reference whose loan is no longer tracked, a call result, a reference read from a place)
    /// may be any local whose address was taken.
    fn known_root(&self, root: &str) -> bool {
        if root.starts_with('L') || root.starts_with('T') {
            return true;
        }
        if let Some(rest) = root.strip_prefix("*L") {
            if let Ok(l) = rest.parse::<LocalId>() {
                return self.body.params.contains(&l);
            }
        }
        false
    }

    /// A write through an unknown reference: every address-taken local gets a new version (F-44).
    fn havoc_addr_taken(&mut self) {
        let ls: Vec<LocalId> = self.addr_taken.iter().copied().collect();
        for l in ls {
            self.st.env.remove(&l);
            self.bump(&format!("L{l}"));
        }
    }

    /// A call of a closure value: the locals closures capture by mut get new versions (F-44).
    fn havoc_mut_captured(&mut self) {
        let ls: Vec<LocalId> = self.mut_captured.iter().copied().collect();
        for l in ls {
            self.st.env.remove(&l);
            self.bump(&format!("L{l}"));
        }
    }

    /// The writes a call may make through its arguments: a `&mut` argument writes its referent
    /// (only the elements of a slice); an argument that holds a `&mut` some other way, or a `&mut`
    /// whose referent is unknown, may write any address-taken local; a closure argument may be
    /// called and write what closures capture by mut (F-44).
    fn call_writes(&mut self, args: &[TExpr], argv: &[Sym]) {
        let mut havoc = false;
        let mut closures = false;
        for (i, a) in args.iter().enumerate() {
            if ty_mentions_closure(&a.ty) {
                closures = true;
            }
            match &a.ty {
                Ty::Ref(true, inner) => match argv.get(i) {
                    Some(Sym::Ref(ps)) => {
                        if !self.known_root(&ps.root) {
                            havoc = true;
                        }
                        if matches!(**inner, Ty::Slice(_) | Ty::Str) {
                            // a slice cannot change length: only its elements may change
                            self.bump(&format!("E:{}{}", ps.root, ps.path));
                        } else {
                            self.write_place(ps);
                        }
                        if ty_has_mut_ref(inner) {
                            havoc = true;
                        }
                    }
                    _ => havoc = true,
                },
                t if ty_has_mut_ref(t) => havoc = true,
                _ => {}
            }
        }
        if havoc {
            self.havoc_addr_taken();
        }
        if closures {
            self.havoc_mut_captured();
        }
    }

    /// A write to a place: an element write invalidates the elements of its container; any other
    /// write invalidates the place and everything below it. Writing a local drops its SSA value.
    fn write_place(&mut self, ps: &PSym) {
        if !self.known_root(&ps.root) {
            self.havoc_addr_taken();
        }
        if let Some(l) = ps.root.strip_prefix('L').and_then(|r| r.parse::<LocalId>().ok()) {
            self.st.env.remove(&l);
        }
        match ps.path.find('[') {
            Some(cut) => {
                let key = format!("E:{}{}", ps.root, &ps.path[..cut]);
                self.bump(&key);
            }
            None => {
                let key = format!("{}{}", ps.root, ps.path);
                self.bump(&key);
            }
        }
    }

    /// The length of a place of slice, array, Vec or Buf type.
    fn len_of(&mut self, ps: &PSym, t: &Ty) -> Poly {
        if let Some(l) = &ps.len {
            return l.clone();
        }
        match t {
            Ty::Array(_, n) => {
                if let Ty::Const(v) = **n {
                    return Poly::c(v);
                }
            }
            Ty::Ref(_, i) => return self.len_of(ps, i),
            _ => {}
        }
        // lengths change only with whole-place writes and `&mut` calls, not element writes
        let key = format!("len({}{})#{}", ps.root, ps.path, self.path_ver(&ps.root, &ps.path, true));
        let a = self.atom_keyed(&key, 0, ISIZE_MAX);
        Poly::atom(a)
    }

    fn place(&mut self, e: &TExpr) -> PSym {
        match &e.kind {
            TK::Local(l) => {
                // a reference-typed local used as a place is the local itself
                PSym { root: format!("L{l}"), path: String::new(), len: None, proj: None }
            }
            TK::Deref(b) => match self.eval(b) {
                Sym::Ref(ps) => ps,
                _ => {
                    let k = self.fresh("deref", 0, 0);
                    PSym { root: format!("?{k}"), path: String::new(), len: None, proj: None }
                }
            },
            TK::Field(b, i) => {
                let pb = self.place(b);
                let fname = field_name(self.c, &b.ty, *i);
                let mut ps = PSym { root: pb.root, path: format!("{}.{fname}", pb.path), len: None, proj: None };
                ps.len = None;
                ps
            }
            TK::Index(b, i) => {
                let pb = self.place(b);
                let idx = self.eval_int(i);
                let len = self.len_of(&pb, &b.ty);
                let ok_goal = idx.as_ref().and_then(|ix| len.sub(ix).and_then(|d| d.add(&Poly::c(-1))).map(Fact::Ge));
                let ok = self.check(e.span, "idx", ok_goal.clone());
                if let (Some(g), false) = (&ok_goal, ok) {
                    // execution continues only if the check held
                    let g2 = g.clone();
                    self.add_fact(g2);
                } else if let Some(g) = ok_goal {
                    self.add_fact(g);
                }
                let it = idx.map(|p| poly_text(&self.canon(&p))).unwrap_or("?".into());
                PSym { root: pb.root, path: format!("{}[{it}]", pb.path), len: None, proj: None }
            }
            TK::SliceRange { base, lo, hi, inclusive } => {
                let pb = self.place(base);
                let len = self.len_of(&pb, &base.ty);
                let lo_p = match lo {
                    Some(l) => self.eval_int(l),
                    None => Some(Poly::c(0)),
                };
                let mut hi_p = match hi {
                    Some(h) => self.eval_int(h),
                    None => Some(len.clone()),
                };
                if *inclusive {
                    hi_p = hi_p.and_then(|h| h.add(&Poly::c(1)));
                }
                let g1 = match (&lo_p, &hi_p) {
                    (Some(l), Some(h)) => h.sub(l).map(Fact::Ge),
                    _ => None,
                };
                let g2 = hi_p.as_ref().and_then(|h| len.sub(h)).map(Fact::Ge);
                let ok1 = self.check(e.span, "slice", g1.clone());
                let ok2 = self.check(e.span, "slice", g2.clone());
                let _ = (ok1, ok2);
                if let Some(g) = g1 {
                    self.add_fact(g);
                }
                if let Some(g) = g2 {
                    self.add_fact(g);
                }
                let (lt, ht) = (lo_p.as_ref().map(|p| poly_text(&self.canon(p))).unwrap_or("?".into()), hi_p.as_ref().map(|p| poly_text(&self.canon(p))).unwrap_or("?".into()));
                let newlen = match (&lo_p, &hi_p) {
                    (Some(l), Some(h)) => h.sub(l),
                    _ => None,
                };
                PSym { root: pb.root.clone(), path: format!("{}[{lt}..{ht}]", pb.path), len: newlen, proj: None }
            }
            TK::Unsize(b) => self.place(b),
            TK::Call { .. } | TK::TraitCall { .. } => {
                // a call result used as a place (a temporary)
                let _ = self.eval(e);
                let k = self.fresh("tmp", 0, 0);
                PSym { root: format!("T{k}"), path: String::new(), len: None, proj: None }
            }
            _ => {
                let _ = self.eval(e);
                let k = self.fresh("tmp", 0, 0);
                PSym { root: format!("T{k}"), path: String::new(), len: None, proj: None }
            }
        }
    }

    fn read_place_int(&mut self, e: &TExpr) -> Poly {
        // a local integer: its SSA value
        if let TK::Local(l) = &e.kind {
            if let Some(Sym::Int(p)) = self.st.env.get(l) {
                return p.clone();
            }
            let (lo, hi) = ty_range(&e.ty);
            let k = format!("L{l}@{}", self.root_ver(&format!("L{l}")));
            let a = self.atom_keyed(&k, lo, hi);
            let p = Poly::atom(a);
            self.st.env.insert(*l, Sym::Int(p.clone()));
            return p;
        }
        let ps = self.place(e);
        let key = format!("val({})", self.pkey(&ps));
        let (mut lo, mut hi) = ty_range(&e.ty);
        if let Some((rl, rh)) = field_range(self.c, e) {
            lo = lo.max(rl);
            hi = hi.min(rh);
        }
        let a = self.atom_keyed(&key, lo, hi);
        // field ranges hold on every read of an unwritten value
        Poly::atom(a)
    }

    // ------------------------------------------------------------ expressions
    fn eval_int(&mut self, e: &TExpr) -> Option<Poly> {
        match self.eval(e) {
            Sym::Int(p) => Some(p),
            _ => None,
        }
    }

    fn eval_cond(&mut self, e: &TExpr) -> Cond {
        match self.eval(e) {
            Sym::Bool(c) => c,
            _ => Cond::default(),
        }
    }

    fn eval(&mut self, e: &TExpr) -> Sym {
        if self.st.dead {
            return Sym::Opaque;
        }
        if self.budget == 0 {
            // nothing below this node is visited: `analyze` then counts every trap site of the
            // body as undischarged (review 2026-10-16)
            self.exhausted = true;
            return Sym::Opaque;
        }
        self.budget -= 1;
        match &e.kind {
            TK::Lit(LitVal::Int(v)) => {
                if e.ty.is_int() {
                    Sym::Int(Poly::c(*v))
                } else {
                    Sym::Opaque
                }
            }
            TK::Lit(LitVal::Bool(b)) => {
                let contra = Some(vec![Fact::Ge(Poly::c(-1))]);
                if *b {
                    Sym::Bool(Cond { pos: Some(vec![]), neg: contra, ..Default::default() })
                } else {
                    Sym::Bool(Cond { pos: contra, neg: Some(vec![]), ..Default::default() })
                }
            }
            TK::Local(l) => {
                if let Some(s) = self.st.env.get(l) {
                    return s.clone();
                }
                match &e.ty {
                    t if t.is_int() => Sym::Int(self.read_place_int(e)),
                    Ty::Ref(..) => {
                        let s = Sym::Ref(PSym { root: format!("*L{l}"), path: String::new(), len: None, proj: None });
                        self.st.env.insert(*l, s.clone());
                        s
                    }
                    _ => Sym::Opaque,
                }
            }
            TK::Const(cid) => match self.c.program.const_int_value(*cid) {
                Some(v) => Sym::Int(Poly::c(v)),
                None => Sym::Opaque,
            },
            TK::Field(..) | TK::Index(..) | TK::Deref(..) => {
                if e.ty.is_int() || e.ty == Ty::Bool {
                    if e.ty == Ty::Bool {
                        let _ = self.place(e);
                        return Sym::Opaque;
                    }
                    Sym::Int(self.read_place_int(e))
                } else if let Ty::Ref(..) = e.ty {
                    // a reference stored in a place
                    let ps = self.place(e);
                    Sym::Ref(PSym { root: format!("*{}", self.pkey(&ps)), path: String::new(), len: None, proj: None })
                } else {
                    let _ = self.place(e);
                    Sym::Opaque
                }
            }
            TK::SliceRange { .. } => {
                let _ = self.place(e);
                Sym::Opaque
            }
            TK::Borrow(_, p) => {
                let ps = self.place(p);
                Sym::Ref(ps)
            }
            TK::Unsize(b) => match self.eval(b) {
                Sym::Ref(ps) => Sym::Ref(ps),
                other => other,
            },
            TK::Unary(UnOp::Neg, a) => {
                let x = self.eval_int(a);
                if let (Some(x), true) = (&x, e.ty.is_int()) {
                    let r = x.neg();
                    if let Some(r) = &r {
                        let (lo, hi) = ty_range(&e.ty);
                        let g1 = r.sub(&Poly::c(lo)).map(Fact::Ge);
                        let g2 = Poly::c(hi).sub(r).map(Fact::Ge);
                        let ok = self.check(e.span, "ovf(neg)", g1) & self.check(e.span, "ovf(neg)", g2);
                        let _ = ok;
                    }
                    return r.map(|p| self.normalize_int(p, &e.ty)).map(Sym::Int).unwrap_or(Sym::Opaque);
                }
                Sym::Opaque
            }
            TK::Unary(UnOp::Not, a) => match self.eval(a) {
                Sym::Bool(c) => Sym::Bool(Cond { pos: c.neg, neg: c.pos, pos_side: c.neg_side, neg_side: c.pos_side }),
                _ => {
                    if e.ty.is_int() {
                        Sym::Int(self.fresh_ty("not", &e.ty))
                    } else {
                        Sym::Opaque
                    }
                }
            },
            TK::Unary(UnOp::Deref, _) => Sym::Opaque,
            TK::Binary(op, a, b) => self.eval_binary(*op, a, b, e),
            TK::Cast(a) => {
                let x = self.eval(a);
                match (x, &e.ty) {
                    (Sym::Int(p), t) if t.is_int() && a.ty.is_int() => {
                        let (lo, hi) = ty_range(t);
                        let (pl, ph) = self.poly_iv(&p);
                        if pl >= lo && ph <= hi {
                            Sym::Int(p)
                        } else {
                            Sym::Int(self.fresh_ty("cast", t))
                        }
                    }
                    (_, t) if t.is_int() => Sym::Int(self.fresh_ty("cast", t)),
                    _ => Sym::Opaque,
                }
            }
            TK::Assign(place, rhs) => {
                let v = self.eval(rhs);
                self.assign(place, v);
                Sym::Opaque
            }
            TK::AssignOp(op, place, rhs) => {
                // the right operand first (F-54), then the place
                let r = self.eval(rhs);
                let cur = if place.ty.is_int() { Sym::Int(self.read_place_int(place)) } else { Sym::Opaque };
                let v = match (cur, r) {
                    (x, y) if place.ty.is_int() && matches!(op, BinOp::Shl | BinOp::Shr) => self.shift(*op, x, y, &place.ty, e.span),
                    (Sym::Int(x), Sym::Int(y)) => self.arith(*op, x, y, &place.ty, e.span),
                    _ => {
                        if place.ty.is_int() {
                            // a trap-capable operator on unknown operands is an undischarged site
                            match op {
                                BinOp::Add | BinOp::Sub | BinOp::Mul => {
                                    self.check(e.span, &format!("ovf({})", op.name()), None);
                                }
                                BinOp::Div | BinOp::Rem => {
                                    self.check(e.span, "div0", None);
                                }
                                _ => {}
                            }
                            Sym::Int(self.fresh_ty("op", &place.ty))
                        } else {
                            Sym::Opaque
                        }
                    }
                };
                self.assign(place, v);
                Sym::Opaque
            }
            TK::Call { f, args, .. } => self.eval_call(*f, args, e),
            TK::TraitCall { args, decl, .. } => {
                let mut argv = vec![];
                for a in args {
                    argv.push(self.eval(a));
                }
                let _ = decl;
                self.call_writes(args, &argv);
                if e.ty.is_int() {
                    Sym::Int(self.fresh_ty("tcall", &e.ty))
                } else {
                    Sym::Opaque
                }
            }
            TK::CallValue(f, args) => {
                self.eval(f);
                let mut argv = vec![];
                for a in args {
                    argv.push(self.eval(a));
                }
                self.call_writes(args, &argv);
                // the closure (or a value holding one) may write what closures capture by mut,
                // or any address-taken local through a captured reference (F-44)
                self.havoc_mut_captured();
                self.havoc_addr_taken();
                if e.ty.is_int() {
                    Sym::Int(self.fresh_ty("ccall", &e.ty))
                } else {
                    Sym::Opaque
                }
            }
            TK::Closure(_) | TK::FnRef(..) => Sym::Opaque,
            TK::Ctor { adt, fields, .. } => {
                for f in fields {
                    self.eval(f);
                }
                self.ctor_checks(*adt, e);
                Sym::Opaque
            }
            TK::CtorUpdate { fields, base, adt, .. } => {
                for (_, f) in fields {
                    self.eval(f);
                }
                self.eval(base);
                self.ctor_checks(*adt, e);
                Sym::Opaque
            }
            TK::Tuple(v) | TK::Array(v) => {
                for x in v {
                    self.eval(x);
                }
                Sym::Opaque
            }
            TK::Repeat(x, _) => {
                self.eval(x);
                Sym::Opaque
            }
            TK::Block(stmts, tail) => {
                for s in stmts {
                    match s {
                        TStmt::Let { pat, init, els, .. } => {
                            let v = match init {
                                Some(i) => self.eval(i),
                                None => Sym::Opaque,
                            };
                            if let Some(el) = els {
                                let saved = self.st.clone();
                                self.eval(el);
                                self.st = saved;
                            }
                            self.bind_pat(pat, v);
                        }
                        TStmt::Expr(x) => {
                            self.eval(x);
                            if matches!(x.ty, Ty::Never) {
                                self.st.dead = true;
                            }
                        }
                    }
                    if self.st.dead {
                        return Sym::Opaque;
                    }
                }
                match tail {
                    Some(t) => {
                        let v = self.eval(t);
                        if matches!(t.ty, Ty::Never) {
                            self.st.dead = true;
                        }
                        v
                    }
                    None => Sym::Opaque,
                }
            }
            TK::If(c, t, el) => {
                let cond = self.eval_cond(c);
                let s0 = self.st.clone();
                self.add_cond(&cond, true);
                let v1 = self.eval(t);
                let s1 = std::mem::replace(&mut self.st, s0);
                self.add_cond(&cond, false);
                let v2 = match el {
                    Some(x) => self.eval(x),
                    None => Sym::Opaque,
                };
                let s2 = std::mem::replace(&mut self.st, s1.clone());
                self.join(s1, s2, &v1, &v2, &e.ty)
            }
            TK::Match(s, arms) => {
                let _ = self.eval(s);
                let s0 = self.st.clone();
                let mut outs: Vec<(State, Sym)> = vec![];
                for a in arms {
                    self.st = s0.clone();
                    self.bind_pat(&a.pat, Sym::Opaque);
                    if let Some(g) = &a.guard {
                        let c = self.eval_cond(g);
                        self.add_cond(&c, true);
                    }
                    let v = self.eval(&a.body);
                    outs.push((self.st.clone(), v));
                }
                if outs.is_empty() {
                    self.st = s0;
                    self.st.dead = true;
                    return Sym::Opaque;
                }
                let (mut acc_s, mut acc_v) = outs.remove(0);
                for (s, v) in outs {
                    let joined = self.join(acc_s.clone(), s, &acc_v, &v, &e.ty);
                    acc_s = self.st.clone();
                    acc_v = joined;
                }
                self.st = acc_s;
                acc_v
            }
            TK::Loop(_, b) => {
                self.havoc_writes(b);
                let saved_dead = self.st.dead;
                let s0 = self.st.clone();
                self.eval(b);
                self.st = s0;
                self.st.dead = saved_dead;
                self.havoc_writes(b);
                // a loop without a break never ends normally
                if matches!(e.ty, Ty::Never) {
                    self.st.dead = true;
                }
                Sym::Opaque
            }
            TK::While(_, c, b) => {
                self.havoc_writes(c);
                self.havoc_writes(b);
                let s0 = self.st.clone();
                let cond = self.eval_cond(c);
                self.add_cond(&cond, true);
                self.eval(b);
                self.st = s0;
                self.havoc_writes(b);
                Sym::Opaque
            }
            TK::For { id, pat, iter, body, range, .. } => {
                self.eval_for(*id, pat, iter, body, range.as_ref());
                Sym::Opaque
            }
            TK::Break(_, v) | TK::Return(v) => {
                if let Some(v) = v {
                    let r = self.eval(v);
                    if let TK::Return(_) = e.kind {
                        self.check_ensures(&r, e.span);
                    }
                }
                self.st.dead = true;
                Sym::Opaque
            }
            TK::Continue(_) => {
                self.st.dead = true;
                Sym::Opaque
            }
            TK::Try { e: inner, .. } => {
                self.eval(inner);
                if e.ty.is_int() {
                    Sym::Int(self.fresh_ty("try", &e.ty))
                } else {
                    Sym::Opaque
                }
            }
            TK::Det { body, .. } => self.eval(body),
            TK::Trap(kind, _) => {
                let k = match kind {
                    TrapKind::Hole(n) => format!("hole({n})"),
                    TrapKind::Unreachable => "unreachable".into(),
                    TrapKind::Elided => "hole(…)".into(),
                    _ => "panic".into(),
                };
                self.site_always(e.span, &k);
                self.st.dead = true;
                Sym::Opaque
            }
            TK::Assert { cond, .. } => {
                let c = self.eval_cond(cond);
                for f in c.pos_side.clone() {
                    self.add_fact(f);
                }
                let ok = match &c.pos {
                    Some(fs) if !fs.is_empty() => {
                        let fs = fs.clone();
                        fs.iter().all(|f| self.prove(f))
                    }
                    _ => false,
                };
                if self.quiet == 0 && !self.st.dead {
                    let ent = self.sites.entry((e.span, "assert".into())).or_insert(true);
                    *ent = *ent && ok;
                }
                self.add_cond(&c, true);
                Sym::Opaque
            }
            TK::AssertCmp { a, b, .. } => {
                self.eval(a);
                self.eval(b);
                self.site_always(e.span, "assert");
                Sym::Opaque
            }
            TK::Format { args, .. } => {
                for a in args {
                    self.eval(a);
                }
                Sym::Opaque
            }
            TK::Matches(s, _) | TK::LetCond(_, s) => {
                self.eval(s);
                Sym::Opaque
            }
            TK::Error | TK::Lit(_) => Sym::Opaque,
        }
    }

    fn normalize_int(&mut self, p: Poly, t: &Ty) -> Poly {
        // keep terms small: large or nonlinear polynomials become a fresh atom with the interval
        if p.t.len() <= 8 && p.degree() <= 2 {
            return p;
        }
        let (lo, hi) = self.poly_iv(&p);
        let (tl, th) = ty_range(t);
        let a = self.fresh("big", lo.max(tl), hi.min(th));
        if p.degree() <= 1 {
            let f = Poly::atom(a).sub(&p);
            if let Some(f) = f {
                self.add_fact(Fact::Eq(f));
            }
        }
        Poly::atom(a)
    }

    fn arith(&mut self, op: BinOp, x: Poly, y: Poly, t: &Ty, sp: Span) -> Sym {
        let (lo, hi) = ty_range(t);
        let r = match op {
            BinOp::Add => x.add(&y),
            BinOp::Sub => x.sub(&y),
            BinOp::Mul => x.mul(&y),
            _ => None,
        };
        match op {
            BinOp::Add | BinOp::Sub | BinOp::Mul => {
                let name = format!("ovf({})", op.name());
                match r {
                    Some(r) => {
                        let g1 = r.sub(&Poly::c(lo)).map(Fact::Ge);
                        let g2 = Poly::c(hi).sub(&r).map(Fact::Ge);
                        let ok1 = self.check(sp, &name, g1.clone());
                        let ok2 = self.check(sp, &name, g2.clone());
                        let _ = (ok1, ok2);
                        // continuing means no overflow happened
                        if let Some(g) = g1 {
                            self.add_fact(g);
                        }
                        if let Some(g) = g2 {
                            self.add_fact(g);
                        }
                        let r = self.normalize_int(r, t);
                        Sym::Int(r)
                    }
                    None => {
                        self.check(sp, &name, None);
                        Sym::Int(self.fresh_ty("ovf", t))
                    }
                }
            }
            BinOp::Div | BinOp::Rem => {
                let nz = if t.is_int() && matches!(t, Ty::Int(i) if !i.signed()) {
                    Some(Fact::Ge(y.add(&Poly::c(-1)).unwrap_or_default()))
                } else {
                    // signed: y > 0 or y < 0; try y >= 1 then -y >= 1
                    let g = Fact::Ge(y.add(&Poly::c(-1)).unwrap_or_default());
                    if self.prove(&g) {
                        Some(g)
                    } else {
                        Some(Fact::Ge(y.neg().and_then(|n| n.add(&Poly::c(-1))).unwrap_or_default()))
                    }
                };
                self.check(sp, "div0", nz);
                if matches!(t, Ty::Int(i) if i.signed()) {
                    // MIN / -1
                    let g = Fact::Ge(x.sub(&Poly::c(lo)).and_then(|d| d.add(&Poly::c(-1))).unwrap_or_default());
                    let g2 = Fact::Ge(y.add(&Poly::c(1)).and_then(|d| d.add(&Poly::c(-1))).unwrap_or_default());
                    let ok = self.prove(&g) || self.prove(&g2) || self.prove(&Fact::Ge(Poly::c(-2).sub(&y).unwrap_or_default()));
                    if self.quiet == 0 && !self.st.dead {
                        let e = self.sites.entry((sp, "divovf".into())).or_insert(true);
                        *e = *e && ok;
                    }
                }
                // result interval
                let (xl, xh) = self.poly_iv(&x);
                let (yl, yh) = self.poly_iv(&y);
                let (rl, rh) = if op == BinOp::Rem {
                    if xl >= 0 && yl > 0 {
                        (0, (yh - 1).min(xh).max(0))
                    } else {
                        let m = yl.abs().max(yh.abs()).saturating_sub(1);
                        (-m, m)
                    }
                } else if xl >= 0 && yl > 0 {
                    (0, xh / yl)
                } else {
                    (lo, hi)
                };
                // the same quotient or remainder of the same operands is the same atom
                // (the key's base interval is the type's; the operand-dependent bounds hold on this
                // path only, so they go into the path state)
                let key = format!("{}({}|{})", op.name(), poly_text(&self.canon(&x)), poly_text(&self.canon(&y)));
                let a = self.atom_keyed(&key, lo, hi);
                self.set_iv(a, rl, rh);
                // relational facts (review 2026-10-23, kc27: `y[j % y.len()]` kept only the
                // interval [0, hi(n) - 1], not its relation to n): for x >= 0 and y >= 1,
                // x % y <= y - 1 and x % y <= x; x / y <= x
                // (only the relations: a constant operand's bound is in the interval already)
                let relational = x.konst().is_none() || y.konst().is_none();
                if relational && (xl >= 0 || self.prove(&Fact::Ge(x.clone()))) && (yl >= 1 || self.prove(&Fact::Ge(y.add(&Poly::c(-1)).unwrap_or_default()))) {
                    let at = Poly::atom(a);
                    if op == BinOp::Rem && y.konst().is_none() {
                        if let Some(f) = y.sub(&at).and_then(|d| d.add(&Poly::c(-1))) {
                            self.add_fact(Fact::Ge(f));
                        }
                    }
                    if x.konst().is_none() {
                        if let Some(f) = x.sub(&at) {
                            self.add_fact(Fact::Ge(f));
                        }
                    }
                }
                Sym::Int(Poly::atom(a))
            }
            _ => Sym::Int(self.fresh_ty("op", t)),
        }
    }

    /// `x << y`, `x >> y`: the amount must be in `0..bits(x)`, read at its own (possibly signed)
    /// type, so both ends are obligations (review 2026-10-16: a negative signed amount traps).
    fn shift(&mut self, op: BinOp, x: Sym, y: Sym, ty: &Ty, sp: Span) -> Sym {
        let bits = match ty {
            Ty::Int(i) => i.bits() as i128,
            _ => 64,
        };
        let yk = if let Sym::Int(y) = &y { Some(y.clone()) } else { None };
        let g_hi = yk.as_ref().and_then(|y| Poly::c(bits - 1).sub(y)).map(Fact::Ge);
        let g_lo = yk.as_ref().map(|y| Fact::Ge(y.clone()));
        self.check(sp, "shift", g_hi.clone());
        self.check(sp, "shift", g_lo.clone());
        // continuing means the amount was in range
        for g in [g_hi, g_lo].into_iter().flatten() {
            self.add_fact(g);
        }
        // a right shift of a non-negative value by an amount in range: 0 <= x >> s <= x, and
        // <= hi(x) >> lo(s) (review 2026-10-23, f5: `y[i >> 1]` under `i < y.len()` lost the
        // relation to i)
        if let (BinOp::Shr, Sym::Int(xp), Some(yp)) = (op, &x, yk.as_ref()) {
            let (xl, xh) = self.poly_iv(xp);
            let (sl, _) = self.poly_iv(yp);
            if (xl >= 0 || self.prove(&Fact::Ge(xp.clone()))) && sl >= 0 {
                let k = sl.min(126);
                let a = self.fresh("shr", 0, if xh < 0 { 0 } else { xh >> k });
                if xp.konst().is_none() {
                    if let Some(f) = xp.sub(&Poly::atom(a)) {
                        self.add_fact(Fact::Ge(f));
                    }
                }
                return Sym::Int(Poly::atom(a));
            }
        }
        Sym::Int(self.fresh_ty("shift", ty))
    }

    fn eval_binary(&mut self, op: BinOp, a: &TExpr, b: &TExpr, e: &TExpr) -> Sym {
        match op {
            BinOp::And | BinOp::Or => {
                let ca = self.eval_cond(a);
                // short circuit: b is evaluated under a (And) or ¬a (Or)
                let s0 = self.st.clone();
                self.add_cond(&ca, op == BinOp::And);
                let cb = self.eval_cond(b);
                let s1 = std::mem::replace(&mut self.st, s0);
                // sites recorded during b remain recorded; the facts b's evaluation added (call
                // `ensures`, passed bounds checks) hold exactly when b was evaluated, so they join
                // the outcome that implies it: `a && b` true, `a || b` false
                let delta: Vec<Fact> = s1.facts.iter().filter(|f| !self.st.fset.contains(*f)).cloned().collect();
                self.st.ver = s1.ver;
                let _ = s1.env;
                if op == BinOp::And {
                    let pos = match (ca.pos, cb.pos) {
                        (Some(mut x), Some(y)) => {
                            x.extend(y);
                            Some(x)
                        }
                        (Some(x), None) | (None, Some(x)) => Some(x),
                        _ => None,
                    };
                    let mut pos_side = ca.pos_side;
                    pos_side.extend(cb.pos_side);
                    pos_side.extend(delta);
                    Sym::Bool(Cond { pos, neg: None, pos_side, neg_side: vec![] })
                } else {
                    let neg = match (ca.neg, cb.neg) {
                        (Some(mut x), Some(y)) => {
                            x.extend(y);
                            Some(x)
                        }
                        (Some(x), None) | (None, Some(x)) => Some(x),
                        _ => None,
                    };
                    let mut neg_side = ca.neg_side;
                    neg_side.extend(cb.neg_side);
                    neg_side.extend(delta);
                    Sym::Bool(Cond { pos: None, neg, pos_side: vec![], neg_side })
                }
            }
            _ if op.is_cmp() => {
                let x = self.eval(a);
                let y = self.eval(b);
                let (Sym::Int(x), Sym::Int(y)) = (x, y) else { return Sym::Bool(Cond::default()) };
                let d = |p: Option<Poly>| p.unwrap_or_default();
                let ge = |p: Poly| Fact::Ge(p);
                Sym::Bool(match op {
                    BinOp::Lt => Cond { pos: Some(vec![ge(d(y.sub(&x).and_then(|z| z.add(&Poly::c(-1)))))]), neg: Some(vec![ge(d(x.sub(&y)))]), ..Default::default() },
                    BinOp::Le => Cond { pos: Some(vec![ge(d(y.sub(&x)))]), neg: Some(vec![ge(d(x.sub(&y).and_then(|z| z.add(&Poly::c(-1)))))]), ..Default::default() },
                    BinOp::Gt => Cond { pos: Some(vec![ge(d(x.sub(&y).and_then(|z| z.add(&Poly::c(-1)))))]), neg: Some(vec![ge(d(y.sub(&x)))]), ..Default::default() },
                    BinOp::Ge => Cond { pos: Some(vec![ge(d(x.sub(&y)))]), neg: Some(vec![ge(d(y.sub(&x).and_then(|z| z.add(&Poly::c(-1)))))]), ..Default::default() },
                    BinOp::Eq => Cond { pos: Some(vec![Fact::Eq(d(x.sub(&y)))]), neg: Some(vec![Fact::Ne(d(x.sub(&y)))]), ..Default::default() },
                    _ => Cond { pos: Some(vec![Fact::Ne(d(x.sub(&y)))]), neg: Some(vec![Fact::Eq(d(x.sub(&y)))]), ..Default::default() },
                })
            }
            _ => {
                let x = self.eval(a);
                let y = self.eval(b);
                if !e.ty.is_int() {
                    return Sym::Opaque;
                }
                match (op, x, y) {
                    (BinOp::Add | BinOp::Sub | BinOp::Mul | BinOp::Div | BinOp::Rem, Sym::Int(x), Sym::Int(y)) => self.arith(op, x, y, &e.ty, e.span),
                    (BinOp::Add | BinOp::Sub | BinOp::Mul, _, _) => {
                        self.check(e.span, &format!("ovf({})", op.name()), None);
                        Sym::Int(self.fresh_ty("ovf", &e.ty))
                    }
                    (BinOp::Div | BinOp::Rem, _, _) => {
                        self.check(e.span, "div0", None);
                        Sym::Int(self.fresh_ty("div", &e.ty))
                    }
                    (BinOp::Shl | BinOp::Shr, x, y) => self.shift(op, x, y, &e.ty, e.span),
                    (BinOp::BitAnd, x, y) => {
                        let (_, th) = ty_range(&e.ty);
                        let mut hi = th;
                        for s in [&x, &y] {
                            if let Sym::Int(p) = s {
                                let (l, h) = self.poly_iv(p);
                                if l >= 0 {
                                    hi = hi.min(h);
                                }
                            }
                        }
                        let unsigned = matches!(&e.ty, Ty::Int(i) if !i.signed());
                        let lo = if unsigned { 0 } else { ty_range(&e.ty).0 };
                        let a = self.fresh("and", lo, hi);
                        Sym::Int(Poly::atom(a))
                    }
                    _ => Sym::Int(self.fresh_ty("bit", &e.ty)),
                }
            }
        }
    }

    fn assign(&mut self, place: &TExpr, v: Sym) {
        match &place.kind {
            TK::Local(l) => {
                let v = match v {
                    Sym::Int(p) if place.ty.is_int() => Sym::Int(self.normalize_int(p, &place.ty)),
                    Sym::Opaque if place.ty.is_int() => Sym::Int(self.fresh_ty("asg", &place.ty)),
                    other => other,
                };
                self.bump(&format!("L{l}"));
                self.st.env.insert(*l, v);
            }
            _ => {
                let ps = self.place(place);
                // writes kill facts about the old contents (a new version of the place)
                self.write_place(&ps);
                // a write to a #[range] field must respect the range (checked at run time outside
                // kernels)
                if let Some((lo, hi)) = field_range(self.c, place) {
                    if let Sym::Int(p) = &v {
                        let g1 = p.sub(&Poly::c(lo)).map(Fact::Ge);
                        let g2 = Poly::c(hi).sub(p).map(Fact::Ge);
                        self.check(place.span, "range", g1);
                        self.check(place.span, "range", g2);
                    } else {
                        self.check(place.span, "range", None);
                    }
                }
            }
        }
    }

    fn ctor_checks(&mut self, adt: AdtId, e: &TExpr) {
        let ad = &self.c.program.adts[adt as usize];
        if ad.invariant.is_some() {
            // construction of an S with an invariant: checked at run time (or proved in kernels)
            let name = format!("inv({})", ad.name);
            self.check(e.span, &name, None);
        }
        let has_range = ad.variants.iter().any(|v| v.fields.iter().any(|f| f.range.is_some()));
        if has_range {
            if let TK::Ctor { fields, variant, .. } = &e.kind {
                let vd = ad.variants[*variant as usize].clone();
                for (i, fe) in fields.iter().enumerate() {
                    if let Some((lo, hi)) = vd.fields.get(i).and_then(|f| f.range) {
                        match self.eval(fe) {
                            Sym::Int(p) => {
                                let g1 = p.sub(&Poly::c(lo)).map(Fact::Ge);
                                let g2 = Poly::c(hi).sub(&p).map(Fact::Ge);
                                self.check(fe.span, "range", g1);
                                self.check(fe.span, "range", g2);
                            }
                            _ => {
                                self.check(fe.span, "range", None);
                            }
                        }
                    }
                }
            }
        }
    }

    fn bind_pat(&mut self, p: &TPat, v: Sym) {
        match &p.kind {
            PK::Bind { local, by_ref: None, sub: None } => {
                let v = match v {
                    Sym::Opaque if p.ty.is_int() => Sym::Int(self.fresh_ty("bind", &p.ty)),
                    other => other,
                };
                self.bump(&format!("L{local}"));
                self.st.env.insert(*local, v);
            }
            _ => {
                let mut ls = vec![];
                p.bindings(&mut ls);
                for l in ls {
                    self.bump(&format!("L{l}"));
                    self.st.env.remove(&l);
                }
            }
        }
    }

    /// Locals assigned and places written anywhere inside `e` become unknown (loops, F-44):
    /// assignments, writes through references, `&mut` arguments (also through a reference held in
    /// a local), and closure calls; a write whose place cannot be resolved may write any
    /// address-taken local.
    fn havoc_writes(&mut self, e: &TExpr) {
        let mut locals = vec![];
        let mut places: Vec<&TExpr> = vec![];
        let c = self.c;
        let mut whole_args: Vec<&TExpr> = vec![];
        let mut ref_args: Vec<(LocalId, bool)> = vec![];
        let mut unknown = false;
        let mut calls_closures = false;
        walk_deep(c, e, &mut |x| match &x.kind {
            TK::Assign(p, _) | TK::AssignOp(_, p, _) => {
                if let TK::Local(l) = p.kind {
                    locals.push(l);
                } else {
                    places.push(p);
                }
            }
            TK::Call { args, .. } | TK::TraitCall { args, .. } | TK::CallValue(_, args) => {
                let is_proj = match &x.kind {
                    TK::Call { f, .. } => c.bodies.get(f).map(|b| !b.footprints.is_empty()).unwrap_or(false),
                    _ => false,
                };
                if matches!(x.kind, TK::CallValue(..)) {
                    calls_closures = true;
                    unknown = true;
                }
                for a in args {
                    if ty_mentions_closure(&a.ty) {
                        calls_closures = true;
                    }
                    if is_proj {
                        continue;
                    }
                    match (&a.ty, &a.kind) {
                        (Ty::Ref(true, inner), TK::Borrow(true, p)) => {
                            if let TK::Local(l) = p.kind {
                                locals.push(l);
                            }
                            whole_args.push(p);
                            if ty_has_mut_ref(inner) {
                                unknown = true;
                            }
                        }
                        (Ty::Ref(true, inner), TK::Local(r)) => {
                            ref_args.push((*r, matches!(**inner, Ty::Slice(_) | Ty::Str)));
                            if ty_has_mut_ref(inner) {
                                unknown = true;
                            }
                        }
                        (t, _) if ty_has_mut_ref(t) => unknown = true,
                        _ => {}
                    }
                }
            }
            TK::Borrow(true, p) => {
                if let TK::Local(l) = p.kind {
                    locals.push(l);
                }
            }
            _ => {}
        });
        let before: HashMap<String, u32> = self.st.ver.clone();
        for l in locals {
            self.st.env.remove(&l);
            self.bump(&format!("L{l}"));
        }
        self.quiet += 1;
        let saved = self.st.clone();
        for p in places {
            match self.place_shape(p) {
                Some(ps) => self.write_place(&ps),
                None => unknown = true,
            }
        }
        for p in whole_args {
            match self.place_shape(p) {
                Some(ps) => {
                    if matches!(p.ty, Ty::Slice(_) | Ty::Str) {
                        if !self.known_root(&ps.root) {
                            unknown = true;
                        }
                        self.bump(&format!("E:{}{}", ps.root, ps.path));
                    } else {
                        self.write_place(&ps);
                    }
                }
                None => unknown = true,
            }
        }
        for (r, slice) in ref_args {
            match self.st.env.get(&r).cloned() {
                Some(Sym::Ref(ps)) if slice => {
                    if !self.known_root(&ps.root) {
                        unknown = true;
                    }
                    self.bump(&format!("E:{}{}", ps.root, ps.path));
                }
                Some(Sym::Ref(ps)) => self.write_place(&ps),
                _ => {
                    if !self.body.params.contains(&r) {
                        unknown = true;
                    }
                }
            }
        }
        if unknown {
            self.havoc_addr_taken();
        }
        if calls_closures {
            self.havoc_mut_captured();
        }
        let ver = self.st.ver.clone();
        self.st = saved;
        // a local whose version changed has no SSA value any more
        for (k, v) in &ver {
            if before.get(k) != Some(v) {
                if let Some(l) = k.strip_prefix('L').and_then(|r| r.parse::<LocalId>().ok()) {
                    self.st.env.remove(&l);
                }
            }
        }
        self.st.ver = ver;
        self.quiet -= 1;
    }

    /// The root and field path of a place, without evaluating index expressions' effects.
    fn place_shape(&mut self, p: &TExpr) -> Option<PSym> {
        match &p.kind {
            TK::Local(l) => Some(PSym { root: format!("L{l}"), path: String::new(), len: None, proj: None }),
            TK::Deref(b) => match &b.kind {
                TK::Local(l) => match self.st.env.get(l) {
                    Some(Sym::Ref(ps)) => Some(ps.clone()),
                    _ => Some(PSym { root: format!("*L{l}"), path: String::new(), len: None, proj: None }),
                },
                TK::Call { .. } => {
                    // a write through a projection result: evaluate the call shape
                    match self.eval(b) {
                        Sym::Ref(ps) => Some(ps),
                        _ => None,
                    }
                }
                _ => self.place_shape(b),
            },
            TK::Field(b, i) => {
                let pb = self.place_shape(b)?;
                let fname = field_name(self.c, &b.ty, *i);
                Some(PSym { root: pb.root, path: format!("{}.{fname}", pb.path), len: None, proj: None })
            }
            TK::Index(b, _) | TK::SliceRange { base: b, .. } => {
                let pb = self.place_shape(b)?;
                Some(PSym { root: pb.root, path: format!("{}[*]", pb.path), len: None, proj: None })
            }
            _ => None,
        }
    }

    fn join(&mut self, s1: State, s2: State, v1: &Sym, v2: &Sym, ty: &Ty) -> Sym {
        if s1.dead && s2.dead {
            self.st = s1;
            return Sym::Opaque;
        }
        if s1.dead {
            self.st = s2;
            return v2.clone();
        }
        if s2.dead {
            self.st = s1;
            return v1.clone();
        }
        // keep facts common to both, env entries equal in both; others become fresh
        let mut st = s1.clone();
        st.facts.retain(|f| s2.fset.contains(f));
        st.fset = st.facts.iter().cloned().collect();
        st.fidx = HashMap::new();
        for (i, f) in st.facts.iter().enumerate() {
            let p = match f {
                Fact::Ge(p) | Fact::Eq(p) | Fact::Ne(p) => p,
            };
            for m in p.t.keys() {
                for a in &m.0 {
                    let v = st.fidx.entry(*a).or_default();
                    if v.last() != Some(&(i as u32)) {
                        v.push(i as u32);
                    }
                }
            }
        }
        // atom intervals: the hull of the two paths'; atom equalities: those both paths have
        let mut touched: BTreeSet<AtomId> = BTreeSet::new();
        for s in [&s1, &s2] {
            touched.extend(s.iv.keys().copied());
            touched.extend(s.uf.keys().copied());
            touched.extend(s.uf.values().copied());
        }
        st.uf = s1.uf.iter().filter(|(k, v)| s2.uf.get(k) == Some(v)).map(|(k, v)| (*k, *v)).collect();
        st.iv = BTreeMap::new();
        for a in touched {
            let (l1, h1) = self.iv_in(&s1, a);
            let (l2, h2) = self.iv_in(&s2, a);
            let v = (l1.min(l2), h1.max(h2));
            if v != self.base_iv(a) {
                st.iv.insert(a, v);
            }
        }
        let mut env = HashMap::new();
        let mut jobs: Vec<(Poly, Poly, AtomId)> = vec![];
        for (l, a) in &s1.env {
            if let Some(b) = s2.env.get(l) {
                match (a, b) {
                    (Sym::Int(x), Sym::Int(y)) if x == y => {
                        env.insert(*l, a.clone());
                    }
                    (Sym::Int(x), Sym::Int(y)) => {
                        let (l1, h1) = self.poly_iv_in(&s1, x);
                        let (l2, h2) = self.poly_iv_in(&s2, y);
                        let at = self.fresh("phi", l1.min(l2), h1.max(h2));
                        jobs.push((x.clone(), y.clone(), at));
                        env.insert(*l, Sym::Int(Poly::atom(at)));
                    }
                    (Sym::Ref(p), Sym::Ref(q)) if p == q => {
                        env.insert(*l, a.clone());
                    }
                    _ => {}
                }
            }
        }
        st.env = env;
        for (k, v) in &s2.ver {
            let e = st.ver.entry(k.clone()).or_insert(0);
            *e = (*e).max(*v);
        }
        let mut same_value = false;
        let r = match (v1, v2) {
            (Sym::Int(x), Sym::Int(y)) if ty.is_int() => {
                if x == y {
                    same_value = true;
                    None
                } else {
                    let (l1, h1) = self.poly_iv_in(&s1, x);
                    let (l2, h2) = self.poly_iv_in(&s2, y);
                    Some((l1.min(l2), h1.max(h2), x.clone(), y.clone()))
                }
            }
            _ => None,
        };
        let result_phi = match r {
            Some((lo, hi, x, y)) => {
                let at = self.fresh("phi", lo, hi);
                jobs.push((x, y, at));
                Some(at)
            }
            None => None,
        };
        let phi_add = self.phi_facts(s1, s2, &jobs);
        self.st = st;
        for f in phi_add {
            self.add_fact(f);
        }
        if same_value {
            return v1.clone();
        }
        match result_phi {
            Some(at) => Sym::Int(Poly::atom(at)),
            _ => {
                if ty.is_int() {
                    Sym::Int(self.fresh_ty("phi", ty))
                } else {
                    Sym::Opaque
                }
            }
        }
    }

    /// Relational facts across a join (review 2026-10-23, kc10: `let j = if i < n { i } else { 0 };
    /// y[j]` kept only j's interval). A linear fact of one path about its value (a single atom)
    /// holds of the merged atom when the other path's value satisfies it too, proved in that
    /// path's state: the per-arm implication c => x = e_arm, used as a case split. At most a few
    /// candidates per side, so a join stays cheap.
    fn phi_facts(&mut self, s1: State, s2: State, jobs: &[(Poly, Poly, AtomId)]) -> Vec<Fact> {
        let mut out = vec![];
        if jobs.is_empty() || s1.dead || s2.dead {
            return out;
        }
        // the candidates of each side: facts of that path that relate its value (one atom) to
        // other atoms, found through the path's per-atom index
        let mut per_side: [Vec<(usize, AtomId, Poly)>; 2] = [vec![], vec![]];
        for (k, (x, y, _)) in jobs.iter().enumerate() {
            for (side, (sa, va)) in [(&s1, x), (&s2, y)].into_iter().enumerate() {
                let va = self.canon_in(sa, va);
                let a = match (va.t.len(), va.t.iter().next()) {
                    (1, Some((m, 1))) if m.0.len() == 1 => m.0[0],
                    _ => continue,
                };
                let mut n = 0;
                for fi in sa.fidx.get(&a).cloned().unwrap_or_default() {
                    let Some(f) = sa.facts.get(fi as usize) else { continue };
                    let ps: Vec<Poly> = match f {
                        Fact::Ge(p) => vec![p.clone()],
                        Fact::Eq(p) => vec![p.clone(), p.neg().unwrap_or_default()],
                        Fact::Ne(_) => vec![],
                    };
                    for p in ps {
                        let linear_in_a = p.t.keys().all(|m| !m.0.contains(&a) || m.0.len() == 1);
                        // only relations: a fact on a alone is kept by the interval hull already
                        let relational = p.t.keys().any(|m| !m.0.is_empty() && !m.0.contains(&a));
                        if linear_in_a && relational && p.t.keys().any(|m| m.0 == vec![a]) && n < 8 {
                            per_side[side].push((k, a, p));
                            n += 1;
                        }
                    }
                }
            }
        }
        if per_side[0].is_empty() && per_side[1].is_empty() {
            return out;
        }
        // prove each candidate of one side in the other side's state (the states are moved in,
        // not cloned)
        let saved = std::mem::replace(&mut self.st, s2);
        self.phi_prove(&per_side[0], jobs, 0, &mut out);
        self.st = s1;
        self.phi_prove(&per_side[1], jobs, 1, &mut out);
        self.st = saved;
        out
    }

    fn phi_prove(&mut self, cands: &[(usize, AtomId, Poly)], jobs: &[(Poly, Poly, AtomId)], side: usize, out: &mut Vec<Fact>) {
        for (k, a, p) in cands {
            let (x, y, at) = &jobs[*k];
            let vb = if side == 0 { y } else { x };
            let c = p.t.get(&Mono(vec![*a])).copied().unwrap_or(0);
            let rest = match Poly::atom(*a).scale(c).and_then(|z| p.sub(&z)) {
                Some(r) => r,
                None => continue,
            };
            let other = vb.scale(c).and_then(|z| rest.add(&z));
            let mine = Poly::atom(*at).scale(c).and_then(|z| rest.add(&z));
            if let (Some(other), Some(mine)) = (other, mine) {
                // a cheap proof: the interval bound, or the fact itself on that path (a full
                // Fourier-Motzkin proof at every join made long bodies quadratic)
                let oc = self.canon(&other);
                let holds = self.poly_iv(&oc).0 >= 0 || self.st.fset.contains(&Fact::Ge(oc.clone()));
                if holds {
                    out.push(Fact::Ge(mine));
                }
            }
        }
    }

    // ------------------------------------------------------------ loops
    fn eval_for(&mut self, id: LoopId, pat: &TPat, iter: &TExpr, body: &TExpr, range: Option<&(Box<TExpr>, Box<TExpr>, bool)>) {
        let (lo, hi) = match range {
            Some((l, h, incl)) => {
                let lo = self.eval_int(l);
                let hi = self.eval_int(h).and_then(|p| if *incl { p.add(&Poly::c(1)) } else { Some(p) });
                (lo, hi)
            }
            None => {
                self.eval(iter);
                (None, None)
            }
        };
        let var = pat.is_irrefutable_bind();
        // T-Cover decision (before the body changes anything)
        if let (Some(l0), Some(h)) = (&lo, &hi) {
            if l0.konst() == Some(0) {
                // the index must be the binder itself, immutable (F-103: `for mut i` that assigns
                // i indexes through an ordinary local; review 2026-10-23, N-94)
                if let Some(v) = var.filter(|v| !self.body.locals[*v as usize].mutable) {
                    self.decide_cover(id, v, h, body);
                }
            }
        }
        let consts = match (&lo, &hi) {
            (Some(l), Some(h)) => match (l.konst(), h.konst()) {
                (Some(a), Some(b)) if b - a <= 64 && b >= a => Some((a, b)),
                _ => None,
            },
            _ => None,
        };
        if let (Some((a, b)), Some(v)) = (consts, var) {
            // unroll a constant trip count
            for k in a..b {
                if self.st.dead {
                    break;
                }
                let saved_dead = self.st.dead;
                self.bump(&format!("L{v}"));
                self.st.env.insert(v, Sym::Int(Poly::c(k)));
                let s_before = self.st.clone();
                self.eval(body);
                if self.st.dead {
                    // continue/break/return inside: fall back to the state before the iteration
                    self.st = s_before;
                    self.havoc_writes(body);
                }
                self.st.dead = saved_dead;
            }
            self.st.env.remove(&v);
            return;
        }
        self.havoc_writes(body);
        let s0 = self.st.clone();
        match var {
            Some(v) => {
                let (tl, th) = ty_range(&pat.ty);
                let a = self.fresh("i", tl, th);
                let ip = Poly::atom(a);
                if let Some(l) = &lo {
                    if let Some(g) = ip.sub(l) {
                        self.add_fact(Fact::Ge(g));
                    }
                }
                if let Some(h) = &hi {
                    if let Some(g) = h.sub(&ip).and_then(|d| d.add(&Poly::c(-1))) {
                        self.add_fact(Fact::Ge(g));
                    }
                }
                self.bump(&format!("L{v}"));
                self.st.env.insert(v, Sym::Int(ip));
            }
            None => self.bind_pat(pat, Sym::Opaque),
        }
        self.eval(body);
        self.st = s0;
        self.havoc_writes(body);
    }

    /// T-Cover (note section 5.9, F-1, F-37): the loop writes `p[i]` exactly once, unconditionally,
    /// with no exit in its body, and T2 proves n == p.len().
    fn decide_cover(&mut self, id: LoopId, var: LocalId, n: &Poly, body: &TExpr) {
        // premise 0: no break, continue, return or ? (targeting this loop or an enclosing one)
        let mut inner_loops = HashSet::new();
        walk_deep(self.c, body, &mut |x| match &x.kind {
            TK::Loop(i, _) | TK::While(i, _, _) | TK::For { id: i, .. } => {
                inner_loops.insert(*i);
            }
            _ => {}
        });
        let mut bad_exit = false;
        walk_deep(self.c, body, &mut |x| match &x.kind {
            TK::Return(_) | TK::Try { .. } => bad_exit = true,
            TK::Break(l, _) | TK::Continue(l) if !inner_loops.contains(l) => bad_exit = true,
            _ => {}
        });
        if bad_exit {
            return;
        }
        // premise 1: the top-level statements contain exactly one write p[i] = e, with no if/match
        // before it
        let stmts: Vec<&TExpr> = match &body.kind {
            TK::Block(ss, tail) => {
                let mut v: Vec<&TExpr> = ss.iter().filter_map(|s| if let TStmt::Expr(e) = s { Some(e) } else { None }).collect();
                if let Some(t) = tail {
                    v.push(t);
                }
                if ss.iter().any(|s| matches!(s, TStmt::Let { .. })) {
                    // lets are fine; they precede or follow the write
                }
                v
            }
            _ => vec![body],
        };
        let mut target: Option<(LocalId, bool)> = None;
        let mut count = 0;
        let mut branch_before = false;
        for s in &stmts {
            match &s.kind {
                TK::Assign(p, _) => {
                    if let TK::Index(base, idx) = &p.kind {
                        if matches!(idx.kind, TK::Local(l) if l == var) {
                            // base rooted at a local, or a footprinted row projection
                            if let Some(r) = cover_base(base) {
                                if branch_before {
                                    return;
                                }
                                target = Some((r, false));
                                count += 1;
                                continue;
                            }
                            if let Some((r, rowvar)) = row_projection_base(self.c, base) {
                                let _ = rowvar;
                                if branch_before {
                                    return;
                                }
                                target = Some((r, true));
                                count += 1;
                                continue;
                            }
                        }
                    }
                }
                TK::If(..) | TK::Match(..) => branch_before = true,
                TK::For { id: inner, .. } => {
                    // a nested covering loop over row `var` of a footprinted projection
                    if let Some(r) = self.row_covers.iter().find(|(l, _)| l == inner).map(|x| x.1) {
                        if branch_before {
                            return;
                        }
                        let _ = r;
                    }
                }
                _ => {}
            }
        }
        // nested row cover: the body's only statement is an inner loop that covers row `var`
        if count == 0 && stmts.len() == 1 {
            if let TK::For { id: inner_id, body: inner_body, range: Some((ilo, ihi, false)), pat: ipat, .. } = &stmts[0].kind {
                // the inner loop must write footprint(row(var))[j] for its own j
                if let (Some(jv), Some(il), Some(ih)) = (ipat.is_irrefutable_bind(), self.eval_int_quiet(ilo), self.eval_int_quiet(ihi)) {
                    if il.konst() == Some(0) {
                        if let Some((root, rowvar)) = inner_row_write(self.c, inner_body, jv) {
                            if rowvar == var {
                                // premise 2 for the inner loop: n_inner == len(row) = blocks_per_row
                                let bpr = self.matrix_field(root, "blocks_per_row");
                                let rows = self.matrix_field(root, "rows");
                                if let (Some(bpr), Some(rows)) = (bpr, rows) {
                                    let ok_inner = ih.sub(&bpr).map(Fact::Eq).map(|g| self.prove(&g)).unwrap_or(false);
                                    let ok_outer = n.sub(&rows).map(Fact::Eq).map(|g| self.prove(&g)).unwrap_or(false);
                                    if ok_inner && ok_outer && no_other_writes(self.c, inner_body, root, true) {
                                        self.row_covers.push((*inner_id, root));
                                        self.covers.push((id, root));
                                    }
                                }
                            }
                        }
                    }
                }
            }
            return;
        }
        let Some((root, is_row)) = target else { return };
        if count != 1 || is_row {
            return;
        }
        // premise 3: no other write to p
        if !no_other_writes(self.c, body, root, false) {
            return;
        }
        // premise 2: n == p.len()
        let base_ty = self.body.locals[root as usize].ty.clone();
        let ps = match &base_ty {
            Ty::Ref(..) => PSym { root: format!("*L{root}"), path: String::new(), len: None, proj: None },
            _ => PSym { root: format!("L{root}"), path: String::new(), len: None, proj: None },
        };
        let len = self.len_of(&ps, &base_ty);
        let g = n.sub(&len).map(Fact::Eq);
        if let Some(g) = g {
            if self.prove(&g) {
                self.covers.push((id, root));
            }
        }
    }

    fn eval_int_quiet(&mut self, e: &TExpr) -> Option<Poly> {
        self.quiet += 1;
        let r = self.eval_int(e);
        self.quiet -= 1;
        r
    }

    /// `(*root).field` of a `&mut Matrix` parameter, as a polynomial.
    fn matrix_field(&mut self, root: LocalId, field: &str) -> Option<Poly> {
        let ty = self.body.locals[root as usize].ty.clone();
        let inner = ty.deref_ty()?.clone();
        let Ty::Adt(a, _) = &inner else { return None };
        let ad = &self.c.program.adts[*a as usize];
        ad.variants.first()?.fields.iter().find(|f| f.name == field)?;
        let ps = PSym { root: format!("*L{root}"), path: format!(".{field}"), len: None, proj: None };
        let key = format!("val({})", self.pkey(&ps));
        let a = self.atom_keyed(&key, 0, u64::MAX as i128);
        Some(Poly::atom(a))
    }

    // ------------------------------------------------------------ calls and contracts
    fn eval_call(&mut self, fid: FnId, args: &[TExpr], e: &TExpr) -> Sym {
        let mut argv = vec![];
        for a in args {
            argv.push(self.eval(a));
        }
        let f: &FnDef = &self.c.program.fns[fid as usize];
        let b = f.builtin.clone();
        // builtins with exact symbolic results
        match b.as_deref() {
            Some("slice_len") | Some("str_len") => {
                if let Some(Sym::Ref(ps)) = argv.first() {
                    let t = args[0].ty.clone();
                    return Sym::Int(self.len_of(ps, &t));
                }
            }
            Some("int_min") | Some("int_max") | Some("cmp_min") | Some("cmp_max") | Some("ord_min") | Some("ord_max") => {
                if let (Some(Sym::Int(pa)), Some(Sym::Int(pb))) = (argv.first(), argv.get(1)) {
                    let (la, ha) = self.poly_iv(pa);
                    let (lb, hb) = self.poly_iv(pb);
                    let is_max = matches!(b_name(&b), "int_max" | "cmp_max" | "ord_max");
                    let (lo, hi) = if is_max { (la.max(lb), ha.max(hb)) } else { (la.min(lb), ha.min(hb)) };
                    let at = self.fresh("minmax", lo, hi);
                    // max(a, b) >= a, b; min(a, b) <= a, b
                    for p in [pa, pb] {
                        let d = if is_max { Poly::atom(at).sub(p) } else { p.sub(&Poly::atom(at)) };
                        if let Some(d) = d {
                            self.add_fact(Fact::Ge(d));
                        }
                    }
                    return Sym::Int(Poly::atom(at));
                }
            }
            Some("int_abs") => {
                if let Some(Sym::Int(a)) = argv.first() {
                    let (la, ha) = self.poly_iv(a);
                    let m = la.saturating_abs().max(ha.saturating_abs());
                    let at = self.fresh("abs", 0, m);
                    return Sym::Int(Poly::atom(at));
                }
            }
            _ => {}
        }
        // requires at the call site
        let cx: &'a Checked = self.c;
        let callee_body: Option<&'a Body> = cx.bodies.get(&fid);
        if let Some(cb) = callee_body {
            if !cb.requires.is_empty() {
                let mut all_ok = true;
                for r in cb.requires.iter() {
                    let facts = self.contract_facts(cb, r, &argv, None);
                    let ok = match facts {
                        Some(fs) if !fs.is_empty() => fs.iter().all(|g| self.prove(g)),
                        _ => false,
                    };
                    if !ok {
                        all_ok = false;
                        if self.quiet == 0 && std::env::var("MITHI_T2_DEBUG").is_ok() {
                            let goals = self.contract_facts(cb, r, &argv, None).unwrap_or_default();
                            eprintln!("T2 unproved req({}) at {}: goals {:?}", f.name, self.c.program.sm.snippet(e.span), goals.iter().map(|g| self.fact_text(g)).collect::<Vec<_>>());
                            for fa in &self.st.facts {
                                eprintln!("    fact {}", self.fact_text(fa));
                            }
                        }
                    }
                    // continuing means the requires held
                    if let Some(fs) = self.contract_facts(cb, r, &argv, None) {
                        for g in fs {
                            self.add_fact(g);
                        }
                    }
                }
                let name = format!("req({})", f.name);
                if self.quiet == 0 && !self.st.dead {
                    let ent = self.sites.entry((e.span, name)).or_insert(true);
                    *ent = *ent && all_ok;
                }
            }
            // #[range] parameters are asserted at call sites
            for (i, p) in f.params.iter().enumerate() {
                if let Some((lo, hi)) = p.range {
                    match argv.get(i) {
                        Some(Sym::Int(x)) => {
                            let g1 = x.sub(&Poly::c(lo)).map(Fact::Ge);
                            let g2 = Poly::c(hi).sub(x).map(Fact::Ge);
                            self.check(e.span, "range", g1);
                            self.check(e.span, "range", g2);
                        }
                        _ => {
                            self.check(e.span, "range", None);
                        }
                    }
                }
            }
        }
        // writes through &mut arguments create new versions of their referents before the
        // callee's `ensures` (which describe the state after the call) are assumed; a footprinted
        // projection writes nothing itself (E-FOOTPRINT is checked at its definition)
        let is_proj = callee_body.map(|b| !b.footprints.is_empty()).unwrap_or(false);
        if !is_proj {
            self.call_writes(args, &argv);
        }
        // the result
        let result = if e.ty.is_int() {
            Sym::Int(self.fresh_ty(&format!("call:{}", f.name), &e.ty))
        } else if let Ty::Ref(..) = e.ty {
            self.callk += 1;
            Sym::Ref(PSym { root: format!("C{}:{}", self.callk, f.name), path: String::new(), len: None, proj: None })
        } else {
            Sym::Opaque
        };
        // ensures after the call
        if let Some(cb) = callee_body {
            for en in cb.ensures.iter() {
                if let Some(fs) = self.contract_facts(cb, en, &argv, Some(&result)) {
                    for g in fs {
                        self.add_fact(g);
                    }
                }
            }
            // a footprint fixes the result's place and length
            if let (Some(fp), Sym::Ref(_)) = (cb.footprints.first().cloned(), &result) {
                if let Some(ps) = self.contract_place(cb, &fp, &argv) {
                    let len = ps.len.clone();
                    let mut r = PSym { root: ps.root.clone(), path: ps.path.clone(), len, proj: Some(f.name.clone()) };
                    // distinct calls write distinct rows: keep the footprint's own key
                    r.path = ps.path.clone();
                    return Sym::Ref(r);
                }
            }
        }
        result
    }

    /// Facts a contract clause of `cb` states, with parameters bound to the call's arguments.
    fn contract_facts(&mut self, cb: &'a Body, clause: &TExpr, argv: &[Sym], result: Option<&Sym>) -> Option<Vec<Fact>> {
        let (goals, side) = self.contract_cond(cb, clause, argv, result);
        // the side facts hold (the clause's calls were evaluated): assume them
        for f in side {
            self.add_fact(f);
        }
        goals
    }

    fn contract_cond(&mut self, cb: &'a Body, clause: &TExpr, argv: &[Sym], result: Option<&Sym>) -> (Option<Vec<Fact>>, Vec<Fact>) {
        let saved_env = self.st.env.clone();
        let mut env = HashMap::new();
        for (i, pl) in cb.params.iter().enumerate() {
            if let Some(v) = argv.get(i) {
                env.insert(*pl, v.clone());
            }
        }
        if let (Some(rl), Some(r)) = (cb.result_local, result) {
            env.insert(rl, r.clone());
        }
        // evaluate in the callee's local space: local ids of `cb` index its own table
        let saved_body = self.body;
        let saved_ver = self.st.ver.clone();
        self.st.env = env;
        self.quiet += 1;
        self.body = cb;
        let c = self.eval_cond(clause);
        self.body = saved_body;
        self.quiet -= 1;
        self.st.env = saved_env;
        // keep versions bumped inside (none expected)
        self.st.ver = saved_ver;
        (c.pos, c.pos_side)
    }

    fn contract_place(&mut self, cb: &'a Body, place: &TExpr, argv: &[Sym]) -> Option<PSym> {
        let saved_env = self.st.env.clone();
        let mut env = HashMap::new();
        for (i, pl) in cb.params.iter().enumerate() {
            if let Some(v) = argv.get(i) {
                env.insert(*pl, v.clone());
            }
        }
        let saved_body = self.body;
        self.st.env = env;
        self.quiet += 1;
        self.body = cb;
        let ps = self.place(place);
        self.body = saved_body;
        self.quiet -= 1;
        self.st.env = saved_env;
        Some(ps)
    }

    fn check_ensures(&mut self, r: &Sym, sp: Span) {
        let body = self.body;
        if body.ensures.is_empty() {
            return;
        }
        let params: Vec<Sym> = body.params.iter().map(|p| self.st.env.get(p).cloned().unwrap_or(Sym::Opaque)).collect();
        let _ = params;
        let mut ok = true;
        for en in body.ensures.clone() {
            // evaluate with the current environment and `result` bound
            let saved = self.st.env.clone();
            if let Some(rl) = body.result_local {
                self.st.env.insert(rl, r.clone());
            }
            self.quiet += 1;
            let c = self.eval_cond(&en);
            self.quiet -= 1;
            self.st.env = saved;
            for f in c.pos_side.clone() {
                self.add_fact(f);
            }
            match c.pos {
                Some(fs) if !fs.is_empty() => {
                    for f in fs {
                        if !self.prove(&f) {
                            ok = false;
                        }
                    }
                }
                _ => ok = false,
            }
        }
        let name = format!("ens({})", self.c.program.fns[self.fid as usize].name);
        if self.quiet == 0 && !self.st.dead {
            let ent = self.sites.entry((sp, name)).or_insert(true);
            *ent = *ent && ok;
        }
    }

    // ------------------------------------------------------------ entry
    fn entry_facts(&mut self) {
        let body = self.body;
        let f = &self.c.program.fns[self.fid as usize];
        // parameter ranges
        for (i, pl) in body.params.iter().enumerate() {
            let p = &f.params[i];
            let ty = &body.locals[*pl as usize].ty;
            if ty.is_int() {
                let (mut lo, mut hi) = ty_range(ty);
                if let Some((rl, rh)) = p.range {
                    lo = lo.max(rl);
                    hi = hi.min(rh);
                }
                let a = self.atom_keyed(&format!("L{pl}@0"), lo, hi);
                self.st.env.insert(*pl, Sym::Int(Poly::atom(a)));
            }
        }
        // requires
        for r in body.requires.clone() {
            self.quiet += 1;
            let c = self.eval_cond(&r);
            self.quiet -= 1;
            self.add_cond(&c, true);
        }
        // invariants of parameter types (assumed for unwritten values, F-43)
        for pl in body.params.clone() {
            let ty = body.locals[pl as usize].ty.clone();
            let inner = match &ty {
                Ty::Ref(_, i) => (**i).clone(),
                t => t.clone(),
            };
            if let Ty::Adt(a, _) = &inner {
                let cx: &'a Checked = self.c;
                if let Some(inv) = cx.program.adts[*a as usize].invariant {
                    if let Some(ib) = cx.bodies.get(&inv) {
                        let arg = match &ty {
                            Ty::Ref(..) => Sym::Ref(PSym { root: format!("*L{pl}"), path: String::new(), len: None, proj: None }),
                            _ => Sym::Ref(PSym { root: format!("L{pl}"), path: String::new(), len: None, proj: None }),
                        };
                        let e = ib.expr.clone();
                        let saved_env = self.st.env.clone();
                        let saved_body = self.body;
                        let mut env = HashMap::new();
                        env.insert(ib.params[0], arg);
                        self.st.env = env;
                        self.quiet += 1;
                        self.body = ib;
                        let c = self.eval_cond(&e);
                        self.body = saved_body;
                        self.quiet -= 1;
                        self.st.env = saved_env;
                        self.add_cond(&c, true);
                    }
                }
            }
        }
    }
}

fn b_name(b: &Option<String>) -> &str {
    b.as_deref().unwrap_or("")
}

/// The local a place is rooted in without passing through a reference (`v`, `s.f`, `a[i]`, the
/// unsized view of `v`); None for places reached through a reference.
fn direct_root(p: &TExpr) -> Option<LocalId> {
    match &p.kind {
        TK::Local(l) => Some(*l),
        TK::Field(b, _) | TK::Index(b, _) => direct_root(b),
        TK::SliceRange { base, .. } => direct_root(base),
        TK::Deref(b) => match &b.kind {
            TK::Unsize(u) => match &u.kind {
                TK::Borrow(_, q) => direct_root(q),
                _ => None,
            },
            _ if !b.ty.is_ref() => direct_root(b),
            _ => None,
        },
        _ => None,
    }
}

fn pat_has_ref_mut(p: &TPat) -> bool {
    match &p.kind {
        PK::Bind { by_ref: Some(true), .. } => true,
        PK::Bind { sub: Some(s), .. } => pat_has_ref_mut(s),
        PK::Tuple(ps) | PK::Or(ps) | PK::Slice(ps, _) => ps.iter().any(pat_has_ref_mut),
        PK::Variant { fields, .. } => fields.iter().any(|(_, x)| pat_has_ref_mut(x)),
        PK::Deref(x) => pat_has_ref_mut(x),
        _ => false,
    }
}

/// (locals whose address may be used to write them, locals captured by mut by a closure of this
/// body): `&mut` of a place rooted directly in a local, a `ref mut` binding of one, and by-mut
/// closure captures.
fn addr_taken_of(c: &Checked, body: &Body) -> (BTreeSet<LocalId>, BTreeSet<LocalId>) {
    let mut taken = BTreeSet::new();
    let mut captured = BTreeSet::new();
    walk_deep(c, &body.expr, &mut |e| match &e.kind {
        TK::Borrow(true, p) => {
            if let Some(l) = direct_root(p) {
                taken.insert(l);
            }
        }
        TK::Closure(cid) => {
            if let Some(cd) = c.closures.get(*cid as usize) {
                for cap in &cd.captures {
                    if cap.mode == CaptureMode::Mut {
                        captured.insert(cap.local);
                        taken.insert(cap.local);
                    }
                }
            }
        }
        TK::Match(s, arms) => {
            if arms.iter().any(|a| pat_has_ref_mut(&a.pat)) {
                if let Some(l) = direct_root(s) {
                    taken.insert(l);
                }
            }
        }
        TK::LetCond(p, s) => {
            if pat_has_ref_mut(p) {
                if let Some(l) = direct_root(s) {
                    taken.insert(l);
                }
            }
        }
        TK::Block(stmts, _) => {
            for st in stmts {
                if let TStmt::Let { pat, init: Some(i), .. } = st {
                    if pat_has_ref_mut(pat) {
                        if let Some(l) = direct_root(i) {
                            taken.insert(l);
                        }
                    }
                }
            }
        }
        _ => {}
    });
    (taken, captured)
}

/// A type that holds a `&mut` somewhere (an `Option<&mut T>`, a tuple of references, ...).
fn ty_has_mut_ref(t: &Ty) -> bool {
    let mut h = false;
    t.walk(&mut |x| {
        if matches!(x, Ty::Ref(true, _)) {
            h = true;
        }
    });
    h
}

/// A type that may be or hold a callable value with captures.
fn ty_mentions_closure(t: &Ty) -> bool {
    let mut h = false;
    t.walk(&mut |x| {
        if matches!(x, Ty::Closure(_) | Ty::Opaque(_)) {
            h = true;
        }
    });
    h
}

/// Every trap-capable node of a body, by syntax alone (closures not entered): used when T2's
/// evaluation budget runs out, so that nothing it did not visit counts as discharged.
fn syntactic_sites(c: &Checked, e: &TExpr, out: &mut Vec<(Span, String)>) {
    let int_signed = |t: &Ty| matches!(t, Ty::Int(i) if i.signed());
    match &e.kind {
        TK::Index(..) => out.push((e.span, "idx".into())),
        TK::SliceRange { .. } => out.push((e.span, "slice".into())),
        TK::Binary(op, _, _) | TK::AssignOp(op, _, _) => {
            let t = match &e.kind {
                TK::AssignOp(_, p, _) => &p.ty,
                _ => &e.ty,
            };
            if t.is_int() {
                match op {
                    BinOp::Add | BinOp::Sub | BinOp::Mul => out.push((e.span, format!("ovf({})", op.name()))),
                    BinOp::Div | BinOp::Rem => {
                        out.push((e.span, "div0".into()));
                        if int_signed(t) {
                            out.push((e.span, "divovf".into()));
                        }
                    }
                    BinOp::Shl | BinOp::Shr => out.push((e.span, "shift".into())),
                    _ => {}
                }
            }
        }
        TK::Unary(UnOp::Neg, _) if int_signed(&e.ty) => out.push((e.span, "ovf(neg)".into())),
        TK::Call { f, .. } => {
            let fd = &c.program.fns[*f as usize];
            if c.bodies.get(f).map(|b| !b.requires.is_empty()).unwrap_or(false) {
                out.push((e.span, format!("req({})", fd.name)));
            }
            if fd.params.iter().any(|p| p.range.is_some()) {
                out.push((e.span, "range".into()));
            }
        }
        TK::Ctor { adt, .. } | TK::CtorUpdate { adt, .. } => {
            let ad = &c.program.adts[*adt as usize];
            if ad.invariant.is_some() {
                out.push((e.span, format!("inv({})", ad.name)));
            }
            if ad.variants.iter().any(|v| v.fields.iter().any(|f| f.range.is_some())) {
                out.push((e.span, "range".into()));
            }
        }
        TK::Assign(p, _) => {
            if field_range(c, p).is_some() {
                out.push((p.span, "range".into()));
            }
        }
        TK::Trap(..) => out.push((e.span, "panic".into())),
        TK::Assert { .. } | TK::AssertCmp { .. } => out.push((e.span, "assert".into())),
        _ => {}
    }
    for ch in e.children() {
        syntactic_sites(c, ch, out);
    }
}

fn div_ceil(a: i128, b: i128) -> i128 {
    let d = a / b;
    if (a % b != 0) && ((a < 0) == (b < 0)) {
        d + 1
    } else {
        d
    }
}
fn div_floor(a: i128, b: i128) -> i128 {
    let d = a / b;
    if (a % b != 0) && ((a < 0) != (b < 0)) {
        d - 1
    } else {
        d
    }
}

fn poly_text(p: &Poly) -> String {
    let mut s = String::new();
    for (m, v) in &p.t {
        s.push_str(&format!("{v}*{:?}+", m.0));
    }
    s
}

fn field_name(c: &Checked, t: &Ty, i: u32) -> String {
    match t.strip_refs() {
        Ty::Adt(a, _) => c.program.adts[*a as usize].variants.first().and_then(|v| v.fields.get(i as usize)).map(|f| f.name.clone()).unwrap_or(i.to_string()),
        _ => i.to_string(),
    }
}

/// The #[range] of the field a place reads (directly, or elementwise through an array field).
fn field_range(c: &Checked, e: &TExpr) -> Option<(i128, i128)> {
    match &e.kind {
        TK::Field(b, i) => match b.ty.strip_refs() {
            Ty::Adt(a, _) => c.program.adts[*a as usize].variants.first().and_then(|v| v.fields.get(*i as usize)).and_then(|f| f.range),
            _ => None,
        },
        TK::Index(b, _) => field_range(c, b),
        _ => None,
    }
}

/// The local a covering write's base is rooted in: `y` (local array/Vec) or `*y` (&mut slice).
fn cover_base(base: &TExpr) -> Option<LocalId> {
    match &base.kind {
        TK::Local(l) => Some(*l),
        TK::Deref(b) => match &b.kind {
            TK::Local(l) => Some(*l),
            _ => None,
        },
        _ => None,
    }
}

/// `*index_mut(&mut *y, t)`: a footprinted row projection of `y` at row `t`.
fn row_projection_base(c: &Checked, base: &TExpr) -> Option<(LocalId, LocalId)> {
    if let TK::Deref(call) = &base.kind {
        if let TK::Call { f, args, .. } = &call.kind {
            let has_fp = c.bodies.get(f).map(|b| !b.footprints.is_empty()).unwrap_or(false);
            if has_fp && args.len() == 2 {
                let recv = place_root(&args[0])?;
                if let TK::Local(t) = args[1].kind {
                    return Some((recv, t));
                }
            }
        }
    }
    None
}

/// The inner loop body writes `(*proj(y, t))[j] = e` once: returns (y, t).
fn inner_row_write(c: &Checked, body: &TExpr, j: LocalId) -> Option<(LocalId, LocalId)> {
    let stmts: Vec<&TExpr> = match &body.kind {
        TK::Block(ss, tail) => {
            let mut v: Vec<&TExpr> = ss.iter().filter_map(|s| if let TStmt::Expr(e) = s { Some(e) } else { None }).collect();
            if let Some(t) = tail {
                v.push(t);
            }
            v
        }
        _ => vec![body],
    };
    let mut found = None;
    let mut count = 0;
    for s in stmts {
        match &s.kind {
            TK::Assign(p, _) => {
                if let TK::Index(base, idx) = &p.kind {
                    if matches!(idx.kind, TK::Local(l) if l == j) {
                        if let Some(rt) = row_projection_base(c, base) {
                            found = Some(rt);
                            count += 1;
                        }
                    }
                }
            }
            TK::If(..) | TK::Match(..) => return None,
            _ => {}
        }
    }
    if count == 1 {
        found
    } else {
        None
    }
}

/// No write to `root` other than the covering write itself (premise 3).
fn no_other_writes(c: &Checked, body: &TExpr, root: LocalId, through_projection: bool) -> bool {
    let mut writes = 0;
    let mut other = false;
    walk_deep(c, body, &mut |x| match &x.kind {
        TK::Assign(p, _) | TK::AssignOp(_, p, _) => {
            if place_root(p) == Some(root) || (through_projection && row_projection_base(c, base_of(p)).map(|r| r.0) == Some(root)) {
                writes += 1;
                if matches!(x.kind, TK::AssignOp(..)) {
                    other = true;
                }
            }
        }
        TK::Borrow(true, p) => {
            if place_root(p) == Some(root) && !through_projection {
                other = true;
            }
        }
        _ => {}
    });
    // premise 3 also covers a `&mut` of p passed by implicit reborrow, or moved or copied into a
    // binding (review 2026-10-23: `poke(y)` was missed where `poke(&mut *y)` was seen, so the
    // loop strong-updated y although poke wrote raw values after the covering write)
    if !through_projection {
        let mut implicit = vec![];
        implicit_mut_uses(c, body, &mut implicit);
        if implicit.iter().any(|(r, _)| *r == root) {
            other = true;
        }
    }
    writes == 1 && !other
}

fn base_of(p: &TExpr) -> &TExpr {
    match &p.kind {
        TK::Index(b, _) | TK::Field(b, _) => b,
        _ => p,
    }
}

/// Fourier–Motzkin: is the system Σ (poly ≥ 0 | poly == 0) infeasible over the rationals?
fn fm_infeasible(sys: Vec<(Poly, bool)>) -> bool {
    // variables: non-constant monomials
    let mut ineqs: Vec<BTreeMap<Mono, i128>> = vec![];
    let mut eqs: Vec<BTreeMap<Mono, i128>> = vec![];
    for (p, eq) in sys {
        if eq {
            eqs.push(p.t);
        } else {
            ineqs.push(p.t);
        }
    }
    let k0 = Mono(vec![]);
    // eliminate equalities by substitution
    while let Some(e) = eqs.pop() {
        let var = e.iter().filter(|(m, _)| !m.0.is_empty()).min_by_key(|(_, v)| v.abs()).map(|(m, v)| (m.clone(), *v));
        let Some((x, a)) = var else {
            if e.get(&k0).copied().unwrap_or(0) != 0 {
                return true;
            }
            continue;
        };
        let subst = |row: &BTreeMap<Mono, i128>| -> Option<BTreeMap<Mono, i128>> {
            let b = match row.get(&x) {
                Some(b) => *b,
                None => return Some(row.clone()),
            };
            // row*|a| - sign(a)*b*e
            let s = a.signum();
            let mut out: BTreeMap<Mono, i128> = BTreeMap::new();
            for (m, v) in row {
                *out.entry(m.clone()).or_insert(0) = v.checked_mul(a.abs())?;
            }
            for (m, v) in &e {
                let t = v.checked_mul(b)?.checked_mul(s)?;
                let ent = out.entry(m.clone()).or_insert(0);
                *ent = ent.checked_sub(t)?;
            }
            out.retain(|_, v| *v != 0);
            Some(normalize_row(out))
        };
        let mut ni = vec![];
        for r in &ineqs {
            match subst(r) {
                Some(x) => ni.push(x),
                None => return false,
            }
        }
        let mut ne = vec![];
        for r in &eqs {
            match subst(r) {
                Some(x) => ne.push(x),
                None => return false,
            }
        }
        ineqs = ni;
        eqs = ne;
    }
    // Fourier–Motzkin on the inequalities
    ineqs = tightest(ineqs);
    for _ in 0..40 {
        // constant rows
        for r in &ineqs {
            if r.keys().all(|m| m.0.is_empty()) && r.get(&k0).copied().unwrap_or(0) < 0 {
                return true;
            }
        }
        ineqs.retain(|r| !r.keys().all(|m| m.0.is_empty()));
        if ineqs.is_empty() {
            return false;
        }
        // pick the variable with the fewest pos*neg pairs
        let mut vars: BTreeMap<Mono, (usize, usize)> = BTreeMap::new();
        for r in &ineqs {
            for (m, v) in r {
                if m.0.is_empty() {
                    continue;
                }
                let e = vars.entry(m.clone()).or_insert((0, 0));
                if *v > 0 {
                    e.0 += 1;
                } else {
                    e.1 += 1;
                }
            }
        }
        let Some((x, _)) = vars.iter().min_by_key(|(_, (p, n))| p * n) else { return false };
        let x = x.clone();
        let (pos, rest): (Vec<_>, Vec<_>) = ineqs.into_iter().partition(|r| r.get(&x).copied().unwrap_or(0) > 0);
        let (neg, zero): (Vec<_>, Vec<_>) = rest.into_iter().partition(|r| r.get(&x).copied().unwrap_or(0) < 0);
        let mut next = zero;
        for p in &pos {
            for n in &neg {
                let a = p[&x];
                let b = -n[&x];
                let mut out: BTreeMap<Mono, i128> = BTreeMap::new();
                let mut ovf = false;
                for (m, v) in p {
                    match v.checked_mul(b) {
                        Some(t) => *out.entry(m.clone()).or_insert(0) += t,
                        None => ovf = true,
                    }
                }
                for (m, v) in n {
                    match v.checked_mul(a) {
                        Some(t) => {
                            let e = out.entry(m.clone()).or_insert(0);
                            match e.checked_add(t) {
                                Some(s) => *e = s,
                                None => ovf = true,
                            }
                        }
                        None => ovf = true,
                    }
                }
                if ovf {
                    continue;
                }
                out.retain(|_, v| *v != 0);
                next.push(normalize_row(out));
            }
        }
        if next.len() > 400 {
            return false;
        }
        ineqs = tightest(next);
    }
    false
}

/// Of inequalities with the same variable part, only the one with the smallest constant matters
/// (`v + c >= 0` for the least c implies the others).
fn tightest(rows: Vec<BTreeMap<Mono, i128>>) -> Vec<BTreeMap<Mono, i128>> {
    let k0 = Mono(vec![]);
    let mut best: BTreeMap<Vec<(Mono, i128)>, i128> = BTreeMap::new();
    for r in rows {
        let c = r.get(&k0).copied().unwrap_or(0);
        let vars: Vec<(Mono, i128)> = r.into_iter().filter(|(m, _)| !m.0.is_empty()).collect();
        let e = best.entry(vars).or_insert(c);
        if c < *e {
            *e = c;
        }
    }
    best.into_iter()
        .map(|(vars, c)| {
            let mut r: BTreeMap<Mono, i128> = vars.into_iter().collect();
            if c != 0 {
                r.insert(k0.clone(), c);
            }
            r
        })
        .collect()
}

fn normalize_row(mut r: BTreeMap<Mono, i128>) -> BTreeMap<Mono, i128> {
    let mut g: i128 = 0;
    for v in r.values() {
        g = gcd(g, v.abs());
    }
    if g > 1 {
        for v in r.values_mut() {
            *v /= g;
        }
    }
    r
}

fn gcd(a: i128, b: i128) -> i128 {
    if b == 0 {
        a
    } else {
        gcd(b, a % b)
    }
}

// ---------------------------------------------------------------- driver

pub fn analyze(c: &Checked, fid: FnId) -> Option<T2Result> {
    let body = c.bodies.get(&fid)?;
    let mut ev = Ev::new(c, fid, body);
    ev.entry_facts();
    // the receiver's place before the body runs (for the footprint comparison)
    let r = ev.eval(&body.expr);
    if !ev.st.dead && !body.ensures.is_empty() {
        ev.check_ensures(&r, body.expr.span);
    }
    if ev.exhausted {
        mark_exhausted(c, &mut ev.sites, &body.expr);
        if !body.ensures.is_empty() {
            let name = format!("ens({}) (T2 budget exhausted)", c.program.fns[fid as usize].name);
            ev.sites.insert((body.expr.span, name), false);
        }
    }
    let mut footprint_ok = None;
    if let Some(fp) = body.footprints.first() {
        // E-FOOTPRINT (F-45): the result's loan targets exactly the declared sub-place
        ev.quiet += 1;
        let decl = ev.place(fp);
        ev.quiet -= 1;
        let ok = match &r {
            Sym::Ref(ps) => ps.root == decl.root && ps.path == decl.path,
            _ => false,
        };
        // and the body writes nothing through its receiver
        let mut writes = false;
        walk_deep(c, &body.expr, &mut |e| {
            if let TK::Assign(p, _) | TK::AssignOp(_, p, _) = &e.kind {
                if let Some(root) = place_root(p) {
                    if body.params.first() == Some(&root) {
                        writes = true;
                    }
                }
            }
        });
        footprint_ok = Some(ok && !writes);
    }
    let sites = ev.sites.iter().map(|((sp, k), ok)| (*sp, k.clone(), *ok)).collect();
    Some(T2Result { footprint_ok, sites, covers: ev.covers, row_covers: ev.row_covers })
}

/// The evaluation budget ran out: every trap-capable site of the body is undischarged, whatever
/// was proved before (review 2026-10-16: sites after the cut-off were silently discharged).
fn mark_exhausted(c: &Checked, sites: &mut BTreeMap<(Span, String), bool>, e: &TExpr) {
    let mut all = vec![];
    syntactic_sites(c, e, &mut all);
    sites.clear();
    for (sp, k) in all {
        sites.insert((sp, format!("{k} (T2 budget exhausted)")), false);
    }
}

fn closure_sites(c: &Checked, fid: FnId) -> Vec<(Span, String)> {
    // traps inside closures created by fid: analysed without facts (their parameters are unknown)
    let mut out = vec![];
    let Some(body) = c.bodies.get(&fid) else { return out };
    let mut cids = vec![];
    walk_deep(c, &body.expr, &mut |e| {
        if let TK::Closure(cid) = e.kind {
            cids.push(cid);
        }
    });
    for cid in cids {
        let cd = &c.closures[cid as usize];
        let fake = Body {
            fid,
            locals: body.locals.clone(),
            params: vec![],
            expr: cd.body.clone(),
            requires: vec![],
            ensures: vec![],
            footprints: vec![],
            result_local: None,
            n_loops: body.n_loops,
            loop_spans: vec![],
        };
        let mut ev = Ev::new(c, fid, &fake);
        ev.eval(&cd.body);
        if ev.exhausted {
            mark_exhausted(c, &mut ev.sites, &cd.body);
        }
        for ((sp, k), ok) in ev.sites {
            if !ok {
                out.push((sp, k));
            }
        }
    }
    out
}

pub fn run(c: &mut Checked) {
    let fids: Vec<FnId> = c.bodies.keys().copied().collect();
    let mut local_sites: HashMap<FnId, Vec<(Span, String)>> = HashMap::new();
    for fid in &fids {
        let f = &c.program.fns[*fid as usize];
        if f.role == FileRole::Std || f.builtin.is_some() || f.body.is_none() {
            continue;
        }
        let Some(r) = analyze(c, *fid) else { continue };
        let mut und: Vec<(Span, String)> = r.sites.iter().filter(|(_, _, ok)| !ok).map(|(s, k, _)| (*s, k.clone())).collect();
        for (sp, _) in &und {
            c.facts.undischarged.insert((*fid, *sp));
        }
        und.extend(closure_sites(c, *fid));
        if r.footprint_ok == Some(false) {
            let f = &c.program.fns[*fid as usize];
            let sp = c.bodies[fid].footprints[0].span;
            c.diags.push(Diag::new("E-FOOTPRINT", sp, format!("`{}`'s result does not borrow exactly its declared footprint (or the body writes through its receiver); a wrong footprint would turn a `par for` into a data race (F-45)", f.name)).in_def(&f.path));
        }
        for (l, root) in r.covers {
            c.facts.covers.entry((*fid, l)).or_default().push(root);
        }
        for (l, root) in r.row_covers {
            c.facts.row_covers.insert((*fid, l), root);
        }
        local_sites.insert(*fid, und);
    }
    // may_trap: least fixpoint over the call graph
    let n = c.program.fns.len() as FnId;
    let mut mt: HashMap<FnId, bool> = HashMap::new();
    for fid in 0..n {
        let f = &c.program.fns[fid as usize];
        let v = match &f.builtin {
            Some(b) => super::stdfacts::may_trap(b),
            None => {
                if f.body.is_none() {
                    // a trait method declaration: may_trap is not part of trait signatures, so a
                    // call through a type parameter may trap (derivation D-D01); bodiless prelude
                    // signatures: kernels are trap-free by construction, others are assumed total
                    // (section P states may_trap where it matters)
                    matches!(f.owner, crate::program::Owner::Trait(_)) && f.role != FileRole::Std
                } else {
                    local_sites.get(&fid).map(|v| !v.is_empty()).unwrap_or(false)
                }
            }
        };
        mt.insert(fid, v);
    }
    let calls: HashMap<FnId, Vec<FnId>> = fids.iter().map(|f| (*f, callees(c, *f).into_iter().map(|x| x.0).collect())).collect();
    loop {
        let mut changed = false;
        for fid in &fids {
            if mt[fid] {
                continue;
            }
            if c.program.fns[*fid as usize].builtin.is_some() {
                continue;
            }
            if calls.get(fid).map(|cs| cs.iter().any(|t| *mt.get(t).unwrap_or(&false))).unwrap_or(false) {
                mt.insert(*fid, true);
                changed = true;
            }
        }
        if !changed {
            break;
        }
    }
    // kernels: (k2)
    let mut diags = vec![];
    for fid in &fids {
        let f = &c.program.fns[*fid as usize];
        if f.role == FileRole::Std {
            continue;
        }
        let sites = local_sites.get(fid).cloned().unwrap_or_default();
        if f.kind == FnKind::Kernel {
            for (sp, k) in &sites {
                diags.push(Diag::new("E-KERNEL-OBLIGATION", *sp, format!("in a kernel, the obligation `{k}` must be discharged statically (DR-011); T2 cannot prove it from the path facts")).in_def(&f.path));
            }
        }
        let ff = c.facts.fns.entry(*fid).or_default();
        ff.may_trap = mt[fid];
        ff.trap_sites = sites.iter().map(|(sp, k)| format!("{k} at {}", c.program.sm.snippet(*sp))).collect();
    }
    for fid in 0..n {
        if !c.facts.fns.contains_key(&fid) && c.program.fns[fid as usize].role != FileRole::Std {
            c.facts.fns.entry(fid).or_default().may_trap = mt[&fid];
        }
    }
    c.diags.extend(diags);
    MAY_TRAP.with(|m| *m.borrow_mut() = mt);
}

thread_local! {
    static MAY_TRAP: std::cell::RefCell<HashMap<FnId, bool>> = std::cell::RefCell::new(HashMap::new());
}

pub fn may_trap_of(fid: FnId) -> bool {
    MAY_TRAP.with(|m| *m.borrow().get(&fid).unwrap_or(&false))
}

pub fn loop_vars_written(_c: &Checked) -> BTreeMap<u32, u32> {
    BTreeMap::new()
}
