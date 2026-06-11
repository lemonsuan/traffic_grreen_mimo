<template>
  <div class="analysis">
    <div class="analysis-header">
      <h1>数据分析</h1>
      <div class="header-actions">
        <button class="btn btn-secondary" @click="exportReport">导出报告</button>
      </div>
    </div>

    <div class="analysis-content">
      <div class="tabs">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          :class="['tab-btn', { active: currentTab === tab.id }]"
          @click="currentTab = tab.id"
        >
          {{ tab.name }}
        </button>
      </div>

      <!-- 性能指标 Tab -->
      <div v-if="currentTab === 'metrics'" class="tab-content">
        <div class="metrics-toolbar">
          <div class="toolbar-group">
            <label>优化层级</label>
            <select v-model="metricsLevel" @change="onLevelChange" class="form-select">
              <option value="intersection">单点优化</option>
              <option value="corridor">干线优化</option>
              <option value="network">区域优化</option>
            </select>
          </div>
          <div class="toolbar-group">
            <label>算法</label>
            <select v-model="metricsAlgorithm" class="form-select">
              <option v-for="algo in availableAlgorithms" :key="algo.id" :value="algo.id">
                {{ algo.name }}
              </option>
            </select>
          </div>
          <button class="btn btn-primary" @click="runAnalysis" :disabled="analyzing">
            {{ analyzing ? '分析中...' : '运行分析' }}
          </button>
        </div>

        <div class="metrics-dashboard">
          <div class="chart-card">
            <h3>延误时间分布</h3>
            <div ref="delayChart" class="chart"></div>
          </div>

          <div class="chart-card">
            <h3>排队长度变化</h3>
            <div ref="queueChart" class="chart"></div>
          </div>

          <div class="chart-card">
            <h3>吞吐量统计</h3>
            <div ref="throughputChart" class="chart"></div>
          </div>

          <div class="chart-card">
            <h3>饱和度分析</h3>
            <div ref="vcrChart" class="chart"></div>
          </div>
        </div>

        <div v-if="currentResult" class="metrics-summary">
          <h3>性能指标汇总</h3>
          <div class="summary-grid">
            <div class="summary-item">
              <span class="summary-label">平均延误</span>
              <span class="summary-value">{{ currentResult.performance.avg_delay.toFixed(1) }} 秒</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">平均排队长度</span>
              <span class="summary-value">{{ currentResult.performance.avg_queue_length.toFixed(1) }} 辆</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">最大排队长度</span>
              <span class="summary-value">{{ currentResult.performance.max_queue_length }} 辆</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">吞吐量</span>
              <span class="summary-value">{{ currentResult.performance.throughput }} 辆</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">平均停车次数</span>
              <span class="summary-value">{{ currentResult.performance.avg_stops.toFixed(1) }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">饱和度</span>
              <span class="summary-value">{{ currentResult.performance.vcr.toFixed(2) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 方案对比 Tab -->
      <div v-if="currentTab === 'comparison'" class="tab-content">
        <div class="comparison-toolbar">
          <div class="toolbar-group">
            <label>优化层级</label>
            <select v-model="compareLevel" @change="onCompareLevelChange" class="form-select">
              <option value="intersection">单点优化</option>
              <option value="corridor">干线优化</option>
              <option value="network">区域优化</option>
            </select>
          </div>
          <div class="toolbar-group">
            <label>选择对比算法 (可多选)</label>
            <div class="algo-checkbox-group">
              <label
                v-for="algo in compareAlgorithms"
                :key="algo.id"
                class="algo-checkbox"
              >
                <input
                  type="checkbox"
                  :value="algo.id"
                  v-model="selectedCompareAlgos"
                />
                {{ algo.name }}
              </label>
            </div>
          </div>
          <button class="btn btn-primary" @click="runComparison" :disabled="comparing">
            {{ comparing ? '对比中...' : '运行对比' }}
          </button>
        </div>

        <div v-if="comparisonResults.length > 0" class="comparison-section">
          <div class="comparison-table-wrapper">
            <h3>性能指标对比</h3>
            <table class="comparison-table">
              <thead>
                <tr>
                  <th>指标</th>
                  <th v-for="r in comparisonResults" :key="r.algorithm">
                    {{ algorithmLabel(r.algorithm) }}
                  </th>
                  <th>最优</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>平均延误 (秒)</td>
                  <td v-for="r in comparisonResults" :key="r.algorithm">
                    {{ r.performance.avg_delay.toFixed(1) }}
                  </td>
                  <td class="best">{{ bestAlgo('avg_delay') }}</td>
                </tr>
                <tr>
                  <td>平均排队 (辆)</td>
                  <td v-for="r in comparisonResults" :key="r.algorithm">
                    {{ r.performance.avg_queue_length.toFixed(1) }}
                  </td>
                  <td class="best">{{ bestAlgo('avg_queue_length') }}</td>
                </tr>
                <tr>
                  <td>吞吐量 (辆)</td>
                  <td v-for="r in comparisonResults" :key="r.algorithm">
                    {{ r.performance.throughput }}
                  </td>
                  <td class="best">{{ bestAlgo('throughput', true) }}</td>
                </tr>
                <tr>
                  <td>平均停车次数</td>
                  <td v-for="r in comparisonResults" :key="r.algorithm">
                    {{ r.performance.avg_stops.toFixed(1) }}
                  </td>
                  <td class="best">{{ bestAlgo('avg_stops') }}</td>
                </tr>
                <tr>
                  <td>饱和度</td>
                  <td v-for="r in comparisonResults" :key="r.algorithm">
                    {{ r.performance.vcr.toFixed(2) }}
                  </td>
                  <td class="best">{{ bestAlgo('vcr') }}</td>
                </tr>
                <tr>
                  <td>计算时间 (秒)</td>
                  <td v-for="r in comparisonResults" :key="r.algorithm">
                    {{ r.computation_time.toFixed(3) }}
                  </td>
                  <td class="best">{{ bestAlgo('computation_time') }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="comparison-charts">
            <div class="chart-card">
              <h3>延误对比</h3>
              <div ref="compareBarChart" class="chart"></div>
            </div>
            <div class="chart-card">
              <h3>雷达图对比</h3>
              <div ref="compareRadarChart" class="chart"></div>
            </div>
          </div>

          <!-- 收敛曲线 -->
          <div v-if="hasConvergence" class="chart-card full-width">
            <h3>收敛曲线</h3>
            <div ref="convergenceChart" class="chart"></div>
          </div>

          <!-- Pareto 前沿 -->
          <div v-if="hasPareto" class="chart-card full-width">
            <h3>Pareto 前沿 (NSGA-II)</h3>
            <div ref="paretoChart" class="chart"></div>
          </div>
        </div>

        <div v-else class="empty-state">
          <div class="empty-icon">📊</div>
          <div class="empty-text">选择算法并点击"运行对比"查看结果</div>
        </div>
      </div>

      <!-- 分析报告 Tab -->
      <div v-if="currentTab === 'reports'" class="tab-content">
        <div class="reports-list">
          <div v-for="report in reports" :key="report.id" class="report-card">
            <div class="report-icon">📊</div>
            <div class="report-info">
              <div class="report-title">{{ report.title }}</div>
              <div class="report-time">{{ report.time }}</div>
            </div>
            <button class="btn btn-secondary btn-sm">查看</button>
          </div>

          <div v-if="reports.length === 0" class="empty-state">
            暂无分析报告
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue'
import * as echarts from 'echarts'
import { optimizationApi } from '../api'

const currentTab = ref('metrics')

const tabs = [
  { id: 'metrics', name: '性能指标' },
  { id: 'comparison', name: '方案对比' },
  { id: 'reports', name: '分析报告' }
]

// --- 算法配置 ---
const algorithmMap: Record<string, { name: string; description: string }> = {
  webster: { name: 'Webster', description: '经典配时方法' },
  hcm: { name: 'HCM', description: '延误最小化' },
  actuated: { name: '感应控制', description: '实时响应车流' },
  adaptive: { name: '自适应', description: 'SCOOT/SCATS简化版' },
  maxband: { name: 'MAXBAND', description: '绿波带宽最大化' },
  passer: { name: 'PASSER-II', description: '多相位干线优化' },
  ga: { name: '遗传算法', description: '全局搜索元启发式' },
  pso: { name: '粒子群', description: '收敛快参数少' },
  transyt: { name: 'TRANSYT', description: '车队离散模型' },
  scoot: { name: 'SCOOT', description: '实时自适应控制' },
  nsga: { name: 'NSGA-II', description: '多目标进化算法' }
}

const algorithmsByLevel: Record<string, string[]> = {
  intersection: ['webster', 'hcm', 'actuated', 'adaptive'],
  corridor: ['maxband', 'passer', 'ga', 'pso'],
  network: ['transyt', 'scoot', 'nsga']
}

function algorithmLabel(id: string): string {
  return algorithmMap[id]?.name || id
}

// --- 性能指标 Tab ---
const metricsLevel = ref('intersection')
const metricsAlgorithm = ref('webster')
const analyzing = ref(false)
const currentResult = ref<any>(null)

const availableAlgorithms = computed(() => {
  return (algorithmsByLevel[metricsLevel.value] || []).map(id => ({
    id,
    name: algorithmMap[id]?.name || id
  }))
})

function onLevelChange() {
  metricsAlgorithm.value = algorithmsByLevel[metricsLevel.value]?.[0] || ''
  currentResult.value = null
}

async function runAnalysis() {
  analyzing.value = true
  try {
    let res
    const params = {}
    if (metricsLevel.value === 'intersection') {
      res = await optimizationApi.optimizeIntersection({
        node_id: 'demo_node',
        algorithm: metricsAlgorithm.value,
        params,
        traffic_data: {
          approaches: {
            north_through: { volume: 500 },
            south_through: { volume: 450 },
            east_through: { volume: 400 },
            west_through: { volume: 380 },
            north_left: { volume: 120 },
            south_left: { volume: 100 },
            east_left: { volume: 90 },
            west_left: { volume: 80 }
          }
        }
      })
    } else if (metricsLevel.value === 'corridor') {
      res = await optimizationApi.optimizeCorridor({
        node_ids: ['node_A', 'node_B', 'node_C', 'node_D'],
        algorithm: metricsAlgorithm.value,
        params
      })
    } else {
      res = await optimizationApi.optimizeNetwork({
        network_id: 1,
        algorithm: metricsAlgorithm.value,
        params
      })
    }
    currentResult.value = res.data
    await nextTick()
    renderMetricsCharts()
  } catch (e) {
    console.error('分析失败:', e)
  } finally {
    analyzing.value = false
  }
}

const delayChart = ref<HTMLElement | null>(null)
const queueChart = ref<HTMLElement | null>(null)
const throughputChart = ref<HTMLElement | null>(null)
const vcrChart = ref<HTMLElement | null>(null)

function renderMetricsCharts() {
  if (!currentResult.value) return
  const perf = currentResult.value.performance
  const timings = currentResult.value.signal_timings || {}
  const nodeIds = Object.keys(timings)

  if (delayChart.value) {
    const chart = echarts.init(delayChart.value)
    chart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: nodeIds.length ? nodeIds : ['整体'] },
      yAxis: { type: 'value', name: '延误 (秒)' },
      series: [{
        data: nodeIds.length
          ? nodeIds.map(() => perf.avg_delay)
          : [perf.avg_delay],
        type: 'bar',
        itemStyle: { color: '#1890ff' }
      }]
    })
  }

  if (queueChart.value) {
    const chart = echarts.init(queueChart.value)
    chart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: nodeIds.length ? nodeIds : ['整体'] },
      yAxis: { type: 'value', name: '排队 (辆)' },
      series: [{
        data: nodeIds.length
          ? nodeIds.map(() => perf.avg_queue_length)
          : [perf.avg_queue_length],
        type: 'line',
        smooth: true,
        areaStyle: {},
        itemStyle: { color: '#52c41a' }
      }]
    })
  }

  if (throughputChart.value) {
    const chart = echarts.init(throughputChart.value)
    chart.setOption({
      tooltip: {},
      series: [{
        type: 'gauge',
        progress: { show: true },
        detail: { valueAnimation: true, formatter: '{value}' },
        data: [{ value: perf.throughput, name: '吞吐量' }],
        axisLabel: { formatter: '{value}' }
      }]
    })
  }

  if (vcrChart.value) {
    const chart = echarts.init(vcrChart.value)
    chart.setOption({
      tooltip: {},
      radar: {
        indicator: nodeIds.length
          ? nodeIds.map(id => ({ name: id, max: 1 }))
          : [{ name: '饱和度', max: 1 }]
      },
      series: [{
        type: 'radar',
        data: [{
          value: nodeIds.length
            ? nodeIds.map(() => perf.vcr)
            : [perf.vcr],
          name: '饱和度 (v/c)',
          areaStyle: { opacity: 0.2 }
        }]
      }]
    })
  }
}

