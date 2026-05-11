# backend/app/models/schemas.py


from pydantic import BaseModel, Field,field_validator
from datetime import datetime
from typing import List, Optional, Union

# ═══════════════════════════════════════════════
# 会话相关
# ═══════════════════════════════════════════════

class ConversationCreate(BaseModel):
    """新建会话请求体"""
    title:   str = Field(default="新对话", description="会话标题")
    persona: str = Field(default="gentle",  description="人设：gentle / rational / humorous")


class ConversationUpdate(BaseModel):
    """更新会话请求体"""
    title:   Optional[str] = Field(default=None)
    persona: Optional[str] = Field(default=None)


class ConversationOut(BaseModel):
    """会话响应体"""
    id:         int
    title:      str
    persona:    str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════
# 消息相关
# ═══════════════════════════════════════════════

class MessageCreate(BaseModel):
    """发送消息请求体"""
    conversation_id: int  = Field(..., description="所属会话 ID")
    content:         str  = Field(..., description="用户消息内容")


class MessageOut(BaseModel):
    """消息响应体"""
    id:              int
    conversation_id: int
    role:            str      # "user" 或 "assistant"
    content:         str
    created_at:      datetime

    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    """发送消息后的完整响应"""
    success:       bool
    message:       str = Field(default="")
    user_message:  Optional[MessageOut] = Field(default=None, description="已存储的用户消息")
    reply:         Optional[MessageOut] = Field(default=None, description="Agent 回复消息")


# ═══════════════════════════════════════════════
# 心情小记相关
# ═══════════════════════════════════════════════

class MoodEntryOut(BaseModel):
    """心情小记响应体"""
    id:               int
    date:             str         # YYYY-MM-DD
    score:            int         # 1-10
    summary_text:     str
    keywords:         List[str]   # 前端直接拿到列表，不用自己 JSON.parse
    conversation_ids: List[int]
    updated_at:       datetime

    model_config = {"from_attributes": True}


class MoodSummaryRequest(BaseModel):
    """触发今日心情总结请求体"""
    date: Optional[str] = Field(
        default=None,
        description="指定日期 YYYY-MM-DD，不传则默认今天"
    )


class MoodSummaryResponse(BaseModel):
    """心情总结响应"""
    success:  bool
    message:  str = Field(default="")
    data:     Optional[MoodEntryOut] = Field(default=None)


class MoodCalendarItem(BaseModel):
    """情绪记录板每格数据（前端日历渲染用）"""
    date:     str
    score:    int
    has_data: bool = True


# ═══════════════════════════════════════════════
# 记忆摘要相关
# ═══════════════════════════════════════════════

class MemorySummaryOut(BaseModel):
    """记忆摘要响应体"""
    id:              int
    conversation_id: int
    summary_text:    str
    message_count:   int
    created_at:      datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════
# 人设相关
# ═══════════════════════════════════════════════

class PersonaOut(BaseModel):
    """人设配置响应体"""
    id:           int
    name:         str
    display_name: str
    avatar_emoji: str
    # 注意：system_prompt 不返回给前端，属于后端内部配置

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════
# 天气相关
# ═══════════════════════════════════════════════

class WeatherSuggestions(BaseModel):
    """LLM 生成的三条建议"""
    travel:   str = Field(description="出行建议")
    food:     str = Field(description="饮食建议")
    clothing: str = Field(description="穿搭建议")


class WeatherOut(BaseModel):
    """天气查询响应体"""
    city:        str
    weather:     str           # 天气状况，例如"晴"
    temperature: str           # 温度，例如"28"
    wind:        str           # 风力，例如"南风3级"
    humidity:    str           # 湿度，例如"65%"
    suggestions: WeatherSuggestions
    cached:      bool = False  # 是否来自缓存


class WeatherResponse(BaseModel):
    success: bool
    message: str = Field(default="")
    data:    Optional[WeatherOut] = Field(default=None)


# ═══════════════════════════════════════════════
# 热点新闻相关
# ═══════════════════════════════════════════════

class NewsItem(BaseModel):
    """单条热点新闻"""
    title:       str
    description: Optional[str] = Field(default="")
    source:      str           # 新闻来源名称
    category:    str           # 社会 / 娱乐 / 科技 / 生活
    url:         Optional[str] = Field(default="")
    published_at: Optional[str] = Field(default="")


class NewsResponse(BaseModel):
    success: bool
    message: str = Field(default="")
    data:    List[NewsItem] = Field(default=[])


# ═══════════════════════════════════════════════
# RAG 相关（内部使用，不直接暴露给前端）
# ═══════════════════════════════════════════════

class RAGResult(BaseModel):
    """单条 RAG 检索结果"""
    text:       str            # 召回的历史文本片段
    date:       str            # 来源日期
    score:      float          # 相似度分数
    entry_type: str            # "mood_entry" 或 "message"


# ═══════════════════════════════════════════════
# 通用响应
# ═══════════════════════════════════════════════

class BaseResponse(BaseModel):
    """通用响应基类"""
    success: bool
    message: str = Field(default="")


class ErrorResponse(BaseModel):
    """错误响应"""
    success:    bool = False
    message:    str
    error_code: Optional[str] = Field(default=None)

class Location(BaseModel):
    """地理位置"""
    longitude: float = Field(..., description="经度")
    latitude: float = Field(..., description="纬度")

class POIInfo(BaseModel):
    """POI信息"""
    id: str = Field(..., description="POI ID")
    name: str = Field(..., description="名称")
    type: str = Field(..., description="类型")
    address: str = Field(..., description="地址")
    location: Location = Field(..., description="经纬度坐标")
    tel: Optional[str] = Field(default=None, description="电话")

class WeatherInfo(BaseModel):
    """天气信息"""
    date: str = Field(..., description="日期 YYYY-MM-DD")
    day_weather: str = Field(default="", description="白天天气")
    night_weather: str = Field(default="", description="夜间天气")
    day_temp: Union[int, str] = Field(default=0, description="白天温度")
    night_temp: Union[int, str] = Field(default=0, description="夜间温度")
    wind_direction: str = Field(default="", description="风向")
    wind_power: str = Field(default="", description="风力")

    @field_validator('day_temp', 'night_temp', mode='before')
    @classmethod
    def parse_temperature(cls, v):
        """解析温度,移除°C等单位"""
        if isinstance(v, str):
            # 移除°C, ℃等单位符号
            v = v.replace('°C', '').replace('℃', '').replace('°', '').strip()
            try:
                return int(v)
            except ValueError:
                return 0
        return v
