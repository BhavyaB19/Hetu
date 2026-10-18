"""TinyFish client, agents and runner, against a fake TinyFish server (no network)."""

import asyncio
import json

import httpx
import pytest

from app.agents import runner, tinyfish
from app.agents.base import AgentError, BaseAgent, CaseQuery
from app.agents.judgment import SCHEMA as JUDGMENT_SCHEMA
from app.agents.judgment import JudgmentAgent
from app.agents.media import ARTICLE_SCHEMA, SEARCH_SCHEMA, MediaAgent
from app.agents.tinyfish import TinyFish
from app.core.config import get_settings
from app.schemas.bundle import CaseBundle, CaseInfo, SourceDocument
from app.services.anonymizer import Person
from app.services.pipeline import anonymize

REAL_SLEEP = asyncio.sleep


@pytest.fixture(autouse=True)
def no_backoff_delays(monkeypatch):
    async def fast_sleep(_seconds):
        await REAL_SLEEP(0)

    monkeypatch.setattr(tinyfish.asyncio, "sleep", fast_sleep)


def done(result: dict) -> dict:
    return {"status": "COMPLETED", "result": result}


class FakeTinyFish:
    """Scripted TinyFish API. `script` maps a start URL to queued outcomes: a run dict
    returned by GET /v1/runs/{id}, or an int HTTP status returned when starting."""

    def __init__(self, script: dict[str, list], pages: dict[str, str] | None = None):
        self.script = script
        self.pages = pages or {}  # public pages downloaded directly, by URL
        self.started: list[dict] = []
        self.headers: list[httpx.Headers] = []
        self.runs: dict[str, dict] = {}
        self.cancelled: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.headers.append(request.headers)
        if request.url.host != "tf.test":
            url = str(request.url)
            return httpx.Response(200, text=self.pages[url]) if url in self.pages else httpx.Response(404)
        path = request.url.path
        if path == "/v1/automation/run-async":
            body = json.loads(request.content)
            outcome = self.script[body["url"]].pop(0)
            if isinstance(outcome, int):
                return httpx.Response(outcome, json={"error": {"code": "RATE_LIMIT_EXCEEDED"}})
            run_id = f"run-{len(self.started)}"
            self.started.append(body)
            self.runs[run_id] = outcome
            return httpx.Response(200, json={"run_id": run_id, "error": None})
        if path.endswith("/cancel"):
            run_id = path.split("/")[3]
            self.cancelled.append(run_id)
            return httpx.Response(200, json={"run_id": run_id, "status": "CANCELLED"})
        run_id = path.split("/")[3]
        return httpx.Response(200, json={"run_id": run_id, **self.runs[run_id]})


class StubRobots:
    def __init__(self, blocked: set[str] = frozenset()):
        self.blocked = blocked

    async def allows(self, url: str) -> bool:
        return url not in self.blocked


def client(fake: FakeTinyFish, blocked: set[str] = frozenset()) -> TinyFish:
    http = httpx.AsyncClient(transport=httpx.MockTransport(fake.handler))
    return TinyFish("tf-key", "https://tf.test", http=http, robots=StubRobots(blocked), poll_seconds=0)


# ---------- client ----------


async def test_run_polls_until_complete_and_sends_rules():
    fake = FakeTinyFish({"https://a.test": [done({"x": 1})]})
    result = await client(fake).run("https://a.test", "Do it.", {"type": "object"}, timeout=5)
    assert result == {"x": 1}
    assert fake.headers[0]["X-API-Key"] == "tf-key"
    body = fake.started[0]
    assert body["output_schema"] == {"type": "object"}
    assert "Never log in" in body["goal"] and "CAPTCHA" in body["goal"]


async def test_rate_limit_is_retried():
    fake = FakeTinyFish({"https://a.test": [429, done({"ok": True})]})
    assert await client(fake).run("https://a.test", "g", {}, timeout=5) == {"ok": True}


