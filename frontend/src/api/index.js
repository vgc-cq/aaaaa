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
}

// 脚本分镜
export const scriptsApi = {
  list: (params) => api.get('/scripts/', { params }),
  get: (id) => api.get(`/scripts/${id}`),
  create: (data) => api.post('/scripts/', data),
  update: (id, data) => api.put(`/scripts/${id}`, data),
  delete: (id) => api.delete(`/scripts/${id}`),
}

// 视频生产
export const videosApi = {
  list: (params) => api.get('/videos/', { params }),
  get: (id) => api.get(`/videos/${id}`),
  create: (data) => api.post('/videos/', data),
  update: (id, data) => api.put(`/videos/${id}`, data),
  delete: (id) => api.delete(`/videos/${id}`),
  kanban: () => api.get('/videos/view/kanban'),
}

// 投流数据
export const adsApi = {
  list: (params) => api.get('/ads/', { params }),
  get: (id) => api.get(`/ads/${id}`),
  create: (data) => api.post('/ads/', data),
  update: (id, data) => api.put(`/ads/${id}`, data),
  delete: (id) => api.delete(`/ads/${id}`),
  highPriority: () => api.get('/ads/view/high_priority'),
}

// 私域线索
export const leadsApi = {
  list: (params) => api.get('/leads/', { params }),
  get: (id) => api.get(`/leads/${id}`),
  create: (data) => api.post('/leads/', data),
  update: (id, data) => api.put(`/leads/${id}`, data),
  delete: (id) => api.delete(`/leads/${id}`),
  today: () => api.get('/leads/view/today'),
}

// 复盘表
export const reviewsApi = {
  list: (params) => api.get('/reviews/', { params }),
  get: (id) => api.get(`/reviews/${id}`),
  create: (data) => api.post('/reviews/', data),
  update: (id, data) => api.put(`/reviews/${id}`, data),
  delete: (id) => api.delete(`/reviews/${id}`),
}

// 知识库
export const knowledgeApi = {
  list: (params) => api.get('/knowledge/', { params }),
  get: (id) => api.get(`/knowledge/${id}`),
  create: (data) => api.post('/knowledge/', data),
  update: (id, data) => api.put(`/knowledge/${id}`, data),
  delete: (id) => api.delete(`/knowledge/${id}`),
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

// AI 工作流
export const aiApi = {
  sellingPoints: (data) => api.post('/ai/workflow/step1_selling_points', data),
  contentAngles: (data) => api.post('/ai/workflow/step2_content_angles', data),
  scriptGeneration: (data) => api.post('/ai/workflow/step3_script_generation', data),
  qualityCheck: (data) => api.post('/ai/workflow/step4_quality_check', data),
  fullWorkflow: (data) => api.post('/ai/workflow/full', data),
  saveResult: (data) => api.post('/ai/workflow/save_result', data),
}

// 智能体
export const agentsApi = {
  list: () => api.get('/agents/agents'),
  adReview: (data) => api.post('/agents/agents/投流复盘助手', data),
  productAnalysis: (data) => api.post('/agents/agents/选品分析助手', data),
  scriptGen: (data) => api.post('/agents/agents/脚本生成助手', data),
  videoQa: (data) => api.post('/agents/agents/视频质检助手', data),
  customerService: (data) => api.post('/agents/agents/客服话术助手', data),
  autoReview: (data) => api.post('/agents/agents/auto_review', data),
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



