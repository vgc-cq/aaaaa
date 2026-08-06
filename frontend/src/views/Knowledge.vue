<template>
  <div>
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <div style="display:flex;align-items:center;gap:12px">
            <span style="font-weight:600">知识库 / 提示词库</span>
            <el-button type="danger" size="small" :disabled="selectedIds.length === 0" @click="handleBatchDelete">删除</el-button>
          </div>
          <div>
            <el-select v-model="filterCategory" placeholder="按分类筛选" clearable style="margin-right:10px;width:160px" @change="loadList">
              <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
            </el-select>
            <el-button type="primary" @click="showDialog()">新增知识</el-button>
          </div>
        </div>
      </template>
      <el-table :data="list" stripe @selection-change="onSelectionChange">
        <el-table-column type="selection" width="45" />
        <el-table-column prop="knowledge_code" label="编号" width="80" />
        <el-table-column prop="category" label="分类" width="120">
          <template #default="{ row }"><el-tag size="small">{{ row.category }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="100" />
        <el-table-column prop="applicable_scene" label="适用场景" width="150" />
        <el-table-column label="内容摘要" min-width="320">
          <template #default="{ row }">
            <div class="multi-line-cell summary-click" @click="showDetail(row)">{{ row.content_summary || '暂无内容' }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="prompt_version" label="版本" width="90" />
        <el-table-column label="使用效果" width="150">
          <template #default="{ row }"><div class="multi-line-cell">{{ row.usage_effect || '-' }}</div></template>
        </el-table-column>
        <el-table-column prop="updater" label="更新人" width="90" />
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

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑知识' : '新增知识'" width="600px">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="知识编号"><el-input v-model="form.knowledge_code" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="分类">
            <el-select v-model="form.category" filterable allow-create>
              <el-option label="商品卖点库" value="商品卖点库" />
              <el-option label="提示词库" value="提示词库" />
              <el-option label="投流复盘库" value="投流复盘库" />
              <el-option label="客服话术库" value="客服话术库" />
              <el-option label="员工SOP" value="员工SOP" />
              <el-option label="爆款内容库" value="爆款内容库" />
              <el-option label="脚本库" value="脚本库" />
            </el-select>
          </el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="来源"><el-input v-model="form.source" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="更新人"><el-input v-model="form.updater" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="适用场景"><el-input v-model="form.applicable_scene" /></el-form-item>
        <el-form-item label="内容摘要"><el-input v-model="form.content_summary" type="textarea" :rows="4" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="提示词版本"><el-input v-model="form.prompt_version" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="使用效果"><el-input v-model="form.usage_effect" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="知识详情" size="520px" destroy-on-close>
      <div v-if="currentDetail" class="detail-panel">
        <div class="detail-head">
          <el-tag>{{ currentDetail.category }}</el-tag>
          <strong>{{ currentDetail.knowledge_code }}</strong>
        </div>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="来源">{{ currentDetail.source || '-' }}</el-descriptions-item>
          <el-descriptions-item label="适用场景">{{ currentDetail.applicable_scene || '-' }}</el-descriptions-item>
          <el-descriptions-item label="版本">{{ currentDetail.prompt_version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="使用效果">{{ currentDetail.usage_effect || '-' }}</el-descriptions-item>
          <el-descriptions-item label="更新人">{{ currentDetail.updater || '-' }}</el-descriptions-item>
        </el-descriptions>
        <h3>完整内容摘要</h3>
        <pre class="detail-content">{{ currentDetail.content_summary || '暂无内容' }}</pre>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { knowledgeApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const list = ref([])
const selectedIds = ref([])
const categories = ref([])
const filterCategory = ref('')
const dialogVisible = ref(false)
const detailVisible = ref(false)
const currentDetail = ref(null)
const form = ref({})

const loadList = async () => {
  const params = filterCategory.value ? { category: filterCategory.value } : {}
  const res = await knowledgeApi.list(params)
  list.value = res.data
}

const loadCategories = async () => {
  const res = await knowledgeApi.categories()
  categories.value = res.data
}

const showDetail = (row) => {
  currentDetail.value = row
  detailVisible.value = true
}

const showDialog = (row) => {
  form.value = row ? { ...row } : { knowledge_code: '', category: '', source: '', applicable_scene: '', content_summary: '', prompt_version: 'v1.0', usage_effect: '', updater: '' }
  dialogVisible.value = true
}

const handleSave = async () => {
  try {
    if (form.value.id) { await knowledgeApi.update(form.value.id, form.value) }
    else { await knowledgeApi.create(form.value) }
    ElMessage.success('保存成功'); dialogVisible.value = false; loadList(); loadCategories()
  } catch (e) { ElMessage.error('保存失败') }
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' })
  await knowledgeApi.delete(id); ElMessage.success('删除成功'); loadList()
}

const onSelectionChange = (rows) => {
  selectedIds.value = rows.map(r => r.id)
}

const handleBatchDelete = async () => {
  if (selectedIds.value.length === 0) { ElMessage.warning('请先勾选要删除的记录'); return }
  try {
    await ElMessageBox.confirm(`确认删除选中的 ${selectedIds.value.length} 条知识条目？`, '提示', { type: 'warning' })
    const res = await knowledgeApi.batchDelete(selectedIds.value)
    ElMessage.success(res.data.message || '删除成功')
    loadList()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error('批量删除失败：' + (e.response?.data?.detail || '请稍后重试'))
  }
}

onMounted(() => { loadList(); loadCategories() })
</script>

<style scoped>
.summary-cell {
  width: 100%;
  display: block;
  border: 0;
  background: transparent;
  color: #5f6673;
  text-align: left;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font: inherit;
}
.summary-cell:hover { color: #2454ff; text-decoration: underline; }
.plain-ellipsis { display:block; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.multi-line-cell {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  overflow: hidden;
  white-space: normal;
  line-height: 1.6;
  max-height: calc(1.6em * 3);
  color: #5f6673;
}
.summary-click { cursor:pointer; }
.detail-panel { padding-right: 6px; }
.detail-head { display:flex; align-items:center; gap:12px; margin-bottom:16px; }
.detail-head strong { font-size:20px; }
.detail-panel h3 { margin:22px 0 10px; font-size:16px; }
.detail-content { white-space:pre-wrap; word-break:break-word; line-height:1.8; background:#f6f8fb; border:1px solid rgba(20,33,61,.08); border-radius:14px; padding:16px; color:#334155; }
.action-row { display:flex; align-items:center; gap:10px; flex-wrap:nowrap; white-space:nowrap; }
.action-row :deep(.el-button) { margin-left:0; }
.action-btn { color:#334155; border-color:#d8e0ea; background:#fff; }
.action-btn:hover { color:#2454ff; border-color:#9db9ff; background:#f5f8ff; }
</style>
