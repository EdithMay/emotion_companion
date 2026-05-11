# PROJECT_ANALYSIS.md

## 1. 项目概述

这个项目是一个面向情绪陪伴与心情记录场景的 AI 应用，产品名在代码中配置为“树洞”。它解决的问题不是简单问答，而是让用户可以在多轮对话中倾诉、被陪伴，并把对话沉淀为心情日记、长期记忆和可回溯的情绪趋势。

项目的核心功能包括：多会话聊天、三种陪伴人设、流式 AI 回复、会话短期上下文、中期摘要记忆、基于 ChromaDB 的长期语义记忆检索、每日心情总结、心情日历、近 7 天趋势、关键词云、天气建议和热点新闻话题引入。用户的典型流程是：进入前端页面，创建或选择一个会话，选择陪伴风格，输入消息；后端保存用户消息并构建 Prompt，必要时由 Agent 主动检索历史记忆，再调用 LLM 生成回复；用户可以点击“今日总结”把当天对话分析为心情记录，并在右侧面板查看日历、趋势和关键词。

这个项目适合投递 AI 应用开发实习、LLM 应用开发实习、Python 后端实习、RAG 工程实习、AIGC 产品研发实习、智能体应用开发实习、前后端联调方向实习。它最值得向面试官介绍的亮点是：我不是只做了一个 LLM 聊天壳，而是围绕真实产品体验实现了“对话、记忆、情绪总结、主动关怀、工具调用、流式输出、前后端状态同步”的完整闭环。

技术选择都对应实际问题：FastAPI 负责清晰地暴露 REST 和 SSE 接口；SQLAlchemy + SQLite 负责会话、消息和心情记录的结构化持久化；ChromaDB + DashScope Embedding 负责语义记忆检索；HelloAgentsLLM 统一封装大模型调用；Vue3 + TypeScript 负责构建可交互聊天界面和情绪看板；高德 MCP 和新闻 API 负责把天气、热点等外部信息接入产品侧栏。

## 2. 技术栈与个人职责

| 技术/框架 | 在项目中的作用 | 为什么选择它 | 我的工作 |
|---|---|---|---|
| Python | 后端主体语言，承载 FastAPI、SQLAlchemy、Agent、RAG、LLM 调用等逻辑 | 生态适合 AI 应用开发，LLM、向量库、Web 后端库都成熟 | 作为主要开发者实现后端路由、服务层、Agent、记忆压缩、心情总结和外部 API 封装 |
| FastAPI | 在 `backend/app/api/main.py` 中创建应用，在 `routes` 下拆分聊天、心情、记忆、天气、新闻接口 | 自动参数校验、文档生成、依赖注入适合接口型 AI 应用 | 设计 `/api/chat`、`/api/mood`、`/api/memory`、`/api/weather`、`/api/news` 路由 |
| Pydantic | `backend/app/models/schemas.py` 定义请求和响应结构 | 让接口输入输出更清晰，减少前后端字段不一致 | 定义 `MessageCreate`、`ChatResponse`、`MoodEntryOut`、`WeatherResponse`、`NewsResponse` 等 Schema |
| SQLAlchemy | `backend/app/models/db_models.py` 定义 ORM 模型，`database.py` 管理连接和 Session | 结构化数据适合用关系模型表达，便于查询会话和消息 | 实现 `Conversation`、`Message`、`MemorySummary`、`MoodEntry`、`PersonaConfig` 表 |
| SQLite | `backend/emotion.db` 存储会话、消息、摘要、心情记录、人设配置 | 本地开发部署简单，适合原型和实习项目展示 | 使用 SQLite 完成核心业务数据持久化；当前代码中未发现 MySQL 连接实现 |
| MySQL | 当前代码中未发现该技术实现 | 如果上线多用户生产环境，可替换 SQLite | 当前未实现，可作为优化方向 |
| LangChain | 当前代码中未发现该技术实现 | 项目没有直接使用 LangChain Agent/Chain | 当前未实现；项目采用自定义 `CompanionAgent` + `HelloAgentsLLM` |
| LangGraph | 当前代码中未发现该技术实现 | 项目没有状态图或节点编排代码 | 当前未实现；可作为复杂多 Agent 流程优化方向 |
| ReAct Agent | 当前代码中没有标准 LangChain ReAct 实现，但 `CompanionAgent` 实现了“LLM 先判断是否调用工具，再执行工具，再二次生成”的 ReAct-like 流程 | 相比固定 if-else，允许模型根据语义决定是否检索历史记忆 | 实现 `MEMORY_TOOL_DESC`、`_parse_tool_call()`、`_execute_search_memory()` 的工具调用闭环 |
| RAG | `backend/app/services/rag_service.py` 实现长期记忆索引与检索 | 用语义检索召回历史心情、摘要和用户消息，帮助 Agent 记住过去 | 实现 `index()`、`search()`、`format_for_prompt()`、`delete_by_date()` |
| ChromaDB | 本地持久化向量库，路径为 `backend/chroma_db`，集合名 `emotion_memories` | 轻量、易本地运行，适合语义记忆和原型验证 | 设计长期记忆写入和相似度过滤，使用 cosine 空间 |
| DashScope Embedding | `RAGService._get_embedding()` 调用 `text-embedding-v4`，维度 1024 | 不需要本地部署模型，适合快速构建语义检索 | 将心情日记、记忆摘要、有价值用户消息向量化写入 ChromaDB |
| BM25 | 当前代码中未发现该技术实现 | 当前只实现向量检索，没有关键词倒排检索 | 未实现；可作为专业术语、精确关键词召回的优化方向 |
| HelloAgentsLLM | `backend/app/services/llm_service.py` 封装 LLM 单例 | 统一处理模型 provider、model、timeout 和调用入口 | 用 `get_llm()` 为 Agent、摘要、天气建议提供统一 LLM 能力 |
| DashScope API / OpenAI-compatible API | Embedding 使用 DashScope；LLM 配置从 `LLM_API_KEY`、`OPENAI_API_KEY`、`LLM_MODEL_ID` 等环境变量读取 | 便于切换模型供应商和部署环境 | 封装配置读取和模型调用入口 |
| StreamingResponse / SSE | `POST /api/chat/message/stream` 使用 `StreamingResponse` 返回 `text/event-stream` | 聊天场景需要边生成边展示，降低等待感 | 实现 `[START]`、`[USER_MSG]`、`[TOOL_USING]`、token、`[DONE]`、`[ERROR]` 事件协议 |
| Vue3 | 前端主体框架，入口为 `frontend/src/main.ts`、`App.vue` | 组件化适合聊天页、侧栏、情绪面板拆分 | 实现聊天界面、会话侧栏、天气组件、热点组件、心情面板 |
| TypeScript | `frontend/src/types/index.ts` 定义前端接口类型 | 强化前后端字段约束，减少调用错误 | 为 Conversation、Message、Mood、Weather、News 定义类型 |
| axios | `frontend/src/services/api.ts` 封装普通 REST 请求 | 请求简洁，有拦截器，适合非流式接口 | 封装会话、心情、天气、新闻、记忆接口 |
| fetch + ReadableStream | `sendMessageStream()` 消费 SSE 流式接口 | axios 不适合直接逐 chunk 读取 SSE token | 实现前端逐 token 追加 AI 回复 |
| ant-design-vue | 前端按钮、输入框、弹窗、标签、折叠面板等 UI 组件 | 快速构建稳定的交互控件 | 在聊天输入、心情弹窗、标签、按钮等场景使用 |
| marked | `MessageBubble.vue` 将助手回复渲染为 Markdown | 支持 AI 回复中的基础格式展示 | 用户消息做转义，助手消息用 `marked.parse()` |
| ECharts | `package.json` 中有依赖，但当前源码中未发现实际使用 | 可用于后续趋势图或数据看板 | 当前代码中未发现实际图表实现 |
| Streamlit | 当前代码中未发现该技术实现 | 项目没有 Streamlit 前端 | 当前未实现 |
| 第三方 API / MCP 工具 | `amap_service.py` 使用高德 MCP，`news_service.py` 使用阿里云市场新闻 API | 扩展天气、定位、热点话题能力 | 封装 `AmapService`、`WeatherService`、`NewsService` |

## 3. 项目整体架构

文字版架构图：

```text
用户 / Vue3 前端页面
    ↓
frontend/src/services/api.ts 请求封装
    ↓
FastAPI 路由层 backend/app/api/routes/*
    ↓
业务 Service / Agent 层 backend/app/services 与 backend/app/agents
    ↓
Memory / RAG / Tool / Database 模块
    ↓
LLM / Embedding / ChromaDB / SQLite / 高德 MCP / 新闻 API
```

前端负责页面交互、会话选择、消息展示、流式 token 追加、心情日历和侧栏工具展示。`ChatView.vue` 负责核心聊天，`ConversationSidebar.vue` 负责会话列表和人设切换，`MoodPanel.vue` 负责心情日历与总结入口，`WeatherWidget.vue` 和 `HotTopicCard.vue` 负责外部信息展示。

