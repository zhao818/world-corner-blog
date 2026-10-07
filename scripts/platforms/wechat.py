# -*- coding: utf-8 -*-
"""微信公众号发布模块 — 封面生成 → 上传素材 → 创建草稿"""
import json, os, requests, importlib.util
from typing import Optional

from .base import BasePlatform, get_platform_cookies, update_platform_cookies, DARK_BG, GOLD, BRAND
from . import register

class WechatPlatform(BasePlatform):
    name = "wechat"
    display_name = "公众号"

    APPID = "wx331b651c8159fdcb"

    def _get_secret(self) -> str:
        creds = get_platform_cookies("wechat")
        secret = creds.get("appsecret", "")
        if not secret:
            env_file = os.path.expanduser("~/.env_wx")
            if os.path.exists(env_file):
                for line in open(env_file, encoding="utf-8"):
                    line = line.strip()
                    if line.startswith("WX_APPSECRET="):
                        secret = line.split("=", 1)[1].strip()
                        break
        return secret

    def _get_token(self) -> Optional[str]:
        secret = self._get_secret()
        if not secret:
            return None
        r = requests.get(
            "https://api.weixin.qq.com/cgi-bin/token",
            params={"grant_type": "client_credential", "appid": self.APPID, "secret": secret},
            timeout=15,
        )
        data = r.json()
        token = data.get("access_token")
        if token:
            update_platform_cookies("wechat", {"access_token": token})
        return token

    def _generate_cover(self, title: str, subtitle: str = "", category: str = "AI提效", date: str = None) -> str:
        if not date:
            from datetime import datetime
            date = datetime.now().strftime("%Y.%m.%d")
        spec = importlib.util.spec_from_file_location(
            "cover_module",
            os.path.expanduser("~/claude-memory/global/tools/wechat-cover-template.py")
        )
        cover = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cover)
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output = os.path.join(script_dir, "articles", f"cover_{title[:10]}.jpg")
        return cover.generate_cover(
            title=title[:9],
            subtitle=subtitle[:17],
            category=category,
            date=date,
            output=output
        )

    def publish(self, meta: dict, body: str, cover_path: str = None) -> dict:
        title = meta.get("title", "")[:9]
        digest = meta.get("digest", meta.get("description", ""))[:17]

        if not cover_path:
            cover_path = self._generate_cover(title, digest)

        token = self._get_token()
        if not token:
            return self.error("无法获取 access_token，检查 ~/.env_wx 或 platform-cookies.json")

        with open(cover_path, "rb") as f:
            resp = requests.post(
                f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image",
                files={"media": ("cover.jpg", f, "image/jpeg")},
                timeout=30,
            )
        data = resp.json()
        thumb_media_id = data.get("media_id")
        if not thumb_media_id:
            return self.error(f"封面上传失败: {data}")

        html_body = self.md_to_html(body, meta)
        full_html = (
            "<section style=\"padding:20px;background:#ffffff;"
            "font-family:-apple-system,BlinkMacSystemFont,'Helvetica Neue','PingFang SC','Microsoft YaHei',sans-serif;"
            "color:#333;\">"
            f"{html_body}"
            "<p style=\"text-align:center;color:#999;margin-top:30px;font-size:14px;\">"
            f"关注公众号「{BRAND}」，获取更多内容</p></section>"
        )

        headers = {"Content-Type": "application/json; charset=utf-8"}
        draft_body = {
            "articles": [{
                "title": title,
                "author": BRAND,
                "digest": digest,
                "content": full_html,
                "thumb_media_id": thumb_media_id,
                "need_open_comment": 0,
                "only_fans_can_comment": 0,
            }]
        }
        resp = requests.post(
            f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}",
            data=json.dumps(draft_body, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            timeout=30,
        )
        result = resp.json()
        if "media_id" in result:
            return self.ok({"media_id": result["media_id"]})
        return self.error(f"创建草稿失败: {result}")

register(WechatPlatform())
