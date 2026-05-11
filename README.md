# 树洞情绪陪伴 Agent

一个面向情绪陪伴、长期记忆和心情复盘场景的 AI 应用。项目支持多会话聊天、三种陪伴人设、SSE 流式回复、短期/中期/长期记忆、基于 ChromaDB 的语义记忆检索、每日心情总结、心情日历、天气建议和热点话题入口。

> 说明：本项目不是简单的 LLM 聊天壳，而是围绕“情绪陪伴”这个具体场景，实现了前端交互、后端接口、消息持久化、Agent 编排、RAG 长期记忆、心情分析和第三方工具接入的完整链路。

## 功能特性

- 多会话聊天：支持创建、切换、修改人设和删除会话。
- 三种陪伴风格：温柔型、理性型、幽默型，通过会话人设动态切换 Prompt。
- 流式 AI 回复：后端使用 `StreamingResponse` / SSE，前端使用 `fetch + ReadableStream` 逐步渲染回复。
- 多层记忆系统：
  - 短期记忆：最近几条原始消息进入 Prompt；
  - 中期记忆：长对话自动压缩为摘要；
  - 长期记忆：重要用户消息、摘要和心情日记写入 ChromaDB。
- RAG 语义记忆检索：Agent 在需要时主动调用 `search_memory` 检索历史记忆。
- 每日心情总结：基于当天用户消息生成情绪分数、关键词和总结文本。
- 情绪看板：展示今日心情、近 7 天趋势、月历和关键词云。
- 天气建议：调用高德 MCP 工具查询天气，并使用 LLM 生成出行、饮食、穿搭建议。
- 热点话题：调用新闻 API 获取热点新闻，作为聊天话题入口。

## 技术栈

### 后端

| 技术 | 作用 |
|---|---|
| Python | 后端主体语言 |
| FastAPI | 提供 REST API 和 SSE 流式接口 |
| SQLAlchemy | ORM 数据模型和数据库操作 |
| SQLite | 本地结构化数据存储 |
| Pydantic | 请求/响应数据校验 |
| HelloAgentsLLM | 大模型调用封装 |
| ChromaDB | 本地向量数据库，用于长期记忆检索 |
| DashScope `text-embedding-v4` | 文本向量化 |
| 高德 MCP | 天气、地理位置等第三方工具能力 |
| 阿里云市场新闻 API | 热点新闻数据来源 |

### 前端

| 技术 | 作用 |
|---|---|
| Vue 3 | 前端应用框架 |
| TypeScript | 类型约束 |
| Vite | 前端构建工具 |
| ant-design-vue | UI 组件 |
| axios | 普通 REST 请求 |
| fetch + ReadableStream | 消费 SSE 流式聊天接口 |
| marked | 渲染 AI 回复中的 Markdown 内容 |

## 项目结构

```text
emotion_companion/
├── backend/
│   ├── run.py
│   ├── emotion.db
│   ├── chroma_db/
│   └── app/
│       ├── api/
│       │   ├── main.py
│       │   └── routes/
│       │       ├── chat.py
│       │       ├── memory.py
│       │       ├── mood.py
│       │       ├── news.py
│       │       └── weather.py
│       ├── agents/
│       │   └── companion_agent.py
│       ├── models/
│       │   ├── db_models.py
│       │   └── schemas.py
│       ├── services/
│       │   ├── amap_service.py
│       │   ├── llm_service.py
│       │   ├── memory_service.py
│       │   ├── news_service.py
│       │   ├── rag_service.py
│       │   ├── summary_service.py
│       │   └── weather_service.py
│       ├── config.py
│       └── database.py
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.vue
│       ├── main.ts
│       ├── services/api.ts
│       ├── stores/appStore.ts
│       ├── types/index.ts
│       ├── views/
│       │   ├── ChatView.vue
│       │   └── MoodBoard.vue
│       └── components/
│           ├── ConversationSidebar.vue
│           ├── HotTopicCard.vue
│           ├── MessageBubble.vue
│           ├── MoodPanel.vue
│           └── WeatherWidget.vue
└── README.md
```

## 核心数据流

### 聊天主流程

```text
用户在前端输入消息
    ↓
ChatView.vue 调用 sendMessageStream()
    ↓
POST /api/chat/message/stream
    ↓
FastAPI 校验 conversation_id 和 content
    ↓
保存用户消息到 SQLite
    ↓
读取最近消息 + 会话摘要 + 人设 Prompt
    ↓
Agent 第一次调用 LLM，判断是否需要 search_memory
    ↓
如需记忆：检索 ChromaDB，并把结果注入第二次 LLM 调用
    ↓
后端通过 SSE 返回 token
    ↓
前端逐步渲染 AI 回复
    ↓
保存 assistant 回复
    ↓
有价值的用户消息写入 ChromaDB
```

