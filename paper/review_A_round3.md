# Review A, Round 3 (methodology and statistics)

**Paper:** "Do Spiking Networks Help Flow-Based Intrusion Detection? A Duplicate-Controlled Comparison on CSE-CIC-IDS2018" (`paper/main.tex`, 346 lines, 8 pages, abstract 248 words)
**Records checked:**
- `results/v5/seeds/summary.json`
- `results/v5/noport/summary.json`
- `results/v3/experiments/group_ce/summary.json`
- `results/v4/*`
- `results/cross_dataset/*`
- `results/analysis/*` (all `NOTE_*.md`, tables and JSON)
- `idsresearch/models.py` (PLE-MLP)

## Score: 7 / 10 (weak accept). Confidence 4/5. Round 1: 5; round 2 projection: about 7 after TEXT/CPU fixes.

**Justification.** The revision addresses most of what I asked for, and does it properly rather than cosmetically:
- five seeds with pre-declared, Holm-corrected tests and stated power;
- a spike-free PLE-MLP control;
- MF1-11 as a co-primary metric;
- disclosure of Dst Port, with a retrained ablation both in distribution and in transfer;
- a unified energy table in which the T = 12 sign flip is now admitted;
- honest label accounting with matched-FAR detection rates;
- name-based column mapping and a per-feature shift analysis;
- the corrected error-floor logic;
- a much cleaner abstract.

I spot-checked about 120 numbers and almost all of them match the records. The verdict ("no evidence that spiking adds accuracy; XGBoost is ahead; the energy sign depends on the cost model; no transfer") is now stated at the strength the evidence supports, with one exception: the abstract's causal sentence about the encoding (R3-2 below).

What keeps it from 8:
- A small set of factual and internal inconsistencies, one of them in the abstract (R3-1).
- Fig. 2(b) contradicts Table V (R3-3).
- The port effect is understated (R3-4).
- Unresolved design limits. There is one split seed and the test partition has been reused in rounds v3, v4 and v5 plus the no-port run. Episode-level leakage remains. The 2017 copy is incomplete. All of these are now disclosed, which I accept for a conference paper, but they cap the evidential weight.

---

## Status of my round-2 must-fix list

| # | Round-2 item | Status | Note |
|---|---|---|---|
| 1 | MF1-11 co-primary | **Resolved** | Table II has both metrics; l. 196 reports the 1.9 → 0.5 gap shrink. |
| 2 | Claims matched to n | **Resolved, with one overreach** | l. 167 is exemplary (CIs, Holm, MDE80, partition-variance caveat). The abstract (l. 21) and l. 38/327 still overreach; see R3-2. |
| 3 | ≥10 seeds + binned-MLP control | **Mostly resolved** | 5 seeds rather than ≥10, but power is stated (MDE80 ≈ 2 / 3.4 points), which is acceptable. The PLE-MLP is added, though capacity-confounded (R3-5). |
| 4 | Dst Port disclosure/ablation | **Resolved, understated** | l. 117 and l. 288 are correct; the magnitude is understated (R3-4). |
| 5 | Consistent energy model | **Resolved in the table, not in the figure** | Table V matches `energy_unified.json` exactly. Fig. 2(b) still plots the old linear-only model (R3-3). |
| 6 | Adaptation label accounting / matched FAR | **Resolved** | l. 297 and l. 323 match `NOTE_5`. The ~83k known-benign flows are disclosed. |
| 7 | Operating-point context | **Resolved** | Infiltration >99% of misses, argmax point, per-day FAR and the "prior offset carries calibration" result (l. 167–171) all verified. |
| 8 | Literature, error floor, "duplicate-controlled" | **Resolved** | l. 48–56, l. 73, l. 198. |
| 9 | Name-based mapping, KS shift, complete 2017 | **Partly resolved** | Mapping and KS are done (l. 269, verified). The complete or corrected 2017 data is still not used; this is disclosed. |
| 10 | Presentation package | **Resolved** | Figures cited, terminology unified, training details added, "nine" → "eight", τ=10% ranking, 0.052 FAR. |
| 11 | Group bootstrap / time-blocked split | **Declined, disclosed** (l. 167, l. 333) | Acceptable for a conference. It remains the main open validity question. |

