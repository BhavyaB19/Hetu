"""Perception Gap Index: how far media and public narratives drift from the court.

Each component is a number from 0 (matches the court) to 1 (fully diverges).
The index is 100 x the weighted sum. Every component carries a plain-language
explanation so the dashboard can show why the score is what it is.
"""

from dataclasses import dataclass

from app.schemas import CaseBundle, Sentiment

DEFAULT_WEIGHTS = {"factual": 0.30, "framing": 0.25, "sentiment": 0.25, "timeline": 0.20}

LABELS = {
    "factual": "Factual divergence",
    "framing": "Framing gap",
    "sentiment": "Public sentiment gap",
    "timeline": "Timeline distortion",
}

# How far each public sentiment sits from the court's final outcome (0 = aligned).
SENTIMENT_DISTANCE: dict[str, dict[Sentiment, float]] = {
    "conviction": {
        "support_victim": 0.0,
        "support_accused": 1.0,
        "neutral_uncertain": 0.5,
        "against_media_bias": 0.5,
    },
    "acquittal": {
        "support_victim": 1.0,
        "support_accused": 0.0,
        "neutral_uncertain": 0.5,
        "against_media_bias": 0.5,
    },
}


@dataclass
class Component:
    key: str
    value: float
    explanation: str


@dataclass
class GapScore:
    score: float
    components: list[Component]
    weights: dict[str, float]


def media_weights(bundle: CaseBundle) -> list[float]:
    """Share of articles that mention each judgment timeline event."""
    events = bundle.judgment.timeline if bundle.judgment else []
    if not bundle.media:
        return [0.0] * len(events)
    counts = [0] * len(events)
    for article in bundle.media:
        for index in set(article.events_mentioned):
            if 0 <= index < len(events):
                counts[index] += 1
    return [c / len(bundle.media) for c in counts]


def factual(bundle: CaseBundle) -> Component:
    claims = [c for m in bundle.media for c in m.claims]
    if not claims:
        return Component("factual", 0.0, "No factual claims were extracted from media coverage.")
    contradicted = sum(c.verdict == "contradicted" for c in claims)
    absent = sum(c.verdict == "absent" for c in claims)
    value = (contradicted + 0.5 * absent) / len(claims)
    return Component(
        "factual",
        value,
        f"{contradicted} of {len(claims)} media claims are contradicted by the judgment and "
        f"{absent} do not appear in it (absent claims count half).",
    )


def framing(bundle: CaseBundle) -> Component:
    if not bundle.media:
        return Component("framing", 0.0, "No media coverage to compare.")
    n = len(bundle.media)
    non_procedural = sum(m.framing != "procedural" for m in bundle.media) / n
    mean_tone = sum(abs(m.tone) for m in bundle.media) / n
    value = 0.5 * non_procedural + 0.5 * mean_tone
    return Component(
        "framing",
        value,
        f"The court reasons procedurally and neutrally. {round(non_procedural * 100)}% of articles "
        f"use a non-procedural frame, and their average emotional intensity is "
        f"{mean_tone:.2f} on a 0-1 scale.",
    )


def sentiment(bundle: CaseBundle) -> Component:
    direction = bundle.judgment.outcome_direction if bundle.judgment else "other"
    if not bundle.public:
        return Component("sentiment", 0.0, "No public reactions were collected.")
    if direction not in SENTIMENT_DISTANCE:
        return Component(
            "sentiment", 0.0, "The outcome is neither a conviction nor an acquittal, so it is not scored."
        )
    distance = SENTIMENT_DISTANCE[direction]
    value = sum(distance[r.sentiment] for r in bundle.public) / len(bundle.public)
    opposed = "support_accused" if direction == "conviction" else "support_victim"
    opposed_share = sum(r.sentiment == opposed for r in bundle.public) / len(bundle.public)
    return Component(
        "sentiment",
        value,
        f"The final outcome is a {direction}. {round(opposed_share * 100)}% of reactions take the "
        f"opposing side; neutral and media-bias reactions count half.",
    )


def timeline(bundle: CaseBundle) -> Component:
    events = bundle.judgment.timeline if bundle.judgment else []
    if not events or not bundle.media:
        return Component("timeline", 0.0, "Not enough timeline or media data to compare.")
    weights = media_weights(bundle)
    diffs = [abs(e.court_weight - w) for e, w in zip(events, weights, strict=True)]
    value = sum(diffs) / len(diffs)
    worst = max(range(len(events)), key=lambda i: diffs[i])
    return Component(
        "timeline",
        value,
        f"Average gap between how much the court and the media emphasise each event. Largest gap: "
        f'"{events[worst].label}" (court {events[worst].court_weight:.0%}, '
        f"media {weights[worst]:.0%} of articles).",
    )


def perception_gap(bundle: CaseBundle, weights: dict[str, float] | None = None) -> GapScore:
    weights = weights or DEFAULT_WEIGHTS
    total = sum(weights.values())
    components = [factual(bundle), framing(bundle), sentiment(bundle), timeline(bundle)]
    score = 100 * sum(weights[c.key] * c.value for c in components) / total
    return GapScore(score=round(score, 1), components=components, weights=weights)
