#!/usr/bin/env python3
"""推公众号草稿：技术越强，人越累？"""
import sys, os, json
sys.path.insert(0, os.path.expanduser("~/world-corner-blog/scripts"))
from platforms.wechat import WechatPlatform

meta = {
    "title": "技术越强，人越累",
    "description": "效率提高≠生活变好",
    "tags": ["AI", "社会观察", "效率"]
}

article_path = os.path.expanduser("~/knowledge-hub/hot-topics/2026-07-03-tech-anxiety-gap/article.md")
with open(article_path, "r", encoding="utf-8") as f:
    body_md = f.read()

wp = WechatPlatform()
result = wp.publish(meta, body_md)
print(json.dumps(result, ensure_ascii=False, indent=2))