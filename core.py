def calculate(bid,fx,ship_jpy,fee_pct,ship_cny,sale_cny,discount_pct,reserve_cny,target):
    if fx<=0 or bid<0 or ship_jpy<0 or not (0<=fee_pct<100) or not (0<=discount_pct<100): raise ValueError("参数不合法")
    cost=(bid+ship_jpy)*fx*(1+fee_pct/100)+ship_cny+reserve_cny
    proceeds=sale_cny*(1-discount_pct/100)
    profit=proceeds-cost
    max_bid=max(0,int((proceeds-target-ship_cny-reserve_cny)/(fx*(1+fee_pct/100))-ship_jpy))
    return round(cost,2),round(profit,2),max_bid