async def test_system_failure_is_retried_but_agent_failure_is_not():
    system = {"status": "FAILED", "error": {"category": "SYSTEM_FAILURE", "message": "boom"}}
    fake = FakeTinyFish({"https://a.test": [system, done({"ok": True})]})
    assert await client(fake).run("https://a.test", "g", {}, timeout=5) == {"ok": True}

    agent = {"status": "FAILED", "error": {"category": "AGENT_FAILURE", "message": "SITE_BLOCKED"}}
    fake = FakeTinyFish({"https://a.test": [agent]})
    with pytest.raises(AgentError, match="SITE_BLOCKED"):
        await client(fake).run("https://a.test", "g", {}, timeout=5)


async def test_timeout_cancels_the_run():
    fake = FakeTinyFish({"https://a.test": [{"status": "RUNNING"}]})
    with pytest.raises(AgentError, match="timed out"):
        await client(fake).run("https://a.test", "g", {}, timeout=0.05)
    assert fake.cancelled == ["run-0"]


async def test_robots_disallowed_url_is_never_sent():
    fake = FakeTinyFish({})
    with pytest.raises(AgentError, match=r"robots.txt"):
        await client(fake, blocked={"https://a.test"}).run("https://a.test", "g", {}, timeout=5)
    assert fake.started == []


@pytest.mark.parametrize("schema", [JUDGMENT_SCHEMA, SEARCH_SCHEMA, ARTICLE_SCHEMA])
def test_schemas_use_only_supported_keywords(schema):
    """TinyFish rejects any output_schema keyword outside its allowlist."""
    allowed = {
        "anyOf",
        "enum",
        "format",
        "items",
        "maxItems",
        "maximum",
        "minItems",
        "minimum",
        "nullable",
        "properties",
        "propertyOrdering",
        "required",
        "type",
    }

    def walk(node):
        assert set(node) <= allowed, set(node) - allowed
        for child in node.get("properties", {}).values():
            walk(child)
        if "items" in node:
            walk(node["items"])
        for name in node.get("required", []):
            assert name in node["properties"]

    walk(schema)
    assert schema["type"] == "object"


# ---------- agents ----------

QUERY = CaseQuery("State v. Example", court="Delhi High Court")
KANOON = "https://indiankanoon.org/search/?formInput=State+v.+Example+Delhi+High+Court"
BING = "https://www.bing.com/news/search?q=State+v.+Example+Delhi+High+Court"


DOC = "https://indiankanoon.org/doc/1/"
BODY = "1. This appeal arises from a judgment of acquittal. " * 20
DOC_HTML = f"""<html><body><nav>menu</nav>
<div class="judgments">
  <div class="covers"><span class="citetop">[Cites 30, Cited by 14]</span></div>
  <h3 class="docsource_main">Supreme Court of India</h3>
  <h2 class="doc_title">State v. Example on 19 April, 2010</h2>
  <h3 class="doc_citations">Equivalent citations: (2010) 6 SCC 1</h3>
  <h3 class="doc_author">Author: A</h3>
  <h3 class="doc_bench">Bench: P. Sathasivam, Swatanter Kumar</h3>
  <pre>IN THE SUPREME COURT OF INDIA</pre>
  <p>{BODY}</p>
  <blockquote>2. The appeal is dismissed &amp; the conviction upheld.</blockquote>
</div><footer>footer</footer></body></html>"""


def test_kanoon_parser():
    from app.agents.indiankanoon import parse_judgment

    j = parse_judgment(DOC_HTML)
    assert (j.court, j.title) == ("Supreme Court of India", "State v. Example on 19 April, 2010")
    assert j.citations == "(2010) 6 SCC 1" and j.bench == "P. Sathasivam, Swatanter Kumar"
    assert j.decided_on.isoformat() == "2010-04-19"
    assert j.text.startswith("IN THE SUPREME COURT OF INDIA")
    assert j.text.endswith("dismissed & the conviction upheld.")
    for noise in ("Cites", "Author", "menu", "footer", "Equivalent"):
        assert noise not in j.text


async def test_judgment_agent_finds_then_downloads_exact_text():
    fake = FakeTinyFish(
        {KANOON: [done({"found": True, "doc_url": DOC, "reason": "Final appeal."})]}, {DOC: DOC_HTML}
    )
    [doc] = await JudgmentAgent(client(fake), timeout=5).run(QUERY)
    assert doc.source_type == "judgment" and doc.source_name == "Supreme Court of India"
    assert (
        doc.title
        == "State v. Example on 19 April, 2010 · (2010) 6 SCC 1 · Bench: P. Sathasivam, Swatanter Kumar"
    )
    assert doc.published_at.isoformat() == "2010-04-19" and doc.url == DOC
    assert BODY.strip() in doc.text
    assert "do not copy the judgment text" in fake.started[0]["goal"]


