# Review C: presentation, clarity and reproducibility

**Paper:** "What Do Spikes Buy in Flow-Based Intrusion Detection? A Leakage-Controlled Study of an Ensemble Spiking Network on CSE-CIC-IDS2018"
**Reviewer focus:** structure and flow, float placement, table/figure/caption clarity, terminology and notation, tone, abstract length, reproducibility from README + scripts.

**Overall score: 6 / 10** (clearly written, honest and unusually well-instrumented; held back by an over-long abstract, two unreferenced figures, a results section whose order forces forward references, and terminology drift. All fixable in one revision.)
**Confidence: 4 / 5** (I read the source and the rendered PDF page by page, ran the test suite, started the detector without Docker, and re-ran the energy and figure scripts in a scratch copy.)

---

## Summary

The paper compares a three-branch ensemble SNN with a parameter-matched MLP, a spike-input control (Enc-ANN) and three tree ensembles on CSE-CIC-IDS2018. The protocol keeps identical feature vectors in one partition and judges every model at a fixed benign false-alarm rate. It adds a time-window ablation, an architecture screen, a duplicate-vector audit, two energy cost models, a cross-dataset test on CIC-IDS2017 with a label-budget adaptation study, and a containerised detector.

The prose is plain, precise and mostly free of hype. Numbers in the text agree with the tables and with the JSON records in `results/` (I spot-checked Table II against `results/v3/experiments/group_ce/summary.json`, and the abstract's derived ratios: 2.9x, 69%, 2.4 to 22x, 26x, 4x, 40x all check out). The released detector works and reproduces the Section VI numbers exactly. The weaknesses are about presentation. The abstract is about 410 words, Figs. 1 and 2 are never cited in the text, the energy material is spread over three subsections that reference each other out of order, and the same concept goes by three or four names (FPR/FAR/false-alarm rate, ANN/MLP/perceptron, "budget" for two different things). Reproducibility is good for the inference and energy parts. For training it depends on Kaggle paths and an environment the README does not describe.

The rendered PDF is exactly 8 pages; page 8 holds only references, and its right column is empty.

---

## Major issues

### M1. Abstract is roughly 410 words; IEEE recommends 150–250
*Location:* abstract (line 21).
*Why:* At ~410 words it fills the whole left column of page 1 in bold and reads like a condensed results section. It lists seven separate findings, five numbers to three decimals, and the architecture screen, which is a secondary result. Many IEEE conferences enforce the 250-word limit in the submission system, so the abstract may be truncated or rejected at upload.
*Fix:* Cut to ~230 words. Keep: motivation, protocol, the main comparison, the encoder-vs-dynamics reading, the energy sign flip, transfer and adaptation. Drop: KS statistic-level detail, the architecture screen, per-model numbers for RF/CatBoost (give a range), the 45 nm 69% figure. Proposed replacement (≈225 words):

> Spiking neural networks (SNNs) are often proposed for network intrusion detection because neuromorphic hardware could run them cheaply at the network edge. Most reported results, however, rest on random row splits of benchmarks that contain many duplicate flows, and they omit tree-ensemble baselines. We revisit the question on CSE-CIC-IDS2018 (16.2 million flows, 13 classes). Rows with identical feature vectors stay in one partition, model fitting, probability calibration, threshold selection and testing use disjoint partitions, and every model is judged at the same benign false-alarm rate. At a 5% false-alarm rate, a three-branch ensemble SNN (rate, latency and population coding; 86k parameters) reaches a macro-F1 of 0.769 ± 0.022. It beats a parameter-matched multilayer perceptron (0.756) but trails a non-spiking network fed the same spike encodings (0.787) and three tree ensembles (0.788–0.808). Attack detection rates differ by less than one point. Two of the hardest classes are nearly unlearnable, because almost all of their feature vectors also occur under other labels. Shortening the SNN's time window from 12 to 4 steps leaves macro-F1 unchanged and cuts synaptic events 2.9-fold. Even so, with published Loihi per-operation costs the SNN needs about 3.0 μJ per flow, against 0.4 μJ for the perceptron. The encoders, not the spiking dynamics, appear to carry the benefit. After threshold recalibration the frozen models detect only 23–32% of CIC-IDS2017 attacks, whereas about 1,100 labelled local flows restore detection above 98%. Code, checkpoints and a containerised detector are released.

### M2. Figures 1 and 2 are never referenced in the text
*Location:* `\label{fig:arch}` (line 116) and `\label{fig:steps}` (line 165). The only `\ref{fig:…}` in the source is to `fig:transfer`.
*Why:* IEEE style expects every float to be cited, and readers of Section IV-B (E-SNN) and Section V-B (time window) are never pointed to the figures that explain them. Fig. 1 also floats to the top of page 4, a full page after its description on page 3.
*Fix:* In Section IV, E-SNN paragraph, first sentence: "Three branches (Fig.~\ref{fig:arch}) share the same architecture …". In Section V-B: "The neural comparison is repeated in Table~\ref{tab:steps} and Fig.~\ref{fig:steps} with 4 and 8 time steps …". Consider moving the `figure*` block before Section IV in the source so that it lands at the top of page 3.

### M3. Results order forces forward references; energy is split across three places
*Location:* Section V-B (Table III, Fig. 2), V-E (Tables VI, VII). Table III's caption says "energy with the optimistic 45 nm model of Table VI (see Table VII for Loihi costs)". Fig. 2(b) plots Loihi costs that are only defined two subsections later. V-C says "the label conflicts described in the next subsection".
*Why:* The reader meets the energy column, the AC counting rule and the Loihi cost model in the reverse of the order they are explained. Table VI repeats the T = 12 row of Table III (ACs 339,801, energy 0.32 μJ for the E-SNN; 28,956 and 0.05 μJ for the Enc-ANN; 0.39 μJ for the ANN). This costs space in an 8-page paper that is already full.
*Fix:* Reorder Section V as follows: A. Detection at a fixed budget (Table II). B. Where the errors are (Table V + audit), which removes the forward reference from the screen. C. Operation counts and energy: define the AC/MAC counting and both cost models here. D. Shorter time windows: Table III + Fig. 2, which now only reference backwards. E. Architecture screen. F. Transfer. Then merge Table VI into Table III by adding a MACs column and a CPU-time column for T = 12, or drop Table VI and give the CPU times in text. This saves roughly a quarter column and puts all the energy material in one place.

### M4. Terminology drift: false-alarm metric, baseline names, branch names, and "budget"
*Location:* throughout.
- **False-alarm metric:** Table II uses "FPR" and "ADR". Tables VIII and IX use "FAR" and "DR". Fig. 2(a) has the y-label "Macro-F1 at 5% FAR". The text says "false-alarm rate", "false-alarm budget", "benign false-alarm budget" and "benign alarm threshold". README says "5% FPR budget".
- **Baseline name:** "Matched ANN" (tables), "parameter-matched multilayer perceptron" / "matched perceptron" (abstract, conclusion), "dense perceptron" (Discussion), "ANN" (Table V, VII), "MLP" (README).
- **Control name:** "spike-input control", "Enc-ANN", "Enc-ANN (control)", "the control", "a plain network that is fed the same spike encodings".
- **Branch name:** Section IV calls it the *temporal* branch, while Fig. 1, the abstract and Related Work say *latency*.
- **"Budget" means two things:** the false-alarm budget τ, and in Table IX and Section V-F the *label* budget ("Budget: share of the 2017 adaptation pool with labels"). In Table IX a row reads "Budget 5%" next to a 5% alarm threshold. The two are easy to confuse.
- **Class names:** "SSH-Bruteforce" vs "FTP-BruteForce". Fig. 3 uses the 2017 spellings ("DoS slowloris", "DoS Slowhttptest", "DoS Hulk") while the text uses "DoS-Slowloris", "DoS-Hulk".
*Fix:* Choose one of each and define it once in Section III-D: "false-alarm rate (FAR)", "detection rate (DR)", "FAR budget τ". Use FAR/DR in every table and figure. Call the baseline "Matched MLP" everywhere (also in Table V's "ANN" column and Table VII). Name the control "Enc-ANN" after its single definition. Rename the branch to *latency* in Section IV. Rename the Table IX column to "Labelled share" and use "label budget" in Section V-F. Normalise class names to "SSH-BruteForce" and map the Fig. 3 tick labels to the 2018 names, with the 2017 name in parentheses if needed.

### M5. Contributions list omits two of the paper's main results
*Location:* Introduction, bullet list (lines 36–42).
*Why:* Section V-F calls the cross-dataset transfer "the most practically relevant finding of the study", and the abstract and Discussion give the two-cost-model energy comparison as much weight as the accuracy comparison. Neither appears among the contributions, while the containerised detector, an engineering artefact, does.
*Fix:* Replace bullets 4–5 with:
> - A time-window ablation ($T \in \{4,8,12\}$) and an energy estimate under two cost models (45\,nm arithmetic and published Loihi per-operation costs), which disagree on whether the SNN is cheaper.
> - A transfer test of the frozen detectors on CIC-IDS2017 and a label-budget study of local adaptation, together with a containerised detector for testing on new flow records.

Move the architecture screen into the first bullet's results or into the limitations. It is a negative control, not a contribution.

### M6. Training hyperparameters and encoder details are missing from the paper
*Location:* Section IV.
*Why:* An outsider cannot rerun the E-SNN from the paper alone. Missing: optimiser, learning rate (4e-4 in `configs/group_ce.json`; the paper only reveals indirectly that 1e-3 is a variant), batch size (1024), weight decay (1e-3), early-stopping patience (10), the hidden widths of the Matched MLP and Enc-ANN, Gaussian receptive-field centres and widths, the definition of the "phase-accumulator" rate code, the initial LIF decay, the training-cap rule (`rare_preserve = 10000`, not "kept in full"), the ratio of the calibration sub-split, and the tree hyperparameters ("fixed, commonly used" is not reproducible; e.g. `catboost_trees = 600`).
*Fix:* Add a compact "Training details" paragraph or a small table, e.g.: "All neural models use Adam (lr $4\times10^{-4}$, weight decay $10^{-3}$, batch 1024), at most 35 epochs, patience 10. The Matched MLP has hidden widths … ; Enc-ANN … . RF: 300 trees, depth 25; XGBoost: …; CatBoost: 600 iterations, … . Full configurations are in `configs/`." State the alarm-calibration/probability-calibration split ratio in Section III-B.

### M7. Equation (1) and the decision rule are ambiguous about which logits are used
*Location:* Section III-D.
*Why:* The text adds a prior offset to z and then writes s(x) in terms of z. It is not clear whether z in Eq. (1) is before or after the offset. The temperature is applied to the benign term but the offset is not mentioned. "Assigned the most probable attack class" does not say whether this uses calibrated probabilities.
*Fix:* Define $\tilde z_c = z_c + \log\pi_c^{\mathrm{full}} - \log\pi_c^{\mathrm{train}}$, then write $s(x)=\log\sum_{c\neq\mathrm{B}} e^{\tilde z_c/T_\mathrm{cal}} - \tilde z_\mathrm{B}/T_\mathrm{cal}$ and "the predicted attack class is $\arg\max_{c\neq\mathrm{B}} \tilde z_c$". Also note in passing that $T$ (time window) and $T_\mathrm{cal}$ (temperature) are distinct. The notation is already kept apart, but Fig. 1 places "divide by $T_\mathrm{cal}$" next to "mean over $T$", so one clause helps.

---

## Minor issues and typos

1. **Last page:** page 8 holds only references in the left column; the right column is empty. Add `\IEEEtriggeratref{N}` or `\balance` (package `balance`) to balance the columns.
2. **Table I:** the uneven Tune/Cal./Test ratios for some classes (DoS-SlowHTTPTest 6,487 / 568 / 11,441; SSH 9,435 / 9,888 / 61,742) look like an error until the reader realises that large duplicate groups are assigned whole. Add one caption sentence: "Ratios per class deviate from 60/10/10/20 because whole duplicate groups are assigned to one partition." "Train used" → "Train (capped)".
3. **Table II** is placed inside Section IV (page 3, before "Matched ANN"), which is acceptable for a top float. FPR has no ± while the other columns do, so add "(mean)" or give the s.d.
4. **Table III:** the Enc-ANN AC count *falls* as T grows (30,272 → 28,956) and so does its energy. The reader will expect the opposite (a longer flattened input). One sentence is needed: the hidden width shrinks to keep parameters matched. The "–" for the Matched ANN T and "0" ACs are fine, but say "dense" in the T column instead of "–".
5. **Table IV** mixes an argmax tuning metric with a 5%-budget test metric in one table. The caption says so, but the text should give the reason (the selection rule was fixed before the budget-based protocol). "Seed 42 of the original reached 0.756" → "The original model (seed 42) reached 0.756".
6. **Table V** silently omits CatBoost. Add a column, or "(CatBoost lies between RF and XGB and is omitted for space)".
7. **Table VIII vs IX:** frozen E-SNN T = 4 recalibrated DR is 0.239 in Table VIII but 0.268 in Table IX, and its FAR in Table IX is 0.062 despite a 5% threshold. Both are explainable (different evaluation subsets; calibration-to-test shift), but neither is explained. One clause each.
8. **Table IX** order: grouping by method (all E-SNN rows, then all XGBoost rows) or giving budgets as columns would make the trend readable at a glance. `fig_finetune.pdf` is generated by `make_figures.py` but unused; either use it in place of Table IX or stop generating it.
9. **Fig. 1:** the smallest labels ("deterministic phase code", "one spike, earlier if larger", the orange note under the Enc-ANN box) render at about 5 pt in print. Enlarge to ≥7 pt or drop the subtitle lines. The meta-net dimensions "39→64→13" appear only in the figure; mention them in the text or remove them.
10. **Fig. 3:** "<0.1%" labels overlap the dashed 5% line and the "0" annotations clutter the Bot/Infiltration/Heartbleed rows. The dashed-line label "Benign false-alarm rate (5%)" overlaps the top bars. Move the line label into the legend; drop the "0" annotations or put "n.d." once.
11. **Fig. 2(a):** the y-label "Macro-F1 at 5% FAR" should match the term chosen in M4. The 1% budget results, which the text discusses, are not plotted; either add them as a faint series or drop the 1% discussion from V-B.
12. **Abstract vs conclusion:** "factor of 2.9" vs "factor of three". Use one.
13. **"Any reported error below that floor on this representation is a sign of leakage"** (V-D): "error" is ambiguous (macro-F1? row error?). Write: "any row-level accuracy above 98.9% on these features indicates leakage".
14. **"which also confirms that training on Kaggle is deterministic for a fixed seed"** (V-C): one matching rerun does not confirm GPU determinism, and the platform name is unnecessary. Proposed: "Its seed-42 run reproduced the screening result to four decimals (0.7620)."
15. **Internal version labels** ("This protocol (v3)", "an earlier version of the study") are project jargon. Write "the protocol in this paper was designed after we had seen test results of an earlier, row-split version of this study …".
16. **Section VI** (containerised detector) is short and mostly engineering. Consider folding it into the Reproducibility section to save space for M6.
17. **Tone and sentence openers:** generally sober. A few phrases read as filler or editorialising: "The headline result is mixed and, we think, useful." (Intro); "What we add is a combination." (Related Work); "We see this as the most practically relevant finding of the study." (V-F). Many consecutive sentences start with "The …" or "This …" (e.g. the E-SNN paragraph, the V-E Loihi paragraph). Suggested: "Our results are mixed." / "Our contribution is to combine three controls that prior work applies separately: …" / "This is the most practically relevant result." Short choppy pairs such as "The first is the data. The CIC datasets…" can be merged.
18. **Related Work, "Spiking networks":** "the choice of code can matter as much as the neuron model" has no citation. Cite Patel et al. [18] here, which is the source of that finding.
19. **Bibliography:** "Neyman-pearson" → protect capitalisation in `references.bib` (`{N}eyman--{P}earson`). Ref. [18] is "to appear" with a 2026 arXiv id; check its status before camera-ready.
20. **Dataset provenance:** the paper says only "as distributed on Kaggle". Name the Kaggle mirror (`solarmainframe/ids-intrusion-csv`, as in the README) and the CIC-IDS2017 source used (`sweety18/cicids2017-full-dataset`, MachineLearningCVE files), so that the "missing Tuesday / Thursday morning" remark can be checked.
21. **Anonymity:** the author name, e-mail and GitHub URL are in the PDF. If the target venue is double-blind, anonymise the repository link.
22. **Title** runs to four lines on page 1. "What Do Spikes Buy in Flow-Based Intrusion Detection? A Leakage-Controlled Study on CSE-CIC-IDS2018" would fit in three.
23. **Macro-F1 rises as the budget tightens** (e.g. E-SNN 0.789 at 1%, 0.769 at 5%, 0.754 at 10% in `summary.json`). This is counter-intuitive for readers who think of ADR. One sentence in V-A explaining that precision on rare classes dominates macro-F1 would pre-empt a reviewer question.
24. **Energy, Enc-ANN missing from Table VII:** `results/v4/energy_loihi.json` already contains the Enc-ANN on the 45 nm accelerator (0.05–0.09 μJ) and with SRAM weight reads (0.39–0.52 μJ, still below the Matched MLP's 1.24 μJ). Table VII lists only the E-SNN and the MLP, yet the Discussion says the control "beats the spiking version on both accuracy and estimated energy". Add the Enc-ANN rows to Table VII so that the claim is visible under the hardware-style cost model as well.

---

## Reproducibility findings (what I actually ran)

Environment: `~/.cache/ids-run-venv` (Python 3.12, torch 2.10.0, snntorch 1.0.0, xgboost 3.2.0, fastapi 0.115.12). No Docker.

| Check | Result |
|---|---|
| `python -m pytest -q tests` | **41 passed, 1 failed.** The failure is `tests/test_v3.py::test_tree_ce_is_unweighted_and_class_mapping_is_preserved[catboost]`: `ModuleNotFoundError: No module named 'catboost'`. `catboost` is listed in `requirements.txt`, but the README never tells a reader to install `requirements.txt` or how to run the tests. `app/requirements.txt`, the only install command in the README, has neither `catboost` nor `pytest`. |
| `python -m idsresearch --help` | Works, but the help text points to `docs/PLAN_TR.md`, which does not exist in the repository. |
| `python -m idsresearch smoke --out …` (README's code check) | **Fails** in the same environment on `catboost` import after the CNN/ANN stages. So the README's "checks the code on synthetic data" step does not pass with the documented app environment. |
| Detector without Docker (`uvicorn server:app --app-dir app`, `PYTHONPATH=.:app`) | **Works.** `/health` → `{"status":"ok","models":["esnn","esnn_t4","xgb"],"demo":true}`. `/api/demo`: E-SNN DR 1.000, FAR 0.0125, 15,695 flows/s; E-SNN T=4 DR 1.000, FAR 0.020; XGBoost DR 1.000, FAR 0.0238. These match Section VI (1.3% and 2.0%) and the ">15,000 flows per second" claim. |
| `app/replay.py app/samples/demo_flows.csv --url …` | Works; streams per-flow ALARM lines. |
| `scripts/energy_loihi.py` (run in a scratch copy because it overwrites `results/v4/energy_loihi.json`) | **Reproduces Table VII exactly** (3.02 / 5.87 / 8.77 μJ; ANN 0.398 / 1.242 μJ). The output differs from the committed JSON only in the absolute checkpoint path. |
| `scripts/make_figures.py --skip-tikz` (scratch copy) | **Reproduces `figure_data.json` byte-identically**; all figures regenerate from `results/`. |
| Main tables vs records | Table II means and s.d. match `results/v3/experiments/group_ce/summary.json`; class-weighted numbers (0.753, 0.747) match `group_weighted`. |

Gaps an outsider would hit:
1. **No environment instructions for training or tests.** README → add: `uv pip install -r requirements.txt` (or `pip install -e .`), then `pytest -q`, then `python -m idsresearch smoke`. Point to `results/v3/requirements-run.lock.txt` as the exact pins. The paper says "package versions are pinned in the repository", but the top-level `requirements.txt` has only ranges.
2. **`scripts/profile_all_steps.py` cannot run from the repository.** It hardcodes a Kaggle working-directory layout (`sys.path.insert(0, "code")`, `raw/*.csv`, `v3/ids2018-v3/experiments/...`, `steps/v4/...`). README says it "needs the checkpoints from Kaggle" but gives no link to those checkpoints. In two places the README says different scripts (`profile_all_steps.py`, `profile_efficiency.py`) reproduce the operation counts.
3. **Only seed-42 checkpoints are shipped** (`app/models/`: E-SNN T=12/T=4, XGBoost; `app/models/profile/`: ANN, Enc-ANN). The paper's Reproducibility section says "frozen checkpoints" without qualification. Seeds 43/44, T=8, the variants and the fine-tuned 2017 models are not in the repo. State this, or publish them (e.g. as a Kaggle dataset or Zenodo record with a DOI).
4. **README coverage is incomplete.** "Every number in the paper can be checked" is not yet true from the README. It has no rows for Table VII (`scripts/energy_loihi.py`), Table IX (`scripts/finetune_cic2017.py` / `results/cross_dataset/finetune_cic2017.json`), Figs. 2–3 (`scripts/make_figures.py`), or building the paper (`scripts/build_paper.sh`). The README title still says "(v3)", but the paper also reports v4 and cross-dataset results.
5. **User-specific paths:** script docstrings say "run with `~/.cache/ids-run-venv/bin/python`". Replace with `python`.
6. **Non-English artefacts:** `results/v3/README_TR.md`, `STATUS_TR.md` and the `docs/PLAN_TR.md` reference are in Turkish or missing; outside readers will not follow them. Translate, or move them out of the public tree.
7. **Training requires Kaggle.** That is acceptable, but the `kaggle/v4-*/template.py` notebooks are not mentioned in the README; say how they map to `idsresearch derive`.

Overall: inference, energy estimates and figures are reproducible offline in minutes, which is better than most IDS papers. Training and op-count profiling are reproducible only for someone who reconstructs the Kaggle layout.

---

## What would raise the score to 8+

1. Abstract cut to ≤250 words (M1); contributions list aligned with the actual findings (M5).
2. Every figure cited; Section V reordered so that energy is defined once and only referenced backwards; Table VI merged into Table III (M2, M3).
3. One name per concept across text, tables and figures: FAR/DR, Matched MLP, Enc-ANN, latency branch, "label budget" vs "FAR budget" (M4).
4. A training-details paragraph or table with optimiser, learning rate, batch size, widths, encoder parameters and tree hyperparameters (M6), and an unambiguous Eq. (1) (M7).
5. README: a three-command "reproduce tests and smoke run" block that passes on a clean machine; a claim→script table covering Tables VII, IX and Figs. 2–3; a link to all checkpoints; and a `profile_all_steps.py` that runs from the repository root.
6. Cosmetic fixes: balanced last page, Fig. 1 font size, Fig. 3 label overlaps, CatBoost in Table V.
