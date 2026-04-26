export const rawScript = `The truth about "10-minute productivity hacks" is that most of them fail by day three.
I tried 17 of them while building my startup in Bengaluru, and only one worked.
In this video, I will show what I deleted from my routine, what stayed, and why my output doubled.`;

export const metadata = {
  platform: "Instagram Reels",
  region: "India",
  niche: "Creator productivity"
};

export const criticClaims = [
  { id: "C1", text: "Hook lacks a concrete curiosity gap in first 2 seconds.", severity: "high" as const },
  { id: "C2", text: "Mid-section drifts into generic advice, hurting pacing.", severity: "medium" as const },
  { id: "C3", text: "CTA appears too late to recover retention drop at 18s.", severity: "medium" as const }
];

export const defender = {
  coreStrength: "Local founder context and honesty make this script credible.",
  warnings: ["Do not remove Bengaluru story anchor.", "Keep candid tone; avoid clickbait language."]
};

export const reasoning = {
  before: [
    "Priority assessment: C1 high severity, but all claims look similar.",
    "Conflict check: uncertain trade-off between urgency and authenticity.",
    "Defender consideration: noted, but not explicitly handled.",
    "Action: generic hook rewrite."
  ],
  after: [
    "Priority assessment: C1 is high severity and unflagged, highest expected retention lift.",
    "Conflict check: C1 fix does not violate cultural anchor from Defender.",
    "Defender consideration: preserve Bengaluru reference and honest tone.",
    "Action: targeted hook rewrite with concrete reveal and local context."
  ]
};

export const diffLines = [
  { type: "removed" as const, text: `The truth about "10-minute productivity hacks" is that most fail by day three.` },
  { type: "added" as const, text: "By day three, 16 of 17 productivity hacks failed me while building in Bengaluru." },
  { type: "added" as const, text: "The one that worked gave me 2x output without longer hours." }
];

export const rewardBefore = {
  r1: 0.42, r2: 0.58, r3: 0.61, r4: 0.38, r5: 0.51,
  r6: 0.55, r7: 0.49, r8: 0.44, r9: 0.52, r10: 0.39,
  process: 0.44, total: 0.49
};

export const rewardAfter = {
  r1: 0.71, r2: 0.74, r3: 0.82, r4: 0.79, r5: 0.76,
  r6: 0.83, r7: 0.78, r8: 0.81, r9: 0.77, r10: 0.85,
  process: 0.78, total: 0.79
};

export const retentionSeries = [
  { t: 0,  before: 100, after: 100 },
  { t: 6,  before: 70,  after: 88  },
  { t: 12, before: 56,  after: 81  },
  { t: 20, before: 41,  after: 73  },
  { t: 30, before: 32,  after: 66  },
  { t: 45, before: 24,  after: 54  },
  { t: 60, before: 18,  after: 47  }
];

export const learningSeries = [
  { episode: 1,   baseline: 0.50, trained: 0.50, retentionLift: 0,  success: 42 },
  { episode: 20,  baseline: 0.51, trained: 0.59, retentionLift: 9,  success: 53 },
  { episode: 40,  baseline: 0.50, trained: 0.64, retentionLift: 14, success: 61 },
  { episode: 60,  baseline: 0.49, trained: 0.70, retentionLift: 19, success: 69 },
  { episode: 80,  baseline: 0.50, trained: 0.74, retentionLift: 24, success: 75 },
  { episode: 100, baseline: 0.50, trained: 0.79, retentionLift: 29, success: 81 }
];

export const sessions = [
  { id: "S-184", date: "Today",      weak: "Hook clarity",      strength: "Relatable opener",   score: 79 },
  { id: "S-183", date: "Yesterday",  weak: "CTA placement",     strength: "Cultural tone",       score: 75 },
  { id: "S-182", date: "2 days ago", weak: "Pacing",            strength: "Specific details",    score: 69 },
  { id: "S-181", date: "3 days ago", weak: "Conflict framing",  strength: "Audience empathy",    score: 64 },
  { id: "S-180", date: "4 days ago", weak: "Hook strength",     strength: "Clear narrative",     score: 60 }
];

export const phases = [
  { id: 1,  name: "Scaffolding",          status: "COMPLETE", tests: 0,  summary: "Project structure, env setup, base classes" },
  { id: 2,  name: "Critic + Defender",    status: "COMPLETE", tests: 8,  summary: "CriticAgent, DefenderAgent, debate loop" },
  { id: 3,  name: "GRPO Pipeline",        status: "COMPLETE", tests: 12, summary: "Curriculum tiers, rollout fn, dry-run gate" },
  { id: 4,  name: "Difficulty Tracker",   status: "COMPLETE", tests: 6,  summary: "DifficultyTracker, CriticEscalationEngine" },
  { id: 5,  name: "HF Deploy",            status: "COMPLETE", tests: 10, summary: "HuggingFace Spaces, FastAPI, demo endpoint" },
  { id: 6,  name: "Safety + Originality", status: "COMPLETE", tests: 16, summary: "ModerationAgent, OriginalityAgent, R6/R7" },
  { id: 7,  name: "Process Reward",       status: "COMPLETE", tests: 21, summary: "ReasoningParser, ProcessVerifier, ProcessReward" },
  { id: 8,  name: "Creator Profile",      status: "COMPLETE", tests: 25, summary: "CreatorProfile, ProfileGenerator, R8 PersonaFit" },
  { id: 9,  name: "Platform Pacing",      status: "COMPLETE", tests: 20, summary: "PlatformRegistry, R9 PlatformPacing, platform-aware R1/R2" },
  { id: 10, name: "A/B Contrastive",      status: "COMPLETE", tests: 25, summary: "ABScriptEnv, ContrastiveReward, A/B rollout fn" },
  { id: 11, name: "Longitudinal Memory",  status: "COMPLETE", tests: 24, summary: "CreatorHistoryBuffer, MemoryCompressor, HistoryStore" },
  { id: 12, name: "Retention Curve",      status: "COMPLETE", tests: 14, summary: "RetentionCurveSimulator, R10, MAE 0.031, model trained" }
];

export const systemStats = {
  totalPhases: 12,
  totalTests: 181,
  totalRewards: 10,
  retentionModelMAE: 0.031,
  peakReward: 0.79,
  successRate: 81,
  retentionLift: 29,
  abWinnerMargin: 0.08
};
