<template>
  <div>
    <el-card class="table-card">
      <template #header>
        <div class="page-header">
          <div class="header-left">
            <span style="font-weight:600">视频生产任务表</span>
            <el-button type="danger" size="small" :disabled="selectedIds.length === 0" @click="handleBatchDelete">删除</el-button>
            <el-select v-model="genProductId" clearable filterable placeholder="关联商品" style="width:230px" @change="onGenProductChange">
              <el-option v-for="p in productOptions" :key="p.id" :label="`${p.product_code} ${p.name}`" :value="p.id" />
            </el-select>
            <el-select v-model="genScriptId" clearable filterable placeholder="关联脚本分镜" style="width:300px">
              <el-option v-for="g in filteredGenScripts" :key="g.id" :label="`${g.title}（共 ${g.count} 个镜头）`" :value="g.id" />
            </el-select>
          </div>
          <el-button type="primary" :loading="wanLoading" @click="generateVideoFromHeader">生成视频</el-button>
        </div>
      </template>

      <el-table :data="list" stripe @selection-change="onSelectionChange">
        <el-table-column type="selection" width="45" />
        <el-table-column prop="video_code" label="编号" width="90" />
        <el-table-column prop="script_title" label="脚本标题" min-width="220" show-overflow-tooltip />
        <el-table-column prop="product_name" label="关联商品" min-width="160" show-overflow-tooltip />
        <el-table-column label="生成进度" width="180">
          <template #default="{ row }">
            <el-progress v-if="rowProgress(row) > 0" :percentage="rowProgress(row)" :status="rowProgress(row) >= 100 ? 'success' : undefined" />
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="发布平台" width="130">
          <template #default="{ row }">
            <el-link v-if="platformLink(row.publish_platform)" type="primary" :href="platformLink(row.publish_platform)" target="_blank" :underline="false">{{ row.publish_platform }}</el-link>
            <span v-else>{{ row.publish_platform || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="发布状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.publish_status === text.published ? 'success' : row.publish_status === text.reviewing ? 'warning' : 'info'" size="small">{{ row.publish_status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="300" fixed="right">
          <template #default="{ row }">
            <div class="action-row">
              <el-button class="action-btn" size="small" :loading="wanLoadingId === row.id" @click="generateWithWan(row)">万相生成</el-button>
              <el-button class="action-btn" size="small" @click="showDetail(row)">详情</el-button>
              <el-button class="action-btn" size="small" @click="showDialog(row)">编辑</el-button>
              <el-button class="action-btn danger-btn" size="small" @click="handleDelete(row.id)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="`编辑视频：${form.video_code || ''}`" width="860px">
      <el-form :model="form" label-width="100px">
        <!-- 基本信息：生成后锁定，不可修改 -->
        <div class="form-section">
          <div class="section-title">基本信息（生成后锁定）</div>
          <el-row :gutter="16">
            <el-col :span="12"><el-form-item label="视频编号"><el-input v-model="form.video_code" disabled /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="生成工具"><el-input :model-value="form.generate_tool || '通义万相'" disabled /></el-form-item></el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="脚本标题">
                <div class="readonly-field">
                  <span>{{ form.script_title || '未选择' }}</span>
                  <el-tag v-if="scriptShotCount" size="small" type="info">{{ scriptShotCount }} 个镜头</el-tag>
                </div>
              </el-form-item>
            </el-col>
            <el-col :span="12"><el-form-item label="关联商品"><div class="readonly-field">{{ form.product_name || '未选择' }}</div></el-form-item></el-col>
          </el-row>
        </div>

        <!-- 任务管理：人工可编辑 -->
        <div class="form-section">
          <div class="section-title">任务管理</div>
          <el-row :gutter="16">
            <el-col :span="12"><el-form-item label="素材状态"><el-select v-model="form.material_status"><el-option :label="text.pending" :value="text.pending" /><el-option :label="text.generating" :value="text.generating" /><el-option :label="text.done" :value="text.done" /><el-option :label="text.optimize" :value="text.optimize" /></el-select></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="优先级"><el-select v-model="form.priority"><el-option label="P1（高）" value="P1" /><el-option label="P2（中）" value="P2" /><el-option label="P3（低）" value="P3" /></el-select></el-form-item></el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="12"><el-form-item label="负责人"><el-input v-model="form.editor" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="版本"><el-input v-model="form.version" /></el-form-item></el-col>
          </el-row>
          <el-form-item label="质检项"><el-input v-model="form.quality_items" type="textarea" /></el-form-item>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="发布平台">
                <el-select v-model="form.publish_platform" filterable allow-create default-first-option placeholder="选择或输入平台" style="width:100%">
                  <el-option v-for="p in platformOptions" :key="p" :label="p" :value="p" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12"><el-form-item label="发布状态"><el-select v-model="form.publish_status"><el-option :label="text.unpublished" :value="text.unpublished" /><el-option :label="text.reviewing" :value="text.reviewing" /><el-option :label="text.published" :value="text.published" /></el-select></el-form-item></el-col>
          </el-row>
        </div>

        <!-- 重新生成参数：仅再次提交万相生成时生效 -->
        <div class="form-section">
          <div class="section-title">重新生成参数（仅在再次提交万相生成时生效）</div>
          <el-row :gutter="16">
            <el-col :span="8">
              <el-form-item label="分辨率">
                <el-select v-model="form.wan_resolution">
                  <el-option label="720P（省钱）" value="720P" />
                  <el-option label="1080P（高清）" value="1080P" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="画面比例">
                <el-select v-model="form.wan_ratio">
                  <el-option label="16:9（横屏）" value="16:9" />
                  <el-option label="9:16（竖屏）" value="9:16" />
                  <el-option label="1:1（方形）" value="1:1" />
                  <el-option label="4:3" value="4:3" />
                  <el-option label="3:4" value="3:4" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8"><el-form-item label="水印"><el-switch v-model="form.wan_watermark" /></el-form-item></el-col>
          </el-row>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存任务</el-button>
        <el-button type="success" :loading="wanLoading" @click="generateFromDialog">保存并重新生成</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="视频任务详情" size="620px" destroy-on-close>
      <div v-if="currentDetail" class="detail-panel">
        <div class="detail-head">
          <el-tag>{{ currentDetail.video_code }}</el-tag>
          <el-link v-if="platformLink(currentDetail.publish_platform)" type="primary" :href="platformLink(currentDetail.publish_platform)" target="_blank" :underline="false" style="font-size:20px;font-weight:600">{{ currentDetail.publish_platform }}</el-link>
          <strong v-else>{{ currentDetail.publish_platform || text.noPlatform }}</strong>
        </div>
        <div v-if="currentDetail.video_url" class="video-wrap">
          <video :src="currentDetail.video_url" controls playsinline style="width:100%;border-radius:12px;background:#000"></video>
          <a :href="currentDetail.video_url" target="_blank" class="video-link">在新窗口打开成品视频</a>
        </div>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="脚本标题">{{ currentDetail.script_title || '-' }}</el-descriptions-item>
          <el-descriptions-item label="关联商品">{{ currentDetail.product_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="素材状态">{{ displayMaterialStatus(currentDetail.material_status) }}</el-descriptions-item>
          <el-descriptions-item label="生成工具">{{ currentDetail.generate_tool || '-' }}</el-descriptions-item>
          <el-descriptions-item label="生成状态">{{ currentDetail.generate_status || '-' }}</el-descriptions-item>
          <el-descriptions-item label="生成任务ID">{{ currentDetail.generate_task_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="负责人">{{ currentDetail.editor || '-' }}</el-descriptions-item>
          <el-descriptions-item label="版本">{{ currentDetail.version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="发布状态">{{ currentDetail.publish_status || '-' }}</el-descriptions-item>
        </el-descriptions>
        <h3>质检项</h3><pre class="detail-content">{{ currentDetail.quality_items || text.noText }}</pre>
        <h3>备注</h3><pre class="detail-content">{{ currentDetail.notes || text.noText }}</pre>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { productsApi, scriptsApi, videosApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const text = {
  pending: '待准备',
  generating: '生成中',
  done: '已完成',
  optimize: '待优化',
  unpublished: '未发布',
  reviewing: '审核中',
  published: '已发布',
  addVideo: '新增视频',
  editVideo: '编辑视频',
  noQa: '暂无质检项',
  noText: '暂无内容',
  noPlatform: '未设置平台',
  noName: '未命名脚本',
  noShotTime: '未设置镜头时间',
}

// 各平台创作者发布页入口（平台改版时只需改这里）
const platformLinks = {
  '抖音': 'https://creator.douyin.com/creator-micro/content/upload',
  '快手': 'https://cp.kuaishou.com/article/publish/video',
  '小红书': 'https://creator.xiaohongshu.com/publish/publish',
  '视频号': 'https://channels.weixin.qq.com',
  '哔哩哔哩': 'https://member.bilibili.com/platform/upload/video/frame',
  '淘宝逛逛': 'https://creator.guanghe.taobao.com/#/workspace/gg',
}
const platformOptions = Object.keys(platformLinks)
const platformLink = (name) => (name && platformLinks[name]) || ''

const list = ref([])
const selectedIds = ref([])
const dialogVisible = ref(false)
const detailVisible = ref(false)
const currentDetail = ref(null)
const form = ref({})
const scriptList = ref([])
const productOptions = ref([])
const genProductId = ref(null)
const genScriptId = ref(null)
const wanLoading = ref(false)
const wanLoadingId = ref(null)
const progressMap = reactive({})
const progressMessage = ref('')
const dialogProgress = ref(0)
const pollingTimers = new Map()

const loadList = async () => {
  const res = await videosApi.list({ limit: 500 })
  list.value = res.data
}
const loadScripts = async () => {
  const res = await scriptsApi.list({ limit: 500 })
  scriptList.value = res.data
}
const loadProducts = async () => {
  const res = await productsApi.list({ limit: 500 })
  productOptions.value = res.data
}
const scriptGroups = computed(() => {
  const groups = new Map()
  for (const s of scriptList.value) {
    const key = s.title || `S${s.id}`
    if (!groups.has(key)) groups.set(key, { id: s.id, title: s.title, product_id: s.product_id, count: 0 })
    groups.get(key).count += 1
  }
  return [...groups.values()]
})
const groupLabel = (group) => `${group.title}（共 ${group.count} 个镜头）`
const filteredGenScripts = computed(() => {
  if (!genProductId.value) return scriptGroups.value
  return scriptGroups.value.filter(g => g.product_id === genProductId.value)
})
const onGenProductChange = () => {
  const matches = filteredGenScripts.value
  // 商品变了，若当前脚本不属于该商品则清空
  if (genScriptId.value && !matches.some(g => g.id === genScriptId.value)) {
    genScriptId.value = null
  }
  // 自动补上该商品对应的脚本分镜（多条时默认选第一条，仍可手动切换）
  if (matches.length > 0) {
    genScriptId.value = matches[0].id
  }
}
const scriptShotCount = computed(() => {
  const group = scriptGroups.value.find(g => g.id === form.value.script_id)
  return group ? group.count : 0
})
const showDetail = (row) => { currentDetail.value = row; detailVisible.value = true }
const displayMaterialStatus = (value) => {
  // '???' 是历史版本写入的脏数据，统一按“待优化”展示
  if (value === '???' || value === text.optimize) return text.optimize
  if (value === text.generating) return text.generating
  if (value === text.done) return text.done
  return value || text.pending
}

const statusProgress = (status) => {
  if (status === 'SUCCEEDED') return 100
  if (status === 'RUNNING') return 55
  if (status === 'PENDING') return 10
  return 0
}
const rowProgress = (row) => {
  if (progressMap[row.id] !== undefined) return progressMap[row.id]
  if (row.generate_status) return statusProgress(row.generate_status)
  if (displayMaterialStatus(row.material_status) === text.done) return 100
  return 0
}

const showDialog = (row) => {
  form.value = row
    ? {
        ...row,
        material_status: displayMaterialStatus(row.material_status),
        wan_resolution: '720P',
        wan_ratio: '16:9',
        wan_watermark: false,
      }
    : {
        video_code: '',
        script_id: null,
        material_status: text.pending,
        generate_tool: '通义万相',
        editor: 'AI视频生成',
        version: 'v1',
        priority: 'P1',
        quality_items: '',
        publish_platform: '抖音',
        publish_status: text.unpublished,
        wan_resolution: '720P',
        wan_ratio: '16:9',
        wan_watermark: false,
      }
  dialogProgress.value = row?.id ? (progressMap[row.id] || 0) : 0
  dialogVisible.value = true
}
const videoPayload = (data) => {
  const { wan_resolution, wan_ratio, wan_watermark, ...payload } = data
  return payload
}
const handleSave = async () => {
  try {
    if (form.value.id) await videosApi.update(form.value.id, videoPayload(form.value))
    else await videosApi.create(videoPayload(form.value))
    ElMessage.success('保存成功')
    dialogVisible.value = false
    loadList()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '保存失败') }
}

const bumpProgress = (videoId, target) => {
  const current = progressMap[videoId] || 0
  progressMap[videoId] = Math.min(target, Math.max(current + 5, current))
  if (form.value.id === videoId) dialogProgress.value = progressMap[videoId]
}
const markProgressDone = (videoId) => {
  progressMap[videoId] = 100
  if (form.value.id === videoId) dialogProgress.value = 100
  progressMessage.value = '万相视频生成已完成，可打开成品视频预览。'
}

const pollWan = async (row) => {
  if (!row.generate_task_id) {
    ElMessage.warning('没有找到万相生成任务ID')
    return
  }
  progressMap[row.id] = progressMap[row.id] || 10
  if (pollingTimers.has(row.id)) clearInterval(pollingTimers.get(row.id))
  const checkOnce = async () => {
    try {
      const res = await videosApi.wanProgress(row.id)
      const status = res.data?.task_status
      if (status) {
        progressMap[row.id] = statusProgress(status)
        if (form.value.id === row.id) dialogProgress.value = progressMap[row.id]
      }
      if (status === 'SUCCEEDED') {
        markProgressDone(row.id)
        clearInterval(pollingTimers.get(row.id))
        pollingTimers.delete(row.id)
        ElMessage.success('万相视频生成完成')
        loadList()
      } else if (status === 'FAILED') {
        progressMessage.value = '万相视频生成失败，请查看任务详情。'
        clearInterval(pollingTimers.get(row.id))
        pollingTimers.delete(row.id)
        ElMessage.error('万相视频生成失败')
        loadList()
      } else {
        progressMessage.value = status === 'PENDING' ? '任务排队中，等待万相开始生成...' : '万相生成中，通常需要 1-5 分钟...'
      }
    } catch (e) {
      bumpProgress(row.id, 85)
      progressMessage.value = e.response?.data?.detail || '正在等待万相生成结果'
    }
  }
  await checkOnce()
  if (!pollingTimers.has(row.id) && (progressMap[row.id] || 0) < 100) {
    pollingTimers.set(row.id, setInterval(checkOnce, 15000))
  }
}

const submitWan = async (video, options = {}) => {
  if (!video.script_id) {
    ElMessage.warning('请先选择脚本分镜标题')
    return false
  }
  wanLoading.value = true
  wanLoadingId.value = video.id || null
  progressMessage.value = '正在提交通义万相视频生成任务...'
  try {
    if (video.id) progressMap[video.id] = 5
    const res = await videosApi.generateWithWan({
      video_id: video.id,
      script_id: video.script_id,
      resolution: options.resolution || '720P',
      ratio: options.ratio || '16:9',
      watermark: Boolean(options.watermark),
    })
    const savedVideo = res.data.video || video
    progressMap[savedVideo.id] = 10
    dialogProgress.value = progressMap[savedVideo.id]
    progressMessage.value = `已提交万相任务：${res.data.task_id}，等待生成...`
    ElMessage.success(`通义万相视频任务已提交，任务ID：${res.data.task_id}`)
    await loadList()
    await pollWan({ ...savedVideo, generate_task_id: savedVideo.generate_task_id || res.data.task_id })
    return true
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '通义万相生成提交失败')
    return false
  } finally {
    wanLoading.value = false
    wanLoadingId.value = null
  }
}

const generateFromDialog = async () => {
  if (!form.value.script_id) {
    ElMessage.warning('请先选择脚本分镜标题')
    return
  }
  let video = form.value
  try {
    if (!video.id) {
      const res = await videosApi.create(videoPayload({ ...form.value, material_status: text.pending }))
      video = res.data
      form.value.id = video.id
      form.value.video_code = video.video_code
    } else {
      await videosApi.update(video.id, videoPayload(form.value))
    }
    await submitWan(video, {
      resolution: form.value.wan_resolution || '720P',
      ratio: form.value.wan_ratio || '16:9',
      watermark: Boolean(form.value.wan_watermark),
    })
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存视频任务失败')
  }
}
const generateWithWan = async (row) => { await submitWan(row, { resolution: '720P', ratio: '16:9', watermark: false }) }
const generateVideoFromHeader = async () => {
  if (!genScriptId.value) {
    ElMessage.warning('请先选择关联商品和脚本分镜')
    return
  }
  const ok = await submitWan({ script_id: genScriptId.value }, { resolution: '720P', ratio: '16:9', watermark: false })
  if (ok) {
    genScriptId.value = null
    genProductId.value = null
  }
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' })
  await videosApi.delete(id)
  ElMessage.success('删除成功')
  loadList()
}
const onSelectionChange = (rows) => { selectedIds.value = rows.map(r => r.id) }
const handleBatchDelete = async () => {
  try {
    await ElMessageBox.confirm(`确认删除选中的 ${selectedIds.value.length} 条视频任务记录？`, '提示', { type: 'warning' })
    const res = await videosApi.batchDelete(selectedIds.value)
    ElMessage.success(res.data.message || '删除成功')
    loadList()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error('批量删除失败：' + (e.response?.data?.detail || '请稍后重试'))
  }
}

onMounted(() => { loadList(); loadScripts(); loadProducts() })
onBeforeUnmount(() => { pollingTimers.forEach(timer => clearInterval(timer)); pollingTimers.clear() })
</script>

<style scoped>
.table-card { margin-top:20px; }
.page-header { display:flex; justify-content:space-between; align-items:center; }
.header-left { display:flex; align-items:center; gap:12px; }
.summary-cell { width:100%; display:block; border:0; background:transparent; color:#5f6673; text-align:left; cursor:pointer; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font:inherit; }
.summary-cell:hover { color:#2454ff; text-decoration:underline; }
.action-row { display:flex; align-items:center; gap:8px; flex-wrap:nowrap; white-space:nowrap; }
.action-row :deep(.el-button) { margin-left:0; }
.action-btn { color:#334155; border-color:#d8e0ea; background:#fff; }
.action-btn:hover { color:#2454ff; border-color:#9db9ff; background:#f5f8ff; }
.danger-btn { color:#f56c6c; border-color:#fbc4c4; }
.danger-btn:hover { color:#f56c6c; border-color:#f56c6c; background:#fef0f0; }
.detail-panel { padding-right:6px; }
.detail-head { display:flex; align-items:center; gap:12px; margin-bottom:16px; }
.detail-head strong { font-size:20px; }
.detail-panel h3 { margin:22px 0 10px; font-size:16px; }
.detail-content { white-space:pre-wrap; word-break:break-word; line-height:1.8; background:#f6f8fb; border:1px solid rgba(20,33,61,.08); border-radius:14px; padding:16px; color:#334155; }
.progress-tip { color:#64748b; font-size:13px; margin-top:6px; }
.muted { color:#94a3b8; }
.video-wrap { margin-bottom:18px; }
.video-link { display:inline-block; margin-top:8px; font-size:13px; color:#2454ff; }
.form-section { padding:14px 16px; margin-bottom:16px; border:1px solid #e5eaf2; border-radius:12px; background:#fbfcfe; }
.form-section + .form-section { margin-top:14px; }
.section-title { font-size:14px; font-weight:600; color:#334155; margin-bottom:12px; padding-left:8px; border-left:3px solid #2454ff; }
.readonly-field { display:flex; align-items:center; gap:8px; min-height:32px; line-height:1.5; color:#334155; padding:0 2px; }
.task-id { font-size:12px; color:#64748b; word-break:break-all; }
</style>
