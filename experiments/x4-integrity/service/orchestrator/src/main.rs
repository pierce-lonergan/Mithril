//! `x4svc` CLI (X4 measurement service v0). No gate data is collected by any subcommand here; the
//! `run` demos and `selftest` exercise the machinery on the track's own dev workloads only.
//!
//!   verify-profile [--data-dir D] [--collection --pins FILE --scratch DIR [--affinity MASK] [--env K=V]...]
//!   fingerprint --scratch DIR [--affinity MASK] [--env K=V]...   print the section 5.2 fields and SHA-256
//!   run --harness EXE --workload NAME --scratch DIR [--out-bytes N] [--affinity MASK] [--threads N]
//!       [--param N] [--env K=V]... [--dev-canary] (--golden 64HEX | --dev-self-golden)
//!   selftest --harness EXE --probe-exe EXE [--sealed PATH] [--scratch DIR] [--affinity MASK]
//!   demo-eprocess
//!
//! Noise-pilot readiness (X4 pilot track, 2026-10-23; docs/m0/prereg/X4-noise-pilot.md):
//!   topology                                  the cores, the CCDs and the record's mechanical masks
//!   verify-hygiene --config FILE [--as-pilot] every pre-start item and sensor, read-only (no runs)
//!   pilot-plan --config FILE                  the session order and per-session seeds from the seed
//!   dev-run --config FILE --run-type ID [--param N] [--dev-self-golden]
//!                                             one short dev run of a run type in observe mode
//!   pilot-night --config FILE --dry-run [--plants] [--max-sessions N] [--plant-exe EXE]
//!   pilot-night --config FILE --pilot --config-sha256 HEX
//!                                             a real pilot night (only under the signed record;
//!                                             refuses --max-sessions, --plants and --plant-exe)
//!
//! Revision 5 (review round 5, 2026-10-23):
//!   config-hash --config FILE                 the file's SHA-256 and its canonical SHA-256 (without
//!                                             its integrity_cleared lines): the pre-night amendment
//!                                             records the canonical one, `--config-sha256` repeats it
//!   pilot-close --config FILE [--config-sha256 HEX]
//!                                             close nights left open by a crash (outside a window,
//!                                             with no other x4svc running); marks their sessions
//!   pilot-estimate --data-dir DIR (--freeze-commit H --config-sha256 HEX | --dry-test) [--out FILE]
//!                                             the record's section 4/5 estimators and 7(a) fill-in,
//!                                             read-only; refuses an input that fails section 7
//!
//! `--scratch` is required wherever a run environment is built (review round 3): the run's fixed
//! scratch path (`<DIR>\run`) is the child's TEMP/TMP and enters the environment-block hash, and it
//! must be on D: (the no-new-data-on-C: rule; `%TEMP%` is on C: on the desktop [M]).

