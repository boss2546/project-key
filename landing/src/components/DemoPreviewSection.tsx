"use client";

import React from "react";
import { motion } from "framer-motion";
import { FileText, StickyNote, Presentation, FolderKanban, PenTool, Package, FileCheck, Settings, BookOpen, Sparkles } from "lucide-react";
import { useSectionReveal, staggerContainer, fadeUpItem } from "@/hooks/useScrollReveal";

const sources = [
  { icon: StickyNote, label: "Notes", color: "#ffd54f" },
  { icon: FileText, label: "PDFs", color: "#ff8a65" },
  { icon: Presentation, label: "Slides", color: "#4fc3f7" },
  { icon: FolderKanban, label: "Projects", color: "#81c784" },
  { icon: PenTool, label: "Writing Style", color: "#b39ddb" },
];

const contextItems = [
  { icon: BookOpen, label: "Project Summary" },
  { icon: FileCheck, label: "Key Decisions" },
  { icon: Settings, label: "User Preferences" },
  { icon: Package, label: "Relevant Docs" },
];

export default function DemoPreviewSection() {
  const { ref, isInView } = useSectionReveal();

  return (
    <section className="section-padding relative" id="demo">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[rgba(0,0,0,0.3)] to-transparent pointer-events-none" />

      <div className="relative max-w-6xl mx-auto" ref={ref}>
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="text-center mb-16"
        >
          <motion.p variants={fadeUpItem} className="text-[13px] font-medium text-[#7170ff] uppercase tracking-wider mb-4">
            Product preview
          </motion.p>
          <motion.h2
            variants={fadeUpItem}
            className="text-[36px] md:text-[48px] font-bold tracking-[-0.03em] leading-tight text-[#f7f8f8] mb-3"
          >
            See it in action.
          </motion.h2>
          <motion.p variants={fadeUpItem} className="text-[15px] text-[#8a8f98]">
            From scattered sources to AI-ready context — all in one view.
          </motion.p>
        </motion.div>

        {/* Mock interface */}
        <motion.div
          variants={fadeUpItem}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="rounded-2xl border border-[rgba(255,255,255,0.06)] bg-[rgba(255,255,255,0.01)] overflow-hidden shadow-[0_20px_60px_rgba(0,0,0,0.4)]"
        >
          {/* Window bar */}
          <div className="flex items-center gap-2 px-4 py-3 border-b border-[rgba(255,255,255,0.05)] bg-[rgba(255,255,255,0.02)]">
            <div className="flex gap-1.5">
              <div className="w-2.5 h-2.5 rounded-full bg-[#ff5f57]" />
              <div className="w-2.5 h-2.5 rounded-full bg-[#febc2e]" />
              <div className="w-2.5 h-2.5 rounded-full bg-[#28c840]" />
            </div>
            <span className="ml-3 text-[11px] text-[#62666d] font-medium">Context Bank — Workspace</span>
          </div>

          {/* Three panels */}
          <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-[rgba(255,255,255,0.05)] min-h-[350px]">
            {/* Sources panel */}
            <div className="p-5">
              <h4 className="text-[12px] font-semibold text-[#62666d] uppercase tracking-wider mb-4">Sources</h4>
              <div className="space-y-2">
                {sources.map((s, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={isInView ? { opacity: 1, x: 0 } : {}}
                    transition={{ delay: 0.5 + i * 0.08 }}
                    className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.04)] hover:border-[rgba(255,255,255,0.08)] transition-colors cursor-default"
                  >
                    <s.icon size={16} style={{ color: s.color }} />
                    <span className="text-[13px] text-[#d0d6e0]">{s.label}</span>
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Context Pack panel */}
            <div className="p-5 bg-[rgba(94,106,210,0.02)]">
              <h4 className="text-[12px] font-semibold text-[#7170ff] uppercase tracking-wider mb-4">
                Context Pack
              </h4>
              <div className="space-y-2">
                {contextItems.map((c, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 10 }}
                    animate={isInView ? { opacity: 1, y: 0 } : {}}
                    transition={{ delay: 0.7 + i * 0.08 }}
                    className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-[rgba(113,112,255,0.06)] border border-[rgba(113,112,255,0.12)] cursor-default"
                  >
                    <c.icon size={16} className="text-[#7170ff]" />
                    <span className="text-[13px] text-[#d0d6e0]">{c.label}</span>
                  </motion.div>
                ))}
              </div>
              <div className="mt-4 p-3 rounded-lg bg-[rgba(255,255,255,0.02)] border border-dashed border-[rgba(255,255,255,0.06)]">
                <p className="text-[11px] text-[#62666d]">Pack Status: <span className="text-emerald-400">Ready</span></p>
                <p className="text-[11px] text-[#62666d]">4 context modules · 12 source files</p>
              </div>
            </div>

            {/* AI Output panel */}
            <div className="p-5">
              <h4 className="text-[12px] font-semibold text-[#62666d] uppercase tracking-wider mb-4">AI Output</h4>
              <motion.div
                initial={{ opacity: 0 }}
                animate={isInView ? { opacity: 1 } : {}}
                transition={{ delay: 1.0 }}
                className="space-y-3"
              >
                <div className="flex items-start gap-2.5">
                  <div className="w-6 h-6 rounded-full bg-gradient-to-br from-[#5e6ad2] to-[#7170ff] flex items-center justify-center shrink-0 mt-0.5">
                    <Sparkles size={12} className="text-white" />
                  </div>
                  <div className="p-3 rounded-lg bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)]">
                    <p className="text-[13px] text-[#d0d6e0] leading-relaxed">
                      Now I understand your project context. I can see your key decisions,
                      preferences, and relevant documents.
                    </p>
                    <p className="text-[13px] text-[#d0d6e0] leading-relaxed mt-2">
                      I can help you draft, summarize, or plan from here.
                    </p>
                  </div>
                </div>
                <div className="flex gap-2 ml-8">
                  <span className="px-2.5 py-1 rounded-md bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.06)] text-[11px] text-[#8a8f98] cursor-default">
                    Draft report
                  </span>
                  <span className="px-2.5 py-1 rounded-md bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.06)] text-[11px] text-[#8a8f98] cursor-default">
                    Summarize
                  </span>
                  <span className="px-2.5 py-1 rounded-md bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.06)] text-[11px] text-[#8a8f98] cursor-default">
                    Plan next steps
                  </span>
                </div>
              </motion.div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
