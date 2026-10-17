#!/usr/bin/env python3
"""gen_zoo.py -- generate the NON-Hearth "instruction zoo" used to validate class/objdump_norm.csv before
freeze (record §7 cross-decoder check). Nothing here reads Hearth.

  python -I gen_zoo.py --xml x86-intel.xml --outdir DIR [--exclude names.txt]

Writes:
  DIR/zoo_avx.c  one noinline wrapper per intrinsic whose CPUID tags are all in AVX_SETS (VEX/EVEX encodings;
                 compile with the AVX-512 flags in ZOO_FLAGS_AVX)
  DIR/zoo_sse.c  the same for intrinsics whose tags are all in SSE_SETS (legacy encodings; ZOO_FLAGS_SSE)
  DIR/zoo_asm.c  hand-written inline assembly: GPR, x87, string and prefix forms whose objdump spelling
                 differs from the XED iclass (condition codes, rep/lock, nop, movsd/cmpsd, ...)
Immediate operands get fixed values; FP compare predicates are enumerated (0..31), integer compare
predicates 0..7, so every predicate spelling of llvm-objdump appears.
"""
import argparse
import os
import xml.etree.ElementTree as ET

AVX_SETS = {"SSE", "SSE2", "SSE3", "SSSE3", "SSE4.1", "SSE4.2", "AVX", "AVX2", "FMA", "F16C", "AVX512F", "AVX512BW",
            "AVX512DQ", "AVX512VL", "AVX512CD", "AVX512_VNNI", "AVX512_BF16", "BMI1", "BMI2", "POPCNT", "LZCNT"}
SSE_SETS = {"SSE", "SSE2", "SSE3", "SSSE3", "SSE4.1", "SSE4.2", "POPCNT"}
ZOO_FLAGS_AVX = ["-mavx512f", "-mavx512bw", "-mavx512dq", "-mavx512vl", "-mavx512cd", "-mavx512vnni",
                 "-mavx512bf16", "-mavx2", "-mfma", "-mf16c", "-mbmi", "-mbmi2", "-mlzcnt", "-mpopcnt"]
ZOO_FLAGS_SSE = ["-msse4.2", "-mpopcnt"]
VEC = {"__m128", "__m128d", "__m128i", "__m256", "__m256d", "__m256i", "__m512", "__m512d", "__m512i",
       "__m128bh", "__m256bh", "__m512bh", "__mmask8", "__mmask16", "__mmask32", "__mmask64"}
SCALAR = {"int", "unsigned int", "short", "unsigned short", "char", "unsigned char", "long long",
          "unsigned long long", "__int64", "unsigned __int64", "float", "double", "__int32", "unsigned __int32",
          "__int16", "unsigned __int16", "__int8", "unsigned __int8", "const int", "const unsigned int",
          "size_t", "long", "unsigned long", "bool", "const float", "const double"}
IMM = {"_CMP_": list(range(32)), "_MM_CMPINT": list(range(8)), "_MM_FROUND": [8], "_MM_FROUND_SAE": [8],
       "_MM_INDEX_SCALE": [4], "_MM_MANTISSA_NORM": [0], "_MM_MANTISSA_SIGN": [0], "_MM_PERM": ["(_MM_PERM_ENUM)0x4e"],
       "_MM_REDUCE": [1], "_MM_ROUND_MODE": [0]}
SKIP_NAMES = {"_mm_prefetch", "_mm_clflush", "_mm_lfence", "_mm_mfence", "_mm_sfence", "_mm_pause", "_mm_setcsr",
              "_mm_getcsr", "_MM_SET_ROUNDING_MODE", "_MM_GET_ROUNDING_MODE", "_MM_SET_EXCEPTION_MASK",
              "_mm_monitor", "_mm_mwait", "_mm_undefined_ps", "_mm_undefined_pd", "_mm_undefined_si128",
              "_mm256_undefined_ps", "_mm256_undefined_pd", "_mm256_undefined_si256", "_mm512_undefined",
              "_mm512_undefined_ps", "_mm512_undefined_pd", "_mm512_undefined_epi32", "_mm_crc32_u64"}

