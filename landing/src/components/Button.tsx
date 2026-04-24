"use client";

import React from "react";
import { motion } from "framer-motion";

interface ButtonProps {
  children: React.ReactNode;
  variant?: "primary" | "ghost" | "glass" | "outline";
  size?: "sm" | "md" | "lg";
  onClick?: () => void;
  className?: string;
  type?: "button" | "submit";
  disabled?: boolean;
}

export default function Button({
  children,
  variant = "primary",
  size = "md",
  onClick,
  className = "",
  type = "button",
  disabled = false,
}: ButtonProps) {
  const base =
    "inline-flex items-center justify-center gap-2 font-medium rounded-lg transition-all duration-300 cursor-pointer select-none";

  const variants = {
    primary:
      "bg-[#5e6ad2] text-white hover:bg-[#7170ff] btn-glow",
    ghost:
      "bg-[rgba(255,255,255,0.02)] text-[#e2e4e7] border border-[rgba(255,255,255,0.08)] hover:bg-[rgba(255,255,255,0.06)] hover:border-[rgba(255,255,255,0.15)]",
    glass:
      "glass text-[#d0d6e0] hover:bg-[rgba(255,255,255,0.06)] hover:text-white",
    outline:
      "border border-[#23252a] text-[#d0d6e0] hover:border-[#7170ff] hover:text-white bg-transparent",
  };

  const sizes = {
    sm: "px-4 py-2 text-[13px]",
    md: "px-6 py-2.5 text-[14px]",
    lg: "px-8 py-3.5 text-[15px] font-semibold",
  };

  return (
    <motion.button
      type={type}
      whileHover={disabled ? {} : { scale: 1.02 }}
      whileTap={disabled ? {} : { scale: 0.98 }}
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      className={`${base} ${variants[variant]} ${sizes[size]} ${className} ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
    >
      {children}
    </motion.button>
  );
}
