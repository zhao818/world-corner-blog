#!/usr/bin/env python3
"""
推理素材匹配器 — 分析文章主题，从推理库中推荐最匹配的谜题

用法:
  python logic_matcher.py "文章标题或关键词"          # 按关键词匹配
  python logic_matcher.py "文章.md" --file            # 按文章文件匹配
  python logic_matcher.py --list                      # 列出所有谜题
  python logic_matcher.py --add "标题" --tags "标签"   # 添加新谜题

输出: 推荐的谜题 id + 融入建议
"""
import sys, os, json, re

LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reasoning-library")
INDEX_PATH = os.path.join(LIB_DIR, "index.json")

def load_index():
    if not os.path.exists(INDEX_PATH):
        print(json.dumps({"version": 1, "puzzles": []}))
        return {"version": 1, "puzzles": []}
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def match_puzzles(keywords, top_n=3):
    """按关键词匹配最相关的谜题"""
    index = load_index()
    if not index["puzzles"]:
        return []

    kw_list = [k.strip().lower() for k in keywords.split() if k.strip()]
    if not kw_list:
        return index["puzzles"][:top_n]

    scored = []
    for p in index["puzzles"]:
        score = 0
        search_text = (p["title"] + " " + " ".join(p["tags"]) + " " +
                       " ".join(p["keywords"]) + " " + " ".join(p["mappings"])).lower()
        for kw in kw_list:
            if kw in search_text:
                score += 10
            if kw in p["mappings"]:
                score += 5  # mappings 匹配加分
            if kw in p["keywords"]:
                score += 3

        # 标题完全匹配加分
        if kw_list and any(kw in p["title"].lower() for kw in kw_list):
            score += 8

        if score > 0:
            scored.append((score, p))

    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:top_n]]

def recommend(keywords, top_n=3):
    """输出推荐结果"""
    results = match_packages(keywords, top_n)
    if not results:
        print("\n当前推理库中没有匹配的谜题。建议手动补充。")
        return

    print(f"\n匹配 '{keywords}' 推荐谜题：")
    for p in results:
        print(f"\n  [{p['id']}] {p['title']} ({'★' * p['difficulty']})")
        print(f"  类型: {p['type']}")
        print(f"  标签: {', '.join(p['tags'])}")
        print(f"  可映射: {', '.join(p['mappings'][:3])}")
        print(f"  文件: {p['file']}")

        # 读取融入建议
        fp = os.path.join(LIB_DIR, p['file'])
        if os.path.exists(fp):
            with open(fp, "r", encoding="utf-8") as f:
                content = f.read()
            m = re.search(r'## 融入建议\n\n(.+?)(?:\n##|\Z)', content, re.DOTALL)
            if m:
                tip = m.group(1).strip().split('\n')[0][:80]
                print(f"  融入建议: {tip}...")

match_packages = match_puzzles  # alias

def add_puzzle():
    """交互式添加新谜题"""
    print("添加新谜题到推理库")
    title = input("  标题: ").strip()
    ptype = input("  类型 (deduction/grid-puzzle/lateral-thinking/pattern/strategy/life-analogy): ").strip()
    tags = input("  标签 (逗号分隔): ").strip()
    mappings = input("  可映射的文章主题 (逗号分隔): ").strip()

    if not title or not ptype:
        print("标题和类型不能为空")
        return

    index = load_index()
    nid = f"r{len(index['puzzles']) + 1:03d}"

    entry = {
        "id": nid, "title": title, "type": ptype,
        "file": f"{ptype}/{nid}-{title.lower().replace(' ', '-')[:30]}.md",
        "difficulty": 3, "tags": [t.strip() for t in tags.split(",") if t.strip()],
        "keywords": [], "mappings": [m.strip() for m in mappings.split(",") if m.strip()]
    }

    index["puzzles"].append(entry)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"已添加 {nid} - {title}")
    print(f"请创建 {entry['file']} 补充题目详情和融入建议")

def main():
    if len(sys.argv) <= 1:
        print(main.__doc__)
        return

    if sys.argv[1] == "--list":
        index = load_index()
        for p in index["puzzles"]:
            diff = "★" * p.get("difficulty", 3)
            print(f"  [{p['id']}] {p['title']} {diff} [{p['type']}]")
        return

    if sys.argv[1] == "--add":
        add_puzzle()
        return

    if sys.argv[1] == "--file" and len(sys.argv) > 2:
        fp = sys.argv[2]
        with open(fp, "r", encoding="utf-8") as f:
            content = f.read()
        # 提取关键词：标题+前200字
        title_m = re.search(r'^#\s*(.+)$', content, re.MULTILINE)
        title = title_m.group(1) if title_m else os.path.basename(fp).replace(".md", "")
        keywords = title
    else:
        keywords = " ".join(sys.argv[1:])

    recommend(keywords)

if __name__ == "__main__":
    main()
