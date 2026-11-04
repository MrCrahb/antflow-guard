import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AntFlow Guard — Live FX & Settlement Operator Console",
  description: "Cross-border payment routing, FX settlement, and real-time AI anomaly triage engine.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#0b132b] text-gray-100 antialiased">
        {children}
      </body>
    </html>
  );
}
