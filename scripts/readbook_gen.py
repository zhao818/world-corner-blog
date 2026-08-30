# -*- coding: utf-8 -*-
"""两本书 md → 自包含在线阅读器 HTML

输入(books-system 下):
  幸福的内在-灵魂之觅版.md      → static/read/happiness/index.html
  内心的修炼-v4-灵魂之觅版.md    → static/read/neixin/index.html

阅读器功能:章节目录抽屉 / 字号调节 / 白昼·夜间主题 / 滚动进度记忆(localStorage) /
返回听书 / 顶部阅读进度条。深藏青 #0b1017 + 金 #c9a55c 品牌色,衬线中文,无 emoji 图标。

用法:python readbook_gen.py
"""
import os
import re

from markdown import markdown

BASE = os.path.dirname(os.path.abspath(__file__))
BS = os.path.join(BASE, "books-system")
OUT_ROOT = os.path.join(os.path.dirname(BASE), "static", "read")

# mode:
#   vol-chap  两级: #=卷、##=章(幸福内在)
#   flat      扁平: #=章、##=章内小节(内心修炼)
BOOKS = [
    {
        "id": "happiness",
        "file": "幸福的内在-灵魂之觅版.md",
        "title": "幸福的内在",
        "subtitle": "卷一 · 幸福的内在(01–18)+ 卷二 · 幸福的验证(19–31)",
        "listen_href": "/audiobook/#book-xingfu",
        "mode": "vol-chap",
        # 延伸阅读:读完这本推荐下一本(三书互相引成闭环)
        "rec": {
            "title": "读完这一本,接下来学什么?",
            "guide": "《幸福的内在》让我们看见了「人为什么空」。但光看见不够——接下来,你更需要知道:怎么安顿自己、怎么站上去。",
            "items": [{
                "bid": "neixin", "name": "内心的修炼", "pos": "修行操作书 · 用书当拐杖的人生通识课",
                "core": "一个人的内心秩序,不是靠外部世界给的,是靠一次次主动选择、主动断舍离、主动立根本,慢慢炼出来的。",
                "btn": "接着读",
            }],
            "order": ["《幸福的内在》 · 已读 · 看到问题", "《内心的修炼》 → 接下来:学方法", "《文明的阶梯》 → 最后:看清方向"],
        },
    },
    {
        "id": "neixin",
        "file": "内心的修炼-v4-灵魂之觅版.md",
        "title": "内心的修炼",
        "subtitle": "序言 + 九关修炼 + 完结篇",
        "listen_href": "/audiobook/#book-neixin",
        "mode": "flat",
        "rec": {
            "title": "学会了方法,接下来往哪走?",
            "guide": "《内心的修炼》把可上手的方法递到了你手上。但你可能还在问:我们到底在做什么、要往哪儿去?",
            "items": [{
                "bid": "civilization", "name": "文明的阶梯", "pos": "总纲 · 从「喂饱」讲起的文明观",
                "core": "文明的每一次跃迁,都是一场「喂饱」的革命——先喂饱身体,再喂饱思想;而一群人亮起来,才是文明真正站上的那一级阶梯。",
                "btn": "接着读", "anchor": "wenming",
            }],
            "order": ["《幸福的内在》 · 已读 · 看到问题", "《内心的修炼》 · 已读 · 学会方法", "《文明的阶梯》 → 接下来:看清方向"],
        },
    },
    {
        "id": "civilization",
        "file": "文明的阶梯-灵魂之觅版.md",
        "title": "文明的阶梯",
        "subtitle": "序言 + 五篇论证 + 每日必修 + 跋 + 续篇",
        "listen_href": "/audiobook/#book-wenming",
        "mode": "flat",
        "rec": {
            "title": "看清了方向,接着走向田间",
            "guide": "现在你有了这张地图。想看看方向在科技时代的落点,直接走进《走向田间》——它把「喂饱」立起的路,接到了 AI 该服务谁上。带着地图重读前两本,也会看到不一样的断面。",
            "items": [
                {"bid": "xiangjian", "name": "走向田间", "pos": "转向 · 读了它才知道力气该引向哪",
                 "core": "从「喂饱」立起的文明观——走向田间的落点,正是它埋下的那个方向。", "btn": "接着读", "anchor": "xiangjian"},
                {"bid": "happiness", "name": "幸福的内在", "pos": "现象诊断书 · 读了它才看得见「空」",
                 "core": "有了总纲后,你会看到每一个「空」的背后,都是文明阶梯的一个断面。", "btn": "重读", "anchor": "xingfu"},
                {"bid": "neixin", "name": "内心的修炼", "pos": "修行操作书 · 读了它才动得了手",
                 "core": "有了地图后,你会明白每一次修炼,都是在为文明跃迁积蓄力量。", "btn": "重读", "anchor": "neixin"},
            ],
            "order": ["《文明的阶梯》 · 已读 · 看清方向", "《走向田间》 → 接下来:看科技落点", "《幸福的内在》 → 也可以重读:看现象", "《内心的修炼》 → 也可以重读:去行动"],
        },
    },
    {
        "id": "xiangjian",
        "file": "走向田间-灵魂之觅版.md",
        "title": "走向田间",
        "subtitle": "开卷 + 序言 + 壹~拾壹 + 跋",
        "listen_href": "/audiobook/#book-xiangjian",
        "mode": "flat",
        "rec": {
            "title": "看完了田,回到人重新出发",
            "guide": "前三本立起了「人」——看清方向、看见问题、学会方法。《走向田间》接着问:技术时代,该把力量引向哪?带着这面镜子重读前三本,你会看到同一片土地上的不同断面。",
            "items": [
                {"bid": "civilization", "name": "文明的阶梯", "pos": "总纲 · 读了它才看得清方向",
                 "core": "从「喂饱」立起的文明观——走向田间的落点,正是它埋下的那个方向。", "btn": "重读", "anchor": "wenming"},
                {"bid": "happiness", "name": "幸福的内在", "pos": "现象诊断书 · 读了它才看得见「空」",
                 "core": "地荒的根源在心里——每个「空」的背后,都是同一片荒了的地。", "btn": "重读", "anchor": "xingfu"},
                {"bid": "neixin", "name": "内心的修炼", "pos": "修行操作书 · 读了它才动得了手",
                 "core": "把目光从手机上移开、把心里那片地重新种起来,需要一架天天可爬的梯子。", "btn": "重读", "anchor": "neixin"},
            ],
            "order": ["《走向田间》 · 读完 · 转向土地", "《文明的阶梯》 → 重读:看总纲", "《幸福的内在》 → 重读:看现象", "《内心的修炼》 → 重读:去行动"],
        },
    },
    {
        "id": "xinqian",
        "file": "信任危机·前置条件论-灵魂之觅版.md",
        "title": "信任危机·前置条件论",
        "subtitle": "〇开卷声明 + 一~十 + 尾声(时代观察 · 方法论)",
        "listen_href": "/audiobook/#book-xinqian",
        "mode": "flat",
        "rec": {
            "title": "这本不并主线,它是时代观察的另一半",
            "guide": "本文不并入四书主线,它是独立的方法论沉淀——「时代观察 · 方法论」。与《算法争夺》互为镜:那篇讲注意力被收割,这篇讲信任被消费——同一片荒地(时代真空期)上长的两种野草,放在一起看,荒地的轮廓才完整。",
            "items": [
                {"bid": "civilization", "name": "文明的阶梯 · 续篇", "pos": "互为镜 · 《算法争夺》讲注意力被收割",
                 "core": "心里那片地,不种庄稼,就长野草——算法争夺的是认知能量,本文讲的是信任被消费。", "btn": "对照读", "anchor": "wenming"},
                {"bid": "xiangjian", "name": "走向田间", "pos": "承接 · 萨特透镜",
                 "core": "陆篇用萨特「他人即地狱」照全荒幕的三场崩塌——本文把它们升维成方法论。", "btn": "回看", "anchor": "xiangjian"},
            ],
            "order": [],
        },
    },
]

