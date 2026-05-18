<script setup>
import { onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import Login from './views/Login.vue'
import Layout from './views/Layout.vue'

const router = useRouter()
const route = useRoute()

onMounted(() => {
  if (route.path === '/login') return
  const token = localStorage.getItem('token')
  if (!token) {
    router.replace('/login')
  } else if (route.path === '/' || route.path === '/home') {
    // stay
  } else {
    router.replace('/home')
  }
})
</script>

<template>
  <router-view />
</template>