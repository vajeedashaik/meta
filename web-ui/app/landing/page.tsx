'use client';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';

const HF_SPACE_URL = 'https://huggingface.co/spaces/YOUR_HF_SPACE';

const NAV_LINKS = [
  { href: '/landing',           label: 'Home',       icon: '🏠' },
  { href: '/dashboard',         label: 'Dashboard',  icon: '🖥️' },
  { href: '/episode',           label: 'Episode',    icon: '▶️' },
  { href: '/ab',                label: 'A/B Battle', icon: '⚔️' },
  { href: '/retention',         label: 'Retention',  icon: '📈' },
  { href: '/memory',            label: 'Memory',     icon: '🧠' },
  { href: '/learning',          label: 'Learning',   icon: '📊' },
  { href: '/learning-playback', label: 'Timeline',   icon: '🎬' },
];

const HOW_IT_WORKS = [
  {
    icon: '🎬',
    title: 'Multi-Agent Debate',
    desc: 'Critic, Defender, and Arbitrator agents engage in structured dialogue about each script.',
  },
  {
    icon: '🧠',
    title: 'Reinforcement Learning',
    desc: 'GRPO training teaches the Arbitrator to make better decisions through experience.',
  },
  {
    icon: '📈',
    title: 'Measurable Results',
    desc: 'Hook strength, coherence, cultural fit — 10 independent reward signals.',
  },
];

