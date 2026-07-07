"""B站登录脚本 — 等待用户扫码，保存Cookie"""
import time, json, os
from playwright.sync_api import sync_playwright

COOKIE_PATH = os.path.expanduser("~/.claude/platform-cookies.json")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()

    page.goto("https://member.bilibili.com/video/upload")
    page.wait_for_load_state("domcontentloaded")
    time.sleep(3)

    print("🔑 浏览器已打开，请登录B站")
    print("📱 扫码登录后，看到上传页面自动保存")
    print("⏳ 等待中...")

    # 每5秒检查一次，最多等5分钟
    for i in range(60):
        time.sleep(5)
        try:
            file_inputs = page.query_selector_all('input[type="file"]')
            if file_inputs:
                print("✅ 检测到上传页面！正在保存Cookie...")
                cookies = context.cookies()
                cookie_dict = {}
                for c in cookies:
                    cookie_dict[c["name"]] = c["value"]

                # 读取现有Cookie
                if os.path.exists(COOKIE_PATH):
                    with open(COOKIE_PATH, "r", encoding="utf-8") as f:
                        all_cookies = json.load(f)
                else:
                    all_cookies = {}

                # 更新B站Cookie
                all_cookies["bilibili"] = cookie_dict
                all_cookies["bilibili"]["login_time"] = time.strftime("%Y-%m-%d %H:%M:%S")

                with open(COOKIE_PATH, "w", encoding="utf-8") as f:
                    json.dump(all_cookies, f, ensure_ascii=False, indent=2)

                print(f"💾 Cookie已保存！字段数: {len(cookie_dict)}")
                browser.close()
                break
        except:
            pass

        if i % 6 == 0:
            print(f"  ⏳ 已等待{i*5}秒...")
    else:
        print("❌ 超时（5分钟）")
        browser.close()
