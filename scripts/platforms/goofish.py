# -*- coding: utf-8 -*-
"""闲鱼发布 — Playwright"""
from .base import BasePlatform, get_platform_cookies

class GoofishPlatform(BasePlatform):
    name = "goofish"
    display_name = "闲鱼"
    def publish(self, meta, body, cover_path=None):
        return self.error("闲鱼模块待实现")

from platforms import register
register(GoofishPlatform())