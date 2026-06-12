<!--
  IntersectionTrend.vue — 交叉口历史趋势图
  功能: ECharts展示延误/排队/V.C比的时间趋势
-->
<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

interface TrendData {
  time: string
  delay: number
  queue: number
  vcr: number
}

const props = defineProps<{
  nodeId: string
  networkId: number
  date?: string
}>()

const emit = defineEmits<{
  timeClick: [time: string]
}>()

const chartRef = ref<HTMLElement | null>(null)
const loading = ref(false)
const data = ref<TrendData[]>([])
let chart: echarts.ECharts | null = null

async function loadData() {
  if (!props.networkId || !props.nodeId || !props.date) return
  loading.value = true
  try {
    const { networkApi } = await import('../api')
    const res = await networkApi.getIntersectionHistory(props.networkId, props.nodeId, props.date)
    data.value = res.data || []
    await nextTick()
    renderChart()
  } catch (e) {
    console.error('加载趋势数据失败:', e)
    // 使用模拟数据
    data.value = generateMockData()
    await nextTick()
    renderChart()
  } finally {
    loading.value = false
  }
}

function generateMockData(): TrendData[] {
  const result: TrendData[] = []
  for (let h = 6; h < 22; h++) {
    for (let m = 0; m < 60; m += 10) {
      const hour = h + m / 60
      const peak = Math.exp(-((hour - 8.5) ** 2) / 2) * 0.7 + Math.exp(-((hour - 17.5) ** 2) / 2) * 0.6
      result.push({
        time: `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`,
        delay: 10 + peak * 40 + Math.random() * 5,
        queue: 5 + peak * 30 + Math.random() * 3,
        vcr: 0.3 + peak * 0.5 + Math.random() * 0.05,
      })
    }
  }
  return result
}

function renderChart() {
  if (!chartRef.value || data.value.length === 0) return
  if (chart) chart.dispose()

  chart = echarts.init(chartRef.value, 'dark')
  const times = data.value.map(d => d.time)

  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 20, top: 30, bottom: 30 },
    xAxis: {
      type: 'category',
      data: times,
      axisLabel: { fontSize: 10, color: '#64748b', interval: 5 },
      axisLine: { lineStyle: { color: '#1a2030' } },
    },
    yAxis: [
      {
        type: 'value', name: '延误(s)',
        axisLabel: { fontSize: 10, color: '#64748b' },
        splitLine: { lineStyle: { color: 'rgba(56,189,248,0.06)' } },
      },
      {
        type: 'value', name: 'V/C',
        max: 1.2,
        axisLabel: { fontSize: 10, color: '#64748b' },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: '延误',
        type: 'line',
        data: data.value.map(d => d.delay),
        smooth: true,
        lineStyle: { color: '#38bdf8', width: 2 },
        areaStyle: { color: 'rgba(56,189,248,0.1)' },
        itemStyle: { color: '#38bdf8' },
      },
      {
        name: '排队',
        type: 'line',
        data: data.value.map(d => d.queue),
        smooth: true,
        lineStyle: { color: '#f59e0b', width: 1.5 },
        itemStyle: { color: '#f59e0b' },
      },
      {
        name: 'V/C',
        type: 'line',
        yAxisIndex: 1,
        data: data.value.map(d => d.vcr),
        smooth: true,
        lineStyle: { color: '#22c55e', width: 1.5, type: 'dashed' },
        itemStyle: { color: '#22c55e' },
      },
    ],
  })

  chart.on('click', (params: any) => {
    if (params.name) emit('timeClick', params.name)
  })
}

watch(() => [props.nodeId, props.date], loadData)
onMounted(loadData)
</script>

<template>
  <div class="intersection-trend">
    <div class="trend-header">
      <span class="label">历史趋势</span>
      <span class="mono" style="font-size: 12px; color: var(--text-secondary)">{{ date || '未选择日期' }}</span>
    </div>
    <div v-if="loading" class="loading-state label">加载中...</div>
    <div v-else ref="chartRef" class="chart-container"></div>
  </div>
</template>

<style scoped>
.intersection-trend {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.trend-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-container {
  width: 100%;
  height: 200px;
  background: var(--bg-primary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.loading-state {
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
}
</style>
