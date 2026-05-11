# 情绪陪伴与心情日记 Agent 网站 — 完整项目规格文档

> 本文档是面向开发者或 Agent 的完整项目说明书，包含产品功能、技术架构、数据库设计、文件结构、接口清单、开发顺序等全部细节，可直接作为新对话的上下文输入。

---

## 一、项目背景与定位

本项目是一个**情绪陪伴与心情日记 Agent 网站**，整体架构参考"HelloAgents 智能旅行助手"项目的四层结构（Routes → Agents → Services → Models），将其中的旅行规划功能替换为情绪陪伴功能。

**核心理念：** 帮助用户向内关注自己的情绪状态，提供 AI 陪伴对话、心情记录、情绪回顾等功能。

**技术栈：**
- 后端：Python + FastAPI + SQLAlchemy + SQLite + ChromaDB + HelloAgents 框架
- 前端：Vue3 + TypeScript + Ant Design Vue + ECharts + vue-wordcloud
- LLM：OpenAI 兼容格式（通过 HelloAgents 框架调用）
- 外部服务：高德地图 MCP（天气）、NewsAPI MCP（热点新闻）

---

## 二、完整功能清单

### 模块 1：对话系统

- 侧栏支持新建、切换、删除多个会话
- 每个会话独立保存消息历史
- 流式对话，前端显示打字机效果
- **三层记忆体系：**
  - 短期记忆：最近 5 条对话原文（实时传入 prompt）
  - 中期记忆：memory_summary 压缩摘要（消息超过 20 条时，自动把最早 15 条压缩为摘要文字，存入数据库，删除原始消息）
  - 长期记忆：ChromaDB 向量检索（跨周、跨会话、语义召回，详见 RAG 模块）
- 记忆边界：跨周（用户三周内的对话和日记均可被检索）

### 模块 2：人设系统

- 三种陪伴风格，本质是切换不同的 system prompt：
  - 🌸 温柔倾听型：语气温柔，善于共情，不急于给建议
  - 🧠 理性分析型：帮用户梳理情绪来源，提供客观视角
  - 😄 幽默解压型：用轻松幽默的方式化解负面情绪
- 每个会话独立记录人设选择
- 切换人设不影响历史对话内容
- 人设配置存储在数据库 persona_config 表，system prompt 可后台修改

### 模块 3：心情总结（一键生成）

- 用户点击"总结今日心情"按钮触发
- Agent 读取今日所有会话的全部消息
- 调用 LLM 分析，要求返回结构化 JSON：
  ```json
  {
    "score": 6,
    "keywords": ["有点疲惫", "期待周末", "工作压力"],
    "summary": "今天整体状态平稳，虽然工作上有些压力，但对周末有所期待..."
  }
  ```
- 情绪得分范围：1-10（1 极度低落，10 极度开心）
- 同一天允许多次更新，保留最新版本
- 生成完成后同步写入 ChromaDB（触发 RAG 索引）

### 模块 4：情绪记录板

- 按月展示方格日历（类似 GitHub 贡献图风格，但按月）
- 颜色映射规则：
  - 无记录：灰色 #E0E0E0
  - 得分 1-2：深蓝色 #1565C0（低落）
  - 得分 3-4：浅蓝色 #64B5F6（平淡）
  - 得分 5-6：浅黄色 #FFF176（平稳）
  - 得分 7-8：浅橙色 #FFB74D（愉快）
  - 得分 9-10：橙红色 #FF5722（非常开心）
- 点击有记录的方格，弹出 Modal 显示当日心情小记详情（日期、得分、关键词标签、总结文字）
- 月份切换器：← 上月 / 下月 →
- 页面下方：近 30 天情绪得分折线图（使用 ECharts）
- 页面下方：本月情绪关键词云（使用 vue-wordcloud，词频越高字越大）

### 模块 5：Agent 主动关怀

- 每次用户进入任意对话时，后端静默执行检测
- 检测逻辑：查询 mood_entries 表最近 3 天的记录，若均存在且 score < 4
- 触发后在 system prompt 末尾注入关怀指令，例如：
  > "用户最近连续三天情绪低落，请在对话开头自然地主动询问近况，语气温柔，不要让用户感到被监视。"
