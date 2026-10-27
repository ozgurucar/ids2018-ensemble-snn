# Local adaptation on CIC-IDS2017

Script: `scripts/finetune_cic2017.py` (run: `python scripts/finetune_cic2017.py ~/.cache/ids-x17/combine.csv results/cross_dataset/finetune_cic2017.json --seeds 42 43 44`).
Raw results: `finetune_cic2017.json` (`summary` = flat per-run list, `runs` = full records incl. per-label alarm rates and budget class counts), log: `finetune_cic2017.log`.
Run time: 438 s wall clock on CPU (10-core Mac, 8 threads) for everything below, including data loading (25 s).

## Protocol (leakage control)

- Data: CIC-IDS2017 MachineLearningCVE `combine.csv`, 2,214,468 flows, loaded with `load()` from `cross_dataset_cic2017.py` (2018 column names, Protocol imputed from destination port). This export has no FTP-Patator, SSH-Patator or Web Attack rows.
- Split: label-blind feature-fingerprint groups (`idsresearch.groups.fingerprint`, 1,941,979 groups; identical feature vectors stay together) into adaptation pool / calibration / test = 50/10/40, split seed 2017. Test: 671,643 benign + 220,113 attack flows, all used (no benign subsampling).
- Budgets: proportional class-stratified samples of the pool only, at least one flow per class present in the pool, a different sample per seed. Sizes: 0.1% = 1,101 flows, 1% = 11,026, 5% = 55,153 (class counts per run are in the JSON; e.g. 0.1% = 835 benign, 112 Hulk, 79 PortScan, 64 DDoS, 5 GoldenEye, 2 SlowHTTPTest, 2 Slowloris, 1 Bot, 1 Infiltration).
- Label space: the 13 CSE-CIC-IDS2018 classes plus PortScan as a 14th class. Heartbleed (11 flows, 5 in test) has no class: never trained on, excluded from macro-F1, counted as an attack in DR.
- Methods:
  - `frozen_recal`: frozen 2018 model, 2018 prior offset and temperature, only the 5% threshold refitted on 2017 benign calibration flows (budget 0, no attack labels).
  - `esnn_t4_finetune`: E-SNN T=4 from `app/models/esnn_t4.pt`, all layers trained, readouts/meta-head extended by a zero-initialised PortScan output, frozen 2018 preprocessor, AdamW lr 1e-4, wd 1e-3, batch 256, unweighted CE, fixed schedule max(5 epochs, 300 steps) (0.1%: 60 epochs = 300 steps; 1%: 7 epochs; 5%: 5 epochs). No early stopping or model selection.
  - `xgb_scratch`: XGBoost trained only on the budget, 2018 hyperparameters (400 trees, depth 8, lr 0.1, subsample/colsample 0.8), same preprocessed features.
  - `xgb_continue`: 2018 XGBoost booster + 100 extra rounds on the budget. The booster is fixed to 13 classes, so PortScan rows are dropped from its training data.
- Decision rule refit exactly as `idsresearch/decision.py` / `evaluation_v3.py`: calibration partition split 50/50 by groups; prior offset via `prior_offset(budget, budget)` (0 for classes in the budget, masked for classes absent from it); temperature fitted on up to 100k rows of the probability half (labelled, restricted to classes the model was trained on); threshold = empirical 5% benign order statistic on the alarm half.
- Nothing (lr, epochs, rounds, thresholds) was chosen with test rows. Schedules were fixed before the full run; one smoke run (seed 42, 0.1%) was used only to check the code ran.

## Results (2017 test partition, mean ± sd over seeds 42, 43, 44)

DR = share of all attack flows that raise an alarm; DR\PS = same without PortScan; macro-F1 over the 9 classes present in test (Benign + 7 2018 families + PortScan), prediction = most likely attack class if alarm else Benign.

| Method | Budget (flows) | FAR | DR | DR\PS | Macro-F1 |
|---|---|---|---|---|---|
| Frozen E-SNN T=4, recal. threshold | 0 | 0.062 | 0.268 | 0.278 | 0.188 |
| Frozen XGBoost, recal. threshold | 0 | 0.050 | 0.314 | 0.237 | 0.291 |
| E-SNN T=4 fine-tuned | 0.1% (1,101) | 0.053 ± 0.002 | 0.985 ± 0.003 | 0.982 ± 0.004 | 0.564 ± 0.007 |
| XGBoost from scratch | 0.1% (1,101) | 0.050 ± 0.001 | 0.996 ± 0.000 | 0.996 ± 0.001 | 0.526 ± 0.011 |
| XGBoost continued | 0.1% (1,101) | 0.051 ± 0.001 | 0.723 ± 0.015 | 0.993 ± 0.004 | 0.510 ± 0.008 |
| E-SNN T=4 fine-tuned | 1% (11,026) | 0.059 ± 0.006 | 0.994 ± 0.001 | 0.993 ± 0.001 | 0.592 ± 0.005 |
| XGBoost from scratch | 1% (11,026) | 0.050 ± 0.001 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.665 ± 0.005 |
| XGBoost continued | 1% (11,026) | 0.050 ± 0.001 | 0.724 ± 0.010 | 0.999 ± 0.001 | 0.494 ± 0.007 |
| E-SNN T=4 fine-tuned | 5% (55,153) | 0.053 ± 0.001 | 0.996 ± 0.000 | 0.995 ± 0.000 | 0.707 ± 0.002 |
| XGBoost from scratch | 5% (55,153) | 0.051 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.686 ± 0.016 |
| XGBoost continued | 5% (55,153) | 0.057 ± 0.006 | 0.749 ± 0.033 | 0.991 ± 0.004 | 0.483 ± 0.054 |

