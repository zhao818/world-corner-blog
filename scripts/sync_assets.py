#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知识库 + 技能总表 → 世界一隅网站 自动同步脚本

来源:
  I:/灵魂之觅/docs/知识库/index.html  →  static/kb/index.html    (替换 title 为站点品牌)
  技能总表(gen_skills_page.py 生成)   →  static/skills/index.html

步骤:复制/生成 → git add → commit → push origin main → GitHub Actions 自动构建上线。
幂等:两页内容无变化时跳过提交,避免空 commit。
计划任务:Windows「KBSync-worldcorner」每周日 10:00 跑本脚本(与 KBIndex-灵魂之觅 9:30 错开)。
"""
import io
import os
import re
import shutil
import subprocess
import sys

BLOG = r"H:\world-corner-blog"
KB_SRC = r"I:\灵魂之觅\docs\知识库\index.html"
KB_DST = os.path.join(BLOG, "static", "kb", "index.html")
GEN_SKILLS = os.path.join(BLOG, "scripts", "gen_skills_page.py")

TITLE = "世界一隅 · 知识库"
BRANCH = "main"


def find_git():
    """定位 git:优先常见安装路径,shutil.which 兜底"""
    candidates = [
        os.environ.get("GIT_EXE", ""),
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files (x86)\Git\cmd\git.exe",
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    hit = shutil.which("git")
    if hit:
        return hit
    return "git"


GIT = find_git()


def sh(args, cwd=None):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "").strip() + ("\n" + (p.stderr or "").strip()).rstrip()


def sync_kb():
    """复制知识库检索树,替换 <title> 为站点品牌标题"""
    if not os.path.isfile(KB_SRC):
        print("✗ 知识库源不存在:", KB_SRC)
        return False
    text = io.open(KB_SRC, encoding="utf-8").read()
    new = re.sub(r"<title>.*?</title>", "<title>%s</title>" % TITLE, text, count=1)
    os.makedirs(os.path.dirname(KB_DST), exist_ok=True)
    io.open(KB_DST, "w", encoding="utf-8").write(new)
    print("→ static/kb/index.html 已同步(%d 字节)" % len(new.encode("utf-8")))
    return True


def sync_skills():
    """调 gen_skills_page.py 生成技能总表页"""
    py = sys.executable or r"C:\Windows\py.exe"
    code, out = sh([py, GEN_SKILLS])
    if out:
        print(out)
    return code == 0


def main():
    ok = sync_kb() and sync_skills()
    if not ok:
        print("同步失败,中止推送")
        return 1

    # 幂等:两页均无改动则跳过
    code, out = sh([GIT, "-C", BLOG, "status", "--porcelain", "--",
                    "static/kb/index.html", "static/skills/index.html"])
    if code != 0:
        print("git status 失败:", out)
        return 1
    if not out.strip():
        print("· 两页均无变化,跳过提交")
        return 0

    code, out = sh([GIT, "-C", BLOG, "add",
                    "static/kb/index.html", "static/skills/index.html"])
    if code != 0:
        print("git add 失败:", out)
        return 1
    code, out = sh([GIT, "-C", BLOG, "commit", "-m",
                    "sync: 知识库检索树 + 技能总表 自动同步"])
    if code != 0 and "nothing to commit" not in out:
        print("git commit 失败:", out)
        return 1
    print(out or "· commit 完成")

    branch, _ = sh([GIT, "-C", BLOG, "branch", "--show-current"])
    if branch != BRANCH:
        print("✗ 当前分支 %s 非 %s,跳过推送" % (branch or "?", BRANCH))
        return 1
    code, out = sh([GIT, "-C", BLOG, "push", "origin", BRANCH])
    print(out or "· push 完成")
    if code != 0:
        print("✗ git push 失败")
        return 1
    print("✓ 已推送,GitHub Actions 自动构建,约 2 分钟后上线")
    return 0


if __name__ == "__main__":
    sys.exit(main())