- 用户无感知，Agent 以自然方式开口，而非机械提示

### 模块 6：天气小组件

- 前端通过浏览器 Geolocation API 获取经纬度
- 传给后端，后端调用高德 MCP（maps_geo 逆地理编码 + maps_weather 查天气）
- LLM 根据天气数据生成三条建议：
  - ☀️ 出行建议（是否适合外出、注意事项）
  - 🥗 饮食建议（根据温度推荐饮食类型）
  - 👕 穿搭建议（具体衣物描述）
- 天气数据内存缓存，每小时自动刷新，避免重复调用 API
- 组件位置：侧栏顶部，小而精，不抢主界面注意力

### 模块 7：热点话题区

- 调用 NewsAPI MCP 拉取今日热点新闻
- 分类：社会 / 娱乐 / 科技 / 生活（用户可选择关注的类别）
- 侧栏展示 3-5 条热点卡片，每条显示标题和来源
- 交互逻辑：点击热点卡片 → 自动填入对话输入框（内容如"我想聊聊关于 XX 的话题"）→ 用户确认发送
- Agent 完全被动，绝不主动推送任何话题

### 模块 8：RAG 长期记忆系统

- 向量数据库：ChromaDB（本地文件存储，零配置）
- 向量化模型：sentence-transformers 的 paraphrase-multilingual-MiniLM-L12-v2（支持中文，模型体积小，本地运行）
- **索引触发时机：**
  - 生成心情小记后：将 summary_text + keywords 向量化存入 ChromaDB，元数据附带 date / score / keywords
  - 会话切换或结束时：将本次对话中有实质内容的用户消息向量化存入（不是每条都存，过滤掉"嗯""好的"等无意义消息）
- **检索触发时机：** 用户每次发消息时，自动执行语义检索，返回 Top 3 相关历史片段
- **最终 prompt 构建顺序：**
  ```
  [system_prompt（人设 + 可能的关怀指令注入）]
  [RAG 检索结果：Top 3 相关历史记忆片段]
  [memory_summary（中期压缩摘要，如果存在）]
  [最近 5 条对话原文]
  [用户当前消息]
  ```

---

## 三、数据库设计（SQLite，5 张表）

```sql
-- 会话表
conversations (
  id           INTEGER PRIMARY KEY,
  title        TEXT,          -- 自动生成或用户命名，例如"周一下午的倾诉"
  persona      TEXT,          -- 当前人设：gentle / rational / humorous
  created_at   TIMESTAMP,
  updated_at   TIMESTAMP
)

-- 消息表
messages (
  id                INTEGER PRIMARY KEY,
  conversation_id   INTEGER,  -- 外键 → conversations.id
  role              TEXT,     -- "user" 或 "assistant"
  content           TEXT,
  created_at        TIMESTAMP
)

-- 记忆摘要表（中期记忆）
memory_summaries (
  id                INTEGER PRIMARY KEY,
  conversation_id   INTEGER,  -- 外键 → conversations.id
  summary_text      TEXT,     -- 压缩后的摘要文字，注入 prompt 使用
  message_count     INTEGER,  -- 本条摘要覆盖了多少条原始消息
  created_at        TIMESTAMP
)

-- 心情小记表
mood_entries (
  id               INTEGER PRIMARY KEY,
  date             TEXT UNIQUE,  -- YYYY-MM-DD，唯一键
  score            INTEGER,      -- 1-10
  summary_text     TEXT,
  keywords         TEXT,         -- JSON 数组，例如 '["焦虑","疲惫","期待"]'
  conversation_ids TEXT,         -- JSON 数组，关联的会话 ID
  updated_at       TIMESTAMP
)

-- 人设配置表
persona_config (
  id             INTEGER PRIMARY KEY,
  name           TEXT,         -- gentle / rational / humorous
  display_name   TEXT,         -- 温柔倾听型 / 理性分析型 / 幽默解压型
  system_prompt  TEXT,         -- 完整的 system prompt 文本
  avatar_emoji   TEXT          -- 🌸 / 🧠 / 😄
)
```

