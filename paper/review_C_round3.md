# Review C, round 3: presentation, clarity and reproducibility

**Score: 7 / 10** (up from 6). **Confidence: 4 / 5.**

**What I did:**
- Read `main.tex` (346 lines) and `RESPONSE_TO_REVIEWERS.md`.
- Built the PDF with tectonic in a scratch copy. It is 8 pages, with references balanced on page 8.
- Rendered the PDF and checked every float.
- Re-ran on CPU: `pytest`, `seed_stats.py` (3-seed and 5-seed), `identifiable_macro_f1.py`, `operating_context.py`, `adapt_summary.py` and `energy_unified.py --skip-test-mix`.
- Diffed every output against the committed files.

**Justification.** The revision fixes almost every presentation problem I raised:
- The abstract is about 246 words.
- All figures are cited, and Section V now runs in a sensible order.
- Table VI is folded into Table IV, and the terminology is unified (FAR/DR, matched MLP, latency branch, label budget).
- Training details are given, and Eq. (1) is unambiguous.

The new statistics are also well reported. The CIs, Holm-adjusted p-values and minimum detectable effects (MDE80) in l.167 all match `results/analysis/seed_stats_5seed_table.md`, and the 5-seed means and s.d. in Table II match `results/v5/seeds/summary.json`. The paper is now clear and honest.

Three things keep it below 8:
1. A logical overstatement about what the PLE-MLP result shows (abstract, contribution 2, l.167, l.327).
2. Fig. 2(b) still plots the energy model that the text now calls incomplete.
3. The repository's front door (README) describes the round-1 paper, and the new analysis scripts cannot be run from the repository alone.

---

## 1. Status of my round-2 concerns

| Round-2 item | Status |
|---|---|
| Abstract ≤ 250 words | **Resolved** (≈246). |
| Figs. 1–2 uncited | **Resolved** (l.119, l.253). |
| Section V order and forward references; Table VI duplicate | **Resolved**: errors → energy → T → screen → transfer; ops are merged into Table IV. |
| Terminology (FPR/FAR, ANN/MLP, temporal/latency, "budget") | **Resolved**. The only residue is "perceptron" used as a description at l.21 and l.121, which is fine. |
| Contributions omit transfer and energy; detector listed | **Resolved** (l.40–41). |
| Training details, encoder parameters, tree hyperparameters | **Resolved** (l.119–129). Small gaps remain: PLE-MLP width and bin fitting, listed below. |
| Eq. (1) ambiguity | **Resolved** (l.109–113). |
| Factual slips (caption, "nine", 10% ranking, partitions, 0.39/0.40, "class-balanced") | **Mostly resolved.** 0.39 remains at l.227, deliberately labelled "linear layers"; see E5. |
| Error-floor sentence | **Resolved** (l.198). |
| Enc-ANN missing from the energy table | **Resolved** (Table V). |
| Table V omits CatBoost | **Resolved** (Table III). |
| Last page unbalanced | **Resolved.** |
| Fig. 1 small fonts; Fig. 3 label overlaps | **Not addressed.** Fig. 2 is now worse: it is scaled to 0.8 column width, so its labels render at about 5 pt. |
| README: tests, smoke, claim → script table, checkpoint list | **Not resolved.** The README is unchanged since round 1 (see R1). |
| `profile_all_steps.py` Kaggle paths; `docs/PLAN_TR.md` | **Not resolved.** |
| Group bootstrap | **Declined**, and stated as a limitation (l.333). Partly justified, but see N1. |

---

## 2. Remaining errors and problems (line numbers refer to `main.tex`)

### E1 (major, text). "Matches" turns non-significance into equivalence, and the causal conclusion does not follow
**Location:** l.21 ("Since a spike-free encoding matches the SNN, any gain over the raw MLP comes from the input encoding"), l.38, l.167 ("A spike-free piecewise-linear encoding thus matches the E-SNN, so whatever the E-SNN gains…"), l.327 ("Any gain over the raw MLP therefore belongs to the input encoding").

**Why this is wrong:**
- The E-SNN's gain over the raw MLP is itself not significant (+1.1 points, Holm p = 0.32).
- The PLE-MLP vs MLP difference (+0.6 points) was never tested.
- The E-SNN vs PLE-MLP difference has an MDE80 of 1.9 points, so "matches" is not shown. No equivalence test was run for it; the TOST was only run for T.

The data support a narrower statement: no neural variant is separable from another at n = 5, and only XGBoost is ahead. Of the gain claims, only the exploratory Enc-ANN − MLP difference comes close (+2.4 points, unadjusted p = 0.057; on 11 classes p = 0.020).