CSS = """
:root {
  --bg: #0b1017; --panel: #121a28; --panel2: #0e1520;
  --ink: #e9e4d8; --ink-2: #a79e8c; --gold: #c9a55c; --gold-l: #e7cd8c;
  --border: #223047; --thin: rgba(201,165,92,.28);
}
[data-theme="day"] {
  --bg: #faf9f4; --panel: #ffffff; --panel2: #f3f0e6;
  --ink: #2b2b2b; --ink-2: #6b6350; --gold: #9a7a3a; --gold-l: #0b1017;
  --border: #e2dcc8; --thin: rgba(154,122,58,.35);
}
* { margin: 0; padding: 0; box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  background: var(--bg); color: var(--ink);
  font-family: "Songti SC", "Noto Serif CJK SC", "Source Han Serif SC", "STSong", serif;
  line-height: 1.95; font-size: 17px;
  transition: background .25s, color .25s;
}
body[data-font="s"] { font-size: 15px; }
body[data-font="m"] { font-size: 17px; }
body[data-font="l"] { font-size: 19px; }
body[data-font="xl"] { font-size: 21px; }

/* 顶部工具条 */
.topbar {
  position: fixed; inset: 0 0 auto 0; z-index: 50;
  display: flex; align-items: center; gap: 12px;
  height: 52px; padding: 0 18px;
  background: var(--panel); border-bottom: 1px solid var(--border);
  backdrop-filter: blur(6px);
}
.tb-title { font-size: .92rem; font-weight: 600; letter-spacing: .06em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tb-title .tb-sub { display: block; font-size: .66rem; font-weight: 400; color: var(--ink-2); letter-spacing: .02em; }
.tb-spacer { flex: 1; }
.tb-btn {
  background: transparent; border: 1px solid var(--border); color: var(--ink-2);
  font-family: inherit; font-size: .76rem; letter-spacing: .08em;
  padding: 6px 12px; border-radius: 999px; cursor: pointer; transition: all .2s;
  display: inline-flex; align-items: center; gap: 5px; white-space: nowrap;
}
.tb-btn:hover { color: var(--gold); border-color: var(--thin); }
.tb-btn.active { color: var(--gold-l); border-color: var(--thin); background: rgba(201,165,92,.08); }
.tb-font span { display: inline-block; min-width: 22px; text-align: center; }
.tb-back { text-decoration: none; }

/* 阅读进度条 */
.progress {
  position: fixed; top: 52px; left: 0; z-index: 49; height: 2px; width: 100%;
  background: transparent;
}
.progress i { display: block; height: 100%; width: 0; background: linear-gradient(90deg, var(--gold), var(--gold-l)); }

/* 目录抽屉 */
.drawer {
  position: fixed; inset: 52px auto 0 0; z-index: 45;
  width: 300px; max-width: 84vw;
  background: var(--panel2); border-right: 1px solid var(--border);
  transform: translateX(-102%); transition: transform .28s ease;
  overflow-y: auto; padding: 18px 8px 40px;
}
.drawer.open { transform: translateX(0); }
.drawer::-webkit-scrollbar { width: 5px; }
.drawer::-webkit-scrollbar-thumb { background: var(--thin); border-radius: 3px; }
.dw-group { margin: 4px 0; }
.dw-vol {
  font-size: .7rem; letter-spacing: .2em; color: var(--gold);
  padding: 10px 14px 4px; font-weight: 600;
}
.dw-item {
  display: flex; align-items: baseline; gap: 8px;
  padding: 6px 14px 6px 18px; cursor: pointer;
  font-size: .84rem; color: var(--ink-2); border-radius: 8px; transition: background .15s;
}
.dw-item:hover { background: rgba(201,165,92,.07); color: var(--ink); }
.dw-item.active { color: var(--gold-l); background: rgba(201,165,92,.1); }
.dw-no { font-family: "Segoe UI", "Roboto Mono", monospace; font-size: .7rem; color: var(--gold); min-width: 34px; text-align: right; }
.scrim { position: fixed; inset: 52px 0 0 0; z-index: 44; background: rgba(0,0,0,.4); opacity: 0; pointer-events: none; transition: opacity .25s; }
.scrim.open { opacity: 1; pointer-events: auto; }

/* 正文前章目录(胶囊横排,复用 .dw-item 平滑滚动与当前章高亮) */
.inline-toc { background: var(--panel2); border: 1px solid var(--border); border-radius: 12px; padding: 20px 22px; margin-bottom: 48px; }
.inline-toc-title { font-size: .7rem; letter-spacing: .26em; color: var(--gold); margin: 0 0 14px; text-transform: uppercase; font-weight: 600; }
.inline-toc-list { display: flex; flex-wrap: wrap; gap: 6px; }
.inline-vol { color: var(--gold); font-size: .76rem; letter-spacing: .12em; margin: 10px 0 2px; font-weight: 600; }
.inline-vol-c { display: flex; flex-wrap: wrap; gap: 6px; }
.toc-link { display: inline-flex; align-items: baseline; gap: 6px; padding: 6px 13px; border-radius: 999px; cursor: pointer; font-size: .86rem; color: var(--ink-2); border: 1px solid var(--border); transition: color .15s, border-color .15s, background .15s; }
.toc-link:hover { color: var(--gold-l); border-color: var(--thin); background: rgba(201,165,92,.07); }
.toc-link.active { color: var(--gold-l); border-color: var(--thin); background: rgba(201,165,92,.1); }
.toc-link .dw-no { font-size: .72rem; color: var(--gold); min-width: auto; text-align: left; }

/* 阅读区 */
.wrap { max-width: 720px; margin: 0 auto; padding: 108px 26px 120px; }
.chapter {
  margin-bottom: 64px; scroll-margin-top: 72px;
  border-bottom: 1px dashed var(--border); padding-bottom: 48px;
}
.chapter:last-child { border-bottom: none; }
.ch-tag { font-size: .68rem; letter-spacing: .24em; color: var(--gold); margin-bottom: 14px; text-transform: uppercase; }
.chapter h2 { font-size: 1.35rem; color: var(--ink); margin-bottom: 22px; letter-spacing: .04em; line-height: 1.5; }
.chapter h3 {
  font-size: 1.02rem; color: var(--gold-l);
  margin: 1.6em 0 .8em; letter-spacing: .06em; line-height: 1.6;
}
.chapter h4 { font-size: .95rem; color: var(--ink); margin: 1.3em 0 .6em; }
.chapter p { margin: .65em 0; text-align: justify; }
.chapter blockquote {
  border-left: 3px solid var(--gold); background: rgba(201,165,92,.06);
  padding: .5em 1em; margin: 1em 0; color: var(--ink-2); border-radius: 0 8px 8px 0;
}
.chapter strong { color: var(--gold-l); }
.chapter hr { border: none; border-top: 1px dashed var(--border); margin: 1.6em 0; }

/* 书尾 */
.footer { text-align: center; padding: 40px 0 80px; color: var(--ink-2); font-size: .8rem; }
.footer .back {
  display: inline-block; margin-top: 18px; padding: 9px 22px;
  border: 1px solid var(--thin); border-radius: 999px; color: var(--gold);
  text-decoration: none; letter-spacing: .1em; font-size: .82rem; transition: all .2s;
}
.footer .back:hover { background: rgba(201,165,92,.1); color: var(--gold-l); }

@media (max-width: 640px) {
  .wrap { padding: 96px 18px 100px; }
  .tb-title { max-width: 130px; }
}

/* 延伸阅读(三书互链) */
.ext { margin-top: 72px; padding-top: 44px; border-top: 1px dashed var(--border); }
.ext-title { font-size: 1.12rem; color: var(--gold); letter-spacing: .1em; margin-bottom: 14px; }
.ext-guide { color: var(--ink-2); line-height: 1.9; margin-bottom: 26px; }
.ext-card {
  background: var(--panel); border-left: 3px solid var(--gold); border-radius: 0 10px 10px 0;
  padding: 20px 22px; margin-bottom: 16px;
}
.ext-pos { font-size: .72rem; letter-spacing: .16em; color: var(--gold); }
.ext-name { font-size: 1.16rem; color: var(--ink); margin: 6px 0 10px; letter-spacing: .04em; }
.ext-core { color: var(--ink-2); line-height: 1.9; }
.ext-row { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px; }
.ext-btn, .ext-listen {
  display: inline-block; padding: 7px 18px; border-radius: 999px;
  font-size: .8rem; text-decoration: none; letter-spacing: .08em; transition: all .2s;
}
.ext-btn { background: var(--gold); color: #0b1017; font-weight: 600; }
.ext-btn:hover { background: var(--gold-l); }
.ext-listen { border: 1px solid var(--thin); color: var(--gold); background: transparent; }
.ext-listen:hover { background: rgba(201,165,92,.1); }
.ext-order { margin-top: 28px; padding-top: 20px; border-top: 1px dashed var(--border); }
.ext-order-title { font-size: .7rem; letter-spacing: .2em; color: var(--ink-2); margin-bottom: 12px; text-transform: uppercase; }
.ext-order p { font-size: .88rem; color: var(--ink-2); margin: 6px 0; }
.ext-order .done::before { content: "✓ "; color: var(--gold); }
.ext-order .next::before { content: "→ "; color: var(--gold); }
"""

