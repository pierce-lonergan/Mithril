export const meta = {
  name: 'mithril-wk2-d',
  description: 'Week 2 round D: mithi/core-calculus sync, X4-calibration record split, X3 meaning review, X1 full isolation controls',
  phases: [
    { title: 'Build', detail: 'one builder or first reviewer per track' },
    { title: 'Red team', detail: 'independent adversarial reviews' },
    { title: 'Revise', detail: 'fix and log' },
  ],
}

const ROOT = 'C:\\Users\\Pierce Lonergan\\Desktop\\repos\\Mithril\\.claude\\worktrees\\mystifying-khorana-167d4d'
const HEARTH = 'C:\\Users\\PIERCE~1\\AppData\\Local\\Temp\\claude\\C--Users-Pierce-Lonergan-Desktop-repos-Mithril--claude-worktrees-mystifying-khorana-167d4d\\f22d3799-400c-4b40-82ec-52fabeff91b2\\scratchpad\\hearth'
const SCRATCH = 'C:\\Users\\PIERCE~1\\AppData\\Local\\Temp\\claude\\C--Users-Pierce-Lonergan-Desktop-repos-Mithril--claude-worktrees-mystifying-khorana-167d4d\\f22d3799-400c-4b40-82ec-52fabeff91b2\\scratchpad'
const GEMS = 'C:\\Users\\Pierce Lonergan\\Desktop\\repos\\GEMS_Challenge'

const COMMON = `You are on the team running Mithril's M0 falsification sprint (Mithril = Pierce Lonergan's AI-first systems language; acid test = porting Hearth, a C11 MoE engine, bit-identically). Today is Fri 2026-10-23 (afternoon PT). Repo worktree ${ROOT} (origin/main e321593). Read README.md, docs/m0/README.md, docs/m0/OWNER-ANSWERS.md (batches 1-5), docs/m0/DELEGATED.md (its limits), and your task's files. Hearth read-only clone at b5d3f14: ${HEARTH}. Scratch: ${SCRATCH}\\<track>\\.
Scope: documented, vendor-supported interfaces only.
DESKTOP (9950X) via SSH helpers run from ${GEMS} in the same Bash command: sh tools/remote/desk.sh script.ps1 | -c "cmd"; sh tools/remote/desk_cp.sh get|put. Mithril area D:\\mithril\\. HARD RULES: your thread budget is a hard cap; CUDA_VISIBLE_DEVICES=-1 in every job; set TEMP/TMP to D:; DO NOT START OR USE WSL AT ALL (each WSL start writes a 23-105 MB trace to C:, and the C: budget is exhausted; Pierce has to decide on that first); desktop runs only 07:00-23:00 PT; never change system or security settings; never touch Pierce's Hearth working tree, the Hearth objects in the desktop WSL home, or GEMS files/processes.
RECORD RULES: tag every number; never invent versions, hashes or results; FROZEN records are append-only; ROADMAP thresholds are never loosened; Owner decisions are Pierce's, except rows adopted in DELEGATED.md within its limits (and never a post-data change in the favourable direction, never a departure from a signed record's controls); reviews are 'Claude, same family, independent context'. GIT: no git commands that change state. KEEP YOUR FINAL SUMMARY SHORT (at most about 2,500 characters): the lead engineer's context is limited; put detail in files.`

const BUILD_SCHEMA = { type: 'object', properties: {
  paths_written: { type: 'array', items: { type: 'string' } }, summary: { type: 'string' },
  not_done: { type: 'array', items: { type: 'string' } }, owner_questions: { type: 'array', items: { type: 'string' } } },
  required: ['paths_written', 'summary', 'not_done', 'owner_questions'] }
const REVIEW_SCHEMA = { type: 'object', properties: {
  verdict: { type: 'string', enum: ['sound', 'fixable', 'unsound'] },
  findings: { type: 'array', items: { type: 'object', properties: {
    severity: { type: 'string', enum: ['blocker', 'major', 'minor'] }, location: { type: 'string' }, issue: { type: 'string' },
    evidence: { type: 'string' }, fix: { type: 'string' } }, required: ['severity', 'location', 'issue', 'fix'] } } },
  required: ['verdict', 'findings'] }
