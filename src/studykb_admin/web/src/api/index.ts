const API_BASE = '/api'

export interface Category {
  name: string
  file_count: number
  materials: Material[]
}

export interface Material {
  name: string
  line_count: number
  has_index: boolean
}

export interface ProgressEntry {
  id: string
  name: string
  status: 'pending' | 'active' | 'review' | 'done'
  comment: string
  updated_at: string | null
  mastered_at: string | null
  review_count: number
  next_review_at: string | null
  related_sections: RelatedSection[]
}

export interface RelatedSection {
  material: string
  start_line: number
  end_line: number
  desc: string
}

export interface ProgressStats {
  pending: number
  active: number
  review: number
  done: number
  total: number
}

// Categories API
export async function fetchCategories(): Promise<Category[]> {
  const res = await fetch(`${API_BASE}/categories`)
  const data = await res.json()
  return data.categories
}

export async function createCategory(name: string): Promise<void> {
  const res = await fetch(`${API_BASE}/categories`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to create category')
  }
}

export async function deleteCategory(name: string): Promise<void> {
  const res = await fetch(`${API_BASE}/categories/${name}`, {
    method: 'DELETE',
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to delete category')
  }
}

// Materials API
export async function fetchMaterials(category: string): Promise<Material[]> {
  const res = await fetch(`${API_BASE}/materials/${category}`)
  const data = await res.json()
  return data.materials
}

export async function fetchMaterialContent(
  category: string,
  material: string,
  startLine = 1,
  endLine = 500
): Promise<{ lines: { num: number; text: string }[]; truncated: boolean }> {
  const res = await fetch(
    `${API_BASE}/materials/${category}/${material}/content?start_line=${startLine}&end_line=${endLine}`
  )
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to fetch content')
  }
  return await res.json()
}

export async function fetchMaterialIndex(category: string, material: string): Promise<string> {
  const res = await fetch(`${API_BASE}/materials/${category}/${material}/index`)
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to fetch index')
  }
  const data = await res.json()
  return data.content
}

export async function deleteMaterial(category: string, material: string): Promise<void> {
  const res = await fetch(`${API_BASE}/materials/${category}/${material}`, {
    method: 'DELETE',
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to delete material')
  }
}

// Progress API
export async function fetchProgress(
  category: string,
  statusFilter?: string[]
): Promise<{ stats: ProgressStats; entries: ProgressEntry[] }> {
  let url = `${API_BASE}/progress/${category}`
  if (statusFilter && statusFilter.length > 0) {
    url += `?status_filter=${statusFilter.join(',')}`
  }
  const res = await fetch(url)
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to fetch progress')
  }
  return await res.json()
}

export async function updateProgress(
  category: string,
  progressId: string,
  data: {
    status: string
    name?: string
    comment?: string
    related_sections?: RelatedSection[]
  }
): Promise<void> {
  const res = await fetch(`${API_BASE}/progress/${category}/${progressId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to update progress')
  }
}

export async function createProgress(
  category: string,
  data: {
    progress_id: string
    name: string
    status?: string
    comment?: string
    related_sections?: RelatedSection[]
  }
): Promise<void> {
  const res = await fetch(`${API_BASE}/progress/${category}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to create progress')
  }
}

