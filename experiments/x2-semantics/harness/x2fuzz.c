/* x2fuzz.c -- driver of the X2 native fuzz harness (FUZZ-DESIGN.md sec. 1, sec. 4). MSVC C11, Windows x64.
 *
 *   x2fuzz selftest [--cpu N] [--scratch DIR]        harness self-tests; step 9 is the exhaustive-engine
 *                                                    plumbing check (V5 stubs on silicon, 4,096 fixed inputs each)
 *   x2fuzz fingerprint                               CPU / microcode / OS / binary fingerprint (JSON)
 *   x2fuzz list                                      the stub table (JSON lines)
 *   x2fuzz run VEC RES [--cpu N] [--collection-authorised]
 *                                                    sampled mode on silicon: VEC -> RES
 *   x2fuzz predict VEC PRED                          the C reference interpreter: VEC -> PRED
 *   x2fuzz exhaustive (--stub ID | --iform IFORM --variant VARIANT) --mxcsr HEX --lo HEX --hi HEX --out DIR
 *                     [--oracle silicon|self|mutant] [--threads T] [--cpus a,b,...] [--max-mismatch-records N]
 *                     [--collection-authorised]
 *                                                    exhaustive mode (V5): in-process compare, mismatches + stream hash
 *
 * Collection guard (revised 2026-10-16 after review): `run` refuses, unless --collection-authorised is given,
 * (a) a vector set whose label does not start with DEV, SELFTEST or VALID, and (b) ANY record whose set id is
 * a budget set (V1, V2, V3, V4, BCAST, F-MEMFAULT; vecfmt.SETS 1-6), whatever the label says. Development
 * tools use the sets DEV (7) and VALID (8). `exhaustive --oracle silicon` refuses to start without the flag.
 * The flag exists for the X2 record's collection runs (FROZEN and SIGNED, docs/m0/README.md); nothing in
 * this build session passes it.
 *
 * MXCSR precondition (FUZZ-DESIGN sec. 2: the flags are clear before each execution): `run` reports a record
 * whose MXCSR has a sticky flag set (bits 5:0) as UNMODELED unless the label starts with VALID; `exhaustive`
 * refuses an --mxcsr with a sticky flag, an unmasked exception or a reserved bit.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <intrin.h>
#include <immintrin.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "build_info.h"
#include "x2harness.h"
#include "x2sha256.h"

static int g_fail = 0;
#define CHECK(cond, ...) do { if (!(cond)) { g_fail++; printf("FAIL "); printf(__VA_ARGS__); printf("\n"); } } while (0)

static void die(const char *m) { fprintf(stderr, "x2fuzz: %s\n", m); exit(2); }

/* ------------------------------------------------------------------ fingerprint */
typedef struct {
    char vendor[13], brand[49];
    unsigned family, model, stepping, cpuid1_eax;
    int avx2, avx512f, avx512bw, avx512vl, avx512vnni, f16c, os_zmm;
    char ucode_hex[17];
    unsigned ucode_hi, ucode_lo;
    char os_build[64];
    char exe_sha256[65];
    char l3_groups[160];        /* logical-processor masks sharing one L3 (one CCD on Zen 5) */
} x2fp;

static void l3_groups(char *out, size_t cap) {
    DWORD len = 0;
    char *buf, *p;
    size_t used = 0;
    out[0] = 0;
    GetLogicalProcessorInformationEx(RelationCache, NULL, &len);
    buf = (char *)malloc(len);
    if (!buf || !GetLogicalProcessorInformationEx(RelationCache, (PSYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX)buf, &len)) {
        free(buf);
        return;
    }
    for (p = buf; p < buf + len;) {
        PSYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX e = (PSYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX)p;
        if (e->Relationship == RelationCache && e->Cache.Level == 3 && used + 24 < cap)
            used += (size_t)_snprintf(out + used, cap - used, "%s0x%llx", used ? "," : "",
                                      (unsigned long long)e->Cache.GroupMask.Mask);
        p += e->Size;
    }
    free(buf);
}

static void file_sha256(const char *path, char out[65]) {
    FILE *f = fopen(path, "rb");
    x2sha s;
    uint8_t buf[1 << 16], d[32];
    size_t n;
    strcpy(out, "unreadable");
    if (!f) return;
    x2sha_init(&s);
    while ((n = fread(buf, 1, sizeof buf, f)) > 0) x2sha_update(&s, buf, n);
    fclose(f);
    x2sha_final(&s, d);
    x2sha_hex(d, out);
}

