"use client";

import React from "react";
import { motion } from "framer-motion";
import { Lock, UserCheck, Download, Trash2, ShieldOff, BrainCircuit, Filter, Leaf } from "lucide-react";
import { useSectionReveal, staggerContainer, fadeUpItem } from "@/hooks/useScrollReveal";

const principles = [
  { icon: Lock, label: "Private by default" },
  { icon: UserCheck, label: "User-controlled context" },
  { icon: Download, label: "Export anytime" },
  { icon: Trash2, label: "Delete anytime" },
  { icon: ShieldOff, label: "Revoke access" },
  { icon: BrainCircuit, label: "No training without consent" },
  { icon: Filter, label: "Only selected data is used" },
  { icon: Leaf, label: "Start with low-risk data" },
];

export default function TrustSection() {
  const { ref, isInView } = useSectionReveal();

  return (
    <section className="section-padding relative" id="trust">
      <div className="max-w-5xl mx-auto" ref={ref}>
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="text-center mb-16"
        >
          <motion.p variants={fadeUpItem} className="text-[13px] font-medium text-[#7170ff] uppercase tracking-wider mb-4">
            Trust & Privacy
          </motion.p>
          <motion.h2
            variants={fadeUpItem}
            className="text-[36px] md:text-[48px] font-bold tracking-[-0.03em] leading-tight text-[#f7f8f8] mb-5"
          >
            Built around<br />
            <span className="text-[#8a8f98]">user control.</span>
          </motion.h2>
          <motion.p variants={fadeUpItem} className="text-[15px] text-[#8a8f98] max-w-lg mx-auto">
            Your data belongs to you. We give you the controls to decide what to share, what to keep, and what to delete.
          </motion.p>
        </motion.div>

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="grid grid-cols-2 md:grid-cols-4 gap-4"
        >
          {principles.map((p, i) => (
            <motion.div
              key={i}
              variants={fadeUpItem}
              className="flex flex-col items-center text-center p-5 rounded-xl bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] hover:border-[rgba(113,112,255,0.15)] transition-all duration-300"
            >
              <div className="w-10 h-10 rounded-xl bg-[rgba(113,112,255,0.08)] border border-[rgba(113,112,255,0.15)] flex items-center justify-center mb-3">
                <p.icon size={18} className="text-[#7170ff]" />
              </div>
              <p className="text-[13px] text-[#d0d6e0] font-medium leading-snug">{p.label}</p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
