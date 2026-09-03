# -*- coding: utf-8 -*-
"""《信任·伦理篇·补遗》封面:世界一隅品牌同款(深藏青 #1E1B4B + 金 #C8A03C + 宋体)

复用 gen_audiobook_covers.make_cover(长标题自动拆两行),生成 1080x1080 同款封面。
输出:scripts/covers/cover-buyi.jpg + static/audio/cover-buyi.jpg(听书页用)

用法:python gen_cover_buyi.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_audiobook_covers import make_cover

HERE = os.path.dirname(os.path.abspath(__file__))
COVERS = os.path.normpath(os.path.join(HERE, "..", "covers"))
AUDIO = os.path.normpath(os.path.join(HERE, "..", "..", "static", "audio"))

TITLE = "信任·伦理篇·补遗"
SUB = "伦理总在迟到,社会总在重造它"

if __name__ == "__main__":
    make_cover(TITLE, SUB, os.path.join(COVERS, "cover-buyi.jpg"))
    make_cover(TITLE, SUB, os.path.join(AUDIO, "cover-buyi.jpg"))
    print("两处封面已生成")
