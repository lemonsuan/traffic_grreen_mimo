import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { simulationApi } from '../api'

export interface Vehicle {
  id: string
  link_id: string
  lane: number
  position: number
  speed: number
  stops: number
}

export interface SignalState {
  current_phase: number
  phase_elapsed: number
}

export interface SimulationMetrics {
  avg_delay: number
  avg_queue_length: number
  max_queue_length: number
  throughput: number
  avg_stops: number
}

export interface SimulationConfig {
  network_id: number
  duration: number
  step_size: number
  speed_multiplier: number
  random_seed?: number
}

export const useSimulationStore = defineStore('simulation', () => {
  const simulationId = ref<number | null>(null)
  const status = ref<'idle' | 'running' | 'paused' | 'completed'>('idle')
  const currentTime = ref(0)
  const duration = ref(3600)
  const vehicles = ref<Vehicle[]>([])
  const signals = ref<Record<string, SignalState>>({})
  const metrics = ref<SimulationMetrics>({
    avg_delay: 0,
    avg_queue_length: 0,
    max_queue_length: 0,
    throughput: 0,
    avg_stops: 0
  })

  let pollTimer: ReturnType<typeof setInterval> | null = null

  const progress = computed(() =>
    duration.value > 0 ? (currentTime.value / duration.value) * 100 : 0
  )
  const vehicleCount = computed(() => vehicles.value.length)
  const isRunning = computed(() => status.value === 'running')

  async function startSimulation(config: SimulationConfig) {
    try {
      const res = await simulationApi.start(config)
      simulationId.value = res.data.simulation_id
      status.value = 'running'
      currentTime.value = 0
      duration.value = config.duration
      startPolling()
      return res.data
    } catch (e) {
      console.error('启动仿真失败:', e)
      throw e
    }
  }

  async function stopSimulation() {
    if (!simulationId.value) return
    stopPolling()
    try {
      const res = await simulationApi.stop(simulationId.value)
      status.value = 'completed'
      if (res.data.results) {
        updateMetrics(res.data.results.metrics || {})
      }
      return res.data
    } catch (e) {
      console.error('停止仿真失败:', e)
      throw e
    }
  }

  async function pauseSimulation() {
    if (!simulationId.value) return
    stopPolling()
    try {
      await simulationApi.pause(simulationId.value)
      status.value = 'paused'
    } catch (e) {
      console.error('暂停仿真失败:', e)
      throw e
    }
  }

  async function resumeSimulation() {
    if (!simulationId.value) return
    try {
      await simulationApi.resume(simulationId.value)
      status.value = 'running'
      startPolling()
    } catch (e) {
      console.error('恢复仿真失败:', e)
      throw e
    }
  }

  async function fetchState() {
    if (!simulationId.value) return
    try {
      const res = await simulationApi.getState(simulationId.value)
      const data = res.data

      status.value = data.status

      if (data.state) {
        currentTime.value = data.state.time || 0
        vehicles.value = data.state.vehicles || []
        signals.value = data.state.signals || {}
        if (data.state.metrics) {
          updateMetrics(data.state.metrics)
        }
      } else {
        currentTime.value = data.current_time || 0
      }

      if (data.status === 'completed') {
        stopPolling()
      }
    } catch (e) {
      console.error('获取仿真状态失败:', e)
    }
  }

  function startPolling() {
    stopPolling()
    pollTimer = setInterval(fetchState, 1000)
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  function updateMetrics(data: any) {
    metrics.value = {
      avg_delay: data.avg_delay || 0,
      avg_queue_length: data.avg_queue_length || 0,
      max_queue_length: data.max_queue_length || 0,
      throughput: data.throughput || 0,
      avg_stops: data.avg_stops || 0
    }
  }

  function reset() {
    stopPolling()
    simulationId.value = null
    status.value = 'idle'
    currentTime.value = 0
    vehicles.value = []
    signals.value = {}
    metrics.value = {
      avg_delay: 0,
      avg_queue_length: 0,
      max_queue_length: 0,
      throughput: 0,
      avg_stops: 0
    }
  }

  return {
    simulationId, status, currentTime, duration,
    vehicles, signals, metrics, progress, vehicleCount, isRunning,
    startSimulation, stopSimulation, pauseSimulation,
    resumeSimulation, fetchState, reset
  }
})
