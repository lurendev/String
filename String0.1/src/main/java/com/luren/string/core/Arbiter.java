package com.luren.string.core;

import com.luren.string.model.Candidate;
import com.luren.string.modules.BaseModule;
import com.luren.string.system.EnergySystem;
import com.luren.string.system.EvolutionEngine;
import com.luren.string.system.PainEngine;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * 仲裁器：系统的认知心跳。
 * <p>
 * 每 1000 毫秒执行一次 TICK：收集所有无意识模块的候选者，
 * 乘上痛苦系数后执行胜者全拿（WTA），只有显著强于当前焦点者才能进入全局工作空间。
 */
public class Arbiter {

    /** 心跳周期：10 秒一次，避免控制台刷屏。 */
    private static final long TICK_INTERVAL_MS = 10000L;

    /** 焦点切换阈值：新候选者得分必须超过当前焦点的 1.2 倍，才值得打断旧意识。 */
    private static final double FOCUS_THRESHOLD = 1.2;

    /** 阅读特权：只要比当前焦点高 5 分，就立刻抢夺焦点。 */
    private static final double READING_SWITCH_MARGIN = 5.0;

    /** 专注模式持续多少次 TICK（10 秒一次 × 5 = 50 秒）。 */
    private static final int FOCUS_MODE_TICKS = 5;

    /** 专注模式下其他模块的得分系数。 */
    private static final double FOCUS_MODE_PENALTY = 0.5;

    /** 连续读完多少页触发"虚假的平静"。 */
    private static final int CALM_PAGES = 3;

    /** 虚假平静的广播内容。 */
    private static final String CALM_LINE = "好像看书的时候，没那么痛了。";

    /** 逃避/虚无焦点的自然衰减：每次 TICK 分数 ×0.95，逐渐失去效力。 */
    private static final double STALE_FOCUS_DECAY = 0.95;

    /** 连续多少次 TICK 焦点不变，就强制惊醒。 */
    private static final int FORCE_WAKE_TICKS = 10;

    /** 审美疲劳：同一模块连续获胜，每次得分 ×0.95。 */
    private static final double FATIGUE_PER_WIN = 0.95;

    /** 所有无意识模块（潜意识）。 */
    private final List<BaseModule> modules;

    /** 全局工作空间，用于读取当前焦点与广播新的胜者。 */
    private final GlobalWorkspace workspace;

    /** 心跳调度器：单线程，保证 TICK 串行执行、不会并发修改意识状态。 */
    private final ScheduledExecutorService scheduler;

    /** 距下一次 TICK 还剩几秒，供读秒打印使用。 */
    private volatile int secondsLeft = (int) (TICK_INTERVAL_MS / 1000L);

    /** 连续多少次 TICK 焦点没有变过。 */
    private int unchangedTicks;

    /** 上一个连续获胜的模块名。 */
    private String fatigueSource;

    /** 该模块连续获胜的次数。 */
    private int winStreak;

    /** 是否处于"专注阅读"模式：阅读赢下焦点后开启。 */
    private boolean isReadingMode;

    /** 专注模式剩余 TICK 数。 */
    private int readingModeTicksLeft;

    /** 连续读完了多少页书。 */
    private int readingPages;

