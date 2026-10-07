---
title: "requests json= 参数导致公众号中文乱码"
date: 2026-06-13
draft: false
---


## 症状
> 你看到什么？

公众号推送文章草稿后，读者看到的中文全部变成 `我是` 这样的 Unicode 转义序列。微信后台预览正常，但推送后乱码。踩了 3 次才修好。

## 根因
> 真正的原因是什么？

`requests.post(url, json=data)` 内部调用 `json.dumps(data)` 时，默认参数 `ensure_ascii=True`，会把所有非 ASCII 字符转成 `\uXXXX`。微信服务器收到后原样展示，不会反转义。

**这不是微信的 bug，是 requests 的默认行为。**

```python
# requests 内部等价于：
body = json.dumps(data, ensure_ascii=True)  # 中文 → \uXXXX
# 发送给微信：{"content": "我是中文"}
# 微信原样展示：我是中文
```

## 修复
> 具体怎么修的？

```python
# ❌ 错误——中文变乱码
requests.post(url, json=data)

# ✅ 正确
import json
headers = {'Content-Type': 'application/json; charset=utf-8'}
requests.post(url, data=json.dumps(data, ensure_ascii=False).encode('utf-8'), headers=headers)
```

关键三步：
1. `ensure_ascii=False` — 中文保持原样
2. `.encode('utf-8')` — 转成字节
3. 手动设 `Content-Type: application/json; charset=utf-8` — 告诉服务器编码

## 怎么避免
> 下次怎么不踩？

- **铁律：调微信 API 时，永远不用 `json=` 参数**，手写 `data=json.dumps(..., ensure_ascii=False).encode('utf-8')`
- 其他中文 API 同理（公众号、企业微信、小程序）
- 如果非要用 `json=`，给 requests 打 monkey patch 设默认 `ensure_ascii=False`（不推荐）
