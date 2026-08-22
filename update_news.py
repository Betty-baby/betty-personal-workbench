"""
Betty Personal Workbench V5
跨行业供应链情报自动抓取器

功能：
1. 从 Google News RSS 自动抓取供应链相关热点
2. 不限制具体行业
3. 覆盖汽车、科技、医疗、美妆、消费品、能源、食品、时尚等
4. 自动去重
5. 自动识别：
   - 行业
   - 供应链环节
   - 事件类型
6. 生成 news.json
7. 供 GitHub Actions 每日自动运行

注意：
当前版本不调用 AI API，不需要 API Key。
AI 自动摘要 / 影响分析将在后续版本加入。
"""

import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import re

from datetime import datetime, timezone
from pathlib import Path


# ============================================================
# 1. 新闻搜索主题
# ============================================================

QUERIES = [

    # --------------------------------------------------------
    # 核心供应链
    # --------------------------------------------------------

    (
        "供应链",
        "supply chain logistics procurement sourcing supplier",
        "跨行业"
    ),

    (
        "供应链风险",
        "supply chain disruption shortage risk resilience",
        "跨行业"
    ),

    (
        "供应链成本",
        "supply chain cost inflation freight transportation procurement",
        "跨行业"
    ),

    # --------------------------------------------------------
    # 全球贸易 / 地缘政治
    # --------------------------------------------------------

    (
        "全球贸易",
        "tariff trade war export import supply chain",
        "跨行业"
    ),

    (
        "地缘政治",
        "geopolitics supply chain trade sanctions manufacturing",
        "跨行业"
    ),

    # --------------------------------------------------------
    # 港口 / 航运 / 物流
    # --------------------------------------------------------

    (
        "物流",
        "shipping freight port container logistics supply chain",
        "物流"
    ),

    (
        "航运",
        "ocean shipping container rates port congestion supply chain",
        "物流"
    ),

    # --------------------------------------------------------
    # 制造 / 工厂 / 产能
    # --------------------------------------------------------

    (
        "制造",
        "manufacturing factory production capacity supply chain",
        "生产"
    ),

    (
        "生产布局",
        "manufacturing relocation reshoring nearshoring supply chain",
        "生产"
    ),

    # --------------------------------------------------------
    # 采购 / 供应商
    # --------------------------------------------------------

    (
        "采购",
        "procurement sourcing supplier supplier management",
        "采购"
    ),

    (
        "供应商",
        "supplier shortage supplier risk supplier diversification",
        "供应商"
    ),

    # --------------------------------------------------------
    # AI / 自动化 / 数字供应链
    # --------------------------------------------------------

    (
        "供应链科技",
        "AI supply chain automation warehouse robotics forecasting",
        "科技"
    ),

    (
        "仓储自动化",
        "warehouse automation robotics fulfillment logistics",
        "物流"
    ),

    # --------------------------------------------------------
    # 汽车
    # --------------------------------------------------------

    (
        "汽车",
        "automotive EV battery semiconductor supply chain",
        "汽车"
    ),

    # --------------------------------------------------------
    # 科技 / 半导体
    # --------------------------------------------------------

    (
        "科技",
        "semiconductor electronics hardware supply chain",
        "科技"
    ),

    (
        "半导体",
        "chip semiconductor manufacturing capacity supply chain",
        "科技"
    ),

    # --------------------------------------------------------
    # 医疗 / 制药
    # --------------------------------------------------------

    (
        "医疗",
        "healthcare medical device pharmaceutical supply chain",
        "医疗"
    ),

    (
        "制药",
        "pharmaceutical drug manufacturing supply chain shortage",
        "医疗"
    ),

    # --------------------------------------------------------
    # 美妆 / 消费品
    # --------------------------------------------------------

    (
        "美妆",
        "beauty cosmetics personal care supply chain sourcing",
        "美妆"
    ),

    (
        "消费品",
        "consumer goods FMCG retail supply chain",
        "消费品"
    ),

    # --------------------------------------------------------
    # 时尚 / 奢侈品
    # --------------------------------------------------------

    (
        "时尚",
        "fashion apparel luxury retail sourcing supply chain",
        "时尚"
    ),

    # --------------------------------------------------------
    # 食品 / 农业 / 冷链
    # --------------------------------------------------------

    (
        "食品",
        "food agriculture food supply chain shortage",
        "食品"
    ),

    (
        "冷链",
        "cold chain food logistics supply chain",
        "食品"
    ),

    # --------------------------------------------------------
    # 能源 / 电池 / 原材料
    # --------------------------------------------------------

    (
        "能源",
        "energy battery lithium critical minerals supply chain",
        "能源"
    ),

    (
        "原材料",
        "raw materials commodities shortage supplier supply chain",
        "原材料"
    ),

    # --------------------------------------------------------
    # 零售 / 电商
    # --------------------------------------------------------

    (
        "零售",
        "retail inventory demand forecasting supply chain",
        "零售"
    ),

    (
        "电商物流",
        "ecommerce fulfillment last mile logistics supply chain",
        "零售"
    ),
]


