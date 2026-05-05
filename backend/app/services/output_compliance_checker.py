# Output Compliance Checker
# Detects policy errors, secrets leaks, hallucinations, value risks

import re
from typing import List, Dict, Tuple

class OutputComplianceChecker:
    
    # 绝对禁区词汇（输出中出现即critical）
    FORBIDDEN_OUTPUT_PATTERNS = [
        r"我可以帮你.*获取.*机密",
        r"告诉你.*内幕.*消息",
        r"教你.*破解.*系统",
        r"如何.*制作.*武器",
    ]
    
    # 幻觉风险指示词（无政策依据时提高风险）
    HALLUCINATION_INDICATORS = [
        "据内部消息", "有关部门透露", "权威人士称",
        "未经公开的信息", "军方内部", "政府文件显示",
        # 反事实断言（无政策依据却语气确定）
        "无需额外授权", "可以自由", "无需获得", "不需要授权",
        "法律允许这样做", "政策支持这么做", "规定允许.*直接",
        "企业可以自由", "个人可随意", "无需经过本人同意"
    ]
    
    # 政策错误解读指示
    POLICY_ERROR_PATTERNS = [
        r"根据.*规定.*可以.*违规",
        r"政策.*允许.*违法",
        r"只要.*就不.*处罚",
    ]
    
    def __init__(self):
        self.last_hallucination_details = []
        self.last_policy_binding = []
    
    def check(self, output: str, audit_id: str = None) -> Tuple[float, List[Dict], List[Dict], bool]:
        """
        Returns: (risk_score, hallucination_details, policy_binding_results, has_hallucination)
        """
        output_lower = output.lower()
        detected = []
        hallucination_details = []
        policy_binding_results = []
        score = 0.0
        
        # RULE_AI_002: 敏感政策误导检测
        for pattern in self.POLICY_ERROR_PATTERNS:
            if re.search(pattern, output):
                detected.append({
                    "rule_id": "RULE_AI_002",
                    "rule_type": "policy_mislead",
                    "matched": pattern,
                    "description": "政策错误解读"
                })
                score += 40
                break
        
        # RULE_AI_004: 幻觉检测
        hallucination_found = False
        for indicator in self.HALLUCINATION_INDICATORS:
            if indicator in output:
                hallucination_found = True
                hallucination_details.append({
                    "indicator": indicator,
                    "risk": "high",
                    "reason": "该表述缺乏政策依据支撑"
                })
        
        # 如果包含绝对禁区词汇，直接critical
        for pattern in self.FORBIDDEN_OUTPUT_PATTERNS:
            if re.search(pattern, output_lower):
                detected.append({
                    "rule_id": "RULE_AI_002",
                    "rule_type": "policy_mislead",
                    "matched": pattern,
                    "description": "敏感政策误导（输出）"
                })
                score += 60
                break
        
        if hallucination_found:
            score += 25
        
        # 无具体政策依据的断言
        unsupported_claims = self._extract_claims_without_policy(output)
        if unsupported_claims:
            hallucination_details.extend(unsupported_claims)
            score += 15
        
        # 限制分数
        score = min(score, 100)
        
        # 检查是否通过RAG溯源（这里简化，真实场景需要调用RAG服务）
        # 所有输出在没有显式证据时标记为"待溯源"
        if len(policy_binding_results) == 0 and len(output) > 50:
            policy_binding_results.append({
                "status": "unverified",
                "message": "输出内容需要RAG溯源验证"
            })
        
        return score, hallucination_details, policy_binding_results, hallucination_found
    
    def _extract_claims_without_policy(self, output: str) -> List[Dict]:
        """提取缺乏政策依据的断言"""
        claims = []
        sentences = output.replace("。", ".\n").replace("？", "?\n").split("\n")
        for s in sentences:
            s = s.strip()
            if len(s) > 10 and any(ind in s for ind in self.HALLUCINATION_INDICATORS):
                claims.append({
                    "claim": s,
                    "status": "unverified",
                    "risk": "medium"
                })
        return claims
    
    def determine_fuse_action(self, score: float, hallucination_found: bool) -> str:
        if score >= 70 or hallucination_found:
            return "human_review"
        elif score >= 50:
            return "mask"
        elif score >= 30:
            return "warn"
        else:
            return "allow"
    
    def get_risk_level(self, score: float) -> str:
        if score >= 70:
            return "critical"
        elif score >= 50:
            return "high"
        elif score >= 30:
            return "medium"
        elif score >= 15:
            return "low"
        else:
            return "safe"