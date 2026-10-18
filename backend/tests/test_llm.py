"""Groq client, strict-schema conversion and provider selection (no network)."""

import json

import groq
import httpx
import pytest

from app.core.config import Settings
from app.schemas.extraction import LLMJudgment, LLMMedia, LLMPublic
from app.services.anonymizer import Person
from app.services.llm import ClaudeLLM, ExtractionError, GroqLLM, make_llm, strict_schema


def walk(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


@pytest.mark.parametrize("model", [LLMJudgment, LLMMedia, LLMPublic])
def test_strict_schema_meets_groq_rules(model):
    schema = strict_schema(model)
    for node in walk(schema):
        assert "title" not in node and "default" not in node
        if "properties" in node:
            assert node["required"] == list(node["properties"])
            assert node["additionalProperties"] is False
    # Refs still point at definitions that exist.
    refs = {n["$ref"].split("/")[-1] for n in walk(schema) if "$ref" in n}
    assert refs <= set(schema.get("$defs", {}))


def test_optional_fields_stay_nullable():
    claim = strict_schema(LLMMedia)["$defs"]["LLMClaim"]["properties"]["judgment_quote"]
    assert {"type": "null"} in claim["anyOf"]


def completion(content: str, finish_reason: str = "stop") -> dict:
    return {
        "id": "c1",
        "object": "chat.completion",
        "created": 0,
        "model": "openai/gpt-oss-120b",
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": finish_reason}
        ],
    }


def groq_with(handler) -> tuple[GroqLLM, list[dict]]:
    sent: list[dict] = []

    def record(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return handler(request)

    llm = GroqLLM("gsk-test", "openai/gpt-oss-120b")
    llm._client = groq.AsyncGroq(
        api_key="gsk-test",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(record)),
    )
    return llm, sent


PERSON = {"name": "Ravi", "role": "accused", "aliases": []}


async def test_groq_parses_strict_json():
    body = json.dumps(
        {"people": [PERSON], "reactions": [{"key": "p1", "sentiment": "neutral_uncertain", "themes": ["x"]}]}
    )
    llm, sent = groq_with(lambda r: httpx.Response(200, json=completion(body)))
    result = await llm.parse("system", "prompt", LLMPublic)
    assert result.people == [Person(name="Ravi", role="accused")]
    fmt = sent[0]["response_format"]
    assert fmt["type"] == "json_schema" and fmt["json_schema"]["strict"] is True
    assert sent[0]["messages"][0] == {"role": "system", "content": "system"}


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (httpx.Response(200, json=completion("{}", finish_reason="length")), "cut off"),
        (httpx.Response(200, json=completion("not json")), "does not match"),
        (
            httpx.Response(200, json=completion(json.dumps({"people": [], "reactions": [{"key": "p1"}]}))),
            "does not match",
        ),
        (httpx.Response(413, json={"error": {"message": "Request too large"}}), "too large"),
        (httpx.Response(429, json={"error": {"message": "TPM exceeded"}}), "rate limit"),
        (httpx.Response(401, json={"error": {"message": "Invalid API Key"}}), "401"),
    ],
)
async def test_groq_failures_become_extraction_errors(response, message):
    llm, _ = groq_with(lambda r: response)
    with pytest.raises(ExtractionError, match=message):
        await llm.parse("system", "prompt", LLMPublic)


def test_provider_selection():
    assert make_llm(Settings(_env_file=None, llm_provider="groq", groq_api_key="gsk")).__class__ is GroqLLM
    assert (
        make_llm(Settings(_env_file=None, llm_provider="groq", groq_api_key="", anthropic_api_key="sk"))
        is None
    )
    assert make_llm(Settings(_env_file=None, anthropic_api_key="sk")).__class__ is ClaudeLLM
    assert make_llm(Settings(_env_file=None, anthropic_api_key="")) is None


# ---------- OpenAI ----------


def responses_body(content: list[dict], status: str = "completed", incomplete: dict | None = None) -> dict:
    return {
        "id": "resp_1",
        "object": "response",
        "created_at": 0,
        "model": "gpt-6.1-sol",
        "status": status,
        "incomplete_details": incomplete,
        "output": [
            {"type": "message", "id": "msg_1", "status": "completed", "role": "assistant", "content": content}
        ],
        "parallel_tool_calls": True,
        "tool_choice": "auto",
        "tools": [],
    }


def openai_with(handler):
    import openai

    from app.services.llm import OpenAILLM

    sent: list[dict] = []

    def record(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return handler(request)

    llm = OpenAILLM("sk-test", "gpt-6.1-sol")
    llm._client = openai.AsyncOpenAI(
        api_key="sk-test", max_retries=0, http_client=httpx.AsyncClient(transport=httpx.MockTransport(record))
    )
    return llm, sent


async def test_openai_parses_strict_json():
    body = json.dumps(
        {"people": [], "reactions": [{"key": "p1", "sentiment": "support_victim", "themes": ["x"]}]}
    )
    llm, sent = openai_with(
        lambda r: httpx.Response(
            200, json=responses_body([{"type": "output_text", "text": body, "annotations": []}])
        )
    )
    result = await llm.parse("system", "prompt", LLMPublic)
    assert result.reactions[0].sentiment == "support_victim"
    fmt = sent[0]["text"]["format"]
    assert fmt["type"] == "json_schema" and fmt["strict"] is True
    assert sent[0]["instructions"] == "system" and sent[0]["input"] == "prompt"


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (httpx.Response(200, json=responses_body([{"type": "refusal", "refusal": "No."}])), "declined"),
        (
            httpx.Response(
                200,
                json=responses_body([], status="incomplete", incomplete={"reason": "max_output_tokens"}),
            ),
            "cut off",
        ),
        (httpx.Response(429, json={"error": {"message": "Rate limit"}}), "rate limit"),
        (httpx.Response(400, json={"error": {"message": "Invalid schema"}}), "400"),
    ],
)
async def test_openai_failures_become_extraction_errors(response, message):
    llm, _ = openai_with(lambda r: response)
    with pytest.raises(ExtractionError, match=message):
        await llm.parse("system", "prompt", LLMPublic)


def test_openai_provider_selection():
    from app.services.llm import OpenAILLM

    assert isinstance(
        make_llm(Settings(_env_file=None, llm_provider="openai", openai_api_key="sk")), OpenAILLM
    )
    # Only the chosen provider's key counts: other providers' keys are ignored.
    assert (
        make_llm(Settings(_env_file=None, llm_provider="openai", groq_api_key="gsk", anthropic_api_key="sk"))
        is None
    )


def test_request_timeouts():
    free = make_llm(Settings(_env_file=None, llm_provider="groq", groq_api_key="gsk"))
    paid = make_llm(Settings(_env_file=None, llm_provider="groq", groq_api_key="gsk", groq_plan="developer"))
    oa = make_llm(Settings(_env_file=None, llm_provider="openai", openai_api_key="sk"))
    assert free._client.timeout == 120
    assert paid._client.timeout == 600 and oa._client.timeout == 600


async def test_network_failures_become_extraction_errors():
    def unreachable(request):
        raise httpx.ConnectTimeout("timed out")

    llm, _ = groq_with(unreachable)
    with pytest.raises(ExtractionError, match="Could not get a response from Groq"):
        await llm.parse("system", "prompt", LLMPublic)
    llm, _ = openai_with(unreachable)
    with pytest.raises(ExtractionError, match="Could not get a response from OpenAI"):
        await llm.parse("system", "prompt", LLMPublic)
