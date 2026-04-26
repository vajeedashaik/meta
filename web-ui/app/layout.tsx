import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/Nav";

export const metadata: Metadata = {
  title: "Viral Script Debugging Engine",
  description: "Interactive storytelling interface for multi-agent RL learning"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-background bg-hero text-foreground antialiased">
        <main className="mx-auto max-w-7xl px-4 py-8 md:px-8">
          <Nav />
          {children}
        </main>
      </body>
    </html>
  );
}
