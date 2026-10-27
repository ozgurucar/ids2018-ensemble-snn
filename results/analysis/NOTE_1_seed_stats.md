# Item 1: seed-level statistics

Script: `scripts/analysis/seed_stats.py` (reads only `summary.json` records).
Outputs: `results/analysis/seed_stats.json`, `results/analysis/seed_stats_table.md`.
Rerun with the 5-seed v5 records (seeds are merged by number; identical reruns are skipped, conflicts are listed):

    ~/.cache/ids-run-venv/bin/python scripts/analysis/seed_stats.py --summary T12=results/v5/<run>/summary.json

Pre-declared family: E-SNN vs matched ANN, E-SNN vs Enc-ANN, E-SNN vs XGBoost (all T = 12), at tau = 5% (primary) and 1%.
Holm is applied within each (metric, tau) family of three, and also across both budgets (six tests) per metric; both are in the JSON.
Pairing is by seed number. Seeds vary initialisation and data order only; the split seed is fixed, so no interval below covers partition variance.

## Key numbers (13-class macro-F1, differences in points)

| Comparison | tau | Mean diff | Welch 95% CI | p Welch (Holm, 3) | per-seed paired diffs | paired p (Holm, 3) |
|---|---|---|---|---|---|---|
| E-SNN minus matched ANN | 5% | +1.3 | [-3.9, +6.6] | 0.40 (0.66) | -1.3, +2.7, +2.6 | 0.41 (0.41) |
| E-SNN minus Enc-ANN | 5% | -1.8 | [-6.3, +2.8] | 0.33 (0.66) | -2.3, -1.0, -2.0 | 0.051 (0.15) |
| E-SNN minus XGBoost | 5% | -3.9 | [-9.0, +1.2] | 0.083 (0.25) | -6.9, -1.6, -3.2 | 0.13 (0.26) |
| E-SNN minus matched ANN | 1% | +1.8 | [-1.2, +4.7] | 0.15 (0.15) | +0.2, +2.3, +2.8 | 0.15 (0.15) |
| E-SNN minus Enc-ANN | 1% | -2.7 | [-5.7, +0.4] | 0.071 (0.14) | -2.9, -1.5, -3.6 | 0.047 (0.097) |
| E-SNN minus XGBoost | 1% | -5.9 | [-8.9, -2.8] | 0.012 (0.035) | -7.9, -4.2, -5.5 | 0.032 (0.097) |

11-class macro-F1 (without FTP-BruteForce and DoS-SlowHTTPTest): at 5% nothing is significant (Welch Holm 0.58 for all three). At 1% the paired tests give Holm-adjusted p = 0.031 for all three comparisons (E-SNN above the ANN by 2.1 points, below Enc-ANN by 2.2 and below XGBoost by 4.4), and Welch gives Holm 0.088, 0.088 and 0.049. Across both budgets (Holm over six), no 11-class comparison stays below 0.05 (smallest 0.061, paired, E-SNN vs Enc-ANN).

Power: with three seeds the smallest difference a Welch test detects with 80% power at the 5% budget is 6.1 to 6.6 points (13-class); the observed gaps are 1.3 to 3.9 points.

Time window (Welch TOST, margin 2 points): no pair is shown equivalent. E-SNN T = 4 minus T = 12 at 5%: -0.3 points, 90% CI [-3.7, +3.1], TOST p = 0.17. T = 8 minus T = 12: -0.3, [-3.7, +3.0], p = 0.17.

Exploratory (unadjusted): Enc-ANN minus RF at 5% is -0.1 points (p = 0.93, 13-class) and +0.6 (p = 0.58, 11-class). XGBoost is above RF and CatBoost (p = 0.018 and 0.015, 13-class), the only tree gaps that the seeds resolve.

## LaTeX-ready sentences

- With three seeds, none of the three pre-declared comparisons at the 5\% budget is significant after Holm correction: the E-SNN differs from the matched ANN by $+1.3$ points (95\% CI $[-3.9, 6.6]$, Welch $p = 0.40$), from Enc-ANN by $-1.8$ points ($[-6.3, 2.8]$, $p = 0.33$) and from XGBoost by $-3.9$ points ($[-9.0, 1.2]$, $p = 0.08$; Holm-adjusted $0.66$, $0.66$ and $0.25$).
- Enc-ANN scored higher than the E-SNN on all three seeds, by 1.0 to 2.3 points (paired $p = 0.051$, Holm $0.15$), so the direction is consistent but the evidence is weak.
- At the 1\% budget the E-SNN is 5.9 points below XGBoost (95\% CI $[-8.9, -2.8]$, Welch $p = 0.012$, Holm-adjusted $0.035$ within that budget, $0.069$ across both budgets).
- With three seeds a two-sided test has 80\% power only for differences of about 6 points, so the absence of significance at the 5\% budget is not evidence of equality.
- For the time window we can only say that we found no detectable difference: the 90\% CI of the $T{=}4$ minus $T{=}12$ difference is $[-3.7, 3.1]$ points, which does not exclude a 2-point effect.

## What changes in the paper

- "above the matched perceptron", "beats a parameter-matched perceptron" (abstract, conclusion) and "below the spike-input control" are not supported as stated; use "no detectable difference at n = 3" with the CIs above.
- "The three are indistinguishable given the seed spread" (Sec. V-B) should become "no detectable difference"; equivalence within 2 points is not shown.
- The only E-SNN gap that survives Holm is E-SNN below XGBoost at tau = 1% (within-budget family).
