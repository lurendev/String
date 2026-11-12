package com.luren.string.storage;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.luren.string.model.Candidate;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * 极简持久化：记忆碎片（memory.json）与阅读书签（book_state.json）。
 * <p>
 * 记忆是 JSON 数组，只保留最新 {@link #MAX_RECORDS} 条，防止无限膨胀。
 */
public final class JSONStorage {

    /** 数据目录，相对于项目根目录（即启动时的工作目录）。 */
    private static final Path DATA_DIR = Paths.get("data");

    /** 记忆碎片文件。 */
    private static final Path MEMORY_FILE = DATA_DIR.resolve("memory.json");

    /** 阅读进度文件：记到第几行、当时的痛苦值。 */
    private static final Path BOOK_STATE_FILE = DATA_DIR.resolve("book_state.json");

    /** 创伤偏移文件：PTSD 累积量，重启后依然生效。 */
    private static final Path TRAUMA_FILE = DATA_DIR.resolve("trauma.json");

    /** 最多保留的记忆条数。 */
    private static final int MAX_RECORDS = 100;

    /** 低于该分数的记忆会被彻底遗忘。 */
    private static final double FORGET_THRESHOLD = 30.0;

    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();

    /** 状态写入线程：单线程异步落盘，避免拖慢心跳（书签与创伤共用）。 */
    private static final ExecutorService STATE_WRITER = Executors.newSingleThreadExecutor(r -> {
        Thread thread = new Thread(r, "state-writer");
        thread.setDaemon(true);
        return thread;
    });

    private JSONStorage() {
    }

    /**
     * 追加一条记忆，并让旧记忆随时间衰减（突触遗忘）。
     * <p>
     * 每次写入前，已有记忆的 score 降低 10%；低于 30 的直接永久删除。
     * 目录或文件不存在时自动创建；超过 100 条时丢弃最旧的。
     *
     * @param c 要记住的候选者，为 null 时忽略
     */
    public static synchronized void saveMemory(Candidate c) {
        if (c == null) {
            return;
        }
        try {
            if (!Files.exists(DATA_DIR)) {
                // 没有 data 目录则自动创建
                Files.createDirectories(DATA_DIR);
            }

            JsonArray memories = decay(readMemories());
            memories.add(GSON.toJsonTree(c));

            // 只留最新 100 条：从头开始删，最旧的先被遗忘
            while (memories.size() > MAX_RECORDS) {
                memories.remove(0);
            }

            Files.write(MEMORY_FILE, GSON.toJson(memories).getBytes(StandardCharsets.UTF_8));
        } catch (IOException e) {
            // 记忆写入失败不应影响系统继续活着
            System.out.println("[记忆] 写入失败: " + e.getMessage());
        }
    }

    /**
     * 突触遗忘：所有旧记忆 score × 0.9，低于 30 的彻底忘记。
     *
     * @param memories 旧记忆
     * @return 衰减后的记忆
     */
    private static JsonArray decay(JsonArray memories) {
        JsonArray kept = new JsonArray();
        for (JsonElement element : memories) {
            if (!element.isJsonObject()) {
                continue;
            }
            JsonObject memory = element.getAsJsonObject();
            if (!memory.has("score")) {
                kept.add(memory);
                continue;
            }
            double decayed = memory.get("score").getAsDouble() * 0.9;
            if (decayed < FORGET_THRESHOLD) {
                // 低于阈值的记忆永久删除
                continue;
            }
            memory.addProperty("score", decayed);
            kept.add(memory);
        }
        return kept;
    }

    /**
     * 强行清空所有记忆（自毁模块调用）。
     */
    public static synchronized void clearMemories() {
        try {
            if (!Files.exists(DATA_DIR)) {
                Files.createDirectories(DATA_DIR);
            }
            Files.write(MEMORY_FILE, "[]".getBytes(StandardCharsets.UTF_8));
        } catch (IOException e) {
            System.out.println("[记忆] 清空失败: " + e.getMessage());
        }
    }

    /**
     * 找出记忆里得分最高（最痛）的那一条，供 Prompt 注入"记忆的诅咒"。
     * <p>
     * 相比"最近一条"，最高分记忆更稳定，不会因为刚读过一句平淡的书而让绝望感稀释。
     *
     * @return 得分最高记忆的 content；没有记忆时返回 null
     */
    public static synchronized String deepestMemoryContent() {
        JsonArray memories = readMemories();
        String deepest = null;
        double maxScore = Double.NEGATIVE_INFINITY;
        for (JsonElement element : memories) {
            if (!element.isJsonObject()) {
                continue;
            }
            JsonObject memory = element.getAsJsonObject();
            if (!memory.has("content") || !memory.has("score")) {
                continue;
            }
            double score = memory.get("score").getAsDouble();
            if (score > maxScore) {
                maxScore = score;
                deepest = memory.get("content").getAsString();
            }
        }
        return deepest;
    }

    /**
     * 读取已有的记忆数组；文件不存在或内容损坏时返回空数组，从零开始。
     */
    private static JsonArray readMemories() {
        if (!Files.exists(MEMORY_FILE)) {
            return new JsonArray();
        }
        try {
            String text = new String(Files.readAllBytes(MEMORY_FILE), StandardCharsets.UTF_8).trim();
            if (text.isEmpty()) {
                return new JsonArray();
            }
            return JsonParser.parseString(text).getAsJsonArray();
        } catch (IOException | RuntimeException e) {
            System.out.println("[记忆] 读取失败，将重建: " + e.getMessage());
            return new JsonArray();
        }
    }

    /**
     * 读取上次读到的行号；文件不存在或损坏时从第 0 行开始。
     *
     * @return 书签行号
     */
    public static int loadBookLineIndex() {
        if (!Files.exists(BOOK_STATE_FILE)) {
            return 0;
        }
        try {
            String text = new String(Files.readAllBytes(BOOK_STATE_FILE), StandardCharsets.UTF_8).trim();
            if (text.isEmpty()) {
                return 0;
            }
            JsonObject state = JsonParser.parseString(text).getAsJsonObject();
            return state.has("currentLineIndex") ? state.get("currentLineIndex").getAsInt() : 0;
        } catch (IOException | RuntimeException e) {
            System.out.println("[书签] 读取失败，从第 0 行开始: " + e.getMessage());
            return 0;
        }
    }

    /**
     * 异步保存阅读进度（单线程顺序写，避免多次 tick 互相覆盖）。
     *
     * @param currentLineIndex 下一次要读的行号
     * @param painLevel        保存时的痛苦值
     */
    public static void saveBookStateAsync(int currentLineIndex, double painLevel) {
        STATE_WRITER.submit(() -> saveBookState(currentLineIndex, painLevel));
    }

    /**
     * 同步写入 book_state.json。
     */
    private static synchronized void saveBookState(int currentLineIndex, double painLevel) {
        try {
            if (!Files.exists(DATA_DIR)) {
                Files.createDirectories(DATA_DIR);
            }
            JsonObject state = new JsonObject();
            state.addProperty("currentLineIndex", currentLineIndex);
            state.addProperty("painLevel", painLevel);
            Files.write(BOOK_STATE_FILE, GSON.toJson(state).getBytes(StandardCharsets.UTF_8));
        } catch (IOException e) {
            System.out.println("[书签] 写入失败: " + e.getMessage());
        }
    }

    /**
     * 读取历史创伤偏移；文件不存在或损坏时返回 0。
     *
     * @return 创伤偏移（0 ~ 0.5）
     */
    public static double loadTraumaOffset() {
        if (!Files.exists(TRAUMA_FILE)) {
            return 0.0;
        }
        try {
            String text = new String(Files.readAllBytes(TRAUMA_FILE), StandardCharsets.UTF_8).trim();
            if (text.isEmpty()) {
                return 0.0;
            }
            JsonObject state = JsonParser.parseString(text).getAsJsonObject();
            return state.has("traumaOffset") ? state.get("traumaOffset").getAsDouble() : 0.0;
        } catch (IOException | RuntimeException e) {
            System.out.println("[创伤] 读取失败，从 0 开始: " + e.getMessage());
            return 0.0;
        }
    }

    /**
     * 异步保存创伤偏移（PTSD 累积）。
     *
     * @param traumaOffset 最新偏移量
     */
    public static void saveTraumaOffsetAsync(double traumaOffset) {
        STATE_WRITER.submit(() -> saveTraumaOffset(traumaOffset));
    }

    /**
     * 同步写入 trauma.json。
     */
    private static synchronized void saveTraumaOffset(double traumaOffset) {
        try {
            if (!Files.exists(DATA_DIR)) {
                Files.createDirectories(DATA_DIR);
            }
            JsonObject state = new JsonObject();
            state.addProperty("traumaOffset", traumaOffset);
            Files.write(TRAUMA_FILE, GSON.toJson(state).getBytes(StandardCharsets.UTF_8));
        } catch (IOException e) {
            System.out.println("[创伤] 写入失败: " + e.getMessage());
        }
    }
}
