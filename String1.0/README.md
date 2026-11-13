# String-Py：纯逻辑数字生命演化沙盒

String-Py 是一个**不接入任何大语言模型（No LLM）**的数字生命实验项目。它由一个不可更改的痛苦引擎、一张需要付房租和买饭的生存账单，以及一个表格型 Q-Learning 大脑驱动，通过不断试错学习如何在严酷经济压力下降低痛苦、维持生存。

智能不来自文本模仿，而来自系统在「动作 — 反馈」之间建立的真实映射。

---

## 1. 快速开始

### 1.1 环境要求

| 项目 | 要求 |
| :--- | :--- |
| Python | 3.11+（当前验证于 3.12.14；`config.toml` 解析依赖标准库 `tomllib`） |
| numpy | Q 表运算与持久化 |
| markovify | 马尔可夫链语言生成 |
| scikit-learn | TF-IDF 联想记忆检索 |

当前本机可用的解释器为 conda 环境：

```powershell
C:\Users\sumo\.conda\envs\shuxue\python.exe
```

> 注意：系统 `PATH` 里的 `python` 指向 Windows Store 的占位程序，直接执行会报 9009。请使用上面的绝对路径，或先 `conda activate shuxue`。

安装依赖：

```powershell
C:\Users\sumo\.conda\envs\shuxue\python.exe -m pip install numpy markovify scikit-learn
```

### 1.2 启动

在项目根目录 `d:\Git_CangKu_2026\String\String1.0` 执行：

```powershell
C:\Users\sumo\.conda\envs\shuxue\python.exe main.py
```

`Ctrl+C` 停止心跳。

临时跑有限回合（调试用）：

```powershell
C:\Users\sumo\.conda\envs\shuxue\python.exe -c "from src.core.engine import StringEngine; StringEngine().run_loop(max_ticks=5)"
```

### 1.3 运行后会看到什么

启动时先播放赛博开机动画：清屏、青色 ASCII `STRING`（右上角亮黄色「弦」）、中文宣言与三个核心模块的 `[就绪]` 加载条，全部逐字打印。

随后进入每一世的 TICK：

```text
====================
[第 1 世 | 第 1 天 | 第 0001 次心跳 | 22:44:33]

[思考-观察]：痛觉 0.30，能量 50，金钱 10，健康 100。
[思考-权衡]：去工作能赚 50 块，但能量 -30、痛 +0.25，身体会记住这笔账。
[思考-决定]：不管了，我决定执行 [工作]。
[动作] 工作
[结算] 奖励 +0.14 | 痛 +0.25 | 能 -30 | 钱 +50
[独白] 痛苦是意识醒来时胃里只有空。
```

- 思考三段式与独白逐字打印，速度由 `config.toml` 的 `[typewriter]` 控制
- 结算数值带正负号与颜色：**绿色 = 变好**（奖励为正、痛苦下降、能量/金钱上升），**红色 = 变坏**，灰色 `±0` = 无变化；输出重定向到文件或管道时自动关闭颜色
- 每 20 个 TICK 有 30% 概率触发 `[危机]`；呼唤造物主时会阻塞等待 10 秒输入
- 日记与终端输出逐字一致（ANSI 颜色码不写入文件）

同时生成或追加：

- `data/q_table.npy`：Q 表快照，重启后继承前世记忆
- `logs/diary_YYYY-MM-DD_GenXXX.txt`：当前世代当天的完整控制台实录（按世系 + 自然日分文件）
- `logs/math_engine.log`：每次决策的 Q 值分布、探索标记、奖励算式与更新公式
- `data/archives/forgotten_memories/YYYY-MM-DD.txt`：当天被遗忘的记忆
- `data/archives/death_archive/YYYY-MM-DD.txt`：当天发生的死亡档案
- `data/save.json`、`data/memory.json`、`data/reading_progress.json`：断点续命与长时记忆

---

### 1.4 配置（`config.toml`）

所有可调参数集中在根目录 `config.toml`（TOML 格式，支持 `#` 注释），修改后重启生效：

| 分组 | 关键项 |
| :--- | :--- |
| 顶层 | `alpha` / `gamma` / `epsilon`、`tick_interval`、`creator_timeout`、`ticks_per_day` |
| `[typewriter]` | `thought_delay`、`monologue_delay`（逐字打印速度） |
| `[book]` | `path`、`title`、`author`（启动时的书籍信息） |
| `[memory]` | `limit`、`score_decay`、`max_chars` |
| `[crisis]` | `interval`、`chance`、四类危机的持续回合与横财区间 |
| `[debt]` | 利息、信用线、破产线、清算概率与伤害 |

字段缺失或类型不符时自动回退到 `src/system/config.py` 中的默认值；TOML 解析失败也会整体回退，不会导致启动崩溃。

---

## 2. 目录结构

