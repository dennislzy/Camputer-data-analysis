from fastapi import FastAPI


from node.final_result_node import create_final_result_node
from node.comment_node import summarize_content
from node.state import AnalysisState
from node.statistics_node import summarize_statistics

app = FastAPI(title="簡單的 FastAPI 應用")
import typer
import uvicorn
from langgraph.graph.state import END, StateGraph


# 基本的 GET 路由
@app.get("/")
async def root():
    return {"message": "歡迎使用 FastAPI"}

@app.get("/test/{category_name}")
async def test(category_name:str):
    workflow = StateGraph(AnalysisState)

    # 添加節點
    workflow.add_node("content_analysis", summarize_content)
    workflow.add_node("statistics_analysis", summarize_statistics)
    workflow.add_node("final_result", create_final_result_node)

    # 定義流程順序
    workflow.set_entry_point("content_analysis")
    workflow.add_edge("content_analysis", "statistics_analysis")
    workflow.add_edge("statistics_analysis", "final_result")
    workflow.add_edge("final_result", END)

    # 編譯圖
    app = workflow.compile()

    initial_state = {
        "query": f"{category_name}價格推薦",
        "content_analysis": "",
        "statistics_analysis": "",
        "final_result": "",
        'category_name': category_name
    }
    result = app.invoke(initial_state)

    return result["final_result"]

# app.include_router(ChatController.router)
# app.include_router(testController.router)


application=typer.Typer()
@application.command()
def start():
   uvicorn.run("main:app", host="127.0.0.1", port=7000, reload=True,workers=1)
if __name__ == "__main__":
    start()