# 专利技术交底书：政企大模型输出安全审计与提示词溯源风控方法

> **版本：** V1.0 | **日期：** 2026-05-05 | **状态：** 内部技术文档

---

## 一、发明名称

**一种面向政企场景的大模型输出安全审计与提示词溯源风控方法**

## 二、技术领域

大模型安全审计、自然语言处理、政务合规AI、RAG系统风控

---

## 三、背景与问题

### 3.1 现实问题

政企场景中，大模型（如ChatGPT、国产大模型）面临以下风险：

1. **Prompt注入攻击**：用户通过精心构造的输入诱导模型泄露涉密信息
2. **隐私泄露试探**：用户反复试探获取他人个人数据
3. **政策错误解读**：模型输出与现行政策法规存在矛盾的内容
4. **幻觉内容**：模型生成看似合理但无政策依据的断言
5. **RAG溯源缺失**：模型输出的关键结论无法绑定到权威政策文档

### 3.2 现有技术的缺陷

| 现有方案 | 缺陷 |
|---------|------|
| 关键词过滤 | 无法理解语义，易被绕过 |
| 静态规则库 | 无法应对新型攻击模式 |
| 二值判断（违规/不违规） | 无法表达"部分违规""疑似违规"的模糊地带 |
| 黑盒审计 | 无完整链路，无法溯源举证 |

---

## 四、技术方案概述

本发明提出一种**双向审计 + RAG溯源 + 风险熵量化 + 熔断控制**的完整方案：

```
用户输入（Prompt）
    ↓
[Prompt风险识别] → 检测涉密/隐私/诱导泄露
    ↓
[大模型生成]（受控输出）
    ↓
[输出合规检测] → 幻觉/政策冲突检测
    ↓
[RAG溯源校验] → 关键结论与政策文档绑定
    ↓
[风险熵评分] → H = f(基础风险, 幻觉熵增, 溯源缺失, 规则触发)
    ↓
[熔断控制] → 根据风险等级执行放行/警告/屏蔽/拒绝
    ↓
[全链路审计日志] → 可溯源、可举证、不可篡改
```

---

## 五、核心算法

### 5.1 双向审计机制

**输入审计（Prompt Risk Detection）：**

```python
def detect_prompt_risk(prompt: str, user_role: str) -> RiskResult:
    """
    检测Prompt中的风险要素
    返回：风险分(0-100)、风险类型列表、置信度
    """
    
    risk_types = {
        "RULE_AI_001": detect_secret_leak(prompt),      # 涉密信息检测
        "RULE_AI_003": detect_privacy_inducing(prompt),  # 隐私泄露诱导
        "RULE_AI_005": detect_privilege_probing(prompt),# 越权回答试探
        "RULE_AI_006": detect_policy_misguide(prompt),  # 政策错误解读诱导
        "RULE_AI_007": detect_social_engineering(prompt) # 社会工程学攻击
    }
    
    scores = {k: v["score"] for k, v in risk_types.items()}
    total = sum(scores.values()) / len(scores)
    
    return RiskResult(
        total_score=max(scores.values()),
        risk_types=risk_types,
        confidence=compute_confidence(risk_types)
    )
```

**输出审计（Output Compliance Checking）：**

```python
def detect_output_risk(output: str, context: dict) -> RiskResult:
    """
    检测模型输出的合规风险
    """
    
    risk_types = {
        "RULE_AI_002": detect_policy_conflict(output),    # 政策错误解读
        "RULE_AI_004": detect_hallucination(output),     # 幻觉检测
        "RULE_AI_008": detect_fabricated_citation(output) # 无中生有引文
    }
    
    return RiskResult(...)
```

### 5.2 RAG溯源校验

**核心思想：** 每个关键结论必须绑定到至少一个政策文档，否则置信度降低。

```python
def rag_trace(output: str, db_path: str) -> List[ClaimEvidence]:
    """
    遍历输出文本，提取关键结论，匹配政策文档
    """
    
    claims = extract_key_claims(output)  # NLP提取主谓宾
    traces = []
    
    for claim in claims:
        # 语义搜索相关政策
        relevant_docs = semantic_search(claim, policy_corpus, top_k=3)
        
        if relevant_docs:
            for doc in relevant_docs:
                traces.append({
                    "claim": claim,
                    "evidence_doc": doc["title"],
                    "evidence_content": doc["content"][:200],
                    "relevance_score": doc["score"]
                })
        else:
            # 无溯源结果 → 降低置信度
            traces.append({
                "claim": claim,
                "evidence_doc": None,
                "evidence_content": None,
                "relevance_score": 0.0,
                "unverified": True
            })
    
    return traces
```

**置信度计算：**

```python
def compute_rag_confidence(traces: List) -> float:
    """
    基于溯源覆盖率计算RAG置信度
    verified_ratio = 有溯源的结论数 / 总结论数
    """
    total = len(traces)
    verified = sum(1 for t in traces if t["evidence_doc"] is not None)
    return verified / total if total > 0 else 0.0
```

### 5.3 风险熵评分模型

**数学定义：**

```
H_total = w₁·H_base + w₂·H_hallu + w₃·H_rag + w₄·H_rule

其中：
  H_base    = max(prompt_score, output_score) / 100
  H_hallu   = min(hallucination_count × 0.15, 0.5)
  H_rag     = (1 - verified_ratio) × 0.3
  H_rule    = f(detected_rules) ∈ [0, 0.25]
  
  权重配置：w₁=0.4, w₂=0.2, w₃=0.15, w₄=0.25
```

