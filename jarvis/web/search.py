import base64
import re
import webbrowser
from urllib.parse import parse_qs, quote, quote_plus, unquote, urlparse

import requests

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


class WebTools:
    def search(self, query: str, limit: int = 5) -> list[dict]:
        query = (query or "").strip()
        if not query:
            return []
        items = []
        for fn in (self._wikipedia, self._ddg_instant, self._bing):
            try:
                extra = fn(query, limit)
            except Exception:
                extra = []
            for it in extra:
                url = it.get("url") or ""
                if url and url not in {x.get("url") for x in items}:
                    items.append(it)
            if len(items) >= limit:
                break
        return items[:limit]

    def _wikipedia(self, query: str, limit: int) -> list[dict]:
        r = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "opensearch",
                "search": query,
                "limit": limit,
                "namespace": 0,
                "format": "json",
            },
            headers=UA,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        titles = data[1] if len(data) > 1 else []
        descs = data[2] if len(data) > 2 else []
        urls = data[3] if len(data) > 3 else []
        items = []
        for i, title in enumerate(titles):
            items.append(
                {
                    "title": title,
                    "snippet": (descs[i] if i < len(descs) else "") or "",
                    "url": urls[i] if i < len(urls) else "",
                }
            )
        if items:
            try:
                t0 = titles[0]
                s = requests.get(
                    f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(t0)}",
                    headers=UA,
                    timeout=12,
                )
                if s.ok:
                    extract = (s.json().get("extract") or "").strip()
                    if extract:
                        items[0]["snippet"] = extract
            except Exception:
                pass
        return items

    def _ddg_instant(self, query: str, limit: int) -> list[dict]:
        r = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            headers=UA,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        items = []
        abstract = (data.get("AbstractText") or "").strip()
        heading = data.get("Heading") or query
        abs_url = data.get("AbstractURL") or ""
        if abstract:
            items.append({"title": heading, "snippet": abstract, "url": abs_url})
        for topic in data.get("RelatedTopics") or []:
            if not isinstance(topic, dict):
                continue
            text = (topic.get("Text") or "").strip()
            url = topic.get("FirstURL") or ""
            if text:
                title = text.split(" - ", 1)[0]
                snip = text.split(" - ", 1)[-1] if " - " in text else ""
                items.append({"title": title, "snippet": snip, "url": url})
            if len(items) >= limit:
                break
        return items

    def _bing(self, query: str, limit: int) -> list[dict]:
        r = requests.get(
            "https://www.bing.com/search?q=" + quote_plus(query),
            headers=UA,
            timeout=15,
        )
        r.raise_for_status()
        items = []
        for m in re.finditer(r'<h2[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', r.text, re.I | re.S):
            href = self._bing_url(m.group(1))
            title = re.sub(r"<[^>]+>", "", m.group(2))
            title = re.sub(r"\s+", " ", title).strip()
            if not href or not title or "bing.com" in href:
                continue
            items.append({"title": title, "url": href, "snippet": ""})
            if len(items) >= limit:
                break
        return items

    def _bing_url(self, href: str) -> str:
        href = (href or "").replace("&", "&")
        qs = parse_qs(urlparse(href).query)
        u = (qs.get("u") or [""])[0]
        if u.startswith("a1"):
            raw = u[2:]
            raw += "=" * ((4 - len(raw) % 4) % 4)
            try:
                return base64.b64decode(raw).decode("utf-8", "replace")
            except Exception:
                return ""
        if href.startswith("http") and "bing.com" not in href:
            return href
        return ""

    def fetch(self, url: str, max_chars: int = 8000) -> str:
        if not url.startswith(("http://", "https://")):
            raise ValueError("Only http/https")
        r = requests.get(url, headers=UA, timeout=25)
        r.raise_for_status()
        text = r.text
        text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
        text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]

    def answer(self, query: str, open_browser: bool = True) -> str:
        query = (query or "").strip()
        if not query:
            return "What should I search for?"
        if open_browser:
            try:
                webbrowser.open("https://www.google.com/search?q=" + quote_plus(query))
            except Exception:
                pass
        items = self.search(query, limit=6)
        if not items:
            return f"Opened a Google search for “{query}”. I couldn't parse extra results here."
        lines = [f"Here's what I found for “{query}”:"]
        for i in items[:5]:
            title = i.get("title") or ""
            url = i.get("url") or ""
            snip = i.get("snippet") or ""
            if title:
                lines.append(f"• {title}")
                if snip:
                    lines.append(f"  {snip[:280]}")
                if url:
                    lines.append(f"  {url}")
        return "\n".join(lines)
