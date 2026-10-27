# Review B: novelty, positioning and significance

**Paper:** "What Do Spikes Buy in Flow-Based Intrusion Detection? A Leakage-Controlled Study of an Ensemble Spiking Network on CSE-CIC-IDS2018"
**Reviewer focus:** novelty, accuracy of prior-work claims, overclaiming, narrative coherence, title/abstract, venue fit.

**Overall score: 5 / 10** (borderline; weak reject at a selective IEEE security venue, weak accept at a mid-tier IEEE conference or workshop)
**Confidence: 4 / 5** (I know the SNN-IDS and NIDS-evaluation literature well; I did not rerun code.)

---

## Summary

The paper evaluates a three-branch ensemble SNN (rate, latency and population coding, 86k parameters) for 13-class flow classification on CSE-CIC-IDS2018. Rows with identical cleaned feature vectors are kept in one partition. There are separate partitions for fitting, probability calibration, alarm-threshold calibration and test, and every model is compared at fixed benign false-alarm budgets (1/5/10%). The baselines are a parameter-matched MLP, a "spike-input control" (Enc-ANN: the same encoders feeding a non-spiking network) and three untuned tree ensembles.

The main findings are mostly negative or mixed:
- E-SNN macro-F1 is 0.769 ± 0.022. It sits above the matched MLP (0.756) and below Enc-ANN (0.787), RF, CatBoost and XGBoost (0.808).
- Attack detection rates differ by less than one point across models.
- The weakest classes are explained by label-conflicting duplicate vectors.
- T = 4 matches T = 12 at 2.9× fewer synaptic events.
- The energy advantage flips sign between a 45 nm adder model and Loihi per-op costs.
- Frozen models transfer poorly to CIC-IDS2017, and about 1.1k local labels restore detection.

The paper is unusually honest. It discloses post-hoc design, reports every screened variant, gives the achieved FPR next to every number and labels energy as an estimate. The spike-input control is the most interesting methodological idea in the paper, and SNN-IDS work should adopt it. My concerns are about **how much is new** (several "findings" replicate known results from the NIDS-evaluation literature that the paper does not cite), **whether the central claim is statistically supported**, and **framing**: the title and abstract foreground a model that the paper itself shows is not the right answer.

---

## Major issues

### M1. The cross-dataset transfer finding is presented as new, but it is well established for exactly this dataset pair
**Location:** Sec. V-F last paragraph ("We see this as the most practically relevant finding of the study … Claims of generalisation should be backed by a cross-dataset test"); abstract; Related Work (no cross-dataset NIDS papers cited).

**Why:** Several works already show that supervised flow-feature models trained on one CIC dataset fail on the other, without retraining. D'hooge et al. (Sensors 2023) trained on CSE-CIC-IDS2018 attack classes and tested on CIC-IDS2017, CIC-DoS2017 and CIC-DDoS2019, which is the same direction as this paper. They concluded that the models rarely learn a generally applicable representation. D'hooge et al. (JCP 2023) did the reverse direction. Cantone et al. (IEEE Access 2024) ran a systematic cross-dataset study over CIC-IDS2017, CSE-CIC-IDS2018 and their corrected LycoS versions. Apruzzese et al. (EuroS&P 2023) make the same pragmatic-assessment argument. Calling this "the most practically relevant finding" without citing these works overclaims, and reviewers from the NIDS community will notice.

**Fix:**
- Cite these works in Related Work, under a "Cross-dataset generalisation" heading.
- Reframe Sec. V-F as *confirming* known transfer failure **for SNNs and under recalibrated thresholds**. The genuinely new parts are the SNN-specific per-class pattern (slow DoS transfers, Bot does not) and the few-label fine-tuning curve versus XGBoost.
- Drop "most practically relevant finding".

### M2. The headline mechanism claim ("the encoders, not the spiking dynamics, carry the benefit") is not statistically supported with n = 3
**Location:** abstract ("our reading is that the input encoders, not the spiking dynamics, carry most of the benefit"); Sec. V-A ("suggests the spike encoders help"); Discussion "What the spikes buy"; Conclusion.

