import axios from 'axios'
import type {
  ConversationOut, ConversationCreate,
  MessageOut, MessageCreate, ChatResponse,
  MoodSummaryRequest, MoodSummaryResponse,
  MoodEntryOut, MoodCalendarItem,
  MemorySummaryOut,
  WeatherResponse,
  NewsResponse,
} from '../types'

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const http = axios.create({ baseURL: BASE, timeout: 120000 })

http.interceptors.response.use(
  r => r,
  e => { console.error('[API]', e.response?.status, e.config?.url); return Promise.reject(e) }
)

// ── 会话 ──────────────────────────────────────────────────────
export const getConversations = () =>
  http.get<ConversationOut[]>('/api/chat/conversations').then(r => r.data)

export const createConversation = (data: ConversationCreate) =>
  http.post<ConversationOut>('/api/chat/conversations', data).then(r => r.data)

export const updateConversation = (id: number, data: ConversationCreate) =>
  http.patch<ConversationOut>(`/api/chat/conversations/${id}`, data).then(r => r.data)

export const deleteConversation = (id: number) =>
  http.delete(`/api/chat/conversations/${id}`).then(r => r.data)

export const getMessages = (cid: number) =>
  http.get<MessageOut[]>(`/api/chat/conversations/${cid}/messages`).then(r => r.data)

export const sendMessage = (data: MessageCreate) =>
  http.post<ChatResponse>('/api/chat/message', data).then(r => r.data)

// ── 心情 ──────────────────────────────────────────────────────
export const generateMoodSummary = (data: MoodSummaryRequest) =>
  http.post<MoodSummaryResponse>('/api/mood/summary', data).then(r => r.data)

export const getAllMoodEntries = () =>
  http.get<MoodEntryOut[]>('/api/mood/entries').then(r => r.data)

export const getMoodCalendar = (year: number, month: number) =>
  http.get<MoodCalendarItem[]>('/api/mood/entries/calendar', { params: { year, month } }).then(r => r.data)

export const getMoodEntryByDate = (date: string) =>
  http.get<MoodEntryOut>(`/api/mood/entries/${date}`).then(r => r.data)

// ── 天气 ──────────────────────────────────────────────────────
export const getWeather = (params: { city?: string; lat?: number; lng?: number }) =>
  http.get<WeatherResponse>('/api/weather', { params }).then(r => r.data)

// ── 新闻 ──────────────────────────────────────────────────────
export const getNews = (category = '社会', limit = 5) =>
  http.get<NewsResponse>('/api/news', { params: { category, limit } }).then(r => r.data)

// ── 记忆 ──────────────────────────────────────────────────────
export const getMemory = (cid: number) =>
  http.get<MemorySummaryOut[]>(`/api/memory/${cid}`).then(r => r.data)


/**
 * 流式发送消息，通过回调逐 token 更新 UI
 *
 * @param data         请求体
 * @param onToken      每收到一个 token 时调用
 * @param onDone       流结束时调用，返回 agent 消息的 id 和 created_at
 * @param onUserMsg    收到用户消息元信息时调用
 * @param onError      发生错误时调用
 * @param onToolUsing  【新增】后端正在调用工具/查记忆时调用
 */
export async function sendMessageStream(
  data: MessageCreate,
  onToken:    (token: string) => void,
  onDone:     (meta: { id: number; created_at: string }) => void,
  onUserMsg:  (meta: { id: number; created_at: string }) => void,
  onError:    (msg: string) => void,
  onToolUsing?: () => void    // 👈 这里新增了参数
): Promise<void> {
  const url = `${BASE}/api/chat/message/stream`

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })

  if (!response.ok || !response.body) {
    onError(`请求失败 ${response.status}`)
    return
  }

  const reader  = response.body.getReader()
  const decoder = new TextDecoder()
  let   buffer  = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // SSE 每条消息以 \n\n 结尾
    const lines = buffer.split('\n\n')
    buffer = lines.pop() ?? ''   // 最后一段可能不完整，留到下次

    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed.startsWith('data:')) continue

      const payload = trimmed.slice(5).trim()

      if (payload === '[START]') {
        continue
      } else if (payload.startsWith('[USER_MSG]')) {
        try {
          const meta = JSON.parse(payload.slice(10))
          onUserMsg(meta)
        } catch {}
      } else if (payload.startsWith('[DONE]')) {
        try {
          const meta = JSON.parse(payload.slice(6))
          if (meta.id) onDone(meta)
        } catch {}
      } else if (payload.startsWith('[ERROR]')) {
        onError(payload.slice(7))
      } else if (payload === '[TOOL_USING]') {
        // 👈 这里新增了解析 [TOOL_USING] 事件
        onToolUsing?.()
      } else {
        // 普通 token
        try {
          const token = JSON.parse(payload)
          onToken(token)
        } catch {
          onToken(payload)
        }
      }
    }
  }
}