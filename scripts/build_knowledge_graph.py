#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_knowledge_graph.py
为「世界一隅」构建 Obsidian 风格的网状知识拓扑与反向链接数据。
扫描 content/ 目录下所有 Markdown 文章，提取元数据、标签、正向链接与 [[WikiLink]] 引用，
计算双向链接、反向链接（Backlinks）与同频关联文章（Related Articles），
生成 static/data/graph-data.json 供前端交互星图与文章反链卡片使用。
"""

import os
import re
import json
import yaml
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = BASE_DIR / "content"
OUTPUT_DIR = BASE_DIR / "static" / "data"
OUTPUT_FILE = OUTPUT_DIR / "graph-data.json"

# 需要排除的页面
EXCLUDE_FILENAMES = {
    "_index.md", "_index.en.md", "archives.md", "archives.en.md",
    "search.md", "search.en.md", "graph.md", "graph.en.md"
}

# 栏目分类映射与友好名称
SECTION_NAMES = {
    "systems-thinking": "系统思维",
    "era-observation": "时代观察",
    "learning": "认知成长",
    "tooling": "效率工具",
    "civilization-ladder": "文明阶梯",
    "pitfalls": "工程避坑",
    "audiobook": "九书听读",
    "collections": "合集整理",
    "about": "关于一隅"
}

def clean_text(text):
    if not text:
        return ""
    # 去除 Markdown 格式标记
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', r'\1', text)
    text = re.sub(r'[*_`~>]', '', text)
    return text.strip()

def extract_excerpt(content, target_keyword, max_len=110):
    """提取包含目标关键词的上下文片段"""
    pos = content.find(target_keyword)
    if pos == -1:
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip() and not p.strip().startswith(('---', '#', '>'))]
        return clean_text(paragraphs[0])[:max_len] + "…" if paragraphs else ""
    start = max(0, pos - 40)
    end = min(len(content), pos + len(target_keyword) + 60)
    snippet = clean_text(content[start:end])
    if start > 0:
        snippet = "…" + snippet
    if end < len(content):
        snippet = snippet + "…"
    return snippet

def get_rel_permalink(file_path):
    """计算相对于站点根目录的相对链接"""
    rel = file_path.relative_to(CONTENT_DIR)
    parts = list(rel.parts)
    filename = parts[-1]
    is_en = filename.endswith(".en.md")
    
    # 去除扩展名
    if is_en:
        slug = filename[:-6]
    elif filename.endswith(".md"):
        slug = filename[:-3]
    else:
        slug = filename
        
    path_parts = parts[:-1]
    
    if is_en:
        permalink = "/en/" + "/".join(path_parts) + ("/" if path_parts else "") + slug + "/"
    else:
        permalink = "/" + "/".join(path_parts) + ("/" if path_parts else "") + slug + "/"
        
    # 规整化连续斜杠
    permalink = re.sub(r'/+', '/', permalink)
    return permalink, is_en, path_parts[0] if path_parts else "root"

def main():
    print("🚀 开始构建知识拓扑与双链关系网络...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    articles = {}
    title_to_url = {}
    slug_to_url = {}
    
    # 1. 扫描所有文件并收集基础信息
    for root, _, files in os.walk(CONTENT_DIR):
        for f in files:
            if not f.endswith(".md") or f in EXCLUDE_FILENAMES:
                continue
                
            file_path = Path(root) / f
            try:
                raw_text = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception as e:
                print(f"⚠️ 读取失败 {file_path}: {e}")
                continue
                
            fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw_text, re.DOTALL)
            if not fm_match:
                continue
                
            fm_text, body_text = fm_match.group(1), fm_match.group(2)
            try:
                fm = yaml.safe_load(fm_text) or {}
            except Exception:
                fm = {}
                
            if fm.get("draft", False):
                continue
                
            title = fm.get("title", "").strip()
            if not title:
                continue
                
            permalink, is_en, section_dir = get_rel_permalink(file_path)
            section_name = SECTION_NAMES.get(section_dir, section_dir)
            
            tags = fm.get("tags") or []
            if isinstance(tags, str):
                tags = [tags]
            tags = [str(t).strip() for t in tags if str(t).strip()]
            
            description = fm.get("description", "") or ""
            date_str = str(fm.get("date", ""))[:10]
            
            aliases = fm.get("aliases") or []
            if isinstance(aliases, str):
                aliases = [aliases]
                
            file_slug = file_path.stem
            
            articles[permalink] = {
                "id": permalink,
                "title": title,
                "url": permalink,
                "type": "article",
                "lang": "en" if is_en else "zh",
                "section": section_name,
                "sectionKey": section_dir,
                "tags": tags,
                "date": date_str,
                "description": description,
                "body": body_text,
                "charCount": len(body_text),
                "aliases": aliases,
                "filePath": str(file_path)
            }
            
            title_to_url[title.lower()] = permalink
            title_to_url[title] = permalink
            slug_to_url[file_slug.lower()] = permalink
            for alias in aliases:
                norm_alias = alias.strip().rstrip("/") + "/"
                slug_to_url[norm_alias.lower()] = permalink

    print(f"✓ 成功索引 {len(articles)} 篇有效文章")

    # 2. 建立关系链接矩阵与反向链接
    links = []
    link_pairs = set()
    backlinks_map = defaultdict(list)
    tag_counts = defaultdict(int)
    article_tags_map = {url: set(a["tags"]) for url, a in articles.items()}
    
    for url, art in articles.items():
        body = art["body"]
        found_targets = set()
        
        # A. 提取 Obsidian [[WikiLink]]
        wikilinks = re.findall(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', body)
        for wl in wikilinks:
            wl_clean = wl.strip()
            target_url = title_to_url.get(wl_clean.lower()) or slug_to_url.get(wl_clean.lower())
            if target_url and target_url != url:
                found_targets.add((target_url, "wikilink", wl_clean))

        # B. 提取标准 Markdown 内部链接 [text](/posts/...)
        md_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', body)
        for text, href in md_links:
            href_clean = href.split('#')[0].split('?')[0].strip()
            if not href_clean:
                continue
            if not href_clean.endswith('/'):
                href_clean += '/'
            target_url = None
            if href_clean in articles:
                target_url = href_clean
            else:
                for a_url in articles:
                    if href_clean.endswith(a_url) or a_url.endswith(href_clean):
                        target_url = a_url
                        break
            if target_url and target_url != url:
                found_targets.add((target_url, "link", text))

        # C. 记录链接与反链信息
        for target_url, link_type, anchor_text in found_targets:
            pair_key = (url, target_url)
            if pair_key not in link_pairs:
                link_pairs.add(pair_key)
                links.append({
                    "source": url,
                    "target": target_url,
                    "type": link_type,
                    "weight": 2.0
                })
                
                excerpt = extract_excerpt(body, anchor_text or articles[target_url]["title"])
                backlinks_map[target_url].append({
                    "sourceUrl": url,
                    "sourceTitle": art["title"],
                    "sourceSection": art["section"],
                    "sourceDate": art["date"],
                    "excerpt": excerpt,
                    "type": link_type
                })

        # D. 统计与关联标签
        for t in art["tags"]:
            tag_id = f"tag:{t}"
            tag_counts[t] += 1
            links.append({
                "source": url,
                "target": tag_id,
                "type": "tag-link",
                "weight": 0.8
            })

    # 3. 计算同频关联文章（Related Articles - 基于共现标签与同栏目推荐）
    related_map = defaultdict(list)
    for url, art in articles.items():
        my_tags = article_tags_map[url]
        candidates = []
        for other_url, other_art in articles.items():
            if other_url == url or other_art["lang"] != art["lang"]:
                continue
            shared_tags = my_tags & article_tags_map[other_url]
            score = len(shared_tags) * 3
            if other_art["sectionKey"] == art["sectionKey"]:
                score += 1
            if score > 0:
                candidates.append((score, other_url))
        
        candidates.sort(key=lambda x: x[0], reverse=True)
        top_related = [c[1] for c in candidates[:4]]
        for rel_url in top_related:
            rel_art = articles[rel_url]
            related_map[url].append({
                "url": rel_url,
                "title": rel_art["title"],
                "section": rel_art["section"],
                "date": rel_art["date"],
                "tags": rel_art["tags"][:3]
            })

    # 4. 构造节点列表（文章节点 + 标签星宿节点）
    nodes = []
    for url, art in articles.items():
        incoming_links = len(backlinks_map.get(url, []))
        outgoing_links = sum(1 for l in links if l["source"] == url and l["type"] != "tag-link")
        val = max(5, min(24, 6 + incoming_links * 3 + outgoing_links))
        
        nodes.append({
            "id": url,
            "title": art["title"],
            "url": url,
            "type": "article",
            "lang": art["lang"],
            "section": art["section"],
            "sectionKey": art["sectionKey"],
            "tags": art["tags"],
            "date": art["date"],
            "description": art["description"],
            "val": val,
            "incomingCount": incoming_links,
            "outgoingCount": outgoing_links
        })

    for tag_name, count in tag_counts.items():
        tag_id = f"tag:{tag_name}"
        nodes.append({
            "id": tag_id,
            "title": f"#{tag_name}",
            "type": "tag",
            "name": tag_name,
            "val": max(4, min(18, 4 + count * 1.5)),
            "count": count
        })

    print(f"✓ 拓扑计算完成：{len(nodes)} 个节点，{len(links)} 条连接线")
    print(f"✓ 反向链接映射：{len(backlinks_map)} 篇具有反链，{len(related_map)} 篇计算了同频关联")

    # 5. 输出标准化 JSON 文件
    graph_data = {
        "generatedAt": "2026-11-08",
        "stats": {
            "articlesCount": len(articles),
            "tagsCount": len(tag_counts),
            "nodesCount": len(nodes),
            "linksCount": len(links),
            "backlinksArticlesCount": len(backlinks_map)
        },
        "nodes": nodes,
        "links": links,
        "backlinks": dict(backlinks_map),
        "related": dict(related_map)
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 知识拓扑与反链数据已就绪：{OUTPUT_FILE}")

if __name__ == "__main__":
    main()
