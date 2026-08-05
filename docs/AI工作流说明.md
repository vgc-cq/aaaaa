# 任务3：AI 工作流搭建说明

## 一、工作流概览

```
输入商品信息 → [Step1] 提取卖点/人群/痛点
                    ↓
              [Step2] 生成3个内容角度
                    ↓
              [Step3] 选择1个角度生成短视频脚本
                    ↓
              [Step4] 拆成秒级分镜
                    ↓
              输出：视频生成提示词 / 剪辑注意事项 / 发布标题
```

## 二、流程节点说明

### Step 1：卖点分析

| 项目 | 说明 |
|------|------|
| **输入** | 商品名称、价格区间、目标用户、核心场景、用户痛点、可表达卖点 |
| **AI模型** | GPT-4o-mini |
| **提示词** | 系统提示："你是一位资深短视频电商选品专家" |
| **输出** | JSON格式：core_selling_points, target_user_tags, pain_point_mapping, risk_warnings |
| **变量** | product_name, price_range, target_users, core_scenes, user_pain_points, selling_points |
| **失败处理** | 返回fallback标记，使用原始卖点作为兜底 |
| **人工审核** | 卖点列表需人工确认后再进入下一步 |

### Step 2：内容角度生成

| 项目 | 说明 |
|------|------|
| **输入** | 商品名称 + Step1的卖点分析结果 |
| **AI模型** | GPT-4o-mini |
| **提示词** | 系统提示："你是一位短视频内容策划专家" |
| **输出** | 3个角度，每个含：angle_id, title, hook, target_emotion, scene, structure, conversion_point |
| **变量** | product_name, selling_points, target_user_tags, pain_points |
| **失败处理** | 返回fallback标记，使用预设模板角度 |
| **人工审核** | 选择最优角度进入脚本生成 |

### Step 3：脚本生成

| 项目 | 说明 |
|------|------|
| **输入** | 商品信息 + 选定的内容角度 + 视频时长 |
| **AI模型** | GPT-4o-mini |
| **提示词** | 系统提示："你是一位短视频脚本创作专家" |
| **输出** | JSON格式：script_title, total_duration, scenes[], publish_title, tags[], quality_checklist[] |
| **每个scene包含** | time_range, scene_desc, voiceover, subtitle, camera_move, material_req, ai_prompt |
| **失败处理** | 返回fallback标记 |
| **人工审核** | 脚本内容必须人工审核后才能进入视频制作 |

### Step 4：质检报告

| 项目 | 说明 |
|------|------|
| **输入** | Step3生成的完整脚本 |
| **AI模型** | GPT-4o-mini |
| **提示词** | 系统提示："你是一位短视频质检专家" |
| **质检维度** | 钩子力、节奏感、卖点传达、合规性、字幕规范、转化引导 |
| **输出** | overall_score, dimensions{score+comment}, issues[], suggestions[], pass(boolean) |
| **失败处理** | 返回"需人工质检"标记 |

## 三、API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/ai/workflow/step1_selling_points` | POST | 单步：卖点分析 |
| `/api/ai/workflow/step2_content_angles` | POST | 单步：内容角度 |
| `/api/ai/workflow/step3_script_generation` | POST | 单步：脚本生成 |
| `/api/ai/workflow/step4_quality_check` | POST | 单步：质检报告 |
| `/api/ai/workflow/full` | POST | 完整工作流（4步串联） |

## 四、完整工作流调用示例

```json
POST /api/ai/workflow/full
{
    "product_name": "便携式无线榨汁杯",
    "price_range": "79-129元",
    "target_users": "上班族、学生、宝妈、健身人群",
    "core_scenes": "早餐、办公室下午茶、宿舍饮品、健身后补充",
    "user_pain_points": "外卖饮品价格高含糖高；早上时间紧；传统榨汁机清洗麻烦",
    "selling_points": "便携、无线、易清洗、制作快、容量适中"
}
```

## 五、返回结果结构

```json
{
    "status": "completed",
    "input": { ... },
    "steps": {
        "step1_selling_points": {
            "core_selling_points": ["卖点1", "卖点2", "卖点3"],
            "target_user_tags": ["上班族", "学生"],
            "pain_point_mapping": { "痛点": "解决方案" },
            "risk_warnings": ["风险提示"]
        },
        "step2_content_angles": {
            "angles": [
                { "angle_id": 1, "title": "...", "hook": "...", "scene": "...", "structure": "..." }
            ]
        },
        "step3_script": {
            "script_title": "...",
            "scenes": [
                { "time_range": "0-3秒", "scene_desc": "...", "voiceover": "...", "ai_prompt": "..." }
            ],
            "publish_title": "...",
            "tags": ["标签1", "标签2"]
        },
        "step4_quality_check": {
            "overall_score": 85,
            "dimensions": { ... },
            "pass": true
        }
    },
    "summary": {
        "selling_points": [...],
        "content_angles_count": 3,
        "script_title": "...",
        "quality_score": 85
    }
}
```

## 六、环境配置

在 `.env` 或环境变量中配置：

```
OPENAI_API_KEY=sk-your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

支持通过修改 `OPENAI_BASE_URL` 接入兼容 OpenAI API 的其他服务。


## 七、本地模拟演示模式

当前版本支持不配置大模型 Key 直接演示：系统会基于商品字段生成卖点、内容角度、秒级分镜、提示词和质检清单，并支持一键写回内容拆解表、脚本分镜表和知识库。后续只需配置 OPENAI_API_KEY 即可替换为真实大模型调用。

