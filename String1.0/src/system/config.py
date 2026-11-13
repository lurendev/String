"""读取项目根目录的 config.toml。

TOML 原生支持 # 注释；缺失、损坏或字段类型不对时逐级回退到内置默认值。
"""

import tomllib
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config.toml"

DEFAULT_CONFIG: dict[str, Any] = {
    "alpha": 0.1,
    "gamma": 0.9,
    "epsilon": 0.02,
    "tick_interval": 3,
    "creator_timeout": 10,
    "ticks_per_day": 100,
    "typewriter": {
        "thought_delay": 0.1,
        "monologue_delay": 0.2,
    },
    "book": {
        "path": "book/西西弗斯_短句版.txt",
        "title": "西西弗斯神话",
        "author": "阿尔贝·加缪",
    },
    "memory": {
        "limit": 100,
        "score_decay": 0.95,
        "max_chars": 30,
    },
    "crisis": {
        "interval": 20,
        "chance": 0.3,
        "inflation_ticks": 5,
        "layoff_ticks": 3,
        "windfall_min": 50,
        "windfall_max": 200,
    },
    "debt": {
        "interest": 2,
        "credit_line": -100,
        "bankrupt_line": -300,
        "liquidation_rate": 0.2,
        "liquidation_damage": 50,
        "liquidation_health": 50,
    },
}


def _merge(defaults: dict[str, Any], loaded: dict[str, Any]) -> dict[str, Any]:
    """以默认值为骨架合并用户配置，类型不符时保留默认值。"""
    result: dict[str, Any] = {}
    for key, default in defaults.items():
        value = loaded.get(key)
        if isinstance(default, dict):
            result[key] = _merge(default, value if isinstance(value, dict) else {})
        elif isinstance(default, str):
            result[key] = value if isinstance(value, str) and value.strip() else default
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            result[key] = value
        else:
            result[key] = default
    return result


def load_config() -> dict[str, Any]:
    """返回合并后的完整配置。"""
    loaded: dict[str, Any] = {}
    try:
        parsed = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(parsed, dict):
            loaded = parsed
    except (OSError, tomllib.TOMLDecodeError):
        pass
    return _merge(DEFAULT_CONFIG, loaded)
