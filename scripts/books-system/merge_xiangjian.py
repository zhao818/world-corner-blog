# -*- coding: utf-8 -*-
"""《走向田间》正文 → 成书 markdown

读 I:\灵魂之觅\docs\走向田间-正文3.md(工作版全文),做机械整理:
  - 剔除末尾 <!--APPEND-->(知识库追加标记)
  - 剔除书首 # 《走向田间...》书名行(书名由阅读器 BOOKS / 听书页 yaml 提供)
  - ## 章标题 → # 一级(阅读器 flat 模式 / TTS split 均按 # 一级切章)
  - 其余正文照抄(含 --- 分隔线、> 引言、**加粗**)
输出 books-system/走向田间-灵魂之觅版.md。

用法:python merge_xiangjian.py
"""
import os
import re

SRC = r"I:\灵魂之觅\docs\走向田间-正文3.md"
BASE = os.path.dirname(os.path.abspath(__file__))
DST = os.path.join(BASE, "走向田间-灵魂之觅版.md")

EXPECT_CHAPTERS = 14  # 开卷/序言/壹~拾壹/跋


def main():
    text = open(SRC, encoding="utf-8").read()

    out = []
    chap = 0
    saw_title = False
    pending = []  # 书首标题之前的引言/分隔线,并入第一章(避免悬在文件头生成伪章节)
    for ln in text.split("\n"):
        s = ln.strip()
        if s == "<!--APPEND-->":
            continue
        # 书首书名行:唯一以 # 开头的一级标题,剔除
        if s.startswith("# 《"):
            continue
        m = re.match(r"^##\s+(.+)$", ln)
        if m:
            chap += 1
            out.append("# " + m.group(1).strip())
            if not saw_title:
                saw_title = True
                if pending:
                    out.append("")
                    out.extend(pending)
                    pending = []
        else:
            if saw_title:
                out.append(ln)
            else:
                pending.append(ln)

    book = "\n".join(out).strip() + "\n"
    open(DST, "w", encoding="utf-8").write(book)

    # 校验
    h1 = re.findall(r"(?m)^# (.+)$", book)
    print("输出:", DST)
    print("总字数(含标题):", len(book))
    print("一级章节数:", len(h1), "(期望 %d)" % EXPECT_CHAPTERS)
    if chap != EXPECT_CHAPTERS:
        print("⚠️ 转换的 ## 章数 %d != %d" % (chap, EXPECT_CHAPTERS))
    for w in ("<!--APPEND-->", "下一篇见", "下一篇文章", "上一篇文章"):
        if w in book:
            print("⚠️ 残留:", w)
    if re.search(r"[_＿]", book):
        print("⚠️ 仍有下划线")
    print("\n-- 章节清单 --")
    for t in h1:
        print("  #", t)


if __name__ == "__main__":
    main()
