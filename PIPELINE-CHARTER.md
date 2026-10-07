# 📋 内容管线 · 项目宪章 & 行动计划

> **品牌**: 美好需要创造 | **定位**: AI提效实战派 + 融合框架
> **版本**: 2026-07-03 | **文件**: `~/world-corner-blog/PIPELINE-CHARTER.md`

---

## 一、核心理念（做什么 & 不做什么）

### 品牌锚点
```
品牌: 美好需要创造（公众号/爱发电/闲鱼）/ 世界一隅（博客/哲思线）
定位: AI提效实战派 —— 讲人话、给干货、可实操
内容线:
  ├── AI提效线 (--track ai)     → 工具/编程/效率方法
  ├── 哲思线 (--track thinking) → 深度思考/反共识
  └── 产品线                    → 付费文章/钩子产品
发布节奏: 每天1-2篇（上午/晚上）
```

### 铁律（不改）
1. **先计划后执行** — 任何 ≥3 步的工作，先写计划再动手
2. **PipelineTracker** — ≥3 步管线自动可视化
3. **单向数据流** — 搜索→生成→发布→追踪→变现，不绕路
4. **平台模块化** — 加新平台只加 platforms/ 文件，不动核心
5. **技能封装** — 重复 4 次的操作自动封成技能

---

## 二、管线总览（全景图）

```
  ① 输入层         ② 生产层          ③ 分发层           ④ 视频层             ⑤ 追踪层          ⑥ 变现&运营
  ┌────────┐      ┌────────┐       ┌────────┐        ┌────────┐          ┌────────┐        ┌────────┐
  │ 搜索引擎 │──▶  │ 文章生成 │──▶  │ 多平台 │──▶    │ 视频生成 │──▶      │ 数据   │──▶    │ 商业   │
  │ 6种引擎 │      │ 4条管线 │      │ 11平台 │        │ 上传服务 │          │ 仪表盘 │        │ 引流   │
  └────────┘      └────────┘       └────────┘        └────────┘          └────────┘        └────────┘
```

### 每阶段的核心入口

| 阶段 | 首选入口 | 场景 | 备用入口 |
|------|---------|------|---------|
| ① 搜索 | `yuanbao_search.py` | 联网查资料 | `deepseek_web.py` |
| ② 文章 | `publish_one.py` | 快速发一篇公众号 | `content_orchestrator.py`（深度） |
| ③ 发布 | `publish.py` | 同步多发几个平台 | 各平台独立脚本 |
| ④ 视频 | `video_pipeline.py` | 文章转短视频 | `upload-video.py`（仅上传） |
| ⑤ 追踪 | `content_dashboard.py serve` | 看发布状态 | `collect_video_stats.py` |
| ⑥ 变现 | `commerce_pipeline.py` | 产品/CRM/引流 | 各 commerce 子模块 |

---

## 三、文件状态评估（稳定/待优化/可废弃）

### 🟢 稳定（不动或少动）

| 文件 | 状态 | 备注 |
|------|------|------|
| `publish_one.py` | ✅ 稳定 | V2已修复JSON解析，日常发文够用 |
| `publish.py` | ✅ 稳定 | 多平台分发，策略模式架构好 |
| `platforms/*.py` | ✅ 稳定 | 11平台模块，加新平台才动 |
| `content_registry.json` | ✅ 稳定 | 统一注册表，数据格式已定 |
| `deepseek_web.py` | ✅ 稳定 | 反检测三层到位，storage_state持久化 |
| `traffic.py` | ✅ 稳定 | 统一引流文案，架构清晰 |

### 🟡 待优化（已知问题，排期修）

| 文件 | 问题 | 优化方向 | 难度 |
|------|------|---------|------|
| `publish_one.py` | 无重试机制、无质量审核 | 指数退避 + 五维评分自动闸门 | 低 |
| `content_orchestrator.py` | 无缓存、Token消耗大 | LRU Cache + 多Agent并行投票 | 中 |
| `video_pipeline.py` | 25秒固定时长、单音色 | 自适应时长 + 多TTS引擎 | 中 |
| `zhihu_answer.py` | 36KB耦合度高 | 拆4模块(fetcher/retriever/gen/publisher) | 中 |
| `content_dashboard.py` | JSON无并发保护 | 迁移SQLite | 低 |
| `publish.py` | 缺发布后验证 | 截图验证 | 中 |
| `upload-video.py` | 仅3平台 | 扩到小红书/视频号 | 低 |

