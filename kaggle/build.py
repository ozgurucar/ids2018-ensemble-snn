"""Build a Kaggle script kernel from a template: embeds idsresearch/ as a zip.

    python kaggle/build.py kaggle/v5/template.py ids-v6-ple-ensemble \
        '{"ple_ensemble_T4": {"models": ["ple_ensemble"], "seeds": [42, 43, 44, 45, 46], "steps": 4}}'
"""
import base64
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(template, slug, experiments):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((ROOT/"idsresearch").glob("*.py")):
            archive.write(path, f"idsresearch/{path.name}")
    source = Path(template).read_text()
    source = source.replace('"__CODE__"', repr(base64.b64encode(buffer.getvalue()).decode()))
    source = source.replace("__EXPERIMENTS__", repr(json.loads(experiments)))
    out = Path(template).parent/"build"/slug
    out.mkdir(parents=True, exist_ok=True)
    (out/f"{slug}.py").write_text(source)
    (out/"kernel-metadata.json").write_text(json.dumps({
        "id": f"ozgurucar/{slug}", "title": slug, "code_file": f"{slug}.py", "language": "python",
        "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
        "dataset_sources": [], "kernel_sources": ["ozgurucar/notebookeb0d7e9071"], "competition_sources": [],
        "machine_shape": "NvidiaTeslaT4"}, indent=1))
    print(out)


if __name__ == "__main__":
    main(*sys.argv[1:4])
