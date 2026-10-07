# -*- coding: utf-8 -*-
"""发布日志 — 防重复推送"""
import json, os
from datetime import datetime

LOG_PATH = os.path.expanduser("~/.claude/publish-log.json")

def _load():
    if os.path.exists(LOG_PATH):
        try:
            with open(LOG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return []

def _save(records):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

def record_publish(title: str, platform: str, pub_type: str = "article", url: str = ""):
    records = _load()
    records.append({
        "title": title,
        "platform": platform,
        "type": pub_type,
        "url": url,
        "date": datetime.now().isoformat(),
    })
    _save(records)

def check_duplicate(title: str, platform: str, days: int = 30):
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(days=days)
    for r in reversed(_load()):
        if r.get("platform") == platform and r.get("title") == title:
            try:
                if datetime.fromisoformat(r["date"]) > cutoff:
                    return r
            except: pass
    return None

def print_summary(days: int = 30):
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(days=days)
    records = [r for r in _load() if datetime.fromisoformat(r["date"]) > cutoff]
    if not records:
        print(f"最近{days}天无发布记录")
        return
    for r in records[-20:]:
        print(f"  [{r['platform']}] {r['title'][:30]} ({r['date'][:10]})")