---

## 四、完整文件结构

```
emotion-companion/
├── backend/
│   ├── .env                          # 环境变量（API Keys）
│   ├── requirements.txt
│   ├── run.py                        # 启动入口
│   └── app/
│       ├── __init__.py
│       ├── config.py                 # 配置管理，读取 .env
│       ├── database.py               # SQLite 初始化，建表，Session 管理
│       ├── models/
│       │   ├── __init__.py
│       │   ├── schemas.py            # Pydantic 数据模型（请求/响应结构）
│       │   └── db_models.py          # SQLAlchemy ORM 模型（对应数据库表）
│       ├── services/
│       │   ├── __init__.py
│       │   ├── llm_service.py        # HelloAgentsLLM 单例，复用原项目
│       │   ├── memory_service.py     # 记忆压缩：消息超 20 条自动压缩为摘要
│       │   ├── rag_service.py        # RAG 核心：ChromaDB 向量化存储与检索
│       │   ├── summary_service.py    # 心情总结：调 LLM 分析今日对话
│       │   ├── weather_service.py    # 高德 MCP 天气查询 + LLM 生成建议
│       │   └── news_service.py       # NewsAPI MCP 热点新闻拉取
│       ├── agents/
│       │   ├── __init__.py
│       │   └── companion_agent.py    # 核心 Agent：整合记忆/RAG/人设/关怀检测
│       └── api/
│           ├── __init__.py
│           ├── main.py               # FastAPI 应用入口，注册路由，CORS
│           └── routes/
│               ├── __init__.py
│               ├── chat.py           # 对话相关接口
│               ├── mood.py           # 心情记录相关接口
│               ├── memory.py         # 记忆管理接口
│               ├── weather.py        # 天气查询接口
│               └── news.py           # 热点新闻接口
│
└── frontend/
    ├── .env.local                    # VITE_API_BASE_URL, VITE_AMAP_WEB_JS_KEY
    ├── vite.config.ts                # @ 路径别名配置
    ├── tsconfig.json
    ├── package.json
    └── src/
        ├── main.ts                   # Vue 应用入口，注册路由和 Ant Design Vue
        ├── App.vue                   # 全局布局：侧栏 + 主内容区路由出口
        ├── types/
        │   └── index.ts              # 所有 TypeScript 类型定义，与后端 schemas.py 严格对应
        ├── services/
        │   └── api.ts                # Axios 封装，所有后端接口调用函数
        ├── components/
        │   ├── ConversationSidebar.vue  # 侧栏：天气组件+热点区+人设选择+会话列表
        │   ├── MessageBubble.vue        # 单条消息气泡（用户/助手样式不同）
        │   ├── WeatherWidget.vue        # 天气小组件（城市/温度/三条建议）
        │   └── HotTopicCard.vue         # 热点卡片（点击触发对话）
        └── views/
            ├── ChatView.vue             # 主对话页（路由：/）
            └── MoodBoard.vue            # 情绪记录板（路由：/mood）
```

---

## 五、后端接口总览

```
# 对话相关
POST   /api/chat/message                        发送消息，返回 Agent 回复
GET    /api/chat/conversations                  获取所有会话列表
POST   /api/chat/conversations                  新建会话
DELETE /api/chat/conversations/{id}             删除会话
GET    /api/chat/conversations/{id}/messages    获取某会话完整消息历史

# 心情记录相关
POST   /api/mood/summary                        触发今日心情总结生成
GET    /api/mood/entries                        获取所有心情记录（供记录板渲染）
GET    /api/mood/entries/{date}                 获取某天心情小记详情

# 记忆管理
GET    /api/memory/{conversation_id}            获取某会话的记忆摘要

# 天气
GET    /api/weather?lat=xx&lng=xx               传入经纬度，返回天气+三条建议

# 热点新闻
GET    /api/news?category=社会&limit=5          返回热点列表
```

---

## 六、核心模块实现细节

### companion_agent.py 的 prompt 构建逻辑

