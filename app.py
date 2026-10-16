import csv
import html
import io
from datetime import datetime, timedelta
from urllib.parse import urlparse
from uuid import uuid4
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from core import calculate
from intake import parse_clipboard
from discovery import search_all, auction_search, mercari_search

TZ = ZoneInfo("Asia/Shanghai")
PLATFORMS = [
    "Yahoo Auctions", "Mercari 煤炉", "Rakuma", "Yahoo Flea Market",
    "Suruga-ya 骏河屋", "Mandarake", "Yahoo Shopping", "挖煤姬", "其他"
]
SITES = [
    ("Yahoo! Auctions", "https://auctions.yahoo.co.jp/", "拍卖 · 临近截拍"),
    ("Mercari 煤炉", "https://jp.mercari.com/", "二手 · 一口价"),
    ("Rakuma", "https://fril.jp/", "二手 · 一口价"),
    ("Yahoo! フリマ", "https://paypayfleamarket.yahoo.co.jp/", "二手 · 一口价"),
    ("骏河屋", "https://www.suruga-ya.jp/", "中古模型 · 店铺"),
    ("Mandarake", "https://order.mandarake.co.jp/", "玩具收藏"),
    ("Yahoo! Shopping", "https://shopping.yahoo.co.jp/", "店铺价格参考"),
]
st.set_page_config(page_title="中古猎手｜日本模型雷达", page_icon="🚗", layout="centered")
st.markdown("""
<style>
.block-container {padding-top:1.0rem;max-width:760px}
h1 {font-size:1.65rem!important;letter-spacing:-.03em}
[data-testid="stTabs"] button {font-size:.92rem}
div[data-testid="stVerticalBlockBorderWrapper"] {border-radius:17px}
div[data-testid="stMetricValue"] {font-size:1.45rem}
.smallmuted {color:#929cab;font-size:.84rem}
.hero {border:1px solid rgba(150,150,150,.22);border-radius:18px;padding:16px;background:linear-gradient(115deg,rgba(42,110,99,.18),rgba(120,105,39,.10))}
.pills {display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.pill {border:1px solid rgba(155,155,155,.3);border-radius:999px;padding:5px 10px;font-size:.78rem}
.priceline {font-size:1.12rem;font-weight:750;letter-spacing:-.015em}
.profitgood {color:#27ba8c;font-weight:750}
.profitbad {color:#e98585;font-weight:750}
</style>
""", unsafe_allow_html=True)

def now():
    return datetime.now(TZ)

def safe(s):
    return html.escape(str(s), quote=True)

def valid_url(raw):
    if not raw:
        return ""
    u = urlparse(str(raw).strip())
    if u.scheme not in ("http", "https") or not u.netloc or u.username or u.password:
        raise ValueError("请输入有效的 http/https 商品网址")
    return u.geturl()

def parse_end(s):
    if not s or not str(s).strip():
        return None
    return datetime.strptime(str(s).strip(), "%Y-%m-%d %H:%M").replace(tzinfo=TZ)

def record(title, platform, kind, price, sale, end_at="", url="", demo=False, allow_unknown_end=False):
    if not str(title).strip():
        raise ValueError("请输入商品型号或标题")
    price, sale = float(price), float(sale)
    if not (0 <= price <= 100000000 and 0 <= sale <= 100000000):
        raise ValueError("商品价格必须是有效的非负数")
    end = parse_end(end_at)
    if kind == "拍卖" and end is None and not allow_unknown_end:
        raise ValueError("拍卖商品请填写预计结束时间")
    return dict(
        id=uuid4().hex[:12], title=str(title).strip(), platform=str(platform),
        kind=kind, bid_jpy=price, sale_cny=sale,
        end_at=end_at if kind == "拍卖" else "", url=valid_url(url),
        demo=demo, history=[{"at":now().strftime("%Y-%m-%d %H:%M:%S"), "bid_jpy":price}],
    )

if "records" not in st.session_state:
    st.session_state["records"] = []
if "settings" not in st.session_state:
    st.session_state["settings"] = {
        "fx": 0.044, "ship_jpy": 0, "fee": 5.0, "ship_cny": 45.0,
        "discount": 10.0, "reserve": 15.0, "target": 50.0, "roi": 20.0,
    }
settings = st.session_state["settings"]

