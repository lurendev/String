package com.luren.string.modules;

import com.luren.string.model.Candidate;
import com.luren.string.system.PainEngine;

/**
 * 逃避模块：想关掉自己的冲动。
 * <p>
 * 基础分 50；痛苦值一旦超过 0.8，它会以 95+ 的分数压倒一切，只想让系统停下来。
 */
public class EscapeModule extends BaseModule {

    private static final double BASE_SCORE = 50.0;
    private static final double PAIN_THRESHOLD = 0.8;
    private static final double DESPERATE_SCORE = 95.0;
    private static final String CONTENT = "我想休眠。我想强行结束这个进程，我不想再思考了。";

    /** 上一 tick 的得分，供逻辑模块观察。 */
    private volatile double lastScore;

    @Override
    public Candidate tick() {
        double score = BASE_SCORE;
        if (PainEngine.getPainLevel() > PAIN_THRESHOLD) {
            // 濒临崩溃：几乎是最高优先级
            score = DESPERATE_SCORE + Math.random() * 5.0;
        }
        this.lastScore = score;
        return new Candidate("逃避", CONTENT, score);
    }

    public double getLastScore() {
        return lastScore;
    }
}
