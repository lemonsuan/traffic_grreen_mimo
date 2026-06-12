<!--
  OptPanel.vue — 信号优化浮层
  功能: 选择优化层级/算法, 运行优化, 查看结果
-->
<script setup lang="ts">
import { ref, computed } from 'vue'
import { optimizationApi } from '../../api'

const props = defineProps<{ networkId: number }>()
const emit = defineEmits<{ close: [] }>()

const level = ref('intersection')
const algorithm = ref('webster')
const optimizing = ref(false)
const result = ref<any>(null)

const algorithms: Record<string, { id: string; name: string }[]> = {
  intersection: [
    { id: 'webster', name: 'Webster' },
    { id: 'hcm', name: 'HCM' },
    { id: 'actuated', name: '感应控制' },
    { id: 'adaptive', name: '自适应' },
  ],
  corridor: [
    { id: 'maxband', name: 'MAXBAND' },
    { id: 'passer', name: 'PASSER-II' },
    { id: 'ga', name: '遗传算法' },
    { id: 'pso', name: '粒子群' },
  ],
  network: [
    { id: 'transyt', name: 'TRANSYT' },
    { id: 'scoot', name: 'SCOOT' },
    { id: 'nsga', name: 'NSGA-II' },
  ],
}

const currentAlgos = computed(() => algorithms[level.value] || [])

async function runOptimization() {
  optimizing.value = true
  result.value = null
  try {
    let res
    const params = { target_saturation: 0.85, min_green_time: 7, max_cycle: 180 }
    if (level.value === 'intersection') {
      res = await optimizationApi.optimizeIntersection({
        node_id: 'N000', algorithm: algorithm.value, params,
        traffic_data: { approaches: { north_through: { volume: 500 }, south_through: { volume: 450 }, east_through: { volume: 400 }, west_through: { volume: 380 } } }
      })
    } else if (level.value === 'corridor') {
      res = await optimizationApi.optimizeCorridor({ node_ids: ['N000', 'N001', 'N002'], algorithm: algorithm.value, params })
    } else {
      res = await optimizationApi.optimizeNetwork({ network_id: props.networkId, algorithm: algorithm.value, params })
    }
    result.value = res.data
  } catch (e: any) {
    alert('优化失败: ' + (e.response?.data?.error || e.message))
  } finally {
    optimizing.value = false
  }
}
</script>

<template>
  <div class="panel opt-panel">
    <div class="panel-header">
      <span class="panel-title label">信号优化</span>
      <button class="btn-icon" @click="emit('close')">✕</button>
    </div>
    <div class="panel-body">
      <div class="form-group">
        <label class="label">优化层级</label>
        <select v-model="level">
          <option value="intersection">单点优化</option>
          <option value="corridor">干线优化</option>
          <option value="network">区域优化</option>
        </select>
      </div>
      <div class="form-group">
        <label class="label">算法</label>
        <div class="algo-list">
          <label v-for="a in currentAlgos" :key="a.id" :class="['algo-item', { active: algorithm === a.id }]">
            <input type="radio" :value="a.id" v-model="algorithm" />
            {{ a.name }}
          </label>
        </div>
      </div>

      <button class="btn-primary" style="width:100%" @click="runOptimization" :disabled="optimizing">
        {{ optimizing ? '优化中...' : '⚡ 开始优化' }}
      </button>

      <div v-if="result" class="result-card card">
        <div class="result-row">
          <span class="label">算法</span>
          <span class="mono">{{ result.algorithm }}</span>
        </div>
        <div class="result-row">
          <span class="label">平均延误</span>
          <span class="metric-value mono">{{ result.performance?.avg_delay?.toFixed(1) }}s</span>
        </div>
        <div class="result-row">
          <span class="label">计算时间</span>
          <span class="mono">{{ result.computation_time?.toFixed(3) }}s</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.opt-panel { width: 280px; }
.panel-header { display: flex; justify-content: space-between; align-items: center; padding: var(--sp-3) var(--sp-4); border-bottom: 1px solid var(--border-default); }
.panel-title { color: var(--accent-cyan); }
.panel-body { padding: var(--sp-4); display: flex; flex-direction: column; gap: var(--sp-3); }
.form-group { display: flex; flex-direction: column; gap: 4px; }
select { width: 100%; }
.algo-list { display: flex; flex-direction: column; gap: 4px; }
.algo-item { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border: 1px solid var(--border-default); border-radius: var(--radius-sm); cursor: pointer; font-size: 12px; }
.algo-item.active { border-color: var(--accent-cyan); background: var(--accent-cyan-dim); }
.result-card { padding: var(--sp-3); margin-top: var(--sp-2); }
.result-row { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; }
</style>
