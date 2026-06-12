/**
 * NetworkLayer — 路网3D渲染层 (Three.js)
 * 路段: PlaneGeometry, 宽度按车道数, 颜色按道路等级
 * 节点: CylinderGeometry, 高度按连接数
 * 信号灯: SphereGeometry 红/绿/黄球
 * 叠加在 Leaflet 瓦片地图上方
 */
import * as THREE from 'three'

export interface NetworkNode {
  node_id: string
  name: string
  lng: number
  lat: number
  node_type: string
  x?: number
  y?: number
  degree?: number
}

export interface NetworkEdge {
  edge_id: string
  name: string
  from_node: string
  to_node: string
  length: number
  speed_limit: number
  lanes_count: number
  road_class: string
}

const ROAD_COLORS: Record<string, number> = {
  motorway: 0xef4444,
  trunk: 0xf97316,
  primary: 0xeab308,
  secondary: 0x22c55e,
  tertiary: 0x38bdf8,
  residential: 0x64748b,
}

export class NetworkLayer {
  private scene: THREE.Scene
  private nodeMeshes: Map<string, THREE.Mesh> = new Map()
  private edgeMeshes: Map<string, THREE.Mesh> = new Map()
  private nodeMap: Map<string, NetworkNode> = new Map()
  private selectedNodeId: string | null = null
  private latLngToScene: (lat: number, lng: number) => { x: number; z: number }

  constructor(scene: THREE.Scene, latLngToScene: (lat: number, lng: number) => { x: number; z: number }) {
    this.scene = scene
    this.latLngToScene = latLngToScene
  }

  /** 加载路网数据 */
  loadNetwork(nodes: NetworkNode[], edges: NetworkEdge[]) {
    this.clear()

    // 建立节点索引
    for (const node of nodes) {
      this.nodeMap.set(node.node_id, node)
    }

    // 渲染路段
    for (const edge of edges) {
      this.addEdge(edge)
    }

    // 渲染节点
    for (const node of nodes) {
      this.addNode(node)
    }
  }

  /** 添加节点(3D圆柱) */
  addNode(node: NetworkNode) {
    const pos = this.latLngToScene(node.lat, node.lng)
    const degree = node.degree || 0
    const radius = Math.max(2, Math.min(degree * 1.5, 8))
    const height = Math.max(3, degree * 2)

    const geometry = new THREE.CylinderGeometry(radius, radius, height, 16)
    const color = node.node_type === 'roundabout' ? 0x22c55e : 0x38bdf8
    const material = new THREE.MeshStandardMaterial({
      color,
      roughness: 0.6,
      metalness: 0.3,
      emissive: color,
      emissiveIntensity: 0.1,
    })

    const mesh = new THREE.Mesh(geometry, material)
    mesh.position.set(pos.x, height / 2, pos.z)
    mesh.castShadow = true
    mesh.userData = { type: 'node', nodeId: node.node_id, name: node.name }

    this.scene.add(mesh)
    this.nodeMeshes.set(node.node_id, mesh)
  }

  /** 添加路段(3D平面) */
  addEdge(edge: NetworkEdge) {
    const fromNode = this.nodeMap.get(edge.from_node)
    const toNode = this.nodeMap.get(edge.to_node)
    if (!fromNode || !toNode) return

    const from = this.latLngToScene(fromNode.lat, fromNode.lng)
    const to = this.latLngToScene(toNode.lat, toNode.lng)

    const dx = to.x - from.x
    const dz = to.z - from.z
    const length = Math.sqrt(dx * dx + dz * dz)
    const angle = Math.atan2(dx, dz)

    // 路面宽度按车道数
    const width = (edge.lanes_count || 1) * 3.5

    const geometry = new THREE.PlaneGeometry(width, length)
    const color = ROAD_COLORS[edge.road_class] || 0x64748b
    const material = new THREE.MeshStandardMaterial({
      color: 0x1a2030, // 深色路面
      roughness: 0.9,
      metalness: 0.05,
    })

    const mesh = new THREE.Mesh(geometry, material)
    mesh.rotation.x = -Math.PI / 2
    mesh.rotation.z = -angle
    mesh.position.set(
      (from.x + to.x) / 2,
      0.05,
      (from.z + to.z) / 2
    )
    mesh.receiveShadow = true
    mesh.userData = { type: 'edge', edgeId: edge.edge_id, name: edge.name }

    this.scene.add(mesh)
    this.edgeMeshes.set(edge.edge_id, mesh)

    // 路边线(发光边缘)
    this.addRoadBorder(from, to, width, length, angle, color)

    // 车道线(虚线)
    this.addLaneLines(from, to, edge.lanes_count, length, angle)
  }