---

## Remaining errors and inconsistencies

### R3-1. Factual mismatches (text vs. records)

| Location | Paper | Record | Verdict |
|---|---|---|---|
| l. 21 (abstract) | "detecting 23%–32% of attack flows after threshold recalibration, **with or without the destination-port input**" | `NOTE_7_noport.md` / `noport_table.md`: without port, recalibrated DR = 0.135 (E-SNN T=4), 0.310 (XGB), 0.344 (Enc-ANN T=4) | **Wrong.** The no-port range is 13.5%–34.4%. The 23–32% range holds only with the port. |
| l. 21, l. 148 | E-SNN T=4 five seeds "0.766 ± 0.012" | `v5/seeds/summary.json → aggregate.esnn["0.05"].macro_f1.std = 0.011482` | **Rounding error** (0.011); probably rounded twice. |
| l. 152 | XGBoost T=4 row "0.808 ± 0.005" | `v5 … xgb["0.05"].macro_f1.std = 0.004491` | **Rounding error** (0.004). The T=12 row (0.0053) is correct. |
| l. 323 | "Macro-F1 stays between 0.49 and 0.71" | Table VII itself: XGBoost continued at 5% = 0.483 (`finetune_cic2017.json`) | **Minor** (should be 0.48). |
| l. 117 vs l. 151 | Enc-ANN T=4 "0.787 → 0.776" | Table II gives Enc-ANN T=4 = 0.779 (5 seeds); 0.787 is the 3-seed value (`v4/steps/summary_T4.json`) | **Internal inconsistency.** The comparison is valid (3 vs 3 seeds) but must say "three-seed reference". |

### R3-2. The abstract's causal claim about the encoding is stronger than the data (l. 21, also l. 38, l. 167, l. 327)

"Since a spike-free encoding matches the SNN, any gain over the raw MLP comes from the input encoding, not from spiking dynamics."

There are three problems:
- **There is no established gain to attribute.** E-SNN vs MLP is +1.1 points (Holm p = 0.32).
- **"Matches" is asserted, not tested.** No equivalence test is run for E-SNN vs PLE-MLP. One is easy and would likely pass: the 95% Welch CI is [−0.9, +1.9], so a 2-point TOST should succeed. That would turn "matches" into a supported claim.
- **The data point the other way for Enc-ANN.** Enc-ANN (0.779) is 1.8 points above the PLE-MLP (0.761) and 2.4 above the MLP (unadjusted p = 0.057 for 13 classes, 0.020 for 11). So the spike-format encoding fed to a non-spiking network does better than binning. "The encoders help because they bin" is therefore not what the controls show, and l. 125 poses exactly this question without answering it.

Suggested wording: "We find no evidence that spiking dynamics add accuracy: the E-SNN is within [−0.9, 1.9] points of a spike-free piecewise-linear MLP (equivalent within 2 points, TOST p = …), and the best neural model is the non-spiking network fed the spike encodings."

### R3-3. Fig. 2(b) contradicts Table V and the text (l. 258 vs l. 227–249)

`figure_data.json → fig_steps.energy_uJ.esnn_45nm = [0.120, 0.220, 0.321]` and `ann_45nm = 0.388` come from the old linear-only model on the demo sample. The figure therefore shows the E-SNN below the MLP at every T under 45 nm. Section V-C and Table V (complete model: 0.18 / 0.33 / 0.49 vs 0.40) say it is 23% above at T = 12. The caption discloses "linear layers only", but the sign question is the paper's central energy point, and the figure shows the opposite answer. Fig. 2(a) also still uses the 3-seed T = 4 values while Table II's primary T = 4 values are 5-seed.

Fix: regenerate panel (b) from `results/analysis/energy_unified.json` (test_mix, complete model, ANN 0.398), add the +SRAM lines, and drop the "within 2.3%" caveat.

