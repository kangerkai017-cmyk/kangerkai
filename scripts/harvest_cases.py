#!/usr/bin/env python3
"""从政府事故调查报告 URL 清单抓取并结构化为案例格式（补充薄危险源类型）。

本机出口代理屏蔽政府站点，故本脚本须在**能访问政府网站**的网络下运行
（或先用你的爬虫把正文落盘到 data/case_harvest/raw/ 再跑 --offline）。

流程：读 candidates.tsv → 抓取(HTML/PDF/DOCX) → 本地 Qwen 忠实抽取字段 →
校验 related_standards 是否命中 17 部在库标准 → 输出案例格式 md + jsonl + 报告。

用法：
    python scripts/harvest_cases.py                 # 抓取 + 抽取
    python scripts/harvest_cases.py --offline        # 只用 raw/ 已落盘正文，不联网
    python scripts/harvest_cases.py --limit 5        # 只处理前 5 条（试跑）
"""
import argparse, json, os, re, sys, hashlib
from urllib.parse import urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARVEST = os.path.join(ROOT, "data", "case_harvest")
RAW = os.path.join(HARVEST, "raw")
NORM = os.path.join(ROOT, "data", "chunks", "norm_chunks.jsonl")
CAND = os.path.join(HARVEST, "candidates.tsv")
OUT_MD = os.path.join(HARVEST, "harvested.md")
OUT_JSONL = os.path.join(HARVEST, "harvested.jsonl")
REPORT = os.path.join(HARVEST, "harvest_report.md")

from pydantic import BaseModel, Field
from src.llm_utils import call_llm_json

FIELDS = ["事故类别","时间","地点","事故经过","直接原因","间接原因","违反规范","伤亡情况","直接经济损失"]


class CaseExtract(BaseModel):
    事故类别: str = ""
    时间: str = ""
    地点: str = ""
    事故经过: str = ""
    直接原因: str = ""
    间接原因: str = ""
    违反规范: list[str] = Field(default_factory=list)
    伤亡情况: str = ""
    直接经济损失: str = ""


SYSTEM = "你是事故调查报告结构化抽取助手。只依据给定正文忠实抽取，缺失字段填\"暂无\"，严禁编造。"
USER_TMPL = (
    "下面是一份事故调查报告正文。请抽取为 JSON，字段："
    "事故类别(如触电/高处坠落/物体打击/坍塌/起重伤害/机械伤害)、时间、地点、"
    "事故经过(简述)、直接原因、间接原因、违反规范(数组，逐条列出报告点名的法律法规或标准，"
    "若含具体标准号和条文号务必原样保留)、伤亡情况、直接经济损失。\n\n正文：\n{body}"
)


