'use client';

import { usePathname } from 'next/navigation';
import { AnimatedRouteLink } from '@/components/AnimatedRouteLink';

export default function AppHeader() {
  const pathname = usePathname();
  const showNav = pathname !== '/submit';

  return (
    <header className="sticky top-0 z-50 border-b border-white/[0.1] bg-black/[0.48] backdrop-blur-md">
      <div className="flex justify-between items-center w-full max-w-6xl mx-auto px-6 md:px-10 h-20">
        <AnimatedRouteLink
          href="/"
          className="text-lg font-semibold tracking-tight text-white/78 font-headline hover:text-[#bdfdff] transition-colors"
        >
          MatDAO
        </AnimatedRouteLink>

        {showNav ? (
          <nav className="hidden md:flex items-center gap-8 text-sm text-white/45">
            <AnimatedRouteLink className="hover:text-white/80 transition-colors" href="/submit">
              Evaluation
            </AnimatedRouteLink>
            <AnimatedRouteLink className="hover:text-white/80 transition-colors" href="/upsell">
              Accuracy
            </AnimatedRouteLink>
          </nav>
        ) : null}

        <div className="rounded-full border border-white/[0.18] bg-white/[0.08] px-4 py-2 text-xs font-medium text-white/70">
          Prototype
        </div>
      </div>
    </header>
  );
}
