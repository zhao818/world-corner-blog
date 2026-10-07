# -*- coding: utf-8 -*-
"""小红书发布 — Playwright + Shadow DOM穿透"""
import os, time
from .base import BasePlatform, get_platform_cookies

class XiaohongshuPlatform(BasePlatform):
    name = "xiaohongshu"
    display_name = "小红书"

    UPLOAD_URL = "https://creator.xiaohongshu.com/publish/publish"
    COOKIE_KEYS = ["web_session", "a1"]

    def _inject_cookies(self, context):
        cookies = get_platform_cookies("xiaohongshu")
        if not cookies.get("a1"):
            return False
        for key in cookies:
            if key in ("web_session", "a1", "webId", "x-user-id-creator.xiaohongshu.com",
                       "access-token-creator.xiaohongshu.com", "galaxy_creator_session_id",
                       "id_token", "xsecappid", "customerClientId", "customer-sso-sid",
                       "galaxy.creator.beaker.session.id"):
                context.add_cookies([{
                    "name": key,
                    "value": cookies[key],
                    "domain": "creator.xiaohongshu.com",
                    "path": "/",
                }])
        return True

    def publish_video(self, filepath: str, title: str, desc: str = "", tags: list = None, cover_path: str = None) -> dict:
        if not os.path.exists(filepath):
            return self.error(f"文件不存在: {filepath}")

        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser, context, page = self._launch_browser(p)

            context.add_init_script("""
                const origAttach = Element.prototype.attachShadow;
                Element.prototype.attachShadow = function(init) {
                    return origAttach.call(this, { ...init, mode: 'open' });
                };
            """)

            has_cookies = self._inject_cookies(context)

            try:
                page.goto(self.UPLOAD_URL, timeout=30000)
                page.wait_for_load_state("domcontentloaded")
                time.sleep(5)

                if "login" in page.url:
                    if has_cookies:
                        print("[小红书] Cookie 已失效，需要扫码登录")
                    else:
                        print("[小红书] 无有效 Cookie，请在浏览器中扫码登录")
                    print("[小红书] 等待扫码...")
                    while "login" in page.url:
                        time.sleep(2)
                    print("[小红书] 登录成功")
                    page.wait_for_load_state("domcontentloaded")
                    time.sleep(5)
                else:
                    print("[小红书] Cookie 有效，已登录")
                time.sleep(2)

                page.wait_for_selector('input[type="file"]', state='attached', timeout=30000)
                page.locator('input[type="file"]').first.set_input_files(filepath)
                print(f"[小红书] 视频已选择: {os.path.basename(filepath)}")

                page.wait_for_selector('input[placeholder*="标题"]', timeout=60000)
                time.sleep(2)
                page.locator('input[placeholder*="标题"]').first.fill(title[:20])
                print(f"[小红书] 标题已填: {title[:20]}")

                if desc:
                    desc_input = page.locator('[contenteditable="true"]').first
                    if desc_input.count() > 0:
                        desc_input.click()
                        page.keyboard.type(desc[:300], delay=20)

                if tags:
                    tag_input = page.locator('input[placeholder*="标签"]').first
                    if tag_input.count() > 0:
                        for tag in tags[:3]:
                            tag_input.fill(tag)
                            page.keyboard.press("Enter")
                            time.sleep(0.5)

                try:
                    page.locator('button:has-text("发布")').last.click()
                    print("[小红书] 已点击发布按钮")
                except Exception as e:
                    return self.error(f"点击发布按钮失败: {str(e)}")

                time.sleep(5)
                return self.ok({"url": self.UPLOAD_URL})

            except Exception as e:
                return self.error(f"小红书失败: {str(e)}")
            finally:
                browser.close()

    def publish(self, meta, body, cover_path=None):
        return self.publish_video(
            meta.get("video_path", ""),
            meta.get("title", ""),
            meta.get("digest", ""),
            meta.get("tags", [])
        )

from platforms import register
register(XiaohongshuPlatform())
