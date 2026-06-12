/**
 * VehicleLayer — 车辆3D渲染层 (Three.js)
 * 在 Three.js 场景中渲染车辆模型，lerp 平滑移动
 * 叠加在 Leaflet 瓦片地图上方
 */
import * as THREE from 'three'

export interface VehicleData {
  id: string
  from_node: string
  to_node: string
  position: number
  edge_length: number
  speed: number
  link_id: string
}

interface NodePos { lat: number; lng: number }

export class VehicleLayer {
  private scene: THREE.Scene
  private vehicles: Map<string, THREE.Mesh> = new Map()
  private nodePositions: Map<string, NodePos> = new Map()
  private vehicleGeometry: THREE.BoxGeometry
  private vehicleMaterials: {
    fast: THREE.MeshStandardMaterial
    slow: THREE.MeshStandardMaterial
    stopped: THREE.MeshStandardMaterial
  }
  private visible = true
  private latLngToScene: (lat: number, lng: number) => { x: number; z: number }

  constructor(scene: THREE.Scene, latLngToScene: (lat: number, lng: number) => { x: number; z: number }) {
    this.scene = scene
    this.latLngToScene = latLngToScene

    // 车辆几何体(小盒子)
    this.vehicleGeometry = new THREE.BoxGeometry(1.5, 1, 3)

    // 三种速度状态的材质
    this.vehicleMaterials = {
      fast: new THREE.MeshStandardMaterial({ color: 0x22c55e, roughness: 0.5 }),    // 绿色 畅通
      slow: new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.5 }),    // 黄色 缓行
      stopped: new THREE.MeshStandardMaterial({ color: 0xef4444, roughness: 0.5 }), // 红色 拥堵
    }
  }

  /** 设置节点坐标映射 */
  setNodePositions(positions: Map<string, NodePos>) {
    this.nodePositions = positions
  }

  /** 批量更新车辆位置 */
  updateVehicles(vehicles: VehicleData[]) {
    const currentIds = new Set(vehicles.map(v => v.id))

    // 移除不在列表中的车辆
    for (const [id, mesh] of this.vehicles) {
      if (!currentIds.has(id)) {
        this.scene.remove(mesh)
        mesh.geometry.dispose()
        this.vehicles.delete(id)
      }
    }

    // 更新或添加车辆
    for (const v of vehicles) {
      let mesh = this.vehicles.get(v.id)

      if (!mesh) {
        mesh = new THREE.Mesh(this.vehicleGeometry, this.vehicleMaterials.fast.clone())
        mesh.castShadow = true
        this.scene.add(mesh)
        this.vehicles.set(v.id, mesh)
      }

      // 计算目标位置
      const fromPos = this.nodePositions.get(v.from_node)
      const toPos = this.nodePositions.get(v.to_node)

      if (fromPos && toPos) {
        const progress = Math.min(Math.max(v.position / (v.edge_length || 100), 0), 1)
        const lat = fromPos.lat + (toPos.lat - fromPos.lat) * progress
        const lng = fromPos.lng + (toPos.lng - fromPos.lng) * progress
        const scenePos = this.latLngToScene(lat, lng)

        // lerp 平滑移动
        mesh.position.x += (scenePos.x - mesh.position.x) * 0.3
        mesh.position.z += (scenePos.z - mesh.position.z) * 0.3
        mesh.position.y = 0.5

        // 朝向
        const angle = Math.atan2(
          toPos.lng - fromPos.lng,
          toPos.lat - fromPos.lat
        )
        mesh.rotation.y += (angle - mesh.rotation.y) * 0.3
      }

      // 根据速度切换材质颜色
      const speed = v.speed || 0
      const targetMat = speed > 40 ? this.vehicleMaterials.fast
        : speed > 20 ? this.vehicleMaterials.slow
        : this.vehicleMaterials.stopped

      if ((mesh.material as THREE.MeshStandardMaterial).color !== targetMat.color) {
        mesh.material = targetMat.clone()
      }
    }
  }

  /** 设置可见性 */
  setVisible(visible: boolean) {
    this.visible = visible
    for (const mesh of this.vehicles.values()) {
      mesh.visible = visible
    }
  }

  /** 清除所有车辆 */
  clear() {
    for (const mesh of this.vehicles.values()) {
      this.scene.remove(mesh)
      mesh.geometry.dispose()
    }
    this.vehicles.clear()
  }

  /** 销毁 */
  dispose() {
    this.clear()
    this.vehicleGeometry.dispose()
    Object.values(this.vehicleMaterials).forEach(m => m.dispose())
  }
}
