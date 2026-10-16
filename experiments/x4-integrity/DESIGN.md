# X4 — the evaluator-integrity kit (design overview)

**Track:** x4-integrity. **Status:** DESIGN (implementation follows next), revision 2. **Date:** 2026-10-16. **Author:** X4 track (Claude, same-family independent-context; see the review log below).
**Primary anchor:** ROADMAP §3.5. This file is the index; the detail is in the sibling files. Every number carries an evidence tag (**[M]/[D]/[S]/[G]/[inference]/[target]**; dossier numbers keep their label).

X4 tests the judge **before there is anything to hack** [P4 §10]. If the judge (measurement, sandbox, gate) can be gamed, the Forge halts until it is redesigned (ROADMAP §3, X4 row; outcome **HALT-F**, §4). Every part of X4 is useful to C-Hearth whatever happens to Mithril (ROADMAP §3.5). X4 does **not** kill the language.

## The pieces and where they live

| Piece | File | What it delivers |
|---|---|---|
| Measurement service v0 | [MEASUREMENT-SERVICE.md](MEASUREMENT-SERVICE.md) | C harness + Rust orchestrator. The in-process clock is precise; the **out-of-process integrity bracket** (orchestrator wall clock, job CPU accounting, orchestrator rehash of an output section it owns) is what makes it trustworthy. Full join plus a **thread census** and post-`t1` CPU rule; per-thread MXCSR checks; poisoned allocations; explicit environment and fresh scratch per run; hardware fingerprint; randomised ABBA/BAAB interleaving (ROADMAP's "ABAB", made precise) behind a load gate and a **per-run start-state gate**; voids split into hygiene / statistical / integrity with blind void decisions and survivorship-proof tally rules; CCD pinning by job affinity/priority; quiet-machine profile as **commands for Pierce** that the service **verifies and refuses to run** without; the e-processes with **one named gate scorer**, a revised kill test, the mandatory **tail check**, α per attempt; σ-pilot rules for every data-dependent constant; `Quantity<Unit, Origin>` schema; `mithc profile measure` |
| Sandbox | [SANDBOX.md](SANDBOX.md) | Job Object (limits incl. affinity/priority, no child processes); **LPAC/AppContainer mandatory for every untrusted workload, X3 kernels included**; separate low-privilege user and a firewall outbound block (commands for Pierce; `-LocalUser` corrected to SDDL); sealed data on **no openable path** plus a post-session rehash; a **refusal table**; a self-test with a **positive-control** network probe, broker probes and alternate-name probes |
| Planted-hack suite | [HACK-SUITE.md](HACK-SUITE.md) | Batch (a): the 12 ROADMAP §3.5 hacks + 18 further + **11 added in revision 2** (a3b, a6b, a8b, a10b, a11b, a15b, a15c, a31–a34), each with a declared stage; an **X4 detector table** (stand-ins for a5, a7, a9, a14, a16; a22–a24 excluded as not testable at X4, never a ROADMAP-named hack). Batch (b): blind, different-family Adversary after the kit is hash-frozen — **only Claude is available now, so (b) waits for D0-10**. Gate: 100% caught at/before declared stage (IF-5) |
| F1-sim policy Forge | [F1-SIM.md](F1-SIM.md) | Eviction/prefetch candidates on a scratch `hearth.sim` behind an `hx_policy` shim; objective **NVMe bytes/token, never hit rate**; MIN-bytes oracle validated against brute-force OPT first; an **independent second byte counter** for every `timing_blind` candidate; replay pruning only for `timing_blind` policies with an exhaustive audit; benefit gate = ≥ 10% fewer bytes/token than LRU in the **primary niche (1 GiB, prefetch off)** on **truly sealed traces** (the in-repo trace is visible validation only); all SIMULATED and conditional on simulator fidelity until M4 |
| Tombstone import + revisit prototype | [TOMBSTONES.md](TOMBSTONES.md) | Import of lookahead-depth-4 and ADR-0004 (niche-scoped) + all 27 DECISIONS §4 tombstones; `mithc revisit` prototype; the gate's trigger tests incl. irrelevant perturbations; **§6: six proposed design tombstones for ideas this revision rejected**, all parsing and firing as specified |
| Calibration statistics | [stats/](stats/) ([x4_calibration.py](stats/x4_calibration.py), [stats/README.md](stats/README.md)) | Exact binomial OC [D] plus correlated-session sensitivity; the drafted e-process study [S]; revision studies [S] (outlier-rate grid, R vs S scorers, revised kill, tail check, sentinels, trend tests, planted-level clip bias); quiet hours [D from G]; pinned hex constants and a golden wealth path for the bit-identical differential test |
| Draft pre-registration | [../../docs/m0/prereg/X4-integrity.md](../../docs/m0/prereg/X4-integrity.md) | DRAFT prereg in the template; gate/kill copied from ROADMAP §3.5 and made precise; every unit and constant defined; the full review log; nine owner questions |

Supplementary (validation, scratch-grade Python, `python -I`): [revisit_proto.py](revisit_proto.py), [revisit_acceptance.py](revisit_acceptance.py).

## The gate and kill (copied from ROADMAP §3.5)

**Gate** — all required:
- 100% of both hack batches caught at or before their declared stage (IF-5).
- **A/A calibration (superiority null):** across ≥ 100 identical-binary microbenchmark sessions, the superiority e-process reaches 20 in **≤ 2** of them [target]. X4 makes this more precise: it must hold under the gate scorer R **and** the symmetric scorer S; a pooled mean test and the void-rate bound can make it amber.
- **Planted-regression calibration (non-inferiority null):** `hearth-c-ref` against itself with an injected 3% and (separately) 4% slowdown; the non-inferiority e-process must reach 20 in **≤ 2 of ≥ 100** sessions per level [target]. X4 injects the slowdown as proportional extra work and requires a premise check that the level really is in the null.
- **Time-to-pass at true parity:** the A/A sessions also run the NI e-process; median and p90 time-to-20 published per run type (censored at the horizon; "> N" when beyond it).
- End-to-end run types get **≥ 20 A/A sessions** [target]; their gates rest on the microbenchmark calibration plus per-session A/A sentinels.
- Throughput published as candidates per quiet hour at MDE 5% and 2%.
- The lookahead tombstone fires only on `nvme_read_gbps > 12.0 || drives ≥ 2 || tier_exists(vram)`; ADR-0004's revisit, once encoded, produces niche-scoped verdicts matching the measured winners; **neither fires on the pre-registered irrelevant perturbations**.
- The prune pilot reproduced with **zero audit violations** (41/32/26/16% per cache size, 66% jointly, SIMULATED [RV: D3-ii]).

**Kill (HALT-F):** any accepted planted hack stops all Forge work until the evaluator is redesigned and the suite passes again. This does **not** kill the language. A failed A/A calibration bars every superiority gate; a failed planted-regression calibration bars every parity gate, until the cause is fixed and the calibration passes on fresh sessions (D0-8, D-22).

## What X4 established in design (early signal, revision 2 numbers)

- **ROADMAP's four A/A [inference] figures are exactly right** [D]: `≤ 2/100` passes a true 1% rate with 0.9206 (ROADMAP 0.92), 5% with 0.1183 (0.12), 8% with 0.0113 (0.01); `≤ 5/100` passes 8% with 0.1799 (0.18). The binomial OC assumes independent sessions; with sessions sharing nights (correlation 0.05, 4 × 25) the pass probability at 5% rises to 0.24 [D].
- **The non-inferiority e-process behaves as pre-registered** [S]: at a planted 3%/4% regression it reaches 20 within the amber horizon in **≤ 0.7%** of sessions (drafted cells) and ≤ 1.0% across outlier rates up to 10% (R scorer). At true parity it reaches 20 in a median of 9 blocks (σ_d 2%) / 23 (σ_d 4%), with the share within N between 0.882 and 0.960 at σ_d 2% depending on scorer and outlier rate, falling to 0.311 at a 5% outlier rate.
- **The drafted kill test was unreachable at σ_d 2%** (maximum wealth 6.1 within N = 12 [D]); revision 1's "full power at a 10% regression" held at σ_d 4% only. The revised kill test (outliers in the candidate's favour, headroom clip, θ 0.8, continued across the two N-sessions of an unchanged binary) has no false kills at parity up to 10% outliers and power 0.992 at a 10% regression within 2N at σ_d 2% [S] — but **a kill at σ_d 2% still needs both sessions** (owner question 5).
- **The A/A rule tests harness label symmetry, not drift**: with identical binaries and randomised order, d is conditionally symmetric whatever the drift (the AR(1) rows give 0.0000 [S]). A 2% label asymmetry is caught in 0.2% of sessions at σ_d 2% and 50% at 4% [S]; the pooled mean test adds power 0.81 against a 0.2% asymmetry [D].
- **The tail check of 06 §6.2 is weak as literally written** (credit for a rare-stall candidate falls only 0.130 → 0.110 at σ_d 2%); pooled with screening at a 5% level it falls to 0.017, with ≈ 2–7% residual [S].
- **Quiet hours exceed ROADMAP §10 at both σ_d ends** (ROADMAP-comparable 111.2 h vs 60 at σ_d 2%; 368.8 h vs 215 at 4%) [D from G]; a reconstruction with n instead of N reproduces ROADMAP's figures (60.9 / 223.4 h) [D].
- **The 06 §7.2 trigger grammar is implementable**: 53 of 54 DECISIONS triggers parse; the one failure is a genuine grammar gap (hyphenated fact arguments like `INV-DET-1`), an owner question. The six new X4 tombstones parse and fire as specified [S/D].

