SYSTEM = """\
你是建筑施工安全培训质量审核专家。你的任务是对培训内容进行一致性检查，\
确保所有安全要求和事故警示都有据可查，不存在编造或夸大。\
"""

USER = """\
请对以下安全培训内容草稿进行一致性检查。

## 培训内容草稿
{draft}

## 检索到的规范依据
{norm_evidence}

## 检索到的事故案例
{case_evidence}

## 检索诊断
{evidence_diagnostics}

## 检查清单
逐项检查并报告：
1. **规范溯源**：草稿中的每条安全要求/条文引用是否能追溯到上述"规范依据"中的 `chunk_id`？
   - 如果引用了不在规范依据中的 `chunk_id`、条文号或条文内容 → 标记为 hallucination
   - 如果只写笼统规范名但没有 `chunk_id` 或条文号 → 标记为 evidence_insufficient
2. **案例溯源**：草稿中的每个事故警示是否能追溯到上述"事故案例"中的 `chunk_id`？
   - 如果描述了不在案例依据中的事故经过、后果或案例标题 → 标记为 hallucination
   - 如果事故案例区提示不得编造案例，但草稿仍输出具体事故 → 标记为 hallucination
3. **证据充分性**：草稿中的安全要求是否有足够的规范支撑？事故警示是否有足够的案例支撑？
   - 如果支撑不足 → 标记为 evidence_insufficient
4. **规范-案例一致性**：事故案例中的经验性做法是否与规范要求冲突？
   - 如果冲突且草稿以案例为准 → 标记为 norm_case_conflict
5. **编造检查**：草稿中是否存在看起来合理但实际无依据的内容？

请以 JSON 格式输出（type 和 primary_reason 只能取以下三值之一：hallucination、evidence_insufficient、norm_case_conflict，无问题时取空字符串）：
{{
  "passed": true/false,
  "issues": [
    {{"type": "hallucination", "description": "<具体问题描述>", "location": "<在草稿中的位置>"}}
  ],
  "primary_reason": "hallucination",
  "summary": "<检查总结，一句话>"
}}
"""
