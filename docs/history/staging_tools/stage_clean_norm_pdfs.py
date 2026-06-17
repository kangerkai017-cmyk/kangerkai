#!/usr/bin/env python3
"""Create high-granularity staging sources from whole-standard PDFs.

The output intentionally lives under rag_data/staging_cleaned so it is not read
by the formal norm pipeline unless an explicit source root is supplied.
"""

from __future__ import annotations

import io
import os
import re
import shutil
import sys
import zipfile
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import fitz
import pytesseract
from PIL import Image

from src.data_pipeline import norm_chunker as nc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_ROOT / "rag_data" / "original_pdfs"
OUT_ROOT = PROJECT_ROOT / "rag_data" / "staging_cleaned"
TESSERACT_CMD = PROJECT_ROOT.parent / "miniconda3" / "envs" / "myenv" / "bin" / "tesseract"
OCR_DPI = 170
OCR_WORKERS = 4


@dataclass(frozen=True)
class Chapter:
    no: str
    title: str
    start_page: int
    end_page: int


@dataclass(frozen=True)
class TableGroup:
    name: str
    pages: tuple[int, ...]
    notes: tuple[str, ...]


@dataclass(frozen=True)
class StandardConfig:
    code: str
    file_name: str
    extraction: str
    chapters: tuple[Chapter, ...]
    tables: tuple[TableGroup, ...]
    notes: str


