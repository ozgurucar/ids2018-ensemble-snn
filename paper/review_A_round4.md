# Review A, Round 4 (final check: methodology and statistics)

**Paper:** `paper/main.tex` at commit `467aab3` (327 lines). I rebuilt it with `tectonic -X compile` into a scratch directory: 8 pages, no errors, no overfull boxes, no undefined references.
**Records checked:**
- `results/v5/seeds/summary.json`
- `results/analysis/seed_stats_5seed_table.md`, including the new TOST section
- `results/analysis/group_bootstrap_table.md`
- `results/analysis/noport_table.md`
- `results/analysis/energy_unified.json`
- `paper/figures/figure_data.json`
- the README

## Final score: 8 / 10 (accept). Confidence 4/5.

Round history: 5 → 7 → 8.

**Justification.** Every item on my round-3 top-5 list is resolved, and each new number I checked matches the records. The paper now states its central claim at the strength the evidence supports. In five seeds there is no evidence that spiking adds accuracy, and the E-SNN is equivalent to a spike-free PLE-MLP within 2 points at the 5% budget (TOST). The best neural model is the non-spiking Enc-ANN; the paper says that the fusion head is an unresolved confound and calls the Enc-ANN edge exploratory. XGBoost is ahead (Holm p = 0.002, and it also survives Holm over all 16 tests). The energy section is internally consistent, the port ablation is reported in full, and a group bootstrap now covers test-sampling variance for DR, FAR and AUC.

What keeps it at 8 rather than 9 is design limits, all of which the paper now discloses (l. 314):
- a single split seed;
- episode-level leakage;
- an incomplete 2017 copy;
- primary-run and PLE choices made after review, with only seeds 45–46 new;
- macro-F1 intervals that cover seed variance only.

None of these is an error. They limit how far the null result generalises.

## My round-3 top 5: status

| # | Round-3 item | Status | Evidence |
|---|---|---|---|
| 1 | Abstract transfer range wrong; s.d. roundings; 0.49; the 0.787/0.779 label | **Resolved** | l. 21: "23%–32% … and 13.5%–34.4% when retrained without the destination port" matches `noport_table.md` (0.135 / 0.310 / 0.344). E-SNN 0.011 and XGB 0.004 match `v5 … std` = 0.01148 / 0.00449. l. 304 now reads "0.48". l. 117 says "compared with the three-seed runs that include it". The old Table III is removed and the three-seed T values are in the text with seed counts (l. 234). |
| 2 | Encoding claim stronger than the data; no TOST | **Resolved** | l. 21, 38, 167, 308, 318. TOST E-SNN vs PLE-MLP: p = 0.020 (13 classes) and 0.031 (11 classes) at 5%; not at 1%; E-SNN vs MLP not equivalent (p = 0.074). All match `seed_stats_5seed_table.md`. Enc-ANN − MLP is +2.4 / +3.7 with 90% CIs excluding 0, and Enc-ANN − PLE is +1.8 to +2.2; both match. The fusion confound is stated (l. 167, l. 308). |
| 3 | Fig. 2(b) contradicted Table IV | **Resolved** | `figure_data.json` uses `energy_unified.json` (complete model: E-SNN 0.177 / 0.333 / 0.490, MLP 0.398, +SRAM lines, Loihi). The preview shows the E-SNN crossing above the MLP at T = 12, consistent with l. 207. Panel (a) uses five seeds at T = 4 and five-seed reference lines (caption l. 239). |
| 4 | Port effect understated; no-port Enc-ANN transfer missing | **Resolved** | l. 117: 2.0 / 2.9 / 1.2 points on MF1-11 (XGB Holm 0.002), with the erratic label-conflicted classes named. l. 269: no-port Enc-ANN FAR 12.7%, recalibrated DR 34.4%, AUC 0.686. l. 314: "one to three macro-F1 points". |
| 5 | Partition variance / group bootstrap; PLE capacity; post-hoc primary switch | **Resolved within stated scope** | l. 167: 2.29M groups, 200 replicates, E-SNN DR 95.89 [95.47, 96.46], FAR 4.91 [4.84, 4.98], E-SNN − XGB −0.84 [−0.93, −0.72], all paired signs kept. All match `group_bootstrap_table.md`. l. 125: 71 hidden units (I re-derived 71.0 from 85,923 parameters), uniform bins on quantile-scaled input. l. 129 and l. 314 disclose the post-review primary switch and that only seeds 45–46 are new. A split-seed redraw remains undone and is stated. |

## Other round-3 points

