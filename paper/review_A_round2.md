# Review A, Round 2 (cross-review of B and C)

## 1. Agreement and disagreement

**With B (novelty, 5/10).**
- *Agree on M2 (n = 3).* My Welch p-values (0.33 vs Enc-ANN, 0.40 vs matched ANN) quantify it.
- *Agree on M3 (binned/PLE MLP baseline).* It is the right test of "encoding vs dynamics"; make it a must-fix.
- *Agree on M4 (error-floor logic).* Identical vectors cannot be separated even by memorisation, so an error below the floor signals different labels or preprocessing, not leakage. I adopt B's framing.
- *Agree on M5 and M6.* The incomplete 2017 copy strengthens my M8. B's M6 overlaps my M7, which adds that the temperature is fitted on 100k *labelled* 2017 flows.
- *Agree on M1 and M8* (missing transfer and energy literature).
- *Partial disagreement on M7 (retitle).* Retitle, but use "duplicate-controlled" rather than "leakage-controlled", since episode-level leakage remains (my M4).

**With C (presentation, 6/10).**
- *Agree on all presentation points* (abstract, uncited figures, terminology, training details, Eq. (1), CatBoost).
- *Disagree on C's proposed abstract.* It keeps "It beats a parameter-matched multilayer perceptron" and "Attack detection rates differ by less than one point". The first is not supported (M1). The second is near-tautological at 5% FAR, because the misses are almost all Infiltration (my M5).
- *Disagree on C's minor 13.* The proposed rewrite "row-level accuracy above 98.9% indicates leakage" repeats the logical slip B identified.
- *C's reproducibility run* reproduces the energy table and figures and measures 15,695 flows/s. C's minor 24 (Enc-ANN with SRAM, 0.39–0.52 µJ) supports "control is cheaper" under a hardware-style model.

## 2. My own points: dropped or downgraded

- **Minor 5 (CPU timing): downgrade to cosmetic.** C's measurement confirms >15k flows/s. Only the v3/v4 discrepancy needs a footnote.
- **Minor 8 (error floor): replace with B's M4 wording.**
- **M6 (45 nm sign flip): keep, but soften.** The LayerNorm cost (0.127 µJ at T = 12) is in the authors' record; my membrane-update charge is an assumption. Robust claim: with the E-SNN's own LayerNorm, the T = 12 advantage disappears.
- **M4 (episode leakage): a [TEXT] fix is acceptable for a conference.** With unverified timestamps, a time-blocked split is a stretch goal.
- **M3 (identifiable-class metric): top priority.** Neither B nor C raises it, and it changes the ranking (E-SNN–RF gap 1.9 → 0.5 points; Enc-ANN rises above RF and CatBoost).

## 3. Joint ranked must-fix list for 8+

Impact = estimated score gain if done well. Locally there are only seed-42 checkpoints, four raw 2018 days and the 2017 CSV; the 2018 test arrays are not local, so group-bootstrap needs Kaggle.

1. **[CPU]** Report macro-F1 over identifiable classes (excluding or merging FTP-BF and SlowHTTPTest) as primary, with 13-class as secondary. Recompute from `summary.json` per-class records. Add CatBoost to Table V. **+1.0**
2. **[TEXT]** Make the claims match the statistics. Add per-seed values and Welch/paired tests for the 2–3 pre-declared comparisons with Holm correction. Replace "beats", "above", "below" and "indistinguishable" with "no detectable difference at n = 3". Soften the mechanism claim per B's wording. **+0.75**
3. **[GPU]** Train ≥10 seeds for E-SNN, Enc-ANN and matched MLP (T = 4 and 12), plus a quantile-bin / piecewise-linear MLP baseline (B M3). **+1.0**
4. **[TEXT]** Disclose Dst Port and Protocol as inputs. **[CPU]** Run a 2017 inference sensitivity check with Dst Port neutralised (constant or permuted) for the three frozen models. **[GPU]** Retrain without Dst Port (3 seeds, E-SNN, Enc-ANN, XGB). **+0.5 (TEXT+CPU), +0.75 with GPU**
5. **[CPU]** Make the energy model consistent:
   - include the E-SNN's LayerNorm (and state any membrane-update assumption) in the 45 nm model;
   - use one ANN figure (0.398 µJ);
   - add the INT8 MLP row and Enc-ANN rows under SRAM/Loihi-style costs (C minor 24);
   - recount ops on a benign-heavy sample;
   - fix "69%" and "17% below".
   **+0.5**
6. **[CPU]** Rerun `finetune_cic2017.py` with the temperature fitted on the label budget only (or with labels counted), and report DR at matched FAR. Label the setting "same-capture re-split" in the abstract (B M6). **+0.5**
7. **[TEXT]** Report the operating-point context:
   - per-day FPR range (0.1%–23% for the E-SNN, already in the records);
   - ADR excluding Infiltration;
   - the argmax point (FPR ~0.1–0.2%, higher macro-F1);
   - NLL/Brier before and after calibration.

   All are already in `summary.json`. **+0.5**
8. **[TEXT]** Reposition against the literature:
   - D'hooge ×2, Cantone and Apruzzese for transfer;
   - Liu and Flood for the FTP/SlowHTTP audit;
   - Gorishniy for encodings;
   - the corrected error-floor logic (B M4);
   - "duplicate-controlled" in the title;
   - an episode-leakage limitation.
   **+0.5**
9. **[CPU]** Rerun the transfer with name-based column mapping on the *complete* 2017 MachineLearningCVE (B M5), plus a per-feature KS shift table. Inference only. **+0.25**
10. **[TEXT]** Presentation package (C):
    - abstract ≤250 words;
    - cite Figs. 1–2;
    - reorder Section V and merge Table VI into Table III;
    - unify terminology;
    - add a training-details paragraph;
    - make Eq. (1) explicit;
    - fix the numeric mismatches: LOIC-UDP caption, the "ranking holds at 10%" claim, FAR 0.052, and 27% vs 23.9%.

    Also fix the README install/test steps. **+0.5**
11. **[GPU]** *(Stretch.)* A time-blocked or episode-held-out 2018 split, or a near-duplicate NN-distance audit on the full data. **+0.5**

**Path to 8:** the TEXT/CPU items (1, 2, 4, 5, 6, 7, 8, 10) reach about 7; item 3 (GPU) secures 8; items 9 and 11 push toward 8.5.
