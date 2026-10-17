import pytest
from httpx import ASGITransport, AsyncClient

from app.db import SessionLocal, engine
from app.main import app
from app.models import Base
from app.pipeline import anonymize
from app.scoring import perception_gap
from app.store import save_case


@pytest.fixture
async def client(demo):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    bundle = anonymize(demo, [])
    async with SessionLocal() as session:
        await save_case(session, bundle, perception_gap(bundle))
        await save_case(session, bundle, perception_gap(bundle))  # re-saving replaces, not duplicates
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_health(client):
    res = await client.get("/health")
    assert res.json() == {"status": "ok", "db": "ok"}


async def test_case_list(client, demo):
    res = await client.get("/cases")
    assert res.status_code == 200
    [case] = res.json()
    assert case["slug"] == "jan-mat-v-state"
    assert case["gap_score"] == perception_gap(demo).score


async def test_case_view(client):
    res = await client.get("/cases/jan-mat-v-state")
    assert res.status_code == 200
    view = res.json()
    components = view["gap"]["components"]
    assert [c["key"] for c in components] == ["factual", "framing", "sentiment", "timeline"]
    assert sum(c["contribution"] for c in components) == pytest.approx(view["gap"]["score"], abs=0.2)
    assert len(view["timeline"]) == 5 and view["timeline"][0]["media_weight"] == 0.8
    dates = [m["published_at"] for m in view["media"]]
    assert dates == sorted(dates)
    claim = view["media"][0]["claims"][0]
    assert claim["evidence"]["source_name"] and claim["evidence"]["quote"]
    assert view["judgment"]["evidence"]["motive"]["source_name"].startswith("High Court")
    assert view["public"]["total"] == 16
    assert sum(s["count"] for s in view["public"]["sentiment"]) == 16
    assert view["public"]["themes"][0]["key"] == "Faith in the courts"
    assert not any("98765" in r["text"] for r in view["public"]["reactions"])


async def test_unknown_case_is_404(client):
    assert (await client.get("/cases/nope")).status_code == 404
