# 📦 内容运营管线全景框架图

> **版本**: 2026-07-03 | **品牌**: 美好需要创造 | **定位**: AI提效实战派 + 融合框架
> **目录**: `~/world-corner-blog/` 生产管线 | `~/catalog/` 深度创作 | `~/.claude/skills/` 技能封装

---

## 一、总览架构（思维导图）

```
                    ┌──────────────────────────────────────────────────────────────┐
                    │                   用户（你）                                  │
                    └──────────┬───────────────────────────────────┬──────────────┘
                               │                                   │
                    ┌──────────▼──────────┐           ┌────────────▼────────────┐
                    │  快速发文？          │           │  深度写文章？             │
                    │  wechat-publish     │           │  content-orchestrator    │
                    │  publish_one.py     │           │  content_orchestrator.py │
                    │  (5步→公众号)       │           │  (7步→含审核闸门)         │
                    └──────────┬──────────┘           └────────────┬────────────┘
                               │                                   │
                               └──────────┬───────────────────────┘
                                          │
                          ┌───────────────▼────────────────┐
                          │       publihs.py                │
                          │   (多平台分发布引擎)              │
                          │   公众号/掘金/B站/知乎/即刻等     │
                          └───────────────┬────────────────┘
                                          │
                          ┌───────────────▼────────────────┐
                          │      video-pipeline             │
                          │  video_pipeline.py (6步→MP4)   │
                          └───────────────┬────────────────┘
                                          │
                          ┌───────────────▼────────────────┐
                          │        成品 + 登记               │
                          │  content_registry.json          │
                          │  content_dashboard.py (看板)    │
                          └────────────────────────────────┘
```

---

## 二、核心管线（三大技能 + 管线入口）

### 📌 入口映射表

```
技能名称              → 脚本                           → 做什么
─────────────────────────────────────────────────────────────────
wechat-publish       → publish_one.py                 → 快速：AI选题→DeepSeek→起草→发公众号
content-orchestrator → catalog/scripts/content_orchestrator.py → 深度：三AI协作→审核→发布→视频
video-pipeline       → projects/remotion-video-platform → 视频：Hook→素材→TTS→渲染→登记
```

### ① wechat-publish — 公众号一键发文

| 步骤 | 功能 | 脚本/文件 | 迭代记录 |
|------|------|-----------|----------|
| 0/5 | **AI自动选题** | `publish_one.py` | 可传参数手动指定选题 |
| 1/5 | **DeepSeek搜索** | `deepseek_web.py` | Playwright + storage_state 持久化登录 |
| 2/5 | **JSON起草** | `publish_one.py` | V2修复: JSON解析增强，自动剥离代码块 |
| 3/5 | **公众号推送** | `platforms/wechat.py` | WechatPlatform 类 |
| 4/5 | **内容登记** | `content_registry.json` | V2: 改用RegistryManager，统一格式+去重 |

### ② content-orchestrator — 三AI协作深度写文章

| 步骤 | 功能 | 脚本 | 引擎 | 说明 |
|------|------|------|------|------|
| Step 1 | **选题调研** | `multi_search()` | 豆包→Gemini→DeepSeek 自动降级 | 自动选第一个成功引擎 |
| Step 2 | **骨架生成** | `content_orchestrator.py` | 同上 | 文章架构+初稿 |
| Step 3 | **精加工** | `content_orchestrator.py` | 同上 | 文献补充+修正 |
| Step 4 | **文章组装** | `content_orchestrator.py` | — | 清洗→合并→写入文件 |
| Step 5 | **管线发布** | → 调 `publish_one.py` | — | 推公众号草稿 |
| Step 6 | **视频生成** | → 调 `video_pipeline.py` | — | Remotion渲染 |
| Step 7 | **登记追踪** | `content_dashboard.py` | — | 内容状态管理 |

> 🚨 **自动降级链**: 豆包 → 失败 → Gemini → 失败 → DeepSeek API → 全部失败 → 提示用户
> **两条内容线**: `--track ai` (AI提效实战派) / `--track thinking` (反共识深度文)
> **审核闸门**: 每步可选 继续/修改/重做/跳过

### ③ video-pipeline — 视频生成管线

