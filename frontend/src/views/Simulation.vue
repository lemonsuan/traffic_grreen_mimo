<template>
  <div class="simulation">
    <div class="sim-header">
      <h1>仿真控制台</h1>
      <div class="header-controls">
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
          <canvas ref="threeCanvas"></canvas>
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
import * as THREE from 'three'

const simulationStore = useSimulationStore()

const canvasContainer = ref<HTMLElement | null>(null)
const threeCanvas = ref<HTMLCanvasElement | null>(null)
const sceneReady = ref(false)
const speedMultiplier = ref(1)

const networks = ref<Array<{ id: number; name: string }>>([])

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

let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let renderer: THREE.WebGLRenderer | null = null
let animFrameId: number | null = null
const vehicleMeshes: Map<string, THREE.Mesh> = new Map()

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

function initThreeScene() {
  if (!threeCanvas.value || !canvasContainer.value) return

  const container = canvasContainer.value
  const width = container.clientWidth
  const height = container.clientHeight

  scene = new THREE.Scene()
  scene.background = new THREE.Color(0xf0f2f5)

  camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 10000)
  camera.position.set(0, 500, 500)
  camera.lookAt(0, 0, 0)

  renderer = new THREE.WebGLRenderer({ canvas: threeCanvas.value, antialias: true })
  renderer.setSize(width, height)
  renderer.setPixelRatio(window.devicePixelRatio)

  const ambientLight = new THREE.AmbientLight(0xffffff, 0.6)
  scene.add(ambientLight)
  const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8)
  directionalLight.position.set(500, 1000, 500)
  scene.add(directionalLight)

  const groundGeo = new THREE.PlaneGeometry(2000, 2000)
  const groundMat = new THREE.MeshStandardMaterial({ color: 0xe8e8e8 })
  const ground = new THREE.Mesh(groundGeo, groundMat)
  ground.rotation.x = -Math.PI / 2
  scene.add(ground)

  const gridHelper = new THREE.GridHelper(2000, 40, 0xcccccc, 0xdddddd)
  scene.add(gridHelper)

  sceneReady.value = true
  animate()
}

function animate() {
  animFrameId = requestAnimationFrame(animate)
  if (renderer && scene && camera) {
    renderer.render(scene, camera)
  }
}

function addRoadNode(x: number, z: number, nodeId: string) {
  if (!scene) return
  const geo = new THREE.CylinderGeometry(8, 8, 4, 16)
  const mat = new THREE.MeshStandardMaterial({ color: 0x1890ff })
  const mesh = new THREE.Mesh(geo, mat)
  mesh.position.set(x, 2, z)
  mesh.name = `node_${nodeId}`
  scene.add(mesh)
}

function addRoadEdge(x1: number, z1: number, x2: number, z2: number) {
  if (!scene) return
  const dx = x2 - x1
  const dz = z2 - z1
  const length = Math.sqrt(dx * dx + dz * dz)
  const angle = Math.atan2(dx, dz)

  const geo = new THREE.BoxGeometry(12, 0.5, length)
  const mat = new THREE.MeshStandardMaterial({ color: 0x333333 })
  const mesh = new THREE.Mesh(geo, mat)
  mesh.position.set((x1 + x2) / 2, 0.25, (z1 + z2) / 2)
  mesh.rotation.y = angle
  scene.add(mesh)
}

function updateVehicles(vehicles: any[]) {
  if (!scene) return

  const existingIds = new Set(vehicles.map((v: any) => v.id))

  for (const [id, mesh] of vehicleMeshes) {
    if (!existingIds.has(id)) {
      scene.remove(mesh)
      vehicleMeshes.delete(id)
    }
  }

  for (const v of vehicles) {
    let mesh = vehicleMeshes.get(v.id)
    if (!mesh) {
      const geo = new THREE.BoxGeometry(6, 4, 10)
      const mat = new THREE.MeshStandardMaterial({ color: 0x52c41a })
      mesh = new THREE.Mesh(geo, mat)
      scene.add(mesh)
      vehicleMeshes.set(v.id, mesh)
    }
    const x = (v.position || 0) * 0.5 - 500
    const z = Math.random() * 200 - 100
    mesh.position.set(x, 2, z)
  }
}

watch(() => simulationStore.vehicles, (newVehicles) => {
  updateVehicles(newVehicles)
}, { deep: true })

async function handleStart() {
  if (!config.value.networkId) return
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
  vehicleMeshes.forEach((mesh) => {
    scene?.remove(mesh)
  })
  vehicleMeshes.clear()
}

function handleResize() {
  if (!canvasContainer.value || !camera || !renderer) return
  const w = canvasContainer.value.clientWidth
  const h = canvasContainer.value.clientHeight
  camera.aspect = w / h
  camera.updateProjectionMatrix()
  renderer.setSize(w, h)
}

onMounted(async () => {
  initThreeScene()
  window.addEventListener('resize', handleResize)

  try {
    const res = await networkApi.list()
    networks.value = (res.data.results || res.data || []).map((n: any) => ({
      id: n.id,
      name: n.name
    }))
  } catch (e) {
    console.error('获取路网列表失败:', e)
  }
})

onUnmounted(() => {
  if (animFrameId) cancelAnimationFrame(animFrameId)
  window.removeEventListener('resize', handleResize)
  renderer?.dispose()
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

.canvas-container canvas {
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