```python
def build_prompt(user_message, conversation_id, persona):
    # 1. 从 persona_config 表取 system_prompt
    system = get_persona_prompt(persona)

    # 2. 关怀检测：查最近 3 天 mood_entries，若得分均 < 4 则注入关怀指令
    if check_low_mood_streak():
        system += "\n用户最近连续三天情绪低落，请在对话开头自然地主动关心。"

    # 3. RAG 检索：用 user_message 语义检索 ChromaDB，取 Top 3
    rag_results = rag_service.search(user_message, top_k=3)

    # 4. 中期记忆：从 memory_summaries 取最新摘要
    memory_summary = get_latest_summary(conversation_id)

    # 5. 短期记忆：取最近 5 条消息原文
    recent_messages = get_recent_messages(conversation_id, limit=5)

    # 最终 prompt 结构
    return [
        {"role": "system",    "content": system},
        {"role": "system",    "content": f"【相关历史记忆】\n{rag_results}"},
        {"role": "system",    "content": f"【近期记忆摘要】\n{memory_summary}"},
        *recent_messages,
        {"role": "user",      "content": user_message}
    ]
```

### memory_service.py 的压缩触发逻辑

```python
def check_and_compress(conversation_id):
    messages = get_all_messages(conversation_id)
    if len(messages) > 20:
        to_compress = messages[:15]
        summary = llm.compress(to_compress)
        save_summary(conversation_id, summary, len(to_compress))
        delete_messages([m.id for m in to_compress])
        # 同步写入 ChromaDB
        rag_service.index(summary, metadata={"type": "memory_summary", ...})
```

### rag_service.py 的核心结构

```python
import chromadb
from sentence_transformers import SentenceTransformer

class RAGService:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.client.get_or_create_collection("emotion_memories")
        self.model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

    def index(self, text: str, metadata: dict):
        embedding = self.model.encode(text).tolist()
        self.collection.add(
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
            ids=[f"{metadata.get('type')}_{metadata.get('date')}_{id(text)}"]
        )

    def search(self, query: str, top_k: int = 3) -> str:
        embedding = self.model.encode(query).tolist()
        results = self.collection.query(query_embeddings=[embedding], n_results=top_k)
        return "\n".join([
            f"· {meta.get('date', '历史')}：{doc}"
            for doc, meta in zip(results["documents"][0], results["metadatas"][0])
        ])
```

### weather_service.py 的流程

```python
async def get_weather_with_suggestions(lat: float, lng: float):
    # 1. 高德 MCP 逆地理编码
    city = amap_mcp.call("maps_geo_reverse", {"location": f"{lng},{lat}"})
    # 2. 高德 MCP 查天气（内存缓存，每小时刷新）
    weather_data = amap_mcp.call("maps_weather", {"city": city})
    # 3. LLM 生成三条建议
    suggestions = llm.generate(f"""
        当前天气：{city}，{weather_data['temperature']}°C，{weather_data['weather']}
        请生成三条简短建议，分别关于：出行、饮食、穿搭。
        格式：JSON {{"travel": "...", "food": "...", "clothing": "..."}}
    """)
    return {**weather_data, "suggestions": suggestions, "city": city}
```

---

## 七、前端侧栏完整结构

```
ConversationSidebar.vue
│
├── WeatherWidget（天气组件）
│   ├── 城市名 + 温度 + 天气图标
│   └── 三条建议折叠展示（出行 / 饮食 / 穿搭）
│
├── 今日热点（HotTopicCard × 3-5 条）
│   ├── 新闻标题
│   ├── 来源标签
│   └── 点击 → 填入输入框文字 → 等待用户确认发送
│
├── 人设选择器（Tab 或 Radio 形式）
│   ├── 🌸 温柔倾听型
│   ├── 🧠 理性分析型
│   └── 😄 幽默解压型
│
└── 会话管理
    ├── + 新建对话（按钮）
    ├── 历史会话列表（按 updated_at 倒序）
    │   ├── 会话标题
    │   ├── 最后一条消息预览
    │   └── 右键/悬停显示删除按钮
    └── 底部跳转按钮：📊 情绪记录板（→ /mood）
```

---

## 八、MoodBoard.vue 页面结构

