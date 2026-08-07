<template>
  <div>
    <el-card class="table-card">
      <template #header>
        <div class="page-header">
          <div class="header-left">
            <span style="font-weight:600">秒级脚本分镜表</span>
            <el-button type="danger" size="small" :disabled="selectedIds.length === 0" @click="handleBatchDelete">删除</el-button>
            <el-select
              v-model="genProductId"
              clearable
              filterable
              placeholder="关联商品"
              style="width:230px"
              @change="onGenProductChange"
            >
              <el-option
                v-for="p in productOptions"
                :key="p.id"
                :label="`${p.product_code} ${p.name}`"
                :value="p.id"
              />
            </el-select>
            <el-select
              v-model="genContentId"
              clearable
              filterable
              placeholder="关联拆解"
              style="width:270px"
            >
              <el-option
                v-for="c in filteredGenContents"
                :key="c.id"
                :label="`${c.content_code} ${c.scene || c.hook || '未命名内容'}`"
                :value="c.id"
              />
            </el-select>
          </div>
          <el-button type="primary" :loading="generating" @click="generateScript">
            {{ generating ? '生成中…' : '生成脚本' }}
          </el-button>
        </div>
      </template>

      <el-table :data="groupedList" stripe @selection-change="onSelectionChange">
        <el-table-column type="selection" width="45" />
        <el-table-column label="脚本标题" min-width="170">
          <template #default="{ row }">
            <span>{{ row.title || '未命名脚本' }}</span>
            <el-tag v-if="row.scenes.length > 1" size="small" style="margin-left:8px">共 {{ row.scenes.length }} 镜</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="关联商品" min-width="170">
          <template #default="{ row }">{{ productName(row.product_id) }}</template>
        </el-table-column>
        <el-table-column label="关联内容" min-width="170">
          <template #default="{ row }">{{ contentName(row.content_id) }}</template>
        </el-table-column>
        <el-table-column label="镜头数" min-width="170">
          <template #default="{ row }">{{ row.scenes.length }}</template>
        </el-table-column>
        <el-table-column label="审核状态" min-width="170">
          <template #default="{ row }">
            <el-dropdown @command="(val) => handleGroupReview(row, val)">
              <span class="status-tag-wrap">
                <el-tag :type="groupStatusType(row)" size="small">{{ groupStatus(row) }}</el-tag>
                <el-icon class="status-tag-arrow"><ArrowDown /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="待审核">待审核</el-dropdown-item>
                  <el-dropdown-item command="已通过">已通过</el-dropdown-item>
                  <el-dropdown-item command="已驳回">已驳回</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
        <el-table-column type="expand" width="50">
          <template #default="{ row }">
            <el-table :data="row.scenes" size="small" border class="nested-table">
              <el-table-column prop="script_code" label="编号" width="80" />
              <el-table-column prop="shot_time" label="镜头时间" width="90" />
              <el-table-column label="画面描述" min-width="180">
                <template #default="{ row: sc }"><div class="clamp-3">{{ sc.scene_desc || '-' }}</div></template>
              </el-table-column>
              <el-table-column label="旁白" min-width="160">
                <template #default="{ row: sc }"><div class="clamp-3">{{ sc.voiceover || '-' }}</div></template>
              </el-table-column>
              <el-table-column label="字幕" min-width="120">
                <template #default="{ row: sc }"><div class="clamp-3">{{ sc.subtitle || '-' }}</div></template>
              </el-table-column>
              <el-table-column label="镜头运动" min-width="100">
                <template #default="{ row: sc }"><div class="clamp-3">{{ sc.camera_move || '-' }}</div></template>
              </el-table-column>
              <el-table-column label="素材要求" min-width="120">
                <template #default="{ row: sc }"><div class="clamp-3">{{ sc.material_req || '-' }}</div></template>
              </el-table-column>
              <el-table-column label="AI提示词" min-width="150">
                <template #default="{ row: sc }"><div class="clamp-3">{{ sc.ai_prompt || '-' }}</div></template>
              </el-table-column>
              <el-table-column label="审核状态" width="100">
                <template #default="{ row: sc }">
                  <el-tag
                    :type="sc.review_status === '已通过' ? 'success' : sc.review_status === '已驳回' ? 'danger' : 'warning'"
                    size="small"
                  >{{ sc.review_status || '待审核' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="210" fixed="right">
                <template #default="{ row: sc }">
                  <div class="actions-nowrap">
                    <el-button size="small" @click="showDetail(sc)">详情</el-button>
                    <el-button size="small" @click="showDialog(sc)">编辑</el-button>
                    <el-button size="small" type="danger" @click="handleDelete(sc.id)">删除</el-button>
                  </div>
                </template>
              </el-table-column>
            </el-table>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="编辑脚本" width="680px">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="关联商品">
              <el-select
                v-model="form.product_id"
                clearable
                filterable
                placeholder="从商品库选择"
                @change="onProductChange"
                style="width:100%"
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
          <el-col :span="12">
            <el-form-item label="关联内容">
              <el-select
                v-model="form.content_id"
                clearable
                filterable
                placeholder="从内容拆解选择"
                @change="onContentChange"
                style="width:100%"
              >
                <el-option
                  v-for="c in filteredContentOptions"
                  :key="c.id"
                  :label="`${c.content_code} ${c.scene || c.hook || '未命名内容'}`"
                  :value="c.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <div v-if="selectedContent" class="ref-panel">
          <div class="ref-title">拆解参考（来自内容拆解）</div>
          <el-descriptions :column="1" size="small" border>
            <el-descriptions-item label="开头钩子">{{ selectedContent.hook || '-' }}</el-descriptions-item>
            <el-descriptions-item label="场景">{{ selectedContent.scene || '-' }}</el-descriptions-item>
            <el-descriptions-item label="人群">{{ selectedContent.target_group || '-' }}</el-descriptions-item>
            <el-descriptions-item label="内容结构">{{ selectedContent.structure || '-' }}</el-descriptions-item>
            <el-descriptions-item label="转化点">{{ selectedContent.conversion_point || '-' }}</el-descriptions-item>
            <el-descriptions-item label="二创角度">{{ selectedContent.remix_angles || '-' }}</el-descriptions-item>
          </el-descriptions>
        </div>

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
          <el-descriptions-item label="关联商品">{{ productName(currentDetail.product_id) }}</el-descriptions-item>
          <el-descriptions-item label="关联内容">{{ contentName(currentDetail.content_id) }}</el-descriptions-item>
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
import { ref, computed, onMounted } from 'vue'
import { scriptsApi, productsApi, contentsApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const rawList = ref([])
const selectedIds = ref([])
const dialogVisible = ref(false)
const detailVisible = ref(false)
const currentDetail = ref(null)
const form = ref({})
const generating = ref(false)
const productOptions = ref([])
const contentOptions = ref([])
const genProductId = ref(null)
const genContentId = ref(null)

// 同一内容拆解（同一爆款视频）生成的所有镜头合并为一组
const groupedList = computed(() => {
  const groups = []
  const byContent = new Map()
  for (const s of rawList.value) {
    if (s.content_id) {
      let g = byContent.get(s.content_id)
      if (!g) {
        g = { content_id: s.content_id, product_id: s.product_id, title: s.title || '未命名脚本', scenes: [] }
        byContent.set(s.content_id, g)
      }
      g.scenes.push(s)
    } else {
      groups.push({
        content_id: null,
        product_id: s.product_id,
        title: s.title || s.scene_desc || s.script_code || '手动脚本',
        scenes: [s],
      })
    }
  }
  groups.push(...byContent.values())
  return groups
})

const filteredGenContents = computed(() => {
  if (!genProductId.value) return contentOptions.value
  return contentOptions.value.filter(c => c.product_id === genProductId.value)
})

const filteredContentOptions = computed(() => {
  if (!form.value.product_id) return contentOptions.value
  return contentOptions.value.filter(c => c.product_id === form.value.product_id)
})

const selectedContent = computed(() => contentOptions.value.find(c => c.id === form.value.content_id) || null)

const loadList = async () => {
  const res = await scriptsApi.list()
  rawList.value = res.data
}

const loadProducts = async () => {
  const res = await productsApi.list({ limit: 500 })
  productOptions.value = res.data
}

const loadContents = async () => {
  const res = await contentsApi.list({ limit: 500 })
  contentOptions.value = res.data
}

const productName = (id) => {
  const p = productOptions.value.find(x => x.id === id)
  return p ? `${p.product_code} ${p.name}` : (id || '-')
}

const contentName = (id) => {
  const c = contentOptions.value.find(x => x.id === id)
  return c ? `${c.content_code} ${c.scene || c.hook || ''}` : (id || '-')
}

const groupStatus = (row) => {
  const statuses = row.scenes.map(s => s.review_status || '待审核')
  if (statuses.every(s => s === '已通过')) return '已通过'
  if (statuses.some(s => s === '已驳回')) return '已驳回'
  return '待审核'
}

const groupStatusType = (row) => {
  const s = groupStatus(row)
  return s === '已通过' ? 'success' : s === '已驳回' ? 'danger' : 'warning'
}

const handleGroupReview = async (row, status) => {
  const ids = row.scenes.map(s => s.id)
  if (!ids.length) return
  try {
    const res = await scriptsApi.batchReview(ids, status)
    ElMessage.success(res.data.message || '审核状态更新成功')
    loadList()
  } catch (e) {
    ElMessage.error('更新失败：' + (e.response?.data?.detail || '请稍后重试'))
  }
}

const onGenProductChange = () => {
  const matches = genProductId.value
    ? contentOptions.value.filter(c => c.product_id === genProductId.value)
    : contentOptions.value
  // 商品变了，若当前拆解不属于该商品则清空
  if (genContentId.value && !matches.some(c => c.id === genContentId.value)) {
    genContentId.value = null
  }
  // 自动填上该商品对应的拆解记录（多条时默认选第一条，仍可手动切换）
  if (!genContentId.value && matches.length > 0) {
    genContentId.value = matches[0].id
  }
}

const generateScript = async () => {
  if (!genContentId.value) {
    ElMessage.warning('请先选择关联商品和内容拆解记录')
    return
  }
  generating.value = true
  try {
    const res = await scriptsApi.generate({
      content_id: genContentId.value,
      product_id: genProductId.value || undefined,
    })
    ElMessage.success(res.data.message || '生成成功')
    genContentId.value = null
    genProductId.value = null
    loadList()
  } catch (e) {
    ElMessage.error('生成失败：' + (e.response?.data?.detail || '请检查 DeepSeek API Key 配置'))
  } finally {
    generating.value = false
  }
}

const showDetail = (row) => {
  currentDetail.value = row
  detailVisible.value = true
}

const showDialog = (row) => {
  form.value = row ? { ...row } : {
    script_code: '',
    product_id: null,
    content_id: null,
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

const onProductChange = () => {
  if (form.value.content_id && !filteredContentOptions.value.some(c => c.id === form.value.content_id)) {
    form.value.content_id = null
  }
}

const onContentChange = (id) => {
  const c = contentOptions.value.find(x => x.id === id)
  if (!c) return
  if (!String(form.value.scene_desc || '').trim()) form.value.scene_desc = c.structure || ''
  if (!String(form.value.voiceover || '').trim()) form.value.voiceover = c.hook || ''
  if (!String(form.value.subtitle || '').trim()) form.value.subtitle = c.conversion_point || ''
  if (!String(form.value.material_req || '').trim()) form.value.material_req = c.scene || ''
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

const onSelectionChange = (rows) => {
  selectedIds.value = rows.flatMap(r => r.scenes.map(s => s.id))
}

const handleBatchDelete = async () => {
  if (selectedIds.value.length === 0) { ElMessage.warning('请先勾选要删除的记录'); return }
  try {
    await ElMessageBox.confirm(`确认删除选中的 ${selectedIds.value.length} 条脚本记录？`, '提示', { type: 'warning' })
    const res = await scriptsApi.batchDelete(selectedIds.value)
    ElMessage.success(res.data.message || '删除成功')
    loadList()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error('批量删除失败：' + (e.response?.data?.detail || '请稍后重试'))
  }
}

onMounted(() => {
  loadList()
  loadProducts()
  loadContents()
})
</script>

<style scoped>
.table-card { margin-top:20px; }
.page-header { display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; }
.header-left { display:flex; align-items:center; gap:12px; }
.nested-table { margin:0 12px 12px; border-radius:10px; overflow:hidden; }
.clamp-3 {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  overflow: hidden;
  white-space: normal;
  line-height: 1.6;
  max-height: calc(1.6em * 3);
  color: #5f6673;
}
.actions-nowrap { white-space: nowrap; }
.status-tag-wrap { display:inline-flex; align-items:center; gap:5px; cursor:pointer; }
.status-tag-arrow { font-size:12px; color:#94a3b8; }
.ref-panel { background:#f8fafc; border:1px solid rgba(20,33,61,.08); border-radius:12px; padding:12px; margin-bottom:14px; }
.ref-title { font-weight:700; color:#334155; margin-bottom:10px; }
.detail-panel { padding-right:6px; }
.detail-head { display:flex; align-items:center; gap:12px; margin-bottom:16px; }
.detail-head strong { font-size:20px; }
.detail-panel h3 { margin:22px 0 10px; font-size:16px; }
.detail-content { white-space:pre-wrap; word-break:break-word; line-height:1.8; background:#f6f8fb; border:1px solid rgba(20,33,61,.08); border-radius:14px; padding:16px; color:#334155; }
</style>
