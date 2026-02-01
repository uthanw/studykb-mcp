# StudyKB MCP Server

<p align="center">
  <strong>知识库管理 + 学习进度追踪 MCP 服务端</strong>
</p>

<p align="center">
  基于 <a href="https://modelcontextprotocol.io/">Model Context Protocol</a> 的智能学习助手后端，专为考研等长期学习场景设计。
</p>

<p align="center">
  <a href="#功能特性">功能特性</a> •
  <a href="#快速开始">快速开始</a> •
  <a href="#mcp-tools-参考">Tools 参考</a> •
  <a href="#配置说明">配置说明</a> •
  <a href="#开发指南">开发指南</a>
</p>

---

## 功能特性

### 知识库管理

- **多学科支持**：按大类（Category）组织资料，如数据结构、计算机组成原理、有机化学等
- **智能索引**：支持为大型资料文件创建章节索引，精确定位到行号
- **全文搜索**：关键词搜索，支持上下文显示，快速定位知识点
- **行级读取**：精确读取指定行范围，避免一次性加载大文件

### 学习进度追踪

- **状态管理**：`pending` → `active` → `done` → `review` 完整学习状态流转
- **艾宾浩斯复习**：基于遗忘曲线自动计算复习时间，科学记忆
- **自动降级**：到期未复习的知识点自动从 `done` 降级为 `review`
- **进度统计**：可视化进度条，一目了然的学习概览

### Agent 友好

- **TUI 风格输出**：返回格式模拟交互式终端，信息密度高
- **Token 优化**：精简输出格式，降低 LLM 调用成本
- **工具链推荐**：每个 Tool 的 description 包含调用时机和推荐的前置/后续调用

---

## 快速开始

### 系统要求

- Python >= 3.10
- 支持 MCP 协议的客户端（如 Claude Desktop、Cursor 等）

### 安装

```bash
# 克隆项目
git clone https://github.com/your-username/studykb-mcp.git
cd studykb-mcp

# 安装（推荐使用虚拟环境）
pip install -e .

# 或者安装完整开发依赖
pip install -e ".[all]"
```

### 配置 MCP 客户端

#### Claude Desktop

编辑 `~/Library/Application Support/Claude/claude_desktop_config.json`（macOS）或相应配置文件：

```json
{
  "mcpServers": {
    "studykb": {
      "command": "studykb-mcp",
      "args": [],
      "env": {
        "STUDYKB_KB_PATH": "/path/to/your/kb",
        "STUDYKB_PROGRESS_PATH": "/path/to/your/progress"
      }
    }
  }
}
```

#### Cursor / VS Code

在 MCP 设置中添加：

```json
{
  "studykb": {
    "command": "studykb-mcp",
    "env": {
      "STUDYKB_KB_PATH": "./kb",
      "STUDYKB_PROGRESS_PATH": "./progress"
    }
  }
}
```

### 准备知识库

创建目录结构：

```
kb/                                    # 知识库根目录
├── 数据结构/                           # 大类 (Category)
│   ├── 王道数据结构.md                 # 资料文件 (Material)
│   ├── 王道数据结构_index.md           # 索引文件 (可选)
│   └── 算法笔记.md
├── 计算机组成原理/
│   ├── 王道计组.md
│   └── 王道计组_index.md
└── 有机化学/
    └── 有机化学教材.md

progress/                              # 进度数据目录（自动创建）
├── 数据结构.json
└── 计算机组成原理.json
```

### 启动服务

```bash
# 使用 CLI（stdio 模式，供 MCP 客户端连接）
studykb-mcp

# 或使用 Python 模块
python -m studykb_mcp
```

--- 

##  

