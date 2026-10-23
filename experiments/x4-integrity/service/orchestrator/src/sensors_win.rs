//! Read-only hygiene sensors for the noise pilot (X4-noise-pilot section 10; X4 pilot track,
//! 2026-10-23). Every reading goes through a documented, vendor-supported interface; nothing here
//! sets a value, loads a driver or touches hardware below the OS:
//! - per-logical-processor load, effective clock, disk queue and write rate, the modified page list
//!   and ACPI thermal zones: Performance Data Helper counters (pdh.dll, English counter paths);
//! - processes and their CPU: Toolhelp process snapshot + `QueryProcessCycleTime` with
//!   PROCESS_QUERY_LIMITED_INFORMATION (works on protected processes such as MsMpEng);
//! - interactive input: `GetLastInputInfo` (sees only the session this process runs in, so the
//!   reading is marked with whether that is the active console session) and the WTS session list;
//! - the active power scheme: `PowerGetActiveScheme`;
//! - GPU utilisation: NVIDIA's documented `nvidia-smi --query-gpu` (a query; it runs no GPU work);
//! - NVMe temperature and the bus type of a volume: `IOCTL_STORAGE_QUERY_PROPERTY`
//!   (StorageDeviceTemperatureProperty, StorageDeviceProperty) on a handle opened with no access
//!   rights (query only);
//! - processor topology: `GetLogicalProcessorInformationEx`;
//! - machine CPU time: `GetSystemTimes` (the gate's machine load since revision 4; PDH `_Total` is
//!   recorded beside it), this process's own times, priority class, memory priority, elevation and
//!   integrity level (`GetProcessTimes`, `GetPriorityClass`, `GetProcessInformation`,
//!   `GetTokenInformation`).
//! The only process-local change is `pin_own_process` (SetProcessAffinityMask on this orchestrator,
//! the "reserved LP" of 06 section 6.7); it is not a system setting.
//!
//! Revision 4 (review 2026-10-23): PDH reports an idle LP's `% Processor Time` with the status
//! PDH_CALC_NEGATIVE_VALUE (idle time over the interval exceeded the time base by clock-tick
//! quantisation) [M: 26-32 of 32 LPs per read]; such an instance is kept as 0.0 and counted, never
//! dropped. Process snapshots carry the parent pid and the creation time.

#![cfg(windows)]

use crate::hygiene::{norm_image, ProcSample};
use std::ffi::c_void;

type Handle = *mut c_void;
const INVALID_HANDLE: Handle = usize::MAX as Handle;

#[repr(C)]
#[derive(Clone, Copy)]
struct PdhFmtValue {
    status: u32,
    _pad: u32,
    value: f64,
}
#[repr(C)]
struct PdhFmtItem {
    name: *mut u16,
    value: PdhFmtValue,
}
#[repr(C)]
struct ProcessEntry32W {
    size: u32,
    usage: u32,
    pid: u32,
    heap_id: usize,
    module_id: u32,
    threads: u32,
    parent: u32,
    pri: i32,
    flags: u32,
    exe: [u16; 260],
}
#[repr(C)]
struct LastInputInfo {
    size: u32,
    time: u32,
}
#[repr(C)]
struct WtsSessionInfoW {
    id: u32,
    station: *mut u16,
    state: u32,
}
#[repr(C)]
struct Guid {
    d1: u32,
    d2: u16,
    d3: u16,
    d4: [u8; 8],
}
#[repr(C)]
struct StoragePropertyQuery {
    property_id: u32,
    query_type: u32,
    additional: [u8; 4],
}

const PDH_FMT_DOUBLE: u32 = 0x0000_0200;
const PDH_FMT_NOCAP100: u32 = 0x0000_8000;
const PDH_MORE_DATA: u32 = 0x8000_07D2;
const PDH_CSTATUS_NEW_DATA: u32 = 0x1;
const PDH_CALC_NEGATIVE_VALUE: u32 = 0x8000_07D8;
const TH32CS_SNAPPROCESS: u32 = 0x2;
const PROCESS_QUERY_LIMITED_INFORMATION: u32 = 0x1000;
const IOCTL_STORAGE_QUERY_PROPERTY: u32 = 0x002D_1400;
const IOCTL_STORAGE_GET_DEVICE_NUMBER: u32 = 0x002D_1080;
const STORAGE_DEVICE_PROPERTY: u32 = 0;
const STORAGE_DEVICE_TEMPERATURE_PROPERTY: u32 = 52;
const FILE_SHARE_READ_WRITE: u32 = 0x3;
const OPEN_EXISTING: u32 = 3;
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

