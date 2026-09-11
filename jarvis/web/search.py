import re

import requests
from html.parser import HTMLParser
from urllib.parse import quote_plus


class WebTools:
    def search(self, query: str, limit: int = 5) -> list[dict]:
        url = "https://html.duckduckgo.com/html/?q=" + quote_plus(query)
        r = requests.get(url, headers={"User-Agent": "JARVIS/2.0"}, timeout=20)
        r.raise_for_status()

        class Parser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.in_a = False
                self.items = []
                self.buf = ""
                self.href = ""

            def handle_starttag(self, tag, attrs):
                if tag == "a":
                    d = dict(attrs)
                    cls = d.get("class", "")
                    if "result__a" in cls:
                        self.in_a = True
                        self.href = d.get("href", "")
                        self.buf = ""

            def handle_data(self, data):
                if self.in_a:
                    self.buf += data

            def handle_endtag(self, tag):
                if tag == "a" and self.in_a:
                    title = self.buf.strip()
                    if title:
                        self.items.append({"title": title, "url": self.href})
                    self.in_a = False

        p = Parser()
        p.feed(r.text)
        return p.items[:limit]

    def fetch(self, url: str, max_chars: int = 8000) -> str:
        if not url.startswith(("http://", "https://")):
            raise ValueError("Only http/https")
        r = requests.get(url, headers={"User-Agent": "JARVIS/2.0"}, timeout=25)
        r.raise_for_status()
        text = r.text
        # strip tags roughly
        text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
        text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
