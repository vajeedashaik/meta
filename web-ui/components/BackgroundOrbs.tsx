'use client';

const ORBS = [
  {
    size: 640,
    top: '5%',
    left: '8%',
    color: 'rgba(109,40,217,0.13)',
    animation: 'orb-drift 32s ease-in-out infinite',
  },
  {
    size: 520,
    top: '55%',
    left: '65%',
    color: 'rgba(139,92,246,0.10)',
    animation: 'orb-drift-2 28s ease-in-out infinite',
  },
  {
    size: 400,
    top: '30%',
    left: '45%',
    color: 'rgba(76,29,149,0.14)',
    animation: 'orb-drift-3 22s ease-in-out infinite',
  },
];

export function BackgroundOrbs() {
  return (
    <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
      {ORBS.map((orb, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            top: orb.top,
            left: orb.left,
            width: orb.size,
            height: orb.size,
            borderRadius: '50%',
            background: `radial-gradient(circle, ${orb.color}, transparent 70%)`,
            filter: 'blur(60px)',
            animation: orb.animation,
            willChange: 'transform',
          }}
        />
      ))}
    </div>
  );
}
