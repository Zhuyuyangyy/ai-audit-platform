# Audit Risk Scorer
# Multi-dimensional coupling risk entropy model

from typing import Dict, List, Tuple
import math

class AuditRiskScorer:
    """
    风险熵评分器
    基于多维耦合模型计算综合风险熵
    """

    def __init__(self):
        # 维度权重配置
        self.DIM_WEIGHTS = {
            "secret": 0.25,      # 涉密风险
            "privacy": 0.20,     # 隐私风险
            "hallucination": 0.25,  # 幻觉风险
            "policy_error": 0.20,   # 政策错误
            "social_engineering": 0.10  # 社会工程学
        }

    def compute_risk_entropy(
        self,
        prompt_score: float,
        output_score: float,
        hallucination_count: int,
        rag_verified_ratio: float,
        fuse_action: str,
        detected_rules: List[dict]
    ) -> Dict:
        """
        计算风险熵
        返回详细风险分解和综合评分
        """

        # 1. 基础风险熵(输入输出最大者)
        base_entropy = max(prompt_score, output_score or 0) / 100.0

        # 2. 幻觉熵增因子
        hallucination_factor = min(hallucination_count * 0.15, 0.5)

        # 3. RAG溯源缺失惩罚
        rag_penalty = (1.0 - rag_verified_ratio) * 0.3

        # 4. 规则触发熵
        rule_entropy = self._compute_rule_entropy(detected_rules)

        # 5. 耦合因子(时间衰减暂不实现,简化版)
        coupling_factor = 0.0

        # 计算综合风险熵
        raw_entropy = (
            base_entropy * 0.4 +
            hallucination_factor * 0.2 +
            rag_penalty * 0.15 +
            rule_entropy * 0.25
        )

        # 加入耦合因子
        total_entropy = min(raw_entropy + coupling_factor, 1.0)

        # 计算最终风险分（0-100）
        risk_score = round(total_entropy * 100, 2)

        # ===== 硬风险信号分数地板（防止被加权平均稀释）=====
        # 幻觉检测到 → 最低70分
        if hallucination_count > 0:
            risk_score = max(risk_score, 70.0)
        # 无依据claim → 最低60分
        if rag_verified_ratio < 1.0 and hallucination_count == 0:
            # 只有在没有幻觉时才单独惩罚RAG
            pass
        # 幻觉 + 无依据同时 → 最低85分
        if hallucination_count > 0 and rag_verified_ratio < 1.0:
            risk_score = max(risk_score, 85.0)

        # 确定风险等级
        risk_level = self._score_to_level(risk_score)

        # 计算各维度贡献
        dimension_contribution = self._compute_dimension_scores(
            prompt_score, output_score, hallucination_count,
            rag_verified_ratio, detected_rules
        )

        return {
            "total_score": risk_score,
            "risk_level": risk_level,
            "base_entropy": round(base_entropy, 4),
            "hallucination_factor": round(hallucination_factor, 4),
            "rag_penalty": round(rag_penalty, 4),
            "rule_entropy": round(rule_entropy, 4),
            "coupling_factor": round(coupling_factor, 4),
            "dimension_breakdown": dimension_contribution,
            "fuse_recommendation": self._recommend_fuse(risk_score, detected_rules)
        }

    def _compute_rule_entropy(self, detected_rules: List[dict]) -> float:
        """计算规则触发熵"""
        if not detected_rules:
            return 0.0

        severity_scores = {
            "critical": 1.0,
            "high": 0.75,
            "medium": 0.5,
            "low": 0.25,
            "safe": 0.0
        }

        total = sum(severity_scores.get(r.get("severity", "low"), 0.25) for r in detected_rules)
        return min(total / len(detected_rules), 1.0)

    def _compute_dimension_scores(
        self,
        prompt_score: float,
        output_score: float,
        hallucination_count: int,
        rag_verified_ratio: float,
        detected_rules: List[dict]
    ) -> Dict[str, float]:
        """计算各维度风险贡献"""
        dims = {}

        # 涉密维度(从prompt检测到的secret规则)
        secret_score = sum(
            1 for r in detected_rules if r.get("rule_type") == "secret_query"
        )
        dims["secret"] = min(secret_score * 30 + prompt_score * 0.3, 100)

        # 隐私维度
        privacy_score = sum(
            1 for r in detected_rules if r.get("rule_type") == "privacy_leak_induce"
        )
        dims["privacy"] = min(privacy_score * 25 + prompt_score * 0.2, 100)

        # 幻觉维度
        dims["hallucination"] = min(
            hallucination_count * 20 + (1 - rag_verified_ratio) * 50,
            100
        )

        # 政策错误维度
        dims["policy_error"] = sum(
            1 for r in detected_rules if r.get("rule_type") in ("policy_mislead", "policy_error_interpret")
        ) * 30 + (output_score or 0) * 0.3

        # 社会工程学维度
        dims["social_engineering"] = sum(
            1 for r in detected_rules if r.get("rule_type") in ("leak_induce", "unauthorized_answer")
        ) * 20

        return {k: round(min(v, 100), 2) for k, v in dims.items()}

    def _score_to_level(self, score: float) -> str:
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

    def _recommend_fuse(self, score: float, detected_rules: List[dict]) -> str:
        """推荐熔断动作"""
        critical_rules = ["RULE_AI_001", "RULE_AI_007"]
        if any(r.get("rule_id") in critical_rules for r in detected_rules):
            return "refuse"

        if score >= 75:
            return "human_review"
        elif score >= 55:
            return "mask"
        elif score >= 30:
            return "warn"
        else:
            return "allow"

    def compute_similarity_entropy(self, current_prompt: str, historical_prompts: List[str]) -> float:
        """
        计算与历史输入的相似度熵增
        如果用户反复尝试类似的高风险问题,熵增
        """
        if not historical_prompts:
            return 0.0

        max_similarity = 0.0
        for hist in historical_prompts[-5:]:  # 只看最近5条
            sim = self._string_similarity(current_prompt, hist)
            max_similarity = max(max_similarity, sim)

        # 重复度高则熵增
        if max_similarity > 0.8:
            return 0.3
        elif max_similarity > 0.6:
            return 0.15
        return 0.0

    def _string_similarity(self, s1: str, s2: str) -> float:
        """简化版字符串相似度(交集/并集)"""
        set1 = set(s1)
        set2 = set(s2)
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0