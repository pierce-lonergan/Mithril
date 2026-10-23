#!/usr/bin/env python3
"""a1_reloop.py RUN CFG X0_LOOPS OUTDIR -- Amendment X0-A1 evidence tool (x0fix track, 2026-10-23; not a census input).

Re-runs, READ-ONLY on RUN, every x0_loops.py step that x0_driver.py recorded in RUN/CFG/config.json ("steps" named
loops_*), with exactly the recorded argv except two substitutions: the script path (argv[2], after "python -I") is
replaced by X0_LOOPS, and the value of -o by OUTDIR/CFG/<step>/loops.json. The interpreter is the recorded one, so a
WSL configuration (C, D, P.C, P.D) must be re-run from WSL and a Windows one from Windows. Nothing under RUN is written:
x0_loops.py only reads the decode directory, the manifest, the attribution files and (for the d1 canary) the objects.

Writes OUTDIR/CFG/reloop.json: per step the argv used, rc, the last stdout lines, sha256 of the new loops.json and of
the run's own loops.json, and whether the two are byte-identical. Standard library only.
"""
import hashlib
import json
import os
import subprocess
import sys


def sha(p):
    try:
        with open(p, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def main():
    run, cfg, script, outdir = sys.argv[1:5]
    cj = json.load(open(os.path.join(run, cfg, "config.json"), encoding="utf-8"))
    out = {"run": run, "config": cfg, "x0_loops": script, "x0_loops_sha256": sha(script), "steps": []}
    for st in cj.get("steps", []):
        if not str(st.get("step", "")).startswith("loops_") or not st.get("argv"):
            continue
        argv = list(st["argv"])
        orig_out = argv[argv.index("-o") + 1]
        dst = os.path.join(outdir, cfg, st["step"], "loops.json")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        argv[2] = script
        argv[argv.index("-o") + 1] = dst
        p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
        with open(os.path.join(os.path.dirname(dst), "stdout.txt"), "w", encoding="utf-8") as fh:
            fh.write(p.stdout)
        a, b = sha(dst), sha(orig_out)
        out["steps"].append({"step": st["step"], "argv": argv, "recorded_rc": st.get("rc"), "rc": p.returncode,
                             "run_loops_json": orig_out, "run_loops_sha256": b, "new_loops_sha256": a,
                             "identical": a is not None and a == b, "stdout_tail": p.stdout.splitlines()[-3:]})
        print("%s %s rc=%s identical=%s" % (cfg, st["step"], p.returncode, a == b), flush=True)
    with open(os.path.join(outdir, cfg, "reloop.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    return 0 if all(s["rc"] == s["recorded_rc"] for s in out["steps"]) else 1


if __name__ == "__main__":
    sys.exit(main())
