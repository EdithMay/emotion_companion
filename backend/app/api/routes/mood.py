# backend/app/api/routes/mood.py

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import date
from ...database import get_db
from ...models.schemas import (
    MoodSummaryRequest, MoodSummaryResponse,
    MoodEntryOut, MoodCalendarItem
)
from ...services.summary_service import (
    generate_mood_summary,
    get_mood_entry_by_date,
    get_all_mood_entries
)

router = APIRouter(prefix="/mood", tags=["心情记录"])

@router.post(
    "/summary",
    response_model=MoodSummaryResponse,
    summary="触发今日心情总结"
)
def create_mood_summary(
    body: MoodSummaryRequest,
    db:   Session = Depends(get_db)
):
    """
    分析今日（或指定日期）所有对话，生成心情小记。
    同一天可多次调用，每次覆盖之前的记录。
    """
    try:
        target_date = body.date or date.today().strftime("%Y-%m-%d")
        entry = generate_mood_summary(db, target_date)
        return MoodSummaryResponse(
            success=True,
            message="心情小记生成成功",
            data=entry
        )
    except ValueError as e:
        # 今天没有对话记录
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ 心情总结失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")

@router.get(
    "/entries",
    response_model=list[MoodEntryOut],
    summary="获取所有心情记录（情绪记录板用）"
)
def get_all_entries(db: Session = Depends(get_db)):
    return get_all_mood_entries(db)

@router.get(
    "/entries/calendar",
    response_model=list[MoodCalendarItem],
    summary="获取指定月份的日历数据"
)
def get_calendar(
    year:  int,
    month: int,
    db:    Session = Depends(get_db)
):
    """
    返回指定年月的每日情绪得分，前端用于渲染方格日历。
    只返回有记录的日期，无记录的日期前端显示灰色。
    """
    month_str = f"{year}-{month:02d}"
    from app.models.db_models import MoodEntry
    entries = (
        db.query(MoodEntry)
        .filter(MoodEntry.date.like(f"{month_str}%"))
        .order_by(MoodEntry.date.asc())
        .all()
    )
    return [
        MoodCalendarItem(date=e.date, score=e.score)
        for e in entries
    ]

@router.get(
    "/entries/{entry_date}",
    response_model=MoodEntryOut,
    summary="获取某天的心情小记详情"
)
def get_entry_by_date(
    entry_date: str,
    db:         Session = Depends(get_db)
):
    entry = get_mood_entry_by_date(db, entry_date)
    if not entry:
        raise HTTPException(
            status_code=404,
            detail=f"{entry_date} 没有心情记录"
        )
    return entry
