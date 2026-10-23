export const meta = {
  name: 'mithril-wk2-c',
  description: 'Week 2 round C: review X0-A1 r2, review X4 pilot rev 4, prepare the X2 record for freeze with the census scope, build the sitting-2 packet',
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

const COMMON = `You are on the team running Mithril's M0 falsification sprint (Mithril = Pierce Lonergan's AI-first systems language; acid test = porting Hearth, a C11 MoE engine, bit-identically). Today is Fri 2026-10-23 (afternoon PT). Repo worktree ${ROOT} (origin/main 94adcf3). Read README.md, docs/m0/README.md, docs/m0/OWNER-ANSWERS.md (batches 1-5), docs/m0/DELEGATED.md (its limits), and your task's files. Hearth read-only clone at b5d3f14: ${HEARTH}. Scratch: ${SCRATCH}\\<track>\\.
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
    key: 'x0r2', threads: 2,
    files: 'experiments/x0-census/scripts/** (x0_loops.py, x0_census.py, judge.py, tests), class/frozen_inputs.json, FREEZE.md, results/tooling_fix_A1/** and the DRAFT amendment text in results/tooling_fix_A1/AMENDMENT-X0-A1.md (create it from the text in results/tooling_fix_A1/README.md or the x0fix track notes if missing). NOT the record docs/m0/prereg/X0-census.md (the lead engineer appends the amendment).',
    build: null,
    lenses: [
      'INDEPENDENT REVIEWER of X0-A1 revision r2 (commit c069600): about 120 changed lines in x0_loops.py (escape reachability rule, the unscreened test, frozen descriptive fields), x0_census.py and judge.py (both_ways). Hunt for any path where a real accumulator split could be silently cleared (neither flagged nor listed unscreened), for both_ways mis-evaluating the frozen reading, and for schema gaps. Run all unit tests on the laptop and write adversarial synthetic streams. If a desktop check is needed, use Windows configurations only (no WSL), at most 2 threads. Also check that results/tooling_fix_A1/ and the amendment text contain the census outputs a fresh re-deriver must not see, and that a data-free X0-A1.1 text exists separately.',
    ],
  },
  {
    key: 'x4rev4', threads: 3,
    files: 'experiments/x4-integrity/service/**, experiments/x4-integrity/IMPLEMENTATION.md, experiments/x4-integrity/pilot/**, docs/m0/prereg/X4-noise-pilot.md (DRAFT)',
    build: null,
    lenses: [
      'INDEPENDENT REVIEWER of X4 noise-pilot revision 4 (commit 94adcf3): re-run the dry night on the desktop (at most 3 threads, Windows only, no WSL), check that PILOT mode cannot run with values differing from the record, that sensors and void rules are blind to outcomes, that cut/void/stop paths are honest, and that the record is complete enough to FREEZE: every unit and rule fixed before data, every open choice either answered by Pierce (OWNER-ANSWERS batch 3 accepted the C01/C02/C25/D0-7a defaults) or listed for him. Produce a short list of exactly what Pierce must do himself before the first night (exact commands; nothing the agents may run).',
    ],
  },
  {
    key: 'x2freeze', threads: 2,
    files: 'experiments/x2-semantics/** and docs/m0/prereg/X2-checker.md (DRAFT)',
    build: `TASK: bring X2 to a freezable state now that X0's census defines its table scope. Read docs/m0/prereg/X2-checker.md, experiments/x2-semantics/TABLE-SCHEMA.md, FUZZ-DESIGN.md, RULES.md, MUTANTS.md, harness/README.md, proofs/README.md, experiments/x0-census/results/x2_scope.json and census.json (census run 1 is X0 data; using its union as X2's scope list is the registered flow; note that X0's own verdict is not yet final, so X2 cites census run 1 by hash and states it will re-scope if the X0 re-run changes the union), and DELEGATED.md rows that answered X2 questions (P9, P10, P14, P28-P34, P62). Do: (1) absorb the census union into the table with semantics/census_absorb.py: every census iclass/iform that the dispatched variants use gets an entry or an explicit out-of-scope reason; add entries for the FP-sensitive iclasses the census found beyond the intrinsic-implied set; (2) apply the B6 reading fix (DIVSS-class denormal/zero divisor sets ZE only on Zen 5 and Bochs) as a table correction with its evidence; (3) regenerate stubs and rebuild the harness on the desktop (Windows/MSVC, at most 2 threads, no WSL); run self-tests and the dev smoke only (no pre-registered budget); (4) update docs/m0/prereg/X2-checker.md so every unit and rule is fixed (applying the adopted DELEGATED rows), the per-iclass vector budget is final, and the record is ready to FREEZE; list anything that still needs Pierce.`,
    lenses: [
      'X2 FREEZE-READINESS REVIEWER: is the table now complete for the census union (every FP-sensitive census iclass has a semantics entry with evidence), are the new entries correct per the SDM (spot-check with your own vectors through semantics/selftest), is the B6 correction justified, and is docs/m0/prereg/X2-checker.md free of undefined units, with no ROADMAP §3.3 threshold loosened and every adopted DELEGATED row applied faithfully? Run the selftests on the laptop.',
    ],
  },
  {
    key: 'sitting2', threads: 0,
    files: 'docs/m0/sittings/2026-10-25/** (new: PACKET.md), docs/m0/OWNER-QUEUE.md (status pointers only)',
    build: `TASK: write the packet for sitting 2 (Sunday 2026-10-25, evening), aimed at about 90 minutes, readable in 10. Read OWNER-ANSWERS.md (batches 1-5), DELEGATED.md, OWNER-QUEUE.md, docs/m0/sittings/2026-10-18/PACKET.md and HOW-TO-SIGN.md, docs/m0/sittings/2026-10-23-chat/SIGNATURES.md, experiments/x0-census/results/tooling_fix_A1/, docs/m0/prereg/X4-noise-pilot.md, experiments/x1-harness/smoke/SMOKE.md. Agenda, in order, each item with a one-paragraph summary, options, recommendation and the exact line he signs or answers: (1) create the signing key (HOW-TO-SIGN steps 1-2) and re-sign every interim item with signed tags (list them: R1-R10, the X0 record 152fa33, X1-amendment-1 ac751b8, batch 5's approval); (2) review the DELEGATED.md rows adopted on 10-23 (59 rows): accept all, or name the ones to reverse; (3) X0-A1: which reading governs P3(c) for X0's verdict, the amended one or the frozen one (explain neutrally: the amendment removes flags, the favourable direction, and was defined post-data; both are reported); (4) the three decisions reserved to him: Q18 template author, Q17 Qwen3 as a different family, C07 normative 06 §6.2; (5) the X3/X4 priority-class recommendation; (6) the X4 noise-pilot record (sign if FROZEN by then) and his pre-night actions; (7) the WSL trace problem on the desktop's C: (WSL writes a 23-105 MB trace per VM start under %LOCALAPPDATA%\\Temp\\DiagOutputDir\\RdClientAutoTrace; about 550 MB so far, over the 500 MB rule): options are (a) Pierce sets [wsl2] guiApplications=false in his .wslconfig and deletes the traces, (b) X0's Linux configurations C and D move off WSL, (c) accept and delete periodically; recommend one; (8) the X1 smoke-run idle window. Put everything else under 'Deferred'.`,
    lenses: [
      'OWNER ADVOCATE: is the packet minimal, neutral and signable in about 90 minutes; does it ask Pierce only for what he alone can decide; are the delegated rows presented so he can actually review them (grouped, with the few that matter flagged); is the X0-A1 question framed neutrally; are the pre-night and WSL actions exact commands for him, never for agents?',
    ],
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
