"""IDS2018 v5: more seeds, a spike-free PLE-MLP control and a Dst Port ablation.

Derives from the prepared v3 group_ce experiment (the output of Kaggle notebook
ozgurucar/notebookeb0d7e9071) and reuses its partitions and preprocessor byte
for byte. Only model fields and seeds change (EXPERIMENTS is filled in at
build time); the decision rule and budgets are those of v3. Development
evidence, not independent validation.
"""
import base64, io, json, os, subprocess, sys, time, zipfile
from pathlib import Path

CODE_ZIP = "__CODE__"
WORK = Path("/kaggle/working/v5")
REPO = WORK/"code"
EXPERIMENTS = __EXPERIMENTS__

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
for name, change in EXPERIMENTS.items():
    out = WORK/name
    if not (out/"manifest.json").exists():
        derive(PARENT, out, change)
    start = time.time()
    train(out, device="cuda")
    score(out, device="cuda")
    summary = summarize(out)
    log["runs"][name] = {"change": change, "seconds": time.time()-start, "experiment_id": summary["experiment_id"]}
    for model, by_tau in summary["aggregate"].items():
        r = by_tau["0.05"]
        print(f"{name} {model} macroF1={r['macro_f1']['mean']:.4f}±{r['macro_f1']['std']:.4f} n={r['macro_f1']['n']} ADR={r['adr']['mean']:.4f} FPR={r['fpr']['mean']:.4f}", flush=True)
    write_json(WORK/"v5-log.json", log)
print("done", flush=True)
