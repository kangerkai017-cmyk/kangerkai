# 项目工程规划：脚手架、目录结构与技术栈

> 状态：历史规划文档。本文档记录项目早期的脚手架与技术栈候选方案，大部分内容已被后续执行文档更新。
>
> 当前执行优先级：
> 1. 研究主线以 `research_plan.md` 为准。
> 2. 已完成的最小原型阶段以 `docs/history/claude_next_steps.md` 为历史执行记录。
> 3. 下一阶段实施以 `next_phase_data_chunk_plan.md` 为准。
>
> 以下内容与当前代码的差异（仅列举，本文不作修改）：
> - 本文中的 Chroma 已被 Elasticsearch + RRF 混合检索方案取代。
> - 本文中的 `loader.py`、`chunker.py`、`labeler.py` 已被 `norm_chunker.py` 统一替代。
> - 本文中的 `sample_data.py` 已移除，mock 数据已清除。
> - 本文中的 Poetry 已被 `requirements.txt` 替代。
> - 本文中的 DeepSeek API 已被本地 `llama.cpp` Qwen3.5 9B 替代。
> - 本文中的 `data/sample/` 目录已清除。
> - `src/retrieval/` 中的正式后端为 `es_store.py`；`norm_retriever.py`、`case_retriever.py` 是 Agent-facing interface。
> - 本文中的 `src/evaluation/` 尚未实现。
>
> 本文所有技术栈选型、目录结构和模块列表仅作历史参考，不作为当前执行依据。
>
> 当前已确认技术路线以 `next_phase_data_chunk_plan.md` 为准：`LangGraph` + `requirements.txt` + `Elasticsearch` + `rrf_hybrid` + `BAAI/bge-large-zh-v1.5` + 本地 `llama.cpp` Qwen OpenAI-compatible 服务。本文中关于 Poetry、DeepSeek API、Chroma、候选技术栈等内容仅作历史参考。

> 本文档供 Codex 阅读后，产出模块接口规格书和 LangGraph StateGraph 设计。

---

## 1. 项目定位

基于 `research_plan.md`，本项目实现一个**面向高危作业情境的 Agentic RAG 安全培训系统**。核心流程：

```
用户指定高危作业主题
  → Scenario Agent 生成训练情境
    → Risk Planner 识别危险源 + 拆分检索目标
      → Norm Retriever + Case Retriever 双路检索
        → Evidence Fusion Agent 融合双证据
          → Consistency Checker 校验一致性
            → Training Agent 生成培训材料 + 评价 + 补训反馈
```

技术关键词：**LangGraph**、**Agentic RAG**、**双证据融合**、**一致性约束**、**中文施工安全领域**。

---

## 2. 技术栈选型（历史候选，已决策）

以下列出早期候选方案。当前实现已完成基础决策，后续不要再按本节重新选型，除非明确进入重构阶段。

### 2.1 框架

| 候选 | 优势 | 劣势 |
|------|------|------|
| **LangGraph** | 状态图原生支持多 Agent 流转、条件分支、回退重检索 | 学习曲线略高 |
| LangChain LCEL | 写法简洁，社区资料多 | 线性流程为主，分支/回退不好表达 |

**倾向 LangGraph**（因 Consistency Checker 存在"不通过 → 重新检索"的回退逻辑，且 7 个 Agent 节点有明确的状态流转关系）。

### 2.2 向量数据库

| 候选 | 优势 | 劣势 |
|------|------|------|
| **Elasticsearch + RRF** | 同时支持 BM25、dense vector、metadata/tag 多路召回，适合后续混合检索 | 需要本地 ES 服务 |
| FAISS | Meta 出品，检索速度快 | 无持久化内置支持 |
| Milvus Lite | 持久化 + 性能兼顾，Python 原生 | 混合检索和工程集成需额外设计 |

### 2.3 Embedding 模型

要求：中文语义理解、支持施工安全领域术语。

| 候选 | 维度 | 说明 |
|------|------|------|
| **BAAI/bge-large-zh-v1.5** | 1024 | 中文 MTEB 榜单前列 |
| BAAI/bge-m3 | 1024 | 多语言，支持稠密+稀疏混合检索 |
| text2vec-large-chinese | 1024 | 中文专用，轻量 |

### 2.4 LLM

要求：中文生成流畅、支持 function calling（LangGraph 工具调用）、上下文窗口足够。

| 候选 | 说明 |
|------|------|
| **DeepSeek API** | 中文能力强，成本低，支持 tool calling |
| Qwen API (通义千问) | 中文友好，有免费额度 |
| 本地部署 (vLLM + Qwen) | 数据不出域，但需要 GPU |

### 2.5 检索策略

| 候选 | 说明 |
|------|------|
| 纯向量检索 (semantic) | 简单，单路召回 |
| 混合检索 (向量 + BM25) | 精确关键词（如"JGJ 80-2016"条文号）不会被向量削弱 |
| 混合 + Reranker | 再排序提升精度，BAAI/bge-reranker-v2-m3 |

### 2.6 其他依赖

