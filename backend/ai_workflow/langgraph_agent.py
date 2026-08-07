"""脚本生成助手 —— LangGraph 智能体实现（六节点版）。

节点（6个，对应业务流程的六个阶段）：
  1. load_data        读取数据：查商品、内容拆解、知识库；缺拆解自动补建
  2. plan             规划：DeepSeek 根据数据规划内容角度（标题/钩子/结构/转化点）
  3. generate_script  生成：DeepSeek 生成秒级分镜脚本
  4. quality_check    质检：打分判断是否合格，不合格走条件边回到生成（最多重试2次）
  5. save_result      写回：保存到脚本分镜表，关联拆解编号，状态"待审核"
  6. human_confirm    人工确认：输出"待人工确认"的交付说明（业务侧在脚本分镜页审核）

边：
  START -> load_data -> plan -> generate_script -> quality_check
  quality_check -> generate_script  （条件边：质检未通过且未超重试上限）
  quality_check -> save_result      （条件边：质检通过）
  save_result -> human_confirm -> END

状态（State）：
  trace         工具调用轨迹（工具名/参数/结果/状态），供前端展示"智能体运行流程"
  final_answer  最终输出文本
  retries       质检重试计数
  业务数据（商品/拆解/脚本/质检/保存结果）在节点间通过 ctx 传递
"""

import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from ai_workflow.agents import (
    MODEL,
    _execute_script_tool,
    _tool_create_content_breakdown,
    _tool_plan_script,
    _tool_query_content_records,
    _tool_query_product,
    _tool_search_knowledge,
    call_ai,
    parse_response,
)

MAX_QUALITY_RETRIES = 2


class ScriptAgentState(TypedDict):
    """LangGraph 的全局状态。"""

    trace: Annotated[list, operator.add]  # 工具调用轨迹（节点返回的条目会追加累积）
    final_answer: str                     # 最终输出
    retries: int                          # 质检重试计数


def _steps(state: ScriptAgentState, items: list) -> list:
    """把 (tool, args, result) 列表转成 trace 条目，轮次号自动递增。"""
    out = []
    for i, (tool, args, result) in enumerate(items, 1):
        out.append({
            "round": len(state.get("trace", [])) + len(out) + 1,
            "tool": tool,
            "args": args,
            "result": result,
            "status": "success" if "error" not in result else "error",
        })
    return out


def build_script_langgraph_agent(db, ctx: dict):
    """构建六节点 LangGraph 图并返回编译后的 app。

    db：数据库会话；ctx：本次请求的业务上下文（product_id、duration、
    product、contents、script、quality、saved 等），由节点执行时读写。
    """

    def load_data_node(state: ScriptAgentState) -> dict:
        """节点1：读取数据——查商品、查拆解、查知识库（补建拆解移到规划节点之后，保证内容有真材实料）。"""
        product = _tool_query_product({"product_id": ctx["product_id"]}, ctx, db)
        contents = _tool_query_content_records({"product_id": ctx["product_id"]}, ctx, db)
        knowledge = _tool_search_knowledge({"keyword": "脚本模板"}, ctx, db)
        entries = [
            ("query_product", {"product_id": ctx["product_id"]}, product),
            ("query_content_records", {"product_id": ctx["product_id"]}, contents),
            ("search_knowledge", {"keyword": "脚本模板"}, knowledge),
        ]
        return {"trace": _steps(state, entries)}

    def plan_node(state: ScriptAgentState) -> dict:
        """节点2：规划——DeepSeek 拆解内容角度；若无拆解记录，则用规划结果补建（保证拆解内容具体、有差异）。"""
        plan = _tool_plan_script({"product_id": ctx["product_id"]}, ctx, db)
        entries = [("plan_script", {"product_id": ctx["product_id"]}, plan)]
        if not ctx.get("contents"):
            created = _tool_create_content_breakdown({"product_id": ctx["product_id"]}, ctx, db)
            entries.append(("create_content_breakdown", {"product_id": ctx["product_id"]}, created))
        return {"trace": _steps(state, entries)}

    def generate_node(state: ScriptAgentState) -> dict:
        """节点3：生成——DeepSeek 生成秒级分镜脚本。"""
        args = {"product_id": ctx["product_id"], "duration": ctx.get("duration", 30)}
        result = _execute_script_tool("generate_script", args, ctx, db)
        return {"trace": _steps(state, [("generate_script", args, result)])}

    def quality_node(state: ScriptAgentState) -> dict:
        """节点4：质检——打分判断是否合格。"""
        result = _execute_script_tool("quality_check_script", {}, ctx, db)
        return {
            "trace": _steps(state, [("quality_check_script", {}, result)]),
            "retries": state.get("retries", 0) + 1,
        }

    def save_node(state: ScriptAgentState) -> dict:
        """节点5：写回——保存到脚本分镜表，关联拆解编号，状态"待审核"。"""
        result = _execute_script_tool("save_script", {}, ctx, db)
        ctx["saved"] = result
        return {"trace": _steps(state, [("save_script", {}, result)])}

    def human_confirm_node(state: ScriptAgentState) -> dict:
        """节点6：人工确认——输出待人工确认的交付说明。"""
        saved = ctx.get("saved") or {}
        qc = ctx.get("quality") or {}
        codes = saved.get("script_codes") or []
        message = (
            f"脚本已生成并保存（编号：{', '.join(codes) or '无'}），"
            f"质检 {qc.get('overall_score', '-')} 分，状态为待审核。"
            "请在'脚本分镜'页面人工确认后再发布。"
        )
        return {
            "trace": _steps(state, [("human_confirm", {"status": "待审核"}, {"message": message})]),
            "final_answer": message,
        }

    def route_after_quality(state: ScriptAgentState) -> str:
        """条件边：质检通过（或重试耗尽）去写回，否则回到生成重做。"""
        quality = ctx.get("quality") or {}
        passed = quality.get("pass", True) or quality.get("overall_score", 0) >= 60
        if passed or state.get("retries", 0) >= MAX_QUALITY_RETRIES:
            return "save"
        return "generate"

    graph = StateGraph(ScriptAgentState)
    graph.add_node("load_data", load_data_node)
    graph.add_node("plan", plan_node)
    graph.add_node("generate_script", generate_node)
    graph.add_node("quality_check", quality_node)
    graph.add_node("save_result", save_node)
    graph.add_node("human_confirm", human_confirm_node)
    graph.add_edge(START, "load_data")
    graph.add_edge("load_data", "plan")
    graph.add_edge("plan", "generate_script")
    graph.add_edge("generate_script", "quality_check")
    graph.add_conditional_edges("quality_check", route_after_quality, {"generate": "generate_script", "save": "save_result"})
    graph.add_edge("save_result", "human_confirm")
    graph.add_edge("human_confirm", END)
    return graph.compile()


def run_script_langgraph_agent(db, ctx: dict) -> tuple:
    """运行六节点 LangGraph 智能体，返回 (最终输出文本, trace)。"""
    app = build_script_langgraph_agent(db, ctx)
    result = app.invoke({"trace": [], "final_answer": "", "retries": 0})
    return result.get("final_answer") or "", result.get("trace") or []
