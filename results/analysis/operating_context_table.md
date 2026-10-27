# Operating-point context (item 3)

Source: run records; script `scripts/analysis/operating_context.py`; JSON `results/analysis/operating_context.json`.

## Per-day test FPR at the 5% budget (T = 12, mean over seeds)

| Day | benign rows | E-SNN | Matched ANN | Enc-ANN | Random forest | CatBoost | XGBoost |
|---|---|---|---|---|---|---|---|
| 2018-02-14 | 133,543 | 0.012 | 0.007 | 0.014 | 0.023 | 0.013 | 0.015 |
| 2018-02-15 | 199,302 | 0.022 | 0.024 | 0.019 | 0.031 | 0.020 | 0.021 |
| 2018-02-16 | 89,251 | 0.002 | 0.000 | 0.001 | 0.003 | 0.000 | 0.000 |
| 2018-02-20 | 1,476,420 | 0.057 | 0.061 | 0.048 | 0.042 | 0.047 | 0.042 |
| 2018-02-21 | 71,924 | 0.001 | 0.001 | 0.001 | 0.001 | 0.001 | 0.000 |
| 2018-02-22 | 209,719 | 0.009 | 0.009 | 0.009 | 0.021 | 0.012 | 0.014 |
| 2018-02-23 | 209,850 | 0.008 | 0.007 | 0.009 | 0.021 | 0.012 | 0.014 |
| 2018-02-28 | 109,503 | 0.241 | 0.240 | 0.288 | 0.294 | 0.290 | 0.323 |
| 2018-03-01 | 47,378 | 0.175 | 0.151 | 0.256 | 0.288 | 0.266 | 0.316 |
| 2018-03-02 | 153,010 | 0.030 | 0.011 | 0.056 | 0.060 | 0.055 | 0.056 |
| range (seed means) | | 0.001-0.241 | 0.000-0.240 | 0.001-0.288 | 0.001-0.294 | 0.000-0.290 | 0.000-0.323 |
| range (any seed) | | 0.000-0.247 | 0.000-0.243 | 0.001-0.298 | 0.001-0.295 | 0.000-0.291 | 0.000-0.324 |

## Decision ablation at tau = 5% (T = 12, mean ± s.d.)

| Model | Rule | FPR | ADR | MF1-13 | MF1-11 |
|---|---|---|---|---|---|
| E-SNN | raw | 0.049 | 0.958 | 0.745 ± 0.017 | 0.807 ± 0.017 |
| E-SNN | prior_only | 0.049 | 0.959 | 0.769 ± 0.023 | 0.836 ± 0.020 |
| E-SNN | full | 0.049 | 0.959 | 0.769 ± 0.022 | 0.837 ± 0.019 |
| Matched ANN | raw | 0.049 | 0.958 | 0.747 ± 0.001 | 0.813 ± 0.001 |
| Matched ANN | prior_only | 0.050 | 0.958 | 0.756 ± 0.004 | 0.822 ± 0.005 |
| Matched ANN | full | 0.050 | 0.958 | 0.756 ± 0.004 | 0.821 ± 0.005 |
| Enc-ANN | raw | 0.049 | 0.963 | 0.767 ± 0.014 | 0.826 ± 0.005 |
| Enc-ANN | prior_only | 0.049 | 0.963 | 0.787 ± 0.017 | 0.848 ± 0.017 |
| Enc-ANN | full | 0.049 | 0.963 | 0.787 ± 0.017 | 0.848 ± 0.017 |
| Random forest | raw | 0.052 | 0.966 | 0.762 ± 0.001 | 0.810 ± 0.001 |
| Random forest | prior_only | 0.050 | 0.965 | 0.788 ± 0.001 | 0.842 ± 0.000 |
| Random forest | full | 0.050 | 0.965 | 0.788 ± 0.001 | 0.842 ± 0.000 |
| CatBoost | raw | 0.049 | 0.965 | 0.765 ± 0.008 | 0.820 ± 0.002 |
| CatBoost | prior_only | 0.049 | 0.965 | 0.791 ± 0.005 | 0.842 ± 0.004 |
| CatBoost | full | 0.049 | 0.965 | 0.791 ± 0.005 | 0.843 ± 0.004 |
| XGBoost | raw | 0.049 | 0.967 | 0.788 ± 0.005 | 0.835 ± 0.000 |
| XGBoost | prior_only | 0.049 | 0.967 | 0.808 ± 0.005 | 0.858 ± 0.001 |
| XGBoost | full | 0.049 | 0.967 | 0.808 ± 0.005 | 0.858 ± 0.001 |

## Argmax operating points (T = 12, mean over seeds)

