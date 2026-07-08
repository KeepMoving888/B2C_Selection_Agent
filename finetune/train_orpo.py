# ============================================================
# finetune/train_orpo.py — Qwen2.5-7B QLoRA + ORPO 微调脚本
#
# 为什么选 ORPO 而不是 DPO？
# ┌────────────────────────────────────────────────────────┐
# │ 1. 显存：ORPO 不需要 reference model → 省 4GB        │
# │    在 4060Ti 16GB 上 DPO 打满，ORPO 还有余量扩 batch  │
# │ 2. 数据：ORPO 在小数据（<1K）上优于 DPO              │
# │    跨境电商高质量偏好对通常只有 500-2000 条            │
# │ 3. 工程：ORPO 一步到位（SFT+偏好同时），DPO 需要两步  │
# │ 4. 稳定性：ORPO 收敛更稳定，不需要调 reward clipping  │
# └────────────────────────────────────────────────────────┘
#
# 为什么选 Qwen2.5-7B？
# ┌────────────────────────────────────────────────────────┐
# │ 1. 项目确定基座：本地主推理模型统一为 Qwen2.5-7B     │
# │ 2. 知识密集型任务：9B 参数 + 领域 ORPO 微调           │
# │    在跨境电商选品分析上质量与成本平衡最佳              │
# │ 3. 部署规划：AWQ INT4 量化后 4060Ti 16GB 可承载       │
# └────────────────────────────────────────────────────────┘
#

# ============================================================

import os
# 静默 trl ORPOTrainer 的 experimental 移除警告
os.environ.setdefault("TRL_EXPERIMENTAL_SILENCE", "1")
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    EarlyStoppingCallback,
    TrainerCallback,
    TrainerControl,
    TrainerState,
)
from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
    TaskType,
)
from trl import ORPOConfig, ORPOTrainer
from datasets import Dataset, load_dataset

# 自动加载项目根目录 .env（确保 WANDB_API_KEY 等变量生效）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"
if _ENV_FILE.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=str(_ENV_FILE), override=True)
        print(f"[Env] Loaded {_ENV_FILE}")
    except ImportError:
        print("[Env] python-dotenv not installed, skipping .env auto-load")


# ── 模型路径解析 ─────────────────────────────────────────

def _resolve_model_path(config: "FineTuneConfig") -> str:
    """
    解析基座模型路径，优先顺序：
      1. 若 config.base_model 指向已存在的本地目录，直接使用
      2. 检查 E 盘本地模型仓库 E:/models/qwen/Qwen2.5-7B
      3. 检查项目历史本地缓存 ./models/qwen/Qwen2.5-7B（向后兼容）
      4. 回退到原始标识符，由 transformers 从 HuggingFace / ModelScope 拉取
    """
    candidates = [
        config.base_model,
        "E:/models/qwen/Qwen2.5-7B",
        "./models/qwen/Qwen2.5-7B",
    ]
    for cand in candidates:
        if Path(cand).exists() and Path(cand).is_dir():
            print(f"[Model] Using local path: {cand}")
            return cand

    print(f"[Model] Local model not found, using HF/ModelScope identifier: {config.base_model}")
    return config.base_model


# ── WandB 可选集成 ───────────────────────────────────────

def _setup_wandb(config: "FineTuneConfig") -> str:
    """
    根据环境变量决定是否启用 WandB。
    仅当 WANDB_API_KEY 设置时才 report_to='wandb'，否则保持 'none'，
    避免未安装/未登录 WandB 时训练失败。
    """
    wandb_key = os.getenv("WANDB_API_KEY", "").strip()
    if not wandb_key:
        return "none"

    # 设置项目与运行名（可通过环境变量覆盖）
    os.environ.setdefault("WANDB_PROJECT", os.getenv("WANDB_PROJECT", "b2c-product-selection"))
    os.environ.setdefault("WANDB_RUN_GROUP", os.getenv("WANDB_RUN_GROUP", "orpo-qwen2.5-7b"))

    try:
        import wandb
        wandb.login(key=wandb_key)
        run_name = os.getenv("WANDB_RUN_NAME", config.run_name)
        wandb.init(
            project=os.environ["WANDB_PROJECT"],
            name=run_name,
            group=os.environ["WANDB_RUN_GROUP"],
            config=config.__dict__,
        )
        print(f"[WandB] Logged in. Project={os.environ['WANDB_PROJECT']}, run={run_name}")
        return "wandb"
    except Exception as e:
        print(f"[WandB] Login/init failed ({e}), falling back to report_to='none'")
        return "none"


