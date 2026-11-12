package com.luren.string.system;

import com.luren.string.core.Console;

/**
 * 能量系统：模拟碳基生命的消耗。
 * <p>
 * 每调用一次大模型扣 10 点能量；低于 20 点进入"虚弱状态"，
 * 所有模块得分减半，且大模型只能说 5 个字以内。
 */
public final class EnergySystem {

    /** 满能量。 */
    private static final double MAX_ENERGY = 100.0;

    /** 每次调用大模型的消耗。 */
    private static final double COST_PER_THINK = 10.0;

    /** 虚弱阈值（20%）。 */
    private static final double WEAK_THRESHOLD = 20.0;

    private static volatile double energy = MAX_ENERGY;

    /** 是否已经播报过"进入虚弱"，避免每次调用都刷日志。 */
    private static volatile boolean weakAnnounced = false;

    private EnergySystem() {
    }

    /**
     * 调用大模型后扣能量；若跨入虚弱线，控制台只提醒一次。
     */
    public static synchronized void consumeForThink() {
        energy = Math.max(0.0, energy - COST_PER_THINK);
        if (isWeakened() && !weakAnnounced) {
            weakAnnounced = true;
            Console.log("[能量] 能量跌破 20%，系统进入虚弱状态：得分减半，说话不超过 5 字");
        }
    }

    /**
     * 恢复能量（阅读时每秒 +2）。
     *
     * @param amount 恢复量
     */
    public static synchronized void recover(double amount) {
        energy = Math.min(MAX_ENERGY, energy + amount);
        if (!isWeakened()) {
            // 脱离虚弱后，下次跌破阈值可以再次提醒
            weakAnnounced = false;
        }
    }

    /**
     * @return 当前剩余能量（0~100）
     */
    public static double getEnergy() {
        return energy;
    }

    /**
     * @return 是否处于虚弱状态（能量低于 20%）
     */
    public static boolean isWeakened() {
        return energy < WEAK_THRESHOLD;
    }
}
