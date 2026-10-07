"""
一键发文脚本 - DeepSeek搜索 + JSON起草 + 公众号推送 + Token计费
用法: python publish_one.py              # AI自动选题
      python publish_one.py "选题标题"    # 手动选题
"""
import sys, os, re, json, time
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# Token 计数器
TK_DIR = os.path.join(SCRIPT_DIR, "deepseek_tokenizer", "deepseek_v3_tokenizer")
_tk = None
def ct(text):
    global _tk
    if _tk is None:
        try:
            from transformers import AutoTokenizer
            _tk = AutoTokenizer.from_pretrained(TK_DIR, trust_remote_code=True)
        except: pass
    if _tk:
        try: return len(_tk.encode(text))
        except: pass
    return len(text)

def log(msg):
    print(f"  {msg}")

def main():
    # 参数解析
    argv = sys.argv[1:]
    # 过滤 --推理 / --logic 标记
    logic_mode = any(a in ('--推理', '--logic') for a in argv)
    argv = [a for a in argv if a not in ('--推理', '--logic')]

    topic = argv[0] if argv else "AI编程效率提升"
    print(f"选题: {topic}" + ("  🧩 推理模式" if logic_mode else ""))
    t0 = time.time()
    from deepseek_web import search as ds

    # Step 0: 自动选题
    if not argv:
        print("\n[0/5] AI自动选题...")
        tp = "你是公众号「美好需要创造」的主编。定位：AI提效实战派。列出3个今天最适合发的选题。每行格式：1. 标题（<=9字）- 理由"
        tr = ds(tp)
        if tr.get("ok"):
            m = re.search(r'(?:^|\n)\s*1[.、]?\s*(.+?)(?:\s*[-–—]|\n|$)', tr["answer"])
            topic = m.group(1).strip()[:20] if m else tr["answer"].strip().split("\n")[0][:20]
            log(f"AI选题: {topic}")

    # Step 1: 搜索（永久加强——永远找逻辑矛盾）
    print("\n[1/5] DeepSeek搜索...")
    sp = f'搜索"{topic}"相关的最新观点、数据、案例。找出这个话题下面最反常识或最实用的3个发现，同时指出其中隐含的逻辑矛盾或两难选择。'
    r1 = ds(sp)
    if not r1.get("ok"): print(f"搜索失败: {r1.get('error')}"); return
    intel = r1["answer"]
    log(f"搜索 ({len(intel)}字, in={ct(sp)} out={ct(intel)} tok)")

    # Step 2: 起草 (JSON输出)
    print("\n[2/5] AI起草...")
    if logic_mode:
        # 🧩 推理模式：文章结构=迷面→解谜→答案
        body_template = (
            "## 壹 · 迷面\n"
            "抛出一个看似矛盾的现象或两难选择（像逻辑题的题目描述）\n"
            "✦ 金句\n\n"
            "## 贰 · 解谜\n"
            "一步步推理，排除干扰项，找到关键变量\n"
            "✦ 金句\n\n"
            "## 叁 · 答案\n"
            "给出结论 + 可操作的判断框架\n"
            "✦ 金句\n\n"
            "关注公众号「美好需要创造」，闲鱼搜「AI编程踩坑清单」"
        )
        style_extra = "文章结构采用「抛矛盾→推理解谜→给答案」的逻辑推理框架。开头像一道逻辑题（\"这里有三个看似矛盾的事实…\"），正文是解题过程，结尾像答案揭晓。保持推理感和悬念感。"
    else:
        body_template = (
            "## 壹 · 标题\n"
            "正文\n"
            "✦ 金句\n\n"
            "## 贰 · 标题\n"
            "正文\n"
            "✦ 金句\n\n"
            "## 叁 · 标题\n"
            "正文\n"
            "✦ 金句\n\n"
            "关注公众号「美好需要创造」，闲鱼搜「AI编程踩坑清单」"
        )
        style_extra = "语调接地气，不教学不说教。"

    dp = f"""你是公众号作者「美好需要创造」。定位：AI提效实战派。选题：「{topic}」。参考资料：{intel[:600]}

直接输出一个JSON（不要```标记）：
{{"title":"标题<=9字","digest":"摘要<=17字","body":"{body_template}"}}

body中用##壹贰叁做章节，每章配✦金句独占一行。{style_extra}"""
    r2 = ds(dp)
    if not r2.get("ok"): print(f"起草失败: {r2.get('error')}"); return
    raw = r2["answer"]
    log(f"起草 ({len(raw)}字, in={ct(dp)} out={ct(raw)} tok)")

    # JSON解析（V2：更健壮的提取 + 回退处理）
    raw_text = raw.strip()
    clean = raw_text
    # 去 markdown 代码块
    clean = re.sub(r'^```(?:json)?\s*\n?', '', clean)
    clean = re.sub(r'\n?```\s*$', '', clean)
    # 提取最外层 JSON 对象
    if not clean.startswith('{'):
        mj = re.search(r'\{[\s\S]*\}', clean)
        if mj: clean = mj.group(0)
        else: clean = raw_text

    title = topic[:9]; digest = topic[:17]; article = raw_text
    try:
        data = json.loads(clean)
        title = data.get('title', title)[:9]
        digest = data.get('digest', digest)[:17]
        body = data.get('body', '')
        if body:
            article = body
            log(f"JSON解析 OK | 标题:{title} | 摘要:{digest}")
        else:
            log("JSON解析 OK 但 body 为空")
    except json.JSONDecodeError:
        # JSON 解析失败 → 尝试把字面量 \n 转成真正换行
        log("JSON解析失败，尝试修复...")
        unescaped = raw_text.replace('\\n', '\n').replace('\\t', '\t')
        # 检查修复后是否有有效内容
        if unescaped != raw_text:
            article = unescaped
            log(f"已转义 \\n (修复后 {len(article)}字)")
        else:
            log("无法修复，使用原始文本")

    # Step 3: 推送公众号
    print("\n[3/5] 推送公众号...")
    from platforms.wechat import WechatPlatform
    wc = WechatPlatform()
    meta = {"title": title, "description": digest}
    pub = wc.publish(meta, article)
    mid = pub.get("media_id", "")
    if mid: log(f"草稿: {mid} (手动发布)")
    else: log(f"失败: {pub}")

    # Step 4: 登记（走 RegistryManager，格式统一）
    print("\n[4/5] 登记...")
    try:
        from content_dashboard import RegistryManager
        reg = RegistryManager()
        existing = reg.find_by_title(title)
        if existing:
            reg.update_platform(existing["id"], "wechat", "published" if mid else "failed")
            log(f"更新已有: {existing['id']}")
        else:
            new_id = reg.add_piece({"title": title, "digest": digest, "type": "article"})
            reg.update_platform(new_id, "wechat", "published" if mid else "failed")
            log(f"新增: {new_id}")
    except Exception as e: log(f"失败: {e}")

    # 计费汇总
    elapsed = time.time() - t0
    ti = ct(sp) + ct(dp); to = ct(intel) + ct(raw)
    cost = 0  # DeepSeek网页版免费，仅统计token量
    print(f"\n搞定 ({elapsed:.0f}s)")
    print(f"标题: {title} | 摘要: {digest} | 正文: {len(article)}字")
    print(f"Token: in={ti} out={to} total={ti+to}")
    print(f"费用: $0 (网页版免费) | 等效API费用: ${ti/1e6*0.14 + to/1e6*0.28:.6f}")

    # 写入仪表盘日志
    try:
        tlog = os.path.join(os.path.expanduser("~"), "token-usage.jsonl")
        with open(tlog, "a", encoding="utf-8") as f:
            json.dump({"timestamp": datetime.now(timezone.utc).isoformat(),
                        "model": "deepseek-web", "input_tokens": ti, "output_tokens": to,
                        "cost_usd": 0, "topic": title}, f, ensure_ascii=False)
            f.write("\n")
    except: pass

if __name__ == "__main__":
    main()
