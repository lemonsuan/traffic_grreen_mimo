<template>
  <div class="optimization">
    <div class="opt-header">
      <h1>信号优化</h1>
    </div>
    
    <div class="opt-content">
      <div class="opt-sidebar">
        <div class="network-selector">
          <h3>路网选择</h3>
          <select v-model="selectedNetworkId" class="form-input" @change="selectedNodeIds = []">
            <option :value="null">请选择路网</option>
            <option v-for="n in networks" :key="n.id" :value="n.id">{{ n.name }}</option>
          </select>
          <div v-if="currentLevel === 'intersection' && availableNodes.length > 0" class="form-group" style="margin-top:8px">
            <label>选择节点</label>
            <select v-model="selectedNodeIds[0]" class="form-input">
              <option v-for="node in availableNodes" :key="node.node_id" :value="node.node_id">
                {{ node.name || node.node_id }}
              </option>
            </select>
          </div>
          <div v-if="currentLevel === 'corridor' && availableNodes.length >= 2" class="form-group" style="margin-top:8px">
            <label>选择节点 (多选)</label>
            <div class="node-checkbox-group">
              <label v-for="node in availableNodes" :key="node.node_id" class="node-checkbox">
                <input type="checkbox" :value="node.node_id" v-model="selectedNodeIds" />
                {{ node.name || node.node_id }}
              </label>
            </div>
          </div>
        </div>

        <div class="level-selector">
          <h3>优化层级</h3>
          <div class="level-buttons">
            <button 
              v-for="level in levels" 
              :key="level.id"
              :class="['level-btn', { active: currentLevel === level.id }]"
              @click="currentLevel = level.id"
            >
              {{ level.name }}
            </button>
          </div>
        </div>
        
        <div class="algorithm-selector">
          <h3>算法选择</h3>
          <div class="algo-list">
            <label 
              v-for="algo in currentAlgorithms" 
              :key="algo.id"
              :class="['algo-item', { active: selectedAlgorithm === algo.id }]"
            >
              <input 
                type="radio" 
                :value="algo.id" 
                v-model="selectedAlgorithm"
                class="algo-radio"
              />
              <div class="algo-info">
                <div class="algo-name">{{ algo.name }}</div>
                <div class="algo-desc">{{ algo.description }}</div>
              </div>
            </label>
          </div>
        </div>
        
        <div class="params-section">
          <h3>参数配置</h3>
          <div class="form-group">
            <label>目标饱和度</label>
            <input v-model.number="params.targetSaturation" type="number" step="0.05" class="form-input" />
          </div>
          <div class="form-group">
            <label>最小绿灯时间 (秒)</label>
            <input v-model.number="params.minGreenTime" type="number" class="form-input" />
          </div>
          <div class="form-group">
            <label>最大周期 (秒)</label>
            <input v-model.number="params.maxCycle" type="number" class="form-input" />
          </div>
        </div>
        
        <button class="btn btn-primary btn-block" @click="runOptimization" :disabled="optimizing">
          {{ optimizing ? '优化中...' : '开始优化' }}
        </button>
      </div>
      
      <div class="opt-main">
        <div v-if="result" class="result-panel">
          <div class="result-header">
            <h2>优化结果</h2>
            <div class="result-actions">
              <button class="btn btn-secondary" @click="applyResult" :disabled="applying">
                {{ applying ? '应用中...' : '应用方案' }}
              </button>
              <button class="btn btn-secondary" @click="compareResult">对比分析</button>
            </div>
          </div>
          
          <div class="result-grid">
            <div class="result-card">
              <div class="result-label">算法</div>
              <div class="result-value">{{ result.algorithm }}</div>
            </div>
            <div class="result-card">
              <div class="result-label">计算时间</div>
              <div class="result-value">{{ result.computation_time.toFixed(2) }}秒</div>
            </div>
            <div class="result-card">
              <div class="result-label">平均延误</div>
              <div class="result-value highlight">{{ result.performance.avg_delay.toFixed(1) }}秒</div>
            </div>
            <div class="result-card">
              <div class="result-label">平均排队</div>
              <div class="result-value">{{ result.performance.avg_queue_length.toFixed(1) }}辆</div>
            </div>
            <div class="result-card">
              <div class="result-label">吞吐量</div>
              <div class="result-value">{{ result.performance.throughput }}辆</div>
            </div>
            <div class="result-card">
              <div class="result-label">饱和度</div>
              <div class="result-value">{{ result.performance.vcr.toFixed(2) }}</div>
            </div>
          </div>
          
          <div class="timing-section">
            <h3>信号配时方案</h3>
            <div v-for="(timing, nodeId) in result.signal_timings" :key="nodeId" class="timing-card">
              <div class="timing-header">
                <span class="timing-node">{{ nodeId }}</span>
                <span class="timing-cycle">周期: {{ timing.cycle_length }}秒</span>
              </div>
              <div class="timing-phases">
                <div 
                  v-for="phase in timing.phases" 
                  :key="phase.index"
                  class="phase-bar"
                  :style="{ width: (phase.green / timing.cycle_length * 100) + '%' }"
                >
                  <div class="phase-green">绿 {{ phase.green }}s</div>
                  <div class="phase-yellow">黄 {{ phase.yellow }}s</div>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div v-else class="empty-state">
          <div class="empty-icon">⚡</div>
          <div class="empty-text">选择优化层级和算法，点击"开始优化"</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { optimizationApi, networkApi } from '../api'

