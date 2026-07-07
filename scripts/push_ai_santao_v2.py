# -*- coding: utf-8 -*-
"""推送AI提效三套路V2到公众号"""
import json, requests, sys, os, importlib.util

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

spec = importlib.util.spec_from_file_location(
    "cover_module",
    os.path.expanduser("~/claude-memory/global/tools/wechat-cover-template.py")
)
cover = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cover)
cover_path = cover.generate_cover(
    title="AI提效三套路",
    subtitle="从8个造轮子项目总结",
    category="AI提效",
    date="2026.07.05",
    output=os.path.join(SCRIPT_DIR, "articles", "cover_ai_santao_v2.jpg")
)
print(f"封面: {cover_path}")

APPID = "wx331b651c8159fdcb"
APPSECRET = "9b25e7466310c7971eeb777600697d3d"
AUTHOR = "美好需要创造"

r = requests.get(
    "https://api.weixin.qq.com/cgi-bin/token",
    params={"grant_type": "client_credential", "appid": APPID, "secret": APPSECRET}
)
token = r.json()["access_token"]
print("token OK")

with open(cover_path, "rb") as f:
    resp = requests.post(
        f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image",
        files={"media": ("cover.jpg", f, "image/jpeg")}
    )
cover_media_id = resp.json()["media_id"]
print(f"封面 media_id: {cover_media_id}")

html_path = os.path.join(SCRIPT_DIR, "articles", "20260705_ai_santao_v2.html")
with open(html_path, "r", encoding="utf-8") as f:
    full_html = f.read()

headers = {"Content-Type": "application/json; charset=utf-8"}
draft_body = {
    "articles": [{
        "title": "AI提效三套路",
        "author": AUTHOR,
        "digest": "从8个造轮子项目总结",
        "content": full_html,
        "thumb_media_id": cover_media_id,
        "need_open_comment": 0,
        "only_fans_can_comment": 0,
    }]
}
resp = requests.post(
    f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}",
    data=json.dumps(draft_body, ensure_ascii=False).encode("utf-8"),
    headers=headers
)
result = resp.json()
if "media_id" in result:
    print(f"✅ 草稿更新成功! media_id: {result['media_id']}")
else:
    print(f"❌ 失败: {result}")