@pytest.mark.parametrize(
    "result",
    [
        {"found": False, "doc_url": None, "reason": "No match."},
        {"found": True, "doc_url": "https://example.com/judgment.pdf", "reason": "Elsewhere."},
    ],
)
async def test_judgment_agent_rejects_missing_or_off_site_results(result):
    fake = FakeTinyFish({KANOON: [done(result)]})
    with pytest.raises(AgentError, match="No judgment"):
        await JudgmentAgent(client(fake), timeout=5).run(QUERY)


async def test_judgment_agent_rejects_empty_pages():
    fake = FakeTinyFish(
        {KANOON: [done({"found": True, "doc_url": DOC, "reason": "x"})]}, {DOC: "<html></html>"}
    )
    with pytest.raises(AgentError, match="no readable judgment"):
        await JudgmentAgent(client(fake), timeout=5).run(QUERY)


async def test_media_agent_reads_articles_and_comments():
    search = done(
        {
            "articles": [
                {
                    "headline": "A",
                    "url": "https://news.test/a",
                    "outlet": "News A",
                    "published_date": "2021-08-21",
                },
                {"headline": "A again", "url": "https://news.test/a", "outlet": "News A"},
                {"headline": "Blocked", "url": "https://blocked.test/b", "outlet": "News B"},
                {"headline": "C", "url": "https://news.test/c", "outlet": "News C"},
                {"headline": "Broken", "url": "https://news.test/d", "outlet": "News D"},
            ]
        }
    )
    article_a = done(
        {
            "headline": "A",
            "outlet": "News A",
            "published_date": None,
            "body": "Body A.",
            "comments": [{"text": "Justice now!", "posted_date": "2021-08-22"}, {"text": "  "}],
        }
    )
    article_c = done(
        {
            "headline": "C",
            "outlet": "News C",
            "published_date": "2023-02-11",
            "body": "Body C.",
            "comments": [],
        }
    )
    failed = {"status": "FAILED", "error": {"category": "AGENT_FAILURE", "message": "TASK_FAILED"}}
    fake = FakeTinyFish(
        {
            BING: [search],
            "https://news.test/a": [article_a],
            "https://news.test/c": [article_c],
            "https://news.test/d": [failed],
        }
    )
    docs = await MediaAgent(client(fake, blocked={"https://blocked.test/b"}), timeout=5).run(QUERY)

    assert [(d.key, d.source_type) for d in docs] == [
        ("media-1", "media"),
        ("public-1-1", "public"),
        ("media-2", "media"),
    ]
    assert docs[0].published_at.isoformat() == "2021-08-21"  # falls back to the search result date
    assert docs[1].source_name == "Reader comments, News A"
    assert "blocked.test" not in {b["url"].split("/")[2] for b in fake.started}


# ---------- runner ----------


class FakeAgent(BaseAgent):
    def __init__(self, name: str, docs: list[SourceDocument] | Exception):
        self.name = name
        self.docs = docs

    async def run(self, query):
        if isinstance(self.docs, Exception):
            raise self.docs
        return self.docs


JUDGMENT = SourceDocument(
    key="judgment", source_type="judgment", source_name="Delhi High Court", text="Held."
)
ARTICLE = SourceDocument(key="media-1", source_type="media", source_name="News A", text="Story.")


async def test_runner_continues_without_media():
    bundle = await runner.run_agents(
        QUERY, [FakeAgent("judgment", [JUDGMENT]), FakeAgent("media", AgentError("no news"))], agent_timeout=5
    )
    assert [d.key for d in bundle.documents] == ["judgment"]
    assert bundle.case.slug == "state-v-example" and bundle.case.court == "Delhi High Court"
    assert not bundle.is_extracted


async def test_runner_fails_without_judgment():
    with pytest.raises(AgentError, match="Judgment collection failed"):
        await runner.run_agents(
            QUERY, [FakeAgent("judgment", AgentError("none")), FakeAgent("media", [ARTICLE])], agent_timeout=5
        )


