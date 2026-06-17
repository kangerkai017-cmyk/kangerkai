# Norm Standard 章节挑选清单（v1）

> 用途：每部规范都只入库**与论文事故案例直接相关**的章节，避免把设计计算、术语、附录证书等无关内容塞进 ES。
>
> 规则：
> - 找到 PDF 后，按"保留"列表的章节切分成单独 PDF 文件
> - 命名格式：`XX_章节名.pdf`，前两位为 chapter_no（与规范原章节号一致即可），下划线后为章节名
> - 放入 `rag_data/rag_data/<标准号>/`，标准号用 `JGJ-XXX-YYYY` 格式（含连字符）
> - 重跑 `scripts/build_norm_chunks.py` + `scripts/_upsert_norm_index.py`
> - 重跑 `scripts/build_training_tasks.py` 看新解锁的 task 数

## 已入库

### TSG 51-2023 起重机械安全技术规程 ✓
- 保留：Ch 4 安装和修理、Ch 5 使用管理、Ch 6 检验（共 54 chunks）
- 跳过：Ch 1 总则、Ch 2 设计、Ch 3 制造、Ch 7 附则、附件 A-H
- 解锁：case-76 → task-起重吊装-013（Tier-W）

### GB 50303-2015 建筑电气工程施工质量验收规范 ✓
- 保留：Ch 3 基本规定、Ch 13 电缆敷设、Ch 17 电缆头制作导线连接和线路绝缘测试、Ch 22 接地装置安装（共 92 chunks）
- 解锁：case-69 → task-临时用电-001（Tier-W）

### JGJ 180-2009 建筑施工土石方工程安全技术规范 ✓
- 保留：Ch 2 基本规定、Ch 6 基坑工程、Ch 7 边坡工程（共 42 chunks，含强制性条文 6.3.2）
- 解锁：case-63 → task-脚手架-XX

### GB 50617-2010 建筑电气照明装置施工与验收规范 ✓
- 保留：Ch 3 基本规定、Ch 4 灯具、Ch 7 通电试运行及测量（共 62 chunks）
- 跳过：Ch 5 插座开关风扇（OCR 未识别章节边界，与案例无关）
- 解锁：case-70 → task-临时用电-002（Tier-W）

### GB/T 13869-2017 用电安全导则 ✓
- 保留：全文（17 chunks，章节短紧凑）
- 涉及 case-68（未自动解锁——案例引用是 standard 级而非条文级，Tier-W BM25 代理未匹配；如需可手工补条文号）

### JGJ 147-2016 建筑拆除工程安全技术规范 ✓
- 保留：Ch 3 基本规定、Ch 4 施工准备、Ch 5 拆除施工、Ch 6 安全管理（共 69 chunks）
- 跳过：Ch 1 总则、Ch 2 术语、Ch 7 文明施工、条文说明、附录
- 解锁：case-56 → task-脚手架-020（Tier-W）
- case-51/53 仍未解锁——它们引用书名《建筑拆除工程安全技术规范》而非代码 JGJ-147-2016；
  需要后续手工补 chapter→case 映射或在 chunker 加 standard_name→code 别名

### 入库后规范库统计（含 JGJ-147）
- norm chunks 总数：1455 → **1791**（+336）
- 已入库标准：17 → **23**（含 TSG-51、JGJ-147 + 4 部 OCR 入库）
- v1 任务集：33 → **46**（+13）
- 4 主题首次齐全：高处作业 9 / 脚手架 22 / 起重吊装 13 / 临时用电 2

### 数据库质量审计（已清理）
- 噪声 article_id：修复 2 处 OCR 漏点错误（`32.10`→`3.2.10`、`42.5`→`4.2.5`，均来自 GB-50303 OCR）
- 顺手清正文开头垃圾引号（GB-6095、GB-T13869 共 3 处）
- 检查并确认：
  - 0 个 duplicate chunk_id
  - 0 个 missing required fields
  - 17 个深嵌套 article（GB-5725 / TSG-51 合法 5 段编号）非噪声
  - 42 个短 article（<30 CJK）全部是 GB-6095 历史 OCR 残留，非本轮引入

### OCR 入库流程（已固化为脚本路径）
1. 源 PDF 放项目根目录
2. 一次性脚本 `_ocr_split_uploaded_norms.py`（已删，需用时复刻）：
   - 缓存 OCR 到 `data/ocr/_raw/<stem>/p001.txt` (已保留 1.2 MB)
   - 扫描全部 1-30 章节起始页（容忍行首 0-2 OCR 噪声字）
   - 单调子序列过滤 + TOC 密度检测 + 条文说明边界识别
   - 切章节 PDF 进 `rag_data/rag_data/<std>/`，注入 chunker cache
3. `python scripts/build_norm_chunks.py`
4. 一次性 upsert 脚本（已删，复用 case 的 upsert 模板改索引名即可）
5. `python scripts/build_training_tasks.py`

## 待补 PDF（已无强阻塞）

所有 P0/P1 优先级标准均已入库。以下仅作未来扩展参考。

### 1. ~~GB 50303-2015 建筑电气工程施工质量验收规范~~ ✓ 已完成
### 2. ~~JGJ 147-2016 建筑拆除工程安全技术规范~~ ✓ 已完成（再次上传完整版后入库）

**全规范 25 章，只保留 4 章**：

| 章号 | 章节名 | 文件命名 | 解锁案例 |
|---|---|---|---|
| 3 | 基本规定 | `03_基本规定.pdf` | 基础语境 |
| 13 | 电缆敷设 | `13_电缆敷设.pdf` | **case-66**（上海宝山龙延，打穿暗埋电缆触电）|
| 17 | 电缆头制作、导线连接和线路绝缘测试 | `17_电缆头制作导线连接和线路绝缘测试.pdf` | case-66, **case-69** |
| 22 | 接地装置安装 | `22_接地装置安装.pdf` | **case-69**（民治东头村，多电气规范交叉）|

