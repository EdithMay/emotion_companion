# backend/app/services/summary_service.py

import json
from datetime import datetime, date
from sqlalchemy.orm import Session
from ..models.db_models import Message, MoodEntry, Conversation
from ..models.schemas import MoodEntryOut
from ..services.llm_service import get_llm
from ..services.rag_service import get_rag_service


def get_today_messages(db: Session, target_date: str = None) -> list[dict]:
    """
    获取指定日期所有会话的全部消息。
    target_date 格式：YYYY-MM-DD，不传则默认今天。
    """
    if not target_date:
        target_date = date.today().strftime("%Y-%m-%d")

    # 取当天所有消息（跨多个会话）
    messages = (
        db.query(Message)
        .filter(Message.created_at >= f"{target_date} 00:00:00")
        .filter(Message.created_at <= f"{target_date} 23:59:59")
        .order_by(Message.created_at.asc())
        .all()
    )
    return [{"role": m.role, "content": m.content} for m in messages]


def get_today_conversation_ids(db: Session, target_date: str = None) -> list[int]:
    """获取指定日期有消息的会话 ID 列表"""
    if not target_date:
        target_date = date.today().strftime("%Y-%m-%d")

    rows = (
        db.query(Message.conversation_id)
        .filter(Message.created_at >= f"{target_date} 00:00:00")
        .filter(Message.created_at <= f"{target_date} 23:59:59")
        .distinct()
        .all()
    )
    return [r[0] for r in rows]


def generate_mood_summary(db: Session, target_date: str = None) -> MoodEntryOut:
    """
    核心方法：分析今日对话，生成心情小记。

    流程：
      1. 读取今日所有会话的全部消息
      2. 调用 LLM 分析，返回 score + keywords + summary
      3. 存入 mood_entries（同天可多次更新，upsert 逻辑）
      4. 写入 ChromaDB（触发 RAG 索引，先删旧索引再写新的）
      5. 返回 MoodEntryOut

    Args:
        db:          数据库 Session
        target_date: 指定日期 YYYY-MM-DD，不传默认今天
    """
    if not target_date:
        target_date = date.today().strftime("%Y-%m-%d")

    print(f"\n📝 开始生成 {target_date} 的心情小记...")

    # ── 步骤 1：读取今日消息 ──────────────────────────────────
    messages = get_today_messages(db, target_date)
    conversation_ids = get_today_conversation_ids(db, target_date)

    if not messages:
        raise ValueError(f"{target_date} 没有任何对话记录，无法生成心情小记")

    # 只取用户消息用于分析（过滤助手回复，避免 LLM 分析自己的话）
    user_messages = [m for m in messages if m["role"] == "user"]
    print(f"   今日用户消息数: {len(user_messages)} 条，涉及会话: {conversation_ids}")

    # ── 步骤 2：调用 LLM 分析 ─────────────────────────────────
    analysis = _analyze_mood(user_messages, target_date)
    print(f"   分析结果: 得分={analysis['score']} 关键词={analysis['keywords']}")

    # ── 步骤 3：存入数据库（upsert）─────────────────────────────
    mood_entry = _upsert_mood_entry(db, target_date, analysis, conversation_ids)
    print(f"   心情小记已保存，ID: {mood_entry.id}")

    # ── 步骤 4：写入 ChromaDB ────────────────────────────────
    _index_to_rag(target_date, analysis)

    print(f"✅ {target_date} 心情小记生成完成\n")

    # ── 步骤 5：返回 MoodEntryOut ────────────────────────────
    return _to_schema(mood_entry)


