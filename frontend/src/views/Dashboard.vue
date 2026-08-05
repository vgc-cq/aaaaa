<template>
  <div class="dashboard">
    <section class="hero-panel">
      <div>
        <div class="hero-kicker">AI Commerce War Room</div>
        <h2>从商品到复盘的业务闭环</h2>
        <p>统一查看商品、视频、投流、待办、异常和负责人负载，方便 5-10 分钟演示。</p>
      </div>
      <div class="hero-badge">
        <strong>{{ summary.overall_roi || 0 }}</strong>
        <span>整体 ROI</span>
      </div>
    </section>

    <el-row :gutter="18" class="summary-cards">
      <el-col :span="6"><el-card shadow="never"><div class="stat-card blue"><span>商品数</span><strong>{{ summary.total_products || 0 }}</strong><small>选品池</small></div></el-card></el-col>
      <el-col :span="6"><el-card shadow="never"><div class="stat-card cyan"><span>视频数</span><strong>{{ summary.total_videos || 0 }}</strong><small>生产任务</small></div></el-card></el-col>
      <el-col :span="6"><el-card shadow="never"><div class="stat-card orange"><span>成交额</span><strong>¥{{ summary.total_revenue || 0 }}</strong><small>模拟数据</small></div></el-card></el-col>
      <el-col :span="6"><el-card shadow="never"><div class="stat-card red"><span>高优先级</span><strong>{{ highPriority.length }}</strong><small>P0/异常</small></div></el-card></el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top:20px">
      <el-col :span="14">
        <el-card>
          <template #header><span>视频表现排名（按 ROI）</span></template>
          <el-table :data="videoRanking" stripe size="small">
            <el-table-column prop="video_code" label="视频" width="80" />
            <el-table-column prop="content_direction" label="内容方向" min-width="170" show-overflow-tooltip />
            <el-table-column prop="play_count" label="播放量" width="90" />
            <el-table-column prop="spend" label="消耗" width="80" />
            <el-table-column prop="revenue" label="成交" width="80" />
            <el-table-column prop="roi" label="ROI" width="80">
              <template #default="{ row }"><el-tag :type="row.roi >= 3 ? 'success' : row.roi >= 1.5 ? 'warning' : 'danger'">{{ row.roi }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="cart_clicks" label="加购" width="80" />
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card class="review-card">
          <template #header><span>最新复盘结论</span></template>
          <div v-if="latestReview">
            <div class="review-period">{{ latestReview.review_period }}</div>
            <p><b>问题：</b>{{ latestReview.problem_analysis }}</p>
            <p><b>动作：</b>{{ latestReview.next_action }}</p>
          </div>
          <el-empty v-else description="暂无复盘数据" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top:20px">
      <el-col :span="12">
        <el-card>
          <template #header><span>今日待处理视图</span></template>
          <el-table :data="todayTasks" size="small" height="260">
            <el-table-column prop="priority" label="优先级" width="80"><template #default="{row}"><el-tag :type="row.priority==='P0'?'danger':row.priority==='P1'?'warning':'info'">{{row.priority}}</el-tag></template></el-table-column>
            <el-table-column prop="module" label="模块" width="90" />
            <el-table-column prop="code" label="编号" width="80" />
            <el-table-column prop="title" label="事项" show-overflow-tooltip />
            <el-table-column prop="owner" label="负责人" width="90" />
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header><span>复盘结果 / 高优先级问题</span></template>
          <el-table :data="highPriority" size="small" height="260">
            <el-table-column prop="video_code" label="视频" width="80" />
            <el-table-column prop="content_direction" label="方向" min-width="130" />
            <el-table-column prop="roi" label="ROI" width="70" />
            <el-table-column prop="priority" label="优先级" width="80"><template #default="{row}"><el-tag type="danger">{{row.priority}}</el-tag></template></el-table-column>
            <el-table-column prop="suggestion" label="建议" show-overflow-tooltip />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top:20px">
      <el-col :span="12">
        <el-card>
          <template #header><span>按负责人看板</span></template>
          <div class="kanban-strip">
            <div v-for="(items, owner) in ownerKanban" :key="owner" class="mini-lane">
              <div class="lane-title">{{ owner }} <b>{{ items.length }}</b></div>
              <div v-for="item in items.slice(0,4)" :key="item.module + item.code" class="mini-card">{{ item.module }} · {{ item.code }} <em>{{ item.status }}</em></div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header><span>按状态看板</span></template>
          <div class="kanban-strip">
            <div v-for="(items, status) in statusKanban" :key="status" class="mini-lane">
              <div class="lane-title">{{ status }} <b>{{ items.length }}</b></div>
              <div v-for="item in items.slice(0,4)" :key="item.module + item.code" class="mini-card">{{ item.module }} · {{ item.code }} <em>{{ item.owner || '未分配' }}</em></div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top:20px">
      <template #header><span>自动复盘明细</span></template>
      <el-table :data="videoAnalysis" stripe size="small">
        <el-table-column prop="video_code" label="视频" width="80" />
        <el-table-column prop="content_direction" label="内容方向" width="160" />
        <el-table-column label="核心指标" width="280"><template #default="{ row }">ROI {{ row.metrics?.roi || '-' }}｜加购率 {{ row.metrics?.cart_click_rate || '-' }}%｜完播 {{ row.metrics?.completion_rate || '-' }}%</template></el-table-column>
        <el-table-column label="决策" width="110"><template #default="{ row }"><el-tag :type="getDecisionType(row.decision)">{{ row.decision }}</el-tag></template></el-table-column>
        <el-table-column prop="feedback" label="用户反馈" show-overflow-tooltip />
        <el-table-column prop="suggestion" label="建议" show-overflow-tooltip />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { analysisApi, reviewsApi } from '../api'

