# 给 Claude Code 的下一步执行说明

## Summary

先做**最小可运行原型**，不要一次性实现完整论文系统。目标是搭出一个可跑通的 Agentic RAG 骨架：输入高危作业主题，经过情境生成、风险规划、规范检索、案例检索、证据融合、一致性检查，最后输出一套作业前安全培训材料。

当前先不关心真实数据，使用 2-3 条 mock 规范和 mock 事故案例即可。

## 技术栈决策

- 框架：使用 `LangGraph`，因为后续需要表达 `Consistency Checker 不通过 -> 回退重检索/改写` 的状态流。
- 包管理：使用 `requirements.txt`，不要用 Poetry，项目当前已在现有环境中开发。
- 向量库：v1 使用 `Chroma`，轻量、可持久化、适合原型。
- Embedding：v1 使用 `BAAI/bge-large-zh-v1.5`，中文施工安全文本优先；先不做 reranker。
- LLM：使用 OpenAI-compatible client，配置项支持 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`LLM_MODEL`，默认模型名写成 `deepseek-chat`。
- 检索策略：v1 只做向量检索 + 元数据过滤；BM25、混合检索、reranker 放到后续 baseline/优化实验。
- PDF 解析：使用 `pdfplumber`，备用 `pymupdf`。

## 项目结构

在当前目录创建原型项目结构：

```text
src/
  config.py
  schema/
    document.py
    state.py
    training.py
  data_pipeline/
    loader.py
    sample_data.py
  retrieval/
    vector_store.py
    norm_retriever.py
    case_retriever.py
  agents/
    graph.py
    scenario_agent.py
    risk_planner.py
    evidence_fusion.py
    consistency_checker.py
    training_agent.py
  prompts/
    scenario.py
    risk_planner.py
    fusion.py
    checker.py
    training.py
scripts/
  build_sample_index.py
  run_training.py
data/
  sample/
requirements.txt
.env.example
README.md
```

## 核心数据结构

`NormChunk` 字段：

```python
doc_type: Literal["norm"]
chunk_id: str
standard_name: str
chapter: str | None
article_id: str | None
text: str
scenario_tags: list[str]
hazard_tags: list[str]
requirement_type: str | None
source: str | None
```

`CaseChunk` 字段：

```python
doc_type: Literal["case"]
chunk_id: str
case_title: str
accident_type: str | None
scenario_tags: list[str]
hazard_tags: list[str]
process: str | None
causes: str | None
consequences: str | None
corrective_measures: str | None
text: str
source: str | None
```

`TrainingState` 至少包含：

```python
topic: str
training_scenario: str | None
hazards_identified: list[str]
norm_queries: list[str]
case_queries: list[str]
norm_evidence: list[NormChunk]
case_evidence: list[CaseChunk]
fused_evidence: dict
draft_training_output: dict | None
consistency_passed: bool
consistency_issues: list[str]
final_training_output: dict | None
retry_count: int
```

## LangGraph 节点接口

### ScenarioAgent

- 输入：`topic`
- 输出：`training_scenario`
- 行为：把宽泛主题聚焦成一个具体作业前培训情境。
- 约束：不生成工人画像，不使用年龄、岗位、违章记录等个人信息。

### RiskPlanner

- 输入：`topic`, `training_scenario`
- 输出：`hazards_identified`, `norm_queries`, `case_queries`
- 行为：识别该情境下应覆盖的危险源，并拆成规范检索问题和事故案例检索问题。

### NormRetriever

- 输入：`norm_queries`, `hazards_identified`
- 输出：`norm_evidence`
- 行为：从规范 chunk 中召回相关条文。

### CaseRetriever

- 输入：`case_queries`, `hazards_identified`
- 输出：`case_evidence`
- 行为：从事故案例 chunk 中召回相似事故。

### EvidenceFusionAgent

- 输入：`training_scenario`, `hazards_identified`, `norm_evidence`, `case_evidence`
- 输出：`fused_evidence`, `draft_training_output`
- 行为：形成“场景-风险-规范要求-事故后果-预防措施”的培训逻辑链。

### ConsistencyChecker

- 输入：`draft_training_output`, `norm_evidence`, `case_evidence`
- 输出：`consistency_passed`, `consistency_issues`
- 行为：检查安全要求是否有规范依据、事故警示是否有案例依据、是否存在编造条文或案例。
- 分支：若不通过且 `retry_count < 1`，回到 `EvidenceFusionAgent` 改写；否则进入 `TrainingAgent`，但在输出中标注证据不足。

### TrainingAgent

- 输入：全部状态
- 输出：`final_training_output`
- 行为：生成最终训练材料，包括作业情境、风险识别题、规范依据、事故警示、操作要点、补训反馈、小测题。

## 最小样例数据

先在 `data/sample/` 内提供硬编码 JSONL 或 Python mock 数据：

- 2 条规范 chunk：
  - 高处作业临边防护
  - 临时用电配电箱/漏电保护
- 2 条事故案例 chunk：
  - 高处坠落事故
  - 触电事故

不要等待真实规范和案例数据，先保证流程跑通。

## 运行脚本

`requirements.txt` 包含：

```text
langgraph
langchain-core
openai
python-dotenv
pydantic
chromadb
sentence-transformers
pdfplumber
pymupdf
```

`.env.example` 包含：

```text
OPENAI_API_KEY=
OPENAI_BASE_URL=
LLM_MODEL=deepseek-chat
EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5
CHROMA_DIR=data/chroma
```

`scripts/build_sample_index.py`：

- 读取 sample 数据；
- 构建 Chroma collection；
- 分别建立 norm/case 两类文档；
- metadata 中必须保留 `doc_type`、`scenario_tags`、`hazard_tags`。

`scripts/run_training.py`：

- 默认 topic：`脚手架拆除作业前安全培训`
- 调用 LangGraph；
- 在终端打印 `final_training_output`；
- 输出必须包含规范依据和事故案例依据。

## 验收标准

完成后必须能运行：

```bash
python scripts/build_sample_index.py
python scripts/run_training.py
```

运行结果至少包含：

- 一个具体作业情境；
- 3 个以上危险源；
- 至少 1 条规范依据；
- 至少 1 条事故案例警示；
- 一段操作要点；
- 一个风险识别问题；
- 2-3 道小测题；
- 一致性检查结果。

## 当前不要做

- 不要实现知识图谱。
- 不要实现移动端 App。
- 不要实现真实数据清洗大流程。
- 不要做完整评测系统。
- 不要做 BM25、reranker、复杂多路召回。
- 不要把工人画像作为主输入。

这一阶段只做可运行原型，证明“高危作业情境 + 规范/事故双证据 + Agentic RAG 训练闭环”能走通。