```
MoodBoard.vue
│
├── 顶部：← 返回对话按钮
│
├── 月份切换区
│   └── ← 2025年5月 →
│
├── 情绪方格日历
│   ├── 星期标题行（日一二三四五六）
│   ├── n×n 方格（按月份天数铺满）
│   │   ├── 有记录：按得分着色
│   │   └── 无记录：灰色
│   └── 点击有记录的格子 → 弹出 Modal
│       └── Modal 内容：日期 / 得分 / 关键词标签 / 总结文字
│
├── 近 30 天情绪折线图（ECharts）
│   ├── X 轴：日期
│   ├── Y 轴：情绪得分（1-10）
│   └── 折线颜色根据得分区间变化
│
└── 本月情绪关键词云（vue-wordcloud）
    └── 词频越高，字体越大，颜色越深
```

---

## 九、环境变量配置

### backend/.env

```ini
OPENAI_API_KEY=你的LLM Key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
AMAP_API_KEY=你的高德服务端Key
NEWS_API_KEY=你的NewsAPI Key
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173
```

### frontend/.env.local

```ini
VITE_API_BASE_URL=http://localhost:8000
VITE_AMAP_WEB_JS_KEY=你的高德Web端JS_API_Key
```

---

## 十、依赖清单

### backend/requirements.txt

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
pydantic==2.7.0
pydantic-settings==2.3.0
python-dotenv==1.0.1
sqlalchemy==2.0.0
httpx==0.27.0
requests==2.32.0
hello-agents>=0.1.0
chromadb>=0.4.0
sentence-transformers>=2.2.0
```

### frontend 关键依赖

```
vue / vue-router / ant-design-vue / @ant-design/icons-vue
axios / dayjs
@amap/amap-jsapi-loader
echarts / vue-echarts
vue-wordcloud
```

---

## 十一、完整开发顺序（共 20 步）

```
【后端基础层】

第 01 步  项目骨架 + 虚拟环境
          创建目录结构，所有 __init__.py 就位，创建 Python 虚拟环境
          验证：find backend -name "*.py" | sort 看到全部包文件

第 02 步  requirements.txt + 依赖安装
          验证：import fastapi / sqlalchemy / chromadb / hello_agents 均成功

第 03 步  config.py
          读取 .env，validate_config() 校验必要 Key，print_config() 打印摘要
          验证：运行 print_config() 看到配置摘要

第 04 步  database.py + db_models.py
          SQLite 初始化，5 张表 ORM 模型，启动时自动插入 3 条 persona_config 默认数据
          验证：生成 emotion.db，5 张表全部存在，persona_config 有 3 条记录

第 05 步  schemas.py（Pydantic 数据模型）
          定义所有请求体和响应体模型，字段与数据库表严格对应
          验证：实例化每个模型无报错

【后端服务层】

第 06 步  llm_service.py
          HelloAgentsLLM 单例，复用原旅行助手项目结构
          验证：get_llm() 返回实例，打印 provider + model

第 07 步  memory_service.py
          消息超 20 条自动触发压缩，压缩后删除原始消息，保存摘要到数据库
          验证：传入 25 条假消息，输出压缩摘要，数据库消息数变为 10 条

第 08 步  rag_service.py
          ChromaDB 本地初始化，sentence-transformers 模型加载
          实现 index(text, metadata) 和 search(query, top_k) 两个核心方法
          验证：写入 3 条假数据，用语义相关词检索，能召回正确结果

第 09 步  summary_service.py
          读取今日所有会话消息，调 LLM 分析返回 score+keywords+summary
          存入 mood_entries，写入 ChromaDB
          验证：传入假对话，返回合法 JSON，数据库有记录，ChromaDB 有索引

第 10 步  weather_service.py
          高德 MCP 初始化（复用旅行助手的 MCPTool 写法）
          逆地理编码 + 天气查询 + LLM 生成三条建议 + 内存缓存
          验证：传入北京经纬度，返回天气数据 + 三条建议文字

第 11 步  news_service.py
          NewsAPI MCP 初始化，按分类拉取热点新闻
          验证：返回 5 条热点，标题/简介/来源字段完整