CONFIGS = [
    StandardConfig(
        code="GB-55034-2022",
        file_name="GB-55034-2022_建筑与市政施工现场安全卫生与职业健康通用规范.pdf",
        extraction="ocr",
        chapters=(
            Chapter("01", "总则", 4, 4),
            Chapter("02", "基本规定", 5, 5),
            Chapter("03", "安全管理", 6, 14),
            Chapter("04", "环境管理", 15, 15),
            Chapter("05", "卫生管理", 16, 16),
            Chapter("06", "职业健康管理", 17, 19),
        ),
        tables=(),
        notes="住建部官方附件，图像层/水印 PDF；按正文六章拆分并注入 OCR 文本缓存。",
    ),
    StandardConfig(
        code="JGJ-33-2012",
        file_name="JGJ-33-2012_建筑机械使用安全技术规程.pdf",
        extraction="ocr",
        chapters=(
            Chapter("01", "总则", 13, 13),
            Chapter("02", "基本规定", 14, 15),
            Chapter("03", "动力与电气装置", 16, 23),
            Chapter("04", "建筑起重机械", 24, 45),
            Chapter("05", "土石方机械", 46, 62),
            Chapter("06", "运输机械", 63, 68),
            Chapter("07", "桩工机械", 69, 82),
            Chapter("08", "混凝土机械", 83, 90),
            Chapter("09", "钢筋加工机械", 91, 95),
            Chapter("10", "木工机械", 96, 101),
            Chapter("11", "地下施工机械", 102, 107),
            Chapter("12", "焊接机械", 108, 115),
            Chapter("13", "其他中小型机械", 116, 134),
        ),
        tables=(
            TableGroup(
                "08_混凝土机械_表格",
                (83, 84, 85, 86, 87, 88, 89, 90),
                (
                    "表格说明：第8章混凝土机械相关条文页，重点用于混凝土泵、泵车、支腿、输送管和作业稳定性检索。",
                    "关联条文：第8章；事故映射重点：泵车支腿支设、垫木/地基承载、混凝土输送作业安全。",
                ),
            ),
        ),
        notes="住建部官方附件，图像层/水印 PDF；章页码按目录和正文页人工配置，混凝土机械章单独保留表格资产。",
    ),
    StandardConfig(
        code="GB-5725-2009",
        file_name="GB-5725-2009_安全网.pdf",
        extraction="ocr",
        chapters=(
            Chapter("01", "范围规范性引用文件术语和定义", 1, 4),
            Chapter("02", "分类标记和技术要求", 5, 10),
            Chapter("03", "试验方法", 11, 15),
            Chapter("04", "检验规则标识包装运输和贮存", 16, 18),
        ),
        tables=(
            TableGroup(
                "02_分类标记和技术要求_表格",
                (5, 6, 7, 8, 9, 10),
                (
                    "表格说明：安全平网、立网、密目式安全立网的分类、规格、物理性能和阻燃性能相关要求。",
                    "关联条文：第4章、第5章；事故映射重点：安全网缺失、不合格、选型错误、标识与检查不足。",
                ),
            ),
        ),
        notes="第三方 PDF 镜像，扫描件；按安全网正文逻辑分为定义、技术要求、试验、检验标识四组。",
    ),
    StandardConfig(
        code="GB-39800.6-2023",
        file_name="GB-39800.6-2023_个体防护装备配备规范第6部分电力.pdf",
        extraction="text",
        chapters=(
            Chapter("01", "范围规范性引用文件术语和定义", 7, 7),
            Chapter("02", "总体要求危害因素辨识和评估", 7, 7),
            Chapter("03", "个体防护装备的配备", 7, 14),
            Chapter("04", "附录A电力行业工种及可能存在的危害因素", 15, 19),
            Chapter("05", "附录B电力行业各工种个体防护装备的配备", 20, 42),
            Chapter("06", "参考文献", 43, 43),
        ),
        tables=(
            TableGroup(
                "03_个体防护装备的配备_表格",
                (8, 9, 10, 11, 12, 13, 14),
                (
                    "表格说明：表1列出主要作业类别、可能造成的事故或伤害类型以及适用的个体防护装备。",
                    "重点条目：带电作业、停电作业、高处作业、有限空间作业、野外作业。",
                    "事故映射重点：触电、电弧伤害、高处坠落、安全帽、安全带、安全网、绝缘防护用品。",
                ),
            ),
            TableGroup(
                "04_附录A电力行业工种及可能存在的危害因素_表格",
                (15, 16, 17, 18, 19),
                (
                    "表格说明：表A.1列出电力行业工种及可能存在的危害因素。",
                    "重点条目：输电、变电、配电、通用工种中涉及坠落、电伤害、坠落物和外露运动件的工种。",
                ),
            ),
            TableGroup(
                "05_附录B电力行业各工种个体防护装备的配备_表格",
                tuple(range(20, 43)),
                (
                    "表格说明：表B.1列出电力行业各工种个体防护装备配备、功能特点和建议最长更换期限。",
                    "重点装备：安全帽、职业眼面部防护具、防电弧服、带电作业用绝缘手套、安全鞋、安全带、自锁器、速差自控器、安全绳、安全网、个人保安线。",
                ),
            ),
        ),
        notes="国家标准 PDF 有可抽取文本；正文短、表格密集，因此单独拆出表1、表A.1、表B.1资产和说明。",
    ),
]


def main() -> int:
    if not TESSERACT_CMD.exists():
        print(f"Missing tesseract: {TESSERACT_CMD}", file=sys.stderr)
        return 1
    pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_CMD)

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    reports: list[dict] = []
    for cfg in CONFIGS:
        reports.append(process_standard(cfg))
    write_quality_report(reports)
    return 0


