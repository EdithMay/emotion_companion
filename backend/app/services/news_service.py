# backend/app/services/news_service.py

import requests
from typing import List
from ..config import get_settings
from ..models.schemas import NewsItem

# 全局单例
_news_service = None


class NewsService:
    """阿里云市场热点新闻拉取服务 (极速数据)"""

    def __init__(self):
        settings = get_settings()
        # 这里的 key 对应的是阿里云的 AppCode
        self.appcode = settings.news_api_key

        # 极速数据获取新闻的接口 URL
        self.base_url = "https://jisunews.market.alicloudapi.com/news/get"

        # 极速数据直接支持中文频道名，这里做一层保险映射
        # 支持的频道包括：头条、新闻、财经、体育、娱乐、军事、教育、科技、NBA、股票、星座、女性、健康、育儿
        self.category_map = {
            "社会": "新闻",
            "娱乐": "娱乐",
            "科技": "科技",
            "生活": "健康"  # 将我们的"生活"映射到它的"健康"或"女性"频道
        }

    def get_hot_news(self, category: str = "社会", limit: int = 5) -> List[NewsItem]:
        """拉取指定分类的热点新闻"""

        # 【严谨逻辑】：没有配置 AppCode，直接拒绝请求，不造假
        if not self.appcode:
            print(f"  ⚠️ 拒绝拉取：未配置阿里云 AppCode (NEWS_API_KEY)")
            raise ValueError("未配置新闻 AppCode，无法获取热点数据")

        api_channel = self.category_map.get(category, "新闻")

        try:
            print(f"  📰 正在通过阿里云拉取【{category}】({api_channel}) 分类的真实新闻...")

            # 阿里云 API 要求的 Header 鉴权方式
            headers = {
                "Authorization": f"APPCODE {self.appcode}",
                "Content-Type": "application/json; charset=UTF-8"
            }

            # 请求参数
            params = {
                "channel": api_channel,
                "num": limit + 5,  # 多拉取几条以备过滤
                "start": 0
            }

            response = requests.get(
                self.base_url,
                headers=headers,
                params=params,
                timeout=8  # 严格控制超时时间
            )
            response.raise_for_status()
            data = response.json()

            # 极速数据的返回格式判断：status 为 0 表示成功
            if str(data.get("status")) != "0":
                error_msg = data.get("msg", "未知错误")
                print(f"  ❌ 阿里云接口返回错误: {error_msg}")
                raise RuntimeError(f"API报错: {error_msg}")

            news_list = []
            # 极速数据的新闻列表放在 result.list 中
            articles = data.get("result", {}).get("list", [])

            # 【严谨逻辑】：接口通了，但没数据，诚实地返回空列表
            if not articles:
                print(f"  ⚠️ 接口正常，但当前分类未返回任何新闻数据")
                return []

            for article in articles:
                title = article.get("title")
                # 过滤失效数据
                if not title:
                    continue

                news_list.append(NewsItem(
                    title=title,
                    description=article.get("content", "")[:100],  # 截取前100字作为简介
                    source=article.get("src") or "网络",
                    category=category,
                    url=article.get("url") or "",
                    published_at=article.get("time") or ""
                ))

                if len(news_list) >= limit:
                    break

            print(f"  ✅ 成功获取 {len(news_list)} 条真实新闻")
            return news_list

        except Exception as e:
            # 【严谨逻辑】：网络或解析错误，向上抛出异常，交给路由层处理
            print(f"  ❌ 获取 {category} 新闻失败: {e}")
            raise RuntimeError(f"获取新闻数据失败: {str(e)}")


def get_news_service() -> NewsService:
    """获取热点新闻服务实例 (单例模式)"""
    global _news_service
    if _news_service is None:
        _news_service = NewsService()
    return _news_service

_news_service_instance = None

def get_news_service() -> NewsService:
    global _news_service_instance
    if _news_service_instance is None:
        _news_service_instance = NewsService()
    return _news_service_instance