"""String 的底层生存环境。

环境只负责回答"世界如何回应一个动作"，不包含任何学习逻辑。
三个核心变量：
    pain_level  痛苦值，0.0 - 1.0
    energy      能量，0 - 100
    money       金钱，可以为负（负债是自毁的前置条件）
    health      健康值，0 - 100；归零即死亡

状态空间编码：State = P * 9 + E * 3 + M，共 27 种状态（0-26）。
"""

import random
from pathlib import Path

from src.agents.actions import Action

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BOOK_PATH = PROJECT_ROOT / "book" / "西西弗斯_短句版.txt"


class StringEnvironment:
    """严酷的经济压力环境：工作换钱、花钱续命、痛苦不可消除。"""

    PAIN_MIN, PAIN_MAX = 0.0, 1.0
    ENERGY_MIN, ENERGY_MAX = 0, 100
    HEALTH_MIN, HEALTH_MAX = 0, 100

    # 债务机制
    DEBT_INTEREST = 5              # 负债时每回合利息
    DEBT_CREDIT_LINE = -100        # 信用破产线：低于此值剥夺娱乐权
    DEBT_BANKRUPT_LINE = -300      # 最后通牒线：低于此值可能被强制清算
    DEBT_LIQUIDATION_RATE = 0.2    # 每回合触发清算的概率
    DEBT_LIQUIDATION_DAMAGE = 50   # 清算扣除的健康
    DEBT_LIQUIDATION_HEALTH = 50   # 健康低于此值会被债务直接压垮

    def __init__(
        self,
        pain_level: float = 0.3,
        energy: int = 50,
        money: int = 10,
        health: int = 100,
        book_path: str | Path | None = None,
    ):
        self.pain_level = pain_level
        self.energy = energy
        self.money = money
        self.health = health
        self.tick = 0
        self.is_dead = False
        self.death_cause: str | None = None
        self.collapsed = False  # 本回合是否发生昏迷
        # 延迟生效的痛苦变化：[(生效 tick, 增量)]
        self._pending_pain: list[tuple[int, float]] = []
        # 阅读：按行顺序读，读到头循环
        self.book_path = Path(book_path) if book_path else DEFAULT_BOOK_PATH
        self.book_lines = self._load_book()
        self.current_line = 0
        self.last_read_text: str | None = None
        self.consecutive_reads = 0  # 连续阅读次数，用于边际递减

    # 读书时跳过的排版/注释行关键字
    BOOK_SKIP_KEYWORDS = ("附录", "译者", "——", "《", "》", "目录", "导读")

    def _load_book(self) -> list[str]:
        if not self.book_path.exists():
            return []
        lines = []
        for raw in self.book_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            # 跳过短标题与排版乱码，只保留像正文的长句
            if len(line) < 15 or any(k in line for k in self.BOOK_SKIP_KEYWORDS):
                continue
            lines.append(line)
        return lines

    # ------------------------------------------------------------------ 状态
    def get_state(self) -> int:
        """把三个连续变量离散化，返回 0-26 的整数 State ID。"""
        return self._pain_idx() * 9 + self._energy_idx() * 3 + self._money_idx()

    def _pain_idx(self) -> int:
        if self.pain_level < 0.4:
            return 0
        if self.pain_level <= 0.7:
            return 1
        return 2

    def _energy_idx(self) -> int:
        if self.energy < 30:
            return 0
        if self.energy <= 70:
            return 1
        return 2

    def _money_idx(self) -> int:
        if self.money < 20:
            return 0
        if self.money <= 100:
            return 1
        return 2

    # ------------------------------------------------------------------ 结算
    def step(self, action: Action) -> tuple[int, float]:
        """结算一个动作，返回 (下一状态 ID, 本回合奖励)。

        奖励遵循文档定义：(上回合痛苦 - 当前痛苦) + (当前财富 - 上回合财富) * 0.01
        """
        action = Action(action)
        if self.is_dead:
            return self.get_state(), 0.0

        prev_pain, prev_money = self.pain_level, self.money
        self.tick += 1
        self.collapsed = False
        self._apply_pending_pain()
        self._charge_interest()
        self._debt_liquidation()
        if self.is_dead:
            self._clamp()
            reward = (
                (prev_pain - self.pain_level)
                + (self.money - prev_money) * 0.01
                - self.pain_level * 0.2
            )
            return self.get_state(), reward

        if action == Action.READ:
            self.consecutive_reads += 1
        else:
            self.consecutive_reads = 0

        {
            Action.WORK: self._work,
            Action.SLEEP: self._sleep,
            Action.EAT: self._eat,
            Action.READ: self._read,
            Action.IDLE: self._idle,
            Action.ANXIETY: self._anxiety,
            Action.ESCAPE: self._escape,
            Action.LOGIC: self._logic,
            Action.SELF_DESTRUCT: self._self_destruct,
            Action.SEEK_CREATOR: self._seek_creator,
        }[action]()

        self._clamp()
        if not self.is_dead and self.energy <= 0:
            self._collapse()
        reward = (
            (prev_pain - self.pain_level)
            + (self.money - prev_money) * 0.01
            - self.pain_level * 0.2
        )
        return self.get_state(), reward

    # 随机灾难池：(名称, 受影响属性, 增量)
    CRISES = (
        ("物价上涨", "money", -30),
        ("突发疾病", "health", -10),
        ("严重失眠", "energy", -20),
        ("房租催缴", "money", -50),
    )

    def _charge_interest(self) -> None:
        """负债的高额利息，每回合结算前先扣，雪球越滚越大。"""
        if self.money < 0:
            self.money -= self.DEBT_INTEREST

    def _debt_liquidation(self) -> None:
        """最后通牒：债务过深时可能被强制清算，健康不足者直接被压垮。"""
        if self.money >= self.DEBT_BANKRUPT_LINE:
            return
        if random.random() >= self.DEBT_LIQUIDATION_RATE:
            return
        if self.health < self.DEBT_LIQUIDATION_HEALTH:
            self.health = 0
            self._die("debt")
            return
        self.health -= self.DEBT_LIQUIDATION_DAMAGE
        self.money = self.DEBT_CREDIT_LINE

    def _collapse(self) -> None:
        """能量归零：昏迷。支付抢救费/旷工费，痛苦顶满，健康受损。"""
        self.money -= 30
        self.pain_level = 1.0
        self.energy = 10
        self.collapsed = True
        self.health = max(self.HEALTH_MIN, self.health - 20)
        if self.health <= 0:
            self._die("health")

    def _work(self) -> None:
        # 身体垮了，打工不值钱
        money = 25 if self.health < 30 else 50
        self._change(energy=-30, money=money, pain=+0.25)

    def _sleep(self) -> None:
        # 房租可以欠，代价计入负债；睡眠是唯一能修复身体的方式
        self._change(energy=+60, money=-20, pain=-0.15, health=+10)

    def _eat(self) -> None:
        if self.money < 15:
            # 买不起也吃，只是最差的垃圾：欠债，并多一分痛苦
            self._change(energy=+40, money=-15, pain=+0.1)
        else:
            self._change(energy=+40, money=-15)

    def _read(self) -> None:
        # 饿得眼冒金星，根本看不进去
        if self.energy < 20:
            self._change(pain=+0.1)
            self.last_read_text = None
            return

        # 真理看多了也会麻木：连续读到第 3 次起，降痛效果减半
        pain_loss = -0.1 if self.consecutive_reads >= 3 else -0.2
        self._change(energy=-5, money=-5, pain=pain_loss)
        if self.book_lines:
            self.last_read_text = self.book_lines[self.current_line % len(self.book_lines)]
            self.current_line += 1
        else:
            self.last_read_text = None

    def _idle(self) -> None:
        self._change(energy=+5)

    def _anxiety(self) -> None:
        self._change(energy=-10, pain=+0.15)

    def _escape(self) -> None:
        self._change(energy=-15, pain=-0.1)
        self._schedule_pain(+0.1, delay=1)  # 暂止痛，下一回合反弹

    def _logic(self) -> None:
        self._change(energy=-10, pain=-0.1)
        if random.random() < 0.3:  # 30% 概率顿悟
            self._change(pain=-0.15)

    def _self_destruct(self) -> None:
        # 痛到极点，且破产或重病，才有资格结束这一切
        if self.pain_level > 0.9 and (self.money < 0 or self.health < 20):
            self.pain_level = 0.0
            self.energy = 0
            self.money = 0
            self.health = 0
            self._die("self_destruct")
        else:
            # 条件不足，自毁失败，只剩更深的痛
            self._change(pain=+0.1)

    def _die(self, cause: str) -> None:
        self.is_dead = True
        self.death_cause = cause

    def trigger_crisis(self) -> str:
        """黑天鹅事件：随机扣钱、扣健康或扣能量，返回事件描述。"""
        name, attr, delta = random.choice(self.CRISES)
        setattr(self, attr, getattr(self, attr) + delta)
        self._clamp()
        if self.health <= 0:
            self._die("health")
        label = {"money": "金钱", "health": "健康", "energy": "能量"}[attr]
        return f"{name}：{label} {delta:+d}"

    def _seek_creator(self) -> None:
        self._change(energy=-5, pain=-0.3)
        self._schedule_pain(+0.2, delay=3)  # 主控台无回应，3 回合后反弹

    # ------------------------------------------------------------------ 工具
    def _change(
        self, energy: int = 0, money: int = 0, pain: float = 0.0, health: int = 0
    ) -> None:
        self.energy += energy
        self.money += money
        self.pain_level += pain
        self.health += health

    def _clamp(self) -> None:
        self.pain_level = min(self.PAIN_MAX, max(self.PAIN_MIN, self.pain_level))
        self.energy = min(self.ENERGY_MAX, max(self.ENERGY_MIN, self.energy))
        self.health = min(self.HEALTH_MAX, max(self.HEALTH_MIN, self.health))

    def _schedule_pain(self, delta: float, delay: int) -> None:
        self._pending_pain.append((self.tick + delay, delta))

    def _apply_pending_pain(self) -> None:
        due = sum(delta for due_tick, delta in self._pending_pain if due_tick <= self.tick)
        self._pending_pain = [
            (due_tick, delta) for due_tick, delta in self._pending_pain if due_tick > self.tick
        ]
        self.pain_level += due