| 步骤 | 功能 | 脚本/技术 | 产出 |
|------|------|-----------|------|
| 0/6 | **Hook选择** | `suggest_hook()` | 8种钩子自动匹配 |
| 1/6 | **文章注册** | `video_pipeline.py` | `data/articles.json` |
| 2/6 | **素材生成** | Pillow组件 | cover.png, bg_main.png, bg_gradient.png, bg_accent_bar.png, theme.json |
| 3/6 | **TTS+BGM** | edge-tts + lo-fi和弦 | `public/bgm_{id}.wav` |
| 4/6 | **Remotion渲染** | `npx remotion render` | `out/{id}.mp4` (1080×1920, 30fps, 25s) |
| 5/6 | **注册表更新** | `content_registry.json` | 发布状态登记 |

> **10套主题**: midnight-galaxy / ocean-depths / sunset-boulevard / forest-canopy / modern-minimalist / golden-hour / arctic-frost / desert-rose / tech-innovation / botanical-garden
> **场景结构**: HookIntro(0-3s) → 数据卡片(3-14.5s) → 金句(14.5-20s) → Outro品牌卡(20-25s)

---

## 三、多平台发布引擎 🌐

### 平台模块一览

```
scripts/platforms/
├── __init__.py         平台注册表 — 所有平台在这里注册
├── base.py             BasePlatform基类 — 统一接口+Cookie管理+反检测三层
│                       ├── SessionPersona（人格化反检测）
│                       ├── Cookie/Token持久化
│                       └── 品牌色常量 DARK_BG/GOLD/BRAND
│
├── wechat.py           公众号      — API推草稿（appID: wx331b651c8159fdcb）
├── bilibili.py         B站        — 视频发布+文章发布
├── douyin.py           抖音       — 视频上传
├── kuaishou.py         快手       — 短视频发布
├── xiaohongshu.py      小红书     — 图文/视频发布
├── zhihu.py            知乎       — 文章发布
├── jike.py             即刻       — 动态发布
├── channels.py         视频号     — channels.weixin.qq.com
├── juejin.py           掘金       — 技术文章发布
├── goofish.py          闲鱼       — 虚拟商品发布
├── goofish_delivery.py 闲鱼发货   — 自动发货
├── afdian.py           爱发电     — 创作者文章
├── tencent_cloud.py    腾讯云社区 — 技术文章
│
├── traffic.py           统一引流文案中心 — 不同内容类型自动匹配引流话术
├── content_adapter.py   内容适配器 — 平台格式转换
└── publish_log.py       发布日志   — 去重+记录
```

### 平台分类

```
文字平台（TEXT）: 公众号 | 掘金 | 知乎 | 即刻 | 腾讯云 | 爱发电 | 闲鱼
视频平台（VIDEO）: 抖音 | 快手 | 视频号 | B站 | 小红书
```

### 调用方式

```bash
# 单平台
python publish.py article.md --wechat         # 只发公众号
python publish.py article.md --bilibili       # 只发B站

# 多平台
python publish.py article.md                   # 发所有平台
python publish.py article.md --bilibili --kuaishou --douyin  # 指定视频平台

# 配置
python publish.py --setup-bilibili            # 引导配置B站Cookie
python publish.py --list-platforms            # 列出所有可用平台
```

---

## 四、数据采集与分析 📊

### 数据采集层 (collectors)

```
scripts/platforms/collectors/
├── base_reader.py        采集基类
├── collect.py            统一采集入口 — 遍历所有平台采集数据
├── inventory_store.py    库存存储 — 写入 content-inventory.json
├── models.py             数据模型
├── wbi_sign.py           B站WBI签名（反爬）
├── bilibili_reader.py    B站数据读取
├── channels_reader.py    视频号数据读取
├── douyin_reader.py      抖音数据读取
├── juejin_reader.py      掘金数据读取
├── kuaishou_reader.py    快手数据读取
├── wechat_reader.py      公众号数据读取
└── zhihu_reader.py       知乎数据读取
```

### 分析报告层 (reports)

```
scripts/platforms/reports/
├── cross_reference.py      交叉引用分析
├── engagement_report.py    互动数据报告
├── feedback_analysis.py    反馈分析
└── strategy_recommend.py   策略推荐
```

### 驱动脚本

| 脚本 | 功能 | 用法 |
|------|------|------|
| `collect_video_stats.py` | 视频数据定时采集 | `--platform bilibili --summary` |
| `content_dashboard.py` | 内容发布可视化仪表盘 | `serve` / `list` / `add` / `mark` / `pending` / `summary` / `sync` |
| `content_eval.py` | 五维评分（标题/结构/金句/引流/品牌） | 综合 ≥70 放行 |
| `content_registry.json` | 内容注册表（所有发布记录） | 统一存取 |

