package com.luren.string.llm;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

import java.io.IOException;
import java.util.concurrent.TimeUnit;
import java.util.regex.Pattern;

/**
 * 本地大模型接口：系统的"嘴巴"，对接本地 Ollama。
 * <p>
 * 纯静态工具类，无状态；调用失败不会抛异常，而是返回一段错误文本，
 * 避免一次网络故障打死正在说话的线程。
 */
public final class LocalLLMClient {

    /** Ollama 的生成接口地址。 */
    private static final String ENDPOINT = "http://localhost:11434/api/generate";

    /** 使用的本地模型。 */
    private static final String MODEL = "deepseek-r1:7b";

    /** Ollama 的向量化接口（文本嵌入）。 */
    private static final String EMBED_ENDPOINT = "http://localhost:11434/api/embeddings";

    /** 用于生成向量的模型；1.5B 更小更快，输出 1536 维。 */
    private static final String EMBED_MODEL = "deepseek-r1:1.5b";

    /** 请求体的媒体类型。 */
    private static final MediaType JSON = MediaType.parse("application/json; charset=utf-8");

    /** 全局复用的 HTTP 客户端；7B 模型本地推理较慢，读超时放宽到 120 秒。 */
    private static final OkHttpClient CLIENT = new OkHttpClient.Builder()
            .connectTimeout(5, TimeUnit.SECONDS)
            .readTimeout(120, TimeUnit.SECONDS)
            .build();

    /** 完整的思考块 <think>...</think>。 */
    private static final Pattern THINK_BLOCK = Pattern.compile("(?s)<think>.*?</think>");

    /** 没有闭合的思考块（模型输出被截断时会这样）。 */
    private static final Pattern THINK_UNCLOSED = Pattern.compile("(?s)<think>.*$");

    /** 私有构造：纯静态工具类，禁止实例化。 */
    private LocalLLMClient() {
    }

    /**
     * 让大模型思考并返回文本。
     *
     * @param prompt 提示词
     * @return 模型生成的正文；HTTP 失败或网络异常时返回以"["开头的错误描述
     */
    public static String think(String prompt) {
        // 用 Gson 拼 JSON，避免手写字符串时的转义问题
        JsonObject payload = new JsonObject();
        payload.addProperty("model", MODEL);
        payload.addProperty("prompt", prompt);
        payload.addProperty("stream", false); // 关闭流式，一次性拿到完整结果

        Request request = new Request.Builder()
                .url(ENDPOINT)
                .post(RequestBody.create(JSON, payload.toString()))
                .build();

        try (Response response = CLIENT.newCall(request).execute()) {
            String body = response.body() == null ? "" : response.body().string();
            if (!response.isSuccessful()) {
                return "[大模型错误] HTTP " + response.code();
            }
            // Ollama 返回 {"response": "...", ...}，只取正文，不把整段 JSON 抛给调用方
            JsonObject result = JsonParser.parseString(body).getAsJsonObject();
            String text = result.has("response") ? result.get("response").getAsString() : body;
            // 干掉 <think> 思考过程，只留最后那句纯粹的独白
            return stripThinking(text);
        } catch (IOException | RuntimeException e) {
            // 机器上 Ollama 没启动、端口不通、返回内容不是合法 JSON 等情况都落到这里
            return "[大模型无响应] " + e.getMessage();
        }
    }

    /**
     * 把一段文本变成向量（Ollama /api/embeddings）。
     *
     * @param text 待向量化的文本
     * @return 1536 维向量；失败时返回长度为 0 的数组，调用方据此跳过向量记忆
     */
    public static double[] embed(String text) {
        if (text == null || text.trim().isEmpty()) {
            return new double[0];
        }
        JsonObject payload = new JsonObject();
        payload.addProperty("model", EMBED_MODEL);
        payload.addProperty("prompt", text);

        Request request = new Request.Builder()
                .url(EMBED_ENDPOINT)
                .post(RequestBody.create(JSON, payload.toString()))
                .build();

        try (Response response = CLIENT.newCall(request).execute()) {
            String body = response.body() == null ? "" : response.body().string();
            if (!response.isSuccessful()) {
                System.out.println("[向量] Embedding 失败: HTTP " + response.code());
                return new double[0];
            }
            JsonObject result = JsonParser.parseString(body).getAsJsonObject();
            if (!result.has("embedding")) {
                return new double[0];
            }
            JsonArray embedding = result.getAsJsonArray("embedding");
            double[] vector = new double[embedding.size()];
            for (int i = 0; i < embedding.size(); i++) {
                vector[i] = embedding.get(i).getAsDouble();
            }
            return vector;
        } catch (IOException | RuntimeException e) {
            System.out.println("[向量] Embedding 异常: " + e.getMessage());
            return new double[0];
        }
    }

    /**
     * 砍掉模型输出里的思考链：完整块和未闭合块都处理。
     *
     * @param text 原始输出
     * @return 只保留正文；全部被砍光时返回空串
     */
    private static String stripThinking(String text) {
        if (text == null) {
            return "";
        }
        String cleaned = THINK_BLOCK.matcher(text).replaceAll("");
        cleaned = THINK_UNCLOSED.matcher(cleaned).replaceAll("");
        return cleaned.trim();
    }
}
