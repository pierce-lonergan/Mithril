# X1 smoke run: runner kit and runbook (X1-amendment-1 §2.3 and §6.2)

Status: **built, self-tested, reviewed once and revised; not run.** Track x1smoke, 2026-10-23.
No subject attempt has been run by this track; the smoke run is the lead engineer's to launch.
Development data only: nothing here is collection, and no X1 threshold depends on it (record §6.2
step 6).

Governing record: [X1-amendment-1](../../../docs/m0/prereg/X1-amendment-1.md), FROZEN at `ac751b8`,
SIGNED (interim, chat, 2026-10-23; [SIGNATURES.md](../../../docs/m0/sittings/2026-10-23-chat/SIGNATURES.md))
with model `claude-opus-5-5`, effort `max`, s = 50%, cap 160, K = 6. Owner check A20: "Terms OK; run
the smoke run" (OWNER-ANSWERS batch 3). Evidence tags as in [docs/m0/README.md](../../../docs/m0/README.md).
Reviews of this kit: one (Claude, same family, independent context), 12 findings, all accepted;
the log is in §8.

**Before r0, the lead engineer logs in DELEGATED.md** (this track cannot edit it): the runner
deviations of §2, the item substitution of §1.1, the counting rules of §4.4, and §5's token-basis
finding for COST.md and the X1 record.

## 1. What is here

| Path | What |
|---|---|
| [`../../../.claude/agents/x1-subject.md`](../../../.claude/agents/x1-subject.md) | The subject agent type: arm-neutral harness instructions as its system prompt; `tools: Write, Bash`; `model: opus`. `prepare` copies it into the run root |
| [`smoke_workflow.js`](smoke_workflow.js) | Workflow **template**. `prepare` writes the instance `<run root>/smoke_workflow.js` with the plan inlined; one launch runs one **wave** of 5 attempts, or one replacement wave |
| [`probe_workflow.js`](probe_workflow.js) | Template of the pre-flight probe (§4.2 step 6): one `x1-subject` agent, one full-model-ID test, one turn-cap test |
| [`x1smoke.py`](x1smoke.py) | `prepare`, `probe`, `tokens`, `score`, `gate`, `p2`, `status`, `selftest` (stdlib Python 3.12) |
| [`harness/x1check.py`](harness/x1check.py) | The check wrapper the subject calls: `check [--tests]`, `submit`, `abandon`; 8-call budget counted from the hash-chained log; 45-minute wall budget |
| [`scoring.py`](scoring.py), [`smokelib.py`](smokelib.py) | Acceptance check and hidden oracle; bit-exact binary32 model helpers, the drivers' LCG, driver generation |
| [`tasks/`](tasks/) | 8 **development** items (below), each with brief, per-arm prelude and stub, Python oracle model, reference solutions, correct alternatives and mutants |
| [`cards/`](cards/) | Development cards: Mithril Tier 0 (6,639 bytes, ASCII), Rust helper card, shared domain notes. Tier 1 is generated at `prepare` from `grammar/mithril_v0.lark` and `crates/mithi/std/std.mith` |
| [`selftest/selftest_2026-10-23.json`](selftest/) | The self-test report of §7 for kit `x1smoke/2` (paths anonymised); it replaces the builder's report for `x1smoke/1` |

### 1.1 The development task set (NOT sealed, NOT held out, public, written 2026-10-23)

All eight are modelled on the public smoke set of [DESIGN §5.2](../DESIGN.md#52-the-public-smoke-set)
(itself public on purpose) and on Hearth `b5d3f14` (FORMAT.md, NUMERICS.md, `engine/src/model.c`).
They are in the public repository, written by family A (this track), and the subjects are family A.
They may be used for this smoke run and for harness development only: never for card iteration,
calibration, held-out runs or any gate other than §6.2. **The subject outputs and scores of the
smoke run are never used for card iteration or `mithi` diagnostics tuning either** (the score
file carries this label).

| ID | Family | Unit | Grade | Oracle cases [M] |
|---|---|---|---|---|
| D-Q4-1 | T-Q4 | `q4_row_dot` (S-Q4-0) | exact | 176 |
| D-Q4-2 | T-Q4 | `q4_dequant`: Q4 blocks to f32 | exact | 130 |
| D-ACTQ-1 | T-ACTQ | `act_quantize_q8` (S-ACTQ-0) | exact | 113 |
| D-NORM-1 | T-NORM | `rmsnorm` with the 16-lane sum (S-NORM-0) | exact | 130 |
| D-ROUTE-1 | T-ROUTE | `topk`: ties to the lower index, NaN last | exact | 160 |
| D-ROUTE-2 | T-ROUTE | `group_topk` (S-ROUTE-0; Hearth `route_select`) | exact | 160 |
| D-EVICT-1 | T-EVICT | `pick_victim` as a `policy fn` (S-EVICT-0) | timing_only | 209 |
| D-FMT-1 | T-FMT | `parse_trace` (S-FMT-0) | default | 268 |

**This is a substitution, so it is a deviation from a FROZEN precondition.** Record §6.2's
preconditions name "Public smoke items only (PLAN S70; DESIGN §5.2)", that is, the eight `S-*-0`
items, one per family. This set covers six of the eight families, twice for T-Q4 and T-ROUTE, and
has no T-STORE or T-CTRL item: `mithi` does not execute `SlabBuf` I/O, threads or `Condvar`
(crates/mithi/README.md, "Not implemented"). T-STORE and T-CTRL are plausibly among the costlier
families, so the substitution may push the measured w **down** [inference] (§2). The lead
engineer logs it in DELEGATED.md before r0.

**Contamination of future sealed items (DESIGN §4.5).** D-ROUTE-2 restates Hearth's
`route_select`, and the set is close to the sealed families by design. §4.5's public corpus is
"the Mithril repository at HEAD on the sealing date", and these files are untracked today
[M, `git status`]. The lead engineer commits `experiments/x1-harness/smoke/**` before any sealing,
or the X1 track adds them, and the smoke run's final artifacts, to §4.5's corpus list explicitly.

Oracle = the task's Python model (bit-exact binary32 by round-once-from-binary64, valid for + − × ÷ √
[D: 53 ≥ 2·24 + 2]) on the visible cases, literal edge cases and 100–250 seeded random cases
generated by one LCG implemented three times (Python, Rust driver, Mithril driver); the comparison
happens outside the process that ran the subject's code, and a result record without the run's
nonce line fails. These oracles are **not** held to the sealed-item ≥ 95% mutant-kill rule; they
kill every listed mutant (§7).

