# -*- coding: utf-8 -*-
"""《信任本源论》封面:世界一隅品牌同款(深藏青 #1E1B4B + 金 #C8A03C + 宋体)

复用 gen_audiobook_covers.make_cover(长标题自动拆两行),生成 1080x1080 同款封面。
输出:scripts/covers/cover-benyuan.jpg + static/audio/cover-benyuan.jpg(听书页用)

用法:python gen_cover_benyuan.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_audiobook_covers import make_cover

HERE = os.path.dirname(os.path.abspath(__file__))
COVERS = os.path.normpath(os.path.join(HERE, "..", "covers"))
AUDIO = os.path.normpath(os.path.join(HERE, "..", "..", "static", "audio"))

TITLE = "信任本源论"
SUB = "信任不是道德,是生存底盘"

if __name__ == "__main__":
    make_cover(TITLE, SUB, os.path.join(COVERS, "cover-benyuan.jpg"))
    make_cover(TITLE, SUB, os.path.join(AUDIO, "cover-benyuan.jpg"))
    print("两处封面已生成")
