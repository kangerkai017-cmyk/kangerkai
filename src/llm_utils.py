import json
import time
from typing import Any, Optional
from pydantic import BaseModel
from openai import OpenAI, OpenAIError
import httpx
from src.config import (
    LLM_DISABLE_THINKING,
    LLM_JSON_SCHEMA_MODELS,
    LLM_MAX_TOKENS,
    LLM_MAX_TOKENS_BY_MODEL,
    LLM_MODEL,
    LLM_STRUCTURED_MODE,
    LLM_TOP_P,
    LLM_USE_JSON_MODE,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
)
from src import metrics
from src.trace_utils import estimate_tokens, trace_log


class LLMTruncatedOutputError(ValueError):
    def __init__(self, response_model: str, finish_reason: str):
        super().__init__(
            f"LLM output truncated for {response_model}; finish_reason={finish_reason}"
        )
        self.response_model = response_model
        self.finish_reason = finish_reason


def get_client() -> OpenAI:
    # Keep requests independent of shell proxy settings; localhost backends and
    # remote OpenAI-compatible APIs both work through the explicit base_url.
    return OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
        http_client=httpx.Client(trust_env=False),
    )


def _json_schema_response_format(response_model: type[BaseModel]) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": response_model.__name__,
            "schema": response_model.model_json_schema(),
        },
    }


def _response_format_for(
    json_mode: bool,
    response_model: Optional[type[BaseModel]] = None,
) -> Optional[dict[str, Any]]:
    if not json_mode:
        return None

    mode = LLM_STRUCTURED_MODE
    if mode == "json_schema" and response_model is not None:
        if response_model.__name__ in LLM_JSON_SCHEMA_MODELS:
            return _json_schema_response_format(response_model)
        return None

    if mode == "json_object":
        return {"type": "json_object"}

    # Backward compatibility for the previous boolean switch.
    if mode == "none" and LLM_USE_JSON_MODE:
        return {"type": "json_object"}

    return None


def call_llm(
    prompt: str,
    system_prompt: str = "",
    temperature: float = 0.3,
    json_mode: bool = False,
    response_model: Optional[type[BaseModel]] = None,
) -> str:
    client = get_client()
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    model_name = response_model.__name__ if response_model is not None else "None"
    max_tokens = (
        LLM_MAX_TOKENS_BY_MODEL.get(response_model.__name__, LLM_MAX_TOKENS)
        if response_model
        else LLM_MAX_TOKENS
    )

    kwargs = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "top_p": LLM_TOP_P,
        "max_tokens": max_tokens,
    }
    if LLM_DISABLE_THINKING:
        if "deepseek.com" in OPENAI_BASE_URL:
            kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
        else:
            # vLLM / jinja-enabled local backends may honor this Qwen flag.
            kwargs["extra_body"] = {
                "chat_template_kwargs": {"enable_thinking": False},
            }
    response_format = _response_format_for(json_mode, response_model)
    if response_format is not None:
        kwargs["response_format"] = response_format

    trace_log(
        "AGENT-LLM",
        (
            f"START schema={model_name} json_mode={json_mode} "
            f"prompt_chars={len(prompt)} prompt_tokens_est={estimate_tokens(prompt)} "
            f"system_chars={len(system_prompt)} max_tokens={max_tokens}"
        ),
    )
    metrics.incr("llm_calls")
    t0 = time.perf_counter()
    response = client.chat.completions.create(**kwargs)
    elapsed = time.perf_counter() - t0
    choice = response.choices[0]
    finish_reason = choice.finish_reason or ""
    usage = getattr(response, "usage", None)
    prompt_tokens = getattr(usage, "prompt_tokens", None) if usage else None
    completion_tokens = getattr(usage, "completion_tokens", None) if usage else None
    content = choice.message.content or ""
    trace_log(
        "AGENT-LLM",
        (
            f"END schema={model_name} seconds={elapsed:.3f} "
            f"finish_reason={finish_reason} prompt_tokens={prompt_tokens} "
            f"completion_tokens={completion_tokens} response_chars={len(content)}"
        ),
    )
    if finish_reason == "length" and not content.strip().endswith("}"):
        raise LLMTruncatedOutputError(model_name, finish_reason)
    return content


def _call_llm_with_fallback(
    prompt: str,
    system_prompt: str,
    temperature: float,
    response_model: Optional[type[BaseModel]],
) -> str:
    try:
        return call_llm(
            prompt,
            system_prompt,
            temperature,
            json_mode=True,
            response_model=response_model,
        )
    except OpenAIError as exc:
        status_code = getattr(exc, "status_code", None)
        if status_code in {429, 500, 502, 503, 504}:
            trace_log(
                "AGENT-LLM",
                (
                    f"ERROR schema={response_model.__name__ if response_model else 'None'} "
                    f"status_code={status_code} retry_plain_json=false error={exc}"
                ),
            )
            raise
        if (
            LLM_STRUCTURED_MODE == "json_schema"
            and response_model is not None
            and response_model.__name__ in LLM_JSON_SCHEMA_MODELS
        ):
            print(
                f"[llm_utils] json_schema request failed for "
                f"{response_model.__name__}; falling back to plain JSON prompt. "
                f"Error: {exc}"
            )
            trace_log(
                "AGENT-LLM",
                f"FALLBACK schema={response_model.__name__} reason=json_schema_error",
            )
            return call_llm(
                prompt,
                system_prompt,
                temperature,
                json_mode=False,
                response_model=None,
            )
        raise


