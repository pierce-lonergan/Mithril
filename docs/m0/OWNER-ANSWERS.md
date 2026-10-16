# Owner answers log

Pierce's answers to questions asked in chat. They are recorded here verbatim, append-only, in the
order given. An answer in chat is the Owner's decision as stated. Under D0-12 as answered below, each
answer is ratified at the next weekly signing sitting. Ratification is the signed record that the
Gatekeeper treats as an AUTHORITY fact ([03-trust](../architecture/03-trust.md)).

The lead engineer posed the questions. Each one below keeps the option text Pierce saw, so it is
clear what he chose.

## 2026-10-16, batch 1 (asked about 11:45 PT)

| ID | Question (abridged) | Answer, verbatim | Option text he saw |
|---|---|---|---|
| D0-10a | How much metered API spend may M0 use? | "No metered API" | "Claude Code plan only. X1 cannot meet DR-017's requirement of two or more model families, so X1 cannot pass or kill and stays amber until a second family exists." |
| D0-10c | Besides Claude, which families should X1 test, and which should author sealed items and give independent reviews? | "Local Qwen3 via Hearth" (the only option selected) | "The pilot the ROADMAP plans: 60 attempts, about 5–10 desktop hours, daytime only, reported but not part of the kill. Uses only the desktop CPU, never the GPU." |
| D0-12 | How do you want to sign pre-registrations before data collection? | "Batch weekly review" | "You sign all records ready that week in one sitting. Collection under any record waits for that sitting, except X0, which you already authorised." |

## 2026-10-16, batch 2 (asked about 14:30 PT)

| ID | Question (abridged) | Answer, verbatim | Option text he saw |
|---|---|---|---|
| X1 rule (amends DR-017's family requirement for X1; to be drafted as a signed amendment) | Which X1 rule should I draft for your signature, given that Claude is the only frontier family? | "Claude kills; pass provisional (Recommended)" | "Claude alone can fire the kill (VP@1 gap >15, or CABW >5 worse than Rust). A pass is only provisional until a second frontier family confirms it at M1. Claude also edits the card, which biases toward passing, so a kill is the more trustworthy signal. Sealed items are generated from templates with deterministic oracles, so no model writes them." |
| D0-10d | Quiet windows: what can I plan on? | "4 pilot nights, then a rule (Recommended)" | "23:00–07:00 PT, starting in week 1. The first 4 nights measure the noise (σ_d). A pre-registered rule then sets 4–7 nights per week, and you re-sign it. You keep GEMS jobs out of those hours." |
| D0-12 (cadence) | When should the weekly signing sitting be? | "Sunday evening (Recommended)" | "First sitting Sun 2026-10-18. I send the agenda and a signing-ready packet Saturday night." |

Earlier instructions, in Pierce's own words in the session brief and follow-up (2026-10-16):

- "Start the parts that need no owner decision: X0 instruction census..."
- Authorisation to commit and push Mithril work to origin main, in small path-limited commits.
- "please do this on ultra code mode and you have permission to do whatever you need to do to
  fulfil this project in its entirety"

  The lead engineer reads this as operational permission: installs, desktop builds, commits and
  agent orchestration. It does not delegate the D0 owner decisions or the gate signatures, because
  ROADMAP §11 says no agent may take those. The coexistence hard rules still apply.

## Consequences the lead engineer must carry through

- **No metered API.**
  - Every metered-API line in COST.md is $0. All agent work, including X1's Claude arm, runs on the
    Claude Code plan, and the plan's usage limits become a schedule constraint.
  - No non-Claude frontier family exists, so every "different model family" requirement in ROADMAP
    (Prover and Adversary for the core note, X2 loop-rule review, the X4 blind batch, X1 item
    authorship) is unmet. Each record says so. A second family can be added only by a new Owner
    answer.
- **The X1 rule** needs a signed amendment record. A kill on Claude alone fires STOP-L as DR-017
  states. A pass is labelled *provisional* until a second frontier family confirms it at M1.
  Held-out items come from templates with deterministic oracles, so no model family authors them.
  The local Qwen3 runs remain a reported pilot outside the kill.
- **Quiet windows.**
  - The first pilot night is possible only after the X4 noise-pilot record is signed, so it falls on
    Sunday 2026-10-18 at the earliest.
  - 23:00–07:00 PT. No Mithril agents, builds or WSL activity run on the desktop in a window.
- **Signing.**
  - Sitting 1 is Sunday 2026-10-18, evening.
  - The packet and agenda are due Saturday 2026-10-17, night. They will be in
    [OWNER-QUEUE.md](OWNER-QUEUE.md).
