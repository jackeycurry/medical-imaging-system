<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <h1>医疗档案管理系统</h1>
        <p>Medical Records Management System</p>
      </div>

      <div class="tabs">
        <button :class="{ active: tab === 'login' }" @click="tab = 'login'">登录</button>
        <button :class="{ active: tab === 'register' }" @click="tab = 'register'">注册</button>
      </div>

      <form v-if="tab === 'login'" @submit.prevent="handleLogin" class="form">
        <div class="form-item">
          <label>用户名</label>
          <input v-model="loginForm.username" placeholder="请输入用户名" required />
        </div>
        <div class="form-item">
          <label>密码</label>
          <input v-model="loginForm.password" type="password" placeholder="请输入密码" required />
        </div>
        <p v-if="error" class="error-msg">{{ error }}</p>
        <button type="submit" :disabled="loading" class="btn-primary">
          <span v-if="loading" class="loading-spinner"></span>
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>

      <form v-else @submit.prevent="handleRegister" class="form">
        <div class="form-item">
          <label>用户名</label>
          <input v-model="registerForm.username" placeholder="请输入用户名" required />
        </div>
        <div class="form-item">
          <label>密码</label>
          <input
            v-model="registerForm.password"
            type="password"
            placeholder="6位以上数字+字母组合"
            required
            @input="checkPasswordStrength"
          />
        </div>
        <div class="password-rules" v-if="registerForm.password">
          <div class="rule" :class="{ ok: rules.length }">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20,6 9,17 4,12"/>
            </svg>
            <span>至少6位字符</span>
          </div>
          <div class="rule" :class="{ ok: rules.digit }">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20,6 9,17 4,12"/>
            </svg>
            <span>包含数字</span>
          </div>
          <div class="rule" :class="{ ok: rules.letter }">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20,6 9,17 4,12"/>
            </svg>
            <span>包含英文字母</span>
          </div>
        </div>
        <div class="strength-bar" v-if="registerForm.password">
          <div class="strength-track">
            <div class="strength-fill" :class="strengthLevel" :style="{ width: strengthWidth }"></div>
          </div>
          <span class="strength-text" :class="strengthLevel">{{ strengthText }}</span>
        </div>
        <p v-if="error" class="error-msg">{{ error }}</p>
        <button type="submit" :disabled="loading || !isPasswordValid" class="btn-primary">
          <span v-if="loading" class="loading-spinner"></span>
          {{ loading ? '注册中...' : '注册' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

const router = useRouter()
const tab = ref('login')
const loading = ref(false)
const error = ref('')
const rules = reactive({ length: false, digit: false, letter: false })
const strengthLevel = ref('')
const strengthText = ref('')
const strengthWidth = ref('0%')

const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({ username: '', password: '' })

const isPasswordValid = computed(() => rules.length && rules.digit && rules.letter)

const checkPasswordStrength = () => {
  const p = registerForm.password
  rules.length = p.length >= 6
  rules.digit = /[0-9]/.test(p)
  rules.letter = /[a-zA-Z]/.test(p)

  const validCount = [rules.length, rules.digit, rules.letter].filter(Boolean).length
  if (validCount === 1) { strengthLevel.value = 'weak'; strengthText.value = '弱'; strengthWidth.value = '33%' }
  else if (validCount === 2) { strengthLevel.value = 'medium'; strengthText.value = '中'; strengthWidth.value = '66%' }
  else if (validCount === 3) { strengthLevel.value = 'strong'; strengthText.value = '强'; strengthWidth.value = '100%' }
  else { strengthLevel.value = ''; strengthText.value = ''; strengthWidth.value = '0%' }
}

const handleLogin = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await api.login(loginForm)
    if (res.code === 200 || res.code === undefined) {
      localStorage.setItem('token', res.data.access_token)
      localStorage.setItem('username', res.data.username)
      localStorage.setItem('role', res.data.role)
      router.push('/home')
    } else {
      error.value = res.message || '登录失败'
    }
  } catch (e) {
    error.value = e.response?.data?.message || '登录失败'
  } finally {
    loading.value = false
  }
}

const handleRegister = async () => {
  if (!isPasswordValid.value) {
    error.value = '密码不符合要求'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const res = await api.register(registerForm)
    if (res.code === 200 || res.code === undefined) {
      error.value = ''
      tab.value = 'login'
      loginForm.username = registerForm.username
      registerForm.password = ''
    } else {
      error.value = res.message || '注册失败'
    }
  } catch (e) {
    error.value = e.response?.data?.message || '注册失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #F5F7FA 0%, #E8ECF1 100%);
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 420px;
  background: #fff;
  border-radius: 16px;
  padding: 48px 40px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.06);
}

.login-header {
  text-align: center;
  margin-bottom: 36px;
}

.login-header h1 {
  font-size: 24px;
  font-weight: 600;
  color: #1f1f1f;
  margin: 0 0 8px;
}

.login-header p {
  font-size: 13px;
  color: #999;
  margin: 0;
  letter-spacing: 0.5px;
}

.tabs {
  display: flex;
  margin-bottom: 28px;
  border-bottom: 1px solid #E8E8E8;
}

.tabs button {
  flex: 1;
  padding: 14px;
  background: none;
  border: none;
  font-size: 15px;
  color: #666;
  cursor: pointer;
  position: relative;
  transition: color 0.2s;
}

.tabs button.active {
  color: #1677FF;
  font-weight: 500;
}

.tabs button.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 2px;
  background: #1677FF;
  border-radius: 2px 2px 0 0;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-item label {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.form-item input {
  padding: 12px 14px;
  border: 1px solid #E8E8E8;
  border-radius: 8px;
  font-size: 14px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.form-item input:focus {
  outline: none;
  border-color: #1677FF;
  box-shadow: 0 0 0 3px rgba(22,119,255,0.1);
}

.form-item input::placeholder {
  color: #BFBFBF;
}

.error-msg {
  color: #FF4D4F;
  font-size: 13px;
  margin: -8px 0 0;
}

.btn-primary {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 13px;
  background: #1677FF;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
  margin-top: 4px;
}

.btn-primary:hover:not(:disabled) {
  background: #4096FF;
}

.btn-primary:disabled {
  background: #D9D9D9;
  cursor: not-allowed;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.password-rules {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  background: #FAFAFA;
  border-radius: 8px;
  margin-top: -4px;
}

.rule {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #BFBFBF;
  transition: color 0.2s;
}

.rule svg {
  width: 16px;
  height: 16px;
}

.rule.ok {
  color: #52C41A;
}

.strength-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.strength-track {
  flex: 1;
  height: 4px;
  background: #E8E8E8;
  border-radius: 2px;
  overflow: hidden;
}

.strength-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s, background 0.3s;
}

.strength-fill.weak { background: #FF4D4F; }
.strength-fill.medium { background: #FA8C16; }
.strength-fill.strong { background: #52C41A; }

.strength-text {
  font-size: 12px;
  font-weight: 500;
  min-width: 24px;
}

.strength-text.weak { color: #FF4D4F; }
.strength-text.medium { color: #FA8C16; }
.strength-text.strong { color: #52C41A; }
</style>