@pytest.fixture
def settings(monkeypatch, tmp_path):
    monkeypatch.setenv("COLLECTED_DIR", str(tmp_path))
    monkeypatch.setenv("TINYFISH_API_KEY", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def test_collect_needs_a_key(settings, monkeypatch):
    monkeypatch.setenv("USE_FIXTURES", "false")
    get_settings.cache_clear()
    with pytest.raises(AgentError, match="TINYFISH_API_KEY"):
        await runner.collect(QUERY)


async def test_collect_replays_cache_with_use_fixtures(settings, monkeypatch, tmp_path):
    monkeypatch.setenv("USE_FIXTURES", "true")
    get_settings.cache_clear()
    with pytest.raises(AgentError, match="no cached collection"):
        await runner.collect(QUERY)

    cached = await runner.run_agents(QUERY, [FakeAgent("judgment", [JUDGMENT])], agent_timeout=5)
    (tmp_path / "state-v-example.json").write_text(cached.model_dump_json(), encoding="utf-8")
    bundle, path = await runner.collect(QUERY)
    assert bundle == cached and path.parent == tmp_path


def test_named_case_titles_do_not_leak_into_slugs():
    bundle = CaseBundle(
        case=CaseInfo(slug="state-v-ravi-kumar", title="State v. Ravi Kumar", category="Criminal Law"),
        documents=[JUDGMENT],
    )
    out = anonymize(bundle, [Person(name="Ravi Kumar", role="accused")])
    assert out.case.title == "State v. [ACCUSED_1]"
    assert "ravi" not in out.case.slug and out.case.slug.startswith("state-v-accused-1-")


async def test_judgment_failure_stops_other_agents_early():
    class SlowMedia(BaseAgent):
        name = "media"
        cancelled = False

        async def run(self, query):
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                SlowMedia.cancelled = True
                raise
            return []

    with pytest.raises(AgentError, match="Judgment collection failed"):
        await asyncio.wait_for(
            runner.run_agents(
                QUERY, [FakeAgent("judgment", AgentError("none")), SlowMedia()], agent_timeout=30
            ),
            timeout=2,
        )
    assert SlowMedia.cancelled


async def test_cancelling_a_run_cancels_it_on_tinyfish():
    fake = FakeTinyFish({"https://a.test": [{"status": "RUNNING"}]})
    task = asyncio.create_task(client(fake).run("https://a.test", "g", {}, timeout=30))
    while not fake.started:
        await REAL_SLEEP(0.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert fake.cancelled == ["run-0"]


async def test_agent_steps_are_logged_once(caplog):
    class Steps(FakeTinyFish):
        polls = 0

        def handler(self, request):
            if request.method == "GET" and "/v1/runs/" in request.url.path:
                Steps.polls += 1
                steps = [{"id": "s1", "action": "Open search results"}]
                if Steps.polls > 1:
                    steps.append({"id": "s2", "action": "Open the matching judgment"})
                status = "COMPLETED" if Steps.polls > 2 else "RUNNING"
                return httpx.Response(
                    200, json={"run_id": "run-0", "status": status, "steps": steps, "result": {}}
                )
            return super().handler(request)

    fake = Steps({"https://a.test": [done({})]})
    with caplog.at_level("INFO", logger="hetu.tinyfish"):
        await client(fake).run("https://a.test", "g", {}, timeout=5)
    steps = [r.getMessage() for r in caplog.records if r.getMessage().startswith("a.test:")]
    assert steps == ["a.test: Open search results", "a.test: Open the matching judgment"]


async def test_collect_reuses_an_earlier_collection(settings, monkeypatch, tmp_path):
    monkeypatch.setenv("USE_FIXTURES", "false")
    get_settings.cache_clear()
    cached = await runner.run_agents(QUERY, [FakeAgent("judgment", [JUDGMENT])], agent_timeout=5)
    (tmp_path / "state-v-example.json").write_text(cached.model_dump_json(), encoding="utf-8")
    bundle, _ = await runner.collect(QUERY)  # no TinyFish key needed: nothing is collected
    assert bundle == cached
    with pytest.raises(AgentError, match="TINYFISH_API_KEY"):
        await runner.collect(QUERY, refresh=True)
