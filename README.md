# Mithril

**A systems language whose primary users are AI agents.** Every claim about code carries
checkable evidence. Performance-critical code is written once as an exact meaning, and every
optimised realisation must be proven equivalent to it. Self-improvement searches only spaces that
are certified not to change outputs. Rejected ideas are kept, with triggers that re-open them when
the world changes.

> **Status: design phase (October 2026).** There is no compiler yet. This repository holds the
> architecture and the research behind it. The first step is a five-to-six-week
> [falsification sprint](docs/ROADMAP.md) built to kill the project cheaply if its central claims
> are wrong. The acid test is porting [Hearth](https://github.com/pierce-lonergan/hearth), a
> local Mixture-of-Experts inference engine, onto Mithril with bit-identical output.

## Why another language?

Language models write software differently from people. They write familiar syntax well and
novel syntax badly. They lose track of hidden state. Their edits fail when they depend on exact
whitespace. They overrate their own work, and in published self-improvement loops they have
learned to game their evaluators. Mithril is designed around those failure modes, using measured
evidence rather than taste:

- **Familiar surface, no false friends.** Code that parses as Rust means what Rust means. A Rust
  form Mithril does not support is rejected with a named diagnostic. Every new concept gets a new
  keyword. Nothing is silently reinterpreted.
- **Signatures that tell the whole story.** Types, effects as capabilities (`uses { io }`), contracts,
  a numeric fidelity grade and a determinism scope. Callees' bodies never need to enter an agent's
  context.
- **One meaning, many checked realisations.** A kernel is an exact, executable meaning in canonical
  IEEE order. Schedules, layouts, policies and placements are separate artifacts. A small trusted
  checker validates the emitted machine code bit for bit against the meaning.
- **Evidence, not assertion.** Proofs, validations, tests, measurements and rejections all live in
  one content-addressed ledger. Each record carries a grade and is invalidated automatically when
  anything it depends on changes. Every number says whether it was measured, simulated or estimated.
- **Prove the space, not the candidate.** This is the tractable form of the Gödel machine. Whole
  classes of change, such as cache and prefetch policies or schedules that preserve the operation
  graph, are certified once as unable to alter outputs. Agents and the built-in improvement loop,
  the **Forge**, then search those classes using performance evidence alone. A deterministic,
  code-only gatekeeper decides promotion within a budgeted error rate.
- **Tombstones that come back to life.** Every rejected idea is stored with its scope, why it
  failed (hardware, tooling, search, effort, evaluation, and so on) and a machine-checkable trigger.
  `mithc revisit` re-opens it when the hardware, toolchain, model or evaluator changes. Re-exploring
  "unfruitful" problem spaces becomes a scheduled computation, not something someone has to
  remember.
- **The language is governed by measurement.** A cold-agent comprehension harness compares
  Mithril against Rust, C and "Rust plus Mithril's tools". It gates every syntax and stdlib decision
  with pre-registered kill criteria. The loop that evolves the agents' own cards, diagnostics and
  scaffolds is a Darwin-Gödel-style loop, and it runs under the same integrity rules as everything
  else.

## A taste (provisional syntax)

```mith
/// NUMERICS §3 of Hearth: one Q4 weight row times one Q8 activation. Exact grade by default.
kernel fn q4_row_dot(w: &[BlockQ4], a: &[ActQ8]) -> f32
    requires w.len() == a.len()
{
    let mut acc: f32 = 0.0;
    for g in 0..w.len() {
        let mut isum: i32 = 0;      // exact integer sum: may be reordered (range proof)
        for j in 0..32 {
            isum += w[g].q.elem(j) * (a[g].q[j] as i32);
            isum += w[g].q.elem(j + 32) * (a[g].q[j + 32] as i32);
        }
        acc = acc + (isum as f32) * (w[g].d.to_f32() * a[g].d);   // fixed order, no contraction
    }
    canon::nan(acc)
}

/// A policy can only emit hints. The store validates every hint, so no policy can change logits.
policy fn pick_victim(slots: &[SlotView], now: Tick) -> Hint<SlotId> {
    let mut best = Hint::none();
    let mut best_age: u64 = 0;
    for s in slots {
        if s.pinned || s.refs > 0 { continue; }
        let age = now.0 - s.last_use.0;
        if age > best_age { best_age = age; best = Hint::some(s.id); }
    }
    best
}
```

## What Mithril is not

- **Not novel notation.** The evidence says novel syntax costs language models accuracy and money.
- **Not a promise of "faster than C" by magic.** Decode on consumer hardware is bandwidth-bound.
  Speed comes from bytes moved, placement and scheduling, which [the docs](docs/ARCHITECTURE.md#77-honest-hearth-performance-ceilings)
  quantify against measured rooflines.
- **Not self-modifying machine code.** Hot-swap happens only at quiescent token boundaries.
- **Not visual generation in v1.** It depends on a GPU backend.

## Documents

| Start here | |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | The architecture from start to finish: thesis, stack, language, numerics, trust, toolchain, agent protocol, Forge, Hearth port, roadmap, risks, owner decisions |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Milestones M0–M7, gates, pre-registered kill criteria, deferral register, cost estimates |
| [docs/SEED-REFINEMENT.md](docs/SEED-REFINEMENT.md) | The original discussion that started this project, refined claim by claim |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Decision records DR-001…DR-027 and design-level tombstones |

Detailed architecture: [language](docs/architecture/01-language.md) ·
[compute](docs/architecture/02-compute.md) · [evidence and trust](docs/architecture/03-trust.md) ·
[compiler, backends, runtime](docs/architecture/04-toolchain.md) ·
[agent protocol](docs/architecture/05-agent-protocol.md) · [the Forge](docs/architecture/06-forge.md) ·
[the Hearth port](docs/architecture/07-hearth-port.md).

Research behind it: [docs/research/](docs/research/) holds 18 cited dossiers (R01–R13, G01–G05).
They cover the Darwin Gödel Machine and its successors, LLM language ergonomics, kernel DSLs, the
local MoE landscape, verification, hardware rooflines, GPU determinism, transcendentals, memory
models and more. [revisited-ideas.md](docs/research/revisited-ideas.md) is a 25-node,
Darwin-Gödel-style archive of once-dismissed computing ideas re-examined for Mithril.
[docs/design/proposals/](docs/design/proposals/) holds the five competing architectures the final
design was assembled from.

## How this design was produced

The design was produced by AI agents (Claude) orchestrated in October 2026:

1. 13 research dossiers, plus 5 gap-filling dossiers chosen by a completeness critic.
2. A recursive, archive-based exploration of dismissed ideas, where a judge picked stepping stones
   across three depths.
3. Five independent architecture proposals, scored by three expert-persona judges.
4. A synthesis, then adversarial review from six angles (consistency, soundness, physics, agent
   value, evidence fidelity, completeness) and two rounds of fixes.

Caveats: the shared web-search budget ran out during part of the research, so some 2025–2026
work may be missing. Each dossier marks what it could not verify. Every number in the documents
is labelled measured, simulated, inference or target.

## License

Apache-2.0. See [LICENSE](LICENSE).
