from src.schema import NormChunk, CaseChunk

NORM_CHUNKS: list[NormChunk] = [
    NormChunk(
        chunk_id="norm_001",
        standard_name="JGJ 80-2016 建筑施工高处作业安全技术规范",
        chapter="4 临边与洞口作业",
        article_id="4.1.1",
        text="坠落高度基准面2m及以上进行临边作业时，应在临空一侧设置防护栏杆，防护栏杆应由上、下两道横杆及栏杆柱组成，上杆离地高度应为1.2m，下杆离地高度应为0.6m，并应设置挡脚板。挡脚板高度不应小于180mm。",
        scenario_tags=["高处作业", "临边作业"],
        hazard_tags=["高处坠落", "物体打击"],
        requirement_type="强制性要求",
        source="JGJ 80-2016",
    ),
    NormChunk(
        chunk_id="norm_002",
        standard_name="JGJ 80-2016 建筑施工高处作业安全技术规范",
        chapter="4 临边与洞口作业",
        article_id="4.2.1",
        text="短边边长大于等于500mm的水平洞口，四周应设置防护栏杆，洞口下方应张挂安全平网。短边边长小于500mm的洞口，应采用坚实的盖板覆盖，盖板应能承受1.1kN/m²的荷载。",
        scenario_tags=["高处作业", "洞口作业"],
        hazard_tags=["高处坠落"],
        requirement_type="强制性要求",
        source="JGJ 80-2016",
    ),
    NormChunk(
        chunk_id="norm_003",
        standard_name="JGJ 46-2005 施工现场临时用电安全技术规范",
        chapter="8 配电箱及开关箱",
        article_id="8.2.10",
        text="开关箱中必须装设漏电保护器，漏电保护器的额定漏电动作电流不应大于30mA，额定漏电动作时间不应大于0.1s。使用于潮湿或有腐蚀介质场所的漏电保护器应采用防溅型产品，其额定漏电动作电流不应大于15mA。",
        scenario_tags=["临时用电", "配电箱使用"],
        hazard_tags=["触电"],
        requirement_type="强制性要求",
        source="JGJ 46-2005",
    ),
    NormChunk(
        chunk_id="norm_004",
        standard_name="JGJ 46-2005 施工现场临时用电安全技术规范",
        chapter="7 电缆线路",
        article_id="7.2.3",
        text="电缆线路应采用埋地或架空敷设，严禁沿地面明设。电缆直接埋地敷设的深度不应小于0.7m，并应在电缆紧邻上、下、左、右侧均匀敷设不小于50mm厚的细砂，然后覆盖砖或混凝土板等硬质保护层。",
        scenario_tags=["临时用电", "电缆敷设"],
        hazard_tags=["触电", "火灾"],
        requirement_type="强制性要求",
        source="JGJ 46-2005",
    ),
]

CASE_CHUNKS: list[CaseChunk] = [
    CaseChunk(
        chunk_id="case_001",
        case_title="某住宅项目脚手架拆除高处坠落事故",
        accident_type="高处坠落",
        scenario_tags=["高处作业", "脚手架拆除"],
        hazard_tags=["高处坠落"],
        process="2023年3月，某住宅项目工地进行外脚手架拆除作业。作业人员王某在拆除顶层脚手板时，未系挂安全带，踩踏已松动的脚手板，从12m高处坠落至地面，经抢救无效死亡。",
        causes="1. 作业人员高处作业未系挂安全带；2. 脚手架拆除作业前未进行安全技术交底；3. 拆除区域下方未设置警戒线和安全网；4. 现场安全管理人员未及时发现和制止违章行为。",
        consequences="1人死亡，直接经济损失约150万元。项目停工整改30天，施工单位被暂扣安全生产许可证。",
        corrective_measures="1. 高处作业必须系挂安全带并设置独立安全绳；2. 拆除作业前必须进行书面安全技术交底；3. 拆除区域下方设置警戒区并张挂安全平网；4. 配备专人旁站监护。",
        text="2023年3月，某住宅项目工地进行外脚手架拆除作业。作业人员王某在拆除顶层脚手板时，未系挂安全带，踩踏已松动的脚手板，从12m高处坠落至地面，经抢救无效死亡。事故原因：作业人员高处作业未系挂安全带；脚手架拆除作业前未进行安全技术交底；拆除区域下方未设置警戒线和安全网；现场安全管理人员未及时发现和制止违章行为。",
        source="住房和城乡建设部事故通报",
    ),
    CaseChunk(
        chunk_id="case_002",
        case_title="某商业综合体临时用电触电事故",
        accident_type="触电",
        scenario_tags=["临时用电", "配电箱使用"],
        hazard_tags=["触电"],
        process="2023年7月，某商业综合体工地在进行室内装修作业时，作业人员李某使用手持电动工具时发生触电。调查发现，李某使用的开关箱漏电保护器已损坏多日未更换，且电动工具电源线绝缘层破损，铜线外露。李某作业时手部出汗，接触到带电部分后触电倒地，经抢救后脱离生命危险但造成右手部分功能丧失。",
        causes='1. 开关箱漏电保护器损坏未及时更换；2. 电动工具电源线绝缘破损未检查修复；3. 作业前未进行用电设备安全检查；4. 未执行「一机、一闸、一漏、一箱」的配电要求。',
        consequences="1人重伤（右手部分功能丧失），直接经济损失约60万元。项目停工整改15天。",
        corrective_measures='1. 严格执行漏电保护器每日试跳检查制度；2. 电动工具使用前必须检查电源线和插头完好性；3. 潮湿环境作业应使用防溅型漏电保护器（动作电流≤15mA）；4. 落实「一机一闸一漏一箱」配电要求。',
        text='2023年7月，某商业综合体工地在进行室内装修作业时，作业人员李某使用手持电动工具时发生触电。调查发现，李某使用的开关箱漏电保护器已损坏多日未更换，且电动工具电源线绝缘层破损，铜线外露。李某作业时手部出汗，接触到带电部分后触电倒地。事故原因：开关箱漏电保护器损坏未及时更换；电动工具电源线绝缘破损未检查修复；作业前未进行用电设备安全检查；未执行「一机、一闸、一漏、一箱」的配电要求。',
        source="应急管理部事故通报",
    ),
]


def get_norm_chunks() -> list[NormChunk]:
    return NORM_CHUNKS


def get_case_chunks() -> list[CaseChunk]:
    return CASE_CHUNKS


def get_all_chunks() -> tuple[list[NormChunk], list[CaseChunk]]:
    return NORM_CHUNKS, CASE_CHUNKS