- **Repository artefacts: resolved.** `seed_stats_5seed_table.md` has no self-comparisons, the header now says T4, and the TOST table covers the model pairs. The README covers v5, `results/analysis/` and the scripts, gives the exact `seed_stats.py` command, lists which inputs live outside the repository (l. 70–72), and the table numbers match the paper. `results/v5` is now 5.6 MB.
- **Energy wording: resolved.** The l. 207 MLP figure is labelled "linear layers (0.39)" vs 0.40 total. l. 230 now gives "7.8 to 22.5 times … or 2.5 to 7.2 times with SRAM", which matches `energy_unified` ratios. The INT8 parity at T = 12 is stated. "Every cost model in Table IV that applies to it" is correct.
- **Holm family specification: resolved.** Holm is applied within each metric and budget, and the 16-test check is stated.

## Still wrong or worth a final touch (none blocking)

1. **l. 21 / l. 38 / l. 318.** The abstract and conclusion say "equivalent … within 2 points" without the qualifier "at the 5% budget". The result fails at 1% (TOST p = 0.087). l. 167 states this correctly. Add "at 5% FAR" in the abstract sentence. *Text, minor.*
2. **l. 167.** The 2-point TOST margin is not justified. It equals the five-seed MDE80, which is a defensible reason; say so in half a sentence. The test is also unadjusted; say "exploratory" or note that it is a single declared equivalence test.
3. **l. 167.** One fact is missing: the PLE-MLP is itself equivalent to the raw MLP at 5% (TOST p = 0.001). Under parameter matching, binning adds nothing over the raw MLP. This supports the capacity caveat at l. 125 and is the honest complement to "E-SNN ≈ PLE-MLP". It takes one clause.
4. **l. 167.** "Macro-F1 gaps are several points" holds only for the XGBoost and Enc-ANN comparisons. E-SNN − MLP is 1.1 points and E-SNN − PLE-MLP is 0.5. Write "up to several points".
5. **Fig. 2(a).** The E-SNN and Enc-ANN lines join a five-seed point (T = 4) to three-seed points (T = 8, 12). The caption says so, but a hollow or distinct marker at T = 4, or no connecting line, would stop readers from reading a trend across different seed counts. *Cosmetic.*
6. **l. 69–70.** Underfull-hbox warnings from the long `\texttt` Kaggle slug. Allow a break or move the slug to a footnote. *Cosmetic.*

I found no remaining mismatch between a number in the text and the records. Additional values spot-checked in this round:
- KS 0.005–0.014 holds across both runs (v5: 0.0056–0.0137).
- Achieved FAR is 4.9–5.0% in both runs.
- The bootstrap's 2,289,573 groups.
- TOST and exploratory CIs.
- Fig. 2 data.
- The README result table.

## Agreement with B and C

**B (round 3: 7; asked for a fusion-matched control for a firm 8).**
- *Agree:* the three-branch fusion confound is the paper's most important open question. The paper now states it plainly (l. 167, l. 308) instead of claiming the encoding carries the gain.
- *Disagree that it is required for 8:* the paper no longer claims what the control would test. Its headline is the negative "no evidence that dynamics add accuracy", supported by E-SNN vs Enc-ANN, PLE-MLP and MLP. That headline does not depend on resolving codes-vs-fusion.
- *Agree:* a second split seed would be the most valuable new experiment. It is a GPU item, and the limitation is disclosed. The group bootstrap answers B's narrower concern about test sampling for the binary metrics.
- *Resolved:* B's E3–E9 (inconsistent T = 4 numbers, energy baseline, missing no-port Enc-ANN row, per-class wording, Holm families, artefact bug, nits). All are fixed in this revision.

**C (round 3: 7; text + CPU items to reach 8).**
- *Agree, and resolved:* E1–E5 and R1–R3. The README rewrite, `\texttt` slugs, captions, the checkpoint list (l. 322 now names exactly what is released) and the `seed_stats` command are all done.
- *Remaining:* outsiders still cannot rerun the no-port and T = 4 Enc-ANN transfer numbers, because those checkpoints are not released (l. 322 says so) and the 2017 data must be fetched. I agree this caps the artefact story, but it is disclosed and does not affect correctness.
- *Agree on N1 (bootstrap from the stored scores):* it is now done. C was right that the "per-row scores were not saved" reason was weaker than stated; the authors acted on it.

**Overall:** I expect B and C to land at 7.5–8 on this revision. My 8 rests on the paper now being correct, internally consistent and honest about scope. The open items (second split seed, fusion-matched PLE ensemble, complete or corrected 2017 data, time-blocked split) are extensions, not fixes.
