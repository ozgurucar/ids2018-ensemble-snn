# Review A — Methodology and Statistics

**Paper:** "What Do Spikes Buy in Flow-Based Intrusion Detection? A Leakage-Controlled Study of an Ensemble Spiking Network on CSE-CIC-IDS2018"
**Reviewer focus:** evaluation protocol validity, statistical support, number-to-record consistency, energy assumptions, CIC-IDS2017 transfer/adaptation.

**Overall score: 5 / 10** (borderline; weak reject in current form, could become a clear accept)
**Confidence: 4 / 5** (I re-derived most reported numbers from `results/*.json` and read the evaluation, transfer and fine-tuning code.)

---

## Summary

The paper evaluates a three-branch ensemble SNN (rate/latency/population codes, 86k parameters) on CSE-CIC-IDS2018 under a protocol that (i) keeps identical cleaned feature vectors in one partition, (ii) uses separate partitions for training, tuning, probability calibration, alarm-threshold calibration and test, and (iii) compares models at a fixed benign false-alarm budget. The SNN is compared with a parameter-matched MLP, a "spike-input control" (Enc-ANN: same encoders, no membrane dynamics) and three untuned tree ensembles. Main claims: the SNN is above the matched MLP but below Enc-ANN and all trees; T=4 matches T=12 at 2.9× fewer synaptic events; energy conclusions flip between a 45 nm AC/MAC model and Loihi per-op costs; two classes (FTP-BruteForce, DoS-SlowHTTPTest) are essentially unidentifiable on this representation; frozen models transfer poorly to CIC-IDS2017, and ~1.1k labelled local flows recover >98% detection.

The engineering and provenance work is unusually good (hashed partitions, immutable run records, derived experiments that refuse to run on changed data, disclosure of all variants, honest limitations). The numbers in the paper are, with a few exceptions listed below, faithfully copied from the records. My concerns are about what the numbers can support: the headline model ranking rests on differences that are not statistically distinguishable with 3 seeds and are largely driven by two classes whose labels the paper itself shows are not identifiable from the features; the protocol still leaves episode-level leakage and a destination-port shortcut in place; the 5% operating point is far from the models' natural operating point and saturates ADR; the 45 nm energy comparison omits costs that would flip its sign at T=12; and the adaptation experiment uses ~100k labelled local flows for calibration that are not counted in the "1,101 labels" claim.

---

## Major issues

### M1. The headline ranking is not statistically supported (3 seeds, no tests, many comparisons)
**Location:** Abstract (l. 21: "above the matched perceptron ... but below the spike-input control ..."), §Results l. 155, Discussion l. 340, Conclusion l. 350.
**Why it matters:** The paper's central interpretive claim ("the input encoders, not the spiking dynamics, carry most of the benefit") rests on E-SNN vs Enc-ANN and E-SNN vs matched ANN differences. From `results/v3/experiments/group_ce/summary.json` (`aggregate.*["0.05"].macro_f1.values`), Welch t-tests on the three seeds give:

| Comparison (τ=5%) | Δ macro-F1 | p (Welch, n=3+3) |
|---|---|---|
| E-SNN − matched ANN | +0.013 | 0.40 |
| E-SNN − Enc-ANN | −0.018 | 0.33 |
| E-SNN − RF | −0.019 | 0.28 |
| E-SNN − CatBoost | −0.022 | 0.23 |
| E-SNN − XGBoost | −0.039 | 0.08 |
| Enc-ANN − RF | −0.001 | 0.93 |

