"use client";

import React from "react";
import { motion } from "framer-motion";
import { FolderOpen, FileText, Package, Zap } from "lucide-react";
import { useSectionReveal, staggerContainer, fadeUpItem } from "@/hooks/useScrollReveal";
import GlassCard from "./GlassCard";

const capabilities = [
  {
    icon: FolderOpen,
    title: "Organize scattered files",
    desc: "Bring your notes, PDFs, projects, and documents into one structured space.",
    color: "#4fc3f7",
  },
  {
    icon: FileText,
    title: "Summarize key knowledge",
    desc: "AI reads, tags, and summarizes so you don't have to re-explain.",
    color: "#818cf8",
  },
  {
    icon: Package,
    title: "Create context packs",
    desc: "Bundle related knowledge into reusable packs for study, work, or projects.",
    color: "#7170ff",
  },
  {
    icon: Zap,
    title: "Use with AI tools",
    desc: "Export your context or connect directly — AI finally understands you.",
    color: "#5e6ad2",
  },
];

export default function SolutionSection() {
  const { ref, isInView } = useSectionReveal();

  return (
    <section className="section-padding relative" id="solution">
      <div className="max-w-5xl mx-auto" ref={ref}>
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="text-center mb-16"
        >
          <motion.p variants={fadeUpItem} className="text-[13px] font-medium text-[#7170ff] uppercase tracking-wider mb-4">
            The solution
          </motion.p>
          <motion.h2
            variants={fadeUpItem}
            className="text-[36px] md:text-[48px] font-bold tracking-[-0.03em] leading-tight text-[#f7f8f8] mb-5"
          >
            Your context, organized once.<br />
            <span className="text-gradient">Reused everywhere.</span>
          </motion.h2>
          <motion.p variants={fadeUpItem} className="text-[16px] text-[#8a8f98] max-w-xl mx-auto">
            Context Bank helps you organize selected data into reusable context packs for AI.
          </motion.p>
        </motion.div>

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="grid grid-cols-1 md:grid-cols-2 gap-5"
        >
          {capabilities.map((cap, i) => (
            <motion.div key={i} variants={fadeUpItem}>
              <GlassCard className="p-7 h-full">
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center mb-4"
                  style={{
                    background: `${cap.color}15`,
                    border: `1px solid ${cap.color}25`,
                  }}
                >
                  <cap.icon size={20} style={{ color: cap.color }} />
                </div>
                <h3 className="text-[17px] font-semibold text-[#f7f8f8] mb-2 tracking-[-0.01em]">{cap.title}</h3>
                <p className="text-[14px] text-[#8a8f98] leading-relaxed">{cap.desc}</p>
              </GlassCard>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
