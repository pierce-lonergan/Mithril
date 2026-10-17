#!/usr/bin/env python3
"""x0_build.py -- census build records (record §5 P1 compile rule, §6 reproducibility, Appendix C `builds`).

Subcommands:
  exec     Run ONE compile and write its build record.
             census build (Ninja / Makefiles configurations): --db compile_commands.json --as FILE --verbatim
                 runs the configure's entry for FILE exactly as written (argv and directory), so the object lands
                 where the generator puts it;
             replay (NON-Hearth regression inputs, probes): --db DB --as FILE --src SRC --obj OBJ [--extra ARG]
                 runs DB's command line for FILE with the source and object swapped (x0_flags.py replay);
             twin (§4.6): --from-record BUILD1.json --obj TWIN.obj --extra /Z7 (or -g)
                 runs the captured command line of build 1 with exactly that one flag added.
           Common: --config CFG --file NAME --build-index K --kind census|twin|replay|probe --record OUT.json
                   --log OUT.log [--frozen-db DB --frozen-as FILE] [--no-listing]
  msbuild  Build records of the census files from a Visual Studio (MSBuild) build's detailed log (configuration A;
           record §2: A's exact cl lines and objects are those of the census build itself):
             --log build.log --project-dir BUILD_DIR --files quant.c,quant_avx2.c,quant_avx512.c --config A
             --build-index K --outdir DIR [--design-time A-vs.design_time_cl_lines.txt] [--msbuild-rc N]
             [--reference-record DIR_OF_BUILD_1]

Every record carries the fields judge.py reads (record Appendix C, x0prep additions): config, file, build_index, rc,
compiler_ran, compiler_sha256 {binary basename: SHA-256} for exactly the binaries the configuration's Table 2.1 pin
lists (cl.exe + c1.dll + c2.dll next to cl.exe; clang-cl.exe; the gcc driver's real file + cc1; clang's real file),
argv_sha256, argv_matches_frozen, errors [{file, line, text}] (MSVC/clang-cl `file(line[,col]): [fatal] error ...`
and GCC/Clang `file:line[:col]: [fatal] error: ...`; errors without a location get file null), includes [path] and
ice. Includes come from a separate listing pass that never writes an object: the same argv without its plumbing,
plus `/showIncludes /Zs` (cl, clang-cl) or `-H -fsyntax-only` (gcc, clang) [the census build's own argv stays
exactly the frozen one]. Internal compiler errors: MSVC C1001 / "INTERNAL COMPILER ERROR", clang "PLEASE submit a
bug report" or "frontend command failed due to signal", GCC "internal compiler error".

argv_matches_frozen:
  * exec: the compiler path (case- and slash-insensitive on Windows) and the flags without per-file plumbing
    (x0_flags.plumbing: source, -o/-MF/-MT/-MQ/-MD/-MMD for GNU drivers, /Fo, /Fd, -c, /c, --) equal those of the
    frozen entry (--frozen-db, the pre-freeze capture). A twin record compares with exactly its one added flag
    removed and records `twin_flag`.
  * msbuild (A): build 1's line IS A's frozen line (record §2). It is compared with the frozen design-time
    ClCompile line of the same file (A-vs.design_time_cl_lines.txt); the token differences are always listed
    (`frozen_diff`). x0final revision (review of 2026-10-16/17; record §5 P1): argv_matches_frozen is true only if,
    after the plumbing (/c, /Fo, /Fd, the source) and the console-only switches /nologo and /diagnostics:column
    [inference: these change the compiler's printed output only] are removed from both, the build line is the
    design-time line plus exactly EXPECTED_A_DELTA (/O2: the frozen vcxproj's Release Optimization MaxSpeed, which
    the design-time lines omit), with every other token equal and in the same order (MSVC switches are last-wins,
    so order matters). Measured on a NON-Hearth Visual Studio project (runbook/logs/x0final_rev_probes.log): the
    build line is the design-time line plus /nologo, /diagnostics:column, /O2 and the /Fd plumbing, in order.
    Build 2's line must also equal build 1's (--reference-record), or argv_matches_frozen is false.
  * msbuild single-file fallback (x0final revision): MSBuild stops a target at the first failed CL task, so a
    genuine failure of one batch leaves the files of later batches uncompiled [M, the same probe]. The driver then
    compiles each census file without a CL task in the build's log with `msbuild PROJECT /t:ClCompile
    /p:Configuration=Release /p:Platform=x64 /p:SelectedFiles=SRC` (one file, the same CL task and line; measured on
    the probe) and passes that log here (--single-log FILE=LOG); the file's record then comes from it
    (`fallback`: "single-file ClCompile").
Per-file rc in an MSBuild build: the CL task's exit status (error MSB6006 "exited with code N", else 1 for a
FAILED task) when the file's own section of the output (cl echoes each source name before compiling it) holds an
error or its object is missing or older than the build; otherwise 0 (cl compiles the files of a batch
independently).
Standard library only; Python >= 3.8. Run with python -I.
"""
import argparse
import datetime
import hashlib
import json
import os
import collections
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import x0_flags  # noqa: E402

