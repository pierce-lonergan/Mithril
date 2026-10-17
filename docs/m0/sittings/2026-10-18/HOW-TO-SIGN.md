# How to sign at sitting 1 (Sun 2026-10-18)

Prepared 2026-10-16 by the packet track (a Claude agent) and revised the same night after one review
(Claude, same family, independent context; [Review log](#review-log)). This page answers **D0-9a**:
how Pierce signs during M0, before the ledger exists. **Pierce chooses** the mechanism. Agents never
create, hold or see a key, never tick a box or fill a Value field, and never write a tag message
([D0_BRIEF](../../../D0_BRIEF.md), "How to sign", rule 6).

Two mechanisms follow. **(a)**, signed git tags, is recommended. **(b)**, an interim chat signature, is
available if (a) cannot be set up on Sunday.

Facts checked on the laptop on 2026-10-16 [M, packet track]:
- no tags exist in the Mithril repository;
- git is `2.55.0.windows.5`;
- Windows OpenSSH is `OpenSSH_for_Windows_9.5p2`;
- the global git config sets no `gpg.format`, `commit.gpgsign` or `tag.gpgsign`, and no
  `user.signingkey` [M, re-checked 2026-10-17T03:27Z], so git has no signing key configured;
- the Appendix B verifier exists only as text inside D0_BRIEF, not as an installed script;
- the extraction command of step 6 produces a script that runs with the laptop's Python and exits 0 on
  today's repository (no tags, no ticks);
- in a synthetic test, the verifier's `check()` was run on an in-memory ticked copy of D0_BRIEF and a
  made-up tag message, with no git and no keys:
  - following the rules of step 3 (AMEND with Values, no `;`) gave 6 decided lines and no problems;
  - a YES with a non-recommended Value was flagged;
  - an `A02:` line voided the whole tag.

---

## (a) Signed tags (D0_BRIEF "How to sign" and Appendix B). Recommended

**Why the key type matters.** Every agent in this sprint runs under Pierce's Windows account [M:
session scratch directories sit under `C:\Users\PIERCE~1\AppData\Local\Temp`]. A signing key that sits
in that account **without a passphrase or a hardware touch** can be used by any agent, so a tag made
with it proves no more than a typed name. D0_BRIEF names this tombstone `software_key_on_agent_account`;
its option for it is SOFT. A passphrase key that is never loaded into a running ssh-agent (PASS), or a
key on a hardware token that needs a touch (HW), cannot be used by an agent without him.

Even with PASS or HW, the key does not stop an agent from changing **what** gets signed. So he reads
the full diff before tagging (step 3) and checks each freeze commit before its tag (step 5).

### Step 1. Check for an existing key (about 2 min)

PowerShell, in his own terminal:

```powershell
git config --global --get user.signingkey      # empty = none configured
Get-ChildItem $HOME\.ssh -ErrorAction SilentlyContinue
ssh-add -l                                      # lists keys loaded in a running ssh-agent, if any
ssh -V                                          # 2026-10-16 laptop: OpenSSH_for_Windows_9.5p2
```

If he already has a passphrase-protected SSH key that he wants to use, he can skip to step 2. It must
**not** be listed by `ssh-add -l`.

### Step 1b. Create a key (about 5–10 min), choosing HW or PASS

**HW**: a FIDO2 security key (needs a token in hand). Whether this OpenSSH build and Windows Hello
handle `-sk` keys on his machine is not verified here.

```powershell
ssh-keygen -t ed25519-sk -O verify-required -C "pierce mithril owner signing (HW)" -f "$HOME\.ssh\mithril_owner_sk"
```

**PASS**: a passphrase key. Choose a passphrase you type, never stored in a file.

```powershell
ssh-keygen -t ed25519 -C "pierce mithril owner signing" -f "$HOME\.ssh\mithril_owner_ed25519"
# Do NOT run ssh-add for this key. A key loaded into ssh-agent can be used by any process in this
# account, including agents. This account must not keep it loaded.
```

Then record the fingerprint for D0-9a's Value line:

```powershell
ssh-keygen -lf "$HOME\.ssh\mithril_owner_ed25519.pub"     # or mithril_owner_sk.pub; copy the SHA256:... part
```

### Step 2. Configure git for signing, in his own user config (about 2 min)

```powershell
$pub = "$HOME\.ssh\mithril_owner_ed25519.pub"              # or the -sk .pub file
git config --global gpg.format ssh
git config --global user.signingkey $pub
# a list of trusted signers, so that git verify-tag can check SSH signatures
$email = git config --global user.email
"$email $(Get-Content $pub)" | Out-File -Encoding ascii "$HOME\.ssh\allowed_signers"
git config --global gpg.ssh.allowedSignersFile "$HOME\.ssh\allowed_signers"
```

**Do not set `commit.gpgsign` or `tag.gpgsign` globally.** Agents commit under the same account, and a
global signing default would make every agent commit ask for the passphrase and fail [inference]. Sign
only by asking for it each time (`-s`, `-S`). If he prefers to leave the global config untouched, every
signing command can carry the settings itself, for example
`git -c gpg.format=ssh -c user.signingkey="$pub" tag -s …`.

Whether `ssh-keygen` prompts for the passphrase in his terminal when git calls it is not verified here
[inference: it normally does]. If it does not, the fallback is to load the key just for the signing
moment (`ssh-add <key>`, sign, `ssh-add -d <key>`). Any process in the account could use the key while
it is loaded, so keep that window to seconds.

### Step 3. Tick the brief (during the sitting)

First, he asks the lead engineer to **hold all commits to `main` from the start of the sitting until
his push** (step 6). Otherwise the push can fail as non-fast-forward.

In his own checkout (`C:\Users\Pierce Lonergan\Desktop\repos\Mithril`), up to date with `origin/main`:

```powershell
cd "C:\Users\Pierce Lonergan\Desktop\repos\Mithril"
git fetch origin
git status                    # expect a clean tree on main; otherwise stop and ask the lead engineer
git pull --ff-only
```

Rules for the edits:
- Edit `docs/D0_BRIEF.md` in an editor and change `[ ]` to `[x]`, **exactly one box per line**.
- Fill each required `Value` field and each `AMEND:` text on the same line.
- Keep **at least three spaces** before `Tag:` and before the next `[`. The verifier finds the end of
  an AMEND text that way.
- **Do not use `;` inside an AMEND text or a Value.** The tag grammar splits fields on `;`.
- **Tick AMEND, not YES, wherever a Value differs from the `(rec …)` printed beside it.** The verifier
  counts such a YES as AMEND **and reports it as a problem** (exit 1).

Commit, signed, with the answers that have no D0_BRIEF line in the commit message (see step 5):

```powershell
git add docs/D0_BRIEF.md
git commit -S -F "$HOME\sitting-1-commit.txt"     # a message file he writes himself
git show --stat HEAD                               # must list docs/D0_BRIEF.md only
git show HEAD -- docs/D0_BRIEF.md                  # the full diff: read every changed line before tagging
```

### Step 4. The D0 tag (one per sitting)

He writes the tag message himself in a file **outside the repository**, in the Appendix B grammar.
The grammar:
- the first line is `D0-SIGN 1`;
- the second is `file: docs/D0_BRIEF.md`;
- then one line per decided item: `<ID>: <CHOICE>[; <field>=<value>]...`.

An AMEND, OTHER or ANSWER needs `text=<the same text as the file>`. Value fields are repeated by name,
for example `t1 cap=$0`.

**Only D0_BRIEF line IDs are allowed** (`D0-…`, `HM-…`, `Q…`). Any other line, for example an
OWNER-QUEUE ID such as `A02`, makes the verifier reject **the whole tag** ("unparsable line"). Answers
without a D0_BRIEF line go in the signed commit message (step 3) or in a record's tag (step 5).

```powershell
git tag -s d0-sign-1 -F "$HOME\d0-sign-1.txt" HEAD
git verify-tag d0-sign-1          # should report a good signature from his key
```

### Step 5. Record signatures (one tag per FROZEN record)

D0_BRIEF §4.3 (a) asks for "a signed git tag over its freeze commit". The name and message below are
this page's proposal [G]. Nothing else depends on them yet.

The freeze hash in the packet is filled in by an agent. Before each record tag, he checks that the
hash holds the record he read (X0 shown; the same for each record):

```powershell
$f = '<X0 freeze commit hash>'                                   # from the packet
git log -1 --format='%H %an %ad %s' $f                           # the freeze commit itself
git show "$($f):docs/m0/prereg/X0-census.md" | Select-String 'Status' | Select-Object -First 1   # must say FROZEN
(git show "$($f):docs/m0/prereg/X0-census.md" | Measure-Object -Line).Lines                     # its line count
git diff $f HEAD -- docs/m0/prereg/X0-census.md                  # empty, or only appended amendments and review lines
git tag -s prereg-sign-x0-census -F "$HOME\sign-x0.txt" $f
```

The message, written by him:
- first line `PREREG-SIGN 1`;
- `record: docs/m0/prereg/X0-census.md`;
- `freeze: <full hash>`;
- `sitting: 1 (2026-10-18)`;
- then the record's own signature-block answers in his words. For X0: the OQ answers or "deferred",
  and the T_forms choice. For X1-amendment-1: the fields of its §10.

The record file itself stays as frozen. Its signature block is only a readable mirror.

### Step 6. Verify and push (about 5 min)

The Appendix B verifier is text in D0_BRIEF. To run it without any agent installing it, extract it
himself:

````powershell
$t = Get-Content docs\D0_BRIEF.md -Raw
$m = [regex]::Match($t, '(?s)## Appendix B.*?```python\r?\n(.*?)```')
$m.Groups[1].Value | Out-File -Encoding utf8 "$HOME\verify_d0_sign.py"
git verify-tag prereg-sign-x0-census      # the authority check, for each record tag (d0-sign-1 in step 4)
python "$HOME\verify_d0_sign.py" .        # advisory: prints DECIDED lines and any PROBLEM lines; exit 0 = no problem found
git push origin main d0-sign-1 prereg-sign-x0-census     # plus any other record tags made
````

What counts:
- **The authority check is `git verify-tag` on each tag, plus the signer's fingerprint matching the
  one on his D0-9a line.** The verifier does not check **whose** key made a signature.
- **The verifier is advisory.** It is agent-written code, extracted from a file agents can edit, and
  run in his account. Exit 0 means it found no problem, not that the signing is valid. Reading the
  extracted script before running it is the careful course.
- If the push is rejected as non-fast-forward (someone committed to `main` during the sitting), he
  does not rebase, because that would rewrite the signed commit. He runs `git pull --no-rebase
  --no-edit`, checks with `git diff --stat HEAD^1 HEAD` (what the merge brought in) that
  `docs/D0_BRIEF.md` is not listed, and pushes again. The signed commit and its tags stay as they are.
- The verifier's git layer has never been run against a real signed tag (D0_BRIEF Appendix B,
  "Status"). If it misbehaves, `git verify-tag` plus reading the ticks is the fallback, and the lead
  engineer logs it.

