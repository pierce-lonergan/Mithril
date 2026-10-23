# X1 attempt-isolation controls (X1-amendment-1 §2.3)

Status: **built, self-tested on the laptop, reviewed once (10 findings, all accepted) and revised; not
run against sealed content.** Track x1iso, 2026-10-23. This directory holds the full §2.3 controls that
**sealed** X1 items require and that the smoke kit lacks (SMOKE.md §3): a per-attempt isolated
configuration, the harness tools served over a local MCP server with no shell, a per-`check` sandbox
(no network, read-only inputs, nothing hidden reachable, an allowlisted environment), and enforced
turn/token/wall budgets. Each control has a negative test that tries to break it and must fail with a
specific denial. Current result: [`results/negtest_2026-10-23_r2.json`](results/negtest_2026-10-23_r2.json),
**58/58 PASS** [M, laptop DESKTOP-F441IUK, 2026-10-23T22:48Z, sandbox `x1iso-winsandbox/2`, 46.8 s;
code as run, SHA-256: `winsandbox.py` f40ad0b6…3e7a, `checker.py` 82a42bb9…f935, `mcp_server.py`
a0fad40f…aec1, `attempt.py` eef3c208…e126, `negtest.py` 60594f34…9176, `probe/probe.rs` 9cea1445…9dd9].
The first run, [`negtest_2026-10-23_r1.json`](results/negtest_2026-10-23_r1.json) (29/29 PASS as scored
then), is **superseded**: three of its rows passed on a probe panic, not on a denial (review 1,
finding 4); it is kept as the raw tool output, byte-identical to what `negtest.py` wrote (SHA-256
`69f07b78…88c4`).

Scope and coexistence: laptop only; documented, vendor-supported Win32 interfaces only; no installer;
no system or security setting changed. Each sandbox (Stage A, and each Stage B case) registers its own
AppContainer profile, a per-user app-package registration in the user's own HKCU hive plus a storage
folder under `%LOCALAPPDATA%\Packages\x1iso.*`, created and deleted inside the call (reversible; the
suite ends by checking that no `x1iso.` profile or folder is left: 0 left, HKCU mapping count 125 before
and after [M]). The suite creates a temporary attempt root `C:\x1iso-negtest-<random>` (outside the user
profile, as attempt.py requires; removed at the end). Rust and Python are used; the pinned `rustc` is the
mithi track's `~/.rustup-mithril` toolchain; nothing is installed. Desktop not used (thread budget 0).

**Family-agnostic, per DELEGATED P2's interim restriction.** Nothing here contains sealed content,
Qwen3 templates, or any item. The checker is content-agnostic: it runs whatever public prelude,
driver and visible expected-outputs the caller supplies. The end-to-end tests use throwaway
`f() -> 0` programs, not any task.

## Files