CONSOLE_ONLY = {"/nologo", "-nologo", "/diagnostics:column", "-diagnostics:column"}
EXPECTED_A_DELTA = ["/O2"]           # Release Optimization=MaxSpeed of the frozen vcxproj; the design-time lines omit it
MSVC_ERR = re.compile(r"^\s*(.*?)\((\d+)(?:,\d+)?\)\s*:\s*(?:fatal\s+)?error\b(?:\s+[A-Z]+\d+)?\s*:\s*(.*?)(?:\s+\[[^\]]*\.vcxproj\])?\s*$")
GNU_ERR = re.compile(r"^\s*(.*?):(\d+):(?:\d+:)?\s*(?:fatal\s+)?error:\s*(.*)$")
NOLOC_ERR = re.compile(r"^\s*(?:cl|clang-cl|clang|gcc|cc1|[\w.-]*gcc[\w.-]*)(?:\.exe)?\s*:\s*(?:Command line\s+)?(?:fatal\s+)?error\b(.*)$", re.I)
ICE_RE = re.compile(r"fatal error C1001|INTERNAL COMPILER ERROR|PLEASE submit a bug report|"
                    r"frontend command failed due to signal|internal compiler error", re.I)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def compiler_binaries(argv0, env=None):
    """{basename: path} of the binaries the Table 2.1 pin of this compiler lists."""
    p = os.path.realpath(argv0)
    base = os.path.basename(p)
    out = {base: p}
    low = base.lower()
    if low == "cl.exe":
        d = os.path.dirname(p)
        for b in ("c1.dll", "c2.dll"):
            out[b] = os.path.join(d, b)
    elif re.search(r"gcc", low) and "clang" not in low:
        r = subprocess.run([argv0, "-print-prog-name=cc1"], capture_output=True, text=True, env=env)
        cc1 = r.stdout.strip()
        if cc1:
            out["cc1"] = os.path.realpath(cc1)
    return out


def hash_binaries(bins):
    out = {}
    for k, p in sorted(bins.items()):
        out[k] = sha256_file(p) if os.path.isfile(p) else None
    return out


def is_msvc_style(argv0):
    return x0_flags.is_msvc_driver(argv0)


def parse_errors(text):
    errs = []
    for line in text.splitlines():
        m = MSVC_ERR.match(line)
        if m and not line.lstrip().startswith(("Note:", "note:")):
            errs.append({"file": m.group(1).strip().strip('"'), "line": int(m.group(2)), "text": m.group(3).strip()[:400]})
            continue
        m = GNU_ERR.match(line)
        if m:
            errs.append({"file": m.group(1).strip(), "line": int(m.group(2)), "text": m.group(3).strip()[:400]})
            continue
        m = NOLOC_ERR.match(line)
        if m:
            errs.append({"file": None, "line": None, "text": line.strip()[:400]})
    return errs


def parse_includes(text, msvc):
    inc = []
    for line in text.splitlines():
        if msvc:
            m = re.match(r"^Note: including file:\s*(.*\S)\s*$", line)
        else:
            m = re.match(r"^\.+ (.*\S)\s*$", line)
        if m:
            inc.append(m.group(1))
    seen, out = set(), []
    for p in inc:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def flags_of(argv, src):
    drop = x0_flags.plumbing(argv, src)
    return [x for k, x in enumerate(argv[1:], 1) if k not in drop]


def norm_exe(p):
    return os.path.normcase(os.path.normpath(p)) if os.name == "nt" or re.match(r"^[A-Za-z]:", p) else p


