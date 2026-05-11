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
import dayjs from 'dayjs'

const props = defineProps<{ role: 'user' | 'assistant'; content: string; created_at: string }>()

const html    = computed(() => props.content.replace(/\n/g, '<br>'))
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
</style>
