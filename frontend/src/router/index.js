import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '仪表盘' } },
  { path: '/products', name: 'Products', component: () => import('../views/Products.vue'), meta: { title: '商品库' } },
  { path: '/contents', name: 'Contents', component: () => import('../views/Contents.vue'), meta: { title: '内容拆解' } },
  { path: '/scripts', name: 'Scripts', component: () => import('../views/Scripts.vue'), meta: { title: '脚本分镜' } },
  { path: '/videos', name: 'Videos', component: () => import('../views/Videos.vue'), meta: { title: '视频任务' } },
  { path: '/ads', name: 'Ads', component: () => import('../views/Ads.vue'), meta: { title: '投流数据' } },
  { path: '/reviews', name: 'Reviews', component: () => import('../views/Reviews.vue'), meta: { title: '数据复盘' } },
  { path: '/knowledge', name: 'Knowledge', component: () => import('../views/Knowledge.vue'), meta: { title: '知识库' } },
  { path: '/ai-workflow', name: 'AiWorkflow', component: () => import('../views/AiWorkflow.vue'), meta: { title: 'AI工作流' } },
  { path: '/agent', name: 'Agent', component: () => import('../views/Agent.vue'), meta: { title: '智能体' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
