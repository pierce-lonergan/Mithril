export const meta = {
  name: 'x1-smoke-batch',
  description: 'X1-amendment-1 6.2 smoke run: one wave (5 attempts) of x1-subject attempts on public development items',
  whenToUse: 'Only by the lead engineer, one launch per wave, between plan readings, as experiments/x1-harness/smoke/SMOKE.md says.',
  phases: [
    { title: 'Attempts', detail: 'x1-subject attempts, at most 5 at a time; no other agent runs in this workflow' },
  ],
}

// X1 smoke-run workflow. This file in the repository is the TEMPLATE: `python x1smoke.py prepare`
// writes <run root>/smoke_workflow.js with the plan (cards, task packets, attempt order, harness
// commands) inlined on the PLAN line below. Launch that instance once per WAVE of 5 attempts, from a
// controller session whose working directory is the run root (SMOKE.md 4.2):
//   Workflow({scriptPath: '<run root>/smoke_workflow.js',
//             args: {run_id: '<run id>', batch: 1, wave: 0, account_quiet: true}})
//   batches 2-4 have waves 0-3 and add gate_sha256: '<the 64-hex gate_sha256 that x1smoke.py gate
//   printed with CONTINUE after the previous batch>'.
//   A replacement wave re-runs infrastructure failures of the same batch (record 2.3 item 7):
//   args: {run_id, batch: k, replace: ['<attempt id>', ...], account_quiet: true, gate_sha256 (k > 1)}.
// After an interruption, relaunch only with resumeFromRunId of the same workflow run; never relaunch
// a wave fresh (its attempts would answer attempt_ended and spend tokens the gate does not count).
// The script runs subject attempts only. It cannot read files, clocks or plan usage (the workflow
// runtime has none of them), so the plan readings, the P2 checks before each wave, the waits and the
// 6.2 decision happen outside it, between launches (SMOKE.md), and it returns its results instead of
// writing them.

const PLAN = null; // @@PLAN@@

if (PLAN === null) {
  throw new Error('This is the template. Run `python x1smoke.py prepare` and launch <run root>/smoke_workflow.js.')
}

const A = args || {}
const spec = PLAN.batches.find(b => b.batch === A.batch)
if (!spec) throw new Error(`args.batch must be one of ${PLAN.batches.map(b => b.batch).join(', ')}`)
if (A.run_id !== PLAN.run_id) throw new Error(`args.run_id must be "${PLAN.run_id}"`)
if (A.account_quiet !== true) {
  throw new Error('args.account_quiet must be true: the lead engineer confirms the account is quiet (SMOKE.md, step Q)')
}
if (spec.batch > 1 && !/^[0-9a-f]{64}$/.test(String(A.gate_sha256 || ''))) {
  throw new Error(`batch ${spec.batch} needs args.gate_sha256: the gate_sha256 that x1smoke.py gate printed with CONTINUE after batch ${spec.batch - 1}`)
}

let todo
let mode
const nWaves = Math.ceil((spec.to - spec.from) / PLAN.wave_size)
if (A.replace !== undefined && A.replace !== null) {
  if (A.wave !== undefined && A.wave !== null) throw new Error('give args.wave or args.replace, not both')
  if (!Array.isArray(A.replace) || A.replace.length === 0 || A.replace.length > PLAN.wave_size) {
    throw new Error(`args.replace must be a list of 1-${PLAN.wave_size} attempt ids of batch ${spec.batch} that did not return`)
  }
  todo = A.replace.map(id => {
    const orig = PLAN.attempts.find(a => a.id === id)
    if (!orig || orig.batch !== spec.batch) throw new Error(`${id} is not a planned attempt of batch ${spec.batch}`)
    const r = PLAN.replacements[id]
    if (!r) throw new Error(`no replacement attempt for ${id}`)
    return r
  })
  mode = 'replace'
} else {
  if (!Number.isInteger(A.wave) || A.wave < 0 || A.wave >= nWaves) {
    throw new Error(`args.wave must be an integer 0..${nWaves - 1} for batch ${spec.batch}`)
  }
  const lo = spec.from + A.wave * PLAN.wave_size
  todo = PLAN.attempts.slice(lo, Math.min(spec.to, lo + PLAN.wave_size))
  mode = 'wave'
}

function section(title, text) {
  return `== ${title} ==\n${String(text).trimEnd()}\n`
}

