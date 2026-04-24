"use client";

import React from "react";
import { motion } from "framer-motion";
import { GraduationCap, Briefcase, Palette, Users } from "lucide-react";
import { useSectionReveal, staggerContainer, fadeUpItem } from "@/hooks/useScrollReveal";
import GlassCard from "./GlassCard";

const useCases = [
  {
    icon: GraduationCap,
    title: "AI Study Context",
    audience: "For students",
    pain: "AI doesn't know what I'm studying.",
    outcome: "Get more accurate study help and revision support.",
    color: "#4fc3f7",
  },
  {
    icon: Briefcase,
    title: "AI Work Context",
    audience: "For professionals",
    pain: "I keep explaining the same project background.",
    outcome: "Write, summarize, and decide faster with project-aware AI.",
    color: "#818cf8",
  },
  {
    icon: Palette,
    title: "Creator Brain",
    audience: "For creators",
    pain: "AI doesn't write in my voice.",
    outcome: "Create content that matches your style and strategy.",
    color: "#7170ff",
  },
  {
    icon: Users,
    title: "Team Knowledge for AI",
    audience: "For small teams",
    pain: "Team knowledge is scattered across tools and people.",
    outcome: "Make team knowledge searchable, reusable, and AI-ready.",
    color: "#5e6ad2",
  },
];

export default function UseCasesSection() {
  const { ref, isInView } = useSectionReveal();

  return (
    <section className="section-padding relative" id="use-cases">
      <div className="max-w-5xl mx-auto" ref={ref}>
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="text-center mb-16"
        >
          <motion.p variants={fadeUpItem} className="text-[13px] font-medium text-[#7170ff] uppercase tracking-wider mb-4">
            Use cases
          </motion.p>
          <motion.h2
            variants={fadeUpItem}
            className="text-[36px] md:text-[48px] font-bold tracking-[-0.03em] leading-tight text-[#f7f8f8]"
          >
            Built for how<br />
            <span className="text-gradient">you actually use AI.</span>
          </motion.h2>
        </motion.div>

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="grid grid-cols-1 md:grid-cols-2 gap-5"
        >
          {useCases.map((uc, i) => (
            <motion.div key={i} variants={fadeUpItem}>
              <GlassCard className="p-7 h-full">
                <div className="flex items-start gap-4 mb-4">
                  <div
                    className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0"
                    style={{
                      background: `${uc.color}12`,
                      border: `1px solid ${uc.color}25`,
                    }}
                  >
                    <uc.icon size={20} style={{ color: uc.color }} />
                  </div>
                  <div>
                    <h3 className="text-[17px] font-semibold text-[#f7f8f8] tracking-[-0.01em]">{uc.title}</h3>
                    <p className="text-[12px] text-[#62666d] font-medium">{uc.audience}</p>
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex items-start gap-2">
                    <span className="text-red-400/70 text-[12px] mt-0.5 shrink-0">✕</span>
                    <p className="text-[13px] text-[#8a8f98] italic">&ldquo;{uc.pain}&rdquo;</p>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-emerald-400/70 text-[12px] mt-0.5 shrink-0">✓</span>
                    <p className="text-[13px] text-[#d0d6e0]">{uc.outcome}</p>
                  </div>
                </div>
              </GlassCard>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
