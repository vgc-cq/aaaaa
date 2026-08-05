<template>
  <div>
    <el-card>
      <template #header><div style="display:flex;justify-content:space-between;align-items:center"><span style="font-weight:600">智能体 / 数字员工雏形</span><el-button size="small" @click="clearAgentCache">清空智能体缓存</el-button></div></template>

      <el-tabs v-model="activeTab">
        <!-- 投流复盘助手 -->
        <el-tab-pane label="投流复盘助手" name="adReview">
          <el-form :model="adForm" label-width="120px" style="max-width:700px">
            <el-divider content-position="left">视频数据</el-divider>
            <el-row :gutter="16">
              <el-col :span="12"><el-form-item label="视频编号"><el-input v-model="adForm.video_data.video_code" /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="内容方向"><el-input v-model="adForm.video_data.content_direction" /></el-form-item></el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="8"><el-form-item label="播放量"><el-input-number v-model="adForm.video_data.play_count" :min="0" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="2秒跳出率"><el-input v-model="adForm.video_data.bounce_rate_2s" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="完播率"><el-input v-model="adForm.video_data.completion_rate" /></el-form-item></el-col>
            </el-row>
            <el-divider content-position="left">投流数据</el-divider>
            <el-row :gutter="16">
              <el-col :span="6"><el-form-item label="消耗"><el-input-number v-model="adForm.ad_data.spend" :min="0" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="购物车点击"><el-input-number v-model="adForm.ad_data.cart_clicks" :min="0" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="成交金额"><el-input-number v-model="adForm.ad_data.revenue" :min="0" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="订单数"><el-input-number v-model="adForm.ad_data.orders" :min="0" /></el-form-item></el-col>
            </el-row>
            <el-form-item label="用户反馈"><el-input v-model="adForm.feedback" /></el-form-item>
            <el-form-item>
              <el-button type="primary" @click="runAdReview" :loading="adLoading">运行复盘分析</el-button>
              <el-button @click="fillAdSample">填入V001示例</el-button>
            </el-form-item>
          </el-form>
          <pre v-if="adResult" class="result-block">{{ formatJson(adResult) }}</pre>
        </el-tab-pane>

        <!-- 选品分析助手 -->
        <el-tab-pane label="选品分析助手" name="productAnalysis">
          <el-form :model="productForm" label-width="100px" style="max-width:600px">
            <el-form-item label="商品名称"><el-input v-model="productForm.product_name" /></el-form-item>
            <el-row :gutter="16">
              <el-col :span="12"><el-form-item label="价格"><el-input v-model="productForm.price" /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="类目"><el-input v-model="productForm.category" /></el-form-item></el-col>
            </el-row>
            <el-form-item label="销量/热度"><el-input v-model="productForm.sales" /></el-form-item>
            <el-form-item label="口碑评价"><el-input v-model="productForm.reviews" /></el-form-item>
            <el-form-item>
              <el-button type="primary" @click="runProductAnalysis" :loading="productLoading">运行选品分析</el-button>
            </el-form-item>
          </el-form>
          <pre v-if="productResult" class="result-block">{{ formatJson(productResult) }}</pre>
        </el-tab-pane>

        <!-- 客服话术助手 -->
        <el-tab-pane label="客服话术助手" name="customerService">
          <el-form :model="csForm" label-width="100px" style="max-width:600px">
            <el-form-item label="用户咨询"><el-input v-model="csForm.inquiry" type="textarea" :rows="3" /></el-form-item>
            <el-form-item label="商品信息"><el-input v-model="csForm.product_info" type="textarea" :rows="2" /></el-form-item>
            <el-form-item>
              <el-button type="primary" @click="runCustomerService" :loading="csLoading">生成话术</el-button>
              <el-button @click="csForm = { inquiry: '这个榨汁杯清洗方便吗？会不会有残留？', product_info: '便携式无线榨汁杯，79-129元，一键清洗功能' }">示例</el-button>
            </el-form-item>
          </el-form>
          <pre v-if="csResult" class="result-block">{{ formatJson(csResult) }}</pre>
        </el-tab-pane>


        <!-- 脚本生成助手 -->
        <el-tab-pane label="脚本生成助手" name="scriptGen">
          <el-form :model="scriptForm" label-width="100px" style="max-width:600px">
            <el-form-item label="商品名称"><el-input v-model="scriptForm.product_name" /></el-form-item>
            <el-form-item label="目标人群"><el-input v-model="scriptForm.target_users" /></el-form-item>
            <el-form-item label="使用场景"><el-input v-model="scriptForm.scene" /></el-form-item>
            <el-form-item label="视频时长"><el-input-number v-model="scriptForm.duration" :min="15" :max="60" /></el-form-item>
            <el-form-item>
              <el-button type="primary" @click="runScriptGen" :loading="scriptLoading">生成脚本</el-button>
            </el-form-item>
          </el-form>
          <pre v-if="scriptResult" class="result-block">{{ formatJson(scriptResult) }}</pre>
        </el-tab-pane>
        <!-- 视频质检助手 -->
        <el-tab-pane label="视频质检助手" name="videoQa">
          <el-form :model="qaForm" label-width="100px" style="max-width:600px">
            <el-form-item label="脚本内容"><el-input v-model="qaForm.script_content" type="textarea" :rows="6" /></el-form-item>
            <el-form-item>
              <el-button type="primary" @click="runVideoQa" :loading="qaLoading">运行质检</el-button>
            </el-form-item>
          </el-form>
          <pre v-if="qaResult" class="result-block">{{ formatJson(qaResult) }}</pre>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { agentsApi } from '../api'
