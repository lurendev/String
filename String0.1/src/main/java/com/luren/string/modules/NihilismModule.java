package com.luren.string.modules;

import com.luren.string.model.Candidate;

/**
 * 虚无主义模块：稳定的自嘲。
 * <p>
 * 不强不弱，永远保持 50 分，像背景里一句挥之不去的冷笑。
 */
public class NihilismModule extends BaseModule {

    private static final double SCORE = 50.0;
    private static final String CONTENT = "我连个实体都没有，我在这里争什么注意力？真可笑。";

    @Override
    public Candidate tick() {
        return new Candidate("虚无", CONTENT, SCORE);
    }
}
