import { Nav } from "@/components/Nav";
import { BackgroundOrbs } from "@/components/BackgroundOrbs";

export default function SiteLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative min-h-screen bg-background text-foreground overflow-hidden">
      <BackgroundOrbs />
      <main className="relative z-10 mx-auto max-w-7xl px-4 py-8 md:px-8">
        <Nav />
        {children}
      </main>
    </div>
  );
}
