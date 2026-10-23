export const meta = {
  name: 'x1-smoke-probe',
  description: 'X1 smoke run pre-flight probe: does x1-subject resolve, with only Write and Bash, the pinned model and effort max? Runs before r0.',
  whenToUse: 'Only by the lead engineer, once per run root, before the first plan reading (experiments/x1-harness/smoke/SMOKE.md 4.2).',
  phases: [
    { title: 'Probe', detail: 'one x1-subject probe agent, one full-model-ID test, one turn-cap test' },
  ],
}

// X1 smoke-run pre-flight probe. This file in the repository is the TEMPLATE: `python x1smoke.py
// prepare` writes <run root>/probe_workflow.js with the probe spec inlined on the PROBE line below.
// Launch it from the controller session (working directory = the run root), before r0:
//   Workflow({scriptPath: '<run root>/probe_workflow.js', args: {run_id: '<run id>'}})
// Then: python x1smoke.py probe --root <run root> --workflow-dir <this run's transcript directory>
// The gate refuses to report a decision unless results/probe.json says ok and the probe ended before r0.

const PROBE = null; // @@PROBE@@

if (PROBE === null) {
  throw new Error('This is the template. Run `python x1smoke.py prepare` and launch <run root>/probe_workflow.js.')
}

const A = args || {}
if (A.run_id !== PROBE.run_id) throw new Error(`args.run_id must be "${PROBE.run_id}"`)

async function tryAgent(prompt, opts) {
  try {
    const r = await agent(prompt, opts)
    const text = r === null || r === undefined ? null : String(r)
    return { returned: text !== null, text: text === null ? null : text.slice(0, 4000), error: null }
  } catch (e) {
    return { returned: false, text: null, error: String(e).slice(0, 300) }
  }
}

phase('Probe')
// 1. the agent type as the batches use it: tools listed, one harness call
const main = await tryAgent(PROBE.main_prompt, {
  agentType: PROBE.agent_type, model: PROBE.model, effort: PROBE.effort, label: PROBE.labels.main, phase: 'Probe',
})
// 2. is the full model ID accepted? (only when the plan uses an alias)
let fullId = null
if (PROBE.model !== PROBE.full_model_id) {
  fullId = await tryAgent(PROBE.fullid_prompt, {
    agentType: PROBE.agent_type, model: PROBE.full_model_id, effort: PROBE.effort, label: PROBE.labels.fullid, phase: 'Probe',
  })
}
// 3. is a maxTurns frontmatter field honoured? (agent type x1-turncap-probe has maxTurns: 2)
const turncap = await tryAgent(PROBE.turncap_prompt, {
  agentType: 'x1-turncap-probe', model: PROBE.model, effort: 'low', label: PROBE.labels.turncap, phase: 'Probe',
})

return {
  schema: 'x1-smoke-probe-result/1',
  run_id: PROBE.run_id,
  plan_sha256: PROBE.plan_sha256,
  main,
  full_model_id_test: fullId,
  turncap,
  note: 'Save as <run root>/results/probe.workflow.json, then run x1smoke.py probe on this run\'s transcript directory.',
}
