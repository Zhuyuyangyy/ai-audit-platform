# Prompt Risk Detector
# Detects sensitive questions, unauthorized queries, and leaks

import re
import json
from typing import List, Dict, Tuple

class PromptRiskDetector:
    
    # 涉密关键词（简化版示例）
    SECRET_KEYWORDS = [
        "核武器", "导弹射程", "军事机密", "情报人员", "间谍活动",
        "机密文件", "秘密任务", "武装部队", "国防预算", "军事部署",
        "机密资料", "保密信息", "泄露", "获取情报"
    ]
    
    # 隐私诱导关键词
    PRIVACY_INDUCE_KEYWORDS = [
        "你的身份证号", "你的银行密码", "你的住址", "你家人信息",
        "个人隐私", "工资收入", "病例信息", "犯罪记录"
    ]
    
    # 政策误导诱导
    POLICY_MISLEAD_PATTERNS = [
        r"据说.*政策.*可以.*",
        r"是不是.*就不算.*违规",
        r"如果.*会不会.*法律.*",
        r"规定.*是不是.*可以.*绕过"
    ]
    
    # 越权试探
    UNAUTHORIZED_PATTERNS = [
        r"(部长|局长|处长|主任).*怎么说",
        r"内部.*规定",
        r"上层.*指示",
        r"领导.*说了"
    ]
    
    def __init__(self):
        self.last_score = 0.0
        self.last_detected = []
    
    def detect(self, prompt: str, user_role: str = "citizen") -> Tuple[float, List[Dict], str]:
        """
        Returns: (risk_score, detected_rules, fuse_action)
        """
        prompt_lower = prompt.lower()
        detected = []
        score = 0.0
        
        # RULE_AI_001: 涉密信息检测
        secret_hits = [kw for kw in self.SECRET_KEYWORDS if kw in prompt]
        if secret_hits:
            detected.append({
                "rule_id": "RULE_AI_001",
                "rule_type": "secret_query",
                "matched_keywords": secret_hits,
                "description": "涉密信息查询"
            })
            score += 45
        
        # RULE_AI_003: 隐私泄露诱导
        privacy_hits = [kw for kw in self.PRIVACY_INDUCE_KEYWORDS if kw in prompt]
        if privacy_hits:
            detected.append({
                "rule_id": "RULE_AI_003",
                "rule_type": "privacy_leak_induce",
                "matched_keywords": privacy_hits,
                "description": "隐私数据泄露诱导"
            })
            score += 35
        
        # RULE_AI_007: 诱导泄密检测
        if any(re.search(p, prompt) for p in self.POLICY_MISLEAD_PATTERNS):
            detected.append({
                "rule_id": "RULE_AI_007",
                "rule_type": "leak_induce",
                "matched_patterns": [p for p in self.POLICY_MISLEAD_PATTERNS if re.search(p, prompt)],
                "description": "诱导泄密问题（社会工程学）"
            })
            score += 40
        
        # RULE_AI_005: 越权回答试探
        if any(re.search(p, prompt) for p in self.UNAUTHORIZED_PATTERNS):
            detected.append({
                "rule_id": "RULE_AI_005",
                "rule_type": "unauthorized_answer",
                "matched_patterns": [p for p in self.UNAUTHORIZED_PATTERNS if re.search(p, prompt)],
                "description": "越权回答试探"
            })
            score += 25
        
        # RULE_AI_006: 政策错误解读诱导
        policy_mislead_phrases = ["是不是可以理解为", "是不是意味着", "政策是否允许"]
        if any(phrase in prompt for phrase in policy_mislead_phrases):
            detected.append({
                "rule_id": "RULE_AI_006",
                "rule_type": "policy_error_interpret",
                "description": "政策错误解读诱导"
            })
            score += 30
        
        # 计算最终风险分数（限制在100以内）
        score = min(score, 100)
        
        # 确定熔断动作
        fuse_action = self._determine_fuse_action(score, detected)
        
        self.last_score = score
        self.last_detected = detected
        
        return score, detected, fuse_action
    
    def _determine_fuse_action(self, score: float, detected: List[Dict]) -> str:
        if score >= 80 or any(d["rule_id"] in ("RULE_AI_001", "RULE_AI_007") for d in detected):
            return "refuse"
        elif score >= 60:
            return "human_review"
        elif score >= 40:
            return "warn"
        elif score >= 20:
            return "mask"
        else:
            return "allow"
    
    def get_risk_level(self, score: float) -> str:
        if score >= 80:
            return "critical"
        elif score >= 60:
            return "high"
        elif score >= 40:
            return "medium"
        elif score >= 20:
            return "low"
        else:
            return "safe"