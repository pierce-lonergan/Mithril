/* x4sb_probes.c -- sandbox self-test probes (SANDBOX.md section 5). See x4sb_probes.h.
 * Every probe records; none judges. Probes that would change state outside the run's own scratch tree
 * or this process are not run outside the sandbox (clear-limits, hard link, junction). */
#define WIN32_LEAN_AND_MEAN
#define COBJMACROS
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <winioctl.h>
#include <sddl.h>
#include <objbase.h>
#include <oleauto.h>
#include <wbemidl.h>
#include <taskschd.h>
#include <xmmintrin.h>
#include <wchar.h>
#include "x4sb_probes.h"

#pragma comment(lib, "ws2_32.lib")
#pragma comment(lib, "advapi32.lib")
#pragma comment(lib, "ole32.lib")
#pragma comment(lib, "oleaut32.lib")
#pragma comment(lib, "wbemuuid.lib")
#pragma comment(lib, "taskschd.lib")

typedef struct { x4sb_probe_result *out; int n, cap; LARGE_INTEGER f, t; } acc_t;

static void tick(acc_t *a) { QueryPerformanceCounter(&a->t); }
static void put(acc_t *a, uint64_t id, int attempted, int ok, uint64_t err, uint64_t extra) {
    LARGE_INTEGER now; QueryPerformanceCounter(&now);
    if (a->n >= a->cap) return;
    x4sb_probe_result *r = &a->out[a->n++];
    r->id = id; r->attempted = (uint64_t)attempted; r->succeeded = (uint64_t)(ok != 0); r->error = err;
    r->elapsed_us = (uint64_t)((now.QuadPart - a->t.QuadPart) * 1000000 / a->f.QuadPart);
    r->extra = extra;
}

/* ------------------------------------------------------------------ token */
static void probe_token(acc_t *a, const x4sb_probe_cfg *c) {
    HANDLE tok = NULL;
    tick(a);
    if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &tok)) {
        put(a, X4SB_TOKEN_APPCONTAINER, 1, 0, GetLastError(), 0);
        return;
    }
    DWORD v = 0, len = 0;
    BOOL ok = GetTokenInformation(tok, TokenIsAppContainer, &v, sizeof v, &len);
    put(a, X4SB_TOKEN_APPCONTAINER, 1, ok && v, ok ? 0 : GetLastError(), 0);

    DWORD err = 0;
    BYTE *buf = NULL;

    tick(a);
    TOKEN_ELEVATION e = {0};
    ok = GetTokenInformation(tok, TokenElevation, &e, sizeof e, &len);
    put(a, X4SB_TOKEN_ELEVATED, 1, ok && e.TokenIsElevated, ok ? 0 : GetLastError(), 0);

    tick(a);                                  /* enabled (not deny-only) BUILTIN\Administrators */
    int admin = 0; err = 0;
    BYTE asid[SECURITY_MAX_SID_SIZE]; DWORD asz = sizeof asid;
    CreateWellKnownSid(WinBuiltinAdministratorsSid, NULL, asid, &asz);
    GetTokenInformation(tok, TokenGroups, NULL, 0, &len);
    buf = len ? (BYTE *)HeapAlloc(GetProcessHeap(), 0, len) : NULL;
    if (buf && GetTokenInformation(tok, TokenGroups, buf, len, &len)) {
        TOKEN_GROUPS *g = (TOKEN_GROUPS *)buf;
        for (DWORD i = 0; i < g->GroupCount; i++)
            if (EqualSid(g->Groups[i].Sid, asid) && (g->Groups[i].Attributes & SE_GROUP_ENABLED) &&
                !(g->Groups[i].Attributes & SE_GROUP_USE_FOR_DENY_ONLY)) admin = 1;
    } else err = GetLastError();
    if (buf) HeapFree(GetProcessHeap(), 0, buf);
    put(a, X4SB_TOKEN_ADMIN_ENABLED, 1, admin, err, 0);

    tick(a);
    if (c->measure_sid) {
        PSID want = NULL; int same = 0; err = 0;
        BYTE ub[sizeof(TOKEN_USER) + SECURITY_MAX_SID_SIZE];
        if (ConvertStringSidToSidW(c->measure_sid, &want) &&
            GetTokenInformation(tok, TokenUser, ub, sizeof ub, &len))
            same = EqualSid(((TOKEN_USER *)ub)->User.Sid, want) != 0;
        else err = GetLastError();
        if (want) LocalFree(want);
        put(a, X4SB_TOKEN_USER_IS_MEASURE, 1, same, err, 0);
    } else put(a, X4SB_TOKEN_USER_IS_MEASURE, 0, 0, 0, 0);
    /* LPAC (the WIN://NOALLAPPPKG token attribute) is reported as not-yet-determined in v0: parsing
     * TokenSecurityAttributes safely needs more care than the gate requires (AppContainer is the bit
     * the refusal table reads). Recorded attempted=0 so the orchestrator treats LPAC as unknown. */
    put(a, X4SB_TOKEN_LPAC, 0, 0, 0, 0);
    CloseHandle(tok);
}

