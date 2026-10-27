# Review B, round 3 (novelty, positioning, significance)

**Score: 7 / 10** (round 2: 5). **Confidence: 4 / 5.**

**Why the score rose.** The paper now asks the right question and answers it honestly. The title and abstract are reframed, and the abstract is 247 words. Related work credits the cross-dataset and dataset-quality literature, and the transfer result is presented as a confirmation, not a discovery. The spike-free PLE-MLP control and the five-seed T = 4 run with Holm-corrected tests were added. Dst Port is disclosed and ablated, the energy model is unified, and the error-floor logic is fixed. The contribution statement (L54) is accurate and defensible: established NIDS evaluation controls, plus a spike-input control, applied to SNN-IDS. For an IEEE conference such as IJCNN or CNS, this is now a solid negative-result paper.

**Why not 8+.** The central causal claim still says more than the data support (see E1 below). The encoding effect is confounded with the three-branch fusion architecture. Every interval reflects a single split. I re-ran the Welch tests from `results/v5/seeds/summary.json`; the numbers below come from that file.

---

## 1. Round-2 concerns: status

| # (round-2 list) | Status |
|---|---|
| 1 Identifiable-class metric | **Resolved.** MF1-11 is a column in Table II, and L196 states the consequence for the ranking. |
| 2 Statistics | **Mostly resolved.** Five seeds at T = 4, four pre-declared comparisons, Holm correction, MDE stated (L167). Group bootstrap and split seeds were declined and stated as a limitation (L333). T = 12 stays at 3 seeds. |
| 3 Prior-work positioning | **Resolved.** D'hooge ×2, Cantone, Apruzzese, Flood, Lanvin, Dampfhoffer, Gorishniy and Shwartz-Ziv are added and used correctly (L48–54). |
| 4 Dst Port | **Resolved.** Disclosed at L117. Ablated in-distribution and in transfer. The slow-DoS transfer claim is now qualified as port-dependent (L288). |
| 5 Title, abstract, contributions | **Resolved.** |
| 6 Spike-free encoding baseline | **Added, but over-interpreted** (E1). |
| 7 Energy consistency | **Mostly resolved.** Table V is good. Fig. 2(b) and the Discussion lag behind it (E2, E4). |
| 8 Adaptation accounting | **Resolved.** The label count equals the budget, DR is reported at matched 1% FAR (L297, L323), and "same-capture re-split, optimistic" is stated. |
| 9 Operating context | **Resolved.** Per-day FAR, argmax point, temperatures and the Infiltration share of misses are given (L167–171). I checked them against `operating_context_table.md` and they match. |
| 10 Seeds | **Partially resolved.** 5 seeds at T = 4 only. |
| 11 Corrections and training details | **Resolved.** |
| 12 Transfer hygiene | **Partially resolved.** Name-based mapping and per-feature KS are in. The full or corrected CIC-IDS2017 export and a near-duplicate audit are not. |

**Spot checks that match the files.** I checked the following and found no discrepancies:
- **Table II, T = 4 block:** all means and s.d. match the v5 summary.
- **L167 statistics:** all Welch CIs, Holm p-values and MDEs match `seed_stats_5seed_table.md`.
- **No-port figures:** L117 and L288 match `NOTE_7_noport.md`.
- **Energy:** Table V and the 23% / 55% figures at L227 match `energy_unified_table.md`.
- **Adaptation:** L297 and L323 (24.8%, 95.9% vs 99.0%) match `NOTE_5`.
- **Reproduction:** v5 seeds 42–44 reproduce v3/v4 for the MLP, XGBoost, the E-SNN and Enc-ANN.

---

## 2. Remaining errors and inconsistencies

**E1. The encoding-vs-dynamics inference is still overstated** (abstract L21, contribution L38, L167, L327). The abstract says: "Since a spike-free encoding matches the SNN, any gain over the raw MLP comes from the input encoding, not from spiking dynamics." This has three problems.
- **(a) Non-significance is not equivalence.** E-SNN − PLE-MLP is +0.5 points with an MDE of about 1.9, and no TOST was run on the five seeds. "Matches" should be "is not distinguishable from".
- **(b) The dynamics claim rests on the wrong comparison.** The evidence that dynamics add nothing is E-SNN vs Enc-ANN: −1.3 points, 4 of 5 paired seeds negative. PLE-MLP is not that comparison.
- **(c) PLE does not reproduce the gain that the spike codes deliver without spikes.** These are my exploratory, unadjusted Welch tests on the v5 values:
  - Enc-ANN − MLP: +2.4 points at 5% (p ≈ 0.06) and +3.7 points at 1% (p ≈ 0.009).
  - PLE-MLP − MLP: +0.6 at 5% (p ≈ 0.07) and +1.5 at 1% (p ≈ 0.04).
  - Enc-ANN − PLE-MLP: +1.8 at 5% (p ≈ 0.12) and +2.2 at 1% (p ≈ 0.06).

  So the best-supported "encoding" effect belongs to Enc-ANN. Enc-ANN differs from PLE-MLP in two ways: its encoding and its three-branch, meta-net fusion architecture.

  A supportable sentence would be: *"Feeding the same spike codes to a non-spiking network is at least as accurate as the SNN; we find no evidence that membrane dynamics add accuracy. Whether the remaining gain over the MLP comes from the codes or from the three-branch fusion is not resolved."*

**E2. Fig. 2(b) contradicts the text** (L258 vs L227 and Table V). The caption says panel (b) uses 45 nm costs "for the linear layers only" on the old 4,400-flow sample. That panel therefore still shows the T = 12 E-SNN below the MLP (0.32 vs 0.39 µJ). The text and Table V say it is 23% above (0.49 vs 0.40). Regenerate the panel from `energy_unified.json` using the complete, test-mix numbers.

