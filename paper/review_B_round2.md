# Review B, round 2 (cross-review of A and C)

## 1. Agreement and disagreement

**Where I agree with A, A is stronger than my own review:**
- **A-M1 (statistics).** The Welch tests show every E-SNN p-value is ≥ 0.08. This subsumes my M2.
- **A-M3 (two classes drive the ranking).** This is the most important finding across the three reviews. Without FTP-BF and SlowHTTPTest, the E-SNN–RF gap shrinks from 1.9 to 0.5 points, and Enc-ANN moves above RF and CatBoost. With my M4: the paper's own audit undercuts its headline metric.
- **A-M2 (Dst Port is an undisclosed input).** It is disqualifying for a "leakage-controlled" paper and also confounds transfer.
- **A-M7 (about 100k labelled calibration flows go uncounted).** This sharpens my M6: the "1,100 labels" claim is miscounted, not only optimistic.
- **A-M4 and A-M5.** "Duplicate-controlled" is the honest term. The per-day benign FAR of 23–32% on the Infiltration days is an in-distribution failure about as large as the transfer failure.
- **A-M6.** Adding LayerNorm and membrane updates flips the 45 nm energy sign at T = 12.

**Where I agree with C:** the abstract length, uncited figures, terminology drift, missing training details and README gaps. C-minor-24 shows the Enc-ANN Loihi/SRAM costs are already in `energy_loihi.json`, so my M8 sub-point becomes a text fix.

**Where I disagree:**
- **C's draft abstract** keeps three claims that A and I show are unsupported:
  - "beats the matched MLP" (p = 0.40);
  - "encoders carry the benefit" (not tested against a binning baseline);
  - "1,100 labels restore detection above 98%" (A-M7).

  Use the draft for its length, not its content.
- **C-minor-13** ("accuracy above 98.9% indicates leakage") repeats the slip from my M4. Leakage cannot separate identical vectors that carry conflicting labels. Beating the floor points to different labels, different preprocessing or a chance partition mix (A-minor-8).
- **A's 8+ bar** (≥10 seeds, split seeds, an episode-blocked split) is a journal bar. For an IEEE conference, 5 seeds plus a group bootstrap is enough, with episode leakage stated as a limitation and "duplicate-controlled" in the title.

## 2. My own points

- **M2:** merge into A-M1.
- **M5 (incomplete 2017 export):** downgrade to minor. A-M8 (extractor version, positional column mapping) and Dst Port are larger confounds.
- **M8:** keep the Dampfhoffer citation. The Enc-ANN costing becomes a [TEXT] fix.
- **M1, M3, M4, M7:** keep. A and C do not cover the prior-work repositioning or the binning baseline.

## 3. Joint ranked must-fix list

Tags:
- **[TEXT]**: a writing change only.
- **[CPU]**: local analysis under 30 minutes on existing data or checkpoints.
- **[GPU]**: Kaggle retraining.

Δ is my estimate of the score impact.

| # | Item | Tag | Δ |
|---|---|---|---|
| 1 | Make 11-class macro-F1 the primary metric (exclude or merge FTP-BF and SlowHTTPTest), with 13-class as secondary. A has already computed it. Add CatBoost to the per-class table. | CPU | +0.5 |
| 2 | Add paired per-seed differences, Holm-corrected tests on 3 pre-declared comparisons, and a group-bootstrap CI. This needs per-row predictions; seed-42 can be re-scored. Rewrite every "beats/below/indistinguishable". | CPU+TEXT | +0.5–0.8 |
| 3 | Reposition against prior work: D'hooge 2023 ×2, Cantone 2024, Apruzzese 2023, Flood 2024, Liu 2022 (FTP/SlowHTTP), Dampfhoffer 2023, Gorishniy 2022. Drop "most practically relevant finding". Frame the novelty as these controls applied to SNN-IDS plus the spike-input control. | TEXT | +0.5–0.8 |
| 4 | Disclose Dst Port and Protocol as inputs, and ablate Dst Port in-distribution and in transfer (E-SNN, Enc-ANN, XGB). XGB can run on CPU. | GPU | +0.5 |
| 5 | Abstract ≤250 words, "duplicate-controlled" in the title, contributions aligned with the findings, Docker moved out of the contributions. | TEXT | +0.5 |
| 6 | Add a binned or PLE MLP baseline with no spikes, so that "encoders, not dynamics" is tested rather than inferred. | GPU | +0.5 |
| 7 | Energy consistency: LayerNorm and membrane updates included at 45 nm, one ANN number, an INT8 row, Enc-ANN Loihi/SRAM rows from the JSON, and "69% less" removed from the abstract. | CPU+TEXT | +0.3–0.5 |
| 8 | Adaptation: fit the temperature on the label budget only, or count those labels. Report DR at matched FAR and macro-F1 next to the abstract claim. | CPU | +0.3 |
| 9 | Report per-day FAR, τ = 0.1% and 0.5%, the argmax point, ADR excluding Infiltration, and NLL/ECE. All are already in the records. | CPU | +0.3 |
| 10 | ≥5 seeds for E-SNN, Enc-ANN and MLP at T = 4 and T = 12. | GPU | +0.3 |
| 11 | Fix the error-floor sentence and the A-flagged mismatches (caption "nine"→"eight", τ = 10% ranking, 27% vs 23.9%, five partitions). Add a training-details paragraph, cite Figs. 1–2, and add a README reproduce block. | TEXT | +0.3 |
| 12 | Transfer hygiene: name-based column mapping, per-feature KS shift, the full or corrected 2017 export, and a test→train nearest-neighbour audit. | CPU | +0.2–0.3 |

**Trajectory.** The text and CPU items (1–3, 5, 7–9, 11) should take the score from 5 to about 6.5–7. Adding the GPU items (4, 6, 10) gets it to about 8 if the conclusions survive. If the E-SNN–Enc-ANN gap vanishes under items 1 and 2, the paper is still publishable as a clean negative result: spikes add nothing measurable over the encoding.
