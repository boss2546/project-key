"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X } from "lucide-react";
import Button from "./Button";

interface NavbarProps {
  onLoginClick: () => void;
  onSignUpClick: () => void;
}

const navLinks = [
  { label: "Product", href: "#solution" },
  { label: "How It Works", href: "#how-it-works" },
  { label: "Use Cases", href: "#use-cases" },
  { label: "Privacy", href: "#trust" },
  { label: "Demo", href: "#demo" },
];

export default function Navbar({ onLoginClick, onSignUpClick }: NavbarProps) {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <>
      <motion.nav
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] }}
        className={`fixed top-0 left-0 right-0 z-[100] transition-all duration-300 ${
          scrolled
            ? "bg-[rgba(8,9,10,0.85)] backdrop-blur-xl border-b border-[rgba(255,255,255,0.05)]"
            : "bg-transparent"
        }`}
      >
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          {/* Logo */}
          <a href="#" className="flex items-center gap-2.5 group">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#5e6ad2] to-[#7170ff] flex items-center justify-center shadow-[0_0_20px_rgba(94,106,210,0.3)]">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <rect x="3" y="3" width="7" height="7" rx="1.5" fill="white" opacity="0.9" />
                <rect x="14" y="3" width="7" height="7" rx="1.5" fill="white" opacity="0.6" />
                <rect x="3" y="14" width="7" height="7" rx="1.5" fill="white" opacity="0.6" />
                <rect x="14" y="14" width="7" height="7" rx="1.5" fill="white" opacity="0.3" />
              </svg>
            </div>
            <span className="text-[16px] font-semibold text-[#f7f8f8] tracking-[-0.02em] group-hover:text-white transition-colors">
              Context Bank
            </span>
          </a>

          {/* Desktop Links */}
          <div className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="px-3.5 py-2 text-[13px] font-medium text-[#d0d6e0] hover:text-[#f7f8f8] rounded-lg hover:bg-[rgba(255,255,255,0.04)] transition-all"
              >
                {link.label}
              </a>
            ))}
          </div>

          {/* Desktop Actions */}
          <div className="hidden md:flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={onLoginClick}>
              Log in
            </Button>
            <Button variant="primary" size="sm" onClick={onSignUpClick}>
              Sign Up
            </Button>
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="md:hidden w-9 h-9 rounded-lg bg-[rgba(255,255,255,0.05)] flex items-center justify-center text-[#d0d6e0] hover:text-white transition-colors"
          >
            {mobileOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </motion.nav>

      {/* Mobile Menu */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="fixed top-16 left-0 right-0 z-[99] bg-[rgba(8,9,10,0.95)] backdrop-blur-xl border-b border-[rgba(255,255,255,0.05)] md:hidden"
          >
            <div className="p-4 flex flex-col gap-1">
              {navLinks.map((link) => (
                <a
                  key={link.label}
                  href={link.href}
                  onClick={() => setMobileOpen(false)}
                  className="px-4 py-3 text-[14px] font-medium text-[#d0d6e0] hover:text-[#f7f8f8] rounded-lg hover:bg-[rgba(255,255,255,0.04)] transition-all"
                >
                  {link.label}
                </a>
              ))}
              <div className="flex gap-3 mt-3 pt-3 border-t border-[rgba(255,255,255,0.05)]">
                <Button variant="ghost" size="sm" className="flex-1" onClick={() => { setMobileOpen(false); onLoginClick(); }}>
                  Log in
                </Button>
                <Button variant="primary" size="sm" className="flex-1" onClick={() => { setMobileOpen(false); onSignUpClick(); }}>
                  Sign Up
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
