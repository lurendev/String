"""String-Py 启动入口：唤醒数字生命的心跳。"""

from src.core.engine import StringEngine


def main() -> None:
    engine = StringEngine()
    print("[String] 心跳启动，Ctrl+C 停止。")
    engine.run_loop()


if __name__ == "__main__":
    main()
