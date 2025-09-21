import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import Link from "next/link";
import Image from "next/image";
import "./globals.css";
import BackgroundFX from "./BackgroundFX";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Scheduly",
  description: "Build your dream schedule",
  icons: {
    icon: "/scheduly.ico",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body
        className={`${inter.variable} ${spaceGrotesk.variable} antialiased font-inter`}
      >
        <BackgroundFX />
        <header className="fixed top-0 inset-x-0 z-50 border-b border-black/[.08] dark:border-white/[.12] bg-background/70 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="mx-auto max-w-6xl px-4 sm:px-6 h-16 flex items-center justify-between">
            <Link
              href="/"
              className="flex items-center gap-2 text-2xl font-semibold tracking-tight font-camera hover:opacity-80 transition-opacity"
            >
              <Image
                src="/scheduly.svg"
                alt="Scheduly"
                width={36}
                height={36}
              />
              Scheduly
            </Link>
            <div className="flex items-center gap-4 text-base">
              <span className="text-sm text-black/60 dark:text-white/60">
                Build your schedule instantly
              </span>
            </div>
          </div>
        </header>
        <main className="pt-16">{children}</main>
      </body>
    </html>
  );
}
