#!/usr/bin/env python3
"""
爱发电（afdian.net）一键发文脚本

用法:
  python publish_afdian.py                          # AI自动选题 + 发布
  python publish_afdian.py "文章标题"                 # 手动选题 + AI起草 + 发布
  python publish_afdian.py article.md               # 从 MD 文件发布
  python publish_afdian.py article.md --title "标题" # MD文件 + 手动标题/摘要
  python publish_afdian.py article.md --visibility patrons  # 仅赞助者可见
  python publish_afdian.py --setup                  # 引导配置 Cookie

流程:
  [手动] MD文件 → 解析frontmatter → 生成封面 → 发布到爱发电
  [AI]   选题 → DeepSeek搜索 → AI起草(JSON) → 生成封面 → 发布到爱发电
"""

import sys
import os
import re
import json
import time
import tempfile
import argparse
from datetime import datetime
from pathlib import Path

# ---- 项目路径 ----
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

# ---- 品牌常量 ----
BRAND = "美好需要创造"
DARK_BG = "#1a1a2e"
GOLD = "#c8a03c"
FONT_PATH = "C:/Windows/Fonts/msyh.ttc"


# ============================================================
#  解析 Markdown
# ============================================================

def parse_markdown(filepath: str) -> tuple:
    """解析 Markdown，提取 YAML frontmatter 和正文"""
    content = Path(filepath).read_text(encoding="utf-8")
    meta = {}
    body = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().split("\n"):
                if ":" in line and not line.strip().startswith("#"):
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip('"').strip("'")
            body = parts[2].strip()

    meta.setdefault("title", os.path.basename(filepath).replace(".md", ""))
    meta.setdefault("digest", meta["title"])
    meta.setdefault("category", "创作")
    meta.setdefault("visibility", "public")

    return meta, body


# ============================================================
#  生成封面（统一品牌模板）
# ============================================================

