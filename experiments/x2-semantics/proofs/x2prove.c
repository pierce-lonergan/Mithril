/* x2prove.c -- exhaustive enumeration routes for the rules of RULES.md sec. 3.1 (rules.v1 draft 2).
 *
 * Revised 2026-10-16 after the same-family, independent-context review of the first run. What each route
 * evaluates is stated per rule in its "route_kind":
 *   table        both sides through the C reference interpreter of the table (../harness/x2ref.c, validated
 *                against the Python reference on 1,000,006 lane cases): lane functions (x2_min, x2_cmp_pred,
 *                x2_comis, x2_maddubs_word, x2_dpbusd_lane, ...) or whole instructions through x2_predict and
 *                the table's EVEX masking function x2_masked;
 *   table+translit  as "table", with a data-movement operation that has no table entry yet transliterated from
 *                semantics/int_ops.py (BLENDVPS sign-bit select, bitwise AND, PABSB/PSIGNB, packs);
 *   algebraic    an integer identity with no table operation on either side (R15, R16): it cannot fail for
 *                the stated ranges and is reported as the per-element algebra, not as a table route;
 *   differential the C transliteration of an SMT lane formula of z3_rules.py / z3_int.py against the table's C
 *                lane function (DIFF-*), or a sha256 over a transliteration's outputs for the Python side to
 *                compare with semantics/int_ops.py (HASH-*; proofs/int_differential.py).
 * The first run's "generic" R08-R11 loops compared transliterations with their own definitions and are gone.
 *
 * Environments: --mxcsr takes a list; every rule whose Env column is environment-dependent (R04-R11, R19,
 * R20, R21) runs once per value and writes one entry per (rule, mxcsr). Integer rules and the DIFF/HASH
 * entries do not read MXCSR and run once. R19-RD/RU/RZ always use RC = RD/RU/RZ with DAZ = FTZ = 0.
 * No silicon instruction is executed: every result is a statement about the table.
 *
 *   x2prove OUT.json [--threads 1|2] [--only R04,R19-RZ] [--mxcsr 1f80,1fc0,...]
 *
 * --only matches rule names exactly. For each entry: inputs enumerated, inputs meeting the side condition,
 * failures inside it (0 = the route agrees with the rule), failures outside it (whether the side condition
 * is load-bearing), the first counterexamples, the wall time.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "build_info.h"
#include "x2ref.h"
#include "x2sha256.h"

#ifndef X2_PROVE_SRC_SHA256
#define X2_PROVE_SRC_SHA256 "unknown"
#endif

#define NAN32(v) (((v) & 0x7F800000u) == 0x7F800000u && ((v) & 0x7FFFFFu))
#define DEN32(v) (((v) & 0x7F800000u) == 0 && ((v) & 0x7FFFFFu))
#define CANON 0x7FC00000u
#define C127 0x42FE0000u
#define CM127 0xC2FE0000u
#define MAGIC 0x4B400000u   /* 1.5 * 2^23 */

typedef struct {
    uint64_t inputs, cond, fail_in, fail_out, extra[4];
    uint64_t cex[4][3];
    int ncex;
    uint8_t hash[32];
} acc_t;

typedef struct {
    int rule, tid, nthreads;
    x2env E;
    acc_t a;
} job_t;

static void note(acc_t *a, int in_cond, int ok, uint64_t x, uint64_t lhs, uint64_t rhs) {
    a->inputs++;
    if (in_cond) a->cond++;
    if (!ok) {
        if (in_cond) a->fail_in++; else a->fail_out++;
        if (in_cond && a->ncex < 4) { a->cex[a->ncex][0] = x; a->cex[a->ncex][1] = lhs; a->cex[a->ncex][2] = rhs; a->ncex++; }
    }
}

/* ------------------------------------------------------------------ transliterations (no table entry yet) */
static uint32_t blendvps_lane(uint32_t a, uint32_t b, uint32_t m) { return (m >> 31) ? b : a; }   /* int_ops.blendvps */
static int32_t sat16(int64_t v) { return v > 32767 ? 32767 : (v < -32768 ? -32768 : (int32_t)v); }
static int32_t sat8(int32_t v) { return v > 127 ? 127 : (v < -128 ? -128 : v); }
static uint8_t pabsb(uint8_t x) { int8_t s = (int8_t)x; return (uint8_t)(s < 0 ? -s : s); }        /* int_ops.pabsb */
static uint8_t psignb(uint8_t a, uint8_t b) {                                                      /* int_ops.psignb */
    int8_t sb = (int8_t)b;
    return sb < 0 ? (uint8_t)(-(int)(int8_t)a) : (sb == 0 ? 0 : a);
}