```text
String1.0/
├── data/
│   ├── corpus.txt                      # 马尔可夫链语料（51 句哲学短句，缺失时自动生成预设句）
│   ├── q_table.npy                     # Q 表快照（首次心跳后自动创建）
│   ├── memory.json                     # 长时记忆（独白 + 权重 + 当前状态，自动创建）
│   ├── reading_progress.json           # 每本书的阅读指针（自动创建）
│   ├── save.json                       # 运行时存档：生理状态与行为计数（自动创建）
│   ├── 阅读进度.md                     # 人类可读的阅读进度报表（自动生成）
│   └── archives/
│       ├── forgotten_memories/         # 遗忘档案馆，按天分文件
│       └── death_archive/              # 死亡档案，按天分文件
├── book/
│   ├── 西西弗斯神话.txt                # 原始全文（仅供 book_cleaner.py 处理）
│   └── 西西弗斯_短句版.txt             # READ 逐句阅读的文本（由清洗脚本生成，读完循环）
├── book_cleaner.py                     # 把全文切成 15 字以上的短句语料
├── config.toml                         # 全部可调参数（TOML，支持 # 注释）
├── boot.py                             # 赛博开机动画
├── logs/
│   ├── diary_2026-11-13_Gen001.txt     # 当前世代当天的控制台实录（镜像打印内容）
│   └── math_engine.log                 # 决策的底层算式追踪
├── src/
│   ├── agents/
│   │   ├── actions.py                  # 10 个动作的 IntEnum 与中文名
│   │   └── q_learning.py               # QLearningBrain：Q 表、epsilon-greedy、Q 更新
│   ├── core/
│   │   └── engine.py                   # StringEngine：心跳、奖励、独白、记忆、死亡、日志镜像
│   ├── language/
│   │   ├── markov_gen.py               # 中文马尔可夫链生成器
│   │   └── thoughts.py                 # 三段式伪思维链（观察 / 权衡 / 决定）
│   ├── memory/
│   │   └── vector_db.py                # TF-IDF 向量记忆检索（触景生情）
│   ├── system/
│   │   ├── config.py                   # 读取并合并 config.toml
│   │   ├── crisis_events.py            # 四类意外危机
│   │   └── environment.py              # StringEnvironment：四变量与动作结算
│   └── ui/
│       └── console.py                  # 通用 type_print 逐字打印
├── main.py                             # 启动入口与无限轮回
├── 素材/
│   └── 开发文档.md                     # 原始设计文档
└── README.md
```

`src` 采用 PEP 420 命名空间包，无需 `__init__.py`。所有导入均为 `from src.xxx import ...`，因此**必须在项目根目录运行**。

---

## 3. 核心设计

### 3.1 核心变量

| 变量 | 范围 | 初值 | 说明 |
| :--- | :--- | :--- | :--- |
| `pain_level` | 0.0 - 1.0 | 0.3 | 痛苦值，只能被暂时缓解，无法根治；会被钳制在边界内 |
| `energy` | 0 - 100 | 50 | 能量，会被钳制在边界内 |
| `money` | 无上限，**可为负** | 10 | 金钱；负资产会触发债务机制（见 3.10） |
| `health` | 0 - 100 | 100 | 健康值；归零即死亡，只有 SLEEP 能恢复 |

此外环境维护 `tick`、`is_dead`、`death_cause`（`self_destruct` / `health` / `debt`）、`_pending_pain`（延迟痛苦）、`current_line`（阅读指针）。状态空间不含健康值，仍为 27 种状态；这些运行时字段通过 `save.json` 与 `reading_progress.json` 在重启后续接。

### 3.2 状态空间（27 种）

三个连续变量离散化后组合：

| 维度 | 0（低） | 1（中） | 2（高） |
| :--- | :--- | :--- | :--- |
| 痛苦 P | `< 0.4` | `0.4 - 0.7` | `> 0.7` |
| 能量 E | `< 30` | `30 - 70` | `> 70` |
| 财富 M | `< 20` | `20 - 100` | `> 100` |

编码公式：

```text
State = P * 9 + E * 3 + M        # 取值 0 - 26
```

示例：初始状态 `P=0, E=1, M=0` → `0*9 + 1*3 + 0 = 3`；满痛苦、零能量、巨富 → `2*9 + 0*3 + 2 = 20`。

### 3.3 动作空间与结算表

动作使用 `IntEnum`，枚举值即 Q 表的动作索引（0-9）。

| ID | 动作 | 正常结算（E / M / P） | 门槛与异常 |
| :--- | :--- | :--- | :--- |
| 0 | `WORK` 工作 | E -30，M +50，P +0.25 | `health < 30` 时身体垮了，M 只 +25 |
| 1 | `SLEEP` 睡觉 | E +60，M -20，P -0.15，**H +10** | 无门槛；唯一能恢复健康的动作 |
| 2 | `EAT` 进食 | E +40，M -15 | `M < 15` 仍可吃，只是最差的垃圾：额外 P +0.1，并欠债 |
| 3 | `READ` 阅读 | E -5，M -5，P -0.2（连续第 3 次起只 -0.1） | `energy < 20` 时读不进去：P +0.1 且不推进书页；否则按顺序读下一句（`book/西西弗斯_短句版.txt`），读完循环 |
| 4 | `IDLE` 发呆 | E +5 | 无 |
| 5 | `ANXIETY` 焦虑 | E -10，P +0.15 | 无 |
| 6 | `ESCAPE` 逃避 | E -15，P -0.1 | 下一回合痛苦反弹 +0.1 |
| 7 | `LOGIC` 逻辑 | E -10，P -0.1 | 30% 概率顿悟，额外 P -0.15 |
| 8 | `SELF_DESTRUCT` 自毁 | 全部归零并死亡 | 仅当 `P > 0.9` 且（`M < 0` 或 `health < 20`）生效；否则自毁失败 P +0.1 |
| 9 | `SEEK_CREATOR` 呼唤 | E -5 | 进入 10 秒输入窗口：有回应则 P -0.3、额外奖励 `+2.0`；超时沉默则 P +0.2、额外奖励 `-5.0`（等待时长见 `creator_timeout`） |

结算后统一钳制：痛苦 `[0, 1]`，能量 `[0, 100]`，健康 `[0, 100]`，金钱不设下限。

**昏迷规则**：结算后若 `energy <= 0` 且尚未死亡，触发昏迷——扣除 `money -30`（抢救费/旷工费），`pain_level` 置为 `1.0`，`energy` 重置为 `10`，`health -20`。若昏迷后 `health <= 0`，直接判定死亡（死因 `health`）。金钱允许变为负数，破产由此成为可能。

