import pytest

from app.scoring import DEFAULT_WEIGHTS, media_weights, perception_gap


def test_demo_components(demo):
    gap = perception_gap(demo)
    values = {c.key: c.value for c in gap.components}
    # 13 claims: 5 contradicted, 2 absent -> (5 + 1) / 13
    assert values["factual"] == pytest.approx(6 / 13)
    # 3 of 5 articles non-procedural; mean |tone| = 2.0 / 5
    assert values["framing"] == pytest.approx(0.5 * 0.6 + 0.5 * 0.4)
    # conviction: 2 support accused (1.0), 3 neutral + 4 media-bias (0.5 each), of 16
    assert values["sentiment"] == pytest.approx(5.5 / 16)
    assert values["timeline"] == pytest.approx((0.2 + 0.3 + 0.2 + 0.35 + 0.6) / 5)


def test_score_is_weighted_sum(demo):
    gap = perception_gap(demo)
    expected = 100 * sum(DEFAULT_WEIGHTS[c.key] * c.value for c in gap.components)
    assert gap.score == pytest.approx(expected, abs=0.05)
    assert 0 <= gap.score <= 100


def test_media_weights(demo):
    assert media_weights(demo) == pytest.approx([0.8, 0.0, 0.6, 0.4, 0.4])


def test_media_matching_the_court_scores_zero(demo):
    for article in demo.media:
        article.framing = "procedural"
        article.tone = 0.0
        for claim in article.claims:
            claim.verdict = "supported"
    for reaction in demo.public:
        reaction.sentiment = "support_victim"
    values = {c.key: c.value for c in perception_gap(demo).components}
    assert values["factual"] == values["framing"] == values["sentiment"] == 0


def test_acquittal_flips_sentiment(demo):
    demo.judgment.outcome_direction = "acquittal"
    sentiment = next(c for c in perception_gap(demo).components if c.key == "sentiment")
    # 7 support victim (1.0) + 7 neutral/media-bias (0.5) of 16
    assert sentiment.value == pytest.approx(10.5 / 16)


def test_empty_case_scores_zero(demo):
    demo.media, demo.public = [], []
    assert perception_gap(demo).score == 0


def test_custom_weights_are_normalized(demo):
    only_factual = perception_gap(demo, {"factual": 2, "framing": 0, "sentiment": 0, "timeline": 0})
    assert only_factual.score == pytest.approx(100 * 6 / 13, abs=0.05)
