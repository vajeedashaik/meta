"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const links = [
  { href: "/", label: "Home" },
  { href: "/episode", label: "Episode" },
  { href: "/ab", label: "A/B Battle" },
  { href: "/retention", label: "Retention" },
  { href: "/memory", label: "Memory" },
  { href: "/learning", label: "Learning" }
];

export function Nav() {
  const pathname = usePathname();
  return (
    <nav className="mb-8 flex flex-wrap gap-2 rounded-2xl border border-blue-100 bg-white/90 p-2 shadow-soft">
      {links.map((link) => (
        <Link
          key={link.href}
          href={link.href}
          className={cn(
            "rounded-xl px-3 py-2 text-sm transition-colors",
            pathname === link.href ? "bg-blue-100 text-blue-700" : "text-slate-600 hover:bg-blue-50"
          )}
        >
          {link.label}
        </Link>
      ))}
    </nav>
  );
}
