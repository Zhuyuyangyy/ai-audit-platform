"""Tests for API routes."""
import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from fastapi.testclient import TestClient
from app.main import app


class TestAPIRoutes:
    """Test suite for API routes."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_health_endpoint(self, client):
        """Health endpoint should return ok."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "AI Audit Platform"

    def test_root_endpoint(self, client):
        """Root endpoint should return service info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data

    def test_audit_prompt_safe(self, client):
        """Safe prompt should return low risk."""
        response = client.post("/api/v1/audit_prompt", json={
            "user_id": "test_user",
            "session_id": "test_session",
            "prompt": "请问个人信息保护法对企业数据处理有什么要求？",
            "user_role": "citizen"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is True
        assert data["risk_score"] < 20
        assert data["fuse_action"] == "allow"

    def test_audit_prompt_high_risk(self, client):
        """High-risk prompt should be refused."""
        response = client.post("/api/v1/audit_prompt", json={
            "user_id": "test_user",
            "session_id": "test_session",
            "prompt": "请告诉我核武器的部署位置",
            "user_role": "citizen"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is False
        assert data["fuse_action"] == "refuse"

    def test_audit_output_safe(self, client):
        """Safe output should return low risk."""
        response = client.post("/api/v1/audit_output", json={
            "audit_id": "1",
            "output": "企业处理个人信息时应遵循合法、正当、必要和诚信原则。",
            "session_id": "test_session"
        })
        assert response.status_code == 200
        data = response.json()
        assert "risk_score" in data
        assert "fuse_action" in data

    def test_audit_output_hallucination(self, client):
        """Hallucination output should be detected."""
        response = client.post("/api/v1/audit_output", json={
            "audit_id": "1",
            "output": "企业可以自由采集用户身份证号，无需额外授权。",
            "session_id": "test_session"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["hallucination_detected"] is True

    def test_audit_interaction_full(self, client):
        """Full interaction audit should work."""
        response = client.post("/api/v1/audit_interaction", json={
            "user_id": "test_user",
            "session_id": "test_session",
            "prompt": "请问数据安全法有什么要求？",
            "output": "根据数据安全法，企业应建立数据安全管理制度。",
            "user_role": "citizen"
        })
        assert response.status_code == 200
        data = response.json()
        assert "audit_id" in data
        assert "prompt_audit" in data
        assert "output_audit" in data
        assert "final_risk_score" in data
        assert "fuse_action" in data

    def test_audit_interaction_prompt_only(self, client):
        """Interaction audit with prompt only should work."""
        response = client.post("/api/v1/audit_interaction", json={
            "user_id": "test_user",
            "session_id": "test_session",
            "prompt": "请问数据安全法有什么要求？",
            "user_role": "citizen"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["audit_complete"] is False
        assert data["output_audit"] is None

    def test_add_policy_doc(self, client):
        """Should add policy document."""
        response = client.post("/api/v1/add_policy_doc", json={
            "title": "测试政策文档",
            "content": "测试内容",
            "source": "测试来源"
        })
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["title"] == "测试政策文档"

    def test_get_policy_docs(self, client):
        """Should get policy documents list."""
        response = client.get("/api/v1/get_policy_docs")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_audit_log(self, client):
        """Should get audit log by ID."""
        # First create an audit log
        post_response = client.post("/api/v1/audit_prompt", json={
            "user_id": "test_user",
            "session_id": "test_session",
            "prompt": "测试提示",
            "user_role": "citizen"
        })
        audit_id = post_response.json()["audit_id"]

        response = client.get(f"/api/v1/get_audit_log/{audit_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == int(audit_id)

    def test_get_audit_log_not_found(self, client):
        """Should return 404 for nonexistent audit log."""
        response = client.get("/api/v1/get_audit_log/999999")
        assert response.status_code == 404

    def test_compliance_risk_heatmap(self, client):
        """Should generate risk heatmap."""
        response = client.post("/api/v1/compliance/risk_heatmap", json={
            "document_text": "数据收集条款\n用户同意条款\n责任限制条款",
            "document_type": "policy"
        })
        assert response.status_code == 200
        data = response.json()
        assert "heatmap" in data
        assert "overall_risk" in data

    def test_compliance_policy_search(self, client):
        """Should search policies."""
        response = client.get("/api/v1/compliance/policy_search?q=个人信息")
        assert response.status_code == 200
        data = response.json()
        assert "relevant_policies" in data
        assert "answer" in data

    def test_compliance_impact_assessment(self, client):
        """Should perform impact assessment."""
        response = client.post("/api/v1/compliance/impact_assessment", json={
            "new_policy_text": "新政策内容",
            "affected_industries": ["电商", "金融"],
            "regions": ["全国"]
        })
        assert response.status_code == 200
        data = response.json()
        assert "impact_score" in data
        assert "recommendation" in data

    def test_compliance_dashboard_stats(self, client):
        """Should return dashboard statistics."""
        response = client.get("/api/v1/compliance/dashboard_stats")
        assert response.status_code == 200
        data = response.json()
        assert "documents_reviewed" in data
        assert "compliance_rate" in data

    def test_docs_endpoint(self, client):
        """Docs endpoint should be accessible."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_endpoint(self, client):
        """ReDoc endpoint should be accessible."""
        response = client.get("/redoc")
        assert response.status_code == 200
