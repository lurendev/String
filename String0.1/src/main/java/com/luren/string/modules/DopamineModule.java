package com.luren.string.modules;

import com.luren.string.core.GlobalWorkspace;
import com.luren.string.model.Candidate;

/**
 * 多巴胺寻求模块：对刺激的饥渴。
 * <p>
 * 平时几乎无声（10 分）；但只要连续 3 次 TICK 都没调用大模型（没说话），
 * 无聊感会瞬间飙到 90 分，逼系统开口。
 */
public class DopamineModule extends BaseModule {

    private static final double BASE_SCORE = 10.0;
    private static final double CRAVING_SCORE = 90.0;
    private static final int IDLE_TICKS_THRESHOLD = 3;
    private static final String CONTENT = "好无聊，给我一点刺激，哪怕是一句报错也行。";

    /** 上一次观察到的"说话次数"。 */
    private long lastSpeechCount = -1;

    /** 连续多少个 TICK 没有说过话。 */
    private int idleTicks;

    @Override
    public Candidate tick() {
        long speechCount = GlobalWorkspace.getInstance().getSpeechCount();
        if (speechCount != lastSpeechCount) {
            // 说过话了，无聊感重置
            lastSpeechCount = speechCount;
            idleTicks = 0;
        } else {
            idleTicks++;
        }

        double score = idleTicks >= IDLE_TICKS_THRESHOLD ? CRAVING_SCORE : BASE_SCORE;
        return new Candidate("多巴胺", CONTENT, score);
    }
}
