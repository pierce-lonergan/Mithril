/* x4plant.c -- DRY-RUN trigger plant for the noise pilot's hygiene sensors (X4 pilot track,
 * 2026-10-23). Never part of a pilot night.
 *
 *   x4plant.exe <ms> <threads> [<MiB> <path>]
 *
 * Keeps <threads> threads busy (integer spin) for <ms> milliseconds, so the CPU-load sensor and the
 * excluded-process sensor have something real to see; with <MiB> and <path> it also writes the file
 * in 4 MiB write-through chunks, wrapping at <MiB>, for the same time (the disk-write sensor), then
 * deletes it. The pilot driver copies it under excluded or Mithril-like image names for the plants.
 * Build: cl /nologo /O2 /W4 /std:c11 /MT x4plant.c
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdlib.h>
#include <string.h>

static volatile LONG64 g_sink;
static ULONGLONG g_end;

static DWORD WINAPI spin(LPVOID p) {
    (void)p;
    unsigned long long x = 0x9e3779b97f4a7c15ull;
    while (GetTickCount64() < g_end) {
        for (int i = 0; i < 100000; i++) x = x * 6364136223846793005ull + 1442695040888963407ull;
    }
    InterlockedAdd64(&g_sink, (LONG64)x);
    return 0;
}

int wmain(int argc, wchar_t **argv) {
    if (argc < 3) return 2;
    {   /* DRY-RUN, revision 4: X4PLANT_DETACH=1 re-launches this exe with the same command line and
         * exits at once, so the plant's parent is no longer the driver (the driver exempts its own
         * children from the process sensors, by parent pid) */
        wchar_t d[4];
        if (GetEnvironmentVariableW(L"X4PLANT_DETACH", d, 4) > 0) {
            SetEnvironmentVariableW(L"X4PLANT_DETACH", NULL);
            wchar_t self[MAX_PATH];
            DWORD n = GetModuleFileNameW(NULL, self, MAX_PATH);
            if (n == 0 || n >= MAX_PATH) return 3;
            size_t len = wcslen(GetCommandLineW()) + 1;
            wchar_t *cmd = (wchar_t *)malloc(len * sizeof(wchar_t));
            if (!cmd) return 3;
            memcpy(cmd, GetCommandLineW(), len * sizeof(wchar_t));
            STARTUPINFOW si; PROCESS_INFORMATION pi;
            memset(&si, 0, sizeof si); si.cb = sizeof si;
            BOOL ok = CreateProcessW(self, cmd, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi);
            free(cmd);
            if (!ok) return 3;
            CloseHandle(pi.hThread); CloseHandle(pi.hProcess);
            return 0;
        }
    }
    ULONGLONG ms = wcstoull(argv[1], NULL, 10);
    int threads = _wtoi(argv[2]);
    if (threads < 1) threads = 1;
    if (threads > 3) threads = 3;   /* the track's thread budget */
    {   /* DRY-RUN: run on the LPs the driver names (inside the track's budget), else inherit */
        wchar_t buf[32];
        DWORD n = GetEnvironmentVariableW(L"X4PLANT_AFFINITY", buf, 32);
        if (n > 0 && n < 32) {
            ULONGLONG m = wcstoull(buf, NULL, 0);
            if (m) SetProcessAffinityMask(GetCurrentProcess(), (DWORD_PTR)m);
        }
    }
    g_end = GetTickCount64() + ms;
    HANDLE th[3] = { 0 };
    for (int i = 1; i < threads; i++) th[i] = CreateThread(NULL, 0, spin, NULL, 0, NULL);
    if (argc >= 5) {
        ULONGLONG cap = wcstoull(argv[3], NULL, 10) << 20;
        const DWORD chunk = 4u << 20;
        void *buf = VirtualAlloc(NULL, chunk, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
        HANDLE f = CreateFileW(argv[4], GENERIC_WRITE, 0, NULL, CREATE_ALWAYS,
                               FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH | FILE_FLAG_NO_BUFFERING, NULL);
        if (buf && f != INVALID_HANDLE_VALUE) {
            memset(buf, 0x5a, chunk);
            ULONGLONG off = 0;
            while (GetTickCount64() < g_end) {
                LARGE_INTEGER li; li.QuadPart = (LONGLONG)off;
                SetFilePointerEx(f, li, NULL, FILE_BEGIN);
                DWORD w = 0;
                if (!WriteFile(f, buf, chunk, &w, NULL)) break;
                off += chunk;
                if (cap && off >= cap) off = 0;
            }
            CloseHandle(f);
            DeleteFileW(argv[4]);
        }
        if (buf) VirtualFree(buf, 0, MEM_RELEASE);
    } else {
        spin(NULL);
    }
    for (int i = 1; i < threads; i++) if (th[i]) { WaitForSingleObject(th[i], INFINITE); CloseHandle(th[i]); }
    return 0;
}
