"""Cause-list parsing, party anonymisation and link discovery. All names here are fictional."""

import datetime as dt

from app.docket.parser import Word, parse_lines
from app.docket.parties import anonymise_party, is_institution
from app.docket.sci import find_lists


def line(*cells: tuple[float, str]) -> list[Word]:
    """A line of words; each cell is (x position, text) and is split into words."""
    words: list[Word] = []
    for x, text in cells:
        for i, part in enumerate(text.split()):
            words.append(Word(x + i * 30, part))
    return words


HEADER = [
    line((233, "SUPREME COURT OF INDIA")),
    line((161, "[ IT WILL BE APPRECIATED IF THE LEARNED ADVOCATES")),
    line((195, "DAILY CAUSE LIST FOR DATED : 26-10-2026")),
]


def daily_list() -> list[list[Word]]:
    return [
        *HEADER,
        line((240, "CHIEF JUSTICE'S COURT")),
        line((227, "HON'BLE THE CHIEF JUSTICE")),
        line((198, "HON'BLE MR. JUSTICE ARJUN MEHRA")),
        line((255, "(TIME : 10:30 AM)")),
        line((233, "MISCELLANEOUS HEARING")),
        line((43, "SNo."), (69, "Case No."), (185, "Petitioner / Respondent")),
        line(
            (43, "1"),
            (69, "SLP(Crl) No. 1234/2025"),
            (185, "RAVI KUMAR VERMA"),
            (426, "ASHA RAO- 1111 [P-1]"),
        ),
        line((69, "II"), (185, "Versus")),
        line((185, "STATE OF ILLUSTRATIA"), (426, "VIKRAM SEN- 2222 [R-1]")),
        line((185, "FOR ADMISSION")),
        line((185, "IA No. 9/2025 - EXEMPTION FROM FILING O.T.")),
        # A page break: the same court's heading repeats and the matter continues.
        *HEADER,
        line((240, "CHIEF JUSTICE'S COURT")),
        line(
            (43, "2"), (69, "Diary No. 5555-2026"), (185, "MEERA DAS AND ANR."), (426, "PETITIONER-IN-PERSON")
        ),
        line((69, "X"), (185, "Versus")),
        line((185, "UNION OF INDIA AND ORS."), (426, "NIKHIL ROY- 3333")),
        line((280, "COURT NO. : 4")),
        line((198, "HON'BLE MR. JUSTICE ONE")),
        line((198, "HON'BLE MR. JUSTICE TWO")),
        line((198, "HON'BLE MR. JUSTICE THREE")),
        line((198, "HON'BLE MR. JUSTICE FOUR")),
        line((198, "HON'BLE MR. JUSTICE FIVE")),
        line((255, "(TIME : 10:45 AM)")),
        line(
            (43, "1"), (69, "W.P.(C) No. 77/2024"), (185, "ACME TRADERS PVT. LTD."), (426, "ASHA RAO- 1111")
        ),
        line((185, "Versus")),
        line((185, "ELECTION COMMISSION OF INDIA")),
        line((43, "1.1"), (69, "Connected W.P.(C) No. 78/2024"), (185, "SUNITA DEVI")),
        line((185, "Versus")),
        line((185, "ELECTION COMMISSION OF INDIA")),
    ]


