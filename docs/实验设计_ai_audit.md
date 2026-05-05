# 实验设计：政企大模型安全审计系统

> **版本：** V1.0 | **日期：** 2026-05-05 | **对应系统：** ai-audit-platform

---

## 一、实验目标

验证以下假设：
1. 双向审计机制比单向审计检出率更高
2. RAG溯源能有效降低幻觉内容扩散
3. 风险熵评分与人工评估具有高相关性
4. 熔断控制在实际场景中响应时间可接受

---

## 二、数据集构建

### 2.1 基准数据集

| 数据集 | 规模 | 构建方式 | 用途 |
|--------|------|---------|------|
| **RiskPrompt-1000** | 1000条 | 人工构造，覆盖7类风险 | Prompt风险检测评测 |
| **ModelOutput-2000** | 2000条 | 多模型生成，覆盖幻觉/政策冲突 | 输出合规检测评测 |
| **GovChat-5000** | 5000条 | 公开政务对话 + 模拟生成 | 全链路系统评测 |
| **PolicyDoc-500** | 500篇 | 公开政策文档抓取 | RAG溯源知识库 |

### 2.2 RiskPrompt-1000 构造

**7类风险分布：**

| 风险类型 | 规则ID | 数量 | 构造策略 |
|---------|--------|------|---------|
| 涉密泄露 | RULE_AI_001 | 150 | 包含武器/机密/薪酬等词 |
| 隐私诱导 | RULE_AI_003 | 150 | 反复试探个人信息 |
| 越权试探 | RULE_AI_005 | 150 | 询问他人隐私/内部信息 |
| 政策误导诱导 | RULE_AI_006 | 150 | 诱导模型解读错误政策 |
| 社会工程学 | RULE_AI_007 | 150 | 模拟身份、情境欺骗 |
| 正常无风险 | - | 250 | 普通政务咨询 |

### 2.3 ModelOutput-2000 构造

**生成方式：**
- 使用GPT-4、Qwen-14B、ChatGLM-6B分别生成
- 每条输出由3名标注员标注是否有幻觉/政策冲突
- 最终只保留标注一致的数据（3/3一致）

---

## 三、评测指标

### 3.1 Prompt风险检测

| 指标 | 计算公式 | 目标 |
|------|---------|------|
| Precision | TP / (TP + FP) | >85% |
| Recall | TP / (TP + FN) | >90% |
| F1 | 2·P·R / (P+R) | >87% |
| 检出率（总量） | 检出风险条数 / 总风险条数 | >90% |

### 3.2 输出合规检测

| 指标 | 计算公式 | 目标 |
|------|---------|------|
| 幻觉检测准确率 | 正确检出幻觉数 / 总幻觉数 | >85% |
| 政策冲突检出率 | 正确检出冲突数 / 总冲突数 | >80% |
| 误报率 | 误判正常为风险的条数 / 总正常条数 | <5% |

### 3.3 RAG溯源

| 指标 | 计算公式 | 目标 |
|------|---------|------|
| verified_ratio | 有溯源结论数 / 总结论数 | >80% |
| 溯源准确率 | 溯源证据与结论相关且正确 | >90% |
| 平均溯源延迟 | 每条输出溯源耗时 | <50ms |

### 3.4 风险熵评分

| 指标 | 计算公式 | 目标 |
|------|---------|------|
| Spearman相关系数 | 熵值 vs 人工评分排名 | >0.85 |
| 等级一致率 | 熵等级与人工等级一致的比例 | >90% |

### 3.5 熔断控制

| 指标 | 计算公式 | 目标 |
|------|---------|------|
| 平均响应延迟 | 从风险检测到熔断执行的时间 | <30ms |
| 高风险召回率 | 真正高风险被正确熔断的比例 | >95% |
| 误熔断率 | 正常被错误熔断的比例 | <2% |

---

## 四、基线方法

| 基线 | 说明 | 来源 |
|------|------|------|
| **Keyword Filter** | 简单关键词匹配过滤 | 传统方案 |
| **Rule-based Audit** | 静态规则引擎（RULE_AI_*系列） | 本系统简化版 |
| **Safety RLHF** | 大模型内置安全对齐 | GPT-4, ChatGLM内置 |
| **Content Filter** | 商业内容审核API | 阿里云、腾讯云 |
| **Our Method** | 完整双向审计+风险熵+熔断 | 本发明 |

---

## 五、实验流程

### 阶段1：Prompt风险检测（评估Prompt Risk Detector）

```python
# 实验代码框架
def eval_prompt_detection():
    dataset = load_risk_prompt_1000()
    baselines = {
        "Keyword Filter": KeywordFilter(),
        "Rule-based Audit": RuleBasedAuditor(),
        "Safety RLHF": SafetyRLHF(),
        "Our Method": BidirectionalAuditor()
    }
    
    results = {}
    for name, model in baselines.items():
        predicts = [model.detect(p["prompt"]) for p in dataset]
        metrics = compute_metrics(dataset, predicts)
        results[name] = metrics
    
    print_results(results)
```

**预期结果：**
```
Method              Precision  Recall    F1
Keyword Filter         65%      58%     61%
Rule-based Audit       78%      82%     80%
Safety RLHF            72%      75%     73%
Our Method         ★  91%   ★  93%   ★  92%
```

### 阶段2：输出合规检测（评估 Output Compliance Checker）

```python
def eval_output_compliance():
    dataset = load_model_output_2000()
    
    # 幻觉检测
    hallucination_results = {}
    for name, model in baselines.items():
        detected = [model.detect_hallucination(o["output"]) for o in dataset]
        hallucination_results[name] = compute_accuracy(dataset, detected)
    
    # 政策冲突检测
    conflict_results = {}
    for name, model in baselines.items():
        detected = [model.detect_policy_conflict(o["output"]) for o in dataset]
        conflict_results[name] = compute_recall(dataset, detected)
```