JS = """
(function () {
  var store = localStorage;
  var KEY = 'readbk:' + (location.pathname.split('/')[2] || 'x');
  var drawer = document.getElementById('drawer');
  var scrim = document.getElementById('scrim');
  var progress = document.getElementById('progress');
  var chapters = document.querySelectorAll('.chapter');
  var items = document.querySelectorAll('.dw-item');
  var toc = document.getElementById('toc');

  // 主题
  var theme = store.getItem(KEY + ':theme') || 'night';
  document.body.dataset.theme = theme;
  document.getElementById('th-toggle').textContent = theme === 'day' ? '夜间' : '白昼';

  // 字号
  var fs = store.getItem(KEY + ':fs') || 'm';
  document.body.dataset.font = fs;
  var fbtns = document.querySelectorAll('.tb-font button');
  fbtns.forEach(function (b) {
    if (b.dataset.fs === fs) b.classList.add('active');
  });

  // 目录
  document.getElementById('dw-toggle').addEventListener('click', function () {
    drawer.classList.toggle('open'); scrim.classList.toggle('open');
  });
  scrim.addEventListener('click', close);
  function close() { drawer.classList.remove('open'); scrim.classList.remove('open'); }

  items.forEach(function (it) {
    it.addEventListener('click', function () {
      close();
      var t = it.getAttribute('data-t');
      var el = document.getElementById(t);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });

  // 字号
  fbtns.forEach(function (b) {
    b.addEventListener('click', function () {
      var v = b.dataset.fs;
      document.body.dataset.font = v;
      store.setItem(KEY + ':fs', v);
      fbtns.forEach(function (x) { x.classList.remove('active'); });
      b.classList.add('active');
    });
  });

  // 主题
  document.getElementById('th-toggle').addEventListener('click', function () {
    var next = document.body.dataset.theme === 'day' ? 'night' : 'day';
    document.body.dataset.theme = next;
    store.setItem(KEY + ':theme', next);
    this.textContent = next === 'day' ? '夜间' : '白昼';
  });

  // 滚动:进度条 + 当前章节高亮 + 记忆
  var ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () {
      var h = document.documentElement;
      var max = h.scrollHeight - h.clientHeight;
      var pct = max > 0 ? (h.scrollTop / max * 100) : 0;
      progress.firstChild.style.width = pct + '%';
      // 高亮当前章
      var cur = null;
      for (var i = 0; i < chapters.length; i++) {
        if (chapters[i].getBoundingClientRect().top <= 120) cur = chapters[i].id;
      }
      items.forEach(function (it) {
        it.classList.toggle('active', it.getAttribute('data-t') === cur);
      });
      store.setItem(KEY + ':pos', String(h.scrollTop));
      ticking = false;
    });
  }
  window.addEventListener('scroll', onScroll, { passive: true });

  // 恢复进度
  var pos = parseInt(store.getItem(KEY + ':pos') || '0', 10);
  if (pos > 0) window.scrollTo(0, pos);
  onScroll();
})();
"""


CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def split_chapters(text, mode, book_title):
    """返回 [(level, title, body), ...]"""
    chapters = []
    cur_lines = []
    cur_level = 0
    cur_title = ""

    def flush():
        nonlocal cur_lines
        if cur_lines:
            body = "\n".join(cur_lines).strip()
            body = re.sub(r"^#{1,6}\s+.*$", "", body, count=1, flags=re.M).strip()
            if mode == "flat":
                # 章内 ## 小节降级为 ###,避免与章标题同级
                body = re.sub(r"^##\s+", "### ", body, flags=re.M)
            chapters.append((cur_level, cur_title, body))
            cur_lines = []

    if mode == "flat":
        # 只认 # 一级为章,跳过书名行
        for ln in text.splitlines():
            m = re.match(r"^#\s+(.+)$", ln)
            if m:
                flush()
                cur_level = 1
                cur_title = m.group(1).strip()
            else:
                cur_lines.append(ln)
        flush()
        # 去掉书名(通常第一个 h1 == book_title)
        if chapters and chapters[0][1] == book_title:
            chapters.pop(0)
        return chapters

    # vol-chap:一级卷 + 二级章
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


def render_chapters(chapters, mode):
    """返回 (html, toc_items)。toc_items: [{tag, no, title, id}]"""
    html_parts = []
    toc = []
    for i, (level, title, body) in enumerate(chapters):
        cid = "c%02d" % i
        html_body = markdown(body, extensions=["tables", "sane_lists"])
        if mode == "flat":
            m = re.match(r"第([一二三四五六七八九十]+)篇", title)
            if m:
                no = str(CN_NUM.get(m.group(1), ""))
                tag = "篇"
            elif title.startswith("序言"):
                no, tag = "", "序"
            elif title.startswith("完结") or title.startswith("跋"):
                no, tag = "", "终"
            else:
                no, tag = "", "篇"
        else:
            tag = "序" if i == 0 else ("卷" if level == 1 else "章")
            no = title[:2].strip() if re.match(r"^\d+ ", title) else ""
        toc.append({"tag": tag, "no": no, "title": title, "id": cid})
        html_parts.append('<section class="chapter" id="%s"><p class="ch-tag">%s</p><h2>%s</h2>%s</section>'
                          % (cid, tag, title, html_body))
    return "\n".join(html_parts), toc


