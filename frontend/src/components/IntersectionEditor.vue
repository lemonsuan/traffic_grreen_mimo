<!--
  IntersectionEditor.vue — 交叉口配置弹框
  4个Tab: 渠化 | 相位 | 仿真 | 指标
-->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { intersectionApi } from '../api'

const props = defineProps<{
  nodeId: string
}>()

const emit = defineEmits<{
  close: []
}>()

const loading = ref(true)
const activeTab = ref('channel')
const detail = ref<any>(null)

const tabs = [
  { id: 'channel', label: '渠化' },
  { id: 'phase', label: '相位' },
  { id: 'sim', label: '仿真' },
  { id: 'metrics', label: '指标' },
]

async function loadDetail() {
  loading.value = true
  try {
    // 需要先获取intersection ID
    // 临时: 直接用nodeId查找
    const res = await intersectionApi.getFullDetail(parseInt(props.nodeId) || 1)
    detail.value = res.data
  } catch (e) {
    console.error('加载交叉口详情失败:', e)
    // 使用模拟数据
    detail.value = {
      node_id: props.nodeId,
      intersection_type: 'cross',
      signal: null,
      approaches: {},
    }
  } finally {
    loading.value = false
  }
}

function getApproachLabel(dir: string): string {
  const map: Record<string, string> = { north: '北进口', south: '南进口', east: '东进口', west: '西进口' }
  return map[dir] || dir
}

function getLaneTypeLabel(type: string): string {
  const map: Record<string, string> = {
    left_turn: '← 左转', through: '↑ 直行', right_turn: '→ 右转',
    left_through: '←↑ 左直', right_through: '↑→ 直右',
    bus: '🚌 公交', emergency: '🚨 应急'
  }
  return map[type] || type
}

onMounted(loadDetail)
</script>

<template>
  <div class="modal-overlay" @click.self="emit('close')">
    <div class="editor-modal">
      <!-- 顶栏 -->
      <div class="editor-header">
        <div class="header-left">
          <span class="header-title">交叉口 {{ detail?.node_id || nodeId }}</span>
          <span class="badge badge-cyan">{{ detail?.intersection_type || '...' }}</span>
        </div>
        <button class="btn-icon" @click="emit('close')">✕</button>
      </div>

      <!-- Tab栏 -->
      <div class="tabs">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          :class="['tab', { active: activeTab === tab.id }]"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
        </button>
      </div>

      <!-- 内容区 -->
      <div class="editor-body" v-if="!loading">
        <!-- Tab: 渠化 -->
        <div v-if="activeTab === 'channel'" class="tab-content">
          <div class="channel-grid">
            <div
              v-for="(approach, dir) in (detail?.approaches || {})"
              :key="dir"
              class="approach-card card"
            >
              <div class="approach-header">
                <span class="approach-dir">{{ getApproachLabel(dir) }}</span>
                <span class="approach-road mono">{{ approach.road_class }}</span>
              </div>
              <div class="lane-list">
                <div
                  v-for="lane in approach.lanes"
                  :key="lane.id"
                  class="lane-item"
                >
                  <span class="lane-type">{{ getLaneTypeLabel(lane.type) }}</span>
                  <span class="lane-display badge" :class="lane.signal_display === 'arrow' ? 'badge-amber' : 'badge-cyan'">
                    {{ lane.signal_display === 'arrow' ? '箭头灯' : '圆灯' }}
                  </span>
                </div>
                <div v-if="!approach.lanes || approach.lanes.length === 0" class="no-lanes">
                  暂无车道数据
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Tab: 相位 -->
        <div v-if="activeTab === 'phase'" class="tab-content">
          <div v-if="detail?.signal" class="phase-list">
            <div class="signal-info">
              <span class="label">周期</span>
              <span class="mono">{{ detail.signal.cycle_length }}s</span>
            </div>
            <div
              v-for="phase in detail.signal.phases"
              :key="phase.index"
              class="phase-item card"
            >
              <div class="phase-header">
                <span class="phase-index">相位 {{ phase.index + 1 }}</span>
                <span :class="['badge', phase.light_type === 'arrow' ? 'badge-amber' : 'badge-cyan']">
                  {{ phase.light_type === 'arrow' ? '箭头灯' : '圆灯' }}
                </span>
              </div>
              <div class="phase-timeline">
                <div class="phase-bar">
                  <div class="phase-green" :style="{ width: (phase.green / detail.signal.cycle_length * 100) + '%' }">
                    绿 {{ phase.green }}s
                  </div>
                  <div class="phase-yellow" :style="{ width: (phase.yellow / detail.signal.cycle_length * 100) + '%' }">
                    {{ phase.yellow }}s
                  </div>
                  <div class="phase-red" :style="{ width: (phase.all_red / detail.signal.cycle_length * 100) + '%' }">
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="empty-state">暂无信号配置</div>
        </div>

        <!-- Tab: 仿真 -->
        <div v-if="activeTab === 'sim'" class="tab-content">
          <div class="empty-state">
            <span class="label">单路口仿真</span>
            <p style="color: var(--text-secondary); margin-top: 8px; font-size: 13px;">
              配置各方向流量后启动微观仿真，验证信号配时效果
            </p>
            <button class="btn-primary" style="margin-top: 16px;">启动仿真</button>
          </div>
        </div>

        <!-- Tab: 指标 -->
        <div v-if="activeTab === 'metrics'" class="tab-content">
          <div class="empty-state">
            <span class="label">历史趋势</span>
            <p style="color: var(--text-secondary); margin-top: 8px; font-size: 13px;">
              选择日期查看该交叉口的延误、排队、饱和度历史趋势
            </p>
          </div>
        </div>
      </div>

      <!-- 加载中 -->
      <div v-else class="editor-body">
        <div class="empty-state">
          <span class="label">加载中...</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.editor-modal {
  width: 800px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.8);
  overflow: hidden;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--sp-3) var(--sp-4);
  border-bottom: 1px solid var(--border-default);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
}

.header-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.editor-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--sp-4);
}

.tab-content {
  min-height: 200px;
}

.channel-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--sp-3);
}

.approach-card {
  padding: var(--sp-3);
}

.approach-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--sp-2);
}

.approach-dir {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.approach-road {
  font-size: 11px;
  color: var(--text-secondary);
}

.lane-list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

.lane-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--sp-1) var(--sp-2);
  background: var(--bg-primary);
  border-radius: var(--radius-sm);
  font-size: 12px;
}

.no-lanes {
  font-size: 12px;
  color: var(--text-muted);
  text-align: center;
  padding: var(--sp-2);
}

.phase-list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.signal-info {
  display: flex;
  gap: var(--sp-2);
  align-items: center;
  font-size: 13px;
}

.phase-item {
  padding: var(--sp-3);
}

.phase-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--sp-2);
}

.phase-index {
  font-size: 13px;
  font-weight: 600;
}

.phase-bar {
  display: flex;
  height: 28px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  gap: 2px;
}

.phase-green {
  background: var(--accent-green);
  color: #0a0e14;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  min-width: 30px;
}

.phase-yellow {
  background: var(--accent-amber);
  color: #0a0e14;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 600;
  min-width: 20px;
}

.phase-red {
  background: var(--accent-red-dim);
  min-width: 10px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  text-align: center;
}
</style>
