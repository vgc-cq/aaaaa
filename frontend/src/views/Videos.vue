<template>
  <div>
    <el-card class="table-card">
      <template #header>
        <div class="page-header">
          <div class="header-left">
            <span style="font-weight:600">&#x89c6;&#x9891;&#x751f;&#x4ea7;&#x4efb;&#x52a1;&#x8868;</span>
            <el-button type="danger" size="small" :disabled="selectedIds.length === 0" @click="handleBatchDelete">&#x5220;&#x9664;</el-button>
          </div>
          <el-button type="primary" @click="showDialog()">&#x65b0;&#x589e;&#x89c6;&#x9891;</el-button>
        </div>
      </template>

      <el-table :data="list" stripe @selection-change="onSelectionChange">
        <el-table-column type="selection" width="45" />
        <el-table-column prop="video_code" label="&#x7f16;&#x53f7;" width="90" />
        <el-table-column label="&#x7d20;&#x6750;&#x72b6;&#x6001;" width="110">
          <template #default="{ row }">{{ displayMaterialStatus(row.material_status) }}</template>
        </el-table-column>
        <el-table-column prop="generate_tool" label="&#x751f;&#x6210;&#x5de5;&#x5177;" width="130" />
        <el-table-column prop="editor" label="&#x8d1f;&#x8d23;&#x4eba;" width="100" />
        <el-table-column label="&#x751f;&#x6210;&#x8fdb;&#x5ea6;" width="180">
          <template #default="{ row }">
            <el-progress v-if="rowProgress(row) > 0" :percentage="rowProgress(row)" :status="rowProgress(row) >= 100 ? 'success' : undefined" />
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="&#x8d28;&#x68c0;&#x9879;" min-width="260">
          <template #default="{ row }">
            <button class="summary-cell" type="button" @click="showDetail(row)">{{ row.quality_items || text.noQa }}</button>
          </template>
        </el-table-column>
        <el-table-column prop="publish_platform" label="&#x5e73;&#x53f0;" width="100" />
        <el-table-column label="&#x53d1;&#x5e03;&#x72b6;&#x6001;" width="110">
          <template #default="{ row }">
            <el-tag :type="row.publish_status === text.published ? 'success' : row.publish_status === text.reviewing ? 'warning' : 'info'" size="small">{{ row.publish_status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="&#x64cd;&#x4f5c;" width="340" fixed="right">
          <template #default="{ row }">
            <div class="action-row">
              <el-button class="action-btn" size="small" :loading="jimengLoadingId === row.id" @click="generateWithJimeng(row)">&#x5373;&#x68a6;&#x751f;&#x6210;</el-button>
              <el-button class="action-btn" size="small" :disabled="!extractTaskId(row.notes)" @click="pollJimeng(row)">&#x67e5;&#x8be2;&#x8fdb;&#x5ea6;</el-button>
              <el-button class="action-btn" size="small" @click="showDetail(row)">&#x8be6;&#x60c5;</el-button>
              <el-button class="action-btn" size="small" @click="showDialog(row)">&#x7f16;&#x8f91;</el-button>
              <el-button class="action-btn" size="small" @click="handleDelete(row.id)">&#x5220;&#x9664;</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? text.editVideo : text.addVideo" width="780px">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="&#x89c6;&#x9891;&#x7f16;&#x53f7;"><el-input v-model="form.video_code" /></el-form-item></el-col>
          <el-col :span="12">
            <el-form-item label="&#x811a;&#x672c;&#x5206;&#x955c;">
              <el-select v-model="form.script_id" filterable placeholder="&#x9009;&#x62e9;&#x8981;&#x751f;&#x6210;&#x89c6;&#x9891;&#x7684;&#x5206;&#x955c;&#x6807;&#x9898;" style="width:100%">
                <el-option v-for="script in scriptList" :key="script.id" :label="scriptLabel(script)" :value="script.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-alert type="info" :closable="false" show-icon style="margin:0 0 14px" title="&#x9009;&#x62e9;&#x811a;&#x672c;&#x5206;&#x955c;&#x6807;&#x9898;&#x540e;&#xff0c;&#x5373;&#x68a6; AI &#x4f1a;&#x4f7f;&#x7528;&#x753b;&#x9762;&#x63cf;&#x8ff0;&#x3001;&#x65c1;&#x767d;&#x3001;&#x5b57;&#x5e55;&#x3001;&#x955c;&#x5934;&#x8fd0;&#x52a8;&#x548c; AI &#x63d0;&#x793a;&#x8bcd;&#x751f;&#x6210;&#x89c6;&#x9891;&#x3002;" />
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="&#x7d20;&#x6750;&#x72b6;&#x6001;"><el-select v-model="form.material_status"><el-option :label="text.pending" :value="text.pending" /><el-option :label="text.generating" :value="text.generating" /><el-option :label="text.done" :value="text.done" /><el-option :label="text.optimize" :value="text.optimize" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="&#x751f;&#x6210;&#x5de5;&#x5177;"><el-input v-model="form.generate_tool" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="&#x8d1f;&#x8d23;&#x4eba;"><el-input v-model="form.editor" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="&#x7248;&#x672c;"><el-input v-model="form.version" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="&#x8d28;&#x68c0;&#x9879;"><el-input v-model="form.quality_items" type="textarea" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="&#x53d1;&#x5e03;&#x5e73;&#x53f0;"><el-input v-model="form.publish_platform" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="&#x53d1;&#x5e03;&#x72b6;&#x6001;"><el-select v-model="form.publish_status"><el-option :label="text.unpublished" :value="text.unpublished" /><el-option :label="text.reviewing" :value="text.reviewing" /><el-option :label="text.published" :value="text.published" /></el-select></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="&#x751f;&#x6210;&#x65f6;&#x957f;"><el-select v-model="form.jimeng_duration"><el-option label="5 &#x79d2;" :value="5" /><el-option label="10 &#x79d2;" :value="10" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="&#x5373;&#x68a6;&#x6c34;&#x5370;"><el-switch v-model="form.jimeng_watermark" /></el-form-item></el-col>
        </el-row>
        <el-form-item v-if="dialogProgress > 0" label="&#x751f;&#x6210;&#x8fdb;&#x5ea6;">
          <el-progress :percentage="dialogProgress" :status="dialogProgress >= 100 ? 'success' : undefined" />
          <div class="progress-tip">{{ progressMessage }}</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">&#x53d6;&#x6d88;</el-button>
        <el-button type="primary" @click="handleSave">&#x4fdd;&#x5b58;&#x4efb;&#x52a1;</el-button>
        <el-button type="success" :loading="jimengLoading" @click="generateFromDialog">&#x4fdd;&#x5b58;&#x5e76;&#x63d0;&#x4ea4;&#x5373;&#x68a6;&#x751f;&#x6210;</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="&#x89c6;&#x9891;&#x4efb;&#x52a1;&#x8be6;&#x60c5;" size="560px" destroy-on-close>
      <div v-if="currentDetail" class="detail-panel">
        <div class="detail-head"><el-tag>{{ currentDetail.video_code }}</el-tag><strong>{{ currentDetail.publish_platform || text.noPlatform }}</strong></div>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="&#x811a;&#x672c;ID">{{ currentDetail.script_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="&#x7d20;&#x6750;&#x72b6;&#x6001;">{{ displayMaterialStatus(currentDetail.material_status) }}</el-descriptions-item>
          <el-descriptions-item label="&#x751f;&#x6210;&#x5de5;&#x5177;">{{ currentDetail.generate_tool || '-' }}</el-descriptions-item>
          <el-descriptions-item label="&#x8d1f;&#x8d23;&#x4eba;">{{ currentDetail.editor || '-' }}</el-descriptions-item>
          <el-descriptions-item label="&#x7248;&#x672c;">{{ currentDetail.version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="&#x53d1;&#x5e03;&#x72b6;&#x6001;">{{ currentDetail.publish_status || '-' }}</el-descriptions-item>
        </el-descriptions>
        <h3>&#x8d28;&#x68c0;&#x9879;</h3><pre class="detail-content">{{ currentDetail.quality_items || text.noText }}</pre>
        <h3>&#x5907;&#x6ce8;</h3><pre class="detail-content">{{ currentDetail.notes || text.noText }}</pre>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted, onBeforeUnmount } from 'vue'
import { scriptsApi, videosApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const text = {
  pending: '\u5f85\u51c6\u5907',
  generating: '\u751f\u6210\u4e2d',
  done: '\u5df2\u5b8c\u6210',
  optimize: '\u5f85\u4f18\u5316',
  unpublished: '\u672a\u53d1\u5e03',
  reviewing: '\u5ba1\u6838\u4e2d',
  published: '\u5df2\u53d1\u5e03',
  addVideo: '\u65b0\u589e\u89c6\u9891',
  editVideo: '\u7f16\u8f91\u89c6\u9891',
  noQa: '\u6682\u65e0\u8d28\u68c0\u9879',
  noText: '\u6682\u65e0\u5185\u5bb9',
  noPlatform: '\u672a\u8bbe\u7f6e\u5e73\u53f0',
  noName: '\u672a\u547d\u540d\u811a\u672c',
  noShotTime: '\u672a\u8bbe\u7f6e\u955c\u5934\u65f6\u95f4',
}

const list = ref([])
const selectedIds = ref([])
const dialogVisible = ref(false)
const detailVisible = ref(false)
const currentDetail = ref(null)
const form = ref({})
const scriptList = ref([])
const jimengLoading = ref(false)
const jimengLoadingId = ref(null)
const progressMap = reactive({})
const progressMessage = ref('')
const pollingTimers = new Map()

const loadList = async () => {
  const res = await videosApi.list({ limit: 500 })
  list.value = res.data
}
const loadScripts = async () => {
  const res = await scriptsApi.list({ limit: 500 })
  scriptList.value = res.data
}
const showDetail = (row) => { currentDetail.value = row; detailVisible.value = true }
const scriptLabel = (script) => `${script.script_code || `S${script.id}`}\uFF5C${script.title || text.noName}\uFF5C${script.shot_time || text.noShotTime}`
const displayMaterialStatus = (value) => {
  if (value === '???' || value === text.optimize) return text.optimize
  if (value === text.generating) return text.generating
  if (value === text.done) return text.done
  return value || text.pending
}
const extractTaskId = (notes = '') => {
  const match = String(notes || '').match(/ID[:\uFF1A]\s*([^\s\n]+)/)
  return match ? match[1] : ''
}
const rowProgress = (row) => {
  if (progressMap[row.id] !== undefined) return progressMap[row.id]
  if (displayMaterialStatus(row.material_status) === text.generating) return 10
  return 0
}
const extractProgressValue = (value) => {
  if (!value || typeof value !== 'object') return null
  for (const key of ['progress', 'percent', 'percentage']) {
    const n = Number(value[key])
    if (Number.isFinite(n)) return Math.max(0, Math.min(100, n > 1 ? n : n * 100))
  }
  for (const item of Object.values(value)) {
    const n = extractProgressValue(item)
    if (n !== null) return n
  }
  return null
}
const dialogProgress = ref(0)

const showDialog = (row) => {
  form.value = row
    ? { ...row, material_status: displayMaterialStatus(row.material_status), jimeng_duration: 5, jimeng_watermark: false }
    : { video_code: '', script_id: null, material_status: text.pending, generate_tool: '\u5373\u68a6AI', editor: 'AI\u89c6\u9891\u751f\u6210', version: 'v1', quality_items: '', publish_platform: '\u6296\u97f3', publish_status: text.unpublished, jimeng_duration: 5, jimeng_watermark: false }
  dialogProgress.value = row?.id ? (progressMap[row.id] || 0) : 0
  dialogVisible.value = true
}
const videoPayload = (data) => {
  const { jimeng_duration, jimeng_watermark, ...payload } = data
  return payload
}
const handleSave = async () => {
  try {
    if (form.value.id) await videosApi.update(form.value.id, videoPayload(form.value))
    else await videosApi.create(videoPayload(form.value))
    ElMessage.success('\u4fdd\u5b58\u6210\u529f')
    dialogVisible.value = false
    loadList()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '????') }
}

const bumpProgress = (videoId, target) => {
  const current = progressMap[videoId] || 0
  progressMap[videoId] = Math.min(target, Math.max(current + 8, current))
  if (form.value.id === videoId) dialogProgress.value = progressMap[videoId]
}
const markProgressDone = (videoId) => {
  progressMap[videoId] = 100
  if (form.value.id === videoId) dialogProgress.value = 100
  progressMessage.value = '\u5373\u68a6\u89c6\u9891\u751f\u6210\u5df2\u5b8c\u6210\uff0c\u8bf7\u67e5\u770b\u4efb\u52a1\u7ed3\u679c\u3002'
}
const pollJimeng = async (row) => {
  const taskId = extractTaskId(row.notes)
  if (!taskId) {
    ElMessage.warning('\u6ca1\u6709\u627e\u5230\u5373\u68a6\u4efb\u52a1ID')
    return
  }
  progressMap[row.id] = progressMap[row.id] || 20
  if (pollingTimers.has(row.id)) clearInterval(pollingTimers.get(row.id))
  const checkOnce = async () => {
    try {
      const res = await videosApi.jimengProgress(row.id)
      const remoteProgress = Number.isFinite(Number(res.data?.progress)) ? Number(res.data.progress) : extractProgressValue(res.data)
      if (remoteProgress !== null) {
        progressMap[row.id] = Math.max(progressMap[row.id] || 0, Math.round(remoteProgress))
        if (form.value.id === row.id) dialogProgress.value = progressMap[row.id]
      }
      const raw = JSON.stringify(res.data || {})
      const done = res.data?.status === 'completed' || /done|success|finish|completed/i.test(raw) || raw.includes('\u5df2\u5b8c\u6210') || raw.includes('\u6210\u529f')
      const failed = res.data?.status === 'failed' || /fail|error/i.test(raw) || raw.includes('\u5931\u8d25')
      if (done) {
        markProgressDone(row.id)
        clearInterval(pollingTimers.get(row.id))
        pollingTimers.delete(row.id)
        ElMessage.success('\u5373\u68a6\u751f\u6210\u5b8c\u6210')
      } else if (failed) {
        progressMessage.value = '\u5373\u68a6\u751f\u6210\u5931\u8d25\uff0c\u8bf7\u67e5\u770b\u63a5\u53e3\u8fd4\u56de\u3002'
        clearInterval(pollingTimers.get(row.id))
        pollingTimers.delete(row.id)
        ElMessage.error('\u5373\u68a6\u751f\u6210\u5931\u8d25')
      } else {
        bumpProgress(row.id, 90)
      }
    } catch (e) {
      bumpProgress(row.id, 85)
      progressMessage.value = e.response?.data?.detail || '\u6b63\u5728\u7b49\u5f85\u5373\u68a6\u751f\u6210\u7ed3\u679c'
    }
  }
  await checkOnce()
  if (!pollingTimers.has(row.id) && (progressMap[row.id] || 0) < 100) {
    pollingTimers.set(row.id, setInterval(checkOnce, 8000))
  }
}
const submitJimeng = async (video, duration = 5, watermark = false) => {
  if (!video.script_id) {
    ElMessage.warning('\u8bf7\u5148\u9009\u62e9\u811a\u672c\u5206\u955c\u6807\u9898')
    return
  }
  jimengLoading.value = true
  jimengLoadingId.value = video.id || null
  progressMessage.value = '\u6b63\u5728\u63d0\u4ea4\u5373\u68a6\u89c6\u9891\u751f\u6210\u4efb\u52a1...'
  try {
    if (video.id) progressMap[video.id] = 5
    const res = await videosApi.generateWithJimeng({ video_id: video.id, script_id: video.script_id, duration, watermark })
    const savedVideo = res.data.video || video
    progressMap[savedVideo.id] = 15
    dialogProgress.value = progressMap[savedVideo.id]
    progressMessage.value = `\u5df2\u63d0\u4ea4\u5373\u68a6\u4efb\u52a1\uff1a${res.data.task_id}\uff0c\u6b63\u5728\u751f\u6210\u4e2d...`
    ElMessage.success(`\u5373\u68a6\u89c6\u9891\u4efb\u52a1\u5df2\u63d0\u4ea4\uff0c\u4efb\u52a1ID\uff1a${res.data.task_id}`)
    await loadList()
    await pollJimeng({ ...savedVideo, notes: savedVideo.notes || `ID: ${res.data.task_id}` })
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '\u5373\u68a6\u89c6\u9891\u751f\u6210\u63d0\u4ea4\u5931\u8d25')
  } finally {
    jimengLoading.value = false
    jimengLoadingId.value = null
  }
}
const generateFromDialog = async () => {
  if (!form.value.script_id) {
    ElMessage.warning('\u8bf7\u5148\u9009\u62e9\u811a\u672c\u5206\u955c\u6807\u9898')
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
    await submitJimeng(video, form.value.jimeng_duration || 5, Boolean(form.value.jimeng_watermark))
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '\u4fdd\u5b58\u89c6\u9891\u4efb\u52a1\u5931\u8d25')
  }
}
const generateWithJimeng = async (row) => { await submitJimeng(row, 5, false) }
const handleDelete = async (id) => {
  await ElMessageBox.confirm('\u786e\u8ba4\u5220\u9664\uff1f', '\u63d0\u793a', { type: 'warning' })
  await videosApi.delete(id)
    ElMessage.success('\u4fdd\u5b58\u6210\u529f')
  loadList()
}
const onSelectionChange = (rows) => { selectedIds.value = rows.map(r => r.id) }
const handleBatchDelete = async () => {
    ElMessage.warning('\u8bf7\u5148\u9009\u62e9\u811a\u672c\u5206\u955c\u6807\u9898')
  try {
    await ElMessageBox.confirm(`\u786e\u8ba4\u5220\u9664\u9009\u4e2d\u7684 ${selectedIds.value.length} \u6761\u89c6\u9891\u4efb\u52a1\u8bb0\u5f55\uff1f`, '\u63d0\u793a', { type: 'warning' })
    const res = await videosApi.batchDelete(selectedIds.value)
    ElMessage.success(res.data.message || '\u5220\u9664\u6210\u529f')
    loadList()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error('\u6279\u91cf\u5220\u9664\u5931\u8d25\uff1a' + (e.response?.data?.detail || '\u8bf7\u7a0d\u540e\u91cd\u8bd5'))
  }
}

onMounted(() => { loadList(); loadScripts() })
onBeforeUnmount(() => { pollingTimers.forEach(timer => clearInterval(timer)); pollingTimers.clear() })
</script>

<style scoped>
.table-card { margin-top:20px; }
.page-header { display:flex; justify-content:space-between; align-items:center; }
.header-left { display:flex; align-items:center; gap:12px; }
.summary-cell { width:100%; display:block; border:0; background:transparent; color:#5f6673; text-align:left; cursor:pointer; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font:inherit; }
.summary-cell:hover { color:#2454ff; text-decoration:underline; }
.action-row { display:flex; align-items:center; gap:10px; flex-wrap:nowrap; white-space:nowrap; }
.action-row :deep(.el-button) { margin-left:0; }
.action-btn { color:#334155; border-color:#d8e0ea; background:#fff; }
.action-btn:hover { color:#2454ff; border-color:#9db9ff; background:#f5f8ff; }
.detail-panel { padding-right:6px; }
.detail-head { display:flex; align-items:center; gap:12px; margin-bottom:16px; }
.detail-head strong { font-size:20px; }
.detail-panel h3 { margin:22px 0 10px; font-size:16px; }
.detail-content { white-space:pre-wrap; word-break:break-word; line-height:1.8; background:#f6f8fb; border:1px solid rgba(20,33,61,.08); border-radius:14px; padding:16px; color:#334155; }
.progress-tip { color:#64748b; font-size:13px; margin-top:6px; }
.muted { color:#94a3b8; }
</style>