**Why:** The key differences are small relative to the seed spread:
- E-SNN vs. matched MLP: +1.3 points, with E-SNN s.d. 0.022.
- E-SNN vs. Enc-ANN: −1.8 points, with Enc-ANN s.d. 0.017. At T = 4 the gap is 2.1 points, with s.d. 0.022 and 0.015.

With three seeds, no confidence intervals and no test, none of these orderings is established. The paper itself says that variants "within the seed spread" are indistinguishable (Sec. V-C) but does not apply that standard to its own headline. Everything is also measured on one test partition, which the Limitations say has been used repeatedly.

**Fix:**
- Report paired differences per seed, with a bootstrap CI over test flows or over the 13 per-class F1s, or raise to ≥5 seeds.
- Soften the claims to match. For example: "we find no evidence that membrane dynamics add accuracy over the same encoding fed to a non-spiking network; the encoding accounts for the MLP→E-SNN gain within seed noise."
- Add a "matched MLP + simple binning/one-hot encoding" control (see M3). That would turn the claim from a reading into a test.

### M3. The spike-input control result is not connected to the tabular-DL literature on numerical-feature encodings
**Location:** Sec. IV (Enc-ANN), Discussion.

**Why:** Deterministic rate, latency and population codes of a scalar are, in effect, fixed binning, thermometer or RBF encodings of numerical features. Gorishniy et al. (NeurIPS 2022) showed that piecewise-linear and periodic embeddings of numerical features substantially improve plain MLPs on tabular data. So "Enc-ANN beats the MLP" is largely an instance of a known effect, and "spikes help because of the encoder" may reduce to "binning helps MLPs". This does not remove the value of the control for the SNN community, but it changes what can be claimed as an insight.

**Fix:**
- Cite Gorishniy et al. and Shwartz-Ziv & Armon (2022) alongside Grinsztajn et al.
- Add one cheap baseline: the MLP with piecewise-linear or quantile-bin one-hot encoding, without spike framing.
- If it matches Enc-ANN, say so plainly. That is a stronger and more useful negative result.

### M4. The feature-group audit and its "error floor" partly replicate known dataset errors and contain a logical slip
**Location:** contribution 3; Sec. V-D ("Any reported error below that floor on this representation is a sign of leakage").

**Why, first (novelty):** Liu et al. (CNS 2022) analysed error prevalence in CSE-CIC-IDS2018. The paper cites them only for Infiltration, not for the FTP-BruteForce / DoS-SlowHTTPTest problem. Please check whether Liu et al. already document that these two classes consist largely of failed or degenerate connections, and credit them if so. Flood et al. (EuroS&P 2024, "Bad Design Smells in Benchmark NIDS Datasets") also catalogue structural problems in these benchmarks and should be cited. The audit is useful, but the contribution should be phrased as quantifying, at feature-vector level, the conflicts that make these classes inseparable. It should not read as a discovery.

**Why, second (logic):** A group of identical vectors with conflicting labels cannot be classified better than its majority label *regardless* of leakage, because memorisation cannot separate identical inputs. An error below 1.10% therefore signals a different label mapping, different cleaning, subsampling or de-duplication. It does not signal leakage.

**Fix:** Rewrite the sentence along these lines: "an error below this floor implies a different label set or preprocessing (e.g., de-duplication or class removal), and such results are not comparable." Also state which "cleaned" representation the floor refers to, before or after column removal.

### M5. Avoidably incomplete CIC-IDS2017 export weakens the transfer and adaptation experiments
**Location:** Sec. V-F ("The export we used lacks two of the original files (Tuesday … and Thursday morning …)").

**Why:** 2,214,468 flows is exactly the full MachineLearningCVE total (2,830,743) minus the Tuesday (445,909) and Thursday-morning (170,366) files. The official export contains both, so this is an incomplete copy, not a property of the export. The missing days hold FTP-Patator, SSH-Patator and the web attacks. Those are exactly the classes that would test whether the "label conflict" classes, brute force and web attacks, transfer. The text also implies the export itself lacks them, which may mislead readers.

**Fix:**
- Use the full official export, or better, the corrected CIC-IDS2017 of Engelen et al. (2021) or Lanvin et al. (CRiSIS 2022), and rerun Table VII/VIII.
- If that is impossible, state that the missing files are specific to the copy used.

