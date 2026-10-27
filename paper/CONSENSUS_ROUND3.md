# Round 3 consensus (reviewers A, B, C)

All three reviewers scored 7/10 (A 7, B 7, C 7; up from 5/5/6 in round 1).
A and C state that the text and CPU fixes below take the paper to 8; B puts them at 7.5 and asks for a fusion-matched control for a firm 8.

## Agreed fixes (raised by two or more reviewers)

1. Encoding claim (A2, B1, C1). "PLE-MLP matches the SNN" was stated without an equivalence test, and "the gain comes from the encoding" was stated although E-SNN vs MLP is not significant. Now tested (results/analysis/seed_stats_5seed_table.md, Welch TOST, margin 2 points):
   - E-SNN vs PLE-MLP is equivalent within 2 points at tau = 5% (13-class p = 0.020; 11-class p = 0.031). It is not shown at 1%.
   - Enc-ANN minus MLP is +2.4 points at 5% and +3.7 points at 1%; the 90% CI excludes 0 (exploratory, unadjusted).
   - Enc-ANN minus PLE-MLP is +1.8 to +2.2 points, so binning alone does not reproduce the Enc-ANN.
   Rewrite: no evidence that spiking dynamics add accuracy; the E-SNN is equivalent to a spike-free PLE-MLP within 2 points at 5%; the best neural model is the non-spiking Enc-ANN, which feeds the same spike codes to a dense network. State that the fusion architecture is not separated from the encoding (B3), and that PLE-MLP's width (~69 hidden units) comes from parameter matching (A5).
2. Fig. 2(b) contradicts Table V (A3, B2, C2). Regenerate it from results/analysis/energy_unified.json (complete model), and panel (a) from the 5-seed T=4 values. Fix the fonts.
3. Inconsistent numbers (A1, B4, C4):
   - Enc-ANN T=4 is 0.779 (5 seeds) vs 0.787 (3 seeds): label each.
   - Standard deviations: E-SNN 0.011, XGB 0.004.
   - 0.39 vs 0.40 µJ.
   - The "0.49–0.71" range should read 0.48.
   - The "2.5–22×" ratio mixes two MLP baselines; pick one.
   - "Every cost model" excludes the Enc-ANN on Loihi.
   - Kaggle slugs use broken \url.
   - Disclose that PLE-MLP was added to the declared family in round 3 and that the primary run moved to T=4 after review.
4. Port ablation is undersold (A4, B4):
   - Report the 11-class loss: 2.0 / 2.9 / 1.2 points.
   - Report the no-port Enc-ANN transfer row: DR 34.4%, AUC 0.686.
   - Abstract l.21: the transfer range "23–32% with or without port" is wrong.
5. Partition variance (A5, B5, C extra). Group bootstrap of DR, FAR and AUC from the per-row test scores (CPU) over fingerprint groups. Macro-F1 needs per-row class predictions, which were not saved, so its seed-only intervals stay a stated limitation.
6. Reproducibility (C3, C5):
   - README is still v3. Add v5, results/analysis and the scripts.
   - State which analyses need the local data or checkpoints.
   - The seed_stats bugs (self-comparisons, T=12 header, KeyError with --no-defaults in --help) are fixed in scripts/analysis/seed_stats.py.

## Declined, stated as limitations
- Fusion-matched PLE ensemble (B3): new GPU experiment; stated as an open confound.
- Second split seed (A5, B5): GPU retraining; partially covered by the group bootstrap.
