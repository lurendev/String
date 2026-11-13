"""String 的意外危机系统：按配置的间隔掷骰，命中后扰动世界。

CrisisManager 只负责掷骰、维护持续效果与写回即时效果；
真正的调用点在 StringEnvironment.step() 内部，保证死亡档案读到结算后的真实数值。
"""

import random


class CrisisManager:
    """四类危机的抽取与结算，参数全部来自 config.toml 的 crisis 段。"""

    EVENTS = ("inflation", "layoff", "illness", "windfall")

    def __init__(self, config: dict) -> None:
        self.interval = int(config["interval"])
        self.chance = float(config["chance"])
        self.inflation_duration = int(config["inflation_ticks"])
        self.layoff_duration = int(config["layoff_ticks"])
        self.windfall_min = int(config["windfall_min"])
        self.windfall_max = int(config["windfall_max"])
        self.inflation_ticks = 0  # 剩余回合：进食扣钱翻倍
        self.layoff_ticks = 0     # 剩余回合：工作收益归零

    def roll(self, env, tick: int) -> str | None:
        """按频率与概率掷骰；触发时立刻修改 env，并返回危机描述。"""
        if tick % self.interval != 0 or random.random() >= self.chance:
            return None

        event = random.choice(self.EVENTS)
        if event == "inflation":
            self.inflation_ticks = self.inflation_duration
            return f"物价上涨：未来 {self.inflation_duration} 回合进食扣钱翻倍"
        if event == "layoff":
            self.layoff_ticks = self.layoff_duration
            return f"裁员降薪：未来 {self.layoff_duration} 回合工作收益归零"
        if event == "illness":
            env.health -= 10
            env.pain_level += 0.15
            env._clamp()
            return "突发疾病：健康 -10，痛 +0.15"

        windfall = random.randint(self.windfall_min, self.windfall_max)
        env.money += windfall
        return f"天降横财：捡到 {windfall} 块"

    def tick_down(self) -> None:
        """每回合结束递减持续效果。"""
        if self.inflation_ticks > 0:
            self.inflation_ticks -= 1
        if self.layoff_ticks > 0:
            self.layoff_ticks -= 1

    @property
    def eat_cost(self) -> int:
        """物价上涨期间进食费用翻倍。"""
        return 30 if self.inflation_ticks > 0 else 15
