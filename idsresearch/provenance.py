import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    os.replace(temporary, path)


def read_json(path):
    return json.loads(Path(path).read_text())


def source_manifest():
    root = Path(__file__).parent
    return {p.name: file_hash(p) for p in sorted(root.glob("*.py"))}


def environment():
    versions = {}
    for name in ("numpy", "pandas", "scipy", "scikit-learn", "torch", "snntorch", "xgboost", "matplotlib", "joblib", "catboost"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return {"python": sys.version, "platform": platform.platform(), "packages": versions}


def assert_sources(manifest):
    if manifest["sources"] != source_manifest():
        raise ValueError("Source changed since preparation. Prepare a new experiment directory.")