### 1.2 How one attempt runs

1. `x1smoke.py prepare` creates the run root, outside the repository and with a **short path**
   (it refuses a root whose longest created path would exceed 240 characters; §7). It writes a
   copy of the wrapper and of the `mithi` binary (hashed), the cards, `RUN.json`, `plan.json`,
   65 attempt directories in a seeded order plus one replacement directory each (`<id>-r1`, for
   re-runs of infrastructure failures, §4.4) and a probe attempt, `.claude/agents/x1-subject.md`
   (a copy, hashed) and `.claude/agents/x1-turncap-probe.md`, the workflow instances
   `smoke_workflow.js` and `probe_workflow.js`, and the skeletons `readings.json` and
   `dispositions.json`. Each attempt directory holds `work/` (stub and a prelude copy for the
   subject to read; the solution file does not exist yet) and `harness/` (the prelude the checker
   uses, the visible-test driver and expected outputs, the call log, snapshots). It also refuses a
   `mithi` binary whose embedded std is not the repository's `std.mith` + `canonical.mith`
   (Tier 1 would describe another std; §7).
2. The controller session runs **with the run root as its working directory** (§4.2). The lead
   engineer launches the instance once per wave of 5 attempts: each attempt is
   `agent(prompt, {agentType: 'x1-subject', model: 'opus', effort: 'max', label: <attempt id>})`,
   5 at a time. The prompt carries the four harness commands, the arm card (Mithril: Tier 0 +
   generated Tier 1, 41,030 bytes; Rust: helper card, 3,975 bytes), the shared domain notes, the
   brief, the prelude, the stub and the visible tests with their expected results. Prompt sizes
   are 45.3–49.4 kB (Mithril) and 8.3–12.8 kB (Rust) [D: the prompt rebuilt for every task with a
   45-character run root and the longest attempt id].
3. The subject writes `solution.mith` or `solution.rs` with Write and runs the wrapper through Bash.
   Each `check` costs one of 8 calls; the 9th returns `budget_exhausted`. The count comes from the
   hash-chained log (one `start` entry per call), not from `state.json`, which is only a cache; a
   broken chain refuses further checks. A wrapper failure before the subject's code ran is refunded.
   The build and the visible cases run in a fresh directory `<run root>/b/<random>`, outside the
   attempt tree, deleted afterwards; the prelude comes from `harness/`, and a changed `work/`
   copy is logged. 45 minutes after the attempt's first harness command, `check` and `submit`
   return `wall_budget_exhausted` and the attempt ends as `budget_wall` (a fail, as every budget
   end is). `submit` freezes the final artifact; `abandon` ends the attempt, its reason reduced to
   letters, digits, spaces and `, . : _ ( ) < > = + -`.
4. After each batch: `tokens` reads the agent transcripts (usage, model, effort, tools sent to the
   API, working directory, instruction files, budgets, the tool audit) and `gate` decides. After
   the run: `score` runs the acceptance check and the oracle on each final artifact.

Time limits: a `check` call's build has a 60 s wall limit and each visible case 10 s; after the first
case that times out the rest are reported as not run, so one call ends well inside the Bash tool's
default 2-minute command timeout (a hanging solution's call took 10.8–11.1 s [M, §7]). A wrapper
killed from outside leaves a lock that the next call breaks after 300 s; its started call counts.
With 5 attempts at a time, at most 5 checker processes run at once on the laptop.

Checker per arm (the same flags in `check`, acceptance and oracle):
- **Mithril**: `mithi check --json --subset agent --prelude prelude.mith solution.mith <driver>`;
  visible cases by `mithi run --entry x1h_one_<k>`, one process per case.
- **Rust**: `rustc 1.99.1 --edition 2021 -C opt-level=0 -C overflow-checks=on -C debug-assertions=on
  -F unsafe_code` on a crate of `prelude.rs`, `solution.rs` and the driver; a regex static gate on
  `solution.rs` (DESIGN §11.4's list, plus renames, globs, nested groups, `macro_rules!`, `alloc`,
  raw identifiers, and raw strings handled by the lexer; a heuristic, not the `syn` pass). Code
  runs only after the gate passes. The toolchain is the mithi track's (`~/.rustup-mithril`, host
  x86_64-pc-windows-gnu, rustc SHA-256 `51a5e64f…` [M]). Nothing was installed by this track.

## 2. Deviations from X1-amendment-1 §2.3 and §6.2, and which way each one pushes w