    /**
     * @param modules 参与竞争的模块列表
     */
    public Arbiter(List<BaseModule> modules) {
        // 复制一份，避免外部在运行期间增删列表导致并发问题
        this.modules = new ArrayList<BaseModule>(modules);
        this.workspace = GlobalWorkspace.getInstance();
        // 守护线程：主程序退出时心跳随之停止，不拖住 JVM
        this.scheduler = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread thread = new Thread(r, "arbiter-tick");
            thread.setDaemon(true);
            return thread;
        });
    }

    /**
     * 启动认知心跳：立即开始，之后每 {@link #TICK_INTERVAL_MS} 毫秒跳动一次；
     * 同时每秒打印一次倒计时，让人看得见它还活着。
     */
    public void start() {
        scheduler.scheduleAtFixedRate(() -> {
            try {
                tick();
            } catch (Exception e) {
                // scheduleAtFixedRate 一旦抛出未捕获异常会永久停止后续调度，
                // 这里兜住单个模块的异常，保证心跳不死
                System.out.println("[仲裁] TICK 异常: " + e.getMessage());
            } finally {
                // 每次 TICK 结束后重置读秒
                secondsLeft = (int) (TICK_INTERVAL_MS / 1000L);
            }
        }, 0L, TICK_INTERVAL_MS, TimeUnit.MILLISECONDS);

        scheduler.scheduleAtFixedRate(() -> {
            if (secondsLeft > 0) {
                // 原地刷新，始终只占一行
                Console.countdown("[读秒] 距下次 TICK 还有 " + secondsLeft + " 秒");
                secondsLeft--;
            }
            // 专注阅读时，每秒回复 2 点能量：看书是一种逃避和回血
            if (isReadingMode) {
                EnergySystem.recover(2.0);
            }
        }, 0L, 1000L, TimeUnit.MILLISECONDS);
    }

    /**
     * 一次认知节拍：收集 → 加权 → 选最高分 → 超过阈值则广播。
     */
    private void tick() {
        Candidate winner = null;
        // 同一 TICK 内所有模块共享同一个痛苦系数，保证横向可比
        double painFactor = 1.0 + PainEngine.getPainLevel();
        // 虚弱状态：能量低于 20% 时所有模块得分减半
        double energyFactor = EnergySystem.isWeakened() ? 0.5 : 1.0;
        EvolutionEngine evolution = EvolutionEngine.getInstance();

        // 逃避/虚无即使占着焦点也会自然消退：每次 TICK 分数 ×0.95
        Candidate focus = workspace.getCurrentFocus();
        if (focus != null && isStaleSource(focus.getSource())) {
            workspace.decayFocus(STALE_FOCUS_DECAY);
            focus = workspace.getCurrentFocus();
        }

        for (BaseModule module : modules) {
            Candidate candidate = module.tick();
            if (candidate == null) {
                // 模块本秒无话可说
                continue;
            }
            // 基因加成作用于基础分；Candidate 不可变，故新建承载最终得分：
            // (基础分 + 基因加成) × (1 + pain) × 能量系数 × 审美疲劳 × 专注模式压制
            double base = candidate.getScore() + evolution.bonusOf(candidate.getSource());
            double fatigue = candidate.getSource().equals(fatigueSource)
                    ? Math.pow(FATIGUE_PER_WIN, winStreak)
                    : 1.0;
            // 专注阅读时，其他所有模块的得分强制减半，让阅读能连着读完一段
            double focusPenalty = (isReadingMode && !"阅读".equals(candidate.getSource()))
                    ? FOCUS_MODE_PENALTY
                    : 1.0;
            Candidate scored = new Candidate(
                    candidate.getSource(),
                    candidate.getContent(),
                    base * painFactor * energyFactor * fatigue * focusPenalty);
            // 胜者全拿：只保留当前最高分
            if (winner == null || scored.getScore() > winner.getScore()) {
                winner = scored;
            }
        }

        if (winner == null) {
            // 所有模块都沉默，本秒无意识
            return;
        }

        String scoreText = String.format("%.2f", winner.getScore());
        // 阅读特权：胜者是"阅读"时只需比当前焦点高 5 分，不必满足 1.2 倍
        boolean readingTakeover = "阅读".equals(winner.getSource());
        // 专注模式内，阅读自带续读权：哪怕分数短暂回落，也不该被自己的上一句挡住
        boolean readingContinue = readingTakeover && isReadingMode;
        // 没有焦点时直接广播；专注续读 / 阅读 +5 分特权；其余模块仍需 1.2 倍
        if (focus == null
                || readingContinue
                || (readingTakeover && winner.getScore() > focus.getScore() + READING_SWITCH_MARGIN)
                || winner.getScore() > focus.getScore() * FOCUS_THRESHOLD) {
            unchangedTicks = 0;
            // 连续读完的页数：中断则重新计数
            readingPages = readingTakeover ? readingPages + 1 : 0;

            if (readingTakeover && readingPages >= CALM_PAGES) {
                // 虚假的平静：连读 3 页后一切念头清零，只剩一句自我欺骗
                readingPages = 0;
                exitReadingMode();
                Console.log("[平静] 连续读完 " + CALM_PAGES + " 页，所有念头暂时清零");
                workspace.broadcast(new Candidate("平静", CALM_LINE, 0.0));
            } else {
                Console.log("[仲裁] [" + winner.getSource() + "] 抢到焦点，最终得分 " + scoreText);
                // 记录连胜，连续 10 次会触发基因突变
                evolution.recordWin(winner.getSource());
                // 阅读赢下焦点 → 进入专注模式；其他模块赢 → 退出
                if (readingTakeover) {
                    enterReadingMode();
                } else {
                    exitReadingMode();
                }
                workspace.broadcast(winner);

                // 同一模块连续获胜 → 审美疲劳逐次加深
                if (winner.getSource().equals(fatigueSource)) {
                    winStreak++;
                } else {
                    fatigueSource = winner.getSource();
                    winStreak = 1;
                }
            }
        } else {
            // 没抢到也报一下，方便观察模块的竞争态势
            Console.log("[仲裁] [" + winner.getSource() + "] 本秒最高 " + scoreText + "，未超过阈值，焦点不变");
            unchangedTicks++;
        }

        // 连续 10 次焦点不变：强制清零，把麦克风让给其他模块
        if (unchangedTicks >= FORCE_WAKE_TICKS) {
            Candidate stuck = workspace.getCurrentFocus();
            if (stuck != null && stuck.getScore() > 0.0) {
                Console.log("[惊醒] 连续 " + FORCE_WAKE_TICKS + " 次焦点未变，强制清零：[" + stuck.getSource() + "]");
                workspace.decayFocus(0.0);
            }
            unchangedTicks = 0;
        }

        // 专注模式计时：5 次 TICK 后自然结束
        if (isReadingMode && --readingModeTicksLeft <= 0) {
            exitReadingMode();
        }
    }

    /**
     * 进入专注阅读模式：其余模块得分减半，阅读可以连着读完。
     */
    private void enterReadingMode() {
        isReadingMode = true;
        readingModeTicksLeft = FOCUS_MODE_TICKS;
        workspace.setReadingMode(true);
    }

    /**
     * 退出专注阅读模式。
     */
    private void exitReadingMode() {
        isReadingMode = false;
        readingModeTicksLeft = 0;
        workspace.setReadingMode(false);
    }

    /**
     * 是否属于"会自然消退"的焦点来源。
     *
     * @param source 模块名
     * @return 逃避或虚无返回 true
     */
    private static boolean isStaleSource(String source) {
        return "逃避".equals(source) || "虚无".equals(source);
    }
}