后端负责业务规则和数据持久化。路由层位于 `backend/app/api/routes`，主要做参数接收、Pydantic 校验、数据库 Session 注入、异常转 HTTP 状态码，不直接承载复杂业务。Service 层位于 `backend/app/services`，负责 LLM、RAG、记忆压缩、心情总结、天气、新闻等业务逻辑。Agent 模块位于 `backend/app/agents/companion_agent.py`，负责把会话记忆、Prompt、人设、工具调用和流式输出组织成完整链路。

Schema / Model 层分别负责接口数据结构和数据库表结构。`schemas.py` 用于前后端接口契约，`db_models.py` 用于 SQLAlchemy ORM。Database 层 `database.py` 统一管理 SQLite 路径、engine、Session 和初始化建表。RAG 模块负责把心情日记、用户消息、摘要记忆写入 ChromaDB，并按语义召回。Tool 模块当前主要体现在两部分：Agent 内部的 `search_memory` 工具，以及 `amap_service.py` 封装的高德 MCP 工具。Memory 模块负责短期最近消息和中期摘要压缩。第三方 API 模块负责天气、定位反查和新闻拉取。

采用这种分层架构的原因是：路由层只关心 HTTP，业务层关心流程，模型层关心数据结构，Agent/RAG 层关心 AI 能力。这样在面试中可以清楚说明“请求如何进来、业务在哪里处理、数据如何保存、AI 如何调用”，也方便未来替换模型、切换数据库、增加新工具或做单元测试。

## 4. 目录结构与文件职责

真实核心目录结构如下，已忽略 `frontend/node_modules`、`backend/chroma_db` 二进制索引和 `__pycache__`：

```text
emotion_companion/
├── main.py
├── emotion_companion_project_spec.md
├── backend/
│   ├── run.py
│   ├── test.py
│   ├── emotion.db
│   ├── chroma_db/
│   └── app/
│       ├── config.py
│       ├── database.py
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
│       └── services/
│           ├── amap_service.py
│           ├── llm_service.py
│           ├── memory_service.py
│           ├── news_service.py
│           ├── rag_service.py
│           ├── summary_service.py
│           └── weather_service.py
└── frontend/
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── App.vue
        ├── main.ts
        ├── router/index.ts
        ├── services/api.ts
        ├── stores/appStore.ts
        ├── types/index.ts
        ├── views/
        │   ├── ChatView.vue
        │   └── MoodBoard.vue
        └── components/
            ├── ConversationSidebar.vue
            ├── HotTopicCard.vue
            ├── MessageBubble.vue
            ├── MoodPanel.vue
            └── WeatherWidget.vue
```

### 4.1 目录职责说明

`backend/app/api` 是后端 HTTP 入口，负责创建 FastAPI 应用、配置 CORS、注册模块路由和启动时初始化数据库。拆出来的好处是接口层清晰，业务不会散落在应用入口里。

`backend/app/api/routes` 按功能拆分路由：聊天、记忆、心情、天气、新闻。这样面试官问“为什么这样设计路由”时，可以回答：每个路由文件对应一个产品能力，接口职责稳定，新增知识库或用户模块时可以独立扩展。

`backend/app/services` 是业务服务层。它把 LLM 调用、RAG、记忆压缩、心情分析、天气和新闻封装成可复用函数或类，让路由层保持薄。比如 `summary_service.py` 同时被心情路由和 RAG 索引逻辑关联，`memory_service.py` 被 Agent 调用。

`backend/app/agents` 是智能体编排层。`CompanionAgent` 不只是调用 LLM，而是组织“保存消息、压缩记忆、构建 Prompt、判断工具调用、执行检索、流式输出、保存回复、写入长期记忆”的完整链路。

`backend/app/models` 分为 ORM 模型和 Pydantic Schema。数据库模型描述表结构，Schema 描述接口结构，这种拆分避免把数据库内部字段直接暴露给前端。

`frontend/src/services` 是前端请求层，所有后端接口统一在 `api.ts` 中封装。页面组件只调用函数，不直接拼 URL，有利于后续统一加 token、错误处理或切换 base URL。

`frontend/src/components` 是可复用 UI 组件，比如消息气泡、侧栏、天气、热点、心情面板。`frontend/src/views` 是页面级视图，目前核心页面是聊天页和心情看板。

当前代码中未发现独立的 `tools/`、`memory/`、`rag/` 目录；相关能力分别集中在 `services/rag_service.py`、`services/memory_service.py` 和 `agents/companion_agent.py` 中。这种结构对当前项目规模是合理的，但如果后续工具增多，可以再拆出 `tools` 包。

### 4.2 核心文件职责说明

| 文件路径 | 核心职责 | 被谁调用 | 调用了谁 | 为什么这样拆分 |
|---|---|---|---|---|
| `backend/run.py` | 使用 uvicorn 启动 `app.api.main:app` | 开发者启动后端 | `app.config.get_settings()` | 把运行入口和 FastAPI 应用定义分开 |
| `backend/app/api/main.py` | 创建 FastAPI app、配置 CORS、注册路由、startup 初始化数据库 | uvicorn | `init_db()`、各 route router | 应用级配置集中管理 |
| `backend/app/api/routes/chat.py` | 会话 CRUD、消息查询、非流式聊天、流式聊天 | 前端 `api.ts` | `get_db()`、`get_companion_agent()`、`Conversation`、`Message` | 聊天相关接口集中，便于维护 |
| `backend/app/api/routes/mood.py` | 心情总结、心情记录列表、日历、按日期查询 | `MoodPanel.vue`、`api.ts` | `summary_service.py`、`MoodEntry` | 心情记录是独立业务域，单独拆路由 |
| `backend/app/api/routes/memory.py` | 查询会话记忆摘要和最新摘要 | 前端 `getMemory()`，当前页面中未明显使用 | `get_latest_summary()`、`MemorySummary` | 让记忆可被独立调试和展示 |
| `backend/app/api/routes/weather.py` | 查询天气和 LLM 建议 | `WeatherWidget.vue` | `WeatherService` | 天气属于侧栏工具，不混入聊天路由 |
| `backend/app/api/routes/news.py` | 查询热点新闻 | `HotTopicCard.vue` | `NewsService` | 热点话题独立接口，便于替换数据源 |
| `backend/app/agents/companion_agent.py` | 核心 Agent，构建 Prompt、工具调用、流式输出、保存消息、写入 RAG | `chat.py` | `llm_service`、`memory_service`、`rag_service`、数据库模型 | AI 编排复杂，独立于路由层 |
| `backend/app/services/memory_service.py` | 最近消息、全部消息、保存消息、摘要压缩 | `CompanionAgent`、`memory.py` | `Message`、`MemorySummary`、`get_llm()` | 记忆读写和压缩策略可复用 |
| `backend/app/services/rag_service.py` | ChromaDB 初始化、Embedding、索引、检索、格式化 Prompt | `CompanionAgent`、`summary_service.py` | DashScope、ChromaDB、`RAGResult` | 长期语义记忆单独封装，便于替换向量库 |
| `backend/app/services/summary_service.py` | 每日心情总结、JSON 解析、MoodEntry upsert、写入 RAG | `mood.py` | `get_llm()`、`get_rag_service()`、`MoodEntry`、`Message` | 情绪分析流程独立于聊天流程 |
| `backend/app/services/llm_service.py` | 创建 `HelloAgentsLLM` 单例 | Agent、记忆压缩、心情总结、天气建议 | `HelloAgentsLLM`、`get_settings()` | 统一 LLM 初始化，避免散落创建 |
| `backend/app/services/amap_service.py` | 高德 MCP 工具封装，包含天气、POI、路线、地理编码方法 | `WeatherService` | `MCPTool` | 第三方工具封装，降低业务层耦合 |
| `backend/app/services/weather_service.py` | 经纬度反查城市、天气解析、缓存、LLM 生成建议 | `weather.py` | `AmapService`、`get_llm()` | 天气业务比路由复杂，放入服务层 |
| `backend/app/services/news_service.py` | 通过阿里云市场新闻 API 拉取热点 | `news.py` | `requests`、`NewsItem` | 新闻源可替换，接口层不关心细节 |
| `backend/app/models/db_models.py` | 定义 `Conversation`、`Message`、`MemorySummary`、`MoodEntry`、`PersonaConfig` | 数据库初始化、路由、服务 | SQLAlchemy `Base` | 数据表结构集中，便于迁移和说明 |
| `backend/app/models/schemas.py` | 定义接口请求/响应模型 | 路由、服务、前端类型参考 | Pydantic | 接口契约清晰，减少隐式字段 |
| `backend/app/database.py` | SQLite engine、Session、建表、默认人设插入 | `api/main.py`、路由依赖 | SQLAlchemy、`PersonaConfig` | 统一数据库生命周期 |
| `frontend/src/services/api.ts` | 前端 API 封装，包含 axios 和 SSE fetch | 所有前端页面/组件 | 后端接口 | 页面不直接拼接口，便于联调 |
| `frontend/src/views/ChatView.vue` | 聊天主界面，加载历史消息，发送流式消息并逐 token 渲染 | `App.vue` 路由出口 | `getMessages()`、`sendMessageStream()` | 页面级状态集中 |
| `frontend/src/components/ConversationSidebar.vue` | 会话列表、新建/删除会话、人设切换、天气和热点入口 | `App.vue` | `getConversations()`、`createConversation()`、`updateConversation()` | 左侧业务操作集中 |
| `frontend/src/components/MoodPanel.vue` | 今日总结、月历、近 7 天趋势、关键词云、详情弹窗 | `App.vue` | 心情相关 API | 情绪数据展示独立复用 |
| `frontend/src/types/index.ts` | 前端类型定义 | `api.ts` 和组件 | 无 | 和后端 Schema 对齐，增强类型安全 |

