# Energy per flow under one set of cost models (45 nm and Loihi)

Script: `scripts/analysis/energy_unified.py` (reuses `count`, `esnn_energy`, `dense_energy` and the checkpoints of `scripts/energy_loihi.py`).
Outputs: `results/analysis/energy_unified.json`, `results/analysis/energy_unified_table.md`. Estimates from operation counts, not measurements. Runtime about 15 s on CPU.

## Op-count sample

- `demo`: `app/samples/demo_flows.csv` = 1,600 benign + 7 x 400 attack flows (not class balanced; 36% benign). Reproduces `results/v4/energy_loihi.json` and the paper's counts exactly (339,801 / 227,501 / 116,864 synaptic events).
- `test_mix` (recommended): flows sampled from the four raw 2018 days that are on disk (6,000 benign, 1,500 per measured attack class), per-class counts weighted by the test-partition support. The eight measured classes cover 92.2% of test rows; benign weight 90.9%. Not measured: LOIC-HTTP, Hulk, SlowHTTPTest, Infiltration, Web.
- Benign flows produce slightly more synaptic events than the attack average (E-SNN T = 12: 349,607 vs 339,801 on demo), so the benign-heavy mix raises E-SNN counts by 2.3% and changes no conclusion.

## Cost models (pJ, Horowitz 2014; Davies et al. 2018)

- 45 nm optimistic: AC 0.9, MAC 4.6. This is the old Table VI model.
- 45 nm complete: + LayerNorm (4 MAC-eq per element, every model that has it) + one FP32 MAC per LIF membrane update (decay and integrate) + one MAC per readout-integrator update. Threshold compare and reset not charged.
- + SRAM: one 32 KB SRAM weight read (10 pJ per FP32 weight) per AC and MAC.
- INT8: int8 add for ACs (0.03), int8 MAC (0.23) for everything else. Like-for-like with Loihi's at most 9-bit weights.
- Loihi: synaptic events 23.6, neuron updates 81, spike routing 1.7; LayerNorm and fusion on a 45 nm FP32 host.

## Unified table (test_mix sample, energy per flow in µJ)

| Model | ACs | MACs | 45 nm optimistic | 45 nm complete | 45 nm complete + SRAM | INT8 | Loihi |
|---|---|---|---|---|---|---|---|
| E-SNN, T = 4 | 120,028 | 3,367 | 0.124 | 0.177 | 1.41 | 0.0071 | 3.09 |
| E-SNN, T = 8 | 233,577 | 3,367 | 0.226 | 0.333 | 2.70 | 0.0132 | 6.02 |
| E-SNN, T = 12 | 347,762 | 3,367 | 0.328 | 0.490 | 4.00 | 0.0193 | 8.95 |
| Enc-ANN, T = 4 | 31,349 | 12,352 | 0.085 | 0.090 | 0.53 | 0.0040 | -- |
| Enc-ANN, T = 8 | 31,034 | 6,568 | 0.058 | 0.061 | 0.44 | 0.0026 | -- |
| Enc-ANN, T = 12 | 30,153 | 5,094 | 0.051 | 0.053 | 0.41 | 0.0022 | -- |
| Matched ANN | 0 | 84,420 | 0.388 | **0.398** | 1.24 | 0.0199 | -- |

E-SNN complete = optimistic + LayerNorm (0.042 / 0.085 / 0.127 µJ at T = 4 / 8 / 12) + membrane and readout updates (0.011 / 0.023 / 0.034 µJ).
Demo-sample values differ by at most 2.3% (E-SNN complete 0.174 / 0.328 / 0.482; Loihi 3.02 / 5.87 / 8.77; Enc-ANN + SRAM 0.39 to 0.52).

Ratios to the matched ANN under the same model (E-SNN / ANN):

| | optimistic | complete | complete + SRAM | INT8 |
|---|---|---|---|---|
| E-SNN, T = 4 | 0.32 | 0.45 | 1.14 | 0.36 |
| E-SNN, T = 8 | 0.58 | 0.84 | 2.18 | 0.66 |
| E-SNN, T = 12 | 0.85 | 1.23 | 3.22 | 0.97 |
| Enc-ANN, T = 12 | 0.13 | 0.13 | 0.33 | 0.11 |

E-SNN on Loihi vs ANN: 7.8x / 15.1x / 22.5x the FP32 ANN (0.398 µJ), 2.5x / 4.8x / 7.2x the FP32 ANN with SRAM reads (1.24 µJ), and 155x / 302x / 449x the INT8 ANN (0.020 µJ).

## Table for the paper (one ANN figure, 0.40 µJ)

```latex
\begin{tabular}{lrrrr}
\toprule
Model & 45\,nm & 45\,nm + SRAM & INT8 & Loihi \\
\midrule
E-SNN, $T = 4$  & 0.18 & 1.41 & 0.007 & 3.1 \\
E-SNN, $T = 8$  & 0.33 & 2.70 & 0.013 & 6.0 \\
E-SNN, $T = 12$ & 0.49 & 4.00 & 0.019 & 9.0 \\
Enc-ANN, $T = 4$  & 0.09 & 0.53 & 0.004 & -- \\
Enc-ANN, $T = 12$ & 0.05 & 0.41 & 0.002 & -- \\
Matched ANN & 0.40 & 1.24 & 0.020 & -- \\
\bottomrule
\end{tabular}
```
(µJ per flow; 45 nm includes LayerNorm for all models and membrane updates for the E-SNN; INT8 uses 8-bit adds and MACs.)

## Sentences for the paper

- Once the E-SNN's per-step layer normalisation and membrane updates are charged at the same 45\,nm prices as the perceptron's own layer normalisation, the estimate is 0.18, 0.33 and 0.49\,$\mu$J per flow at $T = 4$, 8 and 12, against 0.40\,$\mu$J for the matched ANN: 55\% less at $T = 4$, 16\% less at $T = 8$ and 23\% more at $T = 12$.
- Layer normalisation alone costs the E-SNN 0.13\,$\mu$J per flow at $T = 12$, a third of the perceptron's total.
- If each weight is also read from a 32\,KB SRAM, every E-SNN window is more expensive than the ANN (1.4 to 4.0 against 1.2\,$\mu$J), while Enc-ANN stays cheaper (0.41 to 0.53\,$\mu$J).
- With 8-bit arithmetic, the like-for-like point for Loihi's low-precision weights, the matched ANN needs 0.020\,$\mu$J per flow, about 150 times less than the 4-step E-SNN on Loihi (3.1\,$\mu$J).
- Operation counts are taken on a benign-heavy sample weighted to the test-partition class mix (91\% benign over the measured classes); they differ from the earlier 4{,}400-flow sample by less than 3\%.

## Consequences for the paper

- Abstract "69% less synaptic energy": with the optimistic model on the test-mix sample it is 68%; with the complete model it is 55%. Replace with the complete figure or drop.
- Sec. V-E "the estimate ends about 17% below the ANN" at T = 12: with LayerNorm and membrane updates it is 23% above. The sign flips.
- One ANN number: 0.40 µJ (with its LayerNorm) everywhere; 0.39 µJ was linear layers only.
- "class-balanced" op-count sample: it is not; use the test-mix sample.
- Add Enc-ANN rows (0.41 to 0.53 µJ with SRAM) and the INT8 ANN row (0.020 µJ).
