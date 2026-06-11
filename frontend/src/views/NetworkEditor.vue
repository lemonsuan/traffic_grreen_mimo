<template>
  <div class="network-editor">
    <div class="editor-header">
      <h1>路网编辑器</h1>
      <div class="header-actions">
        <button class="btn btn-secondary" @click="importNetwork">导入路网</button>
        <button class="btn btn-primary" @click="saveNetwork">保存路网</button>
      </div>
    </div>
    
    <div class="editor-content">
      <div class="toolbar">
        <div class="tool-group">
          <button 
            v-for="tool in tools" 
            :key="tool.id"
            :class="['tool-btn', { active: currentTool === tool.id }]"
            @click="currentTool = tool.id"
            :title="tool.name"
          >
            {{ tool.icon }}
          </button>
        </div>
        
        <div class="separator"></div>
        
        <div class="tool-group">
          <button class="tool-btn" @click="zoomIn" title="放大">🔍+</button>
          <button class="tool-btn" @click="zoomOut" title="缩小">🔍-</button>
          <button class="tool-btn" @click="resetView" title="重置视图">🏠</button>
        </div>
      </div>
      
      <div class="map-container">
        <div id="map" ref="mapContainer"></div>
      </div>
      
      <div class="properties-panel">
        <h3>属性面板</h3>
        
        <div v-if="selectedNode" class="property-section">
          <h4>节点属性</h4>
          <div class="form-group">
            <label>ID</label>
            <input v-model="selectedNode.node_id" class="form-input" />
          </div>
          <div class="form-group">
            <label>名称</label>
            <input v-model="selectedNode.name" class="form-input" />
          </div>
          <div class="form-group">
            <label>类型</label>
            <select v-model="selectedNode.node_type" class="form-input">
              <option value="intersection">信号灯路口</option>
              <option value="roundabout">环岛</option>
            </select>
          </div>
        </div>
        
        <div v-else-if="selectedEdge" class="property-section">
          <h4>路段属性</h4>
          <div class="form-group">
            <label>ID</label>
            <input v-model="selectedEdge.edge_id" class="form-input" />
          </div>
          <div class="form-group">
            <label>名称</label>
            <input v-model="selectedEdge.name" class="form-input" />
          </div>
          <div class="form-group">
            <label>长度 (米)</label>
            <input v-model.number="selectedEdge.length" type="number" class="form-input" />
          </div>
          <div class="form-group">
            <label>限速 (km/h)</label>
            <input v-model.number="selectedEdge.speed_limit" type="number" class="form-input" />
          </div>
          <div class="form-group">
            <label>车道数</label>
            <input v-model.number="selectedEdge.lanes_count" type="number" class="form-input" />
          </div>
        </div>
        
        <div v-else class="empty-state">
          选择节点或路段查看属性
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useNetworkStore } from '../stores/network'

const networkStore = useNetworkStore()
const mapContainer = ref<HTMLElement | null>(null)
const map = ref<L.Map | null>(null)
const markers = ref<L.CircleMarker[]>([])

const currentTool = ref('select')
const selectedNode = ref<any>(null)
const selectedEdge = ref<any>(null)
const currentNetworkId = ref<number | null>(null)
const newNodeCounter = ref(0)

const tools = [
  { id: 'select', name: '选择', icon: '🔍' },
  { id: 'addNode', name: '添加节点', icon: '📍' },
  { id: 'addEdge', name: '添加路段', icon: '➖' },
  { id: 'delete', name: '删除', icon: '🗑️' }
]

const pendingEdge = ref<{ from: any; marker: L.CircleMarker } | null>(null)

onMounted(async () => {
  initMap()
  await networkStore.fetchNetworks()
})

onUnmounted(() => {
  if (map.value) {
    map.value.remove()
  }
})

function initMap() {
  if (!mapContainer.value) return

  map.value = L.map(mapContainer.value).setView([39.9042, 116.4074], 13)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
  }).addTo(map.value as any)

  map.value.on('click', handleMapClick)
}

function handleMapClick(e: L.LeafletMouseEvent) {
  if (currentTool.value === 'addNode') {
    addNode(e.latlng.lat, e.latlng.lng)
  }
}

