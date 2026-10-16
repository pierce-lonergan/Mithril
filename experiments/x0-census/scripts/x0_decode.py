#!/usr/bin/env python3
"""x0_decode.py -- decode every function found by x0_extract.py with Intel XED.

Usage:
  python3 x0_decode.py MANIFEST.json [MANIFEST.json ...] -o OUTDIR --xed PATH/TO/xed
                       [--objdump PATH/TO/llvm-objdump] [-j 8] [--attr-cache FILE]

Two XED passes, both with the stock `xed` command-line tool:
  1. sweep:      xed -64 -cet -ir <range.bin> -b <start> -v 4 -isa-set
                 per code range (linear sweep from the function's first byte). Gives offset,
                 length, bytes, ICLASS, IFORM, CATEGORY, EXTENSION, ISA_SET, the XED operand
                 fields (MASK, ZEROING, ROUNDC, SAE, BCAST, VL, ...) and decode errors.
  2. attributes: xed -64 -cet -d <hex>
                 once per distinct instruction encoding (cached), for the ATTRIBUTES line
                 (MXCSR, MXCSR_RD, MASKOP_EVEX, SIMD_SCALAR, ...). ICLASS/IFORM/ISA_SET from both
                 passes must agree; disagreements are reported as anomalies.
  -cet (default; --no-cet to drop) makes XED decode endbr64/CET encodings as CET instructions
  instead of reserved NOPs (Ubuntu GCC emits endbr64 by default: -fcf-protection=full).
With --objdump, instruction boundaries are cross-checked against llvm-objdump -d.

Outputs in OUTDIR:
  instructions.jsonl   one record per decoded instruction (and per undecodable span)
  functions.json       per function: tuples (iclass, iform, extension, isa_set, attributes) with counts
  anomalies.json       undecodable bytes, relocation/boundary problems, padding, gaps, crosscheck
  summary.json         totals per configuration label
Exit status 0 = no anomalies of severity "error".
Standard library only; Python >= 3.8.
"""
import argparse
import bisect
import collections
import concurrent.futures as cf
import hashlib
import json
import os
import re
import subprocess
import sys

XDIS_RE = re.compile(r"^XDIS ([0-9a-fA-F]+): (\S+)\s+(\S+)\s+(\S+)\s+([0-9A-F]+)\s*(.*)$")
ERR_RE = re.compile(r"^ERROR: (\S+) Could not decode at offset: (0x[0-9a-fA-F]+) len: (\d+) PC: (0x[0-9a-fA-F]+): \[([0-9A-Fa-f]*)\]")
ICLASS_RE = re.compile(r"^([A-Z][A-Z0-9_]*) ([A-Z][A-Za-z0-9_]*)(?: (.*))?$")
EVEX_FIELDS = ("MASK", "ZEROING", "ROUNDC", "SAE", "BCAST", "BCRC", "VL", "LLRC", "VEXVALID")
TERMINATORS = {"RET_NEAR", "RET_FAR", "JMP", "JMP_FAR", "UD2", "INT3", "HLT", "IRET", "IRETD", "IRETQ"}
PADDING_ICLASSES = {"NOP", "NOP2", "NOP3", "NOP4", "NOP5", "NOP6", "NOP7", "NOP8", "NOP9", "INT3", "FNOP"}


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def parse_fields(s):
    out = {}
    if not s:
        return out
    for tok in s.split(", "):
        tok = tok.strip()
        if not tok:
            continue
        k, _, v = tok.partition(":")
        out[k] = v if v else True
    return out