【后端 Agent + 路由层】

第 12 步  companion_agent.py
          人设注入 + RAG 检索注入 + 中期记忆摘要注入 + 短期记忆注入
          关怀检测逻辑（连续 3 天 score < 4）
          调用 memory_service 检查是否需要压缩
          验证：发一条消息，打印完整 prompt 结构，确认 5 层内容全部存在

第 13 步  Routes 五个文件（chat / mood / memory / weather / news）
          验证：Swagger 文档 /docs 显示全部接口，数量和路径正确

第 14 步  main.py + run.py
          CORS 配置，注册全部路由（/api 前缀），startup 事件校验配置
          验证：服务启动无报错，GET /health 返回 200

【前端层】

第 15 步  types/index.ts + services/api.ts
          TypeScript 类型定义与后端 schemas.py 完全对应
          Axios 实例，120s 超时，请求/响应拦截器，所有接口调用函数
          验证：TypeScript 编译无类型报错

第 16 步  WeatherWidget.vue + HotTopicCard.vue
          WeatherWidget：城市/温度/天气状态/三条建议
          HotTopicCard：标题/来源，点击填入输入框
          验证：组件独立渲染正确，点击热点卡片输入框自动填入文字

第 17 步  ConversationSidebar.vue
          集成 WeatherWidget 和 HotTopicCard
          人设选择 Tab，新建会话按钮，历史会话列表，底部记录板跳转按钮
          验证：点击新建会话侧栏出现新条目，点击历史会话主区域切换

第 18 步  ChatView.vue（主对话页）
          消息气泡列表，底部输入框，打字机流式效果
          "总结今日心情"按钮，总结完成后展示结果
          验证：完整走通一次对话 + 一次心情总结，数据库有记录

第 19 步  MoodBoard.vue（情绪记录板完整页面）
          月份切换器，方格日历（颜色映射+点击弹窗）
          ECharts 折线图（近 30 天），vue-wordcloud 关键词云（本月）
          验证：点击有数据格子弹出小记，折线图数据正确，关键词云渲染正常

【联调验证】

第 20 步  完整端到端验证
          1. 后端健康检查：GET /health 返回 200
          2. 新建会话，发送 3 条消息，切换人设后再发 1 条，确认人设生效
          3. 模拟连续 3 天低分记录，进入对话确认 Agent 主动关怀
          4. 点击"总结今日心情"，确认情绪记录板出现当天数据和颜色
          5. 点击热点卡片，确认输入框自动填入
          6. 情绪记录板：点击方格、查看折线图、查看关键词云
          7. 发送超过 20 条消息，确认记忆压缩触发，消息数减少但摘要存在
          8. RAG 验证：两次对话中提到相同主题，确认第二次 Agent 能召回第一次内容
```

---

## 十二、关键设计决策说明

| 决策 | 选择 | 原因 |
|---|---|---|
| 数据库 | SQLite | 单用户本地项目，零配置，和 ChromaDB 搭配完美 |
| 向量数据库 | ChromaDB | 本地文件存储，Python 原生，无需额外服务 |
| 向量化模型 | paraphrase-multilingual-MiniLM-L12-v2 | 支持中文，模型小，本地运行无需 API |
| 新闻数据源 | NewsAPI | 完全合规，个人免费额度够用，有成熟 MCP Server |
| 热点交互 | 点击填入，不主动推送 | 保护用户注意力，符合情绪陪伴产品调性 |
| 心情总结频率 | 同天可多次更新 | 用户情绪会变化，晚上补充早上的记录是合理需求 |
| 记录板时间维度 | 按月展示 | 月维度是情绪管理最常用的回顾粒度 |
| 记忆边界 | 跨周 | 平衡上下文质量与 token 消耗 |
| 用户系统 | 无（单用户本地） | 降低复杂度，专注核心功能 |

---

*文档版本：最终确认版*
*覆盖全部讨论内容：对话系统、人设系统、心情总结、情绪记录板、Agent 关怀、天气组件、热点话题、RAG 记忆系统、数据库设计、完整开发路径（20 步）*

