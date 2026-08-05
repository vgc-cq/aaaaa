<template>
  <div>
    <el-card class="table-card">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="font-weight:600">客服私域线索表</span>
          <el-button type="primary" @click="showDialog()">新增线索</el-button>
        </div>
      </template>
      <el-table :data="list" stripe>
        <el-table-column prop="lead_code" label="编号" width="90" />
        <el-table-column label="咨询内容" min-width="280">
          <template #default="{ row }"><button class="summary-cell" type="button" @click="showDetail(row)">{{ row.inquiry || '暂无咨询' }}</button></template>
        </el-table-column>
        <el-table-column prop="intent" label="用户意向" width="110">
          <template #default="{ row }"><el-tag :type="row.intent === '高' ? 'danger' : row.intent === '中' ? 'warning' : 'info'" size="small">{{ row.intent }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="follow_status" label="跟进状态" width="120">
          <template #default="{ row }"><el-tag :type="row.follow_status === '已成交' || row.follow_status === '已加微' ? 'success' : 'warning'" size="small">{{ row.follow_status }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="wechat_added" label="加微" width="80" />
        <el-table-column prop="script_template" label="话术模板" min-width="260" />
        <el-table-column prop="owner" label="负责人" width="100" />
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }"><div class="action-row"><el-button class="action-btn" size="small" @click="showDetail(row)">详情</el-button><el-button class="action-btn" size="small" @click="showDialog(row)">编辑</el-button><el-button class="action-btn" size="small" @click="handleDelete(row.id)">删除</el-button></div></template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑线索' : '新增线索'" width="600px">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="16"><el-col :span="12"><el-form-item label="线索编号"><el-input v-model="form.lead_code" /></el-form-item></el-col><el-col :span="12"><el-form-item label="来源视频ID"><el-input-number v-model="form.video_id" :min="1" /></el-form-item></el-col></el-row>
        <el-form-item label="咨询内容"><el-input v-model="form.inquiry" type="textarea" /></el-form-item>
        <el-row :gutter="16"><el-col :span="12"><el-form-item label="用户意向"><el-select v-model="form.intent"><el-option label="高" value="高" /><el-option label="中" value="中" /><el-option label="低" value="低" /></el-select></el-form-item></el-col><el-col :span="12"><el-form-item label="跟进状态"><el-select v-model="form.follow_status"><el-option label="待跟进" value="待跟进" /><el-option label="已加微" value="已加微" /><el-option label="已成交" value="已成交" /></el-select></el-form-item></el-col></el-row>
        <el-row :gutter="16"><el-col :span="12"><el-form-item label="是否加微"><el-select v-model="form.wechat_added"><el-option label="否" value="否" /><el-option label="是" value="是" /></el-select></el-form-item></el-col><el-col :span="12"><el-form-item label="负责人"><el-input v-model="form.owner" /></el-form-item></el-col></el-row>
        <el-form-item label="话术模板"><el-input v-model="form.script_template" type="textarea" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" @click="handleSave">保存</el-button></template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="私域线索详情" size="560px" destroy-on-close>
      <div v-if="currentDetail" class="detail-panel">
        <div class="detail-head"><el-tag>{{ currentDetail.lead_code }}</el-tag><strong>{{ currentDetail.intent || '未判断意向' }}</strong></div>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="来源视频">{{ currentDetail.video_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="跟进状态">{{ currentDetail.follow_status || '-' }}</el-descriptions-item>
          <el-descriptions-item label="是否加微">{{ currentDetail.wechat_added || '-' }}</el-descriptions-item>
          <el-descriptions-item label="负责人">{{ currentDetail.owner || '-' }}</el-descriptions-item>
          <el-descriptions-item label="来源平台">{{ currentDetail.source_platform || '-' }}</el-descriptions-item>
        </el-descriptions>
        <h3>咨询内容</h3><pre class="detail-content">{{ currentDetail.inquiry || '暂无内容' }}</pre>
        <h3>话术模板</h3><pre class="detail-content">{{ currentDetail.script_template || '暂无内容' }}</pre>
        <h3>备注</h3><pre class="detail-content">{{ currentDetail.notes || '暂无内容' }}</pre>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { leadsApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'
const list = ref([])
const dialogVisible = ref(false)
const detailVisible = ref(false)
const currentDetail = ref(null)
const form = ref({})
const loadList = async () => { const res = await leadsApi.list(); list.value = res.data }
const showDetail = (row) => { currentDetail.value = row; detailVisible.value = true }
const showDialog = (row) => { form.value = row ? { ...row } : { lead_code: '', video_id: 1, inquiry: '', intent: '中', follow_status: '待跟进', wechat_added: '否', script_template: '', owner: '客服' }; dialogVisible.value = true }
const handleSave = async () => { try { if (form.value.id) await leadsApi.update(form.value.id, form.value); else await leadsApi.create(form.value); ElMessage.success('保存成功'); dialogVisible.value = false; loadList() } catch (e) { ElMessage.error(e.response?.data?.detail || '保存失败') } }
const handleDelete = async (id) => { await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' }); await leadsApi.delete(id); ElMessage.success('删除成功'); loadList() }
onMounted(loadList)
</script>

<style scoped>
.table-card { margin-top:20px; }
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
</style>