```
studykb-mcp/
├── pyproject.toml                      # 项目配置
├── README.md                           # 本文件
├── src/studykb_mcp/
│   ├── __init__.py
│   ├── __main__.py                     # CLI 入口
│   ├── server.py                       # MCP 服务器核心
│   ├── config/
│   │   └── settings.py                 # 配置管理
│   ├── models/
│   │   ├── kb.py                       # 知识库数据模型
│   │   └── progress.py                 # 进度数据模型
│   ├── services/
│   │   ├── kb_service.py               # 知识库操作服务
│   │   ├── progress_service.py         # 进度管理服务
│   │   └── review_service.py           # 艾宾浩斯复习算法
│   ├── tools/                          # 6 个 MCP Tools
│   │   ├── read_overview.py
│   │   ├── read_progress.py
│   │   ├── update_progress.py
│   │   ├── read_index.py
│   │   ├── read_file.py
│   │   └── grep.py
│   └── utils/
│       ├── formatters.py               # TUI 风格输出格式化
│       └── datetime_utils.py           # 时间工具
├── tests/                              # 测试用例 (65 个)
├── kb/                                 # 知识库目录
└── progress/                           # 进度数据目录
```

---

## MCP Tools 参考

StudyKB 提供 6 个 MCP Tools，覆盖知识库浏览、内容读取、进度管理的完整流程。

### 工具一览

| Tool | 功能 | 必需参数 | 可选参数 |
|------|------|----------|----------|
| `read_overview` | 获取知识库全景图 | - | - |
| `read_progress` | 获取学习进度 | `category` | `status_filter`, `since`, `limit` |
| `update_progress` | 创建/更新进度 | `category`, `progress_id`, `status`, `comment` | `name` |
| `read_index` | 读取资料索引 | `category`, `material` | - |
| `read_file` | 读取资料内容 | `category`, `material`, `start_line`, `end_line` | - |
| `grep` | 搜索关键词 | `category`, `pattern` | `material`, `context_lines`, `max_matches` |

---

### Tool 1: `read_overview`

获取知识库全景图，列出所有大类及其包含的资料文件。

**参数**：无

**调用时机**：
- 对话开始时，了解当前知识库有哪些内容
- 用户提到一个你不确定是否存在的学科/资料时
- 需要向用户展示可学习的范围时

**返回示例**：

```
# Knowledge Base Overview

数据结构/ (3 files)
  ├ 王道数据结构         23965 ln  [IDX]
  ├ 天勤数据结构         18420 ln
  └ 算法全景图            3500 ln  [IDX]

计算机组成原理/ (2 files)
  ├ 王道计组             19800 ln  [IDX]
  └ 唐朔飞计组           15600 ln

---
2 categories, 5 files
[IDX] = index available
```

---

### Tool 2: `read_progress`

获取某个大类的学习进度追踪数据。调用时会自动检查并触发 `done` → `review` 的状态转换。

**参数**：

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `category` | string | 是 | - | 大类名称，如 "数据结构" |
| `status_filter` | array | 否 | null | 筛选状态：`done`, `active`, `review`, `pending` |
| `since` | string | 否 | `"all"` | 时间范围：`7d`, `30d`, `90d`, `all` |
| `limit` | integer | 否 | 20 | 每个状态分组的最大返回条数，-1 返回全部 |

**调用时机**：
- 用户说"继续学习""今天学什么"时
- 需要确定下一个学习内容时
- 检查是否有需要复习的内容时

**返回示例**：

```
# Progress: 数据结构

done: 23 | active: 1 | review: 3 | pending: 18 | total: 45
[====================..........] 51%

## 🔥 active (1)

ds.graph.mst.kruskal | Kruskal算法
  "边排序+并查集思路，正在看具体实现"
  updated: 2h ago

## 🔄 review (3)

ds.linear.array.prefix_sum | 前缀和 | +14d overdue
  "一维二维都搞定了"
  reviewed 2x

ds.tree.traversal.inorder | 中序遍历 | +10d overdue
  "递归秒杀，迭代用栈模拟"
  reviewed 1x

## ✅ done (showing 5, +18 more)

ds.graph.mst.prim         | Prim算法      | Jan 19
ds.graph.shortest.dijkstra | Dijkstra     | Jan 18
ds.graph.traversal.bfs    | BFS          | Jan 17

---
Showing up to 20 per group. Use limit=-1 to fetch all.
```

---

### Tool 3: `update_progress`

创建或更新学习进度条目。