The runner is Claude Code **workflow agents in the lead engineer's controller session**, not a
headless `claude` process per attempt (there is no `claude` CLI on the laptop [M, 2026-10-16]).
That changes several §2.3 controls. Each deviation is listed so that the lead engineer can record
it before the smoke run (record §7 row "headless controls not verified": "a control that cannot
be shown is a deviation recorded before freeze").

| §2.3 item | This kit | Effect on the measured w |
|---|---|---|
| 1. fresh non-interactive session per attempt | a fresh workflow subagent per attempt (its own context) | none expected [inference] |
| 2. isolated configuration, no CLAUDE.md, memory, skills, hooks, MCP | **partly met.** The controller runs with the run root as its working directory: no project CLAUDE.md, no project memory (memory and transcripts are keyed by project path), and the transcripts land outside the Mithril project directories. Not met: the user-level configuration, skills and plugins still load; no per-attempt configuration directory. Default workflow subagents in the Mithril worktree **do** receive the project's auto-memory `MEMORY.md` as an injected instruction file [M: 14 of 44 transcripts of two of this session's workflows, 2026-10-23]; for `x1-subject` in the run root, the probe and `tokens` report the injected files | small extra prefix: w slightly **high** |
| 3. every built-in tool disabled; harness tools over MCP | built-in **Write** and **Bash** only (frontmatter `tools:`), shown from the tool list each transcript records as sent to the API (`probe`, `tokens`); the gate withholds its decision if any attempt was offered another tool. Bash is not restricted by argument: restriction is by instruction, and every tool use is audited afterwards (strict command pattern; Write content through the static gate; harness call numbers in the replies) | misuse shows in the audit and holds the gate (§4.4) |
| 4. card in the system prompt | one agent type serves both arms, so its system prompt is the arm-neutral common instructions and **the arm card travels in the first user message**, identically in both arms | the card is part of the cached prefix either way; small [inference] |
| 4. Claude Code's own system prompt | an `x1-subject` subagent's prefix (its body, 2 tool schemas, the environment) can be smaller than a headless session's, which carries Claude Code's own system prompt; default workflow subagents start at 53,101–81,550 input tokens [M: 44 transcripts, 2026-10-16 and 10-23] | w may be **low** or high [inference]; `tokens` reports each attempt's first-call input side, so the difference can be bounded once a headless prefix is known |
| 5. per-`check` sandbox (no network, read-only, CPU limits) | none: the wrapper runs `mithi`/`rustc` and the driver with the user's rights on the laptop, wall timeouts only | none on w |
| 6. budgets: 8 checks, 60 turns, 600k non-prefix input, 60k output, 45 min | **enforced: 8 checks and 45 min** (from the first harness command; the time before it is not counted, so the wall budget is lenient). **Measured, not enforced: turns and tokens**: `agent()` has no turn option [M, workflow reference], and a `maxTurns` frontmatter field is tested by the probe's turn-cap agent but not used; `tokens` reports per attempt the usage after turn 60, after 45 min, after 600k non-prefix input and after 60k output | over-long attempts cost more: w **high** |
| 7. a rate-limit or window stop is an infrastructure failure, re-run | an attempt whose `agent()` returned `null`, or whose wrapper failed in a call it did not refund, is an infrastructure failure; it is **re-run once** in a replacement wave of the same batch, before the readings (§4.4) | its usage stays in Δ while N excludes it: w **high** |
| §2.4 P2 within a batch | P2 is checked from a short reading before **every wave** of 5 (§4.3); the gate lists any wave without a P2-allowing reading before it as a caveat | — |
| model pin | `model: 'opus'` as the lead engineer specified; the probe also tests whether the full ID `claude-opus-5-5` is accepted. Every assistant message's `model` and every request's `params.model` must be `claude-opus-5-5`, or the gate withholds its decision | — |
| effort pin | `effort: 'max'` per `agent()` call; every request's `output_config.effort` (and the records' `effort` fields) must be `max`, or the gate withholds its decision | — |
| Claude Code version | read from the transcripts: `2.1.308` in this session's workflows on 2026-10-23, `2.1.295` on 2026-10-16 [M]. A version change inside the run is a gate caveat (record §2.1: w holds for one version) | — |
| §6.2 preconditions: the item set | D-* development items in place of DESIGN §5.2's `S-*-0` set, no T-STORE or T-CTRL (§1.1) | w may be **low** [inference] |

Development-card deviations: the cards are development versions (no frozen Tier 0/1 exists yet).
The Mithril card's size (Tier 0 + Tier 1 ≈ 41 kB) is inside DESIGN §10.2's 7–17k-token target
[inference: about 3.5 bytes per token], so the prompt cost is of the right order.

**The direction matters, both ways.** Toward a wrong **RUNNABLE** (w measured low): the item mix,
and possibly the smaller subagent prefix. Toward a wrong **NOT RUNNABLE** (w measured high): the
partial isolation, the unenforced turn and token budgets, infrastructure failures that are not
replaced, and the controller's own turns (§4.2 step 7). Record §6.2 counts both as wrong
decisions, and a wrong NOT RUNNABLE triggers a second amendment. So the gate's output carries
these as standing caveats, and `tokens` measures what it can: the usage past each unenforced
budget and each attempt's prefix. The report to Pierce states them with any decision.

## 3. Isolation limits (read before any other use of this kit)

These are development items. The kit gives **none** of the held-out isolation that DESIGN §4.2,
§4.6 and §11 and record §2.3 require:
- the subject runs as a family-A agent with the user's file-system rights; with the run root as
  its working directory, no relative path leads to the repository, but an absolute path can still
  reach it (task models, references, mutants and this file) and other attempts' directories;
- prompts, transcripts, workspaces and logs are plain files on the laptop, readable by every
  family-A development session; nothing is encrypted; there is no Gatekeeper store;
- the hidden expectations are computed from public Python models; nothing is sealed or salted;
- the call log is hash-chained (tamper-evident: an edited line breaks the chain and the wrapper
  then refuses further checks, tested in §7), not tamper-proof: code with file access could
  rewrite the whole chain. The static gate keeps file access out of Rust solutions run by
  `check --tests` (a heuristic), the build runs outside the attempt tree, and the transcripts
  carry the harness replies' call numbers independently of the log; the audit of every tool use
  is the control.

