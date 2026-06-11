/**
 * Three.js 场景管理器
 */

import * as THREE from 'three'

export class SceneManager {
  private scene: THREE.Scene
  private camera: THREE.PerspectiveCamera
  private renderer: THREE.WebGLRenderer
  private animationId: number | null = null

  constructor(container: HTMLElement) {
    // 创建场景
    this.scene = new THREE.Scene()
    this.scene.background = new THREE.Color(0xf0f0f0)

    // 创建相机
    const width = container.clientWidth
    const height = container.clientHeight
    this.camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 10000)
    this.camera.position.set(0, 500, 500)
    this.camera.lookAt(0, 0, 0)

    // 创建渲染器
    this.renderer = new THREE.WebGLRenderer({ antialias: true })
    this.renderer.setSize(width, height)
    this.renderer.setPixelRatio(window.devicePixelRatio)
    container.appendChild(this.renderer.domElement)

    // 添加光源
    this.setupLights()

    // 添加地面
    this.addGround()

    // 添加坐标轴辅助
    const axesHelper = new THREE.AxesHelper(200)
    this.scene.add(axesHelper)
  }

  private setupLights(): void {
    // 环境光
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6)
    this.scene.add(ambientLight)

    // 方向光
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8)
    directionalLight.position.set(500, 500, 500)
    directionalLight.castShadow = true
    this.scene.add(directionalLight)
  }

  private addGround(): void {
    const geometry = new THREE.PlaneGeometry(2000, 2000)
    const material = new THREE.MeshStandardMaterial({
      color: 0xe8e8e8,
      roughness: 0.8
    })
    const ground = new THREE.Mesh(geometry, material)
    ground.rotation.x = -Math.PI / 2
    ground.receiveShadow = true
    this.scene.add(ground)
  }

  getScene(): THREE.Scene {
    return this.scene
  }

  getCamera(): THREE.PerspectiveCamera {
    return this.camera
  }

  getRenderer(): THREE.WebGLRenderer {
    return this.renderer
  }

  add(object: THREE.Object3D): void {
    this.scene.add(object)
  }

  remove(object: THREE.Object3D): void {
    this.scene.remove(object)
  }

  render(): void {
    this.renderer.render(this.scene, this.camera)
  }

  startAnimationLoop(callback?: () => void): void {
    const animate = () => {
      this.animationId = requestAnimationFrame(animate)
      if (callback) callback()
      this.render()
    }
    animate()
  }

  stopAnimationLoop(): void {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId)
      this.animationId = null
    }
  }

  resize(width: number, height: number): void {
    this.camera.aspect = width / height
    this.camera.updateProjectionMatrix()
    this.renderer.setSize(width, height)
  }

  dispose(): void {
    this.stopAnimationLoop()
    this.renderer.dispose()
  }

  // 相机控制
  setCameraPosition(x: number, y: number, z: number): void {
    this.camera.position.set(x, y, z)
    this.camera.lookAt(0, 0, 0)
  }

  // 视角切换
  setTopView(): void {
    this.setCameraPosition(0, 1000, 0)
  }

  setPerspectiveView(): void {
    this.setCameraPosition(500, 500, 500)
  }

  setSideView(): void {
    this.setCameraPosition(0, 200, 800)
  }
}
