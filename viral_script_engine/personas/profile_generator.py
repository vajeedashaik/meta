import random
from typing import List, Optional

from viral_script_engine.personas.creator_profile import (
    CreatorProfile, CreatorTier, PostingFrequency,
)

_ALL_CRITIQUE_CLASSES = [
    "hook_weakness", "cta_buried", "cta_weakness", "pacing_issue",
    "cultural_mismatch", "originality_low", "section_disorder", "retention_drop",
]

_VOICE_POOL = [
    "direct", "humorous", "educational", "regional", "relatable",
    "Hinglish", "aspirational", "casual", "storytelling", "data-driven",
]

_NICHE_MATURITY_BY_TIER = {
    CreatorTier.BEGINNER: ["new_to_niche"],
    CreatorTier.GROWING: ["new_to_niche", "established_in_niche"],
    CreatorTier.ESTABLISHED: ["established_in_niche", "niche_authority"],
    CreatorTier.VERIFIED: ["niche_authority"],
}

_POSTING_FREQ_BY_TIER = {
    CreatorTier.BEGINNER: [PostingFrequency.RARE, PostingFrequency.REGULAR],
    CreatorTier.GROWING: [PostingFrequency.REGULAR, PostingFrequency.FREQUENT],
    CreatorTier.ESTABLISHED: [PostingFrequency.FREQUENT, PostingFrequency.DAILY],
    CreatorTier.VERIFIED: [PostingFrequency.FREQUENT, PostingFrequency.DAILY],
}


class ProfileGenerator:
    NICHES = [
        "personal finance", "cooking", "fitness", "tech reviews",
        "small business", "agriculture", "fashion", "comedy",
        "productivity", "travel", "education", "local culture",
    ]

    def generate(self, tier: CreatorTier, niche: str, seed: int = 42) -> CreatorProfile:
        rng = random.Random(seed)

        follower_count = self._follower_count(tier, rng)
        engagement_rate = self._engagement_rate(tier, rng)
        retention_rate = round(rng.uniform(0.25, 0.65), 3)
        posting_freq = rng.choice(_POSTING_FREQ_BY_TIER[tier])
        niche_maturity = rng.choice(_NICHE_MATURITY_BY_TIER[tier])
        voice = rng.sample(_VOICE_POOL, k=rng.randint(2, 4))
        platform = rng.choice(["Reels", "Shorts", "TikTok"])

        weak_pool = list(_ALL_CRITIQUE_CLASSES)
        weak_points = rng.sample(weak_pool, k=rng.randint(1, 3))
        remaining = [c for c in weak_pool if c not in weak_points]
        strong_points = rng.sample(remaining, k=min(2, len(remaining)))

        creator_id = f"{tier.value}_{niche.replace(' ', '_')}_{seed}"

        return CreatorProfile(
            creator_id=creator_id,
            tier=tier,
            follower_count=follower_count,
            posting_frequency=posting_freq,
            niche=niche,
            niche_maturity=niche_maturity,
            avg_engagement_rate=engagement_rate,
            avg_retention_rate=retention_rate,
            past_weak_points=weak_points,
            past_strong_points=strong_points,
            voice_descriptors=voice,
            platform_primary=platform,
        )

    def generate_batch(self, n: int, tier_distribution: Optional[dict] = None) -> List[CreatorProfile]:
        if tier_distribution is None:
            tier_distribution = {
                CreatorTier.BEGINNER: 0.40,
                CreatorTier.GROWING: 0.35,
                CreatorTier.ESTABLISHED: 0.20,
                CreatorTier.VERIFIED: 0.05,
            }

        tiers = list(tier_distribution.keys())
        weights = [tier_distribution[t] for t in tiers]
        profiles = []
        rng = random.Random(99)

        for i in range(n):
            tier = rng.choices(tiers, weights=weights, k=1)[0]
            niche = rng.choice(self.NICHES)
            profiles.append(self.generate(tier=tier, niche=niche, seed=i))

        return profiles

    # --- private helpers ---

    def _follower_count(self, tier: CreatorTier, rng: random.Random) -> int:
        ranges = {
            CreatorTier.BEGINNER: (50, 999),
            CreatorTier.GROWING: (1000, 9999),
            CreatorTier.ESTABLISHED: (10000, 99999),
            CreatorTier.VERIFIED: (100000, 2000000),
        }
        lo, hi = ranges[tier]
        return rng.randint(lo, hi)

    def _engagement_rate(self, tier: CreatorTier, rng: random.Random) -> float:
        ranges = {
            CreatorTier.BEGINNER: (0.08, 0.15),
            CreatorTier.GROWING: (0.04, 0.08),
            CreatorTier.ESTABLISHED: (0.02, 0.04),
            CreatorTier.VERIFIED: (0.01, 0.02),
        }
        lo, hi = ranges[tier]
        return round(rng.uniform(lo, hi), 4)
