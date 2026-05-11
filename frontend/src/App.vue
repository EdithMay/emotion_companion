<template>
  <div class="layout">
    <ConversationSidebar
      :active-id="appStore.activeConversationId"
      @select="(id) => appStore.setActive(id)"
      @topic-click="handleTopic"
    />
    <main class="main-area">
      <router-view :pending-topic="pendingTopic" @topic-consumed="pendingTopic = ''" />
    </main>
    <MoodPanel />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ConversationSidebar from './components/ConversationSidebar.vue'
import MoodPanel           from './components/MoodPanel.vue'
import { appStore }        from './stores/appStore'

const pendingTopic = ref('')
const handleTopic  = (title: string) => {
  pendingTopic.value = `我想聊聊关于「${title}」这个话题`
}
</script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif; background: #f5f5f5; }
.layout    { display: flex; height: 100vh; overflow: hidden; min-width: 860px; }
.main-area { flex: 1; overflow: hidden; min-width: 0; }
</style>