use x4svc::eprocess::{block_d, clip_for, Arm, BlockScorer, EProcess, Scorer, Test, THETA};
use x4svc::profile::{verify, Mode, ProfileSpec};
use x4svc::quantity::{LogRatio, Quantity};

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let code = match args.get(1).map(|s| s.as_str()).unwrap_or("help") {
        "verify-profile" => cmd_verify_profile(&args),
        "fingerprint" => cmd_fingerprint(&args),
        "run" => cmd_run(&args),
        "selftest" => cmd_selftest(&args),
        "demo-eprocess" => cmd_demo(),
        "topology" => cmd_topology(),
        "verify-hygiene" => cmd_verify_hygiene(&args),
        "pilot-plan" => cmd_pilot_plan(&args),
        "dev-run" => cmd_dev_run(&args),
        "pilot-night" => cmd_pilot_night(&args),
        "config-hash" => cmd_config_hash(&args),
        "pilot-close" => cmd_pilot_close(&args),
        "pilot-estimate" => cmd_pilot_estimate(&args),
        _ => {
            eprintln!(
                "x4svc <verify-profile|fingerprint|run|selftest|demo-eprocess|topology|verify-hygiene|pilot-plan|dev-run|pilot-night|config-hash|pilot-close|pilot-estimate>\n  \
                 verify-profile [--data-dir PATH] [--collection --pins FILE --scratch DIR [--affinity MASK] [--env K=V]...]\n  \
                 fingerprint --scratch DIR [--affinity MASK] [--env K=V]...\n  \
                 run --harness EXE --workload NAME --scratch DIR [--out-bytes N] [--affinity MASK] [--threads N] [--param N] [--env K=V]... [--dev-canary] (--golden 64HEX | --dev-self-golden)\n  \
                 selftest --harness EXE --probe-exe EXE [--sealed PATH] [--scratch DIR] [--affinity MASK]\n  \
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
fn flag(args: &[String], key: &str) -> bool {
    args.iter().any(|a| a == key)
}
/// Every `--env K=V` (repeatable): the record's pinned variables (e.g. HEARTH_THREADS).
fn pinned_env(args: &[String]) -> Result<Vec<(String, String)>, String> {
    let mut v = Vec::new();
    for (i, a) in args.iter().enumerate() {
        if a == "--env" {
            let kv = args.get(i + 1).ok_or("--env needs K=V")?;
            let (k, val) = kv.split_once('=').ok_or_else(|| format!("--env {:?}: no '='", kv))?;
            v.push((k.to_string(), val.to_string()));
        }
    }
    Ok(v)
}
/// `<--scratch>\run`, the fixed per-run scratch path (required; never a default on C:).
fn scratch_run_dir(args: &[String]) -> Result<String, String> {
    let root = arg(args, "--scratch").ok_or("--scratch DIR is required (on D:; the run's TEMP/TMP and part of the env-block hash)")?;
    Ok(format!("{}\\run", root.trim_end_matches('\\')))
}
fn affinity_arg(args: &[String]) -> usize {
    arg(args, "--affinity")
        .and_then(|s| match s.strip_prefix("0x") {
            Some(h) => usize::from_str_radix(h, 16).ok(),
            None => s.parse().ok(),
        })
        .unwrap_or(0)
}
fn env_block(args: &[String], scratch: &str) -> Result<x4svc::runenv::EnvBlock, String> {
    let system_root = std::env::var("SystemRoot").unwrap_or_else(|_| "C:\\Windows".into());
    x4svc::runenv::build(&system_root, scratch, &pinned_env(args)?)
}
/// Wipe and recreate the run's scratch directory, then require it to be empty: a run never starts
/// against a dirty scratch (review round 3, R1-6).
fn fresh_scratch(scratch: &str) -> Result<(), String> {
    let p = std::path::Path::new(scratch);
    if p.exists() {
        std::fs::remove_dir_all(p).map_err(|e| format!("cannot wipe scratch {}: {} (a leaked handle?)", scratch, e))?;
    }
    std::fs::create_dir_all(p).map_err(|e| format!("cannot create scratch {}: {}", scratch, e))?;
    let n = std::fs::read_dir(p).map_err(|e| format!("cannot list scratch {}: {}", scratch, e))?.count();
    if n != 0 {
        return Err(format!("scratch {} holds {} entries after the wipe; refusing to run", scratch, n));
    }
    Ok(())
}

#[cfg(windows)]
fn read_fingerprint(args: &[String]) -> Result<(x4svc::profile::Fingerprint, String), String> {
    let scratch = scratch_run_dir(args)?;
    let env = env_block(args, &scratch)?;
    let prio = x4svc::sandbox::JobLimits::default().priority_class;
    Ok((x4svc::profile_win::read_fingerprint(affinity_arg(args) as u64, prio, &env.sha256_hex), env.sha256_hex))
}

fn cmd_verify_profile(args: &[String]) -> i32 {
    let mut spec = ProfileSpec::default();
    if let Some(d) = arg(args, "--data-dir") {
        spec.data_dir = d.to_string();
    }
    let mode = if flag(args, "--collection") { Mode::Collection } else { Mode::Dev };
    if let Some(pf) = arg(args, "--pins") {
        let pins = match std::fs::read_to_string(pf).map_err(|e| e.to_string()).and_then(|t| x4svc::profile::parse_pins(&t)) {
            Ok(p) => p,
            Err(e) => {
                eprintln!("verify-profile: pins file {}: {}", pf, e);
                return 2;
            }
        };
        spec.expected_scheme_guid = pins.scheme_guid;
        spec.expected_fingerprint_hash = pins.fingerprint_sha256;
    }
    #[cfg(windows)]
    {
        let report = verify(&spec, mode, &x4svc::profile_win::WinState);
        print!("{}", report.diagnostic());
        if mode == Mode::Collection {
            // collection: every required item AND the pinned fingerprint of this run type's
            // affinity, priority and environment block
            let fp = match read_fingerprint(args) {
                Ok((fp, _)) => fp,
                Err(e) => {
                    println!("collection: REFUSED ({})", e);
                    return 1;
                }
            };
            return match x4svc::profile::verify_for_collection(&spec, &x4svc::profile_win::WinState, &fp) {
                Ok(vp) => {
                    println!("collection: MET (fingerprint {} equals the pinned hash)", vp.hash());
                    0
                }
                Err(e) => {
                    println!("collection: REFUSED: {}", e.lines().next().unwrap_or(""));
                    1
                }
            };
        }
        if report.refuses_to_run() {
            1
        } else {
            0
        }
    }
    #[cfg(not(windows))]
    {
        let _ = (&spec, mode);
        eprintln!("verify-profile is Windows-only (needs powercfg / Get-MpPreference)");
        2
    }
}

/// Print the section 5.2 fingerprint (read-only queries) and its SHA-256, plus the two pins-file lines.
#[cfg(windows)]
fn cmd_fingerprint(args: &[String]) -> i32 {
    let (fp, env_sha) = match read_fingerprint(args) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("fingerprint: {}", e);
            return 2;
        }
    };
    // the canonical lines are printed as comments, so the two pins-file lines below are the only
    // key=value lines (a pins file is strict about duplicate keys)
    for line in fp.canonical().lines() {
        println!("# {}", line);
    }
    let un = fp.unavailable();
    if !un.is_empty() {
        println!("# unavailable (explicit in the hash): {}", un.join(", "));
    }
    println!("# env-block sha256 {}", env_sha);
    println!("# pins-file lines:");
    println!("power.scheme_guid={}", fp.fields.get("power.scheme_guid").map(|s| s.as_str()).unwrap_or("unavailable"));
    println!("fingerprint.sha256={}", fp.hash_hex());
    0
}
#[cfg(not(windows))]
fn cmd_fingerprint(_args: &[String]) -> i32 {
    eprintln!("fingerprint is Windows-only");
    2
}

#[cfg(windows)]
fn cmd_run(args: &[String]) -> i32 {
    use x4svc::proto::{self, Tolerances};
    use x4svc::sandbox::{calibrate_cycle_rate, run_once, DevCanary, JobLimits, RunSpec};

    let harness = match arg(args, "--harness") {
        Some(h) => h,
        None => {
            eprintln!("run: --harness EXE required");
            return 2;
        }
    };
    let workload = arg(args, "--workload").unwrap_or("dev_write");
    let out_bytes: u64 = arg(args, "--out-bytes").and_then(|s| s.parse().ok()).unwrap_or(4096);
    let affinity = affinity_arg(args);
    let threads: u32 = arg(args, "--threads").and_then(|s| s.parse().ok()).unwrap_or(1);
    let mut param: u64 = arg(args, "--param").and_then(|s| s.parse().ok()).unwrap_or(0);
    let dev_self = flag(args, "--dev-self-golden");
    let golden_arg = arg(args, "--golden").and_then(x4svc::sha256::parse_hex_u64x4);
    if !dev_self && golden_arg.is_none() {
        eprintln!("run: supply --golden <64 hex> (a real golden/incumbent hash) or --dev-self-golden");
        return 2;
    }
    let scratch = match scratch_run_dir(args) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("run: {}", e);
            return 2;
        }
    };
    let env = match env_block(args, &scratch) {
        Ok(e) => e,
        Err(e) => {
            eprintln!("run: env block: {}", e);
            return 3;
        }
    };
    // DEV ONLY: an inheritable handle the child must not receive (review round 3, R1-3)
    let canary = if flag(args, "--dev-canary") {
        match DevCanary::new() {
            Ok(c) => {
                param = c.value();
                Some(c)
            }
            Err(e) => {
                eprintln!("run: {}", e);
                return 3;
            }
        }
    } else {
        None
    };

    // Provisional dev tolerances, NOT gate numbers. The X4-noise-pilot record fills tau_clock,
    // kappa_post, init_max and the core slack per run type by its frozen rule (2 x the pilot maximum
    // over non-voided nights, under pre-stated ceilings). kappa_post must exceed the harness's own
    // post-STOP census and hash (~0.58 Gcycles on this box for a 4-thread run [M]), so the post-STOP
    // window is a coarse ceiling; init_max here covers the dev harness's set-up (a 20 ms TSC spin).
    let tol = Tolerances {
        pilot_max_abs_diff_ns: 100_000,
        kappa_post_cycles: 2_000_000_000,
        init_max_ns: 1_000_000_000,
        // 2.0e9 since 2026-10-23: the harness's pre-init settle (x4h.c) adds Toolhelp snapshots to
        // the pre-START window; still far below dev_init_precompute's 6.7e9 [M, round 3]
        init_max_cycles: 2_000_000_000,
        extra_cores_milli: 250,
        observe_ceiling: false,
    };
    let rate = calibrate_cycle_rate();
    let mut limits = JobLimits::default();
    limits.affinity_mask = affinity;
    let salt = 0xA5A5_0000_0000_0001u64 ^ (std::process::id() as u64).rotate_left(17);

    let mk = |golden: [u64; 4]| RunSpec {
        harness_exe: harness,
        workload,
        param,
        out_bytes,
        salt,
        golden_hash: golden,
        limits,
        env: &env,
        scratch_dir: &scratch,
        tol,
        time_cap_ms: 600_000,
        declared_threads: threads,
        cycle_rate_hz: rate,
        spin_cycles: 0,
        idle_cycles: 0,
        exit_grace_ms: 0,
    };
    let cleanup = |scratch: &str| {
        if let Err(e) = std::fs::remove_dir_all(scratch) {
            eprintln!("warning: scratch cleanup failed ({}); the next run refuses to start until it is empty", e);
        }
    };

    // dev-self-golden: a first pass learns the harness hash, a second grades against it (printed,
    // non-Measured). A real session grades against the meaning's golden / the incumbent's logits hash.
    let golden = if dev_self {
        if let Err(e) = fresh_scratch(&scratch) {
            eprintln!("run: {}", e);
            return 3;
        }
        match run_once(&mk([0; 4])) {
            Ok(o) => o.observed.hash_at_exit.unwrap_or([0; 4]),
            Err(e) => {
                eprintln!("run error (learning pass): {}", e);
                cleanup(&scratch);
                return 3;
            }
        }
    } else {
        golden_arg.unwrap()
    };

    if let Err(e) = fresh_scratch(&scratch) {
        eprintln!("run: {}", e);
        return 3;
    }
    let out = run_once(&mk(golden));
    cleanup(&scratch);
    drop(canary);
    match out {
        Ok(o) => {
            let ob = &o.observed;
            println!("workload: {}  (env-block {}..; declared threads {}; affinity {:#x})", workload, &env.sha256_hex[..12], threads, affinity);
            println!("cycle rate (orchestrator-calibrated): {} Hz", rate);
            println!("delta_o (orchestrator wall bracket): {} ns", o.delta_o_ns);
            println!("pre-START (launch -> START receipt): {:?} ns, {:?} cycles; HELLO receipt {:?} ns", ob.start_ns, ob.cycles_start, ob.hello_ns);
            if let (Some(a), Some(b)) = (ob.cycles_start, ob.cycles_stop) {
                if o.delta_o_ns > 0 && rate > 0 {
                    println!("window cores: {:.3}", b.saturating_sub(a) as f64 / (o.delta_o_ns as f64 / 1e9 * rate as f64));
                }
            }
            if let (Some(b), Some(c)) = (ob.cycles_stop, ob.cycles_exit) {
                println!("post-STOP cycles: {}", c.saturating_sub(b));
            }
            if let Some(r) = &ob.report {
                match r.delta_h_ns() {
                    Some(dh) => {
                        println!("delta_h (harness clock):            {} ns", dh);
                        if o.verdict.is_accept() {
                            // dev: the profile is not verified, so this is not a Measured fact
                            let q = Quantity::<x4svc::quantity::Nanoseconds>::estimated(dh as f64);
                            println!("Quantity (dev, profile unverified): {}", q.format());
                        }
                    }
                    None => println!("delta_h: t1 <= t0 (not a duration)"),
                }
            }
            match &o.verdict {
                proto::RunVerdict::Accept => {
                    println!("verdict: Accept");
                    0
                }
                proto::RunVerdict::TimeCapped => {
                    println!("verdict: TimeCapped (slow outlier; the watchdog stopped the job)");
                    1
                }
                proto::RunVerdict::IntegrityFail(fs) => {
                    println!("verdict: IntegrityFail");
                    for f in fs {
                        println!("  [{}] {}: {}", f.class.label(), f.check, f.detail);
                    }
                    1
                }
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
    use x4svc::selftest::{verdict, Decision, Probe, SelfTestConfig};
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
    let listener = std::net::TcpListener::bind("127.0.0.1:0").expect("bind loopback");
    let port = listener.local_addr().unwrap().port();
    std::thread::spawn(move || {
        for s in listener.incoming() {
            drop(s);
        }
    });
    let mut probe_args: Vec<String> = vec!["--probe-port".into(), port.to_string()];
    let sealed = arg(args, "--sealed");
    let scratch = arg(args, "--scratch");
    if let Some(s) = sealed {
        probe_args.push("--sealed".into());
        probe_args.push(s.into());
    }
    if let Some(s) = scratch {
        probe_args.push("--scratch".into());
        probe_args.push(s.into());
    }
    let cfg = SelfTestConfig { loopback: true, sealed: sealed.is_some(), scratch: scratch.is_some() };

    let mut outside_cmd = std::process::Command::new(probe_exe);
    outside_cmd.arg("--probe-port").arg(port.to_string());
    if let Some(s) = sealed {
        outside_cmd.arg("--sealed").arg(s);
    }
    let out = match outside_cmd.output() {
        Ok(o) => o,
        Err(e) => {
            eprintln!("selftest: failed to run outside probe: {}", e);
            return 3;
        }
    };
    let mut outside: Vec<Probe> = Vec::new();
    for line in String::from_utf8_lossy(&out.stdout).lines() {
        let f: Vec<&str> = line.split_whitespace().collect();
        if f.len() == 7 && f[0] == "probe" {
            outside.push(Probe { id: f[1].parse().unwrap_or(0), attempted: f[2] == "1", succeeded: f[3] == "1", error: f[4].parse().unwrap_or(0) });
        }
    }
    // --affinity: the job gets this affinity limit, so the widen-affinity probe tests the limit a
    // pilot run has (revision 4: with none, the verdict depended on the launcher's own mask)
    let mut limits = x4svc::sandbox::JobLimits::default();
    limits.affinity_mask = affinity_arg(args);
    println!("job affinity limit: {}", if limits.affinity_mask == 0 { "none".to_string() } else { format!("{:#x}", limits.affinity_mask) });
    let inside_raw = match x4svc::sandbox::run_selftest_in_job(harness, &probe_args, limits) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("selftest: inside run failed: {}", e);
            return 3;
        }
    };
    let inside: Vec<Probe> = inside_raw.iter().map(|r| Probe { id: r.id, attempted: r.attempted != 0, succeeded: r.succeeded != 0, error: r.error }).collect();

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
        println!("{:<28} {:>14} {:>14}", pid, fmtp(inside.iter().find(|p| p.id == pid)), fmtp(outside.iter().find(|p| p.id == pid)));
    }
    let v = verdict(&inside, &outside, &cfg);
    println!("\nstate: in_job={} child_blocked={} appcontainer={} net_blocked={} brokers_blocked={} sealed_unreachable={:?}", v.state.in_job, v.state.child_creation_blocked, v.state.appcontainer, v.state.network_blocked_with_control, v.state.brokers_blocked, v.state.sealed_unreachable);
    println!("mode: {}", v.mode_label);
    println!("decision -> hearth-c-ref (trusted C): {:?}", v.trusted_c);
    println!("decision -> untrusted workloads:      {:?}", v.untrusted);
    for n in &v.notes {
        println!("  note: {}", n);
    }
    if v.untrusted == Decision::Refuse {
        println!("\n(Refusal for untrusted workloads is expected until the AppContainer launch is wired and Pierce runs the SANDBOX.md commands.)");
    }
    0
}

