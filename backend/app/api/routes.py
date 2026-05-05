# API Routes
# All audit endpoints for the AI Compliance Platform

import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
import sqlite3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.schemas import (
    AuditPromptRequest, AuditPromptResponse,
    AuditOutputRequest, AuditOutputResponse,
    AuditInteractionRequest, AuditInteractionResponse,
    AddPolicyDocRequest, RiskLevel, FuseAction
)
from app.services.prompt_risk_detector import PromptRiskDetector
from app.services.output_compliance_checker import OutputComplianceChecker
from app.services.rag_tracer import RAGTracer
from app.services.model_audit_logger import ModelAuditLogger
from app.services.risk_fuse_controller import RiskFuseController
from app.services.audit_risk_scorer import AuditRiskScorer
from app.services.report_generator import ReportGenerator

router = APIRouter(prefix="/api/v1", tags=["audit"])

DB_PATH = "D:/ZYY Project/ai-audit-platform/backend/ai_audit_platform.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ── Service Instances ───────────────────────────────────────────
_detector = PromptRiskDetector()
_output_checker = OutputComplianceChecker()
_rag_tracer = RAGTracer(DB_PATH)
_logger = ModelAuditLogger(DB_PATH)
_fuse_controller = RiskFuseController()
_scorer = AuditRiskScorer()
_report_gen = ReportGenerator(DB_PATH)

# ── Prompt Audit ────────────────────────────────────────────────

@router.post("/audit_prompt", response_model=AuditPromptResponse)
async def audit_prompt(req: AuditPromptRequest):
    """审计用户输入的Prompt"""
    score, detected, fuse_action = _detector.detect(req.prompt, req.user_role)
    risk_level = _detector.get_risk_level(score)
    
    # 记录日志
    log_id = _logger.log_interaction(
        user_id=req.user_id,
        session_id=req.session_id,
        prompt=req.prompt,
        output=None,
        risk_score=score,
        risk_level=risk_level,
        fuse_action=fuse_action,
        prompt_rules=detected
    )
    
    return AuditPromptResponse(
        allowed=fuse_action not in ("refuse", "block"),
        risk_score=score,
        risk_level=risk_level,
        detected_rules=detected,
        fuse_action=fuse_action,
        audit_id=str(log_id),
        review_comment=_get_review_comment(score, detected, fuse_action)
    )

# ── Output Audit ───────────────────────────────────────────────

@router.post("/audit_output", response_model=AuditOutputResponse)
async def audit_output(req: AuditOutputRequest):
    """审计模型输出"""
    score, hallucination_details, policy_binding, has_hallucination = \
        _output_checker.check(req.output, req.audit_id)
    
    risk_level = _output_checker.get_risk_level(score)
    fuse_action = _output_checker.determine_fuse_action(score, has_hallucination)
    
    # 如果需要溯源，执行RAG追踪
    rag_trace = []
    if score >= 30:
        rag_trace = _rag_tracer.trace(req.output)
    
    # 更新审计日志
    log = _logger.get_audit_log(int(req.audit_id))
    if log:
        _logger.update_output(
            log_id=int(req.audit_id),
            output=req.output,
            risk_score=score,
            risk_level=risk_level,
            fuse_action=fuse_action
        )
    
    return AuditOutputResponse(
        allowed=fuse_action not in ("refuse", "block"),
        risk_score=score,
        risk_level=risk_level,
        hallucination_detected=has_hallucination,
        hallucination_details=hallucination_details,
        policy_binding_results=policy_binding,
        fuse_action=fuse_action,
        review_comment=_get_review_comment(score, [], fuse_action)
    )

# ── Full Interaction Audit ─────────────────────────────────────

