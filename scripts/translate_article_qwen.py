#!/usr/bin/env python3
"""Translate the local ConSTRAG article with a local OpenAI-compatible Qwen server.

The script extracts text before the References section, translates block-by-block
in small batches, and writes a bilingual Markdown reader plus a JSON source map.
It keeps a translation cache so reruns can resume after interruption.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

import fitz
import requests


DEFAULT_MODEL = "Qwen3.5-9B-Q5_K_M"
DEFAULT_BASE_URL = "http://localhost:51000/v1"


SECTION_RE = re.compile(r"^(?:\d+(?:\.\d+)*\.?\s+.+|Abstract|Keywords|CRediT authorship contribution statement|Declaration of Competing Interest|Acknowledgments|Data availability)$")


def clean_text(text: str) -> str:
    text = text.replace("\u00ad", "")
    text = text.replace("−", "-")
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
    text = re.sub(r"[ \t]*\n[ \t]*", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def should_skip_block(text: str) -> bool:
    if not text:
        return True
    if re.fullmatch(r"\d+", text):
        return True
    if text.startswith("Q. Chen et al.") or text.startswith("Computers in Industry"):
        return True
    if text in {"Contents lists available at ScienceDirect", "Computers in Industry"}:
        return True
    if text.startswith("journal homepage:"):
        return True
    return False


def extract_blocks(pdf_path: Path) -> list[dict[str, Any]]:
    doc = fitz.open(pdf_path)
    blocks: list[dict[str, Any]] = []
    block_index = 1
    stop = False
    for page_index, page in enumerate(doc, start=1):
        page_blocks = page.get_text("blocks", sort=True)
        for raw in page_blocks:
            text = clean_text(raw[4])
            if not text:
                continue
            ref_pos = re.search(r"\bReferences\b", text)
            if ref_pos:
                text = text[: ref_pos.start()].strip()
                stop = True
            if should_skip_block(text):
                continue
            block_type = "heading" if SECTION_RE.match(text) and len(text) < 120 else "text"
            if text.startswith("Table "):
                block_type = "table_or_caption"
            if text.startswith("Fig. ") or text.startswith("Figure "):
                block_type = "figure_caption"
            block_id = f"S{block_index:03d}"
            blocks.append(
                {
                    "id": block_id,
                    "page": page_index,
                    "type": block_type,
                    "original": text,
                    "translation": "",
                    "confidence": "text-layer",
                }
            )
            block_index += 1
        if stop:
            break
    return blocks


def strip_thinking(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    return text.strip()


def extract_json_array(text: str) -> list[dict[str, str]]:
    text = strip_thinking(text)
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.S)
    if fenced:
        text = fenced.group(1).strip()
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("translation response is not a JSON array")
    return data


def call_qwen(base_url: str, model: str, messages: list[dict[str, str]], max_tokens: int = 4096) -> str:
    resp = requests.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={"Content-Type": "application/json"},
        json={
            "model": model,
            "messages": messages,
            "temperature": 0.1,
            "top_p": 0.8,
            "max_tokens": max_tokens,
        },
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def translate_batch(base_url: str, model: str, batch: list[dict[str, Any]]) -> dict[str, str]:
    payload = [{"id": b["id"], "text": b["original"]} for b in batch]
    messages = [
        {
            "role": "system",
            "content": (
                "You are a careful academic translator. Translate English research-paper text into faithful, fluent Chinese. "
                "Preserve citations, numbers, equations, model names, acronyms, table labels, figure labels, and technical terms. "
                "Do not summarize. Do not omit details. Return only valid JSON."
            ),
        },
        {
            "role": "user",
            "content": (
                "Translate each item. Return a JSON array with objects exactly in this form: "
                "[{\"id\":\"S001\",\"zh\":\"中文译文\"}].\n\n"
                + json.dumps(payload, ensure_ascii=False)
            ),
        },
    ]
    raw = call_qwen(base_url, model, messages)
    parsed = extract_json_array(raw)
    result: dict[str, str] = {}
    for item in parsed:
        if isinstance(item, dict) and item.get("id") and item.get("zh"):
            result[str(item["id"])] = str(item["zh"]).strip()
    missing = [b["id"] for b in batch if b["id"] not in result]
    if missing:
        raise ValueError(f"missing translations: {missing}")
    return result


def translate_single(base_url: str, model: str, block: dict[str, Any]) -> str:
    messages = [
        {
            "role": "system",
            "content": "Translate English academic paper text into faithful, fluent Chinese. Preserve citations, numbers, terms, and labels. Return only the translation.",
        },
        {"role": "user", "content": block["original"]},
    ]
    return strip_thinking(call_qwen(base_url, model, messages, max_tokens=2048))


def load_cache(cache_path: Path) -> dict[str, str]:
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    return {}


def save_cache(cache_path: Path, cache: dict[str, str]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def translate_blocks(blocks: list[dict[str, Any]], out_dir: Path, base_url: str, model: str, batch_size: int) -> None:
    cache_path = out_dir / "translation_cache.json"
    cache = load_cache(cache_path)
    pending = [b for b in blocks if b["id"] not in cache]
    print(f"blocks={len(blocks)} cached={len(cache)} pending={len(pending)}", flush=True)
    for start in range(0, len(pending), batch_size):
        batch = pending[start : start + batch_size]
        ids = ", ".join(b["id"] for b in batch)
        print(f"translating {ids}", flush=True)
        try:
            translations = translate_batch(base_url, model, batch)
        except Exception as exc:
            print(f"batch failed ({exc}); falling back to single-block translation", flush=True)
            translations = {}
            for block in batch:
                translations[block["id"]] = translate_single(base_url, model, block)
                time.sleep(0.1)
        cache.update(translations)
        save_cache(cache_path, cache)
    for block in blocks:
        block["translation"] = cache.get(block["id"], "")


def write_outputs(pdf_path: Path, blocks: list[dict[str, Any]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    metadata = doc.metadata
    paper_md = out_dir / "paper_translation.md"
    source_map = out_dir / "source_map.json"
    notes = out_dir / "translation_notes.md"

    lines: list[str] = []
    lines.append("# Personalized safety training for construction workers: 中文翻译读本")
    lines.append("")
    lines.append(f"- Source PDF: `{pdf_path.name}`")
    lines.append(f"- Title: {metadata.get('title', '')}")
    lines.append(f"- Authors: {metadata.get('author', '')}")
    lines.append(f"- Journal: {metadata.get('subject', '')}")
    lines.append("- Scope: translated through Data availability; References section excluded as requested.")
    lines.append("")
    lines.append("## Page Index")
    pages = sorted({b["page"] for b in blocks})
    lines.append(", ".join(f"[p.{p}](#page-{p})" for p in pages))
    lines.append("")
    current_page = None
    for block in blocks:
        if current_page != block["page"]:
            current_page = block["page"]
            lines.append(f'<a id="page-{current_page}"></a>')
            lines.append(f"## Page {current_page}")
            lines.append("")
        lines.append(f'<a id="{block["id"]}"></a>')
        lines.append(f"**Source:** p.{block['page']} {block['id']} ({block['type']})")
        lines.append("")
        lines.append(f"**Original:** {block['original']}")
        lines.append("")
        lines.append(f"**中文:** {block['translation']}")
        lines.append("")

    terms = [
        ("personalized safety training", "个性化安全培训"),
        ("large language model-based agent", "基于大语言模型的智能体"),
        ("knowledge graph reasoning", "知识图谱推理"),
        ("retrieval-augmented generation", "检索增强生成"),
        ("worker profile", "工人画像 / 工人概况"),
        ("construction regulation knowledge graph (CRKG)", "施工规范知识图谱（CRKG）"),
        ("construction accident knowledge graph (CAKG)", "施工事故知识图谱（CAKG）"),
        ("domain keywords (DKs)", "领域关键词（DKs）"),
        ("auxiliary keywords (AKs)", "辅助关键词（AKs）"),
    ]
    lines.append("## Terminology")
    lines.append("")
    lines.append("| English | 中文 |")
    lines.append("| --- | --- |")
    for en, zh in terms:
        lines.append(f"| {en} | {zh} |")
    lines.append("")

    paper_md.write_text("\n".join(lines), encoding="utf-8")
    source_map.write_text(json.dumps(blocks, ensure_ascii=False, indent=2), encoding="utf-8")
    notes.write_text(
        "\n".join(
            [
                "# Translation Notes",
                "",
                "- 参考文献部分已按用户要求从 `References` 起剔除。",
                "- PDF 具有可提取文本层；本次使用 PyMuPDF 提取正文块。",
                "- 输出采用段落级中英文对照，包含页码和稳定块 ID。",
                "- 未重新裁剪图表图片；图题、表题和表格文本若在文本层中可提取，则已作为文本块翻译。",
                "- 本地翻译模型：Qwen3.5-9B-Q5_K_M via OpenAI-compatible localhost endpoint。",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--batch-size", type=int, default=4)
    args = parser.parse_args()

    blocks = extract_blocks(args.pdf)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "extracted_blocks.json").write_text(json.dumps(blocks, ensure_ascii=False, indent=2), encoding="utf-8")
    translate_blocks(blocks, args.out_dir, args.base_url, args.model, args.batch_size)
    write_outputs(args.pdf, blocks, args.out_dir)
    print(f"wrote {args.out_dir / 'paper_translation.md'}", flush=True)


if __name__ == "__main__":
    main()
