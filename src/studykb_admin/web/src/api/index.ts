import { apiFetch } from './fetch'

// ─── Types ───────────────────────────────────────────────

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

export interface WorkspaceFile {
  path: string
  type: 'file'
  size: number
}

export interface FileVersion {
  version_id: string
  timestamp: string
  operation: 'create' | 'write' | 'edit' | 'delete'
  description: string
  size: number
  lines: number
}

// ─── Index Types ──────────────────────────────────────────

export interface IndexChapter {
  depth: number
  number: string
  title: string
  start: number
  end: number
  tags: string
}

export interface IndexOverview {
  title: string
  start: number
  end: number
  tags: string
}

export interface IndexLookup {
  title: string
  start: number
  end: number
  keywords: string
  section: string
}

export interface ParsedIndex {
  meta: Record<string, string>
  overview: IndexOverview[]
  chapters: IndexChapter[]
  lookups: IndexLookup[]
}

// ─── Categories API ──────────────────────────────────────

export async function fetchCategories(): Promise<Category[]> {
  const data = await apiFetch<{ categories: Category[] }>('/categories')
  return data.categories
}

export async function createCategory(name: string): Promise<void> {
  await apiFetch<void>('/categories', {
    method: 'POST',
    body: JSON.stringify({ name }),
  })
}

export async function deleteCategory(name: string): Promise<void> {
  await apiFetch<void>(`/categories/${name}`, {
    method: 'DELETE',
  })
}

// ─── Materials API ───────────────────────────────────────

export async function fetchMaterials(category: string): Promise<Material[]> {
  const data = await apiFetch<{ materials: Material[] }>(`/materials/${category}`)
  return data.materials
}

export async function fetchMaterialContent(
  category: string,
  material: string,
  startLine = 1,
  endLine = 500
): Promise<{ lines: { num: number; text: string }[]; truncated: boolean }> {
  const params = new URLSearchParams({
    start_line: String(startLine),
    end_line: String(endLine),
  })
  return apiFetch(`/materials/${category}/${material}/content?${params}`)
}

export async function fetchMaterialIndex(
  category: string,
  material: string,
  format: 'raw' | 'parsed' = 'parsed'
): Promise<{ content?: string; parsed?: ParsedIndex; format: string }> {
  const params = new URLSearchParams({ format })
  return apiFetch(`/materials/${category}/${material}/index?${params}`)
}

export async function deleteMaterial(category: string, material: string): Promise<void> {
  await apiFetch<void>(`/materials/${category}/${material}`, {
    method: 'DELETE',
  })
}

// ─── Progress API ────────────────────────────────────────

export async function fetchProgress(
  category: string,
  statusFilter?: string[]
): Promise<{ stats: ProgressStats; entries: ProgressEntry[] }> {
  let url = `/progress/${category}`
  if (statusFilter && statusFilter.length > 0) {
    const params = new URLSearchParams({ status_filter: statusFilter.join(',') })
    url += `?${params}`
  }
  return apiFetch(url)
}

