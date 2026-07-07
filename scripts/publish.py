#!/usr/bin/env python3
"""
通用发布管线：Markdown 文件 → 文章发布  |  MP4 → 视频发布

文章平台: 公众号(wechat) | 掘金(juejin) | 知乎(zhihu) | 即刻(jike) | 腾讯云(tencent_cloud)
视频平台: 抖音(douyin) | B站(bilibili) | 快手(kuaishou) | 视频号(channels) | 小红书(xiaohongshu)

用法:
  python publish.py article.md                     # 发布到所有文章平台
  python publish.py article.md --wx-only           # 只发公众号
  python publish.py article.md --zhihu             # 只发知乎
  python publish.py article.md --jj-only           # 只发掘金
  python publish.py article.md --jike              # 只发即刻
  python publish.py article.md --tencent           # 只发腾讯云
  python publish.py video.mp4 --douyin             # 只发抖音（视频模式）
  python publish.py video.mp4 --bilibili           # 只发 B站（视频模式）
  python publish.py video.mp4 --all                # 发到所有视频平台
  python publish.py --setup-bilibili               # 引导配置 B站 Cookie
  python publish.py --setup-kuaishou               # 引导配置快手 OAuth
  python publish.py --list-platforms               # 列出所有平台

约定: Markdown 文件头部 YAML frontmatter:
  ---
  title: "标题"
  digest: "摘要"
  category: "技术"
  juejin_category: "6809637771511070734"
  juejin_tags: "6809640445233070098"
  ---
"""

import sys, os, json, re, requests, argparse
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# ===== 平台模块 =====
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from platforms.base import DARK_BG, GOLD, BRAND, get_platform_cookies, update_platform_cookies, load_cookies, save_cookies
from platforms import list_platforms as _list_platforms, publish_to
from platforms.publish_log import check_duplicate, record_publish

# ===== 配置 =====
FONT_PATH = "C:/Windows/Fonts/msyh.ttc"

# 导入时自动触发所有平台模块注册
import platforms.wechat    # noqa
import platforms.juejin    # noqa
import platforms.bilibili  # noqa
import platforms.kuaishou  # noqa
import platforms.douyin    # noqa
import platforms.zhihu     # noqa
import platforms.tencent_cloud  # noqa
import platforms.channels  # noqa
import platforms.xiaohongshu  # noqa
import platforms.goofish     # noqa
import platforms.jike        # noqa


# ===== 工具函数 =====

def parse_markdown(filepath):
    """解析 Markdown 文件，提取 YAML frontmatter 和正文"""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    meta = {}
    body = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            meta_text = parts[1]
            body = parts[2].strip()
            for line in meta_text.strip().split("\n"):
                line = line.strip()
                if ":" in line and not line.startswith("#"):
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip('"').strip("'")

    # 默认值
    meta.setdefault("title", os.path.basename(filepath).replace(".md", ""))
    meta.setdefault("digest", meta["title"])
    meta.setdefault("category", "技术")
    meta.setdefault("juejin_category", "6809637771511070734")
    meta.setdefault("juejin_tags", "6809640445233070098")

    return meta, body


