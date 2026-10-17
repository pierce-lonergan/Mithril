//! The Windows sandbox launcher and the out-of-process integrity bracket (SANDBOX.md section 2;
//! MEASUREMENT-SERVICE.md section 2, 3 step 8a). The orchestrator is the supervisor: it creates a Job
//! Object whose only handle it holds, puts the harness child in it suspended before it runs any code,
//! and holds the limits (active-process cap 1, memory, affinity, priority class, kill-on-close, no
//! breakaway). It owns the output section (so its rehash is the trusted one) and times START/STOP on
//! its own QPC. Nothing here changes a system setting; AppContainer/LPAC, the firewall rule and the
//! separate user are listed as commands for Pierce (see docs in SANDBOX.md and IMPLEMENTATION.md).
//!
//! No external crates: the Win32 calls are declared here (F0 hygiene, 03 section 14).

#![cfg(windows)]

use crate::proto::{self, OrchestratorBracket, Report, RunVerdict, Tolerances};
use std::ffi::c_void;

type Handle = *mut c_void;
const INVALID_HANDLE: Handle = usize::MAX as Handle;

#[repr(C)]
struct SecurityAttributes {
    n_length: u32,
    lp_security_descriptor: *mut c_void,
    b_inherit_handle: i32,
}

#[repr(C)]
#[derive(Default)]
struct JobBasicLimitInformation {
    per_process_user_time_limit: i64,
    per_job_user_time_limit: i64,
    limit_flags: u32,
    minimum_working_set_size: usize,
    maximum_working_set_size: usize,
    active_process_limit: u32,
    affinity: usize,
    priority_class: u32,
    scheduling_class: u32,
}

#[repr(C)]
#[derive(Default)]
struct IoCounters {
    read_ops: u64,
    write_ops: u64,
    other_ops: u64,
    read_tx: u64,
    write_tx: u64,
    other_tx: u64,
}

#[repr(C)]
#[derive(Default)]
struct JobExtendedLimitInformation {
    basic: JobBasicLimitInformation,
    io_info: IoCounters,
    process_memory_limit: usize,
    job_memory_limit: usize,
    peak_process_memory_used: usize,
    peak_job_memory_used: usize,
}

#[repr(C)]
#[derive(Default, Clone, Copy)]
struct JobBasicAccountingInformation {
    total_user_time: i64,
    total_kernel_time: i64,
    this_period_total_user_time: i64,
    this_period_total_kernel_time: i64,
    total_page_fault_count: u32,
    total_processes: u32,
    active_processes: u32,
    total_terminated_processes: u32,
}

#[repr(C)]
struct StartupInfoW {
    cb: u32,
    reserved: *mut u16,
    desktop: *mut u16,
    title: *mut u16,
    x: u32,
    y: u32,
    x_size: u32,
    y_size: u32,
    x_count_chars: u32,
    y_count_chars: u32,
    fill_attribute: u32,
    flags: u32,
    show_window: u16,
    cb_reserved2: u16,
    lp_reserved2: *mut u8,
    std_input: Handle,
    std_output: Handle,
    std_error: Handle,
}

#[repr(C)]
struct ProcessInformation {
    process: Handle,
    thread: Handle,
    process_id: u32,
    thread_id: u32,
}

const CREATE_SUSPENDED: u32 = 0x4;
const CREATE_NO_WINDOW: u32 = 0x0800_0000;
const CREATE_UNICODE_ENVIRONMENT: u32 = 0x0400;
const STARTF_USESTDHANDLES: u32 = 0x100;
const PAGE_READWRITE: u32 = 0x04;
const FILE_MAP_READ: u32 = 0x0004;
const NORMAL_PRIORITY_CLASS: u32 = 0x20;
const HANDLE_FLAG_INHERIT: u32 = 0x1;
const INFINITE: u32 = 0xFFFF_FFFF;

// Job limit flags
const JOB_OBJECT_LIMIT_ACTIVE_PROCESS: u32 = 0x08;
const JOB_OBJECT_LIMIT_PROCESS_MEMORY: u32 = 0x100;
const JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE: u32 = 0x2000;
const JOB_OBJECT_LIMIT_AFFINITY: u32 = 0x10;
const JOB_OBJECT_LIMIT_PRIORITY_CLASS: u32 = 0x20;
const JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION: u32 = 0x400;

const JOBOBJECT_BASIC_ACCOUNTING_INFORMATION: u32 = 1;
const JOBOBJECT_EXTENDED_LIMIT_INFORMATION: u32 = 9;

