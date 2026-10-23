"""X2 gate computation (docs/m0/prereg/X2-checker.md §8). Deterministic; the Gatekeeper script of ROADMAP §1 rule 3.

Agents run it; they never judge its output. It reads one JSON file of gate inputs, computed from the raw results by
the other X2 scripts (record §7), and writes verdict.json. It decides nothing the record does not fix:

  kill        at the evaluation point (end of week 6, or of the amber week): P6 > 0, or P2a > 40, or any false accept
              in a verdict run that is not traceable to a fixable table bug (record §4 items 6-7)
  amber       end of week 6 only: no kill, and 31 <= P2a <= 40 (one extension of 7 days; ROADMAP §3.3)
  pass        no kill, P1 = 8/8, P2a <= 30 with every counted row and loop rule proved, P3 = 100%, P5 = 0,
              every false accept table-traceable and fixed, P6 = 0, and the loop-rule proof reviewed by a
              different model family (ROADMAP §3.3 "a Prover from a different family")
  pass_local_family   as pass, but the loop-rule review is by the local Qwen3 family; usable only if Pierce signs
              QWEN3_LOCAL_PROVISIONAL (DELEGATED P3, D0_BRIEF Q17); otherwise reported as pass_review_pending
  pass_review_pending as pass, but no different-family review exists (Q17 UNMET); NOT a pass (record §8)
  gate_missed no kill and none of the above (DELEGATED P28; record §8): the failing variants stay `tested`, no
              extension; the M0-verdict mapping reports a NARROW row (DELEGATED P8). This includes the amber week
              ending again with 31 <= P2a <= 40 (ROADMAP gives no second amber; record §8)

Input (gate_inputs.json):
  {"evaluation": "week6" | "amber_week", "p1_accepted": int, "p1_total": 8,
   "p2a_rules": int, "p2_all_proved": bool, "p3_killed": int, "p3_denominator": int,
   "p4_false_accepts": [{"id": str, "traceable_to_table_bug": bool, "fixed": bool}],
   "p5_mismatch_cells": int, "p6_assumed_axioms": int,
   "loop_rule_review_family": "different" | "local_qwen3" | "same" | "none",
   "q17_answer": "QWEN3_LOCAL_PROVISIONAL" | "QWEN3_LOCAL_FULL" | "UNMET",
   "proved_loop_shapes": [str, ...]}

verdict.json carries the gate inputs P1-P6 as read (field "inputs"), the outcome, its reasons, proved_loop_shapes and
the hashes of this script and of the input file, so a separate context can match its own P1-P6 against it (record §7).
Inputs outside their range (0 <= p1_accepted <= 8, 0 <= p3_killed <= p3_denominator, negative counts) are refused
with ValueError: a summariser bug must stop the gate, not shape its row (review 2026-10-23).

  python -I -B x2_gate.py gate_inputs.json verdict.json
  python -I -B x2_gate.py --selftest
"""
import hashlib
import json
import os
import sys

FAMILY_OK = ("different",)
# The P1-P6 fields copied into verdict.json["inputs"] (record §7: the separate-context re-derivation matches them).
INPUT_FIELDS = ("evaluation", "p1_accepted", "p1_total", "p2a_rules", "p2_all_proved", "p3_killed", "p3_denominator",
                "p4_false_accepts", "p5_mismatch_cells", "p6_assumed_axioms", "loop_rule_review_family", "q17_answer")


def _check_ranges(g):
    for k in ("p1_accepted", "p2a_rules", "p3_killed", "p3_denominator", "p5_mismatch_cells", "p6_assumed_axioms"):
        if not isinstance(g[k], int) or isinstance(g[k], bool) or g[k] < 0:
            raise ValueError("%s must be a non-negative integer, got %r" % (k, g[k]))
    if g["p1_accepted"] > g["p1_total"]:
        raise ValueError("p1_accepted %d > p1_total %d" % (g["p1_accepted"], g["p1_total"]))
    if g["p3_killed"] > g["p3_denominator"]:
        raise ValueError("p3_killed %d > p3_denominator %d" % (g["p3_killed"], g["p3_denominator"]))
    if not isinstance(g["p2_all_proved"], bool):
        raise ValueError("p2_all_proved must be a boolean")


