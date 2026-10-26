import io
import time
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from detector import Detector, true_labels

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "samples" / "demo_flows.csv"
MAX_ROWS = 200_000

app = FastAPI(title="IDS2018 E-SNN detector", version="3.0")


@lru_cache(maxsize=2)
def detector(name):
    if name not in ("esnn", "xgb"):
        raise HTTPException(400, "model must be esnn or xgb")
    return Detector(name)


def run(frame, model):
    if len(frame) > MAX_ROWS:
        raise HTTPException(413, f"At most {MAX_ROWS} rows per request")
    start = time.perf_counter()
    try:
        out = detector(model).predict(frame)
    except ValueError as error:
        raise HTTPException(422, str(error))
    elapsed = time.perf_counter() - start
    truth = true_labels(frame)
    summary = {"model": model, "rows": len(out), "alarms": int(out.alarm.sum()),
               "seconds": round(elapsed, 3), "flows_per_second": round(len(out) / max(elapsed, 1e-9)),
               "predicted": out.prediction.value_counts().to_dict()}
    if truth is not None:
        out.insert(0, "label", truth.to_numpy())
        attack = truth != "Benign"
        summary["accuracy"] = round(float((out.prediction == truth).mean()), 4)
        summary["detection_rate"] = round(float(out.alarm[attack].mean()), 4) if attack.any() else None
        summary["false_alarm_rate"] = round(float(out.alarm[~attack].mean()), 4) if (~attack).any() else None
    return {"summary": summary, "rows": out.head(500).to_dict(orient="records")}


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "models": ["esnn", "xgb"], "demo": SAMPLES.exists()}


@app.post("/api/predict")
async def predict(file: UploadFile = File(...), model: str = Form("esnn")):
    try:
        frame = pd.read_csv(io.BytesIO(await file.read()), low_memory=False)
    except Exception as error:
        raise HTTPException(400, f"Could not read CSV: {error}")
    return run(frame, model)


class Flows(BaseModel):
    model: str = "esnn"
    flows: list[dict]


@app.post("/api/flows")
def flows(body: Flows):
    return run(pd.DataFrame(body.flows), body.model)


@app.get("/api/demo")
def demo(model: str = "esnn"):
    if not SAMPLES.exists():
        raise HTTPException(404, "Demo sample not bundled")
    return run(pd.read_csv(SAMPLES, low_memory=False), model)
