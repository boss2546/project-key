"use client";

import React from "react";
import { motion } from "framer-motion";
import { MessageSquareOff, RotateCcw, Upload, Brain, HelpCircle } from "lucide-react";
import { useSectionReveal, staggerContainer, fadeUpItem } from "@/hooks/useScrollReveal";
import GlassCard from "./GlassCard";

const painPoints = [
  { icon: MessageSquareOff, text: "Why do I have to explain myself again?" },
  { icon: RotateCcw, text: "Why does every new chat feel like starting from zero?" },
  { icon: Upload, text: "Why do I need to upload the same files again?" },
  { icon: Brain, text: "Why does AI forget my project context?" },
  { icon: HelpCircle, text: "Why does AI sound smart but still not understand me?" },
];

export default function ProblemSection() {
  const { ref, isInView } = useSectionReveal();

  return (
    <section className="section-padding relative" id="problem">
      {/* Background accent */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[rgba(0,0,0,0.3)] to-transparent pointer-events-none" />

      <div className="relative max-w-5xl mx-auto" ref={ref}>
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="text-center mb-16"
        >
          <motion.p variants={fadeUpItem} className="text-[13px] font-medium text-[#7170ff] uppercase tracking-wider mb-4">
            The problem
          </motion.p>
          <motion.h2
            variants={fadeUpItem}
            className="text-[36px] md:text-[48px] font-bold tracking-[-0.03em] leading-tight text-[#f7f8f8] mb-5"
          >
            AI is smart.<br />
            <span className="text-[#8a8f98]">But it still doesn&apos;t know your world.</span>
          </motion.h2>
        </motion.div>

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
        >
          {painPoints.map((point, i) => (
            <motion.div key={i} variants={fadeUpItem}>
              <GlassCard className="p-6 h-full">
                <point.icon size={22} className="text-[#7170ff] mb-4 opacity-70" />
                <p className="text-[15px] text-[#d0d6e0] font-medium leading-relaxed">{point.text}</p>
              </GlassCard>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
