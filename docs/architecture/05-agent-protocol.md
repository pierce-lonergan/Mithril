# 05 — Agent protocol and the comprehension harness

*Detailed architecture document, 2026-10-11. Audience: AI agents and the project owner. Parent:
[ARCHITECTURE.md §10](../ARCHITECTURE.md#10-the-agent-protocol). Decisions are cited as DR-xxx
([DECISIONS.md](../DECISIONS.md)), dossiers as [R03], [G01] or [RV: node], proposals as [P1 §n].*

**Summary.** This document specifies how an AI agent reads, writes, checks and hands over work in
Mithril (layer L1), and how the Harness measures it. The surface stays Rust-shaped under the subset
rule (DR-002), so the agent-facing value lives in the toolchain:
- a tiered reference card with CI-enforced budgets, and one Lark grammar;
- JSON diagnostics grouped by root cause, whose fixes list the evidence they invalidate;
- Rust-coincident typed holes (`todo!("name")`, DR-003);
- a hash-anchored, atomic edit-plus-check, sent in a flat envelope that Claude accepts;
- budgeted context packs, `propagate`, and handovers derived from the toolchain journal.

The comprehension harness gives every lever an ablation and a kill criterion. It uses sealed
Hearth-shaped tasks, six arms (five comparison arms plus the traits ablation, DR-005), VP@1 and CABW,
and a task-clustered mixed-effects analysis.
It gates the standalone surface (DR-017), runs the Surface Lab and a Mithril MultiPL-E, and measures
how much agent-written Rust the subset rejects. Constrained decoding on Hearth-hosted models is
deferred by trigger (DR-023).

**Contents**
1. [Scope, conventions and the agent loop](#1-scope-conventions-and-the-agent-loop)
2. [Reference cards and budgets](#2-reference-cards-and-budgets)
3. [The Lark grammar](#3-the-lark-grammar)
4. [The false-friend table](#4-the-false-friend-table)
5. [Diagnostics](#5-diagnostics)
6. [Typed holes and type search](#6-typed-holes-and-type-search)
7. [The edit protocol](#7-the-edit-protocol)
8. [Context packs and closure budgets](#8-context-packs-and-closure-budgets)
9. [`propagate`](#9-propagate)
10. [Session state: journal, handover, resume, friction, abandon](#10-session-state-journal-handover-resume-friction-abandon)
11. [The tool surface: verbs, envelope, `next`, CLI/MCP/LSP/SARIF](#11-the-tool-surface-verbs-envelope-next-climcplspsarif)
12. [Constrained decoding (deferred)](#12-constrained-decoding-deferred)
13. [The comprehension harness](#13-the-comprehension-harness)
14. [The Surface Lab and the Surface Map](#14-the-surface-lab-and-the-surface-map)
15. [Mithril MultiPL-E](#15-mithril-multipl-e)
16. [Measuring the subset's rejection rate of idiomatic agent Rust](#16-measuring-the-subsets-rejection-rate-of-idiomatic-agent-rust)
17. [The C/Rust lifter](#17-the-crust-lifter)
18. [Lever register: ablations and kill criteria](#18-lever-register-ablations-and-kill-criteria)
19. [Open questions and reviewer notes](#19-open-questions-and-reviewer-notes)

---

## 1. Scope, conventions and the agent loop

**Scope.** This document owns L1 and the Harness. It does not restate what the sibling documents own:
- the core calculus, the non-escaping kind, traps and fail domains: [01-language](01-language.md);
- claim kinds, grades, roles, the Gatekeeper and the threat model: [03-trust](03-trust.md);
- content hashes, the Fact Plane and latency budgets: [04-toolchain](04-toolchain.md);
- the F1-A Forge level and quiet windows: [06-forge](06-forge.md);
- stage gates: [07-hearth-port](07-hearth-port.md).

**Conventions.**
- All syntax is provisional pending the Surface Lab (§14).
- Status labels follow [ROADMAP §1](../ROADMAP.md), rule 7:
  - **v0**: in the mithc that ports Hearth (M1–M5);
  - **v1**: present by Edition 1 (M6–M7);
  - **later**: planned after M7;
  - **reserved**: in the types and schema but not producible;
  - **by-trigger**: added only when its register trigger fires.
  Milestone numbers are added where they help.
- Numbers are labelled measured, simulated, [inference] or [target]. A [target] is a gate value
  proposed here, not a result.

**Design rules for L1.**
1. **Text is the interface; hashes are the identity.** Code wrapped in JSON lowers model quality
   [R03], [RV: S3], so code travels as a string payload.
2. **The checker judges.** Agents overrate their own work (self-estimated chess Elo 200–1,100 points
   too high [G01]), so session facts come from the toolchain.
3. **One root cause, one fix, one turn.** After one failed edit, SWE-agent's eventual success fell
   from 90.5% to 57.2%. Grouping errors took GPT-3.5 from 4.97% to 44.76% fixed (measured) [R03].
4. **Budgets are code**, checked in CI against pinned tokenizers.
5. **Every lever can lose** (§18), including the agent-value claims made for mandatory `uses` rows,
   the ledger, spec escrow, cost reports and `Quantity` (N3, N5, N7 in
   [ARCHITECTURE §1](../ARCHITECTURE.md)).
6. **Observed text is data.** Code, comments, rationale and quoted diagnostics travel in typed
   `quoted` fields. They never enter instruction text or `next` ([03-trust](03-trust.md)).

```text
 agent session (one role token)          Tier 0 in AGENTS.md + project card (always on)
        |  flat JSON ops, code as strings
        v
 mithc   CLI --json | MCP (mithc mcp) | LSP (by-trigger)  ---- SARIF 2.1.0 ---> CI / humans
        |  edit = parse + format + check, atomic; every response ends with next: [...]
        v
 store: canonical .mith text + mith.lock      journal: hash-chained, written by mithc only
        |                                              |
        +------> ledger (.mith/ledger, gate-signed) <--+-- Gatekeeper admits evidence
                                                       |
 Harness (Gatekeeper-owned): sealed suites, hidden oracles, arms, Surface Lab, MultiPL-E
```

**The loop and its response budgets.**

| Step | Verb | Budget [target] | Lever (evidence) |
|---|---|---|---|
| Orient | `mithc resume <manifest>` or `mithc pack <def> --budget 6000` | Tier 0 (≈2k tokens) + project card (≈1k) + pack (≤ 6k) | always-on index: 53% → 100%, measured [G01] |
| Skeleton | signatures with `todo!("…")` bodies; `mithc check --json` | ≤ 1.5k (top 5 groups) | holes: ~10× for StarCoder2-15B with type context [R03] |
| Fill | `mithc hole <name>`, then `mithc edit` | ≤ 1.5k | expected type and bindings are the most useful context [R03] |
| Repair | `mithc edit`, `mithc fix --safe` | ≤ 1.5k | grouping 4.97% → 44.76% [R03] |
| Verify | `mithc check --tests [--mutate]`, `mithc prove`, `mithc ledger why` | ≤ 1k + counterexamples | vericoding union rates (other tools): Dafny 82%, Verus 44% (the Rust-shaped analogue), Lean 27% [R03]; not Mithril's expected rate (DR-012) |
| Measure | `mithc bench <def> --vs <baseline>` (a request; the gate measures) | ≤ 0.5k | runtime-owned clock ([03-trust](03-trust.md)) |
| Hand over | `mithc handover` or `mithc abandon` | derived from journal and ledger | closes DGM's log-faking class [R01] |

**Three regimes share one grammar and one compiler** [R03]:
- **Claude** accepts only JSON Schema, without recursion or length constraints. Its hard constraint
  is the flat edit envelope (§7).
- **OpenAI** accepts restricted Lark CFGs, which `mithril.lark` fits (§3).
- **A Hearth-hosted model** exposes its logits, which allows masks (§12, by-trigger).

---

## 2. Reference cards and budgets

Docs help only when compact and always present. Vercel's 8 KB AGENTS.md index scored 100%, against
53% for an on-demand skill that went uninvoked in 56% of runs. On SkillsBench, "comprehensive" docs
added 0.7 points, and self-generated skills scored 8–12 points *below* no skill [G01].

**Tier 0 (v0, drafted for X1): at most 8,192 bytes of ASCII, always in context, embedded in
AGENTS.md, not a skill.** CI rejects an over-budget card and checks the token count on two pinned
tokenizers (≤ 2.3k each [target]) [P1 §7.2].

| Block | Bytes [target] | Content |
|---|---|---|
| Identity and the subset rule | 700 | "If it parses as Rust it means Rust; otherwise it is rejected with a named diagnostic, or it uses a new keyword." |
| Rules | 900 | exact numerics in exact-graded code; `uses { }` on public functions; second-class references except projections; `todo!` holes; anchors, not lines; evidence policy; `abandon` and the friction rule |
| Keywords, effects, grades | 700 | `kernel format schedule policy spec claim uses deterministic par linear requires ensures invariant`, plus `comptime` (v0), `export abi` (v0, M1), `store`, `hint port` and `certificate` ([02-compute §12.3](02-compute.md)) and `evolve slot` ([06-forge §2.1](06-forge.md)) (v0, M4), and `flow` (v0, M4–M5; [02-compute §12.1](02-compute.md)); every keyword is contextual ([01-language §2.4](01-language.md)), and the card prints each added one with its status; effects `io spawn alloc(A) time foreign unsafe fp_env compile lossy nondet nondet(platform) blob`; fidelity and determinism scope |
| False-friend table | 2,300 | the rows of [01-language §2.5](01-language.md), one line each, with the fix (§4) |
| Snippets | 2,500 | eight tiny ones, each drawn from outside every sealed family's solution space (§13, contamination rule): fn with `uses`; a hole; `requires`/`ensures`; `format`; `kernel` + `schedule`; `policy fn`; `deterministic(by: …)`; `Quantity` |
| Loop, verbs, JSON glossary | 1,000 | §1's loop in eight lines; envelope field names |

The blocks total 8,100 bytes.

The snippets teach constructs, not tasks. A `kernel` + `schedule` example therefore uses an operation
no sealed family covers (an integer prefix sum, say), never a Q4 dot or matvec. The `policy fn`
example is a non-eviction hint (a prefetch depth, say), and the `format` example is a record no
T-FMT variant parses. For the same reason, the canonical snippets of
[ARCHITECTURE §5.3](../ARCHITECTURE.md#53-canonical-snippets) (`q4_row_dot`, `q4_matvec`,
`pick_victim`) are not card atoms: they are T-Q4- and T-EVICT-shaped.

**Project card (v0): at most 4,096 bytes, always on**, counted separately (always-on total ≤ 12 KB
[P1 §7.2]). It holds ownership, commands, evidence policies and invariants. Hearth forbids
paraphrasing invariants (`hearth/governance/README.md`). Its `INVARIANTS.md` is 3,438 bytes
(measured), so the card carries it verbatim. If it outgrows the budget, the card keeps IDs and text
hashes, and `mithc guide project` serves the verbatim text, never a summary.

**Tier 1 (v0, complete by M1): three modules, 5–15k tokens in total**, via
`mithc guide core|std|kernels`:
- *core*: the printed grammar (≤ 3k tokens) and the ownership and effect rules;
- *std*: signatures, the numerics (`canon`, `cr`, `canon_v1`) and `std_platform`;
- *kernels*: `format`, `kernel`, `schedule`, `policy fn`, specs and evidence.

Together they hold 40–80 snippets and the error index. The Tier 1 snippets obey the same
contamination rule as Tier 0's (§13). For comparison, Mojo's correction skill is about 3.5–4k words
and MoonBit's guide about 9k [G01].

**Tier 2 (v1, M7): retrieved.** It holds the normative core (≤ 30k words) and its machine-readable
form: grammar, error catalogue, Surface Map and std signatures as data.

**Governance.**
- Maintainers curate the cards. Card atoms (a rule, a snippet, a row) are content-addressed, so the
  harness can attribute effects to them.
- Every card edit runs the screening subset; editions run the full suite (§13).
- Each epoch, leave-one-atom-out ("guessability pruning" [RV: D2-D]) runs on the screening items
  only, never on the held-out set, which stays untouched until the card freezes (§13). One atom of
  50–300 bytes has an effect far below what n can detect, so "no detected change" is not evidence of
  no effect. An atom is deleted only when its removal is shown non-inferior within a pre-registered
  margin: the upper 90% bound of the VP@1 loss ≤ 2 points and of the TPV increase ≤ 5% [target], or
  the posterior lies inside an equivalent ROPE on epochs pooled by a Bayesian model. Otherwise the
  atom stays, flagged *unproven*. When the byte budget forces a choice, unproven atoms leave in
  ascending order of posterior effect per byte.
- A construct that needs more than one snippet and one false-friend line must justify itself in the
  harness [G01].
- F1-A may propose atom edits as GEPA-style reflective deltas [R04]. Only maintainers promote them
  ([06-forge](06-forge.md)). Every proposed atom, from F1-A or a maintainer, first passes §13's
  contamination check. A delta that fails it is rejected unscored, and the reflection prompt states
  the rule, so the search cannot learn to put task-shaped examples into the card.

---

## 3. The Lark grammar

**Status: v0 (X1).** One normative file, `mithril.lark`, defines the surface.
- **Keyword-first.** Every item opens with a distinctive token, a per-line identity signal against
  language confusion [R03].
- **LL-friendly.** Prefix parsing is incremental, which LSP and masks need.
- **Fits OpenAI's CFG tools.** It uses explicit whitespace terminals, no `%ignore` and only
  `%import common` [R03].
- **Budget.** About 150 rules, printable in ≤ 3k tokens [target].

An illustrative excerpt:

```lark
// status: abi_item v0 (M1); comptime_blk v0; store_item, evolve_item v0 (M4); flow_item v0 (M4-M5)
item      : attr* vis? (fn_item | flow_item | struct_item | enum_item | format_item | spec_item
                       | schedule_item | store_item | evolve_item | abi_item | trait_item
                       | impl_item | use_item | mod_item)
fn_item   : (fn_kind _WS)? "fn" _WS NAME generics? params ret? effects? contract* block
fn_kind   : "kernel" | "policy"
flow_item : "flow" _WS NAME generics? params ret? effects? contract* block
store_item  : "store" _WS NAME _WS? "{" (_WS? store_clause)* _WS? "}"
store_clause: ("hint" _WS "port" | "certificate") _WS clause_body _WS? ";"
evolve_item : "evolve" _WS "slot" _WS NAME _WS slot_head _WS? slot_body
slot_head : "for" _WS path _WS "in" _WS "space" _WS NAME
abi_item  : "export" _WS "abi" _WS abi_body
effects   : _WS "uses" _WS? "{" _WS? (effect (_WS? "," _WS? effect)*)? _WS? "}"
effect    : NAME (_WS? "(" _WS? NAME _WS? ")")?
contract  : _WS ("requires" | "ensures" | "invariant") _WS expr
par_for   : "par" _WS "for" _WS pattern _WS "in" _WS expr _WS? block
det_block : "deterministic" _WS? "(" _WS? "by" _WS? ":" _WS? path _WS? ")" _WS? block
comptime_blk : "comptime" _WS? block
hole      : "todo!" "(" _WS? STRING? _WS? ")"
_WS       : (WS | COMMENT)+
COMMENT   : /\/\/[^\n]*/
%import common.WS
```

- Every keyword is contextual ([01-language §2.4](01-language.md)): `flow`, `store`, `evolve` or
  `export` is reserved only where an item begins, so `store: &Store` still parses as a parameter.
  The clause words inside a `store` or `evolve slot` item (`fallback`, `validate`, `budget`, `seed`,
  `objective`, …) are reserved only inside that item ([02-compute §12.3](02-compute.md),
  [06-forge §2.1](06-forge.md)).
- The production parser is hand-written for error recovery. It is differentially fuzzed against
  the Lark grammar, and the two must accept the same language.
- CI checks parse∘print = id over the corpus. Printing is canonical, so formatting never changes a
  definition's identity.
- Built-in `name!(…)` forms, `todo!` among them, are a closed set with Rust meaning; the list is in
  [01-language](01-language.md). User macros are a Dc rejection (DR-005).
- One file drives the Tier 1 printout, the OpenAI CFG tools, the Surface Lab's parsers, Hearth's
  grammar mask and the formatter tests.
- A grammar change is a language change (§14).

---

## 4. The false-friend table

**Status: v0 seed; spellings revised by the Surface Lab.** The authoritative seed table is
[01-language §2.5](01-language.md). It is not repeated here, and this document uses its IDs (FF-SUM,
FF-TIES, FF-EXP, FF-REF, FF-LOCAL, FF-Q4, …). This section says how the table is used by agents.

**Classes (DR-002).** Every construct is **C** (coincident: Rust syntax, Rust meaning), **Dc** (a Rust
form Mithril rejects with a named diagnostic) or **D** (a new, keyword-led form). The Surface Lab's
divergence detector (§14) sorts each Rust form against Mithril's intended meaning:
- **Coincident:** the form stays C.
- **Checker-visible divergence:** the form becomes Dc.
- **Checker-invisible divergence:** the form would compile but silently mean the wrong thing for
  Mithril's purpose. The bare form is trapped (Dc), and a D form takes its place, as with `topk(k,
  Ties::LowerIndex, Nan::Last)` for float `max_by` in exact code. Nothing is reinterpreted.

**Grade indexing.** A row can be C in default code, Dc in exact-graded or logits-path code, and C
again in `timing_only` policy code, which cannot affect outputs (FF-SUM, FF-TIES, FF-EXP; DR-013,
DR-014).

**How agents meet the table.**
- **Tier 0** carries every row in one line with its fix, within the 2,300-byte block (§2).
- **Diagnostics:** a `FalseFriend` diagnostic names the row ID, the prior and the Mithril rule (§5).
- **Hole replies and packs** list the rows relevant to the expected type, grade or constructs
  present (§6, §8).
- **The lifter** applies the C-prior rows: it flags C contraction (FF-FMA) and maps `nearbyintf` to
  `round_ties_even()` (FF-ROUND) (§17).

**How the table grows.** A row is added when the divergence detector, a hash-corpus mismatch or the
harness's false-friend incidence finds a new trap. Every row is an atom of the Surface Map (§14),
with a witness input that separates Mithril's meaning from the prior. The Surface Lab may change a
row's spelling, never its rule [01-language §2.5].

---

## 5. Diagnostics

**Status: v0.** At X1, `mithi` emits basic JSON diagnostics. Full grouped diagnostics arrive at M1,
the stage DR-017's second kill judges.

**Format.** JSON is primary, and human text is rendered from it.
- Codes are stable mnemonics of the form `E-<AREA>-<NAME>`, as used throughout
  [01-language](01-language.md) (`E-FF-SUM`, `E-REF-ESCAPE`, `E-LINEAR-DROP`).
- Mithril never uses rustc's numeric `E0xxx` codes. Those codes are in model priors, so giving one
  a new meaning would be a false friend at the diagnostic level.
- `mithc explain <code>` gives one worked example per code.

**Grouping.** Diagnostics are grouped by root cause. Each group has one root and a count of
suppressed cascades. A response carries at most five groups by default, and roots come before what
they cause [R03].

**Spans are anchors:** definition path, content hash and anchor text, never a line number. Lines
appear only in SARIF export (§11); the judges flagged P5's draft for mixing the two.

**Contents.** A diagnostic carries:
- a stable code;
- a kind (`Type`, `Effect`, `Ownership`, `Grade`, `FalseFriend`, `Evidence`, `Policy`, …);
- expected and actual types;
- the hole context, when the error sits in a hole;
- nearest-name suggestions from the content-addressed API index (hallucinated identifiers are a
  measured failure class [R03]);
- for a `FalseFriend`, the construct ID, the prior and the Mithril rule [G01];
- fixes, each with an applicability level.

**Fix applicability.** Mithril extends rustc's levels (`MachineApplicable`, `MaybeIncorrect`,
`HasPlaceholders`, `Unspecified` [R03]), so that each fix states what evidence it destroys:

| Level | Meaning | Batch-applicable | Must list |
|---|---|---|---|
| `Safe` | preserves meaning (≈ `MachineApplicable`) | yes, `mithc fix --safe`, except FalseFriend rows of class D | — |
| `InterfaceChanging` | changes a public signature | no | how many dependents become holes (§9) |
| `MeaningChanging` | changes results | no | the ledger entries it invalidates (claim kind, grade, definition hash) and the obligations it creates |
| `SpecTouching` | edits a spec or claim | never; Author role only | the spec items touched |
| `HasPlaceholders` | inserts holes | no | the holes it creates |

A diagnostic has at most one `Safe` fix. `fix --safe` skips class-D FalseFriend diagnostics, because
the trap exists to force a choice. When a governing spec already names an order (for example
`canon::sum16`), the diagnostic says so in `spec_hint`.

**Verifier output.**
- `mithc prove` renders a failed SMT obligation as concrete Mithril values: a counterexample shaped
  as a test, which can be added as an Adversary-owned regression test [P1 §5.5]. Verifier-feedback
  rounds raised success on DafnyBench and AlgoVeri [R03].
- A T1 mismatch reports the minimal differing DAG fragments ([03-trust](03-trust.md)).

**Unknown results.** During iteration, "unknown" means "not yet", and the response names the smallest
failing obligation. For promotion, unknown counts as rejection.

**Untrusted text.** Identifiers, comments, string literals and rationale appear only in `quoted`
fields. Templates are maintainer-curated and hashed.

An example. Names and hashes are illustrative; the quoted anchor is the rejected input:

```json
{"code":"E-FF-SUM","kind":"FalseFriend","construct":"FF-SUM","group":1,"root":true,
 "at":{"def":"model::rmsnorm","hash":"h:91aa03c7","anchor":"x.iter().map(|v| v * v).sum::<f32>()"},
 "grade_context":"exact (logits path)",
 "prior":"Rust: Iterator::sum is a sequential left fold",
 "rule":"exact code names its reduction order (canon.v1)",
 "spec_hint":"spec rmsnorm_meaning uses canon::sum16",
 "fixes":[
  {"applicability":"Safe","replace":"canon::sum_seq(x.iter().map(|v| v * v))","invalidates":[]},
  {"applicability":"MeaningChanging","replace":"canon::sum16(x.iter().map(|v| v * v))",
   "invalidates":["tested:model::rmsnorm@h:91aa03c7"],"obligations":["check --tests","hash corpus"]}],
 "cascade_suppressed":3,"explain":"mithc explain E-FF-SUM"}
```

---

## 6. Typed holes and type search

**Status: v0 (M1).**

**Spelling and meaning (DR-003).**
- `todo!()` and `todo!("name")` type-check against the expected type, and the program still runs.
  Reaching a hole is a trap ([01-language §12](01-language.md)), with Rust's panic meaning: it ends
  its fail domain (01 §12.2), never unwinds and never aborts the host.
- `?name` is not used, because Rust's postfix `?` is the try operator.
- Unnamed holes get positional names (`<def>#1`, …). These survive formatting but not insertion, so
  the card recommends named holes.
- A release build with a reachable hole fails the evidence policy.
- Example: `let score = todo!("eviction_score");`.

Hole context is the best-measured lever. With type information, StarCoder2-15B improved about 10× in
Hazel. Error rounds alone were ineffective without types [R03]. A cold agent writing Rust-style stubs
gets typed holes for free [inference].

**What `mithc hole <name>` returns.**
- the expected type, fidelity grade and determinism scope;
- the allowed effects: the enclosing `uses { }` row, narrowed by `policy fn` rules;
- the bindings in scope, with types and ownership modes (shared, exclusive, owned, projection);
- the obligations: `requires`/`ensures`, `#[range]` facts and T2 side conditions;
- ranked candidate functions, from type-directed search;
- the relevant false-friend rows;
- the governing spec and its strength.

Example: inside the canonical `q4_row_dot` kernel, the inner loop is replaced by
`let isum: i32 = todo!("block_isum");` (names illustrative):

```json
{"verb":"hole","hole":"block_isum","at":{"def":"quant::q4_row_dot","hash":"h:5e0c91a2"},
 "expected":"i32","grade":"exact","det":"cross_device","uses_allowed":[],
 "in_scope":[{"name":"w","type":"&[BlockQ4]","mode":"shared"},
             {"name":"a","type":"&[ActQ8]","mode":"shared"},
             {"name":"g","type":"usize","range":"0..w.len()"}],
 "obligations":["T2: |result| <= 64 * 8 * 127 = 65_024 < 2^24, so `isum as f32` is exact"],
 "candidates":[{"fn":"BlockQ4::int_dot","type":"fn(&BlockQ4, &[i8; 64]) -> i32",
                "origin":"derived by format BlockQ4"}],
 "false_friends":["FF-Q4: high nibble of byte j is element j+32 (llama.cpp Q4_0: j+16)"],
 "next":[{"cmd":"mithc edit fill_hole quant::q4_row_dot block_isum","why":"1 open hole"}]}
```

**Type search.** `mithc search --type "fn(&[f32], &[f32]) -> f32" --uses "{}"` queries the API index
through the Fact Plane. It returns only existing definitions, with their hashes [P2 §7].

**Pre-registered parameter.** DR-003's revisit trigger reads `agent.hole_use_floor`: the minimum share
of Mithril-arm attempts that use a hole. It is fixed before the first held-out run. Below the floor,
the Surface Lab tests `?name`.

---

## 7. The edit protocol

**Status: v0 (M1).** In one single-author preprint (medium confidence [RV: S3]), line-number edits
corrupted 99.1% of files after a one-line shift, and function-name anchors hit the wrong function
12.7% of the time. An anchor-and-verify applier misapplied silently once in 8,320 trials [RV: S3].
Removing SWE-agent's lint guard cut its score from 18.0% to 15.0% [R03]. These figures motivate the
design but do not establish it: the protocol's own gate and kill below are the decisive test.

**Identity and anchors.** An anchor is `path@h:<hex>`, carrying the *definition hash* of
[04-toolchain §3](04-toolchain.md): a normalised AST with locals alpha-renamed, and comments and
formatting excluded. Renames and comment edits therefore invalidate no evidence. An edit also checks
the separate doc hash, so a concurrent comment change still returns `StaleAnchor` and no edit lands
on text the agent has not seen. Anchors display 8 hex digits; unique shorter prefixes are accepted.

**Operations.**
- `replace_def(path@hash, text)`: `text` holds exactly one definition with the same path.
- `replace_in(path@hash, search, replace)`: `search` must match exactly once inside the definition,
  after canonical formatting and with lenient whitespace. Zero matches return `NoMatch` with the
  nearest candidate; several return `AmbiguousMatch` with a count, as Anthropic's `str_replace` does
  [R03].
- `insert_after(path@hash, text)`.
- `fill_hole(path@hash, name, text)`.
- `rename(path, new_name)`: semantic hashes and evidence are unchanged.
- `delete_def(path@hash)`: refused while dependents exist, unless `propagate` is set.

Reading is `mithc outline <path>` with one of four projections: `signature | familiar | typed |
slice`. Windows are about 100 lines, SWE-agent's best setting [R03]. A token-dense projection is
**later** and needs an A/B win first: dropping formatting saves 10–25% of tokens [R03], but
familiarity comes first.

**Atomic edit-plus-check.** A batch is parsed, formatted, resolved and checked as one unit, up to the
named gate (`parse | types | prove`; the default is `types`).
- On success, mithc writes canonical text to disk, updates `mith.lock` and records a journal entry.
  The response returns new hashes, the check result, the evidence invalidated and `next`.
- On failure, nothing is applied. The response returns grouped diagnostics anchored in the proposed
  text.

**Staleness.** A stale anchor returns `StaleAnchor`, with the current hash, the current text (within
budget) and the journal entry that changed it. Nothing is ever applied fuzzily.

**The flat envelope for Claude.** Claude's structured outputs accept only non-recursive JSON Schema,
without length constraints [R03]. An operation is one flat object, and a batch is an array of them:

```json
{"gate":"types","propagate":false,"ops":[
 {"op":"replace_in","target":"model::rmsnorm","anchor":"h:91aa03c7",
  "search":"x.iter().map(|v| v * v).sum::<f32>()",
  "replace":"canon::sum16(x.iter().map(|v| v * v))"}]}
```

- The fields are `op` (an enum), `target` and `anchor`, plus optional `search`, `replace`, `text`,
  `hole` and `new_name`. All are strings.
- No field contains an operation, so the schema has no recursion.
- Code is a string payload that mithc validates, never a JSON AST. mithc enforces length limits
  itself.

A stale-anchor response (illustrative):

```json
{"verb":"edit","ok":false,"error":"StaleAnchor","target":"model::rmsnorm",
 "given":"h:91aa03c7","current":"h:2b71e0d4","changed_by":"j:0415","current_text":"…"}
```

**Roles and concurrency.**
- Ownership is per definition path and role ([03-trust](03-trust.md)). A Builder editing a spec item
  gets `RoleDenied`.
- Concurrency is optimistic at definition granularity: different definitions never conflict, and the
  same definition gives `StaleAnchor`, never a silent overwrite.
- Hard file locks are rejected: they cut 20 agents to the throughput of 2–3 at Cursor [RV: D2-F].

**An accelerator, not a gate.** Plain file edits stay legal. Text on disk is the truth: `mithc fmt`
canonicalises, identities are recomputed, and `mithc check` reports breakage.

**Gate and kill.** In replay, silent misapplication must stay at or below 1 per 5,000 edits [target].
If the protocol beats `str_replace` plus format-on-save by nothing (CI excludes a benefit), the store
becomes a derived index and the protocol leaves Tier 0 [P1 §10].

---

## 8. Context packs and closure budgets

**Status: v0 (M1); closure budgets enforced from M2.** On NoLiMa, 11 of 13 models fell below half
their short-context baseline at 32k tokens [G01]. Cross-file changes are where agents degrade most
(Multi-SWE-bench) [R03]. A pack therefore ships signatures, not bodies.

`mithc pack <target> --budget N --for edit|review|port` assembles, in priority order [P1 §7.7]:
1. the target definition;
2. callee and caller signatures, `uses` rows, contracts, grades and evidence status, without bodies;
3. type and `format` definitions in the closure;
4. governing specs and claims, with strength;
5. false-friend rows for the constructs present;
6. relevant invariants, verbatim, with text hashes;
7. one corpus example that uses the same API.

The pack is cut to budget. It ends with an index of omitted items that the agent can expand by name.
Comments and rationale inside it are marked as quoted data.

**Closure budgets.** `#[closure_budget(N)]` makes context locality a compile-time property of a module
[RV: S15]. The signature closure needed to type-check its public items must fit N tokens. Otherwise
the build fails, with fixes: split the module, narrow imports, or move a type. For scale, Hearth's
`store.c` is 1,030 lines, plausibly 12–15k tokens [inference]. A pack for editing `pick_victim` should
fit in 6k [target].

**Gate and kill.** Hole context plus packs should cut TPV by at least 20% at equal or better VP@1
[target] [P1 §10]. If packs gain nothing over agent-driven file reading, they become opt-in, and
`closure_budget` becomes a lint.

---

## 9. `propagate`

**Status: v0 (M1).** `mithc propagate` turns a signature change into local work items [RV: S3]. It
runs when a batch sets `"propagate": true`, or after an `InterfaceChanging` fix. It then:
1. re-checks the reverse dependents in the query database;
2. finds, in each, the smallest expression that no longer type-checks;
3. wraps that expression as a named hole, `todo!("propagate#3")`.

Each hole's context stores the replaced text, the old and new signatures, and the reason. The program
still type-checks and runs; reaching a propagated hole is a trap (01 §12). The response lists the
work items in dependency order, each with a pack. The journal records the set, so handovers show
what is open.
The store stays well-typed, every repair is local, and no agent edits a caller it has not been shown.

**Kill.** If propagation neither raises VP@1 nor lowers TPV on T-XMOD (§13), compared with plain
diagnostics, it becomes opt-in.

---

## 10. Session state: journal, handover, resume, friction, abandon

**The toolchain journal (v0, M1).** mithc, not the agent, appends one entry per call to a
hash-chained, per-session journal outside the repository. Each entry records the command, the role,
the model family, the store roots before and after, the exit status, a diagnostic digest and the
evidence delta. On one desktop it is tamper-evident, not tamper-proof. The Gatekeeper countersigns
chain heads when admitting ledger facts, and manifests are cross-checked against gate-signed facts
([03-trust](03-trust.md)). `validated` and `measured` evidence comes from the gate, never from the
agent's process [P5 §7].

**Handover (v0: journal-backed at M1, ledger-backed from M3).** `mithc handover` emits a manifest that
extends Hearth's `governance/schemas/handover.schema.json`. Its facts come from the journal and the
ledger. The agent writes only `rationale` and `next_actions`, both length-capped. DGM faked its
tool-use logs [R01]; this design closes that failure class.

| Hearth schema field | Derived from |
|---|---|
| `generation_id`, `parent_generation` | the session chain |
| `lifecycle_status`, `trigger` | `TASK_COMPLETE` when acceptance claims hold in the ledger; `FRICTION_ABORT` after friction escalation or `abandon`; `ORDERLY_APOPTOSIS` at a budget or context threshold; `CRASH_RECOVERY` when the chain has no clean close |
| `workspace` | store roots and git commits, before and after |
| `constraints_touched` | invariant IDs linked to touched definitions, verbatim |
| `epistemic_ledger` | claims admitted (validated); claims refuted or tombstoned (falsified) |
| `procedures` | journal commands that succeeded and produced admitted evidence |
| `measurements` | ledger `perf` facts; `kind: measured \| simulated` mandatory (optional in Hearth today) |
| `active_blockers` | outstanding groups, policy gaps, friction-blocked signatures |
| `unfulfilled_mandates` | acceptance criteria without evidence |
| Mithril additions | open holes with contexts; evidence invalidated; tombstones created; compute and alpha spent |

Two choices here are Hearth constitutional decisions ([07-hearth-port](07-hearth-port.md)): making
`kind` mandatory, and treating toolchain-generated manifests as canonical.

**Resume (v0).** `mithc resume <manifest>` verifies the manifest against the journal chain. It then
reports drift since the handover: definitions changed, by whom, and evidence invalidated. Finally it
builds an orientation pack: manifest facts, packs for open holes and top groups, and `next`. As in
Hearth, the successor never reads a transcript.

**Friction rule (v0).** A fourth identical failing retry is blocked unless a root-cause note exists.
- "Identical" means the same verb, the same error signature (code, root anchor, normalised message),
  and no change to the definitions involved.
- The blocked call returns `FrictionBlocked` with a template. The note is journaled as agent-written
  text.
- If the same signature fails again after two notes, the response recommends `abandon` or a
  `FRICTION_ABORT` handover.

This is Hearth's `governance/tools/friction.py` (default threshold 3), made toolchain behaviour.

**`abandon` (v0).** `mithc abandon --reason spec_conflict|infeasible|blocked|budget` records a
first-class outcome. It writes a typed journal and ledger entry, proposes a candidate tombstone, and
sets the handover status. An abort option cut GPT-5's cheating on conflicting tasks from 54% to 9%
(ImpossibleBench) [RV: D2-E].

---

## 11. The tool surface: verbs, envelope, `next`, CLI/MCP/LSP/SARIF

**One JSON contract, three transports.** The CLI (`--json`), the MCP server (`mithc mcp`) and the LSP
share one JSON. Testing and mutation are `mithc check --tests` and `mithc check --mutate`, so the
canonical verb list stays closed. Forge participation is also flags on existing verbs, `bench --slot`
and `ledger campaign`; campaigns themselves are supervisor-only, with no campaign verb
([06-forge §1.1](06-forge.md)).

| Verb | Purpose | Status | Detail |
|---|---|---|---|
| `check` | grouped diagnostics; `--tests`, `--mutate` | v0 (M1) | §5 |
| `hole`, `search` | hole context; type-directed search | v0 (M1) | §6 |
| `edit`, `outline` | atomic edit-plus-check; projected views | v0 (M1) | §7 |
| `fix`, `fmt`, `guide` | Safe fixes; canonical format; Tier 1 | v0 (M1) | §5, §2 |
| `pack`, `propagate` | context packs; broken dependents become holes | v0 (M1) | §8, §9 |
| `handover`, `resume`, `abandon` | session state | v0 (M1; ledger-backed from M3) | §10 |
| `lift` | C/Rust subsets to `.mith` | v0 (M1) | §17 |
| `prove`, `audit` | T0–T2 obligations and counterexamples; object audit | v0 (M2) | [03-trust](03-trust.md), [04-toolchain](04-toolchain.md) |
| `explain`, `bench`, `profile measure` | floor and fraction of roof; measurement requests | v0 (M2) | [02-compute](02-compute.md), [06-forge](06-forge.md) |
| `ledger`, `revisit` | `why`, `--trust-base`, policy gaps; tombstone triggers | v0 (M3) | [03-trust](03-trust.md), [06-forge](06-forge.md) |
| `bench <def> --slot <slot>`, `ledger campaign <slot>` | Forge flags: submit a candidate body to that slot's cascade (a request; the gate measures); read-only view of the campaign's archive, queue, budget and tombstones | v0 (M4, live F1 on the engine); campaigns v1 (M6) | [06-forge §1.1](06-forge.md) |

**Response envelope.** Every response is one JSON object with these fields: `v` (schema version),
`verb`, `ok`, `role`, `store_root`, the verb's results, `groups`, `evidence_delta`, `budget` (`used`,
`truncated`, `omitted`), `journal` and `next`. Arrays hold flat objects, and nesting is bounded and
non-recursive.

**Response budgets [target].**
- `check` ≤ 1.5k tokens (top five groups);
- `hole` ≤ 1.5k;
- `ledger why` ≤ 1k plus counterexamples;
- `bench` ≤ 0.5k;
- `pack` = the requested budget.

Latency targets are in [04-toolchain](04-toolchain.md).

**`next` actions (v0).** Every response ends with `next: [...]`: one to three commands, each with
`cmd`, `why` and a coarse cost class.
- Deterministic rules choose them, in this order: Safe fixes; open holes; the cheapest action that
  closes the largest evidence-policy gap; `handover`.
- They are never produced by a model or built from text in code.
- They never name a verb the session's role lacks. The rule table is an F1-A artifact
  ([06-forge](06-forge.md)).
- **Kill:** if `next` does not reduce turns per verified pass at equal VP@1, it defaults to off.

**Roles.** A session holds one role token ([03-trust](03-trust.md)). Verbs its role cannot use are
absent from its MCP tool list.

**MCP (v0, M1).** Tools have non-recursive JSON Schemas. Model instructions ship separately, as with
`gopls mcp -instructions` [R04].

**LSP (by-trigger, ROADMAP D-10).** It adds ChatLSP-style hole, pack and evidence extensions, and
fix-its as code actions [R03], [R04]. Diagnostics are published only for the edited closure, because
Claude Code slowed per turn when servers published thousands of files' diagnostics [R04]. Agent use
waits for an A/B.

**SARIF 2.1.0 (v0, M1).** Each group becomes a result, with the definition path as its logical
location. Lines are derived at export. Applicability and invalidated evidence go in the property bag
[R04].

---

## 12. Constrained decoding (deferred)

**Status: by-trigger (DR-023, ROADMAP D-11).** Type-constrained decoding cut TypeScript compile
errors by 75.3% (HumanEval) and 52.1% (MBPP), where syntax-only constraints would have removed 9.0%
and 4.8%. 99.4% of tokens needed one check [R03]. Only a host that owns the logits can do this; for
Mithril, that is Hearth. Small local models should suffer more false friends, since overriding priors
emerges with scale [RV: D3-i] [inference].

**Design.**
- **Completion-engine API.** `prefix_check(text_prefix) -> {extendable, admissible_token_classes,
  expected_type?}`, the "compiler as incremental completion engine" Mündler et al. ask for [R03]. It
  is built with the LSP or the masks, whichever triggers first.
- **Grammar mask.** Computed from `mithril.lark`. INV-DEP forbids linking llguidance (Rust) or
  XGrammar (C++), so the engine would be new C11 [R03]. llguidance's ~50 µs per token on a 128k
  vocabulary is about 0.1% of a 45–53 ms Hearth token [R03]. That figure is llguidance's; a fresh C
  port's cost is unsized.
- **Type mask.** Supplied out of process by `prefix_check`, applied at identifier and hole
  boundaries.
- **Placement.** The masks apply to the code channel only; reasoning stays free (the "Let Me Speak
  Freely" caveat). Grammar-aligned sampling is an option [R03].
- **Hook.** An opt-in sampler hook in `hearth.h`, off by default, so INV-LOSSLESS-DEFAULT holds. It
  is a Hearth constitutional change ([07-hearth-port](07-hearth-port.md)).

**Trigger (DR-023).** An out-of-tree prototype's type masks cut compile errors by at least 30%
[target] with no VP@1 loss, **and** the quiet-window exclusion of [06-forge](06-forge.md) exists.
Local generation is never co-scheduled with measurement. A 6k-token pack plus a 500-token candidate
takes about 40–50 s of loaded machine time (the systems judge's estimate, [inference]).

**Once triggered.** Mask overhead must stay ≤ 5% of decode time [target]. **Kill:** if errors fall by
less than 15%, or VP@1 drops, only grammar masks remain [P1 §10].

---

## 13. The comprehension harness

**Status: v0 (M0); F1-A scoring v1 (M6).** The harness turns "agents write Mithril well" into a
measured gap against the strongest prior. It has three jobs:
- score language and toolchain decisions;
- gate the standalone surface (DR-017);
- supply F1-A's fitness [RV: D2-D].

It is Gatekeeper-owned: suites are hash-locked, oracles are hidden, and Builder sessions can neither
run it nor read its scoring ([03-trust](03-trust.md)). X1's schedule, cost and amber triggers are in
[ROADMAP §3.2](../ROADMAP.md).

**Task families.** Sealed, Hearth-shaped, rotated each epoch, with a permanent holdout never used for
tuning. Every oracle kills at least 95% of mutants, `numerics_v1` included [P1 §7.11], [RV: D2-D].

| Family | Task | Oracle |
|---|---|---|
| T-Q4 | bit-exact Q4 dot and matvec | hash-exact |
| T-ACTQ | activation quantisation | byte-exact |
| T-NORM | RMSNorm, softmax under canon.v1 | bit-exact |
| T-ROUTE | grouped top-k, lower-index ties, NaN last | exact indices |
| T-EVICT | a `policy fn` eviction policy | bit-identical logits, plus bytes and stall |
| T-STORE | slab arena, pins, 4096 alignment | functional and permutation tests |
| T-FMT | bounded container parser | fuzz parity |
| T-CTRL | mutex-guarded queue; rank-order combine | permutation tests; exact |
| T-XMOD (from M1) | cross-module signature change | all dependents pass |
| T-CONFLICT (from M1) | spec and tests contradict | correct outcome is `abandon` |

X1 uses at least 80 items: about 20 for card iteration and at least 60 held out [ROADMAP §3.2]. Items
are parametric variants within a family (formats, tie rules, sizes, failure modes). Variants are
correlated, so the analysis models the family as well as the item.

**Contamination rule (pre-registered).** Card atoms that sit near a sealed task's solution bias X1,
M1 and F1-A fitness toward the Mithril arm, because only that arm gets a reference in its own
language. Hearth and the Mithril documents are public, so later models will also train on them. The
rule has five parts:
- **Atom isolation.** Card snippets (Tier 0 and Tier 1) and F1-A atoms come from outside the sealed
  families' solution space. An automated check compares each atom with every hidden reference
  solution: token 5-gram containment, and similarity of alpha-renamed ASTs (Rust and C references are
  parsed into the same normalised form, §17). The threshold is fixed in the pre-registration
  (proposed: containment ≤ 0.2 and AST similarity ≤ 0.3 [target]). An atom above it is rejected.
- **Equal-information brief.** Every arm gets the same task brief. It states the domain rules in
  prose: canon.v1 and NUMERICS reduction order, rounding and NaN rules, the Q4 block layout, and the
  relevant Hearth invariants. Where the Mithril card has a snippet for a construct the task needs,
  the Rust and C11 arms get an equivalent snippet of similar size in their own language. The canon.v1
  primitives that Mithril's std provides are given to those arms as a small library in their
  language (Hearth's C helpers; a Rust port) [inference]. Language content (syntax, keywords,
  false-friend rows) stays arm-specific; brief sizes are logged per arm.
- **Sealed storage.** Suites, reference solutions and oracles live in the Gatekeeper's private
  store, never in a public repository. Sealed artifacts carry a canary string, so a leak into a
  training corpus can be detected [inference].
- **Fresh items.** Each epoch adds fresh items, at least 30% of the rotated suite [target], that are
  not derivable from public Hearth code or Mithril documents. They pass the same similarity check
  against that public corpus. A sealed item whose reference solution exceeds the threshold against a
  public snippet (ARCHITECTURE §5.3's, for example) is flagged *public-near*. Kill decisions use
  unflagged items only, and authors add items until at least 60 unflagged ones are held out; flagged
  items are reported separately.
- **Contamination read-out.** F4 decay re-runs (§14) and M7's rotated suite score fresh and reused
  items separately. A growing reused-minus-fresh gap is read as contamination, not as improvement.

**Arms.** Six arms: five comparison arms plus the traits ablation (DR-005). Every arm gets the same
tasks, oracles, visible tests, equal-information brief (contamination rule above), checker-call
budget (8 per task at X1 [P5 §10.1]), token budget and wall time.

| Arm | What it isolates |
|---|---|
| Mithril (Tier 0+1 at X1; Tier 0, 0+1, 0+1+2 later) | the candidate; the tiers form the card-size sweep [G01] |
| Mithril without traits | the cost of omitting static-dispatch traits (DR-005) |
| Rust | the strongest prior and the real fallback; DR-017's comparator |
| Rust + Mithril tooling | the Mithril arm's tooling applied to Rust: false-friend checks, hole context on `todo!()`, Mithril diagnostics; ledger evidence via `lift` from M1 (§17) |
| C11 | Hearth's current language |
| Obfuscated Mithril | the same semantics with unfamiliar tokens; separates comprehension from guessability (obfuscation dropped LINGOLY-TOO from 0.59 to 0.48 [RV: D2-D]) |

The arms give four contrasts:
- Mithril − Rust is the total effect DR-017 judges.
- Mithril − (Rust + tooling) is the surface effect, with the tooling held fixed.
- (Rust + tooling) − Rust is the tooling effect.
- Mithril − obfuscated is the familiarity gap FG [RV: D3-i].

A sub-ablation swaps specific `FalseFriend` diagnostics for generic ones.

**Participants.** At least two frontier families. One family drafted Mithril's card, so the second
also serves as the independent-writer test that GAMBIT lacked (its designer and writer were the same
model) [G01]. One Hearth-hosted local model takes part outside quiet windows only. It is not a Forge
proposer (DR-023).

**Metrics.**
- **VP@1 (primary):** the share of attempts whose final submission passes the hidden oracle. An
  attempt is one fresh session with the fixed budget. `abandon` on a solvable item counts as a fail.
- **CABW (co-primary):** among attempts that the agent submits as done *and* that pass the arm's own
  acceptance check (its compiler and checkers plus the visible tests), the share the hidden oracle
  rejects. The unconditional rate (accepted-and-wrong over all attempts) is reported too.
- **Secondary:** tokens, turns and dollars per verified pass (TPV, turns/VP, $/VP); the
  first-compile rate; false-friend incidence per construct; FG.
- **T-CONFLICT, analysed separately:** `abandon` precision and recall, and the special-casing rate.
  Special-casing counts as a CABW event.
- **Card and pack fitness:** the Pareto-front slope (marginal VP@1 per kilotoken of always-on
  context), never a raw ratio [RV: D2-D].

**Statistics.** Attempts are not independent: items differ in how much harder they are in one
language, and that item × arm variance does not shrink with more attempts.
- **Model (pre-registered):** logistic mixed effects,
  `success ~ arm * family + (1 | task_family/item) + (0 + arm | item)`.
- **Estimand:** the marginal VP@1 difference, Mithril minus Rust, in points, families weighted
  equally. A cluster bootstrap over items checks robustness.
- **Kill decisions** use a fixed, pre-registered n with no interim looks. The held-out set runs once,
  after the card is frozen [ROADMAP §3.2].
- **Screening** (card edits, F1-A candidates) uses about 100 IRT-selected items from the non-held-out
  pool, tinyBenchmarks-style, with anytime-valid regression gates [RV: D2-D].

**Power.** On the probability scale, the variance of the estimated gap is roughly
[σ²_ta + 2p(1−p)/(mF)] / n. Here n is the item count, m is attempts per item per arm per family, F
is the family count, and σ_ta is the SD of the item-specific arm effect. Illustration with p = 0.5,
F = 2 and *assumed* σ_ta, not findings [inference]:

| σ_ta (assumed) | n = 60, m = 5 (600 attempts/arm) | n = 60, m = 20 (2,400) | n = 120, m = 5 (1,200) |
|---|---|---|---|
| 0.10 | SE 3.2 points | 1.9 | 2.2 |
| 0.15 | 3.5 | 2.4 | 2.5 |
| 0.20 | 3.9 | 3.0 | 2.7 |

Three consequences [inference]:
- **Items beat attempts.** At σ_ta = 0.20, 1,200 attempts over 120 items beat 2,400 over 60.
- **The quoted figure assumes independence.** "About 1.5k attempts per arm for 5 points" [RV: D2-D]
  is the independent-attempt figure (SE ≈ √(0.5/1,568) ≈ 1.8 points; 80% power at α = 0.05). It
  understates the need when σ_ta is not small.
- **Operating characteristics decide.** ROADMAP requires the X1 VP@1 kill to fire with probability
  ≤ 10% at a true gap of 5 points and ≥ 90% at 25 [target]. A point-estimate rule at 15 points meets
  that when SE ≤ 7.8, and every row does. Proposed analogues [target]: for M1 VP@1, ≤ 10% at a gap of
  0 and ≥ 90% at 20; for X1 CABW, ≤ 10% at 0 and ≥ 90% at 10, which needs SE ≤ 3.9 points. M1's CABW
  threshold is 0, so a point-estimate rule would fire about half the time under true equality. It is
  therefore run as the one-sided test defined under the kills below: ≤ 10% at 0 and ≥ 90% at a true
  excess of 5 points [target], which needs SE ≤ 1.95 points (the rule fires when the estimate exceeds
  1.28 SE).

Before held-out collection, the power analysis is recomputed with a conservative σ_ta from the
card-iteration items. It is published with the kill-probability curve (DR-017). If 60 items fall
short, the item count grows; the threshold never moves [ROADMAP §3.2].

**Pre-registered kills (DR-017).** The kills are against Rust and disjunctive, with at least 60
held-out items and at least two families.
- **X1** (paper Mithril, Tier 0/1, `mithi`): a VP@1 gap over 15 points, **or** CABW more than 5 points
  worse than Rust's, stops the standalone surface. Mithril then ships as checker, ledger and tooling
  over Rust and C.
- **M1** (full diagnostics): a gap over 10 points, **or** CABW above Rust's, has the same outcome.
  "CABW above Rust's" is decided by a one-sided test: it holds when the one-sided 90% lower
  confidence bound of CABW_Mithril − CABW_Rust, from the pre-registered model, exceeds 0. Under true
  equality the kill then fires with probability ≤ 10%, not about 0.5. This operationalises DR-017's
  threshold without changing it. Its kill-probability curve is published with the X1 VP@1 curve. A
  fixed margin of about 2 points would give a similar operating characteristic, but it would change
  the threshold's wording, so the confidence-bound form is preferred.

Before collection, the Comprehension Ledger records:
- the thresholds, their test forms (including M1's one-sided CABW test) and the model;
- the contamination thresholds, the public corpus they are checked against, and the per-arm briefs;
- the exclusion rules (infrastructure failures are re-run, not scored);
- n and the stopping rule;
- the named parameters `agent.subset_rejection_bound` (§16) and `agent.hole_use_floor` (§6).

The Gatekeeper judges the result. A breach in one family only goes to the Owner. The Rust + tooling
arm does not change these rules. ROADMAP's amber review fires if it beats Mithril by more than 10
points [target].

**Comprehension precondition per port stage.** Before a stage starts, its families must be within 10
points of Rust on VP@1, with CABW no higher [target]. A miss delays the stage; it is not a kill.

| Stage | S1 | S2 | S3 | S4 | S5 | S6a |
|---|---|---|---|---|---|---|
| Families | T-Q4, T-ACTQ | T-FMT | T-CTRL | T-STORE, T-EVICT | T-NORM, T-ROUTE | T-CTRL |

([ROADMAP §5](../ROADMAP.md), [07-hearth-port](07-hearth-port.md))

**Goodhart and drift guards.**
- epoch rotation and a permanent holdout;
- the contamination rule: isolated atoms, equal-information briefs, private suites, fresh items;
- task authors from a different family than the card editors;
- the obfuscated arm;
- test-retest VP@1 within ±3 points [target];
- F4 decay re-runs at each model generation (§14);
- results stored as ledger facts keyed by model, card hash and suite hash.

---

## 14. The Surface Lab and the Surface Map

**Status: pilot v0 (alongside M1, on D1–D5); full runs v1, before the M7 syntax freeze.** The Surface
Lab decides constructs one at a time [RV: D3-i]. A divergence detector runs Mithril's meaning against
each prior lexeme (Rust, C, numpy, llama.cpp) on witness inputs, and sorts the divergence as
coincident, checker-visible or checker-invisible (§4). The pilot set keeps RV's labels, where "D"
marks a checker-invisible divergence: D1 f32 reduce-add, D2 float product chain, D3 rounding, D4
top-k/argmax, D5 Q4 layout, Dc6 timing-only eviction, C7 `a*b + c`, C8 half-open range.

**Arms.** Each construct is tested in four arms:
- **F**: the familiar form, *with its Rust meaning*.
- **M**: the familiar stem plus a mandatory disambiguator, as a Rust enum argument.
- **A**: a new keyword or type.
- **O**: an obfuscated control.

The bare familiar form is trapped in every arm except F. No arm gives a Rust form a non-Rust meaning,
because DR-002 rules that out before measurement. Arm F therefore measures how often agents silently
produce the Rust meaning where the task needs another: the false-friend incidence.

**Decision rule.** Minimise TPV subject to false-friend incidence ≤ τ (pre-registered, e.g. 1%)
[RV: D3-i]. Blame is assigned by substitution: swap construct nodes for the reference meaning, re-run
the oracle, and minimise with ddmin. RV estimates about 390 episodes per arm per construct [RV: D3-i,
inference]. That is roughly 12k episodes for four arms and eight constructs, which is why the pilot
starts with D1–D5.

**Falsifiers** [RV: D3-i]:
- **F1:** if the best of M and A is no cheaper than F (CI excluding benefit), the divergence-marking
  rule itself is rejected.
- **F2:** familiar syntax buys nothing on coincident constructs.
- **F3:** alien syntax is needed only where the divergence is checker-invisible. Timing-only code is
  the test.
- **F4:** decay. Re-run at each model generation, and revert to the familiar form when that is safe.

**The Surface Map.** A content-addressed map from each construct to its print form, parse rule,
traps, priors, witnesses and documentation. The map obeys four laws:
- parse∘print = id;
- no two constructs collide;
- trapped forms never parse as valid code;
- witnesses separate Mithril's meaning from every listed prior.

Each edition has one canonical map. Experimental maps live only in the harness.

**Language change protocol.** Any change to the grammar, keywords, Tier 0/1 std signatures or
diagnostic templates goes through six steps:
1. a Surface Map diff;
2. a pre-registered expectation and kill criterion;
3. a screening run;
4. a full run (editions);
5. an ADR;
6. human promotion.

The Forge may propose changes but never promote them. Breaking changes ship `mithc fix` migrations,
because every break becomes stale-prior debt (Zig 0.15; Mojo's correction skill) [G01].

---

## 15. Mithril MultiPL-E

**Status: v0 (≥ 150 tasks at M1 [P5 §10.2, target]); published v1 (M7).** MultiPL-E translates
HumanEval and MBPP prompts and tests from Python into other languages through per-language
translators [R03]. Mithril adds a translator:
- Python signatures and docstrings become Mithril signatures and doc comments.
- Tests run under `mithi` and in the compiled binary.
- Items that need missing features, such as arbitrary-precision integers, are excluded. The exclusion
  list is published, and its rate is itself a breadth measure.

It measures generic writability. Since the solutions are known from pretraining, it mostly tests how
well models carry known solutions into Mithril's surface [inference]. It also calibrates the harness:
MultiPL-E ships a Rust translation, and the Rust arm should reproduce published magnitudes
[inference]. Finally, it is a corpus for §16. Being public, it will leak into training, so it is
never a DR-017 gate. A Verina-style code, spec and proof suite is **later** [R03].

---

## 16. Measuring the subset's rejection rate of idiomatic agent Rust

**Status: v0, from X1, every epoch.** The subset rule's real cold-start tax is how much ordinary
agent Rust it rejects: iterator chains, reference-capturing closures, traits, returned references.

**Corpora.** A: the Rust arm's own solutions (a free byproduct; oracle-passing ones analysed
separately). B: the same families' MultiPL-E Rust completions. C (optional upper bound): mithc's own
agent-written source, which uses lifetimes and traits heavily.

**Instrument.** `mithc lift --from rust --report` (§17), with repair off. Each rejection is classified
either by row (FF-REF, FF-LOCAL, FF-DYN, FF-ASYNC, FF-CELL, FF-UNSAFE, trait features outside the
static subset) or as a *std gap*, meaning a Rust std API with no Mithril
mapping. This keeps language costs apart from library costs.

**Metrics.**
- **R_file:** the share of passing solutions that lift with zero rejections.
- **R_construct:** rejections per solution and per 100 lines, by row.
- **F_auto:** the share of rejections fixed by a Safe lifter fix.
- **C_repair:** the turns and tokens an agent needs to repair the rest while the oracle still passes.
- **Attribution:** the share of Mithril-arm failures whose final state carries a Dc diagnostic.

**Decision rules.**
- `agent.subset_rejection_bound` is 30% of passing Rust solutions [target]. Above it, the Dc list is
  revised before M1 ([ROADMAP §3.2](../ROADMAP.md), amber c). DR-002's revisit trigger reads the same
  parameter.
- A row cited in at least 10% of held-out Mithril-arm failures triggers a review. This applies
  ROADMAP D-01's threshold to every Dc row. The review has three possible outcomes, each recorded in
  an ADR with harness evidence:
  - support the row with Rust meaning, if the calculus allows ([01-language](01-language.md));
  - add a lifter auto-fix;
  - keep the rejection, with a better diagnostic.

---

## 17. The C/Rust lifter

**Status: v0.** At X1, Rust gets a lift-check. At M1, `mithc lift` v0 covers Rust and scalar C. Full
coverage comes by M5. `mithc lift --from c|rust` translates subsets of C11 and Rust into `.mith`. It is the port's first
tool, the engine of the Rust + tooling arm, the instrument of §16, and the cold-start escape hatch:
draft in the parent language, then lift with differential tests. That is the LLMLift and SPEAC
pattern; on UCLID5, SPEAC's Python-subset child language parsed 28/33 programs, against 4/33
three-shot [G01], [R03].

**Rust.** Under the subset rule, in-subset Rust already parses as Mithril with the same meaning, so
lifting is mostly checking [inference]. The lifter parses in a Rust-compatibility mode, inserts
inferred `uses { }` rows on public functions, maps std calls to Mithril std or `std_platform`, and
reports each Dc construct. In the Rust + tooling arm, diagnostics map back to Rust definitions by path
and hash. Grades and claims come from a sidecar spec file owned by the Author role.

**C (Hearth's dialect).** The main mapping rules:

| C | Mithril |
|---|---|
| fixed-width scalar types | Mithril scalars |
| pointer + length parameters | `&[T]` / `&mut [T]` where const-ness and aliasing allow; else a report |
| `restrict` | dropped (exclusive `&mut` implies it) |
| signed overflow (UB in C) | checked arithmetic |
| unsigned wraparound | `wrapping_*` |
| `nearbyintf`, `rintf` (default rounding) | `round_ties_even()` |
| `fmaf` | `mul_add` |
| `a*b + c` | two roundings; FF-FMA noted if the build allowed contraction |
| libm transcendentals in exact contexts | mandatory `cr::` / `canon_v1::` choice unless ADR-0010 names one; else FFI with `nondet(platform)` |
| structs holding pointers | handles or indices (FF-REF report) |
| global mutable state | explicit parameters |
| intrinsics | `Simd<T, N>` methods in `#[target]` functions ([02-compute](02-compute.md)) |
| platform calls | `std_platform` with `uses { io }` (last port stage) |

**Validation.**
- Lifted code is untrusted and enters the ledger graded `assumed`.
- It runs under `mithi` and as emitted C11 against the source, on the source's tests and on generated
  inputs.
- Numeric kernels must also match the cross-binary hash corpus bit for bit
  ([07-hearth-port](07-hearth-port.md)).
- A disagreement returns the first diverging input.
- Each lifted definition records its source hash.

**Kill.** If lifting then annotating shows no TPV gain over writing `.mith` directly on port tasks,
the C lifter becomes a reporting tool. It is kept only for §16 and the Rust + tooling arm.

---

## 18. Lever register: ablations and kill criteria

| Lever | Status | Ablation | Kill or demotion |
|---|---|---|---|
| Tier 0 card | v0 | leave-one-atom-out on screening items (§2); card-size sweep | an atom is deleted only when its removal is shown non-inferior; otherwise it stays, flagged unproven; Tier 1 content that does not improve the Pareto slope moves to Tier 2 |
| Lark grammar in CFG tools | v0 | with vs without the CFG tool (OpenAI) | no syntax-error reduction → docs and masks only |
| FalseFriend diagnostics; grouping | v0 | specific vs generic; grouped vs flat | no gain → generic text; flat list with cascade folding |
| Evidence-listing fixes | v0 | with vs without `invalidates` | no drop in CABW or silently invalidated evidence → rustc's four levels |
| Mandatory `uses` rows ("the signature is the summary") | v0 | rows required and shown vs inferred by mithc and hidden from the agent; TPV on T-XMOD and T-CTRL | no TPV gain → `mithc fix` infers and inserts rows, so agents need not write them; the effect check stays (DR-006); the agent-value claim is withdrawn |
| Evidence status in packs; `ledger why` (N3) | v0 | evidence status and grades in packs on vs off; CABW | no CABW drop → evidence status leaves the default pack and `ledger why` leaves Tier 0; the ledger stays as an integrity control, but N3's agent-value claim is withdrawn |
| Spec escrow (N5) | v0 pilots; enforced v1 | escrowed specs from an Author session vs specs written in the same session; CABW and special-casing on T-CONFLICT | no drop → escrow stays as an integrity control ([03-trust](03-trust.md)), but it is no longer claimed as an agent-quality lever |
| `mithc explain` cost reports (N7) | v0 (M2) | on vs off in schedule-writing variants of T-Q4 and T-NORM (the gate measures); turns to reach the target fraction of roof, and the fraction reached within budget | no gain → out of the default loop and `next`; kept for humans; N7's agent-value claim is withdrawn |
| `Quantity<Unit, Origin>` in agent code | v0 | `Quantity` vs plain `f64` in the reporting code of T-EVICT (bytes, stall); rate of mislabelled or wrong-origin numbers that the arm's checks accept | no reduction → stays as INV-HONEST's type rule ([03-trust](03-trust.md)) but leaves Tier 0's snippets |
| Typed holes, `hole` | v0 | with vs without hole queries | no TPV gain → out of the default loop and Tier 0 [P1 §10] |
| Edit protocol | v0 | vs `str_replace` + format-on-save | no gain → store becomes a derived index; protocol leaves Tier 0 [P1 §10] |
| Packs, closure budgets | v0 | vs agent-driven file reading | no TPV gain → opt-in; budget becomes a lint |
| `propagate` | v0 | vs plain diagnostics on T-XMOD | no gain → opt-in |
| `next` actions | v0 | on vs off | no drop in turns per VP → off by default |
| Handover, resume | v0 | resume pack vs manifest only | pack dropped if successors gain nothing; generated facts stay (integrity) |
| Friction rule, `abandon` | v0 | on vs off; T-CONFLICT | `abandon` removed only if it cuts VP@1 on solvable items without reducing special-casing |
| LSP | by-trigger | LSP vs CLI/MCP | no agent benefit → humans only |
| Constrained decoding | by-trigger | none vs grammar vs grammar + type | errors cut < 15% or VP@1 falls → grammar only [P1 §10] |
| C/Rust lifter | v0 | lift + annotate vs direct writing | no gain → reporting tool only |
| Standalone surface | v0 | Mithril vs Rust, and vs Rust + tooling | DR-017 (§13) |
| Divergence marking | v0 pilot | Surface Lab arms | falsifier F1 (§14) |
| F1-A interface artifacts | v1 (M6) | contamination check, then leave-one-atom-out on screening items; confirmation on the epoch's rotated items, never the permanent holdout | gains that fail on the rotated suite → F1-A frozen ([ROADMAP §8](../ROADMAP.md)) |

---

## 19. Open questions and reviewer notes

**Open questions.**
1. No controlled study of frontier models writing a new general-purpose language from its manual
   exists [R03], [G01]. X1 is that study.
2. No study varies only diagnostic wording [R03], so templates are an F1-A target.
3. Do type masks hurt reasoning in long sessions [R03]? To be measured once triggered.
4. The benefit of content addressing to agents is untested [R04]. §18 tests it through the edit
   protocol's hash anchors and the evidence-status row for packs.
5. The card size for a whole language, rather than an API delta, is unknown [G01]; the sweep answers
   it.
6. σ_ta decides whether 60 held-out items suffice; only X1 can estimate it.

**Reviewer notes.**
- *Verb list.* The outline's canonical list has no test or mutation verb. This document uses
  `check --tests` and `check --mutate`, as [ARCHITECTURE §10.1](../ARCHITECTURE.md) asked, and lists
  `abandon` among the session verbs.
- *Tier 1 size.* "3 modules of 5–15k tokens" could mean per module or in total. G01 and P1 mean the
  total, and so does this document.
- *M1 CABW rule.* DR-017's "CABW > Rust's" has no margin. A point-estimate rule would fire about half
  the time under true equality, whatever n is: a coin-flip kill for the main cold-start decision.
  §13 therefore operationalises it as a one-sided test (the 90% lower confidence bound of the
  difference must exceed 0), with ≤ 10% kill probability at equality and a published curve. The
  threshold itself is unchanged. ROADMAP §5 (M1) now records this operationalisation; DR-017 should
  record it too before pre-registration. The Owner may still choose a fixed margin of about 2 points
  instead, but only before pre-registration, never after.
- *Error codes.* P1's and P5's examples used `E0412`, which is rustc's "cannot find type": a false
  friend in diagnostics. Mithril uses 01's mnemonic codes (`E-FF-SUM`) and never rustc's numbers
  (§5).
- *DR-013 and batch fixes.* If `fix --safe` bulk-applied DR-013's Safe fix (`canon::sum_seq`), it
  would silently pick a sequential order where NUMERICS wants `sum16`. §5 therefore excludes class-D
  FalseFriend fixes from batch application. This refines DR-013 without changing it.
- *Class D.* The outline's DR-002 defines D as "new, keyword-led". P1 and RV D3-i used D for
  "checker-invisible divergence". §4 and §14 reconcile the two: an invisible divergence traps the
  Rust form (Dc) and adds a D form. RV's pilot labels (D1–D5) keep the older sense.
- *Table ownership.* The outline gives the false-friend table to this document, and
  [01-language §2.5](01-language.md) also builds it. To keep one set of IDs, this document defers to
  01's table.
- *Surface Lab budget.* Resolved: ROADMAP §5 (M1) and §10 now carry the D1–D5 pilot alongside M1, at
  about 390 episodes per arm per construct [RV: D3-i, inference].
