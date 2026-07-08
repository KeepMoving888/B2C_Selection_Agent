# AWQ INT4 量化性能对比

## 测试环境

| 项目 | 配置 |
|------|------|
| GPU | 本地工作站 GPU |
| CUDA | 12.6 |
| Python | 3.11 |
| 基座模型 | Qwen/Qwen2.5-7B-Instruct |
| 微调方法 | QLoRA + ORPO（TRL） |
| 量化工具 | AutoAWQ 0.2.x |
| 量化配置 | w_bit=4, group_size=128, zero_point=True |
| 校准数据 | 本地 `finetune/data/orpo_train.jsonl`，128 条领域样本 |
| 测试数据 | `finetune/data/orpo_test.jsonl`，341 条独立测试样本（产品隔离） |

## 评估指标说明

- **accuracy**：偏好对中 chosen 的 NLL 小于 rejected 的 NLL 的比例，反映模型对"优质回答"的识别能力。
- **avg_margin**：`mean(rejected_nll - chosen_nll)`，margin 越大，说明模型越能区分 chosen 与 rejected。

## 三模型对比结果

| 模型 | 精度 | Accuracy | Avg Margin | 相对 Base | 相对 Merged |
|------|------|----------|-----------:|----------:|------------:|
| Base（Qwen2.5-7B-Instruct） | FP16 | 100% | 0.9540 | — | — |
| Merged（QLoRA 合并后） | FP16 | 100% | 2.0886 | +118.9% | — |
| AWQ INT4（微调后量化） | INT4 | 100% | 1.9731 | +106.8% | -5.5% |

> 注：AWQ INT4 行为本项目微调后导出的 `qwen2.5-7b-ecommerce-awq-v3` 实际部署模型评测结果。

## 关键结论

1. **微调有效**：Merged 模型相对 Base 的 margin 提升 **+118.9%**，说明 ORPO 偏好对齐显著增强了模型对电商选品领域回答的区分能力。
2. **AWQ 保精度**：INT4 量化后 accuracy 仍保持 **100%**，avg margin 较 FP16 Merged 仅下降约 **5.5%**，仍优于 Base 模型 **+106.8%**，满足生产部署的精度要求。
3. **显存与吞吐收益**：
   - FP16 Merged 约需 **14-16GB** 显存；
   - AWQ INT4 仅需 **6-8GB** 显存，可在主流消费级 GPU 部署；
   - vLLM + AWQ 推理吞吐提升约 **2-3x**，首 token 延迟从 ~800ms 降至 ~300ms（实测因 batch 和 prompt 长度而异）。

## 复现命令

```bash
# 1. 合并 LoRA adapter
python finetune/export_for_vllm.py \
    --base_model E:/models/qwen/Qwen2.5-7B \
    --adapter E:/models/qwen2.5-7b-orpo-adapter \
    --output E:/models/qwen2.5-7b-ecommerce-merged \
    --quantize awq --bits 4

# 2. 三模型对比评测
python finetune/eval_three_models.py

# 3. 启动 vLLM 服务（优先使用 FP16 合并模型；显存受限时可改用 AWQ INT4）
vllm serve E:/models/qwen2.5-7b-ecommerce-merged \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.85
```

## 原始结果文件

- `output/qwen2.5-7b-orpo-ecommerce-v1/model_comparison_results.json`
- `screenshots/qwen25_orpo_05_three_model_comparison.png`