面试口述回答可以这样说：我按“接口入口、业务服务、AI 编排、数据模型、前端请求、前端组件”拆文件。路由只做 HTTP 和校验，复杂逻辑放到 service 或 agent，这样每个文件都围绕单一职责，后续新增工具、换模型、换数据库时不会影响所有接口。

## 5. 路由设计与接口说明

| 功能模块 | 请求方法 | 请求路径 | 请求参数 | 返回结果 | 调用的 Service/函数 | 涉及的数据表/数据库 | 设计原因 |
|---|---|---|---|---|---|---|---|
| 应用健康 | GET | `/` | 无 | `{name, version, status}` | 无 | 无 | 根路径用于快速确认服务运行 |
| 应用健康 | GET | `/health` | 无 | `{status, service}` | 无 | 无 | 健康检查适合 GET |
| 会话列表 | GET | `/api/chat/conversations` | 无 | `list[ConversationOut]` | 直接查询 ORM | SQLite `conversations` | 读取资源用 GET |
| 创建会话 | POST | `/api/chat/conversations` | `ConversationCreate{title, persona}` | `ConversationOut` | 直接创建 ORM | SQLite `conversations` | 创建资源用 POST |
| 更新会话 | PATCH | `/api/chat/conversations/{conversation_id}` | path `conversation_id`，body `ConversationCreate` | `ConversationOut` | 直接更新 ORM | SQLite `conversations` | 局部更新标题/人设用 PATCH；当前代码未使用 PUT |
| 删除会话 | DELETE | `/api/chat/conversations/{conversation_id}` | path `conversation_id` | `{success, message}` | 直接删除 ORM | SQLite `conversations`、级联 `messages`、`memory_summaries` | 删除资源用 DELETE |
| 消息历史 | GET | `/api/chat/conversations/{conversation_id}/messages` | path `conversation_id` | `list[MessageOut]` | 直接查询 ORM | SQLite `messages` | 历史消息是只读查询 |
| 非流式聊天 | POST | `/api/chat/message` | `MessageCreate{conversation_id, content}` | `ChatResponse` | `CompanionAgent.chat()` | SQLite、ChromaDB、LLM | 发送消息会产生副作用，必须 POST |
| 流式聊天 | POST | `/api/chat/message/stream` | `MessageCreate{conversation_id, content}` | `text/event-stream` | `CompanionAgent.stream_chat()` | SQLite、ChromaDB、LLM | 聊天需要传 body 并写库，使用 POST + SSE |
| 聊天健康 | GET | `/api/chat/health` | 无 | `{status, service, rag_count}` | `agent.rag.count()` | ChromaDB | 查看 Agent 和 RAG 状态 |
| 记忆列表 | GET | `/api/memory/{conversation_id}` | path `conversation_id` | `list[MemorySummaryOut]` | 直接查询 ORM | SQLite `memory_summaries` | 查询会话摘要 |
| 最新记忆 | GET | `/api/memory/{conversation_id}/latest` | path `conversation_id` | `{conversation_id, summary, has_summary}` | `get_latest_summary()` | SQLite `memory_summaries` | 方便调试最新摘要注入 |
| 生成心情总结 | POST | `/api/mood/summary` | `MoodSummaryRequest{date?}` | `MoodSummaryResponse` | `generate_mood_summary()` | SQLite `messages`、`mood_entries`，ChromaDB | 会触发 LLM 分析和写库，用 POST |
| 心情记录列表 | GET | `/api/mood/entries` | 无 | `list[MoodEntryOut]` | `get_all_mood_entries()` | SQLite `mood_entries` | 心情面板加载全部记录 |
| 心情日历 | GET | `/api/mood/entries/calendar` | query `year, month` | `list[MoodCalendarItem]` | 直接查询 `MoodEntry` | SQLite `mood_entries` | 月历只读查询，用 GET query |
| 按日期查心情 | GET | `/api/mood/entries/{entry_date}` | path `entry_date` | `MoodEntryOut` | `get_mood_entry_by_date()` | SQLite `mood_entries` | 点击日历格子查看详情 |
| 天气查询 | GET | `/api/weather` | query `city` 或 `lat,lng` | `WeatherResponse` | `WeatherService` | 高德 MCP、LLM、内存缓存 | 查询外部数据，不修改资源，用 GET |
| 新闻查询 | GET | `/api/news` | query `category, limit` | `NewsResponse` | `NewsService.get_hot_news()` | 阿里云市场新闻 API | 查询热点列表，用 GET |

GET 用于读取资源或查询第三方数据，POST 用于创建资源或触发会写入数据库/调用 LLM 的流程，PATCH 用于局部修改会话标题和人设，DELETE 用于删除会话。当前代码中未发现 PUT 接口。

聊天、心情、记忆、天气、新闻拆成不同路由，是因为它们对应不同业务边界：聊天是核心 Agent 链路，心情是分析沉淀，记忆是摘要查询，天气和新闻是侧栏工具。路由层不直接写复杂业务逻辑，是为了让 HTTP 层保持稳定，避免 LLM、RAG、数据库操作混在路由函数里导致难测试难维护。

参数接收主要通过 FastAPI 的 path/query/body 自动解析完成。body 使用 Pydantic Schema，如 `MessageCreate` 会要求 `conversation_id: int` 和 `content: str`；响应通过 `response_model` 约束，如 `ChatResponse`、`MoodSummaryResponse`。CORS 在 `backend/app/api/main.py` 中通过 `CORSMiddleware` 配置，允许 `settings.get_cors_origins_list()` 中的前端地址访问，默认包含 `http://localhost:5173` 和 `http://127.0.0.1:5173`，这是因为 Vite 前端和 FastAPI 后端运行在不同端口。

流式响应使用 `StreamingResponse`，media type 为 `text/event-stream`。后端生成器按照 SSE 格式 `data: ...\n\n` 输出，前端 `sendMessageStream()` 用 `fetch()` 读取 `response.body.getReader()`，再用 `TextDecoder` 逐块解析。流式响应适合聊天，因为用户不需要等完整回答结束，可以边看边感知模型正在工作。

## 6. 核心业务流程与实现原理

### 6.1 多轮对话流程

流程图：

```text
用户输入
  ↓
ChatView.vue 调用 sendMessageStream()
  ↓
fetch POST /api/chat/message/stream
  ↓
FastAPI chat.py 接收 MessageCreate
  ↓
Pydantic 校验 conversation_id 和 content
  ↓
查询 Conversation 确认会话存在
  ↓
CompanionAgent.stream_chat()
  ↓
save_message() 保存用户消息
  ↓
check_and_compress() 检查是否压缩历史消息
  ↓
_build_prompt() 读取人设、最近消息、最新摘要、关怀指令
  ↓
LLM 第一次调用，判断是否需要 search_memory
  ↓
可选：RAG 检索历史记忆，二次调用 LLM
  ↓
SSE token 返回前端逐步渲染
  ↓
save_message() 保存 assistant 回复
  ↓
有价值用户消息写入 ChromaDB
  ↓
[DONE] 返回真实 assistant message id
```

前端请求体来自 `frontend/src/services/api.ts` 的 `MessageCreate`：

```json
{
  "conversation_id": 1,
  "content": "今天有点难受，想聊聊"
}
```

当前代码中没有 `user_id` 字段，也没有显式 `session_id` 字段。项目用 `conversation_id` 承担会话隔离作用：不同会话的消息通过 `messages.conversation_id` 关联到 `conversations.id`。如果面试官问 user_id 和 session_id，可以说明当前单机版本没有用户体系，`conversation_id` 相当于 session_id；未来多用户版本需要新增 `users` 表，并在 `conversations` 表增加 `user_id` 外键，才能实现不同用户之间的隔离。

后端路由 `send_message_stream()` 位于 `backend/app/api/routes/chat.py`。它先根据 `body.conversation_id` 查询 `Conversation`，不存在则抛出 404；存在则获取 `get_companion_agent()` 单例，并返回 `StreamingResponse(event_stream(), media_type="text/event-stream")`。

历史会话读取分两层：短期记忆由 `get_recent_messages(db, conversation_id, limit=5)` 获取最近 5 条消息；中期记忆由 `get_latest_summary(db, conversation_id)` 获取最新摘要。`_build_prompt()` 把人设 Prompt、工具描述、连续低分关怀指令、会话摘要、最近消息和当前用户消息组合成 messages 列表传给 LLM。

消息保存由 `memory_service.save_message()` 完成。用户消息在调用 LLM 前保存，assistant 回复在流式输出完成后保存。这样即使 LLM 中途失败，至少能保留用户输入；如果保存 assistant 失败，后端会通过 `[ERROR]` SSE 事件通知前端。

