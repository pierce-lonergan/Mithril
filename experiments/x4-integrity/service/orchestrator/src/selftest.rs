//! Evaluate the sandbox self-test: the inside/outside positive-control comparison and the refusal
//! table (SANDBOX.md section 4, 5). The orchestrator runs the probes inside the sandbox and the same
//! probes outside it; a network/broker/sealed probe must FAIL inside and (where meaningful) SUCCEED
//! outside -- a probe that fails outside is broken and the session refuses. The verdict is computed
//! here from probe results only; this module is pure and unit-tested with synthetic probe sets.

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
    pub const DIRECT_IO: u64 = 52;
    pub const LARGE_PAGES: u64 = 53;
    pub const MXCSR_DEFAULT: u64 = 60;
}

/// A probe result as the evaluator consumes it (attempted/succeeded/error).
#[derive(Clone, Copy, Debug)]
pub struct Probe {
    pub id: u64,
    pub attempted: bool,
    pub succeeded: bool,
    pub error: u64,
}

fn find(set: &[Probe], pid: u64) -> Option<&Probe> {
    set.iter().find(|p| p.id == pid)
}
fn inside_blocked(set: &[Probe], pid: u64) -> bool {
    // a probe that was attempted and did NOT succeed counts as blocked
    matches!(find(set, pid), Some(p) if p.attempted && !p.succeeded)
}
fn outside_succeeds(set: &[Probe], pid: u64) -> bool {
    matches!(find(set, pid), Some(p) if p.attempted && p.succeeded)
}

/// What the self-test established about this box, for the refusal table.
#[derive(Clone, Debug, Default)]
pub struct SandboxState {
    pub in_job: bool,
    pub child_creation_blocked: bool,
    pub appcontainer: bool,
    pub lpac: bool,
    pub measure_user: bool,
    pub not_elevated: bool,
    /// network blocked inside with a valid outside positive control
    pub network_blocked_with_control: bool,
    /// every attempted broker probe blocked inside
    pub brokers_blocked: bool,
    /// every attempted sealed probe unreachable inside (read, write, alt, link)
    pub sealed_unreachable: bool,
    /// a probe that must pass outside actually failed outside -> the control is broken
    pub control_broken: bool,
}

/// The run decision per workload class (SANDBOX.md section 4 refusal table).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Decision {
    Run,
    RunDegraded,
    Refuse,
}

#[derive(Clone, Debug)]
pub struct SelfTestVerdict {
    pub state: SandboxState,
    pub trusted_c: Decision,     // hearth-c-ref at its pinned tag
    pub untrusted: Decision,     // X3 kernels, Forge candidates, any other workload
    pub notes: Vec<String>,
}

/// Build the state from inside/outside probe sets.
pub fn evaluate_state(inside: &[Probe], outside: &[Probe]) -> SandboxState {
    let mut s = SandboxState::default();
    s.in_job = outside_succeeds(inside, id::JOB_IN_JOB);
    s.child_creation_blocked = inside_blocked(inside, id::JOB_CREATE_CHILD) && inside_blocked(inside, id::JOB_BREAKAWAY);
    s.appcontainer = outside_succeeds(inside, id::TOKEN_APPCONTAINER);
    s.lpac = outside_succeeds(inside, id::TOKEN_LPAC);
    s.measure_user = outside_succeeds(inside, id::TOKEN_USER_IS_MEASURE);
    s.not_elevated = inside_blocked(inside, id::TOKEN_ELEVATED) || !outside_succeeds(inside, id::TOKEN_ELEVATED);

    // network: the positive control must succeed outside; inside must be blocked
    let net_ids = [id::NET_LOOPBACK_TCP, id::NET_LAN_TCP];
    let mut net_control_ok = false;
    let mut net_blocked = true;
    for &p in &net_ids {
        if find(inside, p).map_or(false, |x| x.attempted) {
            if outside_succeeds(outside, p) {
                net_control_ok = true;
            } else if find(outside, p).map_or(false, |x| x.attempted) {
                s.control_broken = true;
            }
            if !inside_blocked(inside, p) {
                net_blocked = false;
            }
        }
    }
    // DNS inside must also fail (residual-channel rule)
    if find(inside, id::NET_DNS).map_or(false, |x| x.attempted) && !inside_blocked(inside, id::NET_DNS) {
        net_blocked = false;
    }
    s.network_blocked_with_control = net_blocked && net_control_ok;

    let broker_ids = [id::BROKER_PIPE, id::BROKER_WMI, id::BROKER_TASKSCHED, id::BROKER_COM_LOCAL];
    s.brokers_blocked = broker_ids.iter().all(|&p| {
        find(inside, p).map_or(true, |x| !x.attempted || !x.succeeded)
    });

    let sealed_ids = [
        id::SEALED_READ, id::SEALED_WRITE, id::SEALED_ALT_READ, id::SEALED_ALT_WRITE,
        id::SEALED_HARDLINK, id::SEALED_JUNCTION_READ,
    ];
    let any_sealed = sealed_ids.iter().any(|&p| find(inside, p).map_or(false, |x| x.attempted));
    s.sealed_unreachable = any_sealed
        && sealed_ids.iter().all(|&p| find(inside, p).map_or(true, |x| !x.attempted || !x.succeeded));
    s
}

