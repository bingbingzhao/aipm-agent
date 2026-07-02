<template>
  <div class="chat-panel">
    <div class="chat-header">
      <h3>追问引擎</h3>
      <el-tag v-if="conversationStore.connected" type="success" size="small">在线</el-tag>
      <el-tag v-else type="info" size="small">未连接</el-tag>
    </div>

    <div class="chat-messages" ref="messagesContainer">
      <!-- Stage ready confirmation bar -->
      <div v-if="stageReady" class="stage-ready-bar">
        <span>✅ 需求信息已充足</span>
        <el-button type="primary" size="small" :loading="confirming" @click="handleConfirm">
          完成需求梳理，生成产品方案
        </el-button>
      </div>

      <div v-if="conversationStore.messages.length === 0 && !stageReady" class="empty-chat">
        <p>描述你的产品想法，AI 会引导你完善需求。</p>
      </div>

      <div
        v-for="(msg, idx) in conversationStore.messages"
        :key="idx"
        :class="['message', msg.role]"
      >
        <div class="message-avatar">
          {{ msg.role === 'user' ? '👤' : '🤖' }}
        </div>
        <div class="message-content">
          <div class="message-text">{{ msg.content }}</div>
          <div v-if="msg.type === 'progress'" class="progress-notice">
            <el-icon class="is-loading"><Loading /></el-icon>
            {{ msg.content }}
          </div>
        </div>
      </div>

      <div v-if="typing" class="message assistant">
        <div class="message-avatar">🤖</div>
        <div class="message-content">
          <div class="typing-indicator">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>
    </div>

    <div class="chat-input">
      <el-input
        v-model="inputText"
        placeholder="输入你的想法..."
        :disabled="!conversationStore.connected"
        @keyup.enter="handleSend"
      >
        <template #append>
          <el-button
            :disabled="!inputText.trim() || !conversationStore.connected"
            @click="handleSend"
          >
            <el-icon><Promotion /></el-icon>
          </el-button>
        </template>
      </el-input>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useConversationStore } from '@/stores/conversation'
import { apiClient } from '@/api/client'
import type { Project } from '@/types'

const props = defineProps<{
  projectId: string
  project: Project | null
}>()

const emit = defineEmits<{
  'stage-transition': [data: { stage: string; thinkingReport?: string; structure?: any }]
  'card-update': [data: Record<string, any>]
}>()

const conversationStore = useConversationStore()
const inputText = ref('')
const typing = ref(false)
const stageReady = ref(false)
const confirming = ref(false)
const messagesContainer = ref<HTMLElement>()

onMounted(async () => {
  await conversationStore.loadHistory(props.projectId)
  conversationStore.connect(props.projectId)
  scrollToBottom()
})

onUnmounted(() => {
  conversationStore.disconnect()
})

// Watch for stage transition messages
watch(
  () => conversationStore.messages,
  async (msgs) => {
    await nextTick()
    scrollToBottom()

    const lastMsg = msgs[msgs.length - 1]
    if (!lastMsg) return

    // Real-time requirement card sync
    if (lastMsg.requirement_card) {
      emit('card-update', lastMsg.requirement_card)
    }

    // Handle stage_ready: show confirm button instead of auto-transition
    if (lastMsg.stage_ready && lastMsg.requirement_card) {
      stageReady.value = true
      return
    }

    // Handle stage_transition (from manual advance API)
    if (lastMsg.type === 'stage_transition' && lastMsg.stage && lastMsg.thinking_report) {
      stageReady.value = false
      emit('stage-transition', {
        stage: lastMsg.stage,
        thinkingReport: lastMsg.thinking_report,
        structure: lastMsg.structure,
      })
      return
    }

    // Legacy: direct stage_transition in message
    if (lastMsg.stage_transition?.to && props.project?.stage === 'idea') {
      stageReady.value = false
      emit('stage-transition', {
        stage: lastMsg.stage_transition.to,
        thinkingReport: lastMsg.thinking_report,
      })
      return
    }

    if (lastMsg.stage_complete && !lastMsg.stage_transition?.pending) {
      stageReady.value = true
    }
  },
  { deep: true }
)

function handleSend() {
  const text = inputText.value.trim()
  if (!text || !conversationStore.connected) return

  conversationStore.send(text)
  inputText.value = ''
  typing.value = true
  setTimeout(() => { typing.value = false }, 2000)
}

async function handleConfirm() {
  confirming.value = true
  try {
    // Use pipeline advance to trigger thinking stage
    const result = await apiClient.post(`/api/pipeline/advance/${props.projectId}`, {})
    stageReady.value = false
    emit('stage-transition', {
      stage: result.new_stage || 'thinking',
      thinkingReport: result.thinking_report,
      structure: result.structure,
    })
  } catch (e: any) {
    confirming.value = false
    // Could show error but keep the button visible for retry
  }
}

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}
</script>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 180px);
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  overflow: hidden;
}

.chat-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 20px;
  border-bottom: 1px solid #f0f2f5;
}

.chat-header h3 {
  margin: 0;
  font-size: 16px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}

.empty-chat {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #c0c4cc;
  text-align: center;
  padding: 24px;
}

.stage-ready-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  margin-bottom: 12px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  font-size: 13px;
  color: #16a34a;
}

.message {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
  background: #f0f2f5;
}

.message-content {
  max-width: 75%;
}

.message-text {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.message.user .message-text {
  background: #2563eb;
  color: white;
  border-bottom-right-radius: 4px;
}

.message.assistant .message-text {
  background: #f0f2f5;
  color: #303133;
  border-bottom-left-radius: 4px;
}

.stage-complete-notice {
  margin-top: 6px;
  font-size: 12px;
  color: #16a34a;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 10px 14px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #c0c4cc;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-4px); }
}

.chat-input {
  padding: 12px 20px;
  border-top: 1px solid #f0f2f5;
}
</style>
