<template>
  <div>
    <el-card class="vision-card">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="font-weight:600">Qwen-VL-Max 视频/图片内容拆解</span>
          <el-tag type="success">Qwen-VL-Max 看画面，DeepSeek 做拆解</el-tag>
        </div>
      </template>
      <el-form :model="visionForm" label-width="110px">
        <el-row :gutter="16">
          <el-col :span="6">
            <el-form-item label="输入类型">
              <el-select v-model="visionForm.source_type">
                <el-option label="视频URL" value="video_url" />
                <el-option label="图片URL" value="image_url" />
                <el-option label="文字描述" value="text" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="9">
            <el-form-item label="商品名称">
              <el-input v-model="visionForm.product_name" placeholder="可选，如便携式无线榨汁杯" />
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

    <el-card style="margin-top:20px">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="font-weight:600">爆款内容拆解表</span>
          <el-button type="primary" @click="showDialog()">新增内容</el-button>
        </div>
      </template>
      <el-table :data="list" stripe>
        <el-table-column prop="content_code" label="编号" width="80" />
        <el-table-column prop="hook" label="开头钩子" width="200" show-overflow-tooltip />
        <el-table-column prop="scene" label="场景" width="120" />
        <el-table-column prop="target_group" label="人群" width="100" />
        <el-table-column prop="structure" label="内容结构" show-overflow-tooltip />
        <el-table-column prop="conversion_point" label="转化点" width="120" />
        <el-table-column prop="remix_angles" label="二创角度" show-overflow-tooltip />
        <el-table-column prop="analyst" label="拆解人" width="120" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showDialog(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row.id)">删除</el-button>
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { contentsApi, visionApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const list = ref([])
const dialogVisible = ref(false)
const form = ref({})
const visionLoading = ref(false)
const uploadLoading = ref(false)
const visionResult = ref(null)
const selectedMediaFile = ref(null)
const visionForm = ref({
  source_type: 'text',
  source_url: '',
  text: '',
  product_name: '便携式无线榨汁杯',
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

const fillVisionSample = () => {
  visionForm.value = {
    source_type: 'text',
    source_url: '',
    product_name: '便携式无线榨汁杯',
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

onMounted(loadList)
</script>

<style scoped>
.vision-card { margin-bottom: 20px; }
.result-card { margin-top: 14px; background: #f8fafc !important; }
.result-block { background:#f5f7fa; padding:16px; border-radius:12px; white-space:pre-wrap; word-break:break-word; line-height:1.7; }
.upload-text { color:#334155; font-weight:600; padding:18px 0 8px; }
</style>