上下文隔离目前基于 `conversation_id`：查询最近消息、保存消息、压缩摘要都带着 `conversation_id`。但长期 RAG 检索目前 `rag.search(query, top_k=3)` 没有按 `conversation_id` 做 where 过滤，只是 metadata 中保存了 `conversation_id`。这意味着长期记忆可能跨会话召回，是情绪陪伴产品中的一种“用户全局记忆”设计；如果要严格按会话隔离，需要在 `RAGService.search()` 中增加 metadata filter。

### 6.2 RAG 检索增强流程

当前项目包含 RAG，但它不是文档知识库上传型 RAG，而是“长期情绪记忆 RAG”。当前代码中未发现 PDF/TXT/Markdown/DOCX 上传接口，未发现文件保存、文本切片、chunk_size、overlap、文件删除、知识库文件生命周期实现。

已实现的 RAG 流程如下：

1. 写入来源一：`summary_service.generate_mood_summary()` 生成心情日记后，调用 `_index_to_rag()`，先 `rag.delete_by_date(target_date)` 删除当天旧索引，再 `rag.index()` 写入新的心情总结。
2. 写入来源二：`CompanionAgent.stream_chat()` 中 `check_and_compress()` 触发摘要压缩后，会把最新 `MemorySummary` 写入 ChromaDB。
3. 写入来源三：每次用户消息有实质内容时，`CompanionAgent._is_meaningful()` 返回 True，用户消息会通过 `rag.index()` 写入长期记忆。
4. 检索触发：Agent 第一次 LLM 调用可能输出 `[TOOL_CALL:search_memory:query=...]`，`_parse_tool_call()` 解析后调用 `_execute_search_memory()`。
5. 检索执行：`RAGService.search(query, top_k=3)` 调用 DashScope `text-embedding-v4` 得到 1024 维向量，再查 ChromaDB `emotion_memories` 集合。
6. 结果过滤：ChromaDB 返回 cosine distance，代码用 `similarity = 1 - dist` 转成相似度，并过滤 `similarity < 0.6` 的结果。
7. Prompt 注入：`format_for_prompt()` 把结果格式化为短文本，截断超过 150 字的片段，再作为“工具返回结果”追加到 messages 中进行第二次 LLM 调用。

为什么要 RAG：情绪陪伴类 Agent 不能只依赖当前几条消息，否则无法体现“记得你之前说过什么”。把心情日记、摘要和重要消息向量化后，模型可以在用户提到“上次那件事”“你还记得吗”时召回相关历史，减少凭空编造。

检索结果为空时，`_execute_search_memory()` 返回“未找到与该话题相关的历史记忆”之类的提示，后续 LLM 会基于当前对话正常回复。RAG 写入失败和检索失败都被捕获并返回 False 或空列表，不会阻断主聊天流程。

BM25 + 向量混合召回：当前代码中未发现 BM25 实现，也没有倒排索引、关键词分词、结果合并或去重逻辑。如果要优化，可以引入 `rank_bm25` 或 Elasticsearch/OpenSearch：BM25 适合精确关键词、专有名词、故障码召回；向量检索适合理解语义相近表达；混合召回可以先分别取 Top-K，再按归一化分数加权、按文档 ID 去重，最后重排。

### 6.3 Agent 与 Tool 调用机制

项目没有使用 LangChain Agent，也没有标准 ReAct 框架类；当前实现是自定义 ReAct-like Agent。它的核心思想是：不是后端固定判断每句话都检索，而是把 `search_memory` 工具说明写进系统 Prompt，让 LLM 先根据用户意图决定是否输出工具调用指令，再由后端解析并执行工具。

项目中定义的 Tool：

| Tool | 定义位置 | 输入参数 | 输出结果 | 作用 |
|---|---|---|---|---|
| `search_memory` | `backend/app/agents/companion_agent.py` 的 `MEMORY_TOOL_DESC`、`_parse_tool_call()`、`_execute_search_memory()` | `query` 字符串 | 格式化后的 RAG 历史记忆文本 | 让 Agent 主动检索用户过往对话、心情日记和摘要 |
| 高德 MCP 工具集 | `backend/app/services/amap_service.py` | 由 `MCPTool.run()` 传入 tool_name 和 arguments | MCP 返回字符串 | 支持天气、逆地理编码、POI、路线等；当前主要被天气服务使用 |

ReAct 中 Thought、Action、Observation、Final Answer 可以映射为当前项目的流程：Thought 是 LLM 第一次根据 Prompt 判断是否需要记忆；Action 是输出 `[TOOL_CALL:search_memory:query=...]`；Observation 是 `_execute_search_memory()` 返回的历史记忆；Final Answer 是第二次 LLM 基于工具结果生成最终回复。代码没有显式保存 Thought 字段，这是出于产品体验考虑，不把内部推理暴露给用户。

为什么不直接写 if-else：用户表达“你还记得我上次说的那个同事吗”可以触发检索，但真实语言非常多样，固定关键词规则容易漏召回或误召回。让模型根据语义决定是否调用工具，可以减少无意义检索，也更容易扩展新工具。新增 Tool 的典型改动是：在 `MEMORY_TOOL_DESC` 或新的工具描述中加入工具名、用途、调用格式；增加 `_parse_xxx_tool_call()` 和 `_execute_xxx()`；在 `stream_chat()`/`chat()` 中加入分支；如有外部能力，再在 `services` 下封装对应服务。

工具调用错误处理：`_execute_search_memory()` 捕获异常，返回“记忆检索暂时不可用”类文本；这样 LLM 仍然能继续回复。高德 MCP 和新闻 API 则在 service 层抛出或返回空结果，由路由层转成 4xx/5xx。

### 6.4 记忆系统设计

项目实现了短期、中期、长期三层记忆：

短期记忆：`messages` 表中最近 5 条消息，由 `get_recent_messages(limit=5)` 读取，直接作为 role/content 列表放进 Prompt。它保留最近上下文，保证多轮对话连贯。

中期记忆：当某个会话消息数超过 `COMPRESS_THRESHOLD = 20` 时，`check_and_compress()` 会取最早 `COMPRESS_BATCH = 15` 条消息，调用 `_compress_messages()` 让 LLM 压缩成 200 字以内摘要，保存到 `memory_summaries` 表，然后删除这 15 条原始消息。最新摘要由 `get_latest_summary()` 注入 Prompt。

长期记忆：心情日记、压缩摘要、有价值用户消息会写入 ChromaDB。对话时，Agent 可通过 `search_memory` 工具按语义召回长期记忆，再把结果注入第二次 LLM 调用。

不能把所有历史消息都直接放进 Prompt 的原因是：上下文窗口有限，历史越长成本越高，且大量旧消息会稀释当前问题重点。当前设计用“最近 5 条原文 + 中期摘要 + 必要时长期检索”的方式，兼顾连续性、成本和相关性。

在情绪陪伴类 Agent 中，记忆系统的价值是增强关系感。用户不只是得到一次回答，而是能感觉系统理解自己长期的情绪背景。当前代码避免记忆污染的措施包括：`_is_meaningful()` 过滤短语气词，RAG 检索设置相似度阈值 0.6，工具描述要求结果不相关时忽略。但当前未实现用户手动删除/纠正记忆，也未实现 RAG 按用户隔离，这是后续优化点。

### 6.5 情绪分析与主动关怀逻辑

用户心情数据通过 `POST /api/mood/summary` 触发生成。`summary_service.generate_mood_summary()` 会读取指定日期的所有消息，只取 `role == "user"` 的内容交给 LLM 分析，避免把助手自己的回复算入用户情绪。LLM 被要求返回 JSON：

```json
{
  "score": 7,
  "keywords": ["工作压力", "有些疲惫", "期待周末"],
  "summary": "今日心情总结文本"
}
```

代码会解析 JSON，限制 `score` 在 1-10 之间，保证 `keywords` 是列表。如果 JSON 解析失败，则降级为默认 score 5、默认关键词和默认总结。结果通过 `_upsert_mood_entry()` 保存到 `mood_entries` 表，同一天多次生成会覆盖更新。`keywords` 和 `conversation_ids` 以 JSON 字符串存储，返回前端前由 `_to_schema()` 反序列化为列表。

前端展示由 `MoodPanel.vue` 完成：`getAllMoodEntries()` 获取全部记录，用于今日心情、近 7 天趋势和关键词云；`getMoodCalendar(year, month)` 获取月历分数；点击日历格子调用 `getMoodEntryByDate(date)` 弹出详情。近 7 天趋势在前端用 `dayjs` 和已有 entries 计算，关键词云用当月所有 `keywords` 统计频次。

主动关怀逻辑位于 `CompanionAgent._check_care_needed()`：检查最近 3 天，也就是昨天、前天、大前天，是否都有心情记录且分数都小于 4。如果满足条件，就在系统 Prompt 中注入特别提示，让 Agent 在对话开头自然关心用户近况。这样做的意义是，情绪陪伴类产品不能只被动回答，还需要在连续低分状态下体现稳定、温和的关怀。

当前代码中未发现自动定时生成心情总结，也未发现主动推送通知；需要用户点击“今日总结”或由前端触发接口。

### 6.6 数据持久化设计

项目使用两类数据库：

