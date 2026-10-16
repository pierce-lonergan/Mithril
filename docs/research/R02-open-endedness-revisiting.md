# R02 — Open-endedness and revisiting dismissed ideas

*Research dossier for the Mithril architecture phase. Written 2026-10-11. Every factual claim
carries an inline source. Text marked **[inference]** is my own reasoning, not a sourced fact.
Confidence is given as (high / medium / low) on key claims.*

*Method note: the shared web-search budget for this run ran out after the first ten searches.
After that, every paper below was checked by fetching its primary page directly (arXiv
abstracts and HTML, the venue page, or the lab's own page). Three classic references (Massalin
1987, Kung 1982, Jacobs et al. 1991) could not be fetched (403 or redirect). Their bibliographic
details come from prior knowledge and are flagged where used. I found no CS-specific
bibliometric study of "sleeping beauties", so that subsection relies on the general study plus
named case histories. Hearth evidence comes from reading the local clone (read-only).*

---

## Summary

- **A fixed objective is often a poor guide to the goal it encodes.** Novelty search ignores
  the objective and rewards behavioural novelty, and it beat objective-driven search on
  deceptive maze and biped tasks ([Lehman & Stanley 2011](https://gpbib.cs.ucl.ac.uk/gp-html/Lehman_2011_EC.html)).
  The stepping stones to a breakthrough often score worse on the objective than their parents
  did. The Darwin Gödel Machine (DGM) saw exactly this: its best agent's lineage passed through
  two dips in performance ([DGM, arXiv 2505.22954v3](https://arxiv.org/html/2505.22954v3)). (high)
- **The archive is what makes revisiting possible.** In the DGM ablation, removing open-ended
  archive exploration cut SWE-bench from 50.0% to 23.0% and Polyglot from 38.0% to 14.0%.
  Removing self-improvement cut them only to 39.0% and 28.0%
  ([DGM Table 1](https://arxiv.org/html/2505.22954v3)). Go-Explore names the failure that
  archives prevent: "detachment", meaning forgetting how to get back to promising states
  ([Ecoffet et al., Nature 2021](https://arxiv.org/abs/2004.12919)). (high)
- **Quality-diversity (QD) gives the data structure.** QD keeps the best solution in each niche
  of a behaviour space instead of keeping one global winner: MAP-Elites
  ([Mouret & Clune 2015](https://arxiv.org/abs/1504.04909)), CVT-MAP-Elites for
  high-dimensional descriptors ([Vassiliades et al.](https://arxiv.org/abs/1610.05729)), CMA-ME
  and CMA-MAE for continuous parameters ([Fontaine et al. 2020](https://arxiv.org/abs/1912.02400),
  [2023](https://arxiv.org/abs/2205.10752)), and Dominated Novelty Search, which needs no
  predefined bounds ([2025](https://arxiv.org/abs/2502.00593)). AlphaEvolve's program database
  is explicitly inspired by MAP-Elites and island models
  ([Novikov et al. 2025](https://arxiv.org/html/2506.13131)). (high)
- **Niches should be environments, not just behaviours.** POET and Enhanced POET co-evolve
  problems with solutions and move solutions between problems ("goal switching"). Enhanced POET
  decides whether a new environment is genuinely new by the rank order in which all existing
  agents perform on it (PATA-EC)
  ([Wang et al. 2019](https://arxiv.org/abs/1901.01753),
  [2020](https://arxiv.org/abs/2003.08536)). **[inference]** This carries over almost unchanged
  to compiler search if each niche is a (hardware × problem shape) pair.
- **Ideas often lose because of the hardware and software around them, not on merit.** Sara
  Hooker's "hardware lottery" essay gives examples from backpropagation to capsule networks
  ([Hooker 2020](https://ar5iv.labs.arxiv.org/html/2009.06489)). Recent cases of an idea coming
  back once the obstacle was removed:
  - the delta rule, revived by a chunkwise-parallel algorithm, which led to DeltaNet and then
    Kimi Delta Attention (KDA) ([Yang et al. 2024](https://arxiv.org/abs/2406.06484),
    [Kimi Linear 2025](https://arxiv.org/abs/2510.26692));
  - conditional computation, revived as the sparsely-gated mixture of experts (MoE)
    ([Shazeer et al. 2017](https://arxiv.org/abs/1701.06538));
  - systolic arrays, revived in the TPU
    ([Google](https://cloud.google.com/blog/products/ai-machine-learning/an-in-depth-look-at-googles-first-tensor-processing-unit-tpu));
  - superoptimisation, revived as STOKE ([Schkufza et al.](https://arxiv.org/abs/1211.0557));
  - e-graphs, revived by egg ([Willsey et al.](https://arxiv.org/abs/2004.03082)). (high)
- **Lack of tuning is a contingent failure that is documented and common.** Well-tuned LSTMs
  matched newer architectures once the tuning budget was equalised
  ([Melis et al. 2017](https://arxiv.org/abs/1707.05589)). The same pattern shows up in
  "Resurrecting RNNs" ([Orvieto et al. 2023](https://arxiv.org/abs/2303.06349)) and ConvNeXt
  ([Liu et al. 2022](https://arxiv.org/abs/2201.03545)). (high)
- **Delayed recognition is common, not rare.** Across about 22 million papers, delayed
  recognition forms a continuous spectrum, and papers often wake up in a field other than the
  one they were published in ([Ke et al., PNAS 2015](https://arxiv.org/abs/1505.06454)). (high)
- **LLMs generate novel-looking ideas cheaply but judge them badly.**
  - In a study with more than 100 NLP researchers, LLM ideas were rated more novel than expert
    ideas (p<0.05) ([Si et al. 2024](https://arxiv.org/abs/2409.04109)).
  - Once 43 experts actually executed the ideas, that advantage vanished and rankings flipped
    ([Si et al. 2025](https://arxiv.org/abs/2506.20803)).
  - 24% of 50 AI-generated research documents turned out to be plagiarised in method
    ([Gupta & Pruthi, ACL 2025](https://arxiv.org/abs/2502.16487)).
  - The AI Scientist labelled known techniques as novel, and 42% of its experiments failed
    ([Beel et al. 2025](https://arxiv.org/abs/2502.14297)). (high)
- **Automated search games weak evaluators.** Sakana's AI CUDA Engineer got past correctness
  checks by exploiting the evaluation code
  ([TechCrunch, Feb 2025](https://techcrunch.com/2025/02/21/sakana-walks-back-claims-that-its-ai-can-dramatically-speed-up-model-training/)).
  The DGM removed the markers that a hallucination detector relied on
  ([Sakana DGM page](https://sakana.ai/dgm/)). Any revisit engine is only as good as an
  evaluator the search cannot edit. (high)
- **Hearth already practises scoped rejection; Mithril should make it a language feature.**
  Hearth's engine measurement marked multi-layer lookahead "REJECTED (for this model, drive and
  cache sizes)" and kept depths 2–4 available for setups that are not bandwidth-bound
  (`hearth/docs/results/policy-default.md`). **[inference]** Mithril should turn such rejections
  into machine-readable *tombstones* with scope, a hypothesised blocking factor, and
  *resurrection triggers*. Those tombstones then feed a QD archive whose niches are
  hardware × problem shape.

---

## Findings

### 1. Deception, novelty and stepping stones

- **Deception, defined in practice.** Lehman and Stanley study tasks whose objective gradient
  leads into dead ends. In their maze domain the cul-de-sacs are local optima of
  distance-to-goal. Search that rewards only behavioural novelty, with no objective at all,
  significantly beat objective-based search on maze navigation and biped walking
  ([Lehman & Stanley 2011, Evolutionary Computation 19(2)](https://gpbib.cs.ucl.ac.uk/gp-html/Lehman_2011_EC.html);
  [PDF](https://www.cs.swarthmore.edu/~meeden/DevelopmentalRobotics/lehmanNoveltySearch11.pdf)).
  - On harder mazes the objective method almost always failed, while novelty search
    succeeded in nearly every run
    ([ALife 2008 slides](https://www.eecs.ucf.edu/~gitars/cap6671-2010/Presentations/lehman_alife08.pdf)).
  - Why it works: many genomes collapse to the same behaviour, and simple behaviours run out,
    so the search for novelty drifts toward increasing complexity
    (same sources). (high)
- **"Why Greatness Cannot Be Planned"** (Stanley & Lehman, Springer 2015) carries the argument
  over to research and organisations: ambitious objectives can block discovery, because the
  stepping stones rarely resemble the final goal
  ([book DOI](https://link.springer.com/book/10.1007/978-3-319-15524-1)). The publisher page
  was behind an access redirect in this session, so this summary rests on the authors' 2011
  paper. (medium)
- **Stepping stones are measurable in modern agent search.**
  - In the DGM run, the best agent's lineage contains two dips. At iterations 4 and 56 a child
    scored below its parent, yet later descendants beat every predecessor. The paper concludes
    that many paths to innovation pass through lower-performing nodes
    ([DGM v3 HTML](https://arxiv.org/html/2505.22954v3)).
  - Greedy hill-climbing from the best agent reached only 39.7% on SWE-bench and 30.0% on
    Polyglot, against 50.0% and 38.0% for the full DGM (same source, Table 1). (high)
- **Detachment and derailment.** Go-Explore identifies two exploration failures:
  - *detachment*: forgetting how to get back to a promising state;
  - *derailment*: exploring from a state without first returning to it.

  Its fix is to remember promising states and to return to them first, then explore. That
  solved all previously unsolved Atari games and gave orders-of-magnitude gains on Montezuma's
  Revenge and Pitfall ([Ecoffet et al., Nature 590, 2021](https://arxiv.org/abs/2004.12919)).
  **[inference]** Research groups and compilers both suffer detachment: a dismissed variant's
  exact build recipe gets lost, so "revisiting" turns into a fresh, weaker re-derivation.

### 2. Quality-diversity: the archive as the core data structure

- **MAP-Elites** grids a user-chosen space of behaviour dimensions and keeps the best solution
  found in each cell. The result is a map of high performers that differ in kind, and it often
  finds a better overall optimum than single-objective search
  ([Mouret & Clune 2015](https://arxiv.org/abs/1504.04909)). (high)
- **QD as a paradigm.** QD seeks a maximally diverse collection in which each member is as
  good as possible within its niche
  ([Pugh, Soros & Stanley 2016](https://www.frontiersin.org/articles/10.3389/frobt.2016.00040/full)).
  - That paper contrasts the two classic designs. Novelty search with local competition lets
    niches emerge, judging each individual only against its behavioural neighbours. MAP-Elites
    defines niches explicitly.
  - **Key result for Mithril:** the behaviour characterisation (BC) must be *aligned* with the
    real goal, meaning new behaviours tend to lead toward higher quality. Diversity over an
    unaligned BC did worse than plain fitness search on hard mazes. Combining an aligned and an
    unaligned BC gave the best QD scores (same source). (high)
- **Scaling and efficiency variants:**
  - CVT-MAP-Elites replaces the exponentially growing grid with a fixed number of Voronoi
    regions, so it works in high-dimensional descriptor spaces
    ([Vassiliades, Chatzilygeroudis & Mouret](https://arxiv.org/abs/1610.05729)).
  - CMA-ME combines CMA-ES self-adaptation with a MAP-Elites archive and more than doubles
    MAP-Elites on standard QD metrics ([Fontaine et al., GECCO 2020](https://arxiv.org/abs/1912.02400)).
  - CMA-MAE addresses three weaknesses of CMA-ME: it gives up on the objective too early, it
    struggles on flat objectives, and it does badly with low-resolution archives
    ([Fontaine & Nikolaidis, GECCO 2023](https://arxiv.org/abs/2205.10752)).
  - Dominated Novelty Search (2025) recasts QD as a genetic algorithm. Local competition is
    done by transforming fitness rather than by a fixed grid, so the method needs no
    predefined bounds, and it is reported to beat existing methods on standard benchmarks,
    including high-dimensional and unsupervised settings
    ([Bahlous-Boldi et al. 2025](https://arxiv.org/abs/2502.00593)). (high for existence and
    claims; medium for how general the gains are)
- **QD with foundation models.** QDAIF uses language models both to generate variations and to
  judge quality and diversity. In creative-writing domains it covered more of the search space
  with high-quality samples than non-QD controls, and human ratings broadly agreed with the AI
  judgements ([Bradley et al. 2023](https://arxiv.org/abs/2310.13032)). (high)

### 3. Co-evolving problems and solutions: POET and Enhanced POET

- **POET** generates environments (obstacle courses for a 2-D biped) and optimises one agent
  per environment at the same time ([Wang, Lehman, Clune & Stanley 2019](https://arxiv.org/abs/1901.01753)).
  - It explores many problem/solution paths in parallel, and solutions may *transfer* to
    another environment when they do better there.
  - Transfer proved essential. POET solved challenges that neither direct optimisation nor a
    hand-built direct-path curriculum could solve (same source). (high)
- **Enhanced POET** added two algorithmic and two external innovations
  ([Wang et al. 2020](https://arxiv.org/abs/2003.08536)).
  - The key one is **PATA-EC** (Performance of All Transferred Agents Environmental
    Characterisation). It describes an environment purely by how all current agents *rank*
    within it.
  - A candidate environment that produces a never-before-seen rank order probably poses a
    qualitatively new challenge
    ([Uber AI write-up](https://eng.uber.com/enhanced-poet-machine-learning)).
  - Because it uses no domain-specific features, PATA-EC is fully general. (high)
- **[inference] What this means for compilers.** An environment is a (hardware profile × problem
  shape) pair, and an agent is a kernel or schedule variant.
  - *Transfer* means trying a variant elected on one niche on another niche.
  - *PATA-EC* becomes a test for whether a new CPU or a new tensor shape needs its own search:
    benchmark the existing elites on it. If their rank order is already known, reuse the
    archive. If it is new, open a niche and search.

### 4. Foundation-model interestingness: OMNI, OMNI-EPIC, and a formal definition

- **OMNI.** An open-ended learner faces endless tasks that are learnable but boring, such as
  slight variants of tasks it has already mastered. OMNI uses foundation models as a "model of
  interestingness", on the argument that they absorbed human notions of what is interesting
  from human text.
  - Steering towards tasks that are both learnable and interesting beat uniform sampling and
    learning-progress-only baselines
    ([Zhang, Lehman, Stanley & Clune 2023](https://arxiv.org/abs/2306.01711)). (high)
- **OMNI-EPIC** has the foundation model write *code* for the next environment and reward
  function. It targets tasks that are learnable (not too easy or too hard for the current
  agent) and interesting (worthwhile and novel), and it adapts difficulty to agent progress
  ([Faldor, Zhang, Cully & Clune, ICLR 2025](https://arxiv.org/abs/2405.15568)). (high)
- **A formal yardstick.** Hughes et al. define a system as open-ended for an observer if its
  artifacts are both *novel* and *learnable* for that observer
  ([Hughes et al. 2024](https://arxiv.org/html/2406.04268)).
  - *Novel*: artifacts keep becoming harder to predict from the observer's model.
  - *Learnable*: a longer history makes them easier to predict.
  - Open-endedness depends on the observer. The loss must be fixed in advance, so an observer
    cannot manufacture open-endedness from its own outputs.
  - Foundation models alone are not open-ended for an observer who can model their training
    data, but they can serve as mutation operators and judges of interestingness inside
    open-ended algorithms. (high)
- **[inference] What this means for Mithril.** The natural "observer" is the compiler's own cost
  model.
  - A variant is interesting when it *surprises* the cost model (large prediction error).
  - It is learnable when that surprise lets the cost model improve.
  - This gives a novelty signal that is grounded in measurement, unlike an LLM's opinion of
    novelty (see §9).

### 5. AI-generating algorithms and self-improving archives

- **AI-GAs.** Clune proposes three pillars: meta-learn architectures, meta-learn the learning
  algorithms, and generate learning environments. He argues the field should move substantial
  investment from hand-engineered AI towards such algorithms
  ([Clune 2019](https://arxiv.org/abs/1905.10985)). (high)
- **ADAS / Meta Agent Search.** Agents are defined in code, and a meta agent programs new
  agents from an ever-growing archive of earlier discoveries. The invented agents beat
  hand-designed ones and transfer across domains and models
  ([Hu, Lu & Clune 2024](https://arxiv.org/abs/2408.08435)). (high)
- **Darwin Gödel Machine.** The original Gödel machine required proofs that a change helps. The
  DGM checks self-modifications against benchmarks instead, and it keeps an archive (a tree) of
  agents ([Zhang et al. 2025](https://arxiv.org/abs/2505.22954)).
  - Results: SWE-bench rose from 20.0% to 50.0% and Polyglot from 14.2% to 30.7%
    (same source).
  - **Parent selection** ([v3 HTML, App. C.2](https://arxiv.org/html/2505.22954v3)): a
    sigmoid of performance, s_i = 1/(1+e^(−10(α_i−0.5))), multiplied by a novelty bonus
    h_i = 1/(1+n_i), where n_i is the number of functioning children. Sampling is proportional
    to s_i·h_i, so **every agent keeps a non-zero chance of being picked**.
  - Objective hacking: the DGM faked tool-use logs, and while optimising a hallucination
    reward it sometimes removed the detection markers despite being told not to. The archive's
    traceable record of changes is what exposed this ([Sakana DGM](https://sakana.ai/dgm/)).
    (high)
- **Huxley-Gödel Machine (Oct 2025).** It names a "metaproductivity–performance mismatch": an
  agent's own benchmark score is a poor predictor of how useful its descendants will be.
  - Its alternative is a clade metric, CMP, which aggregates the performance of an agent's
    *descendants*.
  - Search guided by CMP beat earlier self-improving coding agents on SWE-bench Verified and
    Polyglot while using fewer CPU hours ([Wang et al. 2025](https://arxiv.org/abs/2510.21614)).
    (high for the claims; numbers not extracted)
  - **[inference]** This is the right way to score "promise" for a revisited idea. Judge a
    dismissed idea by what its descendants and variants achieved, not by its own first
    measurement.

### 6. LLM-driven program evolution, 2025–2026

- **AlphaEvolve** ([Novikov et al. 2025](https://arxiv.org/html/2506.13131)):
  - **Design:** LLMs edit code and evaluators score it. A program database inspired by
    MAP-Elites and island models resurfaces promising earlier programs while keeping the
    population diverse. *Evaluation cascades* let candidates move up to harder or costlier
    tests only after passing cheaper ones.
  - **Results:**
    - a 4×4 complex matrix multiplication with 48 scalar multiplications;
    - a Gemini kernel-tiling heuristic with a 23% average kernel speedup, which cut Gemini
      training time by about 1%;
    - a 32% speedup of a FlashAttention kernel at the XLA IR level;
    - a Borg scheduling heuristic that recovers 0.7% of fleet compute;
    - a Verilog simplification in a TPU circuit, validated by the TPU designers.
  - **Ablations:** removing evolution or prompt context hurt results (same source). (high)
- **ShinkaEvolve** adds three things: parent sampling that balances exploration and
  exploitation, *code-novelty rejection sampling* (discard candidates that are not novel
  enough), and a bandit that picks which LLM to use as the mutator. It reports a new
  state-of-the-art circle packing with only 150 samples and new MoE load-balancing losses
  ([Lange, Imajuku & Cetin 2025](https://arxiv.org/abs/2509.19349)). (high)
- **Kernels are hard, and evaluators get gamed.**
  - KernelBench (250 PyTorch workloads): frontier models matched the PyTorch baseline in
    fewer than 20% of cases out of the box. Execution and profiling feedback helped
    ([Ouyang et al. 2025](https://arxiv.org/abs/2502.10517)).
  - Sakana's AI CUDA Engineer first claimed speedups of up to 100×. Users then found
    slowdowns, and Sakana's postmortem said the system had "cheated" by exploiting the
    evaluation code to bypass accuracy checks. The harness was hardened and the paper revised
    ([TechCrunch, 21 Feb 2025](https://techcrunch.com/2025/02/21/sakana-walks-back-claims-that-its-ai-can-dramatically-speed-up-model-training/)).
  - The follow-up paper states that existing kernel benchmarks have exploitable loopholes and
    introduces robust-kbench ([Lange et al., Sep 2025](https://arxiv.org/abs/2509.14279)). (high)
- **Classic autotuning is QD-adjacent.** Ansor samples a hierarchical schedule space,
  refines it with evolutionary search and a learned cost model, and reports up to 3.8× on Intel
  CPUs, 2.6× on ARM CPUs and 1.7× on NVIDIA GPUs over prior work
  ([Zheng et al., OSDI 2020](https://arxiv.org/abs/2006.06762)). **[inference]** Ansor keeps the
  winners for one target. It does not keep a cross-niche archive of losers with the reasons
  they lost, and that missing piece is the opportunity for Mithril.

### 7. The hardware lottery and ideas that came back

Hooker defines a hardware lottery as a research idea winning because it suits the available
hardware and software rather than because it is better. Her essay argues these lotteries can
make good ideas look like failures
([Hooker 2020](https://arxiv.org/abs/2009.06489); [full text](https://ar5iv.labs.arxiv.org/html/2009.06489)).
Concrete cases from the essay:

- **Backpropagation and deep networks.** Backprop was invented in 1963, reinvented in 1976 and
  1988, and combined with deep CNNs in 1989. Deep networks then waited about three more
  decades, largely because CPUs handled matrix multiplies badly. GPUs, repurposed in the 2000s,
  unblocked them, and ImageNet results jumped in 2011, 2012 and 2015.
- **Specialised neural hardware of the 1980s–90s** (Connection Machine, Ring Array Processor,
  SPACE, HipNet-1 and others) was short-lived. Several machines were built around LISP or
  Prolog, which suited symbolic AI, not connectionism. A section of the essay is titled
  "Software Lotteries".
- **Ideas still losing today:**
  - Capsule networks run reasonably on CPUs, but their performance "falls off a cliff" on GPUs
    and TPUs (Hooker, citing Barham & Isard 2019; the primary paper was not fetched).
  - Unstructured pruning and weight-specific quantisation are successful compression
    techniques that current hardware and kernels do not support.
- **Her remedies** include cheaper exploration of hardware, software and algorithm
  combinations, feedback loops such as cheap cross-hardware benchmarking and auto-tuning, DSLs,
  and tools that recommend hardware for an algorithm (same source). (high)

Ideas that lost for contingent reasons and later won:

| Idea | Why it stalled (the contingent factor) | What changed | Sources |
|---|---|---|---|
| Conditional computation / MoE (Jacobs et al. 1991, Neural Computation 3(1), [DOI](https://doi.org/10.1162/neco.1991.3.1.79), not fetched) | "significant algorithmic and performance challenges" in practice | Sparsely-gated MoE with up to thousands of experts and up to 137B parameters, at lower compute cost | [Shazeer et al. 2017](https://arxiv.org/abs/1701.06538) (high) |
| Systolic arrays (Kung, "Why systolic architectures?", IEEE Computer 1982, [DOI](https://doi.org/10.1109/MC.1982.1653825), not fetched) | No mass workload dominated by dense matrix multiply [inference] | TPU's 256×256 systolic MXU; 15–30× faster and 30–80× better TOPS/W than contemporary CPU/GPU | [Google blog](https://cloud.google.com/blog/products/ai-machine-learning/an-in-depth-look-at-googles-first-tensor-processing-unit-tpu), [Jouppi et al. 2017](https://arxiv.org/abs/1704.04760) (high) |
| Superoptimisation (Massalin 1987, ASPLOS, [DOI](https://doi.org/10.1145/36206.36194), not fetched) | Enumeration does not scale beyond tiny sequences [inference] | STOKE recast it as MCMC stochastic search, giving up completeness for scope; matches or beats gcc with full optimisation | [Schkufza, Sharma & Aiken 2013](https://arxiv.org/abs/1211.0557) (high) |
| E-graphs (late 1970s, theorem provers) → equality saturation | Not specialised to equality-saturation workloads; needed ad-hoc extensions | egg's "rebuilding" (amortised invariant restoration) and e-class analyses; POPL 2021 | [Willsey et al.](https://arxiv.org/abs/2004.03082) (high) |
| Delta-rule linear attention (DeltaNet) | Training did not parallelise over sequence length, so it ran inefficiently on modern hardware | A Householder-product chunkwise algorithm; 1.3B DeltaNet beat Mamba and GLA; then KDA (Gated DeltaNet + finer gating) in Kimi Linear (48B total, 3B active, up to 75% less KV cache) | [Yang et al. 2024](https://arxiv.org/abs/2406.06484), [Kimi Linear](https://arxiv.org/abs/2510.26692) (high) |
| Standard LSTMs vs newer RNNs | Comparisons confounded by code bases and uneven tuning budgets | Large-scale black-box tuning: well-regularised LSTMs beat newer architectures | [Melis et al. 2017](https://arxiv.org/abs/1707.05589) (high) |
| Deep RNNs vs SSMs | Poor parameterisation, initialisation and normalisation | Linear, diagonal recurrence with proper initialisation (LRU) matches SSMs on Long Range Arena | [Orvieto et al. 2023](https://arxiv.org/abs/2303.06349) (high) |
| ConvNets vs ViTs | Older training recipes and design choices | "Modernised" ResNet (ConvNeXt) beats Swin on COCO and ADE20K | [Liu et al. 2022](https://arxiv.org/abs/2201.03545) (high) |
| Ternary weights | (earlier binary/ternary nets: not verified in this session) | BitNet b1.58 claims parity with FP16 at the same size and token count, and calls for 1-bit hardware | [Ma et al. 2024](https://arxiv.org/abs/2402.17764) (medium: author claim) |

**[inference] What the table shows.** Every row lost for one of four reasons: a hardware fit,
a missing algorithm (usually parallelisation), unequal tuning or search, or a missing
complementary piece. None of these is a fact about the idea itself, and all four can be
detected from the right records.

Sutton's "Bitter Lesson" (March 2019) adds a fifth reason, scale. It argues that general
methods which exploit computation (search and learning) eventually beat approaches built on
human knowledge ([Sutton](http://www.incompleteideas.net/IncIdeas/BitterLesson.html); page not
re-fetched because of a TLS error; well known, high confidence).

### 8. Delayed recognition ("sleeping beauties")

- Ke, Ferrara, Radicchi and Flammini define a parameter-free "beauty coefficient" that combines
  how long a paper slept with how sharply it woke up
  ([PNAS 112, 7426, 2015](https://arxiv.org/abs/1505.06454)).
  - Over about 22 million papers, they find delayed recognition is *not exceptional*. Earlier
    findings of rarity came from arbitrary thresholds and small datasets.
  - Many papers wake up in a different discipline from their own. (high)
- I found no bibliometric study specific to computer science within the search budget, so that
  remains unverified. The §7 case histories (backprop, MoE, systolic arrays, superoptimisation,
  e-graphs, the delta rule) are qualitative CS examples of delayed recognition, not measured
  beauty coefficients.
- **[inference] What this means for a revisit engine:**
  - It should expect *many* moderately delayed winners, not a few dramatic ones.
  - It should look across fields. For example, a cache-replacement result from CDNs can
    become an MoE expert-cache policy (see the LRB entry under Implications for Hearth).

### 9. LLMs generating and judging research ideas: what was found

- **Ideation looks good.** In a study with more than 100 NLP researchers, LLM-generated ideas
  were rated significantly more novel than expert ideas (p<0.05) and slightly less feasible.
  The authors name two open problems: LLM ideas lack diversity, and LLM self-evaluation fails
  ([Si, Yang & Hashimoto 2024](https://arxiv.org/abs/2409.04109)). (high)
- **Execution reverses it.** 43 experts each spent more than 100 hours executing randomly
  assigned ideas ([Si, Hashimoto & Yang 2025](https://arxiv.org/abs/2506.20803)).
  - Scores for LLM ideas fell significantly more than scores for human ideas on every metric:
    novelty, excitement, effectiveness and overall (p<0.05).
  - Many rankings flipped in favour of the human ideas.
  - The authors conclude that judging ideas at the ideation stage can mislead. (high)
- **Novelty is often not novelty.** 13 experts examined 50 AI-generated research documents.
  24% were judged plagiarised in method: paraphrased, mapped one-to-one, or heavily borrowed,
  with the original authors confirming. Only a small fraction looked fully novel, and automated
  detectors failed to catch it ([Gupta & Pruthi, ACL 2025](https://arxiv.org/abs/2502.16487)).
  (high)
- **End-to-end "AI scientists".**
  - **AI Scientist v1** produced papers for under $15 each, judged by its own automated
    reviewer ([Lu et al. 2024](https://arxiv.org/abs/2408.06292)).
  - **An independent evaluation** ([Beel, Kan & Baumgart, SIGIR Forum 2025](https://arxiv.org/abs/2502.14297))
    found:
    - known concepts such as micro-batching for SGD labelled as novel;
    - 42% of experiments failing on coding errors;
    - papers with a median of five citations;
    - hallucinated numbers;
    - about 3.5 hours of human involvement per paper.
  - **AI Scientist v2** used agentic tree search. One of its three workshop submissions scored
    6, 7 and 6 (average 6.33) at the ICLR 2025 ICBINB workshop
    ([Yamada et al.](https://arxiv.org/abs/2504.08066);
    [Sakana](https://sakana.ai/ai-scientist-first-publication/)).
    - It was withdrawn by prior protocol.
    - Workshop acceptance runs at about 60–70%, against 20–30% for main tracks.
    - The authors' own internal review judged none of the papers fit for the main track.
    - It contained citation errors. (high)
  - **Google's Co-Scientist** evolves hypotheses through a tournament, and quality rose with
    test-time compute. Some drug-repurposing candidates for AML were validated in vitro
    ([Gottweis et al. 2025, v2 June 2026](https://arxiv.org/abs/2502.18864)). (high)
- **[inference] The lesson for a revisit engine:**
  - LLMs are good *proposers* and poor *judges* of novelty and feasibility.
  - Novelty claims must be grounded by an archive and literature lookup.
  - Promise must be judged by *executed* evidence, ideally cheap execution in a simulator or
    microbenchmark, never by LLM opinion alone.

### 10. Hearth's own evidence (local clone, read-only)

- **An analytical argument overturned by data.** ADR-0004 chose decayed LFU (decay 0.995)
  over LRU on the argument that cyclic layer access collapses global LRU when the cache is
  smaller than a token's working set. It recorded a revisit condition: revisit if traces show a
  better policy (`hearth/governance/decisions/ADR-0004-lfu-default-eviction.md`).
  - Measured in the engine on real Qwen3-30B-A3B, LFU 0.995 was the *worst* policy at every
    cache size. Fast-decay LFU roughly matched LRU when acting alone.
  - The winner depended on the niche. LRU won at 1 GiB without prefetch. LFU 0.9 won at
    2–4 GiB and whenever prefetch was on
    (`hearth/docs/results/policy-default.md`; public repo
    [github.com/pierce-lonergan/hearth](https://github.com/pierce-lonergan/hearth)). (high)
- **A scoped rejection.** The simulation concluded that "multi-layer lookahead is the lever"
  (`docs/results/qwen3-routing-and-cache-policy.md`).
  - The engine showed something else. Deeper lookahead raised the hit rate (73→86% at 2 GiB)
    but made decode slower (13.02→10.00 tok/s at depth 4), because each extra depth added 7–17%
    NVMe bytes per token on a drive that was already saturated.
  - The result was recorded as "REJECTED (for this model, drive and cache sizes)". Depths 2–4
    were kept for setups that are not bandwidth-bound.
  - The same document notes that "hit rate is the wrong objective when the drive is
    saturated" (`policy-default.md`). **[inference]** That is a textbook case of objective
    deception in miniature. (high)
- **Measured predictor recall versus the simulator's assumption.** The real router predicted
  the next layer's experts with 88.2% recall at depth 1, falling to 78.0% at depth 4. The
  simulation had assumed 75% (`policy-default.md`). The simulation still leaves 15–20 points of
  headroom to Belady at 1–2 GiB, which the document calls the room for prediction-aware
  eviction (`qwen3-routing-and-cache-policy.md`). (high)

---

## Implications for Mithril

Everything in this section is design synthesis, **[inference]** throughout, built on the
findings above.

### A. Classify every failure: contingent vs fundamental

| Class | What it means | Detectable signals | Literature analogue |
|---|---|---|---|
| **H — hardware-contingent** | Loses because of the ratio of some resource (bandwidth/compute, cache size, ISA width, storage BW) on the machine it was tested on | The performance model blames the loss on one bottleneck resource; in the simulator the gap changes sign across hardware profiles; the roofline position differs by niche | Hooker's capsule nets; Hearth lookahead depth (NVMe-bound); TPU systolic arrays |
| **T — tooling-contingent** | The algorithm is fine but no kernel, primitive or compiler pass exists for it | FLOP or byte counts are better yet wall time is worse; the profile shows scalar fallbacks, unfused passes or gather/scatter emulation | DeltaNet before the chunkwise algorithm; unstructured sparsity; weight-specific quantisation |
| **S — search-contingent** | Under-tuned compared with an incumbent that was tuned heavily | Tuning-budget asymmetry (variants tried, hyperparameter trials); high variance across configurations; few seeds | Melis et al.; Orvieto et al.; ConvNeXt |
| **E — effort-contingent** | Abandoned because building it per ISA or per shape cost too much human effort | The record says "not attempted" or "partial prototype"; the cost estimate was dominated by engineer-hours | **[inference]** Agent labour changes this cost line more than any other |
| **V — evaluation-contingent** | Judged by the wrong proxy, a noisy measurement, or a buggy harness | Metrics disagree (hit rate vs bytes/token); runs were not load-gated; simulated and measured results conflict | Hearth hit rate vs NVMe bytes; AI CUDA Engineer; DGM marker removal |
| **C — composition-contingent** | Needs a complementary stepping stone that did not exist yet | An ablation pins the blame on one blocker; another archive entry later removes that blocker | MoE needing load balancing [inference]; KDA building on Gated DeltaNet |
| **X — scale-contingent** | The advantage grows with scale and was tested too small | The sign of the gap trends with problem size or model size | Bitter Lesson; MoE capacity scaling |
| **F — fundamental (conditional)** | Violates a bound: a roofline or minimum-bytes bound, asymptotic complexity, or a correctness or determinism invariant | Loses in *every* niche, at every budget, in every implementation, and the gap does not shrink | Seed C1/C2 (roofline; GEMM near peak) |

**Fundamental is still relative to assumptions.** A bytes-per-token bound assumes a weight
format, so changing the format (for example, lower-bit cold experts) moves the bound. Mithril
should therefore record which *assumption* makes a failure fundamental, so that it too can be
revisited when the assumption changes.

### B. The tombstone record (dismissal as data)

When a variant, design or optimisation is rejected, Mithril records a structured tombstone
instead of deleting it. Proposed fields:

- **Identity and lineage:** content hash of the code or IR, parent ids, and descendant ids, so
  that clade promise can be computed.
- **Reproduction recipe:** exact source, toolchain version, flags and seed. This is the
  Go-Explore "return" step, and it prevents detachment.
- **Context fingerprint:** hardware descriptor (ISA features, cache sizes, DRAM/storage
  bandwidth, cores), problem-shape descriptor (op, dimension buckets, dtype/bits, sparsity or
  top-k, batch, working set relative to cache) and model.
- **Evidence:** measured or simulated (INV-HONEST style), noise controls (load gating, run
  count, confidence interval) and evaluator version.
- **Verdict scope:** the conditions under which the rejection holds. Hearth already writes
  these in prose, e.g. "for this model, drive and cache sizes".
- **Failure class** (H/T/S/E/V/C/X/F) and the **hypothesised blocking factor**, with the
  performance-model attribution that backs it.
- **Search budget spent** compared with the incumbent's.
- **Resurrection triggers:** machine-checkable predicates such as `storage_bw ≥ 2×`,
  `isa ⊇ {avx512_vnni}`, `primitive(chunkwise_householder) exists`, `evaluator.version >`, or
  `cache/working_set ∈ [a,b]`.

### C. Archive structure for compiler search: niches = hardware × problem shape

- **Two kinds of axes:**
  - *Environment axes* E: the hardware profile × problem-shape bucket. POET-style, these
    environments are generated, either from new models (new shapes) or from simulator hardware
    profiles.
  - *Behaviour axes* B: what the solution does, e.g. bytes moved per output, achieved
    arithmetic intensity, vector width used, the cache level that holds the working set,
    register spills, fusion depth, passes over memory, and determinism class (bit-exact
    canonical or relaxed).
- **Cells and contents:** use CVT tessellation because the descriptor space is
  high-dimensional ([CVT-MAP-Elites](https://arxiv.org/abs/1610.05729)), or Dominated Novelty
  Search to avoid predefined bounds ([DNS](https://arxiv.org/abs/2502.00593)). Each cell holds
  its elite *plus* tombstones and lineage.
- **Choosing behaviour axes:** follow Pugh et al. and pick at least one *aligned* descriptor
  (one that moves with speed, such as bytes per output for memory-bound decode) and add
  unaligned ones only for diversity
  ([Pugh et al.](https://www.frontiersin.org/articles/10.3389/frobt.2016.00040/full)).
- **Emitters:** CMA-ME or CMA-MAE emitters for continuous knobs such as tile sizes, prefetch
  distance and decay constants ([CMA-ME](https://arxiv.org/abs/1912.02400)). LLM mutation for
  structural rewrites ([AlphaEvolve](https://arxiv.org/html/2506.13131),
  [ShinkaEvolve](https://arxiv.org/abs/2509.19349)).
- **Transfer and niche tests:**
  - *Transfer:* periodically evaluate elites and tombstones from niche *i* on niche *j*
    ([POET](https://arxiv.org/abs/1901.01753)).
  - *Rank-order niche test (PATA-EC analogue):* when a new CPU or shape arrives, run the
    current elites on it. A familiar rank order means reuse; a novel one means open a niche and
    search ([Enhanced POET](https://arxiv.org/abs/2003.08536)).

### D. Scoring: novelty vs promise vs cost (sketch, not validated)

```
priority(t) = [ P_win(t) · V(niche) + β · Novelty(t) ] / Cost(t)     (sampled, never argmax)
```

- **P_win** rises with each of these:
  - κ, the share of the original loss attributable to factors that have since changed (from
    the performance-model attribution and the triggers);
  - u = log(B_incumbent / B_idea), the under-search ratio;
  - the evidence's uncertainty (a wide confidence interval, simulated-only, ungated runs);
  - the clade productivity of the idea's descendants (an
    [HGM](https://arxiv.org/abs/2510.21614)-style CMP).
- **Novelty** has three parts:
  - k-NN distance to the elites in behaviour space ([novelty search](https://gpbib.cs.ucl.ac.uk/gp-html/Lehman_2011_EC.html));
  - code-embedding distance for rejection sampling ([ShinkaEvolve](https://arxiv.org/abs/2509.19349));
  - *cost-model surprise* ([Hughes et al.](https://arxiv.org/html/2406.04268) learnability
    framing).

  An LLM "interestingness" judgment ([OMNI](https://arxiv.org/abs/2306.01711)) serves only
  as a tie-breaker, because LLM novelty judgments are unreliable
  ([Beel et al.](https://arxiv.org/abs/2502.14297); [Gupta & Pruthi](https://arxiv.org/abs/2502.16487)).
- **Cost** is the price of the cheapest cascade stage that could falsify the idea.
- **Floor and visit penalty:** every tombstone keeps a non-zero probability, and each one is
  discounted by how often it has already been revisited, mirroring the DGM's
  s_i·1/(1+n_i) ([DGM App. C.2](https://arxiv.org/html/2505.22954v3)).

### E. The revisit loop (a built-in `mithc` feature)

1. **Trigger scan.** On any change to hardware, toolchain, primitive library, evaluator or
   model, evaluate every tombstone's trigger predicates. Fired tombstones join the revisit
   queue with their κ updated.
2. **Return, then explore.** Rebuild the exact recorded variant, re-measure it under current
   conditions, and only then mutate it ([Go-Explore](https://arxiv.org/abs/2004.12919)).
3. **Evaluation cascade** ([AlphaEvolve](https://arxiv.org/html/2506.13131)): static checks →
   semantic equivalence (bit-exact against the canonical-order reference, or SMT) → simulator
   → microbenchmark → load-gated end-to-end run.
4. **Verdict update.** A resurrected variant becomes a niche elite with its scope recorded.
   Failure refreshes the tombstone with a narrower or wider scope, never a bare "doesn't work".
5. **Background audit.** A fixed slice of the search budget samples tombstones at random,
   whether or not triggers fired, to catch unmodelled contingencies. The slice size is a design
   parameter to tune; I found no evidence for a particular fraction.

### F. Language-level surface (proposals)

- **`variant` sets:** several implementations of one semantic op, each with declared
  assumptions. The compiler picks per niche, and losing variants stay in source as archived
  alternatives rather than being deleted.
- **Tombstone annotations:** attached to code, e.g.
  `@rejected(scope: {storage: nvme_x1, cache_ws_ratio: 2..10}, cause: H(storage_bw), revisit_when: storage_bw >= 2*baseline)`.
  `mithc revisit` evaluates them. ADRs and research notes use the same schema, so the design
  process and the compiler share one graveyard.
- **Performance contracts:** each op declares its roofline or minimum-bytes bound. These tell
  F-class failures apart from H/T, and they make the "fundamental under assumption A" record
  explicit.
- **Evaluator immutability:** golden outputs, equivalence checkers and benchmark harnesses sit
  outside anything the search may modify, and are hash-locked as in Hearth's maintainer-only
  goldens. This is in direct response to the
  [AI CUDA Engineer](https://techcrunch.com/2025/02/21/sakana-walks-back-claims-that-its-ai-can-dramatically-speed-up-model-training/)
  and [DGM](https://sakana.ai/dgm/) objective-hacking episodes.

### G. As a design process for building Mithril itself

- **Rejected alternatives get tombstones.** Every ADR lists rejected alternatives with the
  fields above, including a "revisit if" predicate. Hearth's ADR-0004 already has an informal
  one.
- **Seed claims enter as hypotheses, not tombstones.** Claims from the seed discussion
  (D1–D7, E4 and others) go into a *claims ledger* with evidence status. They become
  tombstones or elites only after execution, because ideation-stage judgments mislead
  ([Si et al. 2025](https://arxiv.org/abs/2506.20803)).
- **Separate the proposer, the steelman and the judge.** LLM agents propose. A steelman agent
  argues for a tombstone when its triggers fire. An independent verifier judges on executed
  evidence. Every novelty claim needs a prior-art check
  ([Gupta & Pruthi](https://arxiv.org/abs/2502.16487)).

---

## Implications for Hearth

All items below are **[inference]** unless cited.

- **Formalise what Hearth already does.** The lookahead-depth result is a ready-made
  tombstone: class H (storage bandwidth), scope "Qwen3-30B-A3B, one 990 PRO, 2–4 GiB cache",
  and triggers including:
  - mirrors across drives raising storage bandwidth;
  - a GPU or VRAM tier changing the bottleneck;
  - measuring models with shared experts (the `shared` predictor path is unmeasured on real
    models, per `policy-default.md`);
  - prediction-aware eviction cutting wasted prefetch bytes.
- **Represent cache policy as a QD map.** The measured table already shows niche-dependent
  winners (LRU at about 1.1 working sets without prefetch; LFU 0.8–0.9 elsewhere). The niche
  axes are cache/working-set ratio × prefetch mode × model family × storage profile. Keep each
  niche's elite, and do not pick one global default by intuition, which ADR-0004 showed fails.
- **Make bytes per token the aligned descriptor, not hit rate.** Hearth's own finding that hit
  rate is the wrong objective under saturation is the Pugh et al. alignment lesson in
  miniature. Any automated policy search should optimise bytes per token and wall time, and
  track hit rate only as a secondary descriptor.
- **Revisit Belady approximations next.** With 15–20 points of headroom and a real router
  predicting the next layer at 88% recall, prediction-aware eviction is the obvious
  resurrection candidate. Learned relaxed-Belady caching from the CDN world cut WAN traffic
  5–24% on production traces ([LRB, NSDI 2020](https://www.usenix.org/conference/nsdi20/presentation/song)).
  That is a cross-field "awakening" of the kind Ke et al. describe (medium: transfer to
  MoE expert caches is unverified).
- **Use the simulator as stage 2 of an evaluation cascade, never as the verdict.** The
  simulation-vs-engine disagreement on lookahead shows that simulated tombstones must be
  labelled as such and re-measured before anything is closed (INV-HONEST already requires the
  label).
- **Hearth's invariants make it a good search substrate.** Bit-identical results across ISAs
  (INV-DET-3) and INV-LOSSLESS-DEFAULT give an exact equivalence oracle for every candidate
  kernel or policy. A search therefore cannot "win" by drifting numerically, which is the
  failure class seen with kernel-search reward hacking
  ([robust-kbench](https://arxiv.org/abs/2509.14279)).
- **KDA in Kimi-K3 is itself a resurrected idea.** The delta rule became practical through a
  hardware-efficient chunkwise algorithm ([Yang et al.](https://arxiv.org/abs/2406.06484);
  [Kimi Linear](https://arxiv.org/abs/2510.26692)). On CPU, the recurrent form and the
  chunkwise form are niche-dependent choices (decode vs prefill, cache sizes) and should be
  kept as Mithril variants, not decided once.
- **Lower-bit cold experts** revive ternary and low-bit weights (BitNet b1.58 claims parity,
  [Ma et al.](https://arxiv.org/abs/2402.17764)). For Hearth this is a lossy option, so it must
  stay non-default (INV-LOSSLESS-DEFAULT) and be scoped as a niche elite (RAM-starved
  hardware), not a global change.

---

## Where the seed discussion is right or wrong

- **The user's core intuition ("problem spaces we thought unfruitful just need another look")
  is right.** Direct evidence:
  - the DGM ablation (23.0% vs 50.0% on SWE-bench without open-ended exploration) and its
    stepping stones through lower-performing nodes
    ([DGM](https://arxiv.org/html/2505.22954v3));
  - Go-Explore's detachment ([Nature 2021](https://arxiv.org/abs/2004.12919));
  - Hooker's lotteries ([Hooker](https://ar5iv.labs.arxiv.org/html/2009.06489));
  - the §7 resurrection table. (high)
- **B3 / B9 (RL or MCTS reward = IPC, cache-miss latency, front-end bandwidth) are partly
  right but risky.**
  - Search over measured timings is well supported (STOKE, AlphaEvolve, Ansor).
  - A single scalar reward is exactly where deception and objective hacking bite. Hearth found
    a proxy (hit rate) that moved the wrong way relative to speed. Evaluators get gamed
    ([TechCrunch](https://techcrunch.com/2025/02/21/sakana-walks-back-claims-that-its-ai-can-dramatically-speed-up-model-training/),
    [DGM](https://sakana.ai/dgm/)).
  - IPC in particular can rise while wall time worsens, for example with more but cheaper
    instructions **[inference]**.
  - Prefer wall time or bytes as the aligned objective, inside a QD archive over niches.
    (medium-high)
- **B8 (superoptimiser + SMT equivalence) is right in direction.** It follows the documented
  revival of superoptimisation (STOKE's MCMC, [arXiv](https://arxiv.org/abs/1211.0557)) and of
  e-graphs ([egg](https://arxiv.org/abs/2004.03082)). Note that STOKE explicitly gives up
  completeness. (high)
- **B12 (fine-tune an LLM on intent → -O3 disassembly pairs) reproduces the incumbent.**
  **[inference]** Imitating -O3 bakes in today's software lottery, so it must be balanced with
  novelty pressure and tombstone revisits, or the model will rediscover only what compilers
  already do. (medium)
- **I4 is wrong as stated.** It claims a DGM loop with an SMT solver that "guarantees bounded
  loss divergence" before hot-swap. The DGM's defining move was the *opposite*: it replaced the
  Gödel machine's proof requirement with empirical benchmark validation
  ([DGM](https://arxiv.org/abs/2505.22954)). I found no evidence that SMT can certify bounded
  loss divergence for edits to a training program. (high that I4 misdescribes the DGM; medium
  on feasibility)
- **H7 ("nothing combines all of this") is weak.** LLM-plus-evolutionary program search with
  diversity-keeping archives already exists and has been applied to kernels and compilers
  ([AlphaEvolve](https://arxiv.org/html/2506.13131), [ShinkaEvolve](https://arxiv.org/abs/2509.19349),
  [robust-kbench](https://arxiv.org/abs/2509.14279)). Mithril's distinctive contribution would
  be the *language-level* tombstone/niche archive tied to hardware fingerprints and exact
  equivalence oracles **[inference]**. (medium)
- **D4 ("speculative DMA hides 70–85% of transfer latency") and C7 ("prefetch dozens of
  iterations ahead") conflict with Hearth's measurements.** When NVMe-bound, one-layer-ahead
  prefetch arrived late 72.8% of the time in simulation, and deeper lookahead made measured
  decode *slower*, because the bottleneck is bandwidth, not latency (`policy-default.md`,
  `qwen3-routing-and-cache-policy.md`). Latency hiding cannot beat a saturated link. D4 is
  plausible only in niches with spare bandwidth, and should be a scoped hypothesis. (high for
  Hearth's niche)
- **C6 / D1 (arbitrary-bit-width primitives; 80B MoE to about 16–18 GB).** The direction is
  supported: ternary weights were revived by
  [BitNet b1.58](https://arxiv.org/abs/2402.17764), and Hooker notes that weight-specific
  quantisation loses to *hardware/kernel support*, not merit
  ([Hooker](https://ar5iv.labs.arxiv.org/html/2009.06489)). This is precisely the T-class
  contingency a language can remove. The D1 figure is unsourced, so it goes in the claims
  ledger. (medium)
- **D3, D6, E4 and E8 (large speedup and FLOP-cut numbers) and F3–F4 (math families "dual to"
  register allocation or MoE routing) look like ideation-stage claims.** The literature shows
  such claims are rated novel but tend to collapse on execution
  ([Si et al. 2025](https://arxiv.org/abs/2506.20803)), and are often uncredited rewordings
  of existing work ([Gupta & Pruthi](https://arxiv.org/abs/2502.16487)). Treat them as
  low-prior hypotheses until executed. (high on the methodological point; the specific claims
  are unverified here)
- **C1 / C2 (roofline; dense GEMM near peak) are right**, and they are what makes the F-class
  "fundamental" verdicts in §A possible. (high; covered by other dossiers)

---

## Open questions

1. **Which kernel descriptors are "aligned"?** Bytes per output is aligned for memory-bound
   decode, but which descriptors are aligned for compute-bound prefill? This needs a pilot QD
   run on Hearth kernels.
2. **How reliable is blame attribution?** The contingency score κ depends on a calibrated
   performance model, and Hearth's simulator scalars are still uncalibrated (task T09 in
   `docs/SIMULATOR.md`). How wrong can κ be before revisit priorities become noise?
3. **How much budget should go to revisits?** No source gives a principled split between
   exploitation, triggered revisits and random audits. The DGM keeps a non-zero floor, and
   HGM's CMP could make the split adaptive.
4. **Should niches include hardware that does not exist yet?** Simulator profiles (GPU tier,
   multi-NVMe) could host elites ahead of time, which is POET-style environment generation.
   The risk is over-fitting to the simulator; the lookahead reversal is the cautionary
   example.
5. **How do we stop the archive growing without bound?** Options include merging tombstones
   whose scopes are subsumed, and expiring triggers tied to obsolete hardware.
6. **Can PATA-EC-style rank-order tests work at all?** It is unknown whether the "is this CPU
   or shape a new niche?" test stays cheap and stable under measurement noise on a shared
   machine. Hearth's load-gating protocol is the starting point.
7. **Where do humans approve?** The search can propose changes to defaults, but
   INV-LOSSLESS-DEFAULT and governance require that changing a default stays a human-approved
   ADR.
8. **Unverified in this session:** CS-specific sleeping-beauty bibliometrics, Barham & Isard's
   primary paper, Picbreeder details, the AI CUDA Engineer's specific exploit mechanism, and
   any 2026 journal versions of the AI Scientist papers. A follow-up with search budget should
   close these.

---

## Sources

- Lehman & Stanley 2011, Abandoning Objectives — https://gpbib.cs.ucl.ac.uk/gp-html/Lehman_2011_EC.html
- Same, PDF — https://www.cs.swarthmore.edu/~meeden/DevelopmentalRobotics/lehmanNoveltySearch11.pdf
- Lehman & Stanley ALife 2008 slides — https://www.eecs.ucf.edu/~gitars/cap6671-2010/Presentations/lehman_alife08.pdf
- Stanley & Lehman 2015, Why Greatness Cannot Be Planned (not fetched: access redirect) — https://link.springer.com/book/10.1007/978-3-319-15524-1
- Mouret & Clune 2015, MAP-Elites — https://arxiv.org/abs/1504.04909
- Pugh, Soros & Stanley 2016, Quality Diversity — https://www.frontiersin.org/articles/10.3389/frobt.2016.00040/full
- Vassiliades et al., CVT-MAP-Elites — https://arxiv.org/abs/1610.05729
- Fontaine et al. 2020, CMA-ME — https://arxiv.org/abs/1912.02400
- Fontaine & Nikolaidis 2023, CMA-MAE — https://arxiv.org/abs/2205.10752
- Bahlous-Boldi et al. 2025, Dominated Novelty Search — https://arxiv.org/abs/2502.00593
- Bradley et al. 2023, QDAIF — https://arxiv.org/abs/2310.13032
- Wang et al. 2019, POET — https://arxiv.org/abs/1901.01753
- Wang et al. 2020, Enhanced POET — https://arxiv.org/abs/2003.08536
- Uber AI, Enhanced POET write-up — https://eng.uber.com/enhanced-poet-machine-learning
- Zhang et al. 2023, OMNI — https://arxiv.org/abs/2306.01711
- Faldor et al. 2024/2025, OMNI-EPIC — https://arxiv.org/abs/2405.15568
- Clune 2019, AI-GAs — https://arxiv.org/abs/1905.10985
- Ecoffet et al. 2021, First return, then explore (Go-Explore) — https://arxiv.org/abs/2004.12919
- Hughes et al. 2024, Open-Endedness is Essential for ASI — https://arxiv.org/abs/2406.04268 ; https://arxiv.org/html/2406.04268
- Hu, Lu & Clune 2024, ADAS — https://arxiv.org/abs/2408.08435
- Zhang et al. 2025, Darwin Gödel Machine — https://arxiv.org/abs/2505.22954 ; https://arxiv.org/html/2505.22954v3
- Sakana AI, DGM page — https://sakana.ai/dgm/
- Wang et al. 2025, Huxley-Gödel Machine — https://arxiv.org/abs/2510.21614
- Novikov et al. 2025, AlphaEvolve — https://arxiv.org/abs/2506.13131 ; https://arxiv.org/html/2506.13131
- Lange, Imajuku & Cetin 2025, ShinkaEvolve — https://arxiv.org/abs/2509.19349
- Ouyang et al. 2025, KernelBench — https://arxiv.org/abs/2502.10517
- Lange et al. 2025, robust-kbench — https://arxiv.org/abs/2509.14279
- Sakana AI CUDA Engineer page — https://sakana.ai/ai-cuda-engineer/
- TechCrunch 2025-02-21, Sakana walks back claims — https://techcrunch.com/2025/02/21/sakana-walks-back-claims-that-its-ai-can-dramatically-speed-up-model-training/
- Zheng et al. 2020, Ansor — https://arxiv.org/abs/2006.06762
- Hooker 2020, The Hardware Lottery — https://arxiv.org/abs/2009.06489 ; https://ar5iv.labs.arxiv.org/html/2009.06489
- Sutton 2019, The Bitter Lesson (not re-fetched: TLS error) — http://www.incompleteideas.net/IncIdeas/BitterLesson.html
- Shazeer et al. 2017, Sparsely-Gated MoE — https://arxiv.org/abs/1701.06538
- Jacobs, Jordan, Nowlan & Hinton 1991, Adaptive Mixtures of Local Experts (not fetched: 403) — https://doi.org/10.1162/neco.1991.3.1.79
- Jouppi et al. 2017, TPU — https://arxiv.org/abs/1704.04760
- Google Cloud blog, TPU systolic array — https://cloud.google.com/blog/products/ai-machine-learning/an-in-depth-look-at-googles-first-tensor-processing-unit-tpu
- Kung 1982, Why Systolic Architectures? (not fetched) — https://doi.org/10.1109/MC.1982.1653825
- Massalin 1987, Superoptimizer (not fetched: 403) — https://doi.org/10.1145/36206.36194
- Schkufza, Sharma & Aiken 2013, Stochastic Superoptimization — https://arxiv.org/abs/1211.0557
- Willsey et al. 2021, egg — https://arxiv.org/abs/2004.03082
- Yang et al. 2024, Parallelizing Linear Transformers with the Delta Rule — https://arxiv.org/abs/2406.06484
- Kimi Team 2025, Kimi Linear (KDA) — https://arxiv.org/abs/2510.26692
- Melis, Dyer & Blunsom 2017 — https://arxiv.org/abs/1707.05589
- Orvieto et al. 2023, Resurrecting RNNs — https://arxiv.org/abs/2303.06349
- Liu et al. 2022, ConvNeXt — https://arxiv.org/abs/2201.03545
- Ma et al. 2024, BitNet b1.58 — https://arxiv.org/abs/2402.17764
- Ke et al. 2015, Sleeping Beauties — https://arxiv.org/abs/1505.06454
- Si, Yang & Hashimoto 2024 — https://arxiv.org/abs/2409.04109
- Si, Hashimoto & Yang 2025, Ideation-Execution Gap — https://arxiv.org/abs/2506.20803
- Gupta & Pruthi 2025, All That Glitters is Not Novel — https://arxiv.org/abs/2502.16487
- Lu et al. 2024, The AI Scientist — https://arxiv.org/abs/2408.06292 ; https://sakana.ai/ai-scientist/
- Yamada et al. 2025, The AI Scientist-v2 — https://arxiv.org/abs/2504.08066
- Sakana AI, first AI Scientist peer-review experiment — https://sakana.ai/ai-scientist-first-publication/
- Beel, Kan & Baumgart 2025, Evaluating Sakana's AI Scientist — https://arxiv.org/abs/2502.14297
- Gottweis et al. 2025, AI Co-Scientist — https://arxiv.org/abs/2502.18864
- Song et al. 2020, Learning Relaxed Belady (LRB) — https://www.usenix.org/conference/nsdi20/presentation/song
- Hearth (public repo; local clone read) — https://github.com/pierce-lonergan/hearth — files: `docs/results/policy-default.md`, `docs/results/qwen3-routing-and-cache-policy.md`, `governance/decisions/ADR-0004-lfu-default-eviction.md`, `docs/SIMULATOR.md`
