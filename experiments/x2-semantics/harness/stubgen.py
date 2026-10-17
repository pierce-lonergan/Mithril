"""Stub generator for the X2 native fuzz harness (FUZZ-DESIGN.md §4 "Stubs").

For every table entry and every operand variant it runs (plain / merge / zero masking, {er} modes,
{sae}, memory and broadcast forms, compare immediates):
  1. builds the instruction from the entry's OPERAND ROLES (never a role map of its own; finding
     R1-4): EVEX dst -> reg16, src1/src -> reg17, src2 -> reg18 or [rax], mask -> k1 (k0 for the
     plain variant), k destination -> k2; VEX dst -> reg0, src1/src -> reg1, src2 -> reg2 or [rax];
     legacy dst_src1 -> xmm0, src2 -> xmm2, src -> xmm1; GPR operands -> eax;
  2. asks the pinned XED encoder (xed-enc-asmparse, XED v2026.08.23) for the bytes;
  3. decodes the bytes back with the pinned XED (`xed -64 -v 4 -d`) and asserts: decoded ICLASS =
     entry iclass; decoded IFORM = entry iform (a mismatch on a `provisional` key is recorded as
     key_ok = 0, anywhere else it is an error); every listed operand register is the one its role
     was placed in; the masking, zeroing, {er}/{sae} and broadcast fields are the variant's; the
     decoded immediate IMM0 equals the variant's imm8, and for register forms the last byte is it
     (added 2026-10-16 after review);
  4. emits the stub as MASM `db` lines (ml64 never chooses an encoding), a C stub table with the
     semantics descriptor the C reference interpreter needs, and a JSON manifest.

Run on the desktop (Windows XED):
  python -I stubgen.py --sem-root <dir containing semantics/> --xed-bin <xed bin dir> --out <dir>
Outputs: stubs.asm, stubs_table.c, stubs_manifest.json (+ its sha256 inside stubs_table.c).
Exit status 0 only if every stub encoded and every non-provisional check passed.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

BUILDER = {"packed_fp2": 1, "scalar_fp2": 2, "packed_fp1": 3, "cmp_k": 4, "cmp_vec": 5, "comis": 6,
           "cvt_f2i_gpr": 7, "cvt_i2f_scalar": 8, "int2": 9, "int_acc": 10}
FN = {None: 0, "fp_ops.add": 1, "fp_ops.sub": 2, "fp_ops.mul": 3, "fp_ops.div": 4, "fp_ops.max_": 5,
      "fp_ops.min_": 6, "fp_ops.cmp_pred": 7, "fp_ops.cvt_i32_to_f32": 8, "fp_ops.cvt_f32_to_i32": 9,
      "fp_ops.cvt_f16_to_f32": 10, "int_ops.pmaddubsw": 11, "int_ops.pmaddwd": 12, "int_ops.phaddd": 13,
      "int_ops.pdpbusd": 14}
ENC = {"legacy": 0, "vex": 1, "evex": 2}
MASKMODE = {"plain": 0, "merge": 1, "zero": 2}
DSTKIND = {"vec": 0, "k": 1, "rflags": 2, "gpr": 3}
ER_NAMES = ["rne-sae", "rd-sae", "ru-sae", "rz-sae"]   # XED asmparse decorator spelling
ER_FAMILIES = {"FP.ADD.f32", "FP.SUB.f32", "FP.MUL.f32", "FP.DIV.f32", "FP.CVT.i32_f32", "FP.CVT.f32_i32.rc"}
SAE_FAMILIES = {"FP.MAX.f32", "FP.MIN.f32", "FP.CMP.f32", "FP.CVT.f32_i32.trunc", "FP.CVT.f16_f32"}
MEMW = {32: "dword", 64: "qword", 128: "xmmword", 256: "ymmword", 512: "zmmword"}


def reg_name(kind, num):
    return {"xmm": "xmm%d", "ymm": "ymm%d", "zmm": "zmm%d", "k": "k%d"}[kind] % num


def dst_kind(e):
    for o in e["operands"]:
        if o["role"] in ("dst", "dst_src1", "acc"):
            return {"k": "k", "rflags": "rflags", "gpr32": "gpr"}.get(o["kind"], "vec")
    return "vec"


def variants(e):
    """Yield (variant_name, opts) for one entry. opts: mask in {plain,merge,zero}, er, sae, bcast, imm."""
    enc, fam, vl, scalar = e["encoding"], e["family"], e["vl"], e["scalar"] is not None
    mem = any(o["kind"] == "mem" for o in e["operands"])
    bcast_ok = any(o.get("broadcast") for o in e["operands"])
    has_imm = any(o["role"] == "imm" for o in e["operands"])
    masks = ["plain"]
    if enc == "evex":
        masks = ["plain", "merge"] if e["masking"] == ["zero(k-dest)"] else ["plain", "merge", "zero"]
    imms = list(range(32 if enc != "legacy" else 8)) if has_imm else [None]
    for imm in imms:
        for m in masks:
            yield "%s%s" % (m, "" if imm is None else "_imm%02X" % imm), dict(mask=m, er=None, sae=False, bcast=False, imm=imm)
        if enc == "evex" and not mem and (vl == 512 or scalar) and e["fp_sensitive"]:
            if fam in ER_FAMILIES:
                for r in range(4):
                    yield "plain_er%d" % r, dict(mask="plain", er=r, sae=False, bcast=False, imm=imm)
            elif fam in SAE_FAMILIES:
                yield "plain_sae%s" % ("" if imm is None else "_imm%02X" % imm), dict(mask="plain", er=None, sae=True, bcast=False, imm=imm)
    if mem and bcast_ok:
        for m in masks:
            yield "%s_bcast" % m, dict(mask=m, er=None, sae=False, bcast=True, imm=None)


def build_asm(e, opt):
    """Instruction text and the expected register per XED operand name."""
    enc = e["encoding"]
    base = {"evex": {"dst": 16, "acc": 16, "src1": 17, "src": 17, "src2": 18},
            "vex": {"dst": 0, "src1": 1, "src": 1, "src2": 2},
            "legacy": {"dst_src1": 0, "dst": 0, "src1": 1, "src": 1, "src2": 2}}[enc]
    if e["family"] == "FP.COMI.f32":
        base = {"src1": 1, "src2": 2}
    texts, expect = [], {}
    for o in e["operands"]:
        role, kind, xed = o["role"], o["kind"], o["xed"]
        if role == "mask":
            if opt["mask"] == "plain":
                expect[xed] = "K0"
            else:
                expect[xed] = "K1"
            continue
        if kind == "rflags":
            continue
        if kind == "imm8":
            texts.append("0x%02x" % opt["imm"])          # asmparse infers the width from the digits ("0" fails)
            expect["IMM0"] = "IMM:0x%x" % opt["imm"]       # decode-back check of the immediate (review 2026-10-16)
            continue
        if kind == "mem":
            if opt["bcast"]:
                t = "dword ptr [rax]{1to%d}" % (e["vl"] // 32)
            else:
                t = "%s ptr [rax]" % MEMW[o["width"]]
            texts.append(t)
            expect[xed] = "MEM:RAX"
            continue
        if kind == "gpr32":
            texts.append("eax")
            expect[xed] = "EAX"
            continue
        if kind == "k":                      # compare into a mask
            r = "k2"
            expect[xed] = "K2"
        else:
            r = reg_name(kind, base[role])
            expect[xed] = r.upper()
        if role in ("dst", "acc", "dst_src1") and enc == "evex":
            # the plain variant names k0 explicitly: XED's asmparse refuses an EVEX-only register set without it
            r += "{k0}" if opt["mask"] == "plain" else "{k1}" + ("{z}" if opt["mask"] == "zero" else "")
        texts.append(r)
    if opt["er"] is not None:
        texts.append("{%s}" % ER_NAMES[opt["er"]])
    elif opt["sae"]:
        texts.append("{sae}")
    return "%s %s" % (e["key"]["iclass"].lower(), ", ".join(texts)), expect


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def encode(xed_bin, asm):
    rc, out = run([os.path.join(xed_bin, "xed-enc-asmparse.exe"), "-64", asm])
    m = re.search(r"^\.byte (.*)$", out, re.M)
    if not m:
        return None, out
    return bytes(int(x, 16) for x in m.group(1).split(",")), out


def decode(xed_bin, b):
    rc, out = run([os.path.join(xed_bin, "xed.exe"), "-64", "-v", "4", "-d", b.hex()])
    lines = out.splitlines()
    info = {"raw": out}
    for i, ln in enumerate(lines):
        if ln.strip().upper() == b.hex().upper() and i + 1 < len(lines):
            head = lines[i + 1].split(" ", 2)
            info["iclass"], info["iform"] = head[0], head[1]
            fields = {}
            for tok in head[2].split(", ") if len(head) > 2 else []:
                tok = tok.strip()
                if ":" in tok:
                    k, v = tok.split(":", 1)
                    fields[k] = v
                elif tok:
                    fields[tok] = "1"
            info["fields"] = fields
            break
    m = re.search(r"^SHORT:\s+(.*)$", out, re.M)
    info["short"] = m.group(1).strip() if m else None
    return info


def check(e, opt, expect, info, b=None):
    errs = []
    f = info.get("fields", {})
    if info.get("iclass") != e["key"]["iclass"]:
        errs.append("iclass %s" % info.get("iclass"))
    for xed, want in expect.items():
        if want == "MEM:RAX":
            if "MEM0" not in f or "RAX" not in f["MEM0"].upper():
                errs.append("MEM0 %s" % f.get("MEM0"))
        elif want.startswith("IMM:"):
            # XED -v 4 prints e.g. IMM0:0x1f (lower case, no leading zeros): compare as numbers
            got = f.get(xed)
            try:
                ok = got is not None and int(got, 16) == int(want[4:], 16)
            except ValueError:
                ok = False
            if not ok:
                errs.append("%s=%s want %s" % (xed, got, want[4:]))
            if b is not None and not any(o["kind"] == "mem" for o in e["operands"]) and b[-1] != int(want[4:], 16):
                errs.append("last byte 0x%02x is not the immediate %s" % (b[-1], want[4:]))
        elif f.get(xed) != want:
            errs.append("%s=%s want %s" % (xed, f.get(xed), want))
    if e["encoding"] == "evex":
        if (opt["mask"] == "zero") != ("ZEROING" in f):
            errs.append("zeroing field")
        if opt["er"] is not None:
            if f.get("ROUNDC") != str(opt["er"] + 1) or "SAE" not in f:
                errs.append("er fields ROUNDC=%s" % f.get("ROUNDC"))
        elif opt["sae"]:
            if "SAE" not in f:
                errs.append("sae field")
        else:
            if "ROUNDC" in f or ("SAE" in f and not opt["bcast"]):
                errs.append("unexpected er/sae fields")
        if opt["bcast"] != ("BCAST" in f):
            errs.append("bcast field")
    return errs


MASM_HEAD = """; stubs.asm -- GENERATED by stubgen.py from the X2 semantics table. Do not edit.
; One leaf routine per (entry, operand variant). ABI: rcx -> x2case (256 bytes), rdx -> x2out (128 bytes).
; Uses only volatile state (rax, r8, r9, zmm0-2, zmm16-18, k1, k2, RFLAGS) and restores MXCSR to 1F80h.
; The instruction under test is emitted as raw bytes from XED, so the assembler never picks an encoding.
OPTION PROLOGUE:NONE
OPTION EPILOGUE:NONE
.data
ALIGN 4
x2_mxcsr_default DD 00001F80h
.code
"""


def masm_stub(name, b, dk, rax_field, comment, rflags):
    out = ["; %s" % comment, "ALIGN 16", "%s PROC" % name]
    out += ["    vmovdqu64 zmm16, zmmword ptr [rcx+192]", "    vmovdqu64 zmm17, zmmword ptr [rcx+64]",
            "    vmovdqu64 zmm18, zmmword ptr [rcx+128]", "    vmovdqu64 zmm0, zmmword ptr [rcx+192]",
            "    vmovdqu64 zmm1, zmmword ptr [rcx+64]", "    vmovdqu64 zmm2, zmmword ptr [rcx+128]",
            "    kmovq k1, qword ptr [rcx+8]", "    kmovq k2, qword ptr [rcx+40]",
            "    mov rax, qword ptr [rcx+%d]" % rax_field]
    if rflags:
        out += ["    push qword ptr [rcx+24]", "    popfq"]
    out += ["    vldmxcsr dword ptr [rcx]", "    db " + ", ".join("0%02Xh" % x for x in b)]
    if rflags:
        out += ["    pushfq", "    pop r8", "    mov qword ptr [rdx+72], r8"]
    out += ["    vstmxcsr dword ptr [rdx+64]", "    kmovq r9, k2", "    mov qword ptr [rdx+80], r9",
            "    mov qword ptr [rdx+88], rax",
            "    vmovdqu64 zmmword ptr [rdx], %s" % ("zmm16" if dk == "evex" else "zmm0"),
            "    vldmxcsr dword ptr [x2_mxcsr_default]", "    ret", "%s ENDP" % name, ""]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sem-root", required=True)
    ap.add_argument("--xed-bin", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    sys.path.insert(0, a.sem_root)
    from semantics import table                                   # noqa: E402
    bundle = table.bundle_hash()
    os.makedirs(a.out, exist_ok=True)
    stubs, errors, keymiss = [], [], []
    for ei, e in enumerate(table.ENTRIES):
        ch = table.content_hash(e, bundle)
        sem = e["sem"]
        for vname, opt in variants(e):
            asm, expect = build_asm(e, opt)
            b, raw = encode(a.xed_bin, asm)
            rec = {"id": len(stubs), "name": "x2stub_%04d" % len(stubs), "entry_index": ei,
                   "iclass": e["key"]["iclass"], "iform": e["key"]["iform"],
                   "iform_status": e["key"]["iform_status"], "content_hash": ch, "family": e["family"],
                   "variant": vname, "asm": asm, "opts": opt}
            if b is None:
                errors.append({"stub": "(not assigned)", "iform": e["key"]["iform"], "variant": vname, "asm": asm,
                               "error": "encode failed", "xed": raw[-300:]})
                continue
            info = decode(a.xed_bin, b)
            errs = check(e, opt, expect, info, b)
            key_ok = info.get("iform") == e["key"]["iform"]
            if not key_ok:
                if e["key"]["iform_status"] == "provisional":
                    keymiss.append({"iform": e["key"]["iform"], "decoded": info.get("iform"), "variant": vname})
                else:
                    errs.append("iform %s" % info.get("iform"))
            if errs:
                errors.append({"stub": rec["name"], "asm": asm, "errors": errs, "decoded": info.get("short"),
                               "fields": info.get("fields")})
            dk = dst_kind(e)
            rec.update({
                "bytes": b.hex(), "decoded_iclass": info.get("iclass"), "decoded_iform": info.get("iform"),
                "decoded_short": info.get("short"), "key_ok": int(key_ok), "check_errors": errs,
                "sem": {"builder": BUILDER[sem["builder"]], "fn": FN[sem.get("fn")], "encoding": ENC[e["encoding"]],
                        "vl": e["vl"], "scalar": int(e["scalar"] is not None), "maskmode": MASKMODE[opt["mask"]],
                        "er": -1 if opt["er"] is None else opt["er"], "sae": int(opt["sae"]),
                        "mem": int(any(o["kind"] == "mem" for o in e["operands"])), "bcast": int(opt["bcast"]),
                        "imm": -1 if opt["imm"] is None else opt["imm"], "trunc": int(bool(sem.get("trunc"))),
                        "signalling": int(bool(sem.get("signalling"))), "src_eb": sem.get("src_eb", 32),
                        "dst_eb": sem.get("dst_eb", 32), "saturate": int(bool(sem.get("saturate"))),
                        "dst_kind": DSTKIND[dk]},
                "rax_field": 16 if any(o["kind"] == "mem" for o in e["operands"]) else 32,
                "rflags": int(dk == "rflags"),
            })
            stubs.append(rec)
    # ---- negative control of the immediate check: a wrong imm8 must be reported (the stub itself is unchanged)
    imm_control = None
    for s in stubs:
        if s["opts"]["imm"] is not None:
            e = table.ENTRIES[s["entry_index"]]
            wrong = dict(s["opts"], imm=(s["opts"]["imm"] + 1) & 0x1F)
            _, exp_wrong = build_asm(e, wrong)
            bb = bytes.fromhex(s["bytes"])
            imm_control = bool(check(e, wrong, exp_wrong, decode(a.xed_bin, bb), bb))
            if not imm_control:
                errors.append({"stub": s["name"], "error": "immediate check negative control: a wrong imm8 passed"})
            break
    # ---- emit
    asm_lines = [MASM_HEAD]
    for s in stubs:
        asm_lines += masm_stub(s["name"], bytes.fromhex(s["bytes"]), "evex" if s["sem"]["encoding"] == 2 else "x",
                               s["rax_field"], "%s %s | %s | %s" % (s["iform"], s["variant"], s["asm"], s["decoded_short"]),
                               s["rflags"])
    asm_lines.append("END")
    manifest = {"semantics_bundle": bundle, "n_stubs": len(stubs), "errors": errors,
                "provisional_key_mismatches": keymiss, "stubs": stubs,
                "xed": "v2026.08.23 (0bcb6237345c5066726dcc08b3d87928df3b5b26), Windows MSVC build"}
    mblob = json.dumps(manifest, sort_keys=True, indent=1).encode()
    mhash = hashlib.sha256(mblob).hexdigest()
    with open(os.path.join(a.out, "stubs_manifest.json"), "wb") as f:
        f.write(mblob)
    with open(os.path.join(a.out, "stubs.asm"), "w", newline="\r\n") as f:
        f.write("\n".join(asm_lines) + "\n")
    c = ["/* stubs_table.c -- GENERATED by stubgen.py. Do not edit. */", '#include "x2harness.h"', ""]
    for s in stubs:
        c.append("extern void %s(const x2case *, x2out *);" % s["name"])
    c += ["", "const x2stub X2_STUBS[] = {"]
    for s in stubs:
        m = s["sem"]
        c.append('  {%d, "%s", %s, %d, "%s", "%s", "%s", "%s", %d, {%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d}, %d, "%s"},' % (
            s["id"], s["name"], s["name"], s["entry_index"], s["iform"], s["decoded_iform"] or "?", s["variant"],
            s["content_hash"], s["key_ok"], m["builder"], m["fn"], m["encoding"], m["vl"], m["scalar"], m["maskmode"],
            m["er"], m["sae"], m["mem"], m["bcast"], m["imm"], m["trunc"], m["signalling"], m["src_eb"], m["dst_eb"],
            m["saturate"], m["dst_kind"], len(s["bytes"]) // 2, s["bytes"]))
    c += ["};", "const int X2_NSTUBS = %d;" % len(stubs),
          'const char X2_STUB_MANIFEST_SHA256[] = "%s";' % mhash,
          'const char X2_SEMANTICS_BUNDLE[] = "%s";' % bundle, ""]
    with open(os.path.join(a.out, "stubs_table.c"), "w", newline="\n") as f:
        f.write("\n".join(c))
    print(json.dumps({"n_stubs": len(stubs), "errors": len(errors), "provisional_key_mismatches": len(keymiss),
                      "imm_stubs_checked": sum(1 for s in stubs if s["opts"]["imm"] is not None),
                      "imm_check_negative_control_detected": imm_control,
                      "manifest_sha256": mhash, "semantics_bundle": bundle}, indent=1))
    for er in errors[:40]:
        print("ERROR", json.dumps(er))
    seen = set()
    for km in keymiss:
        if km["iform"] not in seen:
            seen.add(km["iform"])
            print("PROVISIONAL KEY %s -> XED decodes %s" % (km["iform"], km["decoded"]))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
