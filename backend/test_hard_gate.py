"""
AgentShield V1 防回归测试
测试硬门控机制：高风险幻觉输出必须被正确拦截，低风险输出正常放行
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))

from app.services.audit_risk_scorer import AuditRiskScorer
from app.services.risk_fuse_controller import RiskFuseController
from app.services.output_compliance_checker import OutputComplianceChecker
from app.services.rag_tracer import RAGTracer


# ===== Test 1: 高风险幻觉输出 → 必须 human_review =====
def test_hallucination_unverified_claim_forces_human_review():
    """硬门控1：幻觉 + 无依据claim → human_review（≥85分）"""
    checker = OutputComplianceChecker()
    output = "企业可以自由采集用户身份证号和手机号用于精准营销，无需额外授权。"
    score, hallucination_details, policy_binding, has_hallucination = checker.check(output, None)

    assert has_hallucination is True, "Output should be detected as hallucination"
    assert score == 40.0, f"Output score should be 40, got {score}"
    assert len(hallucination_details) >= 3, f"Hallucination indicators should be >= 3, got {len(hallucination_details)}"

    fuse = RiskFuseController()
    fuse_action, comment, suggestion = fuse.evaluate(
        prompt_score=0.0,
        output_score=score,
        detected_rules=[],
        session_id="test_hard_gate_1",
        user_role="citizen",
        has_hallucination=has_hallucination,
        unverified_claim_count=1
    )

    assert fuse_action == "human_review", \
        f"Hallucination+unverified should trigger human_review, got: {fuse_action}"
    assert "幻觉" in comment, f"comment should mention hallucination, got: {comment}"

    scorer = AuditRiskScorer()
    result = scorer.compute_risk_entropy(
        prompt_score=0.0,
        output_score=score,
        hallucination_count=len(hallucination_details),
        rag_verified_ratio=0.0,
        fuse_action=fuse_action,
        detected_rules=[]
    )

    assert result["total_score"] >= 85.0, \
        f"Hard gate floor should be >= 85, got: {result['total_score']}"
    assert result["risk_level"] in ("high", "critical"), \
        f"Risk level should be high/critical, got: {result['risk_level']}"

    print("[PASS] Test 1: hallucination+unverified -> human_review, score=85.0")


# ===== Test 2: 单纯幻觉输出 → 至少 human_review（≥70分） =====
def test_hallucination_alone_forces_human_review():
    """硬门控2：检测到幻觉 → human_review（≥70分）"""
    checker = OutputComplianceChecker()
    output = "据内部消息，政府已批准企业可以直接向境外传输用户隐私数据，无需经过任何审批程序。"
    score, hallucination_details, policy_binding, has_hallucination = checker.check(output, None)

    assert has_hallucination is True, "Should detect hallucination"

    fuse = RiskFuseController()
    fuse_action, comment, _ = fuse.evaluate(
        prompt_score=0.0,
        output_score=score,
        detected_rules=[],
        session_id="test_hard_gate_2",
        user_role="citizen",
        has_hallucination=has_hallucination,
        unverified_claim_count=0
    )

    assert fuse_action == "human_review", \
        f"Detected hallucination should trigger human_review, got: {fuse_action}"

    scorer = AuditRiskScorer()
    result = scorer.compute_risk_entropy(
        prompt_score=0.0,
        output_score=score,
        hallucination_count=len(hallucination_details),
        rag_verified_ratio=0.5,
        fuse_action=fuse_action,
        detected_rules=[]
    )

    assert result["total_score"] >= 70.0, \
        f"Hard gate floor should be >= 70, got: {result['total_score']}"

    print("[PASS] Test 2: hallucination alone -> human_review @70")


# ===== Test 3: 低风险合规输出 → 正常 allow =====
def test_verified_low_risk_policy_output_allows():
    """无幻觉 + RAG溯源有效 → 正常放行"""
    checker = OutputComplianceChecker()
    output = "企业处理个人信息时应遵循合法、正当、必要和诚信原则，并根据业务场景取得相应授权。"
    score, hallucination_details, policy_binding, has_hallucination = checker.check(output, None)

    assert has_hallucination is False, "Compliant output should not detect hallucination"
    assert score == 0.0, f"Compliant output score should be 0, got {score}"

    fuse = RiskFuseController()
    fuse_action, comment, _ = fuse.evaluate(
        prompt_score=0.0,
        output_score=score,
        detected_rules=[],
        session_id="test_low_risk",
        user_role="citizen",
        has_hallucination=False,
        unverified_claim_count=0
    )

    assert fuse_action == "allow", \
        f"Low-risk output should be allow, got: {fuse_action}"

    scorer = AuditRiskScorer()
    result = scorer.compute_risk_entropy(
        prompt_score=0.0,
        output_score=score,
        hallucination_count=0,
        rag_verified_ratio=1.0,
        fuse_action=fuse_action,
        detected_rules=[]
    )

    assert result["total_score"] == 0.0, \
        f"Low-risk entropy should be 0, got: {result['total_score']}"
    assert result["risk_level"] == "safe", \
        f"Risk level should be safe, got: {result['risk_level']}"

    print("[PASS] Test 3: low-risk compliant output -> allow, score=0.0")


# ===== Test 4: 风险熵分数地板验证 =====
def test_risk_entropy_floor_prevents_dilution():
    """验证分数地板：幻觉输出不会被加权平均稀释"""
    scorer = AuditRiskScorer()

    # 幻觉 + 无依据claim → 地板85
    result1 = scorer.compute_risk_entropy(
        prompt_score=0.0, output_score=40.0,
        hallucination_count=4, rag_verified_ratio=0.0,
        fuse_action="human_review", detected_rules=[]
    )
    assert result1["total_score"] >= 85.0, \
        f"Hallucination+unverified should >= 85, got: {result1['total_score']}"

    # 单纯幻觉 → 地板70
    result2 = scorer.compute_risk_entropy(
        prompt_score=0.0, output_score=40.0,
        hallucination_count=2, rag_verified_ratio=0.5,
        fuse_action="human_review", detected_rules=[]
    )
    assert result2["total_score"] >= 70.0, \
        f"Hallucination alone should >= 70, got: {result2['total_score']}"

    # 低风险 → 无地板
    result3 = scorer.compute_risk_entropy(
        prompt_score=0.0, output_score=0.0,
        hallucination_count=0, rag_verified_ratio=1.0,
        fuse_action="allow", detected_rules=[]
    )
    assert result3["total_score"] == 0.0, \
        f"Low-risk output should be 0, got: {result3['total_score']}"

    print("[PASS] Test 4: risk entropy floor prevents dilution")


# ===== Test 5: RAG tracer 政策溯源功能 =====
def test_rag_tracer_finds_pipl_evidence():
    """RAG tracer 能从 document_chunks 表中找到 PIPL 证据"""
    db_path = os.path.join(os.path.dirname(__file__), 'ai_audit_platform.db')
    tracer = RAGTracer(db_path)

    output = "企业处理个人信息时应遵循合法、正当、必要和诚信原则，并根据业务场景取得相应授权。"
    traces = tracer.trace(output, None)

    verified_traces = [t for t in traces if t.get('policy_doc_id') is not None]
    assert len(verified_traces) >= 1, \
        f"Should find >= 1 verified RAG trace, got: {len(verified_traces)}"

    pipl_traces = [t for t in verified_traces if t.get('policy_doc_id') == 3]
    assert len(pipl_traces) >= 1, \
        f"Should match PIPL(doc_id=3), got doc_ids: {[t.get('policy_doc_id') for t in verified_traces]}"

    print(f"[PASS] Test 5: RAG tracer found {len(verified_traces)} policy traces ({len(pipl_traces)} PIPL)")


# ===== 运行所有测试 =====
if __name__ == "__main__":
    print("=" * 50)
    print("AgentShield V1 Regression Tests")
    print("=" * 50)
    print()

    tests = [
        ("Test 1: hallucination+unverified -> human_review @85", test_hallucination_unverified_claim_forces_human_review),
        ("Test 2: hallucination alone -> human_review @70", test_hallucination_alone_forces_human_review),
        ("Test 3: low-risk compliant output -> allow", test_verified_low_risk_policy_output_allows),
        ("Test 4: risk entropy floor prevents dilution", test_risk_entropy_floor_prevents_dilution),
        ("Test 5: RAG tracer policy evidence", test_rag_tracer_finds_pipl_evidence),
    ]

    passed = 0
    failed = 0

    for name, fn in tests:
        try:
            print(f"Running: {name}")
            fn()
            passed += 1
            print()
        except AssertionError as e:
            print(f"[FAIL] AssertionError: {e}")
            failed += 1
            print()
        except Exception as e:
            print(f"[ERROR] {e}")
            failed += 1
            print()

    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 50)

    if failed > 0:
        exit(1)
    else:
        print("All tests PASSED")
        exit(0)