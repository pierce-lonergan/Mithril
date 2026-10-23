//! Recursive-descent parser for the X1 surface described by grammar/mithril_v0.lark. It is a
//! hand-written Rust-style parser, not generated from the grammar, and it accepts a superset: the
//! Rust forms it parses only so that the checker can name them (lifetimes, `unsafe`, `async`,
//! raw pointers, qualified types, unknown macros), documentation shorthand `…`, bodiless
//! functions and loose `let` statements, and Rust's whitespace rules (the grammar requires
//! whitespace after a keyword before a word or bracket in a few places). grammar/test_grammar.py
//! compares the two on accept/reject (crates/mithi/README.md, "Grammar and parser").

use crate::ast::*;
use crate::diag::{Diag, Span};
use crate::lexer::{Tok, Token};

#[allow(dead_code)]
pub struct Parser {
    toks: Vec<Token>,
    pos: usize,
    file: u16,
    /// Allow prelude-only items (evidence, seam, target) and opaque declarations.
    pub prelude: bool,
    /// set when a field list contained `…` (a partial prelude declaration)
    saw_ellipsis: bool,
    /// current syntactic nesting depth (E-PARSE beyond `MAX_NEST`)
    nest: u32,
    /// the enclosing break targets: (label, is a labelled block, synthetic label given to an
    /// unlabelled loop that a `continue` inside a labelled block targets)
    brk: Vec<(Option<String>, bool, Option<String>)>,
    synth: u32,
}

/// Deepest syntactic nesting accepted (parentheses, blocks, unary operators, types, patterns,
/// items). Beyond it the parse is E-PARSE, so that no recursive pass can exhaust the stack
/// (review 2026-10-16: depth 400 aborted the process).
pub const MAX_NEST: u32 = 512;

type PResult<T> = Result<T, Diag>;

const STRICT_KW: &[&str] = &[
    "as", "break", "const", "continue", "crate", "else", "enum", "extern", "false", "fn", "for", "if", "impl",
    "in", "let", "loop", "match", "mod", "move", "mut", "pub", "ref", "return", "self", "Self", "static",
    "struct", "super", "trait", "true", "type", "unsafe", "use", "where", "while", "async", "await", "dyn",
];

fn is_strict_kw(s: &str) -> bool {
    STRICT_KW.contains(&s)
}

impl Parser {
    pub fn new(toks: Vec<Token>, file: u16) -> Parser {
        Parser { toks, pos: 0, file, prelude: false, saw_ellipsis: false, nest: 0, brk: vec![], synth: 0 }
    }

    /// A loop body, with the loop as the innermost break target; returns the label the loop
    /// gets (its own, or a synthetic one a `continue` inside a labelled block asked for).
    fn loop_body(&mut self, lbl: Option<String>) -> PResult<(Option<String>, Block)> {
        self.brk.push((lbl.clone(), false, None));
        let b = self.block();
        let (_, _, synth) = self.brk.pop().unwrap_or((None, false, None));
        Ok((lbl.or(synth), b?))
    }

    fn enter(&mut self) -> PResult<()> {
        self.nest += 1;
        if self.nest > MAX_NEST {
            self.nest -= 1;
            return Err(Diag::new("E-PARSE", self.span(), format!("nesting too deep (more than {MAX_NEST} levels)")));
        }
        Ok(())
    }

