'use client';

import { usePathname } from 'next/navigation';
import { AnimatedRouteLink } from '@/components/AnimatedRouteLink';

export default function AppHeader() {
  const pathname = usePathname();
  const showNav = pathname !== '/submit';

  return (
    <header className="bg-black/30 docked full-width top-0 sticky z-50">
      <div className="flex justify-between items-center w-full max-w-6xl mx-auto px-6 md:px-10 h-20">
        <AnimatedRouteLink
          href="/"
          className="text-lg font-semibold tracking-tight text-on-surface/60 font-headline"
        >
          MatDAO
        </AnimatedRouteLink>

        {showNav ? (
          <nav className="hidden md:flex items-center gap-8 text-sm text-on-surface/40">
            <AnimatedRouteLink className="hover:text-on-surface/70 transition-colors" href="/submit">
              Evaluation
            </AnimatedRouteLink>
            <AnimatedRouteLink className="hover:text-on-surface/70 transition-colors" href="/upsell">
              Accuracy
            </AnimatedRouteLink>
          </nav>
        ) : null}

        <div className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-medium text-on-surface/70">
          Prototype
        </div>
      </div>
    </header>
  );
}
