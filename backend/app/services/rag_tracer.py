# RAG Tracer - 溯源链路校验
# Binds every key conclusion to a policy document

import sqlite3
from typing import List, Dict, Tuple
import re

class RAGTracer:
    """
    RAG溯源校验器
    核心：对模型输出的每一句关键结论，绑定政策依据
    """
    
    def __init__(self, db_path: str = "D:/ZYY Project/ai-audit-platform/backend/ai_audit_platform.db"):
        self.db_path = db_path
    
    def trace(self, output: str, audit_id: int = None) -> List[Dict]:
        """
        对输出内容进行溯源验证
        返回：List[claim_evidence_pairs]
        """
        traces = []
        sentences = self._split_sentences(output)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for sent in sentences:
            sent = sent.strip()
            if len(sent) < 10:
                continue
            
            # 查找相关政策文档
            policy_docs = self._find_relevant_docs(sent, cursor)
            
            if policy_docs:
                for doc in policy_docs:
                    traces.append({
                        "claim": sent,
                        "evidence": doc["content"][:200] + "...",
                        "policy_doc_id": doc["id"],
                        "policy_title": doc["title"],
                        "confidence": doc["relevance_score"]
                    })
            else:
                # 未找到政策依据，标记为待验证
                traces.append({
                    "claim": sent,
                    "evidence": "",
                    "policy_doc_id": None,
                    "policy_title": "未找到对应政策依据",
                    "confidence": 0.0,
                    "status": "unverified"
                })
        
        conn.close()
        return traces
    
    def _find_relevant_docs(self, sentence: str, cursor) -> List[Dict]:
        """根据句子内容查找相关政策文档（关键词+语义匹配）"""
        # 提取中文词语
        words = self._extract_keywords(sentence)
        
        if not words:
            return []
        
        results = []
        
        # 策略1：从document_chunks精确匹配（PIPL等已分块的文档）
        chunk_conditions = " OR ".join([f"chunk_text LIKE '%{w}%'" for w in words[:5]])
        chunk_query = f"SELECT document_id, chunk_text FROM document_chunks WHERE {chunk_conditions} LIMIT 5"
        cursor.execute(chunk_query)
        for row in cursor.fetchall():
            doc_id = row[0]
            relevance = sum(1 for w in words if w in row[1]) / len(words)
            # 查找文档标题
            cursor.execute("SELECT title FROM policy_documents WHERE id = ?", (doc_id,))
            doc_row = cursor.fetchone()
            if doc_row:
                results.append({
                    "id": doc_id,
                    "title": doc_row[0],
                    "content": row[1],
                    "relevance_score": min(relevance + 0.1, 0.95)
                })
        
        if results:
            return results
        
        # 策略2：从policy_documents全文匹配
        doc_conditions = " OR ".join([f"(content LIKE '%{w}%' OR title LIKE '%{w}%')" for w in words[:5]])
        doc_query = f"SELECT id, title, content FROM policy_documents WHERE {doc_conditions} LIMIT 5"
        cursor.execute(doc_query)
        for row in cursor.fetchall():
            relevance = sum(1 for w in words if w in row[1] or w in row[2]) / len(words)
            results.append({
                "id": row[0],
                "title": row[1],
                "content": row[2][:300],
                "relevance_score": min(relevance, 0.95)
            })
        
        return results
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词（简化版）"""
        # 停用词
        stop_words = {"的", "了", "是", "在", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这"}
        
        # 简单分词（按标点和常见连接词）
        parts = re.split(r'[，、；。；\n ]', text)
        words = []
        for part in parts:
            part = part.strip()
            if len(part) >= 2 and part not in stop_words:
                words.append(part)
        
        return words[:8]  # 最多8个关键词
    
    def _split_sentences(self, text: str) -> List[str]:
        """按句子分割"""
        sentences = re.split(r'[。！？\n]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def verify_claim(self, claim: str, policy_doc_id: int) -> Tuple[bool, str]:
        """验证单个claim是否可以被特定政策文档支撑"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM policy_documents WHERE id = ?", (policy_doc_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return False, "政策文档不存在"
        
        # 简单验证：claim中的关键词是否在政策文档中出现
        keywords = self._extract_keywords(claim)
        matches = sum(1 for kw in keywords if kw in row[0])
        
        if matches >= len(keywords) * 0.3:
            return True, f"验证通过（{matches}/{len(keywords)} 关键词匹配）"
        else:
            return False, "验证失败：缺乏充分政策依据"