Per-attack alarm rate (mean over seeds; test n in brackets):

| Method, budget | Bot (799) | DDoS (51,236) | GoldenEye (4,056) | Hulk (95,572) | SlowHTTPTest (2,212) | Slowloris (2,365) | Infiltration (16) | PortScan (63,852) |
|---|---|---|---|---|---|---|---|---|
| Frozen E-SNN T=4 | 0.000 | 0.004 | 0.999 | 0.375 | 0.415 | 0.995 | 0.000 | 0.244 |
| Frozen XGBoost | 0.596 | 0.174 | 0.288 | 0.250 | 0.165 | 0.965 | 0.000 | 0.502 |
| E-SNN FT 0.1% | 0.000 | 0.994 | 0.992 | 0.991 | 0.654 | 0.979 | 0.062 | 0.993 |
| XGB scratch 0.1% | 0.435 | 0.999 | 1.000 | 1.000 | 0.941 | 0.988 | 0.542 | 0.998 |
| XGB cont. 0.1% | 0.711 | 0.999 | 1.000 | 1.000 | 0.642 | 0.996 | 0.417 | 0.063 |
| E-SNN FT 1% | 0.000 | 0.999 | 0.995 | 0.999 | 0.993 | 0.979 | 0.062 | 0.996 |
| XGB scratch 1% | 0.971 | 1.000 | 0.999 | 1.000 | 1.000 | 1.000 | 0.667 | 1.000 |
| XGB cont. 1% | 0.953 | 1.000 | 0.986 | 1.000 | 0.988 | 0.989 | 0.417 | 0.050 |
| E-SNN FT 5% | 0.319 | 0.999 | 0.996 | 0.999 | 0.997 | 0.998 | 0.062 | 0.997 |
| XGB scratch 5% | 0.995 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.708 | 1.000 |
| XGB cont. 5% | 0.630 | 0.994 | 0.990 | 0.997 | 0.937 | 0.865 | 0.062 | 0.156 |

## Caveats

1. **Optimistic, in-capture adaptation.** Pool, calibration and test come from the same capture days and the same attack episodes; only exact duplicate feature vectors are kept apart. Near-duplicate flows of one attack run appear on both sides. A real operator would label earlier traffic and face later traffic, so these numbers are an upper bound on what local labels buy.
2. **Macro-F1 is low for every method** because 5% FAR on 671k benign test flows is about 33k false alarms, which are spread over attack classes and destroy precision for small classes (Bot 799, Infiltration 16, SlowHTTPTest/Slowloris ~2k). The binary DR/FAR numbers are the more meaningful ones here.
3. **FAR is not exactly 5% on test.** The threshold is set on calibration benign flows; on test the frozen E-SNN gives 6.2%, and the 1% E-SNN fine-tune 5.3% to 6.3% depending on seed. XGBoost-from-scratch stays at 4.9% to 5.1%.
4. **The calibration partition uses labels.** Temperature is fitted on up to 100k labelled calibration flows (as in the 2018 pipeline). This is extra labelled local data beyond the budget, although the threshold itself uses benign flows only and temperature changes the alarm ranking only slightly.
5. `xgb_continue` cannot learn PortScan (fixed 13-class booster), which explains its 72% to 75% DR; without PortScan it is at 99%. It also got worse with more data at 5% (more FAR and DR variance), probably because 100 extra rounds on a small set overfit; this was not tuned.
6. E-SNN schedule, lr and XGBoost settings were fixed a priori, not tuned; a tuned E-SNN might close the Bot gap. Bot has only 1, 9 and 48 labelled flows at the three budgets, and Infiltration exactly one flow at every budget, so these per-class numbers are noisy. Heartbleed (5 test flows) and Infiltration (16) are too small to interpret.
7. The frozen baseline here (recal. threshold on 2017 calibration benign, evaluated on the 40% test partition) differs slightly from Table `tab:transfer` in the paper (threshold on half of all 2017 benign flows), e.g. E-SNN T=4 DR 0.268 vs 0.239, XGBoost 0.314 vs 0.317.
8. The 2017 export lacks the Tuesday and Thursday files, so FTP/SSH brute force and web attacks are not tested. Protocol is imputed.

## Paragraph for the paper (LaTeX-ready, about 190 words)

To ask how much local labelled data an operator would need, we split the CIC-IDS2017 flows by feature-vector fingerprint into an adaptation pool, a calibration partition and a test partition (50/10/40), drew class-stratified labelled samples of 0.1\%, 1\% and 5\% of the pool (1{,}101, 11{,}026 and 55{,}153 flows), and refitted the temperature and the 5\% alarm threshold on the 2017 calibration partition. PortScan was added as a new class. Table~\ref{tab:adapt} gives means over three seeds. Labels recover detection quickly. With only 1{,}101 labelled flows, fine-tuning the 4-step E-SNN from its 2018 checkpoint raises detection from 27\% to 98.5\% at a 5.3\% false-alarm rate, and XGBoost trained from scratch on the same flows reaches 99.6\% at 5.0\%. The fine-tuned E-SNN matches XGBoost on the DoS, DDoS and PortScan traffic but not on Bot flows, which it misses with 0.1\% and 1\% of the pool and detects at 32\% with 5\%, while XGBoost detects 97\% to 99.5\% with 1\% or more. Continuing the 2018 XGBoost model cannot learn PortScan and stays at 72\% to 75\% detection. Because pool and test come from the same capture days, these figures are an optimistic bound for a real deployment.
