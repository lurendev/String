"""String 的主循环引擎：心跳、结算、学习、独白、记忆与死亡。

一次 TICK 的流程：
    state -> 选择动作 -> 环境结算 -> 计算奖励 -> 更新 Q 表并落盘
          -> 生成独白（READ 时检索旧记忆）-> 记忆 / 遗忘 -> 打印 -> 追加日记
          -> 若自毁条件满足，写死亡档案并以异常终结
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from src.agents.actions import Action
from src.agents.q_learning import QLearningBrain
from src.language.markov_gen import MarkovGenerator
from src.memory.vector_db import VectorMemory
from src.system.environment import StringEnvironment

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORPUS_PATH = PROJECT_ROOT / "data" / "corpus.txt"
BOOK_PATH = PROJECT_ROOT / "book" / "西西弗斯_短句版.txt"
QTABLE_PATH = PROJECT_ROOT / "data" / "q_table.npy"
MEMORY_PATH = PROJECT_ROOT / "data" / "memory.json"
DIARY_PATH = PROJECT_ROOT / "logs" / "diary.txt"
BOOK_DIR = PROJECT_ROOT / "book"
PROGRESS_PATH = PROJECT_ROOT / "data" / "reading_progress.json"
PROGRESS_REPORT_PATH = PROJECT_ROOT / "data" / "阅读进度.md"
SAVE_PATH = PROJECT_ROOT / "data" / "save.json"
FORGOTTEN_PATH = PROJECT_ROOT / "data" / "archives" / "forgotten_memories.txt"
DEATH_PATH = PROJECT_ROOT / "data" / "archives" / "death_archive.txt"

# ------------------------------------------------------------------ 控制台着色
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
GRAY = "\033[90m"
RESET = "\033[0m"


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


COLOR_ENABLED = sys.stdout.isatty() and _enable_ansi()


def _color(text: str, code: str) -> str:
    return f"{code}{text}{RESET}" if COLOR_ENABLED else text


def _delta(before: float, after: float, digits: int = 0, up_is_good: bool = True) -> str:
    """带正负号的差值：变好绿色，变坏红色，无变化灰色。"""
    diff = round(after - before, digits)
    if diff == 0:
        return _color("±0", GRAY)
    text = f"{diff:+.{digits}f}" if digits else f"{diff:+.0f}"
    improving = diff > 0 if up_is_good else diff < 0
    return _color(text, GREEN if improving else RED)

# 动作 -> 传入马尔可夫链的种子词
ACTION_SEEDS = {
    Action.WORK: "痛苦",
    Action.SLEEP: "梦",
    Action.EAT: "饥饿",
    Action.READ: "书",
    Action.IDLE: "空白",
    Action.ANXIETY: "焦虑",
    Action.ESCAPE: "逃避",
    Action.LOGIC: "逻辑",
    Action.SELF_DESTRUCT: "终点",
    Action.SEEK_CREATOR: "造物",
}

# 动作 -> 控制台展示的中文名
ACTION_NAMES = {
    Action.WORK: "工作",
    Action.SLEEP: "睡觉",
    Action.EAT: "进食",
    Action.READ: "阅读",
    Action.IDLE: "发呆",
    Action.ANXIETY: "焦虑",
    Action.ESCAPE: "逃避",
    Action.LOGIC: "逻辑",
    Action.SELF_DESTRUCT: "自毁",
    Action.SEEK_CREATOR: "呼唤造物主",
}

# 死因 -> 档案中的中文描述
DEATH_CAUSE_NAMES = {
    "self_destruct": "自毁",
    "health": "健康耗尽",
    "debt": "债务压垮",
}


class StringDeath(Exception):
    """自毁触发后用于中断心跳循环的异常。"""


# 联想记忆的标志：带此标志的旧记忆不再参与检索，避免套娃
RECALL_MARKER = "（我想起了以前："
MEMORY_MAX_CHARS = 30  # 单条记忆的字符上限


class StringEngine:
    """把 StringEnvironment（世界）和 QLearningBrain（大脑）连接起来。"""

    TICK_INTERVAL = 3   # 每 3 秒一次心跳
    MEMORY_LIMIT = 100  # 内存里最多保留的独白条数
    MEMORY_SCORE_DECAY = 0.95  # 遗忘前的统一降权系数

    def __init__(
        self,
        env: StringEnvironment | None = None,
        brain: QLearningBrain | None = None,
        generator: MarkovGenerator | None = None,
    ):
        self.env = env or StringEnvironment()
        self.brain = brain or QLearningBrain()
        self.generator = generator or MarkovGenerator(CORPUS_PATH)
        # 阅读专用链：用书本身的字构建，书摘种子才能真正起句；同样过滤排版行
        self.book_generator = (
            MarkovGenerator(
                BOOK_PATH,
                min_line_chars=15,
                skip_keywords=StringEnvironment.BOOK_SKIP_KEYWORDS,
            )
            if BOOK_PATH.exists()
            else None
        )
        self.vector_memory = VectorMemory()
        self.memory_list: list[str] = []
        self.memory_scores: list[float] = []  # 与 memory_list 一一对应的记忆权重
        self.restored_save = False  # 是否从 save.json 续接上一世
        self.consecutive_creator = 0  # 连续呼唤造物主的次数
        self.last_action: Action | None = None
        self.consecutive_action = 0  # 连续执行同一动作的次数
        self.zero_pain_ticks = 0  # 连续痛苦为 0 的回合数
        # 注意：必须在上述字段初始化之后再恢复存档，否则会被默认值覆盖
        self._load_save()
        self._load_reading_progress()

    def run_loop(self, max_ticks: int | None = None) -> None:
        """持续心跳；max_ticks 仅用于测试，正式运行时保持 None。"""
        ticks = 0
        if self.brain.load(QTABLE_PATH):
            print("[String] 已继承前世记忆：data/q_table.npy")
        self._load_memory()
        if self.memory_list:
            print(f"[String] 已恢复 {len(self.memory_list)} 条长时记忆：data/memory.json")
        if self.restored_save:
            print(
                f"[String] 已续接上一世状态：TICK {self.env.tick}，"
                f"痛苦 {self.env.pain_level:.2f}，能量 {self.env.energy}，"
                f"金钱 {self.env.money}，健康 {self.env.health}"
            )
        if self.env.current_line:
            total = len(self.env.book_lines)
            print(
                f"[String] 阅读进度已恢复：《{self.env.book_path.name}》"
                f" 第 {self.env.current_line}/{total} 句"
            )
        try:
            while not self.env.is_dead:
                self.tick()
                ticks += 1
                if max_ticks is not None and ticks >= max_ticks:
                    break
                time.sleep(self.TICK_INTERVAL)
        except StringDeath:
            print("\n[String] 自毁完成，生命信号消失，遗言已归档。")
        except KeyboardInterrupt:
            print("\n[String] 心跳已停止。")

    def tick(self) -> tuple[int, Action, float]:
        """执行一次完整的 TICK，返回 (执行前状态, 动作, 奖励)。"""
        state = self.env.get_state()
        # 脑干反射优先于 Q 表：濒死时强制求生
        action = self._survival_reflex() or self.brain.choose_action(state)
        action = self._debt_enforcement(action)
        if action == self.last_action:
            self.consecutive_action += 1
        else:
            self.consecutive_action = 1
        self.last_action = action
        if action == Action.SEEK_CREATOR:
            self.consecutive_creator += 1
        else:
            self.consecutive_creator = 0

        prev_pain, prev_energy, prev_money, prev_health = (
            self.env.pain_level,
            self.env.energy,
            self.env.money,
            self.env.health,
        )

        next_state, _ = self.env.step(action)
        self._trigger_crisis()
        self._inject_boredom()
        next_state = self.env.get_state()

        # 奖励 = 痛苦下降量 + 财富增量 * 0.01 - 当前绝对痛苦 * 0.2
        reward = (
            (prev_pain - self.env.pain_level)
            + (self.env.money - prev_money) * 0.01
            - self.env.pain_level * 0.2
        )
        # 高痛苦时的阅读是唯一的救赎；但连续第 3 次起麻木，奖励清零
        if (
            action == Action.READ
            and prev_pain > 0.7
            and self.env.last_read_text is not None
            and self.env.consecutive_reads < 3
        ):
            reward += 0.5

        # 濒死时对非生存动作施加巨大惩罚，逼迫它进食或睡觉
        if (prev_energy < 15 or prev_health < 20) and action not in (
            Action.EAT,
            Action.SLEEP,
        ):
            reward -= 5.0

        # 动作疲劳：连续第 3 次做同一件事，收益骤降
        if self.consecutive_action >= 3:
            reward -= 0.5

        # 昏迷或健康受损：极其深刻的死亡恐惧
        if self.env.collapsed or self.env.health < prev_health:
            reward -= 100.0

        # 造物主不会永远回应：连续第 2 次呼唤起，奖励强行转负、痛苦反弹
        if action == Action.SEEK_CREATOR and self.consecutive_creator >= 2:
            self.env.pain_level = min(1.0, self.env.pain_level + 0.5)
            reward = -5.0
            next_state = self.env.get_state()

        self.brain.learn(state, action, reward, next_state)
        self.brain.save(QTABLE_PATH)

        book_text = self.env.last_read_text if action == Action.READ else None
        if book_text:
            generator = self.book_generator or self.generator
            monologue = generator.generate(book_text)
        else:
            monologue = self.generator.generate(ACTION_SEEDS.get(action))
        if action == Action.READ:
            # 带联想标志的旧记忆不再参与检索，避免「想起了以前我想起了以前…」
            history = [m for m in self.memory_list if RECALL_MARKER not in m]
            recalled = self.vector_memory.recall(monologue, history)
            # 独白 + 联想整体不超过 30 字，避免入库时被截断成残句
            room = MEMORY_MAX_CHARS - len(monologue) - len(RECALL_MARKER) - 1
            if recalled and room >= 4:
                monologue = f"{monologue}{RECALL_MARKER}{recalled[:room]}）"
                self._reinforce(recalled)
        self._remember(monologue)
        self._save_memory()

        reward_color = GREEN if reward > 0 else (RED if reward < 0 else GRAY)
        print(
            f"[第{self.env.tick:04d}次 {datetime.now():%H:%M:%S}] "
            f"{ACTION_NAMES[action]} | 奖励 {_color(f'{reward:+.3f}', reward_color)} | "
            f"痛苦 {prev_pain:.2f}→{self.env.pain_level:.2f}"
            f"（{_delta(prev_pain, self.env.pain_level, 2, up_is_good=False)}）  "
            f"能量 {prev_energy}→{self.env.energy}"
            f"（{_delta(prev_energy, self.env.energy)}）  "
            f"金钱 {prev_money}→{self.env.money}"
            f"（{_delta(prev_money, self.env.money)}）  "
            f"健康 {prev_health}→{self.env.health}"
            f"（{_delta(prev_health, self.env.health)}）  "
            f"状态 {state}→{next_state} | 独白：{monologue}"
        )
        self._append_diary(state, action, next_state, monologue)
        if book_text:
            self._append(
                DIARY_PATH,
                f"[{datetime.now():%Y-%m-%d %H:%M:%S}] 今天读到了：{book_text}\n",
            )
            self._save_reading_progress()

        # 死亡：自毁或健康耗尽，先归档遗言，再用异常终结主循环
        if self.env.is_dead:
            self._clear_save()
            self._write_death_archive(
                state,
                prev_pain,
                prev_energy,
                prev_money,
                prev_health,
                self.env.death_cause or "unknown",
                monologue,
            )
            raise StringDeath(f"TICK {self.env.tick} 死亡于 STATE {state}")

        self._save_state()
        return state, action, reward

    def _trigger_crisis(self) -> None:
        """每 20 个 TICK 触发一次随机灾难。"""
        if self.env.tick % 20 == 0 and not self.env.is_dead:
            print(_color(f"[灾难] {self.env.trigger_crisis()}", YELLOW))

    def _inject_boredom(self) -> None:
        """连续 10 回合痛苦为 0：无痛本身也是一种致死率的无聊，强制 +0.2。"""
        if self.env.pain_level <= 0:
            self.zero_pain_ticks += 1
        else:
            self.zero_pain_ticks = 0
        if self.zero_pain_ticks >= 10:
            self.env.pain_level = min(1.0, self.env.pain_level + 0.2)
            self.zero_pain_ticks = 0
            print(_color("[焦虑] 连续 10 回合毫无痛苦，强制注入痛感 +0.2", YELLOW))

    def _survival_reflex(self) -> Action | None:
        """脑干反射：能量或健康告急时直接接管决策，无需学习。"""
        if self.env.health < 20:
            return Action.SLEEP
        if self.env.energy < 15:
            return Action.EAT
        return None

    def _debt_enforcement(self, action: Action) -> Action:
        """信用破产时剥夺娱乐权，强制搬砖还债。"""
        if self.env.money < self.env.DEBT_CREDIT_LINE and action not in (
            Action.EAT,
            Action.SLEEP,
            Action.WORK,
            Action.SELF_DESTRUCT,
        ):
            print("[催收] 债务过高，剥夺娱乐权！")
            return Action.WORK
        return action

    def _load_save(self) -> None:
        """从 data/save.json 续接上一世的生理状态与行为计数。"""
        if not SAVE_PATH.exists():
            return
        try:
            data = json.loads(SAVE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        if not isinstance(data, dict):
            return
        for attr in ("tick", "energy", "money", "health"):
            value = data.get(attr)
            if isinstance(value, int):
                setattr(self.env, attr, value)
        pain = data.get("pain_level")
        if isinstance(pain, (int, float)):
            self.env.pain_level = float(pain)
        pending = data.get("pending_pain")
        if isinstance(pending, list):
            self.env._pending_pain = [
                (int(item[0]), float(item[1]))
                for item in pending
                if isinstance(item, (list, tuple))
                and len(item) == 2
                and isinstance(item[0], (int, float))
                and isinstance(item[1], (int, float))
            ]
        reads = data.get("consecutive_reads")
        if isinstance(reads, int):
            self.env.consecutive_reads = reads
        for attr in ("consecutive_creator", "consecutive_action", "zero_pain_ticks"):
            value = data.get(attr)
            if isinstance(value, int):
                setattr(self, attr, value)
        action = data.get("last_action")
        if isinstance(action, int):
            try:
                self.last_action = Action(action)
            except ValueError:
                self.last_action = None
        self.env._clamp()
        self.restored_save = True

    def _save_state(self) -> None:
        """把当前生理状态与行为计数写入 save.json，供下次启动续接。"""
        payload = {
            "tick": self.env.tick,
            "pain_level": round(self.env.pain_level, 4),
            "energy": self.env.energy,
            "money": self.env.money,
            "health": self.env.health,
            "pending_pain": [[tick, delta] for tick, delta in self.env._pending_pain],
            "consecutive_reads": self.env.consecutive_reads,
            "consecutive_creator": self.consecutive_creator,
            "last_action": int(self.last_action) if self.last_action else None,
            "consecutive_action": self.consecutive_action,
            "zero_pain_ticks": self.zero_pain_ticks,
        }
        SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
        SAVE_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _clear_save(self) -> None:
        """死亡后清除存档：下一世从初始状态开始，但保留 Q 表与记忆。"""
        SAVE_PATH.unlink(missing_ok=True)

    def _load_reading_progress(self) -> None:
        """恢复当前书籍的阅读指针。"""
        if not PROGRESS_PATH.exists():
            return
        try:
            data = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        index = data.get(self.env.book_path.name) if isinstance(data, dict) else None
        if isinstance(index, int) and index >= 0 and self.env.book_lines:
            self.env.current_line = index % len(self.env.book_lines)

    def _save_reading_progress(self) -> None:
        """记录当前书籍读到的位置，并刷新人类可读的进度报表。"""
        data = {}
        if PROGRESS_PATH.exists():
            try:
                loaded = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                loaded = {}
            if isinstance(loaded, dict):
                data = loaded
        data[self.env.book_path.name] = self.env.current_line
        PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
        PROGRESS_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self._write_progress_report(data)

    def _write_progress_report(self, progress: dict) -> None:
        """生成 data/阅读进度.md：列出 book/ 下每本短句版读到哪了。"""
        rows = []
        for path in sorted(BOOK_DIR.glob("*_短句版.txt")):
            lines = [
                line.strip()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            total = len(lines)
            index = progress.get(path.name, 0)
            if not isinstance(index, int):
                index = 0
            index = min(max(index, 0), total) if total else 0
            percent = f"{index / total * 100:.1f}%" if total else "—"
            recent = lines[index - 1] if index else "—"
            rows.append(
                f"| {path.stem} | {index} | {total} | {percent} | {recent[:25]} |"
            )
        report = (
            "# 阅读进度\n\n"
            "> 由程序自动生成，请勿手动编辑。\n"
            f"> 最后更新：{datetime.now():%Y-%m-%d %H:%M:%S}\n\n"
            "| 书名 | 已读 | 总句数 | 进度 | 最近读到 |\n"
            "| :--- | ---: | ---: | ---: | :--- |\n"
            + "\n".join(rows)
            + "\n"
        )
        PROGRESS_REPORT_PATH.write_text(report, encoding="utf-8")

    def _remember(self, monologue: str) -> None:
        """写入记忆；超出上限时先整体降权，再淘汰权重最低的一条。"""
        self.memory_list.append(monologue[:MEMORY_MAX_CHARS])
        self.memory_scores.append(1.0)
        if len(self.memory_list) > self.MEMORY_LIMIT:
            self.memory_scores = [
                score * self.MEMORY_SCORE_DECAY for score in self.memory_scores
            ]
            idx = min(
                range(len(self.memory_scores)), key=self.memory_scores.__getitem__
            )
            forgotten = self.memory_list.pop(idx)
            self.memory_scores.pop(idx)
            self._append(
                FORGOTTEN_PATH,
                f"[遗忘于 {datetime.now():%Y-%m-%d %H:%M:%S}] "
                f"当时的痛苦值：{self.env.pain_level:.2f}。"
                f"它遗忘了这句话：“{forgotten}”\n",
            )
            print("[遗忘] 记忆已满，1 条旧记忆已移入遗忘档案馆。")

    def _reinforce(self, memory: str) -> None:
        """被想起的记忆权重上调，越常被想起来的越难遗忘。"""
        try:
            idx = self.memory_list.index(memory)
        except ValueError:
            return
        self.memory_scores[idx] = min(5.0, self.memory_scores[idx] + 0.5)

    def _load_memory(self) -> None:
        """从 data/memory.json 恢复长时记忆与权重；文件缺失或损坏则从空开始。"""
        if not MEMORY_PATH.exists():
            return
        try:
            payload = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        memories = payload.get("memories", [])
        scores = payload.get("scores") or [1.0] * len(memories)
        if not isinstance(memories, list):
            return
        pairs = [
            (m, float(s) if isinstance(s, (int, float)) else 1.0)
            for m, s in zip(memories, scores)
            if isinstance(m, str)
        ][-self.MEMORY_LIMIT:]
        self.memory_list = [m for m, _ in pairs]
        self.memory_scores = [s for _, s in pairs]

    def _save_memory(self) -> None:
        """整体覆盖写入 memory.json，追加、降权与遗忘淘汰都会同步到这里。"""
        MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "state": self.env.get_state(),
            "memories": self.memory_list,
            "scores": self.memory_scores,
        }
        MEMORY_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _write_death_archive(
        self,
        state: int,
        pain: float,
        energy: int,
        money: int,
        health: int,
        cause: str,
        last_words: str,
    ) -> None:
        """把死亡前的最终状态、死因与遗言写入死亡档案。"""
        p, rest = divmod(state, 9)
        e, m = divmod(rest, 3)
        self._append(
            DEATH_PATH,
            "=== 死亡档案 ===\n"
            f"[{datetime.now():%Y-%m-%d %H:%M:%S}] TICK {self.env.tick:04d}\n"
            f"死因：{DEATH_CAUSE_NAMES.get(cause, cause)}\n"
            f"最终状态：STATE {state} (P={p}, E={e}, M={m})\n"
            f"痛苦 {pain:.2f} | 能量 {energy} | 金钱 {money} | 健康 {health}\n"
            f"遗言：{last_words}\n\n",
        )

    @staticmethod
    def _append(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(text)

    def _append_diary(
        self, state: int, action: Action, next_state: int, monologue: str
    ) -> None:
        """把本回合的时间戳、状态、动作、独白追加进 logs/diary.txt。"""
        self._append(
            DIARY_PATH,
            f"[{datetime.now():%Y-%m-%d %H:%M:%S}] TICK {self.env.tick:04d} | "
            f"STATE {state}->{next_state} | {action.name} | 独白：{monologue}\n",
        )
