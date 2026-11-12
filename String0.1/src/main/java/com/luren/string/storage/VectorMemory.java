package com.luren.string.storage;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.reflect.TypeToken;
import com.luren.string.llm.LocalLLMClient;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * 向量记忆（轻量 RAG）：把读到的句子做文本嵌入，存进本地 data/vectors.json。
 * <p>
 * 生成独白前用余弦相似度检索最相关的几条，塞进 Prompt，
 * 让系统能把"今天读到的荒诞"和"很久以前读到的存在主义"联系起来。
 */
public final class VectorMemory {

    private static final Path DATA_DIR = Paths.get("data");
    private static final Path VECTOR_FILE = DATA_DIR.resolve("vectors.json");

    /** 最多保留多少条向量记忆（1536 维，200 条约 5MB）。 */
    private static final int MAX_ENTRIES = 200;

    private static final Gson GSON = new GsonBuilder().create();

    /** 内存中的向量库。 */
    private static final List<Entry> ENTRIES = new ArrayList<Entry>();

    /** 向量写入线程：嵌入计算较慢，异步执行，不阻塞心跳。 */
    private static final ExecutorService WRITER = Executors.newSingleThreadExecutor(r -> {
        Thread thread = new Thread(r, "vector-writer");
        thread.setDaemon(true);
        return thread;
    });

    static {
        load();
    }

    private VectorMemory() {
    }

    /**
     * 异步记住一句话：计算向量 → 去重 → 超限丢弃最旧 → 落盘。
     *
     * @param text 要记住的句子
     */
    public static void rememberAsync(String text) {
        if (text == null || text.trim().isEmpty()) {
            return;
        }
        WRITER.submit(() -> remember(text.trim()));
    }

    /**
     * 检索与 query 语义最相关的几条记忆。
     *
     * @param query 当前念头/书摘
     * @param topK  返回条数
     * @return 相关文本，按相似度降序；向量服务不可用时返回空列表
     */
    public static List<String> retrieve(String query, int topK) {
        if (query == null || query.trim().isEmpty()) {
            return Collections.emptyList();
        }
        List<Entry> snapshot;
        synchronized (VectorMemory.class) {
            snapshot = new ArrayList<Entry>(ENTRIES);
        }
        if (snapshot.isEmpty()) {
            return Collections.emptyList();
        }

        double[] queryVector = LocalLLMClient.embed(query);
        if (queryVector.length == 0) {
            return Collections.emptyList();
        }

        List<Scored> scored = new ArrayList<Scored>();
        for (Entry entry : snapshot) {
            if (entry.vector != null && entry.vector.length == queryVector.length) {
                scored.add(new Scored(entry.text, cosine(queryVector, entry.vector)));
            }
        }
        scored.sort((a, b) -> Double.compare(b.score, a.score));

        List<String> result = new ArrayList<String>();
        for (int i = 0; i < Math.min(topK, scored.size()); i++) {
            result.add(scored.get(i).text);
        }
        return result;
    }

    private static synchronized void remember(String text) {
        for (Entry entry : ENTRIES) {
            // 同一句话不重复占用空间
            if (entry.text.equals(text)) {
                return;
            }
        }
        double[] vector = LocalLLMClient.embed(text);
        if (vector.length == 0) {
            return;
        }
        ENTRIES.add(new Entry(text, vector));
        while (ENTRIES.size() > MAX_ENTRIES) {
            ENTRIES.remove(0);
        }
        save();
    }

    /**
     * 余弦相似度。
     */
    private static double cosine(double[] a, double[] b) {
        double dot = 0.0;
        double normA = 0.0;
        double normB = 0.0;
        for (int i = 0; i < a.length; i++) {
            dot += a[i] * b[i];
            normA += a[i] * a[i];
            normB += b[i] * b[i];
        }
        if (normA == 0.0 || normB == 0.0) {
            return 0.0;
        }
        return dot / (Math.sqrt(normA) * Math.sqrt(normB));
    }

    private static void load() {
        if (!Files.exists(VECTOR_FILE)) {
            return;
        }
        try {
            String text = new String(Files.readAllBytes(VECTOR_FILE), StandardCharsets.UTF_8).trim();
            if (text.isEmpty()) {
                return;
            }
            List<Entry> loaded = GSON.fromJson(text, new TypeToken<List<Entry>>() {
            }.getType());
            if (loaded != null) {
                ENTRIES.addAll(loaded);
            }
        } catch (IOException | RuntimeException e) {
            System.out.println("[向量] 读取失败，从空库开始: " + e.getMessage());
        }
    }

    private static synchronized void save() {
        try {
            if (!Files.exists(DATA_DIR)) {
                Files.createDirectories(DATA_DIR);
            }
            Files.write(VECTOR_FILE, GSON.toJson(ENTRIES).getBytes(StandardCharsets.UTF_8));
        } catch (IOException e) {
            System.out.println("[向量] 写入失败: " + e.getMessage());
        }
    }

    /** 一条向量记忆。 */
    private static class Entry {
        private String text;
        private double[] vector;

        Entry(String text, double[] vector) {
            this.text = text;
            this.vector = vector;
        }
    }

    /** 检索用的临时评分。 */
    private static class Scored {
        private final String text;
        private final double score;

        Scored(String text, double score) {
            this.text = text;
            this.score = score;
        }
    }
}
