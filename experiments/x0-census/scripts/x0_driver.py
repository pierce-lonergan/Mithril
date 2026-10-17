#!/usr/bin/env python3
"""x0_driver.py -- the single census driver (record §2, §4, §6, §7): one command per configuration, then one command
that assembles census.json and runs the Gatekeeper.

  init      python -I x0_driver.py init --run RUN --kind census|smoke --source DIR [--mock] [--profile hearth|regression]
            Writes RUN/run.json: run id, start time, host, the SHA-256 of every script pinned in
            class/frozen_inputs.json "scripts" (as the run uses them), and the source check. In census mode (kind
            census) it REFUSES unless (a) the record's status line reads FROZEN (--record, default
            docs/m0/prereg/X0-census.md next to this tree), (b) the 7 Hearth files carry exactly the blob hashes
            of record §2 (class/B_iform.json inputs.hearth_blobs) and the source tree is at the pinned Hearth commit,
            and (c) (x0final revision; pre-freeze review of 2026-10-17) this tree is a clean git checkout tied to the
            FREEZE POINT (freeze_checkout): `git status --porcelain` is empty for experiments/x0-census and the record,
            no ignored file other than __pycache__ lies under class/, scripts/ or flags/, the freeze point is the first
            commit at which the record reads FROZEN, the record at HEAD is the freeze point's record plus an appended
            amendment at most, every class/, scripts/ or flags/ path changed since the freeze point is named in that
            amendment, the --record file is that checkout's record, and every pinned script on disk equals its pin.
            run.json gets freeze_commit (the freeze point), run_commit (HEAD) and post_freeze_changes (x0_census.py
            copies them into census.json; judge.py V4 requires them). With --mock (smoke kind only) the source tree
            must contain the marker file X0_NOT_HEARTH instead; the record status is then not required.
  config    python -I x0_driver.py config --run RUN --config CFG --tools TOOLS.json
                   [--mode census|replay|probe] [--set SET.json] [--target hearth_core]
                   [--from-config CFG --from-file FILE] [--frozen-db DB] [--design-time FILE]
            census mode (A, A-ninja, B-cmake, C, D): configure twice from scratch (the pre-freeze configure commands:
              A Visual Studio 17 2022 -A x64; A-ninja and B-cmake Ninja; C and D Unix Makefiles; Release), build
              twice (A: `cmake --build --config Release --target T -- /m:1` with a detailed MSBuild log and a binary
              log, records by `x0_build.py msbuild`; the others: each census file's compile_commands.json entry run
              verbatim, records by `x0_build.py exec --verbatim`, compared with the frozen pre-freeze capture), the
              debug-info twin of build 1 (+/Z7 or +-g), the effective flags and P3(a) (A, A-ninja: the build's own
              argv; B-cmake, D: + the -### cc1 line; C: + gcc -Q --help=common,optimizers), then for each build:
              extract (one unit with the three files, 18 variants expected from the source), decode (-j 2), the twin
              attribution of each object, loops (Hearth's defaults).
            replay mode (NON-Hearth regression inputs, smoke/regression_set.json; the B-proxy arm,
              runbook/bproxy_set.json): every census file of SET.json is compiled with the frozen command line of the
              Hearth file it stands in for (x0_flags.py replay semantics), twice, plus the twin; one extraction unit
              per census file. probe mode (arm P, configuration P.<CFG>): the reduce probe compiled with <CFG>'s
              build-1 line of --from-file, twice, plus the twin; the wrappers are found by symbol.
            A smoke run (kind smoke) refuses to compile any file whose bytes are a pinned Hearth blob, or any C source or
            header of its source and include directories that shares a pair of consecutive normalised lines with a pinned
            Hearth file (guard_sources). In a census run (pre-freeze review of 2026-10-17) the step first re-checks that
            this tree's pinned scripts equal run.json's and class/frozen_inputs.json's hashes, that the checkout is still
            at run.json's run_commit (Windows) and that the Hearth blobs match; it refuses --frozen-db and
            --design-time; config.json records the scripts' hashes (x0_census.py compares them with run.json's).
  assemble  python -I x0_driver.py assemble --run RUN [--xml XML] [--freeze-commit SHA] [--qualify-tables]
            x0_census.py -> RUN/census.json, then judge.py -> RUN/verdict.json (the evaluation date is judge.py's).
            In a census run --freeze-commit and --scripts-commit are refused (the commits come from init) and the
            scripts are re-checked as in config.

Every external step is logged in RUN/<CFG>/config.json "steps" (argv, rc, start and end UTC, log file). A failed
step is recorded and the driver continues where the record says the failure is data (a compile failure of a census
file); it stops only for tooling it cannot proceed without (configure, missing tools). Thread use: one compiler or
MSBuild node at a time (`/m:1`; MSVC's back end may still use several threads per compile [inference]); XED with at
most 2 workers (-j 2). Never run before the record is FROZEN on Hearth (the init step enforces it).
Standard library only; Python >= 3.8. Run with python -I.
"""
import argparse
import datetime
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                       # experiments/x0-census
sys.path.insert(0, HERE)
import x0_extract  # noqa: E402
import x0_flags  # noqa: E402

CENSUS_FILES = ("quant.c", "quant_avx2.c", "quant_avx512.c")
HEARTH_SRC_REL = "engine/src"
FROZEN_DB = {"A-ninja": "flags/prefreeze/A-ninja.compile_commands.json",
             "B-cmake": "flags/prefreeze/B-cmake.compile_commands.json",
             "C": "flags/C-gcc.compile_commands.json", "D": "flags/D-clang.compile_commands.json",
             "B-proxy": "flags/prefreeze/B-proxy.argv.json"}
DESIGN_TIME_A = "flags/prefreeze/A-vs.design_time_cl_lines.txt"
ROLE = {"A": "release", "D": "release", "B-cmake": "union", "C": "union", "A-ninja": "union", "B-proxy": "secondary"}
HOST = {"A": "windows", "A-ninja": "windows", "B-cmake": "windows", "B-proxy": "windows", "C": "wsl", "D": "wsl"}
ABI = {"A": "win64", "A-ninja": "win64", "B-cmake": "win64", "B-proxy": "win64", "C": "sysv", "D": "sysv"}
TWIN_FLAG = {"A": "/Z7", "A-ninja": "/Z7", "B-cmake": "/Z7", "B-proxy": "/Z7", "C": "-g", "D": "-g"}