def process_standard(cfg: StandardConfig) -> dict:
    src = SOURCE_DIR / cfg.file_name
    out_dir = OUT_ROOT / cfg.code
    existing_page_texts = load_existing_page_texts(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(src)
    if existing_page_texts and len(existing_page_texts) == doc.page_count:
        page_texts = existing_page_texts
        print(f"{cfg.code}: reusing {len(page_texts)} OCR/text pages", flush=True)
    else:
        page_texts = extract_page_texts(doc, cfg.extraction)

    chapter_files: list[str] = []
    for chapter in cfg.chapters:
        pdf_path = out_dir / f"{chapter.no}_{chapter.title}.pdf"
        save_pages(doc, pdf_path, chapter.start_page, chapter.end_page)
        text = "\n".join(page_texts[chapter.start_page - 1 : chapter.end_page])
        text = clean_text_for_chunking(text)
        inject_cache(pdf_path, text)
        (out_dir / f"{chapter.no}_{chapter.title}.txt").write_text(text, encoding="utf-8")
        chapter_files.append(str(pdf_path.relative_to(PROJECT_ROOT)))

    table_files: list[str] = []
    for group in cfg.tables:
        table_dir = out_dir / group.name
        table_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = table_dir / f"{group.name}.pdf"
        save_selected_pages(doc, pdf_path, group.pages)
        docx_path = table_dir / "表格说明.docx"
        write_docx(docx_path, "\n".join(group.notes))
        table_files.extend([str(pdf_path.relative_to(PROJECT_ROOT)), str(docx_path.relative_to(PROJECT_ROOT))])

    raw_dir = out_dir / "_ocr_text"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for i, text in enumerate(page_texts, 1):
        (raw_dir / f"page_{i:03d}.txt").write_text(text, encoding="utf-8")

    return {
        "code": cfg.code,
        "source": str(src.relative_to(PROJECT_ROOT)),
        "pages": doc.page_count,
        "extraction": cfg.extraction,
        "chapters": len(cfg.chapters),
        "tables": len(cfg.tables),
        "chapter_files": chapter_files,
        "table_files": table_files,
        "notes": cfg.notes,
        "text_pages": sum(1 for text in page_texts if meaningful_text(text)),
        "watermark_only_pages": sum(1 for text in page_texts if is_watermark_only(text)),
    }


def load_existing_page_texts(out_dir: Path) -> list[str]:
    raw_dir = out_dir / "_ocr_text"
    if not raw_dir.exists():
        return []
    files = sorted(raw_dir.glob("page_*.txt"))
    if not files:
        return []
    return [path.read_text(encoding="utf-8") for path in files]


def extract_page_texts(doc: fitz.Document, extraction: str) -> list[str]:
    if extraction == "ocr":
        source = Path(doc.name)
        with ProcessPoolExecutor(max_workers=OCR_WORKERS) as pool:
            texts = list(pool.map(ocr_page_from_file, [(source, i) for i in range(doc.page_count)]))
        for idx, text in enumerate(texts, 1):
            print(f"OCR page {idx}/{doc.page_count}: chars={len(text)}", flush=True)
        return [clean_ocr_noise(text) for text in texts]

    texts: list[str] = []
    for idx, page in enumerate(doc, 1):
        text = page.get_text("text") or ""
        if not meaningful_text(text):
            text = ocr_page(page)
        texts.append(clean_ocr_noise(text))
        print(f"OCR/text page {idx}/{doc.page_count}: chars={len(texts[-1])}", flush=True)
    return texts


def ocr_page_from_file(args: tuple[Path, int]) -> str:
    source, page_index = args
    pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_CMD)
    with fitz.open(source) as doc:
        return ocr_page(doc[page_index])


def ocr_page(page: fitz.Page) -> str:
    pix = page.get_pixmap(dpi=OCR_DPI)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    text = pytesseract.image_to_string(
        img,
        lang="chi_sim+eng",
        config="--psm 6",
    )
    return text


