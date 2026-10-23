//! Source files, spans and diagnostics.
//!
//! Codes follow docs/m0/core-calculus.md section 5.16. Codes that the note does not name and that
//! mithi had to introduce are listed in `MITHI_CODES` and are provisional [prov, mithi].

use std::fmt::Write as _;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Default, PartialOrd, Ord)]
pub struct Span {
    pub file: u16,
    pub lo: u32,
    pub hi: u32,
}

impl Span {
    pub const DUMMY: Span = Span { file: u16::MAX, lo: 0, hi: 0 };
    pub fn new(file: u16, lo: u32, hi: u32) -> Span {
        Span { file, lo, hi }
    }
    pub fn to(self, other: Span) -> Span {
        if self.file != other.file {
            return self;
        }
        Span { file: self.file, lo: self.lo.min(other.lo), hi: self.hi.max(other.hi) }
    }
    pub fn is_dummy(&self) -> bool {
        self.file == u16::MAX
    }
}

#[derive(Clone, Debug)]
pub struct SourceFile {
    pub name: String,
    pub text: String,
    /// Role of the file: "std", "prelude" or "user". Diagnostics in "std" are mithi bugs.
    pub role: FileRole,
    line_starts: Vec<u32>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum FileRole {
    Std,
    Prelude,
    User,
}

impl SourceFile {
    pub fn new(name: &str, text: &str, role: FileRole) -> SourceFile {
        let mut line_starts = vec![0u32];
        for (i, b) in text.bytes().enumerate() {
            if b == b'\n' {
                line_starts.push(i as u32 + 1);
            }
        }
        SourceFile { name: name.to_string(), text: text.to_string(), role, line_starts }
    }
    /// 1-based line and column (column in bytes).
    pub fn line_col(&self, pos: u32) -> (u32, u32) {
        let idx = match self.line_starts.binary_search(&pos) {
            Ok(i) => i,
            Err(i) => i - 1,
        };
        (idx as u32 + 1, pos - self.line_starts[idx] + 1)
    }
}

#[derive(Default, Debug, Clone)]
pub struct SourceMap {
    pub files: Vec<SourceFile>,
}

impl SourceMap {
    pub fn add(&mut self, name: &str, text: &str, role: FileRole) -> u16 {
        self.files.push(SourceFile::new(name, text, role));
        (self.files.len() - 1) as u16
    }
    pub fn snippet(&self, sp: Span) -> String {
        if sp.is_dummy() {
            return String::new();
        }
        let f = &self.files[sp.file as usize];
        let lo = (sp.lo as usize).min(f.text.len());
        let hi = (sp.hi as usize).min(f.text.len()).max(lo);
        let s = &f.text[lo..hi];
        let one: String = s.split_whitespace().collect::<Vec<_>>().join(" ");
        if one.chars().count() > 120 {
            let t: String = one.chars().take(117).collect();
            format!("{t}...")
        } else {
            one
        }
    }
    pub fn loc(&self, sp: Span) -> String {
        if sp.is_dummy() {
            return "<builtin>".to_string();
        }
        let f = &self.files[sp.file as usize];
        let (l, c) = f.line_col(sp.lo);
        format!("{}:{}:{}", f.name, l, c)
    }
    pub fn role(&self, sp: Span) -> FileRole {
        if sp.is_dummy() {
            return FileRole::Std;
        }
        self.files[sp.file as usize].role
    }
}

/// Codes mithi introduced because the note does not name one. Each is provisional.
/// E-MOVE-USED left this list on 2026-10-23: the note's §5.16 now names it (review of the round-3
/// sync, finding 2; F-124).
pub const MITHI_CODES: &[(&str, &str)] = &[
    ("E-PARSE", "the text is not in the surface grammar (no note code: syntax errors precede every class)"),
    ("E-UNRESOLVED", "a name that resolves to nothing (reported under class 1 like E-TYPE)"),
    ("E-X1-NOTYET-CANON", "whole-task canon helper (X1 design 5.1a); also used in checker scope"),
    ("E-HOST-UNSUPPORTED", "a construct mithi v0 can type but not execute (runtime only)"),
    ("E-GRANT-LOSSY", "a `lossy` grade label: reserved, no producer in v0 (note section 5.2 names no code)"),
    ("E-SCHED-TARGET", "a schedule whose subject is not a kernel fn, or whose target or feature is not in the catalogue (s1 names no code)"),
];

#[derive(Clone, Debug)]
pub struct Diag {
    pub code: String,
    pub msg: String,
    pub span: Span,
    /// The definition the diagnostic is in, as a path ("store::acquire").
    pub def: Option<String>,
    pub notes: Vec<String>,
    pub warning: bool,
}

impl Diag {
    pub fn new(code: &str, span: Span, msg: impl Into<String>) -> Diag {
        Diag { code: code.to_string(), msg: msg.into(), span, def: None, notes: vec![], warning: false }
    }
    pub fn warn(code: &str, span: Span, msg: impl Into<String>) -> Diag {
        let mut d = Diag::new(code, span, msg);
        d.warning = true;
        d
    }
    pub fn note(mut self, n: impl Into<String>) -> Diag {
        self.notes.push(n.into());
        self
    }
    pub fn in_def(mut self, d: &str) -> Diag {
        self.def = Some(d.to_string());
        self
    }
    /// Precedence class of note section 5.16 (0 = parse errors, before class 1).
    pub fn class(&self) -> u8 {
        precedence_class(&self.code)
    }
    pub fn kind(&self) -> &'static str {
        kind_of(&self.code)
    }
}

