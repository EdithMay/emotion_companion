# backend/app/services/rag_service.py

import os
from pathlib import Path
from typing import List
from ..models.schemas import RAGResult

# ChromaDB 存储路径：backend/chroma_db/
CHROMA_PATH = str(Path(__file__).parent.parent.parent / "chroma_db")

# 全局单例
_rag_instance = None


def get_rag_service() -> "RAGService":
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGService()
    return _rag_instance


class RAGService:
    """
    RAG 长期记忆服务。

    两个核心方法：
      index(text, metadata)   → 向量化并存入 ChromaDB
      search(query, top_k)    → 语义检索，返回相关历史片段

    索引触发时机（由外部调用）：
      - 生成心情小记后（summary_service.py 调用）
      - 记忆压缩完成后（companion_agent.py 调用）
      - 会话中有实质内容的用户消息（companion_agent.py 调用）

    检索触发时机：
      - 用户每次发消息时，companion_agent.py 调用 search()
    """

    def __init__(self):
        print("🔄 初始化 RAG 服务...")
        self._init_chromadb()
        self._init_embedding_model()
        print(f"✅ RAG 服务初始化成功")
        print(f"   ChromaDB 路径: {CHROMA_PATH}")
        print(f"   当前索引数量: {self.collection.count()}")

    def _init_chromadb(self):
        """初始化 ChromaDB 本地持久化存储"""
        import chromadb
        os.makedirs(CHROMA_PATH, exist_ok=True)
        self.client = chromadb.PersistentClient(path=CHROMA_PATH)
        self.collection = self.client.get_or_create_collection(
            name="emotion_memories",
            metadata={
                "hnsw:space": "cosine",
                "hnsw:construction_ef": 128,
                "hnsw:M": 16
            }
        )

    def _init_embedding_model(self):
        """
        使用阿里云 text-embedding-v4 API 进行向量化。
        不需要本地下载模型，直接调用 dashscope 接口。
        """
        import dashscope
        from ..config import get_settings
        settings = get_settings()
        dashscope.api_key = os.getenv("ALY_API_KEY")
        self.dashscope = dashscope
        print("   向量化模型：text-embedding-v4（阿里云 API）")

    def _get_embedding(self, text: str) -> list:
        """
        调用 text-embedding-v4 API 获取文本向量。
        返回 float 列表，维度为 1024。
        """
        from dashscope import TextEmbedding
        response = TextEmbedding.call(
            model="text-embedding-v4",
            input=text,
            dimension=1024
        )
        if response.status_code == 200:
            return response.output["embeddings"][0]["embedding"]
        else:
            raise RuntimeError(
                f"text-embedding-v4 调用失败: "
                f"{response.status_code} {response.message}"
            )



    # ──────────────────────────────────────────
    # 核心方法 1：写入索引
    # ──────────────────────────────────────────

    def index(self, text: str, metadata: dict) -> bool:
        """
        将文本向量化并存入 ChromaDB。

        Args:
            text:     要索引的文本内容
            metadata: 附带元数据，必须包含 type 字段，建议包含 date
                      例如：{"type": "mood_entry", "date": "2025-05-09", "score": 7}
                      例如：{"type": "memory_summary", "conversation_id": "1"}
                      例如：{"type": "user_message", "date": "2025-05-09", "conversation_id": "1"}

        Returns:
            True 表示成功，False 表示失败
        """
        if not text or not text.strip():
            return False

        try:
            embedding = self._get_embedding(text)

            # 构造唯一 ID，避免重复索引
            entry_type = metadata.get("type", "unknown")
            date_str   = metadata.get("date", "nodate")
            unique_id  = f"{entry_type}_{date_str}_{hash(text) % 1000000}"

            # metadata 所有值必须是 str/int/float/bool，不能是 None
            clean_metadata = {
                k: (str(v) if v is not None else "")
                for k, v in metadata.items()
            }

            self.collection.upsert(   # upsert：相同 ID 则覆盖，避免重复
                embeddings=[embedding],
                documents=[text],
                metadatas=[clean_metadata],
                ids=[unique_id]
            )
            return True

        except Exception as e:
            print(f"  ⚠️  RAG 索引失败: {e}")
            return False

    # ──────────────────────────────────────────
    # 核心方法 2：语义检索
    # ──────────────────────────────────────────

    def search(self, query: str, top_k: int = 3) -> List[RAGResult]:
        """
        根据查询文本语义检索最相关的历史片段。

        Args:
            query:  用户当前消息文本
            top_k:  返回最相关的前 N 条

        Returns:
            RAGResult 列表，按相似度从高到低排序
        """
        if not query or not query.strip():
            return []

        try:
            # 当前索引为空时直接返回
            if self.collection.count() == 0:
                return []

            actual_top_k = min(top_k, self.collection.count())
            embedding = self._get_embedding(query)

            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=actual_top_k,
                include=["documents", "metadatas", "distances"]
            )

            rag_results = []
            docs      = results["documents"][0]
            metadatas = results["metadatas"][0]
            distances = results["distances"][0]   # 余弦距离，越小越相似

            for doc, meta, dist in zip(docs, metadatas, distances):
                similarity = 1 - dist   # 转换为相似度分数（0-1）

                # 过滤相似度过低的结果（低于 0.3 的基本不相关）
                if similarity < 0.5:
                    continue

                rag_results.append(RAGResult(
                    text=doc,
                    date=meta.get("date", ""),
                    score=round(similarity, 3),
                    entry_type=meta.get("type", "unknown")
                ))

            return rag_results

        except Exception as e:
            print(f"  ⚠️  RAG 检索失败: {e}")
            return []

    def format_for_prompt(self, results: List[RAGResult]) -> str:
        """
        将检索结果格式化为可直接注入 prompt 的文字。
        供 companion_agent.py 调用。

        输出示例：
          · 2025-04-20（心情日记）：用户提到最近工作压力很大，感到焦虑
          · 2025-04-25（对话记忆）：用户担心和朋友的关系出现裂痕
        """
        if not results:
            return ""

        type_labels = {
            "mood_entry":     "心情日记",
            "memory_summary": "对话记忆",
            "user_message":   "历史对话",
        }

        lines = []
        for r in results:
            label = type_labels.get(r.entry_type, "历史记录")
            date  = r.date if r.date else "历史"
            # 截断过长的文本，避免 prompt 过大
            text  = r.text[:150] + "..." if len(r.text) > 150 else r.text
            lines.append(f"· {date}（{label}）：{text}")

        return "\n".join(lines)

    # ──────────────────────────────────────────
    # 工具方法
    # ──────────────────────────────────────────

    def count(self) -> int:
        """返回当前索引总数"""
        return self.collection.count()

    def delete_by_date(self, date: str) -> bool:
        """删除指定日期的所有索引（用于重新生成心情小记时）"""
        try:
            results = self.collection.get(
                where={"date": date}
            )
            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                print(f"  🗑️  删除 {date} 的 {len(results['ids'])} 条索引")
            return True
        except Exception as e:
            print(f"  ⚠️  删除索引失败: {e}")
            return False