  /** 路边线 */
  private addRoadBorder(
    from: { x: number; z: number },
    to: { x: number; z: number },
    width: number, length: number, angle: number, color: number
  ) {
    const edgeMaterial = new THREE.LineBasicMaterial({ color, linewidth: 1 })

    const leftPoints = [
      new THREE.Vector3(-width / 2, 0.1, -length / 2),
      new THREE.Vector3(-width / 2, 0.1, length / 2),
    ]
    const rightPoints = [
      new THREE.Vector3(width / 2, 0.1, -length / 2),
      new THREE.Vector3(width / 2, 0.1, length / 2),
    ]

    const leftGeo = new THREE.BufferGeometry().setFromPoints(leftPoints)
    const rightGeo = new THREE.BufferGeometry().setFromPoints(rightPoints)

    const leftLine = new THREE.Line(leftGeo, edgeMaterial)
    const rightLine = new THREE.Line(rightGeo, edgeMaterial)

    leftLine.rotation.y = -angle
    rightLine.rotation.y = -angle

    leftLine.position.set((from.x + to.x) / 2, 0, (from.z + to.z) / 2)
    rightLine.position.set((from.x + to.x) / 2, 0, (from.z + to.z) / 2)

    this.scene.add(leftLine)
    this.scene.add(rightLine)
  }

  /** 车道虚线 */
  private addLaneLines(
    from: { x: number; z: number },
    to: { x: number; z: number },
    lanes: number, length: number, angle: number
  ) {
    if (lanes <= 1) return

    const lineMaterial = new THREE.LineBasicMaterial({ color: 0x475569 })

    for (let i = 1; i < lanes; i++) {
      const offset = (i - lanes / 2) * 3.5
      const points: THREE.Vector3[] = []
      const dashLength = 3
      const gapLength = 4
      const segments = Math.floor(length / (dashLength + gapLength))

      for (let j = 0; j < segments; j++) {
        const startZ = -length / 2 + j * (dashLength + gapLength)
        const endZ = startZ + dashLength
        points.push(new THREE.Vector3(offset, 0.12, startZ))
        points.push(new THREE.Vector3(offset, 0.12, endZ))
      }

      const geo = new THREE.BufferGeometry().setFromPoints(points)
      const line = new THREE.LineSegments(geo, lineMaterial)
      line.rotation.y = -angle
      line.position.set((from.x + to.x) / 2, 0, (from.z + to.z) / 2)
      this.scene.add(line)
    }
  }

  /** 选中节点高亮 */
  selectNode(nodeId: string | null) {
    // 取消旧选中
    if (this.selectedNodeId) {
      const oldMesh = this.nodeMeshes.get(this.selectedNodeId)
      if (oldMesh) {
        const mat = oldMesh.material as THREE.MeshStandardMaterial
        mat.emissiveIntensity = 0.1
      }
    }

    this.selectedNodeId = nodeId

    // 高亮新选中
    if (nodeId) {
      const mesh = this.nodeMeshes.get(nodeId)
      if (mesh) {
        const mat = mesh.material as THREE.MeshStandardMaterial
        mat.emissive.setHex(0xf59e0b)
        mat.emissiveIntensity = 0.5
      }
    }
  }

  /** 获取节点信息 */
  getNode(nodeId: string): NetworkNode | undefined {
    return this.nodeMap.get(nodeId)
  }

  /** 获取所有节点位置(用于其他图层) */
  getNodePositions(): Map<string, { lat: number; lng: number }> {
    const result = new Map<string, { lat: number; lng: number }>()
    for (const [id, node] of this.nodeMap) {
      result.set(id, { lat: node.lat, lng: node.lng })
    }
    return result
  }

  /** 射线检测(Raycasting) — 检测点击了哪个节点/路段 */
  raycast(raycaster: THREE.Raycaster): { type: 'node' | 'edge'; id: string } | null {
    // 检测节点
    const nodeMeshes = Array.from(this.nodeMeshes.values())
    const nodeHits = raycaster.intersectObjects(nodeMeshes)
    if (nodeHits.length > 0) {
      const hit = nodeHits[0]
      return { type: 'node', id: hit.object.userData.nodeId }
    }

    // 检测路段
    const edgeMeshes = Array.from(this.edgeMeshes.values())
    const edgeHits = raycaster.intersectObjects(edgeMeshes)
    if (edgeHits.length > 0) {
      const hit = edgeHits[0]
      return { type: 'edge', id: hit.object.userData.edgeId }
    }

    return null
  }

  /** 清除 */
  clear() {
    for (const mesh of this.nodeMeshes.values()) {
      this.scene.remove(mesh)
      mesh.geometry.dispose()
      ;(mesh.material as THREE.Material).dispose()
    }
    for (const mesh of this.edgeMeshes.values()) {
      this.scene.remove(mesh)
      mesh.geometry.dispose()
      ;(mesh.material as THREE.Material).dispose()
    }
    this.nodeMeshes.clear()
    this.edgeMeshes.clear()
    this.nodeMap.clear()
    this.selectedNodeId = null
  }

  /** 销毁 */
  dispose() {
    this.clear()
  }
}