export async function deleteProgress(category: string, progressId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/progress/${category}/${progressId}`, {
    method: 'DELETE',
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to delete progress')
  }
}

// Convert API
export async function getConvertConfig(): Promise<{
  configured: boolean
  api_base: string
  model_version: string
}> {
  const res = await fetch(`${API_BASE}/convert/config`)
  return await res.json()
}

export async function startConversion(
  category: string,
  file: File,
  outputFilename?: string
): Promise<{ task_id: string }> {
  const formData = new FormData()
  formData.append('category', category)
  formData.append('file', file)
  if (outputFilename) {
    formData.append('output_filename', outputFilename)
  }

  const res = await fetch(`${API_BASE}/convert/upload`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to start conversion')
  }
  return await res.json()
}

export async function getConversionStatus(taskId: string): Promise<{
  task_id: string
  status: string
  progress: number
  message: string
  result?: { output_path: string; line_count: number; has_images: boolean }
  error?: string
}> {
  const res = await fetch(`${API_BASE}/convert/status/${taskId}`)
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to get status')
  }
  return await res.json()
}

// Tasks API (Agent operations with WebSocket progress)
export async function getTasksConfigStatus(): Promise<{
  llm: { configured: boolean; model: string; base_url: string }
  mineru: { configured: boolean; model_version: string }
}> {
  const res = await fetch(`${API_BASE}/tasks/config/status`)
  return await res.json()
}

export async function generateIndex(
  category: string,
  material: string,
  sessionId: string
): Promise<{ task_id: string }> {
  const res = await fetch(`${API_BASE}/tasks/generate-index?session_id=${sessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ category, material }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to start index generation')
  }
  return await res.json()
}

export async function initProgress(
  category: string,
  sessionId: string
): Promise<{ task_id: string }> {
  const res = await fetch(`${API_BASE}/tasks/init-progress?session_id=${sessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ category }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to start progress init')
  }
  return await res.json()
}

export async function fullInit(
  category: string,
  sessionId: string,
  options?: { material_path?: string; new_category?: boolean }
): Promise<{ task_id: string }> {
  const res = await fetch(`${API_BASE}/tasks/full-init?session_id=${sessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      category,
      material_path: options?.material_path,
      new_category: options?.new_category,
    }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to start full init')
  }
  return await res.json()
}

// Upload material (unified: MD direct import, others via MinerU)
export async function uploadMaterial(
  category: string,
  file: File,
  overwrite = false,
  sessionId?: string
): Promise<{
  success: boolean
  type: 'direct' | 'conversion'
  message: string
  task_id?: string
  file?: { name: string; line_count: number; has_index: boolean }
}> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('overwrite', String(overwrite))
  if (sessionId) {
    formData.append('session_id', sessionId)
  }

  const res = await fetch(`${API_BASE}/materials/${category}/upload`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to upload material')
  }
  return await res.json()
}

// Axios-like wrapper for components that use api.get()
export const api = {
  async get(url: string) {
    const res = await fetch(`${API_BASE}${url}`)
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Request failed' }))
      throw new Error(err.detail || 'Request failed')
    }
    return { data: await res.json() }
  },
}

// Workspace API
export interface WorkspaceFile {
  path: string
  type: 'file'
  size: number
}

export async function listWorkspaceFiles(
  category: string,
  progressId: string
): Promise<WorkspaceFile[]> {
  const res = await fetch(`${API_BASE}/workspace/${encodeURIComponent(category)}/${encodeURIComponent(progressId)}/files`)
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to list workspace files')
  }
  const data = await res.json()
  return data.files
}

export async function readWorkspaceFile(
  category: string,
  progressId: string,
  filePath: string = 'note.md'
): Promise<{ content: string; truncated: boolean }> {
  const params = new URLSearchParams({ file_path: filePath })
  const res = await fetch(`${API_BASE}/workspace/${encodeURIComponent(category)}/${encodeURIComponent(progressId)}/file?${params}`)
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to read workspace file')
  }
  const data = await res.json()
  return { content: data.content, truncated: data.truncated }
}

export async function writeWorkspaceFile(
  category: string,
  progressId: string,
  filePath: string,
  content: string
): Promise<void> {
  const res = await fetch(`${API_BASE}/workspace/${encodeURIComponent(category)}/${encodeURIComponent(progressId)}/file`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_path: filePath, content }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to write workspace file')
  }
}

export async function deleteWorkspaceFile(
  category: string,
  progressId: string,
  filePath: string
): Promise<void> {
  const params = new URLSearchParams({ file_path: filePath })
  const res = await fetch(`${API_BASE}/workspace/${encodeURIComponent(category)}/${encodeURIComponent(progressId)}/file?${params}`, {
    method: 'DELETE',
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to delete workspace file')
  }
}