export async function updateProgress(
  category: string,
  progressId: string,
  data: {
    status: ProgressEntry['status']
    name?: string
    comment?: string
    related_sections?: RelatedSection[]
  }
): Promise<void> {
  await apiFetch<void>(`/progress/${category}/${progressId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function createProgress(
  category: string,
  data: {
    progress_id: string
    name: string
    status?: ProgressEntry['status']
    comment?: string
    related_sections?: RelatedSection[]
  }
): Promise<void> {
  await apiFetch<void>(`/progress/${category}`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteProgress(category: string, progressId: string): Promise<void> {
  await apiFetch<void>(`/progress/${category}/${progressId}`, {
    method: 'DELETE',
  })
}

// ─── Convert API ─────────────────────────────────────────

export async function getConvertConfig(): Promise<{
  configured: boolean
  api_base: string
  model_version: string
}> {
  return apiFetch('/convert/config')
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

  return apiFetch('/convert/upload', {
    method: 'POST',
    body: formData,
  })
}

export async function getConversionStatus(taskId: string): Promise<{
  task_id: string
  status: string
  progress: number
  message: string
  result?: { output_path: string; line_count: number; has_images: boolean }
  error?: string
}> {
  return apiFetch(`/convert/status/${taskId}`)
}

// ─── Tasks API ───────────────────────────────────────────

export async function getTasksConfigStatus(): Promise<{
  llm: { configured: boolean; model: string; base_url: string }
  mineru: { configured: boolean; model_version: string }
}> {
  return apiFetch('/tasks/config/status')
}

export async function generateIndex(
  category: string,
  material: string,
  sessionId: string
): Promise<{ task_id: string }> {
  const params = new URLSearchParams({ session_id: sessionId })
  return apiFetch(`/tasks/generate-index?${params}`, {
    method: 'POST',
    body: JSON.stringify({ category, material }),
  })
}

export async function cancelTask(sessionId: string): Promise<{ success: boolean; message: string }> {
  const params = new URLSearchParams({ session_id: sessionId })
  return apiFetch(`/tasks/cancel?${params}`, { method: 'POST' })
}

export async function initProgress(
  category: string,
  sessionId: string
): Promise<{ task_id: string }> {
  const params = new URLSearchParams({ session_id: sessionId })
  return apiFetch(`/tasks/init-progress?${params}`, {
    method: 'POST',
    body: JSON.stringify({ category }),
  })
}

export async function fullInit(
  category: string,
  sessionId: string,
  options?: { material_path?: string; new_category?: boolean }
): Promise<{ task_id: string }> {
  const params = new URLSearchParams({ session_id: sessionId })
  return apiFetch(`/tasks/full-init?${params}`, {
    method: 'POST',
    body: JSON.stringify({
      category,
      material_path: options?.material_path,
      new_category: options?.new_category,
    }),
  })
}

// ─── Upload API ──────────────────────────────────────────

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

  return apiFetch(`/materials/${category}/upload`, {
    method: 'POST',
    body: formData,
  })
}

// ─── Workspace API ───────────────────────────────────────

export async function listWorkspaceFiles(
  category: string,
  progressId: string
): Promise<WorkspaceFile[]> {
  const data = await apiFetch<{ files: WorkspaceFile[] }>(
    `/workspace/${encodeURIComponent(category)}/${encodeURIComponent(progressId)}/files`
  )
  return data.files
}

export async function readWorkspaceFile(
  category: string,
  progressId: string,
  filePath: string = 'note.md'
): Promise<{ content: string; truncated: boolean }> {
  const params = new URLSearchParams({ file_path: filePath })
  const data = await apiFetch<{ content: string; truncated: boolean }>(
    `/workspace/${encodeURIComponent(category)}/${encodeURIComponent(progressId)}/file?${params}`
  )
  return { content: data.content, truncated: data.truncated }
}

export async function writeWorkspaceFile(
  category: string,
  progressId: string,
  filePath: string,
  content: string
): Promise<void> {
  await apiFetch<void>(
    `/workspace/${encodeURIComponent(category)}/${encodeURIComponent(progressId)}/file`,
    {
      method: 'POST',
      body: JSON.stringify({ file_path: filePath, content }),
    }
  )
}

export async function deleteWorkspaceFile(
  category: string,
  progressId: string,
  filePath: string
): Promise<void> {
  const params = new URLSearchParams({ file_path: filePath })
  await apiFetch<void>(
    `/workspace/${encodeURIComponent(category)}/${encodeURIComponent(progressId)}/file?${params}`,
    { method: 'DELETE' }
  )
}

// ─── Workspace History API ──────────────────────────────────

export async function listFileHistory(
  category: string,
  progressId: string,
  filePath: string
): Promise<FileVersion[]> {
  const params = new URLSearchParams({ file_path: filePath })
  const data = await apiFetch<{ versions: FileVersion[] }>(
    `/workspace/${encodeURIComponent(category)}/${encodeURIComponent(progressId)}/history?${params}`
  )
  return data.versions
}

export async function getFileVersion(
  category: string,
  progressId: string,
  filePath: string,
  versionId: string
): Promise<string> {
  const params = new URLSearchParams({ file_path: filePath, version_id: versionId })
  const data = await apiFetch<{ content: string }>(
    `/workspace/${encodeURIComponent(category)}/${encodeURIComponent(progressId)}/history/version?${params}`
  )
  return data.content
}

export async function rollbackFile(
  category: string,
  progressId: string,
  filePath: string,
  versionId: string
): Promise<void> {
  await apiFetch<void>(
    `/workspace/${encodeURIComponent(category)}/${encodeURIComponent(progressId)}/history/rollback`,
    {
      method: 'POST',
      body: JSON.stringify({ file_path: filePath, version_id: versionId }),
    }
  )
}