### 心情总结流程

```text
用户点击“今日总结”
    ↓
POST /api/mood/summary
    ↓
读取指定日期所有用户消息
    ↓
调用 LLM 生成 score、keywords、summary
    ↓
写入或更新 mood_entries 表
    ↓
将心情总结写入 ChromaDB
    ↓
前端刷新今日心情、日历、趋势和关键词云
```

### 记忆系统

项目实现了三层记忆：

| 记忆层级 | 数据来源 | 存储位置 | 使用方式 |
|---|---|---|---|
| 短期记忆 | 最近几条原始消息 | SQLite `messages` 表 | 每轮对话直接进入 Prompt |
| 中期记忆 | 较早消息的 LLM 压缩摘要 | SQLite `memory_summaries` 表 | 作为会话摘要注入 Prompt |
| 长期记忆 | 用户关键消息、心情日记、记忆摘要 | ChromaDB `emotion_memories` 集合 | Agent 需要时语义检索 |

## 后端接口概览

后端统一前缀为 `/api`。

| 模块 | 方法 | 路径 | 说明 |
|---|---|---|---|
| 健康检查 | GET | `/` | 应用根路径 |
| 健康检查 | GET | `/health` | 服务健康状态 |
| 会话 | GET | `/api/chat/conversations` | 获取会话列表 |
| 会话 | POST | `/api/chat/conversations` | 创建会话 |
| 会话 | PATCH | `/api/chat/conversations/{conversation_id}` | 修改会话标题或人设 |
| 会话 | DELETE | `/api/chat/conversations/{conversation_id}` | 删除会话 |
| 消息 | GET | `/api/chat/conversations/{conversation_id}/messages` | 获取会话消息 |
| 聊天 | POST | `/api/chat/message` | 非流式发送消息 |
| 聊天 | POST | `/api/chat/message/stream` | SSE 流式发送消息 |
| 聊天 | GET | `/api/chat/health` | Agent / RAG 状态 |
| 记忆 | GET | `/api/memory/{conversation_id}` | 获取会话摘要列表 |
| 记忆 | GET | `/api/memory/{conversation_id}/latest` | 获取最新会话摘要 |
| 心情 | POST | `/api/mood/summary` | 生成指定日期心情总结 |
| 心情 | GET | `/api/mood/entries` | 获取全部心情记录 |
| 心情 | GET | `/api/mood/entries/calendar` | 获取指定月份日历数据 |
| 心情 | GET | `/api/mood/entries/{entry_date}` | 获取某天心情详情 |
| 天气 | GET | `/api/weather` | 根据城市或经纬度查询天气 |
| 新闻 | GET | `/api/news` | 获取热点新闻 |

启动后可访问 Swagger 文档：

```text
http://localhost:8000/docs
```

## 环境要求

建议环境：

- Python 3.10+
- Node.js 18+
- npm 9+
- 可访问大模型和 Embedding API 的网络环境

后端依赖中包含 `hello_agents` 和 `hello_agents.tools.MCPTool`。如果你的环境中无法直接安装该包，请先确保本地已有对应的 `hello_agents` 包，或按你的课程/项目依赖来源安装。

## 后端配置与启动

### 1. 进入后端目录

```bash
cd backend
```

### 2. 创建并激活虚拟环境

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS / Linux：

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. 安装 Python 依赖

当前项目未发现 `requirements.txt`，可以按源码依赖安装：

```bash
pip install fastapi uvicorn sqlalchemy pydantic pydantic-settings python-dotenv requests chromadb dashscope
```

如果你的 `hello_agents` 可以通过 pip 安装，可以继续执行：

```bash
pip install hello-agents
```

如果无法安装，请按你的本地依赖来源安装或将 `hello_agents` 加入 Python 环境。项目中以下模块依赖它：

- `backend/app/services/llm_service.py`
- `backend/app/services/amap_service.py`

高德 MCP 工具还依赖 `uvx` 启动 MCP server，若需要天气能力，请安装 `uv`：

```bash
pip install uv
```

### 4. 配置后端环境变量

在 `backend/` 目录下创建 `.env` 文件：

```env
# 服务配置
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# LLM 配置
# HelloAgentsLLM 会从环境变量读取模型配置
LLM_API_KEY=your_llm_api_key
LLM_BASE_URL=https://your-llm-base-url/v1
LLM_MODEL_ID=your_model_name
LLM_TIMEOUT=300

# 如果你的 LLM 封装使用 OpenAI 风格变量，也可以配置
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o

# DashScope Embedding
# RAGService 会优先读取 LLM_API_KEY 或 OPENAI_API_KEY 作为 dashscope.api_key
# 如果你的 DashScope Key 与 LLM Key 不同，请按实际情况调整代码或环境变量。

# 高德地图 MCP，天气组件需要
AMAP_API_KEY=your_amap_api_key

# 阿里云市场新闻 AppCode，热点新闻组件需要
NEWS_API_KEY=your_news_appcode
```

