<template>
  <div class="w-widget">
    <!-- 加载中 -->
    <div v-if="loading" class="w-loading">⏳ 获取天气中...</div>

    <!-- 正常展示 -->
    <template v-else-if="data">
      <div class="w-row">
        <span class="w-icon">{{ icon }}</span>
        <div class="w-info">
          <div class="w-city-row">
            <span class="w-city">{{ data.city }}</span>
            <span class="w-edit" @click="showInput = !showInput" title="切换城市">✏️</span>
          </div>
          <div class="w-temp">{{ data.temperature }}°C <span class="w-desc">{{ data.weather }}</span></div>
        </div>
      </div>

      <!-- 手动切换城市输入框 -->
      <div v-if="showInput" class="w-city-input">
        <a-input
          v-model:value="manualCity"
          placeholder="输入城市名，如：上海"
          size="small"
          @pressEnter="loadByCity"
        >
          <template #suffix>
            <span style="cursor:pointer;color:#667eea" @click="loadByCity">确定</span>
          </template>
        </a-input>
      </div>

      <a-collapse ghost :bordered="false" style="margin-top:4px">
        <a-collapse-panel key="s" header="今日建议 ▸">
          <div class="w-tips">
            <div>☀️ {{ data.suggestions.travel }}</div>
            <div>🥗 {{ data.suggestions.food }}</div>
            <div>👕 {{ data.suggestions.clothing }}</div>
          </div>
        </a-collapse-panel>
      </a-collapse>
    </template>

    <!-- 失败/未加载 -->
    <div v-else>
      <div class="w-city-input">
        <a-input
          v-model:value="manualCity"
          placeholder="输入城市查询天气，如：北京"
          size="small"
          @pressEnter="loadByCity"
        >
          <template #suffix>
            <span style="cursor:pointer;color:#667eea" @click="loadByCity">查询</span>
          </template>
        </a-input>
      </div>
      <div class="w-retry" @click="load">🌤️ 或自动定位</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getWeather } from '../services/api'
import type { WeatherOut } from '../types'

const data       = ref<WeatherOut | null>(null)
const loading    = ref(false)
const showInput  = ref(false)
const manualCity = ref('')

const ICONS: Record<string, string> = {
  '晴':'☀️','多云':'⛅','阴':'☁️','小雨':'🌦️','中雨':'🌧️',
  '大雨':'⛈️','雪':'❄️','雾':'🌫️','霾':'😷','沙':'🌪️'
}

const icon = computed(() => {
  if (!data.value) return '🌤️'
  for (const k of Object.keys(ICONS)) {
    if (data.value.weather.includes(k)) return ICONS[k]
  }
  return '🌤️'
})

const loadByCity = async () => {
  const city = manualCity.value.trim()
  if (!city) return
  loading.value = true
  showInput.value = false
  try {
    const r = await getWeather({ city })
    if (r.success && r.data) data.value = r.data
  } catch {}
  loading.value = false
  manualCity.value = ''
}

const load = async () => {
  loading.value = true
  const fallback = async () => {
    const r = await getWeather({ city: '北京' })
    if (r.success && r.data) data.value = r.data
  }
  try {
    if (!navigator.geolocation) { await fallback(); loading.value = false; return }
    await new Promise<void>(resolve => {
      navigator.geolocation.getCurrentPosition(
        async pos => {
          try {
            const r = await getWeather({ lat: pos.coords.latitude, lng: pos.coords.longitude })
            if (r.success && r.data) data.value = r.data
            else await fallback()
          } catch { await fallback() }
          resolve()
        },
        async () => { await fallback(); resolve() },
        { timeout: 5000 }
      )
    })
  } catch { await fallback() }
  loading.value = false
}

onMounted(load)
</script>

<style scoped>
.w-widget    { background: linear-gradient(135deg,#e8f4ff,#f0f8ff); border-radius: 12px; padding: 10px 12px; margin-bottom: 8px; }
.w-loading   { font-size: 12px; color: #888; text-align: center; padding: 8px; }
.w-row       { display: flex; align-items: center; gap: 10px; }
.w-icon      { font-size: 28px; }
.w-info      { flex: 1; }
.w-city-row  { display: flex; align-items: center; gap: 4px; }
.w-city      { font-size: 11px; color: #888; }
.w-edit      { font-size: 11px; cursor: pointer; opacity: 0.6; }
.w-edit:hover{ opacity: 1; }
.w-temp      { font-size: 18px; font-weight: 600; color: #222; }
.w-desc      { font-size: 12px; font-weight: 400; color: #888; }
.w-city-input{ margin: 6px 0; }
.w-tips      { display: flex; flex-direction: column; gap: 3px; font-size: 11px; color: #555; line-height: 1.6; }
.w-retry     { font-size: 11px; color: #1890ff; cursor: pointer; text-align: center; padding: 4px; }
:deep(.ant-collapse-header) { padding: 4px 0 !important; font-size: 11px !important; color: #999 !important; }
:deep(.ant-collapse-content-box) { padding: 2px 0 4px !important; }
</style>
