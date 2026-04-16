'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function AppHeader() {
  const pathname = usePathname();
  const showNav = pathname !== '/submit';

  return (
    <header className="bg-black/30 docked full-width top-0 sticky z-50">
      <div className="flex justify-between items-center w-full max-w-6xl mx-auto px-6 md:px-10 h-20">
        <Link
          href="/"
          className="text-lg font-semibold tracking-tight text-on-surface/60 font-headline"
        >
          MatDAO
        </Link>

        {showNav ? (
          <nav className="hidden md:flex items-center gap-8 text-sm text-on-surface/40">
            <Link className="hover:text-on-surface/70 transition-colors" href="/submit">
              Evaluation
            </Link>
            <Link className="hover:text-on-surface/70 transition-colors" href="/upsell">
              Accuracy
            </Link>
          </nav>
        ) : null}

        <div className="flex items-center gap-2">
          <button
            type="button"
            className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs text-on-surface/70 hover:bg-white/10 transition-colors"
            aria-label="Profile"
          >
            <span className="font-medium">Profile</span>
            <span className="material-symbols-outlined text-base leading-none">expand_more</span>
          </button>
        </div>
      </div>
    </header>
  );
}
