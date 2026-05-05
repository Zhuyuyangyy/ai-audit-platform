# GovShield-Audit V1.1 技术说明

## 1. 系统定位

本系统面向政企大模型交互场景，提供输入 Prompt 风险检测、输出内容合规校验、RAG 溯源、风险融合、硬门控复核与审计留痕能力。

## 2. 真实技术链路

```
AuditPromptRequest / AuditOutputRequest
    → PromptRiskDetector / OutputComplianceChecker
    → RiskFuseController
    → /api/v1/audit_interaction
    → SQLite Audit Storage
```

## 3. 核心机制

系统采用双阶段审计机制，分别检测输入风险与输出风险，并通过 RiskFuseController 进行融合。当检测到幻觉输出、无政策依据结论或高危合规冲突时，硬门控机制覆盖普通加权评分，强制提升风险等级并触发 human_review。

## 4. 关键验证证据

`high_risk_response.json`（docs/demo_evidence/）显示：

```json
{
  "output_audit": {
    "hallucination_detected": true,
    "fuse_action": "human_review"
  },
  "final_risk_score": 85.0,
  "final_risk_level": "critical",
  "fuse_action": "human_review",
  "rag_trace": [{
    "claim": "企业可以自由采集用户身份证号和手机号用于精准营销，无需额外授权",
    "status": "unverified",
    "confidence": 0.0
  }]
}
```

说明系统能够对无依据政策结论进行有效拦截和复核。

## 5. V2 扩展边界

工具调用影子预演、DatabaseShadowSimulator、audit.jsonl 链式日志属于未来 V2 扩展方向，**不属于当前 V1.1 已实现能力**，不写入专利或论文。