**参数**：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `category` | string | 是 | 大类名称 |
| `progress_id` | string | 是 | 进度标识，使用点分层级格式，如 `ds.graph.mst.kruskal` |
| `status` | string | 是 | 状态：`active`(正在学习), `done`(已掌握), `review`(需复习) |
| `comment` | string | 是 | 一句话描述当前理解/进度/笔记 |
| `name` | string | 首次必填 | 知识点名称，如 "Kruskal算法" |

**调用时机**：
- 开始学习新知识点时 → `status="active"`
- 用户表示掌握了某个知识点时 → `status="done"`
- 完成复习时 → `status="done"`（会自动增加 review_count）

**状态转换逻辑**：

```
active → done    : 设置 mastered_at, 计算 next_review_at
review → done    : review_count += 1, 重新计算 next_review_at (间隔 × 1.5)
* → active/review: 清除 next_review_at
```

**返回示例**（更新）：

```
✅ Progress updated

数据结构 / ds.graph.mst.kruskal
Kruskal算法

  active → done
  "边排序+并查集，时间O(ElogE)，空间O(V)"

next review: Jan 27 (7d)
```

**返回示例**（新建）：

```
✨ Progress created

数据结构 / ds.dp.knapsack.01
0-1背包问题 [NEW]

  status: active
  "开始学习，先理解状态定义"
```

---

### Tool 4: `read_index`

读取资料的索引文件，获取章节结构和行号映射。

**参数**：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `category` | string | 是 | 大类名称 |
| `material` | string | 是 | 资料名称（不含扩展名），如 "王道数据结构" |

**调用时机**：
- 需要定位某个知识点在资料中的具体位置时
- 准备用 `read_file` 读取内容前，先查行号
- 用户问"这个在书的哪里"时

**返回**：索引文件的完整 Markdown 内容

**无索引时**：

```
⚠️ Index not found: 数据结构/天勤数据结构

No index file available for this material.
Use `grep` to search or `read_file` with estimated ranges.
```

---

### Tool 5: `read_file`

读取资料文件的指定行范围内容。

**参数**：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `category` | string | 是 | 大类名称 |
| `material` | string | 是 | 资料名称（不含扩展名） |
| `start_line` | integer | 是 | 起始行号（包含），从 1 开始 |
| `end_line` | integer | 是 | 结束行号（包含） |

**限制**：单次最多读取 500 行，超出会截断

**返回示例**：

```
# 数据结构/王道数据结构 L14230-14260

14230 | **2. Kruskal 算法**
14231 |
14232 | Kruskal 算法是一种按权值的递增次序选择合适的边来构造最小
14233 | 生成树的方法。
14234 |
14235 | 算法思想：设连通网 N=(V,E)，令最小生成树的初始状态为只有
14236 | n 个顶点而无边的非连通图 T=(V,{})...
```

---

### Tool 6: `grep`

在资料中搜索关键词，返回匹配行及上下文。

**参数**：

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `category` | string | 是 | - | 大类名称 |
| `pattern` | string | 是 | - | 搜索关键词（大小写不敏感） |
| `material` | string | 否 | null | 资料名称，不填则搜索整个大类 |
| `context_lines` | integer | 否 | 2 | 匹配行的上下文行数（上下各 N 行） |
| `max_matches` | integer | 否 | 20 | 最大返回匹配数，-1 返回全部 |

**返回示例**（单文件）：

```
# grep "Kruskal" in 数据结构/王道数据结构
4 matches

[L14230]
  14228 | 的时间复杂度为 O(ElogE)。
> 14230 | **2. Kruskal 算法**
  14232 | Kruskal 算法是一种按权值的递增次序选择合适的边来构造最小

[L14267]
  14265 |
> 14267 | 使用 Kruskal 算法求下图的最小生成树。
  14269 | 解：首先将边按权值排序：
```

**返回示例**（跨文件）：

