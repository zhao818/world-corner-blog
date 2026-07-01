# 🌍 世界一隅 | 认知能量工程

> *"在算法洪流中，守护清醒的微光。"*

基于 [Hugo](https://gohugo.io) + [PaperMod](https://github.com/adityatelange/hugo-PaperMod) 的个人博客，聚焦**系统思维、学习方法、效率工具**三大领域。集成自定义主题组件、自动化发布脚本、以及 AI Agent（Hermes）协作发布规则。

[![Hugo](https://img.shields.io/badge/Hugo-0.146.0-ff4088?logo=hugo)](https://gohugo.io)
[![Deploy](https://img.shields.io/badge/deploy-GitHub%20Pages-brightgreen)](https://pages.github.com)
[![License](https://img.shields.io/badge/license-CC%20BY--SA%204.0-blue)](LICENSE)

## 📂 站点结构

```
content/
├── posts/
│   ├── systems-thinking/   ← 31 篇（文明、认知、孤独、文学连载）
│   ├── tooling/            ← 8 篇（AI审计、工具主权、内容缓冲池）
│   └── learning/           ← 4 篇（内核重构、经济思维、三角函数）
└── pitfalls/               ← 17 个工程踩坑记录
```

**四大导航栏目：** 系统思维 · 学习方法 · 效率工具 · 踩坑宝典

## 🛠 自定义组件

| 组件 | 说明 |
|------|------|
| `layouts/partials/energy-matrix.html` | 能量矩阵 — 深度连接 / 对冲支持 / 认知分发群 QR 卡片 |
| `layouts/partials/series-sidebar.html` | 系列文章侧边栏导航 |
| `layouts/partials/newsletter.html` | Newsletter 订阅组件 |
| `layouts/partials/section-nav-row.html` | 分类导航行 |
| `layouts/pitfalls/` | 踩坑宝典自定义列表/详情页模板 |

### 预览工具

- **`preview_matrix.html`** — 能量矩阵效果预览（含三组 QR 码 + 引用金句）
- **`final_preview.html`** — 最终预览版本（含点击放大模态框 + 佛学引用）

在浏览器直接打开即可预览矩阵卡片效果。

## 🚀 本地开发

```bash
# 1. 克隆仓库
git clone --recurse-submodules https://github.com/zhao818/world-corner-blog.git
cd world-corner-blog

# 2. 安装 Hugo 0.146.0
# macOS
brew install hugo
# Linux (snap)
snap install hugo --channel=extended

# 3. 启动开发服务器
hugo server -D
# 访问 http://localhost:1313
```

## 🤖 Hermes 发布规则

[`.hermes_rules.md`](.hermes_rules.md) 定义了 AI Agent 辅助发布的四层规范：

1. **YAML 语法防火墙** — 标题用 `「」`，标签小写英文，`draft` 默认 `false`
2. **排版工程学** — 架构图用 ` ```text `，代码块声明语言
3. **摘要准则** — 从 `>` 引用块萃取金句（最多 3 条），URL 格式 `https://worldcorner.xyz/posts/{slug}/`
4. **CI/CD 锁定** — Hugo `0.146.0`，Node `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true`

## 🔧 自动化脚本

| 脚本 | 用途 |
|------|------|
| `scripts/zhihu_answer.py` | 知乎回答自动生成 |
| `scripts/push_wechat_draft_intro.py` | 微信公众号草稿推送 |
| `scripts/generate_collection_cover.py` | 合集封面图生成 |

## 📡 部署流程

```
push main → GitHub Actions → hugo -d docs → auto-commit docs/ → GitHub Pages
```

1. 推送代码到 `main` 分支
2. GitHub Actions 触发 `hugo.yml`
3. 安装 Hugo 0.146.0 + Dart Sass
4. 构建到 `docs/` 目录
5. 自动提交 `docs/` 到仓库
6. GitHub Pages 从 `docs/` 文件夹提供服务

## 🔗 关联仓库

| 仓库 | 关系 |
|------|------|
| [world-corner](https://github.com/zhao818/world-corner) | 后端自动化流水线 — CrewAI 多 Agent 内容生产 |
| [claude-memory](https://github.com/zhao818/claude-memory) | AI Agent 共享记忆中枢 — 踩坑知识库 |
| [prompt-engineering-from-pits](https://github.com/zhao818/prompt-engineering-from-pits) | 33 个工程踩坑提炼的提示词方法论 |

## 📄 许可

CC BY-SA 4.0 — 欢迎分享与二次创作，需署名并保留相同许可。
