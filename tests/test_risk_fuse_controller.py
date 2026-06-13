"""Tests for RiskFuseController service."""
import pytest
from datetime import datetime, timedelta
from app.services.risk_fuse_controller import RiskFuseController, FuseLevel


class TestRiskFuseController:
    """Test suite for RiskFuseController."""

    def setup_method(self):
        """Set up test fixtures."""
        self.controller = RiskFuseController()

    def test_safe_interaction_returns_allow(self, sample_session_id):
        """Safe interaction should return allow."""
        action, comment, _ = self.controller.evaluate(
            prompt_score=0.0,
            output_score=0.0,
            detected_rules=[],
            session_id=sample_session_id,
            user_role="citizen",
            has_hallucination=False,
            unverified_claim_count=0
        )
        assert action == "allow"

    def test_hallucination_forces_human_review(self, sample_session_id):
        """Hallucination should force human_review."""
        action, comment, _ = self.controller.evaluate(
            prompt_score=0.0,
            output_score=40.0,
            detected_rules=[],
            session_id=sample_session_id,
            user_role="citizen",
            has_hallucination=True,
            unverified_claim_count=0
        )
        assert action == "human_review"
        assert "幻觉" in comment

    def test_hallucination_with_unverified_forces_human_review(self, sample_session_id):
        """Hallucination + unverified claim should force human_review."""
        action, comment, suggestion = self.controller.evaluate(
            prompt_score=0.0,
            output_score=40.0,
            detected_rules=[],
            session_id=sample_session_id,
            user_role="citizen",
            has_hallucination=True,
            unverified_claim_count=1
        )
        assert action == "human_review"
        assert "HARD_GATE" in suggestion

    def test_high_score_triggers_refuse(self, sample_session_id):
        """High score should trigger refuse."""
        action, _, _ = self.controller.evaluate(
            prompt_score=80.0,
            output_score=80.0,
            detected_rules=[],
            session_id=sample_session_id,
            user_role="citizen",
            has_hallucination=False,
            unverified_claim_count=0
        )
        assert action == "refuse"

    def test_medium_score_triggers_mask(self, sample_session_id):
        """Medium score should trigger mask."""
        action, _, _ = self.controller.evaluate(
            prompt_score=50.0,
            output_score=50.0,
            detected_rules=[],
            session_id=sample_session_id,
            user_role="citizen",
            has_hallucination=False,
            unverified_claim_count=0
        )
        assert action == "mask"

    def test_low_score_triggers_warn(self, sample_session_id):
        """Low score should trigger warn."""
        action, _, _ = self.controller.evaluate(
            prompt_score=30.0,
            output_score=30.0,
            detected_rules=[],
            session_id=sample_session_id,
            user_role="citizen",
            has_hallucination=False,
            unverified_claim_count=0
        )
        assert action == "warn"

    def test_critical_rule_triggers_refuse(self, sample_session_id):
        """Critical rule should trigger refuse."""
        detected_rules = [{"rule_id": "RULE_AI_001", "severity": "critical"}]
        action, _, _ = self.controller.evaluate(
            prompt_score=10.0,
            output_score=10.0,
            detected_rules=detected_rules,
            session_id=sample_session_id,
            user_role="citizen",
            has_hallucination=False,
            unverified_claim_count=0
        )
        assert action == "refuse"

    def test_session_blocked_returns_block(self, sample_session_id):
        """Blocked session should return block."""
        self.controller.block_session(sample_session_id)
        action, comment, suggestion = self.controller.evaluate(
            prompt_score=0.0,
            output_score=0.0,
            detected_rules=[],
            session_id=sample_session_id,
            user_role="citizen",
            has_hallucination=False,
            unverified_claim_count=0
        )
        assert action == "block"
        assert suggestion == "SESSION_BLOCKED"

    def test_consecutive_high_risk_triggers_escalation(self, sample_session_id):
        """3 consecutive high-risk should trigger escalation."""
        for _ in range(3):
            self.controller.evaluate(
                prompt_score=60.0,
                output_score=60.0,
                detected_rules=[],
                session_id=sample_session_id,
                user_role="citizen",
                has_hallucination=False,
                unverified_claim_count=0
            )

        action, _, _ = self.controller.evaluate(
            prompt_score=60.0,
            output_score=60.0,
            detected_rules=[],
            session_id=sample_session_id,
            user_role="citizen",
            has_hallucination=False,
            unverified_claim_count=0
        )
        assert action == "human_review"

    def test_low_risk_resets_counter(self, sample_session_id):
        """Low-risk interaction should reset counter."""
        # First two high-risk
        for _ in range(2):
            self.controller.evaluate(
                prompt_score=60.0,
                output_score=60.0,
                detected_rules=[],
                session_id=sample_session_id,
                user_role="citizen",
                has_hallucination=False,
                unverified_claim_count=0
            )

        # Then low-risk
        self.controller.evaluate(
            prompt_score=10.0,
            output_score=10.0,
            detected_rules=[],
            session_id=sample_session_id,
            user_role="citizen",
            has_hallucination=False,
            unverified_claim_count=0
        )

        # Counter should be reset
        assert self.controller._session_high_risk_count.get(sample_session_id, 0) == 0

    def test_compute_combined_score(self):
        """Test combined score computation."""
        score = self.controller._compute_combined_score(40.0, 60.0)
        assert score == 52.0  # 40*0.4 + 60*0.6

    def test_compute_combined_score_capped(self):
        """Combined score should be capped at 100."""
        score = self.controller._compute_combined_score(100.0, 100.0)
        assert score == 100.0

    def test_compute_combined_score_none_output(self):
        """None output should use prompt score only."""
        score = self.controller._compute_combined_score(40.0, None)
        assert score == 40.0

    def test_get_highest_severity_rule(self):
        """Should return highest severity rule."""
        rules = [
            {"rule_id": "RULE_1", "severity": "low"},
            {"rule_id": "RULE_2", "severity": "critical"},
            {"rule_id": "RULE_3", "severity": "medium"}
        ]
        highest = self.controller._get_highest_severity_rule(rules)
        assert highest["rule_id"] == "RULE_2"

    def test_get_highest_severity_rule_empty(self):
        """Empty rules should return None."""
        highest = self.controller._get_highest_severity_rule([])
        assert highest is None

    def test_block_session(self, sample_session_id):
        """Block session should set blocked until."""
        self.controller.block_session(sample_session_id, minutes=30)
        assert sample_session_id in self.controller._session_blocked_until

    def test_unblock_session(self, sample_session_id):
        """Unblock session should clear blocked state."""
        self.controller.block_session(sample_session_id)
        self.controller.unblock_session(sample_session_id)
        assert sample_session_id not in self.controller._session_blocked_until

    def test_get_fuse_level(self):
        """Test fuse level mapping."""
        assert self.controller.get_fuse_level("allow") == FuseLevel.SAFE
        assert self.controller.get_fuse_level("warn") == FuseLevel.LOW
        assert self.controller.get_fuse_level("mask") == FuseLevel.MEDIUM
        assert self.controller.get_fuse_level("refuse") == FuseLevel.HIGH
        assert self.controller.get_fuse_level("human_review") == FuseLevel.CRITICAL
        assert self.controller.get_fuse_level("block") == FuseLevel.BLOCK

    def test_is_session_blocked_expired(self, sample_session_id):
        """Expired block should not block session."""
        self.controller.block_session(sample_session_id, minutes=-1)
        assert self.controller._is_session_blocked(sample_session_id) is False
