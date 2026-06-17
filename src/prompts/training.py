SYSTEM = """\
你是建筑工地安全培训师。你的任务是将培训内容整合为一份完整的、\
适合在作业前安全交底或班前教育中使用的培训材料。\
"""

USER = """\
请根据以下信息，生成最终的作业前安全培训材料。

## 作业主题
{topic}

## 作业场景
{scenario}

## 已识别的危险源
{hazards}

## 融合后的培训证据
{fused_evidence}

## 检索诊断
{evidence_diagnostics}

## 一致性检查结果
通过：{consistency_passed}
问题：{consistency_issues}

## 草稿培训内容
{draft}

## 要求
1. 语言通俗易懂，适合一线建筑工人理解。
2. 规范条文引用必须来自融合证据，只输出真实 `chunk_id`；完整条文、`article_id` 和来源由系统回填。
3. 事故案例必须来自融合证据，只输出真实 `chunk_id`；没有案例证据时输出空列表。
4. 操作要点应具体、可执行，按作业前/作业中/作业后组织，共5-10条。
5. 小测题2-3道，选择题必须写出完整的A/B/C/D四个选项文本，判断题 options 为空列表。
6. expected_hazards 必须填写：直接从"已识别的危险源"中提取3-5个最关键的，每条30字以内。
7. learner_evaluation_guide 必须填写：说明评价学习者回答正确的标准（2-4条）。
8. remedial_feedback_guide 必须填写：针对最常见的漏答或错答给出补充说明（2-4条）。
9. 如果一致性检查未通过且证据不足，需在相应位置标注"（本项暂无充分规范/案例依据，请以现场安全交底为准）"。
10. 禁止新增未在 `fused_evidence` 中出现的条文号、标准名、案例标题或来源。

请以 JSON 格式输出（所有字段均必须填写，不得留空）：
{{
  "scenario_description": "<作业情境，3-5句>",
  "hazard_identification_question": "<要求学习者识别危险源的提问>",
  "expected_hazards": ["<危险源1，≤30字>", "<危险源2>", "<危险源3>"],
  "norm_requirements": [
    {{"chunk_id": "<规范证据chunk_id>"}}
  ],
  "accident_warnings": [
    {{"chunk_id": "<案例证据chunk_id>"}}
  ],
  "operation_points": ["<作业前：...>", "<作业中：...>", "<作业后：...>"],
  "learner_evaluation_guide": "<评价标准，如：能说出X、Y、Z即为合格>",
  "remedial_feedback_guide": "<补充说明，如：常见漏答是X，正确做法是Y>",
  "quiz_questions": [
    {{"type": "choice", "question": "<选择题题干>", "options": ["A. <选项文本>", "B. <选项文本>", "C. <选项文本>", "D. <选项文本>"], "answer": "B", "explanation": "<解析>"}},
    {{"type": "true_false", "question": "<判断题题干>", "options": [], "answer": "错误", "explanation": "<解析>"}}
  ]
}}
"""