### 🔴 观察中（不确定是否保留）

| 文件 | 问题 | 建议 |
|------|------|------|
| `catalog/scripts/` 目录副本 | blog/scripts/ 和 catalog/scripts/ 有很多重复文件 | **合并到 blog/scripts/，catalog/ 只留 content_orchestrator.py 和搜索引擎** |
| `videofast_server.py` | 单机Flask，订单量未知 | 观察是否真有订单，无则归档 |
| `MoneyPrinterPlus` 项目 | 另一个独立视频项目，与Remotion管线并行 | 确定保留哪个视频方案 |
| `publish_llm_article.py` | 功能被 publish_one.py 覆盖 | 可标记为 deprecated |
| `_debug_wechat.py` | 一次性调试脚本 | 可删除 |

---

## 四、规划路线图

### 第一阶段：立即做（本周）
```
[ ] 统一脚本目录 — catalog/scripts/ 重复脚本只保留 blog/scripts/
[ ] publish_one.py 加入指数退避重试
[ ] publish_one.py 接入 content_eval.py 审核闸门
[ ] publish.py 加入发布后截图验证
```

### 第二阶段：短期（本月）
```
[ ] content_orchestrator 加入 LRU Cache
[ ] video_pipeline 自适应时长
[ ] zhihu_answer.py 拆模块
[ ] content_dashboard.py 迁移 SQLite
```

### 第三阶段：中长期（季度）
```
[ ] 三AI并行独立产出→交叉评审→择优
[ ] CI/CD 管线自动化测试
[ ] 端到端内容发布测试套件
[ ] 统一 API 网关替代散装脚本
```

## 五、执行记录

| 日期 | 任务 | 产出 |
|------|------|------|
| 2026-07-03 | 管线宪章+流程图创建 | PIPELINE-CHARTER.md / pipeline-flow.html / pipeline-map.html |
| 2026-07-03 | Cursor写代码狠活 视频生成+配音校准 | out/cursor写代码狠活.mp4 (25s 2.2MB) |
| 2026-07-03 | Cursor写代码狠活 图文分发 | 掘金✅ 知乎✅ 即刻✅ |
| 2026-07-03 | Cursor写代码狠活 视频分发 | 抖音✅ 快手✅ B站✅ 视频号✅ 小红书⏳(封号) |
| 2026-07-03 | traffic.py 去敏感词 | 6类型 video_description/video_cta 全面清理 |
| 2026-07-03 | publish.py 加 --tencent --afdian 参数 | 腾讯云+爱发电 CLI支持 |
| 2026-07-03 | 追踪层自动化 | 发布后自动静默采集数据 |

> **下次开工建议**: 从选题→写文章→视频→全平台发布完整跑一遍，同步推进路线图优化项

---

## 六、行动计划模板（每次开工前填）

```markdown
## 🎯 本次目标
_一句话说明这次要做什么_

## 📋 执行步骤
- [ ] 步骤 1: _做什么 / 哪个脚本_
- [ ] 步骤 2: _...
- [ ] 步骤 3: _...

## 📁 涉及文件
_列出本次会改/读的文件_

## 🚨 风险
_可能会出问题的地方 / 需要备份的_

## ✅ 完成标准
_做完后怎么判断「搞定了」_

## 💡 参考
_宪章中的哪条原则 / 哪个优化方向_
```

---

## 六、快速决策树

```
想做什么？                          → 先读             → 再用
─────────────────────────────────────────────────────────────
快速发一篇公众号                     → publish_one.py    → python publish_one.py
深度写文章                           → content_orch.py   → python content_orch.py --full
多发几个平台                         → publish.py        → python publish.py article.md
做一个视频                           → video_pipeline.py → python video_pipeline.py --auto
查发布状态                           → content_dashboard → python content_dashboard.py serve
搜资料                               → yuanbao_search.py → python yuanbao_search.py -r "问题"
做知乎引流                           → zhihu_answer.py   → python zhihu_answer.py --auto
看商业状态                           → commerce_pipeline → python commerce_pipeline.py --status
```

---

> **使用方式**：
> 1. 每次开工前，先把**宪章第四节的路线图**看一遍，确定今天做哪个方向
> 2. 用**第五节模板**写行动计划
> 3. 执行中遇到困惑，回来看**第一节核心理念**和**第二节全景图**
> 4. 做完更新宪章的**文件状态评估**
