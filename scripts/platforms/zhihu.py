# -*- coding: utf-8 -*-
"""知乎发布 — Playwright反检测"""
from .base import BasePlatform, get_platform_cookies

class ZhihuPlatform(BasePlatform):
    name = "zhihu"
    display_name = "知乎"
    def publish(self, meta, body, cover_path=None):
        return self.error("知乎模块待实现")

from platforms import register
register(ZhihuPlatform())