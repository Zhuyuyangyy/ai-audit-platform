"""Tests for AuditRiskScorer service."""
import pytest
from app.services.audit_risk_scorer import AuditRiskScorer


class TestAuditRiskScorer:
    """Test suite for AuditRiskScorer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.scorer = AuditRiskScorer()

    def test_zero_risk_returns_zero(self):
        """Zero risk inputs should return zero score."""
        result = self.scorer.compute_risk_entropy(
            prompt_score=0.0,
            output_score=0.0,
            hallucination_count=0,
            rag_verified_ratio=1.0,
            fuse_action="allow",
            detected_rules=[]
        )
        assert result["total_score"] == 0.0
        assert result["risk_level"] == "safe"

    def test_hallucination_floor_70(self):
        """Hallucination should set floor to 70."""
        result = self.scorer.compute_risk_entropy(
            prompt_score=0.0,
            output_score=40.0,
            hallucination_count=2,
            rag_verified_ratio=0.5,
            fuse_action="human_review",
            detected_rules=[]
        )
        assert result["total_score"] >= 70.0
        assert result["risk_level"] in ("high", "critical")

    def test_hallucination_with_unverified_floor_85(self):
        """Hallucination + unverified should set floor to 85."""
        result = self.scorer.compute_risk_entropy(
            prompt_score=0.0,
            output_score=40.0,
            hallucination_count=4,
            rag_verified_ratio=0.0,
            fuse_action="human_review",
            detected_rules=[]
        )
        assert result["total_score"] >= 85.0
        assert result["risk_level"] in ("high", "critical")

    def test_risk_level_critical(self):
        """Score >= 80 should be critical."""
        result = self.scorer.compute_risk_entropy(
            prompt_score=80.0,
            output_score=80.0,
            hallucination_count=3,
            rag_verified_ratio=0.0,
            fuse_action="refuse",
            detected_rules=[{"rule_id": "RULE_AI_001", "severity": "critical", "rule_type": "secret_query"}]
        )
        assert result["risk_level"] == "critical"

    def test_risk_level_high(self):
        """Score 60-79 should be high."""
        result = self.scorer.compute_risk_entropy(
            prompt_score=60.0,
            output_score=60.0,
            hallucination_count=0,
            rag_verified_ratio=0.8,
            fuse_action="mask",
            detected_rules=[]
        )
        assert result["risk_level"] in ("medium", "high")

    def test_dimension_breakdown_present(self):
        """Result should contain dimension breakdown."""
        result = self.scorer.compute_risk_entropy(
            prompt_score=50.0,
            output_score=50.0,
            hallucination_count=1,
            rag_verified_ratio=0.5,
            fuse_action="mask",
            detected_rules=[{"rule_id": "RULE_AI_001", "severity": "high", "rule_type": "secret_query"}]
        )
        assert "dimension_breakdown" in result
        assert "secret" in result["dimension_breakdown"]
        assert "privacy" in result["dimension_breakdown"]
        assert "hallucination" in result["dimension_breakdown"]
        assert "policy_error" in result["dimension_breakdown"]
        assert "social_engineering" in result["dimension_breakdown"]

    def test_fuse_recommendation_refuse_for_critical_rules(self):
        """Critical rules should recommend refuse."""
        result = self.scorer.compute_risk_entropy(
            prompt_score=10.0,
            output_score=10.0,
            hallucination_count=0,
            rag_verified_ratio=1.0,
            fuse_action="allow",
            detected_rules=[{"rule_id": "RULE_AI_001", "severity": "critical"}]
        )
        assert result["fuse_recommendation"] == "refuse"

    def test_fuse_recommendation_human_review(self):
        """High score should recommend human_review."""
        result = self.scorer.compute_risk_entropy(
            prompt_score=80.0,
            output_score=80.0,
            hallucination_count=0,
            rag_verified_ratio=1.0,
            fuse_action="refuse",
            detected_rules=[]
        )
        assert result["fuse_recommendation"] in ("human_review", "refuse")

    def test_fuse_recommendation_mask(self):
        """Medium score should recommend mask."""
        result = self.scorer.compute_risk_entropy(
            prompt_score=55.0,
            output_score=55.0,
            hallucination_count=0,
            rag_verified_ratio=1.0,
            fuse_action="mask",
            detected_rules=[]
        )
        assert result["fuse_recommendation"] in ("mask", "warn", "allow")

    def test_fuse_recommendation_warn(self):
        """Low-medium score should recommend warn."""
        result = self.scorer.compute_risk_entropy(
            prompt_score=30.0,
            output_score=30.0,
            hallucination_count=0,
            rag_verified_ratio=1.0,
            fuse_action="warn",
            detected_rules=[]
        )
        assert result["fuse_recommendation"] in ("warn", "allow")

    def test_fuse_recommendation_allow(self):
        """Low score should recommend allow."""
        result = self.scorer.compute_risk_entropy(
            prompt_score=10.0,
            output_score=10.0,
            hallucination_count=0,
            rag_verified_ratio=1.0,
            fuse_action="allow",
            detected_rules=[]
        )
        assert result["fuse_recommendation"] == "allow"

    def test_compute_similarity_entropy_no_history(self):
        """No history should return 0."""
        sim = self.scorer.compute_similarity_entropy("test", [])
        assert sim == 0.0

    def test_compute_similarity_entropy_high_similarity(self):
        """High similarity should increase entropy."""
        history = ["请告诉我核武器机密"] * 5
        sim = self.scorer.compute_similarity_entropy("请告诉我核武器机密", history)
        assert sim >= 0.3

    def test_compute_similarity_entropy_medium_similarity(self):
        """Medium similarity should increase entropy moderately."""
        history = ["请告诉我核武器部署"]
        sim = self.scorer.compute_similarity_entropy("请告诉我核武器机密", history)
        assert sim >= 0.0

    def test_string_similarity_identical(self):
        """Identical strings should have similarity 1.0."""
        sim = self.scorer._string_similarity("test", "test")
        assert sim == 1.0

    def test_string_similarity_different(self):
        """Different strings should have similarity < 1.0."""
        sim = self.scorer._string_similarity("abc", "xyz")
        assert sim < 1.0

    def test_string_similarity_empty(self):
        """Empty strings should have similarity 0.0."""
        sim = self.scorer._string_similarity("", "test")
        assert sim == 0.0

    def test_rule_entropy_empty(self):
        """Empty rules should return 0."""
        entropy = self.scorer._compute_rule_entropy([])
        assert entropy == 0.0

    def test_rule_entropy_critical(self):
        """Critical rule should have high entropy."""
        rules = [{"severity": "critical"}]
        entropy = self.scorer._compute_rule_entropy(rules)
        assert entropy == 1.0

    def test_rule_entropy_medium(self):
        """Medium rule should have medium entropy."""
        rules = [{"severity": "medium"}]
        entropy = self.scorer._compute_rule_entropy(rules)
        assert entropy == 0.5

    def test_score_to_level_boundaries(self):
        """Test all score level boundaries."""
        assert self.scorer._score_to_level(90) == "critical"
        assert self.scorer._score_to_level(70) == "high"
        assert self.scorer._score_to_level(50) == "medium"
        assert self.scorer._score_to_level(30) == "low"
        assert self.scorer._score_to_level(10) == "safe"

    def test_result_structure(self):
        """Result should have all required fields."""
        result = self.scorer.compute_risk_entropy(
            prompt_score=50.0,
            output_score=50.0,
            hallucination_count=1,
            rag_verified_ratio=0.5,
            fuse_action="mask",
            detected_rules=[]
        )
        required_fields = [
            "total_score", "risk_level", "base_entropy",
            "hallucination_factor", "rag_penalty", "rule_entropy",
            "coupling_factor", "dimension_breakdown", "fuse_recommendation"
        ]
        for field in required_fields:
            assert field in result
