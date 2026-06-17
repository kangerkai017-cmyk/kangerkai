#!/usr/bin/env python3
"""One-off OCR recovery for GB 6095-2021.

The body PDFs (01..06) ship with a broken CID font subset whose ToUnicode map
is missing, so pdfplumber/pymupdf only yield mojibake and the norm chunker
correctly drops them. The pages render fine visually, so we render each page
to an image and OCR it with tesseract (chi_sim), then inject the recovered
text into the chunker's extraction cache so a normal build_norm_chunks() run
flows GB-6095 through the SAME article-splitting path as every other standard.

This is a targeted, one-off action (not a general pipeline change). Re-running
is safe and idempotent.
"""

import io
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import fitz  # pymupdf
import pytesseract
from PIL import Image
from pytesseract import Output

from src.data_pipeline import norm_chunker as nc

GB6095_DIR = nc.PROJECT_ROOT / "rag_data" / "rag_data" / "GB 6095-2021"
RAW_OUT_DIR = nc.PROJECT_ROOT / "data" / "ocr" / "GB-6095-2021"

# Body chapters that are CID-garbled and need OCR. Appendix A (07) is already
# covered by its 表格说明.docx figure chunks, so it is intentionally excluded.
BODY_PDFS = [
    "01_范围与引用文件.pdf",
    "02_术语和定义.pdf",
    "03_分类与标记.pdf",
    "04_技术要求.pdf",
    "05_测试方法.pdf",
    "06_标识与信息.pdf",
]

OCR_DPI = 300

# Systematic glyph errors observed in the chi_sim OCR of this standard. tesseract
# consistently confuses a handful of CJK glyphs here; fixing them by substitution
# is safe because these wrong forms do not otherwise occur in the source.
GLYPH_FIXES = {
    "安全市": "安全带",
    "安全沸": "安全带",
    "安全珊": "安全带",
    "安全强": "安全绳",
    "安全靶挂": "安全悬挂",
    "翟落": "坠落",
    "蔡落": "坠落",
    "荃落": "坠落",
    "鞋落": "坠落",
    "险落": "坠落",
    "验落": "坠落",
    "答悬挂": "坠落悬挂",
    "巧挂": "悬挂",
    "晤吊": "悬吊",
    "嫩吊": "悬吊",
    "最届": "悬吊",
    "连接需": "连接器",
    "锁需": "锁器",
    "自控需": "自控器",
    "缓冲吉": "缓冲器",
    "缓冲天": "缓冲器",
    "冲吉": "缓冲器",
    "组降装置": "缓降装置",
    "炊融": "熔融",
    "系傍": "系带",
    "系闪": "系带",
    "中国定": "中固定",
    "构造服": "构造物",
    "防项电": "防静电",
    "外生殖上需": "外生殖器",
    "只部": "颈部",
    "轩杆": "围杆",
    "于杆作业": "围杆作业",
    "从落悬挂": "坠落悬挂",
    "给落至地面": "坠落至地面",
    "女亲全带": "安全带",
    "民符合": "应符合",
    "包右": "包覆",
    "烧汶焦": "烧焦",
}


def reorder_page(img) -> str:
    """OCR a page image and rebuild reading order from word boxes.

    Default image_to_string segments the page into blocks and emits block by
    block, which scrambles multi-column / split-line layouts in this standard.
    We instead take per-word boxes, regroup all words into visual lines by their
    y-coordinate across the full page width, then sort each line left-to-right.
    This recovers the true reading order for the two-column performance pages.
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


def apply_glyph_fixes(text: str) -> str:
    for wrong, right in GLYPH_FIXES.items():
        text = text.replace(wrong, right)
    return text


_ARTICLE = r"(?:\d+\.)+\d+"


def normalize_for_chunking(text: str) -> str:
    """Reshape OCR lines so norm_chunker._split_articles can detect articles.

    That splitter expects each article as '<number><space><first line>' on one
    line. OCR reorder produces two deviations we repair here:
      1. a bare article-number line ('3.1\\n安全带...') -> join onto next line;
      2. number glued to text ('5.1.1安全带...') -> insert a single space.
    We also pull a line that begins with closing punctuation back onto the
    previous line, since the y-line grouping sometimes drops trailing marks.
    """
    lines = [ln.strip() for ln in text.splitlines()]
    merged: list[str] = []
    for ln in lines:
        if not ln:
            continue
        # closing punctuation orphaned on its own line -> attach to previous
        if merged and ln[0] in "。；：、，)]”》":
            merged[-1] += ln
            continue
        # bare article-number line -> hold and prepend to the next content line
        if re.fullmatch(rf"{_ARTICLE}", ln):
            merged.append(ln + " ")  # marker: needs join with next line
            continue
        if merged and merged[-1].endswith(" "):
            merged[-1] = merged[-1][:-1] + " " + ln
            continue
        merged.append(ln)
    out = "\n".join(m.rstrip(" ") for m in merged)
    # OCR renders a two-digit final level ('3.16') with the last digit split off
    # by a space ('3.1 6'); rejoin so the article id stays intact. Only fires
    # when a number is followed by ' <single-digit> ' (clause text never is).
    for _ in range(2):
        out = re.sub(rf"(?m)^({_ARTICLE}) (\d) ", r"\1\2 ", out)
    # number glued directly to body text at line start -> insert one space.
    # The lookahead must reject a following digit/dot so it cannot backtrack
    # into a just-rejoined number (e.g. '3.10 主' -> matching '3.1' before '0').
    out = re.sub(rf"(?m)^({_ARTICLE})(?=[^\d\s.])", r"\1 ", out)
    return out


def ocr_pdf(path) -> str:
    pages_text: list[str] = []
    with fitz.open(path) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=OCR_DPI)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            pages_text.append(reorder_page(img))
    return normalize_for_chunking(apply_glyph_fixes("\n".join(pages_text)))


def inject_into_extract_cache(path, text: str) -> None:
    """Write OCR text into the norm chunker's extraction cache so a normal
    build_norm_chunks() run transparently consumes it for this PDF, flowing
    GB-6095 through the same article-splitting/tagging/chunk_id path as every
    other standard. Cache key must match norm_chunker._extract_text exactly."""
    nc.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    stat = path.stat()
    cache_key = nc._sha256(
        f"{path.resolve()}|{stat.st_mtime_ns}|{stat.st_size}|{nc.PIPELINE_VERSION}"
    )
    (nc.CACHE_DIR / f"{cache_key}.txt").write_text(text, encoding="utf-8")


def main() -> int:
    RAW_OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name in BODY_PDFS:
        path = GB6095_DIR / name
        if not path.exists():
            print(f"MISSING: {path}")
            continue
        text = ocr_pdf(path)
        out = RAW_OUT_DIR / (path.stem + ".txt")
        out.write_text(text, encoding="utf-8")
        inject_into_extract_cache(path, text)
        cjk = sum(1 for ch in text if "一" <= ch <= "鿿")
        print(f"{name}: chars={len(text)} cjk={cjk} -> {out.relative_to(nc.PROJECT_ROOT)} (cache injected)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
