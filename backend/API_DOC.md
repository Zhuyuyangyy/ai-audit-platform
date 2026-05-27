# GovShield API 文档

> 政务AI合规审计平台 — 文档风险热力图、语义政策搜索、监管影响评估

**版本**: 1.0  
**基础路径**: `/api/v1/compliance`  
**认证**: 无

---

## 目录

- [POST /risk_heatmap](#post-risk_heatmap) — 文档风险热力图
- [GET /policy_search](#get-policy_search) — 语义政策搜索
- [POST /impact_assessment](#post-impact_assessment) — 监管影响评估
- [GET /dashboard_stats](#get-dashboard_stats) — 仪表盘统计

---

## POST /risk_heatmap

对文档进行逐条风险分析，生成可视化热力图，识别高风险条款。

### 请求

**URL**: `POST /api/v1/compliance/risk_heatmap`

**Content-Type**: `application/json`

**Body 参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `document_text` | `string` | ❌ | 文档文本，按换行分段分析。默认分析5条模拟条款 |
| `document_type` | `string` | ❌ | 文档类型，默认 `"policy"` |

### 请求示例

```json
{
  "document_text": "数据收集条款\n用户同意条款\n责任限制条款\n隐私保护条款\n知识产权条款",
  "document_type": "policy"
}
```

### 响应

**Content-Type**: `application/json`

**Body 参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `heatmap` | `object[]` | 各条款风险分析结果 |
| `heatmap[].section` | `string` | 条款编号或摘要 |
| `heatmap[].risk_level` | `number` | 风险等级（0~1，1为最高） |
| `heatmap[].risk_type` | `string` | 风险类型 |
| `heatmap[].highlight` | `string` | 风险描述 |
| `heatmap[].suggestion` | `string` | 整改建议 |
| `overall_risk` | `number` | 整体风险评分（0~1） |
| `recommendations` | `string[]` | 高风险条款的整改建议（risk_level > 0.6） |
| `document_type` | `string` | 输入的文档类型 |

### 响应示例

```json
{
  "heatmap": [
    {
      "section": "第1条",
      "risk_level": 0.72,
      "risk_type": "数据过度收集",
      "highlight": "存在数据收集范围过广",
      "suggestion": "增加数据收集范围限定"
    },
    {
      "section": "第2条",
      "risk_level": 0.45,
      "risk_type": "单方面条款",
      "highlight": "存在单方面终止权",
      "suggestion": "增加对等终止条款"
    }
  ],
  "overall_risk": 0.583,
  "recommendations": ["增加数据收集范围限定"],
  "document_type": "policy"
}
```

### 风险类型分类

| 风险类型 | 说明 |
|----------|------|
| `数据过度收集` | 数据收集范围过广 |
| `单方面条款` | 存在不平等终止权 |
| `模糊定义` | 免责条款定义不清 |
| `高额违约金` | 违约金超出合理范围 |
| `免责条款过宽` | 平台免责范围过大 |
| `用户同意不完整` | 缺乏有效的用户撤回权 |

### 风险等级阈值

| 风险等级 | 阈值 | 建议 |
|----------|------|------|
| 低风险 | 0.0 ~ 0.4 | 通过 |
| 中风险 | 0.4 ~ 0.6 | 建议修改 |
| 高风险 | 0.6 ~ 1.0 | 必须整改 |

---

## GET /policy_search

基于语义相似度搜索相关政策法规条款。

### 请求

**URL**: `GET /api/v1/compliance/policy_search`

**Query 参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `q` | `string` | ❌ | 搜索关键词，为空则返回全部政策 |

### 请求示例

```
GET /api/v1/compliance/policy_search?q=个人信息保护
```

### 响应

**Content-Type**: `application/json`

**Body 参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `relevant_policies` | `object[]` | 相关政策列表 |
| `relevant_policies[].title` | `string` | 政策标题 |
| `relevant_policies[].relevance` | `number` | 相关度（0~1） |
| `relevant_policies[].matching_excerpt` | `string` | 匹配条款摘要 |
| `answer` | `string` | 自然语言回答摘要 |
| `query` | `string` | 输入的查询词 |

### 响应示例

```json
{
  "relevant_policies": [
    {
      "title": "《个人信息保护法》第21条",
      "relevance": 0.92,
      "matching_excerpt": "数据处理者向第三方提供个人信息须取得单独同意"
    },
    {
      "title": "《数据安全法》第27条",
      "relevance": 0.85,
      "matching_excerpt": "开展数据安全风险评估并留存相关记录"
    }
  ],
  "answer": "根据《个人信息保护法》第21条，数据处理者向第三方提供个人信息须取得单独同意。对于您查询的'个人信息保护'相关内容，核心要求是确保数据主体知情并同意。",
  "query": "个人信息保护"
}
```

### 内置政策库

| 政策标题 | 相关度 |
|----------|--------|
| 《个人信息保护法》第21条 | 0.92 |
| 《数据安全法》第27条 | 0.85 |
| 《生成式AI服务管理暂行办法》第12条 | 0.78 |
| 《政务数据共享管理条例》第15条 | 0.71 |

---

## POST /impact_assessment

评估新政策/法规对特定行业和地区的影响，输出合规成本和收益分析。

### 请求

**URL**: `POST /api/v1/compliance/impact_assessment`

**Content-Type**: `application/json`

**Body 参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `new_policy_text` | `string` | ❌ | 新政策文本内容（当前预留） |
| `affected_industries` | `string[]` | ❌ | 受影响行业列表，默认 `["电商", "金融"]` |
| `regions` | `string[]` | ❌ | 受影响地区，默认 `["全国"]` |

### 请求示例

```json
{
  "new_policy_text": "关于加强人工智能治理的若干规定...",
  "affected_industries": ["电商", "金融", "医疗"],
  "regions": ["华东地区"]
}
```

### 响应

**Content-Type**: `application/json`

**Body 参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `impact_score` | `number` | 影响评分（0~10） |
| `affected_parties` | `string[]` | 受影响主体估算 |
| `compliance_costs` | `string` | 预估合规成本范围 |
| `benefits` | `string` | 预期收益说明 |
| `recommendation` | `string` | 建议行动（`proceed_with_caution` / `need_review` / `should_reject`） |
| `industries` | `string[]` | 输入的行业列表 |
| `regions` | `string[]` | 输入的地区列表 |

### 推荐行动阈值

| 评分区间 | 推荐行动 | 说明 |
|----------|----------|------|
| > 7 分 | `proceed_with_caution` | 高影响，审慎推进 |
| 5 ~ 7 分 | `need_review` | 中影响，需要复核 |
| < 5 分 | `should_reject` | 低影响，建议拒绝/重新评估 |

### 响应示例

```json
{
  "impact_score": 7.3,
  "affected_parties": ["电商企业约25000家", "金融企业约12000家", "医疗企业约8000家"],
  "compliance_costs": "¥180M-350M",
  "benefits": "提升数据安全水平，增强公众信任，促进数据合规流通",
  "recommendation": "proceed_with_caution",
  "industries": ["电商", "金融", "医疗"],
  "regions": ["华东地区"]
}
```

---

## GET /dashboard_stats

获取平台整体运营统计指标，供仪表盘展示。

### 请求

**URL**: `GET /api/v1/compliance/dashboard_stats`

**Query 参数**: 无

### 响应

**Content-Type**: `application/json`

**Body 参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `documents_reviewed` | `number` | 已审查文档总数 |
| `risk_detected` | `number` | 检测到风险的文档数 |
| `compliance_rate` | `number` | 合规率（%），0~100 |
| `avg_review_time_minutes` | `number` | 平均审查时长（分钟） |
| `risk_distribution` | `object` | 风险分布 `{high, medium, low}` |
| `trend` | `string` | 趋势：`improving` / `declining` / `stable` |

### 响应示例

```json
{
  "documents_reviewed": 1247,
  "risk_detected": 187,
  "compliance_rate": 91.3,
  "avg_review_time_minutes": 8.5,
  "risk_distribution": {
    "high": 45,
    "medium": 120,
    "low": 235
  },
  "trend": "improving"
}
```

### 统计口径说明

| 指标 | 计算方式 |
|------|----------|
| 合规率 | `(documents_reviewed - risk_detected) / documents_reviewed * 100%` |
| 平均审查时长 | 所有文档审查耗时的算术平均 |
| 高/中/低风险 | 根据风险评分分布统计 |

---

## 通用错误响应

所有端点在出错时返回标准HTTP状态码和以下JSON结构：

```json
{
  "detail": "错误描述"
}
```

| HTTP状态码 | 说明 |
|-----------|------|
| `400` | 请求参数错误 |
| `404` | 资源不存在（如审计日志） |
| `500` | 服务器内部错误 |

---

## 技术栈

- **框架**: FastAPI
- **数据库**: SQLite (`ai_audit_platform.db`)
- **数据验证**: Pydantic
- **知识库**: 内置政策摘要（无外部RAG依赖）