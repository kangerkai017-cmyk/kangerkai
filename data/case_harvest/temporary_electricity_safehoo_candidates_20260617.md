# 临时用电/施工触电案例候选清单（safehoo 抓取）

抓取日期：2026-06-17

入口链接：https://sou.safehoo.com/?q=%E8%A7%A6%E7%94%B5%20%E6%96%BD%E5%B7%A5%E7%8E%B0%E5%9C%BA%20%E6%A1%88%E5%88%97

说明：

- 该入口页实际嵌入百度站内搜索 iframe，真实检索接口为 `https://zhannei.baidu.com/cse/site?...&cc=www.safehoo.com`。
- 原查询词中“案例”误写为“案列”，本次同时按“触电 施工现场 案例”和栏目页筛选。
- safehoo 是二级整理来源。正式入库和论文实验前，应优先追溯到应急管理局、区县政府或事故调查组发布的原始报告。
- 本文件只作为“temporary electricity / electric shock”任务扩充候选池，不等同于已入库、已标注、已验证案例。

## 已抓到正文的强候选

| 编号 | 标题 | safehoo 链接 | safehoo 标注来源 | 事故时间/后果 | 适合补充的任务点 | 入库建议 |
|---|---|---|---|---|---|---|
| TE-SH-01 | 长清济南经济开发区雨污分流改造项目“10.9”一般触电事故调查报告 | https://www.safehoo.com/Case/Case/Electric/202606/5808837.shtml | 长清区应急管理局 | 2023-10-09；1死2伤 | 市政雨污分流改造、总包/专业分包/监理链条、触电事故、迟报、作业人员违反安全技术操作规程 | 高优先级。页面含 PDF 文本预览，适合抽取完整结构字段。 |
| TE-SH-02 | 重庆酉阳资远建设工程有限公司“10·4”一般触电事故调查报告 | https://www.safehoo.com/Case/Case/Electric/202606/5809132.shtml | 重庆市应急管理局 | 2023-10-04；1死1伤，直接经济损失约150万元 | 乡村住房品质提升施工、脚手架搭设、钢管接触 10 kV 高压线、外电线路安全距离、现场监护缺失 | 高优先级。可形成“外电防护/安全距离/脚手架涉电”任务。 |
| TE-SH-03 | 黄岛区“8·25”北京侨信装饰工程有限公司一般触电事故调查报告 | https://www.safehoo.com/Case/Case/Electric/202605/5806963.shtml | 青岛市应急管理局 | 2017-08-25；1死，直接经济损失约175万元 | 大剧院室内精装修、临时用水用电方案、带电接线、无电工证、未切断电源、未佩戴劳动防护用品 | 高优先级。可形成“装修施工临时用电/带电作业禁止”任务。 |
| TE-SH-04 | 辽宁众翔建设有限公司“10·14”一般触电事故调查报告 | https://www.safehoo.com/Case/Case/Electric/202502/5763602.shtml | 海原县应急管理局 | 2024-10-14；1死1伤 | 站外临时废料堆放区吊装施工废料、吊装作业触电、现场作业管理、外电风险 | 高优先级。应进一步抽取直接原因、间接原因和涉及规范。 |

## 待复核候选

这些条目已从 safehoo 电气事故栏目或站内搜索结果确认标题和链接，但本轮未完整抽取正文。建议下一步逐条打开，优先找政府原始链接。