    // ------------------------------------------------------------------ token helpers
    fn peek(&self) -> &Tok {
        &self.toks[self.pos].tok
    }
    fn peek_at(&self, n: usize) -> &Tok {
        let i = (self.pos + n).min(self.toks.len() - 1);
        &self.toks[i].tok
    }
    fn span(&self) -> Span {
        self.toks[self.pos].span
    }
    fn prev_span(&self) -> Span {
        if self.pos == 0 {
            self.span()
        } else {
            self.toks[self.pos - 1].span
        }
    }
    fn bump(&mut self) -> Token {
        let t = self.toks[self.pos].clone();
        if self.pos < self.toks.len() - 1 {
            self.pos += 1;
        }
        t
    }
    fn is_punct(&self, p: &str) -> bool {
        matches!(self.peek(), Tok::Punct(q) if *q == p)
    }
    fn is_punct_at(&self, n: usize, p: &str) -> bool {
        matches!(self.peek_at(n), Tok::Punct(q) if *q == p)
    }
    fn is_word(&self, w: &str) -> bool {
        matches!(self.peek(), Tok::Ident(s) if s == w)
    }
    fn is_word_at(&self, n: usize, w: &str) -> bool {
        matches!(self.peek_at(n), Tok::Ident(s) if s == w)
    }
    fn is_ident_at(&self, n: usize) -> bool {
        matches!(self.peek_at(n), Tok::Ident(s) if !is_strict_kw(s) || s == "self" || s == "Self" || s == "crate" || s == "super")
    }
    fn eat_punct(&mut self, p: &str) -> bool {
        if self.is_punct(p) {
            self.bump();
            true
        } else {
            false
        }
    }
    fn eat_word(&mut self, w: &str) -> bool {
        if self.is_word(w) {
            self.bump();
            true
        } else {
            false
        }
    }
    fn err<T>(&self, msg: impl Into<String>) -> PResult<T> {
        Err(Diag::new("E-PARSE", self.span(), format!("{} (found {})", msg.into(), self.describe())))
    }
    fn describe(&self) -> String {
        match self.peek() {
            Tok::Ident(s) => format!("`{s}`"),
            Tok::Int(v, _) => format!("integer `{v}`"),
            Tok::Float(s, _) => format!("float `{s}`"),
            Tok::Str(_) => "string literal".into(),
            Tok::Char(c) => format!("char {c:?}"),
            Tok::Lifetime(l) => format!("lifetime `'{l}`"),
            Tok::Punct(p) => format!("`{p}`"),
            Tok::Ellipsis => "`…`".into(),
            Tok::Eof => "end of input".into(),
        }
    }
    fn expect_punct(&mut self, p: &str) -> PResult<Span> {
        if self.is_punct(p) {
            Ok(self.bump().span)
        } else {
            self.err(format!("expected `{p}`"))
        }
    }
    fn expect_word(&mut self, w: &str) -> PResult<Span> {
        if self.is_word(w) {
            Ok(self.bump().span)
        } else {
            self.err(format!("expected `{w}`"))
        }
    }
    fn ident(&mut self) -> PResult<Ident> {
        match self.peek().clone() {
            Tok::Ident(s) if !is_strict_kw(&s) || s == "self" || s == "Self" || s == "crate" || s == "super" => {
                let sp = self.bump().span;
                Ok(Ident { name: s, span: sp })
            }
            _ => self.err("expected an identifier"),
        }
    }
    /// Any word, including keywords (for directive words and claim kinds).
    fn any_word(&mut self) -> PResult<Ident> {
        match self.peek().clone() {
            Tok::Ident(s) => {
                let sp = self.bump().span;
                Ok(Ident { name: s, span: sp })
            }
            _ => self.err("expected a word"),
        }
    }
    /// Split a compound token starting with `>` so that one `>` can be consumed.
    fn expect_gt(&mut self) -> PResult<()> {
        let sp = self.span();
        let rest: Option<&'static str> = match self.peek() {
            Tok::Punct(">") => None,
            Tok::Punct(">>") => Some(">"),
            Tok::Punct(">=") => Some("="),
            Tok::Punct(">>=") => Some(">="),
            _ => return self.err("expected `>`"),
        };
        match rest {
            None => {
                self.bump();
            }
            Some(r) => {
                self.toks[self.pos].tok = Tok::Punct(r);
                self.toks[self.pos].span = Span::new(sp.file, sp.lo + 1, sp.hi);
            }
        }
        Ok(())
    }
    fn is_gt_like(&self) -> bool {
        matches!(self.peek(), Tok::Punct(">") | Tok::Punct(">>") | Tok::Punct(">=") | Tok::Punct(">>="))
    }

    // ------------------------------------------------------------------ file
    pub fn parse_file(&mut self) -> PResult<Vec<Item>> {
        let mut items = Vec::new();
        while !matches!(self.peek(), Tok::Eof) {
            if self.is_punct(";") {
                self.bump();
                continue;
            }
            items.push(self.item()?);
        }
        Ok(items)
    }

    fn attrs(&mut self) -> PResult<Vec<Attr>> {
        let mut out = Vec::new();
        loop {
            if self.is_punct("#") && self.is_punct_at(1, "!") && self.is_punct_at(2, "[") {
                // inner attribute: skip
                self.bump();
                self.bump();
                self.skip_balanced()?;
                continue;
            }
            if self.is_punct("#") && self.is_punct_at(1, "[") {
                let start = self.bump().span;
                self.bump(); // [
                let name = self.path_simple()?;
                let mut args = Vec::new();
                if self.is_punct("(") {
                    args = self.attr_args()?;
                } else if self.eat_punct("=") {
                    let t = self.bump();
                    args.push(tok_text(&t.tok));
                }
                let end = self.expect_punct("]")?;
                out.push(Attr { name: name.text(), args, span: start.to(end) });
                continue;
            }
            break;
        }
        Ok(out)
    }

    /// Attribute arguments in parentheses, rendered as text and split at top-level commas.
    fn attr_args(&mut self) -> PResult<Vec<String>> {
        self.expect_punct("(")?;
        let mut args = Vec::new();
        let mut cur = String::new();
        let mut depth = 0;
        loop {
            match self.peek().clone() {
                Tok::Eof => return self.err("unterminated attribute"),
                Tok::Punct(")") if depth == 0 => {
                    self.bump();
                    break;
                }
                Tok::Punct(",") if depth == 0 => {
                    self.bump();
                    args.push(std::mem::take(&mut cur).trim().to_string());
                }
                t => {
                    if matches!(t, Tok::Punct("(") | Tok::Punct("[") | Tok::Punct("{")) {
                        depth += 1;
                    }
                    if matches!(t, Tok::Punct(")") | Tok::Punct("]") | Tok::Punct("}")) {
                        depth -= 1;
                    }
                    let tk = self.bump();
                    if !cur.is_empty() && tk.ws_before {
                        cur.push(' ');
                    }
                    cur.push_str(&tok_text(&tk.tok));
                }
            }
        }
        if !cur.trim().is_empty() {
            args.push(cur.trim().to_string());
        }
        Ok(args)
    }

    fn skip_balanced(&mut self) -> PResult<Span> {
        let open = match self.peek() {
            Tok::Punct(p) if *p == "(" || *p == "[" || *p == "{" => *p,
            _ => return self.err("expected a bracket"),
        };
        let close = match open {
            "(" => ")",
            "[" => "]",
            _ => "}",
        };
        let start = self.bump().span;
        let mut depth = 1;
        loop {
            match self.peek() {
                Tok::Eof => return self.err(format!("unbalanced `{open}`")),
                Tok::Punct(p) if *p == "(" || *p == "[" || *p == "{" => depth += 1,
                Tok::Punct(p) if *p == ")" || *p == "]" || *p == "}" => {
                    depth -= 1;
                    if depth == 0 {
                        let end = self.bump().span;
                        if !matches!(close, ")" | "]" | "}") {
                            unreachable!()
                        }
                        return Ok(start.to(end));
                    }
                }
                _ => {}
            }
            self.bump();
        }
    }

    fn vis(&mut self) -> bool {
        if self.is_word("pub") {
            self.bump();
            if self.is_punct("(") {
                let _ = self.skip_balanced();
            }
            true
        } else {
            false
        }
    }

    pub fn item(&mut self) -> PResult<Item> {
        self.enter()?;
        let r = self.item_inner();
        self.nest -= 1;
        r
    }

    fn item_inner(&mut self) -> PResult<Item> {
        let attrs = self.attrs()?;
        let start = self.span();
        // Loose statements (documentation snippets)
        if attrs.is_empty() && self.is_word("let") {
            let mut stmts = Vec::new();
            while self.is_word("let") || (!self.at_item_start() && !matches!(self.peek(), Tok::Eof)) {
                let s = self.stmt()?;
                stmts.push(s);
            }
            return Ok(Item::LooseStmts(stmts, start.to(self.prev_span())));
        }
        let is_pub = self.vis();
        // out-of-scope item keywords (note section 12)
        if self.is_word("flow") && self.is_ident_at(1) && (self.is_punct_at(2, "(") || self.is_punct_at(2, "<")) {
            // a flow is fn-shaped (02 section 12.1): parse it as one, then report it out of scope
            let sp = self.span();
            self.toks[self.pos].tok = Tok::Ident("fn".into());
            let _ = self.fn_decl(attrs, is_pub, FnKind::Plain, start)?;
            return Ok(Item::OutOfScope(OutOfScope { kw: "FLOW".into(), span: sp }));
        }
        if self.is_word("store") && self.is_ident_at(1) && self.is_punct_at(2, "{") {
            let sp = self.bump().span;
            self.skip_to_block_end()?;
            return Ok(Item::OutOfScope(OutOfScope { kw: "STORE".into(), span: sp }));
        }
        if self.is_word("evolve") && self.is_word_at(1, "slot") {
            let sp = self.bump().span;
            self.skip_to_block_end()?;
            return Ok(Item::OutOfScope(OutOfScope { kw: "EVOLVE".into(), span: sp }));
        }
        if self.is_word("export") && self.is_word_at(1, "abi") {
            let sp = self.bump().span;
            self.skip_to_block_end()?;
            return Ok(Item::OutOfScope(OutOfScope { kw: "EXPORT".into(), span: sp }));
        }
        if self.is_word("comptime") && self.is_punct_at(1, "{") {
            let sp = self.bump().span;
            self.skip_balanced()?;
            return Ok(Item::OutOfScope(OutOfScope { kw: "COMPTIME".into(), span: sp }));
        }
        if self.is_word("macro_rules") && self.is_punct_at(1, "!") {
            let sp = self.bump().span;
            self.bump();
            self.ident()?;
            let e = self.skip_balanced()?;
            self.eat_punct(";");
            return Ok(Item::MacroRules(sp.to(e)));
        }
        // fn kinds
        if self.is_word("kernel") && self.is_word_at(1, "fn") {
            self.bump();
            return Ok(Item::Fn(self.fn_decl(attrs, is_pub, FnKind::Kernel, start)?));
        }
        if self.is_word("policy") && self.is_word_at(1, "fn") {
            self.bump();
            return Ok(Item::Fn(self.fn_decl(attrs, is_pub, FnKind::Policy, start)?));
        }
        if self.is_word("fn")
            || (self.is_word("const") && self.is_word_at(1, "fn"))
            || (self.is_word("unsafe") && self.is_word_at(1, "fn"))
            || (self.is_word("async") && self.is_word_at(1, "fn"))
            || (self.is_word("extern") && (self.is_word_at(1, "fn") || matches!(self.peek_at(1), Tok::Str(_))))
        {
            return Ok(Item::Fn(self.fn_decl(attrs, is_pub, FnKind::Plain, start)?));
        }
        if self.is_word("linear") && self.is_word_at(1, "struct") {
            self.bump();
            return Ok(Item::Struct(self.struct_decl(attrs, is_pub, true, start)?));
        }
        if self.is_word("struct") {
            return Ok(Item::Struct(self.struct_decl(attrs, is_pub, false, start)?));
        }
        if self.is_word("enum") {
            return Ok(Item::Enum(self.enum_decl(attrs, is_pub, start)?));
        }
        if self.is_word("invariant") && self.is_ident_at(1) {
            self.bump();
            let ty = self.path_simple()?;
            self.expect_punct("{")?;
            let cond = self.expr()?;
            let end = self.expect_punct("}")?;
            return Ok(Item::Invariant(InvariantDecl { ty, cond, span: start.to(end) }));
        }
        if self.is_word("impl") || (self.is_word("unsafe") && self.is_word_at(1, "impl")) {
            return Ok(Item::Impl(self.impl_decl(attrs, start)?));
        }
        if self.is_word("trait") || (self.is_word("unsafe") && self.is_word_at(1, "trait")) {
            return Ok(Item::Trait(self.trait_decl(attrs, is_pub, start)?));
        }
        if self.is_word("format") && self.is_ident_at(1) && self.is_punct_at(2, "{") {
            return Ok(Item::Format(self.format_decl(attrs, is_pub, start)?));
        }
        if self.is_word("schedule") && self.is_ident_at(1) && self.is_word_at(2, "for") {
            return Ok(Item::Schedule(self.schedule_decl(start)?));
        }
        if self.is_word("spec") && self.is_ident_at(1) && self.is_word_at(2, "for") {
            return Ok(Item::Spec(self.spec_decl(start)?));
        }
        if self.is_word("use") {
            return Ok(Item::Use(self.use_decl(start)?));
        }
        if self.is_word("mod") {
            self.bump();
            let name = self.ident()?;
            if self.eat_punct(";") {
                let path_attr = attrs.iter().find(|a| a.name == "path").map(|a| a.span);
                return Ok(Item::Mod(ModDecl { name, items: vec![], span: start.to(self.prev_span()), path_attr }));
            }
            self.expect_punct("{")?;
            let mut items = Vec::new();
            while !self.is_punct("}") {
                if matches!(self.peek(), Tok::Eof) {
                    return self.err("unterminated module");
                }
                if self.eat_punct(";") {
                    continue;
                }
                items.push(self.item()?);
            }
            let end = self.expect_punct("}")?;
            let path_attr = attrs.iter().find(|a| a.name == "path").map(|a| a.span);
            return Ok(Item::Mod(ModDecl { name, items, span: start.to(end), path_attr }));
        }
        if self.is_word("const") || self.is_word("static") {
            return Ok(Item::Const(self.const_decl(attrs, is_pub, start)?));
        }
        if self.is_word("type") {
            self.bump();
            let name = self.ident()?;
            let generics = self.generics()?;
            self.expect_punct("=")?;
            let ty = self.ty()?;
            let end = self.expect_punct(";")?;
            return Ok(Item::TypeAlias(name, generics, ty, start.to(end)));
        }
        if self.prelude && self.is_word("evidence") {
            self.bump();
            let name = self.path_simple()?;
            self.expect_punct("{")?;
            let mut fields = Vec::new();
            while !self.is_punct("}") {
                let k = self.ident()?;
                self.expect_punct(":")?;
                let v = self.path_simple()?;
                fields.push((k, v));
                if !self.eat_punct(",") {
                    break;
                }
            }
            let end = self.expect_punct("}")?;
            return Ok(Item::Evidence(EvidenceDecl { name, fields, span: start.to(end) }));
        }
        if self.prelude && self.is_word("seam") {
            self.bump();
            let name = self.ident()?;
            self.expect_punct("{")?;
            let mut fns = Vec::new();
            while self.eat_word("fn") {
                fns.push(self.ident()?);
                self.expect_punct(";")?;
            }
            let end = self.expect_punct("}")?;
            return Ok(Item::Seam(SeamDecl { name, fns, span: start.to(end) }));
        }
        if self.prelude && self.is_word("target") && self.is_word_at(2, "features") {
            self.bump();
            let arch = self.ident()?;
            self.expect_word("features")?;
            self.expect_punct("{")?;
            let mut features = Vec::new();
            while !self.is_punct("}") {
                features.push(self.ident()?);
                if !self.eat_punct(",") {
                    break;
                }
            }
            let end = self.expect_punct("}")?;
            return Ok(Item::Target(TargetDecl { arch, features, span: start.to(end) }));
        }
        self.err("expected an item")
    }

    fn at_item_start(&self) -> bool {
        let w = match self.peek() {
            Tok::Ident(s) => s.as_str(),
            Tok::Punct("#") => return true,
            _ => return false,
        };
        matches!(w, "fn" | "struct" | "enum" | "impl" | "trait" | "use" | "mod" | "pub" | "type" | "static")
            || (w == "kernel" || w == "policy") && self.is_word_at(1, "fn")
            || (w == "const" && !self.is_punct_at(1, "{"))
            || (w == "format" || w == "schedule" || w == "spec") && self.is_ident_at(1)
    }

    /// Skip an out-of-scope item: everything up to and including the first top-level `{ … }`
    /// block, or up to a top-level `;`.
    fn skip_to_block_end(&mut self) -> PResult<()> {
        loop {
            match self.peek() {
                Tok::Eof => return Ok(()),
                Tok::Punct("{") => {
                    self.skip_balanced()?;
                    return Ok(());
                }
                Tok::Punct("(") | Tok::Punct("[") => {
                    self.skip_balanced()?;
                }
                Tok::Punct(";") => {
                    self.bump();
                    return Ok(());
                }
                _ => {
                    self.bump();
                }
            }
        }
    }

    fn fn_decl(&mut self, attrs: Vec<Attr>, is_pub: bool, kind: FnKind, start: Span) -> PResult<FnDecl> {
        let mut is_unsafe = false;
        let mut is_async = false;
        let mut is_const = false;
        let mut is_extern = false;
        loop {
            if self.eat_word("const") {
                is_const = true;
            } else if self.eat_word("unsafe") {
                is_unsafe = true;
            } else if self.eat_word("async") {
                is_async = true;
            } else if self.eat_word("extern") {
                is_extern = true;
                if let Tok::Str(_) = self.peek() {
                    self.bump();
                }
            } else {
                break;
            }
        }
        self.expect_word("fn")?;
        let name = self.ident()?;
        let mut generics = self.generics()?;
        self.expect_punct("(")?;
        let mut self_param = None;
        let mut params = Vec::new();
        // self parameter
        {
            let sp = self.span();
            if self.is_punct("&") && (self.is_word_at(1, "self") || (self.is_word_at(1, "mut") && self.is_word_at(2, "self"))) {
                self.bump();
                let m = self.eat_word("mut");
                self.expect_word("self")?;
                self_param = Some((SelfParam::Ref { mutable: m }, sp.to(self.prev_span())));
            } else if self.is_punct("&") && matches!(self.peek_at(1), Tok::Lifetime(_)) && (self.is_word_at(2, "self") || self.is_word_at(3, "self")) {
                // `&'a self`: lifetimes are Dc; record and keep parsing
                self.bump();
                let lt = self.bump();
                let m = self.eat_word("mut");
                self.expect_word("self")?;
                self_param = Some((SelfParam::Ref { mutable: m }, sp.to(self.prev_span())));
                generics.params.push(GenericParam {
                    name: Ident { name: "'".to_string() + &tok_text(&lt.tok), span: lt.span },
                    bounds: vec![],
                    is_const: None,
                    is_lifetime: true,
                });
            } else if self.is_word("self") || (self.is_word("mut") && self.is_word_at(1, "self")) {
                let m = self.eat_word("mut");
                self.expect_word("self")?;
                if self.eat_punct(":") {
                    let t = self.ty()?;
                    // `self: &Self` and friends
                    let sp2 = sp.to(self.prev_span());
                    match t.kind {
                        TypeKind::Ref { mutable, .. } => self_param = Some((SelfParam::Ref { mutable }, sp2)),
                        _ => self_param = Some((SelfParam::Value { mutable: m }, sp2)),
                    }
                } else {
                    self_param = Some((SelfParam::Value { mutable: m }, sp.to(self.prev_span())));
                }
            }
            if self_param.is_some() && !self.is_punct(")") {
                self.expect_punct(",")?;
            }
        }
        while !self.is_punct(")") {
            let pattrs = self.attrs()?;
            let psp = self.span();
            let pat = self.pat_no_alt()?;
            self.expect_punct(":")?;
            let ty = self.ty()?;
            params.push(Param { pat, ty, attrs: pattrs, span: psp.to(self.prev_span()) });
            if !self.eat_punct(",") {
                break;
            }
        }
        self.expect_punct(")")?;
        let mut ret = None;
        if self.eat_punct("->") {
            ret = Some(self.ty_no_bounds_plus()?);
        }
        let mut uses = None;
        let mut requires = Vec::new();
        let mut ensures = Vec::new();
        loop {
            if self.is_word("uses") && self.is_punct_at(1, "{") {
                self.bump();
                self.bump();
                let mut effs = Vec::new();
                while !self.is_punct("}") {
                    // `unsafe` is a keyword but also a row label (note section 2.3); review
                    // 2026-10-23: `uses { unsafe }` was E-PARSE instead of E-GRANT-UNSAFE
                    let n = if self.is_word("unsafe") { self.any_word()? } else { self.ident()? };
                    let mut arg = None;
                    if self.eat_punct("(") {
                        arg = Some(self.ident()?);
                        self.expect_punct(")")?;
                    }
                    effs.push(Effect { name: n, arg });
                    if !self.eat_punct(",") {
                        break;
                    }
                }
                self.expect_punct("}")?;
                uses = Some(effs);
            } else if self.is_word("requires") {
                self.bump();
                requires.push(self.expr_ns()?);
            } else if self.is_word("ensures") {
                self.bump();
                ensures.push(self.expr_ns()?);
            } else if self.is_word("where") {
                self.bump();
                self.where_clauses(&mut generics)?;
            } else {
                break;
            }
        }
        let sig_span = start.to(self.prev_span());
        let body = if self.is_punct("{") {
            Some(self.block()?)
        } else {
            self.eat_punct(";");
            None
        };
        Ok(FnDecl {
            attrs,
            is_pub,
            kind,
            name,
            generics,
            self_param,
            params,
            ret,
            uses,
            requires,
            ensures,
            body,
            span: start.to(self.prev_span()),
            sig_span,
            is_unsafe,
            is_async,
            is_const,
            is_extern,
        })
    }

    fn where_clauses(&mut self, g: &mut Generics) -> PResult<()> {
        loop {
            if self.is_punct("{") || self.is_punct(";") || matches!(self.peek(), Tok::Eof) || self.is_word("uses") || self.is_word("requires") || self.is_word("ensures") {
                break;
            }
            let t = self.ty()?;
            self.expect_punct(":")?;
            let bs = self.bounds()?;
            g.wheres.push((t, bs));
            if !self.eat_punct(",") {
                break;
            }
        }
        Ok(())
    }

    pub fn generics(&mut self) -> PResult<Generics> {
        let mut g = Generics::default();
        if !self.is_punct("<") {
            return Ok(g);
        }
        self.bump();
        while !self.is_gt_like() {
            if let Tok::Lifetime(l) = self.peek().clone() {
                let sp = self.bump().span;
                let mut bounds = vec![];
                if self.eat_punct(":") {
                    while let Tok::Lifetime(_) = self.peek() {
                        self.bump();
                        if !self.eat_punct("+") {
                            break;
                        }
                    }
                }
                let _ = &mut bounds;
                g.params.push(GenericParam { name: Ident { name: format!("'{l}"), span: sp }, bounds, is_const: None, is_lifetime: true });
            } else if self.eat_word("const") {
                let name = self.ident()?;
                self.expect_punct(":")?;
                let t = self.ty()?;
                g.params.push(GenericParam { name, bounds: vec![], is_const: Some(t), is_lifetime: false });
            } else {
                let name = self.ident()?;
                let mut bounds = vec![];
                if self.eat_punct(":") {
                    bounds = self.bounds()?;
                }
                if self.eat_punct("=") {
                    let _default = self.ty()?;
                }
                g.params.push(GenericParam { name, bounds, is_const: None, is_lifetime: false });
            }
            if !self.eat_punct(",") {
                break;
            }
        }
        self.expect_gt()?;
        Ok(g)
    }

    fn bounds(&mut self) -> PResult<Vec<Bound>> {
        let mut out = Vec::new();
        loop {
            let sp = self.span();
            if let Tok::Lifetime(l) = self.peek().clone() {
                self.bump();
                out.push(Bound::Lifetime(l, sp));
            } else if self.eat_punct("?") {
                let p = self.path_type()?;
                out.push(Bound::Maybe(p));
            } else if self.is_word("for") && self.is_punct_at(1, "<") {
                // higher-ranked bound: lifetimes are Dc
                self.bump();
                let g = self.generics()?;
                for gp in g.params {
                    out.push(Bound::Lifetime(gp.name.name.clone(), gp.name.span));
                }
                continue;
            } else if self.is_punct("(") {
                self.bump();
                let mut inner = self.bounds()?;
                self.expect_punct(")")?;
                out.append(&mut inner);
            } else {
                let p = self.path_type()?;
                let last = p.last().to_string();
                if (last == "Fn" || last == "FnMut" || last == "FnOnce") && self.is_punct("(") {
                    self.bump();
                    let mut params = Vec::new();
                    while !self.is_punct(")") {
                        params.push(self.ty()?);
                        if !self.eat_punct(",") {
                            break;
                        }
                    }
                    self.expect_punct(")")?;
                    let mut ret = None;
                    if self.eat_punct("->") {
                        ret = Some(self.ty_no_bounds_plus()?);
                    }
                    out.push(Bound::FnTrait { kind: last, params, ret, span: sp.to(self.prev_span()) });
                } else {
                    out.push(Bound::Trait(p));
                }
            }
            if !self.eat_punct("+") {
                break;
            }
        }
        Ok(out)
    }

    fn struct_decl(&mut self, attrs: Vec<Attr>, is_pub: bool, linear: bool, start: Span) -> PResult<StructDecl> {
        self.expect_word("struct")?;
        let name = self.ident()?;
        let mut generics = self.generics()?;
        if self.is_word("where") {
            self.bump();
            self.where_clauses(&mut generics)?;
        }
        let mut opaque = false;
        let data = if self.is_punct("{") {
            if matches!(self.peek_at(1), Tok::Ellipsis) {
                self.bump();
                self.bump();
                self.expect_punct("}")?;
                opaque = true;
                VariantData::Unit
            } else {
                self.saw_ellipsis = false;
                let f = self.named_fields()?;
                if self.saw_ellipsis {
                    opaque = true;
                }
                VariantData::Struct(f)
            }
        } else if self.is_punct("(") {
            let f = self.tuple_fields()?;
            if self.is_word("where") {
                self.bump();
                self.where_clauses(&mut generics)?;
            }
            self.expect_punct(";")?;
            VariantData::Tuple(f)
        } else {
            self.expect_punct(";")?;
            VariantData::Unit
        };
        Ok(StructDecl { attrs, is_pub, linear, name, generics, data, opaque, span: start.to(self.prev_span()) })
    }

    fn named_fields(&mut self) -> PResult<Vec<FieldDecl>> {
        self.expect_punct("{")?;
        let mut out = Vec::new();
        while !self.is_punct("}") {
            if matches!(self.peek(), Tok::Ellipsis) {
                // prelude: further fields elided
                self.saw_ellipsis = true;
                self.bump();
                if !self.eat_punct(",") {
                    break;
                }
                continue;
            }
            let attrs = self.attrs()?;
            let is_pub = self.vis();
            let name = self.ident()?;
            self.expect_punct(":")?;
            let ty = self.ty()?;
            out.push(FieldDecl { attrs, is_pub, name, ty });
            if !self.eat_punct(",") {
                break;
            }
        }
        self.expect_punct("}")?;
        Ok(out)
    }

    fn tuple_fields(&mut self) -> PResult<Vec<FieldDecl>> {
        self.expect_punct("(")?;
        let mut out = Vec::new();
        let mut i = 0;
        while !self.is_punct(")") {
            let attrs = self.attrs()?;
            let is_pub = self.vis();
            let sp = self.span();
            let ty = self.ty()?;
            out.push(FieldDecl { attrs, is_pub, name: Ident { name: i.to_string(), span: sp }, ty });
            i += 1;
            if !self.eat_punct(",") {
                break;
            }
        }
        self.expect_punct(")")?;
        Ok(out)
    }

    fn enum_decl(&mut self, attrs: Vec<Attr>, is_pub: bool, start: Span) -> PResult<EnumDecl> {
        self.expect_word("enum")?;
        let name = self.ident()?;
        let mut generics = self.generics()?;
        if self.is_word("where") {
            self.bump();
            self.where_clauses(&mut generics)?;
        }
        self.expect_punct("{")?;
        let mut variants = Vec::new();
        while !self.is_punct("}") {
            if matches!(self.peek(), Tok::Ellipsis) {
                self.bump();
                if !self.eat_punct(",") {
                    break;
                }
                continue;
            }
            let _vattrs = self.attrs()?;
            let vname = self.ident()?;
            let data = if self.is_punct("{") {
                VariantData::Struct(self.named_fields()?)
            } else if self.is_punct("(") {
                VariantData::Tuple(self.tuple_fields()?)
            } else {
                VariantData::Unit
            };
            let mut discr = None;
            if self.eat_punct("=") {
                discr = Some(self.expr()?);
            }
            variants.push(VariantDecl { name: vname, data, discr });
            if !self.eat_punct(",") {
                break;
            }
        }
        let end = self.expect_punct("}")?;
        Ok(EnumDecl { attrs, is_pub, name, generics, variants, span: start.to(end) })
    }

    fn impl_decl(&mut self, attrs: Vec<Attr>, start: Span) -> PResult<ImplDecl> {
        self.eat_word("unsafe");
        self.expect_word("impl")?;
        let mut generics = if self.is_punct("<") { self.generics()? } else { Generics::default() };
        let negative = self.eat_punct("!");
        let first = self.ty_no_bounds_plus()?;
        let (trait_, self_ty) = if self.eat_word("for") {
            let tp = match first.kind {
                TypeKind::Path(p) => p,
                _ => return self.err("expected a trait path before `for`"),
            };
            (Some(tp), self.ty_no_bounds_plus()?)
        } else {
            (None, first)
        };
        if self.is_word("where") {
            self.bump();
            self.where_clauses(&mut generics)?;
        }
        self.expect_punct("{")?;
        let mut members = Vec::new();
        while !self.is_punct("}") {
            if matches!(self.peek(), Tok::Eof) {
                return self.err("unterminated impl");
            }
            if self.eat_punct(";") {
                continue;
            }
            let mut mattrs = self.attrs()?;
            let mstart = self.span();
            let mpub = self.vis();
            // `default fn` (specialization): parsed so that the checker can name it (E-SPECIALIZE)
            if self.is_word("default") && (self.is_word_at(1, "fn") || self.is_word_at(1, "type") || self.is_word_at(1, "const")) {
                let sp = self.span();
                self.bump();
                mattrs.push(Attr { name: "default".into(), args: vec![], span: sp });
            }
            if self.is_word("type") {
                self.bump();
                let n = self.ident()?;
                self.expect_punct("=")?;
                let t = self.ty()?;
                self.expect_punct(";")?;
                members.push(ImplMember::Type(n, t));
            } else if self.is_word("const") && !self.is_word_at(1, "fn") {
                members.push(ImplMember::Const(self.const_decl(mattrs, mpub, mstart)?));
            } else {
                let kind = if self.is_word("kernel") && self.is_word_at(1, "fn") {
                    self.bump();
                    FnKind::Kernel
                } else if self.is_word("policy") && self.is_word_at(1, "fn") {
                    self.bump();
                    FnKind::Policy
                } else {
                    FnKind::Plain
                };
                members.push(ImplMember::Fn(self.fn_decl(mattrs, mpub, kind, mstart)?));
            }
        }
        let end = self.expect_punct("}")?;
        Ok(ImplDecl { attrs, generics, trait_, negative, self_ty, members, span: start.to(end) })
    }

    fn trait_decl(&mut self, attrs: Vec<Attr>, is_pub: bool, start: Span) -> PResult<TraitDecl> {
        self.eat_word("unsafe");
        self.expect_word("trait")?;
        let name = self.ident()?;
        let mut generics = self.generics()?;
        let mut supers = Vec::new();
        if self.eat_punct(":") {
            supers = self.bounds()?;
        }
        if self.is_word("where") {
            self.bump();
            self.where_clauses(&mut generics)?;
        }
        self.expect_punct("{")?;
        let mut members = Vec::new();
        while !self.is_punct("}") {
            if matches!(self.peek(), Tok::Eof) {
                return self.err("unterminated trait");
            }
            if self.eat_punct(";") {
                continue;
            }
            let mattrs = self.attrs()?;
            let mstart = self.span();
            if self.is_word("type") {
                self.bump();
                let n = self.ident()?;
                let mut bs = vec![];
                if self.eat_punct(":") {
                    bs = self.bounds()?;
                }
                self.expect_punct(";")?;
                members.push(TraitMember::Type(n, bs));
            } else if self.is_word("const") && !self.is_word_at(1, "fn") {
                self.bump();
                let n = self.ident()?;
                self.expect_punct(":")?;
                let t = self.ty()?;
                let mut v = None;
                if self.eat_punct("=") {
                    v = Some(self.expr()?);
                }
                self.expect_punct(";")?;
                members.push(TraitMember::Const(n, t, v));
            } else {
                members.push(TraitMember::Fn(self.fn_decl(mattrs, true, FnKind::Plain, mstart)?));
            }
        }
        let end = self.expect_punct("}")?;
        Ok(TraitDecl { attrs, is_pub, name, generics, supers, members, span: start.to(end) })
    }

    fn format_decl(&mut self, attrs: Vec<Attr>, is_pub: bool, start: Span) -> PResult<FormatDecl> {
        self.expect_word("format")?;
        let name = self.ident()?;
        self.expect_punct("{")?;
        let mut fields = Vec::new();
        while !self.is_punct("}") {
            let fsp = self.span();
            let fname = self.ident()?;
            self.expect_punct(":")?;
            let code = self.format_code()?;
            fields.push(FormatField { name: fname, code, span: fsp.to(self.prev_span()) });
            if !self.eat_punct(",") {
                break;
            }
        }
        let end = self.expect_punct("}")?;
        Ok(FormatDecl { attrs, is_pub, name, fields, span: start.to(end) })
    }

    fn format_code(&mut self) -> PResult<FormatCode> {
        if self.eat_punct("[") {
            let inner = self.format_code()?;
            self.expect_punct(";")?;
            let n = self.expr()?;
            self.expect_punct("]")?;
            return Ok(FormatCode::Array(Box::new(inner), n));
        }
        let name = self.any_word()?;
        let mut args = Vec::new();
        if self.eat_punct("<") {
            while !self.is_gt_like() {
                if self.is_ident_at(0) && self.is_punct_at(1, "=") {
                    let k = self.ident()?;
                    self.bump();
                    let v = self.primary_lit_or_path()?;
                    args.push((Some(k), v));
                } else {
                    let v = self.primary_lit_or_path()?;
                    args.push((None, v));
                }
                if !self.eat_punct(",") {
                    break;
                }
            }
            self.expect_gt()?;
        }
        Ok(FormatCode::Named { name, args })
    }

    fn primary_lit_or_path(&mut self) -> PResult<Expr> {
        let sp = self.span();
        match self.peek().clone() {
            Tok::Int(v, s) => {
                self.bump();
                Ok(Expr { kind: ExprKind::Lit(Lit::Int(v, s)), span: sp })
            }
            Tok::Punct("-") => {
                self.bump();
                let e = self.primary_lit_or_path()?;
                Ok(Expr { kind: ExprKind::Unary(UnOp::Neg, Box::new(e)), span: sp.to(self.prev_span()) })
            }
            _ => {
                let p = self.path_expr()?;
                Ok(Expr { kind: ExprKind::Path(p), span: sp.to(self.prev_span()) })
            }
        }
    }

    fn schedule_decl(&mut self, start: Span) -> PResult<ScheduleDecl> {
        self.expect_word("schedule")?;
        let name = self.ident()?;
        self.expect_word("for")?;
        let for_fn = self.path_simple()?;
        self.expect_word("on")?;
        let arch = self.ident()?;
        let mut features = Vec::new();
        if self.eat_punct("(") {
            while !self.is_punct(")") {
                features.push(self.ident()?);
                if !self.eat_punct(",") {
                    break;
                }
            }
            self.expect_punct(")")?;
        }
        self.expect_punct("{")?;
        let mut directives = Vec::new();
        let mut elided = false;
        while !self.is_punct("}") {
            if matches!(self.peek(), Tok::Ellipsis) {
                self.bump();
                elided = true;
                continue;
            }
            let dsp = self.span();
            let verb = self.any_word()?;
            let mut words = Vec::new();
            while !self.is_punct(";") {
                match self.peek().clone() {
                    Tok::Ident(w) => {
                        let mut wsp = self.bump().span;
                        let mut w = w;
                        while self.is_punct(".") && self.is_ident_at(1) {
                            self.bump();
                            let n = self.any_word()?;
                            w = format!("{w}.{}", n.name);
                            wsp = wsp.to(n.span);
                        }
                        words.push(Ident { name: w, span: wsp });
                    }
                    Tok::Int(v, _) => {
                        let wsp = self.bump().span;
                        words.push(Ident { name: v.to_string(), span: wsp });
                    }
                    Tok::Eof => return self.err("unterminated schedule directive"),
                    _ => return self.err("unexpected token in a schedule directive"),
                }
            }
            let end = self.expect_punct(";")?;
            directives.push(Directive { verb, words, span: dsp.to(end) });
        }
        let end = self.expect_punct("}")?;
        Ok(ScheduleDecl { name, for_fn, arch, features, directives, elided, span: start.to(end) })
    }

    fn spec_decl(&mut self, start: Span) -> PResult<SpecDecl> {
        self.expect_word("spec")?;
        let name = self.ident()?;
        self.expect_word("for")?;
        let for_fn = self.path_simple()?;
        self.expect_punct("{")?;
        let mut claims = Vec::new();
        while !self.is_punct("}") {
            let csp = self.span();
            self.expect_word("claim")?;
            let kind = self.any_word()?;
            self.expect_punct("(")?;
            let mut args = Vec::new();
            while !self.is_punct(")") {
                args.push(self.path_simple()?);
                if !self.eat_punct(",") {
                    break;
                }
            }
            self.expect_punct(")")?;
            self.expect_word("requires")?;
            let grade = self.any_word()?;
            let mut qualifier = None;
            if self.is_ident_at(0) && self.is_punct_at(1, "(") {
                let qn = self.any_word()?;
                self.expect_punct("(")?;
                let mut qargs = Vec::new();
                while !self.is_punct(")") {
                    let k = self.ident()?;
                    self.expect_punct(":")?;
                    let asp = self.span();
                    let v = match self.peek().clone() {
                        Tok::Int(v, _) => {
                            self.bump();
                            if self.eat_punct("%") {
                                ClaimArg::Percent(v.to_string(), asp.to(self.prev_span()))
                            } else {
                                ClaimArg::Num(v.to_string(), asp)
                            }
                        }
                        Tok::Float(v, _) => {
                            self.bump();
                            if self.eat_punct("%") {
                                ClaimArg::Percent(v, asp.to(self.prev_span()))
                            } else {
                                ClaimArg::Num(v, asp)
                            }
                        }
                        _ => ClaimArg::Path(self.path_simple()?),
                    };
                    qargs.push((k, v));
                    if !self.eat_punct(",") {
                        break;
                    }
                }
                self.expect_punct(")")?;
                qualifier = Some(ClaimQual { name: qn, args: qargs });
            }
            let end = self.expect_punct(";")?;
            claims.push(Claim { kind, args, grade, qualifier, span: csp.to(end) });
        }
        let end = self.expect_punct("}")?;
        Ok(SpecDecl { name, for_fn, claims, span: start.to(end) })
    }

    fn use_decl(&mut self, start: Span) -> PResult<UseDecl> {
        self.expect_word("use")?;
        let mut tree = Vec::new();
        let prefix = Path { segs: vec![], span: self.span(), global: false };
        self.use_tree(prefix, &mut tree)?;
        let end = self.expect_punct(";")?;
        Ok(UseDecl { tree, span: start.to(end) })
    }

    fn use_tree(&mut self, prefix: Path, out: &mut Vec<Path>) -> PResult<()> {
        let mut p = prefix;
        self.eat_punct("::");
        loop {
            if self.is_punct("{") {
                self.bump();
                while !self.is_punct("}") {
                    self.use_tree(p.clone(), out)?;
                    if !self.eat_punct(",") {
                        break;
                    }
                }
                self.expect_punct("}")?;
                return Ok(());
            }
            if self.eat_punct("*") {
                p.segs.push(PathSeg { ident: Ident { name: "*".into(), span: self.prev_span() }, generics: None });
                out.push(p);
                return Ok(());
            }
            let id = self.ident()?;
            p.segs.push(PathSeg { ident: id, generics: None });
            if self.eat_punct("::") {
                continue;
            }
            if self.eat_word("as") {
                let alias = self.ident()?;
                p.segs.push(PathSeg { ident: Ident { name: format!("as {}", alias.name), span: alias.span }, generics: None });
            }
            out.push(p);
            return Ok(());
        }
    }

    fn const_decl(&mut self, attrs: Vec<Attr>, is_pub: bool, start: Span) -> PResult<ConstDecl> {
        let is_static = if self.eat_word("static") {
            true
        } else {
            self.expect_word("const")?;
            false
        };
        let is_mut = self.eat_word("mut");
        let name = self.ident()?;
        self.expect_punct(":")?;
        let ty = self.ty()?;
        let mut value = None;
        if self.eat_punct("=") {
            value = Some(self.expr()?);
        }
        let end = self.expect_punct(";")?;
        Ok(ConstDecl { attrs, is_pub, is_static, is_mut, name, ty, value, span: start.to(end) })
    }

    // ------------------------------------------------------------------ paths and types
    /// A path without generic arguments: `a::b::c`.
    fn path_simple(&mut self) -> PResult<Path> {
        let sp = self.span();
        let global = self.eat_punct("::");
        let mut segs = vec![PathSeg { ident: self.ident()?, generics: None }];
        while self.is_punct("::") && self.is_ident_at(1) {
            self.bump();
            segs.push(PathSeg { ident: self.ident()?, generics: None });
        }
        Ok(Path { segs, span: sp.to(self.prev_span()), global })
    }

    /// A path in type position: generic arguments with `<` directly.
    fn path_type(&mut self) -> PResult<Path> {
        let sp = self.span();
        let global = self.eat_punct("::");
        let mut segs = Vec::new();
        loop {
            let id = self.ident()?;
            let mut generics = None;
            if self.is_punct("<") {
                generics = Some(self.generic_args()?);
            } else if self.is_punct("::") && self.is_punct_at(1, "<") {
                self.bump();
                generics = Some(self.generic_args()?);
            }
            segs.push(PathSeg { ident: id, generics });
            if self.is_punct("::") && self.is_ident_at(1) {
                self.bump();
                continue;
            }
            break;
        }
        Ok(Path { segs, span: sp.to(self.prev_span()), global })
    }

    /// A path in expression position: generic arguments only with turbofish `::<`.
    fn path_expr(&mut self) -> PResult<Path> {
        let sp = self.span();
        let global = self.eat_punct("::");
        let mut segs = Vec::new();
        loop {
            let id = self.ident()?;
            let mut generics = None;
            if self.is_punct("::") && self.is_punct_at(1, "<") {
                self.bump();
                generics = Some(self.generic_args()?);
            }
            segs.push(PathSeg { ident: id, generics });
            if self.is_punct("::") && self.is_ident_at(1) {
                self.bump();
                continue;
            }
            break;
        }
        Ok(Path { segs, span: sp.to(self.prev_span()), global })
    }

    fn generic_args(&mut self) -> PResult<Vec<GenericArg>> {
        self.expect_punct("<")?;
        let mut out = Vec::new();
        while !self.is_gt_like() {
            if let Tok::Lifetime(l) = self.peek().clone() {
                let sp = self.bump().span;
                out.push(GenericArg::Type(TypeAst {
                    kind: TypeKind::Path(Path {
                        segs: vec![PathSeg { ident: Ident { name: format!("'{l}"), span: sp }, generics: None }],
                        span: sp,
                        global: false,
                    }),
                    span: sp,
                }));
            } else if self.is_ident_at(0) && self.is_punct_at(1, "=") {
                let n = self.ident()?;
                self.bump();
                let t = self.ty()?;
                out.push(GenericArg::Binding(n, t));
            } else if matches!(self.peek(), Tok::Int(..)) || self.is_punct("{") || self.is_punct("-") {
                let e = if self.is_punct("{") {
                    let b = self.block()?;
                    Expr { span: b.span, kind: ExprKind::Block(b) }
                } else {
                    self.primary_lit_or_path()?
                };
                out.push(GenericArg::Const(e));
            } else {
                out.push(GenericArg::Type(self.ty()?));
            }
            if !self.eat_punct(",") {
                break;
            }
        }
        self.expect_gt()?;
        Ok(out)
    }

    pub fn ty(&mut self) -> PResult<TypeAst> {
        self.ty_inner(true)
    }
    fn ty_no_bounds_plus(&mut self) -> PResult<TypeAst> {
        self.ty_inner(false)
    }

    fn ty_inner(&mut self, allow_plus: bool) -> PResult<TypeAst> {
        self.enter()?;
        let r = self.ty_inner_n(allow_plus);
        self.nest -= 1;
        r
    }

    fn ty_inner_n(&mut self, allow_plus: bool) -> PResult<TypeAst> {
        let sp = self.span();
        let kind = match self.peek().clone() {
            Tok::Punct("&") | Tok::Punct("&&") => {
                let double = self.is_punct("&&");
                self.bump();
                let mut lifetime = None;
                if let Tok::Lifetime(l) = self.peek().clone() {
                    self.bump();
                    lifetime = Some(l);
                }
                let mutable = self.eat_word("mut");
                let inner = self.ty_inner(false)?;
                let k = TypeKind::Ref { mutable, lifetime, inner: Box::new(inner) };
                if double {
                    let t = TypeAst { kind: k, span: sp.to(self.prev_span()) };
                    TypeKind::Ref { mutable: false, lifetime: None, inner: Box::new(t) }
                } else {
                    k
                }
            }
            Tok::Punct("*") => {
                self.bump();
                let m = if self.eat_word("mut") {
                    true
                } else {
                    self.expect_word("const")?;
                    false
                };
                let inner = self.ty_inner(false)?;
                TypeKind::RawPtr(m, Box::new(inner))
            }
            Tok::Punct("[") => {
                self.bump();
                let inner = self.ty()?;
                if self.eat_punct(";") {
                    let n = self.expr()?;
                    self.expect_punct("]")?;
                    TypeKind::Array(Box::new(inner), Box::new(n))
                } else {
                    self.expect_punct("]")?;
                    TypeKind::Slice(Box::new(inner))
                }
            }
            Tok::Punct("(") => {
                self.bump();
                let mut elems = Vec::new();
                let mut trailing = false;
                while !self.is_punct(")") {
                    elems.push(self.ty()?);
                    trailing = false;
                    if !self.eat_punct(",") {
                        break;
                    }
                    trailing = true;
                }
                self.expect_punct(")")?;
                if elems.len() == 1 && !trailing {
                    return Ok(elems.pop().unwrap());
                }
                TypeKind::Tuple(elems)
            }
            Tok::Punct("!") => {
                self.bump();
                TypeKind::Never
            }
            Tok::Punct("<") => {
                // <T as Trait>::Name
                self.bump();
                let t = self.ty()?;
                self.expect_word("as")?;
                let tr = self.path_type()?;
                self.expect_gt()?;
                self.expect_punct("::")?;
                let n = self.ident()?;
                TypeKind::QPath(Box::new(t), tr, n)
            }
            Tok::Ident(w) if w == "_" => {
                self.bump();
                TypeKind::Infer
            }
            Tok::Ident(w) if w == "impl" => {
                self.bump();
                TypeKind::ImplTrait(self.bounds()?)
            }
            Tok::Ident(w) if w == "dyn" => {
                self.bump();
                TypeKind::DynTrait(self.bounds()?)
            }
            Tok::Ident(w) if w == "fn" || ((w == "unsafe" || w == "extern") && self.is_word_at(1, "fn")) => {
                while !self.is_word("fn") {
                    self.bump();
                }
                self.bump();
                self.expect_punct("(")?;
                let mut ps = Vec::new();
                while !self.is_punct(")") {
                    ps.push(self.ty()?);
                    if !self.eat_punct(",") {
                        break;
                    }
                }
                self.expect_punct(")")?;
                let mut ret = None;
                if self.eat_punct("->") {
                    ret = Some(Box::new(self.ty_no_bounds_plus()?));
                }
                TypeKind::FnPtr(ps, ret)
            }
            Tok::Ident(_) | Tok::Punct("::") => {
                let p = self.path_type()?;
                if allow_plus && self.is_punct("+") {
                    // bare trait object without dyn (Rust 2015 style): treat as dyn
                    let mut bs = vec![Bound::Trait(p)];
                    while self.eat_punct("+") {
                        let mut more = self.bounds()?;
                        bs.append(&mut more);
                    }
                    TypeKind::DynTrait(bs)
                } else {
                    TypeKind::Path(p)
                }
            }
            _ => return self.err("expected a type"),
        };
        Ok(TypeAst { kind, span: sp.to(self.prev_span()) })
    }

    // ------------------------------------------------------------------ patterns
    fn pat(&mut self) -> PResult<Pat> {
        let sp = self.span();
        self.eat_punct("|");
        let first = self.pat_no_alt()?;
        if self.is_punct("|") {
            let mut alts = vec![first];
            while self.eat_punct("|") {
                alts.push(self.pat_no_alt()?);
            }
            return Ok(Pat { kind: PatKind::Or(alts), span: sp.to(self.prev_span()) });
        }
        Ok(first)
    }

    fn pat_no_alt(&mut self) -> PResult<Pat> {
        self.enter()?;
        let r = self.pat_no_alt_n();
        self.nest -= 1;
        r
    }

    fn pat_no_alt_n(&mut self) -> PResult<Pat> {
        let sp = self.span();
        let kind = match self.peek().clone() {
            Tok::Ident(w) if w == "_" => {
                self.bump();
                PatKind::Wild
            }
            Tok::Punct("..") => {
                self.bump();
                PatKind::Rest
            }
            Tok::Punct("&") | Tok::Punct("&&") => {
                self.bump();
                let m = self.eat_word("mut");
                let inner = self.pat_no_alt()?;
                PatKind::Ref(Box::new(inner), m)
            }
            Tok::Punct("(") => {
                self.bump();
                let mut ps = Vec::new();
                let mut trailing = false;
                while !self.is_punct(")") {
                    ps.push(self.pat()?);
                    trailing = false;
                    if !self.eat_punct(",") {
                        break;
                    }
                    trailing = true;
                }
                self.expect_punct(")")?;
                if ps.len() == 1 && !trailing {
                    return Ok(ps.pop().unwrap());
                }
                PatKind::Tuple(ps)
            }
            Tok::Punct("[") => {
                self.bump();
                let mut ps = Vec::new();
                while !self.is_punct("]") {
                    ps.push(self.pat()?);
                    if !self.eat_punct(",") {
                        break;
                    }
                }
                self.expect_punct("]")?;
                PatKind::Slice(ps)
            }
            Tok::Int(..) | Tok::Float(..) | Tok::Str(_) | Tok::Char(_) | Tok::Punct("-") => {
                let lo = self.lit_expr_for_pat()?;
                if self.is_punct("..=") || self.is_punct("...") {
                    self.bump();
                    let hi = self.lit_expr_for_pat()?;
                    PatKind::Range(Box::new(lo), Box::new(hi), true)
                } else if self.is_punct("..") {
                    self.bump();
                    let hi = self.lit_expr_for_pat()?;
                    PatKind::Range(Box::new(lo), Box::new(hi), false)
                } else {
                    PatKind::Lit(Box::new(lo))
                }
            }
            Tok::Ident(w) if w == "true" || w == "false" => {
                self.bump();
                PatKind::Lit(Box::new(Expr { kind: ExprKind::Lit(Lit::Bool(w == "true")), span: sp }))
            }
            Tok::Ident(w) if w == "ref" || w == "mut" => {
                let by_ref = self.eat_word("ref");
                let mutable = self.eat_word("mut");
                let name = self.ident()?;
                let mut sub = None;
                if self.eat_punct("@") {
                    sub = Some(Box::new(self.pat_no_alt()?));
                }
                PatKind::Ident { name, mutable, by_ref, sub }
            }
            Tok::Ident(_) | Tok::Punct("::") => {
                let p = self.path_expr()?;
                if self.is_punct("(") {
                    self.bump();
                    let mut ps = Vec::new();
                    while !self.is_punct(")") {
                        ps.push(self.pat()?);
                        if !self.eat_punct(",") {
                            break;
                        }
                    }
                    self.expect_punct(")")?;
                    PatKind::TupleStruct(p, ps)
                } else if self.is_punct("{") {
                    self.bump();
                    let mut fs = Vec::new();
                    let mut rest = false;
                    while !self.is_punct("}") {
                        if self.eat_punct("..") {
                            rest = true;
                            break;
                        }
                        let by_ref = self.eat_word("ref");
                        let mutable = self.eat_word("mut");
                        let f = self.ident()?;
                        if self.eat_punct(":") {
                            let fp = self.pat()?;
                            fs.push((f, fp));
                        } else {
                            let fsp = f.span;
                            fs.push((f.clone(), Pat { kind: PatKind::Ident { name: f, mutable, by_ref, sub: None }, span: fsp }));
                        }
                        if !self.eat_punct(",") {
                            break;
                        }
                    }
                    self.expect_punct("}")?;
                    PatKind::Struct(p, fs, rest)
                } else if self.is_punct("..=") || self.is_punct("..") {
                    // path range pattern like `i32::MIN..=0`
                    let incl = self.is_punct("..=");
                    self.bump();
                    let hi = self.lit_expr_for_pat()?;
                    let lo = Expr { kind: ExprKind::Path(p.clone()), span: p.span };
                    PatKind::Range(Box::new(lo), Box::new(hi), incl)
                } else if p.segs.len() == 1 && p.segs[0].generics.is_none() && !starts_upper(&p.segs[0].ident.name) {
                    let name = p.segs[0].ident.clone();
                    let mut sub = None;
                    if self.eat_punct("@") {
                        sub = Some(Box::new(self.pat_no_alt()?));
                    }
                    PatKind::Ident { name, mutable: false, by_ref: false, sub }
                } else {
                    PatKind::Path(p)
                }
            }
            _ => return self.err("expected a pattern"),
        };
        Ok(Pat { kind, span: sp.to(self.prev_span()) })
    }

    fn lit_expr_for_pat(&mut self) -> PResult<Expr> {
        let sp = self.span();
        if self.eat_punct("-") {
            let inner = self.lit_expr_for_pat()?;
            return Ok(Expr { kind: ExprKind::Unary(UnOp::Neg, Box::new(inner)), span: sp.to(self.prev_span()) });
        }
        match self.peek().clone() {
            Tok::Int(v, s) => {
                self.bump();
                Ok(Expr { kind: ExprKind::Lit(Lit::Int(v, s)), span: sp })
            }
            Tok::Float(v, s) => {
                self.bump();
                Ok(Expr { kind: ExprKind::Lit(Lit::Float(v, s)), span: sp })
            }
            Tok::Str(v) => {
                self.bump();
                Ok(Expr { kind: ExprKind::Lit(Lit::Str(v)), span: sp })
            }
            Tok::Char(c) => {
                self.bump();
                Ok(Expr { kind: ExprKind::Lit(Lit::Char(c)), span: sp })
            }
            Tok::Ident(_) => {
                let p = self.path_expr()?;
                Ok(Expr { kind: ExprKind::Path(p), span: sp.to(self.prev_span()) })
            }
            _ => self.err("expected a literal pattern"),
        }
    }

    // ------------------------------------------------------------------ blocks and statements
    pub fn block(&mut self) -> PResult<Block> {
        self.enter()?;
        let r = self.block_inner();
        self.nest -= 1;
        r
    }

    fn block_inner(&mut self) -> PResult<Block> {
        let start = self.expect_punct("{")?;
        let mut stmts = Vec::new();
        let mut tail = None;
        loop {
            if self.is_punct("}") {
                break;
            }
            if matches!(self.peek(), Tok::Eof) {
                return self.err("unterminated block");
            }
            if self.eat_punct(";") {
                continue;
            }
            // items inside blocks
            if self.is_block_item_start() {
                let it = self.item()?;
                stmts.push(Stmt::Item(Box::new(it)));
                continue;
            }
            if self.is_word("let") {
                stmts.push(self.stmt()?);
                continue;
            }
            let e = self.expr_stmt()?;
            let blocklike = is_blocklike(&e);
            if self.eat_punct(";") {
                stmts.push(Stmt::Expr(e, true));
            } else if self.is_punct("}") {
                tail = Some(Box::new(e));
                break;
            } else if blocklike {
                stmts.push(Stmt::Expr(e, false));
            } else {
                return self.err("expected `;` or `}` after an expression");
            }
        }
        let end = self.expect_punct("}")?;
        Ok(Block { stmts, tail, span: start.to(end), is_unsafe: false })
    }

    fn is_block_item_start(&self) -> bool {
        match self.peek() {
            Tok::Punct("#") => self.is_punct_at(1, "["),
            Tok::Ident(w) => {
                matches!(w.as_str(), "fn" | "struct" | "enum" | "impl" | "trait" | "use" | "mod")
                    || (w == "const" && self.is_ident_at(1) && self.is_punct_at(2, ":"))
                    || (w == "static" && (self.is_ident_at(1) || self.is_word_at(1, "mut")))
                    || ((w == "kernel" || w == "policy") && self.is_word_at(1, "fn"))
            }
            _ => false,
        }
    }

    fn stmt(&mut self) -> PResult<Stmt> {
        if self.is_word("let") {
            let sp = self.bump().span;
            let pat = self.pat()?;
            let mut ty = None;
            if self.eat_punct(":") {
                ty = Some(self.ty()?);
            }
            let mut init = None;
            let mut els = None;
            if self.eat_punct("=") {
                init = Some(self.expr()?);
                if self.eat_word("else") {
                    els = Some(self.block()?);
                }
            }
            let end = self.expect_punct(";")?;
            return Ok(Stmt::Let { pat, ty, init, els, span: sp.to(end) });
        }
        let e = self.expr_stmt()?;
        let semi = self.eat_punct(";");
        if !semi && !is_blocklike(&e) && !matches!(self.peek(), Tok::Eof) && !self.is_punct("}") {
            return self.err("expected `;`");
        }
        Ok(Stmt::Expr(e, semi))
    }

    /// An expression in statement position: block-like expressions end the statement.
    fn expr_stmt(&mut self) -> PResult<Expr> {
        if self.starts_blocklike() {
            let e = self.primary(false)?;
            // allow method calls on a block-like statement only for `?`-free simple cases: Rust ends
            // the statement here; a following `.` continues as Rust does for `match {}.x` (it does
            // not); we stop.
            if self.is_punct(".") || self.is_punct("?") {
                let e2 = self.postfix(e)?;
                return self.binary_rest(e2, 0, false).and_then(|l| self.assign_rest(l, false));
            }
            return Ok(e);
        }
        self.expr()
    }

    fn starts_blocklike(&self) -> bool {
        match self.peek() {
            Tok::Punct("{") => true,
            Tok::Lifetime(_) => self.is_punct_at(1, ":"),
            Tok::Ident(w) => match w.as_str() {
                "if" | "match" | "loop" | "while" | "for" => true,
                "unsafe" => self.is_punct_at(1, "{"),
                "par" => self.is_word_at(1, "for"),
                "deterministic" => self.is_punct_at(1, "(") && self.is_word_at(2, "by"),
                _ => false,
            },
            _ => false,
        }
    }

    // ------------------------------------------------------------------ expressions
    pub fn expr(&mut self) -> PResult<Expr> {
        self.expr_with(false)
    }
    /// Expression where a struct literal may not appear (conditions, scrutinees, contracts).
    fn expr_ns(&mut self) -> PResult<Expr> {
        self.expr_with(true)
    }

    fn expr_with(&mut self, ns: bool) -> PResult<Expr> {
        let lhs = self.range_expr(ns)?;
        self.assign_rest(lhs, ns)
    }

    fn assign_rest(&mut self, lhs: Expr, ns: bool) -> PResult<Expr> {
        let op = match self.peek() {
            Tok::Punct("=") => None,
            Tok::Punct("+=") => Some(BinOp::Add),
            Tok::Punct("-=") => Some(BinOp::Sub),
            Tok::Punct("*=") => Some(BinOp::Mul),
            Tok::Punct("/=") => Some(BinOp::Div),
            Tok::Punct("%=") => Some(BinOp::Rem),
            Tok::Punct("^=") => Some(BinOp::BitXor),
            Tok::Punct("&=") => Some(BinOp::BitAnd),
            Tok::Punct("|=") => Some(BinOp::BitOr),
            Tok::Punct("<<=") => Some(BinOp::Shl),
            Tok::Punct(">>=") => Some(BinOp::Shr),
            _ => return Ok(lhs),
        };
        self.bump();
        let rhs = self.expr_with(ns)?;
        let span = lhs.span.to(rhs.span);
        Ok(match op {
            None => Expr { kind: ExprKind::Assign(Box::new(lhs), Box::new(rhs)), span },
            Some(o) => Expr { kind: ExprKind::AssignOp(o, Box::new(lhs), Box::new(rhs)), span },
        })
    }

    fn can_start_expr(&self) -> bool {
        match self.peek() {
            Tok::Ident(w) => !matches!(w.as_str(), "as" | "else" | "in"),
            Tok::Int(..) | Tok::Float(..) | Tok::Str(_) | Tok::Char(_) | Tok::Ellipsis | Tok::Lifetime(_) => true,
            Tok::Punct(p) => matches!(*p, "(" | "[" | "-" | "!" | "*" | "&" | "&&" | "|" | "||" | "::" | "<"),
            Tok::Eof => false,
        }
    }

    fn range_expr(&mut self, ns: bool) -> PResult<Expr> {
        let sp = self.span();
        if self.is_punct("..") || self.is_punct("..=") {
            let incl = self.is_punct("..=");
            self.bump();
            let hi = if self.can_start_expr() && !(ns && self.is_punct("{")) { Some(Box::new(self.bin_expr(0, ns)?)) } else { None };
            return Ok(Expr { kind: ExprKind::Range(None, hi, incl), span: sp.to(self.prev_span()) });
        }
        let lhs = self.bin_expr(0, ns)?;
        if self.is_punct("..") || self.is_punct("..=") {
            let incl = self.is_punct("..=");
            self.bump();
            let hi = if self.can_start_expr() && !self.is_punct("{") { Some(Box::new(self.bin_expr(0, ns)?)) } else { None };
            let span = lhs.span.to(self.prev_span());
            return Ok(Expr { kind: ExprKind::Range(Some(Box::new(lhs)), hi, incl), span });
        }
        Ok(lhs)
    }

    fn bin_op(&self) -> Option<(BinOp, u8)> {
        let p = match self.peek() {
            Tok::Punct(p) => *p,
            _ => return None,
        };
        Some(match p {
            "||" => (BinOp::Or, 1),
            "&&" => (BinOp::And, 2),
            "==" => (BinOp::Eq, 3),
            "!=" => (BinOp::Ne, 3),
            "<" => (BinOp::Lt, 3),
            "<=" => (BinOp::Le, 3),
            ">" => (BinOp::Gt, 3),
            ">=" => (BinOp::Ge, 3),
            "|" => (BinOp::BitOr, 4),
            "^" => (BinOp::BitXor, 5),
            "&" => (BinOp::BitAnd, 6),
            "<<" => (BinOp::Shl, 7),
            ">>" => (BinOp::Shr, 7),
            "+" => (BinOp::Add, 8),
            "-" => (BinOp::Sub, 8),
            "*" => (BinOp::Mul, 9),
            "/" => (BinOp::Div, 9),
            "%" => (BinOp::Rem, 9),
            _ => return None,
        })
    }

    fn bin_expr(&mut self, min_prec: u8, ns: bool) -> PResult<Expr> {
        let lhs = self.unary(ns)?;
        self.binary_rest(lhs, min_prec, ns)
    }

    fn binary_rest(&mut self, mut lhs: Expr, min_prec: u8, ns: bool) -> PResult<Expr> {
        loop {
            // `as` casts bind tighter than every binary operator
            if self.is_word("as") {
                self.bump();
                let t = self.ty_no_bounds_plus()?;
                let span = lhs.span.to(self.prev_span());
                lhs = Expr { kind: ExprKind::Cast(Box::new(lhs), t), span };
                continue;
            }
            let (op, prec) = match self.bin_op() {
                Some(x) => x,
                None => break,
            };
            if prec < min_prec {
                break;
            }
            // comparisons are not associative, as in Rust: `a < b < c` is a parse error
            if prec == 3 {
                if let ExprKind::Binary(o, ..) = &lhs.kind {
                    if matches!(o, BinOp::Eq | BinOp::Ne | BinOp::Lt | BinOp::Le | BinOp::Gt | BinOp::Ge) {
                        return self.err("comparison operators cannot be chained; add parentheses");
                    }
                }
            }
            self.bump();
            // comparisons are non-associative; others left-associative
            let rhs = self.bin_expr(prec + 1, ns)?;
            let span = lhs.span.to(rhs.span);
            lhs = Expr { kind: ExprKind::Binary(op, Box::new(lhs), Box::new(rhs)), span };
        }
        Ok(lhs)
    }

    fn unary(&mut self, ns: bool) -> PResult<Expr> {
        self.enter()?;
        let r = self.unary_n(ns);
        self.nest -= 1;
        r
    }

    fn unary_n(&mut self, ns: bool) -> PResult<Expr> {
        let sp = self.span();
        match self.peek().clone() {
            Tok::Punct("-") => {
                self.bump();
                let e = self.unary(ns)?;
                Ok(Expr { kind: ExprKind::Unary(UnOp::Neg, Box::new(e)), span: sp.to(self.prev_span()) })
            }
            Tok::Punct("!") => {
                self.bump();
                let e = self.unary(ns)?;
                Ok(Expr { kind: ExprKind::Unary(UnOp::Not, Box::new(e)), span: sp.to(self.prev_span()) })
            }
            Tok::Punct("*") => {
                self.bump();
                let e = self.unary(ns)?;
                Ok(Expr { kind: ExprKind::Unary(UnOp::Deref, Box::new(e)), span: sp.to(self.prev_span()) })
            }
            Tok::Punct("&") | Tok::Punct("&&") => {
                let double = self.is_punct("&&");
                self.bump();
                let mutable = self.eat_word("mut");
                let e = self.unary(ns)?;
                let inner = Expr { kind: ExprKind::Ref { mutable, expr: Box::new(e) }, span: sp.to(self.prev_span()) };
                if double {
                    Ok(Expr { kind: ExprKind::Ref { mutable: false, expr: Box::new(inner) }, span: sp.to(self.prev_span()) })
                } else {
                    Ok(inner)
                }
            }
            _ => {
                let p = self.primary(ns)?;
                self.postfix(p)
            }
        }
    }

    fn postfix(&mut self, mut e: Expr) -> PResult<Expr> {
        loop {
            if self.is_punct("?") {
                let end = self.bump().span;
                e = Expr { span: e.span.to(end), kind: ExprKind::Try(Box::new(e)) };
                continue;
            }
            if self.is_punct("(") {
                let args = self.call_args()?;
                let span = e.span.to(self.prev_span());
                e = Expr { kind: ExprKind::Call(Box::new(e), args), span };
                continue;
            }
            if self.is_punct("[") {
                self.bump();
                let idx = self.expr()?;
                let end = self.expect_punct("]")?;
                e = Expr { span: e.span.to(end), kind: ExprKind::Index(Box::new(e), Box::new(idx)) };
                continue;
            }
            if self.is_punct(".") {
                self.bump();
                match self.peek().clone() {
                    Tok::Int(v, None) => {
                        let fsp = self.bump().span;
                        e = Expr { span: e.span.to(fsp), kind: ExprKind::TupleField(Box::new(e), v as u32, fsp) };
                    }
                    Tok::Float(text, None) => {
                        // `t.0.1`
                        let fsp = self.bump().span;
                        let mut parts = text.split('.');
                        let a: u32 = parts.next().unwrap_or("0").parse().unwrap_or(0);
                        let b: u32 = parts.next().unwrap_or("0").parse().unwrap_or(0);
                        e = Expr { span: e.span.to(fsp), kind: ExprKind::TupleField(Box::new(e), a, fsp) };
                        e = Expr { span: e.span.to(fsp), kind: ExprKind::TupleField(Box::new(e), b, fsp) };
                    }
                    Tok::Ident(w) if w == "await" => {
                        let end = self.bump().span;
                        e = Expr { span: e.span.to(end), kind: ExprKind::Await(Box::new(e)) };
                    }
                    Tok::Ident(_) => {
                        let name = self.ident()?;
                        let mut generics = None;
                        if self.is_punct("::") && self.is_punct_at(1, "<") {
                            self.bump();
                            generics = Some(self.generic_args()?);
                        }
                        if self.is_punct("(") {
                            let args = self.call_args()?;
                            let span = e.span.to(self.prev_span());
                            e = Expr { kind: ExprKind::MethodCall { recv: Box::new(e), method: name, generics, args }, span };
                        } else {
                            let span = e.span.to(name.span);
                            e = Expr { kind: ExprKind::Field(Box::new(e), name), span };
                        }
                    }
                    _ => return self.err("expected a field or method name after `.`"),
                }
                continue;
            }
            break;
        }
        Ok(e)
    }

    fn call_args(&mut self) -> PResult<Vec<Expr>> {
        self.expect_punct("(")?;
        let mut args = Vec::new();
        while !self.is_punct(")") {
            args.push(self.expr()?);
            if !self.eat_punct(",") {
                break;
            }
        }
        self.expect_punct(")")?;
        Ok(args)
    }

    fn label(&mut self) -> Option<String> {
        if let Tok::Lifetime(l) = self.peek().clone() {
            if self.is_punct_at(1, ":") {
                self.bump();
                self.bump();
                return Some(l);
            }
        }
        None
    }

    fn primary(&mut self, ns: bool) -> PResult<Expr> {
        self.enter()?;
        let r = self.primary_n(ns);
        self.nest -= 1;
        r
    }

    fn primary_n(&mut self, ns: bool) -> PResult<Expr> {
        let sp = self.span();
        let lbl = self.label();
        if lbl.is_some() {
            if self.is_word("loop") {
                self.bump();
                let (l, b) = self.loop_body(lbl)?;
                return Ok(Expr { kind: ExprKind::Loop(l, b), span: sp.to(self.prev_span()) });
            }
            if self.is_word("while") {
                return self.while_expr(lbl, sp);
            }
            if self.is_word("for") || (self.is_word("par") && self.is_word_at(1, "for")) {
                return self.for_expr(lbl, sp);
            }
            if self.is_punct("{") {
                // a labelled block (note section 3.2, section 12): a one-trip loop,
                // `'a: loop { break 'a { ... } }`, so that every pass reuses T-Loop and T-Jump
                self.brk.push((lbl.clone(), true, None));
                let b = self.block();
                self.brk.pop();
                let b = b?;
                let bsp = b.span;
                let inner = Expr { kind: ExprKind::Block(b), span: bsp };
                let brk = Expr { kind: ExprKind::Break(lbl.clone(), Some(Box::new(inner))), span: bsp };
                let body = Block { stmts: vec![], tail: Some(Box::new(brk)), span: bsp, is_unsafe: false };
                return Ok(Expr { kind: ExprKind::Loop(lbl, body), span: sp.to(self.prev_span()) });
            }
            return self.err("expected a loop or a block after a label");
        }
        match self.peek().clone() {
            Tok::Int(v, s) => {
                self.bump();
                Ok(Expr { kind: ExprKind::Lit(Lit::Int(v, s)), span: sp })
            }
            Tok::Float(v, s) => {
                self.bump();
                Ok(Expr { kind: ExprKind::Lit(Lit::Float(v, s)), span: sp })
            }
            Tok::Str(v) => {
                self.bump();
                Ok(Expr { kind: ExprKind::Lit(Lit::Str(v)), span: sp })
            }
            Tok::Char(c) => {
                self.bump();
                Ok(Expr { kind: ExprKind::Lit(Lit::Char(c)), span: sp })
            }
            Tok::Ellipsis => {
                self.bump();
                Ok(Expr { kind: ExprKind::Ellipsis, span: sp })
            }
            Tok::Punct("(") => {
                self.bump();
                let mut elems = Vec::new();
                let mut trailing = false;
                while !self.is_punct(")") {
                    elems.push(self.expr()?);
                    trailing = false;
                    if !self.eat_punct(",") {
                        break;
                    }
                    trailing = true;
                }
                let end = self.expect_punct(")")?;
                if elems.len() == 1 && !trailing {
                    let e = elems.pop().unwrap();
                    return Ok(Expr { kind: ExprKind::Paren(Box::new(e)), span: sp.to(end) });
                }
                Ok(Expr { kind: ExprKind::Tuple(elems), span: sp.to(end) })
            }
            Tok::Punct("[") => {
                self.bump();
                if self.is_punct("]") {
                    let end = self.bump().span;
                    return Ok(Expr { kind: ExprKind::Array(vec![]), span: sp.to(end) });
                }
                let first = self.expr()?;
                if self.eat_punct(";") {
                    let n = self.expr()?;
                    let end = self.expect_punct("]")?;
                    return Ok(Expr { kind: ExprKind::ArrayRepeat(Box::new(first), Box::new(n)), span: sp.to(end) });
                }
                let mut elems = vec![first];
                while self.eat_punct(",") {
                    if self.is_punct("]") {
                        break;
                    }
                    elems.push(self.expr()?);
                }
                let end = self.expect_punct("]")?;
                Ok(Expr { kind: ExprKind::Array(elems), span: sp.to(end) })
            }
            Tok::Punct("{") => {
                let b = self.block()?;
                Ok(Expr { span: b.span, kind: ExprKind::Block(b) })
            }
            Tok::Punct("|") | Tok::Punct("||") => self.closure(false, sp),
            Tok::Punct("<") => {
                // qualified path expression <T as Trait>::f
                let t = self.ty()?;
                let _ = t;
                self.err("qualified paths in expressions are not in the X1 surface")
            }
            Tok::Ident(w) => match w.as_str() {
                "true" | "false" => {
                    self.bump();
                    Ok(Expr { kind: ExprKind::Lit(Lit::Bool(w == "true")), span: sp })
                }
                "move" if self.is_punct_at(1, "|") || self.is_punct_at(1, "||") => {
                    self.bump();
                    self.closure(true, sp)
                }
                "if" => self.if_expr(),
                "match" => {
                    self.bump();
                    let scrut = self.expr_ns()?;
                    self.expect_punct("{")?;
                    let mut arms = Vec::new();
                    while !self.is_punct("}") {
                        let asp = self.span();
                        let _ = self.attrs()?;
                        let pat = self.pat()?;
                        let mut guard = None;
                        if self.eat_word("if") {
                            guard = Some(self.expr()?);
                        }
                        self.expect_punct("=>")?;
                        let body = self.expr_stmt()?;
                        let blocky = is_blocklike(&body);
                        let aspan = asp.to(body.span);
                        arms.push(MatchArm { pat, guard, body, span: aspan });
                        if !self.eat_punct(",") && !blocky && !self.is_punct("}") {
                            return self.err("expected `,` after a match arm");
                        }
                    }
                    let end = self.expect_punct("}")?;
                    Ok(Expr { kind: ExprKind::Match(Box::new(scrut), arms), span: sp.to(end) })
                }
                "loop" => {
                    self.bump();
                    let (l, b) = self.loop_body(None)?;
                    Ok(Expr { kind: ExprKind::Loop(l, b), span: sp.to(self.prev_span()) })
                }
                "while" => self.while_expr(None, sp),
                "for" => self.for_expr(None, sp),
                "par" if self.is_word_at(1, "for") => self.for_expr(None, sp),
                "unsafe" if self.is_punct_at(1, "{") => {
                    self.bump();
                    let mut b = self.block()?;
                    b.is_unsafe = true;
                    Ok(Expr { kind: ExprKind::Block(b), span: sp.to(self.prev_span()) })
                }
                "async" if self.is_punct_at(1, "{") || self.is_word_at(1, "move") => {
                    self.bump();
                    self.eat_word("move");
                    let b = self.block()?;
                    let inner = Expr { span: b.span, kind: ExprKind::Block(b) };
                    Ok(Expr { kind: ExprKind::Async(Box::new(inner)), span: sp.to(self.prev_span()) })
                }
                "comptime" if self.is_punct_at(1, "{") => {
                    self.bump();
                    let b = self.block()?;
                    let inner = Expr { span: b.span, kind: ExprKind::Block(b) };
                    Ok(Expr { kind: ExprKind::OutOfScope("COMPTIME".into(), Box::new(inner)), span: sp.to(self.prev_span()) })
                }
                "deterministic" if self.is_punct_at(1, "(") && self.is_word_at(2, "by") => {
                    self.bump();
                    self.bump();
                    self.expect_word("by")?;
                    self.expect_punct(":")?;
                    let by = self.path_simple()?;
                    self.expect_punct(")")?;
                    let body = self.block()?;
                    Ok(Expr { kind: ExprKind::Det { by, body }, span: sp.to(self.prev_span()) })
                }
                "break" => {
                    self.bump();
                    let mut l = None;
                    if let Tok::Lifetime(x) = self.peek().clone() {
                        self.bump();
                        l = Some(x);
                    }
                    if l.is_none() && matches!(self.brk.last(), Some((_, true, _))) {
                        // rustc E0695
                        return Err(Diag::new("E-TYPE", sp, "unlabelled `break` inside a labelled block: name the block or the loop"));
                    }
                    let mut v = None;
                    if self.can_start_expr() && !self.is_punct("}") && !(ns && self.is_punct("{")) {
                        v = Some(Box::new(self.expr_with(ns)?));
                    }
                    Ok(Expr { kind: ExprKind::Break(l, v), span: sp.to(self.prev_span()) })
                }
                "continue" => {
                    self.bump();
                    let mut l = None;
                    if let Tok::Lifetime(x) = self.peek().clone() {
                        self.bump();
                        l = Some(x);
                    }
                    match &l {
                        Some(x) => {
                            if let Some((_, true, _)) = self.brk.iter().rev().find(|f| f.0.as_deref() == Some(x.as_str())) {
                                // rustc E0696
                                return Err(Diag::new("E-TYPE", sp, format!("`continue {x}` names a labelled block, not a loop")));
                            }
                        }
                        None => {
                            // an unlabelled `continue` targets the innermost loop, past labelled
                            // blocks (one-trip loops after elaboration): name that loop
                            if matches!(self.brk.last(), Some((_, true, _))) {
                                if let Some(i) = self.brk.iter().rposition(|f| !f.1) {
                                    let name = match (&self.brk[i].0, &self.brk[i].2) {
                                        (Some(n), _) | (None, Some(n)) => n.clone(),
                                        (None, None) => {
                                            self.synth += 1;
                                            let n = format!("'mithi_loop_{}", self.synth);
                                            self.brk[i].2 = Some(n.clone());
                                            n
                                        }
                                    };
                                    l = Some(name);
                                }
                            }
                        }
                    }
                    Ok(Expr { kind: ExprKind::Continue(l), span: sp.to(self.prev_span()) })
                }
                "return" => {
                    self.bump();
                    let mut v = None;
                    if self.can_start_expr() && !self.is_punct("}") {
                        v = Some(Box::new(self.expr_with(ns)?));
                    }
                    Ok(Expr { kind: ExprKind::Return(v), span: sp.to(self.prev_span()) })
                }
                "let" => {
                    // `let` in an `if let` / `while let` condition (handled by callers) or a let-chain
                    self.bump();
                    let p = self.pat()?;
                    self.expect_punct("=")?;
                    let e = self.bin_expr(3, true)?;
                    Ok(Expr { kind: ExprKind::Let(p, Box::new(e)), span: sp.to(self.prev_span()) })
                }
                _ => {
                    // macro invocation
                    if self.is_ident_at(0) && self.is_punct_at(1, "!") && (self.is_punct_at(2, "(") || self.is_punct_at(2, "[") || self.is_punct_at(2, "{")) {
                        return self.macro_call();
                    }
                    let p = self.path_expr()?;
                    if !ns && self.is_punct("{") && self.struct_lit_follows() {
                        return self.struct_lit(p, sp);
                    }
                    Ok(Expr { span: p.span, kind: ExprKind::Path(p) })
                }
            },
            Tok::Punct("::") => {
                let p = self.path_expr()?;
                if !ns && self.is_punct("{") && self.struct_lit_follows() {
                    return self.struct_lit(p, sp);
                }
                Ok(Expr { span: p.span, kind: ExprKind::Path(p) })
            }
            _ => self.err("expected an expression"),
        }
    }

    fn struct_lit_follows(&self) -> bool {
        // `{ }`, `{ ident: `, `{ ident, `, `{ ident }`, `{ ..`
        if self.is_punct_at(1, "}") {
            return true;
        }
        if self.is_punct_at(1, "..") {
            return true;
        }
        if self.is_ident_at(1) {
            return self.is_punct_at(2, ":") && !self.is_punct_at(2, "::") || self.is_punct_at(2, ",") || self.is_punct_at(2, "}");
        }
        if matches!(self.peek_at(1), Tok::Int(..)) {
            return self.is_punct_at(2, ":");
        }
        false
    }

    fn struct_lit(&mut self, path: Path, sp: Span) -> PResult<Expr> {
        self.expect_punct("{")?;
        let mut fields = Vec::new();
        let mut base = None;
        while !self.is_punct("}") {
            if self.eat_punct("..") {
                base = Some(Box::new(self.expr()?));
                break;
            }
            let f = match self.peek().clone() {
                Tok::Int(v, _) => {
                    let s = self.bump().span;
                    Ident { name: v.to_string(), span: s }
                }
                _ => self.ident()?,
            };
            if self.eat_punct(":") {
                let v = self.expr()?;
                fields.push((f, v));
            } else {
                let p = Path { segs: vec![PathSeg { ident: f.clone(), generics: None }], span: f.span, global: false };
                fields.push((f.clone(), Expr { kind: ExprKind::Path(p), span: f.span }));
            }
            if !self.eat_punct(",") {
                break;
            }
        }
        let end = self.expect_punct("}")?;
        Ok(Expr { kind: ExprKind::Struct { path, fields, base }, span: sp.to(end) })
    }

    fn closure(&mut self, is_move: bool, sp: Span) -> PResult<Expr> {
        let mut params = Vec::new();
        if self.eat_punct("||") {
        } else {
            self.expect_punct("|")?;
            while !self.is_punct("|") {
                let pat = self.pat_no_alt()?;
                let mut ty = None;
                if self.eat_punct(":") {
                    ty = Some(self.ty_no_bounds_plus()?);
                }
                params.push(ClosureParam { pat, ty });
                if !self.eat_punct(",") {
                    break;
                }
            }
            self.expect_punct("|")?;
        }
        let mut ret = None;
        // break targets do not cross a closure body
        let outer = std::mem::take(&mut self.brk);
        let body = if self.eat_punct("->") {
            match self.ty_no_bounds_plus() {
                Ok(t) => ret = Some(t),
                Err(d) => {
                    self.brk = outer;
                    return Err(d);
                }
            }
            match self.block() {
                Ok(b) => Expr { span: b.span, kind: ExprKind::Block(b) },
                Err(d) => {
                    self.brk = outer;
                    return Err(d);
                }
            }
        } else {
            match self.expr() {
                Ok(e) => e,
                Err(d) => {
                    self.brk = outer;
                    return Err(d);
                }
            }
        };
        self.brk = outer;
        Ok(Expr { kind: ExprKind::Closure { is_move, params, ret, body: Box::new(body) }, span: sp.to(self.prev_span()) })
    }

    fn if_expr(&mut self) -> PResult<Expr> {
        let sp = self.expect_word("if")?;
        if self.is_word("let") {
            self.bump();
            let p = self.pat()?;
            self.expect_punct("=")?;
            let e = self.expr_ns()?;
            let then = self.block()?;
            let els = self.else_part()?;
            return Ok(Expr { kind: ExprKind::IfLet(p, Box::new(e), then, els), span: sp.to(self.prev_span()) });
        }
        let cond = self.expr_ns()?;
        let then = self.block()?;
        let els = self.else_part()?;
        Ok(Expr { kind: ExprKind::If(Box::new(cond), then, els), span: sp.to(self.prev_span()) })
    }

    fn else_part(&mut self) -> PResult<Option<Box<Expr>>> {
        if !self.eat_word("else") {
            return Ok(None);
        }
        if self.is_word("if") {
            return Ok(Some(Box::new(self.if_expr()?)));
        }
        let b = self.block()?;
        Ok(Some(Box::new(Expr { span: b.span, kind: ExprKind::Block(b) })))
    }

    fn while_expr(&mut self, lbl: Option<String>, sp: Span) -> PResult<Expr> {
        self.expect_word("while")?;
        if self.eat_word("let") {
            let p = self.pat()?;
            self.expect_punct("=")?;
            let e = self.expr_ns()?;
            let (lbl, b) = self.loop_body(lbl)?;
            return Ok(Expr { kind: ExprKind::WhileLet(lbl, p, Box::new(e), b), span: sp.to(self.prev_span()) });
        }
        let c = self.expr_ns()?;
        let (lbl, b) = self.loop_body(lbl)?;
        Ok(Expr { kind: ExprKind::While(lbl, Box::new(c), b), span: sp.to(self.prev_span()) })
    }

    fn for_expr(&mut self, lbl: Option<String>, sp: Span) -> PResult<Expr> {
        let par = self.eat_word("par");
        self.expect_word("for")?;
        let pat = self.pat()?;
        self.expect_word("in")?;
        let iter = self.expr_ns()?;
        let (lbl, body) = self.loop_body(lbl)?;
        Ok(Expr { kind: ExprKind::For { label: lbl, par, pat, iter: Box::new(iter), body }, span: sp.to(self.prev_span()) })
    }

    fn macro_call(&mut self) -> PResult<Expr> {
        let sp = self.span();
        let name = self.ident()?;
        self.expect_punct("!")?;
        let close = match self.peek() {
            Tok::Punct("(") => ")",
            Tok::Punct("[") => "]",
            _ => "}",
        };
        let n = name.name.as_str();
        let known_exprs = matches!(
            n,
            "todo" | "unimplemented" | "unreachable" | "panic" | "assert" | "assert_eq" | "assert_ne" | "debug_assert"
                | "debug_assert_eq" | "debug_assert_ne" | "format" | "write" | "writeln" | "println" | "print"
                | "eprintln" | "eprint" | "dbg" | "vec"
        );
        if n == "matches" {
            self.bump();
            let e = self.expr()?;
            self.expect_punct(",")?;
            let p = self.pat()?;
            if self.eat_word("if") {
                let _g = self.expr()?;
            }
            self.eat_punct(",");
            self.expect_punct(close)?;
            return Ok(Expr { kind: ExprKind::Macro { name, args: MacroArgs::Matches(Box::new(e), p) }, span: sp.to(self.prev_span()) });
        }
        if known_exprs {
            self.bump();
            if self.is_punct(close) {
                self.bump();
                return Ok(Expr { kind: ExprKind::Macro { name, args: MacroArgs::Exprs(vec![]) }, span: sp.to(self.prev_span()) });
            }
            let first = self.expr()?;
            if n == "vec" && self.eat_punct(";") {
                let cnt = self.expr()?;
                self.expect_punct(close)?;
                return Ok(Expr { kind: ExprKind::Macro { name, args: MacroArgs::Repeat(Box::new(first), Box::new(cnt)) }, span: sp.to(self.prev_span()) });
            }
            let mut args = vec![first];
            while self.eat_punct(",") {
                if self.is_punct(close) {
                    break;
                }
                // format-style named arguments `name = expr`
                if self.is_ident_at(0) && self.is_punct_at(1, "=") {
                    self.bump();
                    self.bump();
                }
                args.push(self.expr()?);
            }
            self.expect_punct(close)?;
            return Ok(Expr { kind: ExprKind::Macro { name, args: MacroArgs::Exprs(args) }, span: sp.to(self.prev_span()) });
        }
        let end = self.skip_balanced()?;
        Ok(Expr { kind: ExprKind::Macro { name, args: MacroArgs::Raw }, span: sp.to(end) })
    }
}