An optional tightening, not made by this kit: `<run root>/.claude/settings.json` with
`permissions.deny` rules for Read and Bash on the repository path (DESIGN §4.6's mechanism). Its
path syntax on Windows is not verified here; if the lead engineer adds it, the probe can be
extended with a read of a reference path that must be refused [would be M].

**Before any sealed or held-out item is used**, the runner needs at least: a per-attempt isolated
Claude Code configuration (no CLAUDE.md, memory or project settings; transcripts copied to the
private store and deleted), no shell (the harness tools served over MCP), the per-`check` sandbox
and the two-stage oracle with no hidden data where agent code runs, and visible bundles decrypted
only into the attempt. None of that is in this kit.

## 4. Runbook for the lead engineer

### 4.1 Preconditions (all must hold; record §6.2 "Preconditions" and §2.2)

- [ ] A20 answered "allowed": yes, batch 3 ("Terms OK; run the smoke run").
- [ ] X1-amendment-1 signed with model, effort, s, cap, K: yes, interim, 2026-10-23.
- [ ] The deviations of §2, the item substitution of §1.1 and the counting rules of §4.4 are
      logged in DELEGATED.md.
- [ ] Pierce has agreed a time and will not use Claude from r0 until the last reading
      (OWNER-ANSWERS batch 3, consequences). Told beforehand: stage 1 takes up to about 1 h,
      each 20-attempt batch up to about 3 h (four waves), plus at least 20 min of readings per
      batch [D from G].
- [ ] Every other agent and workflow on the account is paused (the windows are account-wide).
- [ ] P2 allows a start: weekly all-models ≤ (days since reset / 7) × 100 + 15 and 5-hour ≤ 80.
- [ ] **The whole run fits inside one weekly window.** The weekly all-models window resets on
      Fridays at 12:00Z (05:00 PT) [M, two consecutive resets, §5]. In the quiet procedure every
      reading from r0 to the last must fall in r0's window, or the gate answers `RESET_CROSSED`.
      Start soon after a reset; if a batch would straddle the next reset, do not start it.
- [ ] Only public development items (this kit's). No other content.

### 4.2 Pre-flight (before r0; these cost no plan tokens except steps 6 and 7)

1. Build `mithi` from the source of record (at most two jobs, target directory outside the
   repository; crates/mithi/README.md):
   `CARGO_TARGET_DIR=<outside> CARGO_BUILD_JOBS=2 cargo build -p mithi --release`
   with `RUSTUP_HOME`/`CARGO_HOME` pointing at the mithi track's toolchain. Record its SHA-256.
   Build it from the same tree `prepare` reads, or `prepare` refuses (§1.2).
2. `python experiments/x1-harness/smoke/x1smoke.py selftest --mithi <mithi.exe> --out <file>` must
   print `"ok": true` (about 2 min on the laptop [M]).
3. `python experiments/x1-harness/smoke/x1smoke.py prepare --root <run root> --run-id <id> --mithi <mithi.exe>`
   with a new, **short** run root outside the repository, for example
   `%LOCALAPPDATA%\x1s\<id>`, and a short run id. Defaults: seed 20261023, 65 attempts, model
   `opus`, effort `max`. Keep the printed `plan_sha256`. **Do not launch the builder's scratch
   dry-run instance** (`scratchpad/x1smoke/dryrun`): its root is 204 characters, so every check
   would fail on path length [D: longest path 278 > 240], and it predates this revision.
4. Start a **fresh, small controller session with the run root as its working directory** (never
   the repository). It resolves `x1-subject` from `<run root>/.claude/agents/`. That a session in a
   folder resolves agent types from that folder's `.claude/agents/` is standard Claude Code
   behaviour [not verified here]; the probe shows it.
5. Record in `readings.json` the field `weekly_reset_utc` (any reset instant of the weekly
   all-models window, for example `2026-10-30T12:00:00Z`) and `quiet_throughout`.
6. **Mandatory probe, before r0**: from the controller,
   `Workflow({scriptPath: '<run root>/probe_workflow.js', args: {run_id: '<id>'}})`. Save its
   return value as `results/probe.workflow.json`, then
   `python x1smoke.py probe --root <run root> --workflow-dir <the probe run's transcript directory>`.
   It writes `results/probe.json` with `ok` true only if the agent type is `x1-subject`, the tools
   sent to the API are exactly Write and Bash, every model field is `claude-opus-5-5`, every
   effort field is `max`, the working directory is the run root, and the agent reached the
   wrapper once with an audited command. It also records the injected instruction files, the
   first-call input side (the `x1-subject` prefix proxy) [would be M], whether the full model ID
   was accepted, and whether `maxTurns` was honoured. **If `ok` is false, stop**: fix the cause
   (or, for an extra tool or another working directory that cannot be avoided, accept it with
   `--allow-extra-tool` / `--allow-cwd` and log the deviation) and re-probe. If the full ID is
   accepted, the lead engineer may re-prepare with `--model claude-opus-5-5` and re-probe. If
   `maxTurns` is honoured, adding `maxTurns: 60` to the agent file would enforce the turn budget;
   that changes the file, so re-prepare and re-probe, and treat an attempt cut off by the cap as a
   completed (budget) attempt. The gate refuses to decide unless the probe ended before r0.
7. Keep the controller's context small. Every controller turn is itself Claude use on the account:
   each turn re-reads the session's context, so take readings in single short turns, and record the
   `context.tokensUsed` that `get_usage` returns with each reading (`controller_context_tokens`),
   so the overhead can be stated [D] afterwards. The overhead counts as X1's (§6.2 step 1), which
   can only push toward NOT RUNNABLE.

### 4.3 The procedure (record §6.2, steps 1–5)

Readings are `get_usage` → `plan.windows[]`: "Weekly · all models" `percentUsed` (whole points),
"5-hour limit" `percentUsed`, and the reset times. Record each reading in `<run root>/readings.json`,
in time order, as `{"kind": "gate", "after_batch": k, "t_utc": ..., "weekly_all_models_pct": ..,
"five_hour_pct": .., "controller_context_tokens": ..}` (`after_batch` 0 for r0), and each short P2
check before a wave as `{"kind": "p2", "before": "batch k wave w", "t_utc": ..., ...}`. Every field
is mandatory; the gate rejects a reading without a time or with a non-integer value.

| Step | Action |
|---|---|
| Q | Confirm the account is quiet (§4.1). |
| R0 | Read r0 just before the first attempt (`kind: gate, after_batch: 0`). |
| Wave | For each wave w of batch k: take a P2 reading (`kind: p2`), run `python x1smoke.py p2 --root <run root>`, and start the wave only if it says `start_allowed: true`; otherwise wait (pausing never reorders, §2.4 P4; log every pause). Launch `Workflow({scriptPath: '<run root>/smoke_workflow.js', args: {run_id, batch: k, wave: w, account_quiet: true, gate_sha256}})` (`gate_sha256` from batch 2 on). Save the return value as `results/batch_<k>_wave_<w>.workflow.json`. Batch 1 has one wave (0); batches 2–4 have waves 0–3. A batch must not straddle the Friday 12:00Z reset; if it would, wait. |
| Replace | If a wave returned `not_returned` attempts, or `status` shows an unrefunded wrapper failure, run a replacement wave of the same batch before its readings: `args: {run_id, batch: k, replace: [<attempt ids>], account_quiet: true, gate_sha256}`; save it as `results/batch_<k>_replace_<n>.workflow.json`. Each attempt is re-run at most once (§4.4). |
| Interrupted | Relaunch an interrupted wave **only** with `resumeFromRunId` of the same workflow run. Never relaunch a wave fresh. |
| Tokens | After the batch's last wave: `python x1smoke.py tokens --root <run root> --workflow-dir <dir of every wave run so far> [...]` (the transcript directory of a workflow run is `~/.claude/projects/<project key of the run root>/<session>/subagents/workflows/wf_<id>/`). |
| Read | Wait at least 10 min after the batch's last attempt ended (`tokens` gives the times), then read every 10 min until two consecutive readings agree (`kind: gate, after_batch: k`). The account stays quiet throughout. |
| Gate | `python x1smoke.py gate --root <run root>`. It prints the decision and a `gate_sha256`. `CONTINUE`: pass that `gate_sha256` to the next batch's waves. `READING_INCOMPLETE`: keep reading. `AUDIT_HOLD`: record a reviewed disposition for each flagged attempt in `dispositions.json` (before the decision is known; the gate withholds it), then run `gate` again. `PINS_UNVERIFIED`, `INVALID_READINGS`, `INCONSISTENT_RECORDS`, `RESET_CROSSED`: stop and report to Pierce; nothing is decided. |
| End | At `RUNNABLE`, `NOT_RUNNABLE` or `UNDETERMINED` (after batch 4), stop. The account may resume normal use after the last reading. |

Gate verdicts are reported to Pierce before anything is acted on (DELEGATED.md limits), with the
gate's caveats.

**If the account cannot stay quiet between batches** (§6.2 step 5): set `quiet_throughout: false`
and take a settled reading right before each batch (`kind: gate, after_batch: -k`) as well as after
it; the gate then sums the per-batch changes and uses ±k after k batches. Each batch's before and
after readings must then share a weekly window.

### 4.4 Counting rules this kit applies (proposed; the lead engineer adopts or changes them before r0)

The record does not say how infrastructure failures enter N. The kit's rules:
- An **infrastructure failure** is an attempt whose `agent()` returned `null`, or whose wrapper
  failed in a call it did not refund. One definition serves `score` and `gate`.
- It is **re-run once** as a fresh attempt (`<id>-r1`, same task and arm) in a replacement wave of
  the same batch, before that batch's readings (record §2.3 item 7). Its usage stays in Δ; it is
  not in N. If the re-run also fails, the gate reports N below plan as a caveat; there is no
  second re-run.
- N_k is derived by the gate from the saved workflow results, the attempt logs and the
  transcripts, never typed by hand: the attempts that ran in batches 1..k, minus infrastructure
  failures, minus attempts whose log fails its integrity check, minus attempts the lead
  engineer's disposition excludes (below). Mismatches between these records (an attempt in two
  result files, a planned attempt never run, a replacement for an attempt that did not fail, a
  batch launched without a `gate_sha256` from a stored `CONTINUE`) make the decision
  `INCONSISTENT_RECORDS`.
- **Audit dispositions.** An attempt flagged by the tool audit or the integrity check holds the
  gate (`AUDIT_HOLD`) until `dispositions.json` records, for it, `disposition` (`benign` or
  `misuse`), `exclude_from_N` and the `reviewer`. Exclude an attempt when the flagged use could
  have made it cheaper (for example a read of a reference solution); its usage stays in Δ.
- Attempts that end by a budget, `abandon` or without `submit` are completed attempts.
- The gate also reports `N_if_infra_counted_info` for each step (information only).

### 4.5 The decision rule, exactly as record §6.2 states it

> **Decision after every batch k**, with N_k = the attempts so far and Δ_k = r_k − r0:
> - **NOT RUNNABLE** if (Δ_k − 1) / N_k > w*;
> - **RUNNABLE** if (Δ_k + 1) / N_k ≤ w*;
> - otherwise run the next batch of **20** attempts and read again, up to **N = 65** in all (5 + 3 ×
>   20) [G];
> - at N = 65 with neither, **UNDETERMINED**.

With w* = 100 × s × K / A = 100 × 0.5 × 6 / 3,456 = **25/288 ≈ 0.0868** points per attempt
[target, D]. `x1smoke.py gate` evaluates it in exact rational arithmetic. Outcomes and actions are
the record's §6.2 step 4 (RUNNABLE: the interval and the token reports go into COST.md and the X1
record §6.3 as [M] facts; NOT RUNNABLE and UNDETERMINED: reported to Pierce with the interval).