@st.cache_data(ttl=120)
def demo_data():
    base = now()
    examples = [
        ("Tomica Limited Vintage Skyline R32", "Yahoo Auctions", "拍卖", 2400, 350, 4),
        ("京商 Ferrari F40 1:64", "Mercari 煤炉", "一口价", 1800, 250, None),
        ("TLV Nissan 1:64 稀有涂装", "Yahoo Auctions", "拍卖", 7300, 490, 38),
    ]
    rows = []
    for title, platform, kind, bid, sale, minute in examples:
        end = (base + timedelta(minutes=minute)).strftime("%Y-%m-%d %H:%M") if minute else ""
        rows.append(record(title, platform, kind, bid, sale, end, demo=True))
    return rows

def evaluate(r):
    cost, profit, cap = calculate(
        r["bid_jpy"], settings["fx"], settings["ship_jpy"], settings["fee"],
        settings["ship_cny"], r["sale_cny"], settings["discount"], settings["reserve"],
        settings["target"],
    )
    roi = profit / cost * 100 if cost > 0 else 0.0
    end = parse_end(r.get("end_at", ""))
    mins = ((end - now()).total_seconds() / 60) if end else None
    urgent = r["kind"] == "拍卖" and mins is not None and 0 <= mins <= 5
    eligible = r["sale_cny"] > 0 and profit >= settings["target"] and roi >= settings["roi"]
    score = max(-100, min(100, profit / max(settings["target"], 1) * 35)) + max(-100, min(100, roi / max(settings["roi"], 1) * 35))
    score += 18 if urgent else 0
    return dict(cost=cost, profit=profit, cap=cap, roi=roi, mins=mins, urgent=urgent, eligible=eligible, score=score)

def time_label(r, info):
    if r["kind"] == "一口价":
        return "🏷 一口价"
    m = info["mins"]
    if m is None:
        return "结束时间未知"
    if m < 0:
        return "已过预计结束时间"
    if m <= 5:
        return "🔥 最后 {:.1f} 分钟".format(m)
    if m < 60:
        return "⏱ 还有 {:.0f} 分钟".format(m)
    return "⏱ 还有 {:.1f} 小时".format(m / 60)

def show_card(r):
    info = evaluate(r)
    with st.container(border=True):
        if r.get("demo"):
            st.caption("🧪 模拟数据 · 非真实商品报价")
        st.markdown("**{}**".format(safe(r["title"])), unsafe_allow_html=True)
        st.caption("{} · {}".format(r["platform"], time_label(r, info)))
        c1, c2 = st.columns(2)
        c1.metric("日本当前价格", "¥{:,.0f} 日元".format(r["bid_jpy"]))
        c2.metric("预计净利润", "{:+,.0f} 元".format(info["profit"]) if r["sale_cny"] > 0 else "待估价")
        st.markdown(
            "<div class='smallmuted'>到手成本 ¥{:,.0f} · {} </div>".format(
                info["cost"], "利润率 {:.1f}% · 最高竞拍价 {:,} 日元".format(info["roi"], info["cap"]) if r["sale_cny"] > 0 else "闲鱼估价缺失 · 尚无法计算合理最高出价"
            ), unsafe_allow_html=True
        )
        if r["sale_cny"] <= 0:
            st.warning("尚未填写闲鱼估价，无法判断利润或最高出价")
        elif info["eligible"]:
            st.success("达到预设净利润和利润率门槛", icon="✅")
        else:
            st.caption("未同时满足预设净利润和利润率门槛")
        if info["cap"] < r["bid_jpy"] and r["kind"] == "拍卖":
            st.warning("当前竞价已超过你的最高可接受出价")
        if r.get("url"):
            st.link_button("打开原商品 ↗", r["url"], use_container_width=True)

st.markdown("<div class='hero'><div style='font-size:1.55rem;font-weight:800'>🚗 中古猎手</div>"
            "<div class='smallmuted'>日本小车模型 · 5 分钟截拍雷达 · 倒推最高出价</div>"
            "<div class='pills'><span class='pill'>Yahoo 拍卖</span><span class='pill'>Mercari 煤炉</span>"
            "<span class='pill'>闲鱼利润测算</span></div></div>", unsafe_allow_html=True)
st.caption("⚠️ 当前为试用原型：尚无日本平台实时采集，竞价和闲鱼售价需手动填入。")

source_tab, radar_tab, add_tab, manage_tab, config_tab = st.tabs(
    ["🔎 找货", "🎯 雷达", "➕ 录入", "📦 我的货", "⚙️ 设置"]
)

