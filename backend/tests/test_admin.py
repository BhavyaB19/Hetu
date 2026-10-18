import logging

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.repository import save_case
from app.db.session import SessionLocal
from app.main import app, lifespan
from app.services.pipeline import anonymize
from app.services.scoring import perception_gap

pytestmark = pytest.mark.usefixtures("clean_database")

ADMIN_HEADERS = {"X-Admin-Key": "hetu-dev-admin-key"}


@pytest.fixture
async def client(demo):
    bundle = anonymize(demo, [])
    async with SessionLocal() as session:
        await save_case(session, bundle, perception_gap(bundle))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_admin_endpoints_require_auth(client):
    res = await client.get("/admin/cases")
    assert res.status_code == 401
    assert "Unauthorized" in res.json()["detail"]

    res = await client.get("/admin/cases", headers={"X-Admin-Key": "wrong-key"})
    assert res.status_code == 401


async def test_public_routes_cannot_create_cases_or_view_jobs(client):
    # Public POST /cases does not exist (FastAPI returns 405 Method Not Allowed)
    res = await client.post("/cases", json={"name": "Test Case"})
    assert res.status_code == 405

    # Public GET /jobs/{id} does not exist (returns 404 Not Found)
    res = await client.get("/jobs/nonexistent-id")
    assert res.status_code == 404


async def test_admin_cases_workflow(client):
    # 1. Admin can list all cases
    res = await client.get("/admin/cases", headers=ADMIN_HEADERS)
    assert res.status_code == 200
    cases = res.json()
    assert len(cases) == 1
    assert cases[0]["slug"] == "jan-mat-v-state"

    # 2. Patch case to draft
    patch_res = await client.patch(
        "/admin/cases/jan-mat-v-state",
        headers=ADMIN_HEADERS,
        json={"review_state": "draft"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["review_state"] == "draft"

    # Public case list should now be empty because it is draft
    public_res = await client.get("/cases")
    assert public_res.status_code == 200
    assert len(public_res.json()) == 0

    # Public case view should return 404
    public_view = await client.get("/cases/jan-mat-v-state")
    assert public_view.status_code == 404

    # Admin preview still works
    admin_preview = await client.get("/admin/cases/jan-mat-v-state/preview", headers=ADMIN_HEADERS)
    assert admin_preview.status_code == 200
    assert admin_preview.json()["case"]["slug"] == "jan-mat-v-state"

    # 3. Patch back to published and featured
    repub_res = await client.patch(
        "/admin/cases/jan-mat-v-state",
        headers=ADMIN_HEADERS,
        json={"review_state": "published", "featured": True},
    )
    assert repub_res.status_code == 200
    assert repub_res.json()["review_state"] == "published"
    assert repub_res.json()["featured"] is True

    # Public case list now includes it
    public_res2 = await client.get("/cases")
    assert public_res2.status_code == 200
    assert len(public_res2.json()) == 1


async def test_startup_warning_on_default_admin_key(caplog):
    with caplog.at_level(logging.WARNING, logger="hetu.main"):
        async with lifespan(app):
            pass
    msg = "ADMIN_API_KEY is set to the default development value"
    assert any(msg in record.message for record in caplog.records)
