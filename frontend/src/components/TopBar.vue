<!--
  TopBar.vue — 顶部状态栏
  显示: 返回按钮、路网名称、模式切换、连接状态
-->
<script setup lang="ts">
import { useAppStore } from '../stores/app'

const props = defineProps<{
  networkName: string
  networkId: string
}>()

const emit = defineEmits<{
  back: []
}>()

const appStore = useAppStore()

const modes = [
  { id: 'view' as const, label: '查看', icon: '👁' },
  { id: 'edit' as const, label: '编辑', icon: '✏' },
  { id: 'simulate' as const, label: '仿真', icon: '▶' },
  { id: 'optimize' as const, label: '优化', icon: '⚡' },
]
</script>

<template>
  <header class="top-bar">
    <div class="top-left">
      <button class="btn-icon" @click="emit('back')" title="返回列表">
        ←
      </button>
      <div class="network-info">
        <span class="network-id mono">#{{ networkId.padStart(3, '0') }}</span>
        <span class="network-name">{{ networkName }}</span>
      </div>
    </div>

    <div class="top-center">
      <div class="mode-tabs">
        <button
          v-for="m in modes"
          :key="m.id"
          :class="['mode-tab', { active: appStore.mode === m.id }]"
          @click="appStore.setMode(m.id)"
        >
          {{ m.label }}
        </button>
      </div>
    </div>

    <div class="top-right">
      <span class="status-dot online"></span>
      <span class="label">已连接</span>
    </div>
  </header>
</template>

<style scoped>
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 48px;
  padding: 0 var(--sp-4);
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-default);
  z-index: 100;
}

.top-left {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
}

.network-info {
  display: flex;
  align-items: baseline;
  gap: var(--sp-2);
}

.network-id {
  font-size: 12px;
  font-weight: 600;
  color: var(--accent-cyan);
}

.network-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.top-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

.mode-tabs {
  display: flex;
  gap: 0;
  background: var(--bg-primary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.mode-tab {
  padding: 6px 16px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.mode-tab:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.03);
}

.mode-tab.active {
  color: #0a0e14;
  background: var(--accent-cyan);
}

.top-right {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}
</style>
