"""Per-call sandbox for untrusted agent code on Windows (X1 DESIGN 11.2, X1-amendment-1 2.3 item 5).

Documented Win32 interfaces only (no installer, no driver, no system or security setting changed):

- an **AppContainer** process (CreateProcessW with PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES), by
  default a *less privileged* AppContainer (PROC_THREAD_ATTRIBUTE_ALL_APPLICATION_PACKAGES_POLICY,
  opt-out), with **no network capability**. Each sandbox registers its own AppContainer profile
  (CreateAppContainerProfile, name `x1iso.<label>.<random>`), because an unregistered, derive-only SID
  does not launch (CreateProcessW fails with ERROR_FILE_NOT_FOUND [M, laptop, 2026-10-23]). The
  profile is a per-user registration in HKCU plus a storage folder,
  %LOCALAPPDATA%\\Packages\\<name>\\, that the container's SID can write (LPAC included [M]). Both exist
  only for the sandbox's lifetime: `close()` calls DeleteAppContainerProfile, which removes the
  registration and the folder [M]. While the sandbox lives, the folder counts against the disk cap
  (below), so writes there are bounded like writes to `out/`.
  An AppContainer process can open a file only if the file's DACL grants its AppContainer SID, one of
  its capability SIDs, or (for a non-LPAC container) ALL APPLICATION PACKAGES; it runs at Low
  integrity, so it cannot write to a Medium-labelled object even where a DACL would allow it.
  Without the internetClient / privateNetworkClientServer capabilities it has no network: under LPAC
  Winsock does not even initialise (WSAStartup returns 10107 [M]); a non-LPAC container's connect is
  refused (WSAEACCES, 10013 [M]); loopback is isolated for AppContainers unless a loopback exemption (a
  system setting, never made here) exists. That isolation is enforced by Windows' own filtering
  platform [inference], so the negative-test suite re-measures it on every host it runs on.
- one **custom capability SID** per toolchain image (DeriveCapabilitySidsFromName), granted read and
  execute on the image directory only. Every sandbox carries it, so the toolchain is readable;
  nothing else on the disk grants it.
- a **Job Object** per sandbox: a job user-mode CPU-time limit, a job memory limit, an active
  process limit, a hard CPU-rate cap, UI restrictions (no clipboard, desktop, global atoms, system
  parameters, other processes' USER handles), kill-on-job-close, die-on-unhandled-exception, and no
  breakaway. A wall-clock backstop terminates the job.
- only the handles listed in PROC_THREAD_ATTRIBUTE_HANDLE_LIST are inherited (the three pipe ends
  created for this call); the environment block is built from an allowlist (`SANDBOX_ENV_NAMES`),
  never inherited, so no account, session or host variable of the runner reaches sandboxed code.
- a watchdog polls the job's CPU time (user + kernel) and the bytes in the sandbox's writable places
  (`out/` and the profile's storage folder), and terminates the job above either cap; stdout and
  stderr are read through pipes and truncated (the rest is drained and discarded).

The per-call directory layout is `<call>/in` (read-only to the container: the container SID gets
read and execute, the directory keeps its Medium label) and `<call>/out` (the container SID gets
modify, the directory is labelled Low). Nothing else is granted to the call's SID, so a sandbox
cannot read another call's directories, the attempt tree, the repository or anything else in the
user's profile. The caller puts `<call>` under a neutral root with a random name, outside the attempt
tree (mcp_server.py), so no path the sandboxed code can see names an attempt, item or arm.

Grants are made with icacls.exe (a Windows component) on directories this module creates; they never
touch a pre-existing file.

This module only *runs* a command. What goes into `in/` (visible task files and the subject's
workspace, never hidden data) is the caller's responsibility (checker.py, oracle2.py).
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import hashlib
import msvcrt
import os
import secrets
import shutil
import subprocess
import threading
import time
from pathlib import Path

SANDBOX_VERSION = "x1iso-winsandbox/2"   # /2: env allowlist, profile-folder disk cap, CPU = user+kernel

if os.name != "nt":  # pragma: no cover
    raise ImportError("winsandbox is Windows-only")

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
kbase = ctypes.WinDLL("kernelbase", use_last_error=True)
adv = ctypes.WinDLL("advapi32", use_last_error=True)
uenv = ctypes.WinDLL("userenv", use_last_error=True)
ole32 = ctypes.WinDLL("ole32", use_last_error=True)

PSID = ctypes.c_void_p
HANDLE = wt.HANDLE
SIZE_T = ctypes.c_size_t
ULONG_PTR = ctypes.c_size_t


class SID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Sid", PSID), ("Attributes", wt.DWORD)]


class SECURITY_CAPABILITIES(ctypes.Structure):
    _fields_ = [("AppContainerSid", PSID), ("Capabilities", ctypes.POINTER(SID_AND_ATTRIBUTES)),
                ("CapabilityCount", wt.DWORD), ("Reserved", wt.DWORD)]


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD), ("lpReserved", wt.LPWSTR), ("lpDesktop", wt.LPWSTR),
                ("lpTitle", wt.LPWSTR), ("dwX", wt.DWORD), ("dwY", wt.DWORD), ("dwXSize", wt.DWORD),
                ("dwYSize", wt.DWORD), ("dwXCountChars", wt.DWORD), ("dwYCountChars", wt.DWORD),
                ("dwFillAttribute", wt.DWORD), ("dwFlags", wt.DWORD), ("wShowWindow", wt.WORD),
                ("cbReserved2", wt.WORD), ("lpReserved2", ctypes.c_void_p), ("hStdInput", HANDLE),
                ("hStdOutput", HANDLE), ("hStdError", HANDLE)]


class STARTUPINFOEXW(ctypes.Structure):
    _fields_ = [("StartupInfo", STARTUPINFOW), ("lpAttributeList", ctypes.c_void_p)]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [("hProcess", HANDLE), ("hThread", HANDLE), ("dwProcessId", wt.DWORD),
                ("dwThreadId", wt.DWORD)]


class SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("nLength", wt.DWORD), ("lpSecurityDescriptor", ctypes.c_void_p),
                ("bInheritHandle", wt.BOOL)]


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [(n, ctypes.c_ulonglong) for n in ("ReadOperationCount", "WriteOperationCount",
                                                   "OtherOperationCount", "ReadTransferCount",
                                                   "WriteTransferCount", "OtherTransferCount")]


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wt.DWORD), ("MinimumWorkingSetSize", SIZE_T),
                ("MaximumWorkingSetSize", SIZE_T), ("ActiveProcessLimit", wt.DWORD),
                ("Affinity", ULONG_PTR), ("PriorityClass", wt.DWORD), ("SchedulingClass", wt.DWORD)]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION), ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", SIZE_T), ("JobMemoryLimit", SIZE_T),
                ("PeakProcessMemoryUsed", SIZE_T), ("PeakJobMemoryUsed", SIZE_T)]


class JOBOBJECT_BASIC_ACCOUNTING_INFORMATION(ctypes.Structure):
    _fields_ = [("TotalUserTime", ctypes.c_longlong), ("TotalKernelTime", ctypes.c_longlong),
                ("ThisPeriodTotalUserTime", ctypes.c_longlong), ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
                ("TotalPageFaultCount", wt.DWORD), ("TotalProcesses", wt.DWORD),
                ("ActiveProcesses", wt.DWORD), ("TotalTerminatedProcesses", wt.DWORD)]


class JOBOBJECT_BASIC_UI_RESTRICTIONS(ctypes.Structure):
    _fields_ = [("UIRestrictionsClass", wt.DWORD)]


class JOBOBJECT_CPU_RATE_CONTROL_INFORMATION(ctypes.Structure):
    _fields_ = [("ControlFlags", wt.DWORD), ("CpuRate", wt.DWORD)]


# Win32 constants (winbase.h, winnt.h, processthreadsapi.h)
EXTENDED_STARTUPINFO_PRESENT = 0x00080000
CREATE_SUSPENDED = 0x00000004
CREATE_UNICODE_ENVIRONMENT = 0x00000400
CREATE_NO_WINDOW = 0x08000000
STARTF_USESTDHANDLES = 0x00000100
PROC_THREAD_ATTRIBUTE_HANDLE_LIST = 0x00020002
PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES = 0x00020009
PROC_THREAD_ATTRIBUTE_ALL_APPLICATION_PACKAGES_POLICY = 0x0002000F
PROCESS_CREATION_ALL_APPLICATION_PACKAGES_OPT_OUT = 0x01
SE_GROUP_ENABLED = 0x00000004
HANDLE_FLAG_INHERIT = 0x00000001
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 0x102
INFINITE = 0xFFFFFFFF

JobObjectBasicAccountingInformation = 1
JobObjectBasicUIRestrictions = 4
JobObjectExtendedLimitInformation = 9
JobObjectCpuRateControlInformation = 15
JOB_OBJECT_LIMIT_JOB_TIME = 0x00000004
JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x00000008
JOB_OBJECT_LIMIT_JOB_MEMORY = 0x00000200
JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION = 0x00000400
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JOB_OBJECT_UILIMIT_ALL = 0x000000FF   # HANDLES|READ/WRITECLIPBOARD|SYSTEMPARAMETERS|DISPLAYSETTINGS|GLOBALATOMS|DESKTOP|EXITWINDOWS
JOB_OBJECT_CPU_RATE_CONTROL_ENABLE = 0x1
JOB_OBJECT_CPU_RATE_CONTROL_HARD_CAP = 0x4

KILLED_WALL = 0xC0DE0001
KILLED_DISK = 0xC0DE0002
KILLED_CPU = 0xC0DE0003

# prototypes
uenv.DeriveAppContainerSidFromAppContainerName.argtypes = [wt.LPCWSTR, ctypes.POINTER(PSID)]
uenv.DeriveAppContainerSidFromAppContainerName.restype = ctypes.c_long  # HRESULT
uenv.CreateAppContainerProfile.argtypes = [wt.LPCWSTR, wt.LPCWSTR, wt.LPCWSTR, ctypes.c_void_p, wt.DWORD,
                                           ctypes.POINTER(PSID)]
uenv.CreateAppContainerProfile.restype = ctypes.c_long  # HRESULT
uenv.DeleteAppContainerProfile.argtypes = [wt.LPCWSTR]
uenv.DeleteAppContainerProfile.restype = ctypes.c_long  # HRESULT
uenv.GetAppContainerFolderPath.argtypes = [wt.LPCWSTR, ctypes.POINTER(ctypes.c_void_p)]
uenv.GetAppContainerFolderPath.restype = ctypes.c_long  # HRESULT
ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
ole32.CoTaskMemFree.restype = None
adv.FreeSid.argtypes = [PSID]
adv.FreeSid.restype = PSID
adv.ConvertSidToStringSidW.argtypes = [PSID, ctypes.POINTER(wt.LPWSTR)]
adv.ConvertSidToStringSidW.restype = wt.BOOL
kbase.DeriveCapabilitySidsFromName.argtypes = [wt.LPCWSTR, ctypes.POINTER(ctypes.POINTER(PSID)),
                                               ctypes.POINTER(wt.DWORD), ctypes.POINTER(ctypes.POINTER(PSID)),
                                               ctypes.POINTER(wt.DWORD)]
kbase.DeriveCapabilitySidsFromName.restype = wt.BOOL
k32.LocalFree.argtypes = [ctypes.c_void_p]
k32.LocalFree.restype = ctypes.c_void_p
k32.InitializeProcThreadAttributeList.argtypes = [ctypes.c_void_p, wt.DWORD, wt.DWORD, ctypes.POINTER(SIZE_T)]
k32.InitializeProcThreadAttributeList.restype = wt.BOOL
k32.UpdateProcThreadAttribute.argtypes = [ctypes.c_void_p, wt.DWORD, ULONG_PTR, ctypes.c_void_p, SIZE_T,
                                          ctypes.c_void_p, ctypes.c_void_p]
k32.UpdateProcThreadAttribute.restype = wt.BOOL
k32.DeleteProcThreadAttributeList.argtypes = [ctypes.c_void_p]
k32.DeleteProcThreadAttributeList.restype = None
k32.CreateProcessW.argtypes = [wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wt.BOOL, wt.DWORD,
                               ctypes.c_void_p, wt.LPCWSTR, ctypes.c_void_p, ctypes.POINTER(PROCESS_INFORMATION)]
k32.CreateProcessW.restype = wt.BOOL
k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wt.LPCWSTR]
k32.CreateJobObjectW.restype = HANDLE
k32.SetInformationJobObject.argtypes = [HANDLE, ctypes.c_int, ctypes.c_void_p, wt.DWORD]
k32.SetInformationJobObject.restype = wt.BOOL
k32.QueryInformationJobObject.argtypes = [HANDLE, ctypes.c_int, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD)]
k32.QueryInformationJobObject.restype = wt.BOOL
k32.AssignProcessToJobObject.argtypes = [HANDLE, HANDLE]
k32.AssignProcessToJobObject.restype = wt.BOOL
k32.TerminateJobObject.argtypes = [HANDLE, wt.UINT]
k32.TerminateJobObject.restype = wt.BOOL
k32.ResumeThread.argtypes = [HANDLE]
k32.ResumeThread.restype = wt.DWORD
k32.WaitForSingleObject.argtypes = [HANDLE, wt.DWORD]
k32.WaitForSingleObject.restype = wt.DWORD
k32.GetExitCodeProcess.argtypes = [HANDLE, ctypes.POINTER(wt.DWORD)]
k32.GetExitCodeProcess.restype = wt.BOOL
k32.CloseHandle.argtypes = [HANDLE]
k32.CloseHandle.restype = wt.BOOL
k32.CreatePipe.argtypes = [ctypes.POINTER(HANDLE), ctypes.POINTER(HANDLE), ctypes.POINTER(SECURITY_ATTRIBUTES), wt.DWORD]
k32.CreatePipe.restype = wt.BOOL
k32.SetHandleInformation.argtypes = [HANDLE, wt.DWORD, wt.DWORD]
k32.SetHandleInformation.restype = wt.BOOL
k32.TerminateProcess.argtypes = [HANDLE, wt.UINT]
k32.TerminateProcess.restype = wt.BOOL
k32.GetCurrentProcess.argtypes = []
k32.GetCurrentProcess.restype = HANDLE
adv.OpenProcessToken.argtypes = [HANDLE, wt.DWORD, ctypes.POINTER(HANDLE)]
adv.OpenProcessToken.restype = wt.BOOL
adv.GetTokenInformation.argtypes = [HANDLE, ctypes.c_int, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD)]
adv.GetTokenInformation.restype = wt.BOOL


class SandboxError(RuntimeError):
    """An infrastructure failure of the sandbox itself (never a verdict on the subject's code)."""


def _err(what: str) -> SandboxError:
    e = ctypes.get_last_error()
    return SandboxError(f"{what} failed: winerror {e} ({ctypes.FormatError(e).strip()})")


def _sid_to_str(sid) -> str:
    s = wt.LPWSTR()
    if not adv.ConvertSidToStringSidW(sid, ctypes.byref(s)):
        raise _err("ConvertSidToStringSidW")
    try:
        return s.value
    finally:
        k32.LocalFree(s)


def _check_name(name: str) -> None:
    if not (1 <= len(name) <= 64) or not all(c.isalnum() or c in "._-" for c in name):
        raise ValueError("AppContainer name: 1-64 characters of [A-Za-z0-9._-]")


class AppContainerSid:
    """The SID of an AppContainer name, derived without creating a profile."""

    def __init__(self, name: str):
        _check_name(name)
        self.name = name
        self.sid = PSID()
        hr = uenv.DeriveAppContainerSidFromAppContainerName(name, ctypes.byref(self.sid))
        if hr != 0:
            raise SandboxError(f"DeriveAppContainerSidFromAppContainerName failed: HRESULT {hr & 0xFFFFFFFF:#010x}")
        self.str = _sid_to_str(self.sid)

    def close(self):
        if self.sid:
            adv.FreeSid(self.sid)
            self.sid = PSID()


class AppContainerProfile:
    """A registered AppContainer profile (CreateAppContainerProfile).

    A per-user app-package registration in the user's own registry hive (HKCU), not a system or
    security setting. It is required before an AppContainer process will launch (an unregistered,
    derive-only SID fails CreateProcessW with ERROR_FILE_NOT_FOUND [M, laptop, 2026-10-23]). The
    registration comes with a storage folder, %LOCALAPPDATA%\\Packages\\<name>\\ (`storage_root`),
    which the container's SID can write, LPAC included [M]; Sandbox.run counts it against the disk
    cap. It is reversible: `close()` calls DeleteAppContainerProfile, which removes the registration
    and the folder [M, laptop, 2026-10-23].
    """

    def __init__(self, name: str):
        _check_name(name)
        self.name = name
        self.sid = PSID()
        hr = uenv.CreateAppContainerProfile(name, name, name, None, 0, ctypes.byref(self.sid))
        hr &= 0xFFFFFFFF
        if hr == 0x800700B7:  # HRESULT_FROM_WIN32(ERROR_ALREADY_EXISTS): reuse by deriving the SID
            self._derived = AppContainerSid(name)
            self.sid = self._derived.sid
            self.str = self._derived.str
        elif hr != 0:
            raise SandboxError(f"CreateAppContainerProfile({name}) failed: HRESULT {hr:#010x}")
        else:
            self._derived = None
            self.str = _sid_to_str(self.sid)
        try:
            self.storage_root = self._storage_root()
        except Exception:
            self.close()
            raise

    def _storage_root(self) -> Path:
        """The profile's storage folder (the parent of GetAppContainerFolderPath's `AC` folder)."""
        p = ctypes.c_void_p()
        hr = uenv.GetAppContainerFolderPath(self.str, ctypes.byref(p)) & 0xFFFFFFFF
        if hr != 0 or not p.value:
            raise SandboxError(f"GetAppContainerFolderPath({self.name}) failed: HRESULT {hr:#010x}")
        try:
            return Path(ctypes.wstring_at(p.value)).parent
        finally:
            ole32.CoTaskMemFree(p)

    def close(self):
        try:
            uenv.DeleteAppContainerProfile(self.name)
        finally:
            if self._derived is not None:
                self._derived.close()
            elif self.sid:
                adv.FreeSid(self.sid)
            self.sid = PSID()


class CapabilitySid:
    """A custom capability SID derived from a name (DeriveCapabilitySidsFromName)."""

    def __init__(self, name: str):
        self.name = name
        grp = ctypes.POINTER(PSID)()
        ngrp = wt.DWORD()
        caps = ctypes.POINTER(PSID)()
        ncaps = wt.DWORD()
        if not kbase.DeriveCapabilitySidsFromName(name, ctypes.byref(grp), ctypes.byref(ngrp),
                                                  ctypes.byref(caps), ctypes.byref(ncaps)):
            raise _err("DeriveCapabilitySidsFromName")
        if ncaps.value < 1:
            raise SandboxError("DeriveCapabilitySidsFromName returned no capability SID")
        self.sid = PSID(caps[0])
        self.str = _sid_to_str(self.sid)
        self._owned = [grp[i] for i in range(ngrp.value)] + [caps[i] for i in range(1, ncaps.value)]
        self._arrays = [grp, caps]

    def close(self):
        for p in self._owned:
            k32.LocalFree(p)
        if self.sid:
            k32.LocalFree(self.sid)
            self.sid = PSID()
        for a in self._arrays:
            k32.LocalFree(a)
        self._owned, self._arrays = [], []


# ----------------------------------------------------------------------------- ACL helpers (icacls)

ICACLS = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "icacls.exe")


