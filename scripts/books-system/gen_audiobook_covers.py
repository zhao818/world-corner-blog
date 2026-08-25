#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""有声书统一封面生成器(世界一隅品牌同款:深藏青 #1E1B4B + 金 #C8A03C + 宋体)
两本书统一 1080x1080,消除新旧封面比例不一致问题(旧:1024x1024 / 900x383)
用法:python gen_audiobook_covers.py
输出:../covers/cover-happiness.jpg, ../covers/cover-mind-practice.jpg
"""
from PIL import Image, ImageDraw, ImageFont
import os

BG = (30, 27, 74)          # #1E1B4B 深藏青
GOLD = (200, 160, 60)      # #C8A03C
GOLD_LIGHT = (221, 161, 94)  # #DDA15E 星色
TEXT = (242, 240, 246)     # 白
GRAY = (168, 160, 188)     # 灰紫

SIMSUN = "C:/Windows/Fonts/simsun.ttc"   # 宋体(og-cover 同款)
LIGHT = (206, 202, 224)   # 提亮灰,顶部 kicker / 网址用

W = H = 1080
CX = 540
MK_CX, MK_CY = CX, 268    # mark 圆心
MK_R = 148                # 金环半径


def font(size):
    try:
        return ImageFont.truetype(SIMSUN, size)
    except Exception:
        return ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", size)


def draw_mark(d):
    """位于 (48,48) 的 mark.svg,缩放 3.75 倍到 1080 图"""
    d.ellipse([MK_CX - MK_R, MK_CY - MK_R, MK_CX + MK_R, MK_CY + MK_R],
              outline=GOLD, width=15)
    # 四角菱形星(中心 (58,38) 相对圆心偏移 (10,-10))
    sx, sy = MK_CX + 10 * 3.75, MK_CY - 10 * 3.75
    r = 45
    star = [(sx, sy - r), (sx + r, sy), (sx, sy + r), (sx - r, sy)]
    d.polygon(star, fill=GOLD_LIGHT)
    # 左下弧线(98°->150°)
    d.arc([MK_CX - 127.5, MK_CY - 127.5, MK_CX + 127.5, MK_CY + 127.5],
          start=98, end=150, fill=GOLD, width=9)


def draw_sig(d):
    """底部签名:左侧金线 + 右侧签名(按字体基线对齐两行)"""
    d.line([(90, H - 88), (330, H - 88)], fill=GOLD, width=2)
    f_sig = font(30)
    a1, _ = f_sig.getmetrics()
    d.text((352, H - 96 - a1), "世界一隅", fill=GOLD, font=f_sig)
    f_en = font(22)
    a2, _ = f_en.getmetrics()
    d.text((352, H - 96 - a2), "worldcorner.xyz", fill=LIGHT, font=f_en)


def make_cover(title, subtitle, output):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # 顶部 kicker
    f_kick = font(34)
    kick = "WORLD CORNER · 有声书"
    bb = d.textbbox((0, 0), kick, font=f_kick)
    d.text((CX - (bb[2] - bb[0]) // 2, 84), kick, fill=LIGHT, font=f_kick)

    draw_mark(d)

    # 金线
    d.line([(CX - 110, 470), (CX + 110, 470)], fill=GOLD, width=3)

    # 主标题(书名)
    f_title = font(164)
    bb = d.textbbox((0, 0), title, font=f_title)
    d.text((CX - (bb[2] - bb[0]) // 2, 512 - bb[1]), title, fill=TEXT, font=f_title)

    # 副题
    f_sub = font(48)
    bb = d.textbbox((0, 0), subtitle, font=f_sub)
    d.text((CX - (bb[2] - bb[0]) // 2, 700), subtitle, fill=GOLD, font=f_sub)

    draw_sig(d)

    os.makedirs(os.path.dirname(output), exist_ok=True)
    img.save(output, "JPEG", quality=94)
    print("OK", output, img.size)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "covers")
    make_cover("幸福的内在", "31 篇散文小辑 · 完整连播",
               os.path.join(out, "cover-happiness.jpg"))
    make_cover("内心的修炼", "九关修炼体系 · 8 小时连播",
               os.path.join(out, "cover-mind-practice.jpg"))
