<template>
  <div>
    <el-card class="table-card">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="font-weight:600">商品库</span>
          <el-button type="primary" @click="showDialog()">新增商品</el-button>
        </div>
      </template>
      <el-table :data="list" stripe>
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
              <el-button class="action-btn" size="small" @click="handleDelete(row.id)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑商品' : '新增商品'" width="760px">
      <el-alert
        v-if="!form.id"
        title="一键导入：可以粘贴商品文本，或上传 txt/docx/xlsx/csv 文档，系统会自动识别商品名、价格、佣金、类目、热度、口碑、卖点等字段。"
        type="info"
        show-icon
        :closable="false"
        style="margin-bottom:12px"
      />
      <div v-if="!form.id" class="import-box">
        <el-upload
          class="doc-upload"
          action="#"
          :auto-upload="false"
          :limit="1"
          accept=".txt,.docx,.xlsx,.csv"
          :on-change="handleDocChange"
          :on-remove="handleDocRemove"
        >
          <el-button>选择商品文档</el-button>
          <template #tip>
            <span class="doc-tip">支持 txt/docx/xlsx/csv，解析结果会先填入表单，确认后再保存。</span>
          </template>
        </el-upload>
        <el-input
          v-model="importText"
          type="textarea"
          :rows="4"
          placeholder="示例：商品名称：便携式无线榨汁杯；类目：厨房小家电；价格：79-129元；佣金：15%；热度：月销5000+；口碑：4.8分/好评率96%；卖点：便携、无线、易清洗；目标人群：上班族、学生；痛点：外卖饮品价格高、清洗麻烦"
        />
        <div class="import-actions">
          <el-button type="success" @click="oneClickImport">一键导入到表单</el-button>
          <el-button type="primary" :loading="docImportLoading" @click="importDocument">文档一键导入</el-button>
          <el-button @click="fillImportSample">填入示例</el-button>
          <el-button @click="importText = ''">清空</el-button>
        </div>
      </div>

      <el-form :model="form" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="商品编号"><el-input v-model="form.product_code" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="商品名称"><el-input v-model="form.name" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="类目"><el-input v-model="form.category" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="负责人"><el-input v-model="form.owner" /></el-form-item></el-col>
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
          <el-col :span="12"><el-form-item label="评分"><el-input-number v-model="form.score" :min="0" :max="100" /></el-form-item></el-col>
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
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
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
const importText = ref('')
const selectedDocFile = ref(null)
const docImportLoading = ref(false)

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
  form.value = row ? { ...row } : defaultForm()
  importText.value = ''
  dialogVisible.value = true
}

const showDetail = (row) => {
  currentDetail.value = row
  detailVisible.value = true
}

const fillImportSample = () => {
  importText.value = '商品名称：便携式无线榨汁杯；类目：厨房小家电；价格：79-129元；佣金：15%；热度：月销5000+；口碑：4.8分/好评率96%；目标人群：上班族、学生、宝妈、健身人群；卖点：便携、无线、易清洗、制作快、容量适中；痛点：外卖饮品价格高、早上时间紧、传统榨汁机清洗麻烦；风险词：治疗、减肥保证、绝对最低价、全网第一；评分：85；负责人：张三；状态：已选品'
}

const handleDocChange = (uploadFile) => {
  selectedDocFile.value = uploadFile.raw
}

const handleDocRemove = () => {
  selectedDocFile.value = null
}

const normalizeImported = (data) => {
  const cleaned = {}
  Object.entries(data || {}).forEach(([key, value]) => {
    cleaned[key] = value === null ? '' : value
  })
  return cleaned
}

const importDocument = async () => {
  if (!selectedDocFile.value) {
    ElMessage.warning('请先选择 txt/docx/xlsx/csv 商品文档')
    return
  }
  docImportLoading.value = true
  try {
    const fd = new FormData()
    fd.append('file', selectedDocFile.value)
    const res = await productsApi.importDocument(fd)
    form.value = {
      ...form.value,
      ...normalizeImported(res.data.parsed),
      product_code: res.data.parsed?.product_code || form.value.product_code || nextProductCode(),
    }
    importText.value = res.data.text_preview || importText.value
    ElMessage.success('文档解析完成，已填入表单，请确认后保存')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '文档导入失败')
  } finally {
    docImportLoading.value = false
  }
}

const pickText = (text, names) => {
  for (const name of names) {
    const reg = new RegExp(`${name}[：:：]?\\s*([^；;\\n]+)`, 'i')
    const m = text.match(reg)
    if (m) return m[1].trim()
  }
  return ''
}

const parsePrice = (text) => {
  const m = text.match(/(?:价格|售价|价格区间)[：:：]?\s*¥?\s*(\d+(?:\.\d+)?)\s*[-~—至到]\s*¥?\s*(\d+(?:\.\d+)?)/i)
  if (m) return { min: Number(m[1]), max: Number(m[2]) }
  const single = text.match(/(?:价格|售价)[：:：]?\s*¥?\s*(\d+(?:\.\d+)?)/i)
  if (single) return { min: Number(single[1]), max: Number(single[1]) }
  return null
}

const parsePercent = (value) => {
  const m = String(value || '').match(/(\d+(?:\.\d+)?)/)
  return m ? Number(m[1]) : 0
}

const oneClickImport = () => {
  const text = importText.value.trim()
  if (!text) {
    ElMessage.warning('请先粘贴商品信息，或点击“填入示例”')
    return
  }
  const price = parsePrice(text)
  const productName = pickText(text, ['商品名称', '商品名', '名称', '产品名称'])
  form.value = {
    ...form.value,
    product_code: form.value.product_code || nextProductCode(),
    name: productName || form.value.name,
    category: pickText(text, ['类目', '分类', '品类']) || form.value.category,
    price_min: price?.min ?? form.value.price_min,
    price_max: price?.max ?? form.value.price_max,
    commission: parsePercent(pickText(text, ['佣金', '佣金比例'])) || form.value.commission,
    sales_heat: pickText(text, ['热度', '销量', '销量/热度']) || form.value.sales_heat,
    reputation: pickText(text, ['口碑', '评价', '好评率']) || form.value.reputation,
    target_users: pickText(text, ['目标人群', '目标用户', '人群']) || form.value.target_users,
    selling_points: pickText(text, ['卖点', '核心卖点', '可表达卖点']) || form.value.selling_points,
    pain_points: pickText(text, ['痛点', '用户痛点']) || form.value.pain_points,
    risk_words: pickText(text, ['风险词', '合规风险']) || form.value.risk_words,
    owner: pickText(text, ['负责人', '维护人']) || form.value.owner,
    status: pickText(text, ['状态']) || form.value.status,
    score: parsePercent(pickText(text, ['评分', '选品评分'])) || form.value.score,
  }
  ElMessage.success('已导入到表单，请检查后保存')
}

const handleSave = async () => {
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
.import-box {
  margin-bottom: 18px;
  padding: 14px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid rgba(20, 33, 61, .08);
}
.import-actions {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}
.doc-upload {
  margin-bottom: 12px;
}
.doc-tip {
  margin-left: 10px;
  color: #64748b;
  font-size: 13px;
}
</style>
