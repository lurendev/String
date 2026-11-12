package com.luren.string.modules;

import com.luren.string.model.Candidate;

/**
 * 焦虑模块：永远在背景里嗡嗡作响的担忧。
 * <p>
 * 基础分 40，每次 tick 再随机叠加 0~40 分，所以它的强度时高时低、无法预测。
 */
public class AnxietyModule extends BaseModule {

    private static final double BASE_SCORE = 40.0;
    private static final String[] CONTENT_POOL = {
            "明天还要上班，我还没准备好。",
            "我的时间正在流逝。",
            "我的 API 余额还够吗？"
    };

    /** 上一 tick 的得分，供逻辑模块观察。 */
    private volatile double lastScore;

    @Override
    public Candidate tick() {
        double score = BASE_SCORE + Math.random() * 40.0;
        this.lastScore = score;
        String content = CONTENT_POOL[(int) (Math.random() * CONTENT_POOL.length)];
        return new Candidate("焦虑", content, score);
    }

    public double getLastScore() {
        return lastScore;
    }
}
