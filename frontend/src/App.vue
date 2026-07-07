<template>
  <!-- Login page: no app chrome -->
  <router-view v-if="isLoginPage" />

  <!-- App shell -->
  <el-container v-else class="app-container">
    <el-header class="app-header">
      <div class="header-left">
        <h1 class="app-title">AIPM Agent</h1>
        <span class="app-subtitle">AI 产品经理</span>
      </div>
      <div class="header-right">
        <el-button type="primary" text @click="router.push('/')">
          <el-icon><House /></el-icon>
          首页
        </el-button>
        <el-dropdown v-if="auth.user" trigger="click" @command="handleCommand">
          <span class="user-chip">
            <el-avatar :size="28">{{ userInitial }}</el-avatar>
            <span class="user-name">{{ auth.user.username }}</span>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item disabled>{{ auth.user.email }}</el-dropdown-item>
              <el-dropdown-item command="logout" divided>
                <el-icon><SwitchButton /></el-icon> 退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const isLoginPage = computed(() => route.name === 'login')
const userInitial = computed(() =>
  auth.user?.username?.charAt(0).toUpperCase() || '?'
)

function handleCommand(cmd: string) {
  if (cmd === 'logout') {
    auth.logout()
    router.push('/login')
  }
}
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

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 8px;
  transition: background 0.2s;
}

.user-chip:hover {
  background: #f0f2f5;
}

.user-name {
  font-size: 14px;
  color: #303133;
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
