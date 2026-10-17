//! Realistic X1-shaped programs (written by mithi's author from the public smoke-set shapes of
//! experiments/x1-harness/DESIGN.md section 5.2; same model family as mithi's author, so this is a
//! regression suite, not the P-2t twins ROADMAP section 3.2 needs from another family). Each file
//! must be accepted by the checker and its #[test] functions must pass under the interpreter.

use mithi::check::{check, Config};
use mithi::diag::{render_text, FileRole};
use mithi::lower::{SourceInput, CANONICAL_PRELUDE};
use std::path::PathBuf;

fn dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests").join("corpus")
}

/// The canonical prelude plus the canonical BlockQ4 / q4_row_dot snippets (from the documents).
pub fn config_with(user: &str, name: &str) -> Config {
    let repo = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join("..");
    let arch = std::fs::read_to_string(repo.join("docs/ARCHITECTURE.md")).unwrap();
    let lines: Vec<&str> = arch.split('\n').map(|l| l.strip_suffix('\r').unwrap_or(l)).collect();
    // D-C1 (BlockQ4) at 456-462 and D-C2 (q4_row_dot, q4_matvec) at 469-492, as verdicts.json
    // records them; tests/verdicts.rs checks those hashes
    let c1 = lines[455..462].join("\n");
    let c2 = lines[468..492].join("\n");
    let mut cfg = Config::default();
    cfg.inputs.push(SourceInput { name: "<canonical prelude>".into(), text: CANONICAL_PRELUDE.into(), role: FileRole::Prelude, module: String::new() });
    cfg.inputs.push(SourceInput { name: "<D-C1>".into(), text: c1, role: FileRole::Prelude, module: String::new() });
    cfg.inputs.push(SourceInput { name: "<D-C2>".into(), text: c2, role: FileRole::Prelude, module: String::new() });
    cfg.inputs.push(SourceInput { name: name.into(), text: user.into(), role: FileRole::User, module: String::new() });
    cfg.declare_deterministic = vec!["store".into()];
    cfg
}

fn run_file(f: &str) {
    let text = std::fs::read_to_string(dir().join(f)).unwrap();
    let c = check(&config_with(&text, f));
    let errs: Vec<String> = c.errors().iter().map(|d| render_text(c.sm(), d)).collect();
    assert!(errs.is_empty(), "{f} is rejected:\n{}", errs.join("\n"));
    let results = mithi::interp::run_tests(&c);
    assert!(!results.is_empty(), "{f} has no tests");
    let failed: Vec<String> = results.iter().filter_map(|(n, r)| r.as_ref().err().map(|m| format!("{n}: {m}"))).collect();
    for (n, r) in &results {
        println!("{f} {n} ... {}", if r.is_ok() { "ok" } else { "FAILED" });
    }
    assert!(failed.is_empty(), "{}", failed.join("\n"));
}

#[test]
fn norm() {
    run_file("norm.mith");
}
#[test]
fn evict() {
    run_file("evict.mith");
}
#[test]
fn store() {
    run_file("store.mith");
}
#[test]
fn fmt() {
    run_file("fmt.mith");
}
#[test]
fn route() {
    run_file("route.mith");
}
#[test]
fn misc() {
    run_file("misc.mith");
}
#[test]
fn q4() {
    run_file("q4.mith");
}
#[test]
fn stdx() {
    run_file("stdx.mith");
}
#[test]
fn semantics() {
    run_file("semantics.mith");
}
