<template>
  <div>
    <el-card class="table-card">
      <template #header>
        <div class="page-header">
          <div class="header-left">
            <span style="font-weight:600">&#x6570;&#x636e;&#x590d;&#x76d8;&#x8868;</span>
            <el-button type="danger" size="small" :disabled="selectedIds.length === 0" @click="handleBatchDelete">&#x5220;&#x9664;</el-button>
          </div>
          <el-button type="primary" @click="showDialog()">&#x65b0;&#x589e;&#x590d;&#x76d8;</el-button>
        </div>
      </template>

      <el-table :data="list" stripe @selection-change="onSelectionChange">
        <el-table-column type="selection" width="45" />
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="&#x590d;&#x76d8;&#x5468;&#x671f;" width="180">
          <template #default="{ row }">
            <button class="summary-cell" type="button" @click="showDetail(row)">{{ row.review_period || txt.unnamedPeriod }}</button>
          </template>
        </el-table-column>
        <el-table-column label="&#x5546;&#x54c1;&#x8868;&#x73b0;" min-width="220"><template #default="{ row }"><div class="multi-line-cell">{{ row.product_performance || txt.noProduct }}</div></template></el-table-column>
        <el-table-column label="&#x5185;&#x5bb9;&#x8868;&#x73b0;" min-width="220"><template #default="{ row }"><div class="multi-line-cell">{{ row.content_performance || txt.noContent }}</div></template></el-table-column>
        <el-table-column label="&#x6295;&#x6d41;&#x8868;&#x73b0;" min-width="220"><template #default="{ row }"><div class="multi-line-cell">{{ row.ad_performance || txt.noAd }}</div></template></el-table-column>
        <el-table-column label="&#x95ee;&#x9898;&#x5f52;&#x56e0;" min-width="240"><template #default="{ row }"><div class="multi-line-cell">{{ row.problem_analysis || txt.noProblem }}</div></template></el-table-column>
        <el-table-column label="&#x4f18;&#x5316;&#x52a8;&#x4f5c;" min-width="240"><template #default="{ row }"><div class="multi-line-cell">{{ row.next_action || txt.noAction }}</div></template></el-table-column>
        <el-table-column prop="owner" label="&#x8d1f;&#x8d23;&#x4eba;" width="110" />
        <el-table-column label="&#x64cd;&#x4f5c;" width="340" fixed="right">
          <template #default="{ row }">
            <div class="action-row">
              <el-button class="action-btn" size="small" @click="runReviewAgent(row)">&#x667a;&#x80fd;&#x4f53;&#x590d;&#x76d8;</el-button>
              <el-button class="action-btn" size="small" @click="showDetail(row)">&#x8be6;&#x60c5;</el-button>
              <el-button class="action-btn" size="small" @click="showDialog(row)">&#x7f16;&#x8f91;</el-button>
              <el-button class="action-btn" size="small" @click="handleDelete(row.id)">&#x5220;&#x9664;</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card class="agent-card">
      <template #header>
        <div class="page-header">
          <div class="header-left">
            <span style="font-weight:600">&#x590d;&#x76d8;&#x667a;&#x80fd;&#x4f53;</span>
            <el-tag type="success">DeepSeek + &#x4e1a;&#x52a1;&#x6570;&#x636e; + &#x89c4;&#x5219;&#x5224;&#x65ad;</el-tag>
          </div>
          <div class="header-left">
            <el-button size="small" type="primary" :loading="batchLoading" @click="runBatchAgent">&#x4e00;&#x952e;&#x5206;&#x6790;&#x5168;&#x90e8;&#x6295;&#x6d41;</el-button>
            <el-button size="small" type="warning" :loading="autonomousLoading" @click="runAutonomousAgent">&#x8fd0;&#x884c;&#x81ea;&#x4e3b;&#x590d;&#x76d8;&#x667a;&#x80fd;&#x4f53;</el-button>
            <el-button size="small" @click="runLatestAgent">&#x5206;&#x6790;&#x6700;&#x65b0;&#x590d;&#x76d8;</el-button>
            <el-button size="small" @click="clearAgentResult">&#x6e05;&#x7a7a;&#x7ed3;&#x679c;</el-button>
          </div>
        </div>
      </template>

      <el-form :model="agentForm" label-width="110px" class="agent-form">
        <el-row :gutter="16">
          <el-col :span="8"><el-form-item label="&#x590d;&#x76d8;ID"><el-input v-model="agentForm.review_id" :placeholder="txt.latestHint" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="&#x590d;&#x76d8;&#x5468;&#x671f;"><el-input v-model="agentForm.review_period" placeholder="2026W31" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="&#x89c6;&#x9891;ID"><el-input v-model="agentForm.video_id" :placeholder="txt.optional" /></el-form-item></el-col>
        </el-row>
        <el-form-item>
          <el-button type="primary" :loading="agentLoading" @click="runAgentByForm">&#x8fd0;&#x884c;&#x590d;&#x76d8;&#x667a;&#x80fd;&#x4f53;</el-button>
          <el-button :disabled="!agentResult" type="success" @click="saveAgentReview">&#x4fdd;&#x5b58;&#x590d;&#x76d8;&#x5e76;&#x6c89;&#x6dc0;&#x77e5;&#x8bc6;&#x5e93;</el-button>
          <span class="agent-tip">&#x652f;&#x6301;&#x8bfb;&#x53d6;&#x590d;&#x76d8;&#x8868; + &#x89c6;&#x9891; + &#x6295;&#x6d41;&#x6570;&#x636e;&#xff0c;&#x81ea;&#x52a8;&#x751f;&#x6210;&#x5206;&#x6790;&#x7ed3;&#x8bba;&#x3001;&#x4f18;&#x5316;&#x5efa;&#x8bae;&#xff0c;&#x5e76;&#x53ef;&#x6c89;&#x6dc0;&#x5230;&#x77e5;&#x8bc6;&#x5e93;&#x3002;</span>
        </el-form-item>
      </el-form>

      <div v-if="agentResult" class="agent-result">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="&#x667a;&#x80fd;&#x4f53;&#x5224;&#x65ad;">{{ agentResult.decision || '-' }}</el-descriptions-item>
          <el-descriptions-item label="&#x5206;&#x6790;&#x590d;&#x76d8;">{{ agentResult.review?.review_period || '-' }}</el-descriptions-item>
          <el-descriptions-item label="ROI">{{ agentResult.metrics?.roi ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="2&#x79d2;&#x8df3;&#x51fa;&#x7387;">{{ agentResult.metrics?.bounce_rate_2s ?? '-' }}%</el-descriptions-item>
        </el-descriptions>
        <el-divider content-position="left">AI &#x8f93;&#x51fa;</el-divider>
        <el-collapse v-model="activeCollapse">
          <el-collapse-item title="&#x603b;&#x89c8;" name="summary"><pre class="result-block">{{ formatJson(agentResult.ai_output?.summary || agentResult) }}</pre></el-collapse-item>
          <el-collapse-item title="&#x98ce;&#x9669;&#x70b9;" name="risks"><pre class="result-block">{{ formatJson(agentResult.ai_output?.risks || agentResult.rules) }}</pre></el-collapse-item>
          <el-collapse-item title="&#x5f52;&#x56e0;&#x5206;&#x6790;" name="causes"><pre class="result-block">{{ formatJson(agentResult.ai_output?.root_causes) }}</pre></el-collapse-item>
          <el-collapse-item title="&#x4f18;&#x5316;&#x52a8;&#x4f5c;" name="actions"><pre class="result-block">{{ formatJson(agentResult.ai_output?.actions) }}</pre></el-collapse-item>
          <el-collapse-item title="&#x5173;&#x952e;&#x6307;&#x6807;" name="metrics"><pre class="result-block">{{ formatJson(agentResult.ai_output?.key_metrics || agentResult.metrics) }}</pre></el-collapse-item>
          <el-collapse-item title="&#x53ef;&#x6c89;&#x6dc0;&#x77e5;&#x8bc6;" name="knowledge"><pre class="result-block">{{ formatJson(agentResult.ai_output?.knowledge_points) }}</pre></el-collapse-item>
        </el-collapse>
      </div>

      <div v-if="batchResult" class="batch-result">
        <div class="batch-summary">
          <el-tag type="info">批量分析 {{ batchResult.total }} 条投流记录</el-tag>
          <el-tag v-for="(count, decision) in batchResult.decision_counts" :key="decision" :type="decision.includes('停投') ? 'danger' : decision.includes('放量') ? 'success' : 'warning'">
            {{ decision }}：{{ count }}
          </el-tag>
          <el-button size="small" type="success" @click="saveBatchAgent">保存批量复盘</el-button>
        </div>
        <el-alert :title="batchResult.ai_output?.summary || '批量复盘完成'" type="success" :closable="false" />
        <el-table :data="batchResult.items" stripe size="small" style="margin-top:12px">
          <el-table-column prop="video_code" label="视频" width="120" />
          <el-table-column prop="content_direction" label="内容方向" min-width="180" />
          <el-table-column prop="metrics.roi" label="ROI" width="90" />
          <el-table-column prop="metrics.cvr" label="成交转化率" width="110" />
          <el-table-column prop="decision" label="建议" width="150" />
        </el-table>
      </div>

      <div v-if="autonomousPlan" class="autonomous-result">
        <div class="batch-summary">
          <el-tag type="warning">&#x81ea;&#x4e3b;&#x89c4;&#x5212;&#x5df2;&#x751f;&#x6210;</el-tag>
          <el-button size="small" type="danger" :disabled="approvedActionIndexes.length === 0" :loading="autonomousExecuting" @click="executeAutonomousAgent">&#x6267;&#x884c;&#x5df2;&#x9009;&#x52a8;&#x4f5c;</el-button>
        </div>
        <el-alert :title="autonomousPlan.summary || '&#x667a;&#x80fd;&#x4f53;&#x5df2;&#x751f;&#x6210;&#x6267;&#x884c;&#x8ba1;&#x5212;'" type="warning" :closable="false" />
        <div class="approval-tip">&#x667a;&#x80fd;&#x4f53;&#x4f1a;&#x81ea;&#x4e3b;&#x8bfb;&#x53d6;&#x6570;&#x636e;&#x5e76;&#x89c4;&#x5212;&#x5de5;&#x5177;&#x52a8;&#x4f5c;&#xff0c;&#x4f46;&#x5fc5;&#x987b;&#x7ecf;&#x4f60;&#x786e;&#x8ba4;&#x540e;&#x624d;&#x4f1a;&#x4fee;&#x6539;&#x4e1a;&#x52a1;&#x6570;&#x636e;&#x3002;</div>
        <el-checkbox-group v-model="approvedActionIndexes" class="action-check-list">
          <el-checkbox v-for="(action, index) in autonomousPlan.actions" :key="index" :label="index">
            <span>{{ index + 1 }}. {{ toolLabel(action.tool) }} / {{ action.reason || action.decision || '-' }} / {{ action.priority || 'P1' }}</span>
          </el-checkbox>
        </el-checkbox-group>
        <div v-if="executionResult" class="execution-result">
          <el-alert title="&#x5df2;&#x6267;&#x884c;&#x52a8;&#x4f5c;" type="success" :closable="false" />
          <el-table :data="executionResult.executed || []" size="small" stripe style="margin-top:12px">
            <el-table-column label="&#x5de5;&#x5177;" width="180"><template #default="{ row }">{{ toolLabel(row.tool) }}</template></el-table-column>
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column label="&#x6267;&#x884c;&#x7ed3;&#x679c;" min-width="220"><template #default="{ row }">{{ resultLabel(row) }}</template></el-table-column>
          </el-table>
          <div v-if="executionResult.skipped?.length" class="skipped-tip">&#x672a;&#x6267;&#x884c; {{ executionResult.skipped.length }} &#x4e2a;&#x52a8;&#x4f5c;&#xff0c;&#x8bf7;&#x68c0;&#x67e5;&#x6570;&#x636e;&#x5173;&#x8054;&#x3002;</div>
        </div>
      </div>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? txt.editReview : txt.addReview" width="700px">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="16"><el-col :span="12"><el-form-item label="&#x590d;&#x76d8;&#x5468;&#x671f;"><el-input v-model="form.review_period" /></el-form-item></el-col><el-col :span="12"><el-form-item label="&#x8d1f;&#x8d23;&#x4eba;"><el-input v-model="form.owner" /></el-form-item></el-col></el-row>
        <el-form-item label="&#x5546;&#x54c1;&#x8868;&#x73b0;"><el-input v-model="form.product_performance" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="&#x5185;&#x5bb9;&#x8868;&#x73b0;"><el-input v-model="form.content_performance" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="&#x89c6;&#x9891;&#x8868;&#x73b0;"><el-input v-model="form.video_performance" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="&#x6295;&#x6d41;&#x8868;&#x73b0;"><el-input v-model="form.ad_performance" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="&#x95ee;&#x9898;&#x5f52;&#x56e0;"><el-input v-model="form.problem_analysis" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="&#x4f18;&#x5316;&#x52a8;&#x4f5c;"><el-input v-model="form.next_action" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">&#x53d6;&#x6d88;</el-button><el-button type="primary" @click="handleSave">&#x4fdd;&#x5b58;</el-button></template>
    </el-dialog>

    <el-drawer v-model="detailVisible" :title="txt.reviewDetail" size="580px" destroy-on-close>
      <div v-if="currentDetail" class="detail-panel">
        <div class="detail-head"><el-tag>{{ currentDetail.review_level || txt.review }}</el-tag><strong>{{ currentDetail.review_period || txt.unnamedPeriod }}</strong></div>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="&#x8d1f;&#x8d23;&#x4eba;">{{ currentDetail.owner || '-' }}</el-descriptions-item>
          <el-descriptions-item label="&#x72b6;&#x6001;">{{ currentDetail.status || '-' }}</el-descriptions-item>
          <el-descriptions-item label="&#x4f18;&#x5148;&#x7ea7;">{{ currentDetail.priority || '-' }}</el-descriptions-item>
          <el-descriptions-item label="&#x622a;&#x6b62;&#x65f6;&#x95f4;">{{ currentDetail.deadline || '-' }}</el-descriptions-item>
        </el-descriptions>
        <h3>&#x5546;&#x54c1;&#x8868;&#x73b0;</h3><pre class="detail-content">{{ currentDetail.product_performance || txt.noText }}</pre>
        <h3>&#x5185;&#x5bb9;&#x8868;&#x73b0;</h3><pre class="detail-content">{{ currentDetail.content_performance || txt.noText }}</pre>
        <h3>&#x89c6;&#x9891;&#x8868;&#x73b0;</h3><pre class="detail-content">{{ currentDetail.video_performance || txt.noText }}</pre>
        <h3>&#x6295;&#x6d41;&#x8868;&#x73b0;</h3><pre class="detail-content">{{ currentDetail.ad_performance || txt.noText }}</pre>
        <h3>&#x95ee;&#x9898;&#x5f52;&#x56e0;</h3><pre class="detail-content">{{ currentDetail.problem_analysis || txt.noText }}</pre>
        <h3>&#x4f18;&#x5316;&#x52a8;&#x4f5c;</h3><pre class="detail-content">{{ currentDetail.next_action || txt.noText }}</pre>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { reviewsApi, reviewAgentApi, autonomousReviewAgentApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const zh = (codes) => String.fromCharCode(...codes.split(',').map(x => parseInt(x, 16)))
const txt = {
  unnamedPeriod: zh('672a,547d,540d,5468,671f'), noProduct: zh('6682,65e0,5546,54c1,8868,73b0'), noContent: zh('6682,65e0,5185,5bb9,8868,73b0'), noAd: zh('6682,65e0,6295,6d41,8868,73b0'), noProblem: zh('6682,65e0,95ee,9898,5f52,56e0'), noAction: zh('6682,65e0,4f18,5316,52a8,4f5c'), latestHint: zh('53ef,7559,7a7a,ff0c,9ed8,8ba4,6700,65b0'), optional: zh('53ef,9009'), editReview: zh('7f16,8f91,590d,76d8'), addReview: zh('65b0,589e,590d,76d8'), reviewDetail: zh('6570,636e,590d,76d8,8be6,60c5'), review: zh('590d,76d8'), noText: zh('6682,65e0,5185,5bb9'), noData: zh('6682,65e0,6570,636e')
}
const msg = { saveOk: zh('4fdd,5b58,6210,529f'), saveFail: zh('4fdd,5b58,5931,8d25'), delConfirm: zh('786e,8ba4,5220,9664,ff1f'), tip: zh('63d0,793a'), delOk: zh('5220,9664,6210,529f'), chooseDelete: zh('8bf7,5148,52fe,9009,8981,5220,9664,7684,590d,76d8'), batchFail: zh('6279,91cf,5220,9664,5931,8d25'), clearOk: zh('5df2,6e05,7a7a,667a,80fd,4f53,7ed3,679c'), agentOk: zh('590d,76d8,667a,80fd,4f53,5206,6790,5b8c,6210'), agentFail: zh('667a,80fd,4f53,5206,6790,5931,8d25'), runFirst: zh('8bf7,5148,8fd0,884c,667a,80fd,4f53') }
const list = ref([]), selectedIds = ref([]), dialogVisible = ref(false), detailVisible = ref(false), currentDetail = ref(null), form = ref({})
const agentLoading = ref(false), agentResult = ref(null), activeCollapse = ref(['summary', 'risks'])
const batchLoading = ref(false), batchResult = ref(null)
const autonomousLoading = ref(false), autonomousExecuting = ref(false), autonomousPlan = ref(null), executionResult = ref(null), approvedActionIndexes = ref([])
const agentForm = reactive({ review_id: '', review_period: '', video_id: '' })
const loadList = async () => { const res = await reviewsApi.list({ limit: 500 }); list.value = res.data }
const showDetail = (row) => { currentDetail.value = row; detailVisible.value = true }
const showDialog = (row) => { form.value = row ? { ...row } : { review_period: '', product_performance: '', content_performance: '', video_performance: '', ad_performance: '', problem_analysis: '', next_action: '', owner: '' }; dialogVisible.value = true }
const handleSave = async () => { try { if (form.value.id) await reviewsApi.update(form.value.id, form.value); else await reviewsApi.create(form.value); ElMessage.success(msg.saveOk); dialogVisible.value = false; loadList() } catch (e) { ElMessage.error(e.response?.data?.detail || msg.saveFail) } }
const handleDelete = async (id) => { await ElMessageBox.confirm(msg.delConfirm, msg.tip, { type: 'warning' }); await reviewsApi.delete(id); ElMessage.success(msg.delOk); loadList() }
const onSelectionChange = (rows) => { selectedIds.value = rows.map(r => r.id) }
const handleBatchDelete = async () => { if (!selectedIds.value.length) return ElMessage.warning(msg.chooseDelete); try { await ElMessageBox.confirm(`${msg.delConfirm} ${selectedIds.value.length}`, msg.tip, { type: 'warning' }); const res = await reviewsApi.batchDelete(selectedIds.value); ElMessage.success(res.data.message || msg.delOk); loadList() } catch (e) { if (e !== 'cancel' && e !== 'close') ElMessage.error(e.response?.data?.detail || msg.batchFail) } }
const formatJson = (obj) => (!obj ? txt.noData : JSON.stringify(obj, null, 2))
const toolLabel = (tool) => ({
  update_ad_status: '\u66f4\u65b0\u6295\u6d41\u72b6\u6001',
  create_video_task: '\u66f4\u65b0\u89c6\u9891\u4efb\u52a1',
  create_review: '\u521b\u5efa\u590d\u76d8\u8bb0\u5f55',
  save_knowledge: '\u6c89\u6dc0\u77e5\u8bc6\u5e93',
}[tool] || tool || '\u672a\u77e5\u5de5\u5177')
const resultLabel = (row) => {
  if (row.tool === 'update_ad_status') {
    if (row.result && row.result !== '????') return row.result
    return '\u5df2\u6839\u636e\u89c4\u5219\u66f4\u65b0\u6295\u6d41\u72b6\u6001'
  }
  if (row.tool === 'create_video_task') return '\u5df2\u66f4\u65b0\u89c6\u9891\u4efb\u52a1'
  if (row.tool === 'create_review') return '\u5df2\u521b\u5efa\u590d\u76d8\u8bb0\u5f55'
  if (row.tool === 'save_knowledge') return '\u5df2\u5199\u5165\u77e5\u8bc6\u5e93'
  return row.result || '\u5df2\u5b8c\u6210'
}
const clearAgentResult = () => { agentResult.value = null; batchResult.value = null; autonomousPlan.value = null; executionResult.value = null; approvedActionIndexes.value = []; agentForm.review_id = ''; agentForm.review_period = ''; agentForm.video_id = ''; ElMessage.success(msg.clearOk) }
const runAgentByPayload = async (payload) => { agentLoading.value = true; try { const res = await reviewAgentApi.analyze(payload); agentResult.value = res.data.data; activeCollapse.value = ['summary', 'risks', 'causes', 'actions', 'metrics', 'knowledge']; ElMessage.success(msg.agentOk) } catch (e) { ElMessage.error(e.response?.data?.detail || msg.agentFail) } finally { agentLoading.value = false } }
const runLatestAgent = async () => { await runAgentByPayload({ scope: 'latest' }) }
const runAgentByForm = async () => { await runAgentByPayload({ scope: 'latest', review_id: agentForm.review_id ? Number(agentForm.review_id) : null, review_period: agentForm.review_period || null, video_id: agentForm.video_id ? Number(agentForm.video_id) : null }) }
const runReviewAgent = async (row) => { agentForm.review_id = row.id; agentForm.review_period = row.review_period || ''; agentForm.video_id = row.video_id || ''; await runAgentByPayload({ scope: 'latest', review_id: row.id }) }
const saveAgentReview = async () => { if (!agentResult.value) return ElMessage.warning(msg.runFirst); try { const res = await reviewAgentApi.save({ data: agentResult.value }); ElMessage.success(res.data.message || msg.saveOk); await loadList() } catch (e) { ElMessage.error(e.response?.data?.detail || msg.saveFail) } }
const runBatchAgent = async () => {
  batchLoading.value = true
  try {
    const res = await reviewAgentApi.batchAnalyze({ limit: 100, only_spend: false })
    batchResult.value = res.data.data
    ElMessage.success('批量投流复盘完成')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '批量分析失败')
  } finally {
    batchLoading.value = false
  }
}
const saveBatchAgent = async () => {
  if (!batchResult.value) return
  try {
    const res = await reviewAgentApi.batchSave({ data: batchResult.value })
    ElMessage.success(res.data.message || '批量复盘已保存')
    await loadList()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '批量复盘保存失败')
  }
}
const runAutonomousAgent = async () => {
  autonomousLoading.value = true
  try {
    const res = await autonomousReviewAgentApi.run({ goal: 'Analyze all ad data and create prioritized optimization actions' })
    autonomousPlan.value = res.data
    executionResult.value = null
    approvedActionIndexes.value = []
    ElMessage.success('Autonomous review plan created')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || 'Autonomous agent failed')
  } finally {
    autonomousLoading.value = false
  }
}
const executeAutonomousAgent = async () => {
  if (!autonomousPlan.value || approvedActionIndexes.value.length === 0) return
  autonomousExecuting.value = true
  try {
    const res = await autonomousReviewAgentApi.execute({ plan: autonomousPlan.value, approved_indexes: approvedActionIndexes.value })
    executionResult.value = res.data
    approvedActionIndexes.value = []
    ElMessage.success(`Executed ${res.data.executed?.length || 0} actions`)
    await loadList()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || 'Action execution failed')
  } finally {
    autonomousExecuting.value = false
  }
}

