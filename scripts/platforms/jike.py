"""即刻发布 — Playwright + Lexical编辑器"""
import os, time, re
from .base import BasePlatform, get_platform_cookies

class JikePlatform(BasePlatform):
    name = "jike"
    display_name = "即刻"

    HOME_URL = "https://web.okjike.com/"
    COOKIE_KEYS = []

    def publish(self, meta: dict, body_md: str, cover_path: str = None) -> dict:
        title = (meta.get("title") or "").strip()[:80]
        digest = (meta.get("digest") or title)[:200]

        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser, context, page = self._launch_browser(p)

            try:
                page.goto(self.HOME_URL, timeout=30000)
                page.wait_for_load_state("domcontentloaded")
                time.sleep(15)

                if "扫码" in (page.inner_text("body") or ""):
                    print("[即刻] 需要扫码登录...")
                    start = time.time()
                    while "扫码" in (page.inner_text("body") or ""):
                        if time.time() - start > 120:
                            return self.error("即刻登录超时")
                        time.sleep(3)

                editor = page.wait_for_selector(
                    'div[data-lexical-editor="true"][contenteditable="true"]',
                    timeout=15000
                )
                editor.click()
                self._human_delay(500)

                text = self.md_to_plaintext(body_md)
                page.evaluate("""(text) => {
                    const el = document.querySelector(
                        'div[data-lexical-editor="true"][contenteditable="true"]'
                    );
                    if (!el) return;
                    el.focus();
                    const ev = new ClipboardEvent('paste', {
                        clipboardData: new DataTransfer(),
                        bubbles: true, cancelable: true,
                    });
                    ev.clipboardData.setData('text/plain', text);
                    el.dispatchEvent(ev);
                }""", text)
                self._human_delay(1000)

                send_btn = page.locator('button:has-text("发送")')
                if send_btn.is_visible(timeout=5000):
                    send_btn.click()
                    print("[即刻] 已发送")
                    time.sleep(3)
                    return self.ok({"note": "已发布到即刻"})

                return self.error("找不到发送按钮")

            except Exception as e:
                self.debug_snapshot(page, "jike_error")
                return self.error(f"即刻发布失败: {str(e)}")
            finally:
                browser.close()

    def md_to_plaintext(self, body_md: str) -> str:
        text = body_md
        text = re.sub(r"^(#{2,6})\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"```[\s\S]*?```", "", text)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
        text = re.sub(r"!\[.*?\]\(.*?\)", "[图片]", text)
        text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*[-*]\s+", "• ", text, flags=re.MULTILINE)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"(?i)(公众号|关注.*微信|扫码|引流|商务合作).*", "", text)
        return text.strip()[:280]

from platforms import register
register(JikePlatform())