def _balanced_json_slice(text: str) -> str:
    """Extract the first balanced JSON object from an LLM response."""
    start = text.find("{")
    if start < 0:
        raise ValueError("No JSON object start found")

    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(text)):
        char = text[idx]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]

    raise ValueError("No balanced JSON object found")


def _sanitize_json_text(text: str) -> str:
    """Fix common small-model JSON mistakes: None→null, True→true, False→false."""
    import re
    text = re.sub(r'\bNone\b', 'null', text)
    text = re.sub(r'\bTrue\b', 'true', text)
    text = re.sub(r'\bFalse\b', 'false', text)
    return text


def _try_parse(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(_sanitize_json_text(text))
    except json.JSONDecodeError:
        pass
    raise ValueError("not valid JSON")


def _strip_think_block(text: str) -> str:
    """Drop a leading <think>...</think> block if present. With --reasoning off
    and the chatml template this should be a no-op, but kept as a safety net for
    any path where the server-level suppression is absent (e.g. profile change
    without QWEN_CHAT_TEMPLATE set, or a future backend switch)."""
    if "<think>" not in text:
        return text
    end = text.rfind("</think>")
    if end != -1:
        return text[end + len("</think>") :].strip()
    return text


def _extract_json(response: str) -> dict:
    response = _strip_think_block(response.strip())

    # 1. Direct parse
    try:
        return _try_parse(response)
    except ValueError:
        pass

    # 2. Extract from ```json block
    if "```json" in response:
        start = response.index("```json") + 7
        try:
            end = response.index("```", start)
            return _try_parse(response[start:end])
        except (ValueError, json.JSONDecodeError):
            pass

    # 3. Extract from ``` block
    if "```" in response:
        start = response.index("```") + 3
        try:
            end = response.index("```", start)
            return _try_parse(response[start:end])
        except (ValueError, json.JSONDecodeError):
            pass

    # 4. Balanced JSON slice
    try:
        sliced = _balanced_json_slice(response)
        return _try_parse(sliced)
    except (ValueError, json.JSONDecodeError):
        pass

    raise ValueError(f"Cannot parse JSON from response: {response[:500]}")


def _fill_none_values(obj):
    """Recursively replace None with '' for dict values to satisfy Pydantic str fields."""
    if isinstance(obj, dict):
        return {k: _fill_none_values(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_fill_none_values(v) for v in obj]
    if obj is None:
        return ""
    return obj


def call_llm_json(
    prompt: str,
    system_prompt: str = "",
    response_model: Optional[type[BaseModel]] = None,
    temperature: float = 0.3,
) -> BaseModel | dict:
    """Call LLM with JSON mode, parse and optionally validate with Pydantic.

    Returns a Pydantic model instance if response_model is provided,
    otherwise returns a raw dict. Retries once with a stronger JSON instruction
    if the first attempt fails to produce valid JSON.
    """
    instructions = [
        "\n\n请严格只输出一个合法 JSON 对象，不要输出 Markdown 代码块、解释文字或额外前后缀。",
        "\n\n【最后一次机会】你刚才没有输出合法的 JSON。现在请**只**输出一个 JSON 对象，从 { 开始，到 } 结束。不要输出任何其他内容，不要解释，不要道歉。",
    ]

    last_error = None
    for attempt in range(2):
        try:
            response = _call_llm_with_fallback(
                prompt + instructions[attempt],
                system_prompt,
                temperature,
                response_model,
            )
        except LLMTruncatedOutputError:
            raise
        except OpenAIError as e:
            last_error = e
            raise ValueError(f"LLM request failed: {e}") from e
        try:
            data = _extract_json(response)
            data = _fill_none_values(data)
            if response_model is not None:
                return response_model.model_validate(data)
            return data
        except (ValueError, Exception) as e:
            last_error = e
            if attempt == 0:
                trace_log(
                    "AGENT-LLM",
                    (
                        f"RETRY_JSON schema={response_model.__name__ if response_model else 'dict'} "
                        f"attempt=2 reason={type(e).__name__}: {str(e)[:180]}"
                    ),
                )
                continue

    raise ValueError(
        f"LLM failed to produce valid JSON after 2 attempts. "
        f"Last error: {last_error}"
    )
