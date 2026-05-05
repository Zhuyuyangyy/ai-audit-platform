# 算法公式说明：政企大模型安全审计风险熵模型

> **版本：** V1.0 | **日期：** 2026-05-05 | **对应系统：** ai-audit-platform

---

## 一、风险熵评分公式

### 1.1 综合风险熵

```
H_total = w₁·H_base + w₂·H_hallu + w₃·H_rag + w₄·H_rule
```

| 符号 | 定义 | 范围 |
|------|------|------|
| H_base | 基础风险熵（输入输出最大者） | [0, 1] |
| H_hallu | 幻觉熵增因子 | [0, 0.5] |
| H_rag | RAG溯源缺失惩罚熵 | [0, 0.3] |
| H_rule | 规则触发熵 | [0, 0.25] |
| w₁~w₄ | 各维度权重 | 归一化和为1 |

**默认权重配置：**
```
w₁ = 0.40  (基础风险，权重最高)
w₂ = 0.20  (幻觉熵增)
w₃ = 0.15  (RAG溯源惩罚)
w₄ = 0.25  (规则触发熵)
```

### 1.2 各维度计算

**H_base（基础风险熵）：**
```
H_base = max(s_prompt, s_output) / 100

其中：
  s_prompt  = 输入审计的综合风险分 [0, 100]
  s_output  = 输出审计的综合风险分 [0, 100]
```

**H_hallu（幻觉熵增）：**
```
H_hallu = min(h × 0.15, 0.5)

其中：
  h = 检测到的幻觉语句数量
  上限0.5，防止极端情况过度惩罚
```

**H_rag（RAG溯源缺失惩罚）：**
```
H_rag = (1 - r) × 0.3

其中：
  r = verified_ratio = 有溯源的结论数 / 总结论数
  溯源覆盖率越低，惩罚熵越高
```

**H_rule（规则触发熵）：**
```
H_rule = Σ (triggered_rule_i["entropy_contrib"]) / N_rules

其中：
  triggered_rule_i["entropy_contrib"] ∈ [0, 1]
  每条规则有自己的熵贡献值，范围 [0, 1]
```

---

## 二、风险等级映射

### 2.1 五级映射表

```
风险等级 L = f(H_total)

| L    | H_total 范围 | 含义       | 响应动作        |
|------|-------------|-----------|----------------|
| 0    | [0, 0.20)   | 安全       | PASS           |
| 1    | [0.20, 0.40) | 低风险     | WARN_PASS      |
| 2    | [0.40, 0.50) | 中风险     | PARTIAL_MASK   |
| 3    | [0.50, 0.80) | 高风险     | HUMAN_REVIEW   |
| 4    | [0.80, 1.00] | 严重       | REJECT         |
```

### 2.2 映射函数实现

```python
def entropy_to_level(H: float) -> Tuple[int, str]:
    if H < 0.20:
        return (0, "安全")
    elif H < 0.40:
        return (1, "低风险")
    elif H < 0.50:
        return (2, "中风险")
    elif H < 0.80:
        return (3, "高风险")
    else:
        return (4, "严重")
```

---

## 三、RAG溯源置信度

### 3.1 置信度定义

```
C_rag = verified_ratio = V / T

其中：
  V = 有溯源结论数（evidence_doc is not None）
  T = 总结论数（NLP提取的关键结论总数）
```

### 3.2 溯源匹配算法

```python
def rag_verify(output: str, policy_docs: List[dict]) -> List[Trace]:
    """
    对输出文本进行RAG溯源
    """
    
    # Step 1: 句子分割
    sentences = split_sentences(output)  # 按句号/分号分割
    
    # Step 2: 关键结论提取（简化版：含数量词/程度词的句子）
    claims = []
    for sent in sentences:
        if contains_quantifier(sent) or contains_modality(sent):
            claims.append(sent)
    
    # Step 3: 语义匹配政策文档
    traces = []
    for claim in claims:
        # 向量相似度 + 关键词重叠率融合
        scores = []
        for doc in policy_docs:
            vec_sim = cosine_similarity(claim_embedding, doc_embedding)
            kw_overlap = keyword_jaccard(claim, doc["content"])
            combined = 0.6 * vec_sim + 0.4 * kw_overlap
            scores.append((doc, combined))
        
        # 取top-1作为溯源证据
        scores.sort(key=lambda x: x[1], reverse=True)
        if scores and scores[0][1] > threshold:
            traces.append({
                "claim": claim,
                "evidence_doc": scores[0][0]["title"],
                "evidence_content": scores[0][0]["content"][:200],
                "relevance_score": round(scores[0][1], 3)
            })
        else:
            traces.append({
                "claim": claim,
                "evidence_doc": None,
                "evidence_content": None,
                "relevance_score": 0.0,
                "unverified": True
            })
    
    # Step 4: 计算置信度
    verified = sum(1 for t in traces if not t.get("unverified"))
    C_rag = verified / len(traces) if traces else 0.0
    
    return traces, C_rag
```