def run(argv, cwd, env=None):
    t0 = now()
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, errors="replace", env=env)
        return {"started": True, "rc": p.returncode, "out": p.stdout, "err": p.stderr, "utc_start": t0, "utc_end": now()}
    except OSError as e:
        return {"started": False, "rc": None, "out": "", "err": "could not start: %s" % e, "utc_start": t0, "utc_end": now()}


def listing(argv, src, cwd):
    msvc = is_msvc_style(argv[0])
    lst = [argv[0]] + flags_of(argv, src) + (["/showIncludes", "/Zs"] if msvc else ["-H", "-fsyntax-only"]) + [src]
    r = run(lst, cwd)
    return {"argv": lst, "rc": r["rc"], "includes": parse_includes(r["out"] + "\n" + r["err"], msvc)}, r


def make_record(cfg, fname, bi, kind, argv, cwd, src, obj, res, frozen_cmp, lst, extra=None):
    text = (res["out"] or "") + "\n" + (res["err"] or "")
    bins = compiler_binaries(argv[0]) if res["started"] else {}
    rec = {"config": cfg, "file": fname, "build_index": bi, "kind": kind, "argv": argv,
           "argv_sha256": hashlib.sha256(json.dumps(argv).encode()).hexdigest(), "cwd": cwd, "source": src,
           "object": obj, "rc": res["rc"] if res["rc"] is not None else -1, "compiler_ran": bool(res["started"]),
           "compiler_binaries": bins, "compiler_sha256": hash_binaries(bins), "utc_start": res["utc_start"],
           "utc_end": res["utc_end"], "errors": parse_errors(text), "ice": bool(ICE_RE.search(text)),
           "warnings": sum(1 for line in text.splitlines() if re.search(r"\bwarning\b", line, re.I)),
           "includes": lst["includes"] if lst else [], "listing": {k: v for k, v in (lst or {}).items() if k != "includes"},
           "object_exists": bool(obj and os.path.isfile(obj)), "object_sha256": sha256_file(obj) if obj and os.path.isfile(obj) else None}
    rec.update(frozen_cmp)
    if extra:
        rec["twin_flag"] = extra
    return rec, text


def frozen_compare(argv, src, frozen_argv, frozen_src, extra=None):
    if frozen_argv is None:
        return {"argv_matches_frozen": False, "frozen_diff": {"detail": "no frozen command line given"}}
    a = flags_of(argv, src)
    if extra:
        a = [t for t in a if t not in extra] if all(t in a for t in extra) else a + ["<missing twin flag>"]
    f = flags_of(frozen_argv, frozen_src)
    same_exe = norm_exe(argv[0]) == norm_exe(frozen_argv[0])
    ok = same_exe and a == f
    diff = {}
    if not ok:
        diff = {"compiler": [argv[0], frozen_argv[0]] if not same_exe else None,
                "only_run": [t for t in a if t not in f], "only_frozen": [t for t in f if t not in a],
                "order_differs": sorted(a) == sorted(f) and a != f}
    return {"argv_matches_frozen": ok, "frozen_diff": diff, "frozen_argv": frozen_argv}


def load_db_entry(db, name):
    with open(db) as f:
        entries = json.load(f)
    e = x0_flags.find(entries, name)[0]
    return e, x0_flags.entry_argv(e)


