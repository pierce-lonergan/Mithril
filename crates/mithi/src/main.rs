//! mithi command line.
//!
//!   mithi check [options] FILE...      type-check and run the MCore analyses
//!   mithi run   [options] --entry NAME FILE...   run a function with no parameters
//!   mithi test  [options] FILE...      run every #[test] function
//!   mithi parse FILE...                parse only
//!
//! Options: --json, --prelude FILE (repeatable), --canonical-prelude, --module NAME (module of the
//! user files), --doc-snippets, --loose-host NAME, --manifest mith.toml, --subset checker|agent,
//! --no-user-traits.

use mithi::check::{check, Config, Subset};
use mithi::diag::{render_json, render_text, FileRole};
use mithi::lower::SourceInput;

/// The checker and the interpreter recurse over the program; they run on a thread with a large
/// stack (a reservation, committed as used), so that deep but legal programs and deep interpreted
/// recursion end in a diagnostic or the interpreter's frame limit, not a native stack overflow
/// (review 2026-10-16: the 1 MB main-thread stack overflowed at about 300 interpreted frames).
const STACK_BYTES: usize = 1 << 30;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let json = args.iter().any(|a| a == "--json");
    let worker = std::thread::Builder::new().name("mithi".into()).stack_size(STACK_BYTES).spawn(move || cli(&args[1..]));
    let rc = match worker {
        Ok(h) => match h.join() {
            Ok(rc) => rc,
            Err(_) => {
                // a panic is an infrastructure failure of the oracle, never a verdict
                if json {
                    println!("{{\"mithi\":\"{}\",\"verdict\":\"internal-error\"}}", env!("CARGO_PKG_VERSION"));
                } else {
                    eprintln!("mithi: internal error (a panic); this is a mithi bug, not a verdict");
                }
                3
            }
        },
        Err(e) => {
            eprintln!("mithi: cannot start the worker thread: {e}");
            3
        }
    };
    std::process::exit(rc);
}

fn usage() -> i32 {
    eprintln!("usage: mithi (check|run|test|parse) [--json] [--prelude FILE] [--canonical-prelude] [--module NAME] [--doc-snippets] [--loose-host NAME] [--manifest FILE] [--subset checker|agent] [--no-user-traits] [--entry NAME] FILE...");
    2
}