变量说明：

| 变量 | 是否必需 | 作用 |
|---|---|---|
| `LLM_API_KEY` / `OPENAI_API_KEY` | 推荐必填 | LLM 调用和 Embedding 调用所需 key |
| `LLM_BASE_URL` / `OPENAI_BASE_URL` | 视模型供应商而定 | LLM API Base URL |
| `LLM_MODEL_ID` / `OPENAI_MODEL` | 视模型供应商而定 | LLM 模型名称 |
| `AMAP_API_KEY` | 天气功能需要 | 高德 MCP 工具 key |
| `NEWS_API_KEY` | 新闻功能需要 | 阿里云市场新闻 AppCode |
| `CORS_ORIGINS` | 本地前端需要 | 允许前端跨域访问后端 |
| `HOST`、`PORT` | 可选 | 后端监听地址和端口 |

注意：

- 如果没有配置 `AMAP_API_KEY`，天气组件会失败，但聊天主流程不一定受影响。
- 如果没有配置 `NEWS_API_KEY`，新闻接口会返回配置错误。
- 如果没有配置 LLM Key，聊天、心情总结、天气建议、记忆压缩等 LLM 相关能力会不可用。
- 请不要把真实 `.env` 文件提交到 GitHub。

### 5. 启动后端

在 `backend/` 目录下执行：

```bash
python run.py
```

默认服务地址：

```text
http://localhost:8000
```

启动时会自动：

1. 创建 SQLite 数据库表；
2. 初始化默认人设配置；
3. 注册 `/api/chat`、`/api/mood`、`/api/memory`、`/api/weather`、`/api/news` 路由；
4. 输出 Swagger 文档地址。

也可以使用 uvicorn 直接启动：

```bash
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

## 前端配置与启动

### 1. 进入前端目录

```bash
cd frontend
```

### 2. 安装依赖

```bash
npm install
```

### 3. 配置前端环境变量

在 `frontend/` 目录下创建 `.env` 文件：

```env
VITE_API_BASE_URL=http://localhost:8000

# 当前前端源码主要通过后端查询天气。
# 如果后续直接在前端使用高德 Web JS API，可配置以下变量：
VITE_AMAP_WEB_KEY=your_amap_web_key
VITE_AMAP_WEB_JS_KEY=your_amap_web_js_key
```

### 4. 启动前端

```bash
npm run dev
```

默认访问地址：

```text
http://localhost:5173
```

如果前端端口不是 `5173`，需要同步修改后端 `.env` 中的 `CORS_ORIGINS`。

## 推荐启动顺序

1. 启动后端：

```bash
cd backend
python run.py
```

2. 启动前端：

```bash
cd frontend
npm run dev
```

3. 打开浏览器：

```text
http://localhost:5173
```

4. 创建新会话，选择陪伴风格，开始聊天。

## 数据库与本地数据

### SQLite

结构化数据存储在：

```text
backend/emotion.db
```

包含表：

| 表名 | 说明 |
|---|---|
| `conversations` | 会话信息 |
| `messages` | 用户和 AI 消息 |
| `memory_summaries` | 压缩后的中期记忆 |
| `mood_entries` | 每日心情记录 |
| `persona_config` | 人设配置和系统 Prompt |

### ChromaDB

向量数据存储在：

```text
backend/chroma_db/
```

集合名：

```text
emotion_memories
```

写入内容包括：

- 有实质内容的用户消息；
- 长对话压缩后的记忆摘要；
- 每日心情总结和关键词。

### GitHub 上传建议

建议不要提交以下本地数据和敏感文件：

```gitignore
backend/.env
frontend/.env
backend/emotion.db
backend/chroma_db/
frontend/node_modules/
**/__pycache__/
*.pyc
```

如果你希望仓库开箱即用，可以提交 `.env.example`，但不要提交真实 key。

## Agent 设计说明

项目中的核心 Agent 是一个自定义的情绪陪伴 Agent。它没有直接使用 LangChain Agent 或 LangGraph，而是实现了一个轻量 ReAct-like 流程：

```text
构建 Prompt
    ↓
第一次调用 LLM
    ↓
检测是否出现 [TOOL_CALL:search_memory:query=...]
    ↓
如果有：执行 ChromaDB 记忆检索
    ↓
把检索结果作为工具观察结果加入上下文
    ↓
