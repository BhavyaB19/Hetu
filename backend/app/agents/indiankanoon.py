"""Read an Indian Kanoon judgment page (https://indiankanoon.org/doc/<id>/) into text and metadata.

The judgment sits in <div class="judgments">: headings with classes docsource_main
(court), doc_title, doc_citations, doc_bench and doc_author, then the body as
<pre>, <p> and <blockquote> blocks. The citation counter (<div class="covers">) is skipped.
"""

import datetime as dt
import re
from dataclasses import dataclass
from html.parser import HTMLParser

DOC_URL = re.compile(r"^https?://(www\.)?indiankanoon\.org/doc/(\d+)/?$")
BLOCKS = {"p", "pre", "blockquote", "div", "h2", "h3", "br", "li"}
META = {
    "docsource_main": "court",
    "doc_title": "title",
    "doc_citations": "citations",
    "doc_bench": "bench",
    "doc_author": "author",
}


@dataclass
class KanoonJudgment:
    court: str
    title: str
    citations: str | None
    bench: str | None
    decided_on: dt.date | None
    text: str


class _Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0  # depth inside div.judgments; 0 = outside
        self.skip_depth = 0  # depth at which a skipped block (covers, meta heading) started
        self.meta_field: str | None = None
        self.meta: dict[str, str] = {}
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = (dict(attrs).get("class") or "").split()
        if self.depth == 0:
            if tag == "div" and "judgments" in classes:
                self.depth = 1
            return
        if tag == "div":
            self.depth += 1
        if not self.skip_depth:
            field = next((META[c] for c in classes if c in META), None)
            if field or (tag == "div" and "covers" in classes):
                self.skip_depth = self.depth if tag == "div" else -1
                self.meta_field = field
                self.meta.setdefault(field, "") if field else None
        if tag in BLOCKS and not self.skip_depth:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self.depth == 0:
            return
        if self.skip_depth == -1 and tag in ("h2", "h3"):
            self.skip_depth, self.meta_field = 0, None
        if tag == "div":
            if self.skip_depth == self.depth:
                self.skip_depth, self.meta_field = 0, None
            self.depth -= 1
        if tag in BLOCKS and not self.skip_depth:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.depth == 0:
            return
        if self.meta_field:
            self.meta[self.meta_field] += data
        elif not self.skip_depth:
            self.parts.append(data)


def parse_judgment(html: str) -> KanoonJudgment:
    parser = _Parser()
    parser.feed(html)
    text = re.sub(r"[ \t]+\n", "\n", "".join(parser.parts))
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    meta = {k: re.sub(r"\s+", " ", v).strip() for k, v in parser.meta.items()}
    title = meta.get("title", "")
    bench = meta.get("bench", "").removeprefix("Bench:").strip() or None
    citations = meta.get("citations", "").removeprefix("Equivalent citations:").strip() or None
    return KanoonJudgment(
        court=meta.get("court", ""),
        title=title,
        citations=citations,
        bench=bench,
        decided_on=_decided_on(title),
        text=text,
    )


def _decided_on(title: str) -> dt.date | None:
    """Indian Kanoon titles end with 'on 1 December, 2017'."""
    match = re.search(r"\bon (\d{1,2} \w+, \d{4})$", title)
    if not match:
        return None
    try:
        return dt.datetime.strptime(match.group(1), "%d %B, %Y").date()
    except ValueError:
        return None