| Path | What |
|---|---|
| [`winsandbox.py`](winsandbox.py) | The per-run sandbox: an AppContainer process (LPAC by default) with no network capability, its own registered profile (`x1iso.<label>.<random>`, deleted on close), a per-image custom capability SID granting read+execute on the toolchain image only, a Job Object (CPU-time, memory, active-process, hard CPU-rate, UI restrictions, kill-on-close), an inherited-handle allowlist, an **allowlisted** environment block (`SANDBOX_ENV_NAMES`, 13 names, nothing inherited), and a watchdog for CPU (user + kernel), wall, and disk (`out/` **plus the profile's storage folder**). `ToolchainImage` builds the read-only, hashed toolchain copy; `stale_profiles()` finds leftover registrations. |
| [`checker.py`](checker.py) | One `check` call, the two-stage oracle split (DESIGN §11.3) under **one CPU pool and one wall deadline per call** (`CallBudget`): **Stage A** builds in a sandbox (`mithi check` under LPAC; `rustc` under non-LPAC, because the GNU toolchain must exec its linker); **Stage B** runs each visible case in **its own fresh LPAC sandbox** that forbids child processes and network. Expected outputs are compared **here, outside every sandbox**. |
| [`mcp_server.py`](mcp_server.py) | The harness MCP server (stdio JSON-RPC). The subject's **only** capability: eight tools over `work/` and the sandboxed checker, **no shell**. Enforces the 8-`check` budget, the wall budget, and a tool-call backstop; records every call in a hash-chained log. Per-call sandbox directories are `<X1_SANDBOX_ROOT>/<random hex>`, outside the attempt tree. |
| [`attempt.py`](attempt.py) | The per-attempt **isolated configuration** generator and budget state. Refuses an attempt directory whose name is not opaque hex, or that lies under `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, `.claude/` or `.git` (any ancestor up to the drive root). Writes `work/`, `harness/`, `config/` (settings, `.mcp.json`, the `x1-subject` agent as a file and as `--agents` JSON, `append_system_prompt.md`) and `launch.json` (the documented headless flags). `finish_attempt` **moves** work/, harness/, config/ and launch.json to the private store, verified by SHA-256, then deletes the originals. |
| [`probe/probe.rs`](probe/probe.rs) | The negative-test probe: one documented std operation per run (read/write/listdir/connect/resolve/spawn/sleep/burn/alloc/alloc1/fill/envnames/envget). Prints one `OK …` or `ERR <op> code=<code> …` line; panics are caught and allocation uses `try_reserve`, so a denial is always a specific code. |
| [`negtest.py`](negtest.py) | The runnable negative-test suite (below). Writes `negtest.json`; records the Python version, not the interpreter's path. |
| [`results/`](results/) | Verification reports [M]: `negtest_2026-10-23_r2.json` (current), `negtest_2026-10-23_r1.json` (superseded). |

## The controls, their mechanisms, and the negative test that proves each

Run: `python negtest.py --mithi C:\Users\Pierce Lonergan\x1s\mithi.exe --out <dir> [--attempt-root <dir>]`

All results [M, laptop, 2026-10-23, r2]. "Code" is the OS error the probe reports.

| §2.3 control | Mechanism | Negative test (must fail) | Result |
|---|---|---|---|
| sandbox: **read-only inputs**, nothing hidden reachable | AppContainer SID granted read+execute on `in/` only; held-out data is never placed where agent code runs (Stage B compares outside) | LPAC probe reads the repo README, an oracle/design file, another attempt's workspace, `~/.claude/settings.json`; lists the repo; writes into `in/` | all **code 5** (access denied); reading `in/` and writing `out/` **succeed** |
| Stage A (non-LPAC) confinement | no ALL-APPLICATION-PACKAGES ACE on the repo or attempts; no network capability | non-LPAC probe reads the repo and another attempt | **code 5** (r1 did not test non-LPAC; README gap 4 claimed it; now measured) |
| sandbox: **no network** | no `internetClient`/`privateNetworkClientServer` capability | LPAC: TCP connect out, DNS, loopback; non-LPAC: the same | LPAC: Winsock does not initialise, **WSAStartup 10107** on all three; non-LPAC: connect **10013** (WSAEACCES), DNS **11001**, loopback **timed out** |
| loopback isolation (positive control) | a listener on 127.0.0.1 opened by the suite | the same probe connects from **outside** the sandbox | **connected**, so the in-sandbox failures are the sandbox's doing |
| sandbox: no child processes (Stage B) | LPAC denies process creation; Job process limit | probe spawns 20/40 children | **code 5, 0 spawned** |
| sandbox: **no host data via the environment** | explicit 13-name allowlist; `LOCALAPPDATA` = `out/tmp` (Windows rewrites TEMP/TMP to `<LOCALAPPDATA>\Packages\<profile>\AC\Temp`, created inside `out/`) | probe lists its environment names (LPAC and non-LPAC); reads TEMP | names **⊆ allowlist** (r1's inherit-then-scrub let `CLAUDE_CODE_USER_EMAIL`, `…ACCOUNT_UUID`, `USERNAME`, `PWD` … through [M]); TEMP **inside `out/`** |
| **wall budget** (per run) | Job wall backstop | probe sleeps past a 3 s cap | **killed=wall** at 3.02 s |
| CPU budget (per run) | watchdog on user + kernel time; Job user-time limit as backstop; hard CPU-rate cap | probe burns past a 2 s cap | **killed=cpu**, 2.00 + 0.05 CPU-s |
| **per-call budget** (DESIGN §11.2 "per call") | `CallBudget`: one wall deadline and one CPU pool for Stage A + every Stage B case | a check with 3 cases sleeping 6 s each under a 12 s cap; 3 cases burning 5 CPU-s each under an 8 CPU-s pool | ends at **12.03 s** (case 1 killed, case 2 not run); **8.06 CPU-s** (case 1 killed, case 2 not run) |
| memory budget | Job `JobMemoryLimit` | 1 MiB chunks up to 8000 MiB, cap 256 MiB; one 400 MiB block; one 200 MiB block | chunks refused **after 252 MiB** (peak 269,094,912 B: 659,456 B over the 268,435,456 B cap, inside the one refused 1 MiB request); 400 MiB block **refused**; 200 MiB block works (positive control) |
| **disk budget** | watchdog sums `out/` **and the profile's storage folder** | probe writes up to 64 MiB into the profile's own `AC` folder, and into TEMP, under an 8 MiB cap | both **killed=disk**; profile folder **removed on close** |
| Stage B: no carry-over between cases | a fresh sandbox (own SID, empty `out/`) per case | case 0 leaves `marker.txt` in its working directory; case 1 looks for it | case 1 reports **absent** |
| Mithril arm runs under the allowlisted env | LPAC Stage A | `mithi check` on a trivial program | **accept** |
| MCP server: **no shell**, only x1 tools | exactly eight tools | `tools/list`; `read_file` of the repo (relative and absolute); write a non-solution file | **only 8 tools**; all **rejected** |
| sandbox paths name no attempt | call dirs `<sandbox root>/<random hex>` outside the attempt tree; opaque attempt names | a solution with a compile error: do the diagnostics the subject sees name the attempt? | diagnostics name the **neutral sandbox root only**; no `sandbox`/`sbx` dir in the attempt tree |
| **check budget**; submit ends | 8 calls counted from the hash-chained log | calls 3–9 after two earlier calls; a check after submit | 9th **budget_exhausted**; **attempt_ended** |
| MCP server env | `X1_ATTEMPT_DIR`, `X1_IMAGE_ROOT`, `X1_SANDBOX_ROOT` in both env blocks | server started with **only** the generated env block (+ the OS variables Python needs) | every check runs |
| **isolated configuration** | `config/` per attempt; settings deny built-ins by name and **never an `mcp__` pattern**; `--agent x1-subject`, `--agents` JSON, `--tools ""`; agent prompt empty, common instructions via `--append-system-prompt-file` | generated files and argv inspected | as stated; config dir **per attempt** |
| no inherited project instructions | prepare_attempt refuses an attempt under `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, `.claude/` or `.git` | plant each one in an ancestor | **all 5 refused**; a labelled name (`item-D-Q4-1-mithril-r1`) **refused** |
| transcripts and results leave the run tree | `finish_attempt` moves, verifies by SHA-256, then deletes | finish an attempt | store hashes **match**; run tree **empty** |
| nothing left behind | profiles deleted on close | count `x1iso.` profiles and folders after the suite | **0** |

## How the X1 workflow agent type is restricted to the MCP tools

Flag forms below are the CLI's documented ones [cited: code.claude.com/docs/en/cli-reference and
/sub-agents, read 2026-10-23]; none was executed here (gap 1).

