# backend/app/services/weather_service.py

import json
import time
import re
from typing import Optional
from ..models.schemas import WeatherOut, WeatherSuggestions
from ..services.llm_service import get_llm
from ..services.amap_service import get_amap_service

_weather_cache: dict = {}
CACHE_TTL = 3600


class WeatherService:

    def __init__(self):
        self.llm = get_llm()

    def get_weather_by_location(self, lat: float, lng: float) -> WeatherOut:
        """经纬度 → 城市名 → 天气"""
        cache_key = f"{round(lat, 2)}_{round(lng, 2)}"
        if self._is_cache_valid(cache_key):
            print(f"  ☁️  天气数据命中缓存")
            result = _weather_cache[cache_key]["data"]
            result.cached = True
            return result

        # 逆地理编码获取城市
        city = self._reverse_geocode(lat, lng)
        print(f"  📍 逆地理编码结果: {city}")
        return self.get_weather_by_city(city)

    def _reverse_geocode(self, lat: float, lng: float) -> str:
        """
        调用高德 maps_regeocode 接口，经纬度 → 城市名。
        注意：高德地图只覆盖中国境内，境外坐标会返回空或失败。
        """
        try:
            amap   = get_amap_service()
            result = amap.mcp_tool.run({
                "action":    "call_tool",
                "tool_name": "maps_regeocode",
                "arguments": {"location": f"{lng},{lat}"}
            })
            print(f"  逆地理编码原始结果: {result[:200]}")

            # 尝试解析 JSON
            try:
                if "{" in result:
                    start = result.find("{")
                    end   = result.rfind("}") + 1
                    data  = json.loads(result[start:end])
                    comp  = (
                        data.get("regeocode", {})
                            .get("addressComponent", {})
                    )
                    city  = comp.get("city") or comp.get("province", "")
                    if isinstance(city, list):
                        city = city[0] if city else ""
                    if city:
                        return city.replace("市", "").replace("省", "")
            except Exception:
                pass

            # 文本提取兜底
            match = re.search(r'[\u4e00-\u9fa5]{2,4}(?:市|区)', result)
            if match:
                return match.group().replace("市", "").replace("区", "")

        except Exception as e:
            print(f"  ⚠️  逆地理编码失败: {e}")

        return "北京"

    def get_weather_by_city(self, city: str) -> WeatherOut:
        """城市名 → 天气数据 + LLM 建议"""
        cache_key = f"city_{city}"
        if self._is_cache_valid(cache_key):
            print(f"  ☁️  {city} 天气命中缓存")
            result = _weather_cache[cache_key]["data"]
            result.cached = True
            return result

        print(f"  🌐 查询城市天气: {city}")
        amap        = get_amap_service()
        raw         = amap.get_weather(city)
        parsed      = self._parse_weather(raw, city)
        suggestions = self._generate_suggestions(parsed)

        result = WeatherOut(
            city=parsed.get("city", city),
            weather=parsed.get("weather", "晴"),
            temperature=parsed.get("temperature", "25"),
            wind=parsed.get("wind", "微风"),
            humidity=parsed.get("humidity", "50%"),
            suggestions=suggestions,
            cached=False
        )

        _weather_cache[cache_key] = {"data": result, "timestamp": time.time()}
        return result

    def _parse_weather(self, raw: str, city: str) -> dict:
        """解析高德天气返回，兼容实时天气和预报两种格式"""
        try:
            if "{" in raw:
                start = raw.find("{")
                end   = raw.rfind("}") + 1
                data  = json.loads(raw[start:end])

                # 实时天气 lives[]
                lives = data.get("lives", [])
                if lives:
                    live = lives[0]
                    return {
                        "city":        live.get("city", city),
                        "weather":     live.get("weather", "晴"),
                        "temperature": live.get("temperature", "25"),
                        "wind":        f"{live.get('winddirection','')}风{live.get('windpower','')}级",
                        "humidity":    f"{live.get('humidity', '50')}%"
                    }

                # 预报 forecasts[]
                forecasts = data.get("forecasts", [])
                if forecasts:
                    today = forecasts[0]
                    casts = today.get("casts", [{}])
                    cast  = casts[0] if casts else {}
                    return {
                        "city":        today.get("city", city),
                        "weather":     cast.get("dayweather", "晴"),
                        "temperature": cast.get("daytemp", "25"),
                        "wind":        f"{cast.get('daywind','')}风{cast.get('daypower','')}级",
                        "humidity":    "暂无"
                    }
        except Exception as e:
            print(f"  ⚠️  天气数据解析失败: {e}")

        return {"city": city, "weather": "晴", "temperature": "25",
                "wind": "微风", "humidity": "暂无"}

    def _generate_suggestions(self, weather: dict) -> WeatherSuggestions:
        prompt = (
            f"当前天气：{weather.get('city')} "
            f"{weather.get('weather')} "
            f"{weather.get('temperature')}°C "
            f"{weather.get('wind')} 湿度{weather.get('humidity')}\n"
            "请生成三条温馨建议，严格按 JSON 返回，不要 markdown：\n"
            '{"travel":"出行建议20字内","food":"饮食建议20字内","clothing":"穿搭建议20字内"}'
        )
        try:
            resp = self.llm.invoke([{"role": "user", "content": prompt}])
            text = resp if isinstance(resp, str) else getattr(resp, "content", str(resp))
            text = text.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(text)
            return WeatherSuggestions(
                travel=data.get("travel", "注意天气变化，合理出行"),
                food=data.get("food", "均衡饮食，多补充水分"),
                clothing=data.get("clothing", "根据气温适当增减衣物")
            )
        except Exception as e:
            print(f"  ⚠️  建议生成失败: {e}")
            temp = int(weather.get("temperature", 25))
            return WeatherSuggestions(
                travel="注意天气变化" if "雨" not in weather.get("weather","") else "记得带伞",
                food="多喝水，清淡饮食" if temp > 25 else "适当温补，注意保暖",
                clothing="短袖防晒" if temp > 28 else "轻薄外套" if temp > 15 else "厚外套保暖"
            )

    def _is_cache_valid(self, key: str) -> bool:
        if key not in _weather_cache:
            return False
        return time.time() - _weather_cache[key]["timestamp"] < CACHE_TTL

    def clear_cache(self):
        _weather_cache.clear()


def get_weather_service() -> WeatherService:
    return WeatherService()
