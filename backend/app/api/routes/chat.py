# backend/app/api/routes/chat.py

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from ...database import get_db
from ...models.schemas import (
    ConversationCreate, ConversationOut,
    MessageCreate, ChatResponse, MessageOut
)
from ...models.db_models import Conversation, Message
from ...agents.companion_agent import get_companion_agent

router = APIRouter(prefix="/chat", tags=["对话"])

# ── 会话管理 ──────────────────────────────────────────────────

@router.get(
    "/conversations",
    response_model=list[ConversationOut],
    summary="获取所有会话列表"
)
def get_conversations(db: Session = Depends(get_db)):
    """按最后更新时间倒序返回所有会话"""
    convs = (
        db.query(Conversation)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return convs

@router.post(
    "/conversations",
    response_model=ConversationOut,
    summary="新建会话"
)
def create_conversation(
    body: ConversationCreate,
    db:   Session = Depends(get_db)
):
    conv = Conversation(
        title=body.title,
        persona=body.persona
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv

@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationOut,
    summary="更新会话标题或人设"
)
def update_conversation(
    conversation_id: int,
    body: ConversationCreate,
    db:   Session = Depends(get_db)
):
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    if body.title:
        conv.title = body.title
    if body.persona:
        conv.persona = body.persona
    db.commit()
    db.refresh(conv)
    return conv

@router.delete(
    "/conversations/{conversation_id}",
    summary="删除会话"
)
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    db.delete(conv)
    db.commit()
    return {"success": True, "message": "会话已删除"}

@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageOut],
    summary="获取某会话的完整消息历史"
)
def get_messages(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return messages

# ── 核心对话接口 ──────────────────────────────────────────────

@router.post(
    "/message",
    response_model=ChatResponse,
    summary="发送消息，获取 Agent 回复"
)
def send_message(
    body: MessageCreate,
    db:   Session = Depends(get_db)
):
    """
    前端发送用户消息，后端执行完整的 5 层 prompt 构建并返回 Agent 回复。
    """
    # 确认会话存在
    conv = db.query(Conversation).filter(
        Conversation.id == body.conversation_id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")

    try:
        agent    = get_companion_agent()
        response = agent.chat(db, body.conversation_id, body.content)
        return response
    except Exception as e:
        print(f"❌ Agent 对话失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"对话失败: {str(e)}")

from fastapi.responses import StreamingResponse

@router.post(
    "/message/stream",
    summary="发送消息（流式返回）",
    response_class=StreamingResponse
)
def send_message_stream(
    body: MessageCreate,
    db:   Session = Depends(get_db)
):
    """
    SSE 流式接口，前端用 fetch + ReadableStream 消费。
    Content-Type: text/event-stream
    """
    conv = db.query(Conversation).filter(
        Conversation.id == body.conversation_id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")

    try:
        agent = get_companion_agent()

        def event_stream():
            yield "data: [START]\n\n"
            yield from agent.stream_chat(db, body.conversation_id, body.content)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control":               "no-cache",
                "X-Accel-Buffering":           "no",
                "Access-Control-Allow-Origin": "*",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", summary="对话服务健康检查")
def health_check():
    agent = get_companion_agent()
    return {
        "status":  "healthy",
        "service": "companion-agent",
        "rag_count": agent.rag.count()
    }
