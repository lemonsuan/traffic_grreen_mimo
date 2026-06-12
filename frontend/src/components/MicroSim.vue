<!--
  MicroSim.vue — 单路口微观仿真 (Three.js 3D)
  功能: 3D渲染交叉口, 车辆排队/放行动画, 流量参数可调
-->
<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'

interface SimVehicle {
  id: string
  pos: number
  speed: number
  stopped: boolean
  mesh?: THREE.Mesh
}

const props = defineProps<{
  nodeId: string
  initialFlows?: Record<string, number>
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const running = ref(false)
const simTime = ref(0)
const totalQueue = ref(0)
const flows = ref<Record<string, number>>(
  props.initialFlows || { north: 500, south: 450, east: 400, west: 380 }
)

let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let renderer: THREE.WebGLRenderer | null = null
let controls: OrbitControls | null = null
let animId: number | null = null
let simTimer: number | null = null

const vehicles = ref<Record<string, SimVehicle[]>>({
  north: [], south: [], east: [], west: [],
})
let vehicleIdCounter = 0
const phaseIndex = ref(0)
const phaseTimer = ref(0)
const phases = [
  { green: 35, yellow: 3, all_red: 1, greenDirs: ['north', 'south'] },
  { green: 30, yellow: 3, all_red: 1, greenDirs: ['east', 'west'] },
]

const ROAD_WIDTH = 14
const APPROACH_LENGTH = 60

// 车辆几何和材质
const vehicleGeo = new THREE.BoxGeometry(1.5, 1, 3)
const vehicleMats = {
  moving: new THREE.MeshStandardMaterial({ color: 0x22c55e, roughness: 0.5 }),
  stopped: new THREE.MeshStandardMaterial({ color: 0xef4444, roughness: 0.5 }),
  slow: new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.5 }),
}

// 信号灯球体引用
const signalMeshes: Record<string, { red: THREE.Mesh; yellow: THREE.Mesh; green: THREE.Mesh }> = {}

function initScene() {
  if (!canvasRef.value) return

  const w = canvasRef.value.clientWidth
  const h = canvasRef.value.clientHeight

  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x0a0e14)

  camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 500)
  camera.position.set(0, 80, 60)
  camera.lookAt(0, 0, 0)

  renderer = new THREE.WebGLRenderer({ canvas: canvasRef.value, antialias: true })
  renderer.setSize(w, h)
  renderer.setPixelRatio(window.devicePixelRatio)
  renderer.shadowMap.enabled = true

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.1
  controls.maxPolarAngle = Math.PI / 2.2

  // 光源
  scene.add(new THREE.AmbientLight(0xffffff, 0.5))
  const dirLight = new THREE.DirectionalLight(0xffffff, 0.8)
  dirLight.position.set(30, 50, 30)
  dirLight.castShadow = true
  scene.add(dirLight)

  // 地面
  const groundGeo = new THREE.PlaneGeometry(200, 200)
  const groundMat = new THREE.MeshStandardMaterial({ color: 0x111820, roughness: 0.9 })
  const ground = new THREE.Mesh(groundGeo, groundMat)
  ground.rotation.x = -Math.PI / 2
  ground.receiveShadow = true
  scene.add(ground)

  // 道路
  drawRoads()

  // 信号灯
  drawSignals()

  animate()
}

function drawRoads() {
  if (!scene) return

  const roadMat = new THREE.MeshStandardMaterial({ color: 0x1a2030, roughness: 0.9 })
  const stopMat = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 0.2 })
  const lineMat = new THREE.LineBasicMaterial({ color: 0x475569 })

  // NS道路
  const nsGeo = new THREE.PlaneGeometry(ROAD_WIDTH * 2, 200)
  const nsRoad = new THREE.Mesh(nsGeo, roadMat)
  nsRoad.rotation.x = -Math.PI / 2
  nsRoad.position.y = 0.01
  nsRoad.receiveShadow = true
  scene.add(nsRoad)

  // EW道路
  const ewGeo = new THREE.PlaneGeometry(200, ROAD_WIDTH * 2)
  const ewRoad = new THREE.Mesh(ewGeo, roadMat)
  ewRoad.rotation.x = -Math.PI / 2
  ewRoad.position.y = 0.01
  ewRoad.receiveShadow = true
  scene.add(ewRoad)

  // 停止线
  const stopGeo = new THREE.BoxGeometry(ROAD_WIDTH * 2 + 1, 0.05, 0.5)
  const offsets = [
    { x: 0, z: -ROAD_WIDTH, r: 0 },     // 北
    { x: 0, z: ROAD_WIDTH, r: 0 },      // 南
    { x: ROAD_WIDTH, z: 0, r: Math.PI / 2 },  // 东
    { x: -ROAD_WIDTH, z: 0, r: Math.PI / 2 }, // 西
  ]
  for (const off of offsets) {
    const line = new THREE.Mesh(stopGeo, stopMat)
    line.position.set(off.x, 0.1, off.z)
    line.rotation.y = off.r
    scene.add(line)
  }

  // 中心线
  const nsPoints = [new THREE.Vector3(0, 0.08, -100), new THREE.Vector3(0, 0.08, 100)]
  const ewPoints = [new THREE.Vector3(-100, 0.08, 0), new THREE.Vector3(100, 0.08, 0)]
  scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(nsPoints), lineMat))
  scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(ewPoints), lineMat))
}

