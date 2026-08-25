#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技能总表生成器 — 汇总三处技能源,输出自包含 static/skills/index.html
来源:
  1. Claude 全局技能   C:/Users/zhaot/.claude/skills/*/SKILL.md
  2. GitHub App 捆绑   C:/Users/zhaot/AppData/Roaming/com.github.githubapp/app-skills/*/SKILL.md
  3. 项目内技能         I:/灵魂之觅/.codebuddy/skills + .codex/skills
样式:深藏青底 + 金色(与知识库检索树同风格),前端分组筛选 + 关键词搜索,纯 JS,零依赖。
"""
import io
import os
import re
import datetime

# ---------- 品牌色(与全站一致) ----------
BG = "#0f1420"; PANEL = "#161c2b"; LINE = "#26314a"
FG = "#dfe6f3"; DIM = "#8b97ad"; ACCENT = "#c9a55c"; LINK = "#7fb3ff"

SOURCES = [
    ("claude", "Claude 全局技能", "C:/Users/zhaot/.claude/skills"),
    ("githubapp", "GitHub App 捆绑技能", "C:/Users/zhaot/AppData/Roaming/com.github.githubapp/app-skills"),
    ("project", "项目内技能(codebuddy + codex)", "I:/灵魂之觅/.codebuddy/skills"),
]
EXTRA_PROJECT = "I:/灵魂之觅/.codex/skills"


def read_skill_meta(skill_dir):
    """读取单个技能目录的 SKILL.md,提取 name + description"""
    path = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(path):
        return None
    try:
        text = io.open(path, encoding="utf-8", errors="replace").read()
    except Exception:
        return None
    name = os.path.basename(os.path.normpath(skill_dir))
    # description: 兼容 ">-\n  多行" 与单行 "xxx"
    m = re.search(r'^description:\s*(.*)$', text, re.M)
    desc = ""
    if m:
        first = m.group(1).strip()
        if first.startswith('>'):
            # 折叠块:收集后续缩进行
            lines = []
            for line in text.splitlines()[m.end():]:
                if line.startswith('  ') or line.startswith('\t'):
                    lines.append(line.strip())
                else:
                    break
            desc = ' '.join(lines)
        else:
            desc = first.strip().strip('"').strip("'")
    desc = re.sub(r'\s+', ' ', desc).strip()
    return {"name": name, "description": desc}


def collect(group_key, group_name, *roots):
    items = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for d in sorted(os.listdir(root)):
            p = os.path.join(root, d)
            if os.path.isdir(p):
                meta = read_skill_meta(p)
                if meta:
                    items.append({"group": group_key, "gname": group_name, **meta})
    return items


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def build_html(all_items):
    groups = []
    seen = set()
    for gk in ("claude", "githubapp", "project"):
        for it in all_items:
            if it["group"] == gk and gk not in seen:
                seen.add(gk)
                groups.append((gk, it["gname"]))
    data = ",\n".join(
        '{g:"%s",gn:"%s",n:"%s",d:"%s"}' % (
            it["group"], esc(it["gname"]), esc(it["name"]), esc(it["description"]))
        for it in all_items
    )
    group_options = "".join(
        '<option value="%s">%s</option>' % (gk, gn) for gk, gn in groups
    )
    now = datetime.date.today().isoformat()
    total = len(all_items)

    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>世界一隅 · 技能总表</title>
<style>
  :root {{ --bg:{BG}; --panel:{PANEL}; --line:{LINE}; --fg:{FG}; --dim:{DIM};
          --accent:{ACCENT}; --link:{LINK}; }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--fg); font-family:"Microsoft YaHei","PingFang SC",sans-serif; }}
  .wrap {{ max-width:980px; margin:0 auto; padding:36px 24px 60px; }}
  h1 {{ font-size:24px; color:var(--accent); letter-spacing:1px; }}
  .meta {{ font-size:12px; color:var(--dim); margin:8px 0 20px; }}
  .filters {{ display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin-bottom:18px; }}
  #q {{ flex:1; min-width:220px; padding:9px 12px; border-radius:8px; border:1px solid var(--line);
        background:#0e1424; color:var(--fg); font-size:13px; outline:none; }}
  #q:focus {{ border-color:var(--accent); }}
  #g {{ padding:9px 12px; border-radius:8px; border:1px solid var(--line); background:#0e1424;
        color:var(--fg); font-size:13px; outline:none; }}
  .count {{ font-size:12px; color:var(--dim); margin-bottom:12px; }}
  .cards {{ display:grid; grid-template-columns:1fr; gap:10px; }}
  .card {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px 16px; }}
  .card:hover {{ border-color:var(--accent); }}
  .card .nm {{ display:flex; align-items:center; gap:8px; }}
  .card .nm code {{ font-family:Consolas,monospace; font-size:13px; color:var(--accent); }}
  .card .tag {{ font-size:10px; color:var(--dim); border:1px solid var(--line); border-radius:999px;
                padding:2px 8px; }}
  .card .ds {{ font-size:12px; color:var(--dim); line-height:1.7; margin-top:6px; }}
  .card.hide {{ display:none; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>🛠 技能总表</h1>
  <p class="meta">Claude Code / GitHub App / 项目内技能清单 · 共 {total} 项 · 生成于 {now}</p>
  <div class="filters">
    <input id="q" type="search" placeholder="搜索技能名或用途…" autocomplete="off">
    <select id="g">
      <option value="all">全部分组</option>
      {group_options}
    </select>
  </div>
  <p class="count" id="count">共 {total} 项</p>
  <div class="cards" id="cards"></div>
</div>
<script>
var DATA = [{data}];
var cardsEl = document.getElementById('cards');
var countEl = document.getElementById('count');
var qEl = document.getElementById('q');
var gEl = document.getElementById('g');
function render() {{
  var q = qEl.value.trim().toLowerCase();
  var g = gEl.value;
  var html = '', shown = 0;
  DATA.forEach(function (it) {{
    if (g !== 'all' && it.g !== g) return;
    if (q && (it.n.toLowerCase().indexOf(q) < 0) && (it.d.toLowerCase().indexOf(q) < 0)) return;
    shown++;
    html += '<div class="card"><div class="nm"><code>' + it.n + '</code>' +
            '<span class="tag">' + it.gn + '</span></div>' +
            (it.d ? '<p class="ds">' + it.d + '</p>' : '') + '</div>';
  }});
  cardsEl.innerHTML = html;
  countEl.textContent = '共 ' + shown + ' 项' + (g !== 'all' || q ? '' : '');
}}
qEl.addEventListener('input', render);
gEl.addEventListener('change', render);
render();
</script>
</body>
</html>
"""


def main():
    all_items = []
    for gk, gn, root in SOURCES:
        all_items.extend(collect(gk, gn, root))
    # 项目补充 .codex(单独目录)
    all_items.extend(collect("project", "项目内技能(codebuddy + codex)", EXTRA_PROJECT))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static", "skills", "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    io.open(out, "w", encoding="utf-8").write(build_html(all_items))
    print("✅ 技能总表:", out, f"({len(all_items)} 项)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
