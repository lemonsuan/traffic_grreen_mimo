import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// Network API
export const networkApi = {
  list: () => api.get('/networks/'),
  get: (id: number) => api.get(`/networks/${id}/`),
  create: (data: any) => api.post('/networks/', data),
  update: (id: number, data: any) => api.put(`/networks/${id}/`, data),
  delete: (id: number) => api.delete(`/networks/${id}/`),

  // Auto generate
  generate: (type: string, params: any) => api.post('/networks/generate/', { type, params }),

  // Clone
  clone: (id: number, name?: string) => api.post(`/networks/${id}/clone/`, { name }),

  // Nodes
  listNodes: (params?: any) => api.get('/networks/nodes/', { params }),
  getNode: (id: number) => api.get(`/networks/nodes/${id}/`),
  createNode: (data: any) => api.post('/networks/nodes/', data),
  updateNode: (id: number, data: any) => api.put(`/networks/nodes/${id}/`, data),
  deleteNode: (id: number) => api.delete(`/networks/nodes/${id}/`),

  // Edges
  listEdges: (params?: any) => api.get('/networks/edges/', { params }),
  getEdge: (id: number) => api.get(`/networks/edges/${id}/`),
  createEdge: (data: any) => api.post('/networks/edges/', data),
  updateEdge: (id: number, data: any) => api.put(`/networks/edges/${id}/`, data),
  deleteEdge: (id: number) => api.delete(`/networks/edges/${id}/`),

  // Signals
  listSignals: (params?: any) => api.get('/networks/signals/', { params }),
  getSignal: (id: number) => api.get(`/networks/signals/${id}/`),
  createSignal: (data: any) => api.post('/networks/signals/', data),
  updateSignal: (id: number, data: any) => api.put(`/networks/signals/${id}/`, data),
  deleteSignal: (id: number) => api.delete(`/networks/signals/${id}/`),

  // Import/Export
  importNetwork: (id: number, data: any) => api.post(`/networks/${id}/import_network/`, data),
  exportNetwork: (id: number) => api.post(`/networks/${id}/export_network/`, {})
}

// Simulation API
export const simulationApi = {
  list: () => api.get('/simulation/'),
  get: (id: number) => api.get(`/simulation/${id}/`),
  start: (data: any) => api.post('/simulation/start/', data),
  stop: (id: number) => api.post(`/simulation/${id}/stop/`),
  pause: (id: number) => api.post(`/simulation/${id}/pause/`),
  resume: (id: number) => api.post(`/simulation/${id}/resume/`),
  getState: (id: number) => api.get(`/simulation/${id}/state/`),
  getSnapshots: (id: number) => api.get(`/simulation/${id}/snapshots/`),
  getMetrics: (id: number) => api.get(`/simulation/${id}/metrics/`)
}

// Optimization API
export const optimizationApi = {
  getAlgorithms: (level?: string) => api.get('/optimization/algorithms/', { params: { level } }),

  optimizeIntersection: (data: any) => api.post('/optimization/intersection/', data),
  optimizeCorridor: (data: any) => api.post('/optimization/corridor/', data),
  optimizeNetwork: (data: any) => api.post('/optimization/network/', data),
  autoOptimize: (networkId: number) => api.post('/optimization/auto_optimize/', { network_id: networkId }),

  getResults: (params?: any) => api.get('/optimization/results/', { params }),
  getResult: (id: number) => api.get(`/optimization/results/${id}/`),
  applyResult: (id: number) => api.post(`/optimization/results/${id}/apply/`),

  compare: (resultIds: number[]) => api.get('/optimization/compare/', { params: { result_ids: resultIds } })
}

// Analysis API
export const analysisApi = {
  getMetrics: (params: any) => api.get('/analysis/metrics/', { params }),
  getReports: (params?: any) => api.get('/analysis/reports/', { params }),
  getReport: (id: number) => api.get(`/analysis/reports/${id}/`),
  generateReport: (networkId: number, type: string) => api.post('/analysis/generate_report/', { network_id: networkId, type }),
  compare: (resultIds: number[], metrics: string[]) =>
    api.post('/analysis/compare/', { result_ids: resultIds, metrics }),
  exportReport: (networkId: number, type: string, format: string) =>
    api.get('/analysis/export/', { params: { network_id: networkId, type, format } })
}

export default api
