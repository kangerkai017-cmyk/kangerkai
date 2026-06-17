# SafeAgent - 建筑施工安全智能培训与问答系统

基于大语言模型（LLM）和多智能体架构的施工安全知识检索与培训系统。通过双证据知识库（法规规范 + 事故案例）驱动，为建筑工人提供个性化安全培训内容生成和智能问答服务。

## 系统架构

```
用户输入
   │
   ▼
┌──────────────┐
│  意图分类器    │ ─── 识别用户意图：培训 or 问答
└──────┬───────┘
       │
   ┌───┴───┐
   ▼       ▼
培训流水线  问答流水线
   │       │
   ▼       ▼
 三阶段审议  多轮检索+生成
  ┌─┼─┐     ┌─┐
  取 撰 仲   检 生
  证 写 裁   索 成
```

### 核心模块

- **意图分类** — 自动判断用户需求，路由到培训或问答流水线
- **培训流水线（三阶段审议）** — 取证子图 → 撰写子图 → 仲裁子图，迭代优化培训内容
- **问答流水线** — 多轮检索增强生成，精准回答安全相关问题
- **双证据知识库** — 法规规范（Norm）+ 事故案例（Case）联合检索
- **案例-规范链接器** — 从事故案例自动关联相关法规条款
- **一致性检查** — 验证生成内容与检索证据的 grounding 一致性
- **仲裁机制** — 当一致性检查不通过时，触发定向重检索并重新生成

## 项目结构

```
├── app.py                          # Streamlit Web 界面
├── src/
│   ├── agents/                     # 多智能体核心
│   │   ├── unified_graph.py        # 统一图（意图路由）
│   │   ├── graph.py                # 培训流水线图
│   │   ├── qa_graph.py             # 问答流水线图
│   │   ├── intent_classifier.py    # 意图分类
│   │   ├── evidence_fusion.py      # 证据融合
│   │   ├── consistency_checker.py  # 一致性检查
│   │   ├── arbitration.py          # 仲裁节点
│   │   ├── training_agent.py      # 培训内容生成
│   │   ├── qa_agent.py             # 问答生成
│   │   ├── query_rewriter.py       # 查询改写
│   │   ├── risk_planner.py         # 风险规划
│   │   └── scenario_agent.py       # 场景分析
│   ├── retrieval/                  # 检索引擎
│   │   ├── es_store.py             # Elasticsearch 后端（BM25 + 向量 + RRF 融合）
│   │   ├── vector_store.py         # ChromaDB 向量检索
│   │   ├── norm_retriever.py       # 规范检索
│   │   └── case_retriever.py       # 案例检索
│   ├── baselines/                  # 基线方法（B1-B5）
│   ├── data_pipeline/             # 数据处理管道
│   ├── evaluation/                # 评估模块
│   ├── prompts/                    # Prompt 模板
│   ├── schema/                     # 数据模型定义
│   ├── config.py                   # 全局配置
│   └── metrics.py                  # 评估指标
├── scripts/                        # 工具脚本
│   ├── run_agent.py                # 命令行交互入口
│   ├── run_benchmark.py            # 基准测试
│   ├── run_ablation.py             # 消融实验
│   ├── build_norm_chunks.py        # 构建规范索引
│   ├── build_case_chunks.py        # 构建案例索引
│   └── ...
├── data/                           # 数据目录
│   ├── ocr/                        # OCR 处理后的法规文本
│   ├── chunks/                     # 分块后的 JSONL 数据
│   ├── eval/                       # 评估结果
│   └── taxonomy/tags.yaml          # 场景/危险源标签词表
├── rag_data/                       # 原始法规 PDF 及处理数据
├── tests/                          # 单元测试
├── docker-compose.elasticsearch.yml # Elasticsearch 部署配置
├── requirements.txt
└── .env.example                    # 环境变量模板
```

## 快速开始

### 1. 环境准备

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 API Key 和模型配置
```

关键配置项：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | LLM API 密钥 | - |
| `OPENAI_BASE_URL` | API 地址 | `https://api.deepseek.com` |
| `LLM_MODEL` | 模型名称 | `deepseek-v4-pro` |
| `RETRIEVAL_BACKEND` | 检索后端 | `elasticsearch` |
| `ES_URL` | Elasticsearch 地址 | `http://localhost:9200` |

### 3. 启动 Elasticsearch

```bash
docker-compose -f docker-compose.elasticsearch.yml up -d
```

### 4. 构建索引

```bash
# 构建规范索引
python scripts/build_norm_chunks.py
python scripts/build_norm_index.py

# 构建案例索引
python scripts/build_case_chunks.py
python scripts/build_case_index.py
```

### 5. 运行

**Web 界面：**
```bash
streamlit run app.py
```

**命令行交互：**
```bash
python scripts/run_agent.py
```

## 基线方法

系统内置 5 种基线方法用于对比评估：

| 编号 | 方法 | 说明 |
|------|------|------|
| B1 | LLM-Only | 纯 LLM 生成，无检索 |
| B2 | Norm-Only-RAG | 仅规范检索增强 |
| B3 | Naive-Dual-RAG | 简单双源检索，无融合 |
| B4 | Optimized-RAG | 优化检索，无审议机制 |
| B5 | Proposed | 完整提出方法（三阶段审议 + 双证据融合） |

运行基准测试：
```bash
python scripts/run_benchmark.py
```

运行消融实验：
```bash
python scripts/run_ablation.py
```

## 检索策略

- **BM25 文本检索** — 基于关键词的稀疏检索
- **向量语义检索** — 基于 BAAI/bge-large-zh-v1.5 的稠密检索
- **标签路由检索** — 基于场景/危险源标签的精准过滤
- **RRF 融合** — Reciprocal Rank Fusion 多路结果融合
- **Cross-Encoder 重排序** — 可选的精排阶段

## 技术栈

- **框架**：LangGraph + LangChain
- **LLM**：OpenAI 兼容 API（DeepSeek / Qwen 等）
- **检索**：Elasticsearch 8.x + ChromaDB
- **嵌入**：sentence-transformers (BAAI/bge-large-zh-v1.5)
- **前端**：Streamlit
- **数据验证**：Pydantic v2

## License

MIT
