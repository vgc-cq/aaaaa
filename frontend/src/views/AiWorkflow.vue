<template>
  <div>
    <el-card>
      <template #header><div style="display:flex;justify-content:space-between;align-items:center"><span style="font-weight:600">AI 工作流 - 商品到脚本的完整流程</span><el-tag type="warning">已接入 DeepSeek：真实大模型模式</el-tag></div></template>

      <!-- 输入表单 -->
      <el-form :model="inputForm" label-width="100px" style="max-width:800px">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="商品名称"><el-input v-model="inputForm.product_name" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="价格区间"><el-input v-model="inputForm.price_range" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="目标用户"><el-input v-model="inputForm.target_users" /></el-form-item>
        <el-form-item label="核心场景"><el-input v-model="inputForm.core_scenes" /></el-form-item>
        <el-form-item label="用户痛点"><el-input v-model="inputForm.user_pain_points" type="textarea" /></el-form-item>
        <el-form-item label="可表达卖点"><el-input v-model="inputForm.selling_points" type="textarea" /></el-form-item>
        <el-form-item>
          <el-button type="primary" @click="runFullWorkflow" :loading="loading" size="large">
            {{ loading ? 'AI 分析中...' : '运行完整工作流' }}
          </el-button>
          <el-button @click="fillSample">填入示例数据</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 步骤进度 -->
    <el-card v-if="result" style="margin-top:20px">
      <template #header><span style="font-weight:600">工作流执行结果</span></template>

      <el-steps :active="activeStep" finish-status="success" style="margin-bottom:20px">
        <el-step title="卖点分析" />
        <el-step title="内容角度" />
        <el-step title="脚本生成" />
        <el-step title="质检报告" />
      </el-steps>

      <!-- 摘要 -->
      <el-descriptions v-if="result.summary" :column="4" border style="margin-bottom:20px">
        <el-descriptions-item label="核心卖点">{{ result.summary.selling_points?.join('、') }}</el-descriptions-item>
        <el-descriptions-item label="内容角度数">{{ result.summary.content_angles_count }}个</el-descriptions-item>
        <el-descriptions-item label="脚本标题">{{ result.summary.script_title }}</el-descriptions-item>
        <el-descriptions-item label="质检评分">
          <el-tag :type="result.summary.quality_score >= 80 ? 'success' : 'warning'">{{ result.summary.quality_score }}分</el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <!-- 各步骤详情 -->
      <div style="margin-bottom:16px"><el-button type="success" :disabled="!result" @click="saveWorkflowResult">保存结果到业务表</el-button><el-button :disabled="!result" @click="clearWorkflowCache">清空当前结果</el-button><span style="margin-left:10px;color:#697386;font-size:13px">结果会自动记忆；写回业务表后可长期保存。</span></div>
      <el-collapse v-model="activeCollapse">
        <el-collapse-item title="1. 卖点分析结果" name="step1">
          <pre class="result-block">{{ formatJson(result.steps?.step1_selling_points) }}</pre>
        </el-collapse-item>
        <el-collapse-item title="2. 内容角度" name="step2">
          <pre class="result-block">{{ formatJson(result.steps?.step2_content_angles) }}</pre>
        </el-collapse-item>
        <el-collapse-item title="3. 脚本分镜" name="step3">
          <pre class="result-block">{{ formatJson(result.steps?.step3_script) }}</pre>
        </el-collapse-item>
        <el-collapse-item title="4. 质检报告" name="step4">
          <pre class="result-block">{{ formatJson(result.steps?.step4_quality_check) }}</pre>
        </el-collapse-item>
      </el-collapse>
    </el-card>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { aiApi } from '../api'
import { ElMessage } from 'element-plus'

const inputForm = ref({
  product_name: '便携式无线榨汁杯',
  price_range: '79-129元',
  target_users: '上班族、学生、宝妈、健身人群',
  core_scenes: '早餐、办公室下午茶、宿舍饮品、健身后补充',
  user_pain_points: '外卖饮品价格高含糖高；早上时间紧；传统榨汁机清洗麻烦',
  selling_points: '便携、无线、易清洗、制作快、容量适中',
})

const loading = ref(false)
const result = ref(null)
const activeStep = ref(0)
const activeCollapse = ref([])

const CACHE_KEY = 'ecommerce_ai_workflow_cache'
const saveCache = () => {
  localStorage.setItem(CACHE_KEY, JSON.stringify({
    inputForm: inputForm.value,
    result: result.value,
    activeStep: activeStep.value,
    activeCollapse: activeCollapse.value,
    savedAt: new Date().toISOString(),
  }))
}

const restoreCache = () => {
  try {
    const cache = JSON.parse(localStorage.getItem(CACHE_KEY) || '{}')
    if (cache.inputForm) inputForm.value = cache.inputForm
    if (cache.result) result.value = cache.result
    if (cache.activeStep !== undefined) activeStep.value = cache.activeStep
    if (cache.activeCollapse) activeCollapse.value = cache.activeCollapse
  } catch (e) {
    localStorage.removeItem(CACHE_KEY)
  }
}

const clearWorkflowCache = () => {
  result.value = null
  activeStep.value = 0
  activeCollapse.value = []
  localStorage.removeItem(CACHE_KEY)
  ElMessage.success('已清空当前工作流结果')
}

onMounted(restoreCache)
watch([inputForm, result, activeStep, activeCollapse], saveCache, { deep: true })

const fillSample = () => {
  inputForm.value = {
    product_name: '便携式无线榨汁杯',
    price_range: '79-129元',
    target_users: '上班族、学生、宝妈、健身人群',
    core_scenes: '早餐、办公室下午茶、宿舍饮品、健身后补充',
    user_pain_points: '外卖饮品价格高含糖高；早上时间紧；传统榨汁机清洗麻烦；宿舍/办公室空间有限',
    selling_points: '便携、无线、易清洗、制作快、容量适中(300ml)、USB充电、食品级材质',
  }
}

const saveWorkflowResult = async () => {
  if (!result.value) return
  try {
    const res = await aiApi.saveResult(result.value)
    ElMessage.success(`写回成功：生成 ${res.data.script_count} 条分镜`)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '写回失败，请检查后端')
  }
}

const runFullWorkflow = async () => {
  loading.value = true
  activeStep.value = 0
  try {
    const res = await aiApi.fullWorkflow(inputForm.value)
    result.value = res.data
    activeStep.value = 4
    activeCollapse.value = ['step1', 'step2', 'step3', 'step4']
    saveCache()
    saveCache()
    ElMessage.success('工作流执行完成')
  } catch (e) {
    ElMessage.error('工作流执行失败：' + (e.message || '请检查 API 配置'))
  } finally {
    loading.value = false
  }
}

const formatJson = (obj) => {
  if (!obj) return '暂无数据'
  return JSON.stringify(obj, null, 2)
}
</script>

<style scoped>
.result-block {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.6;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>