pub fn precedence_class(code: &str) -> u8 {
    let c = code;
    if c == "E-PARSE" {
        return 0;
    }
    if c.starts_with("E-OUT-OF-SCOPE-") || c.starts_with("E-X1-NOTYET") {
        return 1;
    }
    match c {
        "E-DYN" | "E-REF-FIELD" | "E-LIFETIME" | "E-LOCAL-INSTANTIATE" | "E-LINEAR-INSTANTIATE"
        | "E-FF-CELL" | "E-DROP-IMPL" | "E-GLOBAL-STATE" | "E-TYPE" | "E-UNRESOLVED" | "E-ASYNC"
        | "E-SPECIALIZE" | "E-LINEAR-COPY" | "E-COHERENCE" | "E-MONO-DEPTH" => return 1,
        _ => {}
    }
    if c.starts_with("E-FF-") || c == "E-AMBIENT-IO" || c == "E-MACRO" || c == "E-TRAIT-OFF" {
        return 2;
    }
    if c == "E-ROW-UNDECLARED" || c.starts_with("E-GRANT-") || c == "E-FP-ENV" || c == "E-DET-GRANT"
        || c == "E-IMPL-ROW"
    {
        return 3;
    }
    if c.starts_with("E-BORROW-") || c.starts_with("E-MOVE-") || c.starts_with("E-LOCAL-")
        || c == "E-REF-ESCAPE" || c.starts_with("E-LINEAR-") || c == "E-FOOTPRINT"
    {
        return 4;
    }
    if c.starts_with("E-PAR-") || c.starts_with("E-DET-") {
        return 5;
    }
    if c == "E-GRADE" || c == "E-NAN-RAW-SINK" || c == "E-IMPL-GRADE" {
        return 6;
    }
    if c.starts_with("E-KERNEL-") || c.starts_with("E-TO-") || c.starts_with("E-SCHED-")
        || c.starts_with("E-CLAIM-") || c.starts_with("E-SPEC-") || c.starts_with("E-FMT-")
    {
        return 7;
    }
    8
}

fn kind_of(code: &str) -> &'static str {
    match precedence_class(code) {
        0 => "Syntax",
        1 => {
            if code.starts_with("E-OUT-OF-SCOPE") || code.starts_with("E-X1-NOTYET") {
                "Scope"
            } else {
                "Type"
            }
        }
        2 => "FalseFriend",
        3 => "Effect",
        4 => "Ownership",
        5 => {
            if code.starts_with("E-PAR") {
                "Par"
            } else {
                "Evidence"
            }
        }
        6 => "Grade",
        7 => "SideJudgement",
        _ => "Other",
    }
}

/// Sort key: class, then (out-of-scope first inside class 1), then source position (the anchor),
/// then, at one anchor, the code's spelling in byte order (note section 5.16 and F-117, round-3
/// sync 2026-10-23; before, ties kept the order the passes emitted them in).
pub fn sort_diags(ds: &mut [Diag]) {
    ds.sort_by(|a, b| {
        let ka = (a.warning, a.class(), sub_rank(a), a.span.file, a.span.lo, a.code.as_str());
        let kb = (b.warning, b.class(), sub_rank(b), b.span.file, b.span.lo, b.code.as_str());
        ka.cmp(&kb)
    });
}

fn sub_rank(d: &Diag) -> u8 {
    if d.code.starts_with("E-OUT-OF-SCOPE-") {
        0
    } else {
        1
    }
}

pub fn json_escape(s: &str) -> String {
    let mut o = String::with_capacity(s.len() + 2);
    for ch in s.chars() {
        match ch {
            '"' => o.push_str("\\\""),
            '\\' => o.push_str("\\\\"),
            '\n' => o.push_str("\\n"),
            '\r' => o.push_str("\\r"),
            '\t' => o.push_str("\\t"),
            c if (c as u32) < 0x20 => {
                let _ = write!(o, "\\u{:04x}", c as u32);
            }
            c => o.push(c),
        }
    }
    o
}

pub fn render_text(sm: &SourceMap, d: &Diag) -> String {
    let mut s = String::new();
    let lvl = if d.warning { "warning" } else { "error" };
    let _ = write!(s, "{lvl}[{}] {}: {}", d.code, sm.loc(d.span), d.msg);
    if let Some(def) = &d.def {
        let _ = write!(s, " (in {def})");
    }
    let snip = sm.snippet(d.span);
    if !snip.is_empty() {
        let _ = write!(s, "\n    at: {snip}");
    }
    for n in &d.notes {
        let _ = write!(s, "\n    note: {n}");
    }
    s
}

pub fn render_json(sm: &SourceMap, d: &Diag) -> String {
    let mut s = String::new();
    s.push('{');
    let _ = write!(s, "\"code\":\"{}\",\"kind\":\"{}\",\"class\":{},", json_escape(&d.code), d.kind(), d.class());
    let _ = write!(s, "\"severity\":\"{}\",", if d.warning { "warning" } else { "error" });
    let _ = write!(s, "\"message\":\"{}\",", json_escape(&d.msg));
    let _ = write!(
        s,
        "\"at\":{{\"def\":{},\"anchor\":\"{}\",\"loc\":\"{}\"}}",
        match &d.def {
            Some(x) => format!("\"{}\"", json_escape(x)),
            None => "null".to_string(),
        },
        json_escape(&sm.snippet(d.span)),
        json_escape(&sm.loc(d.span))
    );
    if !d.notes.is_empty() {
        s.push_str(",\"notes\":[");
        for (i, n) in d.notes.iter().enumerate() {
            if i > 0 {
                s.push(',');
            }
            let _ = write!(s, "\"{}\"", json_escape(n));
        }
        s.push(']');
    }
    s.push('}');
    s
}
