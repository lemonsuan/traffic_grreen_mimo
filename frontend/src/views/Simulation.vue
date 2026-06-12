<template>
  <div class="simulation">
    <div class="sim-header">
      <h1>仿真控制台</h1>
      <div class="header-controls">
        <div class="view-buttons" v-if="sceneReady">
          <button class="btn btn-sm" @click="sceneManager?.setTopView()">俯视</button>
          <button class="btn btn-sm" @click="sceneManager?.setPerspectiveView()">透视</button>
          <button class="btn btn-sm" @click="sceneManager?.setSideView()">侧视</button>
        </div>
        <button class="btn btn-primary" @click="handleStart" :disabled="simulationStore.isRunning || !config.networkId">
          ▶️ 启动
        </button>
        <button class="btn btn-secondary" @click="handlePause" :disabled="simulationStore.status !== 'running'">
          ⏸️ 暂停
        </button>
        <button class="btn btn-secondary" @click="handleStop" :disabled="simulationStore.status === 'idle'">
          ⏹️ 停止
        </button>
        <button class="btn btn-secondary" @click="handleReset">
          🔄 重置
        </button>
      </div>
    </div>

    <div class="sim-content">
      <div class="sim-sidebar">
        <div class="config-section">
          <h3>仿真配置</h3>
          <div class="form-group">
            <label>路网</label>
            <select v-model="config.networkId" class="form-input">
              <option value="">选择路网</option>
              <option v-for="n in networks" :key="n.id" :value="n.id">{{ n.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>仿真时长 (秒)</label>
            <input v-model.number="config.duration" type="number" class="form-input" />
          </div>
          <div class="form-group">
            <label>步长 (秒)</label>
            <input v-model.number="config.stepSize" type="number" class="form-input" />
          </div>
          <div class="form-group">
            <label>速度倍率</label>
            <div class="speed-buttons">
              <button
                v-for="speed in [0.5, 1, 2, 5, 10]"
                :key="speed"
                :class="['speed-btn', { active: speedMultiplier === speed }]"
                @click="speedMultiplier = speed"
              >
                {{ speed }}x
              </button>
            </div>
          </div>
        </div>

        <div class="config-section">
          <h3>实时指标</h3>
          <div class="metrics-grid">
            <div class="metric-item">
              <div class="metric-value">{{ simulationStore.metrics.avg_delay.toFixed(1) }}</div>
              <div class="metric-label">平均延误 (秒)</div>
            </div>
            <div class="metric-item">
              <div class="metric-value">{{ simulationStore.metrics.avg_queue_length.toFixed(1) }}</div>
              <div class="metric-label">平均排队 (辆)</div>
            </div>
            <div class="metric-item">
              <div class="metric-value">{{ simulationStore.metrics.throughput }}</div>
              <div class="metric-label">吞吐量 (辆)</div>
            </div>
            <div class="metric-item">
              <div class="metric-value">{{ simulationStore.vehicleCount }}</div>
              <div class="metric-label">总车辆数</div>
            </div>
            <div class="metric-item">
              <div class="metric-value">{{ simulationStore.metrics.vcr.toFixed(2) }}</div>
              <div class="metric-label">饱和度 V/C</div>
            </div>
          </div>
        </div>
      </div>

      <div class="sim-main">
        <div class="canvas-container" ref="canvasContainer">
          <div v-if="!sceneReady" class="canvas-placeholder">
            <div class="placeholder-icon">🚗</div>
            <div class="placeholder-text">3D仿真视图</div>
            <div class="placeholder-subtext">选择路网后启动仿真</div>
          </div>
        </div>

        <div class="sim-footer">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: simulationStore.progress + '%' }"></div>
          </div>
          <div class="time-display">
            {{ formatTime(simulationStore.currentTime) }} / {{ formatTime(simulationStore.duration) }}
          </div>
          <div class="status-badge" :class="simulationStore.status">
            {{ statusText }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useSimulationStore } from '../stores/simulation'
import { networkApi } from '../api'
import { SceneManager } from '../three/SceneManager'
import { RoadRenderer } from '../three/RoadRenderer'
import { VehicleRenderer, VehicleState } from '../three/VehicleRenderer'
import { SignalRenderer, SignalState } from '../three/SignalRenderer'

const simulationStore = useSimulationStore()

const canvasContainer = ref<HTMLElement | null>(null)
const sceneReady = ref(false)
const speedMultiplier = ref(1)

const networks = ref<Array<{ id: number; name: string; nodes: any[]; edges: any[] }>>([])

const config = ref({
  networkId: '',
  duration: 3600,
  stepSize: 1
})

const statusText = computed(() => {
  const map: Record<string, string> = {
    idle: '空闲',
    running: '运行中',
    paused: '已暂停',
    completed: '已完成'
  }
  return map[simulationStore.status] || simulationStore.status
})

let sceneManager: SceneManager | null = null
let roadRenderer: RoadRenderer | null = null
let vehicleRenderer: VehicleRenderer | null = null
let signalRenderer: SignalRenderer | null = null
const nodePositionMap = new Map<string, { x: number; y: number }>()
const edgeDataMap = new Map<string, { from: string; to: string; length: number }>()

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

function initScene() {
  if (!canvasContainer.value) return

  sceneManager = new SceneManager(canvasContainer.value)
  roadRenderer = new RoadRenderer(sceneManager.getScene())
  vehicleRenderer = new VehicleRenderer(sceneManager.getScene())
  signalRenderer = new SignalRenderer(sceneManager.getScene())

  sceneManager.startAnimationLoop()
  sceneReady.value = true
}

function loadNetworkToScene(networkId: number) {
  const network = networks.value.find(n => n.id === networkId)
  if (!network || !roadRenderer || !signalRenderer) return

  roadRenderer.clear()
  signalRenderer.clear()
  vehicleRenderer?.clear()
  nodePositionMap.clear()
  edgeDataMap.clear()

  const nodes = network.nodes || []
  const edges = network.edges || []

  // 用OSM投影坐标(x,y)
  nodes.forEach((node: any) => {
    const x = node.x || 0
    const y = node.y || 0
    nodePositionMap.set(node.node_id, { x, y })
    roadRenderer!.addNode({
      id: node.node_id, x, y,
      type: node.node_type === 'roundabout' ? 'roundabout' : 'intersection'
    })
  })

  edges.forEach((edge: any) => {
    const fromPos = nodePositionMap.get(edge.from_node)
    const toPos = nodePositionMap.get(edge.to_node)
    if (fromPos && toPos) {
      edgeDataMap.set(edge.edge_id, {
        from: edge.from_node,
        to: edge.to_node,
        length: edge.length || 300
      })
      roadRenderer!.addEdge(
        { id: edge.edge_id, from: edge.from_node, to: edge.to_node, lanes: edge.lanes_count || 2, width: (edge.lanes_count || 2) * 3.5 },
        { id: edge.from_node, x: fromPos.x, y: fromPos.y, type: 'intersection' },
        { id: edge.to_node, x: toPos.x, y: toPos.y, type: 'intersection' }
      )
    }
  })

  const signalsData = (network as any).signals || []
  signalsData.forEach((signal: any) => {
    const pos = nodePositionMap.get(signal.node_id)
    if (pos && signal.phases) {
      signalRenderer!.addSignal({
        nodeId: signal.node_id,
        x: pos.x,
        y: pos.y,
        currentPhase: 0,
        phases: signal.phases.map((p: any, i: number) => ({
          index: i,
          green: p.green || p.green_time || 30,
          yellow: p.yellow || p.yellow_time || 3,
          allRed: p.all_red || p.all_red_time || 1
        }))
      })
    }
  })

  if (sceneManager) {
    const xs = nodes.map((n: any) => n.x || 0)
    const ys = nodes.map((n: any) => n.y || 0)
    const cx = (Math.min(...xs) + Math.max(...xs)) / 2
    const cy = (Math.min(...ys) + Math.max(...ys)) / 2
    const range = Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys), 500)
    sceneManager.setCameraPosition(cx + range * 0.5, range * 0.8, cy + range * 0.5)
  }
}