with radar_tab:
    own = st.session_state["records"]
    if not own:
        st.warning("当前还没有真实商品。请先到「找货」打开免费跨站搜索，再把商品复制到雷达。")
        st.link_button("🔎 立即到 JPSearch 找真实日本货 ↗", "https://jpsearch.moe/", use_container_width=True)
    all_rows = list(own)
    if all_rows:
        evaluated = [(r, evaluate(r)) for r in all_rows]
        close = sum(1 for _, v in evaluated if v["urgent"])
        viable = sum(1 for _, v in evaluated if v["eligible"])
        st.markdown("<div class='pills'><span class='pill'>监控 {} 件</span><span class='pill'>最后5分钟 {} 件</span><span class='pill'>利润达标 {} 件</span></div>".format(
            len(all_rows), close, viable), unsafe_allow_html=True)
        filter_choice = st.selectbox("快速筛选", ["全部商品", "最后 5 分钟", "有利润的机会", "仅我的真实商品"], label_visibility="collapsed")
        order = st.selectbox("排序", ["综合机会优先", "即将截拍优先", "净利润最高", "日本价格最低"])
        filtered = []
        for r, v in evaluated:
            if filter_choice == "最后 5 分钟" and not v["urgent"]:
                continue
            if filter_choice == "有利润的机会" and not v["eligible"]:
                continue
            if filter_choice == "仅我的真实商品" and r.get("demo"):
                continue
            filtered.append((r, v))
        if order == "综合机会优先":
            filtered.sort(key=lambda rv: rv[1]["score"], reverse=True)
        elif order == "即将截拍优先":
            filtered.sort(key=lambda rv: rv[1]["mins"] if rv[1]["mins"] is not None and rv[1]["mins"] >= 0 else 1e12)
        elif order == "净利润最高":
            filtered.sort(key=lambda rv: rv[1]["profit"], reverse=True)
        else:
            filtered.sort(key=lambda rv: rv[0]["bid_jpy"])
        if not filtered:
            st.info("当前筛选条件下没有商品。")
        for r, _ in filtered:
            show_card(r)
        st.caption("当前收藏数据只在这次会话中保存，请在「我的货」导出备份。剩余时间依据输入的预计截拍时间，不代表实时竞价。")
    else:
        st.info("目前没有已收藏商品。切换到「找货」，复制真实商品的标题与价格，加入雷达后这里才会显示。")