def cmd_exec(a):
    extra = list(a.extra or [])
    if a.from_record:
        b1 = json.load(open(a.from_record))
        base, bsrc, cwd = b1["argv"], b1["source"], b1["cwd"]
        src = os.path.abspath(a.src) if a.src else bsrc        # arm P: another source with this line
        msvc = is_msvc_style(base[0])
        argv = [base[0]] + flags_of(base, bsrc) + extra + (["/c", "/Fo" + os.path.abspath(a.obj), src] if msvc
                                                            else ["-c", "-o", os.path.abspath(a.obj), src])
        frozen_argv, frozen_src = base, bsrc
        obj = os.path.abspath(a.obj)
    else:
        e, eargv = load_db_entry(a.db, a.as_)
        cwd = e["directory"]
        if a.verbatim:
            if extra or a.src or a.obj:
                raise SystemExit("--verbatim takes no --extra, --src or --obj")
            argv, src = eargv, e["file"]
            out = e.get("output")
            if not out:
                m = next((t for t in argv if t.lower().startswith(("/fo", "-fo"))), None)
                out = m[3:] if m else None
                if out is None and "-o" in argv:
                    out = argv[argv.index("-o") + 1]
            obj = out if (out is None or os.path.isabs(out)) else os.path.join(cwd, out)
        else:
            msvc = is_msvc_style(eargv[0])
            src, obj = os.path.abspath(a.src), os.path.abspath(a.obj)
            argv = [eargv[0]] + flags_of(eargv, e["file"]) + extra + (["/c", "/Fo" + obj, src] if msvc
                                                                       else ["-c", "-o", obj, src])
        frozen_argv, frozen_src = eargv, e["file"]
        if a.frozen_db:
            fe, fargv = load_db_entry(a.frozen_db, a.frozen_as or a.as_)
            frozen_argv, frozen_src = fargv, fe["file"]
    if obj:
        os.makedirs(os.path.dirname(obj), exist_ok=True)
        if os.path.exists(obj):
            os.remove(obj)                         # a build from clean: no stale object can satisfy "object exists"
    fc = frozen_compare(argv, src, frozen_argv, frozen_src, extra or None)
    for p in (a.record, a.log):
        os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    res = run(argv, cwd)
    lst = None
    if not a.no_listing and res["started"]:
        lst, lres = listing(argv, src, cwd)
    rec, text = make_record(a.config, a.file, a.build_index, a.kind, argv, cwd, src, obj, res, fc, lst, extra or None)
    with open(a.log, "w", encoding="utf-8") as f:
        f.write("ARGV %s\nCWD %s\nRC %s\n---- output\n%s\n" % (json.dumps(argv), cwd, res["rc"], text))
        if lst:
            f.write("---- listing pass %s rc %s\n" % (json.dumps(lst["argv"]), lst["rc"]))
    rec["log"] = os.path.abspath(a.log)
    rec["log_sha256"] = sha256_file(a.log)
    with open(a.record, "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    print(json.dumps({"config": a.config, "file": a.file, "build_index": a.build_index, "kind": a.kind, "rc": rec["rc"],
                      "object_exists": rec["object_exists"], "errors": len(rec["errors"]), "ice": rec["ice"],
                      "argv_matches_frozen": rec["argv_matches_frozen"], "includes": len(rec["includes"])}))
    return 0


# ------------------------------------------------------------------------------------------- MSBuild (A)
def parse_design_time(path):
    """A-vs.design_time_cl_lines.txt -> {source basename (lower): [tokens]}"""
    out, cmd = {}, None
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    for line in lines:
        if line.startswith("cmd:"):
            cmd = x0_flags.split_windows(line[4:].strip())
        elif line.startswith("files:") and cmd is not None:
            for f in line[6:].strip().split(";"):
                if f.strip():
                    out[os.path.basename(f.strip()).lower()] = cmd
            cmd = None
    return out


def msbuild_cl_blocks(text):
    """CL task blocks of a detailed MSBuild log: [{"cmd": tokens, "sections": {src basename lower: [lines]},
    "rc": int, "failed": bool}]."""
    blocks, cur = [], None
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith('Task "CL"') and "skipped" not in line:
            cur = {"cmd": None, "out": [], "failed": False, "rc": 0, "tracking": False}
            continue
        if cur is None:
            continue
        if line.startswith('Done executing task "CL"'):
            cur["failed"] = "FAILED" in line
            blocks.append(cur)
            cur = None
            continue
        m = re.match(r"^\s+(\S.*?\\cl\.exe) (/c .*)$", line, re.I) or re.match(r'^\s+"(.*?\\cl\.exe)" (/c .*)$', line, re.I)
        if m and cur["cmd"] is None:
            cur["cmd"] = [m.group(1)] + x0_flags.split_windows(m.group(2))
            continue
        if cur["cmd"] is None:
            continue
        if line.strip() == "Tracking command:":
            cur["tracking"] = True
            continue
        if cur["tracking"]:
            cur["tracking"] = False                    # the tracker's own command line
            if "Tracker.exe" in line or "tracker.exe" in line.lower():
                continue
        m = re.search(r'error MSB6006: "CL\.exe" exited with code (-?\d+)', line, re.I)
        if m:
            cur["rc"] = int(m.group(1))
        cur["out"].append(line)
    for b in blocks:
        srcs = [t for t in (b["cmd"] or [])[1:] if not t.startswith(("/", "-")) and re.search(r"\.(c|cpp)$", t, re.I)]
        b["sources"] = srcs
        names = {os.path.basename(s).lower(): s for s in srcs}
        sec, cur_name = {}, None
        for line in b["out"]:
            s = line.strip()
            if s.lower() in names:
                cur_name = s.lower()
                sec.setdefault(cur_name, [])
                continue
            if cur_name:
                sec[cur_name].append(line)
        b["sections"] = sec
        if b["failed"] and not b["rc"]:
            b["rc"] = 1
    return blocks


