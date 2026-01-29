import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { LogProvider } from "@/lib/log-context";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Dispute Resolution Chat",
  description: "AI-powered dispute resolution system using CrewAI agents",
  keywords: "dispute, resolution, chat, AI, CrewAI, financial",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <LogProvider>
          <div className="min-h-screen bg-background">{children}</div>
        </LogProvider>
      </body>
    </html>
  );
}