```
# grep "并查集" in 数据结构/*
12 matches

-- 王道数据结构 (8) --

[L11479]
> 11479 | ## 5.5.2 并查集
  11481 | 并查集（Union-Find Sets）是一种树型数据结构

-- 算法全景图 (4) --

[L892]
> 892 | │   ├── 并查集 (Union-Find / Disjoint Set) ⭐
```

---

## 典型交互流程

```
用户: "今天学点新东西"
         │
         ▼
    read_overview()          ← 看看知识库有什么
         │
         ▼
    read_progress(...)       ← 看看学到哪了
         │
         ▼
    ┌────┴────┐
    │ 有索引?  │
    └────┬────┘
      是 │ 否
         │    │
         ▼    ▼
  read_index() grep()        ← 定位内容
         │    │
         └──┬─┘
            ▼
      read_file()            ← 读取原文
            │
            ▼
     update_progress()       ← 标记开始学习
            │
            ▼
        [开始讲解]
```

---

## 数据格式

### 进度数据结构

进度数据按大类存储为 JSON 文件：

```json
{
  "category": "数据结构",
  "last_updated": "2025-01-20T14:30:00",
  "entries": {
    "ds.graph.mst.kruskal": {
      "name": "Kruskal算法",
      "status": "done",
      "comment": "边排序+并查集，时间O(ElogE)",
      "updated_at": "2025-01-20T14:30:00",
      "mastered_at": "2025-01-20T14:30:00",
      "review_count": 0,
      "next_review_at": "2025-01-27T00:00:00"
    }
  }
}
```

### 状态定义

| 状态 | 含义 | 触发条件 |
|------|------|----------|
| `pending` | 待学习 | 可选，用于规划 |
| `active` | 正在学习 | 用户开始学习 |
| `done` | 已掌握 | 用户表示掌握，触发复习计时 |
| `review` | 需要复习 | 系统自动从 done 降级 |

### 索引文件格式

索引文件命名规则：`资料名_index.md`

```markdown
# 王道《数据结构》章节索引

## 文件结构概览
| 部分 | 行号范围 | 说明 |
|------|---------|------|
| 前置内容 | 1-311 | 封面、版权、前言 |
| 目录 | 312-730 | 全书目录 |
| 正文 | 732-23923 | 8章正文内容 |

## 第1章 绪论（732-1453行）
| 行号范围 | 内容 |
|---------|------|
| 762-942 | **1.1 数据结构的基本概念** |
| 943-1409 | **1.2 算法和算法评价** |

## 快速查找
| 知识点 | 行号 | 章节 |
|-------|------|------|
| Kruskal算法 | 14230-14280 | 6.4.1 |
| 快速排序 | 20741-20856 | 8.3.2 |
```

---

## 复习机制

### 艾宾浩斯遗忘曲线

StudyKB 实现了基于艾宾浩斯遗忘曲线的间隔重复算法：

```
间隔天数 = 初始间隔 × (增长系数 ^ 复习次数)
```

**默认配置**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 初始间隔 | 7 天 | 首次标记 done 后的复习间隔 |
| 增长系数 | 1.5 | 每次成功复习后间隔的增长倍数 |
| 最大间隔 | 90 天 | 间隔上限 |

**复习计划示例**：

| 复习次数 | 距上次间隔 | 累计天数 |
|----------|-----------|----------|
| 第1次 | 7天 | 7天 |
| 第2次 | 10天 | 17天 |
| 第3次 | 15天 | 32天 |
| 第4次 | 23天 | 55天 |
| 第5次 | 34天 | 89天 |
| 第6次+ | 90天 | 179天+ |

### 自动状态转换

每次调用 `read_progress` 时，系统会自动检查所有 `done` 状态的条目：

- 如果 `next_review_at` 已过期 → 自动转为 `review` 状态
- 用户完成复习后调用 `update_progress(status="done")` → `review_count` +1，重新计算下次复习时间

---