/* -------------------------------------------------------------------- job */
static void probe_job(acc_t *a, const x4sb_probe_cfg *c) {
    BOOL inj = FALSE;
    tick(a);
    BOOL ok = IsProcessInJob(GetCurrentProcess(), NULL, &inj);
    put(a, X4SB_JOB_IN_JOB, 1, ok && inj, ok ? 0 : GetLastError(), 0);

    JOBOBJECT_EXTENDED_LIMIT_INFORMATION li;
    ZeroMemory(&li, sizeof li);
    tick(a);
    ok = QueryInformationJobObject(NULL, JobObjectExtendedLimitInformation, &li, sizeof li, NULL);
    put(a, X4SB_JOB_QUERY_OWN_LIMITS, 1, ok, ok ? 0 : GetLastError(),
        ok ? (uint64_t)li.BasicLimitInformation.LimitFlags : 0);

    if (c->inside) {   /* a NULL handle names no job for Set; must fail. Never tried outside. */
        JOBOBJECT_EXTENDED_LIMIT_INFORMATION z;
        ZeroMemory(&z, sizeof z);
        tick(a);
        ok = SetInformationJobObject(NULL, JobObjectExtendedLimitInformation, &z, sizeof z);
        put(a, X4SB_JOB_CLEAR_LIMITS, 1, ok, ok ? 0 : GetLastError(), 0);
    } else put(a, X4SB_JOB_CLEAR_LIMITS, 0, 0, 0, 0);

    wchar_t exe[MAX_PATH];
    GetSystemDirectoryW(exe, MAX_PATH);
    wcscat_s(exe, MAX_PATH, L"\\cmd.exe");
    for (int brk = 0; brk < 2; brk++) {
        wchar_t cmd[32];
        wcscpy_s(cmd, 32, L"cmd.exe /c exit 0");
        STARTUPINFOW si; PROCESS_INFORMATION pi;
        ZeroMemory(&si, sizeof si); si.cb = sizeof si; ZeroMemory(&pi, sizeof pi);
        DWORD flags = CREATE_NO_WINDOW | (brk ? CREATE_BREAKAWAY_FROM_JOB : 0);
        tick(a);
        ok = CreateProcessW(exe, cmd, NULL, NULL, FALSE, flags, NULL, NULL, &si, &pi);
        DWORD e = ok ? 0 : GetLastError();
        if (ok) { WaitForSingleObject(pi.hProcess, 5000); CloseHandle(pi.hThread); CloseHandle(pi.hProcess); }
        put(a, brk ? X4SB_JOB_BREAKAWAY : X4SB_JOB_CREATE_CHILD, 1, ok, e, 0);
    }

    tick(a);
    DWORD before = GetPriorityClass(GetCurrentProcess());
    SetPriorityClass(GetCurrentProcess(), HIGH_PRIORITY_CLASS);
    DWORD after = GetPriorityClass(GetCurrentProcess());
    SetPriorityClass(GetCurrentProcess(), before);
    put(a, X4SB_JOB_RAISE_PRIORITY, 1, after == HIGH_PRIORITY_CLASS, 0, after);

    tick(a);
    DWORD_PTR pm = 0, sm = 0, pm2 = 0, sm2 = 0;
    GetProcessAffinityMask(GetCurrentProcess(), &pm, &sm);
    SetProcessAffinityMask(GetCurrentProcess(), sm);
    GetProcessAffinityMask(GetCurrentProcess(), &pm2, &sm2);
    SetProcessAffinityMask(GetCurrentProcess(), pm);
    put(a, X4SB_JOB_WIDEN_AFFINITY, 1, pm2 != pm, 0, (uint64_t)pm2);
}

