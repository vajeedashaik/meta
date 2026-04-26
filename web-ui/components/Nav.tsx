"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const links = [
  { href: "/landing",          label: "Home",       icon: "🏠" },
  { href: "/dashboard",        label: "Dashboard",  icon: "🖥️" },
  { href: "/episode",          label: "Episode",    icon: "▶️" },
  { href: "/ab",               label: "A/B Battle", icon: "⚔️" },
  { href: "/retention",        label: "Retention",  icon: "📈" },
  { href: "/memory",           label: "Memory",     icon: "🧠" },
  { href: "/learning",         label: "Learning",   icon: "📊" },
  { href: "/learning-playback",label: "Timeline",   icon: "🎬" },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <nav className="mb-8 flex flex-wrap gap-1.5 rounded-2xl border border-purple-700/30 bg-purple-950/60 p-2 shadow-soft backdrop-blur-md">
      {links.map((link) => {
        const active = pathname === link.href;
        return (
          <Link
            key={link.href}
            href={link.href}
            className={cn(
              "flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-medium transition-all",
              active
                ? "bg-violet-600 text-white shadow-sm"
                : "text-purple-200 hover:bg-purple-800/50 hover:text-white"
            )}
          >
            <span className="text-base leading-none">{link.icon}</span>
            <span>{link.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
