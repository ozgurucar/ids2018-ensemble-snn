# Do spiking networks help flow-based intrusion detection? (CSE-CIC-IDS2018)

This repository compares a three-branch ensemble spiking network (E-SNN) on CSE-CIC-IDS2018 flows with four baselines: a parameter-matched MLP, the same MLP on a spike-free piecewise-linear encoding (PLE-MLP), a spike-input control (Enc-ANN, which feeds the SNN's spike codes to a non-spiking network) and tree ensembles. Rows with identical cleaned feature vectors stay in one partition. Calibration, threshold selection and testing each get their own partition, and all models are compared at the same benign false-alarm rate (FAR).

The paper source is `paper/main.tex` (PDF: `paper/main.pdf`). The code and records it reports are tagged `paper-v1`.

## Main result (5% FAR, T = 4, five seeds 42–46, `results/v5/seeds/summary.json`)

| Model | Macro-F1 (13 classes) | Macro-F1 (11 identifiable classes) | Detection rate |
|---|---|---|---|
| E-SNN | 0.766 ± 0.011 | 0.828 ± 0.014 | 0.959 |
| Matched MLP | 0.755 ± 0.004 | 0.820 ± 0.004 | 0.958 |
| PLE-MLP | 0.761 ± 0.005 | 0.824 ± 0.003 | 0.959 |
| Enc-ANN | 0.779 ± 0.020 | 0.842 ± 0.013 | 0.961 |
| XGBoost | 0.808 ± 0.004 | 0.858 ± 0.001 | 0.967 |

- Only the E-SNN–XGBoost difference is significant: −4.2 points (95% CI [−5.6, −2.8], Holm p = 0.002). Source: `results/analysis/seed_stats_5seed_table.md`.
- At 5% FAR the E-SNN is within 2 points of the PLE-MLP (TOST p = 0.020), so spiking dynamics give no accuracy gain here. The non-spiking Enc-ANN has the highest neural mean, but not significantly above the E-SNN (Holm p = 0.51).
- Intervals cover seed variance, not a redrawn split. A bootstrap over test fingerprint groups adds about ±0.5 points of detection rate, and no paired difference in detection rate or AUC changes sign (`results/analysis/group_bootstrap_table.md`).
- The three-seed T = 12 run, which also includes random forest and CatBoost, is in `results/v3/experiments/group_ce/summary.json` (bottom block of Table II in the paper).
- T = 4 matches T = 12 in accuracy with 2.9× fewer synaptic events. With published Loihi per-operation costs, though, the E-SNN needs 3.1–9.0 µJ per flow. That is 2.5–7.2× the MLP when its SRAM weight reads are counted (1.24 µJ; 0.40 µJ for arithmetic alone). See `results/analysis/energy_unified_table.md`.
- Destination port is a model input. Dropping it costs 1–3 macro-F1 points (13 / 11 classes) and does not improve cross-dataset transfer (`results/analysis/NOTE_7_noport.md`).
- All models do poorly on CIC-IDS2017. With the threshold refitted on local benign flows, 23–32% of attack flows are detected (13.5–34.4% for models retrained without the destination port). The slow application-layer DoS attacks (GoldenEye, Slowloris) are the exception, and only because of the destination-port input. A deployment on other traffic would need retraining.

## Repository layout

| Path | Contents |
|---|---|
| `idsresearch/` | Pipeline: data preparation, feature-group split, models, training, decision rule, evaluation |
| `configs/` | Run configurations (`group_ce.json` is the main run) |
| `kaggle/` | Kaggle kernel templates: `v4-steps` (T = 4/8), `v4-variants` (architecture screen), `v5` (five-seed and no-port runs) |
| `results/v3/` | Main run, T = 12, three seeds (summary, manifest, per-run records) |
| `results/v4/` | Time-window ablation, architecture screen, operation counts, Loihi estimate |
| `results/v5/seeds/` | Five-seed T = 4 run: E-SNN, Enc-ANN, matched MLP, PLE-MLP, XGBoost |
| `results/v5/noport/` | Dst Port ablation, three seeds, T = 4 |
| `results/cross_dataset/` | CIC-IDS2017 transfer and local adaptation |
| `results/analysis/` | CPU analyses used in the paper; each `NOTE_*.md` describes one analysis and its script |
| `scripts/` | Figures, transfer, adaptation, energy and profiling scripts |
| `scripts/analysis/` | Scripts that write `results/analysis/` |
| `app/` | Detector service (FastAPI) and seed-42 checkpoints |

## Install and test

```bash
python -m venv .venv && . .venv/bin/activate      # keep it outside iCloud-synced folders
pip install -r requirements.txt pytest
python -m pytest -q tests                          # 44 tests
python -m idsresearch smoke --out /tmp/smoke       # pipeline on synthetic data
```

The package versions used for the training runs are pinned in `results/v3/requirements-run.lock.txt` and `results/v5/seeds/lock.txt`.

## Reproducing the numbers

These commands regenerate the analyses from the committed run records:

| Paper item | Command | Output |
|---|---|---|
| Table II (5-seed statistics, TOST) | `python scripts/analysis/seed_stats.py --no-defaults --summary T4=results/v5/seeds/summary.json --primary-label T4 --out seed_stats_5seed` | `results/analysis/seed_stats_5seed_table.md` |
| Three-seed statistics (T = 12) | `python scripts/analysis/seed_stats.py` | `results/analysis/seed_stats_table.md` |
| 11-class macro-F1, per-class F1 (Tables II, III) | `python scripts/analysis/identifiable_macro_f1.py` | `results/analysis/identifiable_macro_f1_table.md` |
| Per-day FAR, argmax point, calibration effect | `python scripts/analysis/operating_context.py` | `results/analysis/operating_context_table.md` |
| Adaptation summary (Table VI) | `python scripts/analysis/adapt_summary.py` | `results/analysis/adapt_label_budget_table.md` |
| Energy, demo sample only | `python scripts/analysis/energy_unified.py --skip-test-mix` | `results/analysis/energy_unified_table.md` (demo rows) |
| Figures | `python scripts/make_figures.py --skip-tikz` | `paper/figures/` |
| Paper | `cd paper && tectonic main.tex` | `paper/main.pdf` |

These need data or checkpoints that are not in git:

| Paper item | Script | Needs | Source |
|---|---|---|---|
| Table IV energy (test-mix rows) | `scripts/analysis/energy_unified.py` | four raw 2018 day files in `~/.cache/ids-v4/raw` (02-14, 02-15, 02-21, 03-02) | Kaggle dataset `solarmainframe/ids-intrusion-csv` |
| Transfer (Table V), KS shift, name map | `scripts/cross_dataset_cic2017.py`, `scripts/analysis/transfer_hygiene.py` | `~/.cache/ids-x17/combine.csv` (MachineLearningCVE files concatenated), plus the raw 2018 days above | Kaggle dataset `sweety18/cicids2017-full-dataset` |
| Adaptation (Table VI) | `scripts/finetune_cic2017.py`, `scripts/analysis/adapt_label_budget.py` | `combine.csv` above | as above |
| Dst Port ablation, transfer half | `scripts/analysis/noport.py` | no-port checkpoints in `~/.cache/ids-v5/noport/`, T = 4 Enc-ANN checkpoint in `~/.cache/ids-v4/steps/` | Kaggle kernel outputs (on request, see below) |
| Group bootstrap over test groups (`results/analysis/group_bootstrap_table.md`) | `scripts/analysis/group_bootstrap.py` | per-row test scores (`test_log_odds.npy`), `test_y.npy`, `test_groups.npy` | Kaggle kernel output of the five-seed run; excluded by `.gitignore` because of size (on request, see below) |
| Operation counts from checkpoints | `scripts/profile_all_steps.py` | v3/v4 checkpoints in the Kaggle working-directory layout | Kaggle kernel outputs of the v3 and v4 runs (on request) |

`app/models/` holds only the seed-42 checkpoints: E-SNN at T = 12 and T = 4 and XGBoost, plus the T = 12 matched MLP and Enc-ANN in `profile/`. The other seeds, the PLE-MLP and the no-port models exist only as Kaggle kernel outputs. They are available from the author on request and will be released with the camera-ready version.

## Run the detector

```bash
docker compose up --build
```

Open http://localhost:8000 and upload a CICFlowMeter CSV, or press "Run bundled demo". To replay flows in small batches, as a live sensor would send them:

```bash
python app/replay.py app/samples/demo_flows.csv --url http://localhost:8000
```

Without Docker:

```bash
pip install -r app/requirements.txt
PYTHONPATH=.:app uvicorn server:app --app-dir app --port 8000
```

The service uses the seed-42 checkpoints listed above (E-SNN at T = 12 and T = 4, XGBoost), not the five-seed models. It loads joblib pickles, so only run it with the files shipped here.

API: `POST /api/predict` (multipart CSV, `model=esnn|esnn_t4|xgb`), `POST /api/flows` (JSON `{"model": "esnn", "flows": [...]}`), `GET /api/demo`. The demo flows are taken from the public dataset and may overlap the test split, so the demo numbers are not an evaluation.

## Reproduce training

The pipeline is in `idsresearch/` (`python -m idsresearch --help`). The runs were done on Kaggle with the `solarmainframe/ids-intrusion-csv` dataset. The kernel templates in `kaggle/` build the T = 4/8, variant, five-seed and no-port runs from the main run's partitions and stop if the data hashes differ. `legacy/` keeps the earlier notebook version.
