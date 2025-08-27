from langgraph.graph import MessagesState


class AnalysisState(MessagesState):
    query: str
    category_name:str
    content_analysis: str
    statistics_analysis: str
    final_result: str