---
title: "Gitee 建仓库前没查已有仓库，建了重复仓库"
date: 2026-06-13
draft: false
---


## 症状
> 你看到什么？

踩坑共享平台需要 Gitee 镜像。在 Gitee 上新建了 `pitfall-knowledge-base` 仓库，配置了 GitHub → Gitee 镜像同步。后来发现用户早就有 `claude-memory` 仓库，功能完全重叠——`claude-memory` 本身就是踩坑知识库。

结果：
- 多了一个无用仓库，要手动删除
- 镜像同步配置白做了
- 概念混乱：哪个仓库才是真的？

## 根因
> 到底为什么出问题？

1. **不查就建**：建仓库前没跑 `gh repo list zhao818` 或登录 Gitee 看已有仓库
2. **命名冲动**：想了一个"好听的名字"就建了，没考虑是否和已有仓库功能重叠
3. **平台不统一**：GitHub 一个名、Gitee 一个名，镜像对不齐
4. **没有"先确认再行动"的肌肉记忆**：对平台操作的敬畏不够

## 修复
> 具体步骤。

```bash
# 1. 先查 GitHub 上已有的仓库
gh repo list zhao818 --limit 50

# 2. 再查 Gitee 上已有的仓库
# 浏览器打开 https://gitee.com/Zhaotianbibg1 → 看仓库列表

# 3. 确认没有同名/同功能仓库后，再建
# GitHub → Settings → Developer settings → Personal access tokens
# Gitee → 设置 → 私人令牌

# 4. 名称对齐：GitHub 和 Gitee 用同一个仓库名
# GitHub: zhao818/claude-memory
# Gitee:  Zhaotianbibg1/claude-memory  ← 对齐
```

删除多余仓库后，重新配置镜像：
```bash
# Gitee 仓库设置 → 镜像仓库管理 → 添加镜像
# 源: https://github.com/zhao818/claude-memory.git
# 目标: https://gitee.com/Zhaotianbibg1/claude-memory.git
```

## 怎么避免
> 下次怎么不踩？

1. **建仓库前三问**：
   - 这个仓库解决什么问题？（一句话）
   - 已有仓库有没有已经解决这个问题的？（查列表）
   - 能不能合并到已有仓库而不是新建？（优先合并）
2. **命名对齐**：GitHub 和 Gitee 的仓库名必须一致（否则镜像对不上）
3. **查完整列表**：`gh repo list` + 浏览器确认，两边的仓库都要看
4. **先规划后建仓**：写下来「仓库名 + 用途 + 镜像关系」，确认无误再动手
