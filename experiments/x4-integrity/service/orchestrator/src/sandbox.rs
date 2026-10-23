//! The Windows sandbox launcher and the out-of-process integrity bracket (SANDBOX.md section 2;
//! MEASUREMENT-SERVICE.md section 2, 3 step 8a). The orchestrator is the supervisor: it holds the Job
//! Object's only handle, puts the harness child in it suspended before it runs code, owns the output
//! section, and times/accounts/hashes the run from this process, where no workload code runs.
//!
//! What this process observes itself (all out-of-process, the trusted bracket):
//! - START/STOP QPC stamps and the child's `QueryProcessCycleTime` at START, STOP and after exit,
//!   taken the instant the frame is decoded (not at pipe EOF). CPU after STOP is charged in cycles
//!   against kappa_post (review R1-1/R2-2; job accounting is kept only as a coarse secondary).
//! - A copy and SHA-256 of the output section taken when STOP is decoded, and again after the job is
//!   terminated; they must equal each other, the harness hash and the golden (review R1-7/R2-1).
//! - Strict frame order (HELLO,START,STOP,CENSUS,REPORT with seq 0..4, or a prefix + one FAIL); any
//!   duplicate, reorder, bad seq or extra frame terminates the job and fails the run (review R1-2).
//! - A watchdog: the job is terminated at the time cap; a run capped before STOP is TimeCapped.
//! - An exit grace (revision 4, review 2026-10-23): once REPORT is received the child must exit
//!   within `exit_grace_ms`, or the job is terminated and the run fails `no_exit_after_report`, so no
//!   load can outlive its report into the next run; REPORT and exit are stamped (teardown wall).
//! - The child's exit code (must be 0), peak memory, and the bytes outside the extent.
//!
//! - HELLO receipt and the launch (first-thread resume) are stamped too, so the pre-START window is
//!   bounded out of process (`proto::decide_run`, review round 3).
//!
//! The child gets the section through a handle duplicated with only SECTION_MAP_READ|WRITE, an
//! explicit minimal environment block (runenv.rs), and a fresh scratch directory as its cwd. It
//! inherits exactly two handles, the pipe's write end and that section handle, named in a
//! PROC_THREAD_ATTRIBUTE_HANDLE_LIST (review round 3, R1-3): no other inheritable handle the
//! orchestrator holds (its own SSH stdio pipes, for example) reaches the child.
//! No external crates (F0 hygiene, 03 section 14); the SHA-256 is `crate::sha256`.

#![cfg(windows)]

use crate::proto::{self, Observed, Report, RunVerdict, Tolerances};
use crate::runenv::EnvBlock;
use crate::sha256;
use std::ffi::c_void;

