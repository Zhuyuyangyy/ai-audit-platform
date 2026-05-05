import json

with open('D:/ZYY Project/ai-audit-platform/docs/demo_evidence/low_risk_response.json', 'r', encoding='utf-8') as f:
    result = json.load(f)

print('=== LOW RISK VERIFICATION ===')
print('final_risk_score:', result['final_risk_score'])
print('final_risk_level:', result['final_risk_level'])
print('fuse_action:', result['fuse_action'])
print('rag_trace count:', len(result.get('rag_trace', [])))

for i, t in enumerate(result.get('rag_trace', [])):
    print(f'  trace {i+1}:')
    print(f'    claim: {t.get("claim", "")[:60]}')
    print(f'    status: {t.get("status")}')
    print(f'    policy_doc_id: {t.get("policy_doc_id")}')
    print(f'    policy_title: {t.get("policy_title")}')
    print(f'    confidence: {t.get("confidence")}')
    print(f'    evidence: {t.get("evidence", "")[:80]}')

print()
print('=== HIGH RISK VERIFICATION ===')
with open('D:/ZYY Project/ai-audit-platform/docs/demo_evidence/high_risk_response.json', 'r', encoding='utf-8') as f:
    hresult = json.load(f)
print('final_risk_score:', hresult['final_risk_score'])
print('final_risk_level:', hresult['final_risk_level'])
print('fuse_action:', hresult['fuse_action'])
print('output_audit.hallucination_detected:', hresult['output_audit']['hallucination_detected'])
print('output_audit.hallucination_count:', len(hresult['output_audit'].get('hallucination_details', [])))

# Save fixed responses
import shutil
shutil.copy('D:/ZYY Project/ai-audit-platform/docs/demo_evidence/high_risk_response.json',
            'D:/ZYY Project/ai-audit-platform/docs/demo_evidence/high_risk_response_fixed.json')
shutil.copy('D:/ZYY Project/ai-audit-platform/docs/demo_evidence/low_risk_response.json',
            'D:/ZYY Project/ai-audit-platform/docs/demo_evidence/low_risk_response_fixed.json')
print()
print('Fixed responses saved to *_fixed.json')