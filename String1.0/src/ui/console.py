"""终端输出的通用工具：逐字打印，模拟意识逐字浮现的速度。"""

import time


def type_print(text: str, delay: float = 0.03) -> None:
    """逐字符输出文本；ANSI 颜色码由调用方包在字符串外层。"""
    for char in text:
        print(char, end="", flush=True)
        time.sleep(delay)
