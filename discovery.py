"""Free on-demand search of publicly viewable HTML and optional official API.

No login automation, hidden endpoints, CAPTCHA bypass, or background polling.
Fail closed on robots restrictions. All amounts are unverified listing prices.
"""
import os
import re
from datetime import datetime
from urllib.parse import urlencode, urljoin, urlparse
from urllib.robotparser import RobotFileParser
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

UA = "ZhongguLieshou/0.5 (+https://github.com/yoyoworld1993-staff/-)"
HEADERS = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"}
LIMIT = 18
TIMEOUT = 9
ZONE = ZoneInfo("Asia/Shanghai")
HOSTS = {"mercari": "jp.mercari.com", "auction": "auctions.yahoo.co.jp"}


def result(source, status, reason, url, products=None):
    return {
        "source": source, "status": status, "reason": reason,
        "search_url": url, "products": products or [],
        "observed_at": datetime.now(ZONE).strftime("%Y-%m-%d %H:%M:%S"),
    }


def allowed_link(raw, hostname):
    try:
        u = urlparse(raw)
        if u.scheme != "https" or u.hostname != hostname or u.username or u.password:
            return ""
        return u.geturl()
    except (TypeError, ValueError):
        return ""


def robot_check(url):
    p = urlparse(url)
    robot_url = p.scheme + "://" + p.hostname + "/robots.txt"
    try:
        response = requests.get(robot_url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=False)
        if response.status_code == 404:
            return True, "robots.txt 返回 404"
        if response.status_code != 200 or len(response.content) > 1000000:
            return False, "robots.txt 无法核验（HTTP {}）".format(response.status_code)
        rp = RobotFileParser()
        rp.parse(response.text.splitlines())
        return rp.can_fetch(UA, url), "已核验 robots.txt"
    except requests.RequestException:
        return False, "无法读取 robots.txt"


def html_search(url, source, parser):
    ok, msg = robot_check(url)
    if not ok:
        return result(source, "blocked", "自动读取未获确认：" + msg, url)
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=False)
        if response.status_code != 200:
            return result(source, "unavailable", "商品页 HTTP {}".format(response.status_code), url)
        if len(response.content) > 3000000:
            return result(source, "unavailable", "商品页面超过大小限制", url)
        items = parser(response.text)
        if not items:
            return result(source, "unavailable", "页面没有识别到商品与价格；可能为动态页面或页面结构变化", url)
        return result(source, "ok", "找到 {} 件候选商品。价格为页面报价，未核实库存与品相".format(len(items)), url, items)
    except requests.RequestException as exc:
        return result(source, "unavailable", "网络请求失败：" + str(exc)[:130], url)


PRICE = re.compile(r"(?:現在\s*)?[¥￥]\s*([0-9][0-9,]{0,9})")
YEN = re.compile(r"([0-9][0-9,]{0,9})\s*円")


def extract_price(text):
    m = PRICE.search(text) or YEN.search(text)
    return int(m.group(1).replace(",", "")) if m else None


def parse_mercari_html(source_html):
    soup = BeautifulSoup(source_html, "html.parser")
    found = []
    seen = set()
    for anchor in soup.select('a[href*="/item/"]'):
        url = urljoin("https://jp.mercari.com", anchor.get("href", ""))
        url = allowed_link(url, HOSTS["mercari"])
        if not url:
            continue
        item_id = urlparse(url).path.strip("/").split("/")[-1]
        if not re.fullmatch(r"m[0-9]{7,}", item_id) or item_id in seen:
            continue
        text = anchor.get_text(" ", strip=True)
        card = anchor.find_parent(attrs={"data-testid": "item-cell"})
        if card is None:
            card = anchor.find_parent("li") or anchor
        card_text = card.get_text(" ", strip=True)
        price = extract_price(text) or extract_price(card_text)
        if price is None:
            continue
        title = PRICE.sub("", text).strip()
        title = YEN.sub("", title).strip()
        if not title:
            img = anchor.find("img")
            title = (img.get("alt", "") if img else "").strip()
        if not title:
            title = PRICE.sub("", card_text).strip()
        if not title:
            continue
        seen.add(item_id)
        auction_hint = "現在" in text or "現在" in card_text[:25]
        found.append({
            "id": item_id, "title": title[:220], "platform": "Mercari 煤炉",
            "url": url, "price_jpy": price,
            "kind": "拍卖" if auction_hint else "一口价",
            "end_at": "", "time_status": "未提供截拍时间" if auction_hint else "不适用",
            "evidence": "公开搜索页显示的报价，非成交价",
        })
        if len(found) >= LIMIT:
            break
    return found


