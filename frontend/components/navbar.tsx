"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";

const navLinks = [
  { name: "Platform", href: "#platform" },
  { name: "Agents", href: "#agents" },
  { name: "Workflow", href: "#workflow" },
  { name: "Pricing", href: "#pricing" },
];

export function Navbar() {
  const [isOpen, setIsOpen] = useState(false);
  const router = useRouter();

  const goToDashboard = () => {
    setIsOpen(false);
    router.push("/dashboard");
  };

  return (
    <nav className="fixed left-0 right-0 top-0 z-50 border-b border-border/70 bg-white/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex items-center justify-between h-16">
          <Link
            href="/"
            className="flex items-center gap-2"
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-accent shadow-sm shadow-blue-200">
              <span className="text-xs font-bold tracking-widest text-white">V</span>
            </div>
            <span className="text-lg font-bold tracking-tight text-text-primary">Ventrix</span>
          </Link>

          <div className="hidden md:flex items-center gap-8">
            {navLinks.map((link) => (
              <Link
                key={link.name}
                href={link.href}
                className="text-sm font-medium text-text-secondary transition-colors duration-200 hover:text-blue-accent"
              >
                {link.name}
              </Link>
            ))}
            <Button variant="ghost" size="sm" onClick={goToDashboard}>Log in</Button>
            <Button variant="primary" size="sm" onClick={goToDashboard}>Get started <span className="ml-1.5">→</span></Button>
          </div>

          <button
            className="p-2 text-text-secondary md:hidden"
            onClick={() => setIsOpen(!isOpen)}
            aria-label="Toggle navigation"
            aria-expanded={isOpen}
          >
            <span className="block w-6 h-0.5 bg-text-primary mb-1.5"></span>
            <span className="block w-6 h-0.5 bg-text-primary mb-1.5"></span>
            <span className="block w-6 h-0.5 bg-text-primary"></span>
          </button>
        </div>
        {isOpen && (
          <div className="border-t border-border py-4 md:hidden">
            <div className="flex flex-col gap-1">
              {navLinks.map((link) => (
                <Link key={link.name} href={link.href} onClick={() => setIsOpen(false)} className="rounded-lg px-3 py-2 text-sm font-medium text-text-secondary hover:bg-secondary hover:text-blue-accent">
                  {link.name}
                </Link>
              ))}
              <Button variant="primary" size="sm" className="mt-2" onClick={goToDashboard}>Get started</Button>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}