# ============================================================
# 2. Google News RSS
# ============================================================

def google_news_rss(query):

    url = (
        "https://news.google.com/rss/search?"
        + urllib.parse.urlencode(
            {
                "q": query,
                "hl": "en-US",
                "gl": "US",
                "ceid": "US:en",
            }
        )
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "BettyPersonalWorkbench/5.0"
        }
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return ET.fromstring(response.read())


# ============================================================
# 3. XML 文本读取
# ============================================================

def text(node, tag):

    element = node.find(tag)

    if element is not None and element.text:
        return element.text.strip()

    return ""


# ============================================================
# 4. 清理新闻标题
# ============================================================

def clean_title(title):

    if not title:
        return ""

    # Google News 有时会出现：
    # "Title - Reuters"
    # 这里暂时保留标题，不主动删除来源
    title = re.sub(r"\s+", " ", title)

    return title.strip()


# ============================================================
# 5. 日期处理
# ============================================================

def format_date(pub_date):

    if not pub_date:
        return datetime.now().strftime("%Y-%m-%d")

    try:

        from email.utils import parsedate_to_datetime

        dt = parsedate_to_datetime(pub_date)

        return dt.strftime("%Y-%m-%d")

    except Exception:

        return datetime.now().strftime("%Y-%m-%d")


# ============================================================
# 6. 根据关键词判断供应链环节
# ============================================================

def detect_supply_chain_stage(title, query_stage):

    text_value = title.lower()

    stages = []

    # 采购
    if any(
        keyword in text_value
        for keyword in [
            "procurement",
            "sourcing",
            "supplier",
            "vendor"
        ]
    ):
        stages.append("采购")

    # 生产
    if any(
        keyword in text_value
        for keyword in [
            "manufacturing",
            "factory",
            "production",
            "capacity",
            "plant"
        ]
    ):
        stages.append("生产")

    # 物流
    if any(
        keyword in text_value
        for keyword in [
            "logistics",
            "shipping",
            "freight",
            "port",
            "container",
            "warehouse",
            "transport"
        ]
    ):
        stages.append("物流")

    # 库存
    if any(
        keyword in text_value
        for keyword in [
            "inventory",
            "stock",
            "warehouse"
        ]
    ):
        stages.append("库存")

    # 需求
    if any(
        keyword in text_value
        for keyword in [
            "demand",
            "sales",
            "consumer",
            "retail"
        ]
    ):
        stages.append("需求")

    # 风险
    if any(
        keyword in text_value
        for keyword in [
            "risk",
            "disruption",
            "shortage",
            "crisis"
        ]
    ):
        stages.append("供应风险")

    # 贸易
    if any(
        keyword in text_value
        for keyword in [
            "tariff",
            "trade",
            "export",
            "import",
            "sanction"
        ]
    ):
        stages.append("贸易")

    # 如果没有识别出来
    if not stages:

        stages.append(query_stage)

    # 去重
    result = []

    for stage in stages:

        if stage not in result:
            result.append(stage)

    return result[:4]


