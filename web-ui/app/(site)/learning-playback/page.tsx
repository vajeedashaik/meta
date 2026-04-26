"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { LearningTimeline, EpisodeSnapshot } from "@/components/LearningTimeline";
import { EpisodeControls } from "@/components/EpisodeControls";

const EPISODES: EpisodeSnapshot[] = [
  {
    episode: 1,
    script: `Hook: Do you want more views?\nBody: Here are some tips for getting more views.\nCTA: Follow for more tips.`,
    reasoning: [
      "Priority assessment: C1 high severity, but all claims look similar.",
      "Conflict check: uncertain trade-off between urgency and authenticity.",
      "Defender consideration: noted, but not explicitly handled.",
      "Action: generic hook rewrite.",
    ],
    rewards: { r1: 0.42, r2: 0.58, r3: 0.61, r4: 0.38, r5: 0.51, r6: 0.55, r7: 0.49, r8: 0.44, r9: 0.52, r10: 0.39, process: 0.44, total: 0.49 },
  },
  {
    episode: 20,
    script: `Hook: 16 of 17 productivity hacks failed me building in Bengaluru.\nBody: The one that worked gave me 2x output without longer hours.\nCTA: I'll show you exactly what stayed — watch to the end.`,
    reasoning: [
      "Priority assessment: C1 is high severity and unflagged — highest expected retention lift.",
      "Conflict check: C1 fix does not violate cultural anchor from Defender.",
      "Defender consideration: preserve Bengaluru reference and honest tone.",
      "Action: targeted hook rewrite with concrete reveal and local context.",
    ],
    rewards: { r1: 0.55, r2: 0.63, r3: 0.68, r4: 0.54, r5: 0.60, r6: 0.70, r7: 0.62, r8: 0.57, r9: 0.64, r10: 0.52, process: 0.60, total: 0.59 },
  },
  {
    episode: 40,
    script: `Hook: By day three, 16 of 17 productivity hacks I tested while building in Bengaluru had already failed.\nBody: The one that worked doubled my output — no extra hours.\nCTA: I'll break down exactly which one survived and why. Stay for 30 seconds.`,
    reasoning: [
      "Priority assessment: R1 gap 0.31 — hook specificity is highest lever.",
      "Conflict check: concrete number preserves credibility anchor (C2 unflagged).",
      "Defender consideration: Bengaluru context strengthens regional credibility.",
      "Action: precision hook rewrite citing specific outcome and pattern-interrupt.",
    ],
    rewards: { r1: 0.64, r2: 0.70, r3: 0.75, r4: 0.67, r5: 0.68, r6: 0.78, r7: 0.70, r8: 0.68, r9: 0.72, r10: 0.64, process: 0.68, total: 0.67 },
  },
  {
    episode: 60,
    script: `Hook: By day three, 16 of 17 productivity hacks I tested while building my startup in Bengaluru had already failed me.\nBody: One survived. It doubled my output without a single extra hour.\nCTA: I'm showing you exactly which one — and why the others failed. Watch to the end.`,
    reasoning: [
      "Priority assessment: R1 gap 0.21 — hook near ceiling; pivot to R4 claim resolution.",
      "Conflict check: CTA repositioning does not conflict with core strength.",
      "Defender consideration: honest framing preserved — no clickbait language added.",
      "Action: CTA placement + hook sharpening for retention curve lift.",
    ],
    rewards: { r1: 0.70, r2: 0.73, r3: 0.80, r4: 0.74, r5: 0.73, r6: 0.82, r7: 0.75, r8: 0.76, r9: 0.78, r10: 0.74, process: 0.74, total: 0.73 },
  },
  {
    episode: 80,
    script: `Hook: By day three, 16 of 17 productivity hacks failed. I was building a startup in Bengaluru, tracking every one.\nBody: The survivor doubled my output with zero extra hours logged.\nCTA: Stay 30 seconds — I'll show you the exact system and the 16 that wasted my time.`,
    reasoning: [
      "Priority assessment: R4 gap 0.09 — debate resolution nearly maxed; target R10 retention curve.",
      "Conflict check: pacing adjustment in body preserves coherence (R2 stable).",
      "Defender consideration: 'startup in Bengaluru' grounds credibility; retained.",
      "Action: body restructure for mid-video retention; CTA sharpened to create open loop.",
    ],
    rewards: { r1: 0.73, r2: 0.76, r3: 0.83, r4: 0.79, r5: 0.77, r6: 0.85, r7: 0.79, r8: 0.80, r9: 0.79, r10: 0.82, process: 0.79, total: 0.78 },
  },
  {
    episode: 100,
    script: `Hook: By day three, 16 of 17 productivity hacks had failed me. I was building my startup in Bengaluru, logging every attempt.\nBody: One hack survived and gave me 2x output — no extra hours.\nCTA: I'll show you exactly which one and why the other 16 failed. Stay 30 seconds.`,
    reasoning: [
      "Priority assessment: All gaps < 0.10 — maintain high-performing configuration.",
      "Conflict check: no conflicts detected with Defender-protected elements.",
      "Defender consideration: local voice, honesty, and specificity all preserved.",
      "Action: micro-refinement to hook verb choice for pattern-interrupt optimisation.",
    ],
    rewards: { r1: 0.75, r2: 0.78, r3: 0.85, r4: 0.81, r5: 0.79, r6: 0.86, r7: 0.81, r8: 0.83, r9: 0.81, r10: 0.85, process: 0.81, total: 0.81 },
  },
];

const HISTORY = EPISODES.map((e) => ({ episode: e.episode, total: e.rewards.total }));

export default function LearningPlaybackPage() {
  const [current, setCurrent] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<1 | 2>(1);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const advance = useCallback(() => {
    setCurrent((prev) => {
      if (prev >= EPISODES.length - 1) {
        setPlaying(false);
        return prev;
      }
      return prev + 1;
    });
  }, []);

  useEffect(() => {
    if (playing) {
      const ms = speed === 1 ? 1800 : 900;
      intervalRef.current = setInterval(advance, ms);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [playing, speed, advance]);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-3xl font-bold text-white">AI Learning Timeline</h1>
        <p className="mt-1 text-sm text-purple-300/70">Watch the model learn across episodes</p>
      </div>

      <EpisodeControls
        playing={playing}
        episode={EPISODES[current].episode}
        maxEpisode={EPISODES[EPISODES.length - 1].episode}
        speed={speed}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onSeek={(ep) => {
          const idx = EPISODES.findIndex((e) => e.episode >= ep);
          setCurrent(Math.max(0, idx === -1 ? EPISODES.length - 1 : idx));
        }}
        onSpeedToggle={() => setSpeed((s) => (s === 1 ? 2 : 1))}
      />

      <LearningTimeline
        episodes={EPISODES}
        current={current}
        historySeries={HISTORY}
      />
    </div>
  );
}
