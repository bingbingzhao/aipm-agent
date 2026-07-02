<template>
  <div class="stage-bar">
    <div
      v-for="(stage, idx) in stages"
      :key="stage.key"
      class="stage-step-wrapper"
    >
      <div :class="stageClass(stage.key)">
        <el-icon v-if="stageCompleted(stage.key)"><Check /></el-icon>
        <span v-else class="stage-number">{{ idx + 1 }}</span>
        <span class="stage-label">{{ stage.label }}</span>
      </div>
      <div
        v-if="idx < stages.length - 1"
        :class="['stage-line', { completed: stageCompleted(stage.key) }]"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { STAGE_LABELS } from '@/types'

const props = defineProps<{
  currentStage: string
}>()

const stages = [
  { key: 'idea', label: '① 想法捕获' },
  { key: 'thinking', label: '② 产品思路' },
  { key: 'structure', label: '③ 产品结构' },
  { key: 'prototype', label: '④ 原型' },
  { key: 'prd', label: '⑤ PRD' },
  { key: 'delivery', label: '⑥ 交付' },
]

const stageOrder = ['idea', 'thinking', 'structure', 'prototype', 'prd', 'delivery']

function stageCompleted(stageKey: string) {
  const currentIdx = stageOrder.indexOf(props.currentStage)
  const stageIdx = stageOrder.indexOf(stageKey)
  return stageIdx < currentIdx
}

function stageClass(stageKey: string) {
  if (stageKey === props.currentStage) return 'stage-step active'
  if (stageCompleted(stageKey)) return 'stage-step completed'
  return 'stage-step'
}
</script>

<style scoped>
.stage-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px 24px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  overflow-x: auto;
}

.stage-step-wrapper {
  display: flex;
  align-items: center;
}

.stage-step {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
  color: #909399;
  background: #f0f2f5;
  white-space: nowrap;
  transition: all 0.3s;
}

.stage-step .stage-number {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #dcdfe6;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
}

.stage-step.active {
  color: #2563eb;
  background: #eff6ff;
}

.stage-step.active .stage-number {
  background: #2563eb;
}

.stage-step.completed {
  color: #16a34a;
  background: #f0fdf4;
}

.stage-line {
  width: 24px;
  height: 2px;
  background: #dcdfe6;
  margin: 0 4px;
  transition: background 0.3s;
}

.stage-line.completed {
  background: #16a34a;
}
</style>