function mapVehicleToState(v: any): VehicleState {
  const fromId = v.from_node || ''
  const toId = v.to_node || ''
  const fromPos = nodePositionMap.get(fromId)
  const toPos = nodePositionMap.get(toId)
  const edgeLen = v.edge_length || 300

  let x = 0, y = 0, angle = 0

  if (fromPos && toPos) {
    const progress = Math.min(Math.max((v.position || 0) / edgeLen, 0), 1)
    x = fromPos.x + (toPos.x - fromPos.x) * progress
    y = fromPos.y + (toPos.y - fromPos.y) * progress
    angle = Math.atan2(toPos.x - fromPos.x, toPos.y - fromPos.y)
  }

  return {
    id: v.id,
    x, y, z: 0,
    rotation: angle,
    speed: v.speed || 0,
    type: 'car'
  }
}

watch(() => simulationStore.vehicles, (newVehicles) => {
  if (!vehicleRenderer) return
  const states = newVehicles.map(mapVehicleToState)
  vehicleRenderer.updateVehicles(states)
}, { deep: true })

watch(() => simulationStore.signals, (newSignals) => {
  if (!signalRenderer) return
  Object.entries(newSignals).forEach(([nodeId, sigState]: [string, any]) => {
    const pos = nodePositionMap.get(nodeId)
    if (pos) {
      signalRenderer!.updateSignal({
        nodeId,
        x: pos.x,
        y: pos.y,
        currentPhase: sigState.current_phase || 0,
        phases: []
      })
    }
  })
}, { deep: true })

