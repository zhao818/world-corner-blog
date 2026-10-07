# -*- coding: utf-8 -*-
"""抖音视频发布 — Playwright + 扫码登录 + 反检测"""
import os, time
from .base import BasePlatform, get_platform_cookies

class DouyinPlatform(BasePlatform):
    name = "douyin"
    display_name = "抖音"

    CREATOR_URL = "https://creator.douyin.com/creator-micro/content/upload"
    COOKIE_KEYS = ["sessionid", "sessionid_ss", "sid_tt", "sid_guard", "uid_tt", "uid_tt_ss", "passport_csrf_token", "ttwid", "odin_tt", "UIFID"]

    def publish_video(self, filepath: str, title: str, desc: str = "", tags: list = None, cover_path: str = None) -> dict:
        from playwright.sync_api import sync_playwright
        if not os.path.exists(filepath):
            return self.error(f"文件不存在: {filepath}")

        with sync_playwright() as p:
            browser, context, page = self._launch_browser(p)
            cookies = get_platform_cookies("douyin")
            for k in self.COOKIE_KEYS:
                v = cookies.get(k)
                if v:
                    context.add_cookies([{'name':k,'value':v,'domain':'.douyin.com','path':'/'}])
            if cookies.get("passport_csrf_token"):
                context.add_cookies([{'name':'csrf_session_id','value':cookies['passport_csrf_token'],'domain':'creator.douyin.com','path':'/'}])

            try:
                page.goto(self.CREATOR_URL, timeout=30000)
                page.wait_for_load_state("domcontentloaded")
                time.sleep(5)

                # 检查是否需要扫码
                has_login_ui = page.eval_on_selector_all('text=扫码登录',
                    'els => els.length > 0 && els.some(e => e.offsetParent !== null)')
                if has_login_ui:
                    print("[抖音] 需要扫码，请用抖音扫码登录...")
                    # 等扫码完成（直到登录UI消失）
                    for _ in range(120):
                        still_login = page.eval_on_selector_all('text=扫码登录',
                            'els => els.length > 0 && els.some(e => e.offsetParent !== null)')
                        if not still_login:
                            print("[抖音] 扫码成功")
                            # 刷新页面加载上传区
                            page.goto(self.CREATOR_URL, timeout=30000)
                            page.wait_for_load_state("domcontentloaded")
                            time.sleep(5)
                            break
                        time.sleep(2)
                    else:
                        return self.error("扫码超时")

                # 点"发布视频"按钮
                btn = page.get_by_text('发布视频', exact=True)
                if btn.count() > 0:
                    btn.first.click()
                    time.sleep(3)

                page.wait_for_selector('input[type="file"]', timeout=20000)
                page.locator('input[type="file"]').first.set_input_files(filepath)
                print(f"[抖音] 视频已选择: {os.path.basename(filepath)}")

                page.wait_for_url("**/post/video*", timeout=120000)
                time.sleep(3)

                try:
                    page.locator('button:has-text("我知道了")').first.click(timeout=3000)
                except: pass

                page.locator('input.semi-input').first.fill(title[:55])
                print(f"[抖音] 标题: {title[:55]}")

                if desc:
                    el = page.locator('[contenteditable="true"]').first
                    el.click()
                    el.type(desc[:200], delay=20)

                time.sleep(10)
                page.locator('button:has-text("发布"):not(:has-text("发布视频"))').last.click()
                print("[抖音] 已发布")
                time.sleep(5)

                return self.ok({"url": self.CREATOR_URL})

            except Exception as e:
                return self.error(f"抖音失败: {str(e)}")
            finally:
                browser.close()

    def publish(self, meta, body, cover_path=None):
        return self.publish_video(meta.get("video_path",""), meta.get("title",""), meta.get("digest",""))

from platforms import register
register(DouyinPlatform())