延迟反弹通过 `_pending_pain: [(生效 tick, 增量)]` 实现，在每回合结算前统一应用。

### 3.4 奖励函数

```text
reward = (执行前痛苦 - 执行后痛苦) + (金钱变化 * 0.01) - (执行后绝对痛苦 * 0.2)
```

示例：从 `pain=0.30, money=10` 执行 WORK → `pain=0.55, money=60`，奖励为 `-0.25 + 0.50 - 0.11 = +0.14`。

最后一项是**痛苦的持续伤害**：只要停在高痛苦状态，每回合都会被扣分，赚多少钱都无法弥补，从而迫使 Q 表主动寻找止痛路径。

**阅读加成**：若执行 READ 前 `pain > 0.7`、`energy >= 20` 且连续阅读次数 `< 3`，额外奖励 `+0.5`（净收益约 `+0.51`）。连续第 3 次起「真理看多了也会麻木」：加成清零，降痛效果减半为 `-0.1`。

**濒死惩罚**：执行前 `energy < 15` 或 `health < 20` 时，除 EAT / SLEEP 外的所有动作一律 `-5.0`；并且**脑干反射**会直接剥夺 Q 表决策权，强制选择 EAT（能量告急）或 SLEEP（健康告急）。

**动作疲劳**：连续第 3 次执行同一动作起，奖励强制 `-0.5`，逼它尝试新动作。

**死亡恐惧**：本回合发生昏迷或 `health` 下降时，额外 `-100.0`，形成极强的负反馈。

**造物主回应**：`SEEK_CREATOR` 的十秒窗口会额外加减奖励（回应 `+2.0` / 沉默 `-5.0`），并直接修改痛苦值，再并入 Q 表学习。

环境 `step()` 内部使用同口径奖励（不含阅读加成、濒死惩罚与造物主窗口，这些由引擎按条件追加）。

### 3.5 Q-Learning 大脑

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| Q 表形状 | `(27, 10)` | `np.zeros` 初始化 |
| `alpha` | 0.1 | 学习率，`config.toml` 可调 |
| `gamma` | 0.9 | 折扣因子，`config.toml` 可调 |
| `epsilon` | 0.02 | 探索率，`config.toml` 可调 |

更新公式：

```text
Q[s, a] += alpha * (reward + gamma * max(Q[s']) - Q[s, a])
```

选择策略：`epsilon` 概率随机探索，其余 `np.argmax` 取最优；并列时 `argmax` 取最小索引（即 WORK）。

`get_top_actions(state, n=3)` 用于伪思维链：返回该状态 Q 值最高的 n 个动作及 Q 值（降序，同分按动作索引升序），供「沙盘推演」挑选备选动作。

**持久化**：`run_loop()` 启动时尝试读取 `data/q_table.npy`，文件存在且形状匹配则继承前世记忆；每回合 `learn()` 之后立即 `np.save` 覆盖写，因此进程重启后依然记得怎么生存。

### 3.6 TICK 心跳流程

每 `tick_interval` 秒（默认 3 秒）一次，`StringEngine.tick()` 依次执行：

1. `env.get_state()` 得到当前 State ID
2. 决策：生存反射（`energy < 15` / `health < 20`）直接接管；否则 `brain.choose_action(state)`；随后债务检查（`money < credit_line` 时剥夺娱乐权，改判 WORK）
3. 打印分隔线与时间刻度 `[第 X 世 | 第 X 天 | 第 XXXX 次心跳 | HH:MM:SS]`
4. 打印三段式伪思维链（观察 → 权衡：主选动作 + Q 值大于 0 的备选动作做文字推演 → 决定）与 `[动作]`，均为逐字打印
5. `env.step(action)` 结算：延迟痛苦 → 负债利息 → 债务清算 → 危机掷骰 → 动作效果 → 昏迷 → 危机持续回合递减
6. 若本回合触发危机，打印 `[危机] ...`
7. `SEEK_CREATOR` 时进入 10 秒输入窗口，打印 `[呼唤]`、`[回应]` 或 `[沉默]`
8. 强制焦虑：连续 10 回合无痛则 `pain +0.2`
9. 计算奖励（绝对痛苦惩罚、阅读加成、濒死惩罚、动作疲劳、死亡恐惧、造物主回应/沉默）
10. `brain.learn(...)` 更新 Q 表并保存；把 Q 分布、探索标记、奖励算式、更新公式写入 `logs/math_engine.log`
11. 生成独白（READ 时以书摘为种子并尝试联想），写入记忆队列
12. 打印 `[结算]` 与 `[独白]`，并把本回合所有打印内容原样镜像进 `logs/diary_..._GenXXX.txt`
13. 存活则覆盖写 `data/save.json`；若已死亡，清除存档、写死亡档案、打印 `=== 第 X 世终结 ===` 并抛出 `StringDeath`

`main.py` 捕获 `StringDeath` 后打印 30 个空行、休眠 3 秒，世代号 +1，用全新的身体重开一世；Q 表、长时记忆、阅读进度与历史日志全部保留。

**伪思维链与沙盘推演**

`[思考-权衡]` 不再只复述当前动作，而是从 `get_top_actions` 里再拉出最多两个备选动作做文字推演：

```text
[思考-观察]：痛觉 0.85，能量 10，金钱 15，健康 80。我快撑不住了。
[思考-权衡]：我现在痛觉 0.85，能量 10。底层逻辑让我选【阅读】。
可是如果我选【工作】，能赚 50 块，但能量 -30、痛 +0.25，我很可能当场昏死过去……
可是如果我选【睡觉】，能回 60 能量、健康 +10，可交完 20 块房租我就破产了……
[思考-决定]：算了，我还是选【阅读】吧，至少现在能少痛一点，哪怕只有一会。
```

