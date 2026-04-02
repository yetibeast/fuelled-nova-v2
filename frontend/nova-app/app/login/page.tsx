"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, FormEvent } from "react";
import { login, getStoredUser } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  useEffect(() => {
    if (typeof window !== "undefined" && getStoredUser()) {
      router.replace("/");
    }
  }, [router]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!email.trim()) {
      setError("Email is required.");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      await login(email.trim().toLowerCase(), password);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
      setSubmitting(false);
    }
  }

  return (
    <div className="relative min-h-screen flex items-center justify-center p-4 overflow-hidden" style={{ background: "#080c18" }}>
      {/* Ambient glow blobs */}
      <div
        className="fixed top-[-30%] left-[-15%] w-[70vw] h-[70vh] pointer-events-none"
        style={{ background: "radial-gradient(ellipse, rgba(249,115,22,0.03) 0%, transparent 65%)" }}
      />
      <div
        className="fixed bottom-[-25%] right-[-10%] w-[60vw] h-[60vh] pointer-events-none"
        style={{ background: "radial-gradient(ellipse, rgba(0,180,216,0.025) 0%, transparent 65%)" }}
      />

      <div
        className="relative z-10 grid grid-cols-1 md:grid-cols-[1.1fr_1fr] w-full max-w-[1080px] min-h-[680px] rounded-[20px] overflow-hidden animate-[containerReveal_0.8s_ease-out]"
        style={{
          background: "#0e1525",
          border: "1px solid #253050",
          boxShadow: "0 30px 60px -15px rgba(0,0,0,0.55), 0 0 80px -30px rgba(249,115,22,0.04)",
        }}
      >
        {/* ---- Hero Panel ---- */}
        <section
          className="relative flex flex-col justify-end p-9 overflow-hidden min-h-[260px] md:min-h-0"
          style={{
            backgroundImage: "linear-gradient(180deg, rgba(8,12,24,0) 0%, rgba(8,12,24,0.15) 35%, rgba(8,12,24,0.65) 65%, rgba(8,12,24,0.92) 100%), url('/login-hero.png')",
            backgroundSize: "cover",
            backgroundPosition: "center 20%",
          }}
        >
          {/* Top gradient bar */}
          <div
            className="absolute top-0 left-0 right-0 h-[3px] opacity-75 z-[3]"
            style={{ background: "linear-gradient(90deg, #f97316 0%, #f97316 25%, #00b4d8 65%, transparent 100%)" }}
          />

          {/* Brand */}
          <div className="absolute top-9 left-9 z-[3] flex items-center gap-2.5">
            <div
              className="w-[34px] h-[34px] flex items-center justify-center rounded-[9px] text-white text-[16px] font-bold"
              style={{
                fontFamily: "'Space Grotesk', sans-serif",
                background: "#EF5D28",
                boxShadow: "0 2px 10px rgba(239,93,40,0.25)",
              }}
            >
              N
            </div>
            <div className="text-[#edf1f5] text-lg font-semibold tracking-wide" style={{ fontFamily: "'Space Grotesk', sans-serif", textShadow: "0 1px 8px rgba(0,0,0,0.5)" }}>
              fuelled<span className="text-[#00b4d8] font-light">nova</span>
            </div>
          </div>

          {/* Status live */}
          <span className="absolute top-10 right-9 z-[3] inline-flex items-center gap-1.5 text-[#f97316] font-mono text-[0.62rem] uppercase tracking-widest" style={{ textShadow: "0 1px 6px rgba(0,0,0,0.5)" }}>
            <span className="w-1.5 h-1.5 rounded-full bg-[#f97316] animate-pulse" />
            Systems online
          </span>

          {/* Hero content */}
          <div className="relative z-[2]">
            <h2 className="mb-3 text-[#edf1f5] text-[1.8rem] md:text-[1.8rem] font-semibold leading-tight" style={{ fontFamily: "'Space Grotesk', sans-serif", textShadow: "0 2px 12px rgba(0,0,0,0.4)" }}>
              <span className="text-[#f97316]">Industrial</span> Intelligence,<br />
              <span className="text-[#00b4d8]">Delivered.</span>
            </h2>
            <p className="max-w-[340px] text-[#8892a8] text-sm leading-relaxed" style={{ textShadow: "0 1px 6px rgba(0,0,0,0.3)" }}>
              AI-powered equipment analytics for the energy sector. Real-time pricing,
              market intelligence, and predictive valuations.
            </p>

          </div>
        </section>

        {/* ---- Auth Panel ---- */}
        <section className="flex flex-col justify-center px-7 py-8 md:px-11 md:py-12">
          <div className="mb-7">
            <h1 className="text-[#edf1f5] text-2xl font-semibold mb-1" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>Welcome back</h1>
            <p className="text-[#8892a8] text-sm">Sign in to access the pricing engine.</p>
          </div>

          <form onSubmit={handleSubmit}>
            {/* Email */}
            <div className="mb-3.5">
              <label className="block mb-1.5 text-[#8892a8] text-xs font-medium">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                autoComplete="email"
                autoFocus
                className="w-full rounded-[10px] px-3.5 py-2.5 text-sm text-[#edf1f5] placeholder-[#556178] outline-none transition-all"
                style={{ background: "#1a2340", border: "1px solid #253050" }}
                onFocus={(e) => { e.currentTarget.style.borderColor = "#00b4d8"; e.currentTarget.style.boxShadow = "0 0 0 3px rgba(0,180,216,0.15)"; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = "#253050"; e.currentTarget.style.boxShadow = "none"; }}
              />
            </div>

            {/* Password */}
            <div className="mb-3.5">
              <label className="block mb-1.5 text-[#8892a8] text-xs font-medium">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  className="w-full rounded-[10px] px-3.5 py-2.5 pr-11 text-sm text-[#edf1f5] placeholder-[#556178] outline-none transition-all"
                  style={{ background: "#1a2340", border: "1px solid #253050" }}
                  onFocus={(e) => { e.currentTarget.style.borderColor = "#00b4d8"; e.currentTarget.style.boxShadow = "0 0 0 3px rgba(0,180,216,0.15)"; }}
                  onBlur={(e) => { e.currentTarget.style.borderColor = "#253050"; e.currentTarget.style.boxShadow = "none"; }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute top-1/2 right-3 -translate-y-1/2 text-[#556178] hover:text-[#8892a8] transition-colors p-0 bg-transparent border-none leading-none"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </svg>
                  ) : (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            {/* Forgot */}
            <div className="flex items-center justify-end my-2 mb-5">
              <button type="button" className="text-[#00b4d8] text-xs font-medium bg-transparent border-none p-0" onClick={() => alert("Contact your administrator to reset your password.")}>
                Forgot password?
              </button>
            </div>

            {/* Error banner */}
            {error && (
              <div className="mb-3.5 rounded-[10px] px-3 py-2 text-xs leading-relaxed" style={{ background: "rgba(255,107,107,0.12)", border: "1px solid rgba(255,107,107,0.4)", color: "#ffb3b3" }}>
                {error}
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={submitting}
              className="relative w-full rounded-[10px] py-3 px-6 text-white text-sm font-semibold transition-all hover:translate-y-[-1px] disabled:opacity-85 disabled:cursor-not-allowed"
              style={{
                background: "linear-gradient(135deg, #00b4d8 0%, #0088a8 100%)",
                boxShadow: submitting ? "none" : undefined,
              }}
            >
              <span className="relative z-10 inline-flex items-center gap-2">
                {submitting ? (
                  <>
                    <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Signing in
                  </>
                ) : (
                  "Sign in to Nova"
                )}
              </span>
            </button>
          </form>

          {/* Footer */}
          <div className="mt-5 text-center text-[#556178] text-[0.7rem] leading-relaxed">
            Fuelled Energy Marketing Inc.
          </div>
        </section>
      </div>
    </div>
  );
}
