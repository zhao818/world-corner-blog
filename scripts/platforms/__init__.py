# -*- coding: utf-8 -*-
"""平台注册表 — 所有平台模块在此注册"""
import sys, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(SCRIPT_DIR))

_registry = {}
REGISTRY = _registry

def register(platform):
    _registry[platform.name] = platform

def list_platforms():
    _ensure_loaded()
    return list(_registry.keys())

def publish_to(platform_name: str, meta: dict, body_md: str, cover_path: str = None) -> dict:
    _ensure_loaded()
    plat = _registry.get(platform_name)
    if not plat:
        return {"ok": False, "error": f"未知平台: {platform_name}，可用: {list(_registry.keys())}"}
    return plat.publish(meta, body_md, cover_path)

def publish_video_to(platform_name: str, filepath: str, title: str = "", desc: str = "", tags: list = None, cover_path: str = None) -> dict:
    _ensure_loaded()
    plat = _registry.get(platform_name)
    if not plat:
        return {"ok": False, "error": f"未知平台: {platform_name}，可用: {list(_registry.keys())}"}
    if hasattr(plat, "publish_video"):
        return plat.publish_video(filepath, title, desc, tags or [], cover_path=cover_path)
    meta = {"title": title, "digest": desc, "video_path": filepath, "tags": tags or []}
    return plat.publish(meta, "", cover_path)

def _ensure_loaded():
    if not _registry:
        import platforms.wechat
        import platforms.afdian
        import platforms.tencent_cloud
        import platforms.zhihu
        import platforms.juejin
        import platforms.bilibili
        import platforms.kuaishou
        import platforms.douyin
        import platforms.channels
        import platforms.xiaohongshu
        import platforms.goofish
        import platforms.jike