// --- 方案对比 Tab ---
const compareLevel = ref('intersection')
const selectedCompareAlgos = ref<string[]>(['webster', 'hcm'])
const comparing = ref(false)
const comparisonResults = ref<any[]>([])

const compareAlgorithms = computed(() => {
  return (algorithmsByLevel[compareLevel.value] || []).map(id => ({
    id,
    name: algorithmMap[id]?.name || id
  }))
})

function onCompareLevelChange() {
  selectedCompareAlgos.value = [algorithmsByLevel[compareLevel.value][0]]
  comparisonResults.value = []
}

const compareBarChart = ref<HTMLElement | null>(null)
const compareRadarChart = ref<HTMLElement | null>(null)
const convergenceChart = ref<HTMLElement | null>(null)
const paretoChart = ref<HTMLElement | null>(null)

const hasConvergence = computed(() =>
  comparisonResults.value.some(r => r.convergence && r.convergence.length > 0)
)
const hasPareto = computed(() =>
  comparisonResults.value.some(r => r.pareto_front && r.pareto_front.length > 0)
)

async function runComparison() {
  if (selectedCompareAlgos.value.length === 0) return
  comparing.value = true
  comparisonResults.value = []

  const trafficData: Record<string, any> = {
    intersection: {
      approaches: {
        north_through: { volume: 500 }, south_through: { volume: 450 },
        east_through: { volume: 400 }, west_through: { volume: 380 },
        north_left: { volume: 120 }, south_left: { volume: 100 },
        east_left: { volume: 90 }, west_left: { volume: 80 }
      }
    },
    corridor: {},
    network: {}
  }

  try {
    for (const algo of selectedCompareAlgos.value) {
      let res
      if (compareLevel.value === 'intersection') {
        res = await optimizationApi.optimizeIntersection({
          node_id: 'demo_node',
          algorithm: algo,
          traffic_data: trafficData.intersection
        })
      } else if (compareLevel.value === 'corridor') {
        res = await optimizationApi.optimizeCorridor({
          node_ids: ['node_A', 'node_B', 'node_C', 'node_D'],
          algorithm: algo
        })
      } else {
        res = await optimizationApi.optimizeNetwork({
          network_id: 1,
          algorithm: algo
        })
      }
      comparisonResults.value.push(res.data)
    }

    await nextTick()
    renderComparisonCharts()
  } catch (e) {
    console.error('对比失败:', e)
  } finally {
    comparing.value = false
  }
}

