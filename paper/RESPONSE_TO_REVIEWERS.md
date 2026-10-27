# Response to reviewer comments (Amir, Pablo)

Thank you both for the careful reading. Since the version you reviewed, the study has been rebuilt rather than patched: a new split, a new decision rule, three seeds (five for the main comparison), stronger baselines and several follow-up experiments. Several comments therefore no longer apply in their original form. Each one is listed below with what changed and where to find it.

## Amir

| # | Comment (short) | What we did |
|---|---|---|
| C1, C16 | FPR 0.11 in abstract vs ≤ 0.10 in Table I | Every model now uses one decision rule. The threshold is fitted on a separate alarm-calibration partition and the achieved test FPR is reported next to every result (4.9–5.0% at the 5% budget, Table II). The abstract and the tables use the same numbers. |
| C2, C14 | Do not claim the ceiling is enforced on test | The text says that the threshold is fitted on calibration data only and that the test FPR is measured, not guaranteed (Sec. III-D). We also report the KS distance between benign calibration and test scores (0.005–0.014 across models and seeds) and the per-day FAR, which reaches 24% for the E-SNN on the Infiltration days (Sec. V-A). |
| C3, C4, C17 | Tone too strong | Rewritten throughout in neutral wording. The SNN is no longer called superior; trees are reported as the strongest models. |
| C5, C6, C22 | Unsupported claims (10–20 point drop, consensus statements) | Removed. Every remaining quantitative claim comes from our own runs or a cited source. |
| C7, C8, C21 | Energy claims without hardware | Energy is given only as an estimate from counted operations, under four cost models (45 nm with layer normalisation and membrane updates, 45 nm with SRAM reads, INT8, and published Loihi per-operation costs; Table V, Sec. V-C). The models disagree on whether the SNN is cheaper, and the paper says so. No hardware claims are made. |
| C9 | "Full dataset" while capping rows | Table I gives the support of every class in every partition. Only training is capped, and the text says so. |
| C10, C24 | "Guarantee", row order as time order, exact time gap | The chronological row-order split is gone. Rows with identical feature vectors are grouped, and groups are assigned to partitions, so no test vector appears verbatim in training. We state what this does not prevent (near-duplicates, within-episode leakage) and that the timestamps are unverified. |
| C11 | SMOTETomek ablation | Synthetic oversampling was removed from the protocol. Classes are capped and corrected afterwards with a training-prior offset. |
| C12 | Why 60/40 mixture | The ratio was fixed in the earlier version and is now stated as untuned. The architecture screen includes the pure weighted average (1.0/0) as one variant (Sec. V-E). |
| C13 | One seed is not enough | The main run uses three seeds (42–44); the primary model comparison uses five seeds (42–46) at T = 4, with Welch tests, 95% CIs and Holm correction over four pre-declared comparisons (Table II, Sec. V-A). The split seed is fixed, so the intervals cover seed variance only; this is stated as a limitation. |
| C15 | Stronger baselines | XGBoost, CatBoost and random forest are added, along with a parameter-matched MLP and a spike-input control network. We did not add LSTM/CNN models because the inputs are static flow vectors, not sequences. |
| C18 | Do not overstate per-class results | Table III lists the five classes below F1 0.96 for all six models, and the text explains their causes. Macro-F1 over the 11 identifiable classes is reported next to the 13-class figure (Table II). |
| C19 | Web Attacks: high AUC, near-zero F1 | Added TP/FP/FN analysis. AUC is 0.994, but at the 5% budget the E-SNN finds 98 of 179 attacks with 661 false assignments; average precision is reported as the fairer measure (Sec. V-B). |
| C20 | Exact numbers for Slowloris / SlowHTTPTest | SlowHTTPTest is in Table III. Slowloris is omitted there because every model exceeds 0.96 F1 on it (0.964 for the E-SNN, 0.998 for XGBoost); the paper says so. SlowHTTPTest flows almost all share feature vectors with FTP-BruteForce, which explains the low F1 for every model. |
| C23 | "Dataset limitation" too strong | Now supported by the feature-group audit: 193,353 of 193,360 FTP-BruteForce flows and 139,884 of 139,890 SlowHTTPTest flows have vectors that also occur under other labels. |
| C25 | Conclusion contradicts RF > E-SNN | The conclusion now says that XGBoost is about 4 points ahead of the SNN (Holm p = 0.002, five seeds) and that the SNN cannot be separated from the MLP, the piecewise-linear MLP or the spike-input control. |

## Pablo

| Comment (short) | What we did |
|---|---|
| Split too detailed for the abstract | The abstract now states the protocol in one sentence. Details are in Sec. III. |
| SNNs address efficiency, the split addresses leakage | Agreed. The introduction now separates the two questions. |
| Energy needs hardware or "potentially" | See Amir C7. |
| Which features keep temporal dynamics / what is the SNN input? | Sec. IV now says explicitly that every model receives one static vector of 70 flow statistics, and that the SNN time steps are an encoding device, not network time. |
| Link coding schemes to features; justify combining three codes | A short paragraph connects each code to feature types. The population-only variant in the architecture screen (Sec. V-E) shows what a single code achieves. |
| Final sample and class counts | Table I. |
| Setting per session/day? | The split is by feature group across all days, not by day. |
| One seed is not enough | Three seeds, and five for the main comparison (see Amir C13). |
| Report parameters, time steps, spike rate, latency | Sec. IV (parameters), Table IV (time steps 4/8/12 and operations per flow), Sec. V-C (CPU time). Hidden-layer sparsity (72–74%) is given in the text. |
| Is the reported metric after calibration on validation data? | Yes. Sec. III-D describes the full chain, and test labels are never used to fit anything. |
| Small font in tables | Tables now use the normal font size where the column width allows. |
| Avoid citations in the conclusion | The conclusion has no citations. |
