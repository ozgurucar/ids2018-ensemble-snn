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
uv venv -p 3.12 .venv && uv pip install -p .venv/bin/python --extra-index-url https://download.pytorch.org/whl/cpu --index-strategy unsafe-best-match -r app/requirements.txt
PYTHONPATH=.:app .venv/bin/uvicorn server:app --app-dir app --port 8000
```

API: `POST /api/predict` (multipart CSV, `model=esnn|xgb`), `POST /api/flows` (JSON `{"model": "esnn", "flows": [...]}`), `GET /api/demo`.

The demo flows come from the public dataset and may overlap the test split, so demo numbers are not an evaluation.

## Reproduce training

The full pipeline (24 runs) is in `idsresearch/`; `python -m idsresearch --help`. It was run on Kaggle with the `solarmainframe/ids-intrusion-csv` dataset. `python -m idsresearch smoke --out /tmp/smoke` checks the code on synthetic data. `scripts/profile_efficiency.py` reproduces the operation counts.

The earlier notebook version is kept in `legacy/`.