function addNode(lat: number, lng: number) {
  if (!map.value) return

  newNodeCounter.value++
  const nodeId = `node_${newNodeCounter.value}`

  const marker = L.circleMarker([lat, lng], {
    radius: 10,
    color: '#1890ff',
    fillColor: '#1890ff',
    fillOpacity: 0.8
  })
  marker.addTo(map.value as any)
  markers.value.push(marker)

  const nodeData = {
    node_id: nodeId,
    name: `路口 ${newNodeCounter.value}`,
    node_type: 'intersection',
    lat,
    lng,
    x: 0,
    y: 0,
    marker
  }

  marker.on('click', () => {
    if (currentTool.value === 'select') {
      selectedNode.value = nodeData
      selectedEdge.value = null
    } else if (currentTool.value === 'addEdge') {
      if (!pendingEdge.value) {
        pendingEdge.value = { from: nodeData, marker }
        marker.setStyle({ color: '#52c41a', fillColor: '#52c41a' })
      } else {
        const fromNode = pendingEdge.value.from
        networkStore.createEdge({
          network: currentNetworkId.value!,
          edge_id: `${fromNode.node_id}_${nodeData.node_id}`,
          from_node: fromNode.node_id as any,
          to_node: nodeData.node_id as any,
          length: 500,
          speed_limit: 50,
          lanes_count: 2,
          capacity: 1800,
          road_class: 'arterial',
          is_oneway: false
        }).catch(() => {})
        pendingEdge.value.marker.setStyle({ color: '#1890ff', fillColor: '#1890ff' })
        pendingEdge.value = null
      }
    } else if (currentTool.value === 'delete') {
      map.value?.removeLayer(marker)
      markers.value = markers.value.filter(m => m !== marker)
    }
  })

  if (currentNetworkId.value) {
    networkStore.createNode({
      network: currentNetworkId.value,
      node_id: nodeId,
      name: nodeData.name,
      node_type: nodeData.node_type,
      lat,
      lng,
      x: 0,
      y: 0,
      z: 0
    }).catch(() => {})
  }
}

function zoomIn() {
  map.value?.zoomIn()
}

function zoomOut() {
  map.value?.zoomOut()
}

function resetView() {
  map.value?.setView([39.9042, 116.4074], 13)
}

async function importNetwork() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.json'
  input.onchange = async (e) => {
    const file = (e.target as HTMLInputElement).files?.[0]
    if (!file) return
    try {
      const text = await file.text()
      const data = JSON.parse(text)

      if (!currentNetworkId.value) {
        const network = await networkStore.createNetwork({
          name: data.network?.name || file.name.replace('.json', ''),
          description: data.network?.description || ''
        })
        currentNetworkId.value = network.id
      }

      await networkStore.importNetwork(currentNetworkId.value, data)
      alert('导入成功')
    } catch (err) {
      alert('导入失败: ' + (err as Error).message)
    }
  }
  input.click()
}

async function saveNetwork() {
  try {
    if (!currentNetworkId.value) {
      const network = await networkStore.createNetwork({
        name: `路网_${new Date().toLocaleString('zh-CN')}`,
        description: '从编辑器保存'
      })
      currentNetworkId.value = network.id
    }
    alert('路网已保存')
  } catch (err) {
    alert('保存失败: ' + (err as Error).message)
  }
}
</script>

<style scoped>
.network-editor {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: white;
  border-bottom: 1px solid #e8e8e8;
}

.editor-header h1 {
  margin: 0;
  font-size: 20px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.editor-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.toolbar {
  width: 60px;
  background: white;
  border-right: 1px solid #e8e8e8;
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tool-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tool-btn {
  width: 44px;
  height: 44px;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  font-size: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.tool-btn:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.tool-btn.active {
  background: #1890ff;
  border-color: #1890ff;
  color: white;
}

.separator {
  height: 1px;
  background: #e8e8e8;
  margin: 8px 0;
}

.map-container {
  flex: 1;
  position: relative;
}

#map {
  width: 100%;
  height: 100%;
}

.properties-panel {
  width: 300px;
  background: white;
  border-left: 1px solid #e8e8e8;
  padding: 16px;
  overflow-y: auto;
}

.properties-panel h3 {
  margin: 0 0 16px 0;
  font-size: 16px;
}

.property-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #666;
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

.form-input:focus {
  outline: none;
  border-color: #1890ff;
}

.empty-state {
  text-align: center;
  color: #999;
  padding: 24px;
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

.btn-primary:hover {
  background: #40a9ff;
}

.btn-secondary {
  background: white;
  border: 1px solid #d9d9d9;
}

.btn-secondary:hover {
  border-color: #1890ff;
  color: #1890ff;
}
</style>