| 数据库 | 存储内容 | 代码位置 |
|---|---|---|
| SQLite | 会话、消息、记忆摘要、心情记录、人设配置 | `backend/emotion.db`，模型在 `db_models.py` |
| ChromaDB | 长期语义记忆向量，包括心情日记、摘要、有价值用户消息 | `backend/chroma_db`，服务在 `rag_service.py` |

当前代码中未发现 MySQL 实现。

核心表结构：

| 表 | 字段 | 含义 |
|---|---|---|
| `conversations` | `id`、`title`、`persona`、`created_at`、`updated_at` | 会话基本信息和人设 |
| `messages` | `id`、`conversation_id`、`role`、`content`、`created_at` | 用户和助手消息，按会话隔离 |
| `memory_summaries` | `id`、`conversation_id`、`summary_text`、`message_count`、`created_at` | 压缩后的中期记忆 |
| `mood_entries` | `id`、`date`、`score`、`summary_text`、`keywords`、`conversation_ids`、`updated_at` | 每日心情记录 |
| `persona_config` | `id`、`name`、`display_name`、`avatar_emoji`、`system_prompt` | 三种人设及系统 Prompt |

`conversation_id` 是消息和摘要的会话外键。当前没有 `user_id`、`session_id`、`message_id` 单独暴露概念；数据库中的 `messages.id` 就是 message_id。当前没有 `file_id`，因为未发现文件上传/知识库文件表。

一次聊天请求的数据读写：路由读取 `conversations` 验证会话；Agent 写入用户消息到 `messages`；读取最近消息和最新摘要；可能读取 `mood_entries` 判断连续低分；可能读取 ChromaDB 检索长期记忆；LLM 返回后写入 assistant 消息；最后把有意义的用户消息写入 ChromaDB。

一次文件上传请求：当前代码中未发现该实现。

一致性方面，SQLite 和 ChromaDB 不是事务绑定的。比如心情总结先写 SQLite，再写 ChromaDB；RAG 写入失败不会回滚 SQLite，而是打印警告。这样能保证主流程可用，但可能出现关系库有记录、向量库无索引的情况。优化建议是增加任务状态表、重试队列、一致性校验脚本，或把 RAG 写入设计成异步任务并记录成功/失败状态。

数据库异常处理当前比较基础：部分路由用 try/except 转 HTTPException；`save_message()` 内部没有细粒度回滚处理；`check_and_compress()` 删除原消息和写摘要在同一 Session commit，但 LLM 压缩失败会降级拼接摘要。更稳妥的做法是对数据库写操作加 `try/except db.rollback()`，并统一错误响应格式。

### 6.7 文件上传与知识库生命周期

当前代码中未发现文件上传和知识库文件生命周期实现。具体包括：

- 当前代码中未发现文档上传接口；
- 当前代码中未发现 `UploadFile` 接收逻辑；
- 当前代码中未发现 PDF/TXT/Markdown/DOCX 解析；
- 当前代码中未发现文本切片、`chunk_size`、`overlap`；
- 当前代码中未发现文件元信息表；
- 当前代码中未发现 MD5 去重；
- 当前代码中未发现文件状态管理；
- 当前代码中未发现本地文件删除、数据库记录删除、向量库按文件删除的完整链路。

项目中的 RAG 主要服务于情绪长期记忆，而不是文档知识库。若后续扩展知识库，建议新增 `files` 表保存 `file_id`、文件名、MD5、状态、上传时间、chunk 数；新增 `/api/files/upload`、`/api/files`、`/api/files/{file_id}` 删除接口；向 ChromaDB 写入时 metadata 带 `file_id` 和 `chunk_id`。删除文件时要按顺序处理本地文件、关系库状态、向量库索引，并通过状态补偿避免部分成功导致不一致。

### 6.8 流式响应实现

聊天场景需要流式响应，因为 LLM 生成可能耗时较长，一次性返回会让用户等待空白。当前后端在 `chat.py` 中使用 `StreamingResponse`，实际 token 生成在 `CompanionAgent.stream_chat()`。

后端 SSE 事件包括：

| 事件 | 含义 |
|---|---|
| `data: [START]` | 流开始 |
| `data: [USER_MSG]{...}` | 用户消息已保存，返回真实 id 和 created_at |
| `data: [TOOL_USING]` | Agent 正在检索记忆 |
| `data: "token"` | 普通 token/chunk，JSON 字符串 |
| `data: [DONE]{...}` | assistant 回复保存完成，返回真实 id 和 created_at |
| `data: [ERROR]...` | 出错 |

前端 `sendMessageStream()` 使用 `fetch()`，通过 `reader.read()` 不断读取 chunk，按 `\n\n` 拆分 SSE 事件。`ChatView.vue` 先乐观插入临时用户消息和临时助手消息，收到 token 后把 token 追加到临时助手消息，收到 `[DONE]` 后用服务端真实 id 替换临时 id。

优点是响应快、体验自然、可展示工具调用状态；缺点是实现比普通 JSON 接口复杂，错误处理、断流恢复和最终消息一致性都更难。当前代码中有 `[ERROR]` 事件，但未实现断线重连和中途取消。

## 7. 数据传输与前后端交互

### 7.1 前端到后端

前端 API 调用集中在 `frontend/src/services/api.ts`。普通接口使用 axios：

- `GET /api/chat/conversations`
- `POST /api/chat/conversations`
- `PATCH /api/chat/conversations/{id}`
- `DELETE /api/chat/conversations/{id}`
- `GET /api/chat/conversations/{cid}/messages`
- `POST /api/chat/message`
- `POST /api/mood/summary`
- `GET /api/mood/entries`
- `GET /api/mood/entries/calendar`
- `GET /api/mood/entries/{date}`
- `GET /api/weather`
- `GET /api/news`
- `GET /api/memory/{cid}`

流式聊天单独使用 fetch：

```ts
fetch(`${BASE}/api/chat/message/stream`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ conversation_id: activeId.value, content: text }),
})
```

当前请求没有 token，也没有 user_id。身份与上下文主要靠 `conversation_id`。

### 7.2 后端内部流转

路由层通过 `Depends(get_db)` 获取 SQLAlchemy Session，通过 Pydantic Schema 接收 body，通过 `Query` 接收 query 参数。聊天路由验证会话存在后调用 Agent；心情路由调用 summary service；天气和新闻路由调用各自 service。Service 内部再调用数据库、LLM、RAG 或第三方工具，并返回 Pydantic 对象或普通 dict。

异常处理方式包括：资源不存在抛 404；心情当天无消息抛 400；新闻未配置 AppCode 抛 503；外部 API 报错抛 502 或 500；聊天 Agent 异常抛 500。当前没有全局异常处理中间件，也没有统一 `{code, message, data}` 响应包装。

### 7.3 后端到 LLM / 向量库 / 数据库

LLM 调用统一通过 `get_llm()` 获取 `HelloAgentsLLM`。传入格式是 OpenAI 风格的 messages：

```python
[
  {"role": "system", "content": "...人设和工具描述..."},
  {"role": "system", "content": "...会话摘要..."},
  {"role": "user", "content": "..."},
  {"role": "assistant", "content": "..."},
  {"role": "user", "content": "当前消息"}
]
```

Embedding 调用在 `RAGService._get_embedding()` 中，使用 DashScope `TextEmbedding.call(model="text-embedding-v4", input=text, dimension=1024)`，返回 float list。写入 ChromaDB 时传入 `embeddings`、`documents`、`metadatas`、`ids`；检索时用 `collection.query(query_embeddings=[embedding], n_results=actual_top_k)`。

SQLite 通过 SQLAlchemy ORM 读写。比如保存消息时创建 `Message(conversation_id, role, content)`，`db.add()`、`db.commit()`、`db.refresh()`。心情记录中 `keywords` 和 `conversation_ids` 以 JSON 字符串存储，返回前转为 Python list。

### 7.4 后端到前端

关键接口请求与响应示例：

创建会话：

```json
{
  "title": "5月11日的倾诉",
  "persona": "gentle"
}
```

返回：

```json
{
  "id": 1,
  "title": "5月11日的倾诉",
  "persona": "gentle",
  "created_at": "2026-05-11T10:00:00",
  "updated_at": "2026-05-11T10:00:00"
}
```

发送消息：

```json
{
  "conversation_id": 1,
  "content": "今天被批评了，有点难受"
}
```

非流式返回：

```json
{
  "success": true,
  "message": "回复成功",
  "user_message": {
    "id": 10,
    "conversation_id": 1,
    "role": "user",
    "content": "今天被批评了，有点难受",
    "created_at": "2026-05-11T10:00:00"
  },
  "reply": {
    "id": 11,
    "conversation_id": 1,
    "role": "assistant",
    "content": "AI 回复内容",
    "created_at": "2026-05-11T10:00:02"
  }
}
```

生成心情总结：

```json
{
  "date": "2026-05-11"
}
```

返回：

```json
{
  "success": true,
  "message": "心情小记生成成功",
  "data": {
    "id": 1,
    "date": "2026-05-11",
    "score": 6,
    "summary_text": "今日心情总结文本",
    "keywords": ["工作压力", "疲惫"],
    "conversation_ids": [1],
    "updated_at": "2026-05-11T10:10:00"
  }
}
```

