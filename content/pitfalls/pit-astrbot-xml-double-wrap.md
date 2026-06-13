---
title: "AstrBot 公众号被动回复 XML 二次包装导致微信无法解析"
date: 2026-06-13
draft: false
---


## 症状
> 你看到什么？

AstrBot 微信公众号被动回复模式：AI 正常生成回复，日志显示 `wx buffer hit on trigger` 和 `wx first window timeout` 正常打印，`cached_xml` 里有值。但用户手机端**永远看不到回复**。无任何报错日志——微信静默丢弃了回复。

## 根因
> 到底为什么出问题？

`callback` 函数把 AI 结果用 `create_reply()` 转成**完整 XML** 存入 `cached_xml`：

```python
# callback 函数中
reply_xml = str(create_reply(result, msg))
state["cached_xml"].append(reply_xml)
```

存储的内容已经是完整 XML：
```xml
<xml>
<ToUserName><![CDATA[ofqGA2NNjQOqZL3snP_mzNQrGQLM]]></ToUserName>
<FromUserName><![CDATA[gh_bd189357a403]]></FromUserName>
<Content><![CDATA[你好，我是AI助手]]></Content>
</xml>
```

但 `handle_callback` 从 `cached_xml` 取出后，又用 `_reply_text()` **再包装一次**：
```python
def _reply_text(text: str) -> str:
    reply_obj = create_reply(text, msg)  # 把完整 XML 当作文本再包装
    ...
```

微信收到嵌套 XML → 无法解析 → 静默丢弃。

## 修复
> 怎么做？

所有从 `cached_xml` 取出的分支**不调用 `_reply_text()`**，直接用 `_maybe_encrypt()` 返回原生 XML。涉及 3 个分支：

- `wx buffer hit on trigger`
- `wx buffer hit on retry window`
- `wx buffer hit immediately`

```python
# ❌ 修复前：二次包装
cached_xml = state["cached_xml"].popleft()
return self._reply_text(cached_xml)  # 又包一层！

# ✅ 修复后：直接返回
cached_xml = state["cached_xml"].popleft()
return self._maybe_encrypt(cached_xml, nonce, timestamp)  # 原样返回
```

## 怎么避免
> 下次怎么不踩？

1. **缓存 XML 时标记包装状态**：存的时候标注 `is_wrapped=True`，取的时候检查
2. **包装函数加幂等保护**：`create_reply()` 检测输入是否已包含 `<xml>` 标签，拒绝二次包装
3. **写测试验证端到端**：mock 微信回调 → 缓存回复 → 取出返回，验证 XML 不嵌套
4. **记住金句**：`create_reply` 的输出是最终态——存了就原样取，不要再过任何"包装"函数
