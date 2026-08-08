<template>
  <div>
    <el-card class="table-card">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <div style="display:flex;align-items:center;gap:12px">
            <span style="font-weight:600">商品库</span>
            <el-button
              type="danger"
              size="small"
              :disabled="selectedIds.length === 0"
              @click="handleBatchDelete"
            >删除</el-button>
          </div>
          <div>
            <el-button type="primary" @click="showDialog()" style="margin-right:12px">新增商品</el-button>
          </div>
        </div>
      </template>
      <el-table :data="list" stripe @selection-change="onSelectionChange">
        <el-table-column type="selection" width="45" />
        <el-table-column prop="product_code" label="编号" width="80" />
        <el-table-column label="商品名称" min-width="180">
          <template #default="{ row }">
            <button class="summary-cell" type="button" @click="showDetail(row)">{{ row.name || '未命名商品' }}</button>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="类目" width="100" />
        <el-table-column label="价格区间" width="110">
          <template #default="{ row }">¥{{ row.price_min }}-{{ row.price_max }}</template>
        </el-table-column>
        <el-table-column label="佣金" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.commission !== null && row.commission !== undefined" type="warning" size="small">{{ row.commission }}%</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="sales_heat" label="热度" width="100" />
        <el-table-column prop="reputation" label="口碑" width="120" />
        <el-table-column prop="score" label="评分" width="70" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === '已选品' ? 'success' : 'info'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="owner" label="负责人" width="80" />
        <el-table-column label="卖点" min-width="220">
          <template #default="{ row }">
            <div class="multi-line-cell">{{ row.selling_points || '暂无卖点' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <div class="action-row">
              <el-button class="action-btn" size="small" @click="showDetail(row)">详情</el-button>
              <el-button class="action-btn" size="small" @click="showDialog(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="handleDelete(row.id)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑商品' : '新增商品'" width="780px">
      <el-tabs v-model="activeTab" v-if="!form.id">
        <!-- 页签1：手动录入 -->
        <el-tab-pane label="手动录入" name="manual">
          <el-form :model="form" label-width="100px">
            <el-row :gutter="16">
              <el-col :span="12"><el-form-item label="商品编号"><el-input v-model="form.product_code" /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="商品名称"><el-input v-model="form.name" /></el-form-item></el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="12"><el-form-item label="类目"><el-input v-model="form.category" /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="负责人"><el-input v-model="form.owner" placeholder="默认：选品运营" /></el-form-item></el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="8"><el-form-item label="最低价"><el-input-number v-model="form.price_min" :min="0" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="最高价"><el-input-number v-model="form.price_max" :min="0" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="佣金%"><el-input-number v-model="form.commission" :min="0" :max="100" :precision="1" /></el-form-item></el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="12"><el-form-item label="热度"><el-input v-model="form.sales_heat" placeholder="如：月销5000+" /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="口碑"><el-input v-model="form.reputation" placeholder="如：4.8分/好评率96%" /></el-form-item></el-col>
            </el-row>
            <el-form-item label="目标人群"><el-input v-model="form.target_users" type="textarea" /></el-form-item>
            <el-form-item label="卖点"><el-input v-model="form.selling_points" type="textarea" /></el-form-item>
            <el-form-item label="痛点"><el-input v-model="form.pain_points" type="textarea" /></el-form-item>
            <el-form-item label="风险词"><el-input v-model="form.risk_words" type="textarea" /></el-form-item>
            <el-row :gutter="16">
              <el-col :span="12"><el-form-item label="评分"><el-input-number v-model="form.score" :min="0" :max="100" disabled /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="状态">
                <el-select v-model="form.status">
                  <el-option label="待评估" value="待评估" />
                  <el-option label="已选品" value="已选品" />
                  <el-option label="已淘汰" value="已淘汰" />
                </el-select>
              </el-form-item></el-col>
            </el-row>
          </el-form>
        </el-tab-pane>

        <!-- 页签2：一键导入 -->
        <el-tab-pane label="一键导入" name="import">
          <el-alert
            title="导入说明：字段与商品库一致（商品编号、名称、类目、负责人、价格、佣金、热度、口碑、人群、卖点、痛点、风险词、评分、状态）。商品编号留空自动生成；同名商品自动跳过。"
            type="info" show-icon :closable="false" style="margin-bottom:14px"
          />
          <el-upload
            drag
            :auto-upload="false"
            :limit="1"
            accept=".xlsx"
            :on-change="onFileChange"
            :on-remove="onFileRemove"
            style="margin-bottom:16px"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽 .xlsx 文件到此处，或 <em>点击选择文件</em></div>
            <template #tip>
              <div class="el-upload__tip" style="color:#697386">
                支持一次导入多个商品。
                <el-link type="primary" :underline="false" @click="downloadTemplate">下载导入模板</el-link>
              </div>
            </template>
          </el-upload>
          <el-button type="primary" :loading="importing" @click="handleImport">一键导入</el-button>

          <div v-if="importResult" style="margin-top:16px">
            <el-alert
              :title="`导入完成：成功 ${importResult.imported} 条，跳过 ${importResult.skipped} 条`"
              type="success" :closable="false" style="margin-bottom:12px"
            />
            <el-table :data="importResult.results" max-height="280" size="small" border>
              <el-table-column prop="name" label="商品名称" min-width="150" show-overflow-tooltip />
              <el-table-column prop="product_code" label="编号" width="80" />
              <el-table-column prop="score" label="评分" width="70" />
              <el-table-column prop="status" label="状态" width="90" />
              <el-table-column prop="error" label="备注" min-width="160" show-overflow-tooltip />
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>

      <!-- 编辑模式 / 手动录入：同一套表单 -->
      <el-form v-if="form.id || activeTab === 'manual'" :model="form" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="商品编号"><el-input v-model="form.product_code" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="商品名称"><el-input v-model="form.name" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="类目"><el-input v-model="form.category" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="负责人"><el-input v-model="form.owner" placeholder="默认：选品运营" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8"><el-form-item label="最低价"><el-input-number v-model="form.price_min" :min="0" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="最高价"><el-input-number v-model="form.price_max" :min="0" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="佣金%"><el-input-number v-model="form.commission" :min="0" :max="100" :precision="1" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="热度"><el-input v-model="form.sales_heat" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="口碑"><el-input v-model="form.reputation" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="目标人群"><el-input v-model="form.target_users" type="textarea" /></el-form-item>
        <el-form-item label="卖点"><el-input v-model="form.selling_points" type="textarea" /></el-form-item>
        <el-form-item label="痛点"><el-input v-model="form.pain_points" type="textarea" /></el-form-item>
        <el-form-item label="风险词"><el-input v-model="form.risk_words" type="textarea" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="评分"><el-input-number v-model="form.score" :min="0" :max="100" disabled /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="状态">
            <el-select v-model="form.status">
              <el-option label="待评估" value="待评估" />
              <el-option label="已选品" value="已选品" />
              <el-option label="已淘汰" value="已淘汰" />
            </el-select>
          </el-form-item></el-col>
        </el-row>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button v-if="form.id || activeTab === 'manual'" type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="aiResultVisible" title="AI 选品结果" width="860px">
      <el-alert
        :title="`分析完成：共 ${aiResult?.total ?? 0} 个商品，评分已回填，状态已自动更新`"
        type="success" :closable="false" style="margin-bottom:12px"
      />
      <el-table :data="aiResult?.results || []" max-height="420" size="small" border>
        <el-table-column prop="product_code" label="编号" width="80" />
        <el-table-column prop="name" label="商品名称" min-width="140" show-overflow-tooltip />
        <el-table-column prop="score" label="评分" width="70" />
        <el-table-column prop="status" label="状态" width="90" />
        <el-table-column label="维度分" min-width="240">
          <template #default="{ row }">
            <el-tag size="small">热{{ row.dimensions?.heat }}</el-tag>
            <el-tag size="small" type="warning">口碑{{ row.dimensions?.reputation }}</el-tag>
            <el-tag size="small" type="success">佣{{ row.dimensions?.commission }}</el-tag>
            <el-tag size="small" type="info">内容{{ row.dimensions?.content }}</el-tag>
            <el-tag size="small" type="danger">合规{{ row.dimensions?.compliance }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="AI 建议" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.ai?.recommendation || '未调用 AI（未配置 Key）' }}
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="商品详情" size="560px" destroy-on-close>
      <div v-if="currentDetail" class="detail-panel">
        <div class="detail-head">
          <el-tag>{{ currentDetail.product_code }}</el-tag>
          <strong>{{ currentDetail.name || '未命名商品' }}</strong>
        </div>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="类目">{{ currentDetail.category || '-' }}</el-descriptions-item>
          <el-descriptions-item label="价格区间">¥{{ currentDetail.price_min ?? '-' }} - {{ currentDetail.price_max ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="佣金">{{ currentDetail.commission ?? '-' }}%</el-descriptions-item>
          <el-descriptions-item label="热度">{{ currentDetail.sales_heat || '-' }}</el-descriptions-item>
          <el-descriptions-item label="口碑">{{ currentDetail.reputation || '-' }}</el-descriptions-item>
          <el-descriptions-item label="评分">{{ currentDetail.score ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ currentDetail.status || '-' }}</el-descriptions-item>
          <el-descriptions-item label="负责人">{{ currentDetail.owner || '-' }}</el-descriptions-item>
        </el-descriptions>
        <h3>目标人群</h3><pre class="detail-content">{{ currentDetail.target_users || '暂无内容' }}</pre>
        <h3>卖点</h3><pre class="detail-content">{{ currentDetail.selling_points || '暂无内容' }}</pre>
        <h3>痛点</h3><pre class="detail-content">{{ currentDetail.pain_points || '暂无内容' }}</pre>
        <h3>风险词</h3><pre class="detail-content">{{ currentDetail.risk_words || '暂无内容' }}</pre>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { productsApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const list = ref([])
const dialogVisible = ref(false)
const detailVisible = ref(false)
const currentDetail = ref(null)
const form = ref({})
const activeTab = ref('manual')
const importFile = ref(null)
const importing = ref(false)
const importResult = ref(null)
const selectedIds = ref([])
const aiSelecting = ref(false)
const aiResultVisible = ref(false)
const aiResult = ref(null)

const loadList = async () => {
  const res = await productsApi.list({ limit: 500 })
  list.value = res.data
}

const defaultForm = () => ({
  product_code: nextProductCode(),
  name: '',
  category: '',
  price_min: 0,
  price_max: 0,
  commission: 0,
  sales_heat: '',
  reputation: '',
  target_users: '',
  selling_points: '',
  pain_points: '',
  risk_words: '',
  owner: '选品运营',
  status: '待评估',
  score: 0,
})

const nextProductCode = () => {
  const max = list.value.reduce((acc, item) => {
    const n = Number(String(item.product_code || '').replace(/\D/g, ''))
    return Number.isFinite(n) ? Math.max(acc, n) : acc
  }, 0)
  return `P${String(max + 1).padStart(3, '0')}`
}

const showDialog = (row) => {
  activeTab.value = 'manual'
  importFile.value = null
  importResult.value = null
  form.value = row ? { ...row } : defaultForm()
  dialogVisible.value = true
}

const showDetail = (row) => {
  currentDetail.value = row
  detailVisible.value = true
}

const onFileChange = (uploadFile) => {
  importFile.value = uploadFile.raw
  importResult.value = null
}

const onFileRemove = () => {
  importFile.value = null
  importResult.value = null
}

const downloadTemplate = async () => {
  try {
    const res = await productsApi.importTemplate()
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = '商品导入模板.xlsx'
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error('模板下载失败')
  }
}

const handleImport = async () => {
  if (!importFile.value) {
    ElMessage.warning('请先选择 .xlsx 文件')
    return
  }
  importing.value = true
  try {
    const res = await productsApi.import(importFile.value)
    importResult.value = res.data
    ElMessage.success(`导入完成：成功 ${res.data.imported} 条，跳过 ${res.data.skipped} 条`)
    loadList()
  } catch (e) {
    ElMessage.error('导入失败：' + (e.response?.data?.detail || '请检查文件格式'))
  } finally {
    importing.value = false
  }
}

const handleSave = async () => {
  if (!form.value.name || !String(form.value.name).trim()) {
    ElMessage.warning('请先填写商品名称')
    return
  }
  try {
    if (form.value.id) {
      await productsApi.update(form.value.id, form.value)
    } else {
      await productsApi.create(form.value)
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    loadList()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  }
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' })
  await productsApi.delete(id)
  ElMessage.success('删除成功')
  loadList()
}

const handleBatchDelete = async () => {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先勾选要删除的商品')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${selectedIds.value.length} 个商品？关联的内容拆解和脚本将一并删除。`,
      '提示',
      { type: 'warning' }
    )
    const res = await productsApi.batchDelete(selectedIds.value)
    ElMessage.success(res.data.message || '删除成功')
    loadList()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error('批量删除失败：' + (e.response?.data?.detail || '请稍后重试'))
    }
  }
}

const onSelectionChange = (rows) => {
  selectedIds.value = rows.map(r => r.id)
}

const handleAiSelect = async () => {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先勾选要分析的商品')
    return
  }
  aiSelecting.value = true
  try {
    const res = await productsApi.aiSelect(selectedIds.value)
    aiResult.value = res.data
    aiResultVisible.value = true
    const count = (s) => res.data.results.filter(r => r.status === s).length
    ElMessage.success(`分析完成：已选品 ${count('已选品')} 个，待评估 ${count('待评估')} 个，已淘汰 ${count('已淘汰')} 个`)
    loadList()
  } catch (e) {
    ElMessage.error('AI 选品失败：' + (e.response?.data?.detail || '请检查后端/API Key'))
  } finally {
    aiSelecting.value = false
  }
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
</style>
