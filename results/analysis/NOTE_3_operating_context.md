# Item 3: operating-point context from the records

Script: `scripts/analysis/operating_context.py`. Outputs: `results/analysis/operating_context.json`, `results/analysis/operating_context_table.md`.
All values are from the run records (T = 12 unless stated, mean over three seeds).

## Per-day test FPR at the 5% budget

The pooled 5% is an average over very different days. 2018-02-20 holds 55% of the benign test rows and sits near 4 to 6%. The two Infiltration days are far above the budget:

| Day | benign rows | E-SNN | ANN | Enc-ANN | RF | CatBoost | XGB |
|---|---|---|---|---|---|---|---|
| 2018-02-28 | 109,503 | 0.241 | 0.240 | 0.288 | 0.294 | 0.290 | 0.323 |
| 2018-03-01 | 47,378 | 0.175 | 0.151 | 0.256 | 0.288 | 0.266 | 0.316 |
| 2018-02-20 | 1,476,420 | 0.057 | 0.061 | 0.048 | 0.042 | 0.047 | 0.042 |
| lowest day (02-21) | 71,924 | 0.001 | 0.001 | 0.001 | 0.001 | 0.001 | 0.000 |

Per-day range (seed means): E-SNN 0.1% to 24.1%; matched ANN 0.0% to 24.0%; Enc-ANN 0.1% to 28.8%; RF 0.1% to 29.4%; CatBoost 0.0% to 29.0%; XGBoost 0.0% to 32.3%. Any single seed: E-SNN up to 24.7%, XGBoost up to 32.4%. T = 4 and T = 8 E-SNN: 0.1% to 24.7% and 0.1% to 24.5%.

## Decision ablation at tau = 5% (each rule gets its own 5% threshold)

| Model | raw logits | prior offset only | full (prior + temperature) |
|---|---|---|---|
| E-SNN | 0.745 | 0.769 | 0.769 |
| Matched ANN | 0.747 | 0.756 | 0.756 |
| Enc-ANN | 0.767 | 0.787 | 0.787 |
| Random forest | 0.762 | 0.788 | 0.788 |
| CatBoost | 0.765 | 0.791 | 0.791 |
| XGBoost | 0.788 | 0.808 | 0.808 |

(13-class macro-F1; 11-class in the JSON.) The prior offset adds 0.9 to 2.6 points; temperature adds nothing measurable (fitted T between 0.96 and 1.01; probability-calibration NLL changes in the fourth decimal, e.g. E-SNN 0.0521 to 0.0521). FPR and ADR are unchanged by construction.

## Argmax operating point (no alarm threshold)

| Model | prior-corrected argmax FPR | ADR | MF1-13 | MF1-11 | uncorrected argmax FPR | MF1-13 |
|---|---|---|---|---|---|---|
| E-SNN | 0.0012 | 0.941 | 0.788 ± 0.009 | 0.859 | 0.0051 | 0.789 |
| Matched ANN | 0.0009 | 0.938 | 0.785 ± 0.005 | 0.856 | 0.0057 | 0.770 |
| Enc-ANN | 0.0008 | 0.941 | 0.808 ± 0.010 | 0.873 | 0.0055 | 0.807 |
| Random forest | 0.0014 | 0.915 | 0.769 ± 0.005 | 0.873 | 0.0048 | 0.799 |
| CatBoost | 0.0002 | 0.938 | 0.808 ± 0.002 | 0.862 | 0.0047 | 0.831 |
| XGBoost | 0.0008 | 0.941 | 0.836 ± 0.006 | 0.890 | 0.0058 | 0.819 |

The models' natural operating point is at an FPR of 0.02% to 0.14%, 35 to 250 times below the 5% budget, with higher 13-class macro-F1 than at 5% for every model except random forest.

## Probabilistic quality (test partition, after calibration)

| Model | test NLL | test Brier | binary AP | standardized pAUC at 1% FPR |
|---|---|---|---|---|
| E-SNN | 0.0520 | 0.0226 | 0.975 | 0.973 |
| Matched ANN | 0.0532 | 0.0233 | 0.975 | 0.973 |
| Enc-ANN | 0.0482 | 0.0213 | 0.979 | 0.975 |
| Random forest | 0.0562 | 0.0249 | 0.979 | 0.970 |
| CatBoost | 0.0482 | 0.0213 | 0.980 | 0.975 |
| XGBoost | 0.0459 | 0.0208 | 0.981 | 0.975 |

ECE is not in the records and needs per-row test probabilities (only on Kaggle). NLL before calibration on the test set is not stored; the probability-calibration partition NLL before and after temperature is (`calibration.json`).

## Missed attacks

At 5%, 99.4% (E-SNN) to 99.9% (CatBoost) of missed attack flows are Infiltration (E-SNN: 21,508 of 21,621). Same at 1% and 10%.

## Ranking across budgets (13-class)

- 1%: XGBoost 0.848 > CatBoost 0.838 > RF 0.824 > Enc-ANN 0.816 > E-SNN 0.789 > ANN 0.771 (same order as 5%).
- 5%: XGBoost 0.808 > CatBoost 0.791 > RF 0.788 > Enc-ANN 0.787 > E-SNN 0.769 > ANN 0.756.
- 10%: XGBoost 0.801 > CatBoost 0.782 > **Enc-ANN 0.767 > RF 0.763** > E-SNN 0.754 > ANN 0.748. The order is not the same.

## LaTeX-ready sentences

- The pooled false-alarm rate hides large differences between capture days. At the 5\% budget the E-SNN's per-day test FPR ranges from 0.1\% (2018-02-21) to 24.1\% (2018-02-28), and XGBoost's from below 0.1\% to 32.3\%; the two Infiltration days (02-28 and 03-01) are above 15\% for every model.
- Prior correction accounts for the whole calibration effect: it raises the E-SNN's macro-F1 at the 5\% budget from 0.745 (raw logits) to 0.769, while the fitted temperatures lie between 0.96 and 1.01 and change neither the threshold nor macro-F1.
- Without an alarm threshold, the prior-corrected argmax decision operates at an FPR of 0.02\% to 0.14\% and gives higher macro-F1 than the 5\% budget for every model except random forest (E-SNN $0.788$, Enc-ANN $0.808$, XGBoost $0.836$).
- More than 99\% of the attack flows missed at the 5\% budget are Infiltration.
- The ranking holds at the 1\% budget but not at 10\%, where Enc-ANN (0.767) is above random forest (0.763).

## What changes in the paper

- "The ranking holds at the other budgets" is false at 10% (Enc-ANN above RF).
- "The budget transfers well from calibration to test" holds only for the pooled FPR; per-day FPR is 0.1% to 24% for the E-SNN.
- The keyword "calibration" is mostly prior correction; temperature scaling is near 1 for all models.
