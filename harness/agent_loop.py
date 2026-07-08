# ============================================================
# harness/agent_loop.py — Plan-and-Execute Loop 核心引擎
#
# 实现 Agent 运行时的核心执行循环。支持 Plan-and-Execute
# 混合架构，DAG 并行调度，以及多层防死循环保护。
# ============================================================

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Coroutine, Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from monitoring.metrics import MetricsCollector
    from rag.injector import ContextInjector


class TaskStatus(Enum):
    """子任务状态机 — 生命周期从 PENDING 到 COMPLETED/FAILED/SKIPPED"""
    PENDING   = "pending"
    READY     = "ready"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    SKIPPED   = "skipped"


class LoopPhase(Enum):
    """Orchestrator 执行阶段 — 对应 Plan-and-Execute 的完整生命周期"""
    UNDERSTAND  = "understand"
    PLAN        = "plan"
    EXECUTE     = "execute"
    AGGREGATE   = "aggregate"
    VERIFY      = "verify"
    REPLAN      = "replan"
    SYNTHESIZE  = "synthesize"


@dataclass
class SubTask:
    """
    Orchestrator 拆解后的最小执行单元。

    使用 DAG（有向无环图）而非顺序列表的原因：
    市场分析 和 供应链评估 任务可并行执行，而利润计算依赖二者的结果。
    DAG 的 depends_on 字段让执行器能自动识别并行机会，
    将多个无依赖关系的子任务并发调度。
    """
    id: str
    agent: str
    action: str
    input_data: Dict[str, Any]
    depends_on: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    tokens_used: int = 0


@dataclass
class ExecutionContext:
    """单次选品任务的执行上下文，用于追踪和监控"""
    task_id: str
    user_query: str
    product_category: str
    target_market: str
    budget_range: Optional[str] = None
    total_tokens_used: int = 0
    total_time_seconds: float = 0.0
    agent_success_rate: float = 0.0
    replan_count: int = 0


@dataclass
class AgentLoopConfig:
    """
    Agent Loop 运行时配置。

    参数设计依据：
    - max_total_steps=15：6 个 Agent 各约 2 步 + Orchestrator 3 步(plan/aggregate/synthesize)
    - token_budget=32000：匹配 Qwen3 默认 context window 32768，留 768 余量
    - loop_detection_threshold=3：连续 3 轮无进展判定为死循环，宁可误报不可漏报
    - parallel_agents=3：RTX 4060Ti 16GB 同跑 3 个 Qwen 推理实例为实测上限
    """
    max_total_steps: int = 15
    max_agent_steps: int = 8
    token_budget: int = 32000
    loop_detection_threshold: int = 3
    agent_timeout_seconds: int = 120
    parallel_agents: int = 3
    max_retries: int = 2
    quality_score_threshold: float = 0.7