**After signing.** No agent may edit any ticked line or Value field in D0_BRIEF. The verifier voids a
line changed after its tag until a new tag names it.

**Time:** about 15–60 min the first time for steps 1–2, the key and the configuration [D0_BRIEF §4.3
item 6: 0.25–1 h of key setup], best done before Sunday; steps 3–6 about 10–15 min [inference]; about
5–10 min at later sittings.

---

## (b) Interim chat signature (only if (a) cannot be set up on Sunday)

**Form.** Pierce types one message in the chat with the lead engineer:

```text
SIGN sitting-1: D0-12 YES; D0-12x X0; D0-12i CONFIRMED; D0-10a AMEND text=…, t1 cap=…, stop-loss=…; …;
records: X0-census at <freeze hash>, …
```

The lead engineer then:
- copies it **verbatim** into `docs/m0/sittings/2026-10-18/CHAT-SIGNATURES.md` (append-only, with the
  time);
- commits it;
- marks each item "chat-signed, not an AUTHORITY fact".

Boxes in D0_BRIEF stay unticked, because agents never tick them.

**Weakness, stated plainly.**
- **An agent writes the log.** Nothing binds the text to Pierce. An agent error or a fabricated line
  would look the same as his words.
- Under A10 ("authority is a signature, never a sentence", 03 §1) a chat line is a sentence, so it
  cannot create an AUTHORITY fact. It is no stronger than the typed names D0_BRIEF already calls
  forgeable.
