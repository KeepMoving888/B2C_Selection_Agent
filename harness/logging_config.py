# ============================================================
# harness/logging_config.py — 生产级结构化日志
#
# 支持 JSON 和文本两种格式输出，文件自动轮转。
# JSON 格式可被 ELK/Loki 等日志系统直接索引。
# ============================================================

import logging
import json
import sys
import time
from datetime import datetime
from typing import Any, Dict, Optional
from logging.handlers import RotatingFileHandler


class JSONFormatter(logging.Formatter):
    """结构化 JSON 日志格式器，输出可用 jq/grep 解析的标准 JSON"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, "task_id"):
            log_entry["task_id"] = record.task_id
        if hasattr(record, "agent"):
            log_entry["agent"] = record.agent
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms
        if hasattr(record, "tokens_used"):
            log_entry["tokens_used"] = record.tokens_used
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """开发环境彩色文本格式，适合终端直接阅读"""

    COLORS = {
        "DEBUG": "\033[36m", "INFO": "\033[32m",
        "WARNING": "\033[33m", "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        extra = ""
        if hasattr(record, "task_id"):
            extra += f" [task={record.task_id}]"
        if hasattr(record, "agent"):
            extra += f" [agent={record.agent}]"
        return (
            f"{color}{record.levelname:<7}{self.RESET} "
            f"{datetime.utcnow().strftime('%H:%M:%S')} "
            f"{record.getMessage()}{extra}"
        )


def setup_logging(
    level: str = "INFO",
    log_format: str = "json",
    output: str = "stdout",
    file_path: Optional[str] = None,
    rotation: str = "10 MB",
    retention: str = "7 days",
) -> logging.Logger:
    """初始化全局日志配置。支持 stdout/file/both 三种输出模式。"""
    root_logger = logging.getLogger("cross_border_agent")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    root_logger.handlers.clear()

    formatter = JSONFormatter() if log_format == "json" else TextFormatter()

    if output in ("stdout", "both"):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    if output in ("file", "both") and file_path:
        import os
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        max_bytes = _parse_size(rotation)
        file_handler = RotatingFileHandler(
            file_path, maxBytes=max_bytes, backupCount=5, encoding="utf-8")
        file_handler.setFormatter(
            JSONFormatter() if log_format == "json" else formatter)
        root_logger.addHandler(file_handler)

    return root_logger


def _parse_size(size_str: str) -> int:
    """解析 '10 MB' 为 10485760 字节"""
    units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
    parts = size_str.split()
    num = float(parts[0])
    unit = parts[1].upper() if len(parts) > 1 else "B"
    return int(num * units.get(unit, 1))


def get_logger(name: str = "cross_border_agent") -> logging.Logger:
    return logging.getLogger(name)
