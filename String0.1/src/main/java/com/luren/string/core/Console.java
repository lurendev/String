package com.luren.string.core;

/**
 * 控制台输出小工具：让读秒在同一行原地刷新，又不会被普通日志打断。
 */
public final class Console {

    /** 清空当前行的控制字符（\r 回到行首 + 空格覆盖 + 再回行首）。 */
    private static final String CLEAR_LINE = "\r                                                                        \r";

    private Console() {
    }

    /**
     * 打印一行普通日志；先清掉读秒残留，避免文字粘连。
     *
     * @param message 日志内容
     */
    public static synchronized void log(String message) {
        System.out.print(CLEAR_LINE + message + System.lineSeparator());
        System.out.flush();
    }

    /**
     * 在当前位置原地刷新读秒，不换行。
     *
     * @param text 读秒文本
     */
    public static synchronized void countdown(String text) {
        // 尾部留空格，覆盖上一次更长的文字
        System.out.print("\r" + text + "        ");
        System.out.flush();
    }
}