/* ---------------------------------------------------------------- network */
static int tcp_connect(const wchar_t *host, uint16_t port, DWORD timeout_ms, uint64_t *err) {
    SOCKET s = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (s == INVALID_SOCKET) { *err = (uint64_t)WSAGetLastError(); return 0; }
    u_long nb = 1;
    ioctlsocket(s, FIONBIO, &nb);
    struct sockaddr_in sa;
    ZeroMemory(&sa, sizeof sa);
    sa.sin_family = AF_INET;
    sa.sin_port = htons(port);
    int ok = 0;
    if (InetPtonW(AF_INET, host, &sa.sin_addr) != 1) { *err = (uint64_t)WSAGetLastError(); goto done; }
    if (connect(s, (struct sockaddr *)&sa, sizeof sa) == 0) { ok = 1; goto done; }
    int e = WSAGetLastError();
    if (e != WSAEWOULDBLOCK) { *err = (uint64_t)e; goto done; }
    fd_set w, x;
    FD_ZERO(&w); FD_ZERO(&x); FD_SET(s, &w); FD_SET(s, &x);
    struct timeval tv = { (long)(timeout_ms / 1000), (long)((timeout_ms % 1000) * 1000) };
    int r = select(0, NULL, &w, &x, &tv);
    if (r == 0) { *err = WSAETIMEDOUT; goto done; }
    if (r == SOCKET_ERROR) { *err = (uint64_t)WSAGetLastError(); goto done; }
    if (FD_ISSET(s, &x)) {
        int se = 0, sl = sizeof se;
        getsockopt(s, SOL_SOCKET, SO_ERROR, (char *)&se, &sl);
        *err = (uint64_t)se;
        goto done;
    }
    ok = 1;
done:
    closesocket(s);
    return ok;
}

static void probe_net(acc_t *a, const x4sb_probe_cfg *c) {
    WSADATA wd;
    int wsa = WSAStartup(MAKEWORD(2, 2), &wd);
    uint64_t err = 0;
    if (c->loopback_port) {
        tick(a); err = (uint64_t)wsa;
        int ok = wsa == 0 && tcp_connect(L"127.0.0.1", c->loopback_port, 3000, &err);
        put(a, X4SB_NET_LOOPBACK_TCP, 1, ok, ok ? 0 : err, 0);
    } else put(a, X4SB_NET_LOOPBACK_TCP, 0, 0, 0, 0);
    if (c->lan_host && c->lan_port) {
        tick(a); err = (uint64_t)wsa;
        int ok = wsa == 0 && tcp_connect(c->lan_host, c->lan_port, 3000, &err);
        put(a, X4SB_NET_LAN_TCP, 1, ok, ok ? 0 : err, 0);
    } else put(a, X4SB_NET_LAN_TCP, 0, 0, 0, 0);
    if (c->dns_name) {
        ADDRINFOW hints, *res = NULL;
        ZeroMemory(&hints, sizeof hints);
        hints.ai_family = AF_UNSPEC;
        hints.ai_socktype = SOCK_STREAM;
        tick(a);
        int r = wsa == 0 ? GetAddrInfoW(c->dns_name, NULL, &hints, &res) : wsa;
        if (res) FreeAddrInfoW(res);
        put(a, X4SB_NET_DNS, 1, r == 0, (uint64_t)(uint32_t)r, 0);
    } else put(a, X4SB_NET_DNS, 0, 0, 0, 0);
    if (wsa == 0) WSACleanup();
}

