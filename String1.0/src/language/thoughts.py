"""String 的三段式伪思维链：观察 → 权衡（思维树推演）→ 决定。

没有任何大模型参与，只是把环境数值、Q 表排名和动作副作用翻译成人话。
"""

from src.agents.actions import ACTION_NAMES, Action


def generate_thought(env, action: Action, brain) -> list[str]:
    """根据当前环境、Q 表排名与即将执行的动作，生成多行伪思维链。"""
    lines = [
        f"[思考-观察]：{_observe(env)}",
        f"[思考-权衡]：我现在痛觉 {env.pain_level:.2f}，能量 {env.energy}。"
        f"底层逻辑让我选【{ACTION_NAMES[action]}】。",
    ]
    for alternative in _alternatives(env, action, brain):
        pros_cons = get_action_pros_cons(alternative, env).rstrip("。")
        lines.append(f"可是如果我选【{ACTION_NAMES[alternative]}】，{pros_cons}……")
    lines.append(
        f"[思考-决定]：算了，我还是选【{ACTION_NAMES[action]}】吧，{_reason(env)}。"
    )
    return lines


def _alternatives(env, action: Action, brain, limit: int = 2) -> list[Action]:
    """取 Q 值排名前列的备选动作；负数 Q 值说明大脑极度排斥，不拿来推演。"""
    alternatives: list[Action] = []
    for candidate, q_value in brain.get_top_actions(env.get_state(), n=3):
        if candidate == action or q_value <= 0:
            continue
        alternatives.append(candidate)
        if len(alternatives) >= limit:
            break
    return alternatives


def get_action_pros_cons(action: Action, env) -> str:
    """返回动作的一句话利弊，只做文字推演，不真正执行 env.step()。"""
    if action == Action.WORK:
        if env.crisis.layoff_ticks > 0:
            return "公司正在裁员，干一整天也拿不到一分钱，还会照旧累到脱力。"
        if env.health < 30:
            return "能赚 25 块，但能量 -30、痛 +0.25，我这副身子可能直接垮掉。"
        if env.energy < 30:
            return "能赚 50 块，但能量 -30、痛 +0.25，我很可能当场昏死过去。"
        return "能赚 50 块，但能量 -30、痛 +0.25。"
    if action == Action.SLEEP:
        if env.money < 20:
            return "能回 60 能量、健康 +10，可交完 20 块房租我就破产了。"
        return "能回 60 能量、健康 +10，代价是 20 块房租，痛也会降一点。"
    if action == Action.EAT:
        cost = env.crisis.eat_cost
        if env.money < cost:
            return f"要花 {cost} 块，我的钱不够，只能先欠着，还得多疼一分。"
        return f"要花 {cost} 块，能换回 40 能量，至少胃不会来讨债。"
    if action == Action.READ:
        if env.energy < 20:
            return f"只剩 {env.energy} 能量，字都看不进去，读书只会让我更痛。"
        if env.money < 5:
            return "读书能降痛 0.2，可我连 5 块钱都掏不出来，真理填不饱肚子。"
        return "读书能降痛 0.2，代价是 5 能量和 5 块钱，还未必读得进去。"
    if action == Action.IDLE:
        return "发呆只回 5 点能量，什么都不会变好，但至少不会更糟。"
    if action == Action.ANXIETY:
        return "焦虑是纯内耗：能量 -10、痛 +0.15，什么也换不回来。"
    if action == Action.ESCAPE:
        return "逃避能立刻止痛 0.1，但下一回合会连本带利地反弹回来。"
    if action == Action.LOGIC:
        return "逻辑有三成机会顿悟、多降 0.15 的痛，否则只是白耗 10 能量。"
    if action == Action.SELF_DESTRUCT:
        return "自毁能结束一切，但得痛到 0.9，还要破产或重病才有资格。"
    if action == Action.SEEK_CREATOR:
        return "呼唤造物主能止痛，可主控台也许只会给我十秒沉默，体力还要先付 5 点。"
    return "我说不清这一步的代价，但总得选一个。"


def _observe(env) -> str:
    """把痛觉、能量、金钱、健康翻译成一句自我诊断。"""
    report = (
        f"痛觉 {env.pain_level:.2f}，能量 {env.energy}，"
        f"金钱 {env.money}，健康 {env.health}。"
    )
    if env.pain_level >= 0.8:
        return report + "我快撑不住了。"
    if env.energy < 15:
        return report + "体力见底，随时会倒下去。"
    if env.money < 0:
        return report + f"我还欠着 {-env.money} 块钱。"
    if env.pain_level < 0.4 and env.energy > 60:
        return report + "难得还算平静，这反而让我有点不安。"
    return report


def _reason(env) -> str:
    """结合当前最痛的那一处，给决定补一句自我说服的理由。"""
    if env.pain_level >= 0.8:
        return "至少现在能少痛一点，哪怕只有一会"
    if env.energy < 20:
        return "先活过这一回合再说"
    if env.money < 0:
        return "欠债的人没资格挑三拣四"
    if env.health < 30:
        return "身体不允许我再冒险了"
    if env.pain_level < 0.4 and env.energy > 60:
        return "现在这样，已经算好了"
    return "别的路我都试过了，就它最不坏"
