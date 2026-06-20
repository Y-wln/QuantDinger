from urllib.request import Request, build_opener, ProxyHandler
ph = ProxyHandler({"http":"http://127.0.0.1:7892","https":"http://127.0.0.1:7892"})
opener = build_opener(ph)
try:
    r = opener.open(Request("https://hyblockcapital.com", headers={"User-Agent":"Mozilla/5.0"}), timeout=15)
    print("OK:", r.status)
except Exception as e:
    print("FAIL:", e)
try:
    r = opener.open(Request("https://api.hyblockcapital.com/v2/health", headers={"User-Agent":"Mozilla/5.0"}), timeout=15)
    print("API OK:", r.status, r.read()[:100])
except Exception as e:
    print("API FAIL:", e)