#[cfg(not(windows))]
fn cmd_selftest(_args: &[String]) -> i32 {
    eprintln!("selftest is Windows-only");
    2
}

fn cmd_demo() -> i32 {
    let sigma = 0.02;
    let c = clip_for(sigma);
    let c_run = 4.0 * sigma;
    let mut sc = BlockScorer::new(Scorer::R, c, c_run, 0.0);
    let mut ni = EProcess::make(Test::NonInferiority, c, THETA);
    println!("demo: NI e-process, 12 blocks at a planted +3% (log 1.03 ~ 0.0296), no noise");
    for i in 1..=12 {
        let runs = [(Arm::A, 0.0), (Arm::B, 0.0295588), (Arm::B, 0.0295588), (Arm::A, 0.0)];
        let d = block_d(&runs);
        let x = sc.score(d, &runs);
        let k = ni.update(x);
        let q = Quantity::<LogRatio>::simulated(d, "demo");
        println!("  block {:>2}: d={:+.5} x={:+.5} K_ni={:.4}  ({})", i, d, x, k, q.format());
    }
    println!("crossed 20? {}", ni.crossed());
    0
}

// ------------------------------------------------------------------ noise-pilot readiness

fn load_cfg(args: &[String]) -> Result<(x4svc::pilotcfg::PilotConfig, String), String> {
    let path = arg(args, "--config").ok_or("--config FILE is required")?;
    let text = std::fs::read_to_string(path).map_err(|e| format!("{}: {}", path, e))?;
    Ok((x4svc::pilotcfg::parse(&text).map_err(|e| format!("{}: {}", path, e))?, path.to_string()))
}

