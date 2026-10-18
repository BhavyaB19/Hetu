"""Background case jobs and their API, with collection and processing faked."""

import asyncio
import logging

import pytest
from httpx import ASGITransport, AsyncClient

from app.agents.base import AgentError
from app.main import app
from app.services import jobs

ADMIN_HEADERS = {"X-Admin-Key": "hetu-dev-admin-key"}


@pytest.fixture
async def api():
    jobs._jobs.clear()
    jobs.install_log_capture()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers=ADMIN_HEADERS
    ) as client:
        yield client


async def wait_until_finished(api, job_id: str) -> dict:
    for _ in range(100):
        job = (await api.get(f"/admin/jobs/{job_id}")).json()
        if job["status"] in ("done", "failed"):
            return job
        await asyncio.sleep(0.01)
    raise AssertionError("job did not finish")


async def test_job_runs_collection_then_pipeline(api, monkeypatch, tmp_path):
    release = asyncio.Event()

    async def fake_collect(query):
        logging.getLogger("hetu.agents.media").info("Found 3 news articles; reading them in parallel")
        await release.wait()
        return None, tmp_path / "case.json"

    async def fake_run(path, force_extract):
        logging.getLogger("hetu.pipeline").info("Saved state-v-example: Perception Gap Index 40.0")
        return "state-v-example"

    monkeypatch.setattr(jobs, "collect", fake_collect)
    monkeypatch.setattr(jobs, "run", fake_run)

    res = await api.post("/admin/cases", json={"name": "State v. Example", "court": "Delhi High Court"})
    assert res.status_code == 202
    job = res.json()
    assert job["status"] == "collecting" and job["name"] == "State v. Example"

    # Starting the same case again while it runs returns the same job.
    again = await api.post("/admin/cases", json={"name": "state v example"})
    assert again.json()["id"] == job["id"]

    release.set()
    finished = await wait_until_finished(api, job["id"])
    assert finished["status"] == "done" and finished["slug"] == "state-v-example"
    messages = [e["message"] for e in finished["events"]]
    assert "Found 3 news articles; reading them in parallel" in messages
    assert messages[-1] == "Done. The case is ready."


async def test_failed_collection_is_reported(api, monkeypatch):
    async def failing_collect(query):
        raise AgentError("No judgment found on Indian Kanoon for 'Nothing v. Nobody'.")

    monkeypatch.setattr(jobs, "collect", failing_collect)
    job = (await api.post("/admin/cases", json={"name": "Nothing v. Nobody"})).json()
    finished = await wait_until_finished(api, job["id"])
    assert finished["status"] == "failed"
    assert "No judgment found" in finished["error"]
    assert finished["events"][-1]["level"] == "error"


async def test_logs_from_other_jobs_do_not_mix(api, monkeypatch, tmp_path):
    async def fake_collect(query):
        logging.getLogger("hetu.agents").info(f"working on {query.name}")
        await asyncio.sleep(0.01)
        return None, tmp_path / "x.json"

    async def fake_run(path, force_extract):
        return "slug"

    monkeypatch.setattr(jobs, "collect", fake_collect)
    monkeypatch.setattr(jobs, "run", fake_run)
    a = (await api.post("/admin/cases", json={"name": "Case Alpha"})).json()
    b = (await api.post("/admin/cases", json={"name": "Case Beta"})).json()
    a_msgs = [e["message"] for e in (await wait_until_finished(api, a["id"]))["events"]]
    b_msgs = [e["message"] for e in (await wait_until_finished(api, b["id"]))["events"]]
    assert "working on Case Alpha" in a_msgs and "working on Case Beta" not in a_msgs
    assert "working on Case Beta" in b_msgs and "working on Case Alpha" not in b_msgs


async def test_validation_and_unknown_job(api):
    assert (await api.post("/admin/cases", json={"name": "ab"})).status_code == 422
    assert (await api.post("/admin/cases", json={"name": "!!!!"})).status_code == 422
    assert (await api.get("/admin/jobs/nope")).status_code == 404
