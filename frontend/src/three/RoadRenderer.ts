/**
 * 路网3D渲染器
 */

import * as THREE from 'three'

export interface RoadNode {
  id: string
  x: number
  y: number
  type: 'intersection' | 'roundabout'
}

export interface RoadEdge {
  id: string
  from: string
  to: string
  lanes: number
  width: number
}

export class RoadRenderer {
  private scene: THREE.Scene
  private nodes: Map<string, THREE.Mesh> = new Map()
  private edges: Map<string, THREE.Group> = new Map()

  constructor(scene: THREE.Scene) {
    this.scene = scene
  }

  /**
   * 添加节点
   */
  addNode(node: RoadNode): void {
    const geometry = new THREE.CylinderGeometry(15, 15, 5, 32)
    const material = new THREE.MeshStandardMaterial({
      color: node.type === 'intersection' ? 0x1890ff : 0x52c41a,
      roughness: 0.7
    })

    const mesh = new THREE.Mesh(geometry, material)
    mesh.position.set(node.x, 2.5, node.y)
    mesh.castShadow = true
    mesh.userData = { type: 'node', id: node.id }

    this.scene.add(mesh)
    this.nodes.set(node.id, mesh)
  }

  /**
   * 添加路段
   */
  addEdge(edge: RoadEdge, fromNode: RoadNode, toNode: RoadNode): void {
    const group = new THREE.Group()

    // 计算路段方向和长度
    const dx = toNode.x - fromNode.x
    const dy = toNode.y - fromNode.y
    const length = Math.sqrt(dx * dx + dy * dy)
    const angle = Math.atan2(dx, dy)

    // 创建路面
    const roadWidth = edge.lanes * 3.5
    const roadGeometry = new THREE.PlaneGeometry(roadWidth, length)
    const roadMaterial = new THREE.MeshStandardMaterial({
      color: 0x333333,
      roughness: 0.9
    })

    const road = new THREE.Mesh(roadGeometry, roadMaterial)
    road.rotation.x = -Math.PI / 2
    road.rotation.z = -angle
    road.position.set(
      (fromNode.x + toNode.x) / 2,
      0.1,
      (fromNode.y + toNode.y) / 2
    )
    road.receiveShadow = true
    group.add(road)

    // 添加车道线
    this.addLaneLines(group, fromNode, toNode, edge.lanes, length, angle)

    // 添加边框
    this.addRoadBorders(group, fromNode, toNode, roadWidth, length, angle)

    group.userData = { type: 'edge', id: edge.id }
    this.scene.add(group)
    this.edges.set(edge.id, group)
  }

  /**
   * 添加车道线
   */
  private addLaneLines(
    group: THREE.Group,
    from: RoadNode,
    to: RoadNode,
    lanes: number,
    length: number,
    angle: number
  ): void {
    const lineMaterial = new THREE.LineBasicMaterial({ color: 0xffffff })

    for (let i = 1; i < lanes; i++) {
      const offset = (i - lanes / 2) * 3.5

      // 创建虚线
      const points: THREE.Vector3[] = []
      const dashLength = 5
      const gapLength = 5
      const segments = Math.floor(length / (dashLength + gapLength))

      for (let j = 0; j < segments; j++) {
        const startZ = -length / 2 + j * (dashLength + gapLength)
        const endZ = startZ + dashLength

        points.push(new THREE.Vector3(offset, 0.2, startZ))
        points.push(new THREE.Vector3(offset, 0.2, endZ))
      }

      const geometry = new THREE.BufferGeometry().setFromPoints(points)
      const line = new THREE.LineSegments(geometry, lineMaterial)
      line.rotation.y = -angle

      group.add(line)
    }
  }

  /**
   * 添加路边线
   */
  private addRoadBorders(
    group: THREE.Group,
    from: RoadNode,
    to: RoadNode,
    width: number,
    length: number,
    angle: number
  ): void {
    const borderMaterial = new THREE.LineBasicMaterial({ color: 0xffffff })

    const leftPoints = [
      new THREE.Vector3(-width / 2, 0.2, -length / 2),
      new THREE.Vector3(-width / 2, 0.2, length / 2)
    ]

    const rightPoints = [
      new THREE.Vector3(width / 2, 0.2, -length / 2),
      new THREE.Vector3(width / 2, 0.2, length / 2)
    ]

    const leftGeometry = new THREE.BufferGeometry().setFromPoints(leftPoints)
    const rightGeometry = new THREE.BufferGeometry().setFromPoints(rightPoints)

    const leftLine = new THREE.Line(leftGeometry, borderMaterial)
    const rightLine = new THREE.Line(rightGeometry, borderMaterial)

    leftLine.rotation.y = -angle
    rightLine.rotation.y = -angle

    group.add(leftLine)
    group.add(rightLine)
  }

  /**
   * 移除节点
   */
  removeNode(nodeId: string): void {
    const mesh = this.nodes.get(nodeId)
    if (mesh) {
      this.scene.remove(mesh)
      this.nodes.delete(nodeId)
    }
  }

  /**
   * 移除路段
   */
  removeEdge(edgeId: string): void {
    const group = this.edges.get(edgeId)
    if (group) {
      this.scene.remove(group)
      this.edges.delete(edgeId)
    }
  }

  /**
   * 清除所有
   */
  clear(): void {
    this.nodes.forEach((mesh) => this.scene.remove(mesh))
    this.edges.forEach((group) => this.scene.remove(group))
    this.nodes.clear()
    this.edges.clear()
  }

  /**
   * 高亮节点
   */
  highlightNode(nodeId: string, highlight: boolean = true): void {
    const mesh = this.nodes.get(nodeId)
    if (mesh) {
      const material = mesh.material as THREE.MeshStandardMaterial
      material.emissive.setHex(highlight ? 0x444444 : 0x000000)
    }
  }

  /**
   * 高亮路段
   */
  highlightEdge(edgeId: string, highlight: boolean = true): void {
    const group = this.edges.get(edgeId)
    if (group) {
      group.children.forEach((child) => {
        if (child instanceof THREE.Mesh) {
          const material = child.material as THREE.MeshStandardMaterial
          material.emissive.setHex(highlight ? 0x444444 : 0x000000)
        }
      })
    }
  }
}