**E3. The same T = 4 configuration has two values** (Table II L148/L151 vs Table III L216/L219, and L117).
- Table II gives E-SNN 0.766 ± 0.012 and Enc-ANN 0.779 ± 0.020 (5 seeds).
- Table III and the no-port reference at L117 give 0.766 ± 0.015 and 0.787 ± 0.022 (3 seeds).

The captions are technically correct, but a reader sees Enc-ANN at T = 4 as both 0.779 and 0.787. Use the 5-seed values in Table III, or footnote the difference. At L117, say that the reference is the 3-seed run matching the 3-seed no-port run.

**E4. The energy Discussion omits what Table V shows** (L329, L249).
- **"A 45 nm adder cost favours the SNN at short windows" (L329)** is true only without memory traffic. With SRAM reads, the E-SNN costs more than the MLP at every T: 1.41 vs 1.24 µJ at T = 4. Under INT8, T = 12 is at parity (0.019 vs 0.020).
- **The like-for-like baseline is inconsistent.** L249 calls the INT8 MLP the like-for-like point for Loihi, but L329 quotes "2.5 to 22×" against the FP32 and SRAM figures. Against INT8 the factor is roughly 150–450×. Pick one baseline and state it.

**E5. A configuration was run but not reported** (L288 vs `noport_table.md`). The no-port Enc-ANN (T = 4) transfers best of every model tested:
- recalibrated DR 34.4%;
- ROC AUC 0.686;
- FAR at the 2018 threshold 12.7%.

L333 says "we report every configuration we ran", so it belongs in L288 or Table VI. It does not change the conclusion, since it is still poor transfer.

**E6. Per-class wording for the no-port ablation (L117).** For the E-SNN, the largest per-class moves are FTP-BruteForce (−0.196) and SlowHTTPTest (+0.265). They largely cancel. Say: "the consistent losses are on Slowloris, Web Attacks and Bot; the two label-conflicted classes move erratically."

**E7. The Holm family is under-specified (L167).** "Holm over the four" is applied separately within each (metric, τ) family, which makes 4 families of 4 tests. State this, or apply Holm across all 16 tests. The XGBoost result survives either way.

**E8. Repository artefact (not the paper).** `results/analysis/seed_stats_5seed_table.md` has two errors:
- The "Per-model seeds" block is headed *T = 12* but holds the T = 4 five-seed values.
- The TOST and exploratory tables compare models with themselves ("T4:esnn vs T4:esnn, diff 0, equivalent: yes").

This is a script bug in `seed_stats.py` when one summary is passed. The paper does not use these rows; L253 correctly uses the 3-seed CI. Fix it before release, because a reader of the repository will find "equivalent: yes" next to a zero difference.

**E9. Small text points.**
- L333, grammar: "tree hyperparameters were fixed, and screened only five SNN variants" → "… fixed, and we screened only five …".
- L129: the E-SNN and Enc-ANN T = 4 seeds 42–44 also reproduce the v4 run, not just the MLP and XGBoost. Say so; it supports the determinism claim.
- L125: say whether the 16 PLE bins are quantile or uniform on the already quantile-scaled inputs.

---

## 3. Ranked fixes (largest score effect first)

### Text only

1. **Rewrite the encoding-vs-dynamics claim (E1)** at L21, L38, L167 and L327:
   - "not distinguishable" instead of "matches";
   - dynamics argued from E-SNN vs Enc-ANN;
   - fusion architecture named as an open confound.

   This is the single most important fix, because the abstract's central sentence currently says more than the data support. **+0.3–0.5**
2. **Unify the T = 4 numbers (E3)** and **align the energy Discussion with Table V (E4)**: SRAM and INT8 nuance, one like-for-like baseline. **+0.2**
3. **Report the no-port Enc-ANN transfer row (E5)** and fix the per-class wording (E6). **+0.1**
4. **Specify the Holm families (E7)** and fix the E9 nits. **+0.05**

### CPU (existing records, under 30 minutes)

5. **Regenerate Fig. 2(b)** with the complete test-mix energy model (E2). **+0.2**
6. **Add equivalence and encoding tests from `summary.json`:**
   - TOST (e.g. margin 2 points) for E-SNN vs PLE-MLP and E-SNN vs Enc-ANN on the five seeds;
   - Enc-ANN − MLP and Enc-ANN − PLE-MLP as declared exploratory tests.

   This turns "matches" into either an equivalence result or an honest "inconclusive". **+0.2–0.3**
7. **Fix the self-comparison bug** in `seed_stats.py` and the mislabelled header (E8). **+0** for the paper, but needed for a credible release.

### GPU (Kaggle retraining)

8. **Separate encoding from fusion.** Train a three-branch PLE ensemble with the same fusion head, or single-branch Enc-ANN variants, at T = 4 with 5 seeds. This decides whether "the encoding carries the benefit" or "the ensemble carries the benefit", which is the paper's own question. **+0.5**
9. **Measure partition variance.** Train 2–3 additional split seeds for E-SNN, Enc-ANN, MLP, PLE-MLP and XGBoost at T = 4. Alternatively, save per-row test predictions so that the declined group bootstrap becomes possible. The FTP/SlowHTTPTest group placement (L196) makes split variance the main unquantified uncertainty. **+0.3–0.5**
10. *(Optional, beyond conference scope.)* Transfer on the full or corrected CIC-IDS2017 release, or a packet-level SNN where time steps are real time. **+0.2** at this venue.

**Expected path.** Items 1–7 (text and CPU, about a day) would take the paper to about 7.5. Adding items 8 and 9 would take it to 8, provided the null result holds.
