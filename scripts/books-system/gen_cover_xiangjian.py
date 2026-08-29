# -*- coding: utf-8 -*-
"""《走向田间》封面:世界一隅品牌同款(深藏青 #1E1B4B + 金 #C8A03C + 宋体)

复用 gen_audiobook_covers.make_cover,生成 1080x1080 同款封面。
输出:scripts/covers/cover-xiangjian.jpg(epub 用) + static/audio/cover-xiangjian.jpg(听书页用)

用法:python gen_cover_xiangjian.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_audiobook_covers import make_cover

HERE = os.path.dirname(os.path.abspath(__file__))
COVERS = os.path.normpath(os.path.join(HERE, "..", "covers"))
AUDIO = os.path.normpath(os.path.join(HERE, "..", "..", "static", "audio"))

TITLE = "走向田间"
SUB = "把目光从收割，转回喂养"

if __name__ == "__main__":
    make_cover(TITLE, SUB, os.path.join(COVERS, "cover-xiangjian.jpg"))
    make_cover(TITLE, SUB, os.path.join(AUDIO, "cover-xiangjian.jpg"))
    print("两处封面已生成")
