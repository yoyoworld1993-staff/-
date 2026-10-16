# 中古猎手 · 手机网页版

专为日本中古小车设计的临近截拍比价原型。支持 Yahoo Auctions、Mercari、Rakuma 等货源的**手工数据/CSV 导入**，计算全成本、利润及最高竞拍价，筛选预计结束前 5 分钟拍品。

**重要：当前并未连接 Yahoo、Mercari、闲鱼、挖煤姬的实时数据接口，不能自动搜货，也不会自动出价。** 截拍时间为用户输入的预计时间；页面刷新更新倒计时，但不会更新平台竞价。数据保存在当前 Streamlit 会话，服务器重启或会话过期可能丢失。

## 发布到 Streamlit Community Cloud
1. 登录 https://share.streamlit.io/
2. 点击 Create app / New app → Deploy a public app from GitHub
3. 仓库：`yoyoworld1993-staff/-`；分支：`main`；入口：`app.py`
4. 发布后在 iPhone Safari 打开生成的 HTTPS 地址，使用分享 → 添加到主屏幕。

本仓库公开。不要上传真实采购数据、手机号、账户凭据或 API 密钥。

## 运行本地测试
`python -m pip install -r requirements.txt`
`streamlit run app.py`

后续路线：授权数据源 → 自动巡检 → 永久数据库 → 安全登录 → 手机提醒。

## 免费自动搜索试验版
通过 discovery.py 对 Yahoo Auctions 和 Mercari 搜索页按按钮触发保守读取；遵守 robots.txt，无需登录，不保证网站允许或能成功采集。Yahoo Shopping 官方 API 需要单独申请免费 Client ID。没有最新报价/截拍信息的商品明确标注未知；免费搜索失败可点原站链接。不要依赖本版执行自动竞拍。


## v0.6 真实找货工作流（零付费）
目前免费抓取 Mercari / Yahoo 的后端公开页面在 Render 上受 robots 或页面限制，不能作为可靠货源。因此正式「找货」首页不再把实验抓取当成可用功能。

1. 手机打开「找货」，进入 **JPSearch (https://jpsearch.moe/)** 或 **ZenMarket (https://zenmarket.jp/cn/)** 搜索真实商品。JPSearch 免费版公布每天 3 次搜索、通知每 12 小时检查，不是最后 5 分钟竞拍报价。
2. 想盯临近截拍，可直接点击 Yahoo Auctions 的结束时间升序原站搜索链接，核对结束时间与竞价。
3. 将真实商品标题、日元价格、链接复制，粘贴回中古猎手「找货」底部，确认型号后收藏。
4. 对已收藏商品填写闲鱼保守售价、运费和预计截拍时间，雷达计算利润和出价上限。
5. 从「我的货」定期导出 CSV；云端免费部署当前使用 Streamlit 会话状态，不保证永久保存。

没有第三方公开或授权 API 的商品无法无成本实现无人值守的实时采集，不绕过网站限制或验证码，也不进行自动竞拍。
