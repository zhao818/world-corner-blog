# -*- coding: utf-8 -*-
"""平台基础模块 — BasePlatform + Cookie管理 + 反检测三层系统

Layer 1: playwright-stealth 统一隐身（浏览器指纹覆盖）
Layer 2: 行为多样化（human_delay/type/scroll/click）
Layer 3: 会话人格（急躁型/思考型/细致型，每次随机）
"""
import json, os, time, random, math
from typing import Optional

# ── 品牌常量 ──
DARK_BG = "#1a1a2e"
GOLD = "#c8a03c"
BRAND = "美好需要创造"

# ── Cookie 管理 ──
COOKIE_PATH = os.path.expanduser("~/.claude/platform-cookies.json")

def _load_cookie_file() -> dict:
    if os.path.exists(COOKIE_PATH):
        try:
            with open(COOKIE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {}

def _save_cookie_file(data: dict):
    os.makedirs(os.path.dirname(COOKIE_PATH), exist_ok=True)
    with open(COOKIE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_platform_cookies(platform: str) -> dict:
    data = _load_cookie_file()
    return data.get(platform, {})

def update_platform_cookies(platform: str, updates: dict):
    data = _load_cookie_file()
    if platform not in data:
        data[platform] = {}
    data[platform].update(updates)
    _save_cookie_file(data)

def load_cookies():
    return _load_cookie_file()

def save_cookies(data: dict):
    _save_cookie_file(data)


# ══════════════════════════════════════════════════════════
# Layer 3: 会话人格
# ══════════════════════════════════════════════════════════

class SessionPersona:
    """会话人格 — 每次随机选一种，所有行为参数完全不同"""

    PERSONAS = {
        "急躁型": {
            "typing_speed": (5, 20),      # ms，打字快
            "error_rate": 0.01,           # 1% 打错率
            "delay_profile": "gamma",     # 延时分布
            "fidget_prob": 0.15,          # 15% 概率犹豫动作
            "scroll_pause": (0.3, 0.8),   # 阅读停留短
            "click_offset": (0.3, 0.7),   # 点击偏移范围
        },
        "思考型": {
            "typing_speed": (30, 80),     # ms，打字慢
            "error_rate": 0.04,           # 4% 打错率
            "delay_profile": "exponential",
            "fidget_prob": 0.40,          # 40% 概率犹豫
            "scroll_pause": (1.0, 3.0),   # 阅读停留长
            "click_offset": (0.25, 0.75),
        },
        "细致型": {
            "typing_speed": (15, 45),     # ms，中速
            "error_rate": 0.02,           # 2% 打错率
            "delay_profile": "normal",
            "fidget_prob": 0.25,          # 25% 概率犹豫
            "scroll_pause": (0.5, 1.5),
            "click_offset": (0.2, 0.8),
        },
    }

    VIEWPORTS = [
        (1440, 900),
        (1366, 768),
        (1536, 864),
        (1920, 1080),
        (1280, 720),
    ]

    def __init__(self):
        self.name = random.choice(list(self.PERSONAS.keys()))
        self.config = self.PERSONAS[self.name]
        self.viewport = random.choice(self.VIEWPORTS)
        # 微调 viewport ±5%
        self.viewport = (
            int(self.viewport[0] * random.uniform(0.95, 1.05)),
            int(self.viewport[1] * random.uniform(0.95, 1.05)),
        )


# ══════════════════════════════════════════════════════════
# Layer 2: 行为多样化（human_* 方法）
# ══════════════════════════════════════════════════════════

def _gamma_delay(base_ms: float) -> float:
    """Gamma 分布延时（自然聚集）"""
    return random.gammavariate(2.0, base_ms / 2.0) / 1000.0

def _exp_delay(base_ms: float) -> float:
    """指数分布延时（长尾）"""
    return random.expovariate(1.0 / (base_ms / 1000.0))

def _normal_delay(base_ms: float) -> float:
    """正态分布延时"""
    return max(0.01, random.gauss(base_ms / 1000.0, base_ms / 3000.0))


# ══════════════════════════════════════════════════════════
# BasePlatform — 所有平台自动继承反检测
# ══════════════════════════════════════════════════════════

class BasePlatform:
    name = ""
    display_name = ""

    def __init__(self):
        # Layer 3: 每次实例化随机选人格
        self.persona = SessionPersona()

    # ── 工具方法 ──
    def error(self, msg: str) -> dict:
        return {"success": False, "ok": False, "error": msg}

    def ok(self, data: dict = None) -> dict:
        result = {"success": True, "ok": True}
        if data:
            result.update(data)
        return result

    # ── Layer 1: 统一隐身 ──
    def _apply_stealth(self, page):
        """应用 playwright-stealth 覆盖浏览器指纹"""
        try:
            from playwright_stealth import Stealth
            stealth = Stealth()
            stealth.apply_stealth_sync(page)
        except ImportError:
            # fallback: 手动关键覆盖
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
                window.chrome = {runtime: {}};
            """)

    def _randomize_viewport(self, context):
        """随机化视口大小（±5% 微调已在 persona 中完成）"""
        w, h = self.persona.viewport
        context.set_viewport_size({"width": w, "height": h})

    def _launch_browser(self, playwright):
        """统一启动浏览器（反检测 + 随机视口 + Cookie注入）"""
        browser = playwright.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-first-run",
                "--no-default-browser-check",
            ]
        )
        context = browser.new_context(
            viewport={"width": self.persona.viewport[0], "height": self.persona.viewport[1]},
            user_agent=f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(120,130)}.0.0.0 Safari/537.36",
            locale="zh-CN",
        )
        page = context.new_page()
        self._apply_stealth(page)
        return browser, context, page

    # ── Layer 2: 行为多样化 ──
    def _human_delay(self, base_ms: float = 500):
        """人性化延时（根据人格选择分布）"""
        profile = self.persona.config["delay_profile"]
        if profile == "gamma":
            time.sleep(_gamma_delay(base_ms))
        elif profile == "exponential":
            time.sleep(_exp_delay(base_ms))
        else:
            time.sleep(_normal_delay(base_ms))

    def _human_type(self, page, element, text: str, delay_range: tuple = None):
        """人性化打字（含随机打错+回删）"""
        if delay_range is None:
            delay_range = self.persona.config["typing_speed"]
        error_rate = self.persona.config["error_rate"]

        for char in text:
            # 随机打错
            if random.random() < error_rate:
                wrong_char = chr(ord(char) + random.randint(-2, 2))
                page.keyboard.type(wrong_char, delay=random.randint(*delay_range))
                time.sleep(random.uniform(0.1, 0.3))
                page.keyboard.press("Backspace")
                time.sleep(random.uniform(0.05, 0.15))

            page.keyboard.type(char, delay=random.randint(*delay_range))

            # 长词前停顿
            if char in "，。！？；：、":
                time.sleep(random.uniform(0.2, 0.5))

    def _human_scroll(self, page, distance: int = 300):
        """人性化滚动（随机步数+20%回滚）"""
        steps = random.randint(3, 8)
        step_size = distance // steps
        for _ in range(steps):
            page.mouse.wheel(0, step_size + random.randint(-20, 20))
            time.sleep(random.uniform(0.05, 0.15))

        # 20% 概率回滚
        if random.random() < 0.2:
            time.sleep(random.uniform(*self.persona.config["scroll_pause"]))
            page.mouse.wheel(0, -random.randint(50, 100))

    def _human_click(self, page, element):
        """人性化点击（非中心偏移+变速等待）"""
        lo, hi = self.persona.config["click_offset"]
        box = element.bounding_box()
        if box:
            x = box["x"] + box["width"] * random.uniform(lo, hi)
            y = box["y"] + box["height"] * random.uniform(lo, hi)
            page.mouse.click(x, y)
        else:
            element.click()
        self._human_delay(200)

    def _random_fidget(self, page):
        """犹豫动作（根据人格概率触发）"""
        if random.random() > self.persona.config["fidget_prob"]:
            return
        action = random.choice(["micro_scroll", "pause", "tiny_scroll_back"])
        if action == "micro_scroll":
            page.mouse.wheel(0, random.randint(-15, 15))
        elif action == "pause":
            time.sleep(random.uniform(0.3, 1.0))
        elif action == "tiny_scroll_back":
            page.mouse.wheel(0, -random.randint(5, 20))

    # ── 诊断模式 ──
    def debug_snapshot(self, page, step_name: str, debug_dir: str = None):
        """失败诊断：截图 + 保存HTML + 打印关键元素"""
        if debug_dir is None:
            debug_dir = os.path.expanduser("~/Desktop/debug-publish")
        os.makedirs(debug_dir, exist_ok=True)

        ts = time.strftime("%H%M%S")
        prefix = f"{debug_dir}/{self.name}_{step_name}_{ts}"

        # 1. 截图
        screenshot_path = f"{prefix}.png"
        try:
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"  📸 截图: {screenshot_path}")
        except Exception as e:
            print(f"  📸 截图失败: {e}")

        # 2. 保存HTML
        html_path = f"{prefix}.html"
        try:
            html = page.content()
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"  📄 HTML: {html_path}")
        except Exception as e:
            print(f"  📄 HTML保存失败: {e}")

        # 3. 打印页面关键信息
        try:
            info = page.evaluate("""() => {
                const result = {
                    url: location.href,
                    title: document.title,
                    inputs: [],
                    buttons: [],
                    files: [],
                    errors: [],
                };
                // 所有 input
                document.querySelectorAll('input').forEach(el => {
                    result.inputs.push({
                        type: el.type,
                        placeholder: el.placeholder,
                        name: el.name,
                        id: el.id,
                        visible: el.offsetParent !== null,
                    });
                });
                // 所有 button
                document.querySelectorAll('button, [role="button"]').forEach(el => {
                    result.buttons.push({
                        text: el.innerText.trim().substring(0, 50),
                        class: el.className.substring(0, 80),
                        disabled: el.disabled,
                        visible: el.offsetParent !== null,
                    });
                });
                // file input
                document.querySelectorAll('input[type="file"]').forEach(el => {
                    result.files.push({
                        accept: el.accept,
                        name: el.name,
                        id: el.id,
                    });
                });
                // 错误提示
                document.querySelectorAll('[class*="error"], [class*="warn"], [class*="toast"]').forEach(el => {
                    if (el.innerText.trim()) {
                        result.errors.push(el.innerText.trim().substring(0, 100));
                    }
                });
                return result;
            }""")

            print(f"\n  🔍 页面诊断 [{self.name}]")
            print(f"     URL: {info['url']}")
            print(f"     标题: {info['title']}")
            print(f"     inputs: {len(info['inputs'])}个")
            for inp in info['inputs'][:10]:
                v = "✓" if inp['visible'] else "✗"
                print(f"       [{v}] type={inp['type']} placeholder={inp['placeholder']}")
            print(f"     buttons: {len(info['buttons'])}个")
            for btn in info['buttons'][:10]:
                v = "✓" if btn['visible'] else "✗"
                print(f"       [{v}] {btn['text']} | {btn['class'][:40]}")
            print(f"     file inputs: {len(info['files'])}个")
            if info['errors']:
                print(f"     ⚠️ 页面错误:")
                for err in info['errors'][:5]:
                    print(f"       {err}")
        except Exception as e:
            print(f"  🔍 诊断执行失败: {e}")

    def inspect_step(self, page, step_name: str, inspect_dir: str = None) -> str:
        """逐步截图 + AI分析，返回分析结果"""
        if inspect_dir is None:
            inspect_dir = os.path.expanduser("~/Desktop/debug-publish")
        os.makedirs(inspect_dir, exist_ok=True)

        ts = time.strftime("%H%M%S")
        screenshot_path = f"{inspect_dir}/{self.name}_{step_name}_{ts}.png"

        # 截图
        try:
            page.screenshot(path=screenshot_path, full_page=True)
        except Exception as e:
            return f"截图失败: {e}"

        # 获取页面基础信息
        try:
            page_info = page.evaluate("""() => ({
                url: location.href,
                title: document.title,
                inputCount: document.querySelectorAll('input').length,
                fileInputCount: document.querySelectorAll('input[type="file"]').length,
                buttonCount: document.querySelectorAll('button, [role="button"]').length,
                visibleText: document.body.innerText.substring(0, 500),
            })""")
        except:
            page_info = {}

        # 调用视觉模型分析
        analysis = self._analyze_screenshot(screenshot_path, step_name, page_info)

        print(f"\n  🔍 [{self.name}] {step_name}")
        print(f"     截图: {screenshot_path}")
        print(f"     分析: {analysis}")

        return analysis

    def _analyze_screenshot(self, image_path: str, step_name: str, page_info: dict) -> str:
        """调用视觉模型分析截图"""
        import base64, os

        # 读取图片
        try:
            with open(image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            return f"图片读取失败: {e}"

        prompt = f"""你是一个网页自动化诊断专家。分析这个截图，判断页面状态。

上下文信息：
- 平台: {self.name}
- 当前步骤: {step_name}
- URL: {page_info.get('url', '未知')}
- 页面标题: {page_info.get('title', '未知')}
- input元素数: {page_info.get('inputCount', 0)}
- file input数: {page_info.get('fileInputCount', 0)}
- button数: {page_info.get('buttonCount', 0)}

请分析：
1. 页面是否已登录？（是否有登录框/二维码/未登录提示）
2. 是否有弹窗/遮罩/引导层？（如joyride、modal、overlay）
3. 文件上传区域在哪里？（input[type="file"]是否可见，或拖拽区在哪）
4. 页面主要功能元素是什么？（按钮、输入框、表单等）
5. 如果要上传视频，应该操作哪个元素？给出CSS选择器建议
6. 有没有错误提示或警告信息？

请简洁回答，重点给出可操作的选择器建议。"""

        try:
            from openai import OpenAI

            # 优先使用 DashScope（支持视觉）
            dashscope_key = os.environ.get("DASHSCOPE_API_KEY")
            openai_key = os.environ.get("OPENAI_API_KEY")

            if dashscope_key:
                api_key = dashscope_key
                base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
                model = "qwen-vl-max"
            elif openai_key:
                api_key = openai_key
                base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
                model = "gpt-4o"
            else:
                return "无API Key，跳过AI分析"

            client = OpenAI(api_key=api_key, base_url=base_url, timeout=30)

            resp = client.chat.completions.create(
                model=model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    ]
                }],
                temperature=0,
                max_tokens=1000,
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"AI分析失败: {e}"

    # ── 弹窗/overlay 清理 ──
    def dismiss_overlays(self, page, selectors: list = None):
        """通用弹窗/overlay 清理"""
        if selectors is None:
            selectors = [
                'text=我知道了', 'text=跳过', 'text=关闭', 'text=以后再说',
                'text=立刻体验', 'text=下次再说', 'text=暂不',
                '.close-icon', '[class*="close-btn"]',
                'button:has(svg[class*="close"])',
            ]
        for sel in selectors:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=500):
                    btn.click()
                    time.sleep(0.3)
            except: pass

        # JS 强制移除 overlay/joyride/modal
        page.evaluate("""() => {
            const sels = ['[class*="joyride"]', '[class*="overlay"]', '[class*="modal"]',
                          '[class*="tooltip"]', '[class*="dialog"]', '[class*="mask"]'];
            sels.forEach(sel => {
                document.querySelectorAll(sel).forEach(el => {
                    if (el.tagName !== 'INPUT' && el.tagName !== 'TEXTAREA') {
                        el.style.pointerEvents = 'none';
                        el.style.opacity = '0';
                        el.style.visibility = 'hidden';
                    }
                });
            });
        }""")

    # ── 原有方法 ──
    def md_to_html(self, body_md: str, meta: dict = None) -> str:
        """通用 Markdown → 公众号风格 HTML（生态位法则版）"""
        lines = body_md.split("\n")
        html = []
        for line in lines:
            line = line.rstrip()
            if line.startswith("## ") and not line.startswith("### "):
                html.append(f'<h2 style="font-size:20px;background:#1a1a2e;color:#fff;padding:12px 20px;border-radius:6px;margin-bottom:24px;font-weight:600;border-left:4px solid #c8a03c;">{line[3:]}</h2>')
            elif line.startswith("### "):
                html.append(f'<h3 style="font-size:17px;color:#1a1a2e;font-weight:600;margin-bottom:8px;">{line[4:]}</h3>')
            elif line.startswith("✦"):
                html.append(f'<p style="font-size:15px;color:#c8a03c;line-height:1.8;padding:12px 16px;background:#f8f6f2;border-radius:4px;margin:16px 0;">{line}</p>')
            elif line.strip().startswith(">"):
                text = line.strip()[1:].strip()
                html.append(f'<p style="font-size:15px;color:#666;line-height:1.8;padding:16px 20px;background:#f8f6f2;border-left:3px solid #c8a03c;border-radius:4px;margin-bottom:40px;">{text}</p>')
            elif line.strip() == "":
                pass
            elif line.strip().startswith("- ") or line.strip().startswith("* "):
                html.append(f"<p style=\"margin:5px 0;padding-left:2em;color:#444;\">• {line.strip()[2:]}</p>")
            elif line.strip().startswith("|"):
                pass
            else:
                html.append(f"<p style=\"color:#444;margin-bottom:20px;line-height:1.8;\">{line}</p>")
        return "".join(html)

    def publish(self, meta: dict, body: str, cover_path: str = None) -> dict:
        raise NotImplementedError

    def check_and_refresh(self) -> bool:
        """检查登录态是否需要刷新，默认不需要"""
        return True

    def wait_for_login(self, url: str, timeout: int = 300, poll_interval: int = 5) -> bool:
        """打开登录页，等待用户扫码，检测到真正登录成功后保存Cookie

        Args:
            url: 登录页URL
            timeout: 超时秒数（默认300=5分钟）
            poll_interval: 轮询间隔秒数

        Returns:
            True=登录成功, False=超时
        """
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser, context, page = self._launch_browser(p)
            page.goto(url, timeout=30000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(3)

            print(f"  🔑 请在浏览器中登录 {self.display_name}")
            print(f"  📱 登录成功后浏览器会自动关闭")
            print(f"  ⏳ 等待中（超时{timeout}秒）")
            print(f"  ---")

            start_time = time.time()
            logged_in = False

            while time.time() - start_time < timeout and not logged_in:
                time.sleep(poll_interval)
                elapsed = int(time.time() - start_time)

                try:
                    current_url = page.url
                    page_title = page.title()

                    # 检测条件1：URL跳转到非登录页
                    if "login" not in current_url and "passport" not in current_url:
                        # 再检查是否有file input（真正的上传页面标志）
                        file_inputs = page.query_selector_all('input[type="file"]')
                        if file_inputs:
                            logged_in = True
                            print(f"  ✅ [{elapsed}秒] 检测到上传页面，登录成功！")

                    # 检测条件2：页面标题变化（登录后标题会变）
                    if not logged_in and self.name in ("douyin", "channels"):
                        # 抖音/视频号：登录后标题会从"登录"变成具体页面名
                        if "登录" not in page_title and "login" not in page_title.lower():
                            # 检查是否有功能按钮
                            buttons = page.query_selector_all('button')
                            if len(buttons) > 2:
                                logged_in = True
                                print(f"  ✅ [{elapsed}秒] 页面标题变化，登录成功！")

                    if not logged_in:
                        # 打印状态
                        if elapsed % 15 == 0:
                            print(f"  ⏳ [{elapsed}秒] 等待扫码... 当前页面: {page_title[:30]}")

                except Exception as e:
                    # 页面可能在跳转
                    pass

            if logged_in:
                # 等页面稳定
                time.sleep(3)
                # 重新检查一次确保真的成功
                try:
                    file_inputs = page.query_selector_all('input[type="file"]')
                    if file_inputs:
                        self._save_cookies_after_login(context)
                        print(f"  💾 Cookie已保存")
                        browser.close()
                        return True
                    else:
                        print(f"  ⚠️ 检测到变化但没有上传元素，可能未完全登录")
                        browser.close()
                        return False
                except:
                    self._save_cookies_after_login(context)
                    print(f"  💾 Cookie已保存")
                    browser.close()
                    return True
            else:
                print(f"  ❌ 登录超时（{timeout}秒）")
                browser.close()
                return False

    def _save_cookies_after_login(self, context):
        """登录成功后保存Cookie"""
        cookies = context.cookies()
        cookie_dict = {}
        for c in cookies:
            cookie_dict[c["name"]] = c["value"]

        # 按平台保存关键Cookie
        key_cookies = {}
        for key in self.COOKIE_KEYS:
            if key in cookie_dict:
                key_cookies[key] = cookie_dict[key]

        if key_cookies:
            from .base import update_platform_cookies
            key_cookies["login_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            update_platform_cookies(self.name, key_cookies)
            print(f"  💾 Cookie已保存: {', '.join(key_cookies.keys())}")
        else:
            # 保存所有Cookie作为后备
            from .base import update_platform_cookies
            cookie_dict["login_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            update_platform_cookies(self.name, cookie_dict)
            print(f"  💾 Cookie已保存（全量）: {len(cookie_dict)}个字段")