def xed_sweep(xed, mode, path, base):
    """Run the -ir sweep; return (instructions, errors, declared_error_count)."""
    rc, out, err = run([xed] + mode + ["-ir", path, "-b", hex(base), "-v", "4", "-isa-set"])
    insts, errors, pending, nerr = [], [], None, None
    for line in out.splitlines():
        if line.startswith("XDIS "):
            m = XDIS_RE.match(line)
            if not m:
                errors.append({"kind": "unparsed_xdis", "line": line})
                continue
            addr, cat, ext, isa, hx, dis = m.groups()
            rec = {"offset": int(addr, 16), "len": len(hx) // 2, "hex": hx.lower(), "category": cat,
                   "extension": ext, "isa_set": isa, "disasm": dis.strip()}
            if pending:
                rec["iclass"], rec["iform"], fields = pending
                rec["fields"] = {k: fields[k] for k in EVEX_FIELDS if k in fields}
            else:
                errors.append({"kind": "xdis_without_iclass_line", "offset": rec["offset"]})
            pending = None
            insts.append(rec)
        elif line.startswith("ERROR:"):
            m = ERR_RE.match(line)
            if m:
                kind, off, ln, pc, hx = m.groups()
                errors.append({"kind": "undecodable", "xed_error": kind, "offset": int(pc, 16), "len": int(ln),
                               "hex": hx.lower()})
            else:
                errors.append({"kind": "xed_error_line", "line": line})
            pending = None
        elif line.startswith("# Errors:"):
            nerr = int(line.split(":")[1])
        elif line[:1].isdigit() or line.startswith(("YDIS:", "#", "Mapped", "ASSUMED BASE")) or not line.strip():
            continue
        else:
            m = ICLASS_RE.match(line)
            # an XED instruction header is "ICLASS IFORM field, field, ..." where IFORM is ICLASS or
            # starts with "ICLASS_"; anything else (e.g. "RESETTING STATS") is xed chatter.
            if m and (m.group(2) == m.group(1) or m.group(2).startswith(m.group(1) + "_")):
                pending = (m.group(1), m.group(2), parse_fields(m.group(3)))
    if rc != 0:
        errors.append({"kind": "xed_exit", "rc": rc, "stderr": err.strip()[:500]})
    return insts, errors, nerr


def xed_single(xed, mode, hx):
    rc, out, err = run([xed] + mode + ["-d", hx])
    rec = {}
    for line in out.splitlines():
        k, _, v = line.partition(":")
        k = k.strip()
        if k in ("ICLASS", "CATEGORY", "EXTENSION", "IFORM", "ISA_SET", "SHORT"):
            rec[k.lower()] = v.strip()
        elif k == "ATTRIBUTES":
            rec["attributes"] = sorted(v.split())
    if "iclass" not in rec:
        rec["error"] = (out + err).strip()[:300]
    return hx, rec