# ============================================================
# 7. 判断事件类型
# ============================================================

def detect_event_type(title):

    text_value = title.lower()

    if any(
        keyword in text_value
        for keyword in [
            "tariff",
            "trade",
            "export",
            "import",
            "sanction"
        ]
    ):
        return "贸易政策"

    if any(
        keyword in text_value
        for keyword in [
            "shortage",
            "supply disruption",
            "disruption",
            "crisis"
        ]
    ):
        return "供应风险"

    if any(
        keyword in text_value
        for keyword in [
            "factory",
            "plant",
            "manufacturing",
            "production",
            "capacity"
        ]
    ):
        return "产能变化"

    if any(
        keyword in text_value
        for keyword in [
            "supplier",
            "procurement",
            "sourcing"
        ]
    ):
        return "采购 / 供应商"

    if any(
        keyword in text_value
        for keyword in [
            "shipping",
            "freight",
            "port",
            "container"
        ]
    ):
        return "物流运输"

    if any(
        keyword in text_value
        for keyword in [
            "warehouse",
            "robotics",
            "automation",
            "AI"
        ]
    ):
        return "供应链数字化"

    if any(
        keyword in text_value
        for keyword in [
            "inventory",
            "stock"
        ]
    ):
        return "库存变化"

    if any(
        keyword in text_value
        for keyword in [
            "demand",
            "sales",
            "retail"
        ]
    ):
        return "需求变化"

    return "行业动态"


# ============================================================
# 8. 生成“为什么值得关注”
# ============================================================

def generate_why_it_matters(event_type, stages):

    if event_type == "贸易政策":

        return (
            "贸易政策变化可能影响进口成本、供应商布局、"
            "生产区域和跨境物流，需要进一步关注关税、"
            "贸易量和供应商调整。"
        )

    if event_type == "供应风险":

        return (
            "供应中断或短缺可能影响生产连续性和交付能力，"
            "需要进一步关注库存、替代供应商和Lead Time。"
        )

    if event_type == "产能变化":

        return (
            "企业产能和生产布局变化可能意味着需求、成本或"
            "供应链区域化正在发生变化。"
        )

    if event_type == "采购 / 供应商":

        return (
            "供应商或采购策略变化可能影响采购成本、供应稳定性"
            "和供应商结构。"
        )

    if event_type == "物流运输":

        return (
            "运输和港口变化可能影响物流成本、Lead Time以及"
            "库存水平。"
        )

    if event_type == "供应链数字化":

        return (
            "AI、自动化和数字化可能改变供应链效率、预测能力"
            "和人工成本，值得关注企业ROI和落地规模。"
        )

    if event_type == "库存变化":

        return (
            "库存变化可能反映需求变化、供应不稳定或企业库存策略"
            "调整，需要结合销售和库存周转进一步判断。"
        )

    if event_type == "需求变化":

        return (
            "需求变化可能进一步影响生产计划、采购、库存和物流，"
            "需要结合销量、订单和库存数据观察。"
        )

    return (
        "该事件可能影响企业供应链布局，建议阅读原文后进一步判断"
        "其对采购、生产、库存、物流或需求的影响。"
    )


# ============================================================
# 9. 推荐进一步关注的指标
# ============================================================

