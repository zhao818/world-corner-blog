---
title: "Excel COM wb.Save() 静默失败，必须用 SaveAs"
date: 2026-06-13
draft: false
---


## 症状
> 你看到什么？

用 win32com 打开 Excel 文件，批量修改了几百个单元格的值和批注，调用 `wb.Save()` 后无任何报错。打开文件一看——所有修改都没了，文件还是原来的样子。

```python
# 跑了半小时的修复脚本...
for row in range(2, 500):
    ws.Cells(row, col).Value = fix_value
    ws.Cells(row, col).AddComment(f'原值: {old} → 修复: {fix}')

wb.Save()   # ← 静默失败，半小时白干
wb.Close()
```

## 根因
> 到底为什么出问题？

Excel COM 的 `Save()` 方法在以下情况下**静默失败**（不抛异常、不返回错误码）：

1. **文件来自只读目录**：微信聊天目录 `D:\xwechat_files\...` 下的文件，权限受限
2. **网络路径/UNC 路径**：`\server\share\file.xlsx`
3. **文件被其他进程打开**：Excel 自己或其他程序持有文件锁
4. **磁盘空间不足**：Save 写入失败但不报错

COM 接口的设计缺陷——`Save()` 不返回 HRESULT，异常被吞掉。

## 修复
> 具体步骤，能复制粘贴直接用。

```python
import os
import win32com.client

excel = win32com.client.Dispatch("Excel.Application")
excel.Visible = False
excel.DisplayAlerts = False

wb = excel.Workbooks.Open(src_path)
ws = wb.Worksheets(1)

# ... 做你的修改 ...

# ✅ 正确做法：SaveAs 到可写目录
output = os.path.expanduser('~') + r'\Desktop\output.xlsx'
wb.SaveAs(output, FileFormat=51)   # 51 = xlOpenXMLWorkbook (.xlsx)
wb.Close(SaveChanges=False)        # 已经 SaveAs 过了，不重复保存
excel.Quit()
```

**关键参数**：
- `FileFormat=51`：强制 .xlsx 格式（避免另存为 .xls 丢失批注）
- `SaveChanges=False`：已 SaveAs 过，Close 时不触发二次保存
- `DisplayAlerts=False`：禁止 Excel 弹"是否保存"对话框

## 怎么避免
> 下次怎么不踩？

1. **永远不用 `wb.Save()`**，所有保存走 `SaveAs()` + `Close(SaveChanges=False)`
2. **输出到可控目录**：Desktop / Temp / 项目目录，不要覆盖原文件（方便对比）
3. **保存后验证**：
   ```python
   # 马上读回验证
   import openpyxl
   check = openpyxl.load_workbook(output)
   assert check['Sheet1'].cell(2, col).value == fix_value, "SaveAs 失败！"
   ```
4. **WeChat 目录文件先复制**：`shutil.copy2(src, temp_dir)` 然后再操作