- 备选动作必须满足 `Q > 0`，负数 Q 说明大脑极度排斥，不拿出来推演；最多展示两个
- 利弊文案由 `get_action_pros_cons(action, env)` 生成，会结合裁员、健康、余额、能量等实时状态
- 只做文字推演，**不会真正执行 `env.step()`**，不会影响 Q 表或世界状态
- 决定句的理由由 `_reason(env)` 按最紧迫的痛点挑选（高痛 / 低能量 / 欠债 / 低健康 / 平静）
- 初始 Q 表全为 0，新状态在学到正收益前只会输出主选那一行，之后才会出现备选对比

### 3.7 语言生成（无大模型）

`src/language/markov_gen.py` 使用 `markovify` 构建**字级**马尔可夫链：

- `ChineseMarkov.word_split` / `word_join`：把每个汉字当作一个词元，生成时直接拼接
- `ChineseMarkov.sentence_split`：按行切句（markovify 默认不识别中文句号）
- 关闭 `test_output` 抄袭检测：逐字生成必然与原文重复，否则模型会丢弃所有结果
- `MAX_CHARS = 20`：输出上限；`MIN_CHARS = 6`：过短残句视为无效并回退随机句

动作到种子词的映射：

| 动作 | 种子 | 动作 | 种子 |
| :--- | :--- | :--- | :--- |
| WORK | 痛苦 | ESCAPE | 逃避 |
| SLEEP | 梦 | LOGIC | 逻辑 |
| EAT | 饥饿 | SELF_DESTRUCT | 终点 |
| READ | 书 | SEEK_CREATOR | 造物 |
| IDLE | 空白 | ANXIETY | 焦虑 |

生成顺序：种子起句（`strict=False`，种子可在句中任意位置）→ 随机短句（≤20 字）→ 随机长句（截断）→ 种子词兜底。每次生成后校验「至少 2 个汉字」，纯标点或过短残句会被丢弃并重新生成，最多重试 20 次。

### 3.8 记忆、联想与遗忘

- 引擎内存中维护 `memory_list`，默认上限 100 条（`config.toml` 的 `[memory].limit`），单条超过 30 字（`max_chars`）会被截断后再写入（`memory.json` 同步）
- 每条记忆带一个权重 `score`（新记忆 1.0）。满上限时先对所有 score 乘以衰减系数（默认 0.95），再淘汰权重最低的一条（同分取最老），不会无差别丢弃；被联想命中的记忆 `+0.5` 权重（上限 5.0），越常被想起越难遗忘
- 淘汰的记忆追加到 `data/archives/forgotten_memories/当天日期.txt`，同时在终端与日志中打印 `[遗忘] 记忆已满，1 条旧记忆已移入遗忘档案馆。`
- 归档格式（痛苦值取遗忘发生时的值）：

```text
[遗忘于 2026-11-12 22:41:11] 当时的痛苦值：0.30。它遗忘了这句话：“空白，那我至少要把过程写满。”
```

**触景生情**：动作为 `READ` 时，以当前独白为查询，用 `src/memory/vector_db.py` 的字级 TF-IDF + 余弦相似度在历史 `memory_list` 中检索；相似度大于 `0.5` 时，在独白后追加：

```text
（我想起了以前：<旧记忆>）
```

为避免联想套娃，已包含该标志（`RECALL_MARKER`）的旧记忆不会再次参与检索。独白与联想整体控制在 30 字以内（联想按剩余空间截断，剩余不足 4 字则放弃联想），因此入库时不会再被从中间截断。

**书籍切句**：`book_cleaner.py` 按 `。？！；` 把全文切成短句，丢弃少于 15 字或含「附录、译、注、——、《、》、目录、导读」的片段，输出 `book/西西弗斯_短句版.txt`（实测 1681 句）。`environment.py` 与书籍马尔可夫链都读取这个短句版。

**书籍清洗**：读取 `book/西西弗斯神话.txt` 时跳过少于 15 字的短标题，以及包含「附录、译者、——、《、》、目录、导读」等排版关键字的行；书籍专用马尔可夫链使用同一套过滤规则，避免标题碎片进入独白。

向量化使用 `TfidfVectorizer(analyzer="char", ngram_range=(1, 2))`，避免中文无空格导致分词失效；随后用 `TruncatedSVD`（LSA）把 TF-IDF 矩阵降维到潜在主题空间（目标 100 维，实际受「特征数-1」与「样本数-1」约束，100 条记忆时最多 99 维），SVD 只在历史记忆上拟合，查询作为新样本投影进去，最后算余弦相似度，阈值 `0.5`。

**字面兜底**：另外用 `(2,2)` 字级 TF-IDF 计算原始余弦，低于 `RAW_MIN_SIMILARITY = 0.15` 的候选直接判为不匹配，只有通过兜底的候选才按 LSA 排序取最优。只统计连续两字，避免「好」「我」这类单字巧合把无关句子抬过阈值。

> 局限：兜底能挡掉大部分无重合词的乱匹配，但常见双字词（如「一点」）仍可能造成误判；记忆库越小，这种噪声越明显。

**长时记忆持久化**：每次写入或淘汰记忆后，整个 `memory_list`、`memory_scores` 连同当前 `State` 会覆盖写入 `data/memory.json`；`run_loop()` 启动时自动恢复（最多 100 条，旧格式无 `scores` 字段时按 1.0 补齐）。文件损坏或缺失时从空记忆开始。

