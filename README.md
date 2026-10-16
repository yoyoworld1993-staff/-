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
