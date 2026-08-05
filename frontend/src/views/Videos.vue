<template>
  <div>
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="font-weight:600">视频生产任务表</span>
          <el-button type="primary" @click="showDialog()">新增视频</el-button>
        </div>
      </template>
      <el-table :data="list" stripe>
        <el-table-column prop="video_code" label="编号" width="80" />
        <el-table-column prop="material_status" label="素材状态" width="90" />
        <el-table-column prop="generate_tool" label="生成工具" width="120" />
        <el-table-column prop="editor" label="负责人" width="80" />
        <el-table-column prop="version" label="版本" width="70" />
        <el-table-column prop="quality_items" label="质检项" show-overflow-tooltip />
        <el-table-column prop="publish_platform" label="平台" width="80" />
        <el-table-column prop="publish_status" label="发布状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.publish_status === '已发布' ? 'success' : row.publish_status === '审核中' ? 'warning' : 'info'" size="small">{{ row.publish_status }}</el-tag>
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

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑视频' : '新增视频'" width="600px">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="视频编号"><el-input v-model="form.video_code" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="负责人"><el-input v-model="form.editor" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="素材状态">
            <el-select v-model="form.material_status">
              <el-option label="待准备" value="待准备" />
              <el-option label="已完成" value="已完成" />
            </el-select>
          </el-form-item></el-col>
          <el-col :span="12"><el-form-item label="生成工具"><el-input v-model="form.generate_tool" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="质检项"><el-input v-model="form.quality_items" type="textarea" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="发布平台"><el-input v-model="form.publish_platform" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="发布状态">
            <el-select v-model="form.publish_status">
              <el-option label="未发布" value="未发布" />
              <el-option label="审核中" value="审核中" />
              <el-option label="已发布" value="已发布" />
            </el-select>
          </el-form-item></el-col>
        </el-row>
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
import { videosApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const list = ref([])
const dialogVisible = ref(false)
const form = ref({})

const loadList = async () => {
  const res = await videosApi.list()
  list.value = res.data
}

const showDialog = (row) => {
  form.value = row ? { ...row } : { video_code: '', material_status: '待准备', generate_tool: '', editor: '', version: 'v1', quality_items: '', publish_platform: '', publish_status: '未发布' }
  dialogVisible.value = true
}

const handleSave = async () => {
  try {
    if (form.value.id) { await videosApi.update(form.value.id, form.value) }
    else { await videosApi.create(form.value) }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    loadList()
  } catch (e) { ElMessage.error('保存失败') }
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' })
  await videosApi.delete(id)
  ElMessage.success('删除成功')
  loadList()
}

onMounted(loadList)
</script>
