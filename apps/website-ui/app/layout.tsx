import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "TrustMeBro – Can You Trust What You See Online?",
  description:
    "TrustMeBro is a Chrome extension that uses AI to detect manipulated images, deepfakes, AI-generated content, and misleading context right inside your browser.",
  icons: {
    icon: "/logo.png",
    shortcut: "/logo.png",
    apple: "/logo.png",
  },
  keywords: ["fake news", "ai detection", "deepfake scanner", "chrome extension"],
  openGraph: {
    title: "TrustMeBro – Can You Trust What You See Online?",
    description:
      "Detect fakes before they spread with TrustMeBro's real-time content authenticity Chrome extension.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased bg-gray-950 text-gray-100`}>
        {children}
      </body>
    </html>
  );
}