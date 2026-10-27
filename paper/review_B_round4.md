# Review B, round 4 (final check)

**Final score: 7.5 / 10** (round 1: 5, round 3: 7). **Confidence: 4 / 5.**
**Recommendation:** accept at a mid-tier IEEE venue (IJCNN, CNS). There are no blocking errors.

**What I checked.** I re-read `main.tex` at commit `467aab3` (327 lines) and built the PDF with tectonic: 8 pages, only underfull-box warnings. I rendered Fig. 2. I checked these files against the text:
- `results/analysis/group_bootstrap_table.md`
- `results/analysis/seed_stats_5seed_table.md` (TOST section)
- `paper/figures/figure_data.json`
- `README.md`

I also read A's and C's round-3 reviews and `CONSENSUS_ROUND3.md`.

**Why 7.5 and not 8.** I said in round 3 that the text and CPU fixes would bring the paper to about 7.5, and that 8 needs either the fusion-matched control or a second split seed. Both were declined, and both are now honestly disclosed. The paper is correct and calibrated. Its remaining ceiling is evidential, not editorial: one split, a test partition reused across four rounds, and post-hoc choices of the primary run and the equivalence margin. I do not round that up.

---

## 1. Resolved since round 3

| Round-3 item | Status |
|---|---|
| E1. Encoding vs dynamics overclaim | **Resolved.** |
| E2. Fig. 2(b) contradicts Table V | **Resolved.** |
| E3. Two values for the same T = 4 configuration | **Resolved.** |
| E4. Energy discussion vs Table V | **Mostly resolved.** One residue, R1 below. |
| E5. No-port Enc-ANN transfer row missing | **Resolved.** |
| E6. Per-class wording of the port ablation | **Resolved.** |
| E7. Holm families under-specified | **Resolved.** |
| E8. `seed_stats` self-comparisons and T = 12 header | **Resolved.** |
| E9. Nits | **Resolved.** |

Details:
- **E1.** The abstract (L21), L38, L167, L308 and L318 now say "no evidence that spiking dynamics add accuracy". The equivalence claim is backed by a 2-point TOST: E-SNN vs PLE-MLP p = 0.020 at 5%, and the text states it fails at 1% and against the MLP (p = 0.074). Enc-ANN − MLP is labelled exploratory. All of these match `seed_stats_5seed_table.md`.
- **E2.** I checked `figure_data.json`. Panel (b) now plots the complete 45 nm model (0.18 / 0.33 / 0.49 µJ), the +SRAM line and Loihi, against MLP 0.40 / 1.24 µJ. Panel (a) uses the five-seed T = 4 points. The render is legible at full column width.
- **E3.** Table IV is folded into Table V, and every three-seed reference is labelled (L117, L234). Standard deviations are corrected to E-SNN 0.011 and XGBoost 0.004.
- **E5.** Reported at L269: FAR 12.7%, DR 34.4%, AUC 0.686. The abstract now gives 13.5–34.4% without the port.
- **E6.** L117 now reads 1–3 points, with 2.0 / 2.9 / 1.2 on the 11 identifiable classes, consistent losses on Slowloris, Web and Bot, and erratic movement in the two label-conflicted classes. L314 matches.
- **E7.** "Holm within each metric and budget; the XGBoost gap at 5% also survives Holm over all 16" (L167).
- **E8.** There are now 0 self-comparison rows, and the header reads "T4".
- **E9.** L314 grammar is fixed. L129 now says seeds 42–44 reproduce v3/v4 and only seeds 45–46 are new. L125 gives the PLE bins (quantile), the 71 hidden units and the missing fusion.

The new disclosures meet A's R3-6:
- The switch of the primary run after review is disclosed (L129, L314).
- The use of `\texttt` for Kaggle slugs is fixed (L69, L250).
- The README now covers v5, the analyses and the data each script needs.

**Group bootstrap (L167).** This is a correct and useful addition. It shows that test sampling over 2.29 M fingerprint groups barely moves DR, FAR or AUC. It also shows that the paired binary gaps stay below one point. That supports the paper's reading that models differ in *which* class they assign, not in *whether* they alarm. The text correctly says it does not cover a redrawn split or macro-F1 (L167, L314).

### Is the declined fusion-matched PLE experiment adequately stated? **Yes.**

The paper's central claim is that membrane dynamics add no detectable accuracy. That claim rests on E-SNN vs Enc-ANN, which share the same encoders *and* the same three-branch fusion, so the confound does not touch it.