| 编号 | 标题 | safehoo 链接 | 为什么可能有用 | 初步优先级 |
|---|---|---|---|---|
| TE-SH-05 | 黄岛区“7·15”青岛平枝源装饰工程有限公司一般触电事故调查报告 | https://www.safehoo.com/Case/Case/Electric/202605/5806734.shtml | 装饰工程触电，可能与装修临时用电、带电作业、现场管理相关 | 高 |
| TE-SH-06 | 胶州青岛富居祥和装饰工程有限公司“7·16”一般触电事故调查报告 | https://www.safehoo.com/Case/Case/Electric/202605/5806372.shtml | 装饰工程触电，适合扩充装修施工涉电任务 | 高 |
| TE-SH-07 | 光明新湖太阳公寓装修工程“6·20”一般触电事故调查报告 | https://www.safehoo.com/Case/Case/Electric/202605/5805554.shtml | 装修工程触电，深圳地区报告通常结构较完整 | 高 |
| TE-SH-08 | 光明康佳光明科技中心 A 座 602-1 办公室装修工程“4·20”一般触电事故调查报告 | https://www.safehoo.com/Case/Case/Electric/202605/5805550.shtml | 办公室装修工程触电，可补“室内装修临时用电”场景 | 高 |
| TE-SH-09 | 深圳市深汕特别合作区鲘门镇百安村自建房“8·14”一般触电事故调查报告 | https://www.safehoo.com/Case/Case/Electric/202605/5805544.shtml | 自建房施工触电，适合覆盖小型建设工程和监管薄弱场景 | 中高 |
| TE-SH-10 | 江苏华能建设工程集团有限公司“7.4”触电死亡事故调查报告 | https://www.safehoo.com/Case/Case/Electric/202410/5750344.shtml | 检修锅炉炉腔触电，属于建设/检修单位作业触电，可作为施工检维修补充 | 中 |
| TE-SH-11 | 庐阳区中铁十局集团第三建设有限公司相关触电事故 | https://www.safehoo.com/Case/Case/Electric/202012/5619146.shtml | 中铁施工单位触电事故，可能与建筑施工现场临时用电强相关 | 高 |
| TE-SH-12 | 重庆渝龙电力开发有限责任公司“6·13”触电事故调查报告 | https://www.safehoo.com/Case/Case/Electric/202606/5809305.shtml | 电力施工/检修触电，可补外电作业和停送电管理任务 | 中 |
| TE-SH-13 | 武隆白马“8·6”一般触电事故调查报告 | https://www.safehoo.com/Case/Case/Electric/202606/5809563.shtml | 最新栏目候选，需确认是否属于施工现场 | 中 |
| TE-SH-14 | 长清济南经济开发区雨污分流改造项目“10.9”整改措施落实情况评估报告 | https://www.safehoo.com/Case/Case/Electric/202606/5809572.shtml | 可作为 TE-SH-01 的整改闭环补充，不宜单独当事故案例 | 低 |

## 2026-06-17 续抓与筛选结果

本轮从 safehoo 电气事故栏目页继续抓取 24 条原始候选，并生成机器可读表：

- `data/case_harvest/temporary_electricity_safehoo_candidates.tsv`
- 状态分布：`benchmark_added` 12 条，`agent_stress_candidate` 1 条，`review` 7 条，`exclude` 3 条，`existing_case` 1 条。
- 已追加到 `data/事故案例收集.md` 的正式案例：案例 77-88。
- 正式入库优先覆盖：市政雨污分流外电触电、脚手架外电安全距离、装修吊顶带电接线、装修临时线路无漏保/无接地/无防机械损伤、吊装碰触 10kV 高压线、电力线路换杆未取得停电作业票。