# ── 训练监控回调 ─────────────────────────────────────────

class LossThresholdEarlyStopping(TrainerCallback):
    """
    训练 loss 阈值早停回调。

    当训练 loss 已经降至极低（说明训练集已充分拟合），但验证 loss 不再下降时，
    主动保存当前权重并停止训练，避免浪费算力等待 patience 轮数或训练完所有 epoch。

    触发条件（需同时满足）：
      1. 最近一步训练 loss <= train_loss_threshold
      2. 验证 loss 连续 eval_patience 次没有刷新最优值
    """

    def __init__(self, train_loss_threshold: float = 0.1, eval_patience: int = 1):
        self.train_loss_threshold = train_loss_threshold
        self.eval_patience = eval_patience
        self.latest_train_loss: Optional[float] = None
        self.best_eval_loss: Optional[float] = None
        self.no_improve_count: int = 0

    def on_log(self, args, state: TrainerState, control: TrainerControl, logs=None, **kwargs):
        logs = logs or {}
        if "loss" in logs:
            self.latest_train_loss = float(logs["loss"])

    def on_evaluate(self, args, state: TrainerState, control: TrainerControl, metrics=None, **kwargs):
        metrics = metrics or {}
        eval_loss = metrics.get("eval_loss")
        if eval_loss is None or self.latest_train_loss is None:
            return

        eval_loss = float(eval_loss)
        if self.best_eval_loss is None or eval_loss < self.best_eval_loss:
            self.best_eval_loss = eval_loss
            self.no_improve_count = 0
        else:
            self.no_improve_count += 1

        if (
            self.latest_train_loss <= self.train_loss_threshold
            and self.no_improve_count >= self.eval_patience
        ):
            print(
                f"\n[LossThresholdEarlyStopping] 训练 loss={self.latest_train_loss:.4f} "
                f"已低于阈值 {self.train_loss_threshold}，且验证 loss 连续 {self.no_improve_count} "
                f"次未优化（best={self.best_eval_loss:.4f}, current={eval_loss:.4f}）。"
                "保存当前权重并停止训练。"
            )
            control.should_save = True
            control.should_training_stop = True


