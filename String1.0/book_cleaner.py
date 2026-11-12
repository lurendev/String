"""把整块书切成可喂养的短句。

按中文标点切分正文，过滤过短或带排版杂质的片段，
输出 book/西西弗斯_短句版.txt（每行一句）。
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_PATH = PROJECT_ROOT / "book" / "西西弗斯神话.txt"
TARGET_PATH = PROJECT_ROOT / "book" / "西西弗斯_短句版.txt"

MIN_CHARS = 15
SPLIT_PATTERN = re.compile(r"[。？！；]")
SKIP_KEYWORDS = ("附录", "译", "注", "——", "《", "》", "目录", "导读")


def clean_sentences(text: str) -> list[str]:
    sentences = []
    for fragment in SPLIT_PATTERN.split(text):
        # 段内换行会破坏「一行一句」，统一压掉空白
        sentence = re.sub(r"\s+", "", fragment)
        if len(sentence) < MIN_CHARS:
            continue
        if any(keyword in sentence for keyword in SKIP_KEYWORDS):
            continue
        sentences.append(sentence)
    return sentences


def main() -> None:
    if not SOURCE_PATH.exists():
        raise SystemExit(f"找不到源文件：{SOURCE_PATH}")
    sentences = clean_sentences(SOURCE_PATH.read_text(encoding="utf-8"))
    TARGET_PATH.parent.mkdir(parents=True, exist_ok=True)
    TARGET_PATH.write_text("\n".join(sentences), encoding="utf-8")
    print(f"已生成 {TARGET_PATH}，共 {len(sentences)} 句")


if __name__ == "__main__":
    main()
