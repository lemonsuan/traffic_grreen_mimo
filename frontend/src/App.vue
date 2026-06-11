<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const navItems = [
  { path: '/', name: '首页', icon: '🏠' },
  { path: '/network', name: '路网编辑', icon: '🗺️' },
  { path: '/simulation', name: '仿真控制', icon: '▶️' },
  { path: '/optimization', name: '信号优化', icon: '⚡' },
  { path: '/analysis', name: '数据分析', icon: '📊' }
]

function navigateTo(path: string) {
  router.push(path)
}
</script>

<template>
  <div class="app-layout">
    <nav class="sidebar">
      <div class="logo">
        <div class="logo-icon">🚦</div>
        <div class="logo-text">交通仿真系统</div>
      </div>
      
      <div class="nav-items">
        <div 
          v-for="item in navItems" 
          :key="item.path"
          :class="['nav-item', { active: $route.path === item.path }]"
          @click="navigateTo(item.path)"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span class="nav-text">{{ item.name }}</span>
        </div>
      </div>
    </nav>
    
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 200px;
  background: #001529;
  color: white;
  display: flex;
  flex-direction: column;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo-icon {
  font-size: 24px;
}

.logo-text {
  font-size: 16px;
  font-weight: bold;
}

.nav-items {
  flex: 1;
  padding: 12px 0;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.1);
}

.nav-item.active {
  background: #1890ff;
}

.nav-icon {
  font-size: 18px;
}

.nav-text {
  font-size: 14px;
}

.main-content {
  flex: 1;
  background: #f0f2f5;
  overflow: auto;
}
</style>