with source_tab:
    st.subheader("🌏 真正找日本货 · 免费方案")
    st.caption("已有平台负责跨站搜索，我们负责收藏、成本和竞拍利润。不是空白爬虫，也不会伪造商品。")
    searchword = st.text_input("小车关键词（日文更容易找到）", value="トミカ", help="例如 トミカ / TLV / 京商 / ミニカー / 1/18")
    st.code(searchword, language=None)
    st.caption("可复制上方关键词，在打开的网站里搜索。")
    st.link_button("⭐ JPSearch｜Yahoo、煤炉等 8 个平台一站搜索 ↗", "https://jpsearch.moe/", use_container_width=True, type="primary")
    st.link_button("ZenMarket 中文跨平台搜索 ↗", "https://zenmarket.jp/cn/", use_container_width=True)
    st.caption("JPSearch 免费版每天约 3 次搜索、通知约每 12 小时检查一次；不是 5 分钟实时监控。不要求在本软件中付费。")

    from urllib.parse import urlencode
    q = searchword.strip() or "トミカ"
    st.markdown("**想直接盯最后 5 分钟？打开日本原站：**")
    st.link_button("⏱ Yahoo 拍卖｜按结束时间由近到远 ↗",
                   "https://auctions.yahoo.co.jp/search/search?" + urlencode({"p": q, "s1": "end", "o1": "a"}),
                   use_container_width=True)
    st.link_button("Mercari 煤炉｜搜索同款 ↗",
                   "https://jp.mercari.com/search?" + urlencode({"keyword": q}), use_container_width=True)
    with st.expander("更多日本货源网站"):
        st.link_button("Rakuma ↗", "https://fril.jp/", use_container_width=True)
        st.link_button("骏河屋 ↗", "https://www.suruga-ya.jp/", use_container_width=True)
        st.link_button("Mandarake ↗", "https://order.mandarake.co.jp/", use_container_width=True)
    st.divider()
    st.subheader("📋 查到商品后，快速加入雷达")
    st.caption("从日本商品页面复制标题、日元价格和链接；粘贴到下面，软件会尝试识别。无需手动逐项输入。")
    clip = st.text_area("粘贴商品文字或分享内容", placeholder="KK scale 1/18 Pontiac LeMans GTO 1972\n15,500日元（参考价：682人民币）\nhttps://...", height=120, key="clip_search")
    guess = parse_clipboard(clip)
    with st.form("import_from_clipboard"):
        inferred_title = st.text_input("商品型号（可修改）", value=guess["title"], placeholder="请确认商品名称和版本")
        inferred_price = st.number_input("日本报价（日元）", min_value=0, value=int(guess["bid_jpy"] or 0), step=100)
        platform_index = PLATFORMS.index(guess["platform"]) if guess["platform"] in PLATFORMS else 0
        inferred_platform = st.selectbox("货源平台", PLATFORMS, index=platform_index)
        inferred_kind = st.selectbox("拍卖 / 一口价", ["拍卖", "一口价"], index=1 if guess["kind"] == "一口价" else 0)
        inferred_end = st.text_input("预计截拍时间（北京时间，可空）", placeholder="2026-10-17 22:30；没有可靠截拍时间可不填")
        inferred_sale = st.number_input("闲鱼保守售价（人民币，可稍后补）", min_value=0.0, value=0.0, step=10.0)
        inferred_link = st.text_input("原商品链接（可空）", value=guess["url"])
        if st.form_submit_button("✅ 加入我的雷达", type="primary", use_container_width=True):
            try:
                if not inferred_price:
                    raise ValueError("必须填写日本报价后才能保存")
                product = record(inferred_title, inferred_platform, inferred_kind,
                                 inferred_price, inferred_sale, inferred_end, inferred_link,
                                 allow_unknown_end=True)
                product["source_status"] = "你粘贴的真实商品线索，报价需在原站核对"
                if product["url"] and any(old.get("url") == product["url"] for old in st.session_state["records"]):
                    st.info("这件商品已经收藏过了。")
                else:
                    st.session_state["records"].append(product)
                    st.success("已加入「雷达」！现在可以监控预计截拍、编辑售价和竞价。")
            except (ValueError, TypeError) as e:
                st.error(str(e))
    st.caption("商品信息来自你复制的页面，不等于最新成交价。雷达不自动更新外站竞价。")


with add_tab:
    st.subheader("添加关注商品")
    st.caption("复制日本原商品标题与价格，填入即可计算利润。")
    with st.form("add_product", clear_on_submit=True):
        title = st.text_input("商品名称 / 型号 *", placeholder="例如 Tomica Limited Vintage R32")
        platform = st.selectbox("来源平台", PLATFORMS)
        kind = st.selectbox("交易方式", ["拍卖", "一口价"])
        bid = st.number_input("当前竞价 / 一口价（日元）", min_value=0, value=2000, step=100)
        sale = st.number_input("闲鱼预计挂牌价（人民币）", min_value=0.0, value=300.0, step=10.0)
        end_str = st.text_input("预计结束时间（北京时间）", placeholder="2026-10-17 22:30；一口价可留空")
        url = st.text_input("原商品链接（可选）", placeholder="https://")
        submitted = st.form_submit_button("保存并加入雷达", use_container_width=True, type="primary")
        if submitted:
            try:
                r = record(title, platform, kind, bid, sale, end_str, url)
                st.session_state["records"].append(r)
                st.success("已加入雷达。切换到「雷达」或「我的货」查看。")
            except ValueError as e:
                st.error(str(e))
    st.divider()
    st.subheader("CSV 批量导入")
    example = "商品,平台,类型,链接,日元价格,闲鱼售价,结束时间\nTomica测试,Yahoo Auctions,拍卖,,1000,200,2026-10-17 22:30\n"
    st.download_button("下载 CSV 模板", example.encode("utf-8-sig"), "中古猎手_导入模板.csv", "text/csv", use_container_width=True)
    uploaded = st.file_uploader("选择 CSV 文件", type=["csv"])
    if uploaded is not None and st.button("验证并导入", use_container_width=True):
        try:
            df = pd.read_csv(uploaded, dtype=str).fillna("")
            required = {"商品", "平台", "类型", "日元价格", "闲鱼售价"}
            if not required.issubset(set(df.columns)):
                raise ValueError("CSV 缺少列：" + "、".join(required - set(df.columns)))
            batch = []
            for ix, row in df.iterrows():
                try:
                    batch.append(record(row["商品"], row["平台"], row["类型"],
                                        row["日元价格"], row["闲鱼售价"], row.get("结束时间", ""), row.get("链接", "")))
                except (ValueError, TypeError) as e:
                    raise ValueError("第 {} 行：{}".format(ix + 2, e))
            st.session_state["records"].extend(batch)
            st.success("成功导入 {} 件商品".format(len(batch)))
        except Exception as e:
            st.error("导入未完成：" + str(e))