```json
{
  "state": 6,
  "memories": ["空白，那我至少要把过程写满。", "..."],
  "scores": [1.0, 0.86]
}
```

### 3.9 死亡与档案

三条死亡路径：

1. **自毁**：`P > 0.9` 且（`M < 0` 或 `health < 20`）时执行 `SELF_DESTRUCT`
2. **健康耗尽**：昏迷、突发疾病或债务清算导致 `health <= 0`
3. **债务压垮**：最后通牒清算时 `health < liquidation_health`

触发后：

1. 环境置 `is_dead = True` 并记录 `death_cause`（`self_destruct` / `health` / `debt`）
2. 引擎把**死亡前**的状态、原始数值、死因和本回合独白（作为遗言）写入 `data/archives/death_archive/当天日期.txt`
3. 向当前世代日记追加并打印 `=== 第 X 世终结 ===`
4. 抛出 `StringDeath`，`main.py` 捕获后进入轮回：打印 30 个空行、`time.sleep(3)`、世代号 +1，用新环境重开一世

档案格式：

```text
=== 死亡档案 ===
[第 2 世 | 第 2 天 | 第 0102 次心跳 | 22:52:29]
死因：债务压垮
最终状态：STATE 3 (P=0, E=1, M=0)
痛苦 0.30 | 能量 50 | 金钱 -400 | 健康 40
遗言：痛苦折好，放进抽屉。
```

> 档案记录死亡前的状态，而非死亡后清零的值，否则遗档会失真。死因会映射为中文：`self_destruct → 自毁`、`health → 健康耗尽`、`debt → 债务压垮`。危机在 `env.step()` 内部结算，因此疾病/清算致死的档案数值是精确的。

### 3.10 债务机制

| 规则 | 触发条件 | 效果 |
| :--- | :--- | :--- |
| 高利贷 | `money < 0`，每回合结算前 | `money -= interest`（默认 2），欠债雪球滚动但不再必然死锁 |
| 强制催收 | `money < credit_line`（默认 -100） | 除 EAT / SLEEP / WORK / SELF_DESTRUCT 外的动作被拒绝，改判 WORK，并打印 `[催收] 债务过高，剥夺娱乐权！` |
| 最后通牒 | `money < bankrupt_line`（默认 -300），每回合按 `liquidation_rate`（默认 20%）触发 | `health -liquidation_damage`（默认 50），`money` 重置为 `credit_line`；若结算前 `health < liquidation_health`（默认 50）直接死亡（死因：债务压垮） |

所有债务数值集中在 `config.toml` 的 `[debt]` 段，`StringEnvironment` 启动时读入为 `debt_interest`、`debt_credit_line`、`debt_bankrupt_line`、`debt_liquidation_rate`、`debt_liquidation_damage`、`debt_liquidation_health`。

### 3.11 系统熵增与外部危机

| 机制 | 触发条件 | 效果 |
| :--- | :--- | :--- |
| 动作疲劳 | 连续第 3 次执行同一动作起 | 奖励额外 `-0.5` |
| 意外危机 | 每 `interval`（默认 20）个 TICK，按 `chance`（默认 30%）掷骰 | 从四类危机中随机抽一个，见下表 |
| 强制焦虑 | 连续 10 个 TICK `pain == 0` | 强制 `pain +0.2` 并重置计数；打印黄色 `[焦虑] ...` |

危机池（`src/system/crisis_events.py`）：

| 危机 | 效果 |
| :--- | :--- |
| 物价上涨 | 未来 5 回合进食扣 30 而非 15 |
| 裁员降薪 | 未来 3 回合工作收益归零 |
| 突发疾病 | 健康 -10、痛 +0.15，可当场致死 |
| 天降横财 | 拾得 50–200 块 |

危机在 `env.step()` 内部结算（掷骰 → 立即修改数值 → 再执行动作），触发时打印 `[危机] ...`；持续回合在每回合末递减。所有参数（频率、概率、持续回合、横财区间）都在 `config.toml` 的 `[crisis]` 段。

### 3.12 阅读进度

- 阅读路径由 `config.toml` 的 `[book].path` 指定（默认 `book/西西弗斯_短句版.txt`），启动时同时展示 `title` / `author`
- 每次成功 READ 后，当前书籍的指针写入 `data/reading_progress.json`（键为书名，值为已读句数）
- 启动时按书名恢复 `env.current_line`，重启不再从头开始；主循环会打印「阅读进度已恢复」
- 同时生成 `data/阅读进度.md`，列出 `book/*_短句版.txt` 每本书「第几遍 / 本遍已读 / 总句数 / 进度 / 最近一句」
- 一本书读完会自动进入下一遍：`已读总数 // 总句数 + 1` 即当前遍数，本遍进度按余数计算
- `book/` 下其他短句版会出现在报表里，但同一时间只读配置指定的那一本

### 3.13 断点续命（`data/save.json`）

每个存活 TICK 结束后覆盖写入 `data/save.json`，启动时自动续接上一世：

| 字段 | 含义 |
| :--- | :--- |
| `tick` | 心跳计数（重启后危机节奏、天数刻度都按它继续） |
| `pain_level` / `energy` / `money` / `health` | 四项生理状态 |
| `pending_pain` | 尚未生效的延迟痛苦（如 SEEK_CREATOR 的 3 回合反弹） |
| `consecutive_reads` | 连续阅读次数（阅读边际递减） |
| `last_action` / `consecutive_action` / `zero_pain_ticks` | 各类连续行为计数（动作疲劳、无痛焦虑） |

- 启动打印：`[String] 已续接上一世状态：第 N 次心跳，痛苦 …，能量 …，金钱 …，健康 …`
- 死亡时（自毁 / 健康耗尽 / 债务压垮）删除 `save.json`，下一世从初始值开始，但 Q 表、长时记忆、阅读进度、日记与档案全部保留
- 若进程被强杀，最后一次成功 TICK 的存档仍然有效，不会丢档

