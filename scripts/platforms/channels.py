# -*- coding: utf-8 -*-
"""视频号发布 — Playwright + Shadow DOM穿透"""
import os, time
from .base import BasePlatform, get_platform_cookies

class ChannelsPlatform(BasePlatform):
    name = "channels"
    display_name = "视频号"

    UPLOAD_URL = "https://channels.weixin.qq.com/platform/post/create"
    COOKIE_KEYS = ["wxuin", "sessionid"]

    def _inject_cookies(self, context):
        cookies = get_platform_cookies("channels")
        if not cookies.get("wxuin"):
            return False
        for key in self.COOKIE_KEYS:
            if cookies.get(key):
                context.add_cookies([{
                    "name": key,
                    "value": cookies[key],
                    "domain": "channels.weixin.qq.com",
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

            # 先试 Cookie 登录
            has_cookies = self._inject_cookies(context)

            try:
                page.goto(self.UPLOAD_URL, timeout=30000)
                page.wait_for_load_state("domcontentloaded")
                time.sleep(5)

                # 判断是否登录
                if "login" in page.url:
                    if has_cookies:
                        print("[视频号] Cookie 已失效，需要扫码登录")
                    else:
                        print("[视频号] 无有效 Cookie，请在浏览器中扫码登录")
                    print("[视频号] 等待扫码...")
                    while "login" in page.url:
                        time.sleep(2)
                    print("[视频号] 登录成功")
                    page.wait_for_load_state("domcontentloaded")
                    time.sleep(5)
                else:
                    print("[视频号] Cookie 有效，已登录")
                time.sleep(2)
                page.locator('input[type="file"]').first.set_input_files(filepath)
                print(f"[视频号] 视频已选择: {os.path.basename(filepath)}")

                print("[视频号] 等待上传完成...")
                time.sleep(8)

                # 暴力清除所有弹窗
                page.evaluate("""() => {
                    document.querySelectorAll('[class*="dialog"],[class*="modal"],[class*="mask"],[class*="overlay"],[class*="joyride"],[class*="tooltip"]')
                        .forEach(el => el.remove());
                }""")
                time.sleep(1)

                # 用 AI 识别当前页面
                analysis = self.inspect_step(page, "post_upload")
                print(f"  AI分析: {analysis}")

                # 再试标题输入
                title_input = page.locator('.form-item-body input:not([type="file"]):not([type="range"])').first
                if title_input.count() == 0:
                    return self.error("找不到标题输入框")
                title_input.fill(title[:20])

                if desc:
                    editor = page.locator('[contenteditable][data-placeholder*="描述"], .input-editor').first
                    if editor.count() > 0:
                        editor.click()
                        page.keyboard.type(desc[:500], delay=20)
                    else:
                        print("[视频号] 未找到描述输入框，跳过")

                page.locator('button:has-text("发表")').first.click()
                print("[视频号] 已发表")
                page.wait_for_url("**/post/list**", timeout=60000)
                time.sleep(3)

                return self.ok({"url": "https://channels.weixin.qq.com/platform/post/list"})

            except Exception as e:
                return self.error(f"视频号失败: {str(e)}")
            finally:
                browser.close()

    def publish(self, meta, body, cover_path=None):
        return self.publish_video(meta.get("video_path",""), meta.get("title",""), meta.get("digest",""))

from platforms import register
register(ChannelsPlatform())