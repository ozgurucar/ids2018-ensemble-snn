"""IDS2018 v4: architecture screen for the spiking ensemble (seed 42, T=8).

Variants are ranked on the tuning partition only; test numbers are reported for
every variant, including losers, so the screen cannot be cherry-picked.

Reuses the prepared v3 group_ce partitions and preprocessor byte for byte
(attached as the output of ozgurucar/notebookeb0d7e9071). Only the number of
time steps changes. Decision rule, budgets and seeds are those of v3 and were
fixed before this run. Development evidence, not independent validation.
"""
import base64, io, json, os, subprocess, sys, time, zipfile
from pathlib import Path

CODE_ZIP = "__CODE__"
WORK = Path("/kaggle/working/v4")
REPO = WORK/"code"
BASE = {"models": ["esnn"], "steps": 8}
VARIANTS = {
    "pop8": {"populations": 8},
    "wide": {"hidden": [256, 128]},
    "population_only": {"branches": ["population"]},
    "weighted_fusion": {"alpha": 1.0},
    "fast_lr": {"lr": 0.001, "dropout": 0.1},
}

REPO.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(CODE_ZIP))) as archive:
    archive.extractall(REPO)
parents = [p.parent for p in Path("/kaggle/input").rglob("group_ce/manifest.json") if "test-temp" not in str(p)]
assert len(parents) == 1, parents
PARENT = parents[0]
locks = [p for p in Path("/kaggle/input").rglob("requirements-run.lock.txt") if "test-temp" not in str(p)]
print("parent", PARENT, "lock", locks, flush=True)
lock = [l for l in Path(locks[0]).read_text().splitlines() if l and not l.startswith(("nvidia", "triton"))]
(WORK/"lock.txt").write_text("\n".join(lock)+"\n")
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--disable-pip-version-check", "--extra-index-url", "https://download.pytorch.org/whl/cu128", "-r", str(WORK/"lock.txt")], check=False)
os.environ.setdefault("OMP_NUM_THREADS", "2")
sys.path.insert(0, str(REPO))

from idsresearch.derive import derive
from idsresearch.pipeline import train, score, summarize
from idsresearch.provenance import environment, read_json, write_json

parent_env = read_json(PARENT/"manifest.json")["preparation_environment"]["packages"]
now = environment()["packages"]
print("env diff", {k: (parent_env.get(k), v) for k, v in now.items() if parent_env.get(k) != v}, flush=True)
log = {"parent": str(PARENT), "runs": {}}
for name, change in VARIANTS.items():
    out = WORK/f"variant_{name}"
    if not (out/"manifest.json").exists():
        derive(PARENT, out, {**BASE, **change})
    start = time.time()
    train(out, seeds=[42], device="cuda")
    tune = read_json(out/"runs"/"esnn-42"/"trained.json")["tune_metrics"]["macro_f1"]
    score(out, seeds=[42], device="cuda")
    summary = summarize(out)
    r = summary["aggregate"]["esnn"]["0.05"]
    log["runs"][name] = {"change": change, "tune_macro_f1": tune, "test_macro_f1_tau05": r["macro_f1"]["mean"],
                         "test_adr": r["adr"]["mean"], "seconds": time.time()-start, "experiment_id": summary["experiment_id"]}
    print(name, log["runs"][name], flush=True)
    write_json(WORK/"v4-variants-log.json", log)
print("done", flush=True)
