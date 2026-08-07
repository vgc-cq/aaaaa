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

      <!-- LangGraph 节点卡片：每个节点实时显示状态与真实输出 -->
      <div class="node-flow">
        <template v-for="(card, idx) in NODE_CARDS" :key="card.key">
          <div class="node-card" :class="nodeCardClass(card.key)">
            <div class="node-card-head">
              <span class="node-index">{{ idx + 1 }}</span>
              <div class="node-card-title">
                <div class="node-name">{{ card.title }}</div>
                <div class="node-desc">{{ card.desc }}</div>
              </div>
              <span v-if="nodeStates[card.key] === 'running'" class="status-spinner" />
              <span v-else-if="nodeStates[card.key] === 'success'" class="status-dot status-ok">✓</span>
              <span v-else-if="nodeStates[card.key] === 'skipped'" class="status-dot status-skip">–</span>
              <span v-else class="status-dot status-pending" />
            </div>

            <div v-if="nodeStates[card.key] === 'running'" class="node-output running-note">{{ runningText(card.key) }}</div>

            <div v-else-if="nodeStates[card.key] === 'success' && nodeOutputs[card.key]" class="node-output">
              <!-- 读取数据：扫描到的投流 -->
              <template v-if="card.key === 'load_data'">
                <div class="node-message">{{ nodeOutputs[card.key].message }}</div>
                <template v-if="nodeOutputs[card.key].items.length">
                  <table class="node-table">
                    <tr><th>视频/投流</th><th>内容方向</th><th>消耗</th><th>成交</th></tr>
                    <tr v-for="it in nodeOutputs[card.key].items.slice(0, 6)" :key="it.ad_id">
                      <td>{{ it.video_code || `投流#${it.ad_id}` }}</td>
                      <td class="ellipsis">{{ it.content_direction || '-' }}</td>
                      <td>{{ it.spend ?? '-' }}</td>
                      <td>{{ it.revenue ?? '-' }}</td>
                    </tr>
                  </table>
                  <div v-if="nodeOutputs[card.key].items.length > 6" class="node-more">等共 {{ nodeOutputs[card.key].count }} 条</div>
                </template>
              </template>

              <!-- 指标计算：规则算出的指标与异常 -->
              <template v-else-if="card.key === 'analyze'">
                <table class="node-table">
                  <tr><th>视频</th><th>ROI</th><th>CTR%</th><th>异常</th><th>规则决策</th></tr>
                  <tr v-for="it in nodeOutputs[card.key].items.slice(0, 6)" :key="it.ad_id">
                    <td>{{ it.video_code || `投流#${it.ad_id}` }}</td>
                    <td>{{ it.roi ?? '-' }}</td>
                    <td>{{ it.ctr ?? '-' }}</td>
                    <td>{{ it.issues }}</td>
                    <td class="ellipsis">{{ it.decision }}</td>
                  </tr>
                </table>
                <div v-if="nodeOutputs[card.key].items.length > 6" class="node-more">等共 {{ nodeOutputs[card.key].count }} 条</div>
              </template>

              <!-- AI 复盘：DeepSeek 结论 -->
              <template v-else-if="card.key === 'review'">
                <div v-for="it in nodeOutputs[card.key].items.slice(0, 4)" :key="it.ad_id" class="review-item">
                  <div class="review-item-head">
                    <b>{{ it.video_code || `投流#${it.ad_id}` }}</b>
                    <el-tag :type="ratingTagType(it.rating)" size="small">{{ it.rating || '-' }}</el-tag>
                    <span class="review-decision">{{ it.decision || '-' }}</span>
                    <span v-if="it.self_score != null" class="review-score">自检 {{ it.self_score }} 分</span>
                  </div>
                  <div class="review-summary">{{ it.summary || '-' }}</div>
                  <div v-if="(it.suggestions || []).length" class="review-suggestions">建议：{{ it.suggestions.slice(0, 2).join('；') }}</div>
                </div>
                <div v-if="nodeOutputs[card.key].items.length > 4" class="node-more">等共 {{ nodeOutputs[card.key].count }} 条</div>
              </template>

              <!-- 写回建议 -->
              <template v-else-if="card.key === 'save'">
                <div class="node-message">已写回 {{ nodeOutputs[card.key].saved_count }} 条投流建议，并生成对应复盘记录（自动关联商品/内容/视频）</div>
              </template>

              <!-- 记录日志 -->
              <template v-else-if="card.key === 'record'">
                <div class="node-message">运行日志已写入 agent_runs：运行ID {{ nodeOutputs[card.key].run_log_id }}，处理 {{ nodeOutputs[card.key].processed }} 条</div>
              </template>
            </div>

            <div v-else-if="nodeStates[card.key] === 'skipped'" class="node-output skipped-note">本轮无数据，节点未执行</div>
          </div>
        </template>
      </div>

      <div class="agent-tip">
        智能体会自动扫描"还没有复盘建议"的投流数据，逐条计算指标并生成复盘结论与优化建议
        （建议直接给出，无需人工审批）。后台也会按设定间隔自动巡检（backend/.env 的 REVIEW_INTERVAL_MINUTES 控制）。
      </div>
      <el-form inline>
        <el-form-item>
          <el-checkbox v-model="reviewForce">强制重新复盘（含已复盘）</el-checkbox>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="running" @click="runAgent">开始复盘</el-button>
        </el-form-item>
      </el-form>

      <el-divider content-position="left">最近复盘运行记录（点最右侧箭头查看本次运行结果）</el-divider>
      <el-table :data="logs" size="small" border>
        <el-table-column prop="created_at" label="时间" min-width="170" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column prop="products_processed" label="复盘条数" width="100" />
        <el-table-column label="说明" min-width="220">
          <template #default="{ row }">{{ row.summary?.message || '-' }}</template>
        </el-table-column>
        <el-table-column type="expand" width="50">
          <template #default="{ row }">
            <div class="expand-results">
              <div class="expand-head">{{ row.summary?.message || '本次运行结果' }}</div>
              <el-table v-if="(row.summary?.results || []).length" :data="row.summary.results" size="small" border stripe>
                <el-table-column label="视频" width="110">
                  <template #default="{ row: r }">{{ r.video_code || `视频#${r.video_id}` }}</template>
                </el-table-column>
                <el-table-column prop="content_direction" label="内容方向" min-width="140" show-overflow-tooltip />
                <el-table-column label="ROI" width="80">
                  <template #default="{ row: r }">{{ r.metrics?.roi ?? '-' }}</template>
                </el-table-column>
                <el-table-column label="评级" width="80">
                  <template #default="{ row: r }">
                    <el-tag :type="ratingTagType(r.review?.rating)" size="small">{{ r.review?.rating || '-' }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="决策" width="110">
                  <template #default="{ row: r }">{{ r.review?.decision || '-' }}</template>
                </el-table-column>
                <el-table-column label="总体判断" min-width="180" show-overflow-tooltip>
                  <template #default="{ row: r }">{{ r.review?.summary || '-' }}</template>
                </el-table-column>
                <el-table-column label="优化建议" min-width="260">
                  <template #default="{ row: r }">
                    <el-tooltip placement="top" :teleported="true" :show-after="150" :offset="10" popper-class="suggestion-popper">
                      <template #content>
                        <div class="suggestion-tip">
                          <div v-for="(s, i) in (r.review?.suggestions || [])" :key="i" class="suggestion-tip-line">{{ i + 1 }}. {{ s }}</div>
                        </div>
                      </template>
                      <span class="suggestion-cell">{{ (r.review?.suggestions || []).join('；') || '-' }}</span>
                    </el-tooltip>
                  </template>
                </el-table-column>
              </el-table>
              <div v-else class="expand-empty">本次运行没有生成复盘结果（可能没有未复盘数据，或运行失败）</div>
            </div>
          </template>
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
        <el-table-column label="关联投流" width="120">
          <template #default="{ row }">
            <span>投流#{{ row.ad_id ?? '-' }}</span>
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
              <div class="memory-tip">选择"认可"会写入经验记忆，并沉淀到知识库（标记已生效、全系统可查）；选择"不认可"只写入记忆，避免以后输出类似结论</div>
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
import { reviewsApi } from '../api'
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

// ---------- 投流复盘智能体（LangGraph 节点卡片） ----------
const NODE_CARDS = [
  { key: 'load_data', title: '读取数据', desc: '扫描未复盘投流' },
  { key: 'analyze', title: '指标计算', desc: 'ROI/CTR/CVR（规则）' },
  { key: 'review', title: 'AI 复盘', desc: 'DeepSeek 结论与建议' },
  { key: 'save', title: '写回建议', desc: 'ad_data + 复盘表' },
  { key: 'record', title: '记录日志', desc: 'agent_runs' },
]

const NODE_RUNNING_TEXT = {
  load_data: '正在扫描未复盘的投流数据…',
  analyze: '正在逐条计算指标与异常…',
  review: 'DeepSeek 正在生成复盘结论（含自检评分）…',
  save: '正在写回复盘建议并生成复盘记录…',
  record: '正在写入运行日志…',
}

const reviewForce = ref(false)
const running = ref(false)
const nodeStates = ref({})
const nodeOutputs = ref({})
const logs = ref([])

const runningText = (key) => NODE_RUNNING_TEXT[key] || '运行中…'

const nodeCardClass = (key) => {
  const s = nodeStates.value[key]
  if (s === 'running') return 'node-running'
  if (s === 'success') return 'node-success'
  if (s === 'skipped') return 'node-skipped'
  return ''
}

const statusText = computed(() => {
  if (running.value || Object.values(nodeStates.value).includes('running')) return '智能体运行中…'
  if (Object.values(nodeStates.value).some(s => s === 'success' || s === 'skipped')) return '复盘完成'
  return '待运行'
})
const statusTagType = computed(() => {
  if (running.value || Object.values(nodeStates.value).includes('running')) return 'warning'
  if (Object.values(nodeStates.value).some(s => s === 'success' || s === 'skipped')) return 'success'
  return 'info'
})
const ratingTagType = (rating) => {
  if (rating === '优秀') return 'success'
  if (rating === '较差') return 'danger'
  return 'warning'
}

const handleAgentEvent = (event) => {
  if (!event) return
  if (event.event === 'node') {
    const key = event.node
    nodeStates.value[key] = 'success'
    nodeOutputs.value[key] = event.output
    const idx = NODE_CARDS.findIndex(c => c.key === key)
    const next = NODE_CARDS[idx + 1]
    if (next) nodeStates.value[next.key] = 'running'
  } else if (event.event === 'complete') {
    for (const card of NODE_CARDS) {
      const s = nodeStates.value[card.key]
      if (!s || s === 'running') nodeStates.value[card.key] = s ? 'success' : 'skipped'
    }
    if ((event.results || []).length === 0) ElMessage.info(event.message || '没有未复盘的投流数据')
    else ElMessage.success(`复盘完成：${event.processed} 条投流数据`)
    loadLogs()
  } else if (event.event === 'error') {
    ElMessage.error(event.detail || '复盘失败')
  }
}

const runAgent = async () => {
  running.value = true
  nodeStates.value = {}
  nodeOutputs.value = {}
  nodeStates.value.load_data = 'running'
  try {
    const res = await fetch('/api/review-agent/run/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force: reviewForce.value }),
    })
    if (!res.ok || !res.body) {
      const text = await res.text().catch(() => '')
      throw new Error(text || `接口返回 ${res.status}`)
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    let streamDone = false
    while (!streamDone) {
      const { value, done } = await reader.read()
      streamDone = done
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
      let sep
      while ((sep = buffer.indexOf('\n\n')) >= 0) {
        const raw = buffer.slice(0, sep)
        buffer = buffer.slice(sep + 2)
        const line = raw.split('\n').find(l => l.startsWith('data: '))
        if (!line) continue
        try {
          handleAgentEvent(JSON.parse(line.slice(6)))
        } catch { /* 忽略无法解析的帧 */ }
      }
    }
  } catch (e) {
    ElMessage.error('复盘失败：' + (e.message || '请稍后重试'))
    nodeStates.value = {}
  } finally {
    running.value = false
  }
}

const loadLogs = async () => {
  try {
    const res = await fetch('/api/review-agent/logs?limit=10')
    logs.value = await res.json()
  } catch (e) { /* 忽略 */ }
}

const clearResult = () => {
  nodeStates.value = {}
  nodeOutputs.value = {}
}

onMounted(() => { loadList(); loadLogs() })
</script>

<style scoped>
.agent-card { margin-top:20px; }
.table-card { margin-top:20px; }
.page-header { display:flex; justify-content:space-between; align-items:center; }
.header-left { display:flex; align-items:center; gap:12px; }
.node-flow { display:flex; flex-wrap:wrap; gap:12px; margin:14px 0 4px; }
.node-card { flex:1 1 200px; min-width:200px; background:#fff; border:1px solid #e3e8f0; border-radius:12px; padding:12px; transition:all .2s; }
.node-card-head { display:flex; align-items:center; gap:8px; }
.node-index { width:20px; height:20px; flex:0 0 20px; border-radius:50%; background:#eef2f8; color:#5f6673; font-size:12px; font-weight:700; display:inline-flex; align-items:center; justify-content:center; }
.node-card-title { flex:1; min-width:0; }
.node-name { font-size:14px; font-weight:600; color:#1f2937; }
.node-desc { font-size:12px; color:#94a3b8; margin-top:1px; }
.node-running { border-color:#2454ff; box-shadow:0 0 0 3px rgba(36,84,255,.08); }
.node-running .node-index { background:#2454ff; color:#fff; }
.node-success { border-color:#b7e4c7; background:#fbfefc; }
.node-success .node-index { background:#16a34a; color:#fff; }
.node-skipped { opacity:.55; background:#fafbfc; }
.status-spinner { width:14px; height:14px; flex:0 0 14px; border:2px solid #c7d4ff; border-top-color:#2454ff; border-radius:50%; animation:spin .8s linear infinite; }
.status-dot { width:16px; height:16px; flex:0 0 16px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-size:11px; font-weight:700; }
.status-ok { background:#e8f7ee; color:#16a34a; border:1px solid #b7e4c7; }
.status-skip { background:#f3f4f6; color:#9ca3af; border:1px solid #e2e5ea; }
.status-pending { background:#fff; border:1px solid #d8dee9; }
@keyframes spin { to { transform:rotate(360deg); } }
.node-output { margin-top:10px; max-height:230px; overflow:auto; font-size:12px; color:#475569; border-top:1px dashed #e5e9f0; padding-top:8px; }
.node-message { line-height:1.6; }
.running-note { color:#2454ff; border-top-color:#dbe4ff; }
.skipped-note { color:#9ca3af; }
.node-table { width:100%; border-collapse:collapse; font-size:11px; margin-top:4px; }
.node-table th { text-align:left; color:#94a3b8; font-weight:500; padding:3px 4px; border-bottom:1px solid #eef2f8; white-space:nowrap; }
.node-table td { padding:4px; border-bottom:1px solid #f4f6fa; white-space:nowrap; }
.node-table td.ellipsis { max-width:90px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.node-more { margin-top:6px; color:#94a3b8; font-size:11px; }
.review-item { margin-bottom:8px; }
.review-item:last-child { margin-bottom:0; }
.review-item-head { display:flex; align-items:center; gap:6px; flex-wrap:wrap; }
.review-item-head b { font-size:12px; color:#1f2937; }
.review-decision { color:#e6a23c; font-size:11px; }
.review-score { color:#16a34a; font-size:11px; margin-left:auto; }
.review-summary { color:#475569; line-height:1.5; margin-top:3px; }
.review-suggestions { color:#64748b; line-height:1.5; margin-top:2px; }
.agent-tip { font-size:13px; color:#64748b; line-height:1.7; margin-bottom:14px; }
.result-panel { margin-top:8px; }
.expand-results { padding:6px 4px 2px; }
.suggestion-cell { display:block; cursor:default; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.suggestion-popper { max-width: 480px; }
.suggestion-tip { font-size: 12px; }
.suggestion-tip-line { line-height: 1.6; margin-bottom: 4px; white-space: normal; word-break: break-word; }
.suggestion-tip-line:last-child { margin-bottom: 0; }
.expand-head { font-size:13px; color:#1f2937; font-weight:600; margin-bottom:8px; }
.expand-empty { font-size:13px; color:#94a3b8; padding:8px 4px; }
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
