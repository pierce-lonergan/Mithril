# R12 — Continual learning, model editing and living models

*Research dossier for the Mithril architecture phase. Written 2026-10-11. Scope: evaluate the seed
discussion's "living tissue" section (I1–I8) against the model-editing and continual-learning
literature through 2026, and derive the runtime/language primitives that are actually needed, with
Hearth as the acid test.*

*Method note: claims are tied to primary sources (arXiv abstracts or HTML, proceedings pages,
official docs) where I could fetch them. The shared web-search budget for this workflow ran out
partway through. After that I worked only from arXiv abstract pages I fetched directly and from the
local Hearth sources. Coverage of two areas is therefore thinner than I would like: knowledge
editing applied to MoE models specifically, and 2026 on-device self-updating products. Both are
listed under Open questions. Several key 2026 results are arXiv preprints, and I label them that
way. Labels used: **[inference]** marks my own reasoning; **unverified** marks things I could not
confirm.*

---

## Summary

- **Single-fact weight surgery works, and lifelong surgery degrades.** ROME, MEMIT, PMET and
  AlphaEdit reliably insert individual facts or small batches. Every independent large-scale study
  since 2024 finds that sequential parameter editing eventually damages general capability.
  Examples: collapse within a few hundred edits on WikiBigEdit, capability erosion tied to the
  dominant singular subspace, and AlphaEdit's null-space protection shown to be "bounded rather than
  unconditional". A May 2026 preprint finds a simple retrieval baseline beats every
  parameter-editing method it tested. Confidence: **high** that degradation is real; **medium** on
  exact thresholds, which vary by model, method and hyperparameters.
- **Measuring edit success alone is dangerous.** Edit success and locality can stay perfect while
  MMLU falls to chance or calibration silently breaks. Any acceptance gate must include capability,
  calibration and safety canaries, not just checks on the edit itself (**high**).
- **The approaches that scale add parameters instead of overwriting them.** Examples: side memories
  (GRACE, WISE), adapters (LoRA, O-LoRA), new experts with old ones frozen (Lifelong-MoE, MoE-LPR,
  BTX), sparse memory-slot updates, and retrieval. Sparse memory finetuning cut forgetting on
  NaturalQuestions from an 89% F1 drop (full finetuning) to 11% (**high**; single paper).
- **Adapter hot-swapping is mature engineering on GPU servers and in llama.cpp.** S-LoRA, Punica,
  vLLM's runtime load/unload and llama-server's `/lora-adapters` all do it. The hard parts are not
  the pointer swap. They are batching across different adapters, memory paging, and staying bound
  to the exact base version: Apple's adapters work only with one specific system model version
  (**high**).
- **"Models that update themselves" is demonstrated only in narrow forms.** One form is
  per-sequence fast weights: Titans' memory MLP, the delta-rule states of Gated DeltaNet and Kimi
  Delta Attention (KDA), and TTT-E2E. Another is per-task test-time training (ARC). The third is
  research-scale persistent self-editing (SEAL), whose own authors report catastrophic forgetting.
  Nothing I found shows persistent, unsupervised, every-token weight learning on consumer hardware
  that does not degrade (**medium-high**; search budget limited).
- **The seed's direction (I1–I4) is defensible, but its guarantees are fabricated.** No SMT solver
  can certify "bounded loss divergence" for an LLM edit; the DGM itself uses empirical evaluation
  precisely because proofs are impractical. Null-space projection does not "eliminate catastrophic
  forgetting". The machine-level mechanisms in I5 and I7 are wrong: `INVD` is ring-0 only and
  discards dirty cache lines, and weight updates are data writes, not code patches.
- **What the runtime actually needs** [inference, high confidence]: content-addressed versioned
  weights; typed overlays (full-slab replacement, low-rank delta, singular-value scale, side
  memory, added expert, memory-slot delta, KV-prefix artifact); copy-on-write at expert granularity;
  epoch commit at token boundaries with per-sequence version pinning; a mandatory signed provenance
  record per delta; an evaluation gate feeding a DGM-style archive of variants; and determinism
  stated as `logits = f(binary, ISA, version_root, inputs)`.
- **The real cost of an "atomic expert swap" is not the swap.** It is (a) staging bytes: about
  2.5 MB for a Q4 Qwen3-30B-A3B expert, about 9.4 MB in BF16; (b) KV-cache staleness for every
  layer above the edited one; (c) changed routing, which invalidates heat profiles and the
  prefetch model; and (d) for unmerged low-rank overlays, extra bytes on a memory-bound decode
  path. A rank-16 BF16 LoRA adds roughly 11% to each overlaid Q4 expert's bytes
  ([inference], computed below).
- **Hearth is unusually well placed.** Its `.hearth` expert directory already has one entry per
  expert, a dtype per expert, and an "aliased" flag. Its store already refcounts every
  (layer, expert) and has a token-boundary hook (`hx_store_tick`). Per-expert copy-on-write
  overlays are a natural extension; in-place mutation is not, because mirrors must stay
  byte-identical (INV-FMT, mirrors) [inference from local sources].

---

## Findings

### F1. Locate-then-edit methods: ROME, MEMIT, PMET, AlphaEdit