天气返回结构：

```json
{
  "success": true,
  "message": "查询成功",
  "data": {
    "city": "北京",
    "weather": "晴",
    "temperature": "25",
    "wind": "微风",
    "humidity": "50%",
    "suggestions": {
      "travel": "出行建议",
      "food": "饮食建议",
      "clothing": "穿搭建议"
    },
    "cached": false
  }
}
```

前端渲染方式：聊天消息由 `MessageBubble.vue` 渲染，用户消息转义，助手消息用 Markdown；会话列表由 `ConversationSidebar.vue` 渲染；心情数据由 `MoodPanel.vue` 渲染；天气和新闻分别由 `WeatherWidget.vue` 和 `HotTopicCard.vue` 渲染。loading 状态分散在组件内，如 `typing`、`summarizing`、`loading`。错误提示主要使用 `ant-design-vue` 的 `message.error()`。

## 8. Prompt 设计分析

Prompt 主要分布在以下文件：

| Prompt 类型 | 文件 | 变量来源 | 作用 |
|---|---|---|---|
| 人设系统 Prompt | `backend/app/database.py` 默认插入 `PersonaConfig.system_prompt` | 初始化数据库时插入 gentle/rational/humorous | 控制陪伴风格、回复长度、语气、安全边界 |
| 默认系统 Prompt | `CompanionAgent._default_system_prompt()` | 代码固定文本 | 人设读取失败时兜底 |
| 工具调用 Prompt | `CompanionAgent.MEMORY_TOOL_DESC` | 工具名、调用格式、调用标准 | 让 LLM 自主决定是否调用 `search_memory` |
| 多轮上下文 Prompt | `CompanionAgent._build_prompt()` | 最近消息、最新摘要、当前用户消息 | 保持对话连续 |
| RAG 工具结果 Prompt | `CompanionAgent.stream_chat()` 工具分支 | `rag.format_for_prompt(results)` | 把历史记忆作为背景注入第二次 LLM 调用 |
| 记忆压缩 Prompt | `memory_service._compress_messages()` | 被压缩的早期消息 | 生成 200 字以内中期摘要 |
| 心情总结 Prompt | `summary_service._analyze_mood()` | 当天用户消息、日期 | 生成 score、keywords、summary JSON |
| 天气建议 Prompt | `weather_service._generate_suggestions()` | 城市、天气、温度、风、湿度 | 生成 travel/food/clothing JSON |
| 低分关怀 Prompt | `CompanionAgent._check_care_needed()` | 最近 3 天 `MoodEntry.score` | 连续低分时动态注入关怀指令 |

Prompt 组织方式是分层的。第一层 system 是人设、规则和工具说明，保证模型知道自己是谁、能用什么工具、不能做什么；第二层 system 是会话摘要，作为背景；第三层是最近几条消息和当前用户输入。这样能减少 Prompt 漂移，让模型既保持风格，又不会丢掉当前上下文。

RAG 上下文不是每轮强行注入，而是由 Agent 根据工具描述选择调用。这样可以减少无关历史干扰，也降低 token 成本。检索结果注入时明确告诉模型“记忆只是背景参考，不要逐条复述；如果不相关可以忽略”，这是减少幻觉和过度引用历史的重要设计。

如果面试官问“你怎么调 Prompt”，可以这样回答：我不是只改一句系统提示，而是把 Prompt 拆成人设、工具说明、短期上下文、中期摘要、长期检索结果和动态关怀指令。调试时会观察模型是否太像客服、是否过度说教、是否乱用记忆、是否输出不合规格式，然后分别调整回复长度、禁用话术、工具调用条件和 JSON 输出约束。

## 9. 核心难点与解决方案

### 难点 1：多轮对话上下文管理

- 问题表现：如果只把当前用户输入发给 LLM，回复会缺少上下文；如果把所有历史都发给 LLM，Prompt 会越来越长。
- 产生原因：聊天历史持续增长，LLM 上下文窗口和调用成本有限。
- 解决方案：`get_recent_messages(limit=5)` 保留短期原文，超过 20 条后用 `check_and_compress()` 压缩最早 15 条为 `MemorySummary`，再把最新摘要注入 Prompt。
- 涉及代码位置：`backend/app/services/memory_service.py`、`backend/app/agents/companion_agent.py`。
- 面试时可以怎么讲：我用了“最近消息 + 中期摘要”的方式平衡连续性和成本，不是简单把所有消息塞进 Prompt。

### 难点 2：长期记忆召回

- 问题表现：用户提到之前的事情时，最近 5 条消息可能不包含相关背景。
- 产生原因：情绪陪伴需要跨时间记住重要经历，短期上下文不足。
- 解决方案：把心情日记、压缩摘要、有意义用户消息写入 ChromaDB，Agent 需要时调用 `search_memory` 语义检索。
- 涉及代码位置：`backend/app/services/rag_service.py`、`backend/app/agents/companion_agent.py`。
- 面试时可以怎么讲：我把 RAG 用在用户长期记忆上，而不是只做文档问答，让 Agent 有“记得过去”的体验。

### 难点 3：Agent 工具调用稳定性

- 问题表现：每轮都检索会干扰聊天，不检索又无法记住历史。
- 产生原因：工具调用需要根据语义判断，固定关键词规则不够灵活。
- 解决方案：在系统 Prompt 中定义 `search_memory` 的调用格式和调用条件，第一次 LLM 输出工具指令时由 `_parse_tool_call()` 解析，再执行 RAG 检索和二次生成。
- 涉及代码位置：`CompanionAgent.MEMORY_TOOL_DESC`、`_parse_tool_call()`、`_execute_search_memory()`。
- 面试时可以怎么讲：这是一个轻量 ReAct-like 设计，模型负责意图判断，后端负责工具执行和安全兜底。

### 难点 4：流式输出和前端状态同步

- 问题表现：AI 回复慢时用户等待感强；流式输出又需要处理临时消息、真实消息 ID 和异常。
- 产生原因：LLM 生成耗时不稳定，HTTP 普通响应不能逐 token 展示。
- 解决方案：后端用 `StreamingResponse` 输出 SSE，前端用 `fetch + ReadableStream` 解析 `[USER_MSG]`、token、`[DONE]`，用真实 ID 替换临时 ID。
- 涉及代码位置：`backend/app/api/routes/chat.py`、`CompanionAgent.stream_chat()`、`frontend/src/services/api.ts`、`ChatView.vue`。
- 面试时可以怎么讲：我自己设计了 SSE 事件协议，让 UI 可以同时处理保存消息、工具状态、token 追加和最终落库。

### 难点 5：LLM 结构化输出解析