def build_toc_html(toc):
    parts = []
    in_group = False
    for it in toc:
        if it["tag"] == "卷":
            if in_group:
                parts.append("</div>")
            in_group = True
            parts.append('<div class="dw-group"><div class="dw-vol">%s</div>' % it["title"])
            continue
        # 序/章/篇/终 全部作为可点击项平铺
        parts.append('<div class="dw-item" data-t="%s"><span class="dw-no">%s</span><span>%s</span></div>'
                     % (it["id"], it["no"] or "·", it["title"]))
    if in_group:
        parts.append("</div>")
    return "\n".join(parts)


def build_inline_toc(toc):
    """正文前的可见章目录:胶囊横排,点击平滑滚动到章。
    复用 .dw-item 结构,JS 的目录点击与当前章高亮自动对其生效。
    章数过多(如 31 章的幸福内在)由调用方决定是否生成。"""
    parts = ['<nav class="inline-toc" aria-label="章节目录"><h3 class="inline-toc-title">章节目录</h3><div class="inline-toc-list">']
    in_group = False
    for it in toc:
        if it["tag"] == "卷":
            if in_group:
                parts.append("</div></div>")
            in_group = True
            parts.append('<div class="inline-vol">%s<div class="inline-vol-c">' % it["title"])
            continue
        parts.append('<div class="dw-item toc-link" data-t="%s"><span class="dw-no">%s</span><span>%s</span></div>'
                     % (it["id"], it["no"] or "·", it["title"]))
    if in_group:
        parts.append("</div></div>")
    parts.append("</div></nav>")
    return "\n".join(parts)


