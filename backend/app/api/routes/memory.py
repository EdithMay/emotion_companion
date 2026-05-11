# backend/app/api/routes/memory.py

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from ...database import get_db
from ...models.schemas import MemorySummaryOut
from ...services.memory_service import get_latest_summary
from ...models.db_models import MemorySummary

router = APIRouter(prefix="/memory", tags=["记忆管理"])

@router.get(
    "/{conversation_id}",
    response_model=list[MemorySummaryOut],
    summary="获取某会话的所有记忆摘要"
)
def get_memory(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    summaries = (
        db.query(MemorySummary)
        .filter(MemorySummary.conversation_id == conversation_id)
        .order_by(MemorySummary.created_at.desc())
        .all()
    )
    return summaries

@router.get(
    "/{conversation_id}/latest",
    summary="获取最新一条记忆摘要文本"
)
def get_latest_memory(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    text = get_latest_summary(db, conversation_id)
    return {
        "conversation_id": conversation_id,
        "summary":         text,
        "has_summary":     bool(text)
    }