**Proposed replacements:**
- Abstract: *"Only the gap to XGBoost is significant. The SNN cannot be separated from the MLP, the piecewise-linear MLP or the spike-input control, so we find no evidence that spiking dynamics add accuracy."*
- l.167: *"The E-SNN is not separable from the PLE-MLP either. Since neither is separable from the raw MLP, the data give no evidence that spiking dynamics add accuracy. Whether spike or piecewise-linear encodings help at all remains open; the largest such difference, Enc-ANN over the raw MLP, is +2.4 points (exploratory, unadjusted p = 0.057)."*
- Apply the same change in l.38 and l.327.

### E2 (major, text + CPU). Fig. 2(b) contradicts Table V and the text
**Location:** l.257–258.

**What is wrong:**
- Panel (b) still plots the optimistic 45 nm model ("linear layers only") on the old 4,400-flow sample. It therefore shows the E-SNN below the MLP at every T.
- The text (l.227) and Table V say that with LayerNorm and membrane updates the E-SNN is 23% *above* the MLP at T = 12.
- A reader who looks only at the figure gets the opposite conclusion.
- Panel (a) shows 3-seed T = 4 values, while Table II's primary T = 4 values come from 5 seeds.
- `scripts/make_figures.py` still reads `results/v4/energy_loihi.json`, so the figure cannot reproduce Table V.

**Fix:**
- Point `make_figures.py` at `results/analysis/energy_unified.json` (test_mix sample) and plot the "complete" 45 nm curve.
- Use the 5-seed T = 4 point in panel (a).
- Restore the figure to full column width, or enlarge its fonts to at least 7 pt.

### E3 (medium, text). The same T = 4 configuration has two different numbers
**What is inconsistent:**
- Table II gives E-SNN T = 4 as 0.766 ± 0.012 and Enc-ANN T = 4 as 0.779 ± 0.020 (five seeds).
- Table IV (l.216, l.219) and l.117 give 0.766 ± 0.015 and **0.787** ± 0.022 (three seeds).
- The Dst-Port ablation (l.117) quotes Enc-ANN 0.787 → 0.776. That baseline is the 3-seed number, while the paper's primary figure for the same model is 0.779.

**Fix:**
- Use the 5-seed values in Table IV, or mark the T = 4 rows "(3 seeds; 5-seed values in Table II)".
- In l.117, state that the ablation compares three seeds with three seeds.
- Add to l.129 that the v5 E-SNN and Enc-ANN seeds 42–44 also reproduce v4 exactly. I verified this: 0.7575, 0.7831, 0.7570 and 0.7623, 0.8055, 0.7940. It strengthens the determinism point.

### E4 (minor, text). "Pre-declared four comparisons" (l.167)
The round-2 records (`NOTE_1`) declare three comparisons; the PLE-MLP comparison was added for round 3. If it was fixed before the v5 run, say so ("declared before the five-seed run"). Otherwise call it pre-declared for three comparisons and planned for the fourth.

### E5 (minor, text)
- **l.227:** "below the MLP's 0.39 µJ", while Table V gives 0.40. Either quote 0.40 for both models under the complete model, or write "the MLP's linear layers (0.39 µJ)".
- **l.329:** "by a factor of 2.5 to 22" mixes two MLP baselines: 3.1/1.24 for T = 4 against SRAM, and 9.0/0.40 for T = 12 at 45 nm. Write: "7.8 to 22 times the MLP's 45 nm cost, or 2.5 to 7.2 times its cost with SRAM reads".
- **l.327:** "Enc-ANN is cheaper under every cost model we tried". Enc-ANN has no Loihi entry (Table V shows "–"). Write "under every cost model in Table V that applies to it".
- **l.323:** "Macro-F1 stays between 0.49 and 0.71". Table VII has 0.483 (XGBoost continued, 5%), so write 0.48.
- **l.69 and l.269:** `\url{solarmainframe/...}` and `\url{sweety18/...}` are Kaggle slugs, not URLs; hyperref turns them into broken relative links. Use `\texttt{}` or the full `https://www.kaggle.com/datasets/...` address.
- **l.125:** the PLE-MLP's hidden width and how its 16 bin edges are fitted (quantiles of the training partition?) are not stated.
- **l.140, Table II caption:** say that the XGBoost row in the T = 4 block is the same model as in the T = 12 block (trees do not depend on T), so readers do not look for a difference.
- **l.180, Table III caption:** add "T = 12" next to "three seeds".
- **l.341:** the released Enc-ANN checkpoint is the T = 12 one only (`app/models/profile/encoded_ann.pt`). The PLE-MLP and no-port checkpoints are not released, so say so.
- **Fig. 1 and Fig. 3:** the same font and overlap issues as in round 2.

---

## 3. Reproducibility findings

