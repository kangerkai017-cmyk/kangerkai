#!/usr/bin/env python3
"""Layout-aware OCR for image-based / broken-text-layer norm PDFs.

Some standards ship as image-only PDFs (scanned, or a watermark-only text
layer), so pdfplumber/pymupdf return no usable body text and the norm chunker
either drops them or emits one garbled blob. This tool renders each page, OCRs
it with tesseract (chi_sim), and -- crucially -- rebuilds reading order from
per-word boxes so multi-column / split-line layouts are not scrambled the way
plain image_to_string scrambles them. The recovered text is written into the
norm chunker's extraction cache so a normal build_norm_chunks() run flows the
standard through the SAME article-splitting / tagging / chunk_id path as every
other standard.

This is the shared engine; per-standard entrypoints (e.g. a thin call below or
in a sibling script) supply the source PDFs and an optional glyph-fix map.

Usage:
    python scripts/ocr_image_norm.py "<standard-dir-or-pdf>" [--fixes fixes.json]
"""

import argparse
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import fitz  # pymupdf
import pytesseract
from PIL import Image
from pytesseract import Output

from src.data_pipeline import norm_chunker as nc

OCR_DPI = 300
RAW_OUT_ROOT = nc.PROJECT_ROOT / "data" / "ocr"
_ARTICLE = r"(?:\d+\.)+\d+"


def reorder_page(img) -> str:
    """OCR a page image and rebuild reading order from word boxes.

    Default image_to_string segments the page into blocks and emits block by
    block, which scrambles multi-column / split-line layouts. We take per-word
    boxes, regroup all words into visual lines by y-coordinate across the full
    page width, then sort each line left-to-right -- recovering true reading
    order regardless of column count.
    """
    data = pytesseract.image_to_data(img, lang="chi_sim", output_type=Output.DICT)
    words = []
    for i in range(len(data["text"])):
        t = data["text"][i].strip()
        if not t:
            continue
        words.append((data["left"][i], data["top"][i], data["height"][i], t))
    if not words:
        return ""
    words.sort(key=lambda r: (r[1], r[0]))
    lines: list[list[tuple[int, str]]] = []
    cur: list[tuple[int, str]] = []
    cy = ch = None
    for x, y, h, t in words:
        if cy is None or abs(y - cy) <= max(h, ch or h) * 0.6:
            cur.append((x, t))
            cy = y if cy is None else (cy * len(cur) + y) // (len(cur) + 1)
            ch = h
        else:
            lines.append(cur)
            cur = [(x, t)]
            cy, ch = y, h
    if cur:
        lines.append(cur)
    out = []
    for ln in lines:
        ln.sort(key=lambda r: r[0])
        out.append("".join(t for _, t in ln))
    return "\n".join(out)


def apply_glyph_fixes(text: str, fixes: dict[str, str]) -> str:
    for wrong, right in fixes.items():
        text = text.replace(wrong, right)
    return text


def normalize_for_chunking(text: str) -> str:
    """Reshape OCR lines so norm_chunker._split_articles can detect articles.

    The splitter expects each article as '<number><space><first line>' on one
    line. OCR reorder produces deviations we repair: a bare article-number line
    joined onto the next line; a number glued to text getting a space; a
    two-digit final level split by a space ('3.1 6' -> '3.16'); and a line that
    begins with closing punctuation pulled back onto the previous line.
    """
    lines = [ln.strip() for ln in text.splitlines()]
    merged: list[str] = []
    for ln in lines:
        if not ln:
            continue
        if merged and ln[0] in "。；：、，)]”》":
            merged[-1] += ln
            continue
        if re.fullmatch(rf"{_ARTICLE}", ln):
            merged.append(ln + " ")
            continue
        if merged and merged[-1].endswith(" "):
            merged[-1] = merged[-1][:-1] + " " + ln
            continue
        merged.append(ln)
    out = "\n".join(m.rstrip(" ") for m in merged)
    for _ in range(2):
        out = re.sub(rf"(?m)^({_ARTICLE}) (\d) ", r"\1\2 ", out)
    # number glued to body text; lookahead rejects digit/dot so it cannot
    # backtrack into a just-rejoined number (e.g. '3.10 主' -> '3.1' before '0').
    out = re.sub(rf"(?m)^({_ARTICLE})(?=[^\d\s.])", r"\1 ", out)
    return out


def _is_front_matter_page(text: str) -> bool:
    """Skip table-of-contents / English-contents / cover pages so their
    'X.Y title .... pageno' lines are not mis-parsed as articles. A TOC page is
    full of dot-leader runs (OCR'd as 'oooo'/'....'); an English contents page
    is ASCII-dominated. Body pages are coherent Chinese with neither trait."""
    if not text.strip():
        return True
    leaders = len(re.findall(r"[oe.·…]{4,}", text))
    if leaders >= 3:
        return True
    letters = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    cjk = sum(1 for ch in text if "一" <= ch <= "鿿")
    if letters > cjk:  # English-dominated page
        return True
    return False


def ocr_pdf(path, fixes: dict[str, str]) -> str:
    pages_text: list[str] = []
    with fitz.open(path) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=OCR_DPI)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text = reorder_page(img)
            if _is_front_matter_page(text):
                continue
            pages_text.append(text)
    return normalize_for_chunking(apply_glyph_fixes("\n".join(pages_text), fixes))


def inject_into_extract_cache(path, text: str) -> None:
    """Write OCR text into the norm chunker's extraction cache. Cache key must
    match norm_chunker._extract_text exactly so build_norm_chunks() consumes it."""
    nc.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    stat = path.stat()
    cache_key = nc._sha256(
        f"{path.resolve()}|{stat.st_mtime_ns}|{stat.st_size}|{nc.PIPELINE_VERSION}"
    )
    (nc.CACHE_DIR / f"{cache_key}.txt").write_text(text, encoding="utf-8")


def iter_pdfs(target):
    if target.is_file() and target.suffix.lower() == ".pdf":
        return [target]
    return sorted(p for p in target.rglob("*.pdf"))


def process(target, fixes: dict[str, str]) -> int:
    pdfs = iter_pdfs(target)
    if not pdfs:
        print(f"No PDF found under {target}")
        return 1
    out_dir = RAW_OUT_ROOT / target.name
    out_dir.mkdir(parents=True, exist_ok=True)
    for path in pdfs:
        text = ocr_pdf(path, fixes)
        (out_dir / (path.stem + ".txt")).write_text(text, encoding="utf-8")
        inject_into_extract_cache(path, text)
        cjk = sum(1 for ch in text if "一" <= ch <= "鿿")
        print(f"{path.name}: chars={len(text)} cjk={cjk} (cache injected)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="standard directory or single PDF path")
    ap.add_argument("--fixes", help="optional JSON file: {wrong: right} glyph map")
    args = ap.parse_args()
    from pathlib import Path

    fixes: dict[str, str] = {}
    if args.fixes:
        fixes = json.loads(Path(args.fixes).read_text(encoding="utf-8"))
    return process(Path(args.target), fixes)


if __name__ == "__main__":
    raise SystemExit(main())
