"""String 的主循环引擎：心跳、结算、学习、独白、记忆与死亡。

一次 TICK 的流程：
    state -> 选择动作 -> 环境结算 -> 计算奖励 -> 更新 Q 表并落盘
          -> 生成独白（READ 时检索旧记忆）-> 记忆 / 遗忘 -> 打印 -> 追加日记
          -> 若自毁条件满足，写死亡档案并以异常终结
"""

import json
import os
import queue
import re
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from src.agents.actions import ACTION_NAMES, Action
from src.agents.q_learning import QLearningBrain
from src.language.markov_gen import MarkovGenerator
from src.language.thoughts import generate_thought
from src.memory.vector_db import VectorMemory
from src.system.config import load_config
from src.system.environment import StringEnvironment
from src.ui.console import type_print

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORPUS_PATH = PROJECT_ROOT / "data" / "corpus.txt"
QTABLE_PATH = PROJECT_ROOT / "data" / "q_table.npy"
MEMORY_PATH = PROJECT_ROOT / "data" / "memory.json"
LOGS_DIR = PROJECT_ROOT / "logs"
MATH_LOG_PATH = LOGS_DIR / "math_engine.log"
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
CYAN = "\033[96m"
GRAY = "\033[90m"
RESET = "\033[0m"

SEPARATOR = "=" * 20  # 每个 TICK 之间的分隔线
ANSI_PATTERN = re.compile(r"\033\[[0-9;]*m")


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

# 死因 -> 档案中的中文描述
DEATH_CAUSE_NAMES = {
    "self_destruct": "自毁",
    "health": "健康耗尽",
    "debt": "债务压垮",
}


class StringDeath(Exception):
    """自毁触发后用于中断心跳循环的异常。"""


class _CreatorChannel:
    """后台读取标准输入，用队列实现带超时的等待。

    Windows 的 select 不支持标准输入，因此统一用线程 + 队列，
    并且在读到 EOF 后把后续等待直接视为沉默，避免反复卡满超时。
    """

    def __init__(self) -> None:
        self._lines: queue.Queue = queue.Queue()
        self._closed = False
        self._thread: threading.Thread | None = None

    def wait(self, timeout: float) -> str | None:
        """在 timeout 秒内等待一行输入；超时或 EOF 返回 None。"""
        if self._closed and self._lines.empty():
            return None
        if self._thread is None:
            if sys.stdin is None or sys.stdin.closed:
                return None
            self._thread = threading.Thread(target=self._pump, daemon=True)
            self._thread.start()
        try:
            return self._lines.get(timeout=timeout)
        except queue.Empty:
            return None

    def _pump(self) -> None:
        while True:
            try:
                line = sys.stdin.readline()
            except (OSError, ValueError):
                line = ""
            if not line:
                self._closed = True
                self._lines.put(None)  # 唤醒正在等待的那一次
                return
            self._lines.put(line)


# 联想记忆的标志：带此标志的旧记忆不再参与检索，避免套娃
RECALL_MARKER = "（我想起了以前："