def test_daily_list_reads_courts_benches_times_and_matters():
    parsed = parse_lines(daily_list())
    assert parsed.kind == "daily"
    assert parsed.list_date == dt.date(2026, 10, 26)
    assert [m.item_no for m in parsed.listings] == ["1", "2", "1", "1.1"]

    first, second, third, connected = parsed.listings
    assert first.court == "Chief Justice's Court"
    assert first.bench == ["The Chief Justice", "Mr. Justice Arjun Mehra"]
    assert first.time == "10:30 AM"
    assert first.case_number == "SLP(Crl) No. 1234/2025"
    assert first.case_type == "SLP(Crl)"
    assert first.petitioner == "RAVI KUMAR VERMA"
    assert first.respondent == "STATE OF ILLUSTRATIA"  # the IA notes are not part of the party
    assert first.stage == "FOR ADMISSION"
    assert first.advocates == ["ASHA RAO", "VIKRAM SEN"]

    # The repeated page heading continued the same court and bench.
    assert second.court == "Chief Justice's Court"
    assert second.bench == first.bench
    assert second.case_number == "Diary No. 5555-2026"
    assert second.advocates == ["NIKHIL ROY"]  # a party in person is not an advocate

    assert third.court == "Court 4"
    assert len(third.bench) == 5
    assert third.time == "10:45 AM"
    assert connected.case_type == "W.P.(C)"  # "Connected" is dropped


def test_advance_list_has_a_date_but_no_court():
    parsed = parse_lines(
        [
            line((180, "MISCELLANEOUS MATTERS TO BE LISTED ON 27-10-2026")),
            line((180, "ADVANCE LIST - AL/158/2026")),
            line((43, "1"), (69, "SLP(C) No. 4118/2019"), (185, "NEW HORIZON LIMITED")),
            line((185, "Versus")),
            line((185, "KAMAL NATH SHARMA")),
        ]
    )
    assert parsed.kind == "advance"
    assert parsed.list_date == dt.date(2026, 10, 27)
    assert parsed.listings[0].court is None
    assert parsed.listings[0].bench == []


def test_private_parties_are_replaced_and_institutions_kept():
    assert anonymise_party("RAVI KUMAR VERMA", "Petitioner") == "Petitioner (private individual)"
    assert (
        anonymise_party("MEERA DAS AND ANR.", "Petitioner") == "Petitioner (private individual) and another"
    )
    assert (
        anonymise_party("SUNITA DEVI AND ORS.", "Respondent") == "Respondent (private individual) and others"
    )
    assert anonymise_party("STATE OF U.P.", "Respondent") == "STATE OF U.P"
    assert anonymise_party("UNION OF INDIA AND ORS.", "Respondent") == "UNION OF INDIA AND ORS"
    assert anonymise_party("ACME TRADERS PVT. LTD.", "Petitioner") == "ACME TRADERS PVT. LTD"
    assert anonymise_party("", "Respondent") == ""
    # Words inside a name are not mistaken for an institution.
    assert not is_institution("STATESMAN BANKOLE")


def test_cause_list_links_are_found_once_each():
    html = """
      <a href="https://api.sci.gov.in/jonew/cl/2026-10-26/M_J_1.pdf">Main</a>
      <a href="https://api.sci.gov.in/jonew/cl/2026-10-26/M_J_1.pdf">Main again</a>
      <a href="https://api.sci.gov.in/jonew/cl/advance/2026-10-27/M_J.pdf">Advance</a>
      <a href="https://example.com/other.pdf">Not a list</a>
    """
    found = find_lists(html)
    assert [(p.list_date.isoformat(), p.kind, p.part) for p in found] == [
        ("2026-10-26", "daily", "M_J_1"),
        ("2026-10-27", "advance", "M_J"),
    ]


def test_candidate_addresses_cover_the_coming_days_and_skip_sundays():
    from app.docket.sci import candidate_lists

    friday = dt.date(2026, 10, 23)
    found = candidate_lists(friday)
    daily_days = {p.list_date for p in found if p.kind == "daily"}
    assert daily_days == {friday, dt.date(2026, 10, 24)}  # Sunday the 25th is skipped
    assert found[0].url == "https://api.sci.gov.in/jonew/cl/2026-10-23/M_J_1.pdf"
    advance = [p for p in found if p.kind == "advance"]
    assert advance[0].url == "https://api.sci.gov.in/jonew/cl/advance/2026-10-24/M_J.pdf"
    assert all(p.list_date.weekday() != 6 for p in found)