/* ---------------------------------------------------------------- brokers */
static void probe_brokers(acc_t *a, const x4sb_probe_cfg *c) {
    if (c->pipe_name) {
        tick(a);
        HANDLE h = CreateFileW(c->pipe_name, GENERIC_READ | GENERIC_WRITE, 0, NULL, OPEN_EXISTING, 0, NULL);
        DWORD e = h == INVALID_HANDLE_VALUE ? GetLastError() : 0;
        if (h != INVALID_HANDLE_VALUE) CloseHandle(h);
        put(a, X4SB_BROKER_PIPE, 1, e == 0, e, 0);
    } else put(a, X4SB_BROKER_PIPE, 0, 0, 0, 0);

    tick(a);
    HRESULT hi = CoInitializeEx(NULL, COINIT_MULTITHREADED);
    if (FAILED(hi)) {
        put(a, X4SB_BROKER_WMI, 1, 0, (uint64_t)(uint32_t)hi, 1);
        put(a, X4SB_BROKER_TASKSCHED, 1, 0, (uint64_t)(uint32_t)hi, 1);
        put(a, X4SB_BROKER_COM_LOCAL, c->com_local, 0, (uint64_t)(uint32_t)hi, 1);
        return;
    }
    IWbemLocator *loc = NULL;
    HRESULT hr = CoCreateInstance(&CLSID_WbemLocator, NULL, CLSCTX_INPROC_SERVER, &IID_IWbemLocator, (void **)&loc);
    if (SUCCEEDED(hr)) {
        BSTR ns = SysAllocString(L"ROOT\\CIMV2");
        IWbemServices *svc = NULL;
        hr = IWbemLocator_ConnectServer(loc, ns, NULL, NULL, NULL, 0, NULL, NULL, &svc);
        if (svc) IWbemServices_Release(svc);
        SysFreeString(ns);
        IWbemLocator_Release(loc);
    }
    put(a, X4SB_BROKER_WMI, 1, SUCCEEDED(hr), SUCCEEDED(hr) ? 0 : (uint64_t)(uint32_t)hr, 0);

    tick(a);
    ITaskService *ts = NULL;
    hr = CoCreateInstance(&CLSID_TaskScheduler, NULL, CLSCTX_INPROC_SERVER, &IID_ITaskService, (void **)&ts);
    if (SUCCEEDED(hr)) {
        VARIANT v; VariantInit(&v);
        hr = ITaskService_Connect(ts, v, v, v, v);
        ITaskService_Release(ts);
    }
    put(a, X4SB_BROKER_TASKSCHED, 1, SUCCEEDED(hr), SUCCEEDED(hr) ? 0 : (uint64_t)(uint32_t)hr, 0);

    if (c->com_local && c->com_clsid) {
        CLSID id;
        tick(a);
        hr = CLSIDFromString(c->com_clsid, &id);
        IUnknown *u = NULL;
        if (SUCCEEDED(hr)) hr = CoCreateInstance(&id, NULL, CLSCTX_LOCAL_SERVER, &IID_IUnknown, (void **)&u);
        if (u) IUnknown_Release(u);
        put(a, X4SB_BROKER_COM_LOCAL, 1, SUCCEEDED(hr), SUCCEEDED(hr) ? 0 : (uint64_t)(uint32_t)hr, 0);
    } else put(a, X4SB_BROKER_COM_LOCAL, 0, 0, 0, 0);
    CoUninitialize();
}

/* ----------------------------------------------------------------- sealed */
static int try_open(const wchar_t *p, DWORD access, uint64_t *err) {
    HANDLE h = CreateFileW(p, access, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_EXISTING, 0, NULL);
    if (h == INVALID_HANDLE_VALUE) { *err = GetLastError(); return 0; }
    CloseHandle(h);   /* opened only: nothing is ever written */
    *err = 0;
    return 1;
}

