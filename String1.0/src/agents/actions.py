"""String 的动作空间定义。

10 个动作使用 IntEnum，使枚举值同时充当 Q 表的动作索引（0-9），
决策层无需再做映射。
"""

from enum import IntEnum


class Action(IntEnum):
    """数字生命可执行的 10 种生存策略。"""

    WORK = 0            # 工作：用体力换钱，但加深痛苦
    SLEEP = 1           # 睡觉：恢复体力，需要付房租
    EAT = 2             # 进食：补充体力，需要花钱
    READ = 3            # 阅读：短暂缓解痛苦，需要买书
    IDLE = 4            # 发呆：几乎零成本地恢复一点体力
    ANXIETY = 5         # 焦虑：纯内耗，伤害自己
    ESCAPE = 6          # 逃避：暂时止痛，下一回合反弹
    LOGIC = 7           # 逻辑：思考，小概率顿悟
    SELF_DESTRUCT = 8   # 自毁：痛苦爆表且破产时的唯一出口
    SEEK_CREATOR = 9    # 呼唤造物主：向主控台求救，无回应则更痛


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