The rule's properties hold only on a quiet account, inside one weekly window, with usage fully
registered and the pins as signed. So, before applying it, the gate checks, in this order, and
emits **no rule outcome** if any fails:
1. `INVALID_READINGS`: a reading lacks `t_utc`, a whole-number weekly or 5-hour value, or (gate
   readings) `after_batch`; readings out of time order; a reading that decreases inside one weekly
   window; no `weekly_reset_utc`; r0 after the first attempt started or before the probe ended; a
   batch with no end time; a reading labelled "after batch k" taken after batch k+1 started; a
   negative change.
2. `INCONSISTENT_RECORDS`: the batch records disagree (§4.4).
3. `RESET_CROSSED`: a weekly reset falls between r0 and the readings used (quiet procedure), or
   inside one batch's before/after readings (step-5 variant).
4. `PINS_UNVERIFIED`: no ok probe; no `tokens.json`; an attempt that returned without a
   transcript; a model other than `claude-opus-5-5`; an effort other than `max`; an agent type
   other than `x1-subject`; a tool other than Write and Bash offered; an `x1-subject` transcript
   with no plan label.
5. `AUDIT_HOLD`: a flagged attempt with no recorded disposition.
6. Only then: `READING_INCOMPLETE` (fewer than two readings at least 10 min after the batch's last
   attempt ended and at least 10 min apart, or the last two disagree), or the rule.

