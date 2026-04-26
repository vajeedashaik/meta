"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const links = [
  { href: "/",          label: "Home",       icon: "🏠" },
  { href: "/dashboard", label: "Dashboard",  icon: "🖥️" },
  { href: "/episode",   label: "Episode",    icon: "▶️" },
  { href: "/ab",        label: "A/B Battle", icon: "⚔️" },
  { href: "/retention", label: "Retention",  icon: "📈" },
  { href: "/memory",    label: "Memory",     icon: "🧠" },
  { href: "/learning",  label: "Learning",   icon: "📊" }
];

export function Nav() {
  const pathname = usePathname();
  return (
    <nav className="mb-8 flex flex-wrap gap-1.5 rounded-2xl border border-blue-100 bg-white/90 p-2 shadow-soft">
      {links.map((link) => {
        const active = pathname === link.href;
        return (
          <Link
            key={link.href}
            href={link.href}
            className={cn(
              "flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-medium transition-all",
              active
                ? "bg-primary text-white shadow-sm"
                : "text-slate-600 hover:bg-blue-50 hover:text-primary"
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
