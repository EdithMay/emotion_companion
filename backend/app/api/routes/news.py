# backend/app/api/routes/news.py

from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import NewsResponse
from app.services.news_service import get_news_service

router = APIRouter(prefix="/news", tags=["热点新闻"])

@router.get(
    "",
    response_model=NewsResponse,
    summary="获取热点新闻列表"
)
def get_news(
    category: str = Query(default="社会", description="分类：社会/娱乐/科技/生活"),
    limit:    int = Query(default=5,    ge=1, le=10, description="返回条数")
):
    """
    侧栏热点话题区调用此接口。
    前端点击热点卡片后，自动填入输入框触发对话，Agent 完全被动。
    """
    try:
        svc  = get_news_service()
        news = svc.get_hot_news(category=category, limit=limit)
        return NewsResponse(
            success=True,
            message=f"获取 {category} 新闻成功",
            data=news
        )
    except ValueError as e:
        # AppCode 未配置
        raise HTTPException(status_code=503, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        print(f"❌ 新闻获取失败: {e}")
        raise HTTPException(status_code=500, detail=f"新闻获取失败: {str(e)}")
