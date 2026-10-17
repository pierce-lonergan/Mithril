//! The part of `mith.toml` mithi reads at X1 (note section 12): `[grants]` and
//! `[evidence] fixtures = [...]`. A minimal TOML subset: tables, strings, arrays of strings and
//! arrays of inline tables with string values.

use crate::check::Config;

#[derive(Debug, Clone, PartialEq)]
enum V {
    Str(String),
    Arr(Vec<V>),
    Table(Vec<(String, V)>),
}

pub fn apply(text: &str, cfg: &mut Config) -> Result<(), String> {
    let mut table = String::new();
    // join continued arrays onto one logical line
    let mut logical: Vec<String> = vec![];
    let mut buf = String::new();
    let mut depth = 0i32;
    for raw in text.lines() {
        let line = strip_comment(raw);
        if line.trim().is_empty() && depth == 0 {
            continue;
        }
        for ch in line.chars() {
            match ch {
                '[' | '{' => depth += 1,
                ']' | '}' => depth -= 1,
                _ => {}
            }
        }
        buf.push_str(&line);
        buf.push(' ');
        if depth <= 0 {
            logical.push(std::mem::take(&mut buf));
            depth = 0;
        }
    }
    for l in logical {
        let mut t = l.trim();
        // a table header, possibly followed by keys on the same line (01 section 11's style)
        if t.starts_with('[') && !t.starts_with("[[") {
            if let Some(close) = t.find(']') {
                let name = &t[1..close];
                if !name.contains('=') && !name.contains('"') {
                    table = name.trim().to_string();
                    t = t[close + 1..].trim();
                    if t.is_empty() {
                        continue;
                    }
                }
            }
        }
        // a line may hold several `key = value` pairs (01 section 11's example does)
        let mut rest = t;
        while !rest.is_empty() {
            let eq = rest.find('=').ok_or_else(|| format!("expected `key = value` in `{t}`"))?;
            let key = rest[..eq].trim().trim_matches('"').to_string();
            let (val, used) = parse_value(rest[eq + 1..].trim_start())?;
            let consumed = rest.len() - rest[eq + 1..].trim_start().len() + used;
            rest = rest[consumed..].trim_start();
            apply_key(&table, &key, &val, cfg)?;
        }
    }
    Ok(())
}

fn strip_comment(l: &str) -> String {
    let mut out = String::new();
    let mut in_str = false;
    for c in l.chars() {
        if c == '"' {
            in_str = !in_str;
        }
        if c == '#' && !in_str {
            break;
        }
        out.push(c);
    }
    out
}

fn parse_value(s: &str) -> Result<(V, usize), String> {
    let b = s.as_bytes();
    if b.is_empty() {
        return Err("missing value".into());
    }
    match b[0] {
        b'"' => {
            let end = s[1..].find('"').ok_or("unterminated string")? + 1;
            Ok((V::Str(s[1..end].to_string()), end + 1))
        }
        b'[' => {
            let mut i = 1;
            let mut items = vec![];
            loop {
                while i < s.len() && (b[i] == b' ' || b[i] == b',') {
                    i += 1;
                }
                if i >= s.len() {
                    return Err("unterminated array".into());
                }
                if b[i] == b']' {
                    return Ok((V::Arr(items), i + 1));
                }
                let (v, n) = parse_value(&s[i..])?;
                items.push(v);
                i += n;
            }
        }
        b'{' => {
            let mut i = 1;
            let mut kv = vec![];
            loop {
                while i < s.len() && (b[i] == b' ' || b[i] == b',') {
                    i += 1;
                }
                if i >= s.len() {
                    return Err("unterminated inline table".into());
                }
                if b[i] == b'}' {
                    return Ok((V::Table(kv), i + 1));
                }
                let eq = s[i..].find('=').ok_or("expected `=` in inline table")? + i;
                let k = s[i..eq].trim().trim_matches('"').to_string();
                let mut j = eq + 1;
                while j < s.len() && b[j] == b' ' {
                    j += 1;
                }
                let (v, n) = parse_value(&s[j..])?;
                kv.push((k, v));
                i = j + n;
            }
        }
        _ => {
            let end = s.find(|c: char| c == ' ' || c == ',' || c == ']' || c == '}').unwrap_or(s.len());
            Ok((V::Str(s[..end].to_string()), end))
        }
    }
}

fn strings(v: &V) -> Vec<String> {
    match v {
        V::Arr(a) => a.iter().filter_map(|x| if let V::Str(s) = x { Some(s.clone()) } else { None }).collect(),
        V::Str(s) => vec![s.clone()],
        _ => vec![],
    }
}

fn apply_key(table: &str, key: &str, v: &V, cfg: &mut Config) -> Result<(), String> {
    match (table, key) {
        ("grants", "declare_deterministic") => cfg.declare_deterministic = strings(v),
        ("grants", "unsafe") => cfg.grant_unsafe = strings(v),
        ("grants", "foreign") => cfg.grant_foreign = strings(v),
        ("evidence", "fixtures") => {
            let V::Arr(items) = v else { return Err("fixtures must be an array".into()) };
            for it in items {
                let V::Table(kv) = it else { return Err("each fixture is an inline table".into()) };
                let get = |k: &str| kv.iter().find(|(x, _)| x == k).and_then(|(_, v)| if let V::Str(s) = v { Some(s.clone()) } else { None }).unwrap_or_default();
                cfg.fixtures.push((get("name"), get("kind"), get("subject"), get("grade")));
            }
        }
        _ => {}
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    #[test]
    fn grants_and_fixtures() {
        let mut cfg = crate::check::Config::default();
        super::apply(
            "[grants]   unsafe = [\"std_platform\"]   foreign = [\"std_platform\"]\n           declare_deterministic = [\"store\"]\n[evidence]\nfixtures = [ { name = \"golden::x\", kind = \"deterministic\", subject = \"store::acquire\", grade = \"tested\" } ]\n",
            &mut cfg,
        )
        .unwrap();
        assert_eq!(cfg.declare_deterministic, vec!["store".to_string()]);
        assert_eq!(cfg.fixtures.len(), 1);
        assert_eq!(cfg.fixtures[0].2, "store::acquire");
    }
}
