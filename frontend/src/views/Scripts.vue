<template>
  <div>
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="font-weight:600">秒级脚本分镜表</span>
          <el-button type="primary" @click="showDialog()">新增脚本</el-button>
        </div>
      </template>
      <el-table :data="list" stripe>
        <el-table-column prop="script_code" label="编号" width="80" />
        <el-table-column prop="shot_time" label="镜头时间" width="90" />
        <el-table-column prop="scene_desc" label="画面描述" show-overflow-tooltip />
        <el-table-column prop="voiceover" label="旁白" show-overflow-tooltip />
        <el-table-column prop="subtitle" label="字幕" width="150" show-overflow-tooltip />
        <el-table-column prop="camera_move" label="镜头运动" width="100" />
        <el-table-column prop="review_status" label="审核状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.review_status === '已通过' ? 'success' : 'warning'" size="small">{{ row.review_status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showDialog(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row.id)">删除</el-button>
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { scriptsApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const list = ref([])
const dialogVisible = ref(false)
const form = ref({})

const loadList = async () => {
  const res = await scriptsApi.list()
  list.value = res.data
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