def localpath(p):
    """A path recorded on the other side of the desktop's Windows/WSL boundary, as this side sees it
    (drive path <-> /mnt/<drive>/...). Other paths are returned unchanged."""
    if not isinstance(p, str):
        return p
    if os.name == "nt":
        m = re.match(r"^/mnt/([a-zA-Z])/(.*)$", p)
        return (m.group(1).upper() + ":" + os.sep + m.group(2).replace("/", os.sep)) if m else p
    m = re.match(r"^([a-zA-Z]):[\\/](.*)$", p)
    return ("/mnt/%s/%s" % (m.group(1).lower(), m.group(2).replace(chr(92), "/"))) if m else p


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def sha256(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def jdump(obj, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, sort_keys=True)


def jload(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class Steps:
    def __init__(self, cfgdir):
        self.cfgdir, self.items = cfgdir, []
        os.makedirs(os.path.join(cfgdir, "logs"), exist_ok=True)

    def run(self, name, argv, cwd=None, env=None, log=None, fatal=False):
        log = log or os.path.join(self.cfgdir, "logs", "%s.log" % re.sub(r"[^\w.-]+", "_", name))
        t0 = utc()
        try:
            with open(log, "w", encoding="utf-8", errors="replace") as fh:
                p = subprocess.run(argv, cwd=cwd, env=env, stdout=fh, stderr=subprocess.STDOUT, text=True, errors="replace")
            rc = p.returncode
        except OSError as e:
            rc = None
            with open(log, "a", encoding="utf-8") as fh:
                fh.write("could not start: %s\n" % e)
        rec = {"step": name, "argv": argv, "cwd": cwd, "rc": rc, "utc_start": t0, "utc_end": utc(),
               "log": os.path.abspath(log)}
        self.items.append(rec)
        print("[%s] %s rc=%s" % (rec["utc_end"], name, rc), flush=True)
        if fatal and rc != 0:
            raise SystemExit("step %s failed (rc %s); see %s" % (name, rc, log))
        return rc, log

    def note(self, name, **kw):
        self.items.append(dict({"step": name, "utc_start": utc(), "utc_end": utc()}, **kw))


def py(tools):
    return [tools.get("python") or sys.executable, "-I"]


def script(name):
    return os.path.join(HERE, name)


def record_status(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("Status:"):
                return line.strip()
    return None


# ------------------------------------------------------------------------------------------- init
REL_RECORD = "docs/m0/prereg/X0-census.md"
FROZEN_DIRS = ("experiments/x0-census/class", "experiments/x0-census/scripts", "experiments/x0-census/flags")
REPO = os.path.dirname(os.path.dirname(ROOT))               # experiments/x0-census -> repository root


def pinned_script_hashes(pins):
    """SHA-256 of every file of class/frozen_inputs.json "scripts" as it is on disk under this tree (None: missing)."""
    out = {}
    for rel in sorted((pins.get("scripts") or {})):
        p = os.path.join(ROOT, *rel.split("/"))
        out[rel] = sha256(p) if os.path.exists(p) else None
    return out


def source_blob_check(source):
    blobs = (jload(os.path.join(ROOT, "class", "B_iform.json"), {}).get("inputs") or {}).get("hearth_blobs", {})
    src_check = {}
    for rel, want in sorted(blobs.items()):
        p = os.path.join(source, *rel.split("/"))
        have = x0_extract.git_blob_sha1(open(p, "rb").read()) if os.path.exists(p) else None
        src_check[rel] = {"pinned": want, "found": have, "ok": have == want}
    return src_check, bool(src_check) and all(x["ok"] for x in src_check.values())


def source_commit(source):
    """HEAD of the source tree: `git rev-parse HEAD`, or (when git refuses the tree, e.g. a WSL-made clone seen from
    Windows) a detached HEAD read from .git/HEAD; None otherwise."""
    try:
        p = subprocess.run(["git", "-C", source, "rev-parse", "HEAD"], capture_output=True, text=True)
        c = p.stdout.strip() if p.returncode == 0 else ""
        if re.match(r"^[0-9a-f]{40}$", c):
            return c
    except OSError:
        pass
    try:
        with open(os.path.join(source, ".git", "HEAD"), encoding="ascii") as f:
            c = f.read().strip()
        return c if re.match(r"^[0-9a-f]{40}$", c) else None
    except OSError:
        return None


def cmd_init(a):
    os.makedirs(a.run, exist_ok=True)
    pins = jload(os.path.join(ROOT, "class", "frozen_inputs.json"), {})
    scripts = pinned_script_hashes(pins)
    src_check, blobs_ok = source_blob_check(a.source)
    marker = os.path.exists(os.path.join(a.source, "X0_NOT_HEARTH"))
    status = record_status(a.record) if os.path.exists(a.record) else None
    tie = {}
    commit = source_commit(a.source)
    if a.kind == "census":
        if a.mock:
            raise SystemExit("REFUSED: --mock is for kind smoke only")
        if not (status or "").startswith("Status: FROZEN"):
            raise SystemExit("REFUSED: the record %s is not FROZEN (%r); no census collection before freeze" % (a.record, status))
        if not blobs_ok:
            raise SystemExit("REFUSED: Hearth source blobs differ from record §2: %s" % {k: v for k, v in src_check.items() if not v["ok"]})
        want = (jload(os.path.join(ROOT, "class", "B_iform.json"), {}).get("inputs") or {}).get("hearth_commit")
        if commit != want:
            raise SystemExit("REFUSED: the Hearth source tree is at %r, record §2 pins %s" % (commit, want))
        tie = freeze_checkout(a.record, pins, scripts)
    else:
        if blobs_ok:
            raise SystemExit("REFUSED: the source tree is Hearth b5d3f14 (blobs match); kind smoke never runs on Hearth")
        if a.mock and not marker:
            raise SystemExit("REFUSED: --mock needs the marker file X0_NOT_HEARTH in %s" % a.source)
    run = {"run_id": a.run_id or "%s-%s" % (a.kind, time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())), "kind": a.kind,
           "profile": a.profile, "mock": bool(a.mock), "utc_start": utc(), "host": platform.node(),
           "source": os.path.abspath(a.source), "hearth_commit": commit if a.kind == "census" else None,
           "source_commit": commit, "source_blobs": src_check, "source_blobs_ok": blobs_ok,
           "record_status": status, "scripts_sha256": scripts, "freeze_commit": tie.get("freeze_commit"),
           "run_commit": tie.get("run_commit"), "post_freeze_changes": tie.get("post_freeze_changes"),
           "record_appended_bytes": tie.get("record_appended_bytes"),
           "scripts_match_pins": scripts == (pins.get("scripts") or {}), "driver_argv": sys.argv}
    jdump(run, os.path.join(a.run, "run.json"))
    print(json.dumps({k: run[k] for k in ("run_id", "kind", "profile", "mock", "source_blobs_ok", "scripts_match_pins",
                                          "freeze_commit", "run_commit", "post_freeze_changes")}))
    return 0


def _git_runner(repo):
    def git(*args, binary=False):
        try:
            p = subprocess.run(["git", "-C", repo] + list(args), capture_output=True)
        except OSError as e:
            raise SystemExit("REFUSED: git is needed to tie the census to the freeze commit (%s)" % e)
        if p.returncode != 0:
            raise SystemExit("REFUSED: git %s failed in %s: %s" % (" ".join(args), repo,
                                                                  p.stderr.decode("utf-8", "replace").strip()[:300]))
        return p.stdout if binary else p.stdout.decode("utf-8", "replace")
    return git


def _status_line(text):
    return next((ln.strip() for ln in text.splitlines() if ln.startswith("Status:")), "")


def freeze_checkout(record, pins, scripts, git=None):
    """record §7, §8 item 9, judge.py V4: a census runs only from a clean git checkout tied to the FREEZE POINT, the
    first commit at which the record's status line reads FROZEN (docs/m0/README: "Its commit hash is the freeze
    point"; pre-freeze review of 2026-10-17: before, HEAD was taken as the freeze commit). Refuses unless:
      * the checkout is clean under experiments/x0-census and the record (`git status --porcelain`), and no ignored
        file other than a __pycache__ directory lies under class/, scripts/ or flags/ (`--ignored`: a sourceless
        scripts/<name>.pyc would be importable);
      * the record at HEAD begins, byte for byte, with the record at the freeze point (only an appended amendment
        may follow) and reads FROZEN;
      * every path under class/, scripts/ or flags/ that differs between the freeze point and HEAD is named in the
        appended amendment text (record §10: a logged tooling fix); such a run is post-freeze and lists them;
      * --record is this checkout's record and every pinned script on disk equals its pin.
    Returns {freeze_commit, run_commit (HEAD), post_freeze_changes, record_appended_bytes}."""
    repo = REPO
    git = git or _git_runner(repo)
    head = git("rev-parse", "HEAD").strip()
    dirty = git("status", "--porcelain", "--", "experiments/x0-census", REL_RECORD).strip()
    if dirty:
        raise SystemExit("REFUSED: the checkout %s has changes under experiments/x0-census or the record:\n%s" % (repo, dirty[:2000]))
    ign = [ln[3:] for ln in git("status", "--porcelain", "--ignored", "--", *FROZEN_DIRS).splitlines()
           if ln.startswith("!! ")]
    bad_ign = [p for p in ign if "__pycache__" not in p.strip('"').rstrip("/").split("/")]
    if bad_ign:
        raise SystemExit("REFUSED: ignored files under class/, scripts/ or flags/ (an ignored .pyc is importable): %s"
                         % bad_ign[:20])
    if os.path.normcase(os.path.abspath(record)) != os.path.normcase(os.path.abspath(os.path.join(repo, *REL_RECORD.split("/")))):
        raise SystemExit("REFUSED: --record %s is not the record of the checkout %s" % (record, repo))
    if scripts != (pins.get("scripts") or {}) or not scripts:
        raise SystemExit("REFUSED: the scripts on disk differ from class/frozen_inputs.json \"scripts\"")
    at_head = git("show", "HEAD:%s" % REL_RECORD, binary=True)
    if not _status_line(at_head.decode("utf-8", "replace")).startswith("Status: FROZEN"):
        raise SystemExit("REFUSED: the record at HEAD %s is not FROZEN (%r)" % (head, _status_line(at_head.decode("utf-8", "replace"))))
    freeze, at_freeze = None, None
    for c in git("log", "--format=%H", "--reverse", "HEAD", "--", REL_RECORD).split():
        txt = git("show", "%s:%s" % (c, REL_RECORD), binary=True)
        if _status_line(txt.decode("utf-8", "replace")).startswith("Status: FROZEN"):
            freeze, at_freeze = c, txt
            break
    if freeze is None:
        raise SystemExit("REFUSED: no commit in HEAD's history has the record reading FROZEN")
    if not at_head.startswith(at_freeze):
        raise SystemExit("REFUSED: the record at HEAD differs from the record at the freeze point %s other than by an "
                         "appended amendment (docs/m0/README: only a dated section appended at the end may change it)" % freeze)
    appended = at_head[len(at_freeze):].decode("utf-8", "replace")
    changed = [] if freeze == head else sorted(p for p in git("diff", "--name-only", freeze, head, "--", *FROZEN_DIRS).split() if p)
    unnamed = [p for p in changed if p not in appended and p[len("experiments/x0-census/"):] not in appended]
    if unnamed:
        raise SystemExit("REFUSED: %s changed after the freeze point %s without an amendment naming them (record §10): %s"
                         % (", ".join(FROZEN_DIRS), freeze, unnamed[:20]))
    return {"freeze_commit": freeze, "run_commit": head, "post_freeze_changes": changed,
            "record_appended_bytes": len(at_head) - len(at_freeze)}


def recheck_census_tree(run, pins):
    """config / assemble, kind census (pre-freeze review of 2026-10-17): the scripts these steps run (this tree) must
    be the ones init verified: equal to run.json scripts_sha256 and to class/frozen_inputs.json "scripts". On Windows
    (git installed on the desktop) the checkout's HEAD must still be run.json's run_commit with the record FROZEN; in
    WSL that re-check is skipped (the pins above identify the code). Returns the hashes and what was checked."""
    scripts = pinned_script_hashes(pins)
    if not scripts or scripts != (pins.get("scripts") or {}) or scripts != (run.get("scripts_sha256") or {}):
        diff = sorted(k for k in set(scripts) | set(run.get("scripts_sha256") or {})
                      if scripts.get(k) != (run.get("scripts_sha256") or {}).get(k) or scripts.get(k) != (pins.get("scripts") or {}).get(k))
        raise SystemExit("REFUSED: the scripts of this tree (%s) are not the ones init verified (run.json and "
                         "class/frozen_inputs.json): %s" % (ROOT, diff[:20]))
    checked = {"scripts": "equal to run.json and frozen_inputs.json"}
    if os.name == "nt":
        git = _git_runner(REPO)
        head = git("rev-parse", "HEAD").strip()
        if head != run.get("run_commit"):
            raise SystemExit("REFUSED: this checkout is at %s, init ran at %s" % (head, run.get("run_commit")))
        if not _status_line(git("show", "HEAD:%s" % REL_RECORD)).startswith("Status: FROZEN"):
            raise SystemExit("REFUSED: the record at HEAD is not FROZEN")
        checked["git"] = "HEAD %s equals run.json run_commit; record FROZEN" % head
    else:
        checked["git"] = "skipped outside Windows (WSL); the script pins identify the code"
    return scripts, checked


# ------------------------------------------------------------------------------------------- helpers
def compiler_banner(argv0):
    b = os.path.basename(argv0).lower()
    try:
        if b in ("cl.exe", "cl"):
            p = subprocess.run([argv0], capture_output=True, text=True, errors="replace")
            return (p.stderr or p.stdout).strip().splitlines()[0] if (p.stderr or p.stdout).strip() else None
        p = subprocess.run([argv0, "--version"], capture_output=True, text=True, errors="replace")
        return p.stdout.strip().splitlines()[0] if p.stdout.strip() else None
    except OSError:
        return None


def resource_dir_tree(argv0):
    """The include tree of clang's resource directory: {dir, files, sha256} (sha256 over the sorted relative paths, each
    + NUL + the file's SHA-256 digest, as runbook steps 70 and 71 computed the Table 2.1 pins). Pre-freeze review of
    2026-10-17: the clang-cl form `/clang:` is used for clang-cl only; before, any driver name containing "cl" got it,
    so D's `clang` printed nothing and its tree was recorded as null (run smoke-20261017T054918Z, D/config.json)."""
    try:
        p = subprocess.run([argv0, "/clang:-print-resource-dir"] if x0_flags.is_msvc_driver(argv0)
                           else [argv0, "-print-resource-dir"], capture_output=True, text=True)
        r = os.path.join(p.stdout.strip(), "include")
    except OSError:
        return None
    if not os.path.isdir(r):
        return None
    fs = sorted(os.path.relpath(os.path.join(d, f), r).replace(os.sep, "/") for d, _, ff in os.walk(r) for f in ff)
    h = hashlib.sha256()
    for f in fs:
        h.update(f.encode() + b"\0" + hashlib.sha256(open(os.path.join(r, f), "rb").read()).digest())
    return {"dir": r, "files": len(fs), "sha256": h.hexdigest()}


def headers_info(cfg, argv0):
    """The header environment of Table 2.1 (record §2): Windows SDK, UCRT and MSVC toolset versions (vcvars), the
    libc6-dev version (WSL), clang's resource-dir include tree. judge.py compares it with class/frozen_inputs.json
    "headers" (pre-freeze review of 2026-10-17); a mismatch makes every build of the configuration tooling `other`."""
    out = {}
    if HOST.get(cfg) == "windows":
        out.update(sdk=os.environ.get("WindowsSDKVersion"), ucrt=os.environ.get("UCRTVersion"),
                   vctools=os.environ.get("VCToolsVersion"))
    else:
        try:
            p = subprocess.run(["dpkg-query", "-W", "-f=${Version}", "libc6-dev"], capture_output=True, text=True)
            out["libc_dev"] = p.stdout.strip() or None
        except OSError:
            out["libc_dev"] = None
    if "clang" in os.path.basename(argv0).lower():
        out["resource_dir_sha256"] = resource_dir_tree(argv0)
    return out


def effective_flags(cfg, argv, src, cfgdir, tag, steps, dummy):
    """record §5 P3(a): the effective settings of one census command line, and the matcher result."""
    pats = x0_flags.load_patterns(os.path.join(ROOT, "class", "fp_flag_patterns.txt"))
    msvc = x0_flags.is_msvc_driver(argv[0])
    flags = [x for k, x in enumerate(argv[1:], 1) if k not in x0_flags.plumbing(argv, src)]
    cc1 = gccq = None
    ef = {"argv": argv, "cc1_argv": None, "gcc_q": None}
    fdir = os.path.join(cfgdir, "flags")
    os.makedirs(fdir, exist_ok=True)
    dobj = os.path.join(fdir, "dummy.obj" if msvc else "dummy.o")
    if cfg in ("B-cmake", "D", "B-proxy"):
        rc, log = steps.run("cc1:%s" % tag, [argv[0]] + flags + ["-###"] + (["/c", "/Fo" + dobj, dummy] if msvc else ["-c", "-o", dobj, dummy]),
                            log=os.path.join(fdir, "%s.cc1.txt" % tag))
        cc1 = x0_flags.parse_cc1(open(log, encoding="utf-8", errors="replace").read())
        ef["cc1_argv"] = cc1
        if cc1 is None:
            ef["error"] = "no -cc1 line in the -### output"
    if cfg == "C":
        rc, log = steps.run("gccq:%s" % tag, [argv[0]] + flags + ["-Q", "--help=common,optimizers", "-c", "-o", dobj, dummy],
                            log=os.path.join(fdir, "%s.gccq.txt" % tag))
        gccq = x0_flags.parse_gccq(open(log, encoding="utf-8", errors="replace").read())
        ef["gcc_q"] = {k: v for k, v in (x.split("\t", 1) for x in gccq)}
    m = x0_flags.match_p3a(pats, argv=argv, cc1=cc1, gccq=gccq)
    if cfg in ("B-cmake", "D", "B-proxy") and cc1 is None:
        m = {"error": "cc1 line missing: P3(a) not evaluated"}
    if cfg == "C" and not gccq:
        m = {"error": "gcc -Q output missing: P3(a) not evaluated"}
    return ef, m


def struct_slots(src_paths, struct_name, struct_src, index_names):
    fields, _ = x0_extract.parse_struct(open(struct_src, encoding="utf-8").read(), struct_name)
    n = 0
    for p in src_paths:
        tables, _ = x0_extract.parse_tables(open(p, encoding="utf-8").read(), struct_name)
        for t in tables.values():
            n += sum(1 for s in x0_extract.table_slots(fields, t, index_names) if s["source_function"])
    return n


def run_unit(steps, tools, cfgdir, rel, unit_files, struct_name, struct_src, index_names, expect, label, loops_args,
             twins, source_dirs, probe_functions=None):
    """extract, decode, twin attribution and loops for one extraction unit of one build (cfgdir/rel)."""
    udir = os.path.join(cfgdir, rel)
    tag = rel.replace(os.sep, "_").replace("/", "_")
    os.makedirs(udir, exist_ok=True)
    jdump({"unit": os.path.basename(udir), "files": unit_files}, os.path.join(udir, "unit.json"))
    man = os.path.join(udir, "manifest.json")
    argv = py(tools) + [script("x0_extract.py"), "-o", man, "--label", label, "--readobj", tools["readobj"]]
    if probe_functions:
        argv += ["--functions", ",".join(probe_functions)]
    else:
        argv += ["--struct", struct_name, "--struct-src", struct_src, "--expect-variants", str(expect)]
        if index_names:
            argv += ["--index-names", ",".join(index_names)]
    for f in unit_files:
        argv += ["--pair", "%s=%s" % (f["source"], f["object"])]
    rc, _ = steps.run("extract_%s" % tag, argv)
    if not os.path.exists(man):
        return
    dec = os.path.join(udir, "decode")
    steps.run("decode_%s" % tag, py(tools) + [script("x0_decode.py"), man, "-o", dec, "--xed", tools["xed"],
                                                "--objdump", tools["objdump"], "-j", "2"])
    attrs = []
    for f in unit_files:
        tw = twins.get(f["id"])
        if not tw:
            continue
        ap = os.path.join(udir, "attr", "%s.attr.json" % safe(f["id"]))
        os.makedirs(os.path.dirname(ap), exist_ok=True)
        targv = py(tools) + [script("x0_twin.py"), "--census", f["object"], "--twin", tw, "--source", f["source"],
                             "-o", ap, "--objdump", tools["objdump"]]
        targv += ["--readobj", tools["readobj"]] if f["object"].lower().endswith(".obj") else ["--dwarfdump", tools["dwarfdump"]]
        for d in source_dirs:
            targv += ["--source-dir", d]
        steps.run("attr_%s_%s" % (tag, safe(f["id"])), targv)
        if os.path.exists(ap):
            attrs.append(ap)
    if os.path.exists(os.path.join(dec, "variants.json")):
        largv = py(tools) + [script("x0_loops.py"), dec, "--manifest", man, "-o", os.path.join(udir, "loops.json")] + loops_args
        for ap in attrs:
            largv += ["--attribution", ap]
        steps.run("loops_%s" % tag, largv)


# ------------------------------------------------------------------------------------------- census mode
def configure(steps, cfg, tools, src, bdir):
    if os.path.exists(bdir):
        shutil.rmtree(bdir)
    cm = tools["cmake"]
    if cfg == "A":
        argv = [cm, "-S", src, "-B", bdir, "-G", "Visual Studio 17 2022", "-A", "x64"]
    elif cfg in ("A-ninja", "B-cmake"):
        cc = "cl" if cfg == "A-ninja" else tools["clang_cl"].replace("\\", "/")
        argv = [cm, "-S", src, "-B", bdir, "-G", "Ninja", "-DCMAKE_MAKE_PROGRAM=%s" % tools["ninja"],
                "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON", "-DCMAKE_C_COMPILER=%s" % cc]
    elif cfg in ("C", "D"):
        cc = tools["gcc"] if cfg == "C" else tools["clang"]
        argv = [cm, "-S", src, "-B", bdir, "-G", "Unix Makefiles", "-DCMAKE_BUILD_TYPE=Release",
                "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON", "-DCMAKE_C_COMPILER=%s" % cc]
    else:
        raise SystemExit("no census-mode configure for %s" % cfg)
    steps.run("configure:%s" % os.path.basename(bdir), argv, fatal=True)


def safe(name):
    return re.sub(r"[^\w.#-]+", "_", name)


def build_census(a, cfg, cfgdir, steps, tools, src_root, records):
    """census mode: configure twice from scratch, build twice; build records in cfgdir/builds."""
    frozen = a.frozen_db or (os.path.join(ROOT, *FROZEN_DB[cfg].split("/")) if cfg in FROZEN_DB else None)
    for bi in (1, 2):
        bdir = os.path.join(cfgdir, "cfg%d" % bi)
        configure(steps, cfg, tools, src_root, bdir)
        if cfg == "A":
            blog = os.path.join(cfgdir, "logs", "msbuild_b%d.log" % bi)
            t0 = time.time()
            rc, _ = steps.run("build%d" % bi, [tools["cmake"], "--build", bdir, "--config", "Release", "--target", a.target,
                                               "--", "/m:1", "/nr:false",
                                               "/bl:%s" % os.path.join(cfgdir, "logs", "msbuild_b%d.binlog" % bi),
                                               "/flp:LogFile=%s;Verbosity=detailed" % blog, "/clp:Verbosity=minimal"])
            margv = py(tools) + [script("x0_build.py"), "msbuild", "--log", blog, "--project-dir", bdir, "--files",
                                 ",".join(CENSUS_FILES), "--config", cfg, "--build-index", str(bi), "--outdir",
                                 os.path.join(cfgdir, "builds"), "--design-time",
                                 a.design_time or os.path.join(ROOT, *DESIGN_TIME_A.split("/")),
                                 "--msbuild-rc", str(rc if rc is not None else -1), "--since", str(t0 - 2)]
            if rc != 0:
                # x0final revision: MSBuild stops the target at the first failed CL task [M, runbook/logs/
                # x0final_rev_probes.log], so a census file of a later batch is compiled alone with the same project
                # and CL task (single-file ClCompile); its record then comes from that log
                import x0_build
                blocks = x0_build.msbuild_cl_blocks(open(blog, encoding="utf-8", errors="replace").read())
                done = {os.path.basename(s_).lower() for b_ in blocks for s_ in b_["sources"]}
                proj = os.path.join(bdir, "%s.vcxproj" % a.target)
                sdir = os.path.join(src_root, *HEARTH_SRC_REL.split("/"))
                for f in CENSUS_FILES:
                    if f.lower() in done:
                        continue
                    slog = os.path.join(cfgdir, "logs", "msbuild_b%d_single_%s.log" % (bi, f))
                    steps.run("build%d_single_%s" % (bi, f), [tools.get("msbuild") or "msbuild", proj, "/t:ClCompile",
                                                               "/p:Configuration=Release", "/p:Platform=x64",
                                                               "/p:SelectedFiles=%s" % os.path.join(sdir, f), "/m:1",
                                                               "/nr:false", "/flp:LogFile=%s;Verbosity=detailed" % slog,
                                                               "/clp:Verbosity=minimal"])
                    margv += ["--single-log", "%s=%s" % (f, slog)]
            if bi == 2:
                margv += ["--reference-record", os.path.join(cfgdir, "builds")]
            steps.run("records%d" % bi, margv)
        else:
            steps.note("build%d" % bi, detail="each census file's compile_commands.json entry of cfg%d, run verbatim" % bi)
            for f in CENSUS_FILES:
                steps.run("compile%d_%s" % (bi, f), py(tools) + [
                    script("x0_build.py"), "exec", "--db", os.path.join(bdir, "compile_commands.json"), "--as", f,
                    "--verbatim", "--frozen-db", frozen, "--frozen-as", f, "--config", cfg, "--file", f,
                    "--build-index", str(bi), "--kind", "census",
                    "--record", os.path.join(cfgdir, "builds", "%s.b%d.json" % (f, bi)),
                    "--log", os.path.join(cfgdir, "logs", "compile_b%d_%s.log" % (bi, f))])
        for f in CENSUS_FILES:
            r = jload(os.path.join(cfgdir, "builds", "%s.b%d.json" % (f, bi)))
            if r:
                records[bi][f] = r


def build_replay(a, cfg, cfgdir, steps, tools, files, records, db=None, from_records=None):
    """replay / probe mode: each census file compiled twice with a frozen command line (a db entry, or a build
    record of another configuration with the source swapped)."""
    for bi in (1, 2):
        steps.note("build%d" % bi, detail="replay of frozen per-file command lines")
        for f in files:
            obj = os.path.join(cfgdir, "obj%d" % bi, safe(f["id"]) + (".obj" if HOST.get(cfg.split(".")[-1]) == "windows" else ".o"))
            rec = os.path.join(cfgdir, "builds", "%s.b%d.json" % (f["id"], bi))
            argv = py(tools) + [script("x0_build.py"), "exec"]
            if from_records:
                argv += ["--from-record", from_records, "--src", f["source"]]
            else:
                argv += ["--db", db, "--as", f["as"], "--src", f["source"]]
            argv += ["--obj", obj, "--config", cfg, "--file", f["id"], "--build-index", str(bi),
                     "--kind", "probe" if from_records else "replay", "--record", rec,
                     "--log", os.path.join(cfgdir, "logs", "compile_b%d_%s.log" % (bi, safe(f["id"])))]
            steps.run("compile%d_%s" % (bi, safe(f["id"])), argv)
            r = jload(rec)
            if r:
                records[bi][f["id"]] = r


SHINGLE_SKIP = ("#include", "#pragma", "#endif", "#else")
SHINGLE_K = 2
SHINGLE_DEFINITION = "comments stripped; whitespace collapsed; trivial < 12 non-blank characters or #include/#pragma/#endif/#else; k = 2"


def strip_c_comments(text):
    """C source with every block and line comment removed (pre-freeze review of 2026-10-17: a trailing comment made
    an otherwise equal line differ); string and character literals are kept; newlines inside block comments stay, so
    line numbers do not move."""
    out, i, n, bs = [], 0, len(text), chr(92)
    while i < n:
        c = text[i]
        if c == "/" and text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("".join("\n" if ch == "\n" else " " for ch in text[i:j]))
            i = j
        elif c == "/" and text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif c in "\"'":
            j = i + 1
            while j < n and text[j] != c and text[j] != "\n":
                j += 2 if text[j] == bs else 1
            out.append(text[i:j + 1])
            i = j + 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def nontrivial_lines(text):
    """The normalised non-trivial lines of a C source (x0final revision; the unit of the shingle guard). Pre-freeze
    review of 2026-10-17: comments, including trailing ones, are stripped first, so a line starting with '*' (a
    dereference) is no longer skipped as a comment. Whitespace runs are collapsed to one space and stripped; a line is
    trivial when it has fewer than 12 non-blank characters or starts with #include, #pragma, #endif or #else."""
    out = []
    for line in strip_c_comments(text).splitlines():
        n = re.sub(r"\s+", " ", line.strip())
        if len(re.sub(r"\s", "", n)) < 12 or n.startswith(SHINGLE_SKIP):
            continue
        out.append(n)
    return out


def shingles(text, k=SHINGLE_K, allowed=frozenset()):
    """SHA-256 of every window of k consecutive normalised non-trivial lines (joined by a newline), except windows
    whose lines are all on the allow-list of structural lines (the dispatch-table shape a census mock must share)."""
    nt = nontrivial_lines(text)
    return [hashlib.sha256("\n".join(nt[i:i + k]).encode("utf-8")).hexdigest() for i in range(len(nt) - k + 1)
            if not all(x in allowed for x in nt[i:i + k])]


def guard_paths(a, sset, src_root):
    """Every C source and header the smoke step compiles or can include from its source tree: all .c and .h files of
    the source directories (the census files, the mock's other.c, the set's files and the files next to them) and of
    an engine/include directory (pre-freeze review of 2026-10-17; before: the census files and the .h next to them)."""
    if a.mode == "census":
        dirs = [os.path.join(src_root, *HEARTH_SRC_REL.split("/")), os.path.join(src_root, "engine", "include")]
        files = []
    elif a.mode == "replay" and sset:
        files = [set_path(f["source"], src_root) for f in sset["files"]]
        dirs = [os.path.dirname(p) for p in files] + [set_path(d, src_root) for f in sset["files"] for d in f.get("source_dirs", [])]
    else:
        files = [os.path.join(ROOT, "scripts", "probes", "reduce_probe.c")]
        dirs = [os.path.dirname(files[0])]
    paths = list(files)
    for d in sorted(set(dirs)):
        if os.path.isdir(d):
            paths += [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith((".c", ".h"))]
    return sorted(set(os.path.normpath(p) for p in paths))


def guard_sources(a, run, sset, src_root):
    """A smoke run never compiles Hearth: refuse if any source it would compile (guard_paths) carries the git blob
    hash of one of the pinned Hearth files (class/B_iform.json inputs.hearth_blobs), is not UTF-8, or shares a pair
    of consecutive normalised non-trivial lines with one of them that is not made of allow-listed structural lines
    (class/hearth_shingles.json; added by the x0final revision after the census mock was found to contain verbatim
    Hearth helpers, record §2; pairs instead of runs of three, and comments stripped, since the pre-freeze review of
    2026-10-17 found two-line Hearth runs in smoke_dispatch.c)."""
    if run.get("kind") == "census":
        return
    pinned = set(((jload(os.path.join(ROOT, "class", "B_iform.json"), {}).get("inputs") or {}).get("hearth_blobs") or {}).values())
    sh = jload(os.path.join(ROOT, "class", "hearth_shingles.json"))
    if not sh or not sh.get("shingles") or set((sh.get("hearth_blobs") or {}).values()) != pinned \
            or sh.get("k") != SHINGLE_K or sh.get("definition") != SHINGLE_DEFINITION:
        raise SystemExit("REFUSED: class/hearth_shingles.json is missing, was not made from the pinned Hearth blobs, or "
                         "uses another line definition than this script")
    known = set(sh["shingles"])
    allowed = frozenset(sh.get("allowed_structural_lines") or [])
    for p in guard_paths(a, sset, src_root):
        if not os.path.exists(p):
            continue
        with open(p, "rb") as fh:
            data = fh.read()
        if x0_extract.git_blob_sha1(data) in pinned:
            raise SystemExit("REFUSED: %s is a pinned Hearth file; a smoke run never compiles Hearth" % p)
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            raise SystemExit("REFUSED: %s is not UTF-8; the shingle guard cannot read it" % p)
        hits = [i for i, s in enumerate(shingles(text, allowed=allowed)) if s in known]
        if hits:
            raise SystemExit("REFUSED: %s shares %d pair(s) of consecutive non-trivial lines with a pinned Hearth file "
                             "(first at its non-trivial line %d); a smoke run never compiles Hearth code" % (p, len(hits), hits[0] + 1))


def set_path(p, src_root):
    """A path of a census-file set: '@source/...' is relative to the run's source tree, other relative paths to
    experiments/x0-census."""
    if p.startswith("@source/"):
        return os.path.join(src_root, *p[len("@source/"):].split("/"))
    return p if os.path.isabs(p) else os.path.join(ROOT, *p.split("/"))


def cmd_config(a):
    tools = jload(a.tools)
    run = jload(os.path.join(a.run, "run.json"))
    if run is None:
        raise SystemExit("no run.json in %s (run `init` first)" % a.run)
    cfg = a.config
    base_cfg = cfg.split(".")[-1]                  # P.<CFG> uses <CFG>'s host, ABI and twin flag
    src_root = localpath(run["source"])
    pins = jload(os.path.join(ROOT, "class", "frozen_inputs.json"), {})
    src_check = None
    if run.get("kind") == "census":
        # pre-freeze review of 2026-10-17 (record §8 item 9): every configuration step re-checks that it runs the
        # scripts init verified, from the same checkout, on the pinned Hearth blobs (record §2)
        if a.frozen_db or a.design_time:
            raise SystemExit("REFUSED: --frozen-db and --design-time replace the frozen captures; not in a census run")
        scripts_now, checked = recheck_census_tree(run, pins)
        src_check, ok = source_blob_check(src_root)
        if not ok:
            raise SystemExit("REFUSED: Hearth source blobs differ from record §2: %s" % {k: v for k, v in src_check.items() if not v["ok"]})
    else:
        scripts_now, checked = pinned_script_hashes(pins), {"scripts": "recorded only (smoke run)"}
    cfgdir = os.path.join(a.run, cfg)
    if os.path.exists(cfgdir):
        shutil.rmtree(cfgdir)
    os.makedirs(cfgdir)
    steps = Steps(cfgdir)
    cj = {"config": cfg, "role": ROLE.get(cfg, "secondary"), "host": HOST.get(base_cfg), "abi": ABI.get(base_cfg),
          "mode": a.mode, "driver_argv": sys.argv, "tools": tools, "census_files": [], "effective_flags": {}, "p3a": {},
          "scripts_sha256": scripts_now, "tree_recheck": checked, "source_blobs": src_check}
    try:
        _config(a, cfg, base_cfg, cfgdir, steps, tools, run, src_root, cj)
    finally:
        cj["steps"] = steps.items
        cj["utc_end"] = utc()
        jdump(cj, os.path.join(cfgdir, "config.json"))
    print(json.dumps({"config": cfg, "steps": len(steps.items),
                      "failed_steps": [s["step"] for s in steps.items if "argv" in s and s.get("rc") != 0]}))
    return 0


def _config(a, cfg, base_cfg, cfgdir, steps, tools, run, src_root, cj):
    dummy = os.path.join(cfgdir, "flags", "x0_dummy.c")
    os.makedirs(os.path.dirname(dummy), exist_ok=True)
    with open(dummy, "w") as f:
        f.write("int x0_dummy;\n")
    records = {1: {}, 2: {}}
    sset = jload(a.set) if a.set else None
    guard_sources(a, run, sset, src_root)
    if a.mode == "census":
        if run["kind"] != "census" and not run.get("mock"):
            raise SystemExit("census mode needs a census run (or a --mock smoke run)")
        sdir = os.path.join(src_root, *HEARTH_SRC_REL.split("/"))
        cj["census_files"] = [{"id": f, "source": os.path.join(sdir, f)} for f in CENSUS_FILES]
        cj["generator"] = {"A": "Visual Studio 17 2022 (-A x64)", "A-ninja": "Ninja", "B-cmake": "Ninja",
                           "C": "Unix Makefiles", "D": "Unix Makefiles"}[cfg]
        total = struct_slots([os.path.join(sdir, f) for f in CENSUS_FILES], "hx_kernels", os.path.join(sdir, "hx_quant.h"), None)
        if total != 18:
            raise SystemExit("REFUSED: the census sources list %d dispatched variants; record §4.1 expects 18" % total)
        build_census(a, cfg, cfgdir, steps, tools, src_root, records)
    elif a.mode == "replay":
        files = []
        for f in sset["files"]:
            if f.get("configs") and cfg not in f["configs"]:
                continue
            files.append(dict(f, source=set_path(f["source"], src_root)))
        cj["census_files"] = [{"id": f["id"], "source": f["source"], "as": f["as"]} for f in files]
        cj["generator"] = "replay of the frozen per-file command lines (%s)" % sset["frozen_db"][cfg]
        build_replay(a, cfg, cfgdir, steps, tools, files, records, db=os.path.join(ROOT, *sset["frozen_db"][cfg].split("/")))
    else:                                          # probe: arm P with another configuration's build-1 line
        src = os.path.join(ROOT, "scripts", "probes", "reduce_probe.c")
        files = [{"id": "reduce_probe.c", "source": src, "as": a.from_file, "kind": "probe",
                  "functions": ["x0_probe_reduce_add_ps", "x0_probe_reduce_max_ps", "x0_probe_reduce_add_epi32",
                                "x0_probe_reduce_add_ps_mem", "x0_probe_reduce_max_ps_mem", "x0_probe_reduce_add_epi32_mem"]}]
        cj["census_files"] = [{"id": "reduce_probe.c", "source": src, "as": a.from_file}]
        fr = os.path.join(a.run, a.from_config, "builds", "%s.b1.json" % a.from_file)
        cj["generator"] = "build-1 command line of %s/%s with the source swapped (record §3 arm P)" % (a.from_config, a.from_file)
        build_replay(a, cfg, cfgdir, steps, tools, files, records, from_records=fr)
        sset = {"files": [dict(files[0], canary=None, d2_variants=None, helpers="tree16")]}
    # the debug-info twin of build 1 (record §4.6)
    twins = {}
    for f in cj["census_files"]:
        r1 = records[1].get(f["id"])
        if not r1 or not r1.get("object_exists"):
            continue
        tobj = os.path.join(cfgdir, "twin", safe(f["id"]) + ("_twin.obj" if HOST.get(base_cfg) == "windows" else "_twin.o"))
        trec = os.path.join(cfgdir, "twin", "%s.twin.json" % f["id"])
        steps.run("twin_%s" % safe(f["id"]), py(tools) + [
            script("x0_build.py"), "exec", "--from-record", os.path.join(cfgdir, "builds", "%s.b1.json" % f["id"]),
            "--obj", tobj, "--extra=%s" % TWIN_FLAG[base_cfg], "--config", cfg, "--file", f["id"], "--build-index", "1",
            "--kind", "twin", "--record", trec, "--log", os.path.join(cfgdir, "logs", "twin_%s.log" % safe(f["id"])),
            "--no-listing"])
        t = jload(trec)
        if t and t.get("object_exists"):
            twins[f["id"]] = tobj
    # effective flags and P3(a) on build 1's command line of each census file (record §5 P3(a))
    for f in cj["census_files"]:
        r1 = records[1].get(f["id"])
        if not r1 or not r1.get("argv"):
            cj["p3a"][f["id"]] = {"error": "no build-1 command line"}
            continue
        ef, m = effective_flags(base_cfg, r1["argv"], r1["source"], cfgdir, safe(f["id"]), steps, dummy)
        cj["effective_flags"][f["id"]] = ef
        cj["p3a"][f["id"]] = m
    first = next((r for r in records[1].values() if r.get("argv")), None)
    if first:
        cj["compiler"] = {"path": first["argv"][0], "banner": compiler_banner(first["argv"][0]),
                          "sha256": [{"file": k, "sha256": v} for k, v in sorted((first.get("compiler_sha256") or {}).items())]}
        cj["headers"] = headers_info(base_cfg, first["argv"][0])
    else:
        cj["compiler"], cj["headers"] = {"path": None, "banner": None, "sha256": []}, {}
    # extract, decode, twin attribution, loops, per build
    for bi in (1, 2):
        if a.mode == "census":
            sdir = os.path.join(src_root, *HEARTH_SRC_REL.split("/"))
            ufiles = [{"id": f, "source": os.path.join(sdir, f), "object": records[bi][f]["object"]}
                      for f in CENSUS_FILES if records[bi].get(f, {}).get("object_exists")]
            struct_src = os.path.join(sdir, "hx_quant.h")
            if ufiles:
                expect = struct_slots([u["source"] for u in ufiles], "hx_kernels", struct_src, None)
                run_unit(steps, tools, cfgdir, os.path.join("b%d" % bi, "all"), ufiles, "hx_kernels", struct_src,
                         ["F32", "F16", "BF16", "Q8", "Q4", "I32", "U8"], expect, cfg, [], twins,
                         [sdir, os.path.join(src_root, "engine", "include")])
            continue
        for f in sset["files"]:
            if f.get("configs") and cfg not in f["configs"]:
                continue
            r = records[bi].get(f["id"])
            if not r or not r.get("object_exists"):
                continue
            src = r["source"]
            uf = [{"id": f["id"], "source": src, "object": r["object"]}]
            if sset.get("hearth_defaults"):
                # x0_loops.py's own defaults (Hearth's loop table, d2 slots, helpers); the canary only where it lives
                largs = ["--canary-variant", f.get("canary") or "none"]
            else:
                largs = ["--canary-variant", f.get("canary") or "none",
                         "--loop-table", os.path.join(ROOT, *f["loop_table"].split("/")) if f.get("loop_table")
                         else os.path.join(ROOT, "class", "loop_table.csv"),
                         "--d2-variants", f.get("d2_variants") or "none", "--d2-helper", f.get("d2_helper", "tree16"),
                         "--helpers", f.get("helpers") or "tree16"]
            if f.get("variant_map"):
                largs += ["--variant-map", f["variant_map"]]
            if f.get("probe_pairing") or f.get("functions"):
                largs += ["--probe-pairing"]
            ssrc = set_path(f["struct_src"], src_root) if f.get("struct_src") else src
            sdirs = [os.path.dirname(src)] + [set_path(d, src_root) for d in f.get("source_dirs", [])]
            run_unit(steps, tools, cfgdir, os.path.join("b%d" % bi, safe(f["id"])), uf, f.get("struct"), ssrc,
                     f["index_names"].split(",") if f.get("index_names") else None, f.get("expect_variants"), cfg, largs,
                     {f["id"]: twins[f["id"]]} if f["id"] in twins else {}, sdirs,
                     probe_functions=f.get("functions"))


def cmd_assemble(a):
    tools = jload(a.tools) if a.tools else {}
    run = jload(os.path.join(a.run, "run.json"), {})
    if run.get("kind") == "census":
        # pre-freeze review of 2026-10-17: the commits come from init only, and the assembler and the Gatekeeper run
        # from the tree init verified
        if a.freeze_commit or a.scripts_commit:
            raise SystemExit("REFUSED: in a census run the freeze point and the run commit come from init (run.json) only")
        recheck_census_tree(run, jload(os.path.join(ROOT, "class", "frozen_inputs.json"), {}))
    out = os.path.join(a.run, "census.json")
    argv = py(tools) + [script("x0_census.py"), "--run", a.run, "-o", out]
    if a.xml:
        argv += ["--xml", a.xml]
    if a.freeze_commit:
        argv += ["--freeze-commit", a.freeze_commit]
    if a.scripts_commit:
        argv += ["--scripts-commit", a.scripts_commit]
    if a.qualify_tables:
        argv += ["--qualify-tables"]
    rc = subprocess.run(argv).returncode
    print("x0_census.py rc=%d" % rc)
    rc2 = subprocess.run(py(tools) + [script("judge.py"), out, "-o", os.path.join(a.run, "verdict.json")]).returncode
    print("judge.py rc=%d" % rc2)
    return rc or rc2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init")
    i.add_argument("--run", required=True)
    i.add_argument("--kind", choices=("census", "smoke"), required=True)
    i.add_argument("--source", required=True)
    i.add_argument("--profile", choices=("hearth", "regression"), default="hearth")
    i.add_argument("--mock", action="store_true")
    i.add_argument("--run-id")
    i.add_argument("--record", default=os.path.join(ROOT, "..", "..", "docs", "m0", "prereg", "X0-census.md"))
    c = sub.add_parser("config")
    c.add_argument("--run", required=True)
    c.add_argument("--config", required=True)
    c.add_argument("--tools", required=True)
    c.add_argument("--mode", choices=("census", "replay", "probe"), default="census")
    c.add_argument("--from-config", help="probe mode: the configuration whose build-1 line compiles the reduce probe")
    c.add_argument("--from-file", default="quant_avx512.c", help="probe mode: that configuration's census file")
    c.add_argument("--set", help="replay mode: the census-file set (smoke/regression_set.json)")
    c.add_argument("--target", default="hearth_core")
    c.add_argument("--frozen-db", help="census mode: frozen compile_commands.json (default: the pre-freeze capture)")
    c.add_argument("--design-time", help="A: frozen design-time ClCompile lines (default: the pre-freeze capture)")
    s = sub.add_parser("assemble")
    s.add_argument("--run", required=True)
    s.add_argument("--tools")
    s.add_argument("--xml")
    s.add_argument("--freeze-commit")
    s.add_argument("--scripts-commit")
    s.add_argument("--qualify-tables", action="store_true")
    a = ap.parse_args()
    return {"init": cmd_init, "config": cmd_config, "assemble": cmd_assemble}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