- Under the README's collection rule, a record counts as SIGNED only by his signature. Whether a
  chat-signed record may start collection (the X4 noise pilot, for example) is a further choice that
  only Pierce can make. It would weaken A10 for M0, and this page does not recommend it. Without that
  choice, collection under every record except X0 (R3) waits for the tag. The fallback then buys only
  a dated record of intent.
- Every chat-signed item must be re-signed by tag at sitting 2 (Sun 10-25), and the lead engineer lists
  them in that packet.

---

## Recommendation [G]

**(a), with a PASS key, or HW if a FIDO2 token is at hand.** It is the only mechanism that turns the
chat answers into AUTHORITY facts. It lets the X4-noise-pilot record be SIGNED tonight, which keeps the
10-23 and 10-24 nights open; signing on 10-25 still fits W1. It costs about 15–60 minutes the first
time, which can be spent before Sunday. (b) is a fallback that leaves every signature pending. **Pierce chooses.** His choice and key fingerprint go on D0_BRIEF's D0-9a line, and
in the tag as `D0-9a: <HW|PASS|SOFT>; key fingerprint=SHA256:…`.

---

## Review log

| Date | Reviewer | Family | Context | Scope | Result |
|---|---|---|---|---|---|
| 2026-10-16/17 | review 1: one reviewer agent, adversarial (the same review as the packet's and X1-amendment-1's) | Claude, same family | independent context | This page against D0_BRIEF "How to sign" and Appendix B, OWNER-QUEUE and the packet; lenses: signing safety and time | Finding 10 (minor, four parts), all accepted: (1) `git show --stat HEAD` showed file names only; step 3 now reads the full diff, and step 5 checks each freeze commit before its tag; (2) the verifier is agent-written and advisory; the authority check is `git verify-tag` plus the D0-9a fingerprint; (3) commits to `main` are held during the sitting, and a rejected push is merged, never rebased; (4) the recommendation no longer says (a) is needed for week-1 pilot nights (10-25 still fits W1). Finding 2's time figures apply here too (15–60 min for the key). The other findings concern the packet and X1-amendment-1 and are logged there. The step-5 check commands (all but `git tag`) were dry-run on commit `6b14b35` in Windows PowerShell and printed the commit, the Status line, 1,285 lines and an empty diff [M, reviser, 2026-10-17]; nothing has been run against a real freeze commit or a signed tag |
