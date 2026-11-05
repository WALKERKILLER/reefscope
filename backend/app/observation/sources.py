"""Reference cards the report may cite. `supports` and `limits` are always read together.

Bibliographic fields were checked against Crossref or the publisher page on 2026-11-05.
"""

SOURCES = {
    "CRW-BAA": {
        "title": "NOAA Coral Reef Watch 5km Daily Products Methodology (v3.1)",
        "authors": "NOAA Coral Reef Watch", "year": 2023,
        "url": "https://coralreefwatch.noaa.gov/product/5km/methodology.php",
        "supports": "DHW 为 84 天窗口内 HotSpot ≥ 1 °C 的累积热胁迫（°C-weeks）；Bleaching Alert Area 按 HotSpot 与 DHW 共同分级（2023 年 12 月更新）。",
        "limits": "约 5 km 卫星网格的海表热胁迫背景，不是原位水温、视频白化比例或死亡的因果证据。"},
    "SCHOBERND-2014": {
        "title": "Examining the utility of alternative video monitoring metrics for indexing reef fish abundance",
        "authors": "Schobernd, Bacheler, Conn", "year": 2014,
        "url": "https://doi.org/10.1139/cjfas-2013-0086",
        "supports": "MeanCount（逐帧计数的平均）与真实丰度近似线性；MaxN 在高密度时非线性并低估丰度。",
        "limits": "基于诱饵视频与模拟；相对丰度指数，不是绝对数量或密度。"},
    "HSU-2025": {
        "title": "Optimizing remote underwater video sampling to quantify relative abundance, richness, and corallivory rates of reef fish",
        "authors": "Hsu, Gordon, Ferrari, Hoey, Figueira", "year": 2025,
        "url": "https://doi.org/10.1007/s00338-024-02613-6",
        "supports": "讨论 MeanCount、MaxN、物种丰富度与视频抽帧采样努力之间的关系。",
        "limits": "研究地点与采样协议特定；最优抽帧数量不能直接套用到本平台视频。"},
    "AGRRA-2023": {
        "title": "AGRRA Coral Protocol",
        "authors": "Atlantic and Gulf Rapid Reef Assessment", "year": 2023,
        "url": "https://www.agrra.org/wp-content/uploads/2023/04/AGRRA-Coral-Protocol.pdf",
        "supports": "白化按群体分为 Pale / Partly Bleached / Bleached 等类别，并区分发生率（受影响群体占比）与严重度（受影响表面占比）。",
        "limits": "群体级现场调查协议；画面像素比例不能替代群体白化发生率。"},
    "SIEBECK-2006": {
        "title": "Monitoring coral bleaching using a colour reference card",
        "authors": "Siebeck, Marshall, Klüter, Hoegh-Guldberg", "year": 2006,
        "url": "https://doi.org/10.1007/s00338-006-0123-8",
        "supports": "CoralWatch 色卡以 1–6 级颜色分数记录白化，观察者间差异约 ±1 级。",
        "limits": "需要现场或校色图像中的色卡；本平台的分割模型不输出色卡分数。"},
    "GCRMN-2020": {
        "title": "Status of Coral Reefs of the World: 2020",
        "authors": "Souter et al. (GCRMN)", "year": 2021,
        "url": "https://gcrmn.net/wp-content/uploads/2023/01/Status-of-Coral-Reefs-of-the-World-2020-Full-Report.pdf",
        "supports": "以活硬珊瑚覆盖率与藻类覆盖率作为全球珊瑚礁状况的核心指标。",
        "limits": "覆盖率来自标准化样带或样方调查；斜视视频的画面像素占比不等于覆盖率。"},
    "BEIJBOM-2015": {
        "title": "Towards Automated Annotation of Benthic Survey Images: Variability of Human Experts and Operational Modes of Automation",
        "authors": "Beijbom et al.", "year": 2015,
        "url": "https://doi.org/10.1371/journal.pone.0130312",
        "supports": "底栖覆盖率常用随机点标注估计，并量化了专家之间的标注差异。",
        "limits": "基于俯拍样方图像；不能把模型像素占比直接当作点标注覆盖率。"},
    "HOTA-2021": {
        "title": "HOTA: A Higher Order Metric for Evaluating Multi-object Tracking",
        "authors": "Luiten et al.", "year": 2021,
        "url": "https://doi.org/10.1007/s11263-020-01375-2",
        "supports": "追踪质量需要人工身份真值，HOTA 同时衡量检测与关联。",
        "limits": "没有人工身份真值时无法计算；轨迹数不等于个体数。"},
}