def design_time_compare(argv, src, design_tokens):
    """record §5 P1 (A), x0final revision: the build line must be the design-time line plus exactly
    EXPECTED_A_DELTA, in the same order, once plumbing and the console-only switches are removed from both."""
    def strip(tokens, drop_src):
        return [t for t in tokens if not t.lower().startswith(("/fo", "/fd", "-fo", "-fd")) and t not in ("/c", "-c")
                and not (drop_src and t == src)]
    ft, bt = strip(design_tokens, False), strip(argv[1:], True)
    console = [t for t in bt + ft if t.lower() in CONSOLE_ONLY]
    ft2 = [t for t in ft if t.lower() not in CONSOLE_ONLY]
    bt2 = [t for t in bt if t.lower() not in CONSOLE_ONLY]
    cb, cf = collections.Counter(bt2), collections.Counter(ft2)
    only_b, only_f = sorted((cb - cf).elements()), sorted((cf - cb).elements())
    rest = list(bt2)
    for t in EXPECTED_A_DELTA:
        if t in rest:
            rest.remove(t)
    in_order = rest == ft2
    ok = only_b == sorted(EXPECTED_A_DELTA) and not only_f and in_order
    return {"argv_matches_frozen": ok,
            "frozen_diff": {"only_build": only_b, "only_design_time": only_f, "expected_delta": EXPECTED_A_DELTA,
                            "console_only_removed": console, "same_order_without_delta": in_order, "tolerated": ok},
            "frozen_argv": design_tokens}


