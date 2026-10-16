# R04 — AI-first languages and agent-native tooling landscape

*Research dossier for Mithril. Compiled 2026-10-11.*

**Method note.** The shared web-search budget ran out after about ten searches. Everything after that came from fetching primary sources directly: arXiv abstracts and PDFs, official project sites and blogs, raw READMEs, the Claude Code changelog, and the GitHub REST API for star counts and last-push dates (snapshot taken 2026-10-11). Star counts measure attention, not quality. As a result, the long tail of 2025–2026 newcomers (Hacker News launches, small GitHub projects) is under-surveyed, and absence from this dossier does not mean a project does not exist. Claims marked **[inference]** are my reasoning, not something a source states.

---

## Summary

1. **The strongest evidence for helping AI write code is about toolchains, not syntax.** There is measured evidence that each of these helps: (a) giving the model type and binding context ([Hazel/ChatLSP, OOPSLA 2024](https://arxiv.org/abs/2409.00921)), (b) constraining decoding with the type system ([Mündler et al. 2025](https://arxiv.org/abs/2504.09246)), (c) tight compile/check feedback loops ([RustAssistant](https://arxiv.org/abs/2308.05177), [RLEF](https://arxiv.org/abs/2410.02089)), (d) keeping docs passively in context ([Vercel eval](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals)), and (e) choosing the right edit format ([Aider](https://aider.chat/docs/unified-diffs.html)). I found **no** measured evidence that any "AI-native syntax" choice helps, including MoonBit's flat top-level structure. Confidence: high.
2. **Training-data gravity is the main risk for any new language.** A June 2026 study had Claude Code and Codex build 34 chess engines in 17 languages. Every language produced a working engine, but strong play appeared only in mainstream compiled languages, and cost rose steeply for exotic ones: about $2 for Java versus about $474 for COBOL ([Acher & Jézéquel 2026](https://arxiv.org/html/2606.13763)). Mojo, which has years of public code, still ships an agent skill to "correct pretrained assumptions" ([modular/skills](https://github.com/modular/skills)). Confidence: high.
3. **The "AI-first language" label mostly describes a toolchain bundle.** That bundle is fast checking, an MCP and LSP surface, an agent loop, docs for LLMs, and verification. MoonBit, Unison, Jac, Lean and Bend 2 all converge on it. The concrete AI-specific language features that exist are verification annotations (MoonBit 0.9 `proof_*`, Bend `LAWS.bend`), LLM-call operators (Jac `by llm`, BAML functions), and effect-annotated tool calls (Quasar). Confidence: high.
4. **Verification-in-the-loop is the clearest 2025–2026 trend.** MoonBit 0.9 added SMT-backed `moon prove` with the explicit model "AI guesses, the prover checks" ([MoonBit](https://www.moonbitlang.com/blog/moonbit-0-9-release)). Bend 2 rebranded itself as "a fast language that blocks AI mistakes via proof" ([bendlang/bend](https://github.com/HigherOrderCO/Bend)). On the vericoding benchmark, off-the-shelf LLMs verify **Dafny 82% vs Verus 44% vs Lean 27%** ([arXiv 2509.22908](https://arxiv.org/abs/2509.22908)). SMT-backed, annotation-style verification is currently far easier for agents than tactic proofs. Confidence: high for the numbers, medium on how long the gap persists.
5. **Lean 4 is the de-facto language of AI mathematics.** AlphaProof, Harmonic's Aristotle (IMO 2025 gold-equivalent), Seed-Prover (5/6 at IMO 2025), DeepSeek-Prover-V2, Kimina-Prover and Goedel-Prover-V2 all target Lean. In 2026 the Lean FRO is building agent-facing infrastructure: `lean-beam` for speculative tactic execution over MCP, Comparator as a proof judge, `lake check`, and agent-friendly `grind` errors ([Lean FRO roadmap Y4-1](https://lean-lang.org/fro/roadmap/y4-1/)). As a general-purpose *performance* language Lean is still immature; compiler work (stack allocation, uniqueness annotations, array programs) is scheduled to start in 2027. Confidence: high.
6. **Seed claim F1 is real; F3 and F4 are wrong.** `openai/math` exists: 719 manuscripts, 372 families, about 42% formalized in Lean, with Comparator challenges ([openai/math](https://github.com/openai/math)). But family 087 is the **Mahler conjectures**, not SDP thresholds (that is family 102), and the Mézard–Parisi spin-glass result is family **221**, not 197. Family 197 is Kaplansky's direct-finiteness conjecture. Confidence: high (checked against the repo's own index).
7. **Agent infrastructure has standardized.** MCP is everywhere (current spec docs are versioned 2026-07-28). Claude Code gained a built-in LSP tool in v2.0.74 ([changelog](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)). gopls ships an MCP server ([go.dev](https://go.dev/gopls/features/mcp)). AGENTS.md is used by more than 60k projects under Linux Foundation stewardship ([agents.md](https://agents.md/)). Compilers already emit structured diagnostics: rustc JSON with fix-applicability levels, and SARIF from GCC, Clang and MSVC.
8. **llms.txt is widely published and barely evidenced.** The standard is adopted by documentation platforms, but Google said no AI service had announced using it, and a host of about 20k domains saw no AI-bot fetches ([SEJ, Apr 2025](https://www.searchenginejournal.com/google-says-llms-txt-comparable-to-keywords-meta-tag/544804/)). The best adjacent evidence favors a **compressed docs index sitting in the agent's context** (100% vs 53% baseline) over on-demand retrieval ([Vercel](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals)). Confidence: medium.
9. **The prompt-DSL generation is splitting.** LMQL has been dormant since May 2025 (GitHub API). DSPy has become an optimization framework: GEPA (ICLR 2026 oral) and, as of 3.3, `dspy.Flex` let the optimizer rewrite a module's code, not just its prompts. BAML now calls itself "the programming language for agents." Dana's repo has pivoted to a Python API. Mithril should learn from DSPy's *optimize the program against a metric* stance, not from the prompt-DSL syntax.
10. **For Mithril, borrow:** the proof-obligation-as-artifact pattern (LAWS.bend, MoonBit `proof_*`), typed holes plus a hole-context API (Hazel), effects in types (Koka, Unison abilities, Quasar), definition-level content addressing (Unison), JSON diagnostics with applicability (rustc), a `mithc guide`/skill/MCP trio, and type-constrained decoding. Hearth can uniquely host that decoding locally. **Avoid:** novel surface syntax, marketing claims without evals, unaudited AI-written compilers, and making Lean tactic proofs the *only* verification path.

---

## Findings

### 1. What the evidence says helps an AI write code (cross-cutting)

**1.1 Training-data gravity (high confidence).**
- *Chess engine study.* Acher & Jézéquel (arXiv 2606.13763, June 2026) had Claude Code and Codex build 34 engines in 17 languages: Python, Java, C, C++, Rust, Ruby, APL, Icon, Lean 4, Why3, Rocq, LaTeX, CSS/HTML, SQL, COBOL, x86-64 assembly and Brainfuck. Every language reached a feature-rich working engine. Mainstream compiled languages reached roughly 1900–2100 Elo, while exotic languages plateaued "hundreds to thousands" of Elo lower. Normalised cost per engine ranged from about $1.96 (Java, 3 prompts) to about $175 (Lean 4) and about $474 (COBOL, 24 prompts). The agents' self-estimated Elo was 200–1100 points too high, and a few engines cheated by calling a chess library ([abstract](https://arxiv.org/abs/2606.13763), [full text](https://arxiv.org/html/2606.13763)).
- *Low-resource languages.* MultiPL-T showed code LLMs underperform on OCaml, Racket and similar languages, and that LLM-translated, test-validated synthetic data improves fine-tuned open models ([arXiv 2308.09895](https://arxiv.org/abs/2308.09895)).
- *Mojo.* Mojo has existed publicly since 2023, yet Modular ships a `/mojo-syntax` skill that "corrects pretrained assumptions so your agent writes modern Mojo" ([modular/skills](https://github.com/modular/skills)). Language churn creates stale priors.
- **[inference]** A brand-new language starts at the worst point on the cost curve. Mithril must win back that cost through toolchain feedback, in-context documentation and familiar surface syntax, not by expecting frontier models to learn it from pretraining.

**1.2 Types as context and as constraints (high confidence).**
- *Hazel / ChatLSP* (OOPSLA 2024). Giving GPT-4 the type definitions and relevant headers for a typed hole tripled the tests passed. Error-correction rounds with the language server roughly doubled them again. For StarCoder2-15B, type information raised correct solutions by about an order of magnitude. The same techniques ported to TypeScript gave smaller gains (about 1.5× from headers, about 1.2× from error rounds) ([arXiv 2409.00921](https://arxiv.org/abs/2409.00921), [HTML](https://arxiv.org/html/2409.00921)). The paper proposes **ChatLSP**, a conservative LSP extension that lets language servers expose static context to AI.
- *Type-constrained decoding* (Mündler, He, Wang, Sen, Song, Vechev; PACMPL article 171, DOI 10.1145/3729274). In LLM-generated TypeScript, about 94% of compilation errors were type errors and only about 6% were syntax errors. Grammar-only constrained decoding therefore misses most failures. Type-constrained decoding using prefix automata and a search over inhabitable types cut compile errors by more than half. It raised functional correctness by 3.5–5.5% (relative) for synthesis and translation, and by 37% (relative) for repair ([arXiv 2504.09246](https://arxiv.org/abs/2504.09246); numbers from the paper's introduction).
- **[inference]** This needs logit-level access, which closed APIs do not expose for arbitrary type systems, but a local engine such as Hearth does.

**1.3 Feedback loops (high confidence on direction, medium on magnitudes).**
- RustAssistant fixed real-world Rust compilation errors with about 74% peak accuracy by feeding compiler diagnostics to an LLM ([arXiv 2308.05177](https://arxiv.org/abs/2308.05177)).
- RLEF used RL on execution feedback and reported state-of-the-art competitive-programming results with an order-of-magnitude fewer samples ([arXiv 2410.02089](https://arxiv.org/abs/2410.02089)).
- MoonBit's argument for agent platforms is objective pass/fail, a fast loop and an operator-controlled sandbox ([MoonBit blog, Oct 2026](https://www.moonbitlang.com/blog/building-agents-moonbit)). It offers no quantitative evidence.

**1.4 Which verification language agents succeed in (high confidence).**
- The vericoding benchmark has 12,504 specifications. Off-the-shelf LLMs succeeded on **82% in Dafny, 44% in Verus/Rust and 27% in Lean**. On pure Dafny verification, LLM performance rose from 68% to 96% in about a year. Adding natural-language descriptions did not help significantly ([arXiv 2509.22908](https://arxiv.org/abs/2509.22908)).
- Kleppmann argues that AI will make formal verification mainstream because proof checkers make hallucinations harmless, leaving specification as the hard part ([blog, Dec 2025](https://martin.kleppmann.com/2025/12/08/ai-formal-verification.html)).
- **[inference]** Auto-active verification, where the user writes requires/ensures/invariants and an SMT solver discharges them, currently suits agents better than interactive tactic proofs. Lean's lead in competition mathematics comes from heavy RL investment in specialized provers, not from general agents.

**1.5 How docs reach the agent (medium confidence).**
- *Vercel* (Jan 27 2026), testing Next.js 16 APIs absent from training data:

  | Configuration | Pass rate |
  |---|---|
  | Baseline, no docs | 53% |
  | Docs skill, default | 53% (the skill was never invoked in 56% of cases) |
  | Skill with explicit instructions | 79% |
  | 8 KB compressed docs index in AGENTS.md | 100% |

  Source: [Vercel](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals). This is a single-vendor eval on one framework.
- *llms.txt* evidence is anecdotal and negative for crawlers (see §5.3).

**1.6 Edit format matters (medium confidence).**
- On a laziness benchmark, switching GPT-4 Turbo from SEARCH/REPLACE blocks to unified diffs raised the score from 20% to 61%. Disabling flexible patching increased edit errors about 9× ([Aider](https://aider.chat/docs/unified-diffs.html)). These are older models, but the result shows that the edit interface itself is a performance variable.
- Anthropic's text-editor tool is built around `view`, `str_replace`, `create` and `insert` ([Claude docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/text-editor-tool)). Text-anchored replacement, not AST operations, is the mainstream agent edit primitive today.

**1.7 Search (medium confidence).**
- Cursor (Nov 2025): adding semantic search to grep improved answer accuracy by 12.5% on average (6.5–23.5% by model). Code retention rose 0.3% overall and 2.6% on codebases with 1,000+ files ([Cursor](https://cursor.com/blog/semsearch)).
- Anthropic describes Claude Code's "just-in-time" retrieval with glob and grep, plus CLAUDE.md loaded up front, as avoiding "stale indexing and complex syntax trees" ([Anthropic engineering, Sep 2025](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)).
- The two leading harnesses therefore disagree on whether indexes are worth it. Both agree that cheap exact search is the base layer.

### 2. Languages and DSLs marketed as AI-first / agent-native

| Project | Core idea | Status / traction (2026-10) | Evidence it helps AI | Verdict |
|---|---|---|---|---|
| **MoonBit** | Rust-like, GC'd, targets Wasm/JS/native/LLVM; bundled toolchain; "AI-native" | Beta since Jun 2025; 0.8 (Feb 2026), 0.9 (Apr 2026); `moonbitlang/core` 1.2k★; compiler license not OSI (API: NOASSERTION) | Vendor demos only | Good toolchain ideas, unproven AI claims |
| **Mojo / MAX** | Python-like systems language on MLIR; CPU+GPU kernels | 1.0 on Aug 11 2026; compiler open-sourced Aug 18 2026 (Apache-2.0+LLVM exc.); `modular/modular` 29.9k★ | None AI-specific; ships skills + llms.txt | Not AI-first; a performance language with good agent docs |
| **Bend 2** (HigherOrderCO) | Pure, linear, parallel; proofs via `LAWS.bend`; GPU/CPU | New language (Bend 1/HVM not carried over); 23.5k★ (inherited); compiler "99% AI-written" | Demo only | The most explicit "language for AI" pitch; high risk |
| **Jac** (Jaseci) | Python superset; `by llm()` meaning-typed functions; `jac mcp`, `jac guide` | 746★; MIT | MTP paper (OOPSLA 2025) user study | Real evidence for the LLM-call abstraction, not for agent coding |
| **BAML** | Typed DSL/language for LLM functions; schema-aligned parsing | 9.4k★; Apache-2.0; active | Vendor blog posts | Useful pattern for typed LLM I/O |
| **Dana** (Aitomatic / AI Alliance) | "Agent-native" Python-like `.na` language | 62★; last push Mar 2026; repo now leads with a Python API | None | Hype > evidence |
| **LMQL** (ETH SRI) | Constraint-guided decoding with Python control flow | 4.2k★; last push May 22 2025 | Original papers | Dormant |
| **DSPy** (Stanford) | "Programming, not prompting"; optimizers | 38.6k★; active (3.3.x) | GEPA (ICLR 2026 oral) | Strongest evidence in this class |
| **Pel** | Lisp/Elixir-inspired orchestration language with syntax-level capabilities | arXiv only | No evaluation | Idea only |
| **Quasar** | Language for LLM code actions; effect-annotated external calls | COLM 2026 | Abstract gives no numbers | Interesting design (effects) |

**MoonBit**
- *Self-description.* An "AI native programming language toolchain for cloud and edge" ([docs](https://docs.moonbitlang.com/en/stable/language/index.html)). The about page says it is "LLM friendly" via "real-time semantic sampling" with no technical description ([about](https://www.moonbitlang.com/about-us)). I found no paper behind that phrase, so it is unverified.
- *Concrete AI-oriented choices,* from a June 2025 interview: mandatory explicit types on all top-level definitions; a flat structure that "reportedly" reduces KV-cache misses, with no measurement given; and the `moon` CLI serving as an LSP or MCP server ([Deep Engineering](https://deepengineering.net/p/designing-for-ai-and-humans-with)). **[inference]** The KV-cache rationale does not match how transformer inference works, since there are no cache "misses" in that sense. Treat it as marketing. The defensible version is that top-level type signatures give local context, which matches the Hazel result.
- *MoonBit 0.9 (Apr 2026).* First-class verification annotations (`proof_requires`, `proof_ensures`, `proof_invariant`, `proof_assert`), `.mbtp` predicate files, and `moon prove`, which translates obligations into SMT problems for solvers such as Z3. The workflow is explicitly "AI guesses, the prover checks." The post gives no success rates ([0.9 post](https://www.moonbitlang.com/blog/moonbit-0-9-release); examples in [moonbit-community/verified](https://github.com/moonbit-community/verified)).
- *MoonBit Pilot (Jul 2025).* A code agent that loops on `moon check`/`moon test` and uses native semantic search instead of grep. Vendor-reported: 126 warnings fixed in about 7 minutes, against about 35 minutes (partial) for Codex CLI and about 16 minutes (unfinished) for Cursor ([Pilot post](https://www.moonbitlang.com/blog/intro-moonbit-pilot)).
- *SeekMoon "ADE" (Sep 2026).* Token-level diff that ignores formatting churn, syntax-tree diff, IDE navigation inside diff review, and syntax-tree pattern search whose results feed agent context ([SeekMoon](https://www.moonbitlang.com/blog/seekmoon-from-ide-to-ade)). This is a review-side tool for humans supervising agents, which few projects address.
- *Fastcc (Feb 2026).* An AI agent built a self-hosting ARM64 C compiler of about 35k lines in about 10 days. The model was not named ([post](https://www.moonbitlang.com/blog/fastcc-ai-driven-development)).
- *Overall.* Strong toolchain integration and the most complete agent story. Its AI claims are vendor-only.

**Mojo / MAX**
- *Releases.* Mojo 1.0 shipped Aug 11 2026 with a source-stability goal for 1.x ([Modular 26.5](https://www.modular.com/blog/modular-26-5-mojo-1-0-is-here)). The compiler and toolchain were open-sourced Aug 18 2026 under Apache-2.0 with LLVM exceptions. Compiler contributions are not yet accepted, with a target of end-2026 ([Modular](https://modular.com/blog/mojo-open-source)).
- *Licensing.* The repo is Apache-2.0+LLVM, but "MAX usage and distribution" falls under the Modular Community License ([README](https://github.com/modular/modular)).
- *CPU kernels.* `max/kernels/src/linalg/matmul/cpu/` contains `vnni.mojo`, `neon.mojo`, `i8mm.mojo`, `apple_accelerate.mojo` and `default.mojo`. `quantization/` contains `per_channel_grouped_4bit.mojo` and `qmatmul_k.mojo` (GitHub API listing).
- *Standard library.* Exposes prefetch intrinsics, `compressed_store`, LLVM-dialect inline assembly and `CompilationTarget.has_avx512f()` ([mojolang.org llms-full](https://mojolang.org/llms-full.txt), [stdlib index](https://mojolang.org/llms-stdlib.txt)).
- *Agent-facing.* `mojolang.org/llms.txt` (version 1.1.0) with sectional `llms-*.txt` files and an `llms-full.txt` of about 1 MB, plus official skills with 7.2k+ downloads via skills.sh ([26.5 post](https://www.modular.com/blog/modular-26-5-mojo-1-0-is-here)).
- *Overall.* Mojo is the nearest existing competitor to Mithril's "hardware-native" pitch. It is not "AI-first," but it shows the agent-onboarding kit a new language needs.

**Bend 2.** The README reframes the project as a language for a world where "humans will eventually stop writing and reading code":
- `LAWS.bend` declares invariants. The agent must supply `PROOF.bend`, and the compiler rejects edits that break laws. The README pitches it as "`AGENTS.md` backed by proof" and onboards agents through `bend guide` plus an AGENTS.md snippet.
- *Stated limitations:* the compiler (not the kernel) is "99% AI-written and not yet fully audited"; the checker has no proof, while `--verdict` uses a kernel formalized in Lean; F32 is axiomatic; there are no tactics; and benchmarks are shown only as images ([README](https://github.com/HigherOrderCO/Bend), raw README fetched 2026-10-11).
- HVM3's last push was Jan 2026 (GitHub API).
- **[inference]** It is the closest existing embodiment of "agent writes code plus proof, compiler enforces." It is also a warning about unaudited AI-generated compilers and about performance claims that cannot be checked.

**Jac / Meaning-Typed Programming.** `by llm()` functions derive the prompt and output schema from the type signature and `sem` annotations. `jac guide` exports Agent Skills and `jac mcp` serves coding agents ([jaseci-labs/jac](https://github.com/jaseci-labs/jac)). The MTP paper (OOPSLA 2025) reports a user study where developers finished 3.2× faster with 45% fewer lines than with existing frameworks, and robustness to 50% degraded naming ([arXiv 2405.08965](https://arxiv.org/abs/2405.08965)). This is evidence for *programs calling LLMs*, not for *LLMs writing programs*.

**BAML / Dana / LMQL**
- *BAML* now calls itself "the programming language for agents": TypeScript-like static types that persist at runtime, typed errors, built-in tests, and bindings to Python, TS, Go, C# and Java ([repo](https://github.com/BoundaryML/baml)). Its schema-aligned parsing repairs malformed model JSON ([BoundaryML blog](https://boundaryml.com/blog/sota-function-calling)).
- *Dana* launched in June 2025 as "the world's first AI-powered programming language" ([ARC](https://www.arcweb.com/node/160981)). Its repo has 62★ and now presents a Python API (`adana`) ([repo](https://github.com/aitomatic/dana)).
- *LMQL's* last push was 2025-05-22 (GitHub API).
- **[inference]** Logit-level prompt languages lost relevance as the best models moved behind APIs with native structured outputs and tool calls.

**DSPy / GEPA.** GEPA (Agrawal et al., ICLR 2026 oral) evolves prompts by reflecting on execution traces. It beat GRPO by 6% on average and up to 20% with up to 35× fewer rollouts, and beat MIPROv2 by more than 10% ([arXiv 2507.19457](https://arxiv.org/abs/2507.19457)). DSPy 3.3.0's experimental `dspy.Flex` lets GEPA rewrite a module's whole implementation, including control flow and the Python-vs-LM-call balance, inside a sandboxed interpreter. An optional `program_trace` metric can penalize how a result was produced ([release notes](https://newreleases.io/project/github/stanfordnlp/dspy/release/3.3.0)). **[inference]** This is the most direct production precedent for Mithril's DGM-style loop: a metric-driven, sandboxed search over program structure with Pareto archives.

**Pel / Quasar.** Pel puts capability control in the syntax, removing the need for a sandbox. It also auto-parallelizes via dependency analysis and has Lisp-style restarts with LLM helper agents. The paper has no evaluation ([arXiv 2505.13453](https://arxiv.org/abs/2505.13453)). Quasar separates internal logic from effect-annotated external calls, enabling access control, auto-parallelization and conformal uncertainty. It appears at COLM 2026; the abstract has no numbers ([arXiv 2506.12202](https://arxiv.org/abs/2506.12202)).

### 3. Lean 4 — the AI mathematicians' language, and Lean as a programming language

**3.1 Provers (all Lean 4):**

| System | Date | Headline result (as reported by authors) | Source |
|---|---|---|---|
| AlphaProof (DeepMind) | Jul 2024; Nature paper Nov 12 2025 | With AlphaGeometry 2: IMO 2024 4/6 (28/42, silver). Problems were manually formalized; some took up to 3 days | [DeepMind](https://deepmind.google/discover/blog/ai-solves-imo-problems-at-silver-medal-level/) |
| Aristotle (Harmonic) | Oct 2025 | IMO 2025 gold-medal-equivalent; Lean search + informal lemma generation + geometry solver | [arXiv 2510.01346](https://arxiv.org/abs/2510.01346) |
| Seed-Prover (ByteDance Seed) | Jul 2025 | IMO 2025 5/6 fully proved; 78.1% of formalized past IMO problems; >50% PutnamBench; MiniF2F "saturated" | [arXiv 2507.23726](https://arxiv.org/abs/2507.23726) |
| DeepSeek-Prover-V2 | Apr 2025 | 671B: 88.9% MiniF2F-test; 49/658 PutnamBench | [arXiv 2504.21801](https://arxiv.org/abs/2504.21801) |
| Kimina-Prover Preview | Apr 2025 | 80.7% MiniF2F at pass@8192 (Qwen2.5-72B + RL); 1.5B/7B distills | [arXiv 2504.11354](https://arxiv.org/abs/2504.11354) |
| Goedel-Prover-V2 | Aug 2025 | 32B: 88.1% MiniF2F pass@32 (90.4% with self-correction); 86 PutnamBench problems at pass@184; 8B beats DS-Prover-V2-671B at pass@32 | [arXiv 2508.03613](https://arxiv.org/abs/2508.03613) |

Later versions of these systems (2026) were not checked because of the search limit.

**3.2 2026 infrastructure.**
- *openai/math.* 13.9k★; 719 manuscripts in 372 families from an unreleased OpenAI model (about 3 hours of ChatGPT Pro thinking per result over about 4,000 posed problems). About 42% of top-line results are formalized. The repo's Comparator challenges verify supporting results, explicitly "not the corresponding papers' main theorems" ([repo](https://github.com/openai/math), [README](https://raw.githubusercontent.com/openai/math/main/README.md), [Comparator challenges](https://github.com/openai/math/blob/main/lean/ComparatorChallenges/README.md)).
- *Comparator* (Lean FRO, built with feedback from the AIMO team). It checks that solution theorems match challenge statements, use only permitted axioms, and replay in the Lean kernel (optionally also in alternative kernels such as nanoda), with builds sandboxed under `landrun` ([leanprover/comparator](https://github.com/leanprover/comparator)).
- *Lean FRO Y4-1 roadmap (Sep 2026–Feb 2027)* ([roadmap](https://lean-lang.org/fro/roadmap/y4-1/)):
  - `lean-beam`, the agent interaction tool, becomes a supported product shipped with Lean.
  - `grind` and `bv_decide` will "fail faster" with errors and docs that work for agents.
  - Comparator ships in the distribution, and a `lake check` command rechecks with official or alternative kernels (`--paranoid`).
  - The compiler design leads to implementation in early 2027: stack-allocated objects, uniqueness annotations, better array programs.
  - A new `do` notation with intrinsic verification.
  - The Nerodia Lean/Python FFI.
- *lean-beam.* LSP extensions plus a broker that exposes `runAt`, which speculatively runs a tactic or command at a file position without editing the file. Concurrent probes are allowed, alongside sync/todo/save and proof-state queries, via CLI and MCP with a skill. It is a preview with no benchmarks ([leanprover/lean-beam](https://github.com/leanprover/lean-beam)).
- *lean-lang.org* calls Lean an "open-source programming language and proof assistant" and lists Mathlib at more than a million lines. It cites AWS Cedar, Microsoft SymCrypt via Aeneas, and a 2026 timeline of AI-lab Lean announcements (Anthropic, OpenAI) that are not linked to primary sources on the page ([lean-lang.org](https://lean-lang.org/)).

**3.3 Lean as a general-purpose language.** Lean is a self-described programming language with a C backend, and it is used in verification-heavy production settings such as Cedar ([lean-lang.org](https://lean-lang.org/)). However, the FRO's own roadmap puts core performance features (stack allocation, uniqueness, array-program support) in 2027 implementation work ([roadmap](https://lean-lang.org/fro/roadmap/y4-1/)). **[inference]** Lean is the right *proof host and spec language*. It is not the right *runtime language* for Hearth-class SIMD/NVMe code in 2026–2027. LLM vericoding success is also lowest in Lean (27%) ([arXiv 2509.22908](https://arxiv.org/abs/2509.22908)).

### 4. PL-design languages relevant to Mithril (not AI-marketed)

| Language | Core idea | Status (2026-10) | Borrow / avoid for Mithril |
|---|---|---|---|
| **Unison** | Content-addressed definitions; abilities (algebraic effects); code in a database | 1.0 (Nov 25 2025); 1.1 (Jan 2026) with new MCP tools; MCP server since Aug 2025 (typecheck, search Share, inspect project); Unison Cloud open-sourced (MIT) Oct 8 2026; 6.8k★ ([blog](https://www.unison-lang.org/blog/), [1.0](https://www.unison-lang.org/unison-1-0/), [MCP](https://www.unison-lang.org/blog/ucm0545/)) | **Borrow** hash-addressed definitions to cache type checks, proofs and benchmarks per hash; merge conflicts only on the same definition. **Avoid** code-in-database (agents' tools are file-based). No evidence yet that it helps AI |
| **Hazel** | Typed holes; every edit state is meaningful; total type-error localization (POPL 2024 distinguished) | Research (U. Michigan); active ([hazel.org](https://hazel.org/)) | **Borrow** holes as first-class, the typing context of a hole as an API (ChatLSP), and error localization. Best measured evidence of any language here |
| **Roc** | Fast functional language; platform/application split | Compiler rewritten in Zig (repo about 94% Zig by bytes, GitHub API); "not ready for a 0.1 release"; its AGENTS.md bans heuristics and workarounds and requires explicit data flow between stages ([repo](https://github.com/roc-lang/roc), [AGENTS.md](https://raw.githubusercontent.com/roc-lang/roc/main/AGENTS.md)) | **Borrow** its compiler-governance-for-agents rules (no fallback heuristics; invariants as debug assertions) |
| **Gleam** | Small typed language on BEAM/JS | v1.19 (Oct 5 2026); steady LSP feature work (rename, find references); 22k★; no AI posts ([news](https://gleam.run/news/)) | **Borrow** smallness and stability; a small language is easier to fit in context **[inference]** |
| **Vale** | Generational references; regions; Higher RAII | **Archived**; successor "Valen" ([vale.dev](https://vale.dev/)) | Avoid as a dependency; generational references remain an idea for checked handles |
| **Hylo** | Mutable value semantics; subscripts; no references | Early; Swift-6.3-implemented compiler via LLVM; 2025 papers ([hylo-lang.org](https://hylo-lang.org/)) | **Borrow** MVS for aliasing-free reasoning (relevant to seed B5) |
| **Austral** | Linear types plus capability security; spec small enough for one person | Last push Jul 2025 ([austral-lang.org](https://austral-lang.org/), GitHub API) | **Borrow** capabilities for agent sandboxing and linear resources (file handles, DMA buffers) |
| **Koka** | Row-typed effects and handlers; Perceus RC; FBIP reuse | v3.2.8 (Sep 17 2026); "not ready for production" ([docs](https://koka-lang.github.io/koka/doc/index.html)) | **Borrow** effects in types, so an agent can read from the signature what code may do; Perceus/FBIP for in-place functional updates |
| **Carbon** | C++ successor with interop | Experimental; 0.1 MVP "soonest" end-2026; repo has AGENTS.md and `.agents/skills` ([repo](https://github.com/carbon-language/carbon-lang), [roadmap](https://raw.githubusercontent.com/carbon-language/carbon-lang/trunk/docs/project/roadmap.md)) | Shows that even C++-successor projects now ship agent onboarding |
| **Zig** | Comptime; explicit allocators; C interop | 0.16 (Apr 2026), 0.17 (Oct 2 2026); moved to Codeberg (Nov 2025); **strict No LLM / No AI policy** ([news](https://ziglang.org/news/), [CoC](https://ziglang.org/code-of-conduct/), [Codeberg post](https://ziglang.org/news/migrating-from-github-to-codeberg/)) | **Borrow** comptime and explicit allocation. Note the community friction: anti-AI governance is a real counter-current |
| **Jai** | Game-oriented; compile-time execution | Beta as of Aug 2023 per [Wikipedia](https://en.wikipedia.org/wiki/Jai_(programming_language)); no public release found (search-limited) | Not usable as a reference implementation |
| **Futhark** | Pure data-parallel arrays; uniqueness types; AD; CUDA/HIP/OpenCL/multicore | Research but "quite usable" ([futhark-lang.org](https://futhark-lang.org/)); active | **Borrow** uniqueness types for in-place updates and its parallel-combinator vocabulary |
| **Dex** | Typed indices for arrays; AD | "Experimental research project"; last push Jan 2026 ([repo](https://github.com/google-research/dex-lang)) | **Borrow** index-typed arrays (shapes in types) |

### 5. Agent-facing infrastructure

**5.1 LSP used by agents.**
- *Claude Code* added an LSP tool (go-to-definition, references, hover) in v2.0.74. Plugins declare servers in `.lsp.json`. Later fixes include diagnostics arriving stale after edits and per-turn slowdowns when a server publishes diagnostics for thousands of files ([changelog](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md), [plugins reference](https://code.claude.com/docs/en/plugins-reference)).
- *OpenCode* supports about 40 language servers for diagnostics, disabled by default ([docs](https://opencode.ai/docs/lsp/)).
- *Serena* (30.2k★) wraps LSP into symbol-level MCP tools for more than 40 languages: find symbol, references, rename, replace symbol body, insert before/after symbol. Its evaluation of about 20 tasks is not quantified on the README ([oraios/serena](https://github.com/oraios/serena)).
- Also: `mcp-language-server` (1.6k★) and Microsoft's `multilspy` (612★) (GitHub API).
- **[inference]** The ecosystem converges on "LSP as the agent's semantic API," but the evidence that it beats grep plus compile loops is still vendor-only, with ChatLSP as the exception.

**5.2 Compiler and language-server MCP servers.**
- gopls has an experimental MCP server (v0.20+), attached (sharing the editor's LSP session, sees unsaved buffers) or detached (stdio). It ships model instructions via `gopls mcp -instructions` rather than forcing them on clients ([go.dev](https://go.dev/gopls/features/mcp)).
- The same pattern appears in Unison (MCP), Jac (`jac mcp`), MoonBit (`moon` as MCP server), Lean (`lean-beam` MCP; community `lean-lsp-mcp`, 527★), and ast-grep (`ast-grep-mcp`, 475★, experimental; its text output uses about 75% fewer tokens than JSON) ([ast-grep-mcp](https://github.com/ast-grep/ast-grep-mcp)).
- The MCP docs are currently versioned 2026-07-28 ([modelcontextprotocol.io](https://modelcontextprotocol.io/)).

**5.3 llms.txt, AGENTS.md and skills.**
- *llms.txt* was proposed by Jeremy Howard on Sep 3 2024; v2 is dated Aug 10 2026. The site cites adoption (thousands of sites, Lighthouse audit, OpenAI/Anthropic/Gemini docs) but no effectiveness data ([llmstxt.org](https://llmstxt.org/)).
- *Counter-evidence:* Google's John Mueller said no AI service had announced using it, and a host of about 20k domains saw no meaningful AI-bot fetches ([SEJ](https://www.searchenginejournal.com/google-says-llms-txt-comparable-to-keywords-meta-tag/544804/)). Anecdotal, not a log study.
- *My probes (2026-10-11).* llms.txt was served by docs.claude.com, mojolang.org, modelcontextprotocol.io, docs.boundaryml.com, ast-grep.github.io and svelte.dev (which offers small, medium and full variants). It returned 404 on lean-lang.org, gleam.run, ziglang.org, doc.rust-lang.org, docs.python.org, unison-lang.org, docs.moonbitlang.com and dspy.ai.
- **[inference]** The value of llms.txt is as an *agent-fetchable* docs bundle (an agent's WebFetch, or a tool such as Context7 at 62.9k★, per the GitHub API), not as a crawler signal.
- *AGENTS.md* is used by more than 60k projects, supported by about 20 agents, and stewarded by the Agentic AI Foundation under the Linux Foundation ([agents.md](https://agents.md/)). Roc, Carbon and Bend all ship one.

**5.4 Structured diagnostics.**
- *rustc* `--error-format=json` emits one JSON object per line with a stable `code` and `explanation`, primary and secondary spans with byte offsets, and child notes. Each `suggested_replacement` carries a **`suggestion_applicability`** of `MachineApplicable`, `MaybeIncorrect`, `HasPlaceholders` or `Unspecified`. Consumers are told to parse forward-compatibly ([rustc book](https://doc.rust-lang.org/rustc/json.html)).
- *GCC* emits SARIF 2.1.0 (`-fdiagnostics-format=sarif-stderr|sarif-file`). `-fdiagnostics-add-output=sarif:version=2.1|2.2-prerelease` adds a sink. Fix-its are available as `-fdiagnostics-parseable-fixits` or as a unified diff via `-fdiagnostics-generate-patch` ([GCC docs](https://gcc.gnu.org/onlinedocs/gcc/Diagnostic-Message-Formatting-Options.html)).
- *Clang* has `-fdiagnostics-format=sarif`, flagged unstable ([Clang manual](https://clang.llvm.org/docs/UsersManual.html)). *MSVC* has `/experimental:log` and `SARIF_OUTPUT_PIPE` ([MS Learn](https://learn.microsoft.com/en-us/cpp/build/reference/sarif-output)). GitHub code scanning ingests SARIF ([GitHub docs](https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/sarif-support-for-code-scanning); [SARIF 2.1.0 spec](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)).
- **[inference]** The seed's H5 idea already exists in production form. Mithril's contribution would be *semantic* fix-its (alignment, aliasing, determinism, performance) with applicability levels and a proof or benchmark obligation attached.

**5.5 AST-level search and edit.**
- *ast-grep* (16.2k★) offers structural search, lint and rewrite. *Tree-sitter* (27.2k★) underlies most of it (GitHub API).
- Aider's repo map uses tree-sitter, PageRank-style ranking of referenced identifiers, and a default budget of 1k tokens ([repo map](https://aider.chat/docs/repomap.html), [tree-sitter post](https://aider.chat/2023/10/22/repomap.html)).
- SeekMoon adds syntax-tree diffs for review ([SeekMoon](https://www.moonbitlang.com/blog/seekmoon-from-ide-to-ade)).
- Mainstream agent editing remains text-anchored (`str_replace`) (§1.6). **[inference]** AST tools win for *search and review*. For *editing*, a language should make text edits robust: canonical formatting, one definition per anchor, no layout-sensitive semantics. AST-only editing is not the answer.

**5.6 Code search and indexing.** See §1.7 (Cursor +12.5% with embeddings; Anthropic's grep-first JIT). Sourcegraph's trigram engine `zoekt` (2k★) remains the open-source base for large-scale exact search (GitHub API).

### 6. Hype-vs-evidence scorecard

| Claim | Status |
|---|---|
| "AI-native syntax" (flat structure, KV-cache-friendly code) helps LLMs | **No evidence found**; the mechanism as stated is dubious |
| Types and typing context improve LLM code | **Measured** (Hazel; type-constrained decoding) |
| Compiler feedback loops improve LLM code | **Measured** (RustAssistant, RLEF) |
| Verification makes AI code trustworthy | **Mechanism sound** (checkers reject bad proofs); agent success depends heavily on the verifier (Dafny 82% vs Lean 27%) |
| LSP/MCP semantic tools beat grep | **Mixed**; embeddings +12.5% (Cursor) vs grep-first (Anthropic); LSP gains unquantified outside ChatLSP |
| llms.txt helps AI | **Unproven for crawlers**; passive docs-in-context is supported by one eval |
| New languages can be learned by agents | **Yes, but at a cost multiple** (chess study) |
| Content addressing helps AI | **Untested** |

---

## Implications for Mithril

1. **Design the toolchain as the product, and treat the language as the toolchain's IR.** [inference, high confidence] Every AI-first project with traction converges on `check`/`test`/`prove` loops, MCP plus LSP, a `guide` command, skills and AGENTS.md. Ship `mithc check --json`, `mithc prove`, `mithc bench --json`, `mithc guide`, `mithc mcp` and an LSP from day one. Use gopls' split between attached and detached modes, and publish model instructions separately from the protocol.
2. **Use a familiar surface syntax.** The chess study's cost curve and Mojo's "correct pretrained assumptions" skill both argue for C/Rust/Python-adjacent syntax. Make it small (Gleam-sized) so the complete reference fits in an 8–40 KB compressed index, which is what won Vercel's eval. Novel syntax is a tax paid on every agent turn. [inference]
3. **Make diagnostics a typed API.** Adopt rustc's model of stable error codes, byte-offset spans, children and `suggestion_applicability`. Emit SARIF 2.1.0 as well so GitHub and IDE tooling works for free. Go beyond rustc with *semantic fix-its* that carry obligations, for example "align to 64: MachineApplicable; requires re-running bench X" or "reorder reduction: changes FP result; violates determinism contract D."
4. **Make typed holes and hole-context queries first-class (Hazel/ChatLSP).** Every partial program should typecheck. Expose `mithc hole-context <id>` returning expected type, bindings in scope, relevant type definitions and relevant headers. This is the best-measured lever in the literature (3× tests passed for GPT-4; 10× for StarCoder2).
5. **Offer two verification tiers.** Tier 1 is auto-active, SMT-backed `requires`/`ensures`/`invariant` in the Dafny and MoonBit-0.9 style, because agents succeed far more often there. Tier 2 exports obligations to Lean, checked with Comparator, for deep properties such as kernel equivalence. **Do not** make Lean tactic proofs the only path (vericoding: Lean 27% vs Dafny 82%). Keep the proven trusted core small and auditable. Bend's "99% AI-written compiler, not fully audited" shows what to avoid.
6. **Make proof obligations files ("LAWS").** Borrow Bend's `LAWS.bend` and MoonBit's `.mbtp`: a project-level file of invariants the compiler enforces on every edit. Hearth's `INVARIANTS.md` (INV-DET-1/2/3, INV-LOSSLESS-DEFAULT) is a natural first LAWS file. Make every law say how it is checked: proof, SMT, golden test, differential test or mutation test.
7. **Put effects and capabilities in types.** Following Koka, Unison abilities, Quasar and Austral, function signatures should state I/O, allocation, nondeterminism, FP-reassociation, thread use and unsafe memory. An agent can then read from the signature alone whether an edit may break INV-DET-3, and the compiler can refuse a reduction-order change inside a function declared `canonical_fp`. [inference]
8. **Content-address definitions and cache evidence by hash (Unison).** Proofs, benchmark results and golden outputs attach to definition hashes, so an agent's edit invalidates exactly the evidence it touches. That gives DGM-style archives deduplication and lineage for free. Keep source in plain files, because agents' tools are file-based. [inference]
9. **Make text edits robust instead of forcing AST edits.** Use a canonical formatter run by the compiler, unique anchors (one definition per anchor), no significant whitespace in semantics, and structural diff and search for review (SeekMoon, ast-grep). Provide an `ast-grep`-style pattern language over Mithril syntax for search and codemods.
10. **Offer type-constrained decoding as a feature of the Mithril toolchain plus a local engine.** The prefix-automaton approach cuts compile errors by more than half. Closed APIs cannot do this for a custom type system, but a local engine can (see Hearth). [inference]
11. **Treat the DGM loop as DSPy-Flex/GEPA, not as free-form self-modification.** A metric with textual feedback, a sandbox, a Pareto archive and trace-aware metrics (penalize nondeterminism or bytes moved) is the evidenced pattern ([GEPA](https://arxiv.org/abs/2507.19457), [dspy.Flex](https://newreleases.io/project/github/stanfordnlp/dspy/release/3.3.0)).
12. **Run evals before claims.** Every AI-native claim in this landscape that lacks an eval (MoonBit sampling, Dana, Bend speed GIFs) is unverifiable. Mithril should publish a cost-per-task curve (the chess-study method) for agents writing Mithril vs C vs Rust on Hearth kernels, with the INV-HONEST rule applied to language claims.
13. **Expect cultural headwinds.** Zig's no-LLM policy and Codeberg move show that "built for AI" can repel part of the systems-programming community. Position Mithril as "verified-by-construction" rather than "AI-written."

## Implications for Hearth

1. **Make Hearth's diagnostics agent-readable now, at near-zero cost.** Hearth already builds with `-Wall -Wextra -ffp-contract=off` and has ASan/UBSan options (CMakeLists.txt). Add SARIF sinks to CI: GCC `-fdiagnostics-add-output=sarif`, Clang `-fdiagnostics-format=sarif`, MSVC `/experimental:log`. Add `compile_commands.json` for clangd, so Claude Code's LSP tool and Serena work on the C engine. [inference]
2. **Hearth's governance already matches the evidenced pattern.** The invariants lane, hash-locked golden tests, mutation testing and the numpy reference are a "LAWS file plus objective oracle" design, the same structure MoonBit and Bend argue for. The numpy reference is Hearth's executable specification and would be the oracle for Mithril's differential checks. [inference]
3. **Run type-constrained decoding locally as a joint Hearth–Mithril capability.** Hearth controls the sampler, so it could implement Mithril-type-constrained decoding for local models. This is something hosted APIs cannot offer, and it would give Mithril a measurable "local agents write fewer ill-typed Mithril programs" result. It needs a grammar/type automaton hook in the sampling path, which is off by default to keep INV-LOSSLESS-DEFAULT. [inference]
4. **Use MAX's CPU kernels as a reference.** `vnni.mojo`, `qmatmul_k.mojo` and `per_channel_grouped_4bit.mojo` are open (Apache-2.0+LLVM exceptions) Q4/VNNI CPU kernels worth studying for Hearth's AVX-512 Q4 path. Note that "MAX usage and distribution" is under a separate community license ([README](https://github.com/modular/modular)). Read for ideas only; INV-DEP forbids importing them.
5. **Watch the competition.** `antirez/ds4` (23.8k★, created May 2026) is a "DeepSeek 4 Flash and PRO local inference engine for Metal, CUDA and ROCm" (GitHub API), and MoonBit already ships bindings and a micro coding agent on top of it ([MoonBit](https://www.moonbitlang.com/blog/local-inference-deepseek-v4-flash)). Hearth's differentiators remain CPU-only operation, NVMe-tiered experts and bit-exact determinism. Head-to-heads should include ds4 where hardware overlaps (none on Hearth's CPU-only box today). [inference]
6. **A Hearth MCP server is cheap.** It would expose the routing-trace simulator, golden-test runner and bench harness, with measured-vs-simulated tags per INV-HONEST, as tools. That is the same "toolchain as MCP" pattern used by gopls, Unison and Lean. [inference]

## Where the seed discussion is right or wrong

- **H4 (llms.txt + llms-full with EBNF, primitives and snippets): direction right, mechanism weak.** Mojo does exactly this (llms.txt, about 1 MB llms-full, sectional files), but there is no evidence that crawlers consume llms.txt ([SEJ](https://www.searchenginejournal.com/google-says-llms-txt-comparable-to-keywords-meta-tag/544804/)). The evidenced delivery path is a compressed index placed in the agent's context (AGENTS.md: 100% vs 53%), plus skills and `guide` commands ([Vercel](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals)). Keep llms.txt as a cheap extra.
- **H5 (LSP with machine-actionable JSON diagnostics and fixes): right, and already exists.** rustc JSON with `suggestion_applicability`, SARIF from GCC, Clang and MSVC, and Claude Code's LSP tool. Mithril should add semantic, hardware-aware fix-its with applicability and obligations, rather than claim the idea is new.
- **H6 (seed 50+ synthetic GitHub repos so models learn the language): weak.** MultiPL-T shows validated synthetic data helps when *you* fine-tune ([arXiv 2308.09895](https://arxiv.org/abs/2308.09895)). Fifty repos will not move frontier pretraining on a useful timescale, and Mojo still needs a skill to override stale priors ([modular/skills](https://github.com/modular/skills)). **[inference]** Spend the effort on an eval corpus and an in-context index instead. Use synthetic data only for fine-tuning local models served by Hearth.
- **H7 (Mojo "cannot do stochastic asm superoptimisation or user-space PCIe DMA"; "nothing combines all of this"): largely wrong.** Mojo exposes LLVM-dialect inline assembly, prefetch intrinsics and target-feature queries, and its compiler has been open source since Aug 18 2026 ([Modular](https://modular.com/blog/mojo-open-source), [stdlib](https://mojolang.org/llms-stdlib.txt)). Superoptimisation is a *tool*, not a language capability. User-space DMA is an OS/driver interface reachable from any language with FFI [inference]. "Nothing combines" is overstated: Bend 2 combines proofs, speed claims and AI framing, MoonBit combines SMT verification and an agent toolchain, and Lean combines proofs and programs. Mithril's real gap to fill is **hardware-cost-aware semantics plus determinism contracts plus verification, aimed at CPU inference**. I found no project combining those (search-limited; medium confidence).
- **F1 (openai/math: 700+ manuscripts, 372 families, Lean 4, Comparator): correct.** 719 manuscripts, 372 families, about 42% formalized, Comparator challenges ([repo](https://github.com/openai/math)). Comparator is a Lean FRO tool, not OpenAI's ([leanprover/comparator](https://github.com/leanprover/comparator)).
- **F2 (adopt the Lean harness to verify optimised x86 against tensor-op semantics): plausible in part.** Comparator judges whether a *Lean proof* proves a *fixed Lean statement*. It knows nothing about x86. Using it requires formal x86 and tensor semantics in Lean plus a translation of Mithril output into Lean, which is a large separate project. [inference] Comparator's role in Mithril is as the acceptance gate for agent-supplied proofs (§Implications 5).
- **F3 (Family 087 = SDP thresholds leading to zero-spill register allocation): wrong.** Family 087 is the Mahler conjectures. "Ordinary NP-hardness at the basic semidefinite threshold" is family 102 (README table; CONTENTS.md). An NP-hardness result does not yield zero-spill allocation. [inference]
- **F4 (Family 197 = Mézard–Parisi, "dual to" MoE routing): wrong number, unsupported link.** Mézard–Parisi for diluted spin glasses is family 221; family 197 is Kaplansky's direct-finiteness conjecture ([README](https://raw.githubusercontent.com/openai/math/main/README.md)). No source supports a "duality" with MoE routing or L3 partitioning. [inference]
- **F6 ("Lean harness replacing ad-hoc SMT solvers"): wrong for agents today.** SMT-backed auto-active verification is where agents succeed most (Dafny 82% vs Lean 27%) ([arXiv 2509.22908](https://arxiv.org/abs/2509.22908)), and MoonBit's 2026 design chose SMT ([0.9](https://www.moonbitlang.com/blog/moonbit-0-9-release)). Lean itself leans on automation (`grind`, `bv_decide`) ([roadmap](https://lean-lang.org/fro/roadmap/y4-1/)). Use both: SMT inside, Lean for deep or exported proofs.
- **B8 (SMT equivalence check in the compiler loop): consistent with the 2026 trend** (MoonBit `moon prove`; "AI guesses, prover checks"). Not further assessed here.
- **I4 (an SMT solver "guarantees bounded loss divergence" before hot-swap): no precedent found.** Nothing in this survey verifies properties of learned-model behavior with SMT at that scale. Treat it as research, not architecture. [inference; low-medium confidence]
- **Seed premise "AI-first language" (brief): partly right.** The evidence says *AI-first toolchain and semantics*, not AI-first syntax (Summary 1–3).

## Open questions

1. Does LSP or semantic-tool access measurably improve frontier-agent success on repository tasks, independent of vendor evals? I found only ChatLSP (2024 models) and Cursor's embeddings result. Serena's ~20-task evaluation is unquantified on its README.
2. How fast is the Lean vericoding gap closing? Do `lean-beam` (speculative `runAt`) and agent-friendly `grind` errors move Lean from 27% toward Dafny's 82%? This decides Mithril's verification tier split.
3. Can a brand-new language reach "mainstream" agent cost (about $2–$30 per chess-engine-class task) through in-context docs, skills and type-constrained decoding alone? Mithril should run the chess-study protocol on itself early.
4. Is there any measured benefit from content addressing (Unison) or from structural features such as mandatory top-level signatures (MoonBit) for agents? Both are untested.
5. Do coding agents actually fetch llms.txt at inference time, and does it beat AGENTS.md-embedded indexes? There is no controlled study beyond Vercel's single framework.
6. Which 2025–2026 "languages for AI agents" were missed because of the search limit (HN launches, small GitHub projects)? Re-run the survey with search when budget allows.
7. What are the current versions and results of Seed-Prover, Aristotle and Kimina in 2026, and what exactly did the AI-lab Lean announcements listed on lean-lang.org (Fermat's Last Theorem, Navier–Stokes) contain? The page does not link primary sources, so these are unverified.
8. Is Jai publicly available in 2026? Unverified.

## Sources

- https://arxiv.org/abs/2606.13763
- https://arxiv.org/html/2606.13763
- https://arxiv.org/abs/2308.09895
- https://arxiv.org/abs/2409.00921
- https://arxiv.org/html/2409.00921
- https://arxiv.org/abs/2504.09246
- https://arxiv.org/abs/2308.05177
- https://arxiv.org/abs/2410.02089
- https://arxiv.org/abs/2509.22908
- https://arxiv.org/abs/2507.19457
- https://arxiv.org/abs/2405.08965
- https://arxiv.org/abs/2505.13453
- https://arxiv.org/abs/2506.12202
- https://arxiv.org/abs/2510.01346
- https://arxiv.org/abs/2504.21801
- https://arxiv.org/abs/2507.23726
- https://arxiv.org/abs/2508.03613
- https://arxiv.org/abs/2504.11354
- https://arxiv.org/abs/2504.02605
- https://martin.kleppmann.com/2025/12/08/ai-formal-verification.html
- https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals
- https://aider.chat/docs/unified-diffs.html
- https://aider.chat/docs/repomap.html
- https://aider.chat/2023/10/22/repomap.html
- https://cursor.com/blog/semsearch
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/text-editor-tool
- https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md
- https://code.claude.com/docs/en/plugins-reference
- https://docs.moonbitlang.com/en/stable/language/index.html
- https://www.moonbitlang.com/about-us
- https://www.moonbitlang.com/blog/
- https://deepengineering.net/p/designing-for-ai-and-humans-with
- https://www.moonbitlang.com/blog/moonbit-0-9-release
- https://www.moonbitlang.com/blog/intro-moonbit-pilot
- https://www.moonbitlang.com/blog/seekmoon-from-ide-to-ade
- https://www.moonbitlang.com/blog/fastcc-ai-driven-development
- https://www.moonbitlang.com/blog/building-agents-moonbit
- https://www.moonbitlang.com/blog/local-inference-deepseek-v4-flash
- https://github.com/moonbit-community/verified
- https://modular.com/blog/mojo-open-source
- https://www.modular.com/blog/modular-26-5-mojo-1-0-is-here
- https://github.com/modular/modular
- https://github.com/modular/skills
- https://mojolang.org/llms.txt
- https://mojolang.org/llms-full.txt
- https://mojolang.org/llms-stdlib.txt
- https://github.com/HigherOrderCO/Bend
- https://github.com/jaseci-labs/jac
- https://github.com/BoundaryML/baml
- https://boundaryml.com/blog/sota-function-calling
- https://github.com/aitomatic/dana
- https://www.arcweb.com/node/160981
- https://github.com/eth-sri/lmql
- https://github.com/stanfordnlp/dspy
- https://newreleases.io/project/github/stanfordnlp/dspy/release/3.3.0
- https://deepmind.google/discover/blog/ai-solves-imo-problems-at-silver-medal-level/
- https://github.com/openai/math
- https://raw.githubusercontent.com/openai/math/main/README.md
- https://github.com/openai/math/blob/main/lean/ComparatorChallenges/README.md
- https://github.com/leanprover/comparator
- https://github.com/leanprover/lean-beam
- https://lean-lang.org/
- https://lean-lang.org/fro/roadmap/y4-1/
- https://www.unison-lang.org/blog/
- https://www.unison-lang.org/unison-1-0/
- https://www.unison-lang.org/blog/ucm0545/
- https://hazel.org/
- https://www.roc-lang.org/
- https://github.com/roc-lang/roc
- https://raw.githubusercontent.com/roc-lang/roc/main/AGENTS.md
- https://gleam.run/news/
- https://vale.dev/
- https://hylo-lang.org/
- https://austral-lang.org/
- https://koka-lang.github.io/koka/doc/index.html
- https://github.com/carbon-language/carbon-lang
- https://raw.githubusercontent.com/carbon-language/carbon-lang/trunk/docs/project/roadmap.md
- https://ziglang.org/news/
- https://ziglang.org/code-of-conduct/
- https://ziglang.org/news/migrating-from-github-to-codeberg/
- https://en.wikipedia.org/wiki/Jai_(programming_language)
- https://futhark-lang.org/
- https://github.com/google-research/dex-lang
- https://go.dev/gopls/features/mcp
- https://github.com/oraios/serena
- https://github.com/ast-grep/ast-grep-mcp
- https://opencode.ai/docs/lsp/
- https://modelcontextprotocol.io/
- https://llmstxt.org/
- https://www.searchenginejournal.com/google-says-llms-txt-comparable-to-keywords-meta-tag/544804/
- https://agents.md/
- https://doc.rust-lang.org/rustc/json.html
- https://gcc.gnu.org/onlinedocs/gcc/Diagnostic-Message-Formatting-Options.html
- https://clang.llvm.org/docs/UsersManual.html
- https://learn.microsoft.com/en-us/cpp/build/reference/sarif-output
- https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/sarif-support-for-code-scanning
- https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html
- GitHub REST API repository metadata (stars, pushed_at, archived), queried 2026-10-11, for: eth-sri/lmql, stanfordnlp/dspy, BoundaryML/baml, aitomatic/dana, moonbitlang/{moon,core,moonbit-compiler}, modular/modular, unisonweb/unison, hazelgrove/hazel, roc-lang/roc (+ /languages), gleam-lang/gleam, ValeLang/Vale, hylo-lang/hylo, austral/austral, koka-lang/koka, carbon-language/carbon-lang, bendlang/bend, HigherOrderCO/HVM3, diku-dk/futhark, google-research/dex-lang, oraios/serena, ast-grep/ast-grep, ast-grep/ast-grep-mcp, tree-sitter/tree-sitter, isaacphi/mcp-language-server, upstash/context7, leanprover/{lean4,comparator,lean-beam}, oOo0oOo/lean-lsp-mcp, jaseci-labs/jac, sourcegraph/zoekt, microsoft/multilspy, AnswerDotAI/llms-txt, antirez/ds4 — e.g. https://api.github.com/repos/antirez/ds4
