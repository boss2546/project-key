"use client";

import React from "react";

const footerLinks = [
  {
    title: "Product",
    links: ["Features", "How It Works", "Demo", "Roadmap"],
  },
  {
    title: "Use Cases",
    links: ["Students", "Professionals", "Creators", "Teams"],
  },
  {
    title: "Company",
    links: ["Privacy", "Terms", "Contact", "Blog"],
  },
];

export default function Footer() {
  return (
    <footer className="border-t border-[rgba(255,255,255,0.04)] bg-[rgba(0,0,0,0.2)]">
      <div className="max-w-6xl mx-auto px-6 py-16">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <div className="flex items-center gap-2.5 mb-4">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#5e6ad2] to-[#7170ff] flex items-center justify-center">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                  <rect x="3" y="3" width="7" height="7" rx="1.5" fill="white" opacity="0.9" />
                  <rect x="14" y="3" width="7" height="7" rx="1.5" fill="white" opacity="0.6" />
                  <rect x="3" y="14" width="7" height="7" rx="1.5" fill="white" opacity="0.6" />
                  <rect x="14" y="14" width="7" height="7" rx="1.5" fill="white" opacity="0.3" />
                </svg>
              </div>
              <span className="text-[15px] font-semibold text-[#f7f8f8]">Context Bank</span>
            </div>
            <p className="text-[13px] text-[#62666d] leading-relaxed max-w-[200px]">
              Your personal AI context layer. Organized once, reused everywhere.
            </p>
          </div>

          {/* Links */}
          {footerLinks.map((group) => (
            <div key={group.title}>
              <h4 className="text-[13px] font-semibold text-[#8a8f98] mb-4">{group.title}</h4>
              <ul className="space-y-2.5">
                {group.links.map((link) => (
                  <li key={link}>
                    <a
                      href="#"
                      className="text-[13px] text-[#62666d] hover:text-[#d0d6e0] transition-colors"
                    >
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="pt-8 border-t border-[rgba(255,255,255,0.04)] flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-[12px] text-[#62666d]">
            © 2026 Context Bank. All rights reserved.
          </p>
          <div className="flex gap-6">
            <a href="#" className="text-[12px] text-[#62666d] hover:text-[#8a8f98] transition-colors">Privacy Policy</a>
            <a href="#" className="text-[12px] text-[#62666d] hover:text-[#8a8f98] transition-colors">Terms of Service</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