const router = useRouter()
const currentLevel = ref('intersection')
const selectedAlgorithm = ref('webster')
const optimizing = ref(false)
const result = ref<any>(null)
const applying = ref(false)

const networks = ref<Array<{ id: number; name: string; nodes: any[]; edges: any[] }>>([])
const selectedNetworkId = ref<number | null>(null)
const selectedNodeIds = ref<string[]>([])

const levels = [
  { id: 'intersection', name: '单点优化' },
  { id: 'corridor', name: '干线优化' },
  { id: 'network', name: '区域优化' }
]

const algorithms: Record<string, any[]> = {
  intersection: [
    { id: 'webster', name: 'Webster', description: '经典配时方法，适用于饱和度适中的路口' },
    { id: 'hcm', name: 'HCM', description: '延误最小化，考虑随机延误' },
    { id: 'actuated', name: '感应控制', description: '实时响应车流变化' },
    { id: 'adaptive', name: '自适应', description: 'SCOOT/SCATS简化版' }
  ],
  corridor: [
    { id: 'maxband', name: 'MAXBAND', description: '绿波带宽最大化' },
    { id: 'passer', name: 'PASSER-II', description: '多相位干线优化' },
    { id: 'ga', name: '遗传算法', description: '全局搜索，多目标优化' },
    { id: 'pso', name: '粒子群', description: '收敛快，参数少' }
  ],
  network: [
    { id: 'transyt', name: 'TRANSYT', description: '车队离散模型+爬山法' },
    { id: 'scoot', name: 'SCOOT', description: '实时自适应控制' },
    { id: 'nsga', name: 'NSGA-II', description: '多目标进化算法，Pareto前沿' }
  ]
}

const currentAlgorithms = computed(() => algorithms[currentLevel.value] || [])

const currentNetwork = computed(() => networks.value.find(n => n.id === selectedNetworkId.value))

const availableNodes = computed(() => currentNetwork.value?.nodes || [])

const params = ref({
  targetSaturation: 0.85,
  minGreenTime: 7,
  maxCycle: 180
})

async function loadNetworks() {
  try {
    const res = await networkApi.list()
    const list = res.data.results || res.data || []
    const detailed = await Promise.all(
      list.map(async (n: any) => {
        try {
          const detail = await networkApi.get(n.id)
          return { id: n.id, name: n.name, nodes: detail.data.nodes || [], edges: detail.data.edges || [] }
        } catch {
          return { id: n.id, name: n.name, nodes: [], edges: [] }
        }
      })
    )
    networks.value = detailed
    if (detailed.length > 0) {
      selectedNetworkId.value = detailed[0].id
      if (detailed[0].nodes.length > 0) {
        selectedNodeIds.value = [detailed[0].nodes[0].node_id]
      }
    }
  } catch (e) {
    console.error('获取路网列表失败:', e)
  }
}

function buildTrafficData(nodeId: string) {
  const node = currentNetwork.value?.nodes.find((n: any) => n.node_id === nodeId)
  const connectedEdges = currentNetwork.value?.edges.filter(
    (e: any) => e.from_node === nodeId || e.to_node === nodeId
  ) || []
  const approaches: Record<string, { volume: number }> = {}
  const directions = ['north_through', 'south_through', 'east_through', 'west_through',
    'north_left', 'south_left', 'east_left', 'west_left']
  directions.forEach((dir, i) => {
    const edge = connectedEdges[i % Math.max(connectedEdges.length, 1)]
    const flow = edge ? (edge.capacity || 500) * 0.6 : 400 + Math.random() * 200
    approaches[dir] = { volume: Math.round(flow) }
  })
  return { approaches }
}

