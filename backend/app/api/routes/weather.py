# backend/app/api/routes/weather.py

from fastapi import APIRouter, HTTPException, Query
from ...models.schemas import WeatherResponse
from ...services.weather_service import get_weather_service

router = APIRouter(prefix="/weather", tags=["天气"])

@router.get(
    "",
    response_model=WeatherResponse,
    summary="获取天气 + LLM 生成建议"
)
def get_weather(
    city: str   = Query(default=None,  description="城市名，与经纬度二选一"),
    lat:  float = Query(default=None,  description="纬度"),
    lng:  float = Query(default=None,  description="经度")
):
    """
    支持两种方式：
      1. 传 city 参数：直接按城市名查询
      2. 传 lat + lng：逆地理编码后查询

    前端优先使用 Geolocation API 传经纬度，
    用户未授权位置时退回传 city。
    """
    try:
        svc = get_weather_service()

        if lat is not None and lng is not None:
            data = svc.get_weather_by_location(lat, lng)
        elif city:
            data = svc.get_weather_by_city(city)
        else:
            raise HTTPException(
                status_code=400,
                detail="请提供 city 或 lat+lng 参数"
            )

        return WeatherResponse(
            success=True,
            message="查询成功",
            data=data
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 天气查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"天气查询失败: {str(e)}")
