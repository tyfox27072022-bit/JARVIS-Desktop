"""Light markdown → HTML for the chat pane."""
from __future__ import annotations

import html
import re


def chat_html(who: str, text: str, mine: bool) -> str:
    color = "#8a8474" if mine else "#e8c547"
    body = _md(text or "")
    return (
        f'<div style="margin:12px 0 18px 0;">'
        f'<div style="color:{color};font-size:11px;letter-spacing:0.14em;">{html.escape(who.upper())}</div>'
        f'<div style="color:#e8e4d8;margin-top:6px;line-height:1.55;">{body}</div>'
        f"</div>"
    )


def _md(text: str) -> str:
    parts = []
    buf = []
    in_code = False
    for line in (text or "").splitlines():
        if line.strip().startswith("```"):
            if in_code:
                parts.append(
                    '<pre style="background:#12141a;border:1px solid #1c1910;border-radius:8px;'
                    'padding:10px 12px;overflow:auto;color:#d4cfc0;font-size:13px;">'
                    + html.escape("\n".join(buf))
                    + "</pre>"
                )
                buf = []
                in_code = False
            else:
                if buf:
                    parts.append(_inline("\n".join(buf)))
                    buf = []
                in_code = True
            continue
        buf.append(line)
    if in_code:
        parts.append("<pre>" + html.escape("\n".join(buf)) + "</pre>")
    elif buf:
        parts.append(_inline("\n".join(buf)))
    return "".join(parts) or "&nbsp;"


def _inline(block: str) -> str:
    lines = block.splitlines()
    out = []
    list_buf = []

    def flush_list():
        nonlocal list_buf
        if list_buf:
            items = "".join(f"<li>{_spans(x)}</li>" for x in list_buf)
            out.append(f"<ul style='margin:6px 0 6px 1.2em;padding:0;'>{items}</ul>")
            list_buf = []

    for ln in lines:
        m = re.match(r"^\s*[-•]\s+(.+)$", ln)
        if m:
            list_buf.append(m.group(1))
            continue
        flush_list()
        if re.match(r"^#+\s+", ln):
            t = re.sub(r"^#+\s+", "", ln)
            out.append(f"<div style='color:#e8c547;margin:8px 0 4px 0;'>{_spans(t)}</div>")
        elif ln.strip() == "":
            out.append("<br>")
        else:
            out.append(_spans(ln) + "<br>")
    flush_list()
    return "".join(out)


def _spans(s: str) -> str:
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`([^`]+)`", r"<code style='background:#12141a;padding:1px 5px;border-radius:4px;'>\1</code>", s)
    return s