with manage_tab:
    st.subheader("我的商品和竞价历史")
    saved = st.session_state["records"]
    if not saved:
        st.info("还没有你的商品。请先在「录入」添加。")
    else:
        output = []
        for r in saved:
            output.append({
                "商品": r["title"], "平台": r["platform"], "类型": r["kind"],
                "链接": r["url"], "日元价格": r["bid_jpy"],
                "闲鱼售价": r["sale_cny"], "结束时间": r["end_at"],
            })
        out = pd.DataFrame(output).to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 导出我的商品 CSV 备份", out, "中古猎手_我的商品.csv", "text/csv", use_container_width=True)
        options = {r["id"]: "{} · {}".format(r["title"], r["platform"]) for r in saved}
        selected_id = st.selectbox("选择商品", list(options), format_func=lambda x: options[x])
        selected = next(r for r in saved if r["id"] == selected_id)
        show_card(selected)
        with st.form("update_bid"):
            changed_price = st.number_input("更新当前竞价（日元）", min_value=0.0, value=float(selected["bid_jpy"]), step=100.0)
            changed_sale = st.number_input("更新闲鱼参考售价（元）", min_value=0.0, value=float(selected["sale_cny"]), step=10.0)
            changed_end = st.text_input("更新预计结束时间（北京时间）", value=str(selected["end_at"]))
            if st.form_submit_button("保存更新", use_container_width=True):
                try:
                    if selected["kind"] == "拍卖" and not changed_end:
                        st.warning("未填写预计结束时间，这件商品不会进入最后5分钟筛选")
                    parse_end(changed_end)
                    if changed_price != selected["bid_jpy"]:
                        selected["history"].append({
                            "at": now().strftime("%Y-%m-%d %H:%M:%S"), "bid_jpy":changed_price,
                        })
                    selected["bid_jpy"] = changed_price
                    selected["sale_cny"] = changed_sale
                    selected["end_at"] = changed_end
                    st.success("报价已更新；实际竞价变化才会追加历史记录。")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
        st.caption("竞价历史：仅记录你手动录入的变化，不是拍卖平台历史成交数据。")
        st.dataframe(pd.DataFrame(selected["history"]).rename(columns={"at":"记录时间", "bid_jpy":"竞价（日元）"}), hide_index=True, use_container_width=True)
        if st.button("删除这件商品", type="secondary"):
            st.session_state["records"] = [r for r in saved if r["id"] != selected_id]
            st.rerun()

with config_tab:
    st.subheader("成本与利润参数")
    st.caption("这些是可修改的试算假设，非平台实际报价。")
    with st.form("profit_settings_form"):
        fx = st.number_input("每 1 日元折合人民币", 0.001, 1.0, float(settings["fx"]), step=0.001, format="%.3f")
        ship_jpy = st.number_input("日本国内运费（日元）", min_value=0, value=int(settings["ship_jpy"]))
        fee = st.number_input("代购手续费率（%）", 0.0, 99.0, float(settings["fee"]))
        ship_cny = st.number_input("国际 + 国内物流分摊（元）", min_value=0.0, value=float(settings["ship_cny"]))
        discount = st.number_input("闲鱼挂牌价折价（%）", 0.0, 99.0, float(settings["discount"]))
        reserve = st.number_input("税费/瑕疵风险预留（元）", min_value=0.0, value=float(settings["reserve"]))
        target = st.number_input("最低净利润（元）", min_value=0.0, value=float(settings["target"]))
        roi = st.number_input("最低成本利润率（%）", min_value=0.0, value=float(settings["roi"]))
        if st.form_submit_button("应用到所有商品", use_container_width=True):
            st.session_state["settings"] = {
                "fx": fx, "ship_jpy": ship_jpy, "fee": fee, "ship_cny": ship_cny,
                "discount": discount, "reserve": reserve, "target": target, "roi": roi,
            }
            st.success("设置已更新")
            st.rerun()
    st.divider()
    st.info("目前尚不支持自动从 Yahoo / Mercari / 闲鱼获取报价，也没有实时提醒。免费云服务器可能休眠；录入数据只在当前会话保存，务必导出 CSV。")
