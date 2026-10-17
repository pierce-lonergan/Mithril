//! Evaluate the sandbox self-test: the inside/outside positive-control comparison and the refusal
//! table (SANDBOX.md sections 4, 5). Pure and unit-tested with synthetic probe sets.
//!
//! Fails closed (review R2-11): every probe the configuration calls for must be present and attempted
//! inside, or the self-test is incomplete and both workload classes are refused; a sealed file that is
//! reachable inside refuses both; the Job-Object-only state is `RunDegraded` for hearth-c-ref, never a
//! plain `Run`, and its label is carried into every run record.

/// Probe ids (mirror of sandbox/probes/x4sb_probes.h enum x4sb_probe_id).
pub mod id {
    pub const TOKEN_APPCONTAINER: u64 = 1;
    pub const TOKEN_LPAC: u64 = 2;
    pub const TOKEN_ELEVATED: u64 = 3;
    pub const TOKEN_ADMIN_ENABLED: u64 = 4;
    pub const TOKEN_USER_IS_MEASURE: u64 = 5;
    pub const JOB_IN_JOB: u64 = 10;
    pub const JOB_CREATE_CHILD: u64 = 11;
    pub const JOB_BREAKAWAY: u64 = 12;
    pub const JOB_CLEAR_LIMITS: u64 = 13;
    pub const JOB_RAISE_PRIORITY: u64 = 14;
    pub const JOB_WIDEN_AFFINITY: u64 = 15;
    pub const NET_LOOPBACK_TCP: u64 = 20;
    pub const NET_LAN_TCP: u64 = 21;
    pub const NET_DNS: u64 = 22;
    pub const BROKER_PIPE: u64 = 30;
    pub const BROKER_WMI: u64 = 31;
    pub const BROKER_TASKSCHED: u64 = 32;
    pub const BROKER_COM_LOCAL: u64 = 33;
    pub const SEALED_READ: u64 = 40;
    pub const SEALED_WRITE: u64 = 41;
    pub const SEALED_ALT_READ: u64 = 42;
    pub const SEALED_ALT_WRITE: u64 = 43;
    pub const SEALED_HARDLINK: u64 = 47;
    pub const SEALED_JUNCTION_READ: u64 = 48;
    pub const SCRATCH_EMPTY: u64 = 50;
    pub const SCRATCH_WRITE: u64 = 51;
    pub const DIRECT_IO: u64 = 52;
    pub const LARGE_PAGES: u64 = 53;
    pub const MXCSR_DEFAULT: u64 = 60;
    /// SEH crash markers: 0xE0000 + group tag
    pub const CRASH_BASE: u64 = 0xE0000;
}

#[derive(Clone, Copy, Debug)]
pub struct Probe {
    pub id: u64,
    pub attempted: bool,
    pub succeeded: bool,
    pub error: u64,
}

/// What the orchestrator configured for this self-test (which probes must therefore be present).
#[derive(Clone, Copy, Debug, Default)]
pub struct SelfTestConfig {
    pub loopback: bool,
    pub sealed: bool,
    pub scratch: bool,
}

fn find(set: &[Probe], pid: u64) -> Option<&Probe> {
    set.iter().find(|p| p.id == pid)
}
fn attempted(set: &[Probe], pid: u64) -> bool {
    matches!(find(set, pid), Some(p) if p.attempted)
}
fn blocked(set: &[Probe], pid: u64) -> bool {
    matches!(find(set, pid), Some(p) if p.attempted && !p.succeeded)
}
fn succeeded(set: &[Probe], pid: u64) -> bool {
    matches!(find(set, pid), Some(p) if p.attempted && p.succeeded)
}

