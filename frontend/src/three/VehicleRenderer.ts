/**
 * 车辆3D渲染器
 */

import * as THREE from 'three'

export interface VehicleState {
  id: string
  x: number
  y: number
  z: number
  rotation: number
  speed: number
  type: 'car' | 'truck' | 'bus'
}

export class VehicleRenderer {
  private scene: THREE.Scene
  private vehicles: Map<string, THREE.Group> = new Map()
  private vehiclePool: THREE.Group[] = []
  private maxPoolSize: number = 1000

  constructor(scene: THREE.Scene) {
    this.scene = scene
  }

  /**
   * 创建车辆模型
   */
  private createVehicleModel(type: 'car' | 'truck' | 'bus'): THREE.Group {
    const group = new THREE.Group()

    // 车身颜色
    const colors = {
      car: 0x4a90d9,
      truck: 0x8b4513,
      bus: 0xff8c00
    }

    const bodyMaterial = new THREE.MeshStandardMaterial({
      color: colors[type],
      roughness: 0.5,
      metalness: 0.3
    })

    // 车身
    let bodyGeometry: THREE.BufferGeometry
    let bodyHeight: number

    switch (type) {
      case 'car':
        bodyGeometry = new THREE.BoxGeometry(2, 1.2, 4)
        bodyHeight = 0.6
        break
      case 'truck':
        bodyGeometry = new THREE.BoxGeometry(2.5, 2, 6)
        bodyHeight = 1
        break
      case 'bus':
        bodyGeometry = new THREE.BoxGeometry(2.5, 2.5, 8)
        bodyHeight = 1.25
        break
    }

    const body = new THREE.Mesh(bodyGeometry, bodyMaterial)
    body.position.y = bodyHeight
    body.castShadow = true
    group.add(body)

    // 车顶 (轿车)
    if (type === 'car') {
      const roofGeometry = new THREE.BoxGeometry(1.8, 0.8, 2)
      const roof = new THREE.Mesh(roofGeometry, bodyMaterial)
      roof.position.set(0, 1.6, -0.3)
      roof.castShadow = true
      group.add(roof)
    }

    // 车轮
    const wheelGeometry = new THREE.CylinderGeometry(0.3, 0.3, 0.2, 16)
    const wheelMaterial = new THREE.MeshStandardMaterial({
      color: 0x333333,
      roughness: 0.8
    })

    const wheelPositions = [
      { x: -1, y: 0.3, z: 1.2 },
      { x: 1, y: 0.3, z: 1.2 },
      { x: -1, y: 0.3, z: -1.2 },
      { x: 1, y: 0.3, z: -1.2 }
    ]

    wheelPositions.forEach((pos) => {
      const wheel = new THREE.Mesh(wheelGeometry, wheelMaterial)
      wheel.position.set(pos.x, pos.y, pos.z)
      wheel.rotation.z = Math.PI / 2
      group.add(wheel)
    })

    // 车灯
    const headlightGeometry = new THREE.SphereGeometry(0.15, 8, 8)
    const headlightMaterial = new THREE.MeshStandardMaterial({
      color: 0xffff00,
      emissive: 0xffff00,
      emissiveIntensity: 0.5
    })

    const leftHeadlight = new THREE.Mesh(headlightGeometry, headlightMaterial)
    leftHeadlight.position.set(-0.7, 0.8, 2)
    group.add(leftHeadlight)

    const rightHeadlight = new THREE.Mesh(headlightGeometry, headlightMaterial)
    rightHeadlight.position.set(0.7, 0.8, 2)
    group.add(rightHeadlight)

    return group
  }

  /**
   * 获取或创建车辆
   */
  private getOrCreateVehicle(type: 'car' | 'truck' | 'bus'): THREE.Group {
    // 尝试从对象池获取
    if (this.vehiclePool.length > 0) {
      const vehicle = this.vehiclePool.pop()!
      vehicle.visible = true
      return vehicle
    }

    return this.createVehicleModel(type)
  }

  /**
   * 添加车辆
   */
  addVehicle(state: VehicleState): void {
    const vehicle = this.getOrCreateVehicle(state.type)
    vehicle.position.set(state.x, 0, state.y)
    vehicle.rotation.y = state.rotation
    vehicle.userData = { type: 'vehicle', id: state.id }

    this.scene.add(vehicle)
    this.vehicles.set(state.id, vehicle)
  }

  /**
   * 更新车辆状态
   */
  updateVehicle(state: VehicleState): void {
    const vehicle = this.vehicles.get(state.id)
    if (!vehicle) {
      this.addVehicle(state)
      return
    }

    // 平滑移动
    vehicle.position.x = state.x
    vehicle.position.z = state.y
    vehicle.rotation.y = state.rotation
  }

  /**
   * 移除车辆
   */
  removeVehicle(vehicleId: string): void {
    const vehicle = this.vehicles.get(vehicleId)
    if (vehicle) {
      vehicle.visible = false
      
      // 放回对象池
      if (this.vehiclePool.length < this.maxPoolSize) {
        this.vehiclePool.push(vehicle)
      } else {
        this.scene.remove(vehicle)
      }
      
      this.vehicles.delete(vehicleId)
    }
  }

  /**
   * 批量更新车辆
   */
  updateVehicles(states: VehicleState[]): void {
    const currentIds = new Set(states.map((s) => s.id))

    // 移除不在列表中的车辆
    const toRemove = [...this.vehicles.keys()].filter((id) => !currentIds.has(id))
    toRemove.forEach((id) => this.removeVehicle(id))

    // 更新或添加车辆
    states.forEach((state) => this.updateVehicle(state))
  }

  /**
   * 清除所有车辆
   */
  clear(): void {
    this.vehicles.forEach((vehicle) => {
      vehicle.visible = false
      if (this.vehiclePool.length < this.maxPoolSize) {
        this.vehiclePool.push(vehicle)
      } else {
        this.scene.remove(vehicle)
      }
    })
    this.vehicles.clear()
  }

  /**
   * 获取车辆数量
   */
  getVehicleCount(): number {
    return this.vehicles.size
  }

  /**
   * 高亮车辆
   */
  highlightVehicle(vehicleId: string, highlight: boolean = true): void {
    const vehicle = this.vehicles.get(vehicleId)
    if (vehicle) {
      vehicle.children.forEach((child) => {
        if (child instanceof THREE.Mesh) {
          const material = child.material as THREE.MeshStandardMaterial
          material.emissive.setHex(highlight ? 0x444444 : 0x000000)
        }
      })
    }
  }
}
