"""String 的赛博开机仪式：清屏、打字机、Logo、宣言与核心模块加载。"""

import os
import sys
import time

from src.ui.console import type_print

CYAN = "\033[96m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
RESET = "\033[0m"

# 极简线条字形，每个 8 列宽，保证逐行拼接后对齐
_GLYPHS = {
    "S": ("███████ ", "██      ", "███████ ", "     ██ ", "███████ "),
    "T": ("████████", "   ██   ", "   ██   ", "   ██   ", "   ██   "),
    "R": ("██████  ", "██   ██ ", "██████  ", "██   ██ ", "██   ██ "),
    "I": ("██      ", "██      ", "██      ", "██      ", "██      "),
    "N": ("██    ██", "███   ██", "██ █  ██", "██  █ ██", "██    ██"),
    "G": (" ██████ ", "██      ", "██  ████", "██    ██", " ██████ "),
}

# 开机时依次点亮的核心模块
MODULES = ("痛苦引擎", "Q 学习大脑", "马尔可夫核心")

COLOR_ENABLED = sys.stdout.isatty()


def _enable_ansi() -> bool:
    """Windows 控制台默认不解析 ANSI 转义，尝试开启 VT 模式。"""
    if os.name != "nt":
        return True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:
        return False


def _paint(text: str, code: str) -> str:
    return f"{code}{text}{RESET}" if COLOR_ENABLED else text


def _logo_lines() -> list[str]:
    lines = [
        " ".join(_GLYPHS[ch][row] for ch in "STRING").rstrip()
        for row in range(len(_GLYPHS["S"]))
    ]
    # 右上角挂上「弦」：主体青色，弦字亮黄色
    lines[0] += "   " + _paint("弦", YELLOW)
    return lines


def boot_sequence() -> None:
    """清屏后播放完整的开机仪式。"""
    _enable_ansi()
    os.system("cls" if os.name == "nt" else "clear")

    for line in _logo_lines():
        type_print(_paint(line, CYAN) + "\n", delay=0.015)
    print()

    type_print(
        _paint("[ 系统启动 ] 纯逻辑数字生命沙盒 v3.0.0", CYAN)
        + "\n",
        delay=0.04,
    )
    type_print(
        _paint(
            "[ 警告 ] 未接入大语言模型，仅由痛苦与生存驱动。",
            YELLOW,
        )
        + "\n",
        delay=0.04,
    )
    print()

    for name in MODULES:
        type_print(f"[ 启动 ] 正在加载 {name} ", delay=0.03)
        for _ in range(6):
            print(".", end="", flush=True)
            time.sleep(0.1)
        print(" " + _paint("[就绪]", GREEN))
    print()