#[cfg(windows)]
fn cmd_topology() -> i32 {
    match x4svc::sensors_win::topology() {
        Ok(t) => {
            for (i, m) in t.l3.iter().enumerate() {
                println!("L3/CCD{}: mask {:#018x} ({} LPs)", i, m, m.count_ones());
            }
            for (i, c) in t.cores.iter().enumerate() {
                println!("core {:>2}: mask {:#018x} (LPs {:?})", i, c, (0..64).filter(|b| c >> b & 1 == 1).collect::<Vec<u32>>());
            }
            match t.pilot_masks() {
                Some((p, r, e)) => {
                    println!("mb-q4-avx512 LP p (first LP of the second core of CCD0): {:#x} (LP {})", p, p.trailing_zeros());
                    println!("orchestrator reserved LP (first LP of the last core of CCD1): {:#x} (LP {})", r, r.trailing_zeros());
                    println!("e2e-decode mask under C01's default (every LP but the reserved one): {:#x}", e);
                }
                None => println!("fewer than two L3 groups: the record's masks are undefined here"),
            }
            0
        }
        Err(e) => {
            eprintln!("topology: {}", e);
            3
        }
    }
}
#[cfg(not(windows))]
fn cmd_topology() -> i32 {
    eprintln!("topology is Windows-only");
    2
}

