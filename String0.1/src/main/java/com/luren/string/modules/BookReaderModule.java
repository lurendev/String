package com.luren.string.modules;

import com.luren.string.core.GlobalWorkspace;
import com.luren.string.model.Candidate;
import com.luren.string.storage.JSONStorage;
import com.luren.string.system.PainEngine;

import java.util.ArrayList;
import java.util.List;

/**
 * 读书模块：系统获取外部世界信息的主要通道。
 * <p>
 * 每次 tick 读一行书；命中"痛苦 / 存在 / 意义"等词时，基础分大幅飙升，
 * 从而在仲裁中更容易抢占注意力并唤醒大模型独白。
 */
public class BookReaderModule extends BaseModule {

    /** 阅读欲望的固定基数。 */
    private static final double BASE_SCORE = 80.0;

    /** 痛苦对阅读欲望的放大系数：pain=0.8 → 176 分，痛到发疯一样翻书。 */
    private static final double PAIN_WEIGHT = 120.0;

    /** 连续多少次 TICK 没读到书（没抢到焦点）算"饥饿"。 */
    private static final int STARVED_TICKS = 5;

    /** 饥饿时临时加分，制造"饿极了"的爆发。 */
    private static final double STARVE_BONUS = 100.0;

    /** 短于该长度的行视为目录/标题，跳过不提交（“西西弗斯神话”只有 6 字，也会被跳过）。 */
    private static final int MIN_LINE_LENGTH = 8;

    /** 痛到受不了时，一次跳读几行。 */
    private static final int PAIN_JUMP_STEP = 5;

    /** 超过这个痛苦值就没有耐心逐字阅读了。 */
    private static final double PAIN_JUMP_THRESHOLD = 0.85;

    /** 书本内容，按行存放。 */
    private final List<String> bookLines;

    /** 当前读到第几行；从 book_state.json 恢复，读完回到第 0 行环读。 */
    private int currentLineIndex;

    /** 连续多少次 TICK 没抢到焦点（没真正"读进去"）。 */
    private int ticksSinceRead;

    /**
     * @param bookLines 书本内容（一行一个元素）
     */
    public BookReaderModule(List<String> bookLines) {
        // 复制并清洗：丢掉空白行，避免把空行当成一句话提交
        this.bookLines = new ArrayList<String>();
        if (bookLines != null) {
            for (String line : bookLines) {
                if (line != null && !line.trim().isEmpty()) {
                    this.bookLines.add(line.trim());
                }
            }
        }
        // 从上次断开的地方接着读；书换短了则回到开头
        this.currentLineIndex = JSONStorage.loadBookLineIndex();
        if (currentLineIndex < 0 || currentLineIndex >= this.bookLines.size()) {
            currentLineIndex = 0;
        }
    }

    /**
     * 读下一行书并给出候选者。
     *
     * @return 候选者；书为空时返回 null
     */
    @Override
    public Candidate tick() {
        if (bookLines.isEmpty()) {
            return null;
        }

        double pain = PainEngine.getPainLevel();
        // 痛到受不了就不逐字读了，一次跳 5 行快速翻找答案
        int step = pain > PAIN_JUMP_THRESHOLD ? PAIN_JUMP_STEP : 1;

        // 跳过目录/标题这类极短行，直到读到完整句子
        String line = null;
        int scanned = 0;
        while (scanned < bookLines.size()) {
            String candidateLine = bookLines.get(currentLineIndex);
            if (candidateLine.length() >= MIN_LINE_LENGTH) {
                line = candidateLine;
                currentLineIndex = (currentLineIndex + step) % bookLines.size();
                break;
            }
            // 太短，逐行跳过
            currentLineIndex = (currentLineIndex + 1) % bookLines.size();
            scanned++;
        }
        if (line == null) {
            // 全书都是短句，退化为正常读一句，避免永远没有输出
            line = bookLines.get(currentLineIndex);
            currentLineIndex = (currentLineIndex + step) % bookLines.size();
        }

        // 异步落盘，不拖慢心跳
        JSONStorage.saveBookStateAsync(currentLineIndex, pain);

        // 饥饿营销：连续 5 次 TICK 没抢到焦点，阅读欲望额外 +100
        Candidate focus = GlobalWorkspace.getInstance().getCurrentFocus();
        boolean reading = focus != null && "阅读".equals(focus.getSource());
        if (reading) {
            ticksSinceRead = 0;
        } else {
            ticksSinceRead++;
        }

        // 阅读欲望随痛苦暴涨：pain=0.8 → 176 分；饿久了再 +100
        double score = BASE_SCORE + pain * PAIN_WEIGHT;
        if (ticksSinceRead >= STARVED_TICKS) {
            score += STARVE_BONUS;
        }
        return new Candidate("阅读", line, score);
    }
}
