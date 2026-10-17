//! `x4svc` CLI (X4 measurement service v0). Subcommands:
//!   verify-profile [--data-dir D:\mithril-data]   read-only quiet-machine profile check; refuses when not met
//!   run --harness <exe> --workload <name> [--out-bytes N] [--affinity MASK] [--golden-zero]
//!                                                  drive one measured run through the Job Object + bracket
//!   demo-eprocess                                  print a short e-process wealth trace (sanity, no data)
//! The service never changes system settings; verify-profile prints Pierce's commands on a mismatch.

use x4svc::eprocess::{block_d, clip_for, Arm, BlockScorer, EProcess, Scorer, Test, THETA};
use x4svc::profile::{verify, ProfileSpec};
use x4svc::quantity::{LogRatio, Quantity};

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let cmd = args.get(1).map(|s| s.as_str()).unwrap_or("help");
    let code = match cmd {
        "verify-profile" => cmd_verify_profile(&args),
        "run" => cmd_run(&args),
        "selftest" => cmd_selftest(&args),
        "demo-eprocess" => cmd_demo(),
        _ => {
            eprintln!(
                "x4svc <verify-profile|run|selftest|demo-eprocess>\n  \
                 verify-profile [--data-dir PATH]\n  \
                 run --harness EXE --workload NAME [--out-bytes N] [--affinity MASK] [--golden-zero]\n  \
                 selftest --harness EXE --probe-exe EXE [--sealed PATH] [--scratch DIR]\n  \
                 demo-eprocess"
            );
            2
        }
    };
    std::process::exit(code);
}

fn arg<'a>(args: &'a [String], key: &str) -> Option<&'a str> {
    args.iter().position(|a| a == key).and_then(|i| args.get(i + 1)).map(|s| s.as_str())
}

fn cmd_verify_profile(args: &[String]) -> i32 {
    let mut spec = ProfileSpec::default();
    if let Some(d) = arg(args, "--data-dir") {
        spec.data_dir = d.to_string();
    }
    #[cfg(windows)]
    {
        let reader = x4svc::profile_win::WinState;
        let report = verify(&spec, &reader);
        print!("{}", report.diagnostic());
        return if report.refuses_to_run() { 1 } else { 0 };
    }
    #[cfg(not(windows))]
    {
        let _ = &spec;
        eprintln!("verify-profile is Windows-only (needs powercfg / Get-MpPreference)");
        2
    }
}

#[cfg(windows)]
fn cmd_run(args: &[String]) -> i32 {
    let harness = match arg(args, "--harness") {
        Some(h) => h,
        None => {
            eprintln!("run: --harness EXE required");
            return 2;
        }
    };
    let workload = arg(args, "--workload").unwrap_or("dev_write");
    let out_bytes: usize = arg(args, "--out-bytes").and_then(|s| s.parse().ok()).unwrap_or(4096);
    let affinity: usize = arg(args, "--affinity").and_then(|s| s.parse().ok()).unwrap_or(0);

    // For a dev run we grade against the hash the harness itself produces unless --golden-zero is set
    // (which grades against an all-zero hash to show a hash-mismatch integrity fail). A real session
    // grades against the meaning's golden / the incumbent's logits hash.
    let golden_zero = args.iter().any(|a| a == "--golden-zero");

    let mut limits = x4svc::sandbox::JobLimits::default();
    limits.affinity_mask = affinity;

    // first pass to learn the harness hash (dev convenience), then grade against it
    let probe = x4svc::sandbox::run_once(harness, workload, out_bytes, [0, 0, 0, 0], limits, 100_000, 1000);
    let golden = match &probe {
        Ok(o) if o.report.is_some() && !golden_zero => o.report.as_ref().unwrap().harness_hash(),
        _ => [0, 0, 0, 0],
    };
    let outcome = x4svc::sandbox::run_once(harness, workload, out_bytes, golden, limits, 100_000, 1000);
    match outcome {
        Ok(o) => {
            println!("workload: {}", workload);
            if std::env::var("X4_DEBUG").is_ok() {
                eprintln!("raw bytes: {}", o.raw.len());
                if let Ok(ms) = x4svc::proto::parse(&o.raw) {
                    for m in &ms {
                        eprintln!("  frame type={} seq={} vals={}", m.mtype, m.seq, m.vals.len());
                    }
                } else {
                    eprintln!("  parse error on raw");
                }
            }
            println!("delta_o (orchestrator wall bracket): {} ns", o.delta_o_ns);
            if let Some(r) = &o.report {
                println!("delta_h (harness clock):            {} ns", r.delta_h_ns());
                let q = x4svc::run_time_quantity(r.delta_h_ns(), "mp:9950x/<profile-hash-unpinned>");
                println!("Quantity: {}", q.format());
            }
            println!("verdict: {:?}", o.verdict);
            match o.verdict {
                x4svc::proto::RunVerdict::Accept => 0,
                x4svc::proto::RunVerdict::IntegrityFail(_) => 1,
            }
        }
        Err(e) => {
            eprintln!("run error: {}", e);
            3
        }
    }
}

#[cfg(not(windows))]
fn cmd_run(_args: &[String]) -> i32 {
    eprintln!("run is Windows-only");
    2
}