function DarkNav() {
  const pathname = usePathname();
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 flex justify-center px-4 py-4">
      <div className="flex flex-wrap gap-1.5 rounded-2xl border border-purple-700/30 bg-purple-950/70 p-2 backdrop-blur-md shadow-soft">
        {NAV_LINKS.map((link) => {
          const active = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                'flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-medium transition-all',
                active
                  ? 'bg-violet-600 text-white shadow-sm'
                  : 'text-purple-200 hover:bg-purple-800/50 hover:text-white'
              )}
            >
              <span className="text-base leading-none">{link.icon}</span>
              <span>{link.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

export default function Landing() {
  return (
    /* bg-[#0d0e10] blends with the clip's dark edges — adjust if needed */
    <div className="min-h-screen bg-[#0d0e10] text-white">
      <DarkNav />

      {/* Fixed full-bleed background video */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <iframe
          src="https://drive.google.com/file/d/1l2Olms1JUEYM0_cydOfqciz6kO1S4SbT/preview"
          allow="autoplay"
          className="w-full h-full border-0 scale-[1.02]"
          style={{ objectFit: "cover" }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/30 to-[#0d0e10]/95" />
      </div>

      <div className="relative z-10">

        {/* ── Hero ─────────────────────────────────────────────────────── */}
        <section className="min-h-screen flex items-center px-12 pt-32 pb-20">
          <div className="w-full grid grid-cols-3 gap-8">

            {/* Left — headline + CTA */}
            <motion.div
              className="flex flex-col justify-center col-span-2 lg:col-span-1"
              initial={{ opacity: 0, x: -50 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8 }}
            >
              {/* Accent bar */}
              <div className="w-1 h-24 bg-gradient-to-b from-violet-500 to-transparent mb-8" />

              <p
                className="font-display font-black leading-none tracking-tight text-violet-400 mb-2"
                style={{ fontSize: 'clamp(4.5rem, 5vw, 10rem)' }}
              >
                MetaDebate
              </p>

              {/* Subtitle hero — slightly smaller than before */}
              <h1
                className="font-display font-black leading-none tracking-tight mb-6"
                style={{ fontSize: 'clamp(2rem, 4vw, 3.25rem)' }}
              >
                Train an LLM<br />
                to improve{' '}
                <span className="text-violet-400">Reels</span><br />
                through debate
              </h1>

              <p className="text-purple-200/80 text-lg mb-10 max-w-md leading-relaxed">
                Multi-agent RL: Critic attacks, Defender preserves, Arbitrator
                decides. All 10 reward signals improved 16–46%. Retention
                engagement 3× longer.
              </p>

              <div className="flex gap-4 flex-wrap">
                <motion.div whileHover={{ scale: 1.05 }} className="w-fit">
                  <Link
                    href={HF_SPACE_URL}
                    target="_blank"
                    className="inline-flex items-center gap-3 px-8 py-4 bg-violet-600 hover:bg-violet-700 rounded-full font-semibold transition"
                  >
                    View on Hugging Face →
                  </Link>
                </motion.div>
                <motion.div whileHover={{ scale: 1.05 }} className="w-fit">
                  <Link
                    href="/episode"
                    className="inline-flex items-center gap-3 px-8 py-4 border border-purple-500/40 hover:bg-purple-900/50 rounded-full font-semibold transition"
                  >
                    Run Episode →
                  </Link>
                </motion.div>
              </div>

              <div className="mt-14 flex gap-4 flex-wrap">
                {[
                  { label: 'Total reward improvement', value: '+27%'  },
                  { label: 'Best signal (R10)',         value: '+46%'  },
                  { label: 'Trained avg reward',        value: '0.78'  },
                ].map((s) => (
                  <div
                    key={s.label}
                    className="border border-violet-500/40 rounded-lg p-5 backdrop-blur-md bg-violet-950/60"
                  >
                    <div className="text-sm text-purple-300 mb-1">{s.label}</div>
                    <div className="text-3xl font-bold text-white">{s.value}</div>
                  </div>
                ))}
              </div>
            </motion.div>

            {/* Center — video shows through */}
            <div className="hidden lg:block" />

            {/* Right — stats & quote */}
            <motion.div
              className="hidden lg:flex flex-col justify-center gap-6"
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, delay: 0.2 }}
            >
              <div className="border border-violet-500/40 rounded-xl p-8 backdrop-blur-md bg-violet-950/60">
                <p className="text-white italic mb-4 leading-relaxed text-base">
                  &ldquo;Multi-agent RL for content improvement.
                  This is production-level thinking.&rdquo;
                </p>
                <p className="text-sm text-purple-300">— Hackathon Judge</p>
              </div>

              <div className="border border-violet-500/40 rounded-xl p-8 backdrop-blur-md bg-violet-950/60">
                {[
                  { icon: '📊', value: '0.78', label: 'Trained Avg Reward'     },
                  { icon: '🎯', value: '3×',   label: 'Retention Improvement'  },
                  { icon: '🤖', value: '+27%', label: 'Total Reward Gain'      },
                ].map((s) => (
                  <div key={s.label} className="flex items-center gap-4 mb-5 last:mb-0">
                    <div className="w-12 h-12 rounded-full bg-violet-700/40 flex items-center justify-center shrink-0">
                      <span className="text-xl">{s.icon}</span>
                    </div>
                    <div>
                      <div className="text-3xl font-bold text-white">{s.value}</div>
                      <div className="text-sm text-purple-300">{s.label}</div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-violet-500 to-transparent opacity-25 ml-auto" />
            </motion.div>
          </div>

          {/* Rotating accent ring */}
          <motion.div
            className="absolute top-1/4 right-20 w-36 h-36 rounded-full border border-violet-500/20"
            animate={{ rotate: 360 }}
            transition={{ duration: 22, repeat: Infinity, ease: 'linear' }}
          />
        </section>

        {/* ── How It Works ─────────────────────────────────────────────── */}
        <section className="py-24 px-12 max-w-6xl mx-auto">
          <h2 className="font-display font-black text-4xl mb-12 tracking-tight">How It Works</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {HOW_IT_WORKS.map((item, i) => (
              <motion.div
                key={i}
                className="border border-violet-500/30 rounded-xl p-8 backdrop-blur-md bg-violet-950/50 hover:bg-violet-900/40 transition"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                viewport={{ once: true }}
              >
                <div className="text-4xl mb-4">{item.icon}</div>
                <h3 className="text-xl font-bold mb-2 text-white">{item.title}</h3>
                <p className="text-purple-200/80 leading-relaxed">{item.desc}</p>
              </motion.div>
            ))}
          </div>
        </section>

        {/* ── Phases strip ─────────────────────────────────────────────── */}
        <section className="py-12 px-12 max-w-6xl mx-auto">
          <p className="mb-4 text-xs font-bold uppercase tracking-widest text-purple-400/70">
            All 12 Phases — Gate PASS
          </p>
          <div className="flex flex-wrap gap-2">
            {Array.from({ length: 12 }, (_, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, scale: 0.8 }}
                whileInView={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.04 }}
                viewport={{ once: true }}
                className="flex items-center gap-1.5 rounded-lg border border-violet-500/30 bg-violet-950/50 backdrop-blur-sm px-3 py-2"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-violet-400" />
                <span className="text-xs font-semibold text-violet-300">Phase {i + 1}</span>
                <span className="text-xs text-violet-400">✓</span>
              </motion.div>
            ))}
          </div>
        </section>

        {/* ── Final CTA ────────────────────────────────────────────────── */}
        <section className="py-24 px-12 text-center border-t border-purple-800/40">
          <h2 className="font-display font-black text-4xl mb-4 tracking-tight">
            Ready to see it in action?
          </h2>
          <p className="text-purple-300/80 mb-10">
            Explore the live environment or run a local episode.
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <Link
              href={HF_SPACE_URL}
              target="_blank"
              className="inline-block px-10 py-4 bg-violet-600 hover:bg-violet-700 rounded-full font-semibold transition"
            >
              Launch on HF Space →
            </Link>
            <Link
              href="/episode"
              className="inline-block px-10 py-4 border border-purple-500/40 hover:bg-purple-900/50 rounded-full font-semibold transition"
            >
              Run Local Episode →
            </Link>
          </div>
        </section>

        <footer className="py-8 px-12 text-center text-purple-700/60 text-sm border-t border-purple-900/40">
          MetaDebate — Built for the Hackathon
        </footer>
      </div>
    </div>
  );
}