def _icacls(*args) -> None:
    p = subprocess.run([ICACLS, *args], capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        raise SandboxError(f"icacls {' '.join(args[1:])} on {args[0]} failed: rc {p.returncode}: "
                           f"{(p.stdout + p.stderr).strip()[:300]}")


_USER_SID = None


def current_user_sid() -> str:
    """The SID of this process's user (OpenProcessToken + GetTokenInformation(TokenUser))."""
    global _USER_SID
    if _USER_SID is None:
        TOKEN_QUERY, TokenUser = 0x0008, 1
        tok = HANDLE()
        if not adv.OpenProcessToken(k32.GetCurrentProcess(), TOKEN_QUERY, ctypes.byref(tok)):
            raise _err("OpenProcessToken")
        try:
            need = wt.DWORD()
            adv.GetTokenInformation(tok, TokenUser, None, 0, ctypes.byref(need))
            buf = ctypes.create_string_buffer(need.value)
            if not adv.GetTokenInformation(tok, TokenUser, buf, need, ctypes.byref(need)):
                raise _err("GetTokenInformation(TokenUser)")
            _USER_SID = _sid_to_str(ctypes.cast(buf, ctypes.POINTER(SID_AND_ATTRIBUTES)).contents.Sid)
        finally:
            k32.CloseHandle(tok)
    return _USER_SID


def grant_owner_full(path: Path) -> None:
    """Full control for this process's user on a directory this module just created, inherited.
    Setting a mandatory label needs WRITE_OWNER; outside the user profile (e.g. under C:\\, where
    the user inherits only Modify) the label step fails without this [M, laptop, 2026-10-23]."""
    _icacls(str(path), "/grant", f"*{current_user_sid()}:(OI)(CI)(F)")


def grant_read(path: Path, sid_str: str) -> None:
    """Read and execute for `sid_str`, inherited by every file and directory created below `path`."""
    _icacls(str(path), "/grant", f"*{sid_str}:(OI)(CI)(RX)")


def grant_write(path: Path, sid_str: str) -> None:
    """Modify for `sid_str`, inherited, and a Low mandatory label (an AppContainer runs at Low)."""
    _icacls(str(path), "/grant", f"*{sid_str}:(OI)(CI)(M)")
    _icacls(str(path), "/setintegritylevel", "(OI)(CI)L")


def acl_text(path: Path) -> str:
    p = subprocess.run([ICACLS, str(path)], capture_output=True, text=True, timeout=60)
    return p.stdout


# ----------------------------------------------------------------------------- sandbox call

# Limits of ONE Sandbox.run. DESIGN 11.2's caps are per `check` call; checker.run_check holds one CPU
# pool and one wall deadline per call and hands each run only what is left (review 1, finding 2).
DEFAULT_LIMITS = {
    "cpu_s": 180.0,          # DESIGN 11.2: 180 CPU-seconds per call [G] (user + kernel)
    "wall_s": 540.0,         # DESIGN 11.2: wall backstop 3x [G]
    "memory_bytes": 4 << 30, # DESIGN 11.2: --memory=4g [G]
    "processes": 32,         # rustc -> gcc -> ld chains need a few; DESIGN's pids-limit counts threads
    "cpu_rate_pct": 12.5,    # hard cap: 2 of the laptop's 16 logical processors (DESIGN --cpus=2) [G]
    "out_bytes": 512 << 20,  # DESIGN 11.2: --tmpfs /tmp:size=512m [G]
    "stdout_bytes": 64 << 10,  # DESIGN 11.2: output truncated to 64 KB before it reaches the agent [G]
}


def _env_block(env: dict) -> ctypes.Array:
    # A Unicode environment block: sorted NAME=VALUE pairs, each NUL-terminated, the whole block
    # closed by one more NUL. Built element-wise so the embedded NULs survive (create_unicode_buffer
    # truncates a string initializer at the first NUL).
    items = sorted(env.items(), key=lambda kv: kv[0].upper())
    s = "".join(f"{k}={v}\0" for k, v in items) + "\0"
    return ctypes.create_unicode_buffer(s, len(s))


def _cmdline(argv) -> str:
    return subprocess.list2cmdline([str(a) for a in argv])


def _pipe(inherit_write: bool):
    """An anonymous pipe; the end handed to the child is inheritable, ours is not."""
    sa = SECURITY_ATTRIBUTES(ctypes.sizeof(SECURITY_ATTRIBUTES), None, True)
    r, w = HANDLE(), HANDLE()
    if not k32.CreatePipe(ctypes.byref(r), ctypes.byref(w), ctypes.byref(sa), 0):
        raise _err("CreatePipe")
    ours = r if inherit_write else w
    if not k32.SetHandleInformation(ours, HANDLE_FLAG_INHERIT, 0):
        raise _err("SetHandleInformation")
    return r, w


def _reader(handle, cap: int, sink: dict, key: str):
    fd = msvcrt.open_osfhandle(handle.value, os.O_RDONLY)
    buf, total = bytearray(), 0
    with os.fdopen(fd, "rb", buffering=0) as f:
        while True:
            try:
                chunk = f.read(65536)
            except OSError:
                break
            if not chunk:
                break
            total += len(chunk)
            if len(buf) < cap:
                buf += chunk[: cap - len(buf)]
    sink[key] = bytes(buf)
    sink[key + "_total"] = total


def _writer(handle, data: bytes):
    fd = msvcrt.open_osfhandle(handle.value, os.O_WRONLY)
    with os.fdopen(fd, "wb", buffering=0) as f:
        try:
            f.write(data)
        except OSError:
            pass


def dir_bytes(path: Path) -> int:
    total = 0
    for root, _dirs, files in os.walk(path):
        for n in files:
            try:
                total += os.stat(os.path.join(root, n)).st_size
            except OSError:
                pass
    return total


# The sandbox environment is an explicit allowlist; nothing is inherited from the runner, the MCP
# server or the Claude Code session above them (review 1, finding 1: inherit-then-scrub let 77 of 96
# variables through, account and session identifiers included).
#
# Bisection on the laptop [M, 2026-10-23]: an LPAC launch with the eleven system variables below but
# no LOCALAPPDATA fails with ERROR_ENVVAR_NOT_FOUND (203); adding LOCALAPPDATA alone launches; adding
# USERPROFILE or APPDATA alone does not. LOCALAPPDATA need not name the real folder: Windows rewrites
# the child's LOCALAPPDATA to `<LOCALAPPDATA given>\Packages\<profile>\AC` and TEMP/TMP to
# `...\AC\Temp` [M]. So LOCALAPPDATA is set to the call's `out/tmp`, and Sandbox pre-creates
# `out/tmp/Packages/<profile>/AC/Temp`: the child's temporary files land inside `out/`, under the
# disk cap, and no host path reaches the child through the environment. Values here are system
# paths or constants; no user, account, session or working-directory value is copied.
SANDBOX_ENV_NAMES = frozenset({
    "SystemRoot", "windir", "SystemDrive", "PATH", "PATHEXT", "ComSpec", "TEMP", "TMP", "OS",
    "PROCESSOR_ARCHITECTURE", "NUMBER_OF_PROCESSORS", "LOCALAPPDATA", "RUST_BACKTRACE",
})


def base_env(call_dir: Path, path_dirs) -> dict:
    """The sandbox environment: exactly the names in SANDBOX_ENV_NAMES, never inherited."""
    sysroot = os.environ.get("SystemRoot") or os.environ.get("SYSTEMROOT") or r"C:\Windows"
    tmp = str(call_dir / "out" / "tmp")
    arch = os.environ.get("PROCESSOR_ARCHITECTURE", "AMD64")
    if arch not in ("AMD64", "ARM64", "x86"):
        arch = "AMD64"
    env = {
        "SystemRoot": sysroot, "windir": sysroot, "SystemDrive": sysroot[:2],
        "PATH": ";".join([str(p) for p in path_dirs] + [os.path.join(sysroot, "System32"), sysroot]),
        "PATHEXT": ".COM;.EXE;.BAT;.CMD",
        "ComSpec": os.path.join(sysroot, "System32", "cmd.exe"),
        "TEMP": tmp, "TMP": tmp, "LOCALAPPDATA": tmp, "OS": "Windows_NT",
        "PROCESSOR_ARCHITECTURE": arch, "NUMBER_OF_PROCESSORS": "2", "RUST_BACKTRACE": "0",
    }
    if set(env) != SANDBOX_ENV_NAMES:
        raise SandboxError("sandbox environment does not match its allowlist")
    return env


class Sandbox:
    """One sandbox identity (an AppContainer SID) over one call directory.

    Usage:
        with Sandbox(call_dir, image) as sb:      # call_dir/in, call_dir/out are created and granted
            ... write files into sb.indir ...
            r = sb.run([...], cwd=sb.indir or sb.outdir, limits=...)
    The directory is removed by `close()` unless keep=True.
    """

    def __init__(self, call_dir: Path, image: "ToolchainImage | None" = None, lpac: bool = True,
                 keep: bool = False, name: str | None = None):
        self.call_dir = Path(call_dir)
        if self.call_dir.exists():
            raise SandboxError(f"call directory {self.call_dir} already exists (a call never reuses one)")
        self.image = image
        self.lpac = lpac
        self.keep = keep
        # Profile name `x1iso.<label>.<random>` (<= 64 chars): the random tail keeps every sandbox's
        # AppContainer SID distinct, so one sandbox cannot open another's directories; the fixed
        # prefix lets a leftover registration be found and deleted (stale_profiles()).
        label = "".join(c for c in (name or "") if c.isalnum())[:24]
        self.name = "x1iso." + (label + "." if label else "") + secrets.token_hex(6)
        self.ac = AppContainerProfile(self.name)
        self.cap = None
        try:
            self.cap = CapabilitySid(image.capability_name) if image is not None else None
            self.indir = self.call_dir / "in"
            self.outdir = self.call_dir / "out"
            self.call_dir.mkdir(parents=True)
            grant_owner_full(self.call_dir)
            self.indir.mkdir()
            self.outdir.mkdir()
            grant_read(self.indir, self.ac.str)
            grant_write(self.outdir, self.ac.str)
            # LOCALAPPDATA = out/tmp in the child's environment; Windows rewrites TEMP/TMP to
            # <LOCALAPPDATA>\Packages\<profile>\AC\Temp [M], so that folder is created here, inside out/.
            (self.outdir / "tmp" / "Packages" / self.name / "AC" / "Temp").mkdir(parents=True)
        except Exception:
            self.close()
            raise
        self.runs = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        try:
            if not self.keep and self.call_dir.exists():
                shutil.rmtree(self.call_dir, ignore_errors=True)
        finally:
            self.ac.close()
            if self.cap is not None:
                self.cap.close()

    def disk_bytes(self) -> int:
        """Bytes in every place the container can write: out/ and the profile's storage folder."""
        return dir_bytes(self.outdir) + dir_bytes(self.ac.storage_root)

    def env(self, extra_path=()) -> dict:
        dirs = list(extra_path)
        if self.image is not None:
            dirs = [str(p) for p in self.image.path_dirs()] + dirs
        return base_env(self.call_dir, dirs)

    def run(self, argv, cwd: Path | None = None, env: dict | None = None, limits: dict | None = None,
            stdin_bytes: bytes | None = None) -> dict:
        lim = dict(DEFAULT_LIMITS)
        lim.update(limits or {})
        env = env if env is not None else self.env()
        cwd = Path(cwd) if cwd is not None else self.outdir
        t0 = time.monotonic()

        # job
        job = k32.CreateJobObjectW(None, None)
        if not job:
            raise _err("CreateJobObjectW")
        handles_to_close = [job]
        try:
            ext = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            b = ext.BasicLimitInformation
            b.LimitFlags = (JOB_OBJECT_LIMIT_JOB_TIME | JOB_OBJECT_LIMIT_ACTIVE_PROCESS |
                            JOB_OBJECT_LIMIT_JOB_MEMORY | JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION |
                            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE)
            b.PerJobUserTimeLimit = int(lim["cpu_s"] * 10_000_000)
            b.ActiveProcessLimit = int(lim["processes"])
            ext.JobMemoryLimit = int(lim["memory_bytes"])
            if not k32.SetInformationJobObject(job, JobObjectExtendedLimitInformation, ctypes.byref(ext),
                                               ctypes.sizeof(ext)):
                raise _err("SetInformationJobObject(extended limits)")
            ui = JOBOBJECT_BASIC_UI_RESTRICTIONS(JOB_OBJECT_UILIMIT_ALL)
            if not k32.SetInformationJobObject(job, JobObjectBasicUIRestrictions, ctypes.byref(ui), ctypes.sizeof(ui)):
                raise _err("SetInformationJobObject(UI restrictions)")
            if lim.get("cpu_rate_pct"):
                rate = JOBOBJECT_CPU_RATE_CONTROL_INFORMATION(
                    JOB_OBJECT_CPU_RATE_CONTROL_ENABLE | JOB_OBJECT_CPU_RATE_CONTROL_HARD_CAP,
                    max(1, min(10000, int(round(lim["cpu_rate_pct"] * 100)))))
                if not k32.SetInformationJobObject(job, JobObjectCpuRateControlInformation, ctypes.byref(rate),
                                                   ctypes.sizeof(rate)):
                    raise _err("SetInformationJobObject(CPU rate)")

            # pipes
            out_r, out_w = _pipe(inherit_write=True)
            err_r, err_w = _pipe(inherit_write=True)
            in_r, in_w = _pipe(inherit_write=False)
            child_handles = [in_r, out_w, err_w]

            # attribute list: security capabilities, LPAC opt-out, handle list
            caps = []
            if self.cap is not None:
                caps.append(SID_AND_ATTRIBUTES(self.cap.sid, SE_GROUP_ENABLED))
            cap_arr = (SID_AND_ATTRIBUTES * max(1, len(caps)))(*caps)
            sc = SECURITY_CAPABILITIES(self.ac.sid, cap_arr if caps else None, len(caps), 0)
            n_attr = 3 if self.lpac else 2
            size = SIZE_T()
            k32.InitializeProcThreadAttributeList(None, n_attr, 0, ctypes.byref(size))
            attr_buf = ctypes.create_string_buffer(size.value)
            if not k32.InitializeProcThreadAttributeList(attr_buf, n_attr, 0, ctypes.byref(size)):
                raise _err("InitializeProcThreadAttributeList")
            try:
                if not k32.UpdateProcThreadAttribute(attr_buf, 0, PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES,
                                                     ctypes.byref(sc), ctypes.sizeof(sc), None, None):
                    raise _err("UpdateProcThreadAttribute(security capabilities)")
                hl = (HANDLE * 3)(*child_handles)
                if not k32.UpdateProcThreadAttribute(attr_buf, 0, PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
                                                     ctypes.byref(hl), ctypes.sizeof(hl), None, None):
                    raise _err("UpdateProcThreadAttribute(handle list)")
                if self.lpac:
                    pol = wt.DWORD(PROCESS_CREATION_ALL_APPLICATION_PACKAGES_OPT_OUT)
                    if not k32.UpdateProcThreadAttribute(attr_buf, 0, PROC_THREAD_ATTRIBUTE_ALL_APPLICATION_PACKAGES_POLICY,
                                                         ctypes.byref(pol), ctypes.sizeof(pol), None, None):
                        raise _err("UpdateProcThreadAttribute(LPAC policy)")
                si = STARTUPINFOEXW()
                si.StartupInfo.cb = ctypes.sizeof(STARTUPINFOEXW)
                si.StartupInfo.dwFlags = STARTF_USESTDHANDLES
                si.StartupInfo.hStdInput = in_r
                si.StartupInfo.hStdOutput = out_w
                si.StartupInfo.hStdError = err_w
                si.lpAttributeList = ctypes.cast(attr_buf, ctypes.c_void_p)
                pi = PROCESS_INFORMATION()
                cmd = ctypes.create_unicode_buffer(_cmdline(argv))
                envb = _env_block(env)
                app = str(argv[0]) if os.path.isabs(str(argv[0])) else None
                ok = k32.CreateProcessW(app, cmd, None, None, True,
                                        EXTENDED_STARTUPINFO_PRESENT | CREATE_SUSPENDED |
                                        CREATE_UNICODE_ENVIRONMENT | CREATE_NO_WINDOW,
                                        envb, str(cwd), ctypes.byref(si), ctypes.byref(pi))
                create_err = ctypes.get_last_error()
            finally:
                k32.DeleteProcThreadAttributeList(attr_buf)
            for h in child_handles:
                k32.CloseHandle(h)
            if not ok:
                for h in (out_r, err_r, in_w):
                    k32.CloseHandle(h)
                return {"started": False, "create_error": create_err,
                        "create_error_text": ctypes.FormatError(create_err).strip(), "rc": None,
                        "stdout": "", "stderr": "", "killed": None, "wall_s": round(time.monotonic() - t0, 3)}
            handles_to_close += [pi.hProcess, pi.hThread]
            if not k32.AssignProcessToJobObject(job, pi.hProcess):
                k32.TerminateProcess(pi.hProcess, 1)
                raise _err("AssignProcessToJobObject")

            sink = {}
            th = [threading.Thread(target=_reader, args=(out_r, int(lim["stdout_bytes"]), sink, "stdout"), daemon=True),
                  threading.Thread(target=_reader, args=(err_r, int(lim["stdout_bytes"]), sink, "stderr"), daemon=True),
                  threading.Thread(target=_writer, args=(in_w, stdin_bytes or b""), daemon=True)]
            for t in th:
                t.start()
            if k32.ResumeThread(pi.hThread) == 0xFFFFFFFF:
                k32.TerminateJobObject(job, 1)
                raise _err("ResumeThread")

            killed = None
            deadline = t0 + float(lim["wall_s"])
            cpu_cap = float(lim["cpu_s"])
            next_disk = 0.0
            poll = JOBOBJECT_BASIC_ACCOUNTING_INFORMATION()
            while True:
                w = k32.WaitForSingleObject(pi.hProcess, 100)
                if w == WAIT_OBJECT_0:
                    break
                now = time.monotonic()
                if now >= deadline:
                    killed = "wall"
                    k32.TerminateJobObject(job, KILLED_WALL)
                    k32.WaitForSingleObject(pi.hProcess, 5000)
                    break
                # CPU = user + kernel time of every process in the job (the Job's own limit counts
                # user time only and stays as the backstop).
                if k32.QueryInformationJobObject(job, JobObjectBasicAccountingInformation, ctypes.byref(poll),
                                                 ctypes.sizeof(poll), None):
                    if (poll.TotalUserTime + poll.TotalKernelTime) / 1e7 >= cpu_cap:
                        killed = "cpu"
                        k32.TerminateJobObject(job, KILLED_CPU)
                        k32.WaitForSingleObject(pi.hProcess, 5000)
                        break
                if now >= next_disk:
                    next_disk = now + 0.25
                    if self.disk_bytes() > int(lim["out_bytes"]):
                        killed = "disk"
                        k32.TerminateJobObject(job, KILLED_DISK)
                        k32.WaitForSingleObject(pi.hProcess, 5000)
                        break
            code = wt.DWORD()
            k32.GetExitCodeProcess(pi.hProcess, ctypes.byref(code))
            acct = JOBOBJECT_BASIC_ACCOUNTING_INFORMATION()
            k32.QueryInformationJobObject(job, JobObjectBasicAccountingInformation, ctypes.byref(acct),
                                          ctypes.sizeof(acct), None)
            ext2 = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            k32.QueryInformationJobObject(job, JobObjectExtendedLimitInformation, ctypes.byref(ext2),
                                          ctypes.sizeof(ext2), None)
            stragglers = acct.ActiveProcesses
            k32.TerminateJobObject(job, 0)  # nothing outlives the call
            for t in th:
                t.join(timeout=10)
            user_s = acct.TotalUserTime / 1e7
            if killed is None and user_s >= lim["cpu_s"] * 0.98:
                killed = "cpu"   # the Job's own user-time limit fired between two polls
            res = {
                "started": True, "rc": code.value, "killed": killed,
                "stdout": sink.get("stdout", b"").decode("utf-8", "replace"),
                "stderr": sink.get("stderr", b"").decode("utf-8", "replace"),
                "stdout_total_bytes": sink.get("stdout_total", 0), "stderr_total_bytes": sink.get("stderr_total", 0),
                "cpu_user_s": round(user_s, 3), "cpu_kernel_s": round(acct.TotalKernelTime / 1e7, 3),
                "processes_total": acct.TotalProcesses, "stragglers_killed": stragglers,
                "peak_job_memory_bytes": ext2.PeakJobMemoryUsed,
                "wall_s": round(time.monotonic() - t0, 3), "limits": lim,
            }
            self.runs.append({k: v for k, v in res.items() if k not in ("stdout", "stderr")})
            return res
        finally:
            for h in handles_to_close:
                if h:
                    k32.CloseHandle(h)


_MAPPINGS = r"Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\AppContainer\Mappings"


def stale_profiles() -> list:
    """Names of registered AppContainer profiles this module created (`x1iso.` prefix) that still
    exist. Read-only (HKCU). A sandbox deletes its profile on close; a killed process cannot, so a
    runner calls this after an attempt and deletes what it finds with delete_profile()."""
    import winreg
    names = []
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _MAPPINGS) as k:
            i = 0
            while True:
                try:
                    sid = winreg.EnumKey(k, i)
                except OSError:
                    break
                i += 1
                try:
                    with winreg.OpenKey(k, sid) as sk:
                        moniker = winreg.QueryValueEx(sk, "Moniker")[0]
                except OSError:
                    continue
                if isinstance(moniker, str) and moniker.startswith("x1iso."):
                    names.append(moniker)
    except OSError:
        pass
    return sorted(names)


