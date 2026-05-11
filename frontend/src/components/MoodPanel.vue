<template>
  <aside class="mp">
    <!-- 顶栏 -->
    <div class="mp-header">
      <span class="mp-title">📊 情绪记录</span>
      <a-button size="small" :loading="summarizing" @click="doSummary">
        📝 今日总结
      </a-button>
    </div>

    <div class="mp-body">

      <!-- 今日心情 -->
      <div class="today-block">
        <div class="block-label">今日心情</div>
        <div v-if="todayEntry" class="today-content">
          <div class="today-score" :style="{ color: scoreColor(todayEntry.score) }">
            {{ todayEntry.score }}<span class="score-max">/10</span>
          </div>
          <div class="today-kws">
            <a-tag
              v-for="kw in todayEntry.keywords.slice(0, 4)"
              :key="kw"
              color="purple"
              style="font-size:10px;padding:0 5px;margin:0"
            >{{ kw }}</a-tag>
          </div>
        </div>
        <div v-else class="today-empty">还未生成今日小记</div>
      </div>

      <!-- 近 7 天趋势小点 -->
      <div class="week-trend">
        <div v-for="d in weekTrend" :key="d.date" class="trend-item">
          <div
            class="trend-dot"
            :style="{ background: d.score ? scoreColor(d.score) : '#e8e8e8' }"
            :title="`${d.date.slice(5)}: ${d.score || '无记录'}`"
          />
          <div class="trend-date">{{ d.date.slice(8) }}</div>
        </div>
      </div>

      <!-- 月历 -->
      <div class="month-nav">
        <span class="nav-btn" @click="prevMonth">‹</span>
        <span class="month-lbl">{{ year }} 年 {{ month }} 月</span>
        <span class="nav-btn" @click="nextMonth">›</span>
      </div>

      <div class="cal-grid">
        <div v-for="d in WEEK" :key="d" class="cal-head">{{ d }}</div>
        <div v-for="n in firstDow" :key="`p${n}`" />
        <div
          v-for="day in daysInMonth"
          :key="day"
          :class="['cal-cell', {
            'has-data': !!moodMap.get(ds(day)),
            'is-today': isToday(day)
          }]"
          :style="{ background: cellBg(day) }"
          @click="clickDay(day)"
        >
          <span class="cell-num">{{ day }}</span>
        </div>
      </div>

      <!-- 图例 -->
      <div class="legend">
        <span v-for="l in LEGEND" :key="l.label" class="leg">
          <span class="leg-dot" :style="{ background: l.color }" />{{ l.label }}
        </span>
      </div>

      <!-- 本月关键词云 -->
      <template v-if="wordCloud.length > 0">
        <div class="block-label" style="margin-top:14px;margin-bottom:6px">本月情绪词</div>
        <div class="word-cloud">
          <span
            v-for="(w, i) in wordCloud"
            :key="w.word"
            class="word-item"
            :style="{
              fontSize: `${Math.min(22, 11 + w.count * 3)}px`,
              color: COLORS[i % COLORS.length],
              fontWeight: w.count > 2 ? '600' : '400'
            }"
          >{{ w.word }}</span>
        </div>
      </template>

    </div>

    <!-- 日期详情弹窗 -->
    <a-modal
      v-model:open="showModal"
      :title="`${selectedEntry?.date ?? ''} 心情小记`"
      :footer="null"
      centered
    >
      <div v-if="selectedEntry" class="modal-body">
        <div class="modal-top">
          <div>
            <div style="font-size:12px;color:#aaa;margin-bottom:2px">情绪指数</div>
            <div class="modal-score" :style="{ color: scoreColor(selectedEntry.score) }">
              {{ selectedEntry.score }}<span style="font-size:13px;color:#bbb">/10</span>
            </div>
          </div>
          <div class="modal-kws">
            <a-tag v-for="kw in selectedEntry.keywords" :key="kw" color="purple">{{ kw }}</a-tag>
          </div>
        </div>
        <a-divider style="margin:10px 0" />
        <p class="modal-text">{{ selectedEntry.summary_text }}</p>
      </div>
    </a-modal>

  </aside>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import {
  getMoodCalendar, getMoodEntryByDate,
  getAllMoodEntries, generateMoodSummary
} from '../services/api'
import type { MoodEntryOut } from '../types'

