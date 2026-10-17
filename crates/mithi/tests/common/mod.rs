//! Shared helpers for the regression tests written after the 2026-10-16 review (same family,
//! independent context). A case is (id, expected primary code or "accept", flags, source); flags
//! are those of the CLI: `--canonical-prelude`, `--module NAME`, `--subset agent`.

#![allow(dead_code)]

use mithi::check::{check, Checked, Config, Subset};
use mithi::diag::FileRole;
use mithi::lower::{SourceInput, CANONICAL_PRELUDE};

pub fn checked(src: &str, flags: &str) -> Checked {
    let mut cfg = Config::default();
    let words: Vec<&str> = flags.split_whitespace().collect();
    let mut module = String::new();
    let mut i = 0;
    while i < words.len() {
        match words[i] {
            "--canonical-prelude" => cfg.inputs.push(SourceInput { name: "<canonical prelude>".into(), text: CANONICAL_PRELUDE.into(), role: FileRole::Prelude, module: String::new() }),
            "--module" => {
                i += 1;
                module = words.get(i).copied().unwrap_or("").to_string();
            }
            "--subset" => {
                i += 1;
                if words.get(i) == Some(&"agent") {
                    cfg.subset = Subset::Agent;
                }
            }
            other => panic!("unknown test flag {other}"),
        }
        i += 1;
    }
    cfg.inputs.push(SourceInput { name: "case.mith".into(), text: format!("{src}\n"), role: FileRole::User, module });
    check(&cfg)
}

/// The primary code, or "accept".
pub fn verdict(c: &Checked) -> String {
    match c.primary() {
        Some(d) if !c.errors().is_empty() => d.code.clone(),
        _ => "accept".to_string(),
    }
}

/// Run cases; returns one line per case whose verdict differs.
pub fn run_cases(cases: &[(&str, &str, &str, &str)]) -> Vec<String> {
    let mut bad = vec![];
    for (id, want, flags, src) in cases {
        let c = checked(src, flags);
        let got = verdict(&c);
        if got != *want {
            let all: Vec<String> = c.errors().iter().map(|d| mithi::diag::render_text(c.sm(), d)).collect();
            bad.push(format!("{id}: want {want}, got {got}\n{}", all.join("\n")));
        }
    }
    bad
}

/// Check, then run a function with no parameters (Ok: its value; Err: the trap report).
pub fn run_entry(src: &str, flags: &str, entry: &str) -> Result<String, String> {
    let c = checked(src, flags);
    let errs: Vec<String> = c.errors().iter().map(|d| mithi::diag::render_text(c.sm(), d)).collect();
    assert!(errs.is_empty(), "rejected: {}", errs.join("\n"));
    mithi::interp::run_entry(&c, entry)
}
