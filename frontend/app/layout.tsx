import type { Metadata } from "next";
import "./globals.css";
import Header from "@/components/Header";

export const metadata: Metadata = {
  title: "Trading Assistant",
  description: "Personal intraday trading assistant for NSE",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen flex flex-col">
          <Header />
          <main className="flex-1 max-w-[1440px] w-full mx-auto px-4 py-4">
            {children}
          </main>
          <footer className="border-t border-border dark:border-border-dark py-3 text-center text-xs text-ink-muted">
            Demo mode - not investment advice. Signals are decision support only.
          </footer>
        </div>
      </body>
    </html>
  );
}
