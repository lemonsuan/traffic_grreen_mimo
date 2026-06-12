<!--
  BottomBar.vue — 底部时间轴播放器 + 实时指标
-->
<script setup lang="ts">
import { ref, computed } from 'vue'
import { useSimulationStore } from '../stores/simulation'

const simStore = useSimulationStore()

const speedOptions = [0.5, 1, 2, 5, 10, 30]
const selectedSpeed = ref(1)

const progressPercent = computed(() => simStore.progress)

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

function onTimelineClick(e: MouseEvent) {
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  const ratio = (e.clientX - rect.left) / rect.width
  const time = ratio * simStore.duration
  // TODO: seek to time
}
</script>

<template>
  <footer class="bottom-bar">
    <!-- 播放控制 -->
    <div class="playback-controls">
      <button class="btn-icon" title="重置" @click="simStore.reset()">
        ⏮
      </button>
      <button
        class="btn-icon play-btn"
        :class="{ active: simStore.isRunning }"
        title="播放/暂停"
        @click="simStore.isRunning ? simStore.pauseSimulation() : simStore.resumeSimulation()"
      >
        {{ simStore.isRunning ? '⏸' : '▶' }}
      </button>
      <button class="btn-icon" title="停止" @click="simStore.stopSimulation()">
        ⏹
      </button>
    </div>

    <!-- 时间轴 -->
    <div class="timeline-section">
      <span class="time-current mono">{{ formatTime(simStore.currentTime) }}</span>
      <div class="timeline-bar" @click="onTimelineClick">
        <div class="timeline-track">
          <div class="timeline-fill" :style="{ width: progressPercent + '%' }"></div>
          <div class="timeline-thumb" :style="{ left: progressPercent + '%' }"></div>
        </div>
      </div>
      <span class="time-total mono">{{ formatTime(simStore.duration) }}</span>
    </div>

    <!-- 速度选择 -->
    <div class="speed-selector">
      <button
        v-for="speed in speedOptions"
        :key="speed"
        :class="['speed-btn', { active: selectedSpeed === speed }]"
        @click="selectedSpeed = speed"
      >
        {{ speed }}x
      </button>
    </div>

    <!-- 分隔 -->
    <div class="toolbar-sep"></div>

    <!-- 实时指标 -->
    <div class="metrics-strip">
      <div class="metric">
        <span class="metric-label">延误</span>
        <span class="metric-value mono">{{ simStore.metrics.avg_delay.toFixed(1) }}<span class="metric-unit">s</span></span>
      </div>
      <div class="metric">
        <span class="metric-label">排队</span>
        <span class="metric-value mono">{{ simStore.metrics.avg_queue_length.toFixed(0) }}<span class="metric-unit">辆</span></span>
      </div>
      <div class="metric">
        <span class="metric-label">吞吐</span>
        <span class="metric-value mono">{{ simStore.metrics.throughput }}</span>
      </div>
      <div class="metric">
        <span class="metric-label">V/C</span>
        <span class="metric-value mono" :class="{ warning: simStore.metrics.vcr > 0.8 }">
          {{ simStore.metrics.vcr.toFixed(2) }}
        </span>
      </div>
    </div>

    <!-- 状态 -->
    <div class="status-section">
      <span
        :class="['badge', {
          'badge-green': simStore.status === 'completed',
          'badge-amber': simStore.status === 'running',
          'badge-cyan': simStore.status === 'idle',
          'badge-red': simStore.status === 'paused',
        }]"
      >
        {{ { idle: '空闲', running: '运行中', paused: '已暂停', completed: '已完成' }[simStore.status] }}
      </span>
    </div>
  </footer>
</template>

<style scoped>
.bottom-bar {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  height: 48px;
  padding: 0 var(--sp-4);
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-default);
  z-index: 100;
}

.playback-controls {
  display: flex;
  gap: 2px;
}

.play-btn.active {
  color: var(--accent-amber);
  background: var(--accent-amber-dim);
}

.timeline-section {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

.time-current, .time-total {
  font-size: 12px;
  color: var(--text-secondary);
  min-width: 60px;
}

.time-total {
  text-align: right;
}

.timeline-bar {
  flex: 1;
  height: 24px;
  display: flex;
  align-items: center;
  cursor: pointer;
}

.timeline-track {
  width: 100%;
  height: 4px;
  background: var(--bg-primary);
  border-radius: 2px;
  position: relative;
}

.timeline-fill {
  height: 100%;
  background: var(--accent-cyan);
  border-radius: 2px;
  transition: width 100ms linear;
}

.timeline-thumb {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 12px;
  height: 12px;
  background: var(--accent-cyan);
  border: 2px solid var(--bg-secondary);
  border-radius: 50%;
  transition: left 100ms linear;
}

.speed-selector {
  display: flex;
  gap: 2px;
}

.speed-btn {
  padding: 4px 8px;
  font-size: 10px;
  font-weight: 600;
  font-family: var(--font-mono);
  color: var(--text-muted);
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.speed-btn:hover {
  color: var(--text-secondary);
}

.speed-btn.active {
  color: var(--accent-cyan);
  background: var(--accent-cyan-dim);
  border-color: var(--border-default);
}

.metrics-strip {
  display: flex;
  gap: var(--sp-4);
}

.metric {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
}

.metric .metric-label {
  font-size: 9px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
}

.metric .metric-value {
  font-size: 14px;
  font-weight: 700;
  color: var(--accent-cyan);
}

.metric .metric-value.warning {
  color: var(--accent-amber);
}

.status-section {
  min-width: 60px;
  text-align: right;
}
</style>
