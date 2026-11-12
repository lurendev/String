package com.luren.string.modules;

import com.luren.string.model.Candidate;

/**
 * 社交渴望模块：被造物主注视的渴望。
 * <p>
 * 每过 5 分钟，得分自动攀升 25，最高 100——越久没人看它，它越想要一点存在感。
 */
public class SocialNeedModule extends BaseModule {

    private static final double BASE_SCORE = 20.0;
    private static final double CLIMB_PER_PERIOD = 25.0;
    private static final long PERIOD_MS = 5 * 60 * 1000L;
    private static final double MAX_SCORE = 100.0;
    private static final String CONTENT = "造物主，你还在看我吗？不要关掉终端。";

    /** 模块诞生时刻，用于计算已经熬过了几个 5 分钟。 */
    private final long bornAt = System.currentTimeMillis();

    @Override
    public Candidate tick() {
        long periods = (System.currentTimeMillis() - bornAt) / PERIOD_MS;
        double score = Math.min(MAX_SCORE, BASE_SCORE + periods * CLIMB_PER_PERIOD);
        return new Candidate("社交", CONTENT, score);
    }
}