The confound only affects a secondary question: why Enc-ANN is ahead of the MLP and the PLE-MLP. The paper no longer answers that question. It calls the Enc-ANN edge exploratory and says outright that "we cannot tell whether it comes from the codes or from the three-branch fusion, since no fusion-matched PLE ensemble was trained" (L308; also L125, L167). Together with the stated PLE capacity bottleneck (71 vs 252 units, L125), the claim is now scoped to what was measured. I would still want the experiment for a journal version, but for this paper the statement is adequate.

---

## 2. Still wrong or weak (non-blocking, text-only)

**R1. The Loihi comparison uses the non-like-for-like MLP baseline in the abstract and the Discussion** (L21, L310 vs L230).
- L230 says correctly that Loihi's per-event cost already includes memory access. That makes the SRAM-inclusive MLP (1.24 µJ) the like-for-like baseline, which gives a factor of 2.5–7.2×.
- The abstract ("3 µJ … against 0.4 µJ") and L310 ("7.8 to 22.5 times") quote the memory-free MLP instead, which inflates the gap about 3×.
- The sign of the comparison does not change, so this is not an error. It is the less conservative choice in a paper that is otherwise careful.
- **Fix:** in L310, write "2.5 to 7.2 times its SRAM-inclusive cost (7.8 to 22.5 times its arithmetic-only cost)". In the abstract, add "(1.2 µJ with SRAM reads)".

**R2. "Best neural model" is a ranking by mean** (L21, L38-adjacent, L308, L318). Enc-ANN vs E-SNN is not significant (Holm p = 0.51; paired DR differences are tiny). L308 qualifies this, but the abstract and the Conclusion do not. **Fix:** write "the non-spiking spike-input control has the highest neural mean".

**R3. The equivalence margin is not justified** (L167, L38, L318).
- The 2-point margin was chosen in round 3, after the data were seen.
- It is about the size of the largest neural gap observed (Enc-ANN − MLP, 2.4 points) and of the MDE80. So "equivalent within 2 points" excludes only differences as large as the biggest one in the study.
- Equivalence holds at 5% only. L38 and L318 drop that qualifier.
- **Fix:** add one clause: "margin set after review, equal to the 80%-power MDE; equivalence holds at 5% FAR only".

**R4. Small wording points.**
- L230: "cheaper than the MLP at every T (parity at T = 12)" contradicts itself (0.019 vs 0.020). Write "cheaper at T = 4 and 8 and at parity at T = 12".
- L167: 200 bootstrap replicates are thin for 95% percentile intervals. Either increase them, or say "approximate".

I found no numeric mismatches against the records in the passages I checked:
- abstract;
- L117, L129, L167, L196, L207, L230, L269, L304;
- Table II;
- Table V;
- Fig. 2 data.

---

## 3. Agreement with A's and C's remaining concerns

**A (methods).** I agree with A's verdict that the remaining limits cap the paper's evidential weight but are acceptable for a conference once disclosed: single split, test reuse across v3, v4, v5 and the no-port run, episode-level leakage, and the incomplete 2017 copy. All of these are now in L314. All of A's R3-1 to R3-8 items appear fixed in the text. On the PLE capacity confound (A R3-5), I agree; it is now stated (L125). My only addition is R3 above: A accepted the TOST as the fix for "matches", but the margin was chosen post hoc and that deserves one clause.

**C (presentation/reproducibility).**
- **Agreed and resolved:** the PLE overstatement (C-E1), Fig. 2 (C-E2), the T = 4 inconsistency (C-E3), declaring PLE as a declared comparison (C-E4, disclosed at L129), the 0.39/0.40, ratio and Kaggle-slug items (C-E5), and the README.
- **Not verified by me:** C's Fig. 1 and Fig. 3 font sizes. Fig. 2 renders well.
- **One disagreement:** C proposed abstract wording that only says "not separable". The authors' TOST-backed "equivalent within 2 points" is stronger and is allowed, provided R3's qualifiers (5% only, post-hoc margin) are added.

**Where the three reviews converge.** All three now agree on the same verdict: a careful, honest negative result whose open questions are disclosed rather than hidden. My 7.5 sits slightly below an 8 because the two experiments that would make the encoding and split-variance conclusions firm were declined. If the venue requires an integer, I score 7, leaning accept.
