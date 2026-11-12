"""String 的决策大脑：表格型 Q-Learning。

Q 表形状 (27 种状态, 10 个动作)，初始全为 0。
选择：epsilon-greedy —— epsilon 概率随机探索，其余按 np.argmax 选最优。
学习：Q[s, a] += alpha * (reward + gamma * max(Q[s']) - Q[s, a])
"""

import random
from pathlib import Path

import numpy as np

from src.agents.actions import Action


class QLearningBrain:
    """无模型、无大模型的经验学习核心。"""

    STATE_SIZE = 27
    ACTION_SIZE = len(Action)

    def __init__(self, alpha: float = 0.1, gamma: float = 0.9, epsilon: float = 0.02):
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.q_table = np.zeros((self.STATE_SIZE, self.ACTION_SIZE))

    def choose_action(self, state: int) -> Action:
        """epsilon-greedy：epsilon 概率随机探索，其余利用最优动作。"""
        if random.random() < self.epsilon:
            return Action(random.randrange(self.ACTION_SIZE))
        return Action(int(np.argmax(self.q_table[state])))

    def learn(self, state: int, action: Action, reward: float, next_state: int) -> None:
        """用一步时序差分更新 Q 表。"""
        action = int(action)
        best_next = float(np.max(self.q_table[next_state]))
        current = self.q_table[state, action]
        self.q_table[state, action] = current + self.alpha * (
            reward + self.gamma * best_next - current
        )

    def save(self, path: str | Path) -> None:
        """把 Q 表写入磁盘，供下次启动继承前世记忆。"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, self.q_table)

    def load(self, path: str | Path) -> bool:
        """从磁盘载入 Q 表；文件缺失或形状不符时返回 False，保持全零。"""
        path = Path(path)
        if not path.exists():
            return False
        table = np.load(path)
        if table.shape != self.q_table.shape:
            return False
        self.q_table = table
        return True
