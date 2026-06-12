<!--
  NetworkWorkspace.vue — 路网工作台
  deck.gl + Leaflet: WebGL渲染路网/车辆/信号灯
  路段: PathLayer (宽度按车道数, 颜色按等级)
  车辆: ScatterplotLayer (颜色按速度)
  节点: ScatterplotLayer (半径按连接度)
  信号灯: ScatterplotLayer (颜色按灯色)
-->
<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { Deck } from '@deck.gl/core'
import { PathLayer, ScatterplotLayer, TextLayer } from '@deck.gl/layers'
import { networkApi } from '../api'
import { useAppStore } from '../stores/app'
import { useSimulationStore } from '../stores/simulation'
import TopBar from '../components/TopBar.vue'
import ToolSidebar from '../components/ToolSidebar.vue'
import BottomBar from '../components/BottomBar.vue'
import IntersectionEditor from '../components/IntersectionEditor.vue'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const simStore = useSimulationStore()

const mapContainer = ref<HTMLElement | null>(null)
const loading = ref(true)
const networkId = computed(() => route.params.id as string)
const isNewNetwork = computed(() => networkId.value === 'new')
const networkData = ref<any>(null)
const networkName = ref('')

let map: L.Map | null = null
let deck: any = null

// 数据
const nodePositions = new Map<string, { lat: number; lng: number }>()
let currentNodes: any[] = []
let currentEdges: any[] = []
let currentSignals: any[] = []

// 道路等级颜色 [r, g, b, a]
const ROAD_COLORS: Record<string, number[]> = {
  motorway: [239, 68, 68, 200],
  trunk: [249, 115, 22, 200],
  primary: [234, 179, 8, 200],
  secondary: [34, 197, 94, 200],
  tertiary: [59, 130, 246, 200],
  residential: [148, 163, 184, 180],
}

function initMap() {
  if (!mapContainer.value) return

  map = L.map(mapContainer.value, {
    center: [35.096, 118.352],
    zoom: 14,
    zoomControl: false,
    attributionControl: false,
  })

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
  }).addTo(map)

  // 初始化 deck.gl overlay
  initDeckGL()

  // 地图变化时更新 deck.gl 视口
  map.on('moveend', syncDeck)
  map.on('zoomend', syncDeck)
}

function initDeckGL() {
  if (!map) return

  // 使用 deck.gl 的 Leaflet 集成
  const deckOverlay = new (Deck as any)({
    canvas: createDeckCanvas(),
    width: '100%',
    height: '100%',
    initialViewState: {
      longitude: map.getCenter().lng,
      latitude: map.getCenter().lat,
      zoom: map.getZoom(),
    },
    controller: false,
    layers: [],
    _animate: true,
  })

  deck = deckOverlay
  syncDeck()
}

function createDeckCanvas(): HTMLCanvasElement {
  const container = map!.getContainer()
  const canvas = document.createElement('canvas')
  canvas.style.position = 'absolute'
  canvas.style.top = '0'
  canvas.style.left = '0'
  canvas.style.width = '100%'
  canvas.style.height = '100%'
  canvas.style.pointerEvents = 'none'
  canvas.style.zIndex = '400'

  // 插入到 Leaflet 的 overlay pane 前面
  const pane = container.querySelector('.leaflet-map-pane')
  if (pane) {
    container.insertBefore(canvas, pane)
  } else {
    container.appendChild(canvas)
  }

  return canvas
}

function syncDeck() {
  if (!map || !deck) return

  const center = map.getCenter()
  const zoom = map.getZoom()
  const size = map.getSize()

  deck.setProps({
    width: size.x,
    height: size.y,
    viewState: {
      longitude: center.lng,
      latitude: center.lat,
      zoom: zoom,
    },
  })
}