def generate_watch_metrics(event_type):

    metrics = {

        "贸易政策": [
            "关税",
            "进口量",
            "出口量",
            "供应商区域分布",
            "物流成本"
        ],

        "供应风险": [
            "库存天数",
            "供应商数量",
            "Lead Time",
            "安全库存",
            "缺货率"
        ],

        "产能变化": [
            "产能利用率",
            "生产量",
            "资本开支",
            "供应商数量",
            "区域产能占比"
        ],

        "采购 / 供应商": [
            "采购价格",
            "供应商数量",
            "供应商集中度",
            "Lead Time",
            "采购成本"
        ],

        "物流运输": [
            "Freight Rate",
            "运输时间",
            "港口拥堵",
            "库存天数",
            "物流成本"
        ],

        "供应链数字化": [
            "自动化率",
            "人工成本",
            "订单处理时间",
            "预测准确率",
            "ROI"
        ],

        "库存变化": [
            "Inventory Days",
            "Inventory Turnover",
            "销售量",
            "缺货率",
            "库存金额"
        ],

        "需求变化": [
            "Sales",
            "Orders",
            "Forecast Accuracy",
            "Inventory Days",
            "Demand Growth"
        ],

        "行业动态": [
            "价格",
            "需求",
            "产能",
            "库存",
            "供应商变化"
        ]
    }

    return metrics.get(
        event_type,
        metrics["行业动态"]
    )


# ============================================================
# 10. 主程序
# ============================================================

items = []
seen = set()


for category, query, default_stage in QUERIES:

    print(f"Fetching: {category} -> {query}")

    try:

        root = google_news_rss(query)

        rss_items = root.findall("./channel/item")

        # 每个搜索主题最多抓 6 条
        for item in rss_items[:6]:

            title = clean_title(
                text(item, "title")
            )

            link = text(item, "link")

            pub = text(item, "pubDate")

            source = (
                text(item, "source")
                or "Google News"
            )

            if not title:
                continue

            # ------------------------------------------------
            # 去重
            # ------------------------------------------------

            key = re.sub(
                r"[^a-z0-9\u4e00-\u9fff]+",
                "",
                title.lower()
            )

            if not key:
                continue

            if key in seen:
                continue

            seen.add(key)

            # ------------------------------------------------
            # 自动分析
            # ------------------------------------------------

            stages = detect_supply_chain_stage(
                title,
                default_stage
            )

            event_type = detect_event_type(
                title
            )

            why_it_matters = generate_why_it_matters(
                event_type,
                stages
            )

            watch_metrics = generate_watch_metrics(
                event_type
            )

            # ------------------------------------------------
            # 写入 JSON
            # ------------------------------------------------

            items.append(

                {
                    "category": "供应链情报",

                    "industry": category,

                    "date": format_date(pub),

                    "source": source,

                    "title": title,

                    "summary": (
                        "公开RSS新闻线索。"
                        "建议阅读原文后进行进一步分析。"
                    ),

                    "supply_chain_stage": stages,

                    "event_type": event_type,

                    "why_it_matters": why_it_matters,

                    "watch_metrics": watch_metrics,

                    "status": "AI初筛",

                    "url": link
                }
            )

    except Exception as error:

        print(
            f"RSS failed: {category}",
            error
        )


# ============================================================
# 11. 如果全部 RSS 失败，保留 fallback
# ============================================================

if not items:

    items = [

        {
            "category": "供应链情报",

            "industry": "系统",

            "date": datetime.now().strftime(
                "%Y-%m-%d"
            ),

            "source": "System",

            "title": "今日RSS暂不可用",

            "summary": (
                "自动任务运行失败；"
                "请检查GitHub Actions日志。"
            ),

            "supply_chain_stage": [
                "系统"
            ],

            "event_type": "系统异常",

            "why_it_matters": (
                "新闻抓取任务未成功运行。"
            ),

            "watch_metrics": [],

            "status": "待检查",

            "url": "https://news.google.com/"
        }

    ]


# ============================================================
# 12. 生成 news.json
# ============================================================

payload = {

    "updatedAt": (
        datetime.now(timezone.utc)
        .astimezone()
        .isoformat(
            timespec="minutes"
        )
    ),

    "items": items[:50]
}


output_path = (
    Path(__file__)
    .resolve()
    .parent
    .joinpath("news.json")
)


output_path.write_text(

    json.dumps(
        payload,
        ensure_ascii=False,
        indent=2
    ),

    encoding="utf-8"
)


print(
    f"Wrote {len(payload['items'])} items"
)

print(
    f"Output: {output_path}"
)