ASM = r"""
/* zoo_asm.c -- hand-written forms for the objdump/XED normaliser check. NOT Hearth code. */
void zoo_asm(void)
{
    __asm__ volatile(
        ".intel_syntax noprefix\n"
        "1:\n"
        "jz 1b\n jnz 1b\n ja 1b\n jae 1b\n jb 1b\n jbe 1b\n jl 1b\n jge 1b\n jle 1b\n jg 1b\n"
        "js 1b\n jns 1b\n jp 1b\n jnp 1b\n jo 1b\n jno 1b\n jrcxz 1b\n jmp 1b\n"
        "jz 2f\n jmp 2f\n .p2align 8\n 2:\n"
        "cmovz eax, ecx\n cmovnz eax, ecx\n cmova eax, ecx\n cmovae eax, ecx\n cmovb eax, ecx\n cmovbe eax, ecx\n"
        "cmovl eax, ecx\n cmovge eax, ecx\n cmovle eax, ecx\n cmovg eax, ecx\n cmovs eax, ecx\n cmovns eax, ecx\n"
        "cmovp eax, ecx\n cmovnp eax, ecx\n cmovo eax, ecx\n cmovno eax, ecx\n"
        "setz al\n setnz al\n seta al\n setae al\n setb al\n setbe al\n setl al\n setge al\n setle al\n setg al\n"
        "sets al\n setns al\n setp al\n setnp al\n seto al\n setno al\n"
        "rep movsb\n rep movsq\n rep stosb\n rep stosq\n repe cmpsb\n repne scasb\n movsb\n movsq\n stosd\n lodsb\n"
        "lock xadd dword ptr [rdi], eax\n lock cmpxchg qword ptr [rdi], rcx\n lock add dword ptr [rdi], 1\n"
        "lock or dword ptr [rdi], 1\n lock inc qword ptr [rdi]\n lock cmpxchg16b xmmword ptr [rdi]\n"
        "xchg eax, ecx\n xchg qword ptr [rdi], rax\n bswap eax\n cwde\n cdqe\n cqo\n cdq\n cwd\n cbw\n"
        "movsx eax, cl\n movzx eax, cx\n movsxd rax, ecx\n sal eax, 3\n shl eax, cl\n shld eax, ecx, 3\n"
        "imul eax, ecx, 7\n div ecx\n idiv rcx\n neg eax\n not eax\n bt eax, 3\n bsf eax, ecx\n bsr eax, ecx\n"
        "tzcnt eax, ecx\n lzcnt eax, ecx\n popcnt eax, ecx\n andn eax, ecx, edx\n bextr eax, ecx, edx\n"
        "blsr eax, ecx\n shlx eax, ecx, edx\n sarx eax, ecx, edx\n rorx eax, ecx, 3\n mulx eax, ecx, edx\n"
        "pdep eax, ecx, edx\n pext eax, ecx, edx\n bzhi eax, ecx, edx\n adc eax, ecx\n sbb eax, ecx\n"
        "movabs rax, 0x123456789abcdef0\n lea rax, [rip + 0x10]\n movnti dword ptr [rdi], eax\n"
        "xlatb\n pushfq\n popfq\n enter 16, 0\n leave\n push rbx\n pop rbx\n"
        "endbr64\n nop\n xchg ax, ax\n nop dword ptr [rax]\n nop word ptr [rax + rax]\n int3\n ud2\n pause\n"
        "mfence\n lfence\n sfence\n prefetcht0 byte ptr [rdi]\n prefetchnta byte ptr [rdi]\n prefetchw byte ptr [rdi]\n"
        "call rax\n call qword ptr [rax]\n jmp rax\n notrack jmp rax\n"
        "fld dword ptr [rdi]\n fld qword ptr [rdi]\n fld tbyte ptr [rdi]\n fld st(1)\n fst dword ptr [rdi]\n"
        "fstp qword ptr [rdi]\n fstp st(1)\n fild dword ptr [rdi]\n fild qword ptr [rdi]\n fist dword ptr [rdi]\n"
        "fistp qword ptr [rdi]\n fisttp dword ptr [rdi]\n fadd st, st(1)\n faddp st(1), st\n fiadd dword ptr [rdi]\n"
        "fsub st, st(1)\n fsubr st, st(1)\n fsubp st(1), st\n fsubrp st(1), st\n fmul dword ptr [rdi]\n"
        "fmulp st(1), st\n fdiv st, st(1)\n fdivr st, st(1)\n fdivp st(1), st\n fdivrp st(1), st\n fidiv dword ptr [rdi]\n"
        "fsqrt\n fabs\n fchs\n fxch st(1)\n fcom st(1)\n fcomp st(1)\n fcompp\n fucom st(1)\n fucomp st(1)\n fucompp\n"
        "fcomi st, st(1)\n fcomip st, st(1)\n fucomi st, st(1)\n fucomip st, st(1)\n ftst\n fxam\n"
        "fld1\n fldz\n fldpi\n fldl2e\n fldln2\n frndint\n fscale\n fprem\n fprem1\n fxtract\n f2xm1\n fyl2x\n"
        "fsin\n fcos\n fsincos\n fptan\n fpatan\n fcmovb st, st(1)\n fcmove st, st(1)\n fcmovnbe st, st(1)\n"
        "fnstcw word ptr [rdi]\n fldcw word ptr [rdi]\n fnstsw ax\n fnstenv [rdi]\n fldenv [rdi]\n fnclex\n fninit\n"
        "fwait\n ffree st(1)\n fincstp\n fdecstp\n fnop\n fbld tbyte ptr [rdi]\n fbstp tbyte ptr [rdi]\n"
        "stmxcsr dword ptr [rdi]\n ldmxcsr dword ptr [rdi]\n vstmxcsr dword ptr [rdi]\n vldmxcsr dword ptr [rdi]\n"
        "movsd xmm0, xmm1\n movsd xmm0, qword ptr [rdi]\n cmpsd xmm0, xmm1, 1\n cmpltsd xmm0, xmm1\n"
        "fxsave [rdi]\n fxrstor [rdi]\n emms\n vzeroupper\n vzeroall\n"
        "ret\n"
        ".att_syntax prefix\n" ::: "memory");
}
"""


