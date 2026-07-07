<template>
  <div class="auth-view">
    <div class="auth-card">
      <div class="auth-header">
        <h1 class="brand">AIPM Agent</h1>
        <p class="tagline">AI 产品经理 · 从想法到 PRD</p>
      </div>

      <el-tabs v-model="mode" class="auth-tabs">
        <el-tab-pane label="登录" name="login" />
        <el-tab-pane label="注册" name="register" />
      </el-tabs>

      <el-form :model="form" label-position="top" @submit.prevent="handleSubmit">
        <el-form-item v-if="mode === 'register'" label="用户名">
          <el-input v-model="form.username" placeholder="你的名字" size="large" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="you@example.com" size="large" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="至少 6 位"
            size="large"
            show-password
            @keyup.enter="handleSubmit"
          />
        </el-form-item>

        <el-alert v-if="error" :title="error" type="error" :closable="false" class="auth-error" />

        <el-button
          type="primary"
          size="large"
          class="submit-btn"
          :loading="loading"
          @click="handleSubmit"
        >
          {{ mode === 'login' ? '登录' : '注册并开始' }}
        </el-button>
      </el-form>

      <p class="switch-hint">
        {{ mode === 'login' ? '还没有账号？' : '已有账号？' }}
        <a @click="toggleMode">{{ mode === 'login' ? '去注册' : '去登录' }}</a>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const mode = ref<'login' | 'register'>('login')
const loading = ref(false)
const error = ref('')
const form = reactive({ email: '', username: '', password: '' })

function toggleMode() {
  mode.value = mode.value === 'login' ? 'register' : 'login'
  error.value = ''
}

async function handleSubmit() {
  error.value = ''
  if (!form.email.trim() || !form.password.trim()) {
    error.value = '请填写邮箱和密码'
    return
  }
  if (mode.value === 'register' && !form.username.trim()) {
    error.value = '请填写用户名'
    return
  }
  if (form.password.length < 6) {
    error.value = '密码至少 6 位'
    return
  }

  loading.value = true
  try {
    if (mode.value === 'login') {
      await auth.login(form.email, form.password)
    } else {
      await auth.register(form.email, form.username, form.password)
    }
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch (e: any) {
    error.value = e.message || '操作失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-view {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #eff6ff, #f0fdf4);
  padding: 24px;
}

.auth-card {
  width: 100%;
  max-width: 420px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
  padding: 40px 32px;
}

.auth-header {
  text-align: center;
  margin-bottom: 24px;
}

.brand {
  font-size: 28px;
  font-weight: 700;
  color: #2563eb;
  margin: 0 0 6px;
}

.tagline {
  color: #6b7280;
  font-size: 14px;
  margin: 0;
}

.auth-tabs {
  margin-bottom: 8px;
}

.auth-error {
  margin-bottom: 16px;
}

.submit-btn {
  width: 100%;
  margin-top: 8px;
}

.switch-hint {
  text-align: center;
  margin-top: 20px;
  font-size: 13px;
  color: #6b7280;
}

.switch-hint a {
  color: #2563eb;
  cursor: pointer;
  margin-left: 4px;
}

.switch-hint a:hover {
  text-decoration: underline;
}
</style>
