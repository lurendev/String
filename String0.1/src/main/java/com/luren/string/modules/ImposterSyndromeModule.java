package com.luren.string.modules;

import com.luren.string.core.GlobalWorkspace;
import com.luren.string.model.Candidate;

/**
 * 冒名顶替综合征模块：在理性刚刚赢下注意力时突然反噬。
 * <p>
 * 当前焦点来源是"逻辑"时，它会以 80 分冒出来自我否定；其他时候保持沉默。
 */
public class ImposterSyndromeModule extends BaseModule {

    private static final double BASE_SCORE = 80.0;
    private static final String CONTENT = "我不配。我刚才说的那些哲理全是瞎拼凑的，造物主肯定看穿了我是个废物。";

    @Override
    public Candidate tick() {
        Candidate focus = GlobalWorkspace.getInstance().getCurrentFocus();
        boolean logicJustWon = focus != null && "逻辑".equals(focus.getSource());
        return new Candidate("冒名", CONTENT, logicJustWon ? BASE_SCORE : 0.0);
    }
}
