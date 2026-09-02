# -*- coding: utf-8 -*-
"""《信任·伦理篇》正文 → 成书 markdown

读 I:\灵魂之觅\docs\信任-伦理篇-草稿.md(定稿全文),做机械整理:
  - 剔除书首 # 书名行(书名由听书页 yaml / 文章页提供)
  - 剔除书首文档头(> 引用块:定位/关系/写作规矩,均为元信息不朗读)
  - 剔除文末 *初稿于...* / *关联:* 两行斜体元信息
  - 剔除文末 <!-- 内部导航:... --> HTML 注释行(含知识库内部路径,必删)
  - ## 章标题 → # 一级(TTS split 按 # 一级切章;朗读用 title 注入)
  - 其余正文照抄(含 --- 分隔线、正文 > 引言、**加粗**)
输出 books-system/信任伦理篇-灵魂之觅版.md。

注:剔除谓词同 merge_benyuan(扩到 *初稿于*);HTML 注释按行首 <!-- 剔除。
伦理篇 = 信任系列上游篇/供给篇,6 章:〇开卷/一/二/三/四/尾声。

用法:python merge_lunli.py
"""
import os
import re

SRC = r"I:\灵魂之觅\docs\信任-伦理篇-草稿.md"
BASE = os.path.dirname(os.path.abspath(__file__))
DST = os.path.join(BASE, "信任伦理篇-灵魂之觅版.md")

EXPECT_CHAPTERS = 6  # 〇开卷/一/二/三/四/尾声


def main():
    text = open(SRC, encoding="utf-8").read()

    out = []
    chap = 0
    saw_title = False  # 是否已见到第一个 ## 章标题
    for ln in text.split("\n"):
        s = ln.strip()
        # 文末斜体元信息(初稿声明/成稿声明/关联),剔除
        if s.startswith("*初稿于") or s.startswith("*成稿于") or s.startswith("*关联:"):
            continue
        # 内部导航 HTML 注释行(含知识库 docs/ 内部路径),剔除
        if s.startswith("<!--"):
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
    for w in ("<!--", "初稿于", "*关联:", "草稿", "内部导航"):
        if w in book:
            print("⚠️ 残留:", w)
    if re.search(r"[_＿]", book):
        print("⚠️ 仍有下划线")
    print("\n-- 章节清单 --")
    for t in h1:
        print("  #", t)


if __name__ == "__main__":
    main()