type Handle = *mut c_void;
const INVALID_HANDLE: Handle = usize::MAX as Handle;
const CURRENT_PROCESS: Handle = usize::MAX as Handle; // (HANDLE)-1 pseudo-handle

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
struct StartupInfoExW {
    si: StartupInfoW,
    attr_list: *mut c_void,
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
const EXTENDED_STARTUPINFO_PRESENT: u32 = 0x0008_0000;
const PROC_THREAD_ATTRIBUTE_HANDLE_LIST: usize = 0x0002_0002;
const CURRENT_THREAD: Handle = (usize::MAX - 1) as Handle; // (HANDLE)-2 pseudo-handle
const STARTF_USESTDHANDLES: u32 = 0x100;
const PAGE_READWRITE: u32 = 0x04;
const FILE_MAP_READ: u32 = 0x0004;
const NORMAL_PRIORITY_CLASS: u32 = 0x20;
const HANDLE_FLAG_INHERIT: u32 = 0x1;
const WAIT_TIMEOUT: u32 = 0x102;
const SECTION_MAP_WRITE: u32 = 0x2;
const SECTION_MAP_READ: u32 = 0x4;
const SECTION_QUERY: u32 = 0x1;

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
    fn CreateProcessW(app: *const u16, cmd: *mut u16, pa: *mut SecurityAttributes, ta: *mut SecurityAttributes, inherit: i32, flags: u32, env: *mut c_void, cwd: *const u16, si: *mut StartupInfoW, pi: *mut ProcessInformation) -> i32;
    fn ResumeThread(thread: Handle) -> u32;
    fn WaitForSingleObject(h: Handle, ms: u32) -> u32;
    fn CloseHandle(h: Handle) -> i32;
    fn CreatePipe(read: *mut Handle, write: *mut Handle, sa: *mut SecurityAttributes, size: u32) -> i32;
    fn ReadFile(h: Handle, buf: *mut u8, n: u32, read: *mut u32, ov: *mut c_void) -> i32;
    fn SetHandleInformation(h: Handle, mask: u32, flags: u32) -> i32;
    fn DuplicateHandle(sp: Handle, sh: Handle, tp: Handle, th: *mut Handle, access: u32, inherit: i32, options: u32) -> i32;
    fn CreateFileMappingW(file: Handle, sa: *mut SecurityAttributes, protect: u32, hi: u32, lo: u32, name: *const u16) -> Handle;
    fn MapViewOfFile(map: Handle, access: u32, hi: u32, lo: u32, bytes: usize) -> *mut c_void;
    fn UnmapViewOfFile(p: *const c_void) -> i32;
    fn QueryPerformanceCounter(c: *mut i64) -> i32;
    fn QueryPerformanceFrequency(c: *mut i64) -> i32;
    fn QueryProcessCycleTime(p: Handle, cycles: *mut u64) -> i32;
    fn GetExitCodeProcess(p: Handle, code: *mut u32) -> i32;
    fn GetLastError() -> u32;
    fn InitializeProcThreadAttributeList(list: *mut c_void, count: u32, flags: u32, size: *mut usize) -> i32;
    fn UpdateProcThreadAttribute(list: *mut c_void, flags: u32, attr: usize, value: *const c_void, size: usize, prev: *mut c_void, ret: *mut usize) -> i32;
    fn DeleteProcThreadAttributeList(list: *mut c_void);
    fn QueryThreadCycleTime(t: Handle, cycles: *mut u64) -> i32;
    fn CreateEventW(sa: *mut SecurityAttributes, manual: i32, initial: i32, name: *const u16) -> Handle;
    fn SetEvent(h: Handle) -> i32;
    fn WaitForMultipleObjects(n: u32, handles: *const Handle, wait_all: i32, ms: u32) -> u32;
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
    c.max(1)
}
fn proc_cycles(p: Handle) -> Option<u64> {
    let mut c = 0u64;
    if unsafe { QueryProcessCycleTime(p, &mut c) } != 0 {
        Some(c)
    } else {
        None
    }
}

/// RAII handle (closed on drop); never closes INVALID_HANDLE or a pseudo-handle.
struct OwnedHandle(Handle);
impl Drop for OwnedHandle {
    fn drop(&mut self) {
        if !self.0.is_null() && self.0 != INVALID_HANDLE {
            unsafe { CloseHandle(self.0) };
        }
    }
}
struct OwnedView(*const c_void);
impl Drop for OwnedView {
    fn drop(&mut self) {
        if !self.0.is_null() {
            unsafe { UnmapViewOfFile(self.0) };
        }
    }
}
/// A PROC_THREAD_ATTRIBUTE_HANDLE_LIST naming exactly the handles the child may inherit. The buffer
/// and the handle array must outlive the CreateProcessW call that uses them.
struct HandleList {
    buf: Vec<usize>,
    handles: Box<[Handle]>,
}
impl HandleList {
    fn new(handles: &[Handle]) -> Result<HandleList, String> {
        unsafe {
            let mut size = 0usize;
            InitializeProcThreadAttributeList(std::ptr::null_mut(), 1, 0, &mut size);
            if size == 0 {
                return Err(format!("InitializeProcThreadAttributeList(size) failed {}", GetLastError()));
            }
            let buf = vec![0usize; size / std::mem::size_of::<usize>() + 1];
            let mut hl = HandleList { buf, handles: handles.to_vec().into_boxed_slice() };
            if InitializeProcThreadAttributeList(hl.buf.as_mut_ptr() as *mut c_void, 1, 0, &mut size) == 0 {
                let e = GetLastError();
                std::mem::forget(hl); // never initialised: nothing to delete
                return Err(format!("InitializeProcThreadAttributeList failed {}", e));
            }
            let (p, n) = (hl.handles.as_ptr() as *const c_void, hl.handles.len() * std::mem::size_of::<Handle>());
            if UpdateProcThreadAttribute(hl.buf.as_mut_ptr() as *mut c_void, 0, PROC_THREAD_ATTRIBUTE_HANDLE_LIST, p, n, std::ptr::null_mut(), std::ptr::null_mut()) == 0 {
                return Err(format!("UpdateProcThreadAttribute(HANDLE_LIST) failed {}", GetLastError()));
            }
            Ok(hl)
        }
    }
    fn ptr(&mut self) -> *mut c_void {
        self.buf.as_mut_ptr() as *mut c_void
    }
}
impl Drop for HandleList {
    fn drop(&mut self) {
        unsafe { DeleteProcThreadAttributeList(self.buf.as_mut_ptr() as *mut c_void) };
    }
}

