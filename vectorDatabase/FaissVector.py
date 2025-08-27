from typing import List, Union, Dict, Any, Optional, Callable
from langchain_community.vectorstores import FAISS
from enum import Enum
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
import os
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# 初始化OpenAI嵌入
api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_AI_KEY")
OPEN_AI_EMBEDDING = OpenAIEmbeddings(api_key=api_key)


class DataType(Enum):
    TEXT = 'text'
    DOCUMENT = 'document'


class CustomVectorStore:
    def __init__(self, folder_path='universal_faiss_db', collection_name='documents', 
                 data_type: DataType = DataType.TEXT, text_field: str = 'content'):
        """初始化通用FAISS向量庫
        
        Args:
            folder_path (str): 向量庫存儲路徑
            collection_name (str): 集合名稱
            data_type (DataType): 數據類型
            text_field (str): 文本內容字段名，預設為'content'
        """
        self.folder_path = folder_path
        self.collection_name = collection_name
        self.data_type = data_type
        self.text_field = text_field  # 可配置的文本字段
        self.index_path = os.path.join(folder_path, f"{collection_name}.faiss")
        self.store_path = os.path.join(folder_path, f"{collection_name}.pkl")

        # 創建存儲目錄
        os.makedirs(folder_path, exist_ok=True)

        # 初始化或加載現有的向量庫
        self.db = self._load_db()

        # 如果加載失敗，初始化新的向量庫
        if self.db is None:
            self._initialize_empty_db()

    def _load_db(self):
        """加載現有的向量庫"""
        if not self.exists():
            return None

        try:
            return FAISS.load_local(
                self.folder_path,
                OPEN_AI_EMBEDDING,
                self.collection_name,
                allow_dangerous_deserialization=True
            )
        except Exception as e:
            print(f"加載向量庫時發生錯誤: {e}")
            return None

    def _initialize_empty_db(self):
        """初始化空的向量庫"""
        try:
            self.db = FAISS.from_texts(
                texts=["初始化文檔"],
                embedding=OPEN_AI_EMBEDDING,
                metadatas=[{"initialization": True, "doc_type": "init"}]
            )
            self.db.save_local(self.folder_path, self.collection_name)
        except Exception as e:
            print(f"初始化向量庫時發生錯誤: {e}")
            raise ValueError("無法初始化向量庫")

    def exists(self):
        """檢查向量庫是否存在"""
        return os.path.exists(self.index_path) and os.path.exists(self.store_path)

    def add_documents(self, data: List[Dict[str, Any]], 
                     metadata_fields: Optional[List[str]] = None,
                     text_extractor: Optional[Callable[[Dict], str]] = None,
                     id_field: Optional[str] = None,
                     check_duplicates: bool = False, 
                     overwrite_filter: Optional[Dict[str, Any]] = None):
        """通用添加文檔方法
        
        Args:
            data (List[Dict]): 數據列表
            metadata_fields (Optional[List[str]]): 需要保存為metadata的字段列表，為None時保存所有字段
            text_extractor (Optional[Callable]): 自定義文本提取函數，為None時使用text_field
            id_field (Optional[str]): 用作唯一ID的字段名
            check_duplicates (bool): 是否檢查重複
            overwrite_filter (Optional[Dict]): 覆蓋條件，匹配的文檔會被刪除後重新添加
        """
        if not data:
            print("❌ 沒有數據需要添加")
            return

        print(f"📥 準備添加 {len(data)} 條文檔")

        # 覆蓋模式：根據過濾條件刪除舊文檔
        if overwrite_filter:
            print(f"⚠️ 覆蓋模式：將刪除符合條件 {overwrite_filter} 的舊文檔")
            self._delete_by_filter(overwrite_filter)

        # 去重模式
        if check_duplicates:
            data = self._filter_duplicates(data, text_extractor)
            if not data:
                print("📝 沒有新的文檔需要添加")
                return

        # 提取文本內容
        texts = []
        for item in data:
            if text_extractor:
                text = text_extractor(item)
            else:
                text = item.get(self.text_field, '')
            texts.append(text)

        # 構建metadata
        metadatas = []
        for i, item in enumerate(data):
            # 生成唯一ID
            if id_field and item.get(id_field):
                doc_id = f"doc-{item[id_field]}"
            else:
                doc_id = f"doc-{i}-{datetime.now().timestamp()}"

            metadata = {
                'doc_id': doc_id,
                'batch_timestamp': datetime.now().isoformat(),
                'text_field': self.text_field
            }

            # 添加指定的metadata字段
            if metadata_fields is None:
                # 保存所有字段（除了文本字段）
                for key, value in item.items():
                    if key != self.text_field and value is not None:
                        metadata[key] = value
            else:
                # 只保存指定的字段
                for field in metadata_fields:
                    if item.get(field) is not None:
                        metadata[field] = item[field]

            metadatas.append(metadata)

        # 添加到向量庫
        if self.data_type == DataType.TEXT:
            self.db.add_texts(texts=texts, metadatas=metadatas)
        else:
            documents = [
                Document(page_content=text, metadata=metadata)
                for text, metadata in zip(texts, metadatas)
            ]
            self.db.add_documents(documents=documents)

        # 保存更新後的向量庫
        self.db.save_local(self.folder_path, self.collection_name)
        print(f"✅ 成功添加 {len(data)} 條文檔到向量庫")

    def add_from_get_result(self, get_result_data: List[Dict[str, Any]], 
                           **kwargs):
        """使用get_result方法的數據添加文檔（語法糖）
        
        Args:
            get_result_data (List[Dict]): get_result方法返回的數據
            **kwargs: 傳遞給add_documents的其他參數
        """
        self.add_documents(get_result_data, **kwargs)

    def search_documents(self, query: str, filter_dict: Optional[Dict[str, Any]] = None, 
                        k: int = 50) :
        """搜索相關文檔
        
        Args:
            query (str): 查詢文本
            filter_dict (Optional[Dict]): 過濾條件
            k (int): 返回結果數量
            
        Returns:
            List[Dict]: 搜索結果列表
        """
        results = self.db.similarity_search(
            query=query,
            k=k,
            filter=filter_dict
        )

        # 格式化結果
        formatted_results = []
        for doc in results:
            result = {
                'content': doc.page_content,
                **doc.metadata  # 展開所有metadata
            }
            # 移除None值和內部字段
            result = {k: v for k, v in result.items() 
                     if v is not None and not k.startswith('_')}
            formatted_results.append(result)

        return formatted_results

    def search_documents_mmr(self, query: str, filter_dict: Optional[Dict[str, Any]] = None,
                            fetch_k: int = 100, k: int = 50, 
                            lambda_mult: float = 0.5) -> List[Dict[str, Any]]:
        """使用MMR搜索文檔
        
        Args:
            query (str): 查詢文本
            filter_dict (Optional[Dict]): 過濾條件
            fetch_k (int): 初始獲取數量
            k (int): 最終返回數量
            lambda_mult (float): 多樣性參數
            
        Returns:
            List[Dict]: 搜索結果列表
        """
        results = self.db.max_marginal_relevance_search(
            query=query,
            fetch_k=fetch_k,
            k=k,
            lambda_mult=lambda_mult,
            filter=filter_dict
        )

        formatted_results = []
        for doc in results:
            result = {
                'content': doc.page_content,
                **doc.metadata
            }
            result = {k: v for k, v in result.items() 
                     if v is not None and not k.startswith('_')}
            formatted_results.append(result)

        return formatted_results

    def get_documents_by_filter(self, filter_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        """根據過濾條件獲取文檔
        
        Args:
            filter_dict (Dict): 過濾條件
            
        Returns:
            List[Dict]: 文檔列表
        """
        all_docs = self._get_all_docs()
        filtered_docs = []

        for doc in all_docs:
            match = True
            for key, value in filter_dict.items():
                if doc.metadata.get(key) != value:
                    match = False
                    break
            if match:
                filtered_docs.append(doc)

        # 格式化結果
        formatted_results = []
        for doc in filtered_docs:
            result = {
                'content': doc.page_content,
                **doc.metadata
            }
            result = {k: v for k, v in result.items() 
                     if v is not None and not k.startswith('_')}
            formatted_results.append(result)

        return formatted_results

    def get_unique_values(self, field: str) -> List[Any]:
        """獲取指定字段的所有唯一值
        
        Args:
            field (str): 字段名
            
        Returns:
            List[Any]: 唯一值列表
        """
        all_docs = self._get_all_docs()
        values = set()
        for doc in all_docs:
            value = doc.metadata.get(field)
            if value is not None and value != 'init':
                values.add(value)
        return list(values)

    def get_field_stats(self, group_by_field: str) -> Dict[str, int]:
        """獲取按字段分組的統計信息
        
        Args:
            group_by_field (str): 分組字段名
            
        Returns:
            Dict[str, int]: 字段值到計數的映射
        """
        all_docs = self._get_all_docs()
        stats = {}
        for doc in all_docs:
            value = doc.metadata.get(group_by_field)
            if value is not None and value != 'init':
                stats[value] = stats.get(value, 0) + 1
        return stats

    def delete_by_filter(self, filter_dict: Dict[str, Any]) -> bool:
        """根據過濾條件刪除文檔
        
        Args:
            filter_dict (Dict): 過濾條件
            
        Returns:
            bool: 刪除成功返回True
        """
        return self._delete_by_filter(filter_dict)

    def _delete_by_filter(self, filter_dict: Dict[str, Any]) -> bool:
        """內部刪除方法"""
        try:
            all_docs = self._get_all_docs()
            docs_to_delete = []
            docs_to_keep = []

            for doc in all_docs:
                match = True
                for key, value in filter_dict.items():
                    if doc.metadata.get(key) != value:
                        match = False
                        break
                
                if match:
                    docs_to_delete.append(doc)
                else:
                    docs_to_keep.append(doc)

            if not docs_to_delete:
                print(f"未找到符合條件 {filter_dict} 的文檔")
                return False

            # 重建索引
            if len(docs_to_keep) > 0:
                if self.data_type == DataType.TEXT:
                    texts = [doc.page_content for doc in docs_to_keep]
                    metadatas = [doc.metadata for doc in docs_to_keep]
                    self.db = FAISS.from_texts(
                        texts=texts,
                        embedding=OPEN_AI_EMBEDDING,
                        metadatas=metadatas
                    )
                else:
                    self.db = FAISS.from_documents(
                        documents=docs_to_keep,
                        embedding=OPEN_AI_EMBEDDING
                    )

                self.db.save_local(self.folder_path, self.collection_name)
            else:
                self._initialize_empty_db()

            print(f"成功刪除 {len(docs_to_delete)} 條文檔")
            return True

        except Exception as e:
            print(f"刪除文檔時發生錯誤: {str(e)}")
            return False

    def _filter_duplicates(self, data: List[Dict[str, Any]], 
                          text_extractor: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """過濾重複數據"""
        all_docs = self._get_all_docs()
        existing_texts = set()
        
        for doc in all_docs:
            existing_texts.add(doc.page_content)

        unique_data = []
        duplicates_count = 0

        for item in data:
            if text_extractor:
                text = text_extractor(item)
            else:
                text = item.get(self.text_field, '')
            
            if text not in existing_texts:
                unique_data.append(item)
                existing_texts.add(text)
            else:
                duplicates_count += 1

        if duplicates_count > 0:
            print(f"⚠️ 發現 {duplicates_count} 條重複文檔，已跳過")

        return unique_data

    def _get_all_docs(self) -> List[Document]:
        """獲取所有文檔"""
        if not self.db:
            return []

        all_doc_ids = list(self.db.index_to_docstore_id.values())
        return self.db.get_by_ids(all_doc_ids)

    def create_retriever(self, search_type="similarity", filter_dict: Optional[Dict[str, Any]] = None, **kwargs):
        """創建檢索器用於RAG"""
        search_kwargs = kwargs.copy()

        if filter_dict:
            search_kwargs['filter'] = filter_dict

        return self.db.as_retriever(
            search_type=search_type,
            search_kwargs=search_kwargs
        )

    def delete_all_documents(self):
        """刪除所有文檔並重新初始化"""
        try:
            if os.path.exists(self.index_path):
                os.remove(self.index_path)
            if os.path.exists(self.store_path):
                os.remove(self.store_path)

            self._initialize_empty_db()
            print("成功刪除所有文檔並重新初始化向量庫")

        except Exception as e:
            print(f"刪除向量庫時發生錯誤: {e}")

    def get_total_documents(self) -> int:
        """獲取總文檔數量"""
        all_docs = self._get_all_docs()
        return len([doc for doc in all_docs if not doc.metadata.get('initialization', False)])

    def export_documents(self, filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """導出文檔數據"""
        if filter_dict:
            return self.get_documents_by_filter(filter_dict)
        else:
            all_docs = self._get_all_docs()
            filtered_docs = [
                doc for doc in all_docs 
                if not doc.metadata.get('initialization', False)
            ]

            formatted_results = []
            for doc in filtered_docs:
                result = {
                    'content': doc.page_content,
                    **doc.metadata
                }
                result = {k: v for k, v in result.items() 
                         if v is not None and not k.startswith('_')}
                formatted_results.append(result)

            return formatted_results

