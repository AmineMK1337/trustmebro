"use client";

import Image from "next/image";
import { useState } from "react";
import {
  Download, ChevronRight, Play, ChevronDown, ChevronUp,
  Shield, Zap, ScanSearch, Link2, AlertTriangle,
  CheckCircle2, Globe, Eye, FileText, Menu, X,
  CircleAlert, BadgeCheck, MessageSquare, Heart, Repeat2
} from "lucide-react";

// ─────────────────────────────────────────────
function BrandLogo({ size, className = "" }: { size: number; className?: string }) {
  return (
    <Image
      src="/logo.png"
      alt="TrustMeBro logo"
      width={size}
      height={size}
      className={className}
    />
  );
}

// ─────────────────────────────────────────────
// DATA
// ─────────────────────────────────────────────
const NAV_LINKS = [
  { label: "About", href: "#about" },
  { label: "How It Works", href: "#how-it-works" },
  { label: "Features", href: "#features" },
  { label: "Security", href: "#security" },
];

const FEATURES = [
  {
    icon: <ScanSearch className="w-6 h-6 text-indigo-400" />,
    title: "Content Authenticity Detection",
    desc: "Detect whether images, videos, audio, or documents have been tampered with or AI-generated — with a clear confidence score and highlighted suspicious regions.",
  },
  {
    icon: <Globe className="w-6 h-6 text-indigo-400" />,
    title: "Contextual Consistency Analysis",
    desc: "Identify when real content is reused in a misleading context. TrustMeBro checks whether captions, descriptions, and narratives align with the actual content.",
  },
  {
    icon: <Shield className="w-6 h-6 text-indigo-400" />,
    title: "Source Credibility Scoring",
    desc: "Analyze account behavior patterns, writing style consistency, and suspicious URLs to determine whether a source can actually be trusted.",
  },
];

const STEPS = [
  {
    num: "1",
    title: "Install the Extension",
    desc: "Add TrustMeBro to your Chrome browser with a single click — no account needed to get started.",
    icon: <Download className="w-5 h-5" />,
  },
  {
    num: "2",
    title: "Browse Social Media",
    desc: "Scroll Instagram, X, or LinkedIn as usual. TrustMeBro silently monitors content in the background.",
    icon: <Eye className="w-5 h-5" />,
  },
  {
    num: "3",
    title: "Submit Content for Analysis",
    desc: "Click the TrustMeBro icon on any post, image, or article to trigger an instant AI-powered verification.",
    icon: <ScanSearch className="w-5 h-5" />,
  },
  {
    num: "4",
    title: "Read the Verification Report",
    desc: "Get a clear verdict — Verified, Suspicious, or Manipulated — with a confidence score and plain-language explanation.",
    icon: <FileText className="w-5 h-5" />,
  },
  {
    num: "5",
    title: "Act with Confidence",
    desc: "Share, flag, or ignore content knowing exactly what the AI found — and why. Stay informed, stay safe.",
    icon: <CheckCircle2 className="w-5 h-5" />,
  },
];

const INTEGRATIONS = [
  { label: "Instagram", Icon: Globe },
  { label: "X (Twitter)", Icon: Link2 },
  { label: "LinkedIn", Icon: BadgeCheck },
];

const FAQS_LEFT = [
  {
    q: "How does TrustMeBro detect manipulated content?",
    a: "TrustMeBro uses AI/ML models trained on large datasets of authentic and tampered media. It looks for pixel-level anomalies, compression artifacts, inconsistencies in lighting and shadows, and metadata signals to detect manipulation.",
  },
  {
    q: "Is TrustMeBro free to use?",
    a: "Yes, TrustMeBro is completely free to install and use. There are no hidden fees or subscription plans.",
  },
  {
    q: "What does the confidence score mean?",
    a: "The confidence score (0–100%) reflects how certain the AI is about its verdict. A score above 80% indicates a high-confidence finding. We always recommend human judgment alongside the AI result.",
  },
];

const FAQS_RIGHT = [
  {
    q: "Which platforms does TrustMeBro support?",
    a: "TrustMeBro currently integrates natively with Instagram, X (Twitter), and LinkedIn, with more platforms on our roadmap.",
  },
  {
    q: "What is contextual consistency analysis?",
    a: "This feature checks whether content is being used in a misleading context — for example, real footage from one event shared as if it happened somewhere else. TrustMeBro cross-references captions, dates, and geolocation signals.",
  },
  {
    q: "Is my data private when I use TrustMeBro?",
    a: "TrustMeBro processes analysis requests without storing the original media. We do not sell user data and are committed to full transparency about how AI decisions are made.",
  },
];