#[link(name = "pdh")]
extern "system" {
    fn PdhOpenQueryW(src: *const u16, user: usize, q: *mut isize) -> u32;
    fn PdhAddEnglishCounterW(q: isize, path: *const u16, user: usize, c: *mut isize) -> u32;
    fn PdhCollectQueryData(q: isize) -> u32;
    fn PdhGetFormattedCounterArrayW(c: isize, fmt: u32, size: *mut u32, count: *mut u32, items: *mut PdhFmtItem) -> u32;
    fn PdhGetFormattedCounterValue(c: isize, fmt: u32, typ: *mut u32, v: *mut PdhFmtValue) -> u32;
    fn PdhCloseQuery(q: isize) -> u32;
}
#[link(name = "kernel32")]
extern "system" {
    fn CreateToolhelp32Snapshot(flags: u32, pid: u32) -> Handle;
    fn Process32FirstW(snap: Handle, e: *mut ProcessEntry32W) -> i32;
    fn Process32NextW(snap: Handle, e: *mut ProcessEntry32W) -> i32;
    fn OpenProcess(access: u32, inherit: i32, pid: u32) -> Handle;
    fn QueryProcessCycleTime(p: Handle, c: *mut u64) -> i32;
    fn CloseHandle(h: Handle) -> i32;
    fn GetCurrentProcessId() -> u32;
    fn ProcessIdToSessionId(pid: u32, sid: *mut u32) -> i32;
    fn WTSGetActiveConsoleSessionId() -> u32;
    fn LocalFree(p: *mut c_void) -> *mut c_void;
    fn CreateFileW(name: *const u16, access: u32, share: u32, sa: *mut c_void, disp: u32, flags: u32, tmpl: Handle) -> Handle;
    fn DeviceIoControl(h: Handle, code: u32, inb: *const c_void, inl: u32, outb: *mut c_void, outl: u32, ret: *mut u32, ov: *mut c_void) -> i32;
    fn GetLogicalProcessorInformationEx(rel: u32, buf: *mut u8, len: *mut u32) -> i32;
    fn SetProcessAffinityMask(p: Handle, mask: usize) -> i32;
    fn GetLastError() -> u32;
    fn GetSystemTimes(idle: *mut u64, kernel: *mut u64, user: *mut u64) -> i32;
    fn GetProcessTimes(p: Handle, created: *mut u64, exited: *mut u64, kernel: *mut u64, user: *mut u64) -> i32;
    fn GetCurrentProcess() -> Handle;
    fn GetPriorityClass(p: Handle) -> u32;
    fn GetProcessInformation(p: Handle, class: u32, info: *mut c_void, size: u32) -> i32;
}
#[link(name = "advapi32")]
extern "system" {
    fn OpenProcessToken(p: Handle, access: u32, token: *mut Handle) -> i32;
    fn GetTokenInformation(t: Handle, class: u32, info: *mut c_void, len: u32, ret: *mut u32) -> i32;
    fn GetSidSubAuthorityCount(sid: *mut c_void) -> *mut u8;
    fn GetSidSubAuthority(sid: *mut c_void, n: u32) -> *mut u32;
}
#[link(name = "user32")]
extern "system" {
    fn GetLastInputInfo(i: *mut LastInputInfo) -> i32;
}
#[link(name = "wtsapi32")]
extern "system" {
    fn WTSEnumerateSessionsW(server: Handle, reserved: u32, version: u32, info: *mut *mut WtsSessionInfoW, count: *mut u32) -> i32;
    fn WTSFreeMemory(p: *mut c_void);
}
#[link(name = "powrprof")]
extern "system" {
    fn PowerGetActiveScheme(root: Handle, guid: *mut *mut Guid) -> u32;
}