def generate_cover(title, digest, category):
    """生成品牌封面 900×383，使用品牌色"""
    W, H = 900, 383
    CENTER = W // 2
    img = Image.new("RGB", (W, H), DARK_BG)
    draw = ImageDraw.Draw(img)

    try:
        f18 = ImageFont.truetype(FONT_PATH, 18)
        f56 = ImageFont.truetype(FONT_PATH, 56)
        f20 = ImageFont.truetype(FONT_PATH, 20)
        f15 = ImageFont.truetype(FONT_PATH, 15)
        f14 = ImageFont.truetype(FONT_PATH, 14)
    except Exception:
        f18 = f56 = f20 = f15 = f14 = ImageFont.load_default()

    brand = "世界一隅 · WORLD CORNER"
    bb = draw.textbbox((0, 0), brand, font=f18)
    draw.text((CENTER - (bb[2] - bb[0]) // 2, 10), brand, fill="rgb(220,190,100)", font=f18)

    tag = f"· {category} ·"
    bb = draw.textbbox((0, 0), tag, font=f15)
    tw = bb[2] - bb[0]
    tx = CENTER - tw // 2
    draw.rectangle([(tx - 8, 56), (tx + tw + 8, 78)], outline=GOLD, width=1)
    draw.text((tx, 58), tag, fill=GOLD, font=f15)

    draw.line([(260, 185), (640, 185)], fill=GOLD, width=2)
    bb = draw.textbbox((0, 0), title, font=f56)
    draw.text((CENTER - (bb[2] - bb[0]) // 2, 115), title, fill=GOLD, font=f56)
    draw.line([(340, 215), (560, 215)], fill=GOLD, width=2)

    draw.text((438, 232), "✦", fill=GOLD, font=f20)
    bb = draw.textbbox((0, 0), digest, font=f20)
    draw.text((CENTER - (bb[2] - bb[0]) // 2, 270), digest, fill="#b4b4d2", font=f20)

    today = datetime.now().strftime("%Y.%m.%d")
    draw.text((30, 350), f"{BRAND} / {today}", fill="#8c8caa", font=f14)
    for x in [30, 52, 74]:
        draw.ellipse([(x, 358), (x + 8, 366)], fill=GOLD)
    for x in [854, 832, 810]:
        draw.ellipse([(x, 358), (x + 8, 366)], fill=GOLD)

    # 保存封面
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        cover_path = tmp.name
    img.save(cover_path, "JPEG", quality=95)
    return cover_path


# ===== 设置引导 =====

def setup_bilibili():
    """引导用户配置 B站 Cookie"""
    print("""
╔══════════════════════════════════════════╗
║     B站 Cookie 配置引导                    ║
╚══════════════════════════════════════════╝

请按以下步骤操作:

1. 打开 Chrome/Edge，访问 bilibili.com 并登录
2. 按 F12 打开开发者工具
3. 进入 Application → Cookies → bilibili.com
4. 找到以下 Cookie 字段的值:
""")

    sessdata = input("   SESSDATA: ").strip()
    bili_jct = input("   bili_jct: ").strip()
    dedeuserid = input("   DedeUserID (可选): ").strip()
    buvid3 = input("   buvid3 (可选): ").strip()

    if sessdata and bili_jct:
        update_platform_cookies("bilibili", {
            "SESSDATA": sessdata,
            "bili_jct": bili_jct,
            "DedeUserID": dedeuserid,
            "buvid3": buvid3,
            "configured_at": datetime.now().isoformat(),
        })
        print("\n✅ B站 Cookie 已保存到 ~/.claude/platform-cookies.json")
        print("   现在可以运行: python scripts/publish.py article.md --bilibili")
    else:
        print("\n❌ SESSDATA 和 bili_jct 是必填项，请重新运行 --setup-bilibili")


def setup_kuaishou():
    """引导用户配置快手"""
    from platforms.kuaishou import KuaishouPlatform
    kp = KuaishouPlatform()
    kp.setup_auth()


# ===== 主入口 =====

def main():
    parser = argparse.ArgumentParser(
        description="通用发布管线：MD → 文章平台 | MP4 → 视频平台",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python publish.py article.md                    # 全文章平台发布（公众号+掘金+知乎+即刻）
  python publish.py article.md --wx-only          # 只发公众号
  python publish.py article.md --zhihu            # 只发知乎
  python publish.py article.md --jj-only          # 只发掘金
  python publish.py article.md --jike             # 只发即刻
  python publish.py video.mp4 --douyin            # 只发抖音（视频模式）
  python publish.py video.mp4 --all               # 所有视频平台
  python publish.py --setup-bilibili              # 配置 B站 Cookie
  python publish.py --list-platforms              # 列出支持平台
        """,
    )

    parser.add_argument("file", nargs="?", help="Markdown 文件路径")
    parser.add_argument("--wx-only", action="store_true", help="只发公众号")
    parser.add_argument("--jj-only", action="store_true", help="只发掘金")
    parser.add_argument("--bilibili", action="store_true", help="只发 B站（或加入发布列表）")
    parser.add_argument("--kuaishou", action="store_true", help="只发快手（或加入发布列表）")
    parser.add_argument("--douyin", action="store_true", help="只发抖音（或加入发布列表）")
    parser.add_argument("--zhihu", action="store_true", help="只发知乎（或加入发布列表）")
    parser.add_argument("--jike", action="store_true", help="只发即刻（或加入发布列表）")
    parser.add_argument("--tencent", "--tencent_cloud", action="store_true", help="只发腾讯云（或加入发布列表）")
    parser.add_argument("--channels", action="store_true", help="只发视频号（或加入发布列表）")
    parser.add_argument("--playwright", action="store_true", help="快手使用 Playwright 浏览器自动化")
    parser.add_argument("--no-cover", action="store_true", help="不生成封面")
    parser.add_argument("--setup-bilibili", action="store_true", help="引导配置 B站 Cookie")
    parser.add_argument("--setup-kuaishou", action="store_true", help="引导配置快手 OAuth")
    parser.add_argument("--list-platforms", action="store_true", help="列出所有支持平台")
    parser.add_argument("--log", action="store_true", help="查看最近30天发布记录")
    parser.add_argument("--sync-wechat-urls", action="store_true", help="同步公众号已发布文章URL")
    parser.add_argument("--set-wechat-url", help="手动设置最新公众号文章URL")
    # 智能回答模式
    parser.add_argument("--answer", action="store_true", help="回答模式：将文件作为知乎回答发布")
    parser.add_argument("--question-id", help="回答模式：目标问题 ID")
    args = parser.parse_args()

    # 设置模式
    if args.setup_bilibili:
        setup_bilibili()
        return
    if args.setup_kuaishou:
        setup_kuaishou()
        return
    if args.list_platforms:
        print("支持平台:")
        from platforms import REGISTRY
        for name, p in REGISTRY.items():
            print(f"  {name:12s} → {p.display_name}")
        return
    if args.log:
        from platforms.publish_log import print_summary
        print_summary(30)
        return
    if args.sync_wechat_urls:
        from platforms.wechat import WechatPlatform
        wp = WechatPlatform()
        print("🔄 同步公众号已发布文章URL...")
        urls = wp.sync_published_urls()
        if urls:
            print(f"✅ 已同步 {len(urls)} 篇文章:")
            for t, u in urls.items():
                print(f"   {t}: {u}")
        else:
            print("⚠️ API 无权限（errcode=48001），请用 --set-wechat-url 手动设置")
        return
    if args.set_wechat_url:
        from platforms.wechat import WechatPlatform
        wp = WechatPlatform()
        wp._save_to_registry("手动设置", args.set_wechat_url.strip())
        print(f"✅ 文章URL已保存: {args.set_wechat_url.strip()}")
        return

    # ── 智能回答模式 ──
    if args.answer:
        if not args.question_id:
            print("❌ 回答模式需要 --question-id 参数")
            print("   示例: python publish.py answer.md --answer --question-id=123456")
            sys.exit(1)

        from platforms.zhihu import ZhihuPlatform
        zp = ZhihuPlatform()

        print(f"\n📤 发布回答到问题 {args.question_id}...")
        _check_and_warn(meta.get("title", ""), "zhihu")
        result = zp.publish_answer(args.question_id, body)
        _print_result("zhihu", result, meta.get("title", ""), "answer")
        print()
        print("   管线命令 (下次直接发):")
        print(f"     python publish.py {args.file} --answer --question-id={args.question_id}")
        return

    # 发布模式
    if not args.file:
        parser.print_help()
        return

    md_file = os.path.abspath(args.file)
    if not os.path.exists(md_file):
        print(f"❌ 文件不存在: {md_file}")
        sys.exit(1)

    print(f"📄 解析: {md_file}")
    meta, body = parse_markdown(md_file)

    title = meta.get("title", "")
    digest = meta.get("digest", "")
    category = meta.get("category", "技术")

    print(f"   标题: {title}")
    print(f"   摘要: {digest}")

    # 生成封面
    cover_path = None
    if not args.no_cover:
        print(f"\n🎨 生成封面...")
        cover_path = generate_cover(title, digest, category)
        print(f"   封面: {cover_path}")

    # 决定要发布的平台（支持任意组合）
    specific_platforms = []
    if args.wx_only:    specific_platforms.append("wechat")
    if args.jj_only:    specific_platforms.append("juejin")
    if args.zhihu:      specific_platforms.append("zhihu")
    if args.jike:       specific_platforms.append("jike")
    if args.tencent:    specific_platforms.append("tencent_cloud")

    # 公众号优先发布（其他平台需要它的文章链接）
    wechat_first = "wechat" in specific_platforms or (not specific_platforms)
    if wechat_first and "wechat" not in specific_platforms:
        # 默认全平台模式：确保公众号在列表里
        pass  # 由 all_platforms 处理

    # 如果指定了即刻，确保公众号先发（需要公众号URL）
    article_url = ""

    # 组合模式
    results = {}

    if specific_platforms:
        # 公众号优先
        ordered = specific_platforms
        if "wechat" in ordered and ordered[0] != "wechat":
            ordered = ["wechat"] + [p for p in ordered if p != "wechat"]

        for name in ordered:
            print(f"\n{'='*50}")
            _check_and_warn(title, name)
            # 传文章URL给需要链接的平台（即刻、知乎等）
            if name in ("jike",) and article_url:
                meta["url"] = article_url
                print(f"   🔗 附带公众号文章链接: {article_url}")
            result = publish_to(name, meta, body, cover_path)
            results[name] = result
            _print_result(name, result, title, "article")
            # 公众号发布成功后提取URL
            if name == "wechat" and result.get("success") and result.get("url"):
                article_url = result["url"]
    else:
        all_platforms = ["wechat", "juejin", "zhihu", "jike", "tencent_cloud"]
        for name in all_platforms:
            print(f"\n{'='*50}")
            _check_and_warn(title, name)
            if name in ("jike",) and article_url:
                meta["url"] = article_url
                print(f"   🔗 附带公众号文章链接: {article_url}")
            result = publish_to(name, meta, body, cover_path)
            results[name] = result
            _print_result(name, result, title, "article")
            if name == "wechat" and result.get("success") and result.get("url"):
                article_url = result["url"]

    # 汇总
    print(f"\n{'='*50}")
    success_count = sum(1 for r in results.values() if r.get("success"))
    total = len(results)
    if success_count == total:
        print(f"✅ 全平台发布完成 ({total}/{total})")
    elif success_count > 0:
        print(f"⚠️  部分完成 ({success_count}/{total})，见上方详情")
    else:
        print(f"❌ 发布失败 ({success_count}/{total})，检查各平台配置")

    # 清理临时封面
    if cover_path and os.path.exists(cover_path):
        os.remove(cover_path)


def _print_result(name: str, result: dict, title: str = "", pub_type: str = "article"):
    """格式化打印发布结果，并记录到发布日志"""
    from platforms import REGISTRY
    display = REGISTRY.get(name, type('obj', (object,), {'display_name': name})()).display_name \
        if name in REGISTRY else name
    try:
        display = REGISTRY[name].display_name
    except (KeyError, AttributeError):
        display = name

    if result.get("success"):
        url = result.get("url", "")
        note = result.get("note", "")
        extra = f" → {url}" if url else ""
        hint = f" ({note})" if note else ""
        print(f"[{display}] ✅ 成功{extra}{hint}")
        # 记录到发布日志
        if title:
            record_publish(title, name, pub_type, url)
    else:
        error = result.get("error", "未知错误")
        print(f"[{display}] ❌ {error}")


def _check_and_warn(title: str, name: str) -> bool:
    """发布前查重，发现重复打印警告。返回是否重复"""
    dup = check_duplicate(title, name)
    if dup:
        days_ago = (datetime.now() - datetime.fromisoformat(dup["date"])).days
        print(f"  ⚠️  重复警告：{days_ago}天前已在[{name}]发布过「{title[:30]}」")
        return True
    return False


def main_video(filepath: str, targets: list[str], title: str, desc: str, cover_path: str = None):
    """视频发布模式"""
    from platforms import publish_video_to, REGISTRY

    results = {}
    for name in targets:
        print(f"\n{'='*50}")
        _check_and_warn(title, name)
        result = publish_video_to(name, filepath, title, desc, tags, cover_path=cover_path)
        results[name] = result
        _print_result(name, result, title, "video")

    ok = sum(1 for r in results.values() if r.get("success"))
    print(f"\n{'='*50}")
    if ok == len(results):
        print(f"✅ 视频全平台发布完成 ({ok}/{len(results)})")
    elif ok > 0:
        print(f"⚠️  部分完成 ({ok}/{len(results)})")
    else:
        print(f"❌ 所有平台失败")


if __name__ == "__main__":
    # 先判断是视频还是图文
    if len(sys.argv) > 1 and sys.argv[1].endswith('.mp4'):
        # 视频模式
        import argparse as _ap
        _parser = _ap.ArgumentParser(description="视频发布：MP4 → 抖音/快手/B站")
        _parser.add_argument("video", help="MP4 视频文件")
        _parser.add_argument("--title", "-t", default="")
        _parser.add_argument("--desc", "-d", default="")
        _parser.add_argument("--tags", default="")
        _parser.add_argument("--douyin", action="store_true")
        _parser.add_argument("--kuaishou", action="store_true")
        _parser.add_argument("--bilibili", action="store_true")
        _parser.add_argument("--channels", action="store_true")
        _parser.add_argument("--xiaohongshu", action="store_true")
        _parser.add_argument("--all", action="store_true")
        _args = _parser.parse_args()

        if not os.path.exists(_args.video):
            print(f"❌ 文件不存在: {_args.video}")
            sys.exit(1)

        # 自动从同名 .md 文件读标题
        title = _args.title or ""
        desc = _args.desc or ""
        tags = _args.tags or ""
        if not title:
            md_candidate = os.path.splitext(_args.video)[0] + '.md'
            if os.path.exists(md_candidate):
                md_meta, _ = parse_markdown(md_candidate)
                title = md_meta.get('title', '')
                desc = md_meta.get('digest', title)
                print(f"📄 从 {md_candidate} 读取标题: {title}")
        if not title:
            title = os.path.splitext(os.path.basename(_args.video))[0]
        if not desc:
            desc = title

        targets = []
        if _args.all:
            targets = ["douyin", "kuaishou", "bilibili", "channels"]
        else:
            if _args.douyin:   targets.append("douyin")
            if _args.kuaishou: targets.append("kuaishou")
            if _args.bilibili: targets.append("bilibili")
            if _args.channels: targets.append("channels")
            if _args.xiaohongshu: targets.append("xiaohongshu")
        if not targets:
            targets = ["douyin", "kuaishou", "bilibili"]

        print(f"📹 {_args.video}")
        print(f"📝 标题: {title}")
        print(f"📤 目标: {', '.join(targets)}")

        # 生成封面
        cover_path = None
        if not _args.douyin and not _args.channels and not _args.xiaohongshu:
            try:
                cover_path = generate_cover(title, desc, "视频")
                print(f"🎨 封面已生成: {cover_path}")
            except Exception as e:
                print(f"🎨 封面生成跳过: {e}")

        main_video(_args.video, targets, title, desc, cover_path=cover_path)

        # 清理封面
        if cover_path and os.path.exists(cover_path):
            os.remove(cover_path)
    else:
        main()