// ─────────────────────────────────────────────
// MOCK UI COMPONENTS
// ─────────────────────────────────────────────

function VerificationPopupMock() {
  return (
    <div className="bg-gray-900 rounded-2xl shadow-2xl p-4 w-[320px] font-sans text-xs border border-gray-700">
      <div className="flex items-center gap-2 mb-4">
        <BrandLogo size={20} className="w-5 h-5" />
        <span className="font-semibold text-gray-100 text-sm">TrustMeBro</span>
        <span className="ml-auto text-[10px] bg-amber-500/20 text-amber-400 border border-amber-500/30 font-bold px-2 py-0.5 rounded-full flex items-center gap-1">
          <AlertTriangle className="w-2.5 h-2.5" /> Suspicious
        </span>
      </div>
      <div className="bg-gray-800 rounded-xl h-24 flex items-center justify-center mb-4 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-gray-800 to-gray-700" />
        <div className="relative flex flex-col items-center gap-2 text-gray-300 z-10">
          <ScanSearch className="w-6 h-6 text-indigo-400" />
          <span className="text-[11px] font-medium">Analyzing image structure…</span>
        </div>
        <div className="absolute inset-0 border border-amber-500/40 rounded-xl opacity-60 z-10" />
        <div className="absolute top-0 left-0 right-0 h-10 bg-gradient-to-b from-indigo-500/20 to-transparent animate-scan z-0" />
      </div>
      <div className="mb-4">
        <div className="flex justify-between mb-1.5">
          <span className="text-gray-300">Manipulation confidence</span>
          <span className="text-amber-400 font-bold">74%</span>
        </div>
        <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
          <div className="h-full bg-gradient-to-r from-amber-400 to-orange-500 rounded-full" style={{ width: "74%" }} />
        </div>
      </div>
      <div className="space-y-2 mb-4">
        {[
          { label: "Pixel anomalies detected", hit: true },
          { label: "Metadata stripped", hit: true },
          { label: "Caption matches context", hit: false },
        ].map((f) => (
          <div key={f.label} className="flex items-center gap-2.5">
            {f.hit
              ? <CircleAlert className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />
              : <BadgeCheck className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />}
            <span className={f.hit ? "text-amber-300" : "text-gray-400"}>{f.label}</span>
          </div>
        ))}
      </div>
      <p className="text-[11px] text-gray-400 italic border-t border-gray-800 pt-3">
        "Image shows signs of localized editing around the subject boundary and mismatched lighting."
      </p>
    </div>
  );
}

// Replacement for Page 3 (Feature 1) Image
function SocialMediaScanMockup() {
  return (
    <div className="bg-gray-950 rounded-2xl shadow-2xl p-5 w-[340px] font-sans text-xs border border-gray-800 flex flex-col gap-3">
      {/* Social Post Header */}
      <div className="flex items-center gap-3 mb-2">
        <div className="w-10 h-10 rounded-full bg-gray-800 flex items-center justify-center">
          <Globe className="w-5 h-5 text-gray-500" />
        </div>
        <div className="flex flex-col">
          <span className="font-bold text-gray-100 text-sm">Global News Network</span>
          <span className="text-gray-500">@globalnews • 2h</span>
        </div>
      </div>
      {/* Post Content */}
      <p className="text-gray-300 text-[13px] leading-relaxed">
        Breaking: Unbelievable new footage emerges from the city center. You won't believe what happened next...
      </p>
      {/* Media with Scan Overlay */}
      <div className="relative h-40 rounded-xl bg-gray-800 border border-gray-700 overflow-hidden mt-1">
        <div className="absolute inset-0 bg-gradient-to-tr from-gray-700 to-gray-600" />
        {/* The TrustMeBro Extension Overlay */}
        <div className="absolute inset-0 bg-gray-950/60 backdrop-blur-[2px] flex items-center justify-center">
          <div className="bg-gray-900 border border-indigo-500/40 p-4 rounded-xl shadow-2xl flex flex-col items-center gap-3">
            <div className="relative">
               <ScanSearch className="w-8 h-8 text-indigo-400 relative z-10" />
               <div className="absolute inset-0 bg-indigo-400 blur-md opacity-50 z-0"></div>
            </div>
            <span className="text-indigo-100 font-semibold text-sm">Scanning Image...</span>
            <div className="w-32 h-1.5 bg-gray-800 rounded-full overflow-hidden">
              <div className="w-2/3 h-full bg-indigo-500 rounded-full animate-pulse" />
            </div>
          </div>
        </div>
      </div>
      {/* Social Actions */}
      <div className="flex items-center justify-between text-gray-500 mt-2 px-2">
        <MessageSquare className="w-4 h-4" />
        <Repeat2 className="w-4 h-4" />
        <Heart className="w-4 h-4" />
        <ShareIcon className="w-4 h-4" />
      </div>
    </div>
  );
}
function ShareIcon({ className }: { className?: string }) {
  return <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" /></svg>;
}