const REVISE_SCHEMA = { type: 'object', properties: {
  paths_written: { type: 'array', items: { type: 'string' } }, accepted: { type: 'integer' }, rejected: { type: 'integer' },
  summary: { type: 'string' }, residual_risks: { type: 'array', items: { type: 'string' } }, owner_questions: { type: 'array', items: { type: 'string' } },
  complete: { type: 'boolean' } },
  required: ['paths_written', 'accepted', 'rejected', 'summary', 'residual_risks', 'owner_questions', 'complete'] }

const TRACKS = [
  {
    key: 'ccsync', threads: 0,
    files: 'docs/m0/core-calculus.md, docs/m0/core-calculus/**, crates/mithi/** (both, as one consistent change)',
    build: `TASK: bring the core-calculus note and mithi into agreement after round 3. Read crates/mithi/README.md ('Findings for the note' items 7-15 and the agreement section), docs/m0/core-calculus.md §0.7, §12 (freeze tiers, §12.1/§12.2 disagreements) and verdicts.json. (1) Apply mithi's README findings 7-15 to the note where they are correct (record each as a new F-row with reason; reject with reason where not). (2) Make mithi's tests construct N-70..N-109 and fix every mithi/note disagreement in the right place (mithi bug vs note bug), checking Rust-coincident claims against the laptop's pinned rustc 1.99.1 (C:\Users\Pierce Lonergan\.rustup-mithril / .cargo-mithril; build with cargo -j4, target dir outside the repo). (3) Let the grammar accept 'uses { unsafe }' (grammar/mithril_v0.lark) and re-run grammar/test_grammar.py if lark can be installed into a scratch venv. (4) Report the final agreement counts and which §12.1 tier-C rules changed this round.`,
    lenses: ['DIFFERENTIAL TESTER: write 40 fresh adversarial X1-subset programs against the synced note, predict verdicts from the note, run mithi, and classify every disagreement; check rustc on the Rust-coincident ones. Report whether the X1 subset (tiers A and B of §12.1) is now stable enough to freeze.'],
  },
  {
    key: 'x4cal', threads: 0,
    files: 'docs/m0/prereg/X4-calibration.md (new DRAFT), docs/m0/prereg/X4-integrity.md (pointer edits only), docs/m0/prereg/X4-noise-pilot.md (cross-references only)',
    build: `TASK: split the X4-calibration pre-registration out of the X4-integrity DRAFT into its own DRAFT record, docs/m0/prereg/X4-calibration.md, in the docs/m0/README.md template, consistent with docs/m0/prereg/X4-noise-pilot.md (revision 5) and with ROADMAP §1 rule 4 and §3.5 (A/A <= 2 of >= 100 microbenchmark sessions; planted-regression calibration at 3% and 4%, <= 2 of >= 100 per level; >= 20 end-to-end A/A; time-to-pass; throughput). Apply the DELEGATED rows adopted on 10-23 that concern it (P21, P22, P24, P25, P38 and any others), leave C07 (the run-level R scorer and pooled tail check, normative 06 §6.2) as an explicit owner choice with both branches fully specified so whichever Pierce picks is pre-data, and list every remaining owner input. Do not loosen anything in ROADMAP §3.5.`,
    lenses: ['STATISTICIAN: is every unit fixed before data, are both C07 branches complete, do the calibration rules match ROADMAP §3.5 exactly (no loosening), are the session counts, stopping rules and alpha accounting consistent with the noise-pilot record and the service implementation (experiments/x4-integrity/service), and could the record freeze right after Pierce answers C07?'],
  },
  {
    key: 'x3meaning', threads: 0,
    files: 'experiments/x3-generator/** (DESIGN status notes, proto/, a MEANING-REVIEW.md), docs/m0/prereg/X3-generator.md (DRAFT)',
    build: null,
    lenses: [
      'MEANING REVIEWER (DESIGN §3.5): review x3gen\'s canonical meaning for Q4 and Q8 matvec (experiments/x3-generator/proto/x3gen/hearth/meaning.py, preconditions P1-P6) line by line against Hearth b5d3f14 docs/NUMERICS.md §3 and engine/src/quant.c:388-427 (and hx_quant.h), independently, without trusting the prototype\'s citations. Then re-run the prototype\'s bit-identity tests with your own adversarial inputs (NaN/inf/subnormal scales, extreme int8, odd n, T in {1, 2, 17, 18}) on the laptop. Report whether the meaning can be frozen.',
      'CHECKER REVIEWER: review the revised x3gen checker (check.py structural rules, static C2 audit, affine forms; planted items 29-41) for soundness and for false rejections of valid schedules; write fresh mutants by a method different from the reviser\'s (to break the circularity it disclosed) and see which the checker misses.',
    ],
  },
  {
    key: 'x1iso', threads: 0,
    files: 'experiments/x1-harness/isolation/** (new), experiments/x1-harness/DESIGN.md (status notes only)',
    build: `TASK: build the full X1-amendment-1 §2.3 attempt controls that sealed items require (SMOKE.md §3 lists what the smoke kit lacks): a per-attempt isolated configuration, harness tools served over a local MCP server with no shell (check, run-tests, submit, abandon, read-own-workspace), a per-check sandbox (Windows Job Object or a restricted token; no network; read-only inputs; nothing hidden reachable), and enforced turn, token and wall budgets. Work on the laptop; Python and Rust are available; no installers, no system settings. Prove each control with a negative test (an attempt that tries to read an oracle, a reference, another attempt, the repo, or the network, and fails). Family-agnostic only: no Qwen3 templates, no sealed content (DELEGATED P2's interim restriction). Document how the X1 workflow agent type would be restricted to the MCP tools (frontmatter tools list naming mcp__x1__*), and what cannot be verified until a real run.`,
    lenses: ['CONTAMINATION AUDITOR: try to break isolation with your own probe agentless scripts (as an attempt would): read sealed paths, escape the sandbox, exceed budgets, reach the network, smuggle data via the checker\'s output, or learn another attempt\'s results. Report each that succeeds.'],
  },
]