def cmd_msbuild(a):
    text = open(a.log, encoding="utf-8", errors="replace").read()
    blocks = msbuild_cl_blocks(text)
    singles = {}
    for kv in a.single_log or []:
        f, _, lp = kv.partition("=")
        singles[f.lower()] = lp
    design = parse_design_time(a.design_time) if a.design_time else None
    os.makedirs(a.outdir, exist_ok=True)
    summary = []
    for fname in [x for x in a.files.split(",") if x]:
        key = fname.lower()
        log_used, fallback = a.log, None
        b = next((x for x in blocks if any(os.path.basename(s).lower() == key for s in x["sources"])), None)
        if b is None and key in singles and os.path.exists(singles[key]):
            sb = msbuild_cl_blocks(open(singles[key], encoding="utf-8", errors="replace").read())
            b = next((x for x in sb if any(os.path.basename(s).lower() == key for s in x["sources"])), None)
            if b is not None:
                log_used, fallback = singles[key], "single-file ClCompile (MSBuild stopped before this file's CL task)"
        recfile = os.path.join(a.outdir, "%s.b%d.json" % (fname, a.build_index))
        if b is None:
            rec = {"config": a.config, "file": fname, "build_index": a.build_index, "kind": "census", "rc": -1,
                   "compiler_ran": False, "compiler_sha256": {}, "argv_sha256": None, "argv_matches_frozen": False,
                   "errors": [], "includes": [], "ice": False, "object_exists": False,
                   "detail": "no CL task compiled %s in %s%s" % (fname, a.log, " or in its single-file log" if key in singles else ""),
                   "msbuild_rc": a.msbuild_rc}
        else:
            full = b["cmd"]
            src = next(s for s in b["sources"] if os.path.basename(s).lower() == key)
            # the file's own command line: the batch line with only this source
            argv = [t for t in full if t not in b["sources"] or t == src]
            fo = next((t for t in argv if t.lower().startswith("/fo")), None)
            objdir = fo[3:].strip('"') if fo else ""
            if objdir.endswith(("\\", "/")) or not objdir.lower().endswith(".obj"):
                obj = os.path.join(a.project_dir, objdir, os.path.splitext(os.path.basename(src))[0] + ".obj")
            else:
                obj = os.path.join(a.project_dir, objdir)
            obj = os.path.normpath(obj)
            sec = "\n".join(b["sections"].get(key, []))
            # x0final revision: an error located in ANOTHER source of the batch belongs to that file, even when the
            # log prints it inside this file's section (measured: a broken other.c's error after quant.c's echo)
            others = {os.path.basename(s_).lower() for s_ in b["sources"]} - {key}
            # (MSBuild's own MSB6006 line, located in a .targets file, reports the batch's exit status, not this file)
            errs = [e for e in parse_errors(sec)
                    if not (e.get("file") and (os.path.basename(e["file"].replace("\\", "/")).lower() in others
                                               or e["file"].lower().endswith((".targets", ".props"))))]
            fresh = os.path.isfile(obj) and os.path.getmtime(obj) >= (a.since or 0)
            if fresh and not errs:
                rc = 0                                   # cl compiles the files of a batch independently
            else:
                rc = b["rc"] or 1
            bins = compiler_binaries(full[0])
            lst, _ = listing(argv, src, a.project_dir)
            # frozen comparison (record §2, §5 P1): the design-time line plus exactly EXPECTED_A_DELTA, in order
            fc = {"argv_matches_frozen": False, "frozen_diff": {"detail": "no design-time line"}}
            if design is not None and key in design:
                fc = design_time_compare(argv, src, design[key])
            if a.reference_record:
                ref = json.load(open(os.path.join(a.reference_record, "%s.b1.json" % fname)))
                same = [t for t in ref.get("argv", [])] == argv
                fc["same_line_as_build_1"] = same
                if not same:
                    fc["argv_matches_frozen"] = False
            rec = {"config": a.config, "file": fname, "build_index": a.build_index, "kind": "census", "argv": argv,
                   "batch_sources": b["sources"], "argv_sha256": hashlib.sha256(json.dumps(argv).encode()).hexdigest(),
                   "cwd": a.project_dir, "source": src, "object": obj, "rc": rc, "cl_task_rc": b["rc"],
                   "cl_task_failed": b["failed"], "compiler_ran": True, "compiler_binaries": bins,
                   "compiler_sha256": hash_binaries(bins), "errors": errs, "ice": bool(ICE_RE.search(sec)),
                   "includes": lst["includes"], "listing": {k: v for k, v in lst.items() if k != "includes"},
                   "object_exists": os.path.isfile(obj), "object_fresh": fresh,
                   "object_sha256": sha256_file(obj) if os.path.isfile(obj) else None, "msbuild_rc": a.msbuild_rc,
                   "msbuild_log": os.path.abspath(log_used), "msbuild_log_sha256": sha256_file(log_used),
                   "fallback": fallback}
            rec.update(fc)
        with open(recfile, "w") as f:
            json.dump(rec, f, indent=1, sort_keys=True)
        summary.append({k: rec.get(k) for k in ("file", "rc", "object_exists", "argv_matches_frozen")})
    print(json.dumps(summary))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("exec")
    e.add_argument("--db")
    e.add_argument("--as", dest="as_")
    e.add_argument("--src")
    e.add_argument("--obj")
    e.add_argument("--verbatim", action="store_true")
    e.add_argument("--from-record")
    e.add_argument("--extra", action="append", default=[])
    e.add_argument("--frozen-db")
    e.add_argument("--frozen-as")
    e.add_argument("--config", required=True)
    e.add_argument("--file", required=True)
    e.add_argument("--build-index", type=int, required=True)
    e.add_argument("--kind", default="census", choices=("census", "twin", "replay", "probe"))
    e.add_argument("--record", required=True)
    e.add_argument("--log", required=True)
    e.add_argument("--no-listing", action="store_true")
    m = sub.add_parser("msbuild")
    m.add_argument("--log", required=True)
    m.add_argument("--project-dir", required=True)
    m.add_argument("--files", required=True)
    m.add_argument("--config", default="A")
    m.add_argument("--build-index", type=int, required=True)
    m.add_argument("--outdir", required=True)
    m.add_argument("--design-time")
    m.add_argument("--msbuild-rc", type=int)
    m.add_argument("--since", type=float, help="build start (epoch seconds); objects older than this are stale")
    m.add_argument("--reference-record", help="directory with build 1's records (for build 2)")
    m.add_argument("--single-log", action="append", default=[],
                   help="FILE=LOG: the detailed log of the single-file ClCompile fallback for FILE")
    a = ap.parse_args()
    return {"exec": cmd_exec, "msbuild": cmd_msbuild}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
