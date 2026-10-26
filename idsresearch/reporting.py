from pathlib import Path
from .pipeline import summarize, validated
from .provenance import write_json


def readiness(out):
    manifest, config = validated(out)
    summary = summarize(out)
    blockers = []
    if config.development_only:
        blockers.append("Development suite informed by previously inspected test results; independent confirmation required")
    if config.provenance != "real":
        blockers.append("Synthetic output is software verification, not paper evidence")
    if config.max_files:
        blockers.append("Partial-file run is exploratory")
    if summary["missing_runs"]:
        blockers.append("Missing declared runs: " + ", ".join(summary["missing_runs"]))
    if len(config.seeds) < 3:
        blockers.append("At least three predeclared seeds required for the main table")
    if manifest["timestamp_review"]["timestamp_status"] != "verified":
        blockers.append("Real timestamp review is not verified")
    warnings = []
    for part, values in manifest["split"]["counts"].items():
        rare = [name for name, n in values.items() if n < 20]
        if rare:
            warnings.append(f"{part}: fewer than 20 real examples in {', '.join(rare)}")
    return {"numerical_export_allowed": not blockers, "blockers": blockers, "warnings": warnings,
            "note": "Passing is a numerical provenance check, not publication acceptance or proof of generalisation."}


def tex_escape(text):
    return str(text).replace("_", r"\_").replace("%", r"\%").replace("&", r"\&")


def export(out, destination, draft=False):
    out, destination = Path(out), Path(destination)
    manifest, config = validated(out)
    summary = summarize(out)
    status = readiness(out)
    write_json(out/"readiness.json", status)
    if status["blockers"] and not draft:
        raise ValueError("Paper export refused: " + "; ".join(status["blockers"]))
    destination.mkdir(parents=True, exist_ok=True)
    macro = [r"% Generated from one immutable experiment; do not edit."]
    macro += [rf"\newcommand{{\RunIdentity}}{{\texttt{{{manifest['experiment_id'][:12]}}}}}",
              rf"\newcommand{{\RunSeeds}}{{{len(config.seeds)}}}",
              rf"\newcommand{{\RunSteps}}{{{config.steps}}}",
              rf"\newcommand{{\RunFeatures}}{{{len(manifest['preprocessing']['selected_columns'])}}}",
              rf"\newcommand{{\RunTau}}{{{config.primary_tau}}}",
              rf"\newcommand{{\RunSplit}}{{{tex_escape(config.split)}}}",
              rf"\newcommand{{\RunStatus}}{{{('DRAFT / ' + config.provenance.upper()) if status['blockers'] else 'VERIFIED NUMERICAL EXPORT'}}}"]
    (destination/"macros.tex").write_text("\n".join(macro)+"\n")
    prefix = ("DRAFT / " + config.provenance.upper() + ": ") if status["blockers"] else ""
    table = [r"\begin{table*}[t]", r"\centering", r"\caption{" + prefix + r"Test performance at the predeclared primary calibration FPR budget. Mean $\pm$ sample standard deviation across seeds.}",
             r"\label{tab:main}", r"\begin{tabular}{lrrr}", r"\toprule", r"Model & Macro-F1 & ADR & FPR \\", r"\midrule"]
    def fmt(entry):
        if entry["mean"] is None:
            return "--"
        if entry["std"] is None:
            return f"{entry['mean']:.4f} (n=1)"
        return f"{entry['mean']:.4f} $\\pm$ {entry['std']:.4f}"
    for name, metrics in summary["aggregate"].items():
        values = metrics[str(config.primary_tau)]
        table.append(tex_escape(name)+" & "+" & ".join(fmt(values[k]) for k in ("macro_f1", "adr", "fpr"))+r" \\")
    table += [r"\bottomrule", r"\end{tabular}", r"\end{table*}"]
    (destination/"main_table.tex").write_text("\n".join(table)+"\n")
    accounting = [r"\begin{table*}[t]", r"\centering", r"\caption{" + prefix + r"Sample support at each stage. Only training is capped; no synthetic oversampling is used in the primary protocol.}",
                  r"\label{tab:data}", r"\begin{tabular}{lrrrrr}", r"\toprule", r"Class & Train before cap & Train used & Tune & Cal. & Test \\", r"\midrule"]
    s = manifest["split"]
    for name in manifest["classes"]:
        numbers = [s["train_before_cap"][name], s["train_after_cap"][name], *[s["counts"][p][name] for p in ("tune", "calibration", "test")]]
        accounting.append(tex_escape(name)+" & "+" & ".join(str(n) for n in numbers)+r" \\")
    accounting += [r"\bottomrule", r"\end{tabular}", r"\end{table*}"]
    (destination/"data_table.tex").write_text("\n".join(accounting)+"\n")
    write_json(destination/"source_manifest.json", {"experiment_id": manifest["experiment_id"], "readiness": status, "sources": manifest["sources"]})
    return status
