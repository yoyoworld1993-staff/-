"""Offline parser for text copied from Japanese listings or an iOS screenshot.

This module never makes network calls and never guesses auction ending time.
"""
import re
from urllib.parse import urlparse

URL = re.compile(r"https?://[^\s<>\u3000\"'，。；）)]+", re.I)
JPY = [
    re.compile(r"(?:[¥￥]\s*)?(\d[\d,]{0,11})\s*(?:日元|円|JPY)", re.I),
    re.compile(r"(?:現在価格|現價|现在价格|当前竞价|一口价|即決価格)\s*[:：]?\s*[¥￥]\s*(\d[\d,]{0,11})", re.I),
]

def parse_clipboard(text):
    text = str(text or "").strip()[:12000]
    urls = [x.rstrip(".,;，。；") for x in URL.findall(text)]
    url = urls[0] if urls else ""
    host = urlparse(url).hostname or ""
    platform = "其他"
    if "auctions.yahoo.co.jp" in host:
        platform = "Yahoo Auctions"
    elif "mercari.com" in host:
        platform = "Mercari 煤炉"
    elif "fril.jp" in host:
        platform = "Rakuma"
    elif "suruga-ya.jp" in host:
        platform = "Suruga-ya 骏河屋"
    elif "shopping.yahoo.co.jp" in host:
        platform = "Yahoo Shopping"
    elif "mandarake" in host:
        platform = "Mandarake"
    elif "meruki" in host:
        platform = "挖煤姬"
    bid = None
    for regex in JPY:
        m = regex.search(text)
        if m:
            try:
                bid = int(m.group(1).replace(",", ""))
                break
            except ValueError:
                pass
    lines = [x.strip(" \t\u3000") for x in text.splitlines() if x.strip()]
    title = ""
    for line in lines:
        if re.match(r"https?://", line):
            continue
        if "参考价" in line or "人民币" in line or line.startswith(("剩余时间", "出价次数", "日本国内")):
            continue
        if len(line) >= 8 and re.search(r"[a-zA-Z\u3040-\u30ff\u4e00-\u9fff]", line):
            title = line[:200]
            break
    kind = "一口价" if "一口价" in text or "即決のみ" in text else "拍卖"
    return {"title": title, "platform": platform, "kind": kind,
            "bid_jpy": bid, "url": url}
