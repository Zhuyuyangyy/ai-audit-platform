"""Tests for ModelAuditLogger service."""
import pytest
import sqlite3
import os
from app.services.model_audit_logger import ModelAuditLogger


class TestModelAuditLogger:
    """Test suite for ModelAuditLogger."""

    @pytest.fixture
    def logger(self, tmp_path):
        """Create logger with temporary database."""
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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rag_trace (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_id INTEGER NOT NULL,
                claim TEXT,
                evidence TEXT,
                policy_doc_id INTEGER,
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fuse_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_id INTEGER NOT NULL,
                fuse_reason TEXT,
                action_taken TEXT,
                created_at TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()

        return ModelAuditLogger(db_path)

    def test_log_interaction(self, logger, sample_user_id, sample_session_id, sample_prompt):
        """Should log interaction successfully."""
        log_id = logger.log_interaction(
            user_id=sample_user_id,
            session_id=sample_session_id,
            prompt=sample_prompt,
            output=None,
            risk_score=10.0,
            risk_level="safe",
            fuse_action="allow"
        )
        assert log_id is not None
        assert log_id > 0

    def test_log_interaction_with_rules(self, logger, sample_user_id, sample_session_id, sample_prompt):
        """Should log interaction with rules."""
        rules = [{"rule_id": "RULE_AI_001", "description": "涉密信息查询"}]
        log_id = logger.log_interaction(
            user_id=sample_user_id,
            session_id=sample_session_id,
            prompt=sample_prompt,
            output=None,
            risk_score=10.0,
            risk_level="safe",
            fuse_action="allow",
            prompt_rules=rules
        )
        assert log_id is not None

    def test_log_rag_trace(self, logger, sample_user_id, sample_session_id, sample_prompt):
        """Should log RAG trace."""
        log_id = logger.log_interaction(
            user_id=sample_user_id,
            session_id=sample_session_id,
            prompt=sample_prompt,
            output=None,
            risk_score=10.0,
            risk_level="safe",
            fuse_action="allow"
        )

        logger.log_rag_trace(
            audit_id=log_id,
            claim="测试声明",
            evidence="测试证据",
            policy_doc_id=1
        )

        # Verify trace was logged
        conn = sqlite3.connect(logger.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM rag_trace WHERE audit_id = ?", (log_id,))
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 1

    def test_log_fuse_action(self, logger, sample_user_id, sample_session_id, sample_prompt):
        """Should log fuse action."""
        log_id = logger.log_interaction(
            user_id=sample_user_id,
            session_id=sample_session_id,
            prompt=sample_prompt,
            output=None,
            risk_score=10.0,
            risk_level="safe",
            fuse_action="allow"
        )

        logger.log_fuse_action(
            audit_id=log_id,
            fuse_reason="测试熔断原因",
            action_taken="refuse"
        )

        # Verify fuse action was logged
        conn = sqlite3.connect(logger.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM fuse_records WHERE audit_id = ?", (log_id,))
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 1

    def test_get_audit_log(self, logger, sample_user_id, sample_session_id, sample_prompt):
        """Should get audit log by ID."""
        log_id = logger.log_interaction(
            user_id=sample_user_id,
            session_id=sample_session_id,
            prompt=sample_prompt,
            output=None,
            risk_score=10.0,
            risk_level="safe",
            fuse_action="allow"
        )

        log = logger.get_audit_log(log_id)
        assert log is not None
        assert log["user_id"] == sample_user_id
        assert log["session_id"] == sample_session_id
        assert log["prompt"] == sample_prompt

    def test_get_audit_log_not_found(self, logger):
        """Should return None for nonexistent log."""
        log = logger.get_audit_log(999)
        assert log is None

    def test_get_session_logs(self, logger, sample_user_id, sample_session_id, sample_prompt):
        """Should get all logs for a session."""
        # Log multiple interactions
        for i in range(3):
            logger.log_interaction(
                user_id=sample_user_id,
                session_id=sample_session_id,
                prompt=f"{sample_prompt} {i}",
                output=None,
                risk_score=10.0,
                risk_level="safe",
                fuse_action="allow"
            )

        logs = logger.get_session_logs(sample_session_id)
        assert len(logs) == 3

    def test_get_session_logs_empty(self, logger):
        """Should return empty list for nonexistent session."""
        logs = logger.get_session_logs("nonexistent_session")
        assert len(logs) == 0

    def test_update_output(self, logger, sample_user_id, sample_session_id, sample_prompt):
        """Should update output for existing log."""
        log_id = logger.log_interaction(
            user_id=sample_user_id,
            session_id=sample_session_id,
            prompt=sample_prompt,
            output=None,
            risk_score=10.0,
            risk_level="safe",
            fuse_action="allow"
        )

        logger.update_output(
            log_id=log_id,
            output="测试输出",
            risk_score=20.0,
            risk_level="low",
            fuse_action="warn"
        )

        log = logger.get_audit_log(log_id)
        assert log["output"] == "测试输出"
        assert log["risk_score"] == 20.0
        assert log["risk_level"] == "low"
        assert log["fuse_action"] == "warn"

    def test_log_interaction_with_rag_trace(self, logger, sample_user_id, sample_session_id, sample_prompt):
        """Should log interaction with RAG trace."""
        rag_trace = [
            {"claim": "声明1", "evidence": "证据1", "policy_doc_id": 1},
            {"claim": "声明2", "evidence": "证据2", "policy_doc_id": 2}
        ]
        log_id = logger.log_interaction(
            user_id=sample_user_id,
            session_id=sample_session_id,
            prompt=sample_prompt,
            output=None,
            risk_score=10.0,
            risk_level="safe",
            fuse_action="allow",
            rag_trace=rag_trace
        )
        assert log_id is not None

    def test_multiple_sessions(self, logger, sample_user_id, sample_prompt):
        """Should handle multiple sessions."""
        session1 = "session_1"
        session2 = "session_2"

        logger.log_interaction(
            user_id=sample_user_id,
            session_id=session1,
            prompt=sample_prompt,
            output=None,
            risk_score=10.0,
            risk_level="safe",
            fuse_action="allow"
        )

        logger.log_interaction(
            user_id=sample_user_id,
            session_id=session2,
            prompt=sample_prompt,
            output=None,
            risk_score=20.0,
            risk_level="low",
            fuse_action="warn"
        )

        logs1 = logger.get_session_logs(session1)
        logs2 = logger.get_session_logs(session2)
        assert len(logs1) == 1
        assert len(logs2) == 1
