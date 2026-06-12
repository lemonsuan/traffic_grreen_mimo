<!--
  ChannelCanvas.vue — 3D交叉口渠化渲染 (Three.js)
  功能: 渲染交叉口俯视3D视图, 显示车道/停止线/信号灯
  支持: OrbitControls旋转, 点击车道切换类型
-->
<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'

interface LaneInfo {
  id: number
  index: number
  type: string
  width: number
  signal_display: string
}

interface ApproachData {
  edge_id: string
  road_class: string
  lanes_count: number
  lanes: LaneInfo[]
}

const props = defineProps<{
  approaches: Record<string, ApproachData>
  currentPhase?: number
}>()

const emit = defineEmits<{
  laneClick: [direction: string, laneIndex: number]
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)

let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let renderer: THREE.WebGLRenderer | null = null
let controls: OrbitControls | null = null
let animId: number | null = null

const LANE_WIDTH = 3.5
const LANE_LENGTH = 30
const STOP_LINE_OFFSET = 2

const LANE_COLORS: Record<string, number> = {
  through: 0x38bdf8,
  left_turn: 0xf59e0b,
  right_turn: 0x22c55e,
  left_through: 0xeab308,
  right_through: 0x14b8a6,
  bus: 0xef4444,
  emergency: 0xff0000,
}

function initScene() {
  if (!canvasRef.value) return

  const w = canvasRef.value.clientWidth
  const h = canvasRef.value.clientHeight

  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x0a0e14)

  camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 1000)
  camera.position.set(0, 60, 40)
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
  const groundGeo = new THREE.PlaneGeometry(120, 120)
  const groundMat = new THREE.MeshStandardMaterial({ color: 0x111820, roughness: 0.9 })
  const ground = new THREE.Mesh(groundGeo, groundMat)
  ground.rotation.x = -Math.PI / 2
  ground.receiveShadow = true
  scene.add(ground)

  // 网格
  const grid = new THREE.GridHelper(120, 24, 0x1a3040, 0x111820)
  scene.add(grid)

  animate()
}

function animate() {
  animId = requestAnimationFrame(animate)
  controls?.update()
  if (renderer && scene && camera) {
    renderer.render(scene, camera)
  }
}

function drawIntersection() {
  if (!scene) return

  // 清除旧绘制(保留地面/灯光/网格)
  const toRemove: THREE.Object3D[] = []
  scene.traverse((child) => {
    if (child.userData.custom) toRemove.push(child)
  })
  toRemove.forEach((obj) => scene!.remove(obj))

  const approaches = props.approaches || {}
  const directions: Record<string, { angle: number; label: string }> = {
    north: { angle: 0, label: '北' },
    east: { angle: Math.PI / 2, label: '东' },
    south: { angle: Math.PI, label: '南' },
    west: { angle: -Math.PI / 2, label: '西' },
  }

  for (const [dir, data] of Object.entries(approaches)) {
    const dirInfo = directions[dir]
    if (!dirInfo) continue

    const lanes = data.lanes || []
    const totalWidth = lanes.length * LANE_WIDTH

    // 进口道车道
    lanes.forEach((lane, i) => {
      const offsetX = (i - (lanes.length - 1) / 2) * LANE_WIDTH
      const color = LANE_COLORS[lane.type] || 0x64748b

      // 车道路面
      const geo = new THREE.BoxGeometry(LANE_WIDTH - 0.1, 0.15, LANE_LENGTH)
      const mat = new THREE.MeshStandardMaterial({ color, roughness: 0.8, metalness: 0.1 })
      const mesh = new THREE.Mesh(geo, mat)
      mesh.position.set(offsetX, 0.1, -LANE_LENGTH / 2 - STOP_LINE_OFFSET)
      mesh.rotation.y = dirInfo.angle
      mesh.userData = { custom: true, type: 'lane', direction: dir, index: i }
      scene!.add(mesh)

      // 箭头标记
      const arrowGeo = new THREE.ConeGeometry(0.6, 1.5, 4)
      const arrowMat = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 0.3 })
      const arrow = new THREE.Mesh(arrowGeo, arrowMat)
      arrow.position.set(offsetX, 0.3, -8)
      arrow.rotation.x = Math.PI / 2
      arrow.rotation.y = dirInfo.angle
      arrow.userData = { custom: true }
      scene!.add(arrow)
    })

    // 停止线
    const stopGeo = new THREE.BoxGeometry(totalWidth + 0.5, 0.05, 0.4)
    const stopMat = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 0.2 })
    const stopLine = new THREE.Mesh(stopGeo, stopMat)
    stopLine.position.set(0, 0.2, -STOP_LINE_OFFSET)
    stopLine.rotation.y = dirInfo.angle
    stopLine.userData = { custom: true }
    scene!.add(stopLine)

    // 信号灯
    const lightColor = _getSignalColor(dir)
    const poleGeo = new THREE.CylinderGeometry(0.15, 0.15, 5, 8)
    const poleMat = new THREE.MeshStandardMaterial({ color: 0x666666 })
    const pole = new THREE.Mesh(poleGeo, poleMat)
    pole.position.set(totalWidth / 2 + 1, 2.5, -2)
    pole.rotation.y = dirInfo.angle
    pole.userData = { custom: true }
    scene!.add(pole)

    const bulbGeo = new THREE.SphereGeometry(0.5, 16, 16)
    const bulbMat = new THREE.MeshStandardMaterial({
      color: lightColor, emissive: lightColor, emissiveIntensity: 0.8
    })
    const bulb = new THREE.Mesh(bulbGeo, bulbMat)
    bulb.position.set(totalWidth / 2 + 1, 5.5, -2)
    bulb.rotation.y = dirInfo.angle
    bulb.userData = { custom: true, type: 'signal', direction: dir }
    scene!.add(bulb)
  }
}

function _getSignalColor(direction: string): number {
  // 简化: 奇数相位NS绿, 偶数相位EW绿
  const phase = props.currentPhase || 0
  if (direction === 'north' || direction === 'south') {
    return phase % 2 === 0 ? 0x22c55e : 0xef4444
  } else {
    return phase % 2 === 1 ? 0x22c55e : 0xef4444
  }
}

function handleResize() {
  if (!canvasRef.value || !camera || !renderer) return
  const w = canvasRef.value.clientWidth
  const h = canvasRef.value.clientHeight
  camera.aspect = w / h
  camera.updateProjectionMatrix()
  renderer.setSize(w, h)
}

watch(() => props.approaches, () => drawIntersection(), { deep: true })
watch(() => props.currentPhase, () => drawIntersection())

onMounted(() => {
  initScene()
  drawIntersection()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (animId) cancelAnimationFrame(animId)
  window.removeEventListener('resize', handleResize)
  controls?.dispose()
  renderer?.dispose()
})
</script>

<template>
  <div class="channel-canvas">
    <canvas ref="canvasRef" class="three-canvas"></canvas>
    <div class="canvas-hint label">拖拽旋转 · 滚轮缩放</div>
  </div>
</template>

<style scoped>
.channel-canvas {
  position: relative;
  width: 100%;
  height: 300px;
  background: var(--bg-primary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.three-canvas {
  width: 100%;
  height: 100%;
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
