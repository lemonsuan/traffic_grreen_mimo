# 交通仿真与绿波优化系统

Traffic Simulation and Green Wave Optimization System

## 功能概述

- **路网建模**: 创建和管理交通路网，包括交叉口、路段、车道、信号灯等
- **交通仿真**: 基于微观跟车模型的交通流仿真，支持实时状态监控
- **信号优化**: 三级优化体系 — 单点交叉口、干线绿波、区域路网
- **数据分析**: 性能指标分析、多算法对比、Pareto 前沿可视化

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Django 4.x + Django REST Framework + SQLite |
| 前端 | Vue 3 + Vite + TypeScript + Three.js + ECharts |
| 优化算法 | NumPy + SciPy |

## 优化算法

### Level 1: 单点交叉口
| 算法 | 说明 |
|------|------|
| Webster | 经典 Webster 配时方法 |
| HCM | HCM 第六版延误最小化 |
| 感应控制 | 基于车辆检测器的实时相位切换 |
| 自适应 | SCOOT/SCATS 简化版自适应控制 |

### Level 2: 干线绿波
| 算法 | 说明 |
|------|------|
| MAXBAND | 绿波带宽最大化 (线性规划) |
| PASSER-II | 多流向加权带宽优化 |
| 遗传算法 | SBX 交叉 + 多项式变异 |
| 粒子群优化 | 线性递减惯性权重 PSO |

### Level 3: 区域路网
| 算法 | 说明 |
|------|------|
| TRANSYT | Robertson 车队离散 + 爬山法 |
| SCOOT | 实时三阶段增量微调 |
| NSGA-II | 三目标进化算法 (延误/停车/吞吐量) |

## 快速开始

### 后端

```bash
cd backend
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 `http://localhost:5173`，后端运行在 `http://localhost:8000`。

## API 端点

```
/api/v1/networks/           # 路网 CRUD
/api/v1/simulation/         # 仿真控制
/api/v1/optimization/       # 信号优化
/api/v1/analysis/           # 性能分析
```

## 项目结构

```
traffic_grreen/
├── backend/                    # Django 后端
│   ├── config/                 # 项目配置
│   ├── network/                # 路网模型
│   ├── simulation/             # 仿真引擎
│   ├── optimization/           # 三级优化
│   │   ├── intersection/       #   单点交叉口
│   │   ├── corridor/           #   干线绿波
│   │   └── network/            #   区域路网
│   └── analysis/               # 性能分析
├── frontend/                   # Vue 3 前端
│   └── src/
│       ├── api/                # API 客户端
│       ├── views/              # 页面视图
│       ├── stores/             # Pinia 状态管理
│       ├── three/              # Three.js 3D 渲染
│       └── router/             # 路由配置
└── AGENTS.md
```

## License

MIT