static void fingerprint(x2fp *fp) {
    int r[4];
    unsigned bf, bm, ef, em;
    char path[MAX_PATH];
    HKEY h;
    memset(fp, 0, sizeof *fp);
    __cpuid(r, 0);
    memcpy(fp->vendor, &r[1], 4); memcpy(fp->vendor + 4, &r[3], 4); memcpy(fp->vendor + 8, &r[2], 4);
    __cpuid(r, 1);
    fp->cpuid1_eax = (unsigned)r[0];
    bf = (r[0] >> 8) & 0xF; bm = (r[0] >> 4) & 0xF; ef = (r[0] >> 20) & 0xFF; em = (r[0] >> 16) & 0xF;
    fp->stepping = r[0] & 0xF;
    fp->family = bf == 0xF ? bf + ef : bf;
    fp->model = (bf == 0xF || bf == 6) ? (bm | (em << 4)) : bm;
    fp->f16c = (r[2] >> 29) & 1;
    if ((r[2] >> 27) & 1) {                                       /* OSXSAVE */
        unsigned long long xcr0 = _xgetbv(0);
        fp->os_zmm = (xcr0 & 0xE6) == 0xE6;
    }
    __cpuidex(r, 7, 0);
    fp->avx2 = (r[1] >> 5) & 1; fp->avx512f = (r[1] >> 16) & 1;
    fp->avx512bw = (r[1] >> 30) & 1; fp->avx512vl = (r[1] >> 31) & 1; fp->avx512vnni = (r[2] >> 11) & 1;
    __cpuid(r, 0x80000000);
    if ((unsigned)r[0] >= 0x80000004) {
        __cpuid((int *)(fp->brand), 0x80000002);
        __cpuid((int *)(fp->brand + 16), 0x80000003);
        __cpuid((int *)(fp->brand + 32), 0x80000004);
    }
    strcpy(fp->ucode_hex, "unknown");
    if (RegOpenKeyExA(HKEY_LOCAL_MACHINE, "HARDWARE\\DESCRIPTION\\System\\CentralProcessor\\0", 0, KEY_READ, &h) == ERROR_SUCCESS) {
        /* REG_BINARY; 4 bytes on the 9950X (Windows 11 26200), 8 bytes on some systems. Both halves are
           reported; on the 9950X the 4-byte value equals "Current Record Version". */
        unsigned char b[8] = {0};
        DWORD n = sizeof b, t = 0;
        if (RegQueryValueExA(h, "Update Revision", NULL, &t, b, &n) == ERROR_SUCCESS && (n == 4 || n == 8)) {
            DWORD i;
            for (i = 0; i < n; i++) sprintf(fp->ucode_hex + 2 * i, "%02x", b[i]);
            fp->ucode_lo = b[0] | (b[1] << 8) | (b[2] << 16) | ((unsigned)b[3] << 24);
            fp->ucode_hi = b[4] | (b[5] << 8) | (b[6] << 16) | ((unsigned)b[7] << 24);
        }
        RegCloseKey(h);
    }
    strcpy(fp->os_build, "unknown");
    if (RegOpenKeyExA(HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion", 0, KEY_READ, &h) == ERROR_SUCCESS) {
        char cb[32] = "", dv[32] = "";
        DWORD n = sizeof cb, ubr = 0, nu = sizeof ubr;
        RegQueryValueExA(h, "CurrentBuild", NULL, NULL, (LPBYTE)cb, &n);
        n = sizeof dv;
        RegQueryValueExA(h, "DisplayVersion", NULL, NULL, (LPBYTE)dv, &n);
        RegQueryValueExA(h, "UBR", NULL, NULL, (LPBYTE)&ubr, &nu);
        sprintf(fp->os_build, "%s.%lu (%s)", cb, (unsigned long)ubr, dv);
        RegCloseKey(h);
    }
    GetModuleFileNameA(NULL, path, sizeof path);
    file_sha256(path, fp->exe_sha256);
    l3_groups(fp->l3_groups, sizeof fp->l3_groups);
}

static void print_fp(FILE *o, const x2fp *fp, int cpu) {
    fprintf(o, "{\"vendor\": \"%s\", \"brand\": \"%s\", \"family\": %u, \"model\": %u, \"stepping\": %u, "
               "\"cpuid1_eax\": \"0x%08x\", \"microcode_update_revision_raw\": \"%s\", \"microcode_lo32\": \"0x%08x\", \"microcode_hi32\": \"0x%08x\", "
               "\"os_build\": \"%s\", \"features\": {\"avx2\": %d, \"avx512f\": %d, \"avx512bw\": %d, \"avx512vl\": %d, "
               "\"avx512vnni\": %d, \"f16c\": %d, \"os_zmm_state\": %d}, \"l3_groups\": \"%s\", \"cpu\": %d, \"harness_exe_sha256\": \"%s\", "
               "\"harness_src_sha256\": \"%s\", \"interp_src_sha256\": \"%s\", \"stub_manifest_sha256\": \"%s\", "
               "\"semantics_bundle\": \"%s\", \"compiler\": \"%s\"}",
            fp->vendor, fp->brand, fp->family, fp->model, fp->stepping, fp->cpuid1_eax, fp->ucode_hex, fp->ucode_lo, fp->ucode_hi,
            fp->os_build, fp->avx2, fp->avx512f, fp->avx512bw, fp->avx512vl, fp->avx512vnni, fp->f16c, fp->os_zmm, fp->l3_groups, cpu,
            fp->exe_sha256, X2_HARNESS_SRC_SHA256, X2_INTERP_SRC_SHA256, X2_STUB_MANIFEST_SHA256, X2_SEMANTICS_BUNDLE,
            X2_COMPILER);
}

static int cpu_ok(const x2fp *fp) {
    return fp->avx2 && fp->avx512f && fp->avx512bw && fp->avx512vl && fp->avx512vnni && fp->f16c && fp->os_zmm;
}

static void pin(int cpu) {
    if (cpu < 0) return;
    if (!SetThreadAffinityMask(GetCurrentThread(), (DWORD_PTR)1 << cpu)) die("SetThreadAffinityMask failed");
    Sleep(0);
}

/* ------------------------------------------------------------------ stub execution */
static DWORD call_stub(x2stubfn fn, const x2case *c, x2out *o) {
    DWORD code = 0;
    __try {
        fn(c, o);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        code = GetExceptionCode();
    }
    return code;
}

static DWORD call_load(const void *p, uint64_t *v) {
    DWORD code = 0;
    __try {
        *v = x2probe_load(p);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        code = GetExceptionCode();
    }
    return code;
}

static uint8_t *g_pages;        /* page 0 read-write, page 1 PAGE_NOACCESS (data, not code) */
static size_t g_page;

static void alloc_pages(void) {
    SYSTEM_INFO si;
    GetSystemInfo(&si);
    g_page = si.dwPageSize;
    g_pages = (uint8_t *)VirtualAlloc(NULL, 2 * g_page, MEM_RESERVE, PAGE_NOACCESS);
    if (!g_pages) die("VirtualAlloc reserve failed");
    if (!VirtualAlloc(g_pages, g_page, MEM_COMMIT, PAGE_READWRITE)) die("VirtualAlloc commit failed");
    if (!VirtualAlloc(g_pages + g_page, g_page, MEM_COMMIT, PAGE_NOACCESS)) die("VirtualAlloc noaccess failed");
}

static const x2stub *stub_by_id(uint32_t id) {
    if (id >= (uint32_t)X2_NSTUBS) return NULL;
    return &X2_STUBS[id];
}

/* ------------------------------------------------------------------ files */
static void hdr_hex(char *dst, const char *hex) { memcpy(dst, hex, 64); }

typedef struct { FILE *f; x2vechdr h; x2sha sha; } vecin;

static void vec_open(vecin *v, const char *path) {
    v->f = fopen(path, "rb");
    if (!v->f) die("cannot open vectors file");
    if (fread(&v->h, 1, sizeof v->h, v->f) != sizeof v->h) die("short vectors header");
    if (memcmp(v->h.magic, X2_VEC_MAGIC, 8) != 0 || v->h.rec_size != X2_VEC_REC) die("bad vectors header");
    if (memcmp(v->h.manifest_sha256, X2_STUB_MANIFEST_SHA256, 64) != 0) die("vectors were generated for another stub manifest");
    x2sha_init(&v->sha);
    x2sha_update(&v->sha, &v->h, sizeof v->h);
}

static int vec_next(vecin *v, x2vecrec *r) {
    size_t n = fread(r, 1, sizeof *r, v->f);
    if (n == 0) return 0;
    if (n != sizeof *r) die("truncated vectors record");
    x2sha_update(&v->sha, r, sizeof *r);
    return 1;
}

static FILE *res_open(const char *path, x2reshdr *h, const char *producer, const char *producer_sha, int cpu) {
    FILE *f = fopen(path, "wb");
    if (!f) die("cannot create results file");
    memset(h, 0, sizeof *h);
    memcpy(h->magic, X2_RES_MAGIC, 8);
    h->version = 1;
    h->rec_size = X2_RES_REC;
    hdr_hex(h->manifest_sha256, X2_STUB_MANIFEST_SHA256);
    strncpy(h->producer, producer, sizeof h->producer - 1);
    hdr_hex(h->producer_sha256, producer_sha);
    h->cpu = (uint32_t)cpu;
    fwrite(h, 1, sizeof *h, f);
    return f;
}

static void res_close(FILE *f, x2reshdr *h, vecin *v, uint64_t n) {
    uint8_t d[32];
    char hex[65];
    x2sha_final(&v->sha, d);
    x2sha_hex(d, hex);
    hdr_hex(h->vectors_sha256, hex);
    h->n = n;
    fseek(f, 0, SEEK_SET);
    fwrite(h, 1, sizeof *h, f);
    fclose(f);
    fclose(v->f);
    printf("{\"records\": %llu, \"vectors_sha256\": \"%s\"}\n", (unsigned long long)n, hex);
}

static int label_is_dev(const x2vechdr *h) {
    return strncmp(h->label, "DEV", 3) == 0 || strncmp(h->label, "SELFTEST", 8) == 0 || strncmp(h->label, "VALID", 5) == 0;
}

static int label_is_valid(const x2vechdr *h) { return strncmp(h->label, "VALID", 5) == 0; }

/* vecfmt.SETS: V1 1, V2 2, V3 3, V4 4, BCAST 5, F-MEMFAULT 6 are budget sets; DEV 7 and VALID 8 are not. */
static int set_is_budget(uint32_t set_id) { return set_id >= 1 && set_id <= 6; }

/* An MXCSR the model covers for an execution: every exception masked, no reserved bit, sticky flags clear. */
static int mxcsr_ok_for_execution(uint32_t m) { return (m & 0x1F80u) == 0x1F80u && !(m & ~0xFFFFu) && !(m & 0x3Fu); }

/* ------------------------------------------------------------------ run / predict */
static int cmd_run(const char *vp, const char *rp, int cpu, int authorised) {
    vecin v;
    x2vecrec r;
    x2resrec o;
    x2reshdr h;
    x2fp fp;
    FILE *f;
    uint64_t n = 0;
    char fpath[1024];
    FILE *fj;
    __declspec(align(64)) x2case c;
    fingerprint(&fp);
    if (!cpu_ok(&fp)) die("CPU lacks a required feature (AVX2, AVX-512F/BW/VL/VNNI, F16C, OS ZMM state)");
    vec_open(&v, vp);
    if (!label_is_dev(&v.h) && !authorised)
        die("refusing to execute a non-development vector set without --collection-authorised (X2 collection rule)");
    if (!authorised) {                       /* the label is self-declared: also refuse any budget-set record */
        vecin pre;
        uint64_t k = 0;
        vec_open(&pre, vp);
        while (vec_next(&pre, &r)) {
            if (set_is_budget(r.set_id)) {
                fprintf(stderr, "x2fuzz: record %llu has budget set id %u\n", (unsigned long long)k, r.set_id);
                die("refusing to execute budget-set records (V1-V4, BCAST, F-MEMFAULT) without --collection-authorised "
                    "(X2 collection rule); development vectors use the sets DEV or VALID");
            }
            k++;
        }
        fclose(pre.f);
    }
    pin(cpu);
    alloc_pages();
    f = res_open(rp, &h, "silicon", fp.exe_sha256, cpu);
    while (vec_next(&v, &r)) {
        const x2stub *s = stub_by_id(r.stub_id);
        DWORD code;
        memset(&o, 0, sizeof o);
        o.index = r.index;
        if (!s) { o.status = X2_ST_BADSTUB; fwrite(&o, 1, sizeof o, f); n++; continue; }
        c = r.c;
        /* Never execute outside the model: an unmasked exception (#XM) or reserved MXCSR bits (#GP). A preset
           sticky flag would hide a flag the table predicts but silicon does not raise (FUZZ-DESIGN sec. 2: the
           flags are clear before each execution), so it is outside the model too, except for VALID sets. */
        if ((c.mxcsr & 0x1F80u) != 0x1F80u || (c.mxcsr & ~0xFFFFu) || ((c.mxcsr & 0x3Fu) && !label_is_valid(&v.h))) {
            o.status = X2_ST_UNMODELED;
            fwrite(&o, 1, sizeof o, f);
            n++;
            continue;
        }
        /* Only the six arithmetic flags, IF and reserved bit 1 reach POPFQ: never TF, DF or AC. */
        c.rflags_in = (c.rflags_in & X2_RFLAGS_OBS) | 0x202u;
        if (s->sem.mem) {
            if (r.flags & X2_FLAG_MEMFAULT) {
                size_t nb = 4 * (size_t)r.memfault_boundary;
                uint8_t *p = g_pages + g_page - nb;
                memcpy(p, &r.c.src2, nb);
                c.mem_ptr = (uint64_t)(uintptr_t)p;
            } else {
                c.mem_ptr = (uint64_t)(uintptr_t)&c.src2;
            }
        }
        code = call_stub(s->fn, &c, &o.o);
        if (code) {
            o.status = X2_ST_EXCEPTION;
            o.exc_code = code;
            _mm_setcsr(X2_MXCSR_DEFAULT);   /* a faulting stub never reached its own restore */
        }
        if (_mm_getcsr() != X2_MXCSR_DEFAULT) die("MXCSR not restored by a stub (harness defect)");
        fwrite(&o, 1, sizeof o, f);
        n++;
    }
    res_close(f, &h, &v, n);
    _snprintf(fpath, sizeof fpath, "%s.fingerprint.json", rp);
    fj = fopen(fpath, "w");
    if (fj) { print_fp(fj, &fp, (int)GetCurrentProcessorNumber()); fputc('\n', fj); fclose(fj); }
    return 0;
}

static int cmd_predict(const char *vp, const char *pp) {
    vecin v;
    x2vecrec r;
    x2resrec o;
    x2reshdr h;
    FILE *f;
    uint64_t n = 0;
    vec_open(&v, vp);
    f = res_open(pp, &h, "interp-c", X2_INTERP_SRC_SHA256, -1);
    while (vec_next(&v, &r)) {
        const x2stub *s = stub_by_id(r.stub_id);
        memset(&o, 0, sizeof o);
        o.index = r.index;
        if (!s) o.status = X2_ST_BADSTUB;
        else if (x2_predict(&s->sem, &r.c, &o.o) != 0) o.status = X2_ST_UNMODELED;
        fwrite(&o, 1, sizeof o, f);
        n++;
    }
    res_close(f, &h, &v, n);
    return 0;
}

/* ------------------------------------------------------------------ exhaustive mode (V5) */
#define X2_EX_DEFAULT_CAP 1000000ll    /* mismatch records written before a sweep stops with status "flood" */

typedef struct {
    const x2stub *s;
    uint32_t mxcsr;
    uint64_t lo, hi, chunk;
    int oracle;                   /* 0 silicon, 1 self (interpreter vs itself), 2 mutant (self-test) */
    int nthreads, tid, cpu;
    uint8_t (*chunk_hash)[32];
    FILE *mf;                     /* mismatches file (shared, guarded) */
    CRITICAL_SECTION *lock;
    volatile LONG64 *nrec;        /* mismatch records so far, all threads */
    LONG64 cap;
    volatile LONG *flood, *bad_predict;
    uint64_t mismatches, executions;
} exjob;

static int ex_lanes(const x2stub *s) { return x2_lanes(&s->sem); }

/* The V5 rows: plain register-form unary conversions and the VPMADDUBSW pair domain. */
static int ex_eligible(const x2stub *s) {
    if (s->sem.maskmode != X2M_NONE || s->sem.mem) return 0;
    return s->sem.builder == X2B_PACKED_FP1 || s->sem.builder == X2B_CVT_F2I_GPR || s->sem.builder == X2B_CVT_I2F_SCALAR ||
           (s->sem.builder == X2B_INT2 && s->sem.fn == X2F_PMADDUBSW);
}

static void ex_fill(const x2stub *s, x2case *c, uint64_t x, int n, uint32_t mxcsr) {
    int i;
    memset(c, 0, sizeof *c);
    memset(&c->dst_old, 0x5A, sizeof c->dst_old);
    c->mxcsr = mxcsr;
    c->gpr_in = 0xDEADBEEFDEADBEEFull;
    for (i = 0; i < n; i++) {
        uint32_t v = (uint32_t)(x + (uint64_t)i);
        if (s->sem.builder == X2B_INT2) {           /* VPMADDUBSW pair domain: (u0,u1,s0,s1) per word */
            c->src1.b[2 * i] = (uint8_t)v; c->src1.b[2 * i + 1] = (uint8_t)(v >> 8);
            c->src2.b[2 * i] = (uint8_t)(v >> 16); c->src2.b[2 * i + 1] = (uint8_t)(v >> 24);
        } else if (s->sem.builder == X2B_CVT_I2F_SCALAR) {
            c->gpr_in = 0xDEADBEEF00000000ull | v;
        } else if (s->sem.src_eb == 16 && s->sem.builder == X2B_PACKED_FP1) {
            c->src1.w[i] = (uint16_t)v;
        } else {
            c->src1.d[i] = v;
        }
    }
}

/* The observable bytes of one execution: the destination by kind (64-bit GPR or full 512-bit register) and
 * MXCSR. Both the stream hash and the mismatch test use exactly these bytes (review 2026-10-16: the first
 * build compared the whole x2out, so on silicon the unmodelled RAX / old-destination bytes made every
 * execution a mismatch). */
static size_t ex_obs(const x2stub *s, const x2out *o, uint8_t *buf) {
    size_t k = 0;
    if (s->sem.dst_kind == X2D_GPR) { memcpy(buf, &o->gpr, 8); k = 8; }
    else { memcpy(buf, &o->dst, 64); k = 64; }
    memcpy(buf + k, &o->mxcsr, 4);
    return k + 4;
}

static DWORD WINAPI ex_worker(LPVOID arg) {
    exjob *j = (exjob *)arg;
    const x2stub *s = j->s;
    int n = ex_lanes(s), dom_n = n;
    uint64_t ci, nchunks = (j->hi - j->lo + j->chunk - 1) / j->chunk;
    __declspec(align(64)) x2case c;
    x2out so, po;
    if (s->sem.builder == X2B_CVT_F2I_GPR || s->sem.builder == X2B_CVT_I2F_SCALAR) dom_n = 1;
    pin(j->cpu);
    for (ci = (uint64_t)j->tid; ci < nchunks; ci += (uint64_t)j->nthreads) {
        uint64_t a = j->lo + ci * j->chunk, b = a + j->chunk, x;
        x2sha sh;
        if (*j->flood || *j->bad_predict) break;
        if (b > j->hi) b = j->hi;
        x2sha_init(&sh);
        for (x = a; x < b; x += (uint64_t)dom_n) {
            int m = (int)((b - x) < (uint64_t)dom_n ? (b - x) : (uint64_t)dom_n), i;
            uint8_t sb[80], pb[80], inb[64 * 4];
            size_t ks, kp;
            ex_fill(s, &c, x, m, j->mxcsr);
            if (x2_predict(&s->sem, &c, &po) != 0) { InterlockedExchange(j->bad_predict, 1); break; }
            if (j->oracle == 0) {
                DWORD code = call_stub(s->fn, &c, &so);
                if (code) die("exception in exhaustive mode");
            } else {
                so = po;
                if (j->oracle == 2 && (x % 4096) == 0) {            /* seeded mutant for the self-test */
                    if (s->sem.dst_kind == X2D_GPR) so.gpr ^= 1; else so.dst.d[0] ^= 1;
                }
            }
            for (i = 0; i < m; i++) { uint32_t v = (uint32_t)(x + (uint64_t)i); memcpy(inb + 4 * i, &v, 4); }
            x2sha_update(&sh, inb, 4 * (size_t)m);
            ks = ex_obs(s, &so, sb);
            kp = ex_obs(s, &po, pb);
            x2sha_update(&sh, sb, ks);
            j->executions++;
            if (ks != kp || memcmp(sb, pb, ks) != 0) {
                uint32_t rec[8];
                int lane = -1;
                LONG64 nr;
                if (s->sem.dst_kind == X2D_GPR) lane = so.gpr != po.gpr ? 0 : -1;
                else for (i = 0; i < 16; i++) if (so.dst.d[i] != po.dst.d[i]) { lane = i; break; }
                rec[0] = (uint32_t)x; rec[1] = (uint32_t)lane;
                rec[2] = s->sem.dst_kind == X2D_GPR ? (uint32_t)so.gpr : (lane >= 0 ? so.dst.d[lane] : 0);
                rec[3] = s->sem.dst_kind == X2D_GPR ? (uint32_t)po.gpr : (lane >= 0 ? po.dst.d[lane] : 0);
                rec[4] = so.mxcsr; rec[5] = po.mxcsr; rec[6] = (uint32_t)m; rec[7] = 0;
                j->mismatches++;
                nr = InterlockedIncrement64(j->nrec);
                if (nr <= j->cap) {
                    EnterCriticalSection(j->lock);
                    fwrite(rec, 4, 8, j->mf);
                    LeaveCriticalSection(j->lock);
                }
                if (nr >= j->cap) { InterlockedExchange(j->flood, 1); break; }
            }
        }
        if (*j->flood || *j->bad_predict) break;           /* this chunk is incomplete: its hash stays zero */
        x2sha_final(&sh, j->chunk_hash[ci]);
    }
    return 0;
}

/* Returns 0 (complete) or 1 (flood: the mismatch-record cap was reached and the sweep stopped early; the
 * stream hash then covers an incomplete stream and must not be compared). Dies if the interpreter reports
 * any input of the sweep as outside the model. */
static int run_exhaustive(const x2stub *s, uint32_t mxcsr, uint64_t lo, uint64_t hi, int oracle, int nthreads,
                          const int *cpus, const char *outdir, char stream_hex[65], uint64_t *mism, int quiet, LONG64 cap) {
    uint64_t chunk = (s->sem.src_eb == 16 && s->sem.builder == X2B_PACKED_FP1) ? 65536 : (1ull << 24);
    uint64_t nchunks = (hi - lo + chunk - 1) / chunk, i;
    uint8_t (*hashes)[32] = (uint8_t (*)[32])calloc((size_t)nchunks, 32), d[32];
    exjob jobs[64];
    HANDLE th[64];
    CRITICAL_SECTION lock;
    char path[1024];
    FILE *mf;
    x2sha all;
    int t;
    volatile LONG64 nrec = 0;
    volatile LONG flood = 0, bad_predict = 0;
    DWORD t0 = GetTickCount();
    if (nthreads < 1 || nthreads > 64) die("bad thread count");
    if (hi <= lo) die("exhaustive range is empty");
    if (cap < 1) die("bad --max-mismatch-records");
    {                                                   /* refuse a sweep the interpreter does not model */
        __declspec(align(64)) x2case c0;
        x2out p0;
        ex_fill(s, &c0, lo, 1, mxcsr);
        if (x2_predict(&s->sem, &c0, &p0) != 0) die("the interpreter reports this stub / MXCSR as outside the model");
    }
    CreateDirectoryA(outdir, NULL);
    _snprintf(path, sizeof path, "%s\\mismatches.bin", outdir);
    mf = fopen(path, "wb");
    if (!mf || !hashes) die("cannot create exhaustive outputs");
    InitializeCriticalSection(&lock);
    for (t = 0; t < nthreads; t++) {
        memset(&jobs[t], 0, sizeof jobs[t]);
        jobs[t].s = s; jobs[t].mxcsr = mxcsr; jobs[t].lo = lo; jobs[t].hi = hi; jobs[t].chunk = chunk;
        jobs[t].oracle = oracle; jobs[t].nthreads = nthreads; jobs[t].tid = t; jobs[t].cpu = cpus ? cpus[t] : -1;
        jobs[t].chunk_hash = hashes; jobs[t].mf = mf; jobs[t].lock = &lock;
        jobs[t].nrec = &nrec; jobs[t].cap = cap; jobs[t].flood = &flood; jobs[t].bad_predict = &bad_predict;
        th[t] = CreateThread(NULL, 0, ex_worker, &jobs[t], 0, NULL);
    }
    WaitForMultipleObjects((DWORD)nthreads, th, TRUE, INFINITE);
    fclose(mf);
    if (bad_predict) die("the interpreter reported an input of this sweep as outside the model");
    x2sha_init(&all);
    for (i = 0; i < nchunks; i++) x2sha_update(&all, hashes[i], 32);
    x2sha_final(&all, d);
    x2sha_hex(d, stream_hex);
    *mism = 0;
    {
        uint64_t ex = 0;
        for (t = 0; t < nthreads; t++) { *mism += jobs[t].mismatches; ex += jobs[t].executions; CloseHandle(th[t]); }
        if (!quiet) {
            _snprintf(path, sizeof path, "%s\\summary.json", outdir);
            mf = fopen(path, "w");
            if (mf) {
                x2fp fp;
                fingerprint(&fp);
                fprintf(mf, "{\"stub\": \"%s\", \"iform\": \"%s\", \"variant\": \"%s\", \"mxcsr\": \"0x%04x\", "
                            "\"lo\": \"0x%llx\", \"hi\": \"0x%llx\", \"oracle\": \"%s\", \"threads\": %d, \"executions\": %llu, "
                            "\"mismatches\": %llu, \"status\": \"%s\", \"max_mismatch_records\": %lld, \"stream_sha256\": \"%s\", "
                            "\"stream_complete\": %s, \"chunk\": %llu, \"seconds\": %.3f, \"fingerprint\": ",
                        s->name, s->iform, s->variant, mxcsr, (unsigned long long)lo, (unsigned long long)hi,
                        oracle == 0 ? "silicon" : (oracle == 1 ? "self" : "mutant"), nthreads, (unsigned long long)ex,
                        (unsigned long long)*mism, flood ? "flood" : "complete", (long long)cap, stream_hex,
                        flood ? "false" : "true", (unsigned long long)chunk, (GetTickCount() - t0) / 1000.0);
                print_fp(mf, &fp, -1);
                fprintf(mf, "}\n");
                fclose(mf);
            }
        }
    }
    DeleteCriticalSection(&lock);
    free(hashes);
    return flood ? 1 : 0;
}

static const x2stub *find_stub(const char *iform, const char *variant) {
    int i;
    for (i = 0; i < X2_NSTUBS; i++)
        if (strcmp(X2_STUBS[i].iform, iform) == 0 && strcmp(X2_STUBS[i].variant, variant) == 0) return &X2_STUBS[i];
    return NULL;
}

/* ------------------------------------------------------------------ self-test */
typedef struct { int op; uint32_t a, b, mxcsr; uint32_t want, wflags; const char *label; } kat;
enum { K_ADD = 1, K_SUB, K_MUL, K_DIV, K_MAX, K_MIN, K_I2F, K_F2I, K_F2IT, K_H2F };

/* A few vectors transcribed from semantics/selftest.py (labels as there); the full hand-vector set
 * runs through `predict` in devsmoke.py. */
static const kat KATS[] = {
    {K_ADD, 0x3F800000, 0x33800000, 0x1F80, 0x3F800000, X2_PE, "A1 1+2^-24 RNE"},
    {K_ADD, 0x3F800001, 0x33800000, 0x1F80, 0x3F800002, X2_PE, "A2 (1+2^-23)+2^-24 RNE -> even 1+2^-22"},
    {K_ADD, 0x3F800000, 0x33800000, 0x5F80, 0x3F800001, X2_PE, "A3 1+2^-24 RU"},
    {K_ADD, 0x00000000, 0x80000000, 0x3F80, 0x80000000, 0, "A5 +0 + -0 RD"},
    {K_ADD, 0x7FC01234, 0xFFC05678, 0x1F80, 0x7FC01234, 0, "A6 QNaN,QNaN -> src1"},
    {K_ADD, 0x3F800000, 0x7F800001, 0x1F80, 0x7FC00001, X2_IE, "A6 1.0,SNaN -> quiet(src2)"},
    {K_ADD, 0x7F800000, 0xFF800000, 0x1F80, 0xFFC00000, X2_IE, "A7 +inf + -inf"},
    {K_MUL, 0x7F7FFFFF, 0x40000000, 0x7F80, 0x7F7FFFFF, X2_OE | X2_PE, "A8 MAX*2 RZ"},
    {K_MUL, 0x00000001, 0x3F000000, 0x1F80, 0x00000000, X2_DE | X2_UE | X2_PE, "A11 2^-149*0.5 tie -> +0 (even)"},
    {K_MUL, 0x00800000, 0x3F000000, 0x9F80, 0x00000000, X2_UE | X2_PE, "A12 FTZ 2^-126*0.5"},
    {K_MUL, 0x00800001, 0x3F7FFFFE, 0x1F80, 0x00800000, X2_PE, "A13 band, FTZ=0"},
    {K_MUL, 0x00800000, 0x3F7FFFFF, 0x1F80, 0x00800000, X2_UE | X2_PE, "A13b tiny, rounds up to MIN_NORMAL"},
    {K_ADD, 0x00000001, 0x00000000, 0x1FC0, 0x00000000, 0, "A15 den+0 DAZ=1"},
    {K_DIV, 0x3F800000, 0x40400000, 0x1F80, 0x3EAAAAAB, X2_PE, "A16 1/3"},
    {K_DIV, 0x3F800000, 0x00000001, 0x1F80, 0x7F800000, X2_DE | X2_OE | X2_PE, "A16 1/2^-149 overflow"},
    {K_DIV, 0x00000001, 0x00000000, 0x1F80, 0x7F800000, X2_DE | X2_ZE, "B6 den / +0: DE and ZE both recorded"},
    {K_MAX, 0x00000000, 0x80000000, 0x1F80, 0x80000000, 0, "B1 max(+0,-0) -> src2"},
    {K_MAX, 0x3F800000, 0x7F800001, 0x1F80, 0x7F800001, X2_IE, "B2 max(1,SNaN) -> SNaN NOT quieted"},
    {K_MAX, 0x00000000, 0x80000001, 0x1FC0, 0x80000000, 0, "B4 max(0,-den) DAZ=1 -> -0 (UNCERTAIN F-DAZ-SEL)"},
    {K_I2F, 16777217, 0, 0x1F80, 0x4B800000, X2_PE, "D1 2^24+1 RNE -> 2^24"},
    {K_I2F, 0x80000000, 0, 0x1F80, 0xCF000000, 0, "D1 -2^31 exact"},
    {K_F2I, 0x40200000, 0, 0x1F80, 0x00000002, X2_PE, "D2 2.5 RNE -> 2"},
    {K_F2I, 0x4F000000, 0, 0x1F80, 0x80000000, X2_IE, "D2 2^31 -> indefinite"},
    {K_F2I, 0xCF000000, 0, 0x1F80, 0x80000000, 0, "D2 -2^31 exact (not indefinite)"},
    {K_F2I, 0x00000001, 0, 0x5F80, 0x00000001, X2_PE, "D2 den RU DAZ=0 -> 1 (no DE)"},
    {K_F2IT, 0xC0300000, 0, 0x1F80, 0xFFFFFFFE, X2_PE, "D3 trunc -2.75"},
    {K_H2F, 0x03FF, 0, 0x1F80, 0x387FC000, 0, "D4 f16 max subnormal"},
    {K_H2F, 0x7C01, 0, 0x1F80, 0x7FC02000, X2_IE, "D4 f16 SNaN quieted"},
    {K_H2F, 0x0001, 0, 0x1FC0, 0x33800000, 0, "D4 f16 subnormal ignores DAZ"},
};

static void scratch_path(char *out, size_t cap, const char *scratch, const char *leaf) {
    _snprintf(out, cap, "%s\\%s", scratch, leaf);
    out[cap - 1] = 0;
}

static int selftest(int cpu, const char *scratch) {
    x2fp fp;
    int i;
    char sp[1024];
    printf("== x2fuzz selftest (scratch directory %s)\n", scratch);
    CreateDirectoryA(scratch, NULL);
    /* 1. SHA-256 known answers (FIPS 180-4) */
    {
        static const char *msg[3] = {"", "abc", "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"};
        static const char *want[3] = {"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                                      "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
                                      "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"};
        for (i = 0; i < 3; i++) {
            x2sha s;
            uint8_t d[32];
            char hx[65];
            x2sha_init(&s); x2sha_update(&s, msg[i], strlen(msg[i])); x2sha_final(&s, d); x2sha_hex(d, hx);
            CHECK(strcmp(hx, want[i]) == 0, "sha256 KAT %d", i);
        }
    }
    /* 2. ABI layout shared with the stubs */
    CHECK(sizeof(x2case) == 256 && sizeof(x2out) == 128, "case/out sizes");
    CHECK(offsetof(x2case, k) == 8 && offsetof(x2case, mem_ptr) == 16 && offsetof(x2case, rflags_in) == 24 &&
          offsetof(x2case, gpr_in) == 32 && offsetof(x2case, kdst_in) == 40 && offsetof(x2case, src1) == 64 &&
          offsetof(x2case, src2) == 128 && offsetof(x2case, dst_old) == 192, "case offsets");
    CHECK(offsetof(x2out, mxcsr) == 64 && offsetof(x2out, rflags) == 72 && offsetof(x2out, kdst) == 80 &&
          offsetof(x2out, gpr) == 88, "out offsets");
    CHECK(sizeof(x2vecrec) == X2_VEC_REC && sizeof(x2resrec) == X2_RES_REC && sizeof(x2vechdr) == 256 &&
          sizeof(x2reshdr) == 256, "file record sizes");
    /* 3. interpreter known answers */
    for (i = 0; i < (int)(sizeof KATS / sizeof KATS[0]); i++) {
        const kat *k = &KATS[i];
        x2env e;
        uint32_t fl = 0, r = 0;
        x2_env_make(&e, k->mxcsr, -1, 0);
        switch (k->op) {
        case K_ADD: r = x2_add(k->a, k->b, &e, &fl); break;
        case K_SUB: r = x2_sub(k->a, k->b, &e, &fl); break;
        case K_MUL: r = x2_mul(k->a, k->b, &e, &fl); break;
        case K_DIV: r = x2_div(k->a, k->b, &e, &fl); break;
        case K_MAX: r = x2_max(k->a, k->b, &e, &fl); break;
        case K_MIN: r = x2_min(k->a, k->b, &e, &fl); break;
        case K_I2F: r = x2_cvt_i2f(k->a, &e, &fl); break;
        case K_F2I: r = x2_cvt_f2i(k->a, &e, 0, &fl); break;
        case K_F2IT: r = x2_cvt_f2i(k->a, &e, 1, &fl); break;
        case K_H2F: r = x2_cvt_h2f(k->a, &e, &fl); break;
        }
        CHECK(r == k->want && fl == k->wflags, "interp KAT %s: got %08X/%02X want %08X/%02X", k->label, r, fl, k->want, k->wflags);
    }
    /* 4. stub table */
    {
        int bad = 0, keyok = 0;
        for (i = 0; i < X2_NSTUBS; i++) {
            const x2stub *s = &X2_STUBS[i];
            if (s->id != i || !s->fn || s->sem.builder < 1 || s->sem.builder > 10 || s->nbytes < 2 || s->nbytes > 15) bad++;
            keyok += s->key_ok;
        }
        CHECK(bad == 0, "stub table integrity (%d bad)", bad);
        printf("stubs: %d, decoded iform == entry key: %d, manifest %s\n", X2_NSTUBS, keyok, X2_STUB_MANIFEST_SHA256);
    }
    /* 5. CPU */
    fingerprint(&fp);
    CHECK(cpu_ok(&fp), "CPU features (AVX2, AVX-512F/BW/VL/VNNI, F16C, OS ZMM state)");
    pin(cpu);
    printf("fingerprint: ");
    print_fp(stdout, &fp, (int)GetCurrentProcessorNumber());
    printf("\n");
    if (!cpu_ok(&fp)) return 1;
    /* 6. plumbing probes (data movement only) */
    {
        static const uint32_t mx[] = {0x1F80, 0x1FBF, 0x3F80, 0x5F80, 0x7F80, 0x1FC0, 0x9F80, 0xFFC0};
        for (i = 0; i < (int)(sizeof mx / sizeof mx[0]); i++) {
            uint32_t io[2] = {mx[i], 0};
            x2probe_mxcsr(io);
            CHECK(io[1] == mx[i], "MXCSR round trip %04X -> %04X", mx[i], io[1]);
            CHECK(_mm_getcsr() == X2_MXCSR_DEFAULT, "MXCSR restored after probe");
        }
    }
    {
        __declspec(align(64)) x2case c;
        x2out o;
        uint64_t st = 0x9E3779B97F4A7C15ull;
        int t;
        for (t = 0; t < 64; t++) {
            uint8_t *p = (uint8_t *)&c;
            size_t j;
            for (j = 0; j < sizeof c; j++) { st ^= st << 13; st ^= st >> 7; st ^= st << 17; p[j] = (uint8_t)st; }
            c.mxcsr = 0x1F80 | (t & 1 ? 0x6000 : 0) | (t & 2 ? 0x8040 : 0);
            c.rflags_in = 0x202 | (st & X2_RFLAGS_OBS);
            memset(&o, 0, sizeof o);
            x2probe_copy_evex(&c, &o);
            CHECK(memcmp(&o.dst, &c.src1, 64) == 0, "EVEX path: dst == src1 (trial %d)", t);
            CHECK(o.kdst == c.k, "k path (trial %d)", t);
            CHECK(o.gpr == c.gpr_in, "GPR path (trial %d)", t);
            CHECK((o.rflags & X2_RFLAGS_OBS) == (c.rflags_in & X2_RFLAGS_OBS), "RFLAGS path (trial %d)", t);
            CHECK(o.mxcsr == c.mxcsr, "MXCSR path %04X vs %04X", o.mxcsr, c.mxcsr);
            memset(&o, 0, sizeof o);
            x2probe_copy_vex(&c, &o);
            CHECK(memcmp(&o.dst, &c.src2, 64) == 0, "VEX path: dst == src2 (trial %d)", t);
            CHECK(_mm_getcsr() == X2_MXCSR_DEFAULT, "MXCSR restored");
        }
    }
    /* 7. fault capture on a PAGE_NOACCESS data page (F-MEMFAULT machinery) */
    {
        uint64_t v = 0;
        alloc_pages();
        CHECK(call_load(g_pages + g_page - 8, &v) == 0, "load from the RW page");
        CHECK(call_load(g_pages + g_page, &v) == EXCEPTION_ACCESS_VIOLATION, "load from the NOACCESS page faults");
        CHECK(call_load(g_pages + g_page - 4, &v) == EXCEPTION_ACCESS_VIOLATION, "straddling load faults");
    }
    /* 8. exhaustive engine with the interpreter as oracle (no silicon) */
    {
        const x2stub *s = find_stub("VCVTPS2DQ_ZMMi32_MASKmskw_ZMMf32_AVX512", "plain");
        char h1[65], h2[65], h3[65], h4[65];
        uint64_t m1 = 0, m2 = 0, m3 = 0, m4 = 0;
        int cpus2[2] = {cpu, cpu}, st3, st4;
        CHECK(s != NULL, "exhaustive self-test stub present");
        if (s) {
            uint64_t lo = 0x3F000000ull, hi = lo + (1ull << 20);
            scratch_path(sp, sizeof sp, scratch, "ex_selftest_1");
            run_exhaustive(s, 0x1F80, lo, hi, 1, 1, cpu >= 0 ? cpus2 : NULL, sp, h1, &m1, 1, X2_EX_DEFAULT_CAP);
            scratch_path(sp, sizeof sp, scratch, "ex_selftest_2");
            run_exhaustive(s, 0x1F80, lo, hi, 1, 2, cpu >= 0 ? cpus2 : NULL, sp, h2, &m2, 1, X2_EX_DEFAULT_CAP);
            scratch_path(sp, sizeof sp, scratch, "ex_selftest_3");
            st3 = run_exhaustive(s, 0x1F80, lo, hi, 2, 2, cpu >= 0 ? cpus2 : NULL, sp, h3, &m3, 1, X2_EX_DEFAULT_CAP);
            scratch_path(sp, sizeof sp, scratch, "ex_selftest_4");
            st4 = run_exhaustive(s, 0x1F80, lo, hi, 2, 1, cpu >= 0 ? cpus2 : NULL, sp, h4, &m4, 1, 10);
            CHECK(m1 == 0 && m2 == 0, "self oracle: no mismatches");
            CHECK(strcmp(h1, h2) == 0, "stream hash independent of thread count");
            CHECK(m3 == (hi - lo) / 4096 && st3 == 0, "seeded mutant: %llu mismatches, want %llu", (unsigned long long)m3,
                  (unsigned long long)((hi - lo) / 4096));
            CHECK(strcmp(h1, h3) != 0, "seeded mutant changes the stream hash");
            CHECK(st4 == 1 && m4 == 10, "mismatch-record cap: status %d, %llu records, want flood at 10", st4,
                  (unsigned long long)m4);
            printf("exhaustive self-test: stream %s, mutant mismatches %llu, cap test status %s\n", h1,
                   (unsigned long long)m3, st4 ? "flood" : "complete");
        }
    }
    /* 9. Harness plumbing check of the exhaustive engine's SILICON path (oracle 0). Development check, not data
     *    under the X2 record: every V5-eligible stub executes on silicon over the 4,096 fixed inputs
     *    0x3F000000..0x3F000FFF under MXCSR 0x1F80, and the in-process compare must find 0 mismatches and the
     *    same stream hash as the interpreter-as-oracle run. Added after the 2026-10-16 review, which showed that
     *    the self oracle (so = po) never exercised the silicon path. */
    {
        int nst = 0, nbad = 0;
        int cpus1[1] = {cpu};
        for (i = 0; i < X2_NSTUBS; i++) {
            const x2stub *s = &X2_STUBS[i];
            char hs[65], hp[65];
            uint64_t ms = 0, mp = 0;
            int st;
            if (!ex_eligible(s)) continue;
            scratch_path(sp, sizeof sp, scratch, "ex_plumb");
            st = run_exhaustive(s, 0x1F80, 0x3F000000ull, 0x3F001000ull, 0, 1, cpu >= 0 ? cpus1 : NULL, sp, hs, &ms, 1,
                                X2_EX_DEFAULT_CAP);
            run_exhaustive(s, 0x1F80, 0x3F000000ull, 0x3F001000ull, 1, 1, cpu >= 0 ? cpus1 : NULL, sp, hp, &mp, 1,
                           X2_EX_DEFAULT_CAP);
            nst++;
            if (ms || st || strcmp(hs, hp) != 0) {
                nbad++;
                printf("plumbing: %s %s %s: %llu mismatches, stream %s vs interpreter %s\n", s->name, s->iform, s->variant,
                       (unsigned long long)ms, hs, hp);
            }
        }
        CHECK(nst > 0 && nbad == 0, "exhaustive silicon plumbing: %d of %d V5 stubs disagree", nbad, nst);
        printf("exhaustive silicon plumbing check (development): %d V5-eligible stubs x 4,096 inputs, %d disagreeing\n",
               nst, nbad);
    }
    printf("selftest: %s (%d failures)\n", g_fail ? "FAIL" : "PASS", g_fail);
    return g_fail ? 1 : 0;
}

/* ------------------------------------------------------------------ main */
static const char *arg(int argc, char **argv, const char *name) {
    int i;
    for (i = 1; i < argc - 1; i++) if (strcmp(argv[i], name) == 0) return argv[i + 1];
    return NULL;
}
static int flag(int argc, char **argv, const char *name) {
    int i;
    for (i = 1; i < argc; i++) if (strcmp(argv[i], name) == 0) return 1;
    return 0;
}

int main(int argc, char **argv) {
    const char *cs = argc > 1 ? arg(argc, argv, "--cpu") : NULL;
    int cpu = cs ? atoi(cs) : -1;
    if (argc < 2) { fprintf(stderr, "usage: see x2fuzz.c header\n"); return 2; }
    if (_mm_getcsr() != X2_MXCSR_DEFAULT) die("process MXCSR is not 0x1F80 at entry");
    if (strcmp(argv[1], "selftest") == 0) {
        const char *sc = arg(argc, argv, "--scratch");
        char def[MAX_PATH + 32];
        if (!sc) {
            DWORD n = GetTempPathA(MAX_PATH, def);        /* %TEMP%, with a trailing backslash */
            if (n == 0 || n > MAX_PATH) strcpy(def, ".\\");
            strcat(def, "x2fuzz_selftest");
            sc = def;
        }
        return selftest(cpu, sc);
    }
    if (strcmp(argv[1], "fingerprint") == 0) {
        x2fp fp;
        fingerprint(&fp);
        pin(cpu);
        print_fp(stdout, &fp, (int)GetCurrentProcessorNumber());
        printf("\n");
        return 0;
    }
    if (strcmp(argv[1], "list") == 0) {
        int i;
        for (i = 0; i < X2_NSTUBS; i++) {
            const x2stub *s = &X2_STUBS[i];
            printf("{\"id\": %d, \"name\": \"%s\", \"iform\": \"%s\", \"decoded\": \"%s\", \"variant\": \"%s\", \"key_ok\": %d, \"bytes\": \"%s\"}\n",
                   s->id, s->name, s->iform, s->decoded_iform, s->variant, s->key_ok, s->bytes_hex);
        }
        return 0;
    }
    if (strcmp(argv[1], "run") == 0 && argc >= 4) return cmd_run(argv[2], argv[3], cpu, flag(argc, argv, "--collection-authorised"));
    if (strcmp(argv[1], "predict") == 0 && argc >= 4) return cmd_predict(argv[2], argv[3]);
    if (strcmp(argv[1], "exhaustive") == 0) {
        const char *sid = arg(argc, argv, "--stub"), *mx = arg(argc, argv, "--mxcsr"), *lo = arg(argc, argv, "--lo"),
                   *hi = arg(argc, argv, "--hi"), *out = arg(argc, argv, "--out"), *orc = arg(argc, argv, "--oracle"),
                   *nt = arg(argc, argv, "--threads"), *cl = arg(argc, argv, "--cpus"),
                   *capstr = arg(argc, argv, "--max-mismatch-records");
        int oracle = 0, nthreads = nt ? atoi(nt) : 1, cpus[64], nc = 0, st;
        char hex[65];
        uint64_t mism = 0;
        uint32_t mxv;
        LONG64 cap = capstr ? (LONG64)_strtoi64(capstr, NULL, 10) : X2_EX_DEFAULT_CAP;
        const x2stub *s;
        const char *sif = arg(argc, argv, "--iform"), *svar = arg(argc, argv, "--variant");
        if ((!sid && !(sif && svar)) || !mx || !lo || !hi || !out)
            die("exhaustive needs --stub ID (or --iform IFORM --variant VARIANT) --mxcsr --lo --hi --out");
        s = sid ? stub_by_id((uint32_t)atoi(sid)) : find_stub(sif, svar);
        if (!s || s->sem.maskmode != X2M_NONE || s->sem.mem) die("exhaustive mode needs a plain register-form stub");
        if (!ex_eligible(s))
            die("exhaustive mode covers the V5 rows only: unary conversions and the VPMADDUBSW pair domain");
        mxv = (uint32_t)strtoul(mx, NULL, 16);
        if (!mxcsr_ok_for_execution(mxv))
            die("--mxcsr must mask every exception (bits 12:7 set), have no reserved bit and no sticky flag (bits 5:0 clear)");
        if (orc && strcmp(orc, "self") == 0) oracle = 1;
        else if (orc && strcmp(orc, "mutant") == 0) oracle = 2;
        else if (orc && strcmp(orc, "silicon") != 0) die("--oracle must be silicon, self or mutant");
        if (oracle == 0 && !flag(argc, argv, "--collection-authorised"))
            die("refusing a silicon exhaustive sweep without --collection-authorised (X2 collection rule)");
        if (cl) {
            const char *p = cl;
            while (*p && nc < 64) { cpus[nc++] = atoi(p); while (*p && *p != ',') p++; if (*p) p++; }
            if (nc < nthreads) die("--cpus lists fewer CPUs than --threads");
        }
        st = run_exhaustive(s, mxv, _strtoui64(lo, NULL, 16), _strtoui64(hi, NULL, 16), oracle, nthreads, nc ? cpus : NULL, out,
                            hex, &mism, 0, cap);
        printf("{\"stream_sha256\": \"%s\", \"mismatches\": %llu, \"status\": \"%s\"}\n", hex, (unsigned long long)mism,
               st ? "flood" : "complete");
        return st ? 3 : 0;
    }
    fprintf(stderr, "unknown command\n");
    return 2;
}
