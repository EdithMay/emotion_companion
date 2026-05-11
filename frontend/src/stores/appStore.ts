import { reactive } from 'vue'

export const appStore = reactive({
  activeConversationId: null as number | null,
  setActive(id: number | null) { this.activeConversationId = id }
})