fn wide(s: &str) -> Vec<u16> {
    s.encode_utf16().chain(std::iter::once(0)).collect()
}
unsafe fn from_wide(p: *const u16) -> String {
    if p.is_null() {
        return String::new();
    }
    let mut n = 0usize;
    while *p.add(n) != 0 {
        n += 1;
    }
    String::from_utf16_lossy(std::slice::from_raw_parts(p, n))
}

// ------------------------------------------------------------------------------------------- PDH

/// One PDH query with named counters; a counter that cannot be added is absent (None on read).
pub struct Pdh {
    q: isize,
    counters: Vec<(&'static str, Option<isize>)>,
}

impl Pdh {
    pub fn open(paths: &[&'static str]) -> Result<Pdh, String> {
        let mut q = 0isize;
        let rc = unsafe { PdhOpenQueryW(std::ptr::null(), 0, &mut q) };
        if rc != 0 {
            return Err(format!("PdhOpenQuery failed {:#x}", rc));
        }
        let mut counters = Vec::new();
        for p in paths {
            let mut c = 0isize;
            let w = wide(p);
            let ok = unsafe { PdhAddEnglishCounterW(q, w.as_ptr(), 0, &mut c) } == 0;
            counters.push((*p, if ok { Some(c) } else { None }));
        }
        Ok(Pdh { q, counters })
    }
    pub fn collect(&self) -> bool {
        unsafe { PdhCollectQueryData(self.q) == 0 }
    }
    fn handle(&self, path: &str) -> Option<isize> {
        self.counters.iter().find(|c| c.0 == path).and_then(|c| c.1)
    }
    /// A wildcard counter's instances as (instance name, value). Instances with an invalid status are
    /// dropped, except PDH_CALC_NEGATIVE_VALUE when `clamp_negative` (a fully idle LP's `% Processor
    /// Time`): kept as 0.0. The second value counts the clamped instances.
    pub fn array_clamped(&self, path: &str, clamp_negative: bool) -> Option<(Vec<(String, f64)>, usize, Vec<(String, u32)>)> {
        let c = self.handle(path)?;
        unsafe {
            let (mut size, mut count) = (0u32, 0u32);
            let rc = PdhGetFormattedCounterArrayW(c, PDH_FMT_DOUBLE | PDH_FMT_NOCAP100, &mut size, &mut count, std::ptr::null_mut());
            if rc != PDH_MORE_DATA || size == 0 {
                return None;
            }
            let mut buf: Vec<u64> = vec![0; (size as usize + 7) / 8 + 1];
            let items = buf.as_mut_ptr() as *mut PdhFmtItem;
            if PdhGetFormattedCounterArrayW(c, PDH_FMT_DOUBLE | PDH_FMT_NOCAP100, &mut size, &mut count, items) != 0 {
                return None;
            }
            let mut v = Vec::new();
            let mut clamped = 0usize;
            let mut dropped: Vec<(String, u32)> = Vec::new();
            for i in 0..count as usize {
                let it = &*items.add(i);
                match it.value.status {
                    0 | PDH_CSTATUS_NEW_DATA => v.push((from_wide(it.name), it.value.value)),
                    PDH_CALC_NEGATIVE_VALUE if clamp_negative => {
                        v.push((from_wide(it.name), 0.0));
                        clamped += 1;
                    }
                    st => dropped.push((from_wide(it.name), st)),
                }
            }
            Some((v, clamped, dropped))
        }
    }
    pub fn array(&self, path: &str) -> Option<Vec<(String, f64)>> {
        self.array_clamped(path, false).map(|x| x.0)
    }
    pub fn value(&self, path: &str) -> Option<f64> {
        let c = self.handle(path)?;
        let mut t = 0u32;
        let mut v = PdhFmtValue { status: 0, _pad: 0, value: 0.0 };
        let rc = unsafe { PdhGetFormattedCounterValue(c, PDH_FMT_DOUBLE | PDH_FMT_NOCAP100, &mut t, &mut v) };
        if rc == 0 && v.status == 0 {
            Some(v.value)
        } else {
            None
        }
    }
}
impl Drop for Pdh {
    fn drop(&mut self) {
        unsafe { PdhCloseQuery(self.q) };
    }
}

pub const C_PROC_TIME: &str = "\\Processor(*)\\% Processor Time";
pub const C_PERF: &str = "\\Processor Information(*)\\% Processor Performance";
pub const C_FREQ: &str = "\\Processor Information(*)\\Processor Frequency";
pub const C_THERMAL: &str = "\\Thermal Zone Information(*)\\Temperature";
pub const C_DISK_QUEUE: &str = "\\PhysicalDisk(*)\\Current Disk Queue Length";
pub const C_DISK_WRITE: &str = "\\PhysicalDisk(*)\\Disk Write Bytes/sec";
pub const C_MODIFIED: &str = "\\Memory\\Modified Page List Bytes";

/// A load sample over a window: machine-wide % (the `_Total` instance), per-LP %, the effective clock
/// of each LP in MHz (Processor Frequency x % Processor Performance / 100) and ACPI thermal zones (K).
#[derive(Clone, Debug, Default)]
pub struct LoadSample {
    /// Machine load over the window from `GetSystemTimes`: 1 - d(idle) / (d(kernel) + d(user)), in %
    /// (the gate's reading since revision 4).
    pub sys_total_pct: Option<f64>,
    /// PDH `_Total` of `% Processor Time` over the same window (recorded beside it).
    pub total_pct: Option<f64>,
    pub per_lp_pct: Vec<(String, f64)>,
    /// Per-LP instances PDH reported as PDH_CALC_NEGATIVE_VALUE, kept as 0.0.
    pub clamped_lps: usize,
    /// Instances dropped for any other status: (instance, PDH status), recorded.
    pub dropped: Vec<(String, u32)>,
    pub eff_mhz: Vec<(String, f64)>,
    pub thermal_k: Vec<(String, f64)>,
}

/// (idle, kernel, user) system times in 100 ns, summed over every LP (kernel includes idle).
pub fn system_times() -> Option<(u64, u64, u64)> {
    let (mut i, mut k, mut u) = (0u64, 0u64, 0u64);
    if unsafe { GetSystemTimes(&mut i, &mut k, &mut u) } != 0 {
        Some((i, k, u))
    } else {
        None
    }
}
/// Busy % between two `system_times` readings.
pub fn busy_pct(a: (u64, u64, u64), b: (u64, u64, u64)) -> Option<f64> {
    let di = b.0.checked_sub(a.0)? as f64;
    let dt = (b.1.checked_sub(a.1)? + b.2.checked_sub(a.2)?) as f64;
    if dt <= 0.0 {
        None
    } else {
        Some(((1.0 - di / dt) * 100.0).clamp(0.0, 100.0))
    }
}
/// Busy time (100 ns, summed over LPs) between two `system_times` readings.
pub fn busy_100ns(a: (u64, u64, u64), b: (u64, u64, u64)) -> Option<u64> {
    let di = b.0.checked_sub(a.0)?;
    let dt = b.1.checked_sub(a.1)? + b.2.checked_sub(a.2)?;
    Some(dt.saturating_sub(di))
}
/// This process's own kernel + user time (100 ns).
pub fn own_cpu_100ns() -> Option<u64> {
    let (mut c, mut e, mut k, mut u) = (0u64, 0u64, 0u64, 0u64);
    if unsafe { GetProcessTimes(GetCurrentProcess(), &mut c, &mut e, &mut k, &mut u) } != 0 {
        Some(k + u)
    } else {
        None
    }
}

pub struct Sensors {
    load: Pdh,
    disk: Pdh,
    /// A separate query bracketing each run (per-LP load and effective clock over [launch, exit]).
    run: Pdh,
}

impl Sensors {
    pub fn open() -> Result<Sensors, String> {
        Ok(Sensors {
            load: Pdh::open(&[C_PROC_TIME, C_PERF, C_FREQ, C_THERMAL])?,
            disk: Pdh::open(&[C_DISK_QUEUE, C_DISK_WRITE, C_MODIFIED])?,
            run: Pdh::open(&[C_PROC_TIME, C_PERF, C_FREQ])?,
        })
    }
    /// Open the run bracket (a PDH collect just before the launch).
    pub fn run_bracket_open(&self) {
        self.run.collect();
    }
    /// Close the run bracket (just after exit): per-LP load and effective clock over the run.
    pub fn run_bracket_close(&self) -> LoadSample {
        if !self.run.collect() {
            return LoadSample::default();
        }
        Self::read_load(&self.run, None)
    }
    fn read_load(q: &Pdh, sys: Option<f64>) -> LoadSample {
        let (all, clamped, dropped) = q.array_clamped(C_PROC_TIME, true).unwrap_or_default();
        let total = all.iter().find(|x| x.0 == "_Total").map(|x| x.1);
        let mut per: Vec<(String, f64)> = all.into_iter().filter(|x| x.0 != "_Total").collect();
        per.sort_by_key(|x| x.0.parse::<u32>().unwrap_or(u32::MAX));
        let perf = q.array(C_PERF).unwrap_or_default();
        let freq = q.array(C_FREQ).unwrap_or_default();
        let mut eff: Vec<(String, f64)> = Vec::new();
        for (name, pf) in &perf {
            if name.contains("_Total") {
                continue;
            }
            if let Some(f) = freq.iter().find(|x| &x.0 == name) {
                eff.push((name.clone(), f.1 * pf / 100.0));
            }
        }
        LoadSample { sys_total_pct: sys, total_pct: total, per_lp_pct: per, clamped_lps: clamped, dropped, eff_mhz: eff, thermal_k: Vec::new() }
    }
    pub fn load_sample(&self, window_ms: u64) -> LoadSample {
        let s0 = system_times();
        self.load.collect();
        std::thread::sleep(std::time::Duration::from_millis(window_ms));
        let s1 = system_times();
        let sys = match (s0, s1) {
            (Some(a), Some(b)) => busy_pct(a, b),
            _ => None,
        };
        if !self.load.collect() {
            return LoadSample { sys_total_pct: sys, ..LoadSample::default() };
        }
        let mut l = Self::read_load(&self.load, sys);
        l.thermal_k = self.load.array(C_THERMAL).unwrap_or_default();
        l
    }
    /// (current disk queue summed over disks, write bytes/s over the window, modified page list bytes)
    pub fn disk_sample(&self, window_ms: u64) -> (Option<f64>, Option<f64>, Option<f64>) {
        self.disk.collect();
        std::thread::sleep(std::time::Duration::from_millis(window_ms));
        if !self.disk.collect() {
            return (None, None, None);
        }
        let pick = |v: Option<Vec<(String, f64)>>| v.and_then(|a| a.iter().find(|x| x.0 == "_Total").map(|x| x.1));
        (pick(self.disk.array(C_DISK_QUEUE)), pick(self.disk.array(C_DISK_WRITE)), self.disk.value(C_MODIFIED))
    }
}

// ------------------------------------------------------------------------------------- processes

/// Every process (cycles and creation time for all).
pub fn processes() -> Vec<ProcSample> {
    processes_where(|_| true)
}

/// A process snapshot; cycles and creation time are queried only for images `want` accepts (the
/// others are omitted), which keeps the 250-ms poller cheap.
pub fn processes_where(want: impl Fn(&str) -> bool) -> Vec<ProcSample> {
    let mut v = Vec::new();
    unsafe {
        let snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
        if snap == INVALID_HANDLE || snap.is_null() {
            return v;
        }
        let mut e: ProcessEntry32W = std::mem::zeroed();
        e.size = std::mem::size_of::<ProcessEntry32W>() as u32;
        let mut ok = Process32FirstW(snap, &mut e);
        while ok != 0 {
            let name = String::from_utf16_lossy(&e.exe[..e.exe.iter().position(|&c| c == 0).unwrap_or(260)]);
            let image = norm_image(&name);
            if want(&image) {
                let (mut cycles, mut created) = (None, None);
                if e.pid != 0 {
                    let h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, e.pid);
                    if !h.is_null() {
                        let mut c = 0u64;
                        if QueryProcessCycleTime(h, &mut c) != 0 {
                            cycles = Some(c);
                        }
                        let (mut cr, mut ex, mut k, mut u) = (0u64, 0u64, 0u64, 0u64);
                        if GetProcessTimes(h, &mut cr, &mut ex, &mut k, &mut u) != 0 {
                            created = Some(cr);
                        }
                        CloseHandle(h);
                    }
                } else {
                    cycles = Some(0);
                }
                v.push(ProcSample { pid: e.pid, image, cycles, parent: e.parent, created });
            }
            ok = Process32NextW(snap, &mut e);
        }
        CloseHandle(snap);
    }
    v
}

/// This process's priority class, memory priority (MEMORY_PRIORITY_NORMAL = 5), token elevation and
/// integrity-level RID (0x2000 medium, 0x3000 high), each None when unreadable (record section 10:
/// a PILOT night needs NORMAL_PRIORITY_CLASS and MEMORY_PRIORITY_NORMAL).
#[derive(Clone, Copy, Debug, Default)]
pub struct OwnProcess {
    pub priority_class: Option<u32>,
    pub memory_priority: Option<u32>,
    pub elevated: Option<bool>,
    pub integrity_rid: Option<u32>,
}
pub fn own_process() -> OwnProcess {
    unsafe {
        let me = GetCurrentProcess();
        let pc = GetPriorityClass(me);
        let mut mp = 0u32;
        let memory_priority = if GetProcessInformation(me, 0, &mut mp as *mut u32 as *mut c_void, 4) != 0 { Some(mp) } else { None };
        let mut tok: Handle = std::ptr::null_mut();
        let (mut elevated, mut integrity_rid) = (None, None);
        if OpenProcessToken(me, 0x0008, &mut tok) != 0 {
            let mut el = 0u32;
            let mut ret = 0u32;
            if GetTokenInformation(tok, 20, &mut el as *mut u32 as *mut c_void, 4, &mut ret) != 0 {
                elevated = Some(el != 0);
            }
            let mut buf = [0u64; 16];
            if GetTokenInformation(tok, 25, buf.as_mut_ptr() as *mut c_void, 128, &mut ret) != 0 {
                let sid = buf[0] as usize as *mut c_void;
                let n = *GetSidSubAuthorityCount(sid);
                if n > 0 {
                    integrity_rid = Some(*GetSidSubAuthority(sid, n as u32 - 1));
                }
            }
            CloseHandle(tok);
        }
        OwnProcess { priority_class: if pc != 0 { Some(pc) } else { None }, memory_priority, elevated, integrity_rid }
    }
}

pub fn own_pid() -> u32 {
    unsafe { GetCurrentProcessId() }
}

// ------------------------------------------------------------------------------ input, sessions

/// (last-input tick of this process's session, whether this process runs in the active console
/// session). GetLastInputInfo reports only the calling session; over SSH that is not the console.
pub fn last_input() -> (Option<u32>, Option<bool>) {
    unsafe {
        let mut li = LastInputInfo { size: 8, time: 0 };
        let tick = if GetLastInputInfo(&mut li) != 0 { Some(li.time) } else { None };
        let mut sid = 0u32;
        let console = WTSGetActiveConsoleSessionId();
        let in_console = if ProcessIdToSessionId(GetCurrentProcessId(), &mut sid) != 0 && console != 0xFFFF_FFFF { Some(sid == console) } else { None };
        (tick, in_console)
    }
}

pub fn wts_sessions() -> Option<Vec<(u32, String, u32)>> {
    unsafe {
        let mut p: *mut WtsSessionInfoW = std::ptr::null_mut();
        let mut n = 0u32;
        if WTSEnumerateSessionsW(std::ptr::null_mut(), 0, 1, &mut p, &mut n) == 0 {
            return None;
        }
        let mut v = Vec::new();
        for i in 0..n as usize {
            let s = &*p.add(i);
            v.push((s.id, from_wide(s.station), s.state));
        }
        WTSFreeMemory(p as *mut c_void);
        v.sort();
        Some(v)
    }
}

// ----------------------------------------------------------------------------------- power, GPU

pub fn active_scheme_guid() -> Option<String> {
    unsafe {
        let mut g: *mut Guid = std::ptr::null_mut();
        if PowerGetActiveScheme(std::ptr::null_mut(), &mut g) != 0 || g.is_null() {
            return None;
        }
        let x = &*g;
        let s = format!(
            "{:08x}-{:04x}-{:04x}-{:02x}{:02x}-{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}",
            x.d1, x.d2, x.d3, x.d4[0], x.d4[1], x.d4[2], x.d4[3], x.d4[4], x.d4[5], x.d4[6], x.d4[7]
        );
        LocalFree(g as *mut c_void);
        Some(s)
    }
}

/// GPU utilisation (%) through NVIDIA's documented query CLI; the largest over all GPUs.
pub fn gpu_util() -> Result<f64, String> {
    use std::os::windows::process::CommandExt;
    let out = std::process::Command::new("nvidia-smi")
        .args(["--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"])
        .env("CUDA_VISIBLE_DEVICES", "-1")
        .creation_flags(CREATE_NO_WINDOW)
        .output()
        .map_err(|e| format!("nvidia-smi not runnable: {}", e))?;
    if !out.status.success() {
        return Err(format!("nvidia-smi exit {:?}", out.status.code()));
    }
    let mut best: Option<f64> = None;
    for l in String::from_utf8_lossy(&out.stdout).lines() {
        if let Ok(x) = l.trim().parse::<f64>() {
            best = Some(best.map_or(x, |b: f64| b.max(x)));
        }
    }
    best.ok_or_else(|| "nvidia-smi printed no utilisation".into())
}

// ------------------------------------------------------------------------------------- storage

fn open_query(path: &str) -> Result<Handle, String> {
    let w = wide(path);
    let h = unsafe { CreateFileW(w.as_ptr(), 0, FILE_SHARE_READ_WRITE, std::ptr::null_mut(), OPEN_EXISTING, 0, std::ptr::null_mut()) };
    if h == INVALID_HANDLE || h.is_null() {
        Err(format!("open {} (query only) failed {}", path, unsafe { GetLastError() }))
    } else {
        Ok(h)
    }
}
fn query_property(h: Handle, id: u32, out: &mut [u8]) -> Result<u32, String> {
    let q = StoragePropertyQuery { property_id: id, query_type: 0, additional: [0; 4] };
    let mut ret = 0u32;
    let ok = unsafe {
        DeviceIoControl(h, IOCTL_STORAGE_QUERY_PROPERTY, &q as *const _ as *const c_void, std::mem::size_of::<StoragePropertyQuery>() as u32, out.as_mut_ptr() as *mut c_void, out.len() as u32, &mut ret, std::ptr::null_mut())
    };
    if ok == 0 {
        Err(format!("IOCTL_STORAGE_QUERY_PROPERTY({}) failed {}", id, unsafe { GetLastError() }))
    } else {
        Ok(ret)
    }
}
fn physical_drive_of(volume: char) -> Result<u32, String> {
    let h = open_query(&format!("\\\\.\\{}:", volume))?;
    let mut buf = [0u32; 3];
    let mut ret = 0u32;
    let ok = unsafe { DeviceIoControl(h, IOCTL_STORAGE_GET_DEVICE_NUMBER, std::ptr::null(), 0, buf.as_mut_ptr() as *mut c_void, 12, &mut ret, std::ptr::null_mut()) };
    unsafe { CloseHandle(h) };
    if ok == 0 {
        return Err(format!("IOCTL_STORAGE_GET_DEVICE_NUMBER failed {}", unsafe { GetLastError() }));
    }
    Ok(buf[1])
}

/// STORAGE_BUS_TYPE of the disk behind a volume (7 = USB, 17 = NVMe).
pub fn volume_bus_type(volume: char) -> Result<u32, String> {
    let h = open_query(&format!("\\\\.\\{}:", volume))?;
    let mut buf = [0u8; 1024];
    let r = query_property(h, STORAGE_DEVICE_PROPERTY, &mut buf);
    unsafe { CloseHandle(h) };
    let n = r?;
    if n < 32 {
        return Err("short STORAGE_DEVICE_DESCRIPTOR".into());
    }
    Ok(u32::from_le_bytes([buf[28], buf[29], buf[30], buf[31]]))
}
pub fn bus_type_name(t: u32) -> &'static str {
    match t {
        7 => "USB",
        11 => "SATA",
        17 => "NVMe",
        _ => "other",
    }
}

