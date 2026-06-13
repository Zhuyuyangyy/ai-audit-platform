"""Tests for ReportGenerator service."""
import pytest
import sqlite3
import json
from datetime import datetime
from app.services.report_generator import ReportGenerator


class TestReportGenerator:
    """Test suite for ReportGenerator."""

    @pytest.fixture
    def generator(self, tmp_path):
        """Create generator with temporary database."""
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                prompt TEXT,
                output TEXT,
                risk_score REAL DEFAULT 0,
                risk_level TEXT DEFAULT 'safe',
                fuse_action TEXT DEFAULT 'allow',
                prompt_rules TEXT,
                output_rules TEXT,
                rag_trace TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # Insert test data
        session_id = "test_session_001"
        for i in range(5):
            cursor.execute("""
                INSERT INTO audit_logs (user_id, session_id, prompt, output, risk_score, risk_level, fuse_action, prompt_rules, output_rules, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "user1",
                session_id,
                f"prompt {i}",
                f"output {i}",
                10.0 + i * 20,
                ["safe", "low", "medium", "high", "critical"][i],
                ["allow", "warn", "mask", "human_review", "refuse"][i],
                json.dumps([{"rule_id": f"RULE_{i}", "description": f"规则{i}"}]),
                "[]",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

        conn.commit()
        conn.close()

        return ReportGenerator(db_path)

    def test_generate_session_report(self, generator):
        """Should generate session report."""
        report = generator.generate_session_report("test_session_001")
        assert "error" not in report
        assert report["session_id"] == "test_session_001"
        assert report["total_interactions"] == 5

    def test_generate_session_report_not_found(self, generator):
        """Should return error for nonexistent session."""
        report = generator.generate_session_report("nonexistent")
        assert "error" in report

    def test_report_avg_risk_score(self, generator):
        """Report should contain average risk score."""
        report = generator.generate_session_report("test_session_001")
        assert "avg_risk_score" in report
        assert report["avg_risk_score"] > 0

    def test_report_risk_distribution(self, generator):
        """Report should contain risk distribution."""
        report = generator.generate_session_report("test_session_001")
        assert "risk_distribution" in report
        assert "safe" in report["risk_distribution"]
        assert "low" in report["risk_distribution"]
        assert "medium" in report["risk_distribution"]
        assert "high" in report["risk_distribution"]
        assert "critical" in report["risk_distribution"]

    def test_report_fuse_actions_summary(self, generator):
        """Report should contain fuse actions summary."""
        report = generator.generate_session_report("test_session_001")
        assert "fuse_actions_summary" in report
        assert "allow" in report["fuse_actions_summary"]
        assert "warn" in report["fuse_actions_summary"]

    def test_report_policy_doc_references(self, generator):
        """Report should contain policy document references."""
        report = generator.generate_session_report("test_session_001")
        assert "policy_doc_references" in report

    def test_report_warnings(self, generator):
        """Report should contain warnings."""
        report = generator.generate_session_report("test_session_001")
        assert "warnings" in report
        assert len(report["warnings"]) > 0

    def test_report_generated_at(self, generator):
        """Report should contain generation timestamp."""
        report = generator.generate_session_report("test_session_001")
        assert "generated_at" in report

    def test_report_interactions(self, generator):
        """Report should contain interactions list."""
        report = generator.generate_session_report("test_session_001")
        assert "interactions" in report
        assert len(report["interactions"]) == 5

    def test_report_interaction_structure(self, generator):
        """Interaction should have all required fields."""
        report = generator.generate_session_report("test_session_001")
        interaction = report["interactions"][0]
        required_fields = ["id", "user_id", "prompt", "output", "risk_score", "risk_level", "fuse_action", "created_at"]
        for field in required_fields:
            assert field in interaction

    def test_safe_json_load_valid(self, generator):
        """Should parse valid JSON."""
        result = generator._safe_json_load('[{"key": "value"}]')
        assert isinstance(result, list)
        assert len(result) == 1

    def test_safe_json_load_invalid(self, generator):
        """Should return empty list for invalid JSON."""
        result = generator._safe_json_load("invalid json")
        assert result == []

    def test_safe_json_load_none(self, generator):
        """Should return empty list for None."""
        result = generator._safe_json_load(None)
        assert result == []

    def test_collect_policy_references(self, generator):
        """Should collect policy references from rows."""
        rows = [
            (1, "user1", "session1", "prompt", "output", 10.0, "safe", "allow",
             json.dumps([{"description": "规则1"}, {"description": "规则2"}]), "[]", "2024-01-01"),
            (2, "user1", "session1", "prompt", "output", 20.0, "low", "warn",
             json.dumps([{"description": "规则1"}]), "[]", "2024-01-01")
        ]
        refs = generator._collect_policy_references(rows)
        assert "规则1" in refs
        assert "规则2" in refs

    def test_generate_warnings_high_risk_ratio(self, generator):
        """Should warn when high-risk ratio > 30%."""
        rows = [
            (1, "user1", "session1", "prompt", "output", 80.0, "critical", "refuse", "[]", "[]", "2024-01-01"),
            (2, "user1", "session1", "prompt", "output", 70.0, "high", "human_review", "[]", "[]", "2024-01-01"),
            (3, "user1", "session1", "prompt", "output", 10.0, "safe", "allow", "[]", "[]", "2024-01-01")
        ]
        warnings = generator._generate_warnings(rows, 50.0)
        assert any("高风险" in w for w in warnings)

    def test_generate_warnings_high_avg_score(self, generator):
        """Should warn when average score > 60."""
        rows = [
            (1, "user1", "session1", "prompt", "output", 70.0, "high", "human_review", "[]", "[]", "2024-01-01")
        ]
        warnings = generator._generate_warnings(rows, 70.0)
        assert any("偏高" in w for w in warnings)

    def test_generate_warnings_refuse_actions(self, generator):
        """Should warn when refuse/block actions exist."""
        rows = [
            (1, "user1", "session1", "prompt", "output", 80.0, "critical", "refuse", "[]", "[]", "2024-01-01")
        ]
        warnings = generator._generate_warnings(rows, 50.0)
        assert any("拒绝" in w or "熔断" in w for w in warnings)

    def test_generate_daily_report(self, generator):
        """Should generate daily report."""
        report = generator.generate_daily_report()
        assert "date" in report
        assert "total_interactions" in report
        assert "avg_risk_score" in report
        assert "high_critical_count" in report
        assert "refused_count" in report

    def test_export_json(self, generator):
        """Should export report as JSON string."""
        json_str = generator.export_json("test_session_001")
        report = json.loads(json_str)
        assert report["session_id"] == "test_session_001"
