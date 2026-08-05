<template>
  <div>
    <el-card class="table-card">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="font-weight:600">秒级脚本分镜表</span>
          <el-button type="primary" @click="showDialog()">新增脚本</el-button>
        </div>
      </template>
      <el-table :data="list" stripe>
        <el-table-column prop="script_code" label="编号" width="80" />
        <el-table-column prop="shot_time" label="镜头时间" width="100" />
        <el-table-column label="画面描述" min-width="240">
          <template #default="{ row }">
            <button class="summary-cell" type="button" @click="showDetail(row)">{{ row.scene_desc || '暂无画面描述' }}</button>
          </template>
        </el-table-column>
        <el-table-column prop="voiceover" label="旁白" min-width="220" />
        <el-table-column prop="subtitle" label="字幕" min-width="180" />
        <el-table-column prop="camera_move" label="镜头运动" width="150" />
        <el-table-column prop="review_status" label="审核状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.review_status === '已通过' ? 'success' : row.review_status === '已驳回' ? 'danger' : 'warning'" size="small">
              {{ row.review_status || '待审核' }}
            </el-tag>
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

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑脚本' : '新增脚本'" width="600px">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="脚本编号"><el-input v-model="form.script_code" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="镜头时间"><el-input v-model="form.shot_time" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="画面描述"><el-input v-model="form.scene_desc" type="textarea" /></el-form-item>
        <el-form-item label="旁白"><el-input v-model="form.voiceover" type="textarea" /></el-form-item>
        <el-form-item label="字幕"><el-input v-model="form.subtitle" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="镜头运动"><el-input v-model="form.camera_move" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="审核状态">
            <el-select v-model="form.review_status">
              <el-option label="待审核" value="待审核" />
              <el-option label="已通过" value="已通过" />
              <el-option label="已驳回" value="已驳回" />
            </el-select>
          </el-form-item></el-col>
        </el-row>
        <el-form-item label="素材要求"><el-input v-model="form.material_req" type="textarea" /></el-form-item>
        <el-form-item label="AI提示词"><el-input v-model="form.ai_prompt" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="脚本分镜详情" size="560px" destroy-on-close>
      <div v-if="currentDetail" class="detail-panel">
        <div class="detail-head">
          <el-tag>{{ currentDetail.script_code }}</el-tag>
          <strong>{{ currentDetail.shot_time || '未设置镜头时间' }}</strong>
        </div>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="审核状态">{{ currentDetail.review_status || '-' }}</el-descriptions-item>
          <el-descriptions-item label="关联商品">{{ currentDetail.product_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="关联内容">{{ currentDetail.content_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="负责人">{{ currentDetail.owner || '-' }}</el-descriptions-item>
        </el-descriptions>
        <h3>画面描述</h3>
        <pre class="detail-content">{{ currentDetail.scene_desc || '暂无内容' }}</pre>
        <h3>旁白</h3>
        <pre class="detail-content">{{ currentDetail.voiceover || '暂无内容' }}</pre>
        <h3>字幕</h3>
        <pre class="detail-content">{{ currentDetail.subtitle || '暂无内容' }}</pre>
        <h3>镜头运动</h3>
        <pre class="detail-content">{{ currentDetail.camera_move || '暂无内容' }}</pre>
        <h3>素材要求</h3>
        <pre class="detail-content">{{ currentDetail.material_req || '暂无内容' }}</pre>
        <h3>AI提示词</h3>
        <pre class="detail-content">{{ currentDetail.ai_prompt || '暂无内容' }}</pre>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { scriptsApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const list = ref([])
const dialogVisible = ref(false)
const detailVisible = ref(false)
const currentDetail = ref(null)
const form = ref({})

const loadList = async () => {
  const res = await scriptsApi.list()
  list.value = res.data
}

const showDetail = (row) => {
  currentDetail.value = row
  detailVisible.value = true
}

const showDialog = (row) => {
  form.value = row ? { ...row } : {
    script_code: '',
    shot_time: '',
    scene_desc: '',
    voiceover: '',
    subtitle: '',
    camera_move: '',
    material_req: '',
    ai_prompt: '',
    review_status: '待审核',
  }
  dialogVisible.value = true
}

const handleSave = async () => {
  try {
    if (form.value.id) await scriptsApi.update(form.value.id, form.value)
    else await scriptsApi.create(form.value)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    loadList()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  }
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' })
  await scriptsApi.delete(id)
  ElMessage.success('删除成功')
  loadList()
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