def objdump_boundaries(objdump, path, code_sections):
    """Map section index -> {offset: (len, text)} from llvm-objdump -d (no symbolic operands)."""
    rc, out, err = run([objdump, "-d", "--no-print-imm-hex", "--x86-asm-syntax=intel", path])
    if rc != 0:
        return None, "llvm-objdump failed: " + err.strip()[:300]
    order = [s for s in sorted(code_sections, key=lambda s: s["index"]) if s["size"] > 0]
    res, cur, k = {}, None, -1
    line_re = re.compile(r"^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2}[ \t])+)\s*(.*)$")
    for line in out.splitlines():
        if line.startswith("Disassembly of section "):
            name = line[len("Disassembly of section "):].rstrip(":")
            k += 1
            if k >= len(order) or order[k]["name"] != name:
                return None, "section order mismatch at %r" % name
            cur = res.setdefault(order[k]["index"], {})
            continue
        m = line_re.match(line)
        if m and cur is not None:
            cur[int(m.group(1), 16)] = (len(m.group(2).split()), m.group(3).strip())
    return res, None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifests", nargs="+")
    ap.add_argument("-o", "--outdir", required=True)
    ap.add_argument("--xed", required=True)
    ap.add_argument("--objdump", help="llvm-objdump for boundary cross-check")
    ap.add_argument("-j", "--jobs", type=int, default=8, help="parallel xed processes (default 8)")
    ap.add_argument("--attr-cache", help="JSON cache of xed -d results keyed by hex (shared across runs)")
    ap.add_argument("--no-cet", action="store_true",
                    help="decode without XED's -cet mode (endbr64 then decodes as a reserved NOP)")
    ap.add_argument("--keep-tmp", action="store_true")
    a = ap.parse_args()
    mode = ["-64"] if a.no_cet else ["-64", "-cet"]
    os.makedirs(a.outdir, exist_ok=True)
    tmp = os.path.join(a.outdir, "_tmp")
    os.makedirs(tmp, exist_ok=True)
    rc, ver, _ = run([a.xed, "-version"])
    xed_version = (re.search(r"XED version: \[(.*?)\]", ver) or [None, "?"])[1]

    mans = []
    for p in a.manifests:
        with open(p) as f:
            m = json.load(f)
        mans.extend(m if isinstance(m, list) else [m])

    anomalies = []

    def anomaly(sev, kind, **kw):
        anomalies.append(dict(severity=sev, kind=kind, **kw))

    # ---- pass 1: sweeps (functions + gaps)
    jobs = []
    for mi, man in enumerate(mans):
        with open(man["object"], "rb") as f:
            data = f.read()
        if hashlib.sha256(data).hexdigest() != man["sha256"]:
            anomaly("error", "object_changed_since_extract", object=man["object"])
            continue
        for w in man.get("warnings", []):
            anomaly("warning", "extract_warning", object=man["object"], detail=w)
        for mm in man.get("crosscheck", {}).get("mismatches", []):
            anomaly("error", "symbol_crosscheck_mismatch", object=man["object"], detail=mm)
        units = [("func", f, r) for f in man["functions"] for r in f["code_ranges"]]
        units += [("gap", g, g) for g in man["gaps"] if g["fill"] not in ("int3", "zero")]
        for kind, owner, r in units:
            ln = r["end"] - r["start"]
            fn = os.path.join(tmp, "m%d_s%d_%x.bin" % (mi, owner["section"], r["start"]))
            with open(fn, "wb") as f:
                f.write(data[r["file_offset"]: r["file_offset"] + ln])
            jobs.append((mi, kind, owner, r, fn))

    def do_sweep(job):
        mi, kind, owner, r, fn = job
        return job, xed_sweep(a.xed, mode, fn, r["start"])

    with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
        sweeps = list(ex.map(do_sweep, jobs))

    # ---- pass 2: attributes per distinct encoding
    cache = {}
    if a.attr_cache and os.path.exists(a.attr_cache):
        with open(a.attr_cache) as f:
            cache = json.load(f)
        if cache.get("_xed_version") != xed_version or cache.get("_xed_mode") != mode:
            cache = {}
    cache["_xed_version"], cache["_xed_mode"] = xed_version, mode
    need = sorted({i["hex"] for _, (insts, _, _) in sweeps for i in insts} - set(cache))
    with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
        for hx, rec in ex.map(lambda h: xed_single(a.xed, mode, h), need):
            cache[hx] = rec
    if a.attr_cache:
        with open(a.attr_cache, "w") as f:
            json.dump(cache, f)

    # ---- objdump boundaries
    od = {}
    if a.objdump:
        for mi, man in enumerate(mans):
            res, err = objdump_boundaries(a.objdump, man["object"], man["code_sections"])
            if err:
                anomaly("error", "objdump_crosscheck_unavailable", object=man["object"], detail=err)
            od[mi] = res

    # ---- assemble
    out_insts = open(os.path.join(a.outdir, "instructions.jsonl"), "w")
    funcs_out = []
    per_label = collections.defaultdict(collections.Counter)
    tot = collections.Counter()
    by_func = collections.defaultdict(list)
    for job, (insts, errors, nerr) in sweeps:
        by_func[(job[0], job[1], id(job[2]))].append((job, insts, errors, nerr))
    for key, parts in by_func.items():
        mi, kind, owner = parts[0][0][0], parts[0][0][1], parts[0][0][2]
        man = mans[mi]
        label = man.get("label")
        name = owner.get("name", "<gap %s+%#x>" % (owner["section_name"], owner["start"]))
        all_insts = []
        for job, insts, errors, nerr in sorted(parts, key=lambda p: p[0][3]["start"]):
            r = job[3]
            covered = sum(i["len"] for i in insts) + sum(e.get("len", 0) for e in errors if e["kind"] == "undecodable")
            if covered != r["end"] - r["start"]:
                anomaly("error", "coverage_mismatch", object=man["object"], function=name,
                        range=[r["start"], r["end"]], covered=covered)
            for e in errors:
                anomaly("error", e["kind"], object=man["object"], function=name, detail=e)
            if nerr and nerr != len([e for e in errors if e["kind"] == "undecodable"]):
                anomaly("error", "xed_error_count_mismatch", object=man["object"], function=name, declared=nerr)
            all_insts.extend(insts)
            for e in errors:
                if e["kind"] == "undecodable":
                    out_insts.write(json.dumps({"label": label, "object": man["object"], "function": name,
                                                "section": owner["section_name"], "undecodable": True, **e}) + "\n")
        # attributes + consistency
        for i in all_insts:
            c = cache.get(i["hex"], {})
            i["attributes"] = c.get("attributes", [])
            if "error" in c:
                anomaly("error", "xed_d_failed", object=man["object"], function=name, hex=i["hex"], detail=c["error"])
            for k in ("iclass", "iform", "isa_set", "extension", "category"):
                if c.get(k) and i.get(k) and c[k] != i[k]:
                    anomaly("error", "xed_pass_disagreement", object=man["object"], function=name,
                            offset=i["offset"], field=k, sweep=i[k], single=c[k])
        # padding: trailing NOP/INT3 after the last terminator (only meaningful without a symbol size)
        last_term = max((n for n, i in enumerate(all_insts) if i.get("iclass") in TERMINATORS - {"INT3"}),
                        default=-1)
        for n, i in enumerate(all_insts):
            pad = kind == "gap" or (n > last_term and i.get("iclass") in PADDING_ICLASSES
                                    and owner.get("size_source") != "symbol_size")
            i["padding"] = bool(pad)
        if kind == "gap":
            nonpad = [i for i in all_insts if i.get("iclass") not in PADDING_ICLASSES]
            anomaly("error" if nonpad else "info", "gap_with_code" if nonpad else "padding_gap",
                    object=man["object"], section=owner["section_name"], range=[owner["start"], owner["end"]],
                    n_insts=len(all_insts), n_nonpadding=len(nonpad))
        # relocation fields must sit strictly inside one instruction
        if kind == "func":
            spans = [(i["offset"], i["offset"] + i["len"]) for i in all_insts]
            starts = [s for s, _ in spans]
            for rr in owner["relocs"]:
                if any(d["start"] <= rr["offset"] < d["end"] for d in owner["data_ranges"]):
                    continue
                k = bisect.bisect_right(starts, rr["offset"]) - 1
                ok = k >= 0 and spans[k][0] < rr["offset"] and rr["offset"] + rr["width"] <= spans[k][1]
                if not ok:
                    anomaly("error", "reloc_not_inside_instruction", object=man["object"], function=name,
                            reloc=rr)
            if owner["trailing_int3"]:
                anomaly("info", "trailing_int3_trimmed", object=man["object"], function=name,
                        bytes=owner["trailing_int3"])
            for d in owner["data_ranges"]:
                anomaly("info", "data_in_code_excluded", object=man["object"], function=name, range=[d["start"], d["end"]])
            npad = sum(1 for i in all_insts if i["padding"])
            if npad:
                anomaly("info", "trailing_padding_instructions", object=man["object"], function=name, count=npad)
        # objdump boundaries
        if od.get(mi) is not None and kind == "func":
            sec_od = od[mi].get(owner["section"], {})
            for i in all_insts:
                o = sec_od.get(i["offset"])
                if o is None or o[0] != i["len"] or "<unknown>" in o[1]:
                    anomaly("error", "objdump_boundary_mismatch", object=man["object"], function=name,
                            offset=i["offset"], xed_len=i["len"], objdump=o)
        for i in all_insts:
            rec = {"label": label, "object": man["object"], "function": name, "kind": kind,
                   "section": owner["section_name"], **i}
            out_insts.write(json.dumps(rec) + "\n")
        if kind == "func":
            tuples = collections.Counter()
            for i in all_insts:
                if i["padding"]:
                    continue
                t = (i.get("iclass"), i.get("iform"), i["extension"], i["isa_set"], " ".join(i["attributes"]))
                tuples[t] += 1
                per_label[label][t] += 1
            funcs_out.append({
                "label": label, "object": man["object"], "function": owner["name"], "aliases": owner["aliases"],
                "section": owner["section_name"], "start": owner["start"], "end": owner["end"],
                "size_source": owner["size_source"], "n_insts": sum(tuples.values()),
                "tuples": [{"iclass": t[0], "iform": t[1], "extension": t[2], "isa_set": t[3],
                            "attributes": t[4].split(), "count": n} for t, n in sorted(tuples.items(), key=str)],
            })
            tot["functions"] += 1
            tot["instructions"] += sum(tuples.values())
    out_insts.close()
    with open(os.path.join(a.outdir, "functions.json"), "w") as f:
        json.dump(funcs_out, f, indent=1)
    with open(os.path.join(a.outdir, "anomalies.json"), "w") as f:
        json.dump(anomalies, f, indent=1)
    sev = collections.Counter(x["severity"] for x in anomalies)
    kinds = collections.Counter((x["severity"], x["kind"]) for x in anomalies)
    summary = {"xed": a.xed, "xed_version": xed_version, "xed_mode": mode, "objdump": a.objdump,
               "manifests": a.manifests, "objects": [m["object"] for m in mans], **tot,
               "anomalies": dict(sev), "anomaly_kinds": {"%s:%s" % k: v for k, v in sorted(kinds.items())},
               "distinct_tuples_per_label": {str(k): len(v) for k, v in per_label.items()},
               "distinct_encodings_decoded_with_-d": len(need)}
    with open(os.path.join(a.outdir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    if not a.keep_tmp:
        for fn in os.listdir(tmp):
            os.remove(os.path.join(tmp, fn))
        os.rmdir(tmp)
    print(json.dumps(summary, indent=1))
    return 1 if sev.get("error") else 0


if __name__ == "__main__":
    sys.exit(main())
