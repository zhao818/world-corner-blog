# -*- coding: utf-8 -*-
"""《信任·伦理篇》封面:世界一隅品牌同款(深藏青 #1E1B4B + 金 #C8A03C + 宋体)

复用 gen_audiobook_covers.make_cover(长标题自动拆两行),生成 1080x1080 同款封面。
输出:scripts/covers/cover-lunli.jpg + static/audio/cover-lunli.jpg(听书页用)

用法:python gen_cover_lunli.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_audiobook_covers import make_cover

HERE = os.path.dirname(os.path.abspath(__file__))
COVERS = os.path.normpath(os.path.join(HERE, "..", "covers"))
AUDIO = os.path.normpath(os.path.join(HERE, "..", "..", "static", "audio"))

TITLE = "信任·伦理篇"
SUB = "伦理不是道德说教,是信任的水源"

if __name__ == "__main__":
    make_cover(TITLE, SUB, os.path.join(COVERS, "cover-lunli.jpg"))
    make_cover(TITLE, SUB, os.path.join(AUDIO, "cover-lunli.jpg"))
    print("两处封面已生成")