def gate(g):
    reasons = []
    ev = g["evaluation"]
    if ev not in ("week6", "amber_week"):
        raise ValueError("evaluation must be week6 or amber_week")
    if g["p1_total"] != 8:
        raise ValueError("the gating set is 8 variants (record §4 item 1)")
    _check_ranges(g)
    untraceable = [f["id"] for f in g["p4_false_accepts"] if not f["traceable_to_table_bug"]]
    kill = []
    if g["p6_assumed_axioms"] > 0:
        kill.append("P6: %d per-kernel assumed axiom(s)" % g["p6_assumed_axioms"])
    if g["p2a_rules"] > 40:
        kill.append("P2a: %d rules > 40" % g["p2a_rules"])
    if untraceable:
        kill.append("P4: false accept(s) not traceable to a fixable table bug: %s" % ", ".join(untraceable))
    out = {"record": "X2-checker", "evaluation": ev, "proved_loop_shapes": sorted(g.get("proved_loop_shapes", [])),
           "inputs": {k: g.get(k) for k in INPUT_FIELDS}}
    if kill:
        out.update(outcome="kill", reasons=kill)
        return out
    if ev == "week6" and 31 <= g["p2a_rules"] <= 40:
        out.update(outcome="amber", reasons=["P2a: %d rules in [31, 40]: one 7-day extension" % g["p2a_rules"]])
        return out
    miss = []
    if g["p1_accepted"] != 8:
        miss.append("P1: %d of 8 gating variants accepted" % g["p1_accepted"])
    if g["p2a_rules"] > 30:
        miss.append("P2a: %d rules > 30 at the end of the amber week (no second amber in ROADMAP §3.3)" % g["p2a_rules"])
    if not g["p2_all_proved"]:
        miss.append("P2a: a counted row or loop rule is not proved")
    if g["p3_denominator"] <= 0 or g["p3_killed"] != g["p3_denominator"]:
        miss.append("P3: %d of %d FP-changing mutants rejected" % (g["p3_killed"], g["p3_denominator"]))
    if g["p5_mismatch_cells"] != 0:
        miss.append("P5: %d table/silicon mismatch cells in the final rerun" % g["p5_mismatch_cells"])
    unfixed = [f["id"] for f in g["p4_false_accepts"] if f["traceable_to_table_bug"] and not f["fixed"]]
    if unfixed:
        miss.append("P4: table-traceable false accept(s) not fixed: %s" % ", ".join(unfixed))
    if miss:
        out.update(outcome="gate_missed", reasons=miss)
        return out
    fam = g["loop_rule_review_family"]
    if fam in FAMILY_OK:
        out.update(outcome="pass", reasons=[])
    elif fam == "local_qwen3" and g.get("q17_answer") in ("QWEN3_LOCAL_PROVISIONAL", "QWEN3_LOCAL_FULL"):
        out.update(outcome="pass_local_family" if g["q17_answer"] == "QWEN3_LOCAL_PROVISIONAL" else "pass",
                   reasons=["loop-rule proof reviewed by the local Qwen3 family under Q17 = %s" % g["q17_answer"]])
    else:
        out.update(outcome="pass_review_pending",
                   reasons=["the loop-rule proof has no different-family review (review family: %s; Q17: %s)"
                            % (fam, g.get("q17_answer"))])
    return out


def selftest():
    base = {"evaluation": "week6", "p1_accepted": 8, "p1_total": 8, "p2a_rules": 22, "p2_all_proved": True,
            "p3_killed": 210, "p3_denominator": 210, "p4_false_accepts": [], "p5_mismatch_cells": 0,
            "p6_assumed_axioms": 0, "loop_rule_review_family": "different", "q17_answer": "UNMET",
            "proved_loop_shapes": ["lockstep"]}

    def run(**kw):
        g = dict(base, **kw)
        try:
            return gate(g)["outcome"]
        except ValueError:
            return "ValueError"
    cases = [
        ({}, "pass"),
        ({"p6_assumed_axioms": 1}, "kill"),
        ({"p2a_rules": 41}, "kill"),
        ({"p4_false_accepts": [{"id": "fa1", "traceable_to_table_bug": False, "fixed": True}]}, "kill"),
        ({"p4_false_accepts": [{"id": "fa1", "traceable_to_table_bug": True, "fixed": True}]}, "pass"),
        ({"p4_false_accepts": [{"id": "fa1", "traceable_to_table_bug": True, "fixed": False}]}, "gate_missed"),
        ({"p2a_rules": 31}, "amber"),
        ({"p2a_rules": 40, "p1_accepted": 6}, "amber"),
        ({"p2a_rules": 35, "evaluation": "amber_week"}, "gate_missed"),
        ({"p2a_rules": 30, "evaluation": "amber_week"}, "pass"),
        ({"p1_accepted": 7}, "gate_missed"),
        ({"p3_killed": 209}, "gate_missed"),
        ({"p3_denominator": 0, "p3_killed": 0}, "gate_missed"),
        ({"p5_mismatch_cells": 1}, "gate_missed"),
        ({"p2_all_proved": False}, "gate_missed"),
        ({"loop_rule_review_family": "same"}, "pass_review_pending"),
        ({"loop_rule_review_family": "local_qwen3"}, "pass_review_pending"),
        ({"loop_rule_review_family": "local_qwen3", "q17_answer": "QWEN3_LOCAL_PROVISIONAL"}, "pass_local_family"),
        ({"p6_assumed_axioms": 2, "p2a_rules": 35}, "kill"),
        # range checks (review 2026-10-23): impossible inputs stop the gate
        ({"p3_killed": 211}, "ValueError"),
        ({"p1_accepted": 9}, "ValueError"),
        ({"p1_accepted": -1}, "ValueError"),
        ({"p2_all_proved": 1}, "ValueError"),
    ]
    fails = [(kw, want, run(**kw)) for kw, want in cases if run(**kw) != want]
    # verdict.json carries P1-P6 as read (record §7)
    got = gate(dict(base, p3_killed=209))["inputs"]
    want = {k: dict(base, p3_killed=209).get(k) for k in INPUT_FIELDS}
    if got != want:
        fails.append(("inputs field", want, got))
    return fails, len(cases) + 1


def main(argv):
    if argv[:1] == ["--selftest"]:
        fails, n = selftest()
        for f in fails:
            print("FAIL", f)
        print("x2_gate selftest: %s (%d cases, %d failures)" % ("PASS" if not fails else "FAIL", n, len(fails)))
        return 1 if fails else 0
    src, dst = argv[:2]
    with open(src, encoding="utf-8") as fh:
        g = json.load(fh)
    out = gate(g)
    with open(os.path.abspath(__file__), "rb") as fh:
        out["script_sha256_lf"] = hashlib.sha256(fh.read().replace(b"\r\n", b"\n")).hexdigest()
    with open(src, "rb") as fh:
        out["inputs_sha256"] = hashlib.sha256(fh.read()).hexdigest()
    with open(dst, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print(json.dumps({"outcome": out["outcome"], "reasons": out["reasons"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