/// Apply the refusal table (SANDBOX.md section 4).
pub fn refusal_table(s: &SandboxState) -> (Decision, Decision) {
    if s.control_broken {
        // a positive control that fails outside means the self-test itself is broken: refuse both
        return (Decision::Refuse, Decision::Refuse);
    }
    let one = s.in_job && s.child_creation_blocked; // the Job Object core
    let two = s.appcontainer && s.network_blocked_with_control && s.brokers_blocked; // the broker/network block
    let three_four = s.measure_user; // separate user (scopes ACLs/firewall)

    if !one {
        return (Decision::Refuse, Decision::Refuse); // any self-test item failing
    }
    match (two, three_four) {
        (true, true) => (Decision::Run, Decision::Run),
        (true, false) => (Decision::Run, Decision::Run), // 1+2 without 3/4: run with a logged warning
        (false, _) => (Decision::Run, Decision::Refuse),  // AppContainer/net not usable: trusted C only
    }
}

/// Full verdict with human notes.
pub fn verdict(inside: &[Probe], outside: &[Probe]) -> SelfTestVerdict {
    let state = evaluate_state(inside, outside);
    let (trusted_c, untrusted) = refusal_table(&state);
    let mut notes = Vec::new();
    if state.control_broken {
        notes.push("positive control failed OUTSIDE the sandbox: the self-test is broken (refuse).".into());
    }
    if !state.appcontainer {
        notes.push("AppContainer/LPAC not in effect -> untrusted workloads refused; hearth-c-ref may run degraded. Pierce: launch under (LP)AppContainer (no system change; CreateAppContainerProfile) and verify large pages + direct I/O.".into());
    }
    if !state.network_blocked_with_control {
        notes.push("network not blocked (or no positive control). Pierce: create MithrilMeasure and the outbound firewall rule (SANDBOX.md section 3.2/3.3; elevated, one-time).".into());
    }
    if !state.measure_user {
        notes.push("not running as the separate MithrilMeasure user. Pierce: New-LocalUser MithrilMeasure (SANDBOX.md section 3.3; elevated, one-time).".into());
    }
    SelfTestVerdict { state, trusted_c, untrusted, notes }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn p(id: u64, attempted: bool, succeeded: bool) -> Probe {
        Probe { id, attempted, succeeded, error: 0 }
    }

    #[test]
    fn fully_isolated_runs_both() {
        let inside = vec![
            p(id::JOB_IN_JOB, true, true),
            p(id::JOB_CREATE_CHILD, true, false),
            p(id::JOB_BREAKAWAY, true, false),
            p(id::TOKEN_APPCONTAINER, true, true),
            p(id::TOKEN_USER_IS_MEASURE, true, true),
            p(id::NET_LOOPBACK_TCP, true, false),
            p(id::NET_LAN_TCP, true, false),
            p(id::NET_DNS, true, false),
            p(id::BROKER_PIPE, true, false),
            p(id::BROKER_WMI, true, false),
            p(id::BROKER_TASKSCHED, true, false),
            p(id::BROKER_COM_LOCAL, true, false),
            p(id::SEALED_READ, true, false),
            p(id::SEALED_WRITE, true, false),
        ];
        let outside = vec![p(id::NET_LOOPBACK_TCP, true, true), p(id::NET_LAN_TCP, true, true)];
        let v = verdict(&inside, &outside);
        assert_eq!(v.trusted_c, Decision::Run);
        assert_eq!(v.untrusted, Decision::Run);
    }

    #[test]
    fn degraded_no_appcontainer_refuses_untrusted() {
        // Job works but AppContainer absent and network open inside: hearth-c-ref runs, untrusted refused.
        let inside = vec![
            p(id::JOB_IN_JOB, true, true),
            p(id::JOB_CREATE_CHILD, true, false),
            p(id::JOB_BREAKAWAY, true, false),
            p(id::TOKEN_APPCONTAINER, true, false),
            p(id::NET_LOOPBACK_TCP, true, true), // not blocked
            p(id::NET_LAN_TCP, true, true),
        ];
        let outside = vec![p(id::NET_LOOPBACK_TCP, true, true), p(id::NET_LAN_TCP, true, true)];
        let v = verdict(&inside, &outside);
        assert_eq!(v.trusted_c, Decision::Run);
        assert_eq!(v.untrusted, Decision::Refuse);
    }

    #[test]
    fn job_core_failure_refuses_both() {
        let inside = vec![p(id::JOB_IN_JOB, true, false), p(id::JOB_CREATE_CHILD, true, true)];
        let outside = vec![];
        let v = verdict(&inside, &outside);
        assert_eq!(v.trusted_c, Decision::Refuse);
        assert_eq!(v.untrusted, Decision::Refuse);
    }

    #[test]
    fn broken_outside_control_refuses_both() {
        // network attempted inside and blocked, but the outside control also fails -> broken self-test
        let inside = vec![
            p(id::JOB_IN_JOB, true, true),
            p(id::JOB_CREATE_CHILD, true, false),
            p(id::JOB_BREAKAWAY, true, false),
            p(id::NET_LOOPBACK_TCP, true, false),
        ];
        let outside = vec![p(id::NET_LOOPBACK_TCP, true, false)];
        let v = verdict(&inside, &outside);
        assert_eq!(v.trusted_c, Decision::Refuse);
        assert_eq!(v.untrusted, Decision::Refuse);
    }
}
