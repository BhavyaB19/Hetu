"""Docket refresh and the public docket API, with a fake court and no network or PDFs."""

import datetime as dt

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.docket_repository import case_key
from app.db.session import SessionLocal
from app.docket.parser import ParsedList, ParsedListing
from app.docket.sci import PublishedList
from app.main import app
from app.services import docket

pytestmark = pytest.mark.usefixtures("clean_database")

TODAY = dt.date(2026, 10, 26)
ADMIN = {"X-Admin-Key": "hetu-dev-admin-key"}


def matter(
    item: str, number: str, *, court: str | None = "Court 2", bench: int = 2, **extra
) -> ParsedListing:
    return ParsedListing(
        item_no=item,
        case_number=number,
        case_type=number.split(" No.")[0],
        court=court,
        bench=[f"Mr. Justice {n}" for n in ("Rao", "Iyer", "Sen", "Bose", "Das")[:bench]],
        time="10:30 AM" if court else None,
        time_note=None,
        heading=None,
        petitioner=extra.get("petitioner", "RAVI KUMAR VERMA"),
        respondent=extra.get("respondent", "STATE OF ILLUSTRATIA"),
        advocates=["ASHA RAO"],
        stage=None,
    )


class FakeCourt:
    """Publishes lists from a dict of url -> (bytes, ParsedList)."""

    def __init__(self, lists: dict[PublishedList, tuple[bytes, ParsedList]]):
        self.lists = lists
        self.downloads = 0

    async def published_lists(self) -> list[PublishedList]:
        return list(self.lists)

    async def download(self, url: str) -> bytes:
        self.downloads += 1
        return next(data for p, (data, _) in self.lists.items() if p.url == url)

    def parse(self, data: bytes) -> ParsedList:
        return next(parsed for raw, parsed in self.lists.values() if raw == data)


def published(date: dt.date, kind: str, part: str) -> PublishedList:
    prefix = "advance/" if kind == "advance" else ""
    return PublishedList(f"https://api.sci.gov.in/jonew/cl/{prefix}{date}/{part}.pdf", date, kind, part)


def court_with(**lists: tuple[bytes, ParsedList]) -> FakeCourt:
    tomorrow = TODAY + dt.timedelta(days=1)
    entries = {
        "daily": published(TODAY, "daily", "M_J_1"),
        "advance_today": published(TODAY, "advance", "M_J"),
        "advance_tomorrow": published(tomorrow, "advance", "M_J"),
    }
    return FakeCourt({entries[name]: value for name, value in lists.items()})


def standard_court() -> FakeCourt:
    tomorrow = TODAY + dt.timedelta(days=1)
    return court_with(
        daily=(
            b"daily-1",
            ParsedList(
                TODAY,
                "daily",
                [
                    matter("1", "SLP(Crl) No. 1234/2025"),
                    matter("2", "W.P.(C) No. 77/2024", court="Court 4", bench=5, respondent="UNION OF INDIA"),
                ],
            ),
        ),
        advance_today=(
            b"adv-today",
            ParsedList(TODAY, "advance", [matter("9", "C.A. No. 1/2020", court=None)]),
        ),
        advance_tomorrow=(
            b"adv-tomorrow",
            ParsedList(tomorrow, "advance", [matter("3", "SLP(Crl) No. 1234/2025", court=None, bench=0)]),
        ),
    )


async def refresh(court: FakeCourt) -> docket.RefreshReport:
    async with SessionLocal() as session:
        return await docket.refresh(session, court, today=TODAY, parse=court.parse)


async def test_refresh_stores_anonymised_listings_and_is_idempotent():
    court = standard_court()
    first = await refresh(court)
    assert (first.updated, first.unchanged, first.failed) == (3, 0, 0)
    assert first.listings == 4

    second = await refresh(court)
    assert (second.updated, second.unchanged) == (0, 3)

    from sqlalchemy import func, select

    from app.db import models

    async with SessionLocal() as session:
        assert await session.scalar(select(func.count()).select_from(models.Listing)) == 4
        petitioners = set(await session.scalars(select(models.Listing.petitioner)))
    # The private petitioner was never stored by name.
    assert petitioners == {"Petitioner (private individual)"}