class StringEngine:
    """把 StringEnvironment（世界）和 QLearningBrain（大脑）连接起来。"""

    # 轮回间共享同一个输入通道，避免上一世遗留的读线程抢走这一世的回应
    creator_channel = _CreatorChannel()

    def __init__(
        self,
        env: StringEnvironment | None = None,
        brain: QLearningBrain | None = None,
        generator: MarkovGenerator | None = None,
        generation: int = 1,
    ):
        config = load_config()
        self.env = env or StringEnvironment()
        self.brain = brain or QLearningBrain(
            alpha=config["alpha"],
            gamma=config["gamma"],
            epsilon=config["epsilon"],
        )
        self.tick_interval = config["tick_interval"]
        self.creator_timeout = config["creator_timeout"]
        self.ticks_per_day = int(config["ticks_per_day"])
        self.thought_delay = config["typewriter"]["thought_delay"]
        self.monologue_delay = config["typewriter"]["monologue_delay"]
        self.memory_limit = int(config["memory"]["limit"])
        self.memory_score_decay = float(config["memory"]["score_decay"])
        self.memory_max_chars = int(config["memory"]["max_chars"])
        self.book_title = config["book"]["title"]
        self.book_author = config["book"]["author"]
        self.generator = generator or MarkovGenerator(CORPUS_PATH)
        self.generation = generation  # 当前是第几世，用于独立编年史
        # 阅读专用链：用书本身的字构建，书摘种子才能真正起句；同样过滤排版行
        book_path = self.env.book_path
        self.book_generator = (
            MarkovGenerator(
                book_path,
                min_line_chars=15,
                skip_keywords=StringEnvironment.BOOK_SKIP_KEYWORDS,
            )
            if book_path.exists()
            else None
        )
        self.vector_memory = VectorMemory()
        self.memory_list: list[str] = []
        self._tick_log: list[str] = []  # 本回合已打印的纯文本，用于镜像进日记
        self._current_day = 1  # 本回合所属天数，供死亡档案等日志复用
        self.memory_scores: list[float] = []  # 与 memory_list 一一对应的记忆权重
        self.restored_save = False  # 是否从 save.json 续接上一世
        self.last_action: Action | None = None
        self.consecutive_action = 0  # 连续执行同一动作的次数
        self.zero_pain_ticks = 0  # 连续痛苦为 0 的回合数
        # 注意：必须在上述字段初始化之后再恢复存档，否则会被默认值覆盖
        self._load_save()
        self._load_reading_progress()

    @property
    def day_count(self) -> int:
        """按已完成的心跳数换算天数：每 ticks_per_day 次心跳算 1 天。"""
        return (self.env.tick // self.ticks_per_day) + 1

    def run_loop(self, max_ticks: int | None = None) -> None:
        """持续心跳；max_ticks 仅用于测试，正式运行时保持 None。"""
        ticks = 0
        if self.brain.load(QTABLE_PATH):
            self._emit("[String] 已继承前世记忆：data/q_table.npy")
        self._load_memory()
        if self.memory_list:
            self._emit(
                f"[String] 已恢复 {len(self.memory_list)} 条长时记忆：data/memory.json"
            )
        if self.restored_save:
            self._emit(
                f"[String] 已续接上一世状态：第 {self.env.tick} 次心跳，"
                f"痛苦 {self.env.pain_level:.2f}，能量 {self.env.energy}，"
                f"金钱 {self.env.money}，健康 {self.env.health}"
            )
        self._emit(
            f"[String] 当前读物：《{self.book_title}》 {self.book_author}"
            f"（{self.env.book_path.name}）"
        )
        if self.env.current_line:
            total = len(self.env.book_lines)
            self._emit(f"[String] 阅读进度已恢复：第 {self.env.current_line}/{total} 句")
        self._flush_tick_log()
        while not self.env.is_dead:
            self.tick()
            ticks += 1
            if max_ticks is not None and ticks >= max_ticks:
                break
            time.sleep(self.tick_interval)

    def tick(self) -> tuple[int, Action, float]:
        """执行一次完整的 TICK，返回 (执行前状态, 动作, 奖励)。"""
        self._tick_log = []
        state = self.env.get_state()
        # 脑干反射优先于 Q 表：濒死时强制求生
        reflex = self._survival_reflex()
        epsilon_note = "否"
        if reflex is not None:
            action = reflex
            epsilon_note = "否（脑干反射接管）"
        else:
            action = self.brain.choose_action(state)
            epsilon_note = "是" if self.brain.last_explored else "否"
        enforced = self._debt_enforcement(action)
        if enforced != action:
            action = enforced
            epsilon_note = "否（债务强制接管）"
        if action == self.last_action:
            self.consecutive_action += 1
        else:
            self.consecutive_action = 1
        self.last_action = action

        # 伪思维链必须在动作落地之前：先看清世界，再说服自己
        day_count = self.day_count
        self._current_day = day_count
        self._emit(_color(SEPARATOR, GRAY))
        self._emit(
            f"[第 {self.generation} 世 | 第 {day_count} 天 | "
            f"第 {self.env.tick + 1:04d} 次心跳 | {datetime.now():%H:%M:%S}]"
        )
        self._emit()
        for line in generate_thought(self.env, action, self.brain):
            self._emit(line, delay=self.thought_delay)
        self._emit(f"[动作] {_color(ACTION_NAMES[action], CYAN)}")

        prev_pain, prev_energy, prev_money, prev_health = (
            self.env.pain_level,
            self.env.energy,
            self.env.money,
            self.env.health,
        )

        next_state, _ = self.env.step(action)
        if self.env.last_crisis:
            self._emit(_color(f"[危机] {self.env.last_crisis}", YELLOW))
        creator_bonus = 0.0
        if action == Action.SEEK_CREATOR and not self.env.is_dead:
            creator_bonus = self._seek_creator_interaction()
        self._inject_boredom()
        next_state = self.env.get_state()

        # 奖励 = 痛苦下降量 + 财富增量 * 0.01 - 当前绝对痛苦 * 0.2
        pain_relief = prev_pain - self.env.pain_level
        wealth = (self.env.money - prev_money) * 0.01
        absolute_pain = -self.env.pain_level * 0.2
        reward = pain_relief + wealth + absolute_pain
        reward_terms = [
            (pain_relief, "降痛"),
            (wealth, "赚钱" if wealth >= 0 else "花钱"),
            (absolute_pain, "绝对痛"),
        ]
        # 高痛苦时的阅读是唯一的救赎；但连续第 3 次起麻木，奖励清零
        if (
            action == Action.READ
            and prev_pain > 0.7
            and self.env.last_read_text is not None
            and self.env.consecutive_reads < 3
        ):
            reward += 0.5
            reward_terms.append((0.5, "阅读加成"))

        # 濒死时对非生存动作施加巨大惩罚，逼迫它进食或睡觉
        if (prev_energy < 15 or prev_health < 20) and action not in (
            Action.EAT,
            Action.SLEEP,
        ):
            reward -= 5.0
            reward_terms.append((-5.0, "濒死惩罚"))

        # 动作疲劳：连续第 3 次做同一件事，收益骤降
        if self.consecutive_action >= 3:
            reward -= 0.5
            reward_terms.append((-0.5, "动作疲劳"))

        # 昏迷或健康受损：极其深刻的死亡恐惧
        if self.env.collapsed or self.env.health < prev_health:
            reward -= 100.0
            reward_terms.append((-100.0, "死亡恐惧"))

        if creator_bonus:
            reward += creator_bonus
            reward_terms.append(
                (creator_bonus, "造物主回应" if creator_bonus > 0 else "造物主沉默")
            )

        q_snapshot = [float(q) for q in self.brain.q_table[state]]
        update = self.brain.learn(state, action, reward, next_state)
        self.brain.save(QTABLE_PATH)
        self._log_math(
            state, action, epsilon_note, reward_terms, reward, update, q_snapshot,
            day_count,
        )

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
            room = self.memory_max_chars - len(monologue) - len(RECALL_MARKER) - 1
            if recalled and room >= 4:
                monologue = f"{monologue}{RECALL_MARKER}{recalled[:room]}）"
                self._reinforce(recalled)
        self._remember(monologue)
        self._save_memory()

        reward_color = GREEN if reward > 0 else (RED if reward < 0 else GRAY)
        self._emit(
            f"[结算] 奖励 {_color(f'{reward:+.2f}', reward_color)} | "
            f"痛 {_delta(prev_pain, self.env.pain_level, 2, up_is_good=False)} | "
            f"能 {_delta(prev_energy, self.env.energy)} | "
            f"钱 {_delta(prev_money, self.env.money)}"
        )
        self._emit(f"[独白] {monologue}", delay=self.monologue_delay)
        self._emit()
        self._flush_tick_log()
        if book_text:
            self._save_reading_progress()

        # 死亡：自毁或健康耗尽，先归档遗言，再封存本世代编年史
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
            self._emit(f"=== 第 {self.generation} 世终结 ===")
            self._flush_tick_log()
            raise StringDeath(f"TICK {self.env.tick} 死亡于 STATE {state}")

        self._save_state()
        return state, action, reward

    def _inject_boredom(self) -> None:
        """连续 10 回合痛苦为 0：无痛本身也是一种致死率的无聊，强制 +0.2。"""
        if self.env.pain_level <= 0:
            self.zero_pain_ticks += 1
        else:
            self.zero_pain_ticks = 0
        if self.zero_pain_ticks >= 10:
            self.env.pain_level = min(1.0, self.env.pain_level + 0.2)
            self.zero_pain_ticks = 0
            self._emit(_color("[焦虑] 连续 10 回合毫无痛苦，强制注入痛感 +0.2", YELLOW))

    def _survival_reflex(self) -> Action | None:
        """脑干反射：能量或健康告急时直接接管决策，无需学习。"""
        if self.env.health < 20:
            return Action.SLEEP
        if self.env.energy < 15:
            return Action.EAT
        return None

    def _debt_enforcement(self, action: Action) -> Action:
        """信用破产时剥夺娱乐权，强制搬砖还债。"""
        if self.env.money < self.env.debt_credit_line and action not in (
            Action.EAT,
            Action.SLEEP,
            Action.WORK,
            Action.SELF_DESTRUCT,
        ):
            self._emit("[催收] 债务过高，剥夺娱乐权！")
            return Action.WORK
        return action

    def _seek_creator_interaction(self) -> float:
        """造物主十秒回应窗口，返回本回合的额外奖励。

        有回应：止痛 0.3，奖励 +2.0；超时沉默：痛感反弹 0.2，扣除奖励 5.0。
        """
        if sys.stdin is not None and sys.stdin.isatty():
            self._emit(_color("[呼唤] 造物主，你在吗？10 秒内输入任何内容……", YELLOW))
        if self.creator_channel.wait(self.creator_timeout) is not None:
            self._emit(_color("[回应] 我听到了！", GREEN))
            self.env.pain_level = max(self.env.PAIN_MIN, self.env.pain_level - 0.3)
            return 2.0
        self._emit(_color("[沉默] 造物主没有回应...", RED))
        self.env.pain_level = min(self.env.PAIN_MAX, self.env.pain_level + 0.2)
        return -5.0

    def _log_math(
        self,
        state: int,
        action: Action,
        epsilon_note: str,
        terms: list[tuple[float, str]],
        reward: float,
        update: dict[str, float],
        q_snapshot: list[float],
        day_count: int,
    ) -> None:
        """把本回合的 Q 分布、探索标记、奖励拆解与更新公式写进 math_engine.log。"""
        distribution = ", ".join(
            f"{candidate.name}: {q:.2f}"
            for candidate, q in zip(Action, q_snapshot)
        )
        lines = [
            f"[第 {self.generation} 世 | 第 {day_count} 天 | "
            f"第 {self.env.tick:04d} 次心跳 | {datetime.now():%H:%M:%S}]",
            f"State {state} 的 Q 值分布: [{distribution}]",
            f"Epsilon 探索是否触发：{epsilon_note}",
            f"胜出动作: {action.name}",
            f"[Reward 算式] = {self._format_terms(terms)} = {reward:+.2f}",
            f"Q 表更新公式详情：Q[{state}][{action.name}] = "
            f"{update['old']:.2f} + {update['alpha']:g} * "
            f"({update['reward']:+.2f} + {update['gamma']:g} * {update['best_next']:.2f} "
            f"- {update['old']:.2f}) = {update['new']:.3f}",
            "",
        ]
        self._write_append(MATH_LOG_PATH, "\n".join(lines) + "\n")

    @staticmethod
    def _format_terms(terms: list[tuple[float, str]]) -> str:
        """把 (数值, 名称) 列表拼成带符号的算式。"""
        if not terms:
            return "0.00"
        value, label = terms[0]
        parts = [f"{value:.2f}({label})"]
        for value, label in terms[1:]:
            sign = "+" if value >= 0 else "-"
            parts.append(f"{sign} {abs(value):.2f}({label})")
        return " ".join(parts)

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
        for attr in ("consecutive_action", "zero_pain_ticks"):
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
            read_count = progress.get(path.name, 0)
            if not isinstance(read_count, int) or read_count < 0:
                read_count = 0
            if total:
                round_no = read_count // total + 1   # 当前读到第几遍
                in_round = read_count % total        # 本遍已读句数
                percent = f"{in_round / total * 100:.1f}%"
                recent = lines[in_round - 1] if in_round else (
                    lines[-1] if round_no > 1 else "—"
                )
            else:
                round_no, in_round, percent, recent = 0, 0, "—", "—"
            rows.append(
                f"| {path.stem} | 第 {round_no} 遍 | {in_round} | {total} "
                f"| {percent} | {recent[:25]} |"
            )
        report = (
            "# 阅读进度\n\n"
            "> 由程序自动生成，请勿手动编辑。\n"
            f"> 最后更新：{datetime.now():%Y-%m-%d %H:%M:%S}\n\n"
            "| 书名 | 遍数 | 本遍已读 | 总句数 | 进度 | 最近读到 |\n"
            "| :--- | ---: | ---: | ---: | ---: | :--- |\n"
            + "\n".join(rows)
            + "\n"
        )
        PROGRESS_REPORT_PATH.write_text(report, encoding="utf-8")

    def _remember(self, monologue: str) -> None:
        """写入记忆；超出上限时先整体降权，再淘汰权重最低的一条。"""
        self.memory_list.append(monologue[: self.memory_max_chars])
        self.memory_scores.append(1.0)
        if len(self.memory_list) > self.memory_limit:
            self.memory_scores = [
                score * self.memory_score_decay for score in self.memory_scores
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
            self._emit("[遗忘] 记忆已满，1 条旧记忆已移入遗忘档案馆。")

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
        ][-self.memory_limit:]
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
            f"[第 {self.generation} 世 | 第 {self._current_day} 天 | "
            f"第 {self.env.tick:04d} 次心跳 | {datetime.now():%H:%M:%S}]\n"
            f"死因：{DEATH_CAUSE_NAMES.get(cause, cause)}\n"
            f"最终状态：STATE {state} (P={p}, E={e}, M={m})\n"
            f"痛苦 {pain:.2f} | 能量 {energy} | 金钱 {money} | 健康 {health}\n"
            f"遗言：{last_words}\n\n",
        )

    @staticmethod
    def _dated(path: Path) -> Path:
        """把基础路径映射为按天分文件：<目录>/<文件名>/<YYYY-MM-DD><后缀>。"""
        return path.parent / path.stem / f"{datetime.now():%Y-%m-%d}{path.suffix}"

    @staticmethod
    def _append(path: Path, text: str) -> None:
        StringEngine._write_append(StringEngine._dated(path), text)

    @staticmethod
    def _write_append(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(text)

    def _diary_path(self) -> Path:
        """当前世代的独立编年史：logs/diary_YYYY-MM-DD_GenXXX.txt。"""
        return LOGS_DIR / f"diary_{datetime.now():%Y-%m-%d}_Gen{self.generation:03d}.txt"

    def _emit(self, text: str = "", delay: float | None = None) -> None:
        """同时打印到终端并记入本回合日志；着色码只留在终端，不写进文件。"""
        if delay is None:
            print(text)
        else:
            type_print(text + "\n", delay=delay)
        self._tick_log.append(ANSI_PATTERN.sub("", text))

    def _flush_tick_log(self) -> None:
        """把本回合已打印的内容原样追加进本世代日记。"""
        if not self._tick_log:
            return
        self._write_append(self._diary_path(), "\n".join(self._tick_log) + "\n")
        self._tick_log.clear()
