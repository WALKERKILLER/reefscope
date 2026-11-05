"""Deterministic coral training report; same seven-part outline as the fish report.

Chapter order follows docs/mvp/12-training-report-and-benchmark.md. Every number comes from a
coral-training-run/v1 snapshot; text only states what those numbers can and cannot support.
"""
from copy import deepcopy

from app.analysis.reports import render_html, render_markdown

TEMPLATE_VERSION = "reefscope-coral-report/v1"
TITLE = "珊瑚模型质量报告"
SECTION_NAMES = ("配置与数据", "基线与最佳模型比较", "收敛分析", "类别与场景分组误差", "推理性能与导出一致性", "诊断与实验建议", "局限与复现")


def pct(value):
    return None if value is None else f"{value * 100:.2f}%"


def change(before, after):
    return None if before is None or after is None else f"{pct(before)} → {pct(after)}"


def pair(scores):
    return f"{pct(scores['precision'])} / {pct(scores['recall'])}"


def yes(value):
    return "是" if value else "否"


def make_coral_report(model, training):
    if training.model_id != model.pk:
        raise ValueError("training_model_mismatch")
    source = deepcopy(training.snapshot)
    if source.get("schema") != "coral-training-run/v1":
        raise ValueError("not_a_coral_training_run")
    epochs, selection, args, data = source["epochs"], source["selection"], source["arguments"], source["data"]
    validation, guard, recheck, export, lineage = source["validation"], source["guard"], source["regression_recheck"], source["export"], source["lineage"]
    missing = sorted(set(source["missing_inputs"] + ["independent_evaluation"]))
    facts = {"model_id": model.pk, "model_sha256": model.sha256, "training_run_id": str(training.pk), "evaluation_run_id": None,
             "baseline_evaluation_id": None, "dataset_version": None, "dataset_sha256": None, "protocol_id": None,
             "framework_version": model.framework_version, "source_hashes": training.source_hashes, "lineage": lineage,
             "human_review_status": "pending", "ai_enabled": False}
    best = next(row for row in epochs if row["epoch"] == selection["best_epoch"])
    first, last = epochs[0], epochs[-1]
    local, official = recheck["domains"]["local"], recheck["domains"]["official"]
    lb, la = local["full_image"]["baseline"]["1"], local["full_image"]["adapted"]["1"]
    vb, vs = validation["baseline"], validation["selected"]
    frames, groups, counts = data["local_split_frames"], data["local_split_groups"], data["official_split_counts"]
    tail = epochs[len(epochs) // 2:]
    fixed = [row for row in epochs if row["val/iou@0.5"] is not None]
    per_image = recheck["local_per_image_iou_change"]

    def section(index, paragraphs, rows=None, evidence=None):
        return {"title": SECTION_NAMES[index], "paragraphs": paragraphs, "rows": rows or [], "evidence": evidence}

    sections = [
        section(0, ["冻结 CoralscapesV2 SegFormer-B5 底模，只训练新增的未白化分割分支；白化类直接来自冻结底模。",
                    f"本地数据按 {len(data['scene_groups'])} 个场景组划分：训练 {groups['train']} 组 {frames['train']} 帧，验证 {groups['val']} 组 {frames['val']} 帧，测试 {groups['test']} 组 {frames['test']} 帧。同一场景组的帧不跨划分。",
                    f"训练同时回放 CoralscapesV2 官方训练图 {data['official_replay_images']} 张；官方验证 {counts['val']} 张、测试 {counts['test']} 张。",
                    "报告只读取导入时校验过的数值与摘要，不保存数据路径、设备名称或原始日志，也不调用 AI。"],
                [["模型 ID", model.pk], ["权重 SHA256", model.sha256], ["训练适配器 SHA256", lineage["adapter_sha256"]], ["冻结底模指纹", lineage["frozen_base_sha256"]],
                 ["底模权重未改变", yes(lineage["base_unchanged"])], ["训练记录", facts["training_run_id"]],
                 ["epoch × 每轮 batch", f"{args['epochs']} × {args['steps']}"], ["batch / 裁剪尺寸", f"{args['batch']} / {args['crop']} px"],
                 ["学习率", args["lr"]], ["seed", args["seed"]], ["官方数据 revision / 许可", f"{data['official_revision']} / {data['official_license']}"]],
                {"arguments": args, "data": data}),
        section(1, [f"选定模型与冻结基线在同一本地验证集（{data['local_validation_images']} 帧）上按像素统计未白化类；官方验证 {data['official_validation_images']} 张预测{'逐像素不变' if validation['official_validation_unchanged'] else '有变化'}。",
                    "测试数值来自 v2 回归复核：这些测试图在 v1 已被查看，不是全新独立测试，只能说明修订没有退化，不能作为泛化精度。",
                    "本地测试集没有白化真值，白化识别精度保持 N/A；官方测试的白化类数值属于冻结底模。"],
                [["验证 未白化 IoU（基线 → 选定）", change(vb["iou"], vs["iou"])], ["验证 未白化 F1", change(vb["f1"], vs["f1"])],
                 ["验证 Precision / Recall", f"{pair(vb)} → {pair(vs)}"],
                 [f"本地测试 {local['images']} 张 未白化 IoU（回归复核）", change(lb["iou"], la["iou"])], ["本地测试 未白化 F1", change(lb["f1"], la["f1"])],
                 ["本地测试 Precision / Recall", f"{pair(lb)} → {pair(la)}"],
                 ["本地测试 逐图 IoU 变化", f"改善 {per_image['improved']} · 不变 {per_image['unchanged']} · 变差 {per_image['worse']}"],
                 [f"官方测试 {official['images']} 张 预测变化像素", official["changed_pixels"]],
                 ["官方测试 白化 IoU（底模，未改变）", pct(official["full_image"]["adapted"]["2"]["iou"])],
                 ["本地白化识别精度", None], ["独立测试精度", None]],
                recheck),
        section(2, [f"读取 {len(epochs)} 个 epoch。训练 loss 是每轮 {args['steps']} 个采样 batch 的均值，从 {first['train/loss']:.4f} 降到 {last['train/loss']:.4f}。",
                    f"每轮在本地验证集上扫描 {len(args['threshold_candidates'])} 个阈值，取未白化 IoU 最高者；选定 epoch {selection['best_epoch']}（阈值 {selection['best_threshold']}）是验证 IoU 最高的轮次。",
                    f"后 {len(tail)} 轮验证 IoU 在 {pct(min(r['val/iou'] for r in tail))} 至 {pct(max(r['val/iou'] for r in tail))} 之间。"
                    + ("选定 epoch 是最后一轮，12 轮内未见明确饱和；是否继续训练需另做实验。" if selection["best_epoch"] == selection["last_epoch"] else "选定 epoch 早于最后一轮。"),
                    "没有记录验证 loss 与逐 step loss；曲线不从图片或终端片段补算。"],
                [["最后 epoch", selection["last_epoch"]], ["选定 epoch", selection["best_epoch"]], ["选定阈值", selection["best_threshold"]],
                 ["选定 epoch 验证 IoU / F1", f"{pct(best['val/iou'])} / {pct(best['val/f1'])}"],
                 ["固定阈值 0.5 验证 IoU 最高的 epoch", max(fixed, key=lambda r: r["val/iou@0.5"])["epoch"] if fixed else None],
                 ["训练 loss（首轮 → 末轮）", f"{first['train/loss']:.6f} → {last['train/loss']:.6f}"], ["验证 loss", None],
                 ["训练进程总耗时（含逐轮验证）", f"{source['elapsed_seconds']:.1f} s"]],
                {"first_epoch": first, "selected_epoch": best, "last_epoch": last}),
        section(3, [f"只有未白化类经过训练；白化类在两个测试域上的变化像素合计 {local['bleached_changed_pixels'] + official['bleached_changed_pixels']}。",
                    "场景分组误差按验证组统计；组数少，不能代表海域总体。困难样本未经人工审核。"],
                [*[[f"验证组 {g['group']} IoU（基线 → 选定）", change(g["baseline"]["iou"], g["adapted"]["iou"])] for g in validation["groups"]],
                 ["本地测试 guard 启用", f"{local['guard_active_images']} / {local['images']}"], ["官方测试 guard 启用", f"{official['guard_active_images']} / {official['images']}"],
                 [f"官方训练审计 {recheck['official_train_audit']['images']} 张 变化像素", recheck["official_train_audit"]["changed_pixels"]],
                 ["人工困难样本审核", None]],
                validation["groups"]),
        section(4, [f"单文件权重共 {export['tensor_count']} 个张量（底模 {export['base_tensors']}，训练分支 {export['trained_head_tensors']}），与训练适配器逐值{'一致' if export['all_tensor_values_equal'] else '不一致'}。",
                    f"{export['images_compared']} 张实际图片的预测与训练产物{'逐像素相同' if export['predictions_identical'] else '存在差异'}，{'覆盖' if export['both_guard_branches_exercised'] else '未覆盖'} guard 两个分支。",
                    "未提供固定设备 benchmark，耗时与 FPS 保持 N/A。平台运行时与交付运行时的像素差异见珊瑚分析文档。"],
                [["权重字节数", export["bytes"]], ["需要其他权重文件", yes(export["requires_other_weight_files"])], ["命令行预测逐像素一致", yes(export["cli_identical"])],
                 ["guard 阈值", guard["threshold"]], ["guard 校准使用测试集", yes(guard["test_used_for_calibration"])], ["固定协议 benchmark", None]],
                {"export": export, "guard": guard}),
        section(5, source["warnings"]
                + ([f"本地测试 Recall 从 {pct(lb['recall'])} 降到 {pct(la['recall'])}：误检减少的同时漏检增加，监测场景需评估漏检代价。"] if la["recall"] < lb["recall"] else [])
                + [f"guard 在本地验证 {guard['local_validation_active']}/{guard['local_validation_images']} 帧启用、官方验证 {guard['official_validation_active']}/{guard['official_validation_images']} 张启用，实际按画面域分流；新海域视频需检查 guard 分数分布。",
                   "建议补充未查看过的本地场景组作为冻结测试集并标注白化真值，同时记录验证 loss 与逐 step loss。",
                   "不依据单一 IoU 阈值给出科研可用或工业可用结论。"]),
        section(6, ["报告待人工审阅。缺失项如下；保留它们是为了区分可运行、可评估与科学有效。",
                    "复现需要原始图片、人工标注、数据清单与原始模型，训练日志包不含这些文件。"],
                [["缺失输入", ", ".join(missing)], ["校验过的来源文件", len(training.source_hashes)]], facts),
    ]
    payload = {"schema": "training-report/v1", "template_version": TEMPLATE_VERSION, "model_kind": "coral", **facts, "metrics": {},
               "missing_inputs": missing, "warnings": source["warnings"], "sections": sections, "training_curves": epochs,
               "checkpoint_selection": selection, "coral": {"validation": validation, "local_recheck": {"images": local["images"], "baseline": lb, "adapted": la}}}
    return payload, render_markdown(sections, TITLE), render_html(sections, TITLE)
