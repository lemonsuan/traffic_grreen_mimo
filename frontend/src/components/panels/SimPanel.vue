<!--
  SimPanel.vue — 仿真配置浮层
  功能: 仿真参数配置、启动/停止控制
-->
<script setup lang="ts">
import { ref } from 'vue'
import { useSimulationStore } from '../../stores/simulation'

const props = defineProps<{ networkId: number }>()
const emit = defineEmits<{ close: [] }>()
const simStore = useSimulationStore()

const duration = ref(1800)
const stepSize = ref(1)
const speedMultiplier = ref(1)

async function handleStart() {
  try {
    await simStore.startSimulation({
      network_id: props.networkId,
      duration: duration.value,
      step_size: stepSize.value,
      speed_multiplier: speedMultiplier.value,
    })
  } catch (e: any) {
    alert('启动失败: ' + (e.response?.data?.error || e.message))
  }
}
</script>

<template>
  <div class="panel sim-panel">
    <div class="panel-header">
      <span class="panel-title label">仿真配置</span>
      <button class="btn-icon" @click="emit('close')">✕</button>
    </div>
    <div class="panel-body">
      <div class="form-group">
        <label class="label">仿真时长 (秒)</label>
        <input v-model.number="duration" type="number" />
      </div>
      <div class="form-group">
        <label class="label">步长 (秒)</label>
        <input v-model.number="stepSize" type="number" step="0.1" />
      </div>
      <div class="form-group">
        <label class="label">速度倍率</label>
        <div class="speed-row">
          <button v-for="s in [1, 2, 5, 10]" :key="s"
            :class="['btn-secondary', { active: speedMultiplier === s }]"
            @click="speedMultiplier = s">{{ s }}x</button>
        </div>
      </div>

      <div class="divider"></div>

      <button class="btn-primary" style="width:100%" @click="handleStart" :disabled="simStore.isRunning">
        {{ simStore.isRunning ? '运行中...' : '▶ 启动仿真' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.sim-panel { width: 260px; }
.panel-header { display: flex; justify-content: space-between; align-items: center; padding: var(--sp-3) var(--sp-4); border-bottom: 1px solid var(--border-default); }
.panel-title { color: var(--accent-cyan); }
.panel-body { padding: var(--sp-4); display: flex; flex-direction: column; gap: var(--sp-3); }
.form-group { display: flex; flex-direction: column; gap: 4px; }
.form-group input { width: 100%; }
.speed-row { display: flex; gap: 4px; }
.speed-row button { flex: 1; padding: 4px; font-size: 12px; }
.speed-row .active { background: var(--accent-cyan-dim); color: var(--accent-cyan); border-color: var(--accent-cyan); }
</style>
