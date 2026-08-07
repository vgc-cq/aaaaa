import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

// 商品库
export const productsApi = {
  list: (params) => api.get('/products/', { params }),
  get: (id) => api.get(`/products/${id}`),
  create: (data) => api.post('/products/', data),
  update: (id, data) => api.put(`/products/${id}`, data),
  delete: (id) => api.delete(`/products/${id}`),
  importDocument: (formData) => api.post('/products/import_document', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  }),
  importTemplate: () => api.get('/products/import_template', { responseType: 'blob' }),
  import: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/products/import', fd, { timeout: 300000 })
  },
  aiSelect: (ids) => api.post('/products/ai_select', { product_ids: ids }, { timeout: 300000 }),
  batchDelete: (ids) => api.post('/products/batch_delete', { product_ids: ids }),
  todayTasks: () => api.get('/products/view/today'),
  kanban: () => api.get('/products/view/kanban'),
}

// 内容拆解
export const contentsApi = {
  list: (params) => api.get('/contents/', { params }),
  get: (id) => api.get(`/contents/${id}`),
  create: (data) => api.post('/contents/', data),
  update: (id, data) => api.put(`/contents/${id}`, data),
  delete: (id) => api.delete(`/contents/${id}`),
  batchDelete: (ids) => api.post('/contents/batch_delete', { ids }),
}

// 脚本分镜
export const scriptsApi = {
  list: (params) => api.get('/scripts/', { params }),
  get: (id) => api.get(`/scripts/${id}`),
  create: (data) => api.post('/scripts/', data),
  update: (id, data) => api.put(`/scripts/${id}`, data),
  delete: (id) => api.delete(`/scripts/${id}`),
  batchDelete: (ids) => api.post('/scripts/batch_delete', { ids }),
  batchReview: (ids, review_status) => api.post('/scripts/batch_review', { ids, review_status }),
  generate: (data) => api.post('/scripts/generate', data, { timeout: 300000 }),
}

// 视频生产
export const videosApi = {
  list: (params) => api.get('/videos/', { params }),
  get: (id) => api.get(`/videos/${id}`),
  create: (data) => api.post('/videos/', data),
  update: (id, data) => api.put(`/videos/${id}`, data),
  delete: (id) => api.delete(`/videos/${id}`),
  batchDelete: (ids) => api.post('/videos/batch_delete', { ids }),
  generateWithWan: (data) => api.post('/videos/wan/generate', data, { timeout: 180000 }),
  wanProgress: (videoId) => api.get(`/videos/wan/progress/${videoId}`, { timeout: 120000 }),
  kanban: () => api.get('/videos/view/kanban'),
}

// 投流数据
export const adsApi = {
  list: (params) => api.get('/ads/', { params }),
  get: (id) => api.get(`/ads/${id}`),
  create: (data) => api.post('/ads/', data),
  update: (id, data) => api.put(`/ads/${id}`, data),
  delete: (id) => api.delete(`/ads/${id}`),
  batchDelete: (ids) => api.post('/ads/batch_delete', { ids }),
  highPriority: () => api.get('/ads/view/high_priority'),
  importTemplate: () => api.get('/ads/import_template', { responseType: 'blob' }),
  importData: (formData) => api.post('/ads/import', formData, { timeout: 120000 }),
}

// 复盘表
export const reviewsApi = {
  list: (params) => api.get('/reviews/', { params }),
  get: (id) => api.get(`/reviews/${id}`),
  create: (data) => api.post('/reviews/', data),
  update: (id, data) => api.put(`/reviews/${id}`, data),
  delete: (id) => api.delete(`/reviews/${id}`),
  batchDelete: (ids) => api.post('/reviews/batch_delete', { ids }),
}

// 复盘智能体
export const autonomousReviewAgentApi = {
  run: (data = {}) => api.post('/review-agent/run', data, { timeout: 600000 }),
  logs: (params) => api.get('/review-agent/logs', { params }),
}

// 知识库
export const knowledgeApi = {
  list: (params) => api.get('/knowledge/', { params }),
  get: (id) => api.get(`/knowledge/${id}`),
  create: (data) => api.post('/knowledge/', data),
  update: (id, data) => api.put(`/knowledge/${id}`, data),
  delete: (id) => api.delete(`/knowledge/${id}`),
  batchDelete: (ids) => api.post('/knowledge/batch_delete', { ids }),
  categories: () => api.get('/knowledge/categories/list'),
}

// 视觉内容拆解
export const visionApi = {
  contentBreakdown: (data) => api.post('/ai/vision/content_breakdown', data),
  upload: (formData) => api.post('/ai/vision/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  }),
}

// 数据分析
export const analysisApi = {
  dashboard: () => api.get('/analysis/dashboard'),
  todayTasks: () => api.get('/analysis/today_tasks'),
  ownerKanban: () => api.get('/analysis/owner_kanban'),
  statusKanban: () => api.get('/analysis/status_kanban'),
  highPriority: () => api.get('/analysis/high_priority'),
  allVideos: () => api.get('/analysis/analysis/all_videos'),
  video: (id) => api.get(`/analysis/analysis/video/${id}`),
}

// 数据导出
export const exportApi = {
  all: () => api.get('/export/all', { responseType: 'blob' }),
}

export default api




