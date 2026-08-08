<template>
  <div>
    <el-card class="table-card">
      <template #header>
        <div class="page-header">
          <div class="header-left">
            <span style="font-weight:600">投流数据表</span>
            <el-button type="danger" size="small" :disabled="selectedIds.length === 0" @click="handleBatchDelete">删除</el-button>
          </div>
          <el-button type="primary" @click="showDialog()">新增数据</el-button>
        </div>
      </template>
      <el-table :data="list" stripe @selection-change="onSelectionChange">
        <el-table-column type="selection" width="45" />
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="ad_date" label="投放日期" width="110" />
        <el-table-column label="计划名称" min-width="200">
          <template #default="{ row }"><button class="summary-cell" type="button" @click="showDetail(row)">{{ row.plan_name || '未命名计划' }}</button></template>
        </el-table-column>
        <el-table-column label="关联视频" width="90">
          <template #default="{ row }">{{ videoName(row.video_id) }}</template>
        </el-table-column>
        <el-table-column label="内容方向" min-width="150">
          <template #default="{ row }"><div class="multi-line-cell">{{ row.content_direction || '暂无内容方向' }}</div></template>
        </el-table-column>
        <el-table-column prop="spend" label="消耗" width="80" />
        <el-table-column prop="revenue" label="成交" width="80" />
        <el-table-column prop="roi" label="ROI" width="80">
          <template #default="{ row }"><el-tag :type="row.roi >= 3 ? 'success' : row.roi >= 1 ? 'warning' : 'danger'" size="small">{{ row.roi }}</el-tag></template>
        </el-table-column>
        <el-table-column label="复盘建议" min-width="240">
          <template #default="{ row }"><div class="multi-line-cell">{{ row.review_suggestion || '暂无复盘建议' }}</div></template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }"><div class="action-row"><el-button class="action-btn" size="small" @click="showDetail(row)">详情</el-button><el-button class="action-btn" size="small" @click="showDialog(row)">编辑</el-button><el-button class="action-btn" size="small" @click="handleDelete(row.id)">删除</el-button></div></template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑投流数据' : '新增投流数据'" width="760px">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="手动录入" name="manual">
          <el-form :model="form" label-width="110px">
            <el-form-item label="投放日期"><el-date-picker v-model="form.ad_date" type="date" value-format="YYYY-MM-DD" placeholder="选择投放日期" style="width:100%" /></el-form-item>
            <el-form-item label="关联视频ID"><el-input-number v-model="form.video_id" :min="0" /></el-form-item>
            <el-form-item label="计划名称"><el-input v-model="form.plan_name" /></el-form-item>
            <el-row :gutter="16"><el-col :span="12"><el-form-item label="内容方向"><el-input v-model="form.content_direction" /></el-form-item></el-col><el-col :span="12"><el-form-item label="负责人"><el-input v-model="form.owner" /></el-form-item></el-col></el-row>
            <el-row :gutter="16"><el-col :span="12"><el-form-item label="状态"><el-input v-model="form.status" /></el-form-item></el-col><el-col :span="12"><el-form-item label="优先级"><el-select v-model="form.priority"><el-option label="P0" value="P0"/><el-option label="P1" value="P1"/><el-option label="P2" value="P2"/></el-select></el-form-item></el-col></el-row>
            <el-row :gutter="16"><el-col :span="12"><el-form-item label="播放量"><el-input-number v-model="form.play_count" :min="0" /></el-form-item></el-col><el-col :span="12"><el-form-item label="2秒跳出率"><el-input-number v-model="form.bounce_rate_2s" :min="0" :max="100" /></el-form-item></el-col></el-row>
            <el-row :gutter="16"><el-col :span="12"><el-form-item label="5秒完播率"><el-input-number v-model="form.completion_rate_5s" :min="0" :max="100" /></el-form-item></el-col><el-col :span="12"><el-form-item label="完播率"><el-input-number v-model="form.completion_rate" :min="0" :max="100" /></el-form-item></el-col></el-row>
            <el-row :gutter="16"><el-col :span="12"><el-form-item label="消耗"><el-input-number v-model="form.spend" :min="0" /></el-form-item></el-col><el-col :span="12"><el-form-item label="展现"><el-input-number v-model="form.impressions" :min="0" /></el-form-item></el-col></el-row>
            <el-row :gutter="16"><el-col :span="12"><el-form-item label="点击"><el-input-number v-model="form.clicks" :min="0" /></el-form-item></el-col><el-col :span="12"><el-form-item label="购物车点击"><el-input-number v-model="form.cart_clicks" :min="0" /></el-form-item></el-col></el-row>
            <el-row :gutter="16"><el-col :span="12"><el-form-item label="成交金额"><el-input-number v-model="form.revenue" :min="0" /></el-form-item></el-col><el-col :span="12"><el-form-item label="订单数"><el-input-number v-model="form.orders" :min="0" /></el-form-item></el-col></el-row>
            <el-form-item label="异常判断"><el-input v-model="form.anomaly" /></el-form-item>
            <el-form-item label="用户反馈"><el-input v-model="form.feedback" type="textarea" /></el-form-item>
            <el-form-item label="复盘建议"><el-input v-model="form.review_suggestion" type="textarea" /></el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="一键导入" name="import">
          <el-alert title="导入说明：字段与千川素材报表口径一致（投放日期、视频编号、计划名称、消耗、展现、点击、加购、成交、订单等）。视频编号留空或未匹配到视频任务时自动留空关联；CTR / ROI 导入时自动计算。" type="info" show-icon :closable="false" style="margin-bottom:14px" />
          <el-upload drag :auto-upload="false" :limit="1" accept=".xlsx" :on-change="onFileChange" :on-remove="onFileRemove">
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽 .xlsx 文件到此处，或 <em>点击选择文件</em></div>
            <template #tip>
              <div class="el-upload__tip" style="color:#697386">
                支持一次导入多条投流记录。
                <el-link type="primary" :underline="false" @click="downloadTemplate">下载导入模板</el-link>
              </div>
            </template>
          </el-upload>
          <el-button type="primary" :loading="importing" @click="handleImport">一键导入</el-button>
          <div v-if="importResult" style="margin-top:16px">
            <el-alert :title="`导入完成：成功 ${importResult.imported} 条，跳过 ${importResult.skipped} 条`" type="success" :closable="false" style="margin-bottom:12px" />
            <el-table :data="importResult.results" max-height="280" size="small" border>
              <el-table-column prop="plan_name" label="计划名称" min-width="150" show-overflow-tooltip />
              <el-table-column prop="ad_date" label="投放日期" width="110" />
              <el-table-column prop="video_code" label="视频编号" width="90" />
              <el-table-column prop="spend" label="消耗" width="80" />
              <el-table-column prop="roi" label="ROI" width="80" />
              <el-table-column prop="status" label="结果" width="90" />
              <el-table-column prop="message" label="备注" min-width="180" show-overflow-tooltip />
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button v-if="form.id || activeTab === 'manual'" type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="投流数据详情" size="580px" destroy-on-close>
      <div v-if="currentDetail" class="detail-panel">
        <div class="detail-head"><el-tag>{{ currentDetail.priority || 'P1' }}</el-tag><strong>{{ currentDetail.plan_name || '未命名计划' }}</strong></div>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="投放日期">{{ currentDetail.ad_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="关联视频">{{ videoName(currentDetail.video_id) }}</el-descriptions-item>
          <el-descriptions-item label="内容方向">{{ currentDetail.content_direction || '-' }}</el-descriptions-item>
          <el-descriptions-item label="播放/跳出/完播">{{ currentDetail.play_count || 0 }} / {{ currentDetail.bounce_rate_2s || 0 }}% / {{ currentDetail.completion_rate || 0 }}%</el-descriptions-item>
          <el-descriptions-item label="消耗/成交/ROI">¥{{ currentDetail.spend || 0 }} / ¥{{ currentDetail.revenue || 0 }} / {{ currentDetail.roi || 0 }}</el-descriptions-item>
          <el-descriptions-item label="加购/订单">{{ currentDetail.cart_clicks || 0 }} / {{ currentDetail.orders || 0 }}</el-descriptions-item>
          <el-descriptions-item label="负责人">{{ currentDetail.owner || '-' }}</el-descriptions-item>
        </el-descriptions>
        <h3>异常判断</h3><pre class="detail-content">{{ currentDetail.anomaly || '正常' }}</pre>
        <h3>用户反馈</h3><pre class="detail-content">{{ currentDetail.feedback || '暂无内容' }}</pre>
        <h3>复盘建议</h3><pre class="detail-content">{{ currentDetail.review_suggestion || '暂无内容' }}</pre>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import { adsApi, videosApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const list = ref([])
const videoList = ref([])
const selectedIds = ref([])
const dialogVisible = ref(false)
const detailVisible = ref(false)
const currentDetail = ref(null)
const form = ref({})
const activeTab = ref('manual')
const importFile = ref(null)
const importing = ref(false)
const importResult = ref(null)

const loadList = async () => { const res = await adsApi.list(); list.value = res.data }
const loadVideos = async () => { const res = await videosApi.list({ limit: 500 }); videoList.value = res.data }
const videoName = (id) => {
  const v = videoList.value.find(x => x.id === id)
  return v ? v.video_code : (id || '-')
}
const showDetail = (row) => { currentDetail.value = row; detailVisible.value = true }
const showDialog = (row) => {
  activeTab.value = 'manual'
  importFile.value = null
  importResult.value = null
  form.value = row ? { ...row } : { ad_date: '', video_id: null, plan_name: '', content_direction: '', play_count: 0, bounce_rate_2s: 0, completion_rate_5s: 0, completion_rate: 0, spend: 0, impressions: 0, clicks: 0, cart_clicks: 0, revenue: 0, orders: 0, anomaly: '', review_suggestion: '', feedback: '', owner: '', status: '投放中', priority: 'P1' }
  dialogVisible.value = true
}
const handleSave = async () => { try { if (form.value.id) await adsApi.update(form.value.id, form.value); else await adsApi.create(form.value); ElMessage.success('保存成功'); dialogVisible.value = false; loadList() } catch (e) { ElMessage.error(e.response?.data?.detail || '保存失败') } }
const handleDelete = async (id) => { await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' }); await adsApi.delete(id); ElMessage.success('删除成功'); loadList() }
const onSelectionChange = (rows) => { selectedIds.value = rows.map(r => r.id) }

const handleBatchDelete = async () => {
  if (selectedIds.value.length === 0) { ElMessage.warning('请先勾选要删除的记录'); return }
  try {
    await ElMessageBox.confirm(`确认删除选中的 ${selectedIds.value.length} 条投流数据记录？`, '提示', { type: 'warning' })
    const res = await adsApi.batchDelete(selectedIds.value)
    ElMessage.success(res.data.message || '删除成功')
    loadList()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error('批量删除失败：' + (e.response?.data?.detail || '请稍后重试'))
  }
}

const onFileChange = (uploadFile) => { importFile.value = uploadFile.raw; importResult.value = null }
const onFileRemove = () => { importFile.value = null; importResult.value = null }
const downloadTemplate = async () => {
  try {
    const res = await adsApi.importTemplate()
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = '投流数据导入模板.xlsx'
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error('模板下载失败')
  }
}
const handleImport = async () => {
  if (!importFile.value) { ElMessage.warning('请先选择 .xlsx 文件'); return }
  importing.value = true
  try {
    const formData = new FormData()
    formData.append('file', importFile.value)
    const res = await adsApi.importData(formData)
    importResult.value = res.data
    ElMessage.success(res.data.message || '导入成功')
    loadList()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '导入失败')
  } finally {
    importing.value = false
  }
}

onMounted(() => { loadList(); loadVideos() })
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
.multi-line-cell { display:-webkit-box; -webkit-box-orient:vertical; -webkit-line-clamp:3; overflow:hidden; white-space:normal; line-height:1.6; max-height:calc(1.6em * 3); color:#5f6673; }
</style>
