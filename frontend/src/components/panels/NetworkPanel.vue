<!--
  NetworkPanel.vue — 路网管理浮层
  功能: 路网信息、导出、删除、重新渠化
-->
<script setup lang="ts">
import { ref } from 'vue'
import { networkApi } from '../../api'

const props = defineProps<{
  networkId: number
  networkName: string
  nodeCount: number
  edgeCount: number
  signalCount: number
}>()

const emit = defineEmits<{
  close: []
  refresh: []
}>()

const channelizing = ref(false)

async function handleAutoChannelize() {
  channelizing.value = true
  try {
    await networkApi.autoChannelize(props.networkId)
    alert('自动渠化完成')
    emit('refresh')
  } catch (e: any) {
    alert('渠化失败: ' + (e.response?.data?.error || e.message))
  } finally {
    channelizing.value = false
  }
}

async function handleExport() {
  try {
    const res = await networkApi.exportNetwork(props.networkId)
    const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `network_${props.networkId}.json`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e: any) {
    alert('导出失败: ' + e.message)
  }
}
</script>

<template>
  <div class="panel network-panel">
    <div class="panel-header">
      <span class="panel-title label">路网管理</span>
      <button class="btn-icon" @click="emit('close')">✕</button>
    </div>
    <div class="panel-body">
      <div class="info-grid">
        <div class="info-item">
          <span class="label">名称</span>
          <span class="mono">{{ networkName }}</span>
        </div>
        <div class="info-item">
          <span class="label">节点</span>
          <span class="mono">{{ nodeCount }}</span>
        </div>
        <div class="info-item">
          <span class="label">路段</span>
          <span class="mono">{{ edgeCount }}</span>
        </div>
        <div class="info-item">
          <span class="label">信号灯</span>
          <span class="mono">{{ signalCount }}</span>
        </div>
      </div>

      <div class="divider"></div>

      <div class="actions">
        <button class="btn-secondary" style="width: 100%" @click="handleAutoChannelize" :disabled="channelizing">
          {{ channelizing ? '渠化中...' : '自动渠化' }}
        </button>
        <button class="btn-secondary" style="width: 100%" @click="handleExport">导出 JSON</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.network-panel {
  width: 280px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--sp-3) var(--sp-4);
  border-bottom: 1px solid var(--border-default);
}

.panel-title {
  color: var(--accent-cyan);
}

.panel-body {
  padding: var(--sp-4);
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--sp-2);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.info-item .mono {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.actions {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}
</style>
