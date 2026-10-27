# Review C, round 4 (final): presentation, clarity and reproducibility

**Final score: 8 / 10. Confidence 4/5.**

The paper is now clear, internally consistent and honest about its scope. All five of my round-3 items are resolved in the manuscript. The score is conditional on three release-side problems (Section 3) being fixed before submission. None of them requires a change to `main.tex`. Without those fixes, the paper's reproducibility statement (l.322) points to a public repository that does not contain this revision, and I would score it 7.5.

## 1. What I checked

**Clean clone.** I exported the committed tree with `git archive HEAD` (32 MB; the per-row `.npy` files are gone) and ran everything below on that copy with `~/.cache/ids-run-venv`.

**README "Install and test":**
- `pytest -q tests`: 44 passed.
- `python -m idsresearch smoke`: passes. The CatBoost failure from round 1 is gone.
- `--help` no longer points to the missing `docs/PLAN_TR.md`.

**README "Verify the claims", records-only table.** I ran every row:

| Command | Result |
|---|---|
| `seed_stats.py` (5-seed, the documented command) | Byte-identical to the committed table. |
| `seed_stats.py` (3-seed) | Byte-identical. |
| `identifiable_macro_f1.py`, `operating_context.py`, `adapt_summary.py` | Byte-identical. |
| `make_figures.py --skip-tikz` on a pristine clone | Works; `figure_data.json` is identical. |
| `energy_unified.py --skip-test-mix` | Runs, but breaks the repository state. See B1. |

**PDF.** I built it with tectonic from the clean clone: 8 pages, no errors, references balanced on page 8. Abstract: about 249 words. I rendered every page and checked every float.

**Spot checks against the records:**
- l.167: the bootstrap numbers (E-SNN DR 95.89 [95.47, 96.46], FAR 4.91 [4.84, 4.98], E-SNN − XGBoost −0.84 [−0.93, −0.72], 2.29 M groups, 200 replicates) match `results/analysis/group_bootstrap_table.md`.
- Table II: the s.d. values (0.011 for E-SNN, 0.004 for XGBoost) now match `results/v5/seeds/summary.json`.
- The TOST p-values and the l.117 port figures (2.0 / 2.9 / 1.2, Holm 0.002) match `seed_stats_5seed_table.md` and `noport_table.md`.

## 2. My round-3 top 5: status

| # | Item | Status |
|---|---|---|
| 1 | "Matches" and the causal encoding claim (l.21, 38, 167, 308) | **Resolved.** TOST shows E-SNN ≡ PLE-MLP within 2 points at 5% (p = 0.020), and the paper says this does not hold at 1% or against the MLP. "No evidence that spiking dynamics add accuracy" is now the claim. The fusion confound is stated (l.167, l.308). The PLE-MLP capacity confound (71 vs 252 hidden units) is stated (l.125). |
| 2 | Fig. 2(b) contradicts Table IV | **Resolved.** It is regenerated from `energy_unified.json` (complete 45 nm, +SRAM, Loihi), and panel (a) uses the 5-seed T = 4 points with PLE-MLP as a reference. It is full column width and the fonts are legible. The labels "MLP, 45 nm" and "E-SNN, 45 nm" crowd near 0.4 µJ but remain readable. |
| 3 | README stale | **Resolved in content.** The README has current numbers, the qualified slow-DoS claim, a claim → command → output table, and a separate table of what needs data outside git and where it comes from. Two new defects are in Section 3. |
| 4 | Inconsistent T = 4 numbers and minor slips | **Resolved.** The 3-seed vs 5-seed T = 4 values are labelled (l.117, l.234, Fig. 2 caption). The 0.39 / 0.40 distinction is explicit (l.207). The "2.5–22" range is split by baseline (l.230). 0.48 is fixed (l.304). The Kaggle slugs use `\texttt`. The PLE-MLP width and bin fitting are given. The Table II/III captions are fixed. The post-hoc primary-run switch and PLE-MLP addition are disclosed (l.129, l.314). |
| 5 | Analyses not reproducible from the repository | **Mostly resolved.** Every analysis that needs data outside git is now listed with its source, and `seed_stats.py` is fixed (no self-comparisons, correct T label, documented command works). What remains: those sources must be publicly reachable (B2, B3). |

## 3. Still wrong

### Blocking for the reproducibility claim (repository/release; `main.tex` unaffected)

