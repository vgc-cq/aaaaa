<template>
  <div>
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="font-weight:600">客服私域线索表</span>
          <el-button type="primary" @click="showDialog()">新增线索</el-button>
        </div>
      </template>
      <el-table :data="list" stripe>
        <el-table-column prop="lead_code" label="编号" width="80" />
        <el-table-column prop="inquiry" label="咨询内容" show-overflow-tooltip />
        <el-table-column prop="intent" label="用户意向" width="90">
          <template #default="{ row }">
            <el-tag :type="row.intent === '高' ? 'danger' : row.intent === '中' ? 'warning' : 'info'" size="small">{{ row.intent }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="follow_status" label="跟进状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.follow_status === '已加微' ? 'success' : 'warning'" size="small">{{ row.follow_status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="wechat_added" label="加微" width="70" />
        <el-table-column prop="script_template" label="话术模板" show-overflow-tooltip />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showDialog(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑线索' : '新增线索'" width="600px">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="线索编号"><el-input v-model="form.lead_code" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="来源视频ID"><el-input-number v-model="form.video_id" :min="1" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="咨询内容"><el-input v-model="form.inquiry" type="textarea" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="用户意向">
            <el-select v-model="form.intent">
              <el-option label="高" value="高" /><el-option label="中" value="中" /><el-option label="低" value="低" />
            </el-select>
          </el-form-item></el-col>
          <el-col :span="12"><el-form-item label="跟进状态">
            <el-select v-model="form.follow_status">
              <el-option label="待跟进" value="待跟进" /><el-option label="已加微" value="已加微" /><el-option label="已成交" value="已成交" />
            </el-select>
          </el-form-item></el-col>
        </el-row>
        <el-form-item label="话术模板"><el-input v-model="form.script_template" type="textarea" /></el-form-item>
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
import { leadsApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const list = ref([])
const dialogVisible = ref(false)
const form = ref({})

const loadList = async () => { const res = await leadsApi.list(); list.value = res.data }

const showDialog = (row) => {
  form.value = row ? { ...row } : { lead_code: '', video_id: 1, inquiry: '', intent: '中', follow_status: '待跟进', wechat_added: '否', script_template: '' }
  dialogVisible.value = true
}

const handleSave = async () => {
  try {
    if (form.value.id) { await leadsApi.update(form.value.id, form.value) }
    else { await leadsApi.create(form.value) }
    ElMessage.success('保存成功'); dialogVisible.value = false; loadList()
  } catch (e) { ElMessage.error('保存失败') }
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' })
  await leadsApi.delete(id); ElMessage.success('删除成功'); loadList()
}

onMounted(loadList)
</script>
