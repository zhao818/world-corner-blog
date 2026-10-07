---
title: "Python 缩进错位导致 140 行被动回复代码完全跳过"
date: 2026-06-13
draft: false
---


## 症状
> 你看到什么？

AstrBot 微信公众号适配器中，被动回复模式（`active_send_mode=False`）完全不工作：
- 用户发消息到公众号 → 无任何回复
- 日志报 `TypeError: The response value returned by the view function cannot be None`
- 调试器中 AI 回复正常，部署后就是不行
- 检查了所有逻辑，没发现问题——代码"看起来"都在

```python
# handle_callback 方法的末尾
if self.active_send_mode:
    result_xml = await self.callback(msg)
    if not result_xml:
        return "success"
    ...

    # 以下 140 行被动回复代码...
    from_user = str(getattr(msg, "source", ""))
    to_user = str(getattr(msg, "target", ""))
    # ... 100+ 行逻辑 ...
    return reply_xml

# ← handle_callback 结束，但没有任何 return
```

## 根因
> 到底为什么出问题？

140 行被动回复代码的缩进是 **12 个空格**，对应 3 级缩进（4+4+4），错误地放在了 `if self.active_send_mode:` 块**内部**。

当 `active_send_mode=False`（被动回复模式）时：
1. `if self.active_send_mode:` 条件为 False
2. 整个 if 块被跳过
3. 140 行被动回复逻辑完全不执行
4. `handle_callback` 没有任何 return 语句
5. Flask/Quart 报 `TypeError: ... cannot be None`

**为什么调试器里正常？** 调试环境 `active_send_mode=True`，代码执行了。但生产环境是 `False`——这是一个**环境敏感的缩进 Bug**。

## 修复
> 怎么做？

```python
# 修复前 - 被动回复在 if 块内（12空格 = 3级缩进）
if self.active_send_mode:
    result_xml = await self.callback(msg)
    ...
    # passive reply ← 12空格缩进，在 if 块内！

# 修复后 - 被动回复与 if 同级（4空格 = 方法体顶层）
if self.active_send_mode:
    result_xml = await self.callback(msg)
    ...

# passive reply ← 4空格缩进，在方法体顶层
from_user = str(getattr(msg, "source", ""))
...
return reply_xml
```

**检查工具**：
```bash
# 检查缩进不一致
python -m tabnanny -v your_file.py

# pylint 检查缩进
pylint --disable=all --enable=W0311 your_file.py
```

## 怎么避免
> 下次怎么不踩？

1. **VSCode 缩进参考线**：Settings → Editor → Guides → Indentation: true，任何缩进异常一眼可见
2. **关键逻辑不藏深处**：如果一段逻辑是方法的"主流程"，它不应该在 if 块里
3. **return 语句检查**：每个 HTTP handler / 回调方法，确认**所有分支都有 return**
4. **多环境测试**：修改环境敏感的代码后，在两种模式下都跑一遍（`active_send_mode=True` + `False`）
5. **用 tabnanny CI 检查**：在 pre-commit hook 里加 `python -m tabnanny`，混合 tab/空格直接拒绝
