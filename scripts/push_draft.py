# -*- coding: utf-8 -*-
"""推送文章到公众号草稿箱（含封面上传）"""
import json, requests, sys, os

APPID = "wx331b651c8159fdcb"
APPSECRET = "9b25e7466310c7971eeb777600697d3d"
AUTHOR = "美好需要创造"

html_path = os.path.join(os.path.dirname(__file__), "articles", "20260704_生态位法则.html")
with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

title = "生态位法则"
digest = "模型在自己家反而不如别人家"

# 封面图片路径
cover_path = os.path.join(os.path.dirname(__file__), "cover_intro.jpg")
if not os.path.exists(cover_path):
    print(f"❌ 封面图片不存在: {cover_path}")
    sys.exit(1)

# Step 1: 获取 access_token
print("Step 1: 获取 access_token...")
r = requests.get(
    "https://api.weixin.qq.com/cgi-bin/token",
    params={"grant_type": "client_credential", "appid": APPID, "secret": APPSECRET}
)
data = r.json()
if "access_token" not in data:
    print(f"失败: {data}")
    sys.exit(1)
token = data["access_token"]
print("token 获取成功")

# Step 2: 上传封面素材
print("Step 2: 上传封面素材...")
upload_url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image"
with open(cover_path, "rb") as f:
    resp = requests.post(upload_url, files={"media": (cover_path, f, "image/jpeg")})
upload_data = resp.json()
if "media_id" not in upload_data:
    print(f"❌ 上传封面失败: {upload_data}")
    sys.exit(1)
thumb_media_id = upload_data["media_id"]
print(f"✅ 封面上传成功: {thumb_media_id}")

# Step 3: 创建草稿
print(f"创建草稿「{title}」...")
headers = {"Content-Type": "application/json; charset=utf-8"}
body = {
    "articles": [{
        "title": title[:9],
        "author": AUTHOR,
        "digest": digest[:17],
        "content": content,
        "thumb_media_id": thumb_media_id,
        "need_open_comment": 0,
        "only_fans_can_comment": 0,
    }]
}

r = requests.post(
    f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}",
    data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
    headers=headers
)
result = r.json()
if "media_id" in result:
    print(f"草稿创建成功! media_id: {result['media_id']}")
else:
    print(f"失败: {result}")
