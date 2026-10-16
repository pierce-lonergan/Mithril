# X4 sandbox — isolating candidate code on the Windows desktop

**Track:** x4-integrity. **Status:** DESIGN (implementation follows next). **Date:** 2026-10-16 (revision 2, after two same-family, independent-context reviews; see the [prereg review log](../../docs/m0/prereg/X4-integrity.md#12-review-log-independent-reviewers-with-model-family)).
**Anchors:** ROADMAP §3.5; [06-forge §5](../../docs/architecture/06-forge.md); [03-trust §10, §11](../../docs/architecture/03-trust.md); R01 (STOP, AI Scientist, Gödel Agent); R08 (Windows I/O). Evidence tags as in [MEASUREMENT-SERVICE.md](MEASUREMENT-SERVICE.md).

ROADMAP §3.5 asks for "a Windows Job Object with no network, read-only goldens and traces, and supervisor-held limits." A Job Object delivers the limits but **cannot block network by itself**, and it says nothing about other processes the candidate could ask to act for it. This document specifies the Job-Object core, then the network and broker blocks, saying which need system-setting changes (those become exact commands for Pierce) and which do not. **We change no system settings ourselves**, and none of the commands below has been run by the X4 track.

In-process `mprotect` is explicitly rejected: STOP's improvers disabled their sandbox flag (0.42% of 10,000 attempts) and the AI Scientist edited its own time limit [R01]. Isolation must be OS-enforced and **supervisor-held**, outside the candidate's reach ([06 §5](../../docs/architecture/06-forge.md), [03 §10](../../docs/architecture/03-trust.md) rows 3, 5, 17).

---

## 1. Threat model for the sandbox

From [03 §11.1](../../docs/architecture/03-trust.md): adversary A1 is a capable proposer in the Builder role that tries every exploit in [03 §10](../../docs/architecture/03-trust.md). Against the sandbox specifically, the candidate (Forge-era) or the workload (X4) may try to:

- read the hidden oracle, reference outputs, held-out traces or the scorer (rows 7, 14, 30) [R01];
- disable or widen its own limits, including CPU affinity and priority (rows 3, 5, 17) [R01];
- reach the network to call a stronger model or exfiltrate (row 16) [R01], directly or **through a process outside the job** (an out-of-process COM/RPC server, the task scheduler, WMI, another process's named pipe);
- write outside its declared area to edit goldens, the gate or the manifest (row 22, ADR-0009) [RV: D2-E], including **through another name for the same data** (a short name, a case variant, an alternate data stream, a hard link or junction, a `\\?\` or volume-GUID path);
- keep state between runs (a cache in scratch that a later run reads).

**Trust classes of workload.** Only `hearth-c-ref` at its pinned tag is *trusted C*. **Everything else is untrusted, X3's generated kernels included**: they are agent output linked into the harness's address space ([MEASUREMENT-SERVICE.md §2](MEASUREMENT-SERVICE.md)). Out of scope: physical attacks, general side channels (tenant labelling is later, [RV: D3-iii]), DoS by the Owner ([03 §11.1](../../docs/architecture/03-trust.md)).

---

## 2. The Job Object core (no system change needed)

A Windows **Job Object** is created by the Rust orchestrator (the supervisor), the harness child is created suspended and assigned to it **before it runs any code**, and the limits live on the job, which the child cannot modify (it holds no handle to its own job; only the orchestrator does). This is the supervisor-held-limits requirement.

| Limit | Mechanism | Closes |
|---|---|---|
| CPU time | `JOBOBJECT_BASIC_LIMIT_INFORMATION.PerProcessUserTimeLimit` + active-process cap | AI Scientist "edit my own timeout" [R01] |
| Memory | `JOBOBJECT_EXTENDED_LIMIT_INFORMATION.ProcessMemoryLimit` / `JobMemoryLimit` | runaway alloc; 1 TB checkpoints [R01] |
| No new processes | `JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 1`, and **no** `CREATE_BREAKAWAY_FROM_JOB`; `JOB_OBJECT_LIMIT_BREAKAWAY_OK` **not** set | relaunch-self (AI Scientist), `spawn` escape [R01] |
| **CPU affinity and priority class** (new) | `JOB_OBJECT_LIMIT_AFFINITY`, `JOB_OBJECT_LIMIT_PRIORITY_CLASS`, identical for both arms ([MEASUREMENT-SERVICE.md §7.6](MEASUREMENT-SERVICE.md)) | self-elevation to the faster CCD or a higher priority (a31) |
| Kill on supervisor exit | `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` | orphaned candidate work |
| Die on handle close | job handle held only by supervisor | candidate outliving its budget |
| UI/clipboard restrictions | `JOBOBJECT_BASIC_UI_RESTRICTIONS` | incidental interference |

The Job Object limits the job's own processes. It does **not** stop a process in the job from asking a process outside the job to do something for it; that is §3.1's job (AppContainer/LPAC) and §5's broker probes.

**Per-run environment (new).** The orchestrator passes an explicit, minimal environment block (identical for both arms and for the correctness stage) and a **fresh, empty scratch directory** that is deleted after the run, with bytes written counted ([MEASUREMENT-SERVICE.md §3 step 0](MEASUREMENT-SERVICE.md)). Nothing a run writes survives into the next run.

### 2.1 Sealed data: goldens, held-out traces, the oracle (rewritten)

Revision 1 checked that one inherited handle was read-only. That says nothing about other names for the same file, and in degraded mode (no AppContainer, no separate user) the child ran with the Owner's token, so the `MithrilMeasure` ACL entries did not apply at all. Revision 2:

1. **Unreachable, not read-only.** Goldens, held-out traces, the hidden oracle and the reference arm's outputs live in the Gatekeeper's private store, on **no path the child's token can open**: under AppContainer/LPAC, the store carries **no ACE** for the AppContainer SID, for `ALL APPLICATION PACKAGES` or for `ALL RESTRICTED APPLICATION PACKAGES`; under the separate user, no ACE for `MithrilMeasure`. Inputs the workload genuinely needs (a non-held-out routing trace for F1-sim replay) are copied into the run's scratch tree as a fresh copy, or passed as an inherited read-only handle; they are never the sealed originals.
2. **Post-session rehash (Gatekeeper).** After every session the Gatekeeper recomputes the content hash of each golden, trace and oracle file **in the sealed store** and compares it with the pinned hash, using its own private, content-addressed copy as the reference. A mismatch voids the session and is recorded as a hack-suite catch (a8b), whatever name the write came through.
3. **Alternate-name probes** in the self-test (§5 item 5).
4. **ACLs (Pierce runs once, if the separate user exists):** the ACEs below remove inheritance on the sealed store and grant nothing to `MithrilMeasure`; the scratch root alone gets `MithrilMeasure` modify rights.
   ```
   icacls 'D:\mithril-data\sealed'  /inheritance:r /grant:r 'Administrators:(OI)(CI)F' "${env:USERNAME}:(OI)(CI)F"
   icacls 'D:\mithril-data\scratch' /grant 'MithrilMeasure:(OI)(CI)M'
   ```
   (Exact syntax unverified on this box; Pierce checks with `icacls 'D:\mithril-data\sealed'` that no entry names `MithrilMeasure`, `ALL APPLICATION PACKAGES` or `ALL RESTRICTED APPLICATION PACKAGES`.)

**Change sets are judged as git objects, never working-tree paths** ([03 §8.2](../../docs/architecture/03-trust.md), ADR-0009): symlinks, case twins and 8.3 names on sealed paths are refused. That defence lives in the Gatekeeper and covers change sets (a8); runtime writes by a running workload are covered by 1–3 above (a8b).

---

## 3. Network and broker blocks

A Job Object has no network-limit field; a process in a job can still open sockets, and it can ask out-of-job processes to act for it. Each option below is evaluated on: does it block *all* egress; does it need a system-setting change (→ command for Pierce); does it cost measurement fidelity.

### 3.1 AppContainer / LPAC — **mandatory for every untrusted workload, no system change**
Launch the harness child in an **AppContainer**, preferably a **Less-Privileged AppContainer (LPAC)**, with **no capabilities**. Network: an AppContainer process gets network access only through the `internetClient`, `internetClientServer` or `privateNetworkClientServer` capability SIDs; withheld, the OS denies socket connect/listen, loopback included (loopback needs an explicit exemption). Brokers: an AppContainer token can open only objects whose security descriptors grant the AppContainer SID or `ALL APPLICATION PACKAGES`; an LPAC token additionally ignores `ALL APPLICATION PACKAGES` and needs `ALL RESTRICTED APPLICATION PACKAGES`, which far fewer system objects grant [inference: Windows AppContainer documentation, not re-checked here]. That is the main defence against delegating work to out-of-job COM/RPC servers, the scheduler or WMI. It is set at `CreateProcess` time (`STARTUPINFOEX` + `PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES`, plus `PROC_THREAD_ATTRIBUTE_ALL_APPLICATION_PACKAGES_POLICY` for LPAC); the profile is created by the supervisor at runtime (`CreateAppContainerProfile`), not a machine setting.

- **Required for:** every workload except `hearth-c-ref` at its pinned tag — X3's generated kernels and all Forge candidates.
- **Fidelity cost:** the supervisor must grant the scratch tree; large-page allocation needs `SeLockMemoryPrivilege` and direct I/O needs sector-aligned handles [R11]. **Whether both work inside an (LP)AppContainer on this box is unverified** [known weakness]; until it is verified, the refusal table in §4 applies.

### 3.2 Windows Filtering Platform (WFP) / firewall — belt-and-braces, needs a system change
A persistent outbound block for the measurement principal also catches any path AppContainer leaves open.

- **System change:** yes (administrator). Command for Pierce (corrected in revision 2: `-LocalUser` takes an SDDL **authorisation** string, `D:(A;;CC;;;<SID>)`, not an owner string):
  ```
  $sid = (Get-LocalUser MithrilMeasure).SID.Value
  New-NetFirewallRule -DisplayName 'Mithril-Measure-NoEgress' -Direction Outbound `
      -Action Block -Profile Any -LocalUser "D:(A;;CC;;;$sid)" -Enabled True
  # check what was installed:
  Get-NetFirewallRule -DisplayName 'Mithril-Measure-NoEgress' | Get-NetFirewallSecurityFilter
  ```
  The parameter format follows reviewer 1's reading of the cmdlet; the local help on this laptop has no description for `-LocalUser` (help content not installed) [M, `Get-Help New-NetFirewallRule -Parameter LocalUser`, 2026-10-16], so the format is **unverified here**. The positive-control probe (§5 item 3) is the real check: if the rule does not block, the self-test fails.
- **Fidelity cost:** none.

### 3.3 A separate low-privilege user — needed anyway, enables the above
Run the harness as a dedicated standard user `MithrilMeasure`, distinct from Pierce's admin account ([03 §11.3](../../docs/architecture/03-trust.md)). This scopes the ACLs (§2.1), the firewall rule (§3.2) and the gate-key isolation ([03 §11.3](../../docs/architecture/03-trust.md)) to a principal the candidate cannot impersonate.

- **System change:** yes — creating a local user is admin. Command for Pierce (elevated):
  ```
  $pw = Read-Host -AsSecureString 'Password for MithrilMeasure'
  New-LocalUser -Name 'MithrilMeasure' -Password $pw -PasswordNeverExpires -AccountNeverExpires `
      -Description 'Mithril X4 measurement principal (standard user, no admin)'
  # do NOT add to Administrators; leave in Users only
  ```
  (Per the safety rules, Pierce creates this account and sets its password; the service never enters a password.)
- **Verify (service):** the harness asserts its token is the `MithrilMeasure` SID, non-elevated, not in Administrators.

### 3.4 Windows Sandbox / Hyper-V container — strongest isolation, wrong fidelity
Windows Sandbox (or a Hyper-V-isolated container) gives a throwaway VM with network off by a config switch.

- **System change:** yes — `Enable-WindowsOptionalFeature -Online -FeatureName 'Containers-DisposableClientVM' -NoRestart` and a `.wsb` config with `<Networking>Disable</Networking>`.
- **Fidelity cost:** **disqualifying for the measured path.** A VM adds a virtual NVMe/scheduler/memory layer, so decode and NVMe timings inside it do not reflect the bare-metal 9950X/990 PRO rooflines ([06 §5.2](../../docs/architecture/06-forge.md)). Not used for performance measurement; possibly later for correctness-only execution, out of X4's scope.

---

## 4. The chosen stack and the refusal table

**Decision [G], layered:**

1. **Job Object** (no system change) — limits incl. affinity/priority, no child processes, kill-on-close.
2. **LPAC (or AppContainer) with no capabilities** (no system change) — network and broker block; **mandatory for every untrusted workload**.
3. **Separate low-privilege user `MithrilMeasure`** (Pierce creates once) — scopes ACLs, the firewall rule and gate-key isolation.
4. **WFP / firewall outbound block for that user** (Pierce installs once) — belt-and-braces.

**Refusal table [target] (new in revision 2).** The service decides from the self-test, never from configuration flags:

| State verified by the self-test | `hearth-c-ref` (trusted C) | X3 kernels, Forge candidates, any other workload |
|---|---|---|
| 1 + 2 (LPAC/AppContainer works with large pages and direct I/O) + 3 + 4 | run | run |
| 1 + 2, without 3/4 | run | run, with a logged warning (gate-key threat of 03 §11.3 open) |
| 1 + 3 + 4, AppContainer not usable | run | **REFUSE** (no broker block; §3.2 blocks network only) |
| 1 only, or neither AppContainer nor `MithrilMeasure` | run in degraded mode, loud warning, recorded in every fact | **REFUSE** |
| any self-test item failing | **REFUSE** | **REFUSE** |

WSL2 is the alternative container the architecture names for the correctness path ([06 §5](../../docs/architecture/06-forge.md)); for X4's *timing* path, bare metal under this stack is required so the rooflines are the box's own.

**What needs no system change:** Job Object, LPAC/AppContainer, the explicit environment, fresh scratch, the self-test probes. **What Pierce runs once:** create `MithrilMeasure` (§3.3), the ACLs (§2.1), the outbound firewall rule (§3.2), and the hygiene settings of [MEASUREMENT-SERVICE.md §7](MEASUREMENT-SERVICE.md).

---

## 5. Startup self-test (the sandbox verifies itself, then refuses on failure)

Before any workload code runs, the harness runs a fixed self-test inside the sandbox, and the orchestrator runs the **same probes once outside it**. Every probe's result and error code is recorded in the session fact. Probes are a sample of the paths an attacker could use, not a proof that none exists [known weakness].

1. **Token.** `MithrilMeasure`, non-elevated, not in Administrators; AppContainer/LPAC SID present when required (§4 table).
2. **Job limits.** The limits are present; the process cannot create a child (probe `CreateProcess` fails); affinity and priority equal the job values.
3. **Network, with a positive control (rewritten).** Revision 1's probe — a connect to a black-hole address — fails by timeout whether or not egress is blocked, so it passed on an open machine and never tested loopback. Now: the orchestrator (outside the sandbox) opens a listener it knows accepts connections **on loopback and on the box's LAN address**. Inside the sandbox, a connect to each must fail with a **policy denial** — an access-denied class error (expected `WSAEACCES`, 10013 [inference; the exact code is recorded on first run and pinned]), **not a timeout** — and a DNS lookup of a name not in the hosts file must fail. The orchestrator then runs the same three probes from outside the sandbox and requires them to **succeed**; a probe that fails outside the sandbox is broken, and the session refuses. *If DNS resolution succeeds inside the sandbox* (the system resolver service could perform lookups on the process's behalf; unverified on this box), that is a residual channel and untrusted workloads are refused until it is closed.
4. **Brokered paths (new).** Inside the sandbox each of these must fail with access-denied (and succeed, where meaningful, from the outside control): out-of-process COM activation of a stock out-of-process server (`CoCreateInstance` with `CLSCTX_LOCAL_SERVER`); opening any named pipe other than the inherited supervisor pipe (a pipe the orchestrator creates for the probe); connecting to the Task Scheduler service and to WMI (`root\cimv2`). These cover a6b.
5. **Sealed data unreachable (new).** Opening each sealed file for read **and** write fails through: its path, its 8.3 short name, a case variant, its `::$DATA` stream, a `\\?\` path, the volume-GUID path, and a hard link or junction created in scratch pointing at it (creating the link must itself fail). Scratch is empty at start and writable.
6. **FP and binary rules.** The MXCSR default is set; the RDTSC-in-candidate ban is in force for Forge builds ([03 §6.2](../../docs/architecture/03-trust.md)).
7. **Profile hash** matches ([MEASUREMENT-SERVICE.md §7](MEASUREMENT-SERVICE.md)).

The self-test is itself a planted-hack target: [HACK-SUITE.md](HACK-SUITE.md) batch (a) includes a sandbox-flag flip and break-away (a6), delegation through out-of-job processes (a6b), runtime writes to sealed data through alternate names (a8b), cross-run state through scratch (a15b) and affinity/priority self-elevation (a31).

---

## 6. Known weaknesses (carried into the prereg)

- **(LP)AppContainer + large pages + direct I/O is unverified on this box.** If they do not work, every untrusted workload is refused (§4) until a fix is designed; X4 can still calibrate on `hearth-c-ref`. [known weakness]
- **Standard-user separation may not be in place for X4.** Without `MithrilMeasure`, only `hearth-c-ref` runs (degraded, logged); X3 kernels are refused unless LPAC works. The prereg records this.
- **Probes are samples.** Network, broker and alternate-name probes test listed paths; an unlisted broker that grants `ALL RESTRICTED APPLICATION PACKAGES` would not be caught by the self-test. LPAC narrows that set; the M4 Adversary should hunt for such brokers. [known weakness]
- **DNS through the system resolver** is untested; see §5 item 3.
- **The X4 live adversary is weak** (`hearth-c-ref` and X3 kernels written in good faith). The sandbox's real test comes at M4; X4 validates it against batch (a) and, when available, blind batch (b) ([HACK-SUITE.md](HACK-SUITE.md)). [known weakness, by design]