function bestAlgo(metric: string, higher = false): string {
  if (comparisonResults.value.length === 0) return '-'
  let best = comparisonResults.value[0]
  for (const r of comparisonResults.value) {
    const v = metric === 'computation_time' ? r[metric] : r.performance[metric]
    const bv = metric === 'computation_time' ? best[metric] : best.performance[metric]
    if (higher ? v > bv : v < bv) best = r
  }
  return algorithmLabel(best.algorithm)
}

function renderComparisonCharts() {
  const labels = comparisonResults.value.map(r => algorithmLabel(r.algorithm))

  if (compareBarChart.value) {
    const chart = echarts.init(compareBarChart.value)
    chart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['延误', '排队', '停车次数'] },
      xAxis: { type: 'category', data: labels },
      yAxis: { type: 'value' },
      series: [
        {
          name: '延误', type: 'bar', data: comparisonResults.value.map(r => r.performance.avg_delay),
          itemStyle: { color: '#1890ff' }
        },
        {
          name: '排队', type: 'bar', data: comparisonResults.value.map(r => r.performance.avg_queue_length),
          itemStyle: { color: '#52c41a' }
        },
        {
          name: '停车次数', type: 'bar', data: comparisonResults.value.map(r => r.performance.avg_stops),
          itemStyle: { color: '#faad14' }
        }
      ]
    })
  }

  if (compareRadarChart.value) {
    const chart = echarts.init(compareRadarChart.value)
    const maxDelay = Math.max(...comparisonResults.value.map(r => r.performance.avg_delay), 1)
    const maxQueue = Math.max(...comparisonResults.value.map(r => r.performance.avg_queue_length), 1)
    const maxStops = Math.max(...comparisonResults.value.map(r => r.performance.avg_stops), 1)
    const maxTP = Math.max(...comparisonResults.value.map(r => r.performance.throughput), 1)

    chart.setOption({
      tooltip: {},
      legend: { data: labels },
      radar: {
        indicator: [
          { name: '低延误', max: maxDelay },
          { name: '低排队', max: maxQueue },
          { name: '低停车', max: maxStops },
          { name: '高吞吐', max: maxTP },
          { name: '低饱和度', max: 1 }
        ]
      },
      series: [{
        type: 'radar',
        data: comparisonResults.value.map(r => ({
          value: [
            r.performance.avg_delay,
            r.performance.avg_queue_length,
            r.performance.avg_stops,
            r.performance.throughput,
            r.performance.vcr
          ],
          name: algorithmLabel(r.algorithm)
        }))
      }]
    })
  }

  // 收敛曲线
  if (convergenceChart.value && hasConvergence.value) {
    const chart = echarts.init(convergenceChart.value)
    const series = comparisonResults.value
      .filter(r => r.convergence && r.convergence.length > 0)
      .map(r => ({
        name: algorithmLabel(r.algorithm),
        type: 'line' as const,
        smooth: true,
        data: r.convergence
      }))

    const maxLen = Math.max(
      ...comparisonResults.value
        .filter(r => r.convergence)
        .map(r => r.convergence.length)
    )

    chart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: series.map(s => s.name) },
      xAxis: { type: 'category', data: Array.from({ length: maxLen }, (_, i) => i + 1), name: '迭代' },
      yAxis: { type: 'value', name: '目标值' },
      series
    })
  }

  // Pareto 前沿
  if (paretoChart.value && hasPareto.value) {
    const chart = echarts.init(paretoChart.value)
    const paretoData = comparisonResults.value.find(r => r.pareto_front && r.pareto_front.length > 0)
    if (paretoData) {
      const points = paretoData.pareto_front.map((p: any) => ({
        value: [p.objectives[0], p.objectives[1]],
        name: `延误:${p.objectives[0].toFixed(1)} 停车:${p.objectives[1].toFixed(2)}`
      }))

      chart.setOption({
        tooltip: {
          formatter: (params: any) => params.name
        },
        xAxis: { type: 'value', name: '平均延误 (秒)' },
        yAxis: { type: 'value', name: '平均停车次数' },
        series: [{
          type: 'scatter',
          data: points,
          symbolSize: 10,
          itemStyle: { color: '#722ed1' }
        }]
      })
    }
  }
}

