# -*- coding: utf-8 -*-
"""重新生成封面 + 重新推送草稿"""
import json, requests, sys, os, importlib.util

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 加载封面模板
spec = importlib.util.spec_from_file_location(
    "cover_module",
    os.path.expanduser("~/claude-memory/global/tools/wechat-cover-template.py")
)
cover = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cover)

# 生成封面
print("Step 1: 生成封面...")
cover_path = cover.generate_cover(
    title="生态位法则",
    subtitle="模型在自己家反而不如别人家",
    category="推理",
    date="2026.07.04",
    output=os.path.join(SCRIPT_DIR, "articles", "cover_生态位法则.jpg")
)
print(f"封面已生成: {cover_path}")

APPID = "wx331b651c8159fdcb"
APPSECRET = "9b25e7466310c7971eeb777600697d3d"
AUTHOR = "美好需要创造"

# 获取 token
print("Step 2: 获取 access_token...")
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

# 上传封面
print("Step 3: 上传封面素材...")
with open(cover_path, "rb") as f:
    r = requests.post(
        f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image",
        files={"media": ("cover.jpg", f, "image/jpeg")}
    )
data = r.json()
if "media_id" not in data:
    print(f"上传封面失败: {data}")
    sys.exit(1)
cover_media_id = data["media_id"]
print(f"封面上传成功: {cover_media_id}")

# 读文章 HTML
html_path = os.path.join(SCRIPT_DIR, "articles", "20260704_生态位法则.html")
with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

# 创建草稿
print("Step 4: 创建草稿...")
headers = {"Content-Type": "application/json; charset=utf-8"}
body = {
    "articles": [{
        "title": "生态位法则",
        "author": AUTHOR,
        "digest": "模型在自己家反而不如别人家",
        "content": content,
        "thumb_media_id": cover_media_id,
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
