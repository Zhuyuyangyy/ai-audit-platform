# API Routes
# All audit endpoints for the AI Compliance Platform

import uuid
import random
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

# Shared disclaimer for endpoints that return simulated / placeholder data
_DISCLAIMER_SIMULATED = (
    "DISCLAIMER: This endpoint returns SIMULATED data (random or hardcoded "
    "placeholders). It is NOT connected to a real analytics backend. "
    "Do NOT use these values for production decisions."
)

DB_PATH = os.environ.get(
    "DATABASE_PATH",
    os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "ai_audit_platform.db"))
)

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

# ── Compliance Extended ─────────────────────────────────────

@router.post("/compliance/risk_heatmap")
async def compliance_risk_heatmap(data: dict):
    """生成文档风险热力图"""
    doc_text = data.get("document_text", "")
    doc_type = data.get("document_type", "policy")
    sections = []
    # Simulate section-by-section risk analysis
    section_texts = doc_text.split("\n") if doc_text else ["数据收集条款", "用户同意条款", "责任限制条款", "隐私保护条款"]
    for i, section in enumerate(section_texts[:6]):
        risk_types = ["数据过度收集", "单方面条款", "模糊定义", "高额违约金", "免责条款过宽"]
        risk_level = min(0.95, round(random.uniform(0.3, 0.9), 2)) if section else 0.4
        sections.append({
            "section": f"第{i+1}条" if not section else section[:15],
            "risk_level": risk_level,
            "risk_type": risk_types[i % len(risk_types)],
            "highlight": f"存在{['数据收集范围过广', '单方面终止权', '模糊的免责条款', '违约金偏高', '用户同意条款不完整'][i%5]}",
            "suggestion": ["增加数据收集范围限定", "增加对等终止条款", "明确免责范围", "降低违约金上限", "增加用户撤回权"][i%5]
        })
    avg_risk = round(sum(s["risk_level"] for s in sections) / len(sections), 3)
    return {
        "heatmap": sections,
        "overall_risk": avg_risk,
        "recommendations": [s["suggestion"] for s in sections if s["risk_level"] > 0.6],
        "document_type": doc_type
    }

@router.get("/compliance/policy_search")
async def compliance_policy_search(q: str = ""):
    """语义政策搜索"""
    policies = [
        {"title": "《个人信息保护法》第21条", "relevance": 0.92, "matching_excerpt": "数据处理者向第三方提供个人信息须取得单独同意"},
        {"title": "《数据安全法》第27条", "relevance": 0.85, "matching_excerpt": "开展数据安全风险评估并留存相关记录"},
        {"title": "《生成式AI服务管理暂行办法》第12条", "relevance": 0.78, "matching_excerpt": "提供者应建立知识产权保护机制"},
        {"title": "《政务数据共享管理条例》第15条", "relevance": 0.71, "matching_excerpt": "政务数据跨部门共享需经过安全评估"},
    ]
    filtered = [p for p in policies if q.lower() in p["title"].lower() or q.lower() in p["matching_excerpt"].lower()] if q else policies
    answer = f"根据《个人信息保护法》第21条，数据处理者向第三方提供个人信息须取得单独同意。对于您查询的'{q}'相关内容，核心要求是确保数据主体知情并同意。"
    return {"relevant_policies": filtered, "answer": answer, "query": q}

@router.post("/compliance/impact_assessment")
async def compliance_impact_assessment(data: dict):
    """监管影响评估"""
    policy_text = data.get("new_policy_text", "")
    industries = data.get("affected_industries", ["电商", "金融"])
    regions = data.get("regions", ["全国"])
    score = min(9.5, round(random.uniform(5.0, 9.0), 1))
    impact_score = round(score / 10 * 100, 1)
    return {
        "impact_score": score,
        "affected_parties": [f"{ind}企业约{random.randint(1000, 50000)}家" for ind in industries],
        "compliance_costs": f"¥{random.randint(50, 200)}M-{random.randint(200, 500)}M",
        "benefits": "提升数据安全水平，增强公众信任，促进数据合规流通",
        "recommendation": "proceed_with_caution" if score > 7 else "need_review" if score > 5 else "should_reject",
        "industries": industries,
        "regions": regions
    }

@router.get("/compliance/dashboard_stats")
async def compliance_dashboard_stats():
    """仪表盘统计"""
    return {
        "documents_reviewed": random.randint(800, 1500),
        "risk_detected": random.randint(100, 300),
        "compliance_rate": round(random.uniform(85, 97), 1),
        "avg_review_time_minutes": round(random.uniform(5, 20), 1),
        "risk_distribution": {"high": 45, "medium": 120, "low": 235},
        "trend": "improving"
    }

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