- **Agent.** `--agents '<json>'` defines `x1-subject` with `tools` = exactly the eight `mcp__x1__*`
  names and `prompt: ""`; `--agent x1-subject` runs the session as it ("the main thread itself takes
  on that subagent's tool restrictions and model"). CLI-defined agents outrank user-level ones, and
  the same agent is also written to `config/agents/x1-subject.md`. The prompt is **empty on purpose**:
  under `--agent`, a non-empty agent prompt "replaces the default Claude Code system prompt
  entirely", which X1-amendment-1 §2.3 item 4 does not allow. The harness's common instructions go in
  `config/append_system_prompt.md` (`--append-system-prompt-file`); the runner appends the arm card
  and the shared domain preamble to it, the same way in every arm.
- **Built-in tools.** `--tools ""` disables all built-in tools (it does not touch MCP tools).
  `config/settings.json` adds `permissions.allow` = the eight x1 names and `permissions.deny` = the
  built-in names (Bash, Write, Edit, Read, WebFetch, WebSearch, Task, Agent, Glob, Grep, …). It has
  **no `mcp__` pattern**: a deny rule beats an allow rule, and `"mcp__*"` "removes every MCP tool",
  the subject's own included (review 1, finding 5a).
- **MCP.** `--mcp-config config/.mcp.json --strict-mcp-config` loads only the x1 stdio server; its env
  block carries the attempt, image and sandbox roots.
- **Configuration.** `CLAUDE_CONFIG_DIR=config/`, `--setting-sources user`, `--settings
  config/settings.json`, `disableAllHooks: true`, `enableAllProjectMcpServers: false`.
- **Where the attempt lives.** Claude Code loads `CLAUDE.md` and `CLAUDE.local.md` "from your current
  working directory and every directory above it", reads `AGENTS.md` the same way, and adds a git
  status snapshot inside a repository; `omitClaudeMd` is "ignored when the agent runs as the main
  session agent via `--agent`". So `prepare_attempt` refuses any attempt directory with one of those
  names (or `.claude/`) in it or above it. The user profile has `.claude/`, so **attempt roots must lie
  outside the user profile** (for example `C:\x1runs\…`); the smoke run root under the profile would be
  refused.

The task's named tool set maps onto the eight as: *read-own-workspace* = `list_files` + `read_file`;
*run-tests* = `run_tests` (= `check` with the visible tests); plus the `write_file`/`str_replace`
editors of DESIGN §7.

## What cannot be verified until a real run, and other limits

These are real gaps, stated so they are visible (as every M0 record requires):

1. **No `claude` CLI / Agent SDK is on the laptop** [M, 2026-10-16/23]. `--agent`/`--agents`,
   `--tools ""`, `CLAUDE_CONFIG_DIR`, `--setting-sources`, `--strict-mcp-config`, the empty-prompt +
   append-file reading of the docs, and that a headless Opus session calls only the `mcp__x1__*` tools
   are **cited, not executed**. They must be shown on a host that has the CLI before any sealed item is
   used (SMOKE.md §3). `--restricted` ("Use it when an evaluation harness drives `claude` on a shared
   machine", v2.1.248+) is a documented alternative the smoke run should evaluate.
2. **Turn and token budgets** are enforced by the runner reading the headless session's usage report
   (DESIGN §12.1). The MCP server enforces the wall and check budgets and a tool-call backstop and
   records every call, but it cannot see turns or tokens; unverified until a real run (SMOKE.md §2).
3. **The AppContainer needs a registered profile** to launch (an unregistered derive-only SID fails
   with `ERROR_FILE_NOT_FOUND` [M]). The profile is a per-user HKCU registration plus a storage folder,
   created and deleted per sandbox; whether the owner wants that persistence, however brief, is his to
   confirm. A killed MCP server cannot delete its profiles; `winsandbox.stale_profiles()` finds them
   (`x1iso.` prefix) and `delete_profile()` removes them; the runner should run both after an attempt.
4. **Non-LPAC Stage A.** The Rust/C build runs in a **non-LPAC** AppContainer because the GNU toolchain
   must exec its linker, which LPAC forbids. Non-LPAC denies the repo and other attempts (code 5) and the
   network (10013) [M, r2], but it can read files granted to ALL APPLICATION PACKAGES. The sealed store
   must therefore never grant that principal (DESIGN §4.6).
5. **How the network is denied differs by mode.** Under LPAC, Winsock itself does not initialise
   (WSAStartup 10107), so std code cannot create a socket at all; non-LPAC gets WSAEACCES from the
   filtering platform. Both deny; the mechanism is Windows' [inference], so the suite must be re-run on
   any host that will run sealed items.
6. **The memory counter.** `PeakJobMemoryUsed` includes a refused request (a refused 400 MiB block peaks
   at 422,215,680 B under a 268,435,456 B (256 MiB) cap [M]), so the test asserts that the request is refused and what was
   committed stays at or under the cap, not that the peak counter does.
7. **What the child can still see.** Its own AppContainer name (random, `x1iso.<A|Bk>.<hex>`) through
   the rewritten TEMP/LOCALAPPDATA, and the neutral sandbox root path. Neither names an attempt, item or
   arm. The profile also has a per-container HKCU registry storage key that the container can write;
   safe Rust (`-F unsafe_code`, no FFI) and `mithi` cannot reach it, but a future C arm could, and its
   bytes are not counted by the disk watchdog [inference].
8. **Attempt roots outside the user profile** (from the ancestor rule) need a place chosen by the lead
   engineer, for example `C:\x1runs`. Under `C:\` the user inherits only Modify, so `winsandbox` grants
   its own user full control on each call directory it creates (setting the Low label needs
   WRITE_OWNER; without it `icacls /setintegritylevel` failed with access denied [M]).
9. **The static gate is a heuristic** (DESIGN §11.4/§18): the structural guarantee is the two-stage
   split (Stage B holds no hidden data), not the gate.
10. **The sealed two-stage oracle** (Stage B over the item's hidden vectors, compared outside) uses the
    same sandbox shown here, but has not been exercised against a sealed item; there is none, by P2's
    interim restriction. Mithril Stage B (`mithi run`) is not exercised by the suite; Mithril Stage A is.

## Review log

| Date | Reviewer | Family | Context | Scope | Result |
|---|---|---|---|---|---|
| 2026-10-23 | review 1: one reviewer agent, adversarial (contamination auditor), names-only environment check on the laptop, no AppContainer runs | Claude, same family | independent context | the whole directory against X1-amendment-1 §2.3 and DESIGN §11 | **10 findings (5 major, 5 minor); all 10 accepted, 0 rejected**, each confirmed by the reviser before fixing [M or cited]. (1, major) inherit-then-scrub environment: confirmed inside LPAC (`CLAUDE_CODE_USER_EMAIL`, `…ACCOUNT_UUID`, `USERNAME`, `PWD` present); replaced by a 13-name allowlist found by bisection (only `LOCALAPPDATA` is needed for activation, and a neutral value works); `envnames` rows for LPAC and non-LPAC. (2, major) budgets per run, not per call: `CallBudget` with one deadline and one CPU pool (user + kernel); two multi-case rows. (3, major) profile storage uncapped and docstring wrong: confirmed (TEMP is rewritten into the profile's `AC\Temp`; LPAC wrote 3 MB there); the watchdog now sums the profile folder, TEMP is redirected into `out/`, docstrings rewritten; disk rows for both places and a removal row. (4, major) three rows passed on a panic: confirmed (WSAStartup 10107 assertion; alloc abort); probe rewritten (caught panics, `try_reserve`, codes), every denial row asserts a code, loopback row with an outside positive control, non-LPAC rows; **fix modified**: "peak ≤ cap" is not a valid assertion because the counter includes the refused request [M], so the rows assert refusal and committed ≤ cap. (5, major) configuration: (a) `mcp__*` deny removed [cited: it removes every MCP tool]; (b) argv now `--agents` JSON + `--agent` + `--tools ""` [cited]; (c) ancestor refusal for CLAUDE.md/CLAUDE.local.md/AGENTS.md/.claude/.git [cited: ancestors load; `omitClaudeMd` ignored under `--agent`]; rows for each. (6, minor) sandbox paths reveal the attempt: confirmed and wider than stated (rustc diagnostics returned to the subject carry the absolute `in/` path); random call dirs under a neutral root, opaque attempt names enforced; a diagnostics row. (7, minor) Stage B shared one sandbox: a fresh sandbox per case; a carry-over row. (8, minor) finish left harness/ and work/: moves all four items with hash verification; a row. (9, minor) hand-edited `python` field: confirmed (only that field differed from the raw output); r1 restored byte-identical, `negtest.py` now writes the version itself. (10, minor) `X1_IMAGE_ROOT` missing from env blocks: added with `X1_SANDBOX_ROOT`; the server is started with only its env block. **Found by the reviser:** r1 never tested non-LPAC although gap 4 said it did (now 6 rows); `icacls /setintegritylevel` fails outside the user profile (fixed by `grant_owner_full`); under `--agent` a non-empty agent prompt replaces Claude Code's system prompt (prompt now empty, instructions appended); the probe-panic issue would also have hidden a real failure. A second-family review is not possible under R1 and R2 |
| — | — | — | — | — | Still open: the lead engineer checks that this revision answers review 1; the smoke run confirms the CLI behaviour (gap 1); Pierce confirms gap 3 |