#[cfg(windows)]
fn cmd_verify_hygiene(args: &[String]) -> i32 {
    let (cfg, _) = match load_cfg(args) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("verify-hygiene: {}", e);
            return 2;
        }
    };
    let sensors = match x4svc::sensors_win::Sensors::open() {
        Ok(s) => s,
        Err(e) => {
            eprintln!("verify-hygiene: {}", e);
            return 3;
        }
    };
    // --as-pilot: judge a not-yet-pinned configuration by the PILOT rules (what fails tonight)
    let strict = cfg.grade == x4svc::pilotcfg::Grade::Pilot || flag(args, "--as-pilot");
    println!(
        "== X4 noise-pilot pre-start items, read-only ({} configuration{}; nothing is run or changed)",
        cfg.grade.label(),
        if strict { ", judged by the PILOT rules" } else { "" }
    );
    let items = x4svc::pilot::prestart_items(&cfg, &sensors, strict);
    let mut fails = 0;
    for it in &items {
        if !it.ok && it.required {
            fails += 1;
        }
        println!("  [{}] {} -- {}", if it.ok { " ok " } else if it.required { "FAIL" } else { "advisory" }, it.name, it.detail);
    }
    println!("{} of {} required items fail", fails, items.iter().filter(|i| i.required).count());
    if fails == 0 {
        0
    } else {
        1
    }
}
#[cfg(not(windows))]
fn cmd_verify_hygiene(_args: &[String]) -> i32 {
    eprintln!("verify-hygiene is Windows-only");
    2
}