function drawSignals() {
  if (!scene) return

  const positions = [
    { dir: 'north', x: -ROAD_WIDTH - 3, z: -ROAD_WIDTH - 3 },
    { dir: 'south', x: ROAD_WIDTH + 3, z: ROAD_WIDTH + 3 },
    { dir: 'east', x: ROAD_WIDTH + 3, z: -ROAD_WIDTH - 3 },
    { dir: 'west', x: -ROAD_WIDTH - 3, z: ROAD_WIDTH + 3 },
  ]

  for (const p of positions) {
    // 灯柱
    const poleGeo = new THREE.CylinderGeometry(0.15, 0.15, 5, 8)
    const poleMat = new THREE.MeshStandardMaterial({ color: 0x666666 })
    const pole = new THREE.Mesh(poleGeo, poleMat)
    pole.position.set(p.x, 2.5, p.z)
    scene.add(pole)

    // 灯箱
    const boxGeo = new THREE.BoxGeometry(1, 3, 0.6)
    const boxMat = new THREE.MeshStandardMaterial({ color: 0x333333 })
    const box = new THREE.Mesh(boxGeo, boxMat)
    box.position.set(p.x, 5.5, p.z)
    scene.add(box)

    // 三色灯
    const createBulb = (color: number, y: number) => {
      const geo = new THREE.SphereGeometry(0.3, 16, 16)
      const mat = new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0 })
      const mesh = new THREE.Mesh(geo, mat)
      mesh.position.set(p.x, y, p.z + 0.4)
      scene!.add(mesh)
      return mesh
    }

    signalMeshes[p.dir] = {
      red: createBulb(0xff0000, 6.5),
      yellow: createBulb(0xffd700, 5.5),
      green: createBulb(0x00ff00, 4.5),
    }
  }
}

function updateSignalLights() {
  const currentPhase = phases[phaseIndex.value]
  for (const dir of ['north', 'south', 'east', 'west']) {
    const meshes = signalMeshes[dir]
    if (!meshes) continue

    const isGreen = phaseTimer.value < currentPhase.green && currentPhase.greenDirs.includes(dir)
    const isYellow = !isGreen && phaseTimer.value < currentPhase.green + currentPhase.yellow

    meshes.green.material.emissiveIntensity = isGreen ? 1 : 0
    meshes.yellow.material.emissiveIntensity = isYellow ? 1 : 0
    meshes.red.material.emissiveIntensity = (!isGreen && !isYellow) ? 1 : 0
  }
}

function animate() {
  animId = requestAnimationFrame(animate)
  controls?.update()
  if (renderer && scene && camera) renderer.render(scene, camera)
}

function startSim() {
  running.value = true
  simTimer = window.setInterval(simStep, 100)
}

function stopSim() {
  running.value = false
  if (simTimer) { clearInterval(simTimer); simTimer = null }
}

function resetSim() {
  stopSim()
  simTime.value = 0
  phaseIndex.value = 0
  phaseTimer.value = 0
  totalQueue.value = 0

  // 移除所有车辆mesh
  for (const dir of ['north', 'south', 'east', 'west']) {
    for (const v of vehicles.value[dir]) {
      if (v.mesh && scene) scene.remove(v.mesh)
    }
    vehicles.value[dir] = []
  }
}

