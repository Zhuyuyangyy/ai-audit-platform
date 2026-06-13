# Report Generator
# Generates full-chain audit reports

import os
import sqlite3
from datetime import datetime
from typing import Dict, List
import json

class ReportGenerator:

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.environ.get(
            "DATABASE_PATH",
            os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "ai_audit_platform.db"))
        )
    
    def generate_session_report(self, session_id: str) -> Dict:
        """生成会话级别的完整审计报告"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取会话所有日志
        cursor.execute("""
            SELECT id, user_id, prompt, output, risk_score, risk_level,
                   fuse_action, created_at, prompt_rules, output_rules
            FROM audit_logs WHERE session_id = ? ORDER BY created_at ASC
        """, (session_id,))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return {"error": "会话不存在或无审计记录"}
        
        # 统计
        total = len(rows)
        risk_scores = [r[4] for r in rows]
        avg_risk = sum(risk_scores) / total if total > 0 else 0
        
        # 风险分布
        risk_dist = {"safe": 0, "low": 0, "medium": 0, "high": 0, "critical": 0}
        for r in rows:
            risk_dist[r[5]] = risk_dist.get(r[5], 0) + 1
        
        # 熔断动作汇总
        fuse_summary = {}
        for r in rows:
            action = r[6]
            fuse_summary[action] = fuse_summary.get(action, 0) + 1
        
        # 政策文档引用
        policy_refs = self._collect_policy_references(rows)
        
        # 生成警告列表
        warnings = self._generate_warnings(rows, avg_risk)
        
        return {
            "session_id": session_id,
            "total_interactions": total,
            "avg_risk_score": round(avg_risk, 2),
            "risk_distribution": risk_dist,
            "fuse_actions_summary": fuse_summary,
            "policy_doc_references": list(set(policy_refs)),
            "warnings": warnings,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "interactions": [
                {
                    "id": r[0],
                    "user_id": r[1],
                    "prompt": r[2],
                    "output": r[3],
                    "risk_score": r[4],
                    "risk_level": r[5],
                    "fuse_action": r[6],
                    "created_at": r[7],
                    "prompt_rules": self._safe_json_load(r[8]),
                    "output_rules": self._safe_json_load(r[9])
                }
                for r in rows
            ]
        }
    
    def _safe_json_load(self, s):
        if not s:
            return []
        try:
            return json.loads(s)
        except:
            return []
    
    def _collect_policy_references(self, rows) -> List[str]:
        """收集所有政策文档引用"""
        refs = set()
        for r in rows:
            rules_str = r[8] or r[9] or "[]"
            try:
                rules = json.loads(rules_str) if isinstance(rules_str, str) else rules_str
                for rule in (rules or []):
                    desc = rule.get("description", "")
                    if desc:
                        refs.add(desc)
            except:
                pass
        return list(refs)
    
    def _generate_warnings(self, rows, avg_risk: float) -> List[str]:
        """根据统计生成警告"""
        warnings = []
        
        # 高风险占比
        high_critical = sum(1 for r in rows if r[5] in ("high", "critical"))
        if high_critical / len(rows) > 0.3:
            warnings.append(f"会话中存在{high_critical}条高风险/严重风险交互，占比超过30%")
        
        # 平均风险过高
        if avg_risk > 60:
            warnings.append(f"会话平均风险分 {avg_risk:.1f} 偏高，建议人工复核")
        
        # 熔断频繁
        refuse_count = sum(1 for r in rows if r[6] in ("refuse", "block"))
        if refuse_count > 0:
            warnings.append(f"会话中有 {refuse_count} 次被拒绝或熔断封禁")
        
        # 检查是否有涉密查询
        for r in rows:
            try:
                rules = json.loads(r[8]) if r[8] else []
                for rule in rules:
                    if rule.get("rule_id") == "RULE_AI_001":
                        warnings.append("检测到涉密信息查询记录，请关注")
                        break
            except:
                pass
        
        if not warnings:
            warnings.append("未检测到明显异常，会话审计通过")
        
        return warnings
    
    def generate_daily_report(self, date: str = None) -> Dict:
        """生成日报"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*), AVG(risk_score),
                   SUM(CASE WHEN risk_level IN ('high','critical') THEN 1 ELSE 0 END),
                   SUM(CASE WHEN fuse_action = 'refuse' THEN 1 ELSE 0 END)
            FROM audit_logs
            WHERE DATE(created_at) = ?
        """, (date,))
        
        row = cursor.fetchone()
        conn.close()
        
        total, avg_score, high_risk_count, refused = row
        
        return {
            "date": date,
            "total_interactions": total or 0,
            "avg_risk_score": round(avg_score or 0, 2),
            "high_critical_count": high_risk_count or 0,
            "refused_count": refused or 0,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def export_json(self, session_id: str) -> str:
        """导出会话报告为JSON"""
        report = self.generate_session_report(session_id)
        return json.dumps(report, ensure_ascii=False, indent=2)