/* ------------------------------------------------------------------ table instructions through x2_predict */
static x2sem sem_cmp(int builder, int vl, int imm) {
    x2sem s;
    memset(&s, 0, sizeof s);
    s.builder = builder; s.fn = X2F_CMP; s.encoding = builder == X2B_CMP_K ? X2E_EVEX : X2E_VEX; s.vl = vl;
    s.maskmode = X2M_NONE; s.er = -1; s.imm = imm; s.src_eb = 32; s.dst_eb = 32;
    s.dst_kind = builder == X2B_CMP_K ? X2D_K : X2D_VEC;
    return s;
}

enum { R04 = 0, R05, R06, R07, R08, R09, R10, R11, R12, R13, R14, R15, R16, R17, R19, R19RD, R19RU, R19RZ, R20, R21,
       DIFF_MADDUBS, DIFF_DPBUSD, HASH_PABS_PSIGN, HASH_PACKS, NRULES };
static const char *NAMES[NRULES] = {"R04", "R05", "R06", "R07", "R08", "R09", "R10", "R11", "R12", "R13", "R14", "R15",
                                    "R16", "R17", "R19", "R19-RD", "R19-RU", "R19-RZ", "R20", "R21", "DIFF-MADDUBS",
                                    "DIFF-DPBUSD", "HASH-PABS-PSIGN", "HASH-PACKS"};
static const char *KIND[NRULES] = {"table", "table", "table", "table", "table+translit", "table+translit", "table",
                                   "table", "table", "table", "table+translit", "algebraic", "algebraic", "table+translit",
                                   "table", "table", "table", "table", "table", "table", "differential", "differential",
                                   "differential", "differential"};
static const int ENVDEP[NRULES] = {1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0};
static const char *WHAT[NRULES] = {
    "select(gt(v,127),127,v) == MINPS(v,127) (table relation and MIN lane); side condition: v not NaN; all 2^32 v",
    "select(lt(v,-127),-127,v) == MAXPS(v,-127); side condition: v not NaN; all 2^32 v",
    "VCMPPS ymm (VEX, x2_predict) CMP(v,v,UNORD_Q) lane == all-ones iff isnan(v); all 2^32 v",
    "VCMPPS ymm CMP(v,v,ORD_Q) lane == all-ones iff not isnan(v); all 2^32 v",
    "act_q8 AVX2 instance: and(p, VCMPPS ymm(p,p,ORD_Q)) == (isnan(p) ? +0 : p); compare through x2_predict, AND transliterated; all 2^32 p",
    "canon8 instance: blendv(v, 0x7FC00000, VCMPPS ymm(v,v,UNORD_Q)) == (isnan(v) ? canon : v); compare through x2_predict, BLENDVPS transliterated; all 2^32 v",
    "canon16 instance: VCMPPS zmm into k (x2_predict, UNORD_Q), then mask_mov(v, k, canon) through the table's EVEX masking function x2_masked (merge) == (isnan(v) ? canon : v); all 2^32 v",
    "act_q8 AVX-512 instance: k = VCMPPS zmm into k (ORD_Q), maskz_mov(k, p) through x2_masked (zero) == (isnan(p) ? +0 : p); all 2^32 p",
    "VPDPBUSD lane (x2_dpbusd_lane): pairs at byte positions (0,1) and (2,3) over 2^32 each, acc = 0, == u0*x0 + u1*x1 [extra0 = per-product failures at each position 0..3 with 8 accumulators incl. +-2^31 boundaries (2^16 x 4 x 8), extra1 = per-product cases]",
    "VPMADDUBSW word (x2_maddubs_word) on Q4 pairs n0,n1 in [0,15], x0,x1 in [-127,127] == n0*x0 + n1*x1, no saturation [extra0/1 = min/max pair sum + 2^32]",
    "VPMADDUBSW(PABSB(w), PSIGNB(x, w)) word (PABSB/PSIGNB transliterated) == w0*x0 + w1*x1 over w in [-128,127]^2, x in [-127,127]^2 (DOM-ACT-Q) [extra0 = per-product failures over x in [-128,127], extra1/2 = min/max + 2^32]",
    "ALGEBRAIC IDENTITY, no table operation: (n - 8)*x == n*x - 8*x (int32), n in [0,15], x in [-127,127]; the substantive obligations (DOM-ACT-SUM, no C int32 overflow of a->sum*8) are RULES.md sec. 4.3 T2 facts",
    "ALGEBRAIC IDENTITY, no table operation: u8(q xor 0x80) == q + 128 [extra0 = failures] and q*x == u8(q xor 0x80)*x - 128*x, x in [-127,127]; obligations as R15 (a->sum*bias)",
    "packsswb(packssdw(q)) lane == (int8_t)q (packs transliterated: no table entry); side condition |q| <= 127; all 2^32 q [extra0 = values where both agree]",
    "cvtt((v + M) - M) == cvt(v) under the job's MXCSR (RC on both sides), M = 1.5*2^23; side condition: v not NaN and |v| <= 127 [extra0 = failures with |v| <= 2^22, extra1 = smallest failing |v| bits]",
    "as R19 with RC = RD, DAZ = FTZ = 0, on both sides",
    "as R19 with RC = RU",
    "as R19 with RC = RZ (RULES.md: Z3 counterexample on negative non-integers)",
    "Hearth q_f16(h) through table ops (CVTSI2SS, MULSS by 2^-24 for subnormals) == table VCVTPH2PS lane; all 2^16 h",
    "C `v != v` via UCOMISS(v,v) (x2_comis): (ZF == 0 || PF == 1) == isnan(v); all 2^32 v",
    "C transliteration of the z3 word() formula sat16(zext(u1)*sext(s1) + zext(u0)*sext(s0)) == x2_maddubs_word, all 2^32 (u0,u1,s0,s1)",
    "C transliteration of the z3 VPDPBUSD lane formula acc + sum zext(u)*sext(x) (mod 2^32) == x2_dpbusd_lane: each byte position x 2^16 x 8 accumulators, plus 2^27 pseudo-random (acc, 4 x (u, x)) per thread",
    "sha256 over pabsb(x) for x = 0..255, then psignb(a, b) for a = 0..255, b = 0..255 (C transliterations of R14) [hash: proofs/int_differential.py recomputes it from semantics/int_ops.py]",
    "sha256 over the low byte of sat8(sat16(q)) for q = -2^17 .. 2^17-1 then q = -2^31 .. -2^31+63 and 2^31-64 .. 2^31-1 (R17's transliteration) [hash: as HASH-PABS-PSIGN]",
};

