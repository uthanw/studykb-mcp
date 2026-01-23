# StudyKB MCP Server

知识库 + 进度追踪 MCP 服务端，为考研学习场景设计。

## 功能特性

- **知识库管理**：多学科教材资料的存储、索引、检索
- **进度追踪**：基于艾宾浩斯遗忘曲线的学习状态管理
- **Agent 友好**：返回格式模拟交互式 TUI，信息密度高且 token 开销小

## 安装

```bash
# 使用 pip
pip install -e .

# 开发模式（包含测试依赖）
pip install -e ".[dev]"
```

## 使用

### 启动服务

```bash
# 使用 CLI
studykb-mcp

# 或者使用 Python
python -m studykb_mcp
```

### MCP Tools

| Tool | 功能 |
|------|------|
| `read_overview` | 获取知识库全景图 |
| `read_progress` | 获取学习进度 |
| `update_progress` | 更新学习进度 |
| `read_index` | 读取资料索引 |
| `read_file` | 读取资料内容 |
| `grep` | 搜索关键词 |

## 目录结构

```
kb/                     # 知识库目录
├── 数据结构/
│   ├── 王道数据结构.md
│   └── 王道数据结构_index.md
└── ...

progress/               # 进度数据目录
├── 数据结构.json
└── ...
```

## 配置

通过环境变量配置：

```bash
STUDYKB_KB_PATH=./kb           # 知识库路径
STUDYKB_PROGRESS_PATH=./progress   # 进度数据路径
```

## 运行测试

```bash
pytest
```

## License

MIT
