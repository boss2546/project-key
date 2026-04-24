"use client";

import React from "react";
import { motion } from "framer-motion";
import { ArrowRight, Play } from "lucide-react";
import Button from "./Button";

interface HeroSectionProps {
  onSignUpClick: () => void;
}

export default function HeroSection({ onSignUpClick }: HeroSectionProps) {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16">
      {/* Animated background orbs */}
      <div className="absolute inset-0 pointer-events-none">
        <div
          className="absolute w-[600px] h-[600px] rounded-full opacity-30"
          style={{
            background: "radial-gradient(circle, rgba(94,106,210,0.4), transparent 70%)",
            top: "-10%",
            left: "15%",
            animation: "float-slow 22s ease-in-out infinite",
          }}
        />
        <div
          className="absolute w-[450px] h-[450px] rounded-full opacity-25"
          style={{
            background: "radial-gradient(circle, rgba(79,195,247,0.3), transparent 70%)",
            top: "40%",
            right: "-5%",
            animation: "float-medium 18s ease-in-out infinite",
            filter: "blur(80px)",
          }}
        />
        <div
          className="absolute w-[350px] h-[350px] rounded-full opacity-20"
          style={{
            background: "radial-gradient(circle, rgba(130,143,255,0.35), transparent 70%)",
            bottom: "5%",
            left: "5%",
            animation: "float-slow 25s ease-in-out infinite reverse",
            filter: "blur(60px)",
          }}
        />
        {/* Grid overlay */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
            backgroundSize: "60px 60px",
          }}
        />
      </div>

      <div className="relative z-10 max-w-5xl mx-auto px-6 text-center">
        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[rgba(94,106,210,0.1)] border border-[rgba(94,106,210,0.2)] mb-8"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-[#7170ff] animate-pulse" />
          <span className="text-[13px] font-medium text-[#7170ff]">Your personal AI context layer</span>
        </motion.div>

        {/* Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="text-[48px] md:text-[64px] lg:text-[72px] font-extrabold leading-[1.0] tracking-[-0.04em] text-[#f7f8f8] mb-6"
        >
          Stop explaining yourself
          <br />
          <span className="text-gradient">to AI again and again.</span>
        </motion.h1>

        {/* Subheadline */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.35 }}
          className="text-[16px] md:text-[18px] text-[#8a8f98] max-w-2xl mx-auto mb-10 leading-relaxed"
        >
          Context Bank turns your scattered files, notes, and knowledge into reusable
          context that helps AI understand you, your work, and your goals.
        </motion.p>

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="flex flex-wrap gap-4 justify-center mb-16"
        >
          <Button variant="primary" size="lg" onClick={onSignUpClick}>
            Join the Private Pilot
            <ArrowRight size={16} />
          </Button>
          <Button variant="glass" size="lg" onClick={() => document.getElementById("how-it-works")?.scrollIntoView({ behavior: "smooth" })}>
            <Play size={14} />
            See How It Works
          </Button>
        </motion.div>

        {/* Visual Mockup — Context flow */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.6 }}
          className="relative max-w-4xl mx-auto"
        >
          <div className="flex flex-col md:flex-row items-center justify-center gap-4 md:gap-6">
            {/* Scattered files */}
            <div className="flex flex-col gap-2 items-center">
              <p className="text-[11px] font-medium text-[#62666d] uppercase tracking-wider mb-2">Your scattered data</p>
              <div className="flex flex-wrap gap-2 justify-center max-w-[200px]">
                {["📄 Notes", "📊 Slides", "📁 Projects", "✍️ Writing", "📋 PDFs"].map((item, i) => (
                  <motion.div
                    key={item}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.8 + i * 0.08 }}
                    className="px-3 py-1.5 rounded-lg bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.06)] text-[12px] text-[#8a8f98] font-medium"
                  >
                    {item}
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Arrow */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1.2 }}
              className="text-[#5e6ad2] text-2xl rotate-90 md:rotate-0"
            >
              →
            </motion.div>

            {/* Context vault */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 1.0, duration: 0.5 }}
              className="relative"
            >
              <div className="w-44 h-44 rounded-2xl bg-gradient-to-br from-[rgba(94,106,210,0.15)] to-[rgba(113,112,255,0.05)] border border-[rgba(113,112,255,0.2)] flex items-center justify-center shadow-[0_0_60px_rgba(94,106,210,0.15)]">
                <div className="text-center">
                  <div className="text-3xl mb-2">🏦</div>
                  <p className="text-[13px] font-semibold text-[#f7f8f8]">Context Bank</p>
                  <p className="text-[11px] text-[#8a8f98]">Organized · Structured</p>
                </div>
              </div>
              {/* Glow ring */}
              <div className="absolute inset-0 rounded-2xl shadow-[0_0_40px_rgba(113,112,255,0.1)] pointer-events-none" style={{ animation: "pulse-glow 3s ease-in-out infinite" }} />
            </motion.div>

            {/* Arrow */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1.4 }}
              className="text-[#5e6ad2] text-2xl rotate-90 md:rotate-0"
            >
              →
            </motion.div>

            {/* AI output */}
            <div className="flex flex-col gap-2 items-center">
              <p className="text-[11px] font-medium text-[#62666d] uppercase tracking-wider mb-2">AI that knows you</p>
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 1.3 }}
                className="p-4 rounded-xl bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.06)] max-w-[200px]"
              >
                <p className="text-[12px] text-[#d0d6e0] italic leading-relaxed">
                  &ldquo;I understand your project context. Let me help you draft from here.&rdquo;
                </p>
                <div className="flex items-center gap-1.5 mt-2">
                  <div className="w-4 h-4 rounded-full bg-gradient-to-br from-[#5e6ad2] to-[#7170ff]" />
                  <span className="text-[10px] text-[#62666d]">AI Assistant</span>
                </div>
              </motion.div>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Bottom fade */}
      <div className="absolute bottom-0 inset-x-0 h-32 bg-gradient-to-t from-[#08090a] to-transparent pointer-events-none" />
    </section>
  );
}
