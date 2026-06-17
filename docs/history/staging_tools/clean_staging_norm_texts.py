#!/usr/bin/env python3
"""Post-clean staging sidecar text before promoting staged norms.

This script intentionally edits only `.txt` sidecars under
`rag_data/staging_cleaned`; the chapter PDFs remain the traceable visual assets.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "rag_data" / "staging_cleaned"


def main() -> int:
    clean_all_sidecars()
    split_gb39800_page()
    apply_targeted_fixes()
    return 0


def clean_all_sidecars() -> None:
    for path in STAGING.rglob("*.txt"):
        if "_ocr_text" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        path.write_text(generic_clean(text), encoding="utf-8")


def generic_clean(text: str) -> str:
    text = text.replace("住房城乡建设部信息公开", "")
    text = text.replace("浏览专用", "")
    text = text.replace("标准分享网 www bzfxw com 免费下载", "")
    text = text.replace("标准分享网 www.bzfxw.com 免费下载", "")
    text = text.replace("www bzfxw com", "")
    text = text.replace("GB39800.\n1", "GB39800.1")
    text = text.replace("GB39800.\n6", "GB39800.6")
    text = text.replace("4.\n2", "4.2")
    text = text.replace("3.2 S2", "3.2.2")
    text = text.replace("3. 2. 2", "3.2.2")
    text = text.replace("3. 10", "3.10")
    text = text.replace("5. 1.", "5.1.")
    text = text.replace("5. 2.", "5.2.")
    text = re.sub(r"(?m)^\s*\d+\s*$", "", text)

    cleaned: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            cleaned.append("")
            continue
        cjk = sum("\u4e00" <= ch <= "\u9fff" for ch in line)
        latin = sum(ch.isascii() and ch.isalpha() for ch in line)
        if cjk == 0 and latin >= 8:
            continue
        if cjk <= 2 and latin > max(12, cjk * 6) and not re.search(r"GB|JGJ|NB/T|mm|m/s|kV|kN|N\b", line):
            continue
        cleaned.append(line)
    out = "\n".join(cleaned)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip() + "\n"


def split_gb39800_page() -> None:
    base = STAGING / "GB-39800.6-2023"
    page = (base / "_ocr_text" / "page_007.txt").read_text(encoding="utf-8")
    page = generic_clean(page)
    sec4 = page.index("4 总体要求")

    part_1_3 = page[:sec4].strip()
    part_4_5 = page[sec4:].strip()

    table_pages = []
    for page_no in range(8, 15):
        p = base / "_ocr_text" / f"page_{page_no:03d}.txt"
        table_pages.append(generic_clean(p.read_text(encoding="utf-8")).strip())
    table_text = "\n".join(table_pages)
    sec6_match = re.search(r"(?m)^6\s*\n个体防护装备的配备", table_text)
    if sec6_match:
        sec6_text = "6 个体防护装备的配备\n" + table_text[sec6_match.end() :].strip()
    else:
        sec6_match = re.search(r"(?m)^6 个体防护装备的配备", table_text)
        if not sec6_match:
            raise ValueError("Could not locate GB-39800.6 chapter 6 heading")
        sec6_text = table_text[sec6_match.start() :].strip()

    (base / "01_范围规范性引用文件术语和定义.txt").write_text(part_1_3 + "\n", encoding="utf-8")
    (base / "02_总体要求危害因素辨识和评估.txt").write_text(part_4_5 + "\n", encoding="utf-8")
    (base / "03_个体防护装备的配备.txt").write_text(sec6_text + "\n", encoding="utf-8")


def apply_targeted_fixes() -> None:
    replacements_by_file = {
        "GB-55034-2022/03_安全管理.txt": {
            "3.4 起 BE": "3.4 起重伤害",
            "3444NLC品装作业前": "3.4.1 吊装作业前",
            "3.5 3 OB": "3.5 坍塌",
            "3.6 ik iE": "3.6 机械伤害",
            "3.6 7机械操作人员": "3.6.1 机械操作人员",
            "3.7 BMH #": "3.7 冒顶片帮",
            "3.9 PENSE": "3.9 中毒和窒息",
            "3.12、爆,破 作 业": "3.12 爆破作业",
            "3.2 S2": "3.2.2",
        },
        "JGJ-33-2012/08_混凝土机械.txt": {
            "8.4 ,混凝土输送泵": "8.4 混凝土输送泵",
            "8.4.1 混凝土泵应安放在平丫k 坚实的地面上": "8.4.1 混凝土泵应安放在平整、坚实的地面上",
            "支腿应支设牢靠%": "支腿应支设牢靠，",
            "8.4.10 HERBIE AR EM To PR TE We he BF EPR, BH,": "8.4.10 混凝土泵运行中发生故障时，应立即停机检查。",
        },
        "GB-5725-2009/01_范围规范性引用文件术语和定义.txt": {
            "33\n\n安全立网": "3.3\n安全立网",
            "311\nKG tie ropes": "3.11\n系绳 tie ropes",
            "3..19": "3.19",
            "#432 horizontal safety nets": "安全平网 horizontal safety nets",
        },
        "GB-5725-2009/02_分类标记和技术要求.txt": {
            "5.1.3 Set": "5.1.3 绳结构",
            "5.1.6 MMR": "5.1.6 规格尺寸",
        },
    }
    for rel, replacements in replacements_by_file.items():
        path = STAGING / rel
        text = path.read_text(encoding="utf-8")
        for old, new in replacements.items():
            text = text.replace(old, new)
        path.write_text(generic_clean(text), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
