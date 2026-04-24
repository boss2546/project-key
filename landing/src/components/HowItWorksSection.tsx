"use client";

import React from "react";
import { motion } from "framer-motion";
import { Upload, Tags, Layers, Sparkles } from "lucide-react";
import { useSectionReveal, staggerContainer, fadeUpItem } from "@/hooks/useScrollReveal";

const steps = [
  {
    num: "01",
    icon: Upload,
    title: "Collect",
    desc: "Bring selected files, notes, projects, and knowledge.",
    color: "#4fc3f7",
  },
  {
    num: "02",
    icon: Tags,
    title: "Organize",
    desc: "We classify, tag, summarize, and structure your information.",
    color: "#818cf8",
  },
  {
    num: "03",
    icon: Layers,
    title: "Contextualize",
    desc: "Turn your data into reusable context packs for study, work, or creation.",
    color: "#7170ff",
  },
  {
    num: "04",
    icon: Sparkles,
    title: "Use with AI",
    desc: "Reuse the right context without starting from zero every time.",
    color: "#5e6ad2",
  },
];

export default function HowItWorksSection() {
  const { ref, isInView } = useSectionReveal();

  return (
    <section className="section-padding relative" id="how-it-works">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[rgba(0,0,0,0.3)] to-transparent pointer-events-none" />

      <div className="relative max-w-5xl mx-auto" ref={ref}>
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="text-center mb-20"
        >
          <motion.p variants={fadeUpItem} className="text-[13px] font-medium text-[#7170ff] uppercase tracking-wider mb-4">
            How it works
          </motion.p>
          <motion.h2
            variants={fadeUpItem}
            className="text-[36px] md:text-[48px] font-bold tracking-[-0.03em] leading-tight text-[#f7f8f8]"
          >
            From scattered data<br />
            <span className="text-[#8a8f98]">to AI-ready intelligence.</span>
          </motion.h2>
        </motion.div>

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="grid grid-cols-1 md:grid-cols-4 gap-6 relative"
        >
          {/* Connecting line (desktop) */}
          <div className="hidden md:block absolute top-[60px] left-[12%] right-[12%] h-px bg-gradient-to-r from-[rgba(79,195,247,0.3)] via-[rgba(113,112,255,0.3)] to-[rgba(94,106,210,0.3)]" />

          {steps.map((step, i) => (
            <motion.div key={i} variants={fadeUpItem} className="relative text-center">
              {/* Step circle */}
              <div className="relative z-10 mx-auto mb-6">
                <div
                  className="w-[72px] h-[72px] rounded-2xl mx-auto flex items-center justify-center border"
                  style={{
                    background: `${step.color}10`,
                    borderColor: `${step.color}25`,
                  }}
                >
                  <step.icon size={28} style={{ color: step.color }} />
                </div>
                <div className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-[#191a1b] border border-[rgba(255,255,255,0.08)] flex items-center justify-center">
                  <span className="text-[10px] font-bold text-[#7170ff]">{step.num}</span>
                </div>
              </div>

              <h3 className="text-[17px] font-semibold text-[#f7f8f8] mb-2">{step.title}</h3>
              <p className="text-[14px] text-[#8a8f98] leading-relaxed max-w-[200px] mx-auto">{step.desc}</p>
            </motion.div>
          ))}
        </motion.div>

        {/* Flow diagram */}
        <motion.div
          variants={fadeUpItem}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="mt-16 flex items-center justify-center gap-4 text-[13px] font-medium"
        >
          <span className="px-4 py-2 rounded-lg bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.06)] text-[#8a8f98]">
            Scattered Data
          </span>
          <span className="text-[#5e6ad2]">→</span>
          <span className="px-4 py-2 rounded-lg bg-[rgba(94,106,210,0.1)] border border-[rgba(94,106,210,0.2)] text-[#7170ff]">
            Structured Context
          </span>
          <span className="text-[#5e6ad2]">→</span>
          <span className="px-4 py-2 rounded-lg bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.06)] text-[#8a8f98]">
            AI-ready Intelligence
          </span>
        </motion.div>
      </div>
    </section>
  );
}