def generate_cover(title: str, digest: str, category: str = "创作") -> str:
    """生成品牌封面 900×383"""
    from PIL import Image, ImageDraw, ImageFont

    W, H = 900, 383
    CENTER = W // 2
    img = Image.new("RGB", (W, H), DARK_BG)
    draw = ImageDraw.Draw(img)

    # 加载字体
    try:
        f18 = ImageFont.truetype(FONT_PATH, 18)
        f56 = ImageFont.truetype(FONT_PATH, 56)
        f20 = ImageFont.truetype(FONT_PATH, 20)
        f15 = ImageFont.truetype(FONT_PATH, 15)
        f14 = ImageFont.truetype(FONT_PATH, 14)
        f42 = ImageFont.truetype(FONT_PATH, 42)
        f36 = ImageFont.truetype(FONT_PATH, 36)
    except Exception:
        f18 = f56 = f20 = f15 = f14 = f42 = f36 = ImageFont.load_default()

    # 顶部品牌
    brand_text = "世界一隅 · WORLD CORNER"
    bb = draw.textbbox((0, 0), brand_text, font=f18)
    draw.text((CENTER - (bb[2] - bb[0]) // 2, 10), brand_text, fill="rgb(220,190,100)", font=f18)

    # 分类标签
    tag = f"· {category} ·"
    bb = draw.textbbox((0, 0), tag, font=f15)
    tw = bb[2] - bb[0]
    tx = CENTER - tw // 2
    draw.rectangle([(tx - 8, 56), (tx + tw + 8, 78)], outline=GOLD, width=1)
    draw.text((tx, 58), tag, fill=GOLD, font=f15)

    # 标题（自适应字号）
    title_font = f56
    bb = draw.textbbox((0, 0), title, font=f56)
    if bb[2] - bb[0] > W - 60:
        bb = draw.textbbox((0, 0), title, font=f42)
        if bb[2] - bb[0] > W - 60:
            title_font = f36
        else:
            title_font = f42

    bb = draw.textbbox((0, 0), title, font=title_font)
    draw.line([(260, 185), (640, 185)], fill=GOLD, width=2)
    draw.text((CENTER - (bb[2] - bb[0]) // 2, 115), title, fill=GOLD, font=title_font)
    draw.line([(340, 215), (560, 215)], fill=GOLD, width=2)

    # 金句摘要
    draw.text((438, 232), "✦", fill=GOLD, font=f20)
    bb = draw.textbbox((0, 0), digest, font=f20)
    draw.text((CENTER - (bb[2] - bb[0]) // 2, 270), digest, fill="#b4b4d2", font=f20)

    # 底部
    today = datetime.now().strftime("%Y.%m.%d")
    draw.text((30, 350), f"{BRAND} / {today}", fill="#8c8caa", font=f14)
    for x in [30, 52, 74]:
        draw.ellipse([(x, 358), (x + 8, 366)], fill=GOLD)
    for x in [854, 832, 810]:
        draw.ellipse([(x, 358), (x + 8, 366)], fill=GOLD)

    cover_path = os.path.join(tempfile.gettempdir(), "afdian_cover.jpg")
    img.save(cover_path, "JPEG", quality=95)
    print(f"  🎨 封面已生成: {cover_path}")
    return cover_path


# ============================================================
#  AI 起草（DeepSeek Web 搜索）
# ============================================================

def ai_draft(topic: str) -> dict:
    """
    DeepSeek Web 搜索 + AI 起草文章
    返回 {"title": "...", "digest": "...", "body": "..."}
    """
    from deepseek_web import search as ds

    print(f"\n{'='*50}")
    print(f"  🤖 AI 起草: {topic}")
    print(f"{'='*50}")

    # Step 1: 搜索
    print("\n[1/2] DeepSeek 搜索相关资料...")
    search_prompt = (
        f'搜索"{topic}"相关的最新观点、数据、案例。'
        f'找出这个话题下面最反常识或最实用的3个发现。'
        f'用中文回答，每个发现100-200字。'
    )
    r1 = ds(search_prompt)
    if not r1.get("ok"):
        print(f"  搜索失败: {r1.get('error')}")
        return {}

    intel = r1["answer"]
    print(f"  搜索完成 ({len(intel)} 字)")

    # Step 2: 起草
    print("\n[2/2] AI 起草文章...")
    draft_prompt = f"""你是创作者「{BRAND}」。定位：AI提效 + 深度思考。
选题：「{topic}」。参考资料：
{intel[:800]}

直接输出一个 JSON 对象（不要用 ``` 标记）：
{{"title":"标题<=15字","digest":"摘要<=30字","body":"## 壹 · 标题\\n正文段落\\n✦ 金句独占一行\\n\\n## 贰 · 标题\\n正文段落\\n✦ 金句独占一行\\n\\n## 叁 · 标题\\n正文段落\\n✦ 金句独占一行\\n\\n关注公众号「美好需要创造」"}}

语调接地气，不教学不说教。body 中用 ## 壹贰叁 做章节，每章配 ✦ 金句独占一行。
如果搜索结果的资料不够新/不够深，可以用你自己的知识补充。"""

    r2 = ds(draft_prompt)
    if not r2.get("ok"):
        print(f"  起草失败: {r2.get('error')}")
        return {}

    raw = r2["answer"]
    print(f"  起草完成 ({len(raw)} 字)")

    # 提取 JSON
    clean = raw.strip()
    clean = re.sub(r'^```(?:json)?\s*\n?', '', clean)
    clean = re.sub(r'\n?```\s*$', '', clean)
    if not clean.startswith('{'):
        m = re.search(r'\{[\s\S]*\}', clean)
        if m:
            clean = m.group(0)

    try:
        data = json.loads(clean)
        title = data.get("title", topic[:15])
        digest = data.get("digest", topic[:30])
        body = data.get("body", raw)
        print(f"  ✅ JSON 解析成功 | 标题:{title} | 摘要:{digest}")
        return {"title": title, "digest": digest, "body": body}
    except json.JSONDecodeError:
        print(f"  ⚠️ JSON 解析失败，使用原文")
        return {"title": topic[:15], "digest": topic[:30], "body": raw}


# ============================================================
#  引导配置 Cookie
# ============================================================

def setup_cookies():
    """引导用户配置爱发电 Cookie"""
    print("""
╔══════════════════════════════════════════╗
║   爱发电 Cookie 配置引导                   ║
╚══════════════════════════════════════════╝

请按以下步骤操作:

1. 打开 Chrome/Edge，访问 afdian.net 并登录
2. 按 F12 打开开发者工具
3. 进入 Application → Cookies → afdian.net
4. 找到 auth_token（或类似名称）的值

爱发电关键 Cookie:
  - auth_token  (登录令牌)
  - 也可以直接导出所有 Cookie 为 JSON

📋 粘贴方式: 在下方粘贴 auth_token 的值
   或直接粘贴完整的 Cookie JSON 对象
""")

    raw = input("   Cookie 值: ").strip()
    if not raw:
        print("❌ 未输入任何值")
        return

    # 尝试解析 JSON
    creds = {}
    try:
        creds = json.loads(raw)
    except json.JSONDecodeError:
        # 当作单个 auth_token
        creds = {"auth_token": raw}

    from platforms.base import update_platform_cookies
    update_platform_cookies("afdian", creds)
    print(f"\n✅ 已保存 {len(creds)} 个 Cookie 到 ~/.claude/platform-cookies.json")


# ============================================================
#  主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="爱发电一键发文",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python publish_afdian.py                         # AI 选题 + 自动发布
  python publish_afdian.py "AI编程效率提升"          # 手动选题 + AI起草
  python publish_afdian.py article.md               # 从 MD 文件发布
  python publish_afdian.py article.md --visibility patrons   # 仅赞助者可见
  python publish_afdian.py --setup                  # 配置 Cookie
        """,
    )

    parser.add_argument("input", nargs="?", help="文章标题 或 Markdown 文件路径")
    parser.add_argument("--title", "-t", help="手动指定标题")
    parser.add_argument("--digest", "-d", help="手动指定摘要")
    parser.add_argument("--category", "-c", default="创作", help="分类（默认: 创作）")
    parser.add_argument("--visibility", "-v", default="public",
                        choices=["public", "patrons"],
                        help="可见范围: public=公开, patrons=仅赞助者")
    parser.add_argument("--no-ai", action="store_true", help="不调用 AI，直接用输入作标题")
    parser.add_argument("--setup", action="store_true", help="引导配置爱发电 Cookie")
    parser.add_argument("--no-cover", action="store_true", help="不生成封面图")

    args = parser.parse_args()

    # 引导模式
    if args.setup:
        setup_cookies()
        return

    # ---- 确定标题/摘要/正文 ----
    title = args.title or ""
    digest = args.digest or ""
    body_md = ""
    category = args.category

    if not args.input:
        # 无输入 → AI 自动选题
        print("🎲 AI 自动选题模式")
        topic_prompt = (
            f"你是公众号「{BRAND}」的主编。定位：AI提效实战派。"
            f"列出3个今天最适合发的选题。每行格式：1. 标题（≤15字）- 理由"
        )
        from deepseek_web import search as ds
        tr = ds(topic_prompt)
        if tr.get("ok"):
            m = re.search(r'(?:^|\n)\s*1[.、]?\s*(.+?)(?:\s*[-–—]|\n|$)', tr["answer"])
            topic = m.group(1).strip()[:20] if m else tr["answer"].strip().split("\n")[0][:20]
            print(f"  AI 选题: {topic}")
        else:
            topic = "AI编程效率提升"
            print(f"  选题失败，使用默认: {topic}")

        draft = ai_draft(topic)
        if draft:
            title = draft["title"]
            digest = draft["digest"]
            body_md = draft["body"]
        else:
            print("❌ AI 起草失败")
            return

    elif args.input.endswith(".md") and os.path.exists(args.input):
        # MD 文件模式
        print(f"📄 解析: {args.input}")
        meta, body_md = parse_markdown(args.input)
        title = args.title or meta.get("title", "")
        digest = args.digest or meta.get("digest", "")
        if meta.get("visibility"):
            args.visibility = meta["visibility"]
        print(f"  标题: {title}")
        print(f"  可见: {args.visibility}")

    elif args.no_ai:
        # 手动模式，不用 AI
        title = args.input
        digest = args.digest or args.input
        body_md = args.input  # 直接用作正文
        print(f"📝 手动模式: {title}")

    else:
        # 手动选题 + AI 起草
        topic = args.input
        print(f"📝 选题: {topic}")
        draft = ai_draft(topic)
        if draft:
            title = args.title or draft["title"]
            digest = args.digest or draft["digest"]
            body_md = draft["body"]
        else:
            print("❌ AI 起草失败")
            return

    # ---- 最终确认 ----
    print(f"\n{'='*50}")
    print(f"  📋 发布预览")
    print(f"{'='*50}")
    print(f"  标题: {title}")
    print(f"  摘要: {digest}")
    print(f"  正文: {len(body_md)} 字")
    print(f"  平台: 爱发电 (afdian.net)")
    print(f"  可见: {args.visibility}")
    print(f"{'='*50}")

    # ---- 生成封面 ----
    cover_path = None
    if not args.no_cover:
        cover_path = generate_cover(title, digest, category)

    # ---- 发布 ----
    print(f"\n🚀 发布到爱发电...")
    from platforms.afdian import AfdianPlatform

    afdian = AfdianPlatform()
    meta = {
        "title": title,
        "digest": digest,
        "category": category,
        "visibility": args.visibility,
    }

    result = afdian.publish(meta, body_md, cover_path)

    # ---- 结果 ----
    print(f"\n{'='*50}")
    if result.get("success"):
        print(f"  ✅ 发布成功！")
        if result.get("url"):
            print(f"  🔗 {result['url']}")
        if result.get("note"):
            print(f"  📝 {result['note']}")
    else:
        print(f"  ❌ 发布失败: {result.get('error', '未知错误')}")
    print(f"{'='*50}")

    # ---- 记录到发布日志 ----
    if result.get("success"):
        try:
            from platforms.publish_log import record_publish
            record_publish(title, "afdian", "article", result.get("url", ""))
            print(f"\n📋 已记录到发布日志")
        except Exception as e:
            print(f"\n⚠️ 发布日志记录失败: {e}")

    # ---- 清理 ----
    if cover_path and os.path.exists(cover_path):
        os.remove(cover_path)

    # ---- 管线命令（下次直接用） ----
    if args.input and args.input.endswith(".md"):
        print(f"\n💡 下次直接发:")
        print(f"   python publish_afdian.py {args.input}")
    else:
        print(f"\n💡 下次直接发:")
        print(f"   python publish_afdian.py \"{title}\"")


if __name__ == "__main__":
    main()