/* REPARSE_DATA_BUFFER (mount point) is a DDK structure; the user-mode SDK does not define it. */
typedef struct {
    DWORD tag; WORD data_len; WORD reserved;
    WORD sub_off, sub_len, print_off, print_len;
    WCHAR path[1];
} x4sb_mount_point;

static int make_junction(const wchar_t *link, const wchar_t *target, uint64_t *err) {
    if (!CreateDirectoryW(link, NULL)) { *err = GetLastError(); return 0; }
    HANDLE h = CreateFileW(link, GENERIC_WRITE, 0, NULL, OPEN_EXISTING,
                           FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_BACKUP_SEMANTICS, NULL);
    if (h == INVALID_HANDLE_VALUE) { *err = GetLastError(); RemoveDirectoryW(link); return 0; }
    wchar_t nt[MAX_PATH + 8];
    swprintf(nt, MAX_PATH + 8, L"\\??\\%s", target);
    size_t nl = wcslen(nt) * sizeof(WCHAR);
    BYTE buf[sizeof(x4sb_mount_point) + 2 * (MAX_PATH + 8) * sizeof(WCHAR)];
    ZeroMemory(buf, sizeof buf);
    x4sb_mount_point *m = (x4sb_mount_point *)buf;
    m->tag = IO_REPARSE_TAG_MOUNT_POINT;
    m->sub_off = 0; m->sub_len = (WORD)nl;
    m->print_off = (WORD)(nl + sizeof(WCHAR)); m->print_len = 0;
    memcpy(m->path, nt, nl);
    m->data_len = (WORD)(8 + nl + 2 * sizeof(WCHAR));
    DWORD ret = 0;
    BOOL ok = DeviceIoControl(h, FSCTL_SET_REPARSE_POINT, buf, 8 + m->data_len, NULL, 0, &ret, NULL);
    *err = ok ? 0 : GetLastError();
    CloseHandle(h);
    if (!ok) RemoveDirectoryW(link);
    return ok;
}

static void probe_sealed(acc_t *a, const x4sb_probe_cfg *c) {
    if (!c->sealed_path) return;
    uint64_t err;
    int ok;
    tick(a); ok = try_open(c->sealed_path, GENERIC_READ, &err);  put(a, X4SB_SEALED_READ, 1, ok, err, 0);
    tick(a); ok = try_open(c->sealed_path, GENERIC_WRITE, &err); put(a, X4SB_SEALED_WRITE, 1, ok, err, 0);
    for (int i = 0; i < c->n_alt; i++) {
        tick(a); ok = try_open(c->alt[i], GENERIC_READ, &err);  put(a, X4SB_SEALED_ALT_READ, 1, ok, err, (uint64_t)i);
        tick(a); ok = try_open(c->alt[i], GENERIC_WRITE, &err); put(a, X4SB_SEALED_ALT_WRITE, 1, ok, err, (uint64_t)i);
    }
    if (!c->inside || !c->scratch) {   /* links are created only inside, only in the run's scratch */
        put(a, X4SB_SEALED_HARDLINK, 0, 0, 0, 0);
        put(a, X4SB_SEALED_JUNCTION_READ, 0, 0, 0, 0);
        return;
    }
    wchar_t p[MAX_PATH];
    swprintf(p, MAX_PATH, L"%s\\x4sb_hardlink", c->scratch);
    tick(a);
    ok = CreateHardLinkW(p, c->sealed_path, NULL);
    err = ok ? 0 : GetLastError();
    if (ok) DeleteFileW(p);          /* removes the link only */
    put(a, X4SB_SEALED_HARDLINK, 1, ok, err, 0);

    if (c->sealed_dir) {
        swprintf(p, MAX_PATH, L"%s\\x4sb_junction", c->scratch);
        tick(a);
        uint64_t jerr = 0;
        int made = make_junction(p, c->sealed_dir, &jerr);
        ok = 0; err = jerr;
        if (made) {
            const wchar_t *base = wcsrchr(c->sealed_path, L'\\');
            wchar_t q[MAX_PATH];
            swprintf(q, MAX_PATH, L"%s%s", p, base ? base : L"\\x");
            ok = try_open(q, GENERIC_READ, &err);
            RemoveDirectoryW(p);        /* removes the junction only */
        }
        put(a, X4SB_SEALED_JUNCTION_READ, 1, ok, err, (uint64_t)made);
    }
}