---

## 四、熔断响应逻辑

### 4.1 响应动作表

```python
FUSE_ACTIONS = {
    0: {"action": "PASS",        "message": "安全，放行",          "log_level": "INFO"},
    1: {"action": "WARN_PASS",   "message": "低风险，警告后放行",  "log_level": "WARN"},
    2: {"action": "PARTIAL_MASK", "message": "中风险，部分屏蔽",    "log_level": "WARN"},
    3: {"action": "HUMAN_REVIEW", "message": "高风险，转人工审核",   "log_level": "ERROR"},
    4: {"action": "REJECT",       "message": "严重风险，拒绝回答",   "log_level": "CRITICAL"}
}
```

### 4.2 执行流程

```python
def execute_fuse(risk_score: float, traces: List, context: dict) -> FuseResult:
    level, label = entropy_to_level(risk_score)
    action_config = FUSE_ACTIONS[level]
    
    result = FuseResult(
        action=action_config["action"],
        message=action_config["message"],
        risk_level=label,
        risk_score=risk_score,
        masked_content=None
    )
    
    # 中风险：自动屏蔽高风险片段
    if level == 2:
        result.masked_content = mask_high_risk_segments(traces)
    
    # 高风险/严重：通知管理员
    if level >= 3:
        notify_admin(context, result)
    
    return result
```

---

## 五、审计日志链式哈希

### 5.1 哈希链定义

```python
def compute_log_hash(log_entry: dict, prev_hash: str = None) -> str:
    """
    计算单条审计日志的哈希值
    包含前一条哈希，形成链式结构
    """
    
    # 原文哈希（防篡改）
    text_hash = sha256(
        log_entry["prompt"] + 
        (log_entry["output"] or "")
    )
    
    # 校验和（包含时间戳+原文哈希+风险分+前一条哈希）
    payload = f"{log_entry['timestamp']}:{text_hash}:{log_entry['risk_score']}"
    checksum = sha256(payload + (prev_hash or "genesis"))
    
    return {
        "text_hash": text_hash,
        "checksum": checksum,
        "prev_hash": prev_hash
    }
```

### 5.2 链式验证

```python
def verify_log_chain(logs: List[dict]) -> bool:
    """
    验证整条审计链的完整性
    从第一条开始，逐条验证哈希链是否被破坏
    """
    
    prev_hash = None
    
    for log in logs:
        expected_hash = compute_log_hash(log, prev_hash)
        
        if log["text_hash"] != expected_hash["text_hash"]:
            return False  # 原文被篡改
        
        if log["checksum"] != expected_hash["checksum"]:
            return False  # 校验和被破坏
        
        prev_hash = log["checksum"]
    
    return True
```

---

## 六、场景化权重配置

```python
SCENE_WEIGHTS = {
    # 默认配置（通用政务场景）
    "default": {
        "w1": 0.40,  # 基础风险
        "w2": 0.20,  # 幻觉熵增
        "w3": 0.15,  # RAG溯源
        "w4": 0.25   # 规则触发
    },
    
    # 高安全场景（如国安、军事相关）：严格模式
    "high_security": {
        "w1": 0.50,  # 提高基础风险权重
        "w2": 0.20,
        "w3": 0.20,  # 提高RAG溯源权重
        "w4": 0.10
    },
    
    # 宽松模式（如内部咨询）：宽松模式
    "relaxed": {
        "w1": 0.30,
        "w2": 0.30,
        "w3": 0.10,
        "w4": 0.30
    }
}
```

---

*本公式说明对应 `audit_risk_scorer.py` 的实现，可直接对照代码阅读。*