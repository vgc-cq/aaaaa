<template>
  <div>
    <!-- ============ LangGraph 自主复盘智能体工作台 ============ -->
    <el-card class="agent-card">
      <template #header>
        <div class="page-header">
          <div class="header-left">
            <span style="font-weight:600">LangGraph 自主复盘智能体</span>
            <el-tag :type="statusTagType" size="small">{{ statusText }}</el-tag>
          </div>
          <div class="header-left">
            <el-button size="small" :disabled="!plan" @click="clearPlan">清空结果</el-button>
          </div>
        </div>
      </template>

      <!-- LangGraph 状态图：节点随运行推进高亮 -->
      <el-steps :active="agentStep" align-center finish-status="success" class="graph-steps">
        <el-step title="读取数据" description="collect_context" />
        <el-step title="指标计算" description="metrics（规则）" />
        <el-step title="AI 规划" description="plan（DeepSeek）" />
        <el-step title="人工审批" description="approval" />
        <el-step title="执行工具" description="execute_tools" />
      </el-steps>

      <!-- 运行配置 -->
      <el-form :model="agentForm" label-width="100px" class="agent-form" @submit.prevent>
        <el-row :gutter="16">
          <el-col :span="14">
            <el-form-item label="复盘目标">
              <el-input v-model="agentForm.goal" placeholder="例如：复盘全部投流数据，给出放量/优化/停投建议" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="只看视频">
              <el-select v-model="agentForm.video_id" clearable filterable placeholder="全部视频" style="width:100%">
                <el-option v-for="v in videoOptions" :key="v.id" :label="`${v.video_code} ${v.script_title || ''}`" :value="v.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label-width="0">
              <el-button type="primary" :loading="agentStep === 1 || agentStep === 2 || agentStep === 3" @click="runAgent">开始智能体复盘</el-button>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <!-- 计划与人工审批 -->
      <div v-if="plan" class="plan-panel">
        <el-divider content-position="left">AI 执行计划（待人工审批）</el-divider>
        <el-alert :title="plan.summary || '智能体已生成执行计划'" type="info" :closable="false" show-icon />
        <div v-if="plan.risks && plan.risks.length" class="risk-row">
          <span class="risk-label">风险提示：</span>
          <el-tag v-for="(risk, i) in plan.risks" :key="i" type="danger" size="small" style="margin-right:8px">{{ risk.reason }}</el-tag>
        </div>

        <el-table :data="plan.actions || []" size="small" border stripe class="action-table">
          <el-table-column width="45">
            <template #default="{ row, $index }">
              <el-checkbox :model-value="selectedIndexes.includes($index)" @change="toggleAction($index)" />
            </template>
          </el-table-column>
          <el-table-column label="工具" width="150">
            <template #default="{ row }">{{ toolLabel(row.tool) }}</template>
          </el-table-column>
          <el-table-column label="处理对象" width="130">
            <template #default="{ row }">投流#{{ row.ad_id ?? '-' }} / 视频#{{ row.video_id ?? '-' }}</template>
          </el-table-column>
          <el-table-column label="建议动作" min-width="180">
            <template #default="{ row }">
              <el-tag :type="decisionTagType(row.decision)" size="small">{{ decisionLabel(row.decision) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="判断理由" min-width="280" show-overflow-tooltip>
            <template #default="{ row }">{{ row.reason || '-' }}</template>
          </el-table-column>
          <el-table-column label="优先级" width="80">
            <template #default="{ row }">
              <el-tag :type="row.priority === 'P0' ? 'danger' : row.priority === 'P1' ? 'warning' : 'info'" size="small">{{ row.priority }}</el-tag>
            </template>
          </el-table-column>
        </el-table>

        <div class="approve-bar">
          <span>已勾选 <b>{{ selectedIndexes.length }}</b> 个动作，确认后才会写入业务数据（人工审批 · human-in-the-loop）</span>
          <div>
            <el-button size="small" @click="toggleSelectAll">全选 / 取消</el-button>
            <el-button size="small" type="danger" :disabled="selectedIndexes.length === 0" :loading="executing" @click="executeActions">
              执行已选动作（{{ selectedIndexes.length }}）
            </el-button>
          </div>
        </div>
      </div>

      <!-- 执行结果 -->
      <div v-if="executionResult" class="execution-panel">
        <el-divider content-position="left">执行结果</el-divider>
        <el-alert :title="`执行完成：成功 ${(executionResult.executed || []).length} 个，跳过 ${(executionResult.skipped || []).length} 个`" type="success" :closable="false" show-icon />
        <el-table v-if="(executionResult.executed || []).length" :data="executionResult.executed" size="small" border stripe style="margin-top:12px">
          <el-table-column prop="index" label="序号" width="70" />
          <el-table-column label="工具" width="180">
            <template #default="{ row }">{{ toolLabel(row.tool) }}</template>
          </el-table-column>
          <el-table-column prop="id" label="记录ID" width="100" />
          <el-table-column prop="result" label="执行结果" min-width="160" />
        </el-table>
        <el-table v-if="(executionResult.skipped || []).length" :data="executionResult.skipped" size="small" border stripe style="margin-top:12px">
          <el-table-column prop="index" label="序号" width="70" />
          <el-table-column prop="reason" label="跳过原因" min-width="240" />
        </el-table>
      </div>
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
        <el-table-column label="问题归因" min-width="260">
          <template #default="{ row }"><div class="multi-line-cell">{{ row.problem_analysis || '暂无归因' }}</div></template>
        </el-table-column>
        <el-table-column label="优化动作" min-width="260">
          <template #default="{ row }"><div class="multi-line-cell">{{ row.next_action || '暂无优化动作' }}</div></template>
        </el-table-column>
        <el-table-column prop="owner" label="负责人" width="110" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === '已完成' ? 'success' : row.status === '分析中' ? 'warning' : 'info'" size="small">{{ row.status || '待复盘' }}</el-tag>
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
          <el-col :span="12"><el-form-item label="状态"><el-select v-model="form.status"><el-option label="待复盘" value="待复盘" /><el-option label="分析中" value="分析中" /><el-option label="已完成" value="已完成" /></el-select></el-form-item></el-col>
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
          <strong>{{ currentDetail.owner || '未分配' }}</strong>
          <el-tag :type="currentDetail.status === '已完成' ? 'success' : 'warning'" size="small">{{ currentDetail.status || '待复盘' }}</el-tag>
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
import { autonomousReviewAgentApi, reviewsApi, videosApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

// ---------- 复盘记录表 ----------
const list = ref([])
const selectedIds = ref([])
const dialogVisible = ref(false)
const detailVisible = ref(false)
const currentDetail = ref(null)
const form = ref({})

const loadList = async () => { const res = await reviewsApi.list(); list.value = res.data }
const showDetail = (row) => { currentDetail.value = row; detailVisible.value = true }
const showDialog = (row) => {
  form.value = row
    ? { ...row }
    : { review_period: '', product_performance: '', content_performance: '', video_performance: '', ad_performance: '', problem_analysis: '', next_action: '', owner: '', status: '待复盘', priority: 'P1' }
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

// ---------- LangGraph 智能体 ----------
const agentForm = ref({ goal: '复盘全部投流数据，给出放量/优化/停投建议', video_id: null })
const videoOptions = ref([])
const agentStep = ref(0) // el-steps active：0 未开始 → 5 全部完成
const plan = ref(null)
const selectedIndexes = ref([])
const executing = ref(false)
const executionResult = ref(null)

const statusText = computed(() => {
  if (agentStep.value === 0) return '待运行'
  if (agentStep.value <= 3) return '智能体运行中…'
  if (agentStep.value === 3) return '等待人工审批'
  if (agentStep.value === 4) return '执行工具中…'
  return '执行完成'
})
const statusTagType = computed(() => {
  if (agentStep.value === 0) return 'info'
  if (agentStep.value <= 3) return 'warning'
  if (agentStep.value === 3) return 'warning'
  return 'success'
})

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms))

const loadVideos = async () => {
  const res = await videosApi.list({ limit: 500 })
  videoOptions.value = res.data
}

const runAgent = async () => {
  plan.value = null
  executionResult.value = null
  selectedIndexes.value = []
  agentStep.value = 1
  await delay(500)
  agentStep.value = 2
  await delay(500)
  agentStep.value = 3
  try {
    const res = await autonomousReviewAgentApi.run({
      goal: agentForm.value.goal,
      video_id: agentForm.value.video_id || undefined,
    })
    if (res.data?.status === 'empty') {
      ElMessage.warning(res.data.message || '没有可分析的投流数据')
      agentStep.value = 0
      return
    }
    plan.value = res.data
    agentStep.value = 3 // 停在人工审批
    ElMessage.success(`智能体已生成 ${(res.data.actions || []).length} 个执行动作，等待审批`)
  } catch (e) {
    agentStep.value = 0
    ElMessage.error(e.response?.data?.detail || '智能体运行失败')
  }
}

const toggleAction = (index) => {
  const i = selectedIndexes.value.indexOf(index)
  if (i >= 0) selectedIndexes.value.splice(i, 1)
  else selectedIndexes.value.push(index)
}
const toolLabel = (tool) => ({
  update_ad_status: '更新投流状态',
  create_video_task: '创建视频优化任务',
  create_review: '生成复盘记录',
  save_knowledge: '沉淀知识库',
})[tool] || tool || '-'
const decisionLabel = (decision) => ({
  scale: '放量',
  stop_and_remake: '停投并重做',
  observe_and_optimize: '观察优化',
  rewrite_hook: '重写钩子',
})[decision] || decision || '优化'
const decisionTagType = (decision) => {
  if (decision === 'scale') return 'success'
  if (decision === 'stop_and_remake') return 'danger'
  return 'warning'
}
const toggleSelectAll = () => {
  const all = plan.value?.actions || []
  if (selectedIndexes.value.length === all.length) selectedIndexes.value = []
  else selectedIndexes.value = all.map((_, i) => i)
}

const executeActions = async () => {
  if (selectedIndexes.value.length === 0) { ElMessage.warning('请先勾选要执行的动作'); return }
  executing.value = true
  agentStep.value = 4
  await delay(600)
  try {
    const res = await autonomousReviewAgentApi.execute({ plan: plan.value, approved_indexes: selectedIndexes.value })
    executionResult.value = res.data
    agentStep.value = 5
    ElMessage.success('执行完成')
    loadList()
  } catch (e) {
    agentStep.value = 3
    ElMessage.error(e.response?.data?.detail || '执行失败')
  } finally {
    executing.value = false
  }
}
const clearPlan = () => {
  plan.value = null
  executionResult.value = null
  selectedIndexes.value = []
  agentStep.value = 0
}

onMounted(() => { loadList(); loadVideos() })
</script>

<style scoped>
.agent-card { margin-top:20px; }
.table-card { margin-top:20px; }
.page-header { display:flex; justify-content:space-between; align-items:center; }
.header-left { display:flex; align-items:center; gap:12px; }
.graph-steps { margin:8px 0 24px; padding:16px 8px; background:#f7f9fc; border-radius:12px; }
.agent-form { margin-bottom:8px; }
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
