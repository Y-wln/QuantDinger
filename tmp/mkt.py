import json,urllib.request;proxy=urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"});o=urllib.request.build_opener(proxy)
for s in ["ESPORTSUSDT","ALLOUSDT","SYNUSDT","PORTALUSDT","INJUSDT","STGUSDT","BTCUSDT"]:
 try:
  d=json.loads(o.open("https://fapi.binance.com/fapi/v1/ticker/24hr?symbol="+s,timeout=5).read())
  print(s.replace("USDT","")+": "+d.get("priceChangePercent","?"))
 except: print(s+": ERR")