static uint32_t q_f16(uint32_t h, const x2env *E) {   /* quant.c q_f16, each float operation through the table */
    uint32_t sign = (h & 0x8000u) << 16, e = (h >> 10) & 0x1Fu, m = h & 0x3FFu, fl = 0;
    if (e == 0x1F) return sign | 0x7F800000u | (m << 13) | (m ? 0x00400000u : 0u);
    if (e != 0) return sign | ((e + 112u) << 23) | (m << 13);
    if (m == 0) return sign;
    return sign | x2_mul(x2_cvt_i2f(m, E, &fl), 0x33800000u, E, &fl);   /* (float)m * 5.9604644775390625e-8f */
}

static void r19(acc_t *a, uint32_t v, const x2env *e) {
    uint32_t fl = 0, mag = v & 0x7FFFFFFFu;
    uint32_t lhs = x2_cvt_f2i(x2_sub(x2_add(v, MAGIC, e, &fl), MAGIC, e, &fl), e, 1, &fl);
    uint32_t rhs = x2_cvt_f2i(v, e, 0, &fl);
    int in = !NAN32(v) && mag <= C127, ok = lhs == rhs;
    note(a, in, ok, v, lhs, rhs);
    if (!ok && !NAN32(v)) {
        if (mag <= 0x4A800000u) a->extra[0]++;                   /* |v| <= 2^22 */
        if (a->extra[1] == 0 || mag < a->extra[1]) a->extra[1] = mag;
    }
}

static uint64_t xs64(uint64_t *s) { *s ^= *s << 13; *s ^= *s >> 7; *s ^= *s << 17; return *s; }

