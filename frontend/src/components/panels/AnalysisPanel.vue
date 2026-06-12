<!--
  AnalysisPanel.vue — 数据分析浮层
  功能: 指标查看、报告生成、CSV导出
-->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { analysisApi, networkApi } from '../../api'

const props = defineProps<{ networkId: number }>()
const emit = defineEmits<{ close: [] }>()

const reports = ref<Array<{ id: number; title: string; time: string }>>([])
const loading = ref(false)

async function loadReports() {
  loading.value = true
  try {
    const res = await analysisApi.getReports({ network: props.networkId })
    reports.value = (res.data.results || res.data || []).map((r: any) => ({
      id: r.id,
      title: r.title || `报告 #${r.id}`,
      time: r.created_at ? new Date(r.created_at).toLocaleString('zh-CN') : '',
    }))
  } catch (e) {
    console.error('加载报告失败:', e)
  } finally {
    loading.value = false
  }
}

async function generateReport() {
  try {
    await analysisApi.generateReport(props.networkId, 'simulation')
    await loadReports()
  } catch (e: any) {
    alert('生成失败: ' + e.message)
  }
}

async function exportCSV() {
  try {
    const res = await analysisApi.exportReport(props.networkId, 'simulation', 'csv')
    const blob = new Blob([res.data], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${props.networkId}.csv`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e: any) {
    alert('导出失败: ' + e.message)
  }
}

onMounted(loadReports)
</script>

<template>
  <div class="panel analysis-panel">
    <div class="panel-header">
      <span class="panel-title label">数据分析</span>
      <button class="btn-icon" @click="emit('close')">✕</button>
    </div>
    <div class="panel-body">
      <div class="actions-row">
        <button class="btn-secondary" @click="generateReport">生成报告</button>
        <button class="btn-secondary" @click="exportCSV">导出 CSV</button>
      </div>

      <div class="divider"></div>

      <div class="reports-section">
        <span class="label">报告列表</span>
        <div v-if="loading" class="loading-text label">加载中...</div>
        <div v-else-if="reports.length === 0" class="empty-text">暂无报告</div>
        <div v-else class="reports-list">
          <div v-for="report in reports" :key="report.id" class="report-item card">
            <span class="report-title">{{ report.title }}</span>
            <span class="report-time" style="font-size:11px;color:var(--text-muted)">{{ report.time }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.analysis-panel { width: 300px; }
.panel-header { display: flex; justify-content: space-between; align-items: center; padding: var(--sp-3) var(--sp-4); border-bottom: 1px solid var(--border-default); }
.panel-title { color: var(--accent-cyan); }
.panel-body { padding: var(--sp-4); display: flex; flex-direction: column; gap: var(--sp-3); }
.actions-row { display: flex; gap: var(--sp-2); }
.actions-row button { flex: 1; }
.reports-section { display: flex; flex-direction: column; gap: var(--sp-2); }
.reports-list { display: flex; flex-direction: column; gap: var(--sp-2); max-height: 300px; overflow-y: auto; }
.report-item { padding: var(--sp-2) var(--sp-3); display: flex; flex-direction: column; gap: 2px; }
.report-title { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.loading-text, .empty-text { font-size: 12px; color: var(--text-muted); text-align: center; padding: var(--sp-4); }
</style>