| 用途 | 候选 |
|------|------|
| 文档解析 | pdfplumber / pymupdf（规范和事故案例多为 PDF） |
| 结构化输出 | Pydantic（用于 State Schema、Agent 输入输出校验） |
| 日志/调试 | LangSmith 或本地 logging |
| 包管理 | Poetry / pip + venv |

---

## 3. 目录结构（草案）

```
safety-training-rag/
├── README.md
├── pyproject.toml              # Poetry 项目配置（或 requirements.txt）
├── .env.example                # API key 等环境变量模板
│
├── data/                       # 数据目录（不入 git）
│   ├── raw/                    # 原始 PDF/文本
│   │   ├── norms/              # 施工安全规范文件
│   │   └── cases/              # 事故案例文件
│   ├── chunks/                 # 切分并标注后的 chunk（JSONL）
│   │   ├── norm_chunks.jsonl
│   │   └── case_chunks.jsonl
│   └── test_tasks/             # 测试任务集（JSONL）
│       └── test_tasks.jsonl
│
├── src/
│   ├── __init__.py
│   │
│   ├── config.py               # 全局配置：模型名、API key、路径等
│   │
│   ├── schema/                 # 数据结构定义
│   │   ├── __init__.py
│   │   ├── document.py         # NormChunk, CaseChunk Pydantic 模型
│   │   ├── state.py            # LangGraph State Schema
│   │   └── training.py         # TrainingScenario, TrainingOutput 等
│   │
│   ├── data_pipeline/          # 模块 1-3：数据预处理
│   │   ├── __init__.py
│   │   ├── loader.py           # PDF/文本读取
│   │   ├── chunker.py          # 文档切分 + 元数据标注
│   │   └── labeler.py          # 场景/危险源标签体系
│   │
│   ├── retrieval/              # 模块 4：检索
│   │   ├── __init__.py
│   │   ├── es_store.py         # Elasticsearch 建索引 + 检索
│   │   ├── norm_retriever.py   # 规范检索器
│   │   └── case_retriever.py   # 案例检索器
│   │
│   ├── agents/                 # 模块 5：Agentic RAG 流程
│   │   ├── __init__.py
│   │   ├── graph.py            # LangGraph StateGraph 定义（主入口）
│   │   ├── scenario_agent.py   # 7.1 Scenario Agent
│   │   ├── risk_planner.py     # 7.2 Risk Planner
│   │   ├── evidence_fusion.py  # 7.5 Evidence Fusion Agent
│   │   ├── consistency_checker.py  # 7.6 Consistency Checker
│   │   └── training_agent.py   # 7.7 Training Agent
│   │
│   ├── prompts/                # Prompt 模板集中管理
│   │   ├── __init__.py
│   │   ├── scenario.py
│   │   ├── risk_planner.py
│   │   ├── fusion.py
│   │   ├── checker.py
│   │   └── training.py
│   │
│   └── evaluation/             # 模块 6-7：评测
│       ├── __init__.py
│       ├── metrics.py          # 自动评价指标
│       ├── test_runner.py      # 批量测试运行器
│       └── report.py           # 评测报告生成
│
├── tests/                      # 单元测试
│   ├── test_retrieval/
│   ├── test_agents/
│   └── test_evaluation/
│
├── notebooks/                  # 探索性分析（可选）
│   └── data_exploration.ipynb
│
└── scripts/                    # 运行脚本
    ├── build_index.py          # 构建向量索引
    ├── run_training.py         # 单次训练流程运行
    └── run_evaluation.py       # 批量评测运行
```

---

## 4. 需要 Codex 产出的内容

请 Codex 在阅读本文档和 `research_plan.md` 后，产出以下交付物：

### 4.1 技术栈确认

对 2.1 ~ 2.6 逐项给出推荐选择和理由（一句话即可）。

### 4.2 LangGraph State Schema

用 Pydantic TypedDict 或 dataclass 定义共享状态结构。需要包含：
- 所有 Agent 读取的字段（名称 + 类型）
- 所有 Agent 写入的字段（名称 + 类型）
- 状态在各节点间的流转关系（哪些字段被谁读、被谁写）

### 4.3 每个 Agent 模块的接口规格

每个模块格式如下：

```
module: ScenarioAgent
type: LangGraph node
inputs:
  - topic: str (来自 State)
outputs:
  - training_scenario: str
  - hazards_identified: list[str]
behavior: 根据 topic 生成贴近现场的训练情境描述
edge_cases:
  - topic 过于宽泛时，应聚焦到一个具体作业活动
  - topic 不在高危作业范围内时，拒绝生成
```

### 4.4 数据格式确认

`norm_chunks.jsonl` 和 `case_chunks.jsonl` 每行的 JSON schema（字段名 + 类型 + 中文说明）。

### 4.5 项目启动步骤

按目录结构给出项目初始化命令序列（`poetry init` / `pip install` / `.env` 配置等），确保 Claude Code 能直接执行。

---

## 5. 工程原则

- **可运行优先**：每个模块有明确的输入输出，可以独立测试，不依赖全局状态。
- **模块边界清晰**：prompt 放 `prompts/` 目录，Agent 只负责调用 LLM 和解析输出。
- **配置集中**：所有模型名、路径、超参都收拢到 `config.py`。
- **原型先跑通**：先用 2-3 条样本数据走完整流程，再补全评测和优化。
