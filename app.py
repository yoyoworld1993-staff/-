import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from core import calculate

st.set_page_config(page_title="中古猎手",page_icon="🚗",layout="wide")
st.title("🚗 中古猎手")
st.caption("手机云端原型｜手动/CSV导入，非实时爬虫。数据只保存在当前会话，请及时导出。")
if "items" not in st.session_state: st.session_state['items']=[]
with st.sidebar:
 st.header("利润参数")
 fx=st.number_input("1日元=人民币",min_value=0.001,value=0.045,step=0.001,format="%.3f")
 ship_jpy=st.number_input("日本国内运费（日元）",min_value=0,value=0)
 fee=st.number_input("代购费率%",min_value=0.0,max_value=99.0,value=5.0)
 ship_cny=st.number_input("国际及国内物流（元）",min_value=0.0,value=45.0)
 discount=st.number_input("闲鱼成交折价%",min_value=0.0,max_value=99.0,value=10.0)
 reserve=st.number_input("税费/瑕疵预留（元）",min_value=0.0,value=10.0)
 target=st.number_input("目标净利润（元）",min_value=0.0,value=50.0)
st.subheader("添加商品")
with st.form("add"):
 title=st.text_input("商品名称/型号")
 platform=st.selectbox("货源",["Yahoo Auctions","Mercari","Rakuma","Yahoo Flea Market","Suruga-ya","Mandarake","Yahoo Shopping","挖煤姬","其他"])
 kind=st.selectbox("交易方式",["拍卖","一口价"])
 url=st.text_input("商品链接（可选）")
 bid=st.number_input("当前竞价/一口价（日元）",min_value=0,value=1000)
 sale=st.number_input("闲鱼售价参考（人民币）",min_value=0.0,value=200.0)
 end=st.text_input("预计结束时间：北京时间 YYYY-MM-DD HH:MM（可空）")
 if st.form_submit_button("保存商品",use_container_width=True):
  try:
   from urllib.parse import urlparse
   if not title.strip(): raise ValueError("商品名称不能为空")
   if url and urlparse(url).scheme not in ("https","http"): raise ValueError("仅支持 http/https 链接")
   if end: datetime.strptime(end,"%Y-%m-%d %H:%M")
   st.session_state['items'].append(dict(商品=title,平台=platform,类型=kind,链接=url,日元价格=bid,闲鱼售价=sale,结束时间=end))
   st.success("保存成功")
  except ValueError as e: st.error(str(e))
up=st.file_uploader("CSV 导入（商品、平台、类型、链接、日元价格、闲鱼售价、结束时间）",type="csv")
if up and st.button("导入 CSV"):
 try:
  df=pd.read_csv(up).fillna("")
  required={"商品","平台","类型","链接","日元价格","闲鱼售价","结束时间"}
  if not required.issubset(df.columns): raise ValueError("CSV 缺少字段："+",".join(required-set(df.columns)))
  parsed=[]
  for r in df.to_dict("records"):
   r["日元价格"]=float(r["日元价格"]);r["闲鱼售价"]=float(r["闲鱼售价"])
   if r["日元价格"]<0 or r["闲鱼售价"]<0: raise ValueError("价格不能为负")
   if r["结束时间"]: datetime.strptime(str(r["结束时间"] ),"%Y-%m-%d %H:%M")
   parsed.append(r)
  st.session_state['items'].extend(parsed);st.success(f"成功导入 {len(parsed)} 条")
 except Exception as e: st.error(str(e))
now=datetime.now(ZoneInfo("Asia/Shanghai"))
rows=[]
for i,r in enumerate(st.session_state['items']):
 try:
  cost,profit,cap=calculate(float(r["日元价格"]),fx,ship_jpy,fee,ship_cny,float(r["闲鱼售价"]),discount,reserve,target)
  minutes=None
  if r["结束时间"]:
   finish=datetime.strptime(str(r["结束时间"]),"%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("Asia/Shanghai"))
   minutes=round((finish-now).total_seconds()/60,1)
  urgent=r["类型"]=="拍卖" and minutes is not None and 0<=minutes<=5
  rows.append({**r,"成本人民币":cost,"预计净利润":profit,"最高出价日元":cap,"剩余分钟":minutes,"临近截拍":"🔥" if urgent else "","达标":profit>=target})
 except Exception as e: st.warning(f"第 {i+1} 件商品异常：{e}")
st.subheader("临近截拍雷达")
if rows:
 df=pd.DataFrame(rows)
 a,b,c=st.columns(3)
 a.metric("商品",len(df));b.metric("最后5分钟",int((df["临近截拍"]=="🔥").sum()));c.metric("利润达标",int(df["达标"].sum()))
 if st.toggle("仅看最后5分钟"):df=df[df["临近截拍"]=="🔥"]
 st.dataframe(df.sort_values(["临近截拍","预计净利润"],ascending=[False,False]),hide_index=True,use_container_width=True)
 st.download_button("导出CSV备份",pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig"),"中古猎手_备份.csv","text/csv")
else: st.info("先录入商品或导入 CSV")
st.caption("结束时间仅为手工记录的预计时间；不自动同步平台竞价，不处理拍卖延时。")