def ctype(t):
    return t.replace("const ", "").strip()


def gen(intrs, allowed, exclude):
    lines = ["/* generated by gen_zoo.py -- NOT Hearth code */", "#include <immintrin.h>", "#include <stdint.h>",
             "#include <stddef.h>", "#define ZN __attribute__((noinline))", ""]
    n = 0
    for e in intrs:
        name = e.get("name")
        if name in SKIP_NAMES or name in exclude or e.get("tech") in ("SVML", "MMX", "Other"):
            continue
        cpu = {c.text for c in e.findall("CPUID")}
        if not cpu or not cpu <= allowed:
            continue
        ret = e.find("return")
        rtype = ret.get("type") if ret is not None else "void"
        params = e.findall("parameter")
        ok = rtype == "void" or ctype(rtype) in VEC or ctype(rtype) in SCALAR or "*" in rtype
        decl, args, immlists = [], [], []
        for p in params:
            t, v = p.get("type"), p.get("varname")
            if t == "void" and v is None:
                continue
            if p.get("etype") == "IMM":
                vals = IMM.get(p.get("immtype"), [1])
                immlists.append(vals)
                args.append(None)
                continue
            if not (ctype(t) in VEC or ctype(t) in SCALAR or "*" in t):
                ok = False
                break
            decl.append("%s %s" % (t, v))
            args.append(v)
        if not ok:
            continue
        combos = [[]]
        for vals in immlists:
            combos = [c + [v] for c in combos for v in vals][:32]
        for ci, combo in enumerate(combos):
            it = iter(combo)
            call_args = [a if a is not None else str(next(it)) for a in args]
            fn = "zoo_%s_%d" % (name.lstrip("_"), ci)
            body = "%s(%s)" % (name, ", ".join(call_args))
            if rtype == "void":
                lines.append("ZN void %s(%s) { %s; }" % (fn, ", ".join(decl) or "void", body))
            else:
                lines.append("ZN %s %s(%s) { return %s; }" % (rtype, fn, ", ".join(decl) or "void", body))
            n += 1
    return "\n".join(lines) + "\n", n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--exclude", help="file with intrinsic names to leave out (one per line)")
    a = ap.parse_args()
    exclude = set()
    if a.exclude and os.path.exists(a.exclude):
        exclude = {l.strip() for l in open(a.exclude) if l.strip()}
    intrs = ET.parse(a.xml).getroot().findall("intrinsic")
    os.makedirs(a.outdir, exist_ok=True)
    for fname, allowed in (("zoo_avx.c", AVX_SETS), ("zoo_sse.c", SSE_SETS)):
        txt, n = gen(intrs, allowed, exclude)
        with open(os.path.join(a.outdir, fname), "w", newline="\n") as f:
            f.write(txt)
        print(fname, n, "functions")
    with open(os.path.join(a.outdir, "zoo_asm.c"), "w", newline="\n") as f:
        f.write(ASM)
    print("flags avx:", " ".join(ZOO_FLAGS_AVX), "| flags sse:", " ".join(ZOO_FLAGS_SSE))


if __name__ == "__main__":
    main()
