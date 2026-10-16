# M0: the falsification sprint (working area)

This folder holds the working records of M0, the five-to-six-week falsification sprint defined in
[ROADMAP §3](../ROADMAP.md#3-m0-the-falsification-sprint). ROADMAP is authoritative for every gate,
amber band and kill. Nothing here may loosen a ROADMAP threshold. A record here may only make a
threshold more precise, for example by fixing a unit, a counting rule or a sample, and it must do so
before data is collected.

| Path | What |
|---|---|
| [PLAN.md](PLAN.md) | The executable sprint plan: tracks, owners, week-by-week deliverables, status |
| [prereg/](prereg/) | Pre-registration records, one per experiment or gate |
| [COST.md](COST.md) | Spend and owner hours against the M0 estimate (ROADMAP §10) |
| [../D0_BRIEF.md](../D0_BRIEF.md) | Owner decisions D0-1 to D0-12, with recommendations and signature lines |
| [../../experiments/](../../experiments/) | Experiment code, raw-result manifests and reports |

## Evidence tags

Every number carries one tag.

| Tag | Meaning |
|---|---|
| **[M]** | Measured here, with the command, machine and date that produced it |
| **[D]** | Derived: computed from [M] numbers or from cited sources by a stated formula |
| **[S]** | Simulated, with the simulator and its inputs named |
| **[G]** | Judgment: an expert estimate with no measurement behind it |
| **[inference]** | Inferred from sources but not measured or derived by formula; the sibling docs use this label |
| **[target]** | A pre-registered threshold. It is a choice, not a fact |

A number taken from a research dossier keeps the dossier's label and citation, for example
"7.16 GB/s (measured) [R11]".

## Pre-registration lifecycle (ROADMAP §1 rule 1, D0-12)

Each record in [prereg/](prereg/) has a status line.

1. **DRAFT.** The record may change freely. No data may be collected under it.
2. **FROZEN.** The record is committed. Its commit hash is the freeze point. From then on, only an
   *amendment* may change it: a dated section appended at the end that gives the reason, says
   whether any data had been seen, and leaves the original text in place. Thresholds never move once
   data has been seen (ROADMAP §1 rule 1). A margin found to be unaffordable needs a new signed record
   *before* collection.
3. **SIGNED.** The Owner has signed the frozen record (D0-12). The signature names the freeze commit
   hash.

**Collection rule.** Data may be collected only under a FROZEN record that is either SIGNED or
covered by an explicit Owner instruction to start that experiment. In the second case the record
says so, and the Gatekeeper evaluates nothing until it is SIGNED. If the Owner later amends the
record, the amendment is marked *post-data*, and the affected verdicts are reported both ways.

**Gatekeeper.** Verdicts are computed by deterministic scripts in `experiments/<exp>/` from the
frozen record and the raw results. Agents may run the scripts and write the dossier. They never
judge (ROADMAP §1 rule 3).

**Independence.** Every pre-registration and every result gets an independent review: a separate
agent context with an adversarial brief, recorded in the record's review log. ROADMAP asks for
reviewers from a *different model family*, which this setup cannot yet supply: every agent so far
is a Claude model. Until D0-10 names other families, reviews are logged as **same-family,
independent-context**. That label is weaker than the ROADMAP requirement, and the gap is visible in
every review log.

## Record template

```text
# <ID>: <title>
Status: DRAFT | FROZEN (commit <hash>) | SIGNED (<date>, commit <hash>)
ROADMAP anchor: §3.x
1. Assumption under test, and what follows if it is false
2. Inputs pinned (sources, commits, versions, machines)
3. Arms / configurations
4. Units and counting rules (defined before data)
5. Metrics: primary, secondary, descriptive
6. Sample and power (or why the measurement is exhaustive)
7. Analysis procedure (deterministic script, named)
8. Outcomes: pass / amber / kill / narrowing, each with its action
9. Threats to validity and how each is handled
10. Deviation and re-run policy
11. Deliverables and where they land
12. Review log (independent reviewers, with model family)
13. Signature block
Amendments (appended, dated)
```