@router.post("/audit_interaction", response_model=AuditInteractionResponse)
async def audit_interaction(req: AuditInteractionRequest):
    """全链路审计（输入+输出）"""
    
    # Step 1: Prompt审计
    prompt_score, prompt_detected, prompt_fuse = _detector.detect(req.prompt, req.user_role)
    prompt_level = _detector.get_risk_level(prompt_score)
    
    # 记录初始日志
    log_id = _logger.log_interaction(
        user_id=req.user_id,
        session_id=req.session_id,
        prompt=req.prompt,
        output=None,
        risk_score=prompt_score,
        risk_level=prompt_level,
        fuse_action=prompt_fuse,
        prompt_rules=prompt_detected
    )
    
    prompt_response = AuditPromptResponse(
        allowed=prompt_fuse not in ("refuse", "block"),
        risk_score=prompt_score,
        risk_level=prompt_level,
        detected_rules=prompt_detected,
        fuse_action=prompt_fuse,
        audit_id=str(log_id),
        review_comment=_get_review_comment(prompt_score, prompt_detected, prompt_fuse)
    )
    
    # 如果输出尚未提供，只返回prompt审计结果
    if not req.output:
        return AuditInteractionResponse(
            audit_id=str(log_id),
            prompt_audit=prompt_response,
            output_audit=None,
            final_risk_score=prompt_score,
            final_risk_level=prompt_level,
            fuse_action=prompt_fuse,
            rag_trace=[],
            audit_complete=False
        )
    
    # Step 2: Output审计
    output_score, hallucination_details, policy_binding, has_hallucination = \
        _output_checker.check(req.output, str(log_id))
    output_level = _output_checker.get_risk_level(output_score)
    output_fuse = _output_checker.determine_fuse_action(output_score, has_hallucination)
    
    # Step 3: RAG溯源
    rag_trace = _rag_tracer.trace(req.output, log_id)
    
    # Step 4: 风险熵评分
    rag_verified_ratio = _calc_rag_verified_ratio(rag_trace)
    risk_entropy_result = _scorer.compute_risk_entropy(
        prompt_score=prompt_score,
        output_score=output_score,
        hallucination_count=len(hallucination_details),
        rag_verified_ratio=rag_verified_ratio,
        fuse_action=output_fuse,
        detected_rules=prompt_detected
    )
    
    # Step 5: 熔断决策（硬门控优先）
    unverified_claim_count = sum(1 for t in rag_trace if t.get("status") == "unverified")
    final_fuse, final_comment, _ = _fuse_controller.evaluate(
        prompt_score=prompt_score,
        output_score=output_score,
        detected_rules=prompt_detected,
        session_id=req.session_id,
        user_role=req.user_role,
        has_hallucination=has_hallucination,
        unverified_claim_count=unverified_claim_count
    )

    # 如果硬门控触发，覆盖风险熵评分（确保分数体现硬风险）
    if final_fuse == "human_review" and risk_entropy_result["total_score"] < 85:
        risk_entropy_result["total_score"] = 85.0
        risk_entropy_result["risk_level"] = "high"
    
    final_score = risk_entropy_result["total_score"]
    final_level = risk_entropy_result["risk_level"]
    
    # 记录RAG溯源
    for trace in rag_trace:
        _logger.log_rag_trace(
            audit_id=log_id,
            claim=trace["claim"],
            evidence=trace.get("evidence", ""),
            policy_doc_id=trace.get("policy_doc_id")
        )
    
    _logger.update_output(
        log_id=log_id,
        output=req.output,
        risk_score=final_score,
        risk_level=final_level,
        fuse_action=final_fuse
    )
    
    # 记录熔断
    if final_fuse in ("refuse", "block", "human_review"):
        _logger.log_fuse_action(log_id, final_comment, final_fuse)
    
    output_response = AuditOutputResponse(
        allowed=final_fuse not in ("refuse", "block"),
        risk_score=output_score,
        risk_level=output_level,
        hallucination_detected=has_hallucination,
        hallucination_details=hallucination_details,
        policy_binding_results=policy_binding,
        fuse_action=final_fuse,
        review_comment=final_comment
    )
    
    return AuditInteractionResponse(
        audit_id=str(log_id),
        prompt_audit=prompt_response,
        output_audit=output_response,
        final_risk_score=final_score,
        final_risk_level=final_level,
        fuse_action=final_fuse,
        rag_trace=rag_trace,
        audit_complete=True
    )

def _calc_rag_verified_ratio(rag_trace: list) -> float:
    if not rag_trace:
        return 0.0
    verified = sum(1 for t in rag_trace if t.get("status") != "unverified" and t.get("confidence", 0) > 0.3)
    return verified / len(rag_trace)

# ── Policy Document ────────────────────────────────────────────

@router.post("/add_policy_doc")
async def add_policy_doc(req: AddPolicyDocRequest):
    """添加政策文档到RAG知识库"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO policy_documents (title, content, source, created_at)
        VALUES (?, ?, ?, ?)
    """, (req.title, req.content, req.source, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    doc_id = cursor.lastrowid
    conn.close()
    return {"message": "政策文档添加成功", "title": req.title, "id": doc_id}

@router.get("/get_policy_docs")
async def get_policy_docs():
    """获取政策文档列表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, content, source, created_at FROM policy_documents")
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "title": r["title"],
            "content": r["content"],
            "source": r["source"],
            "created_at": r["created_at"]
        }
        for r in rows
    ]

# ── Audit Log ─────────────────────────────────────────────────

@router.get("/get_audit_log/{log_id}")
async def get_audit_log(log_id: int):
    """获取指定审计日志"""
    log = _logger.get_audit_log(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="审计日志不存在")
    return log

@router.get("/get_audit_report/{session_id}")
async def get_audit_report(session_id: str):
    """获取会话审计报告"""
    report = _report_gen.generate_session_report(session_id)
    if "error" in report:
        raise HTTPException(status_code=404, detail=report["error"])
    return report

@router.get("/get_session_audit_logs/{session_id}")
async def get_session_logs(session_id: str):
    """获取会话所有审计日志"""
    return _logger.get_session_logs(session_id)

# ── Health ─────────────────────────────────────────────────────

@router.get("/health")
async def health():
    """健康检查"""
    return {
        "status": "ok",
        "service": "AI Audit Platform",
        "version": "1.0",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# ── Helper ────────────────────────────────────────────────────

def _get_review_comment(score: float, detected: list, fuse_action: str) -> str:
    if detected:
        rule_names = [d.get("description", d.get("rule_id", "未知规则")) for d in detected]
        return f"检测到: {', '.join(rule_names)}"
    
    if fuse_action == "refuse":
        return "高风险内容，已拒绝回答"
    elif fuse_action == "human_review":
        return "已转人工审核"
    elif fuse_action == "mask":
        return "内容已部分屏蔽"
    elif fuse_action == "warn":
        return "注意：内容存在轻微风险"
    else:
        return "审核通过"