function buildPrompt(at) {
  const t = PLAN.tasks[at.task]
  const arm = t[at.arm]
  return [
    `X1 SMOKE ATTEMPT. Attempt id: ${at.id} (run ${PLAN.run_id}; development item ${at.task}; arm ${at.arm})`,
    '',
    section('HARNESS COMMANDS (run with Bash, copied exactly)',
      `check:          ${at.cmd} check\n` +
      `check + tests:  ${at.cmd} check --tests\n` +
      `submit:         ${at.cmd} submit\n` +
      `abandon:        ${at.cmd} abandon 'short reason'\n` +
      `${PLAN.abandon_note}\n` +
      `Your solution file (create it with Write; it is the only file you may write):\n  ${at.solution_path}`),
    section('ARM CARD', PLAN.cards[at.arm]),
    section('SHARED DOMAIN NOTES', PLAN.preamble),
    section('TASK BRIEF', t.brief),
    section('PRELUDE (read-only; the checker compiles it together with your file)', arm.prelude),
    section('STUB (the required signature; write your file from it)', arm.stub),
    section('VISIBLE TESTS (each is also one of the hidden tests)', arm.visible),
  ].join('\n')
}

function spent() {
  try {
    return budget.spent()
  } catch (e) {
    return null
  }
}

log(`run ${PLAN.run_id}, batch ${spec.batch}, ${mode === 'wave' ? `wave ${A.wave} of ${nWaves}` : `replacements for ${A.replace.join(', ')}`}: ` +
    `${todo.length} attempts (${todo[0].id} .. ${todo[todo.length - 1].id}), ` +
    `${PLAN.concurrency} at a time; agentType ${PLAN.agent_type}, model ${PLAN.model}, effort ${PLAN.effort}`)
phase('Attempts')
const spentBefore = spent()
const queue = todo.slice()
const results = {}
let done = 0

async function worker() {
  while (queue.length > 0) {
    const at = queue.shift()
    let r = null
    let err = null
    try {
      r = await agent(buildPrompt(at), {
        agentType: PLAN.agent_type,
        model: PLAN.model,
        effort: PLAN.effort,
        label: at.id,
        phase: 'Attempts',
      })
    } catch (e) {
      err = String(e).slice(0, 300)
    }
    done += 1
    const text = r === null || r === undefined ? null : String(r)
    results[at.id] = {
      attempt_id: at.id,
      task: at.task,
      arm: at.arm,
      replaces: at.replaces || null,
      returned: text !== null,
      error: err,
      final_line: text === null ? null : text.trim().split('\n').pop().slice(0, 200),
      final_text_chars: text === null ? 0 : text.length,
    }
    log(`${at.id} ${text === null ? 'did not return (infrastructure-failure candidate)' : 'returned'} (${done}/${todo.length})`)
  }
}

await parallel(Array.from({ length: Math.min(PLAN.concurrency, todo.length) }, () => worker))
const spentAfter = spent()
const notReturned = todo.filter(a => !(results[a.id] && results[a.id].returned)).map(a => a.id)
if (notReturned.length > 0) {
  log(`not returned: ${notReturned.join(', ')}. Replace them in a replacement wave of batch ${spec.batch} before the readings (SMOKE.md 4.4)`)
}

return {
  schema: 'x1-smoke-batch-result/2',
  run_id: PLAN.run_id,
  plan_sha256: PLAN.plan_sha256,
  batch: spec.batch,
  wave: mode === 'wave' ? A.wave : null,
  replace: mode === 'replace' ? A.replace : null,
  gate_sha256: spec.batch > 1 ? A.gate_sha256 : null,
  agent_type: PLAN.agent_type,
  model: PLAN.model,
  effort: PLAN.effort,
  concurrency: PLAN.concurrency,
  attempts: todo.map(a => results[a.id]),
  completed: todo.filter(a => results[a.id] && results[a.id].returned).length,
  not_returned: notReturned,
  budget_spent_output_tokens_before: spentBefore,
  budget_spent_output_tokens_after: spentAfter,
  note: mode === 'wave'
    ? `Save this object as <run root>/results/batch_${spec.batch}_wave_${A.wave}.workflow.json. Per-attempt tokens come from the transcripts (x1smoke.py tokens).`
    : `Save this object as <run root>/results/batch_${spec.batch}_replace_<n>.workflow.json (n = 1, 2, ...).`,
}
