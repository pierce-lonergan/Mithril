#!/usr/bin/env python3
"""baseline.py -- X0 §4.5: the intrinsic-implied baseline B_iform / B_mnem, computed before freeze from
Hearth's source and Intel's intrinsics XML only. Writes experiments/x0-census/class/B_iform.json.

Usage:
  python -I baseline.py --hearth HEARTH_CLONE --xml x86-intel.xml
                        [--xed-tables ../class/xed_tables.tsv] [--hand-map ../class/hand_map.csv]
                        [--out ../class/B_iform.json] [--check]

Inputs and pins (the script refuses to run on anything else):
  * Hearth b5d3f14: the census files are read from the working tree of HEARTH_CLONE and must have
    the git blob SHA-1s of record §2 (computed here as sha1("blob <len>\\0" + bytes); no git needed).
  * rust-lang/stdarch intrinsics_data/x86-intel.xml at commit STDARCH_COMMIT, SHA-256 XML_SHA256
    (Intel Intrinsics Guide data, version 3.6.9 dated 07/12/2024).
  * XED's iform -> iclass table: class/xed_tables.tsv (pinned XED v2026.08.23), SHA-256 pinned.
  * class/hand_map.csv: hand mappings, one row per XML <instruction> that has no xed attribute or
    whose xed attribute is not an iform of the pinned XED.

Rule (record §4.5): the intrinsic set is every distinct identifier matching _mm[0-9]*_[a-z0-9_]+ in
quant_avx2.c and quant_avx512.c. Each is looked up by exact name (an absent entry is a fatal error
unless hand-mapped; none is absent at the pinned inputs). Zero <instruction> elements = "no single
instruction": counted, adds nothing. Otherwise the union of the instructions' xed attributes, each
replaced by its hand_map.csv iform where the XED check requires it. No intrinsic is excluded by name.
B_iform = union of iforms; B_mnem = their iclasses via XED's table; T_forms = min(|B_iform|, 105).

Standard library only; Python >= 3.8. Deterministic output.
"""
import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
HEARTH_COMMIT = "b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220"
HEARTH_BLOBS = {  # record §2, git blob SHA-1 at b5d3f14
    "engine/src/quant.c": "e95496945c254335c0d25aafb374575e0db930fe",
    "engine/src/quant_avx2.c": "a2004d22fd50c62b9bffa52b77b02870cd066986",
    "engine/src/quant_avx512.c": "9c7586b16e589989edec35c4bf8c1eee373da886",
    "engine/src/hx_quant.h": "df7e75e3e14f7281e80d47b20fab67a2ab5c99cb",
    "engine/src/hx_platform.h": "53141baa62f703508b50c5e511617732c97f5b2e",
    "engine/include/hearth.h": "0bbc9c9d93da2832d8ca5a5f494c3c1e120beaec",
    "CMakeLists.txt": "217ca743186ac066ee7c13b4ef416bb3704e3d30",
}
SIMD_FILES = ("engine/src/quant_avx2.c", "engine/src/quant_avx512.c")
ALL_FILES = ("engine/src/quant.c",) + SIMD_FILES
STDARCH_COMMIT = "eb9b3025937c85bd271a3ca46a681cd52739db12"
XML_SHA256 = "6762a50652a35ef663fd532ed83b789d19bbc2ac7e94b1771f19d666d96c2c30"
XED_TABLES_SHA256 = "1db25e7f5f02b5796d06cbb94f4cb5ab7d8230ed1091bacae485fa5c517d1d13"
G02 = {"intrinsics": 130, "no_single_instruction": 23, "forms": 105, "mnemonics": 74}  # G02 §1, "my count"
T_FORMS_CAP = 105  # record §4.5 [target]
NAME_RE = re.compile(r"_mm[0-9]*_[a-z0-9_]+")
# Sequence intrinsics whose presence P2/P3(b) and arm P depend on (record §4.5, §5 P2).
SEQ_RE = re.compile(r"_mm[0-9]*_(?:mask_|maskz_|mask3_)?(reduce_[a-z0-9_]+|f(?:n)?m(?:add|sub)[a-z0-9_]*|"
                    r"fmaddsub[a-z0-9_]*|fmsubadd[a-z0-9_]*|rcp[a-z0-9_]*|rsqrt[a-z0-9_]*|hadd_[a-z0-9_]+)")


