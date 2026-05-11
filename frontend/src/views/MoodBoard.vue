<template>
  <div :class="['bwrap', role]">
    <div class="avatar" :class="role">{{ role === 'assistant' ? '🌸' : '🙂' }}</div>
    <div class="bubble" :class="role">
      <div class="bcontent" v-html="html" />
      <div class="btime">{{ fmtTime }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import dayjs from 'dayjs'

const props = defineProps<{ role: 'user' | 'assistant'; content: string; created_at: string }>()

// 配置 marked：禁用自动跳转，避免 XSS
marked.setOptions({ breaks: true })

const html = computed(() => {
  if (props.role === 'user') {
    // 用户消息不解析 Markdown，直接转义换行即可
    return props.content.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>')
  }
  // Agent 回复解析 Markdown
  return marked.parse(props.content) as string
})

const fmtTime = computed(() => dayjs(props.created_at).format('HH:mm'))
</script>

<style scoped>
.bwrap { display: flex; align-items: flex-end; gap: 8px; margin-bottom: 14px; }
.bwrap.user { flex-direction: row-reverse; }
.avatar { width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; background: #f0f0f0; }
.bubble { max-width: 72%; }
.bcontent { padding: 10px 14px; font-size: 14px; line-height: 1.7; word-break: break-word; border-radius: 4px 16px 16px 16px; background: white; color: #333; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.bubble.user .bcontent { background: #667eea; color: white; border-radius: 16px 4px 16px 16px; }
.btime { font-size: 11px; color: #ccc; margin-top: 3px; }
.bwrap.user .btime { text-align: right; }

/* Markdown 内容样式 */
.bcontent :deep(h1),
.bcontent :deep(h2),
.bcontent :deep(h3) { font-size: 14px; font-weight: 600; margin: 10px 0 4px; color: #333; }
.bcontent :deep(h3) { font-size: 13px; }
.bcontent :deep(p)  { margin: 4px 0; }
.bcontent :deep(ul),
.bcontent :deep(ol) { padding-left: 18px; margin: 4px 0; }
.bcontent :deep(li) { margin-bottom: 3px; line-height: 1.6; }
.bcontent :deep(strong) { font-weight: 600; color: #222; }
.bcontent :deep(em) { font-style: italic; color: #555; }
.bcontent :deep(hr) { border: none; border-top: 1px solid #eee; margin: 8px 0; }
.bcontent :deep(blockquote) { border-left: 3px solid #667eea; padding-left: 10px; color: #888; margin: 6px 0; }
.bcontent :deep(code) { background: #f5f5f5; padding: 1px 5px; border-radius: 4px; font-size: 12px; font-family: monospace; }
</style>
