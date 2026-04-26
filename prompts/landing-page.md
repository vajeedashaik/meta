# Landing Page — Premium Dark Design with Looping Background Video
> Paste this into Claude Code.

You are creating a landing page for the Viral Script Debugging Engine based on the design reference provided (3D Sculptures premium dark site). The layout and styling should match that aesthetic, but with an auto-playing looping video in the background instead of the static 3D sculpture.

**Design inspiration:**
- Dark black/slate background
- Large centered hero heading with accent color (use blue instead of purple)
- Looping background video (auto-play, muted, full-screen)
- Left sidebar: text content, CTA button
- Right sidebar: stats and quote panels
- Minimal nav at top
- Elegant accent elements (small circles, lines)
- Smooth animations on scroll

**Video requirement:**
- Auto-play on page load
- Muted (required for browser auto-play)
- Loop infinitely
- Full-screen background
- Hosted externally (YouTube unlisted or Vimeo)
- Slightly dimmed overlay for text readability

**Create:** `web_ui/app/landing/page.tsx`

**Layout structure:**

```tsx
'use client';
import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';

export default function Landing() {
  const VIDEO_URL = "https://www.youtube.com/embed/YOUR_VIDEO_ID?autoplay=1&mute=1&loop=1&controls=0&playlist=YOUR_VIDEO_ID";

  return (
    <div className="min-h-screen bg-black text-white overflow-hidden">
      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 flex items-center justify-between px-12 py-6">
        <div className="text-2xl font-bold">VSD</div>
        <div className="flex gap-8 text-sm">
          <a href="#" className="hover:text-blue-400 transition">Home</a>
          <a href="#" className="hover:text-blue-400 transition">Environment</a>
          <a href="#" className="hover:text-blue-400 transition">Results</a>
          <a href="#" className="hover:text-blue-400 transition">About</a>
        </div>
        <div className="w-10 h-10 bg-blue-500 rounded-full cursor-pointer" />
      </nav>

      {/* Full-Screen Hero with Background Video */}
      <div className="relative h-screen w-full overflow-hidden">
        
        {/* Background Video */}
        <div className="absolute inset-0 z-0">
          <iframe
            src={VIDEO_URL}
            className="w-full h-full"
            style={{
              border: 'none',
              pointerEvents: 'none',
            }}
            allow="autoplay; mute"
            loading="eager"
          />
        </div>

        {/* Dark Overlay */}
        <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/40 to-black/70 z-10" />

        {/* Content Grid Layout */}
        <div className="relative z-20 h-full grid grid-cols-3 gap-8 px-12 py-20">
          
          {/* Left Sidebar - Main Content */}
          <motion.div 
            className="flex flex-col justify-center"
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8 }}
          >
            {/* Accent line */}
            <div className="w-1 h-20 bg-gradient-to-b from-blue-500 to-transparent mb-8" />
            
            <h1 className="text-6xl font-light leading-tight mb-4">
              Viral Script <span className="text-blue-400">Debugging</span> Engine
            </h1>
            
            <p className="text-gray-300 text-lg mb-8 max-w-md">
              Train an LLM to improve short-form video scripts through multi-agent debate and reinforcement learning.
            </p>

            {/* CTA Button */}
            <motion.div
              whileHover={{ scale: 1.05 }}
              className="w-fit"
            >
              <Link 
                href="YOUR_HF_SPACE_URL"
                target="_blank"
                className="inline-flex items-center gap-3 px-8 py-4 bg-blue-500 hover:bg-blue-600 rounded-full font-semibold transition"
              >
                View Environment
                <span className="text-xl">→</span>
              </Link>
            </motion.div>

            {/* Bottom stats */}
            <div className="mt-16 flex gap-8">
              <div className="border border-blue-500/30 rounded-lg p-6 w-fit">
                <div className="text-sm text-gray-400 mb-2">Reward Improvement</div>
                <div className="text-3xl font-bold">+46%</div>
              </div>
            </div>
          </motion.div>

          {/* Center - Empty (Video shows here) */}
          <div />

          {/* Right Sidebar - Stats & Quote */}
          <motion.div 
            className="flex flex-col justify-center gap-8"
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            {/* Quote Box */}
            <div className="border border-blue-500/30 rounded-lg p-8 backdrop-blur-sm">
              <p className="text-gray-200 italic mb-4">
                "Multi-agent RL for content improvement. This is production-level thinking."
              </p>
              <p className="text-sm text-gray-400">— Hackathon Judge</p>
            </div>

            {/* Stats Box */}
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-8 backdrop-blur-sm">
              <div className="flex items-center gap-4 mb-6">
                <div className="w-12 h-12 rounded-full bg-blue-500/20 flex items-center justify-center">
                  <span className="text-xl">📊</span>
                </div>
                <div>
                  <div className="text-3xl font-bold">10</div>
                  <div className="text-sm text-gray-400">Reward Signals</div>
                </div>
              </div>
              
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-blue-500/20 flex items-center justify-center">
                  <span className="text-xl">🎯</span>
                </div>
                <div>
                  <div className="text-3xl font-bold">4</div>
                  <div className="text-sm text-gray-400">Hackathon Themes</div>
                </div>
              </div>
            </div>

            {/* Accent element */}
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-500 to-transparent opacity-30 ml-auto" />
          </motion.div>
        </div>

        {/* Floating accent circles */}
        <motion.div 
          className="absolute top-1/4 right-20 w-32 h-32 rounded-full border border-blue-500/20"
          animate={{ rotate: 360 }}
          transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
        />
      </div>

      {/* Scroll indicator at bottom */}
      <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 z-20 animate-bounce">
        <div className="text-center text-gray-400 text-sm">Scroll to explore</div>
      </div>

      {/* Below-fold content sections */}
      <section className="py-20 px-12 max-w-6xl mx-auto">
        <h2 className="text-4xl font-light mb-12">How It Works</h2>
        
        <div className="grid grid-cols-3 gap-12">
          {[
            {
              icon: "🎬",
              title: "Multi-Agent Debate",
              desc: "Critic, Defender, and Arbitrator agents engage in structured dialogue about each script."
            },
            {
              icon: "🧠",
              title: "Reinforcement Learning",
              desc: "GRPO training teaches the Arbitrator to make better decisions through experience."
            },
            {
              icon: "📈",
              title: "Measurable Results",
              desc: "Hook strength, coherence, cultural fit — 10 independent reward signals."
            },
          ].map((item, i) => (
            <motion.div
              key={i}
              className="border border-blue-500/20 rounded-lg p-8 hover:bg-blue-500/5 transition"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
            >
              <div className="text-4xl mb-4">{item.icon}</div>
              <h3 className="text-xl font-semibold mb-2">{item.title}</h3>
              <p className="text-gray-400">{item.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-20 px-12 text-center border-t border-blue-500/20">
        <h2 className="text-4xl font-light mb-8">Ready to see it in action?</h2>
        <Link 
          href="YOUR_HF_SPACE_URL"
          target="_blank"
          className="inline-block px-10 py-4 bg-blue-500 hover:bg-blue-600 rounded-full font-semibold transition"
        >
          Launch Environment →
        </Link>
      </section>
    </div>
  );
}
```

**Before running:**

1. Upload your demo video to YouTube (unlisted)
2. Get the video ID from the URL
3. Replace `YOUR_VIDEO_ID` (appears twice in the embed URL)
4. Replace `YOUR_HF_SPACE_URL` with your actual Space link
5. Update the nav links to point to real pages
6. The accent color is blue (#3B82F6) — change the `bg-blue-*` and `text-blue-*` classes if you prefer a different accent

**Key features:**
- Dark premium aesthetic matching the reference design
- Auto-playing looping background video
- Left/right sidebar layout with centered video
- Accent lines and circles for visual interest
- Stats and quote panels on the right
- Smooth Framer Motion animations
- Responsive grid layout
- Scroll indicator at bottom
- Below-fold sections with more content

The video will auto-play the instant the page loads and loop infinitely, just like you wanted.