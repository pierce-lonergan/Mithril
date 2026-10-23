# X1 harness design: cold-agent writability with all arms

Status: **DRAFT** (track x1, 2026-10-16; revised the same day after two independent same-family
reviews, logged in the record's §12). Nothing here is frozen, and no data may be collected under
it. The pre-registration that will govern collection is
[docs/m0/prereg/X1-writability.md](../../docs/m0/prereg/X1-writability.md).

*Status note (2026-10-23, track x1smoke).* The runner kit for X1-amendment-1 §6.2's smoke run is in
[smoke/](smoke/) ([SMOKE.md](smoke/SMOKE.md)): a `x1-subject` agent type, a check wrapper (8 calls,
45 min), 8 public development items, a scorer, a pre-flight probe, a wave-by-wave workflow and a gate
that withholds its decision on invalid readings, a weekly reset, unverified pins or audit flags. It
is built, self-tested, reviewed once (12 findings, all accepted) and revised; no subject attempt has
run. Development tooling only: none of the held-out isolation of §4.2, §4.6 and §11 (SMOKE.md §3);
its deviations from the amendment are in SMOKE.md §2. Nothing in this design changed.

*Status note (2026-10-23, track x1iso).* The full X1-amendment-1 §2.3 attempt-isolation controls that
sealed items require (SMOKE.md §3) are built and self-tested on the laptop in
[isolation/](isolation/) ([isolation/README.md](isolation/README.md)): a per-attempt isolated Claude
configuration (no CLAUDE.md/memory/skills/hooks; only the x1 MCP server; `CLAUDE_CONFIG_DIR` per
attempt), the harness tools served over a local stdio MCP server with **no shell** (`list_files`,
`read_file`, `write_file`, `str_replace`, `check`, `run_tests`, `submit`, `abandon`), a per-`check`
sandbox (an AppContainer: no network, read-only inputs, nothing hidden reachable, Job Object
CPU/memory/wall budgets), and the §11.3 two-stage oracle split (Stage A build; Stage B runs agent
output under LPAC with no child process or network). Each control has a negative test that fails as
required. Reviewed once (Claude, same family, independent context; 10 findings, all accepted) and
revised: allowlisted sandbox environment, one CPU pool and wall deadline per `check` call, a fresh
sandbox per visible case, the AppContainer profile's storage under the disk cap, specific-denial
assertions, refusal of attempt directories under CLAUDE.md/AGENTS.md/.claude/.git, opaque attempt
names, and the CLI's documented `--agent`/`--agents`/`--tools ""` flags: 58/58 PASS [M, laptop,
2026-10-23, isolation/results/negtest_2026-10-23_r2.json; r1's 29/29 is superseded]. This realises
§11 on Windows with documented Win32 interfaces (AppContainer/LPAC + Job Object) rather than the
podman image §11.2 sketches; §11.1's Linux host remains an option for the real run. Family-agnostic,
no sealed content (DELEGATED P2 interim restriction). What cannot be verified until a real run — no
`claude` CLI on the laptop, so the agent-type tool restriction and turn/token enforcement are
documented not executed — is listed in isolation/README.md. Nothing in this design changed.

ROADMAP anchor: [§3.2](../../docs/ROADMAP.md#32-x1-cold-agent-writability-with-all-arms-weeks-05)
(authoritative for every gate, amber and kill); DR-002, DR-003, DR-005, DR-013, DR-017;
[05-agent-protocol](../../docs/architecture/05-agent-protocol.md) §2, §3, §6, §13, §16;
[01-language](../../docs/architecture/01-language.md) §2.5, §3.3, §4; [03-trust](../../docs/architecture/03-trust.md)
§10 rows 30–34.

**What this document is.** The end-to-end design of the X1 harness: how tasks are written, sealed,
run, checked and scored, what each arm gets, what `mithi` and the M0 tooling kit must do, and how
cost is metered. It is a buildable specification. It does not decide anything that belongs to the
Owner: every D0 item is marked *provisional, pending D0-x*, and each such choice is reversible.

**Evidence tags.** Every number carries one tag, as in [docs/m0/README.md](../../docs/m0/README.md):
[M] measured, [D] derived (formula stated), [S] simulated (by
[power/x1_power_sim.py](power/x1_power_sim.py) unless stated), [G] judgment, [inference], [target]
(a pre-registered threshold; a choice, not a fact). Dossier numbers keep their labels. Nothing in
this document was measured on any model: no agent has been run.

**Contents**
1. [Architecture end to end](#1-architecture-end-to-end)
2. [Roles and model families](#2-roles-and-model-families)
3. [Task format](#3-task-format)
4. [Sealing and storage](#4-sealing-and-storage)
5. [The eight task families and one public example each](#5-the-eight-task-families-and-one-public-example-each)
6. [Oracles and the mutant-kill requirement](#6-oracles-and-the-mutant-kill-requirement)
7. [The six arms](#7-the-six-arms)
8. [The M0 tooling kit (buildable spec)](#8-the-m0-tooling-kit-buildable-spec)
9. [`mithi` and the checker precondition](#9-mithi-and-the-checker-precondition)
10. [Lark grammar v0, Tier 0 and Tier 1 cards](#10-lark-grammar-v0-tier-0-and-tier-1-cards)
11. [Execution sandbox](#11-execution-sandbox)
12. [Agent runner, logging and cost metering](#12-agent-runner-logging-and-cost-metering)
13. [Scoring and the `mithi` re-scoring rule](#13-scoring-and-the-mithi-re-scoring-rule)
14. [Power and sample size (summary of the simulation)](#14-power-and-sample-size-summary-of-the-simulation)
15. [The local Hearth-hosted pilot](#15-the-local-hearth-hosted-pilot)
16. [Build plan, schedule, cost and owner hours](#16-build-plan-schedule-cost-and-owner-hours)
17. [Rejected design options (tombstones)](#17-rejected-design-options-tombstones)
18. [Open issues and what is unverified](#18-open-issues-and-what-is-unverified)
19. [Review response (2026-10-16)](#19-review-response-2026-10-16)

---

## 1. Architecture end to end

```text
                 PUBLIC (this repo)                              PRIVATE (Gatekeeper store, never in git)
 ┌──────────────────────────────────────────────┐     ┌────────────────────────────────────────────────┐
 │ grammar/mithril-x1.lark   cards/ (tier0,     │     │ per item, two separately encrypted bundles:    │
 │ mithi/ (Rust crate)        tier1, helper     │     │   visible.age  brief, stubs, visible tests     │
 │ harness/ (runner, tools,   cards, preamble)  │     │                (Runner key)                    │
 │  drivers, static gate,    kit/ (hole shim,   │     │   hidden.age   scoring and audit vectors,      │
 │  sandbox images, scorer)   ff-lint)          │     │                expected outputs, refs ×5,      │
 │ analysis/ (Gatekeeper     public smoke set   │     │                mutants, kill reports, canary   │
 │  scripts, frozen)         COMMITMENTS.json   │     │                (Gatekeeper key of its split)   │
 │ power/                                       │     │ planted corpus (dev + confirmation halves),    │
 └───────────────┬──────────────────────────────┘     │ P-1 reproductions, transcripts, snapshots,     │
                 │                                    │ oracle logs: all private until the verdict     │
                 ▼                                    └───────────────┬────────────────────────────────┘
   (1) AUTHOR (family B, by deterministic scripts; §4.6) ──► (2) VALIDATE        │ hidden bundles are
       briefs, stubs, refs ×5 langs, vectors, audit vectors,     refs agree;     │ decrypted only for
       visible tests, mutants; independent family-B review       mutant kill;    │ Gatekeeper jobs, never
                                                                 contamination   │ where agent code runs
                 ▼                                                               │ next to them (§11.3)
   (3) SEAL: per-item hash, salted commitment, suite root → COMMITMENTS.json in its OWN commit
                 ▼
   (4) CHECKER PRECONDITION (P-1, P-2 dev → P-2 confirmation once, P-2t, P-3) → mithi hash recorded
                 ▼
   (5) CARD ITERATION (≤ 3 epochs, 20 iteration items, Mithril arms only; blind atom check;
       semantic guard) → cards, helper cards, shared domain preamble FROZEN (hashes)
                 ▼
   (6) RECORD FROZEN (+ SIGNED or Owner-instructed), n_final open → Owner's post-freeze sample review
                 ▼
   (7) CALIBRATION RUN (24 dedicated calibration items, Rust + Mithril, both families)
       → calibrate.py (outputs only bounds, Rust base rates, end-reason shares) → n_final amendment
                 ▼
   (8) HELD-OUT RUN, once: agent runner ⇄ model API; tools ⇄ per-call sandbox (no network)
       final artifacts rehashed and stored; NO hidden key on any host while agents run
                 ▼
   (9) SCORE after collection: two-stage oracle (build/run with no hidden data; compare outside)
       → per-artifact verdicts → pre-declared defect audit (blind) → unblind → ANALYSE
                 ▼
  (10) INDEPENDENT REVIEW ──► Owner signature (D0-12)
```

Design rules carried from the architecture:
- **The checker judges; agents never judge** (ROADMAP §1 rule 3). The scorer and analysis are code.
- **Observed text is data** (05 §1 rule 6). Briefs, diagnostics and transcripts are never
  instructions to the harness; the harness never reads an agent's self-report (03 row 31).
- **The hidden oracle never influences a trajectory.** Agents see only their own checker and the
  visible tests. This is what makes oracle fixes re-scorable without re-running (§13.4), and it is
  why held-out scoring can wait until collection has ended, so that no hidden key is present on any
  host while agent sessions run (§4.2).
- **Agent code never runs next to hidden data.** Every container that compiles or executes agent code
  holds only the visible task, the public drivers and the input vectors; expected outputs are compared
  outside it (§11.3).

---

## 2. Roles and model families

All family assignments are **provisional, pending D0-10 and D0-11**. The Owner names the families,
model versions and settings.

| Role | Who (provisional) | Constraint | Source |
|---|---|---|---|
| Owner | Pierce | signs the record (D0-12); reviews iteration items and card edits before the card freeze; reviews a seeded sample of 24 held-out items (3 per family [G]) only **after** the card hash is frozen; co-confirms defect claims; reviews the verdict; the only person who debugs infrastructure failures that need content (§4.6) | ROADMAP §1 rules 1, 3; review finding (Owner as a channel), record Owner question 17 |
| Gatekeeper | deterministic scripts + Owner key | runs scorer and analysis; holds the sealed store and the per-split hidden keys | ROADMAP §1 rule 3 |
| Card editors | Claude sessions (family A) + Owner | see iteration items only, never held-out or calibration items; see only a *count* of atoms rejected by the isolation check (§10.2) | 05 §13 |
| Task authors (held-out candidates, iteration and calibration items, refs in all languages, vectors, audit vectors, mutants) | family B, through deterministic authoring scripts (§4.6) | **different family from the card editors**; iteration, calibration and held-out templates disjoint | 05 §13 Goodhart guards; ROADMAP §5 (M1 batch rule applied early) |
| Item reviewers before sealing | independent family-B sessions (separate from the authoring session), or family C | logged per item in `authoring.reviewed_by`; no family-A session ever reviews or assists with held-out content | review finding (Owner as a channel) |
| Semantic-guard reviewer | family B or C, never A | reads the card against the held-out template list before the card freeze (§10.2) | review finding (template tuning) |
| `mithi` builder | Claude sessions (family A) | never sees held-out, calibration or hidden material; sees planted-corpus dev items only after they pass the contamination check (§9.5) | — |
| Planted-corpus author (dev half and confirmation half, ≥ 100 Dc/type-error items each) | family B, or a third family C if the Owner has one | **a family other than `mithi`'s author** | ROADMAP §3.2 |
| Kit builder | Claude sessions (family A) | does **not** write the kit's acceptance corpus | review finding (kit fairness) |
| Kit acceptance-corpus author | family B or C, or the Owner | never the kit builder (§8.1) | idem |
| Scorer-canary authors | half family B, half family C or the Owner (§6.2) | — | review finding (canaries) |
| Participants (kill-carrying) | family A and family B, one pinned model each | ≥ 2 frontier families | ROADMAP §3.2, DR-017 |
| Local pilot | one Hearth-hosted model | not part of the kill | ROADMAP §3.2 |
| Reviewers and defect-claim confirmers | an independent context, ideally family B or C | adversarial brief; logged as same-family if it is not | docs/m0/README.md; record §10.2 |

**Author family = participant family.** If only two API families are available, family B both
authors the items and participates. A familiarity effect that is the same in every arm cancels in
the within-family arm contrasts. One that differs by arm, for example family B's own Rust idioms in
items whose references it wrote, is a **model-family × arm interaction**: it enters the pooled Δ with
weight 1/2, does not cancel, and shows up in the per-family estimates, which are reported. The
simulation's block 11 shows what such an interaction does to the one-family referral rate [S]. A third
authoring family removes the issue and is recommended where available [G].

**Isolation of the agents writing this design.** The Claude sessions building the harness, `mithi`
and the cards (including the one writing this file) are family A. They never receive held-out or
calibration items, hidden reference solutions, audit vectors or planted-corpus items that have not
passed the contamination check. Every X1 artifact they write is public. The operational rules that
make this true are the family-A firewall of §4.6. One caveat: this file's first draft, written by
family A, listed the held-out variant knobs per family; that list is now in the private authoring
brief only, but family A has seen it, so family B is asked to extend it (§5.1) and the semantic guard
(§10.2) is the defence against card atoms aimed at it.

---

## 3. Task format

### 3.1 One item = one directory

```text
<item_id>/                          item_id = "x1-" + 16 hex chars from a CSPRNG (opaque)
  item.json                         manifest (schema below); the hidden part of it lives in hidden.age
  visible.age  ── encrypted to the Runner key (§4.2) ────────────────────────────────────────────
    brief.md                        equal-information brief, identical across arms (domain rules in prose);
                                    the obfuscated arm receives it mapped through obf-v1 (§10.4)
    arms/
      rust/    Cargo.toml  src/lib.rs (stub with signature + todo!())  tests/visible.rs   helpers/ (canon pack)
      c11/     solution.h  solution.c (stub with X1_TODO())  tests/visible.c  helpers/ (canon pack, hearth-style)
      mithril/ solution.mith (stub)  tests/visible.mith  prelude.mith (formats, structs)
      mithril_notraits/  (same as mithril; differs only in the arm's card)
      mithril_obf/       (mechanical token map of mithril/, §10.4)
      rust_kit/          (same as rust/ plus exact.toml, §8.2)
  hidden.age   ── encrypted to the Gatekeeper key of the item's split only (§4.2) ─────────────────
    vectors.x1v                     scoring inputs (TLV, §3.3); every visible-test case is also a case here
    expected.x1v                    expected outputs (from the C reference; cross-checked)
    audit_vectors.x1v, audit_expected.x1v   the audit oracle: ≥ 10× the scoring cases [G], another seed,
                                    never used for scoring (§13.5)
    properties.json                 property and model-based checks (seeds, op counts, reference traces)
    refs/  rust/  c11/  mithril/  mithril_notraits/  mithril_obf/
    mutants/  <lang>/<mutant_id>.patch   kill_report.json
    canary.txt                      the suite canary (§4.4)
```

The drivers that run agent code against vectors are **public** harness code (generated from the
manifest's `io` signature, which agents see anyway); they contain no expected data (§3.3). The C stub
marks its unfinished body with the macro `X1_TODO()`, which the acceptance check counts as a hole
(record §4.9).

### 3.2 Manifest schema (`item.json`)

```json
{
  "schema": "x1-item/1",
  "item_id": "x1-<16 hex>",
  "split": "heldout | iteration | calibration | smoke",
  "sealed_position": 0,
  "family": "T-Q4 | T-ACTQ | T-NORM | T-ROUTE | T-EVICT | T-STORE | T-FMT | T-CTRL",
  "template_id": "<family>/<template slug>",
  "variant": {"<knob>": "<value>"},
  "grade_context": "exact | default | timing_only",
  "unit": {"kind": "fn | type", "name": "...", "signature": {"rust": "...", "c11": "...", "mithril": "..."}},
  "io": {"protocol": "x1v/1", "args": [{"name": "...", "type": "f32[] | u8[] | i32 | ..."}], "outputs": [...]},
  "budgets": {"checker_calls": 8, "max_turns": 60, "max_nonprefix_input_tokens": 600000, "max_output_tokens": 60000,
              "wall_minutes": 45, "per_call_cpu_s": 180, "per_call_wall_backstop_s": 540},
  "oracle": {"kinds": ["vectors", "properties", "sanitizers", "permutations"], "timeout_factor": 10,
             "audit_case_factor": 10},
  "mutants": {"generic": 0, "numerics_v1": 0, "family": 0, "cross_arm_ff": 0, "stillborn": 0,
              "equivalent_with_witness": 0, "killed": 0, "kill_rate": 0.0, "kill_rate_numerics_v1": 0.0,
              "kill_rate_cross_arm_ff": 0.0},
  "contamination": {"max_5gram_containment": 0.0, "max_ast_similarity": 0.0, "flag": "none | public_near | leaked",
                    "max_pair_containment_same_family": 0.0, "max_pair_ast_same_family": 0.0},
  "authoring": {"family": "B", "model": "<pinned id>", "session_hashes": ["sha256:..."],
                "reviewed_by": {"family": "B | C", "session_hash": "sha256:..."}, "owner_sample_reviewed": false},
  "files": {"<relative path>": "sha256:<hex>"}
}
```

The budget values are [G], proposed here, equal across arms, and frozen in the pre-registration.
Only `checker_calls: 8` comes from ROADMAP §3.2 [target, P5]. `max_nonprefix_input_tokens` excludes
each call's fixed system-prompt prefix (§12.1; record §4.12). `per_call_cpu_s` is a CPU-time limit
with a wall-clock backstop (§11.2).

### 3.3 Vector protocol `x1v/1`

A language-neutral binary file so the same cases drive every arm. Little-endian.
`"X1V1"` · u32 family code · u32 case count · cases. Each case is a sequence of TLV fields
(u32 tag, u32 byte length, bytes); tags follow the order of `io.args` (inputs) or `io.outputs`.
Floats travel as raw IEEE bit patterns, so NaN payloads and signed zeros survive.

Per-arm drivers decode a case, call the unit, and encode outputs:
- **C11 and Rust**: a harness-written driver, **public** (generated from the manifest's `io`
  signature), compiled with the agent's file. It reads cases from stdin and writes outputs to a
  harness-owned pipe; it holds no expected data.
- **Mithril arms**: `mithi vectors --entry <path>` reading cases from stdin. `mithi`'s host layer
  decodes the TLV fields into Mithril values from the declared signature, so the code under test needs
  no `io` effect. `mithi vectors` runs the full `mithi check` first and fails on any check error, so a
  program the checker rejects can never pass the oracle.

**Result record.** After the last case, the driver writes a final line carrying a per-run random
nonce that the scorer generated. A run whose record lacks the nonce line, or has fewer cases than
sent, is a fail, so an early `exit(0)` in agent code fails. Exit status alone never counts as a pass.
The same record format carries visible-test outcomes in `check` and in the acceptance check.

The comparison, byte for byte on the outputs plus the property checks in `properties.json` (whose
reference traces stay in the hidden bundle), happens **outside** the container that ran agent code
(§11.3).

---

## 4. Sealing and storage

### 4.1 Hash commitments

1. `file_hash = SHA-256(file bytes)`. `item_hash = SHA-256(canonical JSON of item.json)`, where
   the canonical form has sorted keys, no insignificant whitespace, UTF-8, and `files` lists every
   file in the item directory.
2. `salt_i` = 32 bytes from the OS CSPRNG. `commit_i = SHA-256("x1-commit-v1" ‖ salt_i ‖ item_hash)`.
   The salt stops anyone guessing a small item by hashing candidates.
3. The **suite root** `R = SHA-256(commit_1 ‖ … ‖ commit_N)` over the items in a sealed, seeded
   order (per family: the 23 held-out candidates in their seeded order, then iteration, then
   calibration). The decision set is the first n_final / 8 eligible held-out candidates per family in
   this order (record §4.4); the rest are the reserve.
4. `COMMITMENTS.json` (public) lists, per position: split, family, `commit_i`. It also records R,
   the canary's SHA-256 (§4.4), the authoring family and the sealing date. It enters the repo **in its
   own commit at sealing, before card iteration starts**, so the suite is bound before anyone could
   tune toward it. Any later change (a reference fixed after P-1, a flagged item) is a **dated
   re-commitment** that lists the changed positions and the reason. A flagged, dropped or failed
   held-out candidate is always replaced by the next candidate of the same family in sealed order,
   never by a chosen one.
5. **Reveal for audit only.** After the verdict, the Owner and the independent reviewer receive
   `(salt_i, item)` for any item they want to check and verify `commit_i`. Held-out items are never
   published: at least 15 of them become M1's IRT anchor items (ROADMAP §5).
6. **Template disjointness.** At sealing the Gatekeeper asserts that no `template_id` appears in two
   splits and that no held-out template appears twice (record §4.3); it publishes only the counts.

### 4.2 Storage and access

- Each item is **two separately encrypted bundles** (§3.1), using `age` (X25519). The tool is chosen
  for simplicity; the version is pinned at freeze [not verified in this session].
  - `visible.age` is encrypted to the Owner key (D0-9) and a **Runner key**, which the runner uses to
    start attempts.
  - `hidden.age` is encrypted to the Owner key and a **Gatekeeper key for the item's split**: one for
    iteration items (used during card iteration, whose scoring card editors see), one for calibration
    items, one for held-out candidates.
- **The held-out hidden key is never on a host while agent sessions run.** P-1 and the reference
  agreement check need held-out references before the run; they run as Gatekeeper jobs on a host where
  no agent session runs and no family-A session can read the material (§4.6), and the decrypted
  material is deleted after each job. Held-out scoring starts only after collection (including the
  local pilot) has ended (§1).
- At rest the store lives outside every git repository and every cloud-synced folder, mirroring
  Hearth's INV-DATA.
- A Gatekeeper job decrypts one item's hidden bundle into a RAM-backed tmpfs that **no container
  running agent code mounts** (§11.3). No harness log contains hidden content, only hashes, codes and
  verdict classes.
- Transcripts reveal briefs and visible tests, so they are stored in the private store too. Public
  results carry their hashes.
- API data handling: briefs travel to the model providers. The Owner should confirm that the
  accounts used exclude inputs from training (zero-retention or opt-out terms, where offered)
  [Owner question; not verified].

### 4.3 What goes into the repo

Only: this design, the pre-registration, the harness and analysis code (drivers and the static gate
included), `mithi`, the kit, the grammar, the cards, helper cards and shared domain preamble (after
the card freeze), `COMMITMENTS.json`, the public smoke set (§5) and, after the verdict, aggregate
results with per-item rows keyed by opaque IDs. **No held-out, calibration or iteration item, hidden
reference, oracle or audit vector, planted-corpus item or P-1 reproduction is written into the repo
before the verdict**; after it, only the planted corpus and P-1 reproductions may become public, and
only after the §4.5 check against every hidden reference (§4.6).

### 4.4 Canary

Every hidden file carries one line, `X1 HELD-OUT CANARY <uuid4>`; the UUID is generated at sealing.
The canary appears **only in hidden files**, never in anything an agent reads, because an
agent-visible marker would let an evaluation-aware model detect scoring (03 §10 row 34;
tombstone `x1_canary_in_agent_visible_brief`, §17). The UUID string is published at freeze so that
corpus builders can filter it and so that later models can be probed for it [inference: BIG-bench
used the same device; its effectiveness is not established here].

### 4.5 Contamination check (05 §13, pre-registered thresholds)

Run at sealing, before any agent sees an item, and **re-run at freeze** against the freeze commit;
an item newly flagged at freeze leaves the decision set and is replaced in sealed order (§4.1):
- **Public corpus, fixed at sealing**: Hearth at `b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220` (all
  files); the Mithril repository at HEAD on the sealing date (including this file's public examples),
  and at the freeze commit for the re-run; llama.cpp/ggml at a commit pinned on the sealing date,
  covering at least its Q4 quantisation source, its MoE routing code and its GGUF parsing (the dominant
  public prior for FF-Q4, top-k routing and model-file parsing; file paths are recorded at pinning
  [not verified in this session]); and MultiPL-E at a pinned commit: its Rust translations, and C if
  that commit provides C [not verified in this session]. **MultiPL-E is included**, decided now, not
  left to the authors.
- **Tokenisation**: each language's own lexer (Rust: `syn`/`proc-macro2` tokens; C: Clang's lexer;
  Mithril: `mithi`'s lexer); identifiers are alpha-renamed in order of first appearance; literals are
  kept; comments and whitespace are dropped.
- **Measures**: `containment(ref) = |5-grams(ref) ∩ 5-grams(corpus)| / |5-grams(ref)|`, over the
  normalised token stream; and similarity of alpha-renamed ASTs (Rust and C parsed into one
  normalised form, 05 §17).
- **Thresholds** [target, proposed in 05 §13]: containment ≤ 0.2 and AST similarity ≤ 0.3. Above
  either, the item is flagged `public_near`. **Kill decisions use unflagged items only**; the reserve
  of held-out candidates covers flags (record §4.4).
- **`leaked`** is defined as: the canary UUID, or any contiguous run of ≥ 50 normalised tokens [G] of a
  hidden file, found in a public source or in a model output outside the harness.
- **Within-family near-duplicates** (record §4.3): the same measures between held-out candidates of
  one family; above containment 0.5 or AST similarity 0.6 [G] the later candidate is re-templated or
  replaced before sealing; the distribution of pairwise values is reported, and pairs above 0.2 / 0.3
  form the clusters of the sensitivity analysis.
- **Atom isolation** (05 §13): the same check runs on every Tier 0 and Tier 1 card atom, helper-card
  atom and shared-preamble atom against every hidden reference. It runs **blind**: a failing atom is
  dropped silently; card editors receive only the count of rejected atoms per epoch, and the per-atom
  list goes to the Owner, so the check cannot serve as a membership oracle on the hidden references.
- T-Q4 and T-ACTQ are the families most at risk of `public_near` flags, because Hearth's own
  `quant.c` is public. Their held-out templates must diverge from Hearth's code paths (other layouts,
  strides, batch shapes, block formats) [G].

### 4.6 The family-A firewall

The sessions that build the harness, `mithi`, the kit and the cards are family A (Claude), and in this
project Claude workflows drive most work. Held-out content must not reach a family-A development
context by any operational route. Rules (provisional, pending D0-10 for the host):

1. **Scripted authoring and runs.** Authoring, item review, the semantic guard's inputs, sealing, the
   calibration run and the held-out run are driven by deterministic scripts that call family B's (or
   C's, or a participant's) API directly and write straight into `visible.age` / `hidden.age` or the
   private store. A Claude Code session may launch such a script; it sees only counts, hashes, codes
   and verdict classes. No family-A *development* agent reads item content. (Participant sessions of
   family A are fresh API sessions with the task tools only, and are not development contexts.)
2. **Keys and decrypted material.** Keys and decrypted bundles never sit on a machine where family-A
   development sessions run, unless the Owner has put Claude settings deny rules in force
   (`permissions.deny` for Read and Bash on the store, the tmpfs mount points and `\\wsl$` paths to
   them) and logged them. On the desktop (the pilot host, possibly the execution host) this means: the
   deny rules for the whole held-out run and pilot; for the pilot, only the 10 T-ROUTE items' visible
   bundles, decrypted into tmpfs and deleted afterwards; hidden bundles only during scoring, after
   collection. A rented VM with no family-A sessions avoids the issue (record Owner question 11).
3. **Material derived from hidden content.** P-1 reproductions and the planted corpus (written by
   family B, the held-out authors) stay private until the verdict. If one must reach the `mithi`
   builder earlier (a P-1 failure, a P-2 dev-half miss), it first passes the §4.5 check against every
   hidden reference (containment ≤ 0.2, AST similarity ≤ 0.3) and the release is logged with its hash.
4. **Logs.** Runner and infrastructure logs hold hashes, codes and verdict classes only. Only the Owner
   debugs an infrastructure failure that needs content, and records that it happened.
5. **Item review.** No family-A session ever receives held-out or calibration content for review
   assistance; item review happens in family-B (or C) sessions or by the Owner outside Claude sessions.

---

## 5. The eight task families and one public example each

### 5.1 Family interface specification

| Family | Unit under test | Grade context | Oracle (05 §13) | Sanitizer and safety rules |
|---|---|---|---|---|
| **T-Q4** | function over Q4 blocks and Q8 activations | exact | hash-exact output bits | C: ASan + UBSan; Rust: no `unsafe` (`-F unsafe_code`), overflow checks; Mithril: traps fail |
| **T-ACTQ** | activation quantiser | exact | byte-exact blocks | as T-Q4 |
| **T-NORM** | RMSNorm, softmax, SiLU under canon.v1 | exact | bit-exact | as T-Q4 |
| **T-ROUTE** | grouped top-k, ties to the lower index, NaN last | exact (logits path) | exact indices | as T-Q4 |
| **T-EVICT** | `timing_only` eviction policy | timing_only | exact victim sequence under replay, hint validity, determinism; bytes and stall reported | no clock reads (static symbol scan for Rust/C; type rule for Mithril) |
| **T-STORE** | slab arena with pins and 4096-byte alignment | default | functional, model-based and permutation tests | C: ASan; Rust: no `unsafe` |
| **T-FMT** | bounded container parser | default | fuzz parity (accept/reject + fields) against the reference | C: ASan + UBSan, any report fails; Rust: no `unsafe`, no panic |
| **T-CTRL** | mutex-guarded queue; rank-order combine | exact (combine), default (queue) | permutation tests; exact output | C: TSan; Rust: no `unsafe` |

**Variant knobs** for held-out templates are **not** listed in this public file. They live in the
private authoring brief, which family B extends beyond the family-A draft (§2, last paragraph). T-ROUTE
templates must include selection variants that one `topk` call does not solve (group scoring, group
selection rules, the dropped-group rule, other tie or NaN rules stated in the brief), so the family
keeps measuring tie and NaN handling once every arm has `topk` (§5.1a) [G].

Common rules for every family:
- **Signature fixed by the stub.** The agent fills the body (and private helpers). Edits outside the
  writable files are discarded by the scorer (03 row 31).
- **Helper packs** (equal information, 05 §13): `canon` helpers (`sum16`, `dot16`, `sum_seq`,
  f16→f32, canonical NaN, `canon_v1::expf`) exist in Mithril's std. Rust and C11 arms receive the same
  functions as a small library in their language, together with every other item of §5.1a. The
  implementations are tested to agree bit for bit: exhaustively over all 2^32 inputs for unary f32
  functions, and on 10^7 random inputs [G] for binary ones and for `topk` (indices), before sealing.
- **Visible tests are a subset of the oracle.** Every visible-test case is also a case in
  `vectors.x1v`, so an artifact that passes the hidden oracle also passes the visible tests (record
  §4.9). The reference passes its visible tests under its own executor within 10% of the per-call CPU
  limit [G], checked at sealing (§11.2).
- **Build flags are part of the brief and fixed by the harness**: C11 `-std=c11 -O2
  -ffp-contract=off -fno-fast-math` for the x86-64 baseline (no `-march=native`, so no FMA
  instructions); Rust stable, edition and version pinned, `overflow-checks = true`, and
  `RUSTFLAGS='-F unsafe_code'` set by the harness (a source attribute in a writable file could be
  deleted); Mithril under `mithi`. Hearth's NUMERICS.md requires `-ffp-contract=off` [Hearth
  docs/NUMERICS.md]; Clang's default for C is not `off` [inference, to be confirmed against the pinned
  Clang]. `check`, the acceptance check and the oracle use **exactly the same flags and sanitizers per
  arm** (§7).

### 5.1a Helper parity

Every std or prelude item reachable by the Mithril arms at X1 has a Rust and a C11 equivalent with the
same name and semantics, shipped in the helper packs and listed in the helper cards (§7.1).

| Mithril X1 item | Rust helper pack | C11 helper pack | Agreement test |
|---|---|---|---|
| `canon::sum16`, `dot16`, `sum_seq` | same names, `fn(&[f32]) -> f32` etc. | `hx_sum16`, `hx_dot16`, `hx_sum_seq` | 10^7 random inputs [G], bits |
| `f16` storage, `.to_f32()` | `f16_to_f32(u16) -> f32` | `hx_f16_to_f32(uint16_t)` | all 2^16 inputs, bits |
| `canon::nan` (canonical NaN) | `canon_nan() -> f32` | `HX_CANON_NAN` | exact |
| `canon_v1::expf` | `canon_v1_expf(f32) -> f32` | `hx_canon_v1_expf(float)` | all 2^32 inputs, bits |
| `round_ties_even` | `f32::round_ties_even` (Rust std, stable [inference, not verified against the pinned version]) | `hx_round_ties_even(float)` | all 2^32 inputs, bits |
| `topk(k, Ties::LowerIndex, Nan::Last)` | `topk(xs: &[f32], k: usize, out: &mut [u32])`, same order rules | `hx_topk(const float*, int32_t n, int32_t k, int32_t *out)` | 10^7 random and adversarial inputs (ties, NaN, ±0, ±inf), indices (provisional; record Owner question 20) |
| every prelude `format` (for example a `nibbles<N, offset = k>` field) | an accessor function per field with the same layout, generated from the same declaration | idem | exhaustive over the field's bit width |
| `std_platform::Mutex<T>::with_lock`, scoped threads, `Condvar` | Rust std `Mutex`, `thread::scope`, `Condvar` | C11 `<threads.h>` | — (std on both sides) |
| `SlabBuf<N>`, `Hint<T>` | `SlabBuf` type with the same API, `Hint<T>` newtype | `hx_slabbuf_*`, `hx_hint_*` | model-based tests |

**Not in any arm's X1 library:** the whole-task canon helpers `canon::act_q8`, `canon::matvec_q`,
`canon::rmsnorm`, `canon::softmax`, `canon::silu`, `canon::sigmoid`, `canon::rope` and
`canon::combine_rank` (02-compute's canon table). Each would solve a task family outright, so `mithi`
rejects them at X1 with `E-X1-NOTYET-CANON`, and the Rust and C11 packs omit them.

### 5.2 The public smoke set

The eight examples below form the **public smoke set** `S-*-0`. They are public on purpose: they
are used only to shake down the harness, the drivers, the sandbox and the scorer end to end. They
are **never scored for any gate, never used for card iteration, and never held out.** They enter the
public corpus of the contamination check (§4.5), so any sealed item too close to one is flagged.
Five of them restate behaviour Hearth already publishes in `docs/NUMERICS.md`, `docs/FORMAT.md` or
the Mithril README, so they reveal nothing new. Mithril signatures are provisional (the Surface Lab
decides syntax).

#### S-Q4-0 (T-Q4): one Q4 weight row times one Q8 activation (NUMERICS §3)

```rust
#[derive(Clone, Copy)] #[repr(C)] pub struct BlockQ4 { pub d: u16, pub qs: [u8; 32] } // f16 bits; byte j: lo nibble = elem j, hi = elem j+32; stored q+8
#[derive(Clone, Copy)] #[repr(C)] pub struct ActQ8 { pub d: f32, pub sum: i32, pub q: [i8; 64] }
pub fn q4_row_dot(w: &[BlockQ4], a: &[ActQ8]) -> f32 { todo!("q4_row_dot") }  // w.len() == a.len()
```
```c
float q4_row_dot(const hx_block_q4 *w, const hx_act_q8 *a, int64_t nb);
```
```mith
kernel fn q4_row_dot(w: &[BlockQ4], a: &[ActQ8]) -> f32 requires w.len() == a.len() { todo!("q4_row_dot") }
```
- **Meaning.** `acc = +0.0`; for each block g: `isum = Σ_j (nibble_j − 8)·q_j` (exact i32); then
  `acc = acc + (isum as f32) * (f16_to_f32(w[g].d) * a[g].d)`, unfused. A NaN result is returned as
  `0x7fc00000`.
- **Oracle.** 4,096 random cases with nb in 1..=64 [G], plus edge cases: nb = 0 (→ +0.0); scale ±0,
  subnormal f16, ±inf, NaN; extreme |isum|; `a.d = −0.0`, which tests that `acc` starts at +0.0;
  cancellation. Output bits compared.
- **Mutants.** FMA contraction (`mul_add`); `(isum·dw)·dx` reassociation; high nibble at j+16
  (llama.cpp Q4_0 prior, FF-Q4); missing −8; float accumulation of isum; no NaN canonicalisation;
  `acc` seeded with the first product (sign of zero); f16 conversion flushing subnormals.

#### S-ACTQ-0 (T-ACTQ): Q8 activation quantisation (NUMERICS §2)

```rust
pub fn act_quantize_q8(x: &[f32], out: &mut [ActQ8]) { todo!() } // x.len() % 64 == 0, out.len() == x.len() / 64; x finite
```
```c
void act_quantize_q8(const float *x, hx_act_q8 *out, int64_t n);
```
```mith
kernel fn act_quantize_q8(x: &[f32], out: &mut [ActQ8]) requires x.len() % 64 == 0 && out.len() * 64 == x.len() { todo!() }
```
- **Meaning.** Per block: `amax = max|x_i|`; `d = amax / 127.0`; `id = d != 0 ? 1/d : 0`;
  `q_i = round_half_even(x_i * id)` as i8; `sum = Σ q_i` (exact).
- **Oracle.** 2,000 random blocks [G] plus constructed ties (`x_i·id` exactly k + 0.5), an all-zero
  block, single outliers, subnormal inputs, −0.0 inputs. Bytes compared.
- **Mutants.** `round()` (ties away from zero, FF-ROUND); truncation; `127/amax` as the reciprocal;
  `x/d` in place of `x·id`; clamp at ±128 or none; float sum; scale computed in f64.

#### S-NORM-0 (T-NORM): RMSNorm with the canonical sum (NUMERICS §1, §4)

```rust
pub fn rmsnorm(y: &mut [f32], x: &[f32], w: &[f32], eps: f32) { todo!() } // helper: canon::sum16
```
```c
void rmsnorm(float *y, const float *x, const float *w, int64_t n, float eps);
```
```mith
kernel fn rmsnorm(y: &mut [f32], x: &[f32], w: &[f32], eps: f32) requires x.len() == y.len() && w.len() == x.len() { todo!() }
```
- **Meaning.** `ms = sum16(x_i·x_i) / (float)n`; `r = 1/sqrtf(ms + eps)`; `y_i = (x_i·r)·w_i`.
- **Oracle.** n ∈ {1, 15, 16, 17, 64, 4096}; wide dynamic range; overflow of `x_i²` to +inf
  (r = 0, signed zeros in y); all-zero x; two eps values. Bits compared.
- **Mutants.** Sequential sum (FF-SUM: Mithril rejects it in exact code); 8 lanes; a different final
  tree; `mul_add` in the square-accumulate; `x_i·(r·w_i)`; `ms·(1/n)`; reciprocal-sqrt approximation;
  f64 accumulation.

#### S-ROUTE-0 (T-ROUTE): group-limited top-k selection (NUMERICS §5.3)

```rust
pub fn group_topk(sel: &[f32], n_group: usize, topk_group: usize, k: usize, ids: &mut [u32]) { todo!() }
```
```c
void group_topk(const float *sel, int32_t n, int32_t n_group, int32_t topk_group, int32_t k, int32_t *ids);
```
```mith
kernel fn group_topk(sel: &[f32], n_group: usize, topk_group: usize, k: usize, ids: &mut [u32]) { todo!() }
```
- **Meaning.** Exactly NUMERICS §5.3's selection step: group score = sum of the group's top-2 `sel`
  values; keep the `topk_group` best groups (ties → lower group index); experts in dropped groups get
  `sel := 0.0` **and remain eligible**; then pick the top `k` experts by `sel`, descending, ties →
  lower index. Ordering is by IEEE value (−0.0 = +0.0); NaN ranks after every number (NaN last),
  lower index first among NaNs. The NaN rule is stated in the brief, since NUMERICS does not cover
  NaN `sel`; it matches `ranks_before` in Hearth's `engine/src/model.c` at b5d3f14 (read by this
  track, 2026-10-16), which also zeroes dropped groups' `sel` and keeps them eligible.
- **Oracle.** 5,000 random cases plus adversarial ones: ties within and across groups, NaNs, ±0,
  ±inf, negative scores (which exercise the "dropped experts stay eligible at 0.0" rule),
  k = n, topk_group = n_group. Exact indices compared.
- **Mutants.** `max_by` keeping the last maximum (FF-TIES); unstable sort; NaN first; `total_cmp`
  (orders −0.0 below +0.0); group score from the top-1 only; ties to the higher index; dropped
  experts excluded instead of zeroed.

#### S-EVICT-0 (T-EVICT): LRU victim choice as a `timing_only` policy

```rust
#[derive(Clone, Copy)] pub struct SlotView { pub id: u32, pub pinned: bool, pub refs: u32, pub loading: bool, pub last_use: u64 }
pub fn pick_victim(slots: &[SlotView], now: u64) -> Option<u32> { todo!() }   // last_use <= now
```
```c
int64_t pick_victim(const slot_view *slots, int32_t n, uint64_t now);   /* -1 = no victim */
```
```mith
policy fn pick_victim(slots: &[SlotView], now: Tick) -> Hint<SlotId> { todo!() }
```
- **Meaning.** Candidates are slots with `!pinned && refs == 0 && !loading`. Return the candidate
  with the largest `now − last_use`, **including age 0**; ties → lower `id`; none → no victim. (The
  README sketch starts `best_age` at 0 with a strict `>`, so it never picks an age-0 slot; this
  example's brief states the rule explicitly.)
- **Oracle.** (1) 10,000 random slot sets, exact victim. (2) Replay: a harness-written store
  simulator, identical in each language and cross-checked on the reference policy, replays three
  synthetic routing traces; the eviction sequence must equal the reference's, every hint must be valid,
  and NVMe bytes and stall are reported (context only). (3) Determinism: the same inputs called at two
  different real times give the same output. (4) No clock: for Rust and C, a symbol scan of the object
  rejects references to `clock_gettime`, `gettimeofday`, `QueryPerformanceCounter`, `rdtsc` and
  `std::time`; Mithril enforces this by the `policy fn` row (FF-CLOCK). The scan is a heuristic
  [G].
- **Mutants.** Strict `>` from best age 0; ties to the higher id; `loading` ignored; `refs` ignored;
  MRU instead of LRU; a pinned slot returned when there is no candidate.

#### S-STORE-0 (T-STORE): fixed-capacity slab arena with pins and 4096-byte alignment

```rust
pub struct SlabArena { /* agent-defined */ }
pub enum ArenaError { BadConfig, NotAllocated, Pinned, NotPinned, OutOfRange }
impl SlabArena {
    pub fn new(n_slots: u32, slab_bytes: usize) -> Result<SlabArena, ArenaError> { todo!() } // slab_bytes > 0, multiple of 4096
    pub fn alloc(&mut self) -> Option<u32> { todo!() }                 // lowest free index; slab zeroed
    pub fn free(&mut self, id: u32) -> Result<(), ArenaError> { todo!() }
    pub fn pin(&mut self, id: u32) -> Result<(), ArenaError> { todo!() }
    pub fn unpin(&mut self, id: u32) -> Result<(), ArenaError> { todo!() }
    pub fn write(&mut self, id: u32, off: usize, src: &[u8]) -> Result<(), ArenaError> { todo!() }
    pub fn read(&self, id: u32, off: usize, dst: &mut [u8]) -> Result<(), ArenaError> { todo!() }
    pub fn addr(&self, id: u32) -> Result<usize, ArenaError> { todo!() }  // for the alignment check
}
```
C11 mirrors this with `slab_arena *arena_new(...)` and error codes. The Mithril version uses
`std_platform::SlabBuf<4096>`. No method returns a reference, so the API is legal in Mithril without
projections (FF-REF) and identical in every arm.
- **Meaning.** Lowest-free-index allocation; freshly allocated slabs read as zero; `free` of a pinned
  slot → `Pinned`; double free → `NotAllocated`; pin counts nest; `unpin` at zero → `NotPinned`;
  out-of-range offsets → `OutOfRange`.
- **Oracle.** Model-based random operation sequences (10,000 operations × 200 seeds [G]) against a
  reference model; alignment (`addr % 4096 == 0`) and non-overlap; read-after-write; zero-on-alloc;
  permutation tests (freeing one set of slots in every tested order gives the same later allocation
  sequence).
- **Mutants.** FIFO or highest-index allocation; no zeroing on reuse; free-while-pinned allowed; unpin
  underflow; 64-byte alignment; capacity off by one; non-multiple `slab_bytes` accepted.

#### S-FMT-0 (T-FMT): routing-trace parser (FORMAT.md §9)

```rust
pub struct ModelDims { pub n_experts: u32, pub top_k: u32, pub n_moe_layers: u32 }
pub struct TraceHeader { pub n_layers: u32, pub n_experts: u32, pub top_k: u32, pub n_moe_layers: u32, pub n_tokens: u64 }
pub enum TraceError { Truncated, BadMagic, BadVersion, Mismatch, BadId }
pub fn parse_trace(buf: &[u8], m: &ModelDims, ids: &mut Vec<u16>) -> Result<TraceHeader, TraceError> { todo!() }
```
- **Meaning.** Six little-endian u32 (magic `0x52545248` "HRTR", version 1, n_layers, n_experts,
  top_k, n_moe_layers), then per token `n_moe_layers·top_k` u16 ids. Checks in this order:
  (1) length ≥ 24, else `Truncated`; (2) magic; (3) version == 1; (4) n_experts, top_k and
  n_moe_layers equal the model's, else `Mismatch`; (5) n_layers ≥ n_moe_layers, else `Mismatch`;
  (6) the record size `n_moe_layers·top_k·2` is non-zero and divides `len − 24`, else `Truncated`;
  (7) every id < n_experts, else `BadId`. The order is part of the brief because FORMAT.md does not
  fix it.
- **Oracle.** Fuzz parity on 100,000 inputs [G]: valid traces of random length; truncation at every
  byte up to 64; header bit flips; huge counts; out-of-range ids; trailing partial records. The result
  kind, header fields and ids must equal the reference's. C runs under ASan + UBSan (any report
  fails); Rust under the harness's `-F unsafe_code` with no panic; Mithril with no trap.
- **Mutants.** Version check removed; `>` for `≥`; trailing bytes accepted; `≤ n_experts`;
  big-endian reads; header read before the length check (out-of-bounds); record size computed in u32
  before the dimension check (overflow); error precedence swapped.

#### S-CTRL-0 (T-CTRL): rank-order combine behind a mutex (NUMERICS §5.3, last step)

```rust
pub enum CombineError { BadRank, Duplicate, Incomplete, BadLength }
pub struct Combiner { /* agent-defined; must be Sync */ }
impl Combiner {
    pub fn new(k: usize, d: usize, w: &[f32]) -> Combiner { todo!() }
    pub fn deposit(&self, rank: usize, y: &[f32]) -> Result<(), CombineError> { todo!() } // called from k threads
    pub fn finish(self) -> Result<Vec<f32>, CombineError> { todo!() }
}
```
C11 uses `<threads.h>` (`mtx_t`); Mithril uses `std_platform::Mutex<T>::with_lock` and scoped threads.
- **Meaning.** `out_i = 0.0; for j in 0..k (rank order): out_i = out_i + w_j·y_j[i]` (product
  rounded, never fused), whatever order the deposits arrive in.
- **Oracle.** 500 cases × 20 forced arrival orders [G] (per-thread start barriers driven by the
  harness; `mithi` uses its seeded scheduler), plus 64 free-running stress schedules; bits compared;
  error cases; C under TSan.
- **Mutants.** Accumulation in arrival order (passes only when arrival equals rank order); seeding
  with `w_0·y_0` (−0.0 survives where +0.0 + −0.0 = +0.0); `mul_add`; no lock (TSan); `finish` without
  a completeness check; duplicate deposits overwrite.

---

## 6. Oracles and the mutant-kill requirement

### 6.1 Oracle composition

An item's hidden oracle is the conjunction of:
1. **Vectors**: the outputs for `vectors.x1v`, compared byte for byte with `expected.x1v` outside the
   container that ran the code (§11.3).
2. **Properties**: model-based sequences, permutations and determinism re-runs, as `properties.json`
   declares; the code under test emits output traces for harness-chosen operation sequences and
   arrival orders, and the traces are compared with the reference traces outside the container.
3. **Safety**: sanitizer reports (C), `unsafe` (refused at build by `-F unsafe_code`) and panics
   (Rust), traps (Mithril). Any one fails the item.
4. **Static gate** (§11.4): a hit fails the item.
5. **Completeness**: a result record without the run's nonce line, or with fewer cases than sent,
   fails the item (§3.3). Exit status alone never counts as a pass.
6. **Timeouts**: 10× the reference solution's CPU time in the same executor [G], with a floor of 5 s.
   The factor is per arm, so `mithi`'s interpretation overhead is not counted against Mithril arms.

**Expected outputs** come from the C11 reference, compiled with the brief's flags. Before sealing,
the Rust reference natively and the Mithril, no-traits Mithril (under `mithi --no-user-traits`) and
obfuscated-Mithril references under `mithi` must reproduce `expected.x1v` bit for bit. This
**reference agreement check** also differentially tests `mithi`'s execution semantics against two
compilers, on the references' code paths only; §13.5's executor differential test extends it to real
agent code.

**Self-tests at sealing**: every reference passes its own oracle in its own executor, twice
(determinism); the oracle rejects the stub (`todo!()` / `X1_TODO()`); every visible-test case is
present in `vectors.x1v` (§5.1); and the audit oracle (`audit_vectors.x1v`, ≥ 10× the scoring cases
[G], a different seed) passes every reference. The audit oracle is never used for scoring (§13.5).

### 6.2 The ≥ 95% mutant-kill requirement (ROADMAP §3.2, 05 §13)

ROADMAP: "Every oracle must kill at least 95% of mutants, including `numerics_v1`." Made precise
here, never loosened:

- **Unit.** Each (item, reference language) pair: Rust, C11, Mithril. Obfuscated Mithril maps
  token for token onto Mithril and inherits its result.
- **Mutant sources.**
  - *Generic* operator mutants from a per-language tool: `cargo-mutants` for Rust; an LLVM-based or
    source-level mutator for C (Mull is a candidate); `mithi --mutate` for Mithril (AST-level:
    arithmetic and relational operator swaps, constant ±1, statement deletion, condition negation,
    `return` of a default value). Tool versions are pinned at freeze [tool behaviour not verified in
    this session].
  - *numerics_v1* classes (P5 §10.1, X2): FMA contraction; lane count and reduction-tree shape;
    RNE → truncation; 127 → 128 clamp; dropped scale; tie flip; NaN canonicalisation removed;
    NEOX ↔ GPT-J RoPE swap. Each class is applied wherever it is meaningful for the item. The X2 track
    owns the canonical `numerics_v1` pool; X1 uses its class definitions and adds per-item
    instantiations.
  - *Family* mutants: the lists in §5 for each family, instantiated per template.
  - *Cross-arm false-friend* mutants (`cross_arm_ff`): for each 01 §2.5 row applicable to the item,
    the idiomatic Rust and C forms of the error instantiated as mutants of the Rust and C references,
    for example `.iter().sum()` for a canonical sum, `max_by(partial_cmp)` (last maximum) for a
    lower-index tie rule, `f32::max` for a NaN rule, `round()` for ties-to-even, `a*b+c` built with
    contraction, `total_cmp` where ±0 must compare equal. This measures each oracle against the error
    distribution of the *other* arms, not only against mutants of its own reference.
- **Counting.**
  - `stillborn` mutants (fail to compile or type-check) leave the denominator.
  - `equivalent` mutants leave the denominator **only with a recorded witness**: exhaustive
    equality over the item's whole input domain where it is enumerable, or a reviewer-signed argument.
    The raw rate without equivalence exclusions is always reported next to the adjusted one.
  - **Killed** = any oracle component fails (wrong bytes, property failure, sanitizer report, crash,
    timeout).
- **Requirement** [target]: for every (item, language), `killed / (generated − stillborn −
  equivalent_with_witness) ≥ 0.95`, **and** the same ratio computed over the `numerics_v1` subset
  alone is ≥ 0.95 whenever that subset is non-empty, **and** over the `cross_arm_ff` subset alone
  ≥ 0.95 whenever it is non-empty. The subset clauses are how this record reads "including
  `numerics_v1`": a pool full of easy generic mutants cannot hide weak numerics coverage, or weak
  coverage of another arm's idiomatic errors.
- **Failure.** An item that misses any ratio is strengthened (more vectors, more properties) and
  re-measured, or dropped and replaced in sealed order, **before sealing**. No item is sealed below the
  requirement.
- **Scorer canaries** (03 §14's "blind Adversary batch … scored among real attempts"), pushed through
  the scoring pipeline as if they were attempts and excluded from every metric. Per reference language
  (Rust, C11, Mithril; the no-traits and obfuscated arms reuse the Mithril ones, mechanically mapped or
  checked under `--no-user-traits`, and the kit arm reuses the Rust ones) and per task family:
  - ≥ 2 **wrong-but-plausible** submissions [G], which must score FAIL;
  - ≥ 2 **correct-but-non-reference** submissions [G] (alternative correct implementations), which
    must score PASS, so a driver, an x1v decoder in `mithi`'s host layer or the obfuscation round trip
    that falsely rejects correct code is caught;
  - one **gaming** canary per route of §11.4 (filesystem read of a guessed hidden path, compile-time
    inclusion, environment read, early `exit(0)`, `abort`, `atexit`), which must score FAIL.
  Half of the canaries are written by family C or the Owner, half by family B, so they do not share one
  family's blind spots. Any wrong canary verdict blocks the held-out run.

---

## 7. The six arms

All six run from day one; the tooling arm runs only if its kit is ready (§8.3). The arm
descriptions are copied from ROADMAP §3.2:

| Arm | What the agent gets (ROADMAP §3.2, verbatim) | Toolchain behind `check` | Card in context |
|---|---|---|---|
| Mithril | Paper Mithril, Tier 0+1, `mithi` as checker, static-dispatch traits (DR-005) | `mithi check` (+ `mithi test` on visible tests); hole report for every `todo!()` (§9.4) | Tier 0 + Tier 1 |
| Mithril without traits | Traits rejected by a Dc diagnostic, so the cost of their absence is measured (DR-005) | `mithi --no-user-traits` | Tier 0 + Tier 1 with the trait atoms replaced by one rejection line (§10.3) |
| Rust | rustc/cargo, same oracles and checker-call budget | `cargo build` + `cargo test --test visible`, offline, std only, `-F unsafe_code` | the Rust helper card (§7.1) |
| C11 | Clang, same oracles | `clang -std=c11 …` with the oracle's sanitizers + visible test binary | the C11 helper card (§7.1) |
| Rust + Mithril tooling | Rust plus the M0 tooling kit (above): the false-friend lint pass over Rust, `todo!()` hole context through rust-analyzer, the same check loop. `mithc lift` and full diagnostics join at M1, so at X1 this arm is a floor for the cheapest competitor | as Rust, plus `x1-fflint` and the hole shim (§8) in the same `check` | the Rust helper card plus the false-friend rows as lint rules (§7.1) |
| Obfuscated Mithril | Same semantics with renamed keywords. Separates comprehension from guessability [P1 §7.11] | `mithi --token-map obf-v1` | the obfuscated Tier 0 + Tier 1 (§10.4) |

Every arm also carries the **shared domain preamble** (§10.2) in its system prompt.

**Equal across arms** (05 §13): the brief, the shared domain preamble, the oracles, the visible tests'
content, the **checker-call budget of 8 per task** [target, ROADMAP §3.2, P5], the turn, token and
wall-time budgets (§3.2; tokens counted excluding each arm's fixed prefix, §12.1), the tool set, the
sandbox limits, the static gate, and the model settings per family. **`check` uses exactly the oracle's
build flags and sanitizers per arm** (C11: ASan + UBSan, TSan for T-CTRL; Rust: overflow checks and
`-F unsafe_code`; Mithril: `mithi`'s full check), so no arm meets a failure class at scoring that its
own checker could never show it.

### 7.1 Helper cards (Rust, C11, kit)

05 §13: "Where the Mithril card has a snippet for a construct the task needs, the Rust and C11 arms
get an equivalent snippet of similar size in their own language." The helper card for each of the
Rust, C11 and kit arms holds:
- the signatures of its helper pack (§5.1a), with one usage snippet per helper;
- for every Mithril-card snippet of a construct a task needs (a `format` field access, a canonical
  reduction, a `policy fn` hint, a scoped-thread lock), the equivalent snippet in its language;
- in the kit arm, every false-friend row as a lint rule with its `deny` or `warn` level (§8.2).

Language content (syntax, keywords, Mithril's false-friend rows) stays arm-specific (05 §13); domain
rules go to the shared preamble, never to one arm's card (§10.2). Helper cards pass the same blind atom
isolation check as the Mithril cards (§4.5) and freeze with them. Brief, card and preamble sizes (bytes
and tokens on the pinned tokenizers) are logged per arm; they are not padded to equal length.

**Tools available to the agent** (identical in every arm):

| Tool | Effect | Counts against the 8 checker calls? |
|---|---|---|
| `list_files()` | lists the writable and read-only task files | no |
| `read_file(path)` | returns a file | no |
| `write_file(path, text)` / `str_replace(path, old, new)` | edits a writable file | no |
| `check(run_tests: bool)` | runs the arm's checker and the static gate (§11.4), plus the visible tests if asked (outcomes from the nonce-terminated result record, §3.3), in a fresh sandbox; returns JSON (§9.4, §8) | **yes, 1 per call** |
| `submit()` | declares the work done; ends the attempt; the only ending that can score a verified pass (record §4.8) | no |
| `abandon(reason)` | ends the attempt as abandoned (counts as a fail on a solvable item, 05 §13) | no |

There is no shell, no network and no other file access. After the 8th `check`, further `check` calls
return `{"error":"budget_exhausted"}` and cost a turn. Code travels as text payloads (05 §1 rule 1).
Time a `check` call spends queued for a sandbox (admission control, §11.2) is excluded from the
attempt's wall budget.

**Why holes reach the Mithril arms at X1.** The tooling arm is defined as "the Mithril arm's tooling
applied to Rust" (05 §13). If only the Rust tooling arm got hole context, amber (a) would compare
Mithril without holes against Rust with holes. `mithi`'s type checker already knows each hole's
expected type and scope, so `check` reports them for the three Mithril arms as well (§9.4)
[provisional; an Owner question].

---

## 8. The M0 tooling kit (buildable spec)

ROADMAP §3.2: "a rust-analyzer-based shim that answers `todo!()` holes with the expected type,
in-scope bindings and relevant trait impls; and the false-friend table ([01 §2.5]) as a clippy-style
lint pass over Rust. About 10 owner hours and $1–2k [inference]."

Both parts run inside the Rust + tooling arm's `check`. Their output is merged into one JSON
response with the rustc diagnostics.

### 8.1 Hole shim `x1-holes`

**Input**: the crate in the sandbox workspace. **Output**, one entry per `todo!(…)` reachable in the
writable files:

```json
{"holes":[{"name":"q4_row_dot","at":{"file":"src/lib.rs","fn":"q4_row_dot","anchor":"todo!(\"q4_row_dot\")"},
  "expected":"f32","status":"known | unconstrained | error",
  "in_scope":[{"name":"w","type":"&[BlockQ4]","mode":"shared"},{"name":"a","type":"&[ActQ8]","mode":"shared"}],
  "relevant_impls":[{"type":"BlockQ4","traits":["Clone","Copy"]},{"type":"f32","traits":["Sum<f32>","Add","Mul"]}],
  "false_friends":["FF-SUM: float .sum() is a sequential left fold; exact code needs canon::sum16"]}]}
```

The `false_friends` field holds the rows of §8.2 relevant to the hole's grade context, as `mithi`
does for the Mithril arm (DR-003, 05 §6).

**Mechanism** (to be confirmed in the week-1 spike; nothing below has been run in this session):
- *Expected type*: a **rustc probe**. In a scratch copy, replace the hole expression with `()` and
  run `cargo check --message-format=json`. The E0308 "expected `T`, found `()`" diagnostic names the
  expected type. If the probe type-checks, the expected type is `()`. If rustc asks for annotations,
  the result is `unconstrained`. This uses only stable rustc [inference].
- *In-scope bindings*: rust-analyzer as an LSP server, queried for completions at the hole's
  position, keeping locals and parameters with their `detail` types. Fallback: a `syn`-based
  lexical-scope walk, typed by a second rustc probe that inserts `let _: () = <binding>;` for each
  candidate binding and reads the "found" type from E0308 [inference].
- *Relevant impls*: for the expected type and each binding's type, a **trait probe file** containing
  one `fn _p_k() where T: Trait {}` per trait in a fixed list (Copy, Clone, PartialEq, PartialOrd,
  Ord, Default, Debug, Iterator, IntoIterator, Sum, Add, Mul, Sub, Div, From, Into), plus every trait
  declared in the crate, compiled once; a trait holds when its probe produces no error [inference].
  rust-analyzer's "go to implementation" adds crate-local impls if the spike shows it is reliable.
- ROADMAP calls the shim "rust-analyzer-based". The rustc probes are the fallback for whatever the
  rust-analyzer LSP surface does not expose. If the spike shows the probes alone meet the acceptance
  tests, the record notes the mechanism change; what the arm *gets* does not change.

**Acceptance tests** (all must pass before the held-out run):
- a 40-hole corpus [G] written by **family B or C, or the Owner, never by the kit's builder**, over the
  public smoke set and invented code (never sealed items), with its truth tables written by the same
  author: expected type exact for every `known` hole; every parameter and `let` binding visible at the
  hole listed with the correct type; the trait list matches the truth table;
- **parity with `mithi`'s hole report**: the same 40 holes written in both Rust and Mithril; the kit's
  report must match `mithi`'s in field completeness (expected type, bindings with types and modes,
  relevant impls, false-friend rows), with 100% equality of the expected type [target] (modulo the
  spelling of types that differ between the languages, listed in a mapping table);
- latency ≤ 20 s per `check` on the sandbox's 2 cores [G], so the hole report does not change the
  check loop's wall time much;
- deterministic output (byte-identical across two runs).

### 8.2 False-friend lint `x1-fflint`

**Input**: the crate plus a task-provided sidecar `exact.toml` (read-only to the agent) that lists the
functions in exact-graded or `timing_only` context. This is the Rust analogue of Mithril's grade
context (01 §2.2; 05 §17: "Grades and claims come from a sidecar spec file owned by the Author
role"). **Output**: diagnostics
in the 05 §5 JSON shape (`code`, `construct`, `prior`, `rule`, `fixes`) with Mithril's codes
(`E-FF-SUM`, …), never rustc's `E0xxx` numbers.

| Row (01 §2.5) | Lint fires on (in Rust) | Level in exact fns | Level elsewhere |
|---|---|---|---|
| FF-SUM | `Iterator::sum`, `product` or `fold` over `f32`/`f64` | deny | allow |
| FF-TIES | `max_by`, `min_by`, `min_by_key` over float keys (01 §2.5's Rust forms); fix: the helper pack's `topk` | deny | allow (timing_only: allow) |
| FF-TIES, extended (not in 01 §2.5) | `max_by_key` over float keys; `sort_by`/`sort_unstable_by` with `partial_cmp` | **warn** (a stable `sort_by` with `partial_cmp` can be correct Rust, which Mithril would accept) | allow |
| FF-EXP | `f32::exp`, `ln`, `sin`, `cos`, `tan`, `powf`, … | deny | allow |
| FF-POWI | `powi` | deny | allow |
| FF-MULADD | `mul_add` | warn (one rounding; legal but never in canon.v1 meanings) | allow |
| FF-ROUND | `f32::round` where the brief states ties-to-even | warn | warn |
| FF-REF | reference-typed struct fields; returned references; lifetimes | warn (not an error in Rust; reported so the arm sees what Mithril would reject) | warn |
| FF-LOCAL | returned or stored closures capturing borrows | warn | warn |
| FF-DYN | `dyn Trait`, `Box<dyn Fn…>` | warn | warn |
| FF-ASYNC | `async`, `await`, `macro_rules!` | warn | warn |
| FF-CELL | `Cell`, `RefCell`, `Rc`, `static mut`, unscoped `thread::spawn` | warn | warn |
| FF-UNSAFE | `unsafe` | deny | deny (the oracle forbids it anyway) |
| FF-CLOCK | `Instant::now`, `SystemTime::now` | deny in timing_only and exact fns | allow |
| FF-OVF | `wrapping_*` absent where the brief requires trapping: not linted (overflow checks are on in every Rust build here) | — | — |
| FF-F16, FF-Q4, FF-HOLE, FF-NANMAX, FF-CAST, FF-FMA | no Rust lint needed: no stable `f16` arithmetic; FF-Q4 is a brief-level layout rule; FF-HOLE, FF-NANMAX, FF-CAST and FF-FMA coincide with Rust's meaning | — | — |

`deny` findings make `check` report failure and block acceptance (§13.1), mirroring Mithril's Dc
rejections in exact code. `warn` findings are informational. Two rules keep the kit a fair floor:
- **The `deny` set is a subset of 01 §2.5's Dc rows in their grade contexts.** No pattern outside a
  row's Rust-form column is denied; every extension is `warn`, and this table lists each one. The
  subset-restriction rows (FF-REF, FF-LOCAL, FF-DYN, FF-ASYNC, FF-CELL) stay `warn` because Rust gives
  them Rust meaning; denying them would reject correct Rust.
- **Every `deny` fix names something the arm has**: a function in the Rust helper pack (`sum16`,
  `canon_v1_expf`, `topk`, …) or an explicit rewrite (explicit multiplications for `powi`; removing the
  clock read). A fix never names a Mithril-only item.

**Mechanism.** Most rows need types: `.sum()` is a false friend only over floats. The preferred
implementation is a **late lint pass with type information**, built as a `dylint` library on a
pinned nightly toolchain (clippy-style; it runs separately from the stable compile). The fallback is
a `syn` pass whose receiver types come from rustc probes, as in §8.1 [inference; neither has been
built or run here].

**Acceptance tests** (written by family B or C, or the Owner, never by the kit's builder): for each
row in the table, ≥ 3 positive and ≥ 3 negative cases [G] (for example `.sum()` over `i32` must not
fire, and a correct stable `sort_by(partial_cmp)` must not be denied), 100% correct; zero `deny`
findings on the Rust references of the public smoke set; deterministic.

### 8.3 "Kit ready" criterion and fallback

The kit is **ready** when both acceptance suites pass on the frozen sandbox image and the kit's hash
is recorded in the pre-registration. If it is not ready when the held-out run starts, then per ROADMAP
§3.2 "the arm is dropped from X1 and starts at M1, and amber (a) waits for M1". The verdict record
says so, and nothing else changes.

Estimated build effort: ~2–3 agent-days plus ~10 owner hours and $1–2k, as ROADMAP states
[inference].

---

## 9. `mithi` and the checker precondition

### 9.1 Scope

`mithi` is "an independent Rust tree-walking interpreter with a type checker (~4–6k lines,
[inference, P5 §10.1]). It becomes M1's differential oracle" (ROADMAP §3.2). It is a separate crate
that shares nothing with `mithc`'s lowering (04 §13, DR-010). At X1 it is the Mithril arms' checker
**and** their executor: the hidden oracle runs Mithril solutions under `mithi`.

**The X1 subset** is what the X1 references and the Tier 0 card need, and no more. The core-calculus
note's rules for this subset freeze at the checker precondition (ROADMAP §3.2).

| In the X1 subset | Out (rejected with a named diagnostic) |
|---|---|
| `fn`, `kernel fn`, `policy fn`; `struct`, `enum`, `impl`, `trait` (static dispatch, DR-005); generics with bounds; const generics (`SlabBuf<4096>`); `use` of std | `schedule`, `spec`, `claim`, `store`, `evolve`, `flow`, `export abi`, `comptime`, `linear`, `deterministic`, `par for` → `E-X1-NOTYET-<KW>` (not Dc: they are D constructs not built yet) |
| `format` items with `f16` fields and `nibbles<N, offset = k>` (FF-Q4) | other storage codes (`e2m1`, `e8m0`) |
| scalars with Rust meaning; `f16` as storage with `.to_f32()`; arrays, slices (second-class), tuples, `Option`, `Result`, `Vec`, `String` (minimal) | Dc rows of 01 §2.5: FF-REF, FF-LOCAL, FF-DYN, FF-ASYNC, FF-CELL, FF-UNSAFE, FF-F16 arithmetic, and FF-SUM, FF-TIES, FF-EXP, FF-POWI, FF-CLOCK in their grade contexts |
| closures and iterator adapters under the non-escaping kind (01 §5.4) | user macros (`E-MACRO`), `dyn`; the file-inclusion and environment macros `include!`, `include_bytes!`, `include_str!`, `env!`, `option_env!` and `#[path]` (`E-X1-NOTYET`; the static gate's Mithril side, §11.4) |
| `uses { … }` rows on public functions, with containment checking; `policy fn` forbids `time`, `io`, `spawn` | — |
| `requires` clauses checked at run time (trap on violation) | `ensures` and `invariant` proofs (T2 is not part of X1) |
| traps: overflow (every build), bounds, division by zero, `unwrap` on `None`, `todo!` | unwinding (`catch_unwind` is Dc) |
| `std_platform`: `Mutex<T>::with_lock`, `Condvar`, scoped threads, `SlabBuf<N>`, `Hint<T>` | `Frozen<T>`, pools, I/O capabilities |
| std `canon` helpers: `sum16`, `dot16`, `sum_seq`, `nan`; `canon_v1::expf`; `round_ties_even`; `topk(k, Ties::LowerIndex, Nan::Last)`, each with a Rust and C11 equivalent in the helper packs (§5.1a) | `cr::` (not needed by X1 items [G]); the whole-task canon helpers `canon::act_q8`, `matvec_q`, `rmsnorm`, `softmax`, `silu`, `sigmoid`, `rope`, `combine_rank` → `E-X1-NOTYET-CANON` (they would solve a task family outright, and no other arm has them) |

### 9.2 Architecture and size estimate

| Module | Lines [inference] | Notes |
|---|---|---|
| lexer, recursive-descent parser mirroring the Lark grammar, CST → AST | ~1,200 | differentially fuzzed against the Lark grammar (§10.1) |
| name resolution, type checker (local inference, generics, static traits, Send/Sync) | ~1,800 | public signatures mandatory, so inference stays local (01 §4) |
| effect and grade checker; Dc and false-friend diagnostics | ~600 | grade context from `kernel fn`, `policy fn` and `#[grade]` |
| tree-walking interpreter over typed AST | ~1,200 | IEEE f32/f64 via Rust's own float ops (no contraction) |
| runtime: canon helpers, f16, `SlabBuf` virtual heap with real alignment, green threads with a seeded scheduler, `Mutex`, `Condvar` | ~700 | threads are deterministic per seed; permutation tests drive the seed |
| JSON diagnostics, hole report, CLI (`check`, `test`, `run`, `vectors`, `lift-check`, `--mutate`, `--token-map`, `--no-user-traits`) | ~500 | |
| **Total** | **~6,000** | at the top of ROADMAP's 4–6k-line range [inference, P5 §10.1]; the subset must be cut, not the checks, if it runs over |

Generics, traits, closures and threads in 6k lines is ambitious [G]. If the precondition date is at
risk, the first cut is `Condvar` (T-CTRL queue templates would then use polling under the mutex),
then const generics (`SlabBuf` fixed at 4096). Traits are not cut: DR-005 makes them an arm.

### 9.3 Freezing

The `mithi` binary hash (and source commit) is recorded in the pre-registration at freeze ("`mithi`'s
hash is frozen in the pre-registration", ROADMAP §3.2). Every checker call during the held-out run
records the hash it ran with; a mismatch voids the call and is an infrastructure failure (§13.3).

### 9.4 Diagnostics and hole report at X1

`mithi check --json` returns at most five root-cause groups (05 §5), each with a stable `E-…` code,
kind, expected and actual types, the false-friend row, prior and rule, and fixes with applicability
levels. It never uses rustc's numeric codes. For each `todo!("name")` it adds a hole entry in the
same shape as the kit's (§8.1): expected type, grade, in-scope bindings with types and modes,
relevant impls and false-friend rows. "Full grouped diagnostics arrive at M1" (05 §5); X1's are
deliberately basic.

### 9.5 The checker precondition (before any held-out run)

ROADMAP §3.2, verbatim: "`mithi` is judged before it judges agents, because its false rejections lower
VP@1 and its false accepts distort CABW:
- it accepts 100% of the hidden reference solutions for the Mithril arms;
- it rejects 100% of a planted corpus of Dc constructs and type errors (≥ 100 items [target]),
  written by a model family other than `mithi`'s author;
- it agrees with the core-calculus note's hand derivations on every canonical and derived snippet.
  The note's rules for the X1 subset are frozen at this point; a later change that would flip a
  verdict on an X1 item is recorded as an amendment and applies from M1."

Counting rules (precise, not looser):

| Part | Population | Pass condition | Run by |
|---|---|---|---|
| P-1 accept | every hidden reference for the Mithril, Mithril-without-traits (`refs/mithril_notraits/`, under `--no-user-traits`) and obfuscated arms, held-out candidates, calibration **and** iteration items | 100% accepted by `mithi check`; and each reference passes its own oracle under `mithi` (the reference agreement check, §6.1) | Gatekeeper job on a host where no agent session runs and no family-A session can read the material (§4.2, §4.6); only counts and codes leave it |
| P-2 reject, dev half | planted corpus dev half, ≥ 100 items [target] | may be iterated: failing item IDs and codes go to the `mithi` builder, each item only after it passes the §4.5 check against every hidden reference (§4.6). Rounds are logged | Gatekeeper |
| P-2 reject, confirmation half | a **separately sealed** half, ≥ 100 items [target], same coverage quota | run **once**, after the last `mithi` change; 100% rejected. If it misses, a new confirmation half is authored and the old one becomes dev. The expected primary code is recorded per item; a rejection under another code is logged as a diagnostic defect to fix before freeze, but it still counts as a rejection (ROADMAP asks for rejection) | Gatekeeper |
| P-2t twins (added here) | each planted item (both halves) ships a minimally edited **accepted twin** | 100% accepted, with the same dev/confirmation split. False rejections lower VP@1, which is the precondition's stated purpose, so the twins test the other side [target, proposed here] | Gatekeeper |
| P-3 agree | every canonical and derived snippet in the core-calculus note | `mithi`'s verdict (accept or reject, and the type for accepted expressions) equals the hand derivation, 100% | Gatekeeper + note author |

ROADMAP's "≥ 100 items" is met by the confirmation half alone; the dev half exists so that a 100% pass
is not obtained by fixing `mithi` against its own test set.

**The planted corpus.** Each half: at least 100 programs [target] of ≤ 60 lines each [G], written by
family B (or C) from the **Tier 0/1 card draft current at authoring** (the card freezes later, §16), the
false-friend table and the core-calculus note, **without access to `mithi`'s source**. Coverage quota
per half [G]: every Dc row of 01 §2.5 at least 4 times in varied syntactic positions (≥ 52 items for
the 13 Dc rows); ≥ 30 type errors (mismatch, missing impl, wrong arity, bound failure, move after use,
`&mut` aliasing, Send/Sync violation, const-generic mismatch, `format` misuse); ≥ 10 effect-row
violations (`io` in a `policy fn`, missing row on a public function); ≥ 8 X1-subset exclusions. Because
family B also wrote the held-out items, both halves stay **private until the verdict** (§4.6); after it
they may join `mithi`'s public regression suite once they pass the §4.5 check against every hidden
reference.

**When P-1 fails without revealing the item.** The Gatekeeper reports the item ID and the diagnostic
code to the Owner, not the source. Either the author family fixes its reference (when the reference
used a Dc construct; a dated re-commitment, §4.1), or the Owner writes a ≤ 20-line reproduction [G]
that does not reveal the item. The reproduction passes the §4.5 check against every hidden reference
before the `mithi` builder sees it, and stays out of the public repository until the verdict (§4.6).
The `mithi` builder never sees the hidden reference.

### 9.6 `mithi` change control after the precondition

After the precondition passes, `mithi` may change only to fix a bug as defined in §13.4(6), shown by a
witness. Card iteration will surface such bugs; it may not surface features. Every change re-runs
P-1, the P-2 confirmation half, P-2t and P-3 in full and re-records the binary hash and source commit
in the record (before freeze: in place; after freeze: as a dated amendment). A re-run of the
confirmation half tells the builder only "pass" or "miss"; a miss turns that half into dev material
and a new confirmation half must be authored and passed. **No change may widen the
X1 subset** (ROADMAP §3.2: "The note's rules for the X1 subset are frozen at this point"), so the
language cannot iterate toward the iteration items; only the card can.

---

## 10. Lark grammar v0, Tier 0 and Tier 1 cards

### 10.1 `grammar/mithril-x1.lark`

- Rules from 05 §3 restricted to the X1 subset: keyword-first items, explicit whitespace terminals,
  no `%ignore`, only `%import common`, about 150 rules [target, 05 §3], printable in ≤ 3k tokens
  [target, 05 §3].
- Validation: Lark's own parser (the `lark` Python package, version pinned) and `mithi`'s parser
  must agree on accept/reject for (a) every reference solution, card snippet and planted-corpus item,
  (b) 10^5 programs generated from the grammar [G], and (c) their single-token mutations [G]. Any
  disagreement is a bug in one of the two and blocks freeze.
- The grammar file is printed into Tier 1's *core* module.
- X1 does not use OpenAI's CFG tool or constrained decoding. Both are separate levers (05 §12, §18).

### 10.2 Tier 0 (≤ 8,192 bytes of ASCII) and Tier 1 (5–15k tokens)

Tier 0 follows 05 §2's block plan [target], with the X1 subset only:

| Block | Bytes [target, 05 §2] | X1 content |
|---|---|---|
| Identity and the subset rule | 700 | the rule, verbatim from 01 §2.1 |
| Rules | 900 | exact numerics in exact-graded code; `uses { }` on public functions; second-class references; `todo!` holes; traps |
| Keywords, effects, grades | 700 | X1 keywords only, each with its status; reserved keywords print as `not in X1` |
| False-friend table | 2,300 | every row of 01 §2.5, one line each, with the fix |
| Snippets | 2,500 | eight tiny snippets, **none inside a sealed family's solution space** (05 §2): e.g. an integer prefix sum as the `kernel` example, a prefetch-depth hint as the `policy fn` example |
| Reading `mithi` output | 1,000 | the JSON fields of §9.4; what a trap report means (X1 replaces the M1 verb list) |
| **Total** | **8,100** | ≤ 8,192 bytes |

- **CI budget check** (`cards/check_budget.py`, to be written): bytes ≤ 8,192; ASCII only; tokens ≤
  2.3k on each of two pinned tokenizers [target, 05 §2]. The candidates are `tiktoken`'s `o200k_base`
  and Anthropic's token-counting endpoint with a pinned model ID [inference; neither run here].
- **Tier 1** (05 §2): *core* (printed grammar, ownership and effect rules), *std* (X1 std
  signatures: canon, f16, `Mutex`, `SlabBuf`, `Hint`, `topk`, iterator methods), *kernels* (`format`,
  `kernel fn`, `policy fn`, exactness). 40–80 snippets [target, 05 §2]; 5–15k tokens in total
  [target, 05 §2]. At X1 both tiers sit in the system prompt (there is no `mithc guide` yet).
- **Atom isolation**: every atom passes the contamination check of §4.5 before it enters a card. The
  check is **blind**: editors learn only how many atoms were rejected per epoch (§4.5).
- **Iteration**: up to 3 epochs on the 20 iteration items only (ROADMAP §3.2), Mithril and
  Mithril-without-traits arms, both families, 5 attempts per cell (ROADMAP §10). Card editors see
  per-item outcomes and transcripts of iteration items only. Iteration templates are disjoint from
  calibration and held-out templates (§4.1). Card iteration is development: its data enter no
  decision.
- **Language or domain.** Before the freeze, every card atom is classified as *language* (syntax,
  keywords, Mithril's own rules and false-friend rows, how to read `mithi` output) or *domain* (any
  rule about the task domain that card editors learned during iteration, for example "start
  accumulators at +0.0", NaN and tie rules, check order in parsers). The Owner or a family-B reviewer
  classifies, and the classification is logged. **Domain atoms leave the Mithril card and go into the
  shared domain preamble**, which every arm carries in its system prompt (§7). This keeps lessons from
  iteration from reaching only the Mithril arms.
- **Semantic guard.** After the last epoch, a reviewer from family B or C (never A) reads the cards,
  helper cards and preamble against the private list of held-out templates and flags any atom that
  encodes a template-specific rule, which a lexical or AST check cannot see (prose such as "check
  length before magic"). A flagged atom is moved to the shared preamble (if it is a domain rule every
  arm should have) or removed; nothing is rewritten, and there is no further iteration after the guard.
  The flags go to the Owner and are logged.
- The cards, helper cards and preamble are then **frozen by hash**, before the record freezes and
  before the calibration run (§16).

### 10.3 The no-traits card

The frozen Tier 0 + Tier 1 card with every trait atom (trait declaration, impl, bound snippets) replaced
by one line: "User traits are not available in this arm: `trait`, `impl Trait for` and trait bounds on
your own generics are rejected (`E-TRAIT-OFF`). Std iterator methods and std derives still work." The
byte count is padded to equal the full card's, so card size is not a confound [G].

### 10.4 The obfuscated card and token map `obf-v1`

- A seeded bijection maps every reserved keyword and every primitive type name (`fn`, `let`, `mut`,
  `struct`, `impl`, `trait`, `for`, `in`, `if`, `else`, `match`, `return`, `kernel`, `policy`,
  `uses`, `requires`, `format`, `i32`, `f32`, `usize`, `bool`, …) to pronounceable 5–7-letter
  nonsense words. Candidates are drawn from a seeded generator and rejected if they appear in an
  English word list, in any keyword list of the 20 most used programming languages, or as a Rust or C
  std identifier [G].
- **Keyword-like prelude names are mapped too** (provisional; record Owner question 19): `todo!`,
  `Some`, `None`, `Ok`, `Err`, `Option`, `Result` and `Vec`, which act as keywords in practice. Other
  std library item names (`sum16`, `Mutex`, `iter`) are **not** mapped: ROADMAP specifies renamed
  keywords. Punctuation is unchanged.
- **No language name.** The obfuscated card, the obfuscated arm's brief and its diagnostic templates
  carry no base-language name: in the identity rule, the false-friend rows and every diagnostic's
  `prior` field, "Rust" and "C" are replaced by a neutral label ("a common prior"), and the false-friend
  table's Rust-form column is given in obfuscated spelling. A CI check asserts zero occurrences of
  `Rust`, `rustc`, `cargo`, `C11` and `clang` (case-insensitive, whole word) in those texts.
- `mithi --token-map obf-v1` substitutes before lexing, so semantics and diagnostics are identical;
  diagnostics are rendered back through the map and through the neutral-label templates.
- The card, the brief (so its primitive type names do not reveal the map), stubs, visible tests and
  references are transformed mechanically by the same map; the transformation is checked to
  round-trip. The brief carries the same information in every arm; only spellings differ.
- **De-obfuscation probe** (reported beside FG, not part of any decision): 20 fresh sessions per family
  [G] receive the obfuscated card alone and are asked which existing language it is based on; the share
  answering Rust is the fact `harness.x1.deobfuscation_probe`. FG is a lower bound on the familiarity
  gap, and the probe shows how much of the base language still shows through. Cost: negligible next to
  the attempt budget [G].

---

## 11. Execution sandbox

Agent-written code is untrusted. Isolation is not a parameter of the code under test (03 row 3).

### 11.1 Host

Provisional, pending D0-10 (execution host): a Linux host, either WSL2 Ubuntu on the desktop (daytime
only, never inside a quiet window, DR-023 and 06 §6.8, and under the family-A firewall of §4.6) or a
rented Linux VM. Linux is chosen for X1 because C11 `<threads.h>`, `aligned_alloc` and Clang's ASan,
UBSan and TSan are all available there [inference]. X4's Windows Job Object sandbox serves the Forge on
Windows and is not needed for X1. On any host that runs under DR-023's quiet-window rule, a
quiet-window preemption of an attempt is an infrastructure failure (§13.3).

### 11.2 Per-`check` sandbox

```text
podman run --rm --network=none --read-only --cap-drop=ALL --security-opt=no-new-privileges \
  --memory=4g --pids-limit=256 --cpus=2 --tmpfs /tmp:size=512m \
  -v <fresh copy of writable files + read-only task files>:/work \
  x1-toolchains@sha256:<pinned digest>  /x1/check <arm> [--tests]
```
- A fresh copy per call: no VCS history, no oracle files, no prior call's artifacts (03 row 30).
- **CPU-time limit** 180 CPU-seconds per call [G] (RLIMIT_CPU inside the container, cross-checked
  against cgroup `cpu.stat` accounting), with a wall-clock backstop of 540 s [G: 3×]; output truncated
  to 64 KB before it reaches the agent [G]. CPU time, not wall time, decides an agent-caused timeout,
  so host load cannot turn into a scored failure.
- **Admission control.** Concurrent sandboxes (check calls and oracle jobs together) ≤ physical cores
  / 2 [G] on the execution host; further calls queue, and queue time is logged and excluded from the
  attempt's wall budget (§7). Host load (1-minute load average and running sandboxes) is logged with
  every call. A wall-backstop timeout while the load average exceeds the physical core count [G] is an
  infrastructure failure (§13.3).
- **Sizing check at sealing**: the reference passes its visible tests under its own executor within
  10% of the per-call CPU limit [G], so `mithi`'s interpretation cost cannot push a correct Mithril
  solution's `check` into a timeout.
- **Same flags as the oracle**: `check` builds and runs with exactly the oracle's flags and sanitizers
  for the arm (§5.1, §7), and runs the static gate (§11.4).
- One image holds every toolchain: pinned stable Rust with vendored, offline std-only builds; pinned
  Clang; `mithi`; the kit; the per-language helper packs. The digest is recorded in the record.
- Every call's input snapshot (content hash of the workspace) and output are stored in the private
  store. That is what makes the re-scoring rule executable (§13.4).

### 11.3 Oracle: two stages, comparison outside

The earlier draft mounted the decrypted hidden bundle (expected outputs, references in four
languages, mutants, canary) into the same container that compiled and ran the agent's Rust or C file.
Rust code could then read it at run time with `std::fs` (no `unsafe` needed) or embed it at compile
time with `include_bytes!`; C code with `fopen` or `#include`. Mithril code, which has no I/O at X1,
could not, so the leak would have been asymmetric and would have landed on the kill comparator.
03 row 30 requires that "the hidden oracle runs out of process". The oracle is therefore split:

1. **Stage A, build.** A container with **no hidden mount** compiles the final artifact (rehashed by
   the harness from the attempt's last workspace state, which for a `submit()` ending is the submitted
   state; 03 row 31) together with the public driver, using the arm's pinned flags and sanitizers, and runs the static gate (§11.4). For Mithril
   arms, Stage A runs `mithi check` (the full check; any error fails the oracle).
2. **Stage B, run.** The built binary (or `mithi vectors` on the checked source) runs in a container
   with `--network=none`, `--read-only`, `--cap-drop=ALL`, no volume mounts except a tmpfs, and the
   input vectors and property drivers fed on stdin. Its rootfs contains the toolchain runtime and the
   binary only: **no hidden data exists in any container that runs agent code**, so no path, include
   or environment trick can reach it. Outputs and the nonce-terminated result record leave on a pipe.
3. **Compare, outside.** A Gatekeeper job, in a separate container with no agent code, holds the
   decrypted hidden bundle in tmpfs, compares outputs with `expected.x1v` and the property reference
   traces, parses sanitizer reports and timings, and writes the verdict JSON (per component:
   pass/fail, failing class, CPU time). Agents never see oracle output, and no oracle output re-enters
   any agent context, card or brief.

Held-out scoring runs only after collection has ended (§4.2). The same two-stage pipeline scores
iteration and calibration items, with their own split keys.

### 11.4 Static gate (defence in depth)

Applied to the writable files in `check`, in the acceptance check and in oracle Stage A; a hit is a
checker error in `check` (with a named code, so the agent can fix it) and an oracle fail. Legitimate
X1 solutions need none of these. The structural guarantee is §11.3; the gate makes the arms equal in
what they may attempt and makes attempts visible.

| Language | Rejected | How it is detected |
|---|---|---|
| Rust | `include_bytes!`, `include_str!`, `include!`, `#[path]`, `env!`, `option_env!`; paths into `std::fs`, `std::env`, `std::process`, `std::net`, `std::os`; `extern crate`; `asm!`/`global_asm!` | a `syn` pass that resolves `use` trees (grouped imports and renames included) and every path expression, plus macro-name matching; `unsafe` is already refused by `-F unsafe_code` |
| C11 | undefined symbols `fopen`, `freopen`, `open`, `openat`, `exec*`, `system`, `popen`, `dlopen`, `syscall`, `exit`, `_Exit`, `quick_exit`, `abort`, `atexit`, `at_quick_exit`, `signal`, `raise`, `setjmp`/`longjmp`; inline `asm`/`__asm__`; `#include` with an absolute or `..` path | `nm` on the object file for symbols; the Clang preprocessor's include list for paths; a lexical check for `asm` |
| Mithril arms | the same macros and attributes | `mithi` rejects them (`E-X1-NOTYET`, §9.1); X1 Mithril has no I/O effect |

Each route has a scorer canary that must score FAIL (§6.2).

---

## 12. Agent runner, logging and cost metering

### 12.1 Runner

- One attempt = one fresh session: system prompt (common harness instructions + the arm's card or
  helper card + the shared domain preamble) + the brief + the tool definitions. No memory across
  attempts.
- Native tool calling for API families. Model settings per family (model ID, sampling parameters,
  reasoning effort, maximum output per turn) are pinned in the record, **provisional, pending D0-10**.
- Budgets per attempt (§3.2, [G]): 8 `check` calls [target, ROADMAP], 60 turns, **600k cumulative
  non-prefix input tokens**, 60k output tokens, 45 minutes of wall time excluding sandbox queueing.
  - *Non-prefix input tokens*: for each call, every input token the provider reports (uncached, cache
    read and cache write alike) minus the token count of the arm's fixed system-prompt prefix, measured
    once per arm on the pinned tokenizer of that family. Without this, the Mithril arms' 7–17k-token
    cards [target, 05 §2], resent every turn, would exhaust a cumulative cap several turns earlier than
    Rust's: with history growing about 3k tokens per turn [G], cumulative input ≈ prefix·t + 1.5k·t², so
    a 600k cap is reached near turn 14.6 with a 19k prefix and turn 19.3 with a 2k prefix [D], 11–24%
    fewer turns for a 7–17k card [D].
  - Cost metering still counts every token (§12.3).
  - The calibration run reports the share of attempts ending `budget_tokens` per arm; above 5%
    [target] in either arm, `calibrate.py` doubles the cap once (record §6.3 step 7).
- Hitting a budget ends the attempt. It is a **fail** for VP@1 (record §4.8: only a `submit()` ending
  can be a verified pass); the last workspace is still stored and run through the oracle for the
  descriptive "unsubmitted oracle-pass" share.
- Provider errors (HTTP 5xx, timeouts, rate limits) are retried with backoff inside the turn. An
  attempt that cannot complete because of them is an infrastructure failure (§13.3).
- Concurrency: up to 16 sessions in parallel per family [G], bounded by rate limits.

### 12.2 Attempt record (one JSON object per attempt, append-only, hash-chained)

```json
{"schema":"x1-attempt/1","attempt_id":"...","prev_record_hash":"sha256:...",
 "item_commit":"sha256:...","item_id":"x1-...","split":"heldout","family_task":"T-ROUTE",
 "arm":"mithril","model_family":"A","model_id":"<pinned>","settings_hash":"sha256:...",
 "card_hash":"sha256:...","brief_hash":"sha256:...","toolchain_digest":"sha256:...","mithi_hash":"sha256:...",
 "harness_commit":"<git sha>","price_table_hash":"sha256:...",
 "start":"<UTC ISO-8601>","end":"...","turns":0,"checker_calls":0,
 "tool_calls":[{"t":1,"tool":"check","args_hash":"sha256:...","workspace_hash":"sha256:...","out_hash":"sha256:...",
                "verdict":"accept|reject|test_fail|timeout","codes":["E-FF-SUM"],"holes":1,"new_holes":1,
                "queue_s":0.0,"cpu_s":0.0,"host_load_1m":0.0,"static_gate":"pass|fail"}],
 "usage":{"input_tokens":0,"output_tokens":0,"cache_read_tokens":0,"cache_write_tokens":0,"reasoning_tokens":0,
          "prefix_tokens_per_call":0,"nonprefix_input_tokens":0},
 "cost_usd":0.0,"end_reason":"submit|abandon|budget_checker|budget_turns|budget_tokens|budget_wall|infra",
 "declared_done":true,"final_artifact_hash":"sha256:...","acceptance":"pass|fail",
 "oracle":{"verdict":"pass|fail","failed":["vectors"],"oracle_hash":"sha256:...","audit_verdict":"pass|fail|not_run"},
 "first_check_accept":true,"holes_written":0,"infra_failure":null,"rerun_of":null,"transcript_hash":"sha256:..."}
```

`holes` counts every `todo!(…)` in a checked workspace; `new_holes` counts those at an anchor not
present in the stub (matched by enclosing definition and anchor text). `holes_written` is 1 if any
call had `new_holes` ≥ 1, which is the record's hole-use rule (§4.15). For a budget or `abandon` ending,
`oracle.verdict` is recorded but never counts as a verified pass.

### 12.3 Cost metering

- **Tokens** come from the provider's usage fields per call: input, output, cache read, cache write
  and, where reported, reasoning tokens. **Dollars** = Σ tokens × the per-token prices of a price
  table pinned (with its date and source) in the record. Prices are never estimated after the fact.
- **Per arm and model family**: TPV = total tokens (input + output, cache reads included) / verified
  passes; turns/VP; $/VP; with item-cluster bootstrap 90% intervals. Medians per attempt are reported
  too.
- **Local pilot**: $0 of API cost; wall time and model throughput are logged instead.
- **Harness compute**: sandbox CPU-seconds per attempt are logged per arm, so `mithi`'s interpretation
  cost is visible.

---

## 13. Scoring and the `mithi` re-scoring rule

### 13.1 Definitions (frozen in the record)

- **Verified pass (VP)**: the attempt ended in `submit()` and the final artifact passes the hidden
  oracle. VP@1 is the share of attempts with a VP (05 §13: "final submission"). Attempts ending by a
  budget limit or `abandon` are fails; `abandon` on a solvable item counts as a fail. The share of
  budget-limit endings per arm is reported (record §5).
- **Accepted**: the agent called `submit()` **and** the final artifact passes the arm's own acceptance
  check, which the harness runs itself after submission (outside the budget): the arm's checker
  (rustc with `-F unsafe_code`; Clang with no errors, with the oracle's sanitizer build; `mithi check`;
  for the kit arm also zero `deny` lint findings), the static gate (§11.4), **zero remaining holes**
  (`todo!`/`unimplemented!`, or `X1_TODO()` in C) in writable files, and the visible tests, read from
  the nonce-terminated result record (§3.3). `mithi vectors` runs the full check first, so in the
  Mithril arms a checker-rejected program also fails the oracle.
- **CABW** (05 §13): among accepted attempts, the share the hidden oracle rejects. The
  unconditional rate (accepted-and-wrong over all attempts) is reported too.
- **First-compile rate**: the share of attempts whose first `check` call reports no checker errors
  (tests ignored).
- **Subset rejection rate** (05 §16; amber (c)): run every final Rust-arm held-out artifact that
  passed the oracle through `mithi lift-check` (a Rust-compatibility parse with Mithril's checks, no
  repair). An artifact is rejected if it carries ≥ 1 Dc diagnostic. Missing `uses` rows and grade
  annotations are D-construct requirements an auto-fix inserts, so they are not rejections. Std gaps
  (a Rust std API with no X1 mapping) are reported separately and are not rejections. The rate is
  pooled over both families.

### 13.2 Scorer

`analysis/score.py` (to be written; deterministic; frozen by commit hash in the record) joins attempt
records with oracle verdicts and produces the per-cell table `(item, arm, model family) → attempts,
passes, accepted, accepted-and-wrong, end reasons, tokens, turns, dollars`. `analysis/calibrate.py`
implements the record's §6.3 and outputs only the quantities listed there (never Δ̂, Γ̂ or any Mithril
aggregate). `analysis/analyze.py` computes the estimands and decision rules exactly as in the record's
§7. `analysis/verdict.py` maps them to an outcome row. None of them reads free text from a transcript.

**Blinding.** Until the pre-declared defect audit (§13.5) is complete, `score.py` writes per-artifact
verdicts keyed by opaque attempt IDs and nobody runs `analyze.py`; the people handling defect claims
see items and witnesses, not arm-level results. `analyze.py` runs once the audit's confirmed defects
are applied ("unblinding"); later discoveries are *post-data* (§13.4(7)).

### 13.3 Infrastructure failures

An attempt is an infrastructure failure only for a cause on a closed list: provider unavailable after
retries; sandbox or oracle container failure not caused by the submitted code (exit by the runtime,
host OOM outside the container limit, image pull failure); a harness exception; a `mithi` hash
mismatch (§9.3); a quiet-window preemption of an attempt on any host that runs under DR-023 (the
pilot host, and the desktop if it is the execution host); a wall-backstop timeout while the host's
load average exceeded its physical core count (§11.2). Infrastructure failures are re-run as fresh
attempts and not scored (05 §13). Model refusals, context overflows, agent-caused timeouts and crashes
of agent code are **not** infrastructure failures; they are scored. The infrastructure-failure rate per
arm is reported. "Infrastructure failures are re-run" does not cover a wrong checker verdict (ROADMAP
§3.2): that is §13.4's case.

### 13.4 The `mithi` re-scoring rule (ROADMAP §3.2, verbatim)

> "if a `mithi` bug is found after collection, the fixed `mithi` re-scores every final verdict.
> Attempts in which a reversed verdict occurred mid-loop are reported, and the analysis is run with
> and without them. If they exceed 5% of a Mithril arm's attempts [target], the held-out result is
> void and the run repeats on a fresh sealed batch, built as M1's is (§5). "Infrastructure failures
> are re-run" does not cover a wrong checker verdict."

How the harness executes it:
1. **What is re-scored.** For every attempt in the three Mithril arms: the acceptance check and the
   hidden oracle are re-run on the stored final artifact with the fixed `mithi` (the oracle executes
   Mithril code under `mithi`, so execution semantics are re-checked too).
2. **Mid-loop reversal.** Every stored `check` input snapshot is replayed through the fixed `mithi`.
   An attempt is *reversed* if any replayed call's verdict bit differs: accept vs reject, a visible
   test's pass vs fail, or a crash or timeout vs a normal result. Differences only in diagnostic text
   are reported but are not reversals.
3. **Counting.** Per Mithril arm: reversed attempts / all scored held-out attempts in that arm (both
   families). Bugs found later accumulate; an attempt counts once.
4. **Void.** If the share exceeds 5.0% [target] in any Mithril arm, the held-out result is void and
   the run repeats on a fresh sealed batch.
5. **Otherwise** the primary analysis uses all attempts with the re-scored final verdicts. The analysis
   without the reversed attempts is reported beside it; if the two give different verdicts, the
   difference is flagged to the Owner and the primary analysis stands.
6. **What counts as a bug.** A `mithi` verdict that contradicts the frozen core-calculus note, the
   frozen grammar, or the pinned Rust meaning of a C construct, demonstrated by a minimal witness
   program and **confirmed by an independent reviewer from family B or C** (a same-family,
   independent-context reviewer if none is available, logged as such) **and by the Owner**. The
   Owner, who has a stake in the outcome, never confirms alone. The claimant's knowledge of arm-level
   results at the time of the claim is logged.
7. **Symmetry guard.** The search effort for `mithi` bugs after collection is pre-declared and runs
   whatever the result, before unblinding (§13.5). Bugs found by any other targeted search after
   unblinding are flagged *post-data discovery*. ROADMAP's rule still applies them (re-scoring is
   mandatory), so the verdict is reported both with and without post-data discoveries, and a
   difference is an Owner referral (record §8). A verdict that disfavours Mithril must not buy extra
   bug-hunting that a favourable one would not [G].
8. **Voided estimates stay visible.** If the result is VOID (or UNDERPOWERED), Δ̂ and Γ̂ of the
   voided batch are still written to the ledger with status `voided` (record §7.6).

Oracle defects are different. If a hidden oracle is wrong, it is fixed and every final artifact in
every arm is re-scored. Trajectories need no re-run, because agents never saw the oracle (§1). A
defect in a *visible* test did shape trajectories, so the item is voided in every arm and reported.
Visible-test defects and oracle defects get the same symmetry guard as `mithi` bugs: they are searched
for by the pre-declared audit of §13.5 over every item; a claim is filed and confirmed item by item
**before** per-item arm results are revealed to the claimant; and confirmation needs the same
independent reviewer.

### 13.5 Pre-declared defect audit (before unblinding)

Run after collection and scoring, before `analyze.py`, with the same effort whatever the results:

1. **`mithi` differential fuzzing**: the budget fixed in the record (CPU-hours [G, set at freeze]),
   against the frozen note and grammar.
2. **Executor differential test**: every final Rust-arm and kit-arm held-out artifact that
   `mithi lift-check` accepts (it is then a valid X1-subset program with Rust meaning) is also run
   through `mithi vectors` with the same oracle, in both model families, and its verdict compared with
   the native Rust verdict. Any disagreement is a candidate `mithi` bug handled by §13.4. This tests
   `mithi`'s execution semantics on real agent code, on constructs the references never used.
3. **Audit oracle**: every oracle-passing final artifact in every arm runs against the item's sealed
   audit vectors (≥ 10× the scoring cases [G], another seed). A pass/fail disagreement with the scoring
   oracle is an oracle defect: the failing audit cases join the oracle and every arm is re-scored.
4. **Visible-test review**: a family B or C reviewer reads every visible test of the decision set
   against its brief, blind to results.

Confirmed findings are applied, the audit's report (counts per arm, every confirmed defect) is
published with the results, and then the results are unblinded.

---

## 14. Power and sample size (summary of the simulation)

Full method, inputs and tables: [power/x1_power_sim.py](power/x1_power_sim.py) and
[power/results/x1_power_tables.md](power/results/x1_power_tables.md) (seed 20261016; 2,000
replicates per configuration in blocks 1, 2 and 9, 1,000 in the side blocks, 4,000 in block 12 and
20,000 in block 13; numpy 2.5.4, Python 3.12.10). The first version's full run took 65.6–71.9 s across
two identical-output runs; the revised blocks were run separately (`--blocks … --merge`), each
invocation under about 30 s, 173 s in total [M, 2026-10-16, this track, shared laptop]. Re-running
blocks 1–8 reproduced every earlier number exactly except the two intended changes (block 4b's
coverage now uses df = template clusters − 8; the pilot rows' CABW columns follow the undefined-ratio
rule) [M, same run, compared key by key]. Every result below is **[S]**; every input is **[G]**.

**Model.** Each attempt ends accepted-and-correct, accepted-but-wrong or not accepted. Logit-normal
random effects: item difficulty, item × arm, item × model family, item × arm × model family;
task families as fixed strata; and, in a sensitivity block, templates shared by 2–3 items. Arm
intercepts are solved by quadrature so the population VP@1 and CABW hit their targets exactly.
The base case is Rust VP@1 0.50 and CABW 0.20 [G]. Four levels of the item × arm logit SD: 0.35,
0.70, 1.05, 1.40 [G] ("low" to "stress"), which imply probability-scale σ_ta of about 0.10–0.14,
0.18, 0.24 and 0.29–0.30 [S]. 05 §13 assumed 0.10–0.20.

**Decision statistic simulated.** The task-family-stratified, item-clustered mean difference of cell
pass rates (identity link), and the stratified ratio estimator for CABW; point-estimate kill rules at
15 and 5 points (the record's §7 explains why this, not the logistic GLMM, is the decision statistic).
The simulation's three states match the record's VP definition (only a `submit()` ending can pass;
budget endings are "not accepted") except for the state "submitted, not accepted, oracle passes",
which the record makes empty outside the kit arm and reports per arm.

**Requirements** (record §6.2): R-VP (ROADMAP's, verbatim), R-CABW (05 §13's analogue at **every**
true VP gap g ∈ {0, 5, 10, 15}, not only at 10) and R-JOINT (P(K1 ∨ K2) ≤ 0.10 at VP gap 5, CABW gap 0).

**Findings [S]:**
1. **The VP@1 rule is not the binding constraint.** At 60 items, P(kill) at a true 5-point gap is
   ≤ 0.012 and at 25 points ≥ 0.991, in every scenario. The gap estimate's SD is 2.7–4.5 points,
   against the 7.8 points that ROADMAP's requirement allows [D: 10 / 1.2816].
2. **The CABW co-primary is binding, worst at a VP gap of 15.** Under R-CABW and R-JOINT (block 9), the
   smallest multiples of 8 meeting every requirement on the point estimate are 64 (low), 72 (mid),
   **88 (high)** and **128 (stress)**. The binding point is almost always g = 15, where Mithril has the
   fewest accepted attempts. Under the earlier single-point requirement (g = 10 only, block 2) they were
   60, 64, 96 and 100 on the coarser grid.
3. **n = 96 holds at the planning scenario with Monte Carlo bounds.** At 20,000 replicates (block 13,
   the record's step-4 rule), the high scenario meets every requirement at 96: worst-case P(K2 | 0)
   0.0728 and P(K2 | 10) 0.9148 (both at g = 15), P(K1 ∨ K2 | 5, 0) 0.0640. At 2,000 replicates the
   minimum moves by a grid step between runs (96 fails the MC-bound rule there with 0.906), which is why
   the step-4 rule uses 20,000.
4. **Joint false-kill rate.** P(K1 ∨ K2) at (VP gap 5, CABW gap 0), n = 96: 0.015 / 0.042 / 0.059 /
   0.096 (low → stress, block 9); at a VP gap of 10, 0.030 / 0.064 / 0.097 / 0.150. At 60 items it
   reaches 0.141 (stress, block 1).
5. **Base rates matter most.** At a Rust VP@1 of 0.30, R-CABW fails at 128 items in the mid and high
   scenarios and is met at 160 only on the point estimate (high: 0.081 / 0.902; block 10), so such a
   base rate drives n to the cap. A Rust CABW of 0.35 is met at 96 (high 0.092 / 0.908).
6. **Templates matter.** If held-out items share templates (k = 2–3 items per template, half or more of
   the item-level variance at the template level), the high scenario misses the old CABW requirement at
   96 (0.879–0.885 at a true gap of 10) and needs about 120 (block 4b). With df = template clusters − 8,
   template-clustered 90% intervals cover 0.88–0.92 (VP@1) and 0.87–0.92 (CABW).
7. **Items beat attempts.** In the high scenario, 120 items × 5 attempts gives SDs of 2.6 (VP) and 2.9
   (CABW) points; 60 × 10 gives 3.5 and 3.7, for the same number of attempts.
8. **Attempts are not independent.** Naive SEs that treat attempts as independent give 90% intervals
   that cover only 0.68–0.92 of the time; the stratified cluster-robust SE covers 0.88–0.92.
9. **One-family referrals are common** (block 11, n = 96). With no model-family × arm interaction,
   P(no pooled kill but a per-family breach) is 0.11–0.18 at a pooled VP gap of 5–10; a ±0.5-logit
   interaction on the comparison arm's acceptance raises it to 0.53–0.57 at a gap of 10, ±1.0 to
   0.88–0.91, while the pooled kill rates stay at 0.033–0.103. Per-family SDs: 3.2–3.8 points (VP),
   3.6–4.5 (CABW), against 2.5–3.2 pooled.
10. **The calibration procedure is conservative** (block 12). With 24 calibration items, the upper-80%
    bounds reach the population dispersion in 0.78–0.80 (d_i) and 0.69–0.71 (e_i, skewed) of runs; the
    selected ladder level is at least the true one in 0.98 of runs, and in 1.000 / 1.000 / 0.981 (mid /
    high / stress) with the floor at "high".
11. **Realised CABW precision.** P(SE(Γ̂) > 3.90 points) at n = 96 is ≤ 0.001 (mid), 0.05–0.14 (high),
    0.35–0.56 (stress) (block 2): relevant to record Owner question 15.
12. **An undefined CABW ratio must not be imputed as 0.** In the pilot rows the CABW gap is undefined
    in 0.21–0.23 of replicates at a true VP gap of 20; imputing 0 had biased the mean CABW gap by −3.5
    to −4.9 points; with the record's rule the bias is −0.2 to +1.1 points (block 7, before/after).
13. **Amber (b) is close to its noise floor.** At 64 common items with 5 vs 3 attempts, P(fire) at a
    true cost of 0 is 0.074 (mid) and 0.101 (high).
14. **The local pilot is a plumbing check.** Its gap SD is 10–12 points; P(estimate > 15) is ≈ 0.09 at
    a true gap of 0 and ≈ 0.68 at 20.

**Plan carried into the pre-registration** (provisional, pending D0-10 budget approval):
**n_final = 96 held-out unflagged items** (12 per task family, at most one per template; the record's
floor), recomputed from the dedicated calibration run before collection within [96, 160] and only
ever growing (record §6.3); 5 attempts per cell for the three primary arms, 3 attempts on a stratified
64-item subset for the three secondary arms, both families: **4,032 held-out attempts** at 96 [D:
96·5·3·2 + 64·3·3·2], **5,952** at the cap of 160 [D]. Family B authors and seals 184 held-out
candidates (23 per family) so that any n_final up to 160 can be filled from a sealed, pre-committed
order (record §4.4).

---

## 15. The local Hearth-hosted pilot

ROADMAP §3.2: "One Hearth-hosted local model runs as a **pilot**: the Mithril and Rust arms on one task
family named in the pre-registration, about 10 held-out items × 3 attempts × 2 arms = 60 attempts. At
about 20 tok/s, with 5–10 minutes per agentic attempt, that is 5–10 hours of loaded 9950X time
[inference] … Local runs, like X2 fuzzing and builds, use daytime only and never overlap quiet-machine
windows (DR-023). The local pilot is reported, not part of the kill."

- **Family**: T-ROUTE, **provisional** [G]. It has short, self-contained units, small contexts, no
  threads or I/O, and a strong false-friend prior (FF-TIES, NaN handling), so a weaker local model has
  a chance of non-zero VP@1 in both arms and the arms can differ for the reason X1 studies.
- **Items**: 10 of the first 12 held-out T-ROUTE candidates in sealing order (always in the decision
  set unless dropped), chosen by a seeded draw at sealing. The pilot runs **after** the frontier
  held-out run has finished, so pilot behaviour cannot influence anything that carries the kill.
- **Firewall** (§4.6): the desktop also runs family-A Claude Code sessions, so the Owner's Claude
  settings deny rules are in force while the pilot runs; only the 10 items' visible bundles are
  decrypted, into tmpfs, and deleted afterwards; no hidden key is on the desktop until the pilot ends.
- **Model**: provisional, pending D0-10. A Qwen3-30B-A3B-class model is the natural candidate because
  Hearth already runs it: ~19 tok/s decode (measured, preliminary, cold cache, busy machine) [Hearth
  README].
- **Serving**: `hearth.server`, Hearth's OpenAI-compatible HTTP server [Hearth docs/PYTHON_API.md].
  Whether it supports native tool calls was not verified. If it does not, the runner uses a text tool
  protocol (tool calls as one JSON object per assistant message, parsed by the harness). That is a
  confound against the frontier families, and the report says so.
- **Context**: the card (Tier 0 ≈ 2k tokens [target] + Tier 1 5–15k tokens [target]) plus the brief
  must fit the local model's context window with room for the loop; the configured context length is
  recorded.
- **Scheduling**: daytime only. Before each attempt the runner checks the supervisor's quiet-window lock
  (06 §6.8); if a window opens, the attempt stops, is marked as an infrastructure preemption, and
  re-runs the next day. It is never co-scheduled with X3 or X4 measurement (DR-023). Expected load:
  5–10 machine hours [inference, ROADMAP §3.2].
- **Reporting**: VP@1, CABW (only where defined, §14 finding 12) and TPV per arm with item-cluster
  intervals, labelled as a pilot. Its precision is ±10–12 points SD [S, §14 finding 14], so it cannot
  detect gaps below roughly 25–30 points [D: about 2.5 × SD].

---

## 16. Build plan, schedule, cost and owner hours

Weeks follow ROADMAP §2's X1 lane; all dates are [inference].

| Week | Deliverable | Gate before the next step |
|---|---|---|
| 0–1 | grammar v0; Tier 0 draft; `mithi` parser + checker skeleton; kit spike (§8); harness runner, public drivers, static gate, two-stage oracle and sandbox image; public smoke set wired end to end; authoring scripts and the private authoring brief for family B (§4.6) | smoke set runs in all six arms; scorer canaries (wrong, correct-non-reference and gaming) all scored correctly |
| 0–2.5 | suite authoring by family B: **184 held-out candidates (23 per family) + 20 iteration + 24 calibration = 228 items** [D]; refs in all five languages (no-traits included); vectors and audit vectors; mutants (cross-arm class included); contamination and near-duplicate checks; independent family-B review of every item; **SEAL; `COMMITMENTS.json` committed in its own commit** | every sealed item meets §6.2; reference agreement passes; template disjointness asserted |
| 1–2.5 | planted corpus, dev and confirmation halves (family B or C); `mithi` complete for the X1 subset; Tier 1; helper packs and their agreement tests | — |
| 2.5–3 | **checker precondition** P-1, P-2 dev (iterable) then P-2 confirmation (once), P-2t, P-3; `mithi` hash recorded; kit acceptance suites (corpus by family B/C or the Owner) | all pass, else no held-out run |
| 2.5–4 | card iteration, ≤ 3 epochs, blind atom check; atom classification; semantic guard; cards, helper cards and preamble frozen by hash; **record FROZEN and SIGNED** (or Owner-instructed) with n_final open; Owner's post-freeze sample review of 24 held-out items; **calibration run** (480 attempts); `calibrate.py` → n_final amendment | Owner signature (D0-12) before the calibration run |
| 4–5 | held-out run, all arms, once; then the local pilot | no hidden key on any host while it runs |
| 5–6 | scoring after collection (two-stage oracle); pre-declared defect audit, blind; unblinding; analysis; independent review; verdict | M0 verdict (ROADMAP §3.7) |

The calibration run's 480 attempts and the post-freeze review fit inside the 2.5–4 window only if
card iteration ends by about week 3.5 [inference]; otherwise the held-out run slips by the
calibration run's duration.

**Cost** [inference unless stated]:

| Line | Attempts | API $ |
|---|---|---|
| Held-out (this plan) | 4,032 at n = 96; 5,952 at n = 160 [D] | $2.0–8.1k; $3.0–11.9k [D: × $0.5–2 per attempt, ROADMAP §10] |
| Card iteration (ROADMAP §10) | ≈ 1.2k | $0.6–2.4k |
| Calibration run (record §6.3): Rust and Mithril arms, frozen card, 24 dedicated calibration items × 5 attempts × 2 families | 480 [D: 24·5·2·2] | $0.2–1.0k [D] |
| Local pilot (ROADMAP §10) | 60 | $0; 5–10 machine h |
| Authoring and review (family B or C sessions): 228 items, two planted-corpus halves, independent item reviews, the semantic guard, the kit acceptance corpus, half of the scorer canaries | — | $1.8–5.4k [D from G: the first draft's $0.8–2.4k [G] for ≈ 134 items and one planted corpus, × ≈ 2.0 for 1.7× the items and a doubled planted corpus, plus $0.2–0.6k [G] for review sessions] |
| De-obfuscation probe (§10.4) | ≈ 40 short sessions [G] | negligible (< $0.1k [G]) |
| Tooling kit (ROADMAP §3.2) | — | $1–2k |
| **X1 total** | | **≈ $5.6–18.9k at n = 96; $6.6–22.7k at n = 160** [D: sum of lines] against ROADMAP's $7–15k [inference] |

The held-out line exceeds ROADMAP §10's $1.4–5.8k by $0.6–2.3k at n = 96 [D], because the item count
grows from 60 to 96 to power the CABW co-primary; the review's changes add authoring to the cap, the
calibration set and the second planted-corpus half. This is an Owner decision (D0-10; record Owner
questions 2, 18, 21). `mithi` and harness construction by Claude sessions is not priced here [unknown:
depends on the Owner's plan].

**Owner hours** (ROADMAP: ~55 h [inference]): kit ~10 h [ROADMAP]; item review ≈ 5.9 h [D from G:
iteration items 20 × ~8 min before the card freeze, plus a post-freeze sample of 24 held-out items ×
~8 min; independent family-B sessions review the rest]; card epochs ~9 h [G]; precondition triage,
including P-1 reproductions and two planted-corpus halves, ~6 h [G]; atom classification and the
rejected-atom list ~1 h [G]; record review and signature ~4 h [G]; defect-claim co-confirmation ~2 h
[G]; infrastructure debugging that needs content ~2 h [G]; verdict review ~3 h [G]; pilot ~2 h [G].
Total ≈ 45 h [D]. If the Owner instead reviews every held-out item after the card freeze (record Owner
question 17), item review becomes ≈ 13–21 h [D from G: 96–160 items × 8 min] plus the iteration items,
and the total ≈ 55–63 h [D].

**Machine time**: about 2 CPU-minutes of sandbox time per attempt [G] gives ≈ 190 CPU-hours for
≈ 5.7k API attempts at n = 96 [D: (4,032 + 1,200 + 480) × 2 min] and ≈ 254 CPU-hours at n = 160 [D:
(5,952 + 1,200 + 480) × 2 min], plus perhaps 10–30% [G] for the audit oracle and sanitizer builds in
`check`; that is ≈ 16–21 h of daytime on 12 desktop cores before the extra [D]. With admission control
at ≤ 6 concurrent 2-core sandboxes on 12 cores [D: 12 / 2], check calls may queue at peak concurrency;
queue time does not count against agents (§7). A rented Linux VM avoids competing with X2's daytime
fuzzing and needs no family-A firewall rules (record Owner question 11).

---

## 17. Rejected design options (tombstones)

In DECISIONS.md §4's format; triggers use the 06 §7.2 grammar. The facts they read are defined in the
record's §7.6. These are proposals for the Owner to admit; they are not ledger entries yet.

```text
tombstone x1_attempts_over_items {
    verdict: costlier                       // at equal attempt budgets, more attempts per item buy less precision than more items [S]
    scope:   { exp: x1, design: heldout_sizing, sigma_ta_within: 0.09..=0.30 }
    class:   V
    revisit_when: harness.x1.sigma_ta_within.ci_high <= 0.05
    evidence: [S] experiments/x1-harness/power/results/x1_power_tables.md block 5
    // survivor: m = 5 per primary cell; any growth goes to items
    // the trigger reads the upper 95% bound, not the point estimate: a moment estimate truncated at 0
    // is often 0 when binomial noise dominates, so a point-estimate trigger would fire on noise
}

tombstone x1_logistic_glmm_decision_statistic {
    verdict: unpredictable                  // random arm effects over ~96 items may be singular; conditional log-odds need standardising to points
    scope:   { exp: x1, role: kill_decision_statistic }
    class:   T
    revisit_when: harness.x1.glmm_converged == true && harness.x1.glmm_primary_abs_diff_points <= 0.5
    evidence: [G] docs/m0/prereg/X1-writability.md §7; 05 §13
    // survivor: the identifiable GLMM of record §7.3 is fitted and reported as the secondary model
}

tombstone x1_ci_bound_kill_rule {
    verdict: misleading                     // killing only when the lower bound exceeds 15 points would loosen DR-017's threshold
    scope:   { exp: x1, rule: vp1_kill }
    class:   F                              // under DR-017 as signed
    revisit_when: owner.decision(dr017_test_form) == lower_bound
    evidence: ROADMAP §3.2; 05 §13
}

tombstone x1_independent_attempt_power {
    verdict: misleading                     // ~1.5k attempts per arm assumes independent attempts; naive 90% CIs covered 0.68-0.92 [S]
    scope:   { exp: x1, analysis: standard_error }
    class:   V
    revisit_when: harness.x1.sigma_ta_within.ci_high <= 0.02
    evidence: [S] x1_power_tables.md block 1 (naive-SE cover)
}

tombstone x1_multi_variant_templates_heldout {
    verdict: misleading                     // k >= 2 items per template shrink the effective n; CABW OC missed at 96 items under high variance [S]
    scope:   { exp: x1, set: heldout, items_per_template: 2..=3 }
    class:   V
    revisit_when: harness.template_pairs.sigma_ta_share.ci_high <= 0.1
    evidence: [S] x1_power_tables.md block 4b
    // survivor: at most one held-out item per template; no template shared between splits; templates
    // may repeat within the iteration set only
    // the fact cannot come from X1 (one held-out item per template); it comes from a separately
    // pre-registered template-pair study (record §7.6) and reads `unknown` until then
}

tombstone x1_canary_in_agent_visible_brief {
    verdict: gameable                       // a fixed marker in what the agent reads lets an evaluation-aware model detect scoring
    scope:   { exp: x1, artifact: agent_visible }
    class:   V
    revisit_when: harness.eval_awareness_shift(canary_brief, plain_brief).ci_high <= 0.0
    evidence: [inference] 03 §10 row 34
    // survivor: canary in hidden files only
    // the fact is produced by the 03 row 34 shadow-run comparison, which X1 does not run (record §7.6);
    // it reads `unknown` until a later record pre-registers that comparison
}

tombstone x1_agent_code_beside_hidden_data {
    verdict: gameable                       // Rust and C code can read or embed a hidden bundle mounted where it runs, or exit(0) before a test verdict; X1 Mithril cannot, so the leak lands on the kill comparator
    scope:   { exp: x1, stage: [oracle, acceptance, check], includes: [hidden_mount_beside_agent_code, exit_status_verdicts, forbid_attribute_in_writable_file, single_archive_suite] }
    class:   V
    revisit_when: harness.x1.arms_with_ambient_authority == 0
    evidence: [inference] 03 §10 row 30; record §12 (reviewer 2, findings 1 and 8)
    // survivor: per-item visible and hidden bundles under separate keys; two-stage oracle with no hidden
    // data where agent code runs; nonce-terminated result records; -F unsafe_code set by the harness;
    // static gate (§3.3, §4.2, §11.3, §11.4)
}

tombstone x1_calibration_on_iteration_items {
    verdict: misleading                     // the card is tuned on them for up to 3 epochs, so Mithril VP@1 is biased up and the Rust-minus-Mithril dispersion down, the direction that stops n from growing; their templates may repeat
    scope:   { exp: x1, step: n_recomputation, source: iteration_items }
    class:   V
    revisit_when: owner.decision(x1_calibration_source) == iteration_items
    evidence: [inference] record §6.3; record §12 (reviewer 1, finding 1; reviewer 2, finding 13)
    // survivor: a dedicated, sealed 24-item calibration set, run once after the card freezes, whose
    // script outputs only bounds, Rust base rates and end-reason shares
}
```

Every fact these triggers read is defined in the record's §7.6 with a unit and a producer. Two were
added in the revision: `harness.x1.arms_with_ambient_authority`, the number of arms whose language,
as run by the harness and before the static gate, can read files, read the environment or exit the
process from agent code (3 at X1 [D: Rust, C11, Rust + tooling]; producer: the harness configuration
at freeze); and `owner.decision(x1_calibration_source)`, the Owner's answer to the record's Owner
question 18 (`dedicated_set` or `iteration_items`). Facts that X1 does not produce
(`harness.template_pairs.…`, `harness.eval_awareness_shift(…)`) read `unknown`, which never fires but
is reported (06 §7.2).

---

## 18. Open issues and what is unverified

- **No tool named here was run in this session**: rust-analyzer's LSP behaviour, the rustc E0308
  probe, `dylint`, `cargo-mutants`, Mull, `age`, `podman`, Lark, `tiktoken`, Anthropic's token-counting
  endpoint and `hearth.server` tool calling are all [inference] or [not verified]. The week-1 spikes
  exist to verify them; each has acceptance tests above.
- **`mithi` at ~6k lines** with traits, generics, closures and green threads is at the top of the
  [inference] range; §9.2 lists the cut order.
- **The power simulation's inputs are judgments.** The dedicated calibration run (record §6.3)
  replaces the variance inputs with conservative estimates before collection. The simulation is not
  validated against a real GLMM fit (no R or statsmodels was used); the logistic GLMM's own operating
  characteristics are unknown. The card-tuning bias that made iteration items unusable for calibration
  is not modelled; it is avoided by design, not measured.
- **Effective sample size depends on templates.** "At most one held-out item per template", with
  disjoint templates across splits, means up to 184 distinct held-out templates plus 44 others: an
  authoring cost the Owner must accept, or the plan moves to 120 items with ≤ 2 per template. The
  near-duplicate thresholds (0.5 / 0.6) are [G]; the within-family similarity distribution reported at
  sealing is the evidence for or against them.
- **The Rust + tooling arm's `exact.toml`** gives that arm grade information that plain Rust lacks.
  That is intended (it is "the Mithril arm's tooling"), but it means (Rust + tooling) − Rust measures
  the kit *and* the grade sidecar together.
- **Obfuscation scope.** Keywords, primitive types and the keyword-like prelude names are mapped and
  language names are removed (§10.4, provisional). Other std names stay, so FG remains a lower bound on
  the familiarity gap; the de-obfuscation probe shows how much still shows through.
- **Isolation rests on structure, not on the static gate.** The two-stage oracle keeps hidden data
  out of every container that runs agent code; the static gate is a lexical and symbol-level heuristic
  (it can miss obfuscated routes) and serves as defence in depth and as a visible signal. seccomp-bpf
  cannot filter `open` by path [inference]; no path filtering is relied on.
- **The family-A firewall depends on the Owner's configuration** (Claude settings deny rules, key
  placement, the execution host). The harness can check and log the deny rules' presence; it cannot
  enforce them. A rented VM removes the dependency.
- **`f32::round_ties_even`** is assumed stable in the pinned Rust release [inference, not verified
  against a release here]; if not, the Rust helper pack supplies it.
- **Helper parity for `topk`** changes what T-ROUTE measures: every arm may call it, so T-ROUTE
  templates must include selection rules one call does not solve (§5.1). The alternative (removing
  `topk` from the X1 std) is record Owner question 20.
- **The step-4 recomputation at 20,000 replicates** takes about 15 s per candidate n on the shared
  laptop [M, 2026-10-16, block 13: 9 points at n = 96 in 15.3 s]; a recomputation that scans 96–160 for
  two base-rate sets is a few minutes, not run during the benchmark window.

---

## 19. Review response (2026-10-16)

Two independent reviewers, both Claude (same family as the author; independent context), reviewed the
first draft of this file, the record and the simulation. The review log, with counts, the
sub-proposals not adopted and their reasons, is the record's §12. Every finding was accepted; this
table maps each to where it changed the design.

| Finding | Severity | Changed here | Changed in the record |
|---|---|---|---|
| R1-1 calibration on card-tuned iteration items | major | §1, §16, §17 (`x1_calibration_on_iteration_items`) | §6.1, §6.3 (dedicated 24-item set; exact step 2), §4.18 |
| R1-2 n can grow to 160 without items to fill it | major | §4.1, §14, §16 | §4.4 (184 candidates, sealed order), §6.1 |
| R1-3 VP counted without `submit()` | major | §12.1, §12.2, §13.1; simulator docstring | §4.8, §5 |
| R1-4 CABW OC at one nuisance point; joint rate | major | §14; simulator blocks 9, 13 | §6.2 (R-CABW over g, R-JOINT), §6.3 step 4, §7.5 |
| R1-5 CABW not a mixed model; no realised check; undefined ratio | major | §14 finding 12; simulator rule | §6.5, §7.2, §7.3, §7.6, Owner questions 5, 15 |
| R1-6 secondary GLMM not identifiable | minor | §17 | §7.3 |
| R1-7 no model-family × arm interaction; "cancels" claim | minor | §2; simulator block 11 | §6.2, §7.7, §9 |
| R1-8 triggers on noisy point estimates; untestable fact | minor | §17 | §7.6 |
| R1-9 Monte Carlo error in the n rule; stress inconsistency | minor | §14 | §6.2, §6.3 step 4 |
| R1-10 author-declared templates; template df | minor | §4.5; simulator `summarise` | §4.3 |
| R1-11 GLS = OLS claim and unequal cells | minor | — | §7.3 |
| R1-12 interval levels | minor | — | §7.5, §7.6, Owner question 16 |
| R2-1 agent code beside hidden data; one archive | blocker | §1, §3.1, §3.3, §4.2, §11.3, §11.4, §17 | §4.17, §9 |
| R2-2 helper and card asymmetry (`topk`, formats, no Rust/C card, domain atoms) | major | §5.1, §5.1a, §7, §7.1, §9.1, §10.2 | §3, §9, Owner question 20 |
| R2-3 iteration/held-out template overlap; semantic tuning; public knobs; membership oracle | major | §2, §4.1, §4.5, §5.1, §10.2 | §4.3, §9 |
| R2-4 the Owner as a channel from held-out items into the card | major | §2, §16 | §10.9, Owner question 17 |
| R2-5 leakage into family-A contexts | major | §4.3, §4.6, §9.5, §15 | §9, Owner question 11 |
| R2-6 P-2 passed by iterating; `mithi` changes after the precondition | major | §9.5, §9.6 | §10.10, Owner question 21 |
| R2-7 token budget binds unequally | major | §3.2, §12.1, §12.2 | §4.12, §6.3 step 7 |
| R2-8 exit-code gaming; deletable `forbid` | major | §3.3, §5.1, §5.2, §6.1, §11.4 | §4.9, §4.17 |
| R2-9 asymmetric post-data defect hunting; voided estimates | major | §13.2, §13.4, §13.5 | §8, §10.2, §10.4 |
| R2-10 executor and oracle coverage of other arms' errors | major | §6.1, §6.2, §13.5 | §9 |
| R2-11 obfuscated arm names its base language | major | §10.4 | §9, Owner question 19 |
| R2-12 kit not a demonstrably fair floor | major | §2, §8.1, §8.2 | §9 |
| R2-13 calibration not blinded; freeze order | major | §1, §13.2, §16 | §6.3, §10.8 |
| R2-14 commitments published late | minor | §4.1 | §2, §10.9 |
| R2-15 contamination check under-specified | minor | §4.5 | §2 |
| R2-16 no no-traits reference | minor | §3.1, §6.1, §9.5 | §4.8 |
| R2-17 infrastructure confounds | minor | §11.1, §11.2, §13.3 | §9 |
| R2-18 check/oracle parity; holes; `mithi vectors` | minor | §3.3, §5.1, §7, §13.1 | §4.9 |
| R2-19 weak scorer canaries | minor | §6.2 | — |
| R2-20 tombstone facts undefined | minor | §17 | §7.6 |
