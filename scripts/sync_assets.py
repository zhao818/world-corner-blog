#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""项目资产 + 技能总表 → 世界一隅网站 自动同步脚本

来源:
  项目资产页(gen_assets_page.py 生成,读资产商城 assets.js)→  static/assets/index.html
  技能总表(gen_skills_page.py 生成)                       →  static/skills/index.html

步骤:生成 → git add → commit → push origin main → GitHub Actions 自动构建上线。
幂等:两页内容无变化时跳过提交,避免空 commit。
计划任务:Windows「KBSync-worldcorner」每周日 10:00 跑本脚本。
"""
import os
import shutil
import subprocess
import sys

BLOG = r"H:\world-corner-blog"
GEN_ASSETS = os.path.join(BLOG, "scripts", "gen_assets_page.py")
GEN_SKILLS = os.path.join(BLOG, "scripts", "gen_skills_page.py")

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


def gen_page(label, script):
    py = sys.executable or r"C:\Windows\py.exe"
    code, out = sh([py, script])
    if out:
        print(out)
    if code != 0:
        print("✗ %s 生成失败" % label)
    return code == 0


def main():
    ok = gen_page("项目资产页", GEN_ASSETS) and gen_page("技能总表", GEN_SKILLS)
    if not ok:
        print("同步失败,中止推送")
        return 1

    # 幂等:两页均无改动则跳过
    code, out = sh([GIT, "-C", BLOG, "status", "--porcelain", "--",
                    "static/assets/index.html", "static/skills/index.html"])
    if code != 0:
        print("git status 失败:", out)
        return 1
    if not out.strip():
        print("· 两页均无变化,跳过提交")
        return 0

    code, out = sh([GIT, "-C", BLOG, "add",
                    "static/assets/index.html", "static/skills/index.html"])
    if code != 0:
        print("git add 失败:", out)
        return 1
    code, out = sh([GIT, "-C", BLOG, "commit", "-m",
                    "sync: 项目资产 + 技能总表 自动同步"])
    if code != 0 and "nothing to commit" not in out:
        print("git commit 失败:", out)
        return 1
    print(out or "· commit 完成")

    # push 前先拉远端(Actions 会自动 commit docs/,不拉会 non-fast-forward)
    # 有 tracked 未暂存改动时先 stash,避免 rebase 被拒(untracked 不阻塞,不用管)
    code, dirty = sh([GIT, "-C", BLOG, "status", "--porcelain", "--untracked-files=no"])
    stashed = bool(dirty.strip())
    if stashed:
        code, out = sh([GIT, "-C", BLOG, "stash", "push", "-m", "sync-assets-tmp"])
        if code != 0:
            print("✗ git stash 失败:", out)
            return 1
    code, out = sh([GIT, "-C", BLOG, "pull", "--rebase", "origin", BRANCH])
    if code != 0:
        print("✗ git pull --rebase 失败:", out)
        if stashed:
            sh([GIT, "-C", BLOG, "stash", "pop"])
        return 1
    code, out = sh([GIT, "-C", BLOG, "push", "origin", BRANCH])
    print(out or "· push 完成")
    if code != 0:
        print("✗ git push 失败")
        if stashed:
            sh([GIT, "-C", BLOG, "stash", "pop"])
        return 1
    if stashed:
        code, out = sh([GIT, "-C", BLOG, "stash", "pop"])
        if code != 0:
            print("⚠ stash pop 冲突,请手动 git stash list 处理:", out)
            return 1
    print("✓ 已推送,GitHub Actions 自动构建,约 2 分钟后上线")
    return 0


if __name__ == "__main__":
    sys.exit(main())
