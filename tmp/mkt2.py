import json,urllib.request;proxy=urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"});o=urllib.request.build_opener(proxy)
d=json.loads(o.open("https://fapi.binance.com/fapi/v1/ticker/24hr",timeout=10).read())
wanted={"ESPORTSUSDT","ALLOUSDT","SYNUSDT","PORTALUSDT","INJUSDT","STGUSDT","BTCUSDT"}
for t in d:
 if t["symbol"] in wanted:
  print(t["symbol"].replace("USDT","")+": "+t.get("priceChangePercent","?"))