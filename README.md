# 短视频电商全栈系统

覆盖选品、内容、脚本、视频、投流、客服、复盘、知识库七大板块的提效原型系统。

## 技术栈

- **后端**：Python + FastAPI + SQLAlchemy + SQLite
- **前端**：Vue 3 + Element Plus + Vite
- **AI**：OpenAI API（支持兼容接口切换）

## 快速启动

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8080
```

访问 http://localhost:8080/docs 查看 API 文档

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000 使用系统

### 3. 配置 AI（可选）

在 backend 目录创建 `.env` 文件：

```
OPENAI_API_KEY=你的DeepSeek API Key
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
```

## 功能模块

| 模块 | 路径 | 说明 |
|------|------|------|
| 仪表盘 | `/` | 数据概览、视频排名、复盘结论 |
| 商品库 | `/products` | 商品信息管理、评分、状态 |
| 内容拆解 | `/contents` | 爆款视频拆解、二创角度 |
| 脚本分镜 | `/scripts` | 秒级脚本、AI提示词 |
| 视频任务 | `/videos` | 视频生产管理、质检 |
| 投流数据 | `/ads` | 千川投流数据、ROI分析 |
| 数据复盘 | `/reviews` | 周期复盘、问题归因 |
| 知识库 | `/knowledge` | 卖点库、提示词库、SOP |
| AI工作流 | `/ai-workflow` | 商品→脚本的完整AI流程 |
| 智能体 | `/agent` | 投流复盘/选品/质检等智能体 |

## API 端点

- 商品：`/api/products/`
- 内容：`/api/contents/`
- 脚本：`/api/scripts/`
- 视频：`/api/videos/`
- 投流：`/api/ads/`
- 复盘：`/api/reviews/`
- 知识库：`/api/knowledge/`
- AI工作流：`/api/ai/workflow/full`
- 智能体：`/api/agents/agents`
- 数据分析：`/api/analysis/dashboard`
- 数据导出：`/api/export/all`

## 项目结构

```
├── backend/           # FastAPI 后端
│   ├── main.py       # 入口
│   ├── models.py     # 8张数据表
│   ├── routers/      # API 路由
│   ├── ai_workflow/  # AI 工作流
│   ├── services/     # 业务逻辑
│   └── data/         # 模拟数据
├── frontend/          # Vue 3 前端
│   └── src/views/    # 11个页面
├── docs/              # 项目文档
│   ├── 流程图.md     # 任务1
│   ├── 数据结构说明.md # 任务2
│   ├── AI工作流说明.md # 任务3
│   ├── 智能体说明.md   # 任务4
│   ├── 复盘分析.md     # 任务5
│   └── SOP.md         # 任务6
└── README.md
```


## 当前说明

- 大模型暂不必接入：未配置 OPENAI_API_KEY 时，AI 工作流和智能体会使用本地规则模拟结果，方便先演示业务闭环。
- 前后端端口已统一：后端 8080，前端 3000。



## DeepSeek 接入说明

后端已兼容 OpenAI 格式接口。配置 ackend/.env 后，AI 工作流和智能体会优先调用 DeepSeek；如果未配置 Key，则自动使用本地模拟结果。

推荐配置：

`env
OPENAI_API_KEY=你的DeepSeek API Key
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
` 

