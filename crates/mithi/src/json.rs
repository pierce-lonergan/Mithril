//! Minimal JSON value and parser (RFC 8259 subset sufficient for verdicts.json and fixtures).

use std::collections::BTreeMap;

#[derive(Clone, Debug, PartialEq)]
pub enum Json {
    Null,
    Bool(bool),
    Num(f64),
    Str(String),
    Arr(Vec<Json>),
    Obj(BTreeMap<String, Json>),
}

impl Json {
    pub fn get(&self, k: &str) -> Option<&Json> {
        match self {
            Json::Obj(m) => m.get(k),
            _ => None,
        }
    }
    pub fn as_str(&self) -> Option<&str> {
        match self {
            Json::Str(s) => Some(s),
            _ => None,
        }
    }
    pub fn as_arr(&self) -> &[Json] {
        match self {
            Json::Arr(a) => a,
            _ => &[],
        }
    }
    pub fn as_bool(&self) -> Option<bool> {
        match self {
            Json::Bool(b) => Some(*b),
            _ => None,
        }
    }
    pub fn as_u64(&self) -> Option<u64> {
        match self {
            Json::Num(n) if *n >= 0.0 => Some(*n as u64),
            _ => None,
        }
    }
    pub fn str_of(&self, k: &str) -> Option<&str> {
        self.get(k).and_then(|v| v.as_str())
    }
}

pub fn parse(s: &str) -> Result<Json, String> {
    let b = s.as_bytes();
    let mut i = 0;
    let v = value(s, b, &mut i)?;
    ws(b, &mut i);
    if i != b.len() {
        return Err(format!("trailing data at byte {i}"));
    }
    Ok(v)
}

fn ws(b: &[u8], i: &mut usize) {
    while *i < b.len() && (b[*i] == b' ' || b[*i] == b'\n' || b[*i] == b'\r' || b[*i] == b'\t') {
        *i += 1;
    }
}

fn value(s: &str, b: &[u8], i: &mut usize) -> Result<Json, String> {
    ws(b, i);
    if *i >= b.len() {
        return Err("unexpected end".into());
    }
    match b[*i] {
        b'{' => {
            *i += 1;
            let mut m = BTreeMap::new();
            ws(b, i);
            if *i < b.len() && b[*i] == b'}' {
                *i += 1;
                return Ok(Json::Obj(m));
            }
            loop {
                ws(b, i);
                let k = match value(s, b, i)? {
                    Json::Str(k) => k,
                    _ => return Err(format!("object key must be a string at {i}")),
                };
                ws(b, i);
                if *i >= b.len() || b[*i] != b':' {
                    return Err(format!("expected ':' at {i}"));
                }
                *i += 1;
                let v = value(s, b, i)?;
                m.insert(k, v);
                ws(b, i);
                if *i < b.len() && b[*i] == b',' {
                    *i += 1;
                    continue;
                }
                if *i < b.len() && b[*i] == b'}' {
                    *i += 1;
                    return Ok(Json::Obj(m));
                }
                return Err(format!("expected ',' or '}}' at {i}"));
            }
        }
        b'[' => {
            *i += 1;
            let mut a = Vec::new();
            ws(b, i);
            if *i < b.len() && b[*i] == b']' {
                *i += 1;
                return Ok(Json::Arr(a));
            }
            loop {
                a.push(value(s, b, i)?);
                ws(b, i);
                if *i < b.len() && b[*i] == b',' {
                    *i += 1;
                    continue;
                }
                if *i < b.len() && b[*i] == b']' {
                    *i += 1;
                    return Ok(Json::Arr(a));
                }
                return Err(format!("expected ',' or ']' at {i}"));
            }
        }
        b'"' => {
            *i += 1;
            let mut out = String::new();
            loop {
                if *i >= b.len() {
                    return Err("unterminated string".into());
                }
                let c = b[*i];
                if c == b'"' {
                    *i += 1;
                    return Ok(Json::Str(out));
                }
                if c == b'\\' {
                    *i += 1;
                    let e = b[*i];
                    *i += 1;
                    match e {
                        b'"' => out.push('"'),
                        b'\\' => out.push('\\'),
                        b'/' => out.push('/'),
                        b'b' => out.push('\u{8}'),
                        b'f' => out.push('\u{c}'),
                        b'n' => out.push('\n'),
                        b'r' => out.push('\r'),
                        b't' => out.push('\t'),
                        b'u' => {
                            let h = &s[*i..*i + 4];
                            let mut cp = u32::from_str_radix(h, 16).map_err(|_| "bad \\u")?;
                            *i += 4;
                            if (0xD800..0xDC00).contains(&cp) && s[*i..].starts_with("\\u") {
                                let lo = u32::from_str_radix(&s[*i + 2..*i + 6], 16).map_err(|_| "bad \\u")?;
                                *i += 6;
                                cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00);
                            }
                            out.push(char::from_u32(cp).unwrap_or('\u{FFFD}'));
                        }
                        _ => return Err("bad escape".into()),
                    }
                    continue;
                }
                let ch = s[*i..].chars().next().unwrap();
                out.push(ch);
                *i += ch.len_utf8();
            }
        }
        b't' if s[*i..].starts_with("true") => {
            *i += 4;
            Ok(Json::Bool(true))
        }
        b'f' if s[*i..].starts_with("false") => {
            *i += 5;
            Ok(Json::Bool(false))
        }
        b'n' if s[*i..].starts_with("null") => {
            *i += 4;
            Ok(Json::Null)
        }
        _ => {
            let st = *i;
            while *i < b.len() && (b[*i] == b'-' || b[*i] == b'+' || b[*i] == b'.' || b[*i] == b'e' || b[*i] == b'E' || b[*i].is_ascii_digit()) {
                *i += 1;
            }
            s[st..*i].parse::<f64>().map(Json::Num).map_err(|_| format!("bad value at {st}"))
        }
    }
}