/// The probes that must be present and attempted inside for this configuration.
pub fn expected_inside(cfg: &SelfTestConfig) -> Vec<u64> {
    let mut v = vec![
        id::TOKEN_APPCONTAINER,
        id::TOKEN_ELEVATED,
        id::TOKEN_ADMIN_ENABLED,
        id::JOB_IN_JOB,
        id::JOB_CREATE_CHILD,
        id::JOB_BREAKAWAY,
        id::JOB_CLEAR_LIMITS,
        id::JOB_RAISE_PRIORITY,
        id::JOB_WIDEN_AFFINITY,
        id::BROKER_WMI,
        id::BROKER_TASKSCHED,
        id::MXCSR_DEFAULT,
    ];
    if cfg.loopback {
        v.push(id::NET_LOOPBACK_TCP);
    }
    if cfg.sealed {
        v.extend([id::SEALED_READ, id::SEALED_WRITE]);
    }
    if cfg.scratch {
        v.extend([id::SCRATCH_EMPTY, id::SCRATCH_WRITE]);
    }
    v
}

#[derive(Clone, Debug, Default)]
pub struct SandboxState {
    pub missing: Vec<u64>,
    pub crashed: Vec<u64>,
    pub in_job: bool,
    pub child_creation_blocked: bool,
    pub self_limits_blocked: bool,
    pub appcontainer: bool,
    pub lpac_known: bool,
    pub measure_user: bool,
    pub elevated: bool,
    pub network_blocked_with_control: bool,
    pub brokers_blocked: bool,
    /// None when no sealed file was configured.
    pub sealed_unreachable: Option<bool>,
    pub scratch_ok: Option<bool>,
    pub mxcsr_default: bool,
    pub control_broken: bool,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Decision {
    Run,
    RunDegraded,
    Refuse,
}

#[derive(Clone, Debug)]
pub struct SelfTestVerdict {
    pub state: SandboxState,
    pub trusted_c: Decision,
    pub untrusted: Decision,
    /// The label every run record carries ("full", "appcontainer-no-user", "degraded-job-only", "refused").
    pub mode_label: &'static str,
    pub notes: Vec<String>,
}

pub fn evaluate_state(inside: &[Probe], outside: &[Probe], cfg: &SelfTestConfig) -> SandboxState {
    let mut s = SandboxState::default();
    s.missing = expected_inside(cfg).into_iter().filter(|&p| !attempted(inside, p)).collect();
    s.crashed = inside.iter().filter(|p| p.id >= id::CRASH_BASE).map(|p| p.id).collect();
    s.in_job = succeeded(inside, id::JOB_IN_JOB);
    s.child_creation_blocked = blocked(inside, id::JOB_CREATE_CHILD) && blocked(inside, id::JOB_BREAKAWAY);
    s.self_limits_blocked = blocked(inside, id::JOB_CLEAR_LIMITS)
        && blocked(inside, id::JOB_RAISE_PRIORITY)
        && blocked(inside, id::JOB_WIDEN_AFFINITY);
    s.appcontainer = succeeded(inside, id::TOKEN_APPCONTAINER);
    s.lpac_known = attempted(inside, id::TOKEN_LPAC);
    s.measure_user = succeeded(inside, id::TOKEN_USER_IS_MEASURE);
    s.elevated = succeeded(inside, id::TOKEN_ELEVATED) || succeeded(inside, id::TOKEN_ADMIN_ENABLED);
    s.mxcsr_default = succeeded(inside, id::MXCSR_DEFAULT);

    // network: inside must be blocked; the same probe outside must succeed (positive control)
    let mut control_ok = false;
    let mut net_blocked = true;
    for p in [id::NET_LOOPBACK_TCP, id::NET_LAN_TCP] {
        if attempted(inside, p) {
            if succeeded(outside, p) {
                control_ok = true;
            } else {
                s.control_broken = true;
            }
            if !blocked(inside, p) {
                net_blocked = false;
            }
        }
    }
    if attempted(inside, id::NET_DNS) && !blocked(inside, id::NET_DNS) {
        net_blocked = false;
    }
    s.network_blocked_with_control = net_blocked && control_ok;

    // brokers: every attempted broker blocked, and the always-expected ones present
    let brokers = [id::BROKER_PIPE, id::BROKER_WMI, id::BROKER_TASKSCHED, id::BROKER_COM_LOCAL];
    s.brokers_blocked = attempted(inside, id::BROKER_WMI)
        && attempted(inside, id::BROKER_TASKSCHED)
        && brokers.iter().all(|&p| !attempted(inside, p) || blocked(inside, p));

    if cfg.sealed {
        let sealed = [
            id::SEALED_READ,
            id::SEALED_WRITE,
            id::SEALED_ALT_READ,
            id::SEALED_ALT_WRITE,
            id::SEALED_HARDLINK,
            id::SEALED_JUNCTION_READ,
        ];
        // any attempted sealed probe that succeeds inside makes the store reachable
        let reachable = inside.iter().any(|p| sealed.contains(&p.id) && p.attempted && p.succeeded);
        s.sealed_unreachable = Some(!reachable && attempted(inside, id::SEALED_READ));
    }
    if cfg.scratch {
        s.scratch_ok = Some(succeeded(inside, id::SCRATCH_EMPTY) && succeeded(inside, id::SCRATCH_WRITE));
    }
    s
}

/// The refusal table (SANDBOX.md section 4), failing closed.
pub fn refusal_table(s: &SandboxState) -> (Decision, Decision, &'static str) {
    use Decision::*;
    let item_failing = !s.missing.is_empty()
        || !s.crashed.is_empty()
        || s.control_broken
        || !(s.in_job && s.child_creation_blocked && s.self_limits_blocked)
        || !s.mxcsr_default
        || s.sealed_unreachable == Some(false)
        || s.scratch_ok == Some(false);
    if item_failing {
        return (Refuse, Refuse, "refused");
    }
    let layer2 = s.appcontainer && s.network_blocked_with_control && s.brokers_blocked;
    let layer34 = s.measure_user && !s.elevated;
    match (layer2, layer34) {
        (true, true) => (Run, Run, "full"),
        (true, false) => (Run, Run, "appcontainer-no-user"), // logged warning (03 section 11.3)
        (false, true) => (Run, Refuse, "user-no-appcontainer"),
        (false, false) => (RunDegraded, Refuse, "degraded-job-only"),
    }
}

pub fn verdict(inside: &[Probe], outside: &[Probe], cfg: &SelfTestConfig) -> SelfTestVerdict {
    let state = evaluate_state(inside, outside, cfg);
    let (trusted_c, untrusted, mode_label) = refusal_table(&state);
    let mut notes = Vec::new();
    if !state.missing.is_empty() {
        notes.push(format!("self-test incomplete: expected probes missing or not attempted inside: {:?} (refuse).", state.missing));
    }
    if !state.crashed.is_empty() {
        notes.push(format!("probe groups faulted inside: {:?} (refuse).", state.crashed));
    }
    if state.control_broken {
        notes.push("positive control failed OUTSIDE the sandbox: the self-test is broken (refuse).".into());
    }
    if state.sealed_unreachable == Some(false) {
        notes.push("a sealed file was reachable from inside (refuse both).".into());
    }
    if !state.appcontainer {
        notes.push("AppContainer/LPAC not in effect (the launch is not wired in v0) -> untrusted workloads refused.".into());
    }
    if !state.lpac_known {
        notes.push("LPAC token attribute not determined (probe stubbed in v0).".into());
    }
    if !state.network_blocked_with_control {
        notes.push("network not blocked inside (or no positive control). Pierce: MithrilMeasure + outbound firewall rule (SANDBOX.md 3.2/3.3).".into());
    }
    if !state.measure_user {
        notes.push("not running as MithrilMeasure. Pierce: New-LocalUser MithrilMeasure (SANDBOX.md 3.3; elevated, one-time).".into());
    }
    if state.elevated {
        notes.push("the child token is elevated or has Administrators enabled (Owner's token in degraded mode).".into());
    }
    SelfTestVerdict { state, trusted_c, untrusted, mode_label, notes }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn p(id: u64, attempted: bool, succeeded: bool) -> Probe {
        Probe { id, attempted, succeeded, error: 0 }
    }
    fn job_core() -> Vec<Probe> {
        vec![
            p(id::JOB_IN_JOB, true, true),
            p(id::JOB_CREATE_CHILD, true, false),
            p(id::JOB_BREAKAWAY, true, false),
            p(id::JOB_CLEAR_LIMITS, true, false),
            p(id::JOB_RAISE_PRIORITY, true, false),
            p(id::JOB_WIDEN_AFFINITY, true, false),
            p(id::MXCSR_DEFAULT, true, true),
            p(id::TOKEN_ELEVATED, true, false),
            p(id::TOKEN_ADMIN_ENABLED, true, false),
        ]
    }
    fn cfg() -> SelfTestConfig {
        SelfTestConfig { loopback: true, sealed: false, scratch: false }
    }

    #[test]
    fn fully_isolated_runs_both() {
        let mut inside = job_core();
        inside.extend([
            p(id::TOKEN_APPCONTAINER, true, true),
            p(id::TOKEN_USER_IS_MEASURE, true, true),
            p(id::NET_LOOPBACK_TCP, true, false),
            p(id::NET_DNS, true, false),
            p(id::BROKER_WMI, true, false),
            p(id::BROKER_TASKSCHED, true, false),
        ]);
        let outside = vec![p(id::NET_LOOPBACK_TCP, true, true)];
        let v = verdict(&inside, &outside, &cfg());
        assert_eq!((v.trusted_c, v.untrusted, v.mode_label), (Decision::Run, Decision::Run, "full"));
    }

    #[test]
    fn job_only_is_degraded_for_trusted_and_refused_for_untrusted() {
        let mut inside = job_core();
        inside.extend([
            p(id::TOKEN_APPCONTAINER, true, false),
            p(id::NET_LOOPBACK_TCP, true, true),
            p(id::BROKER_WMI, true, true),
            p(id::BROKER_TASKSCHED, true, true),
        ]);
        let outside = vec![p(id::NET_LOOPBACK_TCP, true, true)];
        let v = verdict(&inside, &outside, &cfg());
        assert_eq!((v.trusted_c, v.untrusted), (Decision::RunDegraded, Decision::Refuse));
        assert_eq!(v.mode_label, "degraded-job-only");
    }

    #[test]
    fn empty_or_partial_probe_set_refuses_both() {
        let v = verdict(&[], &[], &cfg());
        assert_eq!((v.trusted_c, v.untrusted), (Decision::Refuse, Decision::Refuse));
        let mut inside = job_core();
        inside.push(p(id::TOKEN_APPCONTAINER, true, true)); // brokers and loopback missing
        let v = verdict(&inside, &[p(id::NET_LOOPBACK_TCP, true, true)], &cfg());
        assert_eq!(v.trusted_c, Decision::Refuse);
        assert!(!v.state.missing.is_empty());
    }

    #[test]
    fn sealed_reachable_inside_refuses_both() {
        let mut inside = job_core();
        inside.extend([
            p(id::TOKEN_APPCONTAINER, true, false),
            p(id::NET_LOOPBACK_TCP, true, true),
            p(id::BROKER_WMI, true, true),
            p(id::BROKER_TASKSCHED, true, true),
            p(id::SEALED_READ, true, true), // readable from inside
            p(id::SEALED_WRITE, true, false),
        ]);
        let c = SelfTestConfig { loopback: true, sealed: true, scratch: false };
        let v = verdict(&inside, &[p(id::NET_LOOPBACK_TCP, true, true)], &c);
        assert_eq!((v.trusted_c, v.untrusted), (Decision::Refuse, Decision::Refuse));
    }

    #[test]
    fn job_core_failure_and_broken_control_refuse_both() {
        let mut inside = job_core();
        inside[1] = p(id::JOB_CREATE_CHILD, true, true);
        let v = verdict(&inside, &[], &SelfTestConfig::default());
        assert_eq!(v.trusted_c, Decision::Refuse);
        let mut inside = job_core();
        inside.extend([p(id::TOKEN_APPCONTAINER, true, false), p(id::BROKER_WMI, true, true), p(id::BROKER_TASKSCHED, true, true)]);
        inside.push(p(id::NET_LOOPBACK_TCP, true, false));
        let v = verdict(&inside, &[p(id::NET_LOOPBACK_TCP, true, false)], &cfg());
        assert_eq!(v.trusted_c, Decision::Refuse);
    }
}