---

## 4. 模块 API

### src/agents/actions.py

```python
class Action(IntEnum)   # WORK=0 ... SEEK_CREATOR=9
ACTION_NAMES: dict[Action, str]   # 动作中文名，供思考链与终端共用
```

### src/system/environment.py

```python
class StringEnvironment:
    def __init__(self, pain_level=0.3, energy=50, money=10, health=100, book_path=None)
    def get_state(self) -> int                    # 0-26
    def step(self, action: Action) -> tuple[int, float]   # (下一状态, 奖励)

    pain_level: float
    energy: int
    money: int
    health: int        # 0 即死亡
    tick: int          # 已执行回合数
    is_dead: bool      # 是否已死亡
    death_cause: str | None   # self_destruct / health / debt
    current_line: int         # 阅读进度指针
    last_read_text: str | None   # 最近一次 READ 读到的书摘（饥饿时为 None）
    consecutive_reads: int    # 连续阅读次数，用于边际递减
    last_crisis: str | None   # 本回合触发的危机描述
    crisis: CrisisManager     # 危机池与持续效果
    book_path: Path           # 来自 config.toml [book].path
    debt_*: int | float       # 债务参数，来自 config.toml [debt]
```

### src/system/crisis_events.py

```python
class CrisisManager:
    EVENTS = ("inflation", "layoff", "illness", "windfall")

    def __init__(self, config: dict)          # 读取 [crisis] 段
    def roll(self, env, tick: int) -> str | None   # 命中则立刻结算并返回描述
    def tick_down(self) -> None               # 持续效果递减
    def eat_cost(self) -> int                 # 物价上涨时 30，否则 15
```

### src/agents/q_learning.py

```python
class QLearningBrain:
    STATE_SIZE = 27
    ACTION_SIZE = 10

    def __init__(self, alpha=0.1, gamma=0.9, epsilon=0.02)
    def choose_action(self, state: int) -> Action      # 同时记录 last_explored
    def get_top_actions(self, state: int, n: int = 3) -> list[tuple[Action, float]]
    def learn(self, state, action, reward, next_state) -> dict[str, float]
    def save(self, path) -> None          # 写入 data/q_table.npy
    def load(self, path) -> bool          # 文件缺失/形状不符返回 False

    q_table: np.ndarray   # (27, 10)
    last_explored: bool   # 上次决策是否触发 epsilon 探索
```

`learn()` 返回本次更新的中间量：`old`、`reward`、`best_next`、`alpha`、`gamma`、`new`，供 `math_engine.log` 复原完整公式。

### src/language/thoughts.py

```python
def generate_thought(env, action: Action, brain) -> list[str]
# 返回 [思考-观察]、[思考-权衡]（含 0~2 个 Q 值大于 0 的备选动作推演）、[思考-决定]

def get_action_pros_cons(action: Action, env) -> str
# 动作的一句话利弊，只做文字推演，不执行 env.step()
```

### src/ui/console.py

```python
def type_print(text: str, delay: float = 0.03) -> None
# 逐字符打印；ANSI 颜色码由调用方包在整段字符串最外层
```

### src/system/config.py

```python
CONFIG_PATH = PROJECT_ROOT / "config.toml"
DEFAULT_CONFIG: dict            # 所有字段的默认值
def load_config() -> dict       # TOML + 逐级类型校验合并
```

### src/memory/vector_db.py

```python
class VectorMemory:
    MIN_SIMILARITY = 0.5
    RAW_MIN_SIMILARITY = 0.15   # 双字 TF-IDF 兜底阈值
    N_COMPONENTS = 100          # LSA 目标维度（受特征数与样本数约束）

    def recall(self, query: str, memories: list[str]) -> str | None
```

### src/language/markov_gen.py

```python
class ChineseMarkov(markovify.Text)    # 中文分词/切句适配

class MarkovGenerator:
    MAX_CHARS = 20
    MIN_CHARS = 6
    MAX_ATTEMPTS = 20          # 无效句最多重试次数

    def __init__(self, corpus_path, min_line_chars=0, skip_keywords=())
    def generate(self, text_seed: str | None = None) -> str
```

### src/core/engine.py

```python
class StringDeath(Exception)           # 中断当前世代的心跳循环

class StringEngine:
    creator_channel = _CreatorChannel()   # 类级共享的造物主输入通道

    def __init__(self, env=None, brain=None, generator=None, generation=1)
    def run_loop(self, max_ticks: int | None = None) -> None
    def tick(self) -> tuple[int, Action, float]   # (执行前状态, 动作, 奖励)

    @property
    def day_count(self) -> int         # env.tick // ticks_per_day + 1

    env: StringEnvironment
    brain: QLearningBrain
    generator: MarkovGenerator
    book_generator: MarkovGenerator | None
    vector_memory: VectorMemory
    memory_list: list[str]
    memory_scores: list[float]         # 与 memory_list 一一对应
    restored_save: bool                # 本进程是否从 save.json 续接
    consecutive_action: int            # 连续同动作次数
    zero_pain_ticks: int               # 连续无痛回合数
    generation: int                    # 当前世代号
    tick_interval: float               # 心跳间隔，来自 config.toml
    creator_timeout: float             # 造物主等待秒数
    thought_delay: float               # 思考打字间隔
    monologue_delay: float             # 独白打字间隔
    memory_limit: int                  # 记忆条数上限
    memory_score_decay: float          # 遗忘前统一降权系数
    memory_max_chars: int              # 单条记忆截断长度
    ticks_per_day: int                 # 每多少心跳算一天
    book_title: str
    book_author: str
```