const WEEK   = ['日','一','二','三','四','五','六']
const LEGEND = [
  { label: '低落', color: '#1565C0' },
  { label: '平淡', color: '#64B5F6' },
  { label: '平稳', color: '#FFF176' },
  { label: '愉快', color: '#FFB74D' },
  { label: '很好', color: '#FF5722' },
]
const COLORS = ['#667eea','#764ba2','#f5576c','#4facfe','#43e97b','#fa709a','#f093fb','#fee140']

// ── 月份 ──────────────────────────────────────────
const now   = dayjs()
const year  = ref(now.year())
const month = ref(now.month() + 1)

const prevMonth = () => { if (month.value === 1) { year.value--; month.value = 12 } else month.value-- }
const nextMonth = () => { if (month.value === 12) { year.value++; month.value = 1 } else month.value++ }

const pad = (n: number) => String(n).padStart(2, '0')
const ds  = (d: number) => `${year.value}-${pad(month.value)}-${pad(d)}`

const firstDow    = computed(() => dayjs(`${year.value}-${pad(month.value)}-01`).day())
const daysInMonth = computed(() => dayjs(`${year.value}-${pad(month.value)}-01`).daysInMonth())
const isToday     = (d: number) => ds(d) === now.format('YYYY-MM-DD')

// ── 数据 ──────────────────────────────────────────
const moodMap    = ref<Map<string, number>>(new Map())
const allEntries = ref<MoodEntryOut[]>([])
const todayEntry = ref<MoodEntryOut | null>(null)

const loadCalendar = async () => {
  try {
    const items = await getMoodCalendar(year.value, month.value)
    moodMap.value = new Map(items.map(i => [i.date, i.score]))
  } catch {}
}

const loadAll = async () => {
  try {
    allEntries.value = await getAllMoodEntries()
    todayEntry.value = allEntries.value.find(e => e.date === now.format('YYYY-MM-DD')) ?? null
  } catch {}
}

watch([year, month], loadCalendar)

// ── 近 7 天趋势 ────────────────────────────────────
const weekTrend = computed(() =>
  Array.from({ length: 7 }, (_, i) => {
    const d = now.subtract(6 - i, 'day').format('YYYY-MM-DD')
    return { date: d, score: allEntries.value.find(e => e.date === d)?.score ?? 0 }
  })
)

// ── 本月关键词云 ───────────────────────────────────
const wordCloud = computed(() => {
  const mStr = `${year.value}-${pad(month.value)}`
  const freq: Record<string, number> = {}
  allEntries.value
    .filter(e => e.date.startsWith(mStr))
    .forEach(e => e.keywords.forEach(kw => { freq[kw] = (freq[kw] ?? 0) + 1 }))
  return Object.entries(freq)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 18)
    .map(([word, count]) => ({ word, count }))
})

// ── 颜色 ──────────────────────────────────────────
const cellBg = (d: number) => {
  const s = moodMap.value.get(ds(d))
  if (!s) return '#F0F0F0'
  if (s <= 2) return '#1565C0'
  if (s <= 4) return '#64B5F6'
  if (s <= 6) return '#FFF176'
  if (s <= 8) return '#FFB74D'
  return '#FF5722'
}

const scoreColor = (s: number) => {
  if (s <= 2) return '#1565C0'
  if (s <= 4) return '#4da6ff'
  if (s <= 6) return '#f5a623'
  if (s <= 8) return '#ff8c00'
  return '#FF5722'
}

// ── 弹窗 ──────────────────────────────────────────
const showModal     = ref(false)
const selectedEntry = ref<MoodEntryOut | null>(null)

const clickDay = async (d: number) => {
  const date = ds(d)
  if (!moodMap.value.has(date)) return
  try {
    selectedEntry.value = await getMoodEntryByDate(date)
    showModal.value = true
  } catch {}
}

// ── 生成今日总结 ───────────────────────────────────
const summarizing = ref(false)