### M6. "Fixed by ~1,100 local labels" is overstated, and it is not an SNN result
**Location:** abstract ("About 1,100 labelled local flows are enough to bring both the SNN and XGBoost back above 98% detection"); Sec. V-F.

**Why:**
- The adaptation pool and the test set come from the same capture days, split by fingerprint. That is closer to an in-distribution re-split than to deployment, and the paper admits it is "an optimistic bound".
- ADR is dominated by high-volume DoS, DDoS and PortScan flows, while macro-F1 stays at 0.53–0.56 and Bot is missed entirely by the SNN.
- XGBoost *from scratch* on the same 1,101 flows does as well or better. The finding is therefore "this dataset is easy once you have any in-domain labels". It says nothing about SNN fine-tuning.

**Fix:**
- In the abstract, say "on a same-capture re-split" and report macro-F1 or per-class recall next to ADR.
- Use a day-disjoint adaptation/test split for at least one configuration.
- Make the point that tree models need no pre-training at all.

### M7. Title, abstract and contributions foreground the model the paper argues against, and the abstract is far too long
**Location:** title, abstract (≈410 words), Sec. I contributions.

**Why:**
- The real contributions are an evaluation protocol, two controls (spike-input and trees), an energy cost-model sensitivity analysis and a transfer test. The E-SNN is the object of study, not the contribution. "Ensemble Spiking Network" in the subtitle invites reviewers to judge it as a model paper, and it loses that contest.
- The abstract tries to report every experiment. IEEE conference templates typically ask for 150–250 words. At this length the key message (encoder vs. dynamics, cost-model dependence) is buried.

**Fix:**
- Retitle along the lines of "Do Spiking Networks Help Flow-Based Intrusion Detection? Spike-Input Controls, Tree Baselines and Hardware Cost Models on CSE-CIC-IDS2018".
- Cut the abstract to about 220 words, with this structure: problem (SNN-IDS evaluations lack leakage control, tree baselines and cost models) → protocol in one sentence → the three findings (trees > Enc-ANN ≥ SNN; T = 4 suffices, but under Loihi per-op costs the SNN costs more than the MLP; no transfer without local labels) → release.
- Drop the architecture screen and Docker details from the abstract.

### M8. The energy section is credible but not positioned against the SNN-vs-ANN energy literature
**Location:** Sec. V-E, Discussion "Energy needs a hardware model".

**Why:** The recommendation that energy claims should state their cost model and report both is a known conclusion. Dampfhoffer et al. (IEEE TETCI 2023) showed with a hardware-aware model, including memory accesses, that SNNs beat efficient ANN implementations only at very high spike sparsity. Davies et al. (Proc. IEEE 2021) is the more appropriate Loihi survey for per-op and system-level figures. Without these works, the section reads as rediscovering the point.

Two further gaps:
- Enc-ANN is never costed under the Loihi or SRAM model. The abstract nonetheless says Enc-ANN is "cheaper at every window length", which is only shown under the 45 nm arithmetic-only model.
- Loihi per-op energies are charged for synaptic events that originate from the *input encoding*. On Loihi, those input spikes would be injected from the host or an embedded core, with a different cost.

**Fix:**
- Cite Dampfhoffer et al. and Davies et al. 2021, and present the result as an IDS-specific instance of their sparsity threshold. For example, report spikes per synapse per inference and compare it to their 0.15–1.38 range. That would be a nice, quantitative positioning.
- Cost Enc-ANN under the same SRAM-inclusive model, or qualify the abstract sentence.

---

## Minor issues