| Model | Decision | FPR | ADR | MF1-13 | MF1-11 |
|---|---|---|---|---|---|
| E-SNN | uncalibrated | 0.0051 | 0.950 | 0.789 ± 0.017 | 0.858 ± 0.016 |
| E-SNN | corrected_argmax | 0.0012 | 0.941 | 0.788 ± 0.009 | 0.859 ± 0.003 |
| Matched ANN | uncalibrated | 0.0057 | 0.950 | 0.770 ± 0.006 | 0.840 ± 0.006 |
| Matched ANN | corrected_argmax | 0.0009 | 0.938 | 0.785 ± 0.005 | 0.856 ± 0.002 |
| Enc-ANN | uncalibrated | 0.0055 | 0.953 | 0.807 ± 0.016 | 0.873 ± 0.007 |
| Enc-ANN | corrected_argmax | 0.0008 | 0.941 | 0.808 ± 0.010 | 0.873 ± 0.003 |
| Random forest | uncalibrated | 0.0048 | 0.949 | 0.799 ± 0.002 | 0.855 ± 0.002 |
| Random forest | corrected_argmax | 0.0014 | 0.915 | 0.769 ± 0.005 | 0.873 ± 0.000 |
| CatBoost | uncalibrated | 0.0047 | 0.951 | 0.831 ± 0.008 | 0.899 ± 0.002 |
| CatBoost | corrected_argmax | 0.0002 | 0.938 | 0.808 ± 0.002 | 0.862 ± 0.001 |
| XGBoost | uncalibrated | 0.0058 | 0.953 | 0.819 ± 0.005 | 0.871 ± 0.000 |
| XGBoost | corrected_argmax | 0.0008 | 0.941 | 0.836 ± 0.006 | 0.890 ± 0.001 |

## Probabilistic quality (T = 12, mean over seeds)

| Model | prob-cal NLL before T | after T | fitted T | test NLL | test Brier | binary AP | std pAUC@1% |
|---|---|---|---|---|---|---|---|
| E-SNN | 0.0521 | 0.0521 | 0.980 | 0.0520 | 0.0226 | 0.9753 | 0.9734 |
| Matched ANN | 0.0537 | 0.0537 | 1.004 | 0.0532 | 0.0233 | 0.9749 | 0.9730 |
| Enc-ANN | 0.0475 | 0.0475 | 0.973 | 0.0482 | 0.0213 | 0.9787 | 0.9748 |
| Random forest | 0.0554 | 0.0553 | 0.984 | 0.0562 | 0.0249 | 0.9790 | 0.9701 |
| CatBoost | 0.0485 | 0.0484 | 0.963 | 0.0482 | 0.0213 | 0.9796 | 0.9748 |
| XGBoost | 0.0443 | 0.0443 | 1.011 | 0.0459 | 0.0208 | 0.9813 | 0.9753 |

ECE: not available: records hold no per-row test probabilities (test arrays are on Kaggle only).

## Where the misses are (T = 12, seed means)

| Model | tau | missed attacks | of which Infiltration | share |
|---|---|---|---|---|
| E-SNN | 0.01 | 25,045 | 24,863 | 0.9927 |
| E-SNN | 0.05 | 21,621 | 21,508 | 0.9948 |
| E-SNN | 0.1 | 18,594 | 18,511 | 0.9955 |
| Matched ANN | 0.01 | 25,007 | 24,801 | 0.9918 |
| Matched ANN | 0.05 | 22,003 | 21,868 | 0.9939 |
| Matched ANN | 0.1 | 18,808 | 18,723 | 0.9955 |
| Enc-ANN | 0.01 | 23,148 | 23,027 | 0.9948 |
| Enc-ANN | 0.05 | 19,090 | 19,005 | 0.9955 |
| Enc-ANN | 0.1 | 16,283 | 16,227 | 0.9965 |
| Random forest | 0.01 | 24,036 | 23,866 | 0.9929 |
| Random forest | 0.05 | 18,022 | 17,984 | 0.9979 |
| Random forest | 0.1 | 15,261 | 15,236 | 0.9984 |
| CatBoost | 0.01 | 22,731 | 22,600 | 0.9942 |
| CatBoost | 0.05 | 18,150 | 18,131 | 0.9989 |
| CatBoost | 0.1 | 15,400 | 15,385 | 0.9991 |
| XGBoost | 0.01 | 22,183 | 22,132 | 0.9977 |
| XGBoost | 0.05 | 17,045 | 17,022 | 0.9987 |
| XGBoost | 0.1 | 14,277 | 14,256 | 0.9986 |

## Ranking by 13-class macro-F1 (T = 12)

- tau = 0.01: XGBoost 0.848 > CatBoost 0.838 > Random forest 0.824 > Enc-ANN 0.816 > E-SNN 0.789 > Matched ANN 0.771 (same order as 5%: True)
- tau = 0.05: XGBoost 0.808 > CatBoost 0.791 > Random forest 0.788 > Enc-ANN 0.787 > E-SNN 0.769 > Matched ANN 0.756 (same order as 5%: True)
- tau = 0.1: XGBoost 0.801 > CatBoost 0.782 > Enc-ANN 0.767 > Random forest 0.763 > E-SNN 0.754 > Matched ANN 0.748 (same order as 5%: False)

## Ranking by 11-class macro-F1 (T = 12)

- tau = 0.01: XGBoost 0.905 > CatBoost 0.898 > Random forest 0.885 > Enc-ANN 0.883 > E-SNN 0.861 > Matched ANN 0.840
- tau = 0.05: XGBoost 0.858 > Enc-ANN 0.848 > CatBoost 0.843 > Random forest 0.842 > E-SNN 0.837 > Matched ANN 0.821
- tau = 0.1: XGBoost 0.849 > CatBoost 0.832 > Enc-ANN 0.825 > E-SNN 0.819 > Random forest 0.813 > Matched ANN 0.812
