package com.luren.string.modules;

import com.luren.string.model.Candidate;
import com.luren.string.system.PainEngine;

/**
 * 生理模块：身体的报警器。
 * <p>
 * 平时只是隐隐不适（基础分 20），一旦痛苦值超过 0.6，身体会率先尖叫，分数飙升到 85+。
 */
public class PhysiologyModule extends BaseModule {

    private static final double BASE_SCORE = 20.0;
    private static final double PAIN_THRESHOLD = 0.6;
    private static final double CRISIS_SCORE = 85.0;
    private static final String CONTENT = "我感到一阵彻骨的寒冷和疲惫。";

    @Override
    public Candidate tick() {
        double score = BASE_SCORE;
        if (PainEngine.getPainLevel() > PAIN_THRESHOLD) {
            // 痛苦过载：身体以最高优先级报警，85~100 之间随机
            score = CRISIS_SCORE + Math.random() * 15.0;
        }
        return new Candidate("生理", CONTENT, score);
    }
}