async def test_changed_list_replaces_its_listings():
    court = standard_court()
    await refresh(court)
    daily = next(p for p in court.lists if p.kind == "daily")
    court.lists[daily] = (b"daily-2", ParsedList(TODAY, "daily", [matter("1", "SLP(Crl) No. 1234/2025")]))
    report = await refresh(court)
    assert report.updated == 1

    from sqlalchemy import func, select

    from app.db import models

    async with SessionLocal() as session:
        count = await session.scalar(
            select(func.count()).select_from(models.Listing).where(models.Listing.kind == "daily")
        )
    assert count == 1


async def test_one_bad_file_does_not_stop_the_refresh():
    court = standard_court()

    def parse(data: bytes) -> ParsedList:
        if data == b"adv-today":
            raise ValueError("unreadable")
        return court.parse(data)

    async with SessionLocal() as session:
        report = await docket.refresh(session, court, today=TODAY, parse=parse)
    assert (report.updated, report.failed) == (2, 1)


@pytest.fixture
async def client(monkeypatch):
    await refresh(standard_court())
    monkeypatch.setattr("app.api.docket.today_ist", lambda: TODAY)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_docket_shows_the_daily_list_over_the_advance_list(client):
    res = await client.get("/docket")
    assert res.status_code == 200
    body = res.json()
    # Today has a daily list, so today's advance listing is hidden.
    assert [(d["list_date"], d["tentative"], d["matters"]) for d in body["days"]] == [
        ("2026-10-26", False, 2),
        ("2026-10-27", True, 1),
    ]
    assert {r["case_number"] for r in body["results"]} == {"SLP(Crl) No. 1234/2025", "W.P.(C) No. 77/2024"}
    assert body["results"][0]["source_url"].startswith("https://api.sci.gov.in/")


async def test_docket_search_by_case_number_finds_every_listing(client):
    res = await client.get("/docket", params={"q": "slp crl 1234/2025"})
    body = res.json()
    assert body["total"] == 2
    assert [r["list_date"] for r in body["results"]] == ["2026-10-26", "2026-10-27"]
    assert body["results"][1]["tentative"] is True


async def test_docket_filters(client):
    assert (await client.get("/docket", params={"criminal": True})).json()["total"] == 1
    notable = (await client.get("/docket", params={"notable": True})).json()["results"]
    assert [r["case_number"] for r in notable] == ["W.P.(C) No. 77/2024"]
    assert (await client.get("/docket", params={"court": "Court 4"})).json()["total"] == 1


async def test_highlights_show_tracked_matters_and_larger_benches(client):
    res = await client.post(
        "/admin/docket/tracked",
        json={"case_number": "SLP(Crl) No. 1234/2025", "title": "The illustrative bail appeal"},
        headers=ADMIN,
    )
    assert res.status_code == 201
    assert res.json()["next_listing"]["list_date"] == "2026-10-26"

    body = (await client.get("/docket/highlights")).json()
    assert [t["title"] for t in body["tracked"]] == ["The illustrative bail appeal"]
    assert [n["case_number"] for n in body["notable"]] == ["W.P.(C) No. 77/2024"]
    assert body["next_day"]["matters"] == 2


async def test_docket_admin_routes_need_the_key(client):
    assert (await client.post("/admin/docket/refresh")).status_code == 401
    assert (await client.post("/admin/docket/tracked", json={})).status_code == 401


def test_case_keys_match_however_the_number_is_written():
    assert case_key("SLP(Crl) No. 7857/2022") == case_key("slp crl 7857/2022") == "slpcrl78572022"
    assert case_key("Diary No. 50264-2026") == "diary502642026"
