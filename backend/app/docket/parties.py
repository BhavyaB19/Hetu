"""Party names in cause lists, anonymised before anything is stored.

Cause lists name every party. Hetu keeps institutions (the State, government bodies,
companies, courts, banks) as published and replaces private individuals with their role,
as AGENTS.md rule 4 requires. When a name cannot be recognised as an institution it is
treated as a person: wrongly hiding a company is harmless, wrongly showing a person is not.
"""

import re

# Words that only appear in names of institutions, never of private individuals.
INSTITUTION_WORDS = (
    "STATE",
    "UNION OF INDIA",
    "GOVERNMENT",
    "GOVT",
    "GOVERNOR",
    "MINISTRY",
    "DEPARTMENT",
    "DIRECTORATE",
    "DIRECTOR",
    "COMMISSIONER",
    "COMMISSION",
    "COLLECTOR",
    "SECRETARY",
    "OFFICER",
    "REGISTRAR",
    "AUTHORITY",
    "BOARD",
    "COUNCIL",
    "CORPORATION",
    "MUNICIPAL",
    "PANCHAYAT",
    "POLICE",
    "C.B.I",
    "CENTRAL BUREAU",
    "ENFORCEMENT",
    "INCOME TAX",
    "CUSTOMS",
    "HIGH COURT",
    "SUPREME COURT",
    "TRIBUNAL",
    "UNIVERSITY",
    "COLLEGE",
    "INSTITUTE",
    "SCHOOL",
    "HOSPITAL",
    "BANK",
    "INSURANCE",
    "LIMITED",
    "LTD",
    "PVT",
    "PRIVATE LIMITED",
    "LLP",
    "COMPANY",
    "INDUSTRIES",
    "ENTERPRISES",
    "TRUST",
    "SOCIETY",
    "ASSOCIATION",
    "FEDERATION",
    "FOUNDATION",
    "SANGH",
    "UNION",
    "PARTY",
    "ELECTION",
    "RAILWAY",
    "ARMY",
    "NAVY",
    "AIR FORCE",
    "COAST GUARD",
    "NATIONAL",
    "INDIA",
)

_INSTITUTION = re.compile(r"(?<![A-Z])(" + "|".join(re.escape(w) for w in INSTITUTION_WORDS) + r")(?![A-Z])")
# "AND ANR." / "AND ORS." and similar tails say how many more parties there are.
_TAIL = re.compile(r"\s+(AND|&)\s+(ANR|ORS|OTHERS|ANOTHER)\.?\s*$", re.IGNORECASE)


def is_institution(name: str) -> bool:
    return bool(_INSTITUTION.search(name.upper()))


def anonymise_party(name: str, role: str) -> str:
    """The party as Hetu shows it: institutions as published, people as their role."""
    clean = re.sub(r"\s+", " ", name).strip(" ,.")
    if not clean:
        return ""
    tail_match = _TAIL.search(clean)
    tail = (
        " and others"
        if tail_match and tail_match.group(2).upper().startswith(("ORS", "OTH"))
        else (" and another" if tail_match else "")
    )
    head = _TAIL.sub("", clean) if tail_match else clean
    if is_institution(head):
        return clean
    return f"{role} (private individual){tail}"
