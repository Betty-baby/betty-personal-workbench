"""
Betty Personal Workbench V5
Generate news.json from public Google News RSS feeds.

定位：
不是单一行业新闻，而是「供应链视角的全球商业情报」。

覆盖：
- 全球供应链 / 物流 / 航运 / 港口
- 科技 / AI / 半导体 / 数据中心
- 汽车 / EV / 电池
- 医疗 / 制药 / 医疗器械
- 美妆 / 消费品 / 零售
- 能源 / 原材料 / 关键矿产
- 制造业 / 采购 / 贸易 / 关税
- 其他值得从供应链角度观察的热点

适用于 GitHub Actions 每日自动运行。
"""

import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from email.utils import parsedate_to_datetime


# ============================================================
# 1. 新闻搜索主题
# ============================================================

QUERIES = [

    # --------------------------------------------------------
    # 核心供应链
    # --------------------------------------------------------
    (
        "供应链",
        "supply chain disruption logistics procurement manufacturing",
        "供应链"
    ),

    (
        "物流与航运",
        "shipping logistics freight ports container supply chain",
        "物流"
    ),

    (
        "全球贸易",
        "trade tariffs export restrictions import supply chain",
        "贸易"
    ),

    # --------------------------------------------------------
    # 科技 / AI / 半导体
    # --------------------------------------------------------
    (
        "科技供应链",
        "AI data center semiconductor chip supply chain manufacturing",
        "科技"
    ),

    (
        "半导体",
        "semiconductor chip shortage manufacturing equipment materials supply chain",
        "半导体"
    ),

    (
        "AI基础设施",
        "AI data centers GPUs servers power cooling supply chain",
        "AI基础设施"
    ),

    # --------------------------------------------------------
    # 汽车 / EV / 电池
    # --------------------------------------------------------
    (
        "汽车供应链",
        "automotive EV battery electric vehicle supply chain manufacturing",
        "汽车供应链"
    ),

    (
        "电池与材料",
        "battery lithium nickel graphite critical minerals supply chain",
        "电池与原材料"
    ),

    # --------------------------------------------------------
    # 医疗 / 制药
    # --------------------------------------------------------
    (
        "医疗供应链",
        "pharmaceutical medical device healthcare supply chain shortage manufacturing",
        "医疗"
    ),

    (
        "制药",
        "pharmaceutical drug manufacturing API medicine supply chain",
        "制药"
    ),

    # --------------------------------------------------------
    # 美妆 / 消费品 / 零售
    # --------------------------------------------------------
    (
        "美妆供应链",
        "beauty cosmetics skincare personal care supply chain manufacturing ingredients packaging",
        "美妆"
    ),

    (
        "消费品",
        "consumer goods retail inventory sourcing manufacturing supply chain",
        "消费品"
    ),

    # --------------------------------------------------------
    # 能源 / 原材料
    # --------------------------------------------------------
    (
        "能源供应链",
        "energy oil gas LNG electricity power supply chain",
        "能源"
    ),

    (
        "原材料",
        "raw materials commodities metals minerals supply chain",
        "原材料"
    ),

    # --------------------------------------------------------
    # 制造业
    # --------------------------------------------------------
    (
        "制造业",
        "manufacturing factory production capacity reshoring supply chain",
        "生产与产能"
    ),
]


# ============================================================
# 2. Google News RSS
# ============================================================

def google_news_rss(query):

    # 重点：
    # when:7d 尽量限制在最近 7 天
    # 避免再次出现几个月以前的旧文章

    query_with_time = f"{query} when:7d"

    params = {
        "q": query_with_time,
        "hl": "en-US",
        "gl": "US",
        "ceid": "US:en",
    }

    url = (
        "https://news.google.com/rss/search?"
        + urllib.parse.urlencode(params)
    )

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "BettyPersonalWorkbench/5.0"
        }
    )

    with urllib.request.urlopen(req, timeout=20) as response:
        return ET.fromstring(response.read())


# ============================================================
# 3. XML 工具
# ============================================================

def text(node, tag):

    x = node.find(tag)

    if x is not None and x.text:
        return x.text.strip()

    return ""


# ============================================================
# 4. 日期处理
# ============================================================

def parse_date(pub_date):

    if not pub_date:
        return datetime.now(timezone.utc)

    try:
        return parsedate_to_datetime(pub_date).astimezone(timezone.utc)

    except Exception:
        return datetime.now(timezone.utc)


# ============================================================
# 5. 开始抓新闻
# ============================================================

items = []
seen = set()

now = datetime.now(timezone.utc)


for category, query, stage in QUERIES:

    try:

        root = google_news_rss(query)

        rss_items = root.findall("./channel/item")

        # 每个主题最多取 6 条
        for item in rss_items[:6]:

            title = text(item, "title")
            link = text(item, "link")
            pub = text(item, "pubDate")
            source = text(item, "source") or "Google News"

            if not title:
                continue

            # ------------------------------------------------
            # 去重
            # ------------------------------------------------

            key = title.lower().strip()

            if key in seen:
                continue

            seen.add(key)

            # ------------------------------------------------
            # 日期
            # ------------------------------------------------

            published_at = parse_date(pub)

            # ------------------------------------------------
            # 过滤太旧的新闻
            # ------------------------------------------------

            age_days = (
                now - published_at
            ).total_seconds() / 86400

            if age_days > 8:
                continue

            # ------------------------------------------------
            # 新闻对象
            # ------------------------------------------------

            items.append({

                "category": category,

                "date": published_at.strftime(
                    "%Y-%m-%d"
                ),

                "source": source,

                "title": title,

                "summary": (
                    "公开RSS线索。阅读原文后，在WorkBench中记录："
                    "发生了什么？为什么现在发生？"
                    "影响哪个供应链环节？"
                    "谁可能受益或承压？"
                    "下一步应该观察什么数据？"
                ),

                "status": "待核验",

                "stage": stage,

                "url": link,

                # 给前端排序使用
                "publishedAt": published_at.isoformat(),

            })

    except Exception as e:

        print(
            "RSS failed:",
            query,
            e
        )


# ============================================================
# 6. 按最新时间排序
# ============================================================

items.sort(
    key=lambda x: x.get("publishedAt", ""),
    reverse=True
)


# ============================================================
# 7. 如果 RSS 全部失败
# ============================================================

if not items:

    items = [

        {

            "category": "系统",

            "date": datetime.now().strftime(
                "%Y-%m-%d"
            ),

            "source": "System",

            "title": "今日RSS暂不可用",

            "summary": (
                "自动任务已经运行，但暂时没有获取到新闻。"
                "请检查 GitHub Actions 日志。"
            ),

            "status": "待处理",

            "stage": "系统",

            "url": "https://news.google.com/",

            "publishedAt": datetime.now(
                timezone.utc
            ).isoformat(),

        }

    ]


# ============================================================
# 8. 最多保留 20 条
# ============================================================

items = items[:20]


# ============================================================
# 9. 写入 news.json
# ============================================================

payload = {

    "updatedAt": datetime.now(
        timezone.utc
    ).astimezone().isoformat(
        timespec="minutes"
    ),

    "items": items

}


output_path = (
    Path(__file__).resolve().parent
    / "news.json"
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
    "Wrote",
    len(items),
    "items"
)