// Replacement for Page 4 (Feature 2) Image
function DetailedReportMockup() {
  return (
    <div className="bg-gray-900 rounded-2xl shadow-2xl p-5 w-[340px] font-sans text-xs border border-gray-700 flex flex-col gap-4 text-gray-200">
      <div className="flex items-center gap-3 border-b border-gray-800 pb-3">
        <div className="p-2 bg-purple-500/20 rounded-lg border border-purple-500/30">
          <FileText className="w-5 h-5 text-purple-400" />
        </div>
        <div>
          <span className="font-bold text-sm text-gray-100 block">Full Verification Report</span>
          <span className="text-[10px] text-gray-500">ID: TRST-9928-11A</span>
        </div>
      </div>

      <div className="space-y-3">
        {/* Axis 1 */}
        <div className="bg-gray-950 p-3.5 rounded-xl border border-gray-800">
          <div className="flex justify-between items-center mb-2.5">
            <span className="text-gray-300 font-semibold flex items-center gap-1.5">
              <ScanSearch className="w-4 h-4 text-amber-400" /> Authenticity Risk
            </span>
            <span className="text-amber-400 font-bold text-sm">62%</span>
          </div>
          <div className="h-1.5 bg-gray-800 rounded-full mb-2">
            <div className="h-full w-[62%] bg-gradient-to-r from-amber-500 to-amber-400 rounded-full" />
          </div>
          <p className="text-[11px] text-gray-400 leading-relaxed">AI-generation artifacts detected in background textures.</p>
        </div>

        {/* Axis 2 */}
        <div className="bg-gray-950 p-3.5 rounded-xl border border-gray-800">
          <div className="flex justify-between items-center mb-2.5">
            <span className="text-gray-300 font-semibold flex items-center gap-1.5">
              <Globe className="w-4 h-4 text-emerald-400" /> Context Match
            </span>
            <span className="text-emerald-400 font-bold text-sm">95%</span>
          </div>
          <div className="h-1.5 bg-gray-800 rounded-full mb-2">
            <div className="h-full w-[95%] bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-full" />
          </div>
          <p className="text-[11px] text-gray-400 leading-relaxed">Caption aligns with verified geolocated visual data.</p>
        </div>

        {/* Axis 3 */}
        <div className="bg-gray-950 p-3.5 rounded-xl border border-gray-800">
          <div className="flex justify-between items-center mb-2.5">
            <span className="text-gray-300 font-semibold flex items-center gap-1.5">
              <BadgeCheck className="w-4 h-4 text-red-400" /> Source Credibility
            </span>
            <span className="text-red-400 font-bold text-sm">12%</span>
          </div>
          <div className="h-1.5 bg-gray-800 rounded-full mb-2">
            <div className="h-full w-[12%] bg-gradient-to-r from-red-500 to-red-400 rounded-full" />
          </div>
          <p className="text-[11px] text-gray-400 leading-relaxed">Known bot network. Abnormally high posting frequency.</p>
        </div>
      </div>
    </div>
  );
}


// ─────────────────────────────────────────────
// REUSABLE COMPONENTS
// ─────────────────────────────────────────────
function FAQItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-gray-800 py-4 cursor-pointer" onClick={() => setOpen((v) => !v)}>
      <div className="flex justify-between items-center gap-4">
        <span className="text-gray-200 font-medium text-sm">{q}</span>
        {open
          ? <ChevronUp className="w-4 h-4 text-gray-500 flex-shrink-0" />
          : <ChevronDown className="w-4 h-4 text-gray-500 flex-shrink-0" />}
      </div>
      {open && <p className="text-gray-400 text-sm mt-3 leading-relaxed">{a}</p>}
    </div>
  );
}