1. **Related Work, "What we add is a combination."** This is fair and well hedged. Make it explicit that Patel et al. (2026) already show encoding matters more than neuron model, which your Enc-ANN result extends to "encoding matters more than spiking at all". That is a cleaner novelty statement and credits them properly.
2. **"Tree ensembles … untuned, which if anything favours the neural models"** (Sec. IV). The neural models were early-stopped on tuning macro-F1, and the E-SNN had a five-variant screen. Say that the neural side received more tuning effort; that strengthens your point.
3. **Sec. V-A:** "Attack detection rates differ by less than one point." The range is 0.958–0.967 = 0.9 points, so this is correct but borderline. Say "within 0.9 points".
4. **Table III:** Enc-ANN AC counts *decrease* slightly with T (30,272 → 28,956), although the flattened input grows with T. Presumably the first-layer width shrinks to match parameters. Explain this in one clause, or readers will suspect an error.
5. **Sec. V-C:** "confirms that training on Kaggle is deterministic for a fixed seed". One reproduced run does not confirm determinism; say "was reproducible in this instance".
6. **Discussion:** "This does not rule out SNN advantages … on temporal inputs such as packet sequences." Good. Consider naming this as the obvious next experiment (e.g., per-packet SNN on raw PCAP, where time steps are real time), so the negative result has a constructive direction.
7. **Contribution 4** lists "every test result disclosed". Also give the number of test-set evaluations made in total over the v1–v3 history, if known. That makes the multiple-testing caveat concrete.
8. **Wang et al. 2024** is the only prior SNN result on CSE-CIC-IDS2018 (98.82% accuracy, 6 classes). One sentence contrasting their accuracy with your macro-F1 under a group split would illustrate the problem the protocol addresses.
9. **Karthik et al. 2026:** the survey notes that several of their tables are labelled "simulated". The paper describes them neutrally, which is appropriate. Do not add criticism there without quoting.
10. **Calibration framing:** the Neyman–Pearson citation is apt. Note that the empirical-quantile threshold has no finite-sample FPR guarantee, unlike the NP umbrella algorithm of Tong et al. The achieved FPR is fine here, but say so in one clause.
11. **Containerised detector** (Sec. VI) is not a research contribution at an IEEE conference. Move it to the Reproducibility paragraph and drop it from the contributions list.

---

## Missing references (verified)

All checked via Crossref or the publisher/arXiv page.

| Reference | Why it matters | Identifier |
|---|---|---|
| L. D'hooge, M. Verkerken, T. Wauters, F. De Turck, B. Volckaert, "Investigating Generalized Performance of Data-Constrained Supervised Machine Learning Models on Novel, Related Samples in Intrusion Detection," *Sensors* 23(4):1846, 2023 | Trains on CSE-CIC-IDS2018 and tests on CIC-IDS2017 / DoS2017 / DDoS2019; same transfer direction as Sec. V-F (M1) | doi:10.3390/s23041846 |
| L. D'hooge, M. Verkerken, T. Wauters, F. De Turck, B. Volckaert, "Characterizing the Impact of Data-Damaged Models on Generalization Strength in Intrusion Detection," *J. Cybersecurity and Privacy* 3(2):118–144, 2023 | CIC-IDS2017 → CSE-CIC-IDS2018 without retraining (M1) | doi:10.3390/jcp3020008 |
| M. Cantone, C. Marrocco, A. Bria, "Machine Learning in Network Intrusion Detection: A Cross-Dataset Generalization Study," *IEEE Access* 12, 2024 | Systematic cross-dataset study over CIC-IDS2017/2018 and corrected LycoS versions (M1, M5) | doi:10.1109/ACCESS.2024.3472907; arXiv:2402.10974 |
| G. Apruzzese, P. Laskov, J. Schneider, "SoK: Pragmatic Assessment of Machine Learning for Network Intrusion Detection," IEEE EuroS&P 2023, pp. 592–614 | Evaluation-methodology framing, including multiple hardware platforms (M1, M8) | doi:10.1109/EuroSP57164.2023.00042; arXiv:2305.00550 |
| R. Flood, G. Engelen, D. Aspinall, L. Desmet, "Bad Design Smells in Benchmark NIDS Datasets," IEEE EuroS&P 2024, pp. 658–675 | Structural dataset flaws behind the audit (M4) | doi:10.1109/EuroSP60621.2024.00042 |
| M. Lanvin, P.-F. Gimenez, Y. Han, F. Majorczyk, L. Mé, E. Totel, "Errors in the CICIDS2017 Dataset and the Significant Differences in Detection Performances It Makes," CRiSIS 2022, LNCS 13857 | Corrected CIC-IDS2017 for the transfer target (M5) | doi:10.1007/978-3-031-31108-6_2 |
| M. Dampfhoffer, T. Mesquida, A. Valentian, L. Anghel, "Are SNNs Really More Energy-Efficient Than ANNs? An In-Depth Hardware-Aware Study," *IEEE TETCI* 7(3), 2023 | Hardware-aware SNN-vs-ANN energy with memory access, and a sparsity threshold (M8) | doi:10.1109/TETCI.2022.3214509 |
| M. Davies et al., "Advancing Neuromorphic Computing With Loihi: A Survey of Results and Outlook," *Proc. IEEE* 109(5), 2021 | System-level Loihi energy figures to complement Davies 2018 (M8) | doi:10.1109/JPROC.2021.3067593 |
| Y. Gorishniy, I. Rubachev, A. Babenko, "On Embeddings for Numerical Features in Tabular Deep Learning," NeurIPS 2022 | Piecewise-linear and periodic encodings improve MLPs; explains the Enc-ANN effect (M3) | arXiv:2203.05556 |
| R. Shwartz-Ziv, A. Armon, "Tabular Data: Deep Learning Is Not All You Need," *Information Fusion* 81, 2022 | Second source for "trees win on tabular data" | doi:10.1016/j.inffus.2021.11.011 |
| M. Sarhan, S. Layeghy, M. Portmann, "Towards a Standard Feature Set for Network Intrusion Detection System Datasets," *Mobile Netw. Appl.* 27, 2022 | Shared NetFlow feature set and cross-dataset evaluation; relevant to the protocol-field imputation and feature-mismatch issue | doi:10.1007/s11036-021-01843-0 |