/// Calibrate the process-cycle rate: QueryThreadCycleTime units per second of one running thread,
/// measured on this (orchestrator) thread against QPC; the best of three ~30 ms spins (preemption can
/// only lower a trial). Used to turn the child's cycle count into cores (`proto::decide_run`); the
/// harness-reported TSC rate is in-process and is never used for it.
pub fn calibrate_cycle_rate() -> u64 {
    let freq = qpf();
    let mut best = 0f64;
    for _ in 0..3 {
        let (mut c0, mut c1) = (0u64, 0u64);
        let q0 = qpc();
        unsafe { QueryThreadCycleTime(CURRENT_THREAD, &mut c0) };
        let mut q1 = qpc();
        while q1 - q0 < freq * 30 / 1000 {
            std::hint::spin_loop();
            q1 = qpc();
        }
        unsafe { QueryThreadCycleTime(CURRENT_THREAD, &mut c1) };
        let secs = (q1 - q0) as f64 / freq as f64;
        if secs > 0.0 && c1 > c0 {
            best = best.max((c1 - c0) as f64 / secs);
        }
    }
    best as u64
}

/// DEV ONLY (review round 3, R1-3): an inheritable, signalled event the `run --dev-canary` demo
/// creates before a run and names to the workload by value. With the handle list in force the child
/// must NOT receive it. Dropping it closes the handle.
pub struct DevCanary(Handle);
impl DevCanary {
    pub fn new() -> Result<DevCanary, String> {
        let mut sa = SecurityAttributes { n_length: std::mem::size_of::<SecurityAttributes>() as u32, lp_security_descriptor: std::ptr::null_mut(), b_inherit_handle: 1 };
        let h = unsafe { CreateEventW(&mut sa, 1, 1, std::ptr::null()) };
        if h.is_null() {
            Err(format!("CreateEvent failed {}", unsafe { GetLastError() }))
        } else {
            Ok(DevCanary(h))
        }
    }
    pub fn value(&self) -> u64 {
        self.0 as usize as u64
    }
}
impl Drop for DevCanary {
    fn drop(&mut self) {
        unsafe { CloseHandle(self.0) };
    }
}

struct OwnedJob(Handle);
impl Drop for OwnedJob {
    fn drop(&mut self) {
        if !self.0.is_null() {
            unsafe {
                TerminateJobObject(self.0, 0);
                CloseHandle(self.0);
            }
        }
    }
}

/// The supervisor-held limits on the job (SANDBOX.md section 2).
#[derive(Clone, Copy, Debug)]
pub struct JobLimits {
    pub active_process_limit: u32,
    pub process_memory_bytes: usize,
    pub affinity_mask: usize,
    pub priority_class: u32,
}
impl Default for JobLimits {
    fn default() -> Self {
        JobLimits { active_process_limit: 1, process_memory_bytes: 8usize << 30, affinity_mask: 0, priority_class: NORMAL_PRIORITY_CLASS }
    }
}

/// Everything one run needs.
pub struct RunSpec<'a> {
    pub harness_exe: &'a str,
    pub workload: &'a str,
    /// Workload parameter (`--param`; 0 = the workload's default).
    pub param: u64,
    pub out_bytes: u64,
    pub salt: u64,
    pub golden_hash: [u64; 4],
    pub limits: JobLimits,
    pub env: &'a EnvBlock,
    /// Fresh, empty scratch directory (already created); becomes the child's cwd. Deleted by the caller.
    pub scratch_dir: &'a str,
    pub tol: Tolerances,
    /// Hard time cap for the whole run (ms). The watchdog terminates the job at it.
    pub time_cap_ms: u32,
    /// Threads the run type declares (proto::Observed::declared_threads).
    pub declared_threads: u32,
    /// From `calibrate_cycle_rate` (once per orchestrator process).
    pub cycle_rate_hz: u64,
    /// The harness's post-t1 per-thread CPU allowances in cycles (`--spin-cycles` for parked
    /// registered threads, `--idle-cycles` for every other thread); 0 = the harness's own provisional
    /// default. Observe mode passes the X4-noise-pilot section 3 ceilings.
    pub spin_cycles: u64,
    pub idle_cycles: u64,
    /// After REPORT the child must exit within this many ms (0 = only the time cap bounds it).
    pub exit_grace_ms: u32,
}

pub struct RunOutcome {
    pub verdict: RunVerdict,
    pub observed: Observed,
    pub delta_o_ns: u64,
    pub raw: Vec<u8>,
}