---

## 五、商业变现管线 💰

### Commerce 模块

```
scripts/commerce/
├── lead_magnet.py         钩子产品生成 — HTML+PDF+封面（工程人AI提效/深度阅读者AI工具包）
├── product_ladder.py      产品阶梯 — 免费→付费→高价产品体系
├── reader_crm.py          读者CRM — 读者关系管理
├── wechat_keyword.py      微信关键词回复
├── deploy_wechat_keyword.sh  关键词部署脚本
└── __init__.py

scripts/commerce_pipeline.py  — 商业流水线入口
```

### 变现路径

```
免费内容（文章/视频） → 引流到微信 → 赠送钩子产品 → 付费数字产品 → 高价咨询
     ↑                    ↑               ↑              ↑          ↑
  publish.py          traffic.py     lead_magnet.py  goofish.py  product_ladder.py
                    (统一引流文案)
```

---

## 六、引流 & 社区运营管线 📢

| 脚本 | 功能 | 迭代 |
|------|------|------|
| `zhihu_answer.py` | 知乎智能回答：问题→知识库→LLM→去AI味→草稿/发布 | DeepSeek/Qwen双引擎 |
| `zhihu_traffic.py` | 知乎引流：搜索高流量问题→写回答→挂文章链接 | 自动匹配CAD/AI等主题 |
| `zhihu_answer_search.py` | 知乎问题搜索 | 话题定向 |
| `auto_comment.py` | 知乎+掘金自动评论（带 URL 去重） | ~/.claude/commented_articles.json |
| `_run_pub.py` | 知乎掘金自动评论批处理入口 | — |

---

## 七、搜索引擎方案 🔍

| 引擎 | 脚本 | 方式 | 用途 | 优先级 |
|------|------|------|------|--------|
| **元宝搜索** | `yuanbao_search.py` | Playwright + Cookie | 常规搜索 | 1（铁律） |
| **元宝桌面版** | `yuanbao_desktop.py` | 桌面版抓取 | 备用 | 2 |
| **DeepSeek Web** | `deepseek_web.py` | Playwright + storage_state | 文章搜索 | 1（管线用） |
| **DeepSeek API** | `deepseek_search.py` | REST API | 快速模式 | 3 |
| **豆包搜索** | `catalog/scripts/doubao_search.py` | Playwright | 三AI协作 | content-orchestrator用 |
| **Gemini搜索** | `catalog/scripts/gemini_search.py` | Playwright | 三AI协作 | content-orchestrator用 |
| **WebSearch** | 内置工具 | 通用 | 最终降级 | 4（兜底） |

---

## 八、其他工具脚本 🔧

| 脚本 | 功能 | 备注 |
|------|------|------|
| `videofast_server.py` | VideoFast订单服务 — Flask API接单→Remotion渲染→Gmail发成品 | `POST /videofast/order` |
| `patch_videofast.py` | VideoFast三个bug修补 | 不碰凭证行 |
| `upload-video.py` | MP4→抖音/快手/B站上传 | 走Playwright |
| `publish_xhs_video.py` | 小红书视频一键发布 | 独立脚本 |
| `publish_afdian.py` | 爱发电一键发文 | 支持MD文件+AI选题 |
| `publish_llm_article.py` | Huga MD→封面→公众号草稿 | 一次性发布管线 |
| `generate_collection_cover.py` | 合集封面生成 | Pillow |
| `setup_xhs_cookies.py` | 小红书Cookie设置向导 | — |
| `import_yuanbao_cookies.py` | 导入元宝Cookie | — |
| `token_count.py` | Token计费 | v3 tokenizer |
| `deepseek_setup.py` | DeepSeek环境设置 | — |
| `_debug_wechat.py` | 公众号调试 | — |
| `step3_test.py` / `step4_publish.py` | 知乎自动评论测试/发布步骤 | — |
| `issue-to-pitfall.py` | Issue→踩坑记忆转换器 | — |
| `content_registry.json` | 内容注册表 — 所有发布历史 | ~82KB |

---

## 九、迭代时间线（2026年）

