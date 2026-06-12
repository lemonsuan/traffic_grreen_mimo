<!--
  NetworkCard.vue — 路网列表卡片
  工业风卡片，显示路网基本信息和状态
-->
<script setup lang="ts">
interface Props {
  id: number
  name: string
  nodeCount: number
  edgeCount: number
  signalCount: number
  status?: string
  isNew?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  status: 'idle',
  isNew: false
})

const emit = defineEmits<{
  enter: [id: number]
}>()

const statusColors: Record<string, string> = {
  idle: 'var(--text-muted)',
  running: 'var(--accent-green)',
  optimizing: 'var(--accent-amber)',
  error: 'var(--accent-red)',
}

const statusLabels: Record<string, string> = {
  idle: '空闲',
  running: '运行中',
  optimizing: '优化中',
  error: '异常',
}
</script>

<template>
  <div class="network-card card" :class="{ 'is-new': isNew }" @click="!isNew && emit('enter', id)">
    <!-- 新建卡片 -->
    <div v-if="isNew" class="new-card-content">
      <div class="new-icon">+</div>
      <div class="new-label">框选新建路网</div>
    </div>

    <!-- 路网卡片 -->
    <template v-else>
      <div class="card-header">
        <span class="card-id mono">#{{ String(id).padStart(3, '0') }}</span>
        <span class="status-dot" :style="{ background: statusColors[status] }"></span>
      </div>

      <div class="card-name">{{ name }}</div>

      <div class="card-stats">
        <div class="stat">
          <span class="stat-value mono">{{ nodeCount }}</span>
          <span class="stat-label">节点</span>
        </div>
        <div class="stat">
          <span class="stat-value mono">{{ edgeCount }}</span>
          <span class="stat-label">路段</span>
        </div>
        <div class="stat">
          <span class="stat-value mono">{{ signalCount }}</span>
          <span class="stat-label">信号</span>
        </div>
      </div>

      <div class="card-footer">
        <span class="badge badge-cyan">{{ statusLabels[status] || status }}</span>
        <button class="btn-primary btn-enter" @click.stop="emit('enter', id)">进入 →</button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.network-card {
  padding: var(--sp-4);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  min-width: 240px;
}

.network-card:hover {
  border-color: var(--accent-cyan);
  box-shadow: 0 0 12px rgba(56, 189, 248, 0.1);
}

.network-card:active {
  transform: translateY(1px);
}

.is-new {
  border-style: dashed;
  border-color: var(--text-muted);
  justify-content: center;
  align-items: center;
  min-height: 180px;
}

.is-new:hover {
  border-color: var(--accent-cyan);
}

.new-card-content {
  text-align: center;
}

.new-icon {
  font-size: 36px;
  color: var(--text-muted);
  font-weight: 300;
  line-height: 1;
}

.new-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: var(--sp-2);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-id {
  font-size: 12px;
  font-weight: 600;
  color: var(--accent-cyan);
  letter-spacing: 0.05em;
}

.card-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-stats {
  display: flex;
  gap: var(--sp-4);
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.stat-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-secondary);
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: auto;
}

.btn-enter {
  padding: 4px 12px;
  font-size: 12px;
}
</style>