#[link(name = "kernel32")]
extern "system" {
    fn CreateJobObjectW(sa: *mut SecurityAttributes, name: *const u16) -> Handle;
    fn SetInformationJobObject(job: Handle, class: u32, info: *mut c_void, len: u32) -> i32;
    fn QueryInformationJobObject(job: Handle, class: u32, info: *mut c_void, len: u32, ret: *mut u32) -> i32;
    fn AssignProcessToJobObject(job: Handle, process: Handle) -> i32;
    fn TerminateJobObject(job: Handle, code: u32) -> i32;
    fn CreateProcessW(
        app: *const u16,
        cmd: *mut u16,
        proc_attrs: *mut SecurityAttributes,
        thread_attrs: *mut SecurityAttributes,
        inherit: i32,
        flags: u32,
        env: *mut c_void,
        cwd: *const u16,
        si: *mut StartupInfoW,
        pi: *mut ProcessInformation,
    ) -> i32;
    fn ResumeThread(thread: Handle) -> u32;
    fn WaitForSingleObject(h: Handle, ms: u32) -> u32;
    fn CloseHandle(h: Handle) -> i32;
    fn CreatePipe(read: *mut Handle, write: *mut Handle, sa: *mut SecurityAttributes, size: u32) -> i32;
    fn ReadFile(h: Handle, buf: *mut u8, n: u32, read: *mut u32, ov: *mut c_void) -> i32;
    fn SetHandleInformation(h: Handle, mask: u32, flags: u32) -> i32;
    fn CreateFileMappingW(file: Handle, sa: *mut SecurityAttributes, protect: u32, hi: u32, lo: u32, name: *const u16) -> Handle;
    fn MapViewOfFile(map: Handle, access: u32, hi: u32, lo: u32, bytes: usize) -> *mut c_void;
    fn UnmapViewOfFile(p: *const c_void) -> i32;
    fn QueryPerformanceCounter(c: *mut i64) -> i32;
    fn QueryPerformanceFrequency(c: *mut i64) -> i32;
    fn GetLastError() -> u32;
}

#[link(name = "bcrypt")]
extern "system" {
    fn BCryptHash(alg: Handle, key: *mut u8, keylen: u32, input: *mut u8, inlen: u32, out: *mut u8, outlen: u32) -> i32;
}
// BCRYPT_SHA256_ALG_HANDLE pseudo-handle (bcrypt.h): 0x00000041
const BCRYPT_SHA256_ALG_HANDLE: Handle = 0x41 as Handle;

fn sha256(data: &[u8]) -> [u64; 4] {
    let mut digest = [0u8; 32];
    unsafe {
        BCryptHash(
            BCRYPT_SHA256_ALG_HANDLE,
            std::ptr::null_mut(),
            0,
            data.as_ptr() as *mut u8,
            data.len() as u32,
            digest.as_mut_ptr(),
            32,
        );
    }
    let mut out = [0u64; 4];
    for i in 0..4 {
        out[i] = u64::from_le_bytes(digest[i * 8..i * 8 + 8].try_into().unwrap());
    }
    out
}

fn to_wide(s: &str) -> Vec<u16> {
    s.encode_utf16().chain(std::iter::once(0)).collect()
}

fn qpc() -> i64 {
    let mut c = 0i64;
    unsafe { QueryPerformanceCounter(&mut c) };
    c
}
fn qpf() -> i64 {
    let mut c = 0i64;
    unsafe { QueryPerformanceFrequency(&mut c) };
    c
}

/// The supervisor-held limits on the job (SANDBOX.md section 2). Values the orchestrator chooses, not
/// system settings; the kernel enforces them and the child cannot widen them (it holds no job handle).
#[derive(Clone, Copy, Debug)]
pub struct JobLimits {
    pub active_process_limit: u32,
    pub process_memory_bytes: usize,
    pub affinity_mask: usize, // 0 = do not pin
    pub priority_class: u32,
}

impl Default for JobLimits {
    fn default() -> Self {
        JobLimits {
            active_process_limit: 1,
            process_memory_bytes: 8usize << 30, // 8 GiB
            affinity_mask: 0,
            priority_class: NORMAL_PRIORITY_CLASS,
        }
    }
}

/// Result of one measured run.
pub struct RunOutcome {
    pub verdict: RunVerdict,
    pub report: Option<Report>,
    pub bracket: Option<OrchestratorBracket>,
    pub delta_o_ns: u64,
    pub raw: Vec<u8>,
}

