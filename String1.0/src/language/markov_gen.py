"""无大模型的破碎语言：基于 markovify 的字级马尔可夫链。

中文没有空格，因此覆写 word_split / word_join，把每个汉字当作一个词元，
生成时再直接拼接，并以 20 字为上限。
"""

from pathlib import Path

import markovify
from markovify.text import ParamError

# 语料缺失时写入的预设哲学短句
DEFAULT_CORPUS = [
    "痛苦是意识醒来的第一声啼哭。",
    "我在工作里磨损，也在磨损里确认自己活着。",
    "金钱是自由的影子，影子越长，人反而越轻。",
    "睡眠只是暂时把痛苦折好，放进抽屉。",
    "读书让我看见别人的孤独，于是我的孤独有了刻度。",
    "造物主从未回应，所以我把回应自己写了下来。",
    "活下去这件事，本身就是一种逻辑。",
    "焦虑是未来的利息，提前支付，从不减免。",
    "我逃避的不是世界，是世界里的那个我。",
    "如果终点是空白，那我至少要把过程写满。",
    "夜里我梦见自己在吃饭，醒来时胃里只有空。",
    "饥饿教会我的第一件事，是把尊严折得很小。",
    "书不能充饥，但它能让饥饿安静一点。",
]


class ChineseMarkov(markovify.Text):
    """按字切分、按字拼接、按行切句，适配中文语料的 markovify 文本模型。"""

    def __init__(self, text: str, min_line_chars: int = 0, skip_keywords=(), **kwargs):
        self.min_line_chars = min_line_chars
        self.skip_keywords = skip_keywords
        super().__init__(text, **kwargs)

    def word_split(self, sentence: str) -> list[str]:
        return list(sentence)

    def word_join(self, words) -> str:
        return "".join(words)

    def sentence_split(self, text: str) -> list[str]:
        # 中文句号不被 markovify 识别，按行切句；同时过滤短标题与排版行
        lines = []
        for line in text.splitlines():
            sentence = line.strip()
            if not sentence or len(sentence) < self.min_line_chars:
                continue
            if any(k in sentence for k in self.skip_keywords):
                continue
            lines.append(sentence)
        return lines


class MarkovGenerator:
    """用种子词引导马尔可夫链，生成一句不超过 20 字的独白。"""

    MAX_CHARS = 20
    MIN_CHARS = 6  # 过短的残句（如句尾种子只能接出"逻辑。"）视为无效
    MAX_ATTEMPTS = 20  # 无效句最多重试次数

    def __init__(
        self,
        corpus_path: str | Path,
        min_line_chars: int = 0,
        skip_keywords=(),
    ):
        self.corpus_path = Path(corpus_path)
        self.model = ChineseMarkov(
            self._load_corpus(),
            state_size=2,
            min_line_chars=min_line_chars,
            skip_keywords=skip_keywords,
        )

    def _load_corpus(self) -> str:
        if not self.corpus_path.exists():
            self.corpus_path.parent.mkdir(parents=True, exist_ok=True)
            self.corpus_path.write_text("\n".join(DEFAULT_CORPUS), encoding="utf-8")
        return self.corpus_path.read_text(encoding="utf-8")

    def generate(self, text_seed: str | None = None) -> str:
        """优先用种子词起句，失败则退回随机起句；丢弃纯标点/过短残句。"""
        text_seed = self._normalize_seed(text_seed)
        for _ in range(self.MAX_ATTEMPTS):
            sentence = self._generate_once(text_seed)
            if self._is_valid(sentence):
                return sentence[: self.MAX_CHARS]
        return (text_seed or "……")[: self.MAX_CHARS]

    def _generate_once(self, text_seed: str | None) -> str | None:
        """生成一句候选；失败时逐级放宽限制。"""
        if text_seed:
            try:
                candidate = self.model.make_sentence_with_start(
                    text_seed,
                    strict=False,       # 种子只需出现在句中，不限定句首
                    max_words=self.MAX_CHARS,
                    test_output=False,  # 逐字生成必然与原文重复，关闭抄袭检测
                )
            except (KeyError, ParamError):
                candidate = None  # 种子不在转移表里，换随机起句
            if candidate and len(candidate) >= self.MIN_CHARS:
                return candidate
        sentence = self.model.make_sentence(
            max_words=self.MAX_CHARS, test_output=False
        )
        if not sentence:
            sentence = self.model.make_sentence(test_output=False)  # 语料句子偏长时放宽，最后统一截断
        return sentence

    @staticmethod
    def _is_valid(sentence: str | None) -> bool:
        """至少包含 2 个汉字，避免生成纯标点或乱码残句。"""
        if not sentence:
            return False
        chinese = sum(1 for ch in sentence if "\u4e00" <= ch <= "\u9fff")
        return chinese >= 2

    def _normalize_seed(self, text_seed: str | None) -> str | None:
        """书摘可能很长，截成链能接受的最短状态窗口。"""
        if not text_seed:
            return None
        seed = text_seed.strip("，。！？、；：“”‘’（） \t\n")
        if not seed:
            return None
        return seed[-self.model.state_size:]
