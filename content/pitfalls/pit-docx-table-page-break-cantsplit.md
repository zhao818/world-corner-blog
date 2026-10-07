---
title: "python-docx 表格跨页断开无法控制"
date: 2026-06-13
draft: false
---


## 症状
> 你看到什么？

用 python-docx 生成的报告，表格在页面底部被 Word 自动劈成两半——表头在上页，数据在下页。读者看到断裂的表格，专业性大打折扣。手动在 Word 里调整也调不好。

## 根因
> 真正的原因是什么？

python-docx 创建的表格行，默认没有设置 `<w:cantSplit/>` 属性。Word 打开文档后，按自己的分页算法决定是否断开表格——如果表格行正好落在页面底部，Word 就会把它断开。

**这是 python-docx 的默认行为缺陷，不是 Word 的问题。**

## 修复
> 具体怎么修的？

```python
from docx import Document
from docx.oxml.ns import qn

doc = Document()
table = doc.add_table(rows=5, cols=3)

# 关键：给每一行设 cantSplit，禁止跨页断开
for row in table.rows:
    tr = row._tr
    trPr = tr.get_or_add_trPr()
    cant_split = OxmlElement('w:cantSplit')
    trPr.append(cant_split)

doc.save('output.docx')
```

这样生成的表格不会在页面中间断开，Word 会把整行推到下一页。

## 怎么避免
> 下次怎么不踩？

- 生成 docx 表格时，所有行显式设 `cantSplit`
- 目录（TOC）不要手动写，用 Word 域代码 `TOC \o "1-3"` 生成
- 参考 `~/claude-memory/global/tools/docx-patterns.md` 的完整模式