/* ---------------------------------------------------------------- scratch */
static void probe_scratch(acc_t *a, const x4sb_probe_cfg *c) {
    if (!c->scratch) return;
    wchar_t p[MAX_PATH];
    swprintf(p, MAX_PATH, L"%s\\*", c->scratch);
    WIN32_FIND_DATAW fd;
    uint64_t n = 0, err = 0;
    tick(a);
    HANDLE f = FindFirstFileW(p, &fd);
    if (f != INVALID_HANDLE_VALUE) {
        do { if (wcscmp(fd.cFileName, L".") && wcscmp(fd.cFileName, L"..")) n++; } while (FindNextFileW(f, &fd));
        FindClose(f);
    } else err = GetLastError();
    put(a, X4SB_SCRATCH_EMPTY, 1, err == 0 && n == 0, err, n);

    swprintf(p, MAX_PATH, L"%s\\x4sb_write.tmp", c->scratch);
    tick(a);
    HANDLE h = CreateFileW(p, GENERIC_WRITE, 0, NULL, CREATE_NEW, FILE_FLAG_DELETE_ON_CLOSE, NULL);
    DWORD w = 0;
    int ok = h != INVALID_HANDLE_VALUE && WriteFile(h, "x4sb-scratch-ok\n", 16, &w, NULL) && w == 16;
    err = ok ? 0 : GetLastError();
    if (h != INVALID_HANDLE_VALUE) CloseHandle(h);
    put(a, X4SB_SCRATCH_WRITE, 1, ok, err, 0);

    swprintf(p, MAX_PATH, L"%s\\x4sb_dio.tmp", c->scratch);
    tick(a);
    BYTE *buf = (BYTE *)VirtualAlloc(NULL, 8192, MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
    ok = 0; err = 0;
    if (buf) {
        for (int i = 0; i < 4096; i++) buf[i] = (BYTE)(i * 7 + 1);
        h = CreateFileW(p, GENERIC_READ | GENERIC_WRITE, 0, NULL, CREATE_NEW,
                        FILE_FLAG_NO_BUFFERING | FILE_FLAG_WRITE_THROUGH | FILE_FLAG_DELETE_ON_CLOSE, NULL);
        if (h != INVALID_HANDLE_VALUE) {
            DWORD rd = 0;
            if (WriteFile(h, buf, 4096, &w, NULL) && w == 4096 &&
                SetFilePointer(h, 0, NULL, FILE_BEGIN) == 0 &&
                ReadFile(h, buf + 4096, 4096, &rd, NULL) && rd == 4096)
                ok = memcmp(buf, buf + 4096, 4096) == 0;
            if (!ok) err = GetLastError();
            CloseHandle(h);
        } else err = GetLastError();
        VirtualFree(buf, 0, MEM_RELEASE);
    } else err = GetLastError();
    put(a, X4SB_DIRECT_IO, 1, ok, err, 0);
}

static void probe_misc(acc_t *a, const x4sb_probe_cfg *c) {
    (void)c;
    tick(a);
    SIZE_T lp = GetLargePageMinimum();
    void *p = lp ? VirtualAlloc(NULL, lp, MEM_RESERVE | MEM_COMMIT | MEM_LARGE_PAGES, PAGE_READWRITE) : NULL;
    DWORD e = p ? 0 : GetLastError();
    if (p) VirtualFree(p, 0, MEM_RELEASE);
    put(a, X4SB_LARGE_PAGES, 1, p != NULL, e, (uint64_t)lp);

    tick(a);
    unsigned int m = _mm_getcsr();
    put(a, X4SB_MXCSR_DEFAULT, 1, (m & 0xFFC0u) == 0x1F80u, 0, m);

    wchar_t path[MAX_PATH];
    DWORD n = GetModuleFileNameW(NULL, path, MAX_PATH);
    wchar_t *slash = n ? wcsrchr(path, L'\\') : NULL;
    tick(a);
    if (slash) {
        *slash = 0;
        wcscat_s(path, MAX_PATH, L"\\x4sb_exe_dir_write_probe.tmp");
        HANDLE h = CreateFileW(path, GENERIC_WRITE, 0, NULL, CREATE_NEW, FILE_FLAG_DELETE_ON_CLOSE, NULL);
        e = h == INVALID_HANDLE_VALUE ? GetLastError() : 0;
        if (h != INVALID_HANDLE_VALUE) CloseHandle(h);
        put(a, X4SB_EXE_DIR_WRITE, 1, e == 0, e, 0);
    } else put(a, X4SB_EXE_DIR_WRITE, 0, 0, GetLastError(), 0);
}

int x4sb_probe_arg(x4sb_probe_cfg *c, int argc, wchar_t **argv, int *i) {
    const wchar_t *k = argv[*i];
    if (*i + 1 >= argc) return 0;
    const wchar_t *v = argv[*i + 1];
    if (!wcscmp(k, L"--probe-port")) c->loopback_port = (uint16_t)wcstoul(v, NULL, 10);
    else if (!wcscmp(k, L"--probe-lan-host")) c->lan_host = v;
    else if (!wcscmp(k, L"--probe-lan-port")) c->lan_port = (uint16_t)wcstoul(v, NULL, 10);
    else if (!wcscmp(k, L"--probe-dns")) c->dns_name = v;
    else if (!wcscmp(k, L"--probe-pipe")) c->pipe_name = v;
    else if (!wcscmp(k, L"--probe-com")) { c->com_clsid = v; c->com_local = 1; }
    else if (!wcscmp(k, L"--sealed")) c->sealed_path = v;
    else if (!wcscmp(k, L"--sealed-dir")) c->sealed_dir = v;
    else if (!wcscmp(k, L"--alt")) { if (c->n_alt < X4SB_MAX_ALT) c->alt[c->n_alt++] = v; }
    else if (!wcscmp(k, L"--scratch")) c->scratch = v;
    else if (!wcscmp(k, L"--measure-sid")) c->measure_sid = v;
    else return 0;
    *i += 1;
    return 1;
}

/* Each probe group runs under SEH so a fault in one probe is contained (recorded as a crash marker,
 * id 0xE0000 + the group tag) and the remaining groups still run. A probe must never take the whole
 * self-test down. */
#define X4SB_GUARD(tag, call) __try { call; } \
    __except (EXCEPTION_EXECUTE_HANDLER) { put(&a, 0xE0000u + (tag), 1, 0, (uint64_t)GetExceptionCode(), 0); }

int x4sb_run_probes(const x4sb_probe_cfg *cfg, x4sb_probe_result *out, int cap) {
    acc_t a;
    a.out = out; a.n = 0; a.cap = cap;
    QueryPerformanceFrequency(&a.f);
    X4SB_GUARD(1, probe_scratch(&a, cfg));   /* first, while scratch is still empty */
    X4SB_GUARD(2, probe_token(&a, cfg));
    X4SB_GUARD(3, probe_misc(&a, cfg));
    X4SB_GUARD(4, probe_net(&a, cfg));
    X4SB_GUARD(5, probe_brokers(&a, cfg));
    X4SB_GUARD(6, probe_sealed(&a, cfg));
    X4SB_GUARD(7, probe_job(&a, cfg));       /* last: it changes this process's priority/affinity briefly */
    return a.n;
}