None of the E-SNN comparisons reaches p<0.05, even against XGBoost, before any correction for the ~30 comparisons made on the same test partition (6 models × 3 budgets, 3 window lengths, 5 variants, weighted-loss runs). The E-SNN seed values (0.744, 0.787, 0.777) span more than the gaps being interpreted. Moreover, seeds only vary initialization/order; the split seed (2026) is fixed, so partition variance, which is large for the group-concentrated classes (see M3), is not captured at all. The wording "is above"/"is below"/"beats" (Abstract, Conclusion: "It beats a parameter-matched perceptron") is therefore not justified, and the "no difference" claims for T (l. 159: "indistinguishable") and the variant screen are absence-of-evidence statements with very low power.
**Fix:** (a) Run ≥10 seeds for the neural models (each run is ~20–45 min on one GPU per the logs) and ideally 3–5 split seeds. (b) Report group-level bootstrap CIs on the test partition (resample feature groups, or days × groups), and paired comparisons where models share a split. (c) Pre-declare the 2–3 confirmatory comparisons (E-SNN vs Enc-ANN, E-SNN vs matched ANN, E-SNN vs XGB at τ=5%) and apply Holm correction; label everything else exploratory. (d) Replace "indistinguishable" with an equivalence statement (e.g., TOST with a stated margin) or with "no detectable difference at n=3".

### M2. Destination port is a model input; the input description omits it
**Location:** §Models "Input" (l. 108: "70 flow statistics ... durations, packet and byte counts ..."), §Data l. 60 (only source port dropped).
**Why it matters:** `idsresearch/data.py` drops only `src port`/`source port`; `manifest.json → preprocessing.selected_columns` starts with `"Dst Port", "Protocol"`. Destination port is a well-known shortcut in CIC datasets (FTP-BF→21, SSH-BF→22, web/DoS→80/443), lets a model learn "which server was attacked in this testbed", and is exactly the kind of feature that should break under transfer (the 2017 testbed uses different hosts/services). It also feeds the protocol imputation for 2017 (`cross_dataset_cic2017.py` l. 45). A leakage-focused paper must disclose and ablate it.
**Fix:** State explicitly that Dst Port and Protocol are inputs. Add an ablation without Dst Port (at least E-SNN, Enc-ANN, XGB, 3 seeds) for the in-distribution table and the 2017 transfer. If results move materially, make the port-free model primary.

### M3. Two non-identifiable classes drive most of the model ranking
**Location:** Table `tab:main`, Table `tab:perclass`, §"Where the errors are" (l. 213–232), Abstract.
**Why it matters:** The audit (`feature-group-audit.json`) shows the three largest groups (149,331 / 65,374 / 59,909 rows) are mixtures of FTP-BruteForce and DoS-SlowHTTPTest. Because the split assigns whole groups, the label mix of these two classes in each partition is set by a handful of groups: SlowHTTPTest is 87% train / 5% tune / 0.4% cal / 8% test, FTP-BF has only **6** rows in the alarm-calibration half (`alarm_calibration_diagnostics.per_class["FTP-BruteForce"].n = 6`). Predictions on these rows are determined by the training prior of identical vectors, so per-class F1 for them measures the partition draw, not model quality. Recomputing macro-F1 at τ=5% without these two classes (from `per_seed[*].operating_points["0.05"].test.per_class`):

| Model | Macro-F1 (13 cl.) | Macro-F1 (11 cl., excl. FTP-BF & SlowHTTPTest) |
|---|---|---|
| E-SNN | 0.769 | 0.837 |
| Matched ANN | 0.756 | 0.821 |
| Enc-ANN | 0.787 | 0.848 |
| RF | 0.788 | 0.842 |
| CatBoost | 0.791 | 0.843 |
| XGBoost | 0.808 | 0.858 |