/* one slice [lo, hi) of 2^32, in batches of n lanes through an x2_predict compare (R06-R11) */
static void batch_rule(job_t *j, uint64_t lo, uint64_t hi) {
    acc_t *a = &j->a;
    int r = j->rule, vl = (r == R10 || r == R11) ? 512 : 256, n = vl / 32, imm = (r == R06 || r == R09 || r == R10) ? 3 : 7;
    x2sem s = sem_cmp((r == R10 || r == R11) ? X2B_CMP_K : X2B_CMP_VEC, vl, imm);
    __declspec(align(64)) x2case c;
    x2out o;
    x2reg canon, res;
    uint64_t x;
    int i;
    memset(&c, 0, sizeof c);
    memset(&res, 0, sizeof res);
    c.mxcsr = j->E.mxcsr;
    for (i = 0; i < 16; i++) canon.d[i] = CANON;
    for (x = lo; x < hi; x += (uint64_t)n) {
        for (i = 0; i < n; i++) c.src1.d[i] = c.src2.d[i] = (uint32_t)(x + (uint64_t)i);
        if (x2_predict(&s, &c, &o) != 0) { fprintf(stderr, "x2prove: MXCSR 0x%04x outside the model\n", c.mxcsr); exit(2); }
        if (r == R10) x2_masked(&canon, &c.src1, o.kdst, 0, 512, 32, &res);       /* _mm512_mask_mov_ps(v, k, canon) */
        if (r == R11) x2_masked(&c.src1, &c.src1, o.kdst, 1, 512, 32, &res);      /* _mm512_maskz_mov_ps(k, p) */
        for (i = 0; i < n; i++) {
            uint32_t v = c.src1.d[i], l = 0, rr = 0;
            switch (r) {
            case R06: l = o.dst.d[i]; rr = NAN32(v) ? 0xFFFFFFFFu : 0; break;
            case R07: l = o.dst.d[i]; rr = NAN32(v) ? 0 : 0xFFFFFFFFu; break;
            case R08: l = v & o.dst.d[i]; rr = NAN32(v) ? 0 : v; break;              /* VANDPS / VPAND: no entry yet */
            case R09: l = blendvps_lane(v, CANON, o.dst.d[i]); rr = NAN32(v) ? CANON : v; break;
            case R10: l = res.d[i]; rr = NAN32(v) ? CANON : v; break;
            case R11: l = res.d[i]; rr = NAN32(v) ? 0 : v; break;
            }
            note(a, 1, l == rr, v, l, rr);
        }
    }
}

