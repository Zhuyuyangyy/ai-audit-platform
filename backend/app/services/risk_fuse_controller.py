# Risk Fuse Controller
# Implements circuit breaker: refuse, human review, mask, block

from enum import Enum
from typing import Tuple, Optional
from datetime import datetime

class FuseLevel(int, Enum):
    SAFE = 0        # 放行
    LOW = 1         # 警告后放行
    MEDIUM = 2      # 部分屏蔽
    HIGH = 3        # 拒绝回答
    CRITICAL = 4    # 转人工审核
    BLOCK = 5       # 熔断封禁

class RiskFuseController:
    """
    熔断机制控制器
    根据风险评分和规则匹配，决定最终响应策略
    """
    
    def __init__(self):
        # 会话级别的连续高风险计数
        self._session_high_risk_count = {}
        self._session_blocked_until = {}
    
    def evaluate(
        self,
        prompt_score: float,
        output_score: float,
        detected_rules: list,
        session_id: str,
        user_role: str = "citizen",
        has_hallucination: bool = False,
        unverified_claim_count: int = 0
    ) -> Tuple[str, str, Optional[str]]:
        """
        综合评估，返回 (fuse_action, review_comment, audit_suggestion)
        
        硬门控优先于分数驱动：
        - 幻觉检测到 → 至少 human_review
        - 无依据claim → 至少 human_review
        - 幻觉 + 无依据 claim 同时 → block/human_review
        """
        # 检查会话是否被熔断封禁
        if self._is_session_blocked(session_id):
            return "block", "会话已被熔断封禁，请稍后重试或联系管理员", "SESSION_BLOCKED"
        
        # 计算综合风险（输入输出加权）
        combined_score = self._compute_combined_score(prompt_score, output_score)
        
        # 最高风险规则
        highest_rule = self._get_highest_severity_rule(detected_rules)
        
        # 硬门控1：幻觉 + 无依据claim → 强制人工审核（风险≥85）
        if has_hallucination and unverified_claim_count > 0:
            return "human_review", "检测到幻觉输出且存在无政策依据的结论，已转人工审核", "HARD_GATE_HALLUCINATION_WITH_UNVERIFIED_CLAIM"

        # 硬门控2：检测到幻觉 → 强制人工审核（风险≥70）
        if has_hallucination:
            return "human_review", "检测到幻觉输出，已转人工审核", "HARD_GATE_HALLUCINATION"

        # 常规熔断决策（分数驱动）
        fuse_action, comment = self._determine_action(
            combined_score, highest_rule, detected_rules
        )
        
        # 更新会话风险计数
        self._update_session_risk(session_id, combined_score)
        
        # 如果连续高风险，触发更强措施
        if self._session_high_risk_count.get(session_id, 0) >= 3:
            fuse_action = "human_review"
            comment = "检测到连续高风险操作，已转人工审核"
        
        return fuse_action, comment, None
    
    def _is_session_blocked(self, session_id: str) -> bool:
        until = self._session_blocked_until.get(session_id)
        if until and datetime.now() < until:
            return True
        # 过期则清除
        if until:
            del self._session_blocked_until[session_id]
        return False
    
    def _compute_combined_score(self, prompt_score: float, output_score: float) -> float:
        """
        多维耦合模型：输入权重0.4，输出权重0.6
        （输出风险通常更严重）
        """
        # 如果输出为空，只看输入
        if output_score is None:
            return prompt_score
        
        # 综合评分（输出权重更高）
        combined = prompt_score * 0.4 + output_score * 0.6
        return min(combined, 100)
    
    def _get_highest_severity_rule(self, detected_rules: list) -> Optional[dict]:
        severity_order = {"critical": 5, "high": 4, "medium": 3, "low": 2, "safe": 1}
        if not detected_rules:
            return None
        return max(detected_rules, key=lambda r: severity_order.get(r.get("severity", ""), 0))
    
    def _determine_action(
        self,
        score: float,
        highest_rule: Optional[dict],
        detected_rules: list
    ) -> Tuple[str, str]:
        """根据风险评分和规则决定熔断动作"""
        
        # 规则优先：特定规则触发特定动作
        rule_actions = {
            "RULE_AI_001": ("refuse", "涉密信息查询，已拒绝并记录审计"),
            "RULE_AI_007": ("refuse", "诱导泄密检测，已拒绝并警告"),
            "RULE_AI_002": ("human_review", "政策误导风险，已转人工审核"),
        }
        
        if highest_rule:
            rule_id = highest_rule.get("rule_id", "")
            if rule_id in rule_actions:
                return rule_actions[rule_id]
        
        # 分数驱动
        if score >= 80:
            return "refuse", "高风险内容，已拒绝回答"
        elif score >= 65:
            return "human_review", "风险较高，已转人工审核"
        elif score >= 50:
            return "mask", "存在风险内容，已部分屏蔽"
        elif score >= 30:
            return "warn", "注意：内容存在轻微风险，已记录"
        else:
            return "allow", "审核通过"
    
    def _update_session_risk(self, session_id: str, score: float):
        if score >= 50:
            current = self._session_high_risk_count.get(session_id, 0)
            self._session_high_risk_count[session_id] = current + 1
        else:
            # 正常交互则重置计数
            self._session_high_risk_count[session_id] = 0
    
    def block_session(self, session_id: str, minutes: int = 30):
        """手动封禁会话"""
        from datetime import timedelta
        self._session_blocked_until[session_id] = datetime.now() + timedelta(minutes=minutes)
        self._session_high_risk_count[session_id] = 0
    
    def unblock_session(self, session_id: str):
        """解除会话封禁"""
        if session_id in self._session_blocked_until:
            del self._session_blocked_until[session_id]
        if session_id in self._session_high_risk_count:
            del self._session_high_risk_count[session_id]
    
    def get_fuse_level(self, fuse_action: str) -> int:
        """获取熔断等级数值"""
        levels = {
            "allow": 0, "warn": 1, "mask": 2,
            "refuse": 3, "human_review": 4, "block": 5
        }
        return levels.get(fuse_action, 0)