---
title: "Gitee 已配镜像还手动 push gitee，做了多余操作"
date: 2026-06-13
draft: false
---


## 症状
> 你看到什么？

每次 `git commit` 后都跑 `git push origin master && git push gitee master`，两条命令都成功。实际上 Gitee 那边早已配置了从 GitHub 自动镜像同步，push origin 之后 Gitee 会自动拉取。手动再 push gitee 不仅多余，还可能在极端情况下导致冲突。

更严重的是：`git remote` 里 gitee 的 URL 硬编码了 token（`Zhaotianbibg1:cfe33...@gitee.com`），每次 push 都明文传输。

## 根因
> 到底为什么出问题？

1. **不知道镜像已配**：Gitee 后台配了 GitHub → Gitee 镜像后，没有删掉本地的 gitee remote
2. **习惯性操作**：之前手动 push 两个 remote 形成习惯，没人提醒就一直做
3. **没有"查 remote 列表 → 确认是否冗余"的检查步骤**

## 修复
> 怎么做？

```bash
# 删掉 gitee remote（镜像自动同步，不需要手动 push）
git remote remove gitee

# 确认只剩下 origin
git remote -v
# origin  https://github.com/zhao818/claude-memory.git (fetch)
# origin  https://github.com/zhao818/claude-memory.git (push)
```

以后只推 GitHub：
```bash
git push origin master
# Gitee 自动从 GitHub 镜像，无需手动操作
```

## 怎么避免
> 下次怎么不踩？

1. **配了镜像就删 remote**：Gitee 后台配好镜像同步后，立刻 `git remote remove gitee`
2. **commit 前看 remote**：`git remote -v` 确认只有一个 origin，多出来的都是冗余
3. **绝对不把 token 放 remote URL**：如果必须保留多个 remote，用 SSH key 或 credential helper，不用 `https://user:token@host` 格式
4. **记住金句**：镜像自动同步 = 只需要 push 源头，目标不用管
