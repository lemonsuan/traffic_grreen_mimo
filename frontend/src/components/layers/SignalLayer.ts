/**
 * SignalLayer — 信号灯3D渲染层 (Three.js)
 * 信号灯: 灯柱 + 灯箱 + 红/绿/黄球体
 * 根据仿真时钟同步切换灯色
 */
import * as THREE from 'three'

interface SignalState {
  current_phase: number
  phase_elapsed: number
}

interface SignalPhases {
  phases: { green: number; yellow: number; all_red: number }[]
}

export class SignalLayer {
  private scene: THREE.Scene
  private signals: Map<string, THREE.Group> = new Map()
  private signalPhases: Map<string, SignalPhases> = new Map()
  private nodePositions: Map<string, { lat: number; lng: number }> = new Map()
  private latLngToScene: (lat: number, lng: number) => { x: number; z: number }

  constructor(scene: THREE.Scene, latLngToScene: (lat: number, lng: number) => { x: number; z: number }) {
    this.scene = scene
    this.latLngToScene = latLngToScene
  }

  /** 设置节点坐标 */
  setNodePositions(positions: Map<string, { lat: number; lng: number }>) {
    this.nodePositions = positions
  }

  /** 添加信号灯 */
  addSignal(nodeId: string, phases: { green: number; yellow: number; all_red: number }[]) {
    const pos = this.nodePositions.get(nodeId)
    if (!pos) return

    const scenePos = this.latLngToScene(pos.lat, pos.lng)

    const group = new THREE.Group()

    // 灯柱
    const poleGeo = new THREE.CylinderGeometry(0.2, 0.2, 6, 8)
    const poleMat = new THREE.MeshStandardMaterial({ color: 0x666666, roughness: 0.7, metalness: 0.5 })
    const pole = new THREE.Mesh(poleGeo, poleMat)
    pole.position.y = 3
    pole.castShadow = true
    group.add(pole)

    // 灯箱
    const boxGeo = new THREE.BoxGeometry(1.2, 3.5, 0.8)
    const boxMat = new THREE.MeshStandardMaterial({ color: 0x333333, roughness: 0.8 })
    const box = new THREE.Mesh(boxGeo, boxMat)
    box.position.y = 7
    box.castShadow = true
    group.add(box)

    // 红灯
    const redLight = this.createLight(0xff0000)
    redLight.position.set(0, 8.2, 0.5)
    redLight.name = 'red'
    group.add(redLight)

    // 黄灯
    const yellowLight = this.createLight(0xffd700)
    yellowLight.position.set(0, 7, 0.5)
    yellowLight.name = 'yellow'
    group.add(yellowLight)

    // 绿灯
    const greenLight = this.createLight(0x00ff00)
    greenLight.position.set(0, 5.8, 0.5)
    greenLight.name = 'green'
    group.add(greenLight)

    group.position.set(scenePos.x, 0, scenePos.z)
    group.userData = { type: 'signal', nodeId }

    this.scene.add(group)
    this.signals.set(nodeId, group)
    this.signalPhases.set(nodeId, { phases })
  }

  private createLight(color: number): THREE.Mesh {
    const geometry = new THREE.SphereGeometry(0.4, 16, 16)
    const material = new THREE.MeshStandardMaterial({
      color,
      emissive: color,
      emissiveIntensity: 0,
    })
    return new THREE.Mesh(geometry, material)
  }

  /** 更新信号状态 */
  updateSignals(signals: Record<string, { current_phase: number; phase_elapsed: number }>) {
    for (const [nodeId, state] of Object.entries(signals)) {
      const group = this.signals.get(nodeId)
      const phaseData = this.signalPhases.get(nodeId)
      if (!group || !phaseData) continue

      const phase = phaseData.phases[state.current_phase % phaseData.phases.length]
      if (!phase) continue

      const total = phase.green + phase.yellow + phase.all_red
      const elapsed = state.phase_elapsed % total

      let activeLight: 'red' | 'yellow' | 'green'
      if (elapsed < phase.green) activeLight = 'green'
      else if (elapsed < phase.green + phase.yellow) activeLight = 'yellow'
      else activeLight = 'red'

      // 更新灯光 emissiveIntensity
      group.children.forEach((child) => {
        if (child.name === 'red' || child.name === 'yellow' || child.name === 'green') {
          const mat = child.material as THREE.MeshStandardMaterial
          mat.emissiveIntensity = child.name === activeLight ? 1 : 0
        }
      })
    }
  }

  /** 清除 */
  clear() {
    for (const group of this.signals.values()) {
      this.scene.remove(group)
      group.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          child.geometry.dispose()
          ;(child.material as THREE.Material).dispose()
        }
      })
    }
    this.signals.clear()
    this.signalPhases.clear()
  }

  /** 销毁 */
  dispose() {
    this.clear()
  }
}