// ─────────────────────────────────────────────
// MAIN PAGE
// ─────────────────────────────────────────────
export default function Home() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="font-sans antialiased bg-gray-950 text-gray-100 overflow-x-hidden selection:bg-indigo-500/30">

      {/* ── HEADER / HERO ─────────────────────────────── */}
      <header id="about" className="bg-gray-950 text-white border-b border-gray-900">
        <nav className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <BrandLogo size={32} />
            <span className="font-bold text-xl tracking-tight">TrustMeBro</span>
          </div>
          <ul className="hidden md:flex items-center gap-8 text-sm text-gray-400 font-medium">
            {NAV_LINKS.map(({ label, href }) => (
              <li key={label}><a href={href} className="hover:text-indigo-400 transition-colors">{label}</a></li>
            ))}
          </ul>
          <a href="#" className="hidden md:flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold px-5 py-2.5 rounded-lg transition-colors shadow-lg shadow-indigo-600/20">
            <Download className="w-4 h-4" /> Download
          </a>
          <button className="md:hidden text-gray-400 hover:text-white" onClick={() => setMobileOpen((v) => !v)}>
            {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </nav>

        {mobileOpen && (
          <div className="md:hidden border-t border-gray-900 px-6 py-4 space-y-3 bg-gray-950">
            {NAV_LINKS.map(({ label, href }) => (
              <a key={label} href={href} className="block text-gray-300 hover:text-indigo-400 text-sm font-medium">{label}</a>
            ))}
            <a href="#" className="flex items-center gap-2 bg-indigo-600 text-white text-sm font-semibold px-5 py-2.5 rounded-lg w-fit mt-4">
              <Download className="w-4 h-4" /> Download
            </a>
          </div>
        )}

        <div className="max-w-7xl mx-auto px-6 pt-20 pb-24 flex flex-col lg:flex-row items-center gap-16">
          <div className="flex-1 max-w-xl">
            <div className="inline-flex items-center gap-2 bg-indigo-900/30 border border-indigo-500/30 text-indigo-300 text-xs font-semibold px-4 py-1.5 rounded-full mb-6">
              <Zap className="w-3 h-3" /> AI-Powered Content Verification
            </div>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold leading-tight mb-6">
              Can You Trust What{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400">You See Online?</span>
            </h1>
            <p className="text-gray-400 text-lg leading-relaxed mb-10">
              TrustMeBro is a Chrome extension that uses AI to detect manipulated images,
              deepfakes, AI-generated content, and misleading context right inside your
              social media feed. Get a clear verdict in seconds.
            </p>
            <div className="flex flex-wrap items-center gap-5">
              <a href="#" className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-7 py-3.5 rounded-xl transition-colors shadow-lg shadow-indigo-600/20">
                <Download className="w-5 h-5" /> Download Free
              </a>
              <a href="#" className="flex items-center gap-3 text-gray-300 hover:text-white font-medium transition-colors group">
                <div className="w-10 h-10 rounded-full border border-gray-700 group-hover:border-indigo-400 flex items-center justify-center transition-colors">
                  <Play className="w-4 h-4 fill-current group-hover:text-indigo-400" />
                </div>
                Watch Demo
              </a>
            </div>
          </div>
          <div className="flex-1 flex justify-center lg:justify-end">
            <div className="relative">
              <div className="absolute -inset-10 bg-indigo-600/20 rounded-[3rem] blur-3xl" />
              <VerificationPopupMock />
            </div>
          </div>
        </div>

        {/* Feature pills */}
        <div className="border-t border-gray-900 bg-gray-950/50">
          <div className="max-w-7xl mx-auto px-6 py-12 grid grid-cols-1 sm:grid-cols-3 gap-10">
            {FEATURES.map((f) => (
              <div key={f.title} className="flex gap-4 items-start">
                <div className="p-2.5 bg-gray-900 border border-gray-800 rounded-xl shadow-inner mt-0.5">{f.icon}</div>
                <div>
                  <h3 className="font-semibold text-gray-100 text-base mb-1.5">{f.title}</h3>
                  <p className="text-gray-400 text-sm leading-relaxed">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </header>

      {/* ── INTEGRATIONS ─────────────────────────────── */}
      <section className="py-14 border-b border-gray-900 bg-gray-950">
        <div className="max-w-7xl mx-auto px-6">
          <p className="text-center text-gray-500 text-xs uppercase tracking-widest mb-10 font-semibold">
            Works natively inside
          </p>
          <div className="flex flex-wrap justify-center items-center gap-12 md:gap-24">
            {INTEGRATIONS.map(({ label, Icon }) => (
              <div key={label} className="flex flex-col items-center gap-3 group cursor-default">
                <div className="w-14 h-14 rounded-2xl bg-gray-900 border border-gray-800 group-hover:border-indigo-500 group-hover:bg-indigo-950/30 transition-all flex items-center justify-center shadow-lg">
                  <Icon className="w-7 h-7 text-gray-400 group-hover:text-indigo-400 transition-colors" />
                </div>
                <span className="text-gray-500 text-sm font-medium group-hover:text-gray-300 transition-colors">
                  {label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ─────────────────────────────── */}
      <section id="how-it-works" className="py-24 bg-gray-950">
        <div className="max-w-7xl mx-auto px-6">
          <p className="text-center text-indigo-500 text-sm font-bold uppercase tracking-widest mb-3">HOW IT WORKS</p>
          <h2 className="text-center text-3xl md:text-5xl font-extrabold mb-5 text-gray-100">
            How TrustMeBro Works
          </h2>
          <p className="text-center text-gray-400 max-w-2xl mx-auto mb-16 text-base leading-relaxed">
            From installation to verdict in under 10 seconds — no technical knowledge required.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {STEPS.map((s) => (
              <div key={s.num} className="flex gap-5 items-start p-6 rounded-2xl bg-gray-900 border border-gray-800 hover:border-indigo-500/50 hover:bg-gray-800/50 transition-all shadow-lg">
                <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white font-bold text-base flex-shrink-0 shadow-lg shadow-indigo-600/20">
                  {s.num}
                </div>
                <div>
                  <h3 className="font-semibold text-gray-100 text-lg mb-2">{s.title}</h3>
                  <p className="text-gray-400 text-sm leading-relaxed">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FEATURE SHOWCASE 1 (Page 3 Replacement) ─── */}
      <section id="features" className="py-24 bg-gray-900 border-y border-gray-800">
        <div className="max-w-7xl mx-auto px-6 flex flex-col lg:flex-row items-center gap-20">
          <div className="flex-1 max-w-lg">
            <span className="inline-block text-indigo-400 text-xs font-bold uppercase tracking-widest mb-4 bg-indigo-500/10 border border-indigo-500/20 px-3 py-1.5 rounded-full">
              Content Authenticity
            </span>
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-extrabold text-gray-100 mb-6 leading-tight">
              Detect Fakes Before They Spread
            </h2>
            <p className="text-gray-400 text-lg leading-relaxed mb-8">
              TrustMeBro's AI models scan for pixel-level anomalies, compression artifacts,
              deepfake signatures, and GAN-generated patterns — providing a confidence score
              and highlighting suspicious regions directly on the post.
            </p>
            <ul className="space-y-4 mb-10">
              {["Images, videos, audio & documents", "Deepfake & AI-generation detection", "Confidence score + plain-language reasoning"].map((item) => (
                <li key={item} className="flex items-center gap-3 text-base text-gray-300">
                  <CheckCircle2 className="w-5 h-5 text-indigo-500 flex-shrink-0" /> {item}
                </li>
              ))}
            </ul>
            <a href="#" className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-7 py-3.5 rounded-xl transition-colors shadow-lg shadow-indigo-600/20">
              Get For Free
            </a>
          </div>
          <div className="flex-1 flex justify-center">
            <div className="relative">
              {/* Glowing Background */}
              <div className="absolute -inset-10 bg-indigo-600/20 rounded-full blur-3xl" />
              {/* Mockup instead of static image */}
              <div className="relative z-10 transform hover:scale-105 transition-transform duration-500">
                <SocialMediaScanMockup />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── FEATURE SHOWCASE 2 (Page 4 Replacement) ─── */}
      <section className="py-24 bg-gray-950">
        <div className="max-w-7xl mx-auto px-6 flex flex-col lg:flex-row-reverse items-center gap-20">
          <div className="flex-1 max-w-lg">
            <span className="inline-block text-purple-400 text-xs font-bold uppercase tracking-widest mb-4 bg-purple-500/10 border border-purple-500/20 px-3 py-1.5 rounded-full">
              Full Verification Report
            </span>
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-extrabold text-gray-100 mb-6 leading-tight">
              Understand Exactly Why Content Was Flagged
            </h2>
            <p className="text-gray-400 text-lg leading-relaxed mb-8">
              Every verdict comes with a structured report covering all three verification axes:
              content authenticity, contextual consistency, and source credibility — so you
              always know the full picture, not just a red flag.
            </p>
            <ul className="space-y-4 mb-10">
              {["Three-axis analysis in one report", "Context mismatch & reuse detection", "Source behavior & domain credibility"].map((item) => (
                <li key={item} className="flex items-center gap-3 text-base text-gray-300">
                  <CheckCircle2 className="w-5 h-5 text-purple-500 flex-shrink-0" /> {item}
                </li>
              ))}
            </ul>
            <a href="#" className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white font-semibold px-7 py-3.5 rounded-xl transition-colors shadow-lg shadow-purple-600/20">
              Get Started
            </a>
          </div>
          <div className="flex-1 flex justify-center">
            <div className="relative">
               {/* Glowing Background */}
              <div className="absolute -inset-10 bg-purple-600/20 rounded-full blur-3xl" />
              {/* Mockup instead of static image */}
              <div className="relative z-10 transform hover:-translate-y-2 transition-transform duration-500">
                <DetailedReportMockup />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── FAQ ──────────────────────────────────────── */}
      <section id="security" className="py-24 bg-gray-900 border-t border-gray-800">
        <div className="max-w-7xl mx-auto px-6">
          <p className="text-center text-indigo-500 text-sm font-bold uppercase tracking-widest mb-3">
            FREQUENTLY ASKED QUESTIONS
          </p>
          <h2 className="text-center text-3xl md:text-5xl font-extrabold mb-16 text-gray-100">Got Questions? We&apos;ve Got Answers!</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-x-16 gap-y-4">
            <div className="space-y-2">{FAQS_LEFT.map((f) => <FAQItem key={f.q} {...f} />)}</div>
            <div className="space-y-2">{FAQS_RIGHT.map((f) => <FAQItem key={f.q} {...f} />)}</div>
          </div>
        </div>
      </section>

      {/* ── FOOTER ───────────────────────────────────── */}
      <footer className="bg-gray-950 text-gray-400 border-t border-gray-900">
        <div className="max-w-7xl mx-auto px-6 py-16 grid grid-cols-1 md:grid-cols-4 gap-12">
          <div className="md:col-span-1">
            <div className="flex items-center gap-3 mb-4">
                <BrandLogo size={28} className="w-7 h-7" />
              <span className="text-gray-100 font-bold text-lg">TrustMeBro</span>
            </div>
            <p className="text-sm leading-relaxed mb-6">Your AI-Powered Truth Companion for navigating the modern web.</p>
            <p className="text-xs font-bold tracking-wider text-gray-500 mb-3 uppercase">Follow us on:</p>
            <div className="flex gap-4">
              {INTEGRATIONS.map(({ label, Icon }) => (
                <a key={label} href="#" className="w-10 h-10 rounded-full bg-gray-900 border border-gray-800 flex items-center justify-center hover:border-indigo-500 hover:text-indigo-400 transition-colors" aria-label={label}>
                  <Icon className="w-4 h-4" />
                </a>
              ))}
            </div>
          </div>
          <div>
            <h4 className="text-gray-100 font-bold text-base mb-5">Features</h4>
            <ul className="space-y-3 text-sm">
              {["Content Authenticity", "Contextual Consistency", "Source Credibility", "Real-Time Alerts"].map((l) => (
                <li key={l}><a href="#" className="hover:text-indigo-400 transition-colors">{l}</a></li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="text-gray-100 font-bold text-base mb-5">About</h4>
            <ul className="space-y-3 text-sm">
              {["Our Mission", "Research", "Press Release", "Partner with us"].map((l) => (
                <li key={l}><a href="#" className="hover:text-indigo-400 transition-colors">{l}</a></li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="text-gray-100 font-bold text-base mb-5">Download</h4>
            <ul className="space-y-3 text-sm">
              {["For Chrome", "For Firefox", "For Edge", "For Safari"].map((l) => (
                <li key={l}><a href="#" className="hover:text-indigo-400 transition-colors">{l}</a></li>
              ))}
            </ul>
          </div>
        </div>
        <div className="border-t border-gray-900">
          <div className="max-w-7xl mx-auto px-6 py-6 flex flex-col sm:flex-row justify-between items-center gap-4 text-sm">
            <span>© 2024 TrustMeBro. All rights reserved.</span>
            <div className="flex gap-6 font-medium">
              {["Privacy Policy", "Cookies", "Security", "Terms of Service"].map((l) => (
                <a key={l} href="#" className="hover:text-gray-200 transition-colors">{l}</a>
              ))}
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}