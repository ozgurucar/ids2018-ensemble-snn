# Ensemble SNN for intrusion detection on CSE-CIC-IDS2018 (v3)

Leakage-controlled comparison of a three-branch spiking network with a parameter-matched MLP, a spike-input control and three tree ensembles. Rows with identical cleaned feature vectors stay in one partition; calibration, alarm thresholds and test use disjoint partitions; every model is judged at the same benign false-alarm budget.

| Model (5% FPR budget) | Macro-F1 | Attack detection |
|---|---|---|
| E-SNN | 0.769 ± 0.022 | 0.959 |
| Matched ANN | 0.756 ± 0.004 | 0.958 |
| Spike-input control | 0.787 ± 0.017 | 0.963 |
| Random forest | 0.788 ± 0.001 | 0.965 |
| CatBoost | 0.791 ± 0.005 | 0.965 |
| XGBoost | 0.808 ± 0.005 | 0.967 |

Time-window ablation (v4, same partitions): the E-SNN keeps its accuracy with 4 time steps instead of 12 (macro-F1 0.766 ± 0.015 vs 0.769 ± 0.022) while synaptic events per flow fall from 339,801 to 116,864. A five-variant architecture screen (selected on the tuning partition, all test results reported) found no clear improvement. Records: `results/v4/`.

Paper: `paper/main.tex` (PDF in `paper/main.pdf`). Raw run records: `results/v3/`.

## Run the detector

```bash
docker compose up --build
```

Open http://localhost:8000, upload a CICFlowMeter CSV or press "Run bundled demo". To imitate a live sensor:

```bash
python app/replay.py app/samples/demo_flows.csv --url http://localhost:8000
```

Without Docker:

```bash
uv venv -p 3.12 ~/.venvs/ids && uv pip install -p ~/.venvs/ids/bin/python --extra-index-url https://download.pytorch.org/whl/cpu --index-strategy unsafe-best-match -r app/requirements.txt
PYTHONPATH=.:app ~/.venvs/ids/bin/uvicorn server:app --app-dir app --port 8000
```

(Keep the virtual environment outside iCloud-synced folders such as Desktop.)

API: `POST /api/predict` (multipart CSV, `model=esnn|esnn_t4|xgb`), `POST /api/flows` (JSON `{"model": "esnn", "flows": [...]}`), `GET /api/demo`.

The demo flows come from the public dataset and may overlap the test split, so demo numbers are not an evaluation.

## Verify the claims yourself

Every number in the paper can be checked from this repository:

| Claim | How to check |
|---|---|
| Main table, per-class F1 | `results/v3/experiments/*/summary.json` (per-seed records, hashes of checkpoints and test outputs) |
| Time-window ablation, architecture screen | `results/v4/` |
| Operation counts | `python scripts/profile_all_steps.py` (needs the checkpoints from Kaggle; see the script) |
| The service works | `docker compose up --build`, then the demo button or `app/replay.py` |
| Transfer to another network | Download `sweety18/cicids2017-full-dataset` from Kaggle, then `python scripts/cross_dataset_cic2017.py combine.csv out.json` |

The transfer test is deliberately unforgiving: the frozen 2018 models are scored on CIC-IDS2017 without refitting anything. False alarms rise to 23–26%, and with a threshold refitted on local benign traffic only, 23–32% of attack flows are detected. Slow application-layer DoS (GoldenEye, Slowloris) is the exception. Expect to retrain on your own traffic before relying on these models.

## Reproduce training

The full pipeline (24 runs) is in `idsresearch/`; `python -m idsresearch --help`. It was run on Kaggle with the `solarmainframe/ids-intrusion-csv` dataset. `python -m idsresearch smoke --out /tmp/smoke` checks the code on synthetic data. `scripts/profile_efficiency.py` reproduces the operation counts.

The earlier notebook version is kept in `legacy/`.
