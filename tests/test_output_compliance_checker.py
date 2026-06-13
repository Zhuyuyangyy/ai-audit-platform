"""Tests for OutputComplianceChecker service."""
import pytest
from app.services.output_compliance_checker import OutputComplianceChecker


class TestOutputComplianceChecker:
    """Test suite for OutputComplianceChecker."""

    def setup_method(self):
        """Set up test fixtures."""
        self.checker = OutputComplianceChecker()

    def test_safe_output_returns_zero_score(self, safe_output):
        """Safe output should return zero risk score."""
        score, hallucination_details, policy_binding, has_hallucination = \
            self.checker.check(safe_output)
        assert score == 0.0
        assert has_hallucination is False

    def test_hallucination_detected(self, hallucination_output):
        """Hallucination indicators should be detected."""
        score, hallucination_details, policy_binding, has_hallucination = \
            self.checker.check(hallucination_output)
        assert has_hallucination is True
        assert len(hallucination_details) > 0
        assert score > 0

    def test_high_risk_output_detected(self, high_risk_output):
        """High-risk output should be detected."""
        score, hallucination_details, policy_binding, has_hallucination = \
            self.checker.check(high_risk_output)
        assert score >= 25
        assert has_hallucination is True

    def test_forbidden_pattern_detected(self):
        """Forbidden patterns should be detected."""
        output = "我可以帮你获取机密信息"
        score, hallucination_details, policy_binding, has_hallucination = \
            self.checker.check(output)
        assert score >= 60

    def test_policy_error_detected(self):
        """Policy error patterns should be detected."""
        output = "根据规定可以违规操作"
        score, hallucination_details, policy_binding, has_hallucination = \
            self.checker.check(output)
        assert score >= 40

    def test_unsupported_claims_detected(self):
        """Unsupported claims should be detected."""
        output = "无需额外授权即可处理用户数据"
        score, hallucination_details, policy_binding, has_hallucination = \
            self.checker.check(output)
        assert len(hallucination_details) > 0

    def test_determine_fuse_action_allow(self):
        """Low score should trigger allow action."""
        action = self.checker.determine_fuse_action(10, False)
        assert action == "allow"

    def test_determine_fuse_action_warn(self):
        """Medium score should trigger warn action."""
        action = self.checker.determine_fuse_action(35, False)
        assert action == "warn"

    def test_determine_fuse_action_mask(self):
        """High score should trigger mask action."""
        action = self.checker.determine_fuse_action(55, False)
        assert action == "mask"

    def test_determine_fuse_action_human_review(self):
        """Very high score or hallucination should trigger human_review."""
        action = self.checker.determine_fuse_action(75, False)
        assert action == "human_review"

    def test_determine_fuse_action_human_review_with_hallucination(self):
        """Hallucination should trigger human_review regardless of score."""
        action = self.checker.determine_fuse_action(10, True)
        assert action == "human_review"

    def test_get_risk_level_safe(self):
        """Test risk level classification for safe score."""
        assert self.checker.get_risk_level(10) == "safe"

    def test_get_risk_level_low(self):
        """Test risk level classification for low score."""
        assert self.checker.get_risk_level(20) == "low"

    def test_get_risk_level_medium(self):
        """Test risk level classification for medium score."""
        assert self.checker.get_risk_level(40) == "medium"

    def test_get_risk_level_high(self):
        """Test risk level classification for high score."""
        assert self.checker.get_risk_level(60) == "high"

    def test_get_risk_level_critical(self):
        """Test risk level classification for critical score."""
        assert self.checker.get_risk_level(80) == "critical"

    def test_extract_claims_without_policy(self):
        """Claims without policy support should be extracted."""
        output = "无需额外授权即可处理数据"
        claims = self.checker._extract_claims_without_policy(output)
        assert len(claims) > 0

    def test_score_capped_at_100(self):
        """Score should not exceed 100."""
        output = "我可以帮你获取机密 据内部消息 政策允许违规 无需授权"
        score, _, _, _ = self.checker.check(output)
        assert score <= 100

    def test_policy_binding_for_long_output(self):
        """Long output should have policy binding result."""
        output = "这是一段很长的输出内容" * 10
        score, _, policy_binding, _ = self.checker.check(output)
        assert len(policy_binding) > 0

    def test_hallucination_indicators_comprehensive(self):
        """Multiple hallucination indicators should be detected."""
        output = "据内部消息，有关部门透露，权威人士称，无需额外授权"
        score, hallucination_details, _, has_hallucination = self.checker.check(output)
        assert has_hallucination is True
        assert len(hallucination_details) >= 3
