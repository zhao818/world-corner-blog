# -*- coding: utf-8 -*-
"""推送AI提效三套路文章到公众号"""
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
    output=os.path.join(SCRIPT_DIR, "articles", "cover_ai_santao.jpg")
)
print(f"封面: {cover_path}")

APPID = "wx331b651c8159fdcb"
APPSECRET = "9b25e7466310c7971eeb777600697d3d"
AUTHOR = "美好需要创造"

print("获取 token...")
r = requests.get(
    "https://api.weixin.qq.com/cgi-bin/token",
    params={"grant_type": "client_credential", "appid": APPID, "secret": APPSECRET}
)
data = r.json()
if "access_token" not in data:
    print(f"token失败: {data}")
    sys.exit(1)
token = data["access_token"]
print("token OK")

print("上传封面...")
with open(cover_path, "rb") as f:
    r = requests.post(
        f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image",
        files={"media": ("cover.jpg", f, "image/jpeg")}
    )
data = r.json()
if "media_id" not in data:
    print(f"封面上传失败: {data}")
    sys.exit(1)
cover_media_id = data["media_id"]
print(f"封面 media_id: {cover_media_id}")

md_path = os.path.join(SCRIPT_DIR, "articles", "20260705_2109_2026_AI提效实战：从8个造轮子项目.md")
with open(md_path, "r", encoding="utf-8") as f:
    md = f.read()

parts = md.split("---")
body_md = parts[0].strip()

def md_to_html(text):
    lines = text.split("\n")
    html = []
    for line in lines:
        line = line.rstrip()
        if line.startswith("# "):
            html.append(f"<h2 style=\"color:#1a1a2e;border-left:4px solid #c8a03c;padding-left:12px;margin:20px 0 15px;\">{line[2:]}</h2>")
        elif line.startswith("## "):
            html.append(f"<h3 style=\"color:#1a1a2e;margin:18px 0 10px;\">{line[3:]}</h3>")
        elif line.startswith("✦"):
            html.append(f'<p style="color:#c8a03c;font-weight:bold;font-size:18px;margin:15px 0;">{line}</p>')
        elif line.strip() == "":
            pass
        elif line.strip().startswith("- ") or line.strip().startswith("* "):
            html.append(f"<p style=\"margin:5px 0;padding-left:2em;\">• {line.strip()[2:]}</p>")
        else:
            html.append(f"<p style=\"text-indent:2em;line-height:1.8;font-size:16px;margin:10px 0;\">{line}</p>")
    return "".join(html)

body_html = md_to_html(body_md)
full_html = (
    "<section style=\"padding:20px;background:#ffffff;"
    "font-family:-apple-system,BlinkMacSystemFont,'Helvetica Neue','PingFang SC','Microsoft YaHei',sans-serif;"
    "color:#333;\">"
    f"{body_html}"
    "<p style=\"text-align:center;color:#999;margin-top:30px;font-size:14px;\">"
    "关注公众号「美好需要创造」，获取更多AI提效干货</p>"
    "</section>"
)

print("创建草稿...")
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
r = requests.post(
    f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}",
    data=json.dumps(draft_body, ensure_ascii=False).encode("utf-8"),
    headers=headers
)
result = r.json()
if "media_id" in result:
    print(f"✅ 草稿创建成功! media_id: {result['media_id']}")
else:
    print(f"❌ 失败: {result}")
