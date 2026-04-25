from enum import Enum
from typing import List, Optional
from pydantic import BaseModel


class CreatorTier(str, Enum):
    BEGINNER = "beginner"       # 0-1k followers
    GROWING = "growing"         # 1k-10k followers
    ESTABLISHED = "established" # 10k-100k followers
    VERIFIED = "verified"       # 100k+ followers


class PostingFrequency(str, Enum):
    RARE = "rare"           # < 1 post/week
    REGULAR = "regular"     # 1-3 posts/week
    FREQUENT = "frequent"   # 4-7 posts/week
    DAILY = "daily"         # 1+ posts/day


class CreatorProfile(BaseModel):
    creator_id: str
    tier: CreatorTier
    follower_count: int
    posting_frequency: PostingFrequency
    niche: str
    niche_maturity: str                 # "new_to_niche" | "established_in_niche" | "niche_authority"
    avg_engagement_rate: float          # 0.0-1.0 (likes+comments / followers)
    avg_retention_rate: float           # 0.0-1.0 (estimated average watch-through)
    past_weak_points: List[str]         # critique classes they repeatedly struggle with
    past_strong_points: List[str]       # critique classes they consistently handle well
    voice_descriptors: List[str]        # e.g. ["direct", "humorous", "educational", "regional"]
    platform_primary: str               # "Reels" | "Shorts" | "TikTok"

    @property
    def needs_fundamentals(self) -> bool:
        return self.tier in [CreatorTier.BEGINNER, CreatorTier.GROWING]

    @property
    def needs_refinement(self) -> bool:
        return self.tier in [CreatorTier.ESTABLISHED, CreatorTier.VERIFIED]
