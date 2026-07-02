<template>
  <div class="project-view">
    <StageIndicator :current-stage="pipelineStage" />

    <!-- Stage navigation bar -->
    <div v-if="pipelineStage !== 'idea'" class="stage-nav">
      <el-button text @click="handleRegress" :loading="regressing">
        <el-icon><ArrowLeft /></el-icon>
        返回上一阶段
      </el-button>
      <span class="stage-hint-text">当前：{{ STAGE_LABELS[pipelineStage] || pipelineStage }}</span>
    </div>

    <div class="project-content">
      <!-- Left: Chat Panel (Stage ①) -->
      <div v-if="showChat" class="chat-section">
        <ChatPanel
          :project-id="projectId"
          :project="project"
          @stage-transition="onStageTransition"
          @card-update="onCardUpdate"
        />
      </div>

      <!-- Right: Output Panel -->
      <div :class="showChat ? 'output-section' : 'output-section-full'">
        <!-- Stage ②: Product Thinking -->
        <div v-if="pipelineStage === 'thinking'" class="output-panel">
          <h3>📊 产品思路分析</h3>
          <div v-if="thinkingContent" class="thinking-content">
            <div v-for="(section, idx) in thinkingSections" :key="idx">
              <h4>{{ section.title }}</h4>
              <p>{{ section.body }}</p>
            </div>
          </div>
          <div v-else-if="thinkingLoading" class="loading-state">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>正在分析产品思路...</span>
          </div>
          <el-empty v-else description="完成需求卡片后自动生成" />

          <div v-if="thinkingContent" class="stage-actions">
            <el-button type="primary" :loading="advancing" @click="handleAdvance">
              <el-icon><Right /></el-icon>
              继续分析 → 产品结构
            </el-button>
          </div>
        </div>

        <!-- Stage ③: Product Structure -->
        <div v-else-if="pipelineStage === 'structure'" class="output-panel">
          <h3>🏗️ 产品架构</h3>
          <div v-if="structureData" class="structure-content">
            <!-- Modules -->
            <div v-if="structureData.information_architecture?.modules?.length" class="struct-section">
              <h4>功能模块</h4>
              <div v-for="mod in structureData.information_architecture.modules" :key="mod.name" class="struct-card">
                <div class="struct-card-header">
                  <span class="struct-name">{{ mod.name }}</span>
                  <el-tag size="small" :type="mod.priority === 'p0' ? 'danger' : mod.priority === 'p1' ? 'warning' : 'info'">
                    {{ mod.priority.toUpperCase() }}
                  </el-tag>
                </div>
                <p class="struct-desc">{{ mod.description }}</p>
                <div v-if="mod.pages?.length" class="struct-pages">
                  <el-tag v-for="p in mod.pages" :key="p" size="small" effect="plain">
                    {{ p }}
                  </el-tag>
                </div>
              </div>
            </div>

            <!-- Routes -->
            <div v-if="structureData.route_plan?.length" class="struct-section">
              <h4>页面路由</h4>
              <el-table :data="structureData.route_plan" size="small" stripe>
                <el-table-column prop="route" label="路由" width="140" />
                <el-table-column prop="title" label="页面" width="120" />
                <el-table-column prop="description" label="说明" />
              </el-table>
            </div>

            <!-- Features -->
            <div v-if="structureData.feature_tree?.length" class="struct-section">
              <h4>功能树</h4>
              <el-tree :data="featureTreeData" :props="{ children: 'children', label: 'label' }" />
            </div>

            <!-- Data entities -->
            <div v-if="structureData.data_entities?.length" class="struct-section">
              <h4>数据模型</h4>
              <div v-for="entity in structureData.data_entities" :key="entity.name" class="struct-card">
                <div class="struct-card-header">
                  <span class="struct-name">{{ entity.name }}</span>
                </div>
                <div class="entity-fields">
                  <span v-for="f in entity.fields" :key="f.name" class="field-item">
                    {{ f.name }}<em>: {{ f.type }}</em>
                  </span>
                </div>
              </div>
            </div>
          </div>
          <div v-else-if="thinkingLoading" class="loading-state">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>正在生成产品架构...</span>
          </div>
          <el-empty v-else description="等待产品思路完成后自动生成" />

          <div v-if="structureData" class="stage-actions">
            <el-button type="primary" :loading="protoLoading" @click="generatePrototype">
              <el-icon><MagicStick /></el-icon>
              生成产品原型
            </el-button>
          </div>
        </div>

        <!-- Stage ④: Prototype -->
        <div v-else-if="pipelineStage === 'prototype'" class="output-panel">
          <div class="proto-header">
            <h3>🎨 产品原型</h3>
            <el-tag v-if="validationScore !== null" :type="scoreTagType">
              质量评分: {{ validationScore }}/100
            </el-tag>
          </div>

          <div v-if="prototypeHtml" class="prototype-preview">
            <iframe :srcdoc="prototypeHtml" sandbox="allow-scripts" />
          </div>
          <div v-else-if="protoLoading" class="loading-state">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>正在生成原型页面...</span>
          </div>
          <el-empty v-else description="点击按钮生成原型" />

          <div v-if="prototypeHtml" class="stage-actions">
            <el-button @click="iteratePrototype">
              <el-icon><RefreshRight /></el-icon>
              反馈修改
            </el-button>
            <el-button @click="downloadPrototype">
              <el-icon><Download /></el-icon>
              下载 HTML
            </el-button>
            <el-button type="primary" :loading="prdLoading" @click="generatePRD">
              <el-icon><Document /></el-icon>
              生成 PRD
            </el-button>
          </div>
        </div>

        <!-- Stage ⑤: PRD -->
        <div v-else-if="pipelineStage === 'prd'" class="output-panel">
          <h3>📄 产品需求文档</h3>
          <div v-if="prdContent" class="prd-content">
            <div v-html="renderedPRD" />
          </div>
          <div v-else-if="prdLoading" class="loading-state">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>正在生成 PRD...</span>
          </div>
          <el-empty v-else description="完成原型后自动生成" />

          <div v-if="prdContent" class="stage-actions">
            <el-button @click="downloadPRD">
              <el-icon><Download /></el-icon>
              下载 PRD
            </el-button>
            <el-button type="primary" :loading="deliveryLoading" @click="generateDelivery">
              <el-icon><List /></el-icon>
              生成开发任务
            </el-button>
          </div>
        </div>

        <!-- Stage ⑥: Delivery -->
        <div v-else-if="pipelineStage === 'delivery'" class="output-panel">
          <h3>🚀 开发交付计划</h3>
          <div v-if="deliveryData" class="delivery-content">
            <!-- Epics -->
            <div v-if="deliveryData.epics?.length" class="struct-section">
              <h4>Epic 分解</h4>
              <el-collapse>
                <el-collapse-item
                  v-for="epic in deliveryData.epics"
                  :key="epic.id"
                  :title="`${epic.name} (${epic.stories?.length || 0} stories)`"
                >
                  <div v-for="story in epic.stories" :key="story.id" class="story-card">
                    <div class="story-header">
                      <span class="story-name">{{ story.name }}</span>
                      <el-tag size="small">{{ story.story_points }} pts</el-tag>
                    </div>
                    <p class="story-desc">
                      <em>As a {{ story.as_a }}, I want {{ story.i_want }}, so that {{ story.so_that }}.</em>
                    </p>
                    <div v-if="story.tasks?.length" class="task-list">
                      <div v-for="t in story.tasks" :key="t.name" class="task-item">
                        <el-tag size="small" :type="t.role === 'frontend' ? '' : 'info'">{{ t.role }}</el-tag>
                        <span>{{ t.name }}</span>
                        <span class="task-hours">{{ t.estimate_hours }}h</span>
                      </div>
                    </div>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>

            <!-- Sprints -->
            <div v-if="deliveryData.sprints?.length" class="struct-section">
              <h4>Sprint 规划</h4>
              <div v-for="sprint in deliveryData.sprints" :key="sprint.name" class="sprint-card">
                <div class="sprint-header">
                  <strong>{{ sprint.name }}</strong>
                  <span>{{ sprint.duration_weeks }}周 · {{ sprint.total_points }} pts</span>
                </div>
                <p class="sprint-goal">{{ sprint.goal }}</p>
              </div>
            </div>

            <!-- Summary -->
            <div v-if="deliveryData.total_estimate" class="struct-section">
              <h4>总览</h4>
              <el-descriptions :column="2" border size="small">
                <el-descriptions-item label="总周期">{{ deliveryData.total_estimate.weeks }} 周</el-descriptions-item>
                <el-descriptions-item label="团队规模">{{ deliveryData.total_estimate.team_size }} 人</el-descriptions-item>
                <el-descriptions-item label="总 Story Points">{{ deliveryData.total_estimate.total_story_points }}</el-descriptions-item>
              </el-descriptions>
            </div>
          </div>
          <div v-else-if="deliveryLoading" class="loading-state">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>正在生成开发计划...</span>
          </div>
          <el-empty v-else description="完成 PRD 后自动生成" />
        </div>

        <!-- Stage ①: Idea -->
        <div v-else class="output-panel">
          <h3>💡 需求卡片</h3>
          <div v-if="currentRequirementCard" class="requirement-card">
            <div
              v-for="(card, key) in currentRequirementCard"
              :key="key"
              :class="['card-slot', card.state]"
            >
              <div class="card-slot-header">
                <span class="card-slot-label">{{ card.label }}</span>
                <el-tag
                  :type="card.state === 'saturated' ? 'success' : card.state === 'partial' ? 'warning' : 'info'"
                  size="small"
                >
                  {{ card.state === 'saturated' ? '✓' : card.state === 'partial' ? '…' : '○' }}
                </el-tag>
              </div>
              <div v-if="card.value" class="card-slot-value">{{ card.value }}</div>
              <div v-else class="card-slot-empty">等待补充...</div>
            </div>
          </div>
          <div v-else class="stage-hint">
            <p>在左侧对话中描述你的产品想法。</p>
            <p>AI 会引导你完成需求梳理，确认后生成产品思路分析。</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Feedback Dialog -->
    <el-dialog v-model="showFeedback" title="原型修改反馈" width="500px">
      <el-input
        v-model="feedbackText"
        type="textarea"
        :rows="3"
        placeholder="描述你希望修改的地方..."
      />
      <template #footer>
        <el-button @click="showFeedback = false">取消</el-button>
        <el-button type="primary" :loading="protoLoading" @click="doIterate">
          提交修改
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useProjectStore } from '@/stores/project'
import ChatPanel from '@/components/ChatPanel.vue'
import StageIndicator from '@/components/StageIndicator.vue'
import { apiClient } from '@/api/client'
import type { Project } from '@/types'

