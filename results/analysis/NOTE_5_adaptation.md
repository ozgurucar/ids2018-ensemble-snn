# CIC-IDS2017 adaptation: label accounting and matched FAR

Script: `scripts/analysis/adapt_label_budget.py ~/.cache/ids-x17/combine.csv --seeds 42 43 44` (imports the unchanged training, budget and split code of `scripts/finetune_cic2017.py`; about 25 min on CPU), summary `scripts/analysis/adapt_summary.py`.
Outputs: `results/analysis/adapt_label_budget.json` (every run, variant and per-label alarm rate), `results/analysis/adapt_label_budget_summary.json`, `results/analysis/adapt_label_budget_table.md`, log `results/analysis/adapt_label_budget.log`.
The old `results/cross_dataset/finetune_cic2017.json` is untouched; the `orig` variant reproduces it (e.g. E-SNN fine-tuned at 0.1%: FAR 0.0531 / 0.0508 / 0.0536, DR 0.9849 / 0.9823 / 0.9889 per seed, identical to the log).

Decision-rule variants scored on the same trained models:
- orig: temperature on up to 100k labelled 2017 calibration flows (published setting);
- budget_T: temperature fitted on the labelled budget only;
- no_T: no temperature;
- strict: temperature and 5% threshold both from the labelled budget only.
All except strict also use 82,755 benign alarm-calibration flows that must be known to be clean but carry no attack labels.
Matched FAR: DR read off the test ROC at a test FAR of exactly 5% and 1% (oracle comparison view, not a deployable rule).

## Key numbers (means over three seeds)

| Method | Budget | Labelled flows (orig -> budget_T) | FAR | DR | DR @ test FAR 5% | DR @ test FAR 1% | Macro-F1 |
|---|---|---|---|---|---|---|---|
| E-SNN T=4, frozen | 0 | 0 | 0.062 | 0.268 | 0.248 | 0.149 | 0.188 |
| XGBoost, frozen | 0 | 0 | 0.050 | 0.314 | 0.314 | 0.259 | 0.291 |
| E-SNN T=4, fine-tuned | 0.1% | 101,100 -> 1,101 | 0.052 | 0.985 | 0.985 | 0.959 | 0.564 |
| XGBoost, scratch | 0.1% | 101,100 -> 1,101 | 0.050 | 0.996 | 0.996 | 0.990 | 0.532 |
| E-SNN T=4, fine-tuned | 1% | 111,025 -> 11,026 | 0.060 | 0.994 | 0.994 | 0.982 | 0.592 |
| XGBoost, scratch | 1% | 111,025 -> 11,026 | 0.050 | 1.000 | 1.000 | 0.999 | 0.670 |
| E-SNN T=4, fine-tuned | 5% | 155,152 -> 55,153 | 0.053 | 0.996 | 0.996 | 0.993 | 0.707 |
| XGBoost, scratch | 5% | 155,152 -> 55,153 | 0.051 | 1.000 | 1.000 | 1.000 | 0.686 |
| XGBoost, continued | 0.1% / 1% / 5% | budget only | 0.051 / 0.050 / 0.057 | 0.731 / 0.724 / 0.749 | 0.728 / 0.724 / 0.739 | 0.699 / 0.709 / 0.704 | 0.511 / 0.494 / 0.483 |

(Rows for fine-tuned and scratch models show budget_T; orig and no_T differ by at most 0.001 in DR and 0.006 in macro-F1.)

Findings:
1. The 100k labelled calibration flows bought nothing. Fitting the temperature on the budget alone, or not at all, leaves FAR and DR unchanged to the third decimal (macro-F1 within 0.006) for the fine-tuned E-SNN and XGBoost from scratch. The label count is therefore the budget itself (1,101 / 11,026 / 55,153), plus about 83k flows known to be benign for the threshold.
2. Strict (no benign calibration set, everything from the budget): DR is unchanged but the in-sample threshold overshoots the budget at 0.1% (test FAR 7.6% E-SNN, 7.2% XGBoost); at 1% and 5% FAR stays at 5.0 to 5.3%.
3. Matched FAR: the frozen E-SNN T=4 detects 24.8% (not 26.8%) at an exact 5% test FAR. At the 1% budget the fine-tuned E-SNN overshoots (6.0% FAR), but at an exact 5% test FAR its DR is the same, 99.4% vs 100.0% for XGBoost. The gap is clearer at 1% test FAR: 95.9% vs 99.0% with 1,101 labels, 98.2% vs 99.9% with 11,026.
4. Bot remains the failure: alarm rate 0.0 / 0.0 / 0.32 for the fine-tuned E-SNN against 0.42 / 0.97 / 0.995 for XGBoost from scratch.

## Sentences for the paper

- Fitting the temperature only on the labelled budget, or dropping it, changes no reported figure by more than 0.001 in detection rate, so the label count is the budget itself: 1{,}101, 11{,}026 and 55{,}153 flows, plus about 83{,}000 flows known to be benign for the alarm threshold.
- If even the threshold must come from the 1{,}101 labelled flows, detection is unchanged but the test false-alarm rate rises to 7.6\% (E-SNN) and 7.2\% (XGBoost).
- At an equal test false-alarm rate of 5\%, the fine-tuned E-SNN detects 98.5\% of attack flows with 1{,}101 labels against 99.6\% for XGBoost trained from scratch; at 1\% the figures are 95.9\% and 99.0\%.
- At an exact 5\% test false-alarm rate the frozen 4-step E-SNN detects 24.8\% of attacks, and frozen XGBoost 31.4\%.

## Consequences for the paper

- "About 1,100 labelled local flows" survives once stated precisely: 1,101 labels plus known-benign flows for the threshold; the 100k labelled calibration flows can be dropped (budget_T) without effect. Say which setting Table IX uses.
- "raises detection from 27%" (Sec. V-F text) vs 23.9% in Table VIII: on the adaptation test partition at matched 5% FAR the frozen E-SNN T=4 is 24.8%; the 26.8% figure is at a 6.2% FAR.
- The 1% E-SNN row (FAR 0.059) is no longer an unequal comparison problem: at matched FAR the DR is 0.994.
- Still same-capture re-split (pool, calibration and test from the same days and episodes); this rerun does not change that caveat.