def _analyze_mood(user_messages: list[dict], target_date: str) -> dict:
    """
    调用 LLM 分析用户消息，返回结构化情绪数据。

    返回格式：
    {
        "score": 7,
        "keywords": ["有点疲惫", "期待周末", "朋友聚餐"],
        "summary": "今天整体状态平稳..."
    }
    """
    llm = get_llm()

    # 拼接用户消息内容
    dialogue = "\n".join([
        f"用户说：{m['content']}" for m in user_messages
    ])

    prompt = f"""请分析以下用户今日（{target_date}）在情绪陪伴应用中的对话内容，生成心情小记。

用户今日说的话：
{dialogue}

请严格按照以下 JSON 格式返回，不要添加任何额外文字和 markdown 标记：
{{
  "score": 7,
  "keywords": ["关键词1", "关键词2", "关键词3"],
  "summary": "今日心情总结文字，100-200字，温暖自然的语气，用第二人称'你'描述用户的情绪状态"
}}

评分标准（score 为 1-10 的整数）：
  1-2：极度低落、崩溃、绝望
  3-4：情绪低迷、焦虑、难过
  5-6：平稳、一般、有些波动
  7-8：较好、愉快、满足
  9-10：非常开心、兴奋、幸福

keywords 要求：
  - 3-5 个词，提取今日情绪的核心标签
  - 用简短的词或短语，例如："工作压力"、"开心满足"、"有些焦虑"

summary 要求：
  - 温暖自然，像朋友写给你的总结
  - 提到今天的具体情绪事件
  - 结尾可以有一句鼓励或关怀的话"""

    try:
        response = llm.invoke([{"role": "user", "content": prompt}])

        # 提取文本
        if isinstance(response, str):
            text = response.strip()
        elif hasattr(response, "content"):
            text = response.content.strip()
        else:
            text = str(response).strip()

        # 去除可能的 markdown 代码块标记
        text = text.replace("```json", "").replace("```", "").strip()

        # 解析 JSON
        data = json.loads(text)

        # 校验字段完整性
        score    = int(data.get("score", 5))
        score    = max(1, min(10, score))   # 限制在 1-10 范围内
        keywords = data.get("keywords", [])
        summary  = data.get("summary", "")

        if not isinstance(keywords, list):
            keywords = []
        if not summary:
            summary = "今天的心情已记录。"

        return {"score": score, "keywords": keywords, "summary": summary}

    except json.JSONDecodeError as e:
        print(f"  ⚠️  LLM 返回格式解析失败: {e}，使用默认值")
        return {
            "score": 5,
            "keywords": ["今日记录"],
            "summary": "今天的对话已记录，心情状态待分析。"
        }
    except Exception as e:
        print(f"  ⚠️  LLM 分析失败: {e}")
        return {
            "score": 5,
            "keywords": ["今日记录"],
            "summary": "今天的心情已记录。"
        }


def _upsert_mood_entry(
    db: Session,
    target_date: str,
    analysis: dict,
    conversation_ids: list[int]
) -> MoodEntry:
    """
    写入或更新 mood_entries 表。
    同一天多次调用会覆盖之前的记录（upsert 逻辑）。
    """
    existing = (
        db.query(MoodEntry)
        .filter(MoodEntry.date == target_date)
        .first()
    )

    if existing:
        # 更新已有记录
        existing.score            = analysis["score"]
        existing.summary_text     = analysis["summary"]
        existing.keywords         = json.dumps(analysis["keywords"], ensure_ascii=False)
        existing.conversation_ids = json.dumps(conversation_ids)
        existing.updated_at       = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # 新建记录
        entry = MoodEntry(
            date=target_date,
            score=analysis["score"],
            summary_text=analysis["summary"],
            keywords=json.dumps(analysis["keywords"], ensure_ascii=False),
            conversation_ids=json.dumps(conversation_ids),
            updated_at=datetime.utcnow()
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry


def _index_to_rag(target_date: str, analysis: dict):
    """
    将心情小记写入 ChromaDB。
    先删除该日期旧索引，再写入新的，避免重复。
    """
    try:
        rag = get_rag_service()

        # 删除该日期旧的心情日记索引
        rag.delete_by_date(target_date)

        # 写入新索引
        index_text = (
            f"{analysis['summary']} "
            f"情绪关键词：{'、'.join(analysis['keywords'])}"
        )
        rag.index(
            text=index_text,
            metadata={
                "type":  "mood_entry",
                "date":  target_date,
                "score": str(analysis["score"])
            }
        )
        print(f"   RAG 索引写入完成")
    except Exception as e:
        # RAG 写入失败不影响主流程
        print(f"  ⚠️  RAG 索引写入失败（不影响心情小记保存）: {e}")


def _to_schema(entry: MoodEntry) -> MoodEntryOut:
    """ORM 对象转 Pydantic Schema，处理 JSON 字段反序列化"""
    try:
        keywords = json.loads(entry.keywords) if entry.keywords else []
    except json.JSONDecodeError:
        keywords = []

    try:
        conversation_ids = json.loads(entry.conversation_ids) if entry.conversation_ids else []
    except json.JSONDecodeError:
        conversation_ids = []

    return MoodEntryOut(
        id=entry.id,
        date=entry.date,
        score=entry.score,
        summary_text=entry.summary_text,
        keywords=keywords,
        conversation_ids=conversation_ids,
        updated_at=entry.updated_at
    )


def get_mood_entry_by_date(db: Session, target_date: str) -> MoodEntryOut | None:
    """根据日期获取心情小记，供路由层调用"""
    entry = (
        db.query(MoodEntry)
        .filter(MoodEntry.date == target_date)
        .first()
    )
    return _to_schema(entry) if entry else None


def get_all_mood_entries(db: Session) -> list[MoodEntryOut]:
    """获取全部心情记录，供情绪记录板渲染"""
    entries = (
        db.query(MoodEntry)
        .order_by(MoodEntry.date.desc())
        .all()
    )
    return [_to_schema(e) for e in entries]