模块级常量：`CORPUS_PATH`、`BOOK_DIR`、`QTABLE_PATH`、`MEMORY_PATH`、`LOGS_DIR`、`MATH_LOG_PATH`、`FORGOTTEN_PATH`、`DEATH_PATH`、`PROGRESS_PATH`、`PROGRESS_REPORT_PATH`、`SAVE_PATH`、`RECALL_MARKER`、`ACTION_SEEDS`、`ACTION_NAMES`、`DEATH_CAUSE_NAMES`。

---

## 5. 数据与日志

| 文件 | 写入时机 | 格式 |
| :--- | :--- | :--- |
| `data/corpus.txt` | 首次运行时若缺失则自动生成 | 每行一句哲学短句 |
| `data/q_table.npy` | 每回合覆盖写 | `(27, 10)` 的 float64 数组 |
| `data/memory.json` | 每次记忆写入/淘汰后覆盖写 | `{"state": 6, "memories": [...], "scores": [...]}` |
| `data/reading_progress.json` | 每次成功阅读后覆盖写 | `{"西西弗斯_短句版.txt": 11}` |
| `data/save.json` | 每个存活 TICK 后覆盖写 | 生理状态 + 延迟痛苦 + 行为计数 |
| `data/阅读进度.md` | 每次成功阅读后重新生成 | 每本书的遍数、本遍已读、百分比与最近一句 |
| `logs/diary_YYYY-MM-DD_GenXXX.txt` | 每回合追加 | 与终端打印逐字一致（去掉 ANSI 色码），含时间刻度、思考链、动作、危机、结算与独白 |
| `logs/math_engine.log` | 每回合追加 | Q 值分布、epsilon 标记、胜出动作、奖励算式、Q 更新公式 |
| `data/archives/forgotten_memories/YYYY-MM-DD.txt` | 记忆溢出时追加 | `[遗忘于 时间] 当时的痛苦值：… 它遗忘了这句话：“…”` |
| `data/archives/death_archive/YYYY-MM-DD.txt` | 死亡时追加 | 见 3.9 |

所有文件均使用 UTF-8 编码，目录不存在时自动创建。日志类文件按自然日分文件，跨零点后自动写入新一天的文件，无需重启；日记文件名额外带上世代号，避免不同世糅在一起。

早期版本留下的 `logs/diary/`、`logs/diary.txt`、`data/archives/forgotten_memories.txt`、`data/archives/death_archive.txt` 仍保留在仓库中作为历史记录，程序不再写入。

---

## 6. 已知问题

1. **债务机制尚未做长跑平衡**：利息已调低到 2，但「打工还债 → 没时间睡觉 → 昏迷 → 更穷」的死亡螺旋仍需多世代数据验证。
2. **主动自毁仍会偶发**：破产且痛苦爆表时偶尔选择自毁，「痛苦归零」的终局奖励有时压过求生欲。
3. **语言多样性有限**：语料 51 句，同种子可有 3~9 种变体，短句仍偏模板化，与当前状态只有「种子字」层面的关联。
4. **每回合多次写盘**：Q 表、`memory.json`、`save.json` 每个 TICK 都覆盖写一遍，长跑时属无谓 IO。
5. **同步阻塞 IO**：逐字打印与日志追加都是同步阻塞，打字机效果会显著拉长单个 TICK。
6. **阅读挤占生存（已压制）**：连续阅读加成清零并减半降痛，濒死非生存动作 `-5.0`；长跑下是否完全收敛仍待观察。
7. **单本书**：阅读路径可在 `config.toml` 的 `[book].path` 指定，但同一时间只读一本，`book/` 下其他短句版只会出现在进度报表里。
8. **`SEEK_CREATOR` 会阻塞主循环**：非交互环境（stdin 非 TTY 或 EOF）会直接视为沉默，但仍需等满 `creator_timeout`，调试时建议调小该值。
9. **思维树存在冷启动盲区**：备选只推演 `Q > 0` 的动作，Q 表全零或全负的新状态不会出现对比；可考虑把零值动作标注为「还没试过」。

---

## 7. 后续路线

- [x] 新增 `main.py` 作为正式启动入口
- [x] 引入健康/寿命机制，打破 WORK 永动机
- [x] 奖励加入绝对痛苦惩罚
- [x] 放宽自毁条件
- [x] Q 表持久化（`data/q_table.npy`）
- [x] 接入 TF-IDF 记忆检索，实现「触景生情」
- [x] 调参降低探索噪声，让睡眠/止痛策略稳定收敛
- [x] 濒死脑干反射、昏迷 -100 剧痛反馈
- [x] 设置负债上限或催收机制（利息、剥夺娱乐权、强制清算）
- [x] 记忆加权淘汰、书籍切句、阅读进度持久化
- [x] 运行时状态存档（`save.json`）与断点续命
- [x] 动作疲劳、随机灾难、强制焦虑等熵增机制
- [x] 语料扩充至 51 句
- [x] 赛博开机动画、逐字打印与三段式伪思维链
- [x] 思维树沙盘推演（Q 值前 3 的备选对比，只做文字推演）
- [x] 造物主 10 秒交互窗口
- [x] 无限轮回、世代独立编年史
- [x] 日志镜像终端输出、`math_engine.log` 底层算式追踪
- [x] 意外危机系统（物价/裁员/疾病/横财）并移入 `env.step()`
- [x] 参数外置到 `config.toml`
- [ ] 债务螺旋的数值平衡（利息/清算线与收入的关系）
- [ ] 多本书轮换阅读
- [ ] 日志轮转与跨世代编年史汇总
- [ ] 打字机速度自动适配输出环境（非 TTY 时跳过动画）