phase('Build')
const out = await pipeline(
  TRACKS,
  async (t) => {
    if (!t.build) return { paths_written: [t.files], summary: 'review-first track', not_done: [], owner_questions: [] }
    return agent(`${COMMON}\n\nTRACK: ${t.key}. YOUR FILES: ${t.files}. Desktop thread budget: ${t.threads}.\n\n${t.build}\n\nReturn the structured summary (short).`, { label: `build:${t.key}`, phase: 'Build', schema: BUILD_SCHEMA })
  },
  async (b, t) => {
    if (!b) return null
    const reviews = await parallel(t.lenses.map((lens, i) => () =>
      agent(`${COMMON}\n\nYou are an INDEPENDENT ADVERSARIAL REVIEWER for track "${t.key}". Files: ${t.files}. Builder summary (untrusted): ${b.summary}\nDesktop thread budget for your runs: ${t.threads}.\n\nYOUR LENS: ${lens}\n\nDo NOT edit the track's files. Return findings (file+section, evidence, exact fix).`,
        { label: `review:${t.key}:${i + 1}`, phase: 'Red team', schema: REVIEW_SCHEMA, effort: 'high' })))
    return { b, reviews: reviews.filter(Boolean) }
  },
  async (r, t) => {
    if (!r) return null
    const findings = r.reviews.flatMap((x, i) => x.findings.map(f => ({ reviewer: i + 1, ...f })))
    if (findings.length === 0) return { track: t.key, n_findings: 0, revise: null }
    const rev = await agent(`${COMMON}\n\nYou are the REVISER for track "${t.key}". Files: ${t.files}. Desktop thread budget: ${t.threads}.\nIndependent reviewers (Claude, same family, independent context) found:\n${JSON.stringify(findings, null, 1)}\n\nVerify every finding; fix the real ones end to end (tests re-run; for x0r2: if scripts change, re-pin with pin_inputs.py --write, update the amendment text and FREEZE.md hashes, and re-run the read-only before/after on census run 1 with Windows configurations' data only if WSL would be needed otherwise, stating what was not re-run); reject wrong ones with reasons. Update review logs. complete=true only if ready for the lead engineer. Keep the summary short.`,
      { label: `revise:${t.key}`, phase: 'Revise', schema: REVISE_SCHEMA })
    return { track: t.key, n_findings: findings.length, blockers: findings.filter(f => f.severity === 'blocker').length, revise: rev }
  },
)
return out