| 编号 | 标题 | safehoo 链接 | 状态 | 入库/复核理由 |
|---|---|---|---|---|
| TE-SH-15 | 崂山普民环保科技有限公司“6·6”一般触电事故调查报告 | https://www.safehoo.com/Case/Case/Electric/202605/5807143.shtml | agent_stress_candidate | 市政泵站运维、废弃供电线路裸露、盲目施救；施工属性弱，暂不进正式 benchmark。 |
| TE-SH-16 | 黄岛区“9·14”青岛三杨起重机械有限公司一般触电事故调查报告 | https://www.safehoo.com/Case/Case/Electric/202605/5806962.shtml | benchmark_added | 升降平台安装、电焊作业、无证特种作业和电焊机检查缺失。 |
| TE-SH-17 | 黄岛区“3·22”青岛华兴富洲旅游管理有限公司一般触电事故调查报告 | https://www.safehoo.com/Case/Case/Electric/202605/5806727.shtml | review | 经营场所海鲜池触电，非施工场景，暂不入库。 |
| TE-SH-18 | 西湖三墩西湖大学机电维保项目“3·27”一般触电事故调查报告 | https://www.safehoo.com/Case/Case/Electric/202605/5806549.shtml | review | 机电维保触电，需进一步确认与建筑施工临时用电的关系。 |
| TE-SH-19 | 黄岛青岛东方影都文化旅游管理有限公司“8·22”一般触电事故调查报告 | https://www.safehoo.com/Case/Case/Electric/202605/5806491.shtml | review | 照明维修触电，施工属性需人工复核。 |
| TE-SH-20 | 黄岛贝卡尔特（青岛）钢丝产品有限公司“10·15”一般触电事故调查报告 | https://www.safehoo.com/Case/Case/Electric/202605/5806476.shtml | review | 普通生产线用电事故，施工属性弱。 |
| TE-SH-21 | 平度“8.8”一般触电事故调查报告 | https://www.safehoo.com/Case/Case/Electric/202605/5805894.shtml | review | 电磁吸盘线路修理触电，施工属性弱。 |
| TE-SH-22 | 坪山龙田某工业区25号厂房“7·22”一般触电事故调查报告 | https://www.safehoo.com/Case/Case/Electric/202605/5805561.shtml | review | 工业厂房触电，需进一步核对施工/装修属性。 |
| TE-SH-23 | 关于大浪街道佳利工业区三栋一楼装修工程“8·25”触电死亡事故的调查报告 | https://www.safehoo.com/Case/Case/Electric/202604/5805449.shtml | benchmark_added | 装修工地临时导线无漏保、无地线、无防机械损伤，适合临时用电任务。 |

## 可转成 benchmark 的任务方向

1. 外电线路安全距离与防护：从 TE-SH-02 抽取“脚手架钢管靠近 10 kV 高压线”的场景，要求模型给出安全距离、隔离防护、停电/迁移/防护方案和监护要求。
2. 装修工程带电接线：从 TE-SH-03、TE-SH-05、TE-SH-06、TE-SH-07、TE-SH-08 抽取“未切断电源、无证接线、临时线路管理”的场景，要求链接到临时用电和特种作业要求。
3. 市政改造施工触电：从 TE-SH-01 抽取“雨污分流改造项目分包作业触电”场景，覆盖总包、分包、监理安全管理职责。
4. 吊装/外电复合风险：从 TE-SH-04 抽取“吊装废料过程触电”场景，要求模型同时识别起重吊装和外电触电风险。
5. 小型工程/自建房触电：从 TE-SH-09 抽取低组织化施工现场，测试模型能否在信息不足时提出保守、可执行的用电安全措施。

## 入库前必须补的字段

- `case_id`：建议使用 `TE-SH-xx` 或替换为政府原始报告编号。
- `source_url`：优先政府原始报告链接；safehoo 链接作为 `mirror_url`。
- `source_name`：应急管理局/区县政府/事故调查组，而不是只写“安全管理网”。
- `accident_type`：统一为 `electric shock` / `触电`。
- `scenario_tags`：建议包含 `临时用电`、`外电防护`、`装修施工`、`脚手架`、`吊装作业`、`市政工程` 等。
- `related_standards`：必须人工核验到条文级，优先检查 `JGJ 46`、外电线路防护、配电箱、漏电保护、接地接零、持证上岗、停电验电等条款。
- `process`、`direct_causes`、`indirect_causes`、`consequences`：从事故调查报告原文抽取，不使用搜索摘要替代。

## 与当前论文实验的关系

- 当前正式实验的 temporary electricity 子集只有 `n=2`，论文中已标为 diagnostic only。
- 如果从本清单至少抽取并核验 10 条案例，可把 temporary electricity 任务扩到 12-15 个，届时才适合作为主题级结果讨论。
- 在完成结构化入库、norm 链接校验和 DeepSeek/Qwen 重跑前，不应把这些案例写入正式结果表。
