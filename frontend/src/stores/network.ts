import { defineStore } from 'pinia'
import { ref } from 'vue'
import { networkApi } from '../api'

export interface Network {
  id: number
  name: string
  description: string
  srid: number
  created_at: string
  updated_at: string
}

export interface Node {
  id: number
  network: number
  node_id: string
  name: string
  node_type: string
  lng: number
  lat: number
  x: number
  y: number
  z: number
}

export interface Edge {
  id: number
  network: number
  edge_id: string
  from_node: number
  to_node: number
  length: number
  speed_limit: number
  lanes_count: number
  capacity: number
  road_class: string
  is_oneway: boolean
}

export interface Signal {
  id: number
  node: number
  signal_id: string
  cycle_length: number
  offset: number
  control_mode: string
}

export const useNetworkStore = defineStore('network', () => {
  const networks = ref<Network[]>([])
  const currentNetwork = ref<any>(null)
  const nodes = ref<Node[]>([])
  const edges = ref<Edge[]>([])
  const signals = ref<Signal[]>([])
  const loading = ref(false)

  async function fetchNetworks() {
    loading.value = true
    try {
      const res = await networkApi.list()
      networks.value = res.data.results || res.data
    } catch (e) {
      console.error('获取路网列表失败:', e)
    } finally {
      loading.value = false
    }
  }

  async function fetchNetworkDetail(id: number) {
    loading.value = true
    try {
      const res = await networkApi.get(id)
      currentNetwork.value = res.data
      nodes.value = res.data.nodes || []
      edges.value = res.data.edges || []
      signals.value = res.data.signals || []
    } catch (e) {
      console.error('获取路网详情失败:', e)
    } finally {
      loading.value = false
    }
  }

  async function createNetwork(data: Partial<Network>) {
    try {
      const res = await networkApi.create(data)
      networks.value.push(res.data)
      return res.data
    } catch (e) {
      console.error('创建路网失败:', e)
      throw e
    }
  }

  async function createNode(data: Partial<Node>) {
    try {
      const res = await networkApi.createNode(data)
      nodes.value.push(res.data)
      return res.data
    } catch (e) {
      console.error('创建节点失败:', e)
      throw e
    }
  }

  async function createEdge(data: Partial<Edge>) {
    try {
      const res = await networkApi.createEdge(data)
      edges.value.push(res.data)
      return res.data
    } catch (e) {
      console.error('创建路段失败:', e)
      throw e
    }
  }

  async function deleteNode(id: number) {
    try {
      await networkApi.deleteNode(id)
      nodes.value = nodes.value.filter(n => n.id !== id)
    } catch (e) {
      console.error('删除节点失败:', e)
      throw e
    }
  }

  async function deleteEdge(id: number) {
    try {
      await networkApi.deleteEdge(id)
      edges.value = edges.value.filter(e => e.id !== id)
    } catch (e) {
      console.error('删除路段失败:', e)
      throw e
    }
  }

  async function importNetwork(id: number, data: any) {
    try {
      const res = await networkApi.importNetwork(id, data)
      await fetchNetworkDetail(id)
      return res.data
    } catch (e) {
      console.error('导入路网失败:', e)
      throw e
    }
  }

  async function exportNetwork(id: number) {
    try {
      const res = await networkApi.exportNetwork(id)
      return res.data
    } catch (e) {
      console.error('导出路网失败:', e)
      throw e
    }
  }

  return {
    networks, currentNetwork, nodes, edges, signals, loading,
    fetchNetworks, fetchNetworkDetail, createNetwork,
    createNode, createEdge, deleteNode, deleteEdge,
    importNetwork, exportNetwork
  }
})
