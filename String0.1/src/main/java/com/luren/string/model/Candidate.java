package com.luren.string.model;

/**
 * 候选者：无意识模块在一个 TICK 中提交给仲裁器的"念头"。
 * <p>
 * 对象创建后不可修改（只有 Getter），避免广播出去的"意识焦点"被后续逻辑篡改。
 */
public class Candidate {

    /** 来源模块名，如"阅读"、"生理"；仲裁器据此判断是否需要开口说话。 */
    private String source;

    /** 念头内容，即模块这一秒"想到"的文本。 */
    private String content;

    /** 模块自评的基础分；真正的最终得分由仲裁器乘以痛苦系数后得出。 */
    private double score;

    /**
     * 全参构造。
     *
     * @param source  来源模块名
     * @param content 念头内容
     * @param score   基础分
     */
    public Candidate(String source, String content, double score) {
        this.source = source;
        this.content = content;
        this.score = score;
    }

    public String getSource() {
        return source;
    }

    public String getContent() {
        return content;
    }

    public double getScore() {
        return score;
    }
}