(Lemaire et al. 2022 on analytical SNN energy estimation would also fit M8, but I did not verify its bibliographic details, so it is not listed.)

---

## Venue fit and framing

In its current form this is a careful negative-result and evaluation study, with modest novelty and no hardware measurement. Realistic targets:

1. **IEEE CNS (Conference on Communications and Network Security)** or its workshops. CNS is where Liu et al. 2022 appeared, and the audience values dataset-quality and evaluation rigour. For CNS, frame the paper as "evaluation pitfalls for neuromorphic NIDS" and lead with the protocol, the controls and transfer.
2. **IJCNN (IEEE/INNS)**, in an SNN or applications track. The audience understands surrogate-gradient SNNs, encoders and energy accounting. The spike-input control and the cost-model sensitivity are of direct interest there. Lead with "encoding vs. dynamics" and add the M3 binning baseline.
3. **ACM ICONS (Int. Conf. on Neuromorphic Systems)**, if not restricted to IEEE. It is a natural home for "when do SNNs not pay off on neuromorphic cost models", especially with the Dampfhoffer-style sparsity analysis (M8). For a journal extension, *IEEE Transactions on Network and Service Management* fits the transfer and deployment angle.

Selective security venues (IEEE S&P, EuroS&P main track) would need hardware measurement or a temporal/packet-level SNN to clear the novelty bar.

---

## What would raise the score to 8+

1. **Make the mechanism claim a tested result.** Use ≥5 seeds with paired CIs, and add an MLP with plain binning or piecewise-linear encoding (M2, M3). If spikes add nothing over binning, say so as the headline.
2. **Reposition honestly against the NIDS-evaluation literature** (D'hooge 2023 ×2, Cantone 2024, Apruzzese 2023, Flood 2024, Liu 2022 for FTP/SlowHTTPTest). State that the novelty is bringing these controls to SNN-IDS and adding the spike-input control (M1, M4).
3. **Fix the transfer experiment.** Use the full or corrected CIC-IDS2017 and a day-disjoint adaptation split, and report per-class recall and macro-F1 next to ADR (M5, M6).
4. **Strengthen the energy argument.** Position it against Dampfhoffer et al., report spikes per synapse per inference against their threshold, and cost Enc-ANN under the same SRAM-inclusive model. Ideally add one measured number, for example Lava/Loihi 2 via INRC or even a measured CPU/GPU energy (M8).
5. **Reframe the title and a ≤250-word abstract** around the question and the three findings, not the E-SNN (M7).
6. Optionally, add a **temporal-input experiment** (packet-sequence SNN on the same captures), where SNN dynamics have something to integrate. This is the experiment that would turn "what do spikes buy" from a negative into a two-sided answer.
