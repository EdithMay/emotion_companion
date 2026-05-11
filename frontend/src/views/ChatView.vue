<template>
  <div class="chat-view">

    <div v-if="!activeId || activeId < 0" class="empty-state">
      <div class="empty-icon">💬</div>
      <p>从左侧选择或新建一个对话</p>
    </div>

    <template v-else>
      <!-- 顶部栏：只显示标题 -->
      <div class="chat-header">
        <div class="chat-conv-title">{{ convTitle }}</div>
      </div>

      <!-- 消息列表 -->
      <div ref="msgBox" class="msg-area">
        <MessageBubble
          v-for="m in msgs"
          :key="m.id"
          :role="m.role"
          :content="m.content"
          :created_at="m.created_at"
        />

        <div v-if="typing && isWaitingForToken" class="bwrap assistant" style="margin-bottom:14px">
          <div style="width:34px;height:34px;border-radius:50%;background:#f0f0f0;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0">🌸</div>
          <div v-if="toolUsing" class="tool-hint">🔍 正在翻阅记忆中...</div>
          <div v-else class="typing-dots"><span/><span/><span/></div>
        </div>

      </div>


      <!-- 输入区 -->
      <div class="input-bar">
        <a-textarea
          v-model:value="input"
          placeholder="说点什么吧… (Enter 发送，Shift+Enter 换行)"
          :auto-size="{ minRows: 1, maxRows: 5 }"
          :disabled="typing"
          class="input-box"
          @keydown.enter.exact.prevent="send"
        />
        <a-button
          type="primary"
          class="send-btn"
          :loading="typing"
          :disabled="!input.trim()"
          @click="send"
        >发送</a-button>
      </div>
    </template>

  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { message } from 'ant-design-vue'
import { appStore }         from '../stores/appStore'
import { getMessages, getConversations, sendMessageStream  } from '../services/api'
import MessageBubble        from '../components/MessageBubble.vue'
import type { MessageOut }  from '../types'

const props = defineProps<{ pendingTopic: string }>()
const emit  = defineEmits<{ 'topic-consumed': [] }>()

const activeId  = computed(() => appStore.activeConversationId)
const msgs      = ref<MessageOut[]>([])
const input     = ref('')
const typing    = ref(false)
const convTitle = ref('')
const msgBox    = ref<HTMLDivElement>()
const toolUsing = ref(false)   // Agent 正在检索记忆
// 👈 新增的状态变量
       // 是否正在查记忆
const isWaitingForToken = ref(false) // 是否正在等待第一个字吐出来


watch(activeId, async (id) => {
  if (!id || id < 0) { msgs.value = []; return }
  try {
    msgs.value = await getMessages(id)
    const all  = await getConversations()
    convTitle.value = all.find(c => c.id === id)?.title ?? '对话'
    scrollBottom()
  } catch {}
}, { immediate: true })

watch(() => props.pendingTopic, t => {
  if (t) { input.value = t; emit('topic-consumed') }
})

const scrollBottom = () => nextTick(() => {
  if (msgBox.value) msgBox.value.scrollTop = msgBox.value.scrollHeight
})

const send = async () => {
  const text = input.value.trim()
  if (!text || !activeId.value || activeId.value < 0) return

  input.value  = ''
  typing.value = true

  // 乐观渲染用户消息（临时 ID）
  const tmpUserId = Date.now()
  const tmpUser: MessageOut = {
    id: tmpUserId,
    conversation_id: activeId.value,
    role: 'user',
    content: text,
    created_at: new Date().toISOString()
  }
  msgs.value.push(tmpUser)
  scrollBottom()

  // 预先插入一条空的 Agent 消息，流式填充内容
  const tmpAgentId = tmpUserId + 1
  const tmpAgent: MessageOut = {
    id: tmpAgentId,
    conversation_id: activeId.value,
    role: 'assistant',
    content: '',
    created_at: new Date().toISOString()
  }
  msgs.value.push(tmpAgent)
  scrollBottom()

  try {
    await sendMessageStream(
      { conversation_id: activeId.value, content: text },

      // onToken：每个 token 追加到 Agent 消息内容
      (token) => {
        const idx = msgs.value.findIndex(m => m.id === tmpAgentId)
        if (idx > -1) {
          msgs.value[idx] = { ...msgs.value[idx], content: msgs.value[idx].content + token }
          scrollBottom()
        } else {
          const idx = msgs.value.findIndex(m => m.id === tmpAgentId)
          if (idx > -1) {
            msgs.value[idx] = {...msgs.value[idx], content: msgs.value[idx].content + token}
          }
        }
      },

      // onDone：用服务端真实 ID 替换临时 ID
      (meta) => {
        const idx = msgs.value.findIndex(m => m.id === tmpAgentId)
        if (idx > -1) {
          msgs.value[idx] = { ...msgs.value[idx], id: meta.id, created_at: meta.created_at }
        }
        typing.value = false
      },

      // onUserMsg：更新用户消息的真实 ID
      (meta) => {
        const idx = msgs.value.findIndex(m => m.id === tmpUserId)
        if (idx > -1) {
          msgs.value[idx] = { ...msgs.value[idx], id: meta.id, created_at: meta.created_at }
        }
      },

      // onError
      (errMsg) => {
        message.error(`发送失败: ${errMsg}`)
        msgs.value = msgs.value.filter(m => m.id !== tmpAgentId && m.id !== tmpUserId)
        typing.value = false
      },
      // 5. 👈 onToolUsing：后端正在查记忆时触发
      () => {
        toolUsing.value = true
        scrollBottom()
      }

    )
  } catch (e) {
    message.error('网络错误，请重试')
    msgs.value = msgs.value.filter(m => m.id !== tmpAgentId && m.id !== tmpUserId)
    typing.value = false
    toolUsing.value = false
    isWaitingForToken.value = false
  }
}

</script>

<style scoped>
.chat-view    { display: flex; flex-direction: column; height: 100vh; background: #f5f5f5; }
.empty-state  { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #ccc; gap: 12px; }
.empty-icon   { font-size: 60px; }
.chat-header  { padding: 14px 20px; background: white; border-bottom: 1px solid #eee; flex-shrink: 0; }
.chat-conv-title { font-size: 15px; font-weight: 600; color: #333; }
.msg-area     { flex: 1; overflow-y: auto; padding: 20px 20px 10px; }
.input-bar    { display: flex; gap: 10px; padding: 12px 20px; background: white; border-top: 1px solid #eee; flex-shrink: 0; }
.input-box    { flex: 1; }
.send-btn     { background: linear-gradient(135deg,#667eea,#764ba2); border: none; height: auto; padding: 6px 18px; }
.bwrap        { display: flex; align-items: flex-end; gap: 8px; }
.typing-dots  { background: white; border-radius: 4px 16px 16px 16px; padding: 12px 16px; display: flex; gap: 5px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.typing-dots span { width: 7px; height: 7px; background: #ccc; border-radius: 50%; animation: bounce 1s infinite; }
.typing-dots span:nth-child(2) { animation-delay: 0.15s; }
.typing-dots span:nth-child(3) { animation-delay: 0.3s; }
@keyframes bounce { 0%,80%,100%{transform:translateY(0)} 40%{transform:translateY(-8px)} }
</style>
