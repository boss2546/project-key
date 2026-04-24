"use client";

import React from "react";
import { motion } from "framer-motion";
import { ArrowRight, Calendar } from "lucide-react";
import { useSectionReveal, staggerContainer, fadeUpItem } from "@/hooks/useScrollReveal";
import Button from "./Button";

interface CTASectionProps {
  onSignUpClick: () => void;
}

export default function CTASection({ onSignUpClick }: CTASectionProps) {
  const { ref, isInView } = useSectionReveal();

  return (
    <section className="section-padding relative overflow-hidden">
      {/* Background glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div
          className="absolute w-[600px] h-[600px] rounded-full left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          style={{
            background: "radial-gradient(circle, rgba(94,106,210,0.12) 0%, transparent 65%)",
          }}
        />
      </div>

      <div className="relative max-w-3xl mx-auto text-center" ref={ref}>
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
        >
          <motion.h2
            variants={fadeUpItem}
            className="text-[36px] md:text-[48px] font-bold tracking-[-0.03em] leading-tight text-[#f7f8f8] mb-5"
          >
            Build an AI that<br />
            <span className="text-gradient">understands your context.</span>
          </motion.h2>

          <motion.p variants={fadeUpItem} className="text-[16px] text-[#8a8f98] mb-10 max-w-lg mx-auto">
            Join the private pilot and help shape the future of personal context for AI.
          </motion.p>

          <motion.div
            variants={fadeUpItem}
            className="flex flex-wrap gap-4 justify-center"
          >
            <Button variant="primary" size="lg" onClick={onSignUpClick}>
              Sign Up
              <ArrowRight size={16} />
            </Button>
            <Button variant="glass" size="lg">
              <Calendar size={16} />
              Book a Demo
            </Button>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