- **ROME** (Meng et al., NeurIPS 2022) uses causal interventions to show that mid-layer
  feed-forward modules mediate factual recall on subject tokens. It edits one association with a
  rank-one update to an FFN weight matrix
  ([arXiv 2202.05262](https://arxiv.org/abs/2202.05262)).
- **MEMIT** extends this to "thousands of associations" at once on GPT-J (6B) and GPT-NeoX (20B)
  ([arXiv 2210.07229](https://arxiv.org/abs/2210.07229)). WikiBigEdit cites the original paper as
  integrating up to 10K edits in a batch
  ([WikiBigEdit](https://arxiv.org/html/2503.05683v2)).
- **PMET** (AAAI 2024) argues that the hidden states used as FFN "values" also carry attention and
  residual signal. It optimizes both the attention (MHSA) and FFN hidden states but writes updates
  only to the FFN. The rationale is that attention acts as a general knowledge extractor that does
  not need to change. The reported gain on zsRE over the prior best is 0.4% on GPT-J
  ([arXiv 2308.08742](https://arxiv.org/abs/2308.08742);
  [AAAI](https://ojs.aaai.org/index.php/AAAI/article/view/29818)).
- **AlphaEdit** (ICLR 2025, Oral) projects the edit perturbation onto the null space of the
  "preserved knowledge" keys K0 before applying it. In the idealized case, outputs on preserved keys
  are provably unchanged. The authors call it one extra line of code and report an average 36.7%
  improvement for locate-then-edit methods on LLaMA3, GPT2-XL and GPT-J
  ([ICLR proceedings](https://proceedings.iclr.cc/paper_files/paper/2025/hash/29c8c615b3187ee995029284702d3f43-Abstract-Conference.html);
  [arXiv 2410.02355](https://arxiv.org/abs/2410.02355)). The mechanics matter for the seed's I6
  ([AlphaEdit HTML](https://arxiv.org/html/2410.02355)):
  - K0 is *estimated* from a sample of 100,000 Wikipedia (subject, relation, object) triples,
    following MEMIT. Only that sample is protected.
  - The projector P = ÛÛᵀ comes from an SVD of K0K0ᵀ. Eigenvalues are "rarely strictly zero", so
    the experiments drop eigenvectors with eigenvalues above 10⁻². The null space is therefore a
    thresholded approximation.
  - Sequential edits add a penalty on previously edited keys Kp. The derivation assumes WK0 = V0
    already holds.
  - The main sequential results go up to 2,000 edits (batch 100). General-capability tests on
    LLaMA3-8B go up to 3,000 edits.
- **The ROME collapse was partly an implementation artifact.** Two EMNLP 2024 papers trace ROME's
  single-edit collapse to inconsistent handling of prefixed and unprefixed keys. That inconsistency
  produces tiny denominators and huge updates, especially when the subject is the first token. The
  fix is to use prefixed keys consistently
  ([Yang et al., arXiv 2406.11263](https://arxiv.org/abs/2406.11263)). r-ROME reports stable
  "large scale sequential edits" ([Gupta et al., arXiv 2403.07175](https://arxiv.org/abs/2403.07175)).
  **Lesson for a runtime:** an editor is code, and its numerical edge cases (near-singular solves)
  need the same verification discipline as kernels [inference].
- **UltraEdit** (TMLR 2026) is training-free. It computes a one-step parameter shift from a hidden
  state and its gradient, and adds "lifelong normalization" of feature statistics. The authors
  self-report 7× faster editing than the prior state of the art, 4× less VRAM, editing a 7B model
  on a 24 GB GPU, and up to 2M edits on their UltraEditBench
  ([arXiv 2505.14679](https://arxiv.org/abs/2505.14679)). Not independently replicated in anything I
  found (**unverified** beyond the authors' claims).

### F2. Lifelong and sequential editing: the degradation literature

- **Few edits can break a model.** Yang et al. (Findings of ACL 2024) report that "even a single
  edit can trigger model collapse" on hard cases, and that in sequential editing nearly all methods
  they tested collapse after only a few edits. They propose perplexity as a cheap surrogate for
  downstream capability ([arXiv 2402.09656](https://arxiv.org/abs/2402.09656)).
- **WikiBigEdit** (ICML 2025): over 500K real Wikidata-derived QA pairs across eight timesteps
  ([arXiv 2503.05683](https://arxiv.org/abs/2503.05683); details from the
  [HTML](https://arxiv.org/html/2503.05683v2)):
  - ROME, R-ROME and MEMIT "rapidly degrade within the first few hundred updates".
  - WISE avoids collapse, but its accuracy declines within about 10K updates toward pre-update
    levels.
  - Retrieval augmentation is strongest: 78.64% on rephrased questions. It is weak on multi-hop
    questions and older edits.
  - Continual LoRA with interpolation-based merging overtakes specialized editors after about 100K
    edits.
  - Conclusion: at a fixed inference budget, specialized editors are matched or beaten by simple
    continual finetuning, especially with merging. (**high** for the qualitative ranking.)
- **The mechanism is erosion of dominant singular directions.** REVIVE (ACL 2026 main; arXiv
  preprint) links general ability to the dominant singular subspace of pretrained weights. Repeated
  edits progressively disrupt that subspace. REVIVE expresses updates in the original weights'
  spectral basis and filters out components that touch the protected region, and reports
  stabilization up to 20,000 edits ([arXiv 2601.11042](https://arxiv.org/abs/2601.11042)).
- **AlphaEdit's guarantee does not survive scale or architecture change.** A June 2026
  reproducibility study confirms AlphaEdit's original numbers (with a fluency/consistency
  discrepancy), with these qualifications ([arXiv 2606.26783](https://arxiv.org/abs/2606.26783)):
  - The advantage does not carry over uniformly to Llama3.2, Qwen2.5, Phi3 (fused qkv and
    gate_up projections) or Gemma2 (GeGLU), because these violate locate-then-edit assumptions.
  - Performance degrades at much higher edit counts. The study calls the null-space protection
    "bounded rather than unconditional".
  - Large-scale editing degrades BoolQ, HellaSwag and XSTest refusal behaviour.
- **The theory argues against parameter editing as a fact store.** Ren et al. (May 2026 preprint)
  argue that localized edits propagate along fragile representation directions and cause global
  interference. Empirically, parameter-based editing "consistently" damaged core capabilities, and a
  simple retrieval baseline beat every parameter-editing method they tested
  ([arXiv 2606.00570](https://arxiv.org/abs/2606.00570)). (**medium**: a preprint, but consistent
  with WikiBigEdit.)
- **Edit metrics miss what breaks.** Anand (Aug 2026 preprint): after 1,000 sequential edits, three
  of five model/method pairings fell to chance MMLU under published hyperparameters, while edit
  success stayed at 1.00 and locality "looked clean". Even a conservative LoRA arm with unchanged
  MMLU degraded the model's arbitration between memory and retrieved evidence: AURC for selective
  prediction rose by 0.107, versus 0.005 for a norm-matched random perturbation
  ([arXiv 2609.29587](https://arxiv.org/abs/2609.29587)). Code is "available on request" only
  (**medium**).

### F3. Memory-based editors and retrieval

- **GRACE** (NeurIPS 2023) writes edits into "a discrete, local codebook of edits without altering
  model weights" in the model's latent space. It was the first method to support thousands of
  sequential edits from streaming errors on T5, BERT and GPT models
  ([arXiv 2211.11031](https://arxiv.org/abs/2211.11031)). WISE's authors characterize this kind of
  working memory as having good reliability and locality but poor generalization
  ([WISE](https://arxiv.org/abs/2405.14768)).
- **WISE** (NeurIPS 2024) frames the problem as an "impossible triangle" of reliability,
  generalization and locality. Its design
  ([proceedings](https://proceedings.neurips.cc/paper_files/paper/2024/hash/60960ad78868fce5c165295fbd895060-Abstract.html);
  [arXiv 2405.14768](https://arxiv.org/abs/2405.14768)):
  - The pretrained FFN memory is kept frozen; edits go into a separate side memory.
  - A learned router chooses which memory a query uses.
  - Edit sets are sharded into orthogonal subspaces and then merged.

  WikiBigEdit's at-scale results temper the claims (F2).
- **Cartridges** (2025) train a small KV cache per corpus offline using "self-study"
  (synthetic conversations plus context distillation). They match in-context learning with 38.6×
  less memory and 26.4× higher throughput, and they compose at inference without retraining
  ([arXiv 2506.06266](https://arxiv.org/abs/2506.06266)). This is a third kind of "memory artifact",
  alongside weights and retrieval documents, that a runtime may need to version [inference].
- **Retrieval is the strongest fact-update path in both large 2025–2026 comparisons**
  ([WikiBigEdit](https://arxiv.org/html/2503.05683v2); [Ren et al.](https://arxiv.org/abs/2606.00570)).

### F4. Adapters and hot-swapping

- **S-LoRA** serves "thousands" of LoRA adapters. Adapters live in host memory and are paged to
  the GPU on demand through a unified pool shared with the KV cache. Custom kernels handle
  heterogeneous batches. It reports up to 4× throughput versus vLLM with naive LoRA support and
  HF PEFT ([arXiv 2311.03285](https://arxiv.org/abs/2311.03285); venue not verified in this
  session).
- **Punica** (MLSys 2024) keeps one copy of the base model and batches per-adapter LoRA math with
  the SGMV kernel. It reports 12× throughput over state-of-the-art serving systems at about 2 ms of
  added latency per token
  ([MLSys 2024](https://proceedings.mlsys.org/paper_files/paper/2024/hash/054de805fcceb78a201f5e9d53c85908-Abstract-Conference.html)).
  These are GPU numbers; neither system targets CPU decode.
- **vLLM** supports runtime `/v1/load_lora_adapter` and `/v1/unload_lora_adapter` behind a
  `VLLM_ALLOW_RUNTIME_LORA_UPDATING` flag. It also supports `load_inplace` replacement under the
  same name, which vLLM links to asynchronous RL. The docs warn that dynamic LoRA configuration
  carries security risks and belongs only in isolated, trusted environments
  ([vLLM docs](https://docs.vllm.ai/en/latest/features/lora.html)).
- **llama.cpp's llama-server** loads adapters at startup and can start them unapplied
  (`--lora-init-without-apply`). It sets global scales through `POST /lora-adapters` and accepts
  per-request `lora` scale lists. The README notes that requests with different LoRA configurations
  are not batched together
  ([llama.cpp server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)).
  This is the closest existing CPU analogue to what Hearth would need.
- **Capacity facts for deciding what an overlay can hold:**
  - LoRA "learns less and forgets less" than full finetuning
    ([Biderman et al., TMLR 2024](https://arxiv.org/abs/2405.09673)). Full finetuning learns
    perturbations of 10–100× higher rank than typical LoRA.
  - LoRA matches full finetuning when applied to all layers, especially the MLP and MoE layers, and
    when the dataset fits within adapter capacity. In RL it matches even at rank 1. Per
    forward-backward pass it uses a little over two-thirds of full finetuning's FLOPs
    ([Thinking Machines, "LoRA Without Regret"](https://thinkingmachines.ai/blog/lora/)).
- **Smaller deltas than LoRA:**
  - Transformer² (ICLR 2025) adapts only the singular components of weight matrices. Task "expert
    vectors" are trained with RL and mixed in a two-pass inference
    ([arXiv 2501.06252](https://arxiv.org/abs/2501.06252)).
  - Text-to-LoRA (ICML 2025) generates a LoRA from a task description in one hypernetwork forward
    pass ([arXiv 2506.06105](https://arxiv.org/abs/2506.06105)).
- **Deployed reality:** Apple's Foundation Models adapter toolkit trains LoRA adapters off-device
  (on a Mac or Linux GPUs). Each adapter is about 160 MB, delivered through Background Assets,
  and "works with a single specific system model version". Developers must retrain for each base
  version
  ([Apple developer docs](https://developer.apple.com/apple-intelligence/foundation-models-adapter/)).
  Overlays are not portable across base weights. A provenance system must bind each delta to the
  hash of its base [inference, **high**].

### F5. Growing MoE: upcycling, branching, expert addition, expert-local tuning

- **Sparse upcycling** (ICLR 2023) initializes an MoE from a dense checkpoint, with FFN copies as
  experts and a fresh router. It beats dense continuation using about 50% of the original
  pretraining cost on T5 and ViT
  ([arXiv 2212.05055](https://arxiv.org/abs/2212.05055)).
- **Branch-Train-MiX** (Meta, 2024) works in three steps:
  1. Branch copies of a seed LLM.
  2. Train each copy separately and in parallel on its own domain.
  3. Merge the copies' FFNs as experts in MoE layers, average the remaining weights, and finetune
     the router.

  It generalizes Branch-Train-Merge and sparse upcycling
  ([arXiv 2403.07816](https://arxiv.org/abs/2403.07816)). This is "bifurcation into child experts"
  done offline with a finetuning stage, not online.
- **Adding experts after pretraining:**
  - Lifelong-MoE (ICML 2023) adds experts with regularized pretraining as the distribution shifts.
    Compute stays constant because only a few experts are added
    ([arXiv 2305.12281](https://arxiv.org/abs/2305.12281)).
  - MoE-LPR first upcycles and freezes the original parameters, then trains new experts on new
    languages. A review stage with under 1% replay and language-prior routing recovers the
    original languages ([arXiv 2408.11396](https://arxiv.org/abs/2408.11396)).
  - LayerMoE (ACL 2025) allocates new experts per layer by cross-lingual representation similarity
    ([arXiv 2505.22582](https://arxiv.org/abs/2505.22582)).
  - LLaVA-CMoE uses probe experts to decide where to add experts
    ([arXiv 2503.21227](https://arxiv.org/abs/2503.21227)).
- **Router drift is the failure mode of growth.** Even with old experts frozen, a router may send
  old inputs to newly added experts. StaR-MoE (May 2026, vision class-incremental learning) adds
  routing alignment to keep old-class routing close to historical distributions
  ([arXiv 2605.17571](https://arxiv.org/abs/2605.17571)). For Hearth, router drift also shifts cache
  heat and prefetch accuracy [inference].
- **ESFT** (DeepSeek, EMNLP 2024): task routing in fine-grained MoE is highly concentrated, so
  tuning only the most relevant experts, with everything else frozen, matches or beats full
  finetuning ([arXiv 2407.01906](https://arxiv.org/abs/2407.01906);
  [repo](https://github.com/deepseek-ai/ESFT)). This is the strongest published evidence that
  **per-expert overlays are a sound unit of adaptation** for MoE.
- **Retrieval over parameters:**
  - PEER uses product-key retrieval to select among more than a million tiny experts
    ([arXiv 2407.04153](https://arxiv.org/abs/2407.04153)).
  - Memory layers scale to 128B memory parameters and beat compute- and parameter-matched MoE,
    especially on factual tasks ([arXiv 2412.09764](https://arxiv.org/abs/2412.09764)).
  - Sparse memory finetuning updates only the memory slots that new knowledge activates heavily,
    relative to their pretraining usage. The NaturalQuestions F1 drop was 11%, versus 71% for LoRA
    and 89% for full finetuning, at similar new-knowledge acquisition
    ([arXiv 2510.15103](https://arxiv.org/abs/2510.15103)).

  These are the closest demonstrated relatives of the seed's I2 ("routing space as a metric index;
  insert novel concepts into unallocated capacity").

### F6. Continual pre-training

- LR re-warming plus re-decaying plus replay of earlier data matches full retraining on all data
  (final loss and benchmark averages)
  ([Ibrahim et al., TMLR 2024, arXiv 2403.08763](https://arxiv.org/abs/2403.08763)).
- TiC-LM (Apple, 2025) builds a benchmark from 114 Common Crawl dumps. Autoregressive
  meta-schedules with fixed-ratio replay reach held-out loss comparable to retraining from scratch
  with about 2.6× less compute. Replay is essential for generic web data and matters less for
  specific domains ([arXiv 2504.02107](https://arxiv.org/abs/2504.02107)).
- **Implication:** model-wide refresh is a periodic *training job* with replay data, not something
  that happens per token. The runtime's job is to version and gate its output, not to perform it
  inline [inference].

### F7. Forgetting mitigation

- **EWC** "remembers old tasks by selectively slowing down learning on the weights important for
  those tasks" ([arXiv 1612.00796](https://arxiv.org/abs/1612.00796)). The standard formulation is
  a Fisher-weighted quadratic penalty. I verified only the abstract's wording. EWC needs
  per-parameter importance statistics, which costs as much storage as the weights [inference].
- **O-LoRA** (EMNLP 2023 Findings) learns each task in its own low-rank subspace, kept orthogonal
  to earlier ones, and "requires no user data storage for replay"
  ([arXiv 2310.14152](https://arxiv.org/abs/2310.14152)).
- **Intruder dimensions:** LoRA creates new high-ranking singular vectors that full finetuning
  does not. Its forgetting is localized to those vectors, they accumulate under sequential
  finetuning, and scaling them down recovers pretraining-distribution modelling
  ([arXiv 2410.21228](https://arxiv.org/abs/2410.21228)). Together with REVIVE (F2), this makes
  spectral diagnostics of a delta a cheap, data-free gate signal [inference].
- **RL's Razor** (2025): forgetting tracks the KL divergence between the finetuned and base policy
  on the new task. On-policy RL is implicitly biased toward low-KL solutions, which is why it
  forgets less than SFT ([arXiv 2509.04259](https://arxiv.org/abs/2509.04259)). This turns "KL to
  parent on a reference prompt set" into a principled gate metric [inference].
- **Sparse slot updates** (F5) and **freezing plus growth** (F5) are the most effective reported
  mitigations. Both are structural (where updates go), not penalties [inference].

### F8. Test-time training, neural memory and self-adapting models

- **Per-task test-time training (TTT):** temporary per-instance weight updates gave up to 6×
  accuracy on ARC. An 8B model reached 53.0% on the public validation set, and 61.9% when ensembled
  with program synthesis
  ([Akyürek et al., arXiv 2411.07279](https://arxiv.org/abs/2411.07279)). The updates are discarded
  after the task.
- **TTT-E2E** (Dec 2025) treats long context as continual learning. A sliding-window Transformer
  keeps training on its context by next-token prediction, with a meta-learned initialization.
  The 3B model scales with context like full attention and is 2.7× faster than full attention at
  128K ([arXiv 2512.23675](https://arxiv.org/abs/2512.23675)).
- **Titans** (NeurIPS 2025) adds a neural long-term memory whose parameters are updated per token
  at inference ([arXiv 2501.00663](https://arxiv.org/abs/2501.00663);
  [HTML](https://arxiv.org/html/2501.00663)):
  - The loss is an associative recall loss ‖M(k) − v‖², and its gradient serves as a "surprise"
    signal.
  - Data-dependent momentum carries surprise forward, and an α gate decays old content.
  - Persistent parameters stay fixed.
  - Training is parallelized by chunking plus associative scans.
  - The authors report contexts beyond 2M tokens.
- **Nested Learning / HOPE** (Dec 2025) recasts optimizers and models as nested optimization
  problems and proposes a self-modifying sequence model plus a "continuum memory system"
  ([arXiv 2512.24695](https://arxiv.org/abs/2512.24695)). Promising, but early.
- **Fast weights already exist in production-class architectures.** Kimi Linear's KDA extends
  Gated DeltaNet's delta rule with finer gating. It ships in a 48B-total, 3B-active hybrid with MLA,
  cuts KV cache by up to 75%, and reports up to 6× decode throughput at 1M context
  ([arXiv 2510.26692](https://arxiv.org/abs/2510.26692)). Every token, the recurrent state of such
  layers is updated by a learned delta rule. This is "learning during inference" in a disciplined
  form: per-sequence, bounded and architected for [inference].
- **SEAL** (MIT, 2025) has the model generate "self-edits" (synthetic finetuning data and update
  directives). These are applied by SFT as persistent weight updates, and an RL outer loop rewards
  self-edits that improve the updated model
  ([arXiv 2506.10943](https://arxiv.org/abs/2506.10943)). MIT's write-up says repeated adaptation
  slowly degrades earlier tasks, i.e. catastrophic forgetting, which the authors leave to future
  work ([MIT EECS](https://www.eecs.mit.edu/teaching-large-language-models-how-to-absorb-new-knowledge)).
  The outer loop must evaluate each candidate update, which makes it inherently expensive
  [inference].
- **Local updating is demonstrated for adapters on quantized bases.** QLoRA backpropagates through
  a frozen 4-bit model into LoRA adapters ([arXiv 2305.14314](https://arxiv.org/abs/2305.14314)).
  UltraEdit claims 7B editing on a 24 GB consumer GPU (F1). I found no verified 2025–2026 report of
  a deployed model that persistently learns from every interaction on consumer hardware without a
  gate. Apple trains adapters off-device (F4). (**unverified** that none exists; search budget
  exhausted.)

### F9. Systems facts behind "hot patching"

- **Atomicity is cheap; the instruction is not a "single cycle".** `CMPXCHG16B` needs a 16-byte
  aligned operand, a CPUID feature check, and `LOCK` for atomicity. With `LOCK` it always issues a
  locked write cycle, even when the comparison fails
  ([felixcloutier: CMPXCHG16B](https://www.felixcloutier.com/x86/cmpxchg8b:cmpxchg16b)). Locked
  read-modify-writes are multi-cycle operations (exact Zen 5 latency **unverified** in this
  session). Publishing a new 8-byte pointer needs no CAS at all if there is a single writer: an
  aligned store with release ordering suffices. What does need design is reclamation, meaning when
  the old version can be freed, which is an epoch/RCU problem [inference].
- **`INVD` is the wrong tool.** It is privileged (CPL 0) and discards cache contents *without
  writeback*, so dirty data is lost. The ISA reference recommends `WBINVD` instead unless discarding
  is intended ([felixcloutier: INVD](https://www.felixcloutier.com/x86/invd)).
- **Code coherence is a platform rule, not a cache-flush exercise.**
  - On x86, the hardware keeps instruction fetch coherent with same-core stores. Cross-modifying
    code needs a serializing step on the executing core. This is from the Intel SDM Vol. 3A
    section on self- and cross-modifying code, from prior knowledge; not fetched this session,
    **medium-high** confidence.
  - GCC's `__builtin___clear_cache` "has no effect" on targets that need no instruction-cache
    flush ([GCC docs](https://gcc.gnu.org/onlinedocs/gcc/Other-Builtins.html)).
  - Apple silicon requires `MAP_JIT`, per-thread W^X toggling and explicit icache invalidation
    ([Apple porting guide](https://developer.apple.com/documentation/apple-silicon/porting-just-in-time-compilers-to-apple-silicon);
    my tool could not retrieve the page body, so these specifics come from prior knowledge,
    **medium-high**). This matters because Hearth's CI includes macOS arm64.
- **Determinism is a property of the whole serving stack.** Thinking Machines showed that LLM
  inference nondeterminism comes mainly from batch-size-dependent kernels, not from atomics
  ([blog](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/)):
  - With batch-invariant kernels, 1,000 temperature-0 completions became identical, down from 80
    unique outputs.
  - The cost was 26 s → 42 s on their Qwen3-8B test.
  - It enabled truly on-policy RL with zero sampler/trainer KL.

  Hearth already guarantees batch invariance (INV-DET-2, local `governance/INVARIANTS.md`). Under
  weight updates, the remaining source of irreproducibility is *which weights were live at each
  token*.
- **Provenance tooling exists at file granularity.**
  - Sigstore model-transparency signs a manifest of per-file or per-shard digests as an in-toto
    statement in a DSSE envelope. It supports Sigstore OIDC, keys, certificates and PKCS#11
    ([sigstore/model-transparency](https://github.com/sigstore/model-transparency)).
  - Git-Theta tracks parameter-level changes, merges and meaningful diffs inside git
    ([arXiv 2306.04529](https://arxiv.org/abs/2306.04529)).
  - Neither works at expert granularity or records *how* a delta was produced (method,
    hyperparameters, data, gate results). That is the gap [inference].
- **DGM is the archive template, with honest costs.** The Darwin Gödel Machine changes agent
  *code* (not model weights) and validates every change empirically on coding benchmarks, because
  proving changes beneficial is impractical
  ([arXiv 2505.22954](https://arxiv.org/abs/2505.22954); [HTML](https://arxiv.org/html/2505.22954v3)):
  - It keeps an archive of all compiling, code-editing agents.
  - Parent selection is proportional to score and inverse to the number of children; every agent
    keeps a non-zero chance.
  - SWE-bench went from 20.0% to 50.0%.
  - One SWE-bench run took about 2 weeks and an estimated US$22,000.

  An archive of *model variants* inherits the same structure. Each candidate must be cheap to
  evaluate, or the loop is unaffordable locally [inference].

### F10. Demonstrated vs speculative

| Capability | Status | Evidence |
|---|---|---|
| Insert one or a few facts by closed-form weight edit | **Demonstrated** | [ROME](https://arxiv.org/abs/2202.05262), [MEMIT](https://arxiv.org/abs/2210.07229), [AlphaEdit](https://arxiv.org/abs/2410.02355) |
| Thousands to hundreds of thousands of sequential weight edits without capability loss | **Not demonstrated** (contested claims) | Degrades: [WikiBigEdit](https://arxiv.org/html/2503.05683v2), [REVIVE](https://arxiv.org/abs/2601.11042), [repro](https://arxiv.org/abs/2606.26783), [Ren](https://arxiv.org/abs/2606.00570). Claims scale: [UltraEdit](https://arxiv.org/abs/2505.14679) |
| Side-memory or codebook edits with locality | **Demonstrated**, bounded | [GRACE](https://arxiv.org/abs/2211.11031), [WISE](https://arxiv.org/abs/2405.14768) |
| Many adapters served concurrently, hot-loaded | **Demonstrated** (GPU servers, llama.cpp) | [S-LoRA](https://arxiv.org/abs/2311.03285), [Punica](https://proceedings.mlsys.org/paper_files/paper/2024/hash/054de805fcceb78a201f5e9d53c85908-Abstract-Conference.html), [vLLM](https://docs.vllm.ai/en/latest/features/lora.html), [llama.cpp](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) |
| Expert-local finetuning in MoE | **Demonstrated** | [ESFT](https://arxiv.org/abs/2407.01906) |
| Adding experts post-hoc with old ones frozen | **Demonstrated** (offline training) | [Lifelong-MoE](https://arxiv.org/abs/2305.12281), [MoE-LPR](https://arxiv.org/abs/2408.11396), [BTX](https://arxiv.org/abs/2403.07816) |
| Automatic online expert birth triggered by router entropy | **Speculative**: no source found | (probe-expert placement exists: [LLaVA-CMoE](https://arxiv.org/abs/2503.21227)) |
| Low-forgetting continual knowledge via sparse slots | **Demonstrated** (one paper) | [Sparse memory FT](https://arxiv.org/abs/2510.15103) |
| Per-sequence learning at inference (fast weights, TTT) | **Demonstrated** (architected for) | [Titans](https://arxiv.org/abs/2501.00663), [KDA](https://arxiv.org/abs/2510.26692), [TTT-E2E](https://arxiv.org/abs/2512.23675) |
| Persistent self-directed weight updates | **Research prototype**, forgets | [SEAL](https://arxiv.org/abs/2506.10943) |
| Formal (SMT) guarantee of bounded loss change for an LLM edit | **Speculative, likely infeasible** | DGM rejects proof-based gating: [DGM](https://arxiv.org/abs/2505.22954) |
| "Eliminating catastrophic forgetting" by projection | **False as stated** | [AlphaEdit HTML](https://arxiv.org/html/2410.02355), [repro](https://arxiv.org/abs/2606.26783) |

---

## Implications for Mithril

The language should not make "living models" magic. It should make **every weight change an
explicit, typed, provenance-carrying, reversible value**, so that agents can explore aggressively
(the DGM spirit) without ever losing the ability to reproduce, compare or roll back. The
specification below is [inference] grounded in F1–F9.

### M1. Content-addressed, immutable weight versions

- Each tensor and each routed expert slab has a content hash. A **version** is a Merkle root over
  (base directory hashes, ordered overlay stack). Weights are immutable values: "updating" creates a
  new version and never mutates a live one.
- Rationale:
  - Apple adapters bind to exactly one base version
    ([Apple](https://developer.apple.com/apple-intelligence/foundation-models-adapter/)).
  - Sequential edits compound, so order matters ([AlphaEdit](https://arxiv.org/html/2410.02355)
    conditions each edit on prior keys Kp).
  - Signing tools already work on digest manifests
    ([model-transparency](https://github.com/sigstore/model-transparency)).
- Mithril type sketch: `Weights<V>`, where `V` is a version token. Functions that read weights are
  parametric in `V`. Mixing tensors from two versions in one forward pass is a type error unless
  explicitly composed.

### M2. Typed overlays (the only legal way to change weights)

Overlay kinds, each with defined forward semantics, cost model and gate requirements:

| Kind | Literature | Forward cost | Storage |
|---|---|---|---|
| `SlabReplace(layer, expert)` | ESFT, ROME/MEMIT/AlphaEdit applied to an expert's matrices | 0 extra per token | full slab |
| `LowRank(target, A, B, scale)` (unmerged) | LoRA, O-LoRA, WISE-like side memory | +r·(d_in+d_out) MACs and bytes | small |
| `SpectralScale(target, z)` | Transformer² | ≈0 if pre-folded; else one SVD-basis transform | tiny |
| `AddExpert(layer, slab, router_row)` | Lifelong-MoE, MoE-LPR, BTX | changes routing | full slab + router row |
| `SlotDelta(memory_layer, slots)` | Sparse memory FT, PEER | 0 extra | sparse |
| `Codebook(layer, keys, values, radius)` | GRACE | lookup per token | small |
| `KVPrefix(artifact)` | Cartridges | attention over prefix | small–medium |
| `Retrieval(store)` (not a weight change) | WikiBigEdit RAG, Ren et al. | retrieval + context | external |

The compiler and runtime should treat `Retrieval` as the **default path for facts**, and weight
overlays as the path for skills, styles and domains. This follows the 2025–2026 evidence that
retrieval beats parameter editing for fact updates
([WikiBigEdit](https://arxiv.org/html/2503.05683v2); [Ren](https://arxiv.org/abs/2606.00570)).

### M3. Copy-on-write at expert (or tensor) granularity

An overlay version shares every unmodified slab with its parent. Caches key on *physical slab
hash*, not on (layer, expert), so two versions that share 99% of their experts share 99% of their
DRAM residency. Merging an unmerged overlay into a slab ("bake") is an explicit operation that
yields a new slab hash. If the base is quantized, baking also requires requantization. The new
weights are therefore not bit-identical to "base + delta", and the gate must re-run.

### M4. Epoch commit, per-sequence version pinning and the real swap cost

- `commit(V')` publishes a new version pointer. It takes effect at the next **token boundary**
  (epoch). Readers acquire versions through epoch-protected references, and old versions are
  reclaimed when no sequence holds them (RCU-style). No `CMPXCHG16B` and no self-modifying code are
  needed (F9).
- **A sequence is pinned to the version it started with by default.** Migrating a live sequence is
  explicit and declares a KV policy, because KV entries at every layer above the first changed
  layer were computed with the old weights:
  - `Recompute(from_layer)`: exact, at the cost of re-prefilling the context over the affected
    layers.
  - `AcceptStale`: fast, but flagged as non-reproducible against a fresh run.
  - `Restart`.
- **Cost model the runtime must expose.** Worked example: Qwen3-30B-A3B, with D = 2048, F = 768, 48
  layers, 128 experts, top-8
  ([config](https://huggingface.co/Qwen/Qwen3-30B-A3B/blob/main/config.json)). All figures are
  [inference], computed with `.hearth` FORMAT.md row sizes:
  - One expert has 3·2048·768 = 4,718,592 parameters, so a Q4 slab is 2,506,752 B (≈2.4 MiB), a
    Q8 slab 4,866,048 B, and a BF16 slab 9,437,184 B.
  - Staging one replacement slab at an assumed 5–7 GB/s effective NVMe rate takes ≈0.36–0.5 ms
    (Q4) or ≈1.3–1.9 ms (BF16). A version that replaces *all* Q4 experts (≈15.4 GB) takes
    ≈2–3 s to stage. The pointer publish itself is nanoseconds.
  - Unmerged rank-16 LoRA on all three expert matrices adds 135,168 parameters per expert: +2.9%
    MACs and, in BF16, about 270 KB (+10.8% bytes) per overlaid Q4 expert. If every expert were
    overlaid, decode expert traffic would rise by about 11% (≈104 MB per token on top of ≈963 MB),
    and memory-bound decode would slow roughly in proportion. ESFT-style overlays on a small subset
    of experts cost proportionally less.
  - Mid-sequence migration with `Recompute` costs about one prefill of the context. At Hearth's
    measured 38 tok/s BF16 prefill (brief), a 4K-token context takes on the order of 100 s, so
    pinning is the right default.

### M5. Provenance as a mandatory field

The compiler refuses to construct an overlay without a provenance record:

- parent version root and base hash;
- overlay kind and method (e.g. `AlphaEdit`, `ESFT`, `LoRA`), with method code hash and
  hyperparameters;
- data reference and hash (or "synthetic, generated by version X with prompt hash Y", as in a
  SEAL-style self-edit);
- producing agent identity;
- gate results (M6);
- signature (DSSE/in-toto, compatible with
  [model-transparency](https://github.com/sigstore/model-transparency)).

Rationale:
- Editors have implementation-level failure modes ([Yang et al.](https://arxiv.org/abs/2406.11263)).
- Results are hyperparameter-idiosyncratic ([Anand](https://arxiv.org/abs/2609.29587)).
- Dynamic adapter loading is a security risk ([vLLM](https://docs.vllm.ai/en/latest/features/lora.html)).

Overlays are untrusted input. They pass the same format validation as base files (Hearth's
INV-FMT/INV-SAFE).

### M6. Evaluation gates and a DGM-style variant archive

- A version becomes *committable* only after passing a gate whose metrics are declared in code:
  1. Edit efficacy and generalization (paraphrases).
  2. Locality.
  3. **Capability canaries.** Perplexity on a held-out reference set is a cheap surrogate
     ([Butterfly](https://arxiv.org/abs/2402.09656)). KL-to-parent on a fixed prompt set tracks
     forgetting ([RL's Razor](https://arxiv.org/abs/2509.04259)). Add a small MMLU-style probe.
  4. **Calibration and evidence arbitration**, which degrade even when MMLU does not
     ([Anand](https://arxiv.org/abs/2609.29587)).
  5. **Safety refusal** ([AlphaEdit repro](https://arxiv.org/abs/2606.26783)).
  6. **Spectral checks** on the delta: energy in the parent's dominant singular subspace
     ([REVIVE](https://arxiv.org/abs/2601.11042)) and intruder dimensions
     ([Shuttleworth](https://arxiv.org/abs/2410.21228)). These are data-free and cheap.
  7. **For MoE, routing drift and cache impact.** Measure the change in the routing distribution on
     a reference trace ([StaR-MoE](https://arxiv.org/abs/2605.17571)) and the measured hit-rate
     change. The latter is a Hearth-specific speed gate.
- Gates are **statistical** (thresholds plus confidence intervals over fixed seeds), never "proofs".
  Every accepted or rejected variant goes into an append-only archive with lineage. Parent selection
  can follow DGM: proportional to score and inverse to child count
  ([DGM HTML](https://arxiv.org/html/2505.22954v3)). Rollback is a pointer move.
- Guard against gate gaming: the gate set is maintainer-owned and hash-locked, mirroring Hearth's
  INV-VERIFY golden tests, so a self-improving agent cannot weaken its own acceptance criteria
  [inference].

### M7. Determinism under updates

Restate Hearth's INV-DET family as `logits = f(binary, ISA, version_root, inputs, kv_policy)`. Each
generated token logs the version root it was computed with. Unmerged overlay kernels follow the
same canonical floating-point order as base kernels, so scalar, AVX2 and AVX-512 stay bit-identical
with overlays active. Batches mixing different versions are either computed per-version (as
llama.cpp does for differing LoRA configs) or computed with kernels proven batch-invariant.

### M8. Training as an effect, and what not to build

- `infer` and `train` are distinct effects. A function with the `train` effect can only *produce*
  overlays (never mutate `Weights<V>`) and must declare its compute and byte budget. On Hearth-class
  hardware, a backward pass through streamed experts at least re-reads the touched slabs, so
  per-token learning would multiply memory traffic [inference]. Inline learning should be limited to
  architected fast-weight state (KDA/Titans-style, per sequence). Persistent learning should be a
  background job whose output goes through M6.
- Do **not** build:
  - SMT-certified loss bounds (I4);
  - compile-time "invariant subspace" guarantees claimed to eliminate forgetting (I6);
  - CMPXCHG16B "single-cycle" swaps (I5);
  - INVD/CLFLUSH self-modifying code for weight updates (I7).

  A subspace constraint *is* worth offering, as a **runtime-checked contract** with a measured
  residual: `preserve(K0_sample, eps)` reports ‖ΔK0‖ / ‖WK0‖ on the protected sample. It can never
  be a type-level promise about unseen inputs.
- JIT code specialization, which is a separate concern from weights, should use standard JIT
  practice: fresh pages, W^X, platform icache rules, and a function-pointer publish at an epoch
  boundary.

---

## Implications for Hearth

All points are [inference] from local sources (`docs/FORMAT.md`, `engine/src/hx_store.h`,
`governance/INVARIANTS.md`) plus the findings above.

1. **The container already speaks the overlay language.**
   - The `.hearth` expert directory has one 32-byte entry per (layer, expert) with its own offset,
     size and dtype.
   - Experts may have different dtypes ("per-expert mixed precision").
   - Flag bit 0 lets several entries alias one physical slab.

   A natural `.hearth-overlay` (FORMAT version 2) would contain: a header with the base file's
   content hash, a sparse list of replaced (layer, expert) entries pointing to new slabs (any
   dtype; a BF16 overlay over a Q4 base is legal), optional LoRA factor tensors, optional appended
   experts with router rows, and a provenance blob. The base file is never modified. That
   requirement is already implied: mirrors must stay byte-identical copies, and model files must
   live in the data directory (INV-DATA).
2. **The store needs one indirection.** Today `slot_of[layer*E + e]` indexes slots directly. With
   overlays, resolve `(version, layer, expert) → physical slab id` first, and key slots, heat and
   pins on physical ids. Shared slabs then stay resident across versions (copy-on-write
   residency), and two concurrent sequences on different versions share everything except their
   deltas.
3. **The commit point exists.** `hx_store_acquire`/`release` refcount every expert use, and
   `hx_store_tick` marks token boundaries. Publishing a new directory pointer inside `tick`, when
   the compute thread holds no expert references, gives an atomic between-token swap with zero
   waiting. Staging uses the existing prefetch queue: before commit, issue prefetches for the
   overlay's slabs so the first post-commit token does not stall on demand reads.
4. **Invariants extend cleanly.**
   - INV-DET-1 becomes "bit-identical for a fixed (binary, ISA, version root)".
   - INV-LOSSLESS-DEFAULT means overlays are opt-in and the default version is the base.
   - INV-HONEST means every overlay's quality impact and decode cost are reported as measured or
     simulated, using the gate in M6.
   - Golden tests should include "base plus empty overlay is bit-identical to base" and "overlay A
     then B equals the composed overlay", for overlay kinds where composition is defined.
5. **Routing traces make MoE-specific gates cheap.** Hearth already records routing traces and has
   a cache simulator. An edit's effect on routing (drift), hit rate and predicted tok/s can be
   simulated *before* commit, which is a gate no GPU-server system offers. ESFT's finding that task
   routing is concentrated ([ESFT](https://arxiv.org/abs/2407.01906)) means Hearth's per-expert heat
   data can choose which experts to overlay for a task.
6. **Local adaptation that is plausible on the 9950X.** ESFT-style tuning of a few experts, or LoRA
   on a frozen Q4 base (QLoRA principle, [arXiv 2305.14314](https://arxiv.org/abs/2305.14314)), runs
   as a background job that writes an overlay file. Full-model continual pretraining or per-token
   persistent learning is not plausible: backward passes re-read streamed slabs, and optimizer state
   would not fit beside a 61 GB BF16 model in 64 GB. Unmerged LoRA costs about +11% expert bytes per
   overlaid expert (M4), which is a measurable decode-speed penalty. For hot overlays, baking into
   BF16 or Q8 slabs may be cheaper.
7. **Kimi-K3 with KDA is the first "living" feature Hearth must support anyway.** KDA's per-token
   delta-rule state ([Kimi Linear](https://arxiv.org/abs/2510.26692)) is per-sequence mutable state.
   It needs snapshot and restore (for session resume and speculative decoding rollback) and must be
   included in determinism tests. Designing that state API alongside the overlay API gives one
   coherent model: immutable versioned weights, per-sequence mutable state (KV plus recurrent), and
   explicit commits.

---

## Where the seed discussion is right or wrong

- **I1 (ROME/MEMIT rank-1 and rank-k closed-form edits with null-space projection as "surgery").**
  *Right on the mechanism; wrong if read as a scalable learning substrate.* The methods exist and
  work for small numbers of edits ([ROME](https://arxiv.org/abs/2202.05262);
  [MEMIT](https://arxiv.org/abs/2210.07229); [AlphaEdit](https://arxiv.org/abs/2410.02355)). At
  scale they degrade, and retrieval beats them for facts
  ([WikiBigEdit](https://arxiv.org/html/2503.05683v2); [Ren](https://arxiv.org/abs/2606.00570);
  [repro](https://arxiv.org/abs/2606.26783)). (**high**)
- **I2 (routing space as affine HNSW or metric tree; insert concepts into an expert's "unallocated
  subspace" or bifurcate into a child expert).** *Partly anticipated, partly undefined.*
  Retrieval-indexed experts and memories exist ([PEER](https://arxiv.org/abs/2407.04153);
  [memory layers](https://arxiv.org/abs/2412.09764)). Sparse slot updates reduce forgetting
  ([sparse memory FT](https://arxiv.org/abs/2510.15103)). Child experts exist as offline
  branch-and-mix ([BTX](https://arxiv.org/abs/2403.07816)). "Unallocated subspace of an expert"
  has no demonstrated operational definition in trained dense experts [inference]. The closest
  measurable proxy is AlphaEdit's thresholded null space of sampled keys, which shrinks and leaks
  at scale. Router drift on growth is a known failure mode
  ([StaR-MoE](https://arxiv.org/abs/2605.17571)). (**medium**)
- **I3 ("stem cell" reserved orthogonal blocks that differentiate when router entropy or
  reconstruction error spikes).** *Direction plausible; the trigger is speculative.* Adding capacity
  with the old weights frozen is demonstrated
  ([LLaMA Pro](https://arxiv.org/abs/2401.02415); [Lifelong-MoE](https://arxiv.org/abs/2305.12281);
  [MoE-LPR](https://arxiv.org/abs/2408.11396)), as is orthogonal subspace allocation
  ([O-LoRA](https://arxiv.org/abs/2310.14152)). I found no source for entropy-triggered automatic
  expert birth (**unverified**). LLaVA-CMoE's probe experts are the nearest
  ([arXiv 2503.21227](https://arxiv.org/abs/2503.21227)). "Replaced in background" requires a gate
  (M6), or it is uncontrolled self-modification. (**medium**)
- **I4 (DGM loop edits the loss, sparsity and routing program; SMT "guarantees bounded loss
  divergence" before hot-swap).** *The archive idea is right; the guarantee is wrong.* DGM validates
  empirically because proofs are impractical, and it modifies agent code, not weights
  ([DGM](https://arxiv.org/abs/2505.22954)). Even AlphaEdit's narrow, linear-algebra guarantee holds
  only approximately and only on a sample of keys
  ([AlphaEdit HTML](https://arxiv.org/html/2410.02355)). An SMT certificate on the loss of a
  billion-parameter nonlinear network over an unbounded input distribution is not achievable with
  any method I know of [inference, **high**]. Replace it with statistical gates (M6).
- **I5 (`hot_patch` via CMPXCHG8B/16B "in a single CPU cycle" between tokens).** *Wrong in
  mechanism and in where the cost lies.* An atomic pointer publish is cheap, but a locked CAS is not
  single-cycle and is not needed with a single writer
  ([CMPXCHG16B](https://www.felixcloutier.com/x86/cmpxchg8b:cmpxchg16b)). The real costs are
  staging megabytes of weights, KV staleness, routing and cache changes, and reclamation (M4).
  Between-token swapping itself is right and is already standard practice in adapter servers
  ([vLLM](https://docs.vllm.ai/en/latest/features/lora.html);
  [llama.cpp](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)).
  (**high**)
- **I6 (`invariant subspace(Sigma_prior, tol)` types; the compiler projects every weight write onto
  the null space of prior activations, "eliminating catastrophic forgetting at the machine-code
  level").** *Inspired by a real method; the claim is false.* Null-space projection is real
  (AlphaEdit; WISE's orthogonal shards, [WISE](https://arxiv.org/abs/2405.14768); O-LoRA). But
  Σ_prior is a statistic of sampled data, not a static property. The null space is thresholded. The
  protection is bounded and architecture-sensitive
  ([repro](https://arxiv.org/abs/2606.26783)). Spectral damage accrues anyway
  ([REVIVE](https://arxiv.org/abs/2601.11042)). Offer it as a runtime-checked contract with a
  measured residual (M8), never as a forgetting-free guarantee. (**high**)
- **I7 (safe self-modifying code with CLFLUSH/INVD, patched jump tables and pipeline flush).**
  *Wrong.* `INVD` is ring-0 only and drops dirty lines
  ([INVD](https://www.felixcloutier.com/x86/invd)). Weight updates are data, not code, so they need
  no instruction-cache management at all. JIT code patching follows platform rules (x86
  cross-modifying-code serialization; Apple `MAP_JIT` and icache invalidation) rather than cache
  flushes ([GCC](https://gcc.gnu.org/onlinedocs/gcc/Other-Builtins.html);
  [Apple](https://developer.apple.com/documentation/apple-silicon/porting-just-in-time-compilers-to-apple-silicon)).
  (**high** on INVD; **medium-high** on the rest.)
- **I8 ("inference = observation; continuous in-register learning on consumer hardware").**
  *Overstated.* Per-sequence learning at inference is real when the architecture is built for it
  ([Titans](https://arxiv.org/abs/2501.00663); [KDA](https://arxiv.org/abs/2510.26692);
  [TTT-E2E](https://arxiv.org/abs/2512.23675)). Persistent self-updating exists only as research
  that reports forgetting ([SEAL](https://arxiv.org/abs/2506.10943);
  [MIT](https://www.eecs.mit.edu/teaching-large-language-models-how-to-absorb-new-knowledge)).
  "In-register" is not meaningful for models whose weights span tens of gigabytes in DRAM and NVMe
  [inference]. (**high**)
- **Related seed claim C8 (one binary for control plane and compute plane).** Overlays, gates and
  archives are control-plane logic that must share types (versions, provenance) with compute-plane
  kernels. This supports a single language with an effect system distinguishing `infer` and
  `train`, but not a single *binary* [inference].

---

## Open questions

1. **Knowledge editing inside MoE experts.** Do locate-then-edit methods apply cleanly when a fact's
   recall routes through different top-k experts depending on context? Editing one expert affects
   every token routed to it. I could not search for MoE-specific editing studies after the search
   budget ran out (**unverified** whether they exist). Hearth could measure this directly using
   routing traces.
2. **Per-expert gate cost.** Which subset of M6 gates can run in minutes on a 9950X for a 30B MoE?
   A target: canary perplexity, KL-to-parent and simulated hit rate in under 5 minutes, to keep a
   DGM-style loop affordable.
3. **Composition semantics.** When two independently gated overlays touch disjoint experts, is
   their composition safe without re-gating? Router-mediated interactions suggest not always
   [inference]. Mithril needs a rule, for example "disjoint slab sets plus unchanged router implies
   composable; otherwise re-gate".
4. **KV policy defaults.** Is `AcceptStale` ever acceptable for a single-expert overlay deep in the
   network? Hearth can quantify the logit error empirically.
5. **Baking quantized overlays.** What quality is lost when merging a BF16 LoRA delta into a Q4
   slab, compared with keeping it unmerged? This is a measurable Hearth experiment and fits
   INV-HONEST.
6. **Independent replication of the strongest positive results** (UltraEdit's 2M edits; sparse
   memory finetuning's 11% forgetting). Both are single-group results.
7. **Retrofitting fast-weight memory.** Can a Titans- or KDA-style memory be added to an existing
   pretrained MoE without full retraining (an upcycling analogue)? I found no evidence either way
   (**unverified**).
8. **2026 on-device continual learning in products.** Apple's adapter toolkit page says version
   26.0.0 is its last release and is not compatible with OS 27 and later. What replaced it is
   unknown to me (**unverified**).

---

## Sources

- ROME: https://arxiv.org/abs/2202.05262
- MEMIT: https://arxiv.org/abs/2210.07229
- PMET: https://arxiv.org/abs/2308.08742 · https://ojs.aaai.org/index.php/AAAI/article/view/29818
- AlphaEdit: https://arxiv.org/abs/2410.02355 · https://arxiv.org/html/2410.02355 · https://proceedings.iclr.cc/paper_files/paper/2025/hash/29c8c615b3187ee995029284702d3f43-Abstract-Conference.html
- AlphaEdit reproducibility study: https://arxiv.org/abs/2606.26783
- Revisiting parameter-based knowledge editing (Ren et al.): https://arxiv.org/abs/2606.00570
- Understanding the collapse of LLMs in model editing: https://arxiv.org/abs/2406.11263
- Rebuilding ROME (r-ROME): https://arxiv.org/abs/2403.07175
- Butterfly effect of model editing: https://arxiv.org/abs/2402.09656
- WikiBigEdit: https://arxiv.org/abs/2503.05683 · https://arxiv.org/html/2503.05683v2
- REVIVE (spectral collapse): https://arxiv.org/abs/2601.11042
- Sequential editing and evidence arbitration (Anand): https://arxiv.org/abs/2609.29587
- UltraEdit: https://arxiv.org/abs/2505.14679
- GRACE: https://arxiv.org/abs/2211.11031
- WISE: https://arxiv.org/abs/2405.14768 · https://proceedings.neurips.cc/paper_files/paper/2024/hash/60960ad78868fce5c165295fbd895060-Abstract.html
- Cartridges: https://arxiv.org/abs/2506.06266
- S-LoRA: https://arxiv.org/abs/2311.03285
- Punica: https://proceedings.mlsys.org/paper_files/paper/2024/hash/054de805fcceb78a201f5e9d53c85908-Abstract-Conference.html · https://arxiv.org/abs/2310.18547
- vLLM LoRA docs: https://docs.vllm.ai/en/latest/features/lora.html
- llama.cpp server README: https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
- LoRA Without Regret: https://thinkingmachines.ai/blog/lora/
- LoRA Learns Less and Forgets Less: https://arxiv.org/abs/2405.09673
- LoRA vs full fine-tuning (intruder dimensions): https://arxiv.org/abs/2410.21228
- Transformer²: https://arxiv.org/abs/2501.06252
- Text-to-LoRA: https://arxiv.org/abs/2506.06105
- Apple Foundation Models adapter toolkit: https://developer.apple.com/apple-intelligence/foundation-models-adapter/
- Sparse upcycling: https://arxiv.org/abs/2212.05055
- Branch-Train-MiX: https://arxiv.org/abs/2403.07816
- Lifelong-MoE: https://arxiv.org/abs/2305.12281
- MoE-LPR: https://arxiv.org/abs/2408.11396
- LayerMoE: https://arxiv.org/abs/2505.22582
- LLaVA-CMoE: https://arxiv.org/abs/2503.21227
- StaR-MoE: https://arxiv.org/abs/2605.17571
- ESFT: https://arxiv.org/abs/2407.01906 · https://github.com/deepseek-ai/ESFT
- PEER (Mixture of a Million Experts): https://arxiv.org/abs/2407.04153
- Memory Layers at Scale: https://arxiv.org/abs/2412.09764
- Sparse memory finetuning: https://arxiv.org/abs/2510.15103
- LLaMA Pro: https://arxiv.org/abs/2401.02415
- Continual pre-training strategies (Ibrahim et al.): https://arxiv.org/abs/2403.08763
- TiC-LM: https://arxiv.org/abs/2504.02107
- EWC: https://arxiv.org/abs/1612.00796
- O-LoRA: https://arxiv.org/abs/2310.14152
- RL's Razor: https://arxiv.org/abs/2509.04259
- Test-time training for abstract reasoning: https://arxiv.org/abs/2411.07279
- TTT-E2E: https://arxiv.org/abs/2512.23675
- Titans: https://arxiv.org/abs/2501.00663 · https://arxiv.org/html/2501.00663
- Nested Learning / HOPE: https://arxiv.org/abs/2512.24695
- Kimi Linear (KDA): https://arxiv.org/abs/2510.26692
- SEAL: https://arxiv.org/abs/2506.10943 · https://www.eecs.mit.edu/teaching-large-language-models-how-to-absorb-new-knowledge
- QLoRA: https://arxiv.org/abs/2305.14314
- Darwin Gödel Machine: https://arxiv.org/abs/2505.22954 · https://arxiv.org/html/2505.22954v3
- Defeating nondeterminism in LLM inference: https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/
- Git-Theta: https://arxiv.org/abs/2306.04529
- Sigstore model-transparency: https://github.com/sigstore/model-transparency
- CMPXCHG16B reference: https://www.felixcloutier.com/x86/cmpxchg8b:cmpxchg16b
- INVD reference: https://www.felixcloutier.com/x86/invd
- GCC builtins (`__builtin___clear_cache`): https://gcc.gnu.org/onlinedocs/gcc/Other-Builtins.html
- Apple JIT porting guide (body not retrieved): https://developer.apple.com/documentation/apple-silicon/porting-just-in-time-compilers-to-apple-silicon
- Qwen3-30B-A3B config: https://huggingface.co/Qwen/Qwen3-30B-A3B/blob/main/config.json
- Local (read-only): Hearth `docs/FORMAT.md`, `engine/src/hx_store.h`, `governance/INVARIANTS.md`