const props = defineProps<{ id: string }>()
const projectId = props.id

const store = useProjectStore()
const project = ref<Project | null>(null)
const regressing = ref(false)
const advancing = ref(false)
const STAGE_LABELS_MAP: Record<string, string> = {
  idea: '想法捕获', thinking: '产品思路', structure: '产品结构',
  prototype: '原型', prd: 'PRD', delivery: '交付',
}

// Pipeline state
const pipelineStage = ref('idea')
const thinkingContent = ref('')
const structureData = ref<any>(null)
const prototypeHtml = ref('')
const validationScore = ref<number | null>(null)
const thinkingLoading = ref(false)
const protoLoading = ref(false)
const prdLoading = ref(false)
const deliveryLoading = ref(false)
const prdContent = ref('')
const deliveryData = ref<any>(null)
const currentRequirementCard = ref<Record<string, any> | null>(null)
const showFeedback = ref(false)
const feedbackText = ref('')

const showChat = computed(() => pipelineStage.value === 'idea')

const featureTreeData = computed(() => {
  if (!structureData.value?.feature_tree) return []
  return structureData.value.feature_tree.map((f: any) => ({
    label: `${f.name} [${f.priority?.toUpperCase()}]`,
    children: (f.children || []).map((c: any) => ({
      label: c.name,
    })),
  }))
})

