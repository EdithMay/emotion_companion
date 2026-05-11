import { createRouter, createWebHistory } from 'vue-router'
import ChatView  from '../views/ChatView.vue'
import MoodBoard from '../views/MoodBoard.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/',     component: ChatView  },
    { path: '/mood', component: MoodBoard },
  ]
})
