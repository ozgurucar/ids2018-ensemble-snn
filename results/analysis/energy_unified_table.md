# Unified per-flow energy

Script `scripts/analysis/energy_unified.py`; JSON `results/analysis/energy_unified.json`. Estimates, not measurements.

## Sample: test_mix

Measured classes Benign, Bot, DDoS-HOIC, DDoS-LOIC-UDP, DoS-GoldenEye, DoS-Slowloris, FTP-BruteForce, SSH-Bruteforce; they cover 92.2% of test rows; benign weight 90.9%. Missing: DDoS-LOIC-HTTP, DoS-Hulk, DoS-SlowHTTPTest, Infiltration, Web Attacks.

| Model | ACs | MACs | LN el. | Membrane+readout upd. | 45 nm optimistic | 45 nm complete | 45 nm complete + SRAM | INT8 | Loihi |
|---|---|---|---|---|---|---|---|---|---|
| E-SNN, T = 4 | 120,028 | 3,367 | 2,304 | 2,460 | 0.124 | 0.177 | 1.411 | 0.0071 | 3.09 |
| E-SNN, T = 8 | 233,577 | 3,367 | 4,608 | 4,920 | 0.226 | 0.333 | 2.703 | 0.0132 | 6.02 |
| E-SNN, T = 12 | 347,762 | 3,367 | 6,912 | 7,380 | 0.328 | 0.490 | 4.001 | 0.0193 | 8.95 |
| Enc-ANN, T = 4 | 31,349 | 12,352 | 290 | 0 | 0.085 | 0.090 | 0.527 | 0.0040 | -- |
| Enc-ANN, T = 8 | 31,034 | 6,568 | 160 | 0 | 0.058 | 0.061 | 0.437 | 0.0026 | -- |
| Enc-ANN, T = 12 | 30,153 | 5,094 | 110 | 0 | 0.051 | 0.053 | 0.405 | 0.0022 | -- |
| Matched ANN | 0 | 84,420 | 504 | 0 | 0.388 | 0.398 | 1.242 | 0.0199 | -- |

Ratios to the matched ANN under the same cost model (E-SNN / ANN):

- E-SNN, T = 4: optimistic 0.32, complete 0.45, complete+SRAM 1.14, INT8 0.36, Loihi vs ANN 45 nm complete 7.8x
- E-SNN, T = 8: optimistic 0.58, complete 0.84, complete+SRAM 2.18, INT8 0.66, Loihi vs ANN 45 nm complete 15.1x
- E-SNN, T = 12: optimistic 0.85, complete 1.23, complete+SRAM 3.22, INT8 0.97, Loihi vs ANN 45 nm complete 22.5x
- Enc-ANN, T = 4: optimistic 0.22, complete 0.23, complete+SRAM 0.42, INT8 0.20
- Enc-ANN, T = 12: optimistic 0.13, complete 0.13, complete+SRAM 0.33, INT8 0.11

## Sample: demo

| Model | ACs | MACs | LN el. | Membrane+readout upd. | 45 nm optimistic | 45 nm complete | 45 nm complete + SRAM | INT8 | Loihi |
|---|---|---|---|---|---|---|---|---|---|
| E-SNN, T = 4 | 116,864 | 3,367 | 2,304 | 2,460 | 0.121 | 0.174 | 1.377 | 0.0070 | 3.02 |
| E-SNN, T = 8 | 227,501 | 3,367 | 4,608 | 4,920 | 0.220 | 0.328 | 2.636 | 0.0130 | 5.87 |
| E-SNN, T = 12 | 339,801 | 3,367 | 6,912 | 7,380 | 0.321 | 0.482 | 3.914 | 0.0190 | 8.77 |
| Enc-ANN, T = 4 | 30,272 | 12,352 | 290 | 0 | 0.084 | 0.089 | 0.516 | 0.0040 | -- |
| Enc-ANN, T = 8 | 29,881 | 6,568 | 160 | 0 | 0.057 | 0.060 | 0.425 | 0.0026 | -- |
| Enc-ANN, T = 12 | 28,956 | 5,094 | 110 | 0 | 0.049 | 0.052 | 0.392 | 0.0021 | -- |
| Matched ANN | 0 | 84,420 | 504 | 0 | 0.388 | 0.398 | 1.242 | 0.0199 | -- |

Ratios to the matched ANN under the same cost model (E-SNN / ANN):

- E-SNN, T = 4: optimistic 0.31, complete 0.44, complete+SRAM 1.11, INT8 0.35, Loihi vs ANN 45 nm complete 7.6x
- E-SNN, T = 8: optimistic 0.57, complete 0.82, complete+SRAM 2.12, INT8 0.65, Loihi vs ANN 45 nm complete 14.8x
- E-SNN, T = 12: optimistic 0.83, complete 1.21, complete+SRAM 3.15, INT8 0.96, Loihi vs ANN 45 nm complete 22.0x
- Enc-ANN, T = 4: optimistic 0.22, complete 0.22, complete+SRAM 0.42, INT8 0.20
- Enc-ANN, T = 12: optimistic 0.13, complete 0.13, complete+SRAM 0.32, INT8 0.11

## Per-class synaptic events per flow (E-SNN T = 12, test_mix sample)

| Class | ACs | hidden sparsity |
|---|---|---|
| Benign | 349,607 | 0.721 |
| Bot | 337,056 | 0.731 |
| DDoS-HOIC | 321,015 | 0.738 |
| DDoS-LOIC-UDP | 333,758 | 0.709 |
| DoS-GoldenEye | 353,763 | 0.716 |
| DoS-Slowloris | 349,976 | 0.716 |
| FTP-BruteForce | 307,284 | 0.716 |
| SSH-Bruteforce | 338,781 | 0.723 |
