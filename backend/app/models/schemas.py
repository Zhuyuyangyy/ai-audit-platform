# Pydantic schemas for request/response validation
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class RiskLevel(str, Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class FuseAction(str, Enum):
    ALLOW = "allow"                  # 放行
    WARN = "warn"                    # 警告后放行
    MASK = "mask"                    # 部分屏蔽
    REFUSE = "refuse"                # 拒绝回答
    HUMAN_REVIEW = "human_review"    # 转人工审核
    BLOCK = "block"                  # 熔断封禁

# ── Audit Request/Response ────────────────────────────────────

class AuditPromptRequest(BaseModel):
    user_id: str = Field(..., description="用户ID")
    session_id: str = Field(..., description="会话ID")
    prompt: str = Field(..., description="用户输入的Prompt")
    user_role: Optional[str] = Field(default="citizen", description="用户角色")

class AuditPromptResponse(BaseModel):
    allowed: bool
    risk_score: float = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    detected_rules: List[dict]
    fuse_action: FuseAction
    audit_id: Optional[str] = None
    review_comment: Optional[str] = None

class AuditOutputRequest(BaseModel):
    audit_id: str = Field(..., description="关联的审计ID")
    output: str = Field(..., description="模型输出内容")
    session_id: str

class AuditOutputResponse(BaseModel):
    allowed: bool
    risk_score: float
    risk_level: RiskLevel
    hallucination_detected: bool
    hallucination_details: List[dict]
    policy_binding_results: List[dict]
    fuse_action: FuseAction
    review_comment: Optional[str] = None

class AuditInteractionRequest(BaseModel):
    user_id: str
    session_id: str
    prompt: str
    output: Optional[str] = None
    user_role: Optional[str] = "citizen"

class AuditInteractionResponse(BaseModel):
    audit_id: str
    prompt_audit: AuditPromptResponse
    output_audit: Optional[AuditOutputResponse] = None
    final_risk_score: float
    final_risk_level: RiskLevel
    fuse_action: FuseAction
    rag_trace: List[dict]
    audit_complete: bool

# ── Policy Document ────────────────────────────────────────────

class AddPolicyDocRequest(BaseModel):
    title: str
    content: str
    source: str

class PolicyDocumentResponse(BaseModel):
    id: int
    title: str
    content: str
    source: str
    created_at: str

# ── RAG Trace ──────────────────────────────────────────────────

class RAGTraceResult(BaseModel):
    claim: str
    evidence: str
    policy_doc_id: int
    policy_title: str
    confidence: float

# ── Report ────────────────────────────────────────────────────

class AuditReportResponse(BaseModel):
    session_id: str
    total_interactions: int
    avg_risk_score: float
    risk_distribution: dict
    fuse_actions_summary: dict
    policy_doc_references: List[str]
    generated_at: str
    warnings: List[str]