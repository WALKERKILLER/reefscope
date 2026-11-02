"""Deterministic numeric ingest; raw paths/logs never enter shared reports.

Seven-part outline follows docs/mvp/12-training-report-and-benchmark.md,
which attributes YOLO Report Analyst (MIT). No external narrative is executed.
"""
import csv
import io
import json
import math
import hashlib
from pathlib import Path


METRICS = ("metrics/precision(B)", "metrics/recall(B)", "metrics/mAP50(B)", "metrics/mAP50-95(B)")
LOSSES = ("train/box_loss", "train/cls_loss", "train/dfl_loss", "val/box_loss", "val/cls_loss", "val/dfl_loss")
SAFE_ARGS = {"epochs", "batch", "imgsz", "seed", "deterministic", "lr0", "lrf", "momentum", "weight_decay", "warmup_epochs", "patience", "optimizer"}


def bounded_text(path, limit=10_000_000):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError("source_missing_or_too_large")
    with path.open("rb") as stream:
        data = stream.read(limit+1)
    if len(data)>limit:
        raise ValueError("source_missing_or_too_large")
    return data.decode("utf-8-sig"), hashlib.sha256(data).hexdigest()


def finite_number(value, name, probability=False):
    if isinstance(value, bool):
        raise ValueError(f"invalid_numeric_field:{name}")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid_numeric_field:{name}") from exc
    if not math.isfinite(number) or number < 0 or (probability and number > 1):
        raise ValueError(f"invalid_numeric_field:{name}")
    return number


def parse_csv(text):
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or len(reader.fieldnames) > 128:
        raise ValueError("invalid_csv_header")
    names = [name.strip() for name in reader.fieldnames]
    if len(set(names)) != len(names) or "epoch" not in names:
        raise ValueError("invalid_csv_header")
    rows, previous = [], 0
    for source in reader:
        if len(rows) >= 10000 or None in source:
            raise ValueError("invalid_csv_shape")
        source = {key.strip(): value for key, value in source.items()}
        epoch = finite_number(source["epoch"], "epoch")
        if not epoch.is_integer() or epoch <= previous:
            raise ValueError("epochs_not_strictly_increasing")
        row = {"epoch": int(epoch)}
        for name in (*METRICS, *LOSSES, "time"):
            value = source.get(name)
            row[name] = None if value in (None, "") else finite_number(value, name, name in METRICS)
        rows.append(row)
        previous = epoch
    return rows


def ingest(directory):
    root = Path(directory)
    hashes, missing, rows, args = {}, [], [], {}
    csv_path = root / "results.csv"
    if csv_path.exists():
        text, digest = bounded_text(csv_path)
        rows = parse_csv(text)
        hashes["results.csv"] = digest
    if not rows:
        missing.append("numeric_training_curves")
    args_path = root / "args.yaml"
    if args_path.exists():
        import yaml
        text, digest = bounded_text(args_path, 1_000_000)
        try:
            parsed = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise ValueError("invalid_training_args") from exc
        if not isinstance(parsed, dict):
            raise ValueError("invalid_training_args")
        for key in SAFE_ARGS & parsed.keys():
            value = parsed[key]
            if type(value) in (int, float):
                finite_number(value, key)
                args[key] = value
            elif type(value) is bool:
                args[key] = value
            elif key == "optimizer" and isinstance(value, str) and value in {"auto", "SGD", "Adam", "AdamW", "NAdam", "RAdam", "RMSProp", "MuSGD"}:
                args[key] = value
        hashes["args.yaml"] = digest
    else:
        missing.append("training_arguments")
    metadata_path = root / "run_metadata.json"
    fitness = None
    if metadata_path.exists():
        text, digest = bounded_text(metadata_path, 1_000_000)
        metadata = json.loads(text)
        if not isinstance(metadata, dict):
            raise ValueError("invalid_training_metadata")
        if metadata.get("best_fitness") is not None:
            fitness = finite_number(metadata["best_fitness"], "best_fitness", True)
        hashes["run_metadata.json"] = digest
    best = {}
    for name, key in ((METRICS[2], "best_map50_epoch"), (METRICS[3], "best_map50_95_epoch")):
        candidates = [r for r in rows if r[name] is not None]
        best[key] = max(candidates, key=lambda row: row[name])["epoch"] if candidates else None
    missing += ["training_dataset_hash", "framework_best_checkpoint_epoch"]
    warnings = ["训练与验证数值不是独立测试精度。", "框架 best 的保存依据独立记录，不假设为最高 mAP50 epoch。"]
    if any(row.get(name) == 0 for row in rows for name in LOSSES):
        warnings.append("存在零 loss，请复核原始训练记录与损失定义。")
    return {"schema":"fish-training-run/v1", "epochs":rows, "arguments":args, "selection":{
            **best, "last_epoch":rows[-1]["epoch"] if rows else None, "framework_best_fitness":fitness,
            "framework_best_checkpoint_epoch":None, "framework_selection_basis":"framework_recorded_fitness; checkpoint epoch unavailable"},
            "missing_inputs":missing, "warnings":warnings}, hashes