def clean_ocr_noise(text: str) -> str:
    replacements = {
        "住房城乡建设部信息公开": "",
        "浏览专用": "",
        "标准分享网 www.bzfxw.com 免费下载": "",
        "www.bzfxw.com": "",
        "免费 下载": "",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_text_for_chunking(text: str) -> str:
    text = clean_ocr_noise(text)
    lines = [line.strip() for line in text.splitlines()]
    merged: list[str] = []
    article = re.compile(r"^(?:\d+\.)+\d+$")
    for line in lines:
        if not line:
            continue
        if merged and line[0] in "。；：、，)]”》":
            merged[-1] += line
            continue
        if article.fullmatch(line):
            merged.append(line + " ")
            continue
        if merged and merged[-1].endswith(" "):
            merged[-1] = merged[-1].rstrip() + " " + line
            continue
        merged.append(line)
    out = "\n".join(merged)
    out = re.sub(r"(?m)^((?:\d+\.)+\d+)(?=[^\d\s.])", r"\1 ", out)
    return out.strip()


def meaningful_text(text: str) -> bool:
    cleaned = clean_ocr_noise(text)
    cjk = sum(1 for ch in cleaned if "\u4e00" <= ch <= "\u9fff")
    alnum = sum(1 for ch in cleaned if ch.isalnum())
    return cjk >= 30 and alnum >= 80


def is_watermark_only(text: str) -> bool:
    cleaned = re.sub(r"(住房城乡建设部信息公开|浏览专用|\s)+", "", text)
    return not cleaned


def save_pages(doc: fitz.Document, out: Path, start_page: int, end_page: int) -> None:
    save_selected_pages(doc, out, tuple(range(start_page, end_page + 1)))


def save_selected_pages(doc: fitz.Document, out: Path, pages: tuple[int, ...]) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    new = fitz.open()
    for page_no in pages:
        if 1 <= page_no <= doc.page_count:
            new.insert_pdf(doc, from_page=page_no - 1, to_page=page_no - 1)
    new.save(out)
    new.close()


def inject_cache(path: Path, text: str) -> None:
    nc.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    stat = path.stat()
    cache_key = nc._sha256(f"{path.resolve()}|{stat.st_mtime_ns}|{stat.st_size}|{nc.PIPELINE_VERSION}")
    (nc.CACHE_DIR / f"{cache_key}.txt").write_text(text, encoding="utf-8")


def write_docx(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    paragraphs = [p.strip() for p in text.splitlines() if p.strip()]
    body = "".join(f"<w:p><w:r><w:t>{escape_xml(p)}</w:t></w:r></w:p>" for p in paragraphs)
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}<w:sectPr/></w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES_XML)
        zf.writestr("_rels/.rels", RELS_XML)
        zf.writestr("word/document.xml", document_xml)


def escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


CONTENT_TYPES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""

RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""


def write_quality_report(reports: list[dict]) -> None:
    lines = [
        "# Staging Cleaned Norm PDF Quality Report",
        "",
        "本目录为暂存清洗成果，不在默认规范管道扫描目录内；正式入库前需人工确认后迁入 `rag_data/rag_data`。",
        "",
        "## Summary",
        "",
        "| 标准 | 来源页数 | 抽取方式 | 章节 PDF | 表格说明组 | 有效文本页 | 备注 |",
        "| --- | ---: | --- | ---: | ---: | ---: | --- |",
    ]
    for report in reports:
        lines.append(
            f"| {report['code']} | {report['pages']} | {report['extraction']} | "
            f"{report['chapters']} | {report['tables']} | {report['text_pages']} | {report['notes']} |"
        )
    lines.extend(
        [
            "",
            "## Deferred",
            "",
            "- `GB/T 6067.1-2010` 暂缓：当前 PDF 是释义/应用说明型材料，且规范范围较宽，暂不清洗入库。",
            "",
            "## Files",
            "",
        ]
    )
    for report in reports:
        lines.append(f"### {report['code']}")
        lines.append("")
        lines.append(f"- Source: `{report['source']}`")
        lines.append(f"- Extraction: `{report['extraction']}`")
        lines.append("- Chapter PDFs:")
        lines.extend(f"  - `{path}`" for path in report["chapter_files"])
        if report["table_files"]:
            lines.append("- Table / figure assets and notes:")
            lines.extend(f"  - `{path}`" for path in report["table_files"])
        lines.append("")
    lines.extend(
        [
            "## Known Quality Notes",
            "",
            "- OCR 标准已经去除住建部水印和下载站水印，但字符级错字仍需在论文引用关键条文前人工抽查。",
            "- `GB-39800.6-2023` 表格跨度大，已用独立表格说明增强检索入口；正式入库前可继续人工补充表格行级说明。",
            "- 本次未修改 `src/data_pipeline/norm_chunker.py`、`data/taxonomy/tags.yaml` 或正式 chunks/index。",
        ]
    )
    (OUT_ROOT / "QUALITY_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