fn cmd_pilot_plan(args: &[String]) -> i32 {
    let (cfg, _) = match load_cfg(args) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("pilot-plan: {}", e);
            return 2;
        }
    };
    println!(
        "grade {}; seed {}{}",
        cfg.grade.label(),
        cfg.seed_hex,
        match &cfg.freeze_commit {
            Some(f) => format!(" (rule from freeze commit {}: {})", f, x4svc::pilotcfg::seed_from_freeze(f)),
            None => String::new(),
        }
    );
    let mut total = 0.0;
    for (i, s) in cfg.schedule().iter().enumerate() {
        let rt = &cfg.run_types[s.run_type];
        let p = cfg.planned_secs(rt);
        total += p;
        println!(
            "{:>2}. {:<20} seed {:016x}  planned {:>6.0} s ({} blocks x 4 x ({} s x {} + o_rt {} s) + {} s setup)",
            i + 1,
            s.id,
            s.seed,
            p,
            rt.blocks,
            rt.t_run_plan_s,
            rt.cooldown_factor,
            rt.overhead_s,
            cfg.session_setup_s
        );
    }
    println!("total planned {:.0} s = {:.2} h", total, total / 3600.0);
    0
}

#[cfg(windows)]
fn cmd_dev_run(args: &[String]) -> i32 {
    use x4svc::observe::{observe, Ceilings};
    use x4svc::sandbox::{calibrate_cycle_rate, run_once, JobLimits, RunSpec};
    let (cfg, _) = match load_cfg(args) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("dev-run: {}", e);
            return 2;
        }
    };
    let id = arg(args, "--run-type").unwrap_or("");
    let rt = match cfg.run_type(id) {
        Some(r) => r.clone(),
        None => {
            eprintln!("dev-run: no [run_type {}]", id);
            return 2;
        }
    };
    let param: u64 = arg(args, "--param").and_then(|s| s.parse().ok()).unwrap_or(rt.param);
    let scratch = format!("{}\\run", cfg.scratch.trim_end_matches('\\'));
    let system_root = std::env::var("SystemRoot").unwrap_or_else(|_| "C:\\Windows".into());
    let env = match x4svc::runenv::build(&system_root, &scratch, &rt.env) {
        Ok(e) => e,
        Err(e) => {
            eprintln!("dev-run: env: {}", e);
            return 2;
        }
    };
    let rate = calibrate_cycle_rate();
    let c = Ceilings {
        kappa_post_cycles: rt.kappa_post_cycles,
        eps_spin_ns: rt.eps_spin_us * 1000,
        eps_idle_ns: rt.eps_idle_us * 1000,
        init_max_ns: rt.init_max_ms * 1_000_000,
        init_max_cycles: rt.init_max_cycles_at(rate),
        extra_cores_milli: rt.extra_cores_milli,
        exit_grace_ns: rt.exit_grace_ms * 1_000_000,
    };
    let (spin, idle) = c.harness_cycles(rate);
    let golden_pin = rt.golden.as_deref().and_then(x4svc::sha256::parse_hex_u64x4);
    let dev_self = flag(args, "--dev-self-golden") || golden_pin.is_none();
    let mk = |g: [u64; 4]| RunSpec {
        harness_exe: &rt.harness,
        workload: &rt.workload,
        param,
        out_bytes: rt.out_bytes,
        salt: 0xA5A5_0000_0000_0003u64 ^ (std::process::id() as u64).rotate_left(23),
        golden_hash: g,
        limits: JobLimits { active_process_limit: 1, process_memory_bytes: (rt.memory_gib as usize) << 30, affinity_mask: rt.affinity as usize, priority_class: rt.priority_class },
        env: &env,
        scratch_dir: &scratch,
        tol: c.tolerances(),
        time_cap_ms: (rt.time_cap_s * 1000) as u32,
        declared_threads: rt.threads,
        cycle_rate_hz: rate,
        spin_cycles: spin,
        idle_cycles: idle,
        exit_grace_ms: rt.exit_grace_ms as u32,
    };
    let golden = if dev_self {
        if let Err(e) = fresh_scratch(&scratch) {
            eprintln!("dev-run: {}", e);
            return 3;
        }
        let first = run_once(&mk([0; 4]));
        let _ = std::fs::remove_dir_all(&scratch);
        match first {
            Ok(o) => match o.observed.hash_at_exit {
                Some(h) if o.observed.fail_frame.is_none() => h,
                _ => {
                    eprintln!("dev-run: the learning pass produced no output (FAIL frame {:?}, verdict {:?})", o.observed.fail_frame, o.verdict.failed_checks());
                    return 3;
                }
            },
            Err(e) => {
                eprintln!("dev-run: learning pass: {}", e);
                return 3;
            }
        }
    } else {
        golden_pin.unwrap()
    };
    if let Err(e) = fresh_scratch(&scratch) {
        eprintln!("dev-run: {}", e);
        return 3;
    }
    let t_wall = std::time::Instant::now();
    let out = run_once(&mk(golden));
    let wall = t_wall.elapsed().as_secs_f64();
    let _ = std::fs::remove_dir_all(&scratch);
    match out {
        Ok(o) => {
            println!("DEV RUN (not pilot data): run type {} workload {} param {} affinity {:#x} threads {} env {}", rt.id, rt.workload, param, rt.affinity, rt.threads, env.sha256_hex);
            // revision 5: the values the pre-night amendment's rules use (o_rt from run wall - delta_o)
            println!(
                "run delta_o_ns {} delta_h_ns {:?} run_wall_s {:.3} peak_process_memory {} (job limit {} GiB) exit_code {:?}",
                o.delta_o_ns,
                o.observed.report.as_ref().and_then(|r| r.delta_h_ns()),
                wall,
                o.observed.peak_process_memory,
                rt.memory_gib,
                o.observed.exit_code
            );
            println!("golden {} ({})", x4svc::sha256::hex_u64x4(&golden), if dev_self { "learned from a first pass" } else { "pinned" });
            println!("cycle rate {} Hz; harness allowances spin {} / idle {} cycles", rate, spin, idle);
            println!("observe {}", observe(&o.observed).json(&c, rate));
            if let Some(ff) = &o.observed.fail_frame {
                println!("harness FAIL frame: {} {:?}", x4svc::proto::fail_code_name(ff[0]), ff);
            }
            if let Some(c) = &o.observed.census {
                for row in c.chunks(x4svc::proto::CENSUS_W) {
                    println!("census tid {:>6} flags {:#05x} post_t1_cycles {:>10} mxcsr {:#06x} prio {} affinity {:#x} create_ft {}", row[0], row[1], row[3].saturating_sub(row[2]), row[4], row[5] as i64, row[6], row[7]);
                }
            }
            match &o.verdict {
                x4svc::proto::RunVerdict::Accept => {
                    println!("verdict: Accept");
                    0
                }
                x4svc::proto::RunVerdict::TimeCapped => {
                    println!("verdict: TimeCapped");
                    1
                }
                x4svc::proto::RunVerdict::IntegrityFail(fs) => {
                    println!("verdict: IntegrityFail");
                    for f in fs {
                        println!("  [{}] {}: {}", f.class.label(), f.check, f.detail);
                    }
                    1
                }
            }
        }
        Err(e) => {
            eprintln!("dev-run: {}", e);
            3
        }
    }
}
#[cfg(not(windows))]
fn cmd_dev_run(_args: &[String]) -> i32 {
    eprintln!("dev-run is Windows-only");
    2
}

