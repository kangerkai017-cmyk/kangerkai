# 本地 Qwen3.5 服务启动与调用说明

本文档用于在本服务器上启动本地 Qwen3.5 模型服务，并在其他 agent 项目中通过 OpenAI 兼容接口调用该模型。

当前模型通过 `llama.cpp` 运行，模型文件为 GGUF Q5 量化版本。启动脚本会从 8 张 Tesla T4 中动态选择空闲 GPU，优先 3 卡，失败后自动降到 2 卡、1 卡。

## 1. 当前服务信息

```text
llama-server: /home/sicau_kek/vllm/llama.cpp/build/bin/llama-server
model: /home/sicau_kek/vllm/models/qwen35-9b-q5_k_m.gguf
port: 51000
api: http://localhost:51000/v1
model name: qwen35-9b-q5_k_m
```

如果调用方和模型服务在同一台服务器上，使用：

```text
http://localhost:51000/v1
```

如果从其他机器访问，使用：

```text
http://<服务器IP>:51000/v1
```

## 2. 启动 Qwen 服务

使用仓库中的启动脚本：

```bash
bash start_qwen_llama.sh
```

常用覆盖参数：

```bash
# 只从指定 GPU 中动态选择
QWEN_GPUS=3,6,7 bash start_qwen_llama.sh

# 简单问答更快，减少思考 token
QWEN_REASONING_BUDGET=128 bash start_qwen_llama.sh

# 复杂推理更强，允许更多思考 token
QWEN_REASONING_BUDGET=512 bash start_qwen_llama.sh

# 3 卡档尝试更大上下文
QWEN_CTX_3GPU=98304 bash start_qwen_llama.sh
```

保持该终端不要关闭。关闭终端或中断进程后，模型服务会停止。

默认档位：

```text
3gpu-balanced: ctx 65536, parallel 2, KV cache q8_0
2gpu-balanced: ctx 49152, parallel 1, KV cache q8_0
1gpu-safe:     ctx 32768, parallel 1, KV cache q8_0
1gpu-low-kv:   ctx 32768, parallel 1, KV cache q4_0
```

## 3. 在其他项目中调用

### Python OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:51000/v1",
    api_key="local",
)

stream = client.chat.completions.create(
    model="qwen35-9b-q5_k_m",
    messages=[
        {
            "role": "system",
            "content": "<替换为你的领域 agent system prompt>",
        },
        {
            "role": "user",
            "content": "<替换为用户问题>",
        },
    ],
    temperature=0.5,
    top_p=0.9,
    max_tokens=2048,
    stream=True,
)

for chunk in stream:
    delta = chunk.choices[0].delta.content
    if delta:
        print(delta, end="", flush=True)
print()
```

注意：上面的 `system` 内容只是占位符。实际 agent 项目中应替换为该项目自己的角色、任务边界、工具使用规则和输出格式要求。

### LangGraph / LangChain

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://localhost:51000/v1",
    api_key="local",
    model="qwen35-9b-q5_k_m",
    temperature=0.5,
    top_p=0.9,
    max_tokens=2048,
)

result = llm.invoke([
    ("system", "<替换为你的领域 agent system prompt>"),
    ("user", "<替换为用户问题>"),
])

print(result.content)
```

## 4. 连通性测试

连通性测试不设置领域身份，只确认接口是否可用：

```bash
curl http://localhost:51000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer local" \
  -d '{
    "model": "qwen35-9b-q5_k_m",
    "messages": [
      {"role": "user", "content": "请用一句话确认接口可用。"}
    ],
    "max_tokens": 512
  }'
```

如果返回正常文本，说明服务可用。

## 5. 常用检查命令

查看 GPU 占用：

```bash
nvidia-smi
```

查看 `51000` 端口是否被占用：

```bash
ss -ltnp 'sport = :51000'
```

查看 `llama-server` 进程：

```bash
pgrep -af '[l]lama-server'
```

## 6. 注意事项

- 不建议每个项目都启动一个 Qwen 服务；同服务器多个项目应复用同一个 `51000` 服务。
- 当前服务没有强制 API Key 校验，`api_key` 可以填 `local`。
- 该模型是 reasoning 蒸馏模型，默认 `QWEN_REASONING_BUDGET=256`；简单任务可降到 `0` 或 `128`，复杂推理可升到 `512`。
- 默认启用 `flash-attn`、unified KV、prompt cache、continuous batching、KV cache q8_0 和 metrics endpoint。
- 示例 prompt 仅用于说明调用格式，不代表最终 agent 的系统提示词。
- 领域 agent 应在自己的 LangGraph / LangChain 代码中定义专属 system prompt。
