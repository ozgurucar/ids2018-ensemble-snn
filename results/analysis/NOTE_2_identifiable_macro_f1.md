# Item 2: macro-F1 over identifiable classes (co-primary)

Script: `scripts/analysis/identifiable_macro_f1.py` (per-class test F1 and confusion matrices from the records).
Outputs: `results/analysis/identifiable_macro_f1.json` (every label, model, seed, budget), `results/analysis/identifiable_macro_f1_table.md`.
Accepts `--summary LABEL=PATH` for v5 records.

Definitions. MF1-11: mean per-class F1 without FTP-BruteForce and DoS-SlowHTTPTest (99.99% and 99.996% of their flows lie in label-conflicted feature groups). MF1-10: also without Infiltration. ADR excl. Inf.: share of non-Infiltration attack flows that raise an alarm.

## Co-primary table, tau = 5%, T = 12 (mean ± s.d., three seeds)

| Model | MF1 (13) | MF1 (11) | ADR | ADR excl. Inf. |
|---|---|---|---|---|
| E-SNN | 0.769 ± 0.022 | 0.837 ± 0.019 | 0.959 | 0.9998 |
| Matched ANN | 0.756 ± 0.004 | 0.821 ± 0.005 | 0.958 | 0.9997 |
| Enc-ANN | 0.787 ± 0.017 | 0.848 ± 0.017 | 0.963 | 0.9998 |
| Random forest | 0.788 ± 0.001 | 0.842 ± 0.000 | 0.965 | 0.9999 |
| CatBoost | 0.791 ± 0.005 | 0.843 ± 0.004 | 0.965 | 1.0000 |
| XGBoost | 0.808 ± 0.005 | 0.858 ± 0.001 | 0.967 | 1.0000 |

At 1%: MF1-11 = 0.861 (E-SNN), 0.840 (ANN), 0.883 (Enc-ANN), 0.885 (RF), 0.898 (CatBoost), 0.905 (XGBoost).
At 10%: 0.819, 0.812, 0.825, 0.813, 0.832, 0.849.
T = 4 / T = 8 E-SNN MF1-11 at 5%: 0.828 ± 0.018 / 0.832 ± 0.018; Enc-ANN 0.844 ± 0.017 / 0.863 ± 0.013. Wide variant (T = 8, 3 seeds): 0.833 ± 0.017.

```latex
\begin{tabular}{lcccc}
\toprule
Model & MF1 (13 cl.) & MF1 (11 cl.) & ADR & FPR \\
\midrule
E-SNN & $0.769 \pm 0.022$ & $0.837 \pm 0.019$ & $0.959$ & $0.049$ \\
Matched ANN & $0.756 \pm 0.004$ & $0.821 \pm 0.005$ & $0.958$ & $0.050$ \\
Enc-ANN & $0.787 \pm 0.017$ & $0.848 \pm 0.017$ & $0.963$ & $0.049$ \\
Random forest & $0.788 \pm 0.001$ & $0.842 \pm 0.000$ & $0.965$ & $0.050$ \\
CatBoost & $0.791 \pm 0.005$ & $0.843 \pm 0.004$ & $0.965$ & $0.049$ \\
XGBoost & $\mathbf{0.808 \pm 0.005}$ & $\mathbf{0.858 \pm 0.001}$ & $\mathbf{0.967}$ & $0.049$ \\
\bottomrule
\end{tabular}
```

Per-class F1 at 5% with CatBoost (for Table V): DoS-SlowHTTPTest 0.552 / 0.519 / 0.625 / 0.747 / 0.757 / 0.734 (E-SNN, ANN, Enc-ANN, RF, CatBoost, XGB); FTP-BruteForce 0.243 / 0.271 / 0.274 / 0.234 / 0.255 / 0.337; Infiltration 0.127 / 0.124 / 0.152 / 0.169 / 0.166 / 0.171; Web Attacks 0.360 / 0.171 / 0.393 / 0.319 / 0.345 / 0.464; DDoS-LOIC-UDP 0.821 / 0.816 / 0.821 / 0.869 / 0.850 / 0.837. Eight classes, not nine, have F1 at or above 0.96 for every model.

## LaTeX-ready sentences

- Because FTP-BruteForce and DoS-SlowHTTPTest are almost entirely label-conflicted, we also report macro-F1 over the remaining eleven classes as a co-primary metric (Table~\ref{tab:main}).
- On the eleven identifiable classes the E-SNN reaches $0.837 \pm 0.019$, 0.5 points below random forest ($0.842$) instead of 1.9 points on all thirteen classes, and Enc-ANN ($0.848$) moves above random forest and CatBoost ($0.843$). XGBoost stays first ($0.858$).
- Excluding Infiltration, every model detects at least 99.97\% of attack flows at the 5\% budget; more than 99\% of the missed attack flows are Infiltration, so the ADR column mostly measures Infiltration.
- Eight of the thirteen classes reach F1 $\geq 0.96$ for every model; DDoS-LOIC-UDP (0.82 to 0.87) is the ninth and is omitted from Table~\ref{tab:perclass} only for space.

## What changes in the paper

- The 13-class ranking (XGB > CatBoost > RF > Enc-ANN > E-SNN > ANN at 5%) partly reorders on 11 classes at 5% (XGB > Enc-ANN > CatBoost > RF > E-SNN > ANN). At 1% the 11-class order equals the 13-class order. At 10% on 11 classes the E-SNN is above RF.
- "Attack detection rates differ by less than one point across all models" is close to tautological: all differences are Infiltration.
- Table V caption and the "nine of the thirteen classes" sentence: eight, and add CatBoost.