/// The temperature (degrees C) the storage stack reports for the disk behind a volume
/// (StorageDeviceTemperatureProperty: for NVMe the SMART composite temperature).
pub fn nvme_temp_c(volume: char) -> Result<f64, String> {
    let disk = physical_drive_of(volume)?;
    let h = open_query(&format!("\\\\.\\PhysicalDrive{}", disk))?;
    let mut buf = [0u8; 512];
    let r = query_property(h, STORAGE_DEVICE_TEMPERATURE_PROPERTY, &mut buf);
    unsafe { CloseHandle(h) };
    let n = r?;
    let count = u16::from_le_bytes([buf[12], buf[13]]);
    if n < 40 || count == 0 {
        return Err(format!("no temperature info ({} bytes, {} entries)", n, count));
    }
    Ok(i16::from_le_bytes([buf[26], buf[27]]) as f64)
}

// ------------------------------------------------------------------------------------- topology

/// Physical cores (each an LP mask) and L3 caches (each an LP mask) of processor group 0, sorted by
/// lowest LP.
#[derive(Clone, Debug, Default)]
pub struct Topology {
    pub cores: Vec<u64>,
    pub l3: Vec<u64>,
}

pub fn topology() -> Result<Topology, String> {
    unsafe {
        let mut len = 0u32;
        GetLogicalProcessorInformationEx(0xFFFF, std::ptr::null_mut(), &mut len);
        if len == 0 {
            return Err(format!("GetLogicalProcessorInformationEx(size) failed {}", GetLastError()));
        }
        let mut buf = vec![0u8; len as usize];
        if GetLogicalProcessorInformationEx(0xFFFF, buf.as_mut_ptr(), &mut len) == 0 {
            return Err(format!("GetLogicalProcessorInformationEx failed {}", GetLastError()));
        }
        let rd32 = |o: usize| u32::from_le_bytes([buf[o], buf[o + 1], buf[o + 2], buf[o + 3]]);
        let rd16 = |o: usize| u16::from_le_bytes([buf[o], buf[o + 1]]);
        let rd64 = |o: usize| u64::from_le_bytes(buf[o..o + 8].try_into().unwrap());
        let mut t = Topology::default();
        let mut off = 0usize;
        while off + 8 <= len as usize {
            let (rel, size) = (rd32(off), rd32(off + 4) as usize);
            if size == 0 {
                break;
            }
            match rel {
                0 => {
                    // PROCESSOR_RELATIONSHIP: GroupCount at +30, GroupMask[0] at +32 (Mask, Group)
                    if rd16(off + 30) >= 1 && rd16(off + 40) == 0 {
                        t.cores.push(rd64(off + 32));
                    }
                }
                2 => {
                    // CACHE_RELATIONSHIP: Level at +8, Type at +16, GroupMask at +40
                    if buf[off + 8] == 3 && rd16(off + 48) == 0 {
                        t.l3.push(rd64(off + 40));
                    }
                }
                _ => {}
            }
            off += size;
        }
        t.cores.sort_by_key(|m| m.trailing_zeros());
        t.l3.sort_by_key(|m| m.trailing_zeros());
        Ok(t)
    }
}

