<template>
  <div class="dashboard">
    <h1>交通仿真与绿波优化系统</h1>
    
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon">🚦</div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.networks }}</div>
          <div class="stat-label">路网数量</div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon">🚗</div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.simulations }}</div>
          <div class="stat-label">仿真任务</div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon">📊</div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.optimizations }}</div>
          <div class="stat-label">优化方案</div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon">📈</div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.reports }}</div>
          <div class="stat-label">分析报告</div>
        </div>
      </div>
    </div>
    
    <div class="quick-actions">
      <h2>快速操作</h2>
      <div class="actions-grid">
        <router-link to="/network" class="action-card">
          <div class="action-icon">🗺️</div>
          <div class="action-title">创建路网</div>
          <div class="action-desc">在地图上绘制新的路网</div>
        </router-link>
        
        <router-link to="/simulation" class="action-card">
          <div class="action-icon">▶️</div>
          <div class="action-title">运行仿真</div>
          <div class="action-desc">启动交通流仿真</div>
        </router-link>
        
        <router-link to="/optimization" class="action-card">
          <div class="action-icon">⚡</div>
          <div class="action-title">信号优化</div>
          <div class="action-desc">优化信号配时方案</div>
        </router-link>
        
        <router-link to="/analysis" class="action-card">
          <div class="action-icon">📊</div>
          <div class="action-title">查看报告</div>
          <div class="action-desc">分析仿真结果</div>
        </router-link>
      </div>
    </div>
    
    <div class="recent-activity">
      <h2>最近活动</h2>
      <div class="activity-list">
        <div v-for="activity in recentActivities" :key="activity.id" class="activity-item">
          <div class="activity-icon">{{ activity.icon }}</div>
          <div class="activity-content">
            <div class="activity-title">{{ activity.title }}</div>
            <div class="activity-time">{{ activity.time }}</div>
          </div>
        </div>
        <div v-if="recentActivities.length === 0" class="empty-state">
          暂无活动记录
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { networkApi, simulationApi, optimizationApi } from '../api'

const stats = ref({
  networks: 0,
  simulations: 0,
  optimizations: 0,
  reports: 0
})

const recentActivities = ref<Array<{ id: number; icon: string; title: string; time: string }>>([])
const loading = ref(true)

onMounted(async () => {
  loading.value = true
  try {
    const [networksRes, simulationsRes, optimizationsRes] = await Promise.allSettled([
      networkApi.list(),
      simulationApi.list(),
      optimizationApi.getResults()
    ])

    if (networksRes.status === 'fulfilled') {
      const data = networksRes.value.data
      stats.value.networks = data.count || data.results?.length || data.length || 0
    }
    if (simulationsRes.status === 'fulfilled') {
      const data = simulationsRes.value.data
      stats.value.simulations = data.count || data.results?.length || data.length || 0
    }
    if (optimizationsRes.status === 'fulfilled') {
      const data = optimizationsRes.value.data
      stats.value.optimizations = data.count || data.results?.length || data.length || 0
    }

    const activities: Array<{ id: number; icon: string; title: string; time: string }> = []
    if (networksRes.status === 'fulfilled') {
      const nets = networksRes.value.data.results || networksRes.value.data || []
      nets.slice(0, 3).forEach((n: any, i: number) => {
        activities.push({
          id: i + 1,
          icon: '🚦',
          title: `路网: ${n.name}`,
          time: n.created_at ? new Date(n.created_at).toLocaleString('zh-CN') : ''
        })
      })
    }
    if (simulationsRes.status === 'fulfilled') {
      const sims = simulationsRes.value.data.results || simulationsRes.value.data || []
      sims.slice(0, 2).forEach((s: any, i: number) => {
        const statusText = s.status === 'completed' ? '完成' : s.status === 'running' ? '运行中' : s.status
        activities.push({
          id: 100 + i,
          icon: '▶️',
          title: `仿真 ${s.name || '#' + s.id}: ${statusText}`,
          time: s.created_at ? new Date(s.created_at).toLocaleString('zh-CN') : ''
        })
      })
    }
    recentActivities.value = activities
  } catch (e) {
    console.error('获取仪表盘数据失败:', e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.dashboard {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

h1 {
  margin-bottom: 32px;
  color: #1a1a1a;
}

h2 {
  margin-bottom: 16px;
  color: #333;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 48px;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.stat-icon {
  font-size: 32px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #1890ff;
}

.stat-label {
  color: #666;
  font-size: 14px;
}

.quick-actions {
  margin-bottom: 48px;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.action-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  text-decoration: none;
  color: inherit;
  transition: transform 0.2s, box-shadow 0.2s;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.action-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.action-icon {
  font-size: 32px;
  margin-bottom: 12px;
}

.action-title {
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 8px;
}

.action-desc {
  font-size: 14px;
  color: #666;
}

.recent-activity {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.activity-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 8px;
}

.activity-icon {
  font-size: 24px;
}

.activity-title {
  font-size: 14px;
}

.activity-time {
  font-size: 12px;
  color: #999;
}

.empty-state {
  text-align: center;
  color: #999;
  padding: 24px;
}
</style>
