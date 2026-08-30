# -*- coding: utf-8 -*-
"""《信任危机·前置条件论》书稿 md → epub(站点品牌色:深藏青 + 金)

用法:
    python build_epub_xinqian.py
输出:books-system/信任危机·前置条件论-灵魂之觅版.epub
封面:scripts/covers/cover-xinqian.jpg(听书页同款 1080×1080)
"""
import os
import re
import zipfile

from markdown import markdown
from ebooklib import epub

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "信任危机·前置条件论-灵魂之觅版.md")
DST = os.path.join(BASE, "信任危机·前置条件论-灵魂之觅版.epub")
COVER = os.path.join(os.path.dirname(BASE), "covers", "cover-xinqian.jpg")

# 品牌色:深藏青 #0b1017 + 金 #c9a55c / #e7cd8c(与听书页/公众号封面统一)
CSS = """
body {
  font-family: "Songti SC", "Noto Serif CJK SC", "Source Han Serif SC", "STSong", serif;
  line-height: 1.9;
  color: #2b2b2b;
  background: #faf9f4;
}
h1 {
  text-align: center;
  margin: 2.2em 0 1.4em;
  font-size: 1.45em;
  color: #0b1017;
  letter-spacing: .12em;
}
h2 {
  color: #0b1017;
  border-left: 4px solid #c9a55c;
  padding-left: .6em;
  margin-top: 2em;
  font-size: 1.12em;
}
h3, h4 { color: #0b1017; }
p { margin: .6em 0; }
blockquote {
  border-left: 3px solid #c9a55c;
  margin: 1em 0;
  padding: .5em 1em;
  color: #6b6350;
  background: #f4efe2;
}
strong { color: #0b1017; }
hr { border: none; border-top: 1px dashed #c9a55c; margin: 1.8em 0; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
th, td { border: 1px solid #d8d0b8; padding: .5em .7em; font-size: .92em; }
th { background: #f4efe2; color: #0b1017; }
"""


def split_chapters(text):
    """按 # 与 ## 标题行切分,返回 [(level, title, body), ...]"""
    chapters = []
    cur_lines = []
    cur_level = 0
    cur_title = ""

    def flush():
        nonlocal cur_lines
        if cur_lines:
            body = "\n".join(cur_lines).strip()
            body = re.sub(r"^#{1,6}\s+.*$", "", body, count=1, flags=re.M).strip()
            chapters.append((cur_level, cur_title, body))
            cur_lines = []

    for ln in text.splitlines():
        m = re.match(r"^(#{1,2})\s+(.+)$", ln)
        if m:
            flush()
            cur_level = len(m.group(1))
            cur_title = m.group(2).strip()
        else:
            cur_lines.append(ln)
    flush()
    return chapters


def get_cover_bytes():
    if os.path.exists(COVER):
        return open(COVER, "rb").read()
    print("未找到封面:", COVER)
    return None


def main():
    text = open(SRC, encoding="utf-8").read()
    chapters = split_chapters(text)
    print("章节数:", len(chapters))

    book = epub.EpubBook()
    book.set_identifier("xinqian-weiji-2026-v1")
    book.set_title("信任危机·前置条件论")
    book.set_language("zh")
    book.add_author("美好需要创造")

    style = epub.EpubItem(uid="style", file_name="style/stylesheet.css", media_type="text/css", content=CSS)
    book.add_item(style)

    cover = get_cover_bytes()
    if cover:
        book.set_cover("cover.jpg", cover)

    epub_chapters = []
    for i, (level, title, body) in enumerate(chapters):
        html_body = markdown(body, extensions=["tables", "sane_lists"])
        content = '<h%d class="chapter-title">%s</h%d>\n%s' % (level, title, level, html_body)
        ch = epub.EpubHtml(
            title=title,
            file_name="index_split_%03d.xhtml" % i,
            lang="zh",
            content=content,
        )
        ch.add_item(style)
        book.add_item(ch)
        epub_chapters.append((level, ch))

    toc = []
    current = None
    for level, ch in epub_chapters:
        if level == 1:
            current = []
            toc.append((ch, current))
        else:
            if current is not None:
                current.append(ch)
            else:
                toc.append(ch)
    book.toc = toc

    book.spine = ["nav"] + [ch for _, ch in epub_chapters]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # 延伸阅读:时代观察 · 方法论(不并入四书主线,与《算法争夺》互为镜)
    ext_content = """<h2>延伸阅读</h2>
<p><strong>时代观察 · 方法论(不并入四书主线)</strong></p>
<p>本文独立成篇,但站在已有的地基上——承接《走向田间》用萨特「他人即地狱」照出的三场崩塌,把它们升维成方法论;与《算法争夺》互为镜:那篇讲注意力被收割,这篇讲信任被消费,同一片荒地(时代真空期)上长的两种野草。</p>
<blockquote>《算法争夺》(《文明的阶梯》续篇) · 注意力被收割。心里那片地,不种庄稼,就长野草。</blockquote>
<blockquote>《走向田间》 · 承接萨特透镜。陆篇照全荒幕的三场崩塌,本文把它们升维成方法论。</blockquote>
<p><strong>四本书 · 主线</strong></p>
<ul>
<li>《信任危机·前置条件论》 ✓ 已读 · 时代观察</li>
<li>《走向田间》 → 回看 · 萨特透镜</li>
<li>《文明的阶梯》 → 对照 · 算法争夺续篇</li>
<li>《幸福的内在》 / 《内心的修炼》 → 回到主线 · 看人</li>
</ul>
<p><strong>在线阅读</strong> · 世界一隅:worldcorner.xyz/read/xinqian/</p>"""
    ext_ch = epub.EpubHtml(title="延伸阅读", file_name="index_extension.xhtml", lang="zh", content=ext_content)
    ext_ch.add_item(style)
    book.add_item(ext_ch)
    book.toc.append(ext_ch)
    book.spine.append(ext_ch)

    epub.write_epub(DST, book)
    size = os.path.getsize(DST)
    print("已生成:", DST)
    print("大小: %.1f KB" % (size / 1024))


if __name__ == "__main__":
    main()