| Check | Result |
|---|---|
| `pytest -q tests` | **44 passed** (round 2: 41/42). |
| `seed_stats.py` (defaults) | Reproduces `seed_stats_table.md` byte for byte. |
| `seed_stats.py`, 5-seed table | Reproduces `seed_stats_5seed_table.md` **only** with `--no-defaults --summary T4=results/v5/seeds/summary.json --primary-label T4 --out seed_stats_5seed`. That command is documented nowhere. The documented example (docstring and `--help`: `--summary T12=results/v5/seeds/summary.json`) mislabels a T = 4 run as T = 12, and with `--no-defaults` it crashes (`KeyError: 'T12'`). |
| `identifiable_macro_f1.py`, `operating_context.py`, `adapt_summary.py` | Reproduce their committed tables exactly. |
| `energy_unified.py --skip-test-mix` | Runs and reproduces the demo-sample rows. The `test_mix` rows behind Table V need `~/.cache/ids-v4/raw`, which is not in the repository. |
| `noport.py`, `transfer_hygiene.py`, `adapt_label_budget.py` | Hard-wired to `~/.cache/ids-x17/combine.csv`, `~/.cache/ids-v5/noport/...` and `~/.cache/ids-v4/steps/...`. The no-port and T = 4 Enc-ANN checkpoints they load are not in the repository, so the transfer half of `NOTE_7` and Table VI cannot be rerun by an outsider. |

**R1 (major).** The README is unchanged since round 1. Specifically:
- The title still says "(v3)".
- Its results table uses the old names ("Matched ANN", "5% FPR budget") and the 3-seed T = 12 numbers.
- It still claims that slow DoS "is the exception" in transfer, which the paper now says depends on the destination port (l.288).
- It does not mention `results/v5/`, `results/analysis/` or `scripts/analysis/`.
- "Every number in the paper can be checked" has no rows for Table II (5-seed), Table V, Table VII, the KS analysis or the no-port ablation.
- The `idsresearch --help` text still points to the missing `docs/PLAN_TR.md`.

**R2 (minor).** The generated `seed_stats_5seed_table.md` has three bugs:
- The heading says "Per-model seeds (T = 12, …)" over T = 4 data.
- PLE-MLP is missing from the per-model table.
- The TOST and exploratory sections compare each model with itself ("T4:esnn vs T4:esnn … equivalent? yes", p = 1.000).

The paper does not use these rows, but a reader checking the claims will be confused.

**R3 (minor).**
- `results/v5` is 620 MB: 25 files `test_log_odds.npy` of 25 MB each. Use Git LFS or a Zenodo record, and say so in the README.
- Per-row binary test scores are therefore available. This bears on N1.

---

## 4. Ranked fixes that would move the score most

**Text only, no new experiments** (together: 7 → about 8):
1. **E1.** Replace "matches" and "any gain … comes from the encoding" in l.21, l.38, l.167 and l.327 with the non-equivalence wording above. (+0.5)
2. **README rewrite (R1).** Current results and names; a claim → script → data table covering Tables II, V, VII and the no-port ablation; the exact `seed_stats.py` command; which inputs live outside the repository and how to obtain them; the qualified slow-DoS claim. (+0.3; essential for an artefact badge)
3. **E3.** One set of T = 4 numbers, or explicit seed labels, in Table IV and l.117. (+0.2)
4. **E5 and E4 cleanup:** 0.39/0.40, "2.5 to 22", the Loihi "every cost model" wording, 0.48, Kaggle `\url`s, PLE-MLP details, Table II and III captions, Reproducibility checkpoint list. (+0.2)
5. **R2.** Fix the three bugs in `seed_stats.py`'s table and the `--help` example. (+0.1)

**Cheap CPU work** (< 1 h, existing data):
6. **E2.** Regenerate Fig. 2 from `energy_unified.json` with the complete 45 nm model and 5-seed T = 4 points; enlarge the fonts. (+0.3)
7. **N1.** A group bootstrap of DR and partial AUC at fixed FAR from the stored `test_log_odds.npy`. This needs only the test labels and group ids, which the CPU `prepare` step regenerates from the raw CSVs. It would answer the "partition variance" limitation at least for the binary metrics, so the stated reason for declining is weaker than l.333 implies. Macro-F1 would still need class predictions. (+0.2)
8. Package the analysis inputs that are now in `~/.cache` (no-port checkpoints, T = 4 Enc-ANN checkpoint, the 2017 `combine.csv` recipe), or provide a single download script, so that the transfer and Table V numbers can be rerun. (+0.2)

**New experiments (Kaggle GPU):**
9. A second split seed for the 5-seed T = 4 comparison (E-SNN, Enc-ANN, MLP, PLE-MLP, XGBoost). This is the only way to put partition variance into the intervals that support the main claim. (+0.3–0.5)
10. With-port Enc-ANN T = 4 calibration and transfer, so that the no-port transfer row for Enc-ANN (recalibrated DR 0.344, the best of all models in `noport_table.md`) has a with-port counterpart. That number is currently in the records but not in the paper. (+0.1)

Items 1–6 need no GPU and would, in my view, bring the paper to a clear 8 at a mid-tier IEEE venue.