impl Topology {
    /// The record's mechanical choices (X4-noise-pilot section 3): the microbenchmark LP `p` = the
    /// first LP of the second physical core of CCD0 (the L3 group holding the lowest LP); the
    /// orchestrator's reserved LP = the first LP of the last physical core of CCD1; the end-to-end
    /// mask under C01's default = every LP except the reserved one.
    pub fn pilot_masks(&self) -> Option<(u64, u64, u64)> {
        let ccd0 = *self.l3.first()?;
        let ccd1 = *self.l3.get(1)?;
        let cores0: Vec<u64> = self.cores.iter().copied().filter(|c| c & ccd0 == *c).collect();
        let cores1: Vec<u64> = self.cores.iter().copied().filter(|c| c & ccd1 == *c).collect();
        let p = 1u64 << cores0.get(1)?.trailing_zeros();
        let reserved = 1u64 << cores1.last()?.trailing_zeros();
        let all = self.cores.iter().fold(0u64, |a, c| a | c);
        Some((p, reserved, all & !reserved))
    }
}

/// Pin this orchestrator process to a mask (process-local; children in a job get the job's mask).
pub fn pin_own_process(mask: u64) -> Result<(), String> {
    let ok = unsafe { SetProcessAffinityMask(usize::MAX as Handle, mask as usize) };
    if ok == 0 {
        Err(format!("SetProcessAffinityMask({:#x}) failed {}", mask, unsafe { GetLastError() }))
    } else {
        Ok(())
    }
}