// Raw pointer carried into the reader thread (the read-only section view). Read only.
struct SendPtr(*const u8);
unsafe impl Send for SendPtr {}
struct SendHandle(Handle);
unsafe impl Send for SendHandle {}

struct ReaderOut {
    raw: Vec<u8>,
    protocol_error: Option<String>,
    hello: Option<Vec<u64>>,
    fail_frame: Option<Vec<u64>>,
    report: Option<Report>,
    census: Option<Vec<u64>>,
    hello_qpc: Option<i64>,
    start_qpc: Option<i64>,
    stop_qpc: Option<i64>,
    cycles_hello: Option<u64>,
    cycles_start: Option<u64>,
    cycles_stop: Option<u64>,
    cycles_report: Option<u64>,
    report_qpc: Option<i64>,
    hash_at_stop: Option<[u64; 4]>,
    outside_at_stop: u64,
    poison_residual_at_stop: Option<u64>,
    saw_stop: bool,
}

/// Launch one run. Returns the full outcome; the verdict is `proto::decide_run` over what the
/// orchestrator itself observed.
pub fn run_once(spec: &RunSpec) -> Result<RunOutcome, String> {
    if !proto::out_bytes_valid(spec.out_bytes) {
        return Err(format!("out_bytes {} is not a non-zero multiple of 64", spec.out_bytes));
    }
    let total = proto::section_bytes(spec.out_bytes) as usize;
    let off = proto::out_offset(spec.out_bytes) as usize;
    let obn = spec.out_bytes as usize;
    unsafe {
        let mut sa = SecurityAttributes {
            n_length: std::mem::size_of::<SecurityAttributes>() as u32,
            lp_security_descriptor: std::ptr::null_mut(),
            b_inherit_handle: 1,
        };
        // pipe: read end stays here, non-inheritable
        let (mut pr, mut pw): (Handle, Handle) = (INVALID_HANDLE, INVALID_HANDLE);
        if CreatePipe(&mut pr, &mut pw, &mut sa, 1 << 20) == 0 {
            return Err(format!("CreatePipe failed {}", GetLastError()));
        }
        let pipe_r = OwnedHandle(pr);
        let pipe_w = OwnedHandle(pw);
        SetHandleInformation(pipe_r.0, HANDLE_FLAG_INHERIT, 0);

        // section: we hold a full-rights, non-inheritable handle and an RO view; the child gets a
        // handle duplicated with only MAP_READ|MAP_WRITE
        let mut na = SecurityAttributes { n_length: sa.n_length, lp_security_descriptor: std::ptr::null_mut(), b_inherit_handle: 0 };
        let section = OwnedHandle(CreateFileMappingW(INVALID_HANDLE, &mut na, PAGE_READWRITE, (total >> 32) as u32, (total & 0xffff_ffff) as u32, std::ptr::null()));
        if section.0.is_null() {
            return Err(format!("CreateFileMapping failed {}", GetLastError()));
        }
        let view = OwnedView(MapViewOfFile(section.0, FILE_MAP_READ, 0, 0, total));
        if view.0.is_null() {
            return Err(format!("MapViewOfFile(RO) failed {}", GetLastError()));
        }
        let mut child_section: Handle = INVALID_HANDLE;
        if DuplicateHandle(CURRENT_PROCESS, section.0, CURRENT_PROCESS, &mut child_section, SECTION_MAP_READ | SECTION_MAP_WRITE | SECTION_QUERY, 1, 0) == 0 {
            return Err(format!("DuplicateHandle(section) failed {}", GetLastError()));
        }
        let child_section = OwnedHandle(child_section);

        // job with the supervisor-held limits
        let job = OwnedJob(CreateJobObjectW(std::ptr::null_mut(), std::ptr::null()));
        if job.0.is_null() {
            return Err(format!("CreateJobObject failed {}", GetLastError()));
        }
        let mut eli = JobExtendedLimitInformation::default();
        eli.basic.limit_flags = JOB_OBJECT_LIMIT_ACTIVE_PROCESS
            | JOB_OBJECT_LIMIT_PROCESS_MEMORY
            | JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            | JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION
            | JOB_OBJECT_LIMIT_PRIORITY_CLASS;
        eli.basic.active_process_limit = spec.limits.active_process_limit;
        eli.basic.priority_class = spec.limits.priority_class;
        eli.process_memory_limit = spec.limits.process_memory_bytes;
        if spec.limits.affinity_mask != 0 {
            eli.basic.limit_flags |= JOB_OBJECT_LIMIT_AFFINITY;
            eli.basic.affinity = spec.limits.affinity_mask;
        }
        if SetInformationJobObject(job.0, JOBOBJECT_EXTENDED_LIMIT_INFORMATION, &mut eli as *mut _ as *mut c_void, std::mem::size_of::<JobExtendedLimitInformation>() as u32) == 0 {
            return Err(format!("SetInformationJobObject failed {}", GetLastError()));
        }

        // the affinity we declare to the harness: the process mask when none is pinned
        let declared_affinity = spec.limits.affinity_mask as u64;
        let cmd = format!(
            "x4harness.exe --pipe {} --section {} --out-bytes {} --salt {} --workload {}{}{}{}{}",
            pipe_w.0 as usize,
            child_section.0 as usize,
            spec.out_bytes,
            spec.salt,
            spec.workload,
            if spec.limits.affinity_mask != 0 { format!(" --affinity {}", spec.limits.affinity_mask) } else { String::new() },
            if spec.param != 0 { format!(" --param {}", spec.param) } else { String::new() },
            if spec.spin_cycles != 0 { format!(" --spin-cycles {}", spec.spin_cycles) } else { String::new() },
            if spec.idle_cycles != 0 { format!(" --idle-cycles {}", spec.idle_cycles) } else { String::new() }
        );
        let mut cmd_w = to_wide(&cmd);
        let app_w = to_wide(spec.harness_exe);
        let cwd_w = to_wide(spec.scratch_dir);
        let mut env_w = spec.env.utf16.clone();
        // exactly two inheritable handles reach the child (review round 3, R1-3)
        let mut hlist = HandleList::new(&[pipe_w.0, child_section.0])?;
        let mut six: StartupInfoExW = std::mem::zeroed();
        six.si.cb = std::mem::size_of::<StartupInfoExW>() as u32;
        six.si.flags = STARTF_USESTDHANDLES;
        six.si.std_output = pipe_w.0;
        six.si.std_error = INVALID_HANDLE;
        six.si.std_input = INVALID_HANDLE;
        six.attr_list = hlist.ptr();
        let mut pi: ProcessInformation = std::mem::zeroed();
        let ok = CreateProcessW(
            app_w.as_ptr(),
            cmd_w.as_mut_ptr(),
            std::ptr::null_mut(),
            std::ptr::null_mut(),
            1,
            CREATE_SUSPENDED | CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT | EXTENDED_STARTUPINFO_PRESENT,
            env_w.as_mut_ptr() as *mut c_void,
            cwd_w.as_ptr(),
            &mut six as *mut StartupInfoExW as *mut StartupInfoW,
            &mut pi,
        );
        drop(hlist);
        if ok == 0 {
            return Err(format!("CreateProcess failed {}", GetLastError()));
        }
        let process = OwnedHandle(pi.process);
        let thread = OwnedHandle(pi.thread);
        let child_pid = pi.process_id as u64;
        if AssignProcessToJobObject(job.0, process.0) == 0 {
            return Err(format!("AssignProcessToJobObject failed {}", GetLastError()));
        }
        let freq = qpf();
        let launch_qpc = qpc();
        let acct_at_assign = read_accounting(job.0);
        ResumeThread(thread.0);
        drop(thread);
        // close our copy of the write end so the reader sees EOF at child exit; the child keeps its own
        drop(pipe_w);

        // REPORT event: set by the reader the moment REPORT is decoded (not inheritable: the handle list
        // names only the pipe and the section)
        let report_event = OwnedHandle(CreateEventW(std::ptr::null_mut(), 1, 0, std::ptr::null()));
        if report_event.0.is_null() {
            return Err(format!("CreateEvent(report) failed {}", GetLastError()));
        }
        let ev_for_reader = SendHandle(report_event.0);
        // reader thread: frames + STOP-time stamping, done where the frame is decoded
        let rp = SendHandle(pipe_r.0);
        let proc_for_reader = SendHandle(process.0);
        let vp = SendPtr(view.0 as *const u8);
        let salt = spec.salt;
        let out_bytes = spec.out_bytes;
        let reader = std::thread::spawn(move || {
            // rebind the whole Send wrappers first, so the closure captures them whole; a bare `rp.0`
            // would make disjoint-capture (edition 2021) grab the inner non-Send raw pointer instead.
            let rp = rp;
            let proc_for_reader = proc_for_reader;
            let vp = vp;
            let ev_for_reader = ev_for_reader;
            let report_ev = ev_for_reader.0;
            let pipe = rp.0;
            let pproc = proc_for_reader.0;
            let base = vp.0;
            let mut framer = proto::Framer::new();
            let mut sv = proto::SeqValidator::new(proto::Exchange::Run);
            let mut o = ReaderOut {
                raw: Vec::new(),
                protocol_error: None,
                hello: None,
                fail_frame: None,
                report: None,
                census: None,
                hello_qpc: None,
                start_qpc: None,
                stop_qpc: None,
                cycles_hello: None,
                cycles_start: None,
                cycles_stop: None,
                cycles_report: None,
                report_qpc: None,
                hash_at_stop: None,
                outside_at_stop: 0,
                poison_residual_at_stop: None,
                saw_stop: false,
            };
            let mut buf = [0u8; 65536];
            'read: loop {
                let mut n = 0u32;
                let r = ReadFile(pipe, buf.as_mut_ptr(), buf.len() as u32, &mut n, std::ptr::null_mut());
                if r == 0 || n == 0 {
                    break;
                }
                o.raw.extend_from_slice(&buf[..n as usize]);
                let frames = match framer.push(&buf[..n as usize]) {
                    Ok(f) => f,
                    Err(e) => {
                        o.protocol_error = Some(e);
                        break;
                    }
                };
                for f in frames {
                    if let Err(e) = sv.accept(&f) {
                        o.protocol_error = Some(e);
                        break 'read;
                    }
                    match f.mtype {
                        proto::T_HELLO => {
                            o.hello_qpc = Some(qpc());
                            o.cycles_hello = proc_cycles(pproc);
                            o.hello = Some(f.vals.clone());
                        }
                        proto::T_START => {
                            o.start_qpc = Some(qpc());
                            o.cycles_start = proc_cycles(pproc);
                        }
                        proto::T_STOP => {
                            o.stop_qpc = Some(qpc());
                            o.cycles_stop = proc_cycles(pproc);
                            o.saw_stop = true;
                            // copy and hash the extent now, and count bytes outside it
                            let section = std::slice::from_raw_parts(base, total);
                            let mut copy = vec![0u8; obn];
                            copy.copy_from_slice(&section[off..off + obn]);
                            o.hash_at_stop = Some(sha256::digest_u64x4(&copy));
                            o.poison_residual_at_stop = Some(proto::poison_residual(&copy, salt));
                            o.outside_at_stop = proto::outside_changed(section, out_bytes);
                        }
                        proto::T_FAIL => o.fail_frame = Some(f.vals.clone()),
                        proto::T_CENSUS => o.census = Some(f.vals.clone()),
                        proto::T_REPORT => {
                            o.report_qpc = Some(qpc());
                            o.cycles_report = proc_cycles(pproc);
                            o.report = Report::from_frame(&f).ok();
                            SetEvent(report_ev);
                        }
                        _ => {}
                    }
                }
            }
            if o.protocol_error.is_none() && framer.pending() != 0 {
                o.protocol_error = Some(format!("{} trailing bytes after the last frame", framer.pending()));
            }
            o
        });

        // watchdog: wait for exit or REPORT up to the time cap; after REPORT, for at most the exit
        // grace; terminate the job if either runs out
        let mut watchdog_fired = false;
        let mut no_exit_after_report = false;
        let mut exit_qpc: Option<i64> = None;
        let elapsed_ms = || ((qpc() - launch_qpc).max(0) as i128 * 1000 / freq as i128) as u64;
        let waits = [process.0, report_event.0];
        let first = WaitForMultipleObjects(2, waits.as_ptr(), 0, spec.time_cap_ms);
        if first == 0 {
            exit_qpc = Some(qpc());
        } else if first == 1 {
            let left_cap = (spec.time_cap_ms as u64).saturating_sub(elapsed_ms());
            let (wait_ms, by_grace) = if spec.exit_grace_ms != 0 && (spec.exit_grace_ms as u64) < left_cap { (spec.exit_grace_ms as u64, true) } else { (left_cap, false) };
            if WaitForSingleObject(process.0, wait_ms as u32) == WAIT_TIMEOUT {
                if by_grace {
                    no_exit_after_report = true;
                } else {
                    watchdog_fired = true;
                }
                TerminateJobObject(job.0, 0xC0DE);
                WaitForSingleObject(process.0, 5000);
            } else {
                exit_qpc = Some(qpc());
            }
        } else {
            watchdog_fired = true;
            TerminateJobObject(job.0, 0xC0DE);
            WaitForSingleObject(process.0, 5000);
        }
        let ro = reader.join().map_err(|_| "reader thread panicked".to_string())?;
        drop(pipe_r);

        // after exit: cycles, exit code, second hash, bytes outside, peak memory, job cpu
        let cycles_exit = proc_cycles(process.0);
        let mut exit = 0u32;
        let exit_code = if GetExitCodeProcess(process.0, &mut exit) != 0 { Some(exit) } else { None };
        let section_slice = std::slice::from_raw_parts(view.0 as *const u8, total);
        let hash_at_exit = Some(proto::extent_hash(section_slice, out_bytes));
        let outside_at_exit = proto::outside_changed(section_slice, out_bytes);
        // job accounting is tick-granular (~15.6 ms): a coarse secondary only; the per-process cycle
        // count sampled at STOP is the real post-STOP check (review R2-2).
        let acct_after = read_accounting(job.0);
        let peak = query_peak_memory(job.0);

        let to_ns = |c: i64| ((c - launch_qpc).max(0) as i128 * 1_000_000_000i128 / freq as i128) as u64;
        let hello_ns = ro.hello_qpc.map(to_ns);
        let start_ns = ro.start_qpc.map(to_ns);
        let stop_ns = ro.stop_qpc.map(to_ns);
        let report_ns = ro.report_qpc.map(to_ns);
        let exit_ns = exit_qpc.map(to_ns);
        let delta_o_ns = match (ro.start_qpc, ro.stop_qpc) {
            (Some(a), Some(b)) if b > a => ((b - a) as i128 * 1_000_000_000i128 / freq as i128) as u64,
            _ => 0,
        };
        // coarse total job CPU (descriptive, not a verdict input)
        let job_cpu_after_stop_100ns = Some((acct_after.total_user_time + acct_after.total_kernel_time) as u64);
        let _ = acct_at_assign;

        let observed = Observed {
            requested_out_bytes: spec.out_bytes,
            salt: spec.salt,
            child_pid,
            declared_affinity,
            declared_priority_class: spec.limits.priority_class as u64,
            golden_hash: spec.golden_hash,
            protocol_error: ro.protocol_error,
            hello: ro.hello,
            fail_frame: ro.fail_frame,
            report: ro.report,
            census: ro.census,
            hello_ns,
            start_ns,
            stop_ns,
            cycles_hello: ro.cycles_hello,
            cycles_start: ro.cycles_start,
            cycles_stop: ro.cycles_stop,
            cycles_exit,
            cycles_report: ro.cycles_report,
            report_ns,
            exit_ns,
            no_exit_after_report,
            job_cpu_after_stop_100ns,
            hash_at_stop: ro.hash_at_stop,
            hash_at_exit,
            outside_changed_at_stop: ro.outside_at_stop,
            outside_changed_at_exit: outside_at_exit,
            poison_residual_at_stop: ro.poison_residual_at_stop,
            exit_code,
            no_exit: watchdog_fired && ro.saw_stop,
            watchdog_fired,
            peak_process_memory: peak,
            declared_threads: spec.declared_threads,
            cycle_rate_hz: spec.cycle_rate_hz,
        };
        let verdict = proto::decide_run(&observed, &spec.tol);
        let raw = ro.raw;
        // OwnedJob/OwnedHandle/OwnedView drop here: terminate the job, close handles, unmap the view
        Ok(RunOutcome { verdict, observed, delta_o_ns, raw })
    }
}

