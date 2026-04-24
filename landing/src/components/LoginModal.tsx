"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Mail, Lock, Loader2 } from "lucide-react";
import Button from "./Button";

interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSwitchToSignUp: () => void;
}

export default function LoginModal({ isOpen, onClose, onSwitchToSignUp }: LoginModalProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!email.trim() || !password) {
      setError("Please enter email and password.");
      return;
    }

    setLoading(true);

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), password }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || "Login failed. Please try again.");
        setLoading(false);
        return;
      }

      // Save auth to localStorage (same keys as legacy app)
      localStorage.setItem("projectkey_token", data.token);
      localStorage.setItem("projectkey_user", JSON.stringify(data.user));

      // Redirect to legacy app — it reads token from localStorage on init
      window.location.href = "/legacy";
    } catch {
      setError("Cannot connect to server. Please try again.");
      setLoading(false);
    }
  };

  const handleClose = () => {
    setEmail("");
    setPassword("");
    setError("");
    setLoading(false);
    onClose();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[200] flex items-center justify-center p-4"
          onClick={handleClose}
        >
          <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" />

          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            transition={{ duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
            onClick={(e) => e.stopPropagation()}
            className="relative w-full max-w-md glass-strong rounded-2xl overflow-hidden"
          >
            {/* Top gradient line */}
            <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-[#7170ff] to-transparent" />

            <div className="p-8">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-xl font-semibold text-[#f7f8f8]">Welcome back</h2>
                  <p className="text-[13px] text-[#8a8f98] mt-1">Sign in to your Context Bank workspace.</p>
                </div>
                <button
                  onClick={handleClose}
                  className="w-8 h-8 rounded-full bg-[rgba(255,255,255,0.05)] flex items-center justify-center text-[#8a8f98] hover:text-white hover:bg-[rgba(255,255,255,0.1)] transition-all"
                >
                  <X size={16} />
                </button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Error message */}
                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: -5 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="px-4 py-2.5 rounded-lg bg-[rgba(239,68,68,0.1)] border border-[rgba(239,68,68,0.2)] text-[13px] text-red-400"
                  >
                    {error}
                  </motion.div>
                )}

                <div>
                  <label className="block text-[13px] text-[#8a8f98] mb-1.5 font-medium">Email</label>
                  <div className="relative">
                    <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#62666d]" />
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@example.com"
                      disabled={loading}
                      className="w-full bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.08)] rounded-lg pl-10 pr-4 py-3 text-[14px] text-[#f7f8f8] placeholder:text-[#62666d] focus:outline-none focus:border-[#7170ff] focus:ring-1 focus:ring-[rgba(113,112,255,0.3)] transition-all disabled:opacity-50"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[13px] text-[#8a8f98] mb-1.5 font-medium">Password</label>
                  <div className="relative">
                    <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#62666d]" />
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••"
                      disabled={loading}
                      className="w-full bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.08)] rounded-lg pl-10 pr-4 py-3 text-[14px] text-[#f7f8f8] placeholder:text-[#62666d] focus:outline-none focus:border-[#7170ff] focus:ring-1 focus:ring-[rgba(113,112,255,0.3)] transition-all disabled:opacity-50"
                    />
                  </div>
                </div>

                <Button variant="primary" size="lg" className="w-full mt-2" type="submit" disabled={loading}>
                  {loading ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      Signing in...
                    </>
                  ) : (
                    "Sign in"
                  )}
                </Button>
              </form>

              <p className="text-center text-[13px] text-[#8a8f98] mt-4">
                Don&apos;t have an account?{" "}
                <button onClick={onSwitchToSignUp} className="text-[#7170ff] hover:text-[#828fff] transition-colors">
                  Sign up
                </button>
              </p>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