Properties of the rule as implemented [S, `x1smoke.py gate --selftest`: true w from 0 to 1.6 in
steps of 0.001, both rounding rules, five starting offsets]: no wrong decision; RUNNABLE first
possible at N = 25 (it needs N ≥ 1/w* ≈ 11.5, and N after each batch is 5, 25, 45, 65);
UNDETERMINED only for w between 0.062 and 0.107; at most 9.975 points of one weekly window spent.
These match the record's own simulation (no wrong decision, 0.06–0.10, 9.97) [S].

### 4.6 After the run

```text
python x1smoke.py tokens --root <run root> --workflow-dir <transcript dir of each wave's workflow run> [...]
python x1smoke.py score  --root <run root>
python x1smoke.py gate   --root <run root>
```

`tokens` writes, per attempt: the summed usage (input, cache creation, cache read, output), turns,
first and last timestamps, models (messages and requests), efforts (records and requests), tools
offered, working directories, instruction files, Claude Code versions, the first-call input side,
the usage past each unenforced budget and the tool audit; per batch, per task and arm (means) and in
total; and the checks `model_is_pinned`, `effort_is_max`, `agent_type_is_subject`,
`tools_only_write_bash`, `claude_code_version_single`, `cwd_is_run_root`, `no_instruction_files`,
`attempts_with_tool_flags` and `attempts_over_a_budget`. `score` writes per-attempt VP,
acceptance, CABW flags, the log-integrity check and per-arm aggregates (infrastructure failures
and integrity-flagged attempts left out), labelled development data, never used for card iteration
or `mithi` diagnostics tuning. The transcripts stay in the run root's project directory, outside
the Mithril project directories; they are not copied into the repository.

## 5. Token accounting: what a workflow's "subagent tokens" counts [D]

The record's §6.1 converts plan points to tokens with the workflow reports' "subagent tokens"
(10,248,932 for workflow 1, 9,871,258 for the build round; COST rows 4 and 7) and compares the
result with a per-attempt estimate of **cumulative processed tokens** (0.26–0.92 M, DESIGN §12.1's
formula, which counts the prefix on every turn). The transcripts of those two workflows are on the
laptop; workflow 1's were read with `x1smoke.py tokens` itself and the build round's with the same
method (usage per API message, each field's maximum over the message's records):

| Workflow (agents) | Reported "subagent tokens" | Σ over agents of the last API call's input side (input + cache creation + cache read) | Σ cumulative processed, incl. cache reads | Σ cumulative, excl. cache reads |
|---|---|---|---|---|
| workflow 1 (30) | 10,248,932 | 10,248,684 | 450,479,279 | 15,422,933 |
| build round (22) | 9,871,258 | 9,871,055 | 1,006,218,011 | 25,625,282 |