def parse_yahoo_html(source_html):
    soup = BeautifulSoup(source_html, "html.parser")
    found = []
    seen = set()
    for card in soup.select(".Product"):
        a = card.select_one("a.Product__titleLink") or card.select_one('a[href*="/jp/auction/"]')
        if not a:
            continue
        raw = urljoin("https://auctions.yahoo.co.jp", a.get("href", ""))
        url = allowed_link(raw, HOSTS["auction"])
        if not url or url in seen:
            continue
        price_el = card.select_one(".Product__priceInfo .Product__price") or card.select_one(".Product__price")
        price = extract_price(price_el.get_text(" ", strip=True)) if price_el else None
        title = a.get("title") or a.get_text(" ", strip=True)
        if not title or price is None:
            continue
        found.append({
            "id": urlparse(url).path.rsplit("/", 1)[-1],
            "title": title[:220], "platform": "Yahoo Auctions",
            "url": url, "price_jpy": price, "kind": "拍卖", "end_at": "",
            "time_status": "结束时间未核验", "evidence": "公开搜索页报价，非最终成交价",
        })
        seen.add(url)
        if len(found) >= LIMIT:
            break
    return found


def mercari_search(keyword):
    url = "https://jp.mercari.com/search?" + urlencode({"keyword": keyword, "status": "on_sale"})
    return html_search(url, "Mercari 煤炉", parse_mercari_html)


def auction_search(keyword):
    url = "https://auctions.yahoo.co.jp/search/search?" + urlencode({
        "p": keyword, "s1": "end", "o1": "a", "n": 30,
    })
    return html_search(url, "Yahoo Auctions", parse_yahoo_html)


def shopping_search(keyword):
    url = "https://shopping.yahoo.co.jp/search?" + urlencode({"p": keyword})
    app_id = os.getenv("YAHOO_SHOPPING_APP_ID", "").strip()
    if not app_id:
        return result("Yahoo Shopping", "needs_key", "官方 API 需要自行申请 Client ID；目前未配置", url)
    try:
        response = requests.get(
            "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch",
            params={"appid": app_id, "query": keyword, "results": LIMIT,
                    "condition": "used", "in_stock": "true"},
            headers={"User-Agent": UA, "Accept": "application/json"},
            timeout=TIMEOUT, allow_redirects=False,
        )
        if response.status_code != 200:
            return result("Yahoo Shopping", "unavailable", "官方 API HTTP {}".format(response.status_code), url)
        hits = response.json().get("hits", [])
        found = []
        for h in hits[:LIMIT]:
            name = str(h.get("name") or "").strip()
            link = h.get("url", "")
            p = h.get("price")
            if not name or not isinstance(p, (int, float)) or p < 0:
                continue
            try:
                host = urlparse(link).hostname
            except ValueError:
                host = None
            if host not in ("store.shopping.yahoo.co.jp", "shopping.yahoo.co.jp"):
                continue
            link = allowed_link(link, host)
            if not link:
                continue
            found.append({
                "id": str(h.get("code", "")), "title": name[:220],
                "platform": "Yahoo Shopping", "url": link, "price_jpy": int(p),
                "kind": "一口价", "end_at": "", "time_status": "不适用",
                "evidence": "官方商品搜索 API 报价，库存需核实",
            })
        return result("Yahoo Shopping", "ok", "官方 API 找到 {} 件商品".format(len(found)), url, found)
    except (ValueError, requests.RequestException) as exc:
        return result("Yahoo Shopping", "unavailable", "官方 API 失败：" + str(exc)[:130], url)


def search_all(keyword):
    keyword = keyword.strip()
    if not 2 <= len(keyword) <= 60:
        raise ValueError("请输入 2–60 字关键词")
    return [mercari_search(keyword), auction_search(keyword), shopping_search(keyword)]
