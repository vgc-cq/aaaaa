<template>
  <div>
    <el-card class="vision-card">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="font-weight:600">Qwen-VL-Max 视频内容拆解</span>
          <el-tag type="success">Qwen-VL-Max 看画面，DeepSeek 做拆解</el-tag>
        </div>
      </template>
      <el-form :model="visionForm" label-width="110px">
        <el-row :gutter="16">
          <el-col :span="6">
            <el-form-item label="输入类型">
              <el-select v-model="visionForm.source_type">
                <el-option label="视频URL" value="video_url" />
                <el-option label="文字描述" value="text" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="9">
            <el-form-item label="关联商品">
              <el-select
                v-model="visionForm.product_id"
                clearable
                filterable
                placeholder="从商品库选择（可选）"
                @change="onProductChange"
              >
                <el-option
                  v-for="p in productOptions"
                  :key="p.id"
                  :label="`${p.product_code} ${p.name}`"
                  :value="p.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="9">
            <el-form-item label="是否写入表">
              <el-switch v-model="visionForm.save_to_table" active-text="自动保存" inactive-text="只预览" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item v-if="visionForm.source_type !== 'text'" label="本地上传">
          <el-upload
            drag
            action="#"
            :auto-upload="false"
            :limit="1"
            accept="image/*,video/*"
            :on-change="handleMediaChange"
            :on-remove="handleMediaRemove"
          >
            <div class="upload-text">拖拽或点击上传本地视频/图片</div>
            <template #tip>
              <div class="el-upload__tip">文件会保存到 backend/uploads，并自动回填 URL 后交给 Qwen-VL-Max 识别。</div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item v-if="visionForm.source_type !== 'text'" label="素材URL">
          <el-input v-model="visionForm.source_url" placeholder="可填写公开视频/图片URL，也可先上传本地素材自动生成" />
        </el-form-item>
        <el-form-item v-else label="文字描述">
          <el-input v-model="visionForm.text" type="textarea" :rows="4" placeholder="粘贴视频字幕、口播文案或人工画面描述" />
        </el-form-item>
        <el-form-item>
          <el-button :loading="uploadLoading" @click="uploadMedia">上传素材</el-button>
          <el-button type="primary" :loading="visionLoading" @click="runVisionBreakdown">开始拆解</el-button>
          <el-button @click="fillVisionSample">填入文字示例</el-button>
        </el-form-item>
      </el-form>

      <el-card v-if="visionResult" class="result-card" shadow="never">
        <template #header>
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span>拆解结果</span>
            <el-tag v-if="visionResult.saved" type="success">已写入：{{ visionResult.saved.content_code }}</el-tag>
          </div>
        </template>
        <el-descriptions :column="2" border style="margin-bottom:16px">
          <el-descriptions-item label="视觉模型">{{ visionResult.vision_model }}</el-descriptions-item>
          <el-descriptions-item label="分析模型">{{ visionResult.analysis_model }}</el-descriptions-item>
          <el-descriptions-item label="钩子">{{ visionResult.breakdown?.hook }}</el-descriptions-item>
          <el-descriptions-item label="目标人群">{{ visionResult.breakdown?.target_group }}</el-descriptions-item>
          <el-descriptions-item label="场景">{{ visionResult.breakdown?.scene }}</el-descriptions-item>
          <el-descriptions-item label="转化点">{{ visionResult.breakdown?.conversion_point }}</el-descriptions-item>
        </el-descriptions>
        <el-collapse>
          <el-collapse-item title="Qwen-VL-Max 输出的画面/视频文字描述" name="desc">
            <pre class="result-block">{{ visionResult.media_description }}</pre>
          </el-collapse-item>
          <el-collapse-item title="DeepSeek 内容拆解 JSON" name="json">
            <pre class="result-block">{{ formatJson(visionResult.breakdown) }}</pre>
          </el-collapse-item>
        </el-collapse>
      </el-card>
    </el-card>

    <el-card class="table-card">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="font-weight:600">爆款内容拆解表</span>
          <el-button type="primary" @click="showDialog()">新增内容</el-button>
        </div>
      </template>
      <el-table :data="list" stripe>
        <el-table-column prop="content_code" label="编号" width="80" />
        <el-table-column label="开头钩子" min-width="220">
          <template #default="{ row }">
            <button class="summary-cell" type="button" @click="showDetail(row)">{{ row.hook || '暂无钩子' }}</button>
          </template>
        </el-table-column>
        <el-table-column label="场景" min-width="170">
          <template #default="{ row }">
            <div class="multi-line-cell">{{ row.scene || '暂无场景' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="人群" min-width="170">
          <template #default="{ row }">
            <div class="multi-line-cell">{{ row.target_group || '暂无人群' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="内容结构" min-width="230">
          <template #default="{ row }">
            <div class="multi-line-cell">{{ row.structure || '暂无内容结构' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="转化点" min-width="230">
          <template #default="{ row }">
            <div class="multi-line-cell">{{ row.conversion_point || '暂无转化点' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="二创角度" min-width="210">
          <template #default="{ row }">
            <div class="multi-line-cell">{{ row.remix_angles || '暂无二创角度' }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="analyst" label="拆解人" width="150" />
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

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑内容' : '新增内容'" width="600px">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="内容编号"><el-input v-model="form.content_code" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="拆解人"><el-input v-model="form.analyst" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="对标链接"><el-input v-model="form.reference_link" /></el-form-item>
        <el-form-item label="开头钩子"><el-input v-model="form.hook" type="textarea" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="场景"><el-input v-model="form.scene" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="人群"><el-input v-model="form.target_group" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="内容结构"><el-input v-model="form.structure" type="textarea" /></el-form-item>
        <el-form-item label="转化点"><el-input v-model="form.conversion_point" /></el-form-item>
        <el-form-item label="二创角度"><el-input v-model="form.remix_angles" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="内容拆解详情" size="560px" destroy-on-close>
      <div v-if="currentDetail" class="detail-panel">
        <div class="detail-head">
          <el-tag>{{ currentDetail.content_code }}</el-tag>
          <strong>{{ currentDetail.scene || '未命名场景' }}</strong>
        </div>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="对标链接">{{ currentDetail.reference_link || '-' }}</el-descriptions-item>
          <el-descriptions-item label="目标人群">{{ currentDetail.target_group || '-' }}</el-descriptions-item>
          <el-descriptions-item label="拆解人">{{ currentDetail.analyst || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ currentDetail.status || '-' }}</el-descriptions-item>
        </el-descriptions>
        <h3>开头钩子</h3>
        <pre class="detail-content">{{ currentDetail.hook || '暂无内容' }}</pre>
        <h3>内容结构</h3>
        <pre class="detail-content">{{ currentDetail.structure || '暂无内容' }}</pre>
        <h3>转化点</h3>
        <pre class="detail-content">{{ currentDetail.conversion_point || '暂无内容' }}</pre>
        <h3>二创角度</h3>
        <pre class="detail-content">{{ currentDetail.remix_angles || '暂无内容' }}</pre>
        <h3>风险点</h3>
        <pre class="detail-content">{{ currentDetail.risk_points || '暂无内容' }}</pre>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { contentsApi, productsApi, visionApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const list = ref([])
const productOptions = ref([])
const dialogVisible = ref(false)
const detailVisible = ref(false)
const currentDetail = ref(null)
const form = ref({})
const visionLoading = ref(false)
const uploadLoading = ref(false)
const visionResult = ref(null)
const selectedMediaFile = ref(null)
const visionForm = ref({
  source_type: 'video_url',
  source_url: '',
  text: '',
  product_id: null,
  product_name: '',
  save_to_table: true,
})

const handleMediaChange = (uploadFile) => {
  selectedMediaFile.value = uploadFile.raw
  // 选择了本地素材后，清掉旧的外部 URL，避免误把旧链接拿去分析。
  visionForm.value.source_url = ''
  if (uploadFile.raw?.type?.startsWith('image/')) visionForm.value.source_type = 'image_url'
  if (uploadFile.raw?.type?.startsWith('video/')) visionForm.value.source_type = 'video_url'
}

const handleMediaRemove = () => {
  selectedMediaFile.value = null
}

const uploadMedia = async () => {
  if (visionForm.value.source_type === 'text') {
    ElMessage.warning('文字描述模式不需要上传素材')
    return
  }
  if (!selectedMediaFile.value) {
    ElMessage.warning('请先选择本地视频或图片')
    return
  }
  uploadLoading.value = true
  try {
    const fd = new FormData()
    fd.append('file', selectedMediaFile.value)
    const res = await visionApi.upload(fd)
    visionForm.value.source_url = res.data.url
    visionForm.value.source_type = res.data.source_type
    ElMessage.success('上传成功，已回填素材 URL')
    return true
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '上传失败')
    return false
  } finally {
    uploadLoading.value = false
  }
}

const loadList = async () => {
  const res = await contentsApi.list({ limit: 500 })
  list.value = res.data
}

const loadProducts = async () => {
  const res = await productsApi.list({ limit: 500 })
  productOptions.value = res.data
}

const onProductChange = (id) => {
  const p = productOptions.value.find(x => x.id === id)
  visionForm.value.product_name = p ? p.name : ''
}

const fillVisionSample = () => {
  visionForm.value = {
    source_type: 'text',
    source_url: '',
    product_id: null,
    product_name: '',
    save_to_table: true,
    text: '0-3秒：女生早上看闹钟，说每天早上多睡10分钟还能喝到新鲜果汁。3-8秒：展示便携榨汁杯放入水果，一键启动。8-15秒：对比外卖饮品价格高、含糖高。15-25秒：展示加水一键清洗。25-30秒：提示收藏并点击购物车。',
  }
}

const runVisionBreakdown = async () => {
  visionLoading.value = true
  try {
    if (visionForm.value.source_type !== 'text' && selectedMediaFile.value) {
      const ok = await uploadMedia()
      if (!ok) return
    }
    const res = await visionApi.contentBreakdown(visionForm.value)
    visionResult.value = res.data
    ElMessage.success(res.data.saved ? '拆解并写入成功' : '拆解完成')
    if (res.data.saved) loadList()
  } catch (e) {
    ElMessage({
      type: 'error',
      message: e.response?.data?.detail || '内容拆解失败',
      duration: 9000,
      showClose: true,
    })
  } finally {
    visionLoading.value = false
  }
}

const showDialog = (row) => {
  form.value = row ? { ...row } : { content_code: '', hook: '', scene: '', target_group: '', structure: '', conversion_point: '', remix_angles: '', analyst: '' }
  dialogVisible.value = true
}

const showDetail = (row) => {
  currentDetail.value = row
  detailVisible.value = true
}

const handleSave = async () => {
  try {
    if (form.value.id) await contentsApi.update(form.value.id, form.value)
    else await contentsApi.create(form.value)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    loadList()
  } catch (e) { ElMessage.error('保存失败') }
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' })
  await contentsApi.delete(id)
  ElMessage.success('删除成功')
  loadList()
}

const formatJson = (obj) => JSON.stringify(obj || {}, null, 2)

onMounted(() => {
  loadList()
  loadProducts()
})
</script>

<style scoped>
.vision-card { margin-bottom: 20px; }
.table-card { margin-top:20px; }
.result-card { margin-top: 14px; background: #f8fafc !important; }
.result-block { background:#f5f7fa; padding:16px; border-radius:12px; white-space:pre-wrap; word-break:break-word; line-height:1.7; }
.upload-text { color:#334155; font-weight:600; padding:18px 0 8px; }
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