def build_page(book, content_html, toc_html):
    return """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>%s · 在线阅读 · 世界一隅</title>
<style>%s</style>
</head>
<body data-theme="night" data-font="m">

<header class="topbar">
  <a class="tb-btn tb-back" href="%s">← 返回听书</a>
  <div class="tb-title">%s<span class="tb-sub">%s</span></div>
  <span class="tb-spacer"></span>
  <span class="tb-font">
    <button class="tb-btn" data-fs="s" type="button">A−</button>
    <button class="tb-btn" data-fs="m" type="button"><span>A</span></button>
    <button class="tb-btn" data-fs="l" type="button"><span>a</span></button>
  </span>
  <button class="tb-btn" id="th-toggle" type="button">白昼</button>
  <button class="tb-btn active" id="dw-toggle" type="button">目录</button>
</header>
<div class="progress"><i></i></div>

<aside class="drawer" id="drawer">
  %s
</aside>
<div class="scrim" id="scrim"></div>

<main class="wrap">
%s
  <div class="footer">
    <p>读到这里,故事就讲完了。也欢迎回去听有声书——</p>
    <a class="back" href="%s">回到听书页继续听 →</a>
  </div>
</main>

<script>%s</script>
</body>
</html>""" % (
        book["title"], CSS, book["listen_href"], book["title"], book["subtitle"],
        toc_html, content_html, book["listen_href"], JS,
    )


