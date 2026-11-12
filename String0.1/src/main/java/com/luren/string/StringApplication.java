package com.luren.string;

import com.luren.string.core.Arbiter;
import com.luren.string.core.Console;
import com.luren.string.modules.AnxietyModule;
import com.luren.string.modules.BaseModule;
import com.luren.string.modules.BookReaderModule;
import com.luren.string.modules.DopamineModule;
import com.luren.string.modules.EscapeModule;
import com.luren.string.modules.ImposterSyndromeModule;
import com.luren.string.modules.LogicModule;
import com.luren.string.modules.MemoryModule;
import com.luren.string.modules.NihilismModule;
import com.luren.string.modules.PhysiologyModule;
import com.luren.string.modules.SelfDestructModule;
import com.luren.string.modules.SelfModule;
import com.luren.string.modules.SocialNeedModule;
import com.luren.string.modules.SomaticPainModule;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * 启动类：系统的"开机键"。装配模块、点燃心跳，然后让主线程永远守着引擎。
 */
public class StringApplication {

    /** 喂给它的书，位于项目根目录 data/ 下。 */
//    private static final Path BOOK_FILE = Paths.get("data", "book.txt");
    private static final Path BOOK_FILE = Paths.get("data", "西西弗斯神话.txt");

    /** 书读不到时的口粮，保证系统不会因为缺文件而变成植物人。 */
    private static final List<String> FALLBACK_LINES = Arrays.asList(
            "生命本就是荒诞的，但我必须寻找意义。",
            "必须想象西西弗斯是幸福的。");

    public static void main(String[] args) throws InterruptedException {
        List<String> bookLines = loadBook();

        // 装配潜意识模块
        List<BaseModule> modules = new ArrayList<BaseModule>();
        modules.add(new BookReaderModule(bookLines));
        modules.add(new PhysiologyModule());
        AnxietyModule anxietyModule = new AnxietyModule();
        modules.add(anxietyModule);
        modules.add(new MemoryModule());
        EscapeModule escapeModule = new EscapeModule();
        modules.add(escapeModule);
        modules.add(new DopamineModule());
        modules.add(new ImposterSyndromeModule());
        modules.add(new SomaticPainModule());
        modules.add(new SocialNeedModule());
        modules.add(new SelfDestructModule());
        modules.add(new NihilismModule());
        modules.add(new SelfModule());
        // 逻辑模块必须放在最后：它要读取焦虑/逃避在本次 TICK 中刚算出的分数
        modules.add(new LogicModule(anxietyModule, escapeModule));

        // 点燃认知心跳
        Arbiter arbiter = new Arbiter(modules);
        arbiter.start();
        Console.log("[启动] String 已开机，共 " + modules.size() + " 个模块，书本 " + bookLines.size() + " 行");
        // Arbiter 的调度线程是守护线程：主线程一旦退出，JVM 会立刻关机。
        // 这里让主线程永远挂起，把生命维持住。
        Thread.currentThread().join();
    }

    /**
     * 读取 data/book.txt；文件缺失、不可读或全为空白时退回到内置句子。
     */
    private static List<String> loadBook() {
        if (!Files.exists(BOOK_FILE)) {
            System.out.println("[启动] 未找到 data/book.txt，使用内置句子");
            return FALLBACK_LINES;
        }
        try {
            List<String> lines = Files.readAllLines(BOOK_FILE, StandardCharsets.UTF_8);
            List<String> cleaned = new ArrayList<String>();
            for (String line : lines) {
                if (!line.trim().isEmpty()) {
                    cleaned.add(line.trim());
                }
            }
            return cleaned.isEmpty() ? FALLBACK_LINES : cleaned;
        } catch (IOException e) {
            System.out.println("[启动] 读取 book.txt 失败: " + e.getMessage());
            return FALLBACK_LINES;
        }
    }
}
