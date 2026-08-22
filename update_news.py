#!/usr/bin/env python3
"""Generate news.json from public RSS feeds. Intended for GitHub Actions or local scheduled tasks."""
import json, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

QUERIES = [
    ("供应链视角", "supply chain logistics port shipping procurement", "供应链"),
    ("供应链视角", "automotive supply chain China EV battery", "汽车供应链"),
    ("时尚视角", "fashion luxury retail supply chain", "时尚供应链"),
]

def google_news_rss(query):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"})
    req = urllib.request.Request(url, headers={"User-Agent":"BettyPersonalWorkbench/4.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return ET.fromstring(r.read())

def text(node, tag):
    x=node.find(tag)
    return (x.text or "").strip() if x is not None else ""

items=[]; seen=set()
for category, query, stage in QUERIES:
    try:
        root=google_news_rss(query)
        for it in root.findall("./channel/item")[:8]:
            title=text(it,"title"); link=text(it,"link"); pub=text(it,"pubDate"); source=text(it,"source") or "Google News"
            key=title.lower()
            if not title or key in seen: continue
            seen.add(key)
            items.append({"category":category,"date":pub[:16] if pub else datetime.now().strftime("%Y-%m-%d"),"source":source,"title":title,"summary":"公开RSS线索。阅读原文后，再在WorkBench里写下：发生了什么？影响哪个供应链环节？下一步看什么数据？","status":"待核验","stage":stage,"url":link})
    except Exception as e:
        print("RSS failed:", query, e)

# Keep a small fallback so the site never becomes empty.
if not items:
    items=[{"category":"供应链视角","date":datetime.now().strftime("%Y-%m-%d"),"source":"System","title":"今日RSS暂不可用","summary":"自动任务运行失败；请检查GitHub Actions日志。","status":"待核验","stage":"系统","url":"https://news.google.com/"}]

payload={"updatedAt":datetime.now(timezone.utc).astimezone().isoformat(timespec="minutes"),"items":items[:20]}
Path(__file__).resolve().parent.joinpath("news.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
print("Wrote",len(payload["items"]),"items")
