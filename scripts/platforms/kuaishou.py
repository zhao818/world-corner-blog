# -*- coding: utf-8 -*-
"""快手视频发布 — Playwright + 反检测"""
import os, time
from .base import BasePlatform, get_platform_cookies

class KuaishouPlatform(BasePlatform):
    name = "kuaishou"
    display_name = "快手"

    UPLOAD_URL = "https://cp.kuaishou.com/article/publish/video"
    COOKIE_KEYS = ["kuaishou.web.cp.api_st", "kuaishou.web.cp.jwt", "userId"]

    def _inject_cookies(self, context):
        cookies = get_platform_cookies("kuaishou")
        if not cookies.get("kuaishou.web.cp.api_st"):
            return False
        for key in self.COOKIE_KEYS:
            if cookies.get(key):
                context.add_cookies([{
                    "name": key,
                    "value": cookies[key],
                    "domain": ".kuaishou.com",
                    "path": "/",
                }])
        return True

    def _dismiss_joyride(self, page):
        """关掉所有 joyride 引导弹窗（逐个点完）"""
        for _ in range(25):
            clicked = page.eval_on_selector_all(
                '._button_3a31q_1._button-primary_3a31q_60, ._button_3a31q_1.button-primary_3a31q_60, [data-action="skip"]',
                'els => { for(const e of els) { if(e.offsetParent !== null) { e.click(); return true; } } return false; }'
            )
            if not clicked:
                break
            time.sleep(0.8)
        try:
            page.eval_on_selector_all('.react-joyride, #react-joyride-portal', 'els => { for(const e of els) e.remove(); }')
        except: pass

    def publish_video(self, filepath: str, title: str, desc: str = "", tags: list = None, cover_path: str = None) -> dict:
        from playwright.sync_api import sync_playwright
        if not os.path.exists(filepath):
            return self.error(f"文件不存在: {filepath}")

        with sync_playwright() as p:
            browser, context, page = self._launch_browser(p)
            self._inject_cookies(context)

            try:
                page.goto(self.UPLOAD_URL, timeout=30000)
                page.wait_for_load_state("domcontentloaded")
                time.sleep(5)

                if "login" in page.url or "passport" in page.url:
                    return self.error("快手Cookie已过期")

                self._dismiss_joyride(page)

                # 上传视频
                page.wait_for_selector('input[type="file"]', state='attached', timeout=15000)
                page.locator('input[type="file"]').first.set_input_files(filepath)
                print(f"[快手] 视频已选择: {os.path.basename(filepath)}")
                time.sleep(10)

                # 关上传后弹出的 joyride
                self._dismiss_joyride(page)

                # 填作品描述
                if desc:
                    try:
                        desc_el = page.locator('#work-description-edit, [contenteditable="true"]').first
                        if desc_el.count() > 0:
                            desc_el.click()
                            desc_el.type(desc[:500], delay=20)
                    except: pass

                # 发布 — 用JS点，绕过所有遮挡
                for _ in range(10):
                    self._dismiss_joyride(page)
                    for sel in [
                        '[class*="edit-section-btns"] [class*="button-primary"]',
                        'button:has-text("发布")',
                    ]:
                        clicked = page.eval_on_selector_all(sel, 'els => { for(const e of els) { if(e.offsetParent !== null) { e.click(); return true; } } return false; }')
                        if clicked:
                            print("[快手] 已点发布")
                            break
                    if clicked:
                        break
                    time.sleep(1)

                time.sleep(600)  # 等你检查完再关
                return self.ok({"url": self.UPLOAD_URL})

            except Exception as e:
                return self.error(f"快手失败: {str(e)}")
            finally:
                browser.close()

    def publish(self, meta, body, cover_path=None):
        return self.publish_video(meta.get("video_path",""), meta.get("title",""), meta.get("digest",""))

from platforms import register
register(KuaishouPlatform())