### R3-4. The port effect is understated on the co-primary metric (l. 117, l. 333)

"About one point" is the 13-class figure. That figure is diluted by the non-identifiable classes, which move erratically (SlowHTTPTest +0.265, FTP-BF −0.196 for the E-SNN; `noport_table.md`). On MF1-11, the co-primary metric, removing the port costs:
- E-SNN: 2.0 points
- Enc-ANN: 2.9 points
- XGBoost: 1.2 points (Holm p = 0.002)

Slowloris F1 drops by 0.07–0.15 and Web Attacks by 0.04–0.17. Report both numbers and say "one to three points".

The transfer paragraph (l. 288) should also mention the strongest new transfer result: the port-free Enc-ANN has the highest recalibrated DR (34.4%) and the highest 2017 ROC AUC (0.686) of all models tested.

### R3-5. The PLE-MLP is capacity-confounded (l. 125)

Parameter matching on a 70 × 16 = 1,120-dimensional input leaves the PLE-MLP with roughly 69 hidden units, against 252 for the raw MLP (and 21/21/13 for Enc-ANN at T = 12). "PLE matches the E-SNN" may therefore partly reflect a bottleneck rather than the encoding. A width-unconstrained PLE-MLP, or Gorishniy's per-feature linear embedding before the MLP, would separate the two. This does not invalidate the result, but l. 125 and l. 327 should state the hidden width.

### R3-6. Post-hoc primary-run switch and test reuse (l. 129, l. 333)

The paper now designates the five-seed T = 4 run as "primary evidence". That choice was made after T = 4 ≈ T = 12 had been observed on test (round 2), and seeds 42–44 of the E-SNN and Enc-ANN in v5 are the v4 runs. The test partition has now served v3, v4, v5 and the no-port run. The limitations paragraph covers this generically. It should say explicitly that the switch of primary run happened after review, and that only seeds 45–46 are new data.

Holm is applied within each (metric, τ) family of four. Across all 16 tests the XGBoost gap at 5% (p_Welch = 0.001) still survives, so this is a one-clause addition rather than a problem.

### R3-7. Analysis-artefact bugs (repository only, not in the paper)

- `results/analysis/seed_stats_5seed_table.md`:
  - The "Time-window equivalence" section compares `T4:esnn` with `T4:esnn` (diff 0, "equivalent? yes"). This is a self-comparison bug.
  - The "Exploratory" section has the same bug.
  - The "Per-model seeds" header says T = 12, but the values are the T = 4 five-seed run.
- The paper correctly uses the three-seed CI [−3.7, 3.1] from `NOTE_1` (l. 253). Fix the artefacts so that a reader does not find "equivalent: yes" in the released records.

### R3-8. Minor

- **l. 196.** "Puts Enc-ANN above random forest and CatBoost" holds for T = 12. At T = 4 (five seeds), Enc-ANN MF1-11 = 0.842 ties RF (0.842).
- **l. 249, Table V, INT8 E-SNN.** Accumulates are charged at 8-bit add cost (0.03 pJ), but membrane state needs a wider accumulator. State the assumption, since INT8 is the one model in which the E-SNN is cheaper at every T.
- **l. 341.** Only seed-42 checkpoints are released. Releasing the v5 five-seed checkpoints (or test-set probabilities) would let others run the group bootstrap that the authors declined.
- **Missing appendix pointer.** The paper does not point to the released 2017→2018 name-map table (`transfer_hygiene_table.md`); add a sentence or an appendix pointer.

---

## Verified in this round (selection)

