"""
Builds retention_dataset.json from rule-based simulation.

Encoding known relationships between script quality scores and viewer retention:
  - Hook quality (R1) predicts early drop-off at seconds 0–6
  - Coherence (R2) predicts mid-video retention at seconds 6–20
  - Cultural alignment (R3) predicts late retention at seconds 20–60

Dataset format:
{
  "samples": [
    {
      "script_id": "train_001",
      "script_text": "...",
      "platform": "Reels",
      "region": "Mumbai Gen Z",
      "retention_curve": [1.0, 0.95, ...],   # 10 values at seconds [0,3,6,10,15,20,25,30,45,60]
      "curve_source": "rule_based",
      "quality_tier": "high" | "medium" | "low"
    }
  ]
}
"""
import json
import random
from pathlib import Path
from typing import List, Tuple

_TIMEPOINTS = [0, 3, 6, 10, 15, 20, 25, 30, 45, 60]
_OUTPUT_PATH = Path(__file__).parent / "retention_dataset.json"

_PLATFORMS = ["Reels", "Shorts", "Feed", "TikTok"]
_REGIONS = ["Mumbai Gen Z", "pan_india_english", "delhi_millennial", "bangalore_tech"]

_HIGH_SCRIPTS = [
    "Did you know {pct}% of people get this wrong? Here's what actually works. Stop doing what everyone tells you. Use this one simple method instead. The results will genuinely surprise you. Comment 'yes' if you want the full breakdown.",
    "I made {amt}k in 30 days using this strategy. Nobody in your feed is talking about this. Here's exactly what I did step by step. You can start tonight with zero investment. Follow for the full guide.",
    "Your phone is lying to you about money. Here's the truth about compound interest that banks don't want you to know. Start with just $50. Watch what happens after 12 months. This changed everything for me.",
    "Stop scrolling. This is the {amt}-second trick that saved me {pct}% on every bill. I tested it for 3 months. Here's the proof. Save this before it gets taken down.",
    "Why do {pct}% of people fail at saving money? I spent 6 months finding out. The answer surprised me. It has nothing to do with income. Watch till the end for the fix.",
    "The {amt} investing mistake I made at 22 cost me {pct}k. Here's what I wish someone told me. Three rules that actually work. No BS, no courses to sell. Just what changed my life.",
    "How to pay off debt {pct}% faster using the avalanche method. Most people use the wrong strategy. This is the math-backed approach. Takes 5 minutes to set up. Start today.",
    "This bank trick gives you {pct}% more interest — your bank doesn't advertise it. Took me {amt} months to find it. Here's exactly how to set it up in under 2 minutes.",
]

_MED_SCRIPTS = [
    "So today I want to talk about something that I think is really important for a lot of people. Financial planning is something that many people overlook. You should really try to save money regularly if you can. It makes a big difference over time when you think about it.",
    "Hey everyone, welcome back to my channel. Today I'm sharing some tips about managing your finances better. These tips have helped me personally and I hope they help you too. Let me know in the comments what you think about them.",
    "Saving money is actually not that hard once you get into the habit. The main thing is consistency. Try to set aside a fixed amount each month. Over time it really does add up significantly. There are several ways you can approach this.",
    "I've been thinking a lot about financial health lately. It's something that affects everyone. The basics are pretty simple when you break them down. Budget, save, invest — in that order. Most people skip the middle step which is a mistake.",
    "Money management is a skill that anyone can learn. It takes time and practice but it's worth it. Start by tracking your spending for one month. Then identify areas where you can cut back. After that you can start building your savings.",
]

_LOW_SCRIPTS = [
    "Hello guys welcome back um so today basically I wanted to kind of talk about you know like finances and stuff. So basically what I mean is um you should save more money I guess. That's kind of the main point I think. Um yeah so basically just try to do that.",
    "Hey everyone so basically today's video is about money and financial things. I mean you know like it's really important and stuff like that. So yeah basically just save money I guess. Um anyway thanks for watching and stuff.",
    "So um welcome back to my channel. Today I kind of want to sort of discuss um financial things you know. Like basically everyone knows they should save money right. Um so yeah that's basically it I think. Like just try to be better with money or whatever.",
    "Hey guys so um today we're going to talk about kind of like money and finances and all that stuff. So basically um the thing is you know it's pretty important I think. Like I don't know just try to save more I guess. Um yeah so basically that's the main thing.",
    "Welcome back everyone so today basically I wanted to kind of share some thoughts on um financial stuff. Like you know it's important and everything. So basically just try to you know manage your money better or something like that. Um yeah I hope that helps.",
]


