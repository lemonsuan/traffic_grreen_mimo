/**
 * MapLayer — Leaflet地图管理
 * 职责: 初始化瓦片地图、框选工具、坐标转换、事件代理
 */
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet-draw'
import 'leaflet-draw/dist/leaflet.draw.css'

export interface MapLayerOptions {
  container: HTMLElement
  center?: [number, number]
  zoom?: number
  onBboxSelect?: (bbox: { south: number; west: number; north: number; east: number }) => void
  onClick?: (latlng: L.LatLng) => void
}

export class MapLayer {
  map: L.Map
  private drawControl: L.Control.Draw | null = null
  private drawnItems: L.FeatureGroup

  constructor(options: MapLayerOptions) {
    const { container, center = [35.096, 118.352], zoom = 14, onBboxSelect, onClick } = options

    // 创建地图
    this.map = L.map(container, {
      center,
      zoom,
      zoomControl: false,  // 隐藏默认控件(工业风自定义)
      attributionControl: false,
    })

    // OSM瓦片层
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
    }).addTo(this.map)

    // 绘制层
    this.drawnItems = new L.FeatureGroup()
    this.map.addLayer(this.drawnItems)

    // 框选工具
    if (onBboxSelect) {
      this.drawControl = new L.Control.Draw({
        draw: {
          rectangle: {
            shapeOptions: {
              color: '#38bdf8',
              weight: 2,
              fillOpacity: 0.1,
            }
          },
          polygon: false,
          polyline: false,
          marker: false,
          circle: false,
          circlemarker: false,
        },
        edit: {
          featureGroup: this.drawnItems,
          edit: false,
          remove: false,
        }
      })
      this.map.addControl(this.drawControl)

      this.map.on(L.Draw.Event.CREATED, (e: any) => {
        this.drawnItems.clearLayers()
        this.drawnItems.addLayer(e.layer)
        const bounds = e.layer.getBounds()
        onBboxSelect({
          south: bounds.getSouth(),
          west: bounds.getWest(),
          north: bounds.getNorth(),
          east: bounds.getEast(),
        })
      })
    }

    // 点击事件
    if (onClick) {
      this.map.on('click', (e: L.LeafletMouseEvent) => {
        onClick(e.latlng)
      })
    }
  }

  /** 设置地图中心 */
  setCenter(lat: number, lng: number, zoom?: number) {
    this.map.setView([lat, lng], zoom)
  }

  /** 适应边界 */
  fitBounds(bounds: L.LatLngBoundsExpression, padding = 0.1) {
    this.map.fitBounds(bounds, { padding: [50, 50] })
  }

  /** 启用框选模式 */
  enableDraw() {
    if (this.drawControl) {
      // 触发矩形绘制
      new L.Draw.Rectangle(this.map, {
        shapeOptions: {
          color: '#38bdf8',
          weight: 2,
          fillOpacity: 0.1,
        }
      } as any).enable()
    }
  }

  /** 清除绘制 */
  clearDraw() {
    this.drawnItems.clearLayers()
  }

  /** 销毁 */
  dispose() {
    this.map.remove()
  }
}