onMounted(loadList)
</script>

<style scoped>
.table-card, .agent-card { margin-top: 20px; }
.page-header { display:flex; justify-content:space-between; align-items:center; gap:12px; }
.header-left { display:flex; align-items:center; gap:12px; flex-wrap:wrap; }
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
.detail-content, .result-block { white-space:pre-wrap; word-break:break-word; line-height:1.8; background:#f6f8fb; border:1px solid rgba(20,33,61,.08); border-radius:14px; padding:16px; color:#334155; }
.multi-line-cell { display:-webkit-box; -webkit-box-orient:vertical; -webkit-line-clamp:3; overflow:hidden; white-space:normal; line-height:1.6; max-height:calc(1.6em * 3); color:#5f6673; }
.agent-form { margin-top: 8px; }
.agent-tip { margin-left: 10px; color: #64748b; font-size: 13px; }
.agent-result { margin-top: 14px; }
.batch-result { margin-top: 18px; padding-top: 14px; border-top: 1px solid rgba(20,33,61,.08); }
.autonomous-result { margin-top:18px; padding-top:14px; border-top:1px solid rgba(20,33,61,.08); }
.approval-tip { margin:12px 0; color:#64748b; font-size:13px; }
.action-check-list { display:flex; flex-direction:column; gap:10px; padding:14px; border:1px solid rgba(20,33,61,.08); border-radius:12px; background:#fbfcfe; }
.execution-result { margin-top:16px; padding-top:14px; border-top:1px solid rgba(20,33,61,.08); }
.skipped-tip { margin-top:10px; color:#b45309; font-size:13px; }
.batch-summary { display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:12px; }
</style>