def git_blob_sha1(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load_hearth(root):
    src, problems = {}, []
    for rel, blob in HEARTH_BLOBS.items():
        with open(os.path.join(root, rel), "rb") as f:
            data = f.read()
        got = git_blob_sha1(data)
        if got != blob:
            problems.append("%s blob %s != %s" % (rel, got, blob))
        src[rel] = data.decode("utf-8")
    if problems:
        raise SystemExit("Hearth source does not match b5d3f14: " + "; ".join(problems))
    return src


def load_iform_map(path):
    sha = sha256_file(path)
    if sha != XED_TABLES_SHA256:
        raise SystemExit("xed_tables.tsv SHA-256 %s != pinned %s" % (sha, XED_TABLES_SHA256))
    m = {}
    with open(path, encoding="ascii") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if p[0] == "IFORM":
                m[p[1]] = {"iclass": p[2], "category": p[3], "extension": p[4], "isa_set": p[5]}
    return sha, m


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hearth", required=True)
    ap.add_argument("--xml", required=True)
    ap.add_argument("--xed-tables", default=os.path.join(HERE, "..", "class", "xed_tables.tsv"))
    ap.add_argument("--hand-map", default=os.path.join(HERE, "..", "class", "hand_map.csv"))
    ap.add_argument("--out", default=os.path.join(HERE, "..", "class", "B_iform.json"))
    ap.add_argument("--check", action="store_true", help="do not write; exit 1 if the output would differ")
    a = ap.parse_args()

    src = load_hearth(a.hearth)
    xml_sha = sha256_file(a.xml)
    if xml_sha != XML_SHA256:
        raise SystemExit("x86-intel.xml SHA-256 %s != pinned %s" % (xml_sha, XML_SHA256))
    xed_sha, iform_map = load_iform_map(a.xed_tables)
    hand_sha = sha256_file(a.hand_map)
    with open(a.hand_map, encoding="utf-8", newline="") as f:
        hand = {(r["intrinsic"], r["instruction_name"], r["form"]): r for r in csv.DictReader(f)}

    # intrinsic set, with source locations
    names, where = set(), {}
    for rel in SIMD_FILES:
        for ln, line in enumerate(src[rel].split("\n"), 1):
            for n in NAME_RE.findall(line):
                names.add(n)
                where.setdefault(n, []).append("%s:%d" % (os.path.basename(rel), ln))
    root = ET.parse(a.xml).getroot()
    xml_version = (root.get("version"), root.get("date"))
    by_name = {}
    for e in root.findall("intrinsic"):
        by_name.setdefault(e.get("name"), []).append(e)

    problems, used_hand, intrinsics = [], set(), {}
    for n in sorted(names):
        es = by_name.get(n)
        if not es:
            problems.append("intrinsic %s absent from the XML and not hand-mapped" % n)
            continue
        if len(es) != 1:
            problems.append("intrinsic %s has %d XML entries" % (n, len(es)))
        e = es[0]
        ins = []
        for i in e.findall("instruction"):
            key = (n, i.get("name"), i.get("form") or "")
            xed = i.get("xed")
            rec = {"name": i.get("name"), "form": i.get("form"), "xml_xed": xed}
            if xed and xed in iform_map:
                rec.update(iform=xed, source="xml")
            elif key in hand:
                rec.update(iform=hand[key]["iform"], source="hand_map")
                used_hand.add(key)
                if hand[key]["iform"] not in iform_map:
                    problems.append("hand_map iform %s for %s is not an XED iform" % (hand[key]["iform"], n))
                if (hand[key]["xml_xed"] or None) != xed:
                    problems.append("hand_map row for %s records xml_xed %r but the XML has %r" % (n, hand[key]["xml_xed"], xed))
            else:
                problems.append("%s: <instruction %s %r> has %s and no hand_map row" % (
                    n, i.get("name"), i.get("form"), "xed=%s (not an XED iform)" % xed if xed else "no xed attribute"))
                continue
            rec["iclass"] = iform_map[rec["iform"]]["iclass"]
            ins.append(rec)
        intrinsics[n] = {"cpuid": [c.text for c in e.findall("CPUID")], "tech": e.get("tech"),
                         "category": [c.text for c in e.findall("category")], "instructions": ins,
                         "iforms": sorted({r["iform"] for r in ins}), "no_single_instruction": not e.findall("instruction"),
                         "source_sites": where[n]}
    unused = sorted(set(hand) - used_hand)
    if unused:
        problems.append("hand_map rows not used: %s" % unused)

    b_iform = sorted({f for v in intrinsics.values() for f in v["iforms"]})
    b_mnem = sorted({iform_map[f]["iclass"] for f in b_iform})
    xml_forms = sorted({(r["name"], r["form"]) for v in intrinsics.values() for r in v["instructions"]})
    xml_mnem = sorted({r["name"] for v in intrinsics.values() for r in v["instructions"]})
    no_single = sorted(n for n, v in intrinsics.items() if v["no_single_instruction"])
    t_forms = min(len(b_iform), T_FORMS_CAP)
    # category S/G split of B_iform by XED extension (record §4.3)
    S_EXT = {"SSE", "SSE2", "SSE3", "SSSE3", "SSE4", "AVX", "AVX2", "AVX2GATHER", "FMA", "F16C", "AVX512EVEX", "AVX512VEX"}
    prefix = {}
    for n in names:
        p = n.split("_")[1]
        prefix[p] = prefix.get(p, 0) + 1
    seq = {}
    for rel in ALL_FILES:
        for ln, line in enumerate(src[rel].split("\n"), 1):
            for m in SEQ_RE.finditer(line):
                seq.setdefault(m.group(0), []).append("%s:%d" % (os.path.basename(rel), ln))
    out = {
        "record": "X0-census §4.5",
        "inputs": {
            "hearth_commit": HEARTH_COMMIT, "hearth_blobs": HEARTH_BLOBS,
            "stdarch_commit": STDARCH_COMMIT,
            "xml_path": "intrinsics_data/x86-intel.xml", "xml_sha256": xml_sha,
            "xml_version": xml_version[0], "xml_date": xml_version[1],
            "xed_tables_sha256": xed_sha, "hand_map_sha256": hand_sha,
        },
        "rule": "union of XML <instruction xed=...> per intrinsic; hand_map.csv where the XML gives no xed "
                "attribute or one the pinned XED does not define; zero instruction elements = no single instruction",
        "counts": {
            "intrinsics": len(names), "by_prefix": dict(sorted(prefix.items())),
            "no_single_instruction": len(no_single), "b_iform": len(b_iform), "b_mnem": len(b_mnem),
            "b_iform_category_S": sum(1 for f in b_iform if iform_map[f]["extension"] in S_EXT),
            "t_forms": t_forms, "xml_form_strings": len(xml_forms), "xml_instruction_names": len(xml_mnem),
            "hand_mapped_instructions": len(used_hand),
        },
        "reconciliation_g02": {
            "g02": G02,
            "intrinsics": [len(names), G02["intrinsics"]],
            "no_single_instruction": [len(no_single), G02["no_single_instruction"]],
            "forms": {"b_iform_xed_iforms": len(b_iform), "xml_distinct_name_form_strings": len(xml_forms),
                      "g02": G02["forms"]},
            "mnemonics": {"b_mnem_xed_iclasses": len(b_mnem), "xml_distinct_instruction_names": len(xml_mnem),
                          "g02": G02["mnemonics"]},
        },
        "t_forms": {"value": t_forms, "rule": "min(|B_iform|, 105)", "cap": T_FORMS_CAP},
        "no_single_instruction": no_single,
        "b_iform": b_iform,
        "b_mnem": b_mnem,
        "xml_forms": [list(x) for x in xml_forms],
        "intrinsics": intrinsics,
        "source_checks": {
            "sequence_intrinsics_in_census_files": {k: v for k, v in sorted(seq.items())},
            "fma_rcp_rsqrt_reduce_present": sorted(k for k in seq if not k.startswith(("_mm256_hadd", "_mm_hadd", "_mm512_hadd"))),
        },
        "problems": problems,
    }
    data = (json.dumps(out, indent=1, sort_keys=False) + "\n").encode("utf-8")
    sha = hashlib.sha256(data).hexdigest()
    if a.check:
        same = os.path.exists(a.out) and open(a.out, "rb").read() == data
        print("B_iform.json %s (sha256 %s); problems %d" % ("unchanged" if same else "WOULD CHANGE", sha, len(problems)))
        return 0 if same and not problems else 1
    with open(a.out, "wb") as f:
        f.write(data)
    c = out["counts"]
    print("intrinsics %d %s; no single instruction %d; |B_iform| %d; |B_mnem| %d; T_forms %d; XML form strings %d; "
          "hand-mapped %d; problems %d; sha256 %s" % (c["intrinsics"], c["by_prefix"], c["no_single_instruction"],
                                                    c["b_iform"], c["b_mnem"], c["t_forms"], c["xml_form_strings"],
                                                    c["hand_mapped_instructions"], len(problems), sha))
    print("sequence intrinsics:", json.dumps(out["source_checks"]))
    for p in problems:
        print("PROBLEM:", p, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