async function handleStart() {
  if (!config.value.networkId) return
  loadNetworkToScene(Number(config.value.networkId))
  await simulationStore.startSimulation({
    network_id: Number(config.value.networkId),
    duration: config.value.duration,
    step_size: config.value.stepSize,
    speed_multiplier: speedMultiplier.value
  })
}

async function handlePause() {
  await simulationStore.pauseSimulation()
}

async function handleStop() {
  await simulationStore.stopSimulation()
}

function handleReset() {
  simulationStore.reset()
  vehicleRenderer?.clear()
}

function handleResize() {
  if (!canvasContainer.value || !sceneManager) return
  sceneManager.resize(canvasContainer.value.clientWidth, canvasContainer.value.clientHeight)
}

onMounted(async () => {
  initScene()
  window.addEventListener('resize', handleResize)

  try {
    const res = await networkApi.list()
    const list = res.data.results || res.data || []
    const detailed = await Promise.all(
      list.map(async (n: any) => {
        try {
          const detail = await networkApi.get(n.id)
          return { id: n.id, name: n.name, nodes: detail.data.nodes || [], edges: detail.data.edges || [], signals: detail.data.signals || [] }
        } catch {
          return { id: n.id, name: n.name, nodes: [], edges: [], signals: [] }
        }
      })
    )
    networks.value = detailed
  } catch (e) {
    console.error('获取路网列表失败:', e)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  sceneManager?.dispose()
})
</script>

<style scoped>
.simulation {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.sim-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: white;
  border-bottom: 1px solid #e8e8e8;
}

.sim-header h1 {
  margin: 0;
  font-size: 20px;
}

.header-controls {
  display: flex;
  gap: 12px;
  align-items: center;
}

.view-buttons {
  display: flex;
  gap: 4px;
  margin-right: 8px;
}

.btn-sm {
  padding: 4px 10px;
  font-size: 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background: white;
  cursor: pointer;
}

.btn-sm:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.sim-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.sim-sidebar {
  width: 300px;
  background: white;
  border-right: 1px solid #e8e8e8;
  padding: 16px;
  overflow-y: auto;
}

.config-section {
  margin-bottom: 24px;
}

.config-section h3 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #333;
}

.form-group {
  margin-bottom: 12px;
}

.form-group label {
  display: block;
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.form-input {
  width: 100%;
  padding: 8px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 14px;
}

.speed-buttons {
  display: flex;
  gap: 8px;
}

.speed-btn {
  flex: 1;
  padding: 8px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  font-size: 12px;
}

.speed-btn.active {
  background: #1890ff;
  border-color: #1890ff;
  color: white;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.metric-item {
  background: #f5f5f5;
  padding: 12px;
  border-radius: 8px;
  text-align: center;
}

.metric-value {
  font-size: 24px;
  font-weight: bold;
  color: #1890ff;
}

.metric-label {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}

.sim-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.canvas-container {
  flex: 1;
  background: #f0f0f0;
  position: relative;
  overflow: hidden;
}

.canvas-container canvas,
.canvas-container :deep(canvas) {
  width: 100% !important;
  height: 100% !important;
  display: block;
}

.canvas-placeholder {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  z-index: 1;
}

.placeholder-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.placeholder-text {
  font-size: 20px;
  color: #666;
}

.placeholder-subtext {
  font-size: 14px;
  color: #999;
  margin-top: 8px;
}

.sim-footer {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  background: white;
  border-top: 1px solid #e8e8e8;
}

.progress-bar {
  flex: 1;
  height: 8px;
  background: #e8e8e8;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #1890ff;
  transition: width 0.3s;
}

.time-display {
  font-size: 14px;
  color: #333;
  font-family: monospace;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
}

.status-badge.idle { background: #f0f0f0; color: #666; }
.status-badge.running { background: #e6f7ff; color: #1890ff; }
.status-badge.paused { background: #fff7e6; color: #faad14; }
.status-badge.completed { background: #f6ffed; color: #52c41a; }

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

.btn-secondary:hover:not(:disabled) {
  border-color: #1890ff;
  color: #1890ff;
}
</style>
