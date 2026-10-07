#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""项目资产页生成器 — 读取「资产商城」小程序资产清单,输出自包含 static/assets/index.html
数据源:F:/xiaochenxukaifa/资产商城/miniprogram/utils/assets.js(CommonJS,node 加载导出 JSON)
样式:深藏青底 + 金色(与技能总表同风格),前端分组筛选 + 关键词搜索,纯 JS,零依赖。
"""
import io
import json
import os
import subprocess
import datetime

# ---------- 品牌色(与全站一致) ----------
BG = "#0f1420"; PANEL = "#161c2b"; LINE = "#26314a"
FG = "#dfe6f3"; DIM = "#8b97ad"; ACCENT = "#c9a55c"; LINK = "#7fb3ff"

ASSETS_JS = r"F:/xiaochenxukaifa/资产商城/miniprogram/utils/assets.js"
NODE = os.environ.get("NODE_EXE", r"C:/Program Files/nodejs/node.exe")

TYPE_CN = {
    "project": "项目", "agent": "Agent", "script": "脚本",
    "skill": "技能", "bundle": "合集", "tool": "工具", "other": "其他",
}
TYPE_COLOR = {
    "project": "#7fb3ff", "agent": "#c9a55c", "script": "#6ee7a8",
    "skill": "#f0a35c", "bundle": "#e28bb4", "tool": "#8b97ad", "other": "#8b97ad",
}


def load_categories():
    """node 加载 assets.js,返回 categories JSON"""
    code = "const a=require(%r); console.log(JSON.stringify(a.categories));" % ASSETS_JS
    p = subprocess.run([NODE, "-e", code], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError("node 加载失败: %s" % p.stderr[:300])
    return json.loads(p.stdout)


def normalize(a, cat, sub=None):
    """统一资产字段 → dict(name/type/desc/tags/icon)"""
    name = a.get("name", a.get("id", "?"))
    desc = a.get("desc", "")
    typ = a.get("type", "tool")
    if typ not in TYPE_CN:
        typ = "tool"
    tags = list(a.get("tags") or [])
    if not tags and a.get("tag"):
        tags = [a["tag"]]
    if sub:
        tags.insert(0, sub.get("name", ""))
    return {
        "name": name,
        "type": typ,
        "desc": desc,
        "tags": [t for t in tags if t],
        "icon": a.get("icon", ""),
    }


def expand(cat):
    items = []
    for a in cat.get("assets") or []:
        items.append(normalize(a, cat))
    for sc in cat.get("subCategories") or []:
        for a in sc.get("assets") or []:
            items.append(normalize(a, cat, sc))
    return items


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def build_html(categories):
    cat_list = []
    flat = []
    for c in categories:
        items = expand(c)
        if not items:
            continue
        cat_list.append({"id": c["id"], "name": c["name"], "icon": c.get("icon", ""),
                         "desc": c.get("desc", ""), "n": len(items)})
        for it in items:
            it["cid"] = c["id"]
            flat.append(it)
    data = ",\n".join(
        '{c:"%s",n:"%s",t:"%s",d:"%s",g:"%s",i:"%s"}' % (
            it["cid"], esc(it["name"]), it["type"],
            esc(it["desc"]), esc(",".join(it["tags"])),
            esc(it["icon"]))
        for it in flat
    )
    type_opt = "".join('<option value="%s">%s</option>' % (k, v)
                       for k, v in TYPE_CN.items())
    cat_opts = "".join('<option value="%s">%s(%d)</option>' % (c["id"], c["name"], c["n"])
                       for c in cat_list)
    now = datetime.date.today().isoformat()
    total = len(flat)
    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>世界一隅 · 项目资产</title>
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
  #c, #t {{ padding:9px 12px; border-radius:8px; border:1px solid var(--line); background:#0e1424;
        color:var(--fg); font-size:13px; outline:none; }}
  .count {{ font-size:12px; color:var(--dim); margin-bottom:12px; }}
  .cards {{ display:grid; grid-template-columns:1fr; gap:10px; }}
  .card {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px 16px; }}
  .card:hover {{ border-color:var(--accent); }}
  .card .nm {{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; }}
  .card .ic {{ font-size:15px; }}
  .card .nm code {{ font-family:Consolas,monospace; font-size:13px; color:var(--accent); }}
  .card .type {{ font-size:10px; padding:2px 8px; border-radius:999px; border:1px solid var(--line); }}
  .card .tag {{ font-size:10px; color:var(--dim); border:1px solid var(--line); border-radius:999px;
                padding:2px 8px; }}
  .card .ds {{ font-size:12px; color:var(--dim); line-height:1.7; margin-top:6px; }}
  .card.hide {{ display:none; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>📦 项目资产</h1>
  <p class="meta">自研项目 / Agent / 脚本 / 技能目录 · 共 {total} 项 · {len(cat_list)} 个分类 · 生成于 {now}</p>
  <div class="filters">
    <input id="q" type="search" placeholder="搜索资产名或描述…" autocomplete="off">
    <select id="c">
      <option value="all">全部分类</option>
      {cat_opts}
    </select>
    <select id="t">
      <option value="all">全部类型</option>
      {type_opt}
    </select>
  </div>
  <p class="count" id="count">共 {total} 项</p>
  <div class="cards" id="cards"></div>
</div>
<script>
var DATA = [{data}];
var TC = {json.dumps(TYPE_CN, ensure_ascii=False)};
var TP = {json.dumps(TYPE_COLOR)};
var cardsEl = document.getElementById('cards');
var countEl = document.getElementById('count');
var qEl = document.getElementById('q');
var cEl = document.getElementById('c');
var tEl = document.getElementById('t');
function render() {{
  var q = qEl.value.trim().toLowerCase();
  var c = cEl.value, t = tEl.value;
  var html = '', shown = 0;
  DATA.forEach(function (it) {{
    if (c !== 'all' && it.c !== c) return;
    if (t !== 'all' && it.t !== t) return;
    if (q && it.n.toLowerCase().indexOf(q) < 0 && it.d.toLowerCase().indexOf(q) < 0
        && it.g.toLowerCase().indexOf(q) < 0) return;
    shown++;
    var tags = it.g ? it.g.split(',').filter(Boolean).map(function (x) {{
      return '<span class="tag">' + x + '</span>'; }}).join('') : '';
    html += '<div class="card"><div class="nm">' +
      (it.i ? '<span class="ic">' + it.i + '</span>' : '') +
      '<code>' + it.n + '</code>' +
      '<span class="type" style="color:' + (TP[it.t] || '') + ';border-color:' + (TP[it.t] || '') + '40;">' + (TC[it.t] || it.t) + '</span>' +
      tags + '</div>' +
      (it.d ? '<p class="ds">' + it.d + '</p>' : '') + '</div>';
  }});
  cardsEl.innerHTML = html;
  countEl.textContent = '共 ' + shown + ' 项';
}}
qEl.addEventListener('input', render);
cEl.addEventListener('change', render);
tEl.addEventListener('change', render);
render();
</script>
</body>
</html>
"""


def main():
    cats = load_categories()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static", "assets", "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    total = sum(len(expand(c)) for c in cats)
    io.open(out, "w", encoding="utf-8").write(build_html(cats))
    print("✅ 项目资产页:", out, f"({total} 项 / {len(cats)} 分类)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
