"""Tests for RAGTracer service."""
import pytest
import sqlite3
import os
from app.services.rag_tracer import RAGTracer


class TestRAGTracer:
    """Test suite for RAGTracer."""

    @pytest.fixture
    def tracer(self, tmp_path):
        """Create tracer with temporary database."""
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS policy_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT,
                source TEXT,
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                chunk_text TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # Insert test data
        cursor.execute("""
            INSERT INTO policy_documents (title, content, source, created_at)
            VALUES (?, ?, ?, ?)
        """, ("个人信息保护法", "处理个人信息应当遵循合法、正当、必要和诚信原则", "全国人大", "2021-08-20"))

        cursor.execute("""
            INSERT INTO policy_documents (title, content, source, created_at)
            VALUES (?, ?, ?, ?)
        """, ("数据安全法", "开展数据处理活动应当加强风险监测", "全国人大", "2021-06-10"))

        cursor.execute("""
            INSERT INTO document_chunks (document_id, chunk_text, created_at)
            VALUES (?, ?, ?)
        """, (1, "处理个人信息应当遵循合法、正当、必要和诚信原则", "2021-08-20"))

        conn.commit()
        conn.close()

        return RAGTracer(db_path)

    def test_trace_finds_policy_docs(self, tracer):
        """Trace should find relevant policy documents."""
        output = "处理个人信息应当遵循合法、正当、必要和诚信原则"
        traces = tracer.trace(output)

        verified_traces = [t for t in traces if t.get("policy_doc_id") is not None]
        assert len(verified_traces) >= 1

    def test_trace_marks_unverified(self, tracer):
        """Unverifiable claims should be marked unverified."""
        output = "这是一句完全无关的话，没有任何政策依据"
        traces = tracer.trace(output)

        unverified_traces = [t for t in traces if t.get("status") == "unverified"]
        assert len(unverified_traces) >= 1

    def test_trace_returns_empty_for_empty_input(self, tracer):
        """Empty input should return empty traces."""
        traces = tracer.trace("")
        assert len(traces) == 0

    def test_trace_returns_empty_for_short_input(self, tracer):
        """Short input should return empty traces."""
        traces = tracer.trace("短")
        assert len(traces) == 0

    def test_verify_claim_valid(self, tracer):
        """Valid claim should be verified."""
        is_valid, message = tracer.verify_claim(
            "处理个人信息应当遵循合法原则",
            1
        )
        assert is_valid is True
        assert "验证通过" in message

    def test_verify_claim_invalid(self, tracer):
        """Invalid claim should not be verified."""
        is_valid, message = tracer.verify_claim(
            "完全无关的内容",
            1
        )
        assert is_valid is False

    def test_verify_claim_nonexistent_doc(self, tracer):
        """Nonexistent document should return error."""
        is_valid, message = tracer.verify_claim("test", 999)
        assert is_valid is False
        assert "不存在" in message

    def test_extract_keywords(self, tracer):
        """Keywords should be extracted from text."""
        keywords = tracer._extract_keywords("处理个人信息应当遵循合法原则")
        assert len(keywords) > 0
        assert all(len(k) >= 2 for k in keywords)

    def test_extract_keywords_removes_stop_words(self, tracer):
        """Stop words should be removed."""
        keywords = tracer._extract_keywords("的了是在有和就不人都一")
        # Most should be filtered as stop words
        assert len(keywords) == 0 or all(k not in {"的", "了", "是", "在"} for k in keywords)

    def test_extract_keywords_max_limit(self, tracer):
        """Keywords should be limited to 8."""
        text = "关键词1 关键词2 关键词3 关键词4 关键词5 关键词6 关键词7 关键词8 关键词9 关键词10"
        keywords = tracer._extract_keywords(text)
        assert len(keywords) <= 8

    def test_split_sentences(self, tracer):
        """Sentences should be split correctly."""
        sentences = tracer._split_sentences("第一句。第二句！第三句？")
        assert len(sentences) == 3

    def test_split_sentences_with_newlines(self, tracer):
        """Sentences should be split by newlines."""
        sentences = tracer._split_sentences("第一句\n第二句\n第三句")
        assert len(sentences) == 3

    def test_find_relevant_docs_chunk_match(self, tracer):
        """Should find docs from document_chunks."""
        output = "处理个人信息应当遵循合法原则"
        traces = tracer.trace(output)
        chunk_traces = [t for t in traces if t.get("policy_doc_id") == 1]
        assert len(chunk_traces) >= 1

    def test_trace_confidence_score(self, tracer):
        """Traces should have confidence score."""
        output = "处理个人信息应当遵循合法原则"
        traces = tracer.trace(output)
        for trace in traces:
            assert "confidence" in trace
            assert 0 <= trace["confidence"] <= 1

    def test_trace_multiple_sentences(self, tracer):
        """Multiple sentences should produce multiple traces."""
        output = "第一句关于个人信息保护。第二句关于数据安全。"
        traces = tracer.trace(output)
        assert len(traces) >= 2
