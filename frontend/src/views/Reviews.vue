<template>
  <div>
    <!-- ============ 投流数据复盘智能体（LangGraph） ============ -->
    <el-card class="agent-card">
      <template #header>
        <div class="page-header">
          <div class="header-left">
            <span style="font-weight:600">投流数据复盘智能体（LangGraph）</span>
            <el-tag :type="statusTagType" size="small">{{ statusText }}</el-tag>
          </div>
          <div class="header-left">
            <el-button size="small" @click="clearResult">清空结果</el-button>
          </div>
        </div>
      </template>

      <!-- LangGraph 状态图：节点随运行推进高亮 -->
      <el-steps :active="agentStep" align-center finish-status="success" class="graph-steps">
        <el-step title="读取数据" description="扫描未复盘投流" />
        <el-step title="指标计算" description="ROI/CTR/CVR（规则）" />
        <el-step title="AI 复盘" description="DeepSeek 结论与建议" />
        <el-step title="写回建议" description="ad_data + 复盘表" />
        <el-step title="记录日志" description="agent_runs" />
      </el-steps>

      <div class="agent-tip">
        智能体会自动扫描"还没有复盘建议"的投流数据，逐条计算指标并生成复盘结论与优化建议
        （建议直接给出，无需人工审批）。后台也会按设定间隔自动巡检（backend/.env 的 REVIEW_INTERVAL_MINUTES 控制）。
      </div>
      <el-form inline>
        <el-form-item label="每批数量">
          <el-input-number v-model="reviewLimit" :min="1" :max="20" />
        </el-form-item>
        <el-form-item label="重新复盘">
          <el-checkbox v-model="reviewForce">强制重新复盘（含已复盘）</el-checkbox>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="running" @click="runAgent">复盘未复盘投流数据</el-button>
          <el-button :disabled="running" @click="loadLogs">刷新记录</el-button>
        </el-form-item>
      </el-form>

      <div v-if="reviewResult" class="result-panel">
        <el-divider content-position="left">本次复盘结果（建议直接给出）</el-divider>
        <el-alert :title="reviewResult.message" type="success" :closable="false" show-icon />
        <el-table :data="reviewResult.results" size="small" border stripe style="margin-top:12px">
          <el-table-column label="视频" width="110">
            <template #default="{ row }">{{ row.video_code || `视频#${row.video_id}` }}</template>
          </el-table-column>
          <el-table-column prop="content_direction" label="内容方向" min-width="140" show-overflow-tooltip />
          <el-table-column label="ROI" width="80">
            <template #default="{ row }">{{ row.metrics?.roi ?? '-' }}</template>
          </el-table-column>
          <el-table-column label="评级" width="80">
            <template #default="{ row }">
              <el-tag :type="ratingTagType(row.review?.rating)" size="small">{{ row.review?.rating || '-' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="决策" width="110">
            <template #default="{ row }">{{ row.review?.decision || '-' }}</template>
          </el-table-column>
          <el-table-column label="总体判断" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">{{ row.review?.summary || '-' }}</template>
          </el-table-column>
          <el-table-column label="优化建议" min-width="260" show-overflow-tooltip>
            <template #default="{ row }">{{ (row.review?.suggestions || []).join('；') || '-' }}</template>
          </el-table-column>
        </el-table>
      </div>

      <el-divider content-position="left">最近复盘运行记录</el-divider>
      <el-table :data="logs" size="small" border>
        <el-table-column prop="created_at" label="时间" min-width="170" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column prop="products_processed" label="复盘条数" width="100" />
        <el-table-column label="说明" min-width="220">
          <template #default="{ row }">{{ row.summary?.message || '-' }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- ============ 复盘记录表 ============ -->
    <el-card class="table-card">
      <template #header>
        <div class="page-header">
          <div class="header-left">
            <span style="font-weight:600">复盘记录表</span>
            <el-button type="danger" size="small" :disabled="selectedIds.length === 0" @click="handleBatchDelete">删除</el-button>
          </div>
          <el-button type="primary" @click="showDialog()">新增复盘</el-button>
        </div>
      </template>

      <el-table :data="list" stripe @selection-change="onTableSelectionChange">
        <el-table-column type="selection" width="45" />
        <el-table-column label="复盘周期" width="160">
          <template #default="{ row }">
            <button class="summary-cell" type="button" @click="showDetail(row)">{{ row.review_period || '未命名周期' }}</button>
          </template>
        </el-table-column>
        <el-table-column label="关联投流 / 视频" width="150">
          <template #default="{ row }">
            <span>投流#{{ row.ad_id ?? '-' }}</span>
            <span style="margin-left:8px">视频#{{ row.video_id ?? '未关联' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="视频" width="90">
          <template #default="{ row }">{{ row.video_code || (row.video_id ? `视频#${row.video_id}` : '-') }}</template>
        </el-table-column>
        <el-table-column prop="content_direction" label="内容方向" min-width="130" show-overflow-tooltip />
        <el-table-column label="评级" width="80">
          <template #default="{ row }">
            <el-tag :type="ratingTagType(row.review_level)" size="small">{{ row.review_level || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="decision" label="决策" width="110" />
        <el-table-column prop="summary" label="总体判断" min-width="170" show-overflow-tooltip />
        <el-table-column label="问题归因" min-width="260">
          <template #default="{ row }"><div class="multi-line-cell">{{ row.problem_analysis || '暂无归因' }}</div></template>
        </el-table-column>
        <el-table-column label="优化动作" min-width="260">
          <template #default="{ row }"><div class="multi-line-cell">{{ row.next_action || '暂无优化动作' }}</div></template>
        </el-table-column>
        <el-table-column prop="owner" label="负责人" width="110" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="reviewStatusTagType(row.status)" size="small">{{ row.status || '待处理' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <div class="action-row">
              <el-button class="action-btn" size="small" @click="showDetail(row)">详情</el-button>
              <el-button class="action-btn" size="small" @click="showDialog(row)">编辑</el-button>
              <el-button class="action-btn danger-btn" size="small" @click="handleDelete(row.id)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑复盘 -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑复盘' : '新增复盘'" width="720px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="复盘周期"><el-input v-model="form.review_period" placeholder="如：2026年8月第1周" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="负责人"><el-input v-model="form.owner" /></el-form-item></el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="form.status">
                <el-option label="待处理" value="待处理" />
                <el-option label="认可" value="认可" />
                <el-option label="不认可" value="不认可" />
                <el-option label="已完成" value="已完成" />
              </el-select>
              <div class="memory-tip">选择"认可/不认可"会写入智能体经验记忆，影响以后生成</div>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="问题归因"><el-input v-model="form.problem_analysis" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="优化动作"><el-input v-model="form.next_action" type="textarea" :rows="3" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="商品表现"><el-input v-model="form.product_performance" type="textarea" :rows="2" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="内容表现"><el-input v-model="form.content_performance" type="textarea" :rows="2" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="视频表现"><el-input v-model="form.video_performance" type="textarea" :rows="2" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="投流表现"><el-input v-model="form.ad_performance" type="textarea" :rows="2" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailVisible" title="复盘详情" size="600px" destroy-on-close>
      <div v-if="currentDetail" class="detail-panel">
        <div class="detail-head">
          <el-tag>{{ currentDetail.review_period || '复盘' }}</el-tag>
          <el-tag type="info">投流#{{ currentDetail.ad_id ?? '-' }}</el-tag>
          <el-tag type="info">视频#{{ currentDetail.video_id ?? '未关联' }}</el-tag>
          <strong>{{ currentDetail.owner || '未分配' }}</strong>
          <el-tag :type="reviewStatusTagType(currentDetail.status)" size="small">{{ currentDetail.status || '待处理' }}</el-tag>
        </div>
        <h3>问题归因</h3><pre class="detail-content">{{ currentDetail.problem_analysis || '暂无' }}</pre>
        <h3>优化动作</h3><pre class="detail-content">{{ currentDetail.next_action || '暂无' }}</pre>
        <h3>商品 / 内容 / 视频 / 投流表现</h3>
        <pre class="detail-content">
商品：{{ currentDetail.product_performance || '暂无' }}
内容：{{ currentDetail.content_performance || '暂无' }}
视频：{{ currentDetail.video_performance || '暂无' }}
投流：{{ currentDetail.ad_performance || '暂无' }}</pre>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { autonomousReviewAgentApi, reviewsApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

// ---------- 复盘记录表 ----------
const list = ref([])
const selectedIds = ref([])
const dialogVisible = ref(false)
const detailVisible = ref(false)
const currentDetail = ref(null)
const form = ref({})
const reviewStatusTagType = (status) => {
  if (status === '认可' || status === '已完成') return 'success'
  if (status === '不认可') return 'danger'
  if (status === '待处理' || status === '分析中') return 'warning'
  return 'info'
}

const loadList = async () => { const res = await reviewsApi.list(); list.value = res.data }
const showDetail = (row) => { currentDetail.value = row; detailVisible.value = true }
const showDialog = (row) => {
  form.value = row
    ? { ...row }
    : { review_period: '', product_performance: '', content_performance: '', video_performance: '', ad_performance: '', problem_analysis: '', next_action: '', owner: '', status: '待处理', priority: 'P1' }
  dialogVisible.value = true
}
const handleSave = async () => {
  try {
    if (form.value.id) await reviewsApi.update(form.value.id, form.value)
    else await reviewsApi.create(form.value)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    loadList()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '保存失败') }
}
const handleDelete = async (id) => {
  await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' })
  await reviewsApi.delete(id)
  ElMessage.success('删除成功')
  loadList()
}
const onTableSelectionChange = (rows) => { selectedIds.value = rows.map(r => r.id) }
const handleBatchDelete = async () => {
  try {
    await ElMessageBox.confirm(`确认删除选中的 ${selectedIds.value.length} 条复盘记录？`, '提示', { type: 'warning' })
    const res = await reviewsApi.batchDelete(selectedIds.value)
    ElMessage.success(res.data.message || '删除成功')
    loadList()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error('批量删除失败：' + (e.response?.data?.detail || '请稍后重试'))
  }
}

// ---------- 投流复盘智能体（LangGraph） ----------
const reviewLimit = ref(5)
const reviewForce = ref(false)
const running = ref(false)
const agentStep = ref(0) // el-steps active：0 未开始 → 5 全部完成
const reviewResult = ref(null)
const logs = ref([])

const statusText = computed(() => {
  if (agentStep.value === 0) return '待运行'
  if (agentStep.value < 5) return '智能体运行中…'
  return '复盘完成'
})
const statusTagType = computed(() => {
  if (agentStep.value === 0) return 'info'
  if (agentStep.value < 5) return 'warning'
  return 'success'
})
const ratingTagType = (rating) => {
  if (rating === '优秀') return 'success'
  if (rating === '较差') return 'danger'
  return 'warning'
}

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms))

const runAgent = async () => {
  running.value = true
  reviewResult.value = null
  agentStep.value = 0
  try {
    agentStep.value = 1
    await delay(400)
    agentStep.value = 2
    await delay(400)
    agentStep.value = 3
    const res = await autonomousReviewAgentApi.run({ limit: reviewLimit.value, force: reviewForce.value })
    agentStep.value = 4
    await delay(300)
    agentStep.value = 5
    reviewResult.value = res.data
    if ((res.data.results || []).length === 0) ElMessage.info(res.data.message || '没有未复盘的投流数据')
    else ElMessage.success(`复盘完成：${res.data.processed} 条投流数据`)
    await loadLogs()
  } catch (e) {
    agentStep.value = 0
    ElMessage.error(e.response?.data?.detail || '复盘失败')
  } finally {
    running.value = false
  }
}

const loadLogs = async () => {
  try {
    const res = await autonomousReviewAgentApi.logs({ limit: 10 })
    logs.value = res.data
  } catch (e) { /* 忽略 */ }
}

const clearResult = () => {
  reviewResult.value = null
  agentStep.value = 0
}

onMounted(() => { loadList(); loadLogs() })
</script>

<style scoped>
.agent-card { margin-top:20px; }
.table-card { margin-top:20px; }
.page-header { display:flex; justify-content:space-between; align-items:center; }
.header-left { display:flex; align-items:center; gap:12px; }
.graph-steps { margin:8px 0 24px; padding:16px 8px; background:#f7f9fc; border-radius:12px; }
.agent-tip { font-size:13px; color:#64748b; line-height:1.7; margin-bottom:14px; }
.result-panel { margin-top:8px; }
.agent-form { margin-bottom:8px; }
.memory-tip { font-size:12px; color:#94a3b8; line-height:1.5; margin-top:4px; }
.plan-panel { margin-top:8px; }
.risk-row { display:flex; align-items:center; margin:12px 0; }
.risk-label { color:#e6a23c; font-weight:600; white-space:nowrap; }
.action-table { margin-top:12px; }
.approve-bar { display:flex; justify-content:space-between; align-items:center; margin-top:14px; padding:12px 14px; background:#fdf6ec; border:1px solid #f5dab1; border-radius:10px; color:#7c5a20; }
.execution-panel { margin-top:8px; }
.summary-cell { width:100%; display:block; border:0; background:transparent; color:#5f6673; text-align:left; cursor:pointer; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font:inherit; }
.summary-cell:hover { color:#2454ff; text-decoration:underline; }
.action-row { display:flex; align-items:center; gap:10px; flex-wrap:nowrap; white-space:nowrap; }
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
.multi-line-cell { display:-webkit-box; -webkit-box-orient:vertical; -webkit-line-clamp:3; overflow:hidden; white-space:normal; line-height:1.6; max-height:calc(1.6em * 3); color:#5f6673; }
</style>