def load_norm_validation():
    valid, core2code = set(), {}
    with open(NORM, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            code, art = d.get("standard_code"), d.get("article_id")
            if code and art:
                valid.add((code, str(art).strip()))
            if code:
                core = code.split("-")[1]
                core2code[core] = code
                core2code[core.lstrip("T")] = code
    return valid, core2code


CODE_PAT = re.compile(r"(JGJ|GB)\s*/?\s*-?\s*(T)?\s*([0-9]+(?:\.[0-9]+)?)")
ART_PAT = re.compile(r"第\s*([0-9]+(?:\.[0-9]+)+)\s*条|(?<![0-9.])([0-9]+\.[0-9]+(?:\.[0-9]+)*)(?![0-9.])")


def verified_refs(viol_text, valid, core2code):
    cores = set()
    for m in CODE_PAT.finditer(viol_text):
        core = m.group(3); tcore = ("T"+core) if m.group(2) else core
        for c in (tcore, core):
            if c in core2code:
                cores.add(core2code[c])
    arts = {(m.group(1) or m.group(2) or "").strip().rstrip(".") for m in ART_PAT.finditer(viol_text)}
    arts.discard("")
    return sorted({f"{code}:{a}" for code in cores for a in arts if (code, a) in valid})


def fetch(url):
    import requests
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    r = requests.get(url, headers=headers, timeout=40, verify=False)
    r.raise_for_status()
    return r.content, r.headers.get("Content-Type", "")


def pdf_to_text(data):
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=data, filetype="pdf")
        return "\n".join(p.get_text() for p in doc)
    except Exception:
        pass
    try:
        import io
        from pdfminer.high_level import extract_text
        return extract_text(io.BytesIO(data))
    except Exception:
        pass
    # last resort: pdftotext binary
    import subprocess, tempfile
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
        tf.write(data); path = tf.name
    try:
        return subprocess.run(["pdftotext", path, "-"], capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return ""


def html_to_text(data):
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(data, "html.parser")
        for t in soup(["script", "style"]):
            t.decompose()
        return soup.get_text("\n")
    except Exception:
        txt = data.decode("utf-8", "ignore") if isinstance(data, bytes) else data
        txt = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", txt)
        return re.sub(r"(?s)<[^>]+>", " ", txt)


def docx_to_text(data):
    try:
        import io
        from docx import Document
        return "\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs)
    except Exception:
        return ""


def extract_text(data, ctype, url):
    u = url.lower()
    if u.endswith(".pdf") or "pdf" in ctype:
        return pdf_to_text(data)
    if u.endswith(".docx") or "word" in ctype or "officedocument" in ctype:
        return docx_to_text(data)
    return html_to_text(data)


def cache_path(url):
    return os.path.join(RAW, hashlib.sha256(url.encode()).hexdigest()[:16] + ".txt")


def get_text(url, offline):
    cp = cache_path(url)
    if os.path.exists(cp):
        return open(cp, encoding="utf-8").read()
    if offline:
        return ""
    data, ctype = fetch(url)
    text = extract_text(data, ctype, url)
    text = re.sub(r"\n{3,}", "\n\n", (text or "").strip())
    open(cp, "w", encoding="utf-8").write(text)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="只用 raw/ 已落盘正文，不联网")
    ap.add_argument("--limit", type=int, default=0, help="只处理前 N 条（试跑）")
    args = ap.parse_args()

    import warnings
    warnings.filterwarnings("ignore")  # 静默 verify=False 警告

    valid, core2code = load_norm_validation()
    rows = []
    with open(CAND, encoding="utf-8") as f:
        next(f)  # header
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 3 and parts[2].strip():
                rows.append((parts[0].strip(), parts[1].strip(), parts[2].strip()))
    if args.limit:
        rows = rows[: args.limit]

    done_urls = set()
    if os.path.exists(OUT_JSONL):
        for line in open(OUT_JSONL, encoding="utf-8"):
            try:
                done_urls.add(json.loads(line)["url"])
            except Exception:
                pass

    md_blocks, recs, fails = [], [], []
    linked = 0
    for hz, title, url in rows:
        if url in done_urls:
            continue
        try:
            text = get_text(url, args.offline)
            if not text or len(text) < 80:
                fails.append((url, "正文为空/过短（可能抓取失败或需 --offline 落盘）"))
                continue
            prompt = USER_TMPL.format(body=text[:8000])
            ext = call_llm_json(prompt, SYSTEM, response_model=CaseExtract, temperature=0.2)
            viol_text = " ".join(ext.违反规范) if isinstance(ext.违反规范, list) else str(ext.违反规范)
            refs = verified_refs(viol_text, valid, core2code)
            if refs:
                linked += 1
            rec = {"hazard_hint": hz, "title": title, "url": url,
                   "source": urlparse(url).netloc, **ext.model_dump(),
                   "related_standards_verified": refs}
            recs.append(rec)
            block = [f"### 案例：{title}", ""]
            for fld in FIELDS:
                v = rec[fld]
                v = ("；".join(v) if isinstance(v, list) else v) or "暂无"
                block.append(f"- **{fld}**：{v}")
            block.append(f"- **来源**：{rec['source']}")
            block.append(f"- **原文链接**：{url}")
            block.append(f"- **related_standards（已验证在库）**：{', '.join(refs) if refs else '（无，警示/检索用）'}")
            block += ["", "---", ""]
            md_blocks.append("\n".join(block))
            print(f"[OK] {hz} | {title[:24]} | 链接条文={len(refs)}")
        except Exception as e:
            fails.append((url, f"{type(e).__name__}: {e}"))
            print(f"[FAIL] {url} -> {e}")

    # append outputs
    with open(OUT_MD, "a", encoding="utf-8") as f:
        if os.path.getsize(OUT_MD) == 0 if os.path.exists(OUT_MD) else True:
            f.write("# 网络抓取补充案例（政府事故调查报告，忠实抽取）\n\n")
        f.write("\n".join(md_blocks))
    with open(OUT_JSONL, "a", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    from collections import Counter
    by_hz = Counter(r["hazard_hint"] for r in recs)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write(f"# 抓取报告\n\n本次新增 {len(recs)} 条；含已验证在库链接 {linked} 条；失败 {len(fails)} 条。\n\n")
        f.write("## 按危险源\n" + "\n".join(f"- {k}: {v}" for k, v in by_hz.items()) + "\n\n")
        if fails:
            f.write("## 失败清单\n" + "\n".join(f"- {u} :: {why}" for u, why in fails) + "\n")
    print(f"\n新增 {len(recs)} 条（链接 {linked}），失败 {len(fails)}。输出: {OUT_MD} / {OUT_JSONL} / {REPORT}")


if __name__ == "__main__":
    main()
