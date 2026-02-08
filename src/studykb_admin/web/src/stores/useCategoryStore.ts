import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  fetchCategories,
  createCategory,
  deleteCategory,
  deleteMaterial,
  uploadMaterial,
  generateIndex,
  initProgress,
  type Category,
} from '../api'
import { useToast } from '../composables/useToast'
import { useConfirm } from '../composables/useConfirm'
import { useTaskBridge } from '../composables/useTaskBridge'

export const useCategoryStore = defineStore('category', () => {
  const toast = useToast()
  const { confirm } = useConfirm()
  const taskBridge = useTaskBridge()

  // State
  const categories = ref<Category[]>([])
  const selectedCategoryName = ref<string | null>(null)
  const loading = ref(true)
  const error = ref<string | null>(null)
  const selectedMaterials = ref<Set<string>>(new Set())
  const uploading = ref(false)
  const uploadProgress = ref<string | null>(null)

  // Session ID management (persistent via localStorage)
  const STORAGE_KEY = 'studykb_session_id'
  function getSessionId(): string {
    let stored = localStorage.getItem(STORAGE_KEY)
    if (!stored) {
      stored = Math.random().toString(36).substring(2, 10)
      localStorage.setItem(STORAGE_KEY, stored)
    }
    return stored
  }

  // Computed
  const currentCategory = computed(() => {
    return categories.value.find(c => c.name === selectedCategoryName.value) || null
  })

  const materials = computed(() => {
    return currentCategory.value?.materials || []
  })

  const hasSelectedMaterials = computed(() => selectedMaterials.value.size > 0)

  // Actions
  async function load() {
    loading.value = true
    error.value = null
    try {
      categories.value = await fetchCategories()
      if (!selectedCategoryName.value && categories.value.length > 0) {
        selectedCategoryName.value = categories.value[0].name
      }
    } catch (e: any) {
      error.value = e.message || '加载分类失败'
    } finally {
      loading.value = false
    }
  }

  function selectCategory(name: string) {
    selectedCategoryName.value = name
    selectedMaterials.value = new Set()
  }

  function toggleMaterial(name: string) {
    const next = new Set(selectedMaterials.value)
    if (next.has(name)) {
      next.delete(name)
    } else {
      next.add(name)
    }
    selectedMaterials.value = next
  }

  function selectAllMaterials() {
    if (selectedMaterials.value.size === materials.value.length) {
      selectedMaterials.value = new Set()
    } else {
      selectedMaterials.value = new Set(materials.value.map(m => m.name))
    }
  }

  async function create(name: string) {
    try {
      await createCategory(name.trim())
      await load()
      selectedCategoryName.value = name.trim()
      toast.success(`分类「${name.trim()}」创建成功`)
    } catch (e: any) {
      toast.error(e.message || '创建分类失败')
      throw e
    }
  }

  async function remove(name: string) {
    const ok = await confirm({
      title: '删除分类',
      message: `确定要删除分类「${name}」及其所有内容吗？此操作不可恢复。`,
      type: 'danger',
      confirmText: '删除',
    })
    if (!ok) return false

    try {
      await deleteCategory(name)
      if (selectedCategoryName.value === name) {
        selectedCategoryName.value = null
      }
      await load()
      toast.success(`分类「${name}」已删除`)
      return true
    } catch (e: any) {
      toast.error(e.message || '删除分类失败')
      return false
    }
  }

  async function removeMaterial(material: string) {
    if (!selectedCategoryName.value) return false

    const ok = await confirm({
      title: '删除资料',
      message: `确定要删除资料「${material}」吗？`,
      type: 'danger',
      confirmText: '删除',
    })
    if (!ok) return false

    try {
      await deleteMaterial(selectedCategoryName.value, material)
      const next = new Set(selectedMaterials.value)
      next.delete(material)
      selectedMaterials.value = next
      await load()
      toast.success(`资料「${material}」已删除`)
      return true
    } catch (e: any) {
      toast.error(e.message || '删除资料失败')
      return false
    }
  }

  async function upload(files: FileList) {
    if (!selectedCategoryName.value) return

    uploading.value = true
    uploadProgress.value = null
    taskBridge.emit('connect')

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i]
        uploadProgress.value = `上传中 (${i + 1}/${files.length}): ${file.name}`

        const result = await uploadMaterial(selectedCategoryName.value, file, false, getSessionId())

        if (result.type === 'conversion') {
          uploadProgress.value = `已启动转换: ${file.name}`
          taskBridge.emit('startTask', `转换 ${file.name}`)
        }
      }

      await load()
      toast.success('上传完成')
      uploadProgress.value = null
    } catch (e: any) {
      toast.error(`上传失败: ${e.message}`)
      uploadProgress.value = null
    } finally {
      uploading.value = false
    }
  }

  async function genIndex(materialNames: Set<string>) {
    if (!selectedCategoryName.value || materialNames.size === 0) return

    taskBridge.emit('startTask', '生成索引')
    taskBridge.emit('connect')

    try {
      for (const material of materialNames) {
        await generateIndex(selectedCategoryName.value, material, getSessionId())
      }
    } catch (e: any) {
      toast.error(e.message || '启动索引生成失败')
    }
  }

  async function initProgressAction() {
    if (!selectedCategoryName.value) return

    taskBridge.emit('startTask', '初始化进度')
    taskBridge.emit('connect')

    try {
      await initProgress(selectedCategoryName.value, getSessionId())
    } catch (e: any) {
      toast.error(e.message || '启动进度初始化失败')
    }
  }

  // Index preview state
  const indexPreview = ref<{ category: string; material: string } | null>(null)

  function previewIndex(material: string) {
    if (!selectedCategoryName.value) return
    indexPreview.value = {
      category: selectedCategoryName.value,
      material,
    }
  }

  function closeIndexPreview() {
    indexPreview.value = null
  }

  return {
    // State
    categories,
    selectedCategoryName,
    loading,
    error,
    selectedMaterials,
    uploading,
    uploadProgress,
    // Computed
    currentCategory,
    materials,
    hasSelectedMaterials,
    // Actions
    load,
    selectCategory,
    toggleMaterial,
    selectAllMaterials,
    create,
    remove,
    removeMaterial,
    upload,
    genIndex,
    initProgressAction,
    // Index preview
    indexPreview,
    previewIndex,
    closeIndexPreview,
  }
})
