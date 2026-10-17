import pytest

from app.services.anonymizer import Anonymizer, Person


@pytest.fixture
def anon() -> Anonymizer:
    a = Anonymizer()
    a.register(Person(name="Ravi Kumar", role="accused", aliases=["Ravi"]))
    a.register(Person(name="Sunita Devi", role="victim"))
    a.register(Person(name="Mohan Lal", role="witness"))
    return a


def test_full_names_and_aliases_get_the_same_placeholder(anon):
    out = anon.text("Ravi Kumar argued with Sunita Devi. Later, Ravi left.")
    assert out == "[ACCUSED_1] argued with [VICTIM_1]. Later, [ACCUSED_1] left."


def test_case_and_possessives(anon):
    assert anon.text("RAVI KUMAR's motorcycle") == "[ACCUSED_1]'s motorcycle"


def test_names_inside_other_words_are_left_alone(anon):
    # "Ravi" must not be replaced inside "Ravindra"; "Mohan Lal" not inside "Mohan Lalwani".
    assert anon.text("Ravindra met Mohan Lalwani") == "Ravindra met Mohan Lalwani"


def test_placeholders_are_stable_across_registrations():
    a = Anonymizer()
    first = a.register(Person(name="Asha", role="witness"))
    again = a.register(Person(name="ASHA", role="witness", aliases=["Asha Rani"]))
    assert first == again == "[WITNESS_1]"
    assert a.text("Asha Rani testified") == "[WITNESS_1] testified"


def test_roles_are_numbered_separately():
    a = Anonymizer()
    assert a.register(Person(name="Aman", role="witness")) == "[WITNESS_1]"
    assert a.register(Person(name="Bela", role="witness")) == "[WITNESS_2]"
    assert a.register(Person(name="Chotu", role="minor")) == "[MINOR_1]"


@pytest.mark.parametrize(
    "raw",
    [
        "call 9876543210 now",
        "call 98765 43210 now",
        "call +91 98765-43210 now",
        "call +919876543210 now",
        "call 09876543210 now",
    ],
)
def test_phone_numbers(raw):
    assert Anonymizer().text(raw) == "call [PHONE] now"


def test_contact_details():
    out = Anonymizer().text("Mail me at ravi.k+news@example.co.in or DM @ravi_k99. Aadhaar 1234 5678 9012.")
    assert out == "Mail me at [EMAIL] or DM [HANDLE]. Aadhaar [AADHAAR]."


@pytest.mark.parametrize(
    "text",
    [
        "Decided on 10 February 2023 under Section 302 IPC",
        "Criminal Appeal No. 112 of 2021",
        "a fine of Rs. 50,000",
        "FIR dated 2019-03-15",
        "case number 1234567890123",
    ],
)
def test_legal_references_survive(text):
    assert Anonymizer().text(text) == text


def test_deep_skips_identifier_fields(anon):
    data = {"key": "Ravi Kumar", "text": "Ravi Kumar", "items": [{"quote": "Sunita Devi"}]}
    out = anon.deep(data, skip=frozenset({"key"}))
    assert out == {"key": "Ravi Kumar", "text": "[ACCUSED_1]", "items": [{"quote": "[VICTIM_1]"}]}
