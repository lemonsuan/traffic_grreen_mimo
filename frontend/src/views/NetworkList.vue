<!--
  NetworkList.vue — 路网列表页
  显示所有路网卡片，支持新建和进入
-->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { networkApi } from '../api'
import NetworkCard from '../components/NetworkCard.vue'

const router = useRouter()
const networks = ref<Array<{
  id: number; name: string; nodeCount: number; edgeCount: number;
  signalCount: number; status: string
}>>([])
const loading = ref(true)

async function loadNetworks() {
  loading.value = true
  try {
    const res = await networkApi.list()
    const list = res.data.results || res.data || []
    // 获取每个路网的详细统计
    const detailed = await Promise.all(
      list.map(async (n: any) => {
        try {
          const detail = await networkApi.get(n.id)
          const data = detail.data
          return {
            id: n.id,
            name: n.name,
            nodeCount: data.nodes?.length || 0,
            edgeCount: data.edges?.length || 0,
            signalCount: data.signals?.length || 0,
            status: 'idle'
          }
        } catch {
          return {
            id: n.id, name: n.name,
            nodeCount: 0, edgeCount: 0, signalCount: 0,
            status: 'idle'
          }
        }
      })
    )
    networks.value = detailed
  } catch (e) {
    console.error('获取路网列表失败:', e)
  } finally {
    loading.value = false
  }
}

function enterNetwork(id: number) {
  router.push(`/network/${id}`)
}

function createNew() {
  // 跳转到新路网页面，带框选模式标记
  router.push('/network/new?mode=draw')
}

onMounted(loadNetworks)
</script>

<template>
  <div class="network-list-page">
    <!-- 顶栏 -->
    <header class="page-header">
      <div class="header-left">
        <span class="system-icon">🚦</span>
        <h1 class="system-name">智慧交通控制平台</h1>
      </div>
      <div class="header-right">
        <span class="label">SMART TRAFFIC CONTROL</span>
      </div>
    </header>

    <!-- 内容区 -->
    <main class="page-content">
      <div class="section-header">
        <h2 class="section-title">路网管理</h2>
        <span class="section-count mono">{{ networks.length }} 个路网</span>
      </div>

      <!-- 加载中 -->
      <div v-if="loading" class="loading-state">
        <div class="loading-bar"></div>
        <span class="label">加载中...</span>
      </div>

      <!-- 卡片网格 -->
      <div v-else class="card-grid">
        <NetworkCard
          :id="0"
          name=""
          :node-count="0"
          :edge-count="0"
          :signal-count="0"
          :is-new="true"
          @click="createNew"
        />
        <NetworkCard
          v-for="net in networks"
          :key="net.id"
          v-bind="net"
          @enter="enterNetwork"
        />
      </div>
    </main>
  </div>
</template>

<style scoped>
.network-list-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  position: relative;
  z-index: 1;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--sp-4) var(--sp-6);
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-default);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
}

.system-icon {
  font-size: 24px;
}

.system-name {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.header-right .label {
  color: var(--text-muted);
}

.page-content {
  flex: 1;
  padding: var(--sp-6);
  overflow-y: auto;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--sp-5);
}

.section-title {
  font-size: 16px;
  font-weight: 600;
}

.section-count {
  font-size: 12px;
  color: var(--text-secondary);
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--sp-4);
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sp-3);
  padding: var(--sp-8);
}

.loading-bar {
  width: 200px;
  height: 3px;
  background: var(--bg-tertiary);
  border-radius: 2px;
  overflow: hidden;
  position: relative;
}

.loading-bar::after {
  content: '';
  position: absolute;
  top: 0;
  left: -40%;
  width: 40%;
  height: 100%;
  background: var(--accent-cyan);
  animation: loading 1s ease-in-out infinite;
}

@keyframes loading {
  0% { left: -40%; }
  100% { left: 100%; }
}
</style>