fn starts_upper(s: &str) -> bool {
    s.chars().next().map(|c| c.is_ascii_uppercase()).unwrap_or(false)
}

pub fn is_blocklike(e: &Expr) -> bool {
    matches!(
        e.kind,
        ExprKind::Block(_)
            | ExprKind::If(..)
            | ExprKind::IfLet(..)
            | ExprKind::Match(..)
            | ExprKind::While(..)
            | ExprKind::WhileLet(..)
            | ExprKind::Loop(..)
            | ExprKind::For { .. }
            | ExprKind::Det { .. }
    )
}

pub fn tok_text(t: &Tok) -> String {
    match t {
        Tok::Ident(s) => s.clone(),
        Tok::Int(v, s) => format!("{v}{}", s.clone().unwrap_or_default()),
        Tok::Float(v, s) => format!("{v}{}", s.clone().unwrap_or_default()),
        Tok::Str(s) => format!("{s:?}"),
        Tok::Char(c) => format!("{c:?}"),
        Tok::Lifetime(l) => format!("'{l}"),
        Tok::Punct(p) => p.to_string(),
        Tok::Ellipsis => "…".into(),
        Tok::Eof => String::new(),
    }
}

pub fn parse_source(file: u16, src: &str, prelude: bool) -> Result<Vec<Item>, Diag> {
    let toks = crate::lexer::lex(file, src)?;
    let mut p = Parser::new(toks, file);
    p.prelude = prelude;
    p.parse_file()
}