function updateLayers() {
  if (!deck) return

  const layers = []

  // 1. 路段层 (PathLayer)
  if (currentEdges.length > 0) {
    const pathData = currentEdges.map((edge: any) => {
      const fromPos = nodePositions.get(edge.from_node)
      const toPos = nodePositions.get(edge.to_node)
      if (!fromPos || !toPos) return null
      return {
        path: [[fromPos.lng, fromPos.lat], [toPos.lng, toPos.lat]],
        color: ROAD_COLORS[edge.road_class] || [148, 163, 184, 180],
        width: (edge.lanes_count || 1) * 3.5,
        name: edge.name || edge.edge_id,
        lanes: edge.lanes_count,
        speed: edge.speed_limit,
        length: edge.length,
      }
    }).filter(Boolean)

    layers.push(
      new PathLayer({
        id: 'road-edges',
        data: pathData,
        getPath: (d: any) => d.path,
        getColor: (d: any) => d.color,
        getWidth: (d: any) => d.width,
        widthUnits: 'meters',
        widthMinPixels: 2,
        widthMaxPixels: 20,
        capRounded: true,
        jointRounded: true,
        pickable: true,
        // onClick: (info: any) => { /* 路段点击 */ },
      })
    )
  }

  // 2. 节点层 (ScatterplotLayer)
  if (currentNodes.length > 0) {
    const nodeData = currentNodes.map((node: any) => {
      const degree = currentEdges.filter(
        (e: any) => e.from_node === node.node_id || e.to_node === node.node_id
      ).length
      return {
        position: [node.lng, node.lat],
        radius: Math.max(8, Math.min(degree * 4, 25)),
        color: node.node_type === 'roundabout' ? [34, 197, 94, 230] : [59, 130, 246, 230],
        name: node.name || node.node_id,
        nodeId: node.node_id,
      }
    })

    layers.push(
      new ScatterplotLayer({
        id: 'road-nodes',
        data: nodeData,
        getPosition: (d: any) => d.position,
        getRadius: (d: any) => d.radius,
        getFillColor: (d: any) => d.color,
        getLineColor: [255, 255, 255, 200],
        getLineWidth: 2,
        stroked: true,
        filled: true,
        radiusUnits: 'pixels',
        pickable: true,
        onClick: (info: any) => {
          if (info.object) {
            appStore.selectObject({ type: 'node', id: info.object.nodeId, data: info.object })
            appStore.openIntersectionEditor(info.object.nodeId)
          }
        },
      })
    )

    // 节点文字标签
    layers.push(
      new TextLayer({
        id: 'node-labels',
        data: nodeData,
        getPosition: (d: any) => d.position,
        getText: (d: any) => d.name,
        getSize: 11,
        getColor: [15, 23, 42, 200],
        getBackgroundColor: [255, 255, 255, 180],
        backgroundPadding: [4, 2, 4, 2],
        fontFamily: 'Fira Sans, sans-serif',
        fontWeight: 600,
        getTextAnchor: 'middle',
        getAlignmentBaseline: 'bottom',
        pixelOffset: [0, -20],
        sizeUnits: 'pixels',
      })
    )
  }

  // 3. 信号灯层 (ScatterplotLayer)
  if (currentSignals.length > 0) {
    const sigData = currentSignals.map((sig: any) => {
      const pos = nodePositions.get(sig.node_id)
      if (!pos) return null
      // 偏移到节点右上方
      return {
        position: [pos.lng + 0.00003, pos.lat + 0.00003],
        color: [34, 197, 94, 255], // 默认绿
        radius: 5,
        nodeId: sig.node_id,
      }
    }).filter(Boolean)

    layers.push(
      new ScatterplotLayer({
        id: 'signals',
        data: sigData,
        getPosition: (d: any) => d.position,
        getRadius: (d: any) => d.radius,
        getFillColor: (d: any) => d.color,
        getLineColor: [15, 23, 42, 255],
        getLineWidth: 1,
        stroked: true,
        filled: true,
        radiusUnits: 'pixels',
        radiusMinPixels: 4,
        radiusMaxPixels: 8,
      })
    )
  }

  // 4. 车辆层 (ScatterplotLayer) — 仿真时动态更新
  const vehicles = simStore.vehicles
  if (vehicles && vehicles.length > 0) {
    const vehicleData = vehicles.map((v: any) => {
      const fromPos = nodePositions.get(v.from_node)
      const toPos = nodePositions.get(v.to_node)
      if (!fromPos || !toPos) return null

      const progress = Math.min(Math.max(v.position / (v.edge_length || 100), 0), 1)
      const lat = fromPos.lat + (toPos.lat - fromPos.lat) * progress
      const lng = fromPos.lng + (toPos.lng - fromPos.lng) * progress
      const speed = v.speed || 0

      let color: number[]
      if (speed > 40) color = [34, 197, 94, 220]    // 绿色 畅通
      else if (speed > 20) color = [245, 158, 11, 220] // 黄色 缓行
      else color = [239, 68, 68, 220]                 // 红色 拥堵

      return { position: [lng, lat], color, radius: 3, speed }
    }).filter(Boolean)

    layers.push(
      new ScatterplotLayer({
        id: 'vehicles',
        data: vehicleData,
        getPosition: (d: any) => d.position,
        getRadius: (d: any) => d.radius,
        getFillColor: (d: any) => d.color,
        radiusUnits: 'pixels',
        radiusMinPixels: 2,
        radiusMaxPixels: 6,
        _animate: true,
      })
    )
  }

  deck.setProps({ layers })
}

