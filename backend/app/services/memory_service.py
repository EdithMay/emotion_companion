# backend/app/services/memory_service.py

import json
from sqlalchemy.orm import Session
from ..models.db_models import Message, MemorySummary
from ..services.llm_service import get_llm

# 触发压缩的消息数阈值
COMPRESS_THRESHOLD = 20
# 每次压缩最早的消息条数
COMPRESS_BATCH = 15


def get_all_messages(db: Session, conversation_id: int) -> list[Message]:
    """获取某会话全部消息，按时间正序"""
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )


def get_recent_messages(db: Session, conversation_id: int, limit: int = 5) -> list[dict]:
    """
    获取最近 N 条消息，返回 LLM 所需的字典格式。
    供 companion_agent.py 构建 prompt 时使用。
    """
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )
    # 倒序取出后要反转，保证时间正序传给 LLM
    return [
        {"role": m.role, "content": m.content}
        for m in reversed(messages)
    ]


def get_latest_summary(db: Session, conversation_id: int) -> str:
    """
    获取最新一条记忆摘要文本。
    若无摘要返回空字符串，供 companion_agent.py 注入 prompt。
    """
    summary = (
        db.query(MemorySummary)
        .filter(MemorySummary.conversation_id == conversation_id)
        .order_by(MemorySummary.created_at.desc())
        .first()
    )
    return summary.summary_text if summary else ""


def save_message(db: Session, conversation_id: int, role: str, content: str) -> Message:
    """保存一条消息到数据库"""
    msg = Message(
        conversation_id=conversation_id,
        role=role,
        content=content
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def check_and_compress(db: Session, conversation_id: int) -> bool:
    """
    检查消息数量，超过阈值则自动压缩最早一批消息为摘要。

    压缩流程：
      1. 查询该会话全部消息
      2. 消息数 > COMPRESS_THRESHOLD（20条）才触发
      3. 取最早的 COMPRESS_BATCH（15条）调 LLM 压缩
      4. 摘要存入 memory_summaries
      5. 删除这 15 条原始消息
      6. 返回 True 表示发生了压缩，False 表示未触发

    注意：压缩后同步写入 ChromaDB 的逻辑在 rag_service 完成后
          会在 companion_agent.py 里统一调用，这里只负责数据库操作。
    """
    messages = get_all_messages(db, conversation_id)

    if len(messages) <= COMPRESS_THRESHOLD:
        return False

    print(f"  🗜️  消息数 {len(messages)} 超过阈值 {COMPRESS_THRESHOLD}，开始压缩...")

    to_compress = messages[:COMPRESS_BATCH]
    summary_text = _compress_messages(to_compress)

    # 存摘要
    summary = MemorySummary(
        conversation_id=conversation_id,
        summary_text=summary_text,
        message_count=len(to_compress)
    )
    db.add(summary)

    # 删除已压缩的原始消息
    for msg in to_compress:
        db.delete(msg)

    db.commit()

    print(f"  ✅ 压缩完成：{len(to_compress)} 条消息 → 1 条摘要")
    return True


def _compress_messages(messages: list[Message]) -> str:
    """
    调用 LLM 将多条消息压缩为一段记忆摘要文字。

    prompt 要求 LLM：
      - 提取对话中的关键情绪事件、重要话题、用户透露的个人信息
      - 用第三人称描述用户状态
      - 输出 200 字以内的纯文本，不要 JSON，不要标题
    """
    llm = get_llm()

    # 把消息列表格式化为对话文本
    dialogue = "\n".join([
        f"{'用户' if m.role == 'user' else '助手'}: {m.content}"
        for m in messages
    ])

    prompt = f"""请将以下对话压缩为一段简洁的记忆摘要，供 AI 助手后续了解用户背景。

要求：
1. 提取用户透露的关键情绪状态、重要事件、个人信息（如工作、家庭、感情等）
2. 用第三人称描述，例如"用户提到..."
3. 200 字以内，纯文本，不要标题和分项
4. 重点保留对情绪陪伴有价值的信息

对话内容：
{dialogue}

请直接输出摘要文字："""

    try:
        response = llm.invoke([{"role": "user", "content": prompt}])
        if isinstance(response, str):
            return response.strip()
        elif hasattr(response, "content"):
            return response.content.strip()
        else:
            return str(response).strip()

    except Exception as e:
        print(f"  ⚠️  LLM 压缩失败，使用原始拼接: {e}")
        # 降级：直接拼接前 5 条内容作为摘要
        return "对话摘要（压缩失败）：" + " | ".join([
            f"{m.role}: {m.content[:50]}" for m in messages[:5]
        ])
