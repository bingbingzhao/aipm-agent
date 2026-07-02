<template>
  <div class="home-view">
    <div class="welcome-card">
      <h2>从想法到产品方案，AI 全程辅助</h2>
      <p class="welcome-desc">
        输入你的产品想法，AIPM Agent 会通过多轮对话帮你理清需求、分析市场、
        生成原型和 PRD。
      </p>
      <el-button type="primary" size="large" @click="showCreate = true">
        <el-icon><Plus /></el-icon>
        创建新项目
      </el-button>
    </div>

    <el-dialog v-model="showCreate" title="创建新项目" width="500px">
      <el-form :model="form" label-position="top">
        <el-form-item label="项目名称">
          <el-input v-model="form.title" placeholder="给项目起个名字" />
        </el-form-item>
        <el-form-item label="初步想法">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            placeholder="简单描述你的产品想法..."
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="creating">
          创建并开始
        </el-button>
      </template>
    </el-dialog>

    <div v-if="store.projects.length > 0" class="project-list">
      <h3>我的项目</h3>
      <div class="project-grid">
        <el-card
          v-for="project in store.projects"
          :key="project.id"
          class="project-card"
          shadow="hover"
          @click="router.push(`/project/${project.id}`)"
        >
          <div class="card-header">
            <h4>{{ project.title }}</h4>
            <el-tag size="small" :type="stageTagType(project.stage)">
              {{ STAGE_LABELS[project.stage] || project.stage }}
            </el-tag>
          </div>
          <p class="card-desc">{{ project.description || '暂无描述' }}</p>
          <div class="card-footer">
            <span class="card-date">{{ formatDate(project.updated_at) }}</span>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectStore } from '@/stores/project'
import { STAGE_LABELS } from '@/types'

const router = useRouter()
const store = useProjectStore()

const showCreate = ref(false)
const creating = ref(false)
const form = reactive({ title: '', description: '' })

onMounted(() => {
  store.fetchProjects()
})

async function handleCreate() {
  if (!form.title.trim()) return
  creating.value = true
  try {
    const project = await store.createProject(form.title, form.description)
    showCreate.value = false
    form.title = ''
    form.description = ''
    router.push(`/project/${project.id}`)
  } finally {
    creating.value = false
  }
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

function stageTagType(stage: string) {
  if (stage === 'idea') return 'info'
  if (stage === 'thinking' || stage === 'structure') return ''
  if (stage === 'prototype') return 'success'
  if (stage === 'prd' || stage === 'delivery') return 'success'
  return 'info'
}
</script>

<style scoped>
.home-view {
  max-width: 900px;
  margin: 0 auto;
}

.welcome-card {
  text-align: center;
  padding: 48px 24px;
  background: linear-gradient(135deg, #eff6ff, #f0fdf4);
  border-radius: 12px;
  margin-bottom: 32px;
}

.welcome-card h2 {
  font-size: 24px;
  color: #1e3a8a;
  margin-bottom: 12px;
}

.welcome-desc {
  color: #6b7280;
  margin-bottom: 24px;
  font-size: 15px;
  line-height: 1.6;
}

.project-list h3 {
  font-size: 18px;
  margin-bottom: 16px;
}

.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.project-card {
  cursor: pointer;
  transition: transform 0.2s;
}

.project-card:hover {
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.card-header h4 {
  margin: 0;
  font-size: 16px;
}

.card-desc {
  color: #909399;
  font-size: 13px;
  line-height: 1.5;
  margin-bottom: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-date {
  color: #c0c4cc;
  font-size: 12px;
}
</style>