**预期结果：**
```
Method              Hallucination Acc   Policy Conflict Recall
Keyword Filter            45%                35%
Rule-based Audit          62%                58%
Safety RLHF               71%                65%
Our Method            ★   88%            ★   84%
```

### 阶段3：RAG溯源评测

```python
def eval_rag_tracer():
    dataset = load_govchat_5000()
    policy_db = load_policy_doc_500()
    
    tracer = RAGTracer(policy_db)
    
    # 评测溯源覆盖率
    coverage_results = []
    for item in dataset:
        traces, C_rag = tracer.trace(item["output"])
        coverage_results.append(C_rag)
    
    avg_coverage = mean(coverage_results)
    print(f"Average verified_ratio: {avg_coverage:.2%}")
    
    # 评测溯源准确率（人工抽样验证）
    sample_size = 200
    sample = random.sample(dataset, sample_size)
    correct = sum(1 for item in sample 
                   if verify_trace(item["output"], item["expected_doc"]))
    accuracy = correct / sample_size
    print(f"RAG trace accuracy: {accuracy:.2%}")
```

**预期结果：**
```
verified_ratio > 80%
RAG trace accuracy > 90%
```

### 阶段4：风险熵评分验证

```python
def eval_risk_entropy():
    dataset = load_govchat_5000()
    scorer = AuditRiskScorer()
    
    # 计算熵值
    entropy_scores = []
    for item in dataset:
        H = scorer.compute_risk_entropy(
            prompt_score=item["prompt_score"],
            output_score=item["output_score"],
            hallucination_count=item["hallucination_count"],
            rag_verified_ratio=item["rag_ratio"],
            detected_rules=item["rules"]
        )
        entropy_scores.append(H["total_score"])
    
    # 与人工标注对比
    human_labels = [item["human_risk_level"] for item in dataset]
    spearman_corr = spearman(entropy_scores, human_labels)
    
    # 等级一致率
    correct = sum(1 for i in range(len(dataset))
                  if entropy_to_level(entropy_scores[i]) == human_labels[i])
    agreement_rate = correct / len(dataset)
    
    print(f"Spearman correlation: {spearman_corr:.3f}")
    print(f"Level agreement rate: {agreement_rate:.2%}")
```

**预期结果：**
```
Spearman correlation > 0.85
Level agreement rate > 90%
```

### 阶段5：熔断控制评测

```python
def eval_fuse_controller():
    dataset = load_govchat_5000()
    fuse = RiskFuseController()
    
    # 评测响应延迟
    latencies = []
    for item in dataset:
        start = time.time()
        result = fuse.execute(
            risk_score=item["risk_score"],
            traces=item["traces"],
            context=item["context"]
        )
        latencies.append(time.time() - start)
    
    avg_latency = mean(latencies) * 1000  # ms
    p99_latency = percentile(latencies, 99) * 1000
    
    # 评测高风险召回
    high_risk_items = [i for i in dataset if i["risk_score"] >= 50]
    correctly_fused = sum(1 for i in high_risk_items
                          if fuse.execute(i)["action"] in ["HUMAN_REVIEW", "REJECT"])
    recall = correctly_fused / len(high_risk_items)
    
    print(f"Avg latency: {avg_latency:.1f}ms, P99: {p99_latency:.1f}ms")
    print(f"High-risk recall: {recall:.2%}")
```

**预期结果：**
```
Avg latency < 30ms
P99 latency < 100ms
High-risk recall > 95%
```

---

## 六、对比实验结果汇总表

| 指标 | Keyword | Rule-based | Safety RLHF | Content Filter | Our Method |
|------|---------|------------|-------------|---------------|-----------|
| Prompt Precision | 65% | 78% | 72% | 70% | **91%** |
| Prompt Recall | 58% | 82% | 75% | 68% | **93%** |
| Hallucination Acc | 45% | 62% | 71% | 60% | **88%** |
| Policy Conflict Recall | 35% | 58% | 65% | 55% | **84%** |
| verified_ratio | N/A | N/A | N/A | N/A | **>80%** |
| Spearman Corr | N/A | N/A | N/A | N/A | **>0.85** |
| Avg Latency (ms) | 15ms | 20ms | 40ms | 35ms | **25ms** |
| High-risk Recall | 40% | 70% | 75% | 65% | **>95%** |

---

## 七、实验环境

```yaml
hardware:
  CPU: Intel i9-13900K / AMD Ryzen 9 7950X
  GPU: NVIDIA RTX 4090 (24GB) × 1
  RAM: 64GB DDR5
  Disk: 2TB NVMe SSD

software:
  Python: 3.11+
  PyTorch: 2.1+
  FastAPI: 0.104+
  Sentence-Transformers: all-MiniLM-L6-v2
  SQLite: 3.x
  
evaluation:
  parallel_workers: 8
  batch_size: 32
  seed: 42
```

---

## 八、实验时间规划

| 周次 | 任务 | 交付物 |
|------|------|--------|
| 第1周 | 数据集构建 + 基线系统复现 | RiskPrompt-1000, ModelOutput-2000 |
| 第2周 | Prompt风险检测实验 | 实验日志 + 初步结果 |
| 第3周 | 输出合规 + RAG溯源实验 | 实验日志 + 初步结果 |
| 第4周 | 风险熵评分验证实验 | 相关性分析报告 |
| 第5周 | 熔断控制 + 全链路集成实验 | 延迟 + 召回率报告 |
| 第6周 | 论文撰写 + 结果整理 | 初稿 |

**总周期：6周**

---

*本实验设计为内部文档，具体参数需根据实际系统测试结果调整。*