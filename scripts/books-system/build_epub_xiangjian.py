# -*- coding: utf-8 -*-
"""《走向田间》书稿 md → epub(站点品牌色:深藏青 + 金)

用法:
    python build_epub_xiangjian.py
输出:books-system/走向田间-灵魂之觅版.epub
封面:scripts/covers/cover-xiangjian.jpg(听书页同款 1080×1080)
"""
import os
import re
import zipfile

from markdown import markdown
from ebooklib import epub

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "走向田间-灵魂之觅版.md")
DST = os.path.join(BASE, "走向田间-灵魂之觅版.epub")
COVER = os.path.join(os.path.dirname(BASE), "covers", "cover-xiangjian.jpg")

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
    book.set_identifier("xiangjian-tianjian-v1-2026")
    book.set_title("走向田间")
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

    # 延伸阅读:读完这本(器)→ 回到三本「人」的书重读(闭环)
    ext_content = """<h2>延伸阅读</h2>
<p><strong>看完了器,回到人重新出发</strong></p>
<p>前三本立起了「人」——看清方向、看见问题、学会方法。《走向田间》接着问:技术时代,该把力量引向哪?带着这面镜子重读前三本,你会看到同一片土地上的不同断面。</p>
<blockquote>《文明的阶梯》 · 总纲。从「喂饱」立起的文明观——走向田间的落点,正是它埋下的那个方向。</blockquote>
<blockquote>《幸福的内在》 · 现象诊断书。地荒的根源在心里——每个「空」的背后,都是同一片荒了的地。</blockquote>
<blockquote>《内心的修炼》 · 修行操作书。把目光从手机上移开、把心里那片地重新种起来,需要一架天天可爬的梯子。</blockquote>
<p><strong>四本书 · 阅读顺序</strong></p>
<ul>
<li>《走向田间》 ✓ 已读 · 转向土地</li>
<li>《文明的阶梯》 → 重读 · 看总纲</li>
<li>《幸福的内在》 → 重读 · 看现象</li>
<li>《内心的修炼》 → 重读 · 去行动</li>
</ul>
<p><strong>在线阅读</strong> · 世界一隅:worldcorner.xyz/read/xiangjian/</p>"""
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
