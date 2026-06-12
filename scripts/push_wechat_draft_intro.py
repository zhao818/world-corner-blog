# -*- coding: utf-8 -*-
"""
推送《照见幸福》引言到公众号草稿箱
步骤: 生成封面 → 获取access_token → 上传封面素材 → 创建草稿
"""
import json
import sys
import os
import requests
from datetime import date

# ===== 配置 =====
APPID = "wx331b651c8159fdcb"
APPSECRET = "9b25e7466310c7971eeb777600697d3d"
TITLE = "文学更懂你的心"          # ≤9中文字
SUMMARY = "心理学给地图，文学陪你走路"  # ≤17中文字
COVER_OUTPUT = "cover_intro.jpg"
HTML_FILE = os.path.join(os.path.dirname(__file__),
    "..", "content", "posts", "systems-thinking", "wechat-intro-literary-happiness.html")

# ===== Step 0: 引入封面模板 =====
sys.path.insert(0, os.path.expanduser("~/claude-memory/global/tools"))
import importlib.util
cover_spec = importlib.util.spec_from_file_location(
    "wechat_cover_template",
    os.path.expanduser("~/claude-memory/global/tools/wechat-cover-template.py")
)
cover_module = importlib.util.module_from_spec(cover_spec)
cover_spec.loader.exec_module(cover_module)
generate_cover = cover_module.generate_cover

# WSL环境下字体路径修正
cover_module.FONT_PATH = "/mnt/c/Windows/Fonts/msyh.ttc"

print("=" * 50)
print("Step 1: 生成封面...")
cover_path = generate_cover(
    title="文学更懂你的心",
    subtitle="心理学给地图，文学陪你走路",
    category="随笔",
    date="2026.06.13",
    output=COVER_OUTPUT
)

# ===== Step 2: 获取 access_token =====
print("Step 2: 获取 access_token...")
token_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={APPSECRET}"
resp = requests.get(token_url)
token_data = resp.json()
if "access_token" not in token_data:
    print(f"❌ 获取token失败: {token_data}")
    sys.exit(1)
access_token = token_data["access_token"]
print(f"✅ token获取成功: {access_token[:20]}...")

# ===== Step 3: 上传封面为永久素材 =====
print("Step 3: 上传封面素材...")
upload_url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={access_token}&type=image"
with open(cover_path, "rb") as f:
    resp = requests.post(upload_url, files={"media": (cover_path, f, "image/jpeg")})
upload_data = resp.json()
if "media_id" not in upload_data:
    print(f"❌ 上传封面失败: {upload_data}")
    sys.exit(1)
thumb_media_id = upload_data["media_id"]
print(f"✅ 封面上传成功: {thumb_media_id}")

# ===== Step 4: 读取HTML正文 =====
print("Step 4: 读取HTML正文...")
with open(HTML_FILE, "r", encoding="utf-8") as f:
    html_lines = f.readlines()

# 跳过注释行（<!-- 和 -->）
content_lines = []
in_comment = False
for line in html_lines:
    if "<!--" in line:
        in_comment = True
        continue
    if "-->" in line:
        in_comment = False
        continue
    if not in_comment:
        content_lines.append(line)

content_html = "".join(content_lines).strip()
print(f"✅ HTML正文读取成功: {len(content_html)} 字符")

# ===== Step 5: 创建草稿 =====
print("Step 5: 创建草稿...")
draft_url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={access_token}"

draft_data = {
    "articles": [{
        "title": TITLE,
        "author": "美好需要创造",
        "digest": SUMMARY,
        "content": content_html,
        "content_source_url": "",
        "thumb_media_id": thumb_media_id,
        "need_open_comment": 1,
        "only_fans_can_comment": 0,
    }]
}

headers = {"Content-Type": "application/json; charset=utf-8"}
resp = requests.post(
    draft_url,
    data=json.dumps(draft_data, ensure_ascii=False).encode("utf-8"),
    headers=headers
)
result = resp.json()
print(f"API返回: {json.dumps(result, ensure_ascii=False, indent=2)}")

if "media_id" in result:
    print(f"\n✅✅✅ 草稿创建成功！")
    print(f"   草稿 media_id: {result['media_id']}")
    print(f"   请前往公众号后台 → 草稿箱 → 编辑发布")
else:
    errcode = result.get("errcode", "?")
    errmsg = result.get("errmsg", "?")
    print(f"\n❌ 草稿创建失败: errcode={errcode}, errmsg={errmsg}")
    if errcode == 45003:
        print("   → 标题超长（≤9中文字）")
    elif errcode == 45004:
        print("   → 摘要超长（≤17中文字）")
    elif errcode == 40164:
        print("   → IP未加白名单，请在公众号后台添加当前机器IP")
