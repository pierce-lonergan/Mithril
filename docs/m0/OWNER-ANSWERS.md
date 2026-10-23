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

## 2026-10-23, batch 3 (asked about 08:10 PT)

Sitting 1 (Sun 10-18) did not take place; nothing had been signed by 10-23 [M, no tags or owner commits on
origin/main].

| ID | Question (abridged) | Answer, verbatim | Option text he saw |
|---|---|---|---|
| D0-12 / D0-9a (interim) | Sitting 1 didn't happen. How do you want to sign this week? | "Chat now, key on Sunday (Recommended)" | "Reply here, e.g. 'SIGN sitting-1: R1-R6, X0'. I quote your words verbatim into the record (the weaker interim form from HOW-TO-SIGN). On Sun 10-25 you make an SSH signing key and re-sign with signed tags at sitting 2." |
| C01, C02, C25, D0-7a | Accept the registered defaults for the noise pilot's four open inputs? | "Accept all four defaults (Recommended)" | "C01: the 8-thread cap lifts only inside 23:00–07:00 windows. C02: timing runs read the real Qwen3-30B-A3B Q4 file on the NVMe, read-only, never the USB disk. C25: X3's parity result stays provisional until X4's calibration; X4 calibrates on x3_bench. D0-7a: measurement may run unattended inside windows, with no agents running then." |
| A20 | X1 runs its Claude attempts through your Max plan. Have you confirmed the plan's terms allow scripted, headless attempts? | "Terms OK; run the smoke run" | "A capped smoke run, using at most about 10 points of one weekly window, measures what an X1 attempt really costs. Your account must be idle while it runs (≤1 h for the first 5 attempts)." |

Consequences:
- The interim chat signature is recorded verbatim, with its weakness stated in
  [HOW-TO-SIGN](sittings/2026-10-18/HOW-TO-SIGN.md) (b): an agent writes this log. Pierce's own message in the session
  transcript is the primary evidence. Every chat-signed item is re-signed with a signed tag at sitting 2
  (Sun 2026-10-25).
- The noise-pilot record registers the four defaults and can freeze once its service is pilot-ready. The first
  pilot night still needs its signature and Pierce's own pre-night settings.
- The X1 smoke run needs X1-amendment-1 frozen and signed with its pinned fields (model, effort, share s, cap, K).
  It runs only with the account idle, at a time Pierce agrees.

## 2026-10-23, batch 4: Pierce's written delegation and interim signature (about 08:40 PT)

Pierce's message, verbatim:

> Do whatever YOU need to do to make this project work. you have my full written permission to ratify any
> conflicting statements. effort is "max/ultracode"

He sent it in reply to the lead engineer's proposed sitting-1 signature block, whose only blank was the X1 effort
level. The lead engineer reads it as follows. Each reading is recorded here so that Pierce can correct it at
sitting 2 (Sun 2026-10-25), when he re-signs with his key:

1. **Interim signature, sitting 1 (chat form).** The message adopts the proposed block by reference and fills its
   one blank: **effort = `max`**. "ultracode" names the orchestration mode, not an effort level. The full signed
   text and its scope are in [sittings/2026-10-23-chat/SIGNATURES.md](sittings/2026-10-23-chat/SIGNATURES.md).
2. **Written delegation** ("full written permission to ratify any conflicting statements", "do whatever YOU need
   to do to make this project work"). The lead engineer may resolve conflicts between records, and may settle the
   open owner items the work needs:
   - by adopting each item's registered recommended default where one exists;
   - otherwise by a documented choice.

   Every use is logged in [DELEGATED.md](DELEGATED.md), with options, choice, reason and reversibility.
3. **Limits the lead engineer applies to the delegation** (so that it cannot defeat what the project's rules are
   for):
   - It never loosens a ROADMAP threshold. It never makes a post-data change in the favourable direction.
   - It never overrides the coexistence rules, the safety scope (documented, vendor-supported interfaces only),
     or a FROZEN record's append-only rule.
   - It never invents an Owner statement.
   - Gate verdicts are computed by `judge.py` and reported to Pierce before they are acted on.
   - Spending money stays excluded: R1 still says no metered API.