第二次调用 LLM 生成最终回复
```

这样设计的原因是：

- 不是每轮对话都强制检索记忆，避免无关历史干扰；
- 让模型根据语义判断是否需要工具；
- 后端仍然掌握工具执行权，避免模型直接操作数据库；
- 后续可以扩展更多工具，例如日程、网页搜索、知识库、地图服务等。

## SSE 流式协议

聊天流式接口会返回 `text/event-stream`，前端按事件类型解析：

| 事件 | 含义 |
|---|---|
| `[START]` | 流开始 |
| `[USER_MSG]{...}` | 用户消息已保存，返回真实消息 ID |
| `[TOOL_USING]` | Agent 正在检索历史记忆 |
| 普通 token | AI 回复文本片段 |
| `[DONE]{...}` | AI 回复保存完成，返回真实消息 ID |
| `[ERROR]...` | 流式过程中发生错误 |

前端会先插入临时消息，收到真实 ID 后再替换，从而保证聊天体验流畅。

## 当前已实现与未实现

已实现：

- 多会话聊天；
- 流式回复；
- 三种人设；
- SQLite 消息持久化；
- 会话摘要压缩；
- ChromaDB 长期记忆；
- 心情总结和情绪看板；
- 天气建议；
- 热点新闻；
- 高德 MCP 工具封装。

当前代码中未发现以下实现：

- 用户注册、登录和 `user_id` 体系；
- MySQL / PostgreSQL 生产数据库配置；
- LangChain / LangGraph；
- BM25 + 向量混合召回；
- 文档上传型知识库；
- PDF / DOCX / Markdown 文件解析；
- 文件 MD5 去重；
- 文件删除与向量库同步生命周期；
- Docker 部署文件；
- 后端 `requirements.txt`；
- 完整自动化测试。

## 常见问题

### 1. 前端请求后端失败怎么办？

检查：

1. 后端是否启动在 `http://localhost:8000`；
2. 前端 `.env` 中 `VITE_API_BASE_URL` 是否正确；
3. 后端 `.env` 中 `CORS_ORIGINS` 是否包含前端地址；
4. 浏览器控制台是否有跨域错误。

### 2. 聊天接口报错怎么办？

优先检查：

1. LLM API Key 是否配置；
2. `LLM_BASE_URL` 和 `LLM_MODEL_ID` 是否匹配你的模型服务；
3. `hello_agents` 是否安装成功；
4. 后端终端是否有模型调用异常。

### 3. RAG / ChromaDB 报错怎么办？

检查：

1. 是否安装 `chromadb`；
2. 是否安装 `dashscope`；
3. Embedding 所需 API Key 是否可用；
4. `backend/chroma_db/` 是否有写入权限。

### 4. 天气组件不可用怎么办？

检查：

1. `AMAP_API_KEY` 是否配置；
2. 是否安装 `uv`，并能使用 `uvx`；
3. 高德 MCP server 是否可以正常拉起；
4. 如果只是想测试聊天功能，可以先忽略天气组件。

### 5. 新闻组件不可用怎么办？

检查 `NEWS_API_KEY` 是否配置为阿里云市场新闻 API 的 AppCode。未配置时接口会返回服务不可用。

### 6. 上传 GitHub 前需要注意什么？

不要提交真实密钥、本地数据库、向量库和 `node_modules`。建议新增 `.gitignore` 和 `.env.example`。

## 后续优化方向

- 增加用户体系：支持注册登录、用户级会话隔离、用户级 RAG 检索过滤。
- 数据库升级：将 SQLite 替换为 MySQL 或 PostgreSQL，并引入 Alembic 迁移。
- 工程化：补充 `requirements.txt`、Dockerfile、自动化测试和统一日志。
- RAG 优化：增加 metadata filter、rerank、BM25 混合召回和记忆管理界面。
- 知识库扩展：支持文件上传、解析、分块、去重、删除同步。
- 稳定性：增加 LLM 重试、超时控制、异步任务队列和向量索引补偿机制。
- 产品化：增加回答评价、心情报告、用户反馈、管理后台和数据看板。

## 适合展示的项目亮点

- 完成了从前端聊天交互到后端 Agent 编排的完整 AI 应用链路。
- 使用短期上下文、中期摘要、长期向量记忆解决多轮对话记忆问题。
- 通过轻量 ReAct-like 工具调用机制，让 Agent 自主决定是否检索历史记忆。
- 基于 ChromaDB 和 DashScope Embedding 实现长期语义记忆检索。
- 使用 SSE 实现流式聊天，提升大模型回复体验。
- 将用户对话转化为心情分数、关键词和心情日记，实现情绪数据沉淀。
- 接入天气和新闻能力，让 AI 应用具备更完整的产品交互入口。

