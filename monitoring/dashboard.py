# ============================================================
# monitoring/dashboard.py — 监控指标体系
#
# 三层监控金字塔：
# ┌─────────────────────────────────────────────────────────┐
# │ L1: 业务指标 (Business Metrics)                        │
# │   选品采纳率 / 上市成功率 / 分析周期缩短率 / ROI       │
# │   回答谁：老板 / 业务负责人                            │
# ├─────────────────────────────────────────────────────────┤
# │ L2: Agent 指标 (Agent Metrics)                         │
# │   任务成功率 / P95 延迟 / Replan 率 / Token 效率       │
# │   回答谁：AI 工程师 / 技术负责人                       │
# ├─────────────────────────────────────────────────────────┤
# │ L3: 基础设施指标 (Infra Metrics)                       │
# │   GPU 利用率 / 显存占用 / API 延迟 / 错误率            │
# │   回答谁：运维 / SRE                                   │
# └─────────────────────────────────────────────────────────┘
#

# ============================================================

from dataclasses import dataclass, field
from typing import Dict, List
import time
import json


# ── 指标定义 ─────────────────────────────────────────────

@dataclass
class BusinessMetrics:
    """L1: 业务指标 — 证明项目价值"""
    total_selection_tasks: int = 0
    approved_selections: int = 0          # 审批通过数
    selection_adoption_rate: float = 0.0  # 选品建议采纳率
    avg_selection_cycle_hours: float = 0  # 平均选品周期（小时）
    cycle_reduction_pct: float = 0.0      # 相比人工缩短百分比
    products_launched: int = 0            # 实际上线产品数
    first_month_success_rate: float = 0.0 # 首月成功率（ROI>0）
    cost_per_selection: float = 0.0       # 单次选品成本（含 API）
    monthly_api_cost_saved: float = 0.0   # 月度 API 费用节省

    def to_dict(self) -> Dict:
        return {
            "total_selection_tasks": self.total_selection_tasks,
            "selection_adoption_rate": f"{self.selection_adoption_rate:.1%}",
            "avg_selection_cycle": f"{self.avg_selection_cycle_hours:.1f}h",
            "cycle_reduction": f"{self.cycle_reduction_pct:.1%}",
            "products_launched": self.products_launched,
            "first_month_success_rate": f"{self.first_month_success_rate:.1%}",
            "cost_per_selection": f"¥{self.cost_per_selection:.2f}",
            "monthly_api_cost_saved": f"¥{self.monthly_api_cost_saved:.2f}",
        }


@dataclass
class AgentMetrics:
    """L2: Agent 指标 — 证明系统质量"""
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    task_success_rate: float = 0.0

    # 延迟
    p50_latency_seconds: float = 0.0
    p95_latency_seconds: float = 0.0
    p99_latency_seconds: float = 0.0
    latency_samples: List[float] = field(default_factory=list)

    # Agent 细节
    avg_steps_per_task: float = 0.0
    replan_rate: float = 0.0             # 触发 Replan 的比例
    avg_tokens_per_task: int = 0
    agent_success_breakdown: Dict[str, float] = field(default_factory=dict)

    # 模型路由
    premium_model_ratio: float = 0.0     # DeepSeek V4 使用占比
    local_model_ratio: float = 0.0       # Qwen3-8B 使用占比
    avg_latency_ms: float = 0.0

    # 检索
    retrieval_precision: float = 0.0     # RAG 检索精度
    retrieval_recall: float = 0.0
    avg_retrieval_latency_ms: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "total_runs": self.total_runs,
            "task_success_rate": f"{self.task_success_rate:.1%}",
            "latency_p50": f"{self.p50_latency_seconds:.2f}s",
            "latency_p95": f"{self.p95_latency_seconds:.2f}s",
            "latency_p99": f"{self.p99_latency_seconds:.2f}s",
            "avg_steps_per_task": f"{self.avg_steps_per_task:.1f}",
            "replan_rate": f"{self.replan_rate:.1%}",
            "avg_tokens_per_task": self.avg_tokens_per_task,
            "premium_model_ratio": f"{self.premium_model_ratio:.1%}",
            "local_model_ratio": f"{self.local_model_ratio:.1%}",
            "retrieval_precision": f"{self.retrieval_precision:.1%}",
            "retrieval_recall": f"{self.retrieval_recall:.1%}",
        }


@dataclass
class InfraMetrics:
    """L3: 基础设施指标"""
    gpu_utilization_pct: float = 0.0
    vram_used_gb: float = 0.0
    vram_total_gb: float = 16.0
    vllm_queue_depth: int = 0
    vllm_requests_per_second: float = 0.0
    deepseek_api_latency_p50_ms: float = 0.0
    deepseek_api_latency_p95_ms: float = 0.0
    deepseek_api_error_rate: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "gpu_utilization": f"{self.gpu_utilization_pct:.1f}%",
            "vram": f"{self.vram_used_gb:.1f}/{self.vram_total_gb:.1f}GB",
            "vllm_qps": f"{self.vllm_requests_per_second:.1f}",
            "vllm_queue_depth": self.vllm_queue_depth,
            "api_latency_p50": f"{self.deepseek_api_latency_p50_ms:.0f}ms",
            "api_error_rate": f"{self.deepseek_api_error_rate:.1%}",
        }


# ── 指标收集器 ───────────────────────────────────────────

