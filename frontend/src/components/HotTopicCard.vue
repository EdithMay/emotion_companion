<template>
  <div class="ht-wrap">
    <div class="ht-header">
      <span class="ht-title">🔥 今日热点</span>
      <a-select v-model:value="cat" size="small" style="width:68px" @change="load">
        <a-select-option v-for="c in cats" :key="c" :value="c">{{ c }}</a-select-option>
      </a-select>
    </div>
    <a-spin v-if="loading" size="small" style="display:block;text-align:center;padding:8px" />
    <div v-else>
      <div
        v-for="(item, i) in list"
        :key="i"
        class="ht-item"
        @click="$emit('click', item.title)"
      >
        <span :class="['ht-num', i < 3 ? 'hot' : '']">{{ i + 1 }}</span>
        <div class="ht-body">
          <div class="ht-text">{{ item.title }}</div>
          <div class="ht-src">{{ item.source }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getNews } from '../services/api'
import type { NewsItem } from '../types'

defineEmits<{ click: [title: string] }>()

const cats    = ['社会','娱乐','科技','生活']
const cat     = ref('社会')
const list    = ref<NewsItem[]>([])
const loading = ref(false)

const load = async () => {
  loading.value = true
  try {
    const r = await getNews(cat.value, 5)
    if (r.success) list.value = r.data
  } catch {}
  loading.value = false
}

onMounted(load)
</script>

<style scoped>
.ht-wrap   { margin-bottom: 8px; }
.ht-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.ht-title  { font-size: 12px; font-weight: 600; color: #333; }
.ht-item   { display: flex; gap: 6px; padding: 5px 4px; cursor: pointer; border-radius: 6px; transition: background 0.15s; }
.ht-item:hover { background: #f5f5f5; }
.ht-num    { font-size: 11px; font-weight: 700; color: #ccc; min-width: 14px; padding-top: 2px; }
.ht-num.hot { color: #ff6b6b; }
.ht-body   { flex: 1; min-width: 0; }
.ht-text   { font-size: 12px; color: #333; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.ht-src    { font-size: 10px; color: #bbb; margin-top: 1px; }
</style>
