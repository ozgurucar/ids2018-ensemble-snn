# Transfer hygiene

Script `scripts/analysis/transfer_hygiene.py`; JSON `results/analysis/transfer_hygiene.json`.

- Name-mapped and positional feature frames identical: **True** (2,214,468 rows x 78 columns).
- 2017 duplicate 'Fwd Header Length' columns identical: True (rows differing: 0).

| Model | FAR (2018 thr.) | DR | Recal. FAR | Recal. DR | max abs diff vs cic2017.json |
|---|---|---|---|---|---|
| esnn | 0.2621 | 0.6300 | 0.0497 | 0.2304 | 0.00e+00 |
| esnn_t4 | 0.2276 | 0.4196 | 0.0499 | 0.2392 | 0.00e+00 |
| xgb | 0.2523 | 0.4935 | 0.0503 | 0.3171 | 0.00e+00 |

## KS shift, 2018 benign (800,000 rows from 02-14-2018, 02-15-2018, 02-21-2018, 03-02-2018) vs 2017 benign (1,672,837 rows)

Median KS over the 70 model inputs: 0.245; 15 features above 0.3; 7 features shift more than the largest shift between any two 2018 days (median of that day-to-day maximum: 0.625).

| Rank | Feature | KS 2018 vs 2017 | max KS between 2018 days | median 2018 | median 2017 | zero share 2018 | zero share 2017 |
|---|---|---|---|---|---|---|---|
| 1 | Fwd Seg Size Min | 0.485 | 0.359 | 20 | 20 | 0.014 | 0.001 |
| 2 | Fwd Pkt Len Min | 0.403 | 0.343 | 0 | 6 | 0.765 | 0.363 |
| 3 | Pkt Len Min | 0.394 | 0.342 | 0 | 6 | 0.767 | 0.372 |
| 4 | Bwd IAT Min | 0.353 | 0.820 | 1 | 2 | 0.468 | 0.420 |
| 5 | Fwd IAT Tot | 0.351 | 0.528 | 1663 | 4 | 0.223 | 0.236 |
| 6 | Fwd IAT Max | 0.351 | 0.522 | 1273 | 4 | 0.223 | 0.236 |
| 7 | Fwd IAT Mean | 0.350 | 0.565 | 467.8 | 4 | 0.223 | 0.236 |
| 8 | Init Bwd Win Byts | 0.335 | 0.908 | 149 | -1 | 0.033 | 0.056 |
| 9 | Bwd Pkt Len Min | 0.330 | 0.342 | 0 | 6 | 0.774 | 0.444 |
| 10 | RST Flag Cnt | 0.324 | 0.931 | 0 | 0 | 0.676 | 1.000 |

## Explicit column map (2017 -> 2018)

| CIC-IDS2017 | CSE-CIC-IDS2018 |
|---|---|
| Destination Port | Dst Port |
| Flow Duration | Flow Duration |
| Total Fwd Packets | Tot Fwd Pkts |
| Total Backward Packets | Tot Bwd Pkts |
| Total Length of Fwd Packets | TotLen Fwd Pkts |
| Total Length of Bwd Packets | TotLen Bwd Pkts |
| Fwd Packet Length Max | Fwd Pkt Len Max |
| Fwd Packet Length Min | Fwd Pkt Len Min |
| Fwd Packet Length Mean | Fwd Pkt Len Mean |
| Fwd Packet Length Std | Fwd Pkt Len Std |
| Bwd Packet Length Max | Bwd Pkt Len Max |
| Bwd Packet Length Min | Bwd Pkt Len Min |
| Bwd Packet Length Mean | Bwd Pkt Len Mean |
| Bwd Packet Length Std | Bwd Pkt Len Std |
| Flow Bytes/s | Flow Byts/s |
| Flow Packets/s | Flow Pkts/s |
| Flow IAT Mean | Flow IAT Mean |
| Flow IAT Std | Flow IAT Std |
| Flow IAT Max | Flow IAT Max |
| Flow IAT Min | Flow IAT Min |
| Fwd IAT Total | Fwd IAT Tot |
| Fwd IAT Mean | Fwd IAT Mean |
| Fwd IAT Std | Fwd IAT Std |
| Fwd IAT Max | Fwd IAT Max |
| Fwd IAT Min | Fwd IAT Min |
| Bwd IAT Total | Bwd IAT Tot |
| Bwd IAT Mean | Bwd IAT Mean |
| Bwd IAT Std | Bwd IAT Std |
| Bwd IAT Max | Bwd IAT Max |
| Bwd IAT Min | Bwd IAT Min |
| Fwd PSH Flags | Fwd PSH Flags |
| Bwd PSH Flags | Bwd PSH Flags |
| Fwd URG Flags | Fwd URG Flags |
| Bwd URG Flags | Bwd URG Flags |
| Fwd Header Length | Fwd Header Len |
| Bwd Header Length | Bwd Header Len |
| Fwd Packets/s | Fwd Pkts/s |
| Bwd Packets/s | Bwd Pkts/s |
| Min Packet Length | Pkt Len Min |
| Max Packet Length | Pkt Len Max |
| Packet Length Mean | Pkt Len Mean |
| Packet Length Std | Pkt Len Std |
| Packet Length Variance | Pkt Len Var |
| FIN Flag Count | FIN Flag Cnt |
| SYN Flag Count | SYN Flag Cnt |
| RST Flag Count | RST Flag Cnt |
| PSH Flag Count | PSH Flag Cnt |
| ACK Flag Count | ACK Flag Cnt |
| URG Flag Count | URG Flag Cnt |
| CWE Flag Count | CWE Flag Count |
| ECE Flag Count | ECE Flag Cnt |
| Down/Up Ratio | Down/Up Ratio |
| Average Packet Size | Pkt Size Avg |
| Avg Fwd Segment Size | Fwd Seg Size Avg |
| Avg Bwd Segment Size | Bwd Seg Size Avg |
| Fwd Avg Bytes/Bulk | Fwd Byts/b Avg |
| Fwd Avg Packets/Bulk | Fwd Pkts/b Avg |
| Fwd Avg Bulk Rate | Fwd Blk Rate Avg |
| Bwd Avg Bytes/Bulk | Bwd Byts/b Avg |
| Bwd Avg Packets/Bulk | Bwd Pkts/b Avg |
| Bwd Avg Bulk Rate | Bwd Blk Rate Avg |
| Subflow Fwd Packets | Subflow Fwd Pkts |
| Subflow Fwd Bytes | Subflow Fwd Byts |
| Subflow Bwd Packets | Subflow Bwd Pkts |
| Subflow Bwd Bytes | Subflow Bwd Byts |
| Init_Win_bytes_forward | Init Fwd Win Byts |
| Init_Win_bytes_backward | Init Bwd Win Byts |
| act_data_pkt_fwd | Fwd Act Data Pkts |
| min_seg_size_forward | Fwd Seg Size Min |
| Active Mean | Active Mean |
| Active Std | Active Std |
| Active Max | Active Max |
| Active Min | Active Min |
| Idle Mean | Idle Mean |
| Idle Std | Idle Std |
| Idle Max | Idle Max |
| Idle Min | Idle Min |
| (absent; imputed from Dst Port) | Protocol |
