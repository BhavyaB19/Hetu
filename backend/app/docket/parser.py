"""Read a Supreme Court of India cause list into structured listings.

The PDF is a table laid out in four columns at fixed positions (on an A4 page 595 points
wide): serial number, case number, parties, advocates. Above each courtroom's matters sit
its heading (court number, the bench of judges, the start time). Headings repeat at the
top of every page, so a page break inside a courtroom continues the same block.

The parser works on lines of positioned words, which `read_pdf_lines` produces with
pdfplumber; tests build the same lines by hand without any PDF.
"""

import datetime as dt
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

PAGE_WIDTH = 595.0
# Left edges of the columns, in points on an A4 page.
CASE_COLUMN = 60.0
PARTY_COLUMN = 180.0
ADVOCATE_COLUMN = 420.0


@dataclass(frozen=True)
class Word:
    x: float
    text: str


Line = list[Word]


@dataclass
class ParsedListing:
    item_no: str
    case_number: str
    case_type: str
    court: str | None
    bench: list[str]
    time: str | None
    time_note: str | None
    heading: str | None
    petitioner: str
    respondent: str
    advocates: list[str]
    stage: str | None


@dataclass
class ParsedList:
    list_date: dt.date | None
    kind: str  # "daily" or "advance"
    listings: list[ParsedListing] = field(default_factory=list)


_DAILY_DATE = re.compile(r"CAUSE LIST FOR DATED\s*:\s*(\d{2})-(\d{2})-(\d{4})")
_ADVANCE_DATE = re.compile(r"TO BE LISTED ON\s*(\d{2})-(\d{2})-(\d{4})")
_COURT = re.compile(
    r"^(COURT NO\.?\s*:?\s*\d+|CHIEF JUSTICE'?S COURT|REGISTRAR COURT NO\.?\s*\d+)$", re.IGNORECASE
)
_TIME = re.compile(r"\(TIME\s*:\s*(\d{1,2}:\d{2}\s*[AP]M)\)", re.IGNORECASE)
_AFTER = re.compile(r"(ASSEMBLE|SIT) AFTER", re.IGNORECASE)
_SERIAL = re.compile(r"^\d{1,5}(\.\d{1,3})?$")
_CASE = re.compile(r"^(?P<type>.+?)\s*No\.?\s*(?P<num>\d[\d\-]*(?:/\d{4})?)", re.IGNORECASE)
_ADVOCATE = re.compile(r"([A-Z][A-Z .'&()/]*?[A-Z.)])\s*-\s*\d{2,5}")
_STAGE = re.compile(
    r"^(FOR (ADMISSION|ORDERS|FINAL DISPOSAL|JUDGMENT|HEARING|DIRECTIONS|COMPLIANCE)|\{[^}]+\})$",
    re.IGNORECASE,
)
# Text repeated at the top of every page; never part of a matter.
_FURNITURE = re.compile(
    r"^(SUPREME COURT OF INDIA|\[ ?IT WILL BE APPRECIATED|ON RECORD DO NOT SEEK|LISTED BEFORE ALL THE COURTS"
    r"|SNO\.|PETITIONER ?/ ?RESPONDENT|ADVOCATE$|MISCELLANEOUS HEARING|REGULAR HEARING|PART-[A-Z]$"
    r"|ADVANCE LIST|TENTATIVE LIST|NOTE ?:)",
    re.IGNORECASE,
)
# Lines in the party column that end the respondent's name and start the matter's notes.
_NOTE_START = (
    "{",
    "[",
    "IA NO",
    "FOR ",
    "WITH",
    "CONNECTED",
    "PART-HEARD",
    "(",
    "LAST LISTED",
    "TO BE ",
    "ONLY ",
)


def _text(words: Iterable[Word]) -> str:
    return " ".join(w.text for w in words).strip()


def _court_name(raw: str) -> str:
    upper = raw.upper()
    if "CHIEF JUSTICE" in upper:
        return "Chief Justice's Court"
    number = re.search(r"\d+", raw)
    if upper.startswith("REGISTRAR"):
        return f"Registrar Court {number.group()}" if number else "Registrar Court"
    return f"Court {number.group()}" if number else raw.title()


def _date(match: re.Match[str]) -> dt.date:
    day, month, year = (int(g) for g in match.groups())
    return dt.date(year, month, day)


@dataclass
class _Item:
    serial: str
    case: list[str] = field(default_factory=list)
    party: list[str] = field(default_factory=list)
    advocate: list[str] = field(default_factory=list)


def _columns(line: Line) -> tuple[str, str, str]:
    case = _text(w for w in line if CASE_COLUMN <= w.x < PARTY_COLUMN)
    party = _text(w for w in line if PARTY_COLUMN <= w.x < ADVOCATE_COLUMN)
    advocate = _text(w for w in line if w.x >= ADVOCATE_COLUMN)
    return case, party, advocate


