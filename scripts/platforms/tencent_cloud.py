"""腾讯云开发者社区发布 — Playwright + Draft.js
策略分离：publish() 依次尝试 3 种发布策略，一种成功就返回，全部失败才报错。
"""
import os, time, re
from .base import BasePlatform, get_platform_cookies, update_platform_cookies

class TencentCloudPlatform(BasePlatform):
    name = "tencent_cloud"
    display_name = "腾讯云"

    WRITE_URL = "https://cloud.tencent.com/developer/article/write"
    COOKIE_KEYS = ["skey", "uin", "qcmainCSRFToken", "qcommunity_session", "qcloud_uid"]

    MAX_TITLE = 80
    MIN_BODY = 140
    LOGIN_TIMEOUT = 120

    def _inject_cookies(self, context):
        cookies = get_platform_cookies("tencent_cloud")
        if not cookies.get("skey"):
            return False
        for key in self.COOKIE_KEYS:
            value = cookies.get(key)
            if value:
                context.add_cookies([{
                    "name": key,
                    "value": str(value),
                    "domain": ".cloud.tencent.com",
                    "path": "/",
                }])
        return True

    def _fill_title(self, page, title):
        el = page.wait_for_selector("textarea.article-title", timeout=10000)
        el.click()
        el.fill("")
        self._human_type(page, el, title)
        self._random_fidget(page)

    def _strip_ads(self, text: str) -> str:
        lines = text.split("\n")
        clean = []
        for line in lines:
            stripped = line.strip()
            if any(k in stripped for k in ("公众号", "关注微信", "扫码", "引流", "商务合作")):
                continue
            if re.search(r"关注.*公众号|公众号.*关注|微信.*\d{5,}", stripped):
                continue
            clean.append(line)
        return "\n".join(clean)

    def _fill_body(self, page, body_md):
        body_text = self._strip_ads(self.md_to_plaintext(body_md))
        el = page.wait_for_selector(
            'div.public-DraftEditor-content[contenteditable="true"]',
            timeout=10000
        )
        el.click()
        self._human_delay(300)
        page.evaluate("""(text) => {
            const el = document.querySelector(
                'div.public-DraftEditor-content[contenteditable="true"]'
            );
            if (!el) return;
            el.focus();
            const ev = new ClipboardEvent('paste', {
                clipboardData: new DataTransfer(),
                bubbles: true, cancelable: true,
            });
            ev.clipboardData.setData('text/plain', text);
            el.dispatchEvent(ev);
        }""", body_text)
        self._human_delay(1000)

    def _pick_radios(self, page):
        yc = page.locator('label:has(input[type="radio"])').filter(has_text="原创")
        if yc.is_visible(timeout=2000):
            yc.click()
        else:
            radio = page.locator('input[type="radio"]').first
            if radio.is_visible(timeout=2000):
                radio.check()
        self._human_delay(500)

    def _fill_tags(self, page, title):
        search = page.locator('.com-2-tagsinput-bar:has(.com-2-tagsinput-dropdown) .com-2-tag-input').first
        if search.is_visible(timeout=2000):
            search.click()
            self._human_delay(200)
            search.fill("AI")
            self._human_delay(2000)
            item = page.locator('.com-2-tagsinput-dropdown.show li').first
            if item.is_visible(timeout=3000):
                item.click()
                self._human_delay(500)

    def _wait_login(self, page, context):
        if any(k in page.url.lower() for k in ("login", "passport", "auth", "signin")):
            print("[腾讯云] 需要登录，等待扫码...")
            start = time.time()
            while any(k in page.url.lower() for k in ("login", "passport", "auth", "signin")):
                if time.time() - start > self.LOGIN_TIMEOUT:
                    return self.error("腾讯云登录超时")
                time.sleep(2)
            cookies = context.cookies()
            update_platform_cookies("tencent_cloud", {c["name"]: c["value"] for c in cookies})
            print("[腾讯云] Cookie 已更新")

    def _dismiss_popups(self, page):
        self.dismiss_overlays(page)
        for txt in ("不体验", "取消体验", "我知道了", "关闭", "跳过"):
            btn = page.locator(f'button:has-text("{txt}")')
            if btn.is_visible(timeout=1500):
                btn.click()
                self._human_delay(800)

    def _check_error(self, page):
        err = page.evaluate("""() => {
            const t = document.body.innerText;
            const lines = t.split('\\n').filter(l => /不能少于|至少.*字/.test(l));
            if (lines.length > 0) return lines[0].trim();
            if (t.includes('发布失败') || t.includes('校验失败')) return '发布失败';
            return '';
        }""")
        return err

    def _extract_url(self, page):
        time.sleep(3)
        m = re.search(r"/article/(\d+)", page.url)
        if m:
            return f"https://cloud.tencent.com/developer/article/{m.group(1)}"
        text = page.evaluate("document.body.innerText")
        m = re.search(r"article/(\d+)", text)
        if m:
            return f"https://cloud.tencent.com/developer/article/{m.group(1)}"
        return page.url

    # ── 策略 A: 侧栏布局 ──
    def _publish_sidebar(self, page, title):
        if not page.locator('button:has-text("确认发布")').is_visible(timeout=3000):
            return "侧栏无确认发布按钮"
        self._pick_radios(page)
        self._fill_tags(page, title)
        page.evaluate("document.querySelector('.sidebar-bd')?.scrollTo(0, 9999)")
        self._human_delay(500)
        page.locator('button:has-text("确认发布")').click()
        self._human_delay(2000)
        self._dismiss_popups(page)
        return self._check_error(page)

    # ── 策略 B: 头部发布→弹窗布局 ──
    def _publish_header(self, page, title):
        if not page.locator('button.c-btn:has-text("发布")').is_visible(timeout=3000):
            return "头部无发布按钮"
        page.locator('button.c-btn:has-text("发布")').click()
        self._human_delay(2000)
        no_exp = page.locator('button:has-text("不体验")')
        if no_exp.is_visible(timeout=2000):
            no_exp.click()
            self._human_delay(800)
        self._pick_radios(page)
        self._fill_tags(page, title)
        confirm = page.locator('button:has-text("确认发布")').first
        confirm.wait_for(state="attached", timeout=5000)
        confirm.click(force=True)
        self._human_delay(3000)
        err = self._check_error(page)
        if err:
            return err
        text = page.evaluate("document.body.innerText")
        if "发布成功" in text or "文章已发布" in text or "article" in page.url:
            return ""
        return "发布后未检测到成功状态"

    def publish(self, meta: dict, body_md: str, cover_path: str = None) -> dict:
        title = (meta.get("title") or "").strip()[:self.MAX_TITLE]
        if not title:
            return self.error("标题不能为空")

        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser, context, page = self._launch_browser(p)
            if not self._inject_cookies(context):
                return self.error("腾讯云 Cookie 未配置")

            try:
                page.goto(self.WRITE_URL, timeout=30000)
                page.wait_for_load_state("domcontentloaded")
                time.sleep(3)

                r = self._wait_login(page, context)
                if isinstance(r, dict):
                    return r

                self._dismiss_popups(page)
                self._fill_title(page, title)
                self._fill_body(page, body_md)
                self._random_fidget(page)

                for name, strategy in [("侧栏", self._publish_sidebar), ("头部弹窗", self._publish_header)]:
                    print(f"[腾讯云] 尝试{name}策略...")
                    err = strategy(page, title)
                    if not err:
                        url = self._extract_url(page)
                        return self.ok({"url": url, "note": "已发布到腾讯云开发者社区"})
                    print(f"[腾讯云] {name}策略失败: {err}")

                return self.error(f"所有发布策略均失败: {err}")

            except Exception as e:
                self.debug_snapshot(page, "tencent_error")
                return self.error(f"腾讯云发布失败: {str(e)}")
            finally:
                browser.close()

    def md_to_plaintext(self, body_md: str) -> str:
        text = body_md
        text = re.sub(r"^(#{2,6})\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"```[\s\S]*?```", "", text)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*", r"\1", text)
        text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
        text = re.sub(r"!\[.*?\]\(.*?\)", "[图片]", text)
        text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*[-*]\s+", "• ", text, flags=re.MULTILINE)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

from platforms import register
register(TencentCloudPlatform())