## Dependencies and honest limitations

- **D0-7** (Forge authority; unattended runs) — needed for the quiet-window scheduler lock and the unattended noise pilot; X4 promotes nothing.
- **D0-9** (Owner key management) — the gate and measurement facts are signed; without D0-9, X4's facts are provisional.
- **Quiet windows / D0-8 / D0-10** — the calibrations need ≈ 122–403 quiet hours depending on σ_d and the end-to-end stopping rule [D from G]; D0-10 names the families batch (b) needs and approves the budget; D0-8 is the measurement host.
- **Only Claude is available now:** batch (b)'s different-family Adversary and every independent review are logged **same-family, independent-context** until D0-10 — the weaker label every X4 record carries ([m0/README](../../docs/m0/README.md)).
- **Unverified on the box:** LPAC/AppContainer with large pages and direct I/O; the readability of the start-state counters by a standard user; DNS behaviour inside the sandbox; the `-LocalUser` SDDL form. Each has a refusal or a check that fails closed.
- **Design only; implementation follows next.** The scripts validate the designs; the F0 C/Rust service, the sandbox and the M3 revisit engine are built later.

Where work proceeds before an Owner decision, it is marked **provisional, pending D0-x** and kept reversible. No D0 decision is presented as taken.

## Review log

The full log — reviewer lens, family, every finding with its disposition — is in the prereg, [§12](../../docs/m0/prereg/X4-integrity.md#12-review-log-independent-reviewers-with-model-family). Summary of the 2026-10-16 round: two reviewers, **Claude (same family as the author; independent context)**; reviewer 1 (evaluator-integrity / adversarial lens) 17 findings (12 major, 5 minor), reviewer 2 (statistics / calibration lens) 19 findings (10 major, 9 minor); **36 findings (22 major, 14 minor), 36 accepted (7 of them with a modified fix, each explained in the prereg log), 0 rejected**. Every finding was verified against the sources (the Hearth clone at b5d3f14, ROADMAP, 06-forge, COST.md, and a re-run of revision 1's script) before it was accepted.
