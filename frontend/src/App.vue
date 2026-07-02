<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-left">
        <h1 class="app-title">AIPM Agent</h1>
        <span class="app-subtitle">AI 产品经理</span>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="router.push('/')">
          <el-icon><House /></el-icon>
          首页
        </el-button>
      </div>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
</script>

<style scoped>
.app-container {
  min-height: 100vh;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: white;
  border-bottom: 1px solid #e4e7ed;
  height: 60px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.app-title {
  font-size: 18px;
  font-weight: 700;
  color: #2563eb;
  margin: 0;
}

.app-subtitle {
  font-size: 13px;
  color: #909399;
  padding: 2px 8px;
  background: #f0f2f5;
  border-radius: 4px;
}
</style>
