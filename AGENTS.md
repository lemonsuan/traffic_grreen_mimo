# AGENTS.md

## Project type

Traffic simulation and green wave optimization system (交通仿真与绿波优化系统).

Backend: Django 4.x + Django REST Framework + SQLite  
Frontend: Vue 3 + Vite + TypeScript + Three.js

## Project structure

```
traffic_grreen/
├── backend/                    # Django backend
│   ├── config/                 # Project settings
│   ├── network/                # Road network models
│   ├── simulation/             # Traffic simulation engine
│   ├── optimization/           # Three-level optimization
│   │   ├── intersection/       # Level 1: Single intersection
│   │   ├── corridor/           # Level 2: Green wave corridor
│   │   └── network/            # Level 3: Regional network
│   └── analysis/               # Performance analysis
├── frontend/                   # Vue 3 frontend (TODO)
└── AGENTS.md
```

## Common commands

```bash
# Navigate to backend directory first
cd backend

# Run dev server
python manage.py runserver

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run tests
python manage.py test

# Django shell
python manage.py shell
```

## API endpoints

```
/api/v1/networks/           # Road network CRUD
/api/v1/simulation/         # Simulation control
/api/v1/optimization/       # Signal optimization
/api/v1/analysis/           # Performance analysis
```

## Key conventions

- Models use Chinese verbose names
- API uses ViewSet + Router pattern
- Optimization algorithms registered via OptimizerFactory
- Three optimization levels: intersection, corridor, network

## Optimization algorithms

### Level 1: Intersection (单点交叉口)
- webster: Webster classic timing
- hcm: HCM delay minimization
- actuated: Actuated control
- adaptive: Adaptive control
- rl: Reinforcement learning (TODO)

### Level 2: Corridor (干线绿波)
- maxband: MAXBAND bandwidth maximization
- passer: PASSER-II weighted bandwidth (scipy LP)
- ga: Genetic algorithm (SBX crossover)
- pso: Particle swarm optimization

### Level 3: Network (区域路网)
- transyt: TRANSYT hill-climbing with platoon dispersion
- scoot: SCOOT real-time adaptive (cycle/green/offset)
- nsga: NSGA-II multi-objective (Pareto front)