class MetricsCollector:
    """
    统一指标收集器

    指标通过 Prometheus client 暴露 /metrics 端点，Grafana 拉取展示。
    本模块定义指标采集逻辑和 Grafana Dashboard 模板。
    """

    def __init__(self):
        self.business = BusinessMetrics()
        self.agent = AgentMetrics()
        self.infra = InfraMetrics()

    def record_task_completed(self, meta: Dict):
        """Agent 任务完成后记录指标"""
        self.agent.total_runs += 1
        if meta.get("agent_success_rate", 0) >= 0.9:
            self.agent.successful_runs += 1
        else:
            self.agent.failed_runs += 1

        latency = meta.get("total_time_seconds", 0)
        self.agent.latency_samples.append(latency)

        self.agent.avg_steps_per_task = (
            (self.agent.avg_steps_per_task * (self.agent.total_runs - 1)
             + meta.get("total_steps", 0)) / self.agent.total_runs
        )
        self.agent.replan_rate = (
            meta.get("replan_count", 0) / self.agent.total_runs
        )

    def compute_percentiles(self):
        """计算 P50/P95/P99（定期调用，如每小时）"""
        if not self.agent.latency_samples:
            return
        sorted_l = sorted(self.agent.latency_samples)
        n = len(sorted_l)
        self.agent.p50_latency_seconds = sorted_l[n // 2]
        self.agent.p95_latency_seconds = sorted_l[int(n * 0.95)]
        self.agent.p99_latency_seconds = sorted_l[int(n * 0.99)]
        self.agent.task_success_rate = (
            self.agent.successful_runs / max(self.agent.total_runs, 1)
        )

    def get_full_report(self) -> Dict:
        """生成完整监控报告"""
        self.compute_percentiles()
        return {
            "timestamp": time.time(),
            "business": self.business.to_dict(),
            "agent": self.agent.to_dict(),
            "infrastructure": self.infra.to_dict(),
        }


# ── Grafana Dashboard JSON（模板）──────────────────────

GRAFANA_DASHBOARD = {
    "title": "跨境电商选品 Agent 监控大盘",
    "panels": [
        {
            "title": "Agent 任务成功率 (24h)",
            "type": "stat",
            "targets": [{"expr": "agent_task_success_rate"}],
            "thresholds": [
                {"value": 0.9, "color": "green"},
                {"value": 0.8, "color": "yellow"},
                {"value": 0, "color": "red"},
            ],
        },
        {
            "title": "P95 延迟趋势 (7d)",
            "type": "graph",
            "targets": [{"expr": "histogram_quantile(0.95, agent_latency_seconds)"}],
            "alert": {"condition": "avg() > 480",  # 8min 告警
                       "message": "P95 延迟超过 8 分钟！"},
        },
        {
            "title": "Token 消耗趋势 (24h)",
            "type": "graph",
            "targets": [
                {"expr": "rate(agent_tokens_used_total[5m])", "legend": "Token/s"},
                {"expr": "agent_token_budget_remaining", "legend": "Budget"},
            ],
        },
        {
            "title": "模型路由分布 (24h)",
            "type": "piechart",
            "targets": [
                {"expr": "model_route_total{tier='premium'}", "legend": "DeepSeek V4"},
                {"expr": "model_route_total{tier='local'}", "legend": "Qwen3-8B"},
                {"expr": "model_route_total{tier='fallback'}", "legend": "Fallback"},
            ],
        },
        {
            "title": "GPU 显存使用",
            "type": "gauge",
            "targets": [{"expr": "vram_used_gb / vram_total_gb"}],
            "max": 1.0,
            "thresholds": [
                {"value": 0.85, "color": "red"},
                {"value": 0.7, "color": "yellow"},
                {"value": 0, "color": "green"},
            ],
        },
        {
            "title": "选品采纳率 & 首月成功率 (30d)",
            "type": "graph",
            "targets": [
                {"expr": "selection_adoption_rate", "legend": "采纳率"},
                {"expr": "first_month_success_rate", "legend": "首月成功率"},
            ],
        },
    ],
}

# ── 告警规则 ─────────────────────────────────────────────

ALERT_RULES = """
groups:
  - name: agent_alerts
    rules:
      # Agent 成功率告警
      - alert: AgentSuccessRateLow
        expr: agent_task_success_rate < 0.85
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "Agent 成功率低于 85%"
          description: "当前成功率 {{ $value | humanizePercentage }}，请检查错误日志"

      # P95 延迟告警
      - alert: AgentLatencyHigh
        expr: histogram_quantile(0.95, rate(agent_latency_seconds_bucket[5m])) > 480
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "P95 延迟超过 8 分钟"
          description: "当前 P95: {{ $value }}s，可能某个 Agent 卡住或 API 慢"

      # 死循环告警
      - alert: AgentLoopDetected
        expr: rate(agent_loop_detection_total[5m]) > 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "检测到 Agent 死循环"
          description: "{{ $value }} 次死循环，需要人工介入"

      # GPU 显存告警
      - alert: VRAMHighUsage
        expr: vram_used_gb / vram_total_gb > 0.9
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "GPU 显存使用率超过 90%"
          description: "当前 {{ $value | humanizePercentage }}，即将 OOM"

      # API 错误率告警
      - alert: APIErrorRateHigh
        expr: rate(deepseek_api_errors_total[5m]) / rate(deepseek_api_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "DeepSeek API 错误率超过 5%"
          description: "当前错误率 {{ $value | humanizePercentage }}，正在自动降级到本地模型"
"""
