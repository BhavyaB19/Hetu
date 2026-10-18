import type { Metadata } from "next";
import { Manrope, Playfair_Display } from "next/font/google";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { ToastProvider } from "@/components/ui/Toast";
import "./globals.css";

const playfair = Playfair_Display({ subsets: ["latin"], variable: "--font-playfair", display: "swap" });
const manrope = Manrope({ subsets: ["latin"], variable: "--font-manrope", display: "swap" });

export const metadata: Metadata = {
  title: "Hetu — Three Stories. One Connected Verdict.",
  description: "Comparing court judgments, media framing, and public reaction in Indian criminal jurisprudence.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${playfair.variable} ${manrope.variable}`}>
      <body className="flex min-h-screen flex-col bg-ink text-ivory">
        <ToastProvider>
          <DisclaimerBanner />
          <Header />
          <main role="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">{children}</main>
          <Footer />
        </ToastProvider>
      </body>
    </html>
  );
}
