"""Deterministic reports, independent of evaluator metric computation.

Outline attribution: https://github.com/xiangshenchi/yolo-report-analyst (MIT),
research constraints: docs/mvp/12-training-report-and-benchmark.md.
"""
from copy import deepcopy
from html import escape
import json

TEMPLATE_VERSION = "reefscope-fish-report/v1"
SECTION_NAMES = ("配置与数据", "基线与最佳模型比较", "收敛分析", "类别混淆与困难样本", "推理性能", "诊断与实验建议", "局限与复现")


def value_text(value):
    if value is None:
        return "N/A"
    if isinstance(value, dict):
        return value_text(value.get("value"))
    if isinstance(value, float):
        return format(value, ".8g")
    return str(value)


def render_markdown(sections):
    parts = ["# 鱼类模型质量报告"]
    for index, section in enumerate(sections):
        parts.append(f"## {index+1}. {section['title']}")
        parts.extend(section["paragraphs"])
        if section["rows"]:
            parts.append("| 项目 | 记录值 |\n| --- | --- |\n" + "\n".join("| " + " | ".join(value_text(v).replace("|", "\\|").replace("\n", " ") for v in row) + " |" for row in section["rows"]))
        if section.get("evidence") is not None:
            parts.append("```json\n"+json.dumps(section["evidence"], ensure_ascii=False, indent=2, allow_nan=False)+"\n```")
    return "\n\n".join(parts)+"\n"


def render_html(sections):
    style = 'body{font:14px/1.7 system-ui,sans-serif;max-width:960px;margin:32px auto;padding:0 24px;color:#17212c}h1{font-size:26px}h2{font-size:19px;break-after:avoid}table{border-collapse:collapse;width:100%;margin:12px 0}th,td{text-align:left;padding:7px 12px;border-bottom:1px solid #ccd3db;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:11px/1.6 monospace}tr{break-inside:avoid}@media print{body{max-width:none;margin:0}h2{break-after:avoid}pre{font-size:9px}@page{size:A4;margin:16mm}}'
    parts = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>鱼类模型质量报告</title>',f'<style>{style}</style><h1>鱼类模型质量报告</h1>']
    for i, section in enumerate(sections):
        parts.append(f'<section><h2>{i+1}. {escape(section["title"])}</h2>')
        parts.extend(f'<p>{escape(p)}</p>' for p in section["paragraphs"])
        if section["rows"]:
            parts.append('<table><thead><tr><th>项目</th><th>记录值</th></tr></thead><tbody>')
            parts.extend('<tr>'+''.join(f'<td>{escape(value_text(v))}</td>' for v in row)+'</tr>' for row in section["rows"])
            parts.append('</tbody></table>')
        if section.get("evidence") is not None:
            parts.append('<pre>'+escape(json.dumps(section["evidence"],ensure_ascii=False,indent=2,allow_nan=False))+'</pre>')
        parts.append('</section>')
    return ''.join(parts)+'</html>'


