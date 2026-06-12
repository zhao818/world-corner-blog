# -*- coding: utf-8 -*-
"""生成《照见幸福》合集封面 → 桌面"""
import sys, os
import importlib.util

# 加载封面模板
spec = importlib.util.spec_from_file_location(
    "wct",
    os.path.expanduser("~/claude-memory/global/tools/wechat-cover-template.py")
)
wct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wct)

# WSL 字体路径
wct.FONT_PATH = "/mnt/c/Windows/Fonts/msyh.ttc"

# 桌面路径
desktop = "/mnt/c/Users/zhaot/Desktop"

# 生成合集封面
output = os.path.join(desktop, "照见幸福_合集封面.jpg")
wct.generate_cover(
    title="照见幸福",
    subtitle="文学中的心灵圆满之路",
    category="合 集",
    date="2026.06.13",
    output=output
)
print(f"✅ 合集封面已生成: {output}")
