//! The checker driver: build, type-check and run the MCore analyses; report diagnostics in the
//! precedence order of note section 5.16.

use crate::diag::{sort_diags, Diag, FileRole, SourceMap};
use crate::lower::{build, SourceInput};
use crate::program::Program;
use crate::typeck::{Options, Typeck};
use std::collections::HashMap;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Subset {
    /// note section 12: the checker's X1 scope (typing-only acceptance of par, det, schedule,
    /// spec, linear) — the scope the core-calculus gate is judged on. Provisional, pending Q9.
    Checker,
    /// X1 design section 9.1: the agent subset, which rejects those constructs with E-X1-NOTYET.
    Agent,
}

#[derive(Clone)]
pub struct Config {
    pub inputs: Vec<SourceInput>,
    pub doc_snippets: bool,
    pub loose_host: Option<String>,
    /// mith.toml [grants] declare_deterministic
    pub declare_deterministic: Vec<String>,
    pub grant_unsafe: Vec<String>,
    pub grant_foreign: Vec<String>,
    /// evidence fixtures (in addition to prelude `evidence` items): (name, kind, subject, grade)
    pub fixtures: Vec<(String, String, String, String)>,
    pub subset: Subset,
    /// the "Mithril without traits" arm (E-TRAIT-OFF)
    pub no_user_traits: bool,
}

impl Default for Config {
    fn default() -> Self {
        Config {
            inputs: vec![],
            doc_snippets: false,
            loose_host: None,
            declare_deterministic: vec![],
            grant_unsafe: vec![],
            grant_foreign: vec![],
            fixtures: vec![],
            subset: Subset::Checker,
            no_user_traits: false,
        }
    }
}

pub struct Checked {
    pub program: Program,
    pub bodies: HashMap<u32, crate::thir::Body>,
    pub closures: Vec<crate::thir::ClosureDef>,
    pub const_vals: HashMap<u32, crate::thir::TExpr>,
    pub diags: Vec<Diag>,
    pub facts: crate::analysis::Facts,
}

impl Checked {
    pub fn sm(&self) -> &SourceMap {
        &self.program.sm
    }
    /// Errors (not warnings), sorted by precedence.
    pub fn errors(&self) -> Vec<&Diag> {
        self.diags.iter().filter(|d| !d.warning).collect()
    }
    pub fn primary(&self) -> Option<&Diag> {
        self.errors().into_iter().next()
    }
}

pub fn check(cfg: &Config) -> Checked {
    let built = build(&cfg.inputs);
    let mut program = built.program;
    let mut diags = std::mem::take(&mut program.diags);
    // fixtures from the configuration
    for (n, k, s, g) in &cfg.fixtures {
        program.evidences.push(crate::program::Evidence { name: n.clone(), kind: k.clone(), subject: s.clone(), grade: g.clone(), span: crate::diag::Span::DUMMY });
    }
    let (bodies, closures, const_vals, tdiags) = {
        let mut tc = Typeck::new(&program, Options { doc_snippets: cfg.doc_snippets, loose_host: cfg.loose_host.clone() });
        tc.check_all();
        (tc.bodies, tc.closures, tc.const_vals, tc.diags)
    };
    diags.extend(tdiags);
    // a free or inherent function in user code needs a body, as in Rust; a signature alone is
    // documentation shorthand (`--doc-snippets`, item N-03) or a trait's required method
    if !cfg.doc_snippets {
        for f in &program.fns {
            if f.role == FileRole::User && f.body.is_none() && f.builtin.is_none() && f.synthetic.is_none() && !matches!(f.owner, crate::program::Owner::Trait(_)) {
                diags.push(Diag::new("E-TYPE", f.sig_span, format!("`{}` has no body: a function outside a trait needs one (write `todo!(\"{}\")` for a hole)", f.name, f.name)).in_def(&f.path));
            }
        }
    }
    let mut checked = Checked { program, bodies, closures, const_vals, diags, facts: Default::default() };
    crate::analysis::run(&mut checked, cfg);
    // out-of-scope occurrences (note section 12): E-OUT-OF-SCOPE-<KW>
    for (kw, sp) in checked.program.oos.clone() {
        checked.diags.push(Diag::new(&format!("E-OUT-OF-SCOPE-{kw}"), sp, format!("`{}` is outside the checker's X1 scope (note section 12, Q10)", kw.to_lowercase())));
    }
    // diagnostics in std are mithi bugs; keep them visible but separate
    let sm = checked.program.sm.clone();
    for d in checked.diags.iter_mut() {
        if sm.role(d.span) == FileRole::Std && !d.span.is_dummy() {
            d.notes.push("in mithi's std (a mithi bug)".into());
        }
    }
    dedup(&mut checked.diags);
    sort_diags(&mut checked.diags);
    checked
}

fn dedup(ds: &mut Vec<Diag>) {
    let mut seen = std::collections::HashSet::new();
    ds.retain(|d| seen.insert((d.code.clone(), d.span, d.msg.clone())));
}
