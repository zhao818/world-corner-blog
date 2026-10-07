---
title: "Hugo 手写单篇 HTML 跳过全量构建导致分类/列表页不更新"
date: 2026-06-13
draft: false
---


## 症状
> 你看到什么？

新文章 URL 可以正常访问（`/posts/xxx/` 能打开），但：
- 分类页看不到这篇文章
- 首页最新文章列表没有它
- 所有聚合/列表页都不知道这篇文章存在

用户从分类入口进来找不到文章，以为没发布。

## 根因
> 到底为什么出问题？

Hugo 是一个**全量静态站点生成器**——每篇文章的交叉引用、分类聚合、列表渲染，都需要 `hugo -d docs/` 重新计算。手写单篇 HTML 扔进 `docs/` 相当于绕过了整个生成引擎：

```
❌ 手写 HTML → docs/posts/xxx/index.html   ← 文章在，但分类/列表/首页从不更新
✅ hugo -d docs/                           ← 所有页面同步重建
```

**这个错误已经犯过至少 3 次**。

## 修复
> 怎么做？

```bash
# ✅ 唯一正确方式
hugo --minify -d docs/ -F   # -F = --buildFuture，确保未来日期文章也生成
git add docs/ content/
git commit -m "feat: <文章标题>"
git push
```

**绝不允许**：手写单篇 HTML 到 `docs/`、只复制个别文件、任何绕过 hugo 构建的操作。

## 怎么避免
> 下次怎么不踩？

1. **发布管线写死步骤**：step 2 永远是 `hugo --minify -d docs/ -F`，不跳过
2. **写 pre-commit hook**：检测 docs/ 下有新 HTML 但 content/ 无对应 markdown → 拒绝提交
3. **发布后验证**：检查首页和分类页确认新文章出现在列表中
4. **记住金句**：Hugo 不是 PHP——每篇文章的存在需要全站重新编译。看起来能访问 ≠ 发布成功。分类页/列表页/首页 都看到才算数
