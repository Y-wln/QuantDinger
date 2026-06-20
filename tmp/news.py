#!/usr/bin/env python3
"""Crypto News RSS"""
import sys, os, time, re
sys.path.insert(0, '/home/ubuntu/scripts/agents')
from hermes_core import feishu_send
from urllib.request import Request, build_opener, ProxyHandler

ph = ProxyHandler({"http":"http://127.0.0.1:7892","https":"http://127.0.0.1:7892"})
opener = build_opener(ph)

FEEDS = [
    "https://decrypt.co/feed",
    "https://cointelegraph.com/rss",
]

def fetch():
    headlines = []
    for url in FEEDS:
        try:
            req = Request(url, headers={"User-Agent":"Mozilla/5.0"})
            with opener.open(req, timeout=12) as resp:
                content = resp.read().decode("utf-8", errors="ignore")
            items = re.findall(r'<item>.*?<title><!\[CDATA\[(.*?)\]\]></title>.*?</item>', content, re.DOTALL)
            if not items:
                items = re.findall(r'<item>.*?<title>(.*?)</title>.*?</item>', content, re.DOTALL)
            for title in items[:5]:
                title = re.sub(r'<[^>]+>', '', title).strip()
                if title and len(title) > 10:
                    headlines.append(title)
        except Exception as e:
            print("RSS err:", url, e)
    return headlines[:6]

last = set()

if __name__ == "__main__":
    feishu_send("News RSS online | Decrypt + Cointelegraph | 10min")
    print("News RSS started")
    while True:
        try:
            headlines = fetch()
            new = [h for h in headlines if h not in last]
            if new:
                msg = "Crypto News\n" + "\n".join("  " + h[:80] for h in new[:4])
                feishu_send(msg)
                print("News:", len(new), "new")
            last = set(headlines)
        except Exception as e:
            print("err:", e)
        time.sleep(600)
