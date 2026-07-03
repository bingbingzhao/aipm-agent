import { ref } from 'vue'
import { defineStore } from 'pinia'
import { apiClient } from '@/api/client'
import type { ChatMessage } from '@/types'

export const useConversationStore = defineStore('conversation', () => {
  const messages = ref<ChatMessage[]>([])
  const currentCard = ref<Record<string, any> | null>(null)
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
          stage_ready: data.stage_ready,
          requirement_card: data.requirement_card,
          stage_transition: data.stage_transition,
        } as any)
        // Sync requirement card in real-time
        if (data.requirement_card) {
          currentCard.value = data.requirement_card
        }
      } else if (data.type === 'progress') {
        // Background pipeline progress
        messages.value.push({
          role: 'assistant',
          content: data.content,
          type: 'progress',
        } as any)
      } else if (data.type === 'stage_transition') {
        // Pipeline result from background task
        messages.value.push({
          role: 'assistant',
          content: '产品方案已生成！查看右侧面板了解更多。',
          type: 'stage_transition',
          stage: data.stage,
          thinking_report: data.thinking_report,
          structure: data.structure,
        } as any)
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
    currentCard.value = null
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

  return { messages, currentCard, connected, connect, send, disconnect, loadHistory }
})
