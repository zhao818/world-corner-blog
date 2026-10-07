# -*- coding: utf-8 -*-
"""推送文章：别拿错剧本 → 公众号草稿 + 仪表盘登记"""
import sys, os, json, re
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

ARTICLE_FILE = os.path.join(SCRIPT_DIR, "articles", "20260706_Claude定位_内容创作者.md")

# ── Step 1: 解析 frontmatter ──
print("解析文章...")
with open(ARTICLE_FILE, "r", encoding="utf-8") as f:
    raw = f.read()

m = re.search(r'^---\s*\n(.+?)\n---', raw, re.DOTALL)
if not m:
    print("❌ frontmatter 解析失败")
    sys.exit(1)

fm = {}
for line in m.group(1).strip().split("\n"):
    if ":" in line:
        k, v = line.split(":", 1)
        fm[k.strip()] = v.strip().strip('"')

title = fm.get("title", "")
digest = fm.get("digest", "")
body_md = raw.split("---", 2)[2].strip()

print(f"  标题: {title}")
print(f"  摘要: {digest}")

# ── Step 2: 发布到公众号 ──
print("\n推送公众号草稿...")
from platforms.wechat import WechatPlatform

wp = WechatPlatform()
result = wp.publish(
    meta={"title": title, "digest": digest},
    body=body_md,
)
if not result.get("ok"):
    print(f"❌ 发布失败: {result.get('error')}")
    sys.exit(1)

media_id = result.get("media_id")
print(f"✅ 草稿创建成功: {media_id}")

# ── Step 3: 登记仪表盘 ──
print("\n登记仪表盘...")
from content_dashboard import RegistryManager

rm = RegistryManager()
reg = rm.load()

entry = {
    "id": f"20260706_{datetime.now().strftime('%H%M')}_{title}",
    "title": title,
    "digest": digest,
    "created": datetime.now().isoformat(),
    "track": "thinking",
    "platforms": {"wechat": {"status": "pending", "url": "", "media_id": media_id}},
    "sources": [],
}
reg["pieces"].insert(0, entry)
rm.save(reg)
print(f"✅ 仪表盘已登记")
print(f"\n🎉 全部完成: {title} → 公众号草稿箱")
