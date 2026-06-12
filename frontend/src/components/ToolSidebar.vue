<!--
  ToolSidebar.vue — 左侧竖排工具栏
  根据当前模式显示不同工具
-->
<script setup lang="ts">
import { useAppStore } from '../stores/app'

const emit = defineEmits<{
  simStart: []
  simStop: []
  simReset: []
}>()

const appStore = useAppStore()

interface ToolItem {
  id: string
  icon: string
  label: string
  mode?: string
  action?: () => void
}

const viewTools: ToolItem[] = [
  { id: 'select', icon: '⊕', label: '选择', mode: 'view' },
  { id: 'info', icon: 'ℹ', label: '信息', mode: 'view' },
]

const editTools: ToolItem[] = [
  { id: 'add-node', icon: '◉', label: '添加节点', mode: 'edit' },
  { id: 'add-edge', icon: '▬', label: '添加路段', mode: 'edit' },
  { id: 'delete', icon: '✕', label: '删除', mode: 'edit' },
]

const simTools: ToolItem[] = [
  { id: 'sim-start', icon: '▶', label: '启动' },
  { id: 'sim-pause', icon: '⏸', label: '暂停' },
  { id: 'sim-stop', icon: '⏹', label: '停止' },
  { id: 'sim-reset', icon: '↺', label: '重置' },
]

const optTools: ToolItem[] = [
  { id: 'opt-intersection', icon: '①', label: '单点优化', mode: 'optimize' },
  { id: 'opt-corridor', icon: '⇔', label: '干线优化', mode: 'optimize' },
  { id: 'opt-network', icon: '◈', label: '区域优化', mode: 'optimize' },
]

function getTools(): ToolItem[] {
  switch (appStore.mode) {
    case 'edit': return editTools
    case 'simulate': return simTools
    case 'optimize': return optTools
    default: return viewTools
  }
}

function handleToolClick(tool: ToolItem) {
  switch (tool.id) {
    case 'sim-start': emit('simStart'); break
    case 'sim-stop': emit('simStop'); break
    case 'sim-reset': emit('simReset'); break
  }
}
</script>

<template>
  <aside class="tool-sidebar">
    <div class="tool-group">
      <button
        v-for="tool in getTools()"
        :key="tool.id"
        class="tool-btn"
        :title="tool.label"
        @click="handleToolClick(tool)"
      >
        <span class="tool-icon">{{ tool.icon }}</span>
        <span class="tool-label">{{ tool.label }}</span>
      </button>
    </div>
  </aside>
</template>

<style scoped>
.tool-sidebar {
  width: 56px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  padding: var(--sp-2) 0;
  z-index: 100;
}

.tool-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 var(--sp-1);
}

.tool-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: var(--sp-2) var(--sp-1);
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.tool-btn:hover {
  color: var(--accent-cyan);
  background: var(--accent-cyan-dim);
  border-color: var(--border-default);
}

.tool-btn:active {
  transform: translateY(1px);
}

.tool-icon {
  font-size: 16px;
  line-height: 1;
}

.tool-label {
  font-size: 9px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  white-space: nowrap;
}
</style>