def delete_profile(name: str) -> int:
    """DeleteAppContainerProfile for one `x1iso.` profile; returns the HRESULT."""
    if not name.startswith("x1iso."):
        raise ValueError("only x1iso. profiles are deleted here")
    return uenv.DeleteAppContainerProfile(name) & 0xFFFFFFFF


# ----------------------------------------------------------------------------- toolchain image

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class ToolchainImage:
    """A read-only copy of the toolchains (rustc, mithi) that sandboxes may read and execute.

    The analogue of DESIGN 11.2's pinned container image. It is a copy, so the grant to the image's
    capability SID never touches the original toolchain's ACL. `manifest.json` records the SHA-256 of
    every file; `image_id` is the SHA-256 of the manifest's file list.
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        import json
        self.manifest = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        self.image_id = self.manifest["image_id"]
        self.capability_name = self.manifest["capability_name"]

    @property
    def rustc(self) -> Path:
        return self.root / "rust" / "bin" / "rustc.exe"

    @property
    def mithi(self) -> Path:
        return self.root / "mithi" / "mithi.exe"

    def path_dirs(self):
        return [self.root / "rust" / "bin"]

    @property
    def probe(self) -> Path:
        return self.root / "probe" / "probe.exe"

    @staticmethod
    def build(root: Path, rust_toolchain: Path | None, mithi: Path | None,
              extra: "dict | None" = None) -> "ToolchainImage":
        """Copy rustc (bin/rustc.exe and DLLs, lib/) and mithi into `root`, grant the capability.

        `extra` maps a published relative path to a source file (e.g. {"probe/probe.exe": ...})."""
        import json
        root = Path(root)
        if root.exists():
            raise SandboxError(f"{root} exists; an image is built once into a new directory")
        root.mkdir(parents=True)
        # The capability is unique to this image (a random suffix). It is granted on the empty root
        # first, so every file copied in below inherits the grant; nothing else carries it.
        cap_name = "x1isoToolchain" + secrets.token_hex(8)
        cap = CapabilitySid(cap_name)
        try:
            grant_read(root, cap.str)
        finally:
            cap.close()
        if rust_toolchain is not None:
            (root / "rust" / "bin").mkdir(parents=True)
            src = Path(rust_toolchain)
            for p in (src / "bin").iterdir():
                if p.name == "rustc.exe" or p.suffix.lower() == ".dll":
                    shutil.copy2(p, root / "rust" / "bin" / p.name)
            shutil.copytree(src / "lib", root / "rust" / "lib")
        if mithi is not None:
            (root / "mithi").mkdir()
            shutil.copy2(mithi, root / "mithi" / "mithi.exe")
        for rel, srcp in (extra or {}).items():
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(srcp, dst)
        files = {}
        for dp, _dn, fn in os.walk(root):
            for n in fn:
                p = Path(dp) / n
                files[p.relative_to(root).as_posix()] = sha256_file(p)
        listing = "\n".join(f"{k} {v}" for k, v in sorted(files.items()))
        image_id = hashlib.sha256(listing.encode()).hexdigest()
        manifest = {"schema": "x1iso-image/1", "image_id": image_id, "capability_name": cap_name,
                    "source_rust_toolchain": str(rust_toolchain) if rust_toolchain else None,
                    "source_mithi": str(mithi) if mithi else None,
                    "n_files": len(files), "files": files}
        (root / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
        return ToolchainImage(root)

    def verify(self, sample: int | None = None) -> dict:
        """Re-hash the image (all files, or the first `sample` in sorted order) against the manifest."""
        bad = []
        items = sorted(self.manifest["files"].items())
        if sample:
            items = items[:sample]
        for rel, h in items:
            p = self.root / rel
            if not p.exists() or sha256_file(p) != h:
                bad.append(rel)
        return {"ok": not bad, "checked": len(items), "bad": bad[:20]}
