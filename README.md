# 跨境电商 Multi-Agent 智能选品系统

**Cross-border E-commerce Multi-Agent Intelligent Product Selection System**

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
[![License MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![vLLM](https://img.shields.io/badge/Inference-vLLM-orange)](https://github.com/vllm-project/vllm)
[![MCP](https://img.shields.io/badge/Protocol-MCP-blue)](https://modelcontextprotocol.io)
[![CI](https://github.com/KeepMoving888/B2C_Selection_Agent/actions/workflows/ci.yml/badge.svg)](https://github.com/KeepMoving888/B2C_Selection_Agent/actions/workflows/ci.yml)

面向跨境电商企业的智能选品决策系统，通过 **Multi-Agent 协作 + 领域微调大模型 + 实时数据闭环**，将传统需要 1-2 周的市场调研、供应链评估、合规审查、利润测算、趋势预测流程压缩到 **5-15 分钟**。

## 核心能力

- **多 Agent 协作**：6 个专业 Agent（Orchestrator / Market Research / Supply Chain / Compliance / Profit Calculator / Trend Forecast）基于 Plan-and-Execute Loop 与 DAG 并行调度协同工作。
- **领域微调模型**：基于 Qwen2.5-7B 进行 QLoRA + ORPO 偏好对齐微调，再执行 AWQ INT4 量化，平衡效果与部署成本。
- **四层模型路由**：本地 AWQ INT4 → 本地 FP16 Merged → DeepSeek V4 Pro → DeepSeek V4 Flash，含健康检查与自动降级链。
- **RAG 知识增强**：基于历史选品报告与领域知识的向量检索，注入理解、规划、综合阶段。
- **飞书业务闭环**：消息 → 多维表格 → 审批 → 文档 → 知识库 → 群通知，形成可沉淀的选品决策工作流。
- **可观测性**：Prometheus + Grafana 三层监控（业务 / Agent / 基础设施），Docker Compose 一键部署。

## 快速开始

无需安装、无需 GPU，直接通过浏览器访问新版 React 前端：

- **Cloudflare Pages**: [https://b2c-selection-agent.pages.dev](https://b2c-selection-agent.pages.dev)
- **GitHub Pages**: [https://keepmoving888.github.io/B2C_Selection_Agent](https://keepmoving888.github.io/B2C_Selection_Agent)

> 说明：在线版本使用预置数据运行，用于产品功能展示与交互体验。生产部署（含 vLLM / Prometheus / Grafana）请使用 `docker-compose.prod.yml`。

### 本地启动前端

```bash
cd web
npm install
npm run dev
```

访问 `http://localhost:5173` 进入新版选品分析驾驶舱。

## 系统架构

系统采用 **Plan-and-Execute Loop + DAG 并行调度 + MCP 协议解耦工具** 的架构：

```
用户输入关键词
    │
    ▼
┌─────────────────┐    ┌──────────────────────────────────────────┐
│  Orchestrator   │───▶│  Market Research  │  Supply Chain       │
│  任务规划 + 路由 │    │  市场调研          │  供应链评估          │
└─────────────────┘    │  Compliance       │  Profit Calculator  │
    │                  │  合规审查          │  利润测算            │
    ▼                  │  Trend Forecast   │                     │
┌─────────────────┐    └──────────────────────────────────────────┘
│  Context        │                      │
│  Injector (RAG) │◀─────────────────────┘
└─────────────────┘
    │
    ▼
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│  Synthesize     │───▶│  Feishu Docx │───▶│  Wiki / Base │
│  结构化报告生成  │    │  审批与文档   │    │  知识库沉淀  │
└─────────────────┘    └──────────────┘    └─────────────┘
```

### 关键设计

- **6 个专业 Agent**：Orchestrator、Market Research、Supply Chain、Compliance、Profit Calculator、Trend Forecast，全部继承统一 BaseAgent 接口。
- **4 个 MCP Server**：Amazon 数据、供应链（1688/物流）、合规（FDA/专利/关税）、社媒趋势（Google Trends），支持多数据源热插拔。
- **DAG 并行执行**：基于依赖关系的子任务并行调度，含三层防死循环机制（步数/Token 预算/无进展检测）。
- **RAG 增强**：基于历史选品报告与领域知识的向量检索，注入 `_understand` / `_plan` / `_synthesize` 阶段。
- **飞书闭环**：消息 → 多维表格 → 审批 → 文档 → 知识库 → 群通知，完整业务闭环。

## 数据闭环

```
Google Trends 趋势
       ↓
Amazon 竞品搜索（价格 / 评分 / BSR / 销量估算）
       ↓
产品详情 + 评论分析（痛点 / 优点 / 迭代建议）
       ↓
供应链成本 + 合规审查 + 利润测算 + 季节性分析
       ↓
结构化选品报告 → 飞书审批 → 知识库沉淀
```

支持 **在线 API（Rainforest / Amazon PA API）** 与 **预置数据模式** 双数据源，可根据环境灵活选择。

## 前端分析页面

| 决策看板 | 市场分析 | 趋势季节 |
|---|---|---|
| ![dashboard](screenshots/demo-dashboard.png) | ![market](screenshots/demo-market-analysis.png) | ![trend](screenshots/demo-trend-seasonal.png) |

| 评论洞察 | 利润测算 | 供应商 |
|---|---|---|
| ![review](screenshots/demo-review-insights.png) | ![profit](screenshots/demo-profit-analysis.png) | ![suppliers](screenshots/demo-suppliers.png) |

| 合规检查 | 行动计划 | 报告中心 |
|---|---|---|
| ![compliance](screenshots/demo-compliance.png) | ![action](screenshots/demo-action-plan.png) | ![report](screenshots/demo-report-center.png) |

## 模型方案：ORPO 微调 + AWQ 量化

基于 Qwen2.5-7B 进行 QLoRA + ORPO 偏好对齐微调，再对合并后的 FP16 模型执行 AWQ INT4 量化，实现**领域效果提升**与**部署成本降低**的平衡。完整训练、量化与评测脚本见 [`finetune/`](finetune/)。

### 模型权重

| 模型 | 来源 | 用途 |
|---|---|---|
| Qwen2.5-7B | `Qwen/Qwen2.5-7B`（魔塔官方） | 微调基座 |
| qwen2.5-7b-ecommerce-merged | [keepzhe/qwen2.5-7b-ecommerce-merged](https://www.modelscope.cn/models/keepzhe/qwen2.5-7b-ecommerce-merged)（本项目） | ORPO 微调后 FP16 合并模型，优先使用 |
| qwen2.5-7b-ecommerce-awq-v3 | [keepzhe/qwen2.5-7b-ecommerce-awq-v3](https://www.modelscope.cn/models/keepzhe/qwen2.5-7b-ecommerce-awq-v3)（本项目） | 微调后 AWQ INT4 量化模型，显存受限时 fallback |

本地模型统一放置到 `E:/models/` 目录（已在 `config/settings.yaml` 中配置），避免重复线上下载。

### 微调效果（341 条垂直领域偏好对测试集）

| 模型 | 精度 | Accuracy | Avg Margin |
|------|------|:--------:|:----------:|
| Base（Qwen2.5-7B-Instruct） | FP16 | 100% | 0.9540 |
| Merged（QLoRA 合并后） | FP16 | 100% | 2.0886 |
| AWQ INT4（微调后量化） | INT4 | 100% | 1.9731 |

- Merged 相对 Base 的 Avg Margin 提升 **+118.9%**，验证 ORPO 微调对选品偏好对齐有效。
- AWQ 相对 Merged 仅损失 **0.1155** margin，量化对领域效果影响很小。

### 量化收益（AWQ INT4 模型）

| 指标 | Merged FP16 | AWQ INT4 | 收益 |
|------|-------------|----------|------|
| 模型体积 | 14.19 GB | 5.19 GB | **压缩 2.73x** |
| 单条推理延迟 | 7.874 s | 3.633 s | **降低 53.9%** |
| 推理显存占用 | 14.6 GB | 5.4 GB | **降低 63.2%** |
| 测试集 PPL | 1.491 | 1.606 | 质量损失 7.7%，可接受 |

## 部署方案

### 生产部署：完整推理栈

```bash
docker compose -f docker-compose.prod.yml up -d
```

启动 `vllm-ecommerce` + `vllm-base` + `agent-app` + `prometheus` + `grafana` 五服务编排。

生产部署核心要点：

1. **模型存储**：`E:/models/` 作为归档备份；推理前通过 `deploy/sync_models_to_wsl.sh` 同步到 WSL ext4，可将 5.2 GB AWQ 模型加载时间从 ~140 s（9P 协议）降到数十秒。
2. **推理服务**：优先使用 FP16 合并模型；显存受限时 fallback 到 AWQ INT4。
3. **API Gateway**：`deploy/api_gateway.py` 提供四层路由与统一 `/metrics`，Agent/前端只需将 base URL 指向 `http://127.0.0.1:8080/v1`。
4. **监控栈**：Prometheus + Grafana 覆盖业务 / Agent / 基础设施三层指标。
5. **模型校验**：部署前运行 `python scripts/verify_model_integrity.py` 检查模型完整性。

详细部署与 systemd 服务化步骤见 [`deploy/`](deploy/)。

### API Gateway 价值效果

| 维度 | 无 API Gateway | 有 API Gateway | 提升 |
|------|---------------|----------------|------|
| 服务可用性 | 85% | 99.5% | +14.5% |
| 每千次请求推理成本 | ¥12.0 | ¥2.1 | **降低 82%** |
| 故障切换 | 人工介入（分钟级） | 健康检查自动切换（~200 ms） | 自动 |
| 可观测性 | 基本无指标 | Prometheus + Grafana + 路由日志 | 可量化 |

## 工程可观测性

覆盖业务 / Agent / 基础设施三层核心指标：

| 层级 | 指标 | 含义 | 健康阈值 | 异常时操作 |
|------|------|------|---------|-----------|
| 业务 | `gateway_requests_total` | 各后端请求数与状态分布 | 错误率 < 5% | 检查后端健康 `/health` |
| 业务 | `gateway_request_duration_seconds` | 端到端延迟分布 | p99 < 60s | 排查排队或 GPU 满载 |
| 推理 | `vllm:time_to_first_token_seconds` | 首 token 时间（TTFT） | p99 < 10s | 检查请求排队或 prompt 过长 |
| 推理 | `vllm:gpu_cache_usage_perc` | KV Cache GPU 占用率 | < 90% | 调整显存分配或减少并发 |
| 推理 | `vllm:num_requests_waiting` | 排队请求数 | 不持续增长 | 扩容或限流 |

完整监控配置见 [`deploy/`](deploy/) 与 [`monitoring/`](monitoring/)。

## 单元测试与 CI

```bash
pytest tests/ -v
```

测试结果：

| 测试文件 | 用例数 | 结果 |
|---|---|---|
| tests/test_agent_loop.py | 14 | ✅ 全部通过 |
| tests/test_llm_client.py | 5 | ✅ 全部通过 |
| tests/test_monitoring.py | 5 | ✅ 全部通过 |
| tests/test_rag.py | 6 | ✅ 全部通过 |
| **合计** | **30** | **30 passed** |

CI 已通过 GitHub Actions 自动执行敏感词扫描、Ruff 检查、单元测试与 Docker 镜像构建。

## 项目成果与数据效果

| 维度 | 关键指标 | 效果 |
|---|---|---|
| 业务效率 | 选品分析周期 | 从 1-2 周压缩到 **5-15 分钟** |
| 推理成本 | 月度 API 成本（同等调用量） | 从约 ¥270 降至约 ¥45，**降低约 82%** |
| 模型微调 | 垂类偏好对齐 Avg Margin | 从 0.9540 提升至 **2.0886（+118.9%）** |
| 模型量化 | 体积 / 延迟 / 显存 | 压缩 **2.73x**，延迟降低 **53.9%**，显存降低 **63.2%** |
| 部署稳定性 | API Gateway 四层路由 | 可用性从 85% 提升至 **99.5%**，故障切换自动化 |
| 工程可观测性 | Prometheus + Grafana 三层监控 | 业务 / Agent / 基础设施指标全覆盖 |
| 工程质量 | 单元测试覆盖 | 30 个用例全部通过，Agent Loop / LLM Client / Monitoring / RAG 独立可测 |

## License

MIT