def make_report(model, training=None, evaluation=None, baseline=None):
    if evaluation and evaluation.model_id != model.pk:
        raise ValueError("evaluation_model_mismatch")
    if training and training.model_id != model.pk:
        raise ValueError("training_model_mismatch")
    if baseline and not evaluation:
        raise ValueError("comparison_requires_evaluation")
    if baseline and (baseline.dataset_sha256 != evaluation.dataset_sha256 or baseline.protocol_id != evaluation.protocol_id or baseline.config != evaluation.config):
        raise ValueError("incomparable_evaluations")
    source = deepcopy(training.snapshot) if training else {"epochs":[], "selection":{}, "arguments":{}, "missing_inputs":["numeric_training_curves"], "warnings":[]}
    metrics = deepcopy(evaluation.metrics) if evaluation else {}
    missing = sorted(set(source["missing_inputs"] + (evaluation.missing_inputs if evaluation else ["independent_evaluation", "manual_identity_ground_truth", "frozen_test_dataset", "hardware_benchmark"])))
    facts = {
        "model_id":model.pk, "model_sha256":model.sha256, "training_run_id":str(training.pk) if training else None,
        "evaluation_run_id":str(evaluation.pk) if evaluation else None, "baseline_evaluation_id":str(baseline.pk) if baseline else None,
        "dataset_version":evaluation.dataset_version if evaluation else None, "dataset_sha256":evaluation.dataset_sha256 if evaluation else None,
        "protocol_id":evaluation.protocol_id if evaluation else None, "framework_version":model.framework_version,
        "source_hashes":training.source_hashes if training else {}, "human_review_status":"pending", "ai_enabled":False,
    }
    def section(index, paragraphs, rows=None, evidence=None):
        return {"title":SECTION_NAMES[index],"paragraphs":paragraphs,"rows":rows or [],"evidence":evidence}
    epochs, selection = source["epochs"], source["selection"]
    last = epochs[-1] if epochs else {}
    quality_rows = [[key, value] for key,value in metrics.items() if key not in {"benchmark","confusion_matrix","pr_curves","per_class"}]
    if not quality_rows:
        quality_rows = [["AP50 / AP50-95",None],["Precision / Recall / IDF1",None]]
    sections = [
        section(0,["报告只读取已冻结数值，不调用 AI，也不修改源训练或评估指标。", "训练配置仅保留允许公开的数值与优化器设置；数据路径和原始日志不进入报告。"],[["模型 ID",model.pk],["权重 SHA256",model.sha256],["框架版本",model.framework_version],["训练记录",facts["training_run_id"]],["独立评估",facts["evaluation_run_id"]]],source["arguments"]),
        section(1,["独立测试结果见下表。未提供独立 GT 时保持 N/A，验证集最优数值不填入本表。", "基线比较通过同数据 hash、同协议和同配置校验。" if baseline else "未提供可比基线；不报告提升幅度。"],quality_rows,deepcopy(baseline.metrics) if baseline else None),
        section(2,[f"读取 {len(epochs)} 个 epoch 的原始数值。" if epochs else "没有可解析训练曲线；可作为 zero-finetune 记录，不能从图片估算 loss 或精度。", "best_mAP50、best_mAP50-95 与框架实际 best 分别记录。框架 checkpoint epoch 缺失时不根据曲线反推。"],[["最后 epoch",selection.get("last_epoch")],["最高验证 mAP50 的 epoch",selection.get("best_map50_epoch")],["最高验证 mAP50-95 的 epoch",selection.get("best_map50_95_epoch")],["框架 best fitness",selection.get("framework_best_fitness")],["框架 best checkpoint epoch",selection.get("framework_best_checkpoint_epoch")]],{"first_epoch":epochs[0] if epochs else None,"last_epoch":last or None}),
        section(3,["混淆矩阵只使用评估器输出。困难样本需要人工审核，本报告不把训练拼图冒充独立测试样本。"],[["人工困难样本审核",None]],metrics.get("confusion_matrix")),
        section(4,["耗时必须注明固定设备、预热次数、输入尺寸及测量边界。逐阶段模型耗时不等于端到端播放 FPS。"],[["固定协议 benchmark","已提供" if metrics.get("benchmark") else None]],metrics.get("benchmark")),
        section(5,source["warnings"]+["建议补齐冻结测试集、逐类错误分析与人工 ID 真值，再判断模型适用范围。", "不依据单一 mAP 阈值给出科研可用或工业可用结论。"]),
        section(6,["报告待人工审阅。缺失项如下；保留它们是为了区分可运行、可评估与科学有效。", "训练曲线不能提供 IDF1/HOTA；无独立测试真值时，不给出模型泛化精度。"],[["缺失输入",", ".join(missing) or "无已知缺失"]],facts),
    ]
    payload = {"schema":"training-report/v1", "template_version":TEMPLATE_VERSION, **facts, "metrics":metrics,
               "missing_inputs":missing, "warnings":source["warnings"], "sections":sections,
               "training_curves":epochs, "checkpoint_selection":selection}
    return payload, render_markdown(sections), render_html(sections)
