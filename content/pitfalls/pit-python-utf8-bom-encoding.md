---
title: "Python encoding='utf-8' 不能自动处理 BOM"
date: 2026-06-13
draft: false
---


## 症状
> 你看到什么？

```python
with open("config.txt", encoding="utf-8") as f:
    for line in f:
        if line.startswith("GITEE_TOKEN="):  # ← 永远不匹配
            token = line.strip().split("=", 1)[1]
```

文件明明以 `GITEE_TOKEN=cfe33...` 开头，但 `startswith` 永远返回 False，令牌读不到。打了 `print(repr(line))` 才发现行首有 `﻿`。

## 根因
> 真正的原因是什么？

Windows 下某些工具（记事本、PowerShell `Out-File`、部分 IDE）保存 UTF-8 文件时会在文件头加 BOM（Byte Order Mark，`﻿`）。Python 的 `encoding='utf-8'` 不会自动跳过 BOM，它被当作第一个字符读进去。

## 修复
> 具体怎么修的？

```python
# ❌ 错误
with open("config.txt", encoding="utf-8") as f:

# ✅ 正确——自动跳过 BOM
with open("config.txt", encoding="utf-8-sig") as f:
```

一行之差，三天之坑。

## 怎么避免
> 下次怎么不踩？

- 读配置文件、.env、用户输入文件时，默认用 `utf-8-sig`
- 调试编码问题第一招：`print(repr(line))` 看原始字符
- 如果不想改 encoding，可以手动 `line.lstrip('﻿')`