onMounted(async () => {
  project.value = await store.getProject(projectId)

  // Fetch pipeline state (restore from previous session)
  try {
    const state = await apiClient.get(`/api/pipeline/state/${projectId}`)
    pipelineStage.value = state.stage
    if (state.requirement_card) {
      currentRequirementCard.value = state.requirement_card
    }
    if (state.thinking_report) {
      thinkingContent.value = state.thinking_report
    }
    if (state.structure) {
      structureData.value = state.structure
    }
    if (state.prototype_html) {
      prototypeHtml.value = state.prototype_html
    }
    if (state.validation) {
      validationScore.value = state.validation.score
    }
    if (state.prd_document) {
      prdContent.value = state.prd_document
    }
    if (state.delivery) {
      deliveryData.value = state.delivery
      pipelineStage.value = 'delivery'
    }
  } catch {
    // Project just created, no state yet
  }
})

const STAGE_LABELS = STAGE_LABELS_MAP

async function handleRegress() {
  regressing.value = true
  try {
    const result = await apiClient.post(`/api/projects/${projectId}/regress`, {})
    pipelineStage.value = result.stage
    project.value = result
    // Clear local state for stages we've regressed past
    // Only clear stage outputs, NOT requirement_card or conversations
    if (result.stage === 'thinking') {
      structureData.value = null
      prototypeHtml.value = ''
      prdContent.value = ''
      deliveryData.value = null
    } else if (result.stage === 'structure') {
      prototypeHtml.value = ''
      prdContent.value = ''
      deliveryData.value = null
    }
    // idea: keep everything (requirement_card, conversations stay)
    ElMessage.success(`已回退到「${STAGE_LABELS[result.stage]}」`)
  } catch (e: any) {
    ElMessage.error(e.message || '回退失败')
  } finally {
    regressing.value = false
  }
}

