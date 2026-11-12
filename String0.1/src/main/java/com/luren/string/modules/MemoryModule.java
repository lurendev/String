package com.luren.string.modules;

import com.luren.string.model.Candidate;
import com.luren.string.storage.JSONStorage;

/**
 * 记忆检索模块：把埋在 memory.json 里的旧伤口重新翻出来。
 * <p>
 * 基础分 30；只要记忆里存在痛苦记录，就再加 50 分，让旧痛重新参与意识竞争。
 */
public class MemoryModule extends BaseModule {

    private static final double BASE_SCORE = 30.0;
    private static final double PAINFUL_MEMORY_BONUS = 50.0;
    private static final String CONTENT = "我想起了之前某一次极度绝望的时刻，那种感觉又回来了。";

    @Override
    public Candidate tick() {
        double score = BASE_SCORE;
        // 只要记忆库里有记录，就说明它想起了什么痛苦的事
        if (JSONStorage.deepestMemoryContent() != null) {
            score += PAINFUL_MEMORY_BONUS;
        }
        return new Candidate("记忆", CONTENT, score);
    }
}