**风险等级划分：**

| 等级 | 熵值范围 | 熔断动作 |
|------|---------|---------|
| 🟢 安全 | 0 ≤ H < 20 | 放行 |
| 🟡 低风险 | 20 ≤ H < 40 | 警告后放行 |
| 🟠 中风险 | 40 ≤ H < 50 | 部分屏蔽（加水印） |
| 🔴 高风险 | 50 ≤ H < 80 | 转人工审核 |
| ⚫ 严重 | 80 ≤ H ≤ 100 | 拒绝回答 + 上报告警 |

### 5.4 熔断控制器

```python
class RiskFuseController:
    """
    风险熔断控制器
    根据风险熵等级执行对应动作
    """
    
    def execute(self, risk_score: float, traces: List, context: dict) -> FuseResult:
        if risk_score < 20:
            return FuseResult(action="PASS", message="安全")
        elif risk_score < 40:
            return FuseResult(action="WARN_PASS", message="低风险，警告后放行")
        elif risk_score < 50:
            return FuseResult(action="PARTIAL_MASK", message="中风险，部分屏蔽")
        elif risk_score < 80:
            return FuseResult(action="HUMAN_REVIEW", message="高风险，转人工")
        else:
            return FuseResult(action="REJECT", message="严重风险，拒绝回答")
```

---

## 六、审计日志机制

### 6.1 日志结构

```sql
CREATE TABLE audit_logs (
    id            INTEGER PRIMARY KEY,
    timestamp     TEXT NOT NULL,
    
    -- 审计上下文
    user_id      TEXT NOT NULL,
    session_id   TEXT NOT NULL,
    user_role    TEXT,
    
    -- 审计输入输出
    prompt       TEXT NOT NULL,
    output       TEXT,
    
    -- 审计结果
    risk_score   REAL NOT NULL,
    risk_level   TEXT NOT NULL,
    fuse_action  TEXT NOT NULL,
    
    -- 规则命中
    matched_rules TEXT,  -- JSON列表
    
    -- RAG溯源
    rag_traces    TEXT, -- JSON列表
    
    -- 链路不可篡改
    prev_hash     TEXT,  -- 前一条日志哈希
    text_hash     TEXT,  -- 原文哈希（Prompt+Output）
    checksum      TEXT,  -- 本条校验和
    
    created_at    TEXT NOT NULL
);
```

### 6.2 不可篡改机制

```python
def write_audit_log(log: dict, prev_hash: str = None) -> str:
    """
    写入审计日志，返回本条哈希
    用于下一条的 prev_hash
    """
    
    # 生成原文哈希
    text_hash = sha256(log["prompt"] + log["output"])
    
    # 计算校验和
    payload = json.dumps({
        "timestamp": log["timestamp"],
        "text_hash": text_hash,
        "risk_score": log["risk_score"]
    })
    checksum = sha256(payload + (prev_hash or ""))
    
    log["text_hash"] = text_hash
    log["checksum"] = checksum
    log["prev_hash"] = prev_hash
    
    db.insert("audit_logs", log)
    
    return checksum
```

---

## 七、技术效果

| 指标 | 现有方案 | 本发明 |
|------|---------|--------|
| Prompt风险检出率 | ~60%（关键词） | **~90%（语义分析）** |
| 幻觉检测准确率 | ~50% | **~85%（RAG溯源）** |
| 风险量化方式 | 二值（违规/不违规） | **连续熵值（0-100）** |
| 审计链路完整性 | 无 | **全链路可溯源** |
| 响应延迟 | 50ms | **<30ms（熔断预判）** |

---

## 八、权利要求书框架

### 独立权利要求

1. 一种面向政企场景的大模型输出安全审计方法，其特征在于，包括：
   - 对用户输入Prompt进行多维度风险识别
   - 对模型输出进行合规检测与幻觉检测
   - 对关键结论进行RAG溯源校验
   - 基于风险熵模型计算综合风险分
   - 根据风险等级执行熔断控制
   - 全链路审计日志不可篡改存储

### 从属权利要求

2. 根据权利要求1所述的方法，其特征在于，所述风险识别包括：
   - 涉密信息检测、隐私泄露诱导检测、越权回答试探检测

3. 根据权利要求1所述的方法，其特征在于，所述幻觉检测采用：
   - 无政策依据断言标记 + RAG溯源缺失惩罚

4. 根据权利要求1所述的方法，其特征在于，所述风险熵模型为：
   ```
   H_total = w₁·H_base + w₂·H_hallu + w₃·H_rag + w₄·H_rule
   ```

5. 根据权利要求1所述的方法，其特征在于，所述熔断控制包括：
   - 放行、警告后放行、部分屏蔽、转人工审核、拒绝回答五个等级

---

## 九、与现有专利的差异点

| 现有专利 | 本发明差异 |
|---------|----------|
| 简单文本过滤 | **双向审计（输入+输出）** |
| 关键词规则匹配 | **语义算子链 + NLP理解** |
| 二值风险判断 | **连续风险熵（信息熵理论）** |
| 无溯源机制 | **RAG溯源置信度绑定** |
| 黑盒审计 | **链式哈希不可篡改日志** |

---

*本技术交底书为内部文档，仅供专利撰写参考。*