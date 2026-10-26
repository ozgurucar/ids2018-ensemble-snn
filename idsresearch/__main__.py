import argparse
from pathlib import Path
from .config import Config
from .data import audit, load
from .pipeline import prepare, train, score, summarize
from .provenance import write_json
from .reporting import export, readiness
from .synthetic import generate


def main():
    parser = argparse.ArgumentParser(description="Auditable IDS experiments; see docs/PLAN_TR.md")
    sub = parser.add_subparsers(dest="command", required=True)
    a = sub.add_parser("audit")
    a.add_argument("--data", required=True)
    a.add_argument("--timestamp-format", required=True)
    a.add_argument("--out", required=True)
    a = sub.add_parser("prepare")
    a.add_argument("--data", required=True)
    a.add_argument("--config", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--timestamp-format", required=True)
    a.add_argument("--time-review")
    for command in ("train", "evaluate"):
        a = sub.add_parser(command)
        a.add_argument("--experiment", required=True)
        a.add_argument("--models", nargs="+")
        a.add_argument("--seeds", nargs="+", type=int)
        a.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    for command in ("summarize", "check"):
        a = sub.add_parser(command)
        a.add_argument("--experiment", required=True)
    a = sub.add_parser("export")
    a.add_argument("--experiment", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--draft", action="store_true")
    a = sub.add_parser("profile")
    a.add_argument("--experiment", required=True)
    a.add_argument("--model", required=True)
    a.add_argument("--seed", required=True, type=int)
    a.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    a = sub.add_parser("compare")
    a.add_argument("--left", required=True)
    a.add_argument("--right", required=True)
    a.add_argument("--out", required=True)
    a = sub.add_parser("derive")
    a.add_argument("--parent", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--changes", required=True, help="JSON object of model-only config fields")
    a = sub.add_parser("smoke")
    a.add_argument("--out", required=True)
    a.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    args = parser.parse_args()
    if args.command == "audit":
        write_json(args.out, audit(load(args.data, args.timestamp_format)))
    elif args.command == "prepare":
        prepare(args.data, Config.read(args.config), args.out, args.timestamp_format, args.time_review)
    elif args.command == "train":
        train(args.experiment, args.models, args.seeds, args.device)
    elif args.command == "evaluate":
        score(args.experiment, args.models, args.seeds, args.device)
    elif args.command == "summarize":
        summarize(args.experiment)
    elif args.command == "check":
        report = readiness(args.experiment)
        write_json(Path(args.experiment)/"readiness.json", report)
        print(report)
        if report["blockers"]:
            raise SystemExit(2)
    elif args.command == "export":
        export(args.experiment, args.out, args.draft)
    elif args.command == "profile":
        from .profile import profile
        print(profile(args.experiment, args.model, args.seed, args.device))
    elif args.command == "derive":
        import json
        from .derive import derive
        print(derive(args.parent, args.out, json.loads(args.changes))["experiment_id"])
    elif args.command == "compare":
        from .comparison import compare
        compare(args.left, args.right, args.out)
    else:
        root = Path(args.out)
        data = generate(root/"synthetic_data")
        config = Config(provenance="synthetic", seeds=(42,), models=("esnn", "ann", "encoded_ann", "ann_ensemble", "cnn", "rf", "xgb", "catboost"),
                        hidden=(16, 8), steps=4, epochs=2, patience=2, batch_size=128,
                        train_cap=1000, rare_preserve=10, rf_trees=10, xgb_trees=10, catboost_trees=10, min_calibration_benign=2)
        experiment = root/"experiment"
        if not (experiment/"manifest.json").exists():
            prepare(data, config, experiment, "%Y-%m-%d %H:%M:%S")
        train(experiment, device=args.device)
        score(experiment, device=args.device)
        export(experiment, root/"draft_tables", draft=True)
        print("Smoke passed. These synthetic metrics must not be used in the manuscript.")


if __name__ == "__main__":
    main()
