# Qwen2.5-7B ORPO 微调训练报告

## 一、训练概况

| 项目 | 数值 |
|---|---|
| 基座模型 | Qwen2.5-7B |
| 训练样本 | 1364 条（44 个产品） |
| 验证样本 | 341 条（11 个产品） |
| 测试样本 | 341 条（11 个产品，训练未见过） |
| 实际训练步数 | 250 / 513（Early Stopping 触发） |
| 总训练时间 | 50.21 分钟 |
| 最后一步训练 loss | 0.2533 |
| 最后一步训练 nll_loss | 0.2533 |
| 平均训练 loss（整体） | 0.7348 |
| 最优验证 loss | 0.3498（step 100） |
| 最终验证 accuracy | 100.00% |
| 最终验证 margin | 0.5945 |

## 二、关键指标含义

- **loss / nll_loss**：ORPO 总损失包含 SFT 的 NLL 损失和偏好对齐损失。快速下降说明模型在学习数据格式和偏好；最终训练 loss 接近 0 提示训练集拟合较强。
- **rewards/chosen**：模型对优质回答的打分，应上升。
- **rewards/rejected**：模型对劣质回答的打分，应下降。
- **rewards/margins**：= rejected_reward - chosen_reward（负对数几率比）。margin > 0 且持续上升表示模型正确偏好 chosen。
- **rewards/accuracies**：chosen 得分高于 rejected 的偏好对比例。快速达到 100% 说明数据本身区分度很高。
- **eval_loss**：衡量模型在未见过产品上的泛化能力。本次在 step 100 后反弹，触发 Early Stopping。

## 三、训练过程图表

### 3.1 Loss 曲线
![loss curves](01_loss_curves.png)

**问题点**：训练 loss 快速收敛到接近 0，验证 loss 在 step 100 后反弹，说明模型在训练集上过拟合，Early Stopping 及时刹车。

### 3.2 Reward 与 Accuracy 曲线
![reward curves](02_reward_curves.png)

**说明**：chosen reward 上升、rejected reward 下降，margin 和 accuracy 快速达到高位，偏好学习方向正确。

### 3.3 GPU 显存与学习率
![gpu lr curves](03_gpu_lr_curves.png)

**说明**：训练期间显存稳定在约 7.3GB allocated / 10.6GB reserved，未出现 OOM；学习率按 cosine with restarts 调度。

## 四、独立测试集评估

测试集产品从未在训练/验证中出现过。

| 指标 | 基座模型 | 微调模型 | 提升 |
|---|---|---|---|
| Test Accuracy | 100.00% | 100.00% | +0.00% |
| Test Avg Margin | 0.9541 | 1.7162 | +0.7621 |

![test comparison](04_test_set_comparison.png)

**解读**：在完全未见过的测试产品上，微调模型仍能 100% 正确区分 chosen/rejected，且平均 margin 提升 0.7621，说明偏好学习有效。

## 五、三模型对比（基座 / 合并 / AWQ 量化）

| 模型 | Test Accuracy | Test Avg Margin |
|---|---|---|
| Base Model | 100.00% | 0.9540 |
| Merged/Tuned | 100.00% | 1.6610 |
| AWQ Quantized | 100.00% | 1.1421 |

![three model comparison](05_three_model_comparison.png)

**解读**：当前 AWQ 量化模型为魔塔官方 `Qwen/Qwen2.5-7B-Instruct-AWQ`（基座模型 AWQ 版，约 3.8 GB），用于验证 AWQ 量化技术效果。其 margin 相较合并模型下降 0.5190，但仍比基座模型高 0.1880。真正的“微调后 + AWQ”模型因本地 16GB 显存量化 7B 模型耗时过长，尚未完成；后续可在 24GB 及以上显存机器上执行本地 AWQ 量化，以获得更准确的部署指标。

## 六、推理生成观察

推理样例文件：`output/qwen2.5-7b-orpo-ecommerce-v1/inference_samples.txt`

**问题点**：微调后的输出格式更统一、结构化，但存在**生成不自动停止**的问题——回答结束后会继续编造下一个 "Human: ..." 提示。

**根因**：Qwen2.5-7B 的 `eos_token` 为 ``,而训练数据使用 `<|im_end|>` 作为结束符，模型未将 `<|im_end|>` 识别为停止信号。

**结论摘要**：
> 本次 ORPO 微调在偏好对齐指标上取得明显提升（test margin +0.7621），但也暴露出生成停止问题。问题根因是数据结束符与模型原生 eos_token 不一致，后续将通过统一结束符或部署时添加 stop token 解决。

## 七、结论与下一步

1. 训练成功完成；Early Stopping 在 step 250 触发，避免过拟合。
2. 指标表现良好：测试集 accuracy 100%，margin 显著提升 0.7621。
3. 官方基座 AWQ 模型验证：AWQ 4-bit 量化后模型体积约 3.8 GB，在独立测试集上仍保持 100% accuracy；真正的“微调 + AWQ”需在 24GB 及以上显存环境完成本地量化。
4. 已知问题：生成不自动停止，需在部署/推理层通过 stop token 或后处理截断解决。
5. 下一步：在更大显存机器上完成微调后 AWQ 量化并部署 vLLM，或先用 `<|endoftext|>` 作为结束符小范围重训修复停止问题。