/// One sandbox self-test probe result (SANDBOX.md section 5).
#[derive(Clone, Copy, Debug)]
pub struct ProbeResult {
    pub id: u64,
    pub attempted: u64,
    pub succeeded: u64,
    pub error: u64,
    pub extra: u64,
}

/// Run the harness in --selftest mode inside the Job Object and return its probe results. The job
/// limits are checked (a failed SetInformationJobObject returns Err, so the self-test can never run in
/// an unlimited job and still report in_job=true -- review R1-8).
pub fn run_selftest_in_job(harness_exe: &str, probe_args: &[String], limits: JobLimits) -> Result<Vec<ProbeResult>, String> {
    unsafe {
        let mut sa = SecurityAttributes { n_length: std::mem::size_of::<SecurityAttributes>() as u32, lp_security_descriptor: std::ptr::null_mut(), b_inherit_handle: 1 };
        let (mut pr, mut pw): (Handle, Handle) = (INVALID_HANDLE, INVALID_HANDLE);
        if CreatePipe(&mut pr, &mut pw, &mut sa, 1 << 20) == 0 {
            return Err(format!("CreatePipe failed {}", GetLastError()));
        }
        let pipe_r = OwnedHandle(pr);
        let pipe_w = OwnedHandle(pw);
        SetHandleInformation(pipe_r.0, HANDLE_FLAG_INHERIT, 0);
        let job = OwnedJob(CreateJobObjectW(std::ptr::null_mut(), std::ptr::null()));
        if job.0.is_null() {
            return Err("CreateJobObject failed".into());
        }
        let mut eli = JobExtendedLimitInformation::default();
        eli.basic.limit_flags = JOB_OBJECT_LIMIT_ACTIVE_PROCESS | JOB_OBJECT_LIMIT_PROCESS_MEMORY | JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION | JOB_OBJECT_LIMIT_PRIORITY_CLASS;
        eli.basic.active_process_limit = limits.active_process_limit;
        eli.basic.priority_class = limits.priority_class;
        eli.process_memory_limit = limits.process_memory_bytes;
        if limits.affinity_mask != 0 {
            eli.basic.limit_flags |= JOB_OBJECT_LIMIT_AFFINITY;
            eli.basic.affinity = limits.affinity_mask;
        }
        if SetInformationJobObject(job.0, JOBOBJECT_EXTENDED_LIMIT_INFORMATION, &mut eli as *mut _ as *mut c_void, std::mem::size_of::<JobExtendedLimitInformation>() as u32) == 0 {
            return Err(format!("SetInformationJobObject failed {}", GetLastError()));
        }
        let mut cmd = format!("x4harness.exe --selftest --pipe {}", pipe_w.0 as usize);
        for a in probe_args {
            cmd.push(' ');
            cmd.push_str(a);
        }
        let mut cmd_w = to_wide(&cmd);
        let app_w = to_wide(harness_exe);
        let mut hlist = HandleList::new(&[pipe_w.0])?;
        let mut six: StartupInfoExW = std::mem::zeroed();
        six.si.cb = std::mem::size_of::<StartupInfoExW>() as u32;
        six.si.flags = STARTF_USESTDHANDLES;
        six.si.std_output = pipe_w.0;
        six.si.std_error = INVALID_HANDLE;
        six.si.std_input = INVALID_HANDLE;
        six.attr_list = hlist.ptr();
        let mut pi: ProcessInformation = std::mem::zeroed();
        let flags = CREATE_SUSPENDED | CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT | EXTENDED_STARTUPINFO_PRESENT;
        let created = CreateProcessW(app_w.as_ptr(), cmd_w.as_mut_ptr(), std::ptr::null_mut(), std::ptr::null_mut(), 1, flags, std::ptr::null_mut(), std::ptr::null(), &mut six as *mut StartupInfoExW as *mut StartupInfoW, &mut pi);
        drop(hlist);
        if created == 0 {
            return Err(format!("CreateProcess failed {}", GetLastError()));
        }
        let process = OwnedHandle(pi.process);
        let thread = OwnedHandle(pi.thread);
        if AssignProcessToJobObject(job.0, process.0) == 0 {
            return Err(format!("AssignProcessToJobObject failed {}", GetLastError()));
        }
        ResumeThread(thread.0);
        drop(thread);
        drop(pipe_w);
        let mut raw = Vec::new();
        let mut buf = [0u8; 65536];
        loop {
            let mut n = 0u32;
            if ReadFile(pipe_r.0, buf.as_mut_ptr(), buf.len() as u32, &mut n, std::ptr::null_mut()) == 0 || n == 0 {
                break;
            }
            raw.extend_from_slice(&buf[..n as usize]);
        }
        WaitForSingleObject(process.0, 30000);
        let frames = proto::parse_all(&raw)?;
        proto::validate_sequence(proto::Exchange::SelfTest, &frames)?;
        let mut out = Vec::new();
        if let Some(m) = frames.iter().find(|m| m.mtype == proto::T_PROBES) {
            for e in m.vals.chunks(proto::PROBE_W) {
                if e.len() == proto::PROBE_W {
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
        QueryInformationJobObject(job, JOBOBJECT_BASIC_ACCOUNTING_INFORMATION, &mut acct as *mut _ as *mut c_void, std::mem::size_of::<JobBasicAccountingInformation>() as u32, &mut ret);
    }
    acct
}
fn query_peak_memory(job: Handle) -> u64 {
    let mut eli = JobExtendedLimitInformation::default();
    let mut ret = 0u32;
    unsafe {
        QueryInformationJobObject(job, JOBOBJECT_EXTENDED_LIMIT_INFORMATION, &mut eli as *mut _ as *mut c_void, std::mem::size_of::<JobExtendedLimitInformation>() as u32, &mut ret);
    }
    eli.peak_process_memory_used as u64
}