const doSummary = async () => {
  summarizing.value = true
  try {
    const res = await generateMoodSummary({})
    if (res.success && res.data) {
      message.success('今日心情小记已生成')
      await Promise.all([loadCalendar(), loadAll()])
    } else {
      message.warning(res.message || '今天还没有对话记录哦')
    }
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '生成失败')
  }
  summarizing.value = false
}

onMounted(() => { loadCalendar(); loadAll() })
</script>

<style scoped>
.mp         { width: 280px; flex-shrink: 0; height: 100vh; background: white; border-left: 1px solid #eee; display: flex; flex-direction: column; overflow: hidden; }
.mp-header  { display: flex; justify-content: space-between; align-items: center; padding: 14px 14px 10px; border-bottom: 1px solid #f0f0f0; flex-shrink: 0; }
.mp-title   { font-size: 14px; font-weight: 600; color: #333; }
.mp-body    { flex: 1; overflow-y: auto; padding: 12px 14px; }

.today-block   { background: linear-gradient(135deg,#f8f0ff,#f0f4ff); border-radius: 12px; padding: 10px 12px; margin-bottom: 10px; }
.block-label   { font-size: 11px; color: #aaa; margin-bottom: 4px; }
.today-content { display: flex; align-items: center; gap: 10px; }
.today-score   { font-size: 30px; font-weight: 700; line-height: 1; flex-shrink: 0; }
.score-max     { font-size: 12px; color: #bbb; }
.today-kws     { display: flex; flex-wrap: wrap; gap: 3px; }
.today-empty   { font-size: 11px; color: #ccc; text-align: center; padding: 4px 0; }

.week-trend    { display: flex; justify-content: space-between; margin-bottom: 12px; padding: 4px 0; }
.trend-item    { display: flex; flex-direction: column; align-items: center; gap: 3px; }
.trend-dot     { width: 22px; height: 22px; border-radius: 50%; transition: transform 0.15s; cursor: default; }
.trend-dot:hover { transform: scale(1.2); }
.trend-date    { font-size: 9px; color: #bbb; }

.month-nav  { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.nav-btn    { font-size: 20px; color: #999; cursor: pointer; padding: 0 2px; user-select: none; line-height: 1; }
.nav-btn:hover { color: #667eea; }
.month-lbl  { font-size: 13px; font-weight: 600; color: #333; }

.cal-grid   { display: grid; grid-template-columns: repeat(7, 1fr); gap: 3px; margin-bottom: 8px; }
.cal-head   { text-align: center; font-size: 9px; color: #ccc; padding-bottom: 3px; }
.cal-cell   { aspect-ratio: 1; border-radius: 5px; background: #f0f0f0; display: flex; align-items: center; justify-content: center; cursor: default; transition: transform 0.15s; position: relative; }
.cal-cell.has-data { cursor: pointer; }
.cal-cell.has-data:hover { transform: scale(1.15); z-index: 1; }
.cal-cell.is-today { outline: 2px solid #667eea; outline-offset: 1px; }
.cell-num   { font-size: 10px; color: rgba(0,0,0,0.45); font-weight: 500; line-height: 1; }

.legend     { display: flex; gap: 8px; flex-wrap: wrap; }
.leg        { display: flex; align-items: center; gap: 2px; font-size: 10px; color: #aaa; }
.leg-dot    { width: 8px; height: 8px; border-radius: 2px; flex-shrink: 0; }

.word-cloud { display: flex; flex-wrap: wrap; gap: 6px 10px; align-items: baseline; }
.word-item  { line-height: 1.5; cursor: default; transition: transform 0.2s; }
.word-item:hover { transform: scale(1.1); }

.modal-body { padding: 4px 0; }
.modal-top  { display: flex; justify-content: space-between; align-items: center; }
.modal-score{ font-size: 34px; font-weight: 700; }
.modal-kws  { display: flex; flex-wrap: wrap; gap: 4px; justify-content: flex-end; max-width: 180px; }
.modal-text { font-size: 14px; color: #444; line-height: 1.8; margin: 0; }
</style>