const summary = ref({})
const videoRanking = ref([])
const videoAnalysis = ref([])
const latestReview = ref(null)
const todayTasks = ref([])
const highPriority = ref([])
const ownerKanban = ref({})
const statusKanban = ref({})

const getDecisionType = (decision) => decision?.includes('放量') ? 'success' : decision?.includes('停投') ? 'danger' : decision?.includes('优化') ? 'warning' : 'info'

onMounted(async () => {
  const [dashRes, analysisRes, reviewRes, tasksRes, hpRes, ownerRes, statusRes] = await Promise.all([
    analysisApi.dashboard(), analysisApi.allVideos(), reviewsApi.list({ limit: 1 }), analysisApi.todayTasks(), analysisApi.highPriority(), analysisApi.ownerKanban(), analysisApi.statusKanban()
  ])
  summary.value = dashRes.data.summary || {}
  videoRanking.value = dashRes.data.video_ranking || []
  videoAnalysis.value = analysisRes.data || []
  latestReview.value = reviewRes.data?.[0] || null
  todayTasks.value = tasksRes.data || []
  highPriority.value = hpRes.data || []
  ownerKanban.value = ownerRes.data || {}
  statusKanban.value = statusRes.data || {}
})
</script>

<style scoped>
.dashboard { animation: rise .45s ease both; }
.hero-panel { position: relative; overflow: hidden; display:flex; justify-content:space-between; align-items:center; min-height: 168px; padding: 30px; border-radius: 28px; color: #fff; background: linear-gradient(135deg, #111827 0%, #1d2b53 48%, #ff7a1a 140%); box-shadow: 0 24px 60px rgba(17,24,39,.24); }
.hero-panel:after { content:""; position:absolute; right:160px; top:-70px; width:260px; height:260px; border-radius:50%; background: radial-gradient(circle, rgba(25,199,212,.34), transparent 62%); }
.hero-kicker { font-size: 12px; letter-spacing: 2px; opacity: .72; text-transform: uppercase; }
.hero-panel h2 { font-size: 34px; margin: 8px 0; letter-spacing: -1px; }
.hero-panel p { max-width: 620px; opacity: .76; }
.hero-badge { z-index:1; width: 128px; height:128px; border-radius: 32px; display:flex; flex-direction:column; align-items:center; justify-content:center; background: rgba(255,255,255,.13); border: 1px solid rgba(255,255,255,.2); backdrop-filter: blur(16px); }
.hero-badge strong { font-size: 36px; }
.hero-badge span { opacity:.74; font-size:12px; }
.summary-cards { margin-top: 20px; }
.stat-card { min-height: 112px; padding: 4px; display:flex; flex-direction:column; gap: 6px; }
.stat-card span { color:#697386; font-size:13px; }
.stat-card strong { font-size: 30px; line-height:1; }
.stat-card small { color:#8a94a6; }
.stat-card:before { content:""; width: 38px; height: 5px; border-radius: 999px; margin-bottom: 8px; }
.stat-card.blue:before { background:#2454ff; }.stat-card.cyan:before { background:#19c7d4; }.stat-card.orange:before { background:#ff7a1a; }.stat-card.red:before { background:#f56c6c; }
.review-period { display:inline-block; padding: 6px 12px; border-radius: 999px; color:#fff; background: linear-gradient(135deg,#2454ff,#19c7d4); margin-bottom: 12px; }
.review-card p { line-height: 1.75; margin: 8px 0; color:#334155; }
.kanban-strip { display:flex; gap:12px; overflow-x:auto; padding-bottom: 4px; min-height: 260px; }
.mini-lane { flex: 0 0 170px; border-radius: 16px; background: #f6f8fb; border:1px solid rgba(20,33,61,.08); padding: 12px; }
.lane-title { display:flex; justify-content:space-between; font-weight:700; margin-bottom:10px; }
.lane-title b { color:#ff7a1a; }
.mini-card { background:#fff; border-radius:12px; padding:10px; margin-bottom:8px; box-shadow:0 8px 18px rgba(20,33,61,.06); font-size:12px; }
.mini-card em { display:block; margin-top:5px; color:#697386; font-style:normal; }
@keyframes rise { from { opacity:0; transform: translateY(12px); } to { opacity:1; transform: none; } }
</style>