async function runOptimization() {
  if (!selectedNetworkId.value) {
    alert('请先选择路网')
    return
  }
  optimizing.value = true
  result.value = null

  try {
    let res
    const optParams = {
      target_saturation: params.value.targetSaturation,
      min_green_time: params.value.minGreenTime,
      max_cycle: params.value.maxCycle
    }

    if (currentLevel.value === 'intersection') {
      const nodeId = selectedNodeIds.value[0] || availableNodes.value[0]?.node_id
      if (!nodeId) {
        alert('当前路网没有节点，请先创建路网')
        return
      }
      res = await optimizationApi.optimizeIntersection({
        node_id: nodeId,
        algorithm: selectedAlgorithm.value,
        params: optParams,
        traffic_data: buildTrafficData(nodeId)
      })
    } else if (currentLevel.value === 'corridor') {
      const nodeIds = selectedNodeIds.value.length >= 2
        ? selectedNodeIds.value
        : availableNodes.value.slice(0, 4).map((n: any) => n.node_id)
      if (nodeIds.length < 2) {
        alert('干线优化至少需要2个节点')
        return
      }
      res = await optimizationApi.optimizeCorridor({
        node_ids: nodeIds,
        algorithm: selectedAlgorithm.value,
        params: optParams
      })
    } else {
      res = await optimizationApi.optimizeNetwork({
        network_id: selectedNetworkId.value,
        algorithm: selectedAlgorithm.value,
        params: optParams
      })
    }

    result.value = res.data
  } catch (e: any) {
    console.error('优化失败:', e)
    alert('优化请求失败: ' + (e.response?.data?.error || e.message))
  } finally {
    optimizing.value = false
  }
}

async function applyResult() {
  if (!result.value?.id) {
    alert('请先运行优化获取结果')
    return
  }
  applying.value = true
  try {
    await optimizationApi.applyResult(result.value.id)
    alert('信号配时方案已成功应用到路网')
  } catch (e: any) {
    console.error('应用方案失败:', e)
    alert('应用失败: ' + (e.response?.data?.error || e.message))
  } finally {
    applying.value = false
  }
}

function compareResult() {
  router.push('/analysis')
}

onMounted(loadNetworks)
</script>

<style scoped>
.optimization {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.opt-header {
  padding: 16px 24px;
  background: white;
  border-bottom: 1px solid #e8e8e8;
}

.opt-header h1 {
  margin: 0;
  font-size: 20px;
}

.opt-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.opt-sidebar {
  width: 320px;
  background: white;
  border-right: 1px solid #e8e8e8;
  padding: 16px;
  overflow-y: auto;
}

.level-selector,
.algorithm-selector,
.params-section {
  margin-bottom: 24px;
}

.network-selector {
  margin-bottom: 24px;
}

.network-selector h3 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #333;
}

.node-checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}

.node-checkbox {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  cursor: pointer;
  padding: 2px 6px;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
}

.node-checkbox:has(input:checked) {
  border-color: #1890ff;
  background: #e6f7ff;
}

.level-selector h3,
.algorithm-selector h3,
.params-section h3 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #333;
}

.level-buttons {
  display: flex;
  gap: 8px;
}

.level-btn {
  flex: 1;
  padding: 8px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  font-size: 12px;
}

.level-btn.active {
  background: #1890ff;
  border-color: #1890ff;
  color: white;
}

.algo-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.algo-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.algo-item:hover {
  border-color: #1890ff;
}

.algo-item.active {
  border-color: #1890ff;
  background: #e6f7ff;
}

.algo-radio {
  margin-top: 2px;
}

.algo-name {
  font-size: 14px;
  font-weight: bold;
}

.algo-desc {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
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

.btn-block {
  width: 100%;
}

.opt-main {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.result-header h2 {
  margin: 0;
}

.result-actions {
  display: flex;
  gap: 12px;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 32px;
}

.result-card {
  background: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.result-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 8px;
}

.result-value {
  font-size: 24px;
  font-weight: bold;
  color: #333;
}

.result-value.highlight {
  color: #1890ff;
}

.timing-section h3 {
  margin: 0 0 16px 0;
}

.timing-card {
  background: white;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.timing-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}

.timing-node {
  font-weight: bold;
}

.timing-cycle {
  color: #666;
}

.timing-phases {
  display: flex;
  gap: 4px;
  height: 40px;
}

.phase-bar {
  background: #52c41a;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  font-size: 10px;
  color: white;
}

.phase-green {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.phase-yellow {
  background: #faad14;
  padding: 2px 4px;
  border-radius: 0 0 4px 4px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-text {
  font-size: 16px;
  color: #666;
}
</style>
