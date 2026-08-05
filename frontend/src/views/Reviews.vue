<template>
  <div>
    <el-card class="table-card">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="font-weight:600">数据复盘表</span>
          <el-button type="primary" @click="showDialog()">新增复盘</el-button>
        </div>
      </template>
      <el-table :data="list" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="复盘周期" width="170">
          <template #default="{ row }"><button class="summary-cell" type="button" @click="showDetail(row)">{{ row.review_period || '未命名周期' }}</button></template>
        </el-table-column>
        <el-table-column prop="product_performance" label="商品表现" min-width="220" />
        <el-table-column prop="content_performance" label="内容表现" min-width="220" />
        <el-table-column prop="ad_performance" label="投流表现" min-width="220" />
        <el-table-column prop="problem_analysis" label="问题归因" min-width="240" />
        <el-table-column prop="next_action" label="优化动作" min-width="240" />
        <el-table-column prop="owner" label="负责人" width="110" />
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }"><div class="action-row"><el-button class="action-btn" size="small" @click="showDetail(row)">详情</el-button><el-button class="action-btn" size="small" @click="showDialog(row)">编辑</el-button><el-button class="action-btn" size="small" @click="handleDelete(row.id)">删除</el-button></div></template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑复盘' : '新增复盘'" width="700px">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="16"><el-col :span="12"><el-form-item label="复盘周期"><el-input v-model="form.review_period" /></el-form-item></el-col><el-col :span="12"><el-form-item label="负责人"><el-input v-model="form.owner" /></el-form-item></el-col></el-row>
        <el-form-item label="商品表现"><el-input v-model="form.product_performance" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="内容表现"><el-input v-model="form.content_performance" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="视频表现"><el-input v-model="form.video_performance" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="投流表现"><el-input v-model="form.ad_performance" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="问题归因"><el-input v-model="form.problem_analysis" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="优化动作"><el-input v-model="form.next_action" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" @click="handleSave">保存</el-button></template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="数据复盘详情" size="580px" destroy-on-close>
      <div v-if="currentDetail" class="detail-panel">
        <div class="detail-head"><el-tag>{{ currentDetail.review_level || '复盘' }}</el-tag><strong>{{ currentDetail.review_period || '未命名周期' }}</strong></div>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="负责人">{{ currentDetail.owner || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ currentDetail.status || '-' }}</el-descriptions-item>
          <el-descriptions-item label="优先级">{{ currentDetail.priority || '-' }}</el-descriptions-item>
          <el-descriptions-item label="截止时间">{{ currentDetail.deadline || '-' }}</el-descriptions-item>
        </el-descriptions>
        <h3>商品表现</h3><pre class="detail-content">{{ currentDetail.product_performance || '暂无内容' }}</pre>
        <h3>内容表现</h3><pre class="detail-content">{{ currentDetail.content_performance || '暂无内容' }}</pre>
        <h3>视频表现</h3><pre class="detail-content">{{ currentDetail.video_performance || '暂无内容' }}</pre>
        <h3>投流表现</h3><pre class="detail-content">{{ currentDetail.ad_performance || '暂无内容' }}</pre>
        <h3>问题归因</h3><pre class="detail-content">{{ currentDetail.problem_analysis || '暂无内容' }}</pre>
        <h3>优化动作</h3><pre class="detail-content">{{ currentDetail.next_action || '暂无内容' }}</pre>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { reviewsApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'
const list = ref([])
const dialogVisible = ref(false)
const detailVisible = ref(false)
const currentDetail = ref(null)
const form = ref({})
const loadList = async () => { const res = await reviewsApi.list(); list.value = res.data }
const showDetail = (row) => { currentDetail.value = row; detailVisible.value = true }
const showDialog = (row) => { form.value = row ? { ...row } : { review_period: '', product_performance: '', content_performance: '', video_performance: '', ad_performance: '', problem_analysis: '', next_action: '', owner: '' }; dialogVisible.value = true }
const handleSave = async () => { try { if (form.value.id) await reviewsApi.update(form.value.id, form.value); else await reviewsApi.create(form.value); ElMessage.success('保存成功'); dialogVisible.value = false; loadList() } catch (e) { ElMessage.error(e.response?.data?.detail || '保存失败') } }
const handleDelete = async (id) => { await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' }); await reviewsApi.delete(id); ElMessage.success('删除成功'); loadList() }
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
