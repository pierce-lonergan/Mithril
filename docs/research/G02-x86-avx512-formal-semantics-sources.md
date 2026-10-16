# G02 — Machine-readable AVX-512 semantics for the bit-exact checker: reuse vendor-pseudocode-derived models or write our own?

*Research dossier, 2026-10-11. Scope: what existing sources could supply formal, machine-readable semantics for the Zen 5 AVX-512 subset that Mithril's T1 bit-exact matcher (R07) and Exo-style `@instr` declarations (R05) need.*

*Method note: the shared WebSearch budget for this run was already used up when this agent started. Every claim below comes from fetching primary sources directly: papers, GitHub repositories (read through raw files and the GitHub API) and vendor pages. Several numbers are my own counts over files I downloaded; each is labelled as such. 2025–2026 coverage is therefore limited to what those repositories and author pages show. A paper I could not reach by direct fetch may exist; see Open questions.*

---

## Summary

- **No existing source gives bit-precise, silicon-validated floating-point semantics for AVX-512 in a formal format.** The pseudocode-derived line skips FP:
  - Hydride ([paper](https://charithmendis.com/assets/pdf/24-asplos-hydride.pdf)) and MISAAL, its PLDI 2025 successor ([paper](https://charithmendis.com/assets/pdf/25-pldi-misaal.pdf)), are integer-only.
  - VeGen models FP as uninterpreted functions, or as Z3 FPA with its default rounding. Its fuzzer skips every intrinsic whose pseudocode mentions NaN, MXCSR or ROUND, and accepts FP results within a 1e-6 tolerance ([sema-gen.py](https://github.com/ychen306/vegen/blob/rerewrite/sema/x86/sema-gen.py), [fuzzer.py](https://github.com/ychen306/vegen/blob/rerewrite/sema/x86/fuzzer.py)).
  - (high)
- **The vendor pseudocode itself cannot express several bit-level FP facts.** My reading of Intel's intrinsics XML v3.6.9 found these gaps (high):
  - `_mm512_fmadd_ps` is written as `(a*b)+c`, which hides the single rounding.
  - `_mm512_dpbf16_ps` never says that the instruction forces DAZ/FTZ and round-to-nearest-even, and ignores MXCSR. The SDM says all of this ([VDPBF16PS](https://www.felixcloutier.com/x86/vdpbf16ps)).
  - `MAX` and `Convert_FP32_To_BF16` are called but never defined.
  - 397 descriptions carry an unexpanded `[round_note]` placeholder.
  - My counts come from [Rust's copy of the XML](https://github.com/rust-lang/stdarch/blob/master/intrinsics_data/x86-intel.xml).
- **The formal ISA models have no AVX-512 semantics at all.** (high)
  - In the Sail x86 model translated from ACL2, all 1,374 EVEX opcode cases and all 744 VEX cases end in "Opcode Unimplemented in x86isa!" ([evex_opcodes_dispatch.sail](https://github.com/rems-project/sail-x86-from-acl2/blob/master/model/evex_opcodes_dispatch.sail)).
  - In upstream ACL2 x86isa (actively maintained in 2026), 0 of 1,375 EVEX entries have a semantic function. 95 of 747 VEX entries do ([inst-listing.lisp](https://github.com/acl2/acl2/blob/master/books/projects/x86isa/machine/inst-listing.lisp), my count).
- **Alive2's x86 support is small, integer-only and works on LLVM intrinsics, not machine code** ([x86_intrinsics_binop.inc](https://github.com/AliveToolkit/alive2/blob/master/ir/x86_intrinsics_binop.inc)). (high)
  - Upstream has 136 intrinsic entries, 55 of them AVX-512 (shifts, pack, pavg, psadbw, pmadd, pshufb, pternlog).
  - It has no FP, no VNNI and no BF16.
  - The Minotaur paper describes 165 intrinsics written in 660 lines of C++, validated by differential testing against the LLVM JIT. That testing found 14 bugs ([Minotaur](https://arxiv.org/abs/2306.00229)).
- **The best working precedent is "hand-write by need, then co-simulate on hardware".** (high)
  - AWS's s2n-bignum keeps a HOL Light x86 model of about 179 instruction constructors, including about 70 AVX2 integer mnemonics. It adds instructions one at a time, as proofs need them, and tests each against real execution with random states ([INSTRUCTION.md](https://github.com/awslabs/s2n-bignum/blob/main/x86/INSTRUCTION.md)).
  - Its latest additions are dated 2026 ([commits](https://github.com/awslabs/s2n-bignum/commits/main/x86/proofs/instruction.ml)).
  - It has no EVEX and no FP.
- **"Auto-generated" semantics still needed hand work.**
  - Hydride's authors had to edit Intel's and Qualcomm's pseudocode by hand. The shift kinds and saturation widening were ambiguous ([Hydride §5](https://charithmendis.com/assets/pdf/24-asplos-hydride.pdf)).
  - Hydride's repository also holds a hand-coded Rosette file for VNNI `dpbusd`/`dpwssd` and some unpacks ([hand_coded_x86_sema.rkt](https://github.com/akothen/Hydride/blob/main/codegen-generator/targets/x86/hand_coded_x86_sema.rkt)).
  - VeGen's random testing found Intel documentation errors, for example the saturation signedness of `psubus` ([VeGen §6.1](https://charithmendis.com/assets/pdf/21-asplos-vegen.pdf)).
  - (high)
- **Nobody has validated any of these on AMD silicon.** (high for what the sources state)
  - VeGen validated against Intel SDE, an emulator, not hardware ([fuzzer.py](https://github.com/ychen306/vegen/blob/rerewrite/sema/x86/fuzzer.py)).
  - Hydride and Minotaur evaluated on Intel Xeons ([Hydride](https://charithmendis.com/assets/pdf/24-asplos-hydride.pdf), [Minotaur](https://arxiv.org/abs/2306.00229)).
  - Mithril's target is Zen 5.
- **The Intel XML is not openly licensed.** (medium; not legal advice)
  - The Intrinsics Guide shows only "© Intel" ([guide](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html)).
  - Intel's site terms forbid modifying, redistributing, text-mining or systematically downloading site content without permission, unless a material carries its own licence ([Terms of Use](https://www.intel.com/content/www/us/en/legal/terms-of-use.html)).
  - VeGen, Hydride and Rust's stdarch nonetheless vendor copies of the XML.
  - By contrast, Intel XED's encoding datafiles, which now include AVX10.1, AVX10.2 and APX, are Apache-2.0 ([XED](https://github.com/intelxed/xed)).
- **Recommended decision [inference]:** Mithril should **own a single-source, hand-written semantics table** for the instructions it emits.
  - Every artefact is generated from that table: the T1 SMT terms, the `@instr` bodies, a C reference interpreter and, later, a Lean export.
  - Each table entry is then fuzz-validated against Zen 5 silicon, with Bochs's SoftFloat-based AVX-512 emulator as a second oracle.
  - Hydride, VeGen and Alive2 semantics serve as integer cross-check oracles, not as the trusted base.
  - Hearth's current kernels need only about 105 instruction forms (74 mnemonics). About 10 of the mnemonics are FP-semantics-sensitive (my mapping), so this is a weeks-scale job, not years.
- **Generating `@instr` from that table closes Exo's unchecked-`@instr` hole by construction.** The `@instr` body *is* the semantics, so the only remaining trust is "table equals silicon". That is an empirical claim, made explicit and continuously re-tested. [inference]

---

## Findings

### 1. What the T1 matcher actually needs

R07 defines T1 as a structural FP matcher that symbolically evaluates emitted x86 against the meaning. Every opcode it accepts needs an executable semantics. R05 notes that an Exo `@instr` "asserts" that its body is equivalent to the intrinsic, and nothing checks that claim (R05, §Trust boundary). For Hearth-class kernels a usable semantics source must give:

1. **Integer lanes, exact.** Saturation, widening, shuffles and masks. This is the easy part.
2. **FP lanes, bit-exact under the stated environment.** That means:
   - IEEE rounding under MXCSR.RC or embedded `{er}`;
   - single rounding for FMA;
   - x86 NaN selection and quieting;
   - DAZ/FTZ, both as configured and as forced by instructions such as VDPBF16PS;
   - integer-indefinite results for failed conversions ([CVTPS2DQ](https://www.felixcloutier.com/x86/cvtps2dq));
   - the MAXPS rule that returns the second operand on NaN or on ±0 ([MAXPS](https://www.felixcloutier.com/x86/maxps)).
3. **Masking and zeroing semantics** for EVEX `{k}{z}`.
4. **A format an SMT solver can consume**, and later a proof assistant.
5. **Evidence that it matches Zen 5.**

The SMT-LIB FloatingPoint theory has exactly one NaN per sort. It deliberately has no FP-to-IEEE-bit-vector function, because NaN has many encodings ([SMT-LIB FP](https://smt-lib.org/theories-FloatingPoint.shtml)). Item 2 therefore cannot be met by plain FPA terms. NaN selection must be modelled on bit-vectors on top of FPA. **[inference]** This is the single largest gap that every surveyed source leaves open.

**Scope of the problem for Hearth (my count).** I extracted every intrinsic used in Hearth's `quant_avx2.c` and `quant_avx512.c`, 130 distinct names, and mapped them through Intel's XML.
- They map to 105 instruction forms and 74 mnemonics. 23 are casts or multi-instruction "sequence" intrinsics with no single instruction ([quant_avx512.c](https://github.com/pierce-lonergan/hearth/blob/main/engine/src/quant_avx512.c); [XML](https://github.com/rust-lang/stdarch/blob/master/intrinsics_data/x86-intel.xml)).
- 65 of the intrinsics are FP-typed. Most are moves, shuffles, blends and logic ops, which are bitwise.
- The FP-semantics-sensitive mnemonics are about ten: (V)ADDPS/SS, (V)MULPS/SS, (V)MAXPS/SS, VMINPS, (V)CMPPS, VCVTDQ2PS, VCVTPS2DQ and VCVTPH2PS.
- **[inference]** The compiler may choose different instructions for some intrinsics. A real emitted-instruction census is needed, but the order of magnitude, about 100 forms and about 10 FP-hard mnemonics, is robust.
- Zen 5 supports AVX-512 F/CD/BW/DQ/VL, IFMA, VBMI, VBMI2, VNNI, BF16, BITALG, VPOPCNTDQ, GFNI, VAES, VPCLMULQDQ and VP2INTERSECT. It has no FP16 ([Wikipedia Zen 5](https://en.wikipedia.org/wiki/Zen_5), via R08).

### 2. The pseudocode-derived line

#### 2.1 VeGen (ASPLOS 2021)

- **Method:**
  - Python reads the XML that Intel uses to render the Intrinsics Guide.
  - A Z3-based symbolic evaluator for Intel's pseudocode language unrolls loops, inlines calls and if-converts. Its output is SMT formulas, which are lifted to VIDL ([VeGen §6.1](https://charithmendis.com/assets/pdf/21-asplos-vegen.pdf)).
  - Random testing validated the formulas and exposed wrong or ambiguous documentation, for example `psubus` saturation (same source).
- **Artefacts:**
  - The repository vendors Intel's `data-latest.xml` (version 3.5.2, dated 06/05/2020).
  - It also holds a 10 MB generated `intrinsics.all.sema`. By my count it serialises 3,012 intrinsics as SMT-LIB2: 937 `_mm512_*`, 36 VNNI dot products and **zero BF16** ([repo](https://github.com/ychen306/vegen/tree/rerewrite/sema/x86)).
  - 418 entries use **uninterpreted** functions such as `fp_add_64` (my count).
- **FP:**
  - `fp_sema.py` either emits uninterpreted functions or Z3 FPA with Python operators, which means Z3's default round-to-nearest-even. It supports only 32- and 64-bit FP ([fp_sema.py](https://github.com/ychen306/vegen/blob/rerewrite/sema/fp_sema.py)).
  - No MXCSR, DAZ/FTZ or NaN-payload model exists **[inference from code]**.
- **Validation:**
  - `sema-gen.py` runs 100 random tests per intrinsic. It compiles each intrinsic with gcc and runs it under **Intel SDE (`sde64`)**, not on silicon.
  - It skips CPUID groups such as AVX512_BF16, and any intrinsic whose pseudocode contains `NaN`, `MXCSR`, `ROUND`, `FP16`, `MANTISSA`, `SignBit` and similar.
  - It also skips `ternarylogic`, `popcnt`, `lzcnt` and `_cmp_` intrinsics.
  - FP test inputs come from `random.random()`, that is [0, 1), which avoids negatives, NaNs and subnormals. Results are compared with a tolerance of 1e-6 ([sema-gen.py](https://github.com/ychen306/vegen/blob/rerewrite/sema/x86/sema-gen.py), [fuzzer.py](https://github.com/ychen306/vegen/blob/rerewrite/sema/x86/fuzzer.py)).
  - Evaluation compiled with `-ffast-math` ([VeGen §7](https://charithmendis.com/assets/pdf/21-asplos-vegen.pdf)).
- **Licence and status:** MIT. Last push 2022-12-01 ([GitHub API](https://api.github.com/repos/ychen306/vegen)). Dormant.
- **Verdict:**
  - Useful as an **integer** cross-check oracle and as a worked example of an Intel-pseudocode parser.
  - Unusable for bit-exact FP. Its validation method is exactly the kind that hides the bugs Hearth cares about. (high)

#### 2.2 Hydride (ASPLOS 2024)

- **Method:**
  - Separate Python parsers for x86, Hexagon HVX and Arm pseudocode emit Hydride IR in **Rosette**.
  - The IR is canonicalised, and an SMT similarity check groups instructions into 397 parameterised "AutoLLVM" operations covering 3,557 instructions. Of those, 2,029 are x86 scalar and vector instructions spanning SSE2 through AVX-512, grouped into 136 classes ([paper §3, Table 1](https://charithmendis.com/assets/pdf/24-asplos-hydride.pdf)).
- **FP:** "Like Rake, Hydride only supports integer instructions; floating-point is left to future work" (same source). (high)
- **Validation:**
  - Random fuzz testing of the generated semantics against target C builtins (§5).
  - The vendor pseudocode did not distinguish logical from arithmetic right shifts and did not show the widening needed for saturating left shifts, so the authors **hand-edited the vendor specifications** (§5).
  - The x86 evaluation ran on a Xeon Silver 4216 (§6). **[inference]** The fuzzing probably ran there as well; the paper does not say.
  - Hydride found 5 masking bugs in Rake's hand-written HVX and Halide semantics (Table 2). This is the paper's own evidence that hand-written semantics need validation too.
- **Artefacts:**
  - [akothen/Hydride](https://github.com/akothen/Hydride), Apache-2.0, last push 2025-11-20 ([GitHub API](https://api.github.com/repos/akothen/Hydride)).
  - The x86 target directory holds `PseudoCodeParser.py`, `x86RoseCompiler.py`, a 2.2 MB `relevant.x86.xml` copy of Intel data, and a hand-coded Rosette file with 18 definitions. Those definitions include `_mm512_dpbusd_epi32`, `_mm512_dpwssd_epi32`, their masked forms and unpacks, with the Intel XML entries quoted as comments ([targets/x86](https://github.com/akothen/Hydride/tree/main/codegen-generator/targets/x86)).
- **Verdict:**
  - Excellent coverage of integer AVX-512, including VNNI.
  - Rosette output can be queried with SMT, so it can serve as an automatic **equivalence oracle** for Mithril's integer entries **[inference]**.
  - It offers nothing for FP. Its "automatic" claim includes hand edits and hand-coded VNNI. (high)

#### 2.3 MISAAL (PLDI 2025)

- MISAAL is the 2025 successor from the same group. It reuses Hydride's pseudocode-derived semantics to prune and synthesise rewrite rules offline, and reports compile times up to a geomean of 16× faster than Hydride ([paper](https://charithmendis.com/assets/pdf/25-pldi-misaal.pdf)).
- Its workflow figure lists SSE through AVX-512/VNNI for x86.
- The paper text never mentions floating point (my grep). **[inference]** It inherits Hydride's integer-only scope.
- It cites the Hydride code at github.com/akothen/Hydride. **This is the only 2025–2026 development in the pseudocode-derived line that I found**, and it does not add FP.

#### 2.4 Isaria (ASPLOS 2024, CACM 2026) and Diospyros (ASPLOS 2021)

- **Isaria:**
  - Takes an ISA specification written as a **hand-written** executable interpreter in Rosette, plus a cost model.
  - Uses Ruler to synthesise rewrite rules, which are checked by testing and then SMT. Equality-saturation phases are derived automatically ([paper](https://jamesbornholt.com/papers/isaria-asplos24.pdf)).
  - Target: the Tensilica Fusion G3 DSP. No x86.
  - Its rule grammar uses integer scalars (`scalar ::= integer | variable`, same source).
  - A 2026 CACM version exists ([CACM PDF](https://jamesbornholt.com/papers/isaria-cacm26.pdf); [author page](https://jamesbornholt.com/)).
- **Diospyros:**
  - Its rewrite rules are "correct with respect to the real numbers", not strict floating point.
  - Its translation validation models values in real arithmetic and uses uninterpreted functions ([paper](https://jamesbornholt.com/papers/diospyros-asplos21.pdf)).
  - Code: MIT, last push 2024-10 ([repo](https://github.com/cucapra/diospyros)).
- **Verdict:** Neither *derives* semantics. Both consume hand-written ones, and neither is IEEE-bit-exact. They matter to Mithril as **search** designs, for equality saturation over semantics, not as sources of semantics. (high)

### 3. Hand-written, validated models

#### 3.1 Alive2 x86 intrinsics and Minotaur (OOPSLA 2024)

- **Minotaur:**
  - Added "formal semantics for 165 LLVM intrinsic functions that correspond to SIMD operations supported by x86-64", drawn from SSE, AVX, AVX2 and AVX-512.
  - The code is parameterised by vector width, element size and masking, and comes to "only 660 lines of C++".
  - It is deliberately limited: no crypto instructions and no "unpopular" intrinsics ([Minotaur §3](https://arxiv.org/abs/2306.00229)).
- **Validation:**
  - Randomised differential testing runs each intrinsic with constant inputs through LLVM's JIT, then asks Alive2 whether the JIT result refines the semantics.
  - This found 11 wrong-result bugs, for example `pavg` overflow, and 3 malformed queries. After fixing those 14, "extensive testing failed to find additional defects" (same source).
  - **[inference]** The oracle is LLVM's lowering plus the host CPU, a Cascade Lake in the paper's evaluation, so it is silicon-backed but Intel-only.
- **Upstream reality (my inspection, 2026-10):**
  - Alive2's `ir/` directory has `x86_intrinsics.cpp` (775 lines) and three `.inc` tables.
  - The entries are 129 binary, 1 ternary (`pblendvb`) and 6 quaternary (`pternlog` d/q at 128/256/512). 55 are AVX-512.
  - **All are integer**: shifts, pavg, psign, pshufb, phadd/phsub, pmadd, pack, psadbw. There is **no FP, no `vpdpbusd` and no BF16**.
  - So the VNNI support named in the paper either lives in Minotaur's own build or was never upstreamed **(unverified)**.
  - `pternlog` was added on 2025-08-27, and the file was last touched 2026-10-04 ([commits](https://github.com/AliveToolkit/alive2/commits/master/ir/x86_intrinsics.cpp); [binop.inc](https://github.com/AliveToolkit/alive2/blob/master/ir/x86_intrinsics_binop.inc); [quadop.inc](https://github.com/AliveToolkit/alive2/blob/master/ir/x86_intrinsics_quadop.inc)).
  - Alive2 is MIT ([LICENSE](https://github.com/AliveToolkit/alive2/blob/master/LICENSE)).
- **Small defect noticed in passing:** In `X86IntrinTerOp::getTypeConstraints`, the shape check for the third operand tests `b->getType()` rather than `c->getType()` (lines 648–654 of the current file, [x86_intrinsics.cpp](https://github.com/AliveToolkit/alive2/blob/master/ir/x86_intrinsics.cpp)). It is harmless for `pblendvb`, where both operands share a shape. It illustrates that even tiny semantics libraries carry defects.
- **Structural limits for Mithril:**
  - Alive2 checks **LLVM IR** with LLVM's semantics: poison, and nondeterministic NaN bit patterns ([Alive2](https://users.cs.utah.edu/~regehr/alive2-pldi21.pdf)).
  - It cannot certify x86 NaN propagation or machine-code equivalence.
  - Its x86 entries are intrinsic-level semantics with poison lanes, not instruction semantics.
- **Verdict:** A good model of *how compact* parameterised semantics can be (165 intrinsics in 660 lines), and a third integer oracle. Not a reusable base. (high)

#### 3.2 s2n-bignum (AWS, HOL Light)

- **Process:** Instructions are "modeled by need" in three steps: decoding (`decode.ml`), semantics (`x86.ml`, as HOL Light definitions), and a **cosimulation test**. The test scans the project's assembly for instructions, sets random registers, flags and memory, runs the instruction on an independent execution backend, and compares the resulting state with the model ([INSTRUCTION.md](https://github.com/awslabs/s2n-bignum/blob/main/x86/INSTRUCTION.md), [simulator.ml](https://github.com/awslabs/s2n-bignum/blob/main/x86/proofs/simulator.ml)).
- **Coverage (my count):**
  - 179 constructors in `instruction.ml`. VEX-encoded AVX2 integer instructions include VPADD*/VPSUB*, VPMADDWD, VPMADDUBSW, VPMULHRSW, VPSHUFB, VPERMD/Q, VPBLENDVB, VPCLMULQDQ and VPTEST.
  - The register file declares ZMM and opmask registers, but **no EVEX instructions** are listed ([instruction.ml](https://github.com/awslabs/s2n-bignum/blob/main/x86/proofs/instruction.ml)).
  - No FP.
- **Status:** Active. The latest instruction additions are VPADDB (2026-09-09), VPBROADCASTW (2026-07) and the ML-DSA rejection-sampling instructions (2026-06) ([commits](https://github.com/awslabs/s2n-bignum/commits/main/x86/proofs/instruction.ml)). Licence: Apache-2.0 OR ISC OR MIT-0 (file headers).
- **Verdict:** This is the operational template R07 recommended (own the subset, co-simulate), proven at production scale for ML-KEM/ML-DSA AVX2 code. It is not reusable for AVX-512 or FP, but it is the process to copy. (high)

#### 3.3 K x86-64 (PLDI 2019) and Strata (PLDI 2016)

- **K x86-64 coverage:** All non-deprecated sequential user-level Haswell instructions: 3,155 variants across 774 mnemonics, validated by co-simulation and more than 7,000 instruction tests ([repo](https://github.com/kframework/X86-64-semantics)).
- **K x86-64 FP model:**
  - Bit-vectors are interpreted as FP through K's MPFR-backed library, with selectable rounding.
  - But FMA has precision issues, because K's library lacked MPFR's FMA.
  - Exceptions are unsupported, and **all NaNs are quiet**, with no SNaN/QNaN distinction ([paper §6](http://fsl.cs.illinois.edu/publications/dasgupta-park-kasampalis-adve-rosu-2019-pldi.pdf)).
- **K x86-64 status:** Last push 2020-03 ([GitHub API](https://api.github.com/repos/kframework/X86-64-semantics)), and it is pre-AVX-512.
- **Strata** synthesised formulas for Haswell instructions. It models FP instructions as **uninterpreted** functions, which cannot be executed or tested (per the K paper, same source; [Strata](https://stefanheule.com/papers/pldi16-strata.pdf)).
- **Verdict:** Both confirm R07: pre-AVX-512, and FP either imprecise (K) or uninterpreted (Strata). (high)

### 4. Theorem-prover ISA models: ACL2 x86isa and Sail x86

- **Sail x86 (translated from ACL2):**
  - The snapshot model has 2,118 opcode cases. All 1,374 EVEX cases and all 744 VEX cases perform decode and exception checks, then call `x86_model_error("Opcode Unimplemented in x86isa!")` (my grep of [evex_opcodes_dispatch.sail](https://github.com/rems-project/sail-x86-from-acl2/blob/master/model/evex_opcodes_dispatch.sail) and the VEX file).
  - The only vector semantics file is `shuffle_and_unpack.sail` (SHUFPS/SHUFPD/UNPCK), and `topfp.sail` is a 59-byte include stub ([model/](https://github.com/rems-project/sail-x86-from-acl2/tree/master/model)).
  - Licences: BSD-2 for the translator, BSD-3 for the model. Last push 2024-11-29 ([GitHub API](https://api.github.com/repos/rems-project/sail-x86-from-acl2)).
  - **R07 Open Question 2 is answered: the Sail x86 model has zero AVX-512 semantics.** (high)
- **ACL2 x86isa, upstream:**
  - Actively maintained, with 2026 commits from Kestrel that add CRC32 ([commits](https://github.com/acl2/acl2/commits/master/books/projects/x86isa/machine/instructions)).
  - It has grown an `fp/` directory (`mxcsr.lisp`, `arith-spec.lisp`, `cvt-spec.lisp`, `sqrt-spec.lisp`) for SSE-class FP with an MXCSR model ([fp/](https://github.com/acl2/acl2/tree/master/books/projects/x86isa/machine/instructions/fp)).
  - In `inst-listing.lisp`, by my parse, 640 of 1,070 legacy entries, 95 of 747 VEX entries (43 mnemonics) and **0 of 1,375 EVEX entries** have a semantic function. The listing's AVX-512 feature tags stop at F/BW/CD/DQ/VL/ER/PF/IFMA/VBMI/4FMAPS/4VNNIW. It has **no entries for VNNI, BF16, VBMI2, BITALG, VPOPCNTDQ or VP2INTERSECT** ([inst-listing.lisp](https://github.com/acl2/acl2/blob/master/books/projects/x86isa/machine/inst-listing.lisp)).
  - Licence: BSD-3 (file headers).
- **Verdict:** ACL2's SSE FP/MXCSR work is a useful *reference* for how to structure an MXCSR-aware FP layer. Neither model can be reused for AVX-512. (high)
- **Arm contrast:** Cranelift's verifier derives AArch64 specifications from Arm's machine-readable ASL through ASLp. It says the x86-64 backend "does not currently have the same coverage", and only individual x64 rules can be checked ([VeriISLE README](https://github.com/bytecodealliance/wasmtime/blob/main/cranelift/isle/veri/README.md); [ASLp](https://github.com/UQ-PAC/aslp)). Mithril's macOS arm64 back end can lean on vendor formal semantics; its x86 back end cannot. (high)

### 5. Executable but not formal references

- **Bochs:**
  - LGPL-2.1, pushed 2026-10-11.
  - Implements AVX-512, including `avx512_bf16.cc`, `avx512_fma.cc`, `avx512_rcp14.cc`, `avx512_rsqrt14.cc` and `avx512_pfp*.cc`, plus **AVX10.2** files (`avx10_2_bf16.cc`, `avx10_2_minmax.cc`, `avx10_2_cvt_fp8.cc`) and AMX ([cpu/avx](https://github.com/bochs-emu/Bochs/tree/master/bochs/cpu/avx)).
  - FP goes through Berkeley SoftFloat 3e with an x86 status word.
  - VDPBF16PS is implemented as two `f32_mulAdd` calls under a forced-RNE, DAZ/FTZ status. This matches the SDM ([avx512_bf16.cc](https://github.com/bochs-emu/Bochs/blob/master/bochs/cpu/avx/avx512_bf16.cc); [VDPBF16PS](https://www.felixcloutier.com/x86/vdpbf16ps)).
  - **[inference]** It is the strongest *bit-precise executable* oracle available. But it is C++ with no proof, and I found no published silicon-validation record **(unverified)**.
- **Intel SDE:** VeGen used it as its test oracle ([fuzzer.py](https://github.com/ychen306/vegen/blob/rerewrite/sema/x86/fuzzer.py)). It is closed-source and Intel-modelled. **[inference]** It cannot certify AMD behaviour.
- **Rust stdarch `intrinsic-test`:**
  - Generates C and Rust programs that call equivalent intrinsics on random inputs and compares their outputs ([README](https://github.com/rust-lang/stdarch/tree/master/crates/intrinsic-test)).
  - x86 was added to CI on 2025-10-26, when Intel's XML (v3.6.9) moved to `intrinsics_data/` ([commit](https://github.com/rust-lang/stdarch/commit/7b80a1fd2fd0c87d362dff8cd45e9f1718cce3fb)).
  - It tests *implementation agreement*, not semantics. It is a 2025 example of XML-driven differential-test generation.

### 6. The source data: Intel's intrinsics XML, the SDM and XED

**Version and coverage.**
- The live Intrinsics Guide is version **3.6.9, dated 07/12/2024**. It lists AMX variants but **not AVX10/AVX10.2 or APX** ([guide](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html)).
- Direct download of `data-latest.xml` returned HTTP 403 to a scripted client.
- Rust's copy has the same version and date ([x86-intel.xml](https://github.com/rust-lang/stdarch/blob/master/intrinsics_data/x86-intel.xml)).
- My analysis of that file:
  - 7,146 intrinsics in total.
  - 4,465 carry a CPUID tag from the Zen-5-relevant AVX-512 set (F/BW/VL/DQ/CD/VNNI/BF16/VBMI/VBMI2/IFMA/BITALG/VPOPCNTDQ/VP2INTERSECT/GFNI/VAES/VPCLMULQDQ/AVX-VNNI, excluding FP16).
  - Those map to 1,569 distinct XED instruction forms, 603 of them FP-typed.
  - 361 have no instruction element (sequences and casts), and 28 have an empty `<operation>`.
  - Per extension: AVX512F 2,851; VL 2,521; BW 828; DQ 399; VNNI 36; BF16 38; AVX-VNNI 16. There are **0 intrinsics tagged AVX10.1 or AVX10.2**.

**What the pseudocode does not say (my reading of v3.6.9).**
- **FMA:** `_mm512_fmadd_ps` is `dst := (a*b)+c`. Nothing in the text marks single rounding. A naive translator would produce double-rounded semantics, which is wrong in the last bit.
- **BF16 dot product:** `_mm512_dpbf16_ps` is two sequential `+=` of `make_fp32` products. It says nothing about the instruction's forced DAZ/FTZ, fixed RNE, MXCSR-ignoring, per-step-fused behaviour. The SDM states all of these: "MXCSR is not consulted nor updated", input denormals treated as zero, output denormals flushed ([VDPBF16PS](https://www.felixcloutier.com/x86/vdpbf16ps)).
- **BF16 conversion:** `_mm512_cvtneps_pbh` calls `Convert_FP32_To_BF16`, which is **never defined** in the XML (0 definitions). The SDM defines it as follows: denormals become signed zero, NaNs are truncated with the quiet bit forced, and normals use the 0x7FFF+lsb rounding trick ([VCVTNEPS2BF16](https://www.felixcloutier.com/x86/vcvtneps2bf16)).
- **MAX/MIN:** `MAX(...)` is used but never defined. The NaN and ±0 operand rule appears only in a `[max_float_note]` placeholder (49 occurrences) whose text is not in the XML.
- **Rounding notes:** 397 `[round_note]` and 151 `sae_note` placeholders. The relevant text lives outside the file.
- **NaN and MXCSR mentions:** Only 80 of 1,882 FP-typed Zen-5-relevant intrinsics mention NaN, and 72 mention MXCSR. All 126 occurrences of `MXCSR.DAZ` sit in special instructions (getexp/getmant/fixupimm class). **[inference]**
- **Conclusion:** Intrinsics pseudocode documents *dataflow*. Bit-exact FP behaviour lives in SDM prose and tables, such as the NaN-handling rules in SDM Vol. 1 ([SDM](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html); section not re-fetched in this session). A pseudocode parser alone cannot recover it. (high)

**Positive surprise.**
- `_mm512_reduce_add_ps` (a "sequence" intrinsic) specifies a halving tree: first `src[j] + src[j+8]`, then +4, then +2, then lanes 0+1.
- That is exactly the last stage of Hearth's canonical `sum16` (`L[j] = L[j] + L[j+s]` for s = 8, 4, 2, 1) ([XML](https://github.com/rust-lang/stdarch/blob/master/intrinsics_data/x86-intel.xml); [NUMERICS.md](https://github.com/pierce-lonergan/hearth/blob/main/docs/NUMERICS.md)).
- **[inference]** Whether GCC, Clang and MSVC lower it with that exact pairing is unverified. T1 would check the emitted shuffles either way.

**Licence.**
- The guide shows only "© Intel Corporation" ([guide](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html)).
- Intel's Terms of Use apply unless a material carries its own licence. They:
  - forbid modifying, copying and distributing content and creating derivative works (Sec. 5.1);
  - limit documents to informational, non-commercial personal use (Sec. 8.1);
  - forbid text and data mining and systematic downloading without written permission (Sec. 4.1.13–4.1.17) ([ToU](https://www.intel.com/content/www/us/en/legal/terms-of-use.html)).
- VeGen (MIT), Hydride (Apache-2.0) and Rust stdarch (MIT/Apache-2.0) all redistribute copies ([VeGen](https://github.com/ychen306/vegen/blob/rerewrite/sema/x86/data-latest.xml), [Hydride](https://github.com/akothen/Hydride/tree/main/codegen-generator/targets/x86), [stdarch](https://github.com/rust-lang/stdarch/blob/master/intrinsics_data/x86-intel.xml)).
- **[inference; not legal advice]** That shows community tolerance, not a licence grant. Mechanically derived semantics shipped in Mithril's Apache-2.0 repository could count as a derivative work. Semantics hand-written from reading the SDM carry less risk.

**XED.**
- Intel XED is Apache-2.0 ([LICENSE](https://github.com/intelxed/xed/blob/main/LICENSE)).
- Its datafiles cover `avx512f`, `avx512-bf16`, `vnni`, `vp2intersect`, `vpopcntdq-512`, `bitalg`, `vbmi2`, `avx10-1`, `avx10-2`, `apx-f` and future parts (`nvl`, `dmr`) ([datafiles](https://github.com/intelxed/xed/tree/main/datafiles)).
- It gives encodings, operand shapes and iclass names, but **no semantics**. **[inference]** It is the right, cleanly licensed source for Mithril's decoder/encoder tables and for keying the semantics table by XED iclass, the same key the Intel XML uses (`xed="VADDPS_ZMMf32_MASKmskw_..."`).

### 7. Why "generate from pseudocode" fails specifically for Hearth-relevant FP

These points tie §§2–6 together. **[inference]** unless cited.

1. **Default-MXCSR IEEE arithmetic is the easy part.**
   - With DAZ/FTZ off and RC = nearest, ADDPS, MULPS, DIVPS and SQRTPS give IEEE-754 results except for which NaN is produced. SMT-FPA with RNE models those results exactly.
   - Hearth does not set DAZ/FTZ (no MXCSR writes in `engine/src`, my grep) and forbids FMA contraction ([NUMERICS.md](https://github.com/pierce-lonergan/hearth/blob/main/docs/NUMERICS.md)).
   - So any source with FPA-RNE semantics, VeGen's precise mode included, is correct for *non-NaN* results of these instructions.
2. **NaN identity is where the sources fall short.**
   - SMT-FPA cannot express it ([SMT-LIB FP](https://smt-lib.org/theories-FloatingPoint.shtml)). K treats all NaNs as quiet ([K paper](http://fsl.cs.illinois.edu/publications/dasgupta-park-kasampalis-adve-rosu-2019-pldi.pdf)). Alive2 makes NaN bits nondeterministic ([Alive2](https://users.cs.utah.edu/~regehr/alive2-pldi21.pdf)).
   - Hearth canonicalises NaN results to `0x7fc00000` ([NUMERICS.md](https://github.com/pierce-lonergan/hearth/blob/main/docs/NUMERICS.md)), which cuts the requirement to NaN *classification*.
   - But the `amax` and clamping code relies on MAXPS's NaN-skipping operand order. Proving that the canonicalisation catches every NaN path needs exact MAX/CMP/BLENDV semantics.
3. **Non-IEEE instructions are invisible in pseudocode.**
   - VDPBF16PS and VCVTNEPS2BF16 force DAZ/FTZ ([SDM pages](https://www.felixcloutier.com/x86/vdpbf16ps)). CVTPS2DQ produces integer-indefinite results ([CVTPS2DQ](https://www.felixcloutier.com/x86/cvtps2dq)). RCP14/RSQRT14 are approximations; Bochs implements them in dedicated files ([cpu/avx](https://github.com/bochs-emu/Bochs/tree/master/bochs/cpu/avx)).
   - Each needs a bespoke entry whatever the source.
4. **Cross-vendor equality is unestablished.** Every validation record surveyed is Intel hardware or Intel SDE. Whether Zen 5 matches Intel bit-for-bit on approximation instructions (RCP14/RSQRT14) and on NaN selection is **unverified**. Mithril must measure it.

### 8. AVX10 and other 2025–2026 status

- **AVX10 in tooling:**
  - XED has `avx10-1`/`avx10-2` datafiles ([XED](https://github.com/intelxed/xed/tree/main/datafiles)).
  - Bochs implements AVX10.2 BF16, minmax and FP8-convert files ([Bochs](https://github.com/bochs-emu/Bochs/tree/master/bochs/cpu/avx)).
  - The Intrinsics Guide (v3.6.9, 2024) has no AVX10 entries ([guide](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html)).
  - I found **no formal AVX10 semantics** in any source above.
  - Zen 5 implements AVX-512, not AVX10 ([Wikipedia Zen 5](https://en.wikipedia.org/wiki/Zen_5)). **[inference]** AVX10 matters to Mithril only for future Intel targets (R08).
- **Other 2025–2026 items found:**
  - MISAAL (PLDI 2025; integer).
  - Alive2 `pternlog` (2025-08).
  - s2n-bignum AVX2 additions (2026).
  - ACL2 x86isa maintenance (2026; still no EVEX).
  - Rust `intrinsic-test` for x86 (2025-10).
  - Hydride repository activity (2025-11).
  - Isaria in CACM (2026).
  - TAIDL (MICRO 2025, Mendis group). It is an ISA definition language for tensor accelerators that auto-generates test oracles (functional simulators) *and* compiler backends from one definition ([TAIDL](https://github.com/act-compiler/taidl); [DOI](https://doi.org/10.1145/3725843.3756075)). It is not x86, but it is the closest published embodiment of the single-source pattern recommended below.

### 9. Comparison table

| Source | AVX-512 F/BW/VL | VNNI | BF16 | FP bit-precise? (rounding / NaN / DAZ-FTZ-MXCSR) | Format | Licence / status | Silicon validation |
|---|---|---|---|---|---|---|---|
| VeGen | Yes (937 `_mm512` entries, my count) | Yes (36) | No (skipped) | No: uninterpreted, or FPA-RNE; NaN/MXCSR/ROUND intrinsics skipped; 1e-6 tolerance | Z3 → SMT-LIB2 / VIDL | MIT; dormant since 2022 | Intel SDE only, 100 tests per intrinsic |
| Hydride / MISAAL | Yes (2,029 x86 instructions overall) | Yes (hand-coded file) | No | No FP at all | Rosette | Apache-2.0; pushed 2025-11 | Fuzzing vs C builtins (Intel Xeon [inference]) |
| Alive2 upstream x86 | Partial: 55 integer AVX-512 intrinsics | No | No | No FP | C++ → SMT (LLVM-intrinsic level) | MIT; active 2026 | Minotaur: LLVM JIT differential (Intel) |
| s2n-bignum | No EVEX | No | No | No FP | HOL Light | Apache-2.0/ISC/MIT-0; active 2026 | Cosimulation on hardware |
| K x86-64 | No (Haswell) | No | No | MPFR rounding; FMA imprecise; NaNs all quiet; no exceptions | K | Licence unverified; inactive since 2020 | Co-simulation (Haswell era) |
| ACL2 x86isa | 0 EVEX implemented | No entries | No entries | SSE-level MXCSR model (scope unverified) | ACL2 | BSD-3; active 2026 | Not assessed |
| Sail x86 (from ACL2) | 0 (all "Unimplemented") | No | No | No | Sail (→ C/OCaml/Coq/…) | BSD-2/3; last push 2024-11 | Not assessed |
| Isaria / Diospyros | No (Tensilica) | No | No | Real or integer arithmetic | Rosette | MIT | Simulator only |
| Bochs | Yes | Yes | Yes (+ AVX10.2) | Yes in intent (SoftFloat 3e + x86 status) | C++ emulator (not formal) | LGPL-2.1; active 2026 | Unverified |
| Intel XML | Yes (pseudocode) | Yes | Yes | No: FMA, DAZ/FTZ, NaN and MAX rules missing; notes externalised | XML pseudocode | No open licence; v3.6.9 (2024) | N/A |

---

## Implications for Mithril

1. **Decision: hand-write and own the semantics, from one source of truth. [inference; high confidence in direction]**
   - No source can be adopted wholesale as the trusted base for T1:
     - The pseudocode-derived ones are integer-only or FP-imprecise, and were not validated on AMD.
     - The formal ISA models have no AVX-512.
     - Alive2's model works at the wrong level (LLVM IR) and has the wrong NaN semantics.
   - **The decision's cost is small.** Hearth's current kernels need about 105 instruction forms, of which about 10 mnemonics are FP-hard.
   - **There is precedent for compactness:** Minotaur parameterised 165 intrinsics into 660 lines ([Minotaur](https://arxiv.org/abs/2306.00229)), and s2n-bignum maintains its model by need ([INSTRUCTION.md](https://github.com/awslabs/s2n-bignum/blob/main/x86/INSTRUCTION.md)).
   - **Estimate [inference]:** 25–40 parameterised families, about 1.5–3k lines of table plus generator, and a fuzz harness. That is weeks of agent work, not a research programme.
2. **Shape of the table.** Each entry is keyed by XED iclass and records:
   - lane shape;
   - mask mode (merge or zero);
   - integer semantics as bit-vector expressions;
   - FP semantics as an FPA core plus an explicit **x86 FP environment layer**:
     - MXCSR.RC / `{er}`;
     - DAZ/FTZ as configured or forced;
     - NaN selection and quieting as bit-vector logic;
     - integer-indefinite results;
     - MAX/MIN operand order;
   - a `preconditions` field, for example "MXCSR == default", that the T1 matcher must discharge or assume explicitly.
   - XED (Apache-2.0) supplies the encoding and operand side ([XED](https://github.com/intelxed/xed)).
3. **Generate all consumers from the table** (the TAIDL pattern, [TAIDL](https://github.com/act-compiler/taidl)):
   - (a) SMT-LIB2 terms (bit-vectors plus FPA) for T1;
   - (b) Exo-style `@instr` declarations whose bodies are the table's semantics. **This closes R05's unchecked-`@instr` hole by construction**: no hand-written body exists to disagree with the specification;
   - (c) a C reference interpreter for fuzzing;
   - (d) later, a Lean export for the R07 plan to mechanise T1.
   - Remaining trusted base: the table itself, the generator, the SMT solver and the fuzz evidence. [inference]
4. **Validation protocol (the part that actually earns trust):**
   - Fuzz every entry on **Zen 5 silicon**, as the primary oracle, with edge-case generators:
     - SNaN and QNaN with distinct payloads in each operand position;
     - ±0;
     - subnormals;
     - ±∞;
     - conversion overflow boundaries such as 2³¹ and 2²⁴;
     - saturation boundaries;
     - all mask patterns, including all-zero, all-one and alternating;
     - `{er}` variants.
   - Avoid VeGen's choices: [0, 1) inputs, a 1e-6 tolerance, and silently skipping hard intrinsics ([fuzzer.py](https://github.com/ychen306/vegen/blob/rerewrite/sema/x86/fuzzer.py)).
   - Use **Bochs** as a second, independent bit-precise oracle ([Bochs](https://github.com/bochs-emu/Bochs)). Disagreements among table, Zen 5 and Bochs are triaged, as the K team did against the Intel manual.
   - Add an Intel AVX-512 machine or SDE run only if Mithril claims cross-vendor bit-identity.
   - Re-run the fuzz campaign in CI on the target hardware whenever an entry changes, and record coverage per entry. This applies Hearth's INV-HONEST/INV-VERIFY style.
5. **Use the pseudocode-derived corpora as cross-checks, not inputs.**
   - For integer entries, prove SMT equivalence between Mithril's term and Hydride's Rosette semantics, VeGen's `intrinsics.all.sema`, and Alive2's integer intrinsics where they overlap. A disagreement flags a bug in one of the three. This is cheap, automatic, and needs no redistribution of their files if run locally **[inference]**.
   - Optionally, write a *draft generator* that parses the XML locally to propose integer entries for human or agent review. Do not ship the XML or mechanically derived output until the licence question is settled (Open question 2).
6. **Instruction-subset policy:**
   - Mithril's x86 back end should emit only table-covered opcodes, so T1 rejects anything else.
   - Treat VDPBF16PS, VCVTNEPS2BF16, RCP14/RSQRT14 and the FP16/AVX10.2 families as *separate, explicitly modelled* opcodes, admitted one at a time with their own fuzz record.
   - **[inference]** Approximation instructions should stay out of any kernel whose reference is defined by IEEE operations unless the reference itself is defined in terms of that instruction.
7. **Effect typing for the FP environment [inference].** MXCSR is ambient state. Mithril's type and effect system should make "runs under default MXCSR" a checked function effect. Otherwise every T1 certificate silently depends on an unstated precondition. ACL2's `fp/mxcsr.lisp` structure is a reference design ([fp/](https://github.com/acl2/acl2/tree/master/books/projects/x86isa/machine/instructions/fp)).
8. **Search remains untrusted and can borrow freely.** Hydride/MISAAL-style synthesis, Isaria-style rule synthesis plus equality saturation, and VeGen-style pattern generation are all compatible with an owned semantics table. In fact they *need* one. They can live in the untrusted search layer R07 described. [inference]

## Implications for Hearth

1. **Integer quantised paths are cheap to verify.** The Q8/Q4 hot loop uses VPDPBUSD, VPMADDUBSW, VPMADDWD, shifts, packs and shuffles. All are integer, exactly modelled already by Hydride (including hand-coded VNNI), VeGen and partly Alive2 ([Hydride x86](https://github.com/akothen/Hydride/tree/main/codegen-generator/targets/x86); [Alive2](https://github.com/AliveToolkit/alive2/blob/master/ir/x86_intrinsics_binop.inc)). A T1-checked Mithril port of these kernels is low-risk. [inference]
2. **FP risk concentrates in about 10 mnemonics**, and in the NaN path in particular. Hearth's canonical-NaN rule helps ([NUMERICS.md](https://github.com/pierce-lonergan/hearth/blob/main/docs/NUMERICS.md)), but MAXPS's operand-order rule is load-bearing in `amax` and clamping (R07 §Hearth findings). The table must model it exactly, and fuzzing must hit NaN in each operand position.
3. **Make the MXCSR assumption an invariant.**
   - `nearbyintf`-equivalent quantisation via VCVTPS2DQ depends on MXCSR.RC ([CVTPS2DQ](https://www.felixcloutier.com/x86/cvtps2dq)).
   - Hearth never writes MXCSR (my grep), so it inherits the OS or thread default.
   - **[inference]** Add an INV that thread-pool workers run with default MXCSR, and a cheap check at worker start. A host application that enables DAZ/FTZ would otherwise silently break INV-DET-3.
4. **Do not adopt VDPBF16PS for BF16 matmuls without changing the reference.**
   - It flushes subnormals and fuses each pair-step ([VDPBF16PS](https://www.felixcloutier.com/x86/vdpbf16ps)).
   - NUMERICS.md requires the product to be rounded and then added, never fused.
   - Hearth's current BF16 path widens BF16 to f32 by a 16-bit shift, which is exact (`_mm512_slli_epi32` in [quant_avx512.c](https://github.com/pierce-lonergan/hearth/blob/main/engine/src/quant_avx512.c)). Keep it. [inference, high]
5. **`_mm512_reduce_add_ps`'s documented tree equals sum16's final stage** (§6), so a future kernel may use it. Rely on it only after T1, or a disassembly check, confirms the compiler's lowering. [inference]

## Where the seed discussion is right or wrong

- **B8 (SMT, "Z3 / Alive2-style", equivalence check over x86 byte sequences): partly right, materially wrong on tooling.**
  - The SMT backbone is right.
  - Alive2 cannot do this job: it validates LLVM IR, and its x86 support is 136 integer intrinsic entries with no FP, VNNI or BF16 ([Alive2 x86](https://github.com/AliveToolkit/alive2/blob/master/ir/x86_intrinsics_binop.inc)). LLVM's NaN semantics are nondeterministic ([Alive2](https://users.cs.utah.edu/~regehr/alive2-pldi21.pdf)).
  - An x86-level checker needs x86 instruction semantics that no public source provides for AVX-512 FP. (high)
- **B12 (seed the model with Intel optimisation-manual tables; SMT validation in the loop): right on validation, naive on data rights.**
  - Intel's site terms forbid text and data mining and redistribution without permission ([ToU](https://www.intel.com/content/www/us/en/legal/terms-of-use.html)). Cost tables and pseudocode cannot simply be vendored.
  - The pseudocode also lacks the bit-level FP facts that SMT validation needs (§6). (medium)
- **F2 / F6 (adopt a Lean harness, "replacing ad-hoc SMT solvers"): wrong for x86 today.**
  - No Lean, HOL or ACL2 model with AVX-512 semantics exists. ACL2 has 0 EVEX entries implemented, Sail x86 has none, and s2n-bignum's HOL Light model is AVX2 integer only (§§3–4).
  - Lean becomes possible only *after* Mithril owns a table it can export. SMT stays the workhorse, with Lean checking certificates later (R07). (high)
- **H3 (open-source the SMT/Lean proofs): right, with a licence caveat.** Proofs over semantics hand-written from the SDM are cleanly publishable. Proofs over semantics mechanically derived from Intel's XML may not be. [inference; medium]
- **C6 (arbitrary-width integers lowering to popcount/BMI2/VNNI): verification-friendly.** These lowerings are integer-only and fall in the well-covered, exactly modelled part of every source (Hydride VNNI, VeGen, Alive2 shifts and pmadd). C6 is among the cheapest seed ideas to make *verified*. [inference; high]
- **B6 ("vectorisation mathematically guaranteed"): still overstated.** Semantics-driven instruction selection (VeGen, Hydride, MISAAL, Isaria) is complete only relative to its semantics, which are integer-only or real-valued in every surveyed system. It gives no guarantee for IEEE FP kernels. (high)
- **G1 (study alive2, souper, stoke): fine.** Add Hydride, MISAAL, VeGen, Minotaur, s2n-bignum and Bochs. They are more directly relevant to the x86-semantics problem than STOKE, which is unmaintained per R07. (high)

## Open questions

1. **Does Zen 5 match the table, and Intel, bit-for-bit?** This covers NaN selection in two-operand FP ops, MAXPS/MINPS with ±0, VCVTPS2DQ indefinite results, RCP14/RSQRT14 outputs, and VDPBF16PS subnormal handling. It needs a measurement campaign on the 9950X. No surveyed source reports AMD results.
2. **Licence:** may Mithril ship semantics *mechanically derived* from Intel's intrinsics XML under Apache-2.0, or must entries be written from reading the SDM? This needs the user's judgement, or a request to Intel ([ToU §2.2, §5.1](https://www.intel.com/content/www/us/en/legal/terms-of-use.html)).
3. **Literature I could not reach:** Are there 2025–2026 papers on LLM-assisted translation of ISA pseudocode or SDM prose into formal semantics such as Sail or SMT, or on formal AVX10 semantics? Web search was unavailable to this agent. A follow-up search pass is warranted before finalising.
4. **Where does Minotaur's `vpdpbusd.512` support live?** It is not in upstream Alive2 as of 2026-10. Is it in Minotaur's build? (unverified)
5. **Does AMD publish AVX-512 pseudocode** (for example in APM Vol. 4) that could serve as a second, AMD-authored reference? (unverified)
6. **Census of instructions the compiler actually emits** for Hearth's kernels under GCC, Clang and MSVC, as opposed to the 105 forms implied by the intrinsics. This defines Mithril's day-one table.
7. **Can Hydride's Rosette semantics be exported to plain SMT-LIB** for automated cross-checking of Mithril's integer entries without running Racket in CI? [inference: likely yes via Rosette's solver interface; untested]
8. **Bochs provenance:** has its AVX-512 FP implementation been validated against silicon, Intel or AMD? (unverified)

## Sources

- Hydride paper (ASPLOS 2024): https://charithmendis.com/assets/pdf/24-asplos-hydride.pdf (DOI https://doi.org/10.1145/3620665.3640385)
- Hydride code: https://github.com/akothen/Hydride ; https://github.com/akothen/Hydride/tree/main/codegen-generator/targets/x86 ; https://github.com/akothen/Hydride/blob/main/codegen-generator/targets/x86/hand_coded_x86_sema.rkt ; https://api.github.com/repos/akothen/Hydride
- MISAAL (PLDI 2025): https://charithmendis.com/assets/pdf/25-pldi-misaal.pdf (DOI https://doi.org/10.1145/3729301)
- Charith Mendis publications: https://charithmendis.com/
- VeGen paper (ASPLOS 2021): https://charithmendis.com/assets/pdf/21-asplos-vegen.pdf
- VeGen code: https://github.com/ychen306/vegen ; https://github.com/ychen306/vegen/tree/rerewrite/sema/x86 ; https://github.com/ychen306/vegen/blob/rerewrite/sema/x86/fuzzer.py ; https://github.com/ychen306/vegen/blob/rerewrite/sema/x86/sema-gen.py ; https://github.com/ychen306/vegen/blob/rerewrite/sema/fp_sema.py ; https://github.com/ychen306/vegen/blob/rerewrite/sema/x86/data-latest.xml ; https://api.github.com/repos/ychen306/vegen
- Minotaur (OOPSLA 2024): https://arxiv.org/abs/2306.00229 ; https://github.com/minotaur-toolkit/minotaur
- Alive2 x86 intrinsics: https://github.com/AliveToolkit/alive2/blob/master/ir/x86_intrinsics.cpp ; https://github.com/AliveToolkit/alive2/blob/master/ir/x86_intrinsics_binop.inc ; https://github.com/AliveToolkit/alive2/blob/master/ir/x86_intrinsics_quadop.inc ; https://github.com/AliveToolkit/alive2/commits/master/ir/x86_intrinsics.cpp ; https://github.com/AliveToolkit/alive2/blob/master/LICENSE
- Alive2 paper (PLDI 2021): https://users.cs.utah.edu/~regehr/alive2-pldi21.pdf
- Isaria (ASPLOS 2024): https://jamesbornholt.com/papers/isaria-asplos24.pdf ; CACM 2026: https://jamesbornholt.com/papers/isaria-cacm26.pdf ; https://jamesbornholt.com/
- Diospyros (ASPLOS 2021): https://jamesbornholt.com/papers/diospyros-asplos21.pdf ; https://github.com/cucapra/diospyros
- Rake: https://github.com/uwplse/rake
- Sail x86 from ACL2: https://github.com/rems-project/sail-x86-from-acl2 ; https://github.com/rems-project/sail-x86-from-acl2/blob/master/model/evex_opcodes_dispatch.sail ; https://github.com/rems-project/sail-x86-from-acl2/tree/master/model ; https://api.github.com/repos/rems-project/sail-x86-from-acl2
- Sail: https://github.com/rems-project/sail
- ACL2 x86isa: https://github.com/acl2/acl2/blob/master/books/projects/x86isa/machine/inst-listing.lisp ; https://github.com/acl2/acl2/tree/master/books/projects/x86isa/machine/instructions/fp ; https://github.com/acl2/acl2/commits/master/books/projects/x86isa/machine/instructions
- K x86-64 semantics: https://github.com/kframework/X86-64-semantics ; paper: http://fsl.cs.illinois.edu/publications/dasgupta-park-kasampalis-adve-rosu-2019-pldi.pdf ; https://api.github.com/repos/kframework/X86-64-semantics
- Strata (PLDI 2016): https://stefanheule.com/papers/pldi16-strata.pdf
- s2n-bignum: https://github.com/awslabs/s2n-bignum ; https://github.com/awslabs/s2n-bignum/blob/main/x86/INSTRUCTION.md ; https://github.com/awslabs/s2n-bignum/blob/main/x86/proofs/instruction.ml ; https://github.com/awslabs/s2n-bignum/blob/main/x86/proofs/simulator.ml ; https://github.com/awslabs/s2n-bignum/commits/main/x86/proofs/instruction.ml
- Bochs: https://github.com/bochs-emu/Bochs ; https://github.com/bochs-emu/Bochs/tree/master/bochs/cpu/avx ; https://github.com/bochs-emu/Bochs/blob/master/bochs/cpu/avx/avx512_bf16.cc
- Rust stdarch: https://github.com/rust-lang/stdarch/blob/master/intrinsics_data/x86-intel.xml ; https://github.com/rust-lang/stdarch/commit/7b80a1fd2fd0c87d362dff8cd45e9f1718cce3fb ; https://github.com/rust-lang/stdarch/tree/master/crates/intrinsic-test
- Intel Intrinsics Guide: https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html
- Intel Terms of Use: https://www.intel.com/content/www/us/en/legal/terms-of-use.html
- Intel SDM: https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html
- Intel XED: https://github.com/intelxed/xed ; https://github.com/intelxed/xed/blob/main/LICENSE ; https://github.com/intelxed/xed/tree/main/datafiles
- SDM instruction pages (felixcloutier mirror): https://www.felixcloutier.com/x86/vdpbf16ps ; https://www.felixcloutier.com/x86/vcvtneps2bf16 ; https://www.felixcloutier.com/x86/cvtps2dq ; https://www.felixcloutier.com/x86/maxps
- SMT-LIB FloatingPoint theory: https://smt-lib.org/theories-FloatingPoint.shtml
- Cranelift VeriISLE README: https://github.com/bytecodealliance/wasmtime/blob/main/cranelift/isle/veri/README.md ; ASLp: https://github.com/UQ-PAC/aslp
- TAIDL (MICRO 2025): https://github.com/act-compiler/taidl ; https://doi.org/10.1145/3725843.3756075
- Zen 5 ISA support: https://en.wikipedia.org/wiki/Zen_5
- Hearth: https://github.com/pierce-lonergan/hearth/blob/main/docs/NUMERICS.md ; https://github.com/pierce-lonergan/hearth/blob/main/engine/src/quant_avx512.c
- Internal: Mithril/docs/research/R05-kernel-dsls-and-schedules.md ; R07-verification-superoptimization.md ; R08-hardware-reality.md