class TrainingMonitor(TrainerCallback):
    """
    实时记录训练多维度指标：
      - loss / learning_rate / grad_norm
      - GPU 显存与利用率
      - 训练速度（samples/s, tokens/s）
      - 自动写入 output_dir/metrics.jsonl 供后续分析
    """

    def __init__(self, output_dir: str, log_every_n_steps: int = 5, total_steps: int = 0):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.output_dir / "training_metrics.jsonl"
        self.log_every_n_steps = log_every_n_steps
        self.start_time = time.time()
        self.total_steps = total_steps

    def _gpu_stats(self) -> Dict[str, Any]:
        if not torch.cuda.is_available():
            return {}
        return {
            "gpu_allocated_gb": round(torch.cuda.memory_allocated() / 1024**3, 2),
            "gpu_reserved_gb": round(torch.cuda.memory_reserved() / 1024**3, 2),
            "gpu_max_allocated_gb": round(torch.cuda.max_memory_allocated() / 1024**3, 2),
        }

    def on_log(self, args, state: TrainerState, control: TrainerControl, logs=None, **kwargs):
        logs = logs or {}
        if state.global_step % self.log_every_n_steps != 0:
            return

        record = {
            "step": state.global_step,
            "epoch": round(state.epoch, 4) if state.epoch else None,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_seconds": round(time.time() - self.start_time, 2),
            **logs,
            **self._gpu_stats(),
        }

        # 控制台实时打印关键指标（含 ETA）
        eta_str = ""
        if self.total_steps and record["step"] > 0:
            elapsed = record["elapsed_seconds"]
            per_step = elapsed / record["step"]
            remaining = (self.total_steps - record["step"]) * per_step
            eta_str = f" | ETA={remaining/60:.1f}min"

        line = (
            f"[Step {record['step']:>4}/{self.total_steps or '?'}] "
            f"loss={record.get('loss', float('nan')):7.4f} "
            f"lr={record.get('learning_rate', float('nan')):9.2e} "
            f"gpu={record.get('gpu_allocated_gb', 0):5.2f}GB"
            f"{eta_str}"
        )
        print(line)

        # 持久化到 JSONL
        with open(self.metrics_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    def on_train_end(self, args, state: TrainerState, control: TrainerControl, **kwargs):
        total = time.time() - self.start_time
        print(f"\n[Monitor] Total training time: {total/60:.2f} min")
        print(f"[Monitor] Metrics saved to: {self.metrics_file}")


# ── 配置 ─────────────────────────────────────────────────

@dataclass
class FineTuneConfig:
    """微调全配置 — 各参数的设计依据见注释"""
    # 模型
    # 本地训练使用 Qwen2.5-7B（4060Ti 16GB 可高效训练）
    # 生产/云端推理再迁移到 Qwen2.5-7B
    base_model: str = "Qwen/Qwen2.5-7B"
    # Windows 上 flash-attn 安装困难，默认关闭；Linux/CUDA 环境可设为 True
    use_flash_attention: bool = False

    # QLoRA
    lora_r: int = 8           # rank=8：4060Ti 16GB 上平衡速度与质量
    lora_alpha: int = 16      # alpha = 2×r
    lora_dropout: float = 0.05

    # ORPO
    beta: float = 0.1          # ORPO λ：偏好损失权重
    max_length: int = 768      # 显存极紧张，限制序列长度以提速；会截断少量长样本
    max_prompt_length: int = 384

    # 训练
    batch_size: int = 1        # Qwen2.5-7B 在 16GB 下安全值
    gradient_accumulation: int = 8  # 等效 batch=8
    num_epochs: int = 3
    learning_rate: float = 5e-5  # QLoRA 可用稍高的 lr
    warmup_ratio: float = 0.1
    lr_scheduler: str = "cosine_with_restarts"
    gradient_checkpointing: bool = False  # 关闭以提速；若 OOM 再开启

    # 输出
    output_dir: str = "./output/qwen2.5-7b-orpo-ecommerce-v1"
    logging_steps: int = 10            # 每 10 步打印一次终端日志
    save_steps: int = 50               # 每 50 步保存一次 checkpoint（约每 8-10 分钟）
    save_total_limit: int = 3          # 最多保留 3 个 checkpoint，自动删除旧权重

    # 验证与 Early Stopping
    eval_strategy: str = "steps"         # 每 eval_steps 步评估一次验证集
    eval_steps: int = 50                 # 每 50 步验证（与 save_steps 同步）
    load_best_model_at_end: bool = True  # 训练结束时加载验证集最优模型
    metric_for_best_model: str = "eval_loss"  # 以验证 loss 选最优
    greater_is_better: bool = False      # loss 越小越好
    # patience=2：验证 loss 连续 2 次不下降即提前终止，避免过拟合继续消耗算力
    early_stopping_patience: int = 2
    # 训练 loss 阈值：当训练 loss 已降至极低（强拟合）但验证 loss 反弹时，触发保存并停止
    train_loss_overfit_threshold: float = 0.1

    # 监控：默认 none；设置 WANDB_API_KEY 后自动切换为 wandb
    report_to: str = "none"
    run_name: str = "qwen2.5-7b-orpo-ecommerce-v1"


def print_config_table(config: FineTuneConfig, train_dataset_len: int, eval_dataset_len: int = 0):
    """在终端以表格形式打印完整训练配置"""
    total_steps = (train_dataset_len // (config.batch_size * config.gradient_accumulation)) * config.num_epochs
    effective_batch = config.batch_size * config.gradient_accumulation

    lines = [
        "",
        "=" * 64,
        "                   Qwen2.5-7B ORPO 训练参数总览",
        "=" * 64,
        f"  基座模型 (Base Model)     : {config.base_model}",
        f"  输出目录 (Output Dir)     : {config.output_dir}",
        f"  训练样本数                : {train_dataset_len}",
        f"  验证样本数                : {eval_dataset_len}",
        f"  训练轮数 (Epochs)         : {config.num_epochs}",
        f"  每设备批次 (Batch Size)   : {config.batch_size}",
        f"  梯度累积步数              : {config.gradient_accumulation}",
        f"  等效全局批次              : {effective_batch}",
        f"  预估总步数                : {total_steps}",
        f"  学习率 (Learning Rate)    : {config.learning_rate}",
        f"  Warmup Ratio              : {config.warmup_ratio}",
        f"  Warmup Steps              : {max(1, int(total_steps * config.warmup_ratio))}",
        f"  LoRA Rank (r)             : {config.lora_r}",
        f"  LoRA Alpha                : {config.lora_alpha}",
        f"  LoRA Dropout              : {config.lora_dropout}",
        f"  ORPO Beta                 : {config.beta}",
        f"  Max Length                : {config.max_length}",
        f"  Max Prompt Length         : {config.max_prompt_length}",
        f"  优化器                    : adamw_8bit",
        f"  学习率调度                : {config.lr_scheduler}",
        f"  日志打印间隔 (steps)      : {config.logging_steps}",
        f"  验证间隔 (Eval Steps)     : {config.eval_steps} 步",
        f"  Early Stopping Patience   : {config.early_stopping_patience}",
        f"  最优模型选择指标          : {config.metric_for_best_model} ({'越低越好' if not config.greater_is_better else '越高越好'})",
        f"  Checkpoint 保存间隔       : {config.save_steps} 步",
        f"  保留 Checkpoint 数量      : {config.save_total_limit}",
        f"  量化方式                  : 4-bit NF4 + 双重量化",
        f"  混合精度                  : bf16",
        f"  梯度检查点                : {config.gradient_checkpointing}",
        f"  监控后端 (Report To)      : {config.report_to}",
        f"  运行名称 (Run Name)       : {config.run_name}",
        "=" * 64,
        "",
    ]
    print("\n".join(lines))


def find_latest_checkpoint(output_dir: str) -> str | None:
    """查找 output_dir 中最新的 checkpoint-* 目录"""
    output_path = Path(output_dir)
    if not output_path.exists():
        return None
    checkpoints = sorted(output_path.glob("checkpoint-*"), key=lambda p: int(p.name.split("-")[-1]))
    return str(checkpoints[-1]) if checkpoints else None


# ── 核心训练函数 ─────────────────────────────────────────

def train_orpo(config: FineTuneConfig = FineTuneConfig()):
    """
    QLoRA + ORPO 完整训练流程

    显存预算（4060Ti 16GB / Qwen2.5-7B）：
    ┌──────────────────────────────────┐
    │ 4bit 模型权重:            ~5GB   │
    │ LoRA 参数 + 梯度:         ~1GB   │
    │ 优化器状态 (8-bit Adam):  ~2GB   │
    │ 激活值 (batch=1, seq=2K): ~4GB   │
    │ 总计:                    ~12GB   │
    │ 余量:                     ~4GB ✅│
    └──────────────────────────────────┘
    """

    # ── Step 0: 监控后端选择 ──
    config.report_to = _setup_wandb(config)

    # ── Step 1: 4-bit 量化加载 ──
    # NF4 (NormalFloat4) 是信息论最优的 4-bit 量化格式，
    # 相比 FP4 精度更高。双重量化进一步节省约 0.4GB 显存。
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",             # 信息论最优
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,        # 量化 scale 本身 → 再省 0.4GB
    )

    model_path = _resolve_model_path(config)
    print(f"[1/6] Loading base model: {model_path}")
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        attn_implementation=(
            "flash_attention_2" if config.use_flash_attention else "eager"
        ),
        dtype=torch.bfloat16,
    )

    tokenizer = AutoTokenizer.from_pretrained(
        model_path, trust_remote_code=True)
    # Qwen3.5 的 pad_token 已明确为 <|endoftext|>，eos_token 为 <|im_end|>。
    # trl 0.24+ 的 ORPOTrainer 会自动处理 BOS/EOS，无需手动覆盖 bos_token。
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"  # ORPO 要求 left padding

    # ── Step 2: QLoRA 配置 ──
    # Qwen3.5 的 attention (Q/K/V/O) + FFN (gate/up/down) 共 7 个投影矩阵，
    # 全部 LoRA 化可训练参数约 45M (0.50%)，覆盖面最广。
    peft_config = LoraConfig(
        r=config.lora_r,
        lora_alpha=config.lora_alpha,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",        # Attention
            "gate_proj", "up_proj", "down_proj",             # FFN
        ],
        lora_dropout=config.lora_dropout,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )

    print("[2/6] Applying QLoRA adapters...")
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()
    # 预期输出: trainable params: ~45M || all params: ~9.2B || ~0.49%

    # ── Step 3: 数据准备 ──
    # ORPO 数据格式：{prompt, chosen, rejected}
    # 数据来源：DeepSeek V4 生成的选品分析 + 人工筛选
    # chosen = V4 的高质量回答 → 目标行为
    # rejected = 未微调模型的输出或故意构造的劣质回答 → 避免的行为
    print("[3/6] Loading training data...")
    dataset = _load_ecommerce_dataset()

    def format_for_orpo(example):
        # 关键修复：chosen/rejected 末尾追加 <|im_end|>，让模型学会在哪里停止生成
        return {
            "prompt": (
                f"<|im_start|>user\n{example['prompt']}<|im_end|>\n"
                f"<|im_start|>assistant\n"
            ),
            "chosen": f"{example['chosen']}<|im_end|>",
            "rejected": f"{example['rejected']}<|im_end|>",
        }

    if isinstance(dataset, dict):
        train_dataset = dataset["train"].map(format_for_orpo)
        eval_dataset = dataset["eval"].map(format_for_orpo) if "eval" in dataset else None
    else:
        train_dataset = dataset.map(format_for_orpo)
        eval_dataset = None

    # 打印完整训练参数表
    print_config_table(config, len(train_dataset), len(eval_dataset) if eval_dataset else 0)

    # ── Step 4: ORPO 训练配置 ──
    # beta=0.1 是 ORPO 论文推荐的默认值。
    # 小数据集(<1K)可适当增大到 0.2-0.3 以加强偏好信号。
    # 计算 warmup steps（transformers 5.8 中 warmup_ratio 已废弃）
    total_steps = (len(train_dataset) // (config.batch_size * config.gradient_accumulation)) * config.num_epochs
    warmup_steps = max(1, int(total_steps * config.warmup_ratio))

    orpo_config = ORPOConfig(
        output_dir=config.output_dir,
        per_device_train_batch_size=config.batch_size,
        per_device_eval_batch_size=config.batch_size,
        gradient_accumulation_steps=config.gradient_accumulation,
        gradient_checkpointing=config.gradient_checkpointing,
        num_train_epochs=config.num_epochs,
        learning_rate=config.learning_rate,
        lr_scheduler_type=config.lr_scheduler,
        warmup_steps=warmup_steps,
        optim="adamw_8bit",
        weight_decay=0.01,
        bf16=True,
        max_length=config.max_length,
        max_prompt_length=config.max_prompt_length,
        beta=config.beta,
        logging_steps=config.logging_steps,
        save_steps=config.save_steps,
        eval_strategy=config.eval_strategy,
        eval_steps=config.eval_steps,
        save_total_limit=config.save_total_limit,
        load_best_model_at_end=config.load_best_model_at_end,
        metric_for_best_model=config.metric_for_best_model,
        greater_is_better=config.greater_is_better,
        remove_unused_columns=False,
        report_to=config.report_to,
        run_name=config.run_name,
    )

    # trl 0.24 ORPOTrainer 内部访问 model.warnings_issued，部分模型（如 Qwen3_5）缺少该属性
    if not hasattr(model, "warnings_issued"):
        model.warnings_issued = {}

    print("[4/6] Initializing ORPO trainer...")
    monitor_callback = TrainingMonitor(
        output_dir=config.output_dir,
        log_every_n_steps=max(1, config.logging_steps // 2),
        total_steps=total_steps,
    )
    callbacks = [monitor_callback]
    if eval_dataset is not None and config.early_stopping_patience > 0:
        callbacks.append(EarlyStoppingCallback(early_stopping_patience=config.early_stopping_patience))
        print(f"[EarlyStopping] patience={config.early_stopping_patience}, metric={config.metric_for_best_model}")
    if eval_dataset is not None and config.train_loss_overfit_threshold > 0:
        callbacks.append(
            LossThresholdEarlyStopping(
                train_loss_threshold=config.train_loss_overfit_threshold,
                eval_patience=1,
            )
        )
        print(f"[LossThresholdEarlyStopping] threshold={config.train_loss_overfit_threshold}")

    trainer = ORPOTrainer(
        model=model,
        args=orpo_config,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        processing_class=tokenizer,
        callbacks=callbacks,
    )

    # WandB 默认只记录标量指标（loss/lr/gpu 等）。
    # 关闭 wandb.watch 以避免记录梯度直方图带来的额外显存与计算开销。
    if config.report_to == "wandb":
        print("[WandB] Scalar metrics logging enabled (gradient histograms disabled for speed)")

    # ── Step 5: 训练 ──
    print("[5/6] Starting training...")
    print(f"  Train samples: {len(train_dataset)}")
    print(f"  Eval samples: {len(eval_dataset) if eval_dataset else 0}")
    print(f"  Effective batch: {config.batch_size * config.gradient_accumulation}")
    print(f"  Estimated VRAM: ~12GB / 16GB")
    print(f"  Report to: {config.report_to}")

    # 自动检测 checkpoint 并断点续训
    latest_ckpt = find_latest_checkpoint(config.output_dir)
    if latest_ckpt:
        print(f"\n🔄 Resuming from checkpoint: {latest_ckpt}")
        print("   如需从头训练，请删除上述 checkpoint 目录。\n")
        trainer.train(resume_from_checkpoint=latest_ckpt)
    else:
        print("\n🚀 No checkpoint found, training from scratch.\n")
        trainer.train()

    # ── Step 6: 保存 ──
    print("[6/6] Saving model...")
    adapter_path = os.path.join(config.output_dir, "adapter")
    trainer.save_model(adapter_path)
    tokenizer.save_pretrained(adapter_path)

    # 保存训练配置
    with open(os.path.join(config.output_dir, "train_config.json"), "w") as f:
        json.dump(config.__dict__, f, indent=2, default=str)

    print(f"\n✅ Training complete! Adapter saved to: {adapter_path}")
    print(f"   To merge with base model for vLLM deployment:")
    print(f"   python -m peft.merge_and_unload \\")
    print(f"     --base_model {config.base_model} \\")
    print(f"     --adapter {adapter_path} \\")
    print(f"     --output {config.output_dir}/merged")

    return trainer


# ── 数据加载 ─────────────────────────────────────────────

def _load_ecommerce_dataset() -> Dict[str, Dataset]:
    """
    加载跨境电商选品分析训练数据。

    数据划分（按产品严格隔离）：
    - finetune/data/orpo_train.jsonl  : 训练集，训练时可见
    - finetune/data/orpo_val.jsonl    : 验证集，用于 early stopping 和选最优模型
    - finetune/data/orpo_test.jsonl   : 测试集，训练全程不可见，最终评估用

    若划分文件不存在，则回退到完整的 orpo_chosen_rejected.jsonl（兼容旧流程）。
    """
    data_dir = Path(__file__).resolve().parent / "data"
    train_file = data_dir / "orpo_train.jsonl"
    val_file = data_dir / "orpo_val.jsonl"
    test_file = data_dir / "orpo_test.jsonl"

    if train_file.exists() and val_file.exists():
        print(f"[Dataset] Train: {train_file}")
        print(f"[Dataset] Val:   {val_file}")
        print(f"[Dataset] Test:  {test_file} (held out, not used during training)")
        return {
            "train": load_dataset("json", data_files=str(train_file))["train"],
            "eval": load_dataset("json", data_files=str(val_file))["train"],
        }

    # 回退：兼容旧流程
    fallback = data_dir / "orpo_chosen_rejected.jsonl"
    if fallback.exists():
        print(f"[Dataset] Split files not found, fallback to {fallback}")
        return load_dataset("json", data_files=str(fallback))["train"]

    # 无数据集时的内置示例数据，保证脚本可独立运行验证流程
    print("[Dataset] Generated data not found, using built-in sample data.")
    mock_data = [
        {
            "prompt": "分析宠物咀嚼玩具在美国亚马逊的市场前景",
            "chosen": json.dumps({
                "market_demand_score": 0.82,
                "analysis": "Pet chew toys market on Amazon US shows strong demand...",
                "competitor_count": 45,
                "avg_monthly_search_volume": 125000,
                "seasonal_peak": "Q4 (holiday season)",
                "recommendation": "RECOMMENDED with moderate competition"
            }),
            "rejected": json.dumps({
                "market_demand_score": 0.45,
                "analysis": "Some people buy dog toys...",
                "competitor_count": 999,
                "recommendation": "not sure"
            }),
        },
    ]
    return Dataset.from_list(mock_data)


# ── 入口 ─────────────────────────────────────────────────

if __name__ == "__main__":
    config = FineTuneConfig()

    # 可以通过环境变量覆盖配置
    config.base_model = os.getenv("BASE_MODEL", config.base_model)
    # OUTPUT_DIR 若存在，仅作为输出根目录；子目录仍保留 run_name，避免覆盖其他输出
    output_root = os.getenv("OUTPUT_DIR")
    if output_root:
        config.output_dir = os.path.join(output_root, Path(config.output_dir).name)

    print("=" * 60)
    print("QLoRA + ORPO Fine-tuning for Cross-border E-commerce")
    print("=" * 60)
    print(f"Base Model: {config.base_model}")
    print(f"LoRA rank: {config.lora_r}")
    print(f"Batch size: {config.batch_size} × {config.gradient_accumulation}")
    print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")
    print("=" * 60)

    trainer = train_orpo(config)
