import os

from langchain_core.tools import tool
import requests
from langchain_openai import ChatOpenAI

from node.state import AnalysisState


# from node.state import AnalysisState


def generate_statistics(category_name:str) -> dict:
    """生成統計數據"""
    url = f"http://localhost:8080/api/analytics/category-stats/{category_name}"
    response = requests.get(url)
    try:
        return response.json()
    except ValueError:
        print("無法解析 JSON 響應")
        return response.text


def summarize_statistics(state: AnalysisState):
    """只提取關鍵統計數字，不做完整分析"""
    model = ChatOpenAI(
        api_key=os.getenv('OPEN_AI_KEY'),
        model='gpt-4o-mini'
    )
    statistics_context = generate_statistics(state['category_name'])

    prompt = f"""
    請從以下營隊統計數據中提取關鍵數字，用於後續的定價分析：

    數據：
    {statistics_context}

    請提取以下資訊（只要數字和事實，不要分析建議）：

    ## 輸出格式：
    ### 基礎市場數據
    - 該類別營隊總數：[數字]
    - 平均報名率：[百分比]
    - 平均價格：NT$ [價格]
    - 平均每日價格：NT$ [價格]

    ### 成功案例
    - 最高報名率營隊：camp_id [ID]，價格 NT$ [價格]，報名率 [百分比]，主辦方：[名稱]
    - 第二高報名率營隊：camp_id [ID]，價格 NT$ [價格]，報名率 [百分比]，主辦方：[名稱]

    ### 失敗案例  
    - 最低報名率營隊：camp_id [ID]，價格 NT$ [價格]，報名率 [百分比]，主辦方：[名稱]

    ### 價格分布
    - 最低價格：NT$ [價格]（報名率：[百分比]）
    - 最高價格：NT$ [價格]（報名率：[百分比]）
    - 價格中位數：NT$ [價格]

    ### 折扣策略數據
    - 平均早鳥折扣：[金額]元（[百分比]%）
    - 平均團體折扣：[金額]元（[百分比]%）

    ### 時間因素
    - 最常見舉辦月份：[月份]
    - 平均提前報名天數：[天數]

    只提供數據，不要任何分析或建議。
    """

    response = model.invoke(prompt)
    state['statistics_analysis'] = response.content
    return state




