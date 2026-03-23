import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HPMOCD Community Explorer",
  description:
    "Interactive dashboard for exploring High-Performance Multi-Objective Community Detection results on the WebMedia co-authorship network.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full overflow-hidden">{children}</body>
    </html>
  );
}
