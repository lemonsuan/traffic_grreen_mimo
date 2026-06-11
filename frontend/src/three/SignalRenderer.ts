/**
 * 信号灯3D渲染器
 */

import * as THREE from 'three'

export interface SignalState {
  nodeId: string
  x: number
  y: number
  currentPhase: number
  phases: {
    index: number
    green: number
    yellow: number
    allRed: number
  }[]
}

export class SignalRenderer {
  private scene: THREE.Scene
  private signals: Map<string, THREE.Group> = new Map()

  constructor(scene: THREE.Scene) {
    this.scene = scene
  }

  /**
   * 创建信号灯模型
   */
  private createSignalModel(): THREE.Group {
    const group = new THREE.Group()

    // 灯柱
    const poleGeometry = new THREE.CylinderGeometry(0.3, 0.3, 6, 16)
    const poleMaterial = new THREE.MeshStandardMaterial({
      color: 0x666666,
      roughness: 0.7,
      metalness: 0.5
    })
    const pole = new THREE.Mesh(poleGeometry, poleMaterial)
    pole.position.y = 3
    pole.castShadow = true
    group.add(pole)

    // 灯箱
    const boxGeometry = new THREE.BoxGeometry(1.5, 4, 1)
    const boxMaterial = new THREE.MeshStandardMaterial({
      color: 0x333333,
      roughness: 0.8
    })
    const box = new THREE.Mesh(boxGeometry, boxMaterial)
    box.position.y = 7
    box.castShadow = true
    group.add(box)

    // 红灯
    const redLight = this.createLight(0xff0000, 0.4)
    redLight.position.set(0, 8.2, 0.6)
    redLight.name = 'red'
    group.add(redLight)

    // 黄灯
    const yellowLight = this.createLight(0xffd700, 0.4)
    yellowLight.position.set(0, 7, 0.6)
    yellowLight.name = 'yellow'
    group.add(yellowLight)

    // 绿灯
    const greenLight = this.createLight(0x00ff00, 0.4)
    greenLight.position.set(0, 5.8, 0.6)
    greenLight.name = 'green'
    group.add(greenLight)

    return group
  }

  /**
   * 创建单个灯
   */
  private createLight(color: number, radius: number): THREE.Mesh {
    const geometry = new THREE.SphereGeometry(radius, 16, 16)
    const material = new THREE.MeshStandardMaterial({
      color: color,
      emissive: color,
      emissiveIntensity: 0
    })
    return new THREE.Mesh(geometry, material)
  }

  /**
   * 添加信号灯
   */
  addSignal(state: SignalState): void {
    const signal = this.createSignalModel()
    signal.position.set(state.x, 0, state.y)
    signal.userData = { type: 'signal', nodeId: state.nodeId }

    this.scene.add(signal)
    this.signals.set(state.nodeId, signal)

    // 设置初始状态
    this.updateSignal(state)
  }

  /**
   * 更新信号灯状态
   */
  updateSignal(state: SignalState): void {
    const signal = this.signals.get(state.nodeId)
    if (!signal) return

    // 获取当前相位
    const currentPhase = state.phases[state.currentPhase]
    if (!currentPhase) return

    // 计算当前相位的状态
    const totalPhaseTime = currentPhase.green + currentPhase.yellow + currentPhase.allRed
    const phaseElapsed = Date.now() / 1000 % totalPhaseTime

    let activeLight: 'red' | 'yellow' | 'green'

    if (phaseElapsed < currentPhase.green) {
      activeLight = 'green'
    } else if (phaseElapsed < currentPhase.green + currentPhase.yellow) {
      activeLight = 'yellow'
    } else {
      activeLight = 'red'
    }

    // 更新灯光显示
    signal.children.forEach((child) => {
      if (child.name === 'red' || child.name === 'yellow' || child.name === 'green') {
        const material = child.material as THREE.MeshStandardMaterial
        material.emissiveIntensity = child.name === activeLight ? 1 : 0
      }
    })
  }

  /**
   * 批量更新信号灯
   */
  updateSignals(states: SignalState[]): void {
    states.forEach((state) => this.updateSignal(state))
  }

  /**
   * 移除信号灯
   */
  removeSignal(nodeId: string): void {
    const signal = this.signals.get(nodeId)
    if (signal) {
      this.scene.remove(signal)
      this.signals.delete(nodeId)
    }
  }

  /**
   * 清除所有信号灯
   */
  clear(): void {
    this.signals.forEach((signal) => this.scene.remove(signal))
    this.signals.clear()
  }

  /**
   * 设置信号灯可见性
   */
  setVisibility(nodeId: string, visible: boolean): void {
    const signal = this.signals.get(nodeId)
    if (signal) {
      signal.visible = visible
    }
  }
}
