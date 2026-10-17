"""gitlogic_test.py -- exercise x0_driver.py init's freeze-point logic (freeze_checkout: git rev-parse, status
--porcelain [--ignored], show, log --reverse, diff --name-only) against a THROWAWAY git repository that mimics the
Mithril layout (docs/m0/prereg/X0-census.md, experiments/x0-census/{class,scripts,flags}, .gitattributes,
.gitignore). Real git, real x0_driver.py (copied into the throwaway repository); the Hearth source checks are stubbed
(init_one.py STUB) except for the optional last scenario (--hearth PATH, REAL), which reads the Hearth tree as the
census would (blob hashes and HEAD; nothing compiled or decoded).

  python -I gitlogic_test.py --tree X0CENSUS --record RECORD --gitattributes F --gitignore F --work DIR -o OUT.json [--hearth PATH]
"""
import argparse
import json
import os
import shutil
import stat
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INIT_ONE = os.path.join(HERE, "init_one.py")


def rmtree(p):
    def onerr(func, path, _):
        os.chmod(path, stat.S_IWRITE)
        func(path)
    if os.path.exists(p):
        shutil.rmtree(p, onerror=onerr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True)
    ap.add_argument("--record", required=True)
    ap.add_argument("--gitattributes", required=True)
    ap.add_argument("--gitignore", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--hearth")
    ap.add_argument("-o", required=True)
    a = ap.parse_args()
    work = os.path.abspath(a.work)
    repo = os.path.join(work, "repo")
    rmtree(work)
    os.makedirs(repo)
    X = os.path.join(repo, "experiments", "x0-census")
    REC = os.path.join(repo, "docs", "m0", "prereg", "X0-census.md")
    DRV = os.path.join(X, "scripts", "x0_driver.py")
    shutil.copytree(a.tree, X, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    os.makedirs(os.path.dirname(REC))
    shutil.copyfile(a.record, REC)
    shutil.copyfile(a.gitattributes, os.path.join(repo, ".gitattributes"))
    shutil.copyfile(a.gitignore, os.path.join(repo, ".gitignore"))

    def git(*args, check=True):
        p = subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True)
        if check and p.returncode != 0:
            raise SystemExit("harness git %s failed: %s" % (args, p.stderr))
        return p.stdout

    def commit(msg):
        git("add", "-A")
        git("-c", "user.name=x0reg throwaway", "-c", "user.email=x0reg@invalid", "commit", "-q", "-m", msg)
        return git("rev-parse", "HEAD").strip()

    def rd(p):
        with open(p, "rb") as f:
            return f.read()

    def wr(p, b):
        with open(p, "wb") as f:
            f.write(b)

    def append(p, b):
        wr(p, rd(p) + b)

    results = []
    commits = {}

    def init(name, expect, why, record=REC, mode="STUB", source=None, want=None):
        run = os.path.join(work, "runs", name)
        rmtree(run)
        src = source or os.path.join(work, "no-hearth-source")
        p = subprocess.run([sys.executable, "-I", INIT_ONE, DRV, run, record, mode, src], capture_output=True, text=True)
        out = (p.stdout + p.stderr).strip()
        rjp = os.path.join(run, "run.json")
        rj = json.load(open(rjp, encoding="utf-8")) if os.path.exists(rjp) else None
        got = "accept" if (p.returncode == 0 and rj is not None) else "refuse"
        ok = got == expect
        detail = {}
        if got == "accept":
            detail = {k: rj.get(k) for k in ("freeze_commit", "run_commit", "post_freeze_changes", "record_appended_bytes",
                                             "hearth_commit", "source_commit", "source_blobs_ok", "scripts_match_pins")}
            for k, v in (want or {}).items():
                if detail.get(k) != v:
                    ok = False
                    detail.setdefault("mismatch", []).append({k: [detail.get(k), v]})
        else:
            msg = out.splitlines()[-1] if out else ""
            if want and want.get("refusal") and want["refusal"] not in out:
                ok = False
            detail = {"message": msg[:600]}
        results.append({"scenario": name, "why": why, "expect": expect, "got": got, "ok": ok,
                        "head": git("rev-parse", "HEAD").strip(), **detail})
        print("%-4s %-38s expect %-6s got %-6s %s" % ("OK" if ok else "FAIL", name, expect, got,
                                                    (detail.get("message") or "freeze=%s run=%s changes=%s" % (
                                                        (detail.get("freeze_commit") or "")[:7], (detail.get("run_commit") or "")[:7],
                                                        detail.get("post_freeze_changes")))[:200]), flush=True)

    git("init", "-q")
    commits["C1_draft"] = commit("record DRAFT with the x0-census tree")
    init("S0_record_draft", "refuse", "HEAD's record reads DRAFT", want={"refusal": "is not FROZEN"})

    rec = rd(REC)
    assert b"\nStatus: DRAFT" in rec
    wr(REC, rec.replace(b"\nStatus: DRAFT", b"\nStatus: FROZEN", 1))
    commits["C2_frozen"] = c2 = commit("record FROZEN (freeze point)")
    init("S1_freeze_point_clean", "accept", "HEAD is the freeze point, clean",
         want={"freeze_commit": c2, "run_commit": c2, "post_freeze_changes": [], "record_appended_bytes": 0})
    results[-1]["pycache_present_and_ignored"] = os.path.isdir(os.path.join(X, "scripts", "__pycache__"))

    lp = os.path.join(X, "scripts", "x0_loops.py")
    append(lp, b"# uncommitted edit\n")
    init("S2_dirty_tracked_file", "refuse", "uncommitted edit of scripts/x0_loops.py", want={"refusal": "has changes under"})
    git("checkout", "--", "experiments/x0-census/scripts/x0_loops.py")

    up = os.path.join(X, "scripts", "untracked_note.txt")
    wr(up, b"untracked\n")
    init("S3_untracked_file", "refuse", "untracked file under scripts/", want={"refusal": "has changes under"})
    os.remove(up)

    ip = os.path.join(X, "scripts", "evil.pyc")
    wr(ip, b"\x00")
    init("S4_ignored_pyc", "refuse", "ignored scripts/evil.pyc (a sourceless .pyc is importable)",
         want={"refusal": "ignored files under"})
    os.remove(ip)

    append(REC, b"\n## Amendment 1 (throwaway test, 2026-10-18)\n\nClarification only; no tooling change.\n")
    commits["C3_amend1"] = c3 = commit("appended amendment 1, no tooling change")
    init("S5_appended_amendment", "accept", "record = freeze record + appended amendment; no class/scripts/flags change",
         want={"freeze_commit": c2, "run_commit": c3, "post_freeze_changes": []})

    append(lp, b"# throwaway post-freeze tooling fix\n")
    p = subprocess.run([sys.executable, "-I", os.path.join(X, "scripts", "runbook", "pin_inputs.py"), "--write"],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    append(REC, b"\n## Amendment 2 (throwaway test)\n\nTooling fix in scripts/x0_loops.py (logged per record section 10).\n")
    commits["C4_fix_partly_named"] = commit("tooling fix + re-pin; amendment names x0_loops.py only")
    init("S6_change_not_named", "refuse", "re-pinned class/frozen_inputs.json changed but the amendment does not name it",
         want={"refusal": "without an amendment naming them"})

    append(REC, b"Re-pinned: experiments/x0-census/class/frozen_inputs.json.\n")
    commits["C5_fix_named"] = c5 = commit("amendment 2 also names class/frozen_inputs.json")
    init("S7_changes_named", "accept", "every changed class/scripts path is named in the appended amendment",
         want={"freeze_commit": c2, "run_commit": c5, "post_freeze_changes": [
             "experiments/x0-census/class/frozen_inputs.json", "experiments/x0-census/scripts/x0_loops.py"]})

    cp = os.path.join(X, "scripts", "x0_census.py")
    append(cp, b"# edit without re-pin\n")
    append(REC, b"\n## Amendment 3 (throwaway test)\n\nTooling fix in experiments/x0-census/scripts/x0_census.py.\n")
    commit("named script change without re-pin")
    init("S8_named_but_not_repinned", "refuse", "x0_census.py changed and named, frozen_inputs.json not re-pinned",
         want={"refusal": "scripts on disk differ"})
    git("reset", "-q", "--hard", c5)

    rec = rd(REC)
    assert b"ROADMAP anchor:" in rec
    wr(REC, rec.replace(b"ROADMAP anchor:", b"ROADMAP anchor (edited in place):", 1))
    commit("in-place edit of the record body")
    init("S9_in_place_edit", "refuse", "record body edited in place after the freeze point",
         want={"refusal": "other than by an appended amendment"})
    git("reset", "-q", "--hard", c5)

    rec = rd(REC)
    wr(REC, rec.replace(b"ROADMAP anchor:", b"ROADMAP anchor (edited):", 1) + b"\n## Amendment 3 (throwaway)\n\nText.\n")
    commit("in-place edit plus appended amendment")
    init("S10_in_place_edit_plus_append", "refuse", "in-place edit hidden behind an appended amendment",
         want={"refusal": "other than by an appended amendment"})
    git("reset", "-q", "--hard", c5)

    rec = rd(REC)
    wr(REC, rec.replace(b"\nStatus: FROZEN", b"\nStatus: DRAFT", 1).replace(b"ROADMAP anchor:", b"ROADMAP anchor (rewritten):", 1))
    commit("record back to DRAFT with a rewritten body")
    rec = rd(REC)
    wr(REC, rec.replace(b"\nStatus: DRAFT", b"\nStatus: FROZEN", 1))
    commit("record FROZEN again (second freeze attempt)")
    init("S11_unfreeze_edit_refreeze", "refuse", "DRAFT, body rewritten, FROZEN again: the freeze point stays the first FROZEN commit",
         want={"refusal": "freeze point %s" % c2})
    git("reset", "-q", "--hard", c5)

    copy = os.path.join(work, "record_copy.md")
    shutil.copyfile(REC, copy)
    init("S12_record_elsewhere", "refuse", "--record is a byte-identical copy outside the checkout", record=copy,
         want={"refusal": "is not the record of the checkout"})

    fp = os.path.join(X, "flags", "prefreeze", "README.md")
    append(fp, b"\nthrowaway edit\n")
    commit("unnamed flags/ change")
    init("S13_flags_change_not_named", "refuse", "flags/prefreeze/README.md changed, no amendment names it",
         want={"refusal": "without an amendment naming them"})
    git("reset", "-q", "--hard", c5)

    fz = os.path.join(X, "FREEZE.md")
    append(fz, b"\nthrowaway note\n")
    commits["C6_freeze_md"] = c6 = commit("FREEZE.md edited (outside class/scripts/flags)")
    init("S14_change_outside_frozen_dirs", "accept", "FREEZE.md is outside class/, scripts/, flags/ (by design not refused)",
         want={"freeze_commit": c2, "run_commit": c6, "post_freeze_changes": [
             "experiments/x0-census/class/frozen_inputs.json", "experiments/x0-census/scripts/x0_loops.py"]})
    git("reset", "-q", "--hard", c5)

    if a.hearth:
        init("S15_real_hearth_tree", "accept", "unstubbed: Hearth tree %s read by source_blob_check/source_commit" % a.hearth,
             mode="REAL", source=a.hearth,
             want={"freeze_commit": c2, "run_commit": c5, "hearth_commit": "b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220",
                   "source_blobs_ok": True})

    gv = subprocess.run(["git", "--version"], capture_output=True, text=True).stdout.strip()
    rep = {"git": gv, "python": sys.version.split()[0], "repo": repo, "commits": commits, "results": results,
           "all_ok": all(r["ok"] for r in results)}
    with open(a.o, "w", encoding="utf-8", newline="\n") as f:
        json.dump(rep, f, indent=1)
    print("ALL_OK" if rep["all_ok"] else "SOME_FAILED", gv, "python", rep["python"])
    return 0 if rep["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
