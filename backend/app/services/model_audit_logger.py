# Model Audit Logger
# Records full audit trail: user, time, input, output, evidence, risk level

import sqlite3
from datetime import datetime
from typing import Optional

class ModelAuditLogger:
    
    def __init__(self, db_path: str = "D:/ZYY Project/ai-audit-platform/backend/ai_audit_platform.db"):
        self.db_path = db_path
    
    def log_interaction(
        self,
        user_id: str,
        session_id: str,
        prompt: str,
        output: Optional[str],
        risk_score: float,
        risk_level: str,
        fuse_action: str,
        prompt_rules: list = None,
        output_rules: list = None,
        rag_trace: list = None
    ) -> int:
        """记录一次完整交互审计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO audit_logs (
                user_id, session_id, prompt, output, risk_score, risk_level,
                fuse_action, prompt_rules, output_rules, rag_trace, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, session_id, prompt, output, risk_score, risk_level,
            fuse_action,
            str(prompt_rules) if prompt_rules else "[]",
            str(output_rules) if output_rules else "[]",
            str(rag_trace) if rag_trace else "[]",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return log_id
    
    def log_rag_trace(self, audit_id: int, claim: str, evidence: str, policy_doc_id: int):
        """记录RAG溯源结果"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO rag_trace (audit_id, claim, evidence, policy_doc_id, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            audit_id, claim, evidence, policy_doc_id,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        
        conn.commit()
        conn.close()
    
    def log_fuse_action(self, audit_id: int, fuse_reason: str, action_taken: str):
        """记录熔断动作"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO fuse_records (audit_id, fuse_reason, action_taken, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            audit_id, fuse_reason, action_taken,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        
        conn.commit()
        conn.close()
    
    def get_audit_log(self, log_id: int) -> dict:
        """获取指定审计日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, session_id, prompt, output, risk_score, risk_level,
                   fuse_action, created_at FROM audit_logs WHERE id = ?
        """, (log_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            "id": row[0],
            "user_id": row[1],
            "session_id": row[2],
            "prompt": row[3],
            "output": row[4],
            "risk_score": row[5],
            "risk_level": row[6],
            "fuse_action": row[7],
            "created_at": row[8]
        }
    
    def get_session_logs(self, session_id: str) -> list:
        """获取会话所有审计日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, session_id, prompt, output, risk_score, risk_level,
                   fuse_action, created_at
            FROM audit_logs WHERE session_id = ? ORDER BY created_at ASC
        """, (session_id,))
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": r[0], "user_id": r[1], "session_id": r[2],
                "prompt": r[3], "output": r[4], "risk_score": r[5],
                "risk_level": r[6], "fuse_action": r[7], "created_at": r[8]
            }
            for r in rows
        ]
    
    def update_output(self, log_id: int, output: str, risk_score: float, risk_level: str, fuse_action: str):
        """更新审计日志的输出部分（补充输出审计结果）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE audit_logs SET output = ?, risk_score = ?, risk_level = ?, fuse_action = ?
            WHERE id = ?
        """, (output, risk_score, risk_level, fuse_action, log_id))
        conn.commit()
        conn.close()