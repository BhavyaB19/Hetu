import type { Metadata } from "next";
import { Manrope, Playfair_Display } from "next/font/google";
import Link from "next/link";

import "./globals.css";

const playfair = Playfair_Display({ subsets: ["latin"], variable: "--font-playfair", display: "swap" });
const manrope = Manrope({ subsets: ["latin"], variable: "--font-manrope", display: "swap" });

export const metadata: Metadata = {
  title: "Hetu",
  description: "One verdict. Three stories. One connected view.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${playfair.variable} ${manrope.variable}`}>
      <body className="flex min-h-screen flex-col">
        <div role="note" className="border-b border-gold-line bg-gold-soft px-4 py-2 text-center text-xs text-ivory-muted">
          Research and education tool. Not legal advice or a predictor. Online opinion is not representative of all
          of India.
        </div>
        <header className="mx-auto w-full max-w-6xl px-4 py-5 sm:px-6">
          <Link href="/" className="font-serif text-2xl tracking-wide text-ivory">
            Hetu
          </Link>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 pb-16 sm:px-6">{children}</main>
      </body>
    </html>
  );
}
