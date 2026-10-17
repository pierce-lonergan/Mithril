//! Lexer. Keywords are contextual (01 section 2.4), so every word is an `Ident` token and the
//! parser decides; only Rust's strict keywords are reserved by the parser.

use crate::diag::{Diag, Span};

#[derive(Clone, Debug, PartialEq)]
pub enum Tok {
    Ident(String),
    /// Integer literal: value (fits u128) and optional suffix.
    Int(u128, Option<String>),
    /// Float literal: source text (without suffix and underscores) and optional suffix.
    Float(String, Option<String>),
    Str(String),
    Char(char),
    Lifetime(String),
    Punct(&'static str),
    /// U+2026 HORIZONTAL ELLIPSIS: an elided body in documentation snippets.
    Ellipsis,
    Eof,
}

#[derive(Clone, Debug)]
pub struct Token {
    pub tok: Tok,
    pub span: Span,
    /// True if whitespace or a comment precedes the token (used to tell `a < b` from generics
    /// in no case; kept for the formatter and for `x.0.1` style tuple fields).
    pub ws_before: bool,
}

const PUNCTS: &[&str] = &[
    "<<=", ">>=", "...", "..=", "::", "->", "=>", "==", "!=", "<=", ">=", "&&", "||", "+=", "-=", "*=",
    "/=", "%=", "^=", "&=", "|=", "<<", ">>", "..", "+", "-", "*", "/", "%", "^", "!", "&", "|", "=", "<",
    ">", "@", ".", ",", ";", ":", "#", "$", "?", "{", "}", "[", "]", "(", ")",
];

pub fn lex(file: u16, src: &str) -> Result<Vec<Token>, Diag> {
    let bytes = src.as_bytes();
    let mut i = 0usize;
    let mut out = Vec::new();
    let mut ws = true;
    while i < bytes.len() {
        let c = bytes[i];
        // whitespace
        if c == b' ' || c == b'\t' || c == b'\n' || c == b'\r' {
            i += 1;
            ws = true;
            continue;
        }
        // comments
        if c == b'/' && i + 1 < bytes.len() && bytes[i + 1] == b'/' {
            while i < bytes.len() && bytes[i] != b'\n' {
                i += 1;
            }
            ws = true;
            continue;
        }
        if c == b'/' && i + 1 < bytes.len() && bytes[i + 1] == b'*' {
            let start = i;
            let mut depth = 0;
            while i < bytes.len() {
                if bytes[i] == b'/' && i + 1 < bytes.len() && bytes[i + 1] == b'*' {
                    depth += 1;
                    i += 2;
                } else if bytes[i] == b'*' && i + 1 < bytes.len() && bytes[i + 1] == b'/' {
                    depth -= 1;
                    i += 2;
                    if depth == 0 {
                        break;
                    }
                } else {
                    i += 1;
                }
            }
            if depth != 0 {
                return Err(Diag::new("E-PARSE", Span::new(file, start as u32, i as u32), "unterminated block comment"));
            }
            ws = true;
            continue;
        }
        let start = i;
        // ellipsis character (UTF-8 E2 80 A6)
        if c == 0xE2 && i + 2 < bytes.len() && bytes[i + 1] == 0x80 && bytes[i + 2] == 0xA6 {
            i += 3;
            out.push(Token { tok: Tok::Ellipsis, span: Span::new(file, start as u32, i as u32), ws_before: ws });
            ws = false;
            continue;
        }
        if c.is_ascii_alphabetic() || c == b'_' {
            // raw identifiers r#x
            if c == b'r' && i + 2 < bytes.len() && bytes[i + 1] == b'#' && (bytes[i + 2].is_ascii_alphabetic() || bytes[i + 2] == b'_') {
                i += 2;
            }
            let s0 = i;
            while i < bytes.len() && (bytes[i].is_ascii_alphanumeric() || bytes[i] == b'_') {
                i += 1;
            }
            let word = &src[s0..i];
            // byte string / byte literal prefixes
            if word == "b" && i < bytes.len() && bytes[i] == b'\'' {
                // byte literal b'x'
                let (ch, ni) = lex_char(file, src, i)?;
                i = ni;
                out.push(Token { tok: Tok::Int(ch as u128, Some("u8".into())), span: Span::new(file, start as u32, i as u32), ws_before: ws });
                ws = false;
                continue;
            }
            out.push(Token { tok: Tok::Ident(word.to_string()), span: Span::new(file, start as u32, i as u32), ws_before: ws });
            ws = false;
            continue;
        }
        if c.is_ascii_digit() {
            let (tok, ni) = lex_number(file, src, i)?;
            i = ni;
            out.push(Token { tok, span: Span::new(file, start as u32, i as u32), ws_before: ws });
            ws = false;
            continue;
        }
        if c == b'"' {
            let mut s = String::new();
            i += 1;
            loop {
                if i >= bytes.len() {
                    return Err(Diag::new("E-PARSE", Span::new(file, start as u32, i as u32), "unterminated string literal"));
                }
                let ch = src[i..].chars().next().unwrap();
                if ch == '"' {
                    i += 1;
                    break;
                }
                if ch == '\\' {
                    let (e, ni) = lex_escape(file, src, i)?;
                    if let Some(e) = e {
                        s.push(e);
                    }
                    i = ni;
                    continue;
                }
                s.push(ch);
                i += ch.len_utf8();
            }
            out.push(Token { tok: Tok::Str(s), span: Span::new(file, start as u32, i as u32), ws_before: ws });
            ws = false;
            continue;
        }
        if c == b'\'' {
            // char literal or lifetime
            let rest = &src[i + 1..];
            let mut it = rest.chars();
            let first = it.next();
            let second = it.next();
            let is_char = match (first, second) {
                (Some('\\'), _) => true,
                (Some(_), Some('\'')) => true,
                _ => false,
            };
            if is_char {
                let (ch, ni) = lex_char(file, src, i)?;
                i = ni;
                out.push(Token { tok: Tok::Char(ch), span: Span::new(file, start as u32, i as u32), ws_before: ws });
            } else {
                i += 1;
                let s0 = i;
                while i < bytes.len() && (bytes[i].is_ascii_alphanumeric() || bytes[i] == b'_') {
                    i += 1;
                }
                out.push(Token { tok: Tok::Lifetime(src[s0..i].to_string()), span: Span::new(file, start as u32, i as u32), ws_before: ws });
            }
            ws = false;
            continue;
        }
        let mut matched = None;
        for p in PUNCTS {
            if src[i..].starts_with(p) {
                matched = Some(*p);
                break;
            }
        }
        if let Some(p) = matched {
            i += p.len();
            out.push(Token { tok: Tok::Punct(p), span: Span::new(file, start as u32, i as u32), ws_before: ws });
            ws = false;
            continue;
        }
        let ch = src[i..].chars().next().unwrap();
        return Err(Diag::new(
            "E-PARSE",
            Span::new(file, start as u32, (i + ch.len_utf8()) as u32),
            format!("unexpected character {:?} (the surface is ASCII-only, 05 section 3)", ch),
        ));
    }
    out.push(Token { tok: Tok::Eof, span: Span::new(file, bytes.len() as u32, bytes.len() as u32), ws_before: true });
    Ok(out)
}

fn lex_escape(file: u16, src: &str, i: usize) -> Result<(Option<char>, usize), Diag> {
    let b = src.as_bytes();
    let n = b.get(i + 1).copied();
    let r = match n {
        Some(b'n') => (Some('\n'), i + 2),
        Some(b't') => (Some('\t'), i + 2),
        Some(b'r') => (Some('\r'), i + 2),
        Some(b'0') => (Some('\0'), i + 2),
        Some(b'\\') => (Some('\\'), i + 2),
        Some(b'\'') => (Some('\''), i + 2),
        Some(b'"') => (Some('"'), i + 2),
        Some(b'\n') => {
            let mut j = i + 2;
            while j < b.len() && (b[j] == b' ' || b[j] == b'\n' || b[j] == b'\t' || b[j] == b'\r') {
                j += 1;
            }
            (None, j)
        }
        Some(b'x') => {
            let h = src.get(i + 2..i + 4).ok_or_else(|| Diag::new("E-PARSE", Span::new(file, i as u32, i as u32 + 2), "bad escape"))?;
            let v = u8::from_str_radix(h, 16).map_err(|_| Diag::new("E-PARSE", Span::new(file, i as u32, i as u32 + 4), "bad \\x escape"))?;
            (Some(v as char), i + 4)
        }
        Some(b'u') => {
            let close = src[i..].find('}').ok_or_else(|| Diag::new("E-PARSE", Span::new(file, i as u32, i as u32 + 2), "bad \\u escape"))?;
            let h = &src[i + 3..i + close];
            let digits = h.replace('_', "");
            let v = u32::from_str_radix(&digits, 16).map_err(|_| Diag::new("E-PARSE", Span::new(file, i as u32, i as u32 + 2), "bad \\u escape"))?;
            // a Unicode scalar value written with at most six digits (no surrogate, at most
            // 10FFFF), as Rust requires (review 2026-10-16: '\u{110000}' was accepted as '\0')
            let c = if digits.len() <= 6 { char::from_u32(v) } else { None };
            let Some(c) = c else {
                return Err(Diag::new("E-PARSE", Span::new(file, i as u32, (i + close + 1) as u32), "invalid unicode escape: not a Unicode scalar value"));
            };
            (Some(c), i + close + 1)
        }
        _ => return Err(Diag::new("E-PARSE", Span::new(file, i as u32, i as u32 + 2), "unknown escape")),
    };
    Ok(r)
}

fn lex_char(file: u16, src: &str, i: usize) -> Result<(char, usize), Diag> {
    // src[i] == '\''
    let mut j = i + 1;
    let ch;
    if src.as_bytes().get(j) == Some(&b'\\') {
        let (e, nj) = lex_escape(file, src, j)?;
        ch = e.unwrap_or('\0');
        j = nj;
    } else {
        let c = src[j..].chars().next().ok_or_else(|| Diag::new("E-PARSE", Span::new(file, i as u32, j as u32), "bad char literal"))?;
        ch = c;
        j += c.len_utf8();
    }
    if src.as_bytes().get(j) != Some(&b'\'') {
        return Err(Diag::new("E-PARSE", Span::new(file, i as u32, j as u32), "unterminated char literal"));
    }
    Ok((ch, j + 1))
}

const INT_SUFFIXES: &[&str] = &["u8", "u16", "u32", "u64", "u128", "usize", "i8", "i16", "i32", "i64", "i128", "isize"];
const FLOAT_SUFFIXES: &[&str] = &["f32", "f64", "f16"];

fn lex_number(file: u16, src: &str, start: usize) -> Result<(Tok, usize), Diag> {
    let b = src.as_bytes();
    let mut i = start;
    let err = |lo: usize, hi: usize, m: &str| Diag::new("E-PARSE", Span::new(file, lo as u32, hi as u32), m.to_string());
    // radix prefixes
    if b[i] == b'0' && i + 1 < b.len() && (b[i + 1] == b'x' || b[i + 1] == b'b' || b[i + 1] == b'o') {
        let radix = match b[i + 1] {
            b'x' => 16,
            b'b' => 2,
            _ => 8,
        };
        i += 2;
        let s0 = i;
        while i < b.len() && (b[i].is_ascii_hexdigit() || b[i] == b'_') {
            // stop at a suffix start like `u8` in hex? hex digits include no 'u'/'i'
            i += 1;
        }
        let digits: String = src[s0..i].chars().filter(|c| *c != '_').collect();
        // a hex literal may swallow an `f32`-like tail? Rust treats 0x1f32 as hex digits; keep.
        let v = u128::from_str_radix(&digits, radix).map_err(|_| err(start, i, "bad integer literal"))?;
        let (suf, ni) = lex_suffix(src, i, INT_SUFFIXES);
        return Ok((Tok::Int(v, suf), ni));
    }
    while i < b.len() && (b[i].is_ascii_digit() || b[i] == b'_') {
        i += 1;
    }
    let mut is_float = false;
    // fraction: a '.' followed by a digit (not '..' and not '.ident' for method calls/tuple fields)
    if i < b.len() && b[i] == b'.' && i + 1 < b.len() && b[i + 1].is_ascii_digit() {
        is_float = true;
        i += 1;
        while i < b.len() && (b[i].is_ascii_digit() || b[i] == b'_') {
            i += 1;
        }
    } else if i < b.len() && b[i] == b'.' && !(i + 1 < b.len() && (b[i + 1] == b'.' || b[i + 1].is_ascii_alphabetic() || b[i + 1] == b'_')) {
        // `1.` is a float literal
        is_float = true;
        i += 1;
    }
    if i < b.len() && (b[i] == b'e' || b[i] == b'E') {
        let mut j = i + 1;
        if j < b.len() && (b[j] == b'+' || b[j] == b'-') {
            j += 1;
        }
        if j < b.len() && b[j].is_ascii_digit() {
            is_float = true;
            i = j;
            while i < b.len() && (b[i].is_ascii_digit() || b[i] == b'_') {
                i += 1;
            }
        }
    }
    let text: String = src[start..i].chars().filter(|c| *c != '_').collect();
    if is_float {
        let (suf, ni) = lex_suffix(src, i, FLOAT_SUFFIXES);
        return Ok((Tok::Float(text, suf), ni));
    }
    // integer, maybe with a float suffix (1f32)
    let (fsuf, fni) = lex_suffix(src, i, FLOAT_SUFFIXES);
    if fsuf.is_some() {
        return Ok((Tok::Float(text, fsuf), fni));
    }
    let v: u128 = text.parse().map_err(|_| err(start, i, "integer literal too large"))?;
    let (suf, ni) = lex_suffix(src, i, INT_SUFFIXES);
    Ok((Tok::Int(v, suf), ni))
}

fn lex_suffix(src: &str, i: usize, sufs: &[&str]) -> (Option<String>, usize) {
    let b = src.as_bytes();
    let mut j = i;
    while j < b.len() && (b[j].is_ascii_alphanumeric() || b[j] == b'_') {
        j += 1;
    }
    let word = &src[i..j];
    let word = word.trim_start_matches('_');
    if sufs.contains(&word) {
        (Some(word.to_string()), j)
    } else {
        (None, i)
    }
}
