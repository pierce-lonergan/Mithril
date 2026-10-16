# G01 — Can frontier agents write a brand-new language from in-context docs? Standalone .mith vs a hosted/embedded surface

> **Method note.** The shared WebSearch budget for this run was already used up when this task started. Every source below was therefore reached by **fetching primary URLs directly**: arXiv abstract and HTML pages, project READMEs, vendor blogs, and one PDF read locally. These were papers and pages I already knew of, or that sibling dossiers R03 and R04 cite. I ran no open-ended search. "Not found" in this file means "not found without search", not "does not exist". In particular, 2026 successors to the version-drift benchmarks and any 2026 "esoteric language" benchmark may exist and be missing here. Numbers are copied from the fetched pages. Derived ratios are marked **[inference]**.

---

## Summary

- **No controlled study exists (that I could reach) of frontier models writing an *invented general-purpose* language from its manual alone.** R03 and R04 flagged the same gap. The closest direct evidence comes from five places: a counterfactual Python dialect (ThonPy), an unfamiliar verification language (UCLID5), Python-embedded HDLs, Mojo, and one 2026 case where an agent built a chess engine in a language it designed itself. **(high that the gap exists; medium that nothing newer exists)**
- **Brand-new languages are writable, but at a steep cost multiple, and the gap persists in 2026.** In the June 2026 chess-engine study, Claude Code (Opus 4.6/4.7) and Codex (GPT-5.x) produced a working engine in every language they tried. Mainstream engines cost a median of about $40 and took a handful of prompts. Esoteric and legacy engines cost about $60–$480 and took 25–50 prompts. An **agent-designed DSL ("GAMBIT") plus its C++ transpiler** cost $160.89 over 21 prompts and reached 1622 ±68 Elo, about Python's level ([Acher & Jézéquel](https://arxiv.org/html/2606.13763)). **(high)**
- **The worst case is familiar syntax with changed meaning ("false friends"), not unfamiliar syntax.**
  - Changing one rule, stated in the prompt (1-based indexing), cut GPT-4 HumanEval pass@1 on index-sensitive problems from 82.5% to 40.5% ([Wu et al.](https://arxiv.org/html/2307.02477v3)).
  - In Rust, API changes that keep the signature but change behaviour scored 38.0%, against 65.8% for newly stabilised APIs ([RustEvo²](https://arxiv.org/abs/2503.16922)).
  - Mojo, which looks like Python, ships a correction skill of roughly 450–500 lines whose job is to override "obsolete syntax" from pretraining ([modular/skills](https://raw.githubusercontent.com/modular/skills/main/mojo-syntax/SKILL.md)). **(high)**
- **Unfamiliar standalone syntax with only few-shot examples was near-hopeless for 2024 models.** In 660 attempts, no model produced UCLID5 that parsed without special prompting. Three-shot GPT-4-turbo parsed 4 of 33. A Python-subset "child language" with a repair-and-lift step parsed 28 of 33 ([SPEAC HTML](https://arxiv.org/html/2406.03636v4)). **(high for 2024 models; newer models unmeasured)**
- **Embedding a DSL in Python buys tooling, not writability.**
  - GPT-4 Turbo scored **72.2% on Verilog but only 29.8–62.0% on five Python-embedded HDLs**, even though Python is far more common in training data. Zero-shot PyMTL3 scored ≤2–13% ([PyHDL-Eval](https://www.csl.cornell.edu/~cbatten/pdfs/batten-pyhdl-eval-mlcad2024.pdf)).
  - Python-embedded Triton was also hard: zero-shot execution accuracy was about 10–13% on real-world operators ([TritonBench](https://arxiv.org/html/2502.14752)).
  - Rust-embedded Verus (44%) trails standalone Dafny (82%) ([vericoding](https://arxiv.org/abs/2509.22908)).
  - What predicts success is whether the *semantics and concepts* match something the model already knows. **(high)**
- **Low-resource is not the same as unseen.** On AutoCodeBench, Claude Opus 4 scored 80.3% on Elixir, 68.9% on Racket and 40.3% on Python ([AutoCodeBench](https://arxiv.org/html/2508.09101v1)). Off-the-shelf models' pure-Dafny verification rate rose from 68% to 96% in a year ([vericoding](https://arxiv.org/abs/2509.22908)). Languages with *some* training data are closing the gap. Languages with *none* still are not (Mojo, UCLID5, the exotic chess engines). **(medium-high)**
- **Docs in context work when they carry knowledge the model lacks, and only if they are compact and always present.**
  - Vercel: an 8 KB docs index in AGENTS.md scored 100%, against 53% with no docs and 53% with an on-demand skill ([Vercel](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals)).
  - SkillsBench: curated skills added +16.6 pp on average, but "comprehensive" documentation added only +0.7 pp, and self-generated skills *hurt* by 8–12 pp ([SkillsBench](https://arxiv.org/html/2602.12670)).
  - Evaluating AGENTS.md: context files in *familiar* repos did not raise success and raised cost by about 20% ([Gloaguen et al.](https://arxiv.org/html/2602.11988)). **(high)**
- **Recommendation [inference] (medium-high): make Mithril a standalone `.mith` language with a conservative Rust-shaped surface.** Every construct that looks like Rust (or C) must mean the same thing. New concepts get new, keyword-led constructs. Do **not** use a Python near-clone (the Mojo lesson) or a Python-embedded DSL as the primary surface (the PyHDL and Triton lessons). Allow a Python-embedded API only for *schedule and search scripts*, the role where LLMLift and SPEAC show Python works as an intermediate language.
- **Reference card [inference]: plan for a tiered card.**
  - Tier 0: always in context, ≤8 KB (about 2k tokens).
  - Tier 1: a skill or `mithc guide` reference of about 5–15k tokens.
  - Tier 2: the full manual, retrieved on demand.
  - The real-world comparisons are Mojo's correction skill (about 3.5–4k words) and MoonBit's agent guide (about 9k words).
  - Keep the language small enough that Tier 1 covers every construct. The grammar must be a Lark file that fits OpenAI's CFG restrictions. Claude cannot enforce a grammar at decode time, which is another reason to keep the syntax familiar.

---

## Findings

### F1. Direct evidence on writing a language the model has never seen

**F1.1 No controlled study of an invented general-purpose language.** I found no 2025–2026 study that gives a frontier model only the manual of a newly invented general-purpose programming language and measures pass rates. R03 ("I found no controlled 2025–2026 study…") and R04 reached the same conclusion. A search-enabled pass should look for "esoteric language" and "new DSL" benchmarks, which I could not search for. **(medium)**

**F1.2 The closest proxies.**

| Evidence | What the model had in context | Result | Source |
|---|---|---|---|
| **ThonPy** (2023): Python with 1-based indexing, rule stated in the prompt with asserts | Full rule description plus examples | GPT-4 HumanEval pass@1 87.4 → 68.2 (all 164); **82.5 → 40.5** on the 53 index-sensitive problems; code execution 58.4 → 18.6 | [Wu et al. HTML, App. C](https://arxiv.org/html/2307.02477v3) |
| **UCLID5** (verification language), 2024 models | 1–3 shot examples, CoT, self-repair, fine-tuning | 0/660 parse "without special prompting"; 3-shot GPT-4-turbo 4/33; fine-tuned GPT-3.5 2/33; Python-subset child language plus MAX-SMT repair **28/33** | [SPEAC HTML](https://arxiv.org/html/2406.03636v4) |
| **PyMTL3** (Python-embedded HDL), 0 vs 3 ICL examples | Spec plus 0–3 worked examples | GPT-4 13.2% → 47.0%; GPT-4 Turbo 2.0% → 43.6%; zero-shot failures were "basic mistakes": importing a non-existent library, deprecated syntax | [PyHDL-Eval PDF, Table 2](https://www.csl.cornell.edu/~cbatten/pdfs/batten-pyhdl-eval-mlcad2024.pdf) |
| **Mojo** (2024 models), HumanEval-Mojo | Task prompt only | GPT-4o 25.5%, Claude-3.5-Sonnet 39.8%; models "get the algorithm right… but the syntax wrong" and sometimes emit Python | [MojoBench HTML](https://arxiv.org/html/2410.17736) |
| **Hazel** (typed functional, niche) | With and without type context | Without context GPT-4 "often produces syntactically incorrect code"; type definitions were the most useful context (summarised in R03) | [typed holes](https://arxiv.org/html/2409.00921v1) |
| **Kalamang** (natural language, <200 speakers) | Whole grammar book ("several hundred pages") | 2023 baselines 44.7/45.8 chrF vs human 51.6/57.0; Gemini 1.5 later reached human-learner level with the full book in context | [MTOB](https://arxiv.org/abs/2309.16575), [Gemini 1.5](https://arxiv.org/abs/2403.05530) |
| **GAMBIT** (agent-designed chess DSL, 2026) | The agent's own design | Codex designed the DSL and a C++ transpiler, then wrote the engine: 21 prompts, 4,658 LOC, $160.89 canonical ($113.04 list), **1622 ±68 Elo** (self-claim 2170) | [Acher & Jézéquel](https://arxiv.org/html/2606.13763) |

**F1.3 What the proxies agree on [inference].**
1. For 2023–2024 models, an unfamiliar surface with few examples failed at the *syntax* level (UCLID5, PyMTL3 zero-shot, Mojo, Hazel).
2. A handful of in-context examples fixes much of the syntax problem (PyMTL3 2% → 44%) but not semantic transfer (PyMTL3 still trails Verilog by about 29 points).
3. A rule change stated explicitly in context is *not* reliably obeyed when it contradicts a strong prior (ThonPy).
4. 2026 frontier agents in a long agentic loop with an oracle get *something* working in any language, but pay heavily in prompts and dollars (chess study, F3.3).

**F1.4 The GAMBIT result, and its limits.** It is the only 2026 data point I found of an agent writing a non-trivial program in a language that did not exist before the session. It shows that a language *designed by the agent* is writable at roughly **4× the mainstream median cost** (about $161 vs about $40) **[inference from the paper's numbers]**. The resulting engine played at Python level (1622 vs Python's 1616/1499) ([paper](https://arxiv.org/html/2606.13763)).
- Caveats:
  - n = 1.
  - The fetched text does not describe GAMBIT's syntax or how much of it borrowed from C++ or Python.
  - Playing strength comes from the transpiled C++.
  - The designer and the writer were the same model, so the language presumably sat close to that model's priors **[inference]**.
- **(medium)** The obvious next experiment for Mithril is to have agent A design and agent B write, or to have a *different* model family write. Nobody has published that.

### F2. False friends: familiar syntax with changed meaning, and API/version drift

**F2.1 Behavioural changes behind an unchanged signature are the hardest case.** RustEvo² (Mar 2025) turned 588 real Rust API changes (380 std, 208 from 15 crates) into tasks ([abs](https://arxiv.org/abs/2503.16922)).
- Average success: stabilisations **65.8%**, behavioural changes **38.0%**. The authors attribute the gap to difficulty detecting semantic shifts when signatures stay the same.
- APIs before the knowledge cutoff: 56.1%. After: 32.5%.
- RAG improved post-cutoff success by 13.5% on average.
- **(high)** This is the cleanest quantitative evidence that *same surface, different meaning* is the costliest category.

**F2.2 The ThonPy result restated for language design [inference].** One semantic change, explicitly stated with examples, halved GPT-4's accuracy on affected problems ([Wu et al.](https://arxiv.org/html/2307.02477v3)). A "Python-like but…" or "Rust-like but…" language inherits this tax for every *but*. The data are from 2023 models. I found no replication on 2025–2026 frontier models (open question).

**F2.3 The version-drift benchmarks (2024–2025) all find the problem real and only partly fixed by docs.**
- *CodeUpdateArena* (54 functions, 7 Python packages, 670 synthesis examples): prepending documentation of the update "does not allow" the tested open code models (DeepSeek, CodeLlama) to use the change ([abs](https://arxiv.org/abs/2407.06249)). This is a 2024, small-model result. It is the strongest negative evidence on docs-in-context, but likely does not transfer to frontier models **[inference]**.
- *VersiCode* (2024): version-controllable generation is "a significant challenge, even for GPT-4o" ([abs](https://arxiv.org/abs/2406.07411)).
- *LibEvolutionEval* (NAACL 2025; 8 Python libraries): library evolution "significantly influences" performance. Version-specific doc retrieval helps; the abstract gives no number ([abs](https://arxiv.org/abs/2412.04478)).
- *CODESYNC* (ICML 2025; 220 APIs, 6 libraries, 14 LLMs): models "struggle with dynamic code evolution" even after DPO, ORPO or SimPO updating ([abs](https://arxiv.org/abs/2502.16645)).
- *GitChameleon 2.0* (Jul 2025; 328 version-pinned Python problems; [HTML](https://arxiv.org/html/2507.12367v2)):
  - Enterprise models had baselines of 48–51%.
  - RAG over docs added +3 to +17 points (GPT-4.1 48.5 → 58.5; Claude 3.7 Sonnet 48.8 → 56.1; Gemini 2.5 Pro 50.0 → 56.7; Claude 4 Sonnet 59.4 with RAG).
  - Self-debugging against visible tests added about 10–20 points on hidden tests.
  - Claude Code (3.7 Sonnet) went 32.0 → 48.8 when given the problem statement.
  - Even the best configuration left over 40% unsolved.
  - **(high)**

**F2.4 Young languages pay this tax continuously.**
- *Zig 0.15.1* came from 647 commits by 162 contributors over five months. The release notes call the `std.io` "Writergate" overhaul "extremely breaking". They also remove `usingnamespace` and `async`/`await`, make the unmanaged `ArrayList` the default, and change format-method conventions ([release notes](https://ziglang.org/download/0.15.1/release-notes.html)). I found no measurement of LLM error rates on post-0.15 Zig. That LLMs write stale Zig is **unverified**; that each release creates RustEvo²-style stale priors is **[inference]**.
- *Mojo* reached 1.0 on Aug 11, 2026 and promises 1.x changes that are "primarily additive" ([Modular](https://www.modular.com/blog/modular-26-5-mojo-1-0-is-here), [changelog index](https://mojolang.org/docs/changelog)).
  - Its official `mojo-syntax` skill says "Pretrained models generate obsolete syntax". It lists replacements such as `fn` → `def` (now a hard parse error), `alias` → `comptime`, `let` → `var`, `inout`/`owned` → `mut`/`var`, `@value` → `@fieldwise_init`, and `from collections` → `from std.collections`.
  - It also lists **Python false friends**: `lst[-1]` must be written `lst[len(lst) - 1]`, and `s[i]` becomes `s[byte=i]` ([SKILL.md](https://raw.githubusercontent.com/modular/skills/main/mojo-syntax/SKILL.md)). The fetch tool estimated the file at about 450–500 lines and 3,500–4,000 words (approximate).
  - Mojo has years of public code and still needs this correction layer. **(high)**
- *MoonBit* has a Rust-like surface. Its official agent guide (about 1,300 lines and 9,000 words, approximate) lists habits imported from Rust, Swift and JS: `fn main() {}` vs `fn main {}`, `++`/`--`, unnecessary `return`, legacy `f!()`/`f()?`, `await`, `for {}`, and `derive(Show)` vs `Debug`. It also tells the agent to lean on `moon check`, `moon ide` and `moon explain` throughout ([moonbit-agent-guide SKILL.md](https://raw.githubusercontent.com/moonbitlang/moonbit-agent-guide/main/moonbit-agent-guide/SKILL.md), [repo](https://github.com/moonbitlang/moonbit-agent-guide)). **(high)**

**F2.5 Lesson [inference] (high).** Each place a new language *resembles* a popular one but differs in meaning becomes a permanent line in a correction card and a recurring source of agent errors. The cost does not fade, because the parent language keeps dominating training data. Mojo and MoonBit, the two most "AI-aware" young languages, both document this explicitly.

### F3. Young and low-resource languages: per-language results and the trend

**F3.1 Agentic multi-language benchmarks cover only mainstream languages.**
- Multi-SWE-bench covers Java, TS, JS, Go, Rust, C and C++ (1,632 instances; NeurIPS 2025 D&B), with flash and mini subsets ([repo](https://github.com/multi-swe-bench/multi-swe-bench)).
- SWE-PolyBench covers Python, Java, JS and TS (2,110 instances) ([abs](https://arxiv.org/abs/2504.08703)).
- SWE-bench Multilingual covers 9 mainstream languages ([page](https://www.swebench.com/multilingual.html)).
- **None** includes MoonBit, Gleam, Mojo, Zig, Roc or Jac. **(high)**

**F3.2 Where per-language numbers exist, "low-resource" no longer means "low score".**
- *AutoCodeBench* (Aug 2025; 3,920 problems across 20 languages; [HTML, Table 4](https://arxiv.org/html/2508.09101v1)). Claude Opus 4 (reasoning) pass@1 by language:

  | Language | Pass@1 |
  |---|---|
  | Elixir | 80.3 |
  | C# | 74.9 |
  | Kotlin | 72.5 |
  | Racket | 68.9 |
  | Ruby | 61.0 |
  | Java | 55.9 |
  | Shell | 51.6 |
  | Python | 40.3 |
  | Rust | 38.7 |
  | PHP | 28.1 |

  - The authors say the gap between models widens on low-resource languages, where Claude Opus 4 leads.
  - They also hypothesise that their filtering model (DeepSeek-Coder-V2-Lite) removes easy problems less effectively in low-resource languages. That would flatter those languages, so do not read Elixir > Python literally.
- *SWE-bench Multilingual*: Claude 3.7 Sonnet with SWE-agent resolved 42.67% overall, against about 63% on Verified. Rust scored highest (58.1%) and C/C++ lowest (28.6%) ([page](https://www.swebench.com/multilingual.html)).
- Anthropic says only that Opus 4.5 leads "7 out of 8" Multilingual languages, with figures in images ([announcement](https://www.anthropic.com/news/claude-opus-4-5)). I could not extract newer per-language numbers.
- *Aider polyglot* (225 Exercism exercises in C++, Go, Java, JS, Python, Rust) is near saturation: GPT-5 (high) 88.0%, o3-pro 84.9% ([leaderboard](https://aider.chat/docs/leaderboards/)).

**F3.3 The 2026 chess study is the best cost-curve evidence for exotic languages.**
- Agents: Claude Code with Opus 4.6/4.7; Codex with gpt-5-codex, gpt-5.3-codex and gpt-5.4 ([HTML](https://arxiv.org/html/2606.13763)).
- External Elo:

  | Language | External Elo |
  |---|---|
  | Java | 2096 ±132 |
  | Rust | 1989 ±105 |
  | Ruby | 1753 |
  | C++ | 1709 |
  | Python | 1616 / 1499 |
  | C | 1440 / 1402 |
  | x86-64 assembly | 1403 |
  | COBOL | 1365 / 1274 |
  | Brainfuck | 1299 |
  | Lean 4 | 1271 |
  | Icon | 1168 |
  | APL | 686 |
  | SQL | 523 |

- Normalised costs: COBOL $473.50 (24 prompts), Brainfuck $234.60 (30), Lean 4 $175.17 (21), APL $155.52 (26), Python $40.45 (10).
- **Mojo** is listed among mainstream languages, yet its session was "underconverged": about 900 in-session Elo after 7 prompts and $33.65, stopped when the budget ran out.
- The authors list "model mastery of the language" as a confounder they cannot separate from language effects. They suggest the rare-language engines may be something "the previous generation of LLMs could not" build.
- Self-reported Elo was 200–1100 points too high. Agents systematically overrate their own work in unfamiliar settings.
- **(high on numbers; causal attribution to training data is the authors' caveat, not a finding)**

**F3.4 The trend: the gap is closing where data exists.**
- *Vericoding*: off-the-shelf success is Dafny 82%, Verus 44%, Lean 27%. Pure-Dafny verification "rose from 68% to 96%" over the past year ([abs](https://arxiv.org/abs/2509.22908)).
- *MojoBench* (Oct 2024): a model pre-trained and fine-tuned on about 6.58 M filtered Mojo tokens plus 3,200 SFT pairs beat GPT-4o and Claude-3.5-Sonnet by a claimed 30–35% (metric unspecified in the abstract) ([abs](https://arxiv.org/abs/2410.17736), [HTML](https://arxiv.org/html/2410.17736)). A few million tokens of validated data move a small model a long way, which matters for Hearth-hosted local models **[inference]**.
- **[inference] (medium):** Frontier models are closing gaps for languages with *moderate* public data (Elixir, Racket, Dafny, Rust). For languages with *none*, the chess study (exotic languages at 4–12× the mainstream median cost), the Mojo session and the UCLID5 and PyMTL3 zero-shot failures say the prior still dominates. Mithril starts with none.

**F3.5 The pull toward Python is measurable.** In project-initialisation tasks where Python is not the best choice, models still picked Python 58% of the time and never picked Rust. They used NumPy unnecessarily in up to 45% of cases (Twist et al., Findings of ACL 2026; [abs](https://arxiv.org/abs/2503.17181)). Language confusion, meaning output in an unrequested language with defaulting to Python, is documented in R03 ([Moumoula et al.](https://arxiv.org/abs/2503.13620)). **(high)** [inference] A Python-*looking* Mithril would sit closest to this pull and leak Python semantics and libraries most.

**F3.6 No writability data for MoonBit, Gleam, Roc, Jac or Zig.**
- MoonBit's blog (31 posts, Jan 2025–Oct 2026) has AI-themed posts but no writability measurement ([index](https://www.moonbitlang.com/blog/)). Its 2024 "AI-friendly" post claims a "significant improvement" in compile rate at about 3% performance cost, with figures only in an image ([post](https://www.moonbitlang.com/blog/moonbit-ai)).
- MoonBit's Fastcc post reports an unnamed agent writing about 35k lines of MoonBit (a self-hosting ARM64 C compiler) in about 10 days. It does not say how the agent was taught the language ([post](https://www.moonbitlang.com/blog/fastcc-ai-driven-development)). Vendor claim, low confidence, but it suggests a young language with a strong toolchain is writable at scale.
- Roc's AGENTS.md governs compiler work and says nothing about the language being unfamiliar to models ([AGENTS.md](https://raw.githubusercontent.com/roc-lang/roc/main/AGENTS.md)).
- MultiPL-E's README names only a few added languages (Ada, Dart, Clojure, Elixir) and none of the young ones ([repo](https://github.com/nuprl/MultiPL-E)). **(medium; search-limited)**

### F4. Embedded/hosted DSLs vs standalone syntax

**F4.1 PyHDL-Eval is the only controlled embedded-vs-standalone comparison I found.** It was published at MLCAD 2024 (Batten, Pinckney, Liu, Ren, Khailany): 168 spec-to-RTL problems, with Verilog compared to five Python-embedded DSLs ([PDF](https://www.csl.cornell.edu/~cbatten/pdfs/batten-pyhdl-eval-mlcad2024.pdf), [repo](https://github.com/cornell-brg/pyhdl-eval)).
- Pass rates with three ICL examples:

  | Model | Verilog | PyMTL3 | PyRTL | MyHDL | Migen | Amaranth |
  |---|---|---|---|---|---|---|
  | GPT-4 Turbo | **72.2** | 43.6 | 29.8 | 62.0 | 47.3 | 56.0 |
  | GPT-4 | 69.9 | 47.0 | 22.9 | 61.0 | 46.0 | 49.4 |
  | Llama3 70B | 63.2 | 33.0 | 24.4 | 53.8 | 40.2 | 45.2 |

- The authors say this "challenge[s] conventional wisdom": the DSLs gain from the popular host, but "loose" that gain through domain-specific library syntax and semantics.
- **MyHDL**, whose explicit clock and reset match the *Verilog* mental model, came closest to Verilog.
- In the other DSLs, models "frequently declare explicit clock and reset signals" even when the ICL examples showed they were implicit. That is a semantic false friend imported from the dominant domain language.
- **(high for 2024 models)**

**F4.2 Python-embedded GPU DSLs are also hard for LLMs.**
- TritonBench (Feb 2025), zero-shot / one-shot on real-world operators ([HTML](https://arxiv.org/html/2502.14752)):

  | Model | Execution accuracy (zero-shot / one-shot) |
  |---|---|
  | Claude-3.5-Sonnet | 9.79 / 19.57 |
  | DeepSeek-R1 | 13.05 / 22.83 |
  | o1 (best) | 23.91 (one-shot) |

- On PyTorch-aligned operators the best score was DeepSeek-R1 at 53.01 zero-shot.
- The authors found only 95 repositories with more than 100 stars, and 250 files, containing Triton. One-shot examples added about 10 points.
- Meta's KernelAgent generates Triton but publishes no correctness numbers ([repo](https://github.com/meta-pytorch/KernelAgent)). KernelBench now accepts `cuda`, `triton`, `cute`, `tilelang`, `thunderkittens` and `hip` backends but publishes no per-DSL LLM comparison ([repo](https://github.com/ScalingIntelligence/KernelBench)).
- MultiKernelBench (CUDA vs Huawei NPU vs TPU; 285 tasks, 7 LLMs) would be the direct comparison, but its full text could not be fetched. Per-platform numbers are **unverified** ([abs](https://arxiv.org/abs/2507.17773)).
- Helion's case is human familiarity: "Familiarity with PyTorch means you already know most of Helion"; attention in 30 lines vs 120 in Triton. It reports no LLM-writability data ([blog](https://pytorch.org/blog/helion/)).
- I found no LLM-writability data for Exo, cuTile or Pallas. **(medium)**

**F4.3 Hosting in a familiar language does not guarantee writability.**
- *Verus* is Rust-embedded. AutoVerus notes it "does not require LLM to learn a new language" (R03, [AutoVerus](https://arxiv.org/html/2409.13082v2)). Yet it scores 44%, against standalone Dafny's 82%, on vericoding ([abs](https://arxiv.org/abs/2509.22908)). AlgoVeri, on identical contracts, gives Dafny 40.3% and Verus 24.7% (R03, [AlgoVeri](https://arxiv.org/abs/2602.09464)).
- **[inference]** The proof burden and Rust's ownership semantics dominate the familiar host syntax.

**F4.4 What *does* work: generate the model's native language, then lift.**
- SPEAC/Eudoxus chose Python because "no LLM produced UCLID5 code that parsed" in 660 tries. It defines the child language as an abstract class the LLM must extend (`types`, `inputs`, `init`, `next`), repairs it with MAX-SMT, and compiles it to UCLID5: 28/33 parse vs 4/33 ([HTML](https://arxiv.org/html/2406.03636v4)).
- LLMLift writes DSL semantics as Python functions because LLMs "struggle to generate SMT-LIB" (R03, [LLMLift](https://arxiv.org/html/2406.03003)).
- **[inference] (high)** This is the opposite of a DSL that merely *borrows Python syntax*. The model writes *ordinary Python with ordinary meaning* against a small API, and a tool does the lifting. Embedding pays off when host semantics are preserved. It fails when the host syntax wraps alien semantics: staged hardware signals, Triton pointer and mask arithmetic, or Mojo's not-quite-Python indexing.

**F4.5 Synthesis on surface choice [inference].**

| Option | Main benefit | Evidence of risk | Fit to Mithril |
|---|---|---|---|
| Novel standalone syntax | Full design freedom; grammar can be tiny | UCLID5 0/660; Mojo 2024 25–40%; exotic chess engines 4–12× cost; Claude cannot enforce a grammar at decode time | Poor |
| Python near-clone or "superset" | Huge prior | ThonPy halving; Mojo false-friend card; Python-pull 58%; Python semantics (dynamic types, GC, bignum ints, negative indexing) clash with Hearth's determinism and fixed-width needs | Poor |
| Python-embedded DSL | Free parser, LSP and tooling | PyHDL 72 → 30–62; Triton 10–24%; staging confusion between host and device code | Good only for schedule and search scripts |
| Rust-embedded (proc macro) | Free toolchain, ownership | Verus 44% vs Dafny 82%; macro diagnostics are poor (unverified) | Medium |
| **Rust-shaped standalone, false-friend-free** | Familiar tokens and keywords; Rust scored highest on SWE-bench Multilingual for Claude 3.7; own grammar, diagnostics and semantics | MoonBit shows near-Rust syntax still needs a large pitfalls list; every deviation costs | **Best** |

### F5. Docs in context: size, delivery and when they help

**F5.1 Docs help in proportion to the knowledge gap.**
- *Vercel* (Jan 2026) tested Next.js 16 APIs absent from training data ([post](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals)):

  | Configuration | Pass rate |
  |---|---|
  | No docs | 53% |
  | On-demand skill | 53% (never invoked in 56% of runs) |
  | Skill plus explicit "use the skill" instruction | 79% |
  | Compressed docs index in AGENTS.md | **100%** |

  - The index shrank from about 40 KB to 8 KB with no loss.
  - Caveats: single vendor, undisclosed model and task count, an eval built alongside the method.
- *Evaluating AGENTS.md* (ETH/LogicStar; v3 Sep 2026; [HTML](https://arxiv.org/html/2602.11988)), on familiar repos:

  | Context file | SWE-bench Lite | CTXbench |
  |---|---|---|
  | LLM-generated | −0.5 pts (n.s.) | −2 pts (n.s.) |
  | Developer-written | — | +2.4 pts (p = 0.21) |

  - Cost rose about 20–23%.
  - Repository overviews did not help. Tool-usage instructions were followed.
- **[inference] (high):** When the model already knows the material, context is overhead. When it does not (new APIs, a new language), compact always-present context is the single largest lever measured.

**F5.2 Compact beats comprehensive, and curated beats self-written.** SkillsBench (v4 Jun 2026; 87 tasks, 18 model-harness configurations; [HTML](https://arxiv.org/html/2602.12670)):
- Curated skills raised the mean from 33.9% to 50.5%.
- By documentation style: compact +19.0 pp, standard +21.5, detailed +14.5, **comprehensive +0.7**.
- By number of skills: one +18.0, two or three +19.0, four or more +10.1.
- The median SKILL.md is 4.8 KB (about 1.2k tokens).
- Self-generated skills scored *below* no skills: Claude Code + Opus 4.7 −8.1 pp; Codex + GPT-5.5 −11.3; Gemini CLI + 3.1 Pro −11.5.
- Software engineering gained +11.6 (37.6 → 49.2). Claude Code + Opus 4.7 went 43.0 → 61.2.
- **(high)**

**F5.3 Long context degrades.**
- Chroma's Context Rot study (Jul 2025; 18 models including Claude Opus 4 and Sonnet 4) found reliability falls with input length even on simple tasks. All models did better on about 300-token focused inputs than on about 113k-token full inputs ([report](https://www.trychroma.com/research/context-rot)).
- NoLiMa: at 32K tokens, 11 of 13 models fell below 50% of their short-context baseline once literal matches were removed. GPT-4o went from 99.3% to 69.7% ([abs](https://arxiv.org/abs/2502.05167)).
- Anthropic's guidance (Sep 2025) is "the smallest set of high-signal tokens", in a hybrid of upfront CLAUDE.md plus just-in-time retrieval ([post](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)).
- Counterpoint: many-shot ICL with hundreds or thousands of examples can "override pretraining biases", at linear cost ([abs](https://arxiv.org/abs/2404.11018)). Whole-book ICL taught Gemini 1.5 Kalamang ([Gemini 1.5](https://arxiv.org/abs/2403.05530)).
- **[inference]** Large references work for one-shot tasks. For multi-turn agent loops, per-turn cost and context rot favour a compact core plus retrieval, with prompt caching.

**F5.4 Examples are the cheapest unit.**
- PyHDL-Eval: 0 → 1 example took PyMTL3 from about 0–13% to 16–33%. The second example mattered for larger models, and the third added little ([PDF](https://www.csl.cornell.edu/~cbatten/pdfs/batten-pyhdl-eval-mlcad2024.pdf)).
- TritonBench: one-shot added about 10 points ([HTML](https://arxiv.org/html/2502.14752)).
- Retrieval: RustEvo² +13.5% ([abs](https://arxiv.org/abs/2503.16922)); GitChameleon 2.0 +3 to +17 ([HTML](https://arxiv.org/html/2507.12367v2)).
- Feedback: self-debugging +10–20 ([HTML](https://arxiv.org/html/2507.12367v2)); Hazel error rounds about 2× where familiarity was lowest (R03).
- **(high)**

**F5.5 Real-world card sizes for young languages** (approximate; length estimates from the fetch tool):

| Card | Approx. size | Source |
|---|---|---|
| Mojo `mojo-syntax` correction skill | 450–500 lines, 3.5–4k words | [link](https://raw.githubusercontent.com/modular/skills/main/mojo-syntax/SKILL.md) |
| MoonBit agent guide | ~1,300 lines, ~9k words | [link](https://raw.githubusercontent.com/moonbitlang/moonbit-agent-guide/main/moonbit-agent-guide/SKILL.md) |
| Mojo `llms.txt` index (v1.1.0) | Splits into manual, reference, stdlib, CLI files | [link](https://mojolang.org/llms.txt) |
| Vercel winning index | 8 KB | [link](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals) |
| SkillsBench median SKILL.md | 4.8 KB | [link](https://arxiv.org/html/2602.12670) |

[inference] Tension: a young language's *full* agent guide (MoonBit) is roughly 5–10× larger than the evidence-optimal skill size (SkillsBench) or always-on index (Vercel). The resolution is tiering, not one file.

### F6. Constrained decoding and grammar size (brief; R03 has the detail)

- Grammar masks cost tens of microseconds per token in llguidance and XGrammar ([llguidance](https://github.com/guidance-ai/llguidance), [XGrammar](https://arxiv.org/abs/2411.15100)). Type-constrained decoding more than halved TypeScript compile errors ([Mündler et al.](https://arxiv.org/abs/2504.09246)).
- OpenAI GPT-5 custom tools accept Lark CFGs with restrictions ([cookbook](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_new_params_and_tools)). Per R03's reading of the docs, Claude structured outputs accept JSON Schema only, with no recursion ([docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)).
- **[inference] (high):** A grammar mask helps most where syntax is the failure mode, which means novel syntax (UCLID5-like). But the main frontier agent Mithril targets (Claude) cannot apply one. Syntax must therefore be *prior-compatible* for Claude. Grammar masks are a bonus for OpenAI and for Hearth-hosted local models. The type-level masks matter more: compile errors in familiar syntax are mostly type errors (R03).

---

## Implications for Mithril

1. **Surface decision [inference] (medium-high): a standalone `.mith` language with a conservative Rust-shaped surface.**
   - **Shared syntax means the shared semantics.** Use `fn`, `let`/`let mut`, `struct`, `enum`, `match`, `impl`, `u8`/`i32`/`f32`, `&`/`&mut` and `for x in a..b` with Rust meaning. Where Mithril must differ (for example aliasing, or floating-point contraction under INV-DET-3), use a **new keyword or a new type**, never a reinterpretation. The evidence is F2.1 (behavioural changes 38% vs 65.8%), F2.2 (ThonPy) and F2.4 (Mojo and MoonBit pitfall lists).
   - **New concepts are keyword-led and greppable:** `kernel`, `schedule`, `exact`, `prefetch`, `@align(64)`, `@nontemporal`. Leading keywords also give each line a language-identity signal against confusion (R03).
   - **Do not make Mithril a Python near-clone.** Python's pull is strongest (F3.5), and Mojo's experience (F2.4) shows the false-friend tax of a Python-shaped systems language. Python semantics also conflict with Hearth's invariants.
   - **Do not make a Python-embedded DSL the primary surface.** PyHDL-Eval and TritonBench (F4.1–F4.2) show that the host's familiarity does not transfer to the DSL's semantics.
   - **Do provide a Python-embedded *schedule and search* API** (Exo-style, per R05) for the optimisation layer. There, agents write ordinary Python control flow over a small cursor/rewrite API, which matches the SPEAC and LLMLift pattern (F4.4). The schedule's output is checked `.mith` or IR, never trusted Python.
   - **Provide a parent-language lifter as the cold-start escape hatch:** from a C subset and a Rust subset into `.mith`, with differential tests. Hearth's C11 kernels are the first customer (see Hearth below).
2. **Size the reference card in tiers [inference] (medium).**
   - **Tier 0 (always in context, ≤8 KB, about 2k tokens).** Contents: a one-screen grammar summary, keyword list, false-friends table versus Rust/C/Python, about 10 canonical snippets, the determinism and FP rules, and the commands (`mithc check --json`, `mithc guide`). This is the Vercel winner's size.
   - **Tier 1 (skill or `mithc guide`, about 5–15k tokens, 2–3 modules).** Contents: the Lark grammar, stdlib signatures, 40–80 idiomatic snippets covering every construct, and the error-code index. This sits between SkillsBench's compact/standard optimum and the Mojo and MoonBit guides.
   - **Tier 2 (retrieved).** The full manual via MCP, LSP hover and `mithc explain`.
   - **Curated, not self-generated.** Self-generated skills lost 8–12 pp (F5.2). Maintainers write the card and evaluate it like code.
   - **Language size budget.** Keep Mithril small enough that Tier 1 covers *every* construct. If a construct cannot be explained with one snippet and one false-friend line, it is probably too novel.
3. **Grammar [inference] (medium).**
   - Write one normative Lark grammar that fits OpenAI's restrictions (explicit whitespace terminals, no `%ignore` reliance; R03). Keep it small enough to print inside Tier 1 (a few thousand tokens).
   - Prefer LL-friendly, keyword-first productions so prefix parsing is incremental for masks and LSP.
   - Type-level masks (Mündler-style) are worth more than syntax masks for a familiar surface, and are feasible only where Mithril owns the logits (Hearth-hosted models).
4. **Make feedback the main cold-start lever.** Self-debugging gave +10–20 points (GitChameleon 2.0). Hazel's error rounds roughly doubled results. Chess-study agents overrated their own work by 200–1100 Elo. `mithc` must return JSON diagnostics that cite the false-friend rule violated, for example "MITH-E0107: `a*b+c` is not fused under `exact`; use `fma(a,b,c)`" **[inference]**.
5. **Build the cold-start eval before the compiler is finished [inference] (high).**
   - (a) A Mithril MultiPL-E (R03).
   - (b) A *card-size sweep*: Tier 0 only, Tier 0+1, Tier 0+1+2, measured on Claude, GPT and one open model.
   - (c) A *false-friend probe set*: ThonPy-style items, one per deliberate deviation from Rust.
   - (d) A *chess-study-style cost curve*: prompts and dollars per task for the same task in C, Rust and Mithril.
   - (e) An *independent-writer test*: model family A writes a spec in Mithril designed by family B (F1.4).
   - Publish all of it under INV-HONEST.
6. **Freeze early, change additively.** Every breaking change becomes stale-prior debt, as Zig 0.15 and Mojo's pre-1.0 churn show (F2.4). Use editions or `mithc fix` migrations rather than silent semantic changes.

## Implications for Hearth

1. **Hearth's C11 engine is the first real cold-start test, and the surface should minimise semantic distance from it [inference].** A Rust- and C-shaped `.mith` lets agents port `quant_avx2.c` and `model.c` by transliteration plus annotation. A Python-hosted DSL would force a paradigm shift and put the port outside INV-DEP's "C11 runtime only" spirit, unless it only generates C, as Exo does (R05).
2. **The numpy reference is the oracle that makes agent porting safe.** Differential tests (INV-NUM-1/2) and bit-exact cross-ISA checks (INV-DET-3) supply the feedback loop that F5.4 identifies as the biggest lever. The chess study shows unverified agent self-assessment is unreliable.
3. **Write Hearth's determinism rules as a curated Tier-0 card.** The AGENTS.md study found that non-standard requirements and tool instructions are what context files are good for, and that overviews are not. INV-DET-3 (no FMA contraction, fixed 16-lane reductions) is exactly that kind of rule. It is also a semantic false friend, because C compilers may contract FMAs by default **[inference; check per compiler]**. Mithril's `exact` mode should make the rule a type or keyword, not prose.
4. **Use Hearth-hosted local models for the parts frontier APIs cannot do.** Hearth owns the logits, so it can apply Mithril grammar and type masks. MojoBench's roughly 6.6M-token fine-tune beat 2024 frontier models on Mojo, which suggests a small validated Mithril corpus is enough to adapt a local model. Generate that corpus by translating Hearth's own C and numpy code into Mithril and keeping only variants that pass the golden tests (MultiPL-T style) **[inference]**.
5. **Measure the port with a cost curve.** Prompts, dollars and wall time per Hearth module (store, pool, quant, model) in C vs Mithril, under the same agent harness. This is the honest acid test the brief calls for **[inference]**.

## Where the seed discussion is right or wrong

| Claim | Verdict | Evidence |
|---|---|---|
| **H4** (agents read `/llms.txt` + `/llms-full.txt` with EBNF grammar and 20–30 snippets) | **Direction right, delivery and size wrong.** | A compact *always-in-context* index works when it carries new knowledge (Vercel 53% → 100%). An on-demand skill went uninvoked 56% of the time, and "comprehensive" docs added only +0.7 pp (SkillsBench). The existing young-language cards (Mojo about 4k words, MoonBit about 9k) suggest 20–30 snippets are too few to cover a whole language and its false friends **[inference]**. The grammar should be Lark, not prose EBNF. llms.txt is a cheap extra, not the mechanism (R04). |
| **H5** (LSP with machine-actionable JSON diagnostics) | **Right, and probably the highest-leverage item.** | Feedback is worth +10–20 points (GitChameleon 2.0) and about 2× where familiarity is lowest (Hazel, R03). Diagnostics should name the false-friend rule violated **[inference]**. |
| **H6** (seed 50+ synthetic GitHub repos so coding models learn the language) | **Wrong as a cold-start lever for frontier models; right in spirit for local fine-tunes.** | Mojo has years of public code and still ships a correction skill. Inclusion in third-party pretraining is uncontrolled and lagged (R03, R04). A validated corpus *you* fine-tune on works: MojoBench about 6.6M tokens, MultiPL-T. |
| **H7** (Mojo "cannot do stochastic asm superoptimisation or user-space PCIe DMA"; "nothing combines all of this") | Out of G01 scope (see R04). | Relevant here: Mojo is the clearest *cautionary* case for a Python-shaped systems language (F2.4), and the chess study's Mojo session failed to converge. |
| **B4, B6, B7, C7** (surface hardware concepts: `line64`, `streaming`, entropy-tracked branch primitives, async prefetch pipelines) | **Right as semantics, risky as novel surface vocabulary.** | Each new concept is zero-prior vocabulary. Express them as Rust-style attributes and types (`@align(64)`, `@nontemporal`) with conservative defaults, so a missing annotation is never a silent false friend **[inference]**. |
| **C6** (INT2/INT4/FP4/ternary as primitive types) | **Writability-neutral if named familiarly.** | `u4`/`i2`-style names follow Zig's and Rust's conventions. Inventing new names (`bitplane<1.58>`) adds card lines **[inference]**. |
| **E8 syntax sketch** (`tensor<float8,[B,64,64,16],Layout::SpatioTemporal3D>`, `solve_ode(...){ fuse_layers { ... } }`) | **Wrong direction for an AI-first surface.** | C++-template-style generics mixed with novel block keywords put new semantics behind semi-familiar tokens: the false-friend pattern (F2) **[inference]**. |
| **I5, I6** (`hot_patch`; `invariant subspace(...)` types) | **No writability evidence; expect the highest agent cost.** | These are novel semantics with no prior, which only a checker can make safe (Verus/Dafny gap, F4.3) **[inference]**. |
| **B12** (fine-tune an LLM on intent → -O3 disassembly pairs, SMT in the loop) | **Consistent with evidence for local models.** | MojoBench, MultiPL-T. Value for x86 targets is unverified (R03). |
| **H2** (drop-in C-FFI / Python binding) | **Right for adoption; orthogonal to writability.** | A Python *binding* to call Mithril code is different from a Python-*embedded* Mithril surface. Only the latter has the PyHDL-style penalty **[inference]**. |

## Open questions

1. **In-context learning curve for a new general-purpose language on 2026 frontier models.** What pass@1 do Claude Opus 4.7/4.8/5.x and GPT-5.5 reach on a Mithril MultiPL-E with Tier 0, Tier 0+1 or the full manual? No study found. Mithril must measure it.
2. **Have newer models closed the false-friend gap?** ThonPy (2023) and RustEvo² (early 2025) are the latest quantitative points I could reach. A 2026 replication of the counterfactual tasks would settle how much deviation from Rust is affordable.
3. **Is an agent-designed language cheaper for agents?** GAMBIT (n = 1) suggests about 4× mainstream cost and Python-level output. An independent-writer test is needed (F1.4).
4. **Per-DSL kernel writability.** MultiKernelBench's CUDA vs NPU vs TPU numbers were **unverified** here (fetch failed). Data for Exo, cuTile and Pallas: none found.
5. **2026 successors to CodeUpdateArena, VersiCode, LibEvolutionEval and GitChameleon, and any "esoteric language" benchmark.** Not reachable without search. A search-enabled pass should check.
6. **Card-size optimum for a whole language, as opposed to an API delta.** SkillsBench and Vercel measure deltas over a known base. A new language may need more. The size sweep in Implications §5b answers this.
7. **Claude decode-time constraints.** With JSON-Schema-only structured outputs, what is the best envelope (structured AST edits vs text plus fast `mithc check`) for enforcing Mithril syntax with Claude? (R03 open question 5.)
8. **Writability data for MoonBit, Gleam, Roc, Jac and Zig.** None found. MoonBit's Fastcc (35k LOC by an agent) is a vendor anecdote, not an eval.

## Sources

- Acher & Jézéquel 2026, chess engines in 17 languages — https://arxiv.org/html/2606.13763 ; https://arxiv.org/abs/2606.13763
- Wu et al., counterfactual tasks (ThonPy) — https://arxiv.org/abs/2307.02477 ; https://arxiv.org/html/2307.02477v3
- SPEAC / Eudoxus (UCLID5) — https://arxiv.org/abs/2406.03636 ; https://arxiv.org/html/2406.03636v4
- PyHDL-Eval (MLCAD 2024) — https://www.csl.cornell.edu/~cbatten/pdfs/batten-pyhdl-eval-mlcad2024.pdf ; https://github.com/cornell-brg/pyhdl-eval
- MojoBench — https://arxiv.org/abs/2410.17736 ; https://arxiv.org/html/2410.17736
- MTOB (Kalamang) — https://arxiv.org/abs/2309.16575
- Gemini 1.5 report — https://arxiv.org/abs/2403.05530
- Typed holes / Hazel — https://arxiv.org/html/2409.00921v1
- AutoVerus — https://arxiv.org/html/2409.13082v2
- LLMLift — https://arxiv.org/html/2406.03003
- RustEvo² — https://arxiv.org/abs/2503.16922
- CodeUpdateArena — https://arxiv.org/abs/2407.06249
- VersiCode — https://arxiv.org/abs/2406.07411
- LibEvolutionEval — https://arxiv.org/abs/2412.04478
- GitChameleon — https://arxiv.org/abs/2411.05830
- GitChameleon 2.0 — https://arxiv.org/abs/2507.12367 ; https://arxiv.org/html/2507.12367v2
- CODESYNC — https://arxiv.org/abs/2502.16645
- Zig 0.15.1 release notes — https://ziglang.org/download/0.15.1/release-notes.html
- Modular skills / mojo-syntax — https://github.com/modular/skills ; https://raw.githubusercontent.com/modular/skills/main/mojo-syntax/SKILL.md
- Mojo 1.0 post — https://www.modular.com/blog/modular-26-5-mojo-1-0-is-here
- Mojo changelog index — https://mojolang.org/docs/changelog
- Mojo llms.txt — https://mojolang.org/llms.txt
- MoonBit agent guide — https://github.com/moonbitlang/moonbit-agent-guide ; https://raw.githubusercontent.com/moonbitlang/moonbit-agent-guide/main/moonbit-agent-guide/SKILL.md
- MoonBit blog index — https://www.moonbitlang.com/blog/
- MoonBit AI post (2024) — https://www.moonbitlang.com/blog/moonbit-ai
- MoonBit Fastcc — https://www.moonbitlang.com/blog/fastcc-ai-driven-development
- MoonBit "Building Agents" — https://www.moonbitlang.com/blog/building-agents-moonbit
- Roc AGENTS.md — https://raw.githubusercontent.com/roc-lang/roc/main/AGENTS.md
- AutoCodeBench — https://arxiv.org/abs/2508.09101 ; https://arxiv.org/html/2508.09101v1
- SWE-bench Multilingual — https://www.swebench.com/multilingual.html ; https://www.swebench.com/
- Multi-SWE-bench — https://github.com/multi-swe-bench/multi-swe-bench ; https://arxiv.org/abs/2504.02605
- SWE-PolyBench — https://arxiv.org/abs/2504.08703
- Aider polyglot leaderboard — https://aider.chat/docs/leaderboards/
- Claude Opus 4.5 announcement — https://www.anthropic.com/news/claude-opus-4-5
- Vericoding — https://arxiv.org/abs/2509.22908
- AlgoVeri — https://arxiv.org/abs/2602.09464
- Twist et al., LLM language/library preferences — https://arxiv.org/abs/2503.17181
- Language confusion (Moumoula et al.) — https://arxiv.org/abs/2503.13620
- MultiPL-E — https://github.com/nuprl/MultiPL-E ; https://arxiv.org/abs/2208.08227
- TritonBench — https://arxiv.org/abs/2502.14752 ; https://arxiv.org/html/2502.14752
- MultiKernelBench — https://arxiv.org/abs/2507.17773
- KernelBench — https://github.com/ScalingIntelligence/KernelBench
- KernelAgent — https://github.com/meta-pytorch/KernelAgent
- Helion — https://pytorch.org/blog/helion/
- Vercel AGENTS.md vs skills — https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals
- Evaluating AGENTS.md — https://arxiv.org/abs/2602.11988 ; https://arxiv.org/html/2602.11988
- SkillsBench — https://arxiv.org/abs/2602.12670 ; https://arxiv.org/html/2602.12670
- Anthropic, Agent Skills — https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- Anthropic, context engineering — https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Chroma, Context Rot — https://www.trychroma.com/research/context-rot
- NoLiMa — https://arxiv.org/abs/2502.05167
- Many-shot ICL — https://arxiv.org/abs/2404.11018
- Low-resource/DSL code-gen survey — https://arxiv.org/abs/2410.03981
- DocCGen — https://arxiv.org/abs/2406.11925
- Type-constrained decoding — https://arxiv.org/abs/2504.09246
- XGrammar — https://arxiv.org/abs/2411.15100
- llguidance — https://github.com/guidance-ai/llguidance
- OpenAI GPT-5 custom tools / CFG — https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_new_params_and_tools
- Claude structured outputs — https://platform.claude.com/docs/en/build-with-claude/structured-outputs