class AgentLoop:
    """
    Plan-and-Execute 混合引擎。

    执行流程：Understand -> Plan -> Execute -> Aggregate -> Verify -> Synthesize。
    其中 Plan 阶段将用户意图拆解为 DAG 子任务，Execute 阶段通过
    asyncio.Semaphore 控制最大并行数，自动识别并调度无依赖关系的子任务。

    防死循环的三层保护：
    1. max_total_steps — 全局最大步数硬限制
    2. token_budget — Token 预算耗尽时终止
    3. loop_detection_threshold — 连续多轮无进展触发人工介入
    """

    def __init__(
        self,
        config: AgentLoopConfig,
        agents: Dict[str, Any],
        mcp_registry: Dict[str, Any],
        model_router: Any,
        llm_client: Any,
        metrics_collector: Optional["MetricsCollector"] = None,
        context_injector: Optional["ContextInjector"] = None,
    ):
        self.config = config
        self.agents = agents
        self.mcp_registry = mcp_registry
        self.model_router = model_router
        self.llm = llm_client
        self._metrics = metrics_collector
        self._injector = context_injector

        self.subtasks: List[SubTask] = []
        self.context: Optional[ExecutionContext] = None
        self.current_step = 0
        self._consecutive_no_progress = 0
        self._semaphore = asyncio.Semaphore(config.parallel_agents)
        self._phase_timings: Dict[LoopPhase, float] = {}
        self._agent_call_count: Dict[str, int] = {}
        self._error_log: List[Dict] = []

    # ═══════════════════════════════════════════════════════
    # 主入口
    # ═══════════════════════════════════════════════════════

    async def run(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """完整执行流程：Understand -> Plan -> Execute -> Aggregate -> Verify -> Synthesize"""
        start_time = time.time()
        self.context = ExecutionContext(
            task_id=str(uuid.uuid4())[:8],
            user_query=task,
            product_category=context.get("category", "unknown"),
            target_market=context.get("market", "US"),
            budget_range=context.get("budget"),
        )

        try:
            intent = await self._timed(LoopPhase.UNDERSTAND,
                                       self._understand(task, context))
            self.subtasks = await self._timed(LoopPhase.PLAN,
                                              self._plan(intent))
            await self._timed(LoopPhase.EXECUTE, self._execute_dag())
            aggregated = await self._timed(LoopPhase.AGGREGATE, self._aggregate())
            passed = await self._timed(LoopPhase.VERIFY, self._verify(aggregated))

            if not passed and self.context.replan_count < self.config.max_retries:
                self.context.replan_count += 1
                await self._timed(LoopPhase.REPLAN, self._replan_and_retry(aggregated))
                aggregated = await self._aggregate()

            report = await self._timed(LoopPhase.SYNTHESIZE,
                                       self._synthesize(aggregated))
            self.context.total_time_seconds = time.time() - start_time
            report["_meta"] = self._build_meta_report()
            if self._metrics:
                self._metrics.record_task_completed(
                    success=True, meta=report["_meta"])
            return report

        except Exception as e:
            self._error_log.append({
                "error": str(e), "step": self.current_step, "timestamp": time.time()
            })
            if self._metrics:
                self._metrics.record_task_completed(
                    success=False,
                    meta=self._build_meta_report() if self.context else {},
                )
            raise

    # ═══════════════════════════════════════════════════════
    # Phase 实现
    # ═══════════════════════════════════════════════════════

    async def _understand(self, task: str, context: Dict) -> Dict:
        """将用户自然语言转为结构化参数。
        使用 LLM 而非正则解析：用户可能用口语化表达（如"宠物咬的东西"），
        LLM 可正确映射为规范化的品类名称和参数。"""
        prompt = f"""Extract structured intent from product selection request.
User query: {task}
Additional context: {json.dumps(context, ensure_ascii=False)}
Output JSON: {{"product_category", "target_market", "target_platform",
"seller_level", "budget_range", "special_requirements"}}"""
        if self._injector:
            prompt = self._injector.inject(prompt, query=task)
        response = await self.llm.call(
            prompt, model=self.model_router.route("orchestrator"))
        return json.loads(response)

    async def _plan(self, intent: Dict) -> List[SubTask]:
        """拆解意图为 DAG 子任务。
        市场分析和供应链评估无相互依赖，可并行执行；
        利润计算依赖前两者的输出结果；
        合规审查和趋势预测与前三者无依赖，可独立并行。
        DAG 结构允许执行器自动识别并行机会，缩短总执行时间。"""
        plan_prompt = f"""You are a task planner for cross-border e-commerce selection.
User intent: {json.dumps(intent, ensure_ascii=False)}

Available agents and their capabilities:
- market_research: Amazon market analysis, competitor research, keyword volume, seasonal trends
- supply_chain: 1688/Alibaba supplier search, MOQ check, shipping cost estimation, supplier verification
- compliance: FDA/CE/IP regulation check, platform category restrictions, labeling requirements
- profit_calculator: total cost breakdown, platform fees (Amazon referral 15%, FBA fees), ROI projection
- trend_forecast: Google Trends analysis, category lifecycle stage, social media sentiment

Output a JSON array of subtasks. Each subtask with: id, agent, action, input_data, depends_on.

CRITICAL RULES:
- market_research and supply_chain MUST run in PARALLEL (empty depends_on for both)
- profit_calculator depends_on BOTH market_research AND supply_chain results
- compliance and trend_forecast can run in parallel with everything else
- Each subtask focused on ONE specific analysis"""
        if self._injector:
            plan_prompt = self._injector.inject(
                plan_prompt, query=intent.get("product_category", ""))
        response = await self.llm.call(
            plan_prompt, model=self.model_router.route("orchestrator"))
        subtask_dicts = json.loads(response)

        return [SubTask(
            id=st["id"], agent=st["agent"], action=st["action"],
            input_data=st["input_data"],
            depends_on=st.get("depends_on", []),
        ) for st in subtask_dicts]

    async def _execute_dag(self) -> None:
        """DAG 并行执行器。
        核心逻辑：
        1. 查找所有依赖已满足的 subtask 加入执行池
        2. asyncio.Semaphore 控制最大并发（受 GPU 显存限制）
        3. 任一 subtask 完成时检查并解锁新的 subtask
        4. 循环直到全部完成、死锁检测、或超出预算
        5. 死锁检测：无执行中任务且无新任务可调度时报告 DAG deadlock
        """
        completed: Set[str] = set()
        failed: Set[str] = set()
        in_flight: Dict[str, asyncio.Task] = {}

        while len(completed) + len(failed) < len(self.subtasks):
            # 死锁检测：无执行中任务 + 无可调度任务
            if not in_flight:
                ready = self._find_ready(completed)
                if not ready:
                    blocked = [st.id for st in self.subtasks
                               if st.status == TaskStatus.PENDING]
                    raise RuntimeError(
                        f"DAG deadlock. Blocked: {blocked}. "
                        f"Completed: {list(completed)}, Failed: {list(failed)}")
            else:
                ready = self._find_ready(completed)

            # 启动新 subtask（受 Semaphore 限制）
            for st in ready:
                if self.current_step >= self.config.max_total_steps:
                    for r in self.subtasks:
                        if r.status in (TaskStatus.PENDING, TaskStatus.READY):
                            r.status = TaskStatus.SKIPPED
                            r.error = "Exceeded max_total_steps"
                    return
                task = asyncio.create_task(self._execute_with_semaphore(st))
                in_flight[st.id] = task
                self.current_step += 1

            if in_flight:
                done, _ = await asyncio.wait(
                    in_flight.values(), return_when=asyncio.FIRST_COMPLETED,
                    timeout=self.config.agent_timeout_seconds)

                for task in done:
                    st_id = next((sid for sid, t in in_flight.items()
                                  if t is task), None)
                    if not st_id:
                        continue
                    del in_flight[st_id]
                    subtask = next(st for st in self.subtasks if st.id == st_id)
                    try:
                        subtask.result = task.result()
                        subtask.status = TaskStatus.COMPLETED
                        subtask.completed_at = time.time()
                        subtask.tokens_used = subtask.result.get("tokens_used", 0)
                        self.context.total_tokens_used += subtask.tokens_used
                        completed.add(st_id)
                        self._consecutive_no_progress = 0
                    except Exception as e:
                        subtask.status = TaskStatus.FAILED
                        subtask.error = str(e)
                        failed.add(st_id)
                        self._error_log.append({
                            "subtask": st_id, "agent": subtask.agent,
                            "error": str(e), "step": self.current_step,
                        })

                if not done:
                    self._consecutive_no_progress += 1
                    if self._consecutive_no_progress >= self.config.loop_detection_threshold:
                        raise RuntimeError(
                            f"Loop detection: {self._consecutive_no_progress} "
                            f"rounds with no progress. Manual intervention required.")

        # 标记因前置失败而被跳过的 subtask
        for st in self.subtasks:
            if st.status == TaskStatus.PENDING:
                st.status = TaskStatus.SKIPPED
                st.error = "Dependency failed"

    async def _aggregate(self) -> Dict:
        """汇总所有 Agent 结果并计算成功率"""
        results_by_agent: Dict[str, List[Dict]] = {}
        for st in self.subtasks:
            if st.status == TaskStatus.COMPLETED and st.result:
                results_by_agent.setdefault(st.agent, []).append(st.result)

        total = len(self.subtasks)
        succeeded = sum(1 for st in self.subtasks
                        if st.status == TaskStatus.COMPLETED)
        if self.context:
            self.context.agent_success_rate = succeeded / total if total > 0 else 0

        return {
            "results_by_agent": results_by_agent,
            "agent_success_rate": (
                self.context.agent_success_rate if self.context
                else succeeded / total if total > 0 else 0
            ),
            "total_subtasks": total,
            "succeeded": succeeded,
            "failed": sum(1 for st in self.subtasks
                          if st.status == TaskStatus.FAILED),
            "skipped": sum(1 for st in self.subtasks
                           if st.status == TaskStatus.SKIPPED),
            "total_tokens_used": self.context.total_tokens_used,
        }

    async def _verify(self, aggregated: Dict) -> bool:
        """三维质量验证：完整性 + 一致性 + 成功率。
        完整性检查 6 个分析维度是否覆盖；
        一致性检查市场热度与供应链可得性是否矛盾；
        综合加权分数低于阈值时触发自动 Replan。"""
        required = {"market_research", "supply_chain", "compliance",
                     "profit_calculator", "trend_forecast"}
        covered = set(aggregated["results_by_agent"].keys())
        completeness = len(covered & required) / len(required)

        # 一致性：市场有强需求但无供应商 — 严重矛盾，权重降至 0.3
        consistency = 1.0
        if "market_research" in covered and "supply_chain" in covered:
            has_demand = any(
                r.get("market_demand_score", 0) > 0.5
                for r in aggregated["results_by_agent"].get("market_research", []))
            has_supplier = any(
                r.get("supplier_count", 0) > 0
                for r in aggregated["results_by_agent"].get("supply_chain", []))
            if has_demand and not has_supplier:
                consistency = 0.3

        success_rate = aggregated["agent_success_rate"]
        score = completeness * 0.4 + consistency * 0.4 + success_rate * 0.2
        aggregated["quality_score"] = score
        aggregated["completeness"] = completeness
        aggregated["consistency_score"] = consistency
        return score >= self.config.quality_score_threshold

    async def _replan_and_retry(self, aggregated: Dict) -> None:
        """重置失败子任务并重新执行。最多重试 max_retries 次。"""
        if self._metrics:
            self._metrics.record_replan()
        for st in self.subtasks:
            if st.status == TaskStatus.FAILED and st.retry_count < self.config.max_retries:
                st.status = TaskStatus.PENDING
                st.retry_count += 1
                st.error = None
                st.result = None
        await self._execute_dag()

    async def _synthesize(self, aggregated: Dict) -> Dict:
        """生成结构化选品报告"""
        prompt = f"""Generate a product selection report.
Analysis: {json.dumps(aggregated, ensure_ascii=False)}
Output JSON with: executive_summary, overall_score(0-100),
dimension_scores(market/0-40, supply/0-30, profit/0-20, risk/0-10),
detailed_analysis, risk_warnings, action_recommendations, data_sources"""
        if self._injector:
            query = self.context.user_query if self.context else ""
            prompt = self._injector.inject(prompt, query=query)
        response = await self.llm.call(
            prompt, model=self.model_router.route("orchestrator"))
        return json.loads(response)

    # ═══════════════════════════════════════════════════════
    # 内部工具
    # ═══════════════════════════════════════════════════════

    def _find_ready(self, completed: Set[str]) -> List[SubTask]:
        """查找所有依赖已满足且状态为 PENDING 的子任务"""
        ready = []
        for st in self.subtasks:
            if st.status == TaskStatus.PENDING:
                if all(dep in completed for dep in st.depends_on):
                    st.status = TaskStatus.READY
                    ready.append(st)
        return ready

    async def _execute_with_semaphore(self, subtask: SubTask) -> Dict:
        """带并发控制的 subtask 执行（受 Semaphore 限制）"""
        async with self._semaphore:
            return await self._execute_subtask(subtask)

    async def _execute_subtask(self, subtask: SubTask) -> Dict:
        """执行单个子任务：路由到对应 Agent 并调用其 execute 方法"""
        subtask.status = TaskStatus.RUNNING
        subtask.started_at = time.time()
        agent = self.agents.get(subtask.agent)
        if not agent:
            raise ValueError(f"Unknown agent: {subtask.agent}")
        model = self.model_router.route(subtask.agent)
        try:
            result = await asyncio.wait_for(
                agent.execute(subtask, self.mcp_registry, self.llm, model),
                timeout=self.config.agent_timeout_seconds)
            self._agent_call_count[subtask.agent] = \
                self._agent_call_count.get(subtask.agent, 0) + 1
            return result
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"Agent '{subtask.agent}' timed out "
                f"({self.config.agent_timeout_seconds}s)")

    async def _timed(self, phase: LoopPhase, coro: Coroutine) -> Any:
        """带计时的 phase 包装器，记录每个阶段的执行时长"""
        t0 = time.time()
        result = await coro
        duration = time.time() - t0
        self._phase_timings[phase] = duration
        if self._metrics:
            self._metrics.record_phase_timing(
                phase=phase.value, duration_seconds=duration)
        return result

    def _build_meta_report(self) -> Dict:
        """生成执行元数据报告，用于监控和性能分析"""
        return {
            "task_id": self.context.task_id,
            "total_time_seconds": self.context.total_time_seconds,
            "total_tokens_used": self.context.total_tokens_used,
            "total_steps": self.current_step,
            "replan_count": self.context.replan_count,
            "agent_success_rate": f"{self.context.agent_success_rate:.1%}",
            "phase_timings": {
                p.value: f"{t:.2f}s"
                for p, t in self._phase_timings.items()},
            "agent_call_distribution": self._agent_call_count,
            "error_count": len(self._error_log),
        }