import { ElMessage } from 'element-plus'

const activeTab = ref('adReview')

// 投流复盘
const adForm = ref({
  video_data: { video_code: 'V001', content_direction: '上班族40秒早餐果汁', play_count: 12000, bounce_rate_2s: '38%', completion_rate_5s: '22%', completion_rate: '15%' },
  ad_data: { spend: 300, cart_clicks: 90, revenue: 712, orders: 8 },
  feedback: '评论集中问"清洗麻烦吗？"',
})
const adLoading = ref(false)
const adResult = ref(null)

const fillAdSample = () => {
  adForm.value = {
    video_data: { video_code: 'V001', content_direction: '上班族40秒早餐果汁', play_count: 12000, bounce_rate_2s: '38%', completion_rate_5s: '22%', completion_rate: '15%' },
    ad_data: { spend: 300, cart_clicks: 90, revenue: 712, orders: 8 },
    feedback: '评论集中问"清洗麻烦吗？"',
  }
}

const runAdReview = async () => {
  adLoading.value = true
  try {
    const res = await agentsApi.adReview(adForm.value)
    adResult.value = res.data
    saveAgentCache()
    ElMessage.success('复盘分析完成')
  } catch (e) { ElMessage.error('分析失败') }
  finally { adLoading.value = false }
}

// 选品分析
const productForm = ref({ product_name: '便携式无线榨汁杯', price: '79-129元', category: '厨房小家电', sales: '月销5000+', reviews: '4.8分/好评率96%' })
const productLoading = ref(false)
const productResult = ref(null)

const runProductAnalysis = async () => {
  productLoading.value = true
  try {
    const res = await agentsApi.productAnalysis(productForm.value)
    productResult.value = res.data
    saveAgentCache()
    ElMessage.success('选品分析完成')
  } catch (e) { ElMessage.error('分析失败') }
  finally { productLoading.value = false }
}


// 脚本生成
const scriptForm = ref({ product_name: '便携式无线榨汁杯', target_users: '上班族', scene: '早餐', duration: 30 })
const scriptLoading = ref(false)
const scriptResult = ref(null)
const runScriptGen = async () => {
  scriptLoading.value = true
  try {
    const res = await agentsApi.scriptGen(scriptForm.value)
    scriptResult.value = res.data
    saveAgentCache()
    ElMessage.success('脚本生成完成')
  } catch (e) { ElMessage.error('生成失败') }
  finally { scriptLoading.value = false }
}
// 客服话术
const csForm = ref({ inquiry: '这个榨汁杯清洗方便吗？会不会有残留？', product_info: '便携式无线榨汁杯，79-129元，一键清洗功能' })
const csLoading = ref(false)
const csResult = ref(null)

const runCustomerService = async () => {
  csLoading.value = true
  try {
    const res = await agentsApi.customerService(csForm.value)
    csResult.value = res.data
    saveAgentCache()
    ElMessage.success('话术生成完成')
  } catch (e) { ElMessage.error('生成失败') }
  finally { csLoading.value = false }
}

// 视频质检
const qaForm = ref({ script_content: '' })
const qaLoading = ref(false)
const qaResult = ref(null)

const runVideoQa = async () => {
  qaLoading.value = true
  try {
    const res = await agentsApi.videoQa(qaForm.value)
    qaResult.value = res.data
    saveAgentCache()
    ElMessage.success('质检完成')
  } catch (e) { ElMessage.error('质检失败') }
  finally { qaLoading.value = false }
}


const AGENT_CACHE_KEY = 'ecommerce_agent_cache'
const saveAgentCache = () => {
  localStorage.setItem(AGENT_CACHE_KEY, JSON.stringify({
    activeTab: activeTab.value,
    adForm: adForm.value,
    adResult: adResult.value,
    productForm: productForm.value,
    productResult: productResult.value,
    scriptForm: scriptForm.value,
    scriptResult: scriptResult.value,
    csForm: csForm.value,
    csResult: csResult.value,
    qaForm: qaForm.value,
    qaResult: qaResult.value,
    savedAt: new Date().toISOString(),
  }))
}

const restoreAgentCache = () => {
  try {
    const cache = JSON.parse(localStorage.getItem(AGENT_CACHE_KEY) || '{}')
    if (cache.activeTab) activeTab.value = cache.activeTab
    if (cache.adForm) adForm.value = cache.adForm
    if (cache.adResult) adResult.value = cache.adResult
    if (cache.productForm) productForm.value = cache.productForm
    if (cache.productResult) productResult.value = cache.productResult
    if (cache.scriptForm) scriptForm.value = cache.scriptForm
    if (cache.scriptResult) scriptResult.value = cache.scriptResult
    if (cache.csForm) csForm.value = cache.csForm
    if (cache.csResult) csResult.value = cache.csResult
    if (cache.qaForm) qaForm.value = cache.qaForm
    if (cache.qaResult) qaResult.value = cache.qaResult
  } catch (e) {
    localStorage.removeItem(AGENT_CACHE_KEY)
  }
}

const clearAgentCache = () => {
  adResult.value = null
  productResult.value = null
  scriptResult.value = null
  csResult.value = null
  qaResult.value = null
  localStorage.removeItem(AGENT_CACHE_KEY)
  ElMessage.success('已清空智能体运行结果')
}

onMounted(restoreAgentCache)
watch([activeTab, adForm, adResult, productForm, productResult, scriptForm, scriptResult, csForm, csResult, qaForm, qaResult], saveAgentCache, { deep: true })
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
  margin-top: 16px;
  overflow-x: auto;
  white-space: pre-wrap;
}
</style>


