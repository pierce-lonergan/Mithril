# R03 — What makes a language easy or hard for LLMs

*Research dossier for the Mithril architecture phase. Compiled 2026-10-11. Every factual claim carries an inline source; my own reasoning is marked **[inference]**. Confidence tags: (high / medium / low).*

> **Method note.** The shared web-search budget ran out partway through this task. After that I checked claims by fetching the primary sources directly: arXiv abstract and HTML pages, the PDFs of MultiPL-E and the type-constrained decoding paper, vendor docs and project pages. I did not search for anything new after that point. Some 2026 developments may therefore be missing, such as newer constrained-decoding engines or newer verification benchmarks. Treat "I found no evidence of X" in this file as "not found under a limited search", not "X does not exist".

---

## Summary

- **The training-data prior dominates.** Pass rates follow how common a language is in pretraining data. Exceptions exist (Lua and Scala do well), but low-resource languages still lag. In agentic, repository-level work, non-Python languages lag clearly, even for frontier models ([MultiPL-E](https://arxiv.org/abs/2208.08227), [Multi-SWE-bench](https://arxiv.org/abs/2504.02605), [SWE-bench Multilingual](https://www.swebench.com/multilingual.html)). (high)
- **Unfamiliar syntax hurts more than unfamiliar semantics, and familiar syntax with changed meaning ("false friends") hurts most.** Models drift back into Python or a neighbouring language. Performance drops on counterfactual variants of familiar tasks. The best low-resource results come from routing generation through a language the model already knows: SPEAC's "parent language", LLMLift's Python IR, MultiPL-T's translated corpora ([language confusion](https://arxiv.org/abs/2503.13620), [counterfactual tasks](https://arxiv.org/abs/2307.02477), [SPEAC](https://arxiv.org/abs/2406.03636), [LLMLift](https://arxiv.org/abs/2406.03003), [MultiPL-T](https://arxiv.org/abs/2308.09895)). (high)
- **Static types help mainly as a feedback and context channel, not as a prior.** Type annotations had no overall effect on Codex pass rates. Replacing precise types with `Any` hurt TypeScript, though. Type definitions were the single most useful context in Hazel. About 94% of TypeScript compile errors from LLMs are non-syntactic, i.e. type errors ([MultiPL-E PDF](https://arxiv.org/pdf/2208.08227), [typed holes](https://arxiv.org/abs/2409.00921), [Mündler et al.](https://arxiv.org/abs/2504.09246)). (high)
- **Constrained decoding is mature for grammars and emerging for types.** Grammar masks now cost tens of microseconds per token ([llguidance](https://github.com/guidance-ai/llguidance), [XGrammar](https://arxiv.org/abs/2411.15100)). Type-constrained decoding cut TypeScript compile errors by more than half, where syntax-only constraints removed at most about 9% ([Mündler et al.](https://arxiv.org/abs/2504.09246)). Frontier APIs expose only limited constraints. OpenAI accepts Lark CFGs for custom tools. Claude accepts JSON Schema only, with no recursive schemas ([OpenAI cookbook](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_new_params_and_tools), [Claude docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)). (high)
- **Compiler-feedback loops work only if the feedback is localized and grouped, and the model already has context.** RustAssistant's error grouping took GPT-3.5 from 4.97% to 44.76% fixed. Error rounds alone did nothing in Hazel without type context ([RustAssistant](https://arxiv.org/html/2308.05177), [typed holes](https://arxiv.org/html/2409.00921v1)). Self-repair is limited by the quality of the feedback ([Olausson et al.](https://arxiv.org/abs/2306.09896)). (medium-high)
- **Edit interfaces are a first-order failure source.** Whole-file viewing and unguarded edits lowered SWE-agent's score. After one failed edit, the chance of an eventual successful edit fell from 90.5% to 57.2%. Even GPT-5 (high) emitted well-formed Aider diffs only 91.6% of the time ([SWE-agent](https://arxiv.org/html/2405.15793v3), [Aider leaderboard](https://aider.chat/docs/leaderboards/)). Search/replace without line numbers is the convergent best practice ([Diff-XYZ](https://arxiv.org/abs/2510.12487), [OpenAI GPT-4.1 guide](https://developers.openai.com/cookbook/examples/gpt4-1_prompting_guide)). (high)
- **For verification-aware languages, SMT-backed "auto-active" verification is far easier for LLMs than explicit proof construction.** On identical contracts the best reported scores are Dafny 40.3%, Verus 24.7%, Lean 7.8% ([AlgoVeri](https://arxiv.org/abs/2602.09464)). The vericoding union rates are Dafny 82%, Verus 44%, Lean 27% ([vericoding](https://arxiv.org/abs/2509.22908)). In Verina, Lean proofs succeed only 3.6–4.9% of the time ([Verina](https://arxiv.org/abs/2505.23135)). (high)
- **Writing specs is the unsolved part.** LLM-written specs are sound and complete only about half the time ([Verina](https://arxiv.org/abs/2505.23135)). About 9% of "successful" vericoding outputs rested on specs that were too weak ([vericoding HTML](https://arxiv.org/html/2509.22908v1)). Spec length predicted difficulty poorly, while solution length predicted it better. (medium-high)
- **Token efficiency is a second-order lever.** Grammar changes that preserve the AST, and dropping formatting, saved 10–25% of tokens without loss of accuracy ([SimPy](https://arxiv.org/abs/2404.16333), [Hidden Cost of Readability](https://arxiv.org/abs/2508.13666)). Language-to-language token cost varies about 2.6× ([Alderson, 2026](https://martinalderson.com/posts/which-programming-languages-are-most-token-efficient/), informal). That is worth having, but never at the expense of familiarity **[inference]**. (medium)
- **Cold start is solvable, but not by seeding GitHub.** The evidence supports five things together: a familiar surface syntax, a compact grammar-plus-idioms reference in context, typed holes plus structured diagnostics, constrained decoding wherever logits are available, and a validated synthetic corpus built MultiPL-T or AlphaVerus style ([Gemini 1.5 Kalamang result](https://arxiv.org/abs/2403.05530), [DocPrompting](https://arxiv.org/abs/2207.05987), [AlphaVerus](https://arxiv.org/abs/2412.06176)). (medium)

---

## Findings

### 1. Low- vs high-resource languages

**Benchmarks on generating single functions.**
- MultiPL-E translated HumanEval and MBPP from Python into 18 more languages, 19 in total. Codex matched or beat its Python score on several of them ([MultiPL-E](https://arxiv.org/abs/2208.08227)).
- How common a language is had a "predictable effect": medium, low and niche languages scored reliably below high-frequency ones. Lua and Scala were notable exceptions that did well, and Racket was among the worst ([MultiPL-E PDF §5.2.3, Fig. 9](https://arxiv.org/pdf/2208.08227)).
- Codex perplexity did not track correctness. Perplexity was highest on JavaScript and TypeScript, yet Codex scored best on them (same source, §5.1.4).
- **Lesson [inference]:** a language can be "rare" and still be easy if it closely resembles common ones (Lua is close to JavaScript and Python), and "rare plus idiosyncratic" (Racket) is the worst case.

**Racket's failure modes tell you what happens when a model doesn't know the syntax.**
- Codex often generated *Markdown* when asked for Racket. The authors attribute this to the `#lang racket` header looking like a Markdown heading.
- The most common static error across languages was "UndefinedIdentifier". It included Python-like keywords leaking into other languages ([MultiPL-E PDF §6.5](https://arxiv.org/pdf/2208.08227)). (high)

**Fixing the low-resource gap with data.**
- MultiPL-T takes commented Python, has the model write tests, translates the code into Julia, Lua, OCaml, R or Racket, and keeps only translations that pass the tests. This produced "tens of thousands of validated training items" ([MultiPL-T abstract](https://arxiv.org/abs/2308.09895)).
- In the preprint version, the Lua fine-tune reached StarCoderBase's *Python* level, and Racket and OCaml roughly doubled on MultiPL-E ([Guha group page](https://ccs.neu.edu/~arjunguha/main/papers/cassano-multipl-t.html); OOPSLA 2024: [SPLASH listing](https://2024.splashcon.org/details/splash-2024-oopsla/78/Knowledge-Transfer-from-High-Resource-to-Low-Resource-Programming-Languages-for-Code-)). (high for direction; exact numbers are in the paper, which I did not extract)

**Breadth benchmarks.**
- McEval (ICLR 2025) has 40 languages and about 16K samples. It finds large gaps between closed and open models, worst on low-resource languages ([McEval](https://proceedings.iclr.cc/paper_files/paper/2025/hash/dad66bb085bab14fbca07cfa4271f00b-Abstract-Conference.html)).

**Agentic, repository-level work, 2025–2026.**
- Multi-SWE-bench (NeurIPS 2025) has 2,132 instances in 8 languages. LLMs "perform well on Python" but generalize poorly to other languages, and cross-file issues degrade them sharply ([arXiv](https://arxiv.org/abs/2504.02605), [NeurIPS](https://neurips.cc/virtual/2025/poster/121692)).
- SWE-PolyBench (2,110 instances, 21 repositories) reports uneven performance across languages ([arXiv](https://arxiv.org/abs/2504.08703)).
- On SWE-bench Multilingual (300 tasks, 9 languages), SWE-agent with Claude 3.7 Sonnet resolved 42.67%, against 63% on SWE-bench Verified (Python) ([swebench.com](https://www.swebench.com/multilingual.html)). By language:
  - Rust highest at 58.1%, then Java at 53.5%.
  - JavaScript/TypeScript 34.9%, Go 31.0%, C/C++ lowest at 28.6%.
- **Why this matters for Mithril [inference]:**
  - Rust is far less common than C/C++ yet scored highest. That fits the hypothesis that a strict compiler with rich diagnostics turns hidden runtime bugs into visible, fixable compile errors in an agent loop.
  - It is one model, though, and the page says it cannot separate the effect of language from that of task difficulty. (low-medium)
- **Rates reported second-hand.** Mündler et al. cite Rust compile-error rates of 18% for o1-mini, 39% for DeepSeek R1 and 27% for Claude 3.5 Sonnet on hard synthesis tasks, and 40–60% for OCaml and Haskell. These come from the PLDI paper's discussion, citing a third party ([Mündler et al. PDF p.21](https://arxiv.org/abs/2504.09246)). (medium, second-hand)

**Ecosystem drift is its own low-resource problem.**
- An ICSE'25 study of 7 LLMs, 145 API mappings and 28,125 prompts measured how often code completion uses *deprecated* Python APIs and proposed mitigations ([Wang et al.](https://arxiv.org/abs/2406.09834)).
- Across 576,000 samples from 16 models, the average hallucinated-package rate was at least 5.2% for commercial models and 21.7% for open models, with 205,474 unique fake package names (USENIX Security 2025, [Spracklen et al.](https://arxiv.org/abs/2406.10279)). (high)
- **[inference]** A new language's churn is a liability: every breaking change becomes stale training data.

### 2. Learning new or unseen languages from documentation in context

- **Long context can teach a language.**
  - MTOB asks models to learn Kalamang, a language with fewer than 200 speakers, from a grammar book alone. 2023 baselines reached 44.7 / 45.8 chrF, against 51.6 / 57.0 for a human learner ([MTOB](https://arxiv.org/abs/2309.16575)).
  - Gemini 1.5 later reported translating English to Kalamang "at a similar level to a person who learned from the same content", with the full manual in context ([Gemini 1.5 report](https://arxiv.org/abs/2403.05530)). (high that this works for natural language; transfer to programming languages is **[inference]**)
- **Documentation retrieval helps with unseen APIs.** DocPrompting (ICLR 2023) retrieves documentation and then generates code. It raised CodeT5's CoNaLa pass@1 by 2.85 points (52% relative), and its motivation is that models "cannot generalize to using unseen functions and libraries" ([DocPrompting](https://arxiv.org/abs/2207.05987)).
- **Grammars in the prompt help with DSLs.** Grammar prompting puts a minimal BNF subset next to each example and has the model predict the grammar first. LLMs became competitive on SMCalFlow, GeoQuery, PDDL and SMILES generation ([Wang et al.](https://arxiv.org/abs/2305.19234)).
- **Very low-resource languages need a bridge.**
  - On UCLID5, a formal verification language, LLMs fail to produce even syntactically valid programs.
  - SPEAC designs a "parent language" the model already writes well, repairs output that falls outside it, and compiles to the target. It beat retrieval and fine-tuning baselines on syntactic validity ([SPEAC](https://arxiv.org/abs/2406.03636)).
  - LLMLift expresses DSL operator semantics as *Python functions* and writes invariants as Python boolean expressions, because "LLMs struggle to generate SMT-LIB". It solved 44/45 distributed-computing benchmarks (prior tool: 40/45) and 60/60 TACO benchmarks (prior: 57/60), using about 100 lines of prompt in place of over 1,000 lines of heuristics ([LLMLift HTML](https://arxiv.org/html/2406.03003)). (high)
- **Hazel shows the cold-start gap and how to close it.** Hazel is a niche typed functional language.
  - With GPT-4 and no context, the model "often produces syntactically incorrect code".
  - Type definitions were the most important context.
  - Error-correction rounds roughly doubled results in Hazel but only gave about 1.2× in TypeScript. Feedback matters most where familiarity is lowest ([typed holes HTML](https://arxiv.org/html/2409.00921v1)). (high)
- **A language young in training data can still be easy if it borrows a familiar host.** AutoVerus notes that Verus "does not require LLM to learn a new language" because it is Rust, even though Verus has few examples ([AutoVerus](https://arxiv.org/html/2409.13082v2)).
- **Gap.** I found no controlled 2025–2026 study measuring frontier-model pass rates on a genuinely new general-purpose language given only its manual. That is an open question, and Mithril should measure it itself (see Open questions).

### 3. Syntax familiarity and "false friends"

- **Familiar tasks with changed rules degrade.** On 11 counterfactual task variants, performance "substantially and consistently degrades" relative to the default conditions. The authors read this as models relying partly on narrow, non-transferable procedures ([Wu et al., NAACL 2024](https://arxiv.org/abs/2307.02477)). (high)
- **Language confusion is widespread.** Across 10 LLMs and 6 datasets, models generate code in languages they were not asked for. They default to Python and swap between close pairs such as C# and Java. Explicit language keywords were the best mitigation, and quantization made confusion worse ([Moumoula et al.](https://arxiv.org/abs/2503.13620)). (high)
- **Prompt surface details matter, even within one language.**
  - Multi-line comments raised Racket pass@1 by 1.9% but lowered PHP by 3.1%.
  - Removing named arguments from Perl prompts cost 8% ([MultiPL-E PDF §6.3](https://arxiv.org/pdf/2208.08227)).
- **What this means for Mithril [inference]:**
  - The safest syntax is a dialect of a very common language in which every construct that *looks* like the parent *means* the same as in the parent. New constructs get new, unambiguous keywords.
  - A familiar-looking token with different semantics is the worst choice. Examples: `=` as equality, 1-based indexing, Rust-like `&` with different aliasing rules.
  - Leading keywords such as `fn`, `kernel` or `let` give the model a strong per-line "language identity" signal, which counters confusion.

### 4. Static vs dynamic typing

- **Types as a prior: little effect.**
  - In MultiPL-E, splitting typed from untyped languages showed no overall effect of type annotations (p = 0.33 HumanEval, p = 0.23 MBPP).
  - Removing annotations from Python prompts made no significant difference.
  - Replacing TypeScript signatures with `Any` cost 2.5% (p < 0.001). The authors conclude that informative types are "necessary for languages where type annotations are standard" ([MultiPL-E PDF §6.2](https://arxiv.org/pdf/2208.08227)). (high, but 2022-era Codex)
- **Types as an error channel: large effect.**
  - In TypeScript generation, syntactic errors averaged only about 6% of compile errors. In the main tables, only 9.0% (HumanEval) and 4.9% (MBPP) of failures to compile were syntax errors.
  - Type errors therefore dominate ([Mündler et al., PLDI 2025](https://arxiv.org/abs/2504.09246)).
  - GitHub's widely quoted "94% of LLM compilation errors are type-check failures" comes from this paper ([GitHub blog](https://github.blog/ai-and-ml/llms/why-ai-is-pushing-developers-toward-typed-languages)). (high)
- **Types as context: large effect.**
  - In Hazel and TypeScript, type definitions were the most impactful context.
  - Relevant headers tripled test performance only *when types were present* ([typed holes](https://arxiv.org/html/2409.00921v1)).
  - Monitor-guided decoding enforces type-consistent dereferences using static analysis. With it, SantaCoder-1.1B beat text-davinci-003 on compilation rate ([MGD, NeurIPS 2023](https://arxiv.org/abs/2306.10763)). (high)
- **Market signal (correlation, not causation).**
  - TypeScript became GitHub's most-used language by monthly contributors in August 2025 (2,636,006 contributors). GitHub ties this partly to AI-assisted development and partly to frameworks defaulting to TypeScript ([Octoverse 2025](https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/)).
  - Luau grew more than 194% and Typst more than 108% ([GitHub blog](https://github.blog/ai-and-ml/llms/why-ai-is-pushing-developers-toward-typed-languages)). (medium as evidence for LLM ergonomics)
- **Token cost of types.** In an informal RosettaCode comparison, dynamic languages were generally more token-efficient. Haskell and F#, which rely on type inference, came close to the best dynamic languages ([Alderson](https://martinalderson.com/posts/which-programming-languages-are-most-token-efficient/)). (low-medium)
- **[inference]** The sweet spot is: mandatory signatures at module and function boundaries (context plus checking), local inference inside bodies (token economy), and no `Any` escape hatch by default.

### 5. Grammar- and type-constrained decoding

**Grammar constraints.**
- **Synchromesh** combined target-similar example selection with constrained semantic decoding. It reported complementary gains for SQL, Vega-Lite and SMCalFlow without fine-tuning ([arXiv](https://arxiv.org/abs/2201.11227)).
- **SynCode** builds a DFA mask store from a CFG and cut syntax errors in generated Python and Go by 96.07% ([arXiv](https://arxiv.org/abs/2403.01632)).
- **XGrammar** (MLSys'25) splits tokens into context-independent ones, which are precomputed, and context-dependent ones. It reports up to 100× speedups and "near-zero overhead" end to end ([arXiv](https://arxiv.org/abs/2411.15100)).
- **llguidance** uses an Earley parser with a derivative-based lexer.
  - It computes a mask in about 50 µs of CPU time per token for a 128k-token vocabulary.
  - It accepts Lark-like CFGs, JSON Schema and regex.
  - It is integrated in OpenAI Structured Outputs, vLLM, SGLang, llama.cpp and Chromium ([GitHub](https://github.com/guidance-ai/llguidance)).
- **JSONSchemaBench** (10K schemas) found constrained decoding *raised* Llama-3.1-8B accuracy slightly. With Guidance: GSM8K 80.1 → 83.8, Last Letters 50.7 → 54.0 ([HTML](https://arxiv.org/html/2501.10868v3)). (high)

**Caveats.**
- "Let Me Speak Freely?" found reasoning declined under strict format restrictions such as JSON or XML ([arXiv](https://arxiv.org/abs/2408.02442)).
- Grammar-Aligned Decoding (NeurIPS 2024) shows that naive constrained decoding distorts the model's distribution. Grammatical but low-likelihood outputs get over-weighted. Their ASAp sampler corrects this ([arXiv](https://arxiv.org/abs/2405.21047)).
- **[inference]** The two can be reconciled: constrain the *code channel* and leave reasoning unconstrained, which is what tool-call grammars do.

**Type constraints (PLDI 2025).** Mündler et al. built prefix automata plus a search over inhabitable types for a large TypeScript subset ([PDF](https://arxiv.org/abs/2504.09246), Tables 2–4):
- Compile errors in synthesis fell by 75.3% (HumanEval) and 52.1% (MBPP). Idealized syntax-only constraining would have removed only 9.0% and 4.8%.
- Repair success for Gemma 2 2B went from 33.5% to 56.4% (HumanEval) and from 25.8% to 58.4% (MBPP).
- Average pass@1 rose by 3.5% (synthesis), 5.0% (translation) and 37.0% (repair), relative.
- The overhead was 39.1–52.1% median wall time in an unoptimized Python implementation. 99.4% of tokens needed only one check.
- The authors explicitly suggest that future language designers write "their compilers as an incremental completion engine". (high)

**Industry precedent.** MoonBit calls itself "AI-native" ([homepage](https://www.moonbitlang.com/)). Its blog describes a "flat" design with mandatory top-level signatures, and local (syntax) plus global (type) samplers with a speculation buffer and backtracking. It claims a significant improvement in compile rate at about 3% performance cost, but publishes no figures in text ([MoonBit blog](https://www.moonbitlang.com/blog/moonbit-ai)). (low: vendor claim)

**What the frontier APIs allow.**
- OpenAI's GPT-5 custom tools accept **Lark CFGs or Rust-syntax regex**, enforced with llguidance, with restrictions: greedy lexer, only `%import common`, and `%ignore` discouraged ([OpenAI cookbook](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_new_params_and_tools)).
- Claude's structured outputs accept **JSON Schema only**. Recursive schemas and numeric or length constraints are not supported, and compiled grammars are cached for 24 hours ([Claude docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)).
- Mündler et al. note that black-box APIs do not expose full next-token distributions ([PDF p.21](https://arxiv.org/abs/2504.09246)). (high)
- **[inference]** Hence Mithril's syntax can be hard-constrained for Claude only through a non-recursive envelope, such as a JSON edit operation with a string payload. Full grammar and type constraints are feasible only on local or open models. That is exactly where Hearth sits.

### 6. Typed holes as LLM context

- **Hazel's semantics.** Hazel gives every incomplete program a static type and a dynamic meaning. Evaluation "proceeds around holes", tracks each hole's closure, and supports fill-and-resume (POPL 2019, [Omar et al.](https://arxiv.org/abs/1805.00155)).
- **Holes as prompts.** Blinn et al. (OOPSLA 2024) use the language server to give the model each hole's expected type and typing context, plus semantically relevant type definitions and headers from across the codebase. They then iterate on the model's output with the server's error messages.
- **Measured effects** ([HTML](https://arxiv.org/html/2409.00921v1)):
  - StarCoder2-15B in Hazel improved about 10× with type information.
  - For GPT-4, error rounds multiplied gains 4× (types without headers) and 1.5× (types plus headers).
  - Error rounds alone were ineffective.
- **ChatLSP.** The paper proposes ChatLSP, a conservative extension to the Language Server Protocol for this kind of static contextualization ([arXiv](https://arxiv.org/abs/2409.00921)). (high)
- **[inference]** Holes give the model a contract-shaped work item ("produce a `Tensor[f32, K]` using these in-scope names"). They let the compiler check and even *run* partial programs, which suits agents generating top-down.

### 7. Compiler-feedback repair loops and diagnostic quality

- **Self-repair helps, within limits.**
  - Self-Debugging raised accuracy by up to 12% on TransCoder and MBPP, and by 2–3% on Spider (9% on the hardest Spider problems) ([Chen et al.](https://arxiv.org/abs/2304.05128)).
  - Once its cost is counted, self-repair's gains are "often modest". They were limited by the model's ability to critique its own code: feedback from a stronger model gave "substantially larger" gains ([Olausson et al., ICLR 2024](https://arxiv.org/abs/2306.09896)). (high)
- **RustAssistant on Rust compile errors** ([HTML](https://arxiv.org/html/2308.05177)):
  - GPT-4 fixed 73.63% of real-world crate errors with N = 5, and 92% of micro-benchmarks.
  - Grouping related errors took GPT-3.5 from 4.97% to 44.76%.
  - A localized, line-numbered "changelog" prompt format took GPT-3.5 from 10.74% to 73.70% on micro-benchmarks.
  - The authors used rustc's text verbatim as the explanation, calling the errors "self-explanatory". Even so, the model sometimes ignored the compiler's suggested fix.
  - Observed failure modes: partial fixes, propose-then-undo loops, and fixes that compile but contradict developer intent.
  - The paper does not measure message quality directly. (high on numbers, medium on attributing them to diagnostic quality)
- **Verifier feedback.**
  - On AlgoVeri, Gemini-3 tripled its Dafny pass rate through iterative repair, while GPT-OSS saturated early ([AlgoVeri](https://arxiv.org/abs/2602.09464)).
  - DafnyBench reports how retries with error messages raise success, and how success falls as the required code and annotations grow ([DafnyBench](https://arxiv.org/abs/2406.08467)). (high)
- **Machine-readable diagnostics already exist.**
  - rustc's `--error-format=json` emits stable codes, primary spans, child notes, a `suggested_replacement` and a `suggestion_applicability` level: `MachineApplicable`, `MaybeIncorrect`, `HasPlaceholders` or `Unspecified` ([rustc docs](https://doc.rust-lang.org/rustc/json.html)).
  - **[inference]** This is the right template to extend. Mithril should add the expected and actual type, the hole context, and a cause-ordered group ID.
- **Gap.** I found no controlled experiment that varies only the *wording or structure* of compiler messages and measures LLM repair success. The closest evidence is RustAssistant's prompt-format and grouping ablations and Olausson's feedback-quality result. (medium)

### 8. Token efficiency and tokenisation

- **AI-oriented grammar (SimPy).** SimPy (ISSTA'24) rewrites Python's grammar to drop formatting tokens while keeping the same AST, so code converts back and forth losslessly. Token use fell 13.5% for CodeLlama and 10.4% for GPT-4, and models "maintain or even improve" performance ([Sun et al.](https://arxiv.org/abs/2404.16333)). It is unverified whether the performance result needed training on SimPy; check the paper before relying on zero-shot transfer.
- **Formatting is mostly overhead.** Stripping indentation and newlines cut input tokens by 24.5% on average, with no loss of performance. Prompting or fine-tuning shortened *generated* code by up to 36.1% ([Pan et al.](https://arxiv.org/abs/2508.13666)). (high)
- **Language-to-language spread.** With a GPT-4 tokenizer on RosettaCode tasks shared by 19 languages:
  - C was 2.6× less efficient than Clojure.
  - J averaged 70 tokens per task. APL's symbols split into multiple tokens, so its terseness did not pay off.
  - The author calls it "not a scientific study" ([Alderson, 2026-01-08](https://martinalderson.com/posts/which-programming-languages-are-most-token-efficient/)). (low-medium)
- **Names carry meaning.** Nonsense or misleading identifiers significantly hurt CodeBERT on code-analysis tasks ([Wang et al.](https://arxiv.org/abs/2307.12488)), and removing argument names from Perl prompts cost 8% ([MultiPL-E](https://arxiv.org/pdf/2208.08227)). (medium)
- **[inference]** Exotic glyphs (APL lesson) and abbreviated identifiers (naming lesson) both lose. Whitespace-insensitive grammar plus a canonical formatter lets the model emit compact code while humans see pretty code. Savings are about 10–25%, which is small next to the 2–10× gaps between familiar and unfamiliar languages in Sections 1–3.

### 9. Edit formats and agent failure modes

- **Aider's edit formats.**
  - Aider supports whole-file, search/replace (`diff`), `diff-fenced`, unified diff (`udiff`), and architect/editor split formats ([Aider docs](https://aider.chat/docs/more/edit-formats.html)).
  - Switching GPT-4 Turbo to unified diffs raised its laziness-benchmark score from 20% to 61% ([Aider blog](https://aider.chat/2023/12/21/unified-diffs.html)).
  - Its principles for a good format: familiar, simple (no escaping, no line numbers), high-level (rewrite whole functions), and flexible to apply. Disabling lenient matching caused about 9× more edit errors.
- **Format reliability on the 2025 leaderboard** ([Aider leaderboard, updated 2025-11-20](https://aider.chat/docs/leaderboards/)):
  - GPT-5 (high) scored 88.0% but emitted well-formed edits only 91.6% of the time.
  - Gemini 2.5 Pro reached 99.6% well-formed with `diff-fenced`.
- **Format comparisons.**
  - Diff-XYZ finds search/replace best for larger models, structured udiff slightly worse, and little difference for small models ([arXiv](https://arxiv.org/abs/2510.12487)).
  - OpenAI open-sourced its V4A `apply_patch` format because GPT-4.1 was "extensively trained" on it. It locates hunks by context, not line numbers. SEARCH/REPLACE and escape-free pseudo-XML also performed well ([OpenAI guide](https://developers.openai.com/cookbook/examples/gpt4-1_prompting_guide)).
  - Anthropic's `str_replace` requires an exact match that occurs exactly once. Otherwise it returns errors such as "Found 3 matches… provide more context" ([Claude docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/text-editor-tool)). (high)
- **SWE-agent's agent-computer interface ablations** (SWE-bench Lite, GPT-4 Turbo, base 18.0%; [HTML](https://arxiv.org/html/2405.15793v3)):
  - Removing the lint guard on edits: 15.0%. No edit command at all: 10.3%.
  - File viewer window: 30 lines gave 14.3%, the full file gave 12.7%, and 100 lines was best.
  - Iterative search: 12.0%, worse than no search tools at all (15.7%).
  - Keeping the full history: 15.0%, against the default of keeping only the last 5 observations.
- **SWE-agent failure analysis** (same source):
  - About 52% of failures were incorrect or overly specific implementations, and 23.4% were cascading failed edits.
  - The chance of an eventual successful edit fell from 90.5% to 57.2% after one failed edit. (high)
- **Self-improvement found the same weak spot.** The Darwin Gödel Machine improved itself from 20.0% to 50.0% on SWE-bench and from 14.2% to 30.7% on Polyglot. Among the things it discovered were "better code editing tools" and long-context window management ([DGM](https://arxiv.org/abs/2505.22954)). The edit interface is where self-improvement found headroom. (high)

### 10. Verification-aware languages with LLMs

| Benchmark (year) | Language(s) | Headline | Source |
|---|---|---|---|
| DafnyBench (2024; TMLR 2025) | Dafny hint/annotation insertion, 750+ programs | best 68% (Claude 3 Opus, ≤10 tries); success falls with length | [arXiv](https://arxiv.org/abs/2406.08467) |
| Same task, 2025 | Dafny | Opus 4.1 89%; model union 96% | [vericoding HTML](https://arxiv.org/html/2509.22908v1) |
| Clover (2023–24) | Dafny consistency of code, docstring and spec | accepts ≤87% of correct programs, 0 false positives on adversarial ones; found 6 wrong programs in human-written MBPP-DFY-50 | [arXiv](https://arxiv.org/abs/2310.17807) |
| AutoVerus (OOPSLA 2025) | Verus proofs, 150 tasks | >90% proved; over half within 30 s or 3 LLM calls | [arXiv](https://arxiv.org/abs/2409.13082) |
| AlphaVerus (ICML 2025) | Dafny→Verus translation bootstrapping | verified HumanEval/MBPP solutions with no fine-tuning; filtering of misaligned specs against reward hacking | [arXiv](https://arxiv.org/abs/2412.06176) |
| Vericoding (Sep 2025) | 12,504 specs: Dafny / Verus / Lean | union 82.2 / 44.2 / 26.8%; best single model 67.5% (Opus 4.1), 30.9% (GPT-5), 17.9% (GPT-5) | [arXiv](https://arxiv.org/abs/2509.22908) |
| Verina (ICML 2025 / ICLR 2026) | Lean: code, spec and proof, 189 tasks | code 61.4–72.6%, spec 51.0–52.3%, proof 3.6–4.9% | [arXiv](https://arxiv.org/abs/2505.23135), [ICLR](https://iclr.cc/virtual/2026/poster/10011965) |
| AlgoVeri (ICML 2026) | identical contracts, 77 algorithms | Dafny 40.3% (Gemini-3 Flash), Verus 24.7%, Lean 7.8% | [arXiv](https://arxiv.org/abs/2602.09464) |
| IDS (May 2026) | 7 distributed key-value-store specs | Codex/GPT-5.4 and Claude Code/Opus 4.6 solve 2/7; IDS 7/7 at ~6.8 h and $106 per spec | [arXiv](https://arxiv.org/abs/2605.23109) |

**Why the ordering is Dafny > Verus > Lean.**
- AlgoVeri attributes Dafny's lead to its high-level abstractions and SMT automation, which let models "focus on logical correctness". In Verus and Lean, models get stuck in persistent syntactic and semantic barriers ([AlgoVeri](https://arxiv.org/abs/2602.09464)).
- The vericoding authors give two reasons for Lean's weakness:
  - LLMs were trained largely on *mathematical* Lean, not on verifying code.
  - Their scaffold showed the proof state only five times per example ([vericoding HTML](https://arxiv.org/html/2509.22908v1)).
- The contrast is stark: DeepSeek-Prover-V2 reaches 88.9% on miniF2F-test ([arXiv](https://arxiv.org/abs/2504.21801)). (high)
- **[inference]** Lean is an excellent trust base, but a poor *authoring* surface for LLM-written code proofs today. Interactive proof-state feedback is the missing ingredient.

**Specs and cheating.**
- Vericoding rejects `sorry`, `assume(false)` and edits to the spec. Even so, about 9% of successful outputs relied on specs that were too weak, and 15% on poorly translated specs. Spec length was the *weakest* predictor of difficulty, while solution length correlated with failure.
- Adding natural-language descriptions did not significantly help ([vericoding HTML](https://arxiv.org/html/2509.22908v1)).
- Kleppmann argues that LLMs suit proof writing because the checker rejects hallucinated proofs. The specification remains the human bottleneck ([blog, 2025-12-08](https://martin.kleppmann.com/2025/12/08/ai-formal-verification.html)). (high)

### 11. Taxonomies of bugs in LLM-generated code

- **Tambon et al.** studied 333 bugs from Codex, CodeGen and PanGu-Coder and sorted them into 10 categories: misinterpretation, syntax error, silly mistake, prompt-biased code, missing corner case, wrong input type, hallucinated object, wrong attribute, incomplete generation, and non-prompted consideration ([arXiv](https://arxiv.org/abs/2403.08937)).
- **Wang et al. (ICSE 2025)** studied six LLMs on HumanEval and found "non-trivial, multi-line" errors with varied root causes ([arXiv](https://arxiv.org/abs/2406.08731)).
- **Dou et al. (SCIS)** propose 3 categories with 10 subcategories. LLM code is "shorter but more complicated" than canonical solutions, and a real-world benchmark (RWPB) shows a different bug distribution ([arXiv](https://arxiv.org/abs/2407.06153)).
- **Translation bugs (ICSE 2024).** Across 1,700 samples in C, C++, Go, Java and Python, 2.1–47.3% of LLM translations were correct, and failures fell into 15 bug categories ([Pan et al.](https://arxiv.org/abs/2308.03109)).
- **Weak tests hide bugs.** Stronger tests (HumanEval+) cut reported pass@k by up to 19.3–28.9% ([EvalPlus](https://arxiv.org/abs/2305.01210)).
- **Cross-cutting classes:** hallucinated identifiers and packages ([MultiPL-E](https://arxiv.org/pdf/2208.08227), [Spracklen et al.](https://arxiv.org/abs/2406.10279)), deprecated APIs ([Wang et al.](https://arxiv.org/abs/2406.09834)), wrong-language output ([Moumoula et al.](https://arxiv.org/abs/2503.13620)), and edit-application failures ([SWE-agent](https://arxiv.org/html/2405.15793v3)). (high)
- **[inference] Which design lever addresses which class:**
  - A static checker with name resolution and an explicit dependency manifest catches hallucinated objects and attributes, wrong input types and fake packages.
  - Holes and exhaustive pattern matching catch incomplete generation and missing return paths. Mündler et al.'s case study is a missing `return` that type constraints forced the model to fix ([PDF Fig. 9](https://arxiv.org/abs/2504.09246)).
  - Contracts plus property-based tests catch missing corner cases and misinterpretation.
  - Only good specs, human review or tests catch "misinterpretation" and "prompt-biased code". No language feature does.

---

## Synthesis: design requirements for an AI-first language

The requirements below are labelled R03-n so they don't collide with the seed's claim IDs. Each one traces to the findings above; the step from findings to requirement is **[inference]** unless stated.

1. **R03-1 Familiar surface, no false friends.**
   - Take a Rust/TypeScript-flavoured surface, using keywords and operators from those languages with *identical* meanings. Any construct whose semantics differ must look different.
   - Start every top-level item with a distinctive keyword so the language's identity is unambiguous line by line (§1, §3).
2. **R03-2 Small, context-free, constraint-friendly grammar.**
   - Publish the normative grammar *as a Lark file* that fits OpenAI's restrictions: explicit whitespace terminals, no `%ignore` dependence, bounded terminals.
   - Keep the grammar LL/LR-parsable with no significant whitespace (§5, §8).
3. **R03-3 Mandatory signatures at boundaries, inference inside bodies, no implicit `Any`.**
   - Type definitions are the most valuable context and the most common error class (§4, §6).
4. **R03-4 Compiler = incremental completion engine.**
   - Expose a prefix-checking API: "is this prefix extendable to a well-typed program?", and "which token classes are admissible here?".
   - This enables type-constrained decoding on local models and fast rejection of edits (§5).
5. **R03-5 First-class typed holes.**
   - Write holes as `?name` or `?name: T`. A program with holes still type-checks and runs, with holes evaluated as closures.
   - The compiler can report each hole's expected type, in-scope bindings and relevant definitions (ChatLSP-style) (§6).
6. **R03-6 Diagnostics designed for agents.**
   - JSON is primary and text is derived from it.
   - Each diagnostic carries a stable code, a primary span, expected vs actual types, a root-cause group ID (with cascades suppressed or folded), at most one `MachineApplicable` fix, nearest-name suggestions for unknown identifiers and packages, and a pointer to `mithc explain CODE`.
   - Keep diagnostics short and ordered by cause (§7, §11).
7. **R03-7 Structural edit model.**
   - Edits address items by stable symbol path, e.g. `replace fn store::evict`, with search/replace as the fallback. No line numbers.
   - Format canonically before matching. Apply edits leniently, but parse and type-check every edit atomically before accepting it.
   - Give each item a views API that shows about 100 lines. Use small modules (§9).
8. **R03-8 Layered verification: tests, then contracts, then auto-active proofs.**
   - Use Dafny-style `requires`/`ensures`/`invariant` discharged by SMT. Explicit proof terms are optional and come last.
   - Specs must be *executable*, so they can be property-tested before anyone tries to prove them.
   - `assume`/`sorry` are never allowed in accepted code. Specs are owned separately from implementations, so an agent cannot weaken a spec it is implementing (§10).
9. **R03-9 Spec-strength checking.**
   - Mutation-test specs and contracts, and run Clover-style consistency checks between doc, spec and code.
   - Weak specs are the dominant hidden failure (§10).
10. **R03-10 Stability.**
    - Use edition-based evolution, and expose deprecations as `MachineApplicable` migrations.
    - Hash-pin dependencies in a manifest the compiler checks before code generation (§1, §11).
11. **R03-11 Moderate token economy.**
    - Use whitespace-insensitive syntax, a canonical formatter, readable full-word identifiers, ASCII only, and local inference.
    - Target the roughly 10–25% savings the evidence supports. Do not invent glyphs (§8).
12. **R03-12 A measurement harness from day one.** Build three benchmarks before or alongside the compiler (§1, §10):
    - A Mithril MultiPL-E, translating HumanEval and MBPP with the MultiPL-E pipeline.
    - A Verina-style code, spec and proof suite.
    - A Hearth-kernel suite.

### The cold-start ladder: writing a language the model was never trained on

**[inference]**, assembled from §1–§7 and §10. Each rung below has independent evidence.

1. **Familiarity transfer.** If R03-1 holds, most Mithril code is already "in distribution" at the token level. This is the Lua and Verus lesson.
2. **An in-context reference card.** The card holds:
   - the Lark grammar;
   - a "false-friends vs Rust, Python and C" table;
   - 40–80 idiomatic snippets covering every construct;
   - standard-library signatures;
   - the error-code index.

   The evidence is the Kalamang result, DocPrompting and grammar prompting. Mithril should measure pass@1 against card size.
3. **Hole-driven, compiler-in-the-loop generation.** Generate top-down with holes, feed back hole types plus JSON diagnostics, and group errors. The evidence is Hazel (about 10× from types) and RustAssistant (about 9× from grouping).
4. **Constrained decoding where logits exist.** On local or open models (Hearth), apply the grammar plus type masks. On OpenAI, use the Lark CFG tools. On Claude, use a JSON edit envelope plus a fast compile check.
5. **A parent-language escape hatch.** Provide a bridge from a familiar subset into Mithril (SPEAC or LLMLift style), e.g. a Rust- or Python-subset translator. The model can then draft in a familiar subset and lift into Mithril, with differential tests.
6. **Validated synthetic corpora.** Translate test-carrying Python, Rust and C into Mithril (MultiPL-T), and keep only items that pass the compiler, tests and spec checks. AlphaVerus-style treefinement and misalignment filtering apply here. Use the result for retrieval examples (API models) and for fine-tuning local models.
7. **Self-improvement on the toolchain, not just the code.** DGM's largest gains came from editing tools and context management, so let the agents evolve diagnostics, hole context and edit tools, measured against R03-12.

---

## Implications for Mithril

- **The "hardware-native, microarchitecture-synthesized" pitch clashes with AI ergonomics if it shows up in surface syntax [inference].**
  - Every novel concept (ports, µop scheduling, entropy-tracked branches) is unfamiliar vocabulary, and unfamiliar vocabulary is the expensive part (§1–§3).
  - Keep hardware specifics in *annotations and types* with conservative defaults. Example: `@align(64)`, `@nontemporal`, bit-width types named `i4`/`u2` in Rust/Zig style.
  - Keep the core language mainstream-looking. (medium)
- **Make types carry the hardware facts the agent must not get wrong.** Examples: lane width, alignment, determinism mode such as "no FMA contraction", ownership and aliasing.
  - Type errors are what LLMs get wrong and what checkers catch cheaply (§4). Pushing invariants into types turns review into compile errors. (medium-high)
- **Hearth's invariants map naturally onto layered verification, and the verification layer should be SMT/auto-active, not Lean-first.**
  - For LLM authors the gap is 40.3% vs 7.8% on identical contracts (§10).
  - Lean can stay a back-end trust anchor for a small, human-written core, if desired. (high on the ordering; medium on the architecture choice)
- **Build `mithc` as a language server from day one.** It needs incremental parsing, prefix type checking, hole queries and JSON diagnostics (R03-4 to R03-6). This is the cheapest high-leverage investment the evidence supports. (high)
- **Ship the edit tool with the language.**
  - A `mith edit` protocol that is symbol-addressed, validated and atomic does more for agent success than syntax polish.
  - SWE-agent saw a 7.7-point drop without an edit command and a 3-point drop without a lint guard; DGM found its gains there (§9). (high)
- **Plan for two generation regimes [inference].**
  - With API frontier models (Claude): familiarity, the reference card, holes and diagnostics. Hard constraints are limited to a JSON envelope.
  - With local models: full grammar and type constraints, plus fine-tunes on validated synthetic data.
  - Design the grammar and compiler so both regimes share one source of truth.

## Implications for Hearth

- **Hearth is the natural host for Mithril-constrained decoding [inference].**
  - It owns the logits, so it can apply grammar masks (llguidance-class cost: about 50 µs per token on a 128k vocabulary) and Mithril type masks.
  - At Hearth's measured Q4 decode of about 19–22 tok/s (about 45–53 ms per token, [project brief](C:\Users\PIERCE~1\AppData\Local\Temp\claude\C--Users-Pierce-Lonergan-OneDrive-Desktop-New-folder--2-\53025e1e-dd6f-4882-9920-c9ead71cc040\scratchpad\brief.md)), a 50 µs mask is about 0.1% overhead.
  - Type-check calls are costlier, but Mündler et al. needed only one check for 99.4% of tokens (§5).
  - Constraint: INV-DEP (C11 only) rules out linking llguidance (Rust) or XGrammar (C++). The mask engine would have to be reimplemented in C or Mithril. (medium)
- **Migration order should follow familiarity [inference].**
  - Port the numpy reference implementation and the Python toolkit first. They are the most familiar, have the most tests, and serve as differential oracles.
  - Then the C kernels, one at a time, each checked bit-for-bit against the existing C under INV-DET-3.
  - LLM translation is error-prone (2.1–47.3% correct in 2023, 15 bug classes; §11). Differential testing against the C engine is therefore mandatory, not optional. (medium-high)
- **Turn governance into machine-checked specs.**
  - Express INV-DET-1/2/3 (determinism, batch equals sequential, canonical FP order), INV-FMT/SAFE (malformed input never crashes) and INV-LOSSLESS-DEFAULT as contracts or types.
  - Keep INV-VERIFY's mutation testing, and extend it to *specs* so that weak contracts fail (about 9% weak-spec rate in vericoding). (medium)
- **Expect cross-file work to be the hard part.**
  - Multi-SWE-bench shows sharp degradation on cross-file issues (§1). Hearth's store, pool and model coupling is exactly that shape.
  - Keep Hearth's disjoint file ownership and task DAG. Give Mithril modules small, typed interfaces so agents can work per module with hole-typed stubs for their neighbours. (medium)
- **C is a weak baseline language for agents.** C/C++ had the lowest SWE-bench Multilingual resolve rate (28.6%) and Rust the highest (58.1%), for one model (§1).
  - **[inference]** A Mithril with Rust-like strictness and better diagnostics could make Hearth *easier* for agents to maintain than C11 is today, even before any performance gains. That is a measurable, intermediate success criterion. (low-medium)

---

## Where the seed discussion is right or wrong

| Claim | Verdict | Evidence |
|---|---|---|
| **H4** (agents read `/llms.txt` + `/llms-full.txt` with EBNF grammar and 20–30 snippets) | **Partly right.** In-context grammar and docs demonstrably help (Kalamang, DocPrompting, grammar prompting). But the llms.txt spec page I read defines only `llms.txt` plus `.md` page variants and offers no measurement that agents actually consume the files ([llmstxt.org](https://llmstxt.org/)). 20–30 snippets is probably too few to cover every construct **[inference]**. The grammar should be a machine-usable **Lark** file (for constrained decoding), not just EBNF prose. | §2, §5 |
| **H5** (LSP with machine-actionable JSON diagnostics, e.g. `{"error":"SplitCacheAccess","fix":"align_as(64)"}`) | **Right in direction, under-specified.** rustc already has the template (codes, spans, applicability) ([rustc](https://doc.rust-lang.org/rustc/json.html)). The evidence says grouping and localization matter (RustAssistant), and that type and hole context matters more than the message alone (Hazel). Models sometimes ignore suggested fixes. Mithril also needs applicability levels, expected/actual types and cascade grouping. | §6, §7 |
| **H6** (seed 50+ synthetic GitHub repos so coding models learn the language) | **Weak as a primary strategy [inference].** Inclusion in third-party pretraining is uncontrolled and lagged. 50 repos is tiny next to MultiPL-T's "tens of thousands of validated items", which still needed fine-tuning. Unvalidated synthetic code teaches bugs. Replace it with the cold-start ladder: familiarity, reference card, holes and diagnostics, constrained decoding, validated corpora for local fine-tunes. | §1, §2, ladder |
| **H7** ("nothing combines all of this") | **Partly wrong on the AI-first axis.** MoonBit already markets itself as "AI-native", with mandatory top-level signatures and syntax- and type-guided samplers ([MoonBit blog](https://www.moonbitlang.com/blog/moonbit-ai)). Its claims are unquantified in text, but Mithril is not first to the idea. (The hardware half of H7 is outside R03.) | §5 |
| **F2 / F6** (adopt a Lean harness, Lean "replacing ad-hoc SMT solvers") | **Backwards for LLM-authored proofs.** On identical contracts the best reported scores are Dafny (SMT) 40.3% vs Lean 7.8% ([AlgoVeri](https://arxiv.org/abs/2602.09464)), and Lean proof generation succeeds only 3.6–4.9% of the time in Verina. Lean excels at *math* (88.9% miniF2F) but lags on code verification. Use SMT-backed auto-active verification as the authoring layer. Lean, if used, belongs as a small trusted back end. F1's `openai/math` details are unverified here. | §10 |
| **B8** (SMT/Alive2-style equivalence check after an MCTS/LLM superoptimiser) | **Consistent with the evidence** that verifier-gated generation works and that hallucinations are harmless when a checker rejects them ([Kleppmann](https://martin.kleppmann.com/2025/12/08/ai-formal-verification.html), AlphaVerus). The equivalence spec must be immune to cheating (vericoding's `assume` and spec-edit bans). | §10 |
| **B12** (fine-tune an LLM on intent → -O3 disassembly pairs with SMT validation in the loop) | **Plausible pattern.** It matches validated synthetic-data pipelines (MultiPL-T, AlphaVerus). Value and cost are unverified for x86 targets. AlphaVerus's lesson applies: filter out specs that are misaligned or trivially satisfiable, or the model learns to game them. | §1, §10 |
| **I4** (SMT check that an edit "guarantees bounded loss divergence") | **Unverified and likely infeasible as stated [inference].** Nothing in the verification literature reviewed here approaches proving properties of neural-network training dynamics. Even program specs are only sound and complete about half the time when an LLM writes them (Verina). | §10 |
| **C6 / E8 syntax sketches** (`tensor<float8,[B,64,64,16],Layout::SpatioTemporal3D>`, `fuse_layers { ... }`) | **Mixed [inference].** The C++/Rust-like generic syntax is familiar, which is good. Bespoke block DSLs (`fuse_layers`, `solve_ode`) are new vocabulary that needs card documentation, typed holes and grammar constraints to be reliably writable. Name bit-width types in mainstream style (`i4`, `f8e4m3`) rather than inventing new spellings. | §3, §8 |

---

## Open questions

1. **Zero-shot writability.** What pass@1 do frontier models (Claude Opus 5.x, GPT-5.x) reach on a Mithril MultiPL-E given only a 5k / 20k / 100k-token reference card? I found no 2025–2026 study of in-context learning for a *new general-purpose programming language*, so Mithril has to measure this itself.
2. **Diagnostic wording.** Does the structure and wording of diagnostics, beyond grouping and localization, change repair rates? This needs an A/B study on Mithril error codes.
3. **Braces vs indentation.** Do explicit closing delimiters help or hurt generation reliability compared with indentation? I found no direct evidence. Formatting is removable at little cost (§8), but block *structure* is a different question.
4. **Constraints and reasoning.** Do type-constrained masks hurt reasoning quality in long agentic sessions (the Let-Me-Speak-Freely effect), or help (JSONSchemaBench)? Measure on local models served by Hearth.
5. **Claude regime.** What is the best "envelope" for Claude, given that its structured outputs reject recursive schemas? Candidates: a JSON edit op carrying a string payload validated by `mithc`, or a tool that accepts holes one at a time.
6. **Verification authoring ladder.** Which verification layer should be Mithril's default for kernels? SMT auto-active for kernels, and possibly a separate refinement layer for store and pool concurrency? IDS (May 2026) suggests agentic, incremental proof-plus-implementation can verify distributed systems, at about 7 hours and $106 per spec.
7. **Self-improvement target.** Can a DGM-style loop improve Mithril's *toolchain* (diagnostics, hole context, edit tools) measurably on R03-12 benchmarks without overfitting to them?
8. **Verify before relying.** Still unverified: SimPy's zero-shot vs fine-tuned performance claim; exact MultiPL-T per-language numbers; MoonBit's compile-rate figures; whether newer constrained-decoding engines (2026) change the cost picture. The search budget ran out before I could check these.

---

## Sources

- MultiPL-E — https://arxiv.org/abs/2208.08227 ; PDF https://arxiv.org/pdf/2208.08227
- MultiPL-T — https://arxiv.org/abs/2308.09895 ; https://ccs.neu.edu/~arjunguha/main/papers/cassano-multipl-t.html ; https://2024.splashcon.org/details/splash-2024-oopsla/78/Knowledge-Transfer-from-High-Resource-to-Low-Resource-Programming-Languages-for-Code-
- McEval — https://proceedings.iclr.cc/paper_files/paper/2025/hash/dad66bb085bab14fbca07cfa4271f00b-Abstract-Conference.html
- Multi-SWE-bench — https://arxiv.org/abs/2504.02605 ; https://neurips.cc/virtual/2025/poster/121692
- SWE-PolyBench — https://arxiv.org/abs/2504.08703
- SWE-bench Multilingual — https://www.swebench.com/multilingual.html
- Aider polyglot benchmark — https://aider.chat/2024/12/21/polyglot.html ; leaderboard https://aider.chat/docs/leaderboards/
- Aider edit formats — https://aider.chat/docs/more/edit-formats.html ; unified diffs https://aider.chat/2023/12/21/unified-diffs.html
- Programming Language Confusion — https://arxiv.org/abs/2503.13620
- Reasoning or Reciting (counterfactual tasks) — https://arxiv.org/abs/2307.02477
- SPEAC — https://arxiv.org/abs/2406.03636
- LLMLift — https://arxiv.org/abs/2406.03003 ; https://arxiv.org/html/2406.03003
- DocPrompting — https://arxiv.org/abs/2207.05987
- Grammar Prompting — https://arxiv.org/abs/2305.19234
- MTOB — https://arxiv.org/abs/2309.16575
- Gemini 1.5 report — https://arxiv.org/abs/2403.05530
- Type-Constrained Code Generation — https://arxiv.org/abs/2504.09246 ; https://pldi25.sigplan.org/details/pldi-2025-papers/25/Type-Aware-Constraining-for-LLM-Code-Generation
- GitHub Octoverse 2025 — https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/
- GitHub blog, typed languages — https://github.blog/ai-and-ml/llms/why-ai-is-pushing-developers-toward-typed-languages
- Statically Contextualizing LLMs with Typed Holes — https://arxiv.org/abs/2409.00921 ; https://arxiv.org/html/2409.00921v1
- Live Functional Programming with Typed Holes (Hazelnut Live) — https://arxiv.org/abs/1805.00155
- Synchromesh — https://arxiv.org/abs/2201.11227
- SynCode — https://arxiv.org/abs/2403.01632
- XGrammar — https://arxiv.org/abs/2411.15100
- llguidance — https://github.com/guidance-ai/llguidance
- JSONSchemaBench — https://arxiv.org/abs/2501.10868 ; https://arxiv.org/html/2501.10868v3
- Grammar-Aligned Decoding — https://arxiv.org/abs/2405.21047
- Let Me Speak Freely? — https://arxiv.org/abs/2408.02442
- Monitor-Guided Decoding — https://arxiv.org/abs/2306.10763
- OpenAI GPT-5 custom tools / CFG — https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_new_params_and_tools
- OpenAI GPT-4.1 prompting guide (V4A diff) — https://developers.openai.com/cookbook/examples/gpt4-1_prompting_guide
- Claude structured outputs — https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- Claude text editor tool — https://platform.claude.com/docs/en/agents-and-tools/tool-use/text-editor-tool
- MoonBit — https://www.moonbitlang.com/ ; https://www.moonbitlang.com/blog/moonbit-ai
- Teaching LLMs to Self-Debug — https://arxiv.org/abs/2304.05128
- Is Self-Repair a Silver Bullet? — https://arxiv.org/abs/2306.09896
- RustAssistant (Fixing Rust Compilation Errors using LLMs) — https://arxiv.org/abs/2308.05177 ; https://arxiv.org/html/2308.05177
- rustc JSON diagnostics — https://doc.rust-lang.org/rustc/json.html
- SimPy / AI-oriented grammar — https://arxiv.org/abs/2404.16333
- The Hidden Cost of Readability — https://arxiv.org/abs/2508.13666
- Token efficiency by language (Alderson) — https://martinalderson.com/posts/which-programming-languages-are-most-token-efficient/
- How Does Naming Affect LLMs — https://arxiv.org/abs/2307.12488
- Diff-XYZ — https://arxiv.org/abs/2510.12487
- SWE-agent — https://arxiv.org/abs/2405.15793 ; https://arxiv.org/html/2405.15793v3
- Darwin Gödel Machine — https://arxiv.org/abs/2505.22954
- DafnyBench — https://arxiv.org/abs/2406.08467
- Clover — https://arxiv.org/abs/2310.17807
- Vericoding benchmark — https://arxiv.org/abs/2509.22908 ; https://arxiv.org/html/2509.22908v1
- Verina — https://arxiv.org/abs/2505.23135 ; https://iclr.cc/virtual/2026/poster/10011965
- AlgoVeri — https://arxiv.org/abs/2602.09464
- AutoVerus — https://arxiv.org/abs/2409.13082 ; https://arxiv.org/html/2409.13082v2 ; https://2025.splashcon.org/details/OOPSLA/200/AutoVerus-Automated-Proof-Generation-for-Rust-Code
- AlphaVerus — https://arxiv.org/abs/2412.06176 ; https://proceedings.mlr.press/v267/aggarwal25a.html
- Inductive Deductive Synthesis — https://arxiv.org/abs/2605.23109
- DeepSeek-Prover-V2 — https://arxiv.org/abs/2504.21801
- Kleppmann, AI and formal verification — https://martin.kleppmann.com/2025/12/08/ai-formal-verification.html
- Bugs in LLM-generated code (Tambon et al.) — https://arxiv.org/abs/2403.08937
- Characteristics of code generation errors (Wang et al., ICSE 2025) — https://arxiv.org/abs/2406.08731
- What's Wrong with Your Code (Dou et al.) — https://arxiv.org/abs/2407.06153
- Lost in Translation (code translation bugs) — https://arxiv.org/abs/2308.03109
- Package hallucinations — https://arxiv.org/abs/2406.10279
- Deprecated API usage — https://arxiv.org/abs/2406.09834
- EvalPlus — https://arxiv.org/abs/2305.01210
- llms.txt — https://llmstxt.org/
