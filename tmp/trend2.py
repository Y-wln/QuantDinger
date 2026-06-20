import json,urllib.request;proxy=urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"});o=urllib.request.build_opener(proxy)
d=json.loads(o.open("https://fapi.binance.com/fapi/v1/ticker/24hr",timeout=10).read())
wanted={"ESPORTSUSDT","ALLOUSDT","SYNUSDT","PORTALUSDT","INJUSDT","STGUSDT","IOUSDT","ENAUSDT","TAOUSDT","TRUMPUSDT","MEGAUSDT","COAIUSDT","FETUSDT","WLDUSDT","HYPEUSDT","AAVEUSDT"}
print("SYM          24h%%     high%%    low%%     DIR")
for t in d:
 if t["symbol"] in wanted:
  chg=float(t.get("priceChangePercent",0))
  hi=float(t["highPrice"]);lo=float(t["lowPrice"]);last=float(t["lastPrice"])
  from_hi=(last-hi)/hi*100;from_lo=(last-lo)/lo*100
  dr="UP" if chg>1 else "DOWN" if chg<-1 else "FLAT"
  print("%-12s %+6.1f%%  %+5.1f%%  %+5.1f%%  [%s]" % (t["symbol"].replace("USDT",""),chg,from_hi,from_lo,dr))