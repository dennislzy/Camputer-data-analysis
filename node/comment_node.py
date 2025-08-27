import os
import requests

from node.state import AnalysisState
from vectorDatabase.FaissVector import CustomVectorStore, DataType
from  langchain_openai import  ChatOpenAI


def generate_comment_category(category_id):
    """獲取評論數據並格式化"""
    url = f"http://localhost:8080/comments/category/{category_id}"
    response = requests.get(url)

    try:
        data = response.json()
        print(f"✅ 獲取 {len(data)} 條評論數據")

        # 格式化數據
        formatted_data = []
        for item in data:
            formatted_item = {
                'comment': item.get('comment', ''),
                'categoryName': item.get('categoryName', ''),
                'comment_id': item.get('comment_id'),
            }
            formatted_item = {k: v for k, v in formatted_item.items() if v is not None}
            formatted_data.append(formatted_item)

        return formatted_data
    except Exception as e:
        print(e)
        return []


def search_comment(query:str,categoryName:str = None,k:int=30):
    comment_data = generate_comment_category(1)
    comment_vector_store = CustomVectorStore(
        folder_path='comment_faiss_db',
        collection_name='comments',
        data_type=DataType.TEXT,
        text_field='comment'
    )

    if comment_data:
        comment_vector_store.add_documents(
            data=comment_data,
            metadata_fields=['categoryName', 'comment_id'],
            check_duplicates=True,
            id_field='comment_id',
        )
        print(f"✅ 添加完成，總文檔數: {comment_vector_store.get_total_documents()}")
    filter_dict = {'categoryName': categoryName} if categoryName else None

    results = comment_vector_store.search_documents(
        query=query,
        filter_dict=filter_dict,
        k=k
    )
    return  results

def summarize_content(state: AnalysisState):
    model = ChatOpenAI(
        api_key=os.getenv('OPEN_AI_KEY'),
        model='gpt-4o-mini'
    )

    query = state["query"]

    # 獲取文檔列表並提取文本內容
    context = search_comment(query, categoryName=state['category_name'])
    # content = "\n".join([doc.content for doc in context])

    prompt = f"""
        請分析以下留言評論，並按照以下格式輸出：

        ## 分析維度
        - **主題分類**：產品品質、價格、服務、使用體驗等
        - **關鍵問題**：提取主要抱怨點和讚美點

        ## 輸出格式
        關鍵發現：[總結2-3個重點]
        總體分析：給出活動總體評價

        以下為評論內容：
        {context}
        """

    response = model.invoke(prompt)

    state['content_analysis'] = response.content

    return state