All of the following match after rounding:
- **Table II, T = 4 rows:** all MF1, MF1-11, DR and FAR values vs `v5/seeds/summary.json` and recomputed per-class means, except the two s.d. values in R3-1.
- **Table II, T = 12 rows:** match v3 and `NOTE_2`.
- **l. 167:** all eight differences, CIs and Holm p-values vs `seed_stats_5seed_table.md`. MDE80 0.019/0.034 matches "about 2 / 3.4 points". T = 12 Holm p ≥ 0.25 matches `NOTE_1`.
- **v5 reproduction:** seeds 42–44 of MLP and XGB reproduce v3 exactly; E-SNN and Enc-ANN seeds 42–44 equal v4 T = 4.
- **Parameters:** PLE-MLP 85,923; Enc-ANN T = 4 86,701.
- **l. 167, Infiltration:** >99% of misses are Infiltration (recomputed: 99.2–99.9% across all models and seeds).
- **l. 169:** argmax FAR 0.02–0.14%, temperatures 0.96–1.01, the τ = 10% swap and the class-weighted numbers.
- **l. 171:** per-day FAR 0.1–24.1% (E-SNN) and <0.1–32.3% (XGB); >15% on the Infiltration days.
- **l. 117:** no-port 0.754 / 0.776 / 0.799; DR within 0.1 points; Slowloris, Web and Bot as the affected classes.
- **l. 288:** 32.5% / 68.8% GoldenEye / Slowloris; FAR 18% / 22%; DR 13.5% / 31.0%.
- **Tables IV–V:** all op counts and energies vs `energy_unified.json` (test_mix); 23% above, 55% below; factor 2.5–22; sparsity 72–74%; factor 2.9.
- **l. 269:** KS median 0.245, Fwd Seg Size Min 0.485, flag zeros 99.97% vs 68%, Init Bwd −1 vs 149, 7 of 70.
- **l. 297, l. 323:** 83k benign flows, temperature effect ≤0.001, frozen 24.8%, 95.9% vs 99.0%; Table VII matches `finetune_cic2017.json` (orig variant).

---

## Ranked fixes that would move the score most

### Text only (no new experiments)
1. **Fix the abstract transfer sentence** (R3-1): "23–32% with the port; 13.5–34% without". Fix the two s.d. roundings, 0.49 → 0.48, and label 0.787 as the three-seed reference. **+0.3**
2. **Rewrite the encoding claim** (abstract l. 21, l. 38, l. 327) as "no evidence that spiking adds accuracy". Report that Enc-ANN, not PLE binning, is the best neural model, and answer the question posed at l. 125 honestly (R3-2). **+0.4**
3. **Report the port effect as 1–3 points** on MF1-11 (l. 117, l. 333), and add the no-port Enc-ANN transfer result (R3-4). **+0.2**
4. **State the PLE-MLP hidden width** and the capacity caveat (R3-5). Make the post-hoc primary-run switch and the "only seeds 45–46 are new" point explicit (R3-6). **+0.2**
5. **Minor items in R3-8:** INT8 accumulator assumption, Enc-ANN/RF tie at T = 4, name-map pointer. **+0.1**

### New analysis, CPU, under 30 min with existing records and checkpoints
6. **Regenerate Fig. 2(b)** from `energy_unified.json` with the complete model and the +SRAM line. Use five-seed T = 4 values in Fig. 2(a) (R3-3). **+0.3**
7. **Run a TOST (2-point margin)** for E-SNN vs PLE-MLP and E-SNN vs MLP on the five-seed records, and use the result to support or withdraw "matches". Fix the self-comparison bugs in `seed_stats_5seed_table.md` (R3-2, R3-7). **+0.3**

### New experiments (Kaggle / GPU or data download)
8. **Group bootstrap over test feature groups** for the five-seed run (needs the Kaggle-side test arrays and probabilities; CPU-only on Kaggle). This closes the last statistical gap: partition variance. **+0.4**
9. **A width-unconstrained PLE-MLP** (or PLE + per-feature linear embedding), 5 seeds at T = 4 (R3-5). **+0.2**
10. **Transfer on the complete or corrected CIC-IDS2017** (Engelen et al. / Lanvin et al.). Inference for the frozen models, plus re-running the adaptation script. **+0.2**
11. *(Stretch.)* An episode- or time-blocked 2018 split for the E-SNN, Enc-ANN and XGB. **+0.3**

With items 1–7 (text plus CPU) I would rate the paper **8/10**. Adding item 8 makes 8 secure. Items 9–11 would move it toward 8.5–9.
