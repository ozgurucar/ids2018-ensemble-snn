# Item 6: transfer hygiene (name-based mapping, KS shift)

Script: `scripts/analysis/transfer_hygiene.py ~/.cache/ids-x17/combine.csv`. Outputs: `results/analysis/transfer_hygiene.json`, `results/analysis/transfer_hygiene_table.md` (includes the full explicit 2017 to 2018 column map, suitable for an appendix or the repository).

## Name-based mapping

- An explicit 77-entry name map (2017 MachineLearningCVE header to 2018 header; Protocol is absent in 2017 and imputed from Dst Port as before) gives a feature frame that is bit-identical to the positional mapping of `scripts/cross_dataset_cic2017.py` (2,214,468 rows x 78 columns).
- The duplicated 2017 "Fwd Header Length" column is identical to the first copy in every row, so dropping it loses nothing.
- Re-scoring the three frozen detectors on the name-mapped frame reproduces `results/cross_dataset/cic2017.json` exactly (max absolute difference 0): FAR 0.262 / 0.228 / 0.252 and DR 0.630 / 0.420 / 0.494 with the 2018 threshold; recalibrated DR 0.230 / 0.239 / 0.317 (E-SNN T = 12, E-SNN T = 4, XGBoost).

## Per-feature KS shift (benign 2018 vs benign 2017)

Reference: 800,000 benign flows (200,000 per day) from the four raw 2018 days on disk (02-14, 02-15, 02-21, 03-02). The exact 2018 calibration partition cannot be rebuilt locally (group assignment depends on the global order of all ten days' fingerprints), so this approximates it. 2017: all 1,672,837 benign flows. KS is invariant to the monotone log and quantile transforms, so these are also the shifts of the model inputs.

Over the 70 model inputs: median KS 0.245; 15 features above 0.3. Top 10:

| Feature | KS | largest KS between two 2018 days | zero share 2018 / 2017 |
|---|---|---|---|
| Fwd Seg Size Min | 0.485 | 0.359 | 0.014 / 0.001 |
| Fwd Pkt Len Min | 0.403 | 0.343 | 0.77 / 0.36 |
| Pkt Len Min | 0.394 | 0.342 | 0.77 / 0.37 |
| Bwd IAT Min | 0.353 | 0.820 | 0.47 / 0.42 |
| Fwd IAT Tot | 0.351 | 0.528 | 0.22 / 0.24 |
| Fwd IAT Max | 0.351 | 0.522 | 0.22 / 0.24 |
| Fwd IAT Mean | 0.350 | 0.565 | 0.22 / 0.24 |
| Init Bwd Win Byts | 0.335 | 0.908 | 0.03 / 0.06 |
| Bwd Pkt Len Min | 0.330 | 0.342 | 0.77 / 0.44 |
| RST Flag Cnt | 0.324 | 0.931 | 0.68 / 1.00 |

Dst Port KS 0.291, Protocol 0.194.

Two observations matter for interpretation:

1. Extractor-version signatures. RST Flag Cnt and ECE Flag Cnt are zero in 99.97% of 2017 benign flows but only 68% of 2018 benign flows; minimum packet lengths are zero in 77% of 2018 flows against 36% to 44% in 2017; Init Bwd Win Byts has median -1 in 2017 and 149 in 2018. These look like differences in how the two CICFlowMeter versions compute the features, not only network differences.
2. Benign traffic in 2018 is itself very heterogeneous across days. Only 7 of the 70 inputs shift more between 2018 and 2017 than between the two most different 2018 days (median of that day-to-day maximum 0.63). Marginal shift therefore does not by itself explain the transfer failure; the 2017 benign flows mostly fall inside the range of 2018 days, but in combinations (and on the flag and minimum-length features) the models have not seen.

## LaTeX-ready sentences

- We map the CIC-IDS2017 columns to the CSE-CIC-IDS2018 names with an explicit table (released with the code); the result is identical to the positional mapping, and the duplicated 2017 header length column equals its first copy in every row.
- The largest per-feature shifts between 2018 and 2017 benign flows (two-sample KS 0.32 to 0.49) are in the minimum segment and packet lengths, the forward inter-arrival times, the initial backward window and the RST and ECE flag counts. The flag counts are zero in 99.97\% of 2017 flows but only in 68\% of 2018 flows, which points to a change in the flow extractor rather than in the network alone.
- 2018 benign traffic varies almost as much between capture days: only 7 of the 70 inputs shift more between the two datasets than between the two most different 2018 days, so we cannot attribute the transfer failure to network shift rather than to the extractor version and the destination-port input.

## What changes in the paper

- Sec. V-F "Its features match ours one to one": true by name, now verified; state the name map rather than a positional match.
- The transfer failure is confounded with an extractor-version shift (flag counts, minimum lengths, window bytes); the paper should say so (reviewer A, M8). A re-extracted, version-consistent 2017/2018 pair or the complete 2017 export was not tested here (the local export still lacks Tuesday and Thursday morning).
