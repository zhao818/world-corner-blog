---
title: "Git push GitHub SSL 握手失败"
date: 2026-06-13
draft: false
---


## 症状
> 你看到什么？

`git push` 到 GitHub 报错：`fatal: unable to access 'https://github.com/...': SSL connection error` 或 `TLS handshake failed`。每次 push 都失败，ping 不通 GitHub。

## 根因
> 真正的原因是什么？

Windows 环境下，Git 不会自动走系统代理（Clash/V2Ray）。之前只在单仓库设了 `http.proxy`，其他仓库和全局 `.gitconfig` 都没设，每次在新仓库 push 都重复踩坑。

## 修复
> 具体怎么修的？

```bash
git config --global http.proxy http://127.0.0.1:7897
git config --global https.proxy http://127.0.0.1:7897
```

设完立刻生效，所有仓库自动走代理。当前 Clash 代理端口是 7897，如果你的代理端口不同需要改。

## 怎么避免
> 下次怎么不踩？

- 新机器/新系统第一件事：跑上面两行命令
- 用 `git config --global --list | grep proxy` 确认已设
- 别用单仓库 `--local`，那是坑的根源
