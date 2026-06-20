"""HTTP client with retry, timeout, and proxy fallback."""
import time, json, threading
import urllib.request
import urllib.error
from urllib.request import Request, urlopen, build_opener, ProxyHandler

PROXY_URL = 'http://127.0.0.1:7891'


class HTTPClient:
    def __init__(self, retries=3, timeout=10):
        self.retries = retries
        self.timeout = timeout
        self.lock = threading.Lock()
        self._proxy_fails = 0

    def _fetch(self, url, headers=None, timeout=None):
        """Fetch with proxy first, fallback to direct after 3 consecutive failures."""
        timeout = timeout or self.timeout
        hdrs = {'User-Agent': 'Mozilla/5.0'}
        if headers:
            hdrs.update(headers)

        # Try proxy first
        try:
            opener = build_opener(ProxyHandler({'http': PROXY_URL, 'https': PROXY_URL}))
            req = Request(url, headers=hdrs)
            with opener.open(req, timeout=timeout) as resp:
                data = resp.read().decode()
            with self.lock:
                self._proxy_fails = 0
            return json.loads(data)
        except Exception:
            with self.lock:
                self._proxy_fails += 1
            # Fallback to direct after 3 consecutive proxy failures
            if self._proxy_fails >= 3:
                try:
                    req = Request(url, headers=hdrs)
                    with urlopen(req, timeout=min(timeout, 8)) as resp:
                        data = resp.read().decode()
                    with self.lock:
                        self._proxy_fails = 0
                    return json.loads(data)
                except Exception:
                    pass
            raise

    def get(self, url, headers=None):
        last_err = None
        for attempt in range(self.retries):
            try:
                return self._fetch(url, headers)
            except (urllib.error.URLError, urllib.error.HTTPError,
                    TimeoutError, ConnectionError, json.JSONDecodeError) as e:
                last_err = e
                if attempt < self.retries - 1:
                    time.sleep(2 ** attempt)
        raise last_err or RuntimeError(f"GET {url} failed after {self.retries} retries")

    def post(self, url, data, headers=None):
        last_err = None
        for attempt in range(self.retries):
            try:
                body = json.dumps(data).encode()
                hdrs = {'Content-Type': 'application/json'}
                if headers:
                    hdrs.update(headers)
                req = Request(url, data=body, method='POST', headers=hdrs)
                # Try via proxy path
                try:
                    opener = build_opener(ProxyHandler({'http': PROXY_URL, 'https': PROXY_URL}))
                    with opener.open(req, timeout=self.timeout) as resp:
                        return json.loads(resp.read().decode())
                except Exception:
                    with urlopen(req, timeout=self.timeout) as resp:
                        return json.loads(resp.read().decode())
            except (urllib.error.URLError, urllib.error.HTTPError,
                    TimeoutError, ConnectionError, json.JSONDecodeError) as e:
                last_err = e
                if attempt < self.retries - 1:
                    time.sleep(2 ** attempt)
        raise last_err or RuntimeError(f"POST {url} failed after {self.retries} retries")
