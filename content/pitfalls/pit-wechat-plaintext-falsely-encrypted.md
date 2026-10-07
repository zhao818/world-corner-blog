---
title: "公众号明文模式下 nonce/timestamp 非空导致回复被错误加密"
date: 2026-06-13
draft: false
---


## 症状
> 你看到什么？

微信后台配置为「明文模式」。修复了 XML 二次包装后，日志无报错、AI 正常生成回复、`cached_xml` 有值——但用户手机端仍然看不到任何自动回复。表现和 XML 嵌套完全一样，给排查造成极大困扰。

## 根因
> 到底为什么出问题？

`_maybe_encrypt()` 函数不关心当前模式，只检查 `nonce` 和 `timestamp` 是否存在：

```python
def _maybe_encrypt(self, xml, nonce, timestamp):
    if xml and "<Encrypt>" not in xml and nonce and timestamp:
        return self.crypto.encrypt_message(xml, nonce, timestamp)
    return xml or "success"
```

**微信在明文模式下的 POST 请求 URL 中仍然携带 `nonce` 和 `timestamp` 参数**（用于 URL 签名验证，不是加解密），所以条件 `nonce and timestamp` 为真 → 执行加密 → 微信收到 `<Encrypt>` 标签的密文 → 明文模式下无法解析 → 静默丢弃 → 用户永远看不到回复。

## 修复
> 怎么做？

两层防护：

**第一层**：明文模式分支中置空 nonce/timestamp：
```python
if not msg_signature:
    logger.info("明文模式，直接解析消息。")
    msg = parse_message(data.decode("utf-8"))
    nonce = None       # ← 置空，跳过加密
    timestamp = None   # ← 置空，跳过加密
```

**第二层**：增加类级别 `_is_encrypted` 标志：
```python
# __init__ 中
self._is_encrypted: bool = True

# handle_callback 中
self._is_encrypted = bool(msg_signature)

# _maybe_encrypt 中
if xml and "<Encrypt>" not in xml and self._is_encrypted and nonce and timestamp:
    ...
# 任一个为 False 就跳过加密
```

## 怎么避免
> 下次怎么不踩？

1. **加密函数必须显式检查模式**：不能只靠 nonce/timestamp 是否存在——它们在明文模式下也存在
2. **写测试覆盖四种场景**：明文模式 / 安全模式 / 占位符 / 修复前复现
3. **三层防护设计**：类标志 + 参数置空 + 函数内多重检查，降低单一防护失效风险
4. **记住金句**：微信 URL 里的 `nonce` 和 `timestamp` 是签名用的，不是加密开关——不要用它们判断当前模式