static DWORD WINAPI worker(LPVOID p) {
    job_t *j = (job_t *)p;
    acc_t *a = &j->a;
    const x2env *E = &j->E;
    uint64_t lo, hi, x;
    uint32_t fl;
    int r = j->rule;
    uint64_t span = (1ull << 32);
    lo = span / (uint64_t)j->nthreads * (uint64_t)j->tid;
    hi = (j->tid == j->nthreads - 1) ? span : span / (uint64_t)j->nthreads * (uint64_t)(j->tid + 1);
    switch (r) {
    case R06: case R07: case R08: case R09: case R10: case R11:
        batch_rule(j, lo, hi);
        return 0;
    case R04: case R05: case R17: case R19: case R19RD: case R19RU: case R19RZ: case R21: case DIFF_MADDUBS:
        for (x = lo; x < hi; x++) {
            uint32_t v = (uint32_t)x, l, rr;
            fl = 0;
            switch (r) {
            case R04:
                l = (x2_relation(v, C127, E, 0, &fl) == X2_REL_GT) ? C127 : v;
                rr = x2_min(v, C127, E, &fl);
                note(a, !NAN32(v), l == rr, v, l, rr);
                break;
            case R05:
                l = (x2_relation(v, CM127, E, 0, &fl) == X2_REL_LT) ? CM127 : v;
                rr = x2_max(v, CM127, E, &fl);
                note(a, !NAN32(v), l == rr, v, l, rr);
                break;
            case R17: {
                int32_t q = (int32_t)v;
                int32_t w16 = sat16(q);                           /* VPACKSSDW lane */
                int32_t b8 = sat8((int16_t)(uint16_t)w16);        /* VPACKSSWB lane */
                int32_t tr = (int8_t)(uint8_t)(v & 0xFF);         /* (int8_t)q */
                int in = q >= -127 && q <= 127;
                note(a, in, b8 == tr, v, (uint32_t)b8, (uint32_t)tr);
                if (b8 == tr) a->extra[0]++;
                break;
            }
            case R19: case R19RD: case R19RU: case R19RZ: r19(a, v, E); break;
            case R21: {
                int zf, pf, cf;
                x2_comis(v, v, E, 0, &zf, &pf, &cf, &fl);
                l = (zf == 0 || pf == 1);
                rr = NAN32(v) ? 1u : 0u;
                note(a, 1, l == rr, v, l, rr);
                break;
            }
            case DIFF_MADDUBS: {
                uint8_t u0 = (uint8_t)v, u1 = (uint8_t)(v >> 8), s0 = (uint8_t)(v >> 16), s1 = (uint8_t)(v >> 24);
                int32_t t = sat16((int64_t)u1 * (int8_t)s1 + (int64_t)u0 * (int8_t)s0);   /* z3: sat16(zext*sext + zext*sext) */
                int32_t got = (int16_t)x2_maddubs_word(u0, u1, s0, s1);
                note(a, 1, got == t, v, (uint32_t)got, (uint32_t)t);
                break;
            }
            }
        }
        return 0;
    }
    switch (r) {
    case R12: {                                           /* pair level at positions (0,1) and (2,3): 2 x 2^32 */
        static const uint32_t ACC[8] = {0, 1, 0xFFFFFFFFu, 0x7FFFFFFFu, 0x80000000u, 0x12345678u, 0x7FFF8000u, 0x80007FFFu};
        uint32_t u0;
        int pos, ai;
        for (u0 = (uint32_t)j->tid; u0 < 256; u0 += (uint32_t)j->nthreads) {
            int x0, u1, x1, pp;
            for (pp = 0; pp < 2; pp++)
                for (x0 = -128; x0 < 128; x0++)
                    for (u1 = 0; u1 < 256; u1++)
                        for (x1 = -128; x1 < 128; x1++) {
                            uint8_t A[4] = {0, 0, 0, 0}, B[4] = {0, 0, 0, 0};
                            int32_t got, want;
                            A[2 * pp] = (uint8_t)u0; A[2 * pp + 1] = (uint8_t)u1;
                            B[2 * pp] = (uint8_t)x0; B[2 * pp + 1] = (uint8_t)x1;
                            got = (int32_t)x2_dpbusd_lane(0, A, B, 0);
                            want = (int32_t)u0 * x0 + (int32_t)u1 * x1;
                            note(a, 1, got == want, ((uint64_t)pp << 32) | ((uint64_t)u0 << 24) | ((uint64_t)(uint8_t)x0 << 16) |
                                 ((uint64_t)u1 << 8) | (uint8_t)x1, (uint32_t)got, (uint32_t)want);
                        }
        }
        for (pos = j->tid; pos < 4; pos += j->nthreads)    /* per product, each position, nonzero accumulators */
            for (ai = 0; ai < 8; ai++) {
                uint32_t ux;
                for (ux = 0; ux < 65536; ux++) {
                    uint8_t A[4] = {0, 0, 0, 0}, B[4] = {0, 0, 0, 0};
                    uint32_t want;
                    A[pos] = (uint8_t)(ux >> 8);
                    B[pos] = (uint8_t)ux;
                    want = ACC[ai] + (uint32_t)((int32_t)A[pos] * (int8_t)B[pos]);
                    a->extra[1]++;
                    if (x2_dpbusd_lane(ACC[ai], A, B, 0) != want) a->extra[0]++;
                }
            }
        break;
    }
    case R13: {
        int n0, n1, x0, x1;
        int64_t mn = 1 << 30, mx = -(1 << 30);
        for (n0 = j->tid; n0 < 16; n0 += j->nthreads)
            for (n1 = 0; n1 < 16; n1++)
                for (x0 = -127; x0 <= 127; x0++)
                    for (x1 = -127; x1 <= 127; x1++) {
                        int32_t got = (int16_t)x2_maddubs_word((uint8_t)n0, (uint8_t)n1, (uint8_t)x0, (uint8_t)x1);
                        int32_t want = n0 * x0 + n1 * x1;
                        note(a, 1, got == want, ((uint64_t)n0 << 24) | ((uint64_t)(uint8_t)x0 << 16) | ((uint64_t)n1 << 8) | (uint8_t)x1,
                             (uint32_t)got, (uint32_t)want);
                        if (want < mn) mn = want;
                        if (want > mx) mx = want;
                    }
        a->extra[0] = (uint64_t)(mn + (1ll << 32));
        a->extra[1] = (uint64_t)(mx + (1ll << 32));
        break;
    }
    case R14: {
        int w0, w1, x0, x1;
        int64_t mn = 1 << 30, mx = -(1 << 30);
        for (w0 = -128 + j->tid; w0 < 128; w0 += j->nthreads) {
            for (x0 = -128; x0 < 128; x0++) {                 /* per product over the full int8 x range */
                int32_t pr = (int32_t)pabsb((uint8_t)w0) * (int8_t)psignb((uint8_t)x0, (uint8_t)w0);
                if (pr != w0 * x0) a->extra[0]++;
            }
            for (w1 = -128; w1 < 128; w1++) {
                uint8_t u0 = pabsb((uint8_t)w0), u1 = pabsb((uint8_t)w1);
                for (x0 = -127; x0 <= 127; x0++) {
                    uint8_t s0 = psignb((uint8_t)x0, (uint8_t)w0);
                    for (x1 = -127; x1 <= 127; x1++) {
                        int32_t got = (int16_t)x2_maddubs_word(u0, u1, s0, psignb((uint8_t)x1, (uint8_t)w1));
                        int32_t want = w0 * x0 + w1 * x1;
                        if (got != want) note(a, 1, 0, ((uint64_t)(uint8_t)w0 << 24) | ((uint64_t)(uint8_t)x0 << 16) | ((uint64_t)(uint8_t)w1 << 8) | (uint8_t)x1,
                                              (uint32_t)got, (uint32_t)want);
                        else { a->inputs++; a->cond++; }
                        if (want < mn) mn = want;
                        if (want > mx) mx = want;
                    }
                }
            }
        }
        a->extra[1] = (uint64_t)(mn + (1ll << 32));
        a->extra[2] = (uint64_t)(mx + (1ll << 32));
        break;
    }
    case R15: {
        int n, xx;
        if (j->tid) break;
        for (n = 0; n < 16; n++)
            for (xx = -127; xx <= 127; xx++) note(a, 1, (n - 8) * xx == n * xx - 8 * xx, ((uint64_t)n << 8) | (uint8_t)xx, 0, 0);
        break;
    }
    case R16: {
        int q, xx;
        if (j->tid) break;
        for (q = -128; q < 128; q++) {
            uint8_t u = (uint8_t)((uint8_t)q ^ 0x80u);
            if ((int)u != q + 128) a->extra[0]++;
            for (xx = -127; xx <= 127; xx++) note(a, 1, q * xx == (int)u * xx - 128 * xx, ((uint64_t)(uint8_t)q << 8) | (uint8_t)xx, 0, 0);
        }
        break;
    }
    case R20: {
        uint32_t h;
        for (h = (uint32_t)j->tid; h < 65536; h += (uint32_t)j->nthreads) {
            uint32_t fl2 = 0, l = q_f16(h, E), rr = x2_cvt_h2f(h, E, &fl2);
            note(a, 1, l == rr, h, l, rr);
        }
        break;
    }
    case DIFF_DPBUSD: {
        static const uint32_t ACC[8] = {0, 1, 0xFFFFFFFFu, 0x7FFFFFFFu, 0x80000000u, 0x12345678u, 0x7FFF8000u, 0x80007FFFu};
        uint64_t s = 0x9E3779B97F4A7C15ull ^ (uint64_t)(j->tid + 1) * 0xD1B54A32D192ED03ull, k;
        int pos, ai;
        for (pos = j->tid; pos < 4; pos += j->nthreads)
            for (ai = 0; ai < 8; ai++) {
                uint32_t ux;
                for (ux = 0; ux < 65536; ux++) {
                    uint8_t A[4] = {0, 0, 0, 0}, B[4] = {0, 0, 0, 0};
                    uint32_t want, got;
                    A[pos] = (uint8_t)(ux >> 8);
                    B[pos] = (uint8_t)ux;
                    want = ACC[ai] + (uint32_t)((int32_t)A[pos] * (int8_t)B[pos]);   /* acc + zext(u)*sext(x), mod 2^32 */
                    got = x2_dpbusd_lane(ACC[ai], A, B, 0);
                    note(a, 1, got == want, ((uint64_t)pos << 40) | ((uint64_t)ai << 32) | ux, got, want);
                }
            }
        for (k = 0; k < (1ull << 27); k++) {
            uint64_t r1 = xs64(&s), r2 = xs64(&s);
            uint8_t A[4], B[4];
            int t;
            uint32_t acc = (uint32_t)r2, want = acc, got;
            for (t = 0; t < 4; t++) {
                A[t] = (uint8_t)(r1 >> (8 * t));
                B[t] = (uint8_t)(r1 >> (32 + 8 * t));
                want += (uint32_t)((int32_t)A[t] * (int8_t)B[t]);
            }
            got = x2_dpbusd_lane(acc, A, B, 0);
            note(a, 1, got == want, r1, got, want);
        }
        break;
    }
    case HASH_PABS_PSIGN: {
        x2sha h;
        uint32_t xv, b;
        if (j->tid) break;
        x2sha_init(&h);
        for (xv = 0; xv < 256; xv++) { uint8_t y = pabsb((uint8_t)xv); x2sha_update(&h, &y, 1); a->inputs++; }
        for (xv = 0; xv < 256; xv++)
            for (b = 0; b < 256; b++) { uint8_t y = psignb((uint8_t)xv, (uint8_t)b); x2sha_update(&h, &y, 1); a->inputs++; }
        x2sha_final(&h, a->hash);
        break;
    }
    case HASH_PACKS: {
        x2sha h;
        int64_t q;
        int part;
        if (j->tid) break;
        x2sha_init(&h);
        for (part = 0; part < 3; part++) {
            int64_t qlo = part == 0 ? -(1ll << 17) : (part == 1 ? -(1ll << 31) : (1ll << 31) - 64);
            int64_t qhi = part == 0 ? (1ll << 17) : (part == 1 ? -(1ll << 31) + 64 : (1ll << 31));
            for (q = qlo; q < qhi; q++) {
                uint8_t y = (uint8_t)sat8((int16_t)(uint16_t)sat16(q));
                x2sha_update(&h, &y, 1);
                a->inputs++;
            }
        }
        x2sha_final(&h, a->hash);
        break;
    }
    }
    return 0;
}