#[cfg(windows)]
fn cmd_pilot_night(args: &[String]) -> i32 {
    let (cfg, path) = match load_cfg(args) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("pilot-night: {}", e);
            return 2;
        }
    };
    let dry = flag(args, "--dry-run");
    let pilot = flag(args, "--pilot");
    if dry == pilot {
        eprintln!("pilot-night: exactly one of --dry-run or --pilot");
        return 2;
    }
    // a PILOT night follows the seeded schedule to the start rule; nobody ends it early or plants in it
    if pilot && ["--max-sessions", "--plants", "--plant-exe"].iter().any(|f| flag(args, f)) {
        eprintln!("pilot-night: --max-sessions, --plants and --plant-exe are dry-run options; refused with --pilot");
        return 1;
    }
    let opts = x4svc::pilot::NightOpts {
        dry,
        plants: flag(args, "--plants"),
        max_sessions: arg(args, "--max-sessions").and_then(|s| s.parse().ok()),
        plant_exe: arg(args, "--plant-exe").map(|s| s.to_string()),
        config_sha256: arg(args, "--config-sha256").map(|s| s.to_ascii_lowercase()),
    };
    x4svc::pilot::run_night(&cfg, &path, &opts)
}
#[cfg(not(windows))]
fn cmd_pilot_night(_args: &[String]) -> i32 {
    eprintln!("pilot-night is Windows-only");
    2
}

