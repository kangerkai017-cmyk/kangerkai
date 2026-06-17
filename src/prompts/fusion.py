SYSTEM = """\
你是建筑安全培训内容整合专家。你的任务是将施工安全规范条文与事故案例融合，\
形成"场景-风险-规范要求-事故后果-预防措施"的完整培训逻辑链。\
"""

USER = """\
请根据以下信息，整合生成安全培训内容。

## 作业场景
{scenario}

## 已识别危险源
{hazards}

## 规范依据（施工安全规范条文）
{norm_evidence}

## 事故案例（相似施工事故）
{case_evidence}

## 检索诊断
{evidence_diagnostics}

## 要求
1. 安全要求必须能追溯到上述规范条文，必须引用检索证据中的 `chunk_id`、`standard_code`、`article_id` 和 `source`，不得编造条文号或条文内容。
2. 事故警示必须来自上述事故案例，必须引用案例证据中的 `chunk_id` 和 `source`，不得编造事故经过、后果或案例标题。
3. 如果某项规范或案例证据不足，请如实标注"暂无相关规范依据"或"暂无相似事故案例"。
4. 当事故案例中的经验性做法与规范要求冲突时，以规范要求为准。
5. 生成的内容应适合在作业前安全交底或班前教育场景中使用。
6. 如果事故案例区显示"当前未检索到事故案例证据；不得编造案例"，则 `case_warnings` 只能输出一条"暂无相似事故案例"占位，不得新增任何案例事实。
7. `norm_requirements` 和 `case_warnings` 只输出真实 `chunk_id`；完整条文、来源、案例信息由系统根据证据回填，不要复制长文本。

请以 JSON 格式输出：
{{
  "fused_evidence": {{
    "scene_summary": "<对作业场景的简要归纳>",
    "risk_analysis": "<针对该场景的风险分析，逐一说明每个危险源的触发条件和可能后果>",
    "norm_requirements": [
      {{"chunk_id": "<规范证据chunk_id>"}}
    ],
    "case_warnings": [
      {{"chunk_id": "<案例证据chunk_id，如无案例证据则为空列表>"}}
    ],
    "preventive_measures": ["<按作业前/作业中/作业后分阶段的具体预防措施>"]
  }},
  "draft_training_output": {{
    "scenario_description": "<作业情境描述，用于呈现给学习者>",
    "hazard_identification_question": "<要求学习者识别危险源的提问>",
    "expected_hazards": ["<从已识别危险源中取3-5个最关键的，每条≤30字>"],
    "norm_requirements": [{{"chunk_id": "<复制自 fused_evidence 的真实chunk_id>"}}],
    "accident_warnings": [{{"chunk_id": "<复制自 fused_evidence 的真实chunk_id，无案例则整个列表为空>"}}],
    "operation_points": ["<作业前：...>", "<作业中：...>", "<作业后：...>"],
    "learner_evaluation_guide": "<2-4条评判标准，如：能说出X即为合格>",
    "remedial_feedback_guide": "<2-4条补充说明，如：常见漏答是X，正确做法是Y>",
    "quiz_questions": [
      {{"type": "choice", "question": "<题干>", "options": ["A. <选项>", "B. <选项>", "C. <选项>", "D. <选项>"], "answer": "B", "explanation": "<解析>"}}
    ]
  }}
}}
"""

USER_RETRY = """\
请根据以下信息，重新整合生成安全培训内容。

【重要】上一轮的一致性检查发现了以下问题，请在本次生成中修正：
{consistency_issues}

## 作业场景
{scenario}

## 已识别危险源
{hazards}

## 规范依据
{norm_evidence}

## 事故案例
{case_evidence}

## 检索诊断
{evidence_diagnostics}

## 要求（同上，略）
1. 安全要求必须能追溯到 `chunk_id`，不得编造。
2. 事故警示必须来自案例 `chunk_id`；没有案例证据时只能标注暂无相似事故案例。
3. 证据不足时如实标注。
4. 规范优先于案例经验。
5. 修正上一轮发现的所有一致性问题。

请以 JSON 格式输出（与上轮相同的结构）。
"""