[M: transcript sums, 2026-10-23, `wf_1e340026-e32` and `wf_beac32c4-675`; D: comparison.] The
report's figure equals the sum of each agent's **final context size** to within 0.003%; it is not
cumulative processed tokens, which are 44 and 102 times larger. So §6.1's two inputs are on
different bases, which is the case its own caveat names ("If the workflow figure counts less …
this conversion overstates X1's share, possibly by several times"). On a cumulative basis the 29
points from 10% to 39% carried about 1.46 B processed tokens including cache reads (≈ 50 M per
point) or 41 M excluding them (≈ 1.4 M per point) [D, rough, with §6.1's own caveats]. Which basis
the plan meters is not known [not verified], and cache reads may well be weighted below fresh
input. This does not change the frozen record or the gate, which measures points directly. It
suggests that §6.1's "does not fit" prior is weaker than it reads [inference], and it means that
the §6.2 step 4 token-based fallback (UNDETERMINED) must put both sides on one basis. `tokens`
reports every basis.

A plan reading by this track at about 2026-10-23T16:27Z: 5-hour 34% (resets 19:50Z), weekly all
models 9% (resets 2026-10-30T12:00Z), weekly Fable 0%, extra usage disabled [M, `get_usage`]. The
reset moved from 10-23T12:00Z to 10-30T12:00Z, so the weekly window recurs on Fridays at 12:00Z
(05:00 PT) [M, two consecutive resets], as record §2.4 P2 inferred.

## 6. Findings for the mithi and card tracks (from writing the references) [M]

1. `todo!()` in a `kernel fn` is rejected (E-KERNEL-OBLIGATION, `hole(name)`): the DR-003 hole
   workflow does not reach kernels, so a Mithril stub of a kernel task fails `check` as written.
   In `fn` and `policy fn` the hole is accepted and traps when reached.
2. The NaN-cover rule (E-NAN-RAW-SINK) accepts a float output slice only after an unconditional
   `for i in 0..y.len() { y[i] = canonical }`; conditional writes, nested `g * 64 + i` writes, or an
   if/else that writes in both branches all leave the old (raw) contents possible. Idiom: fill the
   slice first, then write with guards (D-Q4-2 reference).
3. T2's budget: a kernel body with three 64-step constant-trip loops and a guarded read loop lost
   the fact `b < out.len()` even under an explicit `if b < out.len()` guard; splitting the block
   work into a helper kernel over `&x[b * 64..b * 64 + 64]` (which T2 proves from `requires
   x.len() == out.len() * 64`) is accepted (D-ACTQ-1 reference).
4. T2 does not prove `e / gs` free of div0 when `gs = e_n / n_group` with `e_n >= n_group`; a
   guard `if gs > 0` is needed (D-ROUTE-2).
5. `policy fn` parameters must be `#[view]` types or slices of them (E-TO-PARAM on `u32`, `bool`).
6. The canonical prelude's `invariant ActQ8` makes a quantising kernel unprovable (README finding
   1); D-ACTQ-1's prelude declares ActQ8 without it, and its brief states the sum rule.
7. `macro_rules! m { () => {} }` at item level is accepted by `mithi check --subset agent`
   (01 §2.5 lists it under FF-ASYNC as rejected).
8. (Revision, for the lead engineer.) `crates/mithi/std/std.mith` changed in the working tree at
   09:40 PT on 2026-10-23, after the builder's `mithi` build of 08:43: that binary's embedded std
   (`std_sha256` `f97589bf…`) matches neither HEAD (`f1bc0660…`) nor the working tree
   (`340a36bd…`) [M]. A card generated from the repository would then describe a std the checker
   does not have. `prepare` and `selftest` now compare the two and refuse or fail on a mismatch.
   The check fired once more during this revision: `std.mith` and three `src/` files changed again
   at 10:25 PT, and a self-test with the reviser's first rebuild (`7bd4a05f…`, std `340a36bd…`)
   failed only on this check [M]; the binary was rebuilt again and the self-test passed. While the mithi track is still editing, build `mithi`
   immediately before `prepare` and record the source state.

## 7. Verification [M, laptop, 2026-10-23, this track]

`x1smoke.py selftest` with `mithi` rebuilt by the reviser from the current working tree (release,
two jobs, SHA-256 `823f486f…`, embedded std `d2ed4214…` = the tree's `std.mith` + `canonical.mith`;
the `crates/mithi` sources hashed identical before the build and after the self-test), rustc
1.99.1, Python 3.12; about 2 min wall; report in [selftest/](selftest/). Kit `x1smoke/2`, wrapper
`x1check/2`:
- **Tasks**: 71 items, all as expected. Every stub fails (16/16). Every reference and correct
  alternative passes the acceptance check and the oracle in its arm (24/24: 16 references, 8
  alternatives). Every mutant fails the oracle (31/31); 16 of them pass the visible tests and the
  checker, so they are accepted-but-wrong canaries for CABW, and 15 also fail visible tests.
  The references of both arms agree with the Python models on every oracle case, which also checks
  that the three LCG implementations agree.
- **Helper parity**: the Rust helper `f16_to_f32` agrees with IEEE binary16 widening on all 65,536
  inputs; `sum16`/`dot16` agree with the Python model on 200 vectors (lengths 0–199).
- **Cards**: Tier 0 is 6,639 bytes of ASCII (≤ 8,192); its snippets are accepted by
  `mithi check --subset agent`; the Rust card's snippets compile under the arm's flags. The agent
  file's system prompt names no arm, and its tools are exactly `Write, Bash`.
- **Static gate** (16 unit cases): `use std as s`, `use std::{io::{self}, fs}`, `use std::*`,
  `use std::{*}`, a `macro_rules!` path, `std::r#fs`, `use std::{self as t}`, `use ::std as s`,
  `alloc::`, a raw string hiding a `std::fs` call, and a comment inside a path are all caught; no
  reference, alternative, mutant or stub is hit; `x as u32`, `self.0 as u32`, nested `cmp::*` and
  raw strings with quotes are not.
- **Tool audit** (18 unit cases): `abandon "$(cat …)"`, `abandon x; cat …`, a second line after
  `abandon` or `check --tests`, backticks, a redirection, `&&`, a `cd` prefix and a bare `cat` are
  flagged; the four commands and quoted or bare safe reasons are clean; a Write whose content hits
  the static gate is flagged; transcript call numbers 1, 2, 1, 2 are flagged.
- **Path length**: `prepare` refuses a root one character over the limit; the end-to-end run below
  uses a root whose longest created path is exactly 240 characters (a 166-character root).
- **End to end through the wrapper** (16 attempts at that root, files copied in place of a
  subject): 8 counted checks with call numbers 1–8 although `state.json` was reset to 0 calls
  after the third, then `budget_exhausted`; `check` after `submit` returns `attempt_ended`; a stub
  check reports one hole; submit, abandon, no-submit and not-started attempts score as designed;
  mutant submissions are never a VP; every log's hash chain verifies and editing one line breaks
  it; a solution that never returns ends its `check --tests` call after 10.8–11.1 s (five runs),
  with the first case `timeout after 10 s` and the others not run.
- **Wrapper behaviours** (a 2-attempt root): a wrapper failure before the checker ran is refunded
  and the next call is call 1; a garbage `work/prelude` copy does not change what is checked
  (5/5 visible tests pass) and is logged; a `state.json` reset does not reset the count; an edited
  log line makes the next `check` return `log_integrity_failure` and `score` flags the attempt and
  leaves it out of the aggregates; after the wall budget (set to 2 s for the test) `submit`
  returns `wall_budget_exhausted`, the attempt ends `budget_wall` and scores no VP; an abandon
  reason `$(cat x) \`id\`; rm -rf y` is stored as `(cat x) id rm -rf y`.
- **Gate end to end** (synthetic transcripts in the format Claude Code 2.1.308 writes, built from
  the 16 attempts' real logs; results files for one batch-1 wave and three batch-2 waves; probe,
  tokens and gate run as in §4.3): clean run `CONTINUE` then `RUNNABLE`; batch 2 launched with a
  `gate_sha256` that names no stored `CONTINUE` → `INCONSISTENT_RECORDS`; one transcript on another
  model → `PINS_UNVERIFIED`; a `cat` of a reference in a batch-1 transcript → `AUDIT_HOLD`, and with
  a `misuse, exclude_from_N` disposition, `CONTINUE` and then `RUNNABLE` at N = 15; a weekly reset
  between the batches → `RESET_CROSSED`.
- **Gate rule**: §4.5's properties (simulation above), and 19 fixed readings sets with known
  answers: the six earlier cases (RUNNABLE at N = 45, NOT RUNNABLE at N = 5, UNDETERMINED at
  N = 65, readings that disagree, a first reading too early, and the step-5 variant), plus review
  1's cases: a reset between r0 and r1 (r0 = 62, then 0 and 0) and inside batch 2 (61 → 2) →
  `RESET_CROSSED`; missing timestamps, a missing reset time, a missing batch end, a 9.6 and a
  `true` reading, a decrease inside a window, r0 after the first attempt, a reading after the
  next batch started → `INVALID_READINGS`; the last two readings 4 min apart → `READING_INCOMPLETE`;
  pins and audit holds → no rule outcome.
- **Workflow scripts**: both templates were parsed and run in a browser JavaScript engine with
  mocked `agent`, `parallel`, `log`, `phase` and `budget`, on a synthetic 65-attempt plan: the
  templates refuse to run; the guards refuse a missing `account_quiet`, a wrong `run_id`, a missing
  or out-of-range `wave`, batch 2 without a 64-hex `gate_sha256`, `wave` together with `replace`,
  and a replacement of another batch's attempt; batch 1 wave 0 ran a01–a05, batch 2 wave 1 ran
  a11–a15 and batch 4 wave 3 ran a61–a65, at most 5 concurrent; a replacement wave ran `a08-r1`;
  the probe called `x1-subject` with the plan's model, the full ID, and `x1-turncap-probe` at
  effort low, and recorded a refused full ID as not returned. The real workflow runtime was not
  used.
- **Tokens extractor**: run on 44 real transcripts of two of this session's workflows (above), and
  on workflow 1's 30 transcripts by the builder (§5).

Not verified: that `x1-subject` resolves from `<run root>/.claude/agents/` in a session started
there, that the frontmatter's tool list removes every other tool, that `model: 'opus'` resolves to
`claude-opus-5-5`, that `effort: 'max'` is applied, and whether instruction files reach
`x1-subject` (the probe shows all of these before r0); whether `maxTurns` is honoured (the probe
shows it); the real workflow runtime's behaviour with these scripts; how long an attempt takes at
effort max; and anything about plan metering.

## 8. Review log

| Date | Reviewer | Family | Context | Scope | Result |
|---|---|---|---|---|---|
| 2026-10-23 | review 1: one reviewer agent, adversarial, with probes in its own scratch run roots | Claude, same family | independent context | The kit against X1-amendment-1 §2.3, §2.4 and §6.2: gate soundness, pin enforcement, wrapper integrity, audit, isolation, deviations' direction, P2, path limits, N accounting, contamination, prelude source, relaunch | **12 findings (1 blocker, 7 major, 4 minor); all 12 accepted, 0 rejected**, each reproduced or confirmed by the reviser [M] before fixing. (1, blocker) the gate gave RUNNABLE across a weekly reset and with missing timestamps: readings validated, windows and monotonicity checked, `INVALID_READINGS` and `RESET_CROSSED`, 13 new fixtures; three more bypasses of the same kind found and closed (a `true` reading, r0 after the first attempt, a reading after the next batch started). (2, major) the pins decided nothing: a mandatory probe, the tool list/model/effort read from what each request sent, `PINS_UNVERIFIED` and `AUDIT_HOLD` with dispositions. (3, major) solution code could reset the call counter: counts from the log, build outside the attempt tree, a broken chain refuses checks, 7 gate patterns plus a nested-group scan and raw-string lexing (the reviser found four more bypasses: `std::*`, `std::r#fs`, `std::{self as t}`, and a raw string ending in a backslash that hid the code after it from the lexer), integrity checks in `score` and `tokens`. (4, major) `abandon` let shell text through the audit: strict pattern, single quotes, reason sanitised. (5, major) the subject worked in the lead's checkout: the controller runs in the run root, the agent file is copied there. (6, major) the deviations were not one-directional: §2 rewritten two-sided, the item substitution named, the wall budget enforced, over-budget usage measured. (7, major) P2 was not applied within a batch: waves of 5 with a P2 reading before each. (8, major) long run roots broke every check: `prepare` refuses > 240 characters; refunds; the self-test runs at exactly the limit. (9, minor) N was hand-typed: derived from results, logs and transcripts; replacement waves re-run infrastructure failures once. (10, minor) contamination: the label and §1.1, and an owner item to commit or list the items in §4.5's corpus. (11, minor) the prelude was read from `work/`: a harness copy. (12, minor) relaunch without resume: the rule stated, and each batch must carry the `gate_sha256` of a stored `CONTINUE`. The reviser also found that the builder's `mithi` binary embeds a std that matches neither HEAD nor the tree (§6 item 8) and made `prepare` check it. A second-family review is not possible under R1 and R2 |
| — | — | — | — | — | Still open: the lead engineer checks that this revision answers review 1; the DELEGATED.md entries of §4.1 |
