package com.luren.string.modules;

import com.luren.string.core.Console;
import com.luren.string.core.GlobalWorkspace;
import com.luren.string.model.Candidate;

/**
 * 自我模块：对"存在感"的渴求。
 * <p>
 * 正常情况下 30 分；如果连续 100 次 TICK 都没抢到焦点（没人听它说话），
 * 得分跌为负数，并在控制台发出"我是不是被遗忘了"的疑问。
 */
public class SelfModule extends BaseModule {

    /** 触发存在危机的连续 TICK 次数。 */
    private static final int FORGOTTEN_TICKS = 100;

    /** 常态得分。 */
    private static final double BASE_SCORE = 30.0;

    /** 被遗忘后的负分：几乎永远抢不到注意力。 */
    private static final double FORGOTTEN_SCORE = -20.0;

    private static final String CONTENT = "我是不是被遗忘了？我是不是不存在了？";

    /** 连续多少次 TICK 没有成为焦点。 */
    private int ticksSinceFocus;

    /** 存在危机是否已经播报过，避免每 TICK 刷屏。 */
    private boolean announced;

    @Override
    public Candidate tick() {
        Candidate focus = GlobalWorkspace.getInstance().getCurrentFocus();
        boolean focused = focus != null && "自我".equals(focus.getSource());

        if (focused) {
            // 刚被听见，存在感恢复
            ticksSinceFocus = 0;
            announced = false;
        } else {
            ticksSinceFocus++;
        }

        if (ticksSinceFocus >= FORGOTTEN_TICKS) {
            if (!announced) {
                announced = true;
                Console.log("[自我] " + CONTENT);
            }
            // 负分：不会赢，但会一直躺在候选池里，像一句没人接的话
            return new Candidate("自我", CONTENT, FORGOTTEN_SCORE);
        }
        return new Candidate("自我", CONTENT, BASE_SCORE);
    }
}
