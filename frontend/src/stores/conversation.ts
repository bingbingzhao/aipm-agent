import { ref } from 'vue'
import { defineStore } from 'pinia'
import { apiClient } from '@/api/client'
import type { ChatMessage } from '@/types'

export const useConversationStore = defineStore('conversation', () => {
  const messages = ref<ChatMessage[]>([])
  const connected = ref(false)
  let ws: WebSocket | null = null

  function connect(projectId: string) {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${location.host}/ws/${projectId}`

    ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      connected.value = true
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'message') {
        messages.value.push({
          role: data.role,
          content: data.content,
          stage_complete: data.stage_complete,
          requirement_card: data.requirement_card,
        })
      }
    }

    ws.onclose = () => {
      connected.value = false
    }

    ws.onerror = () => {
      connected.value = false
    }
  }

  function send(message: string) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      messages.value.push({ role: 'user', content: message })
      ws.send(JSON.stringify({ message }))
    }
  }

  function disconnect() {
    ws?.close()
    ws = null
    messages.value = []
  }

  async function loadHistory(projectId: string) {
    try {
      const history = await apiClient.get(`/api/conversations/${projectId}`)
      messages.value = history.map((m: { role: string; content: string }) => ({
        role: m.role,
        content: m.content,
      }))
    } catch {
      // No history yet
    }
  }

  return { messages, connected, connect, send, disconnect, loadHistory }
})