fn cli(args: &[String]) -> i32 {
    if args.is_empty() {
        return usage();
    }
    let cmd = args[0].as_str();
    let mut json = false;
    let mut cfg = Config::default();
    let mut files = vec![];
    let mut module = String::new();
    let mut entry = None;
    let mut i = 1;
    let mut preludes: Vec<(String, String)> = vec![];
    while i < args.len() {
        let a = args[i].as_str();
        // options that take a value must get a non-empty one
        if matches!(a, "--prelude" | "--module" | "--loose-host" | "--entry" | "--subset" | "--manifest") {
            let v = args.get(i + 1).cloned().unwrap_or_default();
            if v.is_empty() || v.starts_with("--") {
                eprintln!("mithi: {a} needs a value");
                return 2;
            }
        }
        let mut next = || {
            i += 1;
            args.get(i).cloned().unwrap_or_default()
        };
        match a {
            "--json" => json = true,
            "--prelude" => {
                let f = next();
                match std::fs::read_to_string(&f) {
                    Ok(t) => preludes.push((f, t)),
                    Err(e) => {
                        eprintln!("mithi: cannot read {f}: {e}");
                        return 2;
                    }
                }
            }
            "--canonical-prelude" => preludes.push(("<canonical prelude>".into(), mithi::lower::CANONICAL_PRELUDE.into())),
            "--module" => module = next(),
            "--doc-snippets" => cfg.doc_snippets = true,
            "--loose-host" => cfg.loose_host = Some(next()),
            "--entry" => entry = Some(next()),
            "--no-user-traits" => cfg.no_user_traits = true,
            "--subset" => {
                cfg.subset = match next().as_str() {
                    "agent" => Subset::Agent,
                    "checker" => Subset::Checker,
                    other => {
                        // a typo must not silently select the checker subset
                        eprintln!("mithi: unknown --subset value `{other}` (checker or agent)");
                        return 2;
                    }
                }
            }
            "--manifest" => {
                let f = next();
                match std::fs::read_to_string(&f) {
                    Ok(t) => {
                        if let Err(e) = mithi::manifest::apply(&t, &mut cfg) {
                            eprintln!("mithi: {f}: {e}");
                            return 2;
                        }
                    }
                    Err(e) => {
                        eprintln!("mithi: cannot read {f}: {e}");
                        return 2;
                    }
                }
            }
            x if x.starts_with("--") => {
                eprintln!("mithi: unknown option {x}");
                return usage();
            }
            f => files.push(f.to_string()),
        }
        i += 1;
    }
    for (name, text) in preludes {
        cfg.inputs.push(SourceInput { name, text, role: FileRole::Prelude, module: String::new() });
    }
    for f in &files {
        match std::fs::read_to_string(f) {
            Ok(t) => cfg.inputs.push(SourceInput { name: f.clone(), text: t, role: FileRole::User, module: module.clone() }),
            Err(e) => {
                eprintln!("mithi: cannot read {f}: {e}");
                return 2;
            }
        }
    }
    match cmd {
        "parse" => {
            let mut rc = 0;
            for inp in &cfg.inputs {
                match mithi::parser::parse_source(0, &inp.text, inp.role != FileRole::User) {
                    Ok(items) => println!("{}: ok, {} items", inp.name, items.len()),
                    Err(d) => {
                        println!("{}: {} {}", inp.name, d.code, d.msg);
                        rc = 1;
                    }
                }
            }
            rc
        }
        "check" => {
            let c = check(&cfg);
            let errs: Vec<_> = c.diags.iter().collect();
            if json {
                let mut out = String::from("{\"mithi\":\"");
                out.push_str(env!("CARGO_PKG_VERSION"));
                // the std and canonical prelude this binary checks against (DESIGN §9.3 records
                // the oracle's identity with every call)
                out.push_str("\",\"std_sha256\":\"");
                out.push_str(&mithi::sha256::sha256_hex(format!("{}{}", mithi::lower::STD_SOURCE, mithi::lower::CANONICAL_PRELUDE).as_bytes()));
                out.push_str("\",\"verdict\":\"");
                out.push_str(if c.errors().is_empty() { "accept" } else { "reject" });
                out.push_str("\",\"primary\":");
                match c.primary() {
                    Some(d) => out.push_str(&format!("\"{}\"", d.code)),
                    None => out.push_str("null"),
                }
                out.push_str(",\"diagnostics\":[");
                for (k, d) in errs.iter().enumerate() {
                    if k > 0 {
                        out.push(',');
                    }
                    out.push_str(&render_json(c.sm(), d));
                }
                out.push_str("],\"facts\":");
                out.push_str(&c.facts.to_json(&c));
                out.push('}');
                println!("{out}");
            } else {
                for d in &errs {
                    println!("{}", render_text(c.sm(), d));
                }
                let n = c.errors().len();
                if n == 0 {
                    println!("accept");
                } else {
                    println!("reject: {n} error(s); primary {}", c.primary().unwrap().code);
                }
            }
            if c.errors().is_empty() {
                0
            } else {
                1
            }
        }
        "run" | "test" => {
            let c = check(&cfg);
            if !c.errors().is_empty() {
                for d in c.errors() {
                    eprintln!("{}", render_text(c.sm(), d));
                }
                eprintln!("mithi: the checker rejects the program; nothing runs");
                return 1;
            }
            if cmd == "run" {
                let Some(e) = entry else {
                    eprintln!("mithi run needs --entry NAME");
                    return 2;
                };
                match mithi::interp::run_entry(&c, &e) {
                    Ok(s) => {
                        println!("{s}");
                        0
                    }
                    Err(s) => {
                        println!("{s}");
                        1
                    }
                }
            } else {
                let results = mithi::interp::run_tests(&c);
                let mut failed = 0;
                for (name, r) in &results {
                    match r {
                        Ok(_) => println!("test {name} ... ok"),
                        Err(m) => {
                            failed += 1;
                            println!("test {name} ... FAILED: {m}");
                        }
                    }
                }
                println!("{} passed; {} failed", results.len() - failed, failed);
                if failed == 0 {
                    0
                } else {
                    1
                }
            }
        }
        _ => usage(),
    }
}
