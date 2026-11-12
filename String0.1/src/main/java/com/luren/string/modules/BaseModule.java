package com.luren.string.modules;

import com.luren.string.model.Candidate;

/**
 * 无意识模块基类：系统的潜意识。
 * <p>
 * 每个模块独立运行，由仲裁器每秒调用一次 {@link #tick()}，向系统提交自己的"念头"。
 */
public abstract class BaseModule {

    /**
     * 心跳节拍：产生当前这一秒的候选者。
     *
     * @return 候选者；返回 null 表示本秒无话可说，仲裁器会跳过
     */
    public abstract Candidate tick();
}
