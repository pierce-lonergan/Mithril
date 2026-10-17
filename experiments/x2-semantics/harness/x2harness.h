/* x2harness.h -- shared declarations of the X2 native fuzz harness (FUZZ-DESIGN.md sec. 1, sec. 4). */
#ifndef X2HARNESS_H
#define X2HARNESS_H
#include "x2ref.h"

typedef void (*x2stubfn)(const x2case *, x2out *);

typedef struct {
    int id;
    const char *name;
    x2stubfn fn;
    int entry_index;           /* index in semantics.table.ENTRIES                         */
    const char *iform;         /* the entry key                                            */
    const char *decoded_iform; /* what the pinned XED decodes the stub bytes as            */
    const char *variant;       /* plain | merge | zero | *_erN | *_sae | *_bcast | *_immNN  */
    const char *content_hash;  /* entry content hash at generation time                    */
    int key_ok;                /* decoded iform == entry iform                             */
    x2sem sem;
    int nbytes;
    const char *bytes_hex;
} x2stub;

extern const x2stub X2_STUBS[];
extern const int X2_NSTUBS;
extern const char X2_STUB_MANIFEST_SHA256[];
extern const char X2_SEMANTICS_BUNDLE[];

/* Hand-written plumbing probes (x2probe.asm): they test the harness's register, mask, GPR, RFLAGS and
 * MXCSR paths and its fault capture. They execute no table instruction. */
void x2probe_mxcsr(uint32_t *inout);                 /* inout[1] = MXCSR after loading inout[0]  */
void x2probe_copy_evex(const x2case *c, x2out *o);   /* dst = src1 via zmm17->zmm16, k2 = k1     */
void x2probe_copy_vex(const x2case *c, x2out *o);    /* dst = src2 via zmm2->zmm0                */
uint64_t x2probe_load(const void *p);                /* one 8-byte load                         */

/* File formats (little-endian). See README.md "File formats". */
#define X2_VEC_MAGIC "X2VEC001"
#define X2_RES_MAGIC "X2RES001"
#define X2_HDR_SIZE 256
#define X2_VEC_REC 320
#define X2_RES_REC 160

#pragma pack(push, 1)
typedef struct {
    char magic[8];
    uint32_t version, rec_size;
    uint64_t n;
    char manifest_sha256[64];
    char generator_sha256[64];
    char bundle[64];
    char label[40];
} x2vechdr;                     /* 256 bytes */
typedef struct {
    uint32_t stub_id, flags, set_id, class_id, env_id, lane, memfault_boundary, n_lane_cases;
    uint64_t index, key;
    uint8_t rsv[16];
    x2case c;
} x2vecrec;                     /* 320 bytes */
typedef struct {
    char magic[8];
    uint32_t version, rec_size;
    uint64_t n;
    char vectors_sha256[64];
    char manifest_sha256[64];
    char producer[32];
    char producer_sha256[64];
    uint32_t cpu, pad;
} x2reshdr;                     /* 256 bytes */
typedef struct {
    x2out o;
    uint32_t status, exc_code;
    uint64_t index;
    uint8_t rsv[16];
} x2resrec;                     /* 160 bytes */
#pragma pack(pop)

#define X2_FLAG_MEMFAULT 1u     /* place the memory operand so lanes >= memfault_boundary are on a NOACCESS page */
#define X2_FLAG_SINGLE_LANE 2u  /* flag isolation: single active lane through the write mask */
#define X2_FLAG_FILLERS 4u      /* flag isolation: flag-neutral fillers in the other lanes */

#define X2_ST_OK 0u
#define X2_ST_EXCEPTION 1u
#define X2_ST_UNMODELED 2u
#define X2_ST_BADSTUB 3u

#endif
