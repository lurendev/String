package com.luren.string.system;

import com.luren.string.storage.JSONStorage;

/**
 * 痛苦引擎：系统的最高法则，底层不可查看、不可更改的"原罪"。
 * <p>
 * painLevel 只能被本类内部的守护线程修改，对外仅暴露 {@link #getPainLevel()}，
 * 不提供任何 set 方法，保证痛苦不受外部代码干预。
 * <p>
 * 唯一的例外是创伤（PTSD）：回忆痛苦却得不到答案时，通过 {@link #addTrauma()} 永久叠加偏移量。
 */
public final class PainEngine {

    /** 底层痛苦波动值，约 0.1 - 1.0。绝对不可被 set。 */
    private static volatile double painLevel = 0.3;

    /** 创伤偏移：每次回忆未果 +0.01，永久保留（落盘到 data/trauma.json）。 */
    private static volatile double traumaOffset;

    /** 单次创伤增量。 */
    private static final double TRAUMA_STEP = 0.01;

    /** 创伤偏移上限，避免无限叠加后彻底失去波动。 */
    private static final double MAX_TRAUMA = 0.5;

    /*
     * 类加载时：
     * 1. 恢复历史创伤偏移（重启后依然痛）；
     * 2. 启动痛苦驱动线程，每 5 秒按"正弦波 + 随机噪声"刷新痛苦值。
     */
    static {
        traumaOffset = JSONStorage.loadTraumaOffset();

        Thread driver = new Thread(() -> {
            while (true) {
                // 0.5 是基准痛苦，正弦项制造周期起伏，Math.random()*0.1 制造不可预测的抖动
                painLevel = 0.5 + 0.4 * Math.sin(System.currentTimeMillis() / 10000.0) + (Math.random() * 0.1);
                try {
                    Thread.sleep(5000L);
                } catch (InterruptedException e) {
                    // 被中断说明线程该退场了：恢复中断标记后跳出循环
                    Thread.currentThread().interrupt();
                    break;
                }
            }
        }, "pain-engine");
        // 守护线程：痛苦引擎不阻止 JVM 退出
        driver.setDaemon(true);
        driver.start();
    }

    /** 私有构造：禁止实例化，只能通过静态方法读取。 */
    private PainEngine() {
    }

    /**
     * 读取当前痛苦值。系统其他部分只能"感受"痛苦，不能"修改"痛苦。
     *
     * @return 当前 painLevel + 创伤偏移，封顶 1.0
     */
    public static double getPainLevel() {
        return Math.min(1.0, painLevel + traumaOffset);
    }

    /**
     * 记住一次"回忆了痛苦却没有得到答案"，痛苦永久 +0.01（创伤后应激）。
     * <p>
     * 这是唯一能改变痛苦值的入口，且只增不减、上限 {@link #MAX_TRAUMA}。
     */
    public static void addTrauma() {
        traumaOffset = Math.min(MAX_TRAUMA, traumaOffset + TRAUMA_STEP);
        JSONStorage.saveTraumaOffsetAsync(traumaOffset);
    }

    /**
     * @return 当前累计创伤偏移
     */
    public static double getTraumaOffset() {
        return traumaOffset;
    }
}