def _pick_script(quality: str) -> str:
    amt = random.randint(10, 99)
    pct = random.randint(60, 98)
    if quality == "high":
        template = random.choice(_HIGH_SCRIPTS)
    elif quality == "medium":
        template = random.choice(_MED_SCRIPTS)
    else:
        template = random.choice(_LOW_SCRIPTS)
    return template.format(amt=amt, pct=pct)


def _quality_to_scores(quality: str) -> Tuple[float, float, float]:
    if quality == "high":
        r1 = random.uniform(0.78, 1.0)
        r2 = random.uniform(0.72, 1.0)
        r3 = random.uniform(0.68, 1.0)
    elif quality == "medium":
        r1 = random.uniform(0.38, 0.65)
        r2 = random.uniform(0.38, 0.65)
        r3 = random.uniform(0.38, 0.65)
    else:
        r1 = random.uniform(0.05, 0.25)
        r2 = random.uniform(0.08, 0.28)
        r3 = random.uniform(0.08, 0.28)
    return r1, r2, r3


def _generate_curve(r1: float, r2: float, r3: float) -> List[float]:
    """
    Rule-based retention curve at timepoints [0, 3, 6, 10, 15, 20, 25, 30, 45, 60].

    Rules from phase spec:
      s0  = 1.0
      s3  = 1.0 - (0.4 * (1 - r1))        # hook quality predicts early drop
      s10 = prev - (0.1 * (1 - r2))        # coherence predicts mid-video
      s20 = prev - (0.15 * (1 - r3))       # cultural alignment predicts late
      s60 = prev - 0.05                    # natural decay always present
    """
    noise = lambda lo, hi: random.uniform(lo, hi)

    s0 = 1.0
    s3 = max(0.0, 1.0 - (0.4 * (1 - r1)) + noise(-0.02, 0.02))
    s6 = max(0.0, s3 - noise(0.02, 0.06))
    s10 = max(0.0, s6 - (0.1 * (1 - r2)) - noise(0.0, 0.03))
    s15 = max(0.0, s10 - noise(0.03, 0.07))
    s20 = max(0.0, s15 - (0.15 * (1 - r3)) - noise(0.0, 0.03))
    s25 = max(0.0, s20 - noise(0.02, 0.05))
    s30 = max(0.0, s25 - noise(0.02, 0.05))
    s45 = max(0.0, s30 - 0.05 - noise(0.0, 0.04))
    s60 = max(0.0, s45 - 0.05)

    # enforce monotonic decrease
    curve = [s0, s3, s6, s10, s15, s20, s25, s30, s45, s60]
    for i in range(1, len(curve)):
        curve[i] = min(curve[i], curve[i - 1])
    return [round(v, 3) for v in curve]


def build(output_path: str = None, seed: int = 42) -> str:
    """Build and save the dataset. Returns the path written."""
    random.seed(seed)
    path = Path(output_path) if output_path else _OUTPUT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    samples = []
    idx = 1
    for quality, count in [("high", 50), ("medium", 50), ("low", 50)]:
        for _ in range(count):
            platform = random.choice(_PLATFORMS)
            region = random.choice(_REGIONS)
            r1, r2, r3 = _quality_to_scores(quality)
            curve = _generate_curve(r1, r2, r3)
            samples.append({
                "script_id": f"train_{idx:03d}",
                "script_text": _pick_script(quality),
                "platform": platform,
                "region": region,
                "retention_curve": curve,
                "curve_source": "rule_based",
                "quality_tier": quality,
                "r1_score": round(r1, 3),
                "r2_score": round(r2, 3),
                "r3_score": round(r3, 3),
            })
            idx += 1

    with open(path, "w", encoding="utf-8") as f:
        json.dump({"samples": samples}, f, indent=2)

    return str(path)


if __name__ == "__main__":
    out = build()
    print(f"Dataset built: {out} (150 samples)")
