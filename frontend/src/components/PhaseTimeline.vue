<!--
  PhaseTimeline.vue — 相位时间轴编辑器
  功能: 可视化显示各相位绿灯/黄灯/全红时间, 支持拖拽调整
-->
<script setup lang="ts">
import { ref, computed } from 'vue'

interface PhaseData {
  index: number
  green: number
  yellow: number
  all_red: number
  light_type: string
  phase_type: string
}

const props = defineProps<{
  phases: PhaseData[]
  cycleLength: number
}>()

const emit = defineEmits<{
  update: [phases: PhaseData[]]
}>()

const dragging = ref<{ phaseIndex: number; edge: 'green' | 'yellow' } | null>(null)

const totalBarWidth = 100 // percent

const phaseSegments = computed(() => {
  const total = props.cycleLength || 1
  return props.phases.map((p) => ({
    ...p,
    greenPct: (p.green / total) * 100,
    yellowPct: (p.yellow / total) * 100,
    redPct: (p.all_red / total) * 100,
  }))
})

function getPhaseTypeLabel(type: string): string {
  const map: Record<string, string> = {
    through: '直行', left_turn: '左转', right_turn: '右转', pedestrian: '行人',
  }
  return map[type] || type
}

function getLightIcon(type: string): string {
  return type === 'arrow' ? '➜' : '●'
}

function onMouseDown(phaseIndex: number, edge: 'green' | 'yellow', e: MouseEvent) {
  dragging.value = { phaseIndex, edge }
  e.preventDefault()

  const onMouseMove = (ev: MouseEvent) => {
    if (!dragging.value) return
    // 简化: 根据鼠标X位置计算新时间
    const rect = (e.target as HTMLElement).closest('.phase-bar-container')?.getBoundingClientRect()
    if (!rect) return
    const ratio = Math.max(0.05, Math.min(0.95, (ev.clientX - rect.left) / rect.width))
    const newTime = Math.round(ratio * props.cycleLength)

    const newPhases = [...props.phases]
    const phase = { ...newPhases[phaseIndex] }
    if (edge === 'green') {
      const diff = newTime - phase.green
      phase.green = Math.max(5, newTime)
      // 调整下一相位补偿
      if (phaseIndex < newPhases.length - 1) {
        const next = { ...newPhases[phaseIndex + 1] }
        next.green = Math.max(5, next.green - diff)
        newPhases[phaseIndex + 1] = next
      }
    }
    newPhases[phaseIndex] = phase
    emit('update', newPhases)
  }

  const onMouseUp = () => {
    dragging.value = null
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }

  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}
</script>

<template>
  <div class="phase-timeline">
    <div class="timeline-header">
      <span class="label">相位时间轴</span>
      <span class="cycle-info mono">周期: {{ cycleLength }}s</span>
    </div>

    <!-- 相位条 -->
    <div class="phase-bar-container">
      <div
        v-for="seg in phaseSegments"
        :key="seg.index"
        class="phase-bar"
        :style="{ width: seg.greenPct + seg.yellowPct + seg.redPct + '%' }"
      >
        <div
          class="phase-green"
          :style="{ width: (seg.greenPct / (seg.greenPct + seg.yellowPct + seg.redPct) * 100) + '%' }"
          @mousedown="onMouseDown(seg.index, 'green', $event)"
        >
          <span v-if="seg.greenPct > 8" class="phase-text">
            {{ getLightIcon(seg.light_type) }} {{ seg.green }}s
          </span>
        </div>
        <div
          class="phase-yellow"
          :style="{ width: (seg.yellowPct / (seg.greenPct + seg.yellowPct + seg.redPct) * 100) + '%' }"
        >
          <span v-if="seg.yellowPct > 5" class="phase-text-sm">{{ seg.yellow }}s</span>
        </div>
        <div
          class="phase-red"
          :style="{ width: (seg.redPct / (seg.greenPct + seg.yellowPct + seg.redPct) * 100) + '%' }"
        ></div>
      </div>
    </div>

    <!-- 相位标签 -->
    <div class="phase-labels">
      <div
        v-for="seg in phaseSegments"
        :key="seg.index"
        class="phase-label"
        :style="{ width: (seg.greenPct + seg.yellowPct + seg.redPct) + '%' }"
      >
        <span class="phase-index">P{{ seg.index + 1 }}</span>
        <span class="phase-type">{{ getPhaseTypeLabel(seg.phase_type) }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.phase-timeline {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.cycle-info {
  font-size: 12px;
  color: var(--accent-cyan);
}

.phase-bar-container {
  display: flex;
  height: 36px;
  background: var(--bg-primary);
  border-radius: var(--radius-sm);
  overflow: hidden;
  gap: 2px;
  cursor: pointer;
}

.phase-bar {
  display: flex;
  height: 100%;
  gap: 1px;
  min-width: 8px;
}

.phase-green {
  flex: 1;
  background: var(--accent-green);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: ew-resize;
  transition: background 100ms;
  border-radius: 2px 0 0 2px;
}

.phase-green:hover {
  background: #16a34a;
}

.phase-yellow {
  background: var(--accent-amber);
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 4px;
}

.phase-red {
  background: rgba(239, 68, 68, 0.2);
  min-width: 2px;
  border-radius: 0 2px 2px 0;
}

.phase-text {
  font-size: 11px;
  font-weight: 600;
  color: #0a0e14;
  white-space: nowrap;
  pointer-events: none;
}

.phase-text-sm {
  font-size: 9px;
  font-weight: 600;
  color: #0a0e14;
  pointer-events: none;
}

.phase-labels {
  display: flex;
  gap: 2px;
}

.phase-label {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
  min-width: 8px;
}

.phase-index {
  font-size: 10px;
  font-weight: 700;
  color: var(--text-primary);
  font-family: var(--font-mono);
}

.phase-type {
  font-size: 9px;
  color: var(--text-secondary);
}
</style>