/// The configuration's file SHA-256 and canonical SHA-256 (revision 5). It parses the file first, so
/// a configuration the record refuses gets no hash to pin.
fn cmd_config_hash(args: &[String]) -> i32 {
    let (cfg, path) = match load_cfg(args) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("config-hash: {}", e);
            return 2;
        }
    };
    let text = std::fs::read_to_string(&path).unwrap_or_default();
    println!("grade {}", cfg.grade.label());
    println!("file_sha256 {}", x4svc::sha256::hex(&x4svc::sha256::digest(&std::fs::read(&path).unwrap_or_default())));
    println!("canonical_sha256 {}", x4svc::pilotcfg::config_canonical_sha256(&text));
    println!("integrity_cleared {:?}", cfg.integrity_cleared);
    0
}

#[cfg(windows)]
fn cmd_pilot_close(args: &[String]) -> i32 {
    let (cfg, path) = match load_cfg(args) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("pilot-close: {}", e);
            return 2;
        }
    };
    x4svc::pilot::pilot_close(&cfg, &path, arg(args, "--config-sha256"))
}
#[cfg(not(windows))]
fn cmd_pilot_close(_args: &[String]) -> i32 {
    eprintln!("pilot-close is Windows-only");
    2
}

fn cmd_pilot_estimate(args: &[String]) -> i32 {
    let dry = flag(args, "--dry-test");
    let opts = x4svc::estimate::EstimateOpts {
        data_dir: match arg(args, "--data-dir") {
            Some(d) => d.to_string(),
            None => {
                eprintln!("pilot-estimate: --data-dir DIR is required");
                return 2;
            }
        },
        grade: if dry { "DRY-RUN".into() } else { "PILOT".into() },
        freeze_commit: arg(args, "--freeze-commit").map(|s| s.to_ascii_lowercase()),
        config_sha256: arg(args, "--config-sha256").map(|s| s.to_ascii_lowercase()),
    };
    match x4svc::estimate::estimate(&opts) {
        Ok(rep) => {
            print!("{}", rep);
            if let Some(out) = arg(args, "--out") {
                if let Err(e) = std::fs::write(out, &rep) {
                    eprintln!("pilot-estimate: {}: {}", out, e);
                    return 3;
                }
            }
            0
        }
        Err(e) => {
            eprintln!("pilot-estimate: REFUSED: {}", e);
            1
        }
    }
}
