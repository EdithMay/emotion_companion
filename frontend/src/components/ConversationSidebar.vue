<template>
  <aside class="sidebar">
    <!-- 顶部固定区 -->
    <div class="sidebar-fixed">
      <div class="sb-header">
        <div class="sb-logo">
          <span style="font-size:22px">🌳</span>
          <span class="sb-title">树洞</span>
        </div>
      </div>
      <div class="sb-scroll-top">
        <WeatherWidget />
        <HotTopicCard @click="$emit('topic-click', $event)" />

        <div class="section-label">陪伴风格</div>
        <div class="persona-row">
          <div
            v-for="p in PERSONAS"
            :key="p.name"
            :class="['persona-btn', { active: persona === p.name }]"
            @click="switchPersona(p.name)"
          >
            <span style="font-size:16px">{{ p.emoji }}</span>
            <span class="persona-name">{{ p.displayName }}</span>
          </div>
        </div>

        <a-button type="primary" block class="new-btn" @click="newConv">＋ 新建对话</a-button>
      </div>
    </div>

    <!-- 会话列表（可滚动）-->
    <div class="conv-list">
      <div
        v-for="c in convs"
        :key="c.id"
        :class="['conv-item', { active: activeId === c.id }]"
        @click="$emit('select', c.id)"
      >
        <div class="conv-title">{{ c.title }}</div>
        <div class="conv-date">{{ fmtDate(c.updated_at) }}</div>
        <a-popconfirm title="确定删除？" ok-text="删除" cancel-text="取消" @confirm.stop="delConv(c.id)">
          <span class="conv-del" @click.stop>✕</span>
        </a-popconfirm>
      </div>
      <div v-if="convs.length === 0" class="conv-empty">暂无对话，点击上方新建</div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import WeatherWidget from './WeatherWidget.vue'
import HotTopicCard  from './HotTopicCard.vue'
import { getConversations, createConversation, deleteConversation, updateConversation } from '../services/api'
import type { ConversationOut, PersonaType, PersonaOption } from '../types'

const props = defineProps<{ activeId: number | null }>()
const emit  = defineEmits<{ select: [id: number]; 'topic-click': [t: string] }>()

const PERSONAS: PersonaOption[] = [
  { name: 'gentle',   displayName: '温柔',   emoji: '🌸' },
  { name: 'rational', displayName: '理性',   emoji: '🧠' },
  { name: 'humorous', displayName: '幽默',   emoji: '😄' },
]

const convs   = ref<ConversationOut[]>([])
const persona = ref<PersonaType>('gentle')

const load = async () => {
  try {
    convs.value = await getConversations()
    if (!props.activeId && convs.value.length > 0) emit('select', convs.value[0].id)
  } catch (e) { console.error(e) }
}

const newConv = async () => {
  try {
    const c = await createConversation({
      title: `${dayjs().format('M月D日')} 的倾诉`,
      persona: persona.value,
    })
    convs.value.unshift(c)
    emit('select', c.id)
    message.success('新对话已创建')
  } catch { message.error('创建失败') }
}

const delConv = async (id: number) => {
  try {
    await deleteConversation(id)
    convs.value = convs.value.filter(c => c.id !== id)
    if (props.activeId === id) emit('select', convs.value[0]?.id ?? -1)
    message.success('已删除')
  } catch { message.error('删除失败') }
}

const switchPersona = async (name: PersonaType) => {
  persona.value = name
  if (props.activeId && props.activeId > 0) {
    try { await updateConversation(props.activeId, { persona: name }) } catch {}
  }
}

watch(() => props.activeId, id => {
  if (!id) return
  const c = convs.value.find(c => c.id === id)
  if (c) persona.value = c.persona as PersonaType
})

const fmtDate = (t: string) => {
  const d = dayjs(t)
  return d.isSame(dayjs(), 'day') ? d.format('HH:mm') : d.format('MM-DD')
}

onMounted(load)
defineExpose({ reload: load })
</script>

<style scoped>
.sidebar       { width: 256px; flex-shrink: 0; height: 100vh; background: white; border-right: 1px solid #eee; display: flex; flex-direction: column; overflow: hidden; }
.sidebar-fixed { flex-shrink: 0; }
.sb-header     { display: flex; justify-content: space-between; align-items: center; padding: 14px 14px 10px; border-bottom: 1px solid #f0f0f0; }
.sb-logo       { display: flex; align-items: center; gap: 6px; }
.sb-title      { font-size: 18px; font-weight: 700; background: linear-gradient(135deg,#667eea,#764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.sb-scroll-top { padding: 10px 14px 0; max-height: 60vh; overflow-y: auto; }
.section-label { font-size: 11px; color: #aaa; margin: 8px 0 5px; }
.persona-row   { display: flex; gap: 5px; margin-bottom: 10px; }
.persona-btn   { flex: 1; display: flex; flex-direction: column; align-items: center; padding: 6px 2px; border: 1.5px solid #eee; border-radius: 10px; cursor: pointer; transition: all 0.2s; }
.persona-btn.active { border-color: #667eea; background: #f0f0ff; }
.persona-btn:hover  { border-color: #b0b8ff; }
.persona-name  { font-size: 10px; color: #666; margin-top: 2px; }
.new-btn       { background: linear-gradient(135deg,#667eea,#764ba2); border: none; margin-bottom: 8px; }
.conv-list     { flex: 1; overflow-y: auto; padding: 4px 8px; }
.conv-item     { position: relative; padding: 9px 28px 9px 10px; border-radius: 8px; cursor: pointer; margin-bottom: 2px; transition: background 0.15s; }
.conv-item:hover  { background: #f5f5f5; }
.conv-item.active { background: #f0f0ff; }
.conv-title    { font-size: 13px; color: #333; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.conv-date     { font-size: 11px; color: #bbb; margin-top: 2px; }
.conv-del      { position: absolute; right: 8px; top: 50%; transform: translateY(-50%); font-size: 11px; color: #ddd; padding: 2px 3px; border-radius: 3px; }
.conv-del:hover { color: #ff4d4f; background: #fff0f0; }
.conv-empty    { text-align: center; font-size: 12px; color: #ccc; padding: 20px 0; }
</style>
