"""IDS2018 v4: time-window ablation for the spiking ensemble and its spike-input control.

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
STEPS = (4, 8)
CHANGES = {"models": ["esnn", "encoded_ann"]}

REPO.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(CODE_ZIP))) as archive:
    archive.extractall(REPO)
parents = [p.parent for p in Path("/kaggle/input").rglob("group_ce/manifest.json") if "test-temp" not in str(p)]
assert len(parents) == 1, parents
PARENT = parents[0]
locks = [p for p in Path("/kaggle/input").rglob("requirements-run.lock.txt") if "test-temp" not in str(p)]
print("parent", PARENT, "lock", locks, flush=True)
lock = [l for l in Path(locks[0]).read_text().splitlines() if l and not l.startswith(("torch", "nvidia", "triton"))]
(WORK/"lock.txt").write_text("\n".join(lock)+"\n")
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--disable-pip-version-check", "-r", str(WORK/"lock.txt")], check=False)
os.environ.setdefault("OMP_NUM_THREADS", "2")
sys.path.insert(0, str(REPO))

from idsresearch.derive import derive
from idsresearch.pipeline import train, score, summarize
from idsresearch.provenance import environment, read_json, write_json

parent_env = read_json(PARENT/"manifest.json")["preparation_environment"]["packages"]
now = environment()["packages"]
print("env diff", {k: (parent_env.get(k), v) for k, v in now.items() if parent_env.get(k) != v}, flush=True)
log = {"parent": str(PARENT), "runs": {}}
for steps in STEPS:
    out = WORK/f"group_ce_T{steps}"
    if not (out/"manifest.json").exists():
        derive(PARENT, out, {**CHANGES, "steps": steps})
    start = time.time()
    train(out, device="cuda")
    score(out, device="cuda")
    summary = summarize(out)
    log["runs"][steps] = {"seconds": time.time()-start, "experiment_id": summary["experiment_id"]}
    agg = summary["aggregate"]
    for model, by_tau in agg.items():
        r = by_tau["0.05"]
        print(f"T={steps} {model} macroF1={r['macro_f1']['mean']:.4f}±{r['macro_f1']['std']:.4f} ADR={r['adr']['mean']:.4f} FPR={r['fpr']['mean']:.4f}", flush=True)
    write_json(WORK/"v4-log.json", log)
print("done", flush=True)
