<template>
  <el-container class="app-shell">
    <el-aside width="244px" class="app-aside">
      <div class="brand-card">
        <div class="brand-mark">电</div>
        <div>
          <h2>电商增长舱</h2>
          <p>Short Video Ops</p>
        </div>
      </div>
      <el-menu :default-active="currentRoute" router class="nav-menu">
        <el-menu-item index="/"><el-icon><DataBoard /></el-icon><span>仪表盘</span></el-menu-item>
        <el-menu-item index="/products"><el-icon><ShoppingCart /></el-icon><span>商品库</span></el-menu-item>
        <el-menu-item index="/contents"><el-icon><Document /></el-icon><span>内容拆解</span></el-menu-item>
        <el-menu-item index="/scripts"><el-icon><Film /></el-icon><span>脚本分镜</span></el-menu-item>
        <el-menu-item index="/videos"><el-icon><VideoCamera /></el-icon><span>视频任务</span></el-menu-item>
        <el-menu-item index="/ads"><el-icon><TrendCharts /></el-icon><span>投流数据</span></el-menu-item>
        <el-menu-item index="/leads"><el-icon><User /></el-icon><span>私域线索</span></el-menu-item>
        <el-menu-item index="/reviews"><el-icon><DataAnalysis /></el-icon><span>数据复盘</span></el-menu-item>
        <el-menu-item index="/knowledge"><el-icon><Collection /></el-icon><span>知识库</span></el-menu-item>
        <el-menu-item index="/ai-workflow"><el-icon><MagicStick /></el-icon><span>AI工作流</span></el-menu-item>
        <el-menu-item index="/agent"><el-icon><Avatar /></el-icon><span>智能体</span></el-menu-item>
      </el-menu>
    </el-aside>
    <el-container class="content-shell">
      <el-header class="app-header">
        <div>
          <div class="eyebrow">短视频电商 AI 提效原型</div>
          <h1>{{ currentTitle }}</h1>
        </div>
        <el-button type="primary" class="export-btn" @click="exportData"><el-icon><Download /></el-icon> 导出 Excel</el-button>
      </el-header>
      <el-main class="app-main">
        <router-view v-slot="{ Component }">
          <keep-alive>
            <component :is="Component" />
          </keep-alive>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { exportApi } from './api'
import { ElMessage } from 'element-plus'

const route = useRoute()
const currentRoute = computed(() => route.path)
const currentTitle = computed(() => route.meta.title || '仪表盘')

const exportData = async () => {
  try {
    const res = await exportApi.all()
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = 'ecommerce_data.xlsx'
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败，请检查后端是否已启动')
  }
}
</script>

<style>
:root {
  --ink: #14213d;
  --muted: #697386;
  --bg: #eef3f8;
  --panel: rgba(255,255,255,.86);
  --line: rgba(35,52,92,.10);
  --orange: #ff7a1a;
  --blue: #2454ff;
  --cyan: #19c7d4;
  --shadow: 0 18px 48px rgba(32, 49, 88, .12);
  --radius: 18px;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body, #app { height: 100%; font-family: "Microsoft YaHei UI", "Segoe UI", system-ui, sans-serif; color: var(--ink); }
body { background: radial-gradient(circle at 20% 10%, rgba(36,84,255,.16), transparent 28%), radial-gradient(circle at 90% 20%, rgba(255,122,26,.16), transparent 24%), var(--bg); }
.app-shell { height: 100vh; overflow: hidden; }
.app-aside { height: 100vh; position: sticky; top: 0; flex-shrink: 0; padding: 18px 14px; background: linear-gradient(180deg, #101828 0%, #172033 56%, #101828 100%); box-shadow: 12px 0 36px rgba(16, 24, 40, .24); overflow: hidden; }
.brand-card { height: 84px; display: flex; gap: 12px; align-items: center; padding: 16px; border-radius: 22px; color: #fff; background: linear-gradient(135deg, rgba(255,255,255,.14), rgba(255,255,255,.04)); border: 1px solid rgba(255,255,255,.12); margin-bottom: 16px; }
.brand-mark { width: 42px; height: 42px; border-radius: 14px; display:flex;align-items:center;justify-content:center; font-size: 22px; font-weight: 900; background: linear-gradient(135deg, var(--orange), #ffd166); color:#111827; box-shadow: 0 10px 28px rgba(255,122,26,.35); }
.brand-card h2 { font-size: 17px; letter-spacing: .5px; }
.brand-card p { font-size: 11px; opacity: .62; margin-top: 4px; letter-spacing: 1.8px; text-transform: uppercase; }
.nav-menu { height: calc(100vh - 118px); overflow-y: auto; border: 0 !important; background: transparent !important; scrollbar-width: thin; }
.nav-menu .el-menu-item { margin: 6px 0; border-radius: 14px; color: rgba(255,255,255,.72); height: 46px; }
.nav-menu .el-menu-item:hover { background: rgba(255,255,255,.08); color: #fff; }
.nav-menu .el-menu-item.is-active { background: linear-gradient(135deg, rgba(255,122,26,.95), rgba(36,84,255,.9)); color: #fff; box-shadow: 0 12px 26px rgba(36,84,255,.24); }
.content-shell { min-width: 0; height: 100vh; overflow: hidden; }
.app-header { height: 88px; display:flex;align-items:center;justify-content:space-between; padding: 18px 28px; background: rgba(255,255,255,.72); backdrop-filter: blur(16px); border-bottom: 1px solid var(--line); }
.eyebrow { color: var(--muted); font-size: 12px; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 4px; }
.app-header h1 { font-size: 26px; font-weight: 850; letter-spacing: -.5px; }
.export-btn { border: 0; border-radius: 999px; padding: 18px 20px; background: linear-gradient(135deg, var(--blue), var(--cyan)); box-shadow: 0 12px 24px rgba(36,84,255,.22); }
.app-main { height: calc(100vh - 88px); padding: 24px; background: transparent; overflow-y: auto; overflow-x: hidden; }
.el-card { border: 1px solid var(--line) !important; border-radius: var(--radius) !important; background: var(--panel) !important; box-shadow: var(--shadow) !important; backdrop-filter: blur(14px); }
.el-card__header { border-bottom: 1px solid var(--line) !important; font-weight: 700; }
.el-table { border-radius: 14px; overflow: hidden; }
.el-button { border-radius: 12px; }
.el-tag { border-radius: 999px; }
</style>

.nav-menu::-webkit-scrollbar { width: 4px; }
.nav-menu::-webkit-scrollbar-thumb { background: rgba(255,255,255,.18); border-radius: 999px; }
.app-main::-webkit-scrollbar { width: 8px; }
.app-main::-webkit-scrollbar-thumb { background: rgba(20,33,61,.18); border-radius: 999px; }



