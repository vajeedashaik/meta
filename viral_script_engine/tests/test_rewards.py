import pytest
from viral_script_engine.rewards.r1_hook_strength import HookStrengthReward
from viral_script_engine.rewards.r2_coherence import CoherenceReward
from viral_script_engine.rewards.reward_aggregator import RewardAggregator
from viral_script_engine.environment.observations import RewardComponents
from viral_script_engine.environment.actions import ActionType

# ── R1 test hooks ─────────────────────────────────────────────────────────────
HOOK_HIGH_1 = (
    "I made $10,000 in 30 days with 3 crypto strategies. "
    "Here's the secret most people don't know. "
    "This completely changed how I invest."
)
HOOK_HIGH_2 = (
    "Why 95% of people fail at losing weight in 2024. "
    "Most people don't know this simple truth. "
    "It's not about calories at all."
)
HOOK_LOW_1 = (
    "Hey guys, welcome back to my channel! "
    "Today I want to talk about some stuff. "
    "It's going to be super interesting!"
)
HOOK_LOW_2 = (
    "So basically today I'm going to talk about fitness. "
    "It's really important for everyone. "
    "Let's get started with some tips."
)
HOOK_EDGE = (
    "What nobody tells you about starting a business in India. "
    "I found out the hard way. "
    "Here's my experience."
)


@pytest.fixture
def r1():
    return HookStrengthReward()


@pytest.fixture
def r2():
    return CoherenceReward()


@pytest.fixture
def aggregator():
    return RewardAggregator()


# ── R1 tests ──────────────────────────────────────────────────────────────────
def test_r1_high_score_1(r1):
    result = r1.score(HOOK_HIGH_1)
    assert result.score > 0.8


def test_r1_high_score_2(r1):
    result = r1.score(HOOK_HIGH_2)
    assert result.score > 0.8


def test_r1_low_score_1(r1):
    result = r1.score(HOOK_LOW_1)
    assert result.score < 0.3


def test_r1_low_score_2(r1):
    result = r1.score(HOOK_LOW_2)
    assert result.score < 0.3


def test_r1_edge_case(r1):
    result = r1.score(HOOK_EDGE)
    assert 0.3 <= result.score <= 0.7


# ── R2 tests ──────────────────────────────────────────────────────────────────
def test_r2_identical_strings(r2):
    text = "This is a test script for the viral script engine."
    result = r2.score(text, text)
    assert result.score == 0.8


def test_r2_different_strings(r2):
    orig = "I made $10,000 with crypto in 30 days using these 3 strategies."
    diff = "The history of ancient Rome spans over a thousand years of conquest."
    result = r2.score(orig, diff)
    assert result.score == 0.0


# ── Aggregator tests ──────────────────────────────────────────────────────────
def test_aggregator_catastrophic_drop(aggregator):
    start = RewardComponents(r1_hook_strength=0.8, r2_coherence=0.7)
    start.compute_total()
    current = RewardComponents(r1_hook_strength=0.3, r2_coherence=0.7)
    result, log = aggregator.compute(current, start, [ActionType.HOOK_REWRITE])
    assert result.total == 0.0


def test_aggregator_diversity_penalty(aggregator):
    start = RewardComponents(r1_hook_strength=0.6, r2_coherence=0.6)
    start.compute_total()
    current = RewardComponents(r1_hook_strength=0.7, r2_coherence=0.7)
    history = [ActionType.HOOK_REWRITE, ActionType.HOOK_REWRITE, ActionType.HOOK_REWRITE]
    result, log = aggregator.compute(current, start, history)
    assert result.anti_gaming_penalty == 0.15
    assert result.total < 0.7


def test_aggregator_no_penalty(aggregator):
    start = RewardComponents(r1_hook_strength=0.6, r2_coherence=0.6)
    start.compute_total()
    current = RewardComponents(r1_hook_strength=0.7, r2_coherence=0.7)
    history = [ActionType.HOOK_REWRITE, ActionType.CTA_PLACEMENT, ActionType.SECTION_REORDER]
    result, log = aggregator.compute(current, start, history)
    assert result.anti_gaming_penalty == 0.0
    assert result.total > 0
