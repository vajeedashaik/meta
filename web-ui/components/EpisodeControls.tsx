"use client";

import { Pause, Play } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  playing: boolean;
  episode: number;
  maxEpisode: number;
  speed: 1 | 2;
  onPlay: () => void;
  onPause: () => void;
  onSeek: (ep: number) => void;
  onSpeedToggle: () => void;
}

export function EpisodeControls({
  playing,
  episode,
  maxEpisode,
  speed,
  onPlay,
  onPause,
  onSeek,
  onSpeedToggle,
}: Props) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Button
        size="sm"
        onClick={playing ? onPause : onPlay}
        className="gap-1.5"
      >
        {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
        {playing ? "Pause" : "Play"}
      </Button>

      <input
        type="range"
        min={1}
        max={maxEpisode}
        value={episode}
        onChange={(e) => onSeek(Number(e.target.value))}
        className="h-1.5 w-40 cursor-pointer accent-primary"
      />
      <span className="text-xs text-purple-300/70 tabular-nums">
        Episode {episode}/{maxEpisode}
      </span>

      <Button
        size="sm"
        variant="outline"
        onClick={onSpeedToggle}
        className="ml-auto text-xs"
      >
        {speed}x
      </Button>
    </div>
  );
}