The E-SNN–RF gap shrinks from 1.9 to 0.5 points and Enc-ANN moves above RF and CatBoost. The E-SNN vs RF difference in SlowHTTPTest F1 alone (0.552 vs 0.747) contributes 1.5 macro-F1 points. Since the paper itself argues these classes are not separable on this representation, ranking models on a metric that includes them is inconsistent. Note also that the two classes come from different capture days (02-14 vs 02-16), i.e., the labels are recoverable only from time, which is a labelling artefact (consistent with Liu et al.).
**Fix:** Make the primary metric macro-F1 over identifiable classes (or merge FTP-BF+SlowHTTPTest into one "conflicting" class, or apply Liu et al.'s corrected labels), report the 13-class number as secondary, and report per-class results with group-bootstrap CIs. Also add CatBoost to Table `tab:perclass` (it is the best model on SlowHTTPTest, 0.757, and is silently omitted).

### M4. "Leakage-controlled" overstates what exact-duplicate grouping achieves
**Location:** Title, Abstract, Contribution 1 (l. 37), §Feature-group split (l. 64), Limitations (l. 346).
**Why it matters:** `audit.json` shows every attack class comes from a single day and mostly a single contiguous episode (e.g., DoS-Hulk spans 3.3 minutes, DDoS-HOIC 22 minutes; `groups_by_gap_minutes` = 1–2 episodes for nearly all classes). With a group split, train and test contain flows from the *same* attack execution that differ only in jitter (IAT, byte counts), which is the dominant leakage mode in these datasets; the paper mentions it only as a limitation. The record's own `readiness.json` lists "Development suite informed by previously inspected test results" and "Real timestamp review is not verified" as blockers. The protocol therefore controls verbatim duplication, not near-duplicate or episode leakage, and the title should not imply more.
**Fix:** Either (a) add an episode/time-blocked evaluation (e.g., within each attack episode train on the first 60% of time, test on the last 20%; benign by day blocks) even if timestamps are only approximately trusted, or a leave-one-day-out benign evaluation; or (b) add a near-duplicate audit (nearest-neighbour distance from test to train in the scaled space, fraction within ε) and retitle as "duplicate-controlled". The 2017 transfer is the only true out-of-episode test and should be framed as such.

### M5. The 5% operating point saturates ADR and hides strong day-level heterogeneity
**Location:** §Decision rule (l. 104), §Results l. 134 and l. 155 ("Attack detection rates differ by less than one point"), Abstract.
**Why it matters:** (a) The models' own argmax operating point after prior correction is at FPR 0.08–0.2% with *higher* macro-F1 than at τ=5% (E-SNN seed 42: `corrected_argmax.macro_f1` = 0.778 at FPR 0.0020 vs 0.744 at τ=5%; XGB: 0.841 at FPR 0.0008). Forcing every model to alarm on 5% of 2.7M benign test flows (~135k false alarms) is 25–60× looser than their natural operating point and is operationally unrealistic for NIDS. At this point, the ~4% missed attacks are almost entirely Infiltration (6.2% of test attacks, AUC 0.82–0.88), so "ADR differs by <1 point" is close to tautological. (b) The pooled 5% FPR is an average over days dominated by 02-20 (55% of benign rows). Per-day test FPR for the E-SNN ranges 0.1% (02-21) to **23.2%** (02-28) and 15.3% (03-01); for XGBoost 32.3% and 31.5% on those days (`diagnostics.per_recorded_day`). These are the Infiltration days, suggesting unlabelled malicious traffic in "benign". An operator on those days would see 5–6× the budget, which is the same magnitude as the 2017 transfer failure (23–26%).
**Fix:** Add τ ∈ {0.1%, 0.5%} (and the argmax point) to the main table; report ADR excluding Infiltration and per-family detection; report per-day achieved FPR (or its range) with the budget; discuss that the Neyman–Pearson framing gives no guarantee under the day-dependent, non-i.i.d. benign mix (the records themselves state this in `operating_points.*.calibration.guarantee`). Also report the calibration effect (NLL/Brier/ECE before/after prior offset and temperature, and the `decision_ablations` raw/prior-only macro-F1), since "calibration" is a keyword but no calibration metric appears in the paper.

### M6. The 45 nm energy comparison omits E-SNN costs that flip its sign at T=12
**Location:** Table `tab:eff`, l. 238 and l. 256 ("the estimate ends about 17% below the ANN"), Abstract ("69% less synaptic energy"), Table `tab:steps` energy column.
**Why it matters:** The 45 nm model counts E-SNN ACs + fusion MACs only. But the E-SNN applies LayerNorm at every time step (6,912 elements at T=12; `energy_loihi.json → host_layernorm` = 0.127 µJ) and updates 6,912 membranes with a learnable decay (≈6,912 multiply-adds ≈ 0.032 µJ). Adding these gives ≈0.48 µJ at T=12, i.e., ~20% **above** the matched ANN (0.398 µJ including its own LayerNorm), and reduces the T=4 advantage from 69% to ≈56%. Meanwhile the ANN figure is inconsistently 0.39 µJ (Tables `tab:eff`, `tab:steps`, linear only) vs 0.40 µJ (Table `tab:loihi`, Abstract, with LayerNorm). Further: (a) op counts come from `app/samples/demo_flows.csv` — 1,600 benign + 400 each of only 7 attack classes from 4 days — not "class-balanced" and not the test mix (84% benign; DoS-Hulk, LOIC-HTTP, Infiltration, Web absent), so spike rates are not representative; (b) the ANN is charged FP32 MACs while Loihi weights are ≤9-bit (the INT8 ANN at 0.020 µJ, already in `energy_loihi.md`, is the like-for-like point and is omitted); (c) the Loihi mapping assumes per-step LayerNorm on a host, which implies a host round trip per time step that is not costed and makes the model non-deployable as trained.
**Fix:** Include membrane updates and LayerNorm for the E-SNN in the 45 nm model (or remove LayerNorm for both and retrain); use one ANN number consistently; measure op counts on a stratified sample of the actual test partition with its benign share; add the INT8 ANN row; state explicitly that the trained E-SNN would need LayerNorm folding/removal to run on Loihi. Tone down "69% less" in the abstract.

### M7. Adaptation experiment: "1,101 labels" excludes ~100k labelled calibration flows; FAR not matched
**Location:** l. 308, Table `tab:adapt`, Abstract ("About 1,100 labelled local flows are enough ...").
**Why it matters:** In `scripts/finetune_cic2017.py`, `calibrate()` fits the temperature on `prob_local`, which is 100,000 *labelled* rows of the 2017 calibration partition (`finetune_cic2017.json → partitions.calibration_probability_rows = 100000`), restricted to classes the model knows. That is ~90× the 0.1% budget. The threshold additionally assumes access to known-clean benign flows. `finetune_summary.md` caveat 4 discloses this; the paper does not. In addition, the E-SNN fine-tuned at 1% overshoots the budget (seeds: 6.3%, 6.2%, 5.3%), so its DR is compared with XGBoost at unequal FAR. Pool, calibration and test are drawn from the same capture days and attack episodes (acknowledged), so near-duplicates of the same runs are on both sides.
**Fix:** Either fit the temperature on the labelled budget only (or skip temperature for adapted models), or count calibration labels in the budget and say so in the abstract. Report DR at matched achieved FAR (or partial AUC) for all rows. Add a time-ordered adaptation (label early 2017 traffic, test later days) to make the "operator" story credible.

### M8. Transfer failure confounds network shift with feature-extractor/version shift and the port shortcut
**Location:** §Transfer (l. 280–282), Table `tab:transfer`, Abstract, Conclusion.
**Why it matters:** The 2017 MachineLearningCVE export was produced by an older CICFlowMeter with documented feature bugs (Engelen et al.), the column mapping in `cross_dataset_cic2017.py` is positional (`set_axis`) with only a count check, Protocol is imputed from port, and Dst Port is an input (M2). A 23–26% benign FAR under the 2018 threshold may therefore reflect feature-semantics shift rather than "a different network". The site-recalibration threshold is also fit on a random (not group-split) half of 2017 benign rows. The conclusion "none of the models carries its accuracy over to a different network" is plausible but not isolated.
**Fix:** Map columns by name with an explicit table in the appendix; report per-feature distribution shift (e.g., KS per feature, 2017 benign vs 2018 benign); repeat transfer without Dst Port; ideally use the re-extracted, version-consistent CIC-IDS2017/2018 releases (Engelen et al. / Liu et al.) so both datasets share one extractor. Report DR on seen families after recalibration (PortScan/Heartbleed are not in the 2018 label space).

---

## Minor issues

1. **Table `tab:perclass` caption is wrong.** It says classes with F1 ≥ 0.96 for all models are omitted, but DDoS-LOIC-UDP is omitted with F1 0.816 (ANN), 0.821 (E-SNN, Enc-ANN), 0.837 (XGB), 0.850 (CatBoost), 0.869 (RF). Likewise l. 213 "Nine of the thirteen classes ... almost perfectly" should be eight.
2. **"The ranking holds at the other budgets"** (l. 155) is false at τ=10%: Enc-ANN 0.767 > RF 0.763 (`aggregate.encoded_ann["0.1"]`, `aggregate.rf["0.1"]`).
3. **Inconsistent frozen baseline.** l. 308 says fine-tuning "raises detection from 27%", while Table `tab:transfer` gives 23.9% for the same frozen T=4 model. The two use different calibration/evaluation subsets (`finetune_summary.md` caveat 7). Explain this in the text or use one baseline.
4. **FTP wording (l. 232).** All 193,360 FTP-BF rows lie in 54 groups and 193,353 are in conflicting groups, so not "every one of those vectors" conflicts. For Infiltration, 88,810 is a count of *rows* in conflicting groups ("of them" reads as groups), and the audit does not show the conflicting label is Benign.
5. **CPU timing is not reproducible.** Table `tab:eff` (57.1 µs E-SNN, 1.4 µs ANN; `v3/efficiency_cpu.json`) vs re-measurement of the same checkpoints in `v4/efficiency_cpu_v4.json` (105.3 µs, 2.1 µs; p95 1.4 s/batch). The ">15,000 flows/s" claim depends on which run you take (≈9.5k/s by v4). Report median ± IQR over repeated runs and pin the hardware.
6. **"Four disjoint partitions"** (Abstract) — there are five (train, tune, probability-cal, alarm-cal, test).
7. **"One of the three seeds reached 0.744"** (l. 155): 0.744 is the worst seed. "Fell to" is clearer.
8. **The error-floor sentence** (l. 232, "Any reported error below that floor ... is a sign of leakage") is too strong. The floor is an in-sample, full-dataset oracle, and a single test partition can fall below it by chance because conflicting groups have a different label mix there. Qualify it ("on the full dataset, with these labels and this feature set").
9. **The variant screen uses the same tuning partition as early stopping**, so tune macro-F1 (0.775–0.833) is optimistically biased and its rank correlation with test is expected to be poor. The explanation offered ("rewards fitting the easy majority classes") is speculative. The class mix of FTP/SlowHTTP in tune vs test (M3) is a more likely cause and should be checked.
10. **Kaggle determinism** (l. 191) is "consistent with", not "confirmed by", one matching reproduction.
11. **Matched ANN control is incomplete.** A non-temporal control that receives the same population (RBF) feature expansion without time/spikes would show whether the gain is "encoding" or simply "Gaussian basis expansion". Consider adding it.
12. **`figures/fig_finetune.pdf` exists but is never referenced.** Either use it in place of or alongside Table `tab:adapt`, or drop it.
13. **Table `tab:adapt` omits the 0.1% and 1% "XGBoost, continued" rows** that are in the records (DR 0.723 and 0.724). The text summarises them ("72% to 75%"), but the table should be complete.
14. **The "only the slow application-layer DoS attacks transfer well" claim** (l. 282) holds for the SNNs. For XGBoost, GoldenEye transfers at only 28.8%.
15. **The abstract reads "back above 98% detection".** The 2018 in-distribution ADR was ~96%, so "back" is misleading.
16. **The KS distance (0.006) is quoted for E-SNN seed 42 only.** The range across all models and seeds is 0.005–0.014.

---

## Verified numbers (paper vs. records)

All of the following match the records after rounding unless marked **MISMATCH**.

| # | Paper value (location) | Record (file → field) | Record value |
|---|---|---|---|
| 1 | 16,232,929 flows (l. 60) | v3/.../manifest.json → dataset.retained | 16,232,929 ✓ |
| 2 | Web Attacks total 928 (l. 60) | feature-group-audit.json → by_class["Web Attacks"].rows | 928 ✓ |
| 3 | DDoS-HOIC 686,012 / 198,861 (l. 64) | feature-group-audit.json → by_class["DDoS-HOIC"] | 686,012 / 198,861 ✓ |
| 4 | Table 1 all 52 cells | manifest.json → split.train_after_cap/tune/calibration/test | ✓ (all cells checked) |
| 5 | E-SNN 0.769±0.022, ADR 0.959, FPR 0.049 | group_ce/summary.json → aggregate.esnn["0.05"] | 0.7692±0.0220, 0.9586, 0.0492 ✓ |
| 6 | Matched ANN 0.756±0.004 / 0.958 / 0.050 | aggregate.ann["0.05"] | 0.7557±0.0044 / 0.9578 / 0.0497 ✓ |
| 7 | Enc-ANN 0.787±0.017 / 0.963 / 0.049 | aggregate.encoded_ann["0.05"] | 0.7870±0.0167 / 0.9634 / 0.0490 ✓ |
| 8 | RF 0.788±0.001 / 0.965 / 0.050 | aggregate.rf["0.05"] | 0.7879±0.0011 / 0.9655 / 0.0501 ✓ |
| 9 | CatBoost 0.791±0.005 / 0.965 / 0.049 | aggregate.catboost["0.05"] | 0.7909±0.0051 / 0.9652 / 0.0491 ✓ |
| 10 | XGB 0.808±0.005 / 0.967 / 0.049 | aggregate.xgb["0.05"] | 0.8085±0.0053 / 0.9673 / 0.0494 ✓ |
| 11 | τ=1%: XGB 0.848, E-SNN 0.789 | aggregate.{xgb,esnn}["0.01"].macro_f1.mean | 0.8478, 0.7892 ✓ |
| 12 | E-SNN worst seed 0.744 | aggregate.esnn["0.05"].macro_f1.values | 0.7444 ✓ |
| 13 | Weighted CE: E-SNN 0.753±0.004, ANN 0.747±0.003 | group_weighted/summary.json → aggregate | 0.7525±0.0036, 0.7471±0.0032 ✓ |
| 14 | KS 0.006 (E-SNN) | per_seed.esnn[0].benign_calibration_test_ks_distance | 0.0056 ✓ |
| 15 | Per-class F1 table (20 cells) | per_seed[*].operating_points["0.05"].test.per_class[*].f1 (mean) | ✓ all 20; **caption MISMATCH** (minor 1) |
| 16 | Slowloris 0.964 (E-SNN) – 0.998 (XGB) | same | 0.964 / 0.998 ✓ |
| 17 | Web: E-SNN 98 TP, 661 FP, prec 0.13, AUC 0.994, AP 0.49; XGB 160/342, 0.32, 1.000, 0.85 | per_seed.{esnn,xgb}[0] → Web Attacks | ✓ all |
| 18 | FTP 193,360 / 193,353 / 54 groups | feature-group-audit.json | ✓ (wording, minor 4) |
| 19 | SlowHTTPTest 139,884 of 139,890 | same | ✓ |
| 20 | Infiltration 140,610 groups, 88,810 | same | ✓ (88,810 are rows) |
| 21 | 68,467 conflicting groups, floor 1.10% | same → conflicting_groups, empirical_representation_error_floor | 68,467, 0.01096 ✓ |
| 22 | T=4: 0.766±0.015, @1% 0.791 | v4/steps/summary_T4.json → aggregate.esnn | 0.7659±0.0149, 0.7914 ✓ |
| 23 | T=8: 0.766±0.014, @1% 0.800±0.001 | summary_T8.json → aggregate.esnn | 0.7658±0.0139, 0.7995±0.0014 ✓ |
| 24 | Enc-ANN T=4 0.787±0.022 / 0.815; T=8 0.800±0.015 / 0.820; T=12 @1% 0.816 | summary_T4/T8, group_ce | 0.7873±0.0224/0.8145; 0.7999±0.0154/0.8196; 0.8161 ✓ |
| 25 | Screen tune/test (10 cells) | v4/variants/v4-variants-log.json | ✓ all |
| 26 | Wide 0.770±0.014, 0.803±0.007, seed 42 0.7620 | v4/wide/summary_wide.json | 0.7698±0.0140, 0.8028±0.0069, 0.7620 ✓ |
| 27 | Original seed 42 at T=8: 0.756 | summary_T8.json → esnn 0.05 values[0] | 0.7555 ✓ |
| 28 | Params 86,013 / 85,945 / 84,503 | runs/*/trained.json, efficiency_cpu.json | ✓ |
| 29 | Wide params 217,725 | not in records; re-derived from the architecture | 217,725 ✓ |
| 30 | ACs 116,864 / 227,501 / 339,801; MACs 3,328; ANN 84,420; Enc-ANN 28,956 / 5,094 / 30,272 / 29,881 | v3/efficiency_cpu.json, v4/efficiency_cpu_v4.json | ✓ |
| 31 | 45 nm energy 0.32 / 0.39 / 0.05 / 0.12 / 0.22 / 0.08 / 0.06 µJ | efficiency_cpu_v4.json → energy_pj_45nm | ✓ |
| 32 | CPU 57.1 / 1.4 / 16.3 µs | v3/efficiency_cpu.json | ✓ but not reproduced in v4 (minor 5) |
| 33 | Sparsity 72–75%, factor 2.9, ~4× events vs MACs, 17% below, 40× slower | derived from the records above | ✓ |
| 34 | Loihi 3.0 / 5.9 / 8.8 µJ; neuron updates 2,304 / 4,608 / 6,912; ANN 0.40 / 1.24; 2.4–22×; >90% synaptic; ~3/4 from input | v4/energy_loihi.json | ✓ (ANN 0.40 vs 0.39 inconsistency, M6) |
| 35 | 2017 rows 2,214,468; 36 Infiltration; 11 Heartbleed | cross_dataset/cic2017.json | ✓ |
| 36 | Table `tab:transfer` (12 cells) | cic2017.json → models.* | ✓ all |
| 37 | GoldenEye/Slowloris 86% / 87% (T=12), 99.8% / 99.6% (T=4); XGB Bot 61% | cic2017.json → site_recalibrated_5pct.per_label | ✓ |
| 38 | Budgets 1,101 / 11,026 / 55,153; 671,643 benign test flows | finetune_cic2017.json | ✓ |
| 39 | Table `tab:adapt` (27 cells) | finetune_cic2017.json → runs (mean over seeds) | ✓ except **MISMATCH:** E-SNN fine-tuned 0.1% FAR printed 0.053 (and "5.3%" at l. 308), record mean 0.05249 → 0.052 |
| 40 | Bot 0 / 0 / 32% (E-SNN fine-tuned), 97–99.5% (XGB) | finetune_summary.md / runs per_label | ✓ |

**Mismatches and inconsistencies found:** (i) the per-class caption and the "nine of thirteen" count (DDoS-LOIC-UDP); (ii) "ranking holds at other budgets" (fails at τ=10%); (iii) E-SNN fine-tuned 0.1% FAR, 0.053 vs 0.0525; (iv) frozen T=4 DR given as 27% (l. 308) vs 23.9% (Table `tab:transfer`); (v) ANN energy 0.39 vs 0.40 µJ; (vi) the op-count sample described as "class-balanced" when it is 1,600 benign + 7×400; (vii) CPU timing not reproduced by the v4 re-measurement.

---

## What would raise the score to 8+

1. **Statistics:** ≥10 seeds for the neural models plus ≥3 split seeds; group-bootstrap CIs; pre-declared confirmatory comparisons with Holm correction; equivalence tests for the T and variant "no difference" claims (M1).
2. **Primary metric on identifiable classes:** macro-F1 excluding (or merging) FTP-BF/SlowHTTPTest as primary, with the 13-class number secondary (M3). If the E-SNN vs Enc-ANN conclusion survives this and M1, the paper's main message becomes solid.
3. **Dst Port ablation** in-distribution and in transfer (M2).
4. **One stronger leakage control:** a time-blocked/episode-held-out split, or at least a near-duplicate audit, with the title adjusted to match (M4).
5. **Operating points:** add 0.1%/0.5% budgets and the argmax point, ADR excluding Infiltration, per-day FPR, and calibration metrics (M5).
6. **A consistent energy model:** E-SNN LayerNorm and membrane updates included at 45 nm, one ANN number, an INT8 row, and op counts measured on the test mix (M6).
7. **Honest label accounting in adaptation:** temperature fit on the budget only (or the labels counted), DR at matched FAR, and a time-ordered variant (M7).
8. **Transfer with name-based mapping** and a per-feature shift analysis, ideally on version-consistent re-extracted data (M8).

Items 1–3 and 6 are cheap with the existing pipeline and frozen partitions, and together would likely move my score to 7. Adding 4 and 7 would move it to 8+.