## 配置说明

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `STUDYKB_HOST` | `0.0.0.0` | 服务器绑定地址（HTTP 模式时使用） |
| `STUDYKB_PORT` | `8080` | 服务器端口（HTTP 模式时使用） |
| `STUDYKB_KB_PATH` | `./kb` | 知识库目录路径 |
| `STUDYKB_PROGRESS_PATH` | `./progress` | 进度数据目录路径 |
| `STUDYKB_MAX_READ_LINES` | `500` | 单次 read_file 最大行数 |
| `STUDYKB_MAX_GREP_MATCHES` | `100` | 单次 grep 最大匹配数 |
| `STUDYKB_REVIEW_INITIAL_INTERVAL` | `7` | 首次复习间隔（天） |
| `STUDYKB_REVIEW_MULTIPLIER` | `1.5` | 复习间隔增长系数 |
| `STUDYKB_REVIEW_MAX_INTERVAL` | `90` | 最大复习间隔（天） |

### 配置文件

也可以通过 `.env` 文件配置：

```bash
# .env
STUDYKB_KB_PATH=/data/knowledge-base
STUDYKB_PROGRESS_PATH=/data/progress
STUDYKB_MAX_READ_LINES=1000
STUDYKB_REVIEW_INITIAL_INTERVAL=3
```

---

## 开发指南

### 安装开发依赖

```bash
pip install -e ".[all]"
```

### 运行测试

```bash
# 运行所有测试
pytest

# 带覆盖率报告
pytest --cov=studykb_mcp --cov-report=html

# 运行特定测试
pytest tests/test_services/test_review_service.py -v
```

### 代码检查

```bash
# 代码格式化和 lint
ruff check src tests
ruff format src tests

# 类型检查
mypy src
```

### 项目架构

```
src/studykb_mcp/
├── server.py              # MCP Server 入口，注册所有 tools
├── config/settings.py     # 配置管理（pydantic-settings）
├── models/
│   ├── kb.py              # Category, Material 数据模型
│   └── progress.py        # ProgressEntry, ProgressFile 数据模型
├── services/
│   ├── kb_service.py      # 知识库文件操作（异步 IO）
│   ├── progress_service.py # 进度 CRUD + 自动状态转换
│   └── review_service.py  # 艾宾浩斯复习算法
├── tools/                 # 6 个 MCP Tool handlers
└── utils/
    ├── formatters.py      # TUI 风格输出格式化
    └── datetime_utils.py  # 时间格式化工具
```

### 添加新 Tool

1. 在 `tools/` 目录创建新的 handler 文件
2. 在 `server.py` 的 `TOOLS` 列表添加 Tool 定义
3. 在 `HANDLERS` 字典注册 handler
4. 添加测试用例

---

## 常见问题

### Q: 如何创建索引文件？

索引文件需要手动创建，命名为 `资料名_index.md`，放在与资料文件相同的目录下。索引内容应包含章节结构和行号映射，方便快速定位。

### Q: 进度数据存储在哪里？

进度数据按大类存储为 JSON 文件，默认位于 `./progress/` 目录。每个大类一个文件，如 `数据结构.json`。

### Q: 复习时间过了但我没复习会怎样？

系统会在下次调用 `read_progress` 时自动将该条目从 `done` 状态转为 `review` 状态，并显示逾期天数。

### Q: 如何重置复习计数？

目前需要手动编辑进度 JSON 文件，将 `review_count` 设为 0。

### Q: 支持哪些文件格式？

目前仅支持 Markdown (`.md`) 格式的资料文件。

---

## 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| MCP SDK | `mcp>=1.0.0` | Anthropic 官方 Python SDK |
| 传输协议 | stdio | 标准输入输出，供 MCP 客户端连接 |
| 数据验证 | Pydantic v2 | 类型安全的数据模型 |
| 配置管理 | pydantic-settings | 支持环境变量和 .env 文件 |
| 异步 IO | aiofiles | 非阻塞文件操作 |
| 测试框架 | pytest + pytest-asyncio | 异步测试支持 |

---

## License

MIT License

---

## 致谢

- [Model Context Protocol](https://modelcontextprotocol.io/) - Anthropic 开源的 AI 应用协议
- [艾宾浩斯遗忘曲线](https://en.wikipedia.org/wiki/Forgetting_curve) - 科学记忆方法论
# studykb-mcp
