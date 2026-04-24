"use client";

import React from "react";
import { motion } from "framer-motion";

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
}

export default function GlassCard({
  children,
  className = "",
  hover = true,
}: GlassCardProps) {
  return (
    <motion.div
      whileHover={hover ? { y: -6, scale: 1.01 } : undefined}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={`
        relative overflow-hidden rounded-xl
        bg-[rgba(255,255,255,0.02)] 
        border border-[rgba(255,255,255,0.06)]
        backdrop-blur-sm
        transition-all duration-300
        ${hover ? "hover:border-[rgba(113,112,255,0.25)] hover:shadow-[0_12px_40px_rgba(0,0,0,0.3)]" : ""}
        ${className}
      `}
    >
      {/* Gradient overlay on hover */}
      <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-[rgba(94,106,210,0.06)] to-transparent opacity-0 hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
      <div className="relative z-10">{children}</div>
    </motion.div>
  );
}
