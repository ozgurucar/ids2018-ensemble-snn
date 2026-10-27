# Review C, round 2: cross-review of A (methods, 5/10) and B (novelty, 5/10)

## 1. Agreement and disagreement

**All three of us agree on:** the over-long abstract, the mechanism claim exceeding n = 3, the missing Loihi/SRAM cost for Enc-ANN, the detector as a non-contribution, the Kaggle "determinism" overclaim, and the unexplained Table III AC trend.

**A found errors I missed, and I agree with them:**
- The Table V caption and the "nine of thirteen" count are wrong: DDoS-LOIC-UDP is omitted with F1 ≈ 0.82.
- "The ranking holds at the other budgets" is false at τ = 10%.
- The frozen T = 4 detection rate is 27% in the text but 23.9% in Table VIII.
- The ANN energy appears as both 0.39 and 0.40 µJ.
- The op-count sample is called "class-balanced", but it is not.
- The 45 nm model leaves out the E-SNN's LayerNorm and membrane updates; with them, the sign flips at T = 12 (A M6). This is the most serious factual point, because the abstract quotes that model.
- The "1,101 labels" claim does not count the 100k labelled flows used to fit the temperature (A M7).

**Where I partly disagree with A:**
- Ten seeds plus 3–5 split seeds is ideal but not necessary for an 8. Group-bootstrap CIs, paired per-seed differences and softer wording fix the overclaim; five seeds is enough on top of that.
- Making 11-class macro-F1 *the* primary metric after seeing results is itself post hoc. Report it as co-primary.
- A time-blocked or episode split is a new paper. A near-duplicate audit plus "duplicate-controlled" in the title is proportionate.

**I agree with B on:**
- The missing cross-dataset references (D'hooge ×2, Cantone) and Gorishniy et al. on numerical embeddings.
- The error-floor logic: identical vectors cannot be memorised apart, so an error below the floor points to a label or preprocessing difference, not leakage. B's wording replaces my minor 13.
- The incomplete CIC-IDS2017 copy.

**Where I disagree with B:** a packet-sequence SNN and a measured Loihi number belong in future work, not in the must-fix list.

## 2. My own points: dropped or downgraded

- **C M7 (Eq. 1 notation):** downgrade to minor.
- **C M6 (training details):** downgrade to medium. All the values are already in `configs/`; the fix is one paragraph.
- **Cosmetic minors and README gaps:** worth +0.2 at most.

## 3. Joint ranked must-fix list

| # | Item | Tag | Impact |
|---|---|---|---|
| 1 | Fix the factual slips: Table V caption ("eight"); ranking at 10%; five partitions, not four; 27% vs 23.9%; 0.39 vs 0.40 µJ; "class-balanced"; error-floor sentence; Table IX FAR 0.052. | [TEXT] | +0.5 |
| 2 | Match claims to n = 3: paired per-seed differences; "no detectable difference" wherever CIs overlap; mark the mechanism claim as provisional. | [TEXT] | +0.5–1 |
| 3 | Group-bootstrap CIs for Table II and the key differences; 11-class macro-F1 as a co-primary column. | [CPU] (inference only if per-row scores are not stored) | +0.5–1 |
| 4 | Consistent energy model: add E-SNN LayerNorm and membrane updates at 45 nm; one ANN figure; INT8 ANN row; Enc-ANN in Table VII; drop "69% less" from the abstract. | [CPU] | +0.5 |
| 5 | Reposition against prior work: about 10 new references; frame transfer as confirming known failure, now shown for SNNs; retitle; abstract ≤ 250 words; revise contributions. | [TEXT] | +1 |
| 6 | Presentation: cite Figs. 1–2; reorder Section V; merge Table VI into Table III; one term each for FAR/DR, MLP, latency branch, "label budget". | [TEXT] | +0.5 |
| 7 | Adaptation accounting: fit the temperature on the labelled budget, or count those labels; compare DR at matched FAR; add a "same-capture" caveat; rerun transfer on the full 2017 export. | [CPU] | +0.5 |
| 8 | Dst Port ablation (E-SNN, Enc-ANN, XGBoost), in-distribution and on transfer. | [GPU] | +0.5–1; may change the headline |
| 9 | Binned/PLE-encoded MLP baseline; 5 seeds for the neural models. | [GPU] | +0.5–1 |
| 10 | Near-duplicate test-to-train audit; title "duplicate-controlled". | [CPU] + [TEXT] | +0.3 |
| 11 | 0.1% and 0.5% budgets; per-day FPR range; calibration metrics (per-day FPR and decision ablations are already in the records). | [CPU] | +0.3 |
| 12 | Training-details paragraph; README test/smoke instructions; checkpoint link. | [TEXT] | +0.2 |

**Expected scores:**
- Items 1–7 (no GPU): about 7.
- Adding 8–9 (one Kaggle session, about 15 runs): 8 or above, if the conclusions hold.

## 4. Space plan within 8 pages

**New material needs about 0.8 column:** CI and 11-class columns, a training-details paragraph, about 10 references, Dst-Port and binned-MLP rows, a few sentences on near-duplicates and per-day FPR.

**Cuts that recover about 1.2 columns:**
- Shorten the abstract from about 410 to about 230 words (−0.25 col).
- Merge Table VI into Table III (−0.25 col).
- Replace Table IV with two sentences (−0.2 col).
- Fold Section VI into the Reproducibility paragraph (−0.25 col).
- Pivot Table IX so that label budgets become columns (−0.1 col).
- Shrink Fig. 3 (−0.1 col).
- Trim the SNN-IDS paragraph of Related Work (−0.05 col).

**Move to an online supplement (arXiv or repository):** the full Table I per-class support, Table IV, full per-budget results, per-day FPR, the 2017 column mapping, and near-duplicate audit details.