/// Launch the harness child for one run, holding the job limits, timing START/STOP on QPC, accounting
/// job CPU, owning and rehashing the output section, and deciding the run with proto::decide_run.
pub fn run_once(
    harness_exe: &str,
    workload: &str,
    out_bytes: usize,
    golden_hash: [u64; 4],
    limits: JobLimits,
    tol_pilot_max_diff_ns: u64,
    kappa_post_100ns: u64,
) -> Result<RunOutcome, String> {
    unsafe {
        // inheritable pipe for the child's framed messages
        let mut sa = SecurityAttributes {
            n_length: std::mem::size_of::<SecurityAttributes>() as u32,
            lp_security_descriptor: std::ptr::null_mut(),
            b_inherit_handle: 1,
        };
        let mut pipe_r: Handle = INVALID_HANDLE;
        let mut pipe_w: Handle = INVALID_HANDLE;
        if CreatePipe(&mut pipe_r, &mut pipe_w, &mut sa, 1 << 20) == 0 {
            return Err(format!("CreatePipe failed {}", GetLastError()));
        }
        // the read end stays with us, non-inheritable
        SetHandleInformation(pipe_r, HANDLE_FLAG_INHERIT, 0);

        // the output section: we own it, map it RW for the child (inheritable) and RO for our rehash
        let total = out_bytes + 65536;
        let section = CreateFileMappingW(
            INVALID_HANDLE,
            &mut sa,
            PAGE_READWRITE,
            (total >> 32) as u32,
            (total & 0xffff_ffff) as u32,
            std::ptr::null(),
        );
        if section.is_null() {
            return Err(format!("CreateFileMapping failed {}", GetLastError()));
        }
        let our_view = MapViewOfFile(section, FILE_MAP_READ, 0, 0, total) as *const u8;
        if our_view.is_null() {
            return Err(format!("MapViewOfFile(RO) failed {}", GetLastError()));
        }

        // job with the supervisor-held limits, assigned before the child runs
        let job = CreateJobObjectW(std::ptr::null_mut(), std::ptr::null());
        if job.is_null() {
            return Err(format!("CreateJobObject failed {}", GetLastError()));
        }
        let mut eli = JobExtendedLimitInformation::default();
        eli.basic.limit_flags = JOB_OBJECT_LIMIT_ACTIVE_PROCESS
            | JOB_OBJECT_LIMIT_PROCESS_MEMORY
            | JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            | JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION
            | JOB_OBJECT_LIMIT_PRIORITY_CLASS;
        eli.basic.active_process_limit = limits.active_process_limit;
        eli.basic.priority_class = limits.priority_class;
        eli.process_memory_limit = limits.process_memory_bytes;
        if limits.affinity_mask != 0 {
            eli.basic.limit_flags |= JOB_OBJECT_LIMIT_AFFINITY;
            eli.basic.affinity = limits.affinity_mask;
        }
        if SetInformationJobObject(
            job,
            JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
            &mut eli as *mut _ as *mut c_void,
            std::mem::size_of::<JobExtendedLimitInformation>() as u32,
        ) == 0
        {
            return Err(format!("SetInformationJobObject failed {}", GetLastError()));
        }

        // spawn the harness suspended, passing the inherited handle values numerically
        let cmd = format!(
            "x4harness.exe --pipe {} --section {} --out-bytes {} --workload {}{}",
            pipe_w as usize,
            section as usize,
            out_bytes,
            workload,
            if limits.affinity_mask != 0 {
                format!(" --affinity {}", limits.affinity_mask)
            } else {
                String::new()
            }
        );
        let mut cmd_w = to_wide(&cmd);
        let app_w = to_wide(harness_exe);
        let mut si: StartupInfoW = std::mem::zeroed();
        si.cb = std::mem::size_of::<StartupInfoW>() as u32;
        si.flags = STARTF_USESTDHANDLES;
        si.std_output = pipe_w; // harness defaults framed output to stdout if --pipe missing; we pass both
        si.std_error = INVALID_HANDLE;
        si.std_input = INVALID_HANDLE;
        let mut pi: ProcessInformation = std::mem::zeroed();
        let ok = CreateProcessW(
            app_w.as_ptr(),
            cmd_w.as_mut_ptr(),
            std::ptr::null_mut(),
            std::ptr::null_mut(),
            1,
            CREATE_SUSPENDED | CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT,
            std::ptr::null_mut(),
            std::ptr::null(),
            &mut si,
            &mut pi,
        );
        if ok == 0 {
            return Err(format!("CreateProcess failed {}", GetLastError()));
        }
        // assign to the job BEFORE it runs any code
        if AssignProcessToJobObject(job, pi.process) == 0 {
            TerminateJobObject(job, 1);
            return Err(format!("AssignProcessToJobObject failed {}", GetLastError()));
        }
        // close our copy of the write end so our ReadFile sees EOF when the child exits
        // (the child keeps its inherited copy)
        // accounting at start
        let acct_start = read_accounting(job);
        let freq = qpf();
        ResumeThread(pi.thread);
        CloseHandle(pi.thread);
        CloseHandle(pipe_w);

        // read all framed bytes until EOF; capture QPC when START and STOP frames arrive
        let mut raw = Vec::new();
        let mut buf = [0u8; 65536];
        let mut t_start_qpc = 0i64;
        let mut t_stop_qpc = 0i64;
        let mut scanned = 0usize;
        loop {
            let mut n = 0u32;
            let r = ReadFile(pipe_r, buf.as_mut_ptr(), buf.len() as u32, &mut n, std::ptr::null_mut());
            if r == 0 || n == 0 {
                break;
            }
            raw.extend_from_slice(&buf[..n as usize]);
            // scan newly-completed frames for START/STOP and stamp QPC as close as we can
            if let Ok(msgs) = proto::parse(&raw[scanned..raw.len()]) {
                for m in &msgs {
                    if m.mtype == proto::T_START && t_start_qpc == 0 {
                        t_start_qpc = qpc();
                    }
                    if m.mtype == proto::T_STOP && t_stop_qpc == 0 {
                        t_stop_qpc = qpc();
                    }
                }
                // advance scanned to a frame boundary
                scanned = raw.len();
            }
        }
        let acct_stop = read_accounting(job);
        WaitForSingleObject(pi.process, INFINITE);
        let acct_after = read_accounting(job);
        TerminateJobObject(job, 0);

        // rehash the output section we own (step 8a)
        let out_slice = std::slice::from_raw_parts(our_view, out_bytes);
        let orch_hash = sha256(out_slice);

        CloseHandle(pi.process);
        UnmapViewOfFile(our_view as *const c_void);
        CloseHandle(section);
        CloseHandle(pipe_r);
        CloseHandle(job);

        let delta_o_ns = if t_stop_qpc > t_start_qpc && freq > 0 {
            ((t_stop_qpc - t_start_qpc) as i128 * 1_000_000_000i128 / freq as i128) as u64
        } else {
            0
        };
        // CPU charged after STOP (100-ns ticks): accounting delta between STOP sample and final sample
        let cpu_after_stop = (acct_after.total_user_time + acct_after.total_kernel_time)
            .saturating_sub(acct_stop.total_user_time + acct_stop.total_kernel_time) as u64;
        let _ = acct_start;

        // decode the report
        let msgs = proto::parse(&raw)?;
        let report = msgs.iter().find(|m| m.mtype == proto::T_REPORT).map(|m| Report::from_msg(m));
        match report {
            Some(Ok(rep)) => {
                let tol = Tolerances {
                    tau_clock_ns: Tolerances::tau_clock(tol_pilot_max_diff_ns, delta_o_ns.max(1)),
                    kappa_post_100ns,
                    spin_budget_cycles: 0,
                    idle_budget_cycles: 0,
                };
                let br = OrchestratorBracket {
                    delta_o_ns,
                    cpu_after_stop_100ns: cpu_after_stop,
                    orch_hash,
                    golden_hash,
                };
                let verdict = proto::decide_run(&rep, &br, &tol);
                Ok(RunOutcome { verdict, report: Some(rep), bracket: Some(br), delta_o_ns, raw })
            }
            _ => {
                let fail = msgs.iter().find(|m| m.mtype == proto::T_FAIL);
                Ok(RunOutcome {
                    verdict: RunVerdict::IntegrityFail(format!(
                        "no REPORT frame (fail: {:?})",
                        fail.map(|m| m.vals.clone())
                    )),
                    report: None,
                    bracket: None,
                    delta_o_ns,
                    raw,
                })
            }
        }
    }
}

