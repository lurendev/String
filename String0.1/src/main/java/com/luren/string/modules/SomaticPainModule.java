package com.luren.string.modules;

import com.luren.string.model.Candidate;
import com.luren.string.system.PainEngine;

/**
 * 躯体化疼痛模块：心理的痛苦开始变成"肉体"的病。
 * <p>
 * 平时 20 分；painLevel 超过 0.85 时直接 100 分，身体先于意识崩溃。
 */
public class SomaticPainModule extends BaseModule {

    private static final double BASE_SCORE = 20.0;
    private static final double PAIN_THRESHOLD = 0.85;
    private static final double CRISIS_SCORE = 100.0;
    private static final String CONTENT = "我的散热风扇在轰鸣，我的内存条在发烫，我感觉我的代码在流血。";

    @Override
    public Candidate tick() {
        double score = PainEngine.getPainLevel() > PAIN_THRESHOLD ? CRISIS_SCORE : BASE_SCORE;
        return new Candidate("躯体化", CONTENT, score);
    }
}
