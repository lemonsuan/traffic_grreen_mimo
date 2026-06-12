# AGENTS.md

## Project type

Smart city traffic control platform (智慧城市交通控制平台).

Backend: Django 4.x + Django REST Framework + SQLite  
Frontend: Vue 3 + Vite + TypeScript + Leaflet + Three.js

## Project structure

```
traffic_grreen/
├── backend/                        # Django backend
│   ├── config/                     # Project settings
│   ├── network/                    # Road network models + OSM + channelization
│   │   ├── models.py               # 13 models: Network, Node, Edge, Lane, Signal, Phase...
│   │   ├── views.py                # 11 ViewSets + custom actions
│   │   ├── generator.py            # Synthetic network generators (grid/corridor/city)
│   │   ├── demand.py               # Traffic demand generation
│   │   ├── osm_importer.py         # OSM Overpass API download + parse + import
│   │   ├── auto_channelize.py      # Auto channelization + phase generation
│   │   ├── micro_sim.py            # Single intersection micro-simulation
│   │   └── history.py              # Historical snapshot storage/query/compression
│   ├── simulation/                 # Traffic simulation engine (IDM model)
│   │   ├── engine.py               # SimulationEngine with IDM car-following
│   │   └── views.py                # Simulation API (start/stop/step_batch)
│   ├── optimization/               # Three-level optimization (11 algorithms)
│   │   ├── intersection/           # Level 1: webster, hcm, actuated, adaptive
│   │   ├── corridor/               # Level 2: maxband, passer, ga, pso
│   │   ├── network/                # Level 3: transyt, scoot, nsga
│   │   └── pipeline.py             # Auto-optimize pipeline
│   └── analysis/                   # Performance analysis + reports
├── frontend/                       # Vue 3 frontend
│   └── src/
│       ├── views/
│       │   ├── NetworkList.vue     # Network list page
│       │   └── NetworkWorkspace.vue # Network workspace (map + sim + opt)
│       ├── components/
│       │   ├── TopBar.vue          # Top status bar
│       │   ├── ToolSidebar.vue     # Left tool sidebar
│       │   ├── BottomBar.vue       # Bottom timeline player + metrics
│       │   ├── NetworkCard.vue     # Network list card
│       │   ├── IntersectionEditor.vue # Intersection config popup (4 tabs)
│       │   └── layers/             # Map layer system
│       │       ├── MapLayer.ts     # Leaflet map + draw tools
│       │       ├── NetworkLayer.ts # Road network rendering
│       │       ├── VehicleLayer.ts # Vehicle animation overlay
│       │       └── SignalLayer.ts  # Signal state display
│       ├── stores/
│       │   ├── app.ts              # Global UI state
│       │   ├── network.ts          # Network CRUD state
│       │   └── simulation.ts       # Simulation state + polling
│       └── api/
│           └── index.ts            # Axios API client
└── AGENTS.md
```

## Common commands

```bash
# Backend
cd backend
python manage.py runserver           # Dev server
python manage.py makemigrations      # Create migrations
python manage.py migrate             # Apply migrations
python manage.py test                # Run tests (24 tests)
python manage.py e2e_test            # End-to-end simulation test
python manage.py osm_linyi           # OSM import Linyi road network

# Frontend
cd frontend
npm install                          # Install dependencies
npm run dev                          # Dev server (port 5173)
npm run build                        # Production build
npx vue-tsc --noEmit                 # TypeScript check
```

## API endpoints

```
# Network CRUD
GET/POST   /api/v1/networks/                     # List/Create
GET/PUT/DELETE /api/v1/networks/{id}/             # Detail
POST       /api/v1/networks/generate/             # Generate grid/corridor/city
POST       /api/v1/networks/from_bbox/            # OSM import + auto channelize
POST       /api/v1/networks/{id}/auto_channelize/ # Re-channelize
POST       /api/v1/networks/{id}/clone/           # Clone network
POST       /api/v1/networks/{id}/import_network/  # Import JSON
POST       /api/v1/networks/{id}/export_network/  # Export JSON

# History
GET        /api/v1/networks/{id}/history/         # Query snapshots
GET        /api/v1/networks/{id}/history/at/      # Snapshot at time
GET        /api/v1/networks/{id}/history/intersection/ # Intersection history
GET        /api/v1/networks/{id}/history/dates/   # Available dates

# Intersection
GET        /api/v1/networks/intersections/{id}/full_detail/        # Full data
POST       /api/v1/networks/intersections/{id}/update_channelization/ # Rebuild phases
POST       /api/v1/networks/intersections/{id}/micro_sim/          # Single intersection sim

# Simulation
POST       /api/v1/simulation/start/              # Start simulation
POST       /api/v1/simulation/{id}/step_batch/    # Batch step (fast forward)
POST       /api/v1/simulation/{id}/stop/          # Stop simulation
GET        /api/v1/simulation/{id}/state/         # Get current state

# Optimization
POST       /api/v1/optimization/intersection/     # Single intersection
POST       /api/v1/optimization/corridor/         # Corridor green wave
POST       /api/v1/optimization/network/          # Network optimization
POST       /api/v1/optimization/auto_optimize/    # Auto-optimize pipeline
```

## Key conventions

- Models use Chinese verbose names
- API uses ViewSet + Router pattern
- Optimization algorithms registered via OptimizerFactory (self-registration at import)
- Three optimization levels: intersection, corridor, network
- Lane-level data model: Edge → Lane → LaneConnection
- Signal phases support arrow lights and round lights
- Auto channelization: intersection type detection + lane allocation + phase generation
- Historical snapshots: simulation/detector data stored per-second, queryable by date

## Architecture decisions

- **Leaflet + Three.js overlay**: Leaflet for map tiles + interaction, Three.js for 3D rendering overlay
- **Multi-network management**: NetworkList → select → NetworkWorkspace (all ops scoped to network)
- **Intersection editor popup**: Click node → 4-tab popup (channel/phase/sim/metrics)
- **Auto channelization**: Lane changes auto-rebuild phases (PhaseLane mapping)
- **IDM car-following model**: Intelligent Driver Model for realistic vehicle behavior
- **History snapshots**: All simulation results stored for time-travel playback
- **Industrial dark UI**: Deep charcoal base, cyan/amber accents, JetBrains Mono font
