<template>
  <div>
    <el-card class="table-card">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="font-weight:600">视频生产任务表</span>
          <el-button type="primary" @click="showDialog()">新增视频</el-button>
        </div>
      </template>
      <el-table :data="list" stripe>
        <el-table-column prop="video_code" label="编号" width="90" />
        <el-table-column prop="material_status" label="素材状态" width="110" />
        <el-table-column prop="generate_tool" label="生成工具" width="130" />
        <el-table-column prop="editor" label="负责人" width="100" />
        <el-table-column prop="version" label="版本" width="80" />
        <el-table-column label="质检项" min-width="280">
          <template #default="{ row }">
            <button class="summary-cell" type="button" @click="showDetail(row)">{{ row.quality_items || '暂无质检项' }}</button>
          </template>
        </el-table-column>
        <el-table-column prop="publish_platform" label="平台" width="100" />
        <el-table-column prop="publish_status" label="发布状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.publish_status === '已发布' ? 'success' : row.publish_status === '审核中' ? 'warning' : 'info'" size="small">{{ row.publish_status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <div class="action-row">
              <el-button class="action-btn" size="small" @click="showDetail(row)">详情</el-button>
              <el-button class="action-btn" size="small" @click="showDialog(row)">编辑</el-button>
              <el-button class="action-btn" size="small" @click="handleDelete(row.id)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑视频' : '新增视频'" width="600px">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="视频编号"><el-input v-model="form.video_code" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="脚本ID"><el-input-number v-model="form.script_id" :min="1" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="素材状态"><el-select v-model="form.material_status"><el-option label="待准备" value="待准备" /><el-option label="已完成" value="已完成" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="生成工具"><el-input v-model="form.generate_tool" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="负责人"><el-input v-model="form.editor" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="版本"><el-input v-model="form.version" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="质检项"><el-input v-model="form.quality_items" type="textarea" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="发布平台"><el-input v-model="form.publish_platform" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="发布状态"><el-select v-model="form.publish_status"><el-option label="未发布" value="未发布" /><el-option label="审核中" value="审核中" /><el-option label="已发布" value="已发布" /></el-select></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" @click="handleSave">保存</el-button></template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="视频任务详情" size="560px" destroy-on-close>
      <div v-if="currentDetail" class="detail-panel">
        <div class="detail-head"><el-tag>{{ currentDetail.video_code }}</el-tag><strong>{{ currentDetail.publish_platform || '未设置平台' }}</strong></div>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="脚本ID">{{ currentDetail.script_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="素材状态">{{ currentDetail.material_status || '-' }}</el-descriptions-item>
          <el-descriptions-item label="生成工具">{{ currentDetail.generate_tool || '-' }}</el-descriptions-item>
          <el-descriptions-item label="负责人">{{ currentDetail.editor || '-' }}</el-descriptions-item>
          <el-descriptions-item label="版本">{{ currentDetail.version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="发布状态">{{ currentDetail.publish_status || '-' }}</el-descriptions-item>
        </el-descriptions>
        <h3>质检项</h3><pre class="detail-content">{{ currentDetail.quality_items || '暂无内容' }}</pre>
        <h3>备注</h3><pre class="detail-content">{{ currentDetail.notes || '暂无内容' }}</pre>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { videosApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const list = ref([])
const dialogVisible = ref(false)
const detailVisible = ref(false)
const currentDetail = ref(null)
const form = ref({})

const loadList = async () => { const res = await videosApi.list(); list.value = res.data }
const showDetail = (row) => { currentDetail.value = row; detailVisible.value = true }
const showDialog = (row) => {
  form.value = row ? { ...row } : { video_code: '', script_id: 1, material_status: '待准备', generate_tool: '', editor: '', version: 'v1', quality_items: '', publish_platform: '', publish_status: '未发布' }
  dialogVisible.value = true
}
const handleSave = async () => {
  try {
    if (form.value.id) await videosApi.update(form.value.id, form.value)
    else await videosApi.create(form.value)
    ElMessage.success('保存成功'); dialogVisible.value = false; loadList()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '保存失败') }
}
const handleDelete = async (id) => {
  await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' })
  await videosApi.delete(id); ElMessage.success('删除成功'); loadList()
}
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
