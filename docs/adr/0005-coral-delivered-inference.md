# 0005：珊瑚推理沿用交付代码并在平台运行时执行

## Status
Proposed
Class: architecture

## Context and Problem Statement

组员交付了珊瑚白化分割权重 `coral_scs_enhanced_v2.safetensors`（`reef-coral-final/v1`）与单文件推理代码 `coral_model.py`。权重由冻结的 EPFL-ECEO CoralscapesV2 SegFormer-B5、新训练的非白化头和图像特征保护（guard）组成，输出 0 背景、1 非白化、2 白化。交付说明给出的验证环境是 Python 3.13、torch 2.14.1 + CUDA 12.6、Transformers 4.57.1、NumPy 2.5.4；平台后端与鱼类 Worker 使用 torch 2.5.1 + CUDA 12.4、NumPy 1.26.4。需要决定平台以什么方式执行这份模型，才能既保持交付数值语义，又沿用现有 Run、Worker 与产物校验，见 [珊瑚白化分析契约](../specs/draft-coral-bleaching-analysis.md)。

## Decision Drivers

- 掩膜语义与交付一致：类别聚合、guard 判定、裁块与阈值不能被平台改写。
- 沿用 [0003](0003-database-fish-worker.md) 的数据库队列、租约、重试和产物清单，不新增服务进程协议。
- 依赖最少：不为一个模型维护第二套 Python 环境或固定第二个 torch 版本。
- 来源可追溯：推理代码可逐字节对照交付包，上游模型与许可证有记录。

## Considered Options

- 将交付的 `coral_model.py` 原样纳入后端，在平台运行时中执行，并逐像素比较两种运行时的结果。
- 为珊瑚 Worker 单独建立交付验证环境（torch 2.14.1 等），通过子进程或独立服务调用。
- 按交付权重结构在平台内重新实现推理。

## Decision Outcome

选择第一项。`backend/app/analysis/vendor/coral_model.py` 与交付文件逐字节一致（SHA-256 记录在同目录 README），适配器只负责解码、采样、写掩膜和统计，不改动推理路径。后端依赖增加交付要求的 Transformers 4.57.1 与 safetensors 0.8.0，torch 保持平台版本。交付代码在构建模型时把 torch 线程数设为 6 并关闭 TF32，这些是进程级设置，因此 Worker 用 `--kind` 区分鱼类与珊瑚进程，避免影响鱼类追踪。CUDA 支持 BF16 时使用交付验证的 BF16，否则用 FP32，并在摘要中记录。

本地证据（RTX 4060 Laptop，授权视频 30 个采样帧，4K）：

- 适配器掩膜与同一运行时下交付命令行的输出逐像素一致（0 个像素不同）。
- 平台运行时（torch 2.5.1+cu124）与交付验证运行时（torch 2.14.1+cu126）在相同帧上：248,832,000 个像素中 49,164 个不同（0.0198%），全部发生在背景与非白化之间，单帧最多 2,811 个；30 帧的 guard 判定与分数一致；非白化像素总数相差 0.006%。这段视频没有白化预测，白化类在两种运行时下的一致性未经本地检验。
- 每个采样帧约 0.8–0.97 s，峰值显存约 1.3 GB。

## Pros and Cons of the Options

原样纳入交付代码让数值路径与交付一致，并沿用现有 Worker 与产物校验，代价是 BF16 卷积在不同 torch/CUDA 版本间存在边界像素差异，且交付代码的进程级设置要求按 kind 分开 Worker。单独的交付验证环境能复现交付数值，但需要第二套约 6.5 GB 的 Python 环境、跨进程传递帧与错误码，以及另一套依赖升级流程；在测得差异只有 0.02% 边界像素、guard 判定不变时，这些成本不值得。重新实现可以去掉进程级设置，但会复制类别聚合与 guard 逻辑，任何细微偏差都会让交付证据不再适用，且难以审查。若后续出现白化类的跨运行时差异或 guard 判定翻转，应重新评估第二项。

## Links

- [EPFL-ECEO/segformer-b5-finetuned-coralscapesv2-1024-1024-95_class](https://huggingface.co/EPFL-ECEO/segformer-b5-finetuned-coralscapesv2-1024-1024-95_class/tree/a81205e666767b8602c6e7ad8da69b1e013bafdd)，交付使用的上游 revision，Apache-2.0。
- [CoralscapesV2: Panoptic and Fine-Grained Visual Scene Understanding in Coral Reefs](https://arxiv.org/abs/2609.12826)，上游模型的训练数据集；首版数据集见 [arXiv:2503.20000](https://arxiv.org/abs/2503.20000)。
- [safetensors 格式说明](https://huggingface.co/docs/safetensors/index)：文件头为 JSON，注册时无需反序列化 pickle 即可校验。
- [Transformers SegFormer 文档](https://huggingface.co/docs/transformers/model_doc/segformer)。
- [珊瑚白化分析契约](../specs/draft-coral-bleaching-analysis.md)。