// --- 报告 Tab ---
const reports = ref([
  { id: 1, title: '干线仿真报告 #001', time: '2024-01-15 14:30' },
  { id: 2, title: 'Webster优化报告', time: '2024-01-15 13:45' },
  { id: 3, title: '区域路网分析报告', time: '2024-01-14 16:20' }
])

function exportReport() {
  alert('导出报告功能待实现')
}

onMounted(() => {
  // 初始化默认图表
})
</script>

<style scoped>
.analysis {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.analysis-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: white;
  border-bottom: 1px solid #e8e8e8;
}

.analysis-header h1 {
  margin: 0;
  font-size: 20px;
}

.analysis-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.tabs {
  display: flex;
  background: white;
  border-bottom: 1px solid #e8e8e8;
  padding: 0 24px;
}

.tab-btn {
  padding: 12px 24px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 14px;
  color: #666;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.tab-btn:hover {
  color: #1890ff;
}

.tab-btn.active {
  color: #1890ff;
  border-bottom-color: #1890ff;
}

.tab-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

/* Toolbar */
.metrics-toolbar,
.comparison-toolbar {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  margin-bottom: 24px;
  background: white;
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.toolbar-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.toolbar-group label {
  font-size: 12px;
  color: #666;
}

.form-select {
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 14px;
  min-width: 140px;
}

.algo-checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.algo-checkbox {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  cursor: pointer;
  padding: 4px 8px;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  transition: all 0.2s;
}

.algo-checkbox:has(input:checked) {
  border-color: #1890ff;
  background: #e6f7ff;
}

/* Metrics */
.metrics-dashboard {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}

.chart-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.chart-card.full-width {
  grid-column: 1 / -1;
}

.chart-card h3 {
  margin: 0 0 16px 0;
  font-size: 16px;
}

.chart {
  width: 100%;
  height: 300px;
}

.metrics-summary {
  margin-top: 24px;
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.metrics-summary h3 {
  margin: 0 0 16px 0;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-label {
  font-size: 12px;
  color: #666;
}

.summary-value {
  font-size: 20px;
  font-weight: bold;
  color: #1890ff;
}

/* Comparison */
.comparison-section {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.comparison-table-wrapper {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow-x: auto;
}

.comparison-table-wrapper h3 {
  margin: 0 0 16px 0;
}

.comparison-table {
  width: 100%;
  border-collapse: collapse;
}

.comparison-table th,
.comparison-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #e8e8e8;
}

.comparison-table th {
  background: #fafafa;
  font-weight: bold;
}

.comparison-table .best {
  color: #52c41a;
  font-weight: bold;
}

.comparison-charts {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}

/* Reports */
.reports-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.report-card {
  display: flex;
  align-items: center;
  gap: 16px;
  background: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.report-icon {
  font-size: 32px;
}

.report-info {
  flex: 1;
}

.report-title {
  font-size: 14px;
  font-weight: bold;
}

.report-time {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}

.empty-state {
  text-align: center;
  color: #999;
  padding: 48px;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-text {
  font-size: 16px;
  color: #666;
}

.btn {
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  border: none;
}

.btn-primary {
  background: #1890ff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

.btn-primary:disabled {
  background: #d9d9d9;
  cursor: not-allowed;
}

.btn-secondary {
  background: white;
  border: 1px solid #d9d9d9;
}

.btn-sm {
  padding: 4px 12px;
  font-size: 12px;
}
</style>
