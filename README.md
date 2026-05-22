# 🧠 Leakage-Free Ensemble Spiking Neural Network for Network Intrusion Detection

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/downloads/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.x-ee4c2c.svg)](https://pytorch.org/)
[![snnTorch](https://img.shields.io/badge/snnTorch-0.9-green.svg)](https://snntorch.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Official code repository** for the paper:
> *"Leakage-Free Ensemble Spiking Neural Network for Network Intrusion Detection"*

---

## 📋 Overview

This repository implements an **Ensemble Spiking Neural Network (SNN)** for multi-class network intrusion detection on the [CSE-CIC-IDS2018](https://www.unb.ca/cic/datasets/ids-2018.html) dataset. The system combines three distinct neural coding strategies into a unified ensemble with a learned meta-learner, achieving state-of-the-art detection performance while maintaining a **fully leakage-free** experimental protocol.

### Architecture

```
                    ┌───────────────────┐
                    │    Input (x)       │
                    └─────┬─────────────┘
              ┌───────────┼───────────────┐
              ▼           ▼               ▼
       ┌──────────┐ ┌──────────┐  ┌──────────────┐
       │ Rate SNN │ │Temporal  │  │  Hybrid Pop  │
       │(Bernoulli)│ │SNN(Time)│  │  SNN (×4)    │
       └────┬─────┘ └────┬─────┘  └──────┬───────┘
            │             │               │
            ▼             ▼               ▼
       ┌────────────────────────────────────────┐
       │  Learnable Softmax Weights (w₁,w₂,w₃) │
       │  + Meta-Learner MLP (concat → 64 → C) │
       └────────────────┬───────────────────────┘
                        ▼
              ┌───────────────────┐
              │  Final Prediction │
              │  0.6·W + 0.4·Meta │
              └───────────────────┘
```

### Key Features

| Feature | Detail |
|---|---|
| **Rate-Coded SNN** | Bernoulli spike encoding with learnable β — LIF layers: 256→128→64 |
| **Temporal-Coded SNN** | Spike-timing encoding with GELU encoder — LIF layers: 512→256→128 |
| **Hybrid Population SNN** | Population expansion (×4) with residual connections — LIF layers: 384→192→96 |
| **Meta-Learner** | MLP that fuses concatenated SNN outputs for adaptive ensemble weighting |
| **Leakage-Free Protocol** | Chronological stratified split (70/10/20) — no future data in training |
| **Focal Loss** | γ=2.0 with label smoothing (0.05) and dynamic class weights |
| **BorderlineSMOTE** | Applied only on training set after scaling |

---

## 🗂️ Repository Structure

```
.
├── README.md                 # This file
├── notebook.ipynb            # Main experiment notebook (fully reproducible)
├── requirements.txt          # Python dependencies
├── LICENSE                   # MIT License
└── figures/                  # Architecture and result figures
    ├── fig1.png
    ├── fig2.png
    ├── fig3.jpg
    ├── fig4.jpg
    ├── fig5.jpg
    └── fig6.jpg
```

---

## 🚀 Quick Start

### Option 1: Run on Kaggle (Recommended)

This notebook was developed and tested on [Kaggle](https://www.kaggle.com/) with a **Tesla T4 GPU**. You can fork the notebook directly and run it with the [CSE-CIC-IDS2018 dataset](https://www.kaggle.com/datasets/solarmainframe/ids-intrusion-csv).

### Option 2: Local Setup

```bash
# Clone the repository
git clone https://github.com/ozgurucar/ids2018-ensemble-snn.git
cd ids2018-ensemble-snn

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Launch Jupyter
jupyter notebook notebook.ipynb
```

> **Note:** Training requires a CUDA-capable GPU. A Tesla T4 or better is recommended.

---

## ⚙️ Hyperparameters

| Parameter | Value | Description |
|---|---|---|
| `SEED` | 42 | Random seed for full reproducibility |
| `LR` | 4×10⁻⁴ | AdamW learning rate |
| `WEIGHT_DECAY` | 1×10⁻³ | L2 regularization |
| `NUM_EPOCHS` | 35 | Maximum training epochs |
| `PATIENCE` | 20 | Early stopping patience |
| `GRAD_CLIP` | 0.5 | Gradient clipping max norm |
| `FOCAL_GAMMA` | 2.0 | Focal loss focusing parameter |
| `LABEL_SMOOTH` | 0.05 | Label smoothing factor |
| `BATCH_SIZE` | 1024 | Mini-batch size |
| `num_steps` | 12 | SNN simulation timesteps |

---

## 📊 Baseline Comparisons

The notebook includes two baseline models trained with **identical data splits, features, and preprocessing** for a fair comparison:

1. **ANN Baseline** — Feed-forward MLP with residual connection (512→512→256→C)
2. **Random Forest Baseline** — scikit-learn RandomForestClassifier (100 trees, max depth 25)

---

## 📚 Dataset

This work uses the [CSE-CIC-IDS2018 dataset](https://www.unb.ca/cic/datasets/ids-2018.html) from the Canadian Institute for Cybersecurity.

> **Citation:**  
> Sharafaldin, I., Lashkari, A. H., & Ghorbani, A. A. (2018). *Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization.* ICISSP.

---

## 📄 Citation

If you use this code in your research, please cite:

```bibtex
@misc{ids2018_ensemble_snn,
  title   = {Leakage-Free Ensemble Spiking Neural Network for Network Intrusion Detection},
  author  = {Özgür Uçar},
  year    = {2026},
  url     = {https://github.com/ozgurucar/ids2018-ensemble-snn}
}
```

---

## 📝 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
