# -*- coding: utf-8 -*-
"""掘金发布 — API + Cookie"""
from .base import BasePlatform, get_platform_cookies

class JuejinPlatform(BasePlatform):
    name = "juejin"
    display_name = "掘金"
    def publish(self, meta, body, cover_path=None):
        return self.error("掘金模块待实现")

from platforms import register
register(JuejinPlatform())