**跳过**（21 章 + 8 附录）：Ch 1 总则、Ch 2 术语、Ch 4-12（变压器/配电柜/电机等设备安装，事故案例不涉及）、Ch 14-16（穿线敷线）、Ch 18-21（灯具开关）、Ch 23-25（防雷等电位）、所有附录（试验/拧紧力矩参数表）

放入：`rag_data/rag_data/GB-50303-2015/`

预期收益：临时用电主题从 0 → 3+ 任务

---

### 2. JGJ 147-2016 建筑拆除工程安全技术规范（解锁 case-51/53/56 拆除事故）

**全规范 7 章，保留 4 章**：

| 章号 | 章节名 | 文件命名 |
|---|---|---|
| 3 | 基本规定 | `03_基本规定.pdf` |
| 4 | 施工准备 | `04_施工准备.pdf` |
| 5 | 拆除施工 | `05_拆除施工.pdf` ★（最核心，case-51 案例 9 第 5.1.3 条来源）|
| 6 | 安全管理 | `06_安全管理.pdf` |

跳过：Ch 1 总则、Ch 2 术语、Ch 7 文明施工

放入：`rag_data/rag_data/JGJ-147-2016/`

预期收益：解锁 case-51 / case-53 / case-56 共 3 个任务

---

### 3. JGJ 180-2009 建筑施工土石方工程安全技术规范（解锁 case-63 基坑事故）

**全规范 7 章，保留 3 章**：

| 章号 | 章节名 | 文件命名 |
|---|---|---|
| 2 | 基本规定 | `02_基本规定.pdf`（含强制性 2.0.x 条）|
| 6 | 基坑工程 | `06_基坑工程.pdf` ★（含强制性 6.3.2 条，case-63 4.8 米沟槽无放坡直接对应）|
| 7 | 边坡工程 | `07_边坡工程.pdf` |

跳过：Ch 1 总则、Ch 3 机械设备、Ch 4 场地平整、Ch 5 土石方爆破

放入：`rag_data/rag_data/JGJ-180-2009/`

预期收益：解锁 case-63（丁桥单元基坑坍塌）+ 可能让其他几个坍塌 case 命中

---

### 4. GB/T 13869-2017 用电安全导则（解锁 case-68 触电）

整本约 30 页，结构紧凑。**全部入库**——这部是导则不是验收规范，全文都是安全要求。

切章节按其 TOC 即可（"基本原则" / "操作安全" / "防触电措施" 等）。

放入：`rag_data/rag_data/GB-T13869-2017/`（GB/T 用 `GB-T13869-2017` 形式，与现有 `GB-T46-2024` 风格一致）

---

### 5. GB 50617-2010 建筑电气照明装置施工与验收规范（次优先，解锁 case-70）

仅 case-70 一例引用，且只引用第 4.1.1(2) 条。**只切第 4 章**入库即可：
- `04_基本规定_或_照明配电.pdf`（找原文 4.x 章节名填）

放入：`rag_data/rag_data/GB-50617-2010/`

预期：+1 任务

---

## 拉 PDF 的渠道总结

| 网站 | 类型 | 备注 |
|---|---|---|
| openstd.samr.gov.cn | 官方 | GB / GB-T 可在线阅读，多页另存 |
| mohurd.gov.cn | 官方 | JGJ 系列，部分有直链 |
| waizi.org.cn / 集标数字资源网 | 民间整理 | 标榜"高清无水印"通常文字层可抽 |
| chinabuilding.com.cn | 中国建工出版社官方 | 可看到完整 TOC，电子版收费 |
| 工标网 csres.com | 付费 | 最全，30-50 元/部 |

**必须验证**：下载后用 `pdfplumber` 抽前 3 页文字，看是否乱码。乱码 = 扫描版需 OCR，参考 `scripts/ocr_image_norm.py`。

---

## 章节切分操作

PDF 切分推荐工具（任选其一）：

```bash
# pypdf（Python，本项目已装）
python3 -c "
from pypdf import PdfReader, PdfWriter
r = PdfReader('源.pdf')
w = PdfWriter()
for p in range(START_1IDX-1, END_1IDX): w.add_page(r.pages[p])
w.write(open('05_拆除施工.pdf','wb'))
"

# 或 pdftk（命令行）
pdftk source.pdf cat 21-30 output 05_拆除施工.pdf

# 或在线 PDF24/Smallpdf
```

---

## 完成后流程

```bash
# 1. 重建 norm chunks（30s）
CUDA_VISIBLE_DEVICES="" NO_PROXY=localhost,127.0.0.1 python3 scripts/build_norm_chunks.py

# 2. upsert 进 ES（绕开 master 队列锁）
CUDA_VISIBLE_DEVICES="" NO_PROXY=localhost,127.0.0.1 python3 scripts/_upsert_norm_index.py
# 如果脚本已删除，复用 case 的 upsert 模板改下索引名即可

# 3. 重跑 v1 任务集
CUDA_VISIBLE_DEVICES="" NO_PROXY=localhost,127.0.0.1 python3 scripts/build_training_tasks.py

# 4. 跑测试
CUDA_VISIBLE_DEVICES="" NO_PROXY=localhost,127.0.0.1 python3 -m pytest tests/test_training_tasks.py -v
```

每完成一部规范，跑一遍以上 4 步，task 数应稳步增加。

## 目标

完成全部 5 部规范后预期：
- 任务总数：41 → ~50+
- 4 主题全部覆盖（临时用电从 0 → 4+）
- A 档（Tier-S 库内 + 条文）从 33 → ~40