async function loadNetwork() {
  if (isNewNetwork.value) {
    networkName.value = '新建路网'
    loading.value = false
    return
  }

  loading.value = true
  try {
    const id = parseInt(networkId.value)
    const res = await networkApi.get(id)
    networkData.value = res.data
    networkName.value = res.data.name

    currentNodes = res.data.nodes || []
    currentEdges = res.data.edges || []
    currentSignals = res.data.signals || []

    nodePositions.clear()
    for (const node of currentNodes) {
      nodePositions.set(node.node_id, { lat: node.lat, lng: node.lng })
    }

    updateLayers()

    if (currentNodes.length > 0 && map) {
      const bounds = L.latLngBounds(currentNodes.map((n: any) => [n.lat, n.lng]))
      map.fitBounds(bounds, { padding: [50, 50] })
      setTimeout(syncDeck, 300)
    }
  } catch (e) {
    console.error('加载路网失败:', e)
  } finally {
    loading.value = false
  }
}

async function handleSimStart() {
  if (!networkData.value) return
  try {
    await simStore.startSimulation({
      network_id: parseInt(networkId.value),
      duration: 1800, step_size: 1, speed_multiplier: 1,
    })
  } catch (e) { console.error('启动仿真失败:', e) }
}

async function handleSimStop() { await simStore.stopSimulation() }
function handleSimReset() { simStore.reset(); updateLayers() }

// 监听仿真更新
watch(() => simStore.vehicles, () => updateLayers(), { deep: true })
watch(() => simStore.signals, (signals) => {
  // 更新信号灯颜色
  if (currentSignals.length > 0) {
    for (const sig of currentSignals) {
      const state = signals[sig.node_id]
      if (state) {
        const phase = (sig.phases || [])[state.current_phase]
        if (phase) {
          const total = phase.green + phase.yellow + phase.all_red
          const elapsed = (state.phase_elapsed || 0) % total
          const isGreen = elapsed < phase.green
          const isYellow = !isGreen && elapsed < phase.green + phase.yellow
          sig._color = isGreen ? [34, 197, 94, 255] : isYellow ? [245, 158, 11, 255] : [239, 68, 68, 255]
        }
      }
    }
    updateLayers()
  }
}, { deep: true })

onMounted(async () => {
  initMap()
  await loadNetwork()
})

onUnmounted(() => {
  deck?.finalize()
  map?.remove()
})
</script>

<template>
  <div class="workspace">
    <TopBar :network-name="networkName" :network-id="networkId" @back="router.push('/')" />
    <div class="workspace-body">
      <ToolSidebar @sim-start="handleSimStart" @sim-stop="handleSimStop" @sim-reset="handleSimReset" />
      <div class="map-container" ref="mapContainer">
        <div v-if="loading" class="loading-overlay">
          <div class="loading-text">加载中...</div>
        </div>
      </div>
    </div>
    <BottomBar />
    <IntersectionEditor
      v-if="appStore.intersectionEditorOpen"
      :node-id="appStore.intersectionEditorNodeId!"
      @close="appStore.closeIntersectionEditor()"
    />
  </div>
</template>

<style scoped>
.workspace { height: 100vh; display: flex; flex-direction: column; background: var(--bg-base); position: relative; z-index: 1; }
.workspace-body { flex: 1; display: flex; overflow: hidden; }
.map-container { flex: 1; position: relative; }
.loading-overlay { position: absolute; inset: 0; background: rgba(248,250,252,0.8); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.loading-text { color: var(--primary); font-size: 14px; font-weight: 500; }
</style>

<style>
.node-tooltip, .edge-tooltip {
  font-family: 'Fira Sans', sans-serif;
  font-size: 13px;
  border-radius: 8px;
  padding: 8px 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
</style>