async function handleAdvance() {
  advancing.value = true
  thinkingLoading.value = true
  try {
    const result = await apiClient.post(`/api/pipeline/advance/${projectId}`, {})
    pipelineStage.value = 'structure'
    structureData.value = result.structure
    if (result.thinking_report) {
      thinkingContent.value = result.thinking_report
    }
    if (project.value) project.value.stage = 'structure'
    thinkingLoading.value = false
    ElMessage.success('产品结构分析完成！')
  } catch (e: any) {
    ElMessage.error(e.message || '分析失败')
    thinkingLoading.value = false
  } finally {
    advancing.value = false
  }
}

const thinkingSections = computed(() => {
  if (!thinkingContent.value) return []
  // Parse markdown-like sections
  const sections: { title: string; body: string }[] = []
  const lines = thinkingContent.value.split('\n')
  let currentTitle = ''
  let currentBody: string[] = []

  for (const line of lines) {
    if (line.startsWith('##')) {
      if (currentTitle) {
        sections.push({ title: currentTitle, body: currentBody.join('\n') })
      }
      currentTitle = line.replace(/^##\s*/, '')
      currentBody = []
    } else if (currentTitle) {
      currentBody.push(line)
    }
  }
  if (currentTitle) {
    sections.push({ title: currentTitle, body: currentBody.join('\n') })
  }
  return sections
})

const scoreTagType = computed(() => {
  if (validationScore.value === null) return 'info'
  if (validationScore.value >= 80) return 'success'
  if (validationScore.value >= 60) return 'warning'
  return 'danger'
})

const renderedPRD = computed(() => {
  if (!prdContent.value) return ''
  // Simple markdown → HTML
  return prdContent.value
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^#### (.+)$/gm, '<h4>$1</h4>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n- (.+)/g, '\n<li>$1</li>')
    .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
    .replace(/\n\n/g, '<br><br>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
})

function onStageTransition(data: { stage: string; thinkingReport?: string; structure?: any }) {
  pipelineStage.value = data.stage
  thinkingLoading.value = false

  if (data.thinkingReport) {
    thinkingContent.value = data.thinkingReport
  }
  if (data.structure) {
    structureData.value = data.structure
  }
  project.value && (project.value.stage = data.stage)
}

function onCardUpdate(data: Record<string, any>) {
  currentRequirementCard.value = data
}

async function generatePrototype() {
  protoLoading.value = true
  try {
    const result = await apiClient.post(`/api/pipeline/advance/${projectId}`, {})
    pipelineStage.value = 'prototype'
    prototypeHtml.value = result.prototype_html
    validationScore.value = result.validation?.score ?? null
    project.value && (project.value.stage = 'prototype')
    ElMessage.success('原型生成完成！')
  } catch (e: any) {
    ElMessage.error(e.message || '原型生成失败')
  } finally {
    protoLoading.value = false
  }
}

function iteratePrototype() {
  feedbackText.value = ''
  showFeedback.value = true
}

async function doIterate() {
  if (!feedbackText.value.trim()) return
  protoLoading.value = true
  showFeedback.value = false
  try {
    const result = await apiClient.post(`/api/pipeline/iterate/${projectId}`, {
      feedback: feedbackText.value,
    })
    prototypeHtml.value = result.prototype_html
    validationScore.value = result.validation?.score ?? null
    ElMessage.success('原型已更新！')
  } catch (e: any) {
    ElMessage.error(e.message || '原型修改失败')
  } finally {
    protoLoading.value = false
  }
}

function downloadPrototype() {
  const blob = new Blob([prototypeHtml.value], { type: 'text/html' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${project.value?.title || 'prototype'}.html`
  a.click()
  URL.revokeObjectURL(url)
}

async function generatePRD() {
  prdLoading.value = true
  try {
    const result = await apiClient.post(`/api/pipeline/advance/${projectId}`, {})
    pipelineStage.value = 'prd'
    prdContent.value = result.prd_document
    project.value && (project.value.stage = 'prd')
    ElMessage.success('PRD 生成完成！')
  } catch (e: any) {
    ElMessage.error(e.message || 'PRD 生成失败')
  } finally {
    prdLoading.value = false
  }
}

function downloadPRD() {
  const blob = new Blob([prdContent.value], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${project.value?.title || 'prd'}_PRD.md`
  a.click()
  URL.revokeObjectURL(url)
}

async function generateDelivery() {
  deliveryLoading.value = true
  try {
    const result = await apiClient.post(`/api/pipeline/advance/${projectId}`, {})
    pipelineStage.value = 'delivery'
    deliveryData.value = result.delivery
    project.value && (project.value.stage = 'delivery')
    ElMessage.success('开发计划生成完成！')
  } catch (e: any) {
    ElMessage.error(e.message || '开发计划生成失败')
  } finally {
    deliveryLoading.value = false
  }
}
</script>

<style scoped>
.project-view {
  max-width: 1400px;
  margin: 0 auto;
}

.project-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-top: 24px;
  align-items: start;
}

@media (max-width: 900px) {
  .project-content {
    grid-template-columns: 1fr;
  }
}

.output-section {
  position: sticky;
  top: 24px;
}

.output-section-full {
  grid-column: 1 / -1;
  max-width: 900px;
  margin: 0 auto;
}

.output-panel {
  background: white;
  border-radius: 12px;
  padding: 24px;
  min-height: 400px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

.output-panel h3 {
  margin: 0 0 16px;
  font-size: 16px;
}

.proto-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.thinking-content {
  font-size: 14px;
  line-height: 1.8;
  max-height: 60vh;
  overflow-y: auto;
}

.thinking-content h4 {
  color: #2563eb;
  margin: 16px 0 8px;
  font-size: 15px;
}

.thinking-content p {
  white-space: pre-wrap;
  color: #4b5563;
  margin: 0;
}

.loading-state {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
  padding: 48px;
  color: #909399;
}

.stage-actions {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #f0f2f5;
  display: flex;
  gap: 12px;
}

.stage-hint {
  padding: 24px;
  text-align: center;
  color: #909399;
  line-height: 1.8;
}

.requirement-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.card-slot {
  background: #f8fafc;
  border-radius: 8px;
  padding: 10px 14px;
  border-left: 3px solid #e4e7ed;
  transition: border-color 0.3s;
}

.card-slot.saturated {
  border-left-color: #16a34a;
  background: #f0fdf4;
}

.card-slot.partial {
  border-left-color: #f59e0b;
  background: #fffbeb;
}

.card-slot-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-slot-label {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.card-slot-value {
  margin-top: 4px;
  font-size: 13px;
  color: #6b7280;
  line-height: 1.5;
}

.card-slot-empty {
  margin-top: 4px;
  font-size: 12px;
  color: #c0c4cc;
  font-style: italic;
}

.structure-content {
  max-height: 60vh;
  overflow-y: auto;
}

.struct-section {
  margin-bottom: 20px;
}

.struct-section h4 {
  color: #2563eb;
  font-size: 14px;
  margin: 0 0 10px;
}

.struct-card {
  background: #f8fafc;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 8px;
}

.struct-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.struct-name {
  font-weight: 600;
  font-size: 14px;
}

.struct-desc {
  color: #6b7280;
  font-size: 13px;
  margin: 6px 0;
}

.struct-pages {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.entity-fields {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 6px;
}

.field-item {
  font-size: 12px;
  background: #eff6ff;
  padding: 2px 8px;
  border-radius: 4px;
  color: #1e40af;
}

.field-item em {
  font-style: normal;
  color: #6b7280;
}

.prd-content {
  max-height: 65vh;
  overflow-y: auto;
  font-size: 14px;
  line-height: 1.8;
}

.prd-content h2 {
  color: #1e40af;
  font-size: 18px;
  margin: 20px 0 12px;
  padding-bottom: 6px;
  border-bottom: 1px solid #e4e7ed;
}

.prd-content h3 {
  color: #2563eb;
  font-size: 15px;
  margin: 16px 0 8px;
}

.prd-content strong {
  color: #1e3a8a;
}

.prd-content code {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}

.prd-content li {
  margin: 4px 0;
}

.delivery-content {
  max-height: 65vh;
  overflow-y: auto;
}

.story-card {
  background: #f8fafc;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 8px;
}

.story-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.story-name {
  font-weight: 600;
  font-size: 14px;
}

.story-desc {
  color: #6b7280;
  font-size: 13px;
  margin: 6px 0;
  line-height: 1.6;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 8px;
}

.task-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  padding: 4px 0;
}

.task-hours {
  margin-left: auto;
  color: #909399;
  font-size: 12px;
}

.sprint-card {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 8px;
}

.sprint-header {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
}

.sprint-goal {
  color: #6b7280;
  font-size: 13px;
  margin: 4px 0 0;
}
</style>