static double now(void) {
    LARGE_INTEGER f, c;
    QueryPerformanceFrequency(&f);
    QueryPerformanceCounter(&c);
    return (double)c.QuadPart / (double)f.QuadPart;
}

static int selected(const char *only, const char *name) {
    const char *p = only;
    size_t n = strlen(name);
    if (!only) return 1;
    while (*p) {
        const char *q = strchr(p, ',');
        size_t len = q ? (size_t)(q - p) : strlen(p);
        if (len == n && strncmp(p, name, n) == 0) return 1;
        if (!q) break;
        p = q + 1;
    }
    return 0;
}

int main(int argc, char **argv) {
    int nthreads = 2, r, i, nout = 0, nmx = 0, ei;
    const char *only = NULL, *mxl = NULL;
    uint32_t mxv[32];
    FILE *o;
    double t_all = now();
    if (argc < 2) { fprintf(stderr, "usage: x2prove OUT.json [--threads N] [--only R04,R19-RZ] [--mxcsr 1f80,1fc0]\n"); return 2; }
    for (i = 2; i < argc - 1; i++) {
        if (!strcmp(argv[i], "--threads")) nthreads = atoi(argv[i + 1]);
        if (!strcmp(argv[i], "--only")) only = argv[i + 1];
        if (!strcmp(argv[i], "--mxcsr")) mxl = argv[i + 1];
    }
    if (nthreads < 1 || nthreads > 2) { fprintf(stderr, "this track may use at most 2 threads\n"); return 2; }
    if (only) {                                       /* every --only token must name a rule */
        const char *p = only;
        while (*p) {
            const char *q = strchr(p, ',');
            size_t len = q ? (size_t)(q - p) : strlen(p);
            int found = 0;
            for (r = 0; r < NRULES; r++) if (strlen(NAMES[r]) == len && !strncmp(p, NAMES[r], len)) found = 1;
            if (!found) { fprintf(stderr, "x2prove: unknown rule in --only: %.*s\n", (int)len, p); return 2; }
            if (!q) break;
            p = q + 1;
        }
    }
    if (mxl) {
        const char *p = mxl;
        while (*p && nmx < 32) {
            x2env t;
            mxv[nmx] = (uint32_t)strtoul(p, NULL, 16);
            if (x2_env_make(&t, mxv[nmx], -1, 0) != 0 || (mxv[nmx] & 0x3Fu)) {
                fprintf(stderr, "x2prove: MXCSR %04x outside the model (unmasked exception, reserved bit or sticky flag)\n", mxv[nmx]);
                return 2;
            }
            nmx++;
            while (*p && *p != ',') p++;
            if (*p) p++;
        }
    } else {
        mxv[0] = 0x1F80u;
        nmx = 1;
    }
    o = fopen(argv[1], "w");
    if (!o) return 2;
    fprintf(o, "{\"tool\": \"x2prove\", \"prove_src_sha256\": \"%s\", \"interp_src_sha256\": \"%s\", \"compiler\": \"%s\", "
               "\"threads\": %d, \"mxcsr_list\": [", X2_PROVE_SRC_SHA256, X2_INTERP_SRC_SHA256, X2_COMPILER, nthreads);
    for (ei = 0; ei < nmx; ei++) fprintf(o, "%s\"0x%04x\"", ei ? ", " : "", mxv[ei]);
    fprintf(o, "], \"rules\": [\n");
    for (r = 0; r < NRULES; r++) {
        int ne = ENVDEP[r] ? nmx : 1;
        if (!selected(only, NAMES[r])) continue;
        for (ei = 0; ei < ne; ei++) {
            job_t jobs[2];
            HANDLE th[2];
            acc_t s;
            double t0;
            int t, c;
            uint32_t mx = ENVDEP[r] ? mxv[ei] : 0x1F80u;
            char hx[65] = "", mxs[16];
            if (r == R19RD) mx = 0x1F80u | ((uint32_t)X2_RD << 13);
            if (r == R19RU) mx = 0x1F80u | ((uint32_t)X2_RU << 13);
            if (r == R19RZ) mx = 0x1F80u | ((uint32_t)X2_RZ << 13);
            memset(jobs, 0, sizeof jobs);
            memset(&s, 0, sizeof s);
            t0 = now();
            for (t = 0; t < nthreads; t++) {
                jobs[t].rule = r; jobs[t].tid = t; jobs[t].nthreads = nthreads;
                x2_env_make(&jobs[t].E, mx, -1, 0);
                th[t] = CreateThread(NULL, 0, worker, &jobs[t], 0, NULL);
            }
            WaitForMultipleObjects((DWORD)nthreads, th, TRUE, INFINITE);
            for (t = 0; t < nthreads; t++) {
                acc_t *a = &jobs[t].a;
                CloseHandle(th[t]);
                s.inputs += a->inputs; s.cond += a->cond; s.fail_in += a->fail_in; s.fail_out += a->fail_out;
                if (r == R13 || r == R14) {
                    int lo_i = r == R13 ? 0 : 1;
                    if (t == 0 || a->extra[lo_i] < s.extra[lo_i]) s.extra[lo_i] = a->extra[lo_i];
                    if (t == 0 || a->extra[lo_i + 1] > s.extra[lo_i + 1]) s.extra[lo_i + 1] = a->extra[lo_i + 1];
                    if (r == R14) s.extra[0] += a->extra[0];
                } else if (r >= R19 && r <= R19RZ) {
                    s.extra[0] += a->extra[0];
                    if (a->extra[1] && (s.extra[1] == 0 || a->extra[1] < s.extra[1])) s.extra[1] = a->extra[1];
                } else {
                    for (c = 0; c < 4; c++) s.extra[c] += a->extra[c];
                }
                if ((r == HASH_PABS_PSIGN || r == HASH_PACKS) && t == 0) x2sha_hex(a->hash, hx);
                for (c = 0; c < a->ncex && s.ncex < 4; c++) { memcpy(s.cex[s.ncex], a->cex[c], sizeof a->cex[c]); s.ncex++; }
            }
            if (ENVDEP[r] || r == R19RD || r == R19RU || r == R19RZ) sprintf(mxs, "\"0x%04x\"", mx);
            else strcpy(mxs, "null");
            fprintf(o, "%s {\"rule\": \"%s\", \"mxcsr\": %s, \"route_kind\": \"%s\", \"what\": \"%s\", \"inputs\": %llu, "
                       "\"in_side_condition\": %llu, \"failures_in_side_condition\": %llu, \"failures_outside\": %llu, "
                       "\"extra\": [%llu, %llu, %llu, %llu], \"hash\": %s%s%s, \"seconds\": %.3f, \"counterexamples\": [",
                    nout++ ? "," : "", NAMES[r], mxs, KIND[r], WHAT[r],
                    (unsigned long long)s.inputs, (unsigned long long)s.cond, (unsigned long long)s.fail_in,
                    (unsigned long long)s.fail_out, (unsigned long long)s.extra[0], (unsigned long long)s.extra[1],
                    (unsigned long long)s.extra[2], (unsigned long long)s.extra[3], hx[0] ? "\"" : "null", hx, hx[0] ? "\"" : "",
                    now() - t0);
            for (c = 0; c < s.ncex; c++)
                fprintf(o, "%s[\"0x%llx\", \"0x%llx\", \"0x%llx\"]", c ? ", " : "", (unsigned long long)s.cex[c][0],
                        (unsigned long long)s.cex[c][1], (unsigned long long)s.cex[c][2]);
            fprintf(o, "]}\n");
            printf("%-15s mxcsr %04x  inputs %12llu  cond %12llu  fail_in %10llu  fail_out %10llu  extra %llu,%llu,%llu  %s %.2f s\n",
                   NAMES[r], mx, (unsigned long long)s.inputs, (unsigned long long)s.cond, (unsigned long long)s.fail_in,
                   (unsigned long long)s.fail_out, (unsigned long long)s.extra[0], (unsigned long long)s.extra[1],
                   (unsigned long long)s.extra[2], hx, now() - t0);
            fflush(stdout);
            fflush(o);
        }
    }
    fprintf(o, "], \"total_seconds\": %.3f}\n", now() - t_all);
    fclose(o);
    return 0;
}
