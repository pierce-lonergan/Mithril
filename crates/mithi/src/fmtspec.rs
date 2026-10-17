//! The placeholder grammar of Rust's `std::fmt` (`format_spec`), shared by the checker, which
//! validates placeholders and argument counts, and the interpreter, which formats with them:
//!
//! ```text
//! placeholder := '{' [argument] [':' format_spec] '}'
//! format_spec := [[fill] align] [sign] ['#'] ['0'] [width] ['.' precision] type
//! align := '<' | '^' | '>'      sign := '+' | '-'
//! width := count                precision := count | '*'
//! count := integer | integer '$'
//! type := '' | '?' | 'x?' | 'X?' | 'x' | 'X' | 'o' | 'b' | 'e' | 'E' | 'p'
//! ```
//!
//! Named arguments (`{name}`, `name$`) are not supported by mithi v0 (E-TYPE with that message).
//! Review 2026-10-16: specs were accepted and partly ignored (`{:+}`, `{:e}`, `{:*^7}`, `{:#?}`),
//! unknown types (`{:Q}`) were accepted, and positional arguments were rejected.

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Count {
    Lit(usize),
    /// the value of argument n (a `usize`)
    Arg(usize),
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Spec {
    /// the argument printed
    pub arg: usize,
    pub fill: char,
    pub align: Option<char>,
    pub plus: bool,
    pub minus: bool,
    pub alt: bool,
    pub zero: bool,
    pub width: Option<Count>,
    pub precision: Option<Count>,
    /// "", "?", "x?", "X?", "x", "X", "o", "b", "e", "E" or "p"
    pub ty: String,
}

fn parse_count(s: &str, i: &mut usize) -> Result<Option<Count>, String> {
    let b: Vec<char> = s.chars().collect();
    let start = *i;
    while *i < b.len() && b[*i].is_ascii_digit() {
        *i += 1;
    }
    if *i == start {
        // `name$` is a named count; letters without `$` are the format type
        let mut k = *i;
        while k < b.len() && (b[k].is_ascii_alphanumeric() || b[k] == '_') {
            k += 1;
        }
        if k > *i && k < b.len() && b[k] == '$' {
            return Err("named arguments in format strings are not supported by mithi v0".into());
        }
        return Ok(None);
    }
    let n: usize = b[start..*i].iter().collect::<String>().parse().map_err(|_| "a width or precision too large".to_string())?;
    if *i < b.len() && b[*i] == '$' {
        *i += 1;
        return Ok(Some(Count::Arg(n)));
    }
    Ok(Some(Count::Lit(n)))
}

/// One placeholder's text (between the braces); `implicit` is the next implicit argument index.
pub fn parse_placeholder(inner: &str, implicit: &mut usize) -> Result<Spec, String> {
    let (arg_part, spec_part) = match inner.find(':') {
        Some(k) => (&inner[..k], &inner[k + 1..]),
        None => (inner, ""),
    };
    let arg_part = arg_part.trim();
    let explicit = if arg_part.is_empty() {
        None
    } else if arg_part.chars().all(|c| c.is_ascii_digit()) {
        Some(arg_part.parse::<usize>().map_err(|_| "argument index too large".to_string())?)
    } else {
        return Err("named arguments in format strings are not supported by mithi v0".into());
    };
    let b: Vec<char> = spec_part.chars().collect();
    let mut i = 0;
    let mut spec = Spec { arg: 0, fill: ' ', align: None, plus: false, minus: false, alt: false, zero: false, width: None, precision: None, ty: String::new() };
    if b.len() >= 2 && matches!(b[1], '<' | '^' | '>') {
        spec.fill = b[0];
        spec.align = Some(b[1]);
        i = 2;
    } else if !b.is_empty() && matches!(b[0], '<' | '^' | '>') {
        spec.align = Some(b[0]);
        i = 1;
    }
    if i < b.len() && b[i] == '+' {
        spec.plus = true;
        i += 1;
    } else if i < b.len() && b[i] == '-' {
        spec.minus = true;
        i += 1;
    }
    if i < b.len() && b[i] == '#' {
        spec.alt = true;
        i += 1;
    }
    if i < b.len() && b[i] == '0' && !(i + 1 < b.len() && b[i + 1] == '$') {
        spec.zero = true;
        i += 1;
    }
    let rest: String = b[i..].iter().collect();
    let mut j = 0;
    spec.width = parse_count(&rest, &mut j)?;
    let rb: Vec<char> = rest.chars().collect();
    let mut star = false;
    if j < rb.len() && rb[j] == '.' {
        j += 1;
        if j < rb.len() && rb[j] == '*' {
            star = true;
            j += 1;
        } else {
            match parse_count(&rest, &mut j)? {
                Some(c) => spec.precision = Some(c),
                None => return Err("a `.` in a format spec needs a precision".into()),
            }
        }
    }
    let ty: String = rb[j..].iter().collect();
    if !matches!(ty.as_str(), "" | "?" | "x?" | "X?" | "x" | "X" | "o" | "b" | "e" | "E" | "p") {
        return Err(format!("unknown format trait `{ty}` (Rust's types are ?, x, X, o, b, e, E and p)"));
    }
    spec.ty = ty;
    // `.*` takes two arguments, the precision first (std::fmt)
    if star {
        spec.precision = Some(Count::Arg(*implicit));
        *implicit += 1;
    }
    spec.arg = match explicit {
        Some(n) => n,
        None => {
            let n = *implicit;
            *implicit += 1;
            n
        }
    };
    Ok(spec)
}

/// The arguments a list of placeholders uses (each must be given and each given one used).
pub fn args_used(specs: &[Spec]) -> Vec<usize> {
    let mut v = vec![];
    for s in specs {
        v.push(s.arg);
        for c in [s.width, s.precision].into_iter().flatten() {
            if let Count::Arg(n) = c {
                v.push(n);
            }
        }
    }
    v.sort();
    v.dedup();
    v
}

/// Pad a formatted value to the spec's width: zeros after the sign and radix prefix with `0`,
/// otherwise the fill character with the alignment (numbers default right, others left).
pub fn pad(s: String, spec: &Spec, width: Option<usize>, numeric: bool) -> String {
    let Some(w) = width else { return s };
    let n = s.chars().count();
    if n >= w {
        return s;
    }
    let padn = w - n;
    if spec.zero && numeric {
        let mut plen = 0;
        let bytes = s.as_bytes();
        if !bytes.is_empty() && (bytes[0] == b'-' || bytes[0] == b'+') {
            plen = 1;
        }
        if s[plen..].starts_with("0x") || s[plen..].starts_with("0b") || s[plen..].starts_with("0o") {
            plen += 2;
        }
        return format!("{}{}{}", &s[..plen], "0".repeat(padn), &s[plen..]);
    }
    let f = spec.fill.to_string();
    match spec.align.unwrap_or(if numeric { '>' } else { '<' }) {
        '<' => format!("{s}{}", f.repeat(padn)),
        '^' => format!("{}{s}{}", f.repeat(padn / 2), f.repeat(padn - padn / 2)),
        _ => format!("{}{s}", f.repeat(padn)),
    }
}
