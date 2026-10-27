# Do spiking networks help flow-based intrusion detection? (CSE-CIC-IDS2018)

Duplicate-controlled comparison of a three-branch ensemble spiking network (E-SNN) with a parameter-matched MLP, the same MLP on a spike-free piecewise-linear encoding (PLE-MLP), a spike-input control (Enc-ANN: the SNN's spike codes fed to a non-spiking network) and tree ensembles. Rows with identical cleaned feature vectors stay in one partition; probability calibration, alarm thresholds and test use disjoint partitions; every model is judged at the same benign false-alarm rate (FAR).

Paper: `paper/main.tex` (PDF: `paper/main.pdf`). Reviews and responses: `paper/review_*`, `paper/RESPONSE_TO_REVIEWERS.md`.

## Main result (5% FAR, T = 4, five seeds 42–46, `results/v5/seeds/summary.json`)

| Model | Macro-F1 (13 classes) | Macro-F1 (11 identifiable classes) | Detection rate |
|---|---|---|---|
| E-SNN | 0.766 ± 0.011 | 0.828 ± 0.014 | 0.959 |
| Matched MLP | 0.755 ± 0.004 | 0.820 ± 0.004 | 0.958 |
| PLE-MLP | 0.761 ± 0.005 | 0.824 ± 0.003 | 0.959 |
| Enc-ANN | 0.779 ± 0.020 | 0.842 ± 0.013 | 0.961 |
| XGBoost | 0.808 ± 0.004 | 0.858 ± 0.001 | 0.967 |

- Only the gap to XGBoost is significant (E-SNN − XGBoost −4.2 points, 95% CI [−5.6, −2.8], Holm p = 0.002). The E-SNN is equivalent to the PLE-MLP within 2 points at 5% FAR (TOST p = 0.020); we find no evidence that spiking dynamics add accuracy. The best neural model is the non-spiking Enc-ANN (exploratory). These intervals cover seed variance; a bootstrap over test fingerprint groups shows that test-sampling variance is small (about ±0.5 points on detection rate) and that every paired detection-rate and AUC difference keeps its sign (`results/analysis/group_bootstrap_table.md`). No interval covers a redrawn split. Source: `results/analysis/seed_stats_5seed_table.md`.
- The three-seed T = 12 run with random forest and CatBoost is in `results/v3/experiments/group_ce/summary.json` (Table II, bottom block, of the paper).
- 4 time steps match 12 at 2.9× fewer synaptic events, but under published Loihi per-operation costs the E-SNN needs 3.1–9.0 µJ per flow against 0.40 µJ for the MLP on a 45 nm accelerator (`results/analysis/energy_unified_table.md`).
- Destination port is an input. Removing it costs 1–3 macro-F1 points (13 / 11 classes) and does not fix transfer (`results/analysis/NOTE_7_noport.md`).
- Transfer to CIC-IDS2017 fails for every model: after refitting the threshold on local benign flows, 23–32% of attack flows are detected (13.5–34.4% for models retrained without the destination port). The apparent good transfer of slow application-layer DoS (GoldenEye, Slowloris) depends on the destination-port input. Expect to retrain on your own traffic.

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
| `results/analysis/` | CPU analyses behind the paper; each `NOTE_*.md` explains one item and its script |
| `scripts/` | Figures, transfer, adaptation, energy and profiling scripts |
| `scripts/analysis/` | Scripts that produce `results/analysis/` |
| `app/` | Detector service (FastAPI) and seed-42 checkpoints |

## Install and test

```bash
python -m venv .venv && . .venv/bin/activate      # keep it outside iCloud-synced folders
pip install -r requirements.txt pytest
python -m pytest -q tests                          # 44 tests
python -m idsresearch smoke --out /tmp/smoke       # pipeline on synthetic data
```

Exact package versions of the training runs are in `results/v3/requirements-run.lock.txt` and `results/v5/seeds/lock.txt`.

## Verify the claims

These run from the repository alone (records only):

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

| Paper item | Script | Needs | Where it comes from |
|---|---|---|---|
| Table IV energy (test-mix rows) | `scripts/analysis/energy_unified.py` | four raw 2018 day files in `~/.cache/ids-v4/raw` (02-14, 02-15, 02-21, 03-02) | Kaggle dataset `solarmainframe/ids-intrusion-csv` |
| Transfer (Table V), KS shift, name map | `scripts/cross_dataset_cic2017.py`, `scripts/analysis/transfer_hygiene.py` | `~/.cache/ids-x17/combine.csv` (MachineLearningCVE files concatenated), plus the raw 2018 days above | Kaggle dataset `sweety18/cicids2017-full-dataset` |
| Adaptation (Table VI) | `scripts/finetune_cic2017.py`, `scripts/analysis/adapt_label_budget.py` | `combine.csv` above | as above |
| Dst Port ablation, transfer half | `scripts/analysis/noport.py` | no-port checkpoints in `~/.cache/ids-v5/noport/`, T = 4 Enc-ANN checkpoint in `~/.cache/ids-v4/steps/` | Kaggle kernel outputs `ozgurucar/ids-v5-noport` and `ozgurucar/ids-v4-steps` |
| Group bootstrap over test groups (`results/analysis/group_bootstrap_table.md`) | `scripts/analysis/group_bootstrap.py` | per-row test scores (`test_log_odds.npy`), `test_y.npy`, `test_groups.npy` | Kaggle kernel output `ozgurucar/ids-v5-seeds`; the score files are no longer in git (`.gitignore`) |
| Operation counts from checkpoints | `scripts/profile_all_steps.py` | v3/v4 checkpoints in the Kaggle working-directory layout | Kaggle kernel outputs of the v3, `ids-v4-steps` and `ids-v4-variants` runs |

Only seed-42 checkpoints are in `app/models/` (E-SNN T = 12 and T = 4, XGBoost; `profile/` holds the T = 12 matched MLP and Enc-ANN). Other seeds, the PLE-MLP and the no-port models are available only as Kaggle kernel outputs.

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
pip install -r app/requirements.txt
PYTHONPATH=.:app uvicorn server:app --app-dir app --port 8000
```

API: `POST /api/predict` (multipart CSV, `model=esnn|esnn_t4|xgb`), `POST /api/flows` (JSON `{"model": "esnn", "flows": [...]}`), `GET /api/demo`. The demo flows come from the public dataset and may overlap the test split, so demo numbers are not an evaluation.

## Reproduce training

The pipeline is in `idsresearch/` (`python -m idsresearch --help`). It was run on Kaggle with the `solarmainframe/ids-intrusion-csv` dataset; the kernel templates in `kaggle/` derive the T = 4/8, variant, five-seed and no-port runs from the main run's partitions and refuse to run if the data hashes differ. The earlier notebook version is kept in `legacy/`.
