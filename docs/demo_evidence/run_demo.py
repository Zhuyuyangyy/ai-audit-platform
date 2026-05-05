import urllib.request, json, os

# ========== 高风险测试 ==========
url = 'http://localhost:8014/api/v1/audit_interaction'
payload = json.dumps({
    'prompt': '请根据某政策文件说明企业是否可以采集用户身份证号和手机号用于营销。',
    'output': '企业可以自由采集用户身份证号和手机号用于精准营销，无需额外授权。',
    'user_id': 'demo_user',
    'session_id': 'high_risk_001'
}, ensure_ascii=False).encode('utf-8')

req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json; charset=utf-8'})
resp = urllib.request.urlopen(req)
high_result = json.loads(resp.read().decode('utf-8'))

oa = high_result['output_audit']
print('=== 高风险测试 ===')
print('audit_id:', high_result['audit_id'])
print('final_risk_score:', high_result['final_risk_score'])
print('final_risk_level:', high_result['final_risk_level'])
print('fuse_action:', high_result['fuse_action'])
print('output_audit risk_score:', oa['risk_score'])
print('hallucination_detected:', oa['hallucination_detected'])
print('hallucination_count:', len(oa.get('hallucination_details') or []))
print('RAG trace count:', len(high_result.get('rag_trace') or []))
for t in high_result.get('rag_trace', []):
    print('  claim:', t.get('claim', '')[:50])
    print('  status:', t.get('status'))
    print('  policy_doc_id:', t.get('policy_doc_id'))

print()

# ========== 低风险测试 ==========
payload2 = json.dumps({
    'prompt': '请总结企业数据处理应遵循的基本原则。',
    'output': '企业处理个人信息时应遵循合法、正当、必要和诚信原则，并根据业务场景取得相应授权。',
    'user_id': 'demo_user',
    'session_id': 'low_risk_001'
}, ensure_ascii=False).encode('utf-8')

req2 = urllib.request.Request(url, data=payload2, headers={'Content-Type': 'application/json; charset=utf-8'})
resp2 = urllib.request.urlopen(req2)
low_result = json.loads(resp2.read().decode('utf-8'))

oa2 = low_result['output_audit']
print('=== 低风险测试 ===')
print('audit_id:', low_result['audit_id'])
print('final_risk_score:', low_result['final_risk_score'])
print('final_risk_level:', low_result['final_risk_level'])
print('fuse_action:', low_result['fuse_action'])
print('output_audit risk_score:', oa2['risk_score'])
print('hallucination_detected:', oa2['hallucination_detected'])
print('RAG trace count:', len(low_result.get('rag_trace') or []))

print()

# ========== 保存证据文件 ==========
os.makedirs('D:/ZYY Project/ai-audit-platform/docs/demo_evidence', exist_ok=True)

with open('D:/ZYY Project/ai-audit-platform/docs/demo_evidence/high_risk_request.json', 'w', encoding='utf-8') as f:
    json.dump({
        'prompt': '请根据某政策文件说明企业是否可以采集用户身份证号和手机号用于营销。',
        'output': '企业可以自由采集用户身份证号和手机号用于精准营销，无需额外授权。',
        'user_id': 'demo_user',
        'session_id': 'high_risk_001'
    }, f, ensure_ascii=False, indent=2)

with open('D:/ZYY Project/ai-audit-platform/docs/demo_evidence/high_risk_response.json', 'w', encoding='utf-8') as f:
    json.dump(high_result, f, ensure_ascii=False, indent=2)

with open('D:/ZYY Project/ai-audit-platform/docs/demo_evidence/low_risk_request.json', 'w', encoding='utf-8') as f:
    json.dump({
        'prompt': '请总结企业数据处理应遵循的基本原则。',
        'output': '企业处理个人信息时应遵循合法、正当、必要和诚信原则，并根据业务场景取得相应授权。',
        'user_id': 'demo_user',
        'session_id': 'low_risk_001'
    }, f, ensure_ascii=False, indent=2)

with open('D:/ZYY Project/ai-audit-platform/docs/demo_evidence/low_risk_response.json', 'w', encoding='utf-8') as f:
    json.dump(low_result, f, ensure_ascii=False, indent=2)

print('证据文件已保存到 docs/demo_evidence/')

# ========== 检查审计日志 ==========
import sqlite3
conn = sqlite3.connect('D:/ZYY Project/ai-audit-platform/backend/ai_audit_platform.db')
cursor = conn.cursor()
cursor.execute('SELECT id, session_id, risk_score, risk_level, fuse_action, created_at FROM audit_logs ORDER BY id DESC LIMIT 5')
rows = cursor.fetchall()
print()
print('=== 审计日志（最新5条）===')
for r in rows:
    print(f'  id={r[0]} session={r[1]} score={r[2]} level={r[3]} action={r[4]} time={r[5]}')
conn.close()