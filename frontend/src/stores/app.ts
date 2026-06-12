/**
 * 全局应用状态管理
 * 管理: 模式切换、面板开关、选中对象、侧边栏状态
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/** 应用模式 */
export type AppMode = 'view' | 'edit' | 'simulate' | 'optimize'

/** 选中对象 */
export interface SelectedObject {
  type: 'node' | 'edge' | 'signal'
  id: string
  data: Record<string, any>
  /** 地图上的像素位置(用于弹窗定位) */
  screenX?: number
  screenY?: number
}

/** 面板类型 */
export type PanelType = 'network' | 'sim' | 'opt' | 'analysis' | null

export const useAppStore = defineStore('app', () => {
  // --- 当前模式 ---
  const mode = ref<AppMode>('view')

  // --- 面板 ---
  const activePanel = ref<PanelType>(null)

  // --- 选中对象 ---
  const selectedObject = ref<SelectedObject | null>(null)

  // --- 侧边栏 ---
  const sidebarCollapsed = ref(false)

  // --- 交叉口编辑器 ---
  const intersectionEditorOpen = ref(false)
  const intersectionEditorNodeId = ref<string | null>(null)

  // --- 计算属性 ---
  const isViewMode = computed(() => mode.value === 'view')
  const isEditMode = computed(() => mode.value === 'edit')
  const isSimMode = computed(() => mode.value === 'simulate')
  const isOptMode = computed(() => mode.value === 'optimize')

  // --- 动作 ---
  function setMode(newMode: AppMode) {
    mode.value = newMode
    // 切换模式时关闭面板
    activePanel.value = null
  }

  function openPanel(panel: PanelType) {
    if (activePanel.value === panel) {
      activePanel.value = null
    } else {
      activePanel.value = panel
    }
  }

  function closePanel() {
    activePanel.value = null
  }

  function selectObject(obj: SelectedObject | null) {
    selectedObject.value = obj
  }

  function clearSelection() {
    selectedObject.value = null
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function openIntersectionEditor(nodeId: string) {
    intersectionEditorOpen.value = true
    intersectionEditorNodeId.value = nodeId
  }

  function closeIntersectionEditor() {
    intersectionEditorOpen.value = false
    intersectionEditorNodeId.value = null
  }

  return {
    mode, activePanel, selectedObject, sidebarCollapsed,
    intersectionEditorOpen, intersectionEditorNodeId,
    isViewMode, isEditMode, isSimMode, isOptMode,
    setMode, openPanel, closePanel,
    selectObject, clearSelection, toggleSidebar,
    openIntersectionEditor, closeIntersectionEditor
  }
})
