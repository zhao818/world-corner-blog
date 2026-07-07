# -*- coding: utf-8 -*-
"""B站视频发布 — Playwright自动化"""
import os, time
from .base import BasePlatform, get_platform_cookies

class BilibiliPlatform(BasePlatform):
    name = "bilibili"
    display_name = "B站"

    VIDEO_URL = "https://member.bilibili.com/platform/upload/video/frame"
    COOKIE_KEYS = ["SESSDATA", "bili_jct", "DedeUserID", "buvid3", "buvid4", "buvid_fp", "sid", "_uuid", "b_nut", "b_lsid"]

    def _inject_cookies(self, context):
        cookies = get_platform_cookies("bilibili")
        if not cookies.get("SESSDATA"):
            return False
        for key in self.COOKIE_KEYS:
            if cookies.get(key):
                context.add_cookies([{
                    "name": key,
                    "value": cookies[key],
                    "domain": ".bilibili.com",
                    "path": "/",
                }])
        return True

    def publish_video(self, filepath: str, title: str, desc: str = "", tags: list = None, cover_path: str = None) -> dict:
        from playwright.sync_api import sync_playwright
        if not os.path.exists(filepath):
            return self.error(f"文件不存在: {filepath}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            self._inject_cookies(context)
            page = context.new_page()

            try:
                page.goto(self.VIDEO_URL, timeout=30000)
                page.wait_for_load_state("domcontentloaded")
                time.sleep(5)

                if "passport.bilibili.com" in page.url:
                    return self.error("需要重新登录B站")

                page.wait_for_selector('.bcc-upload-wrapper', timeout=20000)
                page.locator('.bcc-upload-wrapper input[type="file"]').first.set_input_files(filepath)
                print(f"[B站] 视频已选择: {os.path.basename(filepath)}")

                # 等上传完成（"上传完成"文字出现），立刻设封面
                page.wait_for_selector('text=上传完成', timeout=180000)
                time.sleep(3)
                print("[B站] 上传完成")

                # ⭐ 第一步：设封面（上传完成后立即做）
                if cover_path and os.path.exists(cover_path):
                    try:
                        # 等封面可点击（'.cover-item'或'.cover-img'或'.edit-text'出现）
                        for _ in range(20):
                            found = page.eval_on_selector_all('.cover-item, .cover-img, .edit-text',
                                'els => { for(const el of els) { if(el.offsetParent !== null) { el.click(); return true; } } return false; }')
                            if found:
                                print("[B站] 已打开封面编辑器")
                                time.sleep(2)
                                break
                            time.sleep(1)
                        else:
                            raise Exception("封面区未出现")

                        # 点"拖拽图片或点击上传"区域
                        upload_area = page.locator('.sub-text:text("拖拽图片或点击上传")')
                        if upload_area.count() == 0:
                            upload_area = page.locator('[class*="upload-area"]').first
                        if upload_area.count() > 0:
                            with page.expect_file_chooser() as fc_info:
                                upload_area.first.click(force=True, timeout=5000)
                            file_chooser = fc_info.value
                            file_chooser.set_files(cover_path)
                            print("[B站] 封面已上传")
                            time.sleep(5)

                            # 点"完成"
                            for _ in range(15):
                                done = page.locator('.button.submit:has-text("完成"), .cover-editor-button .button.submit')
                                if done.count() > 0:
                                    done.first.click(force=True, timeout=3000)
                                    time.sleep(2)
                                    print("[B站] 封面编辑已完成")
                                    break
                                time.sleep(1)
                        else:
                            print("[B站] 未找到上传区域")
                    except Exception as e:
                        print(f"[B站] 封面处理跳过: {e}")

                # ⭐ 第二步：填标题+简介
                page.wait_for_selector('input[placeholder*="标题"]', timeout=30000)
                time.sleep(1)
                page.locator('input[placeholder*="标题"]').first.fill(title[:80])
                print(f"[B站] 标题: {title[:80]}")

                if desc:
                    el = page.locator('.ql-editor').first
                    el.click()
                    el.type(desc[:250], delay=20)

                try:
                    # 勾选"含AI生成内容"声明 — JS强制点击
                    clicked = page.eval_on_selector_all('li.bcc-option:has(span:text("含AI生成内容"))', 'els => { if(els.length>0){els[0].click();return true;} return false; }')
                    if clicked:
                        time.sleep(1)
                        print("[B站] 已勾选AI生成声明")
                except Exception as e:
                    print(f"[B站] 声明勾选跳过: {e}")

                try:
                    page.locator('span.submit-add').first.scroll_into_view_if_needed()
                    time.sleep(1)
                    page.locator('span.submit-add').first.click()
                    print("[B站] 已投稿")
                except Exception as e:
                    print(f"[B站] 投稿点击失败: {e}")
                    raise
                time.sleep(5)

                return self.ok({"url": self.VIDEO_URL})

            except Exception as e:
                return self.error(f"B站失败: {str(e)}")
            finally:
                browser.close()

    def publish(self, meta, body, cover_path=None):
        return self.publish_video(meta.get("video_path",""), meta.get("title",""), meta.get("digest",""))

from platforms import register
register(BilibiliPlatform())