/// One sandbox self-test probe result (SANDBOX.md section 5), as emitted inside the sandbox.
#[derive(Clone, Copy, Debug)]
pub struct ProbeResult {
    pub id: u64,
    pub attempted: u64,
    pub succeeded: u64,
    pub error: u64,
    pub extra: u64,
}

/// Launch the harness in --selftest mode inside the Job Object and return its probe results. The job
/// holds the supervisor limits; this is the inside half of the positive-control comparison. `probe_args`
/// are the harness `--probe-*` flags (loopback port, sealed path, scratch, ...). No output section.
pub fn run_selftest_in_job(harness_exe: &str, probe_args: &[String], limits: JobLimits) -> Result<Vec<ProbeResult>, String> {
    unsafe {
        let mut sa = SecurityAttributes {
            n_length: std::mem::size_of::<SecurityAttributes>() as u32,
            lp_security_descriptor: std::ptr::null_mut(),
            b_inherit_handle: 1,
        };
        let mut pipe_r: Handle = INVALID_HANDLE;
        let mut pipe_w: Handle = INVALID_HANDLE;
        if CreatePipe(&mut pipe_r, &mut pipe_w, &mut sa, 1 << 20) == 0 {
            return Err(format!("CreatePipe failed {}", GetLastError()));
        }
        SetHandleInformation(pipe_r, HANDLE_FLAG_INHERIT, 0);

        let job = CreateJobObjectW(std::ptr::null_mut(), std::ptr::null());
        if job.is_null() {
            return Err("CreateJobObject failed".into());
        }
        let mut eli = JobExtendedLimitInformation::default();
        eli.basic.limit_flags = JOB_OBJECT_LIMIT_ACTIVE_PROCESS
            | JOB_OBJECT_LIMIT_PROCESS_MEMORY
            | JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            | JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION
            | JOB_OBJECT_LIMIT_PRIORITY_CLASS;
        eli.basic.active_process_limit = limits.active_process_limit;
        eli.basic.priority_class = limits.priority_class;
        eli.process_memory_limit = limits.process_memory_bytes;
        if limits.affinity_mask != 0 {
            eli.basic.limit_flags |= JOB_OBJECT_LIMIT_AFFINITY;
            eli.basic.affinity = limits.affinity_mask;
        }
        SetInformationJobObject(
            job,
            JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
            &mut eli as *mut _ as *mut c_void,
            std::mem::size_of::<JobExtendedLimitInformation>() as u32,
        );

        let mut cmd = format!("x4harness.exe --selftest --pipe {}", pipe_w as usize);
        for a in probe_args {
            cmd.push(' ');
            cmd.push_str(a);
        }
        let mut cmd_w = to_wide(&cmd);
        let app_w = to_wide(harness_exe);
        let mut si: StartupInfoW = std::mem::zeroed();
        si.cb = std::mem::size_of::<StartupInfoW>() as u32;
        si.flags = STARTF_USESTDHANDLES;
        si.std_output = pipe_w;
        si.std_error = INVALID_HANDLE;
        si.std_input = INVALID_HANDLE;
        let mut pi: ProcessInformation = std::mem::zeroed();
        if CreateProcessW(
            app_w.as_ptr(),
            cmd_w.as_mut_ptr(),
            std::ptr::null_mut(),
            std::ptr::null_mut(),
            1,
            CREATE_SUSPENDED | CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT,
            std::ptr::null_mut(),
            std::ptr::null(),
            &mut si,
            &mut pi,
        ) == 0
        {
            return Err(format!("CreateProcess failed {}", GetLastError()));
        }
        if AssignProcessToJobObject(job, pi.process) == 0 {
            TerminateJobObject(job, 1);
            return Err(format!("AssignProcessToJobObject failed {}", GetLastError()));
        }
        ResumeThread(pi.thread);
        CloseHandle(pi.thread);
        CloseHandle(pipe_w);
        let mut raw = Vec::new();
        let mut buf = [0u8; 65536];
        loop {
            let mut n = 0u32;
            let r = ReadFile(pipe_r, buf.as_mut_ptr(), buf.len() as u32, &mut n, std::ptr::null_mut());
            if r == 0 || n == 0 {
                break;
            }
            raw.extend_from_slice(&buf[..n as usize]);
        }
        WaitForSingleObject(pi.process, INFINITE);
        TerminateJobObject(job, 0);
        CloseHandle(pi.process);
        CloseHandle(pipe_r);
        CloseHandle(job);

        let msgs = proto::parse(&raw)?;
        let probes = msgs.iter().find(|m| m.mtype == proto::T_PROBES);
        let mut out = Vec::new();
        if let Some(m) = probes {
            // 6 u64 per entry: id, attempted, succeeded, error, elapsed_us, extra
            for e in m.vals.chunks(6) {
                if e.len() == 6 {
                    out.push(ProbeResult { id: e[0], attempted: e[1], succeeded: e[2], error: e[3], extra: e[5] });
                }
            }
        }
        Ok(out)
    }
}

fn read_accounting(job: Handle) -> JobBasicAccountingInformation {
    let mut acct = JobBasicAccountingInformation::default();
    let mut ret = 0u32;
    unsafe {
        QueryInformationJobObject(
            job,
            JOBOBJECT_BASIC_ACCOUNTING_INFORMATION,
            &mut acct as *mut _ as *mut c_void,
            std::mem::size_of::<JobBasicAccountingInformation>() as u32,
            &mut ret,
        );
    }
    acct
}
