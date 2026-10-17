import pytest
from pydantic import ValidationError

from app.pipeline import anonymize, dedupe
from app.schemas import CaseBundle, SourceDocument


def test_demo_fixture_is_valid(demo):
    assert demo.is_extracted
    assert demo.case.is_illustrative


def test_paraphrased_quote_is_rejected(demo):
    data = demo.model_dump(mode="json")
    data["media"][0]["claims"][0]["evidence"]["quote"] = "the attack came from an old feud"
    with pytest.raises(ValidationError, match="quote not found"):
        CaseBundle.model_validate(data)


def test_unknown_document_is_rejected(demo):
    data = demo.model_dump(mode="json")
    data["judgment"]["evidence"]["facts"]["document"] = "nope"
    with pytest.raises(ValidationError, match="unknown document"):
        CaseBundle.model_validate(data)


def test_quote_matching_ignores_whitespace_and_case(demo):
    data = demo.model_dump(mode="json")
    data["judgment"]["evidence"]["trigger"]["quote"] = "the  TRIGGER was\nthe parking dispute alone."
    CaseBundle.model_validate(data)


def test_dedupe_ignores_formatting():
    docs = [
        SourceDocument(key="a", source_type="media", source_name="x", text="Same  story.\n"),
        SourceDocument(key="b", source_type="media", source_name="y", text="same story."),
        SourceDocument(key="c", source_type="media", source_name="z", text="Different story."),
    ]
    assert [d.key for d in dedupe(docs)] == ["a", "c"]


def test_anonymize_redacts_contact_details_but_keeps_evidence_valid(demo):
    out = anonymize(demo, [])
    texts = {d.key: d.text for d in out.documents}
    assert "98765 43210" not in texts["public-4"]
    assert "[PHONE]" in texts["public-4"] and "[HANDLE]" in texts["public-4"]
    assert out.case.slug == demo.case.slug
