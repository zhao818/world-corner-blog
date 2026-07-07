"""
爱发电（afdian.net）文章发布模块

认证方式: Playwright 浏览器自动化 + Cookie 注入
内容类型: 创作者文章/动态（富文本 + 封面图 + 可见范围设置）

爱发电是 Vue.js SPA，发布流程:
1. 打开 afdian.net → 注入 Cookie 登录
2. 导航到创作者 Dashboard
3. 点击「发布」按钮 → 打开发文编辑器（Modal 或独立页）
4. 填写标题 / 正文（富文本）/ 可选封面图
5. 设置可见范围 → 点击发布

🚨 注意: 爱发电编辑器可能使用富文本（contenteditable）或 Markdown，
由 _fill_editor 自动适配。
"""

import json
import os
import re
import time
import random
from typing import Optional

from .base import BasePlatform, get_platform_cookies, update_platform_cookies, DARK_BG, GOLD, BRAND
from . import register


class AfdianPlatform(BasePlatform):
    name = "afdian"
    display_name = "爱发电"

    HOME_URL = "https://ifdian.net"
    DASHBOARD_URL = "https://ifdian.net/dashboard"

    MAX_TITLE_CHARS = 60
    MAX_BODY_CHARS = 20000

    # ===== Cookie 管理 =====

    def _get_cookies_for_playwright(self) -> list:
        """从 platform-cookies.json 提取爱发电 Cookie → Playwright 格式
        
        爱发电 Cookie 混合了两个域名:
        - auth_token → ifdian.net (hostOnly)
        - 其他 cookie → .ifdian.net (subdomain)
        """
        creds = get_platform_cookies("afdian")
        if not creds:
            return []
        cookies = []
        for name, value in creds.items():
            if not value or name in ("configured_at", "expires", "domain"):
                continue
            # auth_token 是 hostOnly，domain 不带点
            domain = "ifdian.net" if name == "auth_token" else ".ifdian.net"
            cookies.append({
                "name": name,
                "value": str(value),
                "domain": domain,
                "path": "/",
            })
        return cookies

    # ===== Markdown → 纯文本（爱发电正文用） =====

    def md_to_plaintext(self, body_md: str) -> str:
        """Markdown → 纯文本（保留基本结构）"""
        text = body_md
        text = re.sub(r"^#{2,6}\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"```[\s\S]*?```", "", text)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
        text = re.sub(r"!\[.*?\]\(.*?\)", "[图片]", text)
        text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    # ===== 主发布逻辑 =====

    def publish(self, meta: dict, body_md: str, cover_path: str = None) -> dict:
        """
        发布文章到爱发电

        Args:
            meta: {
                "title": "文章标题",
                "digest": "摘要（可选，作为副标题）",
                "category": "分类",
                "visibility": "public" | "patrons" (默认 public)
            }
            body_md: Markdown 正文
            cover_path: 封面图本地路径（可选）

        Returns:
            {"success": True, "url": "..."} 或 {"error": "..."}
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return self.error("需要 playwright: pip install playwright && python -m playwright install chromium")

        title = meta.get("title", "")[:self.MAX_TITLE_CHARS]
        body_text = self.md_to_plaintext(body_md)[:self.MAX_BODY_CHARS]
        visibility = meta.get("visibility", "public")

        # 追加品牌尾签
        brand_footer = (
            f"\n\n——\n"
            f"原文首发于公众号「{BRAND}」\n"
            f"世界一隅 · WORLD CORNER"
        )
        if len(body_text) + len(brand_footer) <= self.MAX_BODY_CHARS:
            body_text += brand_footer

        self.log(f"开始发布爱发电文章: {title}")
        self.log(f"  正文: {len(body_text)} 字 | 可见: {visibility}")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,  # 爱发电可能需要手动扫码/验证
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                ],
            )
            viewport = self._randomize_viewport(None)
            context = browser.new_context(
                locale="zh-CN",
                viewport=viewport,
            )

            # 注入 Cookie
            afdian_cookies = self._get_cookies_for_playwright()
            if afdian_cookies:
                context.add_cookies(afdian_cookies)
                self.log(f"已注入 {len(afdian_cookies)} 个 Cookie")
            else:
                self.log("⚠️ 无 Cookie，需要手动登录")

            page = context.new_page()
            self._apply_stealth(page)

            try:
                # ===== Step 1: 导航到首页，检查登录态 =====
                self.log("打开爱发电首页...")
                page.goto(self.HOME_URL, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(5000)

                # 检查登录状态
                if self._needs_login(page):
                    self.log("⚠️ 需要登录，请在浏览器中完成登录...")
                    if not self.wait_for_login(page, login_pattern="login", timeout=300):
                        return self.error("登录超时")
                    # 保存新 Cookie
                    self._save_cookies_from_page(page)
                    page.goto(self.HOME_URL, timeout=30000)
                    page.wait_for_timeout(5000)

                # ===== Step 2: 导航到 Dashboard =====
                self.log("导航到 Dashboard...")
                page.goto(self.DASHBOARD_URL, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(5000)

                # 截图调试
                page.screenshot(path=os.path.expanduser("~/Desktop/afdian-dashboard.png"))

                # ===== Step 3: 打开发布编辑器 =====
                self.log("查找发布入口...")
                if not self._open_editor(page):
                    # 备用：尝试直接导航到发布页
                    self.log("尝试直接导航到发布页...")
                    page.goto("https://afdian.net/dashboard/post/new", timeout=30000)
                    page.wait_for_timeout(5000)
                    # 再试一次找编辑器
                    if not self._is_editor_open(page):
                        self._dump_debug(page, "no-editor")
                        return self.error(
                            "未找到发布编辑器。\n"
                            "  请检查截图 ~/Desktop/afdian-dashboard.png\n"
                            "  可能需要手动在浏览器中点击「发布」按钮\n"
                            "  然后重新运行脚本"
                        )

                # ===== Step 4: 填写标题 =====
                self.log("填写标题...")
                self._fill_title(page, title)

                # ===== Step 5: 填写正文 =====
                self.log("填写正文...")
                self._fill_body(page, body_text)

                # ===== Step 6: 上传封面（可选） =====
                if cover_path and os.path.exists(cover_path):
                    self.log("上传封面图...")
                    self._upload_cover(page, cover_path)

                # ===== Step 7: 设置可见范围 =====
                if visibility == "patrons":
                    self.log("设置可见范围: 仅赞助者...")
                    self._set_visibility(page, "patrons")

                # ===== Step 8: 发布前检查 =====
                self.log("发布前检查...")
                page.wait_for_timeout(2000)
                page.screenshot(path=os.path.expanduser("~/Desktop/afdian-before-publish.png"))

                # ===== Step 9: 点击发布 =====
                self.log("点击发布...")
                result = self._click_publish(page)

                if result.get("success"):
                    self.log(f"✅ 爱发电发布成功 → {result.get('url', '')}")
                else:
                    self._dump_debug(page, "publish-result")
                    self.log("⚠️ 发布结果不确定，请检查截图")

                return result

            except Exception as e:
                try:
                    page.screenshot(path=os.path.expanduser("~/Desktop/afdian-error.png"))
                except:
                    pass
                return self.error(f"发布过程出错: {e}")
            finally:
                self.log("浏览器保持打开 30 秒，检查后手动关闭...")
                time.sleep(30)
                context.close()

    # ===== 内部方法 =====

    def _needs_login(self, page) -> bool:
        """检查是否需要登录"""
        url = page.url.lower()
        body = page.locator('body').inner_text()

        if "login" in url:
            return True
        if "登录" in body and ("扫码" in body or "手机号" in body):
            return True
        # 检查是否有登录按钮（未登录态）
        login_btns = page.locator('button:has-text("登录"), a:has-text("登录")')
        if login_btns.count() > 2:  # 页面上多个登录入口 = 未登录
            return True
        return False

    def _open_editor(self, page) -> bool:
        """打开发布编辑器

        策略（多兜底）:
        1. 找「发布」「写文章」「发动态」按钮
        2. 找固定发帖框（contenteditable）
        3. 检查是否已经在编辑器页面
        """
        # 先检查是否已经在编辑器页面
        if self._is_editor_open(page):
            self.log("  编辑器已打开")
            return True

        # 查找发布按钮
        publish_keywords = [
            "发布", "写文章", "发动态", "新建", "创作",
            "发布动态", "发布文章", "写点什么",
        ]

        for txt in publish_keywords:
            for tag in ["button", "a", "span", "div"]:
                try:
                    el = page.locator(f'{tag}:has-text("{txt}")').first
                    if el.count() > 0 and el.is_visible():
                        self._human_click(page, el)
                        self.log(f"  已点击: '{txt}'")
                        page.wait_for_timeout(4000)
                        if self._is_editor_open(page):
                            return True
                except:
                    continue

        # 查找带有 create/write/post 类名的按钮
        for cls in ["create", "write", "post", "publish", "new-post"]:
            try:
                el = page.locator(f'[class*="{cls}"]').first
                if el.count() > 0 and el.is_visible():
                    self._human_click(page, el)
                    self.log(f"  已点击: [class*={cls}]")
                    page.wait_for_timeout(4000)
                    if self._is_editor_open(page):
                        return True
            except:
                continue

        return False

    def _is_editor_open(self, page) -> bool:
        """检查编辑器是否已打开（标题输入框 + 正文编辑区）"""
        # 标题输入框
        title_selectors = [
            'input[placeholder*="标题"]',
            'input[name="title"]',
            '[class*="title"] input',
            'input[placeholder*="文章"]',
        ]
        # 正文编辑区
        body_selectors = [
            '[contenteditable="true"]',
            'textarea[placeholder*="内容"]',
            'textarea[placeholder*="正文"]',
            '[class*="editor"]',
        ]

        has_title = False
        has_body = False

        for sel in title_selectors:
            try:
                el = page.locator(sel).first
                if el.count() > 0 and el.is_visible():
                    has_title = True
                    break
            except:
                continue

        for sel in body_selectors:
            try:
                el = page.locator(sel).first
                if el.count() > 0 and el.is_visible():
                    has_body = True
                    break
            except:
                continue

        return has_title or has_body

    def _fill_title(self, page, title: str):
        """填写文章标题"""
        for sel in [
            'input[placeholder*="标题"]',
            'input[name="title"]',
            '[class*="title"] input',
            'input[placeholder*="文章"]',
        ]:
            try:
                el = page.locator(sel).first
                if el.count() > 0 and el.is_visible():
                    self._human_click(page, el)
                    page.wait_for_timeout(300)
                    el.fill("")
                    page.wait_for_timeout(100)
                    el.fill(title)
                    self.log(f"  标题已填写: {title} [{sel}]")
                    page.wait_for_timeout(500)
                    return
            except:
                continue

        self.log("  ⚠️ 未找到标题输入框，尝试键盘输入...")

    def _fill_body(self, page, body: str):
        """填写文章正文（支持 contenteditable 和 textarea）"""
        import pyperclip
        pyperclip.copy(body)

        # 策略1: contenteditable（富文本编辑器）
        for sel in [
            '[contenteditable="true"]',
            '[class*="editor"] [contenteditable]',
            '[class*="ql-editor"]',
            '.ProseMirror',
        ]:
            try:
                el = page.locator(sel).first
                if el.count() > 0 and el.is_visible():
                    self._human_click(page, el)
                    page.wait_for_timeout(500)
                    page.keyboard.press("Control+a")
                    page.wait_for_timeout(200)
                    page.keyboard.press("Control+v")
                    self.log(f"  正文已粘贴 ({len(body)}字) [{sel}]")
                    page.wait_for_timeout(1000)
                    return
            except:
                continue

        # 策略2: textarea
        for sel in [
            'textarea[placeholder*="内容"]',
            'textarea[placeholder*="正文"]',
            'textarea',
        ]:
            try:
                el = page.locator(sel).first
                if el.count() > 0 and el.is_visible():
                    self._human_click(page, el)
                    page.wait_for_timeout(300)
                    el.fill("")
                    page.wait_for_timeout(100)
                    el.fill(body)
                    self.log(f"  正文已填写 ({len(body)}字) [{sel}]")
                    page.wait_for_timeout(500)
                    return
            except:
                continue

        self.log("  ⚠️ 未找到正文编辑器，尝试 Ctrl+V...")
        page.keyboard.press("Control+v")

    def _upload_cover(self, page, cover_path: str):
        """上传封面图"""
        for sel in [
            'input[type="file"][accept*="image"]',
            'input[type="file"]',
        ]:
            try:
                el = page.locator(sel).first
                if el.count() > 0:
                    el.set_input_files(cover_path)
                    self.log(f"  封面已上传: {os.path.basename(cover_path)}")
                    page.wait_for_timeout(3000)
                    return
            except:
                continue

        self.log("  ⚠️ 未找到封面上传入口")

    def _set_visibility(self, page, level: str):
        """设置文章可见范围

        Args:
            level: "public" (公开) | "patrons" (仅赞助者)
        """
        if level == "public":
            return  # 默认就是公开

        # 点击可见范围选择器
        visibility_keywords = ["可见", "权限", "谁可以看", "公开", "赞助"]
        for txt in visibility_keywords:
            try:
                el = page.locator(f'text="{txt}"').first
                if el.count() > 0 and el.is_visible():
                    self._human_click(page, el)
                    page.wait_for_timeout(1000)
                    break
            except:
                continue

        # 选择「仅赞助者」
        for txt in ["赞助者", "仅赞助", "付费", "patron"]:
            try:
                el = page.locator(f'text="{txt}"').first
                if el.count() > 0 and el.is_visible():
                    self._human_click(page, el)
                    self.log(f"  已选择: {txt}")
                    page.wait_for_timeout(500)
                    return
            except:
                continue

    def _click_publish(self, page) -> dict:
        """点击发布按钮 → 等待结果 → 返回状态

        爱发电弹窗结构：div.vm-modal-feed > div.vm-feed-pre-setting > div.vm-btn.size32
        发布按钮是 <div> 不是 <button>，class 为 vm-btn
        """
        publish_clicked = False

        # 策略1: 爱发电特有——弹窗内的 .vm-btn（div 按钮）
        for cls in ["vm-btn", ".vm-btn.size32", "[class*='vm-btn']"]:
            try:
                # 限定在弹窗内找，避免点到打开编辑器的按钮
                modal = page.locator('.vm-modal-feed, [class*="vm-modal"]').first
                if modal.count() > 0:
                    btn = modal.locator(cls).last
                else:
                    btn = page.locator(cls).last

                if btn.count() > 0 and btn.is_visible():
                    self._human_click(page, btn)
                    self.log(f"  已点击弹窗内发布按钮 [{cls}]")
                    publish_clicked = True
                    break
            except:
                continue

        # 策略2: 文字匹配（button 或 div）
        if not publish_clicked:
            for txt in ["发布", "确认发布", "保存并发布", "提交"]:
                for tag in ["button", "div"]:
                    try:
                        # 限定在弹窗内
                        modal = page.locator('.vm-modal-feed, [class*="vm-modal"]').first
                        if modal.count() > 0:
                            btn = modal.locator(f'{tag}:has-text("{txt}")').last
                        else:
                            btn = page.locator(f'{tag}:has-text("{txt}")').last
                        if btn.count() > 0 and btn.is_visible():
                            self._human_click(page, btn)
                            self.log(f"  已点击弹窗内 '{txt}'")
                            publish_clicked = True
                            break
                    except:
                        continue
                if publish_clicked:
                    break

        # 策略3: Ctrl+Enter
        if not publish_clicked:
            self.log("  尝试 Ctrl+Enter...")
            page.keyboard.press("Control+Enter")
            publish_clicked = True

        if not publish_clicked:
            return self.error("未找到发布按钮")

        # 等待发布完成
        page.wait_for_timeout(8000)

        # 检查发布结果
        current_url = page.url
        body_text = page.locator('body').inner_text()

        # 成功标志
        success_indicators = [
            "发布成功", "已发布", "success", "文章已发布",
        ]
        for indicator in success_indicators:
            if indicator in body_text:
                return self.success(url=current_url, note="发布成功")

        # 如果 URL 变了（跳转到文章页/列表页），也算成功
        if "/post/" in current_url or "/dashboard" not in current_url:
            return self.success(url=current_url, note="已跳转，请确认")

        # 检查是否有错误提示
        error_indicators = ["失败", "错误", "error", "不能为空", "超长"]
        for indicator in error_indicators:
            if indicator in body_text:
                return self.error(f"发布失败: 页面显示 '{indicator}'")

        # 不确定
        return self.success(
            url=current_url,
            note="发布状态不确定，请手动检查"
        )

    def _dump_debug(self, page, tag: str):
        """保存调试信息"""
        try:
            path = os.path.expanduser(f"~/Desktop/afdian-debug-{tag}.png")
            page.screenshot(path=path, full_page=True)
            self.log(f"调试截图: {path}")

            # 打印页面关键文字
            body = page.locator('body').inner_text()
            lines = [l.strip() for l in body.split('\n') if l.strip()]
            btn_lines = [l for l in lines if any(
                k in l for k in ['发布', '标题', '内容', '登录', '错误', '成功']
            )]
            self.log(f"关键文字: {btn_lines[:20]}")
        except:
            pass


# 自动注册
register(AfdianPlatform())