def _parse_case(lines: list[str]) -> tuple[str, str] | None:
    match = _CASE.match(" ".join(lines))
    if not match:
        return None
    # "Connected" marks a matter heard with the item above it; it is not part of the case type.
    kind = re.sub(r"^CONNECTED\s+", "", re.sub(r"\s+", " ", match.group("type")).strip(), flags=re.IGNORECASE)
    return f"{kind} No. {match.group('num')}", kind


def _parties(lines: list[str]) -> tuple[str, str, str | None]:
    petitioner: list[str] = []
    respondent: list[str] = []
    stage: str | None = None
    side = petitioner
    for line in lines:
        upper = line.upper()
        if upper == "VERSUS":
            side = respondent
            continue
        if _STAGE.match(line) and stage is None:
            stage = line.strip("{}").strip()
        if upper.startswith(_NOTE_START):
            side = []  # everything after this is notes about the matter, not a party
            continue
        side.append(line)
    return " ".join(petitioner), " ".join(respondent), stage


def _advocates(lines: list[str]) -> list[str]:
    names: list[str] = []
    # A party arguing their own case is listed as "PETITIONER-IN-PERSON"; that is not an advocate.
    text = re.sub(r"(PETITIONER|RESPONDENT|APPELLANT)-IN-PERSON", " ", " ".join(lines))
    for match in _ADVOCATE.finditer(text):
        name = re.sub(r"\s+", " ", match.group(1)).strip(" ,")
        if not name or name in names:
            continue
        names.append(name)
    return names


def parse_lines(lines: Iterable[Line]) -> ParsedList:
    result = ParsedList(list_date=None, kind="daily")
    court: str | None = None
    bench: list[str] = []
    time: str | None = None
    time_note: str | None = None
    heading: str | None = None
    previous_was_judge = False
    item: _Item | None = None

    def close() -> None:
        nonlocal item
        if item is None:
            return
        parsed = _parse_case(item.case)
        if parsed:
            petitioner, respondent, stage = _parties(item.party)
            result.listings.append(
                ParsedListing(
                    item_no=item.serial,
                    case_number=parsed[0],
                    case_type=parsed[1],
                    court=court,
                    bench=list(bench),
                    time=time,
                    time_note=time_note,
                    heading=heading,
                    petitioner=petitioner,
                    respondent=respondent,
                    advocates=_advocates(item.advocate),
                    stage=stage,
                )
            )
        item = None

    for line in lines:
        if not line:
            continue
        text = _text(line)
        upper = text.upper()

        if match := _DAILY_DATE.search(upper):
            result.list_date = _date(match)
            continue
        if match := _ADVANCE_DATE.search(upper):
            result.list_date, result.kind = _date(match), "advance"
            continue

        # Item rows start with a serial number in the first column and a case in the second.
        first = line[0]
        if (
            first.x < CASE_COLUMN
            and _SERIAL.match(first.text)
            and any(CASE_COLUMN <= w.x < PARTY_COLUMN for w in line[1:])
        ):
            close()
            item = _Item(serial=first.text)
            case, party, advocate = _columns(line[1:])
            item.case.append(case)
            item.party.append(party) if party else None
            item.advocate.append(advocate) if advocate else None
            previous_was_judge = False
            continue

        if _COURT.match(text):
            name = _court_name(text)
            if name != court:  # the same heading on a new page continues the open matter
                close()
                court, bench, time, time_note, heading = name, [], None, None, None
            previous_was_judge = False
            continue
        if _FURNITURE.match(text):
            continue
        if upper.startswith("HON'BLE") or upper.endswith(", REGISTRAR"):
            close()
            if not previous_was_judge:
                bench, time, time_note = [], None, None  # a new bench sits in this court
            bench.append(re.sub(r"^HON'BLE\s+", "", text, flags=re.IGNORECASE).title())
            previous_was_judge = True
            continue
        previous_was_judge = False
        if match := _TIME.search(upper):
            time = match.group(1).replace("  ", " ")
            continue
        if _AFTER.search(upper) and court:
            time_note = "After the court's regular sitting"
            continue

        if item is not None:
            case, party, advocate = _columns(line)
            if case:
                item.case.append(case)
            if party:
                item.party.append(party)
            if advocate:
                item.advocate.append(advocate)
            continue

        # Category headings such as "[BAIL MATTERS]" between items.
        if text.startswith("[") and text.endswith("]") and len(text) < 80:
            heading = text.strip("[] ").title()

    close()
    return result


def read_pdf_lines(path: Path) -> Iterator[Line]:
    """Lines of words from every page, top to bottom, x scaled to an A4 width."""
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            scale = PAGE_WIDTH / float(page.width)
            rows: dict[int, list[Word]] = {}
            for w in page.extract_words(keep_blank_chars=False, use_text_flow=False):
                rows.setdefault(round(float(w["top"]) / 3), []).append(
                    Word(float(w["x0"]) * scale, w["text"])
                )
            for key in sorted(rows):
                yield sorted(rows[key], key=lambda w: w.x)
            page.flush_cache()
