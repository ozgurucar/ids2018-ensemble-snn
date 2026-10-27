# Dst Port ablation (v5 noport_T4)

Script: `scripts/analysis/noport.py ~/.cache/ids-x17/combine.csv`. Outputs: `results/analysis/noport.json`, `results/analysis/noport_table.md`, log `results/analysis/noport.log`. Kaggle records (summary, manifest, seed-42 calibration files, no checkpoints) copied to `results/v5/noport/`.
The no-port models use the same partitions and preprocessor (sha256 8ef45cb2..., identical to `app/models/preprocessor.joblib`) and the 69 remaining preprocessed columns. With-port references: E-SNN and Enc-ANN at T = 4 (`results/v4/steps/summary_T4.json`) and XGBoost from v3 (trees do not depend on T). Diff = without port minus with port; Holm over the three models within each (metric, tau).

## In-distribution (three seeds)

| Model | MF1-13 @5% with / without | diff, Welch p (Holm) | MF1-11 @5% with / without | diff, Welch p (Holm) | ADR @5% with / without |
|---|---|---|---|---|---|
| E-SNN, T = 4 | 0.766 / 0.754 | -1.2, 0.31 (0.63) | 0.828 / 0.808 | -2.0, 0.19 (0.19) | 0.959 / 0.960 |
| Enc-ANN, T = 4 | 0.787 / 0.776 | -1.2, 0.47 (0.63) | 0.844 / 0.815 | -2.9, 0.083 (0.17); paired 0.053 | 0.961 / 0.962 |
| XGBoost | 0.808 / 0.799 | -1.0, 0.083 (0.25) | 0.858 / 0.847 | -1.2, 0.001 (0.002) | 0.967 / 0.966 |

At 1%: MF1-13 changes by +0.8 (E-SNN), +0.2 (Enc-ANN) and -1.2 (XGBoost, p = 0.035, Holm 0.11) points; MF1-11 by +0.3, -1.3 and -1.4 (XGBoost Holm < 0.001).
The ranking is unchanged without the port: XGBoost 0.799 > Enc-ANN 0.776 > E-SNN 0.754 (13-class, 5%).
Seed spread of the no-port E-SNN is much smaller (s.d. 0.002 vs 0.015), so the E-SNN means are less noisy than with the port.

Per-class F1 at 5% (without minus with port): DoS-Slowloris -0.116 / -0.151 / -0.074 (E-SNN / Enc-ANN / XGBoost); Web Attacks -0.085 / -0.167 / -0.036; Bot -0.023 / -0.021 / -0.010. The label-conflicted classes move erratically for the neural models (SlowHTTPTest +0.265 / +0.133, FTP-BruteForce -0.196 / +0.038), as expected for classes decided by the partition draw. All other classes move by less than 0.03.

## CIC-IDS2017 transfer (seed 42, protocol of scripts/cross_dataset_cic2017.py)

| Model | FAR, 2018 threshold | DR, 2018 threshold | DR after benign-only recal. to 5% | ROC AUC |
|---|---|---|---|---|
| E-SNN T=4, with port | 0.228 | 0.420 | 0.239 | 0.544 |
| E-SNN T=4, without port | 0.178 | 0.314 | 0.135 | 0.467 |
| XGBoost, with port | 0.252 | 0.494 | 0.317 | 0.660 |
| XGBoost, without port | 0.219 | 0.350 | 0.310 | 0.544 |
| Enc-ANN T=4, without port | 0.127 | 0.601 | 0.344 | 0.686 |

The with-port Enc-ANN T = 4 has no calibration record locally, so it is not in the transfer comparison. The with-port rows reproduce `results/cross_dataset/cic2017.json` (differences of 4e-6 or less, caused only by the 3-decimal rounding of scores in the detector API).

Per attack after recalibration, the with-port E-SNN's good transfer on slow DoS depended on the port: GoldenEye 99.8% -> 32.5%, Slowloris 99.6% -> 68.8%. XGBoost loses Bot (60.8% -> 2.8%) and Slowloris (96.4% -> 12.2%) without the port but gains PortScan (49.7% -> 60.5%).

## Is Dst Port a shortcut?

- In-distribution: a small one. Removing it costs about 1 point of 13-class macro-F1 for every model (significant only for XGBoost on the 11-class metric), leaves ADR unchanged to 0.1 point, and does not change the ranking. The loss concentrates on Slowloris, Web Attacks and Bot.
- In transfer: the port is not what makes transfer fail. Without it the false-alarm rate at the 2018 threshold drops only from 23% to 18% (E-SNN) and from 25% to 22% (XGBoost), and detection after recalibration gets worse (E-SNN 23.9% -> 13.5%) or stays the same (XGBoost 31.7% -> 31.0%). The ROC AUC on 2017 falls (0.54 -> 0.47 and 0.66 -> 0.54), so the port carried signal that transfers. In particular, the earlier claim that slow application-layer DoS transfers well was mostly a port effect.

## Sentences for the paper

- Destination port is an input to every model. Retraining without it (three seeds, same partitions) lowers 13-class macro-F1 at the 5\% budget by about one point for each model (E-SNN at $T = 4$: $0.766 \to 0.754$; Enc-ANN: $0.787 \to 0.776$; XGBoost: $0.808 \to 0.799$), leaves the attack detection rate unchanged within 0.1 points and keeps the ranking of the models.
- The loss is concentrated in DoS-Slowloris (F1 lower by 0.07 to 0.15), Web Attacks (0.04 to 0.17) and Bot (0.01 to 0.02), the classes for which the destination port identifies the attacked service in this testbed.
- On CIC-IDS2017 the port-free models do not transfer better. With the 2018 threshold their false-alarm rate is still 18\% (E-SNN) and 22\% (XGBoost), and after recalibration to a 5\% budget they detect 13.5\% and 31.0\% of attack flows, against 23.9\% and 31.7\% with the port.
- The good transfer of the slow application-layer DoS attacks in Table~\ref{tab:transfer} depends on the destination port: without it the 4-step E-SNN flags 32.5\% of GoldenEye and 68.8\% of Slowloris flows instead of 99.8\% and 99.6\%.

## Consequences for the paper

- Disclose Dst Port (and Protocol) as inputs; the ablation supports keeping the with-port models as primary, since the in-distribution effect is about 1 point and the conclusions do not change.
- Sec. V-F "Only the slow application-layer DoS attacks transfer well" should add that this relies on the destination port.
- The transfer failure is not explained by the port shortcut; together with the transfer checks in NOTE_6 it points to network and extractor-version shift.