```
06-10  博客项目初始化（Hugo主题/布局）
06-12  deepseek_search.py / 合集封面 / 封面引导
06-13  hugo配置 / layouts
06-14  issue-to-pitfall / publish_wechat_auto_reply / 视频上传
06-15  upload-video.py / 多平台发布避坑指南视频
06-19  TTS视频系列（3个MP4: 1781845033/7767/7939）
06-20  commerce管线（lead_magnet / product_ladder / reader_crm）
06-21  zhihu_traffic 知乎引流 / auto_comment 自动评论
06-24  xiaowei测试视频 / setup_xhs_cookies
06-26  zhihu_answer 知乎智能回答
06-28  yuanbao_pipeline V4（结构化输出/自动提取）
       content_adapter / 闲鱼 / 腾讯云 / publish.py V2
06-29  V2修复集:
       ├─ publish_one.py — JSON解析增强 + RegistryManager
       ├─ yuanbao_pipeline.py — as_dict / auto_extract / tracker
       ├─ content_dashboard.py — serve/list/add/mark/sync
       └─ collect_video_stats.py — 视频数据采集
06-30  afdian（爱发电）平台上线
07-01  博客目录结构调整
07-03  content-orchestrator 技能封装（三AI协作+自动降级）
       ├─ doubao_search / gemini_search / deepseek_search
       └─ video_pipeline 对接
       文章: 多Agent协作编程实战 / Agentic AI自主编程时代
```

---

## 十、技能封装映射 🔗

```
skill（~/.claude/skills/）         → 调用脚本
──────────────────────────────────────────────────
wechat-publish                     → publish_one.py（5步快速发文）
content-orchestrator               → content_orchestrator.py（7步深度管线）
video-pipeline                     → video_pipeline.py（6步视频生成）
yuanbao-search                     → yuanbao_search.py（搜索降级链）
pipeline_tracker                   → pipeline_tracker.py（管线可视化）
skill-creator                      → 技能封装工具

brand-guidelines                   → 品牌规范（深海蓝#1a1a2e + 暖金#c8a03c）
docx                               → docx生成（表防断+TOC）
xlsx                               → Excel处理
audit                              → 审计五件套
```

---

## 十一、重要路径汇总

```
世界一隅博客:  ~/world-corner-blog/
   ├── scripts/             ← 生产管线（发布/平台/采集）
   ├── content/posts/       ← Hugo文章源
   ├── articles/            ← 微信公众号文章备份
   └── public/              ← 构建产出

深度创作:     ~/catalog/scripts/
   ├── content_orchestrator.py   ← 三AI协作主脚本
   ├── doubao_search.py          ← 豆包搜索
   ├── gemini_search.py          ← Gemini搜索
   └── video_pipeline.py         ← 视频管线（另一副本）

视频平台:     ~/projects/remotion-video-platform/
   ├── scripts/video_pipeline.py ← 视频管线主入口
   ├── src/PromoVideo.tsx        ← Remotion视频模板
   └── out/                      ← 渲染产物 .mp4

技能目录:     ~/.claude/skills/（27个技能）

Cookie/配置:  ~/.claude/
   ├── platform-cookies.json     ← 各平台Cookie
   ├── deepseek-state.json       ← DeepSeek登录态
   └── publish-log.json          ← 发布日志

内容注册表:   ~/world-corner-blog/scripts/content_registry.json
仪表盘:       http://127.0.0.1:5000（content_dashboard.py serve）
```

---

## 十二、快速导航

```
想做什么？                          → 命令/入口
──────────────────────────────────────────────────────────────────
快速发一篇公众号                     python publish_one.py
发一篇到多平台                       python publish.py article.md
深度写文章（三AI协作）               python content_orchestrator.py "话题" --full --track ai
做一个视频                           python video_pipeline.py "标题" --auto
上传视频到平台                       python upload-video.py video.mp4 --all
知乎引流                             python zhihu_traffic.py
知乎回答                             python zhihu_answer.py
发爱发电                             python publish_afdian.py
发小红书视频                         python publish_xhs_video.py
查看内容仪表盘                       python content_dashboard.py serve
查看数据统计                         python collect_video_stats.py --summary
商业变现                             python commerce_pipeline.py --status
搜索                                 python yuanbao_search.py -r "问题"
```

---

> **维护提示**: 每次新增/修改脚本后，请同步更新此框架图。
> 建议保留在 `~/world-corner-blog/CONTENT-PIPELINE-MAP.md`，方便随时查阅。