function simStep() {
  simTime.value += 0.1
  phaseTimer.value += 0.1

  const currentPhase = phases[phaseIndex.value]
  const phaseDuration = currentPhase.green + currentPhase.yellow + currentPhase.all_red
  if (phaseTimer.value >= phaseDuration) {
    phaseIndex.value = (phaseIndex.value + 1) % phases.length
    phaseTimer.value = 0
  }

  updateSignalLights()

  const isGreen = (dir: string) => {
    const p = phases[phaseIndex.value]
    return phaseTimer.value < p.green && p.greenDirs.includes(dir)
  }

  let queueCount = 0

  for (const dir of ['north', 'south', 'east', 'west']) {
    const list = vehicles.value[dir]
    const flow = flows.value[dir] || 400
    const prob = (flow / 3600) * 0.1

    // 生成
    if (Math.random() < prob) {
      const mesh = new THREE.Mesh(vehicleGeo, vehicleMats.moving.clone())
      mesh.castShadow = true
      scene!.add(mesh)
      list.push({ id: `v${vehicleIdCounter++}`, pos: 0, speed: 8 + Math.random() * 4, stopped: false, mesh })
    }

    // 更新
    for (let i = list.length - 1; i >= 0; i--) {
      const v = list[i]
      const leader = i > 0 ? list[i - 1] : null
      const green = isGreen(dir)

      if (!green && v.pos > APPROACH_LENGTH - 10) {
        v.speed = Math.max(0, v.speed - 2)
        if (v.speed < 0.5) { v.stopped = true; queueCount++ }
      } else if (leader) {
        const gap = leader.pos - v.pos - 5
        if (gap < 3) v.speed = Math.max(0, v.speed - 1.5)
        else if (gap > 10) v.speed = Math.min(12, v.speed + 0.5)
      } else {
        v.speed = Math.min(12, v.speed + 0.3)
      }

      v.pos += v.speed * 0.1
      if (v.speed > 0.5) v.stopped = false

      // 更新3D位置
      if (v.mesh) {
        const mat = v.mesh.material as THREE.MeshStandardMaterial
        switch (dir) {
          case 'north':
            v.mesh.position.set(-5, 0.5, -ROAD_WIDTH - v.pos)
            v.mesh.rotation.y = 0
            break
          case 'south':
            v.mesh.position.set(5, 0.5, ROAD_WIDTH + v.pos)
            v.mesh.rotation.y = Math.PI
            break
          case 'east':
            v.mesh.position.set(ROAD_WIDTH + v.pos, 0.5, -5)
            v.mesh.rotation.y = -Math.PI / 2
            break
          case 'west':
            v.mesh.position.set(-ROAD_WIDTH - v.pos, 0.5, 5)
            v.mesh.rotation.y = Math.PI / 2
            break
        }
        // 颜色
        if (v.stopped) mat.color.set(0xef4444)
        else if (v.speed < 4) mat.color.set(0xf59e0b)
        else mat.color.set(0x22c55e)
      }

      // 移除
      if (v.pos > APPROACH_LENGTH + 30) {
        if (v.mesh && scene) scene.remove(v.mesh)
        list.splice(i, 1)
      }
    }
  }

  totalQueue.value = queueCount
}

function handleResize() {
  if (!canvasRef.value || !camera || !renderer) return
  const w = canvasRef.value.clientWidth
  const h = canvasRef.value.clientHeight
  camera.aspect = w / h
  camera.updateProjectionMatrix()
  renderer.setSize(w, h)
}

onMounted(() => {
  initScene()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  stopSim()
  if (animId) cancelAnimationFrame(animId)
  window.removeEventListener('resize', handleResize)
  controls?.dispose()
  renderer?.dispose()
})

defineExpose({ startSim, stopSim, resetSim })
</script>

<template>
  <div class="micro-sim">
    <div class="sim-controls">
      <div class="flow-inputs">
        <div class="flow-item" v-for="dir in ['north', 'south', 'east', 'west']" :key="dir">
          <label class="label">{{ { north: '北', south: '南', east: '东', west: '西' }[dir] }}</label>
          <input v-model.number="flows[dir]" type="number" class="flow-input" />
        </div>
      </div>
      <div class="sim-status">
        <span class="mono" style="font-size:12px;color:var(--accent-cyan)">T: {{ simTime.toFixed(1) }}s</span>
        <span class="mono" style="font-size:12px;color:var(--accent-amber)">排队: {{ totalQueue }}</span>
      </div>
      <div class="sim-buttons">
        <button v-if="!running" class="btn-primary" @click="startSim">▶ 启动</button>
        <button v-else class="btn-secondary" @click="stopSim">⏸ 暂停</button>
        <button class="btn-secondary" @click="resetSim">↺ 重置</button>
      </div>
    </div>
    <div class="canvas-wrapper">
      <canvas ref="canvasRef" class="sim-canvas"></canvas>
      <div class="canvas-hint label">拖拽旋转 · 滚轮缩放</div>
    </div>
  </div>
</template>

<style scoped>
.micro-sim {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.sim-controls {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: var(--sp-3);
  flex-wrap: wrap;
}

.flow-inputs {
  display: flex;
  gap: var(--sp-2);
}

.flow-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.flow-item label { font-size: 10px; }
.flow-input { width: 70px; padding: 4px 6px; font-size: 12px; }

.sim-status {
  display: flex;
  gap: var(--sp-3);
  align-items: center;
}

.sim-buttons {
  display: flex;
  gap: var(--sp-2);
}

.canvas-wrapper {
  position: relative;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.sim-canvas {
  width: 100%;
  height: 400px;
  display: block;
}

.canvas-hint {
  position: absolute;
  bottom: 8px;
  right: 8px;
  font-size: 10px;
  color: var(--text-muted);
  pointer-events: none;
}
</style>
