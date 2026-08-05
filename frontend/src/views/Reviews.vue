<template>
  <div>
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="font-weight:600">数据复盘表</span>
          <el-button type="primary" @click="showDialog()">新增复盘</el-button>
        </div>
      </template>
      <el-table :data="list" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="review_period" label="复盘周期" width="150" />
        <el-table-column prop="product_performance" label="商品表现" show-overflow-tooltip />
        <el-table-column prop="content_performance" label="内容表现" show-overflow-tooltip />
        <el-table-column prop="ad_performance" label="投流表现" show-overflow-tooltip />
        <el-table-column prop="problem_analysis" label="问题归因" show-overflow-tooltip />
        <el-table-column prop="next_action" label="优化动作" show-overflow-tooltip />
        <el-table-column prop="owner" label="负责人" width="100" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showDialog(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑复盘' : '新增复盘'" width="700px">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="复盘周期"><el-input v-model="form.review_period" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="负责人"><el-input v-model="form.owner" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="商品表现"><el-input v-model="form.product_performance" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="内容表现"><el-input v-model="form.content_performance" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="视频表现"><el-input v-model="form.video_performance" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="投流表现"><el-input v-model="form.ad_performance" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="问题归因"><el-input v-model="form.problem_analysis" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="优化动作"><el-input v-model="form.next_action" type="textarea" :rows="2" /></el-form-item>
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
import { reviewsApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const list = ref([])
const dialogVisible = ref(false)
const form = ref({})

const loadList = async () => { const res = await reviewsApi.list(); list.value = res.data }

const showDialog = (row) => {
  form.value = row ? { ...row } : { review_period: '', product_performance: '', content_performance: '', video_performance: '', ad_performance: '', problem_analysis: '', next_action: '', owner: '' }
  dialogVisible.value = true
}

const handleSave = async () => {
  try {
    if (form.value.id) { await reviewsApi.update(form.value.id, form.value) }
    else { await reviewsApi.create(form.value) }
    ElMessage.success('保存成功'); dialogVisible.value = false; loadList()
  } catch (e) { ElMessage.error('保存失败') }
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' })
  await reviewsApi.delete(id); ElMessage.success('删除成功'); loadList()
}

onMounted(loadList)
</script>