- 问题表现：心情总结和天气建议需要 JSON，但模型可能输出 Markdown 或非标准文本。
- 产生原因：LLM 不是严格 JSON 生成器，格式可能漂移。
- 解决方案：Prompt 中明确要求只返回 JSON，代码中去掉 ```json 代码块，再 `json.loads()`；解析失败时使用默认值降级。
- 涉及代码位置：`summary_service._analyze_mood()`、`weather_service._generate_suggestions()`。
- 面试时可以怎么讲：我对 LLM 输出做了格式约束和解析兜底，保证产品功能不会因为一次格式漂移直接崩掉。

### 难点 6：向量库与关系型数据库一致性

- 问题表现：心情记录保存成功但向量写入失败时，长期检索缺少这条记录。
- 产生原因：SQLite 和 ChromaDB 不是同一个事务系统。
- 解决方案：当前主流程优先保证 SQLite 落库，RAG 写入失败只打印警告，不阻塞用户；后续可增加重试队列和一致性校验。
- 涉及代码位置：`summary_service._index_to_rag()`、`rag_service.index()`。
- 面试时可以怎么讲：我当前选择了主数据优先，向量索引作为可补偿的派生数据；生产环境会加任务状态和重试。

### 难点 7：主动关怀触发

- 问题表现：普通聊天机器人只会被动回答，缺少情绪陪伴产品的主动性。
- 产生原因：模型只看到当前输入，不一定知道用户近期连续低落。
- 解决方案：`_check_care_needed()` 检查最近 3 天心情记录，连续低于 4 分时动态注入关怀 Prompt。
- 涉及代码位置：`CompanionAgent._check_care_needed()`、`MoodEntry`。
- 面试时可以怎么讲：我把结构化情绪数据反哺到 Agent Prompt，让产品从“问答”变成“有状态的陪伴”。

### 难点 8：外部 API 不稳定

- 问题表现：天气、新闻、MCP 工具依赖外部配置和网络，容易失败。
- 产生原因：第三方 API 需要 key，可能超时、返回空数据或格式变化。
- 解决方案：新闻服务检查 `NEWS_API_KEY`，requests 设置 timeout；天气服务加 1 小时内存缓存，并在解析失败时提供默认天气和建议。
- 涉及代码位置：`news_service.py`、`weather_service.py`、`amap_service.py`。
- 面试时可以怎么讲：第三方能力我放在独立 service 中，失败时尽量降级，不让侧栏工具影响主聊天。

## 10. 面试讲解版项目总结

### 10.1 1 分钟项目介绍

这个项目是我主要开发的一个情绪陪伴类 AI 应用，名字叫“树洞”。它不只是一个简单聊天页面，而是围绕用户倾诉场景做了多轮对话、三种陪伴人设、流式回复、记忆压缩、长期语义记忆、每日心情总结和情绪日历。后端用 FastAPI + SQLAlchemy + SQLite 管理会话和消息，用 ChromaDB + DashScope Embedding 做长期记忆检索，用自定义 CompanionAgent 组织 Prompt、工具调用和 LLM 回复；前端用 Vue3 + TypeScript 做聊天界面、会话侧栏和心情面板。这个项目最能体现的是我对 LLM 应用完整链路的理解：从接口设计、数据持久化、Prompt 组织、RAG 召回到前端流式渲染，我都做了实际实现。

### 10.2 3 分钟项目介绍

这个项目的业务场景是情绪陪伴和心情记录。用户可以像和朋友聊天一样倾诉，系统会根据不同陪伴风格回复；聊天内容会沉淀成会话历史、记忆摘要和每日心情小记，前端还能展示近 7 天趋势、月历和关键词云。

整体架构上，我把项目分为 Vue3 前端、FastAPI 路由层、Service 层、Agent 层、数据库层和 RAG 层。前端通过 `api.ts` 统一调用接口，聊天流式接口使用 `fetch + ReadableStream`；后端路由只负责参数校验和转发，复杂逻辑放到 `CompanionAgent`、`memory_service`、`summary_service` 和 `rag_service` 中；结构化数据用 SQLite 存，会话和消息通过 `conversation_id` 关联，长期语义记忆写入 ChromaDB。

核心模块是 CompanionAgent。一次聊天请求进来后，它先保存用户消息，再检查是否需要压缩历史消息，然后读取人设 Prompt、最近 5 条消息、中期摘要和连续低分关怀指令来构建 Prompt。第一次调用 LLM 时，模型可以决定是否输出 `search_memory` 工具调用；如果需要，后端用 ChromaDB 检索历史记忆，再把工具结果注入第二次 LLM 调用并流式返回前端。

技术难点主要在上下文管理、长期记忆、流式响应和 LLM 结构化输出。比如心情总结要求模型返回 JSON，我在 Prompt 中约束格式，并在代码里做 JSON 解析和降级；流式输出则设计了 `[START]`、`[USER_MSG]`、token、`[TOOL_USING]`、`[DONE]` 事件，让前端可以边生成边渲染。后续我会优化用户体系、RAG 按用户隔离、异步任务队列、统一异常处理和知识库文件上传能力。

## 11. 面试官可能追问的问题与参考回答

1. **为什么选择 FastAPI？**  
FastAPI 很适合这个项目，因为它天然支持 Pydantic 参数校验、自动 Swagger 文档和依赖注入。我的路由里大量使用 `response_model` 和 `Depends(get_db)`，可以让接口契约和数据库 Session 管理比较清晰。相比手写校验，FastAPI 能减少很多样板代码。

2. **FastAPI 和 Flask 有什么区别？**  
Flask 更轻量、更自由，但很多校验、文档、类型声明需要自己补。FastAPI 基于类型注解和 Pydantic，适合接口较多、前后端分离的项目。这个项目有聊天、心情、天气、新闻等多个接口，用 FastAPI 能让接口结构更明确。

3. **为什么使用 SQLite？**  
当前项目是本地原型和求职展示项目，SQLite 部署简单，不需要额外数据库服务。会话、消息、心情记录这些结构化数据都适合关系表存储。生产环境如果多用户并发增加，可以迁移到 MySQL 或 PostgreSQL。

4. **项目里用 MySQL 了吗？**  
当前代码中未发现 MySQL 实现。数据库连接在 `database.py` 中写死为 SQLite 文件 `backend/emotion.db`。如果要上线，我会把 `DATABASE_URL` 改为环境变量，并引入 Alembic 做迁移。

5. **为什么使用 ChromaDB？**  
ChromaDB 适合本地持久化向量检索，接入成本低。项目用它存储心情日记、记忆摘要和有价值用户消息，集合名是 `emotion_memories`。对实习项目来说，它能快速验证 RAG 长期记忆能力。

6. **RAG 是如何实现的？**  
项目的 RAG 不是文档上传型，而是长期情绪记忆型。`RAGService.index()` 调用 DashScope `text-embedding-v4` 得到 1024 维向量，再 upsert 到 ChromaDB；`search()` 对用户查询向量化后取 Top-K，并过滤相似度低于 0.6 的结果。Agent 只有在模型输出工具调用时才检索。

7. **RAG 如何减少幻觉？**  
RAG 给模型提供真实历史记忆，避免模型凭空猜用户之前说过什么。项目还在 Prompt 中要求“记忆只是背景，不相关可以忽略”，并对检索结果做相似度阈值过滤。这样能减少乱引用历史的概率。

8. **BM25 和向量检索有什么区别？**  
BM25 更偏关键词匹配，适合专有名词、编号、故障码等精确召回；向量检索更偏语义相似，适合表达不同但意思相近的句子。当前项目只实现了向量检索，当前代码中未发现 BM25。后续如果做文档知识库，我会考虑混合召回。

9. **为什么要做混合召回？**  
当前项目未实现混合召回。混合召回的价值是弥补单一向量检索对精确词不敏感的问题，尤其适合产品文档、医疗术语、故障码场景。实现上可以 BM25 和向量各取 Top-K，再归一化分数、去重、重排。

10. **Agent 的 Tool 是如何定义和调用的？**  
`search_memory` 工具定义在 `CompanionAgent` 的 `MEMORY_TOOL_DESC` 中，里面写了工具用途和调用格式。LLM 第一次回复如果包含 `[TOOL_CALL:search_memory:query=...]`，后端用正则解析 query，然后调用 RAG 检索。检索结果会作为工具返回结果追加到 messages，触发第二次 LLM 生成。

11. **为什么不用普通 if-else 判断是否检索？**  
用户表达历史记忆需求的方式很多，固定关键词容易误判。当前设计让 LLM 根据语义决定是否调用工具，后端只负责解析和执行。这样扩展新工具时，也可以继续走“工具描述 + 解析执行”的模式。

12. **ReAct 的流程是什么？项目里怎么体现？**  
标准 ReAct 是 Thought、Action、Observation、Final Answer。项目里 Thought 没有显式暴露，Action 是 LLM 输出工具调用指令，Observation 是 RAG 检索结果，Final Answer 是第二次 LLM 回复。它是一个轻量 ReAct-like 实现，不是 LangChain 标准 Agent。

13. **项目里用 LangChain 或 LangGraph 了吗？**  
当前代码中未发现 LangChain 和 LangGraph 实现。项目使用的是 `HelloAgentsLLM` 和自定义 `CompanionAgent`。如果未来流程更复杂，比如多节点审批、多个工具并行，可以考虑用 LangGraph 重构。

14. **如何管理多轮对话历史？**  
短期历史取最近 5 条消息，中期历史在超过 20 条时压缩最早 15 条为摘要。摘要保存到 `memory_summaries` 表，最新摘要会注入 Prompt。这样不会让 Prompt 无限增长。

15. **session_id 有什么作用？**  
当前项目没有叫 `session_id` 的字段，实际由 `conversation_id` 承担会话标识。它用于查询该会话消息、保存新消息、压缩该会话摘要。未来如果加用户体系，可以把 `conversation_id` 理解为某个用户下的 session。

16. **user_id 和 conversation_id 的区别是什么？**  
当前代码中未发现 `user_id` 实现。理论上 user_id 表示用户身份，conversation_id 表示用户的某一次会话。当前项目是单用户本地版本，只用 conversation_id 做会话隔离。

17. **为什么要做短期、中期、长期记忆？**  
短期记忆保证最近对话连贯，中期摘要保留较长对话的关键信息，长期 RAG 负责跨时间召回重要历史。三层结构能控制 token 成本，也能提升陪伴感。情绪陪伴场景尤其需要长期记忆。

18. **为什么不能把所有历史消息都放进 Prompt？**  
历史消息会越来越多，直接塞进 Prompt 会超上下文、增加成本，还会干扰当前问题。项目用最近 5 条原文加摘要，再必要时检索长期记忆。这样相关性和成本更可控。

19. **文件删除后向量库如何同步？**  
当前代码中未发现文件上传和文件删除实现，也没有 file_id。已有的是 `rag.delete_by_date(date)`，用于重新生成心情日记时删除当天旧索引。如果做文件知识库，需要在向量 metadata 中保存 file_id，并删除时按 file_id 删除 ChromaDB 记录。

20. **流式响应怎么实现？**  
后端 `POST /api/chat/message/stream` 返回 `StreamingResponse`，media type 是 `text/event-stream`。Agent 生成器按 SSE 格式 yield `[START]`、token、`[DONE]` 等事件。前端用 `fetch` 读取 ReadableStream，解析 `data:` 行并逐步追加到助手消息。

21. **如何避免 Prompt 过长？**  
项目只取最近 5 条原始消息，并把更早消息压缩为摘要。RAG 检索结果也会截断到 150 字以内再注入 Prompt。这样可以避免历史上下文无限膨胀。

22. **如果检索结果不准怎么办？**  
当前代码用相似度阈值 0.6 过滤低相关结果，并在 Prompt 中允许模型忽略不相关记忆。后续可以增加 rerank、按 conversation_id/user_id 过滤、混合召回和用户反馈机制。也可以记录检索命中情况用于调参。

23. **如何评估项目效果？**  
可以从对话体验、记忆命中率、心情总结准确性、流式响应延迟、接口错误率几个方面评估。当前代码没有自动评测脚本，这是优化方向。面试中我会重点展示调用链和真实交互闭环。

24. **如何处理大文件上传？**  
当前代码中未发现文件上传实现。如果要做，我会用 FastAPI `UploadFile` 流式保存，限制文件大小，异步解析和分块 embedding。大文件向量化适合放到后台任务，前端轮询处理状态。

25. **如何避免重复上传？**  
当前代码中未发现 MD5 去重实现。知识库版本可以在上传时计算文件 MD5，数据库中保存 hash，重复文件直接返回已有记录或提示用户。这样能避免重复 embedding 和重复占用向量库。

26. **如果 LLM 调用失败怎么办？**  
当前 `_invoke_llm_sync()` 和 `_stream_llm()` 都有异常兜底，会返回或流式输出一段友好的失败提示。心情总结失败会返回默认 score、keywords 和 summary。更完善的做法是加重试、超时控制、熔断和模型降级。

27. **如果向量库和数据库状态不一致怎么办？**  
当前代码主流程以 SQLite 为准，ChromaDB 写入失败不回滚主数据。优化上可以加状态字段、补偿任务和定期一致性校验。比如 mood_entries 中记录 `indexed_status`，失败后后台重试。

28. **如果第三方 API 超时怎么办？**  
新闻服务 requests 设置了 8 秒 timeout，天气服务有 1 小时内存缓存和默认解析兜底。但还没有统一重试和熔断。生产环境可以加 tenacity 重试、缓存降级和错误监控。

29. **为什么天气服务还要调用 LLM？**  
天气 API 只返回结构化天气数据，但产品需要更像陪伴应用的建议。`WeatherService._generate_suggestions()` 把天气数据交给 LLM 生成出行、饮食、穿搭三条短建议。这样工具数据可以转化为更自然的用户价值。

30. **这个项目还能怎么优化？**  
我会优先补用户体系和权限隔离，让 `user_id` 贯穿会话、心情和 RAG metadata。其次补统一异常处理、日志、测试、异步任务和 Docker 部署。AI 侧可以增加混合召回、rerank、记忆纠错和多模型切换。

## 12. 项目优化方向

### 12.1 工程化优化

| 当前可能存在的问题 | 优化方案 | 可能使用的技术 | 对项目价值的提升 |
|---|---|---|---|
| 数据库 URL 写死为 SQLite 文件 | 把 `DATABASE_URL` 放入环境变量 | Pydantic Settings、SQLAlchemy | 方便切换 MySQL/PostgreSQL |
| 异常响应格式不统一 | 增加全局异常处理中间件 | FastAPI exception handler | 前端错误处理更一致 |
| 缺少系统日志 | 引入结构化日志 | logging、loguru | 便于定位 LLM/API/数据库问题 |
| 缺少测试 | 为 service 和路由补单元测试 | pytest、httpx TestClient | 面试和维护更有说服力 |
| 缺少数据库迁移 | 引入迁移工具 | Alembic | 表结构升级更安全 |
| 部署方式不完整 | 增加 Dockerfile 和 compose | Docker、docker-compose | 简化演示和部署 |
| 缺少统一响应格式 | 定义 `BaseResponse[T]` 或统一封装 | Pydantic Generic | 前后端协议更规范 |

### 12.2 性能优化

| 当前可能存在的问题 | 优化方案 | 可能使用的技术 | 对项目价值的提升 |
|---|---|---|---|
| Embedding 每次单条调用 | 批量 embedding | DashScope batch API | 降低知识写入耗时 |
| 心情总结同步阻塞 | 改为后台任务 | Celery、RQ、FastAPI BackgroundTasks | 用户不用等待长任务 |
| SQLite 并发能力有限 | 迁移到 PostgreSQL/MySQL | PostgreSQL、MySQL | 支持多用户并发 |
| RAG 检索只有向量 Top-K | 增加过滤和重排 | metadata filter、reranker | 提升记忆准确率 |
| 天气服务每次创建实例 | 复用 service 单例 | singleton/cache | 减少初始化成本 |
| 前端全量拉心情记录 | 分页或按月加载 | query 参数、缓存 | 降低数据量增长后的压力 |

### 12.3 稳定性优化

| 当前可能存在的问题 | 优化方案 | 可能使用的技术 | 对项目价值的提升 |
|---|---|---|---|
| LLM 调用失败只简单兜底 | 增加重试、降级模型、超时 | tenacity、timeout、fallback model | 降低偶发失败影响 |
| SQLite 和 ChromaDB 不一致 | 增加索引状态和补偿任务 | job queue、定时校验 | 保证长期记忆可靠 |
| SSE 断线无恢复 | 增加中断处理和重新加载消息 | AbortController、消息状态 | 提升聊天稳定性 |
| 第三方 API 不稳定 | 加缓存、熔断、降级文案 | cachetools、Redis | 侧栏工具不影响主流程 |
| 无限调用接口风险 | 增加限流 | slowapi、Redis rate limit | 防止滥用和成本失控 |

### 12.4 可扩展性优化

| 当前可能存在的问题 | 优化方案 | 可能使用的技术 | 对项目价值的提升 |
|---|---|---|---|
| 工具调用写在 Agent 内部 | 抽象 Tool Registry | Python class registry | 新增工具更容易 |
| 没有用户体系 | 增加 User 表和鉴权 | JWT、OAuth2 | 支持多用户和隐私隔离 |
| RAG 未按用户过滤 | metadata 加 user_id 并检索过滤 | Chroma where filter | 避免跨用户记忆污染 |
| 模型配置不够灵活 | 支持多模型切换 | provider adapter | 便于成本和效果权衡 |
| 当前无文档知识库 | 增加文件上传、解析、分块、删除 | UploadFile、pypdf、python-docx | 扩展到学习资料/产品文档问答 |
| 当前无 LangGraph | 复杂 Agent 流程可图编排 | LangGraph | 支持多节点、多工具、多状态 |

### 12.5 产品化优化

| 当前可能存在的问题 | 优化方案 | 可能使用的技术 | 对项目价值的提升 |
|---|---|---|---|
| 用户无法评价回答 | 增加点赞/踩和反馈 | feedback 表 | 优化 Prompt 和模型效果 |
| 用户无法管理记忆 | 增加记忆查看、删除、纠错 | memory UI、RAG delete | 减少错误记忆影响 |
| 情绪趋势较简单 | 增加图表和报告 | ECharts | 提升可视化表达 |
| 无管理后台 | 增加后台查看接口状态 | admin UI | 便于演示和运维 |
| 无权限管理 | 登录注册和会话权限 | JWT、RBAC | 更接近真实产品 |
| 无检索可解释性 | 展示“参考了哪些记忆” | RAG source display | 提升用户信任 |

## 13. 求职展示版项目亮点总结

- 独立设计并实现情绪陪伴类 LLM 应用的完整前后端链路，覆盖会话管理、流式聊天、心情总结、情绪日历和外部工具接入。
- 基于 FastAPI、SQLAlchemy 和 Pydantic 构建清晰的接口层、模型层和服务层，保证路由职责单一、数据结构明确、业务逻辑可维护。
- 实现自定义 `CompanionAgent`，完成 Prompt 分层构建、人格切换、短期上下文、中期摘要、长期记忆检索和 SSE 流式输出。
- 使用 ChromaDB + DashScope `text-embedding-v4` 构建长期语义记忆，将心情日记、对话摘要和关键用户消息沉淀为可召回的 RAG 记忆。
- 设计轻量 ReAct-like 工具调用机制，让 LLM 根据用户意图主动调用 `search_memory`，而不是每轮固定检索，提高对话自然度和记忆使用准确性。
- 通过 LLM 结构化分析用户当日对话，生成 1-10 情绪评分、关键词和总结文本，并在前端实现月历、近 7 天趋势和关键词云展示。
- 实现 `StreamingResponse` + 前端 `fetch ReadableStream` 的流式聊天体验，支持 token 级渲染、工具调用状态提示和服务端真实消息 ID 回填。
- 封装高德 MCP 天气能力和阿里云新闻 API，将外部实时信息转化为侧栏工具和聊天话题入口，体现 AI 应用的产品化扩展能力。

## 14. 输出要求确认

本文档已根据当前项目真实代码生成，重点覆盖项目架构、路由设计、文件拆分、前后端数据传输、Prompt、RAG、Agent、数据库设计、核心调用链和面试追问。对于当前代码中未发现的能力，例如 MySQL、LangChain、LangGraph、BM25、Streamlit、文档上传、文件知识库生命周期和标准文档型 RAG，文档中均已明确标注“当前代码中未发现该实现”或说明其未实现状态。

本文档面向实习求职、项目复盘和技术面试展示，可直接用于准备 AI 应用开发实习、LLM 应用开发实习、Python 后端实习、RAG 工程实习和 AIGC 产品研发相关面试。
