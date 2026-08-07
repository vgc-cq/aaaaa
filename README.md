# 短视频电商全栈系统

覆盖选品、内容、脚本、视频、投流、复盘、知识库七大业务板块的短视频电商 AI 提效原型系统。

## 技术栈

- **后端**：Python + FastAPI + SQLAlchemy + SQLite
- **前端**：Vue 3 + Element Plus + Vite
- **AI**：DeepSeek（文本分析）、Qwen-VL-Max（视频/图片理解）、通义万相 Wan2.7（文生视频）

## 快速启动

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
python main.py        # 或 uvicorn main:app --reload --port 8080
```

访问 http://localhost:8080/docs 查看 API 文档

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000 使用系统

### 3. 配置 AI Key（可选）

在 backend 目录创建 `.env` 文件（可参考 `.env.example`）：

```
OPENAI_API_KEY=你的DeepSeek API Key
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat

QWEN_VL_API_KEY=你的DashScope(通义千问) API Key
WAN_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
WAN_VIDEO_MODEL=wan2.7-t2v
```

未配置 Key 时，相关 AI 功能会自动降级为本地演示，保证流程可跑通。

## 功能模块

| 模块 | 路径 | 说明 |
|------|------|------|
| 仪表盘 | `/` | 数据概览、视频排名、今日待处理、看板 |
| 商品库 | `/products` | 商品管理、Excel 一键导入、AI 选品评分、勾选批量删除 |
| 内容拆解 | `/contents` | 爆款视频/图片/文字拆解（Qwen-VL + DeepSeek 拆 7 类要点）、关联商品 |
| 脚本分镜 | `/scripts` | 关联商品与拆解，DeepSeek 生成 20 秒内秒级分镜，分组展示、审核 |
| 视频任务 | `/videos` | 通义万相 Wan2.7 文生视频、进度查询、质检、发布平台跳转 |
| 投流数据 | `/ads` | 千川投流数据、Excel 一键导入、ROI/异常分析、导入后自动复盘 |
| 数据复盘 | `/reviews` | LangGraph 五节点复盘智能体、节点卡片实时展示、认可沉淀知识库 |
| 知识库 | `/knowledge` | 卖点库、内容库、脚本库、提示词库、复盘经验、SOP |

## 数据复盘智能体（LangGraph）

数据复盘页面内置基于 **LangGraph** 的五节点智能体：

```
读取数据 → 指标计算 → AI 复盘 → 写回建议 → 记录日志
```

- **自动触发**：新增/导入投流数据后自动复盘，后台另有定时巡检（`REVIEW_INTERVAL_MINUTES` 控制）
- **AI 复盘**：DeepSeek 生成评级、决策、问题与优化建议，自带自检评分（低于 60 分重试）
- **节点卡片**：前端流式接收每个节点的真实输出，逐张点亮，运行过程可见
- **经验沉淀**：在复盘记录中把状态标记为"认可"，结论自动沉淀为知识库"已生效"知识，并在下次复盘生成时自动参考；标记"不认可"则写入记忆避免类似输出

## API 端点

- 商品：`/api/products/`
- 内容：`/api/contents/`
- 脚本：`/api/scripts/`
- 视频：`/api/videos/`
- 投流：`/api/ads/`
- 复盘：`/api/reviews/`
- 复盘智能体：`/api/review-agent/run`（一键）、`/api/review-agent/run/stream`（流式）、`/api/review-agent/logs`
- 视觉拆解：`/api/ai/vision/content_breakdown`、`/api/ai/vision/upload`
- 知识库：`/api/knowledge/`
- 数据分析：`/api/analysis/dashboard`
- 数据导出：`/api/export/all`

## 项目结构

```
├── backend/           # FastAPI 后端
│   ├── main.py       # 入口
│   ├── models.py     # 9 张数据表
│   ├── routers/      # API 路由
│   ├── ai_workflow/  # 复盘智能体(LangGraph) / 视觉拆解 / 共享AI调用
│   ├── services/     # 业务逻辑
│   └── data/         # 模拟数据
├── frontend/          # Vue 3 前端
│   └── src/views/    # 8 个功能页面
├── docs/              # 项目文档
│   ├── 流程图.md      # 任务1
│   ├── 数据结构说明.md # 任务2
│   ├── 复盘分析.md    # 任务5
│   └── SOP.md         # 任务6
└── README.md
```
