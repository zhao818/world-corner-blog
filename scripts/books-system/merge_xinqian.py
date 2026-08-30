# -*- coding: utf-8 -*-
"""《信任危机·前置条件论》正文 → 成书 markdown

读 I:\灵魂之觅\docs\信任危机-前置条件论.md(定稿全文),做机械整理:
  - 剔除书首 # 书名行(书名由阅读器 BOOKS / 听书页 yaml 提供)
  - 剔除书首文档头(> 引用块:成稿/定位/核心原创/关联,均为元信息不朗读)
  - 剔除文末 *成稿于...* / *关联:* 两行斜体元信息
  - ## 章标题 → # 一级(阅读器 flat 模式 / TTS split 均按 # 一级切章)
  - 表格保留原样(阅读器渲染;朗读口语化在 tts_xinqian.py 处理)
  - 其余正文照抄(含 --- 分隔线、正文 > 引言、**加粗**)
输出 books-system/信任危机·前置条件论-灵魂之觅版.md。

用法:python merge_xinqian.py
"""
import os
import re

SRC = r"I:\灵魂之觅\docs\信任危机-前置条件论.md"
BASE = os.path.dirname(os.path.abspath(__file__))
DST = os.path.join(BASE, "信任危机·前置条件论-灵魂之觅版.md")

EXPECT_CHAPTERS = 12  # 〇开卷/一~十/尾声


def main():
    text = open(SRC, encoding="utf-8").read()

    out = []
    chap = 0
    saw_title = False  # 是否已见到第一个 ## 章标题
    for ln in text.split("\n"):
        s = ln.strip()
        # 文末斜体元信息(成稿声明/关联),剔除
        if s.startswith("*成稿于") or s.startswith("*关联:"):
            continue
        m = re.match(r"^##\s+(.+)$", ln)
        if m:
            chap += 1
            saw_title = True
            out.append("# " + m.group(1).strip())
        else:
            if saw_title:
                out.append(ln)
            # 未到第一章之前:书名行、> 文档头、首个 --- 全部丢弃

    book = "\n".join(out).strip() + "\n"
    open(DST, "w", encoding="utf-8").write(book)

    # 校验
    h1 = re.findall(r"(?m)^# (.+)$", book)
    print("输出:", DST)
    print("总字数(含标题):", len(book))
    print("一级章节数:", len(h1), "(期望 %d)" % EXPECT_CHAPTERS)
    if chap != EXPECT_CHAPTERS:
        print("⚠️ 转换的 ## 章数 %d != %d" % (chap, EXPECT_CHAPTERS))
    for w in ("<!--APPEND-->", "成稿于", "*关联:", "本文定位"):
        if w in book:
            print("⚠️ 残留:", w)
    if re.search(r"[_＿]", book):
        print("⚠️ 仍有下划线")
    print("\n-- 章节清单 --")
    for t in h1:
        print("  #", t)


if __name__ == "__main__":
    main()