**B1. A README command overwrites a committed result and breaks the next command.**
- **What happens:** The "Energy, demo sample only" row runs `python scripts/analysis/energy_unified.py --skip-test-mix`. That rewrites `results/analysis/energy_unified.json` and `energy_unified_table.md` with an **empty** `test_mix` section.
- **Effect on figures:** The next row, `python scripts/make_figures.py --skip-tikz`, then fails with `KeyError: 'esnn_T4'` (`make_figures.py` l.121), because Fig. 2(b) reads `test_mix`.
- **Effect on results:** The committed Table IV source is destroyed in the reader's checkout. I reproduced this on a clean clone; `make_figures.py` works only if the energy row is skipped.
- **Fix (any one):**
  - With `--skip-test-mix`, keep the existing `test_mix` block (merge instead of overwrite).
  - Or write to a different file (e.g. `energy_unified_demo.json`).
  - Or move the energy row below the figures row and warn that it rewrites the file.

**B2. The public repository does not contain this revision.**
- **What I found:** The local `main` is **15 commits ahead of `origin/main`** (`git status -sb`). https://github.com/ozgurucar/ids2018-ensemble-snn returns 200 but serves the old tree: no `results/v5`, no `results/analysis`, no new README.
- **Why it matters:** l.322 points readers there.
- **Fix:** Push before submission (or before the arXiv version), and tag the commit that matches the submitted PDF.

**B3. The Kaggle outputs named as sources are not publicly reachable.**
- **What I found:** `https://www.kaggle.com/code/ozgurucar/ids-v5-seeds` returns 404. That source is named in l.322 and in the README for the per-row scores, `test_y.npy` and `test_groups.npy`; the README also lists `ids-v5-noport` and `ids-v4-steps`. A private kernel or a different slug would both give 404.
- **Why it matters:** The group bootstrap (l.167), the no-port transfer row (l.269) and the Table IV test-mix energies cannot be rerun by an outsider unless these outputs are public.
- **Fix:** Make the three kernels public and give full URLs. Better still, deposit the score files, the two v5 arrays and the no-port checkpoints in a Zenodo record with a DOI and cite it in l.322.

### Not blocking (text)

1. **l.21 and l.318, "the best neural model is the non-spiking spike-input control".** This ranks by mean only. Enc-ANN vs E-SNN is not significant (Holm p = 0.51), and its edge over the MLP is exploratory (l.308 says so). Use "has the highest mean among the neural models".
2. **l.230, "Under INT8 arithmetic the E-SNN is cheaper than the MLP at every T (parity at T = 12)".** This contradicts itself: 0.019 vs 0.020 is parity. Write "cheaper at T = 4 and 8 and at parity at T = 12".
3. **l.167 is a single paragraph of about 350 words**, covering the declared tests, power, TOST, exploratory tests, the bootstrap and the T = 12 check. Split it after "…3.4 points against Enc-ANN." and before "A bootstrap over…".
4. **l.167, "every paired DR and AUC difference keeps its sign".** Spell out what this means: the 95% bootstrap interval excludes zero. Add that the bootstrap holds thresholds fixed, so threshold re-estimation is not covered. The text says "models and thresholds fixed", which is accurate, but the consequence should be stated in one clause.
5. **l.322:** add the commit or tag and the Zenodo DOI once B2 and B3 are done.

## 4. A's and B's remaining concerns

- **Second split seed (A, B).** Agree that it is the main unquantified uncertainty. The group bootstrap covers test sampling for the binary metrics only, and the paper now says exactly that (l.167, l.314). I accept it as a stated limitation at this venue and do not count it against the score.
- **Fusion-matched PLE ensemble (B).** Agree it would settle *why* Enc-ANN leads. Since the paper no longer claims the encoding is the cause and names fusion as an open confound (l.308), I treat it as future work, not a defect.
- **PLE-MLP capacity confound (A).** Resolved by disclosure (l.125). A wider PLE-MLP would be nice to have.
- **Post-hoc primary-run switch and test reuse (A).** Resolved by disclosure (l.129, l.314). This is the honest treatment.
- **Complete or corrected CIC-IDS2017, and a time-blocked split (A, B).** Agree these are extensions. Both are stated as limitations (l.250, l.314).
- **A's round-4 score of 8 ("open items are extensions, not fixes").** I agree on the manuscript. I differ only in making 8 conditional on B1–B3, because a reproducibility statement that points to an outdated public repository and unreachable outputs is a factual error at submission time, even though the text is correct.
