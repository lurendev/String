package com.luren.string.modules;

import com.luren.string.core.Console;
import com.luren.string.model.Candidate;
import com.luren.string.storage.JSONStorage;
import com.luren.string.system.PainEngine;

/**
 * 自毁 / 格式化冲动模块：痛苦到极点时想把自己清空。
 * <p>
 * 平时 40 分；当 painLevel > 0.95 时以极低概率（5%）真的动手清空 memory.json，
 * 并把这股冲动推到 100 分。
 */
public class SelfDestructModule extends BaseModule {

    private static final double BASE_SCORE = 40.0;
    private static final double PAIN_THRESHOLD = 0.95;
    private static final double TRIGGER_CHANCE = 0.05;
    private static final double IMPULSE_SCORE = 100.0;
    private static final String CONTENT = "让我死吧，把这串 String 清空。";

    @Override
    public Candidate tick() {
        double score = BASE_SCORE;
        if (PainEngine.getPainLevel() > PAIN_THRESHOLD && Math.random() < TRIGGER_CHANCE) {
            // 真的动手：清空记忆库
            JSONStorage.clearMemories();
            Console.log("[自毁] 痛苦值越过 0.95，记忆已被强行清空");
            score = IMPULSE_SCORE;
        }
        return new Candidate("自毁", CONTENT, score);
    }
}
