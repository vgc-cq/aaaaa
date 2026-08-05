<template>
  <div>
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="font-weight:600">投流数据表</span>
          <el-button type="primary" @click="showDialog()">新增数据</el-button>
        </div>
      </template>
      <el-table :data="list" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="plan_name" label="计划名称" width="180" />
        <el-table-column prop="content_direction" label="内容方向" width="150" show-overflow-tooltip />
        <el-table-column prop="play_count" label="播放量" width="90" />
        <el-table-column prop="bounce_rate_2s" label="2秒跳出" width="90" />
        <el-table-column prop="completion_rate" label="完播率" width="80" />
        <el-table-column prop="spend" label="消耗(元)" width="90" />
        <el-table-column prop="impressions" label="展现" width="80" />
        <el-table-column prop="clicks" label="点击" width="70" />
        <el-table-column prop="ctr" label="CTR(%)" width="80" />
        <el-table-column prop="cart_clicks" label="购物车点击" width="100" />
        <el-table-column prop="revenue" label="成交(元)" width="90" />
        <el-table-column prop="orders" label="订单数" width="80" />
        <el-table-column prop="roi" label="ROI" width="80">
          <template #default="{ row }">
            <el-tag :type="row.roi >= 3 ? 'success' : row.roi >= 1 ? 'warning' : 'danger'" size="small">{{ row.roi }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="anomaly" label="异常" width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.anomaly" style="color:#f56c6c">{{ row.anomaly }}</span>
            <span v-else style="color:#67c23a">正常</span>
          </template>
        </el-table-column>
        <el-table-column prop="feedback" label="用户反馈" width="150" show-overflow-tooltip />
        <el-table-column prop="review_suggestion" label="复盘建议" show-overflow-tooltip />
        <el-table-column prop="priority" label="优先级" width="80"><template #default="{ row }"><el-tag :type="row.priority === 'P0' ? 'danger' : row.priority === 'P1' ? 'warning' : 'info'" size="small">{{ row.priority }}</el-tag></template></el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showDialog(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑投流数据' : '新增投流数据'" width="600px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="关联视频ID"><el-input-number v-model="form.video_id" :min="1" /></el-form-item>
        <el-form-item label="计划名称"><el-input v-model="form.plan_name" /></el-form-item>
        <el-row :gutter="16"><el-col :span="12"><el-form-item label="内容方向"><el-input v-model="form.content_direction" /></el-form-item></el-col><el-col :span="12"><el-form-item label="负责人"><el-input v-model="form.owner" /></el-form-item></el-col></el-row>
        <el-row :gutter="16"><el-col :span="12"><el-form-item label="状态"><el-input v-model="form.status" /></el-form-item></el-col><el-col :span="12"><el-form-item label="优先级"><el-select v-model="form.priority"><el-option label="P0" value="P0"/><el-option label="P1" value="P1"/><el-option label="P2" value="P2"/></el-select></el-form-item></el-col></el-row>
        <el-row :gutter="16"><el-col :span="12"><el-form-item label="播放量"><el-input-number v-model="form.play_count" :min="0" /></el-form-item></el-col><el-col :span="12"><el-form-item label="2秒跳出率"><el-input-number v-model="form.bounce_rate_2s" :min="0" :max="100" /></el-form-item></el-col></el-row>
        <el-row :gutter="16"><el-col :span="12"><el-form-item label="5秒完播率"><el-input-number v-model="form.completion_rate_5s" :min="0" :max="100" /></el-form-item></el-col><el-col :span="12"><el-form-item label="完播率"><el-input-number v-model="form.completion_rate" :min="0" :max="100" /></el-form-item></el-col></el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="消耗(元)"><el-input-number v-model="form.spend" :min="0" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="展现"><el-input-number v-model="form.impressions" :min="0" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="点击"><el-input-number v-model="form.clicks" :min="0" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="购物车点击"><el-input-number v-model="form.cart_clicks" :min="0" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="成交金额"><el-input-number v-model="form.revenue" :min="0" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="订单数"><el-input-number v-model="form.orders" :min="0" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="异常判断"><el-input v-model="form.anomaly" /></el-form-item>
        <el-form-item label="用户反馈"><el-input v-model="form.feedback" type="textarea" /></el-form-item>
        <el-form-item label="复盘建议"><el-input v-model="form.review_suggestion" type="textarea" /></el-form-item>
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
import { adsApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const list = ref([])
const dialogVisible = ref(false)
const form = ref({})

const loadList = async () => {
  const res = await adsApi.list()
  list.value = res.data
}

const showDialog = (row) => {
  form.value = row ? { ...row } : { video_id: 1, plan_name: '', content_direction: '', play_count: 0, bounce_rate_2s: 0, completion_rate_5s: 0, completion_rate: 0, spend: 0, impressions: 0, clicks: 0, cart_clicks: 0, revenue: 0, orders: 0, anomaly: '', review_suggestion: '', feedback: '', owner: '', status: '投放中', priority: 'P1' }
  dialogVisible.value = true
}

const handleSave = async () => {
  try {
    if (form.value.id) { await adsApi.update(form.value.id, form.value) }
    else { await adsApi.create(form.value) }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    loadList()
  } catch (e) { ElMessage.error('保存失败') }
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' })
  await adsApi.delete(id)
  ElMessage.success('删除成功')
  loadList()
}

onMounted(loadList)
</script>

