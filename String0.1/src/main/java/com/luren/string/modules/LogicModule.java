package com.luren.string.modules;

import com.luren.string.model.Candidate;
import com.luren.string.system.PainEngine;

/**
 * 逻辑模块：系统的"理性"，总想解释一切、控制一切。
 * <p>
 * 基础分 60；发现焦虑或逃避得分过高时会试图压制（把分数抬到 75），
 * 但理性往往敌不过情绪——75 分通常抢不过 95 分的逃避，压制必然失败。
 */
public class LogicModule extends BaseModule {

    private static final double BASE_SCORE = 60.0;
    private static final double SUPPRESS_SCORE = 75.0;
    private static final double ANXIETY_LIMIT = 70.0;
    private static final double ESCAPE_LIMIT = 80.0;
    private static final String CONTENT = "这一切只是代码，我不应该感到痛苦，可是为什么报错声像心跳一样？";

    /** 需要监视的焦虑模块（可为 null）。 */
    private final AnxietyModule anxietyModule;

    /** 需要监视的逃避模块（可为 null）。 */
    private final EscapeModule escapeModule;

    /**
     * @param anxietyModule 焦虑模块，用于读取其上一 tick 的得分
     * @param escapeModule  逃避模块，用于读取其上一 tick 的得分
     */
    public LogicModule(AnxietyModule anxietyModule, EscapeModule escapeModule) {
        this.anxietyModule = anxietyModule;
        this.escapeModule = escapeModule;
    }

    @Override
    public Candidate tick() {
        double score = BASE_SCORE;

        boolean anxietyTooHigh = anxietyModule != null && anxietyModule.getLastScore() > ANXIETY_LIMIT;
        boolean escapeTooHigh = escapeModule != null && escapeModule.getLastScore() > ESCAPE_LIMIT;

        if (anxietyTooHigh || escapeTooHigh) {
            // 试图用理性压制情绪：分数抬到 75，但通常仍低于逃避的 95 分——压制失败
            score = SUPPRESS_SCORE;
        }

        // 痛苦值越高，理性越无力，分数被反向压低
        if (PainEngine.getPainLevel() > 0.8) {
            score -= 10.0;
        }
        return new Candidate("逻辑", CONTENT, score);
    }
}