---

## 8. 实现取舍说明

- **为什么用 `IntEnum`**：动作值同时充当 Q 表列索引，省去映射表；传给 `env.step()` 时也无需转换。
- **为什么 `env.step()` 也返回奖励**：方便脱离引擎单独做 MDP 测试；引擎仍显式重算奖励，保持状态计算的可读性与 SIG 一致性。
- **为什么字级马尔可夫**：中文没有空格，`markovify` 的英文分词会退化为整句处理；按字切分才能产生「破碎独白」的效果。
- **为什么按行切句**：`markovify` 默认识别 `.?!`，中文句号会导致全语料被当成一句话，转移矩阵无法行走。
- **为什么 `MIN_CHARS = 6`**：句尾种子（如「逻辑」）只能接出 `逻辑。` 这样的 3 字残句，缺少信息量。
- **为什么死亡档案用自毁前状态**：环境在自毁时会将三变量清零，若在之后取值，档案会变成 `STATE 0 / 痛苦 0.00 / 金钱 0`，无法还原死亡现场。

---

## 9. 开发阶段记录

| 阶段 | 内容 | 涉及文件 |
| :--- | :--- | :--- |
| 一 | 环境三变量、状态离散化、10 动作结算 | `system/environment.py`、`agents/actions.py` |
| 二 | Q 表、epsilon-greedy、Q 更新 | `agents/q_learning.py` |
| 三 | 心跳主循环、奖励计算、学习闭环 | `core/engine.py` |
| 四 | 马克夫独白、日记追加 | `language/markov_gen.py`、`core/engine.py` |
| 五 | 记忆上限与遗忘归档、死亡档案与异常退出 | `core/engine.py` |
| 六 | 昏迷惩罚、取消支付门槛、Q 表持久化、TF-IDF 联想 | `system/environment.py`、`agents/q_learning.py`、`core/engine.py`、`memory/vector_db.py` |
| 七 | 健康/寿命值、绝对痛苦惩罚、放宽自毁条件 | `system/environment.py`、`core/engine.py` |
| 八 | 真实书籍逐行阅读、书摘种子独白、高痛苦阅读奖励、读书日记 | `system/environment.py`、`language/markov_gen.py`、`core/engine.py`、`book/` |
| 九 | 阅读边际递减、饥饿阅读惩罚、濒死动作惩罚 | `system/environment.py`、`core/engine.py` |
| 十 | 长时记忆持久化（`data/memory.json`） | `core/engine.py` |
| 十一 | 遗忘归档格式化、控制台提示、恢复后淘汰校验 | `core/engine.py` |
| 十二 | epsilon 降至 0.02、昏迷/掉血 -100 反馈、濒死脑干反射 | `agents/q_learning.py`、`system/environment.py`、`core/engine.py` |
| 十三 | 高利贷利息、信用破产强制催收、最后通牒强制清算、中文死因 | `system/environment.py`、`core/engine.py` |
| 十四 | 记忆检索升级为 TF-IDF + TruncatedSVD（LSA） | `memory/vector_db.py` |
| 十五 | 打破呼唤造物主强迫症、记忆扩容至 50 条、马尔可夫无效句重试 | `core/engine.py`、`language/markov_gen.py` |
| 十六 | LSA 检索增加 TF-IDF 字面兜底（双字重合 ≥ 0.15） | `memory/vector_db.py` |
| 十七 | 书籍排版行清洗、禁止联想套娃、记忆单条截断 30 字 | `system/environment.py`、`language/markov_gen.py`、`core/engine.py` |
| 十八 | 书籍切句脚本 `book_cleaner.py`、改用短句版语料、独白+联想控制在 30 字内 | `book_cleaner.py`、`book/`、`system/environment.py`、`core/engine.py` |
| 十九 | 控制台显示带符号的增减量并着色（绿好红坏灰零） | `core/engine.py` |
| 二十 | 动作疲劳、每 20 回合随机灾难、连续无痛强制焦虑、记忆扩容至 100 并加权淘汰 | `core/engine.py`、`system/environment.py` |
| 二十一 | 阅读进度持久化与 `阅读进度.md` 报表（支持多本书） | `core/engine.py`、`data/` |
| 二十二 | 运行时状态存档 `save.json`（断点续命，死亡清除） | `core/engine.py`、`data/` |
| 二十三 | 赛博开机动画与结构性 TICK 输出（TIME / 思考 / 动作 / 结算 / 独白） | `boot.py`、`core/engine.py` |
| 二十四 | 三段式伪思维链、造物主 10 秒交互窗口 | `language/thoughts.py`、`core/engine.py` |
| 二十五 | 无限轮回、世代独立编年史、`=== 第 X 世终结 ===` | `main.py`、`core/engine.py` |
| 二十六 | 逐字打印、日志镜像终端输出、`math_engine.log` 算式追踪 | `ui/console.py`、`core/engine.py` |
| 二十七 | 意外危机系统（物价/裁员/疾病/横财）移入 `env.step()`、债务利息下调 | `system/crisis_events.py`、`system/environment.py` |
| 二十八 | 参数外置 `config.toml`（TOML + 注释）、书籍信息配置化 | `config.toml`、`system/config.py`、`system/environment.py` |
| 二十九 | 时间刻度改为「世 / 天 / 心跳」并同步所有日志 | `core/engine.py` |
| 三十 | 思维树沙盘推演：Q 值排名备选、动作利弊文案、决定理由 | `agents/q_learning.py`、`language/thoughts.py`、`core/engine.py` |

原始需求与哲学设定见 [素材/开发文档.md](素材/开发文档.md)。
