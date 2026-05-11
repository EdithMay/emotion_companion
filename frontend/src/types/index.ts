export interface ConversationOut {
  id: number
  title: string
  persona: string
  created_at: string
  updated_at: string
}

export interface ConversationCreate {
  title?: string
  persona?: string
}

export interface MessageOut {
  id: number
  conversation_id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface MessageCreate {
  conversation_id: number
  content: string
}

export interface ChatResponse {
  success: boolean
  message: string
  user_message?: MessageOut
  reply?: MessageOut
}

export interface MoodEntryOut {
  id: number
  date: string
  score: number
  summary_text: string
  keywords: string[]
  conversation_ids: number[]
  updated_at: string
}

export interface MoodCalendarItem {
  date: string
  score: number
  has_data: boolean
}

export interface MoodSummaryRequest {
  date?: string
}

export interface MoodSummaryResponse {
  success: boolean
  message: string
  data?: MoodEntryOut
}

export interface WeatherSuggestions {
  travel: string
  food: string
  clothing: string
}

export interface WeatherOut {
  city: string
  weather: string
  temperature: string
  wind: string
  humidity: string
  suggestions: WeatherSuggestions
  cached: boolean
}

export interface WeatherResponse {
  success: boolean
  message: string
  data?: WeatherOut
}

export interface NewsItem {
  title: string
  description: string
  source: string
  category: string
  url: string
  published_at: string
}

export interface NewsResponse {
  success: boolean
  message: string
  data: NewsItem[]
}

export interface MemorySummaryOut {
  id: number
  conversation_id: number
  summary_text: string
  message_count: number
  created_at: string
}

export type PersonaType = 'gentle' | 'rational' | 'humorous'

export interface PersonaOption {
  name: PersonaType
  displayName: string
  emoji: string
}