#[cfg(windows)]
fn cmd_selftest(args: &[String]) -> i32 {
    use x4svc::selftest::{verdict, Decision, Probe};
    let harness = match arg(args, "--harness") {
        Some(h) => h,
        None => {
            eprintln!("selftest: --harness EXE required");
            return 2;
        }
    };
    let probe_exe = match arg(args, "--probe-exe") {
        Some(p) => p,
        None => {
            eprintln!("selftest: --probe-exe EXE required (the outside positive control)");
            return 2;
        }
    };
    // Loopback positive-control listener: accept and immediately close, on its own thread.
    let listener = std::net::TcpListener::bind("127.0.0.1:0").expect("bind loopback");
    let port = listener.local_addr().unwrap().port();
    std::thread::spawn(move || {
        for s in listener.incoming() {
            drop(s); // accept and close; the probe only needs the connect to succeed/deny
        }
    });

    let mut probe_args: Vec<String> = vec!["--probe-port".into(), port.to_string()];
    if let Some(sealed) = arg(args, "--sealed") {
        probe_args.push("--sealed".into());
        probe_args.push(sealed.into());
    }
    if let Some(scratch) = arg(args, "--scratch") {
        probe_args.push("--scratch".into());
        probe_args.push(scratch.into());
    }

    // outside positive control: run the probe exe directly (no job, no AppContainer)
    let mut outside_cmd = std::process::Command::new(probe_exe);
    outside_cmd.arg("--probe-port").arg(port.to_string());
    if let Some(sealed) = arg(args, "--sealed") {
        outside_cmd.arg("--sealed").arg(sealed);
    }
    let out = match outside_cmd.output() {
        Ok(o) => o,
        Err(e) => {
            eprintln!("selftest: failed to run outside probe: {}", e);
            return 3;
        }
    };
    let mut outside: Vec<Probe> = Vec::new();
    let text = String::from_utf8_lossy(&out.stdout);
    for line in text.lines() {
        let f: Vec<&str> = line.split_whitespace().collect();
        if f.len() == 7 && f[0] == "probe" {
            outside.push(Probe {
                id: f[1].parse().unwrap_or(0),
                attempted: f[2] == "1",
                succeeded: f[3] == "1",
                error: f[4].parse().unwrap_or(0),
            });
        }
    }
    // inside: harness --selftest in the Job Object
    let inside_raw = match x4svc::sandbox::run_selftest_in_job(harness, &probe_args, x4svc::sandbox::JobLimits::default()) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("selftest: inside run failed: {}", e);
            return 3;
        }
    };
    let inside: Vec<Probe> = inside_raw
        .iter()
        .map(|r| Probe { id: r.id, attempted: r.attempted != 0, succeeded: r.succeeded != 0, error: r.error })
        .collect();

    println!("== sandbox self-test (inside the Job Object vs outside positive control) ==");
    println!("{:<28} {:>14} {:>14}", "probe", "inside", "outside");
    let mut ids: Vec<u64> = inside.iter().map(|p| p.id).collect();
    for p in &outside {
        if !ids.contains(&p.id) {
            ids.push(p.id);
        }
    }
    ids.sort();
    let fmtp = |o: Option<&Probe>| -> String {
        match o {
            Some(p) if !p.attempted => "skipped".into(),
            Some(p) if p.succeeded => "SUCCEEDED".into(),
            Some(p) => format!("blocked(e={})", p.error),
            None => "-".into(),
        }
    };
    for pid in ids {
        let i = inside.iter().find(|p| p.id == pid);
        let o = outside.iter().find(|p| p.id == pid);
        println!("{:<28} {:>14} {:>14}", pid, fmtp(i), fmtp(o));
    }
    let v = verdict(&inside, &outside);
    println!("\nstate: {:?}", v.state);
    println!("decision -> hearth-c-ref (trusted C): {:?}", v.trusted_c);
    println!("decision -> untrusted workloads:      {:?}", v.untrusted);
    for n in &v.notes {
        println!("  note: {}", n);
    }
    if v.untrusted == Decision::Refuse {
        println!("\n(Refusal for untrusted workloads is expected until Pierce runs the one-time SANDBOX.md commands.)");
    }
    0
}

#[cfg(not(windows))]
fn cmd_selftest(_args: &[String]) -> i32 {
    eprintln!("selftest is Windows-only");
    2
}

fn cmd_demo() -> i32 {
    // A short, data-free sanity trace: a true 3% regression should NOT cross the NI threshold quickly.
    let sigma = 0.02;
    let c = clip_for(sigma);
    let c_run = 4.0 * sigma;
    let mut sc = BlockScorer::new(Scorer::R, c, c_run);
    let mut ni = EProcess::make(Test::NonInferiority, c, THETA);
    println!("demo: NI e-process, 12 blocks at a planted +3% (log 1.03 ~ 0.0296), no noise");
    for i in 1..=12 {
        // B three percent slower each run; A at 0. (deterministic, illustrative only)
        let runs = [
            (Arm::A, 0.0),
            (Arm::B, 0.0295588),
            (Arm::B, 0.0295588),
            (Arm::A, 0.0),
        ];
        let d = block_d(&runs);
        let x = sc.score(d, &runs);
        let k = ni.update(x);
        let q = Quantity::<LogRatio>::simulated(d, "demo");
        println!("  block {:>2}: d={:+.5} x={:+.5} K_ni={:.4}  ({})", i, d, x, k, q.format());
    }
    println!("crossed 20? {}", ni.crossed());
    0
}
