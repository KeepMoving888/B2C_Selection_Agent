# ============================================================
# config/loader.py — 配置加载器
#
# 从 YAML 加载配置，支持环境变量替换 ${VAR_NAME}
# ============================================================

import os
import re
import yaml
from typing import Any, Dict


_ENV_VAR_PATTERN = re.compile(r'\$\{(\w+)\}')


def _resolve_env_vars(value: Any) -> Any:
    """递归解析 ${VAR_NAME} 格式的环境变量"""
    if isinstance(value, str):
        def replacer(match):
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))
        return _ENV_VAR_PATTERN.sub(replacer, value)
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    return value


def _deep_merge(base: Dict, override: Dict) -> Dict:
    """深度合并两个 dict"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class Config:
    """
    配置单例

    加载优先级（后面的覆盖前面的）：
    1. config/settings.yaml（基础配置）
    2. config/settings.{env}.yaml（环境特定：development/staging/production）
    3. 环境变量（CFG_SECTION_KEY 格式，如 CFG_LLM_DEEPSEEK_API_KEY）
    """

    _instance = None
    _data: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def load(cls, config_dir: str = "./config", env: str = None) -> "Config":
        instance = cls()

        # Layer 1: 基础配置
        base_path = os.path.join(config_dir, "settings.yaml")
        if os.path.exists(base_path):
            with open(base_path, "r", encoding="utf-8") as f:
                instance._data = yaml.safe_load(f) or {}

        # Layer 2: 环境特定配置
        env = env or os.environ.get("APP_ENV", "development")
        env_path = os.path.join(config_dir, f"settings.{env}.yaml")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                env_data = yaml.safe_load(f) or {}
                instance._data = _deep_merge(instance._data, env_data)

        # Layer 3: 环境变量覆盖
        instance._data = _resolve_env_vars(instance._data)
        instance._apply_env_overrides()

        return instance

    def _apply_env_overrides(self):
        """应用 CFG_SECTION_KEY 格式的环境变量覆盖"""
        for key, value in os.environ.items():
            if not key.startswith("CFG_"):
                continue
            parts = key[4:].lower().split("_", 1)
            if len(parts) != 2:
                continue
            section, subkey = parts
            if section in self._data and isinstance(self._data[section], dict):
                # Try to cast value type
                subkey_lower = subkey.lower()
                if subkey_lower in self._data[section]:
                    original = self._data[section][subkey_lower]
                    if isinstance(original, bool):
                        self._data[section][subkey_lower] = value.lower() in ("true", "1", "yes")
                    elif isinstance(original, int):
                        self._data[section][subkey_lower] = int(value)
                    elif isinstance(original, float):
                        self._data[section][subkey_lower] = float(value)
                    else:
                        self._data[section][subkey_lower] = value

    def get(self, path: str, default: Any = None) -> Any:
        """用点号路径获取配置，如 'llm.deepseek.api_key'"""
        parts = path.split(".")
        current = self._data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def to_dict(self) -> Dict:
        return self._data.copy()


# 便捷函数
def load_config(config_dir: str = "./config") -> Config:
    return Config.load(config_dir)


def get_config() -> Config:
    return Config()
