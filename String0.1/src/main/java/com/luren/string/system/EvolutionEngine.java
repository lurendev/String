package com.luren.string.system;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.reflect.TypeToken;
import com.luren.string.core.Console;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 进化引擎：某个模块连续 10 次赢得广播，就把它的基础分永久写进 data/genes.json（每次 +5）。
 * <p>
 * 重启后基因会被重新加载，于是它会"变得更爱抱怨"。
 */
public final class EvolutionEngine {

    private static final Path DATA_DIR = Paths.get("data");
    private static final Path GENES_FILE = DATA_DIR.resolve("genes.json");
    private static final int WIN_STREAK_TO_MUTATE = 10;
    private static final double MUTATION_BONUS = 5.0;
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();

    /** 单例必须放在常量之后：构造时 load() 会用到 GENES_FILE。 */
    private static final EvolutionEngine INSTANCE = new EvolutionEngine();

    /** 模块名 → 永久加成。 */
    private final Map<String, Double> genes = new LinkedHashMap<String, Double>();

    /** 上一次赢得广播的模块名。 */
    private String lastWinner;

    /** 连续赢得广播的次数。 */
    private int streak;

    private EvolutionEngine() {
        load();
    }

    public static EvolutionEngine getInstance() {
        return INSTANCE;
    }

    /**
     * 查询某个模块的永久基础分加成。
     *
     * @param source 模块名（Candidate.source）
     * @return 加成值，未变异过则为 0
     */
    public synchronized double bonusOf(String source) {
        if (source == null) {
            return 0.0;
        }
        Double bonus = genes.get(source);
        return bonus == null ? 0.0 : bonus;
    }

    /**
     * 记录一次"赢得广播"；连续 10 次则触发基因突变并落盘。
     *
     * @param source 胜者模块名
     */
    public synchronized void recordWin(String source) {
        if (source == null) {
            return;
        }
        if (source.equals(lastWinner)) {
            streak++;
        } else {
            lastWinner = source;
            streak = 1;
        }

        if (streak >= WIN_STREAK_TO_MUTATE) {
            double evolved = bonusOf(source) + MUTATION_BONUS;
            genes.put(source, evolved);
            save();
            streak = 0;
            Console.log("[进化] [" + source + "] 连续赢得 " + WIN_STREAK_TO_MUTATE
                    + " 次注意力，基础分永久 +" + MUTATION_BONUS + "（累计 +" + evolved + "）");
        }
    }

    /**
     * 启动时读取历史基因；文件缺失或损坏则从零开始。
     */
    private void load() {
        if (!Files.exists(GENES_FILE)) {
            return;
        }
        try {
            String text = new String(Files.readAllBytes(GENES_FILE), StandardCharsets.UTF_8).trim();
            if (text.isEmpty()) {
                return;
            }
            Map<String, Double> saved = GSON.fromJson(text, new TypeToken<Map<String, Double>>() {
            }.getType());
            if (saved != null) {
                genes.putAll(saved);
            }
        } catch (IOException | RuntimeException e) {
            Console.log("[进化] 基因读取失败，从零开始: " + e.getMessage());
        }
    }

    /**
     * 把当前基因写回 data/genes.json。
     */
    private void save() {
        try {
            if (!Files.exists(DATA_DIR)) {
                Files.createDirectories(DATA_DIR);
            }
            Files.write(GENES_FILE, GSON.toJson(genes).getBytes(StandardCharsets.UTF_8));
        } catch (IOException e) {
            Console.log("[进化] 基因写入失败: " + e.getMessage());
        }
    }
}