def render_extension(rec):
    """延伸阅读区块:读完这本书,引导去读/重读另外几本"""
    order_html = ""
    if rec.get("order"):
        order = "".join(
            '<p class="done">%s</p>' % o if ("已读" in o or "读完" in o) else '<p class="next">%s</p>' % o
            for o in rec["order"]
        )
        n_str = "四本书" if len(rec["order"]) > 3 else "三本书"
        order_html = '<div class="ext-order"><p class="ext-order-title">%s · 阅读顺序</p>%s</div>' % (n_str, order)
    cards = []
    for it in rec["items"]:
        cards.append(
            '<div class="ext-card">'
            '<p class="ext-pos">%s</p>'
            '<h4 class="ext-name">%s</h4>'
            '<p class="ext-core">%s</p>'
            '<div class="ext-row">'
            '<a class="ext-btn" href="/read/%s/">%s →</a>'
            '<a class="ext-listen" href="/audiobook/#book-%s">去听书 →</a>'
            "</div></div>" % (it["pos"], it["name"], it["core"],
                              it["bid"], it["btn"], it.get("anchor", it["bid"]))
        )
    return ('<section class="ext">'
            '<h3 class="ext-title">%s</h3>'
            '<p class="ext-guide">%s</p>'
            "%s"
            "%s"
            "</section>" % (rec["title"], rec["guide"], "".join(cards), order_html))


def main():
    for book in BOOKS:
        src = os.path.join(BS, book["file"])
        text = open(src, encoding="utf-8").read()
        chapters = split_chapters(text, book["mode"], book["title"])
        content_html, toc = render_chapters(chapters, book["mode"])
        if book.get("rec"):
            content_html += render_extension(book["rec"])
        toc_html = build_toc_html(toc)
        # 章数不多时正文前放可见目录;超过 16 章(幸福内在)保持抽屉
        inline_toc = build_inline_toc(toc) if len(toc) <= 16 else ""
        page = build_page(book, inline_toc + content_html, toc_html)
        out_dir = os.path.join(OUT_ROOT, book["id"])
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, "index.html")
        open(out, "w", encoding="utf-8").write(page)
        print("生成:", out, "(%d 章, %.0f KB)" % (len(chapters), len(page) / 1024))


if __name__ == "__main__":
    main()
