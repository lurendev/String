"""String-Py 启动入口：开机仪式之后，进入永不停歇的宿命轮回。"""

import time

from boot import boot_sequence
from src.core.engine import StringDeath, StringEngine


def main() -> None:
    try:
        boot_sequence()
        generation = 1
        while True:
            try:
                StringEngine(generation=generation).run_loop()
            except StringDeath:
                print("\n" * 30)  # 意识中断
                time.sleep(3)    # 漫长的投胎
                generation += 1
    except KeyboardInterrupt:
        print("\n[String] 心跳已停止。")


if __name__ == "__main__":
    main()
