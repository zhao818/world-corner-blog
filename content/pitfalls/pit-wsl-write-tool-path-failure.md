---
title: "WSL 环境下 Claude Code Write 工具和 Bash 工具路径空间不一致"
date: 2026-06-13
draft: false
---


## 症状
> 你看到什么？

用 `Write` 工具写文件到 `~/claude-memory/pitfalls/xxx.md`（或用绝对路径 `/home/zhaotianbing/claude-memory/...`），工具报告成功，无报错。但 `ls ~/claude-memory/pitfalls/` 看不到新文件。

实际上本次会话就复现了：5 篇新踩坑用 Write 工具写完后，Bash 下全部找不到。最后用 Bash 重新写入才正确落盘。

## 根因
> 到底为什么出问题？

核心矛盾：**当前会话的 `$HOME` 是 `/c/Users/zhaot`（Windows 侧），但 `Write` 工具把 `/home/zhaotianbing/` 路径解析到了 WSL 原生 Linux 文件系统**。

```
Bash 工具：$HOME → /c/Users/zhaot → ~/claude-memory → /c/Users/zhaot/claude-memory ✅
Write 工具：/home/zhaotianbing/claude-memory → WSL 原生 FS → 文件孤立 ❌
```

两个工具的路径空间不一致 → Write 写入的位置和 Bash 读写的位置不同。Read 工具走了不同的解析路径所以能读到 Write 写的文件，但 Bash 看不到。

## 修复
> 怎么做？

在 WSL 环境创建文件时，用 `Bash` 的 cat heredoc 写入，不走 `Write` 工具：

```bash
cat > ~/claude-memory/pitfalls/new-file.md << 'EOF'
文件内容...
EOF
```

或者先确认 `$HOME` 的实际位置，再决定路径：
```bash
echo $HOME                    # 看当前是 /c/Users/zhaot 还是 /home/zhaotianbing
realpath ~/claude-memory      # 确认仓库实际位置
```

## 怎么避免
> 下次怎么不踩？

1. **WSL 项目优先 Bash 写入**：`cat > file << 'EOF'` 永远正确
2. **写后必验证**：Write/写操作后立刻 `ls` 确认文件出现
3. **不要假设路径**：`~` 可能指向 `/c/Users/zhaot` 而非 `/home/zhaotianbing`
4. **记住金句**：Write 说"成功"不代表文件在你以为的地方。WSL 有两个文件系统——Windows 侧和 Linux 侧——Write 和 Bash 各走各的路径解析。写完不验证 